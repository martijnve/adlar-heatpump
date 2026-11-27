"""Panel mode: the heat pump reached through the thermostat panel's ESPHome actions, faked here."""
from __future__ import annotations

import asyncio

import pytest
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
)

from custom_components.adlar_heatpump import coordinator as coordinator_module
from custom_components.adlar_heatpump.const import DOMAIN, EVENT_PARAMETER_WRITTEN
from custom_components.adlar_heatpump.coordinator import (
    KNOWN_REGISTERS,
    RESERVED_COUNTS,
    ModbusRequestFailed,
    ModbusUnavailable,
)
from custom_components.adlar_heatpump.param_info import PARAMS, find_param
from custom_components.adlar_heatpump.registers import param_key

from .conftest import load_snapshot

ENTRY_ID = "01PANELENTRY"
PREFIX = "living_room_thermostat"
PIN = "0123"
P99 = find_param("P99")


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


class FakePanel:
    """The panel's actions over the v2.2 snapshot, with the firmware's error answers."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.registers, _ = load_snapshot()
        self.reads: list[tuple[int, int]] = []
        self.writes: list[dict] = []
        self.error: str | None = None          # answer every call with this error
        self.short = False                     # answer one word too few
        self.write_answer: dict | None = None  # instead of the echo
        self.delay = 0.0
        self.active = self.most_active = 0
        for action, handler in (
            ("read_parameters", self.read),
            ("write_parameter", self.write),
            ("check_pin", self.check_pin),
        ):
            hass.services.async_register(
                "esphome", f"{PREFIX}_{action}", handler, supports_response=SupportsResponse.ONLY
            )

    def _fail(self) -> None:
        if self.error:
            raise HomeAssistantError(f"Failed to execute the action: {self.error}")

    async def read(self, call: ServiceCall) -> dict:
        start, count = call.data["start"], call.data["count"]
        self.reads.append((start, count))
        self.active += 1
        self.most_active = max(self.most_active, self.active)
        await asyncio.sleep(self.delay)
        self.active -= 1
        assert count not in RESERVED_COUNTS and count <= 125, "the firmware refuses this count"
        self._fail()
        addrs = range(start, start + count)
        if any(a not in self.registers for a in addrs):
            raise HomeAssistantError("Failed to execute the action: exception:2")
        values = [self.registers[a] for a in addrs]
        return {"values": values[1:] if self.short else values}

    async def write(self, call: ServiceCall) -> dict:
        self.writes.append(dict(call.data))
        self._fail()
        if call.data["pin"] != PIN:
            raise HomeAssistantError("Failed to execute the action: pin")
        reg, value = call.data["reg"], call.data["value"]
        before = self.registers[reg]
        if before != call.data["expected"]:
            raise HomeAssistantError(f"Failed to execute the action: mismatch:{before}")
        if self.write_answer is not None:
            return {"before": before, **self.write_answer}
        self.registers[reg] = value
        return {"before": before, "after": value, "echo": True}

    async def check_pin(self, call: ServiceCall) -> dict:
        return {"result": self.error or ("ok" if call.data["pin"] == PIN else "wrong")}


@pytest.fixture
def panel(hass) -> FakePanel:
    return FakePanel(hass)


async def _setup(hass: HomeAssistant, pin: str = PIN) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, entry_id=ENTRY_ID, version=2, minor_version=3, title="Heat pump",
        data={"transport": "panel", "prefix": PREFIX, "pin": pin},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _coordinator(hass):
    return hass.data[DOMAIN][ENTRY_ID]


async def test_setup_has_no_entities_and_a_device(hass, panel):
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.LOADED
    assert er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id) == []
    assert dr.async_get(hass).async_get_device(identifiers={(DOMAIN, ENTRY_ID)})
    assert panel.reads == []                   # no poll, no first refresh
    assert not entry.supports_options


async def test_unload(hass, panel):
    entry = await _setup(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED
    assert ENTRY_ID not in hass.data[DOMAIN]


async def test_reads_never_use_a_reserved_count(hass, panel):
    await _setup(hass)
    raw = await _coordinator(hass).async_read_registers(r.addr for r in PARAMS.values())
    assert panel.reads and not any(count in RESERVED_COUNTS for _, count in panel.reads)
    assert raw == {
        r.addr: panel.registers[r.addr] for r in PARAMS.values() if r.addr in panel.registers
    }


async def test_block_of_eight_is_widened_and_the_extra_word_dropped(hass, panel):
    await _setup(hass)
    coordinator = _coordinator(hass)
    panel.reads.clear()
    coordinator._raw[0x0177] = 2               # P119 known: only the block itself is read
    raw = await coordinator.async_read_registers(range(0x0100, 0x0108))
    assert panel.reads == [(0x0100, 9)]
    assert sorted(raw) == list(range(0x0100, 0x0108))


async def test_register_at_a_range_end_is_read_with_its_lower_neighbour(hass, panel):
    end = next(
        a for a in sorted(KNOWN_REGISTERS)
        if a >= 0x0100 and a + 1 not in KNOWN_REGISTERS and a - 1 in KNOWN_REGISTERS
    )
    panel.registers.setdefault(end, 7)
    panel.registers.setdefault(end - 1, 6)
    await _setup(hass)
    coordinator = _coordinator(hass)
    coordinator._raw[0x0177] = 2
    panel.reads.clear()
    assert await coordinator.async_read_registers([end]) == {end: panel.registers[end]}
    assert panel.reads == [(end - 1, 2)]


async def test_unsupported_register_is_learnt_through_pairs(hass, panel):
    await _setup(hass)
    coordinator = _coordinator(hass)
    coordinator._raw[0x0177] = 2
    del panel.registers[0x0105]
    raw = await coordinator.async_read_registers(range(0x0100, 0x010A))
    assert 0x0105 not in raw and 0x0104 in raw and 0x0106 in raw
    assert coordinator._unsupported == {0x0105}
    panel.reads.clear()
    await coordinator.async_read_registers(range(0x0100, 0x010A))
    assert not any(start <= 0x0105 < start + count for start, count in panel.reads)


async def test_p119_is_read_first_and_scales_temperatures(hass, panel):
    panel.registers[0x0177] = 3                # R290: temperatures in tenths
    panel.registers[0x004F] = 355
    await _setup(hass)
    coordinator = _coordinator(hass)
    # No installer parameter is a temperature register (yet); water inlet T6 is
    await coordinator.async_read_registers([0x004F, 0x0050])
    assert any(start <= 0x0177 < start + count for start, count in panel.reads[:1])
    assert coordinator.temperature_scale == 0.1
    assert coordinator.data[0x004F] == 35.5


async def test_wrong_length_and_firmware_errors(hass, panel):
    await _setup(hass)
    coordinator = _coordinator(hass)
    coordinator._raw[0x0177] = 2
    panel.short = True
    with pytest.raises(HomeAssistantError, match="did not answer"):
        await coordinator.async_read_registers([P99.addr])
    panel.short = False
    for error in ("busy", "no_reply", "bad_length"):
        panel.error = error
        with pytest.raises(ModbusRequestFailed, match=error):
            await coordinator.panel.read(0x0100, 2)
    panel.error = "timeout"
    with pytest.raises(ModbusUnavailable):
        await coordinator.panel.read(0x0100, 2)
    panel.error = "exception:4"
    with pytest.raises(coordinator_module.ModbusRejected) as rejected:
        await coordinator.panel.read(0x0100, 2)
    assert rejected.value.code == 4


async def test_no_answer_in_time_or_no_action_is_unavailable(hass, panel, monkeypatch):
    await _setup(hass)
    coordinator = _coordinator(hass)
    monkeypatch.setattr(coordinator_module, "PANEL_TIMEOUT", 0.01)
    panel.delay = 1
    with pytest.raises(ModbusUnavailable):
        await coordinator.panel.read(0x0100, 2)
    hass.services.async_remove("esphome", f"{PREFIX}_read_parameters")
    with pytest.raises(HomeAssistantError, match="no action"):
        await coordinator.async_read_registers([P99.addr])


async def test_concurrent_reads_are_serialised(hass, panel):
    await _setup(hass)
    coordinator = _coordinator(hass)
    coordinator._raw[0x0177] = 2
    panel.delay = 0.01
    await asyncio.gather(
        coordinator.async_read_registers(range(0x0100, 0x0104)),
        coordinator.async_read_registers(range(0x0110, 0x0114)),
    )
    assert len(panel.reads) == 2 and panel.most_active == 1


async def test_guarded_write(hass, panel):
    await _setup(hass)
    coordinator = _coordinator(hass)
    events = async_capture_events(hass, EVENT_PARAMETER_WRITTEN)
    old = panel.registers[P99.addr]
    new = old + 1
    assert await coordinator.async_write_param(P99, new, expected=old) == new
    write = panel.writes[-1]
    assert write == {"reg": P99.addr, "value": new, "expected": old, "pin": PIN}
    await hass.async_block_till_done()
    assert events[-1].data["old"] == old and events[-1].data["new"] == new
    assert events[-1].data["device_id"]


async def test_write_sent_without_reply_is_logged_then_an_error(hass, panel):
    await _setup(hass)
    coordinator = _coordinator(hass)
    events = async_capture_events(hass, EVENT_PARAMETER_WRITTEN)
    old = panel.registers[P99.addr]
    panel.write_answer = {"after": old + 1, "echo": False}
    with pytest.raises(HomeAssistantError, match=f"without a confirmation; the heat pump now holds {old + 1}"):
        await coordinator.async_write_param(P99, old + 1, expected=old)
    panel.write_answer = {"after": -1, "echo": False}
    with pytest.raises(HomeAssistantError, match="now holds unknown"):
        await coordinator.async_write_param(P99, old + 1, expected=old)
    await hass.async_block_till_done()
    assert [(e.data["old"], e.data["new"]) for e in events] == [(old, old + 1), (old, None)]


async def test_write_mismatch_and_busy_send_nothing_more(hass, panel):
    await _setup(hass)
    coordinator = _coordinator(hass)
    events = async_capture_events(hass, EVENT_PARAMETER_WRITTEN)
    old = panel.registers[P99.addr]
    with pytest.raises(HomeAssistantError, match=f"now {old}"):
        await coordinator.async_write_param(P99, old, expected=old + 1)
    panel.error = "busy"
    with pytest.raises(HomeAssistantError, match="busy"):
        await coordinator.async_write_param(P99, old, expected=old)
    with pytest.raises(ServiceValidationError, match="read the parameter"):
        await coordinator.async_write_param(P99, old)
    await hass.async_block_till_done()
    assert events == []


async def test_wrong_pin_starts_reauth_locked_does_not(hass, panel):
    entry = await _setup(hass, pin="9999")
    coordinator = _coordinator(hass)
    coordinator._raw[0x0177] = 2               # P119 known: the error answers the write itself
    old = panel.registers[P99.addr]
    panel.error = "locked"
    with pytest.raises(HomeAssistantError, match="locked"):
        await coordinator.async_write_param(P99, old, expected=old)
    await hass.async_block_till_done()
    assert not list(entry.async_get_active_flows(hass, {SOURCE_REAUTH}))
    panel.error = None
    with pytest.raises(HomeAssistantError, match="PIN"):
        await coordinator.async_write_param(P99, old, expected=old)
    await hass.async_block_till_done()
    flow = next(iter(entry.async_get_active_flows(hass, {SOURCE_REAUTH})))

    result = await hass.config_entries.flow.async_configure(flow["flow_id"], {"pin": "1111"})
    assert result["errors"] == {"base": "wrong_pin"}
    result = await hass.config_entries.flow.async_configure(flow["flow_id"], {"pin": PIN})
    assert result["type"] == "abort" and result["reason"] == "reauth_successful"
    await hass.async_block_till_done()
    assert entry.data["pin"] == PIN
    assert await _coordinator(hass).async_write_param(P99, old, expected=old) == old


async def test_set_parameter_and_choices_refuse(hass, panel, hass_ws_client):
    entry = await _setup(hass)
    # Even a parameter ticked for automations (by an earlier version) is refused
    hass.config_entries.async_update_entry(entry, options={"automation_params": [param_key(P99)]})
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, ENTRY_ID)})
    with pytest.raises(ServiceValidationError, match="thermostat panel"):
        await hass.services.async_call(
            DOMAIN, "set_parameter",
            {"device_id": device.id, "parameter": "P99", "value": 5}, blocking=True,
        )
    assert panel.writes == []

    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/set_choices", "entry_id": ENTRY_ID, "sensors": [], "automations": []}
    )
    answer = await client.receive_json()
    assert not answer["success"] and "thermostat panel" in answer["error"]["message"]
    await client.send_json_auto_id({"type": f"{DOMAIN}/list", "entry_id": ENTRY_ID})
    answer = await client.receive_json()
    assert answer["result"]["mode"] == "panel"


async def test_ws_write_passes_expected(hass, panel, hass_ws_client):
    await _setup(hass)
    old = panel.registers[P99.addr]
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({
        "type": f"{DOMAIN}/write", "entry_id": ENTRY_ID, "key": param_key(P99),
        "value": old + 1, "expected": old,
    })
    answer = await client.receive_json()
    assert answer["success"], answer
    assert answer["result"] == {"value": old + 1} and panel.writes[-1]["expected"] == old


async def test_config_flow_adds_a_panel_entry(hass, panel):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"transport": "panel"})
    assert result["step_id"] == "panel"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"prefix": PREFIX, "pin": "1111"}
    )
    assert result["errors"] == {"base": "wrong_pin"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"prefix": "other_panel", "pin": PIN}
    )
    assert result["errors"] == {"base": "no_panel"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"prefix": PREFIX, "pin": PIN}
    )
    assert result["type"] == "create_entry"
    entry = result["result"]
    assert entry.version == 2
    assert entry.data == {"transport": "panel", "prefix": PREFIX, "pin": PIN}


async def test_tcp_entry_stays_version_1(hass, fake_client):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": "192.0.2.1", "port": 502, "slave": 1, "scan_interval": 600}
    )
    assert result["type"] == "create_entry"
    assert result["result"].version == 1 and "transport" not in result["result"].data
