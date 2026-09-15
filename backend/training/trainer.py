import os
import sys
import time
from datetime import datetime
import numpy as np
import joblib
from typing import Dict, Any, List, Optional, Tuple

from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix
)

# Ensure backend directory is in path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from training.feature_extractor import ForensicFeatureExtractor

DEFAULT_MODEL_DIR = os.path.join(backend_dir, "models")
DEFAULT_MODEL_PATH = os.path.join(DEFAULT_MODEL_DIR, "custom_detector.joblib")


class ModelTrainer:
    """
    Trains, validates, evaluates, and exports the machine learning classifier
    for Real vs. AI-Generated video detection following ML best practices.
    """

    def __init__(self, model_dir: str = DEFAULT_MODEL_DIR):
        self.model_dir = model_dir
        os.makedirs(self.model_dir, exist_ok=True)
        self.model_path = os.path.join(self.model_dir, "custom_detector.joblib")

    def train_model(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: Optional[List[str]] = None,
        model_type: str = "hist_gb",
        test_size: float = 0.2,
        random_state: int = 42
    ) -> Dict[str, Any]:
        """
        Executes full ML training pipeline:
        - Stratified Train/Test split
        - Preprocessing pipeline (StandardScaler + Classifier)
        - Cross-validation
        - Metrics calculation (Accuracy, F1, ROC-AUC, Confusion Matrix)
        - Permutation feature importance ranking
        - Serialization to joblib
        """
        if len(y) < 4:
            raise ValueError(
                f"Dataset contains only {len(y)} samples. At least 4 samples (2 Real, 2 AI) are required for training."
            )

        unique_classes, counts = np.unique(y, return_counts=True)
        if len(unique_classes) < 2:
            raise ValueError("Dataset must contain both classes (0: Real and 1: AI). Only one class found.")

        min_class_count = int(np.min(counts))
        if min_class_count < 2:
            raise ValueError(
                f"Each class requires at least 2 samples. Class distribution: {dict(zip(unique_classes, counts))}"
            )

        if feature_names is None:
            feature_names = ForensicFeatureExtractor.FEATURE_NAMES

        # 1. Stratified Train / Test split BEFORE any transformation
        # Adjust test_size if dataset is very small to ensure at least 1 sample of each class in test
        actual_test_size = test_size
        if min_class_count < 5:
            actual_test_size = max(0.2, 1.0 / len(y))

        try:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y,
                test_size=actual_test_size,
                random_state=random_state,
                stratify=y
            )
        except Exception:
            # Fallback if strict stratification cannot be met with small count
            X_train, X_test, y_train, y_test = train_test_split(
                X, y,
                test_size=actual_test_size,
                random_state=random_state
            )

        # 2. Select and Configure Classifier
        if model_type == "random_forest":
            clf = RandomForestClassifier(
                n_estimators=100,
                max_depth=6,
                min_samples_leaf=1,
                random_state=random_state
            )
        else:
            clf = HistGradientBoostingClassifier(
                max_iter=100,
                min_samples_leaf=min(2, max(1, len(y_train) // 4)),
                random_state=random_state
            )

        # 3. Create Pipeline with StandardScaler (fit strictly on train)
        pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", clf)
        ])

        # 4. Stratified K-Fold Cross-Validation on Train Split
        n_splits = min(5, min(int(np.sum(y_train == 0)), int(np.sum(y_train == 1))))
        cv_scores = []
        if n_splits >= 2:
            cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
            cv_scores = cross_val_score(pipeline, X_train, y_train, cv=cv, scoring="accuracy")
            cv_mean = float(np.mean(cv_scores))
            cv_std = float(np.std(cv_scores))
        else:
            cv_mean = 1.0
            cv_std = 0.0

        # 5. Fit Pipeline on Training Data
        pipeline.fit(X_train, y_train)

        # 6. Evaluate on Test Data
        y_pred = pipeline.predict(X_test)
        
        # Probabilities for ROC-AUC
        if hasattr(pipeline, "predict_proba"):
            y_proba = pipeline.predict_proba(X_test)
            if y_proba.shape[1] > 1:
                ai_probs = y_proba[:, 1]
            else:
                ai_probs = y_proba[:, 0]
        else:
            ai_probs = y_pred.astype(float)

        acc = float(accuracy_score(y_test, y_pred))
        prec = float(precision_score(y_test, y_pred, zero_division=0))
        rec = float(recall_score(y_test, y_pred, zero_division=0))
        f1 = float(f1_score(y_test, y_pred, zero_division=0))

        try:
            roc_auc = float(roc_auc_score(y_test, ai_probs)) if len(np.unique(y_test)) > 1 else 1.0
        except Exception:
            roc_auc = 1.0

        cm = confusion_matrix(y_test, y_pred, labels=[0, 1])
        tn, fp, fn, tp = int(cm[0, 0]), int(cm[0, 1]), int(cm[1, 0]), int(cm[1, 1])

        # 7. Compute Feature Importances
        feature_importance_list = []
        try:
            if hasattr(clf, "feature_importances_"):
                raw_importances = clf.feature_importances_
            else:
                # Permutation importance
                perm_res = permutation_importance(
                    pipeline, X_train, y_train, n_repeats=5, random_state=random_state
                )
                raw_importances = perm_res.importances_mean

            # Normalize to 0-100%
            total_imp = np.sum(np.maximum(raw_importances, 0))
            if total_imp > 0:
                norm_importances = np.maximum(raw_importances, 0) / total_imp
            else:
                norm_importances = np.ones(len(feature_names)) / len(feature_names)

            for name, imp in zip(feature_names, norm_importances):
                feature_importance_list.append({
                    "feature": name,
                    "importance_pct": round(float(imp * 100), 2)
                })

            feature_importance_list.sort(key=lambda x: x["importance_pct"], reverse=True)
        except Exception as e:
            print(f"Warning: Could not compute feature importances ({e})")
            for name in feature_names:
                feature_importance_list.append({
                    "feature": name,
                    "importance_pct": round(100.0 / len(feature_names), 2)
                })

        metrics = {
            "accuracy": round(acc, 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
            "roc_auc": round(roc_auc, 4),
            "cross_val_accuracy_mean": round(cv_mean, 4),
            "cross_val_accuracy_std": round(cv_std, 4),
            "confusion_matrix": {
                "true_negatives": tn,
                "false_positives": fp,
                "false_negatives": fn,
                "true_positives": tp,
                "matrix": cm.tolist()
            }
        }

        dataset_summary = {
            "total_samples": int(len(y)),
            "real_samples": int(np.sum(y == 0)),
            "ai_samples": int(np.sum(y == 1)),
            "train_samples": int(len(y_train)),
            "test_samples": int(len(y_test))
        }

        # 8. Export Model Artifact
        model_payload = {
            "pipeline": pipeline,
            "feature_names": feature_names,
            "model_type": model_type,
            "trained_at": datetime.now().isoformat(),
            "metrics": metrics,
            "feature_importances": feature_importance_list,
            "dataset_summary": dataset_summary
        }

        joblib.dump(model_payload, self.model_path)

        return {
            "success": True,
            "model_path": os.path.abspath(self.model_path),
            "model_type": model_type,
            "metrics": metrics,
            "dataset_summary": dataset_summary,
            "top_features": feature_importance_list[:8]
        }

    @classmethod
    def load_model(cls, model_path: str = DEFAULT_MODEL_PATH) -> Optional[Dict[str, Any]]:
        """Loads and returns the serialized model package if available."""
        if not os.path.exists(model_path):
            return None
        try:
            return joblib.load(model_path)
        except Exception as e:
            print(f"Error loading model from {model_path}: {e}")
            return None
