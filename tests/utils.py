"""Помощники для тестов: создание пользователей и формирование заголовков."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole


async def seed_user(
    db: AsyncSession,
    email: str = "user@example.com",
    password: str = "SuperSecret123!",
    role: UserRole = UserRole.USER,
    full_name: str = "Test User",
    is_active: bool = True,
) -> User:
    """Создаёт пользователя напрямую в БД с известным паролем."""
    user = User(
        email=email,
        full_name=full_name,
        hashed_password=hash_password(password),
        role=role.value,
        is_active=is_active,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def auth_header(user: User) -> dict[str, str]:
    """Возвращает заголовок ``Authorization`` с access-токеном для пользователя."""
    token, _ = create_access_token(str(user.id), user.role)
    return {"Authorization": f"Bearer {token}"}
