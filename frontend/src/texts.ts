import type { Warning } from "./types";

/** Every text the panel shows; another language is a second object of this shape. */
export const texts = {
  title: "Heat pump parameters",
  heatPump: "Heat pump",
  loading: "Loading…",
  retry: "Try again",
  dismiss: "Dismiss",
  noEntries: "No heat pump is set up.",

  notLoaded:
    "This heat pump cannot be reached, so its parameters cannot be read or changed. " +
    "The sensor and automation choices can still be changed.",
  pumpManual:
    "DC pump control is not on Auto. The pump now runs at the speed set by hand, whatever the heat " +
    "pump needs: a stopped or slow pump with a running compressor can freeze the plate heat " +
    "exchanger. Set DC pump control back to Auto when you are done.",

  search: "Search code, name or description",
  differing: "Differs from baseline",
  baselineReference: "Baseline: the HHI reference defaults.",
  baselineSetOn: (date: string) => `Baseline: set on ${date}.`,
  setBaseline: "Set baseline",
  settingBaseline: "Reading every parameter…",
  setBaselineTitle: "Set the baseline?",
  setBaselineBody:
    "The current value of every parameter becomes the baseline and replaces the one in use. " +
    "Every parameter is read from the heat pump, which takes several seconds.",
  baselineSet: "The baseline is set to the current values.",
  recommended: "Recommended sensors",
  recommendedHint: "Stage the recommended set of parameters as the sensors",
  export: "Export",
  exporting: "Reading every parameter…",
  exported: (name: string) => `Exported to ${name}.`,
  noMatches: "No parameter matches.",

  parameters: (count: number) => (count === 1 ? "1 parameter" : `${count} parameters`),
  shownOf: (shown: number, count: number) => `${shown} of ${count}`,
  unknownDiff: (count: number) => `, ${count} not read`,
  reading: "Reading from the heat pump…",
  readAgain: "Read again",
  readFailed: (message: string) => `The heat pump did not answer: ${message}`,
  noRows: "No parameter of this group matches.",

  noValue: "—",
  range: (range: string) => `Range ${range}`,
  options: (labels: string) => `Options: ${labels}`,
  rangeOf: (min: string, max: string) => `${min} to ${max}`,
  baseline: (value: string) => `Baseline ${value}`,
  differs: "differs",
  readOnly: "Read-only",
  edit: "Edit",
  save: "Save",
  cancel: "Cancel",
  newValue: (label: string) => `New value of ${label}`,
  writing: "Writing…",
  written: (value: string) => `Written. The heat pump now reports ${value}.`,
  notWritten: (message: string) => `Not written: ${message}`,

  errNumber: "Enter a number.",
  errOption: "Choose one of the options.",
  errRange: (range: string) => `Must be within ${range}.`,
  errStep: (step: string) => `Must be a multiple of ${step}.`,

  confirmWriteTitle: "Write this parameter?",
  confirmWrite: "Write",
  oldValue: "Current value",
  newValueShort: "New value",
  rangeLabel: "Range",
  warnings: {
    factory:
      "Factory setting: change it only on the manufacturer's advice. A wrong value can damage the heat pump.",
    protection:
      "This parameter is part of the heat pump's protection. A wrong value can switch off a safeguard " +
      "and damage the unit.",
    dc_pump:
      "Manual DC pump control stays on until it is set back to Auto. A stopped or slow pump with a " +
      "running compressor can freeze the plate heat exchanger.",
  } satisfies Record<Warning, string>,

  sensor: "Sensor",
  sensorHint: "Show this parameter as a sensor entity",
  automation: "Allow automations",
  automationHint: "The adlar_heatpump.set_parameter service may write this parameter",
  confirmAutomationTitle: "Allow automations to write this parameter?",
  confirmAutomationBody:
    "The adlar_heatpump.set_parameter service may then write it, without anyone confirming the value.",
  confirmAutomation: "Allow",

  staged: (count: number) => (count === 1 ? "1 change staged." : `${count} changes staged.`),
  applyHint: "Applying reloads the heat pump's entities.",
  apply: "Apply",
  applying: "Applying…",
  discard: "Discard",
  applied: "The choices are stored and the heat pump's entities were reloaded.",
  stagedFirst: "Apply or discard the staged changes first",
};
