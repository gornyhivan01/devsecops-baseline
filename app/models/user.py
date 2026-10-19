"""Модель пользователя с ролью для RBAC."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.item import Item
    from app.models.refresh_token import RefreshToken


class UserRole(str, enum.Enum):
    """Роли, используемые для RBAC (A01: Broken Access Control)."""

    ADMIN = "admin"
    USER = "user"
    AUDITOR = "auditor"


class User(Base):
    """Пользователь сервиса.

    Роль хранится строкой в БД (портируемо между PostgreSQL и SQLite) и
    валидируется enum'ом на уровне приложения.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default=UserRole.USER.value)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    refresh_tokens: Mapped[list[RefreshToken]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    items: Mapped[list[Item]] = relationship(  # noqa: F821
        back_populates="owner", cascade="all, delete-orphan"
    )
