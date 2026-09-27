"""Base entity for Adlar Heatpump."""
from __future__ import annotations

from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEVICE_NAME, DOMAIN
from .coordinator import AdlarCoordinator
from .registers import CONTROL, LIMIT, PARAM, SENSOR, VERSION, R


class AdlarEntity(CoordinatorEntity[AdlarCoordinator]):
    """Shares the device and the unique_id prefix."""

    def __init__(self, coordinator: AdlarCoordinator, unique_suffix: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{unique_suffix}"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.coordinator.config_entry.entry_id)},
            "name": DEVICE_NAME,
            "manufacturer": "Adlar",
            "model": "Aurora II",
        }


class AdlarRegisterEntity(AdlarEntity):
    """Entity backed by one holding register."""

    def __init__(self, coordinator: AdlarCoordinator, reg: R, unique_suffix: str) -> None:
        super().__init__(coordinator, unique_suffix)
        self._reg = reg
        self._attr_name = reg.name
        self._attr_entity_registry_enabled_default = reg.enabled and reg.group != PARAM
        if reg.group in (LIMIT, VERSION) or (reg.group == PARAM and not self._writable):
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        elif reg.group == PARAM or (reg.group == CONTROL and not reg.enabled):
            self._attr_entity_category = EntityCategory.CONFIG
        elif reg.group == SENSOR and not reg.enabled:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    _writable = False

    @property
    def _raw_value(self):
        return self.coordinator.data.get(self._reg.addr)
