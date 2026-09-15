import os
import sys
import glob
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple, Optional, Callable

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Ensure backend directory is in path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from training.feature_extractor import ForensicFeatureExtractor

SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".avi", ".webm", ".mkv"}

class VideoDatasetManager:
    """
    Manages loading, caching, and scanning of video datasets
    from 'dataset/real' and 'dataset/ai' directory structures.
    """

    def __init__(self, dataset_dir: str = "dataset"):
        self.dataset_dir = dataset_dir
        self.real_dir = os.path.join(dataset_dir, "real")
        self.ai_dir = os.path.join(dataset_dir, "ai")
        self.cache_file = os.path.join(dataset_dir, "dataset_cache.csv")
        self.extractor = ForensicFeatureExtractor()

        # Ensure directory structure exists
        os.makedirs(self.real_dir, exist_ok=True)
        os.makedirs(self.ai_dir, exist_ok=True)

    def _get_file_sig(self, file_path: str) -> str:
        """Computes a fast signature (size + mtime) to detect file changes."""
        try:
            stat = os.stat(file_path)
            return f"{stat.st_size}_{stat.st_mtime}"
        except Exception:
            return ""

    def get_video_files(self) -> Tuple[List[str], List[str]]:
        """Returns list of real and ai video paths."""
        real_files = []
        ai_files = []

        for root, _, files in os.walk(self.real_dir):
            for f in files:
                if os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS:
                    real_files.append(os.path.abspath(os.path.join(root, f)))

        for root, _, files in os.walk(self.ai_dir):
            for f in files:
                if os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS:
                    ai_files.append(os.path.abspath(os.path.join(root, f)))

        return sorted(real_files), sorted(ai_files)

    def load_cache(self) -> pd.DataFrame:
        """Loads cached features if available."""
        if os.path.exists(self.cache_file):
            try:
                df = pd.read_csv(self.cache_file)
                # Verify required columns exist
                required_cols = {"file_path", "file_sig", "label"} | set(ForensicFeatureExtractor.FEATURE_NAMES)
                if required_cols.issubset(set(df.columns)):
                    return df
            except Exception as e:
                print(f"Warning: Could not read cache file ({e}). Starting fresh.")
        return pd.DataFrame()

    def save_cache(self, df: pd.DataFrame) -> None:
        """Saves feature dataframe to cache file."""
        os.makedirs(os.path.dirname(os.path.abspath(self.cache_file)), exist_ok=True)
        df.to_csv(self.cache_file, index=False)

    def scan_and_extract(
        self,
        sample_count: int = 12,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Tuple[np.ndarray, np.ndarray, List[str], List[str]]:
        """
        Scans all videos in dataset/real and dataset/ai.
        Uses cached features when files haven't changed, extracts features for new/modified videos.

        Returns:
            X: numpy array of shape (N, 24)
            y: numpy array of shape (N,) with 0=Real, 1=AI
            feature_names: List of 24 feature names
            file_paths: List of absolute file paths
        """
        real_files, ai_files = self.get_video_files()
        all_items: List[Tuple[str, int]] = [(f, 0) for f in real_files] + [(f, 1) for f in ai_files]

        if not all_items:
            return (
                np.empty((0, len(ForensicFeatureExtractor.FEATURE_NAMES)), dtype=np.float32),
                np.empty((0,), dtype=int),
                ForensicFeatureExtractor.FEATURE_NAMES,
                []
            )

        cache_df = self.load_cache()
        cache_map = {}
        if not cache_df.empty:
            for _, row in cache_df.iterrows():
                cache_map[row["file_path"]] = row

        updated_rows = []
        total = len(all_items)

        for idx, (path, label) in enumerate(all_items):
            sig = self._get_file_sig(path)
            cached_row = cache_map.get(path)

            if cached_row is not None and cached_row["file_sig"] == sig and cached_row["label"] == label:
                # Use cache
                row_dict = cached_row.to_dict()
                updated_rows.append(row_dict)
                if progress_callback:
                    progress_callback(idx + 1, total, f"Cached: {os.path.basename(path)}")
            else:
                # Extract features
                if progress_callback:
                    progress_callback(idx + 1, total, f"Extracting: {os.path.basename(path)}")

                try:
                    _, feat_dict = self.extractor.extract_features(path, sample_count=sample_count)
                    row_dict = {
                        "file_path": path,
                        "file_sig": sig,
                        "label": label,
                        **feat_dict
                    }
                    updated_rows.append(row_dict)
                except Exception as e:
                    print(f"Error extracting features from {path}: {e}")
                    # Skip problematic file or use default zeros
                    continue

        if not updated_rows:
            return (
                np.empty((0, len(ForensicFeatureExtractor.FEATURE_NAMES)), dtype=np.float32),
                np.empty((0,), dtype=int),
                ForensicFeatureExtractor.FEATURE_NAMES,
                []
            )

        new_df = pd.DataFrame(updated_rows)
        self.save_cache(new_df)

        feature_names = ForensicFeatureExtractor.FEATURE_NAMES
        X = new_df[feature_names].to_numpy(dtype=np.float32)
        y = new_df["label"].to_numpy(dtype=int)
        file_paths = new_df["file_path"].tolist()

        return X, y, feature_names, file_paths

    def get_summary(self) -> Dict[str, Any]:
        """Returns overview of current dataset files and cached entries."""
        real_files, ai_files = self.get_video_files()
        cache_df = self.load_cache()

        return {
            "dataset_dir": os.path.abspath(self.dataset_dir),
            "real_videos_count": len(real_files),
            "ai_videos_count": len(ai_files),
            "total_videos": len(real_files) + len(ai_files),
            "cached_entries": len(cache_df) if not cache_df.empty else 0,
            "has_sufficient_data": (len(real_files) >= 2 and len(ai_files) >= 2)
        }
