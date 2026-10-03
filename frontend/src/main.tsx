import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import type { components } from "../generated/api";
import "./style.css";

type Create = components["schemas"]["CreateProject"];
type View = components["schemas"]["ProjectView"];
type Review = components["schemas"]["ReviewView"];

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
    if (projectId)
      void work(async () => {
        update(await api<View>("/projects/" + projectId));
      });
  }, []);
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
          Local fake-model demonstration. Fixed outputs exercise the workflow;
          they do not assess your science. No external model processing.
        </p>
      </header>
      {error && <div role="alert">{error}</div>}
      {busy && <p role="status">Saving or evaluating…</p>}
      <fieldset disabled={busy}>
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
            <label className="check">
              <input
                type="checkbox"
                checked={authorized}
                onChange={(e) => setAuthorized(e.target.checked)}
              />
              I authorize local processing of my pasted project text.
            </label>
            <button
              disabled={!authorized || !title.trim() || !idea.trim()}
              onClick={() =>
                void work(async () => {
                  update(
                    await api<View>("/projects", "POST", {
                      title,
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
            <section>
              <h2>{view.project.title}</h2>
              <p>
                Working revision {view.project.revision} · {view.project.route}{" "}
                · {view.project.stage}
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
            <section>
              <h2>Structured interpretation</h2>
              <p>
                Fixed fake proposal. Accepting confirms representation only;
                evidence remains not inspected.
              </p>
              {view.project.objects.map((obj) => (
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
                    Origin: {obj.origin} · Adoption: {obj.adoption} · Evidence:{" "}
                    {obj.evidence_state} · Freshness: {obj.freshness}
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
            <section>
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
                I am authorized to process this source text locally.
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
            <section>
              <h2>Evaluate this revision</h2>
              <p>
                The fake adapter selects its fixed response internally. The
                unchanged synthetic example and source demonstrate arithmetic;
                other inputs retain pending judgments.
              </p>
              <button
                onClick={() =>
                  void work(async () => {
                    setReview(
                      await api<Review>(
                        "/projects/" + view.project.project_id + "/evaluations",
                        "POST",
                        { expected_revision: view.project.revision },
                      ),
                    );
                    update(
                      await api<View>("/projects/" + view.project.project_id),
                    );
                  })
                }
              >
                Run fake evaluation
              </button>
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
                      Open review of revision {r.revision}
                    </button>
                  </li>
                ))}
              </ul>
            </section>
            {review && (
              <section aria-label="Evaluation review">
                <h2>Review of revision {review.snapshot.project.revision}</h2>
                <p>
                  {review.snapshot.scope} · {review.snapshot.project.route} ·{" "}
                  {review.snapshot.project.stage}
                </p>
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
                          Read snapshot source {c.title}, lines {a.line_start}–
                          {a.line_end}
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
                        Dimension {r.dimension}: {r.rating ?? "—"} · {r.status}
                        <p>{r.rationale}</p>
                        <p>
                          {r.main_limitation} Verifier: {r.verification}.
                        </p>
                      </li>
                    ))}
                  </ul>
                </details>
                <h3>Readiness and applicability</h3>
                <ul aria-label="Readiness gates">
                  {review.policy.gates.map((gate) => (
                    <li key={gate.name}>
                      {gate.name}: {gate.state}
                      {gate.commitment ? ` · ${gate.commitment}` : ""}
                    </li>
                  ))}
                </ul>
                <h3>Recommended next action</h3>
                <p>{review.summary.next_action}</p>
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
