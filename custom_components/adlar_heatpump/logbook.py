"""Logbook entries for writes of installer parameters, on the heat pump's device."""
from __future__ import annotations

from collections.abc import Callable

from homeassistant.components.logbook import LOGBOOK_ENTRY_MESSAGE, LOGBOOK_ENTRY_NAME
from homeassistant.core import Event, HomeAssistant, callback

from .const import DOMAIN, EVENT_PARAMETER_WRITTEN
from .param_info import PARAMS
from .registers import R


def _text(reg: R | None, value) -> str:
    """A value as the panel shows it: the option's label, or the number with its unit."""
    if value is None:
        return "unknown (not read back)"
    if reg is None:
        return str(value)
    if reg.options is not None:
        return reg.options.get(value, str(value))
    return f"{value:g} {reg.unit}" if reg.unit else f"{value:g}"


@callback
def async_describe_events(
    hass: HomeAssistant,
    async_describe_event: Callable[[str, str, Callable[[Event], dict[str, str]]], None],
) -> None:
    """Describe the parameter write event; the user comes with the event's context."""

    @callback
    def describe(event: Event) -> dict[str, str]:
        data = event.data
        # An entry of an earlier version may name a parameter the register map has dropped
        reg = PARAMS.get(data["key"])
        return {
            LOGBOOK_ENTRY_NAME: data["name"],
            LOGBOOK_ENTRY_MESSAGE: (
                f"changed from {_text(reg, data['old'])} to {_text(reg, data['new'])}"
            ),
        }

    async_describe_event(DOMAIN, EVENT_PARAMETER_WRITTEN, describe)
