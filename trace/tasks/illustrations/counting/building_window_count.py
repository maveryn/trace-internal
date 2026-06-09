"""Count lit windows in skyline buildings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ..shared.task_support import uniform_string_probability_map as _uniform_string_probability_map
from ..shared.environment_object_scene import ENVIRONMENT_THEME_IDS, render_environment_object_scene
from ..shared.environment_task_common import (
    environment_render_params,
    environment_scene_entities,
    environment_setting_name,
    feature_bbox_map,
    feature_path_map,
    serialize_environment_objects,
    sort_bboxes_by_ids,
    style_weights,
)


TASK_ID = "task_illustrations__environment__lit_window_count"
SCENE_ID = "environment"
QUERY_ID = "building_window_count"
WINDOW_MODE_SUPPORT: Tuple[str, ...] = ("lit",)
WINDOW_MODE_NAMES: Dict[str, str] = {"lit": "lit windows"}


@dataclass(frozen=True)
class _Defaults:
    object_count_min: int = 8
    object_count_max: int = 14
    canvas_width: int = 1280
    canvas_height: int = 840
    object_size_min_px: int = 58
    object_size_max_px: int = 108
    min_gap_px: int = 6
    max_overlap_fraction: float = 0.02
    placement_max_attempts: int = 420
    render_scale: int = 2
    skyline_building_min: int = 4
    skyline_building_max: int = 7
    target_count_min: int = 1
    target_count_max: int = 10


@dataclass(frozen=True)
class _QueryChoice:
    theme_id: str
    window_mode: str
    theme_probabilities: Dict[str, float]
    window_mode_probabilities: Dict[str, float]


_DEFAULTS = _Defaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("illustrations", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)




def _theme_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get("theme_support", group_default(_GEN_DEFAULTS, "theme_support", ("canal_city", "skyline_street")))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("theme_support must be a sequence")
    supported = tuple(str(value) for value in raw if str(value) in {"canal_city", "skyline_street"})
    if not supported:
        raise ValueError("building window task needs skyline/city themes")
    return tuple(dict.fromkeys(supported))


def _window_mode_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get("window_mode_support", group_default(_GEN_DEFAULTS, "window_mode_support", ("lit",)))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("window_mode_support must be a sequence")
    supported = tuple(str(value) for value in raw if str(value) == "lit")
    if not supported:
        raise ValueError("window_mode_support resolved no supported modes")
    return tuple(dict.fromkeys(supported))


def _target_count(params: Mapping[str, Any], instance_seed: int) -> Tuple[int, Dict[int, float]]:
    low = int(params.get("target_count_min", group_default(_GEN_DEFAULTS, "target_count_min", _DEFAULTS.target_count_min)))
    high = int(params.get("target_count_max", group_default(_GEN_DEFAULTS, "target_count_max", _DEFAULTS.target_count_max)))
    if low < 0 or high < low:
        raise ValueError("invalid target_count range")
    support = tuple(range(int(low), int(high) + 1))
    explicit = params.get("target_count")
    if explicit is not None:
        value = int(explicit)
        if value not in set(support):
            raise ValueError("target_count is outside configured support")
    else:
        index = abs(int(instance_seed))
        value = int(support[int(index) % len(support)])
    return int(value), dict(uniform_probability_map(support, selected=int(value) if explicit is not None else None))


def _query_choice(*, instance_seed: int, params: Mapping[str, Any]) -> _QueryChoice:
    themes = _theme_support(params)
    modes = _window_mode_support(params)
    selection_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:query")
    explicit_theme = params.get("theme_id")
    if explicit_theme is not None:
        theme_id = str(explicit_theme)
        if theme_id not in set(themes):
            raise ValueError(f"theme_id must be one of {themes}")
    else:
        theme_id = str(themes[int(selection_index) % len(themes)])
    explicit_mode = params.get("window_mode")
    if explicit_mode is not None:
        window_mode = str(explicit_mode)
        if window_mode not in set(modes):
            raise ValueError(f"window_mode must be one of {modes}")
    else:
        window_mode = str(modes[int(selection_index // max(1, len(themes))) % len(modes)])
    return _QueryChoice(
        theme_id=str(theme_id),
        window_mode=str(window_mode),
        theme_probabilities=_uniform_string_probability_map(themes, selected=str(theme_id) if explicit_theme is not None else None),
        window_mode_probabilities=_uniform_string_probability_map(modes, selected=str(window_mode) if explicit_mode is not None else None),
    )


def _object_count(params: Mapping[str, Any], instance_seed: int) -> Tuple[int, Dict[str, float]]:
    low = int(params.get("object_count_min", group_default(_GEN_DEFAULTS, "object_count_min", _DEFAULTS.object_count_min)))
    high = int(params.get("object_count_max", group_default(_GEN_DEFAULTS, "object_count_max", _DEFAULTS.object_count_max)))
    support = tuple(range(int(low), int(high) + 1))
    explicit = params.get("object_count")
    if explicit is not None:
        value = int(explicit)
        if value not in set(support):
            raise ValueError("object_count is outside configured support")
    else:
        index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:object_count")
        value = int(support[int(index) % len(support)])
    return int(value), dict(uniform_probability_map(support, selected=int(value) if explicit is not None else None))


def _window_bboxes(scene, window_mode: str) -> Tuple[Tuple[str, list[float]], ...]:
    items = []
    for building in scene.buildings:
        bboxes = building.lit_window_bboxes
        for index, bbox in enumerate(bboxes):
            items.append((f"{building.building_id}_{window_mode}_window_{index:02d}", [round(float(v), 3) for v in bbox]))
    return tuple(items)


def _build_complexity(*, object_count: int, target_count: int, window_mode: str) -> TaskComplexity:
    visual_scan = (int(object_count) - _DEFAULTS.object_count_min) / max(1, _DEFAULTS.object_count_max - _DEFAULTS.object_count_min)
    answer_load = min(1.0, float(target_count) / float(_DEFAULTS.target_count_max))
    window_load = 0.58
    score = 0.35 * max(0.0, min(1.0, visual_scan)) + 0.45 * max(0.0, min(1.0, answer_load)) + 0.20 * window_load
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={
            "visual_scan": round(float(visual_scan), 6),
            "answer_load": round(float(answer_load), 6),
            "window_load": round(float(window_load), 6),
        },
    )


@register_task
class IllustrationsCountingBuildingWindowCountTask:
    """Count lit windows in skyline buildings."""

    task_id = TASK_ID
    domain = "illustrations"
    task_group = "counting"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query = _query_choice(instance_seed=int(instance_seed), params=params)
        requested_object_count, object_count_probabilities = _object_count(params, int(instance_seed))
        desired_target_count, target_count_probabilities = _target_count(params, int(instance_seed))
        render_params = environment_render_params(
            params,
            _RENDER_DEFAULTS,
            fallback={
                "canvas_width": _DEFAULTS.canvas_width,
                "canvas_height": _DEFAULTS.canvas_height,
                "object_size_min_px": _DEFAULTS.object_size_min_px,
                "object_size_max_px": _DEFAULTS.object_size_max_px,
                "min_gap_px": _DEFAULTS.min_gap_px,
                "max_overlap_fraction": _DEFAULTS.max_overlap_fraction,
                "placement_max_attempts": _DEFAULTS.placement_max_attempts,
                "render_scale": _DEFAULTS.render_scale,
                "skyline_building_min": _DEFAULTS.skyline_building_min,
                "skyline_building_max": _DEFAULTS.skyline_building_max,
            },
        )
        last_error: Exception | None = None
        scene = None
        window_items: Tuple[Tuple[str, list[float]], ...] = ()
        for attempt in range(max(1, int(max_attempts))):
            try:
                scene_rng = spawn_rng(int(instance_seed), f"{TASK_ID}:scene", int(attempt))
                scene = render_environment_object_scene(
                    rng=scene_rng,
                    canvas_width=int(render_params["canvas_width"]),
                    canvas_height=int(render_params["canvas_height"]),
                    object_count=int(requested_object_count),
                    render_scale=int(render_params["render_scale"]),
                    theme_weights={theme: (1.0 if theme == query.theme_id else 0.0) for theme in ENVIRONMENT_THEME_IDS},
                    style_weights=style_weights(params, _RENDER_DEFAULTS),
                    object_size_min_px=int(render_params["object_size_min_px"]),
                    object_size_max_px=int(render_params["object_size_max_px"]),
                    min_gap_px=int(render_params["min_gap_px"]),
                    max_overlap_fraction=float(render_params["max_overlap_fraction"]),
                    placement_max_attempts=int(render_params["placement_max_attempts"]),
                    skyline_building_min=int(render_params["skyline_building_min"]),
                    skyline_building_max=int(render_params["skyline_building_max"]),
                    lit_window_count_override=int(desired_target_count),
                )
                window_items = _window_bboxes(scene, str(query.window_mode))
                if len(window_items) == int(desired_target_count):
                    break
                raise ValueError(f"rendered {len(window_items)} lit windows, expected {desired_target_count}")
            except Exception as exc:  # pragma: no cover
                last_error = exc
                scene = None
                window_items = ()
        if scene is None:
            raise RuntimeError(f"could not generate {TASK_ID}: {last_error}") from last_error

        _serialized_objects, object_bboxes, part_bboxes = serialize_environment_objects(scene)
        window_bbox_map = {item_id: bbox for item_id, bbox in window_items}
        counted_window_ids = tuple(item_id for item_id, _bbox in window_items)
        annotation_value = sort_bboxes_by_ids(window_bbox_map, counted_window_ids)
        answer = int(len(counted_window_ids))
        window_phrase = WINDOW_MODE_NAMES[str(query.window_mode)]
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_building_window",
                "annotation_hint_building_window",
                "json_example_building_window",
                "json_example_answer_only_building_window",
            ],
            context=f"prompt defaults for {TASK_ID}",
        )
        slots = {
            "object_count": int(len(scene.placements)),
            "environment_setting": environment_setting_name(str(query.theme_id)),
            "feature_name": "buildings",
            "window_phrase": str(window_phrase),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults["answer_hint_building_window"]).format(window_phrase=str(window_phrase)),
            "annotation_hint": str(prompt_defaults["annotation_hint_building_window"]).format(window_phrase=str(window_phrase)),
            "json_example": str(prompt_defaults["json_example_building_window"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only_building_window"]),
        }
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=QUERY_ID,
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
                "entities": environment_scene_entities(scene),
                "relations": {"query_id": QUERY_ID, "window_mode": str(query.window_mode)},
            },
            "query_spec": {
                "task_id": self.task_id,
                "query_id": QUERY_ID,
                "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "theme": str(query.theme_id),
                    "theme_id": str(query.theme_id),
                    "window_mode": str(query.window_mode),
                    "window_phrase": str(window_phrase),
                    "target_count": int(answer),
                    "target_count_probabilities": dict(target_count_probabilities),
                    "object_count": int(len(scene.placements)),
                    "requested_object_count": int(requested_object_count),
                    "theme_probabilities": dict(query.theme_probabilities),
                    "window_mode_probabilities": dict(query.window_mode_probabilities),
                    "object_count_probabilities": dict(object_count_probabilities),
                },
            },
            "render_spec": {
                "canvas_size": [int(scene.canvas_width), int(scene.canvas_height)],
                "coord_space": "pixel",
                "scene_id": SCENE_ID,
                "style": {
                    "theme_id": str(scene.theme_id),
                    "layout": dict(scene.layout),
                    "style_id": str(scene.style_id),
                    "render_scale": int(scene.render_scale),
                },
            },
            "render_map": {
                "image_id": "img0",
                "object_bboxes_px": object_bboxes,
                "part_bboxes_px": part_bboxes,
                "feature_bboxes_px": feature_bbox_map(scene),
                "feature_paths_px": feature_path_map(scene),
                "window_bboxes_px": window_bbox_map,
                "counted_window_ids": list(counted_window_ids),
            },
            "execution_trace": {
                "query_id": QUERY_ID,
                "scene_id": SCENE_ID,
                "theme_id": str(query.theme_id),
                "window_mode": str(query.window_mode),
                "target_count": int(answer),
                "object_count": int(len(scene.placements)),
                "requested_object_count": int(requested_object_count),
                "building_count": int(len(scene.buildings)),
                "counted_window_ids": list(counted_window_ids),
            },
            "witness_symbolic": {"counted_window_ids": list(counted_window_ids), "window_mode": str(query.window_mode), "answer": int(answer)},
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
            complexity=_build_complexity(object_count=int(len(scene.placements)), target_count=int(answer), window_mode=str(query.window_mode)),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=QUERY_ID,
        )


__all__ = ["IllustrationsCountingBuildingWindowCountTask"]
