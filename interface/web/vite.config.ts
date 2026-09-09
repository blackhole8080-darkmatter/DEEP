import { defineConfig } from "vite";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const configDir = dirname(fileURLToPath(import.meta.url));

// DEEP modern frontend build config.
// - Dev: `npm run dev` serves with HMR, proxying API + WS to the running
//   FastAPI server on :5174 so the new UI talks to the real backend.
// - Prod: `npm run build` emits hashed assets into ../static/app-dist, which
//   FastAPI already serves via the /static mount. The shell is then reachable
//   at /app (see the route in interface/server.py). The legacy UI this once
//   sat beside is gone — static/ now holds only app-dist, icons and the
//   service worker — so /app and / are the whole of the front end.
export default defineConfig(({ command }) => ({
  base: command === "build" ? "/static/app-dist/" : "/",
  build: {
    outDir: resolve(configDir, "../static/app-dist"),
    emptyOutDir: true,
    sourcemap: true,
  },
  server: {
    port: 5174,
    proxy: {
      "/api": { target: "http://127.0.0.1:5174", changeOrigin: true },
      "/ws": { target: "ws://127.0.0.1:5174", ws: true },
      "/network": { target: "http://127.0.0.1:5174", changeOrigin: true },
    },
  },
}));
