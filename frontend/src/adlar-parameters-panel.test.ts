import { expect, it } from "vitest";
import "./adlar-parameters-panel";
import { AdlarParametersPanel } from "./adlar-parameters-panel";
import { texts } from "./texts";
import type { ListResult, Parameter } from "./types";

/** A rendered template as text: its markup with the values filled in. */
function text(value: unknown): string {
  if (Array.isArray(value)) return value.map(text).join("");
  if (value && typeof value === "object" && "strings" in value) {
    const { strings, values } = value as { strings: readonly string[]; values: unknown[] };
    return strings.map((s, i) => s + (i < values.length ? text(values[i]) : "")).join("");
  }
  return typeof value === "string" || typeof value === "number" ? String(value) : "";
}

const parameter: Parameter = {
  key: "0163",
  code: "P99",
  name: "Pump speed regulation temp diff",
  description: null,
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
  value: 6,
};

function panel(over: Partial<ListResult> = {}) {
  const element = new AdlarParametersPanel();
  element._data = {
    entries: [{ entry_id: "a", title: "Heat pump A", loaded: true }],
    entry_id: "a",
    groups: [{ id: "water", title: "P95–P120 Pumps", parameters: [parameter] }],
    recommended: [],
    pump_manual: false,
    baseline_set_at: null,
    ...over,
  };
  return element;
}

it("defines the element and renders the heading while it loads", () => {
  expect(customElements.get("adlar-parameters-panel")).toBe(AdlarParametersPanel);
  const shown = text(new AdlarParametersPanel().render());
  expect(shown).toContain(texts.title);
  expect(shown).toContain(texts.loading);
});

it("shows the groups closed, and one heat pump without a selector", () => {
  const shown = text(panel().render());
  expect(shown).toContain("P95–P120 Pumps");
  expect(shown).toContain("1 parameter");
  expect(shown).not.toContain("P99");
  expect(shown).not.toContain("<select");
  expect(shown).not.toContain(texts.notLoaded);
  expect(shown).not.toContain(texts.pumpManual);
  expect(shown).toContain(texts.baselineReference);
});

it("shows an opened group's parameter with its value, range and baseline", () => {
  const element = panel();
  element._open = new Set(["water"]);
  const shown = text(element.render());
  expect(shown).toContain("P99");
  expect(shown).toContain("6 °C");
  expect(shown).toContain("Range 2 to 10 °C");
  expect(shown).toContain("Baseline 5 °C");
  expect(shown).toContain(texts.edit);
  expect(shown).toContain(texts.automation);
});

it("says so when the heat pump cannot be reached or its pump is on manual", () => {
  const element = panel({
    entries: [
      { entry_id: "a", title: "Heat pump A", loaded: false },
      { entry_id: "b", title: "Heat pump B", loaded: true },
    ],
    pump_manual: true,
  });
  const shown = text(element.render());
  expect(shown).toContain(texts.notLoaded);
  expect(shown).toContain(texts.pumpManual);
  expect(shown).toContain("Heat pump B");
});

it("offers Apply only while a choice differs from what is stored", () => {
  const element = panel();
  expect(text(element.render())).not.toContain(texts.apply);
  element._staged = { sensors: new Set(["0163"]), automations: new Set() };
  const shown = text(element.render());
  expect(shown).toContain("1 change staged.");
  expect(shown).toContain(texts.apply);
  element._staged = { sensors: new Set(), automations: new Set() };
  expect(text(element.render())).not.toContain(texts.apply);
});
