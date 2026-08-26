import pytest
from unittest.mock import patch, MagicMock
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.lip_sync_service import sync_lips

@pytest.fixture
def mock_env():
    with patch.dict(os.environ, {"SYNCLABS_API_KEY": "test_key"}):
        yield

@pytest.fixture
def mock_gcs_upload():
    with patch("services.lip_sync_service.upload_to_gcs") as mock_upload:
        # Return valid signed HTTPS URLs (not localhost)
        mock_upload.side_effect = ["https://storage.googleapis.com/test_video.mp4", "https://storage.googleapis.com/test_audio.mp3"]
        yield mock_upload

@pytest.fixture
def mock_requests():
    with patch("services.lip_sync_service.requests") as mock_req:
        yield mock_req

@pytest.fixture
def mock_sleep():
    with patch("services.lip_sync_service.time.sleep") as m_sleep:
        yield m_sleep

def test_sync_lips_success(mock_env, mock_gcs_upload, mock_requests, mock_sleep, tmp_path):
    # Setup paths
    video_path = str(tmp_path / "vid.mp4")
    audio_path = str(tmp_path / "aud.mp3")

    # Mock POST response
    mock_post_resp = MagicMock()
    mock_post_resp.ok = True
    mock_post_resp.json.return_value = {"id": "test_job_123"}
    mock_requests.post.return_value = mock_post_resp

    # Mock Polling GET responses
    # 1. Processing, 2. Completed
    mock_get_poll_1 = MagicMock()
    mock_get_poll_1.ok = True
    mock_get_poll_1.json.return_value = {"status": "PROCESSING"}
    
    mock_get_poll_2 = MagicMock()
    mock_get_poll_2.ok = True
    mock_get_poll_2.json.return_value = {"status": "COMPLETED", "outputUrl": "https://example.com/out.mp4"}
    
    # Mock Download GET response
    mock_get_download = MagicMock()
    mock_get_download.ok = True
    mock_get_download.content = b"synced_video_content"

    mock_requests.get.side_effect = [mock_get_poll_1, mock_get_poll_2, mock_get_download]

    # Execute
    result = sync_lips(video_path, audio_path)

    # Asserts
    assert result != video_path # Should return new temp path
    assert os.path.exists(result)
    with open(result, "rb") as f:
        assert f.read() == b"synced_video_content"
    
    # Verify SyncLabs payload
    call_kwargs = mock_requests.post.call_args[1]
    assert call_kwargs["json"]["model"] == "lipsync-2"
    assert len(call_kwargs["json"]["input"]) == 2
    assert call_kwargs["json"]["input"][0]["type"] == "video"

def test_sync_lips_failed(mock_env, mock_gcs_upload, mock_requests, mock_sleep):
    video_path = "test.mp4"
    audio_path = "test.mp3"

    mock_post_resp = MagicMock()
    mock_post_resp.ok = True
    mock_post_resp.json.return_value = {"id": "test_job"}
    mock_requests.post.return_value = mock_post_resp

    mock_get_poll = MagicMock()
    mock_get_poll.ok = True
    mock_get_poll.json.return_value = {"status": "FAILED"}
    mock_requests.get.return_value = mock_get_poll

    result = sync_lips(video_path, audio_path)
    assert result == video_path # Fallback

def test_sync_lips_rejected(mock_env, mock_gcs_upload, mock_requests, mock_sleep):
    video_path = "test.mp4"
    audio_path = "test.mp3"

    mock_post_resp = MagicMock()
    mock_post_resp.ok = True
    mock_post_resp.json.return_value = {"id": "test_job"}
    mock_requests.post.return_value = mock_post_resp

    mock_get_poll = MagicMock()
    mock_get_poll.ok = True
    mock_get_poll.json.return_value = {"status": "REJECTED"}
    mock_requests.get.return_value = mock_get_poll

    result = sync_lips(video_path, audio_path)
    assert result == video_path # Fallback

def test_sync_lips_timeout(mock_env, mock_gcs_upload, mock_requests, mock_sleep):
    video_path = "test.mp4"
    audio_path = "test.mp3"

    mock_post_resp = MagicMock()
    mock_post_resp.ok = True
    mock_post_resp.json.return_value = {"id": "test_job"}
    mock_requests.post.return_value = mock_post_resp

    # Return PROCESSING continuously
    mock_get_poll = MagicMock()
    mock_get_poll.ok = True
    mock_get_poll.json.return_value = {"status": "PROCESSING"}
    mock_requests.get.return_value = mock_get_poll

    result = sync_lips(video_path, audio_path)
    assert result == video_path # Fallback
    assert mock_requests.get.call_count == 60 # max_retries

def test_sync_lips_network_exception(mock_env, mock_gcs_upload, mock_requests):
    video_path = "test.mp4"
    audio_path = "test.mp3"

    mock_requests.post.side_effect = Exception("Connection Error")

    result = sync_lips(video_path, audio_path)
    assert result == video_path # Fallback

def test_sync_lips_gcs_fail_fallback(mock_env):
    video_path = "test.mp4"
    audio_path = "test.mp3"
    
    with patch("services.lip_sync_service.upload_to_gcs") as mock_upload:
        mock_upload.side_effect = Exception("GCS down")
        result = sync_lips(video_path, audio_path)
        assert result == video_path # Fallback

def test_sync_lips_local_url_fallback(mock_env, mock_gcs_upload):
    video_path = "test.mp4"
    audio_path = "test.mp3"
    
    # If URLs are localhost, should fallback without calling SyncLabs
    mock_gcs_upload.side_effect = ["http://localhost:8080/vid", "http://localhost:8080/aud"]
    
    with patch("services.lip_sync_service.requests") as mock_req:
        result = sync_lips(video_path, audio_path)
        assert result == video_path
        mock_req.post.assert_not_called()
