import pytest
from unittest.mock import patch, MagicMock
from core.models.scene import Scene
from core.models.timeline import AudioAsset
from core.services.timeline_builder import TimelineBuilder, TimelineValidationException

@pytest.fixture
def mock_timeline_builder():
    return TimelineBuilder("PROJ1")

def test_timeline_duration_logic(mock_timeline_builder):
    # Mock _get_video_duration to return 5.0 seconds for the raw video
    with patch.object(mock_timeline_builder, '_get_video_duration', return_value=5.0):
        scene1 = Scene(scene_id="SCENE1", project_id="PROJ1", scene_number=1, duration=5.0)
        
        # Audio is 6.5 seconds (longer than video)
        audio = AudioAsset(asset_id="A1", uri="audio.mp3", duration=6.5, start_time=0.0, end_time=6.5)
        
        mock_timeline_builder.add_scene(scene1, 5.0, "raw.mp4", [audio])
        
        # The final scene duration should be 6.5 seconds, matching the longest asset
        assert mock_timeline_builder.timeline.items[0].final_scene_duration == 6.5

def test_timeline_reconcile_timing(mock_timeline_builder):
    with patch.object(mock_timeline_builder, '_get_video_duration', return_value=5.0):
        scene1 = Scene(scene_id="S1", project_id="P1", scene_number=1, duration=5.0)
        scene2 = Scene(scene_id="S2", project_id="P1", scene_number=2, duration=5.0)
        
        audio1 = AudioAsset(asset_id="A1", uri="a1.mp3", duration=6.5, start_time=0.0, end_time=6.5)
        audio2 = AudioAsset(asset_id="A2", uri="a2.mp3", duration=4.0, start_time=0.0, end_time=4.0)
        
        mock_timeline_builder.add_scene(scene1, 5.0, "raw1.mp4", [audio1])
        mock_timeline_builder.add_scene(scene2, 5.0, "raw2.mp4", [audio2])
        
        mock_timeline_builder.reconcile_timing()
        
        items = mock_timeline_builder.timeline.items
        
        # S1 is 6.5s
        assert items[0].start_time == 0.0
        assert items[0].end_time == 6.5
        assert items[0].dialogue_assets[0].start_time == 0.0
        
        # S2 is 5.0s (video is 5.0, audio is 4.0, max is 5.0)
        assert items[1].start_time == 6.5
        assert items[1].end_time == 11.5
        assert items[1].dialogue_assets[0].start_time == 6.5
        
        assert mock_timeline_builder.timeline.total_duration == 11.5

def test_timeline_validation(mock_timeline_builder):
    with patch.object(mock_timeline_builder, '_get_video_duration', return_value=0.0):
        scene1 = Scene(scene_id="S1", project_id="P1", scene_number=1, duration=5.0)
        
        # Invalid video path and 0 duration
        mock_timeline_builder.add_scene(scene1, 5.0, "nonexistent.mp4", [])
        
        with pytest.raises(TimelineValidationException):
            mock_timeline_builder.validate()

@patch("moviepy.editor.VideoFileClip")
@patch("moviepy.editor.ImageClip")
@patch("moviepy.editor.concatenate_videoclips")
def test_normalize_video_shorter_than_audio(mock_concat, mock_image_clip, mock_video_clip, mock_timeline_builder):
    """TEST 1: video = 5.0 sec, audio = 6.5 sec -> normalized video = approximately 6.5 sec"""
    # Mock video duration
    mock_v_instance = MagicMock()
    mock_v_instance.duration = 5.0
    mock_v_instance.fps = 30
    mock_v_instance.get_frame.return_value = "dummy_frame"
    mock_video_clip.return_value = mock_v_instance
    
    mock_timeline_builder._get_video_duration = MagicMock(return_value=5.0)
    
    mock_i_instance = MagicMock()
    mock_i_instance.set_duration.return_value = mock_i_instance
    mock_image_clip.return_value = mock_i_instance
    
    mock_final = MagicMock()
    mock_concat.return_value = mock_final
    
    # Run
    res = mock_timeline_builder.normalize_video_to_audio_duration("raw.mp4", 6.5, "SCN1")
    
    # Assert
    mock_image_clip.assert_called_with("dummy_frame")
    mock_i_instance.set_duration.assert_called_with(1.5) # 6.5 - 5.0
    mock_concat.assert_called_with([mock_v_instance, mock_i_instance])
    mock_final.write_videofile.assert_called()
    assert "normalized" in res

def test_normalize_video_longer_than_audio(mock_timeline_builder):
    """TEST 2: video = 8.0 sec, audio = 5.0 sec -> no unnecessary freeze padding"""
    mock_timeline_builder._get_video_duration = MagicMock(return_value=8.0)
    
    # Run
    res = mock_timeline_builder.normalize_video_to_audio_duration("raw.mp4", 5.0, "SCN1")
    
    # Assert
    assert res == "raw.mp4" # Returns original raw video unmodified

