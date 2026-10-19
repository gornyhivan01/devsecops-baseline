"""Безопасность: хеширование паролей (Argon2id) и JWT.

Покрытие OWASP Top 10 2021:

- **A02 Cryptographic Failures** — пароли хешируются Argon2id (memory-hard KDF),
  никогда не хранятся в открытом виде и не попадают в логи.
- **A07 Identification and Authentication Failures** — JWT с коротким временем
  жизни, обязательными claims ``iss``/``aud``/``jti`` и проверкой типа токена.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import get_settings

VALID_ALGORITHMS = {"HS256", "HS384", "HS512", "RS256", "RS384", "RS512", "ES256", "ES384", "ES512"}


def _password_hasher() -> PasswordHasher:
    settings = get_settings()
    return PasswordHasher(
        time_cost=settings.argon2_time_cost,
        memory_cost=settings.argon2_memory_cost,
        parallelism=settings.argon2_parallelism,
    )


def hash_password(password: str) -> str:
    """Хеширует пароль Argon2id и возвращает PHC-строку."""
    return _password_hasher().hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Проверяет пароль против Argon2id-хеша (безопасно против timing-атак)."""
    try:
        return _password_hasher().verify(hashed, password)
    except (VerificationError, InvalidHashError):
        return False


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _build_claims(
    subject: str,
    token_type: str,
    role: str,
    expires_in: timedelta,
    extra: dict[str, Any] | None = None,
) -> tuple[str, datetime]:
    settings = get_settings()
    now = _now_utc()
    expires = now + expires_in
    claims: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "type": token_type,
        "jti": str(uuid.uuid4()),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(expires.timestamp()),
    }
    if extra:
        claims.update(extra)
    token = jwt.encode(claims, settings.secret_key, algorithm=settings.jwt_algorithm)
    return token, expires


def create_access_token(subject: str, role: str) -> tuple[str, datetime]:
    """Выпускает короткоживущий access-токен."""
    settings = get_settings()
    return _build_claims(
        subject,
        token_type="access",  # noqa: S106 — литерал-метка типа токена, не пароль
        role=role,
        expires_in=timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(subject: str, role: str) -> tuple[str, datetime]:
    """Выпускает долгоживущий refresh-токен (хранится в БД и ротируется)."""
    settings = get_settings()
    return _build_claims(
        subject,
        token_type="refresh",  # noqa: S106 — литерал-метка типа токена, не пароль
        role=role,
        expires_in=timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str) -> dict[str, Any]:
    """Декодирует и проверяет JWT.

    Проверяются подпись, алгоритм (allowlist), срок действия и claims
    ``iss``/``aud``. Возвращает словарь claims или выбрасывает ``jwt.InvalidTokenError``.
    """
    settings = get_settings()
    if settings.jwt_algorithm not in VALID_ALGORITHMS:
        raise ValueError(f"Unsupported JWT algorithm: {settings.jwt_algorithm}")
    decoded: dict[str, Any] = jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )
    return decoded
