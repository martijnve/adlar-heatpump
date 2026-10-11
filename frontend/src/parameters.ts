// Pure logic of the panel: what to show of the parameters and what to send.
import { texts } from "./texts";
import type { ExportedParameter, Group, Parameter } from "./types";

/** "P99 Pump speed regulation temp diff"; the DC pump pair has no code. */
export const label = (p: Parameter) => (p.code ? `${p.code} ${p.name}` : p.name);

/** A number without float noise (0.30000000000000004 -> "0.3"). */
const num = (value: number) => String(Number(value.toFixed(4)));

/** A value as the user reads it: the option's label, or the number with its unit. */
export function formatValue(p: Parameter, value: number | null): string {
  if (value === null) return texts.noValue;
  if (p.options) return p.options.find((o) => o.value === value)?.label ?? num(value);
  return p.unit ? `${num(value)} ${p.unit}` : num(value);
}

/** The values a parameter can take, as text; null when unknown. */
export function formatRange(p: Parameter): string | null {
  if (p.options) return p.options.map((o) => o.label).join(", ");
  if (p.min === null || p.max === null) return null;
  return texts.rangeOf(num(p.min), formatValue(p, p.max));
}

/** Has a baseline and a value, and they are not equal. */
export const differs = (p: Parameter) =>
  p.baseline !== null && p.value !== null && p.baseline !== p.value;

/** Every word of the query is in the code, the name or the description. */
export function matches(p: Parameter, query: string): boolean {
  const text = `${p.code ?? ""} ${p.name} ${p.description ?? ""}`.toLowerCase();
  return query.toLowerCase().split(/\s+/).every((word) => text.includes(word));
}

export interface GroupView {
  group: Group;
  /** The parameters to show. */
  rows: Parameter[];
  /** Under "differs": parameters that may differ, because their value isn't read yet. */
  unknown: number;
}

/**
 * The groups with the parameters a search and the "differs from baseline" filter leave.
 * With one of them active a group without anything to show is left out; a group with
 * unread values stays in view under "differs", so it can be opened and read.
 * ponytail: "differs" compares only values already read; the filter does not read the other
 * groups itself (decision 4: no extra bus traffic). A "read all" would need its own command.
 */
export function filterGroups(groups: Group[], query: string, differing: boolean): GroupView[] {
  const active = query.trim() !== "" || differing;
  return groups
    .map((group) => {
      const found = group.parameters.filter((p) => matches(p, query));
      return {
        group,
        rows: differing ? found.filter(differs) : found,
        unknown: differing
          ? found.filter((p) => p.baseline !== null && p.value === null).length
          : 0,
      };
    })
    .filter((view) => !active || view.rows.length > 0 || view.unknown > 0);
}

/** The groups with newly read values filled in; a key that isn't in `values` keeps its value. */
export function withValues(groups: Group[], values: Record<string, number | null>): Group[] {
  return groups.map((group) => ({
    ...group,
    parameters: group.parameters.map((p) => (p.key in values ? { ...p, value: values[p.key] } : p)),
  }));
}

/** What the user typed for a parameter: the value to write, or why it cannot be written. */
export function parseEdit(p: Parameter, input: string): { value: number } | { error: string } {
  const value = Number(input);
  if (input.trim() === "" || !Number.isFinite(value)) return { error: texts.errNumber };
  if (p.options) {
    return p.options.some((o) => o.value === value) ? { value } : { error: texts.errOption };
  }
  if ((p.min !== null && value < p.min) || (p.max !== null && value > p.max)) {
    return { error: texts.errRange(formatRange(p) ?? "") };
  }
  // The same tolerance as the backend's check (coordinator.async_write_param)
  if (p.step && Math.abs(value / p.step - Math.round(value / p.step)) > 1e-6) {
    return { error: texts.errStep(num(p.step)) };
  }
  return { value };
}

/** Which parameters are sensors and which the set_parameter service may write. */
export interface Choices {
  sensors: Set<string>;
  automations: Set<string>;
}

/** The choices as the heat pump's entry has them stored. */
export function storedChoices(groups: Group[]): Choices {
  const all = groups.flatMap((group) => group.parameters);
  return {
    sensors: new Set(all.filter((p) => p.sensor).map((p) => p.key)),
    automations: new Set(all.filter((p) => p.automation).map((p) => p.key)),
  };
}

/** Ticking "allow automations" on such a parameter asks for confirmation first. */
export const riskyForAutomations = (p: Parameter) => p.warning === "factory" || p.warning === "dc_pump";

/** A copy of the set with the key in or out. */
export function withKey(set: Set<string>, key: string, on: boolean): Set<string> {
  const copy = new Set(set);
  if (on) copy.add(key);
  else copy.delete(key);
  return copy;
}

const changed = (a: Set<string>, b: Set<string>) =>
  [...a].filter((key) => !b.has(key)).length + [...b].filter((key) => !a.has(key)).length;

/** How many ticks differ between the stored and the staged choices. */
export const changeCount = (stored: Choices, staged: Choices) =>
  changed(stored.sensors, staged.sensors) + changed(stored.automations, staged.automations);

/** The complete sets, as set_choices wants them. */
export const choicesRequest = (staged: Choices) => ({
  sensors: [...staged.sensors].sort(),
  automations: [...staged.automations].sort(),
});

/** The export as one JSON file: the heat pump's title, the time and every parameter. */
export function exportFile(title: string, at: Date, parameters: ExportedParameter[]) {
  const slug = title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  return {
    name: `${slug}-parameters-${at.toISOString().slice(0, 10)}.json`,
    content: JSON.stringify({ title, exported_at: at.toISOString(), parameters }, null, 2),
  };
}
