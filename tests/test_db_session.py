"""Регресс-тесты выбора пула соединений в движке БД.

Ранее ``get_engine`` включал ``NullPool`` эвристикой по префиксу URL
(``sqlite``), из-за чего знание о тестовом диалекте протекало в продакшн-код.
Теперь режим пула задаётся настройкой ``DATABASE_POOL_DISABLED``.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool

from app.core import config
from app.db import session as db_session

_POSTGRES_URL = "postgresql+asyncpg://app:app@localhost:5432/app"


@pytest.fixture
def isolated_engine(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Изолирует глобальный движок и кэш настроек до и после теста."""
    monkeypatch.setattr(db_session, "_engine", None)
    monkeypatch.setattr(db_session, "_session_factory", None)
    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()


def test_engine_uses_nullpool_when_pool_disabled(
    monkeypatch: pytest.MonkeyPatch, isolated_engine: None
) -> None:
    monkeypatch.setenv("SECRET_KEY", "x" * 40)
    monkeypatch.setenv("DATABASE_URL", _POSTGRES_URL)
    monkeypatch.setenv("DATABASE_POOL_DISABLED", "true")

    engine = db_session.get_engine()

    assert isinstance(engine.pool, NullPool)


def test_engine_uses_queue_pool_by_default(
    monkeypatch: pytest.MonkeyPatch, isolated_engine: None
) -> None:
    monkeypatch.setenv("SECRET_KEY", "x" * 40)
    monkeypatch.setenv("DATABASE_URL", _POSTGRES_URL)
    monkeypatch.delenv("DATABASE_POOL_DISABLED", raising=False)

    engine = db_session.get_engine()

    assert isinstance(engine.pool, AsyncAdaptedQueuePool)
