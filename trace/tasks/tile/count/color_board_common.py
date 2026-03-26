"""Count-task adapters over the shared named-color tile-board helpers."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from ..shared.named_color_board import (
    Coord,
    RectangularNamedColorBoardScene as RectangularColorBoardScene,
    RectangularNamedColorBoardTaskDefaults as RectangularColorBoardTaskDefaults,
    build_palette_trace,
    build_rectangular_named_color_board_render_spec as build_rectangular_color_board_render_spec,
    build_rectangular_named_color_board_scene as build_rectangular_color_board_scene,
    sample_color_board,
)
from ..shared.tile_scene import build_tile_cell_entities


def build_color_board_scene_entities(
    scene: RectangularColorBoardScene,
    *,
    query_color_name: str,
    extra_attrs_by_coord: Mapping[Coord, Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Build scene entities for one rectangular color board with query annotations."""
    extra_attrs = dict(extra_attrs_by_coord) if isinstance(extra_attrs_by_coord, Mapping) else {}
    attrs_by_coord: Dict[Coord, Dict[str, Any]] = {}
    for coord, (name, rgb) in scene.board_colors.items():
        attrs: Dict[str, Any] = {
            "color_name": str(name),
            "fill_rgb": [int(rgb[0]), int(rgb[1]), int(rgb[2])],
            "is_query_match": bool(str(name) == str(query_color_name)),
        }
        per_coord = extra_attrs.get(coord, {})
        if isinstance(per_coord, Mapping):
            attrs.update({str(key): value for key, value in per_coord.items()})
        attrs_by_coord[(int(coord[0]), int(coord[1]))] = attrs
    return build_tile_cell_entities(
        rows=int(scene.rows),
        cols=int(scene.cols),
        attrs_by_coord=attrs_by_coord,
    )


__all__ = [
    "Coord",
    "RectangularColorBoardScene",
    "RectangularColorBoardTaskDefaults",
    "build_color_board_scene_entities",
    "build_palette_trace",
    "build_rectangular_color_board_render_spec",
    "build_rectangular_color_board_scene",
    "sample_color_board",
]
