"""Visual-variation defaults for the tile/path task group."""

from __future__ import annotations

from typing import Any, Dict

from ...shared.visual_defaults import default_noise_fallback, load_task_group_noise_defaults


def _fallback_noise_defaults() -> Dict[str, Any]:
    """Return safe fallback defaults if config is missing or invalid."""
    return default_noise_fallback(apply_prob=0.0)


def _load_task_group_noise_defaults() -> Dict[str, Any]:
    """Load tile/path noise defaults from task-group config."""
    return load_task_group_noise_defaults(
        domain="tile",
        task_group="path",
        fallback=_fallback_noise_defaults(),
        merge_with_fallback=False,
    )


# Task-group-level post-image noise defaults shared by tile/path tasks.
POST_IMAGE_NOISE_DEFAULTS: Dict[str, Any] = _load_task_group_noise_defaults()
