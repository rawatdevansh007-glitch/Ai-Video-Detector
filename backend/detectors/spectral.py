import cv2
import numpy as np
import matplotlib.cm as cm
from typing import Dict, Any, Tuple

class SpectralDetector:
    """
    2D Fast Fourier Transform (FFT) & Azimuthal Power Spectrum Analysis.
    Detects high-frequency periodic grid spikes, upsampling artifacts, and
    deviations from natural 1/f^alpha photographic power decay laws.
    """

    @staticmethod
    def analyze_frame(image: np.ndarray) -> Tuple[float, Dict[str, Any], np.ndarray]:
        """
        Analyzes a single frame's 2D frequency spectrum.
        Returns:
            (anomaly_score [0.0 - 1.0], details_dict, visual_heatmap_bgr)
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Take native center crop to preserve pixel-level periodic grid frequencies without interpolation blur
        h, w = gray.shape
        size = 256
        if h < size or w < size:
            size = min(h, w)
            # Ensure even dimension
            if size % 2 != 0:
                size -= 1
        
        cy, cx = h // 2, w // 2
        gray_crop = gray[cy - size//2 : cy + size//2, cx - size//2 : cx + size//2].astype(np.float32)

        # Apply 2D Hanning window to suppress boundary edge leakage
        hann_1d = np.hanning(size)
        hann_2d = np.outer(hann_1d, hann_1d)
        windowed = gray_crop * hann_2d

        # Compute 2D Fast Fourier Transform
        f_transform = np.fft.fft2(windowed)
        f_shift = np.fft.fftshift(f_transform)
        magnitude = np.abs(f_shift)
        
        # Log magnitude spectrum for visualization
        log_mag = np.log1p(magnitude)
        norm_log_mag = cv2.normalize(log_mag, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

        # 1. Compute Radial Azimuthal Average Profile
        center = size // 2
        y, x = np.ogrid[:size, :size]
        r = np.hypot(x - center, y - center).astype(int)
        
        # Bin frequencies up to radius center
        max_r = center
        r_flat = r.ravel()
        mag_flat = magnitude.ravel()
        
        # Calculate mean magnitude for each radial ring
        radial_bins = np.bincount(r_flat[r_flat < max_r], weights=mag_flat[r_flat < max_r])
        radial_counts = np.bincount(r_flat[r_flat < max_r])
        radial_profile = radial_bins / np.maximum(radial_counts, 1)

        # 2. Check for High-Frequency Energy Ratio
        low_freq = radial_profile[2:int(max_r * 0.25)]
        high_freq = radial_profile[int(max_r * 0.5):int(max_r * 0.85)]

        low_mean = np.mean(low_freq) if len(low_freq) > 0 else 1.0
        high_mean = np.mean(high_freq) if len(high_freq) > 0 else 0.0

        hf_ratio = high_mean / max(low_mean, 1e-6)

        # 3. Detect Periodic Grid Spikes (Upsampling Fingerprints)
        blurred_mag = cv2.GaussianBlur(log_mag, (15, 15), 0)
        highpass_mag = log_mag - blurred_mag
        
        # Zero out center DC neighborhood
        cv2.circle(highpass_mag, (center, center), 15, 0, -1)
        
        # Find peak anomalies in high-pass spectrum
        std_val = float(np.std(highpass_mag))
        mean_val = float(np.mean(highpass_mag))
        threshold = mean_val + 2.5 * std_val
        spikes = int(np.sum(highpass_mag > threshold))

        # Calculate normalized anomaly score [0.0 - 1.0]
        # In natural photographic video crops, spikes range 0-10. Synthetic upsampler grids trigger >= 20.
        spike_score = float(np.clip(spikes / 20.0, 0.0, 1.0))
        hf_score = float(np.clip((hf_ratio - 0.03) / 0.12, 0.0, 1.0))

        # Radial profile variance / smoothness check
        radial_diffs = np.diff(np.log1p(radial_profile[5:int(max_r * 0.8)]))
        profile_irregularity = float(np.std(radial_diffs)) if len(radial_diffs) > 0 else 0.0
        irregularity_score = float(np.clip(profile_irregularity * 2.0, 0.0, 1.0))

        # If periodic spikes are detected, it's a primary signal for generative grid artifacts
        if spikes >= 15:
            composite_score = float(np.clip(
                0.70 * spike_score + 0.20 * hf_score + 0.10 * irregularity_score,
                0.0, 1.0
            ))
        else:
            composite_score = float(np.clip(
                0.50 * spike_score + 0.30 * hf_score + 0.20 * irregularity_score,
                0.0, 1.0
            ))

        # Generate visual false-color heatmap (Magma/Inferno colormap)
        colored_spectrum = cm.inferno(norm_log_mag / 255.0)[:, :, :3]
        colored_bgr = (colored_spectrum * 255).astype(np.uint8)
        colored_bgr = cv2.cvtColor(colored_bgr, cv2.COLOR_RGB2BGR)

        # Overlay crosshair lines for aesthetic forensic look
        cv2.drawMarker(colored_bgr, (center, center), (0, 255, 255), cv2.MARKER_CROSS, 20, 1)

        details = {
            "periodic_spikes": int(spikes),
            "high_freq_ratio": round(float(hf_ratio), 4),
            "profile_irregularity": round(float(profile_irregularity), 4),
            "score": round(composite_score, 3)
        }

        return composite_score, details, colored_bgr
