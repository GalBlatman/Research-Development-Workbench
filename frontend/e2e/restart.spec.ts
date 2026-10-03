import { expect, test } from "@playwright/test";
import { execFileSync, spawn, type ChildProcess } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, dirname, join, resolve } from "node:path";
import { once } from "node:events";
import { createHash } from "node:crypto";

test("private pilot backend process restart preserves revision and immutable review", async ({
  page,
}) => {
  const runtime = mkdtempSync(join(tmpdir(), "rdw-pilot-restart-"));
  const backend = resolve("../backend");
  const python = join(
    backend,
    ".venv",
    process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
  );
  let processHandle: ChildProcess | undefined;
  async function start() {
    processHandle = spawn(
      python,
      [
        "-m",
        "uvicorn",
        "api.app:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8001",
        "--no-access-log",
        "--log-level",
        "warning",
      ],
      {
        cwd: backend,
        env: {
          ...process.env,
          RDW_RUNTIME_ROOT: runtime,
          RDW_DATABASE_MODE: "local-sqlite",
          RDW_PROVIDER: "fake",
        },
        stdio: "ignore",
      },
    );
    for (let attempt = 0; attempt < 100; attempt++) {
      try {
        const health = await fetch("http://127.0.0.1:8001/api/health");
        if (health.ok) return;
      } catch {
        /* Wait for this synthetic process to bind. */
      }
      if (processHandle.exitCode !== null)
        throw new Error("Synthetic backend failed to start");
      await new Promise((done) => setTimeout(done, 100));
    }
    throw new Error("Synthetic backend startup timed out");
  }
  async function stop() {
    if (processHandle && processHandle.exitCode === null) {
      const ended = once(processHandle, "exit");
      if (process.platform === "win32") {
        // The Windows venv launcher has a child Python process. Stop only this test's tree.
        execFileSync(
          "taskkill",
          ["/PID", String(processHandle.pid), "/T", "/F"],
          { windowsHide: true, stdio: "ignore" },
        );
      } else processHandle.kill("SIGTERM");
      await ended;
    }
    processHandle = undefined;
    let stopped = false;
    for (let attempt = 0; attempt < 30; attempt++) {
      try {
        await fetch("http://127.0.0.1:8001/api/health");
      } catch {
        stopped = true;
        break;
      }
      await new Promise((done) => setTimeout(done, 100));
    }
    if (!stopped) throw new Error("Synthetic backend tree did not stop");
  }
  try {
    await start();
    await page.route("**/api/**", async (route) => {
      const url = new URL(route.request().url());
      url.protocol = "http:";
      url.hostname = "127.0.0.1";
      url.port = "8001";
      const response = await route.fetch({ url: url.toString() });
      await route.fulfill({ response });
    });
    await page.goto("/");
    await page.getByRole("button", { name: "Load synthetic example" }).click();
    await page.getByLabel("I authorize local processing").check();
    await page
      .getByRole("button", { name: "Create project", exact: true })
      .click();
    await page.getByRole("button", { name: "Accept representation" }).click();
    await page.getByLabel("I am authorized to process").check();
    await page.getByRole("button", { name: "Add source", exact: true }).click();
    await page.getByRole("button", { name: "Run fake evaluation" }).click();
    const review = page.getByLabel("Evaluation review");
    await expect(review).toBeVisible();
    await review
      .getByText("Deterministic rule trace and exact backend results")
      .click();
    const immutable = await review.locator("details pre").textContent();
    await page
      .getByLabel("Edit original idea")
      .fill("Synthetic revision preserved across process restart.");
    await page.getByRole("button", { name: "Save new revision" }).click();
    await expect(review).toContainText("Historical review");
    let modelRequests = 0;
    page.on("request", (request) => {
      if (
        request.method() === "POST" &&
        /evaluations|workspace-proposals|workspace-checks/.test(request.url())
      )
        modelRequests++;
    });
    await stop();
    await start();
    await page.getByRole("button", { name: "Reload saved project" }).click();
    await expect(page.getByLabel("Edit original idea")).toHaveValue(
      "Synthetic revision preserved across process restart.",
    );
    await page.getByRole("button", { name: /Open review of revision/ }).click();
    await expect(review).toContainText("Historical review");
    await review
      .getByText("Deterministic rule trace and exact backend results")
      .click();
    expect(await review.locator("details pre").textContent()).toBe(immutable);
    expect(modelRequests).toBe(0);
    const exportLink = await page
      .getByRole("link", { name: "Export JSON", exact: true })
      .getAttribute("href");
    expect(exportLink).toBeTruthy();
    const exportUrl = new URL(exportLink!, "http://127.0.0.1:8001");
    exportUrl.port = "8001";
    const exported = await page.request.get(exportUrl.toString());
    expect(exported.ok()).toBeTruthy();
    expect(exported.headers()["content-disposition"]).toContain("attachment");
    const archive = await exported.json();
    expect(archive.project_history.revisions.at(-1).revision).toBe(5);
    expect(archive.reviews[0].snapshot.project.revision).toBe(4);
    const revisedSource = archive.import_bundle.versions.find(
      (version: { document: { version: number; role: string } }) =>
        version.document.version === 2 &&
        version.document.role === "project_draft",
    );
    expect(revisedSource.document.content_sha256).toBe(
      createHash("sha256")
        .update("Synthetic revision preserved across process restart.")
        .digest("hex"),
    );
    expect(revisedSource.text).toBeNull();
  } finally {
    await stop();
    if (
      dirname(resolve(runtime)) !== resolve(tmpdir()) ||
      !basename(runtime).startsWith("rdw-pilot-restart-")
    )
      throw new Error("Unexpected synthetic cleanup target");
    rmSync(runtime, {
      recursive: true,
      force: true,
      maxRetries: 10,
      retryDelay: 100,
    });
  }
});
