/// <reference types="vitest/config" />
import path from "node:path";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    // shadcn/ui-generated components import via "@/..." — kept pointed at
    // src/ as a whole (not e.g. src/presentation/) so it composes with our
    // existing relative imports across domain/application/adapters/etc.
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    // 5180, not the Vite default 5173: that port is already used by
    // another project on this machine.
    port: 5180,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
  },
});
