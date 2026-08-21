"""
Unified Secure Video Downloader Module
Provides a single, deterministic, secure download helper for all video import endpoints (Video Cloner, Trend Cloner, URL Import).
Enforces SSRF validation, anchored platform detection, duration limits, modernized yt-dlp as primary, and RapidAPI as fallback.
"""
import os
import re
import uuid
import json
import logging
import subprocess
import urllib.parse
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

import requests

from core.security import (
    validate_public_url,
    detect_anchored_platform,
    SSRFValidationError,
)
from config import TEMP_DIR

logger = logging.getLogger("video_downloader")

MAX_DURATION_SECONDS = 1800  # 30 minutes
MAX_FILE_SIZE_MB = 500
MOBILE_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
)


@dataclass
class DownloadResult:
    success: bool
    output_path: Optional[str] = None
    duration: float = 0.0
    platform: Optional[str] = None
    file_size_bytes: int = 0
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    retryable: bool = False


def _sanitize_url_for_log(url: str) -> str:
    """Strips query parameters and credentials from URLs before logging to prevent secret leaks."""
    try:
        parsed = urllib.parse.urlparse(url)
        # Retain scheme, host, and path; remove query/fragment/credentials
        clean_netloc = parsed.hostname or "unknown"
        if parsed.port and parsed.port not in (80, 443):
            clean_netloc = f"{clean_netloc}:{parsed.port}"
        return urllib.parse.urlunparse((parsed.scheme, clean_netloc, parsed.path, "", "", ""))
    except Exception:
        return "[sanitized_url]"


def _log_structured_error(
    stage: str,
    platform: Optional[str],
    error_type: str,
    error_message: str,
    retryable: bool = False,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """Logs structured, security-safe error data without leaking secrets or tokens."""
    safe_log = {
        "stage": stage,
        "platform": platform or "unknown",
        "error_type": error_type,
        "error_message": error_message,
        "retryable": retryable,
    }
    if extra:
        safe_log["details"] = extra
    logger.error(json.dumps(safe_log))


def _download_via_rapidapi(
    url: str, output_path: str, rapidapi_key: str
) -> Tuple[bool, Optional[str]]:
    """Attempts YouTube download via RapidAPI if configured. Returns (success, error_reason)."""
    yt_id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url)
    if not yt_id_match:
        return False, "Could not extract YouTube video ID"

    video_id = yt_id_match.group(1)
    api_url = f"https://social-media-video-downloader.p.rapidapi.com/youtube/v3/video/details?videoId={video_id}&urlAccess=proxied"
    headers = {
        "x-rapidapi-host": "social-media-video-downloader.p.rapidapi.com",
        "x-rapidapi-key": rapidapi_key,
    }

    video_tmp = output_path.replace(".mp4", "_v.mp4")
    audio_tmp = output_path.replace(".mp4", "_a.mp4")

    try:
        resp = requests.get(api_url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return False, f"RapidAPI HTTP status {resp.status_code}"

        data = resp.json()
        contents = data.get("contents", [{}])
        if not contents:
            return False, "Empty contents in RapidAPI response"

        videos = contents[0].get("videos", [])
        audios = contents[0].get("audios", [])

        best_video = None
        for v in videos:
            if v.get("label") in ["1080p", "720p"]:
                best_video = v
                break
        if not best_video and videos:
            best_video = videos[0]

        best_audio = None
        if audios:
            for a in audios:
                if "original" in a.get("label", "").lower():
                    best_audio = a
                    break
            if not best_audio:
                for a in audios:
                    lang = a.get("metadata", {}).get("language", "").lower()
                    if "en" in lang or "en" in a.get("label", "").lower():
                        best_audio = a
                        break
            if not best_audio:
                best_audio = audios[0]

        if not best_video or not best_audio:
            return False, "No valid video or audio streams found"

        video_url = best_video.get("url")
        audio_url = best_audio.get("url")
        if not video_url or not audio_url:
            return False, "Missing stream URLs in RapidAPI response"

        # Validate stream URLs against SSRF before downloading
        validate_public_url(video_url, require_https=False, allowed_schemes=("https", "http"))
        validate_public_url(audio_url, require_https=False, allowed_schemes=("https", "http"))

        with requests.get(video_url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(video_tmp, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        with requests.get(audio_url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(audio_tmp, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        merge_cmd = [
            "ffmpeg", "-y",
            "-i", video_tmp,
            "-i", audio_tmp,
            "-c:v", "copy",
            "-c:a", "aac",
            output_path,
        ]
        subprocess.run(merge_cmd, capture_output=True, check=True)
        return True, None
    except Exception as e:
        return False, f"RapidAPI download exception: {str(e)}"
    finally:
        if os.path.exists(video_tmp):
            try:
                os.remove(video_tmp)
            except OSError:
                pass
        if os.path.exists(audio_tmp):
            try:
                os.remove(audio_tmp)
            except OSError:
                pass


def download_video(
    url: str,
    output_path: Optional[str] = None,
    max_duration_seconds: int = MAX_DURATION_SECONDS,
) -> DownloadResult:
    """
    Deterministically and securely downloads a video from a supported platform.
    
    Order of execution:
    1. Strict SSRF validation (validate_public_url).
    2. Anchored platform detection (detect_anchored_platform).
    3. PRIMARY: Modernized yt-dlp invocation (duration probe + mobile UA + iOS/Android extraction args + format fallback).
    4. FALLBACK (YouTube only): If yt-dlp fails and RAPIDAPI_KEY is present, attempt RapidAPI downloader.
    5. If both fail: return structured failure with sanitized logging.
    """
    if not url or not isinstance(url, str):
        _log_structured_error("url_import", None, "invalid_input", "URL is missing or empty")
        return DownloadResult(
            success=False,
            error_type="invalid_input",
            error_message="A valid non-empty URL is required.",
        )

    clean_url = url.strip()

    # Step 1: Strict SSRF & Domain Validation
    try:
        validate_public_url(clean_url, require_https=False, allowed_schemes=("https", "http"))
    except SSRFValidationError as e:
        _log_structured_error("url_import", None, "ssrf_blocked", str(e))
        return DownloadResult(
            success=False,
            error_type="ssrf_blocked",
            error_message=f"Invalid or restricted URL: {str(e)}",
        )
    except Exception as e:
        _log_structured_error("url_import", None, "url_parse_error", str(e))
        return DownloadResult(
            success=False,
            error_type="url_parse_error",
            error_message=f"Failed to validate URL: {str(e)}",
        )

    # Step 2: Detect Anchored Platform
    platform = detect_anchored_platform(clean_url)
    if not platform:
        _log_structured_error("url_import", None, "unsupported_platform", "Domain not recognized")
        return DownloadResult(
            success=False,
            error_type="unsupported_platform",
            error_message="Unsupported platform. We support YouTube, TikTok, Instagram, X/Twitter, Facebook, and Vimeo.",
        )

    # Prepare output path
    if not output_path:
        unique_id = uuid.uuid4().hex[:8]
        output_path = os.path.join(TEMP_DIR, f"url_import_{unique_id}.mp4")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # Step 3: PRIMARY — Modernized yt-dlp Invocation
    # 3a. Probe duration (fast, non-blocking)
    duration = 0.0
    probe_cmd = [
        "yt-dlp",
        "--user-agent", MOBILE_USER_AGENT,
        "--no-download",
        "--print", "duration",
        "--no-warnings",
        "--quiet",
    ]
    if platform == "youtube":
        probe_cmd.extend(["--extractor-args", "youtube:player_client=ios,android"])
    probe_cmd.append(clean_url)

    try:
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=30)
        if probe_result.returncode == 0 and probe_result.stdout.strip():
            try:
                duration = float(probe_result.stdout.strip().splitlines()[0])
                if max_duration_seconds > 0 and duration > max_duration_seconds:
                    _log_structured_error(
                        "url_import",
                        platform,
                        "duration_limit_exceeded",
                        f"Video duration {duration:.1f}s exceeds limit {max_duration_seconds}s",
                    )
                    return DownloadResult(
                        success=False,
                        platform=platform,
                        duration=duration,
                        error_type="duration_limit_exceeded",
                        error_message=f"Video is too long ({int(duration // 60)}min). Maximum is {int(max_duration_seconds // 60)} minutes.",
                    )
            except (ValueError, IndexError):
                duration = 0.0
    except subprocess.TimeoutExpired:
        logger.warning("[VideoDownloader] Metadata duration probe timed out, proceeding to download.")
    except Exception as e:
        logger.warning(f"[VideoDownloader] Duration probe error: {e}")

    # 3b. Download with modernized parameters
    download_cmd = [
        "yt-dlp",
        "--user-agent", MOBILE_USER_AGENT,
        "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--no-playlist",
        "--no-warnings",
        "--max-filesize", f"{MAX_FILE_SIZE_MB}M",
        "-o", output_path,
    ]
    if platform == "youtube":
        download_cmd.extend(["--extractor-args", "youtube:player_client=ios,android"])
    download_cmd.append(clean_url)

    ytdlp_success = False
    ytdlp_error_type = "extraction_error"
    ytdlp_user_msg = "Failed to download video from URL. Please check the link and try again."

    try:
        download_result = subprocess.run(
            download_cmd, capture_output=True, text=True, timeout=300
        )
        if download_result.returncode == 0:
            # Handle possible file extension alterations from yt-dlp
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                for ext in [".mp4", ".webm", ".mkv", ".mp4.mkv"]:
                    alt_path = output_path.replace(".mp4", ext)
                    if os.path.exists(alt_path) and os.path.getsize(alt_path) > 0:
                        try:
                            if os.path.exists(output_path):
                                os.remove(output_path)
                            os.rename(alt_path, output_path)
                            break
                        except OSError:
                            output_path = alt_path
                            break

            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                ytdlp_success = True
        else:
            raw_stderr = download_result.stderr.strip() if download_result.stderr else "Unknown error"
            if "Private video" in raw_stderr or "Sign in" in raw_stderr:
                ytdlp_error_type = "auth_required"
                ytdlp_user_msg = "This video is private or requires login."
            elif "Video unavailable" in raw_stderr or "not available" in raw_stderr:
                ytdlp_error_type = "video_unavailable"
                ytdlp_user_msg = "This video is unavailable or has been removed."
            elif "Unsupported URL" in raw_stderr:
                ytdlp_error_type = "unsupported_url"
                ytdlp_user_msg = "This URL is not supported. Please paste a direct video link."
            elif "403" in raw_stderr:
                ytdlp_error_type = "forbidden_403"
                ytdlp_user_msg = "Video source access was denied by provider."

            _log_structured_error("url_import", platform, ytdlp_error_type, raw_stderr[:300])

    except subprocess.TimeoutExpired:
        ytdlp_error_type = "download_timeout"
        ytdlp_user_msg = "Video download timed out. Please try a shorter video."
        _log_structured_error("url_import", platform, "download_timeout", "yt-dlp process timed out (300s)", retryable=True)
    except Exception as e:
        ytdlp_error_type = "process_error"
        ytdlp_user_msg = "Failed to start video downloader."
        _log_structured_error("url_import", platform, "process_error", str(e))

    if ytdlp_success:
        size_bytes = os.path.getsize(output_path)
        return DownloadResult(
            success=True,
            output_path=output_path,
            duration=duration,
            platform=platform,
            file_size_bytes=size_bytes,
        )

    # Step 4: FALLBACK (YouTube only) — RapidAPI integration
    if platform == "youtube":
        rapidapi_key = os.getenv("RAPIDAPI_KEY")
        if rapidapi_key:
            logger.info(f"[VideoDownloader] yt-dlp failed ({ytdlp_error_type}). Attempting RapidAPI fallback...")
            rapid_success, reason = _download_via_rapidapi(clean_url, output_path, rapidapi_key)
            if rapid_success and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                size_bytes = os.path.getsize(output_path)
                return DownloadResult(
                    success=True,
                    output_path=output_path,
                    duration=duration,
                    platform=platform,
                    file_size_bytes=size_bytes,
                )
            else:
                _log_structured_error("url_import", platform, "rapidapi_fallback_failed", str(reason))

    # Step 5: Both failed or non-YouTube extraction failed
    return DownloadResult(
        success=False,
        platform=platform,
        error_type=ytdlp_error_type,
        error_message=ytdlp_user_msg,
    )
