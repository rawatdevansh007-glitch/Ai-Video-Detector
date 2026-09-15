import os
import uuid
import cv2
import numpy as np
from typing import Dict, Any, List, Optional
import sys
# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from video_processor import VideoProcessor
from detectors.spectral import SpectralDetector
from detectors.temporal import TemporalDetector
from detectors.spatial import SpatialNoiseDetector
from detectors.facial import FacialSeamDetector
from detectors.semantic import SemanticVisionInspector
from detectors.c2pa_checker import C2PAChecker
from training.feature_extractor import ForensicFeatureExtractor
from training.trainer import DEFAULT_MODEL_PATH, ModelTrainer

class ForensicEngine:
    """
    Coordinates the multi-layer video forensics pipeline, aggregates signals,
    and produces calibrated confidence scores and frame-level anomaly timelines.
    """

    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self.facial_detector = FacialSeamDetector()
        self.feature_extractor = ForensicFeatureExtractor()
        self.model_pkg = None
        self.reload_model()

    def reload_model(self):
        """Loads or reloads the trained custom ML model package if present."""
        if os.path.exists(DEFAULT_MODEL_PATH):
            try:
                self.model_pkg = ModelTrainer.load_model(DEFAULT_MODEL_PATH)
            except Exception as e:
                print(f"Warning: Could not load custom model from {DEFAULT_MODEL_PATH}: {e}")
                self.model_pkg = None
        else:
            self.model_pkg = None

    def analyze_video(
        self,
        video_path: str,
        sample_count: int = 16,
        gemini_api_key: Optional[str] = None,
        use_custom_model: bool = True
    ) -> Dict[str, Any]:
        """
        Executes end-to-end multi-layer forensic analysis on a video file.
        """
        analysis_id = str(uuid.uuid4())[:8]
        session_cache = os.path.join(self.cache_dir, analysis_id)
        os.makedirs(session_cache, exist_ok=True)

        # 0. Check C2PA Manifest (Content Credentials) before visual scan
        c2pa_result = C2PAChecker.check_video(video_path)

        if c2pa_result.has_c2pa and c2pa_result.is_ai_generated:
            # FAST-PATH: Manifest indicates an AI generator (e.g., Google, OpenAI, Sora, Veo, etc.)
            # Instantly flag as AI-generated and bypass the visual heuristic scan.
            video_data = VideoProcessor.inspect_and_sample(video_path, target_samples=2)
            metadata = video_data["metadata"]
            sampled_frames = video_data["sampled_frames"]

            frame_results = []
            for idx, frame_item in enumerate(sampled_frames):
                img = frame_item["image"]
                frame_dir = os.path.join(session_cache, f"frame_{idx}")
                os.makedirs(frame_dir, exist_ok=True)
                cv2.imwrite(os.path.join(frame_dir, "original.jpg"), img)
                cv2.imwrite(os.path.join(frame_dir, "fft.jpg"), img)
                cv2.imwrite(os.path.join(frame_dir, "noise.jpg"), img)
                cv2.imwrite(os.path.join(frame_dir, "flow.jpg"), img)

                frame_results.append({
                    "index": idx,
                    "frame_number": frame_item["frame_index"],
                    "timestamp_sec": frame_item["timestamp_sec"],
                    "anomaly_score": 1.0,
                    "spectral_score": 1.0,
                    "temporal_score": 1.0,
                    "noise_score": 1.0,
                    "facial_score": None,
                    "has_face": False,
                    "diagnostics": f"C2PA Content Credentials verify generative AI origin: {c2pa_result.matched_reason or 'AI Generator'}"
                })

            issuer_name = c2pa_result.issuer or "AI Generator"
            generator_info = f" via {c2pa_result.claim_generator}" if c2pa_result.claim_generator and c2pa_result.claim_generator != c2pa_result.issuer else ""
            summary = (
                f"Cryptographically verified via C2PA Content Credentials: The video contains a verified cryptographic manifest "
                f"issued by {issuer_name}{generator_info} ({c2pa_result.matched_reason}). "
                f"Visual heuristic scanning was bypassed."
            )

            return {
                "analysis_id": analysis_id,
                "verdict": "AI_GENERATED",
                "composite_ai_score": 1.0,
                "confidence_level": "Cryptographically Verified",
                "detection_method": "C2PA_CONTENT_CREDENTIALS",
                "visual_scan_bypassed": True,
                "c2pa_provenance": {
                    "has_c2pa": True,
                    "is_ai_generated": True,
                    "issuer": c2pa_result.issuer,
                    "claim_generator": c2pa_result.claim_generator,
                    "digital_source_type": c2pa_result.digital_source_type,
                    "software_agent": c2pa_result.software_agent,
                    "matched_reason": c2pa_result.matched_reason,
                    "raw_manifest": c2pa_result.raw_manifest
                },
                "summary_explanation": summary,
                "semantic_reasoning": None,
                "video_metadata": metadata,
                "metrics": {
                    "spectral": {
                        "score": 1.0,
                        "status": "C2PA VERIFIED AI",
                        "description": "Visual heuristic scan bypassed; video is cryptographically signed as generative AI."
                    },
                    "temporal": {
                        "score": 1.0,
                        "status": "C2PA VERIFIED AI",
                        "description": "Visual heuristic scan bypassed; video is cryptographically signed as generative AI."
                    },
                    "noise_residual": {
                        "score": 1.0,
                        "status": "C2PA VERIFIED AI",
                        "description": "Visual heuristic scan bypassed; video is cryptographically signed as generative AI."
                    },
                    "facial": {
                        "score": 1.0,
                        "status": "C2PA VERIFIED AI",
                        "faces_detected": 0,
                        "description": "Visual heuristic scan bypassed; video is cryptographically signed as generative AI."
                    }
                },
                "frames": frame_results
            }

        # 1. Inspect and Sample Video for Visual Heuristics
        video_data = VideoProcessor.inspect_and_sample(video_path, target_samples=sample_count)
        metadata = video_data["metadata"]
        sampled_frames = video_data["sampled_frames"]
        consecutive_pairs = video_data["consecutive_pairs"]

        frame_results = []
        spectral_scores = []
        temporal_scores = []
        noise_scores = []
        facial_scores = []
        faces_detected_count = 0

        # 2. Process each frame through detection layers
        for idx, (frame_item, pair) in enumerate(zip(sampled_frames, consecutive_pairs)):
            f_idx = frame_item["frame_index"]
            timestamp = frame_item["timestamp_sec"]
            img = frame_item["image"]
            f1, f2 = pair

            # Spectral Layer (2D FFT)
            spec_score, spec_details, spec_vis = SpectralDetector.analyze_frame(img)
            spectral_scores.append(spec_score)

            # Temporal Layer (Optical Flow & Jitter)
            temp_score, temp_details, flow_vis = TemporalDetector.analyze_pair(f1, f2)
            temporal_scores.append(temp_score)

            # Spatial Noise Layer (PRNU / High-Pass Residual)
            noise_score, noise_details, noise_vis = SpatialNoiseDetector.analyze_frame(img)
            noise_scores.append(noise_score)

            # Facial & Boundary Seam Layer
            face_score, face_details, face_vis, has_face = self.facial_detector.analyze_frame(img)
            if has_face:
                faces_detected_count += 1
                facial_scores.append(face_score)

            # Save Visualizations to Session Cache
            frame_dir = os.path.join(session_cache, f"frame_{idx}")
            os.makedirs(frame_dir, exist_ok=True)

            cv2.imwrite(os.path.join(frame_dir, "original.jpg"), img)
            cv2.imwrite(os.path.join(frame_dir, "fft.jpg"), spec_vis)
            cv2.imwrite(os.path.join(frame_dir, "noise.jpg"), noise_vis)
            cv2.imwrite(os.path.join(frame_dir, "flow.jpg"), flow_vis)
            if has_face:
                cv2.imwrite(os.path.join(frame_dir, "facial.jpg"), face_vis)

            # Compute Frame-level Anomaly Index
            if has_face:
                frame_anomaly = (
                    0.35 * spec_score +
                    0.25 * temp_score +
                    0.20 * noise_score +
                    0.20 * face_score
                )
            else:
                frame_anomaly = (
                    0.40 * spec_score +
                    0.35 * temp_score +
                    0.25 * noise_score
                )

            # Generate concise diagnostics note for the frame
            diag_notes = []
            if spec_score >= 0.60:
                diag_notes.append("High-frequency periodic spectral spikes detected")
            if temp_score >= 0.60:
                diag_notes.append("Elevated optical flow motion jitter and warp residual")
            if noise_score >= 0.60:
                diag_notes.append("Irregular sensor noise residual / artificial smoothing")
            if has_face and face_score >= 0.55:
                diag_notes.append("Deepfake face boundary seam or texture mismatch")

            frame_diag = "; ".join(diag_notes) if diag_notes else "Consistent natural frame characteristics."

            frame_results.append({
                "index": idx,
                "frame_number": f_idx,
                "timestamp_sec": timestamp,
                "anomaly_score": round(float(frame_anomaly), 3),
                "spectral_score": round(float(spec_score), 3),
                "temporal_score": round(float(temp_score), 3),
                "noise_score": round(float(noise_score), 3),
                "facial_score": round(float(face_score), 3) if has_face else None,
                "has_face": has_face,
                "diagnostics": frame_diag
            })

        # 3. Aggregate Layer Scores
        avg_spectral = float(np.mean(spectral_scores)) if spectral_scores else 0.0
        avg_temporal = float(np.mean(temporal_scores)) if temporal_scores else 0.0
        avg_noise = float(np.mean(noise_scores)) if noise_scores else 0.0
        avg_facial = float(np.mean(facial_scores)) if facial_scores else 0.0

        # Peak anomaly consideration (take 80th percentile to prevent a single clean frame from masking AI video)
        peak_spectral = float(np.percentile(spectral_scores, 80)) if spectral_scores else 0.0
        peak_temporal = float(np.percentile(temporal_scores, 80)) if temporal_scores else 0.0
        peak_noise = float(np.percentile(noise_scores, 80)) if noise_scores else 0.0

        comb_spectral = 0.6 * avg_spectral + 0.4 * peak_spectral
        comb_temporal = 0.6 * avg_temporal + 0.4 * peak_temporal
        comb_noise = 0.6 * avg_noise + 0.4 * peak_noise

        # 4. Ensemble Composite Score (Heuristics)
        if faces_detected_count > 0:
            heuristic_ai_score = (
                0.35 * comb_spectral +
                0.30 * comb_temporal +
                0.20 * comb_noise +
                0.15 * avg_facial
            )
        else:
            heuristic_ai_score = (
                0.40 * comb_spectral +
                0.35 * comb_temporal +
                0.25 * comb_noise
            )
        heuristic_ai_score = float(np.clip(heuristic_ai_score, 0.0, 1.0))

        # Check for trained custom ML model
        ml_model_info = {
            "is_custom_model_active": False,
            "model_type": None,
            "ml_ai_probability": None,
            "trained_at": None,
            "scoring_mode": "Calibrated Heuristic Baseline"
        }

        if self.model_pkg is not None and "pipeline" in self.model_pkg and use_custom_model:
            try:
                feat_vec, _ = self.feature_extractor.extract_features(video_path, sample_count=min(sample_count, 12))
                pipeline = self.model_pkg["pipeline"]
                proba = pipeline.predict_proba(feat_vec.reshape(1, -1))
                ml_prob = float(proba[0][1] if proba.shape[1] > 1 else proba[0][0])

                # Cross-verification safeguard: if physics & sensor noise heuristics are overwhelmingly authentic,
                # weight physical optical properties higher to avoid false positives
                if heuristic_ai_score < 0.28 and comb_spectral < 0.25 and comb_temporal < 0.25:
                    composite_ai_score = float(np.clip(0.30 * ml_prob + 0.70 * heuristic_ai_score, 0.0, 1.0))
                else:
                    # Blend: 60% Trained ML Classifier + 40% Heuristic Cross-Verification
                    composite_ai_score = float(np.clip(0.60 * ml_prob + 0.40 * heuristic_ai_score, 0.0, 1.0))

                ml_model_info = {
                    "is_custom_model_active": True,
                    "model_type": self.model_pkg.get("model_type", "hist_gb"),
                    "ml_ai_probability": round(ml_prob, 4),
                    "trained_at": self.model_pkg.get("trained_at"),
                    "scoring_mode": "Trained ML Ensemble (Cross-Verified)"
                }
            except Exception as e:
                print(f"Warning: ML model inference failed ({e}), falling back to heuristics.")
                composite_ai_score = heuristic_ai_score
        else:
            composite_ai_score = heuristic_ai_score

        composite_ai_score = float(np.clip(composite_ai_score, 0.0, 1.0))

        # 5. Verdict Classification
        if composite_ai_score >= 0.52:
            verdict = "AI_GENERATED"
            confidence_level = "High" if composite_ai_score >= 0.70 else "Moderate"
            ml_note = f" (ML Model Probability: {int(ml_model_info['ml_ai_probability'] * 100)}%)" if ml_model_info["is_custom_model_active"] else ""
            summary_explanation = (
                f"Video exhibits strong mathematical indicators of synthetic AI generation (Confidence: {int(composite_ai_score * 100)}%{ml_note}). "
                f"Spectral analysis detected {int(comb_spectral * 100)}% anomalous frequency patterns, accompanied by {int(comb_temporal * 100)}% temporal warping."
            )
        elif composite_ai_score >= 0.38:
            verdict = "SUSPICIOUS"
            confidence_level = "Moderate"
            summary_explanation = (
                f"Video contains inconclusive or mixed signals (Anomaly Index: {int(composite_ai_score * 100)}%). "
                f"Certain segments exhibit synthetic-like frequency distribution or compression jitter, but natural sensor patterns remain."
            )
        else:
            verdict = "AUTHENTIC"
            confidence_level = "High" if composite_ai_score <= 0.25 else "Moderate"
            ml_note = f" (ML Model Authenticity: {int((1.0 - ml_model_info['ml_ai_probability']) * 100)}%)" if ml_model_info["is_custom_model_active"] else ""
            summary_explanation = (
                f"Video exhibits natural photographic camera characteristics (Authenticity: {int((1.0 - composite_ai_score) * 100)}%{ml_note}). "
                f"Frequency decay aligns with natural 1/f laws, optical flow conforms to rigid physical motion, and authentic camera sensor noise is present."
            )

        # 6. Optional Multimodal Vision Inspection (Gemini Flash)
        semantic_reasoning = None
        if gemini_api_key or os.environ.get("GEMINI_API_KEY"):
            # Select top anomaly frames
            sorted_frames = sorted(frame_results, key=lambda x: x["anomaly_score"], reverse=True)
            top_indices = [x["index"] for x in sorted_frames[:3]]
            anomaly_images = [sampled_frames[i]["image"] for i in top_indices]
            anomaly_times = [sampled_frames[i]["timestamp_sec"] for i in top_indices]

            semantic_reasoning = SemanticVisionInspector.inspect_anomaly_frames(
                frames=anomaly_images,
                timestamps=anomaly_times,
                api_key=gemini_api_key
            )

        # 7. Package Complete Analysis Result
        result = {
            "analysis_id": analysis_id,
            "verdict": verdict,
            "composite_ai_score": round(composite_ai_score, 3),
            "confidence_level": confidence_level,
            "detection_method": "TRAINED_ML_ENSEMBLE" if ml_model_info["is_custom_model_active"] else "VISUAL_HEURISTICS",
            "visual_scan_bypassed": False,
            "ml_model": ml_model_info,
            "c2pa_provenance": {
                "has_c2pa": c2pa_result.has_c2pa,
                "is_ai_generated": c2pa_result.is_ai_generated,
                "issuer": c2pa_result.issuer,
                "claim_generator": c2pa_result.claim_generator,
                "digital_source_type": c2pa_result.digital_source_type,
                "software_agent": c2pa_result.software_agent,
                "matched_reason": c2pa_result.matched_reason
            },
            "summary_explanation": summary_explanation,
            "semantic_reasoning": semantic_reasoning,
            "video_metadata": metadata,
            "metrics": {
                "spectral": {
                    "score": round(comb_spectral, 3),
                    "status": "HIGH ANOMALY" if comb_spectral >= 0.60 else ("MODERATE" if comb_spectral >= 0.40 else "NORMAL"),
                    "description": "2D Fast Fourier Transform high-frequency periodic grid artifacts and power spectrum decay profile."
                },
                "temporal": {
                    "score": round(comb_temporal, 3),
                    "status": "HIGH JITTER" if comb_temporal >= 0.60 else ("MODERATE" if comb_temporal >= 0.40 else "CONSISTENT"),
                    "description": "Farneback dense optical flow vector curl, warp residual, and inter-frame texture drift."
                },
                "noise_residual": {
                    "score": round(comb_noise, 3),
                    "status": "SYNTHETIC" if comb_noise >= 0.60 else ("IRREGULAR" if comb_noise >= 0.40 else "AUTHENTIC"),
                    "description": "Photo Response Non-Uniformity (PRNU) sensor shot noise vs synthetic artificial over-smoothing."
                },
                "facial": {
                    "score": round(avg_facial, 3),
                    "status": "DEEPFAKE DETECTED" if avg_facial >= 0.55 else ("BLENDING ANOMALY" if avg_facial >= 0.35 else ("NATURAL" if faces_detected_count > 0 else "NO FACE")),
                    "faces_detected": faces_detected_count,
                    "description": "Facial boundary blending seam discontinuities, skin micro-texture, and bilateral facial symmetry."
                }
            },
            "frames": frame_results
        }

        return result
