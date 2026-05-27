"""Base task interface for TRACE generators."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Protocol

from PIL import Image

from ..core.types import TaskComplexity, TypedValue


@dataclass
class TaskOutput:
    """Task-level generation output before builder packaging."""

    prompt: str
    answer_gt: TypedValue
    evidence_gt: TypedValue
    image: Image.Image
    image_id: str
    trace_payload: Dict[str, Any]
    complexity: TaskComplexity
    task_versions: Dict[str, str]
    # Internal generator selector used by wrappers and review replay.
    # Public dataset identity is `query_id`.
    query_variant: str = ""
    scene_id: str = ""
    query_id: str = ""
    prompt_variants: Dict[str, str] = field(default_factory=dict)


class Task(Protocol):
    """Protocol that every registered TRACE task must satisfy."""

    task_id: str
    domain: str
    task_group: str
    default_dataset_enabled: bool

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic task output for the given seed and params."""
