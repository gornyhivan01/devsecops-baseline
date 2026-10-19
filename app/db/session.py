"""Асинхронная сессия и движок SQLAlchemy 2.0.

Движок создаётся лениво при первом обращении, чтобы тесты могли задать
альтернативный ``DATABASE_URL`` и режим пула до первого использования.
Выбор пула управляется настройкой ``DATABASE_POOL_DISABLED``, а не типом СУБД,
поэтому код движка не зависит от конкретного диалекта.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Возвращает (лениво созданный) глобальный async-движок."""
    global _engine
    if _engine is None:
        settings = get_settings()
        kwargs: dict[str, object] = {"pool_pre_ping": True, "echo": settings.debug}
        # NullPool исключает переиспользование соединений между event loop'ами
        # (тесты) и уместен в недолговечных процессах (serverless).
        if settings.database_pool_disabled:
            kwargs["poolclass"] = NullPool
        _engine = create_async_engine(settings.database_url, **kwargs)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Возвращает фабрику сессий."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI-зависимость: выдаёт сессию и гарантированно её закрывает."""
    factory = get_session_factory()
    async with factory() as session:
        yield session
