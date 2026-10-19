"""Health-эндпоинты liveness и readiness.

Разделение на два состояния стандартно для оркестраторов:

- **liveness** — процесс жив; перезапуск, если не отвечает.
- **readiness** — сервис готов принимать трафик (проверяется подключение к БД).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter(tags=["health"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("/health/live", summary="Liveness probe")
async def liveness() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/health/ready", summary="Readiness probe")
async def readiness(db: DbSession) -> dict[str, str]:
    try:
        await db.execute(select(1))
    except Exception as exc:  # noqa: BLE001 — readiness отвечает 503 при любой ошибке БД
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from exc
    return {"status": "ready", "database": "ok"}
