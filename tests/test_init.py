"""Integration setup against the fake controller."""
from __future__ import annotations

from collections import Counter

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.adlar_heatpump.const import CONF_EXPERT_MODE, DOMAIN

ENTRY_ID = "01TESTENTRY"

# Every unique_id upstream 1.4.1 creates: the fork must keep them all
UPSTREAM_UNIQUE_IDS = {
    ("sensor", suffix) for suffix in (
        "0040", "0041", "0042", "0043", "0045", "0046", "0047", "0048", "0049", "004A",
        "004B", "004C", "004D", "004E", "004F", "0050", "0051", "0052", "0054", "0055",
        "0057", "0058", "0059", "005A", "005B", "005C", "0085", "005D", "0027",
        "thermal_power", "cop", "calculated_power", "refrigerant_type",
    )
} | {
    ("binary_sensor", f"status_{mask:04X}")
    for mask in (0x0001, 0x0002, 0x0004, 0x0008, 0x0010, 0x0100, 0x1000, 0x2000, 0x4000, 0x8000)
} | {
    ("number", "num_0300"), ("number", "num_0301"), ("number", "num_0303"),
    ("switch", "onoff"),
    ("select", "sel_0304"), ("select", "sel_0307"), ("select", "sel_0313"),
    ("select", "sel_0314"), ("select", "sel_0316"),
    ("climate", "climate"),
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


async def _setup(hass: HomeAssistant, options: dict | None = None) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, entry_id=ENTRY_ID,
        data={"host": "192.0.2.1", "port": 502, "slave": 1, "scan_interval": 60},
        options=options or {},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _registry_ids(hass: HomeAssistant) -> set[tuple[str, str]]:
    registry = er.async_get(hass)
    return {
        (e.domain, e.unique_id.removeprefix(f"{ENTRY_ID}_"))
        for e in registry.entities.values() if e.config_entry_id == ENTRY_ID
    }


async def test_setup_keeps_upstream_unique_ids(hass, fake_client):
    await _setup(hass)
    ids = _registry_ids(hass)
    assert UPSTREAM_UNIQUE_IDS <= ids, UPSTREAM_UNIQUE_IDS - ids


async def test_entity_counts_default(hass, fake_client):
    await _setup(hass)
    counts = Counter(domain for domain, _ in _registry_ids(hass))
    # 153 status bits; single compressor so no System 2 mirrors
    assert counts["binary_sensor"] == 153
    assert counts["switch"] == 7
    assert counts["select"] == 6            # mode, running mode, 4 curves
    assert counts["number"] == 7            # 4 setpoints, indoor, 2 zones
    assert counts["climate"] == 1
    assert counts["sensor"] > 300           # all P/L parameters read-only


async def test_expert_mode_moves_parameters(hass, fake_client):
    entry = await _setup(hass)
    registry = er.async_get(hass)
    assert registry.async_get_entity_id("sensor", DOMAIN, f"{ENTRY_ID}_011E")

    hass.config_entries.async_update_entry(entry, options={CONF_EXPERT_MODE: True})
    await hass.async_block_till_done()

    # P30 defrost mode is an enum → select; P11 is numeric → number
    assert registry.async_get_entity_id("select", DOMAIN, f"{ENTRY_ID}_sel_011E")
    assert registry.async_get_entity_id("number", DOMAIN, f"{ENTRY_ID}_num_010B")
    assert not registry.async_get_entity_id("sensor", DOMAIN, f"{ENTRY_ID}_011E")
    # Protected parameters stay read-only
    assert registry.async_get_entity_id("sensor", DOMAIN, f"{ENTRY_ID}_0177")
    assert not registry.async_get_entity_id("select", DOMAIN, f"{ENTRY_ID}_sel_0177")

    hass.config_entries.async_update_entry(entry, options={CONF_EXPERT_MODE: False})
    await hass.async_block_till_done()
    assert registry.async_get_entity_id("sensor", DOMAIN, f"{ENTRY_ID}_011E")
    assert not registry.async_get_entity_id("select", DOMAIN, f"{ENTRY_ID}_sel_011E")


async def test_states(hass, fake_client):
    await _setup(hass)
    registry = er.async_get(hass)

    def state(domain, suffix):
        entity_id = registry.async_get_entity_id(domain, DOMAIN, f"{ENTRY_ID}_{suffix}")
        return hass.states.get(entity_id)

    assert state("sensor", "004F").state == "36"
    assert state("sensor", "refrigerant_type").state == "R32"
    assert state("select", "sel_0304").state == "Heating"
    assert state("select", "sel_0314").state == "L8"
    assert state("number", "num_0302").state == "40"
    assert state("switch", "onoff").state == "on"
    assert state("switch", "coil_101A").state == "on"
    climate = state("climate", "climate")
    assert climate.state == "heat"
    assert climate.attributes["temperature"] == 40


async def test_set_temperature_writes_active_setpoint(hass, fake_client):
    await _setup(hass)
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("climate", DOMAIN, f"{ENTRY_ID}_climate")
    await hass.services.async_call(
        "climate", "set_temperature", {"entity_id": entity_id, "temperature": 45}, blocking=True
    )
    client = fake_client.instances[-1]
    assert ("write_register", 0x0301, 45) in client.writes


def _climate_id(hass) -> str:
    return er.async_get(hass).async_get_entity_id("climate", DOMAIN, f"{ENTRY_ID}_climate")


async def _set_mode(hass, fake_client, mode: int, on: int = 1) -> None:
    client = fake_client.instances[-1]
    client.registers[0x0304] = mode
    client.registers[0x0305] = on
    coordinator = hass.data[DOMAIN][ENTRY_ID]
    await coordinator.async_refresh()
    await hass.async_block_till_done()


@pytest.mark.parametrize(
    ("mode", "requested", "written_mode"),
    [
        (1, "cool", 0),        # plain mode switch
        (2, "heat", 5),        # hot water only: keep hot water, add heating
        (4, "heat", 5),        # hot water + cooling → hot water + heating
        (5, "heat", None),     # already there: no mode write
        (0, "heat_cool", 3),
    ],
)
async def test_set_hvac_mode_keeps_hot_water(hass, fake_client, mode, requested, written_mode):
    await _setup(hass)
    await _set_mode(hass, fake_client, mode)
    client = fake_client.instances[-1]
    client.writes.clear()
    await hass.services.async_call(
        "climate", "set_hvac_mode", {"entity_id": _climate_id(hass), "hvac_mode": requested},
        blocking=True,
    )
    mode_writes = [w for w in client.writes if w[1] == 0x0304]
    assert mode_writes == ([("write_register", 0x0304, written_mode)] if written_mode is not None else [])
    assert hass.states.get(_climate_id(hass)).state == requested


async def test_hot_water_only_shows_off_and_ignores_setpoint(hass, fake_client):
    await _setup(hass)
    await _set_mode(hass, fake_client, 2)
    state = hass.states.get(_climate_id(hass))
    assert state.state == "off"
    assert state.attributes["temperature"] is None


async def test_failed_mode_write_does_not_switch_on(hass, fake_client):
    await _setup(hass)
    await _set_mode(hass, fake_client, 0, on=0)
    client = fake_client.instances[-1]
    client.reject[0x0304] = 4
    client.writes.clear()
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "climate", "set_hvac_mode", {"entity_id": _climate_id(hass), "hvac_mode": "heat"},
            blocking=True,
        )
    assert not any(w[1] == 0x0305 for w in client.writes)


async def test_set_temperature_with_hvac_mode(hass, fake_client):
    await _setup(hass)
    client = fake_client.instances[-1]
    client.writes.clear()
    await hass.services.async_call(
        "climate", "set_temperature",
        {"entity_id": _climate_id(hass), "temperature": 20, "hvac_mode": "cool"},
        blocking=True,
    )
    assert client.writes == [("write_register", 0x0304, 0), ("write_register", 0x0300, 20)]


async def test_state_right_after_write(hass, fake_client):
    await _setup(hass)
    await hass.services.async_call("climate", "turn_off", {"entity_id": _climate_id(hass)}, blocking=True)
    await hass.services.async_call("climate", "turn_on", {"entity_id": _climate_id(hass)}, blocking=True)
    assert hass.states.get(_climate_id(hass)).state == "heat"


async def test_expert_toggle_keeps_user_settings(hass, fake_client):
    entry = await _setup(hass)
    registry = er.async_get(hass)
    sensor_id = registry.async_get_entity_id("sensor", DOMAIN, f"{ENTRY_ID}_010B")
    registry.async_update_entity(sensor_id, disabled_by=None, name="HP protect")
    await hass.async_block_till_done()

    hass.config_entries.async_update_entry(entry, options={CONF_EXPERT_MODE: True})
    await hass.async_block_till_done()
    number = registry.async_get(registry.async_get_entity_id("number", DOMAIN, f"{ENTRY_ID}_num_010B"))
    assert number.entity_id == "number." + sensor_id.split(".", 1)[1]
    assert number.disabled_by is None and number.name == "HP protect"

    hass.config_entries.async_update_entry(entry, options={CONF_EXPERT_MODE: False})
    await hass.async_block_till_done()
    sensor = registry.async_get(registry.async_get_entity_id("sensor", DOMAIN, f"{ENTRY_ID}_010B"))
    assert sensor.entity_id == sensor_id
    assert sensor.disabled_by is None and sensor.name == "HP protect"


async def test_unknown_option_value_is_shown(hass, fake_client):
    await _setup(hass)
    await _set_mode(hass, fake_client, 6)
    registry = er.async_get(hass)
    select_id = registry.async_get_entity_id("select", DOMAIN, f"{ENTRY_ID}_sel_0304")
    state = hass.states.get(select_id)
    assert state.state == "Unknown (6)"
    assert "Unknown (6)" in state.attributes["options"]
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            "select", "select_option", {"entity_id": select_id, "option": "Unknown (6)"}, blocking=True
        )


async def test_delta_parameter_is_not_a_temperature(hass, fake_client):
    await _setup(hass, {CONF_EXPERT_MODE: True})
    registry = er.async_get(hass)
    number_id = registry.async_get_entity_id("number", DOMAIN, f"{ENTRY_ID}_num_011A")
    registry.async_update_entity(number_id, disabled_by=None)
    assert registry.async_get(number_id).original_device_class is None
    heating_id = registry.async_get_entity_id("number", DOMAIN, f"{ENTRY_ID}_num_0301")
    assert registry.async_get(heating_id).original_device_class == "temperature"


async def test_dc_pump_needs_expert_mode(hass, fake_client):
    await _setup(hass)
    registry = er.async_get(hass)
    assert registry.async_get_entity_id("sensor", DOMAIN, f"{ENTRY_ID}_0344")
    assert not registry.async_get_entity_id("number", DOMAIN, f"{ENTRY_ID}_num_0344")
