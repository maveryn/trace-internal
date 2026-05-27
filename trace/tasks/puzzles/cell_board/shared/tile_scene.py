"""Shared scene-entity helpers for tile-board tasks."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Tuple

from .grid_graph import cell_id


Coord = Tuple[int, int]


def build_tile_cell_entities(
    *,
    rows: int,
    cols: int,
    attrs_by_coord: Mapping[Coord, Mapping[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    """Build `scene_ir.entities` entries for one dense tile board."""
    extra_attrs = dict(attrs_by_coord) if isinstance(attrs_by_coord, Mapping) else {}
    entities: List[Dict[str, Any]] = []
    for row in range(int(rows)):
        for col in range(int(cols)):
            coord = (int(row), int(col))
            attrs: Dict[str, Any] = {
                "row": int(row),
                "col": int(col),
            }
            per_cell = extra_attrs.get(coord, {})
            if isinstance(per_cell, Mapping):
                attrs.update({str(key): value for key, value in per_cell.items()})
            entities.append(
                {
                    "entity_id": cell_id(coord),
                    "entity_type": "tile_cell",
                    "attrs": attrs,
                }
            )
    return entities


__all__ = ["Coord", "build_tile_cell_entities"]
