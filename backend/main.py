import os
import shutil
import tempfile
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import sys
# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine import ForensicEngine

from contextlib import asynccontextmanager

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
CACHE_DIR = os.path.join(PROJECT_DIR, "cache")
FRONTEND_DIR = os.path.join(PROJECT_DIR, "frontend")
SAMPLES_DIR = os.path.join(PROJECT_DIR, "samples")

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(SAMPLES_DIR, exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure sample videos exist for live demonstration upon startup."""
    sample_file = os.path.join(SAMPLES_DIR, "authentic_camera_sample.mp4")
    if not os.path.exists(sample_file):
        try:
            sys.path.insert(0, PROJECT_DIR)
            import create_samples
            create_samples.generate_sample_videos()
        except Exception as e:
            print(f"Notice: Could not auto-generate sample videos on startup: {e}")
    yield

app = FastAPI(
    title="VeritasVideo API",
    description="AI Video Forensics & Deepfake Detection Engine",
    version="2.0.0",
    lifespan=lifespan
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static frontend files
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# Initialize Engine
forensic_engine = ForensicEngine(cache_dir=CACHE_DIR)

@app.get("/health")
def health_check():
    """Health check endpoint for Render and container orchestration."""
    return {
        "status": "healthy",
        "service": "VeritasVideo Forensic Studio",
        "version": "2.0.0"
    }

@app.get("/")
def serve_index():
    """Serves the frontend dashboard."""
    index_file = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "VeritasVideo Forensic API is running."}

@app.post("/api/analyze")
async def analyze_video(
    file: UploadFile = File(...),
    gemini_api_key: Optional[str] = Form(None),
    sample_count: int = Form(16)
):
    """
    Upload and analyze a video file for synthetic AI generation artifacts.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No video file supplied.")

    upload_dir = os.path.join(CACHE_DIR, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    # Secure temporary file storage
    safe_name = f"upload_{os.path.basename(file.filename)}"
    temp_path = os.path.join(upload_dir, safe_name)

    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Run forensic analysis
        results = forensic_engine.analyze_video(
            video_path=temp_path,
            sample_count=sample_count,
            gemini_api_key=gemini_api_key
        )

        return JSONResponse(content=results)

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    finally:
        # Keep uploaded file or clean up if needed
        pass

@app.get("/api/frame-visual/{analysis_id}/{frame_idx}/{filter_type}")
def get_frame_visual(analysis_id: str, frame_idx: int, filter_type: str):
    """
    Returns the visual forensic heatmap image for a specific analyzed frame and filter.
    Filter types: 'original', 'fft', 'noise', 'flow', 'facial'
    """
    # Sanitize inputs
    valid_filters = ["original", "fft", "noise", "flow", "facial"]
    if filter_type not in valid_filters:
        filter_type = "original"

    img_path = os.path.join(CACHE_DIR, analysis_id, f"frame_{frame_idx}", f"{filter_type}.jpg")
    if not os.path.exists(img_path):
        # Fallback to original if requested filter not present
        fallback_path = os.path.join(CACHE_DIR, analysis_id, f"frame_{frame_idx}", "original.jpg")
        if os.path.exists(fallback_path):
            return FileResponse(fallback_path, media_type="image/jpeg")
        raise HTTPException(status_code=404, detail="Forensic frame visual not found.")

    return FileResponse(img_path, media_type="image/jpeg")

@app.get("/api/sample-video/{sample_type}")
def get_sample_video(sample_type: str):
    """
    Returns pre-packaged sample video (real or AI) for instant testing.
    """
    if sample_type == "real":
        file_path = os.path.join(SAMPLES_DIR, "authentic_camera_sample.mp4")
    elif sample_type == "ai":
        file_path = os.path.join(SAMPLES_DIR, "synthetic_diffusion_sample.mp4")
    elif sample_type == "c2pa":
        file_path = os.path.join(SAMPLES_DIR, "c2pa_ai_sample.mp4")
    else:
        raise HTTPException(status_code=400, detail="Invalid sample type. Choose 'real', 'ai', or 'c2pa'.")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Sample video '{sample_type}' is being generated or not found.")

    return FileResponse(file_path, media_type="video/mp4")


@app.get("/api/model/status")
def get_model_status():
    """
    Returns current model status, performance metrics, and dataset statistics.
    """
    from training.dataset import VideoDatasetManager
    from training.trainer import DEFAULT_MODEL_PATH, ModelTrainer

    dataset_mgr = VideoDatasetManager(dataset_dir=os.path.join(PROJECT_DIR, "dataset"))
    ds_summary = dataset_mgr.get_summary()

    model_pkg = ModelTrainer.load_model(DEFAULT_MODEL_PATH)
    is_trained = model_pkg is not None

    response = {
        "is_trained": is_trained,
        "dataset_summary": ds_summary,
        "model_type": model_pkg.get("model_type") if is_trained else None,
        "trained_at": model_pkg.get("trained_at") if is_trained else None,
        "metrics": model_pkg.get("metrics") if is_trained else None,
        "top_features": model_pkg.get("feature_importances", [])[:8] if is_trained else []
    }
    return JSONResponse(content=response)


@app.post("/api/model/train")
def train_model(
    model_type: str = Form("hist_gb"),
    test_size: float = Form(0.2),
    clear_cache: bool = Form(False)
):
    """
    Triggers feature extraction and ML model training on the dataset.
    """
    from training.dataset import VideoDatasetManager
    from training.trainer import ModelTrainer

    dataset_mgr = VideoDatasetManager(dataset_dir=os.path.join(PROJECT_DIR, "dataset"))
    summary = dataset_mgr.get_summary()

    if not summary["has_sufficient_data"]:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Insufficient data: Found {summary['real_videos_count']} Real and {summary['ai_videos_count']} AI videos. "
                f"At least 2 Real and 2 AI videos are required to train a model."
            )
        )

    if clear_cache and os.path.exists(dataset_mgr.cache_file):
        os.remove(dataset_mgr.cache_file)

    try:
        X, y, feature_names, _ = dataset_mgr.scan_and_extract(sample_count=12)
        trainer = ModelTrainer()
        result = trainer.train_model(
            X, y,
            feature_names=feature_names,
            model_type=model_type,
            test_size=test_size
        )
        # Reload model into engine immediately
        forensic_engine.reload_model()
        return JSONResponse(content=result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


@app.post("/api/model/upload-sample")
async def upload_dataset_sample(
    file: UploadFile = File(...),
    category: str = Form(...)  # "real" or "ai"
):
    """
    Uploads a training video into dataset/real or dataset/ai.
    """
    category = category.lower().strip()
    if category not in ["real", "ai"]:
        raise HTTPException(status_code=400, detail="Category must be 'real' or 'ai'.")

    target_dir = os.path.join(PROJECT_DIR, "dataset", category)
    os.makedirs(target_dir, exist_ok=True)

    filename = os.path.basename(file.filename)
    dest_path = os.path.join(target_dir, filename)

    try:
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        from training.dataset import VideoDatasetManager
        dataset_mgr = VideoDatasetManager(dataset_dir=os.path.join(PROJECT_DIR, "dataset"))
        return JSONResponse(content={
            "success": True,
            "filename": filename,
            "category": category,
            "dataset_summary": dataset_mgr.get_summary()
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
