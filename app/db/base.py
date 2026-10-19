"""Декларативная база моделей SQLAlchemy 2.0."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Базовый класс всех ORM-моделей."""

    __abstract__ = True
