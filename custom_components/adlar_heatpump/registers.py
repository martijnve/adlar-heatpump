"""Register map for the Adlar Castra / Aurora II (SolarEast/HBG controller).

Transcribed from the HHI Modbus developer reference v2.2
(hhi/org.hhi.adlar-heatpump-modbus, docs/Dev support/adlar-modbus-developer-reference-v2.2.md),
which is generated from lib/modbus/adlar-modbus-registers.ts.

Left out on purpose: the 0x0330 Unit Control bitmask (FC06 twin of the command coils, including
drain, refrigerant recovery and factory reset; its safe bits are exposed as coils), the
service-only forcing registers (0x0331-0x0345 except the DC pump pair),
the dangerous command coils (drain, refrigerant recovery, factory reset, forced control),
the legacy curve pair 0x030C/0x030D (protocol < 130) and undocumented addresses.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise

# Register groups: decide platform, poll tier and writability
SENSOR = "sensor"     # read-only measurements, polled every scan
LIMIT = "limit"       # read-only derived limits, slow poll
CONTROL = "control"   # user controls, writable, polled every scan
PARAM = "param"       # P/L installer parameters, slow poll, writable only in expert mode
VERSION = "version"   # firmware/product info, slow poll

FAST_GROUPS = (SENSOR, CONTROL)

ENABLE_DISABLE = {0: "enable", 1: "disable"}
CURVE_OPTIONS = {
    0: "Off", 1: "H1", 2: "H2", 3: "H3", 4: "H4", 5: "H5", 6: "H6", 7: "H7", 8: "H8",
    11: "L1", 12: "L2", 13: "L3", 14: "L4", 15: "L5", 16: "L6", 17: "L7", 18: "L8",
}


@dataclass(frozen=True)
class R:
    """One 16-bit holding register."""

    addr: int
    name: str
    group: str
    unit: str | None = None
    scale: float = 1
    temp: bool = False            # scaled by refrigerant type (P119) instead of `scale`
    min: float | None = None
    max: float | None = None
    options: dict[int, str] | None = None
    signed: bool = True
    enabled: bool = True          # entity enabled by default
    protected: bool = False       # never writable, not even in expert mode
    expert: bool = False          # CONTROL register writable only in expert mode
    delta: bool = False           # °C difference/offset, not an absolute temperature

    @property
    def fast(self) -> bool:
        return self.group in FAST_GROUPS


REGISTERS: list[R] = [
    # --- Status ---
    R(0x0027, "Compressor Target Frequency", SENSOR, unit="Hz"),
    R(0x0028, "Compressor Target Frequency 2", SENSOR, unit="Hz", enabled=False),
    # --- Sensors ---
    R(0x0040, 'Compressor Running Frequency', SENSOR, unit='Hz'),
    R(0x0041, 'Fan Running Speed', SENSOR, unit='RPM'),
    R(0x0042, 'EEV Open Step', SENSOR, unit='P'),
    R(0x0043, 'EVI Valve Open Step', SENSOR, unit='P'),
    R(0x0044, 'AC Input Voltage', SENSOR, unit='V', scale=0.99),
    R(0x0045, 'AC Input Current', SENSOR, unit='A', scale=0.1),
    R(0x0046, 'Compressor Phase Current', SENSOR, unit='A', scale=0.1),
    R(0x0047, 'Compressor IPM Temp', SENSOR, unit='°C', temp=True),
    R(0x0048, 'High Pressure Saturation Temp', SENSOR, unit='°C', temp=True),
    R(0x0049, 'Low Pressure Saturation Temp', SENSOR, unit='°C', temp=True),
    R(0x004A, 'Ambient Temp T1', SENSOR, unit='°C', temp=True),
    R(0x004B, 'Outer Coil Temp T2', SENSOR, unit='°C', temp=True),
    R(0x004C, 'Inner Coil Temp T3', SENSOR, unit='°C', temp=True),
    R(0x004D, 'Suction Temp T4', SENSOR, unit='°C', temp=True),
    R(0x004E, 'Exhaust Temp T5', SENSOR, unit='°C', temp=True),
    R(0x004F, 'Water Inlet Temp T6', SENSOR, unit='°C', temp=True),
    R(0x0050, 'Water Outlet Temp T7', SENSOR, unit='°C', temp=True),
    R(0x0051, 'Economizer Inlet Temp T8', SENSOR, unit='°C', temp=True),
    R(0x0052, 'Economizer Outlet Temp T9', SENSOR, unit='°C', temp=True),
    R(0x0053, 'Device Tooling No', SENSOR, enabled=False),
    R(0x0054, 'DHW Tank Temp', SENSOR, unit='°C', temp=True),
    R(0x0055, 'Plate HX Exhaust Temp', SENSOR, unit='°C', temp=True),
    R(0x0056, 'Drive Manufacturer Code', SENSOR, enabled=False),
    R(0x0057, 'Water Pump Speed PWM', SENSOR, unit='%'),
    R(0x0058, 'Water Flow', SENSOR, unit='L/min'),
    R(0x0059, 'DHW Return Water Temp', SENSOR, unit='°C', temp=True),
    R(0x005A, 'Unit Input Voltage', SENSOR, unit='V'),
    R(0x005B, 'Unit Input Current', SENSOR, unit='A', scale=0.01),
    R(0x005C, 'Unit Input Power', SENSOR, unit='kW', scale=0.01),
    R(0x005D, 'Unit Power Consumption', SENSOR, unit='kWh', signed=False),
    R(0x0072, 'Solar Water Heater Temp', SENSOR, unit='°C', temp=True, enabled=False),
    R(0x0073, 'Zone 2 Temp', SENSOR, unit='°C', temp=True, enabled=False),
    R(0x0074, 'Buffer Tank Temp', SENSOR, unit='°C', temp=True, enabled=False),
    R(0x0075, 'Total Water Outlet Temp', SENSOR, unit='°C', temp=True),
    R(0x0076, 'B Phase Input Voltage', SENSOR, unit='V', enabled=False),
    R(0x0077, 'B Phase Input Current', SENSOR, unit='A', scale=0.01, enabled=False),
    R(0x0078, 'C Phase Input Voltage', SENSOR, unit='V', enabled=False),
    R(0x0079, 'C Phase Input Current', SENSOR, unit='A', scale=0.01, enabled=False),
    R(0x007A, 'Smart Grid Status', SENSOR),
    R(0x007B, 'Zone 2 Mixing Valve Opening', SENSOR, unit='%', enabled=False),
    R(0x007C, 'Zone 1 Mixing Temp', SENSOR, unit='°C', temp=True, enabled=False),
    R(0x007D, 'Zone 1 Mixing Valve Opening', SENSOR, unit='%', enabled=False),
    # Not in the v2.2 model; kept from upstream
    R(0x0085, 'DC Bus Inverter Voltage', SENSOR, unit='V', scale=0.1),
    R(0x00FA, 'Heating Temp Upper Limit', LIMIT, unit='°C', temp=True),
    R(0x00FB, 'Heating Temp Lower Limit', LIMIT, unit='°C', temp=True),
    R(0x00FC, 'Hot Water Temp Upper Limit', LIMIT, unit='°C', temp=True),
    R(0x00FD, 'Hot Water Temp Lower Limit', LIMIT, unit='°C', temp=True),
    R(0x00FE, 'Cooling Temp Upper Limit', LIMIT, unit='°C', temp=True),
    R(0x00FF, 'Cooling Temp Lower Limit', LIMIT, unit='°C', temp=True),
    R(0x0100, 'P00 T1 Ambient temp sensor', PARAM, min=0, max=1, options={0: 'enable', 1: 'disable'}),
    R(0x0101, 'P01 High voltage switch', PARAM, min=0, max=1, options={0: 'enable', 1: 'disable'}),
    R(0x0102, 'P02 Low pressure switch', PARAM, min=0, max=1, options={0: 'enable', 1: 'disable'}),
    R(0x0103, 'P03 Water flow switch', PARAM, min=0, max=1, options={0: 'enable', 1: 'disable'}),
    R(0x0104, 'P04 Thermal overload protection', PARAM, min=0, max=1, options={0: 'enable', 1: 'disable'}),
    R(0x0105, 'P05 Linkage switch (host)', PARAM, min=0, max=3, options={0: 'enable', 1: 'disable', 2: 'thermostatic', 3: 'heating thermostat'}),
    R(0x0106, 'P06 Fan type', PARAM, min=0, max=3, options={0: 'AC', 1: 'DC', 2: 'EC', 3: '3 (undocumented)'}),
    R(0x0107, 'P07 High voltage lock', PARAM, min=0, max=1, options={0: '3 locks', 1: 'no lock'}),
    R(0x0108, 'P08 Low voltage lock', PARAM, min=0, max=1, options={0: '3 locks', 1: 'no lock'}),
    R(0x0109, 'P09 Exhaust lock', PARAM, min=0, max=1, options={0: '3 locks', 1: 'no lock'}),
    R(0x010A, 'P10 Water flow lock', PARAM, min=0, max=1, options={0: '3 locks', 1: 'no lock'}),
    R(0x010B, 'P11 High pressure protection value', PARAM, unit='°C', min=40, max=150),
    R(0x010C, 'P12 High pressure freq limit', PARAM, unit='°C', min=40, max=150),
    R(0x010D, 'P13 Low pressure protection value', PARAM, unit='°C', min=-50, max=-10),
    R(0x010E, 'P14 Low pressure freq limit', PARAM, unit='°C', min=-50, max=-10),
    R(0x010F, 'P15 Exhaust temp protection', PARAM, unit='°C', min=100, max=130),
    R(0x0110, 'P16 Exhaust temp freq limit', PARAM, unit='°C', min=90, max=120),
    R(0x0111, 'P17 Cooling fan speed-up value', PARAM, unit='°C', min=0, max=60),
    R(0x0112, 'P18 Cooling fan speed-down value', PARAM, unit='°C', min=0, max=60),
    R(0x0113, 'P19 Heating fan speed-down value', PARAM, unit='°C', min=0, max=60),
    R(0x0114, 'P20 Heating fan speed-up value', PARAM, unit='°C', min=0, max=60),
    R(0x0115, 'P21 Low temp unit prohibit start', PARAM, unit='°C', min=-40, max=-10),
    R(0x0116, 'P22 E-heating start ambient', PARAM, unit='°C', min=-15, max=40),
    R(0x0117, 'P23 Excessive temp diff alarm', PARAM, unit='°C', min=10, max=30, delta=True),
    R(0x0118, 'P24 Return water compensation', PARAM, unit='°C', min=-10, max=10, delta=True),
    R(0x0119, 'P25 Outlet water compensation', PARAM, unit='°C', min=-10, max=10, delta=True),
    R(0x011A, 'P26 H&C Hysteresis return differential value', PARAM, unit='°C', min=0, max=10, delta=True),
    R(0x011B, 'P27 Floor heating return differential value', PARAM, unit='°C', min=0, max=10, delta=True),
    R(0x011C, 'P28 Pump mode at shutdown', PARAM, min=0, max=4, options={0: 'keep running', 1: 'stop', 2: 'cooling only', 3: 'AC/heating only', 4: 'floor only'}),
    R(0x011D, 'P29 Antifreeze pump running time', PARAM, unit='min', min=0, max=10),
    R(0x011E, 'P30 Defrost mode', PARAM, min=0, max=3, options={0: 'smart', 1: 'timing', 2: 'fast', 3: 'dew point'}),
    R(0x011F, 'P31 Defrost accumulated threshold', PARAM, min=0, max=120),
    R(0x0120, 'P32 Defrost entry coil temp', PARAM, unit='°C', min=-30, max=0),
    R(0x0121, 'P33 Defrost entry temp diff 1', PARAM, unit='°C', min=0, max=20, delta=True),
    R(0x0122, 'P34 Defrost entry temp diff 2', PARAM, unit='°C', min=0, max=20, delta=True),
    R(0x0123, 'P35 Max defrost time', PARAM, unit='min', min=0, max=30),
    R(0x0124, 'P36 Defrost exit coil temp', PARAM, unit='°C', min=0, max=30),
    R(0x0125, 'P37 Shutdown mode (aka "Darwin")', PARAM, min=0, max=2, options={0: 'Smart (unit decides)', 1: 'Direct/Darwin (immediate off at target)', 2: 'Refrig Smart'}),
    R(0x0126, 'P38 Heating main valve initial opening constant', PARAM, min=-999, max=999),
    R(0x0127, 'P39 Pressure sensor settings', PARAM, min=0, max=1, options={0: 'enable', 1: 'disable'}),
    R(0x0128, 'P40 EEV cooling target superheat correction', PARAM, unit='°C', min=-5, max=10, delta=True),
    R(0x0129, 'P41 EEV heating HP freq limit correction', PARAM, unit='°C', min=-10, max=10, delta=True),
    R(0x012A, 'P42 EEV heating target superheat correction', PARAM, unit='°C', min=-5, max=10, delta=True),
    R(0x012B, 'P43 MV switch setting', PARAM, min=0, max=1, options={0: 'disable', 1: 'enable'}),
    R(0x012C, 'P44 Water flow switch failure detect', PARAM, min=0, max=1, options={0: 'enable', 1: 'disable'}),
    R(0x012D, 'P45 Modbus slave address', PARAM, min=1, max=16, protected=True),
    R(0x012E, 'P46 EVI liquid injection valve return diff', PARAM, unit='°C', min=0, max=15, delta=True),
    R(0x012F, 'P47 EVI target superheat constant', PARAM, min=0, max=12),
    R(0x0130, 'P48 Enable DHW tank temp sensor', PARAM, min=0, max=1, options={0: 'disable', 1: 'enable'}),
    R(0x0131, 'P49 Hot water freq running percentage', PARAM, unit='%', min=0, max=100),  # doc range excludes the reference unit's value (§3)
    R(0x0132, 'P50 Cooling target freq constant A', PARAM, min=-100, max=100),
    R(0x0133, 'P51 Cooling min freq', PARAM, unit='Hz', min=15, max=60),
    R(0x0134, 'P52 Cooling target freq upper', PARAM, unit='Hz', min=40, max=120),
    R(0x0135, 'P53 Cooling target freq lower', PARAM, unit='Hz', min=15, max=120),
    R(0x0136, 'P54 Heating target freq constant B', PARAM, min=-100, max=100),
    R(0x0137, 'P55 Heating target freq upper', PARAM, unit='Hz', min=50, max=120),
    R(0x0138, 'P56 Heating target freq lower', PARAM, unit='Hz', min=20, max=120),
    R(0x0139, 'P57 Heating min freq (ambient > 0°C)', PARAM, unit='Hz', min=15, max=60),
    R(0x013A, 'P58 Heating min freq (-10°C ≤ ambient < 0°C)', PARAM, unit='Hz', min=15, max=60),
    R(0x013B, 'P59 Heating min freq (ambient < -10°C)', PARAM, unit='Hz', min=15, max=60),
    R(0x013C, 'P60 Hot water target freq constant', PARAM, min=-100, max=100),
    R(0x013D, 'P61 Hot water target freq upper', PARAM, unit='Hz', min=50, max=120),
    R(0x013E, 'P62 Hot water target freq lower', PARAM, unit='Hz', min=15, max=120),
    R(0x013F, 'P63 Hot water min freq (ambient > 0°C)', PARAM, unit='Hz', min=15, max=60),
    R(0x0140, 'P64 Hot water min freq (-10°C ≤ ambient < 0°C)', PARAM, unit='Hz', min=15, max=60),
    R(0x0141, 'P65 Hot water min freq (ambient < -10°C)', PARAM, unit='Hz', min=15, max=60),
    R(0x0142, 'P66 DC fan initial freq', PARAM, unit='Hz', min=20, max=60),
    R(0x0143, 'P67 DC fan heating min freq', PARAM, unit='Hz', min=20, max=60),
    R(0x0144, 'P68 DC fan heating max freq', PARAM, unit='Hz', min=20, max=80),
    R(0x0145, 'P69 DC fan cooling min freq', PARAM, unit='Hz', min=20, max=60),
    R(0x0146, 'P70 DC fan cooling max freq', PARAM, unit='Hz', min=20, max=80),
    R(0x0147, 'P71 EEV enthalpy control on frequency', PARAM, unit='Hz', min=20, max=80),
    R(0x0148, 'P72 EEV enthalpy stop increase frequency', PARAM, unit='Hz', min=20, max=80),
    R(0x0149, 'P73 EEV cooling main valve opening 1', PARAM, unit='P', min=20, max=480),
    R(0x014A, 'P74 EEV cooling main valve opening 2', PARAM, unit='P', min=20, max=480),
    R(0x014B, 'P75 EEV cooling main valve opening 3', PARAM, unit='P', min=20, max=480),
    R(0x014C, 'P76 EEV cooling main valve min opening', PARAM, unit='P', min=0, max=300),
    R(0x014D, 'P77 EEV heating main valve min opening', PARAM, unit='P', min=0, max=300),
    R(0x014E, 'P78 EEV main valve max opening', PARAM, unit='P', min=100, max=500),
    R(0x014F, 'P79 EEV main valve initial opening const c', PARAM, min=20, max=300),
    R(0x0150, 'P80 EEV main valve initial opening coeff a', PARAM, min=-999, max=999),
    R(0x0151, 'P81 EEV main valve initial opening coeff b', PARAM, min=-999, max=999),
    R(0x0152, 'P82 EEV aux valve max opening', PARAM, unit='P', min=100, max=500),
    R(0x0153, 'P83 EEV aux valve min opening', PARAM, unit='P', min=30, max=300),  # doc range excludes the reference unit's value (§3)
    R(0x0154, 'P84 EEV main valve regulation period', PARAM, unit='s', min=10, max=120),
    R(0x0155, 'P85 EEV aux valve initial opening const c', PARAM, min=-200, max=900),
    R(0x0156, 'P86 EEV aux valve initial opening coeff a', PARAM, min=-999, max=999),
    R(0x0157, 'P87 EEV aux valve initial opening coeff b', PARAM, min=-999, max=999),
    R(0x0158, 'P88 Silent mode compressor freq', PARAM, unit='Hz', min=20, max=70),
    R(0x0159, 'P89 Silent mode fan freq', PARAM, unit='Hz', min=20, max=60),
    R(0x015A, 'P90 EVI entry ambient temperature', PARAM, unit='°C', min=0, max=45),
    R(0x015B, 'P91 EVI forbid entry time', PARAM, unit='min', min=0, max=30),
    R(0x015C, 'P92 EVI entry temperature difference', PARAM, unit='°C', min=0, max=60, delta=True),
    R(0x015D, 'P93 EVI compressor run time to enter', PARAM, unit='min', min=0, max=20),
    R(0x015E, 'P94 EVI aux valve adjustment cycle', PARAM, unit='s', min=10, max=120),
    R(0x015F, 'P95 Network pump mode', PARAM, min=0, max=1, options={0: 'shared', 1: 'independent'}),
    R(0x0160, 'P96 DHW differential value', PARAM, unit='°C', min=0, max=10, delta=True),
    R(0x0161, 'P97 Tank temperature auto compensation', PARAM, min=0, max=1, options={0: 'enable', 1: 'disable'}),
    R(0x0162, 'P98 Tank temperature manual compensation', PARAM, unit='°C', min=-10, max=10, delta=True),
    R(0x0163, 'P99 Pump speed regulation temp diff', PARAM, unit='°C', min=2, max=10, delta=True),
    R(0x0164, 'P100 PWM pump minimum speed', PARAM, unit='%', min=20, max=80),
    R(0x0165, 'P101 Pump control mode', PARAM, min=0, max=1, options={0: 'AC(on/off)', 1: 'DC(PWM)'}),
    R(0x0166, 'P102 Four-way valve control mode', PARAM, min=0, max=1, options={0: 'cooling power on', 1: 'heating power on'}),
    R(0x0167, 'P103 Mode switch min run time', PARAM, unit='min', min=0, max=10),
    R(0x0168, 'P104 Mode switch operating frequency %', PARAM, unit='%', min=20, max=100),
    R(0x0169, 'P105 Cooling ambient temp limit', PARAM, unit='°C', min=10, max=60),
    R(0x016A, 'P106 Heating ambient temp limit', PARAM, unit='°C', min=10, max=60),
    R(0x016B, 'P107 Hot water ambient temp limit', PARAM, unit='°C', min=10, max=60),
    R(0x016C, 'P108 Hot water set temp upper', PARAM, unit='°C', min=30, max=80),
    R(0x016D, 'P109 Hot water set temp lowest', PARAM, unit='°C', min=10, max=30),
    R(0x016E, 'P110 Heating set temp upper', PARAM, unit='°C', min=30, max=80),
    R(0x016F, 'P111 Heating set temp lowest', PARAM, unit='°C', min=15, max=30),
    R(0x0170, 'P112 Cooling set temp upper', PARAM, unit='°C', min=20, max=40),
    R(0x0171, 'P113 Cooling set temp lowest', PARAM, unit='°C', min=5, max=20),
    R(0x0172, 'P114 Nr of compressors', PARAM, min=1, max=2, options={1: 'single', 2: 'pair'}, protected=True),
    R(0x0173, 'P115 Model selection', PARAM, min=0, max=5, protected=True),
    R(0x0174, 'P116 Temp control mode', PARAM, min=0, max=1, options={0: 'inlet T6 (return water)', 1: 'outlet T7 (discharge)'}),
    R(0x0175, 'P117 Antifreeze ambient temp', PARAM, unit='°C', min=0, max=10),
    R(0x0176, 'P118 Antifreeze outlet water', PARAM, unit='°C', min=0, max=20),
    R(0x0177, 'P119 Refrigerant type', PARAM, min=1, max=3, options={1: 'R410A', 2: 'R32', 3: 'R290'}, protected=True),
    R(0x0178, 'P120 Anti-condensation function', PARAM, min=0, max=1, options={0: 'enable', 1: 'disable'}),
    R(0x0179, 'P121 Heating freq shield zone 1 low', PARAM, unit='Hz', min=0, max=120),
    R(0x017A, 'P122 Heating freq shield zone 1 high', PARAM, unit='Hz', min=0, max=120),
    R(0x017B, 'P123 Heating freq shield zone 2 low', PARAM, unit='Hz', min=0, max=120),
    R(0x017C, 'P124 Heating freq shield zone 2 high', PARAM, unit='Hz', min=0, max=120),
    R(0x017D, 'P125 Heating freq shield zone 3 low', PARAM, unit='Hz', min=0, max=120),
    R(0x017E, 'P126 Heating freq shield zone 3 high', PARAM, unit='Hz', min=0, max=120),
    R(0x017F, 'P127 Cooling freq shield zone 1 low', PARAM, unit='Hz', min=0, max=120),
    R(0x0180, 'P128 Cooling freq shield zone 1 high', PARAM, unit='Hz', min=0, max=120),
    R(0x0181, 'P129 Cooling freq shield zone 2 low', PARAM, unit='Hz', min=0, max=120),
    R(0x0182, 'P130 Cooling freq shield zone 2 high', PARAM, unit='Hz', min=0, max=120),
    R(0x0183, 'P131 Cooling freq shield zone 3 low', PARAM, unit='Hz', min=0, max=120),
    R(0x0184, 'P132 Cooling freq shield zone 3 high', PARAM, unit='Hz', min=0, max=120),
    R(0x0185, 'P133 Fan module', PARAM, min=0, max=1, options={0: 'integral module', 1: 'individual module'}),
    R(0x0186, 'P134 Low water flow protection', PARAM, unit='L/min', min=0, max=100),
    R(0x0187, 'P135 Anti-condensation start temp diff', PARAM, unit='°C', min=0, max=50, delta=True),
    R(0x0188, 'P136 Throttle bypass valve open ambient temp', PARAM, unit='°C', min=-20, max=50),
    R(0x0189, 'P137 Throttle bypass delay compressor', PARAM, unit='s', min=0, max=999),
    R(0x018A, 'P138 Defrost compressor frequency', PARAM, unit='Hz', min=40, max=120),
    R(0x018B, 'P139 Buffer tank electric heater', PARAM, min=0, max=2, options={0: 'enable', 1: 'disable', 2: 'AHS (Auxiliary Heat Source)'}),
    R(0x018C, 'P140 DHW electric heater', PARAM, min=0, max=2, options={0: 'enable', 1: 'disable', 2: 'AHS'}),
    R(0x018D, 'P141 Dew point defrost duration', PARAM, unit='min', min=0, max=60),
    R(0x018E, 'P142 Dew point defrost constant', PARAM, min=0, max=60),
    R(0x018F, 'P143 Water temp to enter defrost', PARAM, unit='°C', min=0, max=60),
    R(0x0190, 'P144 Ambient temp to enter defrost', PARAM, unit='°C', min=-20, max=30),
    R(0x0191, 'P145 Outlet water antifreeze protection', PARAM, unit='°C', min=-30, max=10),  # doc range excludes the reference unit's value (§3)
    R(0x0192, 'P146 Pump PWM range setting', PARAM, unit='L/min', min=0, max=100),
    R(0x0193, 'P147 Cooling antifreeze mode', PARAM, min=0, max=2, options={0: 'low pressure', 1: 'temp', 2: 'low pressure + temp'}),
    R(0x0194, 'P148 Cooling antifreeze temperature', PARAM, unit='°C', min=-30, max=10),
    R(0x0195, 'P149 Outlet water high limit temperature', PARAM, unit='°C', min=40, max=80),
    R(0x0196, 'P150 Secondary heating pump select', PARAM, min=0, max=3, options={0: 'power on run', 1: 'power on', 2: 'linkage demand switch', 3: 'temperature control'}),
    R(0x0197, 'P151 Return diff - hot water heat source', PARAM, unit='°C', min=0, max=40, delta=True),
    R(0x0198, 'P152 Return diff - heating heat source', PARAM, unit='°C', min=0, max=40, delta=True),
    R(0x0199, 'P153 DHW heat source upper temp', PARAM, unit='°C', min=15, max=80),
    R(0x019A, 'P154 Heating heat source upper temp', PARAM, unit='°C', min=15, max=80),
    R(0x019B, 'P155 Compressor code (reserved)', PARAM, min=0, max=9999, protected=True),
    R(0x019C, 'P156 Aux EEV selection', PARAM, min=0, max=1, options={0: 'enable', 1: 'disable'}),
    R(0x019D, 'P157 Aux EEV temp diff to reduce', PARAM, unit='°C', min=0, max=99, delta=True),
    R(0x019E, 'P158 Heating limit water temp start ambient', PARAM, unit='°C', min=-45, max=30),
    R(0x019F, 'P159 Limit temperature constant', PARAM, min=0, max=150),
    R(0x01A0, 'P160 Limit temperature coefficient', PARAM, min=-500, max=500),
    R(0x01A1, 'P161 Aux pump selection', PARAM, min=0, max=4, options={0: 'DHW', 1: 'AC', 2: 'floor', 3: 'AC/floor', 4: 'all'}),
    R(0x01A2, 'P162 Antifreeze DHW pipe interval', PARAM, unit='min', min=0, max=360),
    R(0x01A3, 'P163 Min pump speed feedback', PARAM, unit='%', min=0, max=70),
    R(0x01A4, 'P164 Energy level control', PARAM, min=0, max=3, options={0: 'all enable', 1: 'E-heat disable', 2: 'compressor disable', 3: 'all disable'}),
    R(0x01A5, 'P165 Load shedding return difference', PARAM, unit='°C', min=1, max=15, delta=True),
    R(0x01A6, 'P166 Load shedding hysteresis', PARAM, unit='°C', min=1, max=15, delta=True),
    R(0x01A7, 'P167 Load shedding emergency stop return diff', PARAM, unit='°C', min=1, max=15, delta=True),
    R(0x01A8, 'P168 Load shedding hot water start ratio', PARAM, unit='%', min=1, max=100),
    R(0x01A9, 'P169 Load shedding non-hot water start ratio', PARAM, unit='%', min=1, max=100),
    R(0x01AA, 'P170 Load shedding loading cycle', PARAM, unit='min', min=3, max=60),
    R(0x01AB, 'P171 Load shedding shield low voltage ambient', PARAM, unit='°C', min=-50, max=0),
    R(0x01AC, 'P172 DC fan target frequency constant c', PARAM, unit='Hz', min=40, max=70),
    R(0x01AD, 'P173 Heating fan target frequency lower limit', PARAM, unit='Hz', min=20, max=65),
    R(0x01AE, 'P174 Defrost valve opening', PARAM, unit='P', min=0, max=480),
    R(0x01AF, 'P175 Constant temp operation cycle', PARAM, unit='min', min=0, max=360),
    R(0x01B0, 'P176 Minimum defrost time', PARAM, unit='s', min=0, max=999),
    R(0x01B1, 'P177 Defrost segmented water temperature', PARAM, unit='°C', min=0, max=80),
    R(0x01B2, 'P178 High water temp defrost frequency', PARAM, unit='Hz', min=40, max=120),
    R(0x01B3, 'P179 Strong mode frequency increase', PARAM, unit='Hz', min=0, max=40),
    R(0x01B4, 'P180 Powerful mode frequency cap', PARAM, unit='Hz', min=0, max=40),
    R(0x01B5, 'P181 Defrost selection - evaporate side', PARAM, min=0, max=2, options={0: 'current mode', 1: 'heating', 2: 'DHW'}),
    R(0x01B6, 'P182 Pipe electric heating option', PARAM, min=0, max=3, options={0: '3kW+6kW', 1: '3kW', 2: '6kW', 3: 'disabled'}),
    R(0x01B7, 'P183 Parameter password', PARAM, min=0, max=9999, protected=True),
    R(0x01B8, 'P184 Working cond 35D compressor frequency', PARAM, unit='Hz', min=0, max=120),
    R(0x01B9, 'P185 Working cond 35C compressor frequency', PARAM, unit='Hz', min=0, max=120),
    R(0x01BA, 'P186 Working cond 35B compressor frequency', PARAM, unit='Hz', min=0, max=120),
    R(0x01BB, 'P187 Working cond 35A compressor frequency', PARAM, unit='Hz', min=0, max=120),
    R(0x01BC, 'P188 Working cond 35E compressor frequency', PARAM, unit='Hz', min=0, max=120),
    R(0x01BD, 'P189 Working cond 55D compressor frequency', PARAM, unit='Hz', min=0, max=120),
    R(0x01BE, 'P190 Working cond 55C compressor frequency', PARAM, unit='Hz', min=0, max=120),
    R(0x01BF, 'P191 Working cond 55B compressor frequency', PARAM, unit='Hz', min=0, max=120),
    R(0x01C0, 'P192 Working cond 55A compressor frequency', PARAM, unit='Hz', min=0, max=120),
    R(0x01C1, 'P193 Working cond 55E compressor frequency', PARAM, unit='Hz', min=0, max=120),
    R(0x01C2, 'P194 Working cond 35D fan frequency', PARAM, unit='Hz', min=0, max=60),
    R(0x01C3, 'P195 Working cond 35C fan frequency', PARAM, unit='Hz', min=0, max=60),
    R(0x01C4, 'P196 Working cond 35B fan frequency', PARAM, unit='Hz', min=0, max=60),
    R(0x01C5, 'P197 Working cond 35A fan frequency', PARAM, unit='Hz', min=0, max=60),
    R(0x01C6, 'P198 Working cond 35E fan frequency', PARAM, unit='Hz', min=0, max=60),
    R(0x01C7, 'P199 Working cond 55D fan frequency', PARAM, unit='Hz', min=0, max=60),
    R(0x01C8, 'P200 Working cond 55C fan frequency', PARAM, unit='Hz', min=0, max=60),
    R(0x01C9, 'P201 Working cond 55B fan frequency', PARAM, unit='Hz', min=0, max=60),
    R(0x01CA, 'P202 Working cond 55A fan frequency', PARAM, unit='Hz', min=0, max=60),
    R(0x01CB, 'P203 Working cond 55E fan frequency', PARAM, unit='Hz', min=0, max=60),
    R(0x01CC, 'P204 Working cond 35D main valve superheat', PARAM, unit='°C', min=-10, max=10, delta=True),
    R(0x01CD, 'P205 Working cond 35C main valve superheat', PARAM, unit='°C', min=-10, max=10, delta=True),
    R(0x01CE, 'P206 Working cond 35B main valve superheat', PARAM, unit='°C', min=-10, max=10, delta=True),
    R(0x01CF, 'P207 Working cond 35A main valve superheat', PARAM, unit='°C', min=-10, max=10, delta=True),
    R(0x01D0, 'P208 Working cond 35E main valve superheat', PARAM, unit='°C', min=-10, max=10, delta=True),
    R(0x01D1, 'P209 Working cond 55D main valve superheat', PARAM, unit='°C', min=-10, max=10, delta=True),
    R(0x01D2, 'P210 Working cond 55C main valve superheat', PARAM, unit='°C', min=-10, max=10, delta=True),
    R(0x01D3, 'P211 Working cond 55B main valve superheat', PARAM, unit='°C', min=-10, max=10, delta=True),
    R(0x01D4, 'P212 Working cond 55A main valve superheat', PARAM, unit='°C', min=-10, max=10, delta=True),
    R(0x01D5, 'P213 Working cond 55E main valve superheat', PARAM, unit='°C', min=-10, max=10, delta=True),
    R(0x01D6, 'P214 Working cond 35D main valve opening', PARAM, unit='P', min=0, max=500),
    R(0x01D7, 'P215 Working cond 35C main valve opening', PARAM, unit='P', min=0, max=500),
    R(0x01D8, 'P216 Working cond 35B main valve opening', PARAM, unit='P', min=0, max=500),
    R(0x01D9, 'P217 Working cond 35A main valve opening', PARAM, unit='P', min=0, max=500),
    R(0x01DA, 'P218 Working cond 35E main valve opening', PARAM, unit='P', min=0, max=500),
    R(0x01DB, 'P219 Working cond 55D main valve opening', PARAM, unit='P', min=0, max=500),
    R(0x01DC, 'P220 Working cond 55C main valve opening', PARAM, unit='P', min=0, max=500),
    R(0x01DD, 'P221 Working cond 55B main valve opening', PARAM, unit='P', min=0, max=500),
    R(0x01DE, 'P222 Working cond 55A main valve opening', PARAM, unit='P', min=0, max=500),
    R(0x01DF, 'P223 Working cond 55E main valve opening', PARAM, unit='P', min=0, max=500),
    R(0x01E0, 'P224 Working cond 35D aux valve superheat', PARAM, unit='°C', min=-10, max=10, delta=True),
    R(0x01E1, 'P225 Working cond 35C aux valve superheat', PARAM, unit='°C', min=-10, max=10, delta=True),
    R(0x01E2, 'P226 Working cond 35B aux valve superheat', PARAM, unit='°C', min=-10, max=10, delta=True),
    R(0x01E3, 'P227 Working cond 35A aux valve superheat', PARAM, unit='°C', min=-10, max=10, delta=True),
    R(0x01E4, 'P228 Working cond 35E aux valve superheat', PARAM, unit='°C', min=-10, max=10, delta=True),
    R(0x01E5, 'P229 Working cond 55D aux valve superheat', PARAM, unit='°C', min=-10, max=10, delta=True),
    R(0x01E6, 'P230 Working cond 55C aux valve superheat', PARAM, unit='°C', min=-10, max=10, delta=True),
    R(0x01E7, 'P231 Working cond 55B aux valve superheat', PARAM, unit='°C', min=-10, max=10, delta=True),
    R(0x01E8, 'P232 Working cond 55A aux valve superheat', PARAM, unit='°C', min=-10, max=10, delta=True),
    R(0x01E9, 'P233 Working cond 55E aux valve superheat', PARAM, unit='°C', min=-10, max=10, delta=True),
    R(0x01EA, 'P234 Working cond 35D aux valve opening', PARAM, unit='P', min=0, max=500),
    R(0x01EB, 'P235 Working cond 35C aux valve opening', PARAM, unit='P', min=0, max=500),
    R(0x01EC, 'P236 Working cond 35B aux valve opening', PARAM, unit='P', min=0, max=500),
    R(0x01ED, 'P237 Working cond 35A aux valve opening', PARAM, unit='P', min=0, max=500),
    R(0x01EE, 'P238 Working cond 35E aux valve opening', PARAM, unit='P', min=0, max=500),
    R(0x01EF, 'P239 Working cond 55D aux valve opening', PARAM, unit='P', min=0, max=500),
    R(0x01F0, 'P240 Working cond 55C aux valve opening', PARAM, unit='P', min=0, max=500),
    R(0x01F1, 'P241 Working cond 55B aux valve opening', PARAM, unit='P', min=0, max=500),
    R(0x01F2, 'P242 Working cond 55A aux valve opening', PARAM, unit='P', min=0, max=500),
    R(0x01F3, 'P243 Working cond 55E aux valve opening', PARAM, unit='P', min=0, max=500),
    R(0x01F4, 'P244 Working cond 35 low water target flow', PARAM, unit='L/min', min=0, max=100),
    R(0x01F5, 'P245 Working cond 55 high water target flow', PARAM, unit='L/min', min=0, max=100),
    R(0x01F6, 'P246 Working cond 35 rated fan frequency', PARAM, unit='Hz', min=0, max=60),
    R(0x01F7, 'P247 Working cond 35 rated main valve opening', PARAM, unit='P', min=0, max=500),
    R(0x01F8, 'P248 Working cond 55 rated fan frequency', PARAM, unit='Hz', min=0, max=60),
    R(0x01F9, 'P249 Working cond 55 rated main valve opening', PARAM, unit='P', min=0, max=500),
    R(0x01FA, 'P250 Working cond 35 rated main valve superheat', PARAM, unit='°C', min=-10, max=10, delta=True),
    R(0x01FB, 'P251 Working cond PFC shutdown current', PARAM, unit='A', min=0, max=50),
    R(0x01FC, 'P252 Working cond 55 rated main valve superheat', PARAM, unit='°C', min=-10, max=10, delta=True),
    R(0x01FD, 'P253 Working cond PFC turn-on current', PARAM, unit='A', min=0, max=50),
    R(0x01FE, 'P254 Heating medium', PARAM, min=0, max=1, options={0: 'water', 1: 'antifreeze liquid'}),
    R(0x01FF, 'P255 Smart Grid enable', PARAM, min=0, max=1, options={0: 'enable', 1: 'disable'}),
    R(0x0200, 'P256 Peak grid runtime', PARAM, unit='min', min=30, max=999),
    R(0x0201, 'P257 Dual temperature zone selection', PARAM, min=0, max=2, options={0: 'auto', 1: 'manual', 2: 'disable'}),
    R(0x0202, 'P258 Mixing water valve cycle', PARAM, unit='min', min=5, max=20),
    R(0x0203, 'P259 Mixing valve full cycle time', PARAM, unit='s', min=0, max=180),
    R(0x0204, 'P260 Max DC pump speed', PARAM, unit='%', min=50, max=99),
    R(0x0205, 'P261 DC pump constant temp speed', PARAM, unit='%', min=20, max=99),
    R(0x0206, 'P262 Floor heating test mode selection', PARAM, min=0, max=1, options={0: 'Enable', 1: 'Disable'}),
    # --- User control (names of the upstream entities kept) ---
    R(0x0300, "Temp Set Cooling", CONTROL, unit="°C", temp=True, min=7, max=25),
    R(0x0301, "Temp Set Heating", CONTROL, unit="°C", temp=True, min=15, max=60),
    R(0x0302, "Temp Set Hot Water", CONTROL, unit="°C", temp=True, min=20, max=75),
    R(0x0303, "Temp Set Floor Heating", CONTROL, unit="°C", temp=True, min=20, max=60),
    R(0x0304, "Mode", CONTROL, options={
        0: "Cooling", 1: "Heating", 2: "Hot Water", 3: "Floor Heating",
        4: "Hot Water + Cooling", 5: "Hot Water + Heating", 7: "Hot Water + Floor Heating",
    }),
    R(0x0305, "Heatpump ON/OFF", CONTROL, min=0, max=1),
    # No documented range; bounds are a sane guess
    R(0x0306, "Indoor Temp Set Point", CONTROL, unit="°C", temp=True, min=5, max=35, enabled=False),
    R(0x0307, "Running Mode", CONTROL, options={0: "Standard Mode", 1: "Boost", 2: "Silent"}),
    R(0x0313, "Cooling Setting Curve", CONTROL, options=CURVE_OPTIONS),
    R(0x0314, "Heating Setting Curve", CONTROL, options=CURVE_OPTIONS),
    R(0x0315, "Hot Water Setting Curve", CONTROL, options={0: "Off", 1: "1", 2: "2", 3: "3", 4: "4"}),
    R(0x0316, "Underfloor Heating Setting Curve", CONTROL, options=CURVE_OPTIONS),
    R(0x0317, "Zone 2 Temp Set", CONTROL, unit="°C", temp=True, min=7, max=60, enabled=False),
    R(0x0319, "Zone 1 Temp Set", CONTROL, unit="°C", temp=True, min=7, max=60, enabled=False),
    # Manual pump control can stop the water flow while the compressor runs: expert mode only,
    # and the output never below the 20 % floor of P100 (pump minimum speed)
    R(0x0343, "DC Pump Control", CONTROL, options={0: "Auto", 1: "Manual"}, enabled=False, expert=True),
    R(0x0344, "DC Pump Output", CONTROL, unit="%", min=20, max=100, enabled=False, expert=True),
    # --- Version info ---
    R(0x0360, "Program Version", VERSION),
    R(0x0361, "Product Type", VERSION, options={
        0: "Commercial inverter", 1: "Domestic ON/OFF", 2: "Commercial ON/OFF",
    }),
    R(0x0362, "Product Type ID", VERSION),
    R(0x0363, "Protocol Version", VERSION),
    R(0x0800, 'L11 Pipe electricity heating cycle', PARAM, unit='min', min=1, max=300),
    R(0x0801, 'L12 Sterilization mode', PARAM, min=0, max=2, options={0: 'auto', 1: 'off', 2: 'manual'}),
    R(0x0802, 'L13 Days between sterilizations', PARAM, unit='days', min=5, max=30),
    R(0x0803, 'L14 Sterilization start time', PARAM),
    R(0x0804, 'L15 Sterilization run time', PARAM, unit='min', min=0, max=50),
    R(0x0805, 'L16 Sterilization temperature', PARAM, unit='°C', min=50, max=80),
    R(0x0806, 'L17 Water level control', PARAM, min=0, max=2, options={0: 'Off', 1: 'Hi/Lo switch', 2: 'Hi/Hi/Lo switch'}),
    R(0x0807, 'L18 Hydration control', PARAM, min=0, max=1, options={0: 'level only', 1: 'temp + level'}),
    R(0x0808, 'L19 Allow water temperature', PARAM, unit='°C', min=0, max=99),
    R(0x0809, 'L20 Hysteresis replenishment water', PARAM, unit='°C', min=0, max=20, delta=True),
    R(0x080A, 'L21 Low water cut-off operation', PARAM, min=0, max=2, options={0: 'no start', 1: 'on but no start', 2: 'start'}),
    R(0x080B, 'L22 DHW return water setting', PARAM, min=0, max=3, options={0: 'disable', 1: 'continuous return', 2: 'cycle return', 3: 'temperature diff return'}),
    R(0x080C, 'L23 Return water temp setting', PARAM, unit='°C', min=20, max=65),
    R(0x080D, 'L24 Return water temp differential', PARAM, unit='°C', min=1, max=15, delta=True),
    R(0x080E, 'L25 Return water interval period', PARAM, unit='min', min=3, max=90),
    R(0x080F, 'L26 Return water running period', PARAM, unit='min', min=1, max=30),
    R(0x0810, 'L27 Heating low temp curve DIY', PARAM, min=0, max=1, options={0: 'enable DIY curve', 1: 'disable'}),
    R(0x0811, 'L28 Heating low temp curve coefficient k', PARAM, min=-50, max=0),
    R(0x0812, 'L29 Heating low temp curve constant b', PARAM, min=30, max=80),
    R(0x0813, 'L30 Heating capacity statistics', PARAM, min=0, max=1, options={0: 'enable', 1: 'disable'}),
    R(0x0814, 'L31 External pump flow rate', PARAM, unit='L/min', min=0, max=999),
    R(0x0815, 'L32 DHW electric heater power', PARAM, unit='W', min=0, max=9999),
    R(0x0816, 'L33 Pipe electric heater 1 power', PARAM, unit='W', min=0, max=9999),
    R(0x0817, 'L34 Pipe electric heater 2 power', PARAM, unit='W', min=0, max=9999),
    R(0x0818, 'L35 Heating electric heater power', PARAM, unit='W', min=0, max=9999),
    R(0x0819, 'L36 External water pump power', PARAM, unit='W', min=0, max=9999),
]

# Bitmask registers: address -> (register name, {mask: bit name})
BITMASKS: dict[int, tuple[str, dict[int, str]]] = {
    0x0000: ('Running Status 1', {
        0x0001: 'Refrigerant recovery',
        0x0002: 'Primary antifreeze',
        0x0004: 'Secondary antifreeze',
        0x0008: 'Fault alarm',
        0x0010: 'System oil return',
        0x0100: 'System defrost',
        0x1000: 'Const temp shutdown',
        0x2000: 'Fault shutdown',
        0x4000: 'Machine run',
        0x8000: 'Machine wait',
    }),
    0x0001: ('Running Status 2', {
        0x0001: 'High temp sterilization',
        0x0002: 'High temp steril preserve',
        0x0400: 'Controller on off',
    }),
    0x0002: ('Fault State 1', {
        0x0001: 'Wrong phase',
        0x0002: 'Lack of phase',
        0x0004: 'Water flow',
        0x0008: 'Communication',
        0x0010: 'Emergency',
        0x0020: 'Use time expired',
        0x0040: 'Water tank temp',
        0x0080: 'Water inlet temp',
        0x0100: 'Indoor temp',
        0x0200: 'Environmental temp',
        0x0400: 'User backwater temp',
        0x0800: 'Cooling outlet low',
        0x1000: 'Water level switch',
        0x2000: 'Water outlet temp',
        0x4000: 'Heating outlet high',
        0x8000: 'Excessive temp diff',
    }),
    0x0003: ('Fault State 2', {
        0x0001: 'Env low temp protect',
        0x0040: 'Indoor humidity',
        0x0800: 'Phase order dial',
        0x2000: 'Water pump 1 feedback',
        0x4000: 'Water pump 2 feedback',
        0x8000: 'Low water flow',
    }),
    0x0004: ('Fault State 3', {
        0x0001: 'Phase seq disconnect',
        0x0002: 'Expansion board comm',
        0x0004: 'Plate HX temp',
        0x0008: 'Fan motor 1 comm',
        0x0010: 'Fan motor 2 comm',
        0x0020: 'Online model mismatch',
        0x0040: 'Solar HW sensor',
        0x0080: 'AHS temp sensor',
        0x0100: 'Buffer tank',
        0x0200: 'Main outlet temp',
        0x1000: 'Zone 1 temp sensor',
    }),
    0x0005: ('System 1 Fault 1', {
        0x0001: 'High pressure switch',
        0x0002: 'Low pressure switch',
        0x0004: 'High pressure over',
        0x0008: 'Low pressure over',
        0x0010: 'Exhaust over',
        0x0020: 'Current protection',
        0x0040: 'Coil pressure high',
        0x0080: 'Coil temp fault',
        0x0100: 'Return air temp fault',
        0x0200: 'Exhaust temp fault',
        0x0400: 'Economizer inlet fault',
        0x0800: 'Economizer outlet fault',
        0x1000: 'Fan drive comm',
        0x2000: 'DC fan fault',
        0x4000: 'Refrig coil temp fault',
    }),
    0x0006: ('System 1 Fault 2', {
        0x0001: 'High pressure sensor',
        0x0002: 'Low pressure sensor',
        0x0004: 'Middle pressure switch',
        0x0008: 'Coil temp over high',
        0x0010: 'Comp drive board comm',
    }),
    0x0007: ('System 1 Drive Fault 1', {
        0x0001: 'IPM overcurrent',
        0x0002: 'Compressor drive',
        0x0004: 'Compressor overcurrent',
        0x0008: 'Input voltage loss',
        0x0010: 'IPM current sampling',
        0x0020: 'Power comp overheat',
        0x0040: 'Precharge failed',
        0x0080: 'DC bus overvoltage',
        0x0100: 'DC bus undervoltage',
        0x0200: 'AC input undervoltage',
        0x0400: 'AC input overvoltage',
        0x0800: 'Input volt sampling',
        0x1000: 'DSP PFC comm',
        0x2000: 'Radiator temp sensor',
        0x4000: 'DSP comm board',
        0x8000: 'Main control board',
    }),
    0x0008: ('System 1 Drive Fault 2', {
        0x0001: 'Compressor overcurrent alarm',
        0x0002: 'Weak magnetic protection',
        0x0004: 'PIM overheat',
        0x0008: 'PFC overheat',
        0x0010: 'AC input overcurrent',
        0x0020: 'EEPROM error',
        0x0080: 'EEPROM refresh complete',
        0x0100: 'Temp sensing limit',
        0x0200: 'AC undervolt freq limit',
    }),
    0x0009: ('System 1 Drive Fault 3', {
        0x0001: 'IPM overheat shutdown',
        0x0002: 'Compressor missing phase',
        0x0004: 'Compressor overload',
        0x0008: 'Input current sampling',
        0x0010: 'PIM supply voltage',
        0x0020: 'Precharge voltage',
        0x0040: 'EEPROM failure',
        0x0080: 'AC input overvoltage',
        0x0100: 'Microelectronics',
        0x0200: 'Compressor type code',
        0x0400: 'Current sampling overcurrent',
    }),
    0x0019: ('Relay Output 1', {
        0x0001: 'Hot water eheating',
        0x0002: 'Fan high wind',
        0x0008: 'Fan low wind',
        0x0010: 'AC eheating',
        0x0020: 'Floor eheating',
        0x0040: 'Main circulating pump',
        0x0200: 'Elec crankshaft heating',
        0x0400: 'Chassis eheating',
        0x0800: 'Return valve pump',
        0x4000: 'AC solenoid 3-way',
        0x8000: 'Floor solenoid 3-way',
    }),
    0x001A: ('Relay Output 2', {
        0x0001: 'Compressor 1',
        0x0002: 'Liquid injection 1',
        0x0004: 'EVI EEV 1',
        0x0008: 'Four way valve 1',
        0x0010: 'Bypass valve 1',
        0x0020: 'Fan motor 1',
        0x0100: 'Aux heating pump',
        0x0400: 'Compressor 2',
        0x0800: 'Liquid injection 2',
        0x1000: 'EVI EEV 2',
        0x2000: 'Four way valve 2',
    }),
    0x001B: ('Relay Output 3', {
        0x0040: 'Expansion tank eheating',
        0x0080: 'HW heat source pump',
        0x0100: 'Heating heat source pump',
        0x0200: 'AHS signal output',
    }),
    0x001C: ('Relay Output 4', {
        0x0001: 'Pipe eheating 1',
        0x0002: 'Pipe eheating 2',
        0x0004: 'Aux water pump',
        0x0008: 'Zone 2 water pump',
        0x0010: 'Zone 1 water pump',
    }),
    0x001D: ('Switch Port 1', {
        0x0001: 'SW1',
        0x0002: 'SW2',
        0x0004: 'SW3',
        0x0008: 'SW4',
        0x0010: 'SW5',
        0x0020: 'SW6',
        0x0040: 'SW7',
        0x0080: 'SW8',
        0x0100: 'Water flow switch',
        0x0400: 'House heating linkage',
        0x0800: 'Aux HW linkage',
        0x1000: 'Linkage switch',
        0x2000: 'Emergency switch',
    }),
    0x001E: ('Switch Port 2', {
        0x0080: 'High pressure switch 1',
        0x0100: 'Low pressure switch 1',
        0x0200: 'Middle pressure switch 1',
        0x0400: 'High pressure switch 2',
        0x0800: 'Low pressure switch 2',
        0x1000: 'Middle pressure switch 2',
    }),
    0x001F: ('Switch Port 3', {
        0x0020: 'Buffer tank AHS linkage',
    }),
}

# System 2 fault registers mirror System 1 (0x0005-0x0009) at +5; only present with P114 = 2
SYSTEM2_OFFSET = 5
SYSTEM1_FAULT_REGISTERS = range(0x0005, 0x000A)

# Bits in the fault registers that report a state rather than a fault
NON_FAULT_BITS = {(0x0008, 0x0080)}  # EEPROM refresh complete

# Bits of 0x0000 keep the entity names upstream gave them
STATUS1_NAMES = {
    0x0001: "Running Status: Refrigerant Recovery",
    0x0002: "Running Status: Primary Anti-freeze",
    0x0004: "Running Status: Secondary Anti-freeze",
    0x0008: "Running Status: Fault Alarm",
    0x0010: "Running Status: System Oil Return",
    0x0100: "Running Status: System Frosting",
    0x1000: "Running Status: Shutdown after Reaching Temp",
    0x2000: "Running Status: Shutdown after Unit Failure",
    0x4000: "Running Status: Unit Operation",
    0x8000: "Running Status: Unit Waiting for Operation",
}

# Command coils (FC01 read / FC05 write) exposed as switches
COILS: dict[int, str] = {
    0x1000: "Powerful Mode",
    0x1001: "Silent Mode",
    0x1012: "Quick Heat Mode",
    0x1013: "Force Defrost",
    0x1018: "Force Sterilization",
    0x101A: "Allow Water Return",
}

REFRIGERANT_REGISTER = 0x0177
REFRIGERANT_TYPES = {1: "R410A", 2: "R32", 3: "R290"}
COMPRESSORS_REGISTER = 0x0172
SWITCH_REGISTER = 0x0305

# AC input current clamp is non-linear below ~10 A: (raw A, actual A) pairs, §2c
AC_CURRENT_REGISTER = 0x0045
AC_CURRENT_CALIBRATION = [
    (0.0, 0.0), (1.0, 1.0), (2.0, 2.0), (3.0, 2.5), (4.0, 2.9), (5.0, 3.4),
    (6.0, 4.6), (7.0, 5.5), (8.0, 6.8), (9.0, 7.8), (10.0, 8.5), (11.0, 9.0),
]

# Temperature sensors report this or lower when the probe isn't fitted
SENSOR_SENTINEL = -40

BY_ADDR: dict[int, R] = {r.addr: r for r in REGISTERS}


def temperature_scale(refrigerant_type: int | None) -> float:
    """R290 units send temperatures ×10, the others in whole degrees."""
    return 0.1 if refrigerant_type == 3 else 1.0


def calibrate_ac_current(value: float) -> float:
    """Interpolate the AC input current calibration curve (non-linear below ~10 A)."""
    curve = AC_CURRENT_CALIBRATION
    if value <= curve[0][0]:
        return curve[0][1]
    for (x0, y0), (x1, y1) in pairwise(curve):
        if value <= x1:
            return y0 + (value - x0) * (y1 - y0) / (x1 - x0)
    # Above the curve the clamp is linear again: keep the last offset
    return value - (curve[-1][0] - curve[-1][1])


def is_writable(reg: R, expert: bool) -> bool:
    """CONTROL registers (expert-flagged ones in expert mode), PARAM registers only in expert
    mode and only with known bounds."""
    if reg.protected:
        return False
    if reg.group == CONTROL:
        return expert or not reg.expert
    if reg.group == PARAM and expert:
        return reg.options is not None or (reg.min is not None and reg.max is not None)
    return False
