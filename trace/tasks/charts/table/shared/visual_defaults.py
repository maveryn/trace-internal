"""Data-table chart visual-default loader helpers."""

from __future__ import annotations

from typing import Any, Dict

from trace.tasks.shared.visual_defaults import (
    default_noise_fallback,
    load_task_group_background_defaults,
    load_task_group_noise_defaults,
)


def _table_task_group(task_group: str) -> str:
    group = str(task_group)
    return group if group.startswith("table_") else f"table_{group}"


def solid_light_background_fallback() -> Dict[str, Any]:
    """Return the canonical low-structure table background fallback."""

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


def load_table_background_defaults(*, task_group: str) -> Dict[str, Any]:
    """Load table-task background config with the canonical fallback."""

    return load_task_group_background_defaults(
        domain="charts",
        task_group=_table_task_group(str(task_group)),
        fallback=solid_light_background_fallback(),
        merge_with_fallback=True,
    )


def load_table_noise_defaults(*, task_group: str, apply_prob: float) -> Dict[str, Any]:
    """Load table-task post-image noise config with the canonical fallback."""

    return load_task_group_noise_defaults(
        domain="charts",
        task_group=_table_task_group(str(task_group)),
        fallback=default_noise_fallback(apply_prob=float(apply_prob)),
        merge_with_fallback=False,
    )


__all__ = [
    "load_table_background_defaults",
    "load_table_noise_defaults",
    "solid_light_background_fallback",
]
