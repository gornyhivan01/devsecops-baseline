"""Схемы ресурса Item.

Примеры полей и тел запросов заданы для отображения в Swagger UI.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

_EXAMPLE_ITEM_ID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
_EXAMPLE_OWNER_ID = "00000000-0000-0000-0000-000000000001"


class ItemCreate(BaseModel):
    """Тело запроса создания item."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {"title": "Отчёт за квартал", "description": "Черновик отчёта для руководства"},
                {"title": "Задача без описания"},
            ]
        },
    )

    title: str = Field(
        min_length=1,
        max_length=200,
        description="Заголовок item",
        examples=["Отчёт за квартал"],
    )
    description: str | None = Field(
        default=None,
        max_length=10_000,
        description="Описание (необязательно)",
        examples=["Черновик отчёта для руководства"],
    )


class ItemUpdate(BaseModel):
    """Тело запроса обновления item (все поля необязательны)."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={"examples": [{"title": "Обновлённый заголовок"}]},
    )

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Новый заголовок",
        examples=["Обновлённый заголовок"],
    )
    description: str | None = Field(
        default=None,
        max_length=10_000,
        description="Новое описание",
        examples=["Новое описание"],
    )


class ItemRead(BaseModel):
    """Представление item в ответах."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": _EXAMPLE_ITEM_ID,
                    "owner_id": _EXAMPLE_OWNER_ID,
                    "title": "Отчёт за квартал",
                    "description": "Черновик отчёта для руководства",
                    "created_at": "2026-01-01T12:00:00Z",
                    "updated_at": "2026-01-01T12:00:00Z",
                }
            ]
        },
    )

    id: uuid.UUID = Field(description="Идентификатор item", examples=[_EXAMPLE_ITEM_ID])
    owner_id: uuid.UUID = Field(description="Владелец", examples=[_EXAMPLE_OWNER_ID])
    title: str = Field(description="Заголовок", examples=["Отчёт за квартал"])
    description: str | None = Field(description="Описание", examples=["Черновик отчёта"])
    created_at: datetime = Field(description="Создано (UTC)")
    updated_at: datetime = Field(description="Обновлено (UTC)")
