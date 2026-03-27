"""Chart-domain visual-default loader helpers."""

from __future__ import annotations

from typing import Any, Dict

from ...shared.visual_defaults import default_noise_fallback, load_task_group_background_defaults, load_task_group_noise_defaults


def solid_light_background_fallback() -> Dict[str, Any]:
    """Return the canonical low-structure chart background fallback."""

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


def load_chart_background_defaults(*, task_group: str) -> Dict[str, Any]:
    """Load chart-task background config with the canonical fallback."""

    return load_task_group_background_defaults(
        domain="charts",
        task_group=str(task_group),
        fallback=solid_light_background_fallback(),
        merge_with_fallback=True,
    )


def load_chart_noise_defaults(*, task_group: str, apply_prob: float) -> Dict[str, Any]:
    """Load chart-task post-image noise config with the canonical fallback."""

    return load_task_group_noise_defaults(
        domain="charts",
        task_group=str(task_group),
        fallback=default_noise_fallback(apply_prob=float(apply_prob)),
        merge_with_fallback=False,
    )


__all__ = [
    "load_chart_background_defaults",
    "load_chart_noise_defaults",
    "solid_light_background_fallback",
]
