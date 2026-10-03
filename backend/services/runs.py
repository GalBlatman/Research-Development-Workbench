import os
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from uuid import uuid4

from domain.application import RunHandle
from model_adapters.runtime import ProviderFailure
from services.workbench import Workbench


class RunManager:
    """One bounded local worker; durable safe receipts, no paid replay on restart."""

    def __init__(self, root: Path, factory: Callable[[], Workbench]):
        self.root, self.factory = root, factory
        root.mkdir(parents=True, exist_ok=True)
        self.lock = Lock()
        self.busy = False
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="rdw-evaluation")
        for path in root.glob("*.json"):
            run = RunHandle.model_validate_json(path.read_text(encoding="utf-8"))
            if run.state in ("queued", "running"):
                self.write(
                    run.model_copy(
                        update={"state": "failed", "error_code": "INTERRUPTED_NO_AUTOMATIC_REPLAY"}
                    )
                )

    def write(self, run: RunHandle) -> None:
        with self.lock:
            target = self.root / (run.run_id + ".json")
            temporary = target.with_suffix(".tmp")
            temporary.write_text(run.model_dump_json() + "\n", encoding="utf-8", newline="\n")
            os.replace(temporary, target)

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

    def submit(self, project_id: str, revision: int, dimensions: tuple[int, ...] = ()) -> RunHandle:
        with self.lock:
            if self.busy:
                raise ValueError("Another bounded evaluation is running; retry after it completes")
            self.busy = True
        run = RunHandle(
            run_id=uuid4().hex, project_id=project_id, expected_revision=revision, state="queued"
        )
        try:
            self.write(run)
            self.executor.submit(self.execute, run, dimensions)
        except BaseException:
            with self.lock:
                self.busy = False
            raise
        return run

    def execute(self, run: RunHandle, dimensions: tuple[int, ...]) -> None:
        service = None
        try:
            self.write(run.model_copy(update={"state": "running"}))
            service = self.factory()
            review = service.run(run.project_id, run.expected_revision, dimensions)
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
                update={"state": "failed", "error_code": exc.code, "provider_run": exc.metadata}
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
            self.write(run)
            with self.lock:
                self.busy = False

    def close(self) -> None:
        self.executor.shutdown(wait=True)
