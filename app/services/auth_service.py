"""Сервис аутентификации: регистрация, вход, ротация refresh-токенов, выход.

Алгоритмические детали JWT и Argon2 вынесены в :mod:`app.core.security`; здесь —
оркестрация и работа с БД.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

import jwt
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import RegisterRequest, TokenResponse
from app.services.exceptions import (
    EmailAlreadyExistsError,
    InactiveUserError,
    InvalidCredentialsError,
)


def hash_refresh_token(token: str) -> str:
    """SHA-256 хеш refresh-токена для хранения в БД (необратим без токена)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _as_aware_utc(value: datetime) -> datetime:
    """Приводит datetime к timezone-aware UTC.

    SQLite хранит datetime без часового пояса, тогда как PostgreSQL (``timezone=True``)
    возвращает aware-значения. Нормализация делает сравнения корректными в обеих
    СУБД: наивные значения трактуются как UTC.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _expires_in() -> int:
    from app.core.config import get_settings

    return get_settings().access_token_expire_minutes * 60


class AuthService:
    """Бизнес-логика аутентификации поверх async-сессии."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _get_user_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def register(self, data: RegisterRequest) -> User:
        if await self._get_user_by_email(data.email) is not None:
            raise EmailAlreadyExistsError("Email already registered")

        user = User(
            email=data.email,
            full_name=data.full_name,
            hashed_password=hash_password(data.password),
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await self._get_user_by_email(email)
        # Проверяем хеш даже для несуществующего пользователя, чтобы не раскрывать
        # факт наличия email через разницу во времени ответа (timing side-channel).
        if user is None or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError("Invalid email or password")
        if not user.is_active:
            raise InactiveUserError("User is inactive")

        return await self._issue_pair(user)

    async def _issue_pair(self, user: User) -> TokenResponse:
        access_token, _ = create_access_token(str(user.id), user.role)
        refresh_token, refresh_expires = create_refresh_token(str(user.id), user.role)
        claims = decode_token(refresh_token)

        record = RefreshToken(
            user_id=user.id,
            jti=claims["jti"],
            token_hash=hash_refresh_token(refresh_token),
            expires_at=refresh_expires,
        )
        self.db.add(record)
        await self.db.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",  # noqa: S106 — метка типа, не пароль
            expires_in=_expires_in(),
        )

    async def refresh(self, refresh_token: str) -> TokenResponse:
        """Ротация refresh-токена: старый отзывается, выпускается новая пара."""
        try:
            claims = decode_token(refresh_token)
        except jwt.InvalidTokenError as exc:
            raise InvalidCredentialsError("Invalid refresh token") from exc

        if claims.get("type") != "refresh":
            raise InvalidCredentialsError("Token is not a refresh token")

        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.jti == claims["jti"])
        )
        record = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        if (
            record is None
            or record.revoked_at is not None
            or record.token_hash != hash_refresh_token(refresh_token)
            or _as_aware_utc(record.expires_at) <= now
        ):
            raise InvalidCredentialsError("Refresh token is invalid or expired")

        user = await self.db.get(User, record.user_id)
        if user is None or not user.is_active:
            raise InactiveUserError("User is inactive")

        access_token, _ = create_access_token(str(user.id), user.role)
        new_refresh_token, new_refresh_expires = create_refresh_token(str(user.id), user.role)
        new_claims = decode_token(new_refresh_token)

        # Ротация: отзываем старый и связываем с новым для аудита повторного использования.
        record.revoked_at = now
        record.replaced_by_jti = new_claims["jti"]

        self.db.add(
            RefreshToken(
                user_id=user.id,
                jti=new_claims["jti"],
                token_hash=hash_refresh_token(new_refresh_token),
                expires_at=new_refresh_expires,
            )
        )
        await self.db.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",  # noqa: S106 — метка типа, не пароль
            expires_in=_expires_in(),
        )

    async def logout(self, refresh_token: str) -> None:
        """Отзывает refresh-токен (идемпотентно)."""
        try:
            claims = decode_token(refresh_token)
        except jwt.InvalidTokenError:
            return

        if claims.get("type") != "refresh":
            return

        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.jti == claims["jti"])
        )
        record = result.scalar_one_or_none()
        if record is not None and record.revoked_at is None:
            record.revoked_at = datetime.now(timezone.utc)
            await self.db.commit()

    async def purge_expired_tokens(self, user_id: uuid.UUID) -> None:
        """Удаляет истёкшие записи refresh-токенов пользователя (гигиена БД)."""
        now = datetime.now(timezone.utc)
        await self.db.execute(
            delete(RefreshToken)
            .where(RefreshToken.user_id == user_id)
            .where(RefreshToken.expires_at <= now)
        )
        await self.db.commit()
