import { html, nothing } from "lit";
import { differs, formatRange, formatValue, label, parseEdit } from "./parameters";
import type { Choices } from "./parameters";
import { texts } from "./texts";
import type { Parameter } from "./types";

/** What a row needs from the panel. */
export interface RowContext {
  /** Nothing is being read, written or edited: an edit may start. */
  idle: boolean;
  staged: Choices;
  edit: { key: string; input: string } | null;
  /** Key of the parameter being written. */
  writing: string | null;
  result: { key: string; ok: boolean; text: string } | null;
  /** Start editing a parameter; null cancels. */
  onEdit: (p: Parameter | null) => void;
  onInput: (input: string) => void;
  onSave: (p: Parameter, value: number) => void;
  onChoice: (p: Parameter, kind: keyof Choices, on: boolean) => void;
}

const inputValue = (ev: Event) => (ev.target as HTMLInputElement | HTMLSelectElement).value;

function editor(p: Parameter, input: string, c: RowContext) {
  const parsed = parseEdit(p, input);
  const unchanged = "value" in parsed && parsed.value === p.value;
  const save = (ev: Event) => {
    ev.preventDefault();
    if ("value" in parsed && !unchanged) c.onSave(p, parsed.value);
  };
  return html`<form class="editor" novalidate @submit=${save}>
      ${p.options
        ? html`<select aria-label=${texts.newValue(label(p))} @change=${(ev: Event) => c.onInput(inputValue(ev))}>
            ${p.options.map(
              (o) => html`<option value=${o.value} ?selected=${String(o.value) === input}>${o.label}</option>`,
            )}
          </select>`
        : html`<input
              type="number"
              inputmode="decimal"
              aria-label=${texts.newValue(label(p))}
              min=${p.min ?? nothing}
              max=${p.max ?? nothing}
              step=${p.step ?? nothing}
              .value=${input}
              @input=${(ev: Event) => c.onInput(inputValue(ev))}
            />${p.unit ? html`<span class="unit">${p.unit}</span>` : nothing}`}
      <button class="btn primary" type="submit" ?disabled=${"error" in parsed || unchanged}>${texts.save}</button>
      <button class="btn" type="button" @click=${() => c.onEdit(null)}>${texts.cancel}</button>
    </form>
    ${"error" in parsed ? html`<div class="result error" role="alert">${parsed.error}</div>` : nothing}`;
}

function current(p: Parameter, c: RowContext) {
  return html`<div class="current">
    <span class="number">${c.writing === p.key ? texts.writing : formatValue(p, p.value)}</span>
    ${!p.can_edit
      ? html`<span class="tag">${texts.readOnly}</span>`
      : p.value !== null
        ? html`<button class="btn" aria-label="${texts.edit} ${label(p)}" ?disabled=${!c.idle} @click=${() => c.onEdit(p)}>
            ${texts.edit}
          </button>`
        : nothing}
  </div>`;
}

function tick(p: Parameter, kind: keyof Choices, stored: boolean, text: string, hint: string, c: RowContext) {
  const on = c.staged[kind].has(p.key);
  const change = (ev: Event) => {
    // The panel decides (a risky tick asks first): the box follows the staged choices, not the click
    const box = ev.target as HTMLInputElement;
    const wanted = box.checked;
    box.checked = on;
    c.onChoice(p, kind, wanted);
  };
  return html`<label class=${on !== stored ? "staged" : ""} title=${hint}>
    <input type="checkbox" .checked=${on} @change=${change} />${text}
  </label>`;
}

/** One parameter: what it is, its value with the edit control, and its two choices. */
export function parameterRow(p: Parameter, c: RowContext) {
  const range = formatRange(p);
  return html`<div class="row ${differs(p) ? "differs" : ""}">
    <div class="what">
      ${p.code ? html`<span class="code">${p.code}</span>` : nothing}
      <div>
        <div class="name">${p.name}</div>
        ${p.description ? html`<div class="secondary">${p.description}</div>` : nothing}
      </div>
    </div>
    <div class="value">
      ${c.edit?.key === p.key ? editor(p, c.edit.input, c) : current(p, c)}
      ${range ? html`<div class="secondary">${p.options ? texts.options(range) : texts.range(range)}</div>` : nothing}
      ${differs(p)
        ? html`<div class="baseline">${texts.baseline(formatValue(p, p.baseline))} <span class="pill">${texts.differs}</span></div>`
        : nothing}
      ${c.result?.key === p.key
        ? html`<div class="result ${c.result.ok ? "ok" : "error"}" role="status">${c.result.text}</div>`
        : nothing}
    </div>
    <div class="choices">
      ${tick(p, "sensors", p.sensor, texts.sensor, texts.sensorHint, c)}
      ${p.can_edit ? tick(p, "automations", p.automation, texts.automation, texts.automationHint, c) : nothing}
    </div>
  </div>`;
}
