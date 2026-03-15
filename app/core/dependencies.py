from functools import lru_cache
from app.infrastructure.database.repositories import (
    InMemoryChargerRepository,
    InMemorySessionRepository,
    InMemoryTelemetryRepository,
)
from app.application.use_cases import (
    StartChargingUseCase,
    StopChargingUseCase,
    IngestTelemetryUseCase,
)


# Singleton repository instances
# These live for the lifetime of the application
charger_repo = InMemoryChargerRepository()
session_repo = InMemorySessionRepository()
telemetry_repo = InMemoryTelemetryRepository()


# Dependency functions for FastAPI
def get_charger_repo() -> InMemoryChargerRepository:
    return charger_repo


def get_session_repo() -> InMemorySessionRepository:
    return session_repo


def get_telemetry_repo() -> InMemoryTelemetryRepository:
    return telemetry_repo


def get_start_charging_use_case() -> StartChargingUseCase:
    return StartChargingUseCase(
        charger_repo=charger_repo,
        session_repo=session_repo,
    )


def get_stop_charging_use_case() -> StopChargingUseCase:
    return StopChargingUseCase(
        charger_repo=charger_repo,
        session_repo=session_repo,
    )


def get_ingest_telemetry_use_case() -> IngestTelemetryUseCase:
    return IngestTelemetryUseCase(
        charger_repo=charger_repo,
        telemetry_repo=telemetry_repo,
    )