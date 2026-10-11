"""Groups and short descriptions of the installer parameters, for the options flow.

Descriptions follow the OEM manual (HBG Trading R290 system parameters, chapters 2.7,
2.8 and 4.3) where it covers a parameter, and the HHI v2.2 register model otherwise.
"""
from __future__ import annotations

from .registers import REGISTERS

# (step id, title, first address, last address)
PARAM_GROUPS: list[tuple[str, str, int, int]] = [
    ("protection", "P00–P16 Sensors, switches and protection limits", 0x0100, 0x0110),
    ("fan_water", "P17–P29 Fan speed, start limits and water control", 0x0111, 0x011D),
    ("defrost", "P30–P37 Defrost and shutdown", 0x011E, 0x0125),
    ("eev", "P38–P47 Expansion valves and communication", 0x0126, 0x012F),
    ("frequency", "P48–P72 Compressor and fan frequencies", 0x0130, 0x0148),
    ("valves", "P73–P94 Valve openings, silent mode and EVI", 0x0149, 0x015E),
    ("water", "P95–P120 Pumps, setpoint limits and anti-freeze", 0x015F, 0x0178),
    ("shield", "P121–P149 Frequency shields, defrost and water protection", 0x0179, 0x0195),
    ("heat_sources", "P150–P183 Heat sources, cascade and powerful mode", 0x0196, 0x01B7),
    ("working", "P184–P253 Factory working-condition calibration", 0x01B8, 0x01FD),
    ("zones", "P254–P262 Heating medium, smart grid and zones", 0x01FE, 0x0206),
    ("l_params", "L11–L36 Sterilisation, DHW return, heating curve and energy", 0x0800, 0x0819),
    ("service", "DC pump manual control", 0x0343, 0x0344),
]

_FACTORY = "Factory setting; change only on the manufacturer's advice."

# Default choice for a new setup, from Adlår's advanced user manual (Aurora II
# bedieningshandleiding geavanceerd NL1.3): the first set is what its troubleshooting
# (§10, §11.1) tells users to change, the second the rest of its parameter list (§8.2) plus
# useful context; both are shown as sensors, everything else hidden.
RECOMMENDED_EDITABLE = {
    0x0116, 0x0197,                  # P22, P151 backup heating thresholds
    0x0105, 0x011A, 0x0174,          # P05 link switch, P26 hysteresis, P116 inlet/outlet
    0x0117, 0x0163, 0x0164, 0x0192,  # P23 max delta T, P99, P100, P146 pump
    0x0204, 0x0205,                  # P260, P261 pump speeds
    0x0103, 0x0186,                  # P03 flow switch, P134 E03 flow
    0x0801,                          # L12 sterilisation
}
RECOMMENDED_READ_ONLY = {
    0x0115, 0x0118, 0x0119, 0x011D,          # P21, P24, P25, P29
    0x011E, 0x011F, 0x0120, 0x0123, 0x0124,  # P30–P32, P35, P36 defrost
    0x0144, 0x0146, 0x0158, 0x0159,          # P68, P70, P88, P89 fan / silent limits
    0x0169, 0x016A,                          # P105, P106 outdoor limits
    0x0130, 0x01A3, 0x01A9,                  # P48, P163, P169
    0x0125, 0x011C,                          # P37 shutdown mode, P28 pump at target
    *range(0x016C, 0x0172),                  # P108–P113 setpoint limits
    *range(0x0802, 0x0806),                  # L13–L16 sterilisation schedule
    *range(0x0810, 0x0813),                  # L27–L29 own heating curve
}


def recommended_mode(addr: int) -> str:
    if addr in RECOMMENDED_EDITABLE | RECOMMENDED_READ_ONLY:
        return "read_only"
    return "hidden"


def recommended_params() -> dict[str, str]:
    """Options value for a new setup: the recommended non-hidden choices."""
    return {
        f"{addr:04X}": recommended_mode(addr)
        for addr in sorted(RECOMMENDED_EDITABLE | RECOMMENDED_READ_ONLY)
    }

DESCRIPTIONS: dict[int, str] = {
    # --- P00–P16 ---
    0x0100: "Use the outdoor ambient temperature sensor T1.",
    0x0101: "Use the high pressure switch (compressor protection).",
    0x0102: "Use the low pressure switch (compressor protection).",
    0x0103: "Use the water flow switch; without flow the unit stops with E03.",
    0x0104: "Use the compressor thermal overload protection input.",
    0x0105: "Room thermostat on the linkage switch (terminals 19-20): whether an open contact turns the unit off, puts it in standby or turns it off except for hot water.",
    0x0106: "Type of outdoor fan motor fitted. Must match the hardware.",
    0x0107: "After three high pressure trips in a row the unit locks until reset, or never locks.",
    0x0108: "After three low pressure trips in a row the unit locks until reset, or never locks.",
    0x0109: "After three exhaust temperature trips in a row the unit locks until reset, or never locks.",
    0x010A: "After three water flow trips in a row the unit locks until reset, or never locks.",
    0x010B: "High pressure saturation temperature at which the unit stops to protect the compressor.",
    0x010C: "High pressure saturation temperature at which the compressor frequency is reduced (normally P11 − 5).",
    0x010D: "Low pressure saturation temperature at which the unit stops.",
    0x010E: "Low pressure saturation temperature at which the compressor frequency is reduced.",
    0x010F: "Compressor exhaust temperature at which the unit stops.",
    0x0110: "Compressor exhaust temperature at which the frequency is reduced (normally P15 − 10).",
    # --- P17–P29 ---
    0x0111: "Cooling: ambient temperature above which the fan speeds up.",
    0x0112: "Cooling: ambient temperature below which the fan slows down.",
    0x0113: "Heating: ambient temperature above which the fan slows down.",
    0x0114: "Heating: ambient temperature below which the fan speeds up.",
    0x0115: "Below this ambient temperature the unit doesn't start.",
    0x0116: "Heating: outdoor temperature at or below which the external backup heater (boiler or electric) may help; off again at P22 + 3. Adlår: raise it if the house stays cold.",
    0x0117: "Alarm when the difference between water inlet and outlet exceeds this (E37).",
    0x0118: "Correction added to the water inlet (return, T6) temperature reading.",
    0x0119: "Correction added to the water outlet (T7) temperature reading.",
    0x011A: "Heating/cooling hysteresis: how far the water may drift from the setpoint before the unit restarts. 0 = automatic (2–5 °C from the water temperature).",
    0x011B: "Underfloor heating hysteresis, like P26. 0 = automatic.",
    0x011C: "What the built-in pump does once the target temperature is reached: keep running, run 2 min every 10 min, or keep running in cooling, heating/cooling or floor heating only.",
    0x011D: "Minutes the pump runs per 10 minutes during level I anti-freeze protection.",
    # --- P30–P37 ---
    0x011E: "How the unit decides to defrost: smart, by time, fast, or dew point.",
    0x011F: "Accumulated compressor run time before a defrost is considered.",
    0x0120: "Outer coil temperature below which defrosting may start.",
    0x0121: "Ambient-to-coil temperature difference that starts a defrost (condition 1).",
    0x0122: "Ambient-to-coil temperature difference that starts a defrost (condition 2).",
    0x0123: "Longest a defrost may last.",
    0x0124: "Outer coil temperature at which defrosting ends.",
    0x0125: "At the target temperature: let the unit decide when to stop (compressor at minimum frequency for 5 min), stop immediately, or smart in cooling and immediate in heating.",
    # --- P38–P47 ---
    0x0126: "Heating: constant for the initial opening of the main expansion valve.",
    0x0127: "Use the refrigerant pressure sensors.",
    0x0128: "Cooling: correction of the target superheat of the main expansion valve.",
    0x0129: "Heating: correction of the high pressure frequency limit used by the expansion valve control.",
    0x012A: "Heating: correction of the target superheat of the main expansion valve.",
    0x012B: "Use the medium pressure (MV) switch.",
    0x012C: "Detect a failed water flow switch.",
    0x012D: "Modbus slave address of the controller. Changing it breaks this connection.",
    0x012E: "EVI liquid injection valve return difference.",
    0x012F: "EVI (vapour injection) target superheat constant.",
    # --- P48–P72 ---
    0x0130: "Switches the hot water tank sensor on or off. Hot water mode needs it. The sources disagree on the values: Adlår's manual says 0 = on, 1 = off (default 1); the OEM manual says 0 = off, 1 = on.",
    0x0131: "Compressor frequency in hot water mode, as a percentage of its range.",
    0x0132: "Cooling: constant used to calculate the target compressor frequency.",
    0x0133: "Cooling: lowest compressor frequency.",
    0x0134: "Cooling: upper limit of the target compressor frequency.",
    0x0135: "Cooling: lower limit of the target compressor frequency (at most P52).",
    0x0136: "Heating: constant used to calculate the target compressor frequency.",
    0x0137: "Heating: upper limit of the target compressor frequency.",
    0x0138: "Heating: lower limit of the target compressor frequency.",
    0x0139: "Heating: lowest compressor frequency above 0 °C ambient. Lower gives a better COP in mild weather.",
    0x013A: "Heating: lowest compressor frequency between −10 and 0 °C ambient.",
    0x013B: "Heating: lowest compressor frequency below −10 °C ambient.",
    0x013C: "Hot water: constant used to calculate the target compressor frequency.",
    0x013D: "Hot water: upper limit of the target compressor frequency.",
    0x013E: "Hot water: lower limit of the target compressor frequency (at most P61).",
    0x013F: "Hot water: lowest compressor frequency above 0 °C ambient.",
    0x0140: "Hot water: lowest compressor frequency between −10 and 0 °C ambient.",
    0x0141: "Hot water: lowest compressor frequency below −10 °C ambient.",
    0x0142: "DC fan frequency at start-up (rpm = Hz × 15).",
    0x0143: "Heating: lowest DC fan frequency.",
    0x0144: "Heating: highest DC fan frequency.",
    0x0145: "Cooling: lowest DC fan frequency.",
    0x0146: "Cooling: highest DC fan frequency.",
    0x0147: "Compressor frequency above which enhanced (enthalpy) control of the expansion valve starts.",
    0x0148: "Compressor frequency at which the enthalpy increase stops.",
    # --- P73–P94 ---
    0x0149: "Cooling: main expansion valve opening, step 1.",
    0x014A: "Cooling: main expansion valve opening, step 2.",
    0x014B: "Cooling: main expansion valve opening, step 3.",
    0x014C: "Cooling: smallest opening of the main expansion valve.",
    0x014D: "Heating: smallest opening of the main expansion valve.",
    0x014E: "Largest opening of the main expansion valve.",
    0x014F: "Main expansion valve initial opening: constant c.",
    0x0150: "Main expansion valve initial opening: coefficient a.",
    0x0151: "Main expansion valve initial opening: coefficient b.",
    0x0152: "Largest opening of the auxiliary (EVI) expansion valve.",
    0x0153: "Smallest opening of the auxiliary (EVI) expansion valve.",
    0x0154: "How often the main expansion valve is adjusted.",
    0x0155: "Auxiliary expansion valve initial opening: constant c.",
    0x0156: "Auxiliary expansion valve initial opening: coefficient a.",
    0x0157: "Auxiliary expansion valve initial opening: coefficient b.",
    0x0158: "Silent mode: highest compressor frequency. Lower is quieter but gives less capacity.",
    0x0159: "Silent mode: highest fan frequency (rpm = Hz × 15).",
    0x015A: "Ambient temperature below which vapour injection (EVI) may start.",
    0x015B: "Time after compressor start during which EVI may not start.",
    0x015C: "Temperature difference that lets EVI start.",
    0x015D: "Compressor run time before EVI may start.",
    0x015E: "How often the auxiliary (EVI) valve is adjusted.",
    # --- P95–P120 ---
    0x015F: "Whether the circulation pump is shared with other units or independent.",
    0x0160: "Hot water hysteresis: the tank reheats when it drops this far below the setpoint.",
    0x0161: "Automatic compensation of the tank temperature reading.",
    0x0162: "Manual correction added to the tank temperature reading.",
    0x0163: "Inlet-outlet temperature difference the variable-speed pump regulates towards.",
    0x0164: "Lowest speed of the PWM circulation pump.",
    0x0165: "Circulation pump type: on/off (AC) or variable speed (DC, PWM).",
    0x0166: "Which mode energises the four-way valve: cooling or heating.",
    0x0167: "Shortest run time in a mode before switching mode. 0 = no limit.",
    0x0168: "Compressor frequency, in percent, used while switching mode.",
    0x0169: "Ambient temperature limit for cooling mode.",
    0x016A: "Ambient temperature limit for heating mode.",
    0x016B: "Ambient temperature limit for hot water mode.",
    0x016C: "Highest hot water setpoint the user can choose.",
    0x016D: "Lowest hot water setpoint the user can choose.",
    0x016E: "Highest heating setpoint the user can choose.",
    0x016F: "Lowest heating setpoint the user can choose.",
    0x0170: "Highest cooling setpoint the user can choose.",
    0x0171: "Lowest cooling setpoint the user can choose.",
    0x0172: "Number of compressors in the unit. Factory setting.",
    0x0173: "Unit model selection. Factory setting.",
    0x0174: "Which water temperature the unit regulates on: inlet (return, T6) or outlet (T7).",
    0x0175: "Anti-freeze: ambient temperature at or below which protection starts (ends at P117 + 3).",
    0x0176: "Anti-freeze: water outlet temperature at or below which level II protection heats the water.",
    0x0177: "Refrigerant in the unit; decides how temperatures are scaled. Factory setting.",
    0x0178: "Anti-condensation function in cooling.",
    # --- P121–P149 ---
    0x0179: "Heating: lower bound of the first compressor frequency band to skip (to avoid resonance). 0 = off.",
    0x017A: "Heating: upper bound of the first frequency band to skip.",
    0x017B: "Heating: lower bound of the second frequency band to skip.",
    0x017C: "Heating: upper bound of the second frequency band to skip.",
    0x017D: "Heating: lower bound of the third frequency band to skip.",
    0x017E: "Heating: upper bound of the third frequency band to skip.",
    0x017F: "Cooling: lower bound of the first compressor frequency band to skip. 0 = off.",
    0x0180: "Cooling: upper bound of the first frequency band to skip.",
    0x0181: "Cooling: lower bound of the second frequency band to skip.",
    0x0182: "Cooling: upper bound of the second frequency band to skip.",
    0x0183: "Cooling: lower bound of the third frequency band to skip.",
    0x0184: "Cooling: upper bound of the third frequency band to skip.",
    0x0185: "Fan driver: integrated in the main module or a separate module.",
    0x0186: "Water flow at which error E03 is raised. 0 = off (Adlår's advice on E03).",
    0x0187: "Temperature difference at which anti-condensation starts.",
    0x0188: "Ambient temperature above which the throttle bypass valve opens.",
    0x0189: "Delay of the throttle bypass valve after compressor start.",
    0x018A: "Compressor frequency during defrost.",
    0x018B: "Buffer tank electric heater (EH2): enabled, disabled, or used as an auxiliary heat source.",
    0x018C: "Hot water tank electric heater (EH1): enabled, disabled, or used as an auxiliary heat source.",
    0x018D: "Dew point defrost: duration.",
    0x018E: "Dew point defrost: constant.",
    0x018F: "Water temperature needed to allow a defrost.",
    0x0190: "Ambient temperature below which defrosting is possible.",
    0x0191: "Water outlet temperature that triggers anti-freeze protection.",
    0x0192: "Pump model setting for correct flow feedback from the built-in pump; see the pump model table in the manual.",
    0x0193: "Cooling anti-freeze detection: by low pressure, by temperature, or both.",
    0x0194: "Cooling anti-freeze temperature.",
    0x0195: "Highest water outlet temperature.",
    # --- P150–P183 ---
    0x0196: "Heating/cooling circuit pump (P_b): runs with the unit, is switched by a room thermostat, or by the wired controller's sensor.",
    0x0197: "Hot water: outdoor temperature at or below which the external backup heater may help. 0 = off (Adlår's advice on error EA3).",
    0x0198: "Solar/auxiliary heat source for the buffer tank: its pump starts when the source is this much warmer than the tank.",
    0x0199: "Highest hot water temperature from the auxiliary heat source.",
    0x019A: "Highest heating water temperature from the auxiliary heat source.",
    0x019B: "Compressor code (reserved).",
    0x019C: "Use the auxiliary expansion valve.",
    0x019D: "Temperature difference at which the auxiliary expansion valve closes down.",
    0x019E: "Ambient temperature below which the heating water temperature is limited.",
    0x019F: "Constant of the heating water temperature limit.",
    0x01A0: "Coefficient of the heating water temperature limit.",
    0x01A1: "What the auxiliary pump (P_c) serves: hot water, heating/cooling, floor heating, both circuits, or unit circulation.",
    0x01A2: "Interval of the hot water pipe anti-freeze run. 0 = off.",
    0x01A3: "Lowest water flow of the circulation pump. Adlår default 19 (6 kW), 30 (10 kW) or 42 (14 kW) l/min.",
    0x01A4: "Cascade / energy level control: 0 enables intelligent cascade control (P165–P170), 3 disables it.",
    0x01A5: "Cascade: return temperature difference at which the next unit is switched on.",
    0x01A6: "Cascade: return temperature difference at which a unit is switched off.",
    0x01A7: "Cascade: return temperature difference for an emergency stop.",
    0x01A8: "Cascade: share of units that may run in hot water mode.",
    0x01A9: "Maximum compressor power, as a percentage (Adlår). In cascade setups the OEM uses it as the share of units that may run in heating/cooling.",
    0x01AA: "Cascade: time before the next unit is switched on.",
    0x01AB: "Cascade: ambient temperature below which low-voltage shielding applies.",
    0x01AC: "DC fan target frequency constant c.",
    0x01AD: "Heating: lower limit of the fan target frequency.",
    0x01AE: "Expansion valve opening during defrost.",
    0x01AF: "Run cycle at constant temperature.",
    0x01B0: "Shortest defrost.",
    0x01B1: "Water temperature that separates the two defrost stages.",
    0x01B2: "Compressor frequency when defrosting with high water temperature.",
    0x01B3: "Powerful mode: how much the compressor frequency rises per step.",
    0x01B4: "Powerful mode: how far the highest compressor frequency is raised.",
    0x01B5: "Which circuit supplies the heat for defrosting: the current mode, heating, or hot water.",
    0x01B6: "Electric pipe heaters fitted: 3 kW + 6 kW, 3 kW, 6 kW, or none.",
    0x01B7: "Password protecting the parameters on the wired controller. 0 = none.",
    # --- P254–P262 ---
    0x01FE: "Heating medium in the system: water or antifreeze liquid.",
    0x01FF: "SG Ready (smart grid) input. Note: 0 enables, 1 disables.",
    0x0200: "SG Ready: minutes before the unit turns off in the grid's ECO state.",
    0x0201: "Dual temperature zones (radiators plus floor heating through a mixing valve): on at start, on demand, or off.",
    0x0202: "Dual zones: mixing valve adjustment cycle.",
    0x0203: "Dual zones: time the mixing valve takes to go fully open or closed.",
    0x0204: "Highest speed of the DC circulation pump.",
    0x0205: "DC circulation pump speed while the temperature is reached.",
    0x0206: "Floor heating test (screed drying) mode.",
    # --- Service ---
    0x0343: "Auto or manual control of the DC circulation pump. Manual stays on until set back to Auto.",
    0x0344: "Pump speed while DC pump control is manual. Too little flow with a running compressor can freeze the plate heat exchanger.",
    # --- L parameters ---
    0x0800: "Cycle of the electric pipe heating.",
    0x0801: "Legionella sterilisation of the hot water tank: automatic every L13 days at L14, off, or started by hand.",
    0x0802: "Days between two sterilisation runs.",
    0x0803: "Time of day the sterilisation starts.",
    0x0804: "How long the tank is held at the sterilisation temperature.",
    0x0805: "Tank temperature during sterilisation.",
    0x0806: "Water level control of the tank: off, high/low switch, or high/high/low switch.",
    0x0807: "Tank refill control: by level only, or by temperature and level.",
    0x0808: "Water temperature that allows refilling.",
    0x0809: "Hysteresis of the refill water temperature.",
    0x080A: "What happens on low water: don't start, on without starting, or start.",
    0x080B: "Hot water return (circulation) pump P_d: off, always on, in cycles (L25/L26), or by temperature (L23/L24).",
    0x080C: "Hot water return: pipe temperature the circulation keeps.",
    0x080D: "Hot water return: circulation starts at L23 minus this.",
    0x080E: "Hot water return in cycles: interval between runs.",
    0x080F: "Hot water return in cycles: run time.",
    0x0810: "Use the own heating curve L28/L29 instead of the preset curves.",
    0x0811: "Own heating curve slope k: setpoint = k × (ambient + 15) + b. Negative.",
    0x0812: "Own heating curve constant b in setpoint = k × (ambient + 15) + b.",
    0x0813: "Internal energy accounting of the unit.",
    0x0814: "Fixed water flow used for the energy accounting when no flow meter is fitted.",
    0x0815: "Power of the hot water electric heater, for the energy accounting.",
    0x0816: "Power of electric pipe heater 1, for the energy accounting.",
    0x0817: "Power of electric pipe heater 2, for the energy accounting.",
    0x0818: "Power of the heating electric heater, for the energy accounting.",
    0x0819: "Power of the external water pump, for the energy accounting.",
}



def _working_condition(name: str) -> str:
    """P184–P253: calibration at the factory test points (35/55 = water temperature °C)."""
    what = name.split(" ", 1)[1].removeprefix("Working cond ")
    point, _, quantity = what.partition(" ")
    if point[:2] in ("35", "55") and quantity:
        return f"Factory calibration: {quantity} at test point {point} ({point[:2]} °C water). {_FACTORY}"
    return f"Factory calibration: {what}. {_FACTORY}"


for _reg in REGISTERS:
    if 0x01B8 <= _reg.addr <= 0x01FD:
        DESCRIPTIONS.setdefault(_reg.addr, _working_condition(_reg.name))
