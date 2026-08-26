"""
AI Video SaaS Backend - Main Application
========================================
FastAPI application with modular router architecture.

This file handles:
- App initialization
- CORS middleware
- Router includes
- Startup/shutdown events
"""
import os
import sys
import glob
from dotenv import load_dotenv

load_dotenv()

# Force UTF-8 encoding
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

print("DEBUG: Starting AI Video SaaS Backend...")
print(f"Starting app on Port: {os.getenv('PORT', '8001')}")

# --- IMPORTS ---
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- APP INITIALIZATION ---
from config import TEMP_DIR

is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"

app = FastAPI(
    title="CloneFrame API",
    description="Backend API for CloneFrame - AI Video Creation & Cloning Platform",
    version="2.0.0",
    docs_url=None if is_production else "/docs",
    redoc_url=None if is_production else "/redoc",
    openapi_url=None if is_production else "/openapi.json"
)

def download_hindi_font():
    import urllib.request
    fonts_dir = os.path.join(os.path.dirname(__file__), "assets", "fonts")
    os.makedirs(fonts_dir, exist_ok=True)
    font_path = os.path.join(fonts_dir, "NotoSansDevanagari-Bold.ttf")
    if not os.path.exists(font_path):
        print(f"Downloading Noto Sans Devanagari font to {font_path}...")
        url = "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Bold.ttf"
        try:
            urllib.request.urlretrieve(url, font_path)
            print("Font download complete.")
        except Exception as e:
            print(f"Failed to download font: {e}")

download_hindi_font()

# Ensure local temporary working directory exists (private to container)
os.makedirs(TEMP_DIR, exist_ok=True)

# --- CORS MIDDLEWARE (EXACT CANONICAL ALLOWLIST) ---
allowed_origins = [
    "https://cloneframe.com",
    "https://app.cloneframe.com",
    "https://shortcutsai.vercel.app",
]
if not is_production:
    allowed_origins.extend([
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001"
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# --- PIL FIX for MoviePy ---
print("DEBUG: Configuring PIL...")
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
print("DEBUG: PIL Configured.")

# --- STARTUP CLEANUP ---
from config import TEMP_DIR
def cleanup_temp_files():
    """Clean temporary files on startup."""
    print("🧹 Running Startup Cleanup...")
    patterns = ["temp_*", "*.vtt", "viral_cut.mp4"]
    count = 0
    for pattern in patterns:
        for f in glob.glob(os.path.join(TEMP_DIR, pattern)):
            try:
                os.remove(f)
                count += 1
            except:
                pass
    print(f"✨ Cleanup: Removed {count} temporary files.")

# Run cleanup
cleanup_temp_files()

# --- AUTHENTICATED JOB STATUS ENDPOINT ---
from fastapi import Depends, HTTPException
from core.auth import get_current_user
from core.firestore_client import get_job_status

@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str, user_id: str = Depends(get_current_user)):
    job_status = get_job_status(user_id, job_id)
    if not job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_status

# --- ROUTER IMPORTS ---
print("DEBUG: Importing Routers...")
from routers import system, idea_studio, repurposer, dubbing, projects, url_import, trend_cloner, director, video_cloner


# --- ROUTER INCLUDES ---
print("DEBUG: Including Routers...")

# System routes (health, config, user profile)
app.include_router(system.router, tags=["System"])

# Idea Studio routes (brainstorm, script, render)
app.include_router(idea_studio.router, tags=["Idea Studio"])

# Repurposer routes (upload, analyze, cut)
app.include_router(repurposer.router, tags=["Viral Repurposer"])

# Dubbing routes (voiceover, clone, dub)
app.include_router(dubbing.router, tags=["Global Dubber"])

# Projects routes (save, list)
app.include_router(projects.router, tags=["Projects"])

# URL Import routes (yt-dlp video download)
app.include_router(url_import.router, tags=["URL Import"])

# Trend Cloner routes (Veo AI video generation)
app.include_router(trend_cloner.router, tags=["Trend Cloner"])

# Production Director routes
app.include_router(director.router, tags=["AI Production Director"])

# Video Cloner routes (Phase 8D)
app.include_router(video_cloner.router, tags=["Video Cloner"])


print("✅ All Routers Loaded Successfully!")

# --- STARTUP/SHUTDOWN EVENTS ---
@app.on_event("startup")
async def startup_event():
    print("🚀 AI Video SaaS Backend Started!")
    print(f"📍 Environment: {os.getenv('ENVIRONMENT', 'development')}")
    print(f"📍 Project: {os.getenv('GOOGLE_CLOUD_PROJECT', 'shortcutai-backend')}")
    
    # --- STARTUP MODEL VALIDATION GATE (P1: re-enabled) ---
    # Previously commented out ("FOR LOCAL TEST"), which allowed silent drift
    # between ModelRoutingConfig and the live GCP model catalog.
    # Policy:
    #   - SKIP_MODEL_VALIDATION=1   -> force-skip (CI / offline smoke tests)
    #   - No ADC credentials found  -> warn & continue in dev, ABORT in prod
    #   - Live catalog mismatch     -> ALWAYS abort (config error in any env)
    try:
        from google.auth.exceptions import DefaultCredentialsError

        from core.model_validator import validate_production_models

        skip_validation = os.getenv("SKIP_MODEL_VALIDATION", "").strip().lower() in ("1", "true", "yes")
        if skip_validation:
            print("⏭️  Startup model validation SKIPPED (SKIP_MODEL_VALIDATION set).")
            return

        validate_production_models()
    except DefaultCredentialsError:
        is_prod_env = os.getenv("ENVIRONMENT", "development").lower() == "production"
        if is_prod_env:
            print("🚨 STARTUP ABORTED: No GCP Application Default Credentials available for model validation.")
            sys.exit(1)
        print("⚠️  Model validation skipped: no Application Default Credentials (local/dev mode).")
    except Exception as e:
        print(f"🚨 STARTUP ABORTED: {e}")
        sys.exit(1)

@app.on_event("shutdown")
async def shutdown_event():
    print("👋 AI Video SaaS Backend Shutting Down...")

# --- MAIN ENTRY POINT ---
if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting AI Video SaaS Backend on Port 8001...")
    uvicorn.run(app, host="127.0.0.1", port=8001)
