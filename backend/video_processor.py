import os
import cv2
import numpy as np
from typing import List, Dict, Tuple, Any

class VideoProcessor:
    """
    Handles video decoding, metadata inspection, compression bitrate detection,
    and extraction of sampled frames and consecutive frame pairs for temporal analysis.
    """

    @staticmethod
    def calculate_bitrate_and_compression(
        video_path: str,
        cap: cv2.VideoCapture,
        duration_sec: float,
        width: int,
        height: int
    ) -> Tuple[float, float, bool]:
        """
        Reads or computes video bitrate (Mbps), effective 1080p-equivalent bitrate,
        and determines whether heavy compression is present (< 2.0 Mbps for 1080p equivalent).
        """
        bitrate_bps = 0.0
        try:
            val = cap.get(cv2.CAP_PROP_BITRATE)
            if val is not None and val > 0:
                # In some ffmpeg builds, CAP_PROP_BITRATE is in kbps, in others bps
                bitrate_bps = val * 1000.0 if val < 100_000 else val
        except Exception:
            bitrate_bps = 0.0

        # Fallback to file size / duration
        if bitrate_bps <= 0:
            if os.path.exists(video_path):
                file_size_bytes = os.path.getsize(video_path)
                safe_duration = max(duration_sec, 0.05)
                bitrate_bps = (file_size_bytes * 8.0) / safe_duration
            else:
                bitrate_bps = 2_000_000.0  # default 2 Mbps

        bitrate_mbps = bitrate_bps / 1_000_000.0

        # 1080p equivalent pixel density scaling (1920x1080 = 2,073,600 px)
        ref_pixels = 1920.0 * 1080.0
        current_pixels = float(max(width * height, 1))
        effective_1080p_bitrate = bitrate_mbps * (ref_pixels / current_pixels)

        # Flag heavy compression if under 2.0 Mbps for 1080p equivalent pixel density
        is_heavy_compression = bool(effective_1080p_bitrate < 2.0)

        return float(bitrate_mbps), float(effective_1080p_bitrate), is_heavy_compression

    @staticmethod
    def inspect_and_sample(video_path: str, target_samples: int = 16) -> Dict[str, Any]:
        """
        Inspects video metadata, measures bitrate/compression, and extracts evenly spaced frames.
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

            if total_frames > 0 and (width <= 0 or height <= 0):
                height, width = frames_temp[0].shape[:2]

            bitrate_mbps, eff_bitrate, is_heavy = VideoProcessor.calculate_bitrate_and_compression(
                video_path, cap, duration_sec, width, height
            )
            cap.release()

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
                "resolution": f"{width}x{height}",
                "bitrate_mbps": round(bitrate_mbps, 3),
                "effective_1080p_bitrate_mbps": round(eff_bitrate, 3),
                "is_heavy_compression": is_heavy
            }
            return {
                "metadata": metadata,
                "sampled_frames": sampled_frames,
                "consecutive_pairs": consecutive_pairs
            }

        bitrate_mbps, eff_bitrate, is_heavy = VideoProcessor.calculate_bitrate_and_compression(
            video_path, cap, duration_sec, width, height
        )

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
            "resolution": f"{width}x{height}",
            "bitrate_mbps": round(bitrate_mbps, 3),
            "effective_1080p_bitrate_mbps": round(eff_bitrate, 3),
            "is_heavy_compression": is_heavy
        }

        return {
            "metadata": metadata,
            "sampled_frames": sampled_frames,
            "consecutive_pairs": consecutive_pairs
        }
