# EV Platform API

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)
![Tests](https://img.shields.io/badge/tests-22%20passed-brightgreen)
![CI](https://github.com/iMubGit/ev-platform/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-blue)

**Production-grade backend for EV charging infrastructure**
Clean Architecture FastAPI service for chargers, sessions, and real-time telemetry.

##  Features

- Clean / Hexagonal architecture — domain has zero framework imports
- JWT auth — user identity from token (prevents impersonation)
- Strict domain business rules enforced at entity level
- Custom exceptions → automatic HTTP status mapping
- Pagination on all list endpoints
- In-memory repositories (easy PostgreSQL/Redis swap)
- 22 focused unit tests
- GitHub Actions CI

##  Architecture

Follows **Clean Architecture** / Ports & Adapters:
```text
Domain        → Entities, value objects, business rules, repository interfaces
Application   → Use cases / services
Infrastructure→ Concrete adapters (in-memory → PostgreSQL / Redis)
Interfaces    → FastAPI routes, Pydantic schemas, dependency injection
```

##  Tech Stack

| Layer | Technology |
|------------|-----------------------------------|
| API | FastAPI + Pydantic v2 |
| Auth | python-jose + passlib (JWT) |
| ORM | SQLAlchemy (planned) |
| Cache/Stream | Redis (planned) |
| Testing | pytest + pytest-asyncio |
| CI | GitHub Actions |
| Runtime | Python 3.11 |

## 📂 Project Structure
```text
ev-platform/
├── app/
│   ├── core/               # settings, security, deps
│   ├── domain/             # entities, repo interfaces, exceptions
│   ├── application/        # use cases
│   ├── infrastructure/     # repo implementations
│   └── interfaces/         # FastAPI routes & schemas
├── tests/
│   └── unit/
├── .github/workflows/
└── pyproject.toml
```

##  Quick Start
```bash
git clone https://github.com/iMubGit/ev-platform.git
cd ev-platform

python -m venv venv
source venv/Scripts/activate        # Windows Git Bash
# source venv/bin/activate          # Linux/macOS

pip install -e .
pip install pydantic-settings "python-jose[cryptography]" "passlib[bcrypt]" "bcrypt==4.0.1"

uvicorn app.main:app --reload
```

→ Docs: http://127.0.0.1:8000/docs
→ Health: http://127.0.0.1:8000/health

##  Authentication Example
```bash
curl -X POST http://127.0.0.1:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "secret"}'
```

##  Example Workflow
```bash
# 1. Register charger
curl -X POST http://127.0.0.1:8000/chargers/ \
  -H "Content-Type: application/json" \
  -d '{"serial_number": "EV-1001", "location": "Abidjan"}'

# 2. Get token
curl -X POST http://127.0.0.1:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "secret"}'

# 3. Start session
curl -X POST http://127.0.0.1:8000/sessions/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"charger_id": "<uuid-from-register>"}'

# 4. Send telemetry
curl -X POST http://127.0.0.1:8000/telemetry/ \
  -H "Content-Type: application/json" \
  -d '{"charger_id": "<uuid>", "voltage": 400.0, "current": 32.0, "temperature": 45.0}'

# 5. Stop session
curl -X POST http://127.0.0.1:8000/sessions/<session-uuid>/stop \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"energy_kwh": 12.5}'
```

##  API Endpoints

| Method | Endpoint | Description | Auth |
|--------|---------------------------|---------------------------------|------|
| POST | `/auth/token` | Obtain JWT token | No |
| POST | `/chargers/` | Register new charger | No |
| GET | `/chargers/` | List chargers (paginated) | No |
| GET | `/chargers/{id}` | Get charger details | No |
| DELETE | `/chargers/{id}` | Delete charger | No |
| POST | `/sessions/` | Start charging session | Yes |
| POST | `/sessions/{id}/stop` | Stop charging session | Yes |
| POST | `/telemetry/` | Ingest telemetry reading | No |
| GET | `/health` | Health check | No |

##  Tests
```bash
pytest tests/unit/ -v
# or with coverage: pytest --cov=app tests/unit/
```

→ 22 passed (entities, rules, use cases)

##  Domain Business Rules

- Charger must be AVAILABLE to start session
- Cannot stop unless in CHARGING state
- Session cannot be stopped twice
- All energy/power readings ≥ 0
- Power (kW) = voltage × current / 1000
- User ownership enforced via JWT — never request body

##  Architecture Decisions

| Decision | Reason |
|---------------------------------|------------------------------------------------------------------------|
| In-memory repositories | Proves full decoupling — zero domain changes when switching to DB |
| Custom domain exceptions | Clean mapping to HTTP (404, 409, etc.) via FastAPI handlers |
| Pagination on lists | Scalable by default — prevents memory and performance issues |
| User ID from JWT only | Secure — blocks session hijacking and impersonation |

## 📄 License

[MIT](LICENSE)

---

Built with Python · Clean Architecture · Open to remote and relocation opportunities.
PRs, issues, and stars welcome! 