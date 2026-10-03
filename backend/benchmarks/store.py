"""Administrator-only immutable artifacts and exclusive run reservations."""

import json
import os
import tempfile
from pathlib import Path
from typing import Literal, TypeVar

from benchmarks.variants import content_hash, package_identity, validate_import
from domain.benchmark import (
    BenchmarkExpectation,
    BenchmarkProject,
    BenchmarkRun,
    BenchmarkVariant,
    FrozenExpectations,
    FrozenSplit,
    ReservationReport,
    RunConfiguration,
)
from domain.models import Frozen

T = TypeVar("T", bound=Frozen)


class AdminStore:
    def __init__(self, root: Path):
        self.root = root.resolve()
        root.mkdir(parents=True, exist_ok=True)

    def _path(self, category: str, identity: str) -> Path:
        if category not in {
            "projects",
            "variants",
            "runs",
            "splits",
            "claims",
            "batch_slots",
            "annotations",
            "expectations",
        }:
            raise ValueError("Unknown administrator artifact category")
        folder = self.root / category
        folder.mkdir(exist_ok=True)
        return folder / (content_hash(identity) + ".json")

    def write(self, category: str, identity: str, value: Frozen) -> None:
        target = self._path(category, identity)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                dir=target.parent,
                prefix=".stage-",
                suffix=".tmp",
                delete=False,
            ) as stream:
                temporary = Path(stream.name)
                stream.write(value.model_dump_json(indent=2) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            # Atomic publish without overwrite: supported local NTFS/ext4 runtime.
            os.link(temporary, target)
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)

    def read(self, category: str, identity: str, contract: type[T]) -> T:
        return contract.model_validate_json(
            self._path(category, identity).read_text(encoding="utf-8")
        )

    def freeze(self, manifest: FrozenSplit) -> None:
        # All historical assignments remain authoritative, including across versions.
        for path in (self.root / "splits").glob("*.json"):
            previous = FrozenSplit.model_validate_json(path.read_text(encoding="utf-8"))
            for identity, package_id, source_hash, split in manifest.package_assignments:
                for old_identity, old_package, old_hash, old_split in previous.package_assignments:
                    if source_hash == old_hash and identity != old_identity:
                        raise ValueError("Duplicate package relabeled under another project")
                    if (
                        identity == old_identity or package_id == old_package
                    ) and source_hash != old_hash:
                        raise ValueError("Permanent project/package content identity collision")
                    if (identity == old_identity or source_hash == old_hash) and split != old_split:
                        raise ValueError("Permanent package split cannot change")
            old = {a[0]: a[1] for a in previous.assignments}
            if any(
                identity in old and old[identity] != split
                for identity, split, _ in manifest.assignments
            ):
                raise ValueError("Permanent project split cannot change")
        self.write("splits", manifest.version, manifest)

    def import_project(self, project: BenchmarkProject, manifest: FrozenSplit) -> None:
        self.require_manifest(manifest)
        validate_import(project, manifest)
        identity = package_identity(project)
        for path in (self.root / "projects").glob("*.json"):
            previous = BenchmarkProject.model_validate_json(path.read_text(encoding="utf-8"))
            same_content = package_identity(previous) == identity
            same_id = previous.benchmark_id == project.benchmark_id
            same_package = previous.source_package.package_id == project.source_package.package_id
            if same_content and not same_id:
                raise ValueError("Duplicate package relabeled under another project")
            if (same_id or same_package) and not same_content:
                raise ValueError("Permanent project/package content identity collision")
            if same_id and previous.split != project.split:
                raise ValueError("Permanent project split cannot change")
        self.write("projects", project.benchmark_id + ":" + project.version, project)

    def save_variant(
        self, variant: BenchmarkVariant, project: BenchmarkProject, manifest: FrozenSplit
    ) -> None:
        self.require_manifest(manifest)
        validate_import(project, manifest)
        if variant.package_hash != content_hash(project) or variant.split_hash != content_hash(
            manifest
        ):
            raise ValueError("Variant frozen package binding mismatch")
        if variant.benchmark_id != project.benchmark_id or variant.split != project.split:
            raise ValueError("Sibling cross-split variant rejected")
        self.write("variants", variant.variant_id, variant)

    def require_manifest(self, manifest: FrozenSplit) -> None:
        if self.read("splits", manifest.version, FrozenSplit) != manifest:
            raise ValueError("Stored frozen manifest differs")

    def freeze_expectations(
        self, variant: BenchmarkVariant, expectations: tuple[BenchmarkExpectation, ...]
    ) -> None:
        self.write(
            "expectations",
            variant.variant_id,
            FrozenExpectations(
                variant_id=variant.variant_id,
                variant_hash=content_hash(variant),
                expectations=expectations,
            ),
        )

    def require_case(
        self,
        project: BenchmarkProject,
        variant: BenchmarkVariant,
        manifest: FrozenSplit,
        expectations: tuple[BenchmarkExpectation, ...],
    ) -> None:
        self.require_manifest(manifest)
        if (
            self.read("projects", project.benchmark_id + ":" + project.version, BenchmarkProject)
            != project
        ):
            raise ValueError("Stored project differs")
        if self.read("variants", variant.variant_id, BenchmarkVariant) != variant:
            raise ValueError("Stored variant differs")
        artifact = self.read("expectations", variant.variant_id, FrozenExpectations)
        if artifact.variant_hash != content_hash(variant) or artifact.expectations != expectations:
            raise ValueError("Frozen expectations differ")

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

    def reservation_report(self, key: str) -> ReservationReport:
        record = json.loads(self._path("claims", key).read_text(encoding="utf-8"))
        status: Literal["INTERRUPTED_UNCERTAIN", "SUCCEEDED", "FAILED", "INTERRUPTED"]
        try:
            run = self.read("runs", record["run_id"], BenchmarkRun)
            status = run.status
        except FileNotFoundError:
            status = "INTERRUPTED_UNCERTAIN"
        report = ReservationReport(reservation_key=key, run_id=record["run_id"], status=status)
        if status == "INTERRUPTED_UNCERTAIN":
            try:
                self.write("annotations", "reservation:" + key, report)
            except FileExistsError:
                if self.read("annotations", "reservation:" + key, ReservationReport) != report:
                    raise ValueError("Reservation recovery report differs")
        return report
