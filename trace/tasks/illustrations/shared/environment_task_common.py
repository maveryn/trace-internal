"""Shared helpers for environment-object illustration tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

from ...shared.config_defaults import group_default
from .environment_object_scene import (
    ENVIRONMENT_THEME_IDS,
    EnvironmentFeature,
    RenderedEnvironmentObjectScene,
    effective_environment_object_count,
    environment_scene_entities,
)
from .object_library import STYLE_IDS
from .object_rendering import serialize_rendered_illustration_object
from .style_registry import resolve_art_style_weights


FEATURE_TYPES_BY_THEME: Dict[str, tuple[str, ...]] = {
    "park_road": ("road",),
    "river_meadow": ("river",),
    "road_and_river": ("road", "river"),
    "canal_city": ("river",),
    "skyline_street": ("road",),
}

ENVIRONMENT_SETTING_NAMES: Dict[str, str] = {
    "park_road": "a park road setting",
    "river_meadow": "a meadow river setting",
    "road_and_river": "an outdoor setting with both a road and a river",
    "canal_city": "a city canal setting",
    "skyline_street": "a city street setting",
}


def style_weights(params: Mapping[str, Any], render_defaults: Mapping[str, Any]) -> Dict[str, float]:
    return resolve_art_style_weights(params, render_defaults, style_ids=STYLE_IDS)


def environment_render_params(
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    *,
    fallback: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        "canvas_width": int(
            params.get("canvas_width", group_default(render_defaults, "environment_canvas_width", int(fallback["canvas_width"])))
        ),
        "canvas_height": int(
            params.get("canvas_height", group_default(render_defaults, "environment_canvas_height", int(fallback["canvas_height"])))
        ),
        "object_size_min_px": int(
            params.get(
                "object_size_min_px",
                group_default(render_defaults, "environment_object_size_min_px", int(fallback["object_size_min_px"])),
            )
        ),
        "object_size_max_px": int(
            params.get(
                "object_size_max_px",
                group_default(render_defaults, "environment_object_size_max_px", int(fallback["object_size_max_px"])),
            )
        ),
        "min_gap_px": int(params.get("min_gap_px", group_default(render_defaults, "environment_min_gap_px", int(fallback["min_gap_px"])))),
        "max_overlap_fraction": float(
            params.get(
                "max_overlap_fraction",
                group_default(render_defaults, "environment_max_overlap_fraction", float(fallback["max_overlap_fraction"])),
            )
        ),
        "placement_max_attempts": int(
            params.get(
                "placement_max_attempts",
                group_default(render_defaults, "environment_placement_max_attempts", int(fallback["placement_max_attempts"])),
            )
        ),
        "render_scale": int(params.get("render_scale", group_default(render_defaults, "environment_render_scale", int(fallback["render_scale"])))),
        "skyline_building_min": int(params.get("skyline_building_min", group_default(render_defaults, "skyline_building_min", int(fallback.get("skyline_building_min", 7))))),
        "skyline_building_max": int(params.get("skyline_building_max", group_default(render_defaults, "skyline_building_max", int(fallback.get("skyline_building_max", 14))))),
    }


def environment_setting_name(theme_id: str) -> str:
    return ENVIRONMENT_SETTING_NAMES.get(str(theme_id), "an illustrated outdoor scene")


def theme_support(params: Mapping[str, Any], generation_defaults: Mapping[str, Any], *, fallback: Sequence[str] = ENVIRONMENT_THEME_IDS) -> tuple[str, ...]:
    raw = params.get("theme_support", group_default(generation_defaults, "theme_support", tuple(fallback)))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("theme_support must be a sequence")
    supported = tuple(str(value) for value in raw if str(value) in set(ENVIRONMENT_THEME_IDS))
    if not supported:
        raise ValueError("theme_support resolved no supported environment themes")
    return tuple(dict.fromkeys(supported))


def target_feature(scene: RenderedEnvironmentObjectScene, feature_type: str) -> EnvironmentFeature:
    matches = [feature for feature in scene.features if str(feature.feature_type) == str(feature_type)]
    if not matches:
        raise ValueError(f"rendered scene has no feature of type {feature_type}")
    return matches[0]


def serialize_environment_objects(scene: RenderedEnvironmentObjectScene) -> tuple[list[dict[str, Any]], Dict[str, list[float]], Dict[str, list[float]]]:
    serialized_objects = [serialize_rendered_illustration_object(obj) for obj in scene.objects]
    object_bboxes = {str(obj["object_id"]): list(obj["bbox"]) for obj in serialized_objects}
    part_bboxes = {
        str(part["part_id"]): list(part["bbox"])
        for obj in serialized_objects
        for part in obj["parts"]
    }
    return serialized_objects, object_bboxes, part_bboxes


def feature_bbox_map(scene: RenderedEnvironmentObjectScene) -> Dict[str, list[float]]:
    return {str(feature.feature_id): [round(float(v), 3) for v in feature.bbox_xyxy] for feature in scene.features}


def feature_path_map(scene: RenderedEnvironmentObjectScene) -> Dict[str, list[list[float]]]:
    return {
        str(feature.feature_id): [[round(float(x), 3), round(float(y), 3)] for x, y in feature.path_points]
        for feature in scene.features
    }


def sort_bboxes_by_ids(bbox_map: Mapping[str, Sequence[float]], ids: Sequence[str]) -> list[list[float]]:
    boxes = [(str(item_id), [round(float(v), 3) for v in bbox_map[str(item_id)]]) for item_id in ids]
    ordered = sorted(boxes, key=lambda item: (float(item[1][1]), float(item[1][0]), str(item[0])))
    return [box for _item_id, box in ordered]


def capped_object_count_probabilities(
    requested_probabilities: Mapping[str, float],
    theme_probabilities: Mapping[str, float],
) -> Dict[str, float]:
    normalized_theme_probabilities = {
        str(theme): max(0.0, float(probability))
        for theme, probability in theme_probabilities.items()
        if float(probability) > 0.0
    }
    if not normalized_theme_probabilities:
        normalized_theme_probabilities = {str(ENVIRONMENT_THEME_IDS[0]): 1.0}
    theme_total = sum(float(value) for value in normalized_theme_probabilities.values())
    capped: Dict[str, float] = {}
    for theme, theme_probability in normalized_theme_probabilities.items():
        theme_weight = float(theme_probability) / max(1e-9, float(theme_total))
        for requested_count, probability in requested_probabilities.items():
            actual_count = effective_environment_object_count(str(theme), int(requested_count))
            capped[str(actual_count)] = float(capped.get(str(actual_count), 0.0)) + float(theme_weight) * float(probability)
    return dict(sorted(capped.items(), key=lambda item: int(item[0])))


__all__ = [
    "ENVIRONMENT_SETTING_NAMES",
    "FEATURE_TYPES_BY_THEME",
    "capped_object_count_probabilities",
    "environment_render_params",
    "environment_scene_entities",
    "environment_setting_name",
    "feature_bbox_map",
    "feature_path_map",
    "serialize_environment_objects",
    "sort_bboxes_by_ids",
    "style_weights",
    "target_feature",
    "theme_support",
]
