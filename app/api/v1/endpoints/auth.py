"""Эндпоинты аутентификации.

Rate limiting на login/register (A04/A07) — см. ``RATE_LIMIT_AUTH``.

Внимание: без ``from __future__ import annotations`` — slowapi оборачивает
эндпоинты в ``async_wrapper``, ``__globals__`` которого указывает на модуль
slowapi, из-за чего FastAPI не может резолвить строковые (PEP 563) аннотации тел
запросов и трактует их как query-параметры.
"""

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.api.deps import CurrentUser, DbSession
from app.api.responses import (
    CONFLICT,
    FORBIDDEN,
    RATE_LIMITED,
    UNAUTHORIZED,
    VALIDATION,
    merge,
)
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from app.schemas.common import Message
from app.schemas.user import UserRead
from app.services.auth_service import AuthService
from app.services.exceptions import (
    EmailAlreadyExistsError,
    InactiveUserError,
    InvalidCredentialsError,
)

router = APIRouter()


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя",
    description="Создаёт пользователя с ролью по умолчанию ``user``.",
    responses=merge(CONFLICT, VALIDATION, RATE_LIMITED),
)
@limiter.limit(get_settings().rate_limit_auth)
async def register(
    request: Request, response: Response, data: RegisterRequest, db: DbSession
) -> UserRead:
    """Создаёт пользователя с ролью по умолчанию (``user``)."""
    service = AuthService(db)
    try:
        user = await service.register(data)
    except EmailAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return UserRead.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Вход и выпуск токенов",
    description="Проверяет учётные данные и выдаёт пару access + refresh токенов.",
    responses=merge(UNAUTHORIZED, FORBIDDEN, VALIDATION, RATE_LIMITED),
)
@limiter.limit(get_settings().rate_limit_auth)
async def login(
    request: Request, response: Response, data: LoginRequest, db: DbSession
) -> TokenResponse:
    """Проверяет учётные данные и выдаёт пару access + refresh токенов."""
    service = AuthService(db)
    try:
        return await service.login(data.email, data.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except InactiveUserError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Ротация refresh-токена",
    description="Обменивает валидный refresh-токен на новую пару (старый отзывается).",
    responses=merge(UNAUTHORIZED, VALIDATION),
)
async def refresh(data: RefreshRequest, db: DbSession) -> TokenResponse:
    """Обмен валидного refresh-токена на новую пару (старый отзывается)."""
    service = AuthService(db)
    try:
        return await service.refresh(data.refresh_token)
    except (InvalidCredentialsError, InactiveUserError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.post(
    "/logout",
    response_model=Message,
    summary="Выход и отзыв refresh-токена",
    description="Отзывает refresh-токен; access-токен остаётся короткоживущим.",
    responses=merge(UNAUTHORIZED, VALIDATION),
)
async def logout(
    data: RefreshRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> Message:
    """Отзывает refresh-токен; access-токен остаётся короткоживущим."""
    service = AuthService(db)
    await service.logout(data.refresh_token)
    return Message(detail="Logged out")
