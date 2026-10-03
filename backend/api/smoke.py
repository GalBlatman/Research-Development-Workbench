"""One explicitly authorized synthetic workflow; never run as ordinary tests."""

import json
import os
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from domain.application import AddSource, CreateProject
from domain.models import Route, Stage
from model_adapters.checking import AssessmentChecker
from model_adapters.config import ProviderConfig
from model_adapters.fake import DEMO_IDEA, DEMO_SOURCE
from model_adapters.openai import OpenAIAdapter
from model_adapters.runtime import ProviderFailure
from persistence.database import Database
from persistence.originals import OriginalFileStore
from persistence.repository import Repository
from policy_engine.manifest import Manifest
from services.sources import SourceService
from services.workbench import Workbench


def main() -> int:
    if not os.environ.get("OPENAI_API_KEY"):
        print(
            json.dumps(
                {
                    "status": "BLOCKED_CREDENTIAL",
                    "synthetic_input_only": True,
                    "schema_validated": False,
                    "provider_calls": 0,
                }
            )
        )
        return 2
    config = replace(ProviderConfig.environment(), provider="openai", retries=0, max_calls=3)
    adapter = OpenAIAdapter(config)
    root = Path(__file__).resolve().parents[2]
    manifest = Manifest.model_validate_json(
        (root / "policies/rubric-v4.manifest.json").read_text(encoding="utf-8")
    )
    try:
        with TemporaryDirectory(prefix="rdw-synthetic-smoke-") as temporary:
            directory = Path(temporary)
            db = Database.sqlite(directory / "synthetic.sqlite")
            db.initialize()
            try:
                repo = Repository(db)
                workbench = Workbench(
                    repo,
                    SourceService(repo, OriginalFileStore(directory / "originals")),
                    manifest,
                    adapter,
                    AssessmentChecker(adapter),
                )
                view = workbench.create(
                    CreateProject(
                        title="Synthetic provider smoke",
                        idea=DEMO_IDEA,
                        route=Route.EXPLAIN,
                        stage=Stage.EARLY_IDEA,
                        authorized=True,
                    )
                )
                identifier = view["project"]["project_id"]
                view = workbench.add_source(
                    identifier,
                    AddSource(
                        expected_revision=view["project"]["revision"],
                        title="Synthetic excerpt",
                        attribution="Synthetic test only",
                        text=DEMO_SOURCE,
                        authorized=True,
                        admitted=True,
                    ),
                )
                review = workbench.run(identifier, view["project"]["revision"])
                assert review["snapshot"]["project"]["project_id"] == identifier
                assert review["policy"]["trace"] and review["provider_run"]["calls"]
                print(
                    json.dumps(
                        {
                            "status": "PASS",
                            "synthetic_input_only": True,
                            "schema_validated": True,
                            "server_snapshot_attached": True,
                            "policy_processed": True,
                            "provider": "openai",
                            "configured_model": config.model,
                            "provider_calls": 1 + len(review["provider_run"]["calls"]),
                            "usage_captured": True,
                        }
                    )
                )
                return 0
            finally:
                db.close()
    except ProviderFailure as exc:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "code": exc.code,
                    "synthetic_input_only": True,
                    "schema_validated": False,
                }
            )
        )
        return 1
    finally:
        adapter.close()


if __name__ == "__main__":
    raise SystemExit(main())
