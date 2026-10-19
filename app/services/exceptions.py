"""Доменные исключения сервисного слоя."""

from __future__ import annotations


class AuthError(Exception):
    """Базовое исключение аутентификации/авторизации."""


class InvalidCredentialsError(AuthError):
    """Неверные учётные данные или недействительный/отозванный токен."""


class InactiveUserError(AuthError):
    """Пользователь деактивирован."""


class EmailAlreadyExistsError(AuthError):
    """Email уже зарегистрирован."""
