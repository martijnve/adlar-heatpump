// The part of Home Assistant's frontend object the panel uses, and the results of the
// adlar_heatpump/* websocket commands (reference: the docstring of websocket.py).

export interface HomeAssistant {
  callWS<T>(msg: Record<string, unknown>): Promise<T>;
  locale?: { language?: string };
  themes?: { darkMode?: boolean };
}

export interface Option {
  value: number;
  label: string;
}

export type Warning = "factory" | "protection" | "dc_pump";

export interface Parameter {
  /** Register address, four upper-case hex digits. */
  key: string;
  code: string | null;
  name: string;
  description: string | null;
  unit: string | null;
  min: number | null;
  max: number | null;
  /** null for a parameter with options. */
  step: number | null;
  options: Option[] | null;
  can_edit: boolean;
  warning: Warning | null;
  sensor: boolean;
  automation: boolean;
  baseline: number | null;
  value: number | null;
}

export interface Group {
  id: string;
  title: string;
  parameters: Parameter[];
}

export interface Entry {
  entry_id: string;
  title: string;
  loaded: boolean;
}

export interface ListResult {
  entries: Entry[];
  entry_id: string | null;
  groups: Group[];
  recommended: string[];
  pump_manual: boolean | null;
  baseline_set_at: string | null;
}

export interface ExportedParameter {
  code: string | null;
  key: string;
  name: string;
  value: number | null;
  unit: string | null;
  raw: number | null;
}
