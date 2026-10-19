"""Проверка миграций Alembic на реальном PostgreSQL.

Закрывает главный пробел SQLite-тестов: они создают схему через
``Base.metadata.create_all`` и не проверяют сам файл миграции.
"""

from __future__ import annotations

import asyncio

import pytest
from alembic import command
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.integration._support import EXPECTED_TABLES, alembic_config, table_names

# Тесты выполняются в session-loop: движок и БД создаются session-фикстурами,
# и объекты asyncpg не должны пересекать границы event loop.
pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


async def test_upgrade_head_creates_expected_tables(pg_engine: AsyncEngine) -> None:
    """``alembic upgrade head`` создаёт полную схему (users/items/refresh_tokens)."""
    assert EXPECTED_TABLES <= await table_names(pg_engine)


async def test_downgrade_base_and_upgrade_roundtrip(
    migrated_url: str, pg_engine: AsyncEngine
) -> None:
    """``downgrade base`` удаляет таблицы, повторный ``upgrade head`` их возвращает.

    Проверяет, что миграция обратима (наличие рабочего ``downgrade``).
    """
    config = alembic_config(migrated_url)

    await asyncio.to_thread(command.downgrade, config, "base")
    # Остаётся только служебная таблица Alembic с версиями.
    assert await table_names(pg_engine) == {"alembic_version"}

    await asyncio.to_thread(command.upgrade, config, "head")
    assert EXPECTED_TABLES <= await table_names(pg_engine)
