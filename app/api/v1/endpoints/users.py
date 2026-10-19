"""Эндпоинты пользователей и администрирования (RBAC).

Покрытие OWASP Top 10 2021 — **A01 Broken Access Control**:
- ``GET /users`` и ``PATCH /users/{id}`` доступны только администраторам;
- пользователь может менять исключительно собственный профиль.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession, require_roles
from app.api.responses import FORBIDDEN, NOT_FOUND, UNAUTHORIZED, VALIDATION, merge
from app.models.user import User, UserRole
from app.schemas.user import UserRead, UserUpdate

router = APIRouter()

CurrentAdmin = Depends(require_roles(UserRole.ADMIN))

UserId = Annotated[
    uuid.UUID,
    Path(description="UUID пользователя", examples=["00000000-0000-0000-0000-000000000001"]),
]


@router.get(
    "/me",
    response_model=UserRead,
    summary="Текущий пользователь",
    responses=merge(UNAUTHORIZED),
)
async def read_me(current_user: CurrentUser) -> UserRead:
    """Возвращает профиль пользователя, определённого по access-токену."""
    return UserRead.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserRead,
    summary="Обновление собственного профиля",
    description="Обновляет только ``full_name``; поле ``role`` игнорируется (RBAC).",
    responses=merge(UNAUTHORIZED, VALIDATION),
)
async def update_me(
    data: UserUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> UserRead:
    """Пользователь меняет только собственные данные; роль менять нельзя."""
    if data.full_name is not None:
        current_user.full_name = data.full_name
    await db.commit()
    await db.refresh(current_user)
    return UserRead.model_validate(current_user)


@router.get(
    "",
    response_model=list[UserRead],
    summary="Список пользователей (admin)",
    responses=merge(UNAUTHORIZED, FORBIDDEN),
)
async def list_users(db: DbSession, _: User = CurrentAdmin) -> list[UserRead]:
    """Возвращает всех пользователей; доступно только администратору."""
    result = await db.execute(select(User).order_by(User.created_at))
    return [UserRead.model_validate(user) for user in result.scalars().all()]


@router.patch(
    "/{user_id}",
    response_model=UserRead,
    summary="Управление пользователем (admin)",
    description="Администратор может менять ``full_name``, ``role`` и ``is_active``.",
    responses=merge(UNAUTHORIZED, FORBIDDEN, NOT_FOUND, VALIDATION),
)
async def update_user(
    user_id: UserId,
    data: UserUpdate,
    db: DbSession,
    _: User = CurrentAdmin,
) -> UserRead:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if data.full_name is not None:
        user.full_name = data.full_name
    if data.role is not None:
        user.role = data.role.value
    if data.is_active is not None:
        user.is_active = data.is_active

    await db.commit()
    await db.refresh(user)
    return UserRead.model_validate(user)
