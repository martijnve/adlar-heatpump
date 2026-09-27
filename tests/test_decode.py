"""Register decoding, block planning, transport errors and writes against the v2.2 snapshot."""
from __future__ import annotations

import pytest
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.adlar_heatpump.const import DOMAIN
from custom_components.adlar_heatpump.coordinator import (
    BLOCK_SIZE,
    AdlarCoordinator,
    ModbusUnavailable,
    plan_blocks,
)
from custom_components.adlar_heatpump.registers import BY_ADDR, REGISTERS

from .conftest import FakeModbusClient


@pytest.fixture
def coordinator(hass, fake_client):
    entry = MockConfigEntry(domain=DOMAIN, data={"host": "192.0.2.1"})
    entry.add_to_hass(hass)
    return AdlarCoordinator(hass, entry, "192.0.2.1", 502, 1, 60, 600)


def _client() -> FakeModbusClient:
    return FakeModbusClient.instances[-1]


def test_plan_blocks_covers_every_register_once():
    addrs = [r.addr for r in REGISTERS]
    blocks = plan_blocks(addrs)
    covered = [a for start, count in blocks for a in range(start, start + count)]
    assert sorted(covered) == sorted(set(addrs))
    assert all(count <= BLOCK_SIZE for _, count in blocks)


def test_plan_blocks_splits_on_gaps():
    assert plan_blocks([1, 2, 3, 7, 8]) == [(1, 3), (7, 2)]


def test_decoded_snapshot_values(coordinator):
    data = coordinator._fetch_all()
    assert coordinator.refrigerant_type == 2
    assert coordinator.temperature_scale == 1.0
    assert data[0x0044] == 224.73               # 227 × 0.99
    assert data[0x010D] == -40                  # P13, two's complement
    assert data[0x0072] is None                 # solar sensor sentinel −50 °C
    assert data[0x004F] == 36                   # T6 inlet, R32 whole degrees
    assert data[0x0301] == 40                   # heating setpoint
    assert data[0x0019] == 16448                # relay output 1 bitmask stays raw
    assert data[0x0304] == 1                    # option register stays raw
    assert data[0x0363] == 143
    assert data[0x101A] is True and data[0x1000] is False


def test_r290_temperatures_in_tenths(coordinator):
    coordinator._fetch_all()
    client = _client()
    client.registers[0x0177] = 3
    client.registers[0x004F] = 355
    coordinator._last_slow = None
    data = coordinator._fetch_all()
    assert coordinator.temperature_scale == 0.1
    assert data[0x004F] == 35.5


def test_unsupported_register_falls_back_and_is_skipped(coordinator):
    coordinator._fetch_all()
    # 0x0085 isn't in the snapshot: the controller rejects it and it's skipped afterwards
    assert 0x0085 in coordinator._unsupported
    _client().requests.clear()
    coordinator._fetch_all()
    assert not any(addr == 0x0085 for _, addr, _ in _client().requests)


def test_block_with_one_bad_address_keeps_the_rest(coordinator):
    coordinator._fetch_all()
    del _client().registers[0x0048]
    data = coordinator._fetch_all()
    assert data[0x0048] is None
    assert data[0x0049] == 14


def test_other_exception_code_is_not_remembered_as_unsupported(coordinator):
    coordinator._fetch_all()
    _client().reject[0x0048] = 4          # slave device failure: transient
    data = coordinator._fetch_all()
    assert data[0x0048] is None and data[0x0049] == 14
    assert 0x0048 not in coordinator._unsupported
    del _client().reject[0x0048]
    assert coordinator._fetch_all()[0x0048] == 13


def test_timeout_on_one_block_keeps_the_poll(coordinator):
    coordinator._fetch_all()
    _client().fail_at.add(0x0040)
    data = coordinator._fetch_all()
    assert data[0x0040] is None            # the failed block is unknown
    assert data[0x0301] == 40              # other blocks still read
    # The broken connection was closed, a new one opened
    assert len(FakeModbusClient.instances) == 2
    assert not FakeModbusClient.instances[0].connected


def test_every_request_failing_fails_the_poll(coordinator):
    coordinator._fetch_all()
    _client().fail_all = True
    with pytest.raises(Exception, match="no answer"):
        coordinator._fetch_all()


def test_gateway_down_fails_the_poll(coordinator):
    coordinator._fetch_all()
    coordinator._drop_client()
    FakeModbusClient.refuse_connect = True
    try:
        with pytest.raises(ModbusUnavailable):
            coordinator._fetch_all()
    finally:
        FakeModbusClient.refuse_connect = False


def test_coil_rejection_does_not_fail_the_poll(coordinator):
    coordinator._fetch_all()
    _client().reject_coils = 1             # illegal function: no coil support
    data = coordinator._fetch_all()
    assert data[0x1000] is None
    assert data[0x0301] == 40


def test_coils_skipped_below_protocol_130(coordinator):
    coordinator._fetch_all()
    _client().registers[0x0363] = 120
    coordinator._last_slow = None
    coordinator._fetch_all()
    _client().requests.clear()
    coordinator._fetch_all()
    assert not any(name == "read_coils" for name, _, _ in _client().requests)


def test_slow_tier_only_every_interval(coordinator):
    coordinator._fetch_all()
    _client().requests.clear()
    coordinator._fetch_all()
    slow = {r.addr for r in REGISTERS if not r.fast}
    assert not any(addr in slow for _, addr, _ in _client().requests)


def test_failed_slow_tier_keeps_values_and_retries(coordinator):
    coordinator._fetch_all()
    start = next(b for b, n in coordinator._slow_blocks if b <= 0x0177 < b + n)
    _client().fail_at.add(start)
    coordinator._last_slow = None
    data = coordinator._fetch_all()
    assert coordinator.refrigerant_type == 2      # P119 kept from the previous read
    assert data[0x0177] == 2
    assert coordinator._last_slow is None         # retried next poll


async def test_write_clamps_to_range(coordinator):
    coordinator.async_set_updated_data(coordinator._fetch_all())
    await coordinator.async_write_value(BY_ADDR[0x0301], 99)
    assert _client().writes[-1] == ("write_register", 0x0301, 60)
    assert coordinator.data[0x0301] == 60         # shown before the next poll


async def test_write_negative_and_r290_scaling(coordinator):
    coordinator.async_set_updated_data(coordinator._fetch_all())
    await coordinator.async_write_value(BY_ADDR[0x010D], -42)
    assert _client().writes[-1] == ("write_register", 0x010D, (-42) & 0xFFFF)
    assert coordinator.data[0x010D] == -42

    coordinator._raw[0x0177] = 3  # R290: temperatures in tenths
    await coordinator.async_write_value(BY_ADDR[0x0301], 45.5)
    assert _client().writes[-1] == ("write_register", 0x0301, 455)
    assert coordinator.data[0x0301] == 45.5


async def test_write_failure_raises(coordinator):
    coordinator.async_set_updated_data(coordinator._fetch_all())
    _client().reject[0x0301] = 3
    with pytest.raises(HomeAssistantError):
        await coordinator.async_write_value(BY_ADDR[0x0301], 45)
    assert coordinator.data[0x0301] == 40


async def test_coil_write(coordinator):
    coordinator.async_set_updated_data(coordinator._fetch_all())
    await coordinator.async_write_coil(0x1013, True)
    assert _client().writes[-1] == ("write_coil", 0x1013, True)
    assert coordinator.data[0x1013] is True


def test_ac_current_calibration(coordinator):
    reg = BY_ADDR[0x0045]
    assert coordinator.decode(reg, 70) == 5.5
    assert coordinator.decode(reg, 0) == 0
    # Past the curve the sensor is linear again, keeping the last offset
    assert coordinator.decode(reg, 150) == 13.0


def test_equal_intervals_read_slow_tier_every_poll(hass, fake_client):
    entry = MockConfigEntry(domain=DOMAIN, data={"host": "192.0.2.1"})
    entry.add_to_hass(hass)
    coord = AdlarCoordinator(hass, entry, "192.0.2.1", 502, 1, 600, 600)
    coord._fetch_all()
    # The next poll comes slightly early relative to when the slow tier was read
    coord._last_slow -= 599
    _client().requests.clear()
    coord._fetch_all()
    slow = {r.addr for r in REGISTERS if not r.fast}
    assert any(addr in slow for _, addr, _ in _client().requests)
