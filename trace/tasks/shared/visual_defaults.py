"""Shared task-level visual-default loading helpers.

These helpers keep task modules focused on fallback policy while reusing one
implementation for task-group visual section loading.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Mapping

from ...core.visual.defaults import load_task_group_visual_section
from ...core.visual.noise import TRACE_DEFAULT_NOISE_VALUE_RANGES


def default_noise_fallback(*, apply_prob: float) -> Dict[str, Any]:
    """Build a standard deterministic post-noise fallback config."""
    return {
        "apply_prob": float(apply_prob),
        "edit_types": ["blur", "downsample", "jpeg", "noise"],
        "edit_count_range": [1, 2],
        "value_ranges": deepcopy(TRACE_DEFAULT_NOISE_VALUE_RANGES),
    }


def load_task_group_background_defaults(
    *,
    domain: str,
    task_group: str,
    fallback: Mapping[str, Any],
    merge_with_fallback: bool = True,
) -> Dict[str, Any]:
    """Load task-group background defaults with shared section plumbing."""
    return load_task_group_visual_section(
        domain=str(domain),
        task_group=str(task_group),
        section="background",
        fallback=dict(fallback),
        merge_with_fallback=bool(merge_with_fallback),
    )


def load_task_group_noise_defaults(
    *,
    domain: str,
    task_group: str,
    fallback: Mapping[str, Any],
    merge_with_fallback: bool = False,
) -> Dict[str, Any]:
    """Load task-group post-noise defaults with shared section plumbing."""
    return load_task_group_visual_section(
        domain=str(domain),
        task_group=str(task_group),
        section="noise",
        fallback=dict(fallback),
        merge_with_fallback=bool(merge_with_fallback),
    )


__all__ = [
    "default_noise_fallback",
    "load_task_group_background_defaults",
    "load_task_group_noise_defaults",
]
