"""Схемы пользователей и RBAC.

Примеры полей и тел запросов заданы для отображения в Swagger UI.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole

_EXAMPLE_USER_ID = "00000000-0000-0000-0000-000000000001"
_EXAMPLE_EMAIL = "user@example.com"


class UserRead(BaseModel):
    """Представление пользователя в ответах."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": _EXAMPLE_USER_ID,
                    "email": _EXAMPLE_EMAIL,
                    "full_name": "Иван Иванов",
                    "role": "user",
                    "is_active": True,
                    "created_at": "2026-01-01T12:00:00Z",
                }
            ]
        },
    )

    id: uuid.UUID = Field(description="Идентификатор пользователя", examples=[_EXAMPLE_USER_ID])
    email: EmailStr = Field(description="Электронная почта", examples=[_EXAMPLE_EMAIL])
    full_name: str = Field(description="Полное имя", examples=["Иван Иванов"])
    role: UserRole = Field(description="Роль (RBAC)", examples=["user"])
    is_active: bool = Field(description="Активен ли пользователь", examples=[True])
    created_at: datetime = Field(description="Создано (UTC)")


class UserUpdate(BaseModel):
    """Тело запроса обновления пользователя.

    Через ``PATCH /users/me`` роль изменить нельзя — эндпоинт обновляет только
    ``full_name``. Смена роли и активности доступна администратору через
    ``PATCH /users/{user_id}``.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {"full_name": "Иван Петров"},
                {"role": "auditor", "is_active": True},
            ]
        },
    )

    full_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Полное имя",
        examples=["Иван Петров"],
    )
    role: UserRole | None = Field(
        default=None,
        description="Роль (только для администратора)",
        examples=["auditor"],
    )
    is_active: bool | None = Field(
        default=None,
        description="Активность учётной записи (только для администратора)",
        examples=[True],
    )
