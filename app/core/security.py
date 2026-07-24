"""Webhook authentication helpers."""

import hashlib
import hmac


def validate_github_signature(body: bytes, signature: str, secret: str) -> bool:
    """Validate a GitHub HMAC SHA-256 webhook signature."""
    if not signature.startswith("sha256="):
        return False

    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    expected = f"sha256={digest}"
    return hmac.compare_digest(expected, signature)


def validate_shared_secret(provided: str, expected: str) -> bool:
    """Compare a shared webhook secret using constant-time semantics."""
    if not provided:
        return False
    return hmac.compare_digest(provided, expected)
