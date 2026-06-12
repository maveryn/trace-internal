"""Annotation projection helpers for Crossing games scenes."""

from __future__ import annotations

from typing import Sequence

from .rendering import RenderedCrossingScene


def entity_bboxes_for_ids(
    rendered_scene: RenderedCrossingScene,
    entity_ids: Sequence[str],
) -> list[list[float]]:
    """Return rendered entity bboxes for one set of Crossing entity ids."""

    entity_bboxes = rendered_scene.render_map.get("entity_bboxes_px", {})
    bboxes: list[list[float]] = []
    for entity_id in entity_ids:
        bbox = entity_bboxes.get(str(entity_id))
        if bbox is None:
            raise ValueError(f"missing rendered Crossing entity bbox for {entity_id}")
        bboxes.append([round(float(value), 3) for value in bbox])
    return bboxes


__all__ = ["entity_bboxes_for_ids"]
