"""Config flow for Adlar Heatpump."""
from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_PARAMS,
    CONF_SLAVE,
    CONF_SLOW_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE,
    DEFAULT_SLOW_INTERVAL,
    DOMAIN,
)
from .param_info import PARAM_GROUPS
from .registers import (
    EDITABLE,
    HIDDEN,
    PARAM_MODES,
    READ_ONLY,
    REGISTERS,
    R,
    can_edit,
    is_param,
    param_key,
    param_mode,
)

_LOGGER = logging.getLogger(__name__)


class AdlarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Adlar Heatpump."""

    VERSION = 1
    # 1.2: per-parameter choices (CONF_PARAMS) replace the expert mode switch
    MINOR_VERSION = 2

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            def _check():
                # Lazy import here too
                from pymodbus.client import ModbusTcpClient
                client = ModbusTcpClient(
                    host=user_input[CONF_HOST], port=user_input[CONF_PORT]
                )
                connected = client.connect()
                client.close()
                return connected

            try:
                ok = await self.hass.async_add_executor_job(_check)
                if not ok:
                    errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "cannot_connect"

            if not errors:
                return self.async_create_entry(
                    title=f"Adlar Heatpump ({user_input[CONF_HOST]})",
                    data=user_input,
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Required(CONF_SLAVE, default=DEFAULT_SLAVE): int,
                vol.Required(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                ): int,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return AdlarOptionsFlow(config_entry)


KEEP = "keep"
SET_ALL = "set_all"


def field_key(reg: R) -> str:
    """Form field (and translation key) of a parameter."""
    return f"reg_{reg.addr:04x}"


def group_registers(first: int, last: int) -> list[R]:
    return [r for r in REGISTERS if is_param(r) and first <= r.addr <= last]


class AdlarOptionsFlow(config_entries.OptionsFlow):
    """Menu: polling intervals, one page per group of installer parameters, save.

    Each page picks hidden / read-only / editable per parameter; the menu comes back
    after a page and "Save" stores everything and reloads the entry.
    """

    def __init__(self, config_entry):
        self._config_entry = config_entry
        self._options = dict(config_entry.options)
        self._params: dict[str, str] = dict(self._options.get(CONF_PARAMS, {}))

    async def async_step_init(self, user_input=None):
        return self.async_show_menu(
            step_id="init",
            menu_options=["polling", *(f"group_{key}" for key, *_ in PARAM_GROUPS), "save"],
        )

    async def async_step_polling(self, user_input=None):
        if user_input is not None:
            self._options.update(user_input)
            return await self.async_step_init()
        current = {**self._config_entry.data, **self._options}
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=current.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): vol.All(int, vol.Range(min=10)),
                vol.Required(
                    CONF_SLOW_INTERVAL,
                    default=current.get(CONF_SLOW_INTERVAL, DEFAULT_SLOW_INTERVAL),
                ): vol.All(int, vol.Range(min=60)),
            }
        )
        return self.async_show_form(step_id="polling", data_schema=schema)

    async def async_step_save(self, user_input=None):
        # Only shown parameters are stored; a missing one is hidden
        self._options[CONF_PARAMS] = {k: v for k, v in self._params.items() if v != HIDDEN}
        return self.async_create_entry(title="", data=self._options)

    async def _async_group_step(self, key: str, first: int, last: int, user_input):
        registers = group_registers(first, last)
        if user_input is not None:
            set_all = user_input.get(SET_ALL, KEEP)
            for reg in registers:
                mode = user_input.get(field_key(reg), HIDDEN) if set_all == KEEP else set_all
                if mode == EDITABLE and not can_edit(reg):
                    mode = READ_ONLY
                self._params[param_key(reg)] = mode
            return await self.async_step_init()

        fields: dict = {
            vol.Optional(SET_ALL, default=KEEP): SelectSelector(SelectSelectorConfig(
                options=[KEEP, *PARAM_MODES], translation_key=SET_ALL,
                mode=SelectSelectorMode.DROPDOWN,
            )),
        }
        for reg in registers:
            modes = PARAM_MODES if can_edit(reg) else (HIDDEN, READ_ONLY)
            fields[vol.Required(field_key(reg), default=param_mode(reg, self._params))] = (
                SelectSelector(SelectSelectorConfig(
                    options=list(modes), translation_key="param_mode",
                    mode=SelectSelectorMode.DROPDOWN,
                ))
            )
        return self.async_show_form(step_id=f"group_{key}", data_schema=vol.Schema(fields))


def _make_group_step(key: str, first: int, last: int):
    async def step(self, user_input=None):
        return await self._async_group_step(key, first, last, user_input)
    return step


# One async_step_group_<key> per parameter group
for _key, _title, _first, _last in PARAM_GROUPS:
    setattr(AdlarOptionsFlow, f"async_step_group_{_key}", _make_group_step(_key, _first, _last))
