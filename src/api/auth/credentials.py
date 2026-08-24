"""Credential primitives — PBKDF2 password hashing + HS256 JWT tokens.

Stdlib-only (hashlib/hmac/base64) so no new dependencies are needed.

JWT shape: base64url(header).base64url(payload).base64url(HMAC-SHA256 sig)
Payload: {sub, email, role, typ, iat, exp}

Token signing key comes from `DAP_JWT_SECRET`; without it a dev-only
fallback key is used (fine for local preview, must be set in production).
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import time

JWT_SECRET_ENV = "DAP_JWT_SECRET"
_DEV_SECRET = b"dap-dev-insecure-secret-0824"
PBKDF2_ITERATIONS = 600_000
ACCESS_TTL_SECONDS = 900      # 15 min
REFRESH_TTL_SECONDS = 604800  # 7 days


def get_jwt_secret() -> bytes:
    """Signing key from the environment, or the dev fallback when unset."""
    secret = os.environ.get(JWT_SECRET_ENV, "").strip()
    return secret.encode() if secret else _DEV_SECRET


def _b64url_encode(data: bytes) -> bytes:
    return base64.urlsafe_b64encode(data).rstrip(b"=")


def _b64url_decode(data: bytes) -> bytes:
    pad = b"=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def create_token(user_id: str, email: str, role: str, typ: str, ttl: int) -> str:
    """Sign a compact JWT. typ is 'access' or 'refresh'."""
    now = int(time.time())
    header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64url_encode(json.dumps({
        "sub": user_id, "email": email, "role": role, "typ": typ,
        "iat": now, "exp": now + ttl,
    }).encode())
    signing_input = header + b"." + payload
    sig = hmac.new(get_jwt_secret(), signing_input, hashlib.sha256).digest()
    return (signing_input + b"." + _b64url_encode(sig)).decode()


def decode_token(token: str, typ: str | None = None) -> dict | None:
    """Verify signature + expiry. Returns the payload dict, or None."""
    parts = token.split(".")
    if len(parts) != 3:
        return None
    signing_input = (parts[0] + "." + parts[1]).encode()
    expected = hmac.new(get_jwt_secret(), signing_input, hashlib.sha256).digest()
    try:
        if not hmac.compare_digest(expected, _b64url_decode(parts[2].encode())):
            return None
        payload = json.loads(_b64url_decode(parts[1].encode()))
    except (ValueError, json.JSONDecodeError):
        return None
    if payload.get("exp", 0) < int(time.time()):
        return None
    if typ is not None and payload.get("typ") != typ:
        return None
    return payload


def create_token_pair(user_id: str, email: str, role: str) -> tuple[str, str]:
    """(access_token, refresh_token) pair for a verified user."""
    access = create_token(user_id, email, role, "access", ACCESS_TTL_SECONDS)
    refresh = create_token(user_id, email, role, "refresh", REFRESH_TTL_SECONDS)
    return access, refresh


# ─── Password hashing (PBKDF2-HMAC-SHA256, stdlib) ───────────────

def hash_password(password: str) -> str:
    """Salted PBKDF2 hash, encoded 'pbkdf2_sha256$<iters>$<salt>$<hash>'."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Constant-time verify of a stored PBKDF2 hash."""
    try:
        _, iters, salt, expected_hex = stored.split("$")
        iters = int(iters)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iters)
    return hmac.compare_digest(digest.hex(), expected_hex)
