# DevSecOps Baseline — эталонный FastAPI-сервис

[![CI](https://github.com/gornyhivan01/devsecops-baseline/actions/workflows/ci.yml/badge.svg)](https://github.com/gornyhivan01/devsecops-baseline/actions/workflows/ci.yml)

Эталонный репозиторий, демонстрирующий полный путь безопасной поставки
Python-сервиса: от коммита до продакшена. Сейчас выполнен **Этап 1** —
эталонный FastAPI-сервис с практиками безопасности, привязанными к OWASP Top 10
(2021); дальнейшие этапы — в разделе [«План этапов»](#план-этапов).

> Полная архитектура (пайплайн, подпись, ворота релиза, runtime-защита) будет
> достроена на последующих этапах. Сейчас — безопасный фундамент самого сервиса.

## Архитектура

**Стек.** Python 3.12, FastAPI, async SQLAlchemy 2.0 (драйвер `asyncpg`),
PostgreSQL 16, Alembic, Pydantic v2, PyJWT (HS256), Argon2id, structlog, slowapi,
prometheus-fastapi-instrumentator, `fastapi-offline` (ассеты Swagger UI локально).

**Слои и путь запроса.** Запрос проходит middleware сверху вниз, затем эндпоинт,
бизнес-логику и слой доступа к данным:

```
Клиент
  │
  ├─ CORS                     # явный allow-лист origin'ов
  ├─ SecurityHeaders          # самый внешний слой: заголовки на все ответы
  ├─ RateLimit (slowapi)
  │
  ├─ API v1 (app/api/v1/endpoints)   # валидация Pydantic, коды ответов
  │    └─ deps.py                    # сессия БД, текущий пользователь, require_roles
  ├─ Services (app/services)         # бизнес-логика, не знает про HTTP
  ├─ Models / Schemas                # ORM-модели и Pydantic-контракты
  └─ DB (app/db)                     # async engine, sessionmaker, Base
        │
        └─ PostgreSQL 16
```

Правило зависимостей одностороннее — `api → services → db/models`: слой `api` не
работает с ORM напрямую, а `services` не знает про HTTP. Это упрощает
тестирование и замену хранилища.

**Модели данных.**

| Таблица | Ключевые поля | Назначение |
|---|---|---|
| `users` | `id` (UUID), `email` (unique), `full_name`, `hashed_password`, `role`, `is_active`, `created_at`, `updated_at` | пользователи и их роли (`admin` / `user` / `auditor`) |
| `items` | `id` (UUID), `owner_id` → `users.id` (`ON DELETE CASCADE`), `title`, `description`, `created_at`, `updated_at` | пользовательский ресурс с контролем владения |
| `refresh_tokens` | `id`, `user_id` → `users.id` (`ON DELETE CASCADE`), `jti`, `token_hash` (SHA-256), `expires_at`, `revoked_at`, `replaced_by_jti` | refresh-сессии с ротацией и отзывом |

**Аутентификация и авторизация.**

- Access-токен — JWT (HS256), TTL 15 минут, содержит `iss`/`aud`.
- Refresh-токен — TTL 7 дней; в БД хранится только SHA-256 хеш, при обновлении
  старый отзывается (ротация), при `logout` — явный отзыв.
- RBAC — зависимость `require_roles(...)` ограничивает эндпоинт по ролям,
  объектный уровень контролируется владением; чужой объект возвращает **404**
  (анти-энумерация, OWASP A01).

**Конфигурация и наблюдаемость.**

- Настройки — `pydantic-settings` (`app/core/config.py`), обязательный
  `SECRET_KEY ≥ 32` символа, кэш через `lru_cache`.
- Логи — structlog (JSON в проде) с ред-акцией чувствительных полей.
- Метрики — стандартные HTTP на `/metrics`; health — `/health/live` и
  `/health/ready`.
- Документация (`/docs`, `/openapi.json`) включается вне `production`.

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

## Разработка и CI

Пайплайн — [`.github/workflows/ci.yml`](.github/workflows/ci.yml). Задачи
выполняются параллельно и не зависят друг от друга.

### Когда запускается

| Действие | Запуск CI |
|---|---|
| push в `main` | ✅ |
| любой коммит в открытый Pull Request | ✅ |
| push в ветку **без** открытого PR | ❌ не запускается |
| вручную: `Actions → CI → Run workflow` | ✅ (`workflow_dispatch`) |

Практическое следствие: **сначала push ветки, сразу за ним — Pull Request**, тогда
каждый следующий коммит в ветку проверяется автоматически до самого мержа.

### Задачи

| Задача | Что проверяет | Локально |
|---|---|---|
| `ruff` | линтер и форматирование | `uv run ruff check . && uv run black --check .` |
| `mypy` | типы, строгий режим | `uv run mypy app` |
| `pytest` | юнит-тесты и покрытие (порог 75%) | `uv run pytest -m "not integration" --cov=app` |
| `integration` | миграции Alembic и диалектные особенности на PostgreSQL 16 | `docker compose up -d postgres`<br>`INTEGRATION_DATABASE_URL=postgresql+asyncpg://app:app@localhost:5432/app uv run pytest -m integration` |

Все четыре задачи настраиваются в ruleset ветки как обязательные статус-чеки для
мержа в `main`. Отчёт о покрытии выгружается артефактом `coverage-xml`.

### Порядок работы

```bash
git switch -c feature/<краткое-имя>     # или fix/…, docs/…, ci/…
# … изменения …

uv run ruff check . && uv run black --check . && uv run mypy app && uv run pytest

git push -u origin feature/<краткое-имя>
# → открыть Pull Request → ревью → Squash and merge
```

- Ветка `main` защищена: прямые push запрещены, изменения — только через Pull Request.
- Слияние — **Squash and merge**, история линейная (без merge-коммитов).
- Ветка после мержа удаляется.
- Префиксы коммитов: `feat:`, `fix:`, `refactor:`, `docs:`, `ci:`, `test:`, `chore:`.
- Шаблон Pull Request ([`.github/pull_request_template.md`](.github/pull_request_template.md))
  подставляется автоматически и содержит чек-лист проверок.

## Совместная работа

Репозиторий публичный: читать и форкать может любой, права на запись выдаются
приглашением.

**Приглашение:** `Settings → Collaborators and teams → Add people` → GitHub-логин
или e-mail → роль → приглашённый принимает (приглашение действует 7 дней).

| Роль | Возможности | Кому |
|---|---|---|
| Read | чтение, клонирование, PR из форка | наблюдатель, проверяющий |
| Triage | + управление issues/PR без доступа к коду | ведущий задач |
| Write | + push веток и merge PR | разработчик |
| Maintain | + настройки репозитория (без управления участниками) | старший разработчик |
| Admin | полный доступ: секреты, Actions, правила ветки, удаление репозитория | администратор |

Для разработки достаточно **Write**: `Admin` дополнительно позволяет менять правила
ветки и содержимое секретов CI.

**Владельцы кода.** [`.github/CODEOWNERS`](.github/CODEOWNERS) назначает ревьюеров
автоматически: по умолчанию — весь репозиторий, отдельно отмечены критичные модули
(`core/security.py`, `core/security_headers.py`, `core/config.py`, `core/ssrf.py`,
`services/auth_service.py`, `api/`, `db/`, `models/`, `alembic/`). Чтобы ревью
владельца стало обязательным, в ruleset включается **Require review from Code
Owners** вместе с минимум одним одобрением.

**Защита ветки `main`** (ruleset):

- изменения только через Pull Request;
- обязательные статус-чеки `ruff`, `mypy`, `pytest`, `integration`;
- линейная история, запрет force-push и удаления ветки.

Внешним участникам, которым не нужны права на запись, подходит штатный путь
**fork → Pull Request**: работа идёт в личной копии, а изменения попадают в `main`
только после ревью.

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
uv run pytest                       # быстрые тесты (61) + интеграционные пропускаются
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

## Структура проекта

```
.
├── .github/
│   ├── workflows/ci.yml          # пайплайн CI (4 задачи)
│   ├── CODEOWNERS                # владельцы кода для авто-ревью
│   ├── ISSUE_TEMPLATE/           # шаблоны issue (bug, feature)
│   └── pull_request_template.md  # чек-лист Pull Request
├── alembic/
│   ├── env.py                    # асинхронное окружение миграций
│   └── versions/                 # миграции (0001_initial)
├── app/
│   ├── api/
│   │   ├── deps.py               # зависимости: сессия БД, текущий пользователь, RBAC
│   │   ├── responses.py          # типовые ответы об ошибках для OpenAPI
│   │   └── v1/
│   │       ├── endpoints/        # auth, users, items, health
│   │       └── router.py         # сборка префикса /api/v1
│   ├── core/
│   │   ├── config.py             # настройки (pydantic-settings)
│   │   ├── security.py           # Argon2id, JWT
│   │   ├── logging.py            # structlog + ред-акция секретов
│   │   ├── rate_limit.py         # slowapi
│   │   ├── security_headers.py   # заголовки безопасности
│   │   └── ssrf.py               # guard для исходящих URL
│   ├── db/
│   │   ├── base.py               # Declarative Base
│   │   └── session.py            # async engine и sessionmaker (ленивые)
│   ├── models/                   # User, RefreshToken, Item
│   ├── schemas/                  # Pydantic v2 (extra="forbid", валидация)
│   ├── services/                 # бизнес-логика (AuthService, исключения)
│   └── main.py                   # сборка приложения, middleware, метрики
├── docs/owasp-top10.md           # соответствие OWASP Top 10 и допущения
├── tests/
│   ├── integration/              # против реального PostgreSQL (маркер `integration`)
│   └── test_*.py                 # юнит/контракт на SQLite, покрытие OWASP
├── docker-compose.yml            # PostgreSQL 16 для локальной разработки
├── pyproject.toml                # зависимости и настройки инструментов
├── uv.lock                       # зафиксированные версии (воспроизводимость)
└── .env.example                  # шаблон переменных окружения
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
