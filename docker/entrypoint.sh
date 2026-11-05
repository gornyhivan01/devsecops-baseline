#!/bin/sh
# =========================================================================== #
#  DevSecOps Baseline — entrypoint контейнера.
#  1. Накатывает миграции Alembic.
#  2. Запускает uvicorn как главный процесс (exec — получает сигналы docker).
# =========================================================================== #
set -e

echo "[entrypoint] applying migrations (alembic upgrade head)"
alembic upgrade head

echo "[entrypoint] starting uvicorn on 0.0.0.0:${PORT:-8000}"
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers "${UVICORN_WORKERS:-1}" \
    --no-server-header