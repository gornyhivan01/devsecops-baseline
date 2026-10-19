"""Фикстуры интеграционных тестов против реального PostgreSQL.

Назначение — закрыть «слепые зоны» SQLite: миграции, диалектные особенности
(``ILIKE``, ``timestamptz``), каскады внешних ключей на уровне СУБД.

Запуск::

    docker compose up -d postgres
    INTEGRATION_DATABASE_URL=postgresql+asyncpg://app:app@localhost:5432/app \\
        uv run pytest -m integration

На сервере из ``INTEGRATION_DATABASE_URL`` создаётся **временная** база, на неё
накатываются миграции Alembic; по завершении сессии база удаляется. Благодаря
этому рабочая база приложения (``app``) не затрагивается, а миграции
проверяются по-настоящему. Если ``INTEGRATION_DATABASE_URL`` не задан, тесты
пропускаются (обычный прогон ``pytest`` не требует Docker).
"""

from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import AsyncIterator

import asyncpg
import pytest
import pytest_asyncio
from alembic import command
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from tests.integration._support import alembic_config

INTEGRATION_URL_ENV = "INTEGRATION_DATABASE_URL"
# Служебная БД, к которой подключаемся ради CREATE/DROP DATABASE.
MAINTENANCE_DB = "postgres"
DEFAULT_PORT = 5432


async def _admin_connection(base: URL) -> asyncpg.Connection:
    """Подключение к служебной БД для управления временной базой."""
    return await asyncpg.connect(
        host=base.host,
        port=base.port or DEFAULT_PORT,
        user=base.username,
        password=base.password,
        database=MAINTENANCE_DB,
    )


@pytest_asyncio.fixture(scope="session")
async def pg_database() -> AsyncIterator[str]:
    """Создаёт временную БД и возвращает её URL; удаляет по завершении сессии."""
    raw_url = os.environ.get(INTEGRATION_URL_ENV)
    if not raw_url:
        pytest.skip(
            f"{INTEGRATION_URL_ENV} не задан — интеграционные тесты пропущены "
            "(см. tests/integration/conftest.py)"
        )

    base = make_url(raw_url)
    db_name = f"devsecops_it_{uuid.uuid4().hex[:8]}"

    admin = await _admin_connection(base)
    try:
        await admin.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        await admin.close()

    test_url = base.set(database=db_name).render_as_string(hide_password=False)
    try:
        yield test_url
    finally:
        admin = await _admin_connection(base)
        try:
            # WITH (FORCE) доступен с PostgreSQL 13+ и обрывает активные сессии.
            await admin.execute(f'DROP DATABASE IF EXISTS "{db_name}" WITH (FORCE)')
        finally:
            await admin.close()


@pytest_asyncio.fixture(scope="session")
async def migrated_url(pg_database: str) -> AsyncIterator[str]:
    """Накатывает миграции Alembic на временную БД.

    ``command.upgrade`` вызывает ``asyncio.run`` в ``alembic/env.py``, поэтому
    запускаем его в отдельном потоке (в текущем event loop уже активен).
    """
    config = alembic_config(pg_database)
    await asyncio.to_thread(command.upgrade, config, "head")
    yield pg_database


@pytest_asyncio.fixture(scope="session")
async def pg_engine(migrated_url: str) -> AsyncIterator[AsyncEngine]:
    """Async-движок, привязанный к временной БД с накатанной схемой."""
    engine = create_async_engine(migrated_url, poolclass=NullPool)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def pg_session(pg_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Сессия к временной БД (функциональная область видимости)."""
    factory = async_sessionmaker(pg_engine, expire_on_commit=False)
    async with factory() as session:
        yield session
