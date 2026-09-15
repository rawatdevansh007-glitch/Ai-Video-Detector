import os
import json
import mimetypes
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

# Try importing c2pa, with graceful fallback if native library is not yet loaded
try:
    import c2pa
except ImportError:
    c2pa = None

@dataclass
class C2PACheckResult:
    has_c2pa: bool
    is_ai_generated: bool
    issuer: Optional[str] = None
    claim_generator: Optional[str] = None
    digital_source_type: Optional[str] = None
    software_agent: Optional[str] = None
    matched_reason: Optional[str] = None
    raw_manifest: Optional[Dict[str, Any]] = None

class C2PAChecker:
    """
    Reads C2PA (Content Authenticity Initiative) manifests from media files.
    Identifies if Content Credentials originate from an AI generator (e.g. Google, OpenAI, etc.)
    or indicate trained algorithmic media (IPTC digitalSourceType).
    """

    # Known AI generator keywords in issuer, claim generator, or software agent
    AI_ORGANIZATIONS = [
        "openai",
        "google",
        "google llc",
        "google trust services",
        "google deepmind",
        "synthid",
        "sora",
        "veo",
        "imagen",
        "dall-e",
        "chatgpt",
        "midjourney",
        "stability ai",
        "stable diffusion",
        "stable video",
        "runway",
        "pika",
        "luma",
        "kling",
        "firefly"
    ]

    # IPTC Digital Source Types for generative AI
    AI_DIGITAL_SOURCE_TYPES = [
        "trainedalgorithmicmedia",
        "compositesynthetic",
        "algorithmicmedia",
        "virtualrecording"
    ]

    @classmethod
    def get_mime_type(cls, file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        mime_map = {
            ".mp4": "video/mp4",
            ".mov": "video/quicktime",
            ".qt": "video/quicktime",
            ".webm": "video/webm",
            ".avi": "video/x-msvideo",
            ".mkv": "video/x-matroska",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png"
        }
        return mime_map.get(ext, "video/mp4")

    @classmethod
    def check_video(cls, video_path: str) -> C2PACheckResult:
        """
        Inspects the video file for a C2PA manifest.
        If present, inspects signature issuer, claim generator, and assertions.
        """
        if not os.path.exists(video_path):
            return C2PACheckResult(has_c2pa=False, is_ai_generated=False)

        manifest_data = cls._read_manifest_json(video_path)
        if not manifest_data:
            return C2PACheckResult(has_c2pa=False, is_ai_generated=False)

        return cls.evaluate_manifest(manifest_data)

    @classmethod
    def _read_manifest_json(cls, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Extracts raw manifest dictionary using c2pa-python reader,
        or from an accompanying sidecar manifest JSON if present.
        """
        # 1. First attempt: Read embedded C2PA manifest via c2pa-python
        if c2pa is not None:
            mime_type = cls.get_mime_type(file_path)
            try:
                with open(file_path, "rb") as f:
                    with c2pa.Reader(mime_type, f) as reader:
                        manifest_str = reader.json()
                        if manifest_str:
                            return json.loads(manifest_str)
            except Exception:
                pass

        # 2. Second attempt: Check for accompanying sidecar C2PA manifest JSON
        base_name = os.path.basename(file_path).replace("upload_", "")
        samples_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "samples"))

        sidecar_candidates = [
            f"{file_path}.c2pa.json",
            f"{file_path}.json",
            os.path.splitext(file_path)[0] + ".c2pa.json",
            os.path.join(samples_dir, f"{base_name}.c2pa.json"),
            os.path.join(samples_dir, f"{os.path.splitext(base_name)[0]}.c2pa.json")
        ]
        for candidate in sidecar_candidates:
            if os.path.exists(candidate):
                try:
                    with open(candidate, "r", encoding="utf-8") as sc_file:
                        return json.load(sc_file)
                except Exception:
                    pass

        return None

    @classmethod
    def evaluate_manifest(cls, manifest_data: Dict[str, Any]) -> C2PACheckResult:
        """
        Evaluates parsed C2PA manifest store data for AI generation indicators.
        """
        # Find active manifest or iterate through manifests
        manifests = manifest_data.get("manifests", {})
        active_label = manifest_data.get("active_manifest")
        
        target_manifest = manifests.get(active_label) if active_label else None
        if not target_manifest and manifests:
            target_manifest = next(iter(manifests.values()))

        if not target_manifest:
            # Fallback if manifest dictionary is flat
            target_manifest = manifest_data

        # 1. Inspect Signature Issuer
        sig_info = target_manifest.get("signature_info", {})
        issuer = sig_info.get("issuer") or ""
        issuer_clean = issuer.lower().strip()

        # 2. Inspect Claim Generator
        claim_gen = target_manifest.get("claim_generator") or ""
        claim_gen_clean = claim_gen.lower().strip()

        # Check claim generator info list if present
        claim_gen_info = target_manifest.get("claim_generator_info", [])
        for cgi in claim_gen_info:
            if isinstance(cgi, dict) and "name" in cgi:
                claim_gen_clean += " " + cgi["name"].lower()

        # 3. Inspect Assertions (c2pa.actions and digitalSourceType)
        digital_source_type = None
        software_agent = None

        assertions = target_manifest.get("assertions", [])
        for assertion in assertions:
            label = assertion.get("label", "")
            data = assertion.get("data", {})

            if "actions" in label or "actions" in data:
                actions_list = data.get("actions", [])
                for action in actions_list:
                    dst = action.get("digitalSourceType")
                    if dst:
                        digital_source_type = dst
                    sa = action.get("softwareAgent")
                    if sa:
                        software_agent = sa

        # 4. Determine if AI Generator
        # A) Match known AI issuers / organizations
        matched_ai_org = None
        for org in cls.AI_ORGANIZATIONS:
            if org in issuer_clean:
                matched_ai_org = f"AI Issuer '{issuer}'"
                break
            if org in claim_gen_clean:
                matched_ai_org = f"AI Claim Generator '{claim_gen}'"
                break
            if software_agent and org in software_agent.lower():
                matched_ai_org = f"AI Software Agent '{software_agent}'"
                break

        # B) Match IPTC Digital Source Type (trainedAlgorithmicMedia)
        matched_dst = None
        if digital_source_type:
            dst_clean = digital_source_type.lower()
            for ai_dst in cls.AI_DIGITAL_SOURCE_TYPES:
                if ai_dst in dst_clean:
                    matched_dst = f"IPTC Digital Source '{digital_source_type}'"
                    break

        # Final decision
        is_ai = bool(matched_ai_org or matched_dst)
        reason_parts = [r for r in [matched_ai_org, matched_dst] if r]
        matched_reason = " & ".join(reason_parts) if reason_parts else None

        return C2PACheckResult(
            has_c2pa=True,
            is_ai_generated=is_ai,
            issuer=issuer or None,
            claim_generator=claim_gen or None,
            digital_source_type=digital_source_type,
            software_agent=software_agent,
            matched_reason=matched_reason,
            raw_manifest=manifest_data
        )
