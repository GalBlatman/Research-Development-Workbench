"""Administrator-only immutable artifacts and exclusive run reservations."""

import json
from pathlib import Path
from typing import TypeVar

from benchmarks.variants import content_hash, validate_import
from domain.benchmark import (
    BenchmarkProject,
    BenchmarkRun,
    BenchmarkVariant,
    FrozenSplit,
    RunConfiguration,
)
from domain.models import Frozen

T = TypeVar("T", bound=Frozen)


class AdminStore:
    def __init__(self, root: Path):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)

    def _path(self, category: str, identity: str) -> Path:
        folder = self.root / category
        folder.mkdir(exist_ok=True)
        return folder / (content_hash(identity) + ".json")

    def write(self, category: str, identity: str, value: Frozen) -> None:
        with self._path(category, identity).open("x", encoding="utf-8", newline="\n") as f:
            f.write(value.model_dump_json(indent=2) + "\n")

    def read(self, category: str, identity: str, contract: type[T]) -> T:
        return contract.model_validate_json(
            self._path(category, identity).read_text(encoding="utf-8")
        )

    def freeze(self, manifest: FrozenSplit) -> None:
        self.write("splits", manifest.version, manifest)

    def import_project(self, project: BenchmarkProject, manifest: FrozenSplit) -> None:
        validate_import(project, manifest)
        self.write("projects", project.benchmark_id, project)

    def save_variant(
        self, variant: BenchmarkVariant, project: BenchmarkProject, manifest: FrozenSplit
    ) -> None:
        validate_import(project, manifest)
        if variant.benchmark_id != project.benchmark_id or variant.split != project.split:
            raise ValueError("Sibling cross-split variant rejected")
        self.write("variants", variant.variant_id, variant)

    def cache_key(
        self, variant: BenchmarkVariant, manifest: FrozenSplit, configuration: RunConfiguration
    ) -> str:
        return content_hash(
            (content_hash(variant), content_hash(manifest), configuration.model_dump(mode="json"))
        )

    def claim(self, key: str, run_id: str, rerun: bool = False) -> bool:
        # An interrupted/uncertain reservation is never silently retried.
        identity = key + (":" + run_id if rerun else "")
        try:
            with self._path("claims", identity).open("x", encoding="utf-8") as f:
                json.dump({"run_id": run_id, "state": "RESERVED"}, f)
        except FileExistsError:
            return False
        return True

    def save_run(self, run: BenchmarkRun) -> None:
        self.write("runs", run.run_id, run)

    def reserve_batch_slot(self, batch_key: str, limit: int) -> bool:
        # Exclusive immutable slots bound concurrent controllers and resumed invocations.
        for index in range(limit):
            try:
                with self._path("batch_slots", batch_key + ":" + str(index)).open(
                    "x", encoding="utf-8"
                ) as f:
                    json.dump({"batch_key": batch_key, "slot": index}, f)
                return True
            except FileExistsError:
                continue
        return False
