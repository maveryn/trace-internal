"""Helpers for loading task-group visual defaults with fallbacks."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Mapping

from ..task_group_config import get_task_group_defaults


def load_task_group_visual_section(
    *,
    domain: str,
    task_group: str,
    section: str,
    fallback: Mapping[str, Any],
    merge_with_fallback: bool,
) -> Dict[str, Any]:
    """Load one visual section (`background`/`noise`) with fallback handling."""
    cfg = get_task_group_defaults(str(domain), str(task_group))
    visual = cfg.get("visual", {})
    if not isinstance(visual, Mapping):
        return deepcopy(dict(fallback))

    section_value = visual.get(str(section), {})
    if not isinstance(section_value, Mapping):
        return deepcopy(dict(fallback))

    if bool(merge_with_fallback):
        merged = deepcopy(dict(fallback))
        merged.update(dict(section_value))
        return merged
    return dict(section_value)
