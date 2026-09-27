"""Generate the options-flow texts in strings.json and translations/en.json.

Home Assistant takes form labels and help texts only from translations, so the ~290
installer parameters get theirs from registers.py and param_info.py. Run after changing
either: .venv/bin/python tools/gen_translations.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from custom_components.adlar_heatpump.config_flow import (
    SET_ALL,
    field_key,
    group_registers,
)
from custom_components.adlar_heatpump.param_info import (
    DESCRIPTIONS,
    PARAM_GROUPS,
)
from custom_components.adlar_heatpump.registers import can_edit

COMPONENT = ROOT / "custom_components" / "adlar_heatpump"


def _number(value: float) -> str:
    return f"{value:g}".replace("-", "−")


def help_text(reg) -> str:
    text = DESCRIPTIONS[reg.addr]
    if reg.options is not None:
        values = ", ".join(f"{k} = {v}" for k, v in reg.options.items())
        text += f" Values: {values}."
    elif reg.min is not None and reg.max is not None:
        unit = f" {reg.unit}" if reg.unit else ""
        text += f" Range {_number(reg.min)}–{_number(reg.max)}{unit}."
    if not can_edit(reg):
        text += " Can't be made editable."
    return text


def options_section() -> dict:
    steps: dict = {
        "init": {
            "title": "Adlar Heatpump options",
            "description": (
                "Choose per installer parameter how it shows in Home Assistant:\n"
                "- **Hidden**: no entity, and the value isn't read from the heat pump.\n"
                "- **Read-only**: a sensor that shows the value.\n"
                "- **Editable**: a number or dropdown that writes to the heat pump. Wrong "
                "values for protection, valve or frequency parameters can damage it.\n\n"
                "Open a group, make your choices, and finish with **Save**."
            ),
            "menu_options": {
                "polling": "Polling intervals",
                **{f"group_{key}": title for key, title, *_ in PARAM_GROUPS},
                "save": "Save",
            },
        },
        "polling": {
            "title": "Polling intervals",
            "data": {
                "scan_interval": "Scan interval (seconds)",
                "slow_interval": "Parameter read interval (seconds)",
            },
            "data_description": {
                "scan_interval": "How often measurements, status and controls are read.",
                "slow_interval": "How often the shown installer parameters, limits and version info are read.",
            },
        },
    }
    for key, title, first, last in PARAM_GROUPS:
        registers = group_registers(first, last)
        steps[f"group_{key}"] = {
            "title": title,
            "description": "Hidden, read-only or editable per parameter. Back in the menu, **Save** stores the choices.",
            "data": {SET_ALL: "Set all in this group", **{field_key(r): r.name for r in registers}},
            "data_description": {
                SET_ALL: "Applies one choice to every parameter on this page; editable only where allowed.",
                **{field_key(r): help_text(r) for r in registers},
            },
        }
    return {"step": steps}


SELECTORS = {
    "param_mode": {"options": {"hidden": "Hidden", "read_only": "Read-only", "editable": "Editable"}},
    SET_ALL: {"options": {
        "keep": "Choose per parameter", "hidden": "Hidden", "read_only": "Read-only", "editable": "Editable",
    }},
}


def main() -> None:
    for path in (COMPONENT / "strings.json", COMPONENT / "translations" / "en.json"):
        data = json.loads(path.read_text())
        data["options"] = options_section()
        data["selector"] = SELECTORS
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
