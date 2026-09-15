// VeritasVideo Forensic Dashboard Application Logic

document.addEventListener('DOMContentLoaded', () => {
  // Support legacy or generic canvas element IDs if queried
  const canvasLegacyMap = { 'canvas1': 'fftCanvas', 'canvas2': 'flowCanvas', 'canvas3': 'prnuCanvas', 'canvas4': 'faceCanvas' };
  const origGetById = document.getElementById.bind(document);
  document.getElementById = function(id) {
    return origGetById(id) || (canvasLegacyMap[id] ? origGetById(canvasLegacyMap[id]) : null);
  };

  // DOM Elements
  const dropZone = document.getElementById('dropZone');
  const videoInput = document.getElementById('videoInput');
  const fileInfoCard = document.getElementById('fileInfoCard');
  const fileName = document.getElementById('fileName');
  const fileDetails = document.getElementById('fileDetails');
  const removeFileBtn = document.getElementById('removeFileBtn');
  const startAnalysisBtn = document.getElementById('startAnalysisBtn');
  const sampleRealBtn = document.getElementById('sampleRealBtn');
  const sampleAIBtn = document.getElementById('sampleAIBtn');
  const sampleC2PABtn = document.getElementById('sampleC2PABtn');

  const uploadSection = document.getElementById('uploadSection');
  const progressSection = document.getElementById('progressSection');
  const progressBar = document.getElementById('progressBar');
  const progressStepTitle = document.getElementById('progressStepTitle');
  const progressStepDetail = document.getElementById('progressStepDetail');

  const resultsDashboard = document.getElementById('resultsDashboard');
  const verdictBanner = document.getElementById('verdictBanner');
  const verdictIconContainer = document.getElementById('verdictIconContainer');
  const verdictBadge = document.getElementById('verdictBadge');
  const verdictRiskPill = document.getElementById('verdictRiskPill');
  const verdictHeadline = document.getElementById('verdictHeadline');
  const verdictExplanation = document.getElementById('verdictExplanation');

  const c2paBadge = document.getElementById('c2paBadge');
  const c2paBadgeText = document.getElementById('c2paBadgeText');
  const c2paDetailsBox = document.getElementById('c2paDetailsBox');
  const c2paIssuerVal = document.getElementById('c2paIssuerVal');
  const c2paGenVal = document.getElementById('c2paGenVal');
  const c2paSourceTypeVal = document.getElementById('c2paSourceTypeVal');

  const scoreDialCircle = document.getElementById('scoreDialCircle');
  const scorePercentValue = document.getElementById('scorePercentValue');
  const scoreLabelText = document.getElementById('scoreLabelText');

  const mainVideoPlayer = document.getElementById('mainVideoPlayer');
  const currentTimeDisplay = document.getElementById('currentTimeDisplay');
  const timelineContainer = document.getElementById('timelineContainer');
  const timelinePlayhead = document.getElementById('timelinePlayhead');

  const inspectorImage = document.getElementById('inspectorImage');
  const inspectorLoading = document.getElementById('inspectorLoading');
  const inspectedFrameTime = document.getElementById('inspectedFrameTime');
  const frameAnomalyScore = document.getElementById('frameAnomalyScore');
  const frameInspectorDescription = document.getElementById('frameInspectorDescription');
  const prevFrameBtn = document.getElementById('prevFrameBtn');
  const nextFrameBtn = document.getElementById('nextFrameBtn');
  const frameCounterText = document.getElementById('frameCounterText');
  const filterBtns = document.querySelectorAll('.filter-btn');

  const spectralScoreText = document.getElementById('spectralScoreText');
  const spectralScoreBar = document.getElementById('spectralScoreBar');
  const spectralStatusBadge = document.getElementById('spectralStatusBadge');

  const temporalScoreText = document.getElementById('temporalScoreText');
  const temporalScoreBar = document.getElementById('temporalScoreBar');
  const temporalStatusBadge = document.getElementById('temporalStatusBadge');

  const noiseScoreText = document.getElementById('noiseScoreText');
  const noiseScoreBar = document.getElementById('noiseScoreBar');
  const noiseStatusBadge = document.getElementById('noiseStatusBadge');

  const facialScoreText = document.getElementById('facialScoreText');
  const facialScoreBar = document.getElementById('facialScoreBar');
  const facialStatusBadge = document.getElementById('facialStatusBadge');

  // Signal Heatmap Canvases (Editorial Scroll Sections)
  const fftCanvas = document.getElementById('fftCanvas') || document.getElementById('canvas1');
  const flowCanvas = document.getElementById('flowCanvas') || document.getElementById('canvas2');
  const prnuCanvas = document.getElementById('prnuCanvas') || document.getElementById('canvas3');
  const faceCanvas = document.getElementById('faceCanvas') || document.getElementById('canvas4');

  const semanticSection = document.getElementById('semanticSection');
  const semanticAnalysisText = document.getElementById('semanticAnalysisText');

  const analyzeAnotherBtn = document.getElementById('analyzeAnotherBtn');
  const downloadReportBtn = document.getElementById('downloadReportBtn');
  const printReportBtn = document.getElementById('printReportBtn');

  // Settings elements
  const settingsBtn = document.getElementById('settingsBtn');
  const settingsModal = document.getElementById('settingsModal');
  const closeSettingsBtn = document.getElementById('closeSettingsBtn');
  const saveSettingsBtn = document.getElementById('saveSettingsBtn');
  const geminiApiKeyInput = document.getElementById('geminiApiKeyInput');
  const samplingDensitySelect = document.getElementById('samplingDensitySelect');

  // Application State
  let currentFile = null;
  let currentVideoUrl = null;
  let currentAnalysis = null;
  let currentFrameIndex = 0;
  let currentFilter = 'original';
  let progressInterval = null;

  // Settings State
  let geminiApiKey = localStorage.getItem('veritas_gemini_key') || '';
  let samplingDensity = localStorage.getItem('veritas_sampling_density') || '16';
  if (geminiApiKeyInput) geminiApiKeyInput.value = geminiApiKey;
  if (samplingDensitySelect) samplingDensitySelect.value = samplingDensity;

  // Drag and Drop Events & Keyboard Access
  dropZone.addEventListener('click', () => videoInput.click());
  dropZone.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      videoInput.click();
    }
  });
  dropZone.addEventListener('dragenter', (e) => {
    e.preventDefault();
    dropZone.classList.add('is-dragover');
  });
  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('is-dragover');
  });
  dropZone.addEventListener('dragleave', (e) => {
    dropZone.classList.remove('is-dragover');
  });
  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('is-dragover');
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  });

  videoInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelected(e.target.files[0]);
    }
  });

  function handleFileSelected(file) {
    if (!file.type.startsWith('video/') && !file.name.match(/\.(mp4|webm|mov|avi|mkv)$/i)) {
      alert('Please select a valid video file (MP4, WebM, MOV, AVI).');
      return;
    }
    currentFile = file;
    fileName.textContent = file.name;
    fileDetails.textContent = `${(file.size / (1024 * 1024)).toFixed(2)} MB • ${file.type || 'Video'}`;
    
    // Revoke previous blob url if exists
    if (currentVideoUrl) URL.revokeObjectURL(currentVideoUrl);
    currentVideoUrl = URL.createObjectURL(file);
    
    fileInfoCard.classList.remove('hidden');
    dropZone.classList.add('hidden');
  }

  removeFileBtn.addEventListener('click', () => {
    currentFile = null;
    if (currentVideoUrl) URL.revokeObjectURL(currentVideoUrl);
    currentVideoUrl = null;
    videoInput.value = '';
    fileInfoCard.classList.add('hidden');
    dropZone.classList.remove('hidden');
  });

  // Sample Buttons Handler
  if (sampleRealBtn) sampleRealBtn.addEventListener('click', () => loadSampleVideo('real'));
  if (sampleAIBtn) sampleAIBtn.addEventListener('click', () => loadSampleVideo('ai'));
  if (sampleC2PABtn) sampleC2PABtn.addEventListener('click', () => loadSampleVideo('c2pa'));

  async function loadSampleVideo(type) {
    try {
      dropZone.innerHTML = `
        <div class="py-2 text-left">
          <p class="text-xs text-muted font-mono"><i class="fa-solid fa-circle-notch animate-spin mr-2"></i>Loading sample ${type.toUpperCase()} video...</p>
        </div>
      `;
      const res = await fetch(`/api/sample-video/${type}`);
      if (!res.ok) {
        throw new Error(`Sample video not found (status ${res.status})`);
      }
      const blob = await res.blob();
      let filename = 'authentic_camera_sample.mp4';
      if (type === 'ai') filename = 'synthetic_diffusion_sample.mp4';
      if (type === 'c2pa') filename = 'c2pa_ai_sample.mp4';
      const file = new File([blob], filename, { type: 'video/mp4' });
      dropZone.innerHTML = `
        <input type="file" id="videoInput" accept="video/mp4,video/webm,video/quicktime,video/x-msvideo" class="hidden">
        <div class="dropzone-label">
          <span class="dropzone-prompt">Drop video file here, or <span class="dropzone-action">browse</span></span>
          <span class="dropzone-formats">MP4, WebM, MOV, AVI — max 100MB</span>
        </div>
      `;
      // Rebind videoInput if replaced
      const newVideoInput = document.getElementById('videoInput');
      if (newVideoInput) {
        newVideoInput.addEventListener('change', (e) => {
          if (e.target.files && e.target.files.length > 0) handleFileSelected(e.target.files[0]);
        });
      }
      handleFileSelected(file);
    } catch (err) {
      alert(`Could not load sample: ${err.message}`);
      window.location.reload();
    }
  }

  // Start Analysis
  startAnalysisBtn.addEventListener('click', async () => {
    if (!currentFile) return;

    // Show Progress
    uploadSection.classList.add('hidden');
    progressSection.classList.remove('hidden');
    resultsDashboard.classList.add('hidden');

    startProgressAnimation();

    const formData = new FormData();
    formData.append('file', currentFile);
    if (geminiApiKey) formData.append('gemini_api_key', geminiApiKey);
    formData.append('sample_count', samplingDensity);

    try {
      const response = await fetch('/api/analyze', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server returned error ${response.status}`);
      }

      const data = await response.json();
      currentAnalysis = data;
      clearInterval(progressInterval);
      progressBar.style.width = '100%';

      setTimeout(() => {
        progressSection.classList.add('hidden');
        renderResults(data);
      }, 600);

    } catch (error) {
      clearInterval(progressInterval);
      alert(`Forensic analysis failed: ${error.message}`);
      progressSection.classList.add('hidden');
      uploadSection.classList.remove('hidden');
    }
  });

  // Animated Progress Radar
  function startProgressAnimation() {
    let progress = 10;
    progressBar.style.width = '10%';
    const steps = [
      { title: 'Deconstructing Video Stream...', detail: 'Extracting keyframes and validating codec container headers' },
      { title: '2D FFT Spectral Analysis...', detail: 'Scanning azimuthal power distribution for generative checkerboard upsampling spikes', el: 'step-fft' },
      { title: 'Optical Flow & Motion Vectors...', detail: 'Measuring inter-frame temporal coherence and pixel warping drift', el: 'step-temporal' },
      { title: 'Noise Residual & PRNU...', detail: 'Filtering high-pass sensor noise for artificial spatial over-smoothing', el: 'step-noise' },
      { title: 'Facial & Boundary Seam Audit...', detail: 'Checking facial contour blending boundaries and biometric symmetry', el: 'step-seam' },
      { title: 'Ensemble Decision Matrix...', detail: 'Calibrating multi-signal probabilities and compiling anomaly timeline' }
    ];

    let stepIndex = 0;
    progressInterval = setInterval(() => {
      progress += 4;
      if (progress > 95) progress = 95;
      progressBar.style.width = `${progress}%`;

      const targetStep = Math.min(Math.floor((progress / 95) * steps.length), steps.length - 1);
      if (targetStep !== stepIndex) {
        stepIndex = targetStep;
        progressStepTitle.textContent = steps[stepIndex].title;
        progressStepDetail.textContent = steps[stepIndex].detail;
        if (steps[stepIndex].el) {
          const el = document.getElementById(steps[stepIndex].el);
          if (el) {
            el.classList.add('border-cyan-500/60', 'text-cyan-400');
            el.querySelector('i').className = 'fa-solid fa-circle-check text-cyan-400';
          }
        }
      }
    }, 400);
  }

  // Render Forensic Results
  function renderResults(data) {
    resultsDashboard.classList.remove('hidden');

    const isAI = data.verdict === 'AI_GENERATED';
    const isSuspicious = data.verdict === 'SUSPICIOUS';

    // 1. Verdict Styling & Editorial Statement
    const verdictWord = isAI ? 'AI-Generated' : (isSuspicious ? 'Suspicious' : 'Real');
    if (isAI) {
      verdictBanner.className = 'verdict is-ai';
      verdictBanner.setAttribute('data-verdict', 'ai');
    } else if (isSuspicious) {
      verdictBanner.className = 'verdict is-suspicious';
      verdictBanner.setAttribute('data-verdict', 'suspicious');
    } else {
      verdictBanner.className = 'verdict is-real';
      verdictBanner.setAttribute('data-verdict', 'real');
    }

    if (verdictBadge) verdictBadge.textContent = verdictWord;
    if (verdictHeadline) verdictHeadline.textContent = verdictWord;
    if (scoreDialCircle) scoreDialCircle.setAttribute('class', isAI ? 'text-red-500' : (isSuspicious ? 'text-amber-500' : 'text-emerald-500'));
    if (scoreLabelText) scoreLabelText.textContent = 'confidence';

    verdictRiskPill.textContent = `${data.confidence_level} Confidence`;
    verdictExplanation.textContent = data.summary_explanation;

    // Line 3 Confidence formatting (e.g., "84.2% confidence")
    const rawConf = isAI ? (data.composite_ai_score * 100) : ((1.0 - data.composite_ai_score) * 100);
    const formattedConf = rawConf.toFixed(1);
    if (scorePercentValue) scorePercentValue.textContent = `${formattedConf}%`;
    const confValEl = document.getElementById('confidenceValue');
    if (confValEl) confValEl.textContent = `${formattedConf}%`;

    // Horizontal run of mono-xs values (FFT / Flow / PRNU / Face)
    const vFFT = document.getElementById('verdictSubFFT');
    const vFlow = document.getElementById('verdictSubFlow');
    const vPRNU = document.getElementById('verdictSubPRNU');
    const vFace = document.getElementById('verdictSubFace');
    if (vFFT && data.metrics && data.metrics.spectral) {
      vFFT.textContent = `${Math.round(data.metrics.spectral.score * 100)}%`;
    }
    if (vFlow && data.metrics && data.metrics.temporal) {
      vFlow.textContent = `${Math.round(data.metrics.temporal.score * 100)}%`;
    }
    if (vPRNU && data.metrics && data.metrics.noise_residual) {
      vPRNU.textContent = `${Math.round(data.metrics.noise_residual.score * 100)}%`;
    }
    if (vFace && data.metrics && data.metrics.facial) {
      vFace.textContent = data.metrics.facial.faces_detected > 0 ? `${Math.round(data.metrics.facial.score * 100)}%` : 'N/A';
    }

    // C2PA Provenance Handling
    const c2pa = data.c2pa_provenance;
    if (c2pa && c2pa.has_c2pa && c2pa.is_ai_generated) {
      if (c2paBadge) {
        c2paBadge.classList.remove('hidden');
        if (c2paBadgeText) c2paBadgeText.textContent = `C2PA: ${c2pa.issuer || c2pa.claim_generator || 'AI Generator'}`;
      }
      if (c2paDetailsBox) {
        c2paDetailsBox.classList.remove('hidden');
        if (c2paIssuerVal) c2paIssuerVal.textContent = c2pa.issuer || 'AI Issuer';
        if (c2paGenVal) c2paGenVal.textContent = c2pa.claim_generator || c2pa.software_agent || 'Generative Engine';
        if (c2paSourceTypeVal) {
          const dst = c2pa.digital_source_type || 'trainedAlgorithmicMedia';
          c2paSourceTypeVal.textContent = dst.includes('/') ? dst.split('/').pop() : dst;
        }
      }
      if (data.visual_scan_bypassed) {
        verdictHeadline.textContent = 'C2PA Verified AI';
        if (verdictBadge) verdictBadge.textContent = 'C2PA Verified AI';
      }
    } else {
      if (c2paBadge) c2paBadge.classList.add('hidden');
      if (c2paDetailsBox) c2paDetailsBox.classList.add('hidden');
    }

    // Custom ML Model Info Handling
    const mlModel = data.ml_model;
    const mlModelBadge = document.getElementById('mlModelBadge');
    const mlModelBadgeText = document.getElementById('mlModelBadgeText');
    const mlModelDetailsBox = document.getElementById('mlModelDetailsBox');
    const mlModelTypeVal = document.getElementById('mlModelTypeVal');
    const mlModelProbVal = document.getElementById('mlModelProbVal');
    const mlModelWeightVal = document.getElementById('mlModelWeightVal');

    if (mlModel && mlModel.is_custom_model_active) {
      if (mlModelBadge) {
        mlModelBadge.classList.remove('hidden');
        if (mlModelBadgeText) mlModelBadgeText.textContent = `Trained ML: ${Math.round(mlModel.ml_ai_probability * 100)}% AI`;
      }
      if (mlModelDetailsBox) {
        mlModelDetailsBox.classList.remove('hidden');
        if (mlModelTypeVal) mlModelTypeVal.textContent = mlModel.model_type === 'hist_gb' ? 'Histogram Gradient Boosting' : (mlModel.model_type || 'Custom ML');
        if (mlModelProbVal) mlModelProbVal.textContent = `${Math.round(mlModel.ml_ai_probability * 100)}% AI Probability`;
        if (mlModelWeightVal) mlModelWeightVal.textContent = mlModel.scoring_mode || '60% ML + 40% Heuristics';
      }
    } else {
      if (mlModelBadge) mlModelBadge.classList.add('hidden');
      if (mlModelDetailsBox) mlModelDetailsBox.classList.add('hidden');
    }

    // 2. Score Dial Value
    const scorePct = Math.round(data.composite_ai_score * 100);
    const displayScore = isAI ? scorePct : (100 - scorePct);
    scorePercentValue.textContent = `${displayScore}%`;

    // SVG stroke dashoffset: circumference ~ 314.159
    const circumference = 2 * Math.PI * 50;
    const offset = circumference - (displayScore / 100) * circumference;
    setTimeout(() => {
      scoreDialCircle.style.strokeDashoffset = offset;
    }, 100);

    // 3. Setup Video Player & Synchronized Anomaly Timeline
    if (currentVideoUrl) {
      mainVideoPlayer.src = currentVideoUrl;
    }

    renderAnomalyTimeline(data.frames, data.video_metadata.duration_seconds);

    // 4. Setup Frame Inspector
    currentFrameIndex = 0;
    currentFilter = 'original';
    updateFrameInspector();

    // 5. Update Diagnostic Metric Cards
    updateMetricCard('spectral', data.metrics.spectral);
    updateMetricCard('temporal', data.metrics.temporal);
    updateMetricCard('noise', data.metrics.noise_residual);
    updateMetricCard('facial', data.metrics.facial);

    // 6. Semantic Reasoning section
    if (data.semantic_reasoning) {
      semanticSection.classList.remove('hidden');
      semanticAnalysisText.textContent = data.semantic_reasoning;
    } else {
      semanticSection.classList.add('hidden');
    }

    // Scroll smoothly to results
    resultsDashboard.scrollIntoView({ behavior: 'smooth' });
  }

  function updateMetricCard(type, metricData) {
    if (!metricData) return;
    const pct = Math.round(metricData.score * 100);

    let textEl, barEl, badgeEl;
    if (type === 'spectral') {
      textEl = spectralScoreText; barEl = spectralScoreBar; badgeEl = spectralStatusBadge;
    } else if (type === 'temporal') {
      textEl = temporalScoreText; barEl = temporalScoreBar; badgeEl = temporalStatusBadge;
    } else if (type === 'noise') {
      textEl = noiseScoreText; barEl = noiseScoreBar; badgeEl = noiseStatusBadge;
    } else if (type === 'facial') {
      textEl = facialScoreText; barEl = facialScoreBar; badgeEl = facialStatusBadge;
    }

    textEl.textContent = `${pct}%`;
    barEl.style.width = `${pct}%`;
    badgeEl.textContent = metricData.status;

    if (pct >= 70) {
      badgeEl.className = 'px-2 py-0.5 text-[10px] font-mono rounded bg-red-500/10 text-red-400 border border-red-500/20 font-bold';
    } else if (pct >= 40) {
      badgeEl.className = 'px-2 py-0.5 text-[10px] font-mono rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 font-bold';
    } else {
      badgeEl.className = 'px-2 py-0.5 text-[10px] font-mono rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold';
    }
  }

  // Anomaly Timeline Rendering
  function renderAnomalyTimeline(frames, totalDuration) {
    timelineContainer.innerHTML = '<div id="timelinePlayhead" class="absolute top-0 bottom-0 w-0.5 bg-cyan-400 z-20 pointer-events-none transition-all"></div>';
    if (!frames || frames.length === 0) return;

    const barWidth = 100 / frames.length;

    frames.forEach((f, idx) => {
      const bar = document.createElement('div');
      bar.className = 'timeline-bar';
      bar.style.left = `${idx * barWidth}%`;
      bar.style.width = `${barWidth}%`;
      
      const heightPct = Math.max(15, Math.round(f.anomaly_score * 100));
      bar.style.height = `${heightPct}%`;

      if (f.anomaly_score >= 0.65) {
        bar.classList.add('anomaly-high');
      } else if (f.anomaly_score >= 0.35) {
        bar.classList.add('anomaly-med');
      } else {
        bar.classList.add('anomaly-low');
      }

      bar.title = `Frame #${idx + 1} at ${f.timestamp_sec.toFixed(1)}s (Anomaly: ${(f.anomaly_score * 100).toFixed(0)}%)`;

      // Click seeking
      bar.addEventListener('click', () => {
        currentFrameIndex = idx;
        if (mainVideoPlayer.duration) {
          mainVideoPlayer.currentTime = f.timestamp_sec;
        }
        updateFrameInspector();
      });

      timelineContainer.appendChild(bar);
    });

    // Video playhead updates
    mainVideoPlayer.addEventListener('timeupdate', () => {
      const cur = mainVideoPlayer.currentTime;
      const dur = mainVideoPlayer.duration || totalDuration || 1;
      const pct = (cur / dur) * 100;
      const playhead = document.getElementById('timelinePlayhead');
      if (playhead) playhead.style.left = `${pct}%`;

      // Current time display
      const curMin = Math.floor(cur / 60).toString().padStart(2, '0');
      const curSec = Math.floor(cur % 60).toString().padStart(2, '0');
      const durMin = Math.floor(dur / 60).toString().padStart(2, '0');
      const durSec = Math.floor(dur % 60).toString().padStart(2, '0');
      currentTimeDisplay.textContent = `${curMin}:${curSec} / ${durMin}:${durSec}`;
    });

    updateTimelineA11y();
  }

  // Timeline Scrubber Keyboard Seek (ArrowLeft / ArrowRight)
  if (timelineContainer) {
    timelineContainer.addEventListener('keydown', (e) => {
      if (!currentAnalysis || !currentAnalysis.frames || currentAnalysis.frames.length === 0) return;
      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        if (currentFrameIndex > 0) {
          currentFrameIndex--;
          const f = currentAnalysis.frames[currentFrameIndex];
          if (mainVideoPlayer.duration) mainVideoPlayer.currentTime = f.timestamp_sec;
          updateFrameInspector();
        }
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        if (currentFrameIndex < currentAnalysis.frames.length - 1) {
          currentFrameIndex++;
          const f = currentAnalysis.frames[currentFrameIndex];
          if (mainVideoPlayer.duration) mainVideoPlayer.currentTime = f.timestamp_sec;
          updateFrameInspector();
        }
      }
    });
  }

  function updateTimelineA11y() {
    if (!timelineContainer || !currentAnalysis || !currentAnalysis.frames || currentAnalysis.frames.length === 0) return;
    const total = currentAnalysis.frames.length;
    const pct = Math.round(((currentFrameIndex + 1) / total) * 100);
    timelineContainer.setAttribute('aria-valuenow', pct);
    timelineContainer.setAttribute('aria-valuetext', `Frame ${currentFrameIndex + 1} of ${total}`);
  }

  // Update Frame Inspector View
  function updateFrameInspector() {
    if (!currentAnalysis || !currentAnalysis.frames || currentAnalysis.frames.length === 0) return;
    updateTimelineA11y();

    const frame = currentAnalysis.frames[currentFrameIndex];
    inspectedFrameTime.textContent = `Frame #${currentFrameIndex + 1} (${frame.timestamp_sec.toFixed(1)}s)`;
    frameAnomalyScore.textContent = `${(frame.anomaly_score * 100).toFixed(0)}% / 100%`;
    frameAnomalyScore.className = frame.anomaly_score >= 0.65 ? 'font-bold text-red-400' : (frame.anomaly_score >= 0.35 ? 'font-bold text-amber-400' : 'font-bold text-emerald-400');
    
    frameCounterText.textContent = `Frame ${currentFrameIndex + 1} of ${currentAnalysis.frames.length}`;
    frameInspectorDescription.textContent = frame.diagnostics || 'Analyzing frame-level mathematical properties.';

    // Load filter image
    inspectorLoading.classList.remove('hidden');
    const visualUrl = `/api/frame-visual/${currentAnalysis.analysis_id}/${currentFrameIndex}/${currentFilter}`;
    
    const img = new Image();
    img.onload = () => {
      inspectorImage.src = visualUrl;
      inspectorLoading.classList.add('hidden');
    };
    img.onerror = () => {
      inspectorLoading.classList.add('hidden');
      inspectorImage.src = visualUrl; // attempt display
    };
    img.src = visualUrl;

    // Synchronize all 4 full-width forensic signal canvases
    renderAllSignalHeatmaps(currentFrameIndex);
  }

  // Draw Heatmap to Canvas helper
  function drawHeatmapToCanvas(canvas, imageUrl) {
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      canvas.width = img.naturalWidth || 1280;
      canvas.height = img.naturalHeight || 720;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    };
    img.onerror = () => {
      ctx.fillStyle = '#0a0d14';
      ctx.fillRect(0, 0, canvas.width || 640, canvas.height || 360);
      ctx.fillStyle = '#6B6660';
      ctx.font = '12px "JetBrains Mono", monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('FORENSIC HEATMAP UNAVAILABLE', (canvas.width || 640) / 2, (canvas.height || 360) / 2);
    };
    img.src = imageUrl;
  }

  // Render all 4 sequential signal heatmaps
  function renderAllSignalHeatmaps(frameIdx = currentFrameIndex) {
    if (!currentAnalysis || !currentAnalysis.analysis_id) return;
    const id = currentAnalysis.analysis_id;

    const targetFFT = document.getElementById('fftCanvas') || document.getElementById('canvas1') || document.querySelector('[data-signal="fft"] canvas');
    const targetFlow = document.getElementById('flowCanvas') || document.getElementById('canvas2') || document.querySelector('[data-signal="flow"] canvas');
    const targetPRNU = document.getElementById('prnuCanvas') || document.getElementById('canvas3') || document.querySelector('[data-signal="prnu"] canvas');
    const targetFace = document.getElementById('faceCanvas') || document.getElementById('canvas4') || document.querySelector('[data-signal="face"] canvas');

    if (targetFFT) drawHeatmapToCanvas(targetFFT, `/api/frame-visual/${id}/${frameIdx}/fft`);
    if (targetFlow) drawHeatmapToCanvas(targetFlow, `/api/frame-visual/${id}/${frameIdx}/flow`);
    if (targetPRNU) drawHeatmapToCanvas(targetPRNU, `/api/frame-visual/${id}/${frameIdx}/noise`);
    if (targetFace) drawHeatmapToCanvas(targetFace, `/api/frame-visual/${id}/${frameIdx}/facial`);
  }

  // Filter Buttons
  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentFilter = btn.getAttribute('data-filter');
      updateFrameInspector();
    });
  });

  // Prev / Next Frame
  prevFrameBtn.addEventListener('click', () => {
    if (!currentAnalysis || !currentAnalysis.frames) return;
    if (currentFrameIndex > 0) {
      currentFrameIndex--;
      updateFrameInspector();
    }
  });

  nextFrameBtn.addEventListener('click', () => {
    if (!currentAnalysis || !currentAnalysis.frames) return;
    if (currentFrameIndex < currentAnalysis.frames.length - 1) {
      currentFrameIndex++;
      updateFrameInspector();
    }
  });

  // Export JSON Report
  downloadReportBtn.addEventListener('click', () => {
    if (!currentAnalysis) return;
    const blob = new Blob([JSON.stringify(currentAnalysis, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `veritas_forensic_report_${currentAnalysis.analysis_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  });

  // Print Report
  printReportBtn.addEventListener('click', () => window.print());

  // Analyze Another
  analyzeAnotherBtn.addEventListener('click', () => {
    resultsDashboard.classList.add('hidden');
    uploadSection.classList.remove('hidden');
    removeFileBtn.click();
  });

  // Settings Modal Handlers & A11y Focus Trap
  let previouslyFocusedElement = null;

  function openSettingsModal() {
    previouslyFocusedElement = document.activeElement;
    settingsModal.classList.remove('hidden');
    // Place focus on the first interactive element or the close button
    const firstInput = geminiApiKeyInput || closeSettingsBtn;
    if (firstInput) {
      setTimeout(() => firstInput.focus(), 50);
    }
  }

  function closeSettingsModal() {
    settingsModal.classList.add('hidden');
    if (previouslyFocusedElement && typeof previouslyFocusedElement.focus === 'function') {
      previouslyFocusedElement.focus();
    }
  }

  settingsBtn.addEventListener('click', openSettingsModal);
  closeSettingsBtn.addEventListener('click', closeSettingsModal);
  const cancelSettingsBtn = document.getElementById('cancelSettingsBtn');
  if (cancelSettingsBtn) {
    cancelSettingsBtn.addEventListener('click', closeSettingsModal);
  }
  settingsModal.addEventListener('click', (e) => {
    if (e.target === settingsModal) {
      closeSettingsModal();
    }
  });

  // Settings Modal Keyboard Trap & Escape Dismiss
  document.addEventListener('keydown', (e) => {
    if (settingsModal.classList.contains('hidden')) return;

    if (e.key === 'Escape') {
      e.preventDefault();
      closeSettingsModal();
      return;
    }

    if (e.key === 'Tab') {
      const focusable = settingsModal.querySelectorAll(
        'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      );
      if (!focusable || focusable.length === 0) return;

      const firstEl = focusable[0];
      const lastEl = focusable[focusable.length - 1];

      if (e.shiftKey) {
        if (document.activeElement === firstEl) {
          e.preventDefault();
          lastEl.focus();
        }
      } else {
        if (document.activeElement === lastEl) {
          e.preventDefault();
          firstEl.focus();
        }
      }
    }
  });

  saveSettingsBtn.addEventListener('click', () => {
    geminiApiKey = geminiApiKeyInput.value.trim();
    samplingDensity = samplingDensitySelect.value;
    localStorage.setItem('veritas_gemini_key', geminiApiKey);
    localStorage.setItem('veritas_sampling_density', samplingDensity);
    closeSettingsModal();
    alert('Forensic settings saved successfully.');
  });

  // Model Training & Dataset Modal Handlers
  const modelTrainingBtn = document.getElementById('modelTrainingBtn');
  const modelModal = document.getElementById('modelModal');
  const closeModelModalBtn = document.getElementById('closeModelModalBtn');
  const refreshModelStatusBtn = document.getElementById('refreshModelStatusBtn');
  const startTrainingBtn = document.getElementById('startTrainingBtn');
  const generateSamplesBtn = document.getElementById('generateSamplesBtn');
  const trainModelTypeSelect = document.getElementById('trainModelTypeSelect');
  const trainingStatusBox = document.getElementById('trainingStatusBox');
  const trainingStatusText = document.getElementById('trainingStatusText');
  const uploadRealInput = document.getElementById('uploadRealInput');
  const uploadAIInput = document.getElementById('uploadAIInput');

  // Open & Close Modal
  if (modelTrainingBtn) {
    modelTrainingBtn.addEventListener('click', () => {
      modelModal.classList.remove('hidden');
      fetchModelStatus();
    });
  }

  if (closeModelModalBtn) {
    closeModelModalBtn.addEventListener('click', () => {
      modelModal.classList.add('hidden');
    });
  }

  if (refreshModelStatusBtn) {
    refreshModelStatusBtn.addEventListener('click', fetchModelStatus);
  }

  // Fetch and populate model status
  async function fetchModelStatus() {
    try {
      const res = await fetch('/api/model/status');
      if (!res.ok) return;
      const data = await res.json();

      const ds = data.dataset_summary || {};
      const realCount = ds.real_videos_count || 0;
      const aiCount = ds.ai_videos_count || 0;
      const totalCount = ds.total_videos || 0;

      const realCountBadge = document.getElementById('realCountBadge');
      const aiCountBadge = document.getElementById('aiCountBadge');
      const datasetTotalCountText = document.getElementById('datasetTotalCountText');
      if (realCountBadge) realCountBadge.textContent = realCount;
      if (aiCountBadge) aiCountBadge.textContent = aiCount;
      if (datasetTotalCountText) datasetTotalCountText.textContent = `${totalCount} Total Videos (${realCount} Real, ${aiCount} AI)`;

      const modelStatusDot = document.getElementById('modelStatusDot');
      const modelStatusText = document.getElementById('modelStatusText');
      const modelTypeBadge = document.getElementById('modelTypeBadge');
      const modelTrainedDate = document.getElementById('modelTrainedDate');
      const modelMetricsSection = document.getElementById('modelMetricsSection');

      if (data.is_trained) {
        if (modelStatusDot) modelStatusDot.className = 'w-3 h-3 rounded-full bg-emerald-500 animate-pulse';
        if (modelStatusText) modelStatusText.textContent = 'Custom Model Active';
        if (modelTypeBadge) modelTypeBadge.textContent = data.model_type === 'hist_gb' ? 'HistGradientBoosting' : (data.model_type || 'Custom ML');
        if (modelTrainedDate) {
          const dt = data.trained_at ? new Date(data.trained_at).toLocaleDateString() : 'Recently';
          modelTrainedDate.textContent = `Trained: ${dt} on ${ds.total_samples || totalCount} videos`;
        }
        if (modelMetricsSection) modelMetricsSection.classList.remove('hidden');

        // Populate metrics
        const m = data.metrics || {};
        const accEl = document.getElementById('metricAccuracy');
        const rocAucEl = document.getElementById('metricRocAuc');
        const f1El = document.getElementById('metricF1');
        const cvEl = document.getElementById('metricCv');

        if (accEl) accEl.textContent = `${Math.round((m.accuracy || 1) * 100)}%`;
        if (rocAucEl) rocAucEl.textContent = (m.roc_auc !== undefined ? m.roc_auc.toFixed(3) : '1.000');
        if (f1El) f1El.textContent = (m.f1_score !== undefined ? m.f1_score.toFixed(3) : '1.000');
        if (cvEl) cvEl.textContent = `${Math.round((m.cross_val_accuracy_mean || 1) * 100)}%`;

        // Populate Top Features
        const topFeaturesList = document.getElementById('topFeaturesList');
        if (topFeaturesList && data.top_features) {
          topFeaturesList.innerHTML = data.top_features.map((f, idx) => `
            <div class="space-y-1">
              <div class="flex justify-between text-[11px]">
                <span class="text-slate-300">${idx + 1}. ${f.feature.replace(/_/g, ' ')}</span>
                <span class="text-purple-400 font-bold">${f.importance_pct}%</span>
              </div>
              <div class="w-full bg-slate-900 rounded-full h-1.5 overflow-hidden">
                <div class="bg-gradient-to-r from-purple-500 to-indigo-500 h-full rounded-full" style="width: ${Math.max(f.importance_pct, 4)}%"></div>
              </div>
            </div>
          `).join('');
        }
      } else {
        if (modelStatusDot) modelStatusDot.className = 'w-3 h-3 rounded-full bg-slate-500';
        if (modelStatusText) modelStatusText.textContent = 'Default Heuristic Mode';
        if (modelTypeBadge) modelTypeBadge.textContent = 'No Custom Model Trained';
        if (modelTrainedDate) modelTrainedDate.textContent = 'Drop videos into dataset/ to train';
        if (modelMetricsSection) modelMetricsSection.classList.add('hidden');
      }
    } catch (e) {
      console.error('Failed to fetch model status', e);
    }
  }

  // Trigger Model Training
  if (startTrainingBtn) {
    startTrainingBtn.addEventListener('click', async () => {
      const modelType = trainModelTypeSelect ? trainModelTypeSelect.value : 'hist_gb';
      startTrainingBtn.disabled = true;
      trainingStatusBox.classList.remove('hidden');
      trainingStatusText.textContent = 'Extracting forensic features from dataset and training model...';

      const formData = new FormData();
      formData.append('model_type', modelType);
      formData.append('test_size', '0.2');

      try {
        const res = await fetch('/api/model/train', {
          method: 'POST',
          body: formData
        });

        const result = await res.json();
        if (!res.ok) {
          throw new Error(result.detail || 'Training failed');
        }

        trainingStatusText.textContent = `Model trained successfully! Accuracy: ${(result.metrics.accuracy * 100).toFixed(1)}%`;
        setTimeout(() => {
          trainingStatusBox.classList.add('hidden');
          startTrainingBtn.disabled = false;
          fetchModelStatus();
        }, 1500);

      } catch (err) {
        alert(`Training failed: ${err.message}`);
        trainingStatusBox.classList.add('hidden');
        startTrainingBtn.disabled = false;
      }
    });
  }

  // Dataset Upload Handlers
  async function handleDatasetUpload(fileInput, category) {
    const file = fileInput.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('category', category);

    try {
      const res = await fetch('/api/model/upload-sample', {
        method: 'POST',
        body: formData
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Upload failed');
      }

      alert(`Uploaded "${file.name}" to ${category.toUpperCase()} dataset!`);
      fileInput.value = '';
      fetchModelStatus();
    } catch (err) {
      alert(`Upload error: ${err.message}`);
    }
  }

  if (uploadRealInput) uploadRealInput.addEventListener('change', () => handleDatasetUpload(uploadRealInput, 'real'));
  if (uploadAIInput) uploadAIInput.addEventListener('change', () => handleDatasetUpload(uploadAIInput, 'ai'));

  // Generate Samples Button
  if (generateSamplesBtn) {
    generateSamplesBtn.addEventListener('click', async () => {
      generateSamplesBtn.disabled = true;
      generateSamplesBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1"></i> Generating...';

      try {
        const formData = new FormData();
        formData.append('model_type', 'hist_gb');
        formData.append('clear_cache', 'true');

        const res = await fetch('/api/model/train', {
          method: 'POST',
          body: formData
        });

        if (res.ok) {
          alert('Dataset and model calibrated successfully!');
          fetchModelStatus();
        } else {
          const err = await res.json();
          alert(`Calibration message: ${err.detail}`);
        }
      } catch (e) {
        alert(`Error: ${e.message}`);
      } finally {
        generateSamplesBtn.disabled = false;
        generateSamplesBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles text-cyan-400 mr-1.5"></i> Generate Calibration Samples';
      }
    });
  }

  // Initial load of model status
  fetchModelStatus();
});
