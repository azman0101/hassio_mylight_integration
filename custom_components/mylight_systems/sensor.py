"""Sensor platform for MyLight Systems."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfApparentPower, UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MyLightConfigEntry
from .const import CONF_ELECTRIC_POWER_CAPACITY
from .coordinator import (
    MyLightSystemsCoordinatorData,
    MyLightSystemsDataUpdateCoordinator,
)
from .entity import IntegrationMyLightSystemsEntity
from .util.units import ws_to_kwh, ws_to_wh


@dataclass(frozen=True, kw_only=True)
class MyLightSensorEntityDescription(SensorEntityDescription):
    """Describes a sensor entity."""

    value_fn: Callable[[MyLightSystemsCoordinatorData], int | float | str | None]
    attributes_fn: Callable[[MyLightSystemsCoordinatorData], dict] | None = None


def _calculate_grid_returned_energy(data: MyLightSystemsCoordinatorData) -> float | None:
    """Calculate grid returned energy."""
    if data is None or data.produced_energy is None or data.green_energy is None:
        return None

    msb_charge_wh = ws_to_wh(data.msb_charge.value) if data.msb_charge is not None else 0
    result = ws_to_wh(data.produced_energy.value) - ws_to_wh(data.green_energy.value) - msb_charge_wh
    return result if result > 0 else 0


def _heater_attributes(data: MyLightSystemsCoordinatorData) -> dict:
    """Describe provenance without conflating a poll with a measured/decision timestamp."""
    h = data.water_heater
    if h is None:
        return {"discovery": "unavailable"}
    return {
        "discovery": h.discovery,
        "last_read": h.fetched_at.isoformat() if h.fetched_at else None,
        "power_measured_at": h.measured_at.isoformat() if h.measured_at else None,
        "effective_report_period": h.report_period,
        "green_play_ranges": h.green_play.ranges if h.green_play else None,
        "next_command": h.next_command,
    }


MYLIGHT_SENSORS: tuple[MyLightSensorEntityDescription, ...] = (
    MyLightSensorEntityDescription(
        key="total_solar_production",
        translation_key="total_solar_production",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        value_fn=lambda data: ws_to_wh(data.produced_energy.value) if data.produced_energy is not None else None,
    ),
    MyLightSensorEntityDescription(
        key="total_grid_consumption",
        translation_key="total_grid_consumption",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        value_fn=lambda data: ws_to_wh(data.grid_energy.value) if data.grid_energy is not None else None,
    ),
    MyLightSensorEntityDescription(
        key="total_grid_without_battery_consumption",
        translation_key="total_grid_without_battery_consumption",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        value_fn=lambda data: (
            ws_to_wh(data.grid_energy_without_battery.value) if data.grid_energy_without_battery is not None else None
        ),
    ),
    MyLightSensorEntityDescription(
        key="total_autonomy_rate",
        translation_key="total_autonomy_rate",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        # No SensorDeviceClass fits a 0-100% ratio; leaving None is intentional.
        device_class=None,
        suggested_display_precision=2,
        value_fn=lambda data: data.autonomy_rate.value if data.autonomy_rate is not None else None,
    ),
    MyLightSensorEntityDescription(
        key="total_self_conso",
        translation_key="total_self_conso",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        # No SensorDeviceClass fits a 0-100% ratio; leaving None is intentional.
        device_class=None,
        suggested_display_precision=2,
        value_fn=lambda data: data.self_conso.value if data.self_conso is not None else None,
    ),
    MyLightSensorEntityDescription(
        key="total_msb_charge",
        translation_key="total_msb_charge",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        value_fn=lambda data: ws_to_wh(data.msb_charge.value) if data.msb_charge is not None else None,
    ),
    MyLightSensorEntityDescription(
        key="total_msb_discharge",
        translation_key="total_msb_discharge",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        value_fn=lambda data: ws_to_wh(data.msb_discharge.value) if data.msb_discharge is not None else None,
    ),
    MyLightSensorEntityDescription(
        key="total_green_energy",
        translation_key="total_green_energy",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        value_fn=lambda data: ws_to_wh(data.green_energy.value) if data.green_energy is not None else None,
    ),
    MyLightSensorEntityDescription(
        key="battery_state",
        translation_key="battery_state",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        suggested_display_precision=2,
        value_fn=lambda data: ws_to_kwh(data.battery_state.value) if data.battery_state is not None else None,
    ),
    MyLightSensorEntityDescription(
        key="grid_returned_energy",
        translation_key="grid_returned_energy",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        value_fn=_calculate_grid_returned_energy,
    ),
    MyLightSensorEntityDescription(
        key="water_heater_power",
        translation_key="water_heater_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda data: data.water_heater.power if data.water_heater else None,
        attributes_fn=_heater_attributes,
    ),
    MyLightSensorEntityDescription(
        key="water_heater_green_play",
        translation_key="water_heater_green_play",
        value_fn=lambda data: (
            ("enabled" if data.water_heater.green_play.enabled else "disabled")
            if data.water_heater and data.water_heater.green_play
            else None
        ),
        attributes_fn=_heater_attributes,
    ),
    MyLightSensorEntityDescription(
        key="water_heater_energy",
        translation_key="water_heater_energy",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        value_fn=lambda data: (
            ws_to_wh(data.water_heater_energy.value) if data.water_heater_energy is not None else None
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: MyLightConfigEntry, async_add_devices: AddEntitiesCallback
) -> None:
    """Configure sensor platform."""
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [
        MyLightSystemsSensor(
            entry_id=entry.entry_id,
            coordinator=coordinator,
            entity_description=entity_description,
        )
        for entity_description in MYLIGHT_SENSORS
    ]

    capacity = entry.data.get(CONF_ELECTRIC_POWER_CAPACITY)
    if capacity is not None:
        entities.append(
            MyLightElectricPowerCapacitySensor(
                entry_id=entry.entry_id,
                coordinator=coordinator,
                value=float(capacity),
            )
        )

    async_add_devices(entities)


class MyLightSystemsSensor(IntegrationMyLightSystemsEntity, SensorEntity):
    """MyLightSystems Sensor class."""

    entity_description: MyLightSensorEntityDescription

    def __init__(
        self,
        entry_id: str,
        coordinator: MyLightSystemsDataUpdateCoordinator,
        entity_description: MyLightSensorEntityDescription,
    ) -> None:
        """Init."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_{entity_description.key}"
        self.entity_description = entity_description

    @property
    def native_value(self) -> int | float | str | None:
        """Return the state."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return read-only heater observations when relevant."""
        fn = self.entity_description.attributes_fn
        return fn(self.coordinator.data) if fn else None

    @property
    def available(self) -> bool:
        """Return True if last update was successful."""
        return self.coordinator.last_update_success


class MyLightElectricPowerCapacitySensor(IntegrationMyLightSystemsEntity, SensorEntity):
    """Static sensor exposing the subscribed electrical power (kVA)."""

    _attr_translation_key = "electric_power_capacity"
    _attr_native_unit_of_measurement = UnitOfApparentPower.KILO_VOLT_AMPERE
    _attr_device_class = SensorDeviceClass.APPARENT_POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0

    def __init__(
        self,
        entry_id: str,
        coordinator: MyLightSystemsDataUpdateCoordinator,
        value: float,
    ) -> None:
        """Init."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_electric_power_capacity"
        self._attr_native_value = value

    @property
    def available(self) -> bool:
        """Always available — value is static, stored in config entry data."""
        return True
