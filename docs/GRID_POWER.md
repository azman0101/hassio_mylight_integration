# Grid power (0.12.0)

Three read-only power sensors are available when inventory contains exactly one
`cmp` meter with `deviceTypeId=asoka_electric_counter`:

| Sensor key | Meaning (W) |
|---|---|
| `grid_power` | Signed physical meter power: positive import, negative export |
| `grid_import_power` | `max(grid_power, 0)` — whole-house import |
| `grid_export_power` | `max(-grid_power, 0)` — whole-house export |

The source is the meter's `/api/states` `electric_power` reading, not a derivative
of a daily energy counter. Composite devices are not summed: their channels may
include solar and water-heater readings. Multiple candidate grid meters are
ambiguous and are not guessed. This channel/sign convention was verified on an
installation while solar production exceeded household demand; other meter types
are not inferred by name.

Missing, stale, future-dated or incompatible-unit readings remain unknown. A
measured zero is valid. Attributes include the measurement timestamp and report
period. The existing coordinator interval remains unchanged (15 minutes by
default, configurable in integration options). The device report period is not
the Home Assistant collection interval. Shared state reads avoid four concurrent
requests for the same cloud snapshot.

Recorder history starts when these sensors are installed. Zooming a chart cannot
reconstruct samples that were never collected. Comparing whole-house grid import
with heater and solar power reveals coincidence, not a unique causal allocation
to the heater: other loads and asynchronous meters also matter.

No relay commands, GreenPlay schedules or Energy-dashboard sources are changed.

## Relation to upstream

Upstream reimplemented these sensors in acesyde/hassio_mylight_integration#177
(released in upstream 0.11.0) with the same sensor keys, so unique IDs and entity
IDs are the same in both. This fork follows upstream's structure: the meter rule
lives in `MyLightApiClient.async_get_devices` (`InstallationDevices.grid_meter_id`,
`GRID_METER_TYPE`/`GRID_METER_TYPE_ID`), icons come from `icons.json`, and entity
names use upstream's translations.

This fork keeps stricter reads than upstream: stale or future-dated readings are
unknown (upstream exposes the last value as is), `W` is accepted as well as
`watt`, a meter with more than one `electric_power` reading is unknown instead of
taking the first, one `/api/states` response is shared across concurrent readers,
the inventory is re-read every 24 hours, and the sensors expose provenance
attributes.


## Defensive inventory parsing

A valid grid counter remains discoverable when unrelated inventory entries are
null, malformed, or lack a non-empty string identifier. Invalid meter identifiers
are ignored before counting candidates. A master without a report period keeps
the existing 60-second default. A non-list inventory is a read error, not an empty
installation to cache. Coordinator regression tests verify that a failed discovery
is retried and can recover on the next update.

## Switching HACS providers safely

The upstream repository and a fork can both advertise the same
`mylight_systems` domain. Their downloads then target the same
`custom_components/mylight_systems` directory: installing or updating either can
replace the other's code. The running process can retain previously loaded code,
so currently working entities do not prove which code the next restart will load.

Keep only one active HACS provider for this domain. Before changing providers,
back up the integration files and the Home Assistant configuration. Removing an
obsolete HACS download deletes the shared code directory; reinstall the intended,
validated fork **before** reloading the integration or restarting Home Assistant.
Do not remove the configured mylight integration or its entities: retaining the
config entry and unique IDs preserves existing entity IDs, history and dashboard
references.

Before the planned reload, verify the installed version and expected modules,
check the Home Assistant configuration, and keep a rollback copy. After loading
the intended code, verify the grid and water-heater sensors and GreenPlay status.
A pull-request merge alone does not update an installed release; publish and
select the intended fork release through the normal reviewed release process.
