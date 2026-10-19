"""Эндпоинты CRUD ресурса Item.

Покрытие OWASP Top 10 2021:

- **A01 Broken Access Control** — объектный доступ ограничен владельцем; роли
  ``admin``/``auditor`` имеют расширенный доступ, ``auditor`` — только чтение.
- **A03 Injection** — фильтр поиска использует параметризованный ``ilike``
  (без конкатенации строк), что исключает SQL-инъекции.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession, has_role, require_roles
from app.api.responses import FORBIDDEN, NOT_FOUND, UNAUTHORIZED, merge
from app.models.item import Item
from app.models.user import User, UserRole
from app.schemas.common import Message
from app.schemas.item import ItemCreate, ItemRead, ItemUpdate

router = APIRouter()

CurrentEditor = Depends(require_roles(UserRole.ADMIN, UserRole.USER))

ItemId = Annotated[
    uuid.UUID,
    Path(description="UUID item", examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"]),
]


def _can_read(user: User, item: Item) -> bool:
    return has_role(user, UserRole.ADMIN, UserRole.AUDITOR) or item.owner_id == user.id


def _can_write(user: User, item: Item) -> bool:
    return has_role(user, UserRole.ADMIN) or item.owner_id == user.id


@router.get(
    "",
    response_model=list[ItemRead],
    summary="Список items",
    description=(
        "Владелец видит только свои items; ``admin``/``auditor`` — все. "
        "Фильтр ``search`` — по подстроке в заголовке (регистронезависимый)."
    ),
    responses=merge(UNAUTHORIZED),
)
async def list_items(
    db: DbSession,
    current_user: CurrentUser,
    search: str | None = Query(
        default=None,
        max_length=100,
        description="Поиск по подстроке в заголовке (регистронезависимый)",
        examples=["отчёт"],
    ),
) -> list[ItemRead]:
    """Возвращает items: владелец видит свои, admin/auditor — все.

    ``search`` применяется параметризованно (``ilike``), защищая от SQL-инъекций.
    """
    stmt = select(Item)
    if not has_role(current_user, UserRole.ADMIN, UserRole.AUDITOR):
        stmt = stmt.where(Item.owner_id == current_user.id)
    if search:
        stmt = stmt.where(Item.title.ilike(f"%{search}%"))

    result = await db.execute(stmt.order_by(Item.created_at))
    return [ItemRead.model_validate(item) for item in result.scalars().all()]


@router.post(
    "",
    response_model=ItemRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создание item",
    responses=merge(UNAUTHORIZED, FORBIDDEN),
)
async def create_item(
    data: ItemCreate, db: DbSession, current_user: User = CurrentEditor
) -> ItemRead:
    """Создаёт item, принадлежащий текущему пользователю."""
    item = Item(owner_id=current_user.id, title=data.title, description=data.description)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return ItemRead.model_validate(item)


@router.get(
    "/{item_id}",
    response_model=ItemRead,
    summary="Получение item",
    responses=merge(UNAUTHORIZED, NOT_FOUND),
)
async def get_item(item_id: ItemId, db: DbSession, current_user: CurrentUser) -> ItemRead:
    item = await db.get(Item, item_id)
    if item is None or not _can_read(current_user, item):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return ItemRead.model_validate(item)


@router.put(
    "/{item_id}",
    response_model=ItemRead,
    summary="Обновление item",
    responses=merge(UNAUTHORIZED, FORBIDDEN, NOT_FOUND),
)
async def update_item(
    item_id: ItemId,
    data: ItemUpdate,
    db: DbSession,
    current_user: User = CurrentEditor,
) -> ItemRead:
    item = await db.get(Item, item_id)
    if item is None or not _can_write(current_user, item):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    if data.title is not None:
        item.title = data.title
    if data.description is not None:
        item.description = data.description

    await db.commit()
    await db.refresh(item)
    return ItemRead.model_validate(item)


@router.delete(
    "/{item_id}",
    response_model=Message,
    summary="Удаление item",
    responses=merge(UNAUTHORIZED, FORBIDDEN, NOT_FOUND),
)
async def delete_item(
    item_id: ItemId,
    db: DbSession,
    current_user: User = CurrentEditor,
) -> Message:
    item = await db.get(Item, item_id)
    if item is None or not _can_write(current_user, item):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    await db.delete(item)
    await db.commit()
    return Message(detail="Item deleted")
