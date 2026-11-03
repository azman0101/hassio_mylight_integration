"""Read-only discovery and telemetry for a dedicated water-heater meter.

Program ownership follows the meter, not whichever relay was discovered last.
No control endpoint is used here.

This is a helper module, deliberately not named ``water_heater.py`` so it can
never be mistaken for Home Assistant's ``water_heater`` entity platform.
"""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, tzinfo
from typing import Any

from .api.client import MyLightApiClient
from .api.const import DEVICES_URL, ERR_NOT_AUTHORIZED, MEASURES_GROUPING_URL, STATES_URL
from .api.exceptions import UnauthorizedError
from .api.models import Measure, Schedule

# Tolerate small clock differences between the device, the cloud and HA.
CLOCK_SKEW_TOLERANCE = 300


@dataclass
class MeterDiscovery:
    """Result of looking for the dedicated meter in the device inventory."""

    meter: dict | None
    status: str  # "found", "ambiguous" or "not_found"
    discovered_at: datetime


@dataclass
class WaterHeaterData:
    """Optional observations; unknown is never replaced with zero or disabled."""

    energy: Measure | None = None
    power: float | None = None
    measured_at: datetime | None = None
    report_period: float | None = None
    green_play: Schedule | None = None
    next_command: dict[str, Any] | str | None = None
    fetched_at: datetime | None = None
    discovery: str = "not_found"


def finite_number(value: Any) -> float | None:
    """Accept finite JSON numbers, never booleans or numeric strings."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


def _objects(value: Any) -> list[dict]:
    """Ignore null or malformed optional collections rather than crashing the coordinator."""
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _check_auth(response: Any) -> None:
    """Raise like the typed client methods do when the session was rejected."""
    if isinstance(response, dict) and response.get("status") == "error" and response.get("error") == ERR_NOT_AUTHORIZED:
        raise UnauthorizedError()


def find_meter(devices: list[dict]) -> tuple[dict | None, str]:
    """Require one explicitly typed meter, independent of names and ordering."""
    candidates = [
        d
        for d in _objects(devices)
        if d.get("type") in ("cmp", "gmd") and d.get("deviceTypeId") == "water_heater" and isinstance(d.get("id"), str)
    ]
    if len(candidates) != 1:
        return None, "ambiguous" if candidates else "not_found"
    return candidates[0], "found"


def _parse_date(value: Any, tz: tzinfo | None) -> list[datetime]:
    """Return candidate aware datetimes for an API date string.

    Offset-aware dates are unambiguous. Naive legacy dates are local wall-clock
    time in the MyHome portal, so HA local time is tried first and UTC second.
    """
    if not isinstance(value, str):
        return []
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return []
    if parsed.tzinfo is not None:
        return [parsed]
    return [parsed.replace(tzinfo=tz), parsed.replace(tzinfo=UTC)]


def parse_power(state: dict, now: datetime) -> tuple[float | None, datetime | None]:
    """Expose one fresh, correctly typed power measurement in the HA timezone."""
    readings = [
        s["measure"]
        for s in _objects(state.get("sensorStates"))
        if isinstance(s.get("measure"), dict) and s["measure"].get("type") == "electric_power"
    ]
    if len(readings) != 1:
        return None, None
    measure = readings[0]
    if measure.get("unit") not in ("watt", "W"):
        return None, None
    candidates = _parse_date(measure.get("date"), now.tzinfo)
    if not candidates:
        return None, None
    period = finite_number(state.get("effectiveReportPeriod"))
    max_age = max(900, 3 * (period or 300))
    power = finite_number(measure.get("value"))
    for measured_at in candidates:
        age = (now - measured_at).total_seconds()
        if -CLOCK_SKEW_TOLERANCE <= age <= max_age:
            return power, measured_at.astimezone(now.tzinfo)
    return None, candidates[0].astimezone(now.tzinfo)


def _group_day(value: Any, tz: tzinfo | None) -> str | None:
    """Return the HA-local calendar day an energy group belongs to."""
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return value[:10] if len(value) >= 10 else None
    if parsed.tzinfo is not None and tz is not None:
        # A UTC timestamp for local midnight falls on the previous UTC day.
        parsed = parsed.astimezone(tz)
    return parsed.date().isoformat()


def parse_day_energy(energy: Any, day: str, tz: tzinfo | None = None) -> Measure | None:
    """Select the requested local day and reject unknown units or malformed values."""
    if isinstance(energy, dict) and energy.get("status") == "ok":
        groups = [g for g in _objects(energy.get("measures")) if _group_day(g.get("date"), tz) == day]
        if len(groups) == 1:
            values = [v for v in _objects(groups[0].get("values")) if v.get("type") == "energy"]
            if len(values) == 1:
                v = values[0]
                number = finite_number(v.get("value"))
                if number is not None and number >= 0 and v.get("unit") == "Ws":
                    return Measure("energy", number, "Ws")
    return None


async def discover_meter(client: MyLightApiClient, token: str, now: datetime) -> MeterDiscovery:
    """Read the device inventory once; the coordinator caches the result."""
    inventory = await client.async_raw_request("get", DEVICES_URL, {"authToken": token})
    _check_auth(inventory)
    if not isinstance(inventory, dict) or inventory.get("status") != "ok":
        # Not a definitive answer: let the caller retry on the next poll.
        raise ValueError("Device inventory unavailable")
    meter, status = find_meter(inventory.get("devices", []))
    return MeterDiscovery(meter, status, now)


async def read_water_heater(
    client: MyLightApiClient, token: str, now: datetime, discovery: MeterDiscovery
) -> WaterHeaterData:
    """Read optional heater data without compromising the installation's core sensors."""
    data = WaterHeaterData(discovery=discovery.status)
    meter = discovery.meter
    if meter is None:
        return data
    meter_id = meter["id"]
    today = now.date()
    params = {
        "authToken": token,
        "deviceId": meter_id,
        "measureType": "one_phase",
        "groupType": "day",
        "fromDate": today.isoformat(),
        "toDate": (today + timedelta(days=1)).isoformat(),
    }
    results = await asyncio.gather(
        client.async_raw_request("get", MEASURES_GROUPING_URL, params),
        client.async_raw_request("get", STATES_URL, {"authToken": token}),
        client.async_get_schedule(token, "green_play", device_id=meter_id),
        return_exceptions=True,
    )
    for result in results:
        if isinstance(result, UnauthorizedError):
            raise result
        _check_auth(result)
    energy, states, schedule = results
    data.energy = parse_day_energy(energy, today.isoformat(), now.tzinfo)
    if isinstance(states, dict) and states.get("status") == "ok":
        matches = [s for s in _objects(states.get("deviceStates")) if s.get("deviceId") == meter_id]
        if len(matches) == 1:
            state = matches[0]
            data.power, data.measured_at = parse_power(state, now)
            data.report_period = finite_number(state.get("effectiveReportPeriod"))
            command = state.get("nextCommand")
            if command is None and meter.get("masterType") == "gmd":
                # MyHome can store the heater's command on its explicitly linked composite meter.
                parents = [
                    s for s in _objects(states.get("deviceStates")) if s.get("deviceId") == meter.get("masterMac")
                ]
                if len(parents) == 1:
                    command = parents[0].get("nextCommand")
            if isinstance(command, (dict, str)):
                data.next_command = command
    if isinstance(schedule, Schedule):
        data.green_play = schedule
    # This timestamps the read, not the decision time or the age of the sensor report.
    data.fetched_at = now
    return data
