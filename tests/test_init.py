"""Integration setup against the fake controller."""
from __future__ import annotations

from collections import Counter

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.adlar_heatpump.const import CONF_EXPERT_MODE, CONF_PARAMS, DOMAIN

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
        minor_version=2,
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
    # Installer parameters are hidden by default: no entities, not polled
    assert not any(uid.startswith(("0100", "num_0100", "sel_0100")) for _, uid in _registry_ids(hass))
    assert counts["sensor"] == 59


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


def _params(**modes) -> dict:
    """{"010B": "editable", ...} from reg_010b="editable" style keywords."""
    return {CONF_PARAMS: {k.removeprefix("reg_").upper(): v for k, v in modes.items()}}


def _entity(hass, domain: str, suffix: str):
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(domain, DOMAIN, f"{ENTRY_ID}_{suffix}")
    return registry.async_get(entity_id) if entity_id else None


async def test_param_modes_choose_platform(hass, fake_client):
    await _setup(hass, _params(reg_010b="editable", reg_011e="editable", reg_010c="read_only",
                               reg_0177="editable"))
    assert _entity(hass, "number", "num_010B")          # P11 numeric → number
    assert _entity(hass, "select", "sel_011E")          # P30 enum → select
    assert _entity(hass, "sensor", "010C")              # P12 read-only → sensor
    assert not _entity(hass, "sensor", "010D")          # P13 not chosen → hidden
    # P119 is protected: asked editable, shown read-only
    assert _entity(hass, "sensor", "0177") and not _entity(hass, "select", "sel_0177")
    # Chosen entities are enabled
    assert _entity(hass, "number", "num_010B").disabled_by is None
    assert _entity(hass, "sensor", "010C").disabled_by is None


async def test_hidden_params_are_not_polled(hass, fake_client):
    await _setup(hass, _params(reg_010b="read_only"))
    requested = set()
    for name, start, count in fake_client.instances[-1].requests:
        if name == "read_holding_registers":
            requested |= set(range(start, start + count))
    assert 0x010B in requested and 0x0177 in requested and 0x0172 in requested
    assert 0x010D not in requested and 0x0800 not in requested


async def test_mode_change_moves_entity_with_settings(hass, fake_client):
    entry = await _setup(hass, _params(reg_010b="read_only"))
    registry = er.async_get(hass)
    sensor = _entity(hass, "sensor", "010B")
    registry.async_update_entity(sensor.entity_id, name="HP protect", hidden_by=er.RegistryEntryHider.USER)

    hass.config_entries.async_update_entry(entry, options=_params(reg_010b="editable"))
    await hass.async_block_till_done()
    number = _entity(hass, "number", "num_010B")
    assert number.entity_id == "number." + sensor.entity_id.split(".", 1)[1]
    assert number.name == "HP protect" and number.hidden_by == er.RegistryEntryHider.USER
    assert not _entity(hass, "sensor", "010B")

    registry.async_update_entity(number.entity_id, disabled_by=er.RegistryEntryDisabler.USER)
    hass.config_entries.async_update_entry(entry, options=_params(reg_010b="read_only"))
    await hass.async_block_till_done()
    back = _entity(hass, "sensor", "010B")
    assert back.entity_id == sensor.entity_id and back.name == "HP protect"
    assert back.disabled_by == er.RegistryEntryDisabler.USER   # the user's own choice stays

    hass.config_entries.async_update_entry(entry, options=_params())
    await hass.async_block_till_done()
    assert not _entity(hass, "sensor", "010B") and not _entity(hass, "number", "num_010B")


async def test_old_default_disabled_entity_is_enabled_when_chosen(hass, fake_client):
    registry = er.async_get(hass)
    entry = MockConfigEntry(
        domain=DOMAIN, entry_id=ENTRY_ID, minor_version=2,
        data={"host": "192.0.2.1", "port": 502, "slave": 1, "scan_interval": 60},
        options=_params(reg_010b="editable"),
    )
    entry.add_to_hass(hass)
    registry.async_get_or_create(
        "number", DOMAIN, f"{ENTRY_ID}_num_010B", config_entry=entry,
        disabled_by=er.RegistryEntryDisabler.INTEGRATION,
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert _entity(hass, "number", "num_010B").disabled_by is None


@pytest.mark.parametrize("expert", [True, False])
async def test_migrate_expert_mode(hass, fake_client, expert):
    registry = er.async_get(hass)
    entry = MockConfigEntry(
        domain=DOMAIN, entry_id=ENTRY_ID, version=1, minor_version=1,
        data={"host": "192.0.2.1", "port": 502, "slave": 1, "scan_interval": 60},
        options={CONF_EXPERT_MODE: expert, "scan_interval": 600},
    )
    entry.add_to_hass(hass)
    # Expert off: a parameter sensor the user had enabled
    registry.async_get_or_create("sensor", DOMAIN, f"{ENTRY_ID}_010D", config_entry=entry)
    registry.async_get_or_create(
        "sensor", DOMAIN, f"{ENTRY_ID}_010E", config_entry=entry,
        disabled_by=er.RegistryEntryDisabler.INTEGRATION,
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.minor_version == 2 and CONF_EXPERT_MODE not in entry.options
    assert entry.options["scan_interval"] == 600
    params = entry.options[CONF_PARAMS]
    if expert:
        assert params["010B"] == "editable" and params["0177"] == "read_only"
        assert params["0343"] == "editable"
        assert _entity(hass, "number", "num_010D")
    else:
        assert params == {"010D": "read_only"}
        assert _entity(hass, "sensor", "010D") and not _entity(hass, "sensor", "010E")


async def test_dc_pump_hidden_until_chosen(hass, fake_client):
    entry = await _setup(hass)
    assert not _entity(hass, "number", "num_0344") and not _entity(hass, "sensor", "0344")
    hass.config_entries.async_update_entry(entry, options=_params(reg_0344="editable"))
    await hass.async_block_till_done()
    assert _entity(hass, "number", "num_0344").disabled_by is None


async def test_delta_parameter_is_not_a_temperature(hass, fake_client):
    await _setup(hass, _params(reg_011a="editable", reg_0301="editable"))
    assert _entity(hass, "number", "num_011A").original_device_class is None
    assert _entity(hass, "number", "num_0301").original_device_class == "temperature"


async def test_options_flow_keeps_params(hass, fake_client):
    entry = await _setup(hass, _params(reg_010b="editable"))
    flow = hass.config_entries.options
    result = await flow.async_init(entry.entry_id)
    assert result["type"] == "form" and result["step_id"] == "init"
    result = await flow.async_configure(result["flow_id"], {"scan_interval": 300, "slow_interval": 900})
    assert result["type"] == "create_entry"
    await hass.async_block_till_done()
    assert entry.options["scan_interval"] == 300 and entry.options["slow_interval"] == 900
    assert entry.options[CONF_PARAMS] == {"010B": "editable"}


async def test_new_setup_gets_recommended_params(hass, fake_client):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": "192.0.2.1", "port": 502, "slave": 1, "scan_interval": 600}
    )
    assert result["type"] == "create_entry"
    await hass.async_block_till_done()
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    params = entry.options[CONF_PARAMS]
    assert params["011A"] == "editable"          # P26 hysteresis
    assert params["0801"] == "editable"          # L12 sterilisation
    assert params["011E"] == "read_only"         # P30 defrost mode
    assert "010B" not in params                  # P11 protection limit: hidden
    registry = er.async_get(hass)
    assert registry.async_get_entity_id("number", DOMAIN, f"{entry.entry_id}_num_011A")
    assert registry.async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_011E")


async def test_p151_is_an_outdoor_temperature(hass, fake_client):
    await _setup(hass, _params(reg_0197="editable"))
    assert _entity(hass, "number", "num_0197").original_device_class == "temperature"
