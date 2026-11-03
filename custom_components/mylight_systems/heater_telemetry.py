"""Read-only discovery and telemetry for a dedicated water-heater meter.

Energy and power are read on the dedicated meter. The GreenPlay program and the
next planned command belong to the relay that controls the heater, which is a
separate device: the meter's own schedule is not the active program. Neither is
ever taken from "whichever relay was discovered last". No control endpoint is
used here.

This is a helper module, deliberately not named ``water_heater.py`` so it can
never be mistaken for Home Assistant's ``water_heater`` entity platform.
"""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, tzinfo
from typing import Any

from .api.client import MyLightApiClient
from .api.const import DEVICES_URL, ERR_NOT_AUTHORIZED, MEASURES_GROUPING_URL, STATES_URL
from .api.exceptions import UnauthorizedError
from .api.models import Measure, Schedule

# Tolerate small clock differences between the device, the cloud and HA.
CLOCK_SKEW_TOLERANCE = 300


# Vendor spelling (extra "e") observed on live relays, plus the plain spelling.
_GREEN_PLAY_PROGRAM_KEYS = ("greenPlayeEnabled", "greenPlayEnabled")


@dataclass
class MeterDiscovery:
    """Result of looking for the heater's meter and controller in the inventory."""

    meter: dict | None
    status: str  # "found", "ambiguous" or "not_found"
    discovered_at: datetime
    controller: dict | None = None
    controller_status: str = "not_found"  # "found", "ambiguous" or "not_found"


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
    controller_discovery: str = "not_found"


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


def _is_linked(controller: dict, meter: dict) -> bool:
    """Return True when the inventory explicitly links the relay and the meter."""
    controller_id, meter_id = controller.get("id"), meter.get("id")
    return (meter.get("masterMac") is not None and meter.get("masterMac") == controller_id) or (
        controller.get("masterMac") is not None and controller.get("masterMac") == meter_id
    )


def _has_green_play_program(controller: dict) -> bool:
    programs = controller.get("programs")
    return isinstance(programs, dict) and any(key in programs for key in _GREEN_PLAY_PROGRAM_KEYS)


def find_controller(devices: list[dict], meter: dict | None) -> tuple[dict | None, str]:
    """Find the one relay that controls the water heater, never guessing between several.

    A single relay typed ``water_heater`` is accepted. With several, only an
    explicit link to the meter, then a GreenPlay program capability, may narrow
    the choice to exactly one; otherwise the program stays unknown.
    """
    candidates = [
        d
        for d in _objects(devices)
        if d.get("type") == "sw" and d.get("deviceTypeId") == "water_heater" and isinstance(d.get("id"), str)
    ]
    if not candidates:
        return None, "not_found"
    if len(candidates) > 1 and meter is not None:
        linked = [d for d in candidates if _is_linked(d, meter)]
        candidates = linked or candidates
    if len(candidates) > 1:
        capable = [d for d in candidates if _has_green_play_program(d)]
        candidates = capable or candidates
    if len(candidates) != 1:
        return None, "ambiguous"
    return candidates[0], "found"


def _parse_date(value: Any, naive_tz: tzinfo | None) -> datetime | None:
    """Parse an API date with one fixed interpretation per source.

    Offset-aware dates are used as given. Naive dates are interpreted in
    ``naive_tz`` only. The interpretation is never chosen by trying several
    timezones and keeping whichever looks fresh, because that silently changes
    the meaning of the timestamp and can present an old reading as current.
    """
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=naive_tz)


def parse_power(state: dict, now: datetime, naive_tz: tzinfo | None = None) -> tuple[float | None, datetime | None]:
    """Expose one fresh, correctly typed power measurement in the HA timezone.

    Naive measurement dates are local wall-clock time in the MyHome portal and
    on observed installations, so they default to HA's timezone (``now.tzinfo``).
    Pass ``naive_tz=UTC`` only for a source confirmed to send naive UTC dates.
    """
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
    measured_at = _parse_date(measure.get("date"), naive_tz or now.tzinfo)
    if measured_at is None:
        return None, None
    period = finite_number(state.get("effectiveReportPeriod"))
    max_age = max(900, 3 * (period or 300))
    age = (now - measured_at).total_seconds()
    power = finite_number(measure.get("value"))
    # The skew tolerance only absorbs small clock differences; it never changes timezone.
    fresh = -CLOCK_SKEW_TOLERANCE <= age <= max_age
    return (power if fresh else None), measured_at.astimezone(now.tzinfo)


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


async def _no_schedule() -> None:
    """Placeholder when no controller owns a program."""
    return None


async def discover_meter(client: MyLightApiClient, token: str, now: datetime) -> MeterDiscovery:
    """Read the device inventory once; the coordinator caches the result."""
    inventory = await client.async_raw_request("get", DEVICES_URL, {"authToken": token})
    _check_auth(inventory)
    if not isinstance(inventory, dict) or inventory.get("status") != "ok":
        # Not a definitive answer: let the caller retry on the next poll.
        raise ValueError("Device inventory unavailable")
    devices = inventory.get("devices", [])
    meter, status = find_meter(devices)
    controller, controller_status = find_controller(devices, meter)
    return MeterDiscovery(meter, status, now, controller, controller_status)


async def read_water_heater(
    client: MyLightApiClient,
    token: str,
    now: datetime,
    discovery: MeterDiscovery,
    naive_tz: tzinfo | None = None,
) -> WaterHeaterData:
    """Read optional heater data without compromising the installation's core sensors.

    Energy and power come from the meter; the GreenPlay program and next command
    come from the controlling relay. Without one identified relay they stay unknown.
    """
    data = WaterHeaterData(discovery=discovery.status, controller_discovery=discovery.controller_status)
    meter = discovery.meter
    if meter is None:
        return data
    meter_id = meter["id"]
    controller_id = discovery.controller["id"] if discovery.controller is not None else None
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
        _no_schedule()
        if controller_id is None
        else client.async_get_schedule(token, "green_play", device_id=controller_id),
        return_exceptions=True,
    )
    for result in results:
        if isinstance(result, UnauthorizedError):
            raise result
        _check_auth(result)
    energy, states, schedule = results
    data.energy = parse_day_energy(energy, today.isoformat(), now.tzinfo)
    if isinstance(states, dict) and states.get("status") == "ok":
        device_states = _objects(states.get("deviceStates"))
        matches = [s for s in device_states if s.get("deviceId") == meter_id]
        if len(matches) == 1:
            state = matches[0]
            data.power, data.measured_at = parse_power(state, now, naive_tz)
            data.report_period = finite_number(state.get("effectiveReportPeriod"))
        if controller_id is not None:
            # The next command is the one known at read time; GreenPlay may recompute it later.
            controllers = [s for s in device_states if s.get("deviceId") == controller_id]
            if len(controllers) == 1:
                command = controllers[0].get("nextCommand")
                if isinstance(command, (dict, str)):
                    data.next_command = command
    if isinstance(schedule, Schedule):
        data.green_play = schedule
    # This timestamps the read, not the decision time or the age of the sensor report.
    data.fetched_at = now
    return data
