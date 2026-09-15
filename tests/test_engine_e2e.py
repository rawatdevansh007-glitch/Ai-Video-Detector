import os
import sys

backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, backend_dir)

from engine import ForensicEngine

def test_engine():
    samples_dir = os.path.join(os.path.dirname(__file__), "..", "samples")
    cache_dir = os.path.join(os.path.dirname(__file__), "..", "cache")
    
    real_video = os.path.join(samples_dir, "authentic_camera_sample.mp4")
    ai_video = os.path.join(samples_dir, "synthetic_diffusion_sample.mp4")

    engine = ForensicEngine(cache_dir=cache_dir)

    print("\n--- 1. Testing Authentic Camera Video ---")
    res_real = engine.analyze_video(real_video, sample_count=8, use_custom_model=False)
    print(f"Verdict: {res_real['verdict']}")
    print(f"Composite AI Score: {res_real['composite_ai_score']}")
    print(f"Spectral Score: {res_real['metrics']['spectral']['score']}")
    print(f"Temporal Score: {res_real['metrics']['temporal']['score']}")
    print(f"Noise Residual Score: {res_real['metrics']['noise_residual']['score']}")
    print(f"Explanation: {res_real['summary_explanation']}")

    print("\n--- 2. Testing Synthetic AI Video ---")
    res_ai = engine.analyze_video(ai_video, sample_count=8, use_custom_model=False)
    print(f"Verdict: {res_ai['verdict']}")
    print(f"Composite AI Score: {res_ai['composite_ai_score']}")
    print(f"Spectral Score: {res_ai['metrics']['spectral']['score']}")
    print(f"Temporal Score: {res_ai['metrics']['temporal']['score']}")
    print(f"Noise Residual Score: {res_ai['metrics']['noise_residual']['score']}")
    print(f"Explanation: {res_ai['summary_explanation']}")

    assert res_real['verdict'] == "AUTHENTIC", f"Expected AUTHENTIC, got {res_real['verdict']}"
    assert res_ai['verdict'] == "AI_GENERATED", f"Expected AI_GENERATED, got {res_ai['verdict']}"
    assert res_ai['composite_ai_score'] > res_real['composite_ai_score'], "AI score must be higher than Real score"

    print("\n[SUCCESS] End-to-End Forensic Engine validation PASSED!")

if __name__ == "__main__":
    test_engine()
