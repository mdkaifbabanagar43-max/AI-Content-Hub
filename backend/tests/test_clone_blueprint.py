import pytest
from core.models.source_analysis import (
    SourceAnalysis, SourceMediaMetadata, SourceSceneSegment, SceneSemanticAnalysis,
    HookAnalysis, CTAAnalysis, SourceAudioProfile, SourceVisualStyle
)
from core.repositories.clone_blueprint_repo import CloneBlueprintRepository
from core.services.clone_blueprint_builder import CloneBlueprintBuilder

# Mock setup
@pytest.fixture
def mock_source_analysis():
    return SourceAnalysis(
        source_video_id="video_123",
        media_metadata=SourceMediaMetadata(
            duration_seconds=10.0, width=640, height=360, fps=30.0, aspect_ratio="16:9", has_audio=False
        ),
        transcript_text="Test",
        scenes=[
            SourceSceneSegment(scene_number=1, start_seconds=0.0, end_seconds=5.0, duration_seconds=5.0, detection_method="VISUAL"),
            SourceSceneSegment(scene_number=2, start_seconds=5.0, end_seconds=10.0, duration_seconds=5.0, detection_method="VISUAL")
        ],
        semantic_scenes=[
            SceneSemanticAnalysis(
                scene_number=1, narrative_purpose="Setup", visual_action="Action 1", emotion="neutral",
                pacing_intensity="MEDIUM", shot_type="WIDE", camera_motion="STATIC", character_roles=["PROTAGONIST"]
            ),
            SceneSemanticAnalysis(
                scene_number=2, narrative_purpose="Resolution", visual_action="Action 2", emotion="neutral",
                pacing_intensity="MEDIUM", shot_type="CLOSE_UP", camera_motion="STATIC", character_roles=["PROTAGONIST"]
            )
        ],
        hook=HookAnalysis(hook_type="VISUAL_SHOCK", hook_start_seconds=0.0, hook_end_seconds=3.0, confidence=0.9),
        cta=CTAAnalysis(exists=True, start_seconds=8.0, end_seconds=10.0, type="SUBSCRIBE", description="Subscribe CTA"),
        visual_style=SourceVisualStyle(art_style="Test", character_design="Test"),
        audio_profile=SourceAudioProfile()
    )

def test_model_valid_blueprint_parses(mock_source_analysis):
    builder = CloneBlueprintBuilder()
    blueprint = builder.build_from_source(mock_source_analysis, "proj_1", "user_1")
    assert blueprint.source_video_id == "video_123"
    assert blueprint.target_duration_seconds == 10.0

def test_timing_durations_correct(mock_source_analysis):
    builder = CloneBlueprintBuilder()
    blueprint = builder.build_from_source(mock_source_analysis, "proj_1", "user_1")
    for scene in blueprint.scenes:
        assert scene.source_duration_seconds == 5.0
        assert len(scene.shot_sequence) == 1
        assert scene.shot_sequence[0].duration_seconds == 5.0
        # Shot contained inside scene
        assert scene.shot_sequence[0].source_start_seconds >= scene.source_start_seconds
        assert scene.shot_sequence[0].source_end_seconds <= scene.source_end_seconds

def test_structure_beats_valid(mock_source_analysis):
    builder = CloneBlueprintBuilder()
    blueprint = builder.build_from_source(mock_source_analysis, "proj_1", "user_1")
    assert len(blueprint.narrative_structure) == 2
    assert blueprint.narrative_structure[0].type == "HOOK"
    assert blueprint.narrative_structure[1].type == "CTA"

def test_versioning_and_immutability(mock_source_analysis):
    repo = CloneBlueprintRepository()
    builder = CloneBlueprintBuilder()
    blueprint = builder.build_from_source(mock_source_analysis, "proj_1", "user_1")
    
    # Save V1
    success = repo.save("user_1", "proj_1", f"{blueprint.clone_blueprint_id}_v1", blueprint)
    assert success is True
    
    # V1 saved
    fetched = repo.get_version("user_1", "proj_1", blueprint.clone_blueprint_id, 1)
    assert fetched is not None
    
    # Immutability: existing version cannot be silently overwritten
    with pytest.raises(ValueError, match="already exists"):
        repo.save("user_1", "proj_1", f"{blueprint.clone_blueprint_id}_v1", blueprint)
        
    # Save V2
    blueprint.clone_blueprint_version = 2
    success = repo.save("user_1", "proj_1", f"{blueprint.clone_blueprint_id}_v2", blueprint)
    assert success is True
    
    # Latest returns V2
    latest = repo.get_latest("user_1", "proj_1", blueprint.clone_blueprint_id)
    assert latest.clone_blueprint_version == 2
    
def test_security_validation(mock_source_analysis):
    repo = CloneBlueprintRepository()
    builder = CloneBlueprintBuilder()
    blueprint = builder.build_from_source(mock_source_analysis, "proj_1", "user_1")
    
    # Cross-user access rejected during save
    with pytest.raises(PermissionError):
        repo.save("user_wrong", "proj_1", f"{blueprint.clone_blueprint_id}_v1", blueprint)
        
    # Cross-project access rejected
    with pytest.raises(PermissionError):
        repo.save("user_1", "proj_wrong", f"{blueprint.clone_blueprint_id}_v1", blueprint)

def test_builder_preserves_semantics_no_ids(mock_source_analysis):
    builder = CloneBlueprintBuilder()
    blueprint = builder.build_from_source(mock_source_analysis, "proj_1", "user_1")
    
    for scene in blueprint.scenes:
        # Check no project bible IDs
        for role in scene.character_roles:
            assert "CHAR_" not in role
            
        assert "LOC_" not in (scene.location_summary or "")
        assert "PROP_" not in (scene.prop_summary or "")
