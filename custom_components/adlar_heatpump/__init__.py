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
from .registers import PARAM, REGISTERS, is_writable

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
    _remove_switched_param_entities(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


def _remove_switched_param_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Drop the registry entries of P/L parameters that moved platform with expert mode.

    A parameter is a sensor when read-only and a number/select when writable; the unused
    one would otherwise linger as an orphaned, unavailable entity.
    """
    expert = entry.options.get(CONF_EXPERT_MODE, False)
    registry = er.async_get(hass)
    prefix = entry.entry_id
    for reg in REGISTERS:
        if reg.group != PARAM or not is_writable(reg, True):
            continue
        if is_writable(reg, expert):
            stale = [("sensor", f"{prefix}_{reg.addr:04X}")]
        else:
            stale = [("number", f"{prefix}_num_{reg.addr:04X}"), ("select", f"{prefix}_sel_{reg.addr:04X}")]
        for domain, unique_id in stale:
            if entity_id := registry.async_get_entity_id(domain, DOMAIN, unique_id):
                registry.async_remove(entity_id)
