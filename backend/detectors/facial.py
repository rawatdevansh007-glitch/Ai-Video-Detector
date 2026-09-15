import cv2
import numpy as np
from typing import Dict, Any, Tuple

class FacialSeamDetector:
    """
    Facial & Boundary Seam Detection for Deepfakes and Face-swaps.
    Analyzes face perimeter blending boundaries, skin texture micro-smoothness,
    and bilateral symmetry across facial regions.
    """

    def __init__(self):
        # Load OpenCV Haar Cascade for face detection
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)

    def analyze_frame(self, image: np.ndarray) -> Tuple[float, Dict[str, Any], np.ndarray, bool]:
        """
        Analyzes facial regions in the frame.
        Returns:
            (anomaly_score [0.0 - 1.0], details_dict, visual_annotated_bgr, has_face)
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        annotated = image.copy()

        # Detect frontal faces
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=4, minSize=(60, 60)
        )

        if len(faces) == 0:
            return 0.0, {"face_detected": False, "score": 0.0}, annotated, False

        max_face_anomaly = 0.0
        face_details = []

        for (x, y, w, h) in faces:
            # Expand bounding box slightly to capture outer blending seam
            pad_x = int(w * 0.15)
            pad_y = int(h * 0.15)
            x1 = max(0, x - pad_x)
            y1 = max(0, y - pad_y)
            x2 = min(image.shape[1], x + w + pad_x)
            y2 = min(image.shape[0], y + h + pad_y)

            face_roi = gray[y:y+h, x:x+w]
            outer_roi = gray[y1:y2, x1:x2]

            # 1. Edge Seam Discontinuity at Boundary
            # Deepfake face swaps often produce a blurred blending perimeter
            edges = cv2.Canny(outer_roi, 50, 150)
            perimeter_mask = np.zeros_like(outer_roi, dtype=np.uint8)
            # Define an elliptical ring around the face perimeter
            center = (outer_roi.shape[1] // 2, outer_roi.shape[0] // 2)
            axes = (int(w * 0.5), int(h * 0.5))
            cv2.ellipse(perimeter_mask, center, axes, 0, 0, 360, 255, thickness=int(w * 0.1))
            
            seam_edges = cv2.bitwise_and(edges, edges, mask=perimeter_mask)
            seam_density = np.sum(seam_edges > 0) / max(np.sum(perimeter_mask > 0), 1)

            # 2. Skin Texture Micro-smoothness (Laplacian variance)
            # Artificial face swaps frequently look over-smoothed compared to background
            face_laplacian_var = cv2.Laplacian(face_roi, cv2.CV_64F).var()
            bg_laplacian_var = cv2.Laplacian(outer_roi, cv2.CV_64F).var()
            
            texture_ratio = face_laplacian_var / max(bg_laplacian_var, 1e-4)
            # Anomaly if face is unnaturally smoother than surroundings
            texture_anomaly = np.clip((0.85 - texture_ratio) / 0.85, 0.0, 1.0) if texture_ratio < 0.85 else 0.0

            # 3. Bilateral Facial Symmetry (Deepfakes often show asymmetric eye/mouth distortion)
            half_w = w // 2
            left_half = face_roi[:, :half_w]
            right_half = cv2.flip(face_roi[:, w - half_w:], 1)
            
            if left_half.shape == right_half.shape:
                diff = cv2.absdiff(left_half, right_half)
                symmetry_asymmetry = np.mean(diff) / 255.0
            else:
                symmetry_asymmetry = 0.2

            asymmetry_score = np.clip((symmetry_asymmetry - 0.15) / 0.25, 0.0, 1.0)
            seam_score = np.clip((seam_density - 0.08) / 0.20, 0.0, 1.0)

            face_anomaly = float(np.clip(
                0.40 * seam_score + 0.35 * texture_anomaly + 0.25 * asymmetry_score,
                0.0, 1.0
            ))

            max_face_anomaly = max(max_face_anomaly, face_anomaly)

            face_details.append({
                "bbox": [int(x), int(y), int(w), int(h)],
                "seam_score": round(float(seam_score), 3),
                "texture_anomaly": round(float(texture_anomaly), 3),
                "asymmetry_score": round(float(asymmetry_score), 3),
                "score": round(face_anomaly, 3)
            })

            # Draw visual bounding box & indicator on annotated image
            color = (0, 0, 255) if face_anomaly >= 0.55 else ((0, 165, 255) if face_anomaly >= 0.35 else (0, 255, 0))
            cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
            
            # Label
            label = f"Face: {int(face_anomaly * 100)}% anomaly"
            cv2.putText(annotated, label, (x, max(20, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)

        details = {
            "face_detected": True,
            "face_count": len(faces),
            "faces": face_details,
            "score": round(max_face_anomaly, 3)
        }

        return max_face_anomaly, details, annotated, True
