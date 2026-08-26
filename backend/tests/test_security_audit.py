"""
Security Regression Test Suite
Automated regression tests validating security remediations:
- Authentication hardening (test_token/dev_token rejection)
- Insecure endpoints removal (/mock-upload and /temp)
- SSRF prevention & IP filtering
- CORS allowlist enforcement
- Rate limiting protection
- Provider secret boundaries
"""
import pytest
from fastapi.testclient import TestClient

from main import app
from core.security import (
    validate_public_url,
    detect_anchored_platform,
    is_ip_blocked,
    SSRFValidationError
)
from core.rate_limiter import InMemoryRateLimiter


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    return TestClient(app)


# ===================================================================
# 1. AUTHENTICATION REGRESSION TESTS
# ===================================================================

def test_missing_auth_header_rejected(client):
    """Endpoints requiring auth must return 401 when header is missing."""
    resp = client.get("/api/me")
    assert resp.status_code == 401


def test_invalid_bearer_format_rejected(client):
    """Malformed bearer tokens must return 401."""
    resp = client.get("/api/me", headers={"Authorization": "Basic dXNlcjpwYXNz"})
    assert resp.status_code == 401


def test_test_token_rejected_at_runtime(client):
    """Hardcoded 'test_token' must NO LONGER bypass authentication."""
    resp = client.get("/api/me", headers={"Authorization": "Bearer test_token"})
    assert resp.status_code == 401


def test_dev_token_rejected_at_runtime(client):
    """Hardcoded 'dev_token' must NO LONGER bypass authentication."""
    resp = client.get("/api/me", headers={"Authorization": "Bearer dev_token"})
    assert resp.status_code == 401


# ===================================================================
# 2. INSECURE ENDPOINT & STATIC DIR REMOVAL TESTS
# ===================================================================

def test_mock_upload_endpoint_removed(client):
    """The /mock-upload endpoint must not exist."""
    resp = client.put("/mock-upload/exploit.txt", content=b"malicious payload")
    assert resp.status_code in (404, 405)


def test_temp_static_mount_removed(client):
    """The /temp static mount must not be exposed over HTTP."""
    resp = client.get("/temp/some_file.mp4")
    assert resp.status_code == 404


# ===================================================================
# 3. SSRF & URL VALIDATION TESTS
# ===================================================================

def test_ssrf_blocked_ip_ranges():
    """Verify that private, loopback, link-local, and metadata IPs are identified as blocked."""
    # Loopback
    assert is_ip_blocked("127.0.0.1") is True
    assert is_ip_blocked("127.0.1.100") is True
    # Link-local & Cloud metadata
    assert is_ip_blocked("169.254.169.254") is True
    assert is_ip_blocked("169.254.1.1") is True
    # RFC 1918 Private networks
    assert is_ip_blocked("10.0.0.1") is True
    assert is_ip_blocked("172.16.0.1") is True
    assert is_ip_blocked("192.168.1.1") is True
    # Current network & Multicast
    assert is_ip_blocked("0.0.0.0") is True
    assert is_ip_blocked("224.0.0.1") is True
    # IPv6 Loopback
    assert is_ip_blocked("::1") is True


def test_ssrf_validator_rejects_localhost_and_metadata():
    """validate_public_url must reject direct targets to localhost, 127.0.0.1, or 169.254.169.254."""
    with pytest.raises(SSRFValidationError):
        validate_public_url("https://127.0.0.1/secret", require_https=False, allowed_schemes=("http", "https"))

    with pytest.raises(SSRFValidationError):
        validate_public_url("https://169.254.169.254/latest/meta-data/", require_https=False, allowed_schemes=("http", "https"))

    with pytest.raises(SSRFValidationError):
        validate_public_url("https://localhost:8080/admin", require_https=False, allowed_schemes=("http", "https"))


def test_ssrf_validator_rejects_non_http_schemes():
    """File, FTP, gopher schemes must be strictly rejected."""
    for bad_scheme in ["file:///etc/passwd", "ftp://evil.com/file", "gopher://evil.com"]:
        with pytest.raises(SSRFValidationError):
            validate_public_url(bad_scheme, require_https=False, allowed_schemes=("http", "https"))


def test_anchored_platform_detection():
    """Platform detection must be anchored to domain boundaries."""
    # Valid platform URLs
    assert detect_anchored_platform("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "youtube"
    assert detect_anchored_platform("https://youtu.be/dQw4w9WgXcQ") == "youtube"
    assert detect_anchored_platform("https://www.tiktok.com/@user/video/12345") == "tiktok"
    assert detect_anchored_platform("https://instagram.com/reel/12345") == "instagram"

    # Malicious unanchored spoof attempts (MUST RETURN NONE)
    assert detect_anchored_platform("https://attacker.com/youtube.com") is None
    assert detect_anchored_platform("https://169.254.169.254/v1?youtube.com") is None
    assert detect_anchored_platform("https://evil-youtube.com/watch") is None
    assert detect_anchored_platform("https://youtube.com.attacker.com/watch") is None


# ===================================================================
# 4. CORS ALLOWLIST TESTS
# ===================================================================

def test_cors_allowed_canonical_origins(client):
    """Canonical production domains must receive CORS allow headers."""
    canonical_origins = [
        "https://cloneframe.com",
        "https://app.cloneframe.com",
        "https://shortcutsai.vercel.app"
    ]
    for origin in canonical_origins:
        resp = client.options(
            "/api/me",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET"
            }
        )
        assert resp.headers.get("access-control-allow-origin") == origin


def test_cors_rejects_arbitrary_vercel_subdomains(client):
    """Arbitrary third-party .vercel.app domains must NOT receive allow headers."""
    malicious_origin = "https://evil-attacker-site.vercel.app"
    resp = client.options(
        "/api/me",
        headers={
            "Origin": malicious_origin,
            "Access-Control-Request-Method": "GET"
        }
    )
    assert resp.headers.get("access-control-allow-origin") != malicious_origin


# ===================================================================
# 5. RATE LIMITER UNIT TESTS
# ===================================================================

def test_in_memory_rate_limiter_sliding_window():
    """Rate limiter must allow requests within threshold and block when exceeded."""
    limiter = InMemoryRateLimiter()
    user_id = "test_user_rate_test"
    endpoint = "test_endpoint"

    # Max 3 requests in 60s
    assert limiter.check_rate_limit(user_id, endpoint, max_requests=3, window_seconds=60) is True
    assert limiter.check_rate_limit(user_id, endpoint, max_requests=3, window_seconds=60) is True
    assert limiter.check_rate_limit(user_id, endpoint, max_requests=3, window_seconds=60) is True

    # 4th request must be blocked
    assert limiter.check_rate_limit(user_id, endpoint, max_requests=3, window_seconds=60) is False

    # Different user must be independent
    assert limiter.check_rate_limit("other_user", endpoint, max_requests=3, window_seconds=60) is True


# ===================================================================
# 6. PROVIDER SECRET ISOLATION
# ===================================================================

def test_system_config_does_not_expose_secrets(client):
    """The public /system-config endpoint must not return any API keys or secrets."""
    resp = client.get("/system-config")
    assert resp.status_code == 200
    data = resp.json()
    raw_text = str(data).lower()
    assert "sk_" not in raw_text
    assert "aiza" not in raw_text
    assert "private" not in raw_text
    assert "secret" not in raw_text
    assert "key" not in raw_text or "pricing" in raw_text


# ===================================================================
# 7. URL IMPORT & YT-DLP INTEGRATION TEST (MOCKED)
# ===================================================================

def test_url_import_yt_dlp_invocation_mocked(client):
    """Verify URL import endpoint accepts valid video URL, invokes downloader, and handles response without real external calls."""
    from unittest.mock import patch
    from core.auth import get_current_user

    app.dependency_overrides[get_current_user] = lambda: "test_user_import_test"
    try:
        with patch("routers.url_import.download_video") as mock_dl, \
             patch("core.storage_client.upload_to_gcs") as mock_upload, \
             patch("os.path.exists") as mock_exists, \
             patch("os.path.getsize") as mock_size:

            from core.video_downloader import DownloadResult
            mock_dl.return_value = DownloadResult(
                success=True,
                output_path="/tmp/test.mp4",
                duration=30.0,
                platform="youtube",
                file_size_bytes=1024 * 1024
            )
            mock_exists.return_value = True
            mock_size.return_value = 1024 * 1024
            mock_upload.return_value = "https://storage.googleapis.com/test-bucket/url_import_123.mp4"

            resp = client.post(
                "/import-video-url",
                json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
            )
            assert resp.status_code == 200
            assert resp.json()["platform"] == "youtube"
    finally:
        app.dependency_overrides.pop(get_current_user, None)

