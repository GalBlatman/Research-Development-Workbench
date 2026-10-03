import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal, cast

import psycopg
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.middleware.trustedhost import TrustedHostMiddleware

from domain.application import (
    AddSource,
    CreateProject,
    EditProject,
    EvaluateRequest,
    RevisionRequest,
    RunHandle,
    TargetedEvaluation,
)
from domain.models import ProviderRun
from domain.presentation import HistoryView, ProjectView, ReviewView
from domain.research import (
    DIMENSIONS,
    DecisionRequest,
    DevelopRequest,
    RecordRequest,
    SettingsRequest,
    WorkspaceCatalog,
    WorkspaceCheckRequest,
)
from model_adapters.checking import AssessmentChecker
from model_adapters.fake import DEMO_IDEA, DEMO_SOURCE
from model_adapters.openai import OpenAIAdapter
from model_adapters.runtime import ProviderFailure
from persistence.originals import OriginalFileStore
from persistence.repository import AccessDenied, Conflict, Repository
from policy_engine.manifest import Manifest
from services.configuration import LocalConfiguration
from services.research import ResearchService
from services.runs import RunManager, write_provider_receipt
from services.sources import SourceService
from services.workbench import InvalidModelOutput, Workbench

ROOT = Path(__file__).resolve().parents[2]


def create_app(service: Workbench | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if service is not None:
            app.state.runs = None
            app.state.workbench = service
            yield
            return
        local = LocalConfiguration.environment()
        runtime = local.runtime
        manifest = Manifest.model_validate_json(
            (ROOT / "policies/rubric-v5.manifest.json").read_text(encoding="utf-8")
        )
        config = local.provider
        receipts = runtime / "provider-receipts"

        def record_receipt(receipt: ProviderRun) -> None:
            write_provider_receipt(receipts, receipt)

        def make_service() -> Workbench:
            database = local.database()
            database.initialize()
            repo = Repository(database)
            adapter = (
                OpenAIAdapter(config, receipt_sink=record_receipt)
                if config.provider == "openai"
                else None
            )
            verifier = AssessmentChecker(adapter) if adapter is not None else None
            return Workbench(
                repo,
                SourceService(repo, OriginalFileStore(runtime / "originals")),
                manifest,
                adapter,
                verifier,
            )

        app.state.workbench = make_service()
        app.state.runs = (
            RunManager(runtime / "runs", make_service) if config.provider == "openai" else None
        )
        try:
            yield
        finally:
            if app.state.runs:
                app.state.runs.close()
            app.state.workbench.repository.db.close()
            close = getattr(app.state.workbench.adapter, "close", None)
            if close:
                close()

    app = FastAPI(
        title="Research Development Workbench — bounded local workflow",
        lifespan=lifespan,
        separate_input_output_schemas=False,
    )
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"]
    )

    @app.middleware("http")
    async def local_boundary(request: Request, call_next: Any) -> Response:
        origin = request.headers.get("origin")
        if origin and origin not in {
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "http://127.0.0.1:8000",
            "http://localhost:8000",
        }:
            return JSONResponse(
                {"detail": "Only the local app origin is permitted"}, status_code=403
            )
        return cast(Response, await call_next(request))

    @app.exception_handler(sqlite3.OperationalError)
    @app.exception_handler(psycopg.Error)
    async def database_error(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            {
                "detail": "Database busy or unavailable; reload before retrying",
                "code": "DATABASE_OPERATION_FAILED",
            },
            status_code=503,
        )

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            {
                "detail": "Request fields are missing or invalid",
                "fields": [list(error["loc"]) for error in exc.errors()],
            },
            status_code=422,
        )

    @app.exception_handler(ProviderFailure)
    async def provider_error(request: Request, exc: ProviderFailure) -> JSONResponse:
        return JSONResponse(
            {
                "detail": exc.code,
                "code": exc.code,
                "provider_run": exc.metadata.model_dump(mode="json") if exc.metadata else None,
            },
            status_code=503,
        )

    @app.exception_handler(InvalidModelOutput)
    async def model_error(request: Request, exc: InvalidModelOutput) -> JSONResponse:
        return JSONResponse(
            {
                "detail": "Model output was incomplete or invalid; no review published",
                "code": "INVALID_MODEL_OUTPUT",
            },
            status_code=502,
        )

    @app.exception_handler(Conflict)
    async def conflict(request: Request, exc: Conflict) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.exception_handler(AccessDenied)
    async def denied(request: Request, exc: AccessDenied) -> JSONResponse:
        return JSONResponse(
            {"detail": "Record unavailable in this local workspace"}, status_code=404
        )

    @app.exception_handler(ValueError)
    async def invalid(request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse({"detail": str(exc).split("\n")[0]}, status_code=422)

    @app.get("/api/health")
    async def health(request: Request) -> dict[str, Any]:
        adapter = request.app.state.workbench.adapter
        config = getattr(adapter, "provider_config", None)
        return {
            "status": "ok",
            "model": adapter.configuration,
            "policy_version": request.app.state.workbench.manifest.version,
            "policy_manifest_sha256": request.app.state.workbench.manifest.sha256,
            "prompt_version": getattr(adapter, "prompt_configuration", None),
            "budget": {
                "max_calls": config.max_calls,
                "max_run_tokens": config.max_run_tokens,
                "output_limit": config.max_output_tokens,
                "timeout_seconds": config.timeout,
            }
            if config
            else None,
        }

    @app.get("/api/demo")
    async def demo() -> dict[str, str]:
        return {"idea": DEMO_IDEA, "source": DEMO_SOURCE}

    @app.post("/api/projects", status_code=201, response_model=ProjectView)
    async def create(body: CreateProject, request: Request) -> dict[str, Any]:
        return request.app.state.workbench.create(body)  # type: ignore[no-any-return]

    @app.get("/api/projects/{project_id}", response_model=ProjectView)
    async def project(project_id: str, request: Request) -> dict[str, Any]:
        return request.app.state.workbench.view(project_id)  # type: ignore[no-any-return]

    @app.patch("/api/projects/{project_id}", response_model=ProjectView)
    async def edit(project_id: str, body: EditProject, request: Request) -> dict[str, Any]:
        return request.app.state.workbench.edit(project_id, body)  # type: ignore[no-any-return]

    @app.post("/api/projects/{project_id}/sources", status_code=201, response_model=ProjectView)
    async def source(project_id: str, body: AddSource, request: Request) -> dict[str, Any]:
        return request.app.state.workbench.add_source(project_id, body)  # type: ignore[no-any-return]

    @app.post("/api/projects/{project_id}/proposals/{object_id}/accept", response_model=ProjectView)
    async def accept(
        project_id: str, object_id: str, body: RevisionRequest, request: Request
    ) -> dict[str, Any]:
        return request.app.state.workbench.accept(project_id, object_id, body.expected_revision)  # type: ignore[no-any-return]

    @app.post(
        "/api/projects/{project_id}/evaluations",
        status_code=201,
        response_model=ReviewView | RunHandle,
        response_model_exclude_unset=True,
    )
    async def evaluate(project_id: str, body: EvaluateRequest, request: Request) -> Any:
        workbench = request.app.state.workbench
        manager = request.app.state.runs
        if manager is not None:
            workbench._current(project_id, body.expected_revision)
            return JSONResponse(
                manager.submit(
                    project_id,
                    body.expected_revision,
                    evaluation_scope=body.scope,
                    retry_failed=body.retry_failed,
                ).model_dump(mode="json"),
                status_code=202,
            )
        return workbench.run(project_id, body.expected_revision, evaluation_scope=body.scope)

    @app.post(
        "/api/projects/{project_id}/evaluations/targeted",
        response_model=ReviewView | RunHandle,
        response_model_exclude_unset=True,
    )
    async def targeted(project_id: str, body: TargetedEvaluation, request: Request) -> Any:
        workbench = request.app.state.workbench
        manager = request.app.state.runs
        workbench._current(project_id, body.expected_revision)
        if manager is not None:
            return JSONResponse(
                manager.submit(
                    project_id,
                    body.expected_revision,
                    body.dimensions,
                    retry_failed=body.retry_failed,
                ).model_dump(mode="json"),
                status_code=202,
            )
        return workbench.run(project_id, body.expected_revision, body.dimensions)

    @app.get("/api/projects/{project_id}/runs/{run_id}", response_model=RunHandle)
    async def run_state(project_id: str, run_id: str, request: Request) -> RunHandle:
        request.app.state.workbench.repository.authorize(
            request.app.state.workbench.scope(project_id)
        )
        if request.app.state.runs is None:
            raise ValueError("No provider run in the offline fake workflow")
        return cast(RunHandle, request.app.state.runs.get(project_id, run_id))

    @app.get(
        "/api/projects/{project_id}/reviews/{snapshot_id}",
        response_model=ReviewView,
        response_model_exclude_unset=True,
    )
    async def review(project_id: str, snapshot_id: str, request: Request) -> dict[str, Any]:
        return request.app.state.workbench.review(project_id, snapshot_id)  # type: ignore[no-any-return]

    @app.get("/api/projects/{project_id}/sources/{document_id}/{version}/{anchor_id}")
    async def read_source(
        project_id: str, document_id: str, version: int, anchor_id: str, request: Request
    ) -> dict[str, Any]:
        return request.app.state.workbench.source(project_id, document_id, version, anchor_id)  # type: ignore[no-any-return]

    @app.get("/api/projects/{project_id}/workspaces", response_model=WorkspaceCatalog)
    async def workspaces(project_id: str, request: Request) -> dict[str, Any]:
        return ResearchService(request.app.state.workbench).catalog(project_id)

    @app.post("/api/projects/{project_id}/records", response_model=ProjectView)
    async def save_record(project_id: str, body: RecordRequest, request: Request) -> dict[str, Any]:
        return ResearchService(request.app.state.workbench).save(project_id, body)

    @app.post(
        "/api/projects/{project_id}/proposals/{object_id}/decision", response_model=ProjectView
    )
    async def decide(
        project_id: str, object_id: str, body: DecisionRequest, request: Request
    ) -> dict[str, Any]:
        return ResearchService(request.app.state.workbench).decide(project_id, object_id, body)

    @app.patch("/api/projects/{project_id}/settings", response_model=ProjectView)
    async def settings(project_id: str, body: SettingsRequest, request: Request) -> dict[str, Any]:
        return ResearchService(request.app.state.workbench).settings(project_id, body)

    @app.post(
        "/api/projects/{project_id}/workspace-proposals", response_model=ProjectView | RunHandle
    )
    async def propose(project_id: str, body: DevelopRequest, request: Request) -> Any:
        workbench = request.app.state.workbench
        workbench._current(project_id, body.expected_revision)
        manager = request.app.state.runs
        if manager is not None:
            return JSONResponse(
                manager.submit(
                    project_id,
                    body.expected_revision,
                    development=body,
                    retry_failed=body.retry_failed,
                ).model_dump(mode="json"),
                status_code=202,
            )
        return ResearchService(workbench).develop(project_id, body)

    @app.post(
        "/api/projects/{project_id}/workspace-checks",
        response_model=ReviewView | RunHandle,
        response_model_exclude_unset=True,
    )
    async def workspace_check(
        project_id: str, body: WorkspaceCheckRequest, request: Request
    ) -> Any:
        workbench = request.app.state.workbench
        workbench._current(project_id, body.expected_revision)
        manager = request.app.state.runs
        dimensions = DIMENSIONS[body.workspace]
        if manager is not None:
            return JSONResponse(
                manager.submit(
                    project_id,
                    body.expected_revision,
                    dimensions,
                    body.workspace,
                    retry_failed=body.retry_failed,
                ).model_dump(mode="json"),
                status_code=202,
            )
        return workbench.run(project_id, body.expected_revision, dimensions, body.workspace)

    @app.post(
        "/api/projects/{project_id}/sources/{document_id}/versions", response_model=ProjectView
    )
    async def append_source(
        project_id: str, document_id: str, body: AddSource, request: Request
    ) -> dict[str, Any]:
        if not body.text.strip():
            raise ValueError("Source text must contain text")
        return ResearchService(request.app.state.workbench).source_version(
            project_id, document_id, body
        )

    @app.get("/api/projects/{project_id}/history", response_model=HistoryView)
    async def history(project_id: str, request: Request) -> dict[str, Any]:
        return ResearchService(request.app.state.workbench).history(project_id)

    @app.get("/api/projects/{project_id}/history/{revision}/export")
    async def history_export(project_id: str, revision: int, request: Request) -> Response:
        return Response(
            ResearchService(request.app.state.workbench).historical_export(project_id, revision),
            media_type="application/json",
        )

    @app.get("/api/projects/{project_id}/exports/{format}")
    async def export(
        project_id: str, format: Literal["json", "markdown", "plan"], request: Request
    ) -> Response:
        output = request.app.state.workbench.export(project_id, format)
        return Response(
            output,
            media_type="application/json" if format == "json" else "text/markdown",
            headers={
                "Content-Disposition": f'attachment; filename="project.{"json" if format == "json" else "md"}"'
            },
        )

    return app


app = create_app()
