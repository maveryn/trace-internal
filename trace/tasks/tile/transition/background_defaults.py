"""Background-style defaults for the tile/transition task group."""

from __future__ import annotations

from typing import Any, Dict

from ..shared.visual_defaults import load_tile_background_defaults


def _load_task_group_background_defaults() -> Dict[str, Any]:
    """Load tile/transition background defaults from merged task-group config."""
    return load_tile_background_defaults(task_group="transition")


POST_IMAGE_BACKGROUND_DEFAULTS: Dict[str, Any] = _load_task_group_background_defaults()

