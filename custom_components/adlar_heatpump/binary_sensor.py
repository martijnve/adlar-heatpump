"""Binary sensor platform for Adlar Heatpump (status, fault, relay and switch-port bits)."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AdlarCoordinator
from .entity import AdlarEntity
from .registers import (
    BITMASKS,
    COMPRESSORS_REGISTER,
    STATUS1_NAMES,
    SYSTEM1_FAULT_REGISTERS,
    SYSTEM2_OFFSET,
)

STATUS_REGISTERS = (0x0000, 0x0001)
RELAY_SWITCH_REGISTERS = range(0x0019, 0x0020)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: AdlarCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for addr, (reg_name, bits) in BITMASKS.items():
        for mask, bit_name in bits.items():
            entities.append(AdlarBitSensor(coordinator, addr, mask, reg_name, bit_name))

    # Dual-compressor units report System 2 faults at +5 with the System 1 layout
    if coordinator.data.get(COMPRESSORS_REGISTER) == 2:
        for addr in SYSTEM1_FAULT_REGISTERS:
            reg_name, bits = BITMASKS[addr]
            for mask, bit_name in bits.items():
                entities.append(AdlarBitSensor(
                    coordinator, addr + SYSTEM2_OFFSET, mask,
                    reg_name.replace("System 1", "System 2"), bit_name,
                ))

    async_add_entities(entities)


class AdlarBitSensor(AdlarEntity, BinarySensorEntity):
    """One bit of a status/fault/relay/switch-port register."""

    def __init__(self, coordinator, addr: int, mask: int, reg_name: str, bit_name: str):
        if addr == 0x0000:
            # Unique IDs and names as upstream had them
            super().__init__(coordinator, f"status_{mask:04X}")
            self._attr_name = STATUS1_NAMES.get(mask, f"Running Status: {bit_name}")
        else:
            super().__init__(coordinator, f"bit_{addr:04X}_{mask:04X}")
            self._attr_name = f"{reg_name}: {bit_name}"
        self._addr = addr
        self._mask = mask

        if addr in RELAY_SWITCH_REGISTERS:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
            self._attr_entity_registry_enabled_default = False
        elif addr not in STATUS_REGISTERS:
            self._attr_device_class = BinarySensorDeviceClass.PROBLEM
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        elif addr == 0x0000 and mask == 0x0008:
            self._attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self) -> bool | None:
        raw = self.coordinator.data.get(self._addr)
        return None if raw is None else bool(raw & self._mask)
