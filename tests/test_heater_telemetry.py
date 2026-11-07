"""Heater observations use explicit device identities and never issue commands."""

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest

from custom_components.mylight_systems import coordinator as module
from custom_components.mylight_systems.api.const import DEVICES_URL, MEASURES_GROUPING_URL, STATES_URL
from custom_components.mylight_systems.api.exceptions import CommunicationError, UnauthorizedError
from custom_components.mylight_systems.api.models import Measure, Schedule
from custom_components.mylight_systems.coordinator import MyLightSystemsDataUpdateCoordinator
from custom_components.mylight_systems.heater_telemetry import (
    MeterDiscovery,
    WaterHeaterData,
    discover_meter,
    find_controller,
    find_meter,
    parse_day_energy,
    parse_power,
)
from custom_components.mylight_systems.heater_telemetry import read_water_heater as _read

NOW = datetime(2026, 11, 4, 0, 30, tzinfo=ZoneInfo("Europe/Paris"))
METER = {
    "id": "meter-001",
    "type": "cmp",
    "deviceTypeId": "water_heater",
    "masterType": "gmd",
    "masterMac": "parent-001",
}
RELAY = {
    "id": "relay-001",
    "type": "sw",
    "deviceTypeId": "water_heater",
    "programs": {"greenPlayeEnabled": True, "scheduleEnabled": False},
}


async def read_water_heater(client, token, now):
    """Discover then read, as the coordinator does on a cold cache."""
    return await _read(client, token, now, await discover_meter(client, token, now))


def client_fixture(*, energy=None, state=None, schedule=None, devices=None):
    client = AsyncMock()

    async def raw(method, path, params):
        assert method == "get"
        assert path in (DEVICES_URL, MEASURES_GROUPING_URL, STATES_URL)
        if path == DEVICES_URL:
            return {"status": "ok", "devices": devices if devices is not None else [METER, RELAY]}
        if path == MEASURES_GROUPING_URL:
            assert params["deviceId"] == "meter-001"
            assert params["fromDate"] == "2026-11-04"
            assert params["toDate"] == "2026-11-05"
            return energy or {
                "status": "ok",
                "measures": [
                    {"date": "2026-11-04 00:00:00", "values": [{"type": "energy", "value": 3600000, "unit": "Ws"}]}
                ],
            }
        return {
            "status": "ok",
            "deviceStates": state
            if state is not None
            else [
                {
                    "deviceId": "meter-001",
                    "effectiveReportPeriod": 300,
                    "sensorStates": [
                        {
                            "measure": {
                                "type": "electric_power",
                                "value": 2100,
                                "unit": "watt",
                                "date": "2026-11-04 00:29:00",
                            }
                        }
                    ],
                },
                {"deviceId": "relay-001", "nextCommand": {"type": "GREEN_PLAY", "state": "ON"}},
            ],
        }

    client.async_raw_request.side_effect = raw
    client.async_get_schedule.return_value = schedule or Schedule("", "green_play", None, False)
    return client


def test_discovery_does_not_choose_relay_or_french_name():
    assert find_meter([RELAY, METER])[0] == METER
    assert find_meter([{"id": "x", "type": "cmp", "name": "Compteur chauffe eau"}]) == (None, "not_found")
    assert find_meter([METER, {**METER, "id": "other"}]) == (None, "ambiguous")


@pytest.mark.asyncio
async def test_reads_dedicated_meter_and_disabled_empty_program():
    client = client_fixture()
    data = await read_water_heater(client, "test-only-token", NOW)
    assert data.energy.value == 3600000
    assert data.energy_day == "2026-11-04"
    assert data.power == 2100
    assert data.green_play.enabled is False and data.green_play.ranges == ""
    assert data.measured_at.isoformat() == "2026-11-04T00:29:00+01:00"
    # The program belongs to the relay, not to the energy meter.
    client.async_get_schedule.assert_awaited_once_with("test-only-token", "green_play", device_id="relay-001")
    assert data.next_command == {"type": "GREEN_PLAY", "state": "ON"}
    assert data.controller_discovery == "found"
    assert client.async_raw_request.await_count == 3


@pytest.mark.asyncio
async def test_ambiguous_meter_never_guesses_or_fetches_program():
    client = client_fixture(devices=[METER, {**METER, "id": "other"}])
    data = await read_water_heater(client, "test-only-token", NOW)
    assert data.discovery == "ambiguous" and data.energy is None
    client.async_get_schedule.assert_not_awaited()
    assert client.async_raw_request.await_count == 1


@pytest.mark.asyncio
async def test_next_command_comes_from_controller_not_meter_or_parent():
    client = client_fixture(
        state=[
            {"deviceId": "meter-001", "sensorStates": [], "nextCommand": {"state": "meter"}},
            {"deviceId": "parent-001", "nextCommand": {"state": "parent"}},
            {"deviceId": "relay-001", "nextCommand": {"time": "2026-11-04 11:00:00", "state": "ON"}},
            {"deviceId": "unrelated", "nextCommand": {"state": "off"}},
        ]
    )
    data = await read_water_heater(client, "test-only-token", NOW)
    assert data.next_command == {"time": "2026-11-04 11:00:00", "state": "ON"}


@pytest.mark.asyncio
async def test_without_controller_program_and_command_stay_unknown_but_meter_reads():
    client = client_fixture(devices=[METER])
    data = await read_water_heater(client, "test-only-token", NOW)
    assert data.discovery == "found" and data.controller_discovery == "not_found"
    assert data.energy.value == 3600000 and data.power == 2100
    assert data.green_play is None and data.next_command is None
    client.async_get_schedule.assert_not_awaited()


def test_controller_discovery_never_guesses_between_relays():
    other = {"id": "relay-002", "type": "sw", "deviceTypeId": "water_heater"}
    plain = {"id": "relay-003", "type": "sw", "deviceTypeId": "heater"}
    assert find_controller([METER, RELAY, plain], METER) == (RELAY, "found")
    # Several unlinked relays: the one exposing a GreenPlay program wins only if unique.
    assert find_controller([METER, other, RELAY], METER) == (RELAY, "found")
    assert find_controller([METER, other, {**other, "id": "relay-004"}], METER) == (None, "ambiguous")
    assert find_controller([METER, RELAY, {**RELAY, "id": "relay-005"}], METER) == (None, "ambiguous")
    # An explicit inventory link takes precedence over list order and capabilities.
    linked = {**other, "id": "parent-001"}
    assert find_controller([METER, RELAY, linked], METER) == (linked, "found")
    assert find_controller([METER], METER) == (None, "not_found")


@pytest.mark.asyncio
async def test_optional_program_error_preserves_meter_and_auth_errors_propagate():
    client = client_fixture()
    client.async_get_schedule.side_effect = CommunicationError()
    data = await read_water_heater(client, "test-only-token", NOW)
    assert data.green_play is None and data.energy.value == 3600000
    client.async_get_schedule.side_effect = UnauthorizedError()
    with pytest.raises(UnauthorizedError):
        await read_water_heater(client, "test-only-token", NOW)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "groups", [[], [{"date": "2026-11-03", "values": [{"type": "energy", "value": 900, "unit": "Ws"}]}]]
)
async def test_missing_day_is_unknown_not_previous_day_or_zero(groups):
    data = await read_water_heater(client_fixture(energy={"status": "ok", "measures": groups}), "test-only-token", NOW)
    assert data.energy is None
    assert data.energy_day is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "unit,value,expected",
    [("Ws", 0, 0), ("Wh", 3600, None), ("Ws", True, None), ("Ws", -1, None), ("Ws", float("nan"), None)],
)
async def test_energy_units_and_zero(unit, value, expected):
    energy = {
        "status": "ok",
        "measures": [{"date": "2026-11-04", "values": [{"type": "energy", "value": value, "unit": unit}]}],
    }
    data = await read_water_heater(client_fixture(energy=energy), "test-only-token", NOW)
    assert (data.energy.value if data.energy else None) == expected


@pytest.mark.parametrize("age,expected", [(0, 0), (901, None), (-60, 0), (-301, None)])
def test_power_freshness_and_zero(age, expected):
    state = {
        "sensorStates": [
            {
                "measure": {
                    "type": "electric_power",
                    "value": 0,
                    "unit": "watt",
                    "date": (NOW - timedelta(seconds=age)).isoformat(),
                }
            }
        ]
    }
    assert parse_power(state, NOW)[0] == expected


@pytest.mark.asyncio
async def test_coordinator_retains_energy_entity_and_isolates_optional_failure(monkeypatch):
    c = object.__new__(MyLightSystemsDataUpdateCoordinator)
    c.config_entry = SimpleNamespace(
        data={
            "email": "test@example.invalid",
            "password": "test-only",  # noqa: S106
            "grid_type": "one_phase",
            "virtual_device_id": "virtual-001",
            "virtual_battery_id": "battery-001",
        }
    )
    c.client = AsyncMock()
    c.client.async_get_measures_grouping.return_value = []
    c.client.async_get_measures_total.return_value = []
    c.client.async_get_battery_state.return_value = None
    c.authenticate_user = AsyncMock()
    c._MyLightSystemsDataUpdateCoordinator__auth_token = "test-only-token"  # noqa: S105
    monkeypatch.setattr(module.dt_util, "now", lambda: NOW)
    c.client.async_get_measures_total.return_value = [Measure("water_heater_energy", 9_000_000, "Ws")]
    discovery = MeterDiscovery(METER, "found", NOW)
    discover = AsyncMock(return_value=discovery)
    read = AsyncMock(return_value=WaterHeaterData(energy=Measure("energy", 3600, "Ws"), discovery="found"))
    monkeypatch.setattr(module, "discover_meter", discover)
    monkeypatch.setattr(module, "read_water_heater", read)
    data = await c._async_update_data()
    # The lifetime total never switches to the daily meter value.
    assert data.water_heater_energy.value == 9_000_000
    assert data.water_heater.energy.value == 3600
    assert c.client.async_get_measures_grouping.call_args.kwargs["from_date"] == "2026-11-04"
    read.side_effect = CommunicationError()
    data = await c._async_update_data()
    assert data.water_heater is None
    assert data.water_heater_energy.value == 9_000_000
    # Inventory is cached between polls.
    assert discover.await_count == 1


@pytest.mark.asyncio
async def test_coordinator_rediscovers_after_ttl_and_propagates_auth(monkeypatch):
    c = object.__new__(MyLightSystemsDataUpdateCoordinator)
    c.client = AsyncMock()
    discover = AsyncMock(return_value=MeterDiscovery(None, "not_found", NOW))
    monkeypatch.setattr(module, "discover_meter", discover)
    await c._async_read_heater("t", NOW)
    await c._async_read_heater("t", NOW + timedelta(hours=1))
    assert discover.await_count == 1
    await c._async_read_heater("t", NOW + timedelta(hours=25))
    assert discover.await_count == 2
    discover.side_effect = UnauthorizedError()
    c._heater_discovery = None
    with pytest.raises(UnauthorizedError):
        await c._async_read_heater("t", NOW)


def test_sensor_values_and_attributes_keep_unknown_distinct_from_disabled():
    from custom_components.mylight_systems.coordinator import MyLightSystemsCoordinatorData  # noqa: PLC0415
    from custom_components.mylight_systems.sensor import MYLIGHT_SENSORS  # noqa: PLC0415

    data = MyLightSystemsCoordinatorData(*([None] * 11))
    descriptions = {s.key: s for s in MYLIGHT_SENSORS}
    assert descriptions["water_heater_green_play"].value_fn(data) is None
    heater = WaterHeaterData(power=0, green_play=Schedule("", "green_play", None, False), fetched_at=NOW)
    data = data._replace(water_heater=heater, water_heater_energy=Measure("energy", 3600, "Ws"))
    # Not from one identified meter: heater sensors stay unknown.
    assert descriptions["water_heater_power"].value_fn(data) is None
    heater.discovery = "found"
    heater.energy = Measure("energy", 7200, "Ws")
    assert descriptions["water_heater_energy"].value_fn(data) == 1
    assert descriptions["water_heater_energy_today"].value_fn(data) == 2
    assert descriptions["water_heater_power"].value_fn(data) == 0
    assert descriptions["water_heater_green_play"].value_fn(data) == "disabled"
    attributes = descriptions["water_heater_green_play"].attributes_fn(data)
    assert attributes["green_play_ranges"] == ""
    assert "last_read" not in attributes
    assert descriptions["water_heater_green_play"].options == ["enabled", "disabled"]


@pytest.mark.asyncio
async def test_malformed_optional_measurements_preserve_program():
    client = client_fixture(
        energy={"status": "ok", "measures": [None, {"date": "2026-11-04", "values": None}]},
        state=[None, {"deviceId": "meter-001", "sensorStates": [None, {"measure": None}]}],
    )
    data = await read_water_heater(client, "test-only-token", NOW)
    assert data.energy is None and data.power is None
    assert data.green_play.enabled is False


def test_utc_group_date_matches_local_day():
    energy = {
        "status": "ok",
        "measures": [{"date": "2026-11-03T23:00:00Z", "values": [{"type": "energy", "value": 10, "unit": "Ws"}]}],
    }
    assert parse_day_energy(energy, "2026-11-04", NOW.tzinfo).value == 10
    assert parse_day_energy(energy, "2026-11-03", NOW.tzinfo) is None


def _naive_state(date, value=2100):
    return {"sensorStates": [{"measure": {"type": "electric_power", "value": value, "unit": "watt", "date": date}}]}


def test_stale_local_reading_is_never_reinterpreted_as_fresh_utc():
    # Live site: naive dates are Paris wall time. A 61-minute-old reading must be
    # rejected, not shifted to UTC where it would look one minute old.
    now = datetime(2026, 11, 3, 22, 30, tzinfo=ZoneInfo("Europe/Paris"))
    power, measured_at = parse_power(_naive_state("2026-11-03 21:29:00"), now)
    assert power is None
    assert measured_at.isoformat() == "2026-11-03T21:29:00+01:00"


def test_summer_stale_local_reading_is_rejected():
    now = datetime(2026, 7, 3, 22, 30, tzinfo=ZoneInfo("Europe/Paris"))
    assert parse_power(_naive_state("2026-07-03 20:29:00"), now)[0] is None


def test_naive_dates_use_explicit_timezone_for_confirmed_utc_source():
    from datetime import UTC  # noqa: PLC0415

    now = datetime(2026, 11, 3, 22, 30, tzinfo=ZoneInfo("Europe/Paris"))
    power, measured_at = parse_power(_naive_state("2026-11-03 21:29:00"), now, naive_tz=UTC)
    assert power == 2100
    assert measured_at.isoformat() == "2026-11-03T22:29:00+01:00"
    # Live sample: local naive date, 0 W, two minutes old.
    assert parse_power(_naive_state("2026-11-03 22:27:47", 0), now)[0] == 0


@pytest.mark.asyncio
async def test_rejected_session_in_raw_reads_raises_unauthorized():
    client = client_fixture()
    denied = {"status": "error", "error": "not.authorized"}
    client.async_raw_request.side_effect = None
    client.async_raw_request.return_value = denied
    with pytest.raises(UnauthorizedError):
        await discover_meter(client, "test-only-token", NOW)
    with pytest.raises(UnauthorizedError):
        await _read(client, "test-only-token", NOW, MeterDiscovery(METER, "found", NOW))


@pytest.mark.asyncio
async def test_failed_inventory_is_not_cached_as_not_found():
    client = AsyncMock()
    client.async_raw_request.return_value = {"status": "error", "error": "server.error"}
    with pytest.raises(ValueError):
        await discover_meter(client, "test-only-token", NOW)


@pytest.mark.asyncio
@pytest.mark.parametrize("discovery,created", [("found", True), ("not_found", False), ("ambiguous", False)])
async def test_heater_sensors_only_created_for_a_single_meter(discovery, created):
    from custom_components.mylight_systems.coordinator import MyLightSystemsCoordinatorData  # noqa: PLC0415
    from custom_components.mylight_systems.sensor import async_setup_entry  # noqa: PLC0415

    entry = SimpleNamespace(entry_id="e", data={})
    coordinator = SimpleNamespace(
        data=MyLightSystemsCoordinatorData(*([None] * 11), WaterHeaterData(discovery=discovery)),
        config_entry=entry,
    )
    entry.runtime_data = coordinator
    added = []
    await async_setup_entry(None, entry, added.extend)
    keys = {e.entity_description.key for e in added}
    assert "water_heater_energy" in keys
    heater_keys = {"water_heater_power", "water_heater_green_play", "water_heater_energy_today"}
    assert (heater_keys <= keys) is created and (heater_keys & keys == set()) is not created


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "date,expected",
    [
        ("2026-11-03T23:00:00Z", "2026-11-04"),
        ("2026-11-03", None),
        ("2026-11-05", None),
    ],
)
async def test_daily_energy_day_is_the_validated_local_aggregate_day(date, expected):
    from custom_components.mylight_systems.coordinator import MyLightSystemsCoordinatorData  # noqa: PLC0415
    from custom_components.mylight_systems.sensor import MYLIGHT_SENSORS  # noqa: PLC0415

    energy = {
        "status": "ok",
        "measures": [{"date": date, "values": [{"type": "energy", "value": 0, "unit": "Ws"}]}],
    }
    heater = await read_water_heater(client_fixture(energy=energy), "test-only-token", NOW)
    data = MyLightSystemsCoordinatorData(*([None] * 11), water_heater=heater)
    description = next(s for s in MYLIGHT_SENSORS if s.key == "water_heater_energy_today")
    assert description.attributes_fn(data) == {"energy_day": expected}
    # A successful read today never relabels yesterday's or tomorrow's group as today's.
    assert description.value_fn(data) == (0 if expected else None)
    assert heater.energy_day == expected


def test_daily_energy_attributes_clear_when_meter_is_missing():
    from custom_components.mylight_systems.coordinator import MyLightSystemsCoordinatorData  # noqa: PLC0415
    from custom_components.mylight_systems.sensor import MYLIGHT_SENSORS  # noqa: PLC0415

    description = next(s for s in MYLIGHT_SENSORS if s.key == "water_heater_energy_today")
    data = MyLightSystemsCoordinatorData(*([None] * 11))
    assert description.attributes_fn(data) == {"energy_day": None}
    old = WaterHeaterData(energy=Measure("energy", 3600, "Ws"), energy_day="2026-11-03")
    assert description.attributes_fn(data._replace(water_heater=old)) == {"energy_day": None}
