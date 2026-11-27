"""Config flow for Adlar Heatpump."""
from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_PARAMS,
    CONF_PIN,
    CONF_PREFIX,
    CONF_SLAVE,
    CONF_SLOW_INTERVAL,
    CONF_TRANSPORT,
    DEFAULT_PORT,
    DEFAULT_PREFIX,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE,
    DEFAULT_SLOW_INTERVAL,
    DOMAIN,
    TRANSPORT_PANEL,
    TRANSPORT_TCP,
)
from .coordinator import (
    ModbusRejected,
    ModbusUnavailable,
    PanelRefused,
    PanelTransport,
    panel_mode,
)

_LOGGER = logging.getLogger(__name__)

PIN_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))


async def _check_pin(hass: HomeAssistant, prefix: str, pin: str) -> str | None:
    """Ask the panel whether it accepts the PIN; returns the form error, None when it does."""
    try:
        answer = await PanelTransport(hass, prefix, pin).call("check_pin", pin=pin)
    except (ModbusUnavailable, ModbusRejected, PanelRefused):
        return "no_panel"
    return {"ok": None, "wrong": "wrong_pin", "locked": "locked"}.get(answer.get("result"), "no_panel")


class AdlarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Adlar Heatpump."""

    # 2: a panel entry, which adlar 1.6 must refuse; TCP entries stay version 1
    VERSION = 2
    # 1.2: per-parameter choices (CONF_PARAMS) replace the expert mode switch
    # 1.3: parameters are hidden or read-only sensors, never writable entities
    MINOR_VERSION = 3

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None and user_input.get(CONF_TRANSPORT) == TRANSPORT_PANEL:
            return await self.async_step_panel()
        if user_input is not None and CONF_HOST not in user_input:
            errors[CONF_HOST] = "host_required"
        elif user_input is not None:
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
                # Created with the flow's VERSION: a TCP entry is version 1
                self.VERSION = 1
                data = {k: v for k, v in user_input.items() if k != CONF_TRANSPORT}
                return self.async_create_entry(
                    title=f"Adlar Heatpump ({user_input[CONF_HOST]})",
                    data=data,
                    options={CONF_PARAMS: {}},
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_TRANSPORT, default=TRANSPORT_TCP): SelectSelector(
                    SelectSelectorConfig(
                        options=[TRANSPORT_TCP, TRANSPORT_PANEL], translation_key=CONF_TRANSPORT
                    )
                ),
                vol.Optional(CONF_HOST): str,
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

    async def async_step_panel(self, user_input=None):
        """Through the thermostat panel: its action prefix and the write PIN."""
        errors = {}
        if user_input is not None:
            error = await _check_pin(self.hass, user_input[CONF_PREFIX], user_input[CONF_PIN])
            if error is None:
                return self.async_create_entry(
                    title="Adlar Heatpump (thermostat panel)",
                    data={CONF_TRANSPORT: TRANSPORT_PANEL, **user_input},
                    options={},
                )
            errors["base"] = error
        schema = vol.Schema(
            {
                vol.Required(CONF_PREFIX, default=DEFAULT_PREFIX): str,
                vol.Required(CONF_PIN): PIN_SELECTOR,
            }
        )
        return self.async_show_form(step_id="panel", data_schema=schema, errors=errors)

    async def async_step_reauth(self, entry_data):
        """The panel refused the PIN of a write."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        errors = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            error = await _check_pin(self.hass, entry.data[CONF_PREFIX], user_input[CONF_PIN])
            if error is None:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_PIN: user_input[CONF_PIN]}
                )
            errors["base"] = error
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PIN): PIN_SELECTOR}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return AdlarOptionsFlow(config_entry)

    @classmethod
    @callback
    def async_supports_options_flow(cls, config_entry) -> bool:
        """The intervals are about polling, which panel mode doesn't do."""
        return not panel_mode(config_entry)


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
