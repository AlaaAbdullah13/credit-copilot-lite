import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/login": "http://localhost:8000",
      "/ingest": "http://localhost:8000",
      "/query": "http://localhost:8000",
      "/assess": "http://localhost:8000",
      "/approve": "http://localhost:8000",
      "/reject": "http://localhost:8000",
      "/issue": "http://localhost:8000",
    },
  },
});
