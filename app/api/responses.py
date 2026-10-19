"""Готовые описания ответов для OpenAPI (передаются в ``responses=``).

Стандартизируют документацию ошибок в Swagger UI: коды, пояснения и примеры
тела ответа. Примеры важны для API-безопасности — они показывают, что чужие
объекты возвращают 404 (анти-энумерация), а превышение лимита — 429.
"""

from __future__ import annotations

from typing import Any

ResponseSpec = dict[int | str, dict[str, Any]]

UNAUTHORIZED: ResponseSpec = {
    401: {"description": "Не аутентифицирован или недействительный access-токен"}
}
FORBIDDEN: ResponseSpec = {403: {"description": "Недостаточно прав (RBAC)"}}
NOT_FOUND: ResponseSpec = {
    404: {"description": "Ресурс не найден или нет доступа (анти-энумерация)"}
}
CONFLICT: ResponseSpec = {409: {"description": "Пользователь с таким email уже зарегистрирован"}}
VALIDATION: ResponseSpec = {422: {"description": "Ошибка валидации входных данных"}}
RATE_LIMITED: ResponseSpec = {
    429: {
        "description": "Превышен лимит запросов (rate limit)",
        "content": {"application/json": {"example": {"detail": "Rate limit exceeded"}}},
    }
}


def merge(*specs: ResponseSpec) -> ResponseSpec:
    """Объединяет несколько спецификаций ответов в одну (последние перекрывают)."""
    merged: ResponseSpec = {}
    for spec in specs:
        merged.update(spec)
    return merged
