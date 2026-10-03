import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, dirname, join, resolve } from "node:path";
import { spawn } from "node:child_process";

const runtime = mkdtempSync(join(tmpdir(), "rdw-synthetic-e2e-"));
const child = spawn(
  "uv",
  [
    "run",
    "--locked",
    "uvicorn",
    "api.app:app",
    "--host",
    "127.0.0.1",
    "--port",
    "8000",
    "--no-access-log",
  ],
  {
    cwd: "../backend",
    env: {
      ...process.env,
      RDW_RUNTIME_ROOT: runtime,
      RDW_DATABASE_MODE: "local-sqlite",
      RDW_PROVIDER: "fake",
    },
    stdio: "inherit",
  },
);
process.on("SIGTERM", () => {
  child.kill();
});
process.on("SIGINT", () => {
  child.kill();
});
child.on("exit", (code) => {
  if (
    dirname(resolve(runtime)) !== resolve(tmpdir()) ||
    !basename(runtime).startsWith("rdw-synthetic-e2e-")
  )
    throw new Error("Unexpected cleanup target");
  rmSync(runtime, { recursive: true, force: true });
  process.exit(code ?? 0);
});
