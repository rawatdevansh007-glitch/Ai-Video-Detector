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
    def __init__(self, app, host="127.0.0.1", port=8768):
        super().__init__(daemon=True)
        self.server = uvicorn.Server(uvicorn.Config(app, host=host, port=port, log_level="warning"))

    def run(self):
        self.server.run()

    def stop(self):
        self.server.should_exit = True

def test_signals_and_heatmaps():
    port = 8768
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
        # 1. Verify index.html contains all 4 sequential signal sections
        resp = requests.get(f"{base_url}/")
        assert resp.status_code == 200
        html = resp.text

        signals = ["fft", "flow", "prnu", "face"]
        for s in signals:
            assert f'data-signal="{s}"' in html, f'Missing data-signal="{s}" in index.html'

        # 2. Verify all 4 canvas element IDs exist
        canvas_ids = ["fftCanvas", "flowCanvas", "prnuCanvas", "faceCanvas"]
        for cid in canvas_ids:
            assert f'id="{cid}"' in html, f'Missing canvas #{cid} in index.html'

        # 3. Verify Eyebrows and Headings
        assert "01 — SPECTRAL" in html
        assert "02 — OPTICAL FLOW" in html
        assert "03 — SENSOR RESIDUAL" in html
        assert "04 — BIOMETRICS" in html
        assert "Frequency domain" in html
        assert "Motion vectors" in html
        assert "Sensor noise" in html
        assert "Facial boundaries" in html

        # 4. Verify Numeric Subscores
        assert 'id="spectralScoreText"' in html
        assert 'id="temporalScoreText"' in html
        assert 'id="noiseScoreText"' in html
        assert 'id="facialScoreText"' in html

        # 5. Verify signal.css is served and contains grid & responsive tokens
        assert "/static/styles/signal.css" in html
        css_resp = requests.get(f"{base_url}/static/styles/signal.css")
        assert css_resp.status_code == 200
        css = css_resp.text
        assert "min-height: 90vh;" in css
        assert "grid-template-columns: 5fr 7fr;" in css
        assert "gap: var(--s10);" in css
        assert "padding-block: var(--s12);" in css
        assert "@media (max-width: 900px)" in css
        assert "aspect-ratio: 16 / 9;" in css

        # 6. Verify Inspector layout & Sticky Player
        assert 'class="inspector"' in html
        assert 'class="player-sticky"' in html
        assert 'id="mainVideoPlayer"' in html
        assert 'id="timelineContainer"' in html
        assert 'id="timelinePlayhead"' in html
        assert 'id="currentTimeDisplay"' in html

        # 7. Verify inspector.css is served and contains sticky & timeline rules
        assert "/static/styles/inspector.css" in html
        insp_css_resp = requests.get(f"{base_url}/static/styles/inspector.css")
        assert insp_css_resp.status_code == 200
        insp_css = insp_css_resp.text
        assert "grid-template-columns: minmax(320px, 420px) 1fr;" in insp_css
        assert "position: sticky;" in insp_css
        assert "top: var(--s6);" in insp_css
        assert "height: fit-content;" in insp_css
        assert "height: 2px;" in insp_css
        assert "width: 2px !important;" in insp_css
        assert "var(--anomaly" in insp_css
        assert "width: 1px !important;" in insp_css
        assert "var(--ink" in insp_css

        # 8. Verify Sample Buttons directly under hero drag zone
        assert 'id="sampleRealBtn"' in html
        assert 'id="sampleAIBtn"' in html
        assert 'id="sampleC2PABtn"' in html
        assert "Sample Real" in html
        assert "Sample AI-Generated" in html
        assert "Sample C2PA AI" in html
        assert "hero-samples-editorial" in html

        # 9. Verify Settings Trigger & Bone Overlay Modal
        assert 'id="settingsBtn"' in html
        assert "settings-trigger" in html
        assert 'id="settingsModal"' in html
        assert "settings-overlay" in html
        assert 'id="geminiApiKeyInput"' in html
        assert 'id="saveSettingsBtn"' in html
        assert 'id="closeSettingsBtn"' in html

        # 10. Verify Export Footer
        assert '<footer class="export" data-reveal>' in html
        assert "Take the report with you." in html
        assert "Download JSON" in html
        assert "Print summary" in html
        assert 'id="downloadReportBtn"' in html
        assert 'id="printReportBtn"' in html

        # 11. Verify peripherals.css is served and contains bone overlay + footer rules
        assert "/static/styles/peripherals.css" in html
        periph_resp = requests.get(f"{base_url}/static/styles/peripherals.css")
        assert periph_resp.status_code == 200
        periph_css = periph_resp.text
        assert "rgba(244, 241, 236, 0.98)" in periph_css  # bone at 98% opacity
        assert "position: fixed;" in periph_css
        assert "max-width: 480px;" in periph_css
        assert ".export" in periph_css
        assert "Take the report with you" not in periph_css  # CSS shouldn't hardcode text, validates rules exist

        # 12. Verify all 4 heatmaps render after video upload
        sample_path = os.path.join(os.path.dirname(__file__), "..", "samples", "synthetic_diffusion_sample.mp4")
        with open(sample_path, "rb") as vf:
            files = {"file": ("synthetic_diffusion_sample.mp4", vf, "video/mp4")}
            data = {"sampling_density": 8}
            res = requests.post(f"{base_url}/api/analyze", files=files, data=data)

        assert res.status_code == 200, f"Analyze failed: {res.text}"
        analysis_data = res.json()
        analysis_id = analysis_data["analysis_id"]

        # Check frame visuals for all 4 signals
        visual_types = ["fft", "flow", "noise", "facial"]
        for vt in visual_types:
            v_res = requests.get(f"{base_url}/api/frame-visual/{analysis_id}/0/{vt}")
            assert v_res.status_code == 200, f"Frame visual {vt} returned {v_res.status_code}"
            assert "image/jpeg" in v_res.headers.get("content-type", "")
            assert len(v_res.content) > 100, f"Frame visual {vt} is empty"

        # 13. Verify responsive.css is served and enforces 1280px, 900px, and 600px rules
        assert "/static/styles/responsive.css" in html
        resp_css_res = requests.get(f"{base_url}/static/styles/responsive.css")
        assert resp_css_res.status_code == 200
        resp_css = resp_css_res.text
        assert "@media (max-width: 1280px)" in resp_css
        assert "@media (max-width: 900px)" in resp_css
        assert "@media (max-width: 600px)" in resp_css
        # At <900px: inspector becomes single column, player is NOT sticky (position: static)
        assert "grid-template-columns: 1fr !important;" in resp_css
        assert "position: static !important;" in resp_css
        assert "top: auto !important;" in resp_css
        # At <600px: hero H1 clamp to 3rem minimum, timeline markers 1px
        assert "clamp(3rem, 12vw, 4.5rem)" in resp_css
        assert "width: 1px !important;" in resp_css

        # 14. Verify a11y.css is served and implements WCAG AA focus rings & reduced motion
        assert "/static/styles/a11y.css" in html
        a11y_res = requests.get(f"{base_url}/static/styles/a11y.css")
        assert a11y_res.status_code == 200
        a11y_css = a11y_res.text
        assert ":focus-visible" in a11y_css
        assert "outline: 2px solid var(--ink" in a11y_css
        assert "outline-offset: 2px" in a11y_css
        assert "@media (prefers-reduced-motion: reduce)" in a11y_css
        assert "opacity: 1 !important;" in a11y_css
        assert "transform: none !important;" in a11y_css

        # 15. Verify ARIA attributes in HTML (dropZone, timeline, canvases, modal)
        assert 'role="button"' in html
        assert 'tabindex="0"' in html
        assert 'role="slider"' in html
        assert 'aria-label="Forensic anomaly timeline scrubber"' in html
        assert 'role="img"' in html
        assert 'aria-label="2D FFT high-frequency power spectrum heatmap' in html
        assert 'aria-label="Optical flow vector field heatmap' in html
        assert 'aria-label="PRNU sensor noise residual heatmap' in html
        assert 'aria-label="Facial boundary contour heatmap' in html
        assert 'role="dialog"' in html
        assert 'aria-modal="true"' in html
        assert 'aria-labelledby="settingsModalTitle"' in html
        assert 'id="settingsModalTitle"' in html

        # 16. Verify app.js contains keyboard access, focus trap, and Escape dismissal
        app_res = requests.get(f"{base_url}/static/app.js")
        assert app_res.status_code == 200
        app_js = app_res.text
        assert "Enter" in app_js and "videoInput.click()" in app_js
        assert "ArrowLeft" in app_js and "ArrowRight" in app_js
        assert "Escape" in app_js
        assert "closeSettingsModal" in app_js
        assert "previouslyFocusedElement" in app_js

    finally:
        server_thread.stop()
