import { expect, it } from "vitest";
import "./adlar-parameters-panel";
import { AdlarParametersPanel } from "./adlar-parameters-panel";

it("defines the element and renders the heading", () => {
  expect(customElements.get("adlar-parameters-panel")).toBe(AdlarParametersPanel);
  const result = new AdlarParametersPanel().render();
  expect(result.strings.join("")).toContain("<h1>Heat pump parameters</h1>");
});
