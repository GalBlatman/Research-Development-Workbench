import hashlib
import json
import logging
import os
import tempfile
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import RLock
from uuid import uuid4

from domain.application import RunHandle
from domain.models import ProviderRun, Scope
from domain.research import DevelopRequest
from model_adapters.runtime import ProviderFailure, timestamp
from persistence.repository import Conflict
from services.research import ResearchService
from services.workbench import Workbench


def write_provider_receipt(root: Path, receipt: ProviderRun) -> None:
    """Publish a complete immutable ledger receipt; never leave partial JSON."""
    if len(receipt.run_id) != 32 or any(c not in "0123456789abcdef" for c in receipt.run_id):
        raise ValueError("INVALID_SERVER_RUN_ID")
    root.mkdir(parents=True, exist_ok=True)
    target = root / (receipt.run_id + ".json")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=root,
            prefix=".receipt-",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(receipt.model_dump_json() + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, target)
        except FileExistsError:
            if ProviderRun.model_validate_json(target.read_text(encoding="utf-8")) != receipt:
                raise ValueError("Provider receipt history is immutable") from None
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


class RunManager:
    """One bounded local worker; durable safe receipts, no paid replay on restart."""

    def __init__(self, root: Path, factory: Callable[[], Workbench]):
        self.root, self.factory = root, factory
        root.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()
        self.busy = False
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="rdw-evaluation")
        for path in root.glob("*.json"):
            run = RunHandle.model_validate_json(path.read_text(encoding="utf-8"))
            if run.state in ("queued", "running"):
                recovered = self.reconcile(run) if run.request_key else None
                self.write(
                    recovered
                    or run.model_copy(
                        update={
                            "state": "failed",
                            "error_code": "INTERRUPTED_NO_AUTOMATIC_REPLAY",
                            "failure_kind": "interrupted_uncertain",
                            "finished_at": timestamp(),
                        }
                    )
                )

    def reconcile(self, run: RunHandle) -> RunHandle | None:
        service = self.factory()
        try:
            bundle = service.bundle(run.project_id)
            for stored in bundle.snapshots:
                if stored.operation_id == run.run_id:
                    return run.model_copy(
                        update={
                            "state": "succeeded",
                            "snapshot_id": stored.snapshot.snapshot_id,
                            "provider_run": stored.provider_run,
                            "finished_at": timestamp(),
                        }
                    )
            for project in bundle.revisions:
                for obj in project.objects:
                    if obj.operation_id == run.run_id:
                        return run.model_copy(
                            update={
                                "state": "succeeded",
                                "result_revision": obj.revision,
                                "provider_run": obj.provider_run,
                                "finished_at": timestamp(),
                            }
                        )
            return None
        finally:
            service.repository.db.close()
            close = getattr(service.adapter, "close", None)
            if close:
                close()

    def write(self, run: RunHandle) -> None:
        with self.lock:
            target = self.root / (run.run_id + ".json")
            if target.exists():
                previous = RunHandle.model_validate_json(target.read_text(encoding="utf-8"))
                if previous.state in ("succeeded", "failed") and previous != run:
                    raise ValueError("Terminal run history is immutable")
            temporary = target.with_suffix(".tmp")
            with temporary.open("w", encoding="utf-8", newline="\n") as stream:
                stream.write(run.model_dump_json() + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
            logging.getLogger("rdw.operations").info(
                "run_transition run=%s project=%s revision=%s state=%s error=%s calls=%s duration=%s provider=%s model=%s tasks=%s input_tokens=%s output_tokens=%s",
                run.run_id,
                hashlib.sha256(run.project_id.encode()).hexdigest()[:12],
                run.expected_revision,
                run.state,
                run.error_code or "none",
                len(run.provider_run.calls) if run.provider_run else 0,
                run.duration_seconds,
                "openai" if run.provider_run else "fake-or-unavailable",
                "gpt-6-sol"
                if run.provider_run
                and all(c.configured_model == "gpt-6-sol" for c in run.provider_run.calls)
                else "configured-alternate-or-fake",
                ",".join(
                    sorted(
                        {
                            c.task
                            for c in run.provider_run.calls
                            if c.task
                            in {
                                "interpretation",
                                "evaluation",
                                "checking",
                                "workspace",
                                "workspace-check",
                                "baseline",
                            }
                        }
                    )
                )
                if run.provider_run
                else "none",
                sum(c.input_tokens or 0 for c in run.provider_run.calls) if run.provider_run else 0,
                sum(c.output_tokens or 0 for c in run.provider_run.calls)
                if run.provider_run
                else 0,
            )

    def get(self, project_id: str, run_id: str) -> RunHandle:
        if len(run_id) != 32 or any(c not in "0123456789abcdef" for c in run_id):
            raise ValueError("Run unavailable")
        with self.lock:
            try:
                run = RunHandle.model_validate_json(
                    (self.root / (run_id + ".json")).read_text(encoding="utf-8")
                )
            except FileNotFoundError:
                raise ValueError("Run unavailable") from None
        if run.project_id != project_id:
            raise ValueError("Run unavailable")
        return run

    def submit(
        self,
        project_id: str,
        revision: int,
        dimensions: tuple[int, ...] = (),
        target_workspace: str | None = None,
        evaluation_scope: Scope = Scope.INITIAL_SCREEN,
        development: DevelopRequest | None = None,
        retry_failed: bool = False,
    ) -> RunHandle:
        request_key = hashlib.sha256(
            json.dumps(
                [
                    project_id,
                    revision,
                    dimensions,
                    target_workspace,
                    evaluation_scope,
                    development.model_dump(mode="json", exclude={"retry_failed"})
                    if development
                    else None,
                ],
                sort_keys=True,
            ).encode()
        ).hexdigest()
        with self.lock:
            matches = [
                RunHandle.model_validate_json(p.read_text(encoding="utf-8"))
                for p in self.root.glob("*.json")
            ]
            matching = next(
                (
                    r
                    for r in reversed(sorted(matches, key=lambda r: r.started_at or ""))
                    if r.request_key == request_key
                ),
                None,
            )
            if matching and (matching.state != "failed" or not retry_failed):
                return matching
            if self.busy:
                raise Conflict("Another bounded evaluation is running; retry after it completes")
            self.busy = True
            run = RunHandle(
                run_id=uuid4().hex,
                project_id=project_id,
                expected_revision=revision,
                state="queued",
                request_key=request_key,
                started_at=timestamp(),
            )
            try:
                self.write(run)
                self.executor.submit(
                    self.execute, run, dimensions, target_workspace, evaluation_scope, development
                )
            except BaseException:
                self.busy = False
                raise
        return run

    def execute(
        self,
        run: RunHandle,
        dimensions: tuple[int, ...],
        target_workspace: str | None = None,
        evaluation_scope: Scope = Scope.INITIAL_SCREEN,
        development: DevelopRequest | None = None,
    ) -> None:
        service = None
        started = time.monotonic()
        try:
            self.write(run.model_copy(update={"state": "running"}))
            service = self.factory()
            if development is not None:
                view = ResearchService(service).develop(
                    run.project_id, development, operation_id=run.run_id
                )
                latest = view["project"]["objects"][-1]
                run = RunHandle.model_validate(
                    {
                        **run.model_dump(),
                        "state": "succeeded",
                        "result_revision": view["project"]["revision"],
                        "provider_run": latest.get("provider_run"),
                    }
                )
            else:
                review = service.run(
                    run.project_id,
                    run.expected_revision,
                    dimensions,
                    target_workspace,
                    evaluation_scope,
                    operation_id=run.run_id,
                )
                run = RunHandle.model_validate(
                    {
                        **run.model_dump(),
                        "state": "succeeded",
                        "snapshot_id": review["snapshot"]["snapshot_id"],
                        "provider_run": review.get("provider_run"),
                    }
                )
        except ProviderFailure as exc:
            run = run.model_copy(
                update={
                    "state": "failed",
                    "error_code": exc.code,
                    "provider_run": exc.metadata,
                    "failure_kind": "timeout_uncertain"
                    if exc.code == "TIMEOUT_UNCERTAIN"
                    else "transport_uncertain"
                    if exc.code == "TRANSPORT_ERROR_UNCERTAIN"
                    else "budget_exhausted"
                    if exc.code == "BUDGET_EXHAUSTED"
                    else "contract"
                    if exc.code in ("INCOMPLETE_CHECK", "MALFORMED_OUTPUT", "INCOMPLETE_OUTPUT")
                    else "provider",
                }
            )
        except Conflict as exc:
            run = run.model_copy(
                update={
                    "state": "failed",
                    "error_code": "REVISION_CONFLICT_NO_PUBLICATION",
                    "failure_kind": "conflict",
                    "provider_run": exc.provider_metadata,
                }
            )
        except Exception:
            # No provider manuscript/response/credential exception string is persisted or exposed.
            run = run.model_copy(
                update={"state": "failed", "error_code": "RUN_FAILED_NO_PUBLICATION"}
            )
        finally:
            if service is not None:
                service.repository.db.close()
                close = getattr(service.adapter, "close", None)
                if close:
                    close()
            self.write(
                run.model_copy(
                    update={
                        "finished_at": timestamp(),
                        "duration_seconds": time.monotonic() - started,
                    }
                )
            )
            with self.lock:
                self.busy = False

    def close(self) -> None:
        self.executor.shutdown(wait=True)
