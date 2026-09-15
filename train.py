#!/usr/bin/env python
"""
VeritasVideo ML Training Pipeline CLI.
Allows training, evaluating, and exporting custom models using a dataset of videos.

Usage:
    python train.py --data-dir dataset/ --model-type hist_gb
    python train.py --generate-samples  # To generate starter calibration samples
"""

import os
import sys
import argparse

# Ensure UTF-8 console output on Windows to prevent UnicodeEncodeError on filenames with emojis
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Add backend to sys.path
backend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from training.dataset import VideoDatasetManager
from training.trainer import ModelTrainer, DEFAULT_MODEL_PATH
from training.synthetic_generator import generate_dataset_samples


def print_banner():
    print("=" * 70)
    print("       VERITASVIDEO - CUSTOM MACHINE LEARNING TRAINING PIPELINE       ")
    print("=" * 70)


def format_confusion_matrix(cm_dict: dict) -> str:
    tn = cm_dict.get("true_negatives", 0)
    fp = cm_dict.get("false_positives", 0)
    fn = cm_dict.get("false_negatives", 0)
    tp = cm_dict.get("true_positives", 0)

    lines = [
        "                      Predicted Real      Predicted AI",
        f"  Actual Real (0):        {tn:^10}          {fp:^10}",
        f"  Actual AI   (1):        {fn:^10}          {tp:^10}"
    ]
    return "\n".join(lines)


def run_training(args):
    print_banner()

    dataset_dir = os.path.abspath(args.data_dir)
    real_dir = os.path.join(dataset_dir, "real")
    ai_dir = os.path.join(dataset_dir, "ai")

    # If requested or if directories are empty and --generate-samples flag passed
    if args.generate_samples:
        generate_dataset_samples(dataset_dir, count_per_class=args.sample_count)

    manager = VideoDatasetManager(dataset_dir=dataset_dir)
    summary = manager.get_summary()

    print(f"\n[*] Dataset Directory : {dataset_dir}")
    print(f"[*] Authentic Videos  : {summary['real_videos_count']} in '{real_dir}'")
    print(f"[*] AI Videos         : {summary['ai_videos_count']} in '{ai_dir}'")
    print(f"[*] Total Videos      : {summary['total_videos']}")

    if summary["total_videos"] < 4 or not summary["has_sufficient_data"]:
        print("\n[!] INSUFFICIENT DATA:")
        print(f"    You have {summary['real_videos_count']} Real and {summary['ai_videos_count']} AI videos.")
        print("    At least 2 Real videos and 2 AI videos are required to train a model.")
        print(f"\n    Tip: Run with '--generate-samples' to generate calibration samples:")
        print("         python train.py --generate-samples")
        return 1

    if args.clear_cache and os.path.exists(manager.cache_file):
        print("\n[*] Clearing feature cache as requested...")
        os.remove(manager.cache_file)

    # 1. Feature Extraction
    print("\n[*] Extracting forensic features (24-D vector per video)...")
    def progress_callback(cur, total, msg):
        print(f"    [{cur}/{total}] {msg}")

    X, y, feature_names, file_paths = manager.scan_and_extract(
        sample_count=12,
        progress_callback=progress_callback
    )

    print(f"\n[+] Feature extraction complete: {len(X)} feature vectors ready.")

    # 2. Model Training & Evaluation
    trainer = ModelTrainer()
    print(f"\n[*] Training {args.model_type.upper()} classifier...")
    print("    - Scaler: StandardScaler (fitted strictly on training split)")
    print("    - Cross-Validation: Stratified K-Fold")
    print(f"    - Test Split Ratio: {args.test_size * 100:.0f}%")

    try:
        results = trainer.train_model(
            X, y,
            feature_names=feature_names,
            model_type=args.model_type,
            test_size=args.test_size
        )
    except Exception as e:
        print(f"\n[X] Training error: {e}")
        return 1

    metrics = results["metrics"]
    cm = metrics["confusion_matrix"]

    print("\n" + "=" * 70)
    print("                      EVALUATION RESULTS                      ")
    print("=" * 70)
    print(f"  Test Accuracy           : {metrics['accuracy'] * 100:.2f}%")
    print(f"  Precision (AI Detection): {metrics['precision'] * 100:.2f}%")
    print(f"  Recall (AI Detection)   : {metrics['recall'] * 100:.2f}%")
    print(f"  F1-Score                : {metrics['f1_score']:.4f}")
    print(f"  ROC-AUC Score           : {metrics['roc_auc']:.4f}")
    print(f"  Cross-Val Accuracy (Avg): {metrics['cross_val_accuracy_mean'] * 100:.2f}% (std: ±{metrics['cross_val_accuracy_std'] * 100:.2f}%)")

    print("\n  CONFUSION MATRIX (Holdout Test Split):")
    print(format_confusion_matrix(cm))

    print("\n  TOP PREDICTIVE FORENSIC FEATURES:")
    for rank, item in enumerate(results["top_features"], 1):
        print(f"    {rank}. {item['feature']:<32} : {item['importance_pct']:>6.2f}%")

    print("\n" + "=" * 70)
    print(f"[+] Model artifact successfully exported to:")
    print(f"    {results['model_path']}")
    print("    ForensicEngine will automatically utilize this model for all future inferences.")
    print("=" * 70 + "\n")
    return 0


def run_evaluate(args):
    print_banner()
    if not os.path.exists(DEFAULT_MODEL_PATH):
        print(f"\n[!] No trained model found at {DEFAULT_MODEL_PATH}.")
        print("    Run 'python train.py' to train a new model first.")
        return 1

    model_pkg = ModelTrainer.load_model(DEFAULT_MODEL_PATH)
    if not model_pkg:
        print("\n[!] Failed to load model package.")
        return 1

    print(f"\n[*] Model Path      : {DEFAULT_MODEL_PATH}")
    print(f"[*] Model Type      : {model_pkg.get('model_type', 'unknown')}")
    print(f"[*] Trained At      : {model_pkg.get('trained_at', 'unknown')}")

    ds = model_pkg.get("dataset_summary", {})
    print(f"[*] Dataset Size    : {ds.get('total_samples', 'N/A')} videos ({ds.get('real_samples', 'N/A')} Real, {ds.get('ai_samples', 'N/A')} AI)")

    metrics = model_pkg.get("metrics", {})
    print("\n[*] Cached Model Metrics:")
    print(f"    Accuracy  : {metrics.get('accuracy', 0) * 100:.2f}%")
    print(f"    F1-Score  : {metrics.get('f1_score', 0):.4f}")
    print(f"    ROC-AUC   : {metrics.get('roc_auc', 0):.4f}")

    cm = metrics.get("confusion_matrix", {})
    if cm:
        print("\n  CONFUSION MATRIX:")
        print(format_confusion_matrix(cm))

    top_feat = model_pkg.get("feature_importances", [])[:8]
    if top_feat:
        print("\n  TOP PREDICTIVE FORENSIC FEATURES:")
        for rank, item in enumerate(top_feat, 1):
            print(f"    {rank}. {item['feature']:<32} : {item['importance_pct']:>6.2f}%")

    return 0


def main():
    parser = argparse.ArgumentParser(description="Train and evaluate VeritasVideo custom AI detection model.")
    parser.add_argument("--data-dir", type=str, default="dataset", help="Path to video dataset directory containing 'real' and 'ai' subdirectories.")
    parser.add_argument("--model-type", type=str, choices=["hist_gb", "random_forest"], default="hist_gb", help="Classifier architecture.")
    parser.add_argument("--test-size", type=float, default=0.2, help="Proportion of dataset to include in the holdout test split.")
    parser.add_argument("--generate-samples", action="store_true", help="Generate synthetic sample videos in dataset/ for quick testing.")
    parser.add_argument("--sample-count", type=int, default=4, help="Number of samples per class when using --generate-samples.")
    parser.add_argument("--clear-cache", action="store_true", help="Clear cached feature extractions.")
    parser.add_argument("--evaluate-only", action="store_true", help="Only evaluate and display the existing trained model.")

    args = parser.parse_args()

    if args.evaluate_only:
        sys.exit(run_evaluate(args))
    else:
        sys.exit(run_training(args))


if __name__ == "__main__":
    main()
