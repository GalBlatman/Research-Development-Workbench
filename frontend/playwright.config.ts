import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  reporter: "list",
  use: { baseURL: "http://127.0.0.1:5173", headless: true },
  webServer: [
    {
      command: "node e2e/server.mjs",
      url: "http://127.0.0.1:8000/api/health",
      reuseExistingServer: false,
      timeout: 60000,
    },
    {
      command: "pnpm dev",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: false,
      timeout: 60000,
    },
  ],
});
