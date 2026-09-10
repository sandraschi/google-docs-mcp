import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// VITE_API_TARGET lets the fleet-start engine (fleet-start.config.ps1's
// Frontend.ApiTargetEnv) or local dev override the backend origin without
// editing this file — e.g. when the default port is unexpectedly occupied.
const apiTarget = process.env.VITE_API_TARGET || "http://127.0.0.1:11972";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 11973,
    strictPort: true,
    proxy: {
      "/api": { target: apiTarget, changeOrigin: true },
      "/skill": { target: apiTarget, changeOrigin: true },
      "/mcp": { target: apiTarget, changeOrigin: true, ws: true },
    },
  },
});
