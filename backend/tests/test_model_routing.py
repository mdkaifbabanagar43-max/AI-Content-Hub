import ast
import os
import pytest
from unittest.mock import patch, MagicMock, mock_open

from config import ModelRoutingConfig, BASE_DIR
from services.ai_service import route_and_generate_text
from core.services.production_director import determine_story_complexity
import services.source_analyzer as source_analyzer_mod
import services.trend_analyzer as trend_analyzer_mod
import services.lip_sync_service as lip_sync_mod

# ============================================================================
# 1. TEXT ROUTING & CONFIG TESTS
# ============================================================================

@patch("services.ai_service._invoke_bedrock_claude")
@patch("services.ai_service.get_gemini_model")
def test_route_and_generate_text_default_narrative(mock_gemini, mock_claude):
    mock_gemini_instance = MagicMock()
    mock_gemini_instance.generate_content.return_value = MagicMock(text="narrative output")
    mock_gemini.return_value = mock_gemini_instance

    result = route_and_generate_text("test prompt", task="NORMAL_STORY")
    mock_gemini.assert_called_with(ModelRoutingConfig.NORMAL_STORY)
    mock_claude.assert_not_called()
    assert result == "narrative output"

@patch("services.ai_service._invoke_bedrock_claude")
@patch("services.ai_service.get_gemini_model")
def test_route_and_generate_text_complex_storyboard(mock_gemini, mock_claude):
    mock_claude.return_value = "claude output"

    result = route_and_generate_text("test prompt", task="COMPLEX_STORY")
    mock_claude.assert_called_with("test prompt", ModelRoutingConfig.COMPLEX_STORY, 0.7)
    mock_gemini.assert_not_called()
    assert result == "claude output"

def test_config_all_required_keys_defined():
    """Validates that all required model routing keys are defined."""
    required_keys = [
        "SOURCE_ANALYSIS", "TREND_ANALYSIS", "NORMAL_STORY", "COMPLEX_STORY",
        "REFERENCE_IMAGE", "VIDEO_DEFAULT", "VIDEO_FAST", "VIDEO_PREMIUM",
        "QUALITY_REVIEW", "QUALITY_REVIEW_ESCALATE", "VOICE_DEFAULT",
        "VOICE_PREMIUM", "VOICE_LONGFORM", "LIPSYNC"
    ]
    for k in required_keys:
        assert hasattr(ModelRoutingConfig, k), f"Missing key {k} on ModelRoutingConfig"
        val = getattr(ModelRoutingConfig, k)
        assert isinstance(val, str) and len(val) > 0, f"Key {k} has invalid value {val}"

# ============================================================================
# 2. DETERMINISTIC COMPLEXITY ROUTING TESTS
# ============================================================================

def test_determine_story_complexity_boundary_cases():
    """Validates boundary conditions for story complexity classification."""
    # Normal / baseline cases
    assert determine_story_complexity(target_duration_seconds=13.0, scene_count=3, requested_character_count=1) == "NORMAL"
    assert determine_story_complexity(target_duration_seconds=30.0, scene_count=4, requested_character_count=2) == "NORMAL"
    
    # Boundary: Duration > 30.0s
    assert determine_story_complexity(target_duration_seconds=30.1) == "COMPLEX"
    assert determine_story_complexity(target_duration_seconds=60.0) == "COMPLEX"
    
    # Boundary: Scene Count > 4
    assert determine_story_complexity(scene_count=4) == "NORMAL"
    assert determine_story_complexity(scene_count=5) == "COMPLEX"
    
    # Boundary: Character Count >= 3
    assert determine_story_complexity(requested_character_count=2) == "NORMAL"
    assert determine_story_complexity(requested_character_count=3) == "COMPLEX"
    assert determine_story_complexity(requested_character_count=5) == "COMPLEX"
    
    # Explicit Flag
    assert determine_story_complexity(is_complex_flag=True) == "COMPLEX"
    assert determine_story_complexity(target_duration_seconds=10.0, is_complex_flag=True) == "COMPLEX"

# ============================================================================
# 3. CALLER MODEL RESOLUTION & SOURCE-LEVEL NO-HARDCODING REGRESSION TEST
# ============================================================================

def test_source_analyzer_uses_model_routing_config():
    """Validates that analyze_semantics resolves model from ModelRoutingConfig.SOURCE_ANALYSIS."""
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = '{"semantic_scenes":[], "hook":{"hook_type":"VISUAL_SHOCK","hook_start_seconds":0.0,"hook_end_seconds":1.0,"confidence":1.0},"cta":{"exists":false},"visual_style":{"art_style":"3D","character_design":"Test"},"audio_profile":{"has_dialogue":false},"transcript_text":"","dialogue_beats":[]}'
    mock_client.models.generate_content.return_value = mock_resp
    
    with patch("services.source_analyzer.get_gemini_client", return_value=mock_client), \
         patch("builtins.open", mock_open(read_data=b"fake_video_bytes")), \
         patch("services.source_analyzer.types.Part.from_bytes", return_value=MagicMock()):
        source_analyzer_mod.analyze_semantics("/fake/video.mp4", [])
        
        call_kwargs = mock_client.models.generate_content.call_args[1]
        assert call_kwargs["model"] == ModelRoutingConfig.SOURCE_ANALYSIS

def test_trend_analyzer_uses_model_routing_config():
    """Validates that analyze_trend_video resolves model from ModelRoutingConfig.TREND_ANALYSIS."""
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = '{"art_style":"3D","character_design":"Test","humor_mechanism":"Joke","source_language":"EN","transcript_text":"","pacing_scenes":[]}'
    mock_client.models.generate_content.return_value = mock_resp
    
    with patch("services.trend_analyzer.get_gemini_client", return_value=mock_client), \
         patch("builtins.open", mock_open(read_data=b"fake_video_bytes")), \
         patch("services.trend_analyzer.types.Part.from_bytes", return_value=MagicMock()):
        trend_analyzer_mod.analyze_trend_video("/fake/video.mp4")
        
        call_kwargs = mock_client.models.generate_content.call_args[1]
        assert call_kwargs["model"] == ModelRoutingConfig.TREND_ANALYSIS

def test_lip_sync_service_uses_model_routing_config():
    """Validates that lip_sync_service passes ModelRoutingConfig.LIPSYNC."""
    with patch.dict(os.environ, {"SYNCLABS_API_KEY": "test_key"}), \
         patch("services.lip_sync_service.upload_to_gcs", return_value="https://storage.googleapis.com/test.mp4"), \
         patch("services.lip_sync_service.requests.post") as mock_post, \
         patch("services.lip_sync_service.requests.get") as mock_get:
        
        mock_post.return_value.ok = True
        mock_post.return_value.json.return_value = {"id": "sync_123"}
        
        mock_poll_resp = MagicMock()
        mock_poll_resp.ok = True
        mock_poll_resp.json.return_value = {"status": "COMPLETED", "outputUrl": "https://storage.googleapis.com/output.mp4"}
        
        mock_download_resp = MagicMock()
        mock_download_resp.ok = True
        mock_download_resp.content = b"video_bytes"
        
        mock_get.side_effect = [mock_poll_resp, mock_download_resp]
        
        result_path = lip_sync_mod.sync_lips("/fake/video.mp4", "/fake/audio.mp3")
        assert result_path is not None
        
        # Check payload model field
        post_payload = mock_post.call_args[1]["json"]
        assert post_payload["model"] == ModelRoutingConfig.LIPSYNC

def test_no_hardcoded_model_literals_in_services():
    """
    AST Analysis test verifying that no hardcoded model ID literals exist in core service files.
    This test will fail if a developer introduces a raw hardcoded model string.
    """
    forbidden_literals = [
        "gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.1-flash-lite",
        "gemini-3.1-pro-preview", "gemini-2.5-flash-image", "gemini-3.1-flash-image",
        "veo-3.1-generate-001", "veo-3.1-fast-generate-001", "eleven_v3",
        "eleven_flash_v2_5", "eleven_multilingual_v2", "lipsync-2"
    ]
    
    files_to_check = [
        os.path.join(BASE_DIR, "services", "source_analyzer.py"),
        os.path.join(BASE_DIR, "services", "trend_analyzer.py"),
        os.path.join(BASE_DIR, "core", "services", "production_director.py"),
        os.path.join(BASE_DIR, "services", "lip_sync_service.py")
    ]
    
    for file_path in files_to_check:
        assert os.path.exists(file_path), f"Target file does not exist: {file_path}"
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=file_path)
            
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                for forbidden in forbidden_literals:
                    assert node.value != forbidden, (
                        f"Hardcoded model literal '{forbidden}' found in {os.path.basename(file_path)} at line {node.lineno}! "
                        f"Must use ModelRoutingConfig instead."
                    )
