import os
import sys
import unittest
import numpy as np
import cv2

# Add backend to sys.path
backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, backend_dir)

from detectors.spectral import SpectralDetector
from detectors.temporal import TemporalDetector
from detectors.spatial import SpatialNoiseDetector
from detectors.facial import FacialSeamDetector
from engine import ForensicEngine

class TestDetectors(unittest.TestCase):

    def setUp(self):
        # Create a synthetic image with periodic grid (simulating generative upsampling)
        self.ai_image = np.ones((512, 512, 3), dtype=np.uint8) * 120
        for y in range(0, 512, 8):
            for x in range(0, 512, 8):
                self.ai_image[y, x] = 220

        # Create a natural camera image with Gaussian shot noise
        np.random.seed(42)
        base = np.zeros((512, 512, 3), dtype=np.float32)
        for y in range(512):
            base[y, :] = y * 0.4
        noise = np.random.normal(0, 5.0, (512, 512, 3))
        self.real_image = np.clip(base + noise, 0, 255).astype(np.uint8)

    def test_spectral_detector(self):
        # AI image with grid should trigger higher periodic spike anomaly than real image
        ai_score, ai_details, ai_vis = SpectralDetector.analyze_frame(self.ai_image)
        real_score, real_details, real_vis = SpectralDetector.analyze_frame(self.real_image)

        self.assertGreater(ai_score, real_score)
        self.assertGreater(ai_details["periodic_spikes"], real_details["periodic_spikes"])
        self.assertEqual(ai_vis.shape[2], 3)

    def test_temporal_detector(self):
        f1 = self.real_image.copy()
        # Rigid smooth shift (natural motion)
        M = np.float32([[1, 0, 4], [0, 1, 0]])
        f2_rigid = cv2.warpAffine(f1, M, (512, 512))
        rigid_score, rigid_details, _ = TemporalDetector.analyze_pair(f1, f2_rigid)

        # Non-rigid warping / random local jitter (synthetic morphing)
        f2_morph = f1.copy()
        cv2.circle(f2_morph, (256, 256), 60, (255, 0, 0), -1)
        morph_score, morph_details, flow_vis = TemporalDetector.analyze_pair(f1, f2_morph)

        self.assertGreater(morph_score, rigid_score)
        self.assertEqual(flow_vis.shape[2], 3)

    def test_spatial_noise_detector(self):
        score_real, details_real, _ = SpatialNoiseDetector.analyze_frame(self.real_image)
        # Completely smoothed artificial image
        smoothed_img = cv2.GaussianBlur(self.real_image, (15, 15), 0)
        score_smooth, details_smooth, _ = SpatialNoiseDetector.analyze_frame(smoothed_img)

        self.assertGreater(score_smooth, score_real)

    def test_facial_detector_without_face(self):
        detector = FacialSeamDetector()
        score, details, annotated, has_face = detector.analyze_frame(self.real_image)
        self.assertFalse(has_face)
        self.assertEqual(score, 0.0)

if __name__ == "__main__":
    unittest.main()
