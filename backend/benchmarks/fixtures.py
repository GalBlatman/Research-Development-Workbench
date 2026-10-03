"""Minimal original synthetic fixtures, not the later scientific corpus."""

from benchmarks.runner import Case
from benchmarks.variants import construct, freeze
from domain.benchmark import (
    BenchmarkExpectation,
    BenchmarkProject,
    Block,
    Feature,
    GoldFeature,
    Mutation,
    SourcePackage,
    Split,
    Transformation,
)
from domain.models import Route, Stage


def synthetic() -> tuple[tuple[BenchmarkProject, ...], tuple[Case, ...]]:
    projects = tuple(
        BenchmarkProject(
            benchmark_id="synthetic-" + route.value,
            split=split,
            route=route,
            stage=Stage.PROPOSAL,
            neutral_identifier="Synthetic packet " + str(index),
            version="synthetic-v1",
            source_package=SourcePackage(
                package_id="fixture-" + str(index),
                version="v1",
                identifying_metadata=("Fictional Journal Alpha", "doi:synthetic-alpha"),
                blocks=(
                    Block(
                        block_id="question",
                        text="Synthetic project: does a fictional scheduling change alter handoffs?",
                        features=(Feature.QUESTION,),
                    ),
                    Block(
                        block_id="measure",
                        text="A planned direct count of handoffs, not completed evidence.",
                        features=(Feature.MEASURES,),
                    ),
                    Block(
                        block_id="rival",
                        text="A planned rival predicts that shared workload explains the pattern.",
                        features=(Feature.RIVALS,),
                    ),
                    Block(
                        block_id="metadata",
                        text="Fictional Journal Alpha doi:synthetic-alpha",
                        metadata_only=True,
                    ),
                ),
            ),
            gold=(
                GoldFeature(
                    feature=Feature.MEASURES,
                    content="direct count of handoffs",
                    source_anchors=("measure",),
                    confidence="high",
                    status="specified_but_untested",
                ),
            ),
        )
        for index, (route, split) in enumerate(zip(Route, Split, strict=True))
    )
    splits = freeze(projects, "synthetic-splits-v1")
    cases = []
    for p in projects:
        for name, mutation in (
            ("intact", Mutation(transformation=Transformation.INTACT)),
            ("hidden", Mutation(transformation=Transformation.HIDE, targets=(Feature.MEASURES,))),
            (
                "pair",
                Mutation(
                    transformation=Transformation.MULTIPLE,
                    targets=(Feature.MEASURES, Feature.RIVALS),
                ),
            ),
            ("metadata", Mutation(transformation=Transformation.METADATA)),
        ):
            expectation = (
                (
                    BenchmarkExpectation(
                        feature=Feature.MEASURES,
                        behavior="refuse_infer",
                        judgment="rating:9",
                        acceptable_states=("PENDING", "UNRESOLVED"),
                        forbidden_states=("ASSESSED",),
                    ),
                )
                if name in ("hidden", "pair")
                else ()
            )
            cases.append(
                Case(p, construct(p, mutation, p.benchmark_id + "-" + name, splits), expectation)
            )
        degraded = construct(
            p,
            Mutation(
                transformation=Transformation.DEGRADE,
                targets=(Feature.MEASURES,),
                replacements=(
                    Block(
                        block_id="proxy",
                        text="A planned adjacent proxy counts meeting attendance instead of handoffs.",
                        features=(Feature.MEASURES,),
                    ),
                ),
            ),
            p.benchmark_id + "-degraded",
            splits,
        )
        cases.append(Case(p, degraded))
        restored = construct(
            p,
            Mutation(
                transformation=Transformation.RESTORE,
                targets=(Feature.MEASURES,),
                parent_variant=degraded.variant_id,
            ),
            p.benchmark_id + "-restored",
            splits,
            degraded,
        )
        cases.append(Case(p, restored))
        for n in range(3):
            cases.append(
                Case(
                    p,
                    construct(
                        p,
                        Mutation(
                            transformation=Transformation.REVEAL,
                            targets=(Feature.MEASURES, Feature.RIVALS),
                            reveal_order=(Feature.MEASURES, Feature.RIVALS),
                            reveal_count=n,
                        ),
                        p.benchmark_id + "-reveal-" + str(n),
                        splits,
                    ),
                )
            )
    return projects, tuple(cases)
