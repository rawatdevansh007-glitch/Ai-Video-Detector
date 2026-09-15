import os
import cv2
import numpy as np
from typing import Dict, Any, Tuple, List, Optional
from .cnn_detector import PyTorchResNet50Detector

class FacialSeamDetector:
    """
    Facial & Boundary Seam Detection with PyTorch ResNet-50 Deep Learning
    and Multi-Face Array Handling.
    Analyzes multiple subjects per frame, runs independent ResNet-50 inference
    on all detected face crops, and performs max-pooling across faces.
    """

    def __init__(self, cnn_detector: Optional[PyTorchResNet50Detector] = None):
        # Load OpenCV Haar Cascade for face detection
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        self.cnn_detector = cnn_detector if cnn_detector is not None else PyTorchResNet50Detector()

    def extract_faces(
        self,
        image: np.ndarray,
        frame_idx: Optional[int] = None,
        save_dir: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Detects and extracts an array of cropped faces from a frame.
        Optionally saves each face crop as frame_{idx}_face_{face_idx}.jpg.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        h_img, w_img = image.shape[:2]

        # Detect multiple frontal faces
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=4, minSize=(60, 60)
        )

        face_items = []
        if len(faces) == 0:
            return face_items

        for face_idx, (x, y, w, h) in enumerate(faces):
            # Crop with boundary padding
            pad_x = int(w * 0.15)
            pad_y = int(h * 0.15)
            x1 = max(0, x - pad_x)
            y1 = max(0, y - pad_y)
            x2 = min(w_img, x + w + pad_x)
            y2 = min(h_img, y + h + pad_y)

            face_crop = image[y1:y2, x1:x2].copy()
            face_roi_gray = gray[y:y+h, x:x+w]
            outer_roi_gray = gray[y1:y2, x1:x2]

            saved_paths = []
            if save_dir:
                os.makedirs(save_dir, exist_ok=True)
                f_idx_str = str(frame_idx) if frame_idx is not None else "0"
                # Save standard format
                p1 = os.path.join(save_dir, f"frame_{f_idx_str}_face_{face_idx}.jpg")
                cv2.imwrite(p1, face_crop)
                saved_paths.append(p1)
                
                # If frame_idx is int, also save 2-digit padded format e.g. frame_01_face_0.jpg
                if isinstance(frame_idx, int):
                    p2 = os.path.join(save_dir, f"frame_{frame_idx:02d}_face_{face_idx}.jpg")
                    cv2.imwrite(p2, face_crop)
                    saved_paths.append(p2)

            face_items.append({
                "face_idx": face_idx,
                "bbox": [int(x), int(y), int(w), int(h)],
                "crop": face_crop,
                "face_roi_gray": face_roi_gray,
                "outer_roi_gray": outer_roi_gray,
                "saved_paths": saved_paths
            })

        return face_items

    def analyze_frame(
        self,
        image: np.ndarray,
        frame_idx: Optional[int] = None,
        save_dir: Optional[str] = None
    ) -> Tuple[float, Dict[str, Any], np.ndarray, bool]:
        """
        Analyzes facial regions in the frame across multiple subjects.
        Performs PyTorch inference on all detected faces independently and
        computes final facial anomaly score using MAX-POOLING over all faces.
        Returns:
            (max_face_anomaly [0.0 - 1.0], details_dict, visual_annotated_bgr, has_face)
        """
        annotated = image.copy()
        face_items = self.extract_faces(image, frame_idx=frame_idx, save_dir=save_dir)

        if len(face_items) == 0:
            return 0.0, {"face_detected": False, "face_count": 0, "faces": [], "score": 0.0}, annotated, False

        # Extract all crops and run PyTorch ResNet-50 inference independently
        crops = [item["crop"] for item in face_items]
        cnn_scores = self.cnn_detector.predict_face_array(crops)

        face_details = []
        face_scores = []

        for item, cnn_score in zip(face_items, cnn_scores):
            x, y, w, h = item["bbox"]
            face_roi = item["face_roi_gray"]
            outer_roi = item["outer_roi_gray"]

            # 1. Edge Seam Discontinuity at Boundary
            edges = cv2.Canny(outer_roi, 50, 150)
            perimeter_mask = np.zeros_like(outer_roi, dtype=np.uint8)
            center = (outer_roi.shape[1] // 2, outer_roi.shape[0] // 2)
            axes = (int(w * 0.5), int(h * 0.5))
            cv2.ellipse(perimeter_mask, center, axes, 0, 0, 360, 255, thickness=int(w * 0.1))
            seam_edges = cv2.bitwise_and(edges, edges, mask=perimeter_mask)
            seam_density = np.sum(seam_edges > 0) / max(np.sum(perimeter_mask > 0), 1)

            # 2. Skin Texture Micro-smoothness
            face_laplacian_var = cv2.Laplacian(face_roi, cv2.CV_64F).var()
            bg_laplacian_var = cv2.Laplacian(outer_roi, cv2.CV_64F).var()
            texture_ratio = face_laplacian_var / max(bg_laplacian_var, 1e-4)
            texture_anomaly = np.clip((0.85 - texture_ratio) / 0.85, 0.0, 1.0) if texture_ratio < 0.85 else 0.0

            # 3. Bilateral Facial Symmetry
            half_w = w // 2
            left_half = face_roi[:, :half_w]
            right_half = cv2.flip(face_roi[:, w - half_w:], 1)
            if left_half.shape == right_half.shape:
                diff = cv2.absdiff(left_half, right_half)
                symmetry_asymmetry = np.mean(diff) / 255.0
            else:
                symmetry_asymmetry = 0.2

            asymmetry_score = float(np.clip((symmetry_asymmetry - 0.15) / 0.25, 0.0, 1.0))
            seam_score = float(np.clip((seam_density - 0.08) / 0.20, 0.0, 1.0))

            heuristic_score = float(np.clip(
                0.40 * seam_score + 0.35 * texture_anomaly + 0.25 * asymmetry_score,
                0.0, 1.0
            ))

            # Blend PyTorch Deep Learning prediction with Forensic Boundary Analysis
            # Max/Blend of deep representation & boundary artifact
            face_anomaly = float(np.clip(
                0.50 * cnn_score + 0.50 * heuristic_score,
                0.0, 1.0
            ))

            face_scores.append(face_anomaly)

            face_details.append({
                "face_idx": item["face_idx"],
                "bbox": [int(x), int(y), int(w), int(h)],
                "cnn_score": round(float(cnn_score), 3),
                "seam_score": round(float(seam_score), 3),
                "texture_anomaly": round(float(texture_anomaly), 3),
                "asymmetry_score": round(float(asymmetry_score), 3),
                "heuristic_score": round(float(heuristic_score), 3),
                "score": round(float(face_anomaly), 3),
                "saved_paths": item["saved_paths"]
            })

            # Draw visual bounding box & indicator on annotated image
            color = (0, 0, 255) if face_anomaly >= 0.55 else ((0, 165, 255) if face_anomaly >= 0.35 else (0, 255, 0))
            cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
            label = f"Face #{item['face_idx']}: {int(face_anomaly * 100)}%"
            cv2.putText(annotated, label, (x, max(20, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)

        # Requirement 3: MAX-POOLING across all detected faces in the frame
        final_frame_face_score = float(max(face_scores)) if face_scores else 0.0

        details = {
            "face_detected": True,
            "face_count": len(face_items),
            "faces": face_details,
            "pooling_method": "max_pooling",
            "score": round(final_frame_face_score, 3)
        }

        return final_frame_face_score, details, annotated, True
