"""Annotation and trace projection helpers for park/playground scenes."""

from __future__ import annotations

from .rendering import (
    park_decor_bbox_map,
    park_person_bbox_map,
    park_scene_entities,
    serialize_park_scene,
    sort_park_bboxes,
)

__all__ = [
    "park_decor_bbox_map",
    "park_person_bbox_map",
    "park_scene_entities",
    "serialize_park_scene",
    "sort_park_bboxes",
]
