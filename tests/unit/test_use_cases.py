import pytest
from uuid import uuid4

from app.application.use_cases import (
    StartChargingUseCase,
    StartChargingInput,
    StopChargingUseCase,
    StopChargingInput,
    IngestTelemetryUseCase,
    IngestTelemetryInput,
)
from app.infrastructure.database.repositories import (
    InMemoryChargerRepository,
    InMemorySessionRepository,
    InMemoryTelemetryRepository,
)
from app.domain.entities import Charger
from app.domain.exceptions import (
    ChargerNotFoundError,
    ChargerNotAvailableError,
    SessionNotFoundError,
    TelemetryChargerNotFoundError,
)


@pytest.fixture
def charger_repo():
    return InMemoryChargerRepository()


@pytest.fixture
def session_repo():
    return InMemorySessionRepository()


@pytest.fixture
def telemetry_repo():
    return InMemoryTelemetryRepository()


@pytest.fixture
def start_use_case(charger_repo, session_repo):
    return StartChargingUseCase(
        charger_repo=charger_repo,
        session_repo=session_repo,
    )


@pytest.fixture
def stop_use_case(charger_repo, session_repo):
    return StopChargingUseCase(
        charger_repo=charger_repo,
        session_repo=session_repo,
    )


@pytest.fixture
def telemetry_use_case(charger_repo, telemetry_repo):
    return IngestTelemetryUseCase(
        charger_repo=charger_repo,
        telemetry_repo=telemetry_repo,
    )


@pytest.mark.asyncio
async def test_start_charging_success(start_use_case, charger_repo):
    charger = Charger.create("SN-001", "Lagos Island")
    await charger_repo.save(charger)
    result = await start_use_case.execute(
        StartChargingInput(charger_id=charger.id, user_id=uuid4())
    )
    assert result.charger_id == charger.id
    assert result.session_id is not None


@pytest.mark.asyncio
async def test_start_charging_charger_not_found(start_use_case):
    with pytest.raises(ChargerNotFoundError):
        await start_use_case.execute(
            StartChargingInput(charger_id=uuid4(), user_id=uuid4())
        )


@pytest.mark.asyncio
async def test_start_charging_charger_not_available(start_use_case, charger_repo):
    charger = Charger.create("SN-001", "Lagos Island")
    await charger_repo.save(charger)
    await start_use_case.execute(
        StartChargingInput(charger_id=charger.id, user_id=uuid4())
    )
    with pytest.raises(ChargerNotAvailableError):
        await start_use_case.execute(
            StartChargingInput(charger_id=charger.id, user_id=uuid4())
        )


@pytest.mark.asyncio
async def test_stop_charging_success(start_use_case, stop_use_case, charger_repo):
    charger = Charger.create("SN-001", "Lagos Island")
    await charger_repo.save(charger)
    owner_id = uuid4()
    start_result = await start_use_case.execute(
        StartChargingInput(charger_id=charger.id, user_id=owner_id)
    )
    stop_result = await stop_use_case.execute(
        StopChargingInput(
            session_id=start_result.session_id,
            user_id=owner_id,
            energy_kwh=12.5,
        )
    )
    assert stop_result.energy_kwh == 12.5
    assert stop_result.duration_minutes >= 0


@pytest.mark.asyncio
async def test_stop_charging_rejects_another_users_session(
    start_use_case, stop_use_case, charger_repo
):
    charger = Charger.create("SN-SEC-001", "Osogbo")
    await charger_repo.save(charger)

    owner_id = uuid4()
    other_user_id = uuid4()
    start_result = await start_use_case.execute(
        StartChargingInput(charger_id=charger.id, user_id=owner_id)
    )

    with pytest.raises(SessionNotFoundError):
        await stop_use_case.execute(
            StopChargingInput(
                session_id=start_result.session_id,
                user_id=other_user_id,
                energy_kwh=12.5,
            )
        )


@pytest.mark.asyncio
async def test_stop_charging_session_not_found(stop_use_case):
    with pytest.raises(SessionNotFoundError):
        await stop_use_case.execute(
            StopChargingInput(
                session_id=uuid4(),
                user_id=uuid4(),
                energy_kwh=10.0,
            )
        )


@pytest.mark.asyncio
async def test_ingest_telemetry_success(telemetry_use_case, charger_repo):
    charger = Charger.create("SN-001", "Lagos Island")
    await charger_repo.save(charger)
    result = await telemetry_use_case.execute(
        IngestTelemetryInput(
            charger_id=charger.id,
            voltage=400.0,
            current=32.0,
            temperature=45.0,
        )
    )
    assert result.power_kw == 12.8
    assert result.charger_id == charger.id


@pytest.mark.asyncio
async def test_ingest_telemetry_charger_not_found(telemetry_use_case):
    with pytest.raises(TelemetryChargerNotFoundError):
        await telemetry_use_case.execute(
            IngestTelemetryInput(
                charger_id=uuid4(),
                voltage=400.0,
                current=32.0,
                temperature=45.0,
            )
        )
