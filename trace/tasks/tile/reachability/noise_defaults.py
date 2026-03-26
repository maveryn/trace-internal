"""Visual-variation defaults for the tile/reachability task group."""

from __future__ import annotations

from typing import Any, Dict

from ..shared.visual_defaults import load_tile_noise_defaults


def _load_task_group_noise_defaults() -> Dict[str, Any]:
    """Load tile/reachability noise defaults from merged task-group config."""
    return load_tile_noise_defaults(task_group="reachability", apply_prob=0.5)


POST_IMAGE_NOISE_DEFAULTS: Dict[str, Any] = _load_task_group_noise_defaults()
