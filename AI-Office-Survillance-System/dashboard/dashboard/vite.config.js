import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server + preview both on 5174 so it matches the backend CORS origin.
export default defineConfig({
  plugins: [react()],
  server: { port: 5174, host: true },
  preview: { port: 5174, host: true },
});
