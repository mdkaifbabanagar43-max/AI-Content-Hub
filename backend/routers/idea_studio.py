"""
Idea Studio Router
Brainstorm, script generation, preview, and video rendering endpoints
"""
import os
import re
import json
import base64
import uuid
import traceback
import itertools
import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Any

from core.auth import get_current_user
from core.firestore_client import (
    get_user_profile, create_job, update_job_status, 
    get_active_job_count, db
)
from core.storage_client import upload_to_gcs, UPLOAD_BUCKET
from core.plan_limits import get_plan_limits, enforce_rendering_params
from config import PLAN_CAPABILITIES
from permissions import validate_feature_access
from services.ai_service import (
    generate_brainstorm_angles, generate_video_ideas,
    generate_script_and_visuals, get_gemini_model, clean_script_for_tts
)
from tts_service import GoogleTTSClient

router = APIRouter()

# --- REQUEST MODELS ---
class IdeaRequest(BaseModel):
    topic: str
    language: str = "English"
    content_type: str = "educational"  # NEW

class BrainstormRequest(BaseModel):
    topic: str
    language: str = "English"
    content_type: str = "educational"  # NEW

class ProductionRequest(BaseModel):
    title: str
    hook: str = ""
    platform: str = "tiktok"
    duration: str = "30s"
    mood: str = "informative"
    voice_name: str = "en-US-Journey-D"
    language: str = "English"
    content_type: str = "educational"  # NEW
    script: Optional[str] = None
    visual_style: str = "Cinematic"
    bgm_style: str = "Epic"

class FinalRenderRequest(BaseModel):
    script: str = ""
    audio_base64: Optional[str] = None
    visual_plan: Any = None
    scenes: Any = None  # NEW: Scene metadata from frontend
    user_id: str = ""
    topic: str = "Untitled"
    mood: str = "informative"
    platform: str = "tiktok"
    content_type: str = "educational"  # NEW
    visual_style: str = "Cinematic"
    bgm_style: str = "Epic"

    class Config:
        extra = "allow"


class RenderRequest(BaseModel):
    audio_base64: str
    pexels_search_term: str
    script: str
    platform: str = "tiktok"
    visual_plan: List[str] = []
    user_id: str = "demo_user"
    topic: str = "Untitled Project"
    mood: str = "Viral"
    thumbnail_url: str = ""
    subtitle_preset: str = "bold_viral"
    hook_boost: bool = False

# --- ENDPOINTS ---
@router.post("/brainstorm")
def brainstorm_angles(request: BrainstormRequest, user_id: str = Depends(get_current_user)):
    """Generate 4 viral content angles for a topic."""
    print(f"🧠 Brainstorming angles for: {request.topic}")
    return generate_brainstorm_angles(request.topic, request.language)

@router.post("/generate-ideas")
def generate_ideas(request: IdeaRequest, user_id: str = Depends(get_current_user)):
    """Generate 5 high-CTR video concepts."""
    print(f"Received idea request for topic: {request.topic}")
    try:
        ideas_text = generate_video_ideas(request.topic, request.language)
        print(f"AI Response: {ideas_text[:100]}...")
        return {"ideas": ideas_text}
    except Exception as e:
        print(f"Error generating ideas: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

class NovaReelRequest(BaseModel):
    topic: str
    voice_name: str = "en-US-Journey-D"

@router.post("/generate-nova-reel")
def generate_nova_reel(request: NovaReelRequest, user_id: str = Depends(get_current_user)):
    """Generate a 30s video using Amazon Nova Reel and Google TTS."""
    print(f"🎬 Generating Nova Reel (30s) for topic: {request.topic}")
    
    # 1. Generate Script and 5 Visual Prompts (Segmented for Perfect Sync)
    prompt = f"""
    Write a 30-second educational/viral video script about: "{request.topic}".
    The script should be exactly 70-80 words total.
    You MUST divide the script chronologically into exactly 5 logical segments (about 12-16 words each).
    For EACH of the 5 segments, provide the spoken text AND a highly descriptive, cinematic visual prompt for a text-to-video AI that PERFECTLY matches what is being spoken in that specific segment.
    Output ONLY valid JSON in this exact format:
    {{
      "segments": [
        {{
          "text": "The spoken text for segment 1...",
          "visual_prompt": "Cinematic shot of..."
        }},
        ... (exactly 5 segments total)
      ]
    }}
    """
    try:
        model = get_gemini_model()
        response = model.generate_content(prompt)
        text = response.text.replace('```json', '').replace('```', '').strip()
        data = json.loads(text)
        
        segments = data.get('segments', [])
        
        # Ensure exactly 5 segments
        while len(segments) < 5:
            segments.append(segments[-1] if segments else {"text": "And that's it!", "visual_prompt": "Cinematic abstract background"})
            
        segments = segments[:5]
        
        script = " ".join([seg['text'] for seg in segments])
        prompts = [seg['visual_prompt'] for seg in segments]
            
        print(f"✅ Generated Script: {script[:50]}...")
        print(f"✅ Generated {len(prompts)} visual prompts perfectly synced.")
    except Exception as e:
        print(f"Failed to generate script/prompts: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate AI script and prompts.")
    from services.video_service import generate_nova_reel_clip
    
    clips_paths = []
    import concurrent.futures
    
    print("⏳ Starting parallel Nova Reel generation (5 clips, ~3-5 mins)...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        try:
            # executor.map returns results in the exact order of the prompts list
            clips_paths = list(executor.map(generate_nova_reel_clip, prompts))
            print(f"✅ Generated 5 Nova Reel clips in order: {clips_paths}")
        except Exception as exc:
            print(f"❌ Nova Reel generation failed: {exc}")
            raise HTTPException(status_code=500, detail=f"AWS Nova Reel failed: {exc}")
                
    if len(clips_paths) < 5:
        raise HTTPException(status_code=500, detail="Failed to generate all 5 clips.")
        
    # 3. Generate TTS Audio
    print("🎤 Generating TTS Voiceover...")
    tts_client = GoogleTTSClient()
    clean_script = clean_script_for_tts(script)
    audio_path = tts_client.generate_audio(clean_script, voice_name=request.voice_name)
    print("✅ TTS Voiceover generated.")
    
    # 4. Concatenate Video Clips & Add Audio
    print("🎬 Stitching video clips and audio...")
    from viral_editor import get_moviepy, add_viral_captions
    mp = get_moviepy()
    VideoFileClip = mp["VideoFileClip"]
    AudioFileClip = mp["AudioFileClip"]
    concatenate_videoclips = mp["concatenate_videoclips"]
    
    video_clips = [VideoFileClip(p) for p in clips_paths]
    final_video = concatenate_videoclips(video_clips, method="compose")
    
    tts_audio = AudioFileClip(audio_path)
    
    # Trim the video to end exactly when the audio ends (or vice versa)
    min_duration = min(final_video.duration, tts_audio.duration)
    final_video = final_video.subclip(0, min_duration)
    
    final_video = final_video.set_audio(tts_audio.subclip(0, min_duration))
    
    # Export raw stitched video
    temp_stitched_path = f"/app/temp/nova_stitched_{uuid.uuid4().hex}.mp4"
    final_video.write_videofile(temp_stitched_path, fps=24, codec="libx264", audio_codec="aac")
    
    # Cleanup clips
    for vc in video_clips: vc.close()
    tts_audio.close()
    final_video.close()
    
    # 5. Add Viral Captions
    final_output_path = f"/app/temp/nova_final_{uuid.uuid4().hex}.mp4"
    print("💬 Adding Viral Captions...")
    add_viral_captions(temp_stitched_path, final_output_path, "bold_viral", script, "Podcast")
    
    # 6. Upload to Storage
    print("☁️ Uploading to Storage...")
    public_url = upload_to_gcs(final_output_path, "nova_reels")
    
    print(f"🎉 Final Video URL: {public_url}")
    return {"url": public_url, "script": script}
    
@router.post("/generate-script-preview")
def generate_script_preview(request: ProductionRequest, user_id: str = Depends(get_current_user)):
    """Generate script preview with voiceover and visual plan."""
    print(f"📝 Generating Script Preview for: {request.title}")
    
    try:
        script_data = generate_script_and_visuals(
            title=request.title,
            hook=request.hook,
            platform=request.platform,
            duration=request.duration,
            mood=request.mood,
            voice_name=request.voice_name,
            language=request.language,
            visual_style=request.visual_style
        )
        
        print(f"RAW SCRIPT DATA: {json.dumps(script_data)}")
        
        voiceover_text = script_data.get("voiceover", "") or script_data.get("script", "")
        
        return {
            "title": script_data.get("title", request.title),
            "script": voiceover_text,
            "visual_plan": script_data.get("visual_plan", []),
            "voiceover": voiceover_text
        }
    except Exception as e:
        print(f"Script Gen Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/produce-video-assets")
def produce_video_assets(request: ProductionRequest, user_id: str = Depends(get_current_user)):
    """Generate script, visuals, and TTS audio."""
    print(f"--- Production Request Started: {request.title} ---")
    
    try:
        language = request.language
        if language and "hindi" in language.lower():
            language = "Hinglish (Conversational Hindi + English)"

        voiceover_text = ""
        visual_plan = []

        # PATH A: USER PROVIDED SCRIPT
        if request.script and len(request.script) > 10:
            print("✅ Using User-Edited Script...")
            voiceover_text = request.script
            
            # Try Scene Engine
            try:
                from services.scene_engine import scene_engine
                if scene_engine:
                    visual_plan = scene_engine.analyze_script(voiceover_text)
                else:
                    visual_plan = [request.title]
            except Exception:
                visual_plan = [request.title]
        
        # PATH B: LLM GENERATION
        else:
            print("Generating Script & Search Term from Scratch...")
            script_data = generate_script_and_visuals(
                title=request.title,
                platform=request.platform,
                duration=request.duration,
                mood=request.mood,
                voice_name=request.voice_name,
                language=language,
                visual_style=request.visual_style
            )
            voiceover_text = script_data.get("voiceover", "")
            visual_plan = script_data.get("visual_plan", [])
            scenes = script_data.get("scenes", [])

        # --- GENERATE AUDIO (TTS) ---
        audio_base64 = None
        
        if voiceover_text:
            print(f"Main TTS: Generating audio for: {voiceover_text[:50]}...")
            voiceover_text = clean_script_for_tts(voiceover_text)
            
            try:
                tts_client = GoogleTTSClient()
                audio_path = tts_client.generate_audio(voiceover_text, voice_name=request.voice_name)
                
                with open(audio_path, "rb") as audio_file:
                    audio_base64 = base64.b64encode(audio_file.read()).decode("utf-8")
                
                os.remove(audio_path)
                print("Audio Generated & Encoded Successfully.")

            except Exception as e:
                print(f"TTS Service Failed: {e}")
                traceback.print_exc()

        return {
            "title": request.title,
            "script": voiceover_text,
            "voiceover": voiceover_text,
            "visual_plan": visual_plan,
            "scenes": scenes if 'scenes' in locals() else [],
            "audio_base64": audio_base64
        }

    except Exception as e:
        print(f"Production Failed: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/render-final")
def render_final(request: FinalRenderRequest, user_id: str = Depends(get_current_user)):
    """Full video render with credits deduction."""
    print(f"🎬 Starting Final Render for: {request.topic} (User: {user_id})")
    print(f"📦 Request Data: script_len={len(request.script or '')}, audio_present={request.audio_base64 is not None}, visual_plan_len={len(request.visual_plan or [])}")
    
    # Validate required fields (runtime check for better error messages)
    if not request.audio_base64:
        raise HTTPException(status_code=400, detail="Missing audio_base64 - TTS generation may have failed")
    
    if not request.script:
        raise HTTPException(status_code=400, detail="Missing script text")
    
    # Set defaults for optional fields
    if request.visual_plan is None:
        request.visual_plan = [request.topic or "video content"]
    
    # 0. GATEKEEPER CHECK
    profile, plan_config = validate_feature_access(user_id, 'idea_studio')
    
    # --- 1. JOB CREATION ---
    profile_data = get_user_profile(user_id)
    user_plan = profile_data.get('plan', 'starter')
    active_jobs = get_active_job_count(user_id)
    plan_limits = get_plan_limits(user_plan)
    
    if active_jobs >= plan_limits['concurrent']:
        raise HTTPException(
            status_code=429, 
            detail=f"Concurrency Limit Reached. Your plan ({user_plan}) allows {plan_limits['concurrent']} active jobs."
        )

    job_id = create_job(user_id, "idea_studio_script", metadata={"topic": request.topic})
    if not job_id:
        raise HTTPException(status_code=500, detail="Failed to initialize job.")

    # --- 2. SOFT CREDIT CHECK ---
    current_balance = profile_data.get('credits', 0) if profile_data else 0
    ESTIMATED_COST = 5
    if current_balance < ESTIMATED_COST:
        update_job_status(user_id, job_id, "failed_funds")
        raise HTTPException(
            status_code=402, 
            detail=f"Insufficient Credits. Need {ESTIMATED_COST}, Have {current_balance}"
        )
    
    # --- 3. PLAN ENFORCEMENT ---
    safe_height, needs_watermark = enforce_rendering_params(user_plan, 1080)
    
    from config import TEMP_DIR
    unique_id = uuid.uuid4().hex[:8]
    output_video_path = os.path.join(TEMP_DIR, f"output_video_{unique_id}.mp4")
    audio_path = os.path.join(TEMP_DIR, f"temp_audio_{unique_id}.mp3")

    try:
        # 1. Save Audio
        with open(audio_path, "wb") as f:
            f.write(base64.b64decode(request.audio_base64))

        # 2. Calculate clips needed
        from moviepy.editor import AudioFileClip
        temp_audioclip = AudioFileClip(audio_path)
        total_duration = temp_audioclip.duration
        temp_audioclip.close()
        
        num_clips = int(total_duration / 2.5) + 2
        
        # 3. Prepare search terms (Use smart scenes if available)
        if request.scenes and isinstance(request.scenes, list) and len(request.scenes) > 0:
            search_terms = request.scenes
            print(f"✅ Using Smart Mode Scenes for Sync: {len(search_terms)}")
        else:
            search_terms = request.visual_plan if request.visual_plan else [request.topic]
            
            if len(search_terms) < num_clips:
                cycle = itertools.cycle(search_terms)
                extra_terms = [next(cycle) for _ in range(num_clips - len(search_terms))]
                search_terms.extend(extra_terms)
        
        # Lazy import
        from viral_editor import generate_turbo_video

        output_video_path = generate_turbo_video(
            audio_path, 
            search_terms, 
            output_video_path, 
            platform=request.platform,
            main_topic=request.topic,
            mood=request.mood,
            resolution=safe_height,
            watermark=needs_watermark,
            subtitle_preset="bold_viral",
            hook_boost=True,
            brand_kit=profile_data.get('brand_kit') if profile_data else None,
            bgm_style=request.bgm_style
        )
        
        # 4. Upload to Cloud Storage
        print("Uploading...")
        final_url = None
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            backend_dir = os.path.dirname(current_dir)
            key_path = os.path.join(backend_dir, "service-account.json")
            
            from google.cloud import storage
            from google.oauth2 import service_account
            import google.auth
            
            if os.path.exists(key_path):
                creds = service_account.Credentials.from_service_account_file(key_path)
                storage_client = storage.Client(credentials=creds)
            else:
                # Use Application Default Credentials (Cloud Run)
                credentials, project = google.auth.default()
                storage_client = storage.Client(credentials=credentials)

            bucket_name = os.getenv("GCS_BUCKET_NAME", "shortcutai-user-uploads-2026")
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(f"videos/viral_{unique_id}.mp4")
            blob.upload_from_filename(output_video_path, timeout=60)
            
            try:
                final_url = blob.generate_signed_url(
                    version="v4",
                    expiration=datetime.timedelta(hours=1),
                    method="GET"
                )
            except Exception:
                final_url = blob.public_url
        except Exception as upload_err:
            print(f"⚠️ GCS Upload Failed/Bypassed: {upload_err}. Serving video locally via /temp endpoint.")
            from config import LOCAL_BASE_URL
            final_url = f"{LOCAL_BASE_URL}/temp/output_video_{unique_id}.mp4"

        # --- TRANSACTIONAL DEDUCTION ---
        try:
            from services.credit_service import complete_job_and_deduct
            complete_job_and_deduct(user_id, job_id, ESTIMATED_COST, "idea_studio_script")
            
            # --- 5. SAVE TO MY MASTERPIECES ---
            try:
                from firebase_admin import firestore
                db.collection('users').document(user_id).collection('projects').add({
                    'topic': request.topic,
                    'script': request.script[:500] if request.script else "",
                    'video_url': final_url,
                    'created_at': firestore.SERVER_TIMESTAMP,
                    'platform': request.platform,
                    'mood': request.mood,
                    'type': 'generated_v2'
                })
                print("💾 Project Saved to My Masterpieces")
            except Exception as e:
                print(f"❌ Failed to save project to My Masterpieces: {e}")
                
        except Exception as e:
            print(f"Credit deduction warning: {e}")
        
        return {"video_url": final_url}

    except Exception as e:
        print(f"Final Render Failed: {e}")
        traceback.print_exc()
        if job_id:
            update_job_status(user_id, job_id, "failed", error_msg=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
            # Only remove local video if GCS upload actually succeeded
            if final_url and "storage.googleapis.com" in final_url and os.path.exists(output_video_path):
                os.remove(output_video_path)
        except:
            pass
