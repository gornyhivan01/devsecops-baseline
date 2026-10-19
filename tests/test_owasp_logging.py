"""OWASP A09: Security Logging and Monitoring Failures — ред-акция секретов."""

from __future__ import annotations

from app.core.logging import REDACTED, redact


def test_redact_password_and_token_fields() -> None:
    event = {"event": "login", "password": "hunter2", "user": "bob", "token": "abc123"}
    result = redact(None, None, dict(event))
    assert result["password"] == REDACTED
    assert result["token"] == REDACTED
    assert result["user"] == "bob"


def test_redact_authorization_and_refresh_token() -> None:
    event = {
        "authorization": "Bearer eyJ...",
        "refresh_token": "refresh-123",
        "path": "/api/v1/auth/login",
    }
    result = redact(None, None, dict(event))
    assert result["authorization"] == REDACTED
    assert result["refresh_token"] == REDACTED
    assert result["path"] == "/api/v1/auth/login"


def test_redact_does_not_touch_benign_fields() -> None:
    event = {"user_id": "0000", "duration_ms": 42}
    result = redact(None, None, dict(event))
    assert result == event
