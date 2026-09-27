"""Modbus TCP simulator of the Adlar Aurora II controller for the dev Home Assistant.

Serves the live snapshot from the HHI v2.2 reference (tests/fixtures). Addresses that
aren't in the snapshot answer with exception 2 (illegal address), like the controller.
Writes are accepted and kept in memory until the container restarts.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os

from pymodbus.datastore import (
    ModbusDeviceContext,
    ModbusServerContext,
    ModbusSparseDataBlock,
)
from pymodbus.server import StartAsyncTcpServer

FIXTURE = os.environ.get("SNAPSHOT", "/fixtures/snapshot_2026-06-15.json")
PORT = int(os.environ.get("PORT", "502"))


def load() -> tuple[dict[int, int], dict[int, bool]]:
    data = json.load(open(FIXTURE))
    registers = {int(k, 16): v for k, v in data["registers"].items()}
    # System 2-4 fault mirrors exist on the controller but weren't in the snapshot
    for addr in range(0x000A, 0x0019):
        registers.setdefault(addr, 0)
    coils = {int(k, 16): v for k, v in data["coils"].items()}
    return registers, coils


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    registers, coils = load()
    device = ModbusDeviceContext(
        hr=ModbusSparseDataBlock(registers),
        co=ModbusSparseDataBlock(coils),
    )
    logging.info("Serving %d registers and %d coils on port %d", len(registers), len(coils), PORT)
    await StartAsyncTcpServer(ModbusServerContext(devices=device, single=True), address=("0.0.0.0", PORT))


if __name__ == "__main__":
    asyncio.run(main())
