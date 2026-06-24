"""Shared relation-scene object helpers for 3D object-scene tasks."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ...shared.object_scene import _make_object_spec, _project_screen, _sample_shape_dimensions


def make_sampled_object(
    *,
    rng,
    object_id: str,
    shape_type: str,
    object_role: str,
    xy: Tuple[float, float],
    label: str | None = None,
) -> Dict[str, Any]:
    """Create one sampled object spec while preserving domain object-resource metadata."""
    dimensions_xyz, dimension_scale = _sample_shape_dimensions(str(shape_type), object_role=str(object_role), rng=rng)
    return _make_object_spec(
        object_id=str(object_id),
        shape_type=str(shape_type),
        object_role=str(object_role),
        xy=xy,
        dimensions_xyz=dimensions_xyz,
        dimension_scale=float(dimension_scale),
        label=label,
    )


def set_xy(spec: Mapping[str, Any], xy: Tuple[float, float]) -> Dict[str, Any]:
    """Move an object spec on the floor plane without changing its dimensions or identity."""
    updated = dict(spec)
    height = float(updated["dimensions_xyz"][2])
    updated["base_xyz"] = [round(float(xy[0]), 4), round(float(xy[1]), 4), 0.0]
    updated["world_xyz"] = [round(float(xy[0]), 4), round(float(xy[1]), 4), round(float(height * 0.5), 4)]
    return updated


def prompt_name(spec: Mapping[str, Any]) -> str:
    """Return the user-facing object name recorded on a sampled object spec."""
    return str(spec.get("prompt_name", spec.get("object_name", spec.get("shape_type", "object"))))


def can_place(candidate: Mapping[str, Any], placed: Sequence[Mapping[str, Any]], *, clearance: float = 0.12) -> bool:
    """Check floor-plane footprint separation before a relation scene accepts a placement."""
    cx, cy, _cz = (float(value) for value in candidate["world_xyz"])
    for item in placed:
        ix, iy, _iz = (float(value) for value in item["world_xyz"])
        min_distance = float(candidate["footprint_radius"]) + float(item["footprint_radius"]) + float(clearance)
        if math.hypot(float(cx - ix), float(cy - iy)) < min_distance:
            return False
    return True


def finalize_specs(
    specs: Sequence[Mapping[str, Any]],
    *,
    camera,
    frame,
) -> List[Dict[str, Any]]:
    """Attach projected screen/camera coordinates to object specs without altering semantic attrs."""
    finalized_specs: List[Dict[str, Any]] = []
    for spec in specs:
        screen = _project_screen(spec["world_xyz"], camera, frame)
        finalized = dict(spec)
        finalized.update(
            {
                "screen_xy": [round(float(screen[0]), 3), round(float(screen[1]), 3)],
                "camera_xyz": [round(float(screen[5]), 4), round(float(screen[6]), 4), round(float(screen[4]), 4)],
                "camera_distance": round(float(screen[7]), 4),
            }
        )
        finalized_specs.append(finalized)
    return list(finalized_specs)


__all__ = [
    "can_place",
    "finalize_specs",
    "make_sampled_object",
    "prompt_name",
    "set_xy",
]
