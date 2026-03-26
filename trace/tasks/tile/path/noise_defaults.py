"""Visual-variation defaults for the tile/path task group."""

from __future__ import annotations

from typing import Any, Dict

from ..shared.visual_defaults import load_tile_noise_defaults


def _load_task_group_noise_defaults() -> Dict[str, Any]:
    """Load tile/path noise defaults from task-group config."""
    return load_tile_noise_defaults(task_group="path", apply_prob=0.0)


# Task-group-level post-image noise defaults shared by tile/path tasks.
POST_IMAGE_NOISE_DEFAULTS: Dict[str, Any] = _load_task_group_noise_defaults()
