"""The sidebar panel registers once, admin-only, and goes away again."""
from __future__ import annotations

import asyncio

import pytest
from homeassistant.components.frontend import DATA_PANELS
from homeassistant.setup import async_setup_component

from custom_components.adlar_heatpump.panel import (
    PANEL_URL_PATH,
    async_remove_panel,
    async_setup_panel,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    return enable_custom_integrations


@pytest.fixture
async def web(hass):
    # The real frontend needs the hass_frontend package, which the test environment lacks.
    # Panel registration only needs the frontend module and the "frontend" marker, so skip the setup
    # of frontend and of panel_custom (which depends on it).
    for component in ("http",):
        assert await async_setup_component(hass, component, {})
    hass.config.components.add("frontend")
    await hass.async_block_till_done()


async def test_setup_registers_admin_panel_once(hass, web):
    await async_setup_panel(hass)
    panel = hass.data[DATA_PANELS][PANEL_URL_PATH]
    assert panel.require_admin is True
    assert panel.sidebar_title == "Heat pump parameters"
    assert panel.config["_panel_custom"]["name"] == "adlar-parameters-panel"
    assert panel.config["_panel_custom"]["module_url"].startswith(
        "/adlar_heatpump_static/adlar-parameters-panel.js?v="
    )

    await async_setup_panel(hass)  # would raise "Overwriting panel" if it registered twice
    assert hass.data[DATA_PANELS][PANEL_URL_PATH] is panel


async def test_concurrent_setup_registers_once(hass, web):
    # Two config entries set up at the same time; a second static path raises RuntimeError
    await asyncio.gather(async_setup_panel(hass), async_setup_panel(hass))
    assert PANEL_URL_PATH in hass.data[DATA_PANELS]


async def test_remove_panel_is_idempotent(hass, web):
    await async_setup_panel(hass)
    async_remove_panel(hass)
    assert PANEL_URL_PATH not in hass.data[DATA_PANELS]
    async_remove_panel(hass)
    # and it can be added again
    await async_setup_panel(hass)
    assert PANEL_URL_PATH in hass.data[DATA_PANELS]


async def test_no_frontend_does_nothing(hass):
    await async_setup_panel(hass)
    async_remove_panel(hass)
