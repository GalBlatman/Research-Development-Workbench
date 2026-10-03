import { useEffect, useState } from "react";
import type { components } from "../generated/api";

type View = components["schemas"]["ProjectView"];
type Record = components["schemas"]["ResearchRecord"];
type Field = components["schemas"]["ResearchField"];
type Review = components["schemas"]["ReviewView"];
type Run = components["schemas"]["RunHandle"];
type Catalog = components["schemas"]["WorkspaceCatalog"];
type Project = components["schemas"]["Project"];
export type Workspace =
  | "Overview"
  | "Brief"
  | "Literature"
  | "Argument"
  | "Alternatives"
  | "Study"
  | "Usefulness"
  | "Review"
  | "Next Actions"
  | "History";

type Props = {
  view: View;
  review: Review | null;
  active: Workspace;
  navigate: (workspace: Workspace) => void;
  update: (view: View) => Promise<void>;
  showReview: (review: Review) => void;
  work: (action: () => Promise<void>) => Promise<void>;
};

async function request<T>(
  url: string,
  method = "GET",
  data?: unknown,
): Promise<T> {
  const response = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    ...(data ? { body: JSON.stringify(data) } : {}),
  });
  const body = await response.json();
  if (!response.ok)
    throw new Error(
      typeof body.detail === "string"
        ? body.detail
        : "Check required record fields and evidence references.",
    );
  return body as T;
}

export function ResearchWorkspaces({
  view,
  review,
  active,
  navigate,
  update,
  showReview,
  work,
}: Props) {
  const [versionText, setVersionText] = useState("");
  const [reader, setReader] = useState<string | null>(null);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [drafts, setDrafts] = useState<{
    [workspace: string]: { [key: string]: string };
  }>({});
  const [states, setStates] = useState<{
    [workspace: string]: { [key: string]: Field["state"] };
  }>({});
  const [titles, setTitles] = useState<{ [workspace: string]: string }>({});
  const [editing, setEditing] = useState<{
    [workspace: string]: string | null;
  }>({});
  const [source, setSource] = useState("");
  const [supportingAnchors, setSupportingAnchors] = useState<{
    [key: string]: string;
  }>({});
  const supportingAnchor = supportingAnchors[active] ?? "";
  const setSupportingAnchor = (value: string) =>
    setSupportingAnchors((current) => ({ ...current, [active]: value }));
  const [preservedReferences, setPreservedReferences] = useState<{
    [key: string]: components["schemas"]["SourceReference"][];
  }>({});
  const preservedRefs = preservedReferences[active] ?? [];
  const setPreservedRefs = (
    value: components["schemas"]["SourceReference"][],
  ) => setPreservedReferences((current) => ({ ...current, [active]: value }));
  const [dependencyChoices, setDependencyChoices] = useState<{
    [key: string]: string;
  }>({});
  const dependsOn = dependencyChoices[active] ?? "";
  const setDependsOn = (value: string) =>
    setDependencyChoices((current) => ({ ...current, [active]: value }));
  const [classifications, setClassifications] = useState<{
    [key: string]: string;
  }>({});
  const classification = classifications[active] ?? "substantive";
  const setClassification = (value: string) =>
    setClassifications((current) => ({ ...current, [active]: value }));
  const [goal, setGoal] = useState(view.project.session_goal);
  const [route, setRoute] = useState(view.project.route);
  const [stage, setStage] = useState(view.project.stage);
  const [target, setTarget] = useState(view.project.evaluation_target);
  const [history, setHistory] = useState<
    components["schemas"]["HistoryView"] | null
  >(null);
  const root = "/api/projects/" + view.project.project_id;
  useEffect(() => {
    void work(async () => {
      setCatalog(await request<Catalog>(root + "/workspaces"));
    });
  }, [view.project.project_id, view.project.route]);
  useEffect(() => {
    if (active === "History")
      void work(async () => {
        setHistory(await request(root + "/history"));
      });
  }, [active, view.project.revision]);
  const records = view.project.objects.filter(
    (o) =>
      o.payload.kind === "research_record" && o.payload.workspace === active,
  );
  if (active === "Next Actions")
    records.sort((a, b) => {
      const order = (o: typeof a) =>
        o.payload.kind === "research_record"
          ? (o.payload.fields.find((f) => f.key === "order")?.text ?? "")
          : "";
      return order(a).localeCompare(order(b), undefined, { numeric: true });
    });
  const fieldLabels = catalog?.fields[active];
  const payload = (): Record => ({
    kind: "research_record",
    workspace: active as Record["workspace"],
    title: titles[active]?.trim() || active + " note",
    fields: Object.keys(fieldLabels ?? {}).map((key) => ({
      key,
      text: drafts[active]?.[key]?.trim() || null,
      state:
        states[active]?.[key] ??
        (drafts[active]?.[key]?.trim() ? "specified_but_untested" : "missing"),
      origin: "user_text",
      source_refs: [],
    })),
  });
  const supportingSource = view.sources.find(
    (s) =>
      s.source.document_id === supportingAnchor.split("|")[0] && s.admitted,
  );
  const selectedAnchor =
    supportingSource?.anchors.find(
      (a) => a.anchor_id === supportingAnchor.split("|")[1],
    ) ?? supportingSource?.anchors[0];
  const refs = preservedRefs.length
    ? preservedRefs
    : selectedAnchor
      ? [
          {
            document_id: supportingSource!.source.document_id,
            version: supportingSource!.version,
            anchor_id: selectedAnchor.anchor_id,
          },
        ]
      : [];
  function edit(obj: View["project"]["objects"][number]) {
    if (obj.payload.kind !== "research_record") return;
    setEditing({ ...editing, [active]: obj.object_id });
    setTitles({ ...titles, [active]: obj.payload.title });
    setDrafts({
      ...drafts,
      [active]: Object.fromEntries(
        obj.payload.fields.map((f) => [f.key, f.text ?? ""]),
      ),
    });
    setStates({
      ...states,
      [active]: Object.fromEntries(
        obj.payload.fields.map((f) => [f.key, f.state]),
      ),
    });
    setSource(obj.source_refs[0]?.document_id ?? "");
    setPreservedRefs(obj.source_refs);
    setDependsOn("");
    setSupportingAnchor(
      obj.source_refs[0]
        ? obj.source_refs[0].document_id + "|" + obj.source_refs[0].anchor_id
        : "",
    );
  }
  async function save() {
    const record = payload();
    record.fields = record.fields.map((f) => ({ ...f, source_refs: refs }));
    await update(
      await request<View>(root + "/records", "POST", {
        expected_revision: view.project.revision,
        record,
        object_id: editing[active] ?? null,
        source_refs: refs,
        depends_on:
          dependsOn === "__clear"
            ? []
            : dependsOn
              ? [dependsOn]
              : editing[active]
                ? null
                : [],
        change: classification,
      }),
    );
    setEditing({ ...editing, [active]: null });
    setDrafts({ ...drafts, [active]: {} });
    setTitles({ ...titles, [active]: "" });
    setStates({ ...states, [active]: {} });
    setPreservedRefs([]);
    setSupportingAnchor("");
  }
  async function waitForRun(run: Run): Promise<Run> {
    for (let attempt = 0; attempt < 450; attempt++) {
      await new Promise((resolve) => setTimeout(resolve, 2000));
      const current = await request<Run>(root + "/runs/" + run.run_id);
      if (current.state === "failed")
        throw new Error(
          current.error_code ?? "Task failed without publication",
        );
      if (current.state === "succeeded") return current;
    }
    throw new Error("Still running; reload the saved project later.");
  }
  async function propose() {
    const result = await request<View | Run>(
      root + "/workspace-proposals",
      "POST",
      {
        expected_revision: view.project.revision,
        workspace: active,
        object_id: editing[active] ?? null,
        instruction:
          view.project.session_goal || "Propose one bounded improvement",
      },
    );
    if ("project" in result) await update(result);
    else {
      await waitForRun(result);
      await update(await request<View>(root));
    }
  }
  async function checkWorkspace() {
    const result = await request<Review | Run>(
      root + "/workspace-checks",
      "POST",
      { expected_revision: view.project.revision, workspace: active },
    );
    let currentReview: Review;
    if ("snapshot" in result) currentReview = result;
    else {
      const completed = await waitForRun(result);
      if (!completed.snapshot_id)
        throw new Error("Check completed without a review");
      currentReview = await request<Review>(
        root + "/reviews/" + completed.snapshot_id,
      );
    }
    await update(await request<View>(root));
    showReview(currentReview);
  }
  const brief = view.project.objects.find(
    (o) =>
      o.payload.kind === "brief" &&
      o.adoption !== "rejected" &&
      o.adoption !== "superseded",
  );
  const clarified = view.project.objects
    .filter(
      (o) =>
        o.payload.kind === "research_record" &&
        o.payload.workspace === "Brief" &&
        o.adoption === "accepted",
    )
    .reverse()
    .find(
      (o) =>
        o.payload.kind === "research_record" &&
        o.payload.fields.some((f) => f.key === "question" && f.text),
    );
  const question =
    clarified?.payload.kind === "research_record"
      ? clarified.payload.fields.find((f) => f.key === "question")?.text
      : brief?.payload.kind === "brief"
        ? brief.payload.question
        : null;
  return (
    <>
      <nav className="workspace-nav" aria-label="Research workspaces">
        {(
          catalog?.workspaces ?? [
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
          ]
        ).map((name) => (
          <button
            type="button"
            key={name}
            aria-current={active === name ? "page" : undefined}
            onClick={() => navigate(name as Workspace)}
          >
            {name}
          </button>
        ))}
      </nav>
      <section aria-label={active + " workspace"}>
        <h2>{active}</h2>
        <p>
          Project {view.project.title} · revision {view.project.revision} ·{" "}
          {view.project.route} · {view.project.stage}
        </p>
        {active === "Overview" && (
          <>
            <h3>Current question</h3>
            <p>
              {question ??
                "Question needs clarification; the original description is preserved below."}
            </p>
            <h3>Insight to preserve</h3>
            <p>
              {review?.summary.contribution ??
                "No scientific contribution has been assessed yet."}
            </p>
            <h3>Principal obstacle</h3>
            <p>
              {review?.summary.obstacle ??
                "Interpretation and supplied evidence remain provisional."}
            </p>
            <h3>Next useful action</h3>
            <p>
              {review?.summary.next_action ??
                "Check consequential misreadings, add supplied sources if relevant, then request a bounded review."}
            </p>
            <p>
              {view.sources.filter((s) => s.admitted).length} admitted source
              records; no exhaustive literature coverage is claimed. Latest
              review ({review?.target_workspace ?? "project"}):{" "}
              {review
                ? `revision ${review.snapshot.project.revision} · ${review.stale ? "affected by change" : "current for its scope"}`
                : "none opened"}
              .
            </p>
            <p>
              Source verification and user adoption are separate. Missing /
              uninspected material is not a zero score.
            </p>
          </>
        )}
        {active === "Brief" && (
          <details>
            <summary>Route, stage and current help request</summary>
            <label>
              Contribution route
              <select
                aria-label="Contribution route"
                value={route}
                onChange={(e) => setRoute(e.target.value as Project["route"])}
              >
                <option>EXPLAIN</option>
                <option>ESTABLISH</option>
                <option>TEST</option>
              </select>
            </label>
            <label>
              Project stage
              <select
                aria-label="Project stage"
                value={stage}
                onChange={(e) => setStage(e.target.value as Project["stage"])}
              >
                <option>EARLY IDEA</option>
                <option>DISCOVERY PROPOSAL</option>
                <option>SPECIFIED STUDY PROPOSAL</option>
                <option>COMPLETED STUDY</option>
              </select>
            </label>
            <label>
              What help do you need?
              <textarea
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
              />
            </label>
            <label>
              Evaluation target
              <select
                aria-label="Evaluation target"
                value={target}
                onChange={(e) =>
                  setTarget(e.target.value as Project["evaluation_target"])
                }
              >
                <option value="current_project_as_clarified">
                  Current project as clarified
                </option>
                <option value="manuscript_as_written">
                  Manuscript as written
                </option>
              </select>
            </label>
            <button
              onClick={() =>
                void work(async () => {
                  await update(
                    await request<View>(root + "/settings", "PATCH", {
                      expected_revision: view.project.revision,
                      route,
                      stage,
                      session_goal: goal,
                      evaluation_target: target,
                    }),
                  );
                })
              }
            >
              Save project settings
            </button>
          </details>
        )}
        {active === "Literature" && (
          <p>
            Compare only admitted supplied material. A closest predecessor need
            not be a rival. Retrieval absence never establishes a literature
            gap. Source claims, your interpretation and proposed synthesis are
            separate records of meaning.
          </p>
        )}
        {active === "Argument" && (
          <p>
            {view.project.route === "EXPLAIN"
              ? "Develop because-logic, definitions, conditions and discriminating implications; unknowns remain explicit."
              : view.project.route === "ESTABLISH"
                ? "Specify what will become known and how artifacts are excluded. An explanatory mechanism is not required."
                : "Specify the existing claim, unresolved uncertainty and informative test. A new mechanism is not required."}
          </p>
        )}
        {active === "Alternatives" && (
          <p>
            Add distinct plausible accounts, including their source or explicit
            assumption, shared and distinguishing implications, and evidence
            that could weaken them. An unaddressed alternative is not itself
            evidence against the focal account.
          </p>
        )}
        {active === "Study" && (
          <p>
            What claim does this design actually let us make? Proposed evidence
            and user-reported completed evidence remain distinct; the app does
            not execute data or reproduce analyses.
          </p>
        )}
        {active === "Usefulness" && (
          <p>
            Record who could use an insight and how. Practical relevance does
            not increase scholarly contribution automatically; proposed use is
            not demonstrated impact.
          </p>
        )}
        {active === "Next Actions" && (
          <p>
            Prefer a short ordered set of tasks that can change a named
            unresolved judgment. Suggestions require adoption; saving does not
            execute the research.
            <a href={root + "/exports/plan"} download>
              Export next-action plan Markdown
            </a>
          </p>
        )}
        {active === "Literature" && (
          <details>
            <summary>Source shelf and versions</summary>
            <ul>
              {view.sources.map((item) => (
                <li key={item.source.document_id}>
                  {item.source.title} · v{item.version} · {item.state} ·{" "}
                  {item.admitted ? "admitted" : "excluded"} ·{" "}
                  {item.anchors.length} supplied anchors; no exhaustive coverage
                </li>
              ))}
            </ul>
            <label>
              Source to revise
              <select
                aria-label="Source to revise"
                value={source}
                onChange={(e) => setSource(e.target.value)}
              >
                <option value="">Choose an admitted literature source</option>
                {view.sources
                  .filter(
                    (item) =>
                      item.admitted && item.source.role === "literature",
                  )
                  .map((item) => (
                    <option
                      value={item.source.document_id}
                      key={item.source.document_id}
                    >
                      {item.source.title}
                    </option>
                  ))}
              </select>
            </label>
            <label>
              New source-version text
              <textarea
                value={versionText}
                onChange={(e) => setVersionText(e.target.value)}
              />
            </label>
            <button
              disabled={!source || !versionText.trim()}
              onClick={() =>
                void work(async () => {
                  const selected = view.sources.find(
                    (item) => item.source.document_id === source,
                  )!;
                  await update(
                    await request<View>(
                      root + "/sources/" + source + "/versions",
                      "POST",
                      {
                        expected_revision: view.project.revision,
                        title: selected.source.title,
                        attribution:
                          selected.source.attribution ?? "User-supplied source",
                        text: versionText,
                        authorized: true,
                        admitted: true,
                      },
                    ),
                  );
                  setVersionText("");
                })
              }
            >
              Save source version
            </button>
          </details>
        )}
        {review?.target_workspace === active && (
          <aside aria-label="Targeted workspace review">
            <h3>Latest focused check</h3>
            <p>
              {review.snapshot.scope} · revision{" "}
              {review.snapshot.project.revision} ·{" "}
              {review.stale ? "affected by change" : "current for this scope"}
            </p>
            <p>{review.summary.obstacle}</p>
            <p>{review.summary.next_action}</p>
            <button onClick={() => navigate("Review")}>
              Open focused review
            </button>
          </aside>
        )}
        {fieldLabels && (
          <>
            {catalog?.targeted_workspaces.includes(active) && (
              <button onClick={() => void work(checkWorkspace)}>
                Check {active.toLowerCase()} only
              </button>
            )}
            <button onClick={() => void work(propose)}>
              Propose{" "}
              {active === "Next Actions"
                ? "bounded action"
                : active.toLowerCase() + " change"}
            </button>
            {records
              .slice()
              .sort((a, b) => {
                const order = (o: typeof a) =>
                  o.payload.kind === "research_record"
                    ? (o.payload.fields.find((f) => f.key === "order")?.text ??
                      "")
                    : "";
                return order(a).localeCompare(order(b), undefined, {
                  numeric: true,
                });
              })
              .map((obj) => (
                <article
                  className="research-record"
                  key={obj.object_id}
                  aria-label={
                    obj.payload.kind === "research_record"
                      ? obj.payload.title
                      : "Record"
                  }
                >
                  <h3>
                    {obj.payload.kind === "research_record"
                      ? obj.payload.title
                      : obj.object_id}
                  </h3>
                  <p>
                    Origin: {obj.origin} · Adoption: {obj.adoption} · Evidence:{" "}
                    {obj.evidence_state} · Freshness: {obj.freshness}
                  </p>
                  {obj.reason && <p>{obj.reason}</p>}
                  {obj.payload.kind === "research_record" && (
                    <dl>
                      {obj.payload.fields.map((f) => (
                        <div key={f.key}>
                          <dt>{fieldLabels[f.key] ?? f.key}</dt>
                          <dd>
                            {f.text ?? "Not known yet"}{" "}
                            <small>
                              ({f.origin}; {f.state})
                            </small>
                          </dd>
                        </div>
                      ))}
                    </dl>
                  )}
                  {obj.source_refs.map((ref, i) => (
                    <button
                      key={i}
                      onClick={() =>
                        void work(async () => {
                          const passage = await request<{ text: string }>(
                            root +
                              "/sources/" +
                              ref.document_id +
                              "/" +
                              ref.version +
                              "/" +
                              ref.anchor_id,
                          );
                          alertReader(passage.text);
                        })
                      }
                    >
                      Open linked source v{ref.version}
                    </button>
                  ))}
                  {obj.support_dispositions.length > 0 && (
                    <details>
                      <summary>Focused support dispositions</summary>
                      <ul>
                        {obj.support_dispositions.map((d) => (
                          <li key={d.target}>
                            {d.target}: {d.disposition} — {d.reason}
                          </li>
                        ))}
                      </ul>
                    </details>
                  )}
                  <button onClick={() => edit(obj)}>Edit record</button>
                  {obj.adoption === "proposed" && (
                    <>
                      <button
                        disabled={obj.freshness !== "current"}
                        onClick={() =>
                          void work(async () => {
                            await update(
                              await request<View>(
                                root +
                                  "/proposals/" +
                                  obj.object_id +
                                  "/decision",
                                "POST",
                                {
                                  expected_revision: view.project.revision,
                                  action: "accepted",
                                  reason:
                                    "Adopted as project representation, not verified evidence",
                                },
                              ),
                            );
                          })
                        }
                      >
                        Accept suggestion
                      </button>
                      <button
                        onClick={() =>
                          void work(async () => {
                            await update(
                              await request<View>(
                                root +
                                  "/proposals/" +
                                  obj.object_id +
                                  "/decision",
                                "POST",
                                {
                                  expected_revision: view.project.revision,
                                  action: "rejected",
                                  reason: "Not adopted; original retained",
                                },
                              ),
                            );
                          })
                        }
                      >
                        Reject suggestion
                      </button>
                    </>
                  )}
                </article>
              ))}
            <details
              key={active + (editing[active] ?? "new")}
              open={records.length === 0 || !!editing[active]}
            >
              <summary>
                {editing[active]
                  ? "Edit selected record"
                  : "Add a research record"}
              </summary>
              <label>
                Record title
                <input
                  value={titles[active] ?? ""}
                  onChange={(e) =>
                    setTitles({ ...titles, [active]: e.target.value })
                  }
                />
              </label>
              {Object.entries(fieldLabels).map(([key, label]) => (
                <div key={key} className="research-field">
                  <label htmlFor={active + "-" + key}>{label}</label>
                  {catalog?.choices[key] ? (
                    <select
                      id={active + "-" + key}
                      value={drafts[active]?.[key] ?? ""}
                      onChange={(e) =>
                        setDrafts({
                          ...drafts,
                          [active]: {
                            ...drafts[active],
                            [key]: e.target.value,
                          },
                        })
                      }
                    >
                      <option value="">Not known yet</option>
                      {catalog.choices[key].map((choice) => (
                        <option key={choice}>{choice}</option>
                      ))}
                    </select>
                  ) : (
                    <textarea
                      id={active + "-" + key}
                      value={drafts[active]?.[key] ?? ""}
                      onChange={(e) =>
                        setDrafts({
                          ...drafts,
                          [active]: {
                            ...drafts[active],
                            [key]: e.target.value,
                          },
                        })
                      }
                    />
                  )}
                  <label htmlFor={active + "-state-" + key}>
                    {label} — evidence / information state
                  </label>
                  <select
                    id={active + "-state-" + key}
                    value={
                      states[active]?.[key] ??
                      (drafts[active]?.[key]?.trim()
                        ? "specified_but_untested"
                        : "missing")
                    }
                    onChange={(e) =>
                      setStates({
                        ...states,
                        [active]: {
                          ...states[active],
                          [key]: e.target.value as Field["state"],
                        },
                      })
                    }
                  >
                    <option value="missing">Not known yet / missing</option>
                    <option value="specified_but_untested">
                      Specified but untested
                    </option>
                    <option value="not_inspected">
                      Needs a source / not inspected
                    </option>
                    <option value="not_applicable">
                      Not part of this contribution
                    </option>
                    <option value="contested">Contested</option>
                    <option value="contradicted">
                      Contradicted (reported)
                    </option>
                  </select>
                </div>
              ))}
              <label>
                Supporting passage
                {preservedRefs.length > 0 && (
                  <small>
                    Existing source/version/anchor references are retained until
                    you choose a new passage.
                  </small>
                )}
                <select
                  aria-label="Supporting passage"
                  value={supportingAnchor}
                  onChange={(e) => {
                    setSupportingAnchor(e.target.value);
                    setPreservedRefs([]);
                  }}
                >
                  <option value="">No source attached</option>
                  {view.sources
                    .filter((s) => s.admitted)
                    .flatMap((s) =>
                      s.anchors.map((a, i) => (
                        <option
                          value={
                            i === 0
                              ? s.source.document_id
                              : s.source.document_id + "|" + a.anchor_id
                          }
                          key={s.source.document_id + a.anchor_id}
                        >
                          {s.source.title} · v{s.version} · lines {a.line_start}
                          –{a.line_end}
                        </option>
                      )),
                    )}
                </select>
              </label>
              <label>
                Depends on record
                <select
                  aria-label="Depends on record"
                  value={dependsOn}
                  onChange={(e) => setDependsOn(e.target.value)}
                >
                  <option value="">
                    {editing[active]
                      ? "Keep recorded dependencies"
                      : "Workspace dependencies only"}
                  </option>
                  {editing[active] && (
                    <option value="__clear">
                      Remove explicit dependencies
                    </option>
                  )}
                  {view.project.objects
                    .filter((o) => o.adoption === "accepted")
                    .map((o) => (
                      <option key={o.object_id} value={o.object_id}>
                        {o.payload.kind === "research_record"
                          ? o.payload.title
                          : o.payload.kind}
                      </option>
                    ))}
                </select>
              </label>
              <label>
                Change classification
                <select
                  aria-label="Change classification"
                  value={classification}
                  onChange={(e) => setClassification(e.target.value)}
                >
                  <option value="substantive">
                    Changes research meaning / uncertainty about impact
                  </option>
                  <option value="wording">
                    Wording only; meaning unchanged
                  </option>
                  <option value="resources">
                    Resource / feasibility change only
                  </option>
                </select>
              </label>
              <button onClick={() => void work(save)}>
                Save {active.toLowerCase()} record
              </button>
              {editing[active] && (
                <button
                  onClick={() => {
                    setEditing({ ...editing, [active]: null });
                    setDrafts({ ...drafts, [active]: {} });
                  }}
                >
                  Keep original; start another record
                </button>
              )}
            </details>
          </>
        )}
        {active === "History" && history && (
          <>
            <h3>Revisions and adoption history</h3>
            {history.revisions.map((p) => (
              <details key={p.revision}>
                <summary>
                  Revision {p.revision} · {p.route} · {p.stage}
                </summary>
                <p>{p.session_goal}</p>
                <ul>
                  {p.objects.map((o) => (
                    <li key={o.object_id}>
                      {o.payload.kind === "research_record"
                        ? o.payload.title
                        : o.payload.kind}{" "}
                      · {o.origin} · {o.adoption} · {o.evidence_state}
                    </li>
                  ))}
                </ul>
                <a href={root + "/history/" + p.revision + "/export"} download>
                  Export revision {p.revision} JSON
                </a>
              </details>
            ))}
            <h3>User decisions</h3>
            <ul>
              {history.actions.map((a, i) => (
                <li key={i}>
                  Revision {a.revision}: {a.action} — {a.reason}
                </li>
              ))}
            </ul>
            <h3>Source versions</h3>
            <ul>
              {history.source_versions.map((s) => (
                <li key={s.document_id + s.version}>
                  {s.role} · version {s.version} · {s.state}
                </li>
              ))}
            </ul>
            <h3>Immutable reviews</h3>
            {view.reviews.map((r) => (
              <button
                key={r.snapshot_id}
                onClick={() =>
                  void work(async () => {
                    showReview(
                      await request<Review>(root + "/reviews/" + r.snapshot_id),
                    );
                    navigate("Review");
                  })
                }
              >
                Open {r.workspace ?? "project"} review of revision {r.revision}
                {r.stale ? " · affected" : ""}
              </button>
            ))}
          </>
        )}
        {reader && (
          <aside aria-label="Linked source reader">
            <h3>Original linked passage</h3>
            <pre>{reader}</pre>
            <button onClick={() => setReader(null)}>Close source reader</button>
          </aside>
        )}
      </section>
    </>
  );
  function alertReader(text: string) {
    setReader(text);
  }
}
