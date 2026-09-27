"""Register decoding, block planning and writes against the v2.2 snapshot."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.adlar_heatpump.coordinator import (
    BLOCK_SIZE,
    AdlarCoordinator,
    plan_blocks,
)
from custom_components.adlar_heatpump.registers import BY_ADDR, REGISTERS


@pytest.fixture
def coordinator(fake_client):
    hass = MagicMock()
    coord = AdlarCoordinator.__new__(AdlarCoordinator)
    # Only the Modbus side is under test here: skip DataUpdateCoordinator.__init__
    coord.hass = hass
    coord.host, coord.port, coord.slave, coord.slow_interval = "h", 502, 1, 600
    coord._client = None
    coord._unit_kw = None
    coord._raw = {}
    coord._unsupported = set()
    coord._last_slow = None
    fast = {r.addr for r in REGISTERS if r.fast} | set(range(0x20))
    coord._fast_blocks = plan_blocks(fast)
    coord._slow_blocks = plan_blocks({r.addr for r in REGISTERS if not r.fast})
    coord._coil_block = (0x1000, 0x1B)
    return coord


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


def test_unsupported_register_falls_back_and_is_skipped(coordinator, fake_client):
    coordinator._fetch_all()
    client = fake_client.instances[-1]
    # 0x0085 isn't in the snapshot: the controller rejects it and it's skipped afterwards
    assert 0x0085 in coordinator._unsupported
    client.requests.clear()
    coordinator._fetch_all()
    assert not any(addr == 0x0085 for _, addr, _ in client.requests)


def test_block_with_one_bad_address_keeps_the_rest(coordinator, fake_client):
    coordinator._fetch_all()
    client = fake_client.instances[-1]
    del client.registers[0x0048]
    coordinator._last_slow = None
    coordinator._unsupported.clear()
    data = coordinator._fetch_all()
    assert data[0x0048] is None
    assert data[0x0049] == 14


def test_slow_tier_only_every_interval(coordinator, fake_client):
    coordinator._fetch_all()
    client = fake_client.instances[-1]
    client.requests.clear()
    coordinator._fetch_all()
    slow = {r.addr for r in REGISTERS if not r.fast}
    assert not any(addr in slow for _, addr, _ in client.requests)


def test_write_clamps_to_range(coordinator, fake_client):
    coordinator._fetch_all()
    client = fake_client.instances[-1]
    assert coordinator.write_value(BY_ADDR[0x0301], 99)
    assert client.writes[-1] == ("write_register", 0x0301, 60)


def test_write_negative_and_r290_scaling(coordinator, fake_client):
    coordinator._fetch_all()
    client = fake_client.instances[-1]
    coordinator.write_value(BY_ADDR[0x010D], -42)
    assert client.writes[-1] == ("write_register", 0x010D, (-42) & 0xFFFF)
    assert coordinator._fetch_all()[0x010D] == -42

    coordinator._raw[0x0177] = 3  # R290: temperatures in tenths
    coordinator.write_value(BY_ADDR[0x0301], 45.5)
    assert client.writes[-1] == ("write_register", 0x0301, 455)
    assert coordinator._fetch_all()[0x0301] == 45.5


def test_ac_current_calibration(coordinator):
    reg = BY_ADDR[0x0045]
    assert coordinator.decode(reg, 70) == 5.5
    assert coordinator.decode(reg, 0) == 0
