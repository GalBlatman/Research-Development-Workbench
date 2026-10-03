from typing import Any

from pydantic import BaseModel


def strict_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Transport-only schema normalization; local Pydantic validation remains authoritative."""

    def visit(value: Any) -> Any:
        if isinstance(value, list):
            return [visit(item) for item in value]
        if not isinstance(value, dict):
            return value
        node = {
            key: visit(item)
            for key, item in value.items()
            if key not in ("default", "title", "discriminator")
        }
        if "const" in node:
            node["enum"] = [node.pop("const")]
        if "prefixItems" in node:
            items = node.pop("prefixItems")
            if any(item != items[0] for item in items):
                raise ValueError("Unsupported heterogeneous tuple schema")
            node["items"] = items[0]
        if node.get("type") == "object":
            node["additionalProperties"] = False
            node["required"] = list(node.get("properties", {}))
        return node

    return dict(visit(model.model_json_schema()))
