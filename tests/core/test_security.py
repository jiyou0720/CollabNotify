"""Tests for webhook authentication helpers."""

import hashlib
import hmac

from app.core.security import validate_github_signature, validate_shared_secret


def test_github_signature_validation() -> None:
    """GitHub signatures must validate against the exact raw body."""
    body = b'{"event":"value"}'
    digest = hmac.new(b"secret", body, hashlib.sha256).hexdigest()

    assert validate_github_signature(body, f"sha256={digest}", "secret") is True
    assert validate_github_signature(body + b" ", f"sha256={digest}", "secret") is False
    assert validate_github_signature(body, digest, "secret") is False


def test_shared_secret_validation() -> None:
    """Shared-secret validation must reject empty and mismatched values."""
    assert validate_shared_secret("secret", "secret") is True
    assert validate_shared_secret("different", "secret") is False
    assert validate_shared_secret("", "secret") is False
