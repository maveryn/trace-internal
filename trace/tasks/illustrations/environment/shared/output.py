"""Scene-output serialization helpers for environment illustrations."""

from __future__ import annotations

from typing import Any, Dict

from ...shared.object_rendering import serialize_rendered_illustration_object

from .rendering import RenderedEnvironmentObjectScene


def serialize_environment_objects(scene: RenderedEnvironmentObjectScene) -> tuple[list[dict[str, Any]], Dict[str, list[float]], Dict[str, list[float]]]:
    """Serialize foreground objects and return object/part bbox maps."""

    serialized_objects = [serialize_rendered_illustration_object(obj) for obj in scene.objects]
    object_bboxes = {str(obj["object_id"]): list(obj["bbox"]) for obj in serialized_objects}
    part_bboxes = {
        str(part["part_id"]): list(part["bbox"])
        for obj in serialized_objects
        for part in obj["parts"]
    }
    return serialized_objects, object_bboxes, part_bboxes


__all__ = ["serialize_environment_objects"]
