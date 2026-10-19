"""OWASP A02: Cryptographic Failures — Argon2id и проверка целостности JWT."""

from __future__ import annotations

import jwt as pyjwt
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, decode_token, hash_password, verify_password
from tests.utils import seed_user

USER_ID = "00000000-0000-0000-0000-000000000001"


def test_password_hashed_with_argon2id() -> None:
    hashed = hash_password("SuperSecret123!")
    assert hashed.startswith("$argon2id$")
    assert verify_password("SuperSecret123!", hashed) is True
    assert verify_password("wrong-password", hashed) is False


async def test_password_never_stored_in_plaintext(db: AsyncSession) -> None:
    user = await seed_user(db, password="ActualPass123!")
    assert user.hashed_password != "ActualPass123!"
    assert "ActualPass123!" not in user.hashed_password


async def test_tampered_token_is_rejected() -> None:
    token, _ = create_access_token(USER_ID, "user")
    header, payload, signature = token.split(".")
    # Портим первый символ подписи: в base64url его биты всегда значимы, поэтому
    # байты подписи гарантированно изменятся. Подмена последнего символа
    # ненадёжна — его младшие биты являются padding-битами и могут не влиять
    # на декодированные байты (такой тест был флейки).
    tampered_char = "A" if signature[0] != "A" else "B"
    tampered = f"{header}.{payload}.{tampered_char}{signature[1:]}"
    with pytest.raises(pyjwt.InvalidTokenError):
        decode_token(tampered)


async def test_token_claims_include_issuer_audience() -> None:
    from app.core.config import get_settings

    settings = get_settings()
    token, _ = create_access_token(USER_ID, "user")
    claims = decode_token(token)
    assert claims["iss"] == settings.jwt_issuer
    assert claims["aud"] == settings.jwt_audience
    assert claims["type"] == "access"
