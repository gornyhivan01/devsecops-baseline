# DevSecOps Baseline — эталонный FastAPI-сервис

[![CI](https://github.com/gornyhivan01/devsecops-baseline/actions/workflows/ci.yml/badge.svg)](https://github.com/gornyhivan01/devsecops-baseline/actions/workflows/ci.yml)

Эталонный репозиторий, демонстрирующий полный путь безопасной поставки
Python-сервиса: от коммита до продакшена. Сейчас выполнен **Этап 1** —
эталонный FastAPI-сервис с практиками безопасности, привязанными к OWASP Top 10
(2021); дальнейшие этапы — в разделе [«План этапов»](#план-этапов).

> Полная архитектура (пайплайн, подпись, ворота релиза, runtime-защита) будет
> достроена на последующих этапах. Сейчас — безопасный фундамент самого сервиса.

## План этапов

Проект строится поэтапно: от безопасного сервиса до подписанной поставки.
Нумерация этапов 4 и 6 соответствует ссылкам в
[`docs/owasp-top10.md`](docs/owasp-top10.md).

| Этап | Содержание | Результат | Статус |
|---|---|---|---|
| **1. Сервис** | FastAPI + async SQLAlchemy 2.0 + PostgreSQL, JWT/refresh, RBAC, rate limiting, security-заголовки, структурированные логи, стандартные HTTP-метрики, OWASP Top 10, unit- и интеграционные тесты | Безопасный фундамент приложения | ✅ выполнен |
| **2. Контейнеризация** | multi-stage `Dockerfile`, запуск от non-root, `HEALTHCHECK`, `.dockerignore`, compose «app + postgres» | Воспроизводимый образ сервиса | ⬜ не начат |
| **3. CI** | GitHub Actions: `ruff`, `black`, `mypy`, unit-тесты с покрытием и интеграционные тесты с сервисным PostgreSQL, кэш `uv` | Автоматические проверки на каждый PR | ✅ выполнен |
| **4. SCA/SAST/SBOM** | `pip-audit` / `osv-scanner`, secret scanning, CodeQL, CycloneDX SBOM | Нет известных уязвимостей и утечек секретов | ⬜ не начат |
| **5. CD** | staging-окружение, `alembic upgrade head` в пайплайне, smoke-тесты, ограничение доступа к `/metrics`, стратегия отката | Воспроизводимый деплой | ⬜ не начат |
| **6. Supply chain** | Cosign/Sigstore-подпись образов, SLSA provenance, проверка подписи перед деплоем, RS256/keyless JWT | Подписанная и проверяемая поставка | ⬜ не начат |
| **7. Runtime (опционально)** | Prometheus-скрейпинг, дашборды и алерты; Falco, seccomp/AppArmor, NetworkPolicy | Защита и наблюдаемость в рантайме | ⬜ не начат |

**Принцип порядка:** сначала артефакт (2), затем автоматические ворота качества (3),
сканирование (4), доставка (5) и подпись того, что доставляем (6).

**Метрики и наблюдаемость.** На этапе 1 сервис отдаёт только стандартные HTTP-метрики
(запросы, латентность, in-flight, размер ответа) и не содержит бизнес-метрик.
Скрейпинг, дашборды и алерты появляются на этапе 7, а ограничение доступа к `/metrics`
(внутренняя сеть, отдельный порт, auth/mTLS) — на этапе 5.

## CI

Пайплайн (`.github/workflows/ci.yml`) запускается на каждый push в `main` и на
каждый Pull Request.

| Задача | Что проверяет | Локально |
|---|---|---|
| `ruff` | линтер и форматирование | `uv run ruff check . && uv run black --check .` |
| `mypy` | типы, строгий режим | `uv run mypy app` |
| `pytest` | юнит-тесты и покрытие (порог 75%) | `uv run pytest -m "not integration" --cov=app` |
| `integration` | миграции Alembic и диалектные особенности на PostgreSQL 16 | `docker compose up -d postgres`<br>`INTEGRATION_DATABASE_URL=postgresql+asyncpg://app:app@localhost:5432/app uv run pytest -m integration` |

Все четыре задачи — обязательные статус-чеки для мержа в `main` (настраиваются в
ruleset ветки). Покрытие выгружается артефактом `coverage-xml`.

## Возможности

- **FastAPI + async SQLAlchemy 2.0 + PostgreSQL** (драйвер `asyncpg`), миграции Alembic.
- **JWT-аутентификация**: короткоживущий access-токен (15 мин) и refresh-токены с
  ротацией и отзывом (7 дней, хранится только SHA-256 хеш).
- **RBAC-авторизация** на уровне эндпоинтов (`admin`, `user`, `auditor`) и
  объектный контроль владения ресурсами.
- **Rate limiting** (slowapi), **CORS** с явным allow-листом и **security-заголовки**.
- **Структурированное логирование** structlog с обязательной ред-акцией секретов.
- **Prometheus-метрики** (стандартные HTTP) на `/metrics` и health-эндпоинты `/health/live`, `/health/ready`.
- **Документация без CDN**: Swagger UI отдаётся самим сервисом (пакет `fastapi-offline`),
  работает офлайн, не делает запросов к сторонним доменам и содержит примеры
  запросов/ответов и описание кодов ошибок.
- **Охват OWASP Top 10** тестом или пояснением — см. [`docs/owasp-top10.md`](docs/owasp-top10.md).
- **CI на GitHub Actions**: `ruff` + `black`, `mypy` (strict), юнит-тесты с покрытием
  и интеграционные тесты против сервисного PostgreSQL.

## Требования

- Python **3.12** (см. `.python-version`).
- Менеджер зависимостей [`uv`](https://docs.astral.sh/uv/).
- Docker + Docker Compose — только для локального PostgreSQL.

## Быстрый старт

```bash
# 1. Поднять PostgreSQL локально
docker compose up -d postgres

# 2. Создать окружение и сгенерировать SECRET_KEY
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(64))"   # вставьте в SECRET_KEY

# 3. Установить зависимости
uv sync

# 4. Применить миграции
uv run alembic upgrade head

# 5. Запустить сервис
uv run uvicorn app.main:app --reload
```

После старта доступны:

- Swagger UI — <http://localhost:8000/docs>
- Схема OpenAPI — <http://localhost:8000/openapi.json>
- Health — <http://localhost:8000/health/live>, <http://localhost:8000/health/ready>
- Метрики — <http://localhost:8000/metrics>

> Документация (`/docs`, `/openapi.json`) включается вне `production`. При
> `ENVIRONMENT=production` она отключается намеренно (OWASP A05).

## Переменные окружения

Полный перечень — в [`.env.example`](.env.example). Ключевые:

| Переменная | Назначение | По умолчанию |
|---|---|---|
| `SECRET_KEY` | Ключ подписи JWT, **≥ 32 символа** (обязательна) | — |
| `DATABASE_URL` | Строка подключения SQLAlchemy (async) | `postgresql+asyncpg://app:app@localhost:5432/app` |
| `DATABASE_POOL_DISABLED` | Отключить пул соединений (`NullPool`) — для тестов/serverless | `false` |
| `ENVIRONMENT` | `development` / `staging` / `production` | `development` |
| `DEBUG` | Подробный вывод SQL и логи | `false` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | TTL access-токена | `15` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | TTL refresh-токена | `7` |
| `CORS_ORIGINS` | Разрешённые origins (через запятую или JSON-список) | `http://localhost:3000` |
| `RATE_LIMIT_DEFAULT` | Лимит для обычных эндпоинтов | `100/minute` |
| `RATE_LIMIT_AUTH` | Лимит для `login`/`register` | `5/minute` |
| `LOG_LEVEL` / `LOG_JSON` | Уровень и формат логов | `INFO` / `true` |

## API (v1)

| Метод | Путь | Доступ |
|---|---|---|
| GET | `/health/live`, `/health/ready` | публичный |
| GET | `/metrics` | публичный (ограничение — этап 5) |
| POST | `/api/v1/auth/register` | публичный (rate limit) |
| POST | `/api/v1/auth/login` | публичный (rate limit) |
| POST | `/api/v1/auth/refresh` | по refresh-токену |
| POST | `/api/v1/auth/logout` | access + refresh |
| GET / PATCH | `/api/v1/users/me` | аутентифицированный |
| GET | `/api/v1/users` | `admin` |
| PATCH | `/api/v1/users/{user_id}` | `admin` |
| GET | `/api/v1/items` | владелец своих; `admin`/`auditor` — всех |
| POST | `/api/v1/items` | `admin`, `user` |
| GET | `/api/v1/items/{item_id}` | владелец, `admin`, `auditor` |
| PUT / DELETE | `/api/v1/items/{item_id}` | владелец, `admin` |

Чужой объект возвращает **404** (анти-энумерация, OWASP A01).

### Первый администратор

Регистрация всегда создаёт пользователя с ролью `user`. Первого администратора
назначают вручную:

```bash
docker compose exec postgres psql -U app -d app \
  -c "UPDATE users SET role='admin' WHERE email='you@example.com';"
```

## База данных и миграции

```bash
docker compose up -d postgres       # приложение отдельно
uv run alembic upgrade head         # накатить схему
uv run alembic downgrade -1         # откат на одну миграцию
uv run alembic revision -m "..."    # новая миграция
```

## Тесты

Быстрый слой (юнит/контракт) — на SQLite (файл) с `NullPool`
(`DATABASE_POOL_DISABLED=true`) и пониженной стоимостью Argon2id: PostgreSQL для
прогона не требуется.

```bash
uv run pytest                       # быстрые тесты (54) + интеграционные пропускаются
uv run pytest -q                    # краткий вывод
uv run pytest --cov=app             # с покрытием (pytest-cov)
```

Отдельный **интеграционный слой** (маркер `integration`, 7 тестов) выполняется
против **реального PostgreSQL** и закрывает «слепые зоны» SQLite: проверку
миграций Alembic (`upgrade head` / `downgrade base`), диалектные особенности
(`ILIKE` для кириллицы, `timestamptz`) и каскады внешних ключей на уровне СУБД.

```bash
docker compose up -d postgres
INTEGRATION_DATABASE_URL=postgresql+asyncpg://app:app@localhost:5432/app \
    uv run pytest -m integration
```

На сервере создаётся **временная** база `devsecops_it_*`, на неё накатываются
миграции; по завершении она удаляется. Рабочая база приложения не затрагивается,
а без переменной `INTEGRATION_DATABASE_URL` интеграционные тесты пропускаются.

## Качество кода

```bash
uv run ruff check .        # линтер (E/F/I/B/UP/S/C4/ASYNC)
uv run ruff format .       # форматирование
uv run black --check .     # проверка форматирования
uv run mypy app            # строгая проверка типов (strict)
```

## Структура

```
app/
  core/        # config, security (Argon2id + JWT), logging, rate limit,
               # security_headers, ssrf
  db/          # async engine/session (ленивый движок), Base
  models/      # User, RefreshToken, Item
  schemas/     # Pydantic v2 (extra="forbid", валидация)
  services/    # слой бизнес-логики (AuthService, exceptions)
  api/         # deps (RBAC), v1 endpoints (auth, users, items, health), роутеры
  main.py      # точка входа, middleware, метрики
alembic/       # асинхронное окружение и миграции
tests/         # покрытие OWASP Top 10 и компонентов (SQLite)
  integration/ # тесты против реального PostgreSQL (маркер `integration`)
docs/          # расшифровка пунктов OWASP
```

## Практики безопасности (кратко)

| OWASP Top 10 2021 | Реализация |
|---|---|
| A01 Broken Access Control | RBAC (`require_roles`) + объектный доступ по владельцу |
| A02 Cryptographic Failures | Argon2id для паролей, подписанный JWT с `iss`/`aud` |
| A03 Injection | параметризованный SQLAlchemy (без конкатенации) |
| A04 Insecure Design | rate limiting, строгая валидация с `extra="forbid"` |
| A05 Security Misconfiguration | security-заголовки, CORS allow-list, HSTS/CSP (strict для API, `'self'` для docs); ассеты docs — локально |
| A06 Vulnerable Components | зафиксированный lock-файл (`uv.lock`); docs-ассеты из pinned-пакета вместо плавающего CDN; SCA на этапе 4 |
| A07 Auth Failures | короткий TTL access, ротация + отзыв refresh |
| A08 Data Integrity Failures | закладывается в этап 6 (Cosign/SLSA) |
| A09 Logging Failures | структурированные логи без секретов, метрики |
| A10 SSRF | guard `validate_url_for_ssrf` + пояснение |

Подробное соответствие и допущения — в [`docs/owasp-top10.md`](docs/owasp-top10.md).
