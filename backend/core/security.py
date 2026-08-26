"""
Security & SSRF Protection Module
Provides centralized URL validation, IP filtering, and safe HTTP streaming
to protect against Server-Side Request Forgery (SSRF) and malicious redirects.
"""
import os
import re
import socket
import ipaddress
import urllib.parse
from typing import Optional, List, Tuple
import requests

# Blocked IP Networks (IPv4 & IPv6)
BLOCKED_NETWORKS: List[ipaddress.IPv4Network | ipaddress.IPv6Network] = [
    ipaddress.ip_network("0.0.0.0/8"),          # Current network
    ipaddress.ip_network("10.0.0.0/8"),         # RFC 1918 Private
    ipaddress.ip_network("100.64.0.0/10"),      # Carrier-grade NAT
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback
    ipaddress.ip_network("169.254.0.0/16"),     # Link-local & Cloud Metadata (169.254.169.254)
    ipaddress.ip_network("172.16.0.0/12"),      # RFC 1918 Private
    ipaddress.ip_network("192.0.0.0/24"),       # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),       # TEST-NET-1
    ipaddress.ip_network("192.168.0.0/16"),     # RFC 1918 Private
    ipaddress.ip_network("198.18.0.0/15"),      # Network benchmark tests
    ipaddress.ip_network("198.51.100.0/24"),    # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),     # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),        # Multicast
    ipaddress.ip_network("240.0.0.0/4"),        # Reserved / Future use
    ipaddress.ip_network("255.255.255.255/32"), # Broadcast
    # IPv6 Blocked Ranges
    ipaddress.ip_network("::1/128"),            # IPv6 Loopback
    ipaddress.ip_network("::/128"),             # IPv6 Unspecified
    ipaddress.ip_network("fe80::/10"),          # IPv6 Link-local
    ipaddress.ip_network("fc00::/7"),           # IPv6 Unique local (Private)
    ipaddress.ip_network("ff00::/8"),           # IPv6 Multicast
]

# Supported platform domains with strictly anchored hostname patterns
ANCHORED_PLATFORM_PATTERNS = {
    "youtube": re.compile(r"^(?:[a-zA-Z0-9-]+\.)*(?:youtube\.com|youtu\.be)$", re.IGNORECASE),
    "tiktok": re.compile(r"^(?:[a-zA-Z0-9-]+\.)*tiktok\.com$", re.IGNORECASE),
    "instagram": re.compile(r"^(?:[a-zA-Z0-9-]+\.)*instagram\.com$", re.IGNORECASE),
    "twitter": re.compile(r"^(?:[a-zA-Z0-9-]+\.)*(?:twitter\.com|x\.com)$", re.IGNORECASE),
    "facebook": re.compile(r"^(?:[a-zA-Z0-9-]+\.)*(?:facebook\.com|fb\.watch)$", re.IGNORECASE),
    "vimeo": re.compile(r"^(?:[a-zA-Z0-9-]+\.)*vimeo\.com$", re.IGNORECASE),
}


class SSRFValidationError(Exception):
    """Raised when a URL or IP fails SSRF security checks."""
    pass


def is_ip_blocked(ip_str: str) -> bool:
    """Checks if an IP address string belongs to any private/reserved/loopback/metadata range."""
    try:
        ip = ipaddress.ip_address(ip_str)
        for net in BLOCKED_NETWORKS:
            if ip in net:
                return True
        return False
    except ValueError:
        return True


def resolve_hostname_ips(hostname: str, port: int = 443) -> List[str]:
    """Resolves a hostname to all associated IP addresses (both IPv4 and IPv6)."""
    try:
        addr_info = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
        ips = []
        for item in addr_info:
            sockaddr = item[4]
            ip_str = sockaddr[0]
            if ip_str not in ips:
                ips.append(ip_str)
        return ips
    except socket.gaierror as e:
        raise SSRFValidationError(f"DNS resolution failed for hostname '{hostname}': {e}")


def validate_public_url(
    url: str,
    require_https: bool = True,
    allowed_schemes: Tuple[str, ...] = ("https",)
) -> urllib.parse.ParseResult:
    """
    Validates that a URL:
    1. Uses an approved scheme (HTTPS required by default).
    2. Has a valid non-empty hostname.
    3. Resolves strictly to public, non-private, non-metadata IP addresses.
    """
    if not url or not isinstance(url, str):
        raise SSRFValidationError("URL must be a non-empty string.")

    url = url.strip()
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception as e:
        raise SSRFValidationError(f"Malformed URL structure: {e}")

    scheme = parsed.scheme.lower()
    if scheme not in allowed_schemes:
        if require_https and scheme == "http":
            is_prod = os.getenv("ENVIRONMENT", "development").lower() == "production"
            if is_prod:
                raise SSRFValidationError("HTTP is not permitted in production; HTTPS is required.")
        else:
            raise SSRFValidationError(f"Disallowed URL scheme '{parsed.scheme}'. Allowed: {allowed_schemes}")

    hostname = parsed.hostname
    if not hostname:
        raise SSRFValidationError("URL is missing a valid hostname.")

    # Block direct IP literals in hostname if they are blocked
    try:
        ip = ipaddress.ip_address(hostname)
        if is_ip_blocked(str(ip)):
            raise SSRFValidationError(f"Direct IP target '{hostname}' is in a blocked network range.")
    except ValueError:
        pass  # Hostname is a domain name, proceed to DNS resolution

    # Resolve all DNS records
    port = parsed.port or (443 if scheme == "https" else 80)
    resolved_ips = resolve_hostname_ips(hostname, port)
    if not resolved_ips:
        raise SSRFValidationError(f"No IP addresses resolved for hostname '{hostname}'.")

    for ip_str in resolved_ips:
        if is_ip_blocked(ip_str):
            raise SSRFValidationError(f"Hostname '{hostname}' resolves to blocked IP address '{ip_str}'.")

    return parsed


def detect_anchored_platform(url: str) -> Optional[str]:
    """
    Detects supported video platform using strictly anchored domain validation.
    Prevents bypasses where platform domain is placed in query params or paths.
    """
    try:
        parsed = urllib.parse.urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return None
        
        for platform, pattern in ANCHORED_PLATFORM_PATTERNS.items():
            if pattern.match(hostname):
                return platform
        return None
    except Exception:
        return None


def safe_download_stream(
    url: str,
    destination_path: str,
    max_bytes: int = 100 * 1024 * 1024,  # 100 MB default
    allowed_content_types: Optional[List[str]] = None,
    timeout_seconds: int = 30,
    max_redirects: int = 5
) -> int:
    """
    Downloads a remote file with strict security guards:
    - Validates initial URL for SSRF
    - Manually tracks and re-validates each redirect hop before following
    - Limits max redirects
    - Enforces maximum byte size during streaming
    - Validates Content-Type header if specified
    - Writes to destination_path only if all checks pass
    Returns: total bytes written.
    """
    current_url = url
    session = requests.Session()
    session.headers.update({
        "User-Agent": "CloneFrame-SafeMediaFetcher/2.0"
    })

    redirect_count = 0
    while redirect_count <= max_redirects:
        # Validate current hop
        validate_public_url(current_url)

        # Request with allow_redirects=False to inspect each hop
        response = session.get(
            current_url,
            stream=True,
            timeout=timeout_seconds,
            allow_redirects=False
        )

        # Handle redirects manually
        if response.is_redirect or response.status_code in (301, 302, 303, 307, 308):
            redirect_count += 1
            if redirect_count > max_redirects:
                raise SSRFValidationError(f"Too many redirects (exceeded limit of {max_redirects}).")
            
            location = response.headers.get("Location")
            if not location:
                raise SSRFValidationError("Redirect response missing Location header.")
            
            # Resolve relative redirects
            current_url = urllib.parse.urljoin(current_url, location)
            continue

        response.raise_for_status()

        # Validate Content-Type if specified
        if allowed_content_types:
            content_type = response.headers.get("Content-Type", "").lower().split(";")[0].strip()
            if not any(content_type == allowed.lower() or content_type.startswith(allowed.lower()) for allowed in allowed_content_types):
                raise SSRFValidationError(f"Untrusted Content-Type '{content_type}'. Expected one of: {allowed_content_types}")

        # Check declared Content-Length
        content_length = response.headers.get("Content-Length")
        if content_length:
            try:
                if int(content_length) > max_bytes:
                    raise SSRFValidationError(f"File size {int(content_length)} bytes exceeds maximum permitted {max_bytes} bytes.")
            except ValueError:
                pass

        # Stream into temporary destination file with byte counting
        bytes_written = 0
        with open(destination_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=65536):
                if chunk:
                    bytes_written += len(chunk)
                    if bytes_written > max_bytes:
                        raise SSRFValidationError(f"Download stream exceeded maximum permitted size of {max_bytes} bytes.")
                    f.write(chunk)

        return bytes_written

    raise SSRFValidationError("Exceeded maximum redirect limit.")
