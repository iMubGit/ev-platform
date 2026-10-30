# EV Platform API

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)
![CI](https://github.com/iMubGit/ev-platform/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-blue)

**EV charging backend prototype**

A FastAPI service for managing chargers, charging sessions, and telemetry. It uses a layered architecture and in-memory repositories, so it is a prototype rather than a production-ready charging platform.

## Features

- Clean / Hexagonal architecture
- JWT authentication for charger, session, and telemetry API routes
- Session ownership checked against the authenticated token
- Domain business rules enforced by entities
- Custom exceptions mapped to HTTP responses
- Paginated charger listing
- In-memory repositories for development and tests
- GitHub Actions test workflow

## Architecture

```text
Domain         → Entities, business rules, repository interfaces
Application    → Use cases
Infrastructure → In-memory repository implementations
Interfaces     → FastAPI routes, schemas, dependency injection
```

## Tech stack

| Layer | Technology |
|---|---|
| API | FastAPI + Pydantic |
| Auth | python-jose + passlib (JWT) |
| Database | In-memory repositories (persistent database not yet connected) |
| Testing | pytest + pytest-asyncio + HTTPX |
| CI | GitHub Actions |
| Runtime | Python 3.11 |

## Quick start

```bash
git clone https://github.com/iMubGit/ev-platform.git
cd ev-platform

python -m venv venv
# Windows PowerShell: .\venv\Scripts\Activate.ps1
# macOS/Linux: source venv/bin/activate

pip install -e .
pip install pydantic-settings "python-jose[cryptography]" "passlib[bcrypt]" "bcrypt==4.0.1" httpx pytest pytest-asyncio

# Create your local environment file
cp .env.example .env
# Windows PowerShell: Copy-Item .env.example .env
```

Before starting the API, edit `.env`:

1. Generate a signing key:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```
   Put the generated value in `SECRET_KEY`. Keep it private and stable between restarts. Changing this key invalidates all tokens issued with the previous key.
2. Generate an administrator password hash:
   ```bash
   python -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('YOUR-STRONG-PASSWORD'))"
   ```
   Put the generated hash in `ADMIN_PASSWORD_HASH`. Set `ADMIN_USERNAME` and `ADMIN_USER_ID` as appropriate.

The API will not start without a `SECRET_KEY` of at least 32 characters. Login returns 503 until an administrator password hash is configured. Do not commit `.env`.

Start the API:

```bash
uvicorn app.main:app --reload
```

- API docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

## Authentication

Obtain a token using the administrator credentials configured in `.env`:

```bash
curl -X POST http://127.0.0.1:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "<your-configured-password>"}'
```

Send the returned token in the `Authorization` header:

```text
Authorization: Bearer <token>
```

## Example workflow

1. Obtain a token using the authentication example above.
2. Register a charger:

```bash
curl -X POST http://127.0.0.1:8000/chargers/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"serial_number": "EV-1001", "location": "Abidjan"}'
```

3. Start a charging session:

```bash
curl -X POST http://127.0.0.1:8000/sessions/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"charger_id": "<uuid-from-register>"}'
```

4. Submit telemetry:

```bash
curl -X POST http://127.0.0.1:8000/telemetry/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"charger_id": "<uuid>", "voltage": 400.0, "current": 32.0, "temperature": 45.0}'
```

5. Stop the session:

```bash
curl -X POST http://127.0.0.1:8000/sessions/<session-uuid>/stop \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"energy_kwh": 12.5}'
```

## API endpoints

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | `/auth/token` | Obtain JWT token | No |
| POST | `/chargers/` | Register charger | Yes |
| GET | `/chargers/` | List chargers | Yes |
| GET | `/chargers/{id}` | Get charger details | Yes |
| DELETE | `/chargers/{id}` | Delete charger | Yes |
| POST | `/sessions/` | Start charging session | Yes |
| POST | `/sessions/{id}/stop` | Stop charging session (owner only) | Yes |
| POST | `/telemetry/` | Ingest telemetry | Yes |
| GET | `/health` | Health check | No |

Missing, invalid, expired, or malformed bearer tokens receive HTTP 401.

## Tests

```bash
pytest tests/unit/ -v
```

The tests cover domain rules, use cases, and API authentication boundaries.

## Known limitations

- The configured administrator is a single demo account; user registration, roles, and fine-grained permissions are not implemented.
- Telemetry currently accepts the configured JWT. A real charger deployment should use separate device credentials per charger, not a shared administrator token.
- Repositories are in-memory. Data is lost when the application process restarts.
- A persistent database, production deployment configuration, monitoring, and operational controls are still required before real-world use.

## License

[MIT](LICENSE)
