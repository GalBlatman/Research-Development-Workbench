import json
import sys
from pathlib import Path

from pydantic import BaseModel

from api.app import create_app
from domain.models import Project, ReviewSummary
from domain.results import PolicyResult
from domain.sources import SourceAnchor, SourceRecord

ROOT = Path(__file__).resolve().parents[2]


def schema() -> str:
    document = create_app().openapi()
    models: tuple[type[BaseModel], ...] = (
        Project,
        ReviewSummary,
        SourceRecord,
        SourceAnchor,
        PolicyResult,
    )
    components = document.setdefault("components", {}).setdefault("schemas", {})
    for model in models:
        value = model.model_json_schema(ref_template="#/components/schemas/{model}")
        definitions = value.pop("$defs", {})
        components.update(definitions)
        components[model.__name__] = value
    return json.dumps(document, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    target = ROOT / "frontend/generated/openapi.json"
    value = schema()
    if "--check" in sys.argv:
        if target.read_text(encoding="utf-8") != value:
            raise SystemExit("Generated API schema drift; run python -m api.contracts")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(value, encoding="utf-8", newline="\n")
