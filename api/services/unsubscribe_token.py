"""HMAC-SHA256 unsubscribe tokens for the §5.14 weekly opportunity email.

The token format is base64url(HMAC-SHA256(secret, subscription_id + ":" + email))
where `secret` is the EMAIL_UNSUBSCRIBE_SECRET env var. Tokens are stable
across weeks — minting the same (subscription_id, email) pair always
returns the same token. The unsubscribe link binds both fields via the
HMAC, so raw subscription IDs and emails never appear in the URL alone.

Verification is constant-time. A wrong token, a tampered subscription_id,
or a tampered email all return False.

This module reads the secret lazily so callers don't have to inject it.
The secret comes from `api.config.settings.email_unsubscribe_secret`. The
production guard in `api/config.py` refuses to start with EMAIL_DRY_RUN=false
when the secret is empty, so any code path that actually emits links has
a real secret in hand.
"""
from __future__ import annotations

import base64
import hashlib
import hmac

from api.config import settings


class UnsubscribeSecretMissingError(RuntimeError):
    """Raised when mint/verify is called without EMAIL_UNSUBSCRIBE_SECRET set.

    Code paths that mint tokens for outbound mail must run only with a real
    secret in place. This exception is the safety net behind the config-time
    `model_validator` — it's the second line of defense if a unit test or
    dev shell tries to mint a token before the env is loaded.
    """


def _secret_bytes() -> bytes:
    secret = settings.email_unsubscribe_secret
    if not secret:
        raise UnsubscribeSecretMissingError(
            "EMAIL_UNSUBSCRIBE_SECRET is empty. Generate one with "
            "`openssl rand -hex 32` and set it in .env or the VX1 env file."
        )
    return secret.encode("utf-8")


def _payload(subscription_id: str, email: str) -> bytes:
    return f"{subscription_id}:{email}".encode("utf-8")


def mint(subscription_id: str, email: str) -> str:
    """Return a stable HMAC-SHA256 token for this subscription/email pair.

    Same inputs always produce the same token — minting is deterministic.
    """
    digest = hmac.new(_secret_bytes(), _payload(subscription_id, email), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def verify(token: str, subscription_id: str, email: str) -> bool:
    """Return True iff `token` matches mint(subscription_id, email).

    Uses `hmac.compare_digest` for constant-time comparison so timing
    attacks can't leak per-byte hits. Returns False on any tampering
    (wrong token, wrong subscription_id, wrong email, malformed input).
    """
    if not token or not subscription_id or not email:
        return False
    try:
        expected = mint(subscription_id, email)
    except UnsubscribeSecretMissingError:
        # Same surface as a wrong token — no information leak about
        # whether the secret is configured.
        return False
    return hmac.compare_digest(token.encode("ascii"), expected.encode("ascii"))
