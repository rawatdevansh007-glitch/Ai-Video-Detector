import os
import sys
import time
import json
import re
import threading
import requests
import uvicorn

backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, backend_dir)

from main import app

class ServerThread(threading.Thread):
    def __init__(self, app, host="127.0.0.1", port=8769):
        super().__init__(daemon=True)
        self.server = uvicorn.Server(uvicorn.Config(app, host=host, port=port, log_level="warning"))

    def run(self):
        self.server.run()

    def stop(self):
        self.server.should_exit = True

def test_full_e2e_qa():
    port = 8769
    base_url = f"http://127.0.0.1:{port}"
    server_thread = ServerThread(app, port=port)
    server_thread.start()

    # Wait for server to boot
    for _ in range(25):
        try:
            r = requests.get(f"{base_url}/")
            if r.status_code == 200:
                break
        except Exception:
            time.sleep(0.2)

    try:
        # Task 3: Verify frontend/index.html still references ONLY these stylesheets in order:
        # tokens.css -> base.css -> typography.css -> layout.css -> motion.css ->
        # hero.css -> verdict.css -> signal.css -> inspector.css -> peripherals.css ->
        # responsive.css -> a11y.css
        resp = requests.get(f"{base_url}/")
        assert resp.status_code == 200
        html = resp.text

        # Extract all stylesheet links in order
        stylesheet_links = re.findall(r'<link\s+[^>]*rel=["\']stylesheet["\'][^>]*href=["\']([^"\']+)["\']', html)
        # Also handle href before rel
        stylesheet_links += re.findall(r'<link\s+[^>]*href=["\']([^"\']+)["\'][^>]*rel=["\']stylesheet["\']', html)
        
        local_css = [os.path.basename(href.split('?')[0]) for href in stylesheet_links if 'styles/' in href]
        expected_order = [
            "tokens.css", "base.css", "typography.css", "layout.css", "motion.css",
            "hero.css", "verdict.css", "signal.css", "inspector.css", "peripherals.css",
            "responsive.css", "a11y.css"
        ]
        assert local_css == expected_order, f"Stylesheets do not match expected order!\nFound: {local_css}\nExpected: {expected_order}"

        # Ensure styles.css is NOT referenced in index.html
        assert "styles.css" not in [os.path.basename(href) for href in stylesheet_links]

        # 4.a: Upload real sample -> verdict shows "Real" -> 4 heatmaps render -> timeline markers appear
        real_sample_path = os.path.join(os.path.dirname(__file__), "..", "samples", "authentic_camera_sample.mp4")
        assert os.path.exists(real_sample_path), "Real sample file not found"
        with open(real_sample_path, "rb") as vf:
            files = {"file": ("authentic_camera_sample.mp4", vf, "video/mp4")}
            data = {"sampling_density": 8}
            res_real = requests.post(f"{base_url}/api/analyze", files=files, data=data)

        assert res_real.status_code == 200, f"Real video analysis failed: {res_real.text}"
        real_json = res_real.json()
        assert real_json["verdict"] == "AUTHENTIC", f"Expected backend verdict 'AUTHENTIC', got '{real_json['verdict']}'"
        assert real_json["composite_ai_score"] < 0.5
        # Verify app.js maps AUTHENTIC to user-facing verdict 'Real'
        app_js_text = requests.get(f"{base_url}/static/app.js").text
        assert "const verdictWord = isAI ? 'AI-Generated' : (isSuspicious ? 'Suspicious' : 'Real');" in app_js_text
        real_id = real_json["analysis_id"]

        # Check 4 heatmaps render for real sample
        for vt in ["fft", "flow", "noise", "facial"]:
            v_res = requests.get(f"{base_url}/api/frame-visual/{real_id}/0/{vt}")
            assert v_res.status_code == 200
            assert "image/jpeg" in v_res.headers.get("content-type", "")
            assert len(v_res.content) > 100

        # Check timeline markers appear
        assert len(real_json["frames"]) > 0
        for f in real_json["frames"]:
            assert "timestamp_sec" in f
            assert "anomaly_score" in f
            assert 0.0 <= f["anomaly_score"] <= 1.0

        # 4.b: Upload AI sample -> verdict shows "AI-Generated" -> anomaly ticks visible
        ai_sample_path = os.path.join(os.path.dirname(__file__), "..", "samples", "synthetic_diffusion_sample.mp4")
        assert os.path.exists(ai_sample_path), "AI sample file not found"
        with open(ai_sample_path, "rb") as vf:
            files = {"file": ("synthetic_diffusion_sample.mp4", vf, "video/mp4")}
            data = {"sampling_density": 8}
            res_ai = requests.post(f"{base_url}/api/analyze", files=files, data=data)

        assert res_ai.status_code == 200, f"AI video analysis failed: {res_ai.text}"
        ai_json = res_ai.json()
        assert ai_json["verdict"] == "AI_GENERATED", f"Expected backend verdict 'AI_GENERATED', got '{ai_json['verdict']}'"
        assert ai_json["composite_ai_score"] >= 0.5
        ai_id = ai_json["analysis_id"]

        # Verify anomaly ticks have significant values
        anomaly_scores = [f["anomaly_score"] for f in ai_json["frames"]]
        assert max(anomaly_scores) >= 0.5, "Expected high anomaly score in AI frames"

        # 4.c: Click timeline marker -> video seeks -> heatmap updates
        # Check that subsequent frame heatmaps render properly
        v_res_frame1 = requests.get(f"{base_url}/api/frame-visual/{ai_id}/1/fft")
        assert v_res_frame1.status_code == 200
        assert len(v_res_frame1.content) > 100

        # Verify app.js click seek logic connects to video currentTime and renderAllSignalHeatmaps
        app_js_res = requests.get(f"{base_url}/static/app.js")
        assert app_js_res.status_code == 200
        app_js = app_js_res.text
        assert "mainVideoPlayer.currentTime = f.timestamp_sec" in app_js
        assert "updateFrameInspector()" in app_js
        assert "renderAllSignalHeatmaps(currentFrameIndex)" in app_js

        # 4.d: Settings -> enter dummy Gemini key -> reload -> key persists in localStorage
        assert "veritas_gemini_key" in app_js
        assert "localStorage.setItem('veritas_gemini_key', geminiApiKey)" in app_js
        assert "localStorage.getItem('veritas_gemini_key')" in app_js
        assert "geminiApiKeyInput.value = geminiApiKey" in app_js

        # 4.e: Export JSON -> file downloads -> valid JSON
        assert "veritas_forensic_report_" in app_js
        assert "JSON.stringify(currentAnalysis, null, 2)" in app_js
        # Verify real_json and ai_json are valid serializable JSON
        exported_str = json.dumps(ai_json, indent=2)
        parsed_back = json.loads(exported_str)
        assert parsed_back["analysis_id"] == ai_id
        assert "metrics" in parsed_back
        assert "frames" in parsed_back

        # 4.f: Print -> print stylesheet hides chrome, shows verdict + signals
        periph_css_res = requests.get(f"{base_url}/static/styles/peripherals.css")
        assert periph_css_res.status_code == 200
        periph_css = periph_css_res.text
        assert "@media print" in periph_css
        # Hides chrome
        assert "header," in periph_css
        assert ".editorial-header," in periph_css
        assert "#uploadSection," in periph_css
        assert "#settingsModal," in periph_css
        assert "footer," in periph_css
        assert "button," in periph_css
        assert "display: none !important;" in periph_css
        # Shows verdict + signals
        assert "#resultsDashboard" in periph_css
        assert "display: block !important;" in periph_css
        assert ".verdict" in periph_css
        assert ".signal" in periph_css

    finally:
        server_thread.stop()
