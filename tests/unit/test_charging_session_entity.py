import pytest
from uuid import uuid4
from app.domain.entities import ChargingSession
from app.domain.exceptions import (
    SessionAlreadyStoppedError,
    InvalidEnergyValueError,
)


def test_session_starts_with_correct_ids():
    charger_id = uuid4()
    user_id = uuid4()
    session = ChargingSession.start(charger_id=charger_id, user_id=user_id)
    assert session.charger_id == charger_id
    assert session.user_id == user_id
    assert session.started_at is not None
    assert session.ended_at is None
    assert session.energy_kwh == 0.0


def test_session_stop_records_energy():
    session = ChargingSession.start(charger_id=uuid4(), user_id=uuid4())
    session.stop(energy_kwh=12.5)
    assert session.energy_kwh == 12.5
    assert session.ended_at is not None


def test_session_duration_minutes_after_stop():
    session = ChargingSession.start(charger_id=uuid4(), user_id=uuid4())
    session.stop(energy_kwh=12.5)
    assert session.duration_minutes is not None
    assert session.duration_minutes >= 0


def test_session_duration_none_before_stop():
    session = ChargingSession.start(charger_id=uuid4(), user_id=uuid4())
    assert session.duration_minutes is None


def test_session_cannot_stop_twice():
    session = ChargingSession.start(charger_id=uuid4(), user_id=uuid4())
    session.stop(energy_kwh=10.0)
    with pytest.raises(SessionAlreadyStoppedError):
        session.stop(energy_kwh=5.0)


def test_session_rejects_negative_energy():
    session = ChargingSession.start(charger_id=uuid4(), user_id=uuid4())
    with pytest.raises(InvalidEnergyValueError):
        session.stop(energy_kwh=-1.0)


def test_each_session_gets_unique_id():
    session1 = ChargingSession.start(charger_id=uuid4(), user_id=uuid4())
    session2 = ChargingSession.start(charger_id=uuid4(), user_id=uuid4())
    assert session1.id != session2.id