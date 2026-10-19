"""kWh counter: a one-off drop is held back, a lasting one is published."""
from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_restore_cache_with_extra_data,
)

from custom_components.adlar_heatpump.const import DOMAIN
from custom_components.adlar_heatpump.coordinator import (
    AdlarCoordinator,
    ModbusRequestFailed,
)
from custom_components.adlar_heatpump.sensor import COUNTER_DROP_READS

from .conftest import FakeModbusClient

ENTRY_ID = "01TESTENTRY"
KWH = 0x005D


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


async def _setup(hass: HomeAssistant):
    entry = MockConfigEntry(
        domain=DOMAIN, entry_id=ENTRY_ID,
        data={"host": "192.0.2.1", "port": 502, "slave": 1, "scan_interval": 60},
        minor_version=2,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return hass.data[DOMAIN][ENTRY_ID]


def _entity_id(hass: HomeAssistant) -> str:
    return er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{ENTRY_ID}_{KWH:04X}")


async def _poll(hass, coordinator, raw: int) -> str:
    FakeModbusClient.instances[-1].registers[KWH] = raw
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    return hass.states.get(_entity_id(hass)).state


async def test_one_poll_drop_is_held(hass, fake_client):
    coordinator = await _setup(hass)
    assert await _poll(hass, coordinator, 2985) == "2985"
    assert await _poll(hass, coordinator, 0) == "2985"
    assert await _poll(hass, coordinator, 2985) == "2985"
    # An update without a fresh read doesn't count towards a drop
    for _ in range(COUNTER_DROP_READS):
        coordinator.async_set_updated_data({**coordinator.data, KWH: 0})
    await hass.async_block_till_done()
    assert hass.states.get(_entity_id(hass)).state == "2985"


async def test_lasting_drop_is_published(hass, fake_client):
    coordinator = await _setup(hass)
    assert await _poll(hass, coordinator, 2985) == "2985"
    states = [await _poll(hass, coordinator, 5) for _ in range(COUNTER_DROP_READS)]
    assert states == ["2985"] * (COUNTER_DROP_READS - 1) + ["5"]
    assert await _poll(hass, coordinator, 6) == "6"


async def test_drop_right_after_reload_is_held(hass, fake_client):
    mock_restore_cache_with_extra_data(hass, [(
        State(f"sensor.{DOMAIN}_unit_power_consumption", "2985"),
        {"native_value": 2985, "native_unit_of_measurement": "kWh"},
    )])
    er.async_get(hass).async_get_or_create(
        "sensor", DOMAIN, f"{ENTRY_ID}_{KWH:04X}",
        suggested_object_id=f"{DOMAIN}_unit_power_consumption",
    )
    # The snapshot holds 0 for the counter: the first read after setup
    await _setup(hass)
    assert hass.states.get(_entity_id(hass)).state == "2985"


def test_reply_with_wrong_register_count_is_a_failed_read(hass, fake_client):
    entry = MockConfigEntry(domain=DOMAIN, data={"host": "192.0.2.1"})
    entry.add_to_hass(hass)
    coordinator = AdlarCoordinator(hass, entry, "192.0.2.1", 502, 1, 60, 600)
    coordinator._fetch_all()
    client = FakeModbusClient.instances[-1]
    real = client.read_holding_registers

    def short(address, *, count=1, device_id=1):
        response = real(address, count=count, device_id=device_id)
        response.registers = response.registers[1:]
        return response

    client.read_holding_registers = short
    with pytest.raises(ModbusRequestFailed):
        coordinator._read("registers", KWH - 1, 2)
    assert coordinator._client is None
