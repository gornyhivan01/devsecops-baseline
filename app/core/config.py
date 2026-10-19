"""Конфигурация приложения через pydantic-settings.

Значения читаются из переменных окружения и файла ``.env``. Секреты (например,
``SECRET_KEY``) не имеют безопасных значений по умолчанию и должны задаваться явно.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки сервиса.

    Поля сопоставляются с переменными окружения без префикса и без учёта регистра
    (``case_sensitive=False``). Неизвестные переменные игнорируются (``extra="ignore"``),
    чтобы не ломать запуск при смене окружения.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "DevSecOps Baseline Service"
    version: str = "0.1.0"
    environment: str = "development"  # development | staging | production
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # --- JWT / аутентификация ---
    secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"  # HS256 для быстрого старта, RS256/keyless для прода
    access_token_expire_minutes: int = 15  # короткий TTL access-токена
    refresh_token_expire_days: int = 7
    jwt_issuer: str = "devsecops-baseline"
    jwt_audience: str = "devsecops-baseline-clients"

    # --- База данных ---
    database_url: str = "postgresql+asyncpg://app:app@localhost:5432/app"
    # Отключает пул соединений (NullPool). Нужно там, где соединения нельзя
    # переиспользовать между разными event loop'ами (тесты) или где процесс
    # недолговечен (serverless). Не привязано к конкретной СУБД.
    database_pool_disabled: bool = False

    # --- CORS ---
    # NoDecode отключает авто-JSON-разбор составного поля в pydantic-settings,
    # чтобы поддержать человекочитаемый формат "origin1,origin2" (см. валидатор ниже).
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    # --- Rate limiting ---
    rate_limit_default: str = "100/minute"
    rate_limit_auth: str = "5/minute"

    # --- Argon2id (A02: Cryptographic Failures) ---
    argon2_time_cost: int = 3
    argon2_memory_cost: int = 65536  # килобайты (64 MiB)
    argon2_parallelism: int = 4

    # --- Логирование ---
    log_level: str = "INFO"
    log_json: bool = True

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: object) -> object:
        """Принимает JSON-список, строку через запятую или готовый список.

        Человекочитаемый формат ``origin1,origin2`` задокументирован в
        ``.env.example``; JSON-список сохранён для обратной совместимости.
        """
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                try:
                    return json.loads(stripped)
                except json.JSONDecodeError:
                    pass  # не JSON — трактуем как список через запятую
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Возвращает синглтон настроек (кэшируется).

    Кэширование позволяет конструировать приложение без повторного чтения окружения.
    В тестах окружение задаётся до первого вызова.
    """
    return Settings()


settings = get_settings()
