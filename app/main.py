"""Точка входа FastAPI-приложения.

Порядок middleware важен: security-заголовки добавляются последними и потому
оказываются самым внешним слоем, применяясь ко всем ответам.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_offline import FastAPIOffline
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.api.v1.endpoints.health import router as health_router
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.rate_limit import limiter
from app.core.security_headers import SecurityHeadersMiddleware


async def rate_limit_exceeded_handler(request: Request, exc: Exception) -> Response:
    """Возвращает 429 при превышении лимита запросов."""
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded"},
    )


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)
    logger = get_logger("app.main")

    docs_enabled = settings.environment != "production"
    # FastAPIOffline отдаёт ассеты Swagger UI/ReDoc из собственного пакета (локально
    # по /static-offline-docs), исключая загрузку с CDN — важно для supply-chain,
    # offline/air-gapped контуров и приватности. Схема остаётся на /openapi.json.
    app = FastAPIOffline(
        title=settings.app_name,
        version=settings.version,
        openapi_url="/openapi.json" if docs_enabled else None,
        docs_url="/docs" if docs_enabled else None,
        redoc_url=None,
    )

    # CORS: явный allow-лист origin'ов вместо "*".
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Security-заголовки (самый внешний слой).
    app.add_middleware(SecurityHeadersMiddleware)

    # Rate limiting.
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    # Prometheus-метрики (A09: observability).
    Instrumentator(excluded_handlers=["/metrics", "/health/live", "/health/ready"]).instrument(
        app
    ).expose(app, endpoint="/metrics", include_in_schema=False)

    app.include_router(health_router)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    logger.info("app_configured", environment=settings.environment, version=settings.version)
    return app


app = create_app()
