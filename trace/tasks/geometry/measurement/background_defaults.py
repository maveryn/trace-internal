"""Background-style defaults for the geometry/measurement task group."""

from __future__ import annotations

from typing import Any, Dict

from ...shared.visual_defaults import load_task_group_background_defaults
from ..shared.graph_rendering import FALLBACK_GRAPH_STYLE


def _fallback_background_defaults() -> Dict[str, Any]:
    """Return safe fallback defaults if config is missing or invalid."""
    return {
        "enabled": True,
        "styles": {
            "graph_paper": dict(FALLBACK_GRAPH_STYLE)
        },
        "weights": {"graph_paper": 1.0},
    }


def _load_task_group_background_defaults() -> Dict[str, Any]:
    """Load geometry/measurement background defaults from task-group config."""
    return load_task_group_background_defaults(
        domain="geometry",
        task_group="measurement",
        fallback=_fallback_background_defaults(),
        merge_with_fallback=True,
    )


POST_IMAGE_BACKGROUND_DEFAULTS: Dict[str, Any] = _load_task_group_background_defaults()
