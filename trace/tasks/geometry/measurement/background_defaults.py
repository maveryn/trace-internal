"""Background-style defaults for the geometry/measurement task group."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

from ....core.task_group_config import get_task_group_defaults


def _fallback_background_defaults() -> Dict[str, Any]:
    """Return safe fallback defaults if config is missing or invalid."""
    return {
        "enabled": True,
        "styles": {
            "solid_light": {
                "kind": "solid",
                "color": [248, 248, 248],
            }
        },
        "weights": {"solid_light": 1.0},
    }


def _load_task_group_background_defaults() -> Dict[str, Any]:
    """Load geometry/measurement background defaults from task-group config."""
    cfg = get_task_group_defaults("geometry", "measurement")
    visual = cfg.get("visual", {})
    if not isinstance(visual, dict):
        return _fallback_background_defaults()
    background = visual.get("background", {})
    if not isinstance(background, dict):
        return _fallback_background_defaults()
    merged = _fallback_background_defaults()
    merged.update(dict(background))
    return deepcopy(merged)


POST_IMAGE_BACKGROUND_DEFAULTS: Dict[str, Any] = _load_task_group_background_defaults()
