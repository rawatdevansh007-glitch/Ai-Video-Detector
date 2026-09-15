# Deploying VeritasVideo to Render

This guide outlines how to deploy **VeritasVideo** to [Render](https://render.com) as a live, public web service.

---

## Prerequisites
1. A free account on [Render](https://render.com).
2. A GitHub or GitLab account with this repository pushed to it.

---

## Method 1: 1-Click Blueprint Deployment (Recommended)

Render automatically recognizes the included [`render.yaml`](file:///C:/Users/rawat/.gemini/antigravity/scratch/ai-video-detector/render.yaml) file:

1. Push this project to your GitHub repository:
   ```bash
   git init
   git add .
   git commit -m "feat: render deployment configuration"
   git remote add origin https://github.com/<your-username>/<your-repo-name>.git
   git branch -M main
   git push -u origin main
   ```
2. Log in to the [Render Dashboard](https://dashboard.render.com).
3. Click **New +** in the top-right corner and select **Blueprint**.
4. Connect your GitHub repository.
5. Render will automatically read `render.yaml`, configure the Docker environment, set up the health check (`/health`), and provision the web service.
6. Click **Apply**.
7. Once the build finishes (typically 2-3 minutes), your service will be live at `https://<service-name>.onrender.com`!

---

## Method 2: Manual Web Service Setup (Docker)

If you prefer setting up the web service manually through the Render dashboard:

1. In the Render Dashboard, click **New +** -> **Web Service**.
2. Select your repository.
3. Configure the following settings:
   - **Name**: `veritasvideo-detector` (or any preferred name)
   - **Language / Runtime**: `Docker`
   - **Region**: Choose the region closest to you (e.g., Oregon, Ohio, Frankfurt, Singapore)
   - **Branch**: `main`
   - **Instance Type**: `Free` (or higher)
4. Under **Advanced Settings**:
   - **Health Check Path**: `/health`
   - **Auto-Deploy**: `Yes`
5. Click **Create Web Service**.

---

## Method 3: Native Python Runtime (Without Docker)

If you wish to use Render's native Python runtime instead of Docker:

1. In the Render Dashboard, click **New +** -> **Web Service**.
2. Select your repository.
3. Configure:
   - **Language**: `Python`
   - **Build Command**:
     ```bash
     pip install -r requirements.txt && python create_samples.py
     ```
   - **Start Command**:
     ```bash
     uvicorn backend.main:app --host 0.0.0.0 --port $PORT
     ```
   - **Health Check Path**: `/health`
4. Under **Environment Variables**, optionally add:
   - `PYTHON_VERSION`: `3.11.9`
5. Click **Create Web Service**.

---

## Optional: Configuring Google Gemini Vision API

For multimodal visual reasoning (analyzing physical logic, shadows, and anatomical continuity in anomaly frames):

1. Go to your Web Service in the Render Dashboard.
2. Click **Environment**.
3. Add a new variable:
   - **Key**: `GEMINI_API_KEY`
   - **Value**: Your Google Gemini API Key (`AIzaSy...`)
4. Click **Save Changes**. The service will automatically redeploy with Gemini vision reasoning enabled.

---

## Verification & Testing After Deployment

Once Render displays **`Live`**:
1. Open your public Render URL: `https://<service-name>.onrender.com`.
2. Verify the health check:
   - Navigate to `https://<service-name>.onrender.com/health`
   - Expected response: `{"status":"healthy","service":"VeritasVideo Forensic Studio","version":"2.0.0"}`
3. Try analyzing a video or clicking the starter sample buttons (**Sample Authentic**, **Sample AI**, **Sample C2PA AI**).
4. Click **"Train Model"** in the top navbar to inspect your model or upload training videos.
