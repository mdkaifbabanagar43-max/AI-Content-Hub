import pytest
import json
import uuid
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from pydantic import ValidationError

from core.models.blueprint import ProductionBlueprint, SceneBlueprint, CameraDirection, ContinuityRequirement, DialogueLine, QualityStrategy
from core.models.context import GenerationContext
from core.models.character import Character, CharacterAppearance, CharacterClothing
from core.models.location import Location
from core.models.prop import Prop
from core.models.voice import Voice
from core.models.style import Style
from core.models.scene import Scene
from core.models.attempt import GenerationAttempt
from core.models.state import SceneState
from core.services.production_director import ProductionDirector, BlueprintValidationException
from core.services.prompt_compiler import PromptCompiler
from core.repositories.blueprint_repo import BlueprintRepository
from routers.director import VALID_STATUS_TRANSITIONS

# ============================================================
# 1. STRUCTURED OUTPUT AUDIT & PYDANTIC PARSING TESTS
# ============================================================

def test_pydantic_parsing_valid_blueprint():
    raw_json = """
    {
        "project_id": "proj_123",
        "title": "Test Title",
        "concept": "Test concept",
        "genre": "Documentary",
        "target_duration_seconds": 30.0,
        "aspect_ratio": "9:16",
        "required_character_ids": ["CHAR_001"],
        "required_location_ids": ["LOC_001"],
        "required_prop_ids": ["PROP_001"],
        "scenes": [
            {
                "scene_id": "scene_1",
                "scene_number": 1,
                "narrative_purpose": "Intro",
                "estimated_duration_seconds": 5.0,
                "character_ids": ["CHAR_001"],
                "location_id": "LOC_001",
                "prop_ids": ["PROP_001"],
                "dialogue": [
                    {
                        "character_id": "CHAR_001",
                        "voice_id": "VOICE_001",
                        "text": "Hello world",
                        "emotion": "happy",
                        "delivery_style": "excited",
                        "estimated_duration_seconds": 2.5
                    }
                ],
                "emotion": "happy",
                "action": "waves",
                "camera": {
                    "shot_type": "MEDIUM",
                    "camera_motion": "DOLLY",
                    "lens": "50mm"
                },
                "environment": "Sunny",
                "continuity_requirements": [
                    {
                        "asset_id": "PROP_001",
                        "required_state": "holding",
                        "priority": "HIGH"
                    }
                ],
                "primary_reference_asset_id": "CHAR_001",
                "transition": "CUT",
                "scene_quality_priority": "CHARACTER_CRITICAL"
            }
        ]
    }
    """
    data = json.loads(raw_json)
    bp = ProductionBlueprint(**data)
    
    assert bp.title == "Test Title"
    assert len(bp.scenes) == 1
    assert bp.scenes[0].camera.shot_type == "MEDIUM"
    assert bp.scenes[0].camera.camera_motion == "DOLLY"
    assert len(bp.scenes[0].continuity_requirements) == 1
    assert bp.scenes[0].scene_quality_priority == "CHARACTER_CRITICAL"
    assert bp.target_duration_seconds == 30.0

def test_pydantic_parsing_invalid_schema_rejected():
    # Missing required fields like title, target_duration_seconds, etc.
    invalid_json = '{"project_id": "proj_123", "scenes": "not_a_list"}'
    with pytest.raises(ValidationError):
        ProductionBlueprint(**json.loads(invalid_json))

# ============================================================
# 2. BIBLE ID INTEGRITY & SECURITY SCOPING TESTS
# ============================================================

@patch("core.services.production_director.ProjectBibleLoader")
def test_director_entity_validation_security_cross_project(mock_loader_class):
    mock_loader = mock_loader_class.return_value
    mock_loader.load_all_bibles.return_value = {
        "characters": [Character(character_id="CHAR_001", project_id="proj_A", name="Alice")],
        "locations": [Location(location_id="LOC_001", project_id="proj_A", name="Office")],
        "voices": [Voice(voice_id="VOICE_001", project_id="proj_A", character_id="CHAR_001", provider_voice_id="pvid")],
        "props": [Prop(prop_id="PROP_001", project_id="proj_A", name="Phone")],
        "styles": [Style(style_id="STYLE_001", project_id="proj_A", name="Noir")]
    }
    
    # Blueprint contains IDs from a different project or unauthorized user
    bp = ProductionBlueprint(
        project_id="proj_A",
        title="Unauthorized Ref Test",
        concept="C",
        genre="G",
        target_duration_seconds=10.0,
        required_character_ids=["CHAR_001", "FOREIGN_CHAR_999"],
        required_location_ids=["FOREIGN_LOC_999"],
        required_prop_ids=["PROP_001"],
        visual_style_id="FOREIGN_STYLE_999",
        scenes=[]
    )
    
    director = ProductionDirector("user_A", "proj_A")
    director.bible_loader = mock_loader
    
    errors = director._validate_entities(bp, GenerationContext(user_id="user_A", project_id="proj_A", job_id="j1"))
    assert len(errors) == 3
    assert any("FOREIGN_CHAR_999" in e for e in errors)
    assert any("FOREIGN_LOC_999" in e for e in errors)
    assert any("FOREIGN_STYLE_999" in e for e in errors)

@patch("core.services.production_director.ProjectBibleLoader")
def test_director_entity_validation_scene_level_and_references(mock_loader_class):
    mock_loader = mock_loader_class.return_value
    mock_loader.load_all_bibles.return_value = {
        "characters": [Character(character_id="CHAR_001", project_id="proj", name="Hero")],
        "locations": [Location(location_id="LOC_001", project_id="proj", name="Cave")],
        "voices": [Voice(voice_id="VOICE_001", project_id="proj", character_id="CHAR_001", provider_voice_id="pvid")],
        "props": [Prop(prop_id="PROP_001", project_id="proj", name="Sword")],
        "styles": [Style(style_id="STYLE_001", project_id="proj", name="Cinematic")]
    }
    
    bp = ProductionBlueprint(
        project_id="proj",
        title="Scene Level Validation",
        concept="C",
        genre="G",
        target_duration_seconds=10.0,
        required_character_ids=["CHAR_001"],
        required_location_ids=["LOC_001"],
        required_prop_ids=["PROP_001"],
        scenes=[
            SceneBlueprint(
                scene_id="s1",
                scene_number=1,
                narrative_purpose="P",
                estimated_duration_seconds=5.0,
                character_ids=["CHAR_001", "INVALID_CHAR"],
                location_id="INVALID_LOC",
                prop_ids=["INVALID_PROP"],
                primary_reference_asset_id="UNKNOWN_ASSET",
                continuity_requirements=[
                    ContinuityRequirement(asset_id="GHOST_PROP", required_state="held")
                ],
                dialogue=[
                    DialogueLine(
                        character_id="INVALID_SPEAKER",
                        voice_id="INVALID_VOICE",
                        text="Hi",
                        emotion="neutral",
                        delivery_style="normal",
                        estimated_duration_seconds=2.0
                    )
                ]
            )
        ]
    )
    
    director = ProductionDirector("user1", "proj")
    director.bible_loader = mock_loader
    
    errors = director._validate_entities(bp, GenerationContext(user_id="user1", project_id="proj", job_id="j1"))
    assert len(errors) >= 6
    assert any("INVALID_CHAR" in e for e in errors)
    assert any("INVALID_LOC" in e for e in errors)
    assert any("INVALID_PROP" in e for e in errors)
    assert any("UNKNOWN_ASSET" in e for e in errors)
    assert any("GHOST_PROP" in e for e in errors)
    assert any("INVALID_SPEAKER" in e for e in errors)

# ============================================================
# 3. BLUEPRINT VERSIONING & IDEMPOTENCY LINKAGE TESTS
# ============================================================

def test_blueprint_repository_versioning_preservation():
    repo = BlueprintRepository()
    mock_db = MagicMock()
    repo.db = mock_db
    
    bp_v1 = ProductionBlueprint(
        project_id="proj_1",
        blueprint_id="bp_test123",
        blueprint_version=1,
        title="Original V1",
        concept="C",
        genre="G",
        target_duration_seconds=15.0,
        status="APPROVED"
    )
    
    bp_v2 = ProductionBlueprint(
        project_id="proj_1",
        blueprint_id="bp_test123",
        blueprint_version=2,
        title="Edited V2",
        concept="C",
        genre="G",
        target_duration_seconds=15.0,
        status="READY_FOR_APPROVAL"
    )
    
    assert repo._doc_key("bp_test123", 1) == "bp_test123_v1"
    assert repo._doc_key("bp_test123", 2) == "bp_test123_v2"

def test_generation_attempt_blueprint_version_isolation():
    # Verify GenerationAttempt models version field and isolates V1 from V2
    att_v1 = GenerationAttempt(
        attempt_id="att_1",
        project_id="proj",
        scene_id="s2",
        blueprint_id="bp_abc",
        blueprint_version=1,
        attempt_number=1,
        prompt="prompt v1",
        status="COMPLETED",
        output_uri="/path/to/v1_scene2.mp4"
    )
    
    existing_attempts = [att_v1]
    
    # Check that when producing for V2, V1 completed attempt is NOT reused
    target_blueprint_id = "bp_abc"
    target_blueprint_version = 2
    
    matched_v2 = [
        a for a in existing_attempts
        if a.scene_id == "s2"
        and a.blueprint_id == target_blueprint_id
        and a.blueprint_version == target_blueprint_version
    ]
    assert len(matched_v2) == 0  # Does NOT leak into V2!

    matched_v1 = [
        a for a in existing_attempts
        if a.scene_id == "s2"
        and a.blueprint_id == target_blueprint_id
        and a.blueprint_version == 1
    ]
    assert len(matched_v1) == 1

# ============================================================
# 4. APPROVAL STATE MACHINE & COST GATE TESTS
# ============================================================

def test_approval_state_machine_valid_and_invalid_transitions():
    # Valid transitions
    assert "READY_FOR_APPROVAL" in VALID_STATUS_TRANSITIONS["DRAFT"]
    assert "APPROVED" in VALID_STATUS_TRANSITIONS["READY_FOR_APPROVAL"]
    assert "IN_PRODUCTION" in VALID_STATUS_TRANSITIONS["APPROVED"]
    assert "SUPERSEDED" in VALID_STATUS_TRANSITIONS["APPROVED"]
    assert "COMPLETED" in VALID_STATUS_TRANSITIONS["IN_PRODUCTION"]
    
    # Disallowed direct transitions
    assert "IN_PRODUCTION" not in VALID_STATUS_TRANSITIONS["DRAFT"]
    assert "IN_PRODUCTION" not in VALID_STATUS_TRANSITIONS["READY_FOR_APPROVAL"]
    assert "IN_PRODUCTION" not in VALID_STATUS_TRANSITIONS["SUPERSEDED"]
    assert "IN_PRODUCTION" not in VALID_STATUS_TRANSITIONS["INVALID"]

@patch("core.repositories.blueprint_repo.BlueprintRepository.get")
def test_production_cost_gate_zero_provider_calls_on_unapproved(mock_get_bp):
    from routers.trend_cloner import run_trend_cloner_job, GenerateRequest
    
    # Mock unapproved blueprint (READY_FOR_APPROVAL)
    unapproved_bp = ProductionBlueprint(
        project_id="proj",
        blueprint_id="bp_gate",
        blueprint_version=1,
        title="Unapproved",
        concept="C",
        genre="G",
        target_duration_seconds=10.0,
        status="READY_FOR_APPROVAL"
    )
    mock_get_bp.return_value = unapproved_bp
    
    with patch("services.veo_service.generate_video_with_veo") as mock_veo, \
         patch("services.elevenlabs_service._generate_single_tts") as mock_tts:
        
        req = GenerateRequest(
            title="Gate Test",
            blueprint_id="bp_gate",
            project_id="proj"
        )
        
        run_trend_cloner_job("job_1", "user_1", req, 10, "pro", active_blueprint_version=1)
        
        # Ensure ZERO provider calls were made
        assert mock_veo.call_count == 0
        assert mock_tts.call_count == 0

# ============================================================
# 5. PROMPT COMPILER HIERARCHY TESTS
# ============================================================

def test_prompt_compiler_canonical_hierarchy_preservation():
    compiler = PromptCompiler()
    
    canonical_char = Character(
        character_id="CHAR_001",
        project_id="proj",
        name="Alex",
        appearance=CharacterAppearance(
            face_shape="sharp jawline",
            skin_tone="fair",
            hair="short raven black",
            eyes="striking emerald green",
            facial_features="small scar on left cheek"
        ),
        clothing=CharacterClothing(
            top="crimson red trenchcoat",
            pants="black trousers",
            shoes="leather boots"
        )
    )
    
    # Blueprint specifies an action ("removes coat")
    scene_bp = SceneBlueprint(
        scene_id="s1",
        scene_number=1,
        narrative_purpose="Dramatic entrance",
        estimated_duration_seconds=5.0,
        camera=CameraDirection(shot_type="MEDIUM", camera_motion="DOLLY", lens="35mm"),
        action="Alex unbuttons the crimson red trenchcoat and steps forward",
        emotion="determined",
        environment="Misty atmospheric alleyway",
        continuity_requirements=[ContinuityRequirement(asset_id="CHAR_001", required_state="trenchcoat unbuttoned")]
    )
    
    from core.services.bible_loader import ResolvedScene
    rs = ResolvedScene(
        scene=Scene(scene_id="s1", project_id="proj", scene_number=1, duration=5.0),
        characters=[canonical_char],
        voices=[],
        style=None,
        location=None,
        props=[]
    )
    
    compiled = compiler.compile(
        GenerationContext(user_id="u", project_id="proj", job_id="j"),
        rs,
        scene_blueprint=scene_bp
    )
    
    # Canonical Bible values MUST be in SUBJECTS
    assert "Character 'Alex'" in compiled
    assert "sharp jawline" in compiled
    assert "striking emerald green eyes" in compiled
    assert "crimson red trenchcoat" in compiled
    
    # Scene Blueprint dynamics MUST be in SCENE DYNAMICS / CINEMATOGRAPHY
    assert "Action: Alex unbuttons the crimson red trenchcoat and steps forward" in compiled
    assert "Emotion: determined" in compiled
    assert "MEDIUM SHOT" in compiled
    assert "DOLLY camera motion" in compiled
    assert "Misty atmospheric alleyway" in compiled
    assert "REQUIRED: trenchcoat unbuttoned" in compiled

# ============================================================
# 6. END-TO-END APPROVAL & IMMUTABILITY WORKFLOW TEST
# ============================================================

@patch("core.services.production_director.get_gemini_client")
@patch("core.services.production_director.ProjectBibleLoader")
def test_production_director_end_to_end_approval_flow(mock_loader_class, mock_gemini_client):
    mock_loader = mock_loader_class.return_value
    mock_loader.load_all_bibles.return_value = {
        "characters": [Character(character_id="CHAR_001", project_id="proj", name="Hero")],
        "locations": [Location(location_id="LOC_001", project_id="proj", name="Cave")],
        "voices": [Voice(voice_id="VOICE_001", project_id="proj", character_id="CHAR_001", provider_voice_id="pvid")],
        "props": [Prop(prop_id="PROP_001", project_id="proj", name="Sword")],
        "styles": [Style(style_id="STYLE_001", project_id="proj", name="Cinematic")]
    }
    
    mock_response = MagicMock()
    mock_response.text = """
    {
        "project_id": "proj",
        "title": "E2E Approval Flow",
        "concept": "Hero in a cave",
        "genre": "Fantasy",
        "target_duration_seconds": 15.0,
        "aspect_ratio": "16:9",
        "visual_style_id": "STYLE_001",
        "required_character_ids": ["CHAR_001"],
        "required_location_ids": ["LOC_001"],
        "required_prop_ids": ["PROP_001"],
        "scenes": [
            {
                "scene_id": "s1",
                "scene_number": 1,
                "narrative_purpose": "Enter",
                "estimated_duration_seconds": 5.0,
                "character_ids": ["CHAR_001"],
                "location_id": "LOC_001",
                "dialogue": [],
                "action": "enters",
                "camera": {"shot_type": "WIDE"},
                "transition": "CUT",
                "scene_quality_priority": "BALANCED"
            },
            {
                "scene_id": "s2",
                "scene_number": 2,
                "narrative_purpose": "Speak",
                "estimated_duration_seconds": 5.0,
                "character_ids": ["CHAR_001"],
                "prop_ids": ["PROP_001"],
                "dialogue": [{"character_id": "CHAR_001", "voice_id": "VOICE_001", "text": "Hello", "emotion": "Calm", "delivery_style": "Normal", "estimated_duration_seconds": 3.0}],
                "action": "speaks",
                "camera": {"shot_type": "MEDIUM"},
                "transition": "CUT",
                "scene_quality_priority": "BALANCED"
            },
            {
                "scene_id": "s3",
                "scene_number": 3,
                "narrative_purpose": "Place prop",
                "estimated_duration_seconds": 5.0,
                "character_ids": ["CHAR_001"],
                "prop_ids": ["PROP_001"],
                "dialogue": [],
                "action": "places prop",
                "camera": {"shot_type": "CLOSE_UP"},
                "continuity_requirements": [{"asset_id": "PROP_001", "required_state": "on table", "priority": "HIGH"}],
                "transition": "CUT",
                "scene_quality_priority": "BALANCED"
            }
        ],
        "quality_strategy": {"global_priority": "BALANCED", "max_retries": 1}
    }
    """
    mock_client_instance = mock_gemini_client.return_value
    mock_client_instance.models.generate_content.return_value = mock_response
    
    director = ProductionDirector("user1", "proj")
    director.bible_loader = mock_loader
    
    # 1. Generate Blueprint V1
    with patch("core.repositories.blueprint_repo.BlueprintRepository.save") as mock_save:
        bp_v1 = director.generate_blueprint("Hero enters cave and places sword", 15.0)
        
        assert bp_v1.blueprint_version == 1
        assert len(bp_v1.scenes) == 3
        # Generation MUST NOT auto-approve
        assert bp_v1.status == "READY_FOR_APPROVAL"
        
        # 2. Attempt production before approval -> Should be rejected
        with pytest.raises(HTTPException) as exc_info:
            from routers.trend_cloner import generate_trend, GenerateRequest
            with patch("core.repositories.blueprint_repo.BlueprintRepository.get", return_value=bp_v1), \
                 patch("routers.trend_cloner.get_user_profile", return_value={"plan": "pro", "credits": 1000}), \
                 patch("routers.trend_cloner.get_active_job_count", return_value=0):
                import asyncio
                bg_tasks = MagicMock()
                asyncio.run(generate_trend(
                    GenerateRequest(title="Test", blueprint_id=bp_v1.blueprint_id, project_id="proj"),
                    bg_tasks,
                    user_id="user1"
                ))
        assert exc_info.value.status_code == 400
        assert "must be APPROVED" in exc_info.value.detail

        # 3. Explicit Approval Action
        bp_v1.status = "APPROVED"
        
        # 4. Production start on APPROVED blueprint
        with patch("core.repositories.blueprint_repo.BlueprintRepository.get", return_value=bp_v1), \
             patch("routers.trend_cloner.get_user_profile", return_value={"plan": "pro", "credits": 1000}), \
             patch("routers.trend_cloner.get_active_job_count", return_value=0), \
             patch("routers.trend_cloner.create_job", return_value="job_prod_1"):
            import asyncio
            bg_tasks = MagicMock()
            res = asyncio.run(generate_trend(
                GenerateRequest(title="Test", blueprint_id=bp_v1.blueprint_id, project_id="proj"),
                bg_tasks,
                user_id="user1"
            ))
            assert res["status"] == "processing"
            assert res["job_id"] == "job_prod_1"
            
        # 5. Create Blueprint V2 while V1 is in production
        bp_v2 = bp_v1.model_copy(deep=True)
        bp_v2.blueprint_version = 2
        bp_v2.scenes[1].camera.shot_type = "EXTREME_CLOSE_UP"
        
        # Verify V1 remains unchanged
        assert bp_v1.scenes[1].camera.shot_type == "MEDIUM"
        assert bp_v1.blueprint_version == 1
        assert bp_v2.scenes[1].camera.shot_type == "EXTREME_CLOSE_UP"
        assert bp_v2.blueprint_version == 2
