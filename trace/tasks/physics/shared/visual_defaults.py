"""Physics-domain visual-default loader helpers."""

from __future__ import annotations

from typing import Any, Dict

from ...shared.visual_defaults import default_noise_fallback, load_task_group_background_defaults, load_task_group_noise_defaults


def solid_light_background_fallback() -> Dict[str, Any]:
    """Return the canonical low-structure physics background fallback."""

    return {
        "enabled": True,
        "styles": {
            "solid_light": {
                "kind": "solid",
                "color": [248, 249, 251],
            }
        },
        "weights": {"solid_light": 1.0},
    }


def load_physics_background_defaults(*, task_group: str) -> Dict[str, Any]:
    """Load physics-task background defaults for one task group."""

    return load_task_group_background_defaults(
        domain="physics",
        task_group=str(task_group),
        fallback=solid_light_background_fallback(),
        merge_with_fallback=True,
    )


def load_physics_noise_defaults(*, task_group: str, apply_prob: float) -> Dict[str, Any]:
    """Load physics-task post-image noise defaults for one task group."""

    return load_task_group_noise_defaults(
        domain="physics",
        task_group=str(task_group),
        fallback=default_noise_fallback(apply_prob=float(apply_prob)),
        merge_with_fallback=False,
    )


__all__ = [
    "load_physics_background_defaults",
    "load_physics_noise_defaults",
    "solid_light_background_fallback",
]

