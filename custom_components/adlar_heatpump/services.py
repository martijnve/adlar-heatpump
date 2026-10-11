"""The set_parameter service: automations write the installer parameters ticked for them."""
from __future__ import annotations

import voluptuous as vol
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.service import async_register_admin_service

from .const import CONF_AUTOMATION_PARAMS, DOMAIN
from .coordinator import loaded_coordinator
from .param_info import find_param
from .registers import param_key

SERVICE_SET_PARAMETER = "set_parameter"
ATTR_PARAMETER = "parameter"
ATTR_VALUE = "value"

SET_PARAMETER_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Required(ATTR_PARAMETER): cv.string,
        vol.Required(ATTR_VALUE): vol.Coerce(float),
    }
)


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register the service; an admin service, so users without admin rights can't call it."""

    async def set_parameter(call: ServiceCall) -> None:
        device = dr.async_get(hass).async_get(call.data[ATTR_DEVICE_ID])
        entry = next(
            (
                e for e in hass.config_entries.async_entries(DOMAIN)
                if device is not None and e.entry_id in device.config_entries
            ),
            None,
        )
        if entry is None:
            raise ServiceValidationError(f"{call.data[ATTR_DEVICE_ID]} is not an Adlar heat pump")
        reg = find_param(call.data[ATTR_PARAMETER])
        if reg is None:
            raise ServiceValidationError(f"Unknown parameter {call.data[ATTR_PARAMETER]}")
        if param_key(reg) not in entry.options.get(CONF_AUTOMATION_PARAMS, []):
            raise ServiceValidationError(
                f'{reg.name} may not be written by automations: tick "Allow automations" '
                "for it in the Heat pump parameters panel"
            )
        await loaded_coordinator(hass, entry).async_write_param(
            reg, call.data[ATTR_VALUE], call.context
        )

    async_register_admin_service(
        hass, DOMAIN, SERVICE_SET_PARAMETER, set_parameter, SET_PARAMETER_SCHEMA
    )
