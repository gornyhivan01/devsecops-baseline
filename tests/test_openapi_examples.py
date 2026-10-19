"""Проверка, что примеры запросов и описания ошибок присутствуют в OpenAPI.

Эти данные отображаются в Swagger UI (`/docs`), поэтому тест защищает от
случайного удаления примеров при рефакторинге схем.
"""

from __future__ import annotations

from httpx import AsyncClient


async def test_request_schemas_have_examples(client: AsyncClient) -> None:
    spec = (await client.get("/openapi.json")).json()
    schemas = spec["components"]["schemas"]

    for name in (
        "RegisterRequest",
        "LoginRequest",
        "RefreshRequest",
        "ItemCreate",
        "ItemUpdate",
        "UserUpdate",
    ):
        assert schemas[name].get("examples"), f"нет примеров для схемы {name}"


async def test_register_body_is_documented(client: AsyncClient) -> None:
    spec = (await client.get("/openapi.json")).json()
    body = spec["paths"]["/api/v1/auth/register"]["post"]["requestBody"]
    assert body["content"]["application/json"]["schema"]["$ref"].endswith("/RegisterRequest")


async def test_error_responses_are_documented(client: AsyncClient) -> None:
    spec = (await client.get("/openapi.json")).json()

    login = spec["paths"]["/api/v1/auth/login"]["post"]["responses"]
    assert "401" in login
    assert "429" in login  # rate limiting описан в документации

    item_get = spec["paths"]["/api/v1/items/{item_id}"]["get"]["responses"]
    assert "404" in item_get  # анти-энумерация: чужой объект -> 404
