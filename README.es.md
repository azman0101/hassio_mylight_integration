# MyLight Systems

> Fork mantenido por [azman0101](https://github.com/azman0101/hassio_mylight_integration), basado en el proyecto de [Pierre-Emmanuel Mercier (@acesyde)](https://github.com/acesyde/hassio_mylight_integration). Se conservan la licencia MIT y los créditos originales; véase [NOTICE.md](NOTICE.md).

🌐 [English](README.en.md) | [Français](README.md) | [Português](README.pt.md) | [Deutsch](README.de.md) | **Español**

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]

_Integración para conectar con [MyLight Systems][mylight_systems]._

> [!Warning]
>
> Esta integración actualmente solo es compatible con el área de cliente **MyHome**. Para soporte de **MyLight150**, una extensión dedicada está disponible en [Racailloux/mylight150_ha](https://github.com/Racailloux/mylight150_ha).

**Esta integración configurará las siguientes plataformas.**

## Entidades proporcionadas

### Sensores

| ID de entidad                                   | Descripción                                            | Unidad | Clase de estado    |
| ----------------------------------------------- | ------------------------------------------------------ | ------ | ------------------ |
| `sensor.total_solar_production`                 | Energía acumulada producida por los paneles solares    | Wh     | `total_increasing` |
| `sensor.total_grid_consumption`                 | Energía consumida de la red (con batería virtual)      | Wh     | `total_increasing` |
| `sensor.total_grid_without_battery_consumption` | Energía consumida de la red (sin batería virtual)      | Wh     | `total_increasing` |
| `sensor.total_autonomy_rate`                    | % del consumo cubierto por solar + batería             | %      | `measurement`      |
| `sensor.total_self_conso`                       | % de la producción solar consumida localmente          | %      | `measurement`      |
| `sensor.total_msb_charge`                       | Energía acumulada cargada en la Smart Battery          | Wh     | `total_increasing` |
| `sensor.total_msb_discharge`                    | Energía acumulada descargada de la Smart Battery       | Wh     | `total_increasing` |
| `sensor.total_green_energy`                     | Energía solar consumida directamente por su hogar      | Wh     | `total_increasing` |
| `sensor.battery_state`                          | Energía almacenada actualmente en la Smart Battery     | kWh    | `measurement`      |
| `sensor.grid_returned_energy`                   | Energía solar exportada a la red                       | Wh     | `total_increasing` |
| `sensor.water_heater_energy` | Energía acumulada del calentador; desactivado de forma predeterminada | Wh | `total_increasing` |
| `sensor.electric_power_capacity` | Potencia eléctrica contratada, si el perfil la proporciona | kVA | `measurement` |
| `sensor.grid_power` | Potencia de red: positiva importación, negativa exportación | W | `measurement` |
| `sensor.grid_import_power` | Potencia importada de toda la vivienda | W | `measurement` |
| `sensor.grid_export_power` | Potencia exportada a la red | W | `measurement` |
| `sensor.water_heater_energy_today` | Energía de hoy del contador dedicado al calentador (desde 0.11.0) | Wh | `total_increasing` |
| `sensor.water_heater_power` | Potencia medida del calentador (desde 0.11.0) | W | `measurement` |
| `sensor.water_heater_green_play` | Estado del programa GreenPlay: `enabled` o `disabled` (desde 0.11.0) | — | — |

### Potencia de red — desde 0.12.0

Tres sensores de solo lectura si se identifica un único contador compatible. Las lecturas ausentes u obsoletas permanecen desconocidas. El intervalo de consulta no cambia. Véase [origen y límites](docs/GRID_POWER.md).

### Calentador de agua y GreenPlay — desde 0.11.0

Los ID de entidad de la tabla son ejemplos basados en las claves de los sensores. Los ID reales dependen del idioma, del nombre de la integración y de los cambios de nombre. Consulte la página del dispositivo antes de usarlos en una automatización.

Los tres sensores nuevos solo se crean si se encuentra exactamente un contador dedicado de tipo `cmp` o `gmd` con `deviceTypeId=water_heater` al iniciar la integración. La energía y la potencia proceden del contador. El programa GreenPlay y la próxima orden proceden del relé de control identificado por separado. Si el relé falta o su identificación es ambigua, el estado GreenPlay permanece desconocido.

`water_heater_energy_today` se reinicia cada día según la zona horaria de Home Assistant. El sensor acumulativo existente `water_heater_energy` conserva su ID y significado; permanece desactivado de forma predeterminada y puede estar desconocido si la API no proporciona ese total. Los datos ausentes y las lecturas de potencia antiguas no se sustituyen por cero.

GreenPlay es un sensor enum, no un interruptor. Sus atributos incluyen `green_play_ranges`, `next_command`, `power_measured_at`, `effective_report_period`, `discovery` y `controller_discovery`. Un programa activo no significa que el relé esté encendido; un relé encendido no demuestra consumo de la resistencia.

El intervalo de consulta configurado no cambia (15 minutos de forma predeterminada). Reinicie Home Assistant tras actualizar mediante HACS. Si la detección no estaba disponible temporalmente al iniciar, vuelva a cargar la integración cuando se recupere la conexión. Consulte los límites y las comprobaciones de lectura en la [documentación detallada](docs/WATER_HEATER_READ_ONLY.md), en inglés. Antes de cambiar entre el repositorio upstream y este fork en HACS, lea la [guía de cambio de proveedor](docs/INSTALL.md), en inglés.

### Interruptores

| ID de entidad         | Descripción                                          | Notas                                                |
| --------------------- | ---------------------------------------------------- | ---------------------------------------------------- |
| `switch.master_relay` | Controla el relé principal de su instalación         | Solo disponible cuando un relé está emparejado       |

## Instalación

## Automática

[![Abra su instancia de Home Assistant y abra un repositorio en el Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=azman0101&repository=hassio_mylight_integration&category=integration)

## Manual

1. Abra el directorio de su configuración de HA (donde se encuentra `configuration.yaml`).
2. Si no tiene un directorio `custom_components`, créelo.
3. Dentro de `custom_components`, cree una nueva carpeta llamada `mylight_systems`.
4. Descargue _todos_ los archivos del directorio `custom_components/mylight_systems/` de este repositorio.
5. Coloque los archivos descargados en la nueva carpeta creada.
6. Reinicie Home Assistant.
7. En la interfaz de HA, vaya a "Configuración" → "Integraciones", haga clic en "+" y busque "MyLight Systems".

## La configuración se realiza desde la interfaz

## Arquitectura

Consulte [ARCHITECTURE.md](ARCHITECTURE.md) para el diagrama completo de componentes y el flujo de datos.

## Solución de problemas

### "Falta el interruptor de relé"

La entidad `switch.master_relay` solo se crea cuando un relé (`sw`) está emparejado a su instalación. Si no tiene un relé, esta entidad no aparecerá.

### "Los valores de los sensores están congelados / no se actualizan"

El coordinador consulta la API cada 15 minutos. Si los valores dejan de actualizarse:

1. Abra **Ajustes → Dispositivos y servicios → MyLight Systems** y verifique si hay un aviso de error.
2. Active el registro de depuración y revise los registros de Home Assistant:

```yaml
# configuration.yaml
logger:
  default: warning
  logs:
    custom_components.mylight_systems: debug
```

3. Busque entradas `CommunicationError` o `UpdateFailed` — indican un problema de red o un cambio en la API.

### "Error de autenticación" tras cambiar la contraseña

Si cambió su contraseña de MyLight externamente, la integración mostrará un error de autenticación. Vaya a **Ajustes → Dispositivos y servicios → MyLight Systems** y use la opción **Volver a autenticar** para introducir sus nuevas credenciales.

## ¡Las contribuciones son bienvenidas!

Si desea contribuir, lea las [directrices de contribución](CONTRIBUTING.md).

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
