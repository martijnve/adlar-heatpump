"""Switch platform for Adlar Heatpump (ON/OFF and command coils)."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AdlarCoordinator
from .entity import AdlarEntity
from .registers import BY_ADDR, COILS, SWITCH_REGISTER


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: AdlarCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SwitchEntity] = [AdlarSwitch(coordinator)]
    entities += [AdlarCoilSwitch(coordinator, addr, name) for addr, name in COILS.items()]
    async_add_entities(entities)


class AdlarSwitch(AdlarEntity, SwitchEntity):
    _attr_name = "Heatpump ON/OFF"

    def __init__(self, coordinator: AdlarCoordinator) -> None:
        super().__init__(coordinator, "onoff")

    @property
    def is_on(self) -> bool | None:
        raw = self.coordinator.data.get(SWITCH_REGISTER)
        return None if raw is None else bool(raw)

    async def _write(self, value: int) -> None:
        await self.hass.async_add_executor_job(
            self.coordinator.write_value, BY_ADDR[SWITCH_REGISTER], value
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs) -> None:
        await self._write(1)

    async def async_turn_off(self, **kwargs) -> None:
        await self._write(0)


class AdlarCoilSwitch(AdlarEntity, SwitchEntity):
    """Command coil, read with FC01 and written with FC05."""

    def __init__(self, coordinator: AdlarCoordinator, addr: int, name: str) -> None:
        super().__init__(coordinator, f"coil_{addr:04X}")
        self._addr = addr
        self._attr_name = name

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.get(self._addr)

    async def _write(self, value: bool) -> None:
        await self.hass.async_add_executor_job(
            self.coordinator.write_coil, self._addr, value
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs) -> None:
        await self._write(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._write(False)
