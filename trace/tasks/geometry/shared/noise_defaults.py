"""Visual-variation defaults shared across geometry domain tasks."""

from __future__ import annotations

from typing import Any, Dict

from ...shared.visual_defaults import (
    default_noise_fallback,
    load_domain_noise_defaults,
    load_task_group_noise_defaults,
)


def _fallback_noise_defaults() -> Dict[str, Any]:
    """Return safe fallback defaults if config is missing or invalid."""
    return default_noise_fallback(apply_prob=0.5)


def load_geometry_noise_defaults(*, task_group: str | None = None) -> Dict[str, Any]:
    """Load geometry noise defaults with optional task-group override support."""
    fallback = _fallback_noise_defaults()
    if task_group is not None and str(task_group).strip():
        return load_task_group_noise_defaults(
            domain="geometry",
            task_group=str(task_group),
            fallback=fallback,
            merge_with_fallback=False,
        )
    return load_domain_noise_defaults(
        domain="geometry",
        fallback=fallback,
        merge_with_fallback=False,
    )


# Geometry measurement post-image noise defaults, sourced from domain config
# unless a task-group override is defined.
POST_IMAGE_NOISE_DEFAULTS: Dict[str, Any] = load_geometry_noise_defaults(task_group="measurement")
