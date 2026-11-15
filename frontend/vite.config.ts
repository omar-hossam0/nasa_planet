import { defineConfig } from "vite";

export default defineConfig({
  base: "./",
  build: { outDir: "../dist/product", emptyOutDir: true },
  server: {
    proxy: {
      "/v1": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
    },
  },
});
