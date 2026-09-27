"""Climate platform for Adlar Heatpump."""
from __future__ import annotations

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.climate.const import (
    ATTR_HVAC_MODE,
    PRESET_BOOST,
    PRESET_ECO,
    PRESET_NONE,
    HVACAction,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AdlarCoordinator
from .entity import AdlarEntity
from .registers import BY_ADDR, SWITCH_REGISTER

# Modbus register addresses
_MODE_REGISTER = 0x0304
_RUNNING_MODE_REGISTER = 0x0307
_SETPOINT_COOLING = 0x0300
_SETPOINT_HEATING = 0x0301
_SETPOINT_FLOOR = 0x0303
_WATER_INLET_TEMP = 0x004F
_COMPRESSOR_FREQUENCY = 0x0040

# Mode register values: 0 Cooling, 1 Heating, 2 Hot Water, 3 Floor Heating,
# 4 Hot Water + Cooling, 5 Hot Water + Heating, 7 Hot Water + Floor Heating.
# The climate entity covers space heating/cooling only: Hot Water alone shows as OFF (as
# upstream did), and a hot water combination shows as its space mode.
_MODBUS_TO_HVAC = {
    0: HVACMode.COOL, 1: HVACMode.HEAT, 3: HVACMode.HEAT_COOL,
    4: HVACMode.COOL, 5: HVACMode.HEAT, 7: HVACMode.HEAT_COOL,
}
_HOT_WATER_MODES = {2, 4, 5, 7}
# Mode to write for an HVAC mode, without and with hot water
_HVAC_TO_MODBUS = {
    HVACMode.COOL: (0, 4),
    HVACMode.HEAT: (1, 5),
    HVACMode.HEAT_COOL: (3, 7),
}
_HVAC_TO_SETPOINT = {
    HVACMode.COOL: _SETPOINT_COOLING,
    HVACMode.HEAT: _SETPOINT_HEATING,
    HVACMode.HEAT_COOL: _SETPOINT_FLOOR,
}

# Preset modes
_PRESET_TO_MODBUS = {
    PRESET_NONE:  0,  # Standard
    PRESET_BOOST: 1,  # Boost
    PRESET_ECO:   2,  # Silent
}
_MODBUS_TO_PRESET = {v: k for k, v in _PRESET_TO_MODBUS.items()}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: AdlarCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AdlarClimate(coordinator)])


class AdlarClimate(AdlarEntity, ClimateEntity):
    """Climate entity for Adlar Aurora II."""

    _attr_name = "Adlar Heatpump"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT, HVACMode.HEAT_COOL]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE |
        ClimateEntityFeature.PRESET_MODE |
        ClimateEntityFeature.TURN_ON |
        ClimateEntityFeature.TURN_OFF
    )
    _attr_preset_modes = [PRESET_NONE, PRESET_BOOST, PRESET_ECO]

    def __init__(self, coordinator: AdlarCoordinator) -> None:
        super().__init__(coordinator, "climate")
        self._attr_target_temperature_step = coordinator.temperature_scale

    @property
    def _mode(self) -> int | None:
        return self.coordinator.data.get(_MODE_REGISTER)

    @property
    def _setpoint_register(self) -> int | None:
        return _HVAC_TO_SETPOINT.get(_MODBUS_TO_HVAC.get(self._mode))

    @property
    def current_temperature(self) -> float | None:
        return self.coordinator.data.get(_WATER_INLET_TEMP)

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        if not self.coordinator.data.get(SWITCH_REGISTER):
            return HVACMode.OFF
        return _MODBUS_TO_HVAC.get(self._mode, HVACMode.OFF)

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return current action based on compressor frequency."""
        mode = self.hvac_mode
        if mode == HVACMode.OFF:
            return HVACAction.OFF
        if (self.coordinator.data.get(_COMPRESSOR_FREQUENCY) or 0) > 0:
            return HVACAction.COOLING if mode == HVACMode.COOL else HVACAction.HEATING
        return HVACAction.IDLE

    @property
    def target_temperature(self) -> float | None:
        """Return setpoint for current mode."""
        register = self._setpoint_register
        return self.coordinator.data.get(register) if register else None

    @property
    def min_temp(self) -> float:
        reg = BY_ADDR.get(self._setpoint_register or _SETPOINT_HEATING)
        return float(reg.min)

    @property
    def max_temp(self) -> float:
        reg = BY_ADDR.get(self._setpoint_register or _SETPOINT_HEATING)
        return float(reg.max)

    @property
    def preset_mode(self) -> str | None:
        """Return current preset (Standard/Boost/Silent)."""
        return _MODBUS_TO_PRESET.get(
            self.coordinator.data.get(_RUNNING_MODE_REGISTER), PRESET_NONE
        )

    async def _write(self, address: int, value: float) -> None:
        await self.coordinator.async_write_value(BY_ADDR[address], value)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode (Standard/Boost/Silent)."""
        await self._write(_RUNNING_MODE_REGISTER, _PRESET_TO_MODBUS.get(preset_mode, 0))

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode (on/off + mode register).

        A running hot water function is kept: HEAT from Hot Water writes Hot Water + Heating.
        Each write raises on failure, so the unit isn't switched on after a failed mode write.
        """
        if hvac_mode == HVACMode.OFF:
            await self._write(SWITCH_REGISTER, 0)
            return
        without_dhw, with_dhw = _HVAC_TO_MODBUS[hvac_mode]
        target = with_dhw if self._mode in _HOT_WATER_MODES else without_dhw
        if self._mode != target:
            await self._write(_MODE_REGISTER, target)
        if not self.coordinator.data.get(SWITCH_REGISTER):
            await self._write(SWITCH_REGISTER, 1)

    async def async_turn_on(self) -> None:
        await self._write(SWITCH_REGISTER, 1)

    async def async_turn_off(self) -> None:
        await self._write(SWITCH_REGISTER, 0)

    async def async_set_temperature(self, **kwargs) -> None:
        """Set the target temperature, switching mode first when `hvac_mode` is given."""
        hvac_mode = kwargs.get(ATTR_HVAC_MODE)
        if hvac_mode is not None:
            await self.async_set_hvac_mode(hvac_mode)
            if hvac_mode == HVACMode.OFF:
                return
        temp = kwargs.get(ATTR_TEMPERATURE)
        register = self._setpoint_register
        if temp is None or register is None:
            return
        reg = BY_ADDR[register]
        if not reg.min <= temp <= reg.max:
            raise ServiceValidationError(
                f"{temp} is outside {reg.name} range {reg.min}-{reg.max}"
            )
        await self._write(register, temp)
