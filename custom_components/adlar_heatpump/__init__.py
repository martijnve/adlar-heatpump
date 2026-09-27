"""Adlar Heatpump (Aurora II) integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_EXPERT_MODE,
    CONF_PARAMS,
    CONF_SLAVE,
    CONF_SLOW_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE,
    DEFAULT_SLOW_INTERVAL,
    DOMAIN,
)
from .coordinator import AdlarCoordinator
from .registers import (
    EDITABLE,
    HIDDEN,
    READ_ONLY,
    REGISTERS,
    can_edit,
    is_param,
    param_key,
    param_mode,
)

_LOGGER = logging.getLogger(__name__)

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
        params=entry.options.get(CONF_PARAMS, {}),
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    _sync_param_entities(hass, entry)
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


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """1.1 → 1.2: the expert mode switch becomes a choice per installer parameter.

    Expert mode on: every parameter that can be edited becomes editable, the rest
    read-only. Expert mode off: parameters whose sensor the user had enabled stay
    read-only, the others hidden.
    """
    if entry.version > 1:
        return False
    if entry.minor_version < 2:
        options = dict(entry.options)
        expert = options.pop(CONF_EXPERT_MODE, False)
        registry = er.async_get(hass)
        params: dict[str, str] = {}
        for reg in REGISTERS:
            if not is_param(reg):
                continue
            if expert:
                params[param_key(reg)] = EDITABLE if can_edit(reg) else READ_ONLY
                continue
            sensor_id = registry.async_get_entity_id(
                "sensor", DOMAIN, f"{entry.entry_id}_{reg.addr:04X}"
            )
            if sensor_id and not registry.async_get(sensor_id).disabled_by:
                params[param_key(reg)] = READ_ONLY
        options[CONF_PARAMS] = params
        hass.config_entries.async_update_entry(entry, options=options, minor_version=2)
        _LOGGER.info("Migrated expert mode (%s) to %d shown parameters", expert, len(params))
    return True


def _sync_param_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Make the registry match the user's choice per installer parameter.

    Hidden: the entries on every platform go. Read-only (sensor) or editable
    (number/select): the entry of the other platform moves over with the user's settings
    (hidden, name, icon, area, entity_id object id, and disabled when the user disabled
    it). The user chose to show the parameter, so it isn't left disabled by default.
    """
    params = entry.options.get(CONF_PARAMS, {})
    registry = er.async_get(hass)
    prefix = entry.entry_id
    for reg in REGISTERS:
        if not is_param(reg):
            continue
        sensor = ("sensor", f"{prefix}_{reg.addr:04X}")
        writable = ("select", f"{prefix}_sel_{reg.addr:04X}") if reg.options is not None \
            else ("number", f"{prefix}_num_{reg.addr:04X}")
        mode = param_mode(reg, params)
        if mode == HIDDEN:
            for domain, unique_id in (sensor, writable):
                if entity_id := registry.async_get_entity_id(domain, DOMAIN, unique_id):
                    registry.async_remove(entity_id)
            continue
        new, old = (writable, sensor) if mode == EDITABLE else (sensor, writable)
        new_id = registry.async_get_entity_id(new[0], DOMAIN, new[1])
        old_id = registry.async_get_entity_id(old[0], DOMAIN, old[1])
        if old_id is not None:
            old_entry = registry.async_get(old_id)
            registry.async_remove(old_id)
            if new_id is None:
                user_disabled = old_entry.disabled_by == er.RegistryEntryDisabler.USER
                new_entry = registry.async_get_or_create(
                    new[0], DOMAIN, new[1],
                    config_entry=entry,
                    suggested_object_id=old_id.split(".", 1)[1],
                    disabled_by=old_entry.disabled_by if user_disabled else None,
                    hidden_by=old_entry.hidden_by,
                )
                registry.async_update_entity(
                    new_entry.entity_id,
                    name=old_entry.name,
                    icon=old_entry.icon,
                    area_id=old_entry.area_id,
                )
                continue
        # Created disabled by an earlier default; the user has now chosen to show it
        if new_id is not None and (
            registry.async_get(new_id).disabled_by == er.RegistryEntryDisabler.INTEGRATION
        ):
            registry.async_update_entity(new_id, disabled_by=None)
