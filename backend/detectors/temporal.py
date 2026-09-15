import cv2
import numpy as np
from typing import Dict, Any, Tuple

class TemporalDetector:
    """
    Temporal Coherence & Optical Flow Jitter Analysis.
    Measures frame-to-frame flow field consistency, structural warping,
    and unnatural inter-frame texture drift characteristic of video diffusion models.
    """

    @staticmethod
    def analyze_pair(frame1: np.ndarray, frame2: np.ndarray) -> Tuple[float, Dict[str, Any], np.ndarray]:
        """
        Analyzes consecutive frame pair motion fields.
        Returns:
            (anomaly_score [0.0 - 1.0], details_dict, visual_flow_bgr)
        """
        # Convert to grayscale and downscale slightly for speed and noise reduction
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY) if len(frame1.shape) == 3 else frame1
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY) if len(frame2.shape) == 3 else frame2

        h, w = gray1.shape
        target_w = 480
        scale = target_w / w if w > target_w else 1.0
        if scale < 1.0:
            target_h = int(h * scale)
            g1 = cv2.resize(gray1, (target_w, target_h), interpolation=cv2.INTER_AREA)
            g2 = cv2.resize(gray2, (target_w, target_h), interpolation=cv2.INTER_AREA)
        else:
            g1, g2 = gray1, gray2

        # Compute Dense Optical Flow (Farneback method)
        flow = cv2.calcOpticalFlowFarneback(
            g1, g2, None,
            pyr_scale=0.5, levels=3, winsize=15,
            iterations=3, poly_n=5, poly_sigma=1.2, flags=0
        )

        mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])

        # 1. Flow Magnitude Variance and Jitter
        mean_mag = np.mean(mag)
        std_mag = np.std(mag)
        mag_cov = std_mag / max(mean_mag, 1e-4)  # Coefficient of variation

        # 2. Angular Divergence / Gradient Curl
        # Natural motion has smooth spatial gradients of flow vectors.
        # AI video drift produces high spatial divergence/irregularity in motion vectors.
        flow_dx = cv2.Sobel(flow[..., 0], cv2.CV_32F, 1, 0, ksize=3)
        flow_dy = cv2.Sobel(flow[..., 1], cv2.CV_32F, 0, 1, ksize=3)
        flow_curl = np.abs(flow_dx) + np.abs(flow_dy)
        curl_density = np.mean(flow_curl)

        # 3. Inter-Frame Structural Residual (Motion Warped SSIM / Difference)
        # Warp g1 toward g2 using flow field
        flow_map = np.empty_like(flow)
        flow_map[..., 0] = np.repeat(np.arange(flow.shape[1])[np.newaxis, :], flow.shape[0], axis=0) + flow[..., 0]
        flow_map[..., 1] = np.repeat(np.arange(flow.shape[0])[:, np.newaxis], flow.shape[1], axis=1) + flow[..., 1]
        
        warped_g1 = cv2.remap(g1, flow_map[..., 0].astype(np.float32), flow_map[..., 1].astype(np.float32), cv2.INTER_LINEAR)
        warp_diff = cv2.absdiff(warped_g1, g2)
        mean_warp_residual = float(np.mean(warp_diff))
        p90_residual = float(np.percentile(warp_diff, 90))

        # In natural video with continuous rigid camera/object motion:
        # - Curl is close to 0 (smooth vector field)
        # - Warp residual is low
        # In synthetic video with non-rigid morphing/boiling:
        # - Curl is high, localized warp residual is high
        residual_score = float(np.clip((p90_residual - 2.0) / 12.0, 0.0, 1.0))
        curl_score = float(np.clip((curl_density - 0.25) / 0.8, 0.0, 1.0))
        cov_score = float(np.clip((mag_cov - 0.6) / 2.0, 0.0, 1.0)) if mean_mag > 0.05 else 0.0

        composite_score = float(np.clip(
            0.45 * residual_score + 0.35 * curl_score + 0.20 * cov_score,
            0.0, 1.0
        ))

        # Generate Visual HSV Optical Flow Map
        hsv = np.zeros((g1.shape[0], g1.shape[1], 3), dtype=np.uint8)
        hsv[..., 0] = ang * 180 / np.pi / 2  # Hue = angle [0-180]
        hsv[..., 1] = 255                     # Saturation = 255
        hsv[..., 2] = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX) # Value = magnitude

        flow_bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        # Resize visual map back to original frame size if downscaled
        if scale < 1.0:
            flow_bgr = cv2.resize(flow_bgr, (w, h), interpolation=cv2.INTER_LINEAR)

        details = {
            "mean_flow_magnitude": round(float(mean_mag), 3),
            "flow_jitter_density": round(float(curl_density), 3),
            "warp_residual_error": round(float(mean_warp_residual), 2),
            "score": round(composite_score, 3)
        }

        return composite_score, details, flow_bgr
