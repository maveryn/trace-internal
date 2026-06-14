"""Scene-local objective contracts for environment illustration count tasks."""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import Any, Dict, Mapping, Sequence, Tuple

from ...shared.config_defaults import group_default
from ...shared.deterministic_sampling import resolve_selection_index
from ..shared.task_support import uniform_string_probability_map
from ._lifecycle import BoundCountResult, EnvironmentChoice, EnvironmentCountPlan
from .shared.annotations import sort_bboxes_by_ids, target_feature
from .shared.prompts import required_environment_prompt_defaults
from .shared.rendering import effective_environment_object_count
from .shared.sampling import (
    FEATURE_TYPES_BY_THEME,
    environment_setting_name,
    global_feature_type_probabilities,
    int_bounds,
    sample_count_support,
    sample_object_count,
    theme_support,
)


RELATION_SUPPORT: Tuple[str, ...] = ("above", "below")
CROSSING_THEME_SUPPORT: Dict[str, Tuple[str, ...]] = {
    "bridge": ("river_meadow", "road_and_river", "canal_city"),
    "crosswalk": ("park_road", "road_and_river", "skyline_street"),
}
CROSSING_NAMES: Dict[str, str] = {"bridge": "bridges", "crosswalk": "crosswalks"}
CROSSED_FEATURE_NAMES: Dict[str, str] = {"bridge": "river", "crosswalk": "road"}
CITY_THEME_SUPPORT: Tuple[str, ...] = ("canal_city", "skyline_street")
WINDOW_MODE_SUPPORT: Tuple[str, ...] = ("lit",)


@dataclass(frozen=True)
class CountContractDefaults:
    """Default sampler/render ranges for one environment count contract."""

    object_count_min: int
    object_count_max: int
    target_count_min: int
    target_count_max: int
    canvas_width: int = 1280
    canvas_height: int = 840
    object_size_min_px: int = 62
    object_size_max_px: int = 116
    min_gap_px: int = 6
    max_overlap_fraction: float = 0.02
    placement_max_attempts: int = 420
    render_scale: int = 2
    skyline_building_min: int = 7
    skyline_building_max: int = 14


FEATURE_SIDE_DEFAULTS = CountContractDefaults(
    object_count_min=12,
    object_count_max=18,
    target_count_min=1,
    target_count_max=18,
)
ON_FEATURE_DEFAULTS = CountContractDefaults(
    object_count_min=12,
    object_count_max=18,
    target_count_min=2,
    target_count_max=7,
)
CROSSING_DEFAULTS = CountContractDefaults(
    object_count_min=12,
    object_count_max=18,
    target_count_min=1,
    target_count_max=5,
)
LIT_WINDOW_DEFAULTS = CountContractDefaults(
    object_count_min=8,
    object_count_max=14,
    target_count_min=1,
    target_count_max=10,
    object_size_min_px=58,
    object_size_max_px=108,
    skyline_building_min=4,
    skyline_building_max=7,
)


def render_fallback(defaults: CountContractDefaults) -> Dict[str, Any]:
    """Return render fallback values consumed by the shared lifecycle."""

    return {
        "canvas_width": int(defaults.canvas_width),
        "canvas_height": int(defaults.canvas_height),
        "object_size_min_px": int(defaults.object_size_min_px),
        "object_size_max_px": int(defaults.object_size_max_px),
        "min_gap_px": int(defaults.min_gap_px),
        "max_overlap_fraction": float(defaults.max_overlap_fraction),
        "placement_max_attempts": int(defaults.placement_max_attempts),
        "render_scale": int(defaults.render_scale),
        "skyline_building_min": int(defaults.skyline_building_min),
        "skyline_building_max": int(defaults.skyline_building_max),
    }


def sample_scene_object_count(
    params: Mapping[str, Any],
    instance_seed: int,
    _choice: EnvironmentChoice,
    generation_defaults: Mapping[str, Any],
    *,
    public_id: str,
    defaults: CountContractDefaults,
) -> Tuple[int, Dict[str, float]]:
    """Resolve the foreground clutter count independent of the answer count."""

    return sample_object_count(
        params,
        generation_defaults,
        fallback_min=int(defaults.object_count_min),
        fallback_max=int(defaults.object_count_max),
        instance_seed=int(instance_seed),
        namespace=f"{public_id}:object_count",
    )


def sample_target_count_by_keys(
    params: Mapping[str, Any],
    _instance_seed: int,
    choice: EnvironmentChoice,
    generation_defaults: Mapping[str, Any],
    *,
    low_key: str,
    high_key: str,
    defaults: CountContractDefaults,
) -> Tuple[int, Dict[str, float]]:
    """Sample the requested answer support from task-specific count bounds."""

    low, high = int_bounds(
        params,
        generation_defaults,
        low_key=str(low_key),
        high_key=str(high_key),
        fallback_low=int(defaults.target_count_min),
        fallback_high=int(defaults.target_count_max),
    )
    return sample_count_support(
        params=params,
        support=tuple(range(int(low), int(high) + 1)),
        explicit_key="target_count",
        cycle_index=int(choice.branch_index),
    )


def relation_support(params: Mapping[str, Any], generation_defaults: Mapping[str, Any]) -> Tuple[str, ...]:
    """Resolve the allowed side-relation operands for feature-side counts."""

    raw = params.get("relation_support", group_default(generation_defaults, "relation_support", RELATION_SUPPORT))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("relation_support must be a sequence")
    support = tuple(str(value) for value in raw if str(value) in set(RELATION_SUPPORT))
    if not support:
        raise ValueError("relation_support resolved no supported relations")
    return tuple(dict.fromkeys(support))


def resolve_feature_choice(
    instance_seed: int,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    *,
    public_id: str,
    include_relation: bool,
) -> EnvironmentChoice:
    """Resolve the sampled theme, road/river feature, and optional side relation.

    This contract binds only semantic operands that change the count predicate.
    Theme controls which road/river features can be rendered; relation is kept
    internal to the task contract and does not become a public query branch.
    """

    themes = theme_support(params, generation_defaults)
    branch_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{public_id}:cycle")
    explicit_theme = params.get("theme_id")
    if explicit_theme is not None:
        theme_id = str(explicit_theme)
        if theme_id not in set(themes):
            raise ValueError(f"theme_id must be one of {themes}")
        theme_probabilities = uniform_string_probability_map(themes, selected=theme_id)
    else:
        theme_id = str(themes[int(branch_index) % len(themes)])
        theme_probabilities = uniform_string_probability_map(themes)

    feature_values = FEATURE_TYPES_BY_THEME[str(theme_id)]
    explicit_feature = params.get("feature_type")
    if explicit_feature is not None:
        feature_type = str(explicit_feature)
        if feature_type not in set(feature_values):
            raise ValueError(f"feature_type {feature_type!r} is not available for theme {theme_id!r}")
        feature_probabilities = global_feature_type_probabilities(themes, selected=feature_type)
    else:
        feature_type = str(feature_values[int(branch_index // max(1, len(themes))) % len(feature_values)])
        feature_probabilities = global_feature_type_probabilities(themes)

    relation = None
    relation_probabilities = None
    if include_relation:
        relations = relation_support(params, generation_defaults)
        explicit_relation = params.get("relation")
        if explicit_relation is not None:
            relation = str(explicit_relation)
            if relation not in set(relations):
                raise ValueError(f"relation must be one of {relations}")
            relation_probabilities = uniform_string_probability_map(relations, selected=relation)
        else:
            relation = str(relations[int(branch_index // max(1, len(themes) * len(feature_values))) % len(relations)])
            relation_probabilities = uniform_string_probability_map(relations)

    return EnvironmentChoice(
        branch_index=int(branch_index),
        theme_id=str(theme_id),
        theme_probabilities=dict(theme_probabilities),
        feature_type=str(feature_type),
        feature_type_probabilities=dict(feature_probabilities),
        relation=relation,
        relation_probabilities=relation_probabilities,
    )


def feature_side_render_overrides(
    params: Mapping[str, Any],
    choice: EnvironmentChoice,
    requested_object_count: int,
    target_count: int,
) -> Dict[str, Any]:
    """Force enough objects onto the requested side without guaranteeing the final count by construction."""

    effective_count = effective_environment_object_count(str(choice.theme_id), int(requested_object_count))
    explicit_replay = any(
        key in params
        for key in ("object_count", "target_count", "target_count_min", "target_count_max")
    )
    placement_cap = 8 if explicit_replay else int(effective_count)
    target_zone = "land_above" if str(choice.relation) == "above" else "land_below"
    forced_side_count = max(1, min(int(target_count), int(effective_count), int(placement_cap)))
    return {"zone_count_overrides": {target_zone: int(forced_side_count)}}


def on_feature_render_overrides(
    _params: Mapping[str, Any],
    choice: EnvironmentChoice,
    _requested_object_count: int,
    target_count: int,
) -> Dict[str, Any]:
    """Place the exact answer objects in the queried road/river zone."""

    return {
        "bridge_count_override": 0,
        "crosswalk_count_override": 0,
        "zone_count_overrides": {str(choice.feature_type): int(target_count)},
    }


def counted_side_object_ids(*, scene: Any, feature_id: str, relation: str) -> Tuple[str, ...]:
    """Return foreground object ids whose trace relation matches the requested side."""

    ids = []
    for placement in scene.placements:
        relation_info = placement.relations.get(str(feature_id))
        if isinstance(relation_info, Mapping) and str(relation_info.get("vertical_relation")) == str(relation):
            ids.append(str(placement.object_id))
    return tuple(ids)


def bind_feature_side_result(
    scene: Any,
    choice: EnvironmentChoice,
    object_bboxes: Mapping[str, list[float]],
    _feature_bboxes: Mapping[str, list[float]],
    _target_count: int,
) -> BoundCountResult:
    """Bind feature-side witnesses from object-feature relations in the trace.

    The witness set is every foreground object whose projected center falls on
    the requested side of the selected road/river feature; the feature itself is
    context, so it is recorded in metadata but excluded from bbox evidence.
    """

    feature = target_feature(scene, str(choice.feature_type))
    counted_object_ids = counted_side_object_ids(
        scene=scene,
        feature_id=str(feature.feature_id),
        relation=str(choice.relation),
    )
    annotation_value = sort_bboxes_by_ids(object_bboxes, counted_object_ids)
    feature_name = "road" if choice.feature_type == "road" else "river"
    return BoundCountResult(
        answer=int(len(counted_object_ids)),
        annotation_value=list(annotation_value),
        render_map_extra={"counted_object_ids": list(counted_object_ids), "target_feature_id": str(feature.feature_id)},
        scene_relations={"feature_type": str(choice.feature_type), "feature_id": str(feature.feature_id), "relation": str(choice.relation)},
        execution_extra={
            "feature_type": str(choice.feature_type),
            "feature_id": str(feature.feature_id),
            "relation": str(choice.relation),
            "counted_object_ids": list(counted_object_ids),
            "object_zones": {placement.object_id: placement.zone_id for placement in scene.placements},
        },
        witness_symbolic={
            "counted_object_ids": list(counted_object_ids),
            "feature_id": str(feature.feature_id),
            "feature_type": str(choice.feature_type),
            "relation": str(choice.relation),
            "answer": int(len(counted_object_ids)),
        },
        query_params={
            "feature_type": str(choice.feature_type),
            "feature_id": str(feature.feature_id),
            "feature_name": str(feature_name),
            "relation": str(choice.relation),
            "feature_type_probabilities": dict(choice.feature_type_probabilities or {}),
            "relation_probabilities": dict(choice.relation_probabilities or {}),
        },
    )


def bind_on_feature_result(
    scene: Any,
    choice: EnvironmentChoice,
    object_bboxes: Mapping[str, list[float]],
    _feature_bboxes: Mapping[str, list[float]],
    target_count: int,
) -> BoundCountResult:
    """Bind exact foreground objects located on or in the selected feature.

    For this contract the renderer is forced to place an exact number of
    objects in the queried road/river zone, and the binder rejects samples where
    the rendered placement metadata no longer matches that target.
    """

    feature = target_feature(scene, str(choice.feature_type))
    counted_object_ids = tuple(
        str(placement.object_id)
        for placement in scene.placements
        if str(placement.zone_id) == str(choice.feature_type)
    )
    if len(counted_object_ids) != int(target_count):
        raise ValueError(f"on-feature count {len(counted_object_ids)} did not match target {target_count}")
    annotation_value = sort_bboxes_by_ids(object_bboxes, counted_object_ids)
    feature_phrase = "on the road" if choice.feature_type == "road" else "in or on the river"
    return BoundCountResult(
        answer=int(len(counted_object_ids)),
        annotation_value=list(annotation_value),
        render_map_extra={"counted_object_ids": list(counted_object_ids), "target_feature_id": str(feature.feature_id)},
        scene_relations={"feature_type": str(choice.feature_type), "feature_id": str(feature.feature_id)},
        execution_extra={
            "feature_type": str(choice.feature_type),
            "feature_id": str(feature.feature_id),
            "counted_object_ids": list(counted_object_ids),
            "object_zones": {placement.object_id: placement.zone_id for placement in scene.placements},
        },
        witness_symbolic={
            "counted_object_ids": list(counted_object_ids),
            "feature_id": str(feature.feature_id),
            "feature_type": str(choice.feature_type),
            "answer": int(len(counted_object_ids)),
        },
        query_params={
            "feature_type": str(choice.feature_type),
            "feature_id": str(feature.feature_id),
            "feature_phrase": str(feature_phrase),
            "feature_type_probabilities": dict(choice.feature_type_probabilities or {}),
        },
    )


def prompt_slots_feature_side(
    prompt_defaults: Mapping[str, Any],
    choice: EnvironmentChoice,
    _bound: BoundCountResult,
    _scene: Any,
    *,
    public_id: str,
) -> Dict[str, Any]:
    """Format prompt slots for a road/river side-count question."""

    defaults = required_environment_prompt_defaults(
        prompt_defaults,
        [
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "question_text_feature_side_object_count",
            "answer_hint_feature_side",
            "annotation_hint_feature_side",
            "json_example_feature_side",
            "json_example_answer_only_feature_side",
        ],
        context=f"prompt defaults for {public_id}",
    )
    feature_name = "road" if choice.feature_type == "road" else "river"
    return {
        "environment_setting": environment_setting_name(str(choice.theme_id)),
        "question_text": str(defaults["question_text_feature_side_object_count"]).format(
            relation_word=str(choice.relation),
            feature_name=str(feature_name),
        ),
        "json_output_contract": str(defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(defaults["json_output_contract_answer_only"]),
        "answer_hint": str(defaults["answer_hint_feature_side"]).format(relation_word=str(choice.relation), feature_name=str(feature_name)),
        "annotation_hint": str(defaults["annotation_hint_feature_side"]).format(relation_word=str(choice.relation), feature_name=str(feature_name)),
        "json_example": str(defaults["json_example_feature_side"]),
        "json_example_answer_only": str(defaults["json_example_answer_only_feature_side"]),
    }


def prompt_slots_on_feature(
    prompt_defaults: Mapping[str, Any],
    choice: EnvironmentChoice,
    _bound: BoundCountResult,
    _scene: Any,
    *,
    public_id: str,
) -> Dict[str, Any]:
    """Format prompt slots for an on-road/on-river foreground-object count."""

    defaults = required_environment_prompt_defaults(
        prompt_defaults,
        [
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "question_text_on_feature_object_count",
            "answer_hint_on_feature",
            "annotation_hint_on_feature",
            "json_example_on_feature",
            "json_example_answer_only_on_feature",
        ],
        context=f"prompt defaults for {public_id}",
    )
    feature_phrase = "on the road" if choice.feature_type == "road" else "in or on the river"
    return {
        "environment_setting": environment_setting_name(str(choice.theme_id)),
        "question_text": str(defaults["question_text_on_feature_object_count"]).format(feature_phrase=str(feature_phrase)),
        "json_output_contract": str(defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(defaults["json_output_contract_answer_only"]),
        "answer_hint": str(defaults["answer_hint_on_feature"]).format(feature_phrase=str(feature_phrase)),
        "annotation_hint": str(defaults["annotation_hint_on_feature"]).format(feature_phrase=str(feature_phrase)),
        "json_example": str(defaults["json_example_on_feature"]),
        "json_example_answer_only": str(defaults["json_example_answer_only_on_feature"]),
    }


def crossing_support(params: Mapping[str, Any], generation_defaults: Mapping[str, Any]) -> Tuple[str, ...]:
    """Resolve supported bridge/crosswalk operands for crossing counts."""

    raw = params.get(
        "crossing_type_support",
        group_default(generation_defaults, "crossing_type_support", tuple(CROSSING_THEME_SUPPORT)),
    )
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("crossing_type_support must be a sequence")
    support = tuple(str(value) for value in raw if str(value) in set(CROSSING_THEME_SUPPORT))
    if not support:
        raise ValueError("crossing_type_support resolved no supported crossing types")
    return tuple(dict.fromkeys(support))


def resolve_crossing_choice(
    instance_seed: int,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    *,
    public_id: str,
) -> EnvironmentChoice:
    """Resolve the crossing type and compatible environment theme.

    Crosswalks require road-capable themes and bridges require river-capable
    themes, so theme sampling is conditioned on the chosen crossing type while
    the marginal theme probabilities remain trace-visible.
    """

    crossing_values = crossing_support(params, generation_defaults)
    branch_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{public_id}:cycle")
    explicit_crossing = params.get("crossing_type")
    if explicit_crossing is not None:
        crossing_type = str(explicit_crossing)
        if crossing_type not in set(crossing_values):
            raise ValueError(f"crossing_type must be one of {crossing_values}")
        crossing_probabilities = uniform_string_probability_map(crossing_values, selected=crossing_type)
    else:
        crossing_type = str(crossing_values[int(branch_index) % len(crossing_values)])
        crossing_probabilities = uniform_string_probability_map(crossing_values)

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

    return EnvironmentChoice(
        branch_index=int(branch_index),
        theme_id=str(theme_id),
        theme_probabilities=dict(sorted(theme_probabilities.items())),
        crossing_type=str(crossing_type),
        crossing_type_probabilities=dict(crossing_probabilities),
    )


def crossing_render_overrides(
    _params: Mapping[str, Any],
    choice: EnvironmentChoice,
    _requested_object_count: int,
    target_count: int,
) -> Dict[str, Any]:
    """Force the queried crossing type to the sampled target count."""

    return {
        "bridge_count_override": int(target_count) if choice.crossing_type == "bridge" else None,
        "crosswalk_count_override": int(target_count) if choice.crossing_type == "crosswalk" else None,
    }


def bind_crossing_result(
    scene: Any,
    choice: EnvironmentChoice,
    _object_bboxes: Mapping[str, list[float]],
    feature_bboxes: Mapping[str, list[float]],
    target_count: int,
) -> BoundCountResult:
    """Bind bridge/crosswalk feature bboxes as the counted witnesses."""

    counted_feature_ids = tuple(
        str(item.feature_id)
        for item in scene.features
        if str(item.feature_type) == str(choice.crossing_type)
    )
    if len(counted_feature_ids) != int(target_count):
        raise ValueError(f"crossing count {len(counted_feature_ids)} did not match target {target_count}")
    crossing_name = CROSSING_NAMES[str(choice.crossing_type)]
    crossed_feature_name = CROSSED_FEATURE_NAMES[str(choice.crossing_type)]
    return BoundCountResult(
        answer=int(len(counted_feature_ids)),
        annotation_value=sort_bboxes_by_ids(feature_bboxes, counted_feature_ids),
        render_map_extra={"counted_feature_ids": list(counted_feature_ids)},
        scene_relations={"crossing_type": str(choice.crossing_type)},
        execution_extra={"crossing_type": str(choice.crossing_type), "counted_feature_ids": list(counted_feature_ids)},
        witness_symbolic={
            "counted_feature_ids": list(counted_feature_ids),
            "crossing_type": str(choice.crossing_type),
            "answer": int(len(counted_feature_ids)),
        },
        query_params={
            "crossing_type": str(choice.crossing_type),
            "crossing_name": str(crossing_name),
            "crossed_feature_name": str(crossed_feature_name),
            "crossing_type_probabilities": dict(choice.crossing_type_probabilities or {}),
        },
    )


def prompt_slots_crossing(
    prompt_defaults: Mapping[str, Any],
    choice: EnvironmentChoice,
    _bound: BoundCountResult,
    _scene: Any,
    *,
    public_id: str,
) -> Dict[str, Any]:
    """Format prompt slots for bridge/crosswalk feature-count questions."""

    defaults = required_environment_prompt_defaults(
        prompt_defaults,
        [
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "question_text_crossing_feature_count",
            "answer_hint_crossing_feature",
            "annotation_hint_crossing_feature",
            "json_example_crossing_feature",
            "json_example_answer_only_crossing_feature",
        ],
        context=f"prompt defaults for {public_id}",
    )
    crossing_name = CROSSING_NAMES[str(choice.crossing_type)]
    crossed_feature_name = CROSSED_FEATURE_NAMES[str(choice.crossing_type)]
    return {
        "environment_setting": environment_setting_name(str(choice.theme_id)),
        "question_text": str(defaults["question_text_crossing_feature_count"]).format(
            crossing_name=str(crossing_name),
            crossed_feature_name=str(crossed_feature_name),
        ),
        "json_output_contract": str(defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(defaults["json_output_contract_answer_only"]),
        "answer_hint": str(defaults["answer_hint_crossing_feature"]).format(crossing_name=str(crossing_name), crossed_feature_name=str(crossed_feature_name)),
        "annotation_hint": str(defaults["annotation_hint_crossing_feature"]).format(crossing_name=str(crossing_name), crossed_feature_name=str(crossed_feature_name)),
        "json_example": str(defaults["json_example_crossing_feature"]),
        "json_example_answer_only": str(defaults["json_example_answer_only_crossing_feature"]),
    }


def window_mode_support(params: Mapping[str, Any], generation_defaults: Mapping[str, Any]) -> Tuple[str, ...]:
    """Resolve supported building-window modes for the window count contract."""

    raw = params.get("window_mode_support", group_default(generation_defaults, "window_mode_support", WINDOW_MODE_SUPPORT))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("window_mode_support must be a sequence")
    supported = tuple(str(value) for value in raw if str(value) == "lit")
    if not supported:
        raise ValueError("window_mode_support resolved no supported modes")
    return tuple(dict.fromkeys(supported))


def resolve_window_choice(
    instance_seed: int,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    *,
    public_id: str,
) -> EnvironmentChoice:
    """Resolve a city theme and the fixed lit-window predicate."""

    themes = theme_support(params, generation_defaults, fallback=CITY_THEME_SUPPORT)
    themes = tuple(theme for theme in themes if theme in set(CITY_THEME_SUPPORT))
    if not themes:
        raise ValueError("lit-window count requires canal_city or skyline_street theme support")
    modes = window_mode_support(params, generation_defaults)
    branch_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{public_id}:cycle")

    explicit_theme = params.get("theme_id")
    if explicit_theme is not None:
        theme_id = str(explicit_theme)
        if theme_id not in set(themes):
            raise ValueError(f"theme_id must be one of {themes}")
        theme_probabilities = uniform_string_probability_map(themes, selected=theme_id)
    else:
        theme_id = str(themes[int(branch_index) % len(themes)])
        theme_probabilities = uniform_string_probability_map(themes)

    explicit_mode = params.get("window_mode")
    if explicit_mode is not None:
        window_mode = str(explicit_mode)
        if window_mode not in set(modes):
            raise ValueError(f"window_mode must be one of {modes}")
        window_mode_probabilities = uniform_string_probability_map(modes, selected=window_mode)
    else:
        window_mode = str(modes[int(branch_index // max(1, len(themes))) % len(modes)])
        window_mode_probabilities = uniform_string_probability_map(modes)

    return EnvironmentChoice(
        branch_index=int(branch_index),
        theme_id=str(theme_id),
        theme_probabilities=dict(theme_probabilities),
        window_mode=str(window_mode),
        window_mode_probabilities=dict(window_mode_probabilities),
    )


def window_render_overrides(
    _params: Mapping[str, Any],
    _choice: EnvironmentChoice,
    _requested_object_count: int,
    target_count: int,
) -> Dict[str, Any]:
    """Force the renderer to light exactly the sampled number of windows."""

    return {"lit_window_count_override": int(target_count)}


def window_bboxes(scene: Any, window_mode: str) -> Tuple[Tuple[str, list[float]], ...]:
    """Return lit-window bbox records keyed by stable building/window ids."""

    items = []
    for building in scene.buildings:
        for index, bbox in enumerate(building.lit_window_bboxes):
            items.append((f"{building.building_id}_{window_mode}_window_{index:02d}", [round(float(v), 3) for v in bbox]))
    return tuple(items)


def bind_window_result(
    scene: Any,
    choice: EnvironmentChoice,
    _object_bboxes: Mapping[str, list[float]],
    _feature_bboxes: Mapping[str, list[float]],
    target_count: int,
) -> BoundCountResult:
    """Bind lit-window boxes as minimal visual witnesses for building windows."""

    window_items = window_bboxes(scene, str(choice.window_mode))
    if len(window_items) != int(target_count):
        raise ValueError(f"rendered {len(window_items)} lit windows, expected {target_count}")
    window_bbox_map = {item_id: bbox for item_id, bbox in window_items}
    counted_window_ids = tuple(item_id for item_id, _bbox in window_items)
    return BoundCountResult(
        answer=int(len(counted_window_ids)),
        annotation_value=sort_bboxes_by_ids(window_bbox_map, counted_window_ids),
        render_map_extra={"window_bboxes_px": dict(window_bbox_map), "counted_window_ids": list(counted_window_ids)},
        scene_relations={"window_mode": str(choice.window_mode)},
        execution_extra={
            "window_mode": str(choice.window_mode),
            "building_count": int(len(scene.buildings)),
            "counted_window_ids": list(counted_window_ids),
        },
        witness_symbolic={
            "counted_window_ids": list(counted_window_ids),
            "window_mode": str(choice.window_mode),
            "answer": int(len(counted_window_ids)),
        },
        query_params={
            "window_mode": str(choice.window_mode),
            "window_phrase": "lit windows",
            "window_mode_probabilities": dict(choice.window_mode_probabilities or {}),
        },
    )


def prompt_slots_window(
    prompt_defaults: Mapping[str, Any],
    choice: EnvironmentChoice,
    _bound: BoundCountResult,
    _scene: Any,
    *,
    public_id: str,
) -> Dict[str, Any]:
    """Format prompt slots for the lit-window building-count contract."""

    defaults = required_environment_prompt_defaults(
        prompt_defaults,
        [
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "question_text_building_window_count",
            "answer_hint_building_window",
            "annotation_hint_building_window",
            "json_example_building_window",
            "json_example_answer_only_building_window",
        ],
        context=f"prompt defaults for {public_id}",
    )
    window_phrase = "lit windows"
    return {
        "environment_setting": environment_setting_name(str(choice.theme_id)),
        "question_text": str(defaults["question_text_building_window_count"]).format(window_phrase=str(window_phrase)),
        "json_output_contract": str(defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(defaults["json_output_contract_answer_only"]),
        "answer_hint": str(defaults["answer_hint_building_window"]).format(window_phrase=str(window_phrase)),
        "annotation_hint": str(defaults["annotation_hint_building_window"]).format(window_phrase=str(window_phrase)),
        "json_example": str(defaults["json_example_building_window"]),
        "json_example_answer_only": str(defaults["json_example_answer_only_building_window"]),
    }


def feature_side_plan(public_id: str, local_query_id: str, prompt_query_key: str) -> EnvironmentCountPlan:
    """Build the plan for counting objects on one side of a road/river."""

    return EnvironmentCountPlan(
        public_id=str(public_id),
        local_query_id=str(local_query_id),
        seed_namespace=f"{public_id}:scene",
        prompt_query_key=str(prompt_query_key),
        resolve_choice=partial(resolve_feature_choice, public_id=str(public_id), include_relation=True),
        object_count_sampler=partial(sample_scene_object_count, public_id=str(public_id), defaults=FEATURE_SIDE_DEFAULTS),
        target_count_sampler=partial(
            sample_target_count_by_keys,
            low_key="feature_side_target_count_min",
            high_key="feature_side_target_count_max",
            defaults=FEATURE_SIDE_DEFAULTS,
        ),
        render_overrides=feature_side_render_overrides,
        bind_result=bind_feature_side_result,
        prompt_slots=partial(prompt_slots_feature_side, public_id=str(public_id)),
        render_fallback=render_fallback(FEATURE_SIDE_DEFAULTS),
    )


def on_feature_plan(public_id: str, local_query_id: str, prompt_query_key: str) -> EnvironmentCountPlan:
    """Build the plan for counting foreground objects on a road/river."""

    return EnvironmentCountPlan(
        public_id=str(public_id),
        local_query_id=str(local_query_id),
        seed_namespace=f"{public_id}:scene",
        prompt_query_key=str(prompt_query_key),
        resolve_choice=partial(resolve_feature_choice, public_id=str(public_id), include_relation=False),
        object_count_sampler=partial(sample_scene_object_count, public_id=str(public_id), defaults=ON_FEATURE_DEFAULTS),
        target_count_sampler=partial(
            sample_target_count_by_keys,
            low_key="on_feature_target_count_min",
            high_key="on_feature_target_count_max",
            defaults=ON_FEATURE_DEFAULTS,
        ),
        render_overrides=on_feature_render_overrides,
        bind_result=bind_on_feature_result,
        prompt_slots=partial(prompt_slots_on_feature, public_id=str(public_id)),
        render_fallback=render_fallback(ON_FEATURE_DEFAULTS),
    )


def crossing_plan(public_id: str, local_query_id: str, prompt_query_key: str) -> EnvironmentCountPlan:
    """Build the plan for counting bridge/crosswalk features."""

    return EnvironmentCountPlan(
        public_id=str(public_id),
        local_query_id=str(local_query_id),
        seed_namespace=f"{public_id}:scene",
        prompt_query_key=str(prompt_query_key),
        resolve_choice=partial(resolve_crossing_choice, public_id=str(public_id)),
        object_count_sampler=partial(sample_scene_object_count, public_id=str(public_id), defaults=CROSSING_DEFAULTS),
        target_count_sampler=partial(
            sample_target_count_by_keys,
            low_key="crossing_target_count_min",
            high_key="crossing_target_count_max",
            defaults=CROSSING_DEFAULTS,
        ),
        render_overrides=crossing_render_overrides,
        bind_result=bind_crossing_result,
        prompt_slots=partial(prompt_slots_crossing, public_id=str(public_id)),
        render_fallback=render_fallback(CROSSING_DEFAULTS),
    )


def lit_window_plan(public_id: str, local_query_id: str) -> EnvironmentCountPlan:
    """Build the plan for counting lit building windows."""

    return EnvironmentCountPlan(
        public_id=str(public_id),
        local_query_id=str(local_query_id),
        seed_namespace=f"{public_id}:scene",
        prompt_query_key="building_window_count",
        resolve_choice=partial(resolve_window_choice, public_id=str(public_id)),
        object_count_sampler=partial(sample_scene_object_count, public_id=str(public_id), defaults=LIT_WINDOW_DEFAULTS),
        target_count_sampler=partial(
            sample_target_count_by_keys,
            low_key="target_count_min",
            high_key="target_count_max",
            defaults=LIT_WINDOW_DEFAULTS,
        ),
        render_overrides=window_render_overrides,
        bind_result=bind_window_result,
        prompt_slots=partial(prompt_slots_window, public_id=str(public_id)),
        render_fallback=render_fallback(LIT_WINDOW_DEFAULTS),
    )


__all__ = [
    "crossing_plan",
    "feature_side_plan",
    "lit_window_plan",
    "on_feature_plan",
]
