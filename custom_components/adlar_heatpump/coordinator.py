"""Modbus TCP data coordinator for Adlar Heatpump."""
from __future__ import annotations

import inspect
import logging
import time
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .registers import (
    AC_CURRENT_REGISTER,
    COILS,
    REFRIGERANT_REGISTER,
    REGISTERS,
    SENSOR,
    SENSOR_SENTINEL,
    R,
    calibrate_ac_current,
    temperature_scale,
)

_LOGGER = logging.getLogger(__name__)

# Delay between Modbus requests (seconds)
# Gives the JPX-3002 splitter and EW11 time to process each request
REQUEST_DELAY = 0.2

# Registers per read request. The controller answers up to 125, but small blocks keep a
# failing block cheap to retry register by register.
BLOCK_SIZE = 32

# Modbus exception code for an address the controller doesn't implement
ILLEGAL_DATA_ADDRESS = 2

# All status/fault/relay registers, including the System 2-4 mirrors, in one read
STATUS_BLOCK = range(0x0020)


def _to_signed(value: int) -> int:
    return value - 0x10000 if value & 0x8000 else value


def plan_blocks(addresses) -> list[tuple[int, int]]:
    """Group addresses into (start, count) runs of contiguous addresses, at most BLOCK_SIZE long."""
    blocks: list[tuple[int, int]] = []
    for addr in sorted(set(addresses)):
        if blocks:
            start, count = blocks[-1]
            if addr == start + count and count < BLOCK_SIZE:
                blocks[-1] = (start, count + 1)
                continue
        blocks.append((addr, 1))
    return blocks


class ModbusUnavailable(Exception):
    """Gateway niet bereikbaar - hele pollcyclus overslaan."""


class AdlarCoordinator(DataUpdateCoordinator):
    """Polls the heat pump in two tiers and decodes all registers.

    `data` maps register address to decoded value: numbers for measurements, the raw
    integer for bitmask and option registers, bool for coils (0x10xx).
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        host: str,
        port: int,
        slave: int,
        scan_interval: int,
        slow_interval: int,
    ) -> None:
        self.host = host
        self.port = port
        self.slave = slave
        self.slow_interval = slow_interval
        self._client = None
        self._unit_kw: str | None = None
        self._raw: dict[int, int] = {}
        self._unsupported: set[int] = set()
        self._last_slow: float | None = None

        fast = {r.addr for r in REGISTERS if r.fast} | set(STATUS_BLOCK)
        slow = {r.addr for r in REGISTERS if not r.fast}
        self._fast_blocks = plan_blocks(fast)
        self._slow_blocks = plan_blocks(slow)
        self._coil_block = (min(COILS), max(COILS) - min(COILS) + 1)

        super().__init__(
            hass, _LOGGER, name=DOMAIN, config_entry=entry,
            update_interval=timedelta(seconds=scan_interval),
        )

    # ── Refrigerant ────────────────────────────────────────────────────

    @property
    def refrigerant_type(self) -> int | None:
        return self._raw.get(REFRIGERANT_REGISTER)

    @property
    def temperature_scale(self) -> float:
        return temperature_scale(self.refrigerant_type)

    # ── Transport ──────────────────────────────────────────────────────

    def _get_client(self):
        """Return connected client, reconnect if needed."""
        from pymodbus.client import ModbusTcpClient
        if self._client is None or not self._client.connected:
            if self._client is not None:
                try:
                    self._client.close()
                except Exception:
                    pass
            self._client = ModbusTcpClient(host=self.host, port=self.port, timeout=10)
            if not self._client.connect():
                self._client = None
                raise ModbusUnavailable(
                    f"geen verbinding met {self.host}:{self.port}"
                )
        return self._client

    def _unit(self, method) -> dict:
        """pymodbus renamed `slave` to `device_id` in 3.10; pass whichever this version takes."""
        if self._unit_kw is None:
            params = inspect.signature(method).parameters
            self._unit_kw = "device_id" if "device_id" in params else "slave"
        return {self._unit_kw: self.slave}

    def _request(self, name: str, address: int, **kwargs):
        """Send one request. Returns the response, or None on a Modbus exception response.

        Transport failures drop the connection and raise ModbusUnavailable.
        """
        time.sleep(REQUEST_DELAY)
        client = self._get_client()
        method = getattr(client, name)
        try:
            result = method(address, **kwargs, **self._unit(method))
        except Exception as err:
            self._client = None
            raise ModbusUnavailable(f"{name} 0x{address:04X}: {err}") from err
        if result.isError():
            if getattr(result, "exception_code", None) == ILLEGAL_DATA_ADDRESS:
                return None
            self._client = None
            raise ModbusUnavailable(f"{name} 0x{address:04X}: {result}")
        return result

    def _read_blocks(self, blocks: list[tuple[int, int]]) -> None:
        """Read holding register blocks into the raw cache.

        A block the controller rejects is retried register by register; addresses it
        rejects on their own are remembered and skipped from then on.
        """
        for start, count in blocks:
            addrs = [a for a in range(start, start + count) if a not in self._unsupported]
            if not addrs:
                continue
            for sub_start, sub_count in plan_blocks(addrs):
                result = self._request(
                    "read_holding_registers", sub_start, count=sub_count
                )
                if result is not None:
                    for i, value in enumerate(result.registers[:sub_count]):
                        self._raw[sub_start + i] = value
                    continue
                for addr in range(sub_start, sub_start + sub_count):
                    single = self._request("read_holding_registers", addr, count=1)
                    if single is None:
                        _LOGGER.debug("Register 0x%04X not supported, skipping it", addr)
                        self._unsupported.add(addr)
                        self._raw.pop(addr, None)
                    else:
                        self._raw[addr] = single.registers[0]

    def _read_coils(self) -> dict[int, bool]:
        start, count = self._coil_block
        result = self._request("read_coils", start, count=count)
        if result is None:
            return {}
        return {addr: bool(result.bits[addr - start]) for addr in COILS}

    # ── Decoding ───────────────────────────────────────────────────────

    def decode(self, reg: R, raw: int) -> float | int | None:
        value = _to_signed(raw) if reg.signed else raw
        if reg.temp:
            scale = self.temperature_scale
            if scale != 1:
                value = round(value * scale, 1)
            if reg.group == SENSOR and value <= SENSOR_SENTINEL:
                return None
            return value
        if reg.scale != 1:
            value = value * reg.scale
            if reg.addr == AC_CURRENT_REGISTER:
                value = calibrate_ac_current(value)
            value = round(value, 2)
        return value

    def encode(self, reg: R, value: float) -> int:
        """Clamp to the register's range and turn a display value into a raw word."""
        if reg.min is not None:
            value = max(value, reg.min)
        if reg.max is not None:
            value = min(value, reg.max)
        if reg.temp:
            raw = round(value / self.temperature_scale)
        else:
            raw = round(value / reg.scale)
        return raw & 0xFFFF

    # ── Polling ────────────────────────────────────────────────────────

    async def _async_update_data(self) -> dict:
        try:
            return await self.hass.async_add_executor_job(self._fetch_all)
        except Exception as err:
            raise UpdateFailed(f"Error communicating with heatpump: {err}") from err

    def _fetch_all(self) -> dict:
        now = time.monotonic()
        if self._last_slow is None or now - self._last_slow >= self.slow_interval:
            self._read_blocks(self._slow_blocks)
            self._last_slow = now
        self._read_blocks(self._fast_blocks)
        coils = self._read_coils()

        data: dict[int, object] = {}
        for reg in REGISTERS:
            raw = self._raw.get(reg.addr)
            if raw is None:
                data[reg.addr] = None
            elif reg.options is not None:
                data[reg.addr] = raw
            else:
                data[reg.addr] = self.decode(reg, raw)
        for addr in STATUS_BLOCK:
            data[addr] = self._raw.get(addr)
        data.update(coils)
        return data

    # ── Writing ────────────────────────────────────────────────────────

    def write_value(self, reg: R, value: float) -> bool:
        """Write a holding register (FC06) and update the cache so the slow tier shows it."""
        raw = self.encode(reg, value)
        try:
            result = self._request("write_register", reg.addr, value=raw)
        except ModbusUnavailable as err:
            _LOGGER.error("Write error at 0x%04X: %s", reg.addr, err)
            return False
        if result is None:
            _LOGGER.error("Write to 0x%04X rejected by the controller", reg.addr)
            return False
        self._raw[reg.addr] = raw
        return True

    def write_coil(self, address: int, value: bool) -> bool:
        """Write a command coil (FC05)."""
        try:
            result = self._request("write_coil", address, value=value)
        except ModbusUnavailable as err:
            _LOGGER.error("Write error at coil 0x%04X: %s", address, err)
            return False
        return result is not None
