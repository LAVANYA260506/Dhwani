"""
Session token helpers.

There are no accounts. When an application is created, a random token is
returned to the browser once. The database stores only a keyed hash of it
(HMAC-SHA256 with SECRET_KEY), so a leaked database cannot be used to resume
someone's application. Changing SECRET_KEY invalidates all existing sessions.
"""

import hashlib
import hmac
import secrets

from app.config import settings


def generate_session_token() -> tuple[str, str]:
    """Return (raw_token, token_hash). Send the raw token to the client once;
    store only the hash."""
    raw_token = secrets.token_urlsafe(32)
    return raw_token, hash_token(raw_token)


def hash_token(raw_token: str) -> str:
    """Keyed hash of a token, as a 64-character hex string."""
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        raw_token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def tokens_match(raw_token: str, stored_hash: str) -> bool:
    """Constant-time check of a presented token against the stored hash."""
    return hmac.compare_digest(hash_token(raw_token), stored_hash)


def parse_bearer_token(authorization_header: str | None) -> str | None:
    """Extract the token from an 'Authorization: Bearer <token>' header."""
    if not authorization_header:
        return None
    scheme, _, token = authorization_header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()