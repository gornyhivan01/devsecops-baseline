# syntax=docker/dockerfile:1

# =========================================================================== #
#  DevSecOps Baseline — этап 2: контейнеризация
#  Multi-stage Dockerfile: в build-слое только зависимости, в runtime —
#  только то, что нужно для запуска, и всё от пользователя без прав (non-root).
# =========================================================================== #

# ---------------------------------------------------------------------------
# Стадия build: формируем виртуальное окружение uv без самого проекта.
# Все зависимости имеют manylinux-wheels, поэтому компилятор не нужен.
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_NO_PROGRESS=1

# Бинарник uv прямо из официального образа astral.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Сначала только манифесты — слой с зависимостями кэшируется,
# пока pyproject.toml / uv.lock не менялись.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# ---------------------------------------------------------------------------
# Стадия runtime: минимальный образ с .venv из build-стадии.
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Непривилегированный пользователь для запуска (без root-процессов в контейнере).
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin app

# Готовое окружение + исходники приложения.
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app alembic.ini pyproject.toml uv.lock ./
COPY --chown=app:app alembic alembic
COPY --chown=app:app app/ app/
COPY --chown=app:app docker/ docker/

USER app

EXPOSE 8000

# Healthcheck: /health/live отвечает 200, как только приложение поднялось.
# Python-однострочник вместо curl — в образе нет лишних утилит (slim).
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=3)" || exit 1

# Запуск: миграции Alembic, затем uvicorn (см. docker/entrypoint.sh).
ENTRYPOINT ["/app/docker/entrypoint.sh"]