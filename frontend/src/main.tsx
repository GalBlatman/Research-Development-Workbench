import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import type { components } from "../generated/api";
import "./style.css";
import { ResearchWorkspaces, type Workspace } from "./workspaces";

type Create = components["schemas"]["CreateProject"];
type View = components["schemas"]["ProjectView"];
type Review = components["schemas"]["ReviewView"];
type Run = components["schemas"]["RunHandle"];
type Budget = {
  max_calls: number;
  max_run_tokens: number;
  output_limit: number;
  timeout_seconds: number;
};

async function api<T>(url: string, method = "GET", data?: unknown): Promise<T> {
  const response = await fetch("/api" + url, {
    method,
    headers: { "Content-Type": "application/json" },
    ...(data ? { body: JSON.stringify(data) } : {}),
  });
  const body = await response.json();
  if (!response.ok)
    throw new Error(
      typeof body.detail === "string"
        ? body.detail
        : "Invalid request. Check the required fields.",
    );
  return body as T;
}

function App() {
  const [reviewScope, setReviewScope] =
    useState<components["schemas"]["EvaluateRequest"]["scope"]>(
      "INITIAL_SCREEN",
    );
  const [active, setActive] = useState<Workspace>("Overview");
  const [sessionGoal, setSessionGoal] = useState(
    "Assess the idea and identify the next useful step",
  );
  const [view, setView] = useState<View | null>(null);
  const [title, setTitle] = useState("");
  const [idea, setIdea] = useState("");
  const [route, setRoute] = useState<Create["route"]>("EXPLAIN");
  const [stage, setStage] = useState<Create["stage"]>("DISCOVERY PROPOSAL");
  const [authorized, setAuthorized] = useState(false);
  const [sourceTitle, setSourceTitle] = useState("");
  const [attribution, setAttribution] = useState("");
  const [sourceText, setSourceText] = useState("");
  const [sourceAuthorized, setSourceAuthorized] = useState(false);
  const [admitted, setAdmitted] = useState(true);
  const [review, setReview] = useState<Review | null>(null);
  const [passage, setPassage] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [provider, setProvider] = useState("loading");
  const [activePolicy, setActivePolicy] = useState<{
    policy_version: string;
    policy_manifest_sha256: string;
    prompt_version: string | null;
  } | null>(null);
  const [budget, setBudget] = useState<Budget | null>(null);
  const [runMessage, setRunMessage] = useState("");
  const projectId = new URLSearchParams(location.search).get("project");

  function update(next: View) {
    setView(next);
    setTitle(next.project.title);
    setIdea(
      next.sources.find((s) => s.source.role === "project_draft")?.text ?? "",
    );
    history.replaceState(null, "", "?project=" + next.project.project_id);
  }
  async function work(action: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (e) {
      setError(e instanceof Error ? e.message : "The operation failed.");
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    void api<{
      model: string;
      budget: Budget | null;
      policy_version: string;
      policy_manifest_sha256: string;
      prompt_version: string | null;
    }>("/health")
      .then((health) => {
        setProvider(health.model);
        setActivePolicy(health);
        setBudget(health.budget);
      })
      .catch(() => setError("Provider configuration could not be loaded."));
    if (projectId)
      void work(async () => {
        const saved = await api<View>("/projects/" + projectId);
        update(saved);
        const latest = saved.reviews
          .filter((r) => r.workspace == null && r.scope !== "TARGETED_CHECK")
          .at(-1);
        if (latest)
          setReview(
            await api<Review>(
              "/projects/" + projectId + "/reviews/" + latest.snapshot_id,
            ),
          );
      });
  }, []);
  useEffect(() => {
    if (
      !view ||
      active === "Review" ||
      active === "History" ||
      active === "Next Actions"
    )
      return;
    const latest = view.reviews
      .filter((r) =>
        active === "Overview"
          ? r.workspace == null && r.scope !== "TARGETED_CHECK"
          : r.workspace === active,
      )
      .at(-1);
    if (!latest) {
      if (active === "Overview") setReview(null);
      return;
    }
    let cancelled = false;
    void api<Review>(
      "/projects/" + view.project.project_id + "/reviews/" + latest.snapshot_id,
    )
      .then((value) => {
        if (!cancelled) setReview(value);
      })
      .catch(() => {
        if (!cancelled) setError("Saved review could not be loaded.");
      });
    return () => {
      cancelled = true;
    };
  }, [active, view?.project.revision, view?.reviews.length]);
  async function evaluateRevision(current: View): Promise<Review> {
    const root = "/projects/" + current.project.project_id;
    const result = await api<Review | Run>(root + "/evaluations", "POST", {
      expected_revision: current.project.revision,
      scope: reviewScope,
    });
    if ("snapshot" in result) return result;
    setRunMessage("Evaluation queued; checking runs before publication.");
    for (let attempts = 0; attempts < 450; attempts++) {
      await new Promise((resolve) => setTimeout(resolve, 2000));
      const run = await api<Run>(root + "/runs/" + result.run_id);
      setRunMessage("Evaluation " + run.state + ".");
      if (run.state === "failed")
        throw new Error(
          run.error_code ?? "Evaluation failed without publication.",
        );
      if (run.state === "succeeded" && run.snapshot_id)
        return api<Review>(root + "/reviews/" + run.snapshot_id);
    }
    throw new Error(
      "Still running. Reload the saved project later to open the completed review.",
    );
  }
  async function demo() {
    const data = await api<{ idea: string; source: string }>("/demo");
    setTitle("Synthetic knowledge-sharing example");
    setIdea(data.idea);
    setSourceTitle("Synthetic predecessor");
    setAttribution("Synthetic test fixture");
    setSourceText(data.source);
    setRoute("EXPLAIN");
    setStage("EARLY IDEA");
  }
  async function changed(next: View) {
    update(next);
    if (review)
      setReview(
        await api<Review>(
          "/projects/" +
            next.project.project_id +
            "/reviews/" +
            review.snapshot.snapshot_id,
        ),
      );
  }
  async function saveEdit() {
    if (!view) return;
    const next = await api<View>(
      "/projects/" + view.project.project_id,
      "PATCH",
      { expected_revision: view.project.revision, idea },
    );
    update(next);
    if (review)
      setReview(
        await api<Review>(
          "/projects/" +
            next.project.project_id +
            "/reviews/" +
            review.snapshot.snapshot_id,
        ),
      );
  }

  return (
    <main>
      <header>
        <p className="eyebrow">RESEARCH DEVELOPMENT WORKBENCH</p>
        <h1>From a question to a next step</h1>
        <p>
          {provider.startsWith("openai:")
            ? `Local bounded research workflow using ${provider}. Reviews are interpretive judgments, not independent scientific verification.`
            : "Local fake-model demonstration. Fixed outputs exercise the workflow; no external model processing."}
        </p>
      </header>
      {provider.startsWith("openai:") && (
        <p>
          Only admitted text is sent to OpenAI with store=false, foreground
          requests and no tools. Zero Data Retention requires eligible account
          controls.{" "}
          {budget &&
            `Per run: at most ${budget.max_calls} attempts, ${budget.max_run_tokens} reserved tokens, ${budget.output_limit} output tokens per call, and ${budget.timeout_seconds} seconds per request.`}
        </p>
      )}
      {error && <div role="alert">{error}</div>}
      {busy && <p role="status">Saving or evaluating…</p>}
      <fieldset disabled={busy || provider === "loading"}>
        {!view ? (
          <section>
            <h2>Start a project</h2>
            <button type="button" onClick={() => void work(demo)}>
              Load synthetic example
            </button>
            <label>
              Project title
              <input
                value={title}
                maxLength={200}
                onChange={(e) => setTitle(e.target.value)}
              />
            </label>
            <label>
              Your idea or description
              <textarea
                value={idea}
                maxLength={20000}
                onChange={(e) => setIdea(e.target.value)}
              />
            </label>
            <div className="row">
              <label>
                Contribution route
                <select
                  value={route}
                  onChange={(e) => setRoute(e.target.value as Create["route"])}
                >
                  <option>EXPLAIN</option>
                  <option>ESTABLISH</option>
                  <option>TEST</option>
                </select>
              </label>
              <label>
                Project stage
                <select
                  value={stage}
                  onChange={(e) => setStage(e.target.value as Create["stage"])}
                >
                  <option>EARLY IDEA</option>
                  <option>DISCOVERY PROPOSAL</option>
                  <option>SPECIFIED STUDY PROPOSAL</option>
                  <option>COMPLETED STUDY</option>
                </select>
              </label>
            </div>
            <label>
              What help do you need?
              <textarea
                value={sessionGoal}
                onChange={(e) => setSessionGoal(e.target.value)}
              />
            </label>
            <label className="check">
              <input
                type="checkbox"
                checked={authorized}
                onChange={(e) => setAuthorized(e.target.checked)}
              />
              {provider.startsWith("openai:")
                ? "I authorize OpenAI processing"
                : "I authorize local processing"}{" "}
              of my pasted project text.
            </label>
            <button
              disabled={!authorized || !idea.trim()}
              onClick={() =>
                void work(async () => {
                  update(
                    await api<View>("/projects", "POST", {
                      title: title.trim() || "Untitled project",
                      session_goal: sessionGoal,
                      idea,
                      route,
                      stage,
                      authorized,
                    }),
                  );
                })
              }
            >
              Create project
            </button>
          </section>
        ) : (
          <>
            <ResearchWorkspaces
              view={view}
              review={review}
              active={active}
              navigate={setActive}
              update={changed}
              showReview={setReview}
              work={work}
            />
            <div
              hidden={
                active !== "Overview" &&
                active !== "Review" &&
                active !== "Literature" &&
                active !== "Brief"
              }
            >
              <section hidden={active !== "Overview" && active !== "Brief"}>
                <h2>{view.project.title}</h2>
                <p>
                  Working revision {view.project.revision} ·{" "}
                  {view.project.route} · {view.project.stage}
                </p>
                <label>
                  Edit original idea
                  <textarea
                    value={idea}
                    maxLength={20000}
                    onChange={(e) => setIdea(e.target.value)}
                  />
                </label>
                <button onClick={() => void work(saveEdit)}>
                  Save new revision
                </button>
              </section>
              <section hidden={active !== "Overview" && active !== "Brief"}>
                <h2>Structured interpretation</h2>
                <p>
                  Proposed interpretation. Accepting confirms representation
                  only; evidence remains not inspected.
                </p>
                {view.project.objects
                  .filter((obj) => obj.payload.kind !== "research_record")
                  .map((obj) => (
                    <article key={obj.object_id}>
                      <p>
                        <strong>
                          {"question" in obj.payload
                            ? obj.payload.question
                            : obj.payload.kind}
                        </strong>
                      </p>
                      {"core_insight" in obj.payload && (
                        <p>{obj.payload.core_insight}</p>
                      )}
                      <p>
                        Origin: {obj.origin} · Adoption: {obj.adoption} ·
                        Evidence: {obj.evidence_state} · Freshness:{" "}
                        {obj.freshness}
                      </p>
                      {obj.adoption === "proposed" && (
                        <button
                          onClick={() =>
                            void work(async () => {
                              await changed(
                                await api<View>(
                                  "/projects/" +
                                    view.project.project_id +
                                    "/proposals/" +
                                    obj.object_id +
                                    "/accept",
                                  "POST",
                                  { expected_revision: view.project.revision },
                                ),
                              );
                            })
                          }
                        >
                          Accept representation
                        </button>
                      )}
                    </article>
                  ))}
              </section>
              <section
                hidden={active !== "Overview" && active !== "Literature"}
              >
                <h2>Literature and sources</h2>
                <label>
                  Source title
                  <input
                    value={sourceTitle}
                    maxLength={200}
                    onChange={(e) => setSourceTitle(e.target.value)}
                  />
                </label>
                <label>
                  Attribution
                  <input
                    value={attribution}
                    maxLength={500}
                    onChange={(e) => setAttribution(e.target.value)}
                  />
                </label>
                <label>
                  Pasted source text
                  <textarea
                    value={sourceText}
                    maxLength={50000}
                    onChange={(e) => setSourceText(e.target.value)}
                  />
                </label>
                <label className="check">
                  <input
                    type="checkbox"
                    checked={sourceAuthorized}
                    onChange={(e) => setSourceAuthorized(e.target.checked)}
                  />
                  {provider.startsWith("openai:")
                    ? "I authorize OpenAI to process"
                    : "I am authorized to process"}{" "}
                  this source text locally.
                </label>
                <label className="check">
                  <input
                    type="checkbox"
                    checked={admitted}
                    onChange={(e) => setAdmitted(e.target.checked)}
                  />
                  Include this version in the evaluation packet.
                </label>
                <button
                  disabled={
                    !sourceAuthorized ||
                    !sourceTitle.trim() ||
                    !attribution.trim() ||
                    !sourceText.trim()
                  }
                  onClick={() =>
                    void work(async () => {
                      await changed(
                        await api<View>(
                          "/projects/" + view.project.project_id + "/sources",
                          "POST",
                          {
                            expected_revision: view.project.revision,
                            title: sourceTitle,
                            attribution,
                            text: sourceText,
                            authorized: sourceAuthorized,
                            admitted,
                          },
                        ),
                      );
                      setSourceText("");
                    })
                  }
                >
                  Add source
                </button>
                <ul>
                  {view.sources.map((s) => (
                    <li key={s.source.document_id}>
                      {s.source.title} · version {s.version} · {s.source.role} ·{" "}
                      {s.state} · {s.admitted ? "included" : "excluded"}{" "}
                      {s.admitted &&
                        s.anchors.map((a) => (
                          <button
                            key={a.anchor_id}
                            onClick={() =>
                              void work(async () => {
                                const p = await api<{ text: string }>(
                                  "/projects/" +
                                    view.project.project_id +
                                    "/sources/" +
                                    s.source.document_id +
                                    "/" +
                                    s.version +
                                    "/" +
                                    a.anchor_id,
                                );
                                setPassage(p.text);
                              })
                            }
                          >
                            Inspect {s.source.title}, lines {a.line_start}–
                            {a.line_end}
                          </button>
                        ))}
                    </li>
                  ))}
                </ul>
                {passage !== null && (
                  <aside aria-label="Source passage">
                    <h3>Original source passage</h3>
                    <pre>{passage}</pre>
                  </aside>
                )}
              </section>
              <section hidden={active !== "Overview" && active !== "Review"}>
                <h2>Evaluate this revision</h2>
                <p>
                  {provider === "deterministic-fake-v1" || provider === "fake"
                    ? "Offline fake evaluation uses fixed synthetic responses; other inputs retain pending judgments."
                    : `Provider: ${provider}. Bounded evaluation includes a focused checking pass; interpretive support is not independent evidence verification.`}
                </p>
                <label htmlFor="review-scope">Review scope</label>
                <select
                  id="review-scope"
                  value={reviewScope}
                  onChange={(e) =>
                    setReviewScope(
                      e.target
                        .value as components["schemas"]["EvaluateRequest"]["scope"],
                    )
                  }
                >
                  <option value="INITIAL_SCREEN">Initial screen</option>
                  <option value="FULL_EVALUATION">Full evaluation</option>
                  <option value="REVISION_REVIEW">Revision evaluation</option>
                </select>
                <button
                  onClick={() =>
                    void work(async () => {
                      setReview(await evaluateRevision(view));
                      update(
                        await api<View>("/projects/" + view.project.project_id),
                      );
                    })
                  }
                >
                  {provider === "deterministic-fake-v1" || provider === "fake"
                    ? "Run fake evaluation"
                    : "Run evaluation"}
                </button>
                {runMessage && <p role="status">{runMessage}</p>}
                <ul>
                  {view.reviews.map((r) => (
                    <li key={r.snapshot_id}>
                      <button
                        onClick={() =>
                          void work(async () => {
                            setReview(
                              await api<Review>(
                                "/projects/" +
                                  view.project.project_id +
                                  "/reviews/" +
                                  r.snapshot_id,
                              ),
                            );
                          })
                        }
                      >
                        Open review of revision {r.revision} ·{" "}
                        {r.workspace ?? "Integrated"} · {r.scope} ·{" "}
                        {r.stale ? "affected" : "current"} · rubric v
                        {r.policy_version}
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
              {review && (
                <section
                  hidden={active !== "Overview" && active !== "Review"}
                  aria-label="Evaluation review"
                >
                  <h2>Review of revision {review.snapshot.project.revision}</h2>
                  <p>
                    {review.snapshot.scope} · {review.snapshot.project.route} ·{" "}
                    {review.snapshot.project.stage}
                  </p>
                  <p>
                    Rubric v{review.snapshot.policy_version} · manifest{" "}
                    {review.snapshot.policy_manifest_sha256}
                  </p>
                  <p>
                    Model {review.snapshot.model_configuration ?? "fixture"} ·
                    prompts {review.snapshot.prompt_version ?? "fixture"}
                  </p>
                  <p>
                    Target:{" "}
                    {review.target_workspace ?? "Integrated project review"}.
                    Frozen metadata remains historical after configuration
                    changes.
                  </p>
                  {activePolicy &&
                    (review.snapshot.policy_manifest_sha256 !==
                      activePolicy.policy_manifest_sha256 ||
                      review.snapshot.model_configuration !== provider ||
                      review.snapshot.prompt_version !==
                        activePolicy.prompt_version) && (
                      <p role="status">
                        Historical review configuration differs from the active
                        rubric, model or prompts. Deliberate reevaluation is
                        required for a current comparison.
                      </p>
                    )}
                  {review.snapshot.imported && (
                    <p role="status">
                      Imported historical review: supplied provenance and
                      support dispositions have not been independently
                      reverified by this server.
                    </p>
                  )}
                  <p>{review.summary.disclaimer}</p>
                  {review.stale && (
                    <p role="status">
                      Historical review — working project has changed. This
                      snapshot remains unchanged.
                    </p>
                  )}
                  <h3>Contribution / insight to preserve</h3>
                  <p>{review.summary.contribution}</p>
                  <h3>Principal obstacle</h3>
                  <p>{review.summary.obstacle}</p>
                  <h3>Evidence and status limitations</h3>
                  <ul>
                    {review.summary.limitations.map((l, i) => (
                      <li key={i}>{l}</li>
                    ))}
                  </ul>
                  <h3>Source packet for this snapshot</h3>
                  <p>
                    Provided to the fake fixture; no semantic inspection. Each
                    link opens the frozen source version.
                  </p>
                  <ul>
                    {review.coverage.map((c) => (
                      <li key={c.document_id}>
                        {c.title} · version {c.version} · {c.state}
                        {c.anchors.map((a) => (
                          <button
                            key={a.anchor_id}
                            onClick={() =>
                              void work(async () => {
                                const p = await api<{ text: string }>(
                                  "/projects/" +
                                    view.project.project_id +
                                    "/sources/" +
                                    c.document_id +
                                    "/" +
                                    c.version +
                                    "/" +
                                    a.anchor_id,
                                );
                                setPassage(p.text);
                              })
                            }
                          >
                            Read snapshot source {c.title}, lines {a.line_start}
                            –{a.line_end}
                          </button>
                        ))}
                      </li>
                    ))}
                  </ul>
                  <h3>Applicable rubric results</h3>
                  <table>
                    <thead>
                      <tr>
                        <th>Block</th>
                        <th>Result</th>
                        <th>Status</th>
                        <th>Reason</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(["idea", "study", "project"] as const).map((name) => (
                        <tr key={name}>
                          <th>{name}</th>
                          <td>{review.policy[name].displayed ?? "—"}</td>
                          <td>{review.policy[name].status}</td>
                          <td>{review.policy[name].reason}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <p>
                    {review.policy.label} · Editorial:{" "}
                    {review.policy.editorial_status}
                  </p>
                  <details>
                    <summary>Dimension judgments and limits</summary>
                    <ul>
                      {review.assessment.ratings.map((r) => (
                        <li key={r.dimension}>
                          Dimension {r.dimension}: {r.rating ?? "—"} ·{" "}
                          {r.status}
                          <p>{r.rationale}</p>
                          <p>
                            {r.main_limitation} Verifier: {r.verification}.
                          </p>
                        </li>
                      ))}
                    </ul>
                  </details>
                  {review.provider_run && (
                    <details>
                      <summary>
                        Provider usage and focused support checks
                      </summary>
                      <p>
                        Run {review.provider_run.run_id}:{" "}
                        {review.provider_run.status}
                      </p>
                      <ul>
                        {review.provider_run.calls.map((call, i) => (
                          <li key={i}>
                            {call.task}:{" "}
                            {call.returned_model ?? call.configured_model} ·{" "}
                            {call.status} · input{" "}
                            {call.input_tokens ?? "unknown"}, output{" "}
                            {call.output_tokens ?? "unknown"}
                          </li>
                        ))}
                      </ul>
                      <ul>
                        {review.statements.map((statement) => (
                          <li key={statement.statement_id}>
                            {statement.kind}: {statement.text}
                          </li>
                        ))}
                      </ul>
                      <ul>
                        {review.checks.map((check) => (
                          <li key={check.target}>
                            {check.target}: {check.disposition} — {check.reason}
                          </li>
                        ))}
                      </ul>
                    </details>
                  )}
                  <h3>Route assessment basis</h3>
                  <ul aria-label="Route assessment basis">
                    {review.assessment.route_assessment.map((item) => (
                      <li key={item.item}>
                        {item.item}: {item.status} — {item.reason} · checking:{" "}
                        {item.verification}
                      </li>
                    ))}
                  </ul>
                  <p>
                    Account articulated:{" "}
                    {String(review.assessment.account_articulated)} · checking:{" "}
                    {review.assessment.account_articulated_verification}; study
                    assessable: {String(review.assessment.study_assessable)} ·
                    checking: {review.assessment.study_assessable_verification}
                  </p>
                  <h3>Readiness and applicability</h3>
                  <ul aria-label="Readiness gates">
                    {review.policy.gates.map((gate) => (
                      <li key={gate.name}>
                        {gate.name}: {gate.state}
                        {gate.commitment ? ` · ${gate.commitment}` : ""}
                        {gate.provisional ? " · provisional" : ""}
                        {gate.missed.length
                          ? ` — ${gate.missed.join("; ")}`
                          : ""}
                      </li>
                    ))}
                  </ul>
                  <h3>Recommended next action</h3>
                  <p>{review.summary.next_action}</p>
                  {review.summary.diagnostic_action && (
                    <>
                      <p>
                        Decision issue: {review.summary.diagnostic_action.issue}
                      </p>
                      <p>
                        Required input:{" "}
                        {review.summary.diagnostic_action.required_input}
                      </p>
                    </>
                  )}
                  <p>{review.summary.deliverable}</p>
                  <ul>
                    {review.summary.outcome_branches.map((branch, i) => (
                      <li key={i}>{branch}</li>
                    ))}
                  </ul>
                  <details>
                    <summary>
                      Deterministic rule trace and exact backend results
                    </summary>
                    <pre>{JSON.stringify(review.policy, null, 2)}</pre>
                  </details>
                </section>
              )}
              <section>
                <h2>Export and reload</h2>
                <p>
                  Exports include project history and reviews. Original source
                  files and private storage references are excluded.
                </p>
                <a
                  href={
                    "/api/projects/" +
                    view.project.project_id +
                    "/exports/markdown"
                  }
                  download
                >
                  Export Markdown
                </a>
                {" · "}
                <a
                  href={
                    "/api/projects/" + view.project.project_id + "/exports/json"
                  }
                  download
                >
                  Export JSON
                </a>
                <p>Bookmark this project URL to reload its saved state.</p>
                <button onClick={() => location.reload()}>
                  Reload saved project
                </button>
              </section>
            </div>
          </>
        )}
      </fieldset>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
