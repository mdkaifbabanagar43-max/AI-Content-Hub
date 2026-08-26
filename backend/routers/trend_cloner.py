import os
import json
from google.cloud import firestore
import math
import uuid
import subprocess
from typing import Optional, Union, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, File, UploadFile, Form
from pydantic import BaseModel

from core.auth import get_current_user
from services.veo_service import generate_video_with_veo
from services.trend_analyzer import analyze_trend_video
from services.trend_remixer import remix_trend
from services.intent_adapters.trend_adapter import use_ucd_trend
from config import TEMP_DIR, CREDIT_COSTS
from core.storage_client import upload_to_gcs
from core.firestore_client import get_user_profile, create_job, update_job_status, get_active_job_count, get_job_status
from core.plan_limits import get_plan_limits

router = APIRouter()


# ─────────────────────────────────────────────────────────────
# REQUEST MODELS
# ─────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    url: str
    niche: str = "General"


class SceneBeatRequest(BaseModel):
    """Per-scene beat from the AI Director (multi-scene generation)."""
    scene_id: int = 1
    shot_type: str = "wide_establish"
    veo_prompt: str
    duration_s: float = 2.5
    dialogue_lines: List[Dict[str, Any]] = []

    @property
    def scene_number(self) -> int:
        return self.scene_id



class GenerateRequest(BaseModel):
    # Multi-scene (new, preferred)
    scenes: Optional[List[SceneBeatRequest]] = None
    # Backward-compat single prompt
    veo_prompt: str = ""
    title: str
    script: Union[str, List[Dict[str, Any]]] = ""
    # Character consistency (optional)
    character_set_id: Optional[str] = None
    # Project ID for Bible contexts (optional)
    project_id: Optional[str] = None
    # Outro Text Card (optional)
    outro_text_card: Optional[str] = None
    # Burn Captions (optional, default False)
    burn_captions: bool = False
    # Use Lip Sync (optional, default True)
    use_lip_sync: bool = True
    # Production Blueprint ID (optional)
    blueprint_id: Optional[str] = None


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def download_video_yt_dlp(url: str, output_path: str) -> bool:
    """Legacy helper: delegates to shared secure video downloader."""
    try:
        from core.video_downloader import download_video
        result = download_video(url, output_path=output_path)
        return result.success and os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except Exception as e:
        print(f"video_downloader error: {e}")
        return False


def _get_ffmpeg():
    """Return the path to ffmpeg, preferring imageio_ffmpeg."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def merge_audio_video(video_path: str, audio_path: str, output_path: str, trim_duration: float = 0.0):
    """Overlay audio on video using MoviePy."""
    from moviepy.editor import VideoFileClip, AudioFileClip
    print(f"[Trend Cloner] Overlaying audio via MoviePy: {audio_path}")
    video_clip = VideoFileClip(video_path)
    audio_clip = AudioFileClip(audio_path)

    final_clip = video_clip.set_audio(audio_clip)

    if trim_duration > 0:
        final_clip = final_clip.subclip(0, min(trim_duration, final_clip.duration))

    final_clip.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        fps=30,                            # Fix 4: 30fps
        ffmpeg_params=["-crf", "23", "-preset", "medium"],  # Fix 5: CRF
        logger=None
    )
    video_clip.close()
    audio_clip.close()
    final_clip.close()


def _fetch_user_plan(user_id: str) -> str:
    """Fetch user plan tier from Firestore. Returns 'free' on any failure."""
    try:
        from core.firestore_client import get_firestore_client
        db = get_firestore_client()
        doc = db.collection("users").document(user_id).get()
        if doc.exists:
            return doc.to_dict().get("plan", "free").lower()
    except Exception as e:
        print(f"[Trend Cloner] Could not fetch plan for {user_id}: {e}")
    return "free"


# ─────────────────────────────────────────────────────────────
# ANALYZE ENDPOINT
# ─────────────────────────────────────────────────────────────

@router.post("/api/trend-cloner/analyze")
async def analyze_trend(
    url: Optional[str] = Form(None),
    niche: str = Form("General"),
    file: Optional[UploadFile] = File(None),
    user_id: str = Depends(get_current_user)
):
    print(f"[Trend Cloner] Analyzing URL/File for niche: {niche}")
    unique_id = uuid.uuid4().hex[:8]
    output_filename = f"trend_import_{unique_id}.mp4"
    output_path = os.path.join(TEMP_DIR, output_filename)

    # 1. Obtain Video
    if file:
        print("[Trend Cloner] Saving uploaded file...")
        contents = await file.read()
        with open(output_path, "wb") as f:
            f.write(contents)
    elif url:
        print(f"[Trend Cloner] Downloading URL: {url}")
        success = download_video_yt_dlp(url, output_path)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to download video. Is the link public?")
    else:
        raise HTTPException(status_code=400, detail="Must provide either url or file.")

    try:
        # 2. Gemini Vision Analysis
        analysis = analyze_trend_video(output_path)

        # 3. Multi-scene Remix
        # P3/Phase-F: flag-gated UCD adoption (wow-moment overlay +
        # transcript separation guard). Default OFF => byte-identical
        # legacy path; flip via UCD_TREND_ENABLED=1 after review.
        if use_ucd_trend():
            from services.intent_adapters.trend_adapter import remix_trend_via_ucd
            print("[TrendCloner] UCD_TREND_ENABLED=1 - UCD wow-moment path active")
            remix_result = remix_trend_via_ucd(analysis, niche)
        else:
            remix_result = remix_trend(analysis, niche)

        # 4. If character_set_id is auto-generated, save character ref
        art_style = analysis.get("art_style", "")
        character_design = analysis.get("character_design", "")
        if art_style and character_design:
            try:
                auto_char_id = f"{niche.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}"
                from core.character_refs import save_character_ref, _build_veo_prefix
                save_character_ref(auto_char_id, {
                    "art_style": art_style,
                    "character_design": character_design,
                    "veo_prefix": _build_veo_prefix(art_style, character_design),
                    "niche": niche,
                })
                remix_result["suggested_character_set_id"] = auto_char_id
            except Exception as e:
                print(f"[Trend Cloner] Character ref save failed (non-blocking): {e}")

        os.remove(output_path)
        return {"concepts": remix_result.get("concepts", []), "character_set_id": remix_result.get("suggested_character_set_id")}

    except Exception as e:
        print(f"Error during trend analysis: {e}")
        if os.path.exists(output_path):
            os.remove(output_path)
        raise HTTPException(status_code=500, detail=f"Failed to analyze video: {str(e)}")


# ─────────────────────────────────────────────────────────────
# GENERATE ENDPOINT
# ─────────────────────────────────────────────────────────────

@router.post("/api/trend-cloner/generate")
async def generate_trend(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user)
):
    print(f"[Trend Cloner] Generating trend: '{request.title}' | scenes={len(request.scenes or [])} | char_set={request.character_set_id}")

    # 0. Concurrency & Credit Pre-flight Check
    num_scenes = len(request.scenes) if request.scenes else 1
    credits_cost = CREDIT_COSTS.get('trend_cloner_base', 10) + (num_scenes * CREDIT_COSTS.get('trend_cloner_veo_per_scene', 25))

    profile_data = get_user_profile(user_id)
    if not profile_data:
        raise HTTPException(status_code=401, detail="User profile not found")

    user_plan = profile_data.get('plan', 'starter')
    current_credits = profile_data.get('credits', 0)

    if current_credits < credits_cost:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. Required: {credits_cost}, Available: {current_credits}."
        )

    active_jobs = get_active_job_count(user_id)
    plan_limits = get_plan_limits(user_plan)

    if active_jobs >= plan_limits.get('concurrent', 1):
        raise HTTPException(
            status_code=429,
            detail=f"Concurrency Limit Reached. Plan allows {plan_limits.get('concurrent', 1)} jobs."
        )

    # 0.5 Blueprint Validation & Production Cost Gate
    active_blueprint_version = None
    if request.blueprint_id:
        from core.repositories.blueprint_repo import BlueprintRepository
        bp_repo = BlueprintRepository()
        project_id = request.project_id or "legacy_project"
        bp = bp_repo.get(user_id, project_id, request.blueprint_id)
        if not bp:
            raise HTTPException(status_code=404, detail="Blueprint not found.")
        if bp.status != "APPROVED":
            raise HTTPException(status_code=400, detail=f"Blueprint must be APPROVED to start production. Current status: {bp.status}")
        
        active_blueprint_version = bp.blueprint_version
        bp.status = "IN_PRODUCTION"
        bp_repo.save(user_id, bp)
        
        # Override num_scenes based on blueprint
        num_scenes = len(bp.scenes)
        credits_cost = CREDIT_COSTS.get('trend_cloner_base', 10) + (num_scenes * CREDIT_COSTS.get('trend_cloner_veo_per_scene', 25))

    # 1. Create Job in Firestore
    job_metadata = {
        "credits_cost": credits_cost,
        "title": request.title,
        "num_scenes": num_scenes,
        "blueprint_id": request.blueprint_id,
        "blueprint_version": active_blueprint_version
    }
    job_id = create_job(user_id, "trend_cloner", metadata=job_metadata)
    if not job_id:
        raise HTTPException(status_code=500, detail="Failed to initialize job.")

    # 2. Dispatch Background Task with immutable blueprint version reference
    background_tasks.add_task(run_trend_cloner_job, job_id, user_id, request, credits_cost, user_plan, active_blueprint_version)

    return {"status": "processing", "job_id": job_id, "credits_cost": credits_cost}


@router.get("/api/trend-cloner/status/{job_id}")
def check_trend_cloner_status(job_id: str, user_id: str = Depends(get_current_user)):
    status = get_job_status(user_id, job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return status


def run_trend_cloner_job(job_id: str, user_id: str, request: GenerateRequest, credits_cost: int, user_plan: str, active_blueprint_version: Optional[int] = None):
    """Background worker for Trend Cloner pipeline with strict immutable blueprint execution."""
    print(f"[Trend Cloner Job] Starting {job_id} for user {user_id}")
    
    # ── Immutable Blueprint Verification Gate BEFORE ANY Provider Call ──
    active_blueprint = None
    if request.blueprint_id:
        from core.repositories.blueprint_repo import BlueprintRepository
        bp_repo = BlueprintRepository()
        project_id = request.project_id or "legacy_project"
        active_blueprint = bp_repo.get(user_id, project_id, request.blueprint_id, version=active_blueprint_version)
        if not active_blueprint or active_blueprint.status not in ["APPROVED", "IN_PRODUCTION"]:
            print(f"[Trend Cloner Job REJECTED] Blueprint {request.blueprint_id} (v{active_blueprint_version}) not approved.")
            update_job_status(user_id, job_id, "failed", error="Blueprint must be APPROVED to produce.")
            return

    update_job_status(user_id, job_id, "processing", progress="Initializing...")

    unique_id = uuid.uuid4().hex[:8]
    merged_path = os.path.join(TEMP_DIR, f"merged_{unique_id}.mp4")
    stitched_path = os.path.join(TEMP_DIR, f"stitched_{unique_id}.mp4")
    final_path = os.path.join(TEMP_DIR, f"final_{unique_id}.mp4")
    watermarked_path = os.path.join(TEMP_DIR, f"watermarked_{unique_id}.mp4")
    audio_path = None
    
    # --- PHASE 6: TIMELINE BUILDER ---
    from core.services.timeline_builder import TimelineBuilder
    timeline_builder = TimelineBuilder(request.project_id or "legacy_project")
    # ---------------------------------

    try:
        # ── 1. Resolve Character Consistency Seed ──────────────
        character_ref = None
        reference_image_uri = None
        if request.character_set_id:
            try:
                from core.character_refs import get_or_create_character_ref
                first_prompt = (request.scenes[0].veo_prompt if request.scenes else request.veo_prompt)
                character_ref = get_or_create_character_ref(
                    character_set_id=request.character_set_id,
                    art_style=first_prompt.split(",")[0] if first_prompt else "",
                    character_design=first_prompt.split(",")[1] if "," in first_prompt else "",
                )
                print(f"[Trend Cloner Job] Character consistency seed loaded: {request.character_set_id}")
            except Exception as e:
                print(f"[Trend Cloner Job] Character ref lookup failed (non-blocking): {e}")

        # NEW: I2V Character Locking Pipeline
        try:
            from services.asset_generator import generate_character_reference
            first_prompt = (request.scenes[0].veo_prompt if request.scenes else request.veo_prompt)
            parts = first_prompt.split(",") if first_prompt else []
            subject = parts[1].strip() if len(parts) > 1 else "main character"
            
            update_job_status(user_id, job_id, "processing", progress="Generating canonical character portrait...")
            reference_image_uri = generate_character_reference(subject)
            if reference_image_uri:
                print(f"[Trend Cloner Job] Generated reference image: {reference_image_uri}")
        except Exception as e:
            print(f"[Trend Cloner Job WARNING] I2V Asset generation failed, falling back to T2V: {e}")

        # ── 2. Generate Audio & Video Line-by-Line ─────────────
        script_timings = []
        current_time = 0.0

        if request.scenes and len(request.scenes) > 0:
            from services.elevenlabs_service import _generate_single_tts, VOICE_MAP
            from moviepy.editor import VideoFileClip, AudioFileClip
            
            print(f"[Trend Cloner Job] Multi-scene mode: Aligning audio and video line-by-line for {len(request.scenes)} scenes...")
            for i, scene in enumerate(request.scenes):
                update_job_status(user_id, job_id, "processing", progress=f"Generating scene {i+1} of {len(request.scenes)}...")
                
                # Extract dialogue for this scene
                scene_text = ""
                speaker = "Male"
                meme = "none"
                if scene.dialogue_lines:
                    scene_text = " ".join([dl.get("text", "") for dl in scene.dialogue_lines])
                    speaker = scene.dialogue_lines[0].get("speaker", "Male")
                    meme = scene.dialogue_lines[0].get("meme_overlay", "none")

                scene_duration = 5.0  # Default if no text
                audio_clip_path = None
                
                # Generate audio if there is text
                if scene_text.strip():
                    print(f"[Trend Cloner Job] Generating TTS for {speaker}: {scene_text[:30]}...")
                    vid = VOICE_MAP.get(speaker, "IKne3meq5aSn9XLyUdCD")
                    audio_clip_path = _generate_single_tts(scene_text, vid)
                    aclip = AudioFileClip(audio_clip_path)
                    scene_duration = aclip.duration
                    aclip.close()
                    
                    script_timings.append({
                        "start": current_time,
                        "end": current_time + scene_duration,
                        "meme_overlay": meme
                    })
                    current_time += scene_duration

                # Generate Veo clip (standard 5 seconds minimum to avoid API errors)
                target_veo_duration = max(5, math.ceil(scene_duration))
                
                scene_prompt = scene.veo_prompt
                active_reference_uri = reference_image_uri
                
                # --- PHASE 4: BIBLE LOADER & PROMPT COMPILER ---
                scene_bp = None
                try:
                    from core.models.context import GenerationContext
                    from core.services.bible_loader import ProjectBibleLoader
                    from core.services.prompt_compiler import PromptCompiler
                    from core.services.reference_manager import ReferenceManager
                    
                    project_id = request.project_id or "legacy_project"
                    gen_context = GenerationContext(
                        user_id=user_id,
                        project_id=project_id,
                        job_id=job_id
                    )
                    
                    loader = ProjectBibleLoader()
                    resolved_scene = loader.resolve_scene(gen_context, str(scene.scene_id))
                    
                    # Find matching SceneBlueprint if running with Blueprint
                    if active_blueprint:
                        scene_bp = next((sb for sb in active_blueprint.scenes if sb.scene_id == str(scene.scene_id) or sb.scene_number == (i+1)), None)

                    compiler = PromptCompiler()
                    compiled = compiler.compile(gen_context, resolved_scene, scene_blueprint=scene_bp)
                    if compiled.strip():
                        scene_prompt = compiled
                        
                    ref_mgr = ReferenceManager()
                    ref_uri = ref_mgr.get_reference_uri(gen_context, resolved_scene)
                    if ref_uri:
                        active_reference_uri = ref_uri
                        
                    # --- PHASE 5: CONTINUITY ---
                    try:
                        from core.services.continuity_manager import ContinuityManager
                        cont_mgr = ContinuityManager()
                        previous_scene_id = request.scenes[i-1].scene_id if i > 0 else None
                        previous_state = cont_mgr.get_previous_state(gen_context, str(previous_scene_id)) if previous_scene_id else None
                        
                        compiled = compiler.compile(gen_context, resolved_scene, previous_state, scene_blueprint=scene_bp)
                        if compiled.strip():
                            scene_prompt = compiled
                    except Exception as cont_e:
                        print(f"[Trend Cloner Job] Continuity Error: {cont_e}")
                        
                    print(f"[Trend Cloner Job] Scene {scene.scene_id} resolved via Bibles.")
                    
                    # Audit Logging
                    try:
                        from core.firestore_client import get_db
                        get_db().collection("audit_logs").add({
                            "project_id": project_id,
                            "job_id": job_id,
                            "scene_id": str(scene.scene_id),
                            "character_ids": [c.character_id for c in resolved_scene.characters],
                            "location_id": resolved_scene.location.location_id if resolved_scene.location else None,
                            "style_id": resolved_scene.style.style_id if resolved_scene.style else None,
                            "prop_ids": [p.prop_id for p in resolved_scene.props],
                            "selected_reference_uri": active_reference_uri,
                            "compiled_prompt": scene_prompt,
                            "model": "veo-3.1",
                            "timestamp": firestore.SERVER_TIMESTAMP
                        })
                    except Exception as audit_e:
                        print(f"[Audit Log Error] {audit_e}")
                        
                except Exception as e:
                    print(f"[Trend Cloner Job] Legacy / Bible Resolution skipped: {e}")
                # -----------------------------------------------

                if character_ref and not "SUBJECTS:" in scene_prompt:
                    from core.character_refs import apply_character_seed
                    scene_prompt = apply_character_seed(scene_prompt, character_ref)
                    
                # --- PHASE 5: IDEMPOTENCY & GENERATION LOOP ---
                accepted_raw_path = None
                try:
                    from core.repositories.attempt_repo import GenerationAttemptRepository
                    from core.models.attempt import GenerationAttempt
                    
                    attempt_repo = GenerationAttemptRepository()
                    project_id_attempt = request.project_id or "legacy_project"
                    existing_attempts = attempt_repo.list(user_id, project_id_attempt)
                    
                    if request.blueprint_id:
                        scene_attempts = [
                            a for a in existing_attempts 
                            if a.scene_id == str(scene.scene_id)
                            and a.blueprint_id == request.blueprint_id
                            and a.blueprint_version == active_blueprint_version
                        ]
                    else:
                        scene_attempts = [a for a in existing_attempts if a.scene_id == str(scene.scene_id)]
                        
                    scene_attempts.sort(key=lambda a: a.attempt_number)
                    
                    if scene_attempts and scene_attempts[-1].status == "COMPLETED" and scene_attempts[-1].output_uri:
                        test_path = scene_attempts[-1].output_uri
                        if os.path.exists(test_path):
                            try:
                                from moviepy.editor import VideoFileClip
                                with VideoFileClip(test_path) as tc:
                                    if tc.duration > 0:
                                        print(f"[Trend Cloner Job] Scene {scene.scene_id} already COMPLETED for bp_v{active_blueprint_version}. Reusing output.")
                                        accepted_raw_path = test_path
                            except Exception as e:
                                print(f"[Trend Cloner Job] Previous attempt file corrupt/unreadable, ignoring: {e}")
                        else:
                            print(f"[Trend Cloner Job] Previous attempt file missing on disk, ignoring.")
                except Exception as idemp_e:
                    print(f"[Trend Cloner Job] Idempotency Error: {idemp_e}")
                
                if not accepted_raw_path:
                    max_retries = 1
                    attempt_num = 1
                    quality_threshold = 8.0
                    
                    while attempt_num <= max_retries + 1:
                        print(f"[Trend Cloner Job] Generating Scene {scene.scene_id} - Attempt {attempt_num}")
                        attempt = None
                        try:
                            project_id_attempt = request.project_id or "legacy_project"
                            attempt = GenerationAttempt(
                                attempt_id=str(uuid.uuid4()),
                                project_id=project_id_attempt,
                                scene_id=str(scene.scene_id),
                                blueprint_id=request.blueprint_id,
                                blueprint_version=active_blueprint_version if request.blueprint_id else None,
                                attempt_number=attempt_num,
                                prompt=scene_prompt,
                                reference_uri=active_reference_uri,
                                status="GENERATING"
                            )
                            attempt_repo.save(user_id, project_id_attempt, attempt.attempt_id, attempt)
                        except Exception as e:
                            pass
                            
                        video_bytes = generate_video_with_veo(
                            prompt=scene_prompt, 
                            target_duration=target_veo_duration,
                            reference_image_uri=active_reference_uri
                        )
                        if not video_bytes:
                            if attempt:
                                attempt.status = "FAILED"
                                try: attempt_repo.save(user_id, project_id_attempt, attempt.attempt_id, attempt)
                                except: pass
                            raise Exception(f"Veo generation failed for scene {i+1}.")
                        
                        raw_path = os.path.join(TEMP_DIR, f"scene_{unique_id}_{i}_raw_att{attempt_num}.mp4")
                        if isinstance(video_bytes, bytes):
                            with open(raw_path, "wb") as f:
                                f.write(video_bytes)
                        elif isinstance(video_bytes, str) and video_bytes.startswith("gs://"):
                            from core.storage_client import download_gcs_uri
                            download_gcs_uri(video_bytes, raw_path)
                            
                        if attempt:
                            attempt.output_uri = raw_path
                            attempt.status = "REVIEWING"
                            try: attempt_repo.save(user_id, project_id_attempt, attempt.attempt_id, attempt)
                            except: pass
                            
                        # QUALITY REVIEW
                        try:
                            from core.services.quality_reviewer import QualityReviewer
                            reviewer = QualityReviewer()
                            quality_priority = scene_bp.scene_quality_priority if scene_bp else "BALANCED"
                            review_res = reviewer.review_video(raw_path, scene_prompt, scene_quality_priority=quality_priority)
                            print(f"[Trend Cloner Job] Quality Review: Overall {review_res.overall} (Priority: {quality_priority})")
                            
                            if attempt:
                                attempt.score = review_res.overall
                                attempt.quality_review_id = str(uuid.uuid4())
                                
                            if review_res.overall >= quality_threshold:
                                if attempt:
                                    attempt.status = "COMPLETED"
                                    try: attempt_repo.save(user_id, project_id_attempt, attempt.attempt_id, attempt)
                                    except: pass
                                accepted_raw_path = raw_path
                                break # Accept
                            else:
                                if attempt_num > max_retries:
                                    if attempt:
                                        attempt.status = "NEEDS_REVIEW"
                                        try: attempt_repo.save(user_id, project_id_attempt, attempt.attempt_id, attempt)
                                        except: pass
                                    accepted_raw_path = raw_path
                                    break
                                else:
                                    if attempt:
                                        attempt.status = "RETRYING"
                                        try: attempt_repo.save(user_id, project_id_attempt, attempt.attempt_id, attempt)
                                        except: pass
                                        
                                    weak_dims = [
                                        ("character_consistency", review_res.character_consistency),
                                        ("scene_adherence", review_res.scene_adherence),
                                        ("visual_quality", review_res.visual_quality),
                                        ("continuity", review_res.continuity)
                                    ]
                                    weakest = min(weak_dims, key=lambda x: x[1])
                                    
                                    instruction = ""
                                    if weakest[0] == "character_consistency":
                                        instruction = "CRITICAL: Stronger adherence to canonical character reference. Preserve canonical face, hair, and clothing."
                                    elif weakest[0] == "scene_adherence":
                                        instruction = "CRITICAL: Strengthen exact action, required props, and scene objective."
                                    elif weakest[0] == "visual_quality":
                                        instruction = "CRITICAL: Fix anatomy, realistic motion, and clean rendering. Avoid artifacts."
                                    elif weakest[0] == "continuity":
                                        instruction = "CRITICAL: Strengthen continuity from previous scene. Maintain state."
                                        
                                    scene_prompt = scene_prompt + f"\n\nREGENERATION TARGET: {instruction}"
                                    attempt_num += 1
                        except Exception as rev_e:
                            print(f"[Quality Reviewer Error] {rev_e}")
                            if attempt:
                                attempt.status = "NEEDS_REVIEW"
                                try: attempt_repo.save(user_id, project_id_attempt, attempt.attempt_id, attempt)
                                except: pass
                            accepted_raw_path = raw_path
                            break
                            
                # Save completed state
                try:
                    from core.models.state import SceneState
                    new_state = SceneState(
                        scene_id=str(scene.scene_id),
                        project_id=request.project_id or "legacy_project",
                        character_states=[],
                        environment_state=None,
                        prop_states=[]
                    )
                    try:
                        from core.services.continuity_manager import ContinuityManager
                        from core.models.context import GenerationContext
                        ctx = GenerationContext(user_id=user_id, project_id=request.project_id or "legacy_project", job_id=job_id)
                        ContinuityManager().save_state(ctx, new_state)
                    except: pass
                except Exception as state_e:
                    print(f"[Trend Cloner Job] Failed to save SceneState: {state_e}")
                    
                raw_path = accepted_raw_path
                # --- END PHASE 5 ---
                    
                # --- PHASE 6: TIMELINE SCENE ADDITION ---
                from core.models.timeline import AudioAsset
                dialogue_assets = []
                if audio_clip_path:
                    dialogue_assets.append(AudioAsset(
                        asset_id=str(uuid.uuid4()),
                        asset_type="dialogue",
                        uri=audio_clip_path,
                        duration=scene_duration,
                        start_time=0.0,
                        end_time=scene_duration,
                        scene_id=str(scene.scene_id)
                    ))
                    
                timeline_builder.add_scene(
                    scene=scene,
                    expected_duration=scene_duration,
                    raw_video_path=raw_path,
                    dialogue_assets=dialogue_assets
                )
                # ----------------------------------------
                
            print(f"[Trend Cloner Job] Reconciling and executing timeline for {len(request.scenes)} scenes...")
            update_job_status(user_id, job_id, "processing", progress="Building production timeline...")
            
            # --- PHASE 6: TIMELINE EXECUTION ---
            timeline_builder.reconcile_timing()
            
            update_job_status(user_id, job_id, "processing", progress="Normalizing duration and lip-syncing...")
            scene_clip_paths = timeline_builder.execute_timeline(use_lip_sync=request.use_lip_sync)
            
            timeline_builder.validate()
            # -----------------------------------
            
            update_job_status(user_id, job_id, "processing", progress="Stitching scenes...")
            from services.video_engine import concat_scenes
            concat_scenes(scene_clip_paths, merged_path, fps=30, crf=23, outro_text=request.outro_text_card)
            
            # --- 14. FINAL MASTER VALIDATION ---
            if not os.path.exists(merged_path):
                raise Exception("Final assembly failed: file does not exist.")
            
            try:
                final_v = VideoFileClip(merged_path)
                final_dur = final_v.duration
                final_v.close()
                if final_dur <= 0:
                    raise Exception("Final assembly failed: duration <= 0")
                if abs(final_dur - timeline_builder.timeline.total_duration) > 0.5: # 0.5s tolerance
                    print(f"FINAL_DURATION_DRIFT: Timeline expected {timeline_builder.timeline.total_duration}s, got {final_dur}s")
                update_job_status(user_id, job_id, "ASSEMBLY_COMPLETE", progress="Final video verified.")
            except Exception as final_e:
                raise Exception(f"Final master validation failed: {final_e}")
            # -----------------------------------

        else:
            # ── Fallback: Single-scene mode ──────────
            print(f"[Trend Cloner Job] Single-scene mode: generating Veo clip...")
            update_job_status(user_id, job_id, "processing", progress="Generating video...")
            veo_prompt = request.veo_prompt
            if character_ref:
                from core.character_refs import apply_character_seed
                veo_prompt = apply_character_seed(veo_prompt, character_ref)

            video_bytes = generate_video_with_veo(
                prompt=veo_prompt, 
                target_duration=8,
                reference_image_uri=reference_image_uri
            )
            if not video_bytes:
                raise Exception("Veo generation failed.")

            raw_path = os.path.join(TEMP_DIR, f"veo_raw_{unique_id}.mp4")
            if isinstance(video_bytes, bytes):
                with open(raw_path, "wb") as f:
                    f.write(video_bytes)
            elif isinstance(video_bytes, str) and video_bytes.startswith("gs://"):
                from core.storage_client import download_gcs_uri
                download_gcs_uri(video_bytes, raw_path)

            if request.script:
                from services.elevenlabs_service import generate_voiceover
                from moviepy.editor import VideoFileClip, AudioFileClip
                result = generate_voiceover(request.script)
                if isinstance(result, tuple):
                    audio_path, script_timings = result
                else:
                    audio_path = result
                    
                raw_video = VideoFileClip(raw_path)
                audio_clip = AudioFileClip(audio_path)
                video_with_audio = raw_video.set_audio(audio_clip)
                final_scene = video_with_audio.subclip(0, min(audio_clip.duration, raw_video.duration))
                final_scene.write_videofile(
                    merged_path,
                    codec="libx264",
                    audio_codec="aac",
                    fps=30,
                    ffmpeg_params=["-crf", "23", "-preset", "medium"],
                    logger=None
                )
                raw_video.close()
                audio_clip.close()
                final_scene.close()

                if request.use_lip_sync and audio_path:
                    update_job_status(user_id, job_id, "processing", progress="Lip-syncing video...")
                    from services.lip_sync_service import sync_lips
                    merged_path = sync_lips(merged_path, audio_path)
            else:
                import shutil
                shutil.copy2(raw_path, merged_path)

        # ── 3. Meme Overlays ────────────────────────────
        if script_timings:
            try:
                update_job_status(user_id, job_id, "processing", progress="Applying dynamic overlays...")
                from viral_editor import apply_meme_overlays
                apply_meme_overlays(merged_path, script_timings, merged_path)
            except Exception as e:
                print(f"[Trend Cloner Job WARNING] Meme overlay failed: {e}")

        # ── 4. Burn Viral Captions (Optional) ────────────
        if request.burn_captions:
            try:
                update_job_status(user_id, job_id, "processing", progress="Burning viral subtitles...")
                from viral_editor import add_viral_captions
                add_viral_captions(merged_path, final_path, subtitle_preset="bold_viral")
            except Exception as e:
                print(f"[Trend Cloner Job WARNING] Caption burning failed: {e}")
                final_path = merged_path
        else:
            final_path = merged_path

        # ── 6. Watermark ───────────────────────────────────────
        from services.video_engine import apply_watermark_if_needed
        apply_watermark_if_needed(final_path, watermarked_path, plan_tier=user_plan)
        upload_source = watermarked_path if os.path.exists(watermarked_path) else final_path

        # ── 7. Upload to GCS ───────────────────────────────────
        update_job_status(user_id, job_id, "processing", progress="Saving final video...")
        gcs_path = f"users/{user_id}/trends/final_trend_{unique_id}.mp4"
        gcs_url = upload_to_gcs(upload_source, gcs_path)

        # ── 8. QA Harness (soft gate — log only) ──────────────
        try:
            qa_script = os.path.join(os.path.dirname(__file__), "..", "scripts", "qa_compare_trend_clone.py")
            if os.path.exists(qa_script):
                subprocess.run(["python", qa_script, "--generated", upload_source], capture_output=True, timeout=30)
        except Exception:
            pass

        # ── 9. Deduct Credits & Complete ───────────────────────
        from services.credit_service import complete_job_and_deduct
        complete_job_and_deduct(user_id, job_id, credits_cost, "trend_cloner")
        
        update_job_status(user_id, job_id, "completed", progress="Done!", video_url=gcs_url)

    except Exception as e:
        print(f"[Trend Cloner Job] Error: {e}")
        import traceback
        traceback.print_exc()
        update_job_status(user_id, job_id, "failed", error_msg=str(e), progress="Failed")

    finally:
        print(f"[Trend Cloner Job] Cleanup for {job_id}")
        cleanup_paths = [merged_path, stitched_path, final_path, watermarked_path, audio_path]
        cleanup_paths.extend(scene_clip_paths)

        for path in cleanup_paths:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
