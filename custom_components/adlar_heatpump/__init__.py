"""Adlar Heatpump (Aurora II) integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_EXPERT_MODE,
    CONF_SLAVE,
    CONF_SLOW_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE,
    DEFAULT_SLOW_INTERVAL,
    DOMAIN,
)
from .coordinator import AdlarCoordinator
from .registers import REGISTERS, is_writable

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.NUMBER, Platform.SWITCH, Platform.SELECT, Platform.CLIMATE]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Options override the values given at setup (the options flow edits scan interval)
    config = {**entry.data, **entry.options}
    coordinator = AdlarCoordinator(
        hass,
        entry,
        host=config[CONF_HOST],
        port=config.get(CONF_PORT, DEFAULT_PORT),
        slave=config.get(CONF_SLAVE, DEFAULT_SLAVE),
        scan_interval=config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        slow_interval=config.get(CONF_SLOW_INTERVAL, DEFAULT_SLOW_INTERVAL),
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    _migrate_switched_entities(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        coordinator: AdlarCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await hass.async_add_executor_job(coordinator.close)
    return unloaded


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


def _migrate_switched_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Move registry entries of registers that change platform with expert mode.

    A register is a sensor when read-only and a number/select when writable. The entry of
    the platform no longer used is replaced by one for the new platform that keeps the
    user's settings (enabled/hidden, name, icon, area, entity_id object id).
    """
    expert = entry.options.get(CONF_EXPERT_MODE, False)
    registry = er.async_get(hass)
    prefix = entry.entry_id
    for reg in REGISTERS:
        if is_writable(reg, True) == is_writable(reg, False):
            continue
        sensor = ("sensor", f"{prefix}_{reg.addr:04X}")
        writable = ("select", f"{prefix}_sel_{reg.addr:04X}") if reg.options is not None \
            else ("number", f"{prefix}_num_{reg.addr:04X}")
        old, new = (sensor, writable) if is_writable(reg, expert) else (writable, sensor)
        old_id = registry.async_get_entity_id(old[0], DOMAIN, old[1])
        if old_id is None:
            continue
        old_entry = registry.async_get(old_id)
        registry.async_remove(old_id)
        if registry.async_get_entity_id(new[0], DOMAIN, new[1]):
            continue
        new_entry = registry.async_get_or_create(
            new[0], DOMAIN, new[1],
            config_entry=entry,
            suggested_object_id=old_id.split(".", 1)[1],
            disabled_by=old_entry.disabled_by,
            hidden_by=old_entry.hidden_by,
        )
        registry.async_update_entity(
            new_entry.entity_id,
            name=old_entry.name,
            icon=old_entry.icon,
            area_id=old_entry.area_id,
        )
