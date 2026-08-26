import os
import pytest
from unittest.mock import patch
from core.models.source_analysis import SourceAnalysis
from services.source_analyzer import (
    probe_media_metadata,
    detect_scene_segments,
    run_source_analysis,
    GeminiSemanticResponse
)

FIXTURE_VIDEO = os.path.join(os.path.dirname(__file__), "fixtures", "test_video.mp4")

@pytest.fixture
def mock_gemini_response():
    return GeminiSemanticResponse(
        semantic_scenes=[
            {
                "scene_number": 1,
                "narrative_purpose": "Establish Hook",
                "visual_action": "Red screen",
                "emotion": "neutral",
                "pacing_intensity": "MEDIUM",
                "shot_type": "ESTABLISHING",
                "camera_motion": "STATIC",
                "character_roles": [],
                "location_summary": "Abstract red",
                "prop_summary": "None",
                "lighting_summary": "Bright",
                "transition": "CUT",
                "dialogue_intent": "None"
            },
            {
                "scene_number": 2,
                "narrative_purpose": "Escalation",
                "visual_action": "Green screen",
                "emotion": "neutral",
                "pacing_intensity": "MEDIUM",
                "shot_type": "WIDE",
                "camera_motion": "STATIC",
                "character_roles": [],
                "location_summary": "Abstract green",
                "prop_summary": "None",
                "lighting_summary": "Bright",
                "transition": "CUT",
                "dialogue_intent": "None"
            },
            {
                "scene_number": 3,
                "narrative_purpose": "Resolution",
                "visual_action": "Blue screen",
                "emotion": "neutral",
                "pacing_intensity": "MEDIUM",
                "shot_type": "CLOSE_UP",
                "camera_motion": "STATIC",
                "character_roles": [],
                "location_summary": "Abstract blue",
                "prop_summary": "None",
                "lighting_summary": "Bright",
                "transition": "CUT",
                "dialogue_intent": "None"
            }
        ],
        hook={
            "hook_type": "VISUAL_SHOCK",
            "hook_start_seconds": 0.0,
            "hook_end_seconds": 3.0,
            "hook_description": "Starts with red",
            "confidence": 0.9
        },
        cta={
            "exists": False,
            "start_seconds": None,
            "end_seconds": None,
            "type": "NONE",
            "description": None
        },
        visual_style={
            "art_style": "Abstract solid colors",
            "character_design": "None",
            "visual_style_summary": "Basic colors",
            "color_tone": "RGB",
            "lighting_summary": "Flat",
            "animation_or_live_action": "ANIMATION",
            "realism_level": "Low"
        },
        audio_profile={
            "has_speech": False,
            "speech_tempo": "UNKNOWN",
            "has_background_music": False,
            "music_mood": None,
            "sfx_present": False
        },
        transcript_text="[No speech]",
        dialogue_beats=[]
    )

def test_media_metadata_probing():
    # Only run if fixture exists
    if not os.path.exists(FIXTURE_VIDEO):
        pytest.skip(f"Fixture not found at {FIXTURE_VIDEO}")
        
    metadata = probe_media_metadata(FIXTURE_VIDEO)
    
    # Check that actual factual metrics were probed
    assert metadata.duration_seconds > 0
    assert metadata.width == 640
    assert metadata.height == 360
    assert metadata.fps == 30.0
    assert metadata.aspect_ratio == "16:9"
    assert metadata.has_audio is False

def test_scene_segments():
    if not os.path.exists(FIXTURE_VIDEO):
        pytest.skip("Fixture not found")
        
    segments = detect_scene_segments(FIXTURE_VIDEO, 10.0)
    
    assert len(segments) > 0
    assert segments[0].start_seconds == 0.0
    # Ensure they don't overlap and durations are correct
    for seg in segments:
        assert seg.end_seconds > seg.start_seconds
        assert seg.duration_seconds == round(seg.end_seconds - seg.start_seconds, 3)

@patch("services.source_analyzer.analyze_trend_video")
@patch("services.source_analyzer.analyze_semantics")
def test_full_source_analysis(mock_analyze, mock_trend_analyze, mock_gemini_response):
    if not os.path.exists(FIXTURE_VIDEO):
        pytest.skip("Fixture not found")
        
    mock_analyze.return_value = mock_gemini_response
    mock_trend_analyze.return_value = {"art_style": "Abstract solid colors", "character_design": "None"}
    
    analysis = run_source_analysis(FIXTURE_VIDEO, "test_source_id_001")
    
    # Validates against the normalized model
    assert isinstance(analysis, SourceAnalysis)
    assert analysis.source_video_id == "test_source_id_001"
    assert analysis.media_metadata.duration_seconds > 0
    assert analysis.hook.hook_type == "VISUAL_SHOCK"
    assert analysis.cta.exists is False
    assert len(analysis.semantic_scenes) == 3
    assert analysis.visual_style.animation_or_live_action == "ANIMATION"

def test_backward_compatibility():
    # Existing code in trend_analyzer.py must remain untouched
    from services.trend_analyzer import analyze_trend_video
    assert callable(analyze_trend_video)
