"""
Instance-Local Rate Limiter Module
Provides in-memory sliding window rate limiting for FastAPI endpoints.
Note: This is an instance-local protective layer designed to prevent abuse,
brute force, and rapid request spam on single Cloud Run container instances.
Distributed quota enforcement is authoritatively handled by Firestore
active-job concurrency tracking and server-side credit validation.
"""
import time
from collections import defaultdict
from typing import Dict, List, Optional
from fastapi import Request, HTTPException, status


class InMemoryRateLimiter:
    def __init__(self):
        # Key: (endpoint_tag, identifier), Value: List of timestamps (seconds)
        self._requests: Dict[str, List[float]] = defaultdict(list)

    def check_rate_limit(
        self,
        identifier: str,
        endpoint_tag: str,
        max_requests: int,
        window_seconds: int
    ) -> bool:
        """
        Checks if the request exceeds max_requests within window_seconds.
        Cleans up expired timestamps in the sliding window.
        Returns: True if allowed, False if rate limited.
        """
        now = time.time()
        key = f"{endpoint_tag}:{identifier}"
        timestamps = self._requests[key]

        # Evict timestamps outside the sliding window
        cutoff = now - window_seconds
        while timestamps and timestamps[0] < cutoff:
            timestamps.pop(0)

        if len(timestamps) >= max_requests:
            return False

        timestamps.append(now)
        return True

    def get_retry_after(
        self,
        identifier: str,
        endpoint_tag: str,
        window_seconds: int
    ) -> int:
        """Returns estimated seconds until the oldest request in the window expires."""
        now = time.time()
        key = f"{endpoint_tag}:{identifier}"
        timestamps = self._requests.get(key, [])
        if not timestamps:
            return 1
        oldest = timestamps[0]
        retry_after = int(window_seconds - (now - oldest)) + 1
        return max(1, retry_after)


# Global instance-local rate limiter
limiter = InMemoryRateLimiter()


def rate_limit(max_requests: int = 15, window_seconds: int = 60, endpoint_tag: Optional[str] = None):
    """
    FastAPI dependency factory for instance-local sliding window rate limiting.
    Identifies clients by authenticated user_id if present in request.state or client IP.
    """
    async def dependency(request: Request):
        # Extract user_id from authorization or client IP
        auth_header = request.headers.get("Authorization", "")
        identifier = "anonymous"
        if auth_header.startswith("Bearer "):
            # Use hash of token or token snippet as identifier to avoid overhead
            identifier = auth_header[-16:]
        elif request.client and request.client.host:
            identifier = request.client.host

        tag = endpoint_tag or request.url.path

        is_allowed = limiter.check_rate_limit(
            identifier=identifier,
            endpoint_tag=tag,
            max_requests=max_requests,
            window_seconds=window_seconds
        )

        if not is_allowed:
            retry_after = limiter.get_retry_after(identifier, tag, window_seconds)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds}s. Please retry in {retry_after}s.",
                headers={"Retry-After": str(retry_after)}
            )
        return True

    return dependency
