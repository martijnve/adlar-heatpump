import { css } from "lit";

// Home Assistant's theme variables only, so the panel follows the light and the dark theme.
export const styles = css`
  :host {
    display: block;
    height: 100dvh;
    color: var(--primary-text-color);
    background: var(--primary-background-color);
  }
  .page {
    display: flex;
    flex-direction: column;
    height: 100%;
    container-type: inline-size;
  }
  .header {
    display: flex;
    align-items: center;
    gap: 8px;
    box-sizing: border-box;
    height: var(--header-height, 56px);
    padding: 0 12px;
    flex: none;
    color: var(--app-header-text-color, var(--primary-text-color));
    background: var(--app-header-background-color, var(--primary-color));
    border-bottom: var(--app-header-border-bottom, none);
  }
  h1 {
    flex: 1;
    min-width: 0;
    margin: 0 4px;
    font-size: 20px;
    font-weight: 400;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .header select {
    flex: 0 1 auto;
    min-width: 0;
    max-width: 50%;
  }
  @container (max-width: 520px) {
    /* The selector gets a line of its own under the title */
    .header {
      flex-wrap: wrap;
      height: auto;
      min-height: var(--header-height, 56px);
    }
    .header select {
      flex: 1 1 100%;
      max-width: none;
      margin-bottom: 8px;
    }
  }
  .content {
    flex: 1;
    overflow-y: auto;
  }
  .inner,
  .pinned {
    box-sizing: border-box;
    width: 100%;
    max-width: 1100px;
    margin: 0 auto;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .pinned {
    flex: none;
    padding-bottom: 12px;
  }

  /* Controls */
  button,
  input,
  select {
    font: inherit;
    color: var(--primary-text-color);
  }
  .btn {
    height: 36px;
    padding: 0 12px;
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    background: transparent;
    color: var(--primary-color);
    font-weight: 500;
    white-space: nowrap;
    cursor: pointer;
  }
  .btn.primary {
    border-color: transparent;
    background: var(--primary-color);
    color: var(--text-primary-color, #fff);
  }
  .btn:disabled {
    opacity: 0.45;
    cursor: default;
  }
  input[type="search"],
  input[type="number"],
  select {
    box-sizing: border-box;
    height: 36px;
    padding: 0 8px;
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    background: var(--card-background-color);
  }
  input[type="checkbox"] {
    width: 18px;
    height: 18px;
    margin: 0;
    flex: none;
    accent-color: var(--primary-color);
  }
  :is(button, input, select, .toggle):focus-visible {
    outline: 2px solid var(--primary-color);
    outline-offset: 1px;
  }
  label {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
  }
  .secondary {
    color: var(--secondary-text-color);
    font-size: 0.875rem;
    line-height: 1.35;
  }

  /* Banners */
  .banner {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    border-radius: 8px;
    border-left: 4px solid var(--info-color, var(--primary-color));
    background: color-mix(in srgb, var(--info-color, var(--primary-color)) 12%, var(--card-background-color));
    line-height: 1.4;
  }
  .banner > span {
    flex: 1;
  }
  .banner.warning {
    border-color: var(--warning-color);
    background: color-mix(in srgb, var(--warning-color) 16%, var(--card-background-color));
  }
  .banner.error {
    border-color: var(--error-color);
    background: color-mix(in srgb, var(--error-color) 14%, var(--card-background-color));
  }
  .banner.ok {
    border-color: var(--success-color);
    background: color-mix(in srgb, var(--success-color) 14%, var(--card-background-color));
  }
  .banner.pump {
    font-weight: 500;
  }

  /* Search, filter and the actions on all parameters */
  .toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px 12px;
  }
  .toolbar input[type="search"] {
    flex: 1 1 16rem;
    min-width: 0;
  }
  .toolbar .baseline-text {
    flex: 1 1 14rem;
  }

  /* Groups */
  .group {
    border: 1px solid var(--divider-color);
    border-radius: var(--ha-card-border-radius, 12px);
    background: var(--card-background-color);
    overflow: hidden;
  }
  .group-head {
    display: flex;
    align-items: center;
    gap: 8px;
    padding-right: 12px;
  }
  .toggle {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 8px 12px 12px;
    border: 0;
    background: none;
    text-align: left;
    cursor: pointer;
  }
  .toggle ha-icon {
    flex: none;
    color: var(--secondary-text-color);
    transition: transform 0.15s;
  }
  .toggle[aria-expanded="true"] ha-icon {
    transform: rotate(90deg);
  }
  .toggle .title {
    font-weight: 500;
  }
  .toggle .count {
    display: block;
    font-weight: 400;
  }
  .group-body {
    border-top: 1px solid var(--divider-color);
  }
  .group-body > .banner,
  .group-body > .note {
    margin: 12px;
  }
  .note {
    color: var(--secondary-text-color);
  }

  /* One parameter */
  .row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 17rem) 11rem;
    gap: 8px 20px;
    padding: 12px 16px 12px 13px;
    border-left: 3px solid transparent;
  }
  .row + .row {
    border-top: 1px solid var(--divider-color);
  }
  .row.differs {
    border-left-color: var(--accent-color);
  }
  .loading .row {
    opacity: 0.55;
  }
  .what {
    display: flex;
    gap: 8px;
  }
  .name {
    font-weight: 500;
  }
  .code {
    flex: none;
    min-width: 2.8rem;
    color: var(--secondary-text-color);
    font-variant-numeric: tabular-nums;
  }
  .value {
    display: flex;
    flex-direction: column;
    gap: 4px;
    min-width: 0;
  }
  .current,
  .editor {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    min-height: 36px;
  }
  .number {
    flex: 1;
    min-width: 0;
    font-size: 1.05rem;
    font-weight: 500;
    font-variant-numeric: tabular-nums;
    overflow-wrap: anywhere;
  }
  .editor input {
    width: 5rem;
  }
  .editor select {
    flex: 1 1 100%;
    min-width: 0;
    max-width: 100%;
  }
  .tag,
  .pill {
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 0.75rem;
    white-space: nowrap;
  }
  .tag {
    color: var(--secondary-text-color);
    border: 1px solid var(--divider-color);
  }
  .pill {
    color: var(--text-accent-color, #fff);
    background: var(--accent-color);
  }
  .baseline {
    font-size: 0.875rem;
  }
  .result {
    font-size: 0.875rem;
    line-height: 1.35;
    overflow-wrap: anywhere;
  }
  .result.ok {
    color: var(--success-color);
  }
  .result.error {
    color: var(--error-color);
  }
  .choices {
    display: flex;
    flex-direction: column;
    gap: 8px;
    font-size: 0.875rem;
  }
  .choices label.staged {
    color: var(--primary-color);
    font-weight: 500;
  }
  .choices label.staged::after {
    content: "•";
  }
  @container (max-width: 760px) {
    .inner {
      padding: 12px 8px;
    }
    .pinned {
      padding: 12px 8px;
    }
    .row {
      grid-template-columns: minmax(0, 1fr);
    }
    .choices {
      flex-direction: row;
      flex-wrap: wrap;
      gap: 8px 20px;
    }
  }

  /* Staged choices */
  .bar {
    flex: none;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: flex-end;
    gap: 8px 12px;
    padding: 10px 16px;
    border-top: 1px solid var(--divider-color);
    background: var(--card-background-color);
    box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.12);
  }
  .bar > span {
    flex: 1 1 14rem;
  }

  /* Confirmations */
  dialog {
    box-sizing: border-box;
    width: min(30rem, calc(100vw - 32px));
    padding: 20px;
    border: 0;
    border-radius: var(--ha-card-border-radius, 12px);
    color: var(--primary-text-color);
    background: var(--card-background-color);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
  }
  dialog::backdrop {
    background: rgba(0, 0, 0, 0.5);
  }
  dialog h2 {
    margin: 0 0 12px;
    font-size: 1.25rem;
    font-weight: 400;
  }
  dialog p {
    margin: 0 0 12px;
    line-height: 1.4;
  }
  dialog dl {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    gap: 6px 16px;
    margin: 0 0 12px;
  }
  dialog dt {
    color: var(--secondary-text-color);
  }
  dialog dd {
    margin: 0;
    font-weight: 500;
    overflow-wrap: anywhere;
  }
  dialog .buttons {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 20px;
  }
`;
