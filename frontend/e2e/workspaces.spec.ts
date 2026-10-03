import { test, expect, type Page } from "@playwright/test";

async function setup(page: Page, route = "EXPLAIN") {
  const demo = await (await page.request.get("/api/demo")).json();
  let view = await (
    await page.request.post("/api/projects", {
      data: {
        title: "Synthetic workspace project",
        idea: demo.idea,
        route,
        stage: "EARLY IDEA",
        authorized: true,
        session_goal: "Clarify the next bounded research task",
      },
    })
  ).json();
  const root = "/api/projects/" + view.project.project_id;
  view = await (
    await page.request.post(root + "/sources", {
      data: {
        expected_revision: view.project.revision,
        title: "Synthetic source",
        attribution: "Synthetic fixture only",
        text: demo.source,
        authorized: true,
        admitted: true,
      },
    })
  ).json();
  await page.goto("/?project=" + view.project.project_id);
  await expect(
    page.getByRole("navigation", { name: "Research workspaces" }),
  ).toBeVisible();
  return { view, root, demo };
}

async function workspace(page: Page, name: string) {
  await page
    .getByRole("navigation", { name: "Research workspaces" })
    .getByRole("button", { name, exact: true })
    .click();
  await expect(
    page.getByLabel(name + " workspace", { exact: true }),
  ).toBeVisible();
}

test("all workspaces share state; navigation preserves unsaved notes and offline actions", async ({
  page,
}) => {
  const { root } = await setup(page);
  for (const name of [
    "Overview",
    "Brief",
    "Literature",
    "Argument",
    "Alternatives",
    "Study",
    "Usefulness",
    "Review",
    "Next Actions",
    "History",
  ])
    await workspace(page, name);
  await workspace(page, "Alternatives");
  await page
    .getByLabel("Record title", { exact: true })
    .fill("Incentive alternative");
  await page
    .getByLabel("Alternative account", { exact: true })
    .fill("Shared incentives could explain this synthetic pattern");
  await page
    .getByLabel("What it implies", { exact: true })
    .fill(
      "Changed incentives rather than requests would distinguish this account",
    );
  await workspace(page, "Usefulness");
  await workspace(page, "Alternatives");
  await expect(
    page.getByLabel("Alternative account", { exact: true }),
  ).toHaveValue(/Shared incentives/);
  await page
    .getByRole("button", { name: "Save alternatives record", exact: true })
    .click();
  await expect(
    page.getByRole("article", { name: "Incentive alternative" }),
  ).toContainText("user_text");
  await page.getByText("Add a research record", { exact: true }).click();
  await page
    .getByLabel("Record title", { exact: true })
    .fill("Understanding alternative");
  await page
    .getByLabel("Alternative account", { exact: true })
    .fill("Shared understanding is a separate plausible synthetic assumption");
  await page
    .getByLabel("Discriminating evidence needed", { exact: true })
    .fill("Compare independent changes in incentives and requests");
  await page
    .getByRole("button", { name: "Save alternatives record", exact: true })
    .click();
  await expect(
    page.getByRole("article", { name: "Understanding alternative" }),
  ).toBeVisible();
  const view = await (await page.request.get(root)).json();
  expect(
    view.project.objects.filter(
      (o: { payload: { workspace?: string } }) =>
        o.payload.workspace === "Alternatives",
    ),
  ).toHaveLength(2);
  await workspace(page, "Next Actions");
  await page
    .getByRole("button", { name: "Propose bounded action", exact: true })
    .click();
  const action = page.getByRole("article", {
    name: "Proposed Next Actions note",
  });
  await expect(action).toContainText("Unresolved judgment it can change");
  await expect(action).toContainText("Required input / evidence");
  await expect(action).toContainText("Expected deliverable");
  await action
    .getByRole("button", { name: "Reject suggestion", exact: true })
    .click();
  await expect(action).toContainText("rejected");
  await page.reload();
  await workspace(page, "Alternatives");
  await expect(
    page.getByRole("article", { name: "Understanding alternative" }),
  ).toBeVisible();
});

test("literature keeps source claims, interpretation and inference separate through source versions", async ({
  page,
}) => {
  const { root, demo } = await setup(page);
  await workspace(page, "Literature");
  const view = await (await page.request.get(root)).json();
  const source = view.sources.find(
    (s: { source: { role: string } }) => s.source.role === "literature",
  );
  await page
    .getByLabel("Record title", { exact: true })
    .fill("Predecessor comparison");
  await page
    .getByLabel("What the source claims", { exact: true })
    .fill(demo.source);
  await page
    .getByLabel("User interpretation", { exact: true })
    .fill("My interpretation is tentative");
  await page
    .getByLabel("Model synthesis / unresolved inference", { exact: true })
    .fill("No model synthesis has been inspected");
  await page
    .getByLabel("Relation to the project", { exact: true })
    .selectOption("closest predecessor");
  await page
    .getByLabel("Overlap / departure", { exact: true })
    .selectOption("unresolved overlap");
  await page
    .getByLabel("Supporting passage", { exact: true })
    .selectOption(source.source.document_id);
  await page
    .getByRole("button", { name: "Save literature record", exact: true })
    .click();
  const card = page.getByRole("article", { name: "Predecessor comparison" });
  await expect(card).toContainText("closest predecessor");
  await expect(card).toContainText("My interpretation is tentative");
  await expect(card).toContainText("No model synthesis has been inspected");
  await card.getByRole("button", { name: "Open linked source v1" }).click();
  await expect(page.getByLabel("Linked source reader")).toContainText(
    demo.source,
  );
  await page.getByRole("button", { name: "Close source reader" }).click();
  await page.getByText("Source shelf and versions", { exact: true }).click();
  await page
    .getByLabel("Source to revise", { exact: true })
    .selectOption(source.source.document_id);
  await page
    .getByLabel("New source-version text", { exact: true })
    .fill("Synthetic revised predecessor excerpt; overlap remains unresolved.");
  await page
    .getByRole("button", { name: "Save source version", exact: true })
    .click();
  await expect(card).toContainText("affected_by_change");
  await card.getByRole("button", { name: "Open linked source v1" }).click();
  await expect(page.getByLabel("Linked source reader")).toContainText(
    demo.source,
  );
  const history = await (await page.request.get(root + "/history")).json();
  expect(
    history.source_versions.filter(
      (s: { document_id: string }) =>
        s.document_id === source.source.document_id,
    ),
  ).toHaveLength(2);
  await card.getByRole("button", { name: "Edit record", exact: true }).click();
  await page
    .getByLabel("Record title", { exact: true })
    .fill("Revised predecessor comparison");
  await page
    .getByRole("button", { name: "Save literature record", exact: true })
    .click();
  const edited = page.getByRole("article", {
    name: "Revised predecessor comparison",
  });
  await edited.getByRole("button", { name: "Open linked source v1" }).click();
  await expect(page.getByLabel("Linked source reader")).toContainText(
    demo.source,
  );
  const current = await (await page.request.get(root)).json();
  expect(current.project.objects.at(-1).source_refs[0].version).toBe(1);
});

test("adoption creates revision, selective staleness and scoped refresh; old review and export stay immutable", async ({
  page,
}) => {
  const { view, root } = await setup(page);
  await workspace(page, "Argument");
  await page
    .getByRole("button", { name: "Check argument only", exact: true })
    .click();
  await expect(page.getByLabel("Targeted workspace review")).toContainText(
    "current for this scope",
  );
  const arg = await (await page.request.get(root)).json();
  const argumentReview = arg.reviews.find(
    (r: { workspace?: string }) => r.workspace === "Argument",
  );
  await workspace(page, "Study");
  await page
    .getByRole("button", { name: "Check study only", exact: true })
    .click();
  await expect(page.getByLabel("Targeted workspace review")).toContainText(
    "current for this scope",
  );
  const before = await (await page.request.get(root)).json();
  const old = before.reviews.find(
    (r: { workspace?: string }) => r.workspace === "Study",
  );
  const oldReview = await (
    await page.request.get(root + "/reviews/" + old.snapshot_id)
  ).json();
  const oldExport = await (
    await page.request.get(
      root + "/history/" + view.project.revision + "/export",
    )
  ).text();
  await page
    .getByRole("button", { name: "Propose study change", exact: true })
    .click();
  const suggestion = page.getByRole("article", { name: "Proposed Study note" });
  await expect(suggestion).toContainText("proposed");
  await suggestion
    .getByRole("button", { name: "Accept suggestion", exact: true })
    .click();
  await expect(suggestion).toContainText("accepted");
  await expect(suggestion).toContainText("not_inspected");
  await expect(page.getByLabel("Targeted workspace review")).toContainText(
    "affected by change",
  );
  const updated = await (await page.request.get(root)).json();
  expect(updated.project.revision).toBe(view.project.revision + 2);
  const unrelated = await (
    await page.request.get(root + "/reviews/" + argumentReview.snapshot_id)
  ).json();
  expect(unrelated.stale).toBe(false);
  const historical = await (
    await page.request.get(root + "/reviews/" + old.snapshot_id)
  ).json();
  expect(historical.snapshot).toEqual(oldReview.snapshot);
  expect(historical.policy).toEqual(oldReview.policy);
  expect(
    await (
      await page.request.get(
        root + "/history/" + view.project.revision + "/export",
      )
    ).text(),
  ).toBe(oldExport);
  await page
    .getByRole("button", { name: "Check study only", exact: true })
    .click();
  await expect(page.getByLabel("Targeted workspace review")).toContainText(
    "current for this scope",
  );
  await workspace(page, "History");
  await expect(
    page.getByText(/accepted — Adopted as project representation/),
  ).toBeVisible();
  await page
    .getByRole("button", {
      name:
        "Open Study review of revision " +
        view.project.revision +
        " · affected",
      exact: true,
    })
    .click();
  await expect(page.getByLabel("Evaluation review")).toContainText(
    oldReview.summary.obstacle,
  );
});

for (const route of ["ESTABLISH", "TEST"])
  test(
    route + " workspaces never require a fabricated mechanism",
    async ({ page }) => {
      await setup(page, route);
      await workspace(page, "Argument");
      await expect(page.getByLabel("Argument workspace")).toContainText(
        "mechanism is not required",
      );
      await expect(
        page.getByLabel("Because-logic / explanatory account", { exact: true }),
      ).toHaveCount(0);
      await page
        .getByLabel("Record title", { exact: true })
        .fill(route + " task");
      await page
        .getByLabel("Focal claim / answer", { exact: true })
        .fill("Synthetic route-appropriate knowledge need");
      await page
        .getByRole("button", { name: "Save argument record", exact: true })
        .click();
      await expect(
        page.getByRole("article", { name: route + " task" }),
      ).toContainText("Synthetic route-appropriate knowledge need");
    },
  );

test("dependency edit preserves lineage and focused review invalidates after later consequential change", async ({
  page,
}) => {
  const { root } = await setup(page);
  await workspace(page, "Usefulness");
  await page
    .getByLabel("Record title", { exact: true })
    .fill("Synthetic boundary");
  await page
    .getByLabel("Boundaries on use", { exact: true })
    .fill("Original synthetic boundary");
  await page
    .getByRole("button", { name: "Save usefulness record", exact: true })
    .click();
  const upstreamArticle = page.getByRole("article", {
    name: "Synthetic boundary",
    exact: true,
  });
  await expect(upstreamArticle).toBeVisible();
  let view = await (await page.request.get(root)).json();
  const upstream = view.project.objects.at(-1);
  await workspace(page, "Study");
  await page
    .getByLabel("Record title", { exact: true })
    .fill("Dependent synthetic study");
  await page
    .getByLabel("What claim can this design support?", { exact: true })
    .fill("Conditional synthetic claim");
  await page
    .getByLabel("Depends on record", { exact: true })
    .selectOption(upstream.object_id);
  await page
    .getByRole("button", { name: "Save study record", exact: true })
    .click();
  const studyArticle = page.getByRole("article", {
    name: "Dependent synthetic study",
    exact: true,
  });
  await expect(studyArticle).toBeVisible();
  view = await (await page.request.get(root)).json();
  const dependent = view.project.objects.at(-1);
  await page
    .getByRole("button", { name: "Check study only", exact: true })
    .click();
  await expect(page.getByLabel("Targeted workspace review")).toContainText(
    "current for this scope",
  );
  await studyArticle
    .getByRole("button", { name: "Edit record", exact: true })
    .click();
  await expect(
    page
      .getByLabel("Depends on record", { exact: true })
      .getByRole("option", { name: "Keep recorded dependencies" }),
  ).toBeAttached();
  await page
    .getByLabel("Change classification", { exact: true })
    .selectOption("wording");
  await page
    .getByRole("button", { name: "Save study record", exact: true })
    .click();
  await expect(studyArticle).toHaveCount(2);
  view = await (await page.request.get(root)).json();
  expect(view.project.objects.at(-1).dependencies).toEqual(
    dependent.dependencies,
  );
  await workspace(page, "Usefulness");
  await upstreamArticle
    .getByRole("button", { name: "Edit record", exact: true })
    .click();
  await page
    .getByLabel("Change classification", { exact: true })
    .selectOption("wording");
  await page
    .getByLabel("Boundaries on use", { exact: true })
    .fill("Original synthetic  boundary");
  await page
    .getByRole("button", { name: "Save usefulness record", exact: true })
    .click();
  await expect(upstreamArticle).toHaveCount(2);
  view = await (await page.request.get(root)).json();
  expect(view.project.objects.at(-1).dependency_identity).toBe(
    upstream.object_id,
  );
  await page.reload();
  await workspace(page, "Study");
  await expect(page.getByLabel("Targeted workspace review")).toContainText(
    "current for this scope",
  );
  await workspace(page, "Usefulness");
  await upstreamArticle
    .last()
    .getByRole("button", { name: "Edit record", exact: true })
    .click();
  await page
    .getByLabel("Change classification", { exact: true })
    .selectOption("substantive");
  await page
    .getByLabel("Boundaries on use", { exact: true })
    .fill("Consequentially different synthetic boundary");
  await page
    .getByRole("button", { name: "Save usefulness record", exact: true })
    .click();
  await expect(upstreamArticle).toHaveCount(3);
  await workspace(page, "Study");
  await expect(page.getByLabel("Targeted workspace review")).toContainText(
    "affected by change",
  );
});

test("GATE-3 Overview preserves integrated review and scoped reviews reopen with reproducibility metadata", async ({
  page,
}) => {
  const { view, root } = await setup(page);
  const full = await (
    await page.request.post(root + "/evaluations", {
      data: {
        expected_revision: view.project.revision,
        scope: "FULL_EVALUATION",
      },
    })
  ).json();
  const scoped = await (
    await page.request.post(root + "/workspace-checks", {
      data: { expected_revision: view.project.revision, workspace: "Study" },
    })
  ).json();
  await page.reload();
  await expect(page.getByLabel("Evaluation review")).toContainText(
    "FULL_EVALUATION",
  );
  await expect(page.getByLabel("Evaluation review")).toContainText("Rubric v5");
  await expect(page.getByLabel("Evaluation review")).toContainText(
    full.snapshot.policy_manifest_sha256,
  );
  await workspace(page, "Study");
  await expect(page.getByLabel("Targeted workspace review")).toContainText(
    "TARGETED_CHECK",
  );
  await expect(page.getByLabel("Targeted workspace review")).toContainText(
    String(scoped.snapshot.project.revision),
  );
  await workspace(page, "Overview");
  await expect(page.getByLabel("Evaluation review")).toContainText(
    "Integrated project review",
  );
  await expect(page.getByLabel("Evaluation review")).toContainText(
    "FULL_EVALUATION",
  );
});
