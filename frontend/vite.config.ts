import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: { port: 5173 },
  build: {
    // Split heavy vendor code so the initial route stays small and chunks
    // cache independently on Vercel's CDN.
    rollupOptions: {
      output: {
        manualChunks: {
          "react-vendor": ["react", "react-dom", "react-router-dom"],
          "motion-vendor": ["framer-motion"],
          "web3-vendor": ["wagmi", "viem", "@tanstack/react-query"],
        },
      },
    },
    chunkSizeWarningLimit: 900,
  },
});
