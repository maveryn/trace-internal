"""Versioned type registry for answer/evidence envelopes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Set


@dataclass(frozen=True)
class TypeRegistry:
    """Registered envelope type ids loaded from disk."""

    version: str
    answer_types: Set[str]
    evidence_types: Set[str]

    def validate_answer_type(self, type_id: str) -> bool:
        return type_id in self.answer_types

    def validate_evidence_type(self, type_id: str) -> bool:
        return type_id in self.evidence_types


DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parents[1] / "configs" / "type_registry_v1.json"


def load_type_registry(path: str | Path | None = None) -> TypeRegistry:
    """Load type registry JSON and return a validated in-memory object."""
    registry_path = Path(path) if path is not None else DEFAULT_REGISTRY_PATH
    raw = json.loads(registry_path.read_text(encoding="utf-8"))
    return TypeRegistry(
        version=str(raw["type_registry_version"]),
        answer_types=set(str(v) for v in raw.get("answer_types", [])),
        evidence_types=set(str(v) for v in raw.get("evidence_types", [])),
    )
