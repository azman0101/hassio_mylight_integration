"""Read-only discovery and telemetry for a dedicated water-heater meter.

Program ownership follows the meter, not whichever relay was discovered last.
No control endpoint is used here.
"""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from .api.client import MyLightApiClient
from .api.const import DEVICES_URL, MEASURES_GROUPING_URL, STATES_URL
from .api.exceptions import UnauthorizedError
from .api.models import Measure, Schedule


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
    try:
        measured_at = datetime.fromisoformat(measure["date"])
        if measured_at.tzinfo is None:
            # Legacy API dates are local wall-clock dates, as in the MyHome portal.
            measured_at = measured_at.replace(tzinfo=now.tzinfo)
    except KeyError, ValueError, TypeError:
        return None, None
    period = finite_number(state.get("effectiveReportPeriod"))
    max_age = max(900, 3 * (period or 300))
    age = (now - measured_at).total_seconds()
    power = finite_number(measure.get("value"))
    return (power if 0 <= age <= max_age else None), measured_at


def parse_day_energy(energy: Any, day: str) -> Measure | None:
    """Select the requested day and reject unknown units or malformed values."""
    if isinstance(energy, dict) and energy.get("status") == "ok":
        groups = [g for g in _objects(energy.get("measures")) if str(g.get("date", ""))[:10] == day]
        if len(groups) == 1:
            values = [v for v in _objects(groups[0].get("values")) if v.get("type") == "energy"]
            if len(values) == 1:
                v = values[0]
                number = finite_number(v.get("value"))
                if number is not None and number >= 0 and v.get("unit") == "Ws":
                    return Measure("energy", number, "Ws")
    return None


async def read_water_heater(client: MyLightApiClient, token: str, now: datetime) -> WaterHeaterData:
    """Read optional heater data without compromising the installation's core sensors."""
    data = WaterHeaterData()
    inventory = await client.async_raw_request("get", DEVICES_URL, {"authToken": token})
    if not isinstance(inventory, dict) or inventory.get("status") != "ok":
        return data
    meter, data.discovery = find_meter(inventory.get("devices", []))
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
    energy, states, schedule = results
    data.energy = parse_day_energy(energy, today.isoformat())
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
