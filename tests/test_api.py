import os
import sys
import time
import threading
import requests
import uvicorn

backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, backend_dir)

from main import app

class ServerThread(threading.Thread):
    def __init__(self, app, host="127.0.0.1", port=8765):
        super().__init__(daemon=True)
        self.server = uvicorn.Server(uvicorn.Config(app, host=host, port=port, log_level="warning"))

    def run(self):
        self.server.run()

    def stop(self):
        self.server.should_exit = True

def test_web_and_api():
    port = 8765
    base_url = f"http://127.0.0.1:{port}"
    server_thread = ServerThread(app, port=port)
    server_thread.start()

    # Wait for server to boot
    for _ in range(20):
        try:
            r = requests.get(f"{base_url}/")
            if r.status_code == 200:
                break
        except Exception:
            time.sleep(0.2)

    try:
        print("\n--- 1. Testing GET / (Index page) ---")
        res = requests.get(f"{base_url}/")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        assert "VeritasVideo" in res.text, "Index HTML must contain VeritasVideo branding"
        print("[OK] Index HTML served correctly.")

        print("\n--- 1b. Testing GET /health (Render Health Check) ---")
        res_health = requests.get(f"{base_url}/health")
        assert res_health.status_code == 200, f"Expected 200, got {res_health.status_code}"
        health_data = res_health.json()
        assert health_data.get("status") == "healthy"
        print("[OK] Health check endpoint passed.")

        print("\n--- 2. Testing Sample Video Endpoints ---")
        res_real = requests.get(f"{base_url}/api/sample-video/real")
        assert res_real.status_code == 200, f"Expected 200, got {res_real.status_code}"
        assert "video/mp4" in res_real.headers.get("content-type", "")
        print(f"[OK] Real sample video served ({len(res_real.content)} bytes).")

        res_ai = requests.get(f"{base_url}/api/sample-video/ai")
        assert res_ai.status_code == 200, f"Expected 200, got {res_ai.status_code}"
        assert "video/mp4" in res_ai.headers.get("content-type", "")
        print(f"[OK] AI sample video served ({len(res_ai.content)} bytes).")

        res_c2pa = requests.get(f"{base_url}/api/sample-video/c2pa")
        assert res_c2pa.status_code == 200, f"Expected 200, got {res_c2pa.status_code}"
        assert "video/mp4" in res_c2pa.headers.get("content-type", "")
        print(f"[OK] C2PA sample video served ({len(res_c2pa.content)} bytes).")

        print("\n--- 3. Testing POST /api/analyze with C2PA fast-path bypass ---")
        samples_dir = os.path.join(os.path.dirname(__file__), "..", "samples")
        c2pa_file = os.path.join(samples_dir, "c2pa_ai_sample.mp4")
        with open(c2pa_file, "rb") as f:
            resp_c2pa = requests.post(
                f"{base_url}/api/analyze",
                files={"file": ("c2pa_ai_sample.mp4", f, "video/mp4")}
            )
        assert resp_c2pa.status_code == 200
        d_c2pa = resp_c2pa.json()
        assert d_c2pa["verdict"] == "AI_GENERATED"
        assert d_c2pa["detection_method"] == "C2PA_CONTENT_CREDENTIALS"
        assert d_c2pa["visual_scan_bypassed"] is True
        print(f"[OK] C2PA Fast-path bypass verified: {d_c2pa['summary_explanation'][:60]}...")

        print("\n--- 4. Testing POST /api/analyze with visual heuristic scan ---")
        sample_file = os.path.join(samples_dir, "synthetic_diffusion_sample.mp4")
        
        with open(sample_file, "rb") as f:
            response = requests.post(
                f"{base_url}/api/analyze",
                files={"file": ("synthetic_diffusion_sample.mp4", f, "video/mp4")},
                data={"sample_count": "4"}
            )

        assert response.status_code == 200, f"Analysis failed: {response.text}"
        data = response.json()
        assert "analysis_id" in data, "Response must include analysis_id"
        assert "verdict" in data, "Response must include verdict"
        assert "metrics" in data, "Response must include metrics"
        assert len(data["frames"]) == 4, f"Expected 4 frames, got {len(data['frames'])}"
        print(f"[OK] Video analyzed successfully: Verdict={data['verdict']}, Score={data['composite_ai_score']}")

        analysis_id = data["analysis_id"]
        print(f"\n--- 4. Testing Frame Visual Heatmap Endpoints (ID: {analysis_id}) ---")
        for filter_type in ["original", "fft", "noise", "flow"]:
            vis_res = requests.get(f"{base_url}/api/frame-visual/{analysis_id}/0/{filter_type}")
            assert vis_res.status_code == 200, f"Failed for filter {filter_type}: status {vis_res.status_code}"
            assert "image/jpeg" in vis_res.headers.get("content-type", "")
            print("[OK] Filter visual")

        print("\n[ALL API AND WEB TESTS PASSED SUCCESSFULLY!]")

    finally:
        server_thread.stop()

if __name__ == "__main__":
    test_web_and_api()
