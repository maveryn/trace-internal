"""Games-domain visual-default loader helpers."""

from __future__ import annotations

from typing import Any, Dict

from ...shared.visual_defaults import default_noise_fallback, load_task_group_background_defaults, load_task_group_noise_defaults


def solid_table_background_fallback() -> Dict[str, Any]:
    """Return the canonical low-structure games background fallback."""

    return {
        "enabled": True,
        "styles": {
            "felt_green": {
                "kind": "solid",
                "color": [42, 92, 74],
            }
        },
        "weights": {"felt_green": 1.0},
    }


def load_games_background_defaults(*, task_group: str) -> Dict[str, Any]:
    """Load games-task background defaults for one task group."""

    return load_task_group_background_defaults(
        domain="games",
        task_group=str(task_group),
        fallback=solid_table_background_fallback(),
        merge_with_fallback=True,
    )


def load_games_noise_defaults(*, task_group: str, apply_prob: float) -> Dict[str, Any]:
    """Load games-task post-image noise defaults for one task group."""

    return load_task_group_noise_defaults(
        domain="games",
        task_group=str(task_group),
        fallback=default_noise_fallback(apply_prob=float(apply_prob)),
        merge_with_fallback=False,
    )


__all__ = [
    "load_games_background_defaults",
    "load_games_noise_defaults",
    "solid_table_background_fallback",
]

