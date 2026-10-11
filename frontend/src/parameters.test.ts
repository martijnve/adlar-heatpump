import { describe, expect, it } from "vitest";
import {
  changeCount,
  choicesRequest,
  differs,
  exportFile,
  filterGroups,
  formatRange,
  formatValue,
  matches,
  parseEdit,
  riskyForAutomations,
  storedChoices,
  withKey,
  withValues,
} from "./parameters";
import type { Group, Parameter } from "./types";

function param(over: Partial<Parameter> = {}): Parameter {
  return {
    key: "0163",
    code: "P99",
    name: "Pump speed regulation temp diff",
    description: "Inlet-outlet temperature difference the pump regulates towards.",
    unit: "°C",
    min: 2,
    max: 10,
    step: 1,
    options: null,
    can_edit: true,
    warning: null,
    sensor: false,
    automation: false,
    baseline: 5,
    value: 5,
    ...over,
  };
}

const choice = param({
  key: "0105",
  code: "P05",
  name: "Linkage switch",
  description: "Room thermostat.",
  unit: null,
  min: 0,
  max: 1,
  step: null,
  options: [
    { value: 0, label: "enable" },
    { value: 1, label: "disable" },
  ],
  baseline: 0,
  value: null,
});

const groups: Group[] = [
  { id: "water", title: "Water", parameters: [param(), param({ key: "0164", code: "P100", name: "Pump mode", value: 7 })] },
  { id: "protection", title: "Protection", parameters: [choice, param({ key: "0100", code: "P00", name: "Ambient sensor", description: null, baseline: null, value: null })] },
];

describe("values as text", () => {
  it("shows a number with its unit, an option by its label and nothing as a dash", () => {
    expect(formatValue(param(), 5)).toBe("5 °C");
    expect(formatValue(param({ unit: null }), 0.1 + 0.2)).toBe("0.3");
    expect(formatValue(choice, 1)).toBe("disable");
    expect(formatValue(choice, 7)).toBe("7");
    expect(formatValue(param(), null)).toBe("—");
  });

  it("gives the range of a number and the labels of a choice", () => {
    expect(formatRange(param())).toBe("2 to 10 °C");
    expect(formatRange(choice)).toBe("enable, disable");
    expect(formatRange(param({ min: null }))).toBeNull();
  });
});

describe("differs from baseline", () => {
  it("needs a baseline and a value that are not equal", () => {
    expect(differs(param({ baseline: 5, value: 6 }))).toBe(true);
    expect(differs(param({ baseline: 5, value: 5 }))).toBe(false);
    expect(differs(param({ baseline: null, value: 6 }))).toBe(false);
    expect(differs(param({ baseline: 5, value: null }))).toBe(false);
    expect(differs(param({ baseline: 0, value: 1 }))).toBe(true);
  });
});

describe("search and filter", () => {
  it("searches the code, the name and the description, whatever the case", () => {
    expect(matches(param(), "p99")).toBe(true);
    expect(matches(param(), "REGULATION")).toBe(true);
    expect(matches(param(), "inlet-outlet")).toBe(true);
    expect(matches(param(), "pump towards")).toBe(true);
    expect(matches(param(), "pump defrost")).toBe(false);
    expect(matches(param({ code: null, description: null }), "pump ")).toBe(true);
  });

  it("keeps every group and parameter without a search or filter", () => {
    const views = filterGroups(groups, " ", false);
    expect(views.map((v) => [v.group.id, v.rows.length, v.unknown])).toEqual([
      ["water", 2, 0],
      ["protection", 2, 0],
    ]);
  });

  it("leaves out the groups a search finds nothing in", () => {
    const views = filterGroups(groups, "pump", false);
    expect(views.map((v) => v.group.id)).toEqual(["water"]);
    expect(views[0].rows.map((p) => p.code)).toEqual(["P99", "P100"]);
    expect(filterGroups(groups, "nothing like this", false)).toEqual([]);
  });

  it("shows what differs and keeps a group whose values aren't read yet", () => {
    const views = filterGroups(groups, "", true);
    expect(views.map((v) => [v.group.id, v.rows.map((p) => p.code), v.unknown])).toEqual([
      ["water", ["P100"], 0],
      // P05 has a baseline and no value; P00 has no baseline, so it cannot differ
      ["protection", [], 1],
    ]);
  });

  it("combines the search and the filter", () => {
    expect(filterGroups(groups, "p99", true)).toEqual([]);
    expect(filterGroups(groups, "p100", true)[0].rows.map((p) => p.code)).toEqual(["P100"]);
  });

  it("fills in newly read values and leaves the rest", () => {
    const read = withValues(groups, { "0105": 1, "0100": null, "0164": 5 });
    expect(read[1].parameters[0].value).toBe(1);
    expect(read[0].parameters.map((p) => p.value)).toEqual([5, 5]);
    expect(read[0].parameters[0]).toBe(groups[0].parameters[0]);
    expect(groups[1].parameters[0].value).toBeNull();
    expect(filterGroups(read, "", true).map((v) => [v.group.id, v.rows.map((p) => p.code)])).toEqual([
      ["protection", ["P05"]],
    ]);
  });
});

describe("an edited value", () => {
  it("accepts a value in range and on the step grid", () => {
    expect(parseEdit(param(), "2")).toEqual({ value: 2 });
    expect(parseEdit(param(), "10")).toEqual({ value: 10 });
    expect(parseEdit(param({ min: -5, step: 0.5 }), "-2.5")).toEqual({ value: -2.5 });
    expect(parseEdit(param({ step: 0.1 }), "2.3")).toEqual({ value: 2.3 });
  });

  it("refuses what is no number", () => {
    expect(parseEdit(param(), "")).toEqual({ error: "Enter a number." });
    expect(parseEdit(param(), "  ")).toEqual({ error: "Enter a number." });
    expect(parseEdit(param(), "abc")).toEqual({ error: "Enter a number." });
  });

  it("refuses a value outside min and max, naming the range", () => {
    expect(parseEdit(param(), "1")).toEqual({ error: "Must be within 2 to 10 °C." });
    expect(parseEdit(param(), "11")).toEqual({ error: "Must be within 2 to 10 °C." });
  });

  it("refuses a value off the step grid", () => {
    expect(parseEdit(param(), "2.5")).toEqual({ error: "Must be a multiple of 1." });
    expect(parseEdit(param({ step: 0.5 }), "2.25")).toEqual({ error: "Must be a multiple of 0.5." });
  });

  it("takes only one of the options of a choice", () => {
    expect(parseEdit(choice, "1")).toEqual({ value: 1 });
    expect(parseEdit(choice, "2")).toEqual({ error: "Choose one of the options." });
  });
});

describe("staged choices", () => {
  const stored: Group[] = [
    {
      id: "g",
      title: "G",
      parameters: [
        param({ key: "0001", sensor: true }),
        param({ key: "0002", sensor: true, automation: true }),
        param({ key: "0003" }),
      ],
    },
  ];

  it("reads the stored choices from the list", () => {
    const choices = storedChoices(stored);
    expect([...choices.sensors]).toEqual(["0001", "0002"]);
    expect([...choices.automations]).toEqual(["0002"]);
  });

  it("counts every tick that differs from what is stored", () => {
    const from = storedChoices(stored);
    expect(changeCount(from, storedChoices(stored))).toBe(0);
    const staged = {
      sensors: withKey(withKey(from.sensors, "0003", true), "0001", false),
      automations: withKey(from.automations, "0003", true),
    };
    expect(changeCount(from, staged)).toBe(3);
    // Ticking and unticking leaves nothing to apply
    expect(changeCount(from, { ...staged, sensors: withKey(withKey(staged.sensors, "0003", false), "0001", true), automations: from.automations })).toBe(0);
    expect([...from.sensors]).toEqual(["0001", "0002"]);
  });

  it("sends the complete sets, not the changes", () => {
    const from = storedChoices(stored);
    const staged = { sensors: withKey(from.sensors, "0003", true), automations: withKey(from.automations, "0002", false) };
    expect(choicesRequest(staged)).toEqual({ sensors: ["0001", "0002", "0003"], automations: [] });
  });

  it("stages exactly the recommended set as the sensors", () => {
    const from = storedChoices(stored);
    const staged = { ...from, sensors: new Set(["0003", "0002"]) };
    expect(changeCount(from, staged)).toBe(2);
    expect(choicesRequest(staged)).toEqual({ sensors: ["0002", "0003"], automations: ["0002"] });
  });

  it("asks before automations may write a factory or DC pump parameter", () => {
    expect(riskyForAutomations(param({ warning: "factory" }))).toBe(true);
    expect(riskyForAutomations(param({ warning: "dc_pump" }))).toBe(true);
    expect(riskyForAutomations(param({ warning: "protection" }))).toBe(false);
    expect(riskyForAutomations(param())).toBe(false);
  });
});

describe("export", () => {
  it("is one JSON file with the title, the time and the parameters as the backend gave them", () => {
    const parameters = [
      { code: "P99", key: "0163", name: "Pump speed regulation temp diff", value: 5, unit: "°C", raw: 5 },
      { code: null, key: "0343", name: "DC Pump Control", value: null, unit: null, raw: null },
    ];
    const file = exportFile("Adlar Heatpump (modbus-sim)", new Date("2026-10-11T13:30:00Z"), parameters);
    expect(file.name).toBe("adlar-heatpump-modbus-sim-parameters-2026-10-11.json");
    expect(JSON.parse(file.content)).toEqual({
      title: "Adlar Heatpump (modbus-sim)",
      exported_at: "2026-10-11T13:30:00.000Z",
      parameters,
    });
  });
});
