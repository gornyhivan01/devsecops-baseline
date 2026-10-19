"""Pydantic-схемы запросов/ответов."""

from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.common import Message
from app.schemas.item import ItemCreate, ItemRead, ItemUpdate
from app.schemas.user import UserRead, UserUpdate

__all__ = [
    "AccessTokenResponse",
    "ItemCreate",
    "ItemRead",
    "ItemUpdate",
    "LoginRequest",
    "Message",
    "RefreshRequest",
    "RegisterRequest",
    "TokenResponse",
    "UserRead",
    "UserUpdate",
]
