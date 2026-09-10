import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 11973,
    strictPort: true,
    proxy: {
      "/api": { target: "http://127.0.0.1:11972", changeOrigin: true },
      "/skill": { target: "http://127.0.0.1:11972", changeOrigin: true },
      "/mcp": {
        target: "http://127.0.0.1:11972",
        changeOrigin: true,
        ws: true,
      },
    },
  },
});
