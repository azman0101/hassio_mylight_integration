# MyLight Systems

> Dieser Fork wird von [azman0101](https://github.com/azman0101/hassio_mylight_integration) gepflegt und basiert auf dem Projekt von [Pierre-Emmanuel Mercier (@acesyde)](https://github.com/acesyde/hassio_mylight_integration). MIT-Lizenz und ursprüngliche Namensnennungen bleiben erhalten; siehe [NOTICE.md](NOTICE.md).

🌐 [English](README.en.md) | [Français](README.md) | [Português](README.pt.md) | **Deutsch** | [Español](README.es.md)

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]

_Integration zur Verbindung mit [MyLight Systems][mylight_systems]._

> [!Warning]
>
> Diese Integration unterstützt derzeit nur den Kundenbereich **MyHome**. Für **MyLight150**-Support steht eine separate Erweiterung unter [Racailloux/mylight150_ha](https://github.com/Racailloux/mylight150_ha) zur Verfügung.

**Diese Integration richtet die folgenden Plattformen ein.**

## Bereitgestellte Entitäten

### Sensoren

| Entitäts-ID                                     | Beschreibung                                           | Einheit | Statusklasse       |
| ----------------------------------------------- | ------------------------------------------------------ | ------- | ------------------ |
| `sensor.total_solar_production`                 | Kumulierte Energie aus Solarmodulen                    | Wh      | `total_increasing` |
| `sensor.total_grid_consumption`                 | Netzbezug (mit virtueller Batterie)                    | Wh      | `total_increasing` |
| `sensor.total_grid_without_battery_consumption` | Netzbezug (ohne virtuelle Batterie)                    | Wh      | `total_increasing` |
| `sensor.total_autonomy_rate`                    | % des Verbrauchs gedeckt durch Solar + Batterie        | %       | `measurement`      |
| `sensor.total_self_conso`                       | % der Solarproduktion lokal verbraucht                 | %       | `measurement`      |
| `sensor.total_msb_charge`                       | Kumulierte Energie in die Smart Battery geladen        | Wh      | `total_increasing` |
| `sensor.total_msb_discharge`                    | Kumulierte Energie aus der Smart Battery entladen      | Wh      | `total_increasing` |
| `sensor.total_green_energy`                     | Solarenergie direkt vom Haushalt verbraucht            | Wh      | `total_increasing` |
| `sensor.battery_state`                          | Aktuell in der Smart Battery gespeicherte Energie      | kWh     | `measurement`      |
| `sensor.grid_returned_energy`                   | Solarenergie ins Netz eingespeist                      | Wh      | `total_increasing` |
| `sensor.water_heater_energy` | Kumulierte Energie des Warmwasserbereiters; standardmäßig deaktiviert | Wh | `total_increasing` |
| `sensor.electric_power_capacity` | Vertragliche Anschlussleistung, sofern im Profil vorhanden | kVA | `measurement` |
| `sensor.grid_power` | Netzleistung: positiv Bezug, negativ Einspeisung | W | `measurement` |
| `sensor.grid_import_power` | Netzbezugsleistung des gesamten Hauses | W | `measurement` |
| `sensor.grid_export_power` | Netzeinspeiseleistung | W | `measurement` |
| `sensor.water_heater_energy_today` | Heutiger Energieverbrauch des eigenen Warmwasserzählers (seit 0.11.0) | Wh | `total_increasing` |
| `sensor.water_heater_power` | Gemessene Leistung des Warmwasserbereiters (seit 0.11.0) | W | `measurement` |
| `sensor.water_heater_green_play` | GreenPlay-Programmstatus: `enabled` oder `disabled` (seit 0.11.0) | — | — |

### Netzleistung — seit 0.12.0

Drei schreibgeschützte Sensoren bei genau einem kompatiblen Netzzähler. Fehlende oder veraltete Werte bleiben unbekannt. Das Abfrageintervall bleibt unverändert. Siehe [Datenquelle und Grenzen](docs/GRID_POWER.md).

### Warmwasserbereiter und GreenPlay — seit 0.11.0

Die Entitäts-IDs in der Tabelle sind Beispiele anhand der Sensorschlüssel. Die tatsächlichen IDs hängen von Sprache, Integrationsnamen und Umbenennungen ab. Prüfen Sie die Geräteseite, bevor Sie sie in Automatisierungen verwenden.

Die drei neuen Sensoren werden nur erstellt, wenn beim Einrichten genau ein eigener Zähler vom Typ `cmp` oder `gmd` mit `deviceTypeId=water_heater` gefunden wird. Energie und Leistung stammen vom Zähler. GreenPlay-Programm und nächster geplanter Befehl stammen vom getrennt erkannten Steuerrelais. Fehlt dieses oder ist die Zuordnung mehrdeutig, bleibt der GreenPlay-Status unbekannt.

`water_heater_energy_today` beginnt täglich entsprechend der Home-Assistant-Zeitzone neu. Das Attribut `energy_day` gibt das validierte lokale Datum des Tageswerts an; Dashboard-Karten müssen dieses Datum prüfen statt der Aktualisierungszeit in Home Assistant. Der bestehende kumulative Sensor `water_heater_energy` behält ID und Bedeutung, bleibt standardmäßig deaktiviert und kann unbekannt sein, wenn die API den Gesamtwert nicht liefert. Fehlende Daten und veraltete Leistungswerte werden nicht durch null ersetzt.

GreenPlay ist ein Enum-Sensor, kein Schalter. Seine Attribute umfassen `green_play_ranges`, `next_command`, `power_measured_at`, `effective_report_period`, `discovery` und `controller_discovery`. Ein aktiviertes Programm bedeutet nicht, dass das Relais eingeschaltet ist; ein eingeschaltetes Relais beweist keinen Stromverbrauch des Heizelements.

Das eingestellte Abfrageintervall bleibt unverändert (standardmäßig 15 Minuten). Starten Sie Home Assistant nach einem HACS-Update neu. War die Erkennung beim Start vorübergehend nicht verfügbar, laden Sie die Integration nach Wiederherstellung der Verbindung neu. Weitere Grenzen und Leseprüfungen stehen in der [ausführlichen Dokumentation](docs/WATER_HEATER_READ_ONLY.md) auf Englisch. Lesen Sie vor einem Wechsel zwischen dem Upstream-Repository und diesem Fork in HACS die [Anleitung zum Anbieterwechsel](docs/INSTALL.md) auf Englisch.

### Schalter

| Entitäts-ID           | Beschreibung                                        | Hinweise                                          |
| --------------------- | --------------------------------------------------- | ------------------------------------------------- |
| `switch.master_relay` | Steuert das Hauptrelais Ihrer Installation          | Nur verfügbar, wenn ein Relais gekoppelt ist      |

## Installation

## Automatisch

[![Öffnen Sie Ihre Home Assistant-Instanz und öffnen Sie ein Repository im Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=azman0101&repository=hassio_mylight_integration&category=integration)

## Manuell

1. Öffnen Sie das Verzeichnis Ihrer HA-Konfiguration (dort wo sich `configuration.yaml` befindet).
2. Falls kein Verzeichnis `custom_components` vorhanden ist, erstellen Sie es.
3. Erstellen Sie in `custom_components` einen neuen Ordner namens `mylight_systems`.
4. Laden Sie _alle_ Dateien aus dem Verzeichnis `custom_components/mylight_systems/` dieses Repositories herunter.
5. Legen Sie die heruntergeladenen Dateien in den neu erstellten Ordner.
6. Starten Sie Home Assistant neu.
7. Gehen Sie in der HA-Oberfläche zu „Konfiguration" → „Integrationen", klicken Sie auf „+" und suchen Sie nach „MyLight Systems".

## Die Konfiguration erfolgt über die Benutzeroberfläche

## Architektur

Siehe [ARCHITECTURE.md](ARCHITECTURE.md) für das vollständige Komponentendiagramm und den Datenfluss.

## Fehlerbehebung

### „Relais-Schalter fehlt"

Die Entität `switch.master_relay` wird nur erstellt, wenn ein Relais (`sw`) mit Ihrer Installation gekoppelt ist. Ohne Relais erscheint diese Entität nicht.

### „Sensorwerte sind eingefroren / aktualisieren sich nicht"

Der Koordinator fragt die API alle 15 Minuten ab. Wenn sich die Werte nicht mehr aktualisieren:

1. Öffnen Sie **Einstellungen → Geräte und Dienste → MyLight Systems** und prüfen Sie, ob ein Fehlerbanner angezeigt wird.
2. Aktivieren Sie das Debug-Logging und prüfen Sie die Home Assistant-Protokolle:

```yaml
# configuration.yaml
logger:
  default: warning
  logs:
    custom_components.mylight_systems: debug
```

3. Suchen Sie nach `CommunicationError`- oder `UpdateFailed`-Einträgen — diese weisen auf ein Netzwerkproblem oder eine API-Änderung hin.

### „Authentifizierung fehlgeschlagen" nach Passwortänderung

Wenn Sie Ihr MyLight-Passwort extern geändert haben, zeigt die Integration einen Authentifizierungsfehler an. Gehen Sie zu **Einstellungen → Geräte und Dienste → MyLight Systems** und verwenden Sie die Option **Erneut authentifizieren**, um Ihre neuen Zugangsdaten einzugeben.

## Beiträge sind willkommen!

Wenn Sie beitragen möchten, lesen Sie bitte die [Beitragsrichtlinien](CONTRIBUTING.md).

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
