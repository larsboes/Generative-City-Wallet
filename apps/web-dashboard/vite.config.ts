import path from "node:path";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react()],
  server: { port: 3000 },
  resolve: {
    dedupe: ["react", "react-dom"],
    alias: {
      "@spark/shared": path.resolve(__dirname, "../../packages/shared/src/index.ts"),
    },
  },
});
