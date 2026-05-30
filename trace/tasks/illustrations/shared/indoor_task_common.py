"""Shared helpers for indoor-room illustration tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

from ....core.sampling import normalize_positive_weights
from ....core.seed import spawn_rng
from ...shared.config_defaults import group_default
from ...shared.deterministic_sampling import resolve_selection_index
from .indoor_room_scene import (
    INDOOR_CONTAINER_TYPES,
    INDOOR_FURNITURE_TYPES,
    INDOOR_OBJECT_TYPES,
    INDOOR_SURFACE_TYPES,
    INDOOR_THEME_IDS,
    IndoorObjectSpec,
    RenderedIndoorRoomScene,
    indoor_scene_entities,
    render_indoor_room_scene,
)
from .object_library import STYLE_IDS, display_name_for_object_type, serialize_object


INDOOR_SETTING_NAMES: Dict[str, str] = {
    "living_room": "a living room",
    "kitchen": "a kitchen",
    "study": "a study",
    "bedroom": "a bedroom",
}


def indoor_setting_name(theme_id: str) -> str:
    return INDOOR_SETTING_NAMES.get(str(theme_id), "an illustrated indoor room")


def display_name(object_type: str) -> str:
    return display_name_for_object_type(str(object_type))


def uniform_string_probability_map(values: Sequence[str], *, selected: str | None = None) -> Dict[str, float]:
    support = tuple(str(value) for value in values)
    if not support:
        return {}
    if selected is not None:
        return {str(selected): 1.0}
    probability = 1.0 / float(len(support))
    return {str(value): float(probability) for value in support}


def theme_support(params: Mapping[str, Any], generation_defaults: Mapping[str, Any]) -> tuple[str, ...]:
    raw = params.get("theme_support", group_default(generation_defaults, "indoor_theme_support", INDOOR_THEME_IDS))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("theme_support must be a sequence")
    supported = tuple(str(value) for value in raw if str(value) in set(INDOOR_THEME_IDS))
    if not supported:
        raise ValueError("theme_support resolved no supported indoor themes")
    return tuple(dict.fromkeys(supported))


def typed_support(
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    *,
    param_key: str,
    default_key: str,
    fallback: Sequence[str],
    error_name: str,
) -> tuple[str, ...]:
    raw = params.get(param_key, group_default(generation_defaults, default_key, tuple(fallback)))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError(f"{param_key} must be a sequence")
    allowed = set(str(value) for value in fallback)
    supported = tuple(str(value) for value in raw if str(value) in allowed)
    if not supported:
        raise ValueError(f"{error_name} resolved no supported values")
    return tuple(dict.fromkeys(supported))


def support_choice(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
    support: Sequence[str],
    explicit_key: str,
) -> tuple[str, Dict[str, float]]:
    explicit = params.get(explicit_key)
    values = tuple(str(value) for value in support)
    if explicit is not None:
        choice = str(explicit)
        if choice not in set(values):
            raise ValueError(f"{explicit_key} must be one of {values}")
        return choice, uniform_string_probability_map(values, selected=choice)
    selection_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    choice = str(values[int(selection_index) % len(values)])
    return choice, uniform_string_probability_map(values)


def style_weights(params: Mapping[str, Any], render_defaults: Mapping[str, Any]) -> Dict[str, float]:
    raw = params.get("style_weights", group_default(render_defaults, "style_weights", {style: 1.0 for style in STYLE_IDS}))
    if not isinstance(raw, Mapping):
        raise ValueError("style_weights must be a mapping")
    return normalize_positive_weights({str(key): float(value) for key, value in raw.items()}, default_keys=STYLE_IDS)


def indoor_theme_weights(theme_id: str) -> Dict[str, float]:
    return {theme: (1.0 if str(theme) == str(theme_id) else 0.0) for theme in INDOOR_THEME_IDS}


def indoor_render_params(
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    *,
    fallback: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        "canvas_width": int(
            params.get("canvas_width", group_default(render_defaults, "indoor_canvas_width", int(fallback["canvas_width"])))
        ),
        "canvas_height": int(
            params.get("canvas_height", group_default(render_defaults, "indoor_canvas_height", int(fallback["canvas_height"])))
        ),
        "object_size_min_px": int(
            params.get(
                "object_size_min_px",
                group_default(render_defaults, "indoor_object_size_min_px", int(fallback["object_size_min_px"])),
            )
        ),
        "object_size_max_px": int(
            params.get(
                "object_size_max_px",
                group_default(render_defaults, "indoor_object_size_max_px", int(fallback["object_size_max_px"])),
            )
        ),
        "render_scale": int(params.get("render_scale", group_default(render_defaults, "indoor_render_scale", int(fallback["render_scale"])))),
    }


def render_indoor_scene_from_specs(
    *,
    task_id: str,
    instance_seed: int,
    attempt_index: int,
    specs: Sequence[IndoorObjectSpec],
    theme_id: str,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    fallback: Mapping[str, Any],
) -> RenderedIndoorRoomScene:
    render_params = indoor_render_params(params, render_defaults, fallback=fallback)
    rng = spawn_rng(int(instance_seed), f"{task_id}:indoor-scene", int(attempt_index))
    return render_indoor_room_scene(
        rng=rng,
        object_specs=tuple(specs),
        canvas_width=int(render_params["canvas_width"]),
        canvas_height=int(render_params["canvas_height"]),
        render_scale=int(render_params["render_scale"]),
        theme_weights=indoor_theme_weights(str(theme_id)),
        style_weights=style_weights(params, render_defaults),
        object_size_min_px=int(render_params["object_size_min_px"]),
        object_size_max_px=int(render_params["object_size_max_px"]),
        highlight_container_type=str(params.get("highlight_container_type", "") or ""),
    )


def serialize_indoor_scene(scene: RenderedIndoorRoomScene) -> tuple[list[dict[str, Any]], Dict[str, list[float]], Dict[str, list[float]]]:
    serialized_objects = [serialize_object(obj) for obj in scene.objects]
    object_bboxes = {str(obj["object_id"]): list(obj["bbox"]) for obj in serialized_objects}
    part_bboxes = {
        str(part["part_id"]): list(part["bbox"])
        for obj in serialized_objects
        for part in obj["parts"]
    }
    return serialized_objects, object_bboxes, part_bboxes


def surface_bbox_map(scene: RenderedIndoorRoomScene) -> Dict[str, list[float]]:
    return {str(surface.surface_id): [round(float(v), 3) for v in surface.bbox_xyxy] for surface in scene.surfaces}


def surface_support_bbox_map(scene: RenderedIndoorRoomScene) -> Dict[str, list[float]]:
    return {str(surface.surface_id): [round(float(v), 3) for v in surface.support_bbox_xyxy] for surface in scene.surfaces}


def container_bbox_map(scene: RenderedIndoorRoomScene) -> Dict[str, list[float]]:
    return {str(container.container_id): [round(float(v), 3) for v in container.bbox_xyxy] for container in scene.containers}


def container_interior_bbox_map(scene: RenderedIndoorRoomScene) -> Dict[str, list[float]]:
    return {str(container.container_id): [round(float(v), 3) for v in container.interior_bbox_xyxy] for container in scene.containers}


def furniture_bbox_map(scene: RenderedIndoorRoomScene) -> Dict[str, list[float]]:
    return {str(furniture.furniture_id): [round(float(v), 3) for v in furniture.bbox_xyxy] for furniture in scene.furniture}


def placement_map(scene: RenderedIndoorRoomScene) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    for placement in scene.placements:
        result[str(placement.object_id)] = {
            "object_type": str(placement.object_type),
            "placement_kind": str(placement.placement_kind),
            "surface_id": placement.surface_id,
            "surface_type": placement.surface_type,
            "surface_contact_px": [round(float(v), 3) for v in placement.surface_contact_px] if placement.surface_contact_px else None,
            "surface_depth": round(float(placement.surface_depth), 4) if placement.surface_depth is not None else None,
            "container_id": placement.container_id,
            "container_type": placement.container_type,
            "region_relation": placement.region_relation,
            "region_furniture_id": placement.region_furniture_id,
            "relations": dict(placement.relations),
            "role": str(placement.role),
        }
    return result


def sort_bboxes_by_ids(bbox_map: Mapping[str, Sequence[float]], ids: Sequence[str]) -> list[list[float]]:
    boxes = [(str(item_id), [round(float(v), 3) for v in bbox_map[str(item_id)]]) for item_id in ids]
    ordered = sorted(boxes, key=lambda item: (float(item[1][1]), float(item[1][0]), str(item[0])))
    return [box for _item_id, box in ordered]


__all__ = [
    "INDOOR_CONTAINER_TYPES",
    "INDOOR_FURNITURE_TYPES",
    "INDOOR_OBJECT_TYPES",
    "INDOOR_SETTING_NAMES",
    "INDOOR_SURFACE_TYPES",
    "INDOOR_THEME_IDS",
    "IndoorObjectSpec",
    "container_bbox_map",
    "container_interior_bbox_map",
    "display_name",
    "furniture_bbox_map",
    "indoor_scene_entities",
    "indoor_setting_name",
    "render_indoor_scene_from_specs",
    "serialize_indoor_scene",
    "sort_bboxes_by_ids",
    "support_choice",
    "surface_bbox_map",
    "surface_support_bbox_map",
    "theme_support",
    "typed_support",
    "uniform_string_probability_map",
    "placement_map",
]
