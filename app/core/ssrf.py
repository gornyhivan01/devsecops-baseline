"""Защита от SSRF (Server-Side Request Forgery).

Покрытие OWASP Top 10 2021:

- **A10 Server-Side Request Forgery** — эталонный сервис сам не выполняет
  исходящие HTTP-запросы, поэтому уязвимость отсутствует. Тем не менее модуль
  предоставляет вспомогательную функцию :func:`validate_url_for_ssrf`, которая
  демонстрирует правильную проверку URL перед любым запросом: отклоняются
  схемы, отличные от http/https, и адреса, резолвящиеся во внутренние диапазоны
  (localhost, RFC1918, link-local и пр.). Функция покрыта unit-тестом и может
  быть перенесена в сервисы, которым требуется исходящий HTTP.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

_ALLOWED_SCHEMES = {"http", "https"}


def _is_private_ip(ip: str) -> bool:
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )


def validate_url_for_ssrf(url: str) -> str:
    """Проверяет URL на допустимость для исходящего запроса.

    Возвращает исходный URL, если он безопасен, иначе выбрасывает ``ValueError``.

    Проверки:
      1. схема должна быть http/https;
      2. host должен присутствовать;
      3. host не должен резолвиться во внутренний/loopback/зарезервированный адрес.

    Ограничение: DNS-ребиндинг не покрывается этой функцией; для полной защиты
    нужен отдельный DNS-резолвер с повторной проверкой IP на момент соединения.
    """
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise ValueError(f"Scheme not allowed: {parsed.scheme!r}")
    if not parsed.hostname:
        raise ValueError("URL must include a host")

    # Проверяем и буквальный IP, и результат DNS-резолвинга имени хоста.
    candidates: set[str] = {parsed.hostname}
    if not _looks_like_ip(parsed.hostname):
        try:
            for info in socket.getaddrinfo(parsed.hostname, None):
                address = info[4][0]
                if isinstance(address, str):
                    candidates.add(address)
        except OSError:
            # Не удалось резолвить — не блокируем по этому признаку, но и не пропускаем
            # явно приватный литерал ниже.
            pass

    if any(_is_private_ip(candidate) for candidate in candidates):
        raise ValueError(f"URL resolves to a private/internal address: {parsed.hostname!r}")

    return url


def _looks_like_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False
