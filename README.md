\# EV Platform API



!\[Python](https://img.shields.io/badge/Python-3.11-blue)

!\[FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)

!\[Tests](https://img.shields.io/badge/tests-22%20passed-brightgreen)

!\[CI](https://github.com/iMubGit/ev-platform/actions/workflows/ci.yml/badge.svg)

!\[License](https://img.shields.io/badge/license-MIT-blue)



A production-grade EV Charging Infrastructure Backend built with Clean Architecture, FastAPI, and Python 3.11.



\## Architecture



This project follows Clean Architecture (Hexagonal / Ports \& Adapters):

```

Domain        → Pure Python entities and business rules

Application   → Use cases orchestrating domain logic

Infrastructure → Repository implementations (in-memory / PostgreSQL)

Interfaces    → FastAPI routes, schemas, and HTTP handlers

```



Business logic is completely independent of FastAPI, SQLAlchemy, and any infrastructure concern. The domain layer has zero framework imports.



\## Tech Stack



\- Python 3.11

\- FastAPI

\- Pydantic v2 + pydantic-settings

\- JWT Authentication (python-jose + passlib)

\- SQLAlchemy (planned — PostgreSQL)

\- Redis (planned — telemetry streams)

\- Pytest + pytest-asyncio

\- GitHub Actions CI



\## Project Structure

```

app/

├── core/           Settings, security, dependencies

├── domain/         Entities, repository interfaces, exceptions

├── application/    Use cases

├── infrastructure/ Repository implementations

└── interfaces/     API routes and schemas

```



\## Running Locally

```bash

\# Clone and setup

git clone https://github.com/iMubGit/ev-platform.git

cd ev-platform

python -m venv venv

source venv/Scripts/activate   # Windows Git Bash

pip install -e .

pip install pydantic-settings "python-jose\[cryptography]" "passlib\[bcrypt]" "bcrypt==4.0.1"



\# Start the server

uvicorn app.main:app --reload

```



API docs available at: http://127.0.0.1:8000/docs



\## Authentication

```bash

\# Get a token

curl -X POST http://127.0.0.1:8000/auth/token \\

&#x20; -H "Content-Type: application/json" \\

&#x20; -d '{"username": "admin", "password": "secret"}'



\# Use the token on protected endpoints

curl -X POST http://127.0.0.1:8000/sessions/ \\

&#x20; -H "Authorization: Bearer <token>" \\

&#x20; -H "Content-Type: application/json" \\

&#x20; -d '{"charger\_id": "<uuid>"}'

```



\## API Endpoints



| Method | Endpoint | Description | Auth Required |

|--------|----------|-------------|---------------|

| POST | /auth/token | Get JWT token | No |

| POST | /chargers/ | Register charger | No |

| GET | /chargers/ | List all chargers | No |

| GET | /chargers/{id} | Get charger by ID | No |

| DELETE | /chargers/{id} | Delete charger | No |

| POST | /sessions/ | Start charging session | Yes |

| POST | /sessions/{id}/stop | Stop charging session | Yes |

| POST | /telemetry/ | Ingest telemetry event | No |

| GET | /health | Health check | No |



\## Running Tests

```bash

pytest tests/unit/ -v

```



Expected: 22 passed



\## Domain Business Rules



\- Charger must be AVAILABLE before a session can start

\- Charger cannot stop charging if not in CHARGING state

\- Session cannot be stopped twice

\- Energy readings must be non-negative

\- Power calculation: voltage × current / 1000 = kW

\- User identity is extracted from JWT token — not passed in request body



\## Architecture Decisions



Why in-memory repositories?

Demonstrates the Clean Architecture boundary — use cases and domain are completely decoupled from persistence. Swapping to SQLAlchemy requires zero changes to domain or application layers.



Why custom exceptions instead of ValueError?

Domain exceptions map directly to HTTP status codes via FastAPI exception handlers. EntityNotFoundError → 404, BusinessRuleViolationError → 409.



Why pagination on all list methods?

Production systems cannot load unbounded result sets into memory. Default limit=100 with offset ensures scalability from day one.



Why JWT user\_id extraction from token?

Session ownership is determined by the authenticated user, not by client-supplied data. This prevents a user from creating sessions on behalf of other users.

