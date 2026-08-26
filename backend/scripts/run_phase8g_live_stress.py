import os
import sys
import json
import time
import uuid
import datetime
import subprocess
import glob
from typing import Dict, Any, List
from dotenv import load_dotenv

# Ensure backend root is on sys.path and load environment variables
backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, backend_root)
load_dotenv(os.path.join(backend_root, ".env"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

os.environ.setdefault("GCP_PROJECT_ID", "shortcutai-backend")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "shortcutai-backend")

import firebase_admin
from firebase_admin import credentials, firestore

from core.models.context import GenerationContext
from core.models.blueprint import (
    ProductionBlueprint,
    SceneBlueprint,
    CameraDirection,
    DialogueLine,
    QualityStrategy
)
from core.models.character import Character
from core.models.attempt import GenerationAttempt
from core.services.bible_loader import ProjectBibleLoader, ResolvedScene
from core.services.reference_manager import ReferenceManager
from core.services.prompt_compiler import PromptCompiler
from core.services.continuity_manager import ContinuityManager
from core.services.canonical_generation_engine import (
    CanonicalGenerationEngine,
    CanonicalGenerationRequest
)
from core.services.timeline_builder import TimelineBuilder
from core.repositories.attempt_repo import GenerationAttemptRepository
from core.repositories.blueprint_repo import BlueprintRepository
from core.repositories.character_repo import CharacterRepository
from firebase_utils import upload_file

TEMP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "temp", "phase8g_stress"))
os.makedirs(TEMP_DIR, exist_ok=True)

def probe_video(file_path: str) -> Dict[str, Any]:
    """Probes a video file using ffprobe and returns metadata."""
    if not os.path.exists(file_path):
        return {"error": "File not found"}
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        duration = float(data.get("format", {}).get("duration", 0.0))
        video_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
        audio_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)
        
        return {
            "duration": duration,
            "width": int(video_stream.get("width", 0)),
            "height": int(video_stream.get("height", 0)),
            "video_codec": video_stream.get("codec_name"),
            "audio_codec": audio_stream.get("codec_name") if audio_stream else None,
            "has_audio": audio_stream is not None,
            "file_size_bytes": os.path.getsize(file_path)
        }
    except Exception as e:
        return {"error": str(e)}

def extract_keyframe(video_path: str, output_path: str, timestamp_sec: float = 1.0) -> bool:
    """Extracts a frame from video for forensic review."""
    try:
        cmd = [
            "ffmpeg", "-y", "-ss", str(timestamp_sec), "-i", video_path,
            "-vframes", "1", "-q:v", "2", output_path
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        return os.path.exists(output_path)
    except Exception as e:
        print(f"[FrameExtract] Error extracting frame: {e}")
        return False

def run_phase8g_live_stress():
    print("=================================================================")
    print("PHASE 8G: 30–60 SECOND LIVE CHARACTER CONSISTENCY STRESS TEST")
    print("=================================================================")
    start_time_all = time.time()
    
    # Initialize Firebase if not already initialized
    try:
        db = firestore.client()
    except Exception:
        firebase_admin.initialize_app()
        db = firestore.client()
        
    user_id = "user_phase8g_stress"
    project_id = "proj_phase8g_stress"
    blueprint_id = f"bp_phase8g_{uuid.uuid4().hex[:8]}"
    
    print(f"[Init] User: {user_id} | Project: {project_id} | Blueprint ID: {blueprint_id}")
    
    # -------------------------------------------------------------
    # 1. Populate Firestore Project Bible with 2 Characters
    # -------------------------------------------------------------
    char_repo = CharacterRepository()
    char_a = Character(
        character_id="char_padlock_male",
        project_id=project_id,
        name="Mr. Brass Padlock",
        legacy_character_design="Anthropomorphic brass padlock-headed male character in modern Indian kurta and jeans, stylized 3D CGI animation",
        canonical_reference_uri=None
    )
    char_b = Character(
        character_id="char_padlock_female",
        project_id=project_id,
        name="Mrs. Silver Padlock",
        legacy_character_design="Anthropomorphic silver padlock-headed female character in vibrant traditional Indian saree, stylized 3D CGI animation",
        canonical_reference_uri=None
    )
    char_repo.save(user_id, project_id, "char_padlock_male", char_a)
    char_repo.save(user_id, project_id, "char_padlock_female", char_b)
    print("[Bible] Saved Character A (Mr. Brass Padlock) and Character B (Mrs. Silver Padlock) to Firestore.")
    
    # -------------------------------------------------------------
    # 2. Build 8-Scene Production Blueprint (41.0s Total)
    # -------------------------------------------------------------
    cam_tracking = CameraDirection(shot_type="MEDIUM", lens="35mm", camera_motion="TRACKING", angle="EYE_LEVEL", framing="CENTERED", depth_of_field="SHALLOW", lighting="BRIGHT_DAYLIGHT")
    cam_wide = CameraDirection(shot_type="WIDE", lens="24mm", camera_motion="STATIC", angle="EYE_LEVEL", framing="WIDE_TWO_SHOT", depth_of_field="MEDIUM", lighting="BRIGHT_DAYLIGHT")
    cam_close = CameraDirection(shot_type="CLOSE_UP", lens="50mm", camera_motion="STATIC", angle="EYE_LEVEL", framing="TIGHT", depth_of_field="SHALLOW", lighting="BRIGHT_DAYLIGHT")
    cam_dolly = CameraDirection(shot_type="MEDIUM", lens="35mm", camera_motion="DOLLY", angle="SLIGHT_LOW", framing="CENTERED", depth_of_field="SHALLOW", lighting="BRIGHT_DAYLIGHT")
    
    scenes = [
        SceneBlueprint(
            scene_id="scn_g1_intro",
            scene_number=1,
            narrative_purpose="Establish canonical appearance of Character A approaching wooden door",
            estimated_duration_seconds=5.0,
            action="Anthropomorphic brass padlock-headed male character in modern Indian kurta walks toward the wooden front door carrying keys.",
            emotion="neutral",
            environment="Front porch of Indian suburban house with traditional carved wooden door",
            camera=cam_tracking,
            character_ids=["char_padlock_male"],
            scene_quality_priority="CHARACTER_CRITICAL"
        ),
        SceneBlueprint(
            scene_id="scn_g2_b_enters",
            scene_number=2,
            narrative_purpose="Character B enters and approaches Character A",
            estimated_duration_seconds=5.0,
            action="Anthropomorphic silver padlock-headed female character in colorful traditional Indian saree approaches the front porch smiling.",
            emotion="happy",
            environment="Front porch of Indian suburban house with traditional carved wooden door",
            camera=cam_wide,
            character_ids=["char_padlock_female", "char_padlock_male"],
            scene_quality_priority="CHARACTER_CRITICAL"
        ),
        SceneBlueprint(
            scene_id="scn_g3_dialogue",
            scene_number=3,
            narrative_purpose="Short conversation near the door",
            estimated_duration_seconds=5.0,
            action="Brass padlock husband gestures toward the door lock while silver padlock wife responds attentively.",
            emotion="curious",
            environment="Front porch of Indian suburban house with traditional carved wooden door",
            camera=cam_close,
            character_ids=["char_padlock_male", "char_padlock_female"],
            dialogue=[
                DialogueLine(
                    character_id="char_padlock_male",
                    voice_label="voice_male_01",
                    text="Did you remember the lock?",
                    emotion="curious",
                    delivery_style="comedic",
                    estimated_duration_seconds=2.4
                )
            ],
            scene_quality_priority="BALANCED"
        ),
        SceneBlueprint(
            scene_id="scn_g4_action",
            scene_number=4,
            narrative_purpose="Character A attempts comedic locking action",
            estimated_duration_seconds=6.0,
            action="Brass padlock husband secures the door handle using a small novelty baby prop playfully while silver padlock wife watches.",
            emotion="excited",
            environment="Front porch of Indian suburban house with traditional carved wooden door",
            camera=cam_dolly,
            character_ids=["char_padlock_male", "char_padlock_female"],
            scene_quality_priority="ACTION_CRITICAL"
        ),
        SceneBlueprint(
            scene_id="scn_g5_camera_change",
            scene_number=5,
            narrative_purpose="Camera framing shift to test identity persistence",
            estimated_duration_seconds=5.0,
            action="Close shot of silver padlock wife smiling with amusement near the front porch entrance.",
            emotion="happy",
            environment="Front porch of Indian suburban house with traditional carved wooden door",
            camera=cam_close,
            character_ids=["char_padlock_female"],
            scene_quality_priority="CHARACTER_CRITICAL"
        ),
        SceneBlueprint(
            scene_id="scn_g6_movement",
            scene_number=6,
            narrative_purpose="Character A turns and walks while maintaining body proportions",
            estimated_duration_seconds=5.0,
            action="Brass padlock husband walks a few paces along the porch and turns back to face his wife.",
            emotion="confident",
            environment="Front porch of Indian suburban house with traditional carved wooden door",
            camera=cam_tracking,
            character_ids=["char_padlock_male"],
            scene_quality_priority="CHARACTER_CRITICAL"
        ),
        SceneBlueprint(
            scene_id="scn_g7_two_char_close",
            scene_number=7,
            narrative_purpose="Both characters in close framing testing cross-contamination",
            estimated_duration_seconds=5.0,
            action="Silver padlock wife inspects the door lock while brass padlock husband gives a thumbs up.",
            emotion="happy",
            environment="Front porch of Indian suburban house with traditional carved wooden door",
            camera=cam_wide,
            character_ids=["char_padlock_female", "char_padlock_male"],
            scene_quality_priority="BALANCED"
        ),
        SceneBlueprint(
            scene_id="scn_g8_ending",
            scene_number=8,
            narrative_purpose="Both characters conclude story together",
            estimated_duration_seconds=5.0,
            action="Both brass padlock husband and silver padlock wife wave cheerfully toward the camera from the front porch.",
            emotion="happy",
            environment="Front porch of Indian suburban house with traditional carved wooden door",
            camera=cam_wide,
            character_ids=["char_padlock_male", "char_padlock_female"],
            scene_quality_priority="VISUAL_QUALITY_CRITICAL"
        )
    ]
    
    authoritative_art_style = "Stylized high-quality 3D animated film, consistent CGI character design"
    authoritative_character_design = "Anthropomorphic brass padlock-headed male in modern Indian attire and silver padlock-headed female in traditional Indian saree"
    
    bp = ProductionBlueprint(
        blueprint_id=blueprint_id,
        blueprint_version=1,
        project_id=project_id,
        title="Padlock Couple Door Lock Comedy",
        concept="A 3D animated comedy about a brass padlock-headed husband attempting to lock the house door with humorous props while his silver padlock-headed wife reacts.",
        genre="Animated Comedy",
        authoritative_art_style=authoritative_art_style,
        authoritative_character_design=authoritative_character_design,
        target_duration_seconds=41.0,
        scenes=scenes,
        quality_strategy=QualityStrategy(max_retries=1, min_overall_score=7.0),
        status="APPROVED"
    )
    
    bp_repo = BlueprintRepository()
    bp_repo.save(user_id, bp)
    print(f"[Blueprint] Saved 8-scene blueprint to Firestore ({len(scenes)} scenes, 41.0s target).")
    
    # -------------------------------------------------------------
    # 3. Instantiate Canonical Pipeline Services
    # -------------------------------------------------------------
    bible_loader = ProjectBibleLoader()
    ref_manager = ReferenceManager()
    prompt_compiler = PromptCompiler()
    continuity_manager = ContinuityManager()
    engine = CanonicalGenerationEngine()
    attempt_repo = GenerationAttemptRepository()
    timeline = TimelineBuilder(project_id)
    
    context = GenerationContext(
        user_id=user_id,
        project_id=project_id,
        job_id=blueprint_id,
        metadata={
            "art_style": authoritative_art_style,
            "character_design": authoritative_character_design,
            "reference_cache": {}
        }
    )
    
    # Forensic Telemetry Collection
    telemetry = {
        "blueprint_id": blueprint_id,
        "user_id": user_id,
        "project_id": project_id,
        "start_time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scenes": [],
        "reference_generation_calls": 0,
        "reference_cache_hits": 0,
        "reference_uris": {},
        "total_veo_calls": 0,
        "total_retries": 0,
        "elevenlabs_calls": 0,
        "synclabs_calls": 0
    }
    
    previous_scene_id = None
    
    # -------------------------------------------------------------
    # 4. Execute Real Pipeline Scene by Scene
    # -------------------------------------------------------------
    for scene in bp.scenes:
        scene_start_time = time.time()
        print("\n-----------------------------------------------------------------")
        print(f"[Orchestrator] EXECUTING SCENE {scene.scene_number} / {len(bp.scenes)}: {scene.scene_id}")
        print(f"[Orchestrator] Narrative: {scene.narrative_purpose} | Duration: {scene.estimated_duration_seconds}s")
        print("-----------------------------------------------------------------")
        
        attempt_id = f"attempt_{bp.blueprint_id}_{scene.scene_id}"
        attempt = GenerationAttempt(
            attempt_id=attempt_id,
            project_id=project_id,
            scene_id=scene.scene_id,
            attempt_number=1,
            prompt="",
            blueprint_id=bp.blueprint_id,
            blueprint_version=bp.blueprint_version
        )
        
        # Step 4a: Resolve Scene & References
        previous_state = continuity_manager.get_previous_state(context, previous_scene_id)
        resolved_scene = bible_loader.resolve_scene_blueprint(context, scene)
        prompt = prompt_compiler.compile(context, resolved_scene, previous_state=previous_state, scene_blueprint=scene)
        
        # Check cache state before resolution
        primary_char = resolved_scene.characters[0] if resolved_scene.characters else None
        char_id = primary_char.character_id if primary_char else "default"
        is_cache_hit = char_id in context.metadata.get("reference_cache", {})
        
        ref_resolution = ref_manager.resolve_reference_with_telemetry(context, resolved_scene)
        reference_uri = ref_resolution.reference_uri
        
        if ref_resolution.reference_generation_attempted and ref_resolution.reference_generation_status == "SUCCESS":
            telemetry["reference_generation_calls"] += 1
            print(f"[ReferenceManager] GENERATED new canonical reference asset for {char_id}: {reference_uri}")
        elif is_cache_hit:
            telemetry["reference_cache_hits"] += 1
            print(f"[ReferenceManager] REUSED cached canonical reference for {char_id}: {reference_uri}")
            
        telemetry["reference_uris"][char_id] = reference_uri
        
        # Save Attempt Record Initial Telemetry
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
        speaker = scene.dialogue[0].voice_label if scene.dialogue else "Male"
        if dialogue_text:
            telemetry["elevenlabs_calls"] += 1
            
        # Step 4b: Canonical Engine Generation
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
            use_lip_sync=True,
            max_retries=min(bp.quality_strategy.max_retries, 1) if bp.quality_strategy else 1,
            expected_duration=scene.estimated_duration_seconds or 5.0
        )
        
        print(f"[Prompt Forensics] Prompt length: {len(prompt)} chars | Reference URI: {reference_uri}")
        print(f"[Prompt Forensics] Prompt Preview: {prompt[:160]}...")
        
        try:
            gen_result = engine.generate_scene(req)
            scene_status = "PASSED"
        except Exception as e:
            print(f"[Orchestrator WARNING] Scene {scene.scene_id} rejected or failed: {e}")
            scene_status = "REJECTED_BY_REVIEWER"
            # Find the generated raw attempt video in temp
            raw_candidates = glob.glob(os.path.join(os.path.abspath("temp"), f"canonical_raw_{scene.scene_id}_*.mp4"))
            fallback_video_path = raw_candidates[-1] if raw_candidates else ""
            gen_result = CanonicalGenerationResult(
                scene_id=scene.scene_id,
                final_scene_path=fallback_video_path,
                raw_video_path=fallback_video_path,
                audio_path=None,
                audio_duration=0.0,
                status=scene_status
            )
            
        final_attempt = attempt_repo.get(user_id, project_id, attempt_id)
        attempts_count = final_attempt.attempt_number if final_attempt else 1
        
        telemetry["total_veo_calls"] += attempts_count
        if attempts_count > 1:
            telemetry["total_retries"] += (attempts_count - 1)
            
        final_scene_path = gen_result.final_scene_path
        raw_probe = probe_video(final_scene_path) if final_scene_path else {}
        
        # Extract frame for visual forensic review
        frame_out_path = os.path.join(TEMP_DIR, f"frame_{scene.scene_id}.jpg")
        if final_scene_path and os.path.exists(final_scene_path):
            extract_keyframe(final_scene_path, frame_out_path, timestamp_sec=1.5)
        
        # Step 4c: Register with TimelineBuilder
        dialogue_assets = []
        if gen_result.audio_path:
            from core.models.timeline import AudioAsset
            audio_asset = AudioAsset(
                asset_id=uuid.uuid4().hex,
                uri=gen_result.audio_path,
                duration=gen_result.audio_duration,
                start_time=0.0,
                end_time=gen_result.audio_duration
            )
            dialogue_assets.append(audio_asset)
            
        if final_scene_path and os.path.exists(final_scene_path):
            timeline.add_scene(scene, req.expected_duration, final_scene_path, dialogue_assets)
        
        # Step 4d: Continuity Update
        from core.models.state import SceneState
        new_state = SceneState(scene_id=scene.scene_id, project_id=project_id)
        continuity_manager.save_state(context, new_state)
        previous_scene_id = scene.scene_id
        
        scene_elapsed = time.time() - scene_start_time
        
        scene_telemetry = {
            "scene_number": scene.scene_number,
            "scene_id": scene.scene_id,
            "narrative_purpose": scene.narrative_purpose,
            "expected_duration": scene.estimated_duration_seconds,
            "raw_generated_duration": raw_probe.get("duration"),
            "raw_video_path": final_scene_path,
            "extracted_frame_path": frame_out_path if os.path.exists(frame_out_path) else None,
            "character_ids": scene.character_ids,
            "primary_character_id": char_id,
            "reference_uri_used": reference_uri,
            "reference_source": ref_resolution.reference_source,
            "reference_reused": is_cache_hit,
            "total_attempts": attempts_count,
            "scene_status": scene_status,
            "quality_review": final_attempt.quality_review if final_attempt else None,
            "audio_duration": gen_result.audio_duration,
            "has_dialogue": bool(dialogue_text),
            "generation_time_seconds": round(scene_elapsed, 2),
            "final_prompt_sent": prompt
        }
        telemetry["scenes"].append(scene_telemetry)
        print(f"[Scene Complete] Scene {scene.scene_number} finished in {round(scene_elapsed, 1)}s. Raw duration: {raw_probe.get('duration')}s.")

    # -------------------------------------------------------------
    # 5. Execute Timeline Normalization & Final Assembly
    # -------------------------------------------------------------
    print("\n=================================================================")
    print("[Timeline] RECONCILING & ASSEMBLING FINAL MASTER TIMELINE...")
    print("=================================================================")
    timeline.reconcile_timing()
    timeline.validate()
    
    master_video_path = timeline.execute_timeline()
    master_probe = probe_video(master_video_path)
    
    total_elapsed = time.time() - start_time_all
    
    telemetry["end_time"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    telemetry["total_runtime_seconds"] = round(total_elapsed, 2)
    telemetry["master_video_path"] = master_video_path
    telemetry["master_probe"] = master_probe
    
    # Upload Master Video & Frames to GCS
    try:
        master_gcs_uri = upload_file(master_video_path, folder=f"master_videos/{project_id}")
        telemetry["master_gcs_uri"] = master_gcs_uri
        print(f"[GCS] Master Video uploaded successfully: {master_gcs_uri}")
    except Exception as up_err:
        print(f"[GCS Upload Warning] {up_err}")
        
    # Save Telemetry JSON
    telemetry_file = os.path.join(TEMP_DIR, "phase8g_stress_telemetry.json")
    with open(telemetry_file, "w") as f:
        json.dump(telemetry, f, indent=2)
        
    print(f"\n[Telemetry Saved] {telemetry_file}")
    print(f"[Master Video] {master_video_path} (Duration: {master_probe.get('duration')}s)")
    print(f"[Total Runtime] {round(total_elapsed, 1)}s")
    
    return telemetry

if __name__ == "__main__":
    run_phase8g_live_stress()
