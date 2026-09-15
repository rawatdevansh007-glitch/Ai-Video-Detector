import os
import sys
import unittest
from unittest.mock import patch

backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, backend_dir)

from detectors.c2pa_checker import C2PAChecker, C2PACheckResult
from engine import ForensicEngine

class TestC2PADetector(unittest.TestCase):

    def test_evaluate_manifest_openai_sora(self):
        """Tests parsing a C2PA manifest from OpenAI (Sora)."""
        manifest_data = {
            "active_manifest": "urn:c2pa:openai_sora_video",
            "manifests": {
                "urn:c2pa:openai_sora_video": {
                    "claim_generator": "OpenAI Sora v1.0",
                    "signature_info": {
                        "issuer": "OpenAI, LLC",
                        "time": "2026-08-01T12:00:00Z"
                    },
                    "assertions": [
                        {
                            "label": "c2pa.actions",
                            "data": {
                                "actions": [
                                    {
                                        "action": "c2pa.created",
                                        "softwareAgent": "OpenAI Sora",
                                        "digitalSourceType": "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        }

        result = C2PAChecker.evaluate_manifest(manifest_data)
        self.assertTrue(result.has_c2pa)
        self.assertTrue(result.is_ai_generated)
        self.assertIn("OpenAI", result.issuer)
        self.assertIn("trainedAlgorithmicMedia", result.digital_source_type)
        self.assertIn("OpenAI", result.matched_reason)

    def test_evaluate_manifest_google_veo(self):
        """Tests parsing a C2PA manifest from Google (Veo / SynthID)."""
        manifest_data = {
            "active_manifest": "urn:c2pa:google_veo",
            "manifests": {
                "urn:c2pa:google_veo": {
                    "claim_generator": "Google DeepMind Veo Video Generator",
                    "signature_info": {
                        "issuer": "Google LLC - SynthID Video Credentials",
                        "time": "2026-08-15T10:00:00Z"
                    },
                    "assertions": [
                        {
                            "label": "c2pa.actions",
                            "data": {
                                "actions": [
                                    {
                                        "action": "c2pa.created",
                                        "softwareAgent": "Google Veo 2",
                                        "digitalSourceType": "trainedAlgorithmicMedia"
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        }

        result = C2PAChecker.evaluate_manifest(manifest_data)
        self.assertTrue(result.has_c2pa)
        self.assertTrue(result.is_ai_generated)
        self.assertIn("Google", result.issuer)
        self.assertIn("Google", result.matched_reason)

    def test_evaluate_manifest_authentic_camera(self):
        """Tests parsing a C2PA manifest from an authentic hardware camera (Leica/Sony)."""
        manifest_data = {
            "active_manifest": "urn:c2pa:leica_camera",
            "manifests": {
                "urn:c2pa:leica_camera": {
                    "claim_generator": "Leica M11-P Content Credentials",
                    "signature_info": {
                        "issuer": "Leica Camera AG",
                        "time": "2026-05-10T14:30:00Z"
                    },
                    "assertions": [
                        {
                            "label": "c2pa.actions",
                            "data": {
                                "actions": [
                                    {
                                        "action": "c2pa.created",
                                        "softwareAgent": "Leica Firmware 2.1"
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        }

        result = C2PAChecker.evaluate_manifest(manifest_data)
        self.assertTrue(result.has_c2pa)
        self.assertFalse(result.is_ai_generated)
        self.assertEqual(result.issuer, "Leica Camera AG")

    def test_check_video_no_c2pa(self):
        """Tests checking standard video file without C2PA manifest."""
        samples_dir = os.path.join(os.path.dirname(__file__), "..", "samples")
        sample_path = os.path.join(samples_dir, "authentic_camera_sample.mp4")
        result = C2PAChecker.check_video(sample_path)
        self.assertFalse(result.has_c2pa)
        self.assertFalse(result.is_ai_generated)

    def test_pipeline_c2pa_ai_bypass(self):
        """Tests that when C2PA indicates an AI generator, visual scan is completely bypassed."""
        samples_dir = os.path.join(os.path.dirname(__file__), "..", "samples")
        cache_dir = os.path.join(os.path.dirname(__file__), "..", "cache")
        test_video = os.path.join(samples_dir, "authentic_camera_sample.mp4")

        mock_c2pa_result = C2PACheckResult(
            has_c2pa=True,
            is_ai_generated=True,
            issuer="OpenAI, LLC",
            claim_generator="OpenAI Sora",
            digital_source_type="http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia",
            software_agent="Sora",
            matched_reason="AI Issuer 'OpenAI, LLC' & IPTC Digital Source"
        )

        engine = ForensicEngine(cache_dir=cache_dir)

        # Mock C2PAChecker.check_video to simulate an OpenAI Sora C2PA signed video
        with patch.object(C2PAChecker, "check_video", return_value=mock_c2pa_result):
            # Also patch visual heuristic detectors to ensure they are NEVER called!
            with patch("engine.SpectralDetector.analyze_frame") as mock_spectral:
                with patch("engine.TemporalDetector.analyze_pair") as mock_temporal:
                    with patch("engine.SpatialNoiseDetector.analyze_frame") as mock_spatial:
                        res = engine.analyze_video(test_video, sample_count=8)

                        # Assert visual scan was completely bypassed!
                        mock_spectral.assert_not_called()
                        mock_temporal.assert_not_called()
                        mock_spatial.assert_not_called()

                        # Assert instant AI verdict
                        self.assertEqual(res["verdict"], "AI_GENERATED")
                        self.assertEqual(res["composite_ai_score"], 1.0)
                        self.assertEqual(res["detection_method"], "C2PA_CONTENT_CREDENTIALS")
                        self.assertTrue(res["visual_scan_bypassed"])
                        self.assertTrue(res["c2pa_provenance"]["is_ai_generated"])
                        self.assertEqual(res["c2pa_provenance"]["issuer"], "OpenAI, LLC")
                        self.assertIn("Sora", res["summary_explanation"])

if __name__ == "__main__":
    unittest.main()
