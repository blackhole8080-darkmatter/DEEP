import { defineConfig } from "vite";
import { resolve } from "path";

// DEEP modern frontend build config.
// - Dev: `npm run dev` serves with HMR, proxying API + WS to the running
//   FastAPI server on :7768 so the new UI talks to the real backend.
// - Prod: `npm run build` emits hashed assets into ../static/app-dist, which
//   FastAPI already serves via the /static mount. The shell is then reachable
//   at /app (see the new route in interface/server.py) with ZERO impact on the
//   legacy UI at /ai.
export default defineConfig({
  base: "/static/app-dist/",
  build: {
    outDir: resolve(__dirname, "../static/app-dist"),
    emptyOutDir: true,
    sourcemap: true,
  },
  server: {
    port: 5174,
    proxy: {
      "/api": { target: "http://127.0.0.1:7768", changeOrigin: true },
      "/ws": { target: "ws://127.0.0.1:7768", ws: true },
    },
  },
});
