"""Validate an explicit manifest supplied by the caller; never load files implicitly."""

import hashlib
import json
from typing import Annotated, Literal, Self

from pydantic import Field, StrictInt, model_validator

from domain.models import Frozen, Hash, Text


class Dimension(Frozen):
    id: Annotated[StrictInt, Field(ge=1, le=10)]
    name: Text
    weight: Annotated[StrictInt, Field(gt=0)]
    block: Literal["idea", "study"]
    source: Text


class Rule(Frozen):
    id: Text
    source: Text
    consequence: Text


class Profile(Frozen):
    id: Text
    source: Text
    minimum_total: StrictInt | None
    floors: tuple[tuple[StrictInt, StrictInt], ...]
    requirements: tuple[str, ...]


class Manifest(Frozen):
    rubric_id: Literal["research-idea-protocol"]
    version: Literal["4", "5"]
    implementation_version: Literal["4.2.0", "5.0.0"]
    canonical_path: Literal["policies/rubric-v4.md", "policies/rubric-v5.md"]
    canonical_sha256: Hash
    status: Literal["implemented"]
    executable: Literal[True]
    dimensions: tuple[Dimension, ...]
    rules: tuple[Rule, ...]
    profiles: tuple[Profile, ...]
    anchors: tuple[str, ...]
    routes: tuple[str, ...]
    route_items: tuple[str, ...]
    rounding: Literal["nearest_whole_half_up_after_gates"]
    report_obligations: tuple[str, ...]

    @model_validator(mode="after")
    def versioned_contract(self) -> Self:
        expected = {
            "4": ("4.2.0", "policies/rubric-v4.md"),
            "5": ("5.0.0", "policies/rubric-v5.md"),
        }[self.version]
        if (self.implementation_version, self.canonical_path) != expected:
            raise ValueError("Manifest policy/version identity mismatch")
        if tuple(d.id for d in self.dimensions) != tuple(range(1, 11)):
            raise ValueError("Manifest requires the ten ordered v4 dimensions")
        if tuple(d.weight for d in self.dimensions) != (10, 10, 15, 15, 8, 9, 8, 10, 10, 5):
            raise ValueError("Weights disagree with v4")
        if tuple(d.block for d in self.dimensions) != ("idea",) * 7 + ("study",) * 3:
            raise ValueError("Invalid block applicability")
        for values in ([r.id for r in self.rules], [p.id for p in self.profiles]):
            if len(values) != len(set(values)):
                raise ValueError("Duplicate manifest identifiers")
        if len(self.anchors) != 11 or set(self.routes) != {"EXPLAIN", "ESTABLISH", "TEST"}:
            raise ValueError("Invalid anchor/route contract")
        return self

    @property
    def sha256(self) -> str:
        canonical = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
