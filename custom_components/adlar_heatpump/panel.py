"""Admin-only sidebar panel for the installer parameters."""
from __future__ import annotations

from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import DOMAIN

PANEL_URL_PATH = "adlar-heatpump-parameters"
PANEL_ELEMENT = "adlar-parameters-panel"
BUNDLE_URL = f"/{DOMAIN}_static/{PANEL_ELEMENT}.js"
BUNDLE_FILE = Path(__file__).parent / "frontend" / f"{PANEL_ELEMENT}.js"
DATA_REGISTERED = f"{DOMAIN}_panel_registered"
# A static path cannot be removed or registered twice, so it is served once per run
DATA_SERVED = f"{DOMAIN}_panel_served"


async def async_setup_panel(hass: HomeAssistant) -> None:
    """Serve the bundle and add the sidebar panel; does nothing when already set up."""
    # Without http and the frontend (e.g. in tests) there is no sidebar to add to.
    if (
        hass.data.get(DATA_REGISTERED)
        or hass.http is None
        or "frontend" not in hass.config.components
    ):
        return
    integration = await async_get_integration(hass, DOMAIN)
    if not hass.data.get(DATA_SERVED):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(BUNDLE_URL, str(BUNDLE_FILE), cache_headers=False)]
        )
        hass.data[DATA_SERVED] = True
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=PANEL_ELEMENT,
        sidebar_title="Heat pump parameters",
        sidebar_icon="mdi:heat-pump",
        # The version query makes browsers load a new bundle after an update.
        module_url=f"{BUNDLE_URL}?v={integration.version}",
        require_admin=True,
    )
    hass.data[DATA_REGISTERED] = True


def async_remove_panel(hass: HomeAssistant) -> None:
    """Remove the sidebar panel again; safe when it was never added."""
    if hass.data.pop(DATA_REGISTERED, None):
        frontend.async_remove_panel(hass, PANEL_URL_PATH)
