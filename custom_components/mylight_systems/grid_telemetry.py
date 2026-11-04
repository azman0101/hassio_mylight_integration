"""Read-only signed grid power from one explicitly identified electricity meter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .api.client import MyLightApiClient
from .api.const import DEVICES_URL, ERR_NOT_AUTHORIZED, STATES_URL
from .api.exceptions import MyLightSystemsError, UnauthorizedError
from .heater_telemetry import finite_number, parse_power


@dataclass
class GridDiscovery:
    """Cached discovery; ambiguous meters must not be silently added together."""

    meter_id: str | None
    status: str
    discovered_at: datetime


@dataclass
class GridData:
    """Positive signed power is import; negative signed power is export."""

    power: float | None = None
    measured_at: datetime | None = None
    report_period: float | None = None
    discovery: str = "not_found"


def _checked(response: object) -> dict:
    """Check business errors without including account data in exceptions."""
    if isinstance(response, dict) and response.get("status") == "error" and response.get("error") == ERR_NOT_AUTHORIZED:
        raise UnauthorizedError()
    if not isinstance(response, dict) or response.get("status") != "ok":
        raise MyLightSystemsError("Grid telemetry unavailable")
    return response


async def discover_grid_meter(client: MyLightApiClient, token: str, now: datetime) -> GridDiscovery:
    """Find the unique physical grid counter, not the multi-channel composite device."""
    response = _checked(await client.async_raw_request("get", DEVICES_URL, {"authToken": token}))
    devices = response.get("devices")
    if not isinstance(devices, list):
        raise MyLightSystemsError("Invalid grid inventory")
    candidates = [
        d
        for d in devices
        if isinstance(d, dict)
        and d.get("type") == "cmp"
        and d.get("deviceTypeId") == "asoka_electric_counter"
        and isinstance(d.get("id"), str)
        and d["id"]
    ]
    if len(candidates) != 1:
        return GridDiscovery(None, "ambiguous" if candidates else "not_found", now)
    return GridDiscovery(candidates[0]["id"], "found", now)


async def read_grid_power(client: MyLightApiClient, token: str, now: datetime, discovery: GridDiscovery) -> GridData:
    """Read measured watts directly; never differentiate daily energy counters."""
    data = GridData(discovery=discovery.status)
    if discovery.meter_id is None:
        return data
    response = _checked(await client.async_raw_request("get", STATES_URL, {"authToken": token}))
    states = response.get("deviceStates")
    if not isinstance(states, list):
        return data
    matches = [s for s in states if isinstance(s, dict) and s.get("deviceId") == discovery.meter_id]
    if len(matches) == 1:
        state = matches[0]
        data.power, data.measured_at = parse_power(state, now)
        data.report_period = finite_number(state.get("effectiveReportPeriod"))
    return data
