# Deploying VeritasVideo on Vercel (100% Free Static Hosting)

This guide walks you through deploying VeritasVideo to **Vercel** with zero cost, zero credit card requirement, and instant automated builds.

---

## Why Static Deployment on Vercel?

VeritasVideo features a dual-mode architecture:
1. **Cloud / Python Mode**: Used for local servers or dedicated GPU containers (e.g. Render, Hugging Face Docker).
2. **In-Browser Client-Side Engine**: Performs all forensic calculations (2D FFT frequency decay, dense optical flow vectors, PRNU sensor noise residual, ResNet-50 biometric seam analysis, multi-subject detection, Chart.js timeline, and Grad-CAM overlays) **directly inside the user's browser** via HTML5 Canvas and Web APIs.

Because Vercel Serverless Functions have a strict **250MB limit** and short timeouts, heavy ML Python packages (`torch`, `opencv`, `scikit-learn`) cannot be hosted on Vercel Serverless. By deploying VeritasVideo as a **static web application**, it runs completely free on Vercel with blazing-fast global CDN delivery.

---

## Option 1: First-Time Deployment on Vercel

1. Log in to [Vercel](https://vercel.com) and click **"Add New..."** → **"Project"**.
2. Select your GitHub repository: `Ai-Video-Detector`.
3. In the **Configure Project** screen:
   - **Framework Preset**: Select **"Other"** (or leave default, as `vercel.json` and `package.json` now automatically configure this).
   - **Root Directory**: `./` (default).
   - **Build and Output Settings**:
     - **Build Command**: Leave empty or keep `echo 'VeritasVideo static deployment ready'`.
     - **Output Directory**: Leave empty or keep `./`.
4. Click **Deploy**.
5. Your project will build and deploy in ~10 seconds!

---

## Option 2: Fixing an Existing Vercel Project

If your previous deployment failed with:
`Error: No FastAPI entrypoint found. Set "tool.vercel.entrypoint"`

This happened because Vercel previously detected `requirements.txt` and automatically locked the project framework to **FastAPI**.

Follow these 3 quick steps to fix it:

1. Open your project on the [Vercel Dashboard](https://vercel.com).
2. Go to **Settings** → **General** → **Build & Development Settings**:
   - Change **Framework Preset** from **FastAPI** to **Other**.
   - Toggle **Override** next to **Build Command** and ensure it is empty (or `echo 'VeritasVideo static deployment ready'`).
   - Toggle **Override** next to **Output Directory** and ensure it is empty (or `./`).
   - Click **Save**.
3. Go to the **Deployments** tab:
   - Click the three dots (`...`) on the latest deployment.
   - Click **Redeploy**.

Your deployment will now succeed immediately!
