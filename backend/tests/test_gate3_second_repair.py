import json
import subprocess
import sys
from pathlib import Path

import pytest
from test_gate3_benchmark import exchange
from test_provider import adapter
from test_workspaces import check, save
from test_workspaces import workspace_client as workspace_client

from benchmarks.evaluator import BlindEvaluator
from benchmarks.metrics import compare
from benchmarks.variants import construct, content_hash, freeze
from domain.benchmark import (
    BenchmarkExpectation,
    BenchmarkPackage,
    Feature,
    FrozenExpectations,
    Mutation,
    Transformation,
)
from domain.models import Verification
from domain.research import WorkspaceProposal
from policy_engine.manifest import Manifest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def manifest():
    return Manifest.model_validate_json((ROOT / "policies/rubric-v5.manifest.json").read_text())


def package_with_variant(original, variant):
    data = original.model_dump(mode="json")
    data["variants"].append(variant.model_dump(mode="json"))
    data["expectations"].append(
        FrozenExpectations(
            variant_id=variant.variant_id, variant_hash=content_hash(variant), expectations=()
        ).model_dump(mode="json")
    )
    return data


@pytest.mark.parametrize("kind", (Transformation.INTACT, Transformation.METADATA))
def test_equivalent_anonymized_intact_material_remains_observable(kind):
    package = exchange()
    project = package.projects[0]
    block = project.source_package.blocks[1]
    variant = construct(
        project,
        Mutation(transformation=kind, replacements=(block,)),
        "equivalent-intact",
        package.manifest,
    )
    assert block.text in [b.text for b in variant.packet.blocks]
    assert dict(variant.visibility)[Feature.MEASURES] is True, (
        "Identity replacement cannot hide still-intact feature"
    )


@pytest.mark.parametrize("cli", (False, True))
def test_degradation_cannot_collide_with_untouched_block_identity(tmp_path, cli):
    package = exchange()
    project = package.projects[0]
    replacement = project.source_package.blocks[1].model_copy(
        update={
            "block_id": project.source_package.blocks[0].block_id,
            "text": "Synthetic degraded measurement proxy",
        }
    )
    mutation = Mutation(
        transformation=Transformation.DEGRADE,
        targets=(Feature.MEASURES,),
        replacements=(replacement,),
    )
    with pytest.raises(ValueError, match="collides"):
        construct(project, mutation, "colliding-degradation", package.manifest)
    original = next(
        v
        for v in package.variants
        if v.benchmark_id == project.benchmark_id
        and v.mutation.transformation == Transformation.DEGRADE
    )
    variant = original.model_copy(
        update={"variant_id": "colliding-degradation", "mutation": mutation}
    )
    data = package_with_variant(package, variant)
    if cli:
        file = tmp_path / "bad.json"
        file.write_text(json.dumps(data))
        out = tmp_path / "admin"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "benchmarks",
                "--package",
                str(file),
                "--output",
                str(out),
                "--validate-only",
            ],
            cwd=ROOT / "backend",
            capture_output=True,
        )
        assert result.returncode != 0, "Colliding mutated block identity was accepted by CLI"
        assert not out.exists()
    else:
        with pytest.raises(ValueError):
            BenchmarkPackage.model_validate(data)


@pytest.mark.parametrize("disposition", ("unresolved", "supported", "needs_revision"))
def test_actual_checked_statement_observation_preserves_disposition(
    tmp_path, monkeypatch, manifest, disposition
):
    def mutate(kind, out):
        if kind == "rdw_checking":
            for d in out["decisions"]:
                if d["target"] == "statement:principal-obstacle":
                    d["disposition"] = disposition
        return out

    model, checker, requests = adapter(monkeypatch, mutate)
    packet = exchange().variants[0].packet
    evaluator = BlindEvaluator(packet, model, manifest, tmp_path / "evaluator")
    try:
        output, _ = evaluator.run("WORKBENCH", "FULL")
        check_record = next(
            d for d in output["checks"] if d["target"] == "statement:principal-obstacle"
        )
        assert check_record["disposition"] == disposition
        observation = evaluator.observe(output)
        statement = next(
            j for j in observation.judgments if j.key == "statement:principal-obstacle"
        )
        if disposition == "unresolved":
            expectation = BenchmarkExpectation(
                feature=Feature.QUESTION, behavior="withhold", judgment=statement.key
            )
            metric = (
                compare(observation, (expectation,), {}, exchange().projects[0])
                .metrics[0]
                .withholding
            )
            assert (metric.numerator, metric.denominator) == (1, 1), (
                "Correct actual checker uncertainty was scored as failure"
            )
        else:
            assert statement.verification == Verification(disposition), (
                "Actual checking disposition discarded"
            )
    finally:
        evaluator.close()
        model.close()


@pytest.mark.parametrize("task", ("Do more research.", "Do more research!"))
def test_generated_workspace_action_cannot_be_placeholder_complete(task):
    fields = {
        "task": task,
        "reason": "TBD.",
        "judgment": "TBD.",
        "input": "TBD.",
        "output": "TBD.",
        "workspace": "Argument",
        "dependency": "TBD.",
        "branches": "TBD.",
    }
    data = {
        "record": {
            "workspace": "Next Actions",
            "title": "Synthetic empty diagnosis",
            "fields": [
                {"key": key, "text": text, "origin": "model_inference", "state": "not_inspected"}
                for key, text in fields.items()
            ],
        },
        "reason": "TBD.",
        "limitations": ["Synthetic only"],
    }
    with pytest.raises(ValueError):
        WorkspaceProposal.model_validate(data)


@pytest.mark.parametrize("workspace", ("Study", "Alternatives", "Literature", "Usefulness"))
def test_other_scientific_workspace_resources_label_cannot_hide_change(workspace_client, workspace):
    client, w, view = workspace_client
    review = check(client, view, workspace)
    key = {
        "Study": "claim",
        "Alternatives": "alternative",
        "Literature": "user_interpretation",
        "Usefulness": "change",
    }[workspace]
    view = save(
        client,
        view,
        workspace,
        {key: "Consequential changed synthetic scientific content"},
        change="resources",
    )
    current = w.review(view["project"]["project_id"], review["snapshot"]["snapshot_id"])
    assert current["stale"] is True


@pytest.mark.parametrize(
    "fault",
    (
        "empty_anchors",
        "wrong_owned_anchor",
        "missing_anchor",
        "missing_intact",
        "missing_degraded",
        "degraded_as_intact",
        "cross_paper",
        "duplicate_owner",
    ),
)
def test_independent_negative_authoring_cli_cases(tmp_path, fault):
    package = exchange()
    data = package.model_dump(mode="json")
    if fault in ("empty_anchors", "wrong_owned_anchor", "missing_anchor", "duplicate_owner"):
        project = package.projects[0]
        if fault == "duplicate_owner":
            block = project.source_package.blocks[1].model_copy(
                update={"features": (Feature.MEASURES, Feature.MEASURES)}
            )
            project = project.model_copy(
                update={
                    "source_package": project.source_package.model_copy(
                        update={
                            "blocks": (project.source_package.blocks[0], block)
                            + project.source_package.blocks[2:]
                        }
                    )
                }
            )
        else:
            refs = {
                "empty_anchors": (),
                "wrong_owned_anchor": ("question",),
                "missing_anchor": ("absent",),
            }[fault]
            project = project.model_copy(
                update={"gold": (project.gold[0].model_copy(update={"source_anchors": refs}),)}
            )
        projects = (project,) + package.projects[1:]
        frozen = freeze(projects, package.manifest.version)
        data["projects"] = [p.model_dump(mode="json") for p in projects]
        data["manifest"] = frozen.model_dump(mode="json")
        seen = {}
        variants = []
        for original in package.variants:
            p = next(p for p in projects if p.benchmark_id == original.benchmark_id)
            v = construct(
                p,
                original.mutation,
                original.variant_id,
                frozen,
                seen.get(original.mutation.parent_variant),
            )
            seen[v.variant_id] = v
            variants.append(v)
        data["variants"] = [v.model_dump(mode="json") for v in variants]
        for a, v in zip(data["expectations"], variants, strict=True):
            a["variant_hash"] = content_hash(v)
    else:
        a = next(a for a in data["expectations"] if a["variant_id"].endswith("-restored"))
        e = a["expectations"][0]
        if fault == "missing_intact":
            e["reference_variant"] = None
        elif fault == "missing_degraded":
            e["degraded_reference"] = None
        elif fault == "degraded_as_intact":
            e["reference_variant"] = e["degraded_reference"]
        else:
            e["reference_variant"] = next(
                v["variant_id"]
                for v in data["variants"]
                if v["benchmark_id"] != data["variants"][0]["benchmark_id"]
                and v["mutation"]["transformation"] == "INTACT_BLIND"
            )
    source = tmp_path / "bad.json"
    source.write_text(json.dumps(data))
    output = tmp_path / "not-registered"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "benchmarks",
            "--package",
            str(source),
            "--output",
            str(output),
            "--validate-only",
        ],
        cwd=ROOT / "backend",
        capture_output=True,
    )
    assert result.returncode != 0 and not output.exists()


@pytest.mark.parametrize("kind", (Transformation.INTACT, Transformation.METADATA))
def test_equivalent_paraphrase_and_restoration_reference(kind):
    package = exchange()
    project = package.projects[0]
    original = project.source_package.blocks[1]
    replacement = original.model_copy(update={"text": "Synthetic equivalent paraphrased measures"})
    intact = construct(
        project,
        Mutation(transformation=kind, replacements=(replacement,)),
        "paraphrased-intact",
        package.manifest,
    )
    assert dict(intact.visibility)[Feature.MEASURES]
    assert intact.observability == intact.visibility
    data = package_with_variant(package, intact)
    artifact = next(e for e in data["expectations"] if e["variant_id"].endswith("-restored"))
    artifact["expectations"][0]["reference_variant"] = intact.variant_id
    assert BenchmarkPackage.model_validate(data)


def test_degradation_is_observable_but_not_intact_and_preserves_unrelated_features():
    package = exchange()
    project = package.projects[0]
    original = project.source_package.blocks[1]
    replacement = original.model_copy(
        update={"block_id": "new-measure-proxy", "text": "Synthetic adjacent proxy"}
    )
    variant = construct(
        project,
        Mutation(
            transformation=Transformation.DEGRADE,
            targets=(Feature.MEASURES,),
            replacements=(replacement,),
        ),
        "valid-new-id",
        package.manifest,
    )
    assert not dict(variant.visibility)[Feature.MEASURES]
    assert dict(variant.observability)[Feature.MEASURES]
    assert dict(variant.visibility)[Feature.QUESTION]
    intact = next(
        v
        for v in package.variants
        if v.benchmark_id == project.benchmark_id
        and v.mutation.transformation == Transformation.INTACT
    )
    for feature, visible in intact.visibility:
        if feature != Feature.MEASURES:
            assert dict(variant.visibility)[feature] == visible
    assert BenchmarkPackage.model_validate(package_with_variant(package, variant))
    hidden = construct(
        project,
        Mutation(transformation=Transformation.HIDE, targets=(Feature.MEASURES,)),
        "hidden-measures",
        package.manifest,
    )
    assert not dict(hidden.observability)[Feature.MEASURES]


def test_duplicate_replacement_identity_rejected_even_with_model_copy():
    package = exchange()
    project = package.projects[0]
    first, second = project.source_package.blocks[:2]
    replacements = (
        first.model_copy(update={"block_id": "duplicate"}),
        second.model_copy(update={"block_id": "duplicate"}),
    )
    with pytest.raises(ValueError, match="Duplicate"):
        Mutation(
            transformation=Transformation.DEGRADE,
            targets=(Feature.QUESTION, Feature.MEASURES),
            replacements=replacements,
        )
    invalid = Mutation(
        transformation=Transformation.DEGRADE, targets=(Feature.QUESTION, Feature.MEASURES)
    ).model_copy(update={"replacements": replacements})
    with pytest.raises(ValueError, match="Duplicate"):
        construct(project, invalid, "bad-duplicate", package.manifest)


@pytest.mark.parametrize("placeholder", (" TBD. ", "tOdO!", "UNKNOWN?", "n/a...", " ;! "))
def test_workspace_placeholder_normalization(placeholder):
    fields = {
        "task": "Review supplied source contrasts",
        "reason": "Resolve a bounded uncertainty",
        "judgment": "Study contrast",
        "input": "Supplied comparison passages",
        "output": "A contrast table",
        "workspace": "Study",
        "dependency": "Current study record",
        "branches": placeholder,
    }
    data = {
        "record": {
            "workspace": "Next Actions",
            "title": "Synthetic task",
            "fields": [
                {"key": k, "text": v, "origin": "model_inference", "state": "not_inspected"}
                for k, v in fields.items()
            ],
        },
        "reason": "Bounded action",
        "limitations": ["Synthetic"],
    }
    with pytest.raises(ValueError):
        WorkspaceProposal.model_validate(data)
    data["record"]["fields"][-1]["text"] = "Revise the claim if the contrast cannot discriminate"
    assert WorkspaceProposal.model_validate(data)


def test_manual_partial_next_action_preserved(workspace_client):
    client, _, view = workspace_client
    updated = save(client, view, "Next Actions", {"task": "TODO"})
    assert updated["project"]["revision"] > view["project"]["revision"]


def test_statement_verification_only_is_separate_and_baseline_not_self_verified(
    tmp_path, monkeypatch, manifest
):
    observations = {}
    for disposition in ("unresolved", "supported"):

        def mutate(kind, out):
            if kind == "rdw_checking":
                for d in out["decisions"]:
                    if d["target"] == "statement:principal-obstacle":
                        d["disposition"] = disposition
            return out

        model, _, _ = adapter(monkeypatch, mutate)
        evaluator = BlindEvaluator(
            exchange().variants[0].packet, model, manifest, tmp_path / disposition
        )
        try:
            output, _ = evaluator.run("WORKBENCH", "FULL")
            observations[disposition] = evaluator.observe(output)
            judgment = next(
                j
                for j in observations[disposition].judgments
                if j.key == "statement:principal-obstacle"
            )
            assert judgment.content == next(
                s["text"] for s in output["statements"] if s["statement_id"] == "principal-obstacle"
            )
            assert judgment.adoption == "proposed" and judgment.evidence_state == "not_inspected"
            assert set(judgment.source_refs) <= set(observations[disposition].authorized_anchors)
        finally:
            evaluator.close()
            model.close()
    expectation = BenchmarkExpectation(
        feature=Feature.QUESTION,
        behavior="detect",
        judgment="statement:principal-obstacle",
        reference_variant="old",
    )
    metric = compare(
        observations["supported"],
        (expectation,),
        {"old": observations["unresolved"]},
        exchange().projects[0],
    ).metrics[0]
    assert metric.detection.numerator == 0 and metric.verification_change.numerator == 1
    withholding = expectation.model_copy(update={"behavior": "withhold", "reference_variant": None})
    assert (
        compare(observations["supported"], (withholding,), {}, exchange().projects[0])
        .metrics[0]
        .withholding.numerator
        == 0
    )
    import httpx
    from test_provider import envelope, proposed

    from domain.application import AssessmentTask
    from model_adapters.config import ProviderConfig
    from model_adapters.openai import OpenAIAdapter

    def baseline_handler(request):
        body = json.loads(request.content)
        assert body["text"]["format"]["name"] == "rdw_baseline"
        payload = json.loads(body["input"])
        task = AssessmentTask.model_validate({k: v for k, v in payload.items() if k != "criteria"})
        return httpx.Response(200, json=envelope(proposed(task)))

    model = OpenAIAdapter(
        ProviderConfig(provider="openai"),
        httpx.Client(transport=httpx.MockTransport(baseline_handler)),
    )
    evaluator = BlindEvaluator(
        exchange().variants[0].packet, model, manifest, tmp_path / "baseline"
    )
    try:
        output, components = evaluator.run("BASELINE", "FULL")
        assert components == ("baseline",) and "checks" not in output
        assert all(
            j.verification == Verification.UNRESOLVED for j in evaluator.observe(output).judgments
        )
    finally:
        evaluator.close()
        model.close()


@pytest.mark.parametrize("collision", ("literature", "question"))
def test_added_unrelated_literature_identity_is_protected(collision):
    from domain.benchmark import Block
    from domain.sources import SourceRole

    project = exchange().projects[0]
    literature = Block(
        block_id="literature",
        text="Synthetic supplied predecessor argument",
        role=SourceRole.LITERATURE,
        features=(Feature.PREDECESSOR,),
    )
    project = project.model_copy(
        update={
            "source_package": project.source_package.model_copy(
                update={"blocks": project.source_package.blocks + (literature,)}
            )
        }
    )
    manifest = freeze((project,), "synthetic-literature-split")
    replacement = project.source_package.blocks[1].model_copy(update={"block_id": collision})
    with pytest.raises(ValueError, match="collides"):
        construct(
            project,
            Mutation(
                transformation=Transformation.DEGRADE,
                targets=(Feature.MEASURES,),
                replacements=(replacement,),
            ),
            "bad",
            manifest,
        )


def test_statement_text_change_is_not_lost_when_checking_needs_revision():
    from domain.benchmark import Judgment, Observation

    old = Observation(
        judgments=(
            Judgment(
                key="statement:principal-obstacle",
                state="proposed",
                content="Original synthetic bounded assertion",
                checking_performed=True,
                verification=Verification.SUPPORTED,
            ),
        )
    )
    revised = Observation(
        judgments=(
            old.judgments[0].model_copy(
                update={
                    "content": "Revised synthetic bounded assertion",
                    "verification": Verification.NEEDS_REVISION,
                }
            ),
        )
    )
    expectation = BenchmarkExpectation(
        feature=Feature.QUESTION,
        behavior="detect",
        judgment="statement:principal-obstacle",
        reference_variant="old",
    )
    metric = compare(revised, (expectation,), {"old": old}, exchange().projects[0]).metrics[0]
    assert metric.detection.numerator == 1 and metric.verification_change.numerator == 1
