"""Fake Modbus client fed by the snapshot fixture in the HHI v2.2 reference."""
from __future__ import annotations

import json
from pathlib import Path
from typing import ClassVar
from unittest.mock import patch

import pytest

from custom_components.adlar_heatpump import coordinator as coordinator_module

FIXTURE = Path(__file__).parent / "fixtures" / "snapshot_2026-06-15.json"


def load_snapshot() -> tuple[dict[int, int], dict[int, bool]]:
    data = json.loads(FIXTURE.read_text())
    registers = {int(k, 16): v for k, v in data["registers"].items()}
    # System 2-4 fault mirrors exist on the controller but weren't in the snapshot
    for addr in range(0x000A, 0x0019):
        registers.setdefault(addr, 0)
    coils = {int(k, 16): v for k, v in data["coils"].items()}
    return registers, coils


class _Response:
    def __init__(self, registers=None, bits=None, exception_code=None):
        self.registers = registers or []
        self.bits = bits or []
        self.exception_code = exception_code

    def isError(self) -> bool:
        return self.exception_code is not None


class FakeModbusClient:
    """Answers like the controller: exception code 2 for addresses it doesn't have."""

    instances: ClassVar[list[FakeModbusClient]] = []

    def __init__(self, host=None, port=None, timeout=None):
        self.registers, self.coils = load_snapshot()
        self.connected = False
        self.requests: list[tuple[str, int, int]] = []
        self.writes: list[tuple[str, int, object]] = []
        FakeModbusClient.instances.append(self)

    def connect(self) -> bool:
        self.connected = True
        return True

    def close(self) -> None:
        self.connected = False

    def read_holding_registers(self, address, *, count=1, device_id=1):
        self.requests.append(("read_holding_registers", address, count))
        addrs = range(address, address + count)
        if any(a not in self.registers for a in addrs):
            return _Response(exception_code=2)
        return _Response(registers=[self.registers[a] for a in addrs])

    def read_coils(self, address, *, count=1, device_id=1):
        self.requests.append(("read_coils", address, count))
        return _Response(bits=[self.coils.get(a, False) for a in range(address, address + count)])

    def write_register(self, address, *, value, device_id=1):
        self.writes.append(("write_register", address, value))
        if address not in self.registers:
            return _Response(exception_code=2)
        self.registers[address] = value
        return _Response()

    def write_coil(self, address, *, value, device_id=1):
        self.writes.append(("write_coil", address, value))
        self.coils[address] = value
        return _Response()


@pytest.fixture
def fake_client():
    FakeModbusClient.instances.clear()
    with patch("pymodbus.client.ModbusTcpClient", FakeModbusClient), \
            patch.object(coordinator_module, "REQUEST_DELAY", 0):
        yield FakeModbusClient
