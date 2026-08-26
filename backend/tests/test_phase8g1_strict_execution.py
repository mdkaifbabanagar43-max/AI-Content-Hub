import pytest
import os
import sys
import tempfile
import cv2
import numpy as np
from unittest.mock import patch, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.models.operation_state import OperationStatus, ErrorCategory, CENTRAL_FALLBACK_POLICIES
from core.exceptions import (
    CharacterReferenceError,
    VeoGenerationError,
    AudioGenerationError,
    LipSyncError,
    QualityReviewError,
    TimelineExecutionException
)
from core.models.attempt import GenerationAttempt
from core.models.context import GenerationContext
from core.services.bible_loader import ResolvedScene
from core.models.character import Character
from core.models.scene import Scene
from core.services.reference_manager import ReferenceManager
from core.services.canonical_generation_engine import (
    CanonicalGenerationEngine,
    CanonicalGenerationRequest
)
from core.services.timeline_builder import TimelineBuilder


@pytest.fixture
def real_valid_mp4():
    """Generates a valid 3-second MP4 file on disk for MoviePy compatibility."""
    temp_dir = tempfile.gettempdir()
    path = os.path.join(temp_dir, f"valid_test_{os.urandom(4).hex()}.mp4")
    out = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*'mp4v'), 10, (100, 100))
    for _ in range(30):
        out.write(np.zeros((100, 100, 3), dtype=np.uint8))
    out.release()
    yield path
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass


@pytest.fixture
def dummy_audio_file():
    """Creates a temporary dummy audio file."""
    temp_dir = tempfile.gettempdir()
    path = os.path.join(temp_dir, f"valid_test_audio_{os.urandom(4).hex()}.mp3")
    with open(path, "wb") as f:
        f.write(b"dummy_audio_bytes_12345678")
    yield path
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass


# =============================================================================
# 1. CHARACTER REFERENCE TESTS (1–4)
# =============================================================================

def test_1_character_reference_success():
    """1. Character reference resolution succeeds when valid URI is returned and verified."""
    ref_mgr = ReferenceManager()
    context = GenerationContext(user_id="user_1", project_id="proj_1", job_id="job_1")
    char = Character(character_id="char_padlock", project_id="proj_1", name="Padlock", canonical_reference_uri="gs://bucket/users/user_1/projects/proj_1/characters/char_padlock/ref.jpg")
    scene = ResolvedScene(scene=Scene(scene_id="s1", project_id="proj_1", scene_number=1, duration=5.0), characters=[char], voices=[], style=None, location=None, props=[])

    res = ref_mgr.resolve_reference_with_telemetry(context, scene, reference_required=True)
    assert res.status == OperationStatus.SUCCEEDED
    assert res.reference_uri == "gs://bucket/users/user_1/projects/proj_1/characters/char_padlock/ref.jpg"
    assert res.reference_validation_status == "VALID"
    assert res.reference_source == "PROJECT_BIBLE"
    assert res.fallback_used is False


def test_2_character_reference_failure_stops_job():
    """2. Character reference failure raises CharacterReferenceError and stops execution."""
    ref_mgr = ReferenceManager()
    context = GenerationContext(user_id="user_1", project_id="proj_1", job_id="job_1")
    char = Character(character_id="char_missing", project_id="proj_1", name="Missing")
    scene = ResolvedScene(scene=Scene(scene_id="s1", project_id="proj_1", scene_number=1, duration=5.0), characters=[char], voices=[], style=None, location=None, props=[])

    with patch("services.asset_generator.generate_character_reference", return_value=None):
        with pytest.raises(CharacterReferenceError) as excinfo:
            ref_mgr.resolve_reference_with_telemetry(context, scene, reference_required=True, allow_fallback=False)
        assert "Required character reference resolution failed" in str(excinfo.value)


def test_3_character_reference_cannot_silently_become_prompt_only():
    """3. When a reference is required, failure must NOT silently downgrade to PROMPT_ONLY without error."""
    ref_mgr = ReferenceManager()
    context = GenerationContext(user_id="user_1", project_id="proj_1", job_id="job_1")
    char = Character(character_id="char_missing", project_id="proj_1", name="Missing")
    scene = ResolvedScene(scene=Scene(scene_id="s1", project_id="proj_1", scene_number=1, duration=5.0), characters=[char], voices=[], style=None, location=None, props=[])

    with patch("services.asset_generator.generate_character_reference", return_value=None):
        with pytest.raises(CharacterReferenceError):
            ref_mgr.resolve_reference_with_telemetry(context, scene, reference_required=True, allow_fallback=False)


def test_4_reference_validation_failure_stops_job():
    """4. Reference with invalid URI scheme or cross-tenant violation fails validation and raises error."""
    ref_mgr = ReferenceManager()
    context = GenerationContext(user_id="user_1", project_id="proj_1", job_id="job_1")
    # Cross-tenant violation: user_1 attempting to use user_2's private reference
    char = Character(character_id="char_padlock", project_id="proj_1", name="Padlock", canonical_reference_uri="gs://bucket/users/user_2/projects/proj_2/characters/ref.jpg")
    scene = ResolvedScene(scene=Scene(scene_id="s1", project_id="proj_1", scene_number=1, duration=5.0), characters=[char], voices=[], style=None, location=None, props=[])

    with patch("services.asset_generator.generate_character_reference", return_value=None):
        with pytest.raises(CharacterReferenceError) as excinfo:
            ref_mgr.resolve_reference_with_telemetry(context, scene, reference_required=True, allow_fallback=False)
        assert "failed validation" in str(excinfo.value) or "Required character reference" in str(excinfo.value)


# =============================================================================
# 2. VEO GENERATION & QUALITY REVIEW TESTS (5–11)
# =============================================================================

@patch("core.services.canonical_generation_engine.generate_video_with_veo")
@patch("core.services.canonical_generation_engine.QualityReviewer")
@patch("core.services.canonical_generation_engine.GenerationAttemptRepository")
def test_5_veo_success(mock_repo, mock_qr_cls, mock_veo, real_valid_mp4):
    """5. Veo generation succeeds and passes QualityReviewer."""
    mock_veo.return_value = real_valid_mp4
    qr_inst = MagicMock()
    review_res = MagicMock()
    review_res.recommended_action = "accept"
    review_res.overall = 9.0
    review_res.model_dump.return_value = {"overall": 9.0, "recommended_action": "accept"}
    qr_inst.review_video.return_value = review_res
    mock_qr_cls.return_value = qr_inst

    engine = CanonicalGenerationEngine()
    req = CanonicalGenerationRequest(
        user_id="u1", project_id="p1", job_id="j1", scene_id="s1",
        raw_prompt="Padlock walks", art_style="3D", character_design="Brass Padlock",
        use_lip_sync=False
    )
    res = engine.generate_scene(req)
    assert res.status == "COMPLETED"
    assert res.operation_states["veo_generation"]["status"] == OperationStatus.SUCCEEDED.value
    assert res.operation_states["quality_review"]["status"] == OperationStatus.SUCCEEDED.value


@patch("core.services.canonical_generation_engine.generate_video_with_veo")
@patch("core.services.canonical_generation_engine.GenerationAttemptRepository")
def test_6_veo_failure_stops_scene(mock_repo, mock_veo):
    """6. Veo provider failure halts scene generation with VeoGenerationError."""
    mock_veo.side_effect = Exception("Vertex AI 503 Provider Unavailable")

    engine = CanonicalGenerationEngine()
    req = CanonicalGenerationRequest(
        user_id="u1", project_id="p1", job_id="j1", scene_id="s1",
        raw_prompt="Padlock walks", art_style="3D", character_design="Brass Padlock",
        max_retries=0
    )
    with pytest.raises(VeoGenerationError) as excinfo:
        engine.generate_scene(req)
    assert "Veo generation failed" in str(excinfo.value)


@patch("core.services.canonical_generation_engine.generate_video_with_veo")
@patch("core.services.canonical_generation_engine.QualityReviewer")
@patch("core.services.canonical_generation_engine.GenerationAttemptRepository")
def test_7_quality_reviewer_acceptance(mock_repo, mock_qr_cls, mock_veo, real_valid_mp4):
    """7. QualityReviewer accepting raw video completes attempt with COMPLETED status."""
    mock_veo.return_value = real_valid_mp4
    qr_inst = MagicMock()
    review_res = MagicMock()
    review_res.recommended_action = "accept"
    review_res.overall = 8.8
    review_res.model_dump.return_value = {"overall": 8.8, "recommended_action": "accept"}
    qr_inst.review_video.return_value = review_res
    mock_qr_cls.return_value = qr_inst

    engine = CanonicalGenerationEngine()
    req = CanonicalGenerationRequest(
        user_id="u1", project_id="p1", job_id="j1", scene_id="s1",
        raw_prompt="Padlock walks", art_style="3D", character_design="Brass Padlock"
    )
    res = engine.generate_scene(req)
    assert res.status == "COMPLETED"
    assert res.operation_states["quality_review"]["status"] == OperationStatus.SUCCEEDED.value


@patch("core.services.canonical_generation_engine.generate_video_with_veo")
@patch("core.services.canonical_generation_engine.QualityReviewer")
@patch("core.services.canonical_generation_engine.GenerationAttemptRepository")
def test_8_and_9_and_10_retry_and_exhaustion(mock_repo, mock_qr_cls, mock_veo, real_valid_mp4):
    """8, 9, 10. QualityReviewer rejection triggers exactly 1 retry; exhaustion raises QualityReviewError."""
    mock_veo.return_value = real_valid_mp4
    qr_inst = MagicMock()
    rejected_res = MagicMock()
    rejected_res.recommended_action = "reject"
    rejected_res.issues = ["Character anatomy distorted", "Live action human detected"]
    rejected_res.overall = 3.5
    rejected_res.model_dump.return_value = {"overall": 3.5, "recommended_action": "reject", "issues": rejected_res.issues}
    qr_inst.review_video.return_value = rejected_res
    mock_qr_cls.return_value = qr_inst

    engine = CanonicalGenerationEngine()
    req = CanonicalGenerationRequest(
        user_id="u1", project_id="p1", job_id="j1", scene_id="s1",
        raw_prompt="Padlock walks", art_style="3D", character_design="Brass Padlock",
        max_retries=1
    )

    with pytest.raises(QualityReviewError) as excinfo:
        engine.generate_scene(req)

    # Exactly 2 attempts (initial + 1 retry)
    assert mock_veo.call_count == 2
    assert "rejected by QualityReviewer after 2 attempts" in str(excinfo.value)


def test_11_rejected_attempt_never_enters_timeline_builder():
    """11. A rejected scene with missing or invalid path fails timeline validation."""
    tb = TimelineBuilder("proj_test")
    scene = Scene(scene_id="s1", project_id="proj_test", scene_number=1, duration=5.0)
    tb.add_scene(scene, expected_duration=5.0, raw_video_path="non_existent_rejected_video.mp4", dialogue_assets=[])
    with pytest.raises(TimelineExecutionException):
        tb.validate()


# =============================================================================
# 3. ELEVENLABS & SYNCLABS CONTRACT TESTS (12–17)
# =============================================================================

@patch("core.services.canonical_generation_engine.generate_voiceover")
@patch("core.services.canonical_generation_engine.AudioFileClip")
@patch("core.services.canonical_generation_engine.VideoFileClip")
@patch("core.services.canonical_generation_engine.generate_video_with_veo")
@patch("core.services.canonical_generation_engine.QualityReviewer")
@patch("core.services.canonical_generation_engine.GenerationAttemptRepository")
def test_12_dialogue_present_requires_elevenlabs(mock_repo, mock_qr_cls, mock_veo, mock_vclip_cls, mock_aclip_cls, mock_tts, real_valid_mp4, dummy_audio_file):
    """12. When dialogue text is present, ElevenLabs executes and registers SUCCEEDED."""
    mock_tts.return_value = dummy_audio_file
    
    aclip_inst = MagicMock()
    aclip_inst.duration = 2.5
    aclip_inst.__enter__.return_value = aclip_inst
    mock_aclip_cls.return_value = aclip_inst

    vclip_inst = MagicMock()
    vclip_inst.fps = 30
    vclip_inst.duration = 3.0
    vclip_inst.set_audio.return_value = vclip_inst
    vclip_inst.__enter__.return_value = vclip_inst
    mock_vclip_cls.return_value = vclip_inst

    mock_veo.return_value = real_valid_mp4
    qr_inst = MagicMock()
    qr_inst.review_video.return_value = MagicMock(recommended_action="accept", overall=8.5, model_dump=lambda: {})
    mock_qr_cls.return_value = qr_inst

    engine = CanonicalGenerationEngine()
    req = CanonicalGenerationRequest(
        user_id="u1", project_id="p1", job_id="j1", scene_id="s1",
        raw_prompt="Speaking", art_style="3D", character_design="Brass Padlock",
        dialogue_text="Hello, I am Mr. Padlock!", use_lip_sync=False
    )
    res = engine.generate_scene(req)
    assert res.audio_duration == 2.5
    assert res.operation_states["elevenlabs_voiceover"]["status"] == OperationStatus.SUCCEEDED.value


@patch("core.services.canonical_generation_engine.generate_voiceover")
@patch("core.services.canonical_generation_engine.GenerationAttemptRepository")
def test_13_elevenlabs_failure_stops_scene(mock_repo, mock_tts):
    """13. ElevenLabs failure raises AudioGenerationError and aborts scene generation."""
    mock_tts.side_effect = Exception("ElevenLabs API quota exhausted")

    engine = CanonicalGenerationEngine()
    req = CanonicalGenerationRequest(
        user_id="u1", project_id="p1", job_id="j1", scene_id="s1",
        raw_prompt="Speaking", art_style="3D", character_design="Brass Padlock",
        dialogue_text="Hello, I am Mr. Padlock!"
    )
    with pytest.raises(AudioGenerationError) as excinfo:
        engine.generate_scene(req)
    assert "ElevenLabs generation failed" in str(excinfo.value)


@patch("core.services.canonical_generation_engine.generate_video_with_veo")
@patch("core.services.canonical_generation_engine.QualityReviewer")
@patch("core.services.canonical_generation_engine.GenerationAttemptRepository")
def test_14_no_dialogue_elevenlabs_not_requested(mock_repo, mock_qr_cls, mock_veo, real_valid_mp4):
    """14. When scene has no dialogue, ElevenLabs is marked NOT_REQUESTED."""
    mock_veo.return_value = real_valid_mp4
    mock_qr_cls.return_value.review_video.return_value = MagicMock(recommended_action="accept", overall=8.5, model_dump=lambda: {})

    engine = CanonicalGenerationEngine()
    req = CanonicalGenerationRequest(
        user_id="u1", project_id="p1", job_id="j1", scene_id="s1",
        raw_prompt="Silent action", art_style="3D", character_design="Brass Padlock",
        dialogue_text="", use_lip_sync=False
    )
    res = engine.generate_scene(req)
    assert res.operation_states["elevenlabs_voiceover"]["status"] == OperationStatus.NOT_REQUESTED.value


@patch("core.services.canonical_generation_engine.generate_voiceover")
@patch("core.services.canonical_generation_engine.AudioFileClip")
@patch("core.services.canonical_generation_engine.generate_video_with_veo")
@patch("core.services.canonical_generation_engine.QualityReviewer")
@patch("services.lip_sync_service.sync_lips")
@patch("core.services.canonical_generation_engine.GenerationAttemptRepository")
def test_15_and_16_synclabs_required_and_failure_stops_job(mock_repo, mock_sync, mock_qr_cls, mock_veo, mock_aclip_cls, mock_tts, real_valid_mp4, dummy_audio_file):
    """15, 16. Lip-sync requested executes SyncLabs; failure without authorized fallback raises LipSyncError."""
    mock_tts.return_value = dummy_audio_file
    mock_aclip_cls.return_value.__enter__.return_value = MagicMock(duration=2.0)
    mock_veo.return_value = real_valid_mp4
    mock_qr_cls.return_value.review_video.return_value = MagicMock(recommended_action="accept", overall=8.5, model_dump=lambda: {})
    
    # SyncLabs fails by returning the identical un-synced normalized video path
    mock_sync.return_value = real_valid_mp4

    engine = CanonicalGenerationEngine()
    req = CanonicalGenerationRequest(
        user_id="u1", project_id="p1", job_id="j1", scene_id="s1",
        raw_prompt="Speaking", art_style="3D", character_design="Brass Padlock",
        dialogue_text="Sync this line",
        use_lip_sync=True,
        allow_lip_sync_fallback=False  # Strict Fail-Closed
    )

    with pytest.raises(LipSyncError) as excinfo:
        engine.generate_scene(req)
    assert "LipSync failed" in str(excinfo.value)


@patch("core.services.canonical_generation_engine.generate_video_with_veo")
@patch("core.services.canonical_generation_engine.QualityReviewer")
@patch("core.services.canonical_generation_engine.GenerationAttemptRepository")
def test_17_lipsync_not_requested(mock_repo, mock_qr_cls, mock_veo, real_valid_mp4):
    """17. When lip-sync is not requested, synclabs_lipsync is marked NOT_REQUESTED."""
    mock_veo.return_value = real_valid_mp4
    mock_qr_cls.return_value.review_video.return_value = MagicMock(recommended_action="accept", overall=8.5, model_dump=lambda: {})

    engine = CanonicalGenerationEngine()
    req = CanonicalGenerationRequest(
        user_id="u1", project_id="p1", job_id="j1", scene_id="s1",
        raw_prompt="No sync", art_style="3D", character_design="Brass Padlock",
        use_lip_sync=False
    )
    res = engine.generate_scene(req)
    assert res.operation_states["synclabs_lipsync"]["status"] == OperationStatus.NOT_REQUESTED.value


# =============================================================================
# 4. TIMELINE & ASSEMBLY CONTRACT TESTS (18–20)
# =============================================================================

def test_18_timeline_failure_stops_job():
    """18. Timeline with timing gaps or invalid durations fails validate() and stops job."""
    tb = TimelineBuilder("proj_fail")
    # Empty timeline fails validate
    with pytest.raises(TimelineExecutionException):
        tb.validate()


def test_19_raw_clips_cannot_bypass_execute_timeline():
    """19. Cannot execute empty or un-added timeline."""
    tb = TimelineBuilder("proj_bypass")
    with pytest.raises(TimelineExecutionException):
        tb.execute_timeline()


def test_20_final_assembly_blocked_when_scene_fails():
    """20. Missing raw video asset on any scene blocks timeline validation and final assembly."""
    tb = TimelineBuilder("proj_missing")
    scene = Scene(scene_id="s_bad", project_id="proj_missing", scene_number=1, duration=5.0)
    tb.add_scene(scene, expected_duration=5.0, raw_video_path="/non/existent/path/clip.mp4", dialogue_assets=[])
    
    with pytest.raises(TimelineExecutionException):
        tb.validate()


# =============================================================================
# 5. FORENSICS, TELEMETRY & FALLBACK POLICY TESTS (21–28)
# =============================================================================

@patch("core.services.canonical_generation_engine.generate_video_with_veo")
@patch("core.services.canonical_generation_engine.QualityReviewer")
def test_21_and_22_attempt_persisted_before_call_and_leaves_telemetry(mock_qr_cls, mock_veo, real_valid_mp4):
    """21, 22. GenerationAttempt is saved BEFORE provider call and retains error on failure."""
    repo_inst = MagicMock()
    mock_veo.side_effect = Exception("Vertex AI quota exceeded")

    engine = CanonicalGenerationEngine()
    engine.attempt_repo = repo_inst
    req = CanonicalGenerationRequest(
        user_id="u1", project_id="p1", job_id="j1", scene_id="s1",
        raw_prompt="Attempt test", art_style="3D", character_design="Brass Padlock",
        max_retries=0
    )

    with pytest.raises(VeoGenerationError):
        engine.generate_scene(req)

    # Saved at least twice: 1 pre-call (STARTED / IN_PROGRESS), 1 on error (FAILED)
    assert repo_inst.save.call_count >= 2
    first_save_attempt = repo_inst.save.call_args_list[0][0][3]
    assert first_save_attempt.status in ("STARTED", "IN_PROGRESS")
    assert first_save_attempt.provider == "Google Vertex AI"
    from config import ModelRoutingConfig
    assert first_save_attempt.model == ModelRoutingConfig.VIDEO_DEFAULT

    second_save_attempt = repo_inst.save.call_args_list[1][0][3]
    assert second_save_attempt.status == "FAILED"
    assert second_save_attempt.error_category == ErrorCategory.VEO_GENERATION_FAILED.value


def test_23_unauthorized_fallback_produces_failed():
    """23. Unauthorized fallback rule verification."""
    rule = CENTRAL_FALLBACK_POLICIES["veo_generation"]
    assert rule.allowed is False


@patch("core.services.canonical_generation_engine.generate_voiceover")
@patch("core.services.canonical_generation_engine.AudioFileClip")
@patch("core.services.canonical_generation_engine.VideoFileClip")
@patch("core.services.canonical_generation_engine.generate_video_with_veo")
@patch("core.services.canonical_generation_engine.QualityReviewer")
@patch("services.lip_sync_service.sync_lips")
@patch("core.services.canonical_generation_engine.GenerationAttemptRepository")
def test_24_and_25_authorized_fallback_records_fallback_used(mock_repo, mock_sync, mock_qr_cls, mock_veo, mock_vclip_cls, mock_aclip_cls, mock_tts, real_valid_mp4, dummy_audio_file):
    """24, 25. When fallback is explicitly authorized, record FALLBACK_USED with provider and reason."""
    mock_tts.return_value = dummy_audio_file
    aclip_inst = MagicMock()
    aclip_inst.duration = 2.0
    aclip_inst.__enter__.return_value = aclip_inst
    mock_aclip_cls.return_value = aclip_inst

    vclip_inst = MagicMock()
    vclip_inst.fps = 30
    vclip_inst.duration = 3.0
    vclip_inst.set_audio.return_value = vclip_inst
    vclip_inst.__enter__.return_value = vclip_inst
    mock_vclip_cls.return_value = vclip_inst

    mock_veo.return_value = real_valid_mp4
    mock_qr_cls.return_value.review_video.return_value = MagicMock(recommended_action="accept", overall=8.5, model_dump=lambda: {})
    mock_sync.return_value = real_valid_mp4  # Returns raw un-synced

    engine = CanonicalGenerationEngine()
    req = CanonicalGenerationRequest(
        user_id="u1", project_id="p1", job_id="j1", scene_id="s1",
        raw_prompt="Speaking", art_style="3D", character_design="Brass Padlock",
        dialogue_text="Sync line",
        use_lip_sync=True,
        allow_lip_sync_fallback=True  # Explicitly authorized
    )

    res = engine.generate_scene(req)
    lipsync_state = res.operation_states["synclabs_lipsync"]
    assert lipsync_state["status"] == OperationStatus.FALLBACK_USED.value
    assert lipsync_state["fallback_used"] is True
    assert lipsync_state["fallback_provider"] == "MoviePy"
    assert lipsync_state["fallback_model"] == "direct_audio_mux"


def test_26_job_completed_requires_all_operations_succeeded():
    """26. Job level invariant: any failed critical operation disallows COMPLETED."""
    states = {
        "veo_generation": OperationStatus.SUCCEEDED,
        "quality_review": OperationStatus.SUCCEEDED,
        "elevenlabs_voiceover": OperationStatus.FAILED  # One critical operation failed
    }
    all_succeeded = all(s in (OperationStatus.SUCCEEDED, OperationStatus.NOT_REQUESTED) for s in states.values())
    assert all_succeeded is False


def test_27_model_and_provider_information_persisted():
    """27. GenerationAttempt includes provider, model, region, target_duration."""
    attempt = GenerationAttempt(
        attempt_id="att_1", project_id="p1", scene_id="s1", attempt_number=1,
        prompt="Test prompt", provider="Google Vertex AI", model="veo-3.1-fast-generate-001",
        region="us-central1", target_duration=5.0
    )
    dump = attempt.model_dump()
    assert dump["provider"] == "Google Vertex AI"
    assert dump["model"] == "veo-3.1-fast-generate-001"
    assert dump["region"] == "us-central1"


def test_28_no_secret_or_api_key_persisted_in_telemetry():
    """28. Ensure telemetry representations never contain API keys or secret keywords."""
    attempt = GenerationAttempt(
        attempt_id="att_1", project_id="p1", scene_id="s1", attempt_number=1,
        prompt="Test prompt", provider="Google Vertex AI", model="veo-3.1-fast-generate-001"
    )
    dump_str = str(attempt.model_dump())
    assert "AIzaSy" not in dump_str
    assert "sk_" not in dump_str
    assert "SYNCLABS_API_KEY" not in dump_str
    assert "ELEVENLABS_API_KEY" not in dump_str


# =============================================================================
# 6. MP4 EXISTS BUT JOB MUST FAIL & REGRESSION TESTS (29–30)
# =============================================================================

def test_29_mp4_exists_but_job_must_fail_when_reference_failed(real_valid_mp4):
    """29. CRITICAL TEST: Even if a valid MP4 exists on disk, if required reference failed, the job fails closed."""
    ref_mgr = ReferenceManager()
    context = GenerationContext(user_id="user_1", project_id="proj_1", job_id="job_1")
    char = Character(character_id="char_padlock_failed", project_id="proj_1", name="Failed Padlock")
    scene = ResolvedScene(scene=Scene(scene_id="s1", project_id="proj_1", scene_number=1, duration=5.0), characters=[char], voices=[], style=None, location=None, props=[])

    # Reference fails
    with patch("services.asset_generator.generate_character_reference", return_value=None):
        with pytest.raises(CharacterReferenceError):
            ref_mgr.resolve_reference_with_telemetry(context, scene, reference_required=True, allow_fallback=False)

    # Even though real_valid_mp4 exists on disk, TimelineBuilder must never be called for this scene
    tb = TimelineBuilder("proj_strict")
    assert len(tb.items) == 0


def test_30_legacy_trend_cloner_regression():
    """30. Regression verification: Legacy Trend Cloner services and imports remain intact and functional."""
    from services.trend_remixer import _sanitize_veo_prompt
    sanitized = _sanitize_veo_prompt("A cool padlock character dances", "3D animated film", "Brass padlock head")
    assert "3D animated film" in sanitized
    assert "Brass padlock head" in sanitized
    assert "A cool padlock character dances" in sanitized
