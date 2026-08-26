"""
Dubbing Router
Video dubbing, voiceover generation, and voice cloning endpoints
"""
import os
import uuid
import time
import shutil
import traceback

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from core.auth import get_current_user
from core.firestore_client import (
    get_user_profile, create_job, update_job_status,
    get_active_job_count
)
from core.storage_client import (
    upload_to_gcs, upload_file, download_from_gcs
)
from core.plan_limits import get_plan_limits, enforce_rendering_params
from permissions import validate_feature_access
from tts_service import GoogleTTSClient
from config import TEMP_DIR

router = APIRouter()

# --- REQUEST MODELS ---
class VoiceoverRequest(BaseModel):
    text: str
    voice_name: str = "en-US-Journey-D"

# --- ENDPOINTS ---
@router.post("/generate-voiceover")
async def generate_voiceover(request: VoiceoverRequest, user_id: str = Depends(get_current_user)):
    """Generate TTS voiceover audio."""
    try:
        print(f"🎤 Generating Voiceover: {request.text[:50]}... ({request.voice_name})")
        
        # Handle CLONED VOICE (Mock)
        voice_name = request.voice_name
        if voice_name and voice_name.startswith("cloned_"):
            print("🧬 Using Cloned Voice Model (Mock Mode)")
            voice_name = "en-US-Journey-F"

        # Generate Audio
        tts_client = GoogleTTSClient()
        mp3_path = tts_client.generate_audio(request.text, voice_name)
        
        # Upload to Firebase
        print(f"Uploading {mp3_path} to Firebase...")
        audio_url = upload_file(mp3_path, folder="voiceovers")
        
        # Cleanup
        try:
            os.remove(mp3_path)
        except:
            pass

        if not audio_url:
            raise Exception("Failed to upload audio to Firebase")

        return {"audio_url": audio_url}

    except Exception as e:
        print(f"❌ Error generating voiceover: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clone-voice")
async def clone_voice(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user)
):
    """Voice cloning endpoint (Premium Architecture)."""
    print(f"🧬 Cloning Voice for User: {user_id}")
    
    try:
        # Check plan
        profile, plan_config = validate_feature_access(user_id, 'dubbing')
        if not plan_config.get('premium_voices', False):
            raise HTTPException(status_code=403, detail="Voice cloning requires a Pro/Creator plan.")

        # Save File (Simulated Analysis)
        temp_path = os.path.join(TEMP_DIR, f"temp_clone_{uuid.uuid4()}.mp3")
        with open(temp_path, "wb") as f:
            f.write(file.file.read())
            
        print("🧠 Analyzing voice characteristics (Deepfake Model)...")
        time.sleep(2)  # Simulated processing
        
        # Cleanup
        os.remove(temp_path)
        
        # Return Mock Voice ID
        mock_voice_id = f"cloned_{user_id}_{uuid.uuid4().hex[:4]}"
        
        # Save to user profile (Simulated DB update)
        try:
            from core.firestore_client import db
            if db:
                user_ref = db.collection('users').document(user_id)
                user_doc = user_ref.get()
                if user_doc.exists:
                    voices = user_doc.to_dict().get("custom_voices", [])
                    voices.append({"id": mock_voice_id, "name": f"My Cloned Voice ({file.filename})", "status": "active"})
                    user_ref.update({"custom_voices": voices})
        except Exception as e_db:
            print(f"⚠️ Could not save custom voice to DB: {e_db}")
        
        return {"voice_id": mock_voice_id, "status": "active", "message": "Voice successfully cloned and added to your profile."}
        
    except Exception as e:
        print(f"Cloning Failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.post("/analyze-vision")
async def analyze_vision(
    file: UploadFile = File(...),
    video_format: str = Form("TikTok"),
    duration: str = Form("30 seconds"),
    mood: str = Form("Viral"),
    user_id: str = Depends(get_current_user)
):
    """Analyze video with Gemini 2.0 vision."""
    temp_input_path = os.path.join(TEMP_DIR, f"temp_analyze_{uuid.uuid4()}.mp4")
    try:
        print(f"👁️ Receiving Video for Analysis: {file.filename} [{video_format}, {duration}, {mood}]")
        
        # Save Uploaded Video
        with open(temp_input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Call Vision Service
        from vision_service import VideoAnalyzer
        analyzer = VideoAnalyzer()
        script = analyzer.generate_script(temp_input_path, video_format, duration, mood)
        
        # Cleanup
        if os.path.exists(temp_input_path):
            os.remove(temp_input_path)
            
        return JSONResponse(content={"script": script})

    except Exception as e:
        print(f"❌ Analysis Failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.post("/merge-video-audio")
async def merge_video_audio(
    video_file: UploadFile = File(...), 
    audio_url: str = Form(...),
    user_id: str = Depends(get_current_user)
):
    """Merge video with new audio track."""
    unique_id = uuid.uuid4()
    temp_video = os.path.join(TEMP_DIR, f"temp_merge_v_{unique_id}.mp4")
    temp_audio = os.path.join(TEMP_DIR, f"temp_merge_a_{unique_id}.mp3")
    final_output = os.path.join(TEMP_DIR, f"final_output_{unique_id}.mp4")
    
    try:
        print(f"🎬 Merging Video + Audio: {video_file.filename}")
        
        # Save Video
        with open(temp_video, "wb") as buffer:
            shutil.copyfileobj(video_file.file, buffer)
            
        # Download Audio with SSRF Protection
        from core.security import safe_download_stream, SSRFValidationError
        try:
            safe_download_stream(
                url=audio_url,
                destination_path=temp_audio,
                max_bytes=25 * 1024 * 1024,  # 25 MB max audio
                allowed_content_types=["audio/mpeg", "audio/mp3", "audio/wav", "audio/aac", "audio/x-m4a", "audio/mp4", "application/octet-stream"]
            )
        except SSRFValidationError as ssrf_err:
            raise HTTPException(status_code=400, detail=f"Invalid audio URL: {str(ssrf_err)}")
                
        # Processing
        from moviepy.editor import VideoFileClip, AudioFileClip
        clip = VideoFileClip(temp_video)
        audio = AudioFileClip(temp_audio)
        
        # Trim Audio to Match Video
        final_audio = audio.subclip(0, min(audio.duration, clip.duration))
        final_clip = clip.set_audio(final_audio)
        
        # Write Output
        final_clip.write_videofile(final_output, codec="libx264", audio_codec="aac")
        
        # Cleanup Resources
        clip.close()
        audio.close()
        final_clip.close()
        
        # Upload
        cloud_url = upload_file(final_output, folder="final_creations")
        print(f"✅ Merge Success: {cloud_url}")
        
        return {"final_url": cloud_url}

    except Exception as e:
        print(f"❌ Merge Failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
        
    finally:
        # Cleanup
        for f in [temp_video, temp_audio, final_output]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass

@router.post("/dub-video")
async def dub_video_endpoint(
    file: UploadFile = File(None),
    gcs_uri: str = Form(None),
    voice_name: str = Form(...), 
    target_lang: str = Form('es'),
    sync_mode: str = Form('audio'),
    is_preview: bool = Form(False),
    user_id: str = Depends(get_current_user)
):
    """Translate and dub video to target language."""
    print(f"🎤 Dub Video -> {target_lang} ({voice_name}) | Mode: {sync_mode} | Preview: {is_preview}")

    if not file and not gcs_uri:
        raise HTTPException(status_code=400, detail="No file or GCS URI provided.")
    
    # GATEKEEPER CHECK
    profile, plan_config = validate_feature_access(user_id, 'dubbing')
    
    user_plan = profile.get('plan', 'starter')
    plan_limits = get_plan_limits(user_plan)
    
    # Non-subscriber gate
    if not is_preview and not plan_limits.get('allow_export', True):
        raise HTTPException(
            status_code=403, 
            detail="Free Preview Mode: Upgrade to Export. Only 15s previews are allowed."
        )

    # Premium voices gate
    if "Journey" in voice_name or "cloned" in voice_name:
        if not plan_config.get('premium_voices', False):
            raise HTTPException(
                status_code=403, 
                detail="Premium/Cloned voices are locked. Please upgrade."
            )

    # Save Input
    unique_id = str(uuid.uuid4())
    temp_input = os.path.join(TEMP_DIR, f"temp_dub_input_{unique_id}.mp4")
    
    if file:
        with open(temp_input, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    elif gcs_uri:
        try:
            print(f"☁️ Downloading from GCS: {gcs_uri}")
            if not gcs_uri.startswith("gs://"):
                raise Exception("Invalid GCS URI (must start with gs://)")
                
            parts = gcs_uri.replace("gs://", "").split("/")
            bucket_name = parts[0]
            blob_name = "/".join(parts[1:])
            
            if not download_from_gcs(blob_name, temp_input, bucket_name=bucket_name):
                raise Exception("Failed to download or fallback video")
            print("✅ Download Complete")
        except Exception as e_dl:
            raise HTTPException(status_code=400, detail=f"Failed to download GCS file: {str(e_dl)}")
    
    # JOB CREATION
    job_id = None
    estimated_cost = 0
    
    if not is_preview:
        # Concurrency check
        profile_data = get_user_profile(user_id)
        active_jobs = get_active_job_count(user_id)
        
        if active_jobs >= plan_limits['concurrent']:
            if os.path.exists(temp_input):
                os.remove(temp_input)
            raise HTTPException(
                status_code=429, 
                detail=f"Concurrency Limit Reached. Plan allows {plan_limits['concurrent']} jobs."
            )

        job_id = create_job(user_id, "dubbing", metadata={"target_lang": target_lang, "voice": voice_name})
        
        try:
            from moviepy.editor import VideoFileClip
            check_clip = VideoFileClip(temp_input)
            duration_mins = check_clip.duration / 60.0
            check_clip.close()
            
            COST_PER_MIN = 10
            estimated_cost = max(1, int(duration_mins * COST_PER_MIN))
            
            balance = profile_data.get('credits', 0) if profile_data else 0
            
            if balance < estimated_cost:
                update_job_status(user_id, job_id, "failed_funds")
                if os.path.exists(temp_input):
                    os.remove(temp_input)
                raise HTTPException(
                    status_code=402, 
                    detail=f"Insufficient Credits. Need {estimated_cost}, Have {balance}"
                )

        except HTTPException:
            raise
        except Exception as e_prep:
            print(f"Dubbing Prep Failed: {e_prep}")
            if job_id:
                update_job_status(user_id, job_id, "failed_prep")
            if os.path.exists(temp_input):
                os.remove(temp_input)
            raise HTTPException(status_code=500, detail="Preparation Failed")
    
    # Preview: Trim to 15s
    if is_preview:
        print("✂️ Creating 15s Preview Clip...")
        try:
            from moviepy.editor import VideoFileClip
            preview_input = os.path.join(TEMP_DIR, f"temp_dub_preview_{unique_id}.mp4")
            clip = VideoFileClip(temp_input)
            end_time = min(15.0, clip.duration)
            preview_clip = clip.subclip(0, end_time)
            preview_clip.write_videofile(preview_input, codec="libx264", audio_codec="aac", logger=None)
            clip.close()
            preview_clip.close()
            
            os.remove(temp_input)
            temp_input = preview_input
            print(f"✅ Preview Clip Ready: {temp_input}")
        except Exception as e_trim:
            print(f"⚠️ Preview Trim Failed: {e_trim}")

    try:
        # Run Dubbing
        from dubbing_service import VideoDubber
        dubber = VideoDubber()
        
        safe_height, needs_watermark = enforce_rendering_params(user_plan, 1080)

        dubbed_video_path, dubbed_audio_path = dubber.dub_video(
            temp_input, 
            target_lang, 
            voice_name, 
            resolution=safe_height, 
            watermark=needs_watermark
        )
        
        if not dubbed_video_path or not dubbed_audio_path:
            if os.path.exists(temp_input):
                os.remove(temp_input)
            raise HTTPException(status_code=500, detail="Dubbing Service returned None")

        final_video_url = None
        audio_cloud_url = None
        
        # Handle Sync Mode
        if sync_mode == 'lipsync':
            print("👄 Lip Sync Requested...")
            original_url = upload_to_gcs(temp_input, f"dubbing/original_{unique_id}.mp4")
            audio_url = upload_to_gcs(dubbed_audio_path, f"dubbing/audio_{unique_id}.mp3")
            
            if not original_url or not audio_url:
                raise HTTPException(status_code=500, detail="Failed to upload assets for Lip Sync")

            try:
                from services.lipsync_service import sync_lips
                final_video_url = sync_lips(original_url, audio_url)
                audio_cloud_url = audio_url
            except Exception as e_ls:
                print(f"❌ Lip Sync Failed: {e_ls}")
                raise HTTPException(status_code=500, detail=f"Lip Sync Service Failed: {str(e_ls)}")
        else:
            # Audio Sync (Standard)
            print("🔉 Audio Sync Mode. Uploading local result.")
            final_video_url = upload_to_gcs(dubbed_video_path, f"dubbed_videos/audio_sync_{unique_id}.mp4")
            audio_cloud_url = upload_to_gcs(dubbed_audio_path, f"dubbed_audios/audio_{unique_id}.mp3")

        # Credit Deduction
        if not is_preview and job_id:
            try:
                from services.credit_service import complete_job_and_deduct
                complete_job_and_deduct(user_id, job_id, estimated_cost, "dubbing")
            except Exception as e:
                print(f"Credit deduction warning: {e}")

        # Cleanup
        try:
            if os.path.exists(temp_input):
                os.remove(temp_input)
            if dubbed_video_path and os.path.exists(dubbed_video_path):
                os.remove(dubbed_video_path)
            if dubbed_audio_path and os.path.exists(dubbed_audio_path):
                os.remove(dubbed_audio_path)
        except:
            pass
        
        return JSONResponse(content={
            "status": "success",
            "video_url": final_video_url, 
            "audio_url": audio_cloud_url,
            "preview": is_preview
        })

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Dubbing Endpoint Error: {e}")
        if job_id and not is_preview:
            update_job_status(user_id, job_id, "failed", error_msg=str(e))
        traceback.print_exc()
        if os.path.exists(temp_input):
            try:
                os.remove(temp_input)
            except:
                pass
        raise HTTPException(status_code=500, detail=str(e))
