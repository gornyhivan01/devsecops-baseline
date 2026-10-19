"""Security-заголовки через middleware.

Покрытие OWASP Top 10 2021:

- **A05 Security Misconfiguration** — явно заданные заголовки, защищающие от
  clickjacking, MIME-sniffing и утечки referrer, а также строгая HSTS.

CSP задаётся строгой (``default-src 'none'``) для ответов API. Для страниц
документации (Swagger UI / ReDoc) применяется отдельная политика: их ассеты
отдаются локально (пакет ``fastapi-offline``), поэтому внешние источники не
разрешаются — остаётся ``'self'``. ``'unsafe-inline'`` нужен только для
inline-скрипта инициализации Swagger UI. Документация доступна только вне
``production``, так что политика не ослабляет рабочий API.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Строгая политика по умолчанию: ни один ресурс не разрешён.
STRICT_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"

# Политика для страниц документации: только собственные ресурсы сервиса.
# ``'unsafe-inline'`` необходим для inline-скрипта инициализации Swagger UI.
DOCS_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self' data:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; base-uri 'self'; form-action 'none'"
)

DOCS_PATH_PREFIXES = ("/docs", "/redoc")


def _csp_for_path(path: str) -> str:
    """Возвращает CSP: ослабленную для страниц документации, строгую для API."""
    return DOCS_CSP if path.startswith(DOCS_PATH_PREFIXES) else STRICT_CSP


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Добавляет набор защитных заголовков ко всем ответам API."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=(), usb=()"
        )
        response.headers["Content-Security-Policy"] = _csp_for_path(request.url.path)
        # HSTS применим только поверх HTTPS; при локальном HTTP браузер безопасно его игнорирует.
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        # API не кэширует чувствительные ответы по умолчанию.
        response.headers["Cache-Control"] = "no-store"

        return response
