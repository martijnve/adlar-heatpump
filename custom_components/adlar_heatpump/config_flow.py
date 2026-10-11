"""Config flow for Adlar Heatpump."""
from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import callback

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
from .param_info import recommended_params

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
                    # Start with the parameters Adlår's manual has users look at or change
                    options={CONF_PARAMS: recommended_params()},
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


class AdlarOptionsFlow(config_entries.OptionsFlow):
    """Polling intervals; the per-parameter choices live in the parameter panel."""

    def __init__(self, config_entry):
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        options = dict(self._config_entry.options)
        if user_input is not None:
            return self.async_create_entry(title="", data={**options, **user_input})
        current = {**self._config_entry.data, **options}
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
        return self.async_show_form(step_id="init", data_schema=schema)
