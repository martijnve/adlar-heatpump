"""Modbus TCP data coordinator for Adlar Heatpump."""
from __future__ import annotations

import inspect
import logging
import threading
import time
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
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

# Protocol version register; coils (FC01/FC05) need protocol >= 130
PROTOCOL_VERSION_REGISTER = 0x0363
MIN_PROTOCOL_COILS = 130

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


class ModbusRequestFailed(Exception):
    """One request got no (valid) answer; the connection is dropped and the next request reconnects."""


class ModbusRejected(Exception):
    """The controller answered with a Modbus exception response."""

    def __init__(self, code: int | None, message: str) -> None:
        super().__init__(message)
        self.code = code


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
        # Polls and writes run in different executor threads; one request at a time
        self._lock = threading.Lock()
        self._unit_kw: str | None = None
        self._raw: dict[int, int] = {}
        self._coils: dict[int, bool] = {}
        self._unsupported: set[int] = set()
        self._last_slow: float | None = None

        fast = {r.addr for r in REGISTERS if r.fast} | set(STATUS_BLOCK)
        slow = {r.addr for r in REGISTERS if not r.fast}
        self._fast_blocks = plan_blocks(fast)
        self._slow_blocks = plan_blocks(slow)
        self._coil_blocks = plan_blocks(COILS)

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

    def _drop_client(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                _LOGGER.debug("Error closing Modbus client", exc_info=True)
        self._client = None

    def close(self) -> None:
        """Close the connection (on unload)."""
        with self._lock:
            self._drop_client()

    def _get_client(self):
        """Return connected client, reconnect if needed."""
        from pymodbus.client import ModbusTcpClient
        if self._client is None or not self._client.connected:
            self._drop_client()
            self._client = ModbusTcpClient(host=self.host, port=self.port, timeout=10)
            if not self._client.connect():
                self._drop_client()
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
        """Send one request and return the response.

        Raises ModbusUnavailable when the gateway can't be reached, ModbusRequestFailed when
        the request got no valid answer, ModbusRejected on an exception response.
        """
        with self._lock:
            time.sleep(REQUEST_DELAY)
            client = self._get_client()
            method = getattr(client, name)
            try:
                result = method(address, **kwargs, **self._unit(method))
            except Exception as err:
                self._drop_client()
                raise ModbusRequestFailed(f"{name} 0x{address:04X}: {err}") from err
            if result.isError():
                code = getattr(result, "exception_code", None)
                if code is None:
                    # Older pymodbus returns transport errors as an error object
                    self._drop_client()
                    raise ModbusRequestFailed(f"{name} 0x{address:04X}: {result}")
                raise ModbusRejected(code, f"{name} 0x{address:04X}: exception code {code}")
            return result

    def _read(self, kind: str, start: int, count: int) -> list:
        name = "read_coils" if kind == "coils" else "read_holding_registers"
        result = self._request(name, start, count=count)
        values = result.bits if kind == "coils" else result.registers
        return list(values[:count])

    def _read_blocks(self, blocks: list[tuple[int, int]], store: dict, kind: str, forget: bool) -> tuple[int, int]:
        """Read blocks into `store`; returns (requests answered, requests failed).

        A block the controller rejects is retried address by address; addresses rejected
        on their own as illegal are remembered and skipped from then on. When `forget` is
        set, addresses that couldn't be read lose their cached value.
        """
        ok = failed = 0
        for start, count in blocks:
            addrs = [a for a in range(start, start + count) if a not in self._unsupported]
            for sub_start, sub_count in plan_blocks(addrs):
                try:
                    values = self._read(kind, sub_start, sub_count)
                except ModbusRequestFailed as err:
                    _LOGGER.debug("Read failed: %s", err)
                    failed += 1
                    if forget:
                        for addr in range(sub_start, sub_start + sub_count):
                            store.pop(addr, None)
                    continue
                except ModbusRejected:
                    values = None
                if values is not None:
                    ok += 1
                    for i, value in enumerate(values):
                        store[sub_start + i] = value
                    continue
                for addr in range(sub_start, sub_start + sub_count):
                    try:
                        store[addr] = self._read(kind, addr, 1)[0]
                        ok += 1
                    except ModbusRejected as err:
                        if err.code == ILLEGAL_DATA_ADDRESS:
                            _LOGGER.debug("Address 0x%04X not supported, skipping it", addr)
                            self._unsupported.add(addr)
                            store.pop(addr, None)
                        elif forget:
                            store.pop(addr, None)
                    except ModbusRequestFailed as err:
                        _LOGGER.debug("Read failed: %s", err)
                        failed += 1
                        if forget:
                            store.pop(addr, None)
        return ok, failed

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

    def _build_data(self) -> dict:
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
        for addr in COILS:
            coil = self._coils.get(addr)
            data[addr] = None if coil is None else bool(coil)
        return data

    # ── Polling ────────────────────────────────────────────────────────

    async def _async_update_data(self) -> dict:
        try:
            return await self.hass.async_add_executor_job(self._fetch_all)
        except Exception as err:
            raise UpdateFailed(f"Error communicating with heatpump: {err}") from err

    def _fetch_all(self) -> dict:
        now = time.monotonic()
        if self._last_slow is None or now - self._last_slow >= self.slow_interval:
            # Keep the previous values of a failed slow block (P119 in particular, which
            # sets the temperature scale) and retry the whole tier on the next poll
            _, failed = self._read_blocks(self._slow_blocks, self._raw, "registers", forget=False)
            if not failed:
                self._last_slow = now
        ok, failed = self._read_blocks(self._fast_blocks, self._raw, "registers", forget=True)
        if not ok:
            raise ModbusRequestFailed(f"no answer to any of {failed} requests")
        protocol = self._raw.get(PROTOCOL_VERSION_REGISTER)
        if protocol is None or protocol >= MIN_PROTOCOL_COILS:
            self._read_blocks(self._coil_blocks, self._coils, "coils", forget=True)
        return self._build_data()

    # ── Writing ────────────────────────────────────────────────────────

    def _write(self, name: str, address: int, value) -> None:
        try:
            self._request(name, address, value=value)
        except (ModbusUnavailable, ModbusRequestFailed, ModbusRejected) as err:
            raise HomeAssistantError(f"Writing 0x{address:04X} failed: {err}") from err

    async def async_write_value(self, reg: R, value: float) -> None:
        """Write a holding register (FC06); raises HomeAssistantError when it fails.

        The cache is updated straight away, so the entity (and the slow tier) shows the
        new value before the next poll.
        """
        raw = self.encode(reg, value)
        await self.hass.async_add_executor_job(self._write, "write_register", reg.addr, raw)
        self._raw[reg.addr] = raw
        self.async_set_updated_data(self._build_data())

    async def async_write_coil(self, address: int, value: bool) -> None:
        """Write a command coil (FC05); raises HomeAssistantError when it fails."""
        await self.hass.async_add_executor_job(self._write, "write_coil", address, value)
        self._coils[address] = value
        self.async_set_updated_data(self._build_data())
