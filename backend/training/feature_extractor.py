import os
import sys
import cv2
import numpy as np
from typing import Dict, Any, List, Tuple, Optional

# Ensure backend directory is in path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from video_processor import VideoProcessor
from detectors.spectral import SpectralDetector
from detectors.temporal import TemporalDetector
from detectors.spatial import SpatialNoiseDetector
from detectors.facial import FacialSeamDetector


class ForensicFeatureExtractor:
    """
    Extracts a dense 24-dimensional normalized forensic feature vector
    from video files for training and inference with machine learning models.
    """

    FEATURE_NAMES: List[str] = [
        # 1-5: Spectral (FFT) features
        "spectral_mean_score",
        "spectral_peak_score",
        "spectral_mean_spikes",
        "spectral_mean_hf_ratio",
        "spectral_mean_irregularity",
        # 6-10: Temporal (Optical Flow) features
        "temporal_mean_score",
        "temporal_peak_score",
        "temporal_mean_flow_mag",
        "temporal_mean_curl",
        "temporal_mean_warp_residual",
        # 11-15: Spatial Noise & Sensor (PRNU) features
        "spatial_noise_mean_score",
        "spatial_noise_peak_score",
        "spatial_noise_mean_var",
        "spatial_noise_mean_cov",
        "spatial_noise_flat_patch_ratio",
        # 16-19: Facial & Boundary Seam features
        "facial_detected_ratio",
        "facial_mean_anomaly",
        "facial_mean_seam_score",
        "facial_mean_texture_anomaly",
        # 20-24: Color, Histogram & Coherence features
        "color_channel_correlation",
        "color_histogram_entropy",
        "illumination_drift_var",
        "interframe_ssim_mean",
        "interframe_ssim_var",
    ]

    def __init__(self):
        self.facial_detector = FacialSeamDetector()

    def extract_features(
        self,
        video_path: str,
        sample_count: int = 12
    ) -> Tuple[np.ndarray, Dict[str, float]]:
        """
        Extracts the 24-dimensional forensic feature vector from a video file.

        Returns:
            features: 1D numpy array of shape (24,), dtype float32
            feature_dict: Dict mapping feature name to value
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Sample frames and consecutive pairs
        video_data = VideoProcessor.inspect_and_sample(video_path, target_samples=sample_count)
        sampled_frames = video_data.get("sampled_frames", [])
        consecutive_pairs = video_data.get("consecutive_pairs", [])

        if not sampled_frames:
            # Fallback zero-vector if video could not be decoded
            features = np.zeros(len(self.FEATURE_NAMES), dtype=np.float32)
            return features, {name: 0.0 for name in self.FEATURE_NAMES}

        # 1. Spectral Layer metrics
        spec_scores = []
        spec_spikes = []
        spec_hf_ratios = []
        spec_irregularities = []

        # 2. Spatial Noise Layer metrics
        noise_scores = []
        noise_vars = []
        noise_covs = []
        noise_flat_ratios = []

        # 3. Facial Layer metrics
        face_scores = []
        face_seams = []
        face_textures = []
        faces_detected_count = 0

        # 4. Color & Illumination metrics
        frame_luminances = []
        color_corrs = []
        entropies = []

        for frame_item in sampled_frames:
            img = frame_item["image"]
            h, w = img.shape[:2]

            # Spectral
            s_score, s_det, _ = SpectralDetector.analyze_frame(img)
            spec_scores.append(s_score)
            spec_spikes.append(s_det.get("periodic_spikes", 0))
            spec_hf_ratios.append(s_det.get("high_freq_ratio", 0.0))
            spec_irregularities.append(s_det.get("profile_irregularity", 0.0))

            # Spatial
            n_score, n_det, _ = SpatialNoiseDetector.analyze_frame(img)
            noise_scores.append(n_score)
            noise_vars.append(n_det.get("mean_noise_variance", 0.0))
            noise_covs.append(n_det.get("variance_cov", 0.0))
            noise_flat_ratios.append(n_det.get("flat_patch_ratio", 0.0))

            # Facial
            f_score, f_det, _, has_face = self.facial_detector.analyze_frame(img)
            if has_face:
                faces_detected_count += 1
                face_scores.append(f_score)
                faces = f_det.get("faces", [])
                if faces:
                    face_seams.append(faces[0].get("seam_score", 0.0))
                    face_textures.append(faces[0].get("texture_anomaly", 0.0))
                else:
                    face_seams.append(0.0)
                    face_textures.append(0.0)

            # Color channel correlation
            if len(img.shape) == 3 and img.shape[2] == 3:
                b = img[:, :, 0].ravel().astype(np.float32)
                g = img[:, :, 1].ravel().astype(np.float32)
                r = img[:, :, 2].ravel().astype(np.float32)
                # Sample 1000 pixels for fast correlation
                idx = np.random.choice(len(b), min(1000, len(b)), replace=False)
                b_s, g_s, r_s = b[idx], g[idx], r[idx]
                rg_corr = float(np.corrcoef(r_s, g_s)[0, 1]) if np.std(r_s) > 1e-4 and np.std(g_s) > 1e-4 else 0.0
                rb_corr = float(np.corrcoef(r_s, b_s)[0, 1]) if np.std(r_s) > 1e-4 and np.std(b_s) > 1e-4 else 0.0
                gb_corr = float(np.corrcoef(g_s, b_s)[0, 1]) if np.std(g_s) > 1e-4 and np.std(b_s) > 1e-4 else 0.0
                color_corrs.append((rg_corr + rb_corr + gb_corr) / 3.0)
                
                # Luminance and Shannon Entropy
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray = img
                color_corrs.append(1.0)

            frame_luminances.append(float(np.mean(gray)))

            # Histogram entropy
            hist, _ = np.histogram(gray, bins=32, range=(0, 256), density=True)
            hist = hist[hist > 0]
            entropy = -np.sum(hist * np.log2(hist))
            entropies.append(float(entropy))

        # Temporal Layer metrics
        temp_scores = []
        temp_mags = []
        temp_curls = []
        temp_warps = []
        ssim_scores = []

        for pair in consecutive_pairs:
            f1, f2 = pair
            t_score, t_det, _ = TemporalDetector.analyze_pair(f1, f2)
            temp_scores.append(t_score)
            temp_mags.append(t_det.get("mean_flow_magnitude", 0.0))
            temp_curls.append(t_det.get("flow_jitter_density", 0.0))
            temp_warps.append(t_det.get("warp_residual_error", 0.0))

            # Simplified SSIM for temporal coherence
            g1 = cv2.cvtColor(f1, cv2.COLOR_BGR2GRAY) if len(f1.shape) == 3 else f1
            g2 = cv2.cvtColor(f2, cv2.COLOR_BGR2GRAY) if len(f2.shape) == 3 else f2
            g1_s = cv2.resize(g1, (128, 128)).astype(np.float32)
            g2_s = cv2.resize(g2, (128, 128)).astype(np.float32)
            mu1, mu2 = np.mean(g1_s), np.mean(g2_s)
            var1, var2 = np.var(g1_s), np.var(g2_s)
            covar = np.mean((g1_s - mu1) * (g2_s - mu2))
            c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
            ssim = ((2 * mu1 * mu2 + c1) * (2 * covar + c2)) / ((mu1**2 + mu2**2 + c1) * (var1 + var2 + c2) + 1e-6)
            ssim_scores.append(float(np.clip(ssim, -1.0, 1.0)))

        # Aggregate metrics safely
        total_frames = max(len(sampled_frames), 1)
        feat_dict: Dict[str, float] = {
            # Spectral
            "spectral_mean_score": float(np.mean(spec_scores)) if spec_scores else 0.0,
            "spectral_peak_score": float(np.percentile(spec_scores, 80)) if spec_scores else 0.0,
            "spectral_mean_spikes": float(np.mean(spec_spikes)) if spec_spikes else 0.0,
            "spectral_mean_hf_ratio": float(np.mean(spec_hf_ratios)) if spec_hf_ratios else 0.0,
            "spectral_mean_irregularity": float(np.mean(spec_irregularities)) if spec_irregularities else 0.0,
            # Temporal
            "temporal_mean_score": float(np.mean(temp_scores)) if temp_scores else 0.0,
            "temporal_peak_score": float(np.percentile(temp_scores, 80)) if temp_scores else 0.0,
            "temporal_mean_flow_mag": float(np.mean(temp_mags)) if temp_mags else 0.0,
            "temporal_mean_curl": float(np.mean(temp_curls)) if temp_curls else 0.0,
            "temporal_mean_warp_residual": float(np.mean(temp_warps)) if temp_warps else 0.0,
            # Spatial
            "spatial_noise_mean_score": float(np.mean(noise_scores)) if noise_scores else 0.0,
            "spatial_noise_peak_score": float(np.percentile(noise_scores, 80)) if noise_scores else 0.0,
            "spatial_noise_mean_var": float(np.mean(noise_vars)) if noise_vars else 0.0,
            "spatial_noise_mean_cov": float(np.mean(noise_covs)) if noise_covs else 0.0,
            "spatial_noise_flat_patch_ratio": float(np.mean(noise_flat_ratios)) if noise_flat_ratios else 0.0,
            # Facial
            "facial_detected_ratio": float(faces_detected_count / total_frames),
            "facial_mean_anomaly": float(np.mean(face_scores)) if face_scores else 0.0,
            "facial_mean_seam_score": float(np.mean(face_seams)) if face_seams else 0.0,
            "facial_mean_texture_anomaly": float(np.mean(face_textures)) if face_textures else 0.0,
            # Color & Dynamics
            "color_channel_correlation": float(np.mean(color_corrs)) if color_corrs else 0.0,
            "color_histogram_entropy": float(np.mean(entropies)) if entropies else 0.0,
            "illumination_drift_var": float(np.var(frame_luminances)) if frame_luminances else 0.0,
            "interframe_ssim_mean": float(np.mean(ssim_scores)) if ssim_scores else 1.0,
            "interframe_ssim_var": float(np.var(ssim_scores)) if ssim_scores else 0.0,
        }

        # Build ordered vector
        features = np.array([feat_dict[name] for name in self.FEATURE_NAMES], dtype=np.float32)
        # Ensure no NaN or Inf
        features = np.nan_to_num(features, nan=0.0, posinf=1.0, neginf=0.0)

        return features, feat_dict
