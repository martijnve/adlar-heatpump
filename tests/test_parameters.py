"""The parameter panel's websocket API, the set_parameter service and their wiring."""
from __future__ import annotations

import pytest
from homeassistant.components.frontend import DATA_PANELS
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import (
    HomeAssistantError,
    ServiceValidationError,
    Unauthorized,
)
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
)

from custom_components.adlar_heatpump.const import (
    CONF_AUTOMATION_PARAMS,
    CONF_PARAMS,
    DOMAIN,
    EVENT_PARAMETER_WRITTEN,
)
from custom_components.adlar_heatpump.logbook import async_describe_events
from custom_components.adlar_heatpump.panel import PANEL_URL_PATH
from custom_components.adlar_heatpump.param_info import (
    PARAM_GROUPS,
    PARAMS,
    PROTECTION_EXTRA,
    REFERENCE_DEFAULTS,
    find_param,
    group_params,
    param_code,
    warning_class,
)
from custom_components.adlar_heatpump.registers import BY_ADDR, can_edit

ENTRY_ID = "01TESTENTRY"
BASELINE_KEY = f"{DOMAIN}.baseline.{ENTRY_ID}"
P99 = "P99 Pump speed regulation temp diff"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


async def _setup(hass: HomeAssistant, sensors=(), automations=()) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, entry_id=ENTRY_ID, minor_version=3, title="Heat pump",
        data={"host": "192.0.2.1", "port": 502, "slave": 1, "scan_interval": 60},
        options={
            CONF_PARAMS: {key: "read_only" for key in sensors},
            CONF_AUTOMATION_PARAMS: list(automations),
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def _send(client, command: str, **fields) -> dict:
    await client.send_json_auto_id({"type": f"{DOMAIN}/{command}", **fields})
    return await client.receive_json()


async def _ok(client, command: str, **fields):
    answer = await _send(client, command, entry_id=ENTRY_ID, **fields)
    assert answer["success"], answer
    return answer["result"]


async def _error(client, command: str, **fields) -> str:
    answer = await _send(client, command, entry_id=ENTRY_ID, **fields)
    assert not answer["success"] and answer["error"]["code"] == "home_assistant_error", answer
    return answer["error"]["message"]


def _device_id(hass: HomeAssistant) -> str:
    return dr.async_get(hass).async_get_device(identifiers={(DOMAIN, ENTRY_ID)}).id


def _sensor(hass: HomeAssistant, key: str):
    entity_id = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{ENTRY_ID}_{key}")
    return hass.states.get(entity_id) if entity_id else None


def _logbook(hass: HomeAssistant, event) -> dict:
    described = {}
    async_describe_events(hass, lambda domain, event_type, describe: described.update({event_type: describe}))
    return described[event.event_type](event)


# ── Parameter data ─────────────────────────────────────────────────────


def test_parameter_data():
    # 263 P and 26 L parameters plus the DC pump pair, each in exactly one group
    assert len(PARAMS) == 291
    grouped = [r for group_id, *_ in PARAM_GROUPS for r in group_params(group_id)]
    assert sorted(r.addr for r in grouped) == sorted(r.addr for r in PARAMS.values())
    assert sum(can_edit(r) for r in PARAMS.values()) == 284
    # param_step and the write validation assume no parameter is refrigerant-scaled
    assert not any(r.temp or r.scale != 1 for r in PARAMS.values())

    codes = [param_code(r) for r in PARAMS.values()]
    assert codes.count(None) == 2 and len(set(codes)) == 290
    assert all(c[0] in "PL" and c[1:].isdigit() for c in codes if c)
    assert find_param("p99").addr == 0x0163 and find_param(" L13 ").addr == 0x0802
    assert find_param("0344").addr == 0x0344 and find_param("P999") is None

    assert PROTECTION_EXTRA <= {r.addr for r in PARAMS.values()}
    assert warning_class(BY_ADDR[0x010B]) == "protection"      # P11, protection group
    assert warning_class(BY_ADDR[0x0176]) == "protection"      # P118 anti-freeze
    assert warning_class(BY_ADDR[0x01B8]) == "factory"         # P184 calibration
    assert warning_class(BY_ADDR[0x0344]) == "dc_pump"
    assert warning_class(BY_ADDR[0x0163]) is None


def test_reference_defaults():
    # The reference's 64 without L14, whose default is in another notation than the register
    assert len(REFERENCE_DEFAULTS) == 63 and 0x0803 not in REFERENCE_DEFAULTS
    for addr, default in REFERENCE_DEFAULTS.items():
        reg = BY_ADDR[addr]
        assert f"{addr:04X}" in PARAMS
        if reg.options is not None:
            assert default in reg.options, reg.name
        elif reg.min is not None:
            assert reg.min <= default <= reg.max, reg.name


# ── list ───────────────────────────────────────────────────────────────


async def test_list(hass, fake_client, hass_ws_client):
    await _setup(hass, sensors=["010B"], automations=["0163"])
    client = await hass_ws_client(hass)
    result = (await _send(client, "list"))["result"]     # no entry_id: the first entry

    assert result["entries"] == [{"entry_id": ENTRY_ID, "title": "Heat pump", "loaded": True}]
    assert result["entry_id"] == ENTRY_ID
    assert [(g["id"], g["title"]) for g in result["groups"]] == [(g[0], g[1]) for g in PARAM_GROUPS]
    params = {p["key"]: p for g in result["groups"] for p in g["parameters"]}
    assert len(params) == 291
    assert len(result["recommended"]) == 47 and "0163" in result["recommended"]
    assert result["pump_manual"] is False and result["baseline_set_at"] is None

    assert params["0163"] == {
        "key": "0163", "code": "P99", "name": "Pump speed regulation temp diff",
        "description": "Inlet-outlet temperature difference the variable-speed pump regulates towards.",
        "unit": "°C", "min": 2, "max": 10, "step": 1, "options": None,
        "can_edit": True, "warning": None, "sensor": False, "automation": True,
        "baseline": 5,       # the reference's default
        "value": None,       # no sensor, so not polled
    }
    shown = params["010B"]
    assert shown["sensor"] and not shown["automation"] and shown["value"] == 65
    assert shown["warning"] == "protection" and shown["baseline"] is None
    pump = params["0343"]
    assert pump["code"] is None and pump["name"] == "DC Pump Control"
    assert pump["warning"] == "dc_pump" and pump["step"] is None and pump["can_edit"]
    assert pump["options"] == [{"value": 0, "label": "Auto"}, {"value": 1, "label": "Manual"}]
    assert pump["value"] == 0                                # read for pump_manual
    assert not params["012D"]["can_edit"] and not params["0803"]["can_edit"]
    assert params["01B8"]["warning"] == "factory"

    answer = await _send(client, "list", entry_id="nope")
    assert "Unknown heat pump" in answer["error"]["message"]


async def test_list_without_entries(hass, hass_ws_client):
    assert await async_setup_component(hass, DOMAIN, {})
    client = await hass_ws_client(hass)
    result = (await _send(client, "list"))["result"]
    assert result["entries"] == [] and result["entry_id"] is None and result["groups"] == []


async def test_admin_only(hass, fake_client, hass_ws_client, hass_read_only_access_token, hass_read_only_user):
    await _setup(hass, automations=["0163"])
    client = await hass_ws_client(hass, hass_read_only_access_token)
    for command, fields in (
        ("list", {}),
        ("read_group", {"group": "water"}),
        ("write", {"key": "0163", "value": 5}),
        ("set_choices", {"sensors": [], "automations": []}),
        ("export", {}),
        ("set_baseline", {}),
    ):
        answer = await _send(client, command, entry_id=ENTRY_ID, **fields)
        assert answer["error"]["code"] == "unauthorized", command
    with pytest.raises(Unauthorized):
        await hass.services.async_call(
            DOMAIN, "set_parameter",
            {"device_id": _device_id(hass), "parameter": "P99", "value": 5},
            blocking=True, context=Context(user_id=hass_read_only_user.id),
        )
    assert fake_client.instances[-1].writes == []


# ── read_group ─────────────────────────────────────────────────────────


async def test_read_group_reads_unpolled_parameters(hass, fake_client, hass_ws_client):
    await _setup(hass, sensors=["010B"])
    client = await hass_ws_client(hass)
    fake = fake_client.instances[-1]
    assert _sensor(hass, "010B").state == "65"
    fake.registers[0x010B] = 70
    fake.requests.clear()

    values = (await _ok(client, "read_group", group="protection"))["values"]
    assert len(values) == 17 and values["010B"] == 70 and values["010D"] == -40
    # One request on the coordinator's own connection, and the cache follows
    assert fake.requests == [("read_holding_registers", 0x0100, 17)]
    assert len(fake_client.instances) == 1
    await hass.async_block_till_done()
    assert _sensor(hass, "010B").state == "70"
    result = await _ok(client, "list")
    assert result["groups"][0]["parameters"][13]["value"] == -40    # P13 has no sensor

    assert "Unknown parameter group" in await _error(client, "read_group", group="nope")
    fake.fail_all = True
    assert "did not answer" in await _error(client, "read_group", group="protection")


# ── write ──────────────────────────────────────────────────────────────


async def test_write_reads_back_and_logs(hass, fake_client, hass_ws_client, hass_admin_user):
    await _setup(hass)
    client = await hass_ws_client(hass)
    fake = fake_client.instances[-1]
    events = async_capture_events(hass, EVENT_PARAMETER_WRITTEN)
    fake.requests.clear()

    assert await _ok(client, "write", key="0163", value=5) == {"value": 5}
    assert fake.writes == [("write_register", 0x0163, 5)]
    # Read before (the old value) and after (the read-back)
    assert fake.requests == [("read_holding_registers", 0x0163, 1)] * 2
    assert hass.data[DOMAIN][ENTRY_ID].data[0x0163] == 5
    await hass.async_block_till_done()
    assert events[0].data == {
        "device_id": _device_id(hass), "key": "0163", "name": P99, "old": 7, "new": 5,
    }
    assert events[0].context.user_id == hass_admin_user.id
    assert _logbook(hass, events[0]) == {"name": P99, "message": "changed from 7 °C to 5 °C"}

    # A negative value, and a choice
    assert await _ok(client, "write", key="0115", value=-20) == {"value": -20}
    assert fake.writes[-1] == ("write_register", 0x0115, 0x10000 - 20)
    assert await _ok(client, "write", key="0343", value=1) == {"value": 1}
    await hass.async_block_till_done()
    assert _logbook(hass, events[2])["message"] == "changed from Auto to Manual"
    assert (await _ok(client, "list"))["pump_manual"] is True


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("012D", 2, "read-only"),            # P45 is protected
        ("0803", 2200, "read-only"),         # L14 has no known range
        ("0163", 11, "outside 2 to 10"),
        ("0163", 5.5, "not a multiple of 1"),
        ("011E", 4, "not one of [0, 1, 2, 3]"),
        ("FFFF", 1, "Unknown parameter"),
    ],
)
async def test_write_refusals(hass, fake_client, hass_ws_client, key, value, message):
    await _setup(hass)
    client = await hass_ws_client(hass)
    events = async_capture_events(hass, EVENT_PARAMETER_WRITTEN)
    assert message in await _error(client, "write", key=key, value=value)
    await hass.async_block_till_done()
    assert fake_client.instances[-1].writes == [] and events == []


async def test_write_read_back_mismatch(hass, fake_client, hass_ws_client):
    await _setup(hass)
    client = await hass_ws_client(hass)
    fake = fake_client.instances[-1]
    events = async_capture_events(hass, EVENT_PARAMETER_WRITTEN)
    fake.keeps[0x0163] = 6
    message = await _error(client, "write", key="0163", value=5)
    assert message == f"{P99}: wrote 5, but the heat pump reports 6"
    # The cache and the logbook follow what the heat pump holds
    assert hass.data[DOMAIN][ENTRY_ID].data[0x0163] == 6
    await hass.async_block_till_done()
    assert (events[0].data["old"], events[0].data["new"]) == (7, 6)


async def test_write_rejected_by_controller(hass, fake_client, hass_ws_client):
    await _setup(hass)
    client = await hass_ws_client(hass)
    fake_client.instances[-1].reject[0x0163] = 4
    message = await _error(client, "write", key="0163", value=5)
    assert "Writing 0x0163 failed: read_holding_registers" in message
    assert fake_client.instances[-1].writes == []


async def test_write_without_read_back_is_still_logged(hass, fake_client, hass_ws_client):
    await _setup(hass)
    client = await hass_ws_client(hass)
    fake = fake_client.instances[-1]
    events = async_capture_events(hass, EVENT_PARAMETER_WRITTEN)
    write = fake.write_register

    def write_then_go_silent(address, **kwargs):
        fake.fail_at.add(address)
        return write(address, **kwargs)

    fake.write_register = write_then_go_silent
    message = await _error(client, "write", key="0163", value=5)
    assert message == f"{P99}: wrote 5, but could not read it back"
    assert fake.registers[0x0163] == 5
    await hass.async_block_till_done()
    assert _logbook(hass, events[0])["message"] == "changed from 7 °C to unknown (not read back)"


# ── set_choices ────────────────────────────────────────────────────────


async def test_set_choices_reloads_and_syncs_sensors(hass, fake_client, hass_ws_client):
    entry = await _setup(hass)
    client = await hass_ws_client(hass)
    first = hass.data[DOMAIN][ENTRY_ID]
    assert not _sensor(hass, "010B")

    await _ok(client, "set_choices", sensors=["010B", "0177"], automations=["0163"])
    # Answered after the reload: no waiting needed here
    assert entry.state is ConfigEntryState.LOADED and hass.data[DOMAIN][ENTRY_ID] is not first
    assert entry.options == {
        CONF_PARAMS: {"010B": "read_only", "0177": "read_only"},
        CONF_AUTOMATION_PARAMS: ["0163"],
    }
    assert _sensor(hass, "010B").state == "65"
    params = {p["key"]: p for g in (await _ok(client, "list"))["groups"] for p in g["parameters"]}
    assert params["010B"]["sensor"] and params["0163"]["automation"]

    await _ok(client, "set_choices", sensors=["0177"], automations=["0163"])
    assert not _sensor(hass, "010B") and _sensor(hass, "0177")

    # Only editable parameters can be ticked for automations; nothing is stored
    assert "P45" in await _error(client, "set_choices", sensors=[], automations=["012D"])
    assert "Unknown parameters: 9999" in await _error(client, "set_choices", sensors=["9999"], automations=[])
    assert entry.options[CONF_PARAMS] == {"0177": "read_only"}


# ── export and baseline ────────────────────────────────────────────────


async def test_export(hass, fake_client, hass_ws_client):
    await _setup(hass)
    client = await hass_ws_client(hass)
    parameters = {p["key"]: p for p in (await _ok(client, "export"))["parameters"]}
    assert len(parameters) == 291
    assert parameters["0115"] == {
        "code": "P21", "key": "0115", "name": "Low temp unit prohibit start",
        "value": -26, "unit": "°C", "raw": 65510,
    }
    assert parameters["012D"]["value"] == 1          # protected ones are exported too
    assert parameters["0344"]["code"] is None and parameters["0344"]["raw"] == 0


async def test_baseline(hass, fake_client, hass_ws_client, hass_storage):
    entry = await _setup(hass)
    client = await hass_ws_client(hass)

    def baselines(result) -> dict:
        return {p["key"]: p["baseline"] for g in result["groups"] for p in g["parameters"]}

    # Seeded from the reference: 63 parameters have a default, the others none
    seeded = baselines(await _ok(client, "list"))
    assert sum(v is not None for v in seeded.values()) == 63
    assert seeded["0163"] == 5 and seeded["0164"] is None

    set_at = (await _ok(client, "set_baseline"))["baseline_set_at"]
    result = await _ok(client, "list")
    own = baselines(result)
    assert result["baseline_set_at"] == set_at
    assert own["0163"] == 7 and own["0164"] == 70 and None not in own.values()
    assert hass_storage[BASELINE_KEY]["data"]["values"]["0115"] == -26

    # Kept outside the config entry: survives a reload, goes with the entry
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert baselines(await _ok(client, "list")) == own
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert BASELINE_KEY not in hass_storage


# ── Not loaded ─────────────────────────────────────────────────────────


async def test_unreachable_heat_pump_is_listed_as_not_loaded(hass, fake_client, hass_ws_client, monkeypatch):
    monkeypatch.setattr(fake_client, "refuse_connect", True)
    entry = await _setup(hass, sensors=["010B"])
    assert entry.state is ConfigEntryState.SETUP_RETRY
    client = await hass_ws_client(hass)
    result = await _ok(client, "list")
    assert result["entries"][0]["loaded"] is False and result["pump_manual"] is None
    shown = result["groups"][0]["parameters"][11]
    assert shown["key"] == "010B" and shown["sensor"] and shown["value"] is None


async def test_not_loaded_refuses_bus_access(hass, fake_client, hass_ws_client):
    entry = await _setup(hass, automations=["0163"])
    device_id = _device_id(hass)
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    client = await hass_ws_client(hass)
    for command, fields in (
        ("read_group", {"group": "water"}),
        ("write", {"key": "0163", "value": 5}),
        ("export", {}),
        ("set_baseline", {}),
    ):
        assert "is not loaded" in await _error(client, command, **fields), command
    with pytest.raises(HomeAssistantError, match="is not loaded"):
        await hass.services.async_call(
            DOMAIN, "set_parameter", {"device_id": device_id, "parameter": "P99", "value": 5},
            blocking=True,
        )


# ── Service ────────────────────────────────────────────────────────────


async def test_service_writes_ticked_parameters_only(hass, fake_client, hass_admin_user):
    await _setup(hass, automations=["0163", "0344"])
    fake = fake_client.instances[-1]
    events = async_capture_events(hass, EVENT_PARAMETER_WRITTEN)
    device_id = _device_id(hass)

    async def call(parameter, value, device=device_id, **kwargs):
        await hass.services.async_call(
            DOMAIN, "set_parameter",
            {"device_id": device, "parameter": parameter, "value": value},
            blocking=True, **kwargs,
        )

    context = Context(user_id=hass_admin_user.id)
    await call("p99", 6, context=context)
    await call("0344", "45")                 # the DC pump pair goes by register key
    assert fake.writes == [("write_register", 0x0163, 6), ("write_register", 0x0344, 45)]
    await hass.async_block_till_done()
    assert events[0].context is context and events[0].data["new"] == 6
    assert _logbook(hass, events[1]) == {"name": "DC Pump Output", "message": "changed from 0 % to 45 %"}

    with pytest.raises(ServiceValidationError, match='tick "Allow automations"'):
        await call("P100", 30)
    with pytest.raises(ServiceValidationError, match="outside 2 to 10"):
        await call("P99", 1)
    with pytest.raises(ServiceValidationError, match="Unknown parameter P999"):
        await call("P999", 1)
    with pytest.raises(ServiceValidationError, match="not an Adlar heat pump"):
        await call("P99", 5, device="nope")
    fake.keeps[0x0163] = 9
    with pytest.raises(HomeAssistantError, match="wrote 5, but the heat pump reports 9"):
        await call("P99", 5)
    assert len(fake.writes) == 3


# ── Wiring ─────────────────────────────────────────────────────────────


@pytest.fixture
async def web(hass):
    # As in test_panel: http is real, the frontend only marked as set up
    assert await async_setup_component(hass, "http", {})
    hass.config.components.add("frontend")


async def test_panel_stays_through_reloads_and_goes_with_the_last_entry(
    hass, fake_client, web, hass_ws_client
):
    entry = await _setup(hass)
    panel = hass.data[DATA_PANELS][PANEL_URL_PATH]
    assert panel.require_admin is True
    assert hass.services.has_service(DOMAIN, "set_parameter")

    first = hass.data[DOMAIN][ENTRY_ID]
    client = await hass_ws_client(hass)
    await _ok(client, "set_choices", sensors=["010B"], automations=[])
    assert hass.data[DOMAIN][ENTRY_ID] is not first              # reloaded
    assert hass.data[DATA_PANELS][PANEL_URL_PATH] is panel
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.data[DATA_PANELS][PANEL_URL_PATH] is panel

    # A second heat pump keeps the panel when the first is removed
    other = MockConfigEntry(
        domain=DOMAIN, entry_id="01OTHER", minor_version=3,
        data={"host": "192.0.2.2", "port": 502, "slave": 1, "scan_interval": 60},
    )
    other.add_to_hass(hass)
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.data[DATA_PANELS][PANEL_URL_PATH] is panel
    await hass.config_entries.async_remove(other.entry_id)
    await hass.async_block_till_done()
    assert PANEL_URL_PATH not in hass.data[DATA_PANELS]


async def test_unreachable_heat_pump_has_the_panel(hass, fake_client, web, monkeypatch):
    monkeypatch.setattr(fake_client, "refuse_connect", True)
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert PANEL_URL_PATH in hass.data[DATA_PANELS]
