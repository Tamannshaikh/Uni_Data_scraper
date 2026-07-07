import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import tsConfigPaths from "vite-tsconfig-paths";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import { nitro } from "nitro/vite";

export default defineConfig({
  plugins: [
    tsConfigPaths(),
    tailwindcss(),
    tanstackStart({
      server: {
        entry: "server",
      },
    }),
    nitro({
      preset: "vercel",
      routeRules: {
        '/api/v1/**': { proxy: 'https://tamanna1234-uniscraper-backend.hf.space/api/v1/**' }
      }
    }),
    react(),
  ],
  server: {
    port: 5173,
    proxy: {
      // Proxy API calls to the FastAPI backend during development
      "/api": {
        target: "https://tamanna1234-uniscraper-backend.hf.space",
        changeOrigin: true,
      },
    },
  },
});
