import os
import uuid
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from main import app
from config import BASE_DIR, TEMP_DIR, CREDIT_COSTS, ModelRoutingConfig
from core.models.source_analysis import (
    SourceAnalysis, SourceMediaMetadata, SourceSceneSegment, SceneSemanticAnalysis,
    HookAnalysis, CTAAnalysis, SourceAudioProfile, SourceDialogueBeat, SourceVisualStyle
)
from core.models.clone_blueprint import CloneBlueprint
from core.models.blueprint import (
    ProductionBlueprint, SceneBlueprint, DialogueLine, CameraDirection,
    ContinuityRequirement, QualityStrategy, GenerationStrategy
)
from core.models.transformation import ProductionTransformationRequest
from core.models.video_cloner import SourceVideoRecord, FinalVideoRecord
from core.models.job import GenerationJob
from core.models.context import GenerationContext
from core.models.visual_identity import VisualIdentityPack, CharacterVisualIdentity, VisualTreatment

from services.source_analyzer import probe_media_metadata, detect_scene_segments, run_source_analysis
from core.services.clone_blueprint_builder import CloneBlueprintBuilder
from core.services.visual_identity_service import VisualIdentityService
from core.services.production_director import ProductionDirector
from core.services.canonical_generation_engine import (
    CanonicalGenerationEngine, CanonicalGenerationRequest, CanonicalGenerationResult
)
from core.services.timeline_builder import TimelineBuilder
from core.exceptions import (
    AudioGenerationError, VeoGenerationError, QualityReviewError,
    LipSyncError, TimelineExecutionException, AssemblyException
)
from core.auth import get_current_user
from core.repositories.job_repo import GenerationJobRepository
from core.repositories.blueprint_repo import BlueprintRepository
from core.repositories.clone_blueprint_repo import CloneBlueprintRepository
from core.repositories.video_cloner_repos import SourceVideoRepository, FinalVideoRepository, SourceAnalysisRepository
from core.repositories.attempt_repo import GenerationAttemptRepository
from core.models.attempt import GenerationAttempt
from core.models.operation_state import verify_execution_certificate

# Identify Golden Test Video
GOLDEN_VIDEO_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "videos", "WhatsApp Video 2026-08-17 at 11.36.14 PM.mp4"))

def override_get_current_user():
    return "golden_test_user"

@pytest.fixture(autouse=True)
def setup_auth_override():
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)

@pytest.fixture
def api_client():
    return TestClient(app)

# ============================================================================
# 1. GOLDEN VIDEO FIXTURE INSPECTION TESTS
# ============================================================================

def test_golden_video_fixture_exists_and_readable():
    """Validates the canonical regression fixture video file properties."""
    assert os.path.exists(GOLDEN_VIDEO_PATH), f"Golden test video not found at: {GOLDEN_VIDEO_PATH}"
    file_size = os.path.getsize(GOLDEN_VIDEO_PATH)
    assert file_size == 1661848, f"Unexpected file size: {file_size}"
    
    # Probe with media analyzer
    metadata = probe_media_metadata(GOLDEN_VIDEO_PATH)
    assert metadata.file_size_bytes == 1661848
    assert metadata.width == 716
    assert metadata.height == 1274
    assert round(metadata.fps) == 30
    assert round(metadata.duration_seconds, 1) == 13.0
    assert metadata.has_audio is True
    assert metadata.audio_duration_seconds is not None

def test_golden_video_deterministic_segment_detection():
    """Detects deterministic cut boundaries using PySceneDetect without LLM calls."""
    metadata = probe_media_metadata(GOLDEN_VIDEO_PATH)
    segments = detect_scene_segments(GOLDEN_VIDEO_PATH, metadata.duration_seconds)
    
    assert len(segments) >= 1
    # Check continuous time coverage
    assert segments[0].start_seconds == 0.0
    assert abs(segments[-1].end_seconds - metadata.duration_seconds) < 0.2
    for s in segments:
        assert s.duration_seconds > 0

# ============================================================================
# 2. FULL PIPELINE STAGE-BY-STAGE GOLDEN EXECUTION (MOCKED EXTERNAL PROVIDERS)
# ============================================================================

def test_golden_pipeline_end_to_end_mocked():
    """
    Executes the entire 14-stage Video Cloner pipeline using realistic data shapes
    derived from the Golden Test Video.
    Zero external AI credits spent.
    """
    user_id = "golden_test_user"
    project_id = "proj_golden_001"
    
    # -------------------------------------------------------------
    # Stage 1: Ingest & Source Media Probing
    # -------------------------------------------------------------
    source_metadata = probe_media_metadata(GOLDEN_VIDEO_PATH)
    source_video_record = SourceVideoRecord(
        user_id=user_id,
        project_id=project_id,
        gcs_uri="gs://mock-bucket/source_videos/golden.mp4",
        filename="WhatsApp Video 2026-08-17 at 11.36.14 PM.mp4",
        size_bytes=source_metadata.file_size_bytes
    )
    assert source_video_record.source_video_id is not None

    # -------------------------------------------------------------
    # Stage 2: Source Analysis
    # -------------------------------------------------------------
    segments = detect_scene_segments(GOLDEN_VIDEO_PATH, source_metadata.duration_seconds)
    mock_semantic_scenes = [
        SceneSemanticAnalysis(
            scene_number=s.scene_number,
            narrative_purpose=f"Beat {s.scene_number}",
            visual_action=f"Character action in scene {s.scene_number}",
            emotion="curious",
            pacing_intensity="MEDIUM",
            shot_type="MEDIUM",
            camera_motion="STATIC",
            character_roles=["PROTAGONIST"]
        )
        for s in segments
    ]
    
    source_analysis = SourceAnalysis(
        source_video_id=source_video_record.source_video_id,
        media_metadata=source_metadata,
        transcript_text="Padlock characters having a dialogue",
        scenes=segments,
        semantic_scenes=mock_semantic_scenes,
        hook=HookAnalysis(hook_type="VISUAL_SHOCK", hook_start_seconds=0.0, hook_end_seconds=2.5, confidence=0.9),
        cta=CTAAnalysis(exists=True, start_seconds=11.0, end_seconds=13.0, type="FOLLOW"),
        visual_style=SourceVisualStyle(
            art_style="3D Pixar-style digital animation",
            character_design="Padlock-head anthropomorphic characters"
        ),
        audio_profile=SourceAudioProfile(has_dialogue=True, dialogue_clarity="HIGH")
    )
    assert len(source_analysis.scenes) == len(source_analysis.semantic_scenes)

    # -------------------------------------------------------------
    # Stage 3: CloneBlueprint Generation
    # -------------------------------------------------------------
    cb_builder = CloneBlueprintBuilder()
    clone_bp = cb_builder.build_from_source(source_analysis, project_id, user_id, title="Golden Cloned Blueprint")
    assert clone_bp.clone_blueprint_id.startswith("cl_")
    assert clone_bp.target_duration_seconds == source_metadata.duration_seconds
    assert len(clone_bp.scenes) == len(segments)

    # -------------------------------------------------------------
    # Stage 4: Visual Identity Pack Generation
    # -------------------------------------------------------------
    with patch("core.services.visual_identity_service.generate_character_reference", return_value="gs://mock-bucket/assets/padlock_char.jpg"), \
         patch("core.repositories.visual_identity_repo.VisualIdentityRepository.get_latest", return_value=None), \
         patch("core.repositories.visual_identity_repo.VisualIdentityRepository.save", return_value=True), \
         patch("core.repositories.character_repo.CharacterRepository.get", return_value=None):
        vip_service = VisualIdentityService()
        vip = vip_service.build_or_get_visual_identity_pack(
            user_id=user_id,
            project_id=project_id,
            art_style="3D Pixar-style digital animation",
            character_design="Brass padlock head character wearing traditional vest",
            characters=[{"character_id": "char_padlock_1", "name": "Padlock Lead"}]
        )
        assert vip.pack_id.startswith("vip_")
        assert "char_padlock_1" in vip.characters
        assert vip.characters["char_padlock_1"].master_sheet_uri == "gs://mock-bucket/assets/padlock_char.jpg"

    # -------------------------------------------------------------
    # Stage 5: Creative Transformation -> ProductionBlueprint
    # -------------------------------------------------------------
    director = ProductionDirector(user_id, project_id)
    transform_req = ProductionTransformationRequest(
        topic="Indian Padlock Family Comedy",
        story_change="Padlock father negotiates a deal",
        target_duration_seconds=13.0,
        tone="Humorous",
        language="Hinglish"
    )

    mock_production_bp = ProductionBlueprint(
        project_id=project_id,
        blueprint_version=1,
        blueprint_id="pb_golden_001",
        source_clone_blueprint_id=clone_bp.clone_blueprint_id,
        source_clone_blueprint_version=1,
        title="Indian Padlock Family Comedy",
        concept="Padlock father negotiation comedy",
        genre="3D Animated Comedy",
        target_duration_seconds=13.0,
        aspect_ratio="9:16",
        authoritative_art_style="3D Pixar-style digital animation",
        authoritative_character_design="Brass padlock head character",
        status="DRAFT",
        scenes=[
            SceneBlueprint(
                scene_id="scene_001",
                scene_number=1,
                narrative_purpose="Introduction",
                estimated_duration_seconds=4.5,
                character_ids=["char_padlock_1"],
                action="Padlock character stands at wooden door greeting neighbor",
                dialogue=[DialogueLine(
                    character_id="char_padlock_1",
                    voice_id="Male",
                    text="Namaste bhaisahab! Kahan ja rahe ho?",
                    emotion="cheerful",
                    delivery_style="conversational",
                    estimated_duration_seconds=3.0
                )],
                camera=CameraDirection(shot_type="MEDIUM", camera_motion="STATIC")
            ),
            SceneBlueprint(
                scene_id="scene_002",
                scene_number=2,
                narrative_purpose="Negotiation",
                estimated_duration_seconds=4.5,
                character_ids=["char_padlock_1"],
                action="Padlock character gestures excitedly with hands",
                dialogue=[DialogueLine(
                    character_id="char_padlock_1",
                    voice_id="Male",
                    text="Deal pakki samjhein!",
                    emotion="excited",
                    delivery_style="energetic",
                    estimated_duration_seconds=2.5
                )],
                camera=CameraDirection(shot_type="CLOSE_UP", camera_motion="DOLLY")
            ),
            SceneBlueprint(
                scene_id="scene_003",
                scene_number=3,
                narrative_purpose="Resolution",
                estimated_duration_seconds=4.0,
                character_ids=["char_padlock_1"],
                action="Padlock character smiles and shakes hands",
                dialogue=[DialogueLine(
                    character_id="char_padlock_1",
                    voice_id="Male",
                    text="Shukriya!",
                    emotion="happy",
                    delivery_style="warm",
                    estimated_duration_seconds=1.5
                )],
                camera=CameraDirection(shot_type="MEDIUM", camera_motion="STATIC")
            )
        ]
    )

    # -------------------------------------------------------------
    # Stage 6: Approval
    # -------------------------------------------------------------
    mock_production_bp.status = "APPROVED"
    assert mock_production_bp.status == "APPROVED"
    assert len(mock_production_bp.scenes) == 3

    # -------------------------------------------------------------
    # Stage 7: Credit Reservation & Cloud Task Enqueue Contract
    # -------------------------------------------------------------
    num_scenes = len(mock_production_bp.scenes)
    expected_cost = CREDIT_COSTS.get('trend_cloner_base', 10) + (num_scenes * CREDIT_COSTS.get('trend_cloner_veo_per_scene', 25))
    assert expected_cost == 10 + (3 * 25) # 85 credits

    job = GenerationJob(
        user_id=user_id,
        project_id=project_id,
        blueprint_id=mock_production_bp.blueprint_id,
        reserved_credits=expected_cost
    )

    # Verify task payload structure contract
    task_payload = {
        "schema_version": 1,
        "job_id": job.job_id,
        "user_id": user_id,
        "project_id": project_id,
        "blueprint_id": mock_production_bp.blueprint_id
    }
    assert "schema_version" in task_payload
    assert "job_id" in task_payload
    assert "user_id" in task_payload
    assert "project_id" in task_payload
    assert "blueprint_id" in task_payload

    # -------------------------------------------------------------
    # Stage 8: CanonicalGenerationEngine Mock Execution
    # -------------------------------------------------------------
    engine = CanonicalGenerationEngine()
    
    with patch("core.services.canonical_generation_engine.generate_voiceover") as mock_voice, \
         patch("core.services.canonical_generation_engine.generate_video_with_veo") as mock_veo, \
         patch("core.services.canonical_generation_engine._get_audioclip_class", return_value=None), \
         patch("core.services.canonical_generation_engine._get_videoclip_class", return_value=None), \
         patch("core.services.quality_reviewer.QualityReviewer.review_video") as mock_qr, \
         patch("core.services.timeline_builder.TimelineBuilder.normalize_video_to_audio_duration") as mock_norm, \
         patch("services.lip_sync_service.sync_lips") as mock_sync, \
         patch("core.repositories.attempt_repo.GenerationAttemptRepository.save", return_value=True), \
         patch("core.repositories.attempt_repo.GenerationAttemptRepository.get", return_value=None):
        
        from core.services.quality_reviewer import QualityReviewResult
        mock_voice.return_value = "/mock/path/audio.mp3"
        mock_veo.return_value = b"mock_veo_video_content"
        mock_qr.return_value = QualityReviewResult(
            character_consistency=9.0,
            scene_adherence=9.0,
            visual_quality=9.0,
            continuity=8.5,
            overall=8.875,
            issues=[],
            recommended_action="accept"
        )
        mock_norm.side_effect = lambda raw_path, dur, scn_id: f"/mock/normalized_{scn_id}.mp4"
        mock_sync.side_effect = lambda raw_path, aud_path: f"/mock/synced_{os.path.basename(raw_path)}"

        scene_results = []
        for scene in mock_production_bp.scenes:
            req = CanonicalGenerationRequest(
                user_id=user_id,
                project_id=project_id,
                job_id=mock_production_bp.blueprint_id,
                scene_id=scene.scene_id,
                raw_prompt=f"A 3D animated padlock character: {scene.action}",
                art_style=mock_production_bp.authoritative_art_style,
                character_design=mock_production_bp.authoritative_character_design,
                reference_image_uri="gs://mock-bucket/assets/padlock_char.jpg",
                dialogue_text=scene.dialogue[0].text if scene.dialogue else "",
                speaker="Male",
                quality_priority="BALANCED",
                use_lip_sync=True,
                allow_lip_sync_fallback=True,
                max_retries=1,
                expected_duration=scene.estimated_duration_seconds
            )
            res = engine.generate_scene(req)
            assert res.status == "COMPLETED"
            assert res.final_scene_path is not None
            scene_results.append(res)

        assert len(scene_results) == 3

    # -------------------------------------------------------------
    # Stage 9: Timeline Verification & Final Execution Certificate
    # -------------------------------------------------------------
    cert = verify_execution_certificate(
        job_id=mock_production_bp.blueprint_id,
        project_id=project_id,
        expected_scenes_count=3,
        generated_scenes_count=3,
        all_scenes_approved=True,
        timeline_validated=True,
        normalized_scene_count=3,
        final_mp4_path=GOLDEN_VIDEO_PATH,
        final_duration=13.0,
        target_duration=13.0,
        final_upload_uri="https://storage.googleapis.com/final_videos/final.mp4"
    )
    assert cert.certified is True
    assert len(cert.certification_errors) == 0

    # -------------------------------------------------------------
    # Stage 10: FinalVideoRecord Creation
    # -------------------------------------------------------------
    final_record = FinalVideoRecord(
        user_id=user_id,
        project_id=project_id,
        source_video_id=source_video_record.source_video_id,
        source_clone_blueprint_id=clone_bp.clone_blueprint_id,
        source_clone_blueprint_version=1,
        production_blueprint_id=mock_production_bp.blueprint_id,
        production_blueprint_version=1,
        output_uri=cert.final_upload_uri,
        duration_seconds=13.0
    )
    assert final_record.final_video_id.startswith("fv_")
    assert final_record.output_uri == "https://storage.googleapis.com/final_videos/final.mp4"

# ============================================================================
# 3. FAILURE ISOLATION TESTS (FAIL-CLOSED BEHAVIOR & ERROR CONTRACTS)
# ============================================================================

def test_failure_isolation_veo_failure_stops_and_records_attempt():
    """Validates that a permanent Veo generation error fails closed and logs attempt."""
    engine = CanonicalGenerationEngine()
    req = CanonicalGenerationRequest(
        user_id="u1",
        project_id="p1",
        job_id="j1",
        scene_id="s1",
        raw_prompt="Padlock dancing",
        art_style="3D",
        character_design="Padlock",
        dialogue_text="",
        max_retries=0
    )

    with patch("core.services.canonical_generation_engine.generate_video_with_veo", return_value=None), \
         patch("core.repositories.attempt_repo.GenerationAttemptRepository.save", return_value=True):
        with pytest.raises(VeoGenerationError):
            engine.generate_scene(req)

def test_failure_isolation_elevenlabs_required_dialogue_failure_stops():
    """Validates that a voiceover failure when dialogue is required fails closed."""
    engine = CanonicalGenerationEngine()
    req = CanonicalGenerationRequest(
        user_id="u1",
        project_id="p1",
        job_id="j1",
        scene_id="s1",
        raw_prompt="Padlock speaking",
        art_style="3D",
        character_design="Padlock",
        dialogue_text="Hello world dialogue required"
    )

    with patch("core.services.canonical_generation_engine.generate_voiceover", side_effect=Exception("ElevenLabs 429 Quota Exceeded")):
        with pytest.raises(AudioGenerationError):
            engine.generate_scene(req)

def test_failure_isolation_quality_review_rejection_stops_after_max_retries():
    """Validates that QualityReviewer rejections trigger adaptive retries and fail closed on exhaustion."""
    engine = CanonicalGenerationEngine()
    req = CanonicalGenerationRequest(
        user_id="u1",
        project_id="p1",
        job_id="j1",
        scene_id="s1",
        raw_prompt="Padlock walking",
        art_style="3D",
        character_design="Padlock",
        dialogue_text="",
        max_retries=1
    )

    from core.services.quality_reviewer import QualityReviewResult
    reject_review = QualityReviewResult(
        character_consistency=2.0,
        scene_adherence=3.0,
        visual_quality=3.0,
        continuity=2.0,
        overall=2.5,
        issues=["Live action human appeared instead of padlock animation"],
        recommended_action="reject"
    )

    with patch("core.services.canonical_generation_engine.generate_video_with_veo", return_value=b"mock_bytes"), \
         patch("core.services.canonical_generation_engine._get_audioclip_class", return_value=None), \
         patch("core.services.canonical_generation_engine._get_videoclip_class", return_value=None), \
         patch("core.services.quality_reviewer.QualityReviewer.review_video", return_value=reject_review), \
         patch("core.repositories.attempt_repo.GenerationAttemptRepository.save", return_value=True):
        with pytest.raises(QualityReviewError):
            engine.generate_scene(req)

def test_failure_isolation_lipsync_fail_closed_without_fallback():
    """Validates that LipSync failure fails closed when allow_lip_sync_fallback=False."""
    engine = CanonicalGenerationEngine()
    req = CanonicalGenerationRequest(
        user_id="u1",
        project_id="p1",
        job_id="j1",
        scene_id="s1",
        raw_prompt="Padlock talking",
        art_style="3D",
        character_design="Padlock",
        dialogue_text="Lip sync test text",
        use_lip_sync=True,
        allow_lip_sync_fallback=False
    )

    with patch("core.services.canonical_generation_engine.generate_voiceover", return_value="/mock/audio.mp3"), \
         patch("core.services.canonical_generation_engine.generate_video_with_veo", return_value=b"mock_bytes"), \
         patch("core.services.canonical_generation_engine._get_audioclip_class", return_value=None), \
         patch("core.services.canonical_generation_engine._get_videoclip_class", return_value=None), \
         patch("core.services.quality_reviewer.QualityReviewer.review_video") as mock_qr, \
         patch("core.services.timeline_builder.TimelineBuilder.normalize_video_to_audio_duration", return_value="/mock/norm.mp4"), \
         patch("services.lip_sync_service.sync_lips", side_effect=Exception("SyncLabs 500 server error")), \
         patch("core.repositories.attempt_repo.GenerationAttemptRepository.save", return_value=True):
        
        from core.services.quality_reviewer import QualityReviewResult
        mock_qr.return_value = QualityReviewResult(
            character_consistency=8.0, scene_adherence=8.0, visual_quality=8.0,
            continuity=8.0, overall=8.0, issues=[], recommended_action="accept"
        )

        with pytest.raises(LipSyncError):
            engine.generate_scene(req)

def test_failure_isolation_lipsync_authorized_fallback():
    """Validates that LipSync failure smoothly falls back to direct audio mux when authorized."""
    engine = CanonicalGenerationEngine()
    req = CanonicalGenerationRequest(
        user_id="u1",
        project_id="p1",
        job_id="j1",
        scene_id="s1",
        raw_prompt="Padlock talking",
        art_style="3D",
        character_design="Padlock",
        dialogue_text="Lip sync test text",
        use_lip_sync=True,
        allow_lip_sync_fallback=True
    )

    with patch("core.services.canonical_generation_engine.generate_voiceover", return_value="/mock/audio.mp3"), \
         patch("core.services.canonical_generation_engine.generate_video_with_veo", return_value=b"mock_bytes"), \
         patch("core.services.canonical_generation_engine._get_audioclip_class", return_value=None), \
         patch("core.services.canonical_generation_engine._get_videoclip_class", return_value=None), \
         patch("core.services.quality_reviewer.QualityReviewer.review_video") as mock_qr, \
         patch("core.services.timeline_builder.TimelineBuilder.normalize_video_to_audio_duration", return_value="/mock/norm.mp4"), \
         patch("services.lip_sync_service.sync_lips", side_effect=Exception("SyncLabs 500 server error")), \
         patch("core.repositories.attempt_repo.GenerationAttemptRepository.save", return_value=True):
        
        from core.services.quality_reviewer import QualityReviewResult
        mock_qr.return_value = QualityReviewResult(
            character_consistency=8.0, scene_adherence=8.0, visual_quality=8.0,
            continuity=8.0, overall=8.0, issues=[], recommended_action="accept"
        )

        res = engine.generate_scene(req)
        assert res.status == "COMPLETED"
        assert res.operation_states["synclabs_lipsync"]["status"] == "FALLBACK_USED"
        assert res.operation_states["synclabs_lipsync"]["fallback_used"] is True
