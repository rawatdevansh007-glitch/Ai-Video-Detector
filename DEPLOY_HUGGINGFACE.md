# Deploying VeritasVideo to Hugging Face Spaces (100% Free, No Credit Card)

VeritasVideo supports **Static Space (`sdk: static`)**, which is **100% completely free on Hugging Face Spaces and requires zero credit cards or payment verification**.

In Static mode, VeritasVideo runs an in-browser client-side video forensics engine powered by HTML5 Video, Canvas pixel decoding, high-pass PRNU noise filtering, motion vector extraction, 2D FFT spectral analysis, biometric boundary checks, and direct multimodal reasoning via Google Gemini Flash.

---

## Quick Deploy (Free Static Space)

### Step 1: Create a Space on Hugging Face
1. Go to [Hugging Face Spaces](https://huggingface.co/spaces) and sign in.
2. Click **Create new Space** (or go to `https://huggingface.co/new-space`).
3. Fill in:
   - **Space name**: `veritas-video-forensics` (or any name you like)
   - **License**: `mit`
   - **Space SDK**: Select **Static** (HTML / JavaScript)
   - **Space hardware**: **Free**
4. Click **Create Space**.

---

### Step 2: Push Code to your Hugging Face Space

You can push directly from your local repository using Git:

1. Open your terminal in this repository folder:
   ```powershell
   git remote add hf https://huggingface.co/spaces/<YOUR_HF_USERNAME>/<YOUR_SPACE_NAME>
   ```
2. Push the main branch:
   ```powershell
   git push hf main
   ```
   *(When prompted for a password, enter your Hugging Face Access Token with **write** permissions from [Hugging Face Settings > Tokens](https://huggingface.co/settings/tokens)).*

3. That's it! Hugging Face immediately serves your static site at:
   `https://huggingface.co/spaces/<YOUR_HF_USERNAME>/<YOUR_SPACE_NAME>`

---

## Features Supported in Free Static Deployment

| Feature | Static Space (Free, No Credit Card) | Local / Docker Python Backend |
|---|---|---|
| **Cost / Payment** | **100% Free (No Card Needed)** | Docker requires card verification on HF |
| **Instant Launch** | **Instant (no container build time)** | ~2-3 min build time |
| **Client-Side Video Decoding** | Supported (HTML5 Canvas & Video API) | Supported (OpenCV & FFmpeg) |
| **2D FFT & Power Spectrum** | In-browser spectral analysis & heatmaps | In-browser & NumPy/SciPy |
| **Optical Flow & Motion Vectors** | In-browser temporal coherence & vector field | In-browser & Farneback dense optical flow |
| **PRNU Noise Residual** | In-browser high-pass Laplacian sensor noise | In-browser & high-pass filtering |
| **Biometric & Facial Seams** | Biometric seam detection & facial boundary tracking | PyTorch ResNet-50 deep learning model |
| **Weighted Ensemble Scoring** | Dynamic weighted ensemble $\sum w_i A_i$ | Dynamic weighted ensemble $\sum w_i A_i$ |
| **Compression Mitigation** | Auto bit-rate scaling for low bitrates | Auto bit-rate scaling for low bitrates |
| **Google Gemini Multimodal AI** | Direct client-side via Settings modal | Server-side or client-side |
| **JSON Export & Print Reports** | Supported | Supported |
| **Sample Test Videos** | Bundled in `/samples` (Real, AI, C2PA) | Bundled in `/samples` |

---

## Running with the Full Python & PyTorch Backend Locally

If you want to run the full PyTorch ResNet-50 and OpenCV backend on your local machine:

1. Double-click `run.bat` (or run `./run.ps1` in PowerShell).
2. The server starts at `http://127.0.0.1:8000`.
3. Open the URL in any web browser.

