"""Регресс-тесты конфигурации: разбор составного поля ``CORS_ORIGINS``.

Ранее значение ``CORS_ORIGINS=http://a,http://b`` (формат из ``.env.example``)
приводило к падению на импорте: pydantic-settings пытался выполнить ``json.loads``
для составного поля *до* валидатора. Теперь поле помечено ``NoDecode`` и
разбирается вручную, принимая оба формата.
"""

from __future__ import annotations

import pytest

from app.core.config import Settings


def test_cors_origins_parsed_from_env_comma_separated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://a, http://b")
    monkeypatch.setenv("SECRET_KEY", "x" * 40)

    settings = Settings()

    assert settings.cors_origins == ["http://a", "http://b"]


def test_cors_origins_accepts_json_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", '["http://a"]')
    monkeypatch.setenv("SECRET_KEY", "x" * 40)

    settings = Settings()

    assert settings.cors_origins == ["http://a"]


def test_cors_origins_single_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://only-one")
    monkeypatch.setenv("SECRET_KEY", "x" * 40)

    settings = Settings()

    assert settings.cors_origins == ["http://only-one"]


def test_database_pool_disabled_defaults_to_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_POOL_DISABLED", raising=False)
    monkeypatch.setenv("SECRET_KEY", "x" * 40)

    assert Settings().database_pool_disabled is False


def test_database_pool_disabled_parsed_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_POOL_DISABLED", "true")
    monkeypatch.setenv("SECRET_KEY", "x" * 40)

    assert Settings().database_pool_disabled is True
