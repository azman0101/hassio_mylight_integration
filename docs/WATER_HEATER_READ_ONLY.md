# Water heater and GreenPlay observations

This change only reads telemetry. It adds no service for enabling GreenPlay,
editing schedules, or switching the heater. Existing switch controls are unchanged.

## Entities

- The existing `water_heater_energy` sensor is unchanged: it always reports the
  lifetime cumulative total from `measures/total`, keeping its unique ID, meaning,
  `total_increasing` state class and default-disabled setting. It never switches
  to the daily value, so long-term statistics and the Energy dashboard stay valid.
- `water_heater_energy_today` is a new daily counter from the dedicated meter's
  `energy` (Ws, exposed as Wh). It resets at local midnight.
- `water_heater_power` exposes fresh `electric_power` in watts. Zero is a valid
  reading; a missing, stale, future-dated or unsupported reading is unknown.
- `water_heater_green_play` is an enum sensor, not a switch: `enabled`, `disabled`
  or unknown, read from the controlling relay. Attributes include raw
  `green_play_ranges`, `next_command`, `power_measured_at`,
  `effective_report_period`, `discovery` and `controller_discovery`. The poll time
  is not exposed, so the recorder does not write a new row on every update.

The three heater sensors above are only created when exactly one dedicated meter
is discovered at setup. Installations without one get no always-unknown entities;
reload the integration after a meter is added, or if discovery was temporarily
unavailable at startup. A `not_found` or `ambiguous` discovery result is cached
for up to 24 hours; reloading the integration re-reads the inventory at once.
  A disabled program with empty ranges is valid, not an API failure.

An enabled GreenPlay program does not mean the relay is currently on. An energized
relay does not guarantee the resistance is consuming power: its thermostat can
open the circuit. A weekly range is not a measured heating cycle.

## Device binding

Discovery requires exactly one `cmp` or `gmd` with `deviceTypeId=water_heater`.
It does not use a translated name, the last relay, or a hardcoded installation ID.
With multiple candidate meters, the new observations remain unknown and report
`discovery=ambiguous`; explicit user selection is deferred to a subsequent change.
With no supported meter, `discovery=not_found`. Raw reads check for
`not.authorized` like the typed client methods, so an expired session triggers
reauthentication instead of looking like a missing meter.

The meter and the controller are separate devices. Energy and power are read on
the meter. The GreenPlay program and `nextCommand` are read on the relay that
controls the heater: on the live installation the meter's own schedule is
disabled with empty ranges while the relay's program is enabled, and only the
relay carries the next command.

The controller is the single `sw` device with `deviceTypeId=water_heater`. With
several such relays, an explicit inventory link to the meter (`masterMac` in
either direction) narrows the choice, then a GreenPlay program capability
(`programs.greenPlayeEnabled`, vendor spelling). If that still leaves more than
one, or none exists, `controller_discovery` is `ambiguous` or `not_found` and the
program and next command stay unknown; the last relay in the list is never
taken. Energy and power are still reported from the meter.

The next command is the one known at read time; GreenPlay may recompute it
later. It does not by itself prove that heating started or how long it lasted.
The meter's `state` is not evidence of heating either: on the live installation
it read `on` while the relay was `off` and power was 0 W.

## API contracts

The existing `async_get_schedule(token, schedule_type)` call remains valid for
`electric_tariff`. Device schedules require `device_id` and send `deviceId`.
`category` is optional. Successful HTTP responses must also have `status=ok`,
a matching type, boolean enabled, and string ranges. No token or real device ID
from the installation is included in tests or documentation.

The dedicated meter uses `/api/measures/grouping` with `groupType=day` and
`measureType=one_phase`. The date field must match the requested local day;
offset-aware group dates are converted to HA local time before comparing;
missing days and unknown units remain unknown. `one_phase` follows the MyHome
client for ordinary device charts; other meter schemas require separate fixtures.

The coordinator's daily bounds now use the Home Assistant timezone, including
around midnight when the container system clock is UTC. Existing global-energy
entities retain their identifiers. Global optional battery semantics, CSV range
handling and grid import/export definitions are outside this PR.

## Timing and limits

The configured polling interval is unchanged (default 15 minutes). The device
inventory is cached and re-read at most every 24 hours. Three optional reads run
per poll when a supported heater is found (daily meter energy, states, GreenPlay
schedule), in parallel with the core reads rather than after them.
Optional endpoint failures do not invalidate unrelated global sensors; a rejected
session still triggers the existing authentication handling.

Measurement time and API-read time are separate. Each source has one fixed date
interpretation, never chosen according to whether the result looks fresh.
Offset-aware dates are used as given. Dates without an offset are HA local wall
time, matching MyHome's portal and the live installation (Europe/Paris).
`parse_power`/`read_water_heater` take an explicit `naive_tz` for a source
confirmed to send naive UTC dates; nothing switches to it automatically.
Power is rejected beyond max(15 minutes, three device reporting periods), and
readings up to 5 minutes in the future are accepted to tolerate clock skew. That
tolerance never changes the timezone: a local reading 61 minutes old is rejected.
`nextCommand` is retained as supplied: its timestamp schema and timezone are not
inferred, and `last_read` is not advertised as the time a decision was made.

The device-specific schedule response shapes were provided by the installation
owner. The `energy` meter contract follows the public MyHome client; no live
query of that meter with a cloud token, pilot deployment, or actuator test has
been performed for this PR. A read-only post-merge check must confirm dates,
units, and next-command provenance before using the values for control.

## Comparing GreenPlay with Solcast

Initially collect GreenPlay's observed planning and actual heater consumption,
and compare them with Solcast decisions simulated at the same time. Keep forecast
versions available before each decision. Neither schedule ranges nor weather data
are presented as an accessible numerical GreenPlay PV forecast. No production
notification or pilot automation is installed by this change.

## Daily-energy dates and dashboard sampling

The daily energy sensor exposes `energy_day` (`YYYY-MM-DD`), the aggregate date
validated against the API response in Home Assistant's timezone. It is null when
the requested day's energy is missing, invalid, or the meter is not identified.
It is **not** the meter's last measurement time or a guarantee of complete
acquisition. A valid zero is retained.

A dashboard's "consumed today" display must compare `energy_day` with today's
date in Home Assistant's timezone. Do not use `last_updated` or `last_reported`:
a successful poll or restart can report old data with a new HA timestamp. After
midnight, an old aggregate date should display N/A until today's data arrives.
Do not substitute zero, yesterday's value, or a power timestamp.

Custom cards are not part of this integration or of the HACS download. When
adapting one, build today's date as `YYYY-MM-DD` in Home Assistant's timezone
(for example with `Intl.DateTimeFormat('en-CA', {timeZone, year: 'numeric',
month: '2-digit', day: '2-digit'})`) and compare it with `energy_day` as a plain
string. With integration versions before 0.12.2, which do not expose
`energy_day`, such a card displays N/A.

Power charts contain sampled observations, normally polled every 15 minutes.
Use a label such as **Measured power — sampled readings**, show observation
markers, and state that connecting segments are a visual aid, not continuous
measurement. Keep unknown values as gaps. For example, annotate a stepped chart:

> Points are sampled measurements. Steps between points do not prove that power
> remained constant. Short heater cycles or grid-import spikes may be missed.

Do not integrate those sparse points to claim exact heater energy or savings.
Use the dedicated daily energy total for energy, subject to acquisition coverage.
This change does not repair historical statistics or alter entity mappings,
polling, relay controls, or Energy dashboard settings.
