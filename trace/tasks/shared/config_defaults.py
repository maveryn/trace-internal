"""Task-level config fallback helpers shared across task modules."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from ...core.task_group_config import resolve_task_group_section_defaults


def group_default(mapping: Mapping[str, Any], key: str, fallback: Any) -> Any:
    """Return `mapping[key]` when present; otherwise return `fallback`."""
    if key in mapping:
        return mapping.get(key)
    return fallback


def split_generation_rendering_prompt_defaults(
    mapping: Mapping[str, Any],
    *,
    task_id: str | None = None,
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """Return `generation`, `rendering`, and `prompt` defaults sections."""
    generation = resolve_task_group_section_defaults(mapping, "generation", task_id=task_id)
    rendering = resolve_task_group_section_defaults(mapping, "rendering", task_id=task_id)
    prompt = resolve_task_group_section_defaults(mapping, "prompt", task_id=task_id)
    return generation, rendering, prompt
