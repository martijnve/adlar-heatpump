"""Select platform for Adlar Heatpump (modes, curves, and P/L enums in expert mode)."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_EXPERT_MODE, DOMAIN
from .coordinator import AdlarCoordinator
from .entity import AdlarRegisterEntity
from .registers import REGISTERS, R, is_writable


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: AdlarCoordinator = hass.data[DOMAIN][entry.entry_id]
    expert = entry.options.get(CONF_EXPERT_MODE, False)
    async_add_entities(
        AdlarSelect(coordinator, reg)
        for reg in REGISTERS
        if is_writable(reg, expert) and reg.options is not None
    )


class AdlarSelect(AdlarRegisterEntity, SelectEntity):
    _writable = True

    def __init__(self, coordinator: AdlarCoordinator, reg: R) -> None:
        super().__init__(coordinator, reg, f"sel_{reg.addr:04X}")
        self._values = {label: value for value, label in reg.options.items()}

    @property
    def options(self) -> list[str]:
        return self._option_labels()

    @property
    def current_option(self) -> str | None:
        return self._option_label()

    async def async_select_option(self, option: str) -> None:
        if option not in self._values:
            raise ServiceValidationError(f"{option} can't be written to {self._reg.name}")
        await self.coordinator.async_write_value(self._reg, self._values[option])
