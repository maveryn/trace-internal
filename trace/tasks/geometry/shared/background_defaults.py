"""Background defaults shared across geometry domain tasks."""

from __future__ import annotations

from typing import Any, Dict

from ...shared.visual_defaults import (
    load_domain_background_defaults,
    load_task_group_background_defaults,
)
from .graph_rendering import FALLBACK_GRAPH_STYLE


def _fallback_background_defaults() -> Dict[str, Any]:
    """Return safe fallback defaults if config is missing or invalid."""
    return {
        "enabled": True,
        "styles": {"graph_paper": dict(FALLBACK_GRAPH_STYLE)},
        "weights": {"graph_paper": 1.0},
    }


def load_geometry_background_defaults(*, task_group: str | None = None) -> Dict[str, Any]:
    """Load geometry background defaults with optional task-group override support."""
    fallback = _fallback_background_defaults()
    if task_group is not None and str(task_group).strip():
        return load_task_group_background_defaults(
            domain="geometry",
            task_group=str(task_group),
            fallback=fallback,
            merge_with_fallback=True,
        )
    return load_domain_background_defaults(
        domain="geometry",
        fallback=fallback,
        merge_with_fallback=True,
    )


# Geometry measurement_2d background defaults, sourced from domain config
# unless a task-group override is defined.
POST_IMAGE_BACKGROUND_DEFAULTS: Dict[str, Any] = load_geometry_background_defaults(task_group="measurement_2d")
