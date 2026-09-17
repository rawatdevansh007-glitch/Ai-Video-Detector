# Deploying VeritasVideo to Hugging Face Spaces

This guide explains how to deploy **VeritasVideo** to [Hugging Face Spaces](https://huggingface.co/spaces) as a live public web application.

> [!TIP]
> **Why Hugging Face Spaces is recommended:**
> Hugging Face Spaces provides **16 GB RAM** and **2 vCPUs** on its **Free Tier** (unlike Render's free tier which has a 512 MB memory limit). This ensures PyTorch ResNet-50, OpenCV, and all multi-signal forensic models run smoothly without running out of memory.

---

## Method 1: Connect via GitHub (Automatic Deployment)

1. Go to [Hugging Face Spaces](https://huggingface.co/spaces) and log in or create a free account.
2. Click **Create new Space** (or navigate to `https://huggingface.co/new-space`).
3. Fill in the details:
   - **Space name**: `veritas-video-detector` (or your preferred name)
   - **License**: `mit` (or choose another)
   - **Space SDK**: Select **Docker** -> **Blank**
   - **Space hardware**: **Free - 2 vCPU · 16 GB RAM**
4. Under **Repository**:
   - You can connect your GitHub repository directly, or push using Git (see Method 2 below).

---

## Method 2: Deploy Directly using Git

1. Create a new Space on Hugging Face:
   - Go to `https://huggingface.co/new-space`
   - Select **Space SDK: Docker**
   - Hardware: **Free (16 GB RAM)**
   - Click **Create Space**

2. On your local machine, add the Hugging Face Space repository as a remote:
   ```bash
   git remote add hf https://huggingface.co/spaces/<YOUR-HF-USERNAME>/<YOUR-SPACE-NAME>
   ```

3. Push your code to Hugging Face:
   ```bash
   git push hf main
   ```
   *(When prompted for password, use your Hugging Face Access Token with write permissions from `https://huggingface.co/settings/tokens`)*.

4. Hugging Face will automatically:
   - Read the included `Dockerfile`
   - Build the container with PyTorch CPU and FFmpeg
   - Launch VeritasVideo on port `7860`
   - Provide you with a public URL: `https://huggingface.co/spaces/<YOUR-USERNAME>/<YOUR-SPACE-NAME>`

---

## Optional: Configuring Google Gemini Vision API

For multimodal visual reasoning (shadow checking, physics consistency, and generative artifacts):

1. In your Hugging Face Space, click **Settings** (top right).
2. Scroll to **Variables and secrets**.
3. Under **Secrets**, click **New secret**:
   - **Name**: `GEMINI_API_KEY`
   - **Value**: Your Google Gemini API Key (`AQ...`)
4. Save the secret. The Space will automatically reload with Gemini reasoning enabled!
