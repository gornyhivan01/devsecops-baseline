"""Prometheus-метрики: служебный эндпоинт `/metrics`.

Проверяем минимальный контракт: эндпоинт доступен, отдаёт текст в формате
Prometheus и содержит стандартные HTTP-метрики после обычного запроса.
Скрейпинг, дашборды и алертинг — инфраструктурная задача (этап 7) и здесь
не проверяются.
"""

from __future__ import annotations

from httpx import AsyncClient


async def test_metrics_endpoint_returns_prometheus_text(client: AsyncClient) -> None:
    response = await client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")


async def test_metrics_contain_http_requests_total(client: AsyncClient) -> None:
    """Счётчик должен появляться после запроса к инструментированной ручке."""
    await client.get("/openapi.json")

    body = (await client.get("/metrics")).text

    assert "http_requests_total" in body


async def test_metrics_not_in_openapi_schema(client: AsyncClient) -> None:
    """Служебный эндпоинт не должен попадать в публичную OpenAPI-схему."""
    schema = (await client.get("/openapi.json")).json()

    assert "/metrics" not in schema["paths"]
