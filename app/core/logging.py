"""Структурированное логирование через structlog с обязательной ред-акцией секретов.

Покрытие OWASP Top 10 2021:

- **A09 Security Logging and Monitoring Failures** — единый структурированный
  JSON-журнал, из которого гарантированно исключаются пароли, токены и прочие
  чувствительные данные.

Список чувствительных полей перечислен в :data:`SENSITIVE_FIELDS` и применяется
на самом раннем этапе пайплайна процессоров structlog.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

# Имена ключей (и любые вхождения этих подстрок), чьи значения подлежат ред-акции.
SENSITIVE_FIELDS = frozenset(
    {
        "password",
        "passphrase",
        "secret",
        "token",
        "authorization",
        "cookie",
        "set-cookie",
        "api_key",
        "apikey",
        "refresh_token",
        "access_token",
        "private_key",
        "x-api-key",
    }
)

REDACTED = "[REDACTED]"


def redact(_logger: Any, _name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Заменяет значения чувствительных ключей на ``[REDACTED]``."""
    for key in list(event_dict):
        if any(marker in key.lower() for marker in SENSITIVE_FIELDS):
            event_dict[key] = REDACTED
    return event_dict


def configure_logging(settings: Any) -> None:
    """Настраивает structlog с выводом в JSON (или human-readable) в stdout."""
    timestamper = structlog.processors.TimeStamper(fmt="iso")

    processors: list[Any] = [
        redact,
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if getattr(settings, "log_json", True):
        renderer: Any = structlog.processors.JSONRenderer(ensure_ascii=False)
    else:
        renderer = structlog.dev.ConsoleRenderer()

    processors.append(renderer)

    # structlog пишет в stdout через PrintLoggerFactory; базовый уровень — из настроек.
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=settings.log_level)

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelNamesMapping()[settings.log_level.upper()]
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "app") -> Any:
    """Возвращает структурный логгер с привязанным именем источника."""
    return structlog.get_logger().bind(logger=name)
