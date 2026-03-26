"""Shared coordinate-grounded evidence helpers for tile tasks."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ...shared.bbox_projection import BBox, ordered_ids_to_point_path_and_bbox_set
from .path_grid import cell_id


Coord = Tuple[int, int]


def sort_coords_row_major(coords: Sequence[Coord]) -> List[Coord]:
    """Return coordinates in canonical row-major order."""
    return sorted({(int(row), int(col)) for row, col in coords}, key=lambda item: (int(item[0]), int(item[1])))


def coordinate_set_evidence_artifacts(
    *,
    coords: Sequence[Coord],
    bbox_map: Mapping[str, BBox],
) -> Dict[str, Any]:
    """Build canonical `grid_point_set` evidence plus projections for one coordinate set."""
    ordered_coords = sort_coords_row_major(coords)
    ordered_ids = [cell_id(coord) for coord in ordered_coords]
    pixel_points, bbox_set = ordered_ids_to_point_path_and_bbox_set(
        ordered_ids=ordered_ids,
        bbox_map=bbox_map,
    )
    grid_points = [[int(row), int(col)] for row, col in ordered_coords]
    return {
        "evidence_type": "grid_point_set",
        "evidence_value": list(grid_points),
        "witness_symbolic": {
            "type": "id_set",
            "ids": list(ordered_ids),
        },
        "projected_evidence": {
            "grid_point_set": list(grid_points),
            "pixel_point_set": list(pixel_points),
            "bbox_set": list(bbox_set),
        },
    }


def coordinate_path_evidence_artifacts(
    *,
    coords: Sequence[Coord],
    bbox_map: Mapping[str, BBox],
) -> Dict[str, Any]:
    """Build canonical `grid_point_path` evidence plus projections for one coordinate path."""
    ordered_coords = [(int(row), int(col)) for row, col in coords]
    ordered_ids = [cell_id(coord) for coord in ordered_coords]
    pixel_points, bbox_set = ordered_ids_to_point_path_and_bbox_set(
        ordered_ids=ordered_ids,
        bbox_map=bbox_map,
    )
    grid_points = [[int(row), int(col)] for row, col in ordered_coords]
    return {
        "evidence_type": "grid_point_path",
        "evidence_value": list(grid_points),
        "witness_symbolic": {
            "type": "id_path",
            "ids": list(ordered_ids),
        },
        "projected_evidence": {
            "grid_point_path": list(grid_points),
            "pixel_point_path": list(pixel_points),
            "bbox_set": list(bbox_set),
        },
    }


__all__ = [
    "Coord",
    "coordinate_path_evidence_artifacts",
    "coordinate_set_evidence_artifacts",
    "sort_coords_row_major",
]
