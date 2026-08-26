"""
Repurposer Router
Video upload, AI analysis, and repurposing endpoints
"""
import os
import re
import json
import time
import uuid
import traceback
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Form, BackgroundTasks
from pydantic import BaseModel

from core.auth import get_current_user
from core.firestore_client import (
    get_user_profile, create_job, update_job_status,
    get_active_job_count, save_project
)
from core.storage_client import (
    generate_signed_upload_url, download_from_gcs, upload_to_gcs,
    UPLOAD_BUCKET
)
from core.plan_limits import get_plan_limits, enforce_rendering_params
from permissions import validate_feature_access
from services.ai_service import get_gemini_model
from config import TEMP_DIR

router = APIRouter()

# --- REQUEST MODELS ---
class AnalyzeRequest(BaseModel):
    youtube_url: str

class CutRequest(BaseModel):
    start_time: str
    end_time: str
    style: str = "Intense"
    caption_style: str = "bold_viral"
    subtitle_preset: str = "bold_viral"
    hook_boost: bool = False
    custom_hook_text: Optional[str] = None
    title: Optional[str] = None
    mode: str = "standard"
    gcs_path: Optional[str] = None
    resolution: int = 1080
    video_url: Optional[str] = None
    content_type: str = "podcast"
    layout_mode: str = "podcast_stack"
    min_width: int = 1080
    skip_captions: bool = False

# --- HELPERS ---
def parse_time(time_str: str) -> float:
    """Converts MM:SS or MM:SS.mmm to seconds (float)."""
    try:
        parts = time_str.replace(',', '.').split(':')
        if len(parts) == 2:
            m, s = parts
            return float(m) * 60 + float(s)
        elif len(parts) == 3:
            h, m, s = parts
            return float(h) * 3600 + float(m) * 60 + float(s)
        return 0.0
    except:
        return 0.0

# --- ENDPOINTS ---
@router.post("/get-upload-url")
def post_get_upload_url(
    filename: str = Form(...), 
    content_type: str = Form(...), 
    user_id: str = Depends(get_current_user)
):
    """Generates a Signed URL for direct PUT upload to GCS."""
    print(f"🔑 Generating Signed URL for: {filename}")
    try:
        result = generate_signed_upload_url(filename, content_type)
        return {"upload_url": result["upload_url"], "gcs_path": result["gcs_path"]}
    except Exception as e:
        print(f"Signed URL Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get-upload-url")
def get_upload_url_v2(
    filename: str, 
    content_type: str = "video/mp4", 
    user_id: str = Depends(get_current_user)
):
    """GET version of signed URL generation."""
    try:
        result = generate_signed_upload_url(filename, content_type)
        return {
            "upload_url": result["upload_url"],
            "public_uri": f"gs://{UPLOAD_BUCKET}/{result['gcs_path']}",
            "file_path": result["gcs_path"]
        }
    except Exception as e:
        print(f"Signed URL Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze-file-gcs")
async def analyze_file_gcs(
    gcs_path: str = Form(...),
    style: str = Form("Viral Mix"),
    content_type: str = Form("Podcast"),
    clip_length: str = Form("Medium"),
    user_id: str = Depends(get_current_user)
):
    """Downloads file from GCS and analyzes with Gemini 2.0 (Multimodal)."""
    print(f"--- Analyzing GCS File: {gcs_path} (Style: {style}, Type: {content_type}) ---")
    
    local_video_path = os.path.join(TEMP_DIR, os.path.basename(gcs_path))
    
    try:
        # 1. Download from GCS
        print("Downloading from GCS...")
        if not download_from_gcs(gcs_path, local_video_path):
            raise HTTPException(status_code=400, detail="Failed to download video from GCS")
        print("Download Complete.")

        # 2. Analyze with Gemini 2.0
        print("Sending VIDEO to Gemini 2.0 Flash (Multimodal)...")
        from google.genai import types
        
        model = get_gemini_model()
        gcs_uri = f"gs://{UPLOAD_BUCKET}/{gcs_path}"
        print(f"🔗 Video URI: {gcs_uri}")
        
        # Check if GCS client is available (either service account or ADC)
        from core.storage_client import get_storage_client
        gcs_client = None
        try:
            gcs_client = get_storage_client()
        except Exception as gcs_err:
            print(f"⚠️ GCS Client not available: {gcs_err}. Bypassing GCS upload.")
            
        if gcs_client:
            try:
                bucket = gcs_client.bucket(UPLOAD_BUCKET)
                blob = bucket.blob(gcs_path)
                if blob.exists():
                    video_part = types.Part.from_uri(file_uri=gcs_uri, mime_type="video/mp4")
                    print(f"✅ GCS Video Mode: Using GCS URI {gcs_uri}")
                else:
                    print(f"🔗 Blob {gcs_path} not in GCS. Fast-tracking Local Video Mode...")
                    gcs_client = None
            except Exception as verify_err:
                print(f"⚠️ GCS check failed: {verify_err}. Falling back to Local Video Mode.")
                gcs_client = None
                
        if not gcs_client:
            print(f"🔗 Local Video Mode. Reading {local_video_path} into memory...")
            with open(local_video_path, "rb") as f:
                video_bytes = f.read()
            video_part = types.Part.from_bytes(data=video_bytes, mime_type="video/mp4")
        
        # Duration logic
        min_sec, max_sec = 30, 60
        if clip_length == "Short":
            min_sec, max_sec = 15, 30
        if clip_length == "Long":
            min_sec, max_sec = 60, 90
        
        print(f"⏱️ Target Duration: {min_sec}-{max_sec}s")

        # Dynamic prompt based on content type
        specific_prompt = ""
        if content_type == "Podcast":
            specific_prompt = "Focus on DEEP CONTEXT. Find the setup, the realization, and the conclusion."
        elif content_type == "Comedy":
            specific_prompt = "Find the full joke structure: Setup -> Build -> Punchline -> Laughter."
        elif content_type == "Gaming":
            specific_prompt = "Focus on the full fail/win sequence. Context leads to better payoffs."
        elif content_type == "Vlog":
            specific_prompt = "Focus on the emotional peak of the story. Include the build-up."
        else:
            specific_prompt = "Focus on high retention moments with context."

        prompt = f"""
        You are a Retention-Focused Video Editor.
        Analyze this video to find HIGH-QUALITY segments suitable for Long-Form Shorts.
        
        **System Instructions:**
        {specific_prompt}
        
        **Universal Criteria:**
        - Clips must be physically continuous.
        - `end_time` > `start_time` (Min {min_sec}s, Max {max_sec}s).
        - Timestamps must be "MM:SS".
        
        **Strict Output Rules:**
        - Return strictly valid JSON.
        - Prioritize QUALITY over Quantity. Return 3-5 clips max.
        
        Return JSON: 
        [
            {{ 
                "title": "Compelling Title", 
                "start_time": "MM:SS", 
                "end_time": "MM:SS", 
                "virality_score": 9, 
                "reason": "Clear setup and payoff.",
                "hooks": [
                    "A Controversial/Curiosity Hook",
                    "A Question Hook",
                    "A Direct Value Hook"
                ]
            }}
        ]
        """
        
        # Generate with retry & network connection recovery
        response = None
        for attempt in range(3):
            try:
                if attempt > 0:
                    model = get_gemini_model()  # Reset gRPC channels on retry
                response = model.generate_content([prompt, video_part])
                break
            except Exception as e:
                print(f"Gemini attempt {attempt + 1} failed: {e}")
                # If GCS gRPC stream failed due to socket/network drop, switch to local payload
                if any(err_kw in str(e) for err_kw in ["503", "UNAVAILABLE", "Connection", "socket", "WSA"]):
                    if os.path.exists(local_video_path):
                        print("🔄 Network drop detected. Fast-switching to Local Data Payload...")
                        try:
                            from google.genai import types
                            with open(local_video_path, "rb") as f:
                                video_bytes = f.read()
                            video_part = types.Part.from_bytes(data=video_bytes, mime_type="video/mp4")
                        except Exception as read_err:
                            print(f"Failed to read local fallback video: {read_err}")
                time.sleep(3 * (attempt + 1))
        
        if not response:
            raise HTTPException(status_code=500, detail="Failed to analyze video after retries")
        
        # Parse response
        try:
            text = response.text.replace('```json', '').replace('```', '').strip()
        except ValueError as val_err:
            print(f"❌ Gemini Response Error (likely blocked by safety/recitation filters): {val_err}")
            block_reason = "Blocked by safety/recitation filters"
            if response.candidates:
                candidate = response.candidates[0]
                finish_reason = getattr(candidate, 'finish_reason', None)
                if finish_reason:
                    finish_reason_str = str(finish_reason)
                    block_reason = f"Blocked: finish_reason={finish_reason_str}"
                    print(f"⚠️ Candidate finish reason: {finish_reason_str}")
            raise HTTPException(
                status_code=400,
                detail=f"The video analysis was blocked by Gemini. Reason: {block_reason}. This usually happens when the video contains copyrighted music, religious poems/recitations, or flagged content."
            )
        
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            text = match.group(0)
        
        try:
            viral_clips = json.loads(text)
        except json.JSONDecodeError:
            print(f"JSON Parse Error: {text}")
            viral_clips = []
        
        # Sort and limit
        viral_clips.sort(key=lambda x: x.get('virality_score', 0), reverse=True)
        viral_clips = viral_clips[:5]

        return {"viral_clips": viral_clips}

    except HTTPException:
        raise
    except Exception as e:
        print(f"GCS Analysis Failed: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


    
def process_repurpose_video(job_id: str, user_id: str, request: CutRequest, video_path: str):
    """Background task to process the video repurposing."""
    try:
        start_seconds = parse_time(request.start_time)
        end_seconds = parse_time(request.end_time)
        
        # Auto-correction
        if start_seconds > end_seconds:
            start_seconds, end_seconds = end_seconds, start_seconds
        
        # Load Video
        from moviepy.editor import VideoFileClip
        clip = VideoFileClip(video_path)
        video_duration = clip.duration
        
        # Safety bounds
        if end_seconds > video_duration:
            end_seconds = video_duration
        if start_seconds >= video_duration:
            start_seconds = 0
            end_seconds = min(30.0, video_duration)
        
        # Cap at 60s
        if (end_seconds - start_seconds) > 60.0:
            end_seconds = start_seconds + 60.0
            
        final_duration_mins = (end_seconds - start_seconds) / 60.0
        COST_PER_MIN = 5 
        credits_cost = max(1, int(final_duration_mins * COST_PER_MIN))
        
        profile_data = get_user_profile(user_id)
        user_plan = profile_data.get('plan', 'starter')
        
        # Update job to 'processing' (it was 'pending')
        update_job_status(user_id, job_id, "processing")
        
        safe_height, needs_watermark = enforce_rendering_params(user_plan, 1280)
        
        # Cut Segment
        cut_clip = clip.subclip(start_seconds, end_seconds)
        
        # Set target dimensions for shorts
        target_w, target_h = 1080, 1920
        
        # Apply Smart Crop
        try:
            from viral_editor import apply_smart_crop
            cropped_result = apply_smart_crop(cut_clip, mode=request.mode, target_width=target_w, target_height=target_h)
            
            if cropped_result is not None:
                cut_clip = cropped_result
            else:
                raise Exception("Smart crop returned None")
        except Exception as e_cut:
            print(f"⚠️ Smart Crop Failed: {e_cut}. Fallback to center crop.")
            # Fallback center crop
            w, h = cut_clip.size
            source_ratio = w / h
            target_ratio = target_w / target_h
            
            if source_ratio > target_ratio:
                new_width = int(h * target_ratio)
                x1 = (w - new_width) // 2
                cut_clip = cut_clip.crop(x1=x1, width=new_width, height=h)
            else:
                new_height = int(w / target_ratio)
                y1 = (h - new_height) // 2
                cut_clip = cut_clip.crop(y1=y1, width=w, height=new_height)
            
            cut_clip = cut_clip.resize((target_w, target_h))

        # --- B-ROLL INJECTION (The OpusClip Killer) ---
        # Inject B-Roll at t=2.0s for 2.5 seconds to break visual monotony
        try:
            if cut_clip.duration > 5.0 and request.title:
                from viral_editor import batch_download_videos
                print(f"🎬 Injecting AI B-Roll for topic: {request.title}")
                b_roll_paths = batch_download_videos([request.title], min_width=1080)
                
                if b_roll_paths and len(b_roll_paths) > 0:
                    from moviepy.editor import VideoFileClip, CompositeVideoClip
                    b_roll = VideoFileClip(b_roll_paths[0])
                    
                    # Trim B-Roll to 2.5s
                    b_duration = min(2.5, b_roll.duration)
                    b_roll = b_roll.subclip(0, b_duration)
                    
                    # Resize B-Roll to fit portrait target
                    if b_roll.w > target_w:
                        b_roll = b_roll.resize(width=target_w)
                    if b_roll.h < target_h:
                        b_roll = b_roll.resize(height=target_h)
                    b_crop_x = (b_roll.w - target_w) / 2
                    b_crop_y = (b_roll.h - target_h) / 2
                    b_roll = b_roll.crop(x1=b_crop_x, y1=b_crop_y, width=target_w, height=target_h)
                    
                    # Start B-Roll at t=2.0s
                    b_roll = b_roll.set_start(2.0).without_audio()
                    
                    # Composite
                    cut_clip = CompositeVideoClip([cut_clip, b_roll])
                    print("✅ B-Roll injected successfully.")
        except Exception as e_broll:
            print(f"⚠️ B-Roll injection failed, continuing without it: {e_broll}")

        temp_cut_path = os.path.join(TEMP_DIR, f"temp_viral_cut_{job_id}.mp4")
        cut_clip.write_videofile(temp_cut_path, codec="libx264", audio_codec="aac", preset="ultrafast", logger=None)
        
        clip.close()
        cut_clip.close()
        
        # Add Captions (unless user opted to skip)
        if request.skip_captions:
            print("⏭️ Skipping captions (user opted out — video may already have captions)")
            output_path = temp_cut_path  # Use the cut video directly
        else:
            print(f"Adding Animated Captions ({request.subtitle_preset})...")
            output_path = os.path.join(TEMP_DIR, f"viral_captioned_{job_id}.mp4")
            
            from viral_editor import add_viral_captions
            
            preset = request.subtitle_preset
            if request.caption_style and request.caption_style != "bold_viral":
                if request.caption_style.lower() == "hormozi":
                    preset = "bold_viral"
                elif request.caption_style.lower() == "clean":
                    preset = "podcast_clean"
            
            brand_kit = profile_data.get("brand_kit") if profile_data else None
                    
            add_viral_captions(
                temp_cut_path, 
                output_path, 
                subtitle_preset=preset, 
                hook_boost=request.hook_boost, 
                platform="shorts", 
                brand_kit=brand_kit, 
                custom_hook_text=request.custom_hook_text,
                headline_text=request.title,
                use_progress_bar=True
            )
        
        # Validate Output
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise Exception("Video generation produced an empty file.")

        print(f"✅ Generated Video Size: {os.path.getsize(output_path)} bytes")
        
        # Upload
        unique_filename = f"viral_{uuid.uuid4().hex[:8]}.mp4"
        cloud_url = upload_to_gcs(output_path, f"viral_shorts/{unique_filename}")
        
        if not cloud_url:
            raise Exception("Upload failed")
        
        print(f"✅ Final Public URL: {cloud_url}")
        
        # Save Record
        save_project(user_id, f"Viral Short ({request.style})", "repurpose", cloud_url, f"Style: {request.style}")
        
        # Deduct Credits
        try:
            from services.credit_service import complete_job_and_deduct
            complete_job_and_deduct(user_id, job_id, credits_cost, "repurposer_cut")
        except Exception as e:
            print(f"Credit deduction warning: {e}")
            
        update_job_status(user_id, job_id, "completed", result_url=cloud_url)

        # Cleanup
        try:
            if temp_cut_path != output_path:
                os.remove(temp_cut_path)
            os.remove(output_path)
        except:
            pass

    except Exception as e:
        print(f"Background Processing Error: {e}")
        traceback.print_exc()
        update_job_status(user_id, job_id, "failed", error_msg=str(e))

@router.post("/repurpose-video")
def repurpose_video(request: CutRequest, background_tasks: BackgroundTasks, user_id: str = Depends(get_current_user)):
    """Cut, crop, and caption a video segment in the background."""
    print(f"--- Repurposing Video: {request.start_time} to {request.end_time} ---")
    
    # 0. GATEKEEPER CHECK
    profile, plan_config = validate_feature_access(user_id, 'repurposer_basic')

    # Gate: Smart Face Tracking
    if request.mode in ('smart_solo', 'content_fit'):
        if not plan_config.get('repurposer_smart_crop', False):
            raise HTTPException(
                status_code=403, 
                detail="Smart Face Tracking is a Creator feature. Please upgrade."
            )

    if not request.gcs_path:
        raise HTTPException(status_code=400, detail="No uploaded video found. Please upload first.")

    video_path = os.path.join(TEMP_DIR, os.path.basename(request.gcs_path))
    
    # Stateless Recovery
    if not os.path.exists(video_path) or os.path.getsize(video_path) < 1000:
        print(f"🔄 Re-downloading from GCS: {request.gcs_path}")
        if not download_from_gcs(request.gcs_path, video_path):
            raise HTTPException(status_code=400, detail="Failed to download video")
            
    # Calculate duration/costs upfront
    start_seconds = parse_time(request.start_time)
    end_seconds = parse_time(request.end_time)
    if start_seconds > end_seconds:
        start_seconds, end_seconds = end_seconds, start_seconds
    if (end_seconds - start_seconds) > 60.0:
        end_seconds = start_seconds + 60.0
    final_duration_mins = (end_seconds - start_seconds) / 60.0
    COST_PER_MIN = 5 
    credits_cost = max(1, int(final_duration_mins * COST_PER_MIN))
    
    profile_data = get_user_profile(user_id)
    user_plan = profile_data.get('plan', 'starter')
    active_jobs = get_active_job_count(user_id)
    plan_limits = get_plan_limits(user_plan)
    
    if active_jobs >= plan_limits['concurrent']:
        raise HTTPException(
            status_code=429, 
            detail=f"Concurrency Limit Reached. Plan allows {plan_limits['concurrent']} jobs."
        )

    # Check export permission
    if not plan_limits.get('allow_export', True):
        raise HTTPException(
            status_code=403, 
            detail="Free Preview Mode: Upgrade to Export."
        )

    job_id = create_job(user_id, "repurpose_video", metadata={"credits_cost": credits_cost})
    
    # Dispatch Background Task
    background_tasks.add_task(process_repurpose_video, job_id, user_id, request, video_path)
    
    return {"status": "processing", "job_id": job_id}
