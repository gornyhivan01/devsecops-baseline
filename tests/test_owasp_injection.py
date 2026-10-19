"""OWASP A03: Injection — параметризованные запросы исключают SQL-инъекции."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.utils import auth_header, seed_user


async def test_search_treats_input_literally(client: AsyncClient, db: AsyncSession) -> None:
    """Вредоносная строка поиска обрабатывается как литерал, а не как SQL."""
    user = await seed_user(db)
    await client.post("/api/v1/items", json={"title": "normal"}, headers=auth_header(user))

    payload = "'; DROP TABLE items; --"
    response = await client.get(
        "/api/v1/items", params={"search": payload}, headers=auth_header(user)
    )
    assert response.status_code == 200
    assert response.json() == []  # вредоносный ввод ничего не совпал

    # Таблица и данные на месте.
    after = await client.get("/api/v1/items", headers=auth_header(user))
    assert len(after.json()) == 1


async def test_injection_cannot_leak_other_owners_data(
    client: AsyncClient, db: AsyncSession
) -> None:
    attacker = await seed_user(db, email="attacker@example.com")
    victim = await seed_user(db, email="victim@example.com")
    await client.post("/api/v1/items", json={"title": "victim secret"}, headers=auth_header(victim))

    payload = "' OR 1=1 --"
    response = await client.get(
        "/api/v1/items", params={"search": payload}, headers=auth_header(attacker)
    )
    assert response.status_code == 200
    assert response.json() == []  # чужие данные не утекли
