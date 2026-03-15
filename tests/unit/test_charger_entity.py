import pytest
from uuid import uuid4
from app.domain.entities import Charger, ChargerStatus
from app.domain.exceptions import (
    ChargerNotAvailableError,
    ChargerNotChargingError,
)


def test_charger_created_with_available_status():
    charger = Charger.create("SN-001", "Lagos Island")
    assert charger.status == ChargerStatus.AVAILABLE
    assert charger.serial_number == "SN-001"
    assert charger.location == "Lagos Island"
    assert charger.id is not None


def test_charger_start_charging():
    charger = Charger.create("SN-001", "Lagos Island")
    charger.start_charging()
    assert charger.status == ChargerStatus.CHARGING


def test_charger_stop_charging():
    charger = Charger.create("SN-001", "Lagos Island")
    charger.start_charging()
    charger.stop_charging()
    assert charger.status == ChargerStatus.AVAILABLE


def test_charger_cannot_start_if_already_charging():
    charger = Charger.create("SN-001", "Lagos Island")
    charger.start_charging()
    with pytest.raises(ChargerNotAvailableError):
        charger.start_charging()


def test_charger_cannot_stop_if_not_charging():
    charger = Charger.create("SN-001", "Lagos Island")
    with pytest.raises(ChargerNotChargingError):
        charger.stop_charging()


def test_charger_mark_offline():
    charger = Charger.create("SN-001", "Lagos Island")
    charger.mark_offline()
    assert charger.status == ChargerStatus.OFFLINE


def test_charger_mark_faulted():
    charger = Charger.create("SN-001", "Lagos Island")
    charger.mark_faulted()
    assert charger.status == ChargerStatus.FAULTED


def test_each_charger_gets_unique_id():
    charger1 = Charger.create("SN-001", "Lagos")
    charger2 = Charger.create("SN-002", "Abuja")
    assert charger1.id != charger2.id