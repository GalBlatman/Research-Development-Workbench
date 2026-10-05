import json

import pytest
from test_gate3_final_metrics import manifest as manifest

from benchmarks.calibration import configuration, freeze, summarize
from benchmarks.evaluator import DIMENSIONS, ROUTE_TARGETS, RULE_TARGETS, BlindEvaluator
from benchmarks.fixtures import synthetic
from domain.benchmark import RunConfiguration
from model_adapters.config import ProviderConfig
from model_adapters.fake import FakeModel
from model_adapters.openai import policy_contract


@pytest.mark.parametrize("route", ("EXPLAIN", "ESTABLISH", "TEST"))
@pytest.mark.parametrize(
    "component", ("Argument", "Brief", "Literature", "Study", "Usefulness", "Alternatives")
)
def test_canonical_targeted_contract_exact_scope(tmp_path, manifest, route, component):
    case = next(c for c in synthetic()[1] if c.project.route == route)
    evaluator = BlindEvaluator(case.variant.packet, FakeModel(), manifest, tmp_path / "blind")
    try:
        task = evaluator.task(component, extended=True)
        assert task.dimensions == tuple(
            d for d in DIMENSIONS[component] if route == "EXPLAIN" or d >= 8
        )
        contract = policy_contract(task)
        assert set(contract["dimensions"]) == {str(d) for d in task.dimensions}
        expected_items = ROUTE_TARGETS[component] if route != "EXPLAIN" else ()
        assert set(contract["route_questions"]) == set(expected_items)
        assert set(task.semantic_rule_ids) <= set(RULE_TARGETS[component])
        assert set(r["id"] for r in contract["semantic_rules"]) == set(task.semantic_rule_ids)
        forbidden = (
            "journal",
            "interest_proximity",
            "method_families",
            "private_paper_id",
            "execution_scope",
            "case_id",
        )
        assert not any(
            '"' + key + '"' in json.dumps(task.model_dump(mode="json")) for key in forbidden
        )
        output, components = evaluator.run("WORKBENCH", component, extended=True)
        assert components[0] == "evaluation:" + component
        assert "interpretation" not in components
        assert {r["dimension"] for r in output["assessment"]["ratings"]} == set(task.dimensions)
    finally:
        evaluator.close()


def test_frozen_configuration_cannot_change(tmp_path):
    path = tmp_path / "config.json"
    freeze(path, {"model": "configured-model", "paper_batch": 4})
    freeze(path, {"paper_batch": 4, "model": "configured-model"})
    with pytest.raises(ValueError, match="FROZEN_CALIBRATION_CONFIGURATION_CHANGED"):
        freeze(path, {"model": "different"})


def test_configuration_uses_existing_model_and_explicit_budget():
    pc = ProviderConfig(provider="openai", model="configured-model")
    config = configuration(pc, "Brief", "WORKBENCH", "synthetic-commit")
    assert config.model == pc.model and config.task_version == "benchmark-v2"
    assert dict(config.parameters)["max_calls"] == pc.max_calls
    assert config.budget.max_tokens == pc.max_run_tokens
    assert config.budget.max_cost_usd == 5
    RunConfiguration.model_validate(config.model_dump())


@pytest.mark.parametrize("route", ("EXPLAIN", "ESTABLISH", "TEST"))
@pytest.mark.parametrize("component", ("Brief", "Study", "Usefulness", "Literature"))
@pytest.mark.parametrize("mode", ("WORKBENCH", "BASELINE"))
def test_mock_provider_extended_scope_and_admin_exclusion(
    tmp_path, manifest, monkeypatch, route, component, mode
):
    from test_provider import adapter

    case = next(c for c in synthetic()[1] if c.project.route == route)
    model, _, requests = adapter(monkeypatch)
    evaluator = BlindEvaluator(case.variant.packet, model, manifest, tmp_path / "blind")
    try:
        output, _ = evaluator.run(mode, component, extended=True)
        task = evaluator.task(component, extended=True)
        assert {r["dimension"] for r in output["assessment"]["ratings"]} == set(task.dimensions)
        assert {r["item"] for r in output["assessment"]["route_assessment"]} == set(
            task.route_items
        )
        assert len(requests) == (1 if mode == "BASELINE" else 2)
        assert all(
            not {"tools", "files", "vector_store_ids"}.intersection(body) for body in requests
        )
        for body in requests:
            assert body["store"] is False and body["background"] is False
            assert not any(
                key in body["input"]
                for key in (
                    "private_paper_id",
                    "interest_proximity",
                    "method_families",
                    "execution_scope",
                )
            )
    finally:
        evaluator.close()
        model.close()


def test_stage_variants_are_nested_in_one_paper(tmp_path, manifest):
    from test_benchmarks import configuration as fake_configuration
    from test_benchmarks import runner

    r, _, cases = runner(tmp_path, manifest)
    first = r.execute(cases[0], fake_configuration())
    second = first.model_copy(
        update={"benchmark_id": "other-stage-package", "variant_id": "other-stage-case"}
    )
    sidecar = {
        "cases": [
            {
                "case_id": run.variant_id,
                "private_paper_id": "same-paper",
                "route": "EXPLAIN",
                "stage": stage,
                "execution_scope": "FULL_WORKBENCH",
                "target_components": ["Study"],
            }
            for run, stage in ((first, "COMPLETED STUDY"), (second, "EARLY IDEA"))
        ],
        "papers": [
            {
                "private_paper_id": "same-paper",
                "journal": "Synthetic journal",
                "interest_proximity": "CLOSE",
                "primary_substantive_area": "Synthetic area",
                "method_families": ["synthetic-method"],
            }
        ],
    }
    report = summarize((first, second), sidecar)
    assert report["overall"]["paper_count"] == 1
    assert report["overall"]["case_count"] == 2
    assert len(report["strata"]) >= 8
