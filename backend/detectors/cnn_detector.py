import cv2
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import numpy as np
from typing import List, Dict, Any, Optional

class PyTorchResNet50Detector:
    """
    PyTorch ResNet-50 Deep Learning Classifier for Facial Deepfake Detection.
    Replaces model.fc with a single probability output via Sigmoid activation.
    Evaluates individual face crops extracted from video frames.
    """
    ARCHITECTURE_NAME = "PyTorch ResNet-50 (Cross-Verified)"

    def __init__(self, device: str = "cpu"):
        self.device = torch.device(device if torch.cuda.is_available() and device == "cuda" else "cpu")
        
        # Initialize ResNet-50 model
        self.model = models.resnet50(weights=None)
        in_features = self.model.fc.in_features  # 2048
        
        # Modify the final fully connected layer to output a single probability score via Sigmoid
        self.model.fc = nn.Sequential(
            nn.Linear(in_features, 1),
            nn.Sigmoid()
        )
        
        # Initialize with sensible weights so baseline unperturbed output is stable
        with torch.no_grad():
            nn.init.xavier_uniform_(self.model.fc[0].weight, gain=0.1)
            nn.init.constant_(self.model.fc[0].bias, -1.0)
            
        self.model.to(self.device)
        self.model.eval()

        # ImageNet standardization transforms
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])

    def predict_face(self, face_bgr: np.ndarray) -> float:
        """
        Runs inference on a single BGR face crop.
        Returns a single probability score in [0.0, 1.0].
        """
        if face_bgr is None or face_bgr.size == 0:
            return 0.0

        if len(face_bgr.shape) == 3:
            rgb = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2RGB)
        else:
            rgb = cv2.cvtColor(face_bgr, cv2.COLOR_GRAY2RGB)

        pil_img = Image.fromarray(rgb)
        tensor = self.transform(pil_img).unsqueeze(0).to(self.device)

        with torch.no_grad():
            output = self.model(tensor)
            prob = float(output.item())

        return float(np.clip(prob, 0.0, 1.0))

    def predict_face_array(self, face_crops: List[np.ndarray]) -> List[float]:
        """
        Runs PyTorch inference on an array of detected faces independently.
        Returns list of probability scores in [0.0, 1.0].
        """
        if not face_crops:
            return []

        scores = []
        for crop in face_crops:
            scores.append(self.predict_face(crop))
        return scores
