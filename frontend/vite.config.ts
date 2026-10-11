import { defineConfig } from "vite";

// One ES module, served by the integration (custom_components/adlar_heatpump/frontend).
export default defineConfig({
  build: {
    lib: {
      entry: "src/adlar-parameters-panel.ts",
      formats: ["es"],
      fileName: () => "adlar-parameters-panel.js",
    },
    outDir: "../custom_components/adlar_heatpump/frontend",
    emptyOutDir: true,
    target: "es2022",
    minify: true,
    sourcemap: false,
  },
});
