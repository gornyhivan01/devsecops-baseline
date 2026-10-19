"""Rate limiting через slowapi.

Покрытие OWASP Top 10 2021:

- **A04 Insecure Design** и **A07 Identification and Authentication Failures** —
  ограничение частоты запросов к точкам входа (login/register) и API в целом
  снижает поверхность для брутфорса и credential stuffing.

Значения по умолчанию берутся из настроек ``RATE_LIMIT_*``. В проде хранилище
лимитов следует вынести в Redis поверх slowapi, чтобы ограничения были общими
для всех реплик сервиса.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[get_settings().rate_limit_default],
    headers_enabled=True,
)
