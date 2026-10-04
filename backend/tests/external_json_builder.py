"""Synthetic external builder: stdlib JSON/hash only; public docs/schema contract."""

import hashlib
import json
import sys
from pathlib import Path

schema = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert schema["properties"]["schema_version"]["const"] == "benchmark-package-v1"


def h(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def defaults(name, data):
    for key, item in schema["$defs"][name]["properties"].items():
        if "default" in item and key not in data:
            data[key] = item["default"]
    return data


block = defaults(
    "Block",
    {
        "block_id": "synthetic-question",
        "text": "Synthetic fictional handoff question.",
        "features": ["question"],
    },
)
source = defaults(
    "SourcePackage", {"package_id": "synthetic-external-source", "version": "v1", "blocks": [block]}
)
project = {
    "benchmark_id": "synthetic-external-paper",
    "split": "DEVELOPMENT",
    "route": "EXPLAIN",
    "stage": "EARLY IDEA",
    "neutral_identifier": "Synthetic packet",
    "source_package": source,
    "gold": [],
    "version": "v1",
    "paper_identity": "synthetic-opaque-identity",
}
manifest = {
    "version": "synthetic-external-splits-v1",
    "assignments": [[project["benchmark_id"], project["split"], h(project)]],
    "package_assignments": [
        [
            project["benchmark_id"],
            source["package_id"],
            h(project["paper_identity"]),
            project["split"],
        ]
    ],
}
packet_data = {
    "route": project["route"],
    "stage": project["stage"],
    "blocks": [{"role": block["role"], "text": block["text"]}],
}
variant = {
    "variant_id": "synthetic-external-intact",
    "benchmark_id": project["benchmark_id"],
    "split": project["split"],
    "version": project["version"],
    "mutation": defaults("Mutation", {"transformation": "INTACT_BLIND"}),
    "visibility": [["question", True]],
    "packet": {"packet_id": h(packet_data), **packet_data},
    "package_hash": h(project),
    "split_hash": h(manifest),
}
artifact = {"variant_id": variant["variant_id"], "variant_hash": h(variant), "expectations": []}
package = {
    "schema_version": "benchmark-package-v1",
    "manifest": manifest,
    "projects": [project],
    "variants": [variant],
    "expectations": [artifact],
}
Path(sys.argv[2]).write_text(json.dumps(package, ensure_ascii=False), encoding="utf-8")
