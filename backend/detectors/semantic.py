import os
import io
import cv2
import numpy as np
from PIL import Image
from typing import Optional, List

class SemanticVisionInspector:
    """
    Optional Multimodal Vision Forensic Inspector using Gemini Flash.
    Provides semantic forensic reasoning on suspicious frames (e.g. lighting direction,
    physics violations, morphing limbs, distorted hands/teeth, floating artifacts).
    """

    @staticmethod
    def inspect_anomaly_frames(
        frames: List[np.ndarray],
        timestamps: List[float],
        api_key: Optional[str] = None
    ) -> Optional[str]:
        """
        Sends sampled anomaly frames to Gemini Flash for semantic forensic evaluation.
        """
        key = api_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            return None

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=key)

            # Convert up to 3 frames to PIL Images
            pil_images = []
            frame_notes = []
            for i, (frame, t) in enumerate(zip(frames[:3], timestamps[:3])):
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb)
                pil_images.append(pil_img)
                frame_notes.append(f"Frame {i+1} (at {t:.1f}s)")

            prompt = (
                "You are an expert digital media forensic investigator. "
                "Inspect the provided video frames carefully for signs of synthetic AI generation (diffusion/Sora/Kling/Runway artifacts) or deepfake manipulation.\n\n"
                "Look for:\n"
                "1. Anatomical / physical impossibilities: unnatural hand/finger geometry, irregular teeth, morphing structures.\n"
                "2. Lighting & shadow discrepancies: conflicting light sources, missing or impossible reflections, unnatural specular highlights.\n"
                "3. Texture & background artifacts: uncanny smooth skin without pores, warped straight lines, drifting textures.\n\n"
                "Provide a concise, 2-3 paragraph forensic assessment detailing your findings and a qualitative verdict on whether this footage exhibits synthetic or authentic physical traits."
            )

            contents = [prompt] + pil_images

            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=contents,
            )

            return response.text if response and response.text else None

        except Exception as e:
            print(f"[SemanticVisionInspector] Notice: Gemini analysis skipped ({str(e)})")
            return None
