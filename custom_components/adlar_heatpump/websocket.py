"""Websocket API of the parameter panel. Every command is admin only.

A parameter is addressed by its `key`: the register address as four upper-case hex digits
("0163"). A value is a number in the parameter's unit; for a parameter with `options` it
is the `value` of one of them. Values the heat pump did not give are null.

Errors come as the websocket error `{code, message}`: `unauthorized` for a user who is no
admin, `invalid_format` for a malformed request, `home_assistant_error` for everything
else, with a `message` to show the user (unknown entry, entry not loaded, value refused,
heat pump not answering, read-back mismatch).

adlar_heatpump/list
    Request: `entry_id` (optional; default: the first entry).
    Reads no parameters from the heat pump, only DC pump control, for `pump_manual`.
    Result:
        entries          [{entry_id, title, loaded}]: the heat pumps; `loaded` is false
                         while one cannot be reached (or is disabled or reloading)
        entry_id         the entry the fields below are about; null when there is none
        groups           [{id, title, parameters: [parameter]}]; empty when there is no entry
        recommended      [key]: the recommended set of sensors
        pump_manual      true while DC pump control is not on Auto; null when unknown
        baseline_set_at  ISO timestamp of the last set_baseline; null while the baseline
                         is the defaults of the HHI reference
    parameter:
        key          "0163"
        code         "P99", "L13"; null for the DC pump pair
        name         without the code
        description  text or null
        unit         text or null
        min, max     numbers or null
        step         number; null for a parameter with options
        options      [{value, label}] or null
        can_edit     whether `write` accepts it (false: protected, or no known range)
        warning      "factory", "protection", "dc_pump" or null
        sensor       shown as a sensor entity
        automation   the set_parameter service may write it
        baseline     value to compare with, or null when it has none
        value        last value read; null when not loaded or not read yet (a parameter
                     without a sensor is only read by read_group, export and set_baseline)

adlar_heatpump/read_group
    Request: `entry_id`, `group` (a group id from list).
    Reads the group's parameters from the heat pump now; the sensors follow.
    Result: {values: {key: value}}

adlar_heatpump/write
    Request: `entry_id`, `key`, `value`.
    Writes one parameter and reads it back. Refused, with nothing sent to the heat pump:
    a parameter that is not `can_edit`, a value outside min..max, off the step grid or not
    one of the options. A read-back that differs from the value written is an error that
    names both; so is a read-back without an answer. Every write that went out leaves a
    logbook entry on the device.
    Result: {value}: the value read back

adlar_heatpump/set_choices
    Request: `entry_id`, `sensors` [key], `automations` [key]: the complete new sets.
    Stores which parameters are sensors and which the service may write. Only `can_edit`
    parameters may be in `automations`. A change reloads the entry: the answer comes when
    the reload is done, and values of parameters without a sensor are gone until read again.
    Result: null

adlar_heatpump/export
    Request: `entry_id`.
    Reads every parameter from the heat pump, protected ones included.
    Result: {parameters: [{code, key, name, value, unit, raw}]}; `raw` is the register
    word (0..65535)

adlar_heatpump/set_baseline
    Request: `entry_id`.
    Reads every parameter and stores the values as the baseline, replacing the previous one.
    Result: {baseline_set_at}
"""
from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import CONF_AUTOMATION_PARAMS, CONF_PARAMS, DOMAIN
from .coordinator import AdlarCoordinator, loaded_coordinator
from .param_info import (
    DC_PUMP_CONTROL_REGISTER,
    DESCRIPTIONS,
    PARAM_GROUPS,
    PARAMS,
    REFERENCE_DEFAULTS,
    group_params,
    param_code,
    param_name,
    param_step,
    recommended_params,
    warning_class,
)
from .registers import READ_ONLY, R, can_edit, param_key

ENTRY_ID = {vol.Required("entry_id"): str}


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register the websocket commands."""
    for command in (ws_list, ws_read_group, ws_write, ws_set_choices, ws_export, ws_set_baseline):
        websocket_api.async_register_command(hass, command)


def baseline_store(hass: HomeAssistant, entry_id: str) -> Store:
    """Where set_baseline keeps {"set_at", "values": {key: value}}.

    Not in the config entry: changing that reloads it.
    """
    return Store(hass, 1, f"{DOMAIN}.baseline.{entry_id}")


def _entry(hass: HomeAssistant, entry_id: str) -> ConfigEntry:
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN:
        raise HomeAssistantError(f"Unknown heat pump {entry_id}")
    return entry


def _coordinator(hass: HomeAssistant, msg: dict[str, Any]) -> AdlarCoordinator:
    return loaded_coordinator(hass, _entry(hass, msg["entry_id"]))


async def _read(coordinator: AdlarCoordinator, regs: list[R]) -> dict[str, Any]:
    """Read parameters from the heat pump; key -> value, None for one it rejects."""
    raw = await coordinator.async_read_registers(r.addr for r in regs)
    return {
        param_key(r): coordinator.data.get(r.addr) if r.addr in raw else None for r in regs
    }


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/list", vol.Optional("entry_id"): str})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_list(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """The heat pumps and, for one of them, every installer parameter."""
    entries = hass.config_entries.async_entries(DOMAIN)
    result: dict[str, Any] = {
        "entries": [
            {"entry_id": e.entry_id, "title": e.title, "loaded": e.state is ConfigEntryState.LOADED}
            for e in entries
        ],
        "entry_id": None,
        "groups": [],
        "recommended": list(recommended_params()),
        "pump_manual": None,
        "baseline_set_at": None,
    }
    entry = _entry(hass, msg["entry_id"]) if "entry_id" in msg else next(iter(entries), None)
    if entry is None:
        connection.send_result(msg["id"], result)
        return

    data: dict = {}
    if entry.state is ConfigEntryState.LOADED:
        coordinator = loaded_coordinator(hass, entry)
        # The pump pair is only polled when shown as a sensor, and manual control must not
        # go unnoticed: one request per list
        with suppress(HomeAssistantError):
            await coordinator.async_read_registers([DC_PUMP_CONTROL_REGISTER])
        data = coordinator.data
    pump = data.get(DC_PUMP_CONTROL_REGISTER)

    stored = await baseline_store(hass, entry.entry_id).async_load()
    baseline = stored["values"] if stored else {
        f"{addr:04X}": value for addr, value in REFERENCE_DEFAULTS.items()
    }
    sensors = entry.options.get(CONF_PARAMS, {})
    automations = entry.options.get(CONF_AUTOMATION_PARAMS, [])

    def parameter(reg: R) -> dict[str, Any]:
        key = param_key(reg)
        return {
            "key": key,
            "code": param_code(reg),
            "name": param_name(reg),
            "description": DESCRIPTIONS.get(reg.addr),
            "unit": reg.unit,
            "min": reg.min,
            "max": reg.max,
            "step": param_step(reg),
            "options": None if reg.options is None else [
                {"value": value, "label": label} for value, label in reg.options.items()
            ],
            "can_edit": can_edit(reg),
            "warning": warning_class(reg),
            "sensor": key in sensors,
            "automation": key in automations,
            "baseline": baseline.get(key),
            "value": data.get(reg.addr),
        }

    result |= {
        "entry_id": entry.entry_id,
        "groups": [
            {"id": group_id, "title": title, "parameters": [parameter(r) for r in group_params(group_id)]}
            for group_id, title, _, _ in PARAM_GROUPS
        ],
        "pump_manual": None if pump is None else pump != 0,
        "baseline_set_at": stored["set_at"] if stored else None,
    }
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/read_group", **ENTRY_ID, vol.Required("group"): str}
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_read_group(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Read one group from the heat pump, also the parameters that aren't polled."""
    coordinator = _coordinator(hass, msg)
    regs = group_params(msg["group"])
    if not regs:
        raise HomeAssistantError(f"Unknown parameter group {msg['group']}")
    connection.send_result(msg["id"], {"values": await _read(coordinator, regs)})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/write",
        **ENTRY_ID,
        vol.Required("key"): str,
        vol.Required("value"): vol.Coerce(float),
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_write(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Write one parameter; the answer is the value read back."""
    coordinator = _coordinator(hass, msg)
    reg = PARAMS.get(msg["key"])
    if reg is None:
        raise HomeAssistantError(f"Unknown parameter {msg['key']}")
    value = await coordinator.async_write_param(reg, msg["value"], connection.context(msg))
    connection.send_result(msg["id"], {"value": value})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/set_choices",
        **ENTRY_ID,
        vol.Required("sensors"): [str],
        vol.Required("automations"): [str],
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_set_choices(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Store which parameters are sensors and which automations may write."""
    entry = _entry(hass, msg["entry_id"])
    sensors, automations = set(msg["sensors"]), set(msg["automations"])
    if unknown := (sensors | automations) - PARAMS.keys():
        raise HomeAssistantError(f"Unknown parameters: {', '.join(sorted(unknown))}")
    if locked := sorted(PARAMS[k].name for k in automations if not can_edit(PARAMS[k])):
        raise HomeAssistantError(f"Read-only, not for automations: {', '.join(locked)}")
    options = {
        **entry.options,
        CONF_PARAMS: {key: READ_ONLY for key in sorted(sensors)},
        CONF_AUTOMATION_PARAMS: sorted(automations),
    }
    if hass.config_entries.async_update_entry(entry, options=options):
        # The update listener is reloading the entry and holds its setup lock meanwhile:
        # answer when the reload is done, so the panel can read straight away
        await asyncio.sleep(0)
        async with entry.setup_lock:
            pass
    connection.send_result(msg["id"])


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/export", **ENTRY_ID})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_export(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Read every parameter from the heat pump, protected ones included."""
    coordinator = _coordinator(hass, msg)
    raw = await coordinator.async_read_registers(r.addr for r in PARAMS.values())
    connection.send_result(msg["id"], {
        "parameters": [
            {
                "code": param_code(reg),
                "key": key,
                "name": param_name(reg),
                "value": coordinator.data.get(reg.addr) if reg.addr in raw else None,
                "unit": reg.unit,
                "raw": raw.get(reg.addr),
            }
            for key, reg in PARAMS.items()
        ]
    })


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/set_baseline", **ENTRY_ID})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_set_baseline(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Make the current values the baseline the panel compares against."""
    coordinator = _coordinator(hass, msg)
    values = await _read(coordinator, list(PARAMS.values()))
    stored = {
        "set_at": dt_util.utcnow().isoformat(),
        "values": {key: value for key, value in values.items() if value is not None},
    }
    await baseline_store(hass, msg["entry_id"]).async_save(stored)
    connection.send_result(msg["id"], {"baseline_set_at": stored["set_at"]})
