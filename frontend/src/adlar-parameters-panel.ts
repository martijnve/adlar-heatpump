import { html, LitElement, nothing } from "lit";
import type { PropertyValues, TemplateResult } from "lit";
import {
  changeCount,
  choicesRequest,
  exportFile,
  filterGroups,
  formatRange,
  formatValue,
  label,
  riskyForAutomations,
  storedChoices,
  withKey,
  withValues,
} from "./parameters";
import type { Choices, GroupView } from "./parameters";
import { parameterRow } from "./row";
import type { RowContext } from "./row";
import { styles } from "./styles";
import { texts } from "./texts";
import type { ExportedParameter, Group, HomeAssistant, ListResult, Parameter } from "./types";

/** A question in the dialog; `action` runs when the user confirms. */
interface Confirmation {
  title: string;
  body: TemplateResult;
  confirm: string;
  action: () => void;
}

const message = (err: unknown) => (err as { message?: string } | null)?.message ?? String(err);

function download(name: string, content: string) {
  // ponytail: a blob link; the companion apps' webviews may ignore it, a download served by the
  // integration would be needed there
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([content], { type: "application/json" }));
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
}

/** Admin panel for the installer parameters: read, change, and choose sensors and automations. */
export class AdlarParametersPanel extends LitElement {
  static properties = {
    // Set by Home Assistant on a custom panel.
    hass: { attribute: false },
    narrow: { type: Boolean },
    route: { attribute: false },
    panel: { attribute: false },
    _data: { state: true },
    _error: { state: true },
    _query: { state: true },
    _differing: { state: true },
    _open: { state: true },
    _reads: { state: true },
    _staged: { state: true },
    _edit: { state: true },
    _writing: { state: true },
    _result: { state: true },
    _confirm: { state: true },
    _busy: { state: true },
    _notice: { state: true },
  };
  static styles = styles;

  declare hass?: HomeAssistant;
  declare narrow: boolean;
  declare route: unknown;
  declare panel: unknown;
  /** The last answer of `list`, with the values read since. */
  declare _data: ListResult | null;
  declare _error: string | null;
  declare _query: string;
  declare _differing: boolean;
  /** Ids of the opened groups. */
  declare _open: Set<string>;
  declare _reads: Record<string, { reading?: boolean; error?: string }>;
  /** The choices being staged; null while they are as stored. */
  // ponytail: leaving the panel drops staged choices without asking; a guard on navigation if
  // that turns out to bite
  declare _staged: Choices | null;
  declare _edit: RowContext["edit"];
  declare _writing: string | null;
  declare _result: RowContext["result"];
  declare _confirm: Confirmation | null;
  /** What an action on the whole heat pump is doing, while it runs. */
  declare _busy: string | null;
  declare _notice: { ok: boolean; text: string } | null;
  private _started = false;

  constructor() {
    super();
    this.narrow = false;
    this._data = null;
    this._error = null;
    this._query = "";
    this._differing = false;
    this._open = new Set();
    this._reads = {};
    this._staged = null;
    this._edit = null;
    this._writing = null;
    this._result = null;
    this._confirm = null;
    this._busy = null;
    this._notice = null;
  }

  protected updated(changed: PropertyValues) {
    if (this.hass && !this._started) {
      this._started = true;
      this._load();
    }
    const dialog = this.renderRoot.querySelector("dialog");
    if (this._confirm && !dialog?.open) dialog?.showModal();
    if (!this._confirm && dialog?.open) dialog.close();
    if (changed.has("_edit") && this._edit && !changed.get("_edit")) {
      this.renderRoot.querySelector<HTMLElement>(".editor input, .editor select")?.focus();
    }
  }

  private get _entry() {
    return this._data?.entries.find((entry) => entry.entry_id === this._data?.entry_id);
  }

  private _call<T>(command: string, data: Record<string, unknown> = {}) {
    return this.hass!.callWS<T>({
      type: `adlar_heatpump/${command}`,
      entry_id: this._data?.entry_id,
      ...data,
    });
  }

  /** Ask for the heat pumps and the parameters of one of them (default: the one shown). */
  private async _load(entryId = this._data?.entry_id) {
    try {
      // Without an entry_id the backend answers for the first heat pump
      this._data = await this._call<ListResult>("list", { entry_id: entryId ?? undefined });
      this._error = null;
    } catch (err) {
      this._error = message(err);
    }
  }

  // ponytail: the chosen heat pump is not in the URL, so a page reload shows the first one again
  private _select(entryId: string) {
    this._open = new Set();
    this._reads = {};
    this._staged = null;
    this._edit = null;
    this._result = null;
    this._notice = null;
    this._load(entryId);
  }

  private _toggle(group: Group) {
    const open = !this._open.has(group.id);
    this._open = withKey(this._open, group.id, open);
    if (open && this._entry?.loaded) this._read(group.id);
    if (!open && group.parameters.some((p) => p.key === this._edit?.key)) this._edit = null;
  }

  /** Read a group from the heat pump now. */
  private async _read(groupId: string) {
    const entryId = this._data?.entry_id;
    const current = () => this._data?.entry_id === entryId;
    this._reads = { ...this._reads, [groupId]: { reading: true } };
    let error: string | undefined;
    try {
      const { values } = await this._call<{ values: Record<string, number | null> }>("read_group", {
        group: groupId,
      });
      if (current()) this._data = { ...this._data!, groups: withValues(this._data!.groups, values) };
    } catch (err) {
      error = message(err);
    }
    if (current()) this._reads = { ...this._reads, [groupId]: { error } };
  }

  private _filter(change: { _query?: string; _differing?: boolean }) {
    Object.assign(this, change);
    // The row being edited may leave the view
    this._edit = null;
  }

  private _askWrite(p: Parameter, value: number) {
    const range = formatRange(p);
    this._confirm = {
      title: texts.confirmWriteTitle,
      body: html`<p><strong>${label(p)}</strong></p>
        <dl>
          <dt>${texts.oldValue}</dt>
          <dd>${formatValue(p, p.value)}</dd>
          <dt>${texts.newValueShort}</dt>
          <dd>${formatValue(p, value)}</dd>
          ${range ? html`<dt>${texts.rangeLabel}</dt><dd>${range}</dd>` : nothing}
        </dl>
        ${p.warning ? html`<p class="banner warning">${texts.warnings[p.warning]}</p>` : nothing}`,
      confirm: texts.confirmWrite,
      action: () => this._write(p, value),
    };
  }

  private async _write(p: Parameter, value: number) {
    this._edit = null;
    this._result = null;
    this._writing = p.key;
    let failed = false;
    try {
      const result = await this._call<{ value: number }>("write", { key: p.key, value });
      this._data = { ...this._data!, groups: withValues(this._data!.groups, { [p.key]: result.value }) };
      this._result = { key: p.key, ok: true, text: texts.written(formatValue(p, result.value)) };
    } catch (err) {
      failed = true;
      this._result = { key: p.key, ok: false, text: texts.notWritten(message(err)) };
    }
    this._writing = null;
    const group = this._data!.groups.find((g) => g.parameters.some((q) => q.key === p.key));
    // After a failure the heat pump may hold either value: show what it has now
    if (failed && group) await this._read(group.id);
    // `list` reads DC pump control again, for the banner
    if (p.warning === "dc_pump") await this._load();
  }

  private _choose(p: Parameter, kind: keyof Choices, on: boolean) {
    const stage = () => {
      const staged = this._staged ?? storedChoices(this._data!.groups);
      this._staged = { ...staged, [kind]: withKey(staged[kind], p.key, on) };
    };
    if (!(kind === "automations" && on && riskyForAutomations(p))) return stage();
    this._confirm = {
      title: texts.confirmAutomationTitle,
      body: html`<p><strong>${label(p)}</strong></p>
        <p class="banner warning">${texts.warnings[p.warning!]}</p>
        <p>${texts.confirmAutomationBody}</p>`,
      confirm: texts.confirmAutomation,
      action: stage,
    };
  }

  private _recommend() {
    const staged = this._staged ?? storedChoices(this._data!.groups);
    this._staged = { ...staged, sensors: new Set(this._data!.recommended) };
  }

  /** Run an action on the whole heat pump; its result or its error becomes the notice. */
  private async _run(busy: string, action: () => Promise<string>) {
    this._busy = busy;
    this._notice = null;
    this._edit = null;
    try {
      this._notice = { ok: true, text: await action() };
    } catch (err) {
      this._notice = { ok: false, text: message(err) };
    }
    this._busy = null;
  }

  private _apply() {
    return this._run(texts.applying, async () => {
      await this._call("set_choices", choicesRequest(this._staged!));
      this._staged = null;
      this._result = null;
      // The entry was reloaded: values of parameters without a sensor are gone until read again
      await this._load();
      if (this._entry?.loaded) for (const id of this._open) await this._read(id);
      return texts.applied;
    });
  }

  private _askBaseline() {
    this._confirm = {
      title: texts.setBaselineTitle,
      body: html`<p>${texts.setBaselineBody}</p>`,
      confirm: texts.setBaseline,
      action: () =>
        this._run(texts.settingBaseline, async () => {
          await this._call("set_baseline");
          await this._load();
          return texts.baselineSet;
        }),
    };
  }

  private _export() {
    return this._run(texts.exporting, async () => {
      const { parameters } = await this._call<{ parameters: ExportedParameter[] }>("export");
      const file = exportFile(this._entry!.title, new Date(), parameters);
      download(file.name, file.content);
      return texts.exported(file.name);
    });
  }

  private _confirmed() {
    const action = this._confirm!.action;
    this._confirm = null;
    action();
  }

  render() {
    const data = this._data;
    const staged = data ? (this._staged ?? storedChoices(data.groups)) : null;
    const changes = data && staged ? changeCount(storedChoices(data.groups), staged) : 0;
    const locked = changes > 0 || this._busy !== null || this._writing !== null;
    return html`<div class="page" style="color-scheme: ${this.hass?.themes?.darkMode ? "dark" : "light"}">
      <div class="header">
        <ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>
        <h1>${texts.title}</h1>
        ${data && data.entries.length > 1
          ? html`<select
              aria-label=${texts.heatPump}
              title=${changes > 0 ? texts.stagedFirst : ""}
              ?disabled=${locked}
              @change=${(ev: Event) => this._select((ev.target as HTMLSelectElement).value)}
            >
              ${data.entries.map(
                (entry) =>
                  html`<option value=${entry.entry_id} ?selected=${entry.entry_id === data.entry_id}>
                    ${entry.title}
                  </option>`,
              )}
            </select>`
          : nothing}
      </div>
      ${this._pinned()}
      <div class="content">
        <div class="inner">
          ${data && staged ? this._body(data, staged) : this._error ? nothing : html`<div class="note">${texts.loading}</div>`}
        </div>
      </div>
      ${changes > 0
        ? html`<div class="bar">
            <span><strong>${texts.staged(changes)}</strong> ${texts.applyHint}</span>
            <button class="btn" ?disabled=${this._busy !== null} @click=${() => (this._staged = null)}>
              ${texts.discard}
            </button>
            <button class="btn primary" ?disabled=${this._busy !== null} @click=${this._apply}>
              ${this._busy === texts.applying ? texts.applying : texts.apply}
            </button>
          </div>`
        : nothing}
      <dialog aria-labelledby="confirm-title" @close=${() => (this._confirm = null)}>
        ${this._confirm
          ? html`<h2 id="confirm-title">${this._confirm.title}</h2>
              ${this._confirm.body}
              <div class="buttons">
                <button class="btn" @click=${() => (this._confirm = null)}>${texts.cancel}</button>
                <button class="btn primary" @click=${this._confirmed}>${this._confirm.confirm}</button>
              </div>`
          : nothing}
      </dialog>
    </div>`;
  }

  /** What must not scroll out of view: the pump warning, and how the last action went. */
  private _pinned() {
    if (!this._data?.pump_manual && !this._error && !this._busy && !this._notice) return nothing;
    return html`<div class="pinned">
      ${this._data?.pump_manual
        ? html`<div class="banner warning pump" role="alert">
            <ha-icon icon="mdi:alert"></ha-icon><span>${texts.pumpManual}</span>
          </div>`
        : nothing}
      ${this._error
        ? html`<div class="banner error" role="alert">
            <span>${this._error}</span>
            <button class="btn" @click=${() => this._load()}>${texts.retry}</button>
          </div>`
        : nothing}
      ${this._busy ? html`<div class="banner" role="status"><span>${this._busy}</span></div>` : nothing}
      ${this._notice
        ? html`<div class="banner ${this._notice.ok ? "ok" : "error"}" role="status">
            <span>${this._notice.text}</span>
            <button class="btn" @click=${() => (this._notice = null)}>${texts.dismiss}</button>
          </div>`
        : nothing}
    </div>`;
  }

  private _body(data: ListResult, staged: Choices) {
    const entry = this._entry;
    if (!entry) return html`<div class="note">${texts.noEntries}</div>`;
    const views = filterGroups(data.groups, this._query, this._differing);
    const filtered = this._query.trim() !== "" || this._differing;
    const canRead = entry.loaded && this._busy === null;
    const context: RowContext = {
      idle: this._busy === null && this._writing === null && this._edit === null,
      staged,
      edit: this._edit,
      writing: this._writing,
      result: this._result,
      onEdit: (p) => {
        this._edit = p && { key: p.key, input: String(p.value) };
        this._result = null;
      },
      onInput: (input) => (this._edit = { ...this._edit!, input }),
      onSave: (p, value) => this._askWrite(p, value),
      onChoice: (p, kind, on) => this._choose(p, kind, on),
    };
    return html`${entry.loaded
        ? nothing
        : html`<div class="banner warning" role="alert"><span>${texts.notLoaded}</span></div>`}
      <div class="toolbar">
        <input
          type="search"
          placeholder=${texts.search}
          aria-label=${texts.search}
          .value=${this._query}
          @input=${(ev: Event) => this._filter({ _query: (ev.target as HTMLInputElement).value })}
        />
        <label>
          <input
            type="checkbox"
            .checked=${this._differing}
            @change=${(ev: Event) => this._filter({ _differing: (ev.target as HTMLInputElement).checked })}
          />${texts.differing}
        </label>
        <button class="btn" title=${texts.recommendedHint} ?disabled=${this._busy !== null} @click=${this._recommend}>
          ${texts.recommended}
        </button>
        <button class="btn" ?disabled=${!canRead} @click=${this._export}>${texts.export}</button>
      </div>
      <div class="toolbar">
        <span class="secondary baseline-text">
          ${data.baseline_set_at
            ? texts.baselineSetOn(
                new Date(data.baseline_set_at).toLocaleString(this.hass?.locale?.language, {
                  dateStyle: "medium",
                  timeStyle: "short",
                }),
              )
            : texts.baselineReference}
        </span>
        <button class="btn" ?disabled=${!canRead} @click=${this._askBaseline}>${texts.setBaseline}</button>
      </div>
      ${views.length
        ? views.map((view) => this._group(view, context, filtered, entry.loaded))
        : html`<div class="note">${texts.noMatches}</div>`}`;
  }

  private _group(view: GroupView, context: RowContext, filtered: boolean, loaded: boolean) {
    const { group, rows } = view;
    const open = this._open.has(group.id);
    const read = this._reads[group.id] ?? {};
    return html`<section class="group">
      <div class="group-head">
        <button class="toggle" aria-expanded=${open} @click=${() => this._toggle(group)}>
          <ha-icon icon="mdi:chevron-right"></ha-icon>
          <span>
            <span class="title">${group.title}</span>
            <span class="secondary count">
              ${filtered
                ? texts.shownOf(rows.length, group.parameters.length)
                : texts.parameters(group.parameters.length)}${view.unknown ? texts.unknownDiff(view.unknown) : ""}
            </span>
          </span>
        </button>
        ${open && loaded
          ? html`<button class="btn" ?disabled=${read.reading || this._busy !== null} @click=${() => this._read(group.id)}>
              ${texts.readAgain}
            </button>`
          : nothing}
      </div>
      ${open
        ? html`<div class="group-body ${read.reading ? "loading" : ""}">
            ${read.reading ? html`<div class="note" role="status">${texts.reading}</div>` : nothing}
            ${read.error
              ? html`<div class="banner error" role="alert"><span>${texts.readFailed(read.error)}</span></div>`
              : nothing}
            ${rows.length
              ? rows.map((p) => parameterRow(p, { ...context, idle: context.idle && !read.reading }))
              : html`<div class="note">${texts.noRows}</div>`}
          </div>`
        : nothing}
    </section>`;
  }
}

if (!customElements.get("adlar-parameters-panel")) {
  customElements.define("adlar-parameters-panel", AdlarParametersPanel);
}
