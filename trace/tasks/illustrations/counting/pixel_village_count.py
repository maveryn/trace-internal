"""Counting tasks over top-down pixel village scenes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import hash64
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ..shared.pixel_village_rendering import PixelVillageEntity, PixelVillageScene, render_pixel_village_map
from ..shared.task_support import bounds, sample_count, uniform_string_probability_map


OBJECT_TYPE_COUNT_TASK_ID = "task_illustrations__pixel_village__object_type_count"
PERSON_PATH_COUNT_TASK_ID = "task_illustrations__pixel_village__person_path_count"
TERRITORY_OBJECT_COUNT_TASK_ID = "task_illustrations__pixel_village__territory_object_count"
BUILDING_NEAR_PATH_COUNT_TASK_ID = "task_illustrations__pixel_village__building_near_path_count"
SCENE_ID = "pixel_village"
OBJECT_TYPE_COUNT_QUERY_ID = "object_type_count"
PERSON_PATH_COUNT_QUERY_ID = "people_on_path_count"
TERRITORY_OBJECT_COUNT_QUERY_ID = "territory_object_count"
BUILDING_NEAR_PATH_COUNT_QUERY_ID = "building_near_path_count"

TARGET_OBJECT_KEYS: Tuple[str, ...] = (
    "building",
    "person",
    "tree",
    "crate",
    "lamp_post",
    "well",
    "pond",
)
TARGET_PUBLIC_NAME: Dict[str, str] = {
    "building": "building",
    "person": "person",
    "tree": "tree",
    "crate": "crate",
    "lamp_post": "lamp post",
    "well": "well",
    "pond": "pond",
}
TARGET_PROMPT_PLURAL: Dict[str, str] = {
    "building": "buildings",
    "person": "people",
    "tree": "trees",
    "crate": "crates",
    "lamp_post": "lamp posts",
    "well": "wells",
    "pond": "ponds",
}
TARGET_PROMPT_UNIT: Dict[str, str] = {
    "building": "building",
    "person": "person",
    "tree": "tree",
    "crate": "crate",
    "lamp_post": "lamp post",
    "well": "well",
    "pond": "pond",
}

TERRITORY_OBJECT_KEYS: Tuple[str, ...] = (
    "cemetery_grave_marker",
    "orchard_tree",
    "farm_plot_crop_row",
    "farm_plot_vegetable_patch",
)
TERRITORY_OBJECT_SPECS: Dict[str, Dict[str, str]] = {
    "cemetery_grave_marker": {
        "territory_id": "cemetery_0",
        "territory_type": "cemetery",
        "territory_name": "cemetery",
        "target_public_name": "grave marker",
        "target_plural": "grave markers",
        "target_unit": "grave marker",
        "force_mode_param": "cemetery_mode",
    },
    "orchard_tree": {
        "territory_id": "orchard_0",
        "territory_type": "orchard",
        "territory_name": "orchard",
        "target_public_name": "tree",
        "target_plural": "trees",
        "target_unit": "tree",
        "force_mode_param": "orchard_mode",
    },
    "farm_plot_crop_row": {
        "territory_id": "farm_plot_0",
        "territory_type": "farm_plot",
        "territory_name": "farm plot",
        "target_public_name": "crop row",
        "target_plural": "crop rows",
        "target_unit": "crop row",
        "force_mode_param": "farm_plot_mode",
    },
    "farm_plot_vegetable_patch": {
        "territory_id": "farm_plot_0",
        "territory_type": "farm_plot",
        "territory_name": "farm plot",
        "target_public_name": "vegetable patch",
        "target_plural": "vegetable patches",
        "target_unit": "vegetable patch",
        "force_mode_param": "farm_plot_mode",
    },
}


@dataclass(frozen=True)
class _Defaults:
    canvas_width: int = 960
    canvas_height: int = 720
    tile_px: int = 32
    theme_mode: str = "temperate"
    cemetery_mode: str = "auto"
    orchard_mode: str = "auto"
    farm_plot_mode: str = "auto"
    windmill_mode: str = "auto"
    path_person_count_min: int = 2
    path_person_count_max: int = 6
    background_person_path_clearance: int = 1
    object_answer_count_max: int = 8
    territory_object_answer_count_max: int = 8
    building_near_path_distance: int = 1
    building_near_path_answer_count_max: int = 8
    annotation_padding_px: float = 0.0


@dataclass(frozen=True)
class _ObjectTypeSample:
    target_object: str
    target_plural: str
    target_unit: str
    target_public_name: str
    target_object_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _PathPeopleSample:
    path_person_count: int
    path_person_count_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _TerritoryObjectSample:
    target_key: str
    territory_id: str
    territory_type: str
    territory_name: str
    target_public_name: str
    target_plural: str
    target_unit: str
    force_mode_param: str
    target_probabilities: Dict[str, float]


_DEFAULTS = _Defaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("illustrations", "counting")

_OBJECT_GEN_DEFAULTS, _OBJECT_RENDER_DEFAULTS, _OBJECT_PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=OBJECT_TYPE_COUNT_TASK_ID,
)
_PATH_GEN_DEFAULTS, _PATH_RENDER_DEFAULTS, _PATH_PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=PERSON_PATH_COUNT_TASK_ID,
)
_TERRITORY_GEN_DEFAULTS, _TERRITORY_RENDER_DEFAULTS, _TERRITORY_PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TERRITORY_OBJECT_COUNT_TASK_ID,
)
_BUILDING_NEAR_PATH_GEN_DEFAULTS, _BUILDING_NEAR_PATH_RENDER_DEFAULTS, _BUILDING_NEAR_PATH_PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=BUILDING_NEAR_PATH_COUNT_TASK_ID,
)


def _normalize_target_key(value: Any) -> str:
    text = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    if text == "lamp":
        text = "lamp_post"
    if text == "people":
        text = "person"
    if text.endswith("s") and text[:-1] in TARGET_OBJECT_KEYS:
        text = text[:-1]
    return str(text)


def _normalize_territory_object_key(value: Any) -> str:
    text = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "cemetery": "cemetery_grave_marker",
        "grave_marker": "cemetery_grave_marker",
        "grave_markers": "cemetery_grave_marker",
        "orchard": "orchard_tree",
        "orchard_trees": "orchard_tree",
        "trees_in_orchard": "orchard_tree",
        "farm_crop_row": "farm_plot_crop_row",
        "crop_row": "farm_plot_crop_row",
        "crop_rows": "farm_plot_crop_row",
        "farm_vegetable_patch": "farm_plot_vegetable_patch",
        "vegetable_patch": "farm_plot_vegetable_patch",
        "vegetable_patches": "farm_plot_vegetable_patch",
    }
    return aliases.get(text, text)


def _target_support(params: Mapping[str, Any], defaults: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get("target_object_support", group_default(defaults, "target_object_support", TARGET_OBJECT_KEYS))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("target_object_support must be a sequence")
    support = tuple(dict.fromkeys(_normalize_target_key(value) for value in raw))
    invalid = [value for value in support if value not in set(TARGET_OBJECT_KEYS)]
    if invalid:
        raise ValueError(f"unsupported pixel village target objects: {invalid}")
    if not support:
        raise ValueError("target_object_support must contain at least one supported target")
    return support


def _territory_object_support(params: Mapping[str, Any], defaults: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get(
        "territory_object_support",
        group_default(defaults, "territory_object_support", TERRITORY_OBJECT_KEYS),
    )
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("territory_object_support must be a sequence")
    support = tuple(dict.fromkeys(_normalize_territory_object_key(value) for value in raw))
    invalid = [value for value in support if value not in set(TERRITORY_OBJECT_KEYS)]
    if invalid:
        raise ValueError(f"unsupported pixel village territory-object targets: {invalid}")
    if not support:
        raise ValueError("territory_object_support must contain at least one supported target")
    return support


def _resolve_target_object(
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
) -> tuple[str, Dict[str, float]]:
    support = _target_support(params, defaults)
    explicit = params.get("target_object")
    if explicit is None:
        explicit = params.get("target_public_name")
    if explicit is not None:
        target = _normalize_target_key(explicit)
        if target not in set(support):
            raise ValueError("target_object is outside configured support")
        return str(target), uniform_string_probability_map(support, selected=str(target))
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{task_id}:target_object")
    return str(support[int(index) % len(support)]), uniform_string_probability_map(support)


def _resolve_territory_object(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
) -> tuple[str, Dict[str, float]]:
    support = _territory_object_support(params, defaults)
    explicit = params.get("territory_object")
    if explicit is None:
        explicit = params.get("target_territory_object")
    if explicit is not None:
        target = _normalize_territory_object_key(explicit)
        if target not in set(support):
            raise ValueError("territory_object is outside configured support")
        return str(target), uniform_string_probability_map(support, selected=str(target))
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TERRITORY_OBJECT_COUNT_TASK_ID}:territory_object",
    )
    return str(support[int(index) % len(support)]), uniform_string_probability_map(support)


def _validate_query_id(params: Mapping[str, Any], expected: str) -> None:
    explicit = params.get("query_id")
    if explicit is not None and str(explicit) != str(expected):
        raise ValueError(f"query_id must be {expected!r}")


def _scene_seed(task_id: str, instance_seed: int, attempt_index: int) -> int:
    if int(attempt_index) == 0:
        return int(instance_seed)
    return int(hash64(int(instance_seed), f"{task_id}:scene_attempt", int(attempt_index)))


def _render_scene(
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    attempt_index: int,
    path_person_count: int = 0,
    background_person_path_clearance: int = 0,
) -> PixelVillageScene:
    return render_pixel_village_map(
        _scene_seed(str(task_id), int(instance_seed), int(attempt_index)),
        width=int(params.get("canvas_width", group_default(render_defaults, "pixel_village_canvas_width", _DEFAULTS.canvas_width))),
        height=int(params.get("canvas_height", group_default(render_defaults, "pixel_village_canvas_height", _DEFAULTS.canvas_height))),
        tile_px=int(params.get("tile_px", group_default(render_defaults, "pixel_village_tile_px", _DEFAULTS.tile_px))),
        grid_cols=params.get("grid_cols", group_default(render_defaults, "pixel_village_grid_cols", None)),
        grid_rows=params.get("grid_rows", group_default(render_defaults, "pixel_village_grid_rows", None)),
        cemetery_mode=str(params.get("cemetery_mode", group_default(render_defaults, "pixel_village_cemetery_mode", _DEFAULTS.cemetery_mode))),
        orchard_mode=str(params.get("orchard_mode", group_default(render_defaults, "pixel_village_orchard_mode", _DEFAULTS.orchard_mode))),
        farm_plot_mode=str(params.get("farm_plot_mode", group_default(render_defaults, "pixel_village_farm_plot_mode", _DEFAULTS.farm_plot_mode))),
        windmill_mode=str(params.get("windmill_mode", group_default(render_defaults, "pixel_village_windmill_mode", _DEFAULTS.windmill_mode))),
        theme_mode=str(params.get("theme_mode", group_default(render_defaults, "pixel_village_theme_mode", _DEFAULTS.theme_mode))),
        path_person_count=int(path_person_count),
        background_person_path_clearance=int(background_person_path_clearance),
    )


def _bbox(entity: PixelVillageEntity, *, pad: float = 0.0, image_size: tuple[int, int]) -> list[float]:
    x0, y0, x1, y1 = entity.bbox_xyxy
    width, height = image_size
    p = max(0.0, float(pad))
    return [
        round(max(0.0, float(x0) - p), 3),
        round(max(0.0, float(y0) - p), 3),
        round(min(float(width), float(x1) + p), 3),
        round(min(float(height), float(y1) + p), 3),
    ]


def _entity_bbox_map(scene: PixelVillageScene, *, pad: float = 0.0) -> Dict[str, list[float]]:
    return {
        str(entity.entity_id): _bbox(entity, pad=float(pad), image_size=scene.image.size)
        for entity in scene.entities
    }


def _entity_footprint(entity: PixelVillageEntity) -> set[tuple[int, int]]:
    x, y, w, h = entity.tile_xywh
    return {
        (int(xx), int(yy))
        for xx in range(int(x), int(x) + int(w))
        for yy in range(int(y), int(y) + int(h))
    }


def _counted_object_entities(scene: PixelVillageScene, target_object: str) -> Tuple[PixelVillageEntity, ...]:
    target = str(target_object)
    public_name = TARGET_PUBLIC_NAME[target]
    if target == "building":
        return tuple(entity for entity in scene.entities if str(entity.category) == "building")
    if target == "person":
        return tuple(entity for entity in scene.entities if str(entity.category) == "person")
    return tuple(entity for entity in scene.entities if str(entity.public_name) == str(public_name))


def _path_people(scene: PixelVillageScene) -> Tuple[PixelVillageEntity, ...]:
    path_tiles = {tuple(int(v) for v in tile) for tile in scene.trace.get("path_tiles", [])}
    return tuple(
        entity
        for entity in scene.entities
        if str(entity.category) == "person" and bool(_entity_footprint(entity) & path_tiles)
    )


def _territory_object_entities(scene: PixelVillageScene, sample: _TerritoryObjectSample) -> Tuple[PixelVillageEntity, ...]:
    return tuple(
        entity
        for entity in scene.entities
        if str(entity.public_name) == str(sample.target_public_name)
        and str(entity.metadata.get("territory_id", "")) == str(sample.territory_id)
    )


def _entity_near_any_tile(
    entity: PixelVillageEntity,
    tiles: set[tuple[int, int]],
    *,
    distance: int,
) -> bool:
    radius = max(0, int(distance))
    x, y, w, h = entity.tile_xywh
    for tx, ty in tiles:
        nearest_x = min(max(int(tx), int(x)), int(x) + int(w) - 1)
        nearest_y = min(max(int(ty), int(y)), int(y) + int(h) - 1)
        if max(abs(int(tx) - nearest_x), abs(int(ty) - nearest_y)) <= radius:
            return True
    return False


def _buildings_near_path(scene: PixelVillageScene, *, distance: int) -> Tuple[PixelVillageEntity, ...]:
    path_tiles = {tuple(int(v) for v in tile) for tile in scene.trace.get("path_tiles", [])}
    return tuple(
        entity
        for entity in scene.entities
        if str(entity.category) == "building" and _entity_near_any_tile(entity, path_tiles, distance=int(distance))
    )


def _scene_entities(scene: PixelVillageScene) -> list[dict[str, Any]]:
    return [entity.as_dict() for entity in scene.entities]


def _scene_territories(scene: PixelVillageScene) -> list[dict[str, Any]]:
    return [territory.as_dict() for territory in scene.territories]


def _render_metadata(scene: PixelVillageScene) -> dict[str, Any]:
    return {
        "renderer_id": str(scene.trace.get("renderer_id", "")),
        "theme_mode": str(scene.trace.get("theme_mode", "")),
        "theme_id": str(scene.trace.get("theme_id", "")),
        "grid_cols": int(scene.trace.get("grid_cols", 0)),
        "grid_rows": int(scene.trace.get("grid_rows", 0)),
        "tile_px": int(scene.trace.get("tile_px", 0)),
        "map_offset_xy": list(scene.trace.get("map_offset_xy", [])),
        "map_size_px": list(scene.trace.get("map_size_px", [])),
        "cemetery_present": bool(scene.trace.get("cemetery_present", False)),
        "orchard_present": bool(scene.trace.get("orchard_present", False)),
        "farm_plot_present": bool(scene.trace.get("farm_plot_present", False)),
        "windmill_present": bool(scene.trace.get("windmill_present", False)),
    }


def _build_object_sample(*, instance_seed: int, params: Mapping[str, Any]) -> _ObjectTypeSample:
    target_object, target_probs = _resolve_target_object(
        task_id=OBJECT_TYPE_COUNT_TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        defaults=_OBJECT_GEN_DEFAULTS,
    )
    return _ObjectTypeSample(
        target_object=str(target_object),
        target_plural=str(TARGET_PROMPT_PLURAL[str(target_object)]),
        target_unit=str(TARGET_PROMPT_UNIT[str(target_object)]),
        target_public_name=str(TARGET_PUBLIC_NAME[str(target_object)]),
        target_object_probabilities=dict(target_probs),
    )


def _build_path_sample(*, instance_seed: int, params: Mapping[str, Any]) -> _PathPeopleSample:
    count_min, count_max = bounds(
        params,
        _PATH_GEN_DEFAULTS,
        "path_person_count_min",
        "path_person_count_max",
        _DEFAULTS.path_person_count_min,
        _DEFAULTS.path_person_count_max,
    )
    count, probabilities = sample_count(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{PERSON_PATH_COUNT_TASK_ID}:path_person_count",
        low=int(count_min),
        high=int(count_max),
        explicit_key="path_person_count",
    )
    return _PathPeopleSample(
        path_person_count=int(count),
        path_person_count_probabilities=dict(probabilities),
    )


def _build_territory_object_sample(*, instance_seed: int, params: Mapping[str, Any]) -> _TerritoryObjectSample:
    target_key, probabilities = _resolve_territory_object(
        instance_seed=int(instance_seed),
        params=params,
        defaults=_TERRITORY_GEN_DEFAULTS,
    )
    spec = TERRITORY_OBJECT_SPECS[str(target_key)]
    return _TerritoryObjectSample(
        target_key=str(target_key),
        territory_id=str(spec["territory_id"]),
        territory_type=str(spec["territory_type"]),
        territory_name=str(spec["territory_name"]),
        target_public_name=str(spec["target_public_name"]),
        target_plural=str(spec["target_plural"]),
        target_unit=str(spec["target_unit"]),
        force_mode_param=str(spec["force_mode_param"]),
        target_probabilities=dict(probabilities),
    )


def _object_complexity(*, scene: PixelVillageScene, answer: int) -> TaskComplexity:
    visual_scan = min(1.0, max(0.0, (int(scene.trace.get("entity_count", 0)) - 35) / 70.0))
    answer_load = min(1.0, max(0.0, (int(answer) - 1) / 18.0))
    scene_variety = min(1.0, 0.2 + 0.2 * sum(bool(scene.trace.get(key, False)) for key in ("cemetery_present", "orchard_present", "farm_plot_present", "windmill_present")))
    score = 0.45 * visual_scan + 0.35 * answer_load + 0.20 * scene_variety
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={
            "visual_scan": round(float(visual_scan), 6),
            "answer_load": round(float(answer_load), 6),
            "scene_variety": round(float(scene_variety), 6),
        },
    )


def _path_complexity(*, scene: PixelVillageScene, answer: int) -> TaskComplexity:
    people_count = int(scene.trace.get("category_counts", {}).get("person", 0)) if isinstance(scene.trace.get("category_counts"), Mapping) else 0
    visual_scan = min(1.0, max(0.0, (int(scene.trace.get("entity_count", 0)) - 35) / 70.0))
    person_scan = min(1.0, max(0.0, (people_count - 7) / 8.0))
    answer_load = min(1.0, max(0.0, (int(answer) - _DEFAULTS.path_person_count_min) / max(1, _DEFAULTS.path_person_count_max - _DEFAULTS.path_person_count_min)))
    score = 0.35 * visual_scan + 0.35 * person_scan + 0.30 * answer_load
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={
            "visual_scan": round(float(visual_scan), 6),
            "person_scan": round(float(person_scan), 6),
            "answer_load": round(float(answer_load), 6),
        },
    )


def _territory_complexity(*, scene: PixelVillageScene, answer: int) -> TaskComplexity:
    visual_scan = min(1.0, max(0.0, (int(scene.trace.get("entity_count", 0)) - 30) / 65.0))
    answer_load = min(1.0, max(0.0, (int(answer) - 2) / 6.0))
    territory_load = min(1.0, 0.25 + 0.18 * int(scene.trace.get("territory_count", 0)))
    score = 0.40 * visual_scan + 0.35 * answer_load + 0.25 * territory_load
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={
            "visual_scan": round(float(visual_scan), 6),
            "answer_load": round(float(answer_load), 6),
            "territory_load": round(float(territory_load), 6),
        },
    )


def _building_path_complexity(*, scene: PixelVillageScene, answer: int) -> TaskComplexity:
    building_count = int(scene.trace.get("category_counts", {}).get("building", 0)) if isinstance(scene.trace.get("category_counts"), Mapping) else 0
    visual_scan = min(1.0, max(0.0, (int(scene.trace.get("entity_count", 0)) - 30) / 65.0))
    building_scan = min(1.0, max(0.0, (building_count - 3) / 5.0))
    answer_load = min(1.0, max(0.0, (int(answer) - 1) / 7.0))
    score = 0.35 * visual_scan + 0.35 * building_scan + 0.30 * answer_load
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={
            "visual_scan": round(float(visual_scan), 6),
            "building_scan": round(float(building_scan), 6),
            "answer_load": round(float(answer_load), 6),
        },
    )


@register_task
class IllustrationsPixelVillageObjectTypeCountTask:
    """Count approved public object categories in a top-down pixel village."""

    task_id = OBJECT_TYPE_COUNT_TASK_ID
    domain = "illustrations"
    task_group = "counting"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        _validate_query_id(params, OBJECT_TYPE_COUNT_QUERY_ID)
        last_error: Exception | None = None
        sample = _build_object_sample(instance_seed=int(instance_seed), params=params)
        answer_count_max = int(
            params.get(
                "target_answer_count_max",
                group_default(_OBJECT_GEN_DEFAULTS, "target_answer_count_max", _DEFAULTS.object_answer_count_max),
            )
        )
        scene: PixelVillageScene | None = None
        counted_entities: Tuple[PixelVillageEntity, ...] = ()
        for attempt in range(max(1, int(max_attempts))):
            try:
                scene_params: Mapping[str, Any] = params
                if sample.target_object == "tree":
                    scene_params = {**params, "cemetery_mode": "none"}
                scene = _render_scene(
                    task_id=self.task_id,
                    instance_seed=int(instance_seed),
                    params=scene_params,
                    render_defaults=_OBJECT_RENDER_DEFAULTS,
                    attempt_index=int(attempt),
                    path_person_count=0,
                )
                counted_entities = _counted_object_entities(scene, sample.target_object)
                answer_count = len(counted_entities)
                if 0 < answer_count <= answer_count_max:
                    break
                last_error = RuntimeError(
                    f"sampled target object count {answer_count} is outside allowed range 1..{answer_count_max}"
                )
                scene = None
            except Exception as exc:  # pragma: no cover
                last_error = exc
                scene = None
        if scene is None:
            raise RuntimeError(f"could not generate {self.task_id}: {last_error}") from last_error

        pad = float(params.get("annotation_padding_px", group_default(_OBJECT_RENDER_DEFAULTS, "annotation_padding_px", _DEFAULTS.annotation_padding_px)))
        entity_bboxes = _entity_bbox_map(scene, pad=pad)
        counted_entity_ids = tuple(sorted(str(entity.entity_id) for entity in counted_entities))
        annotation_value = [entity_bboxes[entity_id] for entity_id in counted_entity_ids]
        answer = int(len(counted_entity_ids))

        prompt_defaults = required_group_defaults(
            _OBJECT_PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_pixel_village_object_type",
                "annotation_hint_pixel_village_object_type",
                "json_example_pixel_village_object_type",
                "json_example_answer_only_pixel_village_object_type",
            ],
            context=f"prompt defaults for {self.task_id}",
        )
        slots = {
            "target_plural": str(sample.target_plural),
            "target_unit": str(sample.target_unit),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults["answer_hint_pixel_village_object_type"]).format(target_plural=str(sample.target_plural)),
            "annotation_hint": str(prompt_defaults["annotation_hint_pixel_village_object_type"]).format(target_unit=str(sample.target_unit)),
            "json_example": str(prompt_defaults["json_example_pixel_village_object_type"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only_pixel_village_object_type"]),
        }
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=OBJECT_TYPE_COUNT_QUERY_ID,
            slots=slots,
            instance_seed=int(instance_seed),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            preferred_mode="answer_and_annotation",
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        trace_payload = {
            "scene_ir": {
                "domain": self.domain,
                "scene_id": SCENE_ID,
                "entities": _scene_entities(scene),
                "territories": _scene_territories(scene),
                "relations": {
                    "query_id": OBJECT_TYPE_COUNT_QUERY_ID,
                    "target_object": str(sample.target_object),
                    "target_public_name": str(sample.target_public_name),
                },
            },
            "query_spec": {
                "task_id": self.task_id,
                "query_id": OBJECT_TYPE_COUNT_QUERY_ID,
                "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "target_object": str(sample.target_object),
                    "target_plural": str(sample.target_plural),
                    "target_public_name": str(sample.target_public_name),
                    "target_count": int(answer),
                    "target_answer_count_max": int(answer_count_max),
                    "render_constraints": {
                        "cemetery_mode": "none" if sample.target_object == "tree" else "task_default",
                    },
                    "target_object_probabilities": dict(sample.target_object_probabilities),
                    "renderer": _render_metadata(scene),
                },
            },
            "render_spec": {
                "canvas_size": [int(scene.image.size[0]), int(scene.image.size[1])],
                "coord_space": "pixel",
                "scene_id": SCENE_ID,
                "style": {
                    "renderer_id": str(scene.trace.get("renderer_id", "")),
                    "style_id": "top_down_pixel_rpg",
                    "theme_id": str(scene.trace.get("theme_id", "")),
                    "tile_px": int(scene.trace.get("tile_px", 0)),
                    "grid_cols": int(scene.trace.get("grid_cols", 0)),
                    "grid_rows": int(scene.trace.get("grid_rows", 0)),
                },
            },
            "render_map": {
                "image_id": "img0",
                "entity_bboxes_px": dict(entity_bboxes),
                "path_tiles": list(scene.trace.get("path_tiles", [])),
                "counted_entity_ids": list(counted_entity_ids),
            },
            "execution_trace": {
                "query_id": OBJECT_TYPE_COUNT_QUERY_ID,
                "scene_id": SCENE_ID,
                "target_object": str(sample.target_object),
                "target_public_name": str(sample.target_public_name),
                "answer": int(answer),
                "counted_entity_ids": list(counted_entity_ids),
                "category_counts": dict(scene.trace.get("category_counts", {})),
                "public_name_counts": dict(scene.trace.get("public_name_counts", {})),
                "renderer": _render_metadata(scene),
            },
            "witness_symbolic": {
                "counted_entity_ids": list(counted_entity_ids),
                "target_object": str(sample.target_object),
                "count": int(answer),
                "answer": int(answer),
            },
            "projected_annotation": {"bbox_set": list(annotation_value)},
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
            answer_gt=TypedValue(type="integer", value=int(answer)),
            annotation_gt=TypedValue(type="bbox_set", value=list(annotation_value)),
            image=scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_object_complexity(scene=scene, answer=answer),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=OBJECT_TYPE_COUNT_QUERY_ID,
        )


@register_task
class IllustrationsPixelVillagePersonPathCountTask:
    """Count people placed directly on path tiles in a top-down pixel village."""

    task_id = PERSON_PATH_COUNT_TASK_ID
    domain = "illustrations"
    task_group = "counting"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        _validate_query_id(params, PERSON_PATH_COUNT_QUERY_ID)
        last_error: Exception | None = None
        sample = _build_path_sample(instance_seed=int(instance_seed), params=params)
        scene: PixelVillageScene | None = None
        counted_entities: Tuple[PixelVillageEntity, ...] = ()
        for attempt in range(max(1, int(max_attempts))):
            try:
                scene = _render_scene(
                    task_id=self.task_id,
                    instance_seed=int(instance_seed),
                    params=params,
                    render_defaults=_PATH_RENDER_DEFAULTS,
                    attempt_index=int(attempt),
                    path_person_count=int(sample.path_person_count),
                    background_person_path_clearance=int(
                        params.get(
                            "background_person_path_clearance",
                            group_default(
                                _PATH_RENDER_DEFAULTS,
                                "background_person_path_clearance",
                                _DEFAULTS.background_person_path_clearance,
                            ),
                        )
                    ),
                )
                counted_entities = _path_people(scene)
                if len(counted_entities) == int(sample.path_person_count):
                    break
                last_error = RuntimeError("rendered path-person count did not match requested count")
                scene = None
            except Exception as exc:  # pragma: no cover
                last_error = exc
                scene = None
        if scene is None:
            raise RuntimeError(f"could not generate {self.task_id}: {last_error}") from last_error

        pad = float(params.get("annotation_padding_px", group_default(_PATH_RENDER_DEFAULTS, "annotation_padding_px", _DEFAULTS.annotation_padding_px)))
        entity_bboxes = _entity_bbox_map(scene, pad=pad)
        counted_entity_ids = tuple(sorted(str(entity.entity_id) for entity in counted_entities))
        annotation_value = [entity_bboxes[entity_id] for entity_id in counted_entity_ids]
        answer = int(len(counted_entity_ids))

        prompt_defaults = required_group_defaults(
            _PATH_PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_pixel_village_person_path",
                "annotation_hint_pixel_village_person_path",
                "json_example_pixel_village_person_path",
                "json_example_answer_only_pixel_village_person_path",
            ],
            context=f"prompt defaults for {self.task_id}",
        )
        slots = {
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults["answer_hint_pixel_village_person_path"]),
            "annotation_hint": str(prompt_defaults["annotation_hint_pixel_village_person_path"]),
            "json_example": str(prompt_defaults["json_example_pixel_village_person_path"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only_pixel_village_person_path"]),
        }
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=PERSON_PATH_COUNT_QUERY_ID,
            slots=slots,
            instance_seed=int(instance_seed),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            preferred_mode="answer_and_annotation",
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        trace_payload = {
            "scene_ir": {
                "domain": self.domain,
                "scene_id": SCENE_ID,
                "entities": _scene_entities(scene),
                "territories": _scene_territories(scene),
                "relations": {
                    "query_id": PERSON_PATH_COUNT_QUERY_ID,
                    "path_membership_rule": "person tile footprint intersects a path tile",
                },
            },
            "query_spec": {
                "task_id": self.task_id,
                "query_id": PERSON_PATH_COUNT_QUERY_ID,
                "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "path_person_count": int(sample.path_person_count),
                    "path_person_count_probabilities": dict(sample.path_person_count_probabilities),
                    "renderer": _render_metadata(scene),
                },
            },
            "render_spec": {
                "canvas_size": [int(scene.image.size[0]), int(scene.image.size[1])],
                "coord_space": "pixel",
                "scene_id": SCENE_ID,
                "style": {
                    "renderer_id": str(scene.trace.get("renderer_id", "")),
                    "style_id": "top_down_pixel_rpg",
                    "theme_id": str(scene.trace.get("theme_id", "")),
                    "tile_px": int(scene.trace.get("tile_px", 0)),
                    "grid_cols": int(scene.trace.get("grid_cols", 0)),
                    "grid_rows": int(scene.trace.get("grid_rows", 0)),
                },
            },
            "render_map": {
                "image_id": "img0",
                "entity_bboxes_px": dict(entity_bboxes),
                "path_tiles": list(scene.trace.get("path_tiles", [])),
                "counted_entity_ids": list(counted_entity_ids),
            },
            "execution_trace": {
                "query_id": PERSON_PATH_COUNT_QUERY_ID,
                "scene_id": SCENE_ID,
                "answer": int(answer),
                "counted_entity_ids": list(counted_entity_ids),
                "path_tiles": list(scene.trace.get("path_tiles", [])),
                "path_person_requested_count": int(scene.trace.get("path_person_requested_count", 0)),
                "path_person_placed_count": int(scene.trace.get("path_person_placed_count", 0)),
                "background_person_path_clearance": int(scene.trace.get("background_person_path_clearance", 0)),
                "category_counts": dict(scene.trace.get("category_counts", {})),
                "public_name_counts": dict(scene.trace.get("public_name_counts", {})),
                "renderer": _render_metadata(scene),
            },
            "witness_symbolic": {
                "counted_entity_ids": list(counted_entity_ids),
                "path_membership_rule": "tile_footprint_intersects_path_tile",
                "count": int(answer),
                "answer": int(answer),
            },
            "projected_annotation": {"bbox_set": list(annotation_value)},
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
            answer_gt=TypedValue(type="integer", value=int(answer)),
            annotation_gt=TypedValue(type="bbox_set", value=list(annotation_value)),
            image=scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_path_complexity(scene=scene, answer=answer),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=PERSON_PATH_COUNT_QUERY_ID,
        )


@register_task
class IllustrationsPixelVillageTerritoryObjectCountTask:
    """Count target objects inside a named pixel-village territory."""

    task_id = TERRITORY_OBJECT_COUNT_TASK_ID
    domain = "illustrations"
    task_group = "counting"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        _validate_query_id(params, TERRITORY_OBJECT_COUNT_QUERY_ID)
        last_error: Exception | None = None
        sample = _build_territory_object_sample(instance_seed=int(instance_seed), params=params)
        answer_count_max = int(
            params.get(
                "target_answer_count_max",
                group_default(
                    _TERRITORY_GEN_DEFAULTS,
                    "target_answer_count_max",
                    _DEFAULTS.territory_object_answer_count_max,
                ),
            )
        )
        scene: PixelVillageScene | None = None
        counted_entities: Tuple[PixelVillageEntity, ...] = ()
        for attempt in range(max(1, int(max_attempts))):
            try:
                scene_params: Mapping[str, Any] = {**params, sample.force_mode_param: "force"}
                scene = _render_scene(
                    task_id=self.task_id,
                    instance_seed=int(instance_seed),
                    params=scene_params,
                    render_defaults=_TERRITORY_RENDER_DEFAULTS,
                    attempt_index=int(attempt),
                    path_person_count=0,
                )
                counted_entities = _territory_object_entities(scene, sample)
                answer_count = len(counted_entities)
                if 0 < answer_count <= answer_count_max:
                    break
                last_error = RuntimeError(
                    f"territory-object count {answer_count} is outside allowed range 1..{answer_count_max}"
                )
                scene = None
            except Exception as exc:  # pragma: no cover
                last_error = exc
                scene = None
        if scene is None:
            raise RuntimeError(f"could not generate {self.task_id}: {last_error}") from last_error

        pad = float(
            params.get(
                "annotation_padding_px",
                group_default(_TERRITORY_RENDER_DEFAULTS, "annotation_padding_px", _DEFAULTS.annotation_padding_px),
            )
        )
        entity_bboxes = _entity_bbox_map(scene, pad=pad)
        counted_entity_ids = tuple(sorted(str(entity.entity_id) for entity in counted_entities))
        annotation_value = [entity_bboxes[entity_id] for entity_id in counted_entity_ids]
        answer = int(len(counted_entity_ids))

        prompt_defaults = required_group_defaults(
            _TERRITORY_PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_pixel_village_territory_object",
                "annotation_hint_pixel_village_territory_object",
                "json_example_pixel_village_territory_object",
                "json_example_answer_only_pixel_village_territory_object",
            ],
            context=f"prompt defaults for {self.task_id}",
        )
        slots = {
            "territory_name": str(sample.territory_name),
            "target_plural": str(sample.target_plural),
            "target_unit": str(sample.target_unit),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults["answer_hint_pixel_village_territory_object"]).format(
                target_plural=str(sample.target_plural),
                territory_name=str(sample.territory_name),
            ),
            "annotation_hint": str(prompt_defaults["annotation_hint_pixel_village_territory_object"]).format(
                target_unit=str(sample.target_unit),
                territory_name=str(sample.territory_name),
            ),
            "json_example": str(prompt_defaults["json_example_pixel_village_territory_object"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only_pixel_village_territory_object"]),
        }
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=TERRITORY_OBJECT_COUNT_QUERY_ID,
            slots=slots,
            instance_seed=int(instance_seed),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            preferred_mode="answer_and_annotation",
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        trace_payload = {
            "scene_ir": {
                "domain": self.domain,
                "scene_id": SCENE_ID,
                "entities": _scene_entities(scene),
                "territories": _scene_territories(scene),
                "relations": {
                    "query_id": TERRITORY_OBJECT_COUNT_QUERY_ID,
                    "territory_id": str(sample.territory_id),
                    "territory_type": str(sample.territory_type),
                    "target_public_name": str(sample.target_public_name),
                },
            },
            "query_spec": {
                "task_id": self.task_id,
                "query_id": TERRITORY_OBJECT_COUNT_QUERY_ID,
                "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "territory_object": str(sample.target_key),
                    "territory_id": str(sample.territory_id),
                    "territory_type": str(sample.territory_type),
                    "territory_name": str(sample.territory_name),
                    "target_public_name": str(sample.target_public_name),
                    "target_count": int(answer),
                    "target_answer_count_max": int(answer_count_max),
                    "render_constraints": {str(sample.force_mode_param): "force"},
                    "territory_object_probabilities": dict(sample.target_probabilities),
                    "renderer": _render_metadata(scene),
                },
            },
            "render_spec": {
                "canvas_size": [int(scene.image.size[0]), int(scene.image.size[1])],
                "coord_space": "pixel",
                "scene_id": SCENE_ID,
                "style": {
                    "renderer_id": str(scene.trace.get("renderer_id", "")),
                    "style_id": "top_down_pixel_rpg",
                    "theme_id": str(scene.trace.get("theme_id", "")),
                    "tile_px": int(scene.trace.get("tile_px", 0)),
                    "grid_cols": int(scene.trace.get("grid_cols", 0)),
                    "grid_rows": int(scene.trace.get("grid_rows", 0)),
                },
            },
            "render_map": {
                "image_id": "img0",
                "entity_bboxes_px": dict(entity_bboxes),
                "counted_entity_ids": list(counted_entity_ids),
            },
            "execution_trace": {
                "query_id": TERRITORY_OBJECT_COUNT_QUERY_ID,
                "scene_id": SCENE_ID,
                "territory_object": str(sample.target_key),
                "territory_id": str(sample.territory_id),
                "territory_type": str(sample.territory_type),
                "target_public_name": str(sample.target_public_name),
                "answer": int(answer),
                "counted_entity_ids": list(counted_entity_ids),
                "category_counts": dict(scene.trace.get("category_counts", {})),
                "public_name_counts": dict(scene.trace.get("public_name_counts", {})),
                "renderer": _render_metadata(scene),
            },
            "witness_symbolic": {
                "counted_entity_ids": list(counted_entity_ids),
                "territory_id": str(sample.territory_id),
                "target_public_name": str(sample.target_public_name),
                "count": int(answer),
                "answer": int(answer),
            },
            "projected_annotation": {"bbox_set": list(annotation_value)},
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
            answer_gt=TypedValue(type="integer", value=int(answer)),
            annotation_gt=TypedValue(type="bbox_set", value=list(annotation_value)),
            image=scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_territory_complexity(scene=scene, answer=answer),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=TERRITORY_OBJECT_COUNT_QUERY_ID,
        )


@register_task
class IllustrationsPixelVillageBuildingNearPathCountTask:
    """Count buildings within a configured tile distance of any path tile."""

    task_id = BUILDING_NEAR_PATH_COUNT_TASK_ID
    domain = "illustrations"
    task_group = "counting"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        _validate_query_id(params, BUILDING_NEAR_PATH_COUNT_QUERY_ID)
        last_error: Exception | None = None
        distance = int(
            params.get(
                "near_path_tile_distance",
                group_default(
                    _BUILDING_NEAR_PATH_GEN_DEFAULTS,
                    "near_path_tile_distance",
                    _DEFAULTS.building_near_path_distance,
                ),
            )
        )
        answer_count_max = int(
            params.get(
                "target_answer_count_max",
                group_default(
                    _BUILDING_NEAR_PATH_GEN_DEFAULTS,
                    "target_answer_count_max",
                    _DEFAULTS.building_near_path_answer_count_max,
                ),
            )
        )
        scene: PixelVillageScene | None = None
        counted_entities: Tuple[PixelVillageEntity, ...] = ()
        for attempt in range(max(1, int(max_attempts))):
            try:
                scene = _render_scene(
                    task_id=self.task_id,
                    instance_seed=int(instance_seed),
                    params=params,
                    render_defaults=_BUILDING_NEAR_PATH_RENDER_DEFAULTS,
                    attempt_index=int(attempt),
                    path_person_count=0,
                )
                counted_entities = _buildings_near_path(scene, distance=distance)
                answer_count = len(counted_entities)
                if 0 < answer_count <= answer_count_max:
                    break
                last_error = RuntimeError(
                    f"building-near-path count {answer_count} is outside allowed range 1..{answer_count_max}"
                )
                scene = None
            except Exception as exc:  # pragma: no cover
                last_error = exc
                scene = None
        if scene is None:
            raise RuntimeError(f"could not generate {self.task_id}: {last_error}") from last_error

        pad = float(
            params.get(
                "annotation_padding_px",
                group_default(_BUILDING_NEAR_PATH_RENDER_DEFAULTS, "annotation_padding_px", _DEFAULTS.annotation_padding_px),
            )
        )
        entity_bboxes = _entity_bbox_map(scene, pad=pad)
        counted_entity_ids = tuple(sorted(str(entity.entity_id) for entity in counted_entities))
        annotation_value = [entity_bboxes[entity_id] for entity_id in counted_entity_ids]
        answer = int(len(counted_entity_ids))

        prompt_defaults = required_group_defaults(
            _BUILDING_NEAR_PATH_PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_pixel_village_building_near_path",
                "annotation_hint_pixel_village_building_near_path",
                "json_example_pixel_village_building_near_path",
                "json_example_answer_only_pixel_village_building_near_path",
            ],
            context=f"prompt defaults for {self.task_id}",
        )
        slots = {
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults["answer_hint_pixel_village_building_near_path"]),
            "annotation_hint": str(prompt_defaults["annotation_hint_pixel_village_building_near_path"]),
            "json_example": str(prompt_defaults["json_example_pixel_village_building_near_path"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only_pixel_village_building_near_path"]),
        }
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=BUILDING_NEAR_PATH_COUNT_QUERY_ID,
            slots=slots,
            instance_seed=int(instance_seed),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            preferred_mode="answer_and_annotation",
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        trace_payload = {
            "scene_ir": {
                "domain": self.domain,
                "scene_id": SCENE_ID,
                "entities": _scene_entities(scene),
                "territories": _scene_territories(scene),
                "relations": {
                    "query_id": BUILDING_NEAR_PATH_COUNT_QUERY_ID,
                    "near_path_rule": "building tile footprint has Chebyshev tile distance <= near_path_tile_distance from any path tile",
                    "near_path_tile_distance": int(distance),
                },
            },
            "query_spec": {
                "task_id": self.task_id,
                "query_id": BUILDING_NEAR_PATH_COUNT_QUERY_ID,
                "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "near_path_tile_distance": int(distance),
                    "target_count": int(answer),
                    "target_answer_count_max": int(answer_count_max),
                    "renderer": _render_metadata(scene),
                },
            },
            "render_spec": {
                "canvas_size": [int(scene.image.size[0]), int(scene.image.size[1])],
                "coord_space": "pixel",
                "scene_id": SCENE_ID,
                "style": {
                    "renderer_id": str(scene.trace.get("renderer_id", "")),
                    "style_id": "top_down_pixel_rpg",
                    "theme_id": str(scene.trace.get("theme_id", "")),
                    "tile_px": int(scene.trace.get("tile_px", 0)),
                    "grid_cols": int(scene.trace.get("grid_cols", 0)),
                    "grid_rows": int(scene.trace.get("grid_rows", 0)),
                },
            },
            "render_map": {
                "image_id": "img0",
                "entity_bboxes_px": dict(entity_bboxes),
                "path_tiles": list(scene.trace.get("path_tiles", [])),
                "counted_entity_ids": list(counted_entity_ids),
            },
            "execution_trace": {
                "query_id": BUILDING_NEAR_PATH_COUNT_QUERY_ID,
                "scene_id": SCENE_ID,
                "near_path_tile_distance": int(distance),
                "answer": int(answer),
                "counted_entity_ids": list(counted_entity_ids),
                "path_tiles": list(scene.trace.get("path_tiles", [])),
                "category_counts": dict(scene.trace.get("category_counts", {})),
                "public_name_counts": dict(scene.trace.get("public_name_counts", {})),
                "renderer": _render_metadata(scene),
            },
            "witness_symbolic": {
                "counted_entity_ids": list(counted_entity_ids),
                "near_path_tile_distance": int(distance),
                "count": int(answer),
                "answer": int(answer),
            },
            "projected_annotation": {"bbox_set": list(annotation_value)},
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
            answer_gt=TypedValue(type="integer", value=int(answer)),
            annotation_gt=TypedValue(type="bbox_set", value=list(annotation_value)),
            image=scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_building_path_complexity(scene=scene, answer=answer),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=BUILDING_NEAR_PATH_COUNT_QUERY_ID,
        )


__all__ = [
    "IllustrationsPixelVillageBuildingNearPathCountTask",
    "IllustrationsPixelVillageObjectTypeCountTask",
    "IllustrationsPixelVillagePersonPathCountTask",
    "IllustrationsPixelVillageTerritoryObjectCountTask",
]
