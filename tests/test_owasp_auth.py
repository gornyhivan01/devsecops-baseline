"""OWASP A07: Identification and Authentication Failures.

Проверяются: короткий TTL access-токена, refresh-токены с ротацией и отзывом,
отклонение неверных учётных данных.
"""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.utils import seed_user

PASSWORD = "SuperSecret123!"


async def _login(client: AsyncClient, email: str = "user@example.com", password: str = PASSWORD):
    return await client.post("/api/v1/auth/login", json={"email": email, "password": password})


async def test_register_returns_created(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "full_name": "New User", "password": PASSWORD},
    )
    assert response.status_code == 201
    assert response.json()["email"] == "new@example.com"
    assert "password" not in response.json()


async def test_login_returns_token_pair(client: AsyncClient, db: AsyncSession) -> None:
    await seed_user(db, password=PASSWORD)
    response = await _login(client)
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["expires_in"] == 15 * 60


async def test_login_wrong_password_rejected(client: AsyncClient, db: AsyncSession) -> None:
    await seed_user(db, password=PASSWORD)
    response = await _login(client, password="definitely-wrong")
    assert response.status_code == 401


async def test_duplicate_email_conflict(client: AsyncClient, db: AsyncSession) -> None:
    await seed_user(db, email="dup@example.com")
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "full_name": "X", "password": PASSWORD},
    )
    assert response.status_code == 409


async def test_refresh_rotation_invalidates_old_token(
    client: AsyncClient, db: AsyncSession
) -> None:
    await seed_user(db, password=PASSWORD)
    login = await _login(client)
    old_refresh = login.json()["refresh_token"]

    first = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert first.status_code == 200
    assert first.json()["access_token"]

    # Повторное использование уже отозванного refresh-токена отклоняется.
    second = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert second.status_code == 401


async def test_logout_revokes_refresh_token(client: AsyncClient, db: AsyncSession) -> None:
    await seed_user(db, password=PASSWORD)
    login = await _login(client)
    refresh = login.json()["refresh_token"]
    access = login.json()["access_token"]

    headers = {"Authorization": f"Bearer {access}"}
    logout = await client.post(
        "/api/v1/auth/logout", json={"refresh_token": refresh}, headers=headers
    )
    assert logout.status_code == 200

    # Отозванный refresh-токен больше не работает.
    retry = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert retry.status_code == 401
