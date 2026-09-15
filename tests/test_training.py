import os
import sys
import numpy as np
import pytest

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from training.feature_extractor import ForensicFeatureExtractor
from training.dataset import VideoDatasetManager
from training.trainer import ModelTrainer, DEFAULT_MODEL_PATH
from training.synthetic_generator import generate_dataset_samples
from engine import ForensicEngine

TEST_DATASET_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_dataset"))


@pytest.fixture(scope="module")
def setup_test_dataset():
    """Generates a small test dataset with 2 real and 2 AI videos."""
    os.makedirs(TEST_DATASET_DIR, exist_ok=True)
    generate_dataset_samples(TEST_DATASET_DIR, count_per_class=2)
    yield TEST_DATASET_DIR


def test_feature_extractor(setup_test_dataset):
    dataset_dir = setup_test_dataset
    real_video = os.path.join(dataset_dir, "real", "sample_real_1.mp4")
    ai_video = os.path.join(dataset_dir, "ai", "sample_ai_1.mp4")

    extractor = ForensicFeatureExtractor()

    feat_real, dict_real = extractor.extract_features(real_video, sample_count=6)
    feat_ai, dict_ai = extractor.extract_features(ai_video, sample_count=6)

    assert len(feat_real) == len(ForensicFeatureExtractor.FEATURE_NAMES)
    assert len(feat_ai) == len(ForensicFeatureExtractor.FEATURE_NAMES)
    assert len(feat_real) == 24

    # No NaN or Inf
    assert not np.isnan(feat_real).any()
    assert not np.isinf(feat_real).any()
    assert not np.isnan(feat_ai).any()
    assert not np.isinf(feat_ai).any()

    # Verify key feature dictionary keys exist
    for key in ["spectral_mean_score", "temporal_mean_curl", "spatial_noise_mean_var"]:
        assert key in dict_real
        assert key in dict_ai


def test_dataset_manager_and_caching(setup_test_dataset):
    dataset_dir = setup_test_dataset
    mgr = VideoDatasetManager(dataset_dir=dataset_dir)

    summary = mgr.get_summary()
    assert summary["real_videos_count"] >= 2
    assert summary["ai_videos_count"] >= 2
    assert summary["has_sufficient_data"] is True

    # Scan and extract
    X, y, feature_names, file_paths = mgr.scan_and_extract(sample_count=6)
    assert len(X) >= 4
    assert len(y) >= 4
    assert set(y) == {0, 1}
    assert os.path.exists(mgr.cache_file)

    # Second scan should hit cache without error
    X2, y2, _, _ = mgr.scan_and_extract(sample_count=6)
    assert np.array_equal(X, X2)
    assert np.array_equal(y, y2)


def test_model_training_pipeline(setup_test_dataset):
    dataset_dir = setup_test_dataset
    mgr = VideoDatasetManager(dataset_dir=dataset_dir)
    X, y, feature_names, _ = mgr.scan_and_extract(sample_count=6)

    test_model_dir = os.path.join(dataset_dir, "models")
    trainer = ModelTrainer(model_dir=test_model_dir)
    train_res = trainer.train_model(
        X, y,
        feature_names=feature_names,
        model_type="hist_gb",
        test_size=0.25
    )

    assert train_res["success"] is True
    metrics = train_res["metrics"]
    assert "accuracy" in metrics
    assert "f1_score" in metrics
    assert "roc_auc" in metrics
    assert "confusion_matrix" in metrics

    # Verify model artifact saved
    assert os.path.exists(train_res["model_path"])

    # Verify model package structure
    loaded = ModelTrainer.load_model(train_res["model_path"])
    assert loaded is not None
    assert "pipeline" in loaded
    assert "metrics" in loaded
    assert "feature_importances" in loaded


def test_engine_ml_inference(setup_test_dataset):
    dataset_dir = setup_test_dataset
    real_video = os.path.join(dataset_dir, "real", "sample_real_1.mp4")
    test_model_path = os.path.join(dataset_dir, "models", "custom_detector.joblib")

    engine = ForensicEngine()
    engine.model_pkg = ModelTrainer.load_model(test_model_path)
    assert engine.model_pkg is not None

    result = engine.analyze_video(real_video, sample_count=4)
    assert "ml_model" in result
    assert result["ml_model"]["is_custom_model_active"] is True
    assert result["ml_model"]["ml_ai_probability"] is not None
    assert result["detection_method"] == "TRAINED_ML_ENSEMBLE"
