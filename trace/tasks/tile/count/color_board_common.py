"""Count-task adapters over the shared named-color tile-board helpers."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

from ..shared.named_color_board import (
    Coord,
    RectangularNamedColorBoardScene as RectangularColorBoardScene,
    RectangularNamedColorBoardTaskDefaults as RectangularColorBoardTaskDefaults,
    build_palette_trace,
    build_rectangular_named_color_board_render_spec as build_rectangular_color_board_render_spec,
    build_rectangular_named_color_board_scene as build_rectangular_color_board_scene,
    sample_color_board,
)
from ..shared.grid_graph import connected_components_for_active_coords
from ..shared.tile_evidence import sort_coords_row_major
from ..shared.tile_scene import build_tile_cell_entities


def build_color_component_catalog(
    scene: RectangularColorBoardScene,
) -> List[Dict[str, Any]]:
    """Return per-color component summaries for one rectangular named-color board."""
    catalog: List[Dict[str, Any]] = []
    for palette_color_name, palette_color_rgb in scene.palette:
        matching_coords = sort_coords_row_major(
            [
                (int(row), int(col))
                for (row, col), (name, _rgb) in scene.board_colors.items()
                if str(name) == str(palette_color_name)
            ]
        )
        if not matching_coords:
            raise RuntimeError("sampled query color must appear at least once on the board")
        component_coords = [
            sort_coords_row_major(component)
            for component in connected_components_for_active_coords(matching_coords)
        ]
        component_sizes = [int(len(component)) for component in component_coords]
        largest_component_size = max(component_sizes) if component_sizes else 0
        largest_component_indices = [
            int(index)
            for index, size in enumerate(component_sizes)
            if int(size) == int(largest_component_size)
        ]
        catalog.append(
            {
                "query_color_name": str(palette_color_name),
                "query_color_rgb": [int(palette_color_rgb[0]), int(palette_color_rgb[1]), int(palette_color_rgb[2])],
                "matching_coords": [[int(row), int(col)] for row, col in matching_coords],
                "component_coords": [
                    [[int(row), int(col)] for row, col in component]
                    for component in component_coords
                ],
                "component_count": int(len(component_coords)),
                "component_sizes": [int(size) for size in component_sizes],
                "largest_component_size": int(largest_component_size),
                "largest_component_indices": [int(index) for index in largest_component_indices],
            }
        )
    return catalog


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
    "build_color_component_catalog",
    "Coord",
    "RectangularColorBoardScene",
    "RectangularColorBoardTaskDefaults",
    "build_color_board_scene_entities",
    "build_palette_trace",
    "build_rectangular_color_board_render_spec",
    "build_rectangular_color_board_scene",
    "sample_color_board",
]
