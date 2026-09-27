"""Sensor platform for Adlar Heatpump."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_EXPERT_MODE, DOMAIN
from .coordinator import AdlarCoordinator
from .entity import AdlarEntity, AdlarRegisterEntity
from .registers import (
    CONTROL,
    PARAM,
    REFRIGERANT_REGISTER,
    REFRIGERANT_TYPES,
    REGISTERS,
    SENSOR,
    R,
    is_writable,
)

DEVICE_CLASS_BY_UNIT = {
    "°C": SensorDeviceClass.TEMPERATURE,
    "Hz": SensorDeviceClass.FREQUENCY,
    "V": SensorDeviceClass.VOLTAGE,
    "A": SensorDeviceClass.CURRENT,
    "W": SensorDeviceClass.POWER,
    "kW": SensorDeviceClass.POWER,
    "kWh": SensorDeviceClass.ENERGY,
    "L/min": SensorDeviceClass.VOLUME_FLOW_RATE,
    "s": SensorDeviceClass.DURATION,
    "min": SensorDeviceClass.DURATION,
    "d": SensorDeviceClass.DURATION,
}
# Units the register map spells differently from Home Assistant
HA_UNIT = {"RPM": "rpm", "days": "d"}

# Encoded as major*100 + minor*10 + patch (433 = V4.3.3)
VERSION_REGISTERS = (0x0360, 0x0363)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: AdlarCoordinator = hass.data[DOMAIN][entry.entry_id]
    expert = entry.options.get(CONF_EXPERT_MODE, False)

    entities: list[SensorEntity] = [
        AdlarSensor(coordinator, reg)
        for reg in REGISTERS
        if reg.group != CONTROL and not (reg.group == PARAM and is_writable(reg, expert))
    ]
    entities.append(AdlarThermalPowerSensor(coordinator))
    entities.append(AdlarCOPSensor(coordinator))
    entities.append(AdlarCalculatedPowerSensor(coordinator))
    entities.append(AdlarRefrigerantSensor(coordinator))

    async_add_entities(entities)


class AdlarSensor(AdlarRegisterEntity, SensorEntity):
    """Read-only view of one register."""

    def __init__(self, coordinator: AdlarCoordinator, reg: R) -> None:
        super().__init__(coordinator, reg, f"{reg.addr:04X}")
        unit = HA_UNIT.get(reg.unit, reg.unit)
        if reg.options is not None:
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = list(reg.options.values())
        elif reg.addr in VERSION_REGISTERS:
            pass
        else:
            self._attr_native_unit_of_measurement = unit
            self._attr_device_class = DEVICE_CLASS_BY_UNIT.get(unit)
            if reg.unit == "kWh":
                # TOTAL so HA treats a drop (counter reset) as a reset, not an error
                self._attr_state_class = SensorStateClass.TOTAL
                self._attr_icon = "mdi:counter"
            elif reg.group == SENSOR:
                self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        value = self._raw_value
        if value is None:
            return None
        if self._reg.options is not None:
            return self._reg.options.get(value)
        if self._reg.addr in VERSION_REGISTERS:
            return f"{value // 100}.{value // 10 % 10}.{value % 10}"
        return value


class AdlarThermalPowerSensor(AdlarEntity, SensorEntity):
    """Thermal power output calculated from flow and delta-T."""

    _attr_name = "Thermal Power"
    _attr_native_unit_of_measurement = "kW"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:heat-wave"

    def __init__(self, coordinator: AdlarCoordinator) -> None:
        super().__init__(coordinator, "thermal_power")

    @property
    def native_value(self) -> float | None:
        return thermal_power(self.coordinator.data)


class AdlarCOPSensor(AdlarEntity, SensorEntity):
    """COP = Thermal Power / Electrical Power."""

    _attr_name = "COP"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:lightning-bolt-circle"

    def __init__(self, coordinator: AdlarCoordinator) -> None:
        super().__init__(coordinator, "cop")

    @property
    def native_value(self) -> float | None:
        thermal_kw = thermal_power(self.coordinator.data)
        electrical_kw = self.coordinator.data.get(0x005C) or 0
        if thermal_kw is None or electrical_kw <= 0:
            return None
        return round(thermal_kw / electrical_kw, 2)


class AdlarCalculatedPowerSensor(AdlarEntity, SensorEntity):
    """Estimated power = AC input voltage × calibrated AC input current."""

    _attr_name = "Calculated Power"
    _attr_native_unit_of_measurement = "W"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:flash"

    def __init__(self, coordinator: AdlarCoordinator) -> None:
        super().__init__(coordinator, "calculated_power")

    @property
    def native_value(self) -> float | None:
        voltage = self.coordinator.data.get(0x0044) or 0
        current = self.coordinator.data.get(0x0045)
        if voltage <= 0 or current is None:
            return None
        return round(voltage * current, 1)


class AdlarRefrigerantSensor(AdlarEntity, SensorEntity):
    """Koelmiddeltype sensor — toont R32/R290/R410A op basis van P119 (0x0177)."""

    _attr_name = "Refrigerant Type"
    _attr_icon = "mdi:molecule"

    def __init__(self, coordinator: AdlarCoordinator) -> None:
        super().__init__(coordinator, "refrigerant_type")

    @property
    def native_value(self):
        raw = self.coordinator.refrigerant_type
        if raw is None:
            return "Unknown"
        return REFRIGERANT_TYPES.get(raw, f"Unknown ({raw})")

    @property
    def extra_state_attributes(self):
        return {
            "temperature_scale": self.coordinator.temperature_scale,
            "p119_register": f"0x{REFRIGERANT_REGISTER:04X}",
        }


def thermal_power(data: dict) -> float | None:
    """kW from water flow (L/min) and outlet minus inlet temperature."""
    flow, t_in, t_out = data.get(0x0058), data.get(0x004F), data.get(0x0050)
    if flow is None or t_in is None or t_out is None:
        return None
    return round(flow * (t_out - t_in) * 4.186 / 60, 2)
