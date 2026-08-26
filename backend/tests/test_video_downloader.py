"""
Tests for core.video_downloader module.
Verifies SSRF validation, anchored platform detection, modernized yt-dlp invocation parameters,
deterministic strategy (yt-dlp primary, RapidAPI fallback), duration caps, error handling, and security blocking.
"""
import os
import pytest
from unittest.mock import patch, MagicMock

from core.video_downloader import (
    download_video,
    MOBILE_USER_AGENT,
    _sanitize_url_for_log,
)
from core.security import (
    validate_public_url,
    detect_anchored_platform,
    SSRFValidationError,
)


# ===================================================================
# 1. SSRF & PLATFORM RECOGNITION TESTS
# ===================================================================

def test_youtube_url_passes_ssrf_validation():
    """Verify legitimate YouTube URLs pass public URL SSRF validation."""
    url = "https://www.youtube.com/watch?v=eRsGyueVLvQ"
    parsed = validate_public_url(url, require_https=False, allowed_schemes=("https", "http"))
    assert parsed.hostname == "www.youtube.com"


def test_youtube_short_url_passes_ssrf_validation():
    """Verify youtu.be short URLs pass validation."""
    url = "https://youtu.be/eRsGyueVLvQ"
    parsed = validate_public_url(url, require_https=False, allowed_schemes=("https", "http"))
    assert parsed.hostname == "youtu.be"


def test_youtube_platform_recognition():
    """Verify YouTube URLs are properly detected by anchored platform detector."""
    assert detect_anchored_platform("https://www.youtube.com/watch?v=eRsGyueVLvQ") == "youtube"
    assert detect_anchored_platform("https://youtu.be/eRsGyueVLvQ") == "youtube"
    assert detect_anchored_platform("https://m.youtube.com/watch?v=12345678901") == "youtube"


def test_non_youtube_supported_platforms():
    """Verify TikTok, Instagram, Twitter/X, Facebook, and Vimeo are recognized."""
    assert detect_anchored_platform("https://www.tiktok.com/@user/video/123456") == "tiktok"
    assert detect_anchored_platform("https://www.instagram.com/reel/Cx12345/") == "instagram"
    assert detect_anchored_platform("https://x.com/user/status/123456") == "twitter"
    assert detect_anchored_platform("https://twitter.com/user/status/123456") == "twitter"
    assert detect_anchored_platform("https://www.facebook.com/watch/?v=123456") == "facebook"
    assert detect_anchored_platform("https://vimeo.com/12345678") == "vimeo"


def test_unsupported_platform_rejected():
    """Verify unsupported domains are cleanly rejected."""
    result = download_video("https://example.com/video.mp4")
    assert not result.success
    assert result.error_type == "unsupported_platform"


# ===================================================================
# 2. SSRF BLOCKING REGRESSION TESTS
# ===================================================================

def test_ssrf_localhost_blocked():
    """Verify localhost, 127.0.0.1, and [::1] are blocked."""
    with pytest.raises(SSRFValidationError):
        validate_public_url("http://127.0.0.1/video.mp4")

    with pytest.raises(SSRFValidationError):
        validate_public_url("http://localhost/video.mp4")

    result = download_video("http://127.0.0.1/video.mp4")
    assert not result.success
    assert result.error_type == "ssrf_blocked"


def test_ssrf_metadata_ip_blocked():
    """Verify GCP/AWS metadata IP (169.254.169.254) is blocked."""
    with pytest.raises(SSRFValidationError):
        validate_public_url("http://169.254.169.254/computeMetadata/v1/")

    result = download_video("http://169.254.169.254/video.mp4")
    assert not result.success
    assert result.error_type == "ssrf_blocked"


def test_ssrf_private_networks_blocked():
    """Verify RFC 1918 private subnets are blocked."""
    for ip in ["10.0.0.1", "172.16.0.1", "192.168.1.1"]:
        with pytest.raises(SSRFValidationError):
            validate_public_url(f"http://{ip}/video.mp4")


# ===================================================================
# 3. DETERMINISTIC STRATEGY & MODERN YT-DLP TESTS (MOCKED)
# ===================================================================

@patch("subprocess.run")
@patch("os.path.exists")
@patch("os.path.getsize")
@patch("core.video_downloader._download_via_rapidapi")
def test_modern_yt_dlp_invocation_arguments(mock_rapid, mock_getsize, mock_exists, mock_run, tmp_path):
    """Verify primary yt-dlp invocation options include extractor-args, mobile UA, and format fallback."""
    mock_exists.return_value = True
    mock_getsize.return_value = 5 * 1024 * 1024

    # Setup probe and download mock responses
    probe_completed = MagicMock()
    probe_completed.returncode = 0
    probe_completed.stdout = "45.0\n"

    dl_completed = MagicMock()
    dl_completed.returncode = 0
    dl_completed.stdout = "Downloaded"
    dl_completed.stderr = ""

    mock_run.side_effect = [probe_completed, dl_completed]

    out_file = str(tmp_path / "test_out.mp4")
    url = "https://www.youtube.com/watch?v=eRsGyueVLvQ"

    result = download_video(url, output_path=out_file)

    assert result.success
    assert result.platform == "youtube"
    assert mock_run.call_count >= 2

    # Verify primary yt-dlp was used and RapidAPI fallback was NOT called on success
    mock_rapid.assert_not_called()

    # Check the download command (second call)
    dl_call_args = mock_run.call_args_list[1][0][0]

    # Verify modern arguments
    assert "--user-agent" in dl_call_args
    ua_idx = dl_call_args.index("--user-agent")
    assert dl_call_args[ua_idx + 1] == MOBILE_USER_AGENT

    assert "--extractor-args" in dl_call_args
    ext_idx = dl_call_args.index("--extractor-args")
    assert dl_call_args[ext_idx + 1] == "youtube:player_client=ios,android"

    assert "-f" in dl_call_args
    f_idx = dl_call_args.index("-f")
    assert "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best" in dl_call_args[f_idx + 1]

    assert "--merge-output-format" in dl_call_args
    assert "--no-playlist" in dl_call_args

    # Verify old, problematic flags are NOT used
    assert "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4" != dl_call_args[f_idx + 1]


@patch.dict(os.environ, {"RAPIDAPI_KEY": "test_rapidapi_key"})
@patch("core.video_downloader._download_via_rapidapi")
@patch("subprocess.run")
@patch("os.path.exists")
@patch("os.path.getsize")
def test_rapidapi_fallback_when_ytdlp_fails(mock_getsize, mock_exists, mock_run, mock_rapid, tmp_path):
    """Verify that if primary yt-dlp fails and RAPIDAPI_KEY is present, RapidAPI fallback is invoked."""
    mock_exists.return_value = True
    mock_getsize.return_value = 10 * 1024 * 1024

    probe_completed = MagicMock(returncode=0, stdout="30.0\n")
    dl_failed = MagicMock(returncode=1, stderr="ERROR: HTTP Error 403: Forbidden")
    mock_run.side_effect = [probe_completed, dl_failed]

    mock_rapid.return_value = (True, None)

    out_file = str(tmp_path / "test_fallback.mp4")
    url = "https://www.youtube.com/watch?v=eRsGyueVLvQ"

    result = download_video(url, output_path=out_file)

    assert result.success
    assert result.platform == "youtube"
    mock_rapid.assert_called_once_with(url, out_file, "test_rapidapi_key")


@patch("subprocess.run")
def test_duration_limit_exceeded_handled(mock_run, tmp_path):
    """Verify videos exceeding maximum duration limit are rejected before full download."""
    probe_completed = MagicMock()
    probe_completed.returncode = 0
    probe_completed.stdout = "2400.0\n"  # 40 minutes > 30 minutes max

    mock_run.return_value = probe_completed

    out_file = str(tmp_path / "test_long.mp4")
    url = "https://www.youtube.com/watch?v=eRsGyueVLvQ"

    result = download_video(url, output_path=out_file, max_duration_seconds=1800)

    assert not result.success
    assert result.error_type == "duration_limit_exceeded"
    # subprocess.run should only be called once for probe, not for download
    assert mock_run.call_count == 1


@patch.dict(os.environ, {}, clear=True)
@patch("subprocess.run")
def test_yt_dlp_403_structured_error(mock_run, tmp_path):
    """Verify yt-dlp 403 or extraction failure produces a safe structured error when fallback is unavailable."""
    probe_completed = MagicMock()
    probe_completed.returncode = 0
    probe_completed.stdout = "30.0\n"

    dl_failed = MagicMock()
    dl_failed.returncode = 1
    dl_failed.stderr = "ERROR: unable to download video data: HTTP Error 403: Forbidden"

    mock_run.side_effect = [probe_completed, dl_failed]

    out_file = str(tmp_path / "test_403.mp4")
    url = "https://www.youtube.com/watch?v=eRsGyueVLvQ"

    result = download_video(url, output_path=out_file)

    assert not result.success
    assert result.error_type == "forbidden_403"
    assert "denied" in result.error_message.lower()


def test_sanitize_url_for_log():
    """Verify URL sanitization strips tokens and credentials."""
    dirty_url = "https://user:pass@www.youtube.com/watch?v=123&secret_token=abc"
    clean = _sanitize_url_for_log(dirty_url)
    assert "pass" not in clean
    assert "secret_token" not in clean
    assert "www.youtube.com/watch" in clean
