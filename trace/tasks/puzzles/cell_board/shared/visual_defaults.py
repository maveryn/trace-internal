"""Cell-board puzzle visual-default loader helpers."""

from __future__ import annotations

from typing import Any, Dict

from trace.tasks.shared.visual_defaults import (
    default_noise_fallback,
    load_scene_background_defaults,
    load_scene_noise_defaults,
)


def solid_light_background_fallback() -> Dict[str, Any]:
    """Return the canonical low-structure tile background fallback."""
    return {
        "enabled": True,
        "styles": {
            "solid_light": {
                "kind": "solid",
                "color": [246, 246, 246],
            }
        },
        "weights": {"solid_light": 1.0},
    }


def _cell_board_scene_id(scene_id: str) -> str:
    group = str(scene_id)
    return group if group.startswith("cell_board_") else f"cell_board_{group}"


def load_tile_background_defaults(*, scene_id: str) -> Dict[str, Any]:
    """Load one cell-board scene background config with the canonical fallback."""
    return load_scene_background_defaults(
        domain="puzzles",
        scene_id=_cell_board_scene_id(str(scene_id)),
        fallback=solid_light_background_fallback(),
        merge_with_fallback=True,
    )


def load_tile_noise_defaults(*, scene_id: str, apply_prob: float) -> Dict[str, Any]:
    """Load one cell-board scene noise config with the canonical fallback."""
    return load_scene_noise_defaults(
        domain="puzzles",
        scene_id=_cell_board_scene_id(str(scene_id)),
        fallback=default_noise_fallback(apply_prob=float(apply_prob)),
        merge_with_fallback=False,
    )


__all__ = [
    "load_tile_background_defaults",
    "load_tile_noise_defaults",
    "solid_light_background_fallback",
]
