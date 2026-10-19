"""OWASP A03/A04: строгая валидация входных данных.

Схемы используют ``extra="forbid"`` (защита от mass assignment) и явные
ограничения длины/формата (защита от ресурсных атак и переполнения).
"""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.utils import auth_header, seed_user

PASSWORD = "SuperSecret123!"


async def test_register_rejects_extra_fields(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "x@example.com",
            "full_name": "X",
            "password": PASSWORD,
            "is_admin": True,  # попытка массового назначения
        },
    )
    assert response.status_code == 422


async def test_register_rejects_weak_password(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "x@example.com", "full_name": "X", "password": "short"},
    )
    assert response.status_code == 422


async def test_register_rejects_invalid_email(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "full_name": "X", "password": PASSWORD},
    )
    assert response.status_code == 422


async def test_item_title_too_long_rejected(client: AsyncClient, db: AsyncSession) -> None:
    user = await seed_user(db)
    response = await client.post(
        "/api/v1/items", json={"title": "a" * 300}, headers=auth_header(user)
    )
    assert response.status_code == 422


async def test_item_rejects_unknown_fields(client: AsyncClient, db: AsyncSession) -> None:
    user = await seed_user(db)
    response = await client.post(
        "/api/v1/items",
        json={"title": "x", "owner_id": "someone-else"},
        headers=auth_header(user),
    )
    assert response.status_code == 422
