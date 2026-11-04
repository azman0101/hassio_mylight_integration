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
