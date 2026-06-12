"""Source-generator output record for graph-paper public tasks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping


@dataclass(frozen=True)
class SourceTaskOutput:
    """Output-shaped record used inside graph-paper scene shared helpers."""

    prompt: str
    answer_gt: Any
    annotation_gt: Any
    image: Any
    image_id: str
    trace_payload: Mapping[str, Any]
    task_versions: Mapping[str, str] = field(default_factory=dict)
    query_id: str | None = None
    prompt_variants: Mapping[str, str] = field(default_factory=dict)
