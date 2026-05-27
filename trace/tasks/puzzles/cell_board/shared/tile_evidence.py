"""Shared pixel-grounded evidence helpers for tile tasks."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from trace.tasks.shared.bbox_projection import BBox, ordered_ids_to_point_sequence_and_bbox_set
from .grid_graph import cell_id


Coord = Tuple[int, int]


def sort_coords_row_major(coords: Sequence[Coord]) -> List[Coord]:
    """Return coordinates in canonical row-major order."""
    return sorted({(int(row), int(col)) for row, col in coords}, key=lambda item: (int(item[0]), int(item[1])))


def coordinate_set_evidence_artifacts(
    *,
    coords: Sequence[Coord],
    bbox_map: Mapping[str, BBox],
) -> Dict[str, Any]:
    """Build public pixel point-set evidence plus private grid-coordinate metadata."""
    ordered_coords = sort_coords_row_major(coords)
    ordered_ids = [cell_id(coord) for coord in ordered_coords]
    pixel_points, bbox_set = ordered_ids_to_point_sequence_and_bbox_set(
        ordered_ids=ordered_ids,
        bbox_map=bbox_map,
    )
    grid_points = [[int(row), int(col)] for row, col in ordered_coords]
    return {
        "evidence_type": "point_set",
        "evidence_value": [list(point) for point in pixel_points],
        "witness_symbolic": {
            "type": "point_set",
            "count": len(pixel_points),
        },
        "private_witness": {
            "ids": list(ordered_ids),
            "grid_points": list(grid_points),
        },
        "projected_evidence": {
            "type": "point_set",
            "point_set": [list(point) for point in pixel_points],
            "pixel_point_set": [list(point) for point in pixel_points],
            "bbox_set": list(bbox_set),
        },
    }


def coordinate_path_evidence_artifacts(
    *,
    coords: Sequence[Coord],
    bbox_map: Mapping[str, BBox],
) -> Dict[str, Any]:
    """Build public pixel point-path evidence plus private grid-coordinate metadata."""
    ordered_coords = [(int(row), int(col)) for row, col in coords]
    ordered_ids = [cell_id(coord) for coord in ordered_coords]
    pixel_points, bbox_set = ordered_ids_to_point_sequence_and_bbox_set(
        ordered_ids=ordered_ids,
        bbox_map=bbox_map,
    )
    grid_points = [[int(row), int(col)] for row, col in ordered_coords]
    return {
        "evidence_type": "point_sequence",
        "evidence_value": [list(point) for point in pixel_points],
        "witness_symbolic": {
            "type": "point_sequence",
            "count": len(pixel_points),
        },
        "private_witness": {
            "ids": list(ordered_ids),
            "grid_path": list(grid_points),
        },
        "projected_evidence": {
            "type": "point_sequence",
            "point_sequence": [list(point) for point in pixel_points],
            "pixel_point_sequence": [list(point) for point in pixel_points],
            "bbox_set": list(bbox_set),
        },
    }


__all__ = [
    "Coord",
    "coordinate_path_evidence_artifacts",
    "coordinate_set_evidence_artifacts",
    "sort_coords_row_major",
]
