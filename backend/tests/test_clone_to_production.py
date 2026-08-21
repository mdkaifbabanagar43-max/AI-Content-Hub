import pytest
from unittest.mock import patch, MagicMock

from core.models.clone_blueprint import (
    CloneBlueprint, CloneSceneBlueprint, CloneShot, NarrativeBeat, PacingProfile
)
from core.models.source_analysis import HookAnalysis, CTAAnalysis, SourceAudioProfile, SourceVisualStyle
from core.models.blueprint import ProductionBlueprint, SceneBlueprint, DialogueLine
from core.models.transformation import ProductionTransformationRequest
from core.services.production_director import ProductionDirector, MissingAssetException
import json

@pytest.fixture
def mock_clone_blueprint():
    return CloneBlueprint(
        clone_blueprint_id="cl_001",
        source_video_id="video_001",
        project_id="proj_1",
        user_id="user_1",
        clone_blueprint_version=1,
        source_analysis_version="1.0.0",
        title="Test Clone",
        source_duration_seconds=30.0,
        target_duration_seconds=30.0,
        aspect_ratio="16:9",
        hook=HookAnalysis(hook_type="VISUAL_SHOCK", confidence=1.0),
        narrative_structure=[NarrativeBeat(type="HOOK", start_seconds=0, end_seconds=3, description="Hook", importance="HIGH")],
        pacing_profile=PacingProfile(overall_intensity="HIGH", average_shot_duration=2.0, fastest_shot_duration=1.0, slowest_shot_duration=3.0, scene_count=1, shot_count=1, rhythm_description="Fast"),
        visual_style_profile=SourceVisualStyle(art_style="Cinematic", character_design="Realistic"),
        audio_profile=SourceAudioProfile(),
        cta_structure=CTAAnalysis(exists=False),
        scenes=[
            CloneSceneBlueprint(
                scene_id="scn_1", scene_number=1, source_start_seconds=0.0, source_end_seconds=5.0, source_duration_seconds=5.0,
                narrative_purpose="Setup", visual_action="Hero walks in", emotion="curious", pacing="MEDIUM",
                shot_sequence=[CloneShot(shot_number=1, source_start_seconds=0, source_end_seconds=5, duration_seconds=5, shot_type="WIDE", camera_motion="STATIC", visual_action="Walks in")],
                character_roles=["PROTAGONIST"], location_summary="Coffee shop", prop_summary="phone"
            )
        ]
    )

@pytest.fixture
def mock_bibles():
    # Mocking ProjectBibleLoader to return some assets
    class MockBible:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
            
    return {
        "characters": [MockBible(character_id="CHAR_001", name="Alex")],
        "locations": [MockBible(location_id="LOC_001", name="Coffee Shop")],
        "props": [MockBible(prop_id="PROP_001", name="Phone")],
        "voices": [MockBible(voice_id="VOICE_001", character_id="CHAR_001")],
        "styles": [MockBible(style_id="STYLE_001", name="Cinematic Dark")]
    }

@patch("core.services.production_director.get_gemini_client")
@patch("core.services.bible_loader.ProjectBibleLoader.load_all_bibles")
@patch("core.repositories.blueprint_repo.BlueprintRepository.save")
def test_successful_transformation(mock_save, mock_load_bibles, mock_get_client, mock_clone_blueprint, mock_bibles):
    mock_load_bibles.return_value = mock_bibles
    
    # Mock Gemini returning a valid ProductionBlueprint mapped perfectly
    mock_client = MagicMock()
    mock_response = MagicMock()
    
    mock_response.text = json.dumps({
        "project_id": "proj_1",
        "title": "Crypto Wallet Story",
        "concept": "Alex loses his wallet",
        "genre": "Drama",
        "target_duration_seconds": 30.0,
        "visual_style_id": "STYLE_001",
        "required_character_ids": ["CHAR_001"],
        "required_location_ids": ["LOC_001"],
        "required_prop_ids": ["PROP_001"],
        "scenes": [
            {
                "scene_id": "pscn_1",
                "scene_number": 1,
                "narrative_purpose": "Setup",
                "estimated_duration_seconds": 5.0,
                "character_ids": ["CHAR_001"],
                "location_id": "LOC_001",
                "prop_ids": ["PROP_001"],
                "dialogue": [
                    {
                        "character_id": "CHAR_001",
                        "voice_id": "VOICE_001",
                        "text": "Where is my crypto wallet?",
                        "emotion": "panic",
                        "delivery_style": "frantic",
                        "estimated_duration_seconds": 3.0
                    }
                ],
                "camera": {
                    "shot_type": "WIDE",
                    "camera_motion": "STATIC"
                },
                "transition": "CUT"
            }
        ]
    })
    
    mock_client.models.generate_content.return_value = mock_response
    mock_get_client.return_value = mock_client
    
    director = ProductionDirector("user_1", "proj_1")
    req = ProductionTransformationRequest(
        topic="Make it about losing a crypto wallet",
        requested_character_ids=["CHAR_001"],
        requested_style_id="STYLE_001"
    )
    
    result = director.transform_clone_blueprint(mock_clone_blueprint, req)
    
    # Assert successful transform
    assert result.source_clone_blueprint_id == "cl_001"
    assert result.source_clone_blueprint_version == 1
    assert result.visual_style_id == "STYLE_001"
    assert result.scenes[0].character_ids == ["CHAR_001"]
    assert result.scenes[0].camera.shot_type == "WIDE" # Camera preserved
    assert result.status == "DRAFT"
    
    mock_save.assert_called_once()

@patch("core.services.production_director.get_gemini_client")
@patch("core.services.bible_loader.ProjectBibleLoader.load_all_bibles")
def test_missing_asset_exception(mock_load_bibles, mock_get_client, mock_clone_blueprint, mock_bibles):
    mock_load_bibles.return_value = mock_bibles
    
    mock_client = MagicMock()
    mock_response = MagicMock()
    
    # Mock Gemini outputting the special MISSING_ASSET string because it wants a crypto wallet prop
    mock_response.text = json.dumps({
        "project_id": "proj_1",
        "title": "Crypto Wallet Story",
        "concept": "Alex loses his wallet",
        "genre": "Drama",
        "target_duration_seconds": 30.0,
        "required_prop_ids": ["MISSING_ASSET:PROP:crypto wallet:scn_1"],
        "scenes": []
    })
    
    mock_client.models.generate_content.return_value = mock_response
    mock_get_client.return_value = mock_client
    
    director = ProductionDirector("user_1", "proj_1")
    req = ProductionTransformationRequest(topic="Make it about losing a crypto wallet")
    
    with pytest.raises(MissingAssetException) as excinfo:
        director.transform_clone_blueprint(mock_clone_blueprint, req)
        
    assert excinfo.value.payload["asset_type"] == "PROP"
    assert excinfo.value.payload["description"] == "crypto wallet"
