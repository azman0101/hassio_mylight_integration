"""Signed physical meter readings, missing data, and shared cloud requests."""

import asyncio
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest

from custom_components.mylight_systems.api.client import MyLightApiClient
from custom_components.mylight_systems.api.const import DEVICES_URL, STATES_URL
from custom_components.mylight_systems.api.exceptions import CommunicationError, UnauthorizedError
from custom_components.mylight_systems.grid_telemetry import GridData, discover_grid_meter, read_grid_power
from custom_components.mylight_systems.sensor import _grid_value

NOW = datetime(2026, 11, 4, 14, 0, tzinfo=ZoneInfo("Europe/Paris"))
METER = {"id": "grid-test", "type": "cmp", "deviceTypeId": "asoka_electric_counter"}


def fixture_client(devices, power=-1500, age=0, unit="watt"):
    client = AsyncMock()

    async def raw(method, path, params):
        assert method == "get"
        if path == DEVICES_URL:
            return {"status": "ok", "devices": devices}
        assert path == STATES_URL
        return {
            "status": "ok",
            "deviceStates": [
                {
                    "deviceId": "grid-test",
                    "effectiveReportPeriod": 150,
                    "sensorStates": [
                        {
                            "measure": {
                                "type": "electric_power",
                                "unit": unit,
                                "value": power,
                                "date": (NOW - timedelta(seconds=age)).strftime("%Y-%m-%d %H:%M:%S"),
                            }
                        }
                    ],
                },
                {
                    "deviceId": "composite",
                    "sensorStates": [{"measure": {"type": "electric_power", "value": 999999, "unit": "watt"}}],
                },
            ],
        }

    client.async_raw_request.side_effect = raw
    return client


@pytest.mark.asyncio
@pytest.mark.parametrize("power,imported,exported", [(1500, 1500, 0), (-1500, 0, 1500), (0, 0, 0)])
async def test_signed_power_and_separate_directions(power, imported, exported):
    client = fixture_client([METER, {"id": "composite", "type": "gmd"}], power)
    discovery = await discover_grid_meter(client, "fixture-token", NOW)
    grid = await read_grid_power(client, "fixture-token", NOW, discovery)
    data = SimpleNamespace(grid=grid)
    assert _grid_value(data, "signed") == power
    assert _grid_value(data, "import") == imported
    assert _grid_value(data, "export") == exported
    assert grid.measured_at == NOW and grid.report_period == 150


@pytest.mark.asyncio
@pytest.mark.parametrize("devices,status", [([], "not_found"), ([METER, {**METER, "id": "other"}], "ambiguous")])
async def test_never_guess_or_sum_ambiguous_meters(devices, status):
    client = fixture_client(devices)
    discovery = await discover_grid_meter(client, "fixture-token", NOW)
    assert discovery.status == status
    grid = await read_grid_power(client, "fixture-token", NOW, discovery)
    assert _grid_value(SimpleNamespace(grid=grid), "import") is None
    assert client.async_raw_request.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("age,unit", [(901, "watt"), (0, "Wh"), (-301, "watt")])
async def test_stale_wrong_unit_and_future_are_unknown(age, unit):
    client = fixture_client([METER], age=age, unit=unit)
    discovery = await discover_grid_meter(client, "fixture-token", NOW)
    grid = await read_grid_power(client, "fixture-token", NOW, discovery)
    assert grid.power is None
    assert _grid_value(SimpleNamespace(grid=grid), "import") is None


@pytest.mark.asyncio
async def test_auth_error_propagates_and_missing_power_is_not_zero():
    client = fixture_client([METER])
    client.async_raw_request.return_value = {"status": "error", "error": "not.authorized"}
    client.async_raw_request.side_effect = None
    with pytest.raises(UnauthorizedError):
        await discover_grid_meter(client, "fixture-token", NOW)
    assert _grid_value(SimpleNamespace(grid=GridData(discovery="found")), "import") is None


@pytest.mark.asyncio
async def test_concurrent_states_read_is_shared_and_token_or_expiry_refreshes():
    client = MyLightApiClient("https://example.invalid", AsyncMock())
    client._execute_request = AsyncMock(return_value={"status": "ok", "deviceStates": []})
    await asyncio.gather(
        *[client.async_raw_request("get", STATES_URL, {"authToken": "fixture-token"}) for _ in range(4)]
    )
    assert client._execute_request.await_count == 1
    await client.async_get_states("fixture-token")
    assert client._execute_request.await_count == 1
    client._states_created -= 6
    await client.async_get_states("fixture-token")
    assert client._execute_request.await_count == 2
    await client.async_get_states("different-fixture-token")
    assert client._execute_request.await_count == 3


@pytest.mark.asyncio
async def test_failed_states_request_is_retried():
    client = MyLightApiClient("https://example.invalid", AsyncMock())
    client._execute_request = AsyncMock(side_effect=[CommunicationError(), {"status": "ok", "deviceStates": []}])
    with pytest.raises(CommunicationError):
        await client.async_get_states("fixture-token")
    assert await client.async_get_states("fixture-token") == {"status": "ok", "deviceStates": []}
    assert client._execute_request.await_count == 2
