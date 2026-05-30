"""Merged environment feature-relation counting task."""

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
from ..shared.task_support import query_support as _shared_query_support
from ..shared.environment_object_scene import ENVIRONMENT_THEME_IDS, render_environment_object_scene
from ..shared.environment_task_common import (
    FEATURE_TYPES_BY_THEME,
    capped_object_count_probabilities,
    environment_render_params,
    environment_scene_entities,
    environment_setting_name,
    feature_bbox_map,
    feature_path_map,
    serialize_environment_objects,
    sort_bboxes_by_ids,
    style_weights,
    target_feature,
    theme_support,
)


TASK_ID = "task_illustrations__environment__feature_relation_count"
SCENE_ID = "environment"
QUERY_IDS: Tuple[str, ...] = (
    "feature_side_object_count",
    "on_feature_object_count",
    "crossing_feature_count",
)
RELATION_SUPPORT: Tuple[str, ...] = ("above", "below")
CROSSING_THEME_SUPPORT: Dict[str, Tuple[str, ...]] = {
    "bridge": ("river_meadow", "road_and_river", "canal_city"),
    "crosswalk": ("park_road", "road_and_river", "skyline_street"),
}
CROSSING_NAMES: Dict[str, str] = {"bridge": "bridges", "crosswalk": "crosswalks"}
CROSSED_FEATURE_NAMES: Dict[str, str] = {"bridge": "river", "crosswalk": "road"}


@dataclass(frozen=True)
class _Defaults:
    object_count_min: int = 12
    object_count_max: int = 18
    feature_side_target_count_min: int = 1
    feature_side_target_count_max: int = 12
    on_feature_target_count_min: int = 2
    on_feature_target_count_max: int = 7
    crossing_target_count_min: int = 1
    crossing_target_count_max: int = 5
    canvas_width: int = 1280
    canvas_height: int = 840
    object_size_min_px: int = 62
    object_size_max_px: int = 116
    min_gap_px: int = 6
    max_overlap_fraction: float = 0.02
    placement_max_attempts: int = 420
    render_scale: int = 2


@dataclass(frozen=True)
class _QueryChoice:
    query_id: str
    branch_index: int
    query_probabilities: Dict[str, float]
    theme_id: str
    theme_probabilities: Dict[str, float]
    feature_type: str | None = None
    feature_type_probabilities: Dict[str, float] | None = None
    relation: str | None = None
    relation_probabilities: Dict[str, float] | None = None
    crossing_type: str | None = None
    crossing_type_probabilities: Dict[str, float] | None = None


_DEFAULTS = _Defaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("illustrations", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)






def _relation_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get("relation_support", group_default(_GEN_DEFAULTS, "relation_support", RELATION_SUPPORT))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("relation_support must be a sequence")
    support = tuple(str(value) for value in raw if str(value) in set(RELATION_SUPPORT))
    if not support:
        raise ValueError("relation_support resolved no supported relations")
    return tuple(dict.fromkeys(support))


def _crossing_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get("crossing_type_support", group_default(_GEN_DEFAULTS, "crossing_type_support", tuple(CROSSING_THEME_SUPPORT)))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("crossing_type_support must be a sequence")
    support = tuple(str(value) for value in raw if str(value) in set(CROSSING_THEME_SUPPORT))
    if not support:
        raise ValueError("crossing_type_support resolved no supported crossing types")
    return tuple(dict.fromkeys(support))


def _global_feature_type_probabilities(themes: Sequence[str], *, selected: str | None = None) -> Dict[str, float]:
    if selected is not None:
        return {str(selected): 1.0}
    weights = {"road": 0.0, "river": 0.0}
    for theme in themes:
        support = FEATURE_TYPES_BY_THEME[str(theme)]
        probability = 1.0 / float(len(support))
        for feature_type in support:
            weights[str(feature_type)] += probability
    total = sum(weights.values())
    return {key: value / total for key, value in sorted(weights.items()) if value > 0.0}


def _choose_query(*, params: Mapping[str, Any], instance_seed: int) -> Tuple[str, Dict[str, float], int]:
    query_values = _shared_query_support(params, _GEN_DEFAULTS, QUERY_IDS)
    base_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:cycle")
    explicit_query = params.get("query_id")
    if explicit_query is not None:
        query_id = str(explicit_query)
        if query_id not in set(query_values):
            raise ValueError("query_id is outside configured support")
        return query_id, _uniform_string_probability_map(query_values, selected=query_id), int(base_index)
    query_id = str(query_values[int(base_index) % len(query_values)])
    return query_id, _uniform_string_probability_map(query_values), int(base_index // max(1, len(query_values)))


def _resolve_feature_query(
    *,
    params: Mapping[str, Any],
    branch_index: int,
    query_id: str,
    query_probabilities: Mapping[str, float],
) -> _QueryChoice:
    themes = theme_support(params, _GEN_DEFAULTS)
    explicit_theme = params.get("theme_id")
    if explicit_theme is not None:
        theme_id = str(explicit_theme)
        if theme_id not in set(themes):
            raise ValueError(f"theme_id must be one of {themes}")
        theme_probabilities = _uniform_string_probability_map(themes, selected=theme_id)
    else:
        theme_id = str(themes[int(branch_index) % len(themes)])
        theme_probabilities = _uniform_string_probability_map(themes)

    feature_support = FEATURE_TYPES_BY_THEME[str(theme_id)]
    explicit_feature = params.get("feature_type")
    if explicit_feature is not None:
        feature_type = str(explicit_feature)
        if feature_type not in set(feature_support):
            raise ValueError(f"feature_type {feature_type!r} is not available for theme {theme_id!r}")
        feature_probabilities = _global_feature_type_probabilities(themes, selected=feature_type)
    else:
        feature_type = str(feature_support[int(branch_index // max(1, len(themes))) % len(feature_support)])
        feature_probabilities = _global_feature_type_probabilities(themes)

    relation = None
    relation_probabilities = None
    if str(query_id) == "feature_side_object_count":
        relations = _relation_support(params)
        explicit_relation = params.get("relation")
        if explicit_relation is not None:
            relation = str(explicit_relation)
            if relation not in set(relations):
                raise ValueError(f"relation must be one of {relations}")
            relation_probabilities = _uniform_string_probability_map(relations, selected=relation)
        else:
            relation = str(relations[int(branch_index // max(1, len(themes) * len(feature_support))) % len(relations)])
            relation_probabilities = _uniform_string_probability_map(relations)

    return _QueryChoice(
        query_id=str(query_id),
        branch_index=int(branch_index),
        query_probabilities=dict(query_probabilities),
        theme_id=str(theme_id),
        theme_probabilities=dict(theme_probabilities),
        feature_type=str(feature_type),
        feature_type_probabilities=dict(feature_probabilities),
        relation=relation,
        relation_probabilities=relation_probabilities,
    )


def _resolve_crossing_query(
    *,
    params: Mapping[str, Any],
    branch_index: int,
    query_probabilities: Mapping[str, float],
) -> _QueryChoice:
    crossing_values = _crossing_support(params)
    explicit_crossing = params.get("crossing_type")
    if explicit_crossing is not None:
        crossing_type = str(explicit_crossing)
        if crossing_type not in set(crossing_values):
            raise ValueError(f"crossing_type must be one of {crossing_values}")
        crossing_probabilities = _uniform_string_probability_map(crossing_values, selected=crossing_type)
    else:
        crossing_type = str(crossing_values[int(branch_index) % len(crossing_values)])
        crossing_probabilities = _uniform_string_probability_map(crossing_values)

    theme_options = CROSSING_THEME_SUPPORT[str(crossing_type)]
    explicit_theme = params.get("theme_id")
    if explicit_theme is not None:
        theme_id = str(explicit_theme)
        if theme_id not in set(theme_options):
            raise ValueError(f"theme_id must be one of {theme_options} for crossing_type {crossing_type!r}")
        theme_probabilities = {theme_id: 1.0}
    else:
        theme_id = str(theme_options[int(branch_index // max(1, len(crossing_values))) % len(theme_options)])
        theme_probabilities: Dict[str, float] = {}
        for crossing in crossing_values:
            crossing_probability = 1.0 / float(len(crossing_values))
            options = CROSSING_THEME_SUPPORT[str(crossing)]
            theme_probability = crossing_probability / float(len(options))
            for theme in options:
                theme_probabilities[str(theme)] = float(theme_probabilities.get(str(theme), 0.0)) + float(theme_probability)

    return _QueryChoice(
        query_id="crossing_feature_count",
        branch_index=int(branch_index),
        query_probabilities=dict(query_probabilities),
        theme_id=str(theme_id),
        theme_probabilities=dict(sorted(theme_probabilities.items())),
        crossing_type=str(crossing_type),
        crossing_type_probabilities=dict(crossing_probabilities),
    )


def _resolve_query_choice(*, instance_seed: int, params: Mapping[str, Any]) -> _QueryChoice:
    query_id, query_probabilities, branch_index = _choose_query(params=params, instance_seed=int(instance_seed))
    if str(query_id) == "crossing_feature_count":
        return _resolve_crossing_query(params=params, branch_index=int(branch_index), query_probabilities=query_probabilities)
    return _resolve_feature_query(
        params=params,
        branch_index=int(branch_index),
        query_id=str(query_id),
        query_probabilities=query_probabilities,
    )


def _int_bounds(params: Mapping[str, Any], low_key: str, high_key: str, fallback_low: int, fallback_high: int) -> Tuple[int, int]:
    if "target_count_min" in params or "target_count_max" in params:
        low = int(params.get("target_count_min", fallback_low))
        high = int(params.get("target_count_max", fallback_high))
    else:
        low = int(params.get(low_key, group_default(_GEN_DEFAULTS, low_key, fallback_low)))
        high = int(params.get(high_key, group_default(_GEN_DEFAULTS, high_key, fallback_high)))
    if low < 0 or high < low:
        raise ValueError(f"invalid {low_key}/{high_key} range")
    return int(low), int(high)


def _target_count(params: Mapping[str, Any], choice: _QueryChoice) -> Tuple[int, Dict[str, float]]:
    if choice.query_id == "on_feature_object_count":
        low, high = _int_bounds(
            params,
            "on_feature_target_count_min",
            "on_feature_target_count_max",
            _DEFAULTS.on_feature_target_count_min,
            _DEFAULTS.on_feature_target_count_max,
        )
    elif choice.query_id == "crossing_feature_count":
        low, high = _int_bounds(
            params,
            "crossing_target_count_min",
            "crossing_target_count_max",
            _DEFAULTS.crossing_target_count_min,
            _DEFAULTS.crossing_target_count_max,
        )
    else:
        low, high = _int_bounds(
            params,
            "feature_side_target_count_min",
            "feature_side_target_count_max",
            _DEFAULTS.feature_side_target_count_min,
            _DEFAULTS.feature_side_target_count_max,
        )
    support = tuple(range(int(low), int(high) + 1))
    explicit = params.get("target_count")
    if explicit is not None:
        value = int(explicit)
        if value not in set(support):
            raise ValueError("target_count is outside configured support")
    else:
        value = int(support[int(choice.branch_index) % len(support)])
    return int(value), dict(uniform_probability_map(support, selected=int(value) if explicit is not None else None))


def _object_count(params: Mapping[str, Any], choice: _QueryChoice) -> Tuple[int, Dict[str, float]]:
    low = int(params.get("object_count_min", group_default(_GEN_DEFAULTS, "object_count_min", _DEFAULTS.object_count_min)))
    high = int(params.get("object_count_max", group_default(_GEN_DEFAULTS, "object_count_max", _DEFAULTS.object_count_max)))
    support = tuple(range(int(low), int(high) + 1))
    explicit = params.get("object_count")
    if explicit is not None:
        value = int(explicit)
        if value not in set(support):
            raise ValueError("object_count is outside configured support")
    else:
        value = int(support[int(choice.branch_index) % len(support)])
    return int(value), dict(uniform_probability_map(support, selected=int(value) if explicit is not None else None))


def _render_params(params: Mapping[str, Any]) -> Dict[str, Any]:
    return environment_render_params(
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
        },
    )


def _counted_side_object_ids(*, scene, feature_id: str, relation: str) -> Tuple[str, ...]:
    ids = []
    for placement in scene.placements:
        relation_info = placement.relations.get(str(feature_id))
        if isinstance(relation_info, Mapping) and str(relation_info.get("vertical_relation")) == str(relation):
            ids.append(str(placement.object_id))
    return tuple(ids)


def _build_complexity(*, query_id: str, object_count: int, target_count: int, theme_id: str) -> TaskComplexity:
    visual_scan = (int(object_count) - _DEFAULTS.object_count_min) / max(1, _DEFAULTS.object_count_max - _DEFAULTS.object_count_min)
    if str(query_id) == "feature_side_object_count":
        answer_load = min(1.0, float(target_count) / max(1.0, float(_DEFAULTS.feature_side_target_count_max)))
        relation_load = 0.82
    elif str(query_id) == "on_feature_object_count":
        answer_load = min(1.0, float(target_count) / max(1.0, float(_DEFAULTS.on_feature_target_count_max)))
        relation_load = 0.70
    else:
        answer_load = min(1.0, float(target_count) / max(1.0, float(_DEFAULTS.crossing_target_count_max)))
        relation_load = 0.76
    scene_load = 1.0 if str(theme_id) in {"road_and_river", "canal_city", "skyline_street"} else 0.65
    score = 0.38 * max(0.0, min(1.0, visual_scan)) + 0.32 * max(0.0, min(1.0, answer_load)) + 0.18 * relation_load + 0.12 * scene_load
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={
            "visual_scan": round(float(visual_scan), 6),
            "answer_load": round(float(answer_load), 6),
            "relation_load": round(float(relation_load), 6),
            "scene_load": round(float(scene_load), 6),
        },
    )


@register_task
class IllustrationsCountingFeatureRelationObjectCountTask:
    """Count environment objects or crossing features relative to roads/rivers."""

    task_id = TASK_ID
    domain = "illustrations"
    task_group = "counting"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        choice = _resolve_query_choice(instance_seed=int(instance_seed), params=params)
        requested_object_count, requested_object_count_probabilities = _object_count(params, choice)
        target_count, target_count_probabilities = _target_count(params, choice)
        object_count_probabilities = capped_object_count_probabilities(
            requested_object_count_probabilities,
            choice.theme_probabilities,
        )
        render_params = _render_params(params)
        scene = None
        feature = None
        counted_object_ids: Tuple[str, ...] = ()
        counted_feature_ids: Tuple[str, ...] = ()
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                scene_rng = spawn_rng(int(instance_seed), f"{TASK_ID}:scene:{choice.query_id}", int(attempt))
                overrides: Dict[str, Any] = {}
                if choice.query_id == "on_feature_object_count":
                    overrides["bridge_count_override"] = 0
                    overrides["crosswalk_count_override"] = 0
                    overrides["zone_count_overrides"] = {str(choice.feature_type): int(target_count)}
                elif choice.query_id == "crossing_feature_count":
                    overrides["bridge_count_override"] = int(target_count) if choice.crossing_type == "bridge" else None
                    overrides["crosswalk_count_override"] = int(target_count) if choice.crossing_type == "crosswalk" else None
                scene = render_environment_object_scene(
                    rng=scene_rng,
                    canvas_width=int(render_params["canvas_width"]),
                    canvas_height=int(render_params["canvas_height"]),
                    object_count=int(requested_object_count),
                    render_scale=int(render_params["render_scale"]),
                    theme_weights={theme: (1.0 if theme == choice.theme_id else 0.0) for theme in ENVIRONMENT_THEME_IDS},
                    style_weights=style_weights(params, _RENDER_DEFAULTS),
                    object_size_min_px=int(render_params["object_size_min_px"]),
                    object_size_max_px=int(render_params["object_size_max_px"]),
                    min_gap_px=int(render_params["min_gap_px"]),
                    max_overlap_fraction=float(render_params["max_overlap_fraction"]),
                    placement_max_attempts=int(render_params["placement_max_attempts"]),
                    **overrides,
                )
                if choice.query_id == "crossing_feature_count":
                    counted_feature_ids = tuple(
                        str(item.feature_id)
                        for item in scene.features
                        if str(item.feature_type) == str(choice.crossing_type)
                    )
                    if len(counted_feature_ids) == int(target_count):
                        break
                    raise ValueError(f"crossing count {len(counted_feature_ids)} did not match target {target_count}")
                feature = target_feature(scene, str(choice.feature_type))
                if choice.query_id == "on_feature_object_count":
                    counted_object_ids = tuple(
                        str(placement.object_id)
                        for placement in scene.placements
                        if str(placement.zone_id) == str(choice.feature_type)
                    )
                    if len(counted_object_ids) == int(target_count):
                        break
                    raise ValueError(f"on-feature count {len(counted_object_ids)} did not match target {target_count}")
                side_min, side_max = _int_bounds(
                    params,
                    "feature_side_target_count_min",
                    "feature_side_target_count_max",
                    _DEFAULTS.feature_side_target_count_min,
                    _DEFAULTS.feature_side_target_count_max,
                )
                counted_object_ids = _counted_side_object_ids(
                    scene=scene,
                    feature_id=str(feature.feature_id),
                    relation=str(choice.relation),
                )
                if int(side_min) <= len(counted_object_ids) <= int(side_max):
                    break
                raise ValueError(f"feature-side count {len(counted_object_ids)} outside range {side_min}..{side_max}")
            except Exception as exc:  # pragma: no cover
                last_error = exc
                scene = None
                feature = None
                counted_object_ids = ()
                counted_feature_ids = ()
        if scene is None:
            raise RuntimeError(f"could not generate {TASK_ID}: {last_error}") from last_error

        serialized_objects, object_bboxes, part_bboxes = serialize_environment_objects(scene)
        feature_bboxes = feature_bbox_map(scene)
        feature_paths = feature_path_map(scene)
        if choice.query_id == "crossing_feature_count":
            evidence_value = sort_bboxes_by_ids(feature_bboxes, counted_feature_ids)
            answer = int(len(counted_feature_ids))
        else:
            evidence_value = sort_bboxes_by_ids(object_bboxes, counted_object_ids)
            answer = int(len(counted_object_ids))

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_feature_side",
                "evidence_hint_feature_side",
                "json_example_feature_side",
                "json_example_answer_only_feature_side",
                "answer_hint_on_feature",
                "evidence_hint_on_feature",
                "json_example_on_feature",
                "json_example_answer_only_on_feature",
                "answer_hint_crossing_feature",
                "evidence_hint_crossing_feature",
                "json_example_crossing_feature",
                "json_example_answer_only_crossing_feature",
            ],
            context=f"prompt defaults for {TASK_ID}",
        )
        feature_name = "road" if choice.feature_type == "road" else "river"
        feature_phrase = "on the road" if choice.feature_type == "road" else "in or on the river"
        crossing_name = CROSSING_NAMES.get(str(choice.crossing_type), "")
        crossed_feature_name = CROSSED_FEATURE_NAMES.get(str(choice.crossing_type), "")
        if choice.query_id == "feature_side_object_count":
            answer_hint = str(prompt_defaults["answer_hint_feature_side"]).format(
                relation_word=str(choice.relation),
                feature_name=str(feature_name),
            )
            evidence_hint = str(prompt_defaults["evidence_hint_feature_side"]).format(
                relation_word=str(choice.relation),
                feature_name=str(feature_name),
            )
            json_example = str(prompt_defaults["json_example_feature_side"])
            json_example_answer_only = str(prompt_defaults["json_example_answer_only_feature_side"])
        elif choice.query_id == "on_feature_object_count":
            answer_hint = str(prompt_defaults["answer_hint_on_feature"]).format(feature_phrase=str(feature_phrase))
            evidence_hint = str(prompt_defaults["evidence_hint_on_feature"]).format(feature_phrase=str(feature_phrase))
            json_example = str(prompt_defaults["json_example_on_feature"])
            json_example_answer_only = str(prompt_defaults["json_example_answer_only_on_feature"])
        else:
            answer_hint = str(prompt_defaults["answer_hint_crossing_feature"]).format(
                crossing_name=str(crossing_name),
                crossed_feature_name=str(crossed_feature_name),
            )
            evidence_hint = str(prompt_defaults["evidence_hint_crossing_feature"]).format(
                crossing_name=str(crossing_name),
                crossed_feature_name=str(crossed_feature_name),
            )
            json_example = str(prompt_defaults["json_example_crossing_feature"])
            json_example_answer_only = str(prompt_defaults["json_example_answer_only_crossing_feature"])

        slots = {
            "object_count": int(len(scene.placements)),
            "environment_setting": environment_setting_name(str(choice.theme_id)),
            "feature_name": str(feature_name),
            "feature_phrase": str(feature_phrase),
            "relation_word": str(choice.relation or ""),
            "crossing_name": str(crossing_name),
            "crossed_feature_name": str(crossed_feature_name),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(answer_hint),
            "evidence_hint": str(evidence_hint),
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
        }
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(choice.query_id),
            slots=slots,
            instance_seed=int(instance_seed),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            preferred_mode="answer_and_evidence",
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        feature_id = str(feature.feature_id) if feature is not None else None
        trace_payload = {
            "scene_ir": {
                "domain": self.domain,
                "scene_id": SCENE_ID,
                "entities": environment_scene_entities(scene),
                "relations": {
                    "query_id": str(choice.query_id),
                    "feature_type": choice.feature_type,
                    "feature_id": feature_id,
                    "relation": choice.relation,
                    "crossing_type": choice.crossing_type,
                },
            },
            "query_spec": {
                "task_id": self.task_id,
                "query_id": str(choice.query_id),
                "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "theme": str(choice.theme_id),
                    "theme_id": str(choice.theme_id),
                    "feature_type": choice.feature_type,
                    "feature_id": feature_id,
                    "relation": choice.relation,
                    "crossing_type": choice.crossing_type,
                    "crossing_name": crossing_name,
                    "crossed_feature_name": crossed_feature_name,
                    "object_count": int(len(scene.placements)),
                    "requested_object_count": int(requested_object_count),
                    "target_count": int(answer),
                    "query_probabilities": dict(choice.query_probabilities),
                    "target_count_probabilities": dict(target_count_probabilities),
                    "theme_probabilities": dict(choice.theme_probabilities),
                    "feature_type_probabilities": dict(choice.feature_type_probabilities or {}),
                    "relation_probabilities": dict(choice.relation_probabilities or {}),
                    "crossing_type_probabilities": dict(choice.crossing_type_probabilities or {}),
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
                "feature_bboxes_px": feature_bboxes,
                "feature_paths_px": feature_paths,
                "counted_object_ids": list(counted_object_ids),
                "counted_feature_ids": list(counted_feature_ids),
                "target_feature_id": feature_id,
            },
            "execution_trace": {
                "query_id": str(choice.query_id),
                "scene_id": SCENE_ID,
                "theme_id": str(choice.theme_id),
                "feature_type": choice.feature_type,
                "feature_id": feature_id,
                "relation": choice.relation,
                "crossing_type": choice.crossing_type,
                "target_count": int(answer),
                "object_count": int(len(scene.placements)),
                "requested_object_count": int(requested_object_count),
                "counted_object_ids": list(counted_object_ids),
                "counted_feature_ids": list(counted_feature_ids),
                "object_zones": {placement.object_id: placement.zone_id for placement in scene.placements},
                "objects": serialized_objects,
            },
            "witness_symbolic": {
                "counted_object_ids": list(counted_object_ids),
                "counted_feature_ids": list(counted_feature_ids),
                "feature_id": feature_id,
                "feature_type": choice.feature_type,
                "relation": choice.relation,
                "crossing_type": choice.crossing_type,
                "answer": int(answer),
            },
            "projected_evidence": {"bbox_set": list(evidence_value)},
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
            answer_gt=TypedValue(type="integer", value=int(answer)),
            evidence_gt=TypedValue(type="bbox_set", value=list(evidence_value)),
            image=scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_build_complexity(
                query_id=str(choice.query_id),
                object_count=int(len(scene.placements)),
                target_count=int(answer),
                theme_id=str(choice.theme_id),
            ),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(choice.query_id),
        )


__all__ = ["IllustrationsCountingFeatureRelationObjectCountTask"]
