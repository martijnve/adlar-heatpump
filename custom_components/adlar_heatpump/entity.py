"""Base entity for Adlar Heatpump."""
from __future__ import annotations

from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEVICE_NAME, DOMAIN
from .coordinator import AdlarCoordinator
from .registers import LIMIT, VERSION, R, is_param


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
        # An installer parameter exists only because the user chose to show it: enabled
        self._attr_entity_registry_enabled_default = reg.enabled or is_param(reg)
        secondary = is_param(reg) or reg.group in (LIMIT, VERSION) or not reg.enabled
        if secondary and self._writable:
            self._attr_entity_category = EntityCategory.CONFIG
        elif secondary:
            # Home Assistant doesn't allow the config category on read-only platforms
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    _writable = False

    @property
    def _raw_value(self):
        return self.coordinator.data.get(self._reg.addr)

    def _option_labels(self) -> list[str]:
        """Option labels, plus one for a value the register map doesn't know.

        Home Assistant drops a state that isn't in the options, so the unknown value
        gets a label of its own instead of showing as unknown.
        """
        labels = list(self._reg.options.values())
        raw = self._raw_value
        if raw is not None and raw not in self._reg.options:
            labels.append(unknown_label(raw))
        return labels

    def _option_label(self) -> str | None:
        raw = self._raw_value
        if raw is None:
            return None
        return self._reg.options.get(raw, unknown_label(raw))


def unknown_label(raw: int) -> str:
    return f"Unknown ({raw})"
