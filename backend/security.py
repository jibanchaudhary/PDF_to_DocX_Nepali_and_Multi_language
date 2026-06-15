"""Deployment-time security controls for the PDFlow API.

Everything here is *opt-in via environment variables* so local development keeps
working with zero configuration. Before exposing the service publicly (where a
GPU is doing the OCR) set at least:

    PDFLOW_API_KEYS          comma-separated keys that may start conversions
    PDFLOW_MAX_PER_HOUR      jobs accepted per identity per rolling hour
    PDFLOW_MAX_CONCURRENT    in-flight jobs per identity

An "identity" is the presented API key (when configured) otherwise the client
IP. The IP fallback means the rate limiter still bounds abuse of the public web
UI, which cannot carry a secret key. Reads of a job are authorised by possession
of its high-entropy job id (a capability URL), so the browser's EventSource /
``<img>`` requests work without custom headers.

NOTE: behind a reverse proxy, ``request.client.host`` is the proxy. To rate-limit
by real client IP, terminate at a trusted proxy and run uvicorn with
``--forwarded-allow-ips`` (ProxyHeadersMiddleware). We deliberately do NOT trust
``X-Forwarded-For`` here because clients can forge it.
"""

from __future__ import annotations

import os
import time
import hashlib
import secrets
import threading
from collections import deque
from typing import Deque, Dict, List, Optional

from fastapi import Header, HTTPException, Request


# --------------------------------------------------------------------------- #
# Env helpers / configuration
# --------------------------------------------------------------------------- #
def _csv_env(name: str) -> List[str]:
    return [p.strip() for p in os.environ.get(name, "").split(",") if p.strip()]


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


# Auth: when empty, authentication is DISABLED (development default).
API_KEYS = set(_csv_env("PDFLOW_API_KEYS"))

# Per-identity limits.
MAX_PER_HOUR = _int_env("PDFLOW_MAX_PER_HOUR", 30)
MAX_CONCURRENT = _int_env("PDFLOW_MAX_CONCURRENT", 2)

# Upload / resource caps (consumed by the API and the conversion worker).
MAX_UPLOAD_BYTES = _int_env("PDFLOW_MAX_UPLOAD_MB", 50) * 1024 * 1024
MAX_PAGES = _int_env("PDFLOW_MAX_PAGES", 300)
MAX_OCR_MP = _int_env("PDFLOW_MAX_OCR_MP", 200)         # per-page megapixels at OCR zoom
MAX_PREVIEW_MP = _int_env("PDFLOW_MAX_PREVIEW_MP", 16)  # previews downscale above this
JOB_TIMEOUT_SEC = _int_env("PDFLOW_JOB_TIMEOUT_SEC", 600)
JOB_TTL_SEC = _int_env("PDFLOW_JOB_TTL_SEC", 3600)

# CORS: comma-separated allowed origins; default "*" (lock down for production).
ALLOW_ORIGINS = _csv_env("PDFLOW_ALLOW_ORIGINS") or ["*"]


# --------------------------------------------------------------------------- #
# Rate limiter (in-process — matches the single-worker registry design)
# --------------------------------------------------------------------------- #
class RateLimiter:
    """Per-identity rolling-hour quota + concurrent-job cap.

    The quota is charged when a job is *accepted*; the concurrency slot is held
    for the lifetime of the job (acquired before submit, released when the worker
    finishes) so the heavy GPU path can never be over-subscribed by one client.
    """

    def __init__(self, max_per_hour: int, max_concurrent: int) -> None:
        self._max_per_hour = max_per_hour
        self._max_concurrent = max_concurrent
        self._lock = threading.Lock()
        self._history: Dict[str, Deque[float]] = {}
        self._active: Dict[str, int] = {}

    def check_quota(self, identity: str) -> None:
        if not self._max_per_hour:
            return
        now = time.time()
        with self._lock:
            hist = self._history.setdefault(identity, deque())
            cutoff = now - 3600
            while hist and hist[0] < cutoff:
                hist.popleft()
            if len(hist) >= self._max_per_hour:
                raise HTTPException(
                    status_code=429,
                    detail="Hourly conversion limit reached. Try again later.",
                    headers={"Retry-After": "3600"},
                )
            hist.append(now)

    def acquire_slot(self, identity: str) -> None:
        if not self._max_concurrent:
            return
        with self._lock:
            active = self._active.get(identity, 0)
            if active >= self._max_concurrent:
                raise HTTPException(
                    status_code=429,
                    detail="Too many conversions in progress. Wait for one to finish.",
                    headers={"Retry-After": "30"},
                )
            self._active[identity] = active + 1

    def release_slot(self, identity: str) -> None:
        with self._lock:
            n = self._active.get(identity, 0)
            if n <= 1:
                self._active.pop(identity, None)
            else:
                self._active[identity] = n - 1


rate_limiter = RateLimiter(MAX_PER_HOUR, MAX_CONCURRENT)


# --------------------------------------------------------------------------- #
# API-key auth (gates the expensive POST /api/convert only)
# --------------------------------------------------------------------------- #
def _verify_key(x_api_key: Optional[str], authorization: Optional[str]) -> Optional[str]:
    presented = x_api_key
    if not presented and authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer":
            presented = token.strip()
    if not API_KEYS:
        return presented  # auth disabled (dev)
    if presented:
        for key in API_KEYS:
            if secrets.compare_digest(presented, key):
                return presented
    raise HTTPException(status_code=401, detail="A valid API key is required.",
                        headers={"WWW-Authenticate": "ApiKey"})


def _identity(request: Request, key: Optional[str]) -> str:
    if key:
        # Hash so raw keys never land in dicts or logs.
        return "key:" + hashlib.sha256(key.encode()).hexdigest()[:16]
    host = request.client.host if request.client else "unknown"
    return "ip:" + host


async def auth_identity(
    request: Request,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    authorization: Optional[str] = Header(default=None),
) -> str:
    """FastAPI dependency: enforce auth (if configured) + the hourly quota.

    Returns a stable identity string used to scope the concurrency slot.
    """
    key = _verify_key(x_api_key, authorization)
    identity = _identity(request, key)
    rate_limiter.check_quota(identity)
    return identity
