"""Поведение, специфичное для PostgreSQL и отличающееся от SQLite.

Эти проверки сознательно не могут пройти на SQLite — именно поэтому нужен
интеграционный слой на «боевой» СУБД.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Uuid, bindparam, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.db.session import get_db
from app.main import app
from app.models.item import Item
from app.models.user import User
from tests.utils import seed_user

# Тесты выполняются в session-loop: движок, сессии и временная БД создаются
# session-фикстурами, и объекты asyncpg не должны пересекать границы loop.
pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]

_CYRILLIC_EMAIL = "cyrillic@example.com"
_API_EMAIL = "api-pg@example.com"
_PASSWORD = "SuperSecret123!"


async def test_cyrillic_ilike_is_case_insensitive(pg_session: AsyncSession) -> None:
    """``ILIKE`` игнорирует регистр кириллицы.

    На SQLite ``ilike`` компилируется в ``lower(x) LIKE lower(y)``, а встроенная
    ``lower()`` SQLite работает только с ASCII — совпадения не было бы.
    """
    user = await seed_user(pg_session, email=_CYRILLIC_EMAIL)
    pg_session.add(Item(owner_id=user.id, title="Отчёт за квартал"))
    await pg_session.commit()

    result = await pg_session.execute(select(Item).where(Item.title.ilike("%отчёт%")))
    assert result.scalars().all(), "ILIKE должен игнорировать регистр кириллицы"


async def test_foreign_key_cascade_on_delete(pg_session: AsyncSession) -> None:
    """``ON DELETE CASCADE`` работает на уровне СУБД.

    Удаление выполняется «сырым» Core-DELETE, чтобы исключить участие
    ORM-каскада и проверить именно ограничение внешнего ключа.
    """
    user = await seed_user(pg_session, email="cascade@example.com")
    item = Item(owner_id=user.id, title="каскад")
    pg_session.add(item)
    await pg_session.commit()
    item_id = item.id

    await pg_session.execute(
        text("DELETE FROM users WHERE id = :uid").bindparams(bindparam("uid", type_=Uuid)),
        {"uid": user.id},
    )
    await pg_session.commit()

    pg_session.expire_all()
    assert await pg_session.get(Item, item_id) is None


async def test_timestamps_are_timezone_aware(pg_session: AsyncSession) -> None:
    """``timestamptz`` сохраняет зону; SQLite вернул бы naive-дату."""
    user = await seed_user(pg_session, email="tz@example.com")
    await pg_session.refresh(user)
    assert user.created_at.tzinfo is not None


async def test_search_endpoint_finds_cyrillic_ignoring_case(pg_engine: AsyncEngine) -> None:
    """Сквозная проверка через API: поиск по кириллице не зависит от регистра.

    Сессия приложения подменяется через ``dependency_overrides`` на временную
    БД, поэтому проверяется реальный маршрут ``GET /api/v1/items?search=``.
    """
    factory = async_sessionmaker(pg_engine, expire_on_commit=False)

    async def _override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        transport = ASGITransport(app=app, client=("127.0.0.1", 50000))
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            await client.post(
                "/api/v1/auth/register",
                json={"email": _API_EMAIL, "full_name": "PG User", "password": _PASSWORD},
            )
            login = await client.post(
                "/api/v1/auth/login", json={"email": _API_EMAIL, "password": _PASSWORD}
            )
            assert login.status_code == 200
            token = login.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            created = await client.post(
                "/api/v1/items", json={"title": "Отчёт за квартал"}, headers=headers
            )
            assert created.status_code == 201

            found = await client.get("/api/v1/items", params={"search": "отчёт"}, headers=headers)
            assert found.status_code == 200
            titles = [item["title"] for item in found.json()]
            assert "Отчёт за квартал" in titles
    finally:
        app.dependency_overrides.clear()


async def test_user_model_is_bound_to_temporary_database(pg_session: AsyncSession) -> None:
    """Санити-проверка: ``seed_user`` работает и на PostgreSQL."""
    user = await seed_user(pg_session, email="sanity@example.com")
    assert isinstance(user, User)
