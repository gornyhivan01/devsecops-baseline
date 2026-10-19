"""OWASP A01: Broken Access Control — RBAC и объектный доступ."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserRole
from tests.utils import auth_header, seed_user


async def test_auditor_cannot_create_item(client: AsyncClient, db: AsyncSession) -> None:
    auditor = await seed_user(db, email="auditor@example.com", role=UserRole.AUDITOR)
    response = await client.post("/api/v1/items", json={"title": "x"}, headers=auth_header(auditor))
    assert response.status_code == 403


async def test_user_cannot_read_other_users_item(client: AsyncClient, db: AsyncSession) -> None:
    owner = await seed_user(db, email="owner@example.com")
    other = await seed_user(db, email="other@example.com")

    created = await client.post(
        "/api/v1/items",
        json={"title": "secret", "description": "private"},
        headers=auth_header(owner),
    )
    item_id = created.json()["id"]

    response = await client.get(f"/api/v1/items/{item_id}", headers=auth_header(other))
    # 404, а не 403 — не раскрываем сам факт существования чужого ресурса.
    assert response.status_code == 404


async def test_regular_user_cannot_list_users(client: AsyncClient, db: AsyncSession) -> None:
    user = await seed_user(db)
    response = await client.get("/api/v1/users", headers=auth_header(user))
    assert response.status_code == 403


async def test_admin_can_list_users(client: AsyncClient, db: AsyncSession) -> None:
    admin = await seed_user(db, email="admin@example.com", role=UserRole.ADMIN)
    response = await client.get("/api/v1/users", headers=auth_header(admin))
    assert response.status_code == 200
    assert any(u["email"] == "admin@example.com" for u in response.json())


async def test_user_cannot_self_escalate_role(client: AsyncClient, db: AsyncSession) -> None:
    user = await seed_user(db)
    response = await client.patch(
        "/api/v1/users/me", json={"role": "admin"}, headers=auth_header(user)
    )
    assert response.status_code == 200
    assert response.json()["role"] == "user"


async def test_owner_can_update_own_item(client: AsyncClient, db: AsyncSession) -> None:
    owner = await seed_user(db)
    created = await client.post("/api/v1/items", json={"title": "mine"}, headers=auth_header(owner))
    item_id = created.json()["id"]

    response = await client.put(
        f"/api/v1/items/{item_id}", json={"title": "updated"}, headers=auth_header(owner)
    )
    assert response.status_code == 200
    assert response.json()["title"] == "updated"
