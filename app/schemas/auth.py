"""Схемы аутентификации.

Валидация входных данных (A03/A04): строгая типизация, ``extra="forbid"`` и
ограничение длины пароля предотвращают неожиданные поля и ресурсные атаки.

Для Swagger UI заданы примеры полей (``examples``) и целых тел запросов
(``json_schema_extra``), чтобы документация была самодостаточной.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field

_EXAMPLE_EMAIL = "user@example.com"
_EXAMPLE_PASSWORD = "SuperSecret123!"  # noqa: S105 — демонстрационный пример, не секрет
_EXAMPLE_ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.<payload>.<signature>"  # noqa: S105
_EXAMPLE_REFRESH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.<payload>.<signature>"  # noqa: S105


class RegisterRequest(BaseModel):
    """Тело запроса регистрации нового пользователя."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "email": _EXAMPLE_EMAIL,
                    "full_name": "Иван Иванов",
                    "password": _EXAMPLE_PASSWORD,
                }
            ]
        },
    )

    email: EmailStr = Field(description="Электронная почта", examples=[_EXAMPLE_EMAIL])
    full_name: str = Field(
        min_length=1,
        max_length=200,
        description="Полное имя",
        examples=["Иван Иванов"],
    )
    password: str = Field(
        min_length=12,
        max_length=128,
        description="Пароль (минимум 12 символов)",
        examples=[_EXAMPLE_PASSWORD],
    )


class LoginRequest(BaseModel):
    """Тело запроса входа."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={"examples": [{"email": _EXAMPLE_EMAIL, "password": _EXAMPLE_PASSWORD}]},
    )

    email: EmailStr = Field(description="Электронная почта", examples=[_EXAMPLE_EMAIL])
    password: str = Field(
        min_length=1,
        max_length=128,
        description="Пароль",
        examples=[_EXAMPLE_PASSWORD],
    )


class AccessTokenResponse(BaseModel):
    """Ответ с короткоживущим access-токеном."""

    access_token: str = Field(
        description="JWT access-токен",
        examples=[_EXAMPLE_ACCESS_TOKEN],
    )
    token_type: str = Field(default="bearer", description="Тип токена", examples=["bearer"])
    expires_in: int = Field(
        description="Время жизни access-токена, секунды",
        examples=[900],
    )


class TokenResponse(AccessTokenResponse):
    """Ответ с парой access + refresh токенов."""

    refresh_token: str = Field(
        description="JWT refresh-токен (ротируется при каждом обновлении)",
        examples=[_EXAMPLE_REFRESH_TOKEN],
    )


class RefreshRequest(BaseModel):
    """Тело запроса ротации или отзыва refresh-токена."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={"examples": [{"refresh_token": _EXAMPLE_REFRESH_TOKEN}]},
    )

    refresh_token: str = Field(
        description="Действующий refresh-токен",
        examples=[_EXAMPLE_REFRESH_TOKEN],
    )
