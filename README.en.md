# MyLight Systems

> Fork maintained by [azman0101](https://github.com/azman0101/hassio_mylight_integration), based on [Pierre-Emmanuel Mercier (@acesyde)'s project](https://github.com/acesyde/hassio_mylight_integration). MIT license and original credits are preserved; see [NOTICE.md](NOTICE.md).

🌐 **English** | [Français](README.md) | [Português](README.pt.md) | [Deutsch](README.de.md) | [Español](README.es.md)

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]

_Integration to integrate with [MyLight Systems][mylight_systems]._

> [!Warning]
>
> This integration currently only supports the **MyHome** customer area. For **MyLight150** support, a dedicated extension is available at [Racailloux/mylight150_ha](https://github.com/Racailloux/mylight150_ha).

**This integration will set up the following platforms.**

## Provided Entities

### Sensors

| Entity ID                                       | Description                                         | Unit | State Class        |
| ----------------------------------------------- | --------------------------------------------------- | ---- | ------------------ |
| `sensor.total_solar_production`                 | Cumulative energy produced by solar panels          | Wh   | `total_increasing` |
| `sensor.total_grid_consumption`                 | Grid energy drawn (accounting for virtual battery)  | Wh   | `total_increasing` |
| `sensor.total_grid_without_battery_consumption` | Grid energy drawn (excluding virtual battery)       | Wh   | `total_increasing` |
| `sensor.total_autonomy_rate`                    | % of consumption covered by solar + battery         | %    | `measurement`      |
| `sensor.total_self_conso`                       | % of solar production consumed locally              | %    | `measurement`      |
| `sensor.total_msb_charge`                       | Cumulative energy charged into the Smart Battery    | Wh   | `total_increasing` |
| `sensor.total_msb_discharge`                    | Cumulative energy discharged from the Smart Battery | Wh   | `total_increasing` |
| `sensor.total_green_energy`                     | Solar energy consumed directly by your home         | Wh   | `total_increasing` |
| `sensor.battery_state`                          | Current energy stored in the Smart Battery          | kWh  | `measurement`      |
| `sensor.grid_returned_energy`                   | Solar energy exported back to the grid              | Wh   | `total_increasing` |
| `sensor.water_heater_energy` | Cumulative water heater energy; disabled by default | Wh | `total_increasing` |
| `sensor.electric_power_capacity` | Subscribed electrical power, when supplied by the profile | kVA | `measurement` |
| `sensor.grid_power` | Signed grid power: positive import, negative export | W | `measurement` |
| `sensor.grid_import_power` | Whole-house grid import power | W | `measurement` |
| `sensor.grid_export_power` | Grid export power | W | `measurement` |
| `sensor.water_heater_energy_today` | Today's energy from the dedicated water heater meter (since 0.11.0) | Wh | `total_increasing` |
| `sensor.water_heater_power` | Measured water heater power (since 0.11.0) | W | `measurement` |
| `sensor.water_heater_green_play` | GreenPlay program status: `enabled` or `disabled` (since 0.11.0) | — | — |

### Grid power — since 0.12.0

Three read-only sensors are created when one compatible grid meter is identified. Missing or stale readings stay unknown. The existing polling interval is unchanged; zoom cannot reconstruct missing samples. See [source and limitations](docs/GRID_POWER.md).

### Water heater and GreenPlay — since 0.11.0

The entity IDs in the table are examples based on sensor keys. Actual Home Assistant entity IDs depend on the language, integration name and any renaming. Check the device page before using them in an automation.

The three new sensors are created only when exactly one dedicated meter of type `cmp` or `gmd`, with `deviceTypeId=water_heater`, is found during integration setup. Energy and power come from the meter. The GreenPlay program and next planned command come from the separately identified controlling relay. If that relay is missing or ambiguous, GreenPlay status stays unknown.

`water_heater_energy_today` resets each day in Home Assistant's timezone. The existing cumulative `water_heater_energy` sensor keeps its identifier and meaning. It remains disabled by default and may be unknown if the API does not provide that total. Missing data and stale power readings are not replaced with zero.

GreenPlay is an enum sensor, not a switch. Its attributes include `green_play_ranges`, `next_command`, `power_measured_at`, `effective_report_period`, `discovery` and `controller_discovery`. An enabled GreenPlay program does not mean the relay is on, and an energized relay does not prove that the heating element is consuming power.

The configured polling interval is unchanged (15 minutes by default). After updating through HACS, restart Home Assistant to load the new code. If discovery was temporarily unavailable during setup, reload the integration once the connection recovers. See the [detailed documentation](docs/WATER_HEATER_READ_ONLY.md) for limits and read-only checks. Before switching between the upstream repository and this fork in HACS, read the [provider switching guide](docs/INSTALL.md).

### Switches

| Entity ID             | Description                                    | Notes                                        |
| --------------------- | ---------------------------------------------- | -------------------------------------------- |
| `switch.master_relay` | Controls the master relay on your installation | Only available when a relay device is paired |

## Installation

## Automatic

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=azman0101&repository=hassio_mylight_integration&category=integration)

## Manual

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
   3In the `custom_components` directory (folder) create a new folder called `mylight_systems`.
3. Download _all_ the files from the `custom_components/mylight_systems/` directory (folder) in this repository.
4. Place the files you downloaded in the new directory (folder) you created.
5. Restart Home Assistant
6. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "MyLight Systems"

## Configuration is done in the UI

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full component diagram and data flow.

## Troubleshooting

### "Relay switch is missing"

The `switch.master_relay` entity is only created when a relay device (`sw` type) is paired to your installation. If you do not have a relay, this entity will not appear.

### "Sensor values are stuck / not updating"

The coordinator polls the API every 15 minutes. If values stop updating:

1. Open **Settings → Devices & Services → MyLight Systems** and check for an error banner.
2. Enable debug logging and check the Home Assistant logs:

```yaml
# configuration.yaml
logger:
  default: warning
  logs:
    custom_components.mylight_systems: debug
```

3. Look for `CommunicationError` or `UpdateFailed` entries — these indicate a network issue or an API change.

### "Authentication failed" after a password change

If you change your MyLight password externally, the integration will show an authentication error. Go to **Settings → Devices & Services → MyLight Systems** and use the **Re-authenticate** option to enter your new credentials.

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

---

[mylight_systems]: https://www.mylight-systems.com/
[commits-shield]: https://img.shields.io/github/commit-activity/y/azman0101/hassio_mylight_integration.svg?style=for-the-badge
[commits]: https://github.com/azman0101/hassio_mylight_integration/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/azman0101/hassio_mylight_integration.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-azman0101-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/azman0101/hassio_mylight_integration.svg?style=for-the-badge
[releases]: https://github.com/azman0101/hassio_mylight_integration/releases
