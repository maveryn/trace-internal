"""Task-level config fallback helpers shared across task modules."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple


def group_default(mapping: Mapping[str, Any], key: str, fallback: Any) -> Any:
    """Return `mapping[key]` when present; otherwise return `fallback`."""
    if key in mapping:
        return mapping.get(key)
    return fallback


def _section_defaults(mapping: Mapping[str, Any], section: str) -> Dict[str, Any]:
    """Return one task-group config section as a plain dictionary."""
    value = mapping.get(str(section), {})
    if not isinstance(value, Mapping):
        return {}
    return dict(value)


def split_generation_rendering_prompt_defaults(
    mapping: Mapping[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """Return `generation`, `rendering`, and `prompt` defaults sections."""
    generation = _section_defaults(mapping, "generation")
    rendering = _section_defaults(mapping, "rendering")
    prompt = _section_defaults(mapping, "prompt")
    return generation, rendering, prompt
