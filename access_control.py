"""Signed, HttpOnly owner sessions for user files and search tasks.

No client-supplied user_hash or task_id is itself proof of ownership.
Configure KO_SESSION_SECRET in cloud deployments. All application replicas must
share that secret; otherwise cookies are invalid across replicas/restarts.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time

from fastapi import HTTPException, Request
from starlette.responses import Response

LOG = logging.getLogger("AcademicAPI")
COOKIE_NAME = "ko_owner_session"
MAX_AGE = 48 * 60 * 60
raw_secret = os.environ.get("KO_SESSION_SECRET", "").strip()
_SECRET = raw_secret.encode("utf-8") if raw_secret else secrets.token_bytes(32)
if not raw_secret:
    LOG.warning("KO_SESSION_SECRET is missing: using an ephemeral session key. Configure a persistent secret for production.")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def issue_session(response: Response, owner: str, secure: bool) -> None:
    if not owner or len(owner) > 128 or any(c in owner for c in "/\\."):
        raise ValueError("Invalid owner")
    payload = _b64(json.dumps(
        {"owner": owner, "expires": int(time.time()) + MAX_AGE, "nonce": secrets.token_hex(8)},
        separators=(",", ":"), sort_keys=True
    ).encode("utf-8"))
    signature = _b64(hmac.new(_SECRET, payload.encode("ascii"), hashlib.sha256).digest())
    response.set_cookie(
        COOKIE_NAME, payload + "." + signature,
        max_age=MAX_AGE, httponly=True, secure=secure, samesite="lax", path="/"
    )


def revoke_session(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


def session_owner(request: Request) -> str | None:
    raw = request.cookies.get(COOKIE_NAME, "")
    if len(raw) > 1024 or raw.count(".") != 1:
        return None
    payload, signature = raw.split(".", 1)
    try:
        expected = _b64(hmac.new(_SECRET, payload.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(signature.encode("ascii"), expected.encode("ascii")):
            return None
        decoded = json.loads(_decode(payload))
        if not isinstance(decoded, dict) or decoded.get("expires", 0) <= time.time():
            return None
        owner = decoded.get("owner")
        if not isinstance(owner, str) or not owner or len(owner) > 128 or any(c in owner for c in "/\\."):
            return None
        return owner
    except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def require_owner(request: Request, expected: str, local: bool = False) -> str:
    if local and expected == "local_user":
        return expected
    actual = session_owner(request)
    if not actual or not hmac.compare_digest(actual, expected):
        raise HTTPException(status_code=403, detail="Access denied: not the owner of this resource")
    return actual


def require_same_origin(request: Request) -> None:
    """Reject clearly cross-origin state mutations (defense in depth with SameSite)."""
    origin = request.headers.get("origin", "")
    if origin:
        from urllib.parse import urlsplit
        host = request.headers.get("host", "")
        parsed = urlsplit(origin)
        if parsed.netloc.lower() != host.lower() or parsed.scheme not in ("http", "https"):
            raise HTTPException(status_code=403, detail="Cross-origin mutation denied")
