import { LitElement, html } from "lit";

/** Admin panel for the installer parameters; the real UI comes in a later step. */
export class AdlarParametersPanel extends LitElement {
  // Set by Home Assistant on a custom panel.
  static properties = {
    hass: { attribute: false },
    narrow: { type: Boolean },
    route: { attribute: false },
    panel: { attribute: false },
  };

  hass?: unknown;
  narrow = false;
  route?: unknown;
  panel?: unknown;

  render() {
    return html`<h1>Heat pump parameters</h1><p>Coming soon</p>`;
  }
}

if (!customElements.get("adlar-parameters-panel")) {
  customElements.define("adlar-parameters-panel", AdlarParametersPanel);
}
