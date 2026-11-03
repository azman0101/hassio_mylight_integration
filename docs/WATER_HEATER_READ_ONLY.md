# Water heater and GreenPlay observations

This change only reads telemetry. It adds no service for enabling GreenPlay,
editing schedules, or switching the heater. Existing switch controls are unchanged.

## Entities

- The existing `water_heater_energy` unique-ID suffix is retained. For one explicitly
  identified water-heater meter it now reads that meter's daily `energy` in Ws
  and exposes Wh. Its existing default-disabled setting is retained.
- `water_heater_power` exposes fresh `electric_power` in watts. Zero is a valid
  reading; a missing, stale, future-dated or unsupported reading is unknown.
- `water_heater_green_play` is a sensor, not a switch: `enabled`, `disabled` or
  unknown. Attributes include raw `green_play_ranges`, `next_command`,
  `last_read`, `power_measured_at`, `effective_report_period`, and `discovery`.
  A disabled program with empty ranges is valid, not an API failure.

An enabled GreenPlay program does not mean the relay is currently on. An energized
relay does not guarantee the resistance is consuming power: its thermostat can
open the circuit. A weekly range is not a measured heating cycle.

## Device binding

Discovery requires exactly one `cmp` or `gmd` with `deviceTypeId=water_heater`.
It does not use a translated name, the last relay, or a hardcoded installation ID.
With multiple candidate meters, the new observations remain unknown and report
`discovery=ambiguous`; explicit user selection is deferred to a subsequent change.
With no supported meter, `discovery=not_found`. A historical aggregate heater
measure, when provided by the installation, remains a fallback only in that case.

The meter owns the requested GreenPlay schedule. A `nextCommand` on its explicitly
linked composite parent (`masterType=gmd`, `masterMac`) is used only when the meter
itself has none. Commands on unrelated relays are never attributed to it.

## API contracts

The existing `async_get_schedule(token, schedule_type)` call remains valid for
`electric_tariff`. Device schedules require `device_id` and send `deviceId`.
`category` is optional. Successful HTTP responses must also have `status=ok`,
a matching type, boolean enabled, and string ranges. No token or real device ID
from the installation is included in tests or documentation.

The dedicated meter uses `/api/measures/grouping` with `groupType=day` and
`measureType=one_phase`. The date field must match the requested local day;
missing days and unknown units remain unknown. `one_phase` follows the MyHome
client for ordinary device charts; other meter schemas require separate fixtures.

The coordinator's daily bounds now use the Home Assistant timezone, including
around midnight when the container system clock is UTC. Existing global-energy
entities retain their identifiers. Global optional battery semantics, CSV range
handling and grid import/export definitions are outside this PR.

## Timing and limits

The configured polling interval is unchanged (default 15 minutes). Four optional
reads are added when a supported heater is found: inventory, daily meter energy,
states, and GreenPlay schedule. Unsupported installations only need discovery.
Optional endpoint failures do not invalidate unrelated global sensors; a rejected
session still triggers the existing authentication handling.

Measurement time and API-read time are separate. Legacy timestamps without an
offset are interpreted as HA local wall time, matching MyHome's local parsing;
this assumption needs confirmation if installations outside that timezone are used.
Power is rejected beyond max(15 minutes, three device reporting periods).
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
