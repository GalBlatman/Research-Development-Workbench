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
    page.getByText("Why do fictional teams share knowledge?", { exact: true }),
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
  // Reload resets the default to limited: pending results display without zero substitution.
  await expect(
    page.getByLabel("Evaluation review").locator("tbody"),
  ).toContainText("pending");
  await page.getByLabel("Fake evaluation fixture").selectOption("scored");
  await page.getByRole("button", { name: "Run fake evaluation" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Invalid fake-model evaluation",
  );
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
  expect(await page.evaluate(() => "syntheticInjection" in window)).toBe(false);
});
