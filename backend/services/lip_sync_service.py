import os
import time
import requests
import uuid
import tempfile
from core.storage_client import upload_to_gcs, UPLOAD_BUCKET
from config import ModelRoutingConfig

def sync_lips(video_path: str, audio_path: str) -> str:
    """
    Submits a video and audio file to the Sync Labs v2 API.
    Uploads the local files to GCS first to generate publicly accessible signed URLs.
    Polls the API for completion and downloads the final lip-synced video.
    Falls back to the original video_path if any step fails.
    """
    api_key = os.getenv("SYNCLABS_API_KEY")
    
    # If no API key is provided, fallback to returning the original video immediately
    if not api_key:
        print("[LipSync Service WARNING] SYNCLABS_API_KEY not set. Bypassing lip-sync and returning raw video.")
        time.sleep(2)  # Simulate processing
        return video_path

    print(f"[LipSync Service] Starting lip-sync for video: {video_path}")
    
    # 1. Upload to GCS to get signed URLs
    job_uuid = uuid.uuid4().hex[:8]
    video_blob_name = f"synclabs_input_v2/{job_uuid}_video.mp4"
    audio_blob_name = f"synclabs_input_v2/{job_uuid}_audio.mp3"

    print("[LipSync Service] Uploading media to GCS for Sync Labs access...")
    try:
        video_url = upload_to_gcs(video_path, video_blob_name, UPLOAD_BUCKET)
        audio_url = upload_to_gcs(audio_path, audio_blob_name, UPLOAD_BUCKET)
    except Exception as e:
        print(f"[LipSync Service ERROR] Failed to upload files to GCS: {e}")
        return video_path

    if not video_url or not audio_url:
        print("[LipSync Service ERROR] Failed to obtain signed URLs for media.")
        return video_path

    # Check if URLs are localhost mock URLs (which won't work with Sync Labs)
    if "localhost" in video_url or "127.0.0.1" in video_url or "localhost" in audio_url or "127.0.0.1" in audio_url:
        print("[LipSync Service ERROR] URLs are local mocks, cannot send to Sync Labs.")
        return video_path

    # 2. Call Sync Labs v2 Generate API
    api_url = "https://api.sync.so/v2/generate"
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": ModelRoutingConfig.LIPSYNC,
        "input": [
            {
                "type": "video",
                "url": video_url
            },
            {
                "type": "audio",
                "url": audio_url
            }
        ]
    }
    
    print("[LipSync Service] Submitting job to Sync Labs v2 API...")
    try:
        response = requests.post(api_url, json=payload, headers=headers)
        if not response.ok:
            print(f"[LipSync Service ERROR] Sync Labs API submission failed: {response.text}")
            return video_path
            
        job_data = response.json()
        job_id = job_data.get("id")
        
        if not job_id:
            print("[LipSync Service ERROR] No job ID returned.")
            return video_path
            
        print(f"[LipSync Service] Job submitted successfully. ID: {job_id}")
        
        # 3. Polling Loop
        poll_url = f"{api_url}/{job_id}"
        max_retries = 60 # Polling every 5 seconds = 5 mins max
        for i in range(max_retries):
            poll_resp = requests.get(poll_url, headers=headers)
            if not poll_resp.ok:
                print(f"[LipSync Service ERROR] Polling failed: {poll_resp.text}")
                return video_path
                
            status_data = poll_resp.json()
            status = status_data.get("status")
            
            if status == "COMPLETED":
                result_url = status_data.get("outputUrl")
                if not result_url:
                    print("[LipSync Service ERROR] Job completed but no outputUrl returned.")
                    return video_path
                    
                print("[LipSync Service] Lip-sync complete! Downloading result...")
                
                # Download result
                download_resp = requests.get(result_url)
                if not download_resp.ok:
                    print("[LipSync Service ERROR] Failed to download result video.")
                    return video_path
                    
                output_path = os.path.join(tempfile.gettempdir(), f"synced_{uuid.uuid4().hex}.mp4")
                with open(output_path, "wb") as f:
                    f.write(download_resp.content)
                    
                return output_path
                
            elif status in ["FAILED", "REJECTED"]:
                print(f"[LipSync Service ERROR] Job failed on Sync Labs server. Status: {status}")
                return video_path
                
            print(f"[LipSync Service] Polling... Status: {status}")
            time.sleep(5)
            
        print("[LipSync Service ERROR] Polling timed out.")
        return video_path
        
    except Exception as e:
        print(f"[LipSync Service ERROR] Exception during lip-sync: {e}")
        return video_path
