"""Background-style defaults for the tile/count task group."""

from __future__ import annotations

from typing import Any, Dict

from ...shared.visual_defaults import load_task_group_background_defaults


def _fallback_background_defaults() -> Dict[str, Any]:
    """Return safe fallback defaults if config is missing or invalid."""
    return {
        "enabled": True,
        "styles": {
            "solid_light": {
                "kind": "solid",
                "color": [246, 246, 246],
            }
        },
        "weights": {"solid_light": 1.0},
    }


def _load_task_group_background_defaults() -> Dict[str, Any]:
    """Load tile/count background defaults from merged task-group config."""
    return load_task_group_background_defaults(
        domain="tile",
        task_group="count",
        fallback=_fallback_background_defaults(),
        merge_with_fallback=True,
    )


POST_IMAGE_BACKGROUND_DEFAULTS: Dict[str, Any] = _load_task_group_background_defaults()
