"""Count-task adapters over the shared named-color tile-board helpers."""

from __future__ import annotations

from typing import Any, Dict, List

from ..shared.named_color_board import (
    RectangularNamedColorBoardScene as RectangularColorBoardScene,
    RectangularNamedColorBoardTaskDefaults as RectangularColorBoardTaskDefaults,
    build_palette_trace,
    build_rectangular_named_color_board_render_spec as build_rectangular_color_board_render_spec,
    build_rectangular_named_color_board_scene as build_rectangular_color_board_scene,
    sample_color_board,
)
from ..shared.grid_graph import connected_components_for_active_coords
from ..shared.tile_evidence import sort_coords_row_major


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
__all__ = [
    "build_color_component_catalog",
    "RectangularColorBoardScene",
    "RectangularColorBoardTaskDefaults",
    "build_palette_trace",
    "build_rectangular_color_board_render_spec",
    "build_rectangular_color_board_scene",
    "sample_color_board",
]
