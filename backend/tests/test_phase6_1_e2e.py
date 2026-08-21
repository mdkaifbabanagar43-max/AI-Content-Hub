import pytest
from core.models.scene import Scene
from core.models.timeline import AudioAsset
from core.services.timeline_builder import TimelineBuilder

def test_phase6_1_e2e_duration_logic():
    builder = TimelineBuilder("PROJ_E2E")
    
    # Mock video durations
    mock_durations = {
        "raw_s1.mp4": 5.0,
        "raw_s2.mp4": 8.0,
        "raw_s3.mp4": 7.0,
    }
    
    # Monkeypatch _get_video_duration to simulate video files
    def mock_get_video_duration(video_path: str) -> float:
        return mock_durations.get(video_path, 0.0)
        
    builder._get_video_duration = mock_get_video_duration
    
    # SCENE 1: Video 5.0s, Audio 6.5s
    s1 = Scene(scene_id="S1", project_id="P", scene_number=1, duration=5.0)
    a1 = AudioAsset(asset_id="A1", uri="a1.mp3", duration=6.5, start_time=0.0, end_time=6.5)
    builder.add_scene(s1, 5.0, "raw_s1.mp4", [a1])
    
    # SCENE 2: Video 8.0s, Audio 5.0s
    s2 = Scene(scene_id="S2", project_id="P", scene_number=2, duration=8.0)
    a2 = AudioAsset(asset_id="A2", uri="a2.mp3", duration=5.0, start_time=0.0, end_time=5.0)
    builder.add_scene(s2, 8.0, "raw_s2.mp4", [a2])
    
    # SCENE 3: Video 7.0s, Audio 7.0s
    s3 = Scene(scene_id="S3", project_id="P", scene_number=3, duration=7.0)
    a3 = AudioAsset(asset_id="A3", uri="a3.mp3", duration=7.0, start_time=0.0, end_time=7.0)
    builder.add_scene(s3, 7.0, "raw_s3.mp4", [a3])
    
    # Execute Timing Reconciliation
    builder.reconcile_timing()
    
    items = builder.timeline.items
    
    # Assert Scene 1: 0 -> 6.5
    assert items[0].start_time == 0.0
    assert items[0].end_time == 6.5
    assert items[0].final_scene_duration == 6.5
    
    # Assert Scene 2: 6.5 -> 14.5
    assert items[1].start_time == 6.5
    assert items[1].end_time == 14.5
    assert items[1].final_scene_duration == 8.0
    
    # Assert Scene 3: 14.5 -> 21.5
    assert items[2].start_time == 14.5
    assert items[2].end_time == 21.5
    assert items[2].final_scene_duration == 7.0
    
    # Assert Total Duration
    assert builder.timeline.total_duration == 21.5
    
    print("\n[Phase 6.1 E2E Test] Success! All timeline assertions matched expected drift bounds.")
