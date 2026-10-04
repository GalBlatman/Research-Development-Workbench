import { expect, test } from "@playwright/test";

test("synthetic browser -> real backend -> review, immutable edit, export and reload", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Load synthetic example" }).click();
  await page.getByLabel("I authorize local processing").check();
  await page
    .getByRole("button", { name: "Create project", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Structured interpretation" }),
  ).toBeVisible();
  await expect(page.getByText("Origin: model_inference")).toContainText(
    "Evidence: not_inspected",
  );
  await expect(
    page
      .getByLabel("Overview workspace")
      .getByText("Why do fictional teams share knowledge?", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Accept representation" }).click();
  await expect(page.getByText("Origin: model_inference")).toContainText(
    "Adoption: accepted",
  );
  await expect(page.getByText("Origin: model_inference")).toContainText(
    "Evidence: not_inspected",
  );
  await page.getByLabel("I am authorized to process").check();
  await page.getByRole("button", { name: "Add source", exact: true }).click();
  await expect(
    page.getByText("Synthetic predecessor · version 1"),
  ).toBeVisible();
  await page
    .getByRole("button", { name: /Inspect Synthetic predecessor/ })
    .click();
  await expect(page.getByLabel("Source passage")).toContainText(
    "not a published article",
  );
  await page.getByRole("button", { name: "Run fake evaluation" }).click();
  const review = page.getByLabel("Evaluation review");
  await expect(review).toBeVisible();
  await expect(
    review.locator("tbody tr").filter({
      has: page.getByRole("rowheader", { name: "idea", exact: true }),
    }),
  ).toContainText("50");
  await expect(review).toContainText("pending");
  await review
    .getByText("Deterministic rule trace and exact backend results")
    .click();
  await expect(review).toContainText("ROUTE-TOTAL");
  const snapshot = await review.locator("details pre").textContent();
  for (const name of ["Export Markdown", "Export JSON"]) {
    const download = page.waitForEvent("download");
    await page.getByRole("link", { name, exact: true }).click();
    const file = await download;
    expect(await file.failure()).toBeNull();
    const stream = await file.createReadStream();
    const chunks: Buffer[] = [];
    if (stream) for await (const chunk of stream) chunks.push(chunk as Buffer);
    const output = Buffer.concat(chunks).toString("utf8");
    expect(output).toContain("Fake fixture output");
    expect(output).not.toContain("original_storage_reference");
    if (name === "Export JSON")
      expect(JSON.parse(output).schema_version).toBe("rdw-app-1");
  }
  await page
    .getByLabel("Edit original idea")
    .fill("Synthetic revised question without assessed science.");
  await page.getByRole("button", { name: "Save new revision" }).click();
  await expect(review).toContainText("Historical review");
  expect(await review.locator("details pre").textContent()).toBe(snapshot);
  await page.getByRole("button", { name: "Reload saved project" }).click();
  await expect(page.getByLabel("Edit original idea")).toHaveValue(
    "Synthetic revised question without assessed science.",
  );
  await page.getByRole("button", { name: /Open review of revision/ }).click();
  await expect(page.getByLabel("Evaluation review")).toContainText(
    "Historical review",
  );
  await page.getByRole("button", { name: "Run fake evaluation" }).click();
  // Changed input selects the internal limited response; pending is not zero.
  await expect(
    page.getByLabel("Evaluation review").locator("tbody"),
  ).toContainText("pending");
  await expect(page.getByLabel("Fake evaluation fixture")).toHaveCount(0);
});

test("ESTABLISH displays not applicable and safely renders pasted markup", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("Project title").fill("Synthetic discovery");
  await page
    .getByLabel("Your idea or description")
    .fill(
      "<script>window.syntheticInjection=true</script> Unassessed description.",
    );
  await page.getByLabel("Contribution route").selectOption("ESTABLISH");
  await page.getByLabel("I authorize local processing").check();
  await page
    .getByRole("button", { name: "Create project", exact: true })
    .click();
  await page.getByRole("button", { name: "Run fake evaluation" }).click();
  await expect(
    page.getByLabel("Evaluation review").locator("tbody"),
  ).toContainText("not_applicable");
  await expect(
    page.getByLabel("Evaluation review").locator("tbody"),
  ).toContainText("pending");
  await expect(page.getByLabel("Readiness gates")).toContainText(
    "NOT_APPLICABLE",
  );
  expect(await page.evaluate(() => "syntheticInjection" in window)).toBe(false);
});

test("run-handle UI polls a stored backend review and surfaces bounded failure", async ({
  page,
}) => {
  const demo = await (await page.request.get("/api/demo")).json();
  let view = await (
    await page.request.post("/api/projects", {
      data: {
        title: "Synthetic run UI",
        idea: demo.idea,
        route: "EXPLAIN",
        stage: "EARLY IDEA",
        authorized: true,
      },
    })
  ).json();
  const root = "/api/projects/" + view.project.project_id;
  view = await (
    await page.request.post(root + "/sources", {
      data: {
        expected_revision: view.project.revision,
        title: "Synthetic excerpt",
        attribution: "Synthetic fixture only",
        text: demo.source,
        authorized: true,
        admitted: true,
      },
    })
  ).json();
  const review = await (
    await page.request.post(root + "/evaluations", {
      data: { expected_revision: view.project.revision },
    })
  ).json();
  let failed = false;
  const handle = {
    run_id: "a".repeat(32),
    project_id: view.project.project_id,
    expected_revision: view.project.revision,
    state: "queued",
  };
  // Mock the asynchronous wire protocol only. The displayed historical score comes from the real backend.
  await page.route("**/api/health", (route) =>
    route.fulfill({ json: { status: "ok", model: "openai:gpt-6-sol" } }),
  );
  await page.route("**" + root + "/evaluations", (route) =>
    route.fulfill({ status: 202, json: handle }),
  );
  await page.route("**" + root + "/runs/" + handle.run_id, (route) =>
    route.fulfill({
      json: {
        ...handle,
        state: failed ? "failed" : "succeeded",
        snapshot_id: failed ? null : review.snapshot.snapshot_id,
        error_code: failed ? "BUDGET_EXHAUSTED" : null,
      },
    }),
  );
  await page.goto("/?project=" + view.project.project_id);
  await expect(
    page.getByRole("heading", { name: "Structured interpretation" }),
  ).toBeVisible();
  await expect(page.getByText(/Zero Data Retention requires/)).toBeVisible();
  await page
    .getByRole("button", { name: "Run evaluation", exact: true })
    .click();
  await expect(page.getByLabel("Evaluation review")).toContainText("50");
  failed = true;
  await page
    .getByRole("button", { name: "Run evaluation", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("BUDGET_EXHAUSTED");
  await expect(page.getByLabel("Evaluation review")).toContainText("50");
});

for (const route of ["EXPLAIN", "ESTABLISH", "TEST"]) {
  test(`${route} shows route assessment basis and provisional gates`, async ({
    page,
  }) => {
    await page.goto("/");
    await page.getByLabel("Project title").fill(`Synthetic ${route} basis`);
    await page
      .getByLabel("Your idea or description")
      .fill("Synthetic unresolved handoff premise; no inspected evidence.");
    await page.getByLabel("Contribution route").selectOption(route);
    await page.getByLabel("I authorize local processing").check();
    await page
      .getByRole("button", { name: "Create project", exact: true })
      .click();
    await page.getByRole("button", { name: "Run fake evaluation" }).click();
    const basis = page.getByLabel("Route assessment basis");
    await expect(basis.locator("li")).toHaveCount(6);
    await expect(basis).toContainText("knowledge_need");
    await expect(basis).toContainText("next_use");
    await expect(basis).toContainText("NOT INSPECTED");
    await expect(basis).toContainText("checking: unresolved");
    await expect(basis).toContainText("Fixed fake fixture");
    await expect(page.getByLabel("Evaluation review")).toContainText(
      "Account articulated:",
    );
    await expect(page.getByLabel("Readiness gates")).toContainText("UNKNOWN");
  });
}
