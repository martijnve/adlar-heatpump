"""Sensor platform for Adlar Heatpump."""
from __future__ import annotations

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_PARAMS, DOMAIN
from .coordinator import AdlarCoordinator
from .entity import AdlarEntity, AdlarRegisterEntity
from .registers import (
    REFRIGERANT_REGISTER,
    REFRIGERANT_TYPES,
    REGISTERS,
    SENSOR,
    R,
    is_shown,
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

# Reads in a row a kWh counter must show a lower value before the drop is published
COUNTER_DROP_READS = 3


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: AdlarCoordinator = hass.data[DOMAIN][entry.entry_id]
    params = entry.options.get(CONF_PARAMS, {})

    # Every shown register that isn't a user control is a sensor
    entities: list[SensorEntity] = [
        (AdlarEnergyCounter if reg.unit == "kWh" else AdlarSensor)(coordinator, reg)
        for reg in REGISTERS
        if is_shown(reg, params) and not is_writable(reg)
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
        elif reg.addr in VERSION_REGISTERS:
            pass
        else:
            self._attr_native_unit_of_measurement = unit
            # A temperature difference must not be converted like an absolute temperature
            if not reg.delta:
                self._attr_device_class = DEVICE_CLASS_BY_UNIT.get(unit)
            if reg.unit == "kWh":
                # A drop of the counter (controller reset, 16-bit wrap) starts a new cycle
                self._attr_state_class = SensorStateClass.TOTAL_INCREASING
                self._attr_icon = "mdi:counter"
            elif reg.group == SENSOR:
                self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def options(self) -> list[str] | None:
        return self._option_labels() if self._reg.options is not None else None

    @property
    def native_value(self):
        value = self._raw_value
        if value is None:
            return None
        if self._reg.options is not None:
            return self._option_label()
        if self._reg.addr in VERSION_REGISTERS:
            return f"{value // 100}.{value // 10 % 10}.{value % 10}"
        return value


class AdlarEnergyCounter(AdlarSensor, RestoreSensor):
    """kWh counter that ignores a one-off lower reading.

    Home Assistant takes any drop of a total_increasing sensor as a meter reset and adds the
    next reading in full, so 2985 -> 0 -> 2985 would count 2985 kWh twice. A real drop
    (controller reset, 16-bit wrap) is published once COUNTER_DROP_READS fresh reads agree.
    """

    _held = None    # last accepted value; survives failed reads and, restored, a reload
    _low_reads = 0
    _seen_reads = 0  # coordinator.reads for this register when last looked at

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_sensor_data()) is not None:
            self._held = last.native_value
        self._track()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._track()
        super()._handle_coordinator_update()

    def _track(self) -> None:
        reads = self.coordinator.reads[self._reg.addr]
        value = self._raw_value
        if value is None or reads == self._seen_reads:
            return
        self._seen_reads = reads
        if self._held is None or value >= self._held:
            self._held, self._low_reads = value, 0
            return
        self._low_reads += 1
        if self._low_reads >= COUNTER_DROP_READS:
            self._held, self._low_reads = value, 0

    @property
    def native_value(self):
        return None if self._raw_value is None else self._held


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
