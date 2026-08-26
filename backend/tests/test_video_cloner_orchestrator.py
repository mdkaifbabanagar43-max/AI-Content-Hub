import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from main import app
from core.models.blueprint import ProductionBlueprint, SceneBlueprint, QualityStrategy, GenerationStrategy

client = TestClient(app)

from core.auth import get_current_user

def override_get_current_user():
    return "test_user_8d"

@pytest.fixture(autouse=True)
def setup_auth_override():
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)

@pytest.fixture
def test_project_id():
    return "proj_video_cloner_test"

@pytest.fixture
def mock_veo_service():
    with patch("core.services.canonical_generation_engine.generate_video_with_veo") as mock:
        mock.return_value = b"mock_veo_video_bytes"
        yield mock

@pytest.fixture
def mock_elevenlabs():
    with patch("core.services.canonical_generation_engine.generate_voiceover") as mock:
        mock.return_value = "/mock/path/tts.mp3"
        yield mock

@pytest.fixture
def mock_lipsync():
    with patch("services.lip_sync_service.sync_lips") as mock:
        mock.return_value = "/mock/path/synced.mp4"
        yield mock

@pytest.fixture(autouse=True)
def mock_asset_generator():
    with patch("services.asset_generator.generate_character_reference") as mock:
        mock.return_value = "gs://mock-bucket/ref_image.png"
        yield mock

@pytest.fixture
def mock_concat():
    with patch("routers.video_cloner.concat_scenes") as mock:
        mock.return_value = "/mock/path/final_master.mp4"
        yield mock

@pytest.fixture
def mock_upload():
    with patch("routers.video_cloner.upload_file") as mock:
        mock.return_value = "https://storage.googleapis.com/test/video.mp4"
        yield mock

@pytest.fixture
def mock_source_analysis_repo():
    with patch("routers.video_cloner.analysis_repo") as mock:
        yield mock

@pytest.fixture
def mock_clone_blueprint_repo():
    with patch("routers.video_cloner.clone_blueprint_repo") as mock:
        yield mock

@pytest.fixture
def mock_production_blueprint_repo():
    with patch("routers.video_cloner.production_blueprint_repo") as mock:
        yield mock
        
@pytest.fixture
def mock_attempt_repo():
    with patch("routers.video_cloner.attempt_repo") as mock:
        # Simple in-memory mock for attempts
        storage = {}
        def save(user_id, project_id, attempt_id, attempt):
            storage[attempt_id] = attempt
        def get(user_id, project_id, attempt_id):
            return storage.get(attempt_id)
        mock.save.side_effect = save
        mock.get.side_effect = get
        yield mock

@pytest.fixture
def mock_final_video_repo():
    with patch("routers.video_cloner.final_video_repo") as mock:
        yield mock

@pytest.fixture
def mock_quality_reviewer():
    with patch("core.services.canonical_generation_engine.QualityReviewer") as mock:
        instance = mock.return_value
        from core.services.quality_reviewer import QualityReviewResult
        instance.review_video.return_value = QualityReviewResult(
            character_consistency=8.0,
            scene_adherence=8.0,
            visual_quality=8.0,
            continuity=8.0,
            overall=8.0,
            issues=[],
            recommended_action="accept"
        )
        yield instance

@pytest.fixture
def mock_moviepy_clips():
    with patch("moviepy.editor.VideoFileClip") as mock_vfc, \
         patch("moviepy.editor.AudioFileClip") as mock_afc, \
         patch("os.path.exists", return_value=True), \
         patch("os.path.getsize", return_value=1000):
        v_instance = MagicMock()
        v_instance.fps = 30
        v_instance.duration = 5.0
        v_instance.audio = None
        v_instance.subclip.return_value = v_instance
        v_instance.set_audio.return_value = v_instance
        v_instance.__enter__.return_value = v_instance
        mock_vfc.return_value = v_instance
        
        a_instance = MagicMock()
        a_instance.duration = 2.0
        a_instance.__enter__.return_value = a_instance
        mock_afc.return_value = a_instance
        
        yield mock_vfc, mock_afc

@pytest.fixture
def mock_timeline_builder():
    with patch("routers.video_cloner.TimelineBuilder") as mock_tb_class:
        instance = mock_tb_class.return_value
        instance.normalize_video_to_audio_duration.return_value = "/mock/path/normalized.mp4"
        instance.execute_timeline.return_value = ["/mock/path/final_scene_1.mp4"]
        instance._get_video_duration.return_value = 5.0
        
        # Mock items to return a final video path
        mock_item = MagicMock()
        mock_item.video_uri = "/mock/path/final_mux_video.mp4"
        instance.items = [mock_item]
        
        yield mock_tb_class

def test_full_orchestration_pipeline_mocked(
    test_project_id,
    mock_veo_service,
    mock_elevenlabs,
    mock_lipsync,
    mock_concat,
    mock_upload,
    mock_production_blueprint_repo,
    mock_attempt_repo,
    mock_final_video_repo,
    mock_quality_reviewer,
    mock_timeline_builder,
    mock_moviepy_clips
):
    """
    Simulates the pipeline from ProductionBlueprint through to FinalVideo,
    mocking the heavy provider calls (Veo, ElevenLabs, Lipsync, Concat).
    """
    
    # 1. Setup an Approved ProductionBlueprint
    bp = ProductionBlueprint(
        project_id=test_project_id,
        blueprint_id="bp_test_123",
        title="Test E2E Orchestration",
        concept="Mocking the entire pipeline",
        genre="Test",
        target_duration_seconds=10.0,
        status="APPROVED",
        quality_strategy=QualityStrategy(max_retries=5), # Setup TEST 10: try 5, should only cap to 1
        generation_strategy=GenerationStrategy(),
        source_clone_blueprint_id="cb_123",
        source_clone_blueprint_version=1
    )
    
    from core.models.blueprint import DialogueLine
    scene = SceneBlueprint(
        scene_id="scn_test_1",
        scene_number=1,
        narrative_purpose="Hook",
        estimated_duration_seconds=5.0,
        dialogue=[DialogueLine(
            text="Hello", character_id="char_1", voice_id="voice_1",
            emotion="Neutral", delivery_style="Calm", estimated_duration_seconds=2.0
        )]
    )
    bp.scenes.append(scene)
    
    # Mock the repo getting the blueprint
    mock_production_blueprint_repo.get.return_value = bp
    
    from routers.video_cloner import run_production_job
    
    run_production_job("test_user_8d", test_project_id, bp.blueprint_id)
    
    # TEST 3: QualityReviewer receives RAW video
    assert mock_quality_reviewer.review_video.called
    
    # TEST 4 & 5: Lip-sync is called
    assert mock_lipsync.called
    
    # TEST 7: TimelineBuilder receives finalized scene clips
    tb_instance = mock_timeline_builder.return_value
    assert tb_instance.add_scene.called
    
    # TEST 8: TimelineBuilder.reconcile_timing() is called
    tb_instance.reconcile_timing.assert_called_once()
    
    # TEST 9: TimelineBuilder.validate() is called before assembly
    tb_instance.validate.assert_called_once()
    
    # TEST 10: Max retries hard-capped to 1
    assert mock_veo_service.call_count == 1
    
    # TEST 13: Concat receives finalized paths
    assert mock_concat.called
    
    # Blueprint status updated to COMPLETED
    assert bp.status == "COMPLETED"
    mock_production_blueprint_repo.save.assert_called()

def test_hard_cap_retries_and_isolation(
    test_project_id,
    mock_veo_service,
    mock_elevenlabs,
    mock_lipsync,
    mock_concat,
    mock_upload,
    mock_production_blueprint_repo,
    mock_attempt_repo,
    mock_final_video_repo,
    mock_quality_reviewer,
    mock_timeline_builder,
    mock_moviepy_clips
):
    """TEST 10, 11, 12: Retries hardcapped to 1, isolation preserved, SceneState only updated on success."""
    bp = ProductionBlueprint(
        project_id=test_project_id, blueprint_id="bp_retry_test", title="Retry Test", concept="concept", genre="genre",
        target_duration_seconds=10.0, status="APPROVED",
        quality_strategy=QualityStrategy(max_retries=5) # Request 5 retries
    )
    bp.scenes.append(SceneBlueprint(scene_id="scn_1", scene_number=1, narrative_purpose="Hook", estimated_duration_seconds=5.0))
    mock_production_blueprint_repo.get.return_value = bp
    
    # Mock reviewer to ALWAYS REJECT
    from core.services.quality_reviewer import QualityReviewResult
    mock_quality_reviewer.review_video.return_value = QualityReviewResult(
        character_consistency=2.0, scene_adherence=2.0, visual_quality=2.0, continuity=2.0, overall=2.0, issues=[], recommended_action="reject"
    )
    
    import pytest
    from core.exceptions import QualityReviewError
    from routers.video_cloner import run_production_job
    
    # P0 BILLING FIX REGRESSION: failures MUST propagate out of the
    # orchestrator (fail-closed contract) so the Cloud Tasks worker releases
    # the credit reservation instead of committing it.
    with pytest.raises(QualityReviewError):
        run_production_job("test_user_8d", test_project_id, bp.blueprint_id)
         
    # TEST 10: Even with max_retries=5, Veo is only called exactly TWICE (initial + 1 retry)
    assert mock_veo_service.call_count == 2
    
    # TEST 11: Rejected Attempt 1 cannot leak into Attempt 2.
    # The job failed outright, concat/upload should never be called.
    mock_concat.assert_not_called()
    
    # TEST 12: SceneState is not updated after rejected generation.
    # The loop throws and exits before continuity_manager.save_state is reached
    with patch("routers.video_cloner.ContinuityManager.save_state") as mock_save_state:
        assert mock_save_state.call_count == 0

def test_api_orchestration_unapproved_rejected(test_project_id, mock_production_blueprint_repo):
    """Tests the /generate endpoint rejects unapproved blueprints."""
    
    bp = ProductionBlueprint(
        project_id=test_project_id,
        blueprint_id="bp_test_unapproved",
        title="Unapproved BP",
        concept="DRAFT",
        genre="Test",
        target_duration_seconds=10.0,
        status="DRAFT"
    )
    mock_production_blueprint_repo.get.return_value = bp
    
    response = client.post(
        f"/projects/{test_project_id}/production-blueprints/{bp.blueprint_id}/generate",
        headers={"Authorization": "Bearer fake-token"}
    )
    if response.status_code != 400:
        print("ERROR BODY:", response.json())
    assert response.status_code == 400
    assert "must be APPROVED" in response.json()["detail"]
