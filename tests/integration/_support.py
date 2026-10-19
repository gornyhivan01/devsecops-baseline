"""Вспомогательные функции для интеграционных тестов на PostgreSQL.

Модуль вынесен отдельно, чтобы его могли импортировать и ``conftest.py``, и
сами тесты без циклического импорта ``conftest``.
"""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncEngine

# tests/integration/_support.py -> parents[2] == корень репозитория
REPO_ROOT = Path(__file__).resolve().parents[2]

EXPECTED_TABLES: frozenset[str] = frozenset({"users", "items", "refresh_tokens", "alembic_version"})


def alembic_config(url: str) -> Config:
    """Конфиг Alembic с программно переопределённым URL.

    Значение подхватывается в ``alembic/env.py`` (там URL из настроек
    используется только если явное значение не задано).
    """
    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


async def table_names(engine: AsyncEngine) -> set[str]:
    """Возвращает имена таблиц в основной схеме."""
    async with engine.connect() as connection:
        names = await connection.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
    return set(names)
