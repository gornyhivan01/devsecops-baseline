"""Общие схемы."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Message(BaseModel):
    """Простой ответ с сообщением."""

    model_config = ConfigDict(json_schema_extra={"examples": [{"detail": "Item deleted"}]})

    detail: str = Field(description="Текст сообщения", examples=["Item deleted"])
