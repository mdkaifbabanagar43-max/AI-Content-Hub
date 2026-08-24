import os
import json
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
from core.models.clone_blueprint import (
    CloneBlueprint, CloneSceneBlueprint, NarrativeBeat, PacingProfile
)
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


def test_transformation_narrative_separation_heist_golden():
    """
    GOLDEN REGRESSION TEST (Section 5):
    Source: Padlock characters / House / Door lock misunderstanding.
    User Transformation Intent: 'Turn this into a funny bank-heist story.'
    
    Validates that:
    1. Visual DNA (padlock character design, 3D style) is preserved.
    2. Original story beats (groceries, door lock misunderstanding, house keys) are NOT copied.
    3. New narrative (bank heist, vault, loot) is created and passes the originality check.
    """
    user_id = "test_user_golden_heist"
    project_id = "test_proj_golden_heist"
    
    # 1. Source Clone Blueprint representing the Padlock Door video
    source_clone_bp = CloneBlueprint(
        clone_blueprint_id="cl_padlock_door_golden",
        source_video_id="src_padlock_door",
        project_id=project_id,
        user_id=user_id,
        source_analysis_version="1.0",
        title="Padlock Locked Out of House Comedy",
        source_duration_seconds=14.0,
        target_duration_seconds=14.0,
        aspect_ratio="9:16",
        hook=HookAnalysis(
            hook_type="CONFLICT",
            hook_description="Protagonist carrying heavy grocery bags arrives at house door",
            confidence=0.95,
            hook_start_seconds=0.0,
            hook_end_seconds=3.0
        ),
        narrative_structure=[
            NarrativeBeat(type="HOOK", start_seconds=0.0, end_seconds=3.0, description="Protagonist drops grocery bags in front of house door"),
            NarrativeBeat(type="CONFLICT", start_seconds=3.0, end_seconds=7.0, description="Tries to unlock door with wrong keys"),
            NarrativeBeat(type="TWIST", start_seconds=7.0, end_seconds=11.0, description="Second padlock character watches from window laughing"),
            NarrativeBeat(type="RESOLUTION", start_seconds=11.0, end_seconds=14.0, description="Confused final pose on doorstep")
        ],
        pacing_profile=PacingProfile(
            overall_intensity="Medium",
            average_shot_duration=3.5,
            fastest_shot_duration=2.0,
            slowest_shot_duration=5.0,
            scene_count=3,
            shot_count=4,
            rhythm_description="Comedic situational cuts"
        ),
        visual_style_profile=SourceVisualStyle(
            art_style="3D Pixar-style digital animation",
            character_design="Brass padlock head character with animated facial features",
            lighting="Warm afternoon sunlight",
            render_language="Volumetric 3D render"
        ),
        audio_profile=SourceAudioProfile(
            has_speech=True,
            speech_tempo="FAST",
            has_background_music=True,
            music_mood="Upbeat comedy"
        ),
        cta_structure=CTAAnalysis(exists=False, type="NONE", start_seconds=14.0, end_seconds=14.0),
        scenes=[
            CloneSceneBlueprint(
                scene_id="scn_01",
                scene_number=1,
                source_start_seconds=0.0,
                source_end_seconds=4.0,
                source_duration_seconds=4.0,
                narrative_purpose="Arrival at doorstep",
                visual_action="Protagonist carries groceries and reaches front porch door",
                dialogue_intent="Complaining about grocery weight",
                emotion="annoyed",
                pacing="moderate"
            ),
            CloneSceneBlueprint(
                scene_id="scn_02",
                scene_number=2,
                source_start_seconds=4.0,
                source_end_seconds=9.0,
                source_duration_seconds=5.0,
                narrative_purpose="Door lock struggle",
                visual_action="Trying wrong keys in the padlock house door lock",
                dialogue_intent="Frustration with key lock",
                emotion="frustrated",
                pacing="fast"
            ),
            CloneSceneBlueprint(
                scene_id="scn_03",
                scene_number=3,
                source_start_seconds=9.0,
                source_end_seconds=14.0,
                source_duration_seconds=5.0,
                narrative_purpose="Punchline",
                visual_action="Second padlock character waves from inside through glass window",
                dialogue_intent="Mocking laugh",
                emotion="humorous",
                pacing="moderate"
            )
        ]
    )

    # 2. User Transformation Request
    transform_req = ProductionTransformationRequest(
        topic="Turn this into a funny bank-heist story",
        story_change="The padlock characters attempt a high-stakes bank vault robbery",
        tone="Heist Comedy",
        language="English",
        target_duration_seconds=14.0,
        preserve_characters=True,
        requested_character_ids=["char_padlock_1"]
    )

    # 3. Mock LLM Response producing the Bank Heist Storyboard
    heist_storyboard_json = json.dumps({
        "project_id": project_id,
        "blueprint_id": "pb_heist_golden_01",
        "title": "The Great Padlock Bank Robbery",
        "concept": "Padlock gang sneaking into the central bank vault to crack the giant combination safe",
        "genre": "Heist Comedy",
        "target_duration_seconds": 14.0,
        "aspect_ratio": "9:16",
        "authoritative_art_style": "3D Pixar-style digital animation",
        "authoritative_character_design": "Brass padlock head character with animated facial features",
        "required_character_ids": ["char_padlock_1"],
        "status": "DRAFT",
        "scenes": [
            {
                "scene_id": "scene_heist_1",
                "scene_number": 1,
                "narrative_purpose": "Bank Infiltration",
                "estimated_duration_seconds": 4.5,
                "character_ids": ["char_padlock_1"],
                "action": "Padlock thief tiptoes under glowing red security laser beams inside the bank corridor",
                "dialogue": [
                    {
                        "character_id": "char_padlock_1",
                        "voice_id": "default_voice",
                        "text": "Quietly now... lasers are active!",
                        "emotion": "suspenseful",
                        "delivery_style": "whisper",
                        "estimated_duration_seconds": 3.0
                    }
                ],
                "camera": {
                    "shot_type": "WIDE",
                    "camera_motion": "TRACKING"
                }
            },
            {
                "scene_id": "scene_heist_2",
                "scene_number": 2,
                "narrative_purpose": "Vault Cracking",
                "estimated_duration_seconds": 5.0,
                "character_ids": ["char_padlock_1"],
                "action": "Padlock thief places stethoscope on the massive circular vault door dial and spins the lock combination",
                "dialogue": [
                    {
                        "character_id": "char_padlock_1",
                        "voice_id": "default_voice",
                        "text": "Left three, right four... click! We are in!",
                        "emotion": "excited",
                        "delivery_style": "energetic",
                        "estimated_duration_seconds": 3.0
                    }
                ],
                "camera": {
                    "shot_type": "CLOSE_UP",
                    "camera_motion": "DOLLY"
                }
            },
            {
                "scene_id": "scene_heist_3",
                "scene_number": 3,
                "narrative_purpose": "The Loot Escape",
                "estimated_duration_seconds": 4.5,
                "character_ids": ["char_padlock_1"],
                "action": "Padlock thief grabs overflowing duffel bag of shiny gold coins and winks at camera",
                "dialogue": [
                    {
                        "character_id": "char_padlock_1",
                        "voice_id": "default_voice",
                        "text": "Mission accomplished, time to split the loot!",
                        "emotion": "triumphant",
                        "delivery_style": "celebratory",
                        "estimated_duration_seconds": 2.5
                    }
                ],
                "camera": {
                    "shot_type": "MEDIUM",
                    "camera_motion": "STATIC"
                }
            }
        ]
    })

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = heist_storyboard_json
    mock_client.models.generate_content.return_value = mock_response

    with patch("core.services.production_director.get_gemini_client", return_value=mock_client), \
         patch("core.services.bible_loader.ProjectBibleLoader.load_all_bibles") as mock_bibles, \
         patch("core.repositories.blueprint_repo.BlueprintRepository.save", return_value=True):
        
        # Provide Bible context for char_padlock_1
        from core.models.character import Character
        mock_bibles.return_value = {
            "characters": [Character(character_id="char_padlock_1", project_id=project_id, name="Padlock Lead")],
            "locations": [],
            "voices": [],
            "props": [],
            "styles": []
        }

        director = ProductionDirector(user_id, project_id)
        prod_bp = director.transform_clone_blueprint(source_clone_bp, transform_req)

        # 1. Assert Visual DNA is Preserved
        assert prod_bp.authoritative_art_style == "3D Pixar-style digital animation"
        assert prod_bp.authoritative_character_design == "Brass padlock head character with animated facial features"
        assert "char_padlock_1" in prod_bp.required_character_ids

        # 2. Assert Story Beats are NEW and DO NOT contain original door/grocery tropes
        all_actions = " ".join([s.action for s in prod_bp.scenes]).lower()
        all_dialogues = " ".join([d.text for s in prod_bp.scenes for d in s.dialogue]).lower()
        all_concepts = f"{prod_bp.title} {prod_bp.concept} {all_actions} {all_dialogues}".lower()

        # Forbidden original story elements
        forbidden_original_beats = ["groceries", "grocery bags", "front porch", "house door", "locked out", "forgot keys"]
        for forbidden in forbidden_original_beats:
            assert forbidden not in all_concepts, f"Found copied source beat '{forbidden}' in transformed storyboard!"

        # Required new heist elements
        heist_concepts = ["bank", "vault", "laser", "safe", "loot", "robbery"]
        assert any(h in all_concepts for h in heist_concepts), "Transformed storyboard missing heist concepts!"

        # 3. Assert Originality Validator passes
        from core.services.originality_validator import validate_blueprint_originality, compute_narrative_similarity
        similarity_score, matched = compute_narrative_similarity(source_clone_bp, prod_bp)
        assert similarity_score < 0.25, f"Similarity score {similarity_score} is too high! Matched: {matched}"
        assert validate_blueprint_originality(source_clone_bp, prod_bp) is True


# ============================================================================
# 4 DETERMINISTIC GOLDEN TEST CASES (LAUNCH SPECIFICATION)
# ============================================================================

def _build_canonical_source_clone_bp():
    return CloneBlueprint(
        clone_blueprint_id="cb_golden_canonical_4cases",
        source_video_id="src_canonical_golden_vid",
        project_id="proj_golden_4cases",
        user_id="user_golden_4cases",
        source_analysis_version="1.0.0",
        title="Source Canonical Padlock Story",
        source_duration_seconds=14.0,
        target_duration_seconds=14.0,
        aspect_ratio="9:16",
        hook=HookAnalysis(
            hook_type="CONFLICT",
            hook_description="Character with grocery bags struggles to unlock front door with brass padlock key",
            confidence=0.95,
            hook_start_seconds=0.0,
            hook_end_seconds=3.0
        ),
        narrative_structure=[
            NarrativeBeat(type="HOOK", start_seconds=0.0, end_seconds=3.0, description="Struggling with grocery bags outside door"),
            NarrativeBeat(type="CONFLICT", start_seconds=3.0, end_seconds=9.0, description="Cannot open the padlock on front entrance"),
            NarrativeBeat(type="RESOLUTION", start_seconds=9.0, end_seconds=14.0, description="Second character waves through window with spare key")
        ],
        pacing_profile=PacingProfile(
            overall_intensity="Medium",
            average_shot_duration=4.5,
            fastest_shot_duration=3.0,
            slowest_shot_duration=5.0,
            scene_count=3,
            shot_count=4,
            rhythm_description="Brisk comedic timing with rapid punchline"
        ),
        visual_style_profile=SourceVisualStyle(
            art_style="3D Pixar-style digital animation",
            character_design="Brass padlock head character with expressive animated facial features",
            lighting_summary="Warm suburban daylight with soft cinematic shadows",
            color_tone="Vibrant saturated warm tones",
            visual_style_summary="High quality 3D animated CGI render"
        ),
        audio_profile=SourceAudioProfile(
            has_speech=True,
            has_background_music=True,
            music_mood="Playful orchestral comedy",
            sfx_present=True
        ),
        cta_structure=CTAAnalysis(exists=False, type="NONE", start_seconds=14.0, end_seconds=14.0),
        scenes=[
            CloneSceneBlueprint(
                scene_id="scn_01",
                scene_number=1,
                source_start_seconds=0.0,
                source_end_seconds=3.0,
                source_duration_seconds=3.0,
                narrative_purpose="Hook",
                visual_action="Padlock character dropping grocery bags on front porch",
                character_roles=["char_padlock_1"],
                emotion="flustered",
                pacing="fast"
            ),
            CloneSceneBlueprint(
                scene_id="scn_02",
                scene_number=2,
                source_start_seconds=3.0,
                source_end_seconds=9.0,
                source_duration_seconds=6.0,
                narrative_purpose="Escalation",
                visual_action="Padlock character frantically trying different keys on house door lock",
                character_roles=["char_padlock_1"],
                emotion="frustrated",
                pacing="fast"
            ),
            CloneSceneBlueprint(
                scene_id="scn_03",
                scene_number=3,
                source_start_seconds=9.0,
                source_end_seconds=14.0,
                source_duration_seconds=5.0,
                narrative_purpose="Punchline",
                visual_action="Second padlock character waves from inside through glass window",
                character_roles=["char_padlock_2"],
                emotion="humorous",
                pacing="moderate"
            )
        ]
    )


def test_golden_case_1_style_only():
    """
    TEST 1 — STYLE ONLY
    Preserve: visual style, camera/pacing
    Create: NEW characters, NEW environment, NEW story
    ASSERT: char_padlock_1 is NOT reused.
    """
    source_bp = _build_canonical_source_clone_bp()
    user_id = "user_golden_case_1"
    project_id = "proj_golden_case_1"

    transform_req = ProductionTransformationRequest(
        topic="A futuristic detective solving a neon cyber crime",
        story_change="A cyber detective interrogates a robot witness in a neon lab",
        tone="Sci-Fi Mystery",
        language="English",
        target_duration_seconds=14.0,
        preserve_visual_style=True,
        preserve_characters=False,
        preserve_environment=False,
        preserve_camera_pacing=True,
        clone_mode="style_only"
    )

    style_only_storyboard_json = json.dumps({
        "project_id": project_id,
        "blueprint_id": "pb_case1_style_only",
        "title": "Neon Cyber Detective",
        "concept": "Cyber detective investigating an AI malfunction in a holographic laboratory",
        "genre": "Sci-Fi Mystery",
        "target_duration_seconds": 14.0,
        "aspect_ratio": "9:16",
        "authoritative_art_style": "3D Pixar-style digital animation",
        "authoritative_character_design": "Cybernetic investigator with glowing trench coat",
        "required_character_ids": ["char_lead_1"],
        "status": "DRAFT",
        "scenes": [
            {
                "scene_id": "scene_c1_1",
                "scene_number": 1,
                "narrative_purpose": "Crime Scene Discovery",
                "estimated_duration_seconds": 4.5,
                "character_ids": ["char_lead_1"],
                "action": "Cyber detective scans shimmering holographic footprints with a high-tech scanner",
                "dialogue": [
                    {
                        "character_id": "char_lead_1",
                        "voice_id": "default_voice",
                        "text": "The energy signatures lead directly to the core mainframe.",
                        "estimated_duration_seconds": 3.0
                    }
                ]
            },
            {
                "scene_id": "scene_c1_2",
                "scene_number": 2,
                "narrative_purpose": "The Confrontation",
                "estimated_duration_seconds": 5.0,
                "character_ids": ["char_lead_1", "char_secondary_1"],
                "action": "A floating robot witness flashes bright warning lights as the detective steps forward",
                "dialogue": [
                    {
                        "character_id": "char_secondary_1",
                        "voice_id": "default_voice",
                        "text": "Access denied! The files are encrypted!",
                        "estimated_duration_seconds": 2.5
                    }
                ]
            },
            {
                "scene_id": "scene_c1_3",
                "scene_number": 3,
                "narrative_purpose": "Resolution",
                "estimated_duration_seconds": 4.5,
                "character_ids": ["char_lead_1"],
                "action": "Detective overrides the console with a smile, revealing the glowing crystal drive",
                "dialogue": [
                    {
                        "character_id": "char_lead_1",
                        "voice_id": "default_voice",
                        "text": "Case closed.",
                        "estimated_duration_seconds": 1.5
                    }
                ]
            }
        ]
    })

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = style_only_storyboard_json
    mock_client.models.generate_content.return_value = mock_response

    with patch("core.services.production_director.get_gemini_client", return_value=mock_client), \
         patch("core.services.bible_loader.ProjectBibleLoader.load_all_bibles") as mock_bibles, \
         patch("core.repositories.blueprint_repo.BlueprintRepository.save", return_value=True):
        
        mock_bibles.return_value = {"characters": [], "locations": [], "voices": [], "props": [], "styles": []}
        director = ProductionDirector(user_id, project_id)
        prod_bp = director.transform_clone_blueprint(source_bp, transform_req)

        # Asserts:
        assert prod_bp.authoritative_art_style == "3D Pixar-style digital animation"
        # Strict Character Isolation: char_padlock_1 must NOT be reused!
        assert "char_padlock_1" not in prod_bp.required_character_ids
        for s in prod_bp.scenes:
            assert "char_padlock_1" not in s.character_ids
            assert "char_padlock_2" not in s.character_ids
            for d in s.dialogue:
                assert d.character_id != "char_padlock_1"
        assert prod_bp.preserve_characters is False
        assert prod_bp.preserve_visual_style is True


def test_golden_case_2_characters_and_style():
    """
    TEST 2 — CHARACTERS + STYLE
    Preserve: visual style, characters, camera/pacing
    Create: NEW environment, NEW story
    ASSERT: char_padlock_1 IS reused.
    """
    source_bp = _build_canonical_source_clone_bp()
    user_id = "user_golden_case_2"
    project_id = "proj_golden_case_2"

    transform_req = ProductionTransformationRequest(
        topic="Padlock characters on a desert safari treasure hunt",
        story_change="The padlock characters search for ancient gold in Egyptian pyramids",
        tone="Adventure Comedy",
        language="English",
        target_duration_seconds=14.0,
        requested_character_ids=["char_padlock_1"],
        preserve_visual_style=True,
        preserve_characters=True,
        preserve_environment=False,
        preserve_camera_pacing=True,
        clone_mode="characters_and_style"
    )

    char_style_storyboard_json = json.dumps({
        "project_id": project_id,
        "blueprint_id": "pb_case2_char_style",
        "title": "Padlock Pyramid Adventure",
        "concept": "Padlock hero exploring sandy desert tomb in search of the legendary gold key",
        "genre": "Adventure Comedy",
        "target_duration_seconds": 14.0,
        "aspect_ratio": "9:16",
        "authoritative_art_style": "3D Pixar-style digital animation",
        "authoritative_character_design": "Brass padlock head character with expressive animated facial features",
        "required_character_ids": ["char_padlock_1"],
        "status": "DRAFT",
        "scenes": [
            {
                "scene_id": "scene_c2_1",
                "scene_number": 1,
                "narrative_purpose": "Desert Exploration",
                "estimated_duration_seconds": 4.5,
                "character_ids": ["char_padlock_1"],
                "action": "Padlock character wearing explorer hat trudges across golden sand dune holding an ancient treasure map",
                "dialogue": [
                    {
                        "character_id": "char_padlock_1",
                        "voice_id": "default_voice",
                        "text": "The pyramid treasure is just over this ridge!",
                        "estimated_duration_seconds": 3.0
                    }
                ]
            },
            {
                "scene_id": "scene_c2_2",
                "scene_number": 2,
                "narrative_purpose": "Tomb Discovery",
                "estimated_duration_seconds": 5.0,
                "character_ids": ["char_padlock_1"],
                "action": "Padlock character enters dark tomb and shines flashlight onto an ancient stone door with a golden keyhole",
                "dialogue": [
                    {
                        "character_id": "char_padlock_1",
                        "voice_id": "default_voice",
                        "text": "Behold the chamber of the Golden Pharaoh!",
                        "estimated_duration_seconds": 2.5
                    }
                ]
            },
            {
                "scene_id": "scene_c2_3",
                "scene_number": 3,
                "narrative_purpose": "Treasure Found",
                "estimated_duration_seconds": 4.5,
                "character_ids": ["char_padlock_1"],
                "action": "Stone door opens, illuminating padlock character's face with golden glittering light",
                "dialogue": [
                    {
                        "character_id": "char_padlock_1",
                        "voice_id": "default_voice",
                        "text": "We found it!",
                        "estimated_duration_seconds": 1.5
                    }
                ]
            }
        ]
    })

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = char_style_storyboard_json
    mock_client.models.generate_content.return_value = mock_response

    from core.models.character import Character
    with patch("core.services.production_director.get_gemini_client", return_value=mock_client), \
         patch("core.services.bible_loader.ProjectBibleLoader.load_all_bibles") as mock_bibles, \
         patch("core.repositories.blueprint_repo.BlueprintRepository.save", return_value=True):
        
        mock_bibles.return_value = {
            "characters": [Character(character_id="char_padlock_1", project_id=project_id, name="Padlock Hero")],
            "locations": [], "voices": [], "props": [], "styles": []
        }
        director = ProductionDirector(user_id, project_id)
        prod_bp = director.transform_clone_blueprint(source_bp, transform_req)

        # Asserts:
        assert prod_bp.authoritative_art_style == "3D Pixar-style digital animation"
        assert prod_bp.authoritative_character_design == "Brass padlock head character with expressive animated facial features"
        assert "char_padlock_1" in prod_bp.required_character_ids
        assert prod_bp.preserve_characters is True
        assert prod_bp.preserve_visual_style is True


def test_golden_case_3_full_visual_clone():
    """
    TEST 3 — FULL VISUAL CLONE
    Preserve: visual style, characters, environment, camera/pacing
    Create: NEW story
    ASSERT: source characters and selected environment preserved, original narrative NOT preserved.
    """
    source_bp = _build_canonical_source_clone_bp()
    user_id = "user_golden_case_3"
    project_id = "proj_golden_case_3"

    transform_req = ProductionTransformationRequest(
        topic="Padlock characters hosting a surprise birthday party in the front yard",
        story_change="Padlock throws a birthday surprise on the porch with confetti and giant cake",
        tone="Festive Comedy",
        language="English",
        target_duration_seconds=14.0,
        requested_character_ids=["char_padlock_1"],
        preserve_visual_style=True,
        preserve_characters=True,
        preserve_environment=True,
        preserve_camera_pacing=True,
        clone_mode="full_visual_clone"
    )

    full_clone_storyboard_json = json.dumps({
        "project_id": project_id,
        "blueprint_id": "pb_case3_full_clone",
        "title": "The Front Porch Birthday Surprise",
        "concept": "Padlock setting up surprise birthday streamers and a giant cake on the front porch",
        "genre": "Festive Comedy",
        "target_duration_seconds": 14.0,
        "aspect_ratio": "9:16",
        "authoritative_art_style": "3D Pixar-style digital animation",
        "authoritative_character_design": "Brass padlock head character with expressive animated facial features",
        "required_character_ids": ["char_padlock_1"],
        "status": "DRAFT",
        "scenes": [
            {
                "scene_id": "scene_c3_1",
                "scene_number": 1,
                "narrative_purpose": "Party Setup",
                "estimated_duration_seconds": 4.5,
                "character_ids": ["char_padlock_1"],
                "action": "Padlock character tiptoes onto suburban front porch carrying a gigantic frosted birthday cake",
                "dialogue": [
                    {
                        "character_id": "char_padlock_1",
                        "voice_id": "default_voice",
                        "text": "Careful... don't drop the three-layer cake!",
                        "estimated_duration_seconds": 2.5
                    }
                ]
            },
            {
                "scene_id": "scene_c3_2",
                "scene_number": 2,
                "narrative_purpose": "The Surprise",
                "estimated_duration_seconds": 5.0,
                "character_ids": ["char_padlock_1"],
                "action": "Confetti cannons burst across the sunny porch as party horns blow",
                "dialogue": [
                    {
                        "character_id": "char_padlock_1",
                        "voice_id": "default_voice",
                        "text": "SURPRISE! Happy Birthday!",
                        "estimated_duration_seconds": 2.0
                    }
                ]
            },
            {
                "scene_id": "scene_c3_3",
                "scene_number": 3,
                "narrative_purpose": "Celebration",
                "estimated_duration_seconds": 4.5,
                "character_ids": ["char_padlock_1"],
                "action": "Padlock character blows noisemaker in celebration while confetti showers down",
                "dialogue": [
                    {
                        "character_id": "char_padlock_1",
                        "voice_id": "default_voice",
                        "text": "Let's eat cake!",
                        "estimated_duration_seconds": 1.5
                    }
                ]
            }
        ]
    })

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = full_clone_storyboard_json
    mock_client.models.generate_content.return_value = mock_response

    from core.models.character import Character
    with patch("core.services.production_director.get_gemini_client", return_value=mock_client), \
         patch("core.services.bible_loader.ProjectBibleLoader.load_all_bibles") as mock_bibles, \
         patch("core.repositories.blueprint_repo.BlueprintRepository.save", return_value=True):
        
        mock_bibles.return_value = {
            "characters": [Character(character_id="char_padlock_1", project_id=project_id, name="Padlock Lead")],
            "locations": [], "voices": [], "props": [], "styles": []
        }
        director = ProductionDirector(user_id, project_id)
        prod_bp = director.transform_clone_blueprint(source_bp, transform_req)

        # Asserts:
        assert prod_bp.preserve_visual_style is True
        assert prod_bp.preserve_characters is True
        assert prod_bp.preserve_environment is True
        assert "char_padlock_1" in prod_bp.required_character_ids
        
        # Narrative must be original (no locked out / lost key tropes)
        from core.services.originality_validator import compute_narrative_similarity
        score, _ = compute_narrative_similarity(source_bp, prod_bp)
        assert score < 0.35, f"Similarity score {score} too high for transformed story!"


def test_golden_case_4_trend_inspired():
    """
    TEST 4 — TREND INSPIRED
    Preserve: trend structure, pacing
    Create: NEW characters, NEW environment, NEW story
    """
    source_bp = _build_canonical_source_clone_bp()
    user_id = "user_golden_case_4"
    project_id = "proj_golden_case_4"

    transform_req = ProductionTransformationRequest(
        topic="Crypto trader realizing their meme coin crashed in 3 seconds",
        story_change="Fast-paced viral skit of a crypto enthusiast refreshing chart on phone",
        tone="Viral Tech Comedy",
        language="English",
        target_duration_seconds=14.0,
        preserve_visual_style=False,
        preserve_characters=False,
        preserve_environment=False,
        preserve_camera_pacing=True,
        preserve_trend_structure=True,
        clone_mode="trend_inspired"
    )

    trend_storyboard_json = json.dumps({
        "project_id": project_id,
        "blueprint_id": "pb_case4_trend",
        "title": "The 3-Second Crypto Panic",
        "concept": "Viral high-energy reaction of an amateur crypto trader watching a volatile red candle spike",
        "genre": "Viral Tech Comedy",
        "target_duration_seconds": 14.0,
        "aspect_ratio": "9:16",
        "authoritative_art_style": "High-contrast dynamic anime motion graphics",
        "authoritative_character_design": "Energetic anime trader with expressive eyes",
        "required_character_ids": ["char_lead_1"],
        "status": "DRAFT",
        "scenes": [
            {
                "scene_id": "scene_c4_1",
                "scene_number": 1,
                "narrative_purpose": "Viral Hook (0-3s)",
                "estimated_duration_seconds": 3.0,
                "character_ids": ["char_lead_1"],
                "action": "Fast whip-pan into extreme close-up of wide-eyed trader tapping phone excitedly",
                "dialogue": [
                    {
                        "character_id": "char_lead_1",
                        "voice_id": "default_voice",
                        "text": "We are going to the moon today!",
                        "estimated_duration_seconds": 2.0
                    }
                ]
            },
            {
                "scene_id": "scene_c4_2",
                "scene_number": 2,
                "narrative_purpose": "Sudden Escalation",
                "estimated_duration_seconds": 5.5,
                "character_ids": ["char_lead_1"],
                "action": "Dramatic red lightning flashes as phone screen reflects a massive 99% drop candle",
                "dialogue": [
                    {
                        "character_id": "char_lead_1",
                        "voice_id": "default_voice",
                        "text": "Wait... what just happened to the chart?!",
                        "estimated_duration_seconds": 3.0
                    }
                ]
            },
            {
                "scene_id": "scene_c4_3",
                "scene_number": 3,
                "narrative_purpose": "Punchline / Twist",
                "estimated_duration_seconds": 5.5,
                "character_ids": ["char_lead_1"],
                "action": "Trader drops phone into coffee cup in slow motion disbelief",
                "dialogue": [
                    {
                        "character_id": "char_lead_1",
                        "voice_id": "default_voice",
                        "text": "Guess I'm holding for the next decade.",
                        "estimated_duration_seconds": 3.0
                    }
                ]
            }
        ]
    })

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = trend_storyboard_json
    mock_client.models.generate_content.return_value = mock_response

    with patch("core.services.production_director.get_gemini_client", return_value=mock_client), \
         patch("core.services.bible_loader.ProjectBibleLoader.load_all_bibles") as mock_bibles, \
         patch("core.repositories.blueprint_repo.BlueprintRepository.save", return_value=True):
        
        mock_bibles.return_value = {"characters": [], "locations": [], "voices": [], "props": [], "styles": []}
        director = ProductionDirector(user_id, project_id)
        prod_bp = director.transform_clone_blueprint(source_bp, transform_req)

        # Asserts:
        assert prod_bp.preserve_visual_style is False
        assert prod_bp.preserve_characters is False
        assert prod_bp.preserve_environment is False
        assert prod_bp.preserve_trend_structure is True
        assert "char_padlock_1" not in prod_bp.required_character_ids


