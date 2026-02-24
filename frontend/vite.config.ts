import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 3000,
    proxy: {
      "/api": "http://localhost:5001",
      "/socket.io": {
        target: "http://localhost:5001",
        ws: true,
      },
    },
  },
  build: {
    outDir: "../static",
    emptyOutDir: true,
  },
});
