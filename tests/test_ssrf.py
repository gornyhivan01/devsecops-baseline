"""OWASP A10: Server-Side Request Forgery — валидация исходящих URL."""

from __future__ import annotations

import pytest

from app.core.ssrf import validate_url_for_ssrf


def test_allows_public_https_url() -> None:
    assert validate_url_for_ssrf("https://example.com/path?q=1") == "https://example.com/path?q=1"


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:8080/x",
        "http://127.0.0.1/x",
        "http://169.254.169.254/latest/meta-data",  # link-local: облачные метаданные
        "http://[::1]/x",  # IPv6 loopback
        "http://10.0.0.1/x",  # RFC1918
        "http://192.168.1.1/x",  # RFC1918
        "http://172.16.0.1/x",  # RFC1918
        "ftp://example.com/x",  # недопустимая схема
        "file:///etc/passwd",  # недопустимая схема
    ],
)
def test_blocks_private_and_unsafe_urls(url: str) -> None:
    with pytest.raises(ValueError):
        validate_url_for_ssrf(url)


def test_requires_host() -> None:
    with pytest.raises(ValueError):
        validate_url_for_ssrf("http:///no-host")
