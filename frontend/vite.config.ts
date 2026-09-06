import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The FastAPI service (server.py) runs on :8000 and owns /api.
// In dev, Vite serves the UI on :5173 and proxies /api through.
// `npm run build` emits ../frontend/dist, which server.py serves in production.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
