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

Redis must also be running for login protection. By default, the API asks for a CAPTCHA after more than 5 attempts for the same username/IP combination, or more than 20 attempts from one IP, within a 15-minute window. These counters count all login attempts. The API does not hard-lock a username/IP pair or shared IP: after the CAPTCHA threshold, the client must send a verified Turnstile token with that login request. A valid CAPTCHA permits that one request to proceed to password checking; it does not reset the IP counter. After CAPTCHA verification, a separate per-IP limit allows up to 30 password checks in a one-hour window by default. Exceeding that limit returns HTTP 429 with a retry delay. Configure `LOGIN_CAPTCHA_VERIFIED_ATTEMPTS_PER_IP` and `LOGIN_CAPTCHA_VERIFIED_WINDOW_SECONDS` to adjust this protection. Failed credentials are also counted by username and across the platform for monitoring only. Reaching the default username alert threshold of 5 or global alert threshold of 500 writes a warning to the application log; these monitoring counters do not freeze accounts or block other users. Configure `TURNSTILE_SECRET_KEY` on the backend. The future browser client must use a public Turnstile site key, create the widget with action `login`, and send its response as `captcha_token` in the `/auth/token` JSON body. The site key is not a backend secret; the secret key must never be exposed to the client or committed to Git. If a CAPTCHA is required but the backend secret is missing, or Cloudflare cannot be reached, login fails with HTTP 503 rather than bypassing verification. If the token is missing or invalid, the API returns HTTP 403. Optionally set `TURNSTILE_EXPECTED_HOSTNAME` to enforce the expected hostname. Configure `REDIS_URL`, `LOGIN_RATE_LIMIT_*`, and `LOGIN_CAPTCHA_*` settings in `.env` as needed.

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
| POST | `/auth/token` | Obtain JWT token (Turnstile required after suspicious activity) | No |
| POST | `/chargers/` | Register charger | Yes |
| GET | `/chargers/` | List chargers | Yes |
| GET | `/chargers/{id}` | Get charger details | Yes |
| DELETE | `/chargers/{id}` | Delete charger | Yes |
| POST | `/sessions/` | Start charging session | Yes |
| POST | `/sessions/{id}/stop` | Stop charging session (owner only) | Yes |
| POST | `/telemetry/` | Ingest telemetry | Yes |
| GET | `/health` | Health check | No |

Missing, invalid, expired, or malformed bearer tokens receive HTTP 401. Login requests may receive HTTP 403 when a Turnstile challenge is required or fails.

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
