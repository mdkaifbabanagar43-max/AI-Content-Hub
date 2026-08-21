import pytest
from unittest.mock import patch, MagicMock
from core.models.state import SceneState, CharacterState
from core.models.context import GenerationContext
from core.models.scene import Scene
from core.models.character import Character
from core.services.bible_loader import ResolvedScene
from core.services.prompt_compiler import PromptCompiler
from core.services.continuity_manager import ContinuityManager

@pytest.fixture
def mock_gen_context():
    return GenerationContext(user_id="USER1", project_id="PROJ1", job_id="JOB1")

def test_continuity_manager_saves_and_loads(mock_gen_context):
    with patch("core.services.continuity_manager.SceneStateRepository") as MockRepo:
        mock_repo_inst = MockRepo.return_value
        
        mgr = ContinuityManager()
        state = SceneState(scene_id="SCENE1", project_id="PROJ1")
        
        mgr.save_state(mock_gen_context, state)
        assert mock_repo_inst.save.called
        
        mock_repo_inst.get.return_value = state
        loaded = mgr.get_previous_state(mock_gen_context, "SCENE1")
        assert loaded.scene_id == "SCENE1"

def test_prompt_compiler_with_continuity():
    compiler = PromptCompiler()
    
    mock_context = GenerationContext(user_id="U1", project_id="P1", job_id="J1")
    scene = Scene(scene_id="S1", project_id="P1", scene_number=2, duration=5.0)
    char = Character(character_id="C1", project_id="P1", name="Alex")
    
    resolved = ResolvedScene(scene=scene, characters=[char], voices=[], style=None, location=None, props=[])
    
    prev_state = SceneState(
        scene_id="S0", 
        project_id="P1",
        character_states=[
            CharacterState(
                character_id="C1",
                clothing_state="blue jacket",
                held_objects=["phone"]
            )
        ]
    )
    
    prompt = compiler.compile(mock_context, resolved, previous_state=prev_state)
    assert "CONTINUITY FROM PREVIOUS SCENE:" in prompt
    assert "Alex is wearing blue jacket." in prompt
    assert "Alex was holding: phone." in prompt
    
def test_quality_reviewer_mock():
    with patch("core.services.quality_reviewer.get_gemini_client") as MockClient:
        mock_client_inst = MockClient.return_value
        mock_response = MagicMock()
        mock_response.text = '{"character_consistency": 9.0, "scene_adherence": 8.5, "visual_quality": 8.0, "continuity": 8.0, "overall": 8.375, "issues": [], "recommended_action": "accept"}'
        mock_client_inst.models.generate_content.return_value = mock_response
        
        from core.services.quality_reviewer import QualityReviewer
        with patch.object(QualityReviewer, '_extract_frames', return_value=[]):
            reviewer = QualityReviewer()
            res = reviewer.review_video("dummy.mp4", "prompt")
            
            assert res.overall == 8.375
            assert res.character_consistency == 9.0
