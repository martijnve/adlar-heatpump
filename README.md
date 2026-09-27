# Adlar Heatpump (Aurora II) — Home Assistant Integration

Fork of [conradhagemans/adlar-heatpump](https://github.com/conradhagemans/adlar-heatpump) that exposes every register in the HHI v2.2 register map.

A HACS-compatible custom integration for the **Adlar Castra Aurora II** heat pump, communicating over **Modbus TCP** via an RS485-to-WiFi gateway.

No YAML required. All setup is done through the Home Assistant UI.

---

## Hardware setup

This integration was developed and tested with the following hardware:

- **JPX-3002** RS485 splitter (2 master / 1 slave):
  - **Slave port** → Modbus RS485 cable from the heat pump
  - **Master 1** → JAN module (original controller)
  - **Master 2** → Elfin EW11A (RS485 to WiFi/TCP bridge)
- The **Elfin EW11A** configured as TCP Server on port **502**
- Modbus slave ID of the heat pump: **1** (default)

Any RS485-to-Modbus-TCP bridge should work (Waveshare, USR-W610, etc.).

---

## Elfin EW11 configuration

**Serial Port Settings:**
- Baud Rate: `9600`
- Data Bit: `8`
- Stop Bit: `1`
- Parity: `None`
- Buffer Size: `1024`
- Gap Time: `100`

**Communication Settings:**
- Protocol: `TCP Server`
- Local Port: `502`

---

## Installation

### Via HACS (recommended)

1. Open **HACS → Integrations**
2. Click the three-dot menu → **Custom repositories**
3. Add `https://github.com/martijnve/adlar-heatpump`, category: **Integration**
4. Search for **Adlar Heatpump** and install
5. Restart Home Assistant

### Manual

Copy the `custom_components/adlar_heatpump/` folder into your HA `config/custom_components/` directory, then restart.

---

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Adlar Heatpump**
3. Enter:
   - **IP address** of your RS485-TCP gateway
   - **Port** (default `502`)
   - **Slave ID** (default `1`)
   - **Scan interval** in seconds (default `60`)

Scan interval, parameter read interval and expert mode can be changed later under **Configure**.

---

## Entities created

Every register in the [HHI Modbus developer reference v2.2](https://github.com/hhi/org.hhi.adlar-heatpump-modbus/blob/HEAD/docs/Dev%20support/adlar-modbus-developer-reference-v2.2.md#5-master-register-table-code-leading) becomes an entity, about 520 in total. Only the ones most people need are enabled by default (about 165); enable the rest under the device page. The register map lives in `custom_components/adlar_heatpump/registers.py`.

| # | Group | Registers | Entities | Enabled by default |
|---|---|---|---|---|
| 1 | Measurements | `0x0027`–`0x0028`, `0x0040`–`0x007D`, `0x0085` | Sensor | Temperatures, frequencies, valves, pump, flow, electrical, energy; not the 3-phase, zone and solar sensors or the code registers |
| 2 | Calculated | — | Sensor: Thermal Power, COP, Calculated Power (AC voltage × calibrated AC current), Refrigerant Type | Yes |
| 3 | Running status | `0x0000`–`0x0001` | Binary sensor per bit | Yes |
| 4 | Faults | `0x0002`–`0x0009` (+ System 2 at `0x000A`–`0x000E` on dual-compressor units) | Binary sensor per bit, device class *problem* | Yes (diagnostic) |
| 5 | Relay outputs, switch ports | `0x0019`–`0x001F` | Binary sensor per bit | No |
| 6 | User control | `0x0300`–`0x0319`, `0x0343`–`0x0344` | Climate, number (cooling / heating / hot water / floor setpoints, indoor and zone setpoints), select (mode, running mode, 4 curves), switch (ON/OFF). DC pump control and output: sensors, writable in expert mode | Setpoints, mode, curves, ON/OFF |
| 7 | Command coils | `0x1000`, `0x1001`, `0x1012`, `0x1013`, `0x1018`, `0x101A` | Switch: Powerful, Silent, Quick Heat, Force Defrost, Force Sterilization, Allow Water Return | Yes |
| 8 | Limits | `0x00FA`–`0x00FF` | Sensor (diagnostic) | Yes |
| 9 | Version info | `0x0360`–`0x0363` | Sensor (diagnostic) | Yes |
| 10 | Installer parameters P00–P262, L11–L36 | `0x0100`–`0x0206`, `0x0800`–`0x0819` | Sensor; number/select in expert mode | No |

Entity names and unique IDs of the upstream 1.4.x entities are unchanged, so existing dashboards and automations keep working. Two value changes when upgrading from upstream 1.4.x:

1. **Fan Running Speed** (`0x0041`) is reported in rpm, per the v2.2 register model, instead of Hz. Home Assistant raises a *units changed* repair for its long-term statistics once; resolve it under **Developer Tools → Statistics**.
2. **AC Input Current** (`0x0045`), and **Calculated Power** derived from it, go through the clamp calibration curve, so they read differently from upstream's raw ×0.1.

### Expert mode

**Settings → Devices & Services → Adlar Heatpump → Configure** has an *Expert mode* switch. With it on, the installer parameters become writable number/select entities (clamped to the documented range). With it off they are read-only sensors. DC pump control and output (`0x0343`/`0x0344`) are also writable only in expert mode: manual pump control stays in effect until set back to Auto, and a stopped pump with a running compressor can freeze the plate heat exchanger. Some parameters are never writable: P45 slave address, P114 compressors, P115 model, P119 refrigerant, P155 compressor code, P183 password, and any parameter without a documented range.

> Wrong values for protection, valve or frequency parameters can damage the heat pump. Only change a parameter when you know what it does.

Left out on purpose: the Unit Control bitmask `0x0330` (FC06 twin of the command coils, including drain, recovery and factory reset; its safe bits are the coil switches), the service-only forcing registers (`0x0331`–`0x033E`, `0x0345`), the coils for system drain, refrigerant recovery, factory reset and forced control, the legacy curve pair `0x030C`/`0x030D`, and undocumented addresses.

---

## Technical notes

### Polling
- Registers are read in blocks of up to 32 contiguous addresses (FC03) and coils in contiguous FC01 blocks, so a poll takes about 13 requests instead of about 45. Coils are skipped on controllers with protocol version below 130.
- A request that times out or is rejected only makes that block unknown for this poll; the entities go unavailable only when the gateway can't be reached or nothing answers.
- Measurements, status and controls are read every scan interval (default 60 s). Parameters, limits and version info are read every *parameter read interval* (default 600 s); a value you write shows immediately.
- If the controller rejects a block, its registers are read one by one. Addresses it doesn't implement are skipped from then on.

### Scaling
- Temperatures follow the refrigerant type in P119 (`0x0177`): whole degrees for R32/R410A and tenths for R290. This applies to reads and to setpoint writes.
- Probes that aren't fitted report −40 °C or lower and show as *unknown*. Zone 1 Mixing Temp (`0x007C`) reports 0 °C instead; since that is also a valid reading, it is shown as is.
- AC input current (`0x0045`) goes through the non-linear clamp calibration curve from the reference.

### Modbus addressing
Addresses are PDU addresses as sent on the wire (`0x004A` = 74). No offset is applied.

---

## Development

- `devbox run test` runs the tests (creates `.venv` from `requirements_test.txt` on first use); `devbox run lint` runs ruff.
- `docker compose -f dev/docker-compose.yml up -d` starts a Home Assistant on http://localhost:8124 with this integration bind-mounted from the checkout, plus a Modbus TCP simulator (`dev/simulator.py`) serving the reference snapshot. Add the integration with host `modbus-sim`, port `502`. Restart the HA container after a code change.

---

## Disclaimer

This integration is community-developed and not affiliated with Adlår. Use at your own risk. Incorrect writes to control registers could affect heat pump operation. Always verify setpoints before applying changes.
