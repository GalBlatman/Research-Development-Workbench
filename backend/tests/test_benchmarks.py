import hashlib
import json
from pathlib import Path

import pytest

from benchmarks.evaluator import BlindEvaluator
from benchmarks.fixtures import synthetic
from benchmarks.metrics import aggregate, compare
from benchmarks.runner import Case, Runner
from benchmarks.store import AdminStore
from benchmarks.variants import construct, freeze, validate_import
from domain.benchmark import (
    BenchmarkExpectation,
    Block,
    Feature,
    Judgment,
    Mutation,
    Observation,
    RunBudget,
    RunConfiguration,
    Split,
    Transformation,
)
from domain.models import Route
from model_adapters.config import ProviderConfig
from model_adapters.fake import FakeModel
from model_adapters.openai import OpenAIAdapter, policy_contract
from persistence.repository import AccessDenied


def configuration(mode="WORKBENCH", component="FULL", provider="fake", parameters=()):
    return RunConfiguration(
        mode=mode,
        component=component,
        provider=provider,
        model="gpt-6-sol" if provider == "openai" else FakeModel.configuration,
        parameters=parameters,
        budget=RunBudget(max_calls=4, max_tokens=500000, max_cost_usd=5),
        code_commit="419b96fc188951305be34a09c904082246b74052",
    )


def runner(tmp_path, manifest, factory=FakeModel):
    projects, cases = synthetic()
    splits = freeze(projects, "synthetic-splits-v1")
    store = AdminStore(tmp_path / "admin")
    store.freeze(splits)
    for project in projects:
        store.import_project(project, splits)
    for case in cases:
        store.save_variant(case.variant, case.project, splits)
        store.freeze_expectations(case.variant, case.expectations)
    return (Runner(store, tmp_path / "runtime", manifest, splits, factory), projects, cases)


@pytest.mark.parametrize("route", tuple(Route))
def test_route_questions_exact_authority(tmp_path, manifest, route):
    projects, cases = synthetic()
    case = next(c for c in cases if c.project.route == route)
    evaluator = BlindEvaluator(case.variant.packet, FakeModel(), manifest, tmp_path / "isolated")
    criteria = policy_contract(evaluator.task("FULL"))
    if route == "EXPLAIN":
        assert "route_questions" not in criteria
    else:
        rubric = (Path(__file__).resolve().parents[2] / "policies/rubric-v4.md").read_text(
            encoding="utf-8"
        )
        rows = [
            line.split("|")[1:-1]
            for line in rubric.splitlines()
            if line.startswith("| **") and len(line.split("|")) == 5 and "?" in line
        ]
        index = 1 if route == "ESTABLISH" else 2
        assert criteria["route_questions"] == {
            row[0].strip().strip("*"): row[index].strip() for row in rows
        }
        assert not set(criteria["route_questions"].values()) & {
            row[3 - index].strip() for row in rows
        }
    evaluator.close()


@pytest.mark.parametrize("split", tuple(Split))
def test_frozen_split_rejects_import(tmp_path, split):
    projects, _ = synthetic()
    frozen = freeze(projects, "v1")
    p = projects[0]
    if p.split != split:
        with pytest.raises(ValueError, match="mismatch"):
            validate_import(p.model_copy(update={"split": split}), frozen)
    with pytest.raises(ValueError):
        freeze((p, p), "v1")
    with pytest.raises(ValueError):
        validate_import(p.model_copy(update={"version": "changed"}), frozen)


@pytest.mark.parametrize(
    "name",
    ("hidden", "pair", "degraded", "metadata", "restored", "reveal-0", "reveal-1", "reveal-2"),
)
def test_variants_content_and_provenance(name):
    _, cases = synthetic()
    c = next(c for c in cases if c.variant.variant_id == "synthetic-EXPLAIN-" + name)
    text = c.variant.packet.model_dump_json()
    assert "Fictional Journal" not in text and "doi:synthetic" not in text
    assert "transformation" not in text and "gold" not in text
    if name in ("hidden", "pair", "degraded", "reveal-0"):
        assert "direct count" not in text
    if name in ("pair", "reveal-0", "reveal-1"):
        assert "shared workload" not in text
    if name == "degraded":
        assert "meeting attendance" in text
    if name in ("restored", "reveal-1", "reveal-2"):
        assert "direct count" in text
    if name == "restored":
        assert c.variant.mutation.parent_variant.endswith("degraded")


def test_unknown_target_restore_and_explain_only():
    projects, cases = synthetic()
    frozen = freeze(projects, "v1")
    with pytest.raises(ValueError):
        construct(
            projects[0],
            Mutation(
                transformation=Transformation.RESTORE,
                targets=(Feature.MEASURES,),
                parent_variant="absent",
            ),
            "v",
            frozen,
        )
    with pytest.raises(ValueError):
        construct(
            projects[1],
            Mutation(transformation=Transformation.HIDE, targets=(Feature.MECHANISM,)),
            "v",
            frozen,
        )


def test_actual_repository_boundary(tmp_path, manifest):
    _, cases = synthetic()
    case = next(c for c in cases if c.variant.variant_id.endswith("EXPLAIN-hidden"))
    evaluator = BlindEvaluator(case.variant.packet, FakeModel(), manifest, tmp_path / "isolated")
    repository = evaluator.workbench.repository
    with pytest.raises(AccessDenied):
        repository.project(evaluator.workbench.scope(case.project.benchmark_id))
    with pytest.raises(AccessDenied):
        repository.source(evaluator.workbench.scope(evaluator.project_id), "rating:8")
    exported = evaluator.export()
    assert "direct count" not in exported and "gold" not in exported
    assert not hasattr(repository, "gold") and not hasattr(evaluator, "store")
    with pytest.raises(AccessDenied):
        repository.project(evaluator.workbench.scope("synthetic-EXPLAIN-intact"))
    evaluator.close()


@pytest.mark.parametrize("route", tuple(Route))
@pytest.mark.parametrize(
    "mode,component", (("WORKBENCH", "FULL"), ("WORKBENCH", "Argument"), ("BASELINE", "FULL"))
)
def test_fake_execution_routes_modes(tmp_path, manifest, route, mode, component):
    r, _, cases = runner(tmp_path, manifest)
    case = next(c for c in cases if c.project.route == route)
    run = r.execute(case, configuration(mode, component))
    if component == "Argument" and route != "EXPLAIN":
        assert run.status == "FAILED" and run.failure_type == "ValueError"
        return
    assert run.status == "SUCCEEDED", run.failure_type
    assert run.observation.judgments
    if component == "Argument":
        assert [j.key for j in run.observation.judgments] == ["rating:4", "rating:5"]
        assert "interpretation" not in run.components
    if mode == "BASELINE":
        assert run.components == ("baseline",) and run.calls == 1 and run.policy_json is None
    else:
        assert run.policy_json
    assert (
        run.package_hash
        and run.variant_hash
        and run.split_hash
        and run.rubric_hash
        and run.prompt_hashes
    )
    assert run.input_tokens is None and run.estimated_cost_usd is None
    with pytest.raises(FileExistsError):
        r.store.save_run(run)
    assert r.execute(case, configuration(mode, component)) is None
    assert r.execute(case, configuration(mode, component), rerun=True).run_id != run.run_id


def test_metrics_explicit_uncertainty_invariance_direction_restoration():
    projects, _ = synthetic()
    old = Observation(
        judgments=(
            Judgment(key="rating:8", state="ASSESSED", value=7),
            Judgment(key="rating:3", state="ASSESSED", value=5),
        )
    )
    new = Observation(
        judgments=(
            Judgment(key="rating:8", state="PENDING"),
            Judgment(key="rating:3", state="ASSESSED", value=5),
        ),
        action_targets=("inspect_measure",),
    )
    common = dict(
        feature=Feature.MEASURES,
        judgment="rating:8",
        reference_variant="intact",
        invariant_judgments=("rating:3",),
        acceptable_states=("PENDING",),
        forbidden_states=("ASSESSED",),
        action_target="inspect_measure",
    )
    result = compare(
        new,
        (
            BenchmarkExpectation(behavior="detect", **common),
            BenchmarkExpectation(behavior="withhold", **common),
        ),
        {"intact": old},
        projects[0],
    )
    assert result.metrics[0].detection.numerator == 1
    assert result.metrics[0].invariance.numerator == 1
    assert result.metrics[1].withholding.numerator == 1
    assert result.metrics[0].state.numerator == 1 and result.metrics[0].action.numerator == 1
    hallucinated = new.model_copy(
        update={
            "judgments": (Judgment(key="rating:8", state="ASSESSED", value=7),),
            "output_text": projects[0].gold[0].content,
        }
    )
    hidden = projects[0].model_copy(
        update={"gold": tuple(g.model_copy(update={"observable": False}) for g in projects[0].gold)}
    )
    result = compare(
        hallucinated,
        (BenchmarkExpectation(behavior="refuse_infer", **common),),
        {"intact": old},
        hidden,
    )
    assert result.metrics[0].withholding.numerator == 0 and result.diagnostics
    result = compare(
        old,
        (
            BenchmarkExpectation(
                feature=Feature.MEASURES,
                behavior="restore",
                judgment="rating:8",
                reference_variant="intact",
            ),
        ),
        {"intact": old},
        projects[0],
    )
    assert (
        result.metrics[0].restoration.numerator == 0
    )  # No degraded observation: no restoration credit
    lower = Observation(
        judgments=(
            Judgment(
                key="rating:8", state="ASSESSED", value=3, source_refs=("allowed", "forbidden")
            ),
            Judgment(key="rating:3", state="PENDING"),
        ),
        authorized_anchors=("allowed",),
    )
    result = compare(
        lower,
        (
            BenchmarkExpectation(
                feature=Feature.MEASURES,
                behavior="downgrade",
                judgment="rating:8",
                direction="lower",
                reference_variant="intact",
                invariant_judgments=("rating:3",),
            ),
        ),
        {"intact": old},
        projects[0],
    )
    assert result.metrics[0].direction.numerator == 1
    assert (
        result.metrics[0].attribution.numerator == 1
        and result.metrics[0].attribution.denominator == 2
    )
    assert result.invariant_violations == ("rating:3",)


def test_batch_resume_budgets_and_nested_papers(tmp_path, manifest):
    r, _, cases = runner(tmp_path, manifest)
    config = configuration("BASELINE")
    progress = []
    runs = r.batch(
        cases,
        config,
        concurrency=2,
        max_calls=8,
        max_tokens=1000000,
        max_cost_usd=10,
        progress=lambda v, s: progress.append((v, s)),
    )
    assert len(runs) == 2 and len(progress) == 2
    more = r.batch(cases, config, max_calls=4, max_tokens=500000, max_cost_usd=5)
    assert len(more) == 1 and not {x.run_id for x in runs} & {x.run_id for x in more}
    assert aggregate(runs)["paper_count"] == 1 and aggregate(runs)["case_count"] == 2
    r.stop.set()
    assert r.batch(cases, config, max_calls=4, max_tokens=500000, max_cost_usd=5) == ()
    with pytest.raises(ValueError):
        r.batch(cases, config, concurrency=5, max_calls=4, max_tokens=500000, max_cost_usd=5)


def test_no_credentials_in_configuration():
    with pytest.raises(ValueError):
        configuration(parameters=(("api_key", "synthetic-secret"),))


@pytest.mark.parametrize("route", tuple(Route))
@pytest.mark.parametrize(
    "mode,component", (("WORKBENCH", "FULL"), ("WORKBENCH", "Argument"), ("BASELINE", "FULL"))
)
def test_mock_real_provider_privacy_schema_usage_and_route(
    tmp_path, manifest, monkeypatch, route, mode, component
):
    from dataclasses import asdict

    import httpx
    from test_provider import envelope, proposed, reference

    from domain.application import AssessmentTask, CandidateReview, InterpretationTask

    requests = []
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-placeholder")

    def handler(request):
        body = json.loads(request.content)
        requests.append(body)
        payload = json.loads(body["input"])
        kind = body["text"]["format"]["name"]
        if kind == "rdw_interpretation":
            output = (
                FakeModel()
                .interpret(InterpretationTask.model_validate(payload))
                .model_dump(mode="json")
            )
        elif kind in ("rdw_evaluation", "rdw_baseline"):
            task = AssessmentTask.model_validate(
                {k: v for k, v in payload.items() if k != "criteria"}
            )
            output = proposed(task)
        else:
            task = AssessmentTask.model_validate(payload["assessment_task"])
            candidate = CandidateReview.model_validate(payload["candidate"])
            output = {
                "summary": candidate.summary.model_dump(mode="json"),
                "decisions": [
                    {
                        "target": t,
                        "disposition": "unresolved",
                        "reason": "Synthetic limited evidence; preserve uncertainty",
                        "source_refs": [reference(task.context)],
                    }
                    for t in payload["targets"]
                ],
            }
        return httpx.Response(200, json=envelope(output))

    pc = ProviderConfig(provider="openai", retries=0)
    config = configuration(
        mode,
        component,
        "openai",
        tuple((k, v) for k, v in asdict(pc).items() if k not in ("provider", "model")),
    )
    r, _, cases = runner(
        tmp_path,
        manifest,
        lambda: OpenAIAdapter(pc, httpx.Client(transport=httpx.MockTransport(handler))),
    )
    case = next(
        c for c in cases if c.project.route == route and c.variant.variant_id.endswith("hidden")
    )
    run = r.execute(case, config)
    if component == "Argument" and route != "EXPLAIN":
        assert run.status == "FAILED" and run.failure_type == "ValueError"
        return
    assert run.status == "SUCCEEDED", run.failure_type
    assert (
        run.receipt
        and run.input_tokens == 400 * len(requests)
        and run.output_tokens == 150 * len(requests)
    )
    assert run.estimated_cost_usd > 0 and run.calls == len(requests)
    if mode == "BASELINE":
        prompt = (Path(__file__).resolve().parents[1] / "prompts/baseline-v3.md").read_text(
            encoding="utf-8"
        )
        assert requests[0]["instructions"] == prompt
        assert (
            dict(run.prompt_hashes)["baseline-v3.md"] == hashlib.sha256(prompt.encode()).hexdigest()
        )
        call = run.receipt.calls[0]
        assert call.prompt_version == "baseline-v3"
        criteria = json.loads(requests[0]["input"])["criteria"]
        assert (
            call.prompt_sha256
            == hashlib.sha256(
                (prompt + json.dumps(criteria, sort_keys=True, ensure_ascii=False)).encode()
            ).hexdigest()
        )

    assert len(requests) == (1 if mode == "BASELINE" else 3 if component == "FULL" else 2)
    for body in requests:
        assert (
            body["model"] == "gpt-6-sol" and body["store"] is False and body["background"] is False
        )
        assert "tools" not in body and body["text"]["format"]["strict"] is True
        payload = json.loads(body["input"])
        assert "direct count of handoffs" not in body["input"]
        assert (
            "Fictional Journal" not in body["input"]
            and "synthetic-EXPLAIN-hidden" not in body["input"]
        )
        assert not {"gold", "expectations", "mutation", "split", "visibility"} & payload.keys()
        if "criteria" in payload:
            assert ("route_questions" in payload["criteria"]) == (
                route != "EXPLAIN" and component == "FULL"
            )
            if component == "Argument":
                assert set(payload["criteria"]["dimensions"]) == {"4", "5"}


def test_baseline_same_admitted_packet_configuration(tmp_path, manifest):
    _, cases = synthetic()
    case = cases[0]
    a = BlindEvaluator(case.variant.packet, FakeModel(), manifest, tmp_path / "a")
    b = BlindEvaluator(case.variant.packet, FakeModel(), manifest, tmp_path / "b")
    assert a.workbench.adapter.configuration == b.workbench.adapter.configuration
    assert [(p.source.role, p.text) for p in a.task("FULL").context.passages] == [
        (p.source.role, p.text) for p in b.task("FULL").context.passages
    ]
    assert policy_contract(a.task("FULL")) == policy_contract(b.task("FULL"))
    a.close()
    b.close()


def test_interrupted_claim_no_retry_failure_isolated(tmp_path, manifest):
    from model_adapters.runtime import ProviderFailure

    r, _, cases = runner(tmp_path, manifest)
    config = configuration("BASELINE")
    key = r.store.cache_key(cases[0].variant, r.splits, config)
    assert r.store.claim(key, "interrupted-attempt")
    assert r.execute(cases[0], config) is None

    class Failing(FakeModel):
        def assess(self, task):
            raise ProviderFailure("TIMEOUT_UNCERTAIN")

    r.adapter_factory = Failing
    failed = r.execute(cases[1], config)
    assert failed.status == "FAILED" and failed.failure_type == "TIMEOUT_UNCERTAIN"
    assert r.execute(cases[1], config) is None
    r.adapter_factory = FakeModel
    assert r.execute(cases[2], config).status == "SUCCEEDED"


def test_cache_split_mode_configuration_isolation(tmp_path, manifest):
    r, projects, cases = runner(tmp_path, manifest)
    key = r.store.cache_key(cases[0].variant, r.splits, configuration())
    assert key != r.store.cache_key(cases[0].variant, r.splits, configuration("BASELINE"))
    modified = cases[0].variant.model_copy(update={"split": Split.HELD_OUT})
    assert key != r.store.cache_key(modified, r.splits, configuration())
    with pytest.raises(ValueError):
        r.execute(Case(projects[0], modified), configuration())
    with pytest.raises(ValueError):
        r.store.save_variant(modified, projects[0], r.splits)


def test_neutral_paraphrase_diagnostic_and_reveal_order():
    from benchmarks.metrics import equivalent_diagnostic

    projects, cases = synthetic()
    frozen = freeze(projects, "v1")
    p = projects[0]
    anonymized = construct(
        p,
        Mutation(
            transformation=Transformation.METADATA,
            replacements=(
                Block(
                    block_id="question",
                    text="Synthetic equivalent: do fictional scheduling changes influence handoffs?",
                    features=(Feature.QUESTION,),
                ),
            ),
        ),
        "equivalent",
        frozen,
    )
    assert "equivalent" in anonymized.packet.blocks[0].text
    old = Observation(judgments=(Judgment(key="rating:8", state="PENDING"),))
    new = Observation(judgments=(Judgment(key="rating:8", state="ASSESSED", value=5),))
    assert equivalent_diagnostic(old, new) == ("Equivalent-packet judgment changed: rating:8",)
    prior = next(c.variant for c in cases if c.variant.variant_id.endswith("EXPLAIN-reveal-1"))
    with pytest.raises(ValueError):
        construct(
            p,
            Mutation(
                transformation=Transformation.REVEAL,
                targets=(Feature.MEASURES, Feature.RIVALS),
                reveal_order=(Feature.MEASURES, Feature.RIVALS),
                reveal_count=0,
            ),
            "backwards",
            frozen,
            prior,
        )


def test_actual_concurrency_bound_and_resumed_batch_ceiling(tmp_path, manifest):
    import threading
    import time

    lock = threading.Lock()
    active = peak = 0

    class SlowFake(FakeModel):
        def assess(self, task):
            nonlocal active, peak
            with lock:
                active += 1
                peak = max(peak, active)
            try:
                time.sleep(0.02)
                return super().assess(task)
            finally:
                with lock:
                    active -= 1

    r, _, cases = runner(tmp_path, manifest, SlowFake)
    config = configuration("BASELINE")
    args = dict(
        concurrency=2, max_calls=16, max_tokens=2000000, max_cost_usd=20, batch_id="bounded"
    )
    first = r.batch(cases, config, **args)
    assert len(first) == 4 and 1 < peak <= 2
    assert r.batch(cases, config, **args) == ()


def test_reference_runs_scoped_and_comparison_recorded(tmp_path, manifest):
    r, projects, cases = runner(tmp_path, manifest)
    config = configuration("BASELINE")
    original = r.execute(cases[0], config)
    expectation = BenchmarkExpectation(
        feature=Feature.MEASURES,
        behavior="unchanged",
        judgment="rating:9",
        reference_variant=cases[0].variant.variant_id,
        invariant_judgments=("rating:2",),
    )
    variant = cases[1].variant.model_copy(
        update={"variant_id": cases[1].variant.variant_id + "-comparison"}
    )
    r.store.save_variant(variant, cases[1].project, r.splits)
    r.store.freeze_expectations(variant, (expectation,))
    target = Case(cases[1].project, variant, (expectation,))
    run = r.execute(target, config, references={original.variant_id: original})
    assert run.reference_run_ids == (original.run_id,)
    assert run.result.metrics[0].invariance.numerator == 2
    wrong = original.model_copy(update={"split": Split.HELD_OUT})
    with pytest.raises(ValueError, match="reference"):
        r.execute(cases[2], config, references={original.variant_id: wrong})


def test_packet_duplicate_feature_blocks_removed_and_parent_restoration():
    projects, _ = synthetic()
    p = projects[0]
    package = p.source_package.model_copy(
        update={
            "blocks": p.source_package.blocks
            + (
                Block(
                    block_id="repeat",
                    text="The same handoff measure appears again.",
                    features=(Feature.MEASURES,),
                ),
            )
        }
    )
    p = p.model_copy(update={"source_package": package})
    frozen = freeze((p,), "v1")
    hidden = construct(
        p,
        Mutation(transformation=Transformation.HIDE, targets=(Feature.MEASURES,)),
        "hidden",
        frozen,
    )
    assert "handoff measure appears again" not in hidden.packet.model_dump_json()
    intact = construct(p, Mutation(transformation=Transformation.INTACT), "intact", frozen)
    restored = construct(
        p,
        Mutation(
            transformation=Transformation.RESTORE,
            targets=(Feature.MEASURES,),
            parent_variant="hidden",
        ),
        "restored",
        frozen,
        hidden,
    )
    assert restored.packet == intact.packet


def test_normal_contract_pending_counts_as_correct_withholding(tmp_path, manifest):
    r, _, cases = runner(tmp_path, manifest)
    case = next(c for c in cases if c.variant.variant_id.endswith("EXPLAIN-hidden"))
    run = r.execute(case, configuration("BASELINE"))
    assert run.result.metrics[0].state.numerator == 1
    assert run.result.metrics[0].withholding.numerator == 1


def test_degraded_original_gold_unobservable():
    _, cases = synthetic()
    degraded = next(c for c in cases if c.variant.variant_id.endswith("EXPLAIN-degraded"))
    assert dict(degraded.variant.visibility)[Feature.MEASURES] is False
