"""A reload (options change) must not leave the old coordinator polling."""
from __future__ import annotations

from datetime import timedelta

import pytest
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.adlar_heatpump.const import DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


async def test_reload_stops_old_coordinator(hass, fake_client):
    entry = MockConfigEntry(
        domain=DOMAIN, entry_id="01RELOAD", minor_version=2,
        data={"host": "192.0.2.1", "port": 502, "slave": 1, "scan_interval": 30},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    hass.config_entries.async_update_entry(entry, options={"scan_interval": 600, "slow_interval": 600})
    await hass.async_block_till_done()
    client = fake_client.instances[-1]
    client.requests.clear()

    # Past the old 30 s interval, well before the new 600 s one: nothing may poll
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=95))
    await hass.async_block_till_done()
    assert client.requests == []
