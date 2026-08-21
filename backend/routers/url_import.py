"""
URL Import Router
Download videos from YouTube, TikTok, Instagram, etc. using shared secure video downloader.
"""
import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.auth import get_current_user
from core.storage_client import upload_to_gcs
from core.video_downloader import download_video
from config import TEMP_DIR

router = APIRouter()


# --- REQUEST MODEL ---
class URLImportRequest(BaseModel):
    url: str


# --- ENDPOINT ---
@router.post("/import-video-url")
async def import_video_url(
    request: URLImportRequest,
    user_id: str = Depends(get_current_user)
):
    """Download a video from a URL using shared secure video downloader and prepare it for analysis."""
    url = request.url.strip()

    unique_id = uuid.uuid4().hex[:8]
    output_filename = f"url_import_{unique_id}.mp4"
    output_path = os.path.join(TEMP_DIR, output_filename)

    try:
        result = download_video(url, output_path=output_path)
        if not result.success or not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            status_code = 400
            if result.error_type in ["download_timeout", "process_error", "file_missing"]:
                status_code = 500
            elif result.error_type == "duration_limit_exceeded":
                status_code = 400
            raise HTTPException(status_code=status_code, detail=result.error_message or "Failed to download video.")

        file_size = os.path.getsize(output_path)
        print(f"[URL Import] Downloaded: {output_filename} ({file_size / 1024 / 1024:.1f} MB)")

        # Upload to GCS
        gcs_blob_name = output_filename
        print(f"[URL Import] Uploading to GCS: {gcs_blob_name}")
        gcs_url = upload_to_gcs(output_path, gcs_blob_name)

        return {
            "gcs_path": gcs_blob_name,
            "filename": output_filename,
            "platform": result.platform,
            "duration": result.duration if result.duration > 0 else None,
            "file_size_mb": round(file_size / 1024 / 1024, 1)
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[URL Import] Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
