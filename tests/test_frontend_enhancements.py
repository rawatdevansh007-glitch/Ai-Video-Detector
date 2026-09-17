import os
import json
import re
import pytest

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(PROJECT_DIR, "frontend")

def test_html_structure_enhancements():
    for html_path in [os.path.join(FRONTEND_DIR, "index.html"), os.path.join(PROJECT_DIR, "index.html")]:
        assert os.path.exists(html_path), f"Missing {html_path}"
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. Chart.js CDN script inclusion
        assert "chart.js" in content.lower(), f"Chart.js missing in {html_path}"

        # 2. Weighted ensemble breakdown box
        assert "ensembleBreakdownBox" in content
        assert "ensembleFinalScoreVal" in content
        for signal_id in ["Bio", "Flow", "FFT", "PRNU"]:
            assert f"ensembleWeight{signal_id}" in content
            assert f"ensembleBar{signal_id}" in content
            assert f"ensembleRaw{signal_id}" in content
            assert f"ensembleContrib{signal_id}" in content

        # 3. Interactive Chart.js anomaly timeline canvas
        assert "anomalyChartCanvas" in content

        # 4. Multi-subject container and tab list
        assert "multiSubjectContainer" in content
        assert "subjectTabsList" in content

        # 5. Grad-CAM dual-layer viewport & interactive controls
        assert "gradcamViewport" in content
        assert "gradcamFaceBase" in content
        assert "gradcamHeatmapOverlay" in content
        assert "gradcamControls" in content
        assert "gradcamToggleBtn" in content
        assert "gradcamBlendSelect" in content
        assert "gradcamOpacityRange" in content

        # 6. Video compression warning banner
        assert "compressionWarningBanner" in content
        assert "High Video Compression Detected" in content

def test_javascript_logic_enhancements():
    for js_path in [os.path.join(FRONTEND_DIR, "app.js"), os.path.join(PROJECT_DIR, "app.js")]:
        assert os.path.exists(js_path), f"Missing {js_path}"
        with open(js_path, "r", encoding="utf-8") as f:
            code = f.read()

        assert "function getSemanticTheme" in code
        assert "#10b981" in code
        assert "#f59e0b" in code
        assert "#ef4444" in code

        assert "function renderWeightedEnsembleBreakdown" in code
        assert "ensembleFinalScoreVal" in code
        assert "ensembleWeight" in code
        assert "ensembleContrib" in code

        assert "function renderAnomalyChart" in code
        assert "anomalyChartInstance" in code
        assert "mainVideoPlayer.currentTime = f.timestamp_sec" in code
        assert "updateChartActivePoint" in code

        assert "function renderMultiSubjectTabs" in code
        assert "multiSubjectContainer" in code
        assert "subjectTabsList" in code
        assert "currentSubjectIndex" in code
        assert "updateSubjectView" in code

        assert "gradcamFaceBase" in code
        assert "gradcamHeatmapOverlay" in code
        assert "gradcamToggleBtn" in code
        assert "gradcamBlendSelect" in code
        assert "gradcamOpacityRange" in code
        assert "mixBlendMode" in code

        assert "low_bitrate_flag" in code
        assert "compressionWarningBanner" in code

def test_backend_multi_face_and_gradcam_artifacts():
    backend_dir = os.path.join(PROJECT_DIR, "backend")
    import sys
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    from engine import ForensicEngine
    import numpy as np
    import cv2

    engine = ForensicEngine(cache_dir=os.path.join(PROJECT_DIR, "cache"))

    fake_frame = np.full((360, 640, 3), 120, dtype=np.uint8)
    cv2.ellipse(fake_frame, (320, 180), (80, 110), 0, 0, 360, (180, 160, 140), -1)

    temp_dir = os.path.join(PROJECT_DIR, "cache", "test_frame_artifacts")
    os.makedirs(temp_dir, exist_ok=True)

    score, details, annotated, has_face = engine.facial_detector.analyze_frame(fake_frame, frame_idx=0, save_dir=temp_dir)
    assert "faces" in details
    assert isinstance(details["faces"], list)
    assert "score" in details

    assert os.path.exists(os.path.join(temp_dir, "gradcam.png"))
    assert os.path.exists(os.path.join(temp_dir, "face_crop.jpg"))
