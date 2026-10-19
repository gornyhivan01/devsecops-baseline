"""Глобальная конфигурация pytest.

Ключевой момент: переменные окружения задаются **до** импорта приложения, потому
что настройки кэшируются (``lru_cache``) и читаются один раз. Для тестов
используется SQLite (файл), Argon2 с пониженной стоимостью и высокие лимиты
rate limiting, чтобы не мешать массовым запросам.
"""

from __future__ import annotations

import os
import tempfile

# --- окружение ДО импортов приложения ---
if os.environ.get("BASELINE_TEST_ENV") != "1":
    _tmp_dir = tempfile.mkdtemp(prefix="baseline_test_")
    os.environ["BASELINE_TEST_ENV"] = "1"
    os.environ["SECRET_KEY"] = "test-secret-key-0123456789abcdef0123456789abcd"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp_dir}/test.db"
    # NullPool: тесты создают движок в одном event loop, а используют в другом.
    os.environ["DATABASE_POOL_DISABLED"] = "true"
    os.environ["ARGON2_TIME_COST"] = "1"
    os.environ["ARGON2_MEMORY_COST"] = "1024"
    os.environ["ARGON2_PARALLELISM"] = "1"
    os.environ["RATE_LIMIT_DEFAULT"] = "10000/minute"
    os.environ["RATE_LIMIT_AUTH"] = "10000/minute"
    os.environ["ENVIRONMENT"] = "test"
    os.environ["LOG_JSON"] = "false"

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import get_engine, get_session_factory  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Item, RefreshToken, User  # noqa: E402


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _create_schema() -> None:
    """Создаёт схему БД один раз на тестовую сессию."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest_asyncio.fixture(autouse=True)
async def _clean_tables() -> None:
    """Очищает таблицы перед каждым тестом (порядок важен из-за FK)."""
    factory = get_session_factory()
    async with factory() as session:
        for model in (Item, RefreshToken, User):
            await session.execute(model.__table__.delete())
        await session.commit()


@pytest_asyncio.fixture
async def db():
    """Выдаёт чистую async-сессию (общая функция-scope с сессионным loop)."""
    factory = get_session_factory()
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    """HTTP-клиент с ASGI-транспортом (без реального сетевого сокета)."""
    transport = ASGITransport(app=app, client=("127.0.0.1", 50000))
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
