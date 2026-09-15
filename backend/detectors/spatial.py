import cv2
import numpy as np
import matplotlib.cm as cm
from typing import Dict, Any, Tuple

class SpatialNoiseDetector:
    """
    High-Pass Noise Residual & Sensor Pattern (PRNU) Consistency Analysis.
    Extracts high-frequency sensor noise residuals to evaluate natural camera shot noise
    versus artificial spatial over-smoothing and GAN/diffusion noise distribution anomalies.
    """

    @staticmethod
    def analyze_frame(image: np.ndarray) -> Tuple[float, Dict[str, Any], np.ndarray]:
        """
        Analyzes a single frame's spatial noise residual.
        Returns:
            (anomaly_score [0.0 - 1.0], details_dict, visual_noise_bgr)
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()
        
        # Standardize working size
        h, w = gray.shape
        target_dim = 512
        gray_scaled = cv2.resize(gray, (target_dim, target_dim), interpolation=cv2.INTER_AREA).astype(np.float32)

        # 1. Extract Noise Residual: I_orig - Denoised(I_orig)
        # We use a 3x3 median filter as a simple non-linear denoiser
        denoised = cv2.medianBlur(gray_scaled.astype(np.uint8), 3).astype(np.float32)
        residual = gray_scaled - denoised

        # 2. Patch-based Noise Variance Analysis
        patch_size = 32
        n_patches = target_dim // patch_size
        variances = []

        for i in range(n_patches):
            for j in range(n_patches):
                patch = residual[i*patch_size:(i+1)*patch_size, j*patch_size:(j+1)*patch_size]
                var = np.var(patch)
                variances.append(var)

        variances = np.array(variances)
        
        # Natural camera noise has a characteristic variance floor and moderate coefficient of variation
        mean_var = np.mean(variances)
        std_var = np.std(variances)
        var_cov = std_var / max(mean_var, 1e-5)

        # 3. Patch variance consistency & synthetic over-smoothing analysis
        # Natural camera sensor noise has healthy mean variance and uniform distribution across patches.
        # Synthetic video has either severe over-smoothing (mean_var < 0.5) or high patch irregularity (cov > 2.2).
        cov_anomaly = float(np.clip((var_cov - 2.0) / 2.2, 0.0, 1.0))
        smoothness_anomaly = float(np.clip((0.6 - mean_var) / 0.6, 0.0, 1.0)) if mean_var < 0.6 else 0.0
        
        # Fraction of abnormally flat/smooth patches
        flat_patch_ratio = float(np.mean(variances < 0.25))
        flat_patch_anomaly = float(np.clip(flat_patch_ratio / 0.40, 0.0, 1.0))

        composite_score = float(np.clip(
            0.40 * cov_anomaly + 0.35 * smoothness_anomaly + 0.25 * flat_patch_anomaly,
            0.0, 1.0
        ))

        # 4. Generate Visual Heatmap of Noise Residual
        # Amplify residual for human visual inspection
        amplified = np.clip(np.abs(residual) * 8.0, 0, 255).astype(np.uint8)
        norm_amplified = cv2.normalize(amplified, None, 0, 255, cv2.NORM_MINMAX)
        
        colored_noise = cm.coolwarm(norm_amplified / 255.0)[:, :, :3]
        colored_bgr = (colored_noise * 255).astype(np.uint8)
        colored_bgr = cv2.cvtColor(colored_bgr, cv2.COLOR_RGB2BGR)

        # Resize back to original aspect ratio
        visual_bgr = cv2.resize(colored_bgr, (w, h), interpolation=cv2.INTER_LINEAR)

        details = {
            "mean_noise_variance": round(float(mean_var), 3),
            "variance_cov": round(float(var_cov), 3),
            "flat_patch_ratio": round(float(flat_patch_ratio), 3),
            "score": round(composite_score, 3)
        }

        return composite_score, details, visual_bgr
