"""Number platform for Adlar Heatpump (setpoints, and P/L parameters in expert mode)."""
from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_EXPERT_MODE, DOMAIN
from .coordinator import AdlarCoordinator
from .entity import AdlarRegisterEntity
from .registers import REGISTERS, SWITCH_REGISTER, R, is_writable


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: AdlarCoordinator = hass.data[DOMAIN][entry.entry_id]
    expert = entry.options.get(CONF_EXPERT_MODE, False)
    async_add_entities(
        AdlarNumber(coordinator, reg)
        for reg in REGISTERS
        if is_writable(reg, expert) and reg.options is None and reg.addr != SWITCH_REGISTER
    )


class AdlarNumber(AdlarRegisterEntity, NumberEntity):
    _writable = True
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: AdlarCoordinator, reg: R) -> None:
        super().__init__(coordinator, reg, f"num_{reg.addr:04X}")
        self._attr_native_unit_of_measurement = {"days": "d"}.get(reg.unit, reg.unit)
        if reg.unit == "°C":
            self._attr_device_class = NumberDeviceClass.TEMPERATURE
        self._attr_native_min_value = reg.min
        self._attr_native_max_value = reg.max
        # R290 units take tenths of a degree
        self._attr_native_step = coordinator.temperature_scale if reg.temp else reg.scale

    @property
    def native_value(self) -> float | None:
        return self._raw_value

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_write_value(self._reg, value)
