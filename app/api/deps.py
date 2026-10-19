"""Общие зависимости FastAPI: авторизация, RBAC, текущий пользователь.

Покрытие OWASP Top 10 2021:

- **A01 Broken Access Control** — :func:`require_roles` декларативно ограничивает
  доступ к эндпоинтам по ролям; объектный уровень контролируется владением ресурса.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User, UserRole

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db)]


def _credentials_error(detail: str = "Could not validate credentials") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    """Извлекает пользователя из access-токена Authorization: Bearer."""
    if credentials is None:
        raise _credentials_error("Not authenticated")

    try:
        claims = decode_token(credentials.credentials)
    except (jwt.InvalidTokenError, ValueError) as exc:
        raise _credentials_error() from exc

    if claims.get("type") != "access":
        raise _credentials_error("Not an access token")

    try:
        user_id = uuid.UUID(claims["sub"])
    except (KeyError, ValueError) as exc:
        raise _credentials_error() from exc

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise _credentials_error("User not found or inactive")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole) -> Callable[..., Awaitable[User]]:
    """Возвращает зависимость, допускающую только перечисленные роли."""

    async def _require_roles(user: CurrentUser) -> User:
        if UserRole(user.role) not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return _require_roles


def has_role(user: User, *roles: UserRole) -> bool:
    """Удобная проверка роли без поднятия HTTP-исключения."""
    return UserRole(user.role) in roles
