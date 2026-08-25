import os
import uuid
import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Form

from core.auth import get_current_user
from core.storage_client import upload_file, generate_signed_get_url
from core.models.video_cloner import SourceVideoRecord, FinalVideoRecord
from core.repositories.video_cloner_repos import (
    SourceVideoRepository, SourceAnalysisRepository, FinalVideoRepository
)
from core.repositories.clone_blueprint_repo import CloneBlueprintRepository
from core.repositories.blueprint_repo import BlueprintRepository
from core.repositories.attempt_repo import GenerationAttemptRepository
from core.models.attempt import GenerationAttempt

from services.source_analyzer import run_source_analysis
from core.services.clone_blueprint_builder import CloneBlueprintBuilder
from core.services.production_director import ProductionDirector
from core.models.transformation import ProductionTransformationRequest

# For Orchestration Loop
from core.services.bible_loader import ProjectBibleLoader
from config import CREDIT_COSTS
from fastapi import Request
from starlette.responses import JSONResponse
from core.repositories.job_repo import GenerationJobRepository
from core.models.job import GenerationJob
from core.tasks import enqueue_generation_task
from core.auth_oidc import verify_cloud_run_oidc_token
from core.services.reference_manager import ReferenceManager
from core.services.prompt_compiler import PromptCompiler
from services.veo_service import generate_video_with_veo
from core.services.quality_reviewer import QualityReviewer
from core.services.continuity_manager import ContinuityManager
from services.elevenlabs_service import generate_voiceover
from services.lip_sync_service import sync_lips as lip_sync_video
from core.services.timeline_builder import TimelineBuilder
from services.video_engine import concat_scenes
from config import TEMP_DIR

router = APIRouter(prefix="/projects", tags=["Video Cloner"])

source_repo = SourceVideoRepository()
analysis_repo = SourceAnalysisRepository()
clone_blueprint_repo = CloneBlueprintRepository()
production_blueprint_repo = BlueprintRepository()
final_video_repo = FinalVideoRepository()
attempt_repo = GenerationAttemptRepository()

@router.post("/{project_id}/source-videos")
async def upload_source_video(
    project_id: str,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user)
):
    """Ingests a source video, stores in GCS, and generates a SourceVideoRecord."""
    # Basic validation
    if not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Must be a video file")
        
    temp_path = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_{file.filename}")
    try:
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)
            
        url = upload_file(temp_path, folder=f"source_videos/{project_id}")
        if not url:
            raise HTTPException(status_code=500, detail="Failed to upload source video")
            
        record = SourceVideoRecord(
            user_id=user_id,
            project_id=project_id,
            gcs_uri=url,
            filename=file.filename,
            size_bytes=len(content)
        )
        
        source_repo.save(user_id, project_id, record.source_video_id, record)
        return record
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

class UrlSourceRequest(BaseModel):
    url: str

@router.post("/{project_id}/source-videos/from-url")
def import_source_video_from_url(
    project_id: str,
    body: UrlSourceRequest,
    user_id: str = Depends(get_current_user)
):
    """Downloads a video from supported platforms via shared secure downloader, uploads to GCS, and returns SourceVideoRecord."""
    from core.video_downloader import download_video
    temp_filename = f"url_ingest_{uuid.uuid4().hex[:8]}.mp4"
    temp_path = os.path.join(TEMP_DIR, temp_filename)
    try:
        result = download_video(body.url, output_path=temp_path)
        if not result.success or not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
            status_code = 400
            if result.error_type in ["download_timeout", "process_error"]:
                status_code = 500
            raise HTTPException(status_code=status_code, detail=result.error_message or "Failed to download video from URL")

        url = upload_file(temp_path, folder=f"source_videos/{project_id}")
        if not url:
            raise HTTPException(status_code=500, detail="Failed to upload downloaded video to GCS")

        record = SourceVideoRecord(
            user_id=user_id,
            project_id=project_id,
            gcs_uri=url,
            filename=temp_filename,
            size_bytes=os.path.getsize(temp_path)
        )
        source_repo.save(user_id, project_id, record.source_video_id, record)
        return record
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

class VisualIdentityRequest(BaseModel):
    art_style: Optional[str] = None
    character_design: Optional[str] = None
    characters: Optional[List[Dict[str, Any]]] = None
    environments: Optional[List[Dict[str, Any]]] = None
    props: Optional[List[Dict[str, Any]]] = None

@router.post("/{project_id}/visual-identity-pack")
def create_visual_identity_pack(
    project_id: str,
    req: VisualIdentityRequest,
    user_id: str = Depends(get_current_user)
):
    """Generates or locks the VisualIdentityPack for a project."""
    from core.services.visual_identity_service import VisualIdentityService
    vis = VisualIdentityService()
    pack = vis.build_or_get_visual_identity_pack(
        user_id=user_id,
        project_id=project_id,
        art_style=req.art_style or "Cinematic digital animation",
        character_design=req.character_design or "Characters as described in source video",
        characters=req.characters,
        environments=req.environments,
        props=req.props
    )
    return pack

@router.get("/{project_id}/visual-identity-pack")
def get_visual_identity_pack(
    project_id: str,
    user_id: str = Depends(get_current_user)
):
    """Retrieves the active VisualIdentityPack for a project."""
    from core.repositories.visual_identity_repo import VisualIdentityRepository
    vip_repo = VisualIdentityRepository()
    pack = vip_repo.get_latest(user_id, project_id)
    if not pack:
        raise HTTPException(status_code=404, detail="No VisualIdentityPack found for this project")
    return pack

@router.post("/{project_id}/source-videos/{source_video_id}/analyze")
def analyze_source_video(
    project_id: str,
    source_video_id: str,
    user_id: str = Depends(get_current_user)
):
    """Triggers SourceAnalysis generation."""
    source_record = source_repo.get(user_id, project_id, source_video_id)
    if not source_record:
        raise HTTPException(status_code=404, detail="Source video not found")
        
    # Check if analysis already exists
    existing_analyses = analysis_repo.list(user_id, project_id)
    for analysis in existing_analyses:
        if analysis.source_video_id == source_video_id:
            return analysis
            
    import urllib.request
    from config import TEMP_DIR
    local_path = os.path.join(TEMP_DIR, f"analyze_{source_video_id}.mp4")
    try:
        urllib.request.urlretrieve(source_record.gcs_uri, local_path)
        analysis = run_source_analysis(local_path, source_video_id)
        analysis_repo.save(user_id, project_id, analysis.analysis_id, analysis)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")
    finally:
        if os.path.exists(local_path):
            try:
                os.remove(local_path)
            except:
                pass

@router.get("/{project_id}/source-videos/{source_video_id}/analysis")
def get_source_analysis(
    project_id: str,
    source_video_id: str,
    user_id: str = Depends(get_current_user)
):
    """Gets the stored analysis for a source video."""
    analyses = analysis_repo.list(user_id, project_id)
    for analysis in analyses:
        if analysis.source_video_id == source_video_id:
            return analysis
    raise HTTPException(status_code=404, detail="Analysis not found")

@router.post("/{project_id}/source-videos/{source_video_id}/clone-blueprint")
def generate_clone_blueprint_from_source_video(
    project_id: str,
    source_video_id: str,
    user_id: str = Depends(get_current_user)
):
    """Generates a CloneBlueprint directly from a source_video_id."""
    analyses = analysis_repo.list(user_id, project_id)
    analysis = None
    for a in analyses:
        if a.source_video_id == source_video_id:
            analysis = a
            break
    if not analysis:
        raise HTTPException(status_code=404, detail="SourceAnalysis not found for this video. Please analyze the video first.")
        
    try:
        builder = CloneBlueprintBuilder()
        blueprint = builder.build_from_source(analysis, project_id, user_id)
        doc_id = f"{blueprint.clone_blueprint_id}_v{blueprint.clone_blueprint_version}"
        clone_blueprint_repo.save(user_id, project_id, doc_id, blueprint)
        return blueprint
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clone generation failed: {e}")

class CloneBlueprintRequest(BaseModel):
    analysis_id: str

@router.post("/{project_id}/clone-blueprints")
def generate_clone_blueprint(
    project_id: str,
    request: CloneBlueprintRequest,
    user_id: str = Depends(get_current_user)
):
    """Generates a CloneBlueprint from a SourceAnalysis."""
    analysis = analysis_repo.get(user_id, project_id, request.analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="SourceAnalysis not found")
        
    try:
        builder = CloneBlueprintBuilder()
        blueprint = builder.build_from_source(analysis, project_id, user_id)
        doc_id = f"{blueprint.clone_blueprint_id}_v{blueprint.clone_blueprint_version}"
        clone_blueprint_repo.save(user_id, project_id, doc_id, blueprint)
        return blueprint
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clone generation failed: {e}")

@router.get("/{project_id}/clone-blueprints/{clone_blueprint_id}")
def get_clone_blueprint(
    project_id: str,
    clone_blueprint_id: str,
    user_id: str = Depends(get_current_user)
):
    bp = clone_blueprint_repo.get_latest(user_id, project_id, clone_blueprint_id)
    if not bp:
        raise HTTPException(status_code=404, detail="CloneBlueprint not found")
    return bp

@router.post("/{project_id}/clone-blueprints/{clone_blueprint_id}/transform")
def transform_clone_blueprint(
    project_id: str,
    clone_blueprint_id: str,
    request: ProductionTransformationRequest,
    user_id: str = Depends(get_current_user)
):
    """Transforms a CloneBlueprint into a prescriptive ProductionBlueprint."""
    clone_bp = clone_blueprint_repo.get_latest(user_id, project_id, clone_blueprint_id)
    if not clone_bp:
        raise HTTPException(status_code=404, detail="CloneBlueprint not found")
        
    try:
        director = ProductionDirector(user_id, project_id)
        production_bp = director.transform_clone_blueprint(clone_bp, request)
        production_blueprint_repo.save(user_id, production_bp)
        return production_bp
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transformation failed: {e}")

@router.get("/{project_id}/production-blueprints/{production_blueprint_id}")
def get_production_blueprint(
    project_id: str,
    production_blueprint_id: str,
    user_id: str = Depends(get_current_user)
):
    bp = production_blueprint_repo.get(user_id, project_id, production_blueprint_id)
    if not bp:
        raise HTTPException(status_code=404, detail="ProductionBlueprint not found")
    return bp

@router.get("/{project_id}/production-blueprints/{production_blueprint_id}/status")
def get_production_blueprint_status(
    project_id: str,
    production_blueprint_id: str,
    user_id: str = Depends(get_current_user)
):
    bp = production_blueprint_repo.get(user_id, project_id, production_blueprint_id)
    if not bp:
        raise HTTPException(status_code=404, detail="ProductionBlueprint not found")
    
    final_video_url = None
    if hasattr(bp, "final_video_url") and bp.final_video_url:
        final_video_url = bp.final_video_url
    elif hasattr(bp, "output_uri") and bp.output_uri:
        final_video_url = bp.output_uri

    return {
        "blueprint_id": bp.blueprint_id,
        "status": bp.status,
        "final_video_url": final_video_url,
        "output_uri": final_video_url,
    }


@router.post("/{project_id}/production-blueprints/{production_blueprint_id}/approve")
def approve_production_blueprint(
    project_id: str,
    production_blueprint_id: str,
    user_id: str = Depends(get_current_user)
):
    bp = production_blueprint_repo.get(user_id, project_id, production_blueprint_id)
    if not bp:
        raise HTTPException(status_code=404, detail="ProductionBlueprint not found")
        
    if bp.status not in ["DRAFT", "READY_FOR_APPROVAL", "APPROVED", "IN_PRODUCTION", "FAILED"]:
        raise HTTPException(status_code=400, detail="Cannot approve blueprint in current state")
        
    bp.status = "APPROVED"
    production_blueprint_repo.save(user_id, bp)
    return {"status": "APPROVED"}

# --- ORCHESTRATION LOOP ---

def run_production_job(user_id: str, project_id: str, blueprint_id: str):
    """End-to-End Orchestrator (Phase 8D)"""
    print(f"[Orchestrator] Starting job for {blueprint_id}")
    bp = production_blueprint_repo.get(user_id, project_id, blueprint_id)
    if not bp:
        print(f"[Orchestrator] Aborting. Blueprint not found for ID: {blueprint_id}")
        return
    if bp.status not in ["APPROVED", "IN_PRODUCTION"]:
        print(f"[Orchestrator] Aborting. Blueprint status is {bp.status}, expected APPROVED or IN_PRODUCTION.")
        return
        
    from core.models.context import GenerationContext
    from core.services.canonical_generation_engine import CanonicalGenerationEngine, CanonicalGenerationRequest
    
    context = GenerationContext(user_id=user_id, project_id=project_id, job_id=blueprint_id)
    # 5. CHARACTER REFERENCE CACHE - Initialize in context metadata
    context.metadata = {"reference_cache": {}}
    
    bible_loader = ProjectBibleLoader()
    prompt_compiler = PromptCompiler()
    ref_manager = ReferenceManager()
    continuity_manager = ContinuityManager()
    timeline = TimelineBuilder(project_id)
    engine = CanonicalGenerationEngine()
    
    # 4. VISUAL IDENTITY SOURCE OF TRUTH
    clone_bp = None
    if bp.source_clone_blueprint_id:
        clone_bp = clone_blueprint_repo.get_latest(user_id, project_id, bp.source_clone_blueprint_id)
        
    raw_art_style = getattr(bp, "authoritative_art_style", None)
    authoritative_art_style = raw_art_style if isinstance(raw_art_style, str) and raw_art_style else "Cinematic 3D Animation"
    
    raw_char_design = getattr(bp, "authoritative_character_design", None)
    authoritative_character_design = raw_char_design if isinstance(raw_char_design, str) and raw_char_design else "A character"
    
    if clone_bp and clone_bp.visual_style_profile:
        clone_style = getattr(clone_bp.visual_style_profile, "art_style", None)
        if isinstance(clone_style, str) and clone_style:
            authoritative_art_style = clone_style
        clone_char = getattr(clone_bp.visual_style_profile, "character_design", None)
        if isinstance(clone_char, str) and clone_char:
            authoritative_character_design = clone_char
        
    context.metadata["art_style"] = authoritative_art_style
    context.metadata["character_design"] = authoritative_character_design
    
    # Load project VisualIdentityPack if available
    try:
        from core.repositories.visual_identity_repo import VisualIdentityRepository
        vip_repo = VisualIdentityRepository()
        vip = vip_repo.get_latest(user_id, project_id)
        if vip:
            context.metadata["visual_identity_pack"] = vip
            print(f"[Orchestrator] Loaded VisualIdentityPack {vip.pack_id} for project {project_id}")
    except Exception as vip_err:
        print(f"[Orchestrator] VisualIdentityPack context load warning: {vip_err}")
    
    scene_clip_paths = []
    
    try:
        previous_scene_id = None
        for scene in bp.scenes:
            print(f"[Orchestrator] Processing Scene {scene.scene_number}")
            
            # Idempotency / Checkpoint check
            attempt_id = f"attempt_{bp.blueprint_id}_{scene.scene_id}"
            attempt = attempt_repo.get(user_id, project_id, attempt_id)
            if not attempt:
                attempt = GenerationAttempt(
                    attempt_id=attempt_id,
                    project_id=project_id,
                    scene_id=scene.scene_id,
                    attempt_number=1,
                    prompt="",
                    blueprint_id=bp.blueprint_id,
                    blueprint_version=bp.blueprint_version
                )
                attempt_repo.save(user_id, project_id, attempt_id, attempt)
                
            if attempt.status == "COMPLETED" and attempt.output_uri:
                print(f"[Orchestrator] Scene {scene.scene_number} already completed.")
                local_scene_path = attempt.output_uri
                if attempt.output_uri.startswith("http://") or attempt.output_uri.startswith("https://"):
                    local_scene_path = os.path.join(TEMP_DIR, f"scene_{scene.scene_id}.mp4")
                    if not os.path.exists(local_scene_path) or os.path.getsize(local_scene_path) == 0:
                        import urllib.request
                        try:
                            urllib.request.urlretrieve(attempt.output_uri, local_scene_path)
                        except Exception as dl_err:
                            print(f"[Orchestrator] Failed to download cached scene {scene.scene_id}: {dl_err}")
                
                if os.path.exists(local_scene_path) and os.path.getsize(local_scene_path) > 0:
                    scene_clip_paths.append(local_scene_path)
                    timeline.add_scene(scene, scene.estimated_duration_seconds or 5.0, local_scene_path, [])
                    continue
                else:
                    print(f"[Orchestrator] Cached scene file {local_scene_path} missing, re-generating.")
                
            # 1. Compile prompt & reference
            previous_state = continuity_manager.get_previous_state(context, previous_scene_id)
            resolved_scene = bible_loader.resolve_scene_blueprint(context, scene)
            prompt = prompt_compiler.compile(context, resolved_scene, previous_state=previous_state, scene_blueprint=scene)
            
            has_character = bool(scene.character_ids or (resolved_scene and resolved_scene.characters))
            reference_required = has_character
            ref_resolution = ref_manager.resolve_reference_with_telemetry(
                context,
                resolved_scene,
                reference_required=reference_required,
                allow_fallback=False
            )
            reference_uri = ref_resolution.reference_uri
                
            attempt.prompt = prompt
            attempt.reference_uri = reference_uri
            attempt.reference_requested = ref_resolution.reference_requested
            attempt.reference_source = ref_resolution.reference_source
            attempt.reference_asset_id = ref_resolution.reference_asset_id
            attempt.reference_generation_attempted = ref_resolution.reference_generation_attempted
            attempt.reference_generation_status = ref_resolution.reference_generation_status
            attempt.reference_validation_status = ref_resolution.reference_validation_status
            attempt.reference_failure_reason = ref_resolution.reference_failure_reason
            attempt.fallback_mode = ref_resolution.fallback_mode
            attempt.status = "IN_PROGRESS"
            attempt_repo.save(user_id, project_id, attempt_id, attempt)
            
            dialogue_text = scene.dialogue[0].text if scene.dialogue else ""
            speaker = scene.dialogue[0].voice_id if scene.dialogue else "Male" # Using voice_id field for speaker map
            
            # 2. Canonical Engine Generation
            use_lip_sync_req = getattr(scene, "use_lip_sync", None)
            if use_lip_sync_req is None:
                use_lip_sync_req = getattr(bp, "use_lip_sync", None)
            if use_lip_sync_req is None:
                use_lip_sync_req = bool(dialogue_text)
            else:
                use_lip_sync_req = bool(use_lip_sync_req)
                
            allow_lip_sync_fb = getattr(scene, "allow_lip_sync_fallback", None)
            if allow_lip_sync_fb is None:
                allow_lip_sync_fb = getattr(bp, "allow_lip_sync_fallback", None)
            allow_lip_sync_fb = bool(allow_lip_sync_fb) if allow_lip_sync_fb is not None else True

            req = CanonicalGenerationRequest(
                user_id=user_id,
                project_id=project_id,
                job_id=blueprint_id,
                scene_id=scene.scene_id,
                raw_prompt=prompt,
                art_style=authoritative_art_style,
                character_design=authoritative_character_design,
                reference_image_uri=reference_uri,
                reference_requested=ref_resolution.reference_requested,
                reference_required=reference_required,
                reference_source=ref_resolution.reference_source,
                reference_asset_id=ref_resolution.reference_asset_id,
                reference_generation_attempted=ref_resolution.reference_generation_attempted,
                reference_generation_status=ref_resolution.reference_generation_status,
                reference_validation_status=ref_resolution.reference_validation_status,
                reference_failure_reason=ref_resolution.reference_failure_reason,
                fallback_mode=ref_resolution.fallback_mode,
                dialogue_text=dialogue_text,
                speaker=speaker,
                quality_priority=scene.scene_quality_priority if scene.scene_quality_priority else "BALANCED",
                use_lip_sync=use_lip_sync_req,
                allow_lip_sync_fallback=allow_lip_sync_fb,
                max_retries=(bp.quality_strategy.max_retries if bp.quality_strategy else 1),  # Engine clamps to MAX_SCENE_QUALITY_RETRIES ceiling
                expected_duration=scene.estimated_duration_seconds or 5.0
            )
            
            try:
                result = engine.generate_scene(req)
                final_scene_path = result.final_scene_path
                
                # Setup dialogue assets for TimelineBuilder
                dialogue_assets = []
                if result.audio_path:
                    from core.models.timeline import AudioAsset
                    audio_asset = AudioAsset(asset_id=uuid.uuid4().hex, uri=result.audio_path, duration=result.audio_duration, start_time=0.0, end_time=result.audio_duration)
                    dialogue_assets.append(audio_asset)
                    
                # 5. Timeline Registration
                timeline.add_scene(scene, req.expected_duration, final_scene_path, dialogue_assets)
                
            except Exception as e:
                print(f"[Orchestrator] Canonical Engine Generation Failed for Scene {scene.scene_id}: {e}")
                raise
                    
            # 6. Continuity Update
            from core.models.state import SceneState
            new_state = SceneState(scene_id=scene.scene_id, project_id=project_id)
            continuity_manager.save_state(context, new_state)
            previous_scene_id = scene.scene_id
            
            # 7. Upload Scene Clip to GCS & Record Attempt
            scene_gcs_url = None
            try:
                scene_gcs_url = upload_file(final_scene_path, folder=f"scene_clips/{project_id}")
            except Exception as up_err:
                print(f"[Orchestrator] Scene clip upload warning: {up_err}")
                
            attempt.output_uri = scene_gcs_url or final_scene_path
            attempt.status = "COMPLETED"
            attempt_repo.save(user_id, project_id, attempt_id, attempt)
            
            scene_clip_paths.append(final_scene_path)
            
        # Assembly (Fail-Closed)
        print("[Orchestrator] All scenes generated. Reconciling and Validating Timeline...")
        timeline.reconcile_timing()
        timeline.validate()
        
        # Retrieve authoritative clips from timeline
        print("[Orchestrator] Executing Timeline Normalization...")
        final_scene_paths = timeline.execute_timeline(use_lip_sync=False)
        
        if not final_scene_paths or len(final_scene_paths) != len(bp.scenes):
            from core.exceptions import AssemblyException
            raise AssemblyException(f"Timeline execution count ({len(final_scene_paths) if final_scene_paths else 0}) != blueprint scenes ({len(bp.scenes)})")

        # Ensure all clips exist on local disk and verify physical durations
        valid_final_paths = []
        total_duration_assembled = 0.0
        for i, p in enumerate(final_scene_paths):
            if not p or not os.path.exists(p) or os.path.getsize(p) == 0:
                from core.exceptions import AssemblyException
                raise AssemblyException(f"Normalized scene clip {i+1} is missing or empty: {p}")
            p_dur = timeline._get_video_duration(p)
            print(f"[Orchestrator] Scene {i+1} verified physical duration: {p_dur:.3f}s (file: {p})")
            valid_final_paths.append(p)
            total_duration_assembled += p_dur
            
        if len(valid_final_paths) != len(bp.scenes):
            from core.exceptions import AssemblyException
            raise AssemblyException(f"Total valid assembled clips ({len(valid_final_paths)}) != expected scenes ({len(bp.scenes)})")
            
        print(f"[Orchestrator] Total verified timeline duration: {total_duration_assembled:.3f}s across {len(valid_final_paths)} clips.")
        print(f"[Orchestrator] Assembling {len(valid_final_paths)} scene clips...")
        final_output = os.path.join(TEMP_DIR, f"final_{bp.blueprint_id}.mp4")
        concat_scenes(valid_final_paths, final_output)
        
        if not os.path.exists(final_output) or os.path.getsize(final_output) == 0:
            from core.exceptions import AssemblyException
            raise AssemblyException(f"Final concatenated video missing or empty: {final_output}")

        # Upload final output
        public_url = upload_file(final_output, folder=f"final_videos/{project_id}")
        if not public_url:
            from core.exceptions import AssemblyException
            raise AssemblyException("Final video GCS upload failed or returned empty URL")

        # Final Execution Certificate verification
        from core.models.operation_state import verify_execution_certificate
        certificate = verify_execution_certificate(
            job_id=blueprint_id,
            project_id=project_id,
            expected_scenes_count=len(bp.scenes),
            generated_scenes_count=len(valid_final_paths),
            all_scenes_approved=True,
            timeline_validated=True,
            normalized_scene_count=len(valid_final_paths),
            final_mp4_path=final_output,
            final_duration=total_duration_assembled,
            target_duration=bp.target_duration_seconds or 0.0,
            final_upload_uri=public_url
        )

        if not certificate.certified:
            from core.exceptions import AssemblyException
            raise AssemblyException(f"Execution Certificate validation failed: {'; '.join(certificate.certification_errors)}")

        # Persist FinalVideoRecord
        record = FinalVideoRecord(
            user_id=user_id,
            project_id=project_id,
            source_video_id=bp.source_clone_blueprint_id or "unknown",
            source_clone_blueprint_id=bp.source_clone_blueprint_id or "unknown",
            source_clone_blueprint_version=bp.source_clone_blueprint_version or 1,
            production_blueprint_id=bp.blueprint_id,
            production_blueprint_version=bp.blueprint_version,
            output_uri=public_url,
            duration_seconds=total_duration_assembled
        )
        final_video_repo.save(user_id, project_id, record.final_video_id, record)
        
        bp.status = "COMPLETED"
        production_blueprint_repo.save(user_id, bp)
        print(f"[Orchestrator] Success! Output: {public_url}")
        
    except Exception as e:
        print(f"[Orchestrator] Job Failed: {e}")
        import traceback
        traceback.print_exc()
        try:
            bp.status = "FAILED"
            production_blueprint_repo.save(user_id, bp)
        except Exception:
            pass
        # P0 BILLING FIX (fail-closed contract): Re-raise so the Cloud Tasks
        # worker's exception handler runs release_reservation(). Swallowing
        # here made the worker fall through to mark_completed(), committing
        # the user's credit reservation for a FAILED generation.
        raise

@router.post("/{project_id}/production-blueprints/{production_blueprint_id}/generate")
def generate_production(
    project_id: str,
    production_blueprint_id: str,
    user_id: str = Depends(get_current_user)
):
    """Reserves credits and enqueues a GenerationJob to Cloud Tasks."""
    bp = production_blueprint_repo.get(user_id, project_id, production_blueprint_id)
    if not bp:
        raise HTTPException(status_code=404, detail="ProductionBlueprint not found")
        
    if bp.status not in ["APPROVED", "IN_PRODUCTION", "READY_FOR_APPROVAL"]:
        raise HTTPException(status_code=400, detail=f"Blueprint must be APPROVED to generate, currently {bp.status}")
        
    # Cost calculation
    num_scenes = len(bp.scenes) if getattr(bp, 'scenes', None) else 14
    credits_cost = CREDIT_COSTS.get('trend_cloner_base', 10) + (num_scenes * CREDIT_COSTS.get('trend_cloner_veo_per_scene', 25))
    
    # Create Job & Reserve
    job_repo = GenerationJobRepository()
    job = GenerationJob(
        user_id=user_id,
        project_id=project_id,
        blueprint_id=production_blueprint_id
    )
    
    success = job_repo.create_and_reserve(job, credits_cost)
    if not success:
        raise HTTPException(status_code=400, detail="Insufficient credits for this generation job.")
        
    # Enqueue task
    enqueued = enqueue_generation_task(user_id, project_id, production_blueprint_id, job.job_id)
    if not enqueued:
        job_repo.release_reservation(user_id, project_id, production_blueprint_id, job.job_id)
        raise HTTPException(status_code=500, detail="Failed to enqueue Cloud Task. Credits released.")
        
    bp.status = "IN_PRODUCTION"
    production_blueprint_repo.save(user_id, bp)
    
    return JSONResponse(
        status_code=202,
        content={"message": "Generation queued", "job_id": job.job_id, "status": "QUEUED"}
    )

class TaskPayload(BaseModel):
    schema_version: int
    job_id: str
    user_id: str
    project_id: str
    blueprint_id: str
    test_mode: bool = False

@router.post("/_internal/tasks/generate-production")
async def generate_worker(request: Request, payload: TaskPayload):
    """Internal OIDC-authenticated worker for Cloud Tasks."""
    verify_cloud_run_oidc_token(request)
    
    job_repo = GenerationJobRepository()
    
    # Validate Ownership (App-level checks)
    bp = production_blueprint_repo.get(payload.user_id, payload.project_id, payload.blueprint_id)
    if not bp:
        import logging
        logging.warning(f"Worker FAILED for {payload.job_id}: Blueprint not found. user={payload.user_id} project={payload.project_id} bp_id={payload.blueprint_id}")
        # Non-retryable
        job_repo.release_reservation(payload.user_id, payload.project_id, payload.blueprint_id, payload.job_id)
        return {"status": "FAILED", "reason": "Blueprint not found"}
        
    # Idempotency / State Lock
    started = job_repo.try_start_job(payload.user_id, payload.project_id, payload.blueprint_id, payload.job_id)
    if not started:
        import logging
        logging.warning(f"Worker IGNORED for {payload.job_id}: Job already running, completed, or missing.")
        # Already RUNNING or COMPLETED, or FAILED. Idempotent success returns 200 so Cloud Tasks stops.
        return {"status": "IGNORED", "reason": "Job is already running or completed"}
        
    try:
        if payload.test_mode:
            import time
            import logging
            logging.info(f"Running safe TEST MODE worker execution for job {payload.job_id}")
            time.sleep(1) # Simulate safe test execution
            # Commit credits
            job_repo.mark_completed(payload.user_id, payload.project_id, payload.blueprint_id, payload.job_id)
            return {"status": "COMPLETED", "test_mode": True}

        # Execute the actual canonical generation engine
        run_production_job(payload.user_id, payload.project_id, payload.blueprint_id)
        
        # Commit credits
        job_repo.mark_completed(payload.user_id, payload.project_id, payload.blueprint_id, payload.job_id)
        return {"status": "COMPLETED"}
    except HTTPException as he:
        # Retryable or specific HTTP exceptions should propagate to Cloud Tasks
        raise he
    except Exception as e:
        import traceback
        import logging
        logging.error(f"Generation error for job {payload.job_id}: {traceback.format_exc()}")
        # run_production_job follows a fail-closed contract: any exception it
        # raises is treated as a permanent generation failure. Release the
        # credit reservation so the user is NOT charged for failed work, then
        # return 200 so Cloud Tasks does not retry a permanent error.
        job_repo.release_reservation(payload.user_id, payload.project_id, payload.blueprint_id, payload.job_id)
        
        # We return 200 to Cloud Tasks so it DOES NOT retry unless we specifically throw a 50x.
        # As per the requirements, permanent failures should return 2xx to stop retries.
        return {"status": "FAILED", "reason": str(e)}
