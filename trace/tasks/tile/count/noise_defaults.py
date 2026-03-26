"""Visual-variation defaults for the tile/count task group."""

from __future__ import annotations

from typing import Any, Dict

from ...shared.visual_defaults import default_noise_fallback, load_task_group_noise_defaults


def _fallback_noise_defaults() -> Dict[str, Any]:
    """Return safe fallback defaults if config is missing or invalid."""
    return default_noise_fallback(apply_prob=0.5)


def _load_task_group_noise_defaults() -> Dict[str, Any]:
    """Load tile/count noise defaults from merged task-group config."""
    return load_task_group_noise_defaults(
        domain="tile",
        task_group="count",
        fallback=_fallback_noise_defaults(),
        merge_with_fallback=False,
    )


POST_IMAGE_NOISE_DEFAULTS: Dict[str, Any] = _load_task_group_noise_defaults()
