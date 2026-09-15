import os
import cv2
import numpy as np
from typing import List, Dict, Tuple, Any

class VideoProcessor:
    """
    Handles video decoding, metadata inspection, and extraction of sampled frames
    and consecutive frame pairs for temporal analysis.
    """

    @staticmethod
    def inspect_and_sample(video_path: str, target_samples: int = 16) -> Dict[str, Any]:
        """
        Inspects video metadata and extracts evenly spaced frames and frame pairs.
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration_sec = total_frames / fps if total_frames > 0 and fps > 0 else 0.0

        if total_frames <= 0:
            # Fallback: scan through frames manually
            frames_temp = []
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                frames_temp.append(frame)
            total_frames = len(frames_temp)
            duration_sec = total_frames / fps if fps > 0 else 0.0
            cap.release()
            
            # Reopen or use collected frames
            sampled_indices = np.linspace(0, max(0, total_frames - 2), min(target_samples, total_frames)).astype(int)
            sampled_frames = []
            consecutive_pairs = []
            for idx in sampled_indices:
                f1 = frames_temp[idx]
                f2 = frames_temp[min(idx + 1, total_frames - 1)]
                t = idx / fps if fps > 0 else 0.0
                sampled_frames.append({
                    "frame_index": int(idx),
                    "timestamp_sec": float(t),
                    "image": f1
                })
                consecutive_pairs.append((f1, f2))

            metadata = {
                "total_frames": total_frames,
                "fps": round(fps, 2),
                "width": width,
                "height": height,
                "duration_seconds": round(duration_sec, 2),
                "resolution": f"{width}x{height}"
            }
            return {
                "metadata": metadata,
                "sampled_frames": sampled_frames,
                "consecutive_pairs": consecutive_pairs
            }

        # Select evenly distributed indices (leaving room for consecutive pair idx+1)
        max_idx = max(0, total_frames - 2)
        count = min(target_samples, max_idx + 1)
        if count <= 1:
            sampled_indices = [0]
        else:
            sampled_indices = np.linspace(0, max_idx, count, dtype=int)
        
        # Deduplicate while preserving order
        sampled_indices = sorted(list(set(sampled_indices)))

        sampled_frames = []
        consecutive_pairs = []

        for idx in sampled_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret1, frame1 = cap.read()
            if not ret1 or frame1 is None:
                continue

            # Read consecutive frame for temporal analysis
            ret2, frame2 = cap.read()
            if not ret2 or frame2 is None:
                frame2 = frame1.copy()

            t = idx / fps if fps > 0 else 0.0
            sampled_frames.append({
                "frame_index": int(idx),
                "timestamp_sec": float(t),
                "image": frame1
            })
            consecutive_pairs.append((frame1, frame2))

        cap.release()

        if len(sampled_frames) == 0:
            raise ValueError("Failed to extract any readable frames from video.")

        metadata = {
            "total_frames": total_frames,
            "fps": round(fps, 2),
            "width": width,
            "height": height,
            "duration_seconds": round(duration_sec, 2),
            "resolution": f"{width}x{height}"
        }

        return {
            "metadata": metadata,
            "sampled_frames": sampled_frames,
            "consecutive_pairs": consecutive_pairs
        }
