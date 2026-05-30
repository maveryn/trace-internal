"""Count Boolean combinations of prompt-named procedural icon shapes and colors."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.color_format import format_named_color_with_hex
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import uniform_probability_map
from ...shared.named_colors import available_named_colors, named_color
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.weighted_sampling import sample_weighted_value, weighted_probability_map
from ..shared.defaults import ICON_SHARED_DEFAULTS
from ..shared.evidence import bbox_set_evidence
from ..shared.icon_scene import sort_bboxes_reading_order
from ..shared.icon_task_rendering import icon_render_style_trace, resolve_icon_render_params, sample_icon_instance_noise
from ..shared.procedural_named_icon_field_scene import (
    SCENE_ID,
    NamedIconFieldSpec,
    render_procedural_named_icon_field_scene,
    serialize_named_icon_instance,
    resolve_named_icon_fill_style_probabilities,
    resolve_named_icon_fill_style_support,
    resolve_named_icon_int_bounds,
    rotation_for_named_shape,
    uniform_string_probability_map,
)
from ..shared.procedural_named_icons import (
    PROCEDURAL_NAMED_ICON_FILL_STYLES,
    PROCEDURAL_NAMED_ICON_SHAPES,
    QUERYABLE_PROCEDURAL_NAMED_ICON_FILL_STYLES,
    procedural_named_icon_display_name,
    procedural_named_icon_fill_style_display_name,
    procedural_named_icon_fill_style_probability_map,
    sample_procedural_named_icon_fill_style,
    validate_procedural_named_icon_fill_style_support,
)


TASK_ID = "task_icons__named_field__shape_attribute_boolean_count"

QUERY_IDS: Tuple[str, ...] = (
    "shape_and_color_count",
    "shape_or_color_count",
    "shape_and_not_color_count",
    "color_and_not_shape_count",
    "neither_shape_nor_color_count",
    "exactly_one_shape_or_color_count",
)

_ATTRIBUTE_AXES: Tuple[str, ...] = ("color", "fill_style")

_QUERY_EXPRESSION_TEMPLATES: Dict[str, str] = {
    "shape_and_color_count": "shape_id == target_shape_id AND {attribute_expression}",
    "shape_or_color_count": "shape_id == target_shape_id OR {attribute_expression}",
    "shape_and_not_color_count": "shape_id == target_shape_id AND NOT ({attribute_expression})",
    "color_and_not_shape_count": "{attribute_expression} AND shape_id != target_shape_id",
    "neither_shape_nor_color_count": "shape_id != target_shape_id AND NOT ({attribute_expression})",
    "exactly_one_shape_or_color_count": "(shape_id == target_shape_id) XOR ({attribute_expression})",
}

_NON_STACK_LAYOUT_MODES: Tuple[str, ...] = (
    "jittered_grid",
    "ordered_grid",
    "shelf_rows",
    "free_scatter",
)


@dataclass(frozen=True)
class _TaskDefaults:
    object_count_min: int = 8
    object_count_max: int = 20
    object_count_max_answer_offset: int = 10
    target_count_min: int = 1
    target_count_max: int = 6
    canvas_width: int = 800
    canvas_height: int = 480
    outer_margin_px: int = ICON_SHARED_DEFAULTS.outer_margin_px
    panel_padding_px: int = ICON_SHARED_DEFAULTS.panel_padding_px
    panel_corner_radius_px: int = ICON_SHARED_DEFAULTS.panel_corner_radius_px
    scene_icon_size_min_px: int = 48
    scene_icon_size_max_px: int = 96
    scene_max_overlap_fraction: float = 0.0
    scene_placement_max_attempts: int = ICON_SHARED_DEFAULTS.scene_placement_max_attempts
    scene_size_shrink_rounds: int = ICON_SHARED_DEFAULTS.scene_size_shrink_rounds
    scene_size_shrink_factor: float = ICON_SHARED_DEFAULTS.scene_size_shrink_factor
    panel_title_font_size_px: int = ICON_SHARED_DEFAULTS.panel_title_font_size_px
    reference_panel_width_px: int = ICON_SHARED_DEFAULTS.reference_panel_width_px
    reference_icon_size_px: int = ICON_SHARED_DEFAULTS.reference_icon_size_px
    panel_gap_px: int = ICON_SHARED_DEFAULTS.panel_gap_px
    palette_size_min: int = 8
    palette_size_max: int = 10
    color_channel_min: int = 24
    color_channel_max: int = 230
    min_color_distance: float = 40.0
    color_distance_space: str = "lab"
    background_color_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.background_color_rgb
    panel_fill_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_fill_rgb
    panel_border_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_border_rgb
    header_text_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.header_text_rgb
    icon_noise_edit_types: Tuple[str, ...] = ICON_SHARED_DEFAULTS.icon_noise_edit_types
    icon_noise_edit_count_range: Tuple[int, int] = ICON_SHARED_DEFAULTS.icon_noise_edit_count_range
    named_icon_layout_modes: Tuple[str, ...] = _NON_STACK_LAYOUT_MODES
    named_icon_slot_padding_px: int = 6
    named_icon_slot_jitter_px: int = 8
    named_icon_stack_gap_px: int = 1
    named_icon_fill_style_support: Tuple[str, ...] = PROCEDURAL_NAMED_ICON_FILL_STYLES
    queryable_named_icon_fill_style_support: Tuple[str, ...] = QUERYABLE_PROCEDURAL_NAMED_ICON_FILL_STYLES
    attribute_axis_probabilities: Dict[str, float] | None = None


@dataclass(frozen=True)
class _NamedColorEntry:
    name: str
    rgb: Tuple[int, int, int]
    label: str


@dataclass(frozen=True)
class _IconSemanticSpec:
    shape_id: str
    color_name: str
    fill_style: str
    partition: str


@dataclass(frozen=True)
class _SampleSpec:
    query_id: str
    target_shape_id: str
    target_shape_name: str
    target_attribute_axis: str
    target_attribute_value: str
    target_attribute_label: str
    target_color: _NamedColorEntry | None
    target_fill_style: str
    target_fill_style_label: str
    target_answer: int
    object_count: int
    object_count_max_answer_offset: int
    arrangement_mode: str
    partition_counts: Dict[str, int]
    semantic_specs: Tuple[_IconSemanticSpec, ...]
    query_probabilities: Dict[str, float]
    shape_probabilities: Dict[str, float]
    color_probabilities: Dict[str, float]
    fill_style_probabilities: Dict[str, float]
    attribute_axis_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    object_count_probabilities: Dict[str, float]
    arrangement_mode_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("icons", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)



def _int_param(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(key, group_default(_GEN_DEFAULTS, key, fallback)))


def _shape_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get("shape_id_support", group_default(_GEN_DEFAULTS, "shape_id_support", PROCEDURAL_NAMED_ICON_SHAPES))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("shape_id_support must be a sequence")
    values = tuple(str(value) for value in raw)
    unsupported = sorted(set(values) - set(PROCEDURAL_NAMED_ICON_SHAPES))
    if unsupported:
        raise ValueError(f"unsupported procedural named icon shapes: {unsupported}")
    support = tuple(dict.fromkeys(values))
    if len(support) < 2:
        raise ValueError("shape_id_support must include at least two shapes")
    return support


def _color_support(params: Mapping[str, Any]) -> Tuple[_NamedColorEntry, ...]:
    color_by_name = {
        str(name): tuple(int(channel) for channel in rgb)
        for name, rgb in available_named_colors()
    }
    raw = params.get("named_color_support", group_default(_GEN_DEFAULTS, "named_color_support", tuple(color_by_name)))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("named_color_support must be a sequence")
    names = tuple(dict.fromkeys(str(value).strip().lower() for value in raw if str(value).strip()))
    unsupported = sorted(set(names) - set(color_by_name))
    if unsupported:
        raise ValueError(f"unsupported named colors: {unsupported}")
    if len(names) < 2:
        raise ValueError("named_color_support must include at least two colors")
    return tuple(
        _NamedColorEntry(
            name=str(name),
            rgb=tuple(int(channel) for channel in named_color(str(name))),
            label=format_named_color_with_hex(str(name), named_color(str(name))),
        )
        for name in names
    )




def _attribute_axis_probability_map(params: Mapping[str, Any]) -> Dict[str, float]:
    raw = params.get(
        "attribute_axis_probabilities",
        group_default(_GEN_DEFAULTS, "attribute_axis_probabilities", {"color": 0.5, "fill_style": 0.5}),
    )
    if not isinstance(raw, Mapping):
        raw = {"color": 0.5, "fill_style": 0.5}
    weights = {
        str(axis): max(0.0, float(raw.get(str(axis), 0.0)))
        for axis in _ATTRIBUTE_AXES
    }
    total = sum(float(value) for value in weights.values())
    if total <= 0.0:
        raise ValueError("attribute_axis_probabilities must assign positive mass")
    return {str(axis): float(weights[str(axis)]) / float(total) for axis in _ATTRIBUTE_AXES}


def _sample_attribute_axis(params: Mapping[str, Any], rng) -> Tuple[str, Dict[str, float]]:
    explicit = params.get("attribute_axis")
    probabilities = _attribute_axis_probability_map(params)
    if explicit is not None:
        axis = str(explicit)
        if axis not in _ATTRIBUTE_AXES:
            raise ValueError(f"attribute_axis must be one of {_ATTRIBUTE_AXES}")
        return axis, {axis: 1.0}
    threshold = float(rng.random())
    cumulative = 0.0
    for axis in _ATTRIBUTE_AXES:
        cumulative += float(probabilities[str(axis)])
        if threshold <= cumulative:
            return str(axis), dict(probabilities)
    return str(_ATTRIBUTE_AXES[-1]), dict(probabilities)


def _query_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get("boolean_query_ids", group_default(_GEN_DEFAULTS, "boolean_query_ids", QUERY_IDS))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("boolean_query_ids must be a sequence")
    values = tuple(dict.fromkeys(str(value) for value in raw if str(value).strip()))
    unsupported = sorted(set(values) - set(QUERY_IDS))
    if unsupported:
        raise ValueError(f"unsupported Boolean named-icon query ids: {unsupported}")
    if not values:
        raise ValueError("boolean_query_ids resolved no query ids")
    return values


def _arrangement_mode_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get(
        "named_icon_layout_modes",
        group_default(_RENDER_DEFAULTS, "named_icon_layout_modes", _DEFAULTS.named_icon_layout_modes),
    )
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        values = _DEFAULTS.named_icon_layout_modes
    else:
        values = tuple(str(value) for value in raw if str(value).strip())
    unsupported = sorted(set(values) - set(_NON_STACK_LAYOUT_MODES))
    if unsupported:
        raise ValueError(f"Boolean named-icon counting only supports non-stack layouts; got {unsupported}")
    modes = tuple(dict.fromkeys(values))
    if not modes:
        raise ValueError("named_icon_layout_modes resolved no supported non-stack layouts")
    return modes



def _compose(total: int, buckets: int, rng, *, require_positive_if_possible: bool) -> Tuple[int, ...]:
    if buckets <= 0:
        return ()
    if total < 0:
        raise ValueError("cannot compose a negative total")
    if total == 0:
        return tuple(0 for _ in range(buckets))
    if require_positive_if_possible and total >= buckets:
        remaining = int(total) - int(buckets)
        values = [1 for _ in range(buckets)]
    else:
        remaining = int(total)
        values = [0 for _ in range(buckets)]
    for _ in range(int(remaining)):
        values[int(rng.randrange(0, int(buckets)))] += 1
    rng.shuffle(values)
    return tuple(int(value) for value in values)


def _predicate(query_id: str, *, is_shape: bool, is_attribute: bool) -> bool:
    if query_id == "shape_and_color_count":
        return bool(is_shape and is_attribute)
    if query_id == "shape_or_color_count":
        return bool(is_shape or is_attribute)
    if query_id == "shape_and_not_color_count":
        return bool(is_shape and not is_attribute)
    if query_id == "color_and_not_shape_count":
        return bool(is_attribute and not is_shape)
    if query_id == "neither_shape_nor_color_count":
        return bool((not is_shape) and (not is_attribute))
    if query_id == "exactly_one_shape_or_color_count":
        return bool(is_shape) ^ bool(is_attribute)
    raise ValueError(f"unsupported Boolean named-icon query id: {query_id}")


def _initial_partition_counts(query_id: str, target_answer: int, rng) -> Dict[str, int]:
    target = int(target_answer)
    if target < 1:
        raise ValueError("target_answer must be positive")
    if query_id == "shape_and_color_count":
        return {"both": target, "shape_only": 1, "attribute_only": 1, "neither": 1}
    if query_id == "shape_or_color_count":
        both, shape_only, attribute_only = _compose(target, 3, rng, require_positive_if_possible=True)
        return {"both": both, "shape_only": shape_only, "attribute_only": attribute_only, "neither": 1}
    if query_id == "shape_and_not_color_count":
        return {"both": 1, "shape_only": target, "attribute_only": 1, "neither": 1}
    if query_id == "color_and_not_shape_count":
        return {"both": 1, "shape_only": 1, "attribute_only": target, "neither": 1}
    if query_id == "neither_shape_nor_color_count":
        return {"both": 1, "shape_only": 1, "attribute_only": 1, "neither": target}
    if query_id == "exactly_one_shape_or_color_count":
        shape_only, attribute_only = _compose(target, 2, rng, require_positive_if_possible=True)
        return {"both": 1, "shape_only": shape_only, "attribute_only": attribute_only, "neither": 1}
    raise ValueError(f"unsupported Boolean named-icon query id: {query_id}")


def _safe_fill_partitions(query_id: str) -> Tuple[str, ...]:
    if query_id == "shape_and_color_count":
        return ("shape_only", "attribute_only", "neither")
    if query_id == "shape_or_color_count":
        return ("neither",)
    if query_id == "shape_and_not_color_count":
        return ("both", "attribute_only", "neither")
    if query_id == "color_and_not_shape_count":
        return ("both", "shape_only", "neither")
    if query_id == "neither_shape_nor_color_count":
        return ("both", "shape_only", "attribute_only")
    if query_id == "exactly_one_shape_or_color_count":
        return ("both", "neither")
    raise ValueError(f"unsupported Boolean named-icon query id: {query_id}")


def _answer_from_partitions(query_id: str, partition_counts: Mapping[str, int]) -> int:
    counts = {str(key): int(value) for key, value in partition_counts.items()}
    if query_id == "shape_and_color_count":
        return counts.get("both", 0)
    if query_id == "shape_or_color_count":
        return counts.get("both", 0) + counts.get("shape_only", 0) + counts.get("attribute_only", 0)
    if query_id == "shape_and_not_color_count":
        return counts.get("shape_only", 0)
    if query_id == "color_and_not_shape_count":
        return counts.get("attribute_only", 0)
    if query_id == "neither_shape_nor_color_count":
        return counts.get("neither", 0)
    if query_id == "exactly_one_shape_or_color_count":
        return counts.get("shape_only", 0) + counts.get("attribute_only", 0)
    raise ValueError(f"unsupported Boolean named-icon query id: {query_id}")


def _partition_counts_for_query(
    *,
    query_id: str,
    target_answer: int,
    object_count: int,
    rng,
) -> Dict[str, int]:
    counts = _initial_partition_counts(str(query_id), int(target_answer), rng)
    current_total = sum(int(value) for value in counts.values())
    if int(object_count) < int(current_total):
        raise ValueError("object_count leaves no room for required Boolean distractor partitions")
    fillable = _safe_fill_partitions(str(query_id))
    while current_total < int(object_count):
        counts[str(rng.choice(fillable))] += 1
        current_total += 1
    answer = _answer_from_partitions(str(query_id), counts)
    if answer != int(target_answer):
        raise RuntimeError("partition fill changed Boolean target answer")
    return {str(key): int(value) for key, value in counts.items()}


def _other_value(rng, values: Sequence[str], excluded: str) -> str:
    candidates = [str(value) for value in values if str(value) != str(excluded)]
    if not candidates:
        raise ValueError("no alternate value available")
    return str(rng.choice(candidates))


def _semantic_specs_from_partitions(
    *,
    partition_counts: Mapping[str, int],
    target_shape_id: str,
    target_color_name: str,
    target_fill_style: str,
    attribute_axis: str,
    shape_support: Sequence[str],
    color_support: Sequence[_NamedColorEntry],
    fill_style_support: Sequence[str],
    fill_style_probabilities: Dict[str, float],
    rng,
) -> Tuple[_IconSemanticSpec, ...]:
    color_names = tuple(str(entry.name) for entry in color_support)
    fill_styles = tuple(str(value) for value in fill_style_support)

    def build_spec(*, shape_matches: bool, attribute_matches: bool, partition: str) -> _IconSemanticSpec:
        shape_id = str(target_shape_id) if bool(shape_matches) else _other_value(rng, shape_support, str(target_shape_id))
        if str(attribute_axis) == "color":
            color_name = str(target_color_name) if bool(attribute_matches) else _other_value(rng, color_names, str(target_color_name))
            fill_style = sample_procedural_named_icon_fill_style(
                rng,
                support=fill_styles,
                probabilities=fill_style_probabilities,
            )
        elif str(attribute_axis) == "fill_style":
            color_name = str(rng.choice(color_names))
            fill_style = str(target_fill_style) if bool(attribute_matches) else _other_value(rng, fill_styles, str(target_fill_style))
        else:
            raise ValueError(f"unsupported attribute axis: {attribute_axis}")
        return _IconSemanticSpec(
            shape_id=str(shape_id),
            color_name=str(color_name),
            fill_style=str(fill_style),
            partition=str(partition),
        )

    specs: list[_IconSemanticSpec] = []
    for _ in range(int(partition_counts.get("both", 0))):
        specs.append(build_spec(shape_matches=True, attribute_matches=True, partition="both"))
    for _ in range(int(partition_counts.get("shape_only", 0))):
        specs.append(build_spec(shape_matches=True, attribute_matches=False, partition="shape_only"))
    for _ in range(int(partition_counts.get("attribute_only", 0))):
        specs.append(build_spec(shape_matches=False, attribute_matches=True, partition="attribute_only"))
    for _ in range(int(partition_counts.get("neither", 0))):
        specs.append(build_spec(shape_matches=False, attribute_matches=False, partition="neither"))
    rng.shuffle(specs)
    return tuple(specs)


def _sample_spec(*, instance_seed: int, params: Mapping[str, Any]) -> _SampleSpec:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}:sample")
    shape_support = _shape_support(params)
    color_support = _color_support(params)
    fill_style_support = resolve_named_icon_fill_style_support(params, _GEN_DEFAULTS, fallback_support=_DEFAULTS.named_icon_fill_style_support, queryable_only=False, queryable_fallback_support=_DEFAULTS.queryable_named_icon_fill_style_support)
    fill_style_probabilities = resolve_named_icon_fill_style_probabilities(params, _GEN_DEFAULTS, fill_style_support)
    queryable_fill_style_support = resolve_named_icon_fill_style_support(params, _GEN_DEFAULTS, fallback_support=_DEFAULTS.named_icon_fill_style_support, queryable_only=True, queryable_fallback_support=_DEFAULTS.queryable_named_icon_fill_style_support)
    query_support = _query_support(params)
    arrangement_support = _arrangement_mode_support(params)
    attribute_axis, attribute_axis_probabilities = _sample_attribute_axis(params, rng)
    answer_min, answer_max = resolve_named_icon_int_bounds(params, _GEN_DEFAULTS, "target_count_min", "target_count_max", _DEFAULTS.target_count_min, _DEFAULTS.target_count_max)
    object_min, object_max = resolve_named_icon_int_bounds(params, _GEN_DEFAULTS, "object_count_min", "object_count_max", _DEFAULTS.object_count_min, _DEFAULTS.object_count_max)
    object_max_answer_offset = _int_param(params, "object_count_max_answer_offset", _DEFAULTS.object_count_max_answer_offset)
    if answer_min < 1:
        raise ValueError("Boolean named-icon counting uses target_count_min >= 1")
    if object_max_answer_offset < 0:
        raise ValueError("object_count_max_answer_offset must be non-negative")

    explicit_query = params.get("query_id", params.get("boolean_query_id"))
    if explicit_query is not None:
        query_id = str(explicit_query)
        if query_id not in query_support:
            raise ValueError(f"query_id must be one of {query_support}")
    else:
        query_id = str(rng.choice(query_support))

    answer_support = tuple(range(int(answer_min), int(answer_max) + 1))
    target_count_probabilities = weighted_probability_map(
        answer_support,
        params.get("target_count_weights", group_default(_GEN_DEFAULTS, "target_count_weights", None)),
    )
    explicit_target = params.get("target_count", params.get("target_answer"))
    if explicit_target is not None:
        target_answer = int(explicit_target)
        if target_answer not in set(answer_support):
            raise ValueError(f"target_count must be in {answer_support}")
    else:
        target_answer = int(sample_weighted_value(rng, answer_support, target_count_probabilities))

    explicit_shape = params.get("shape_id", params.get("target_shape_id"))
    if explicit_shape is not None:
        target_shape_id = str(explicit_shape)
        if target_shape_id not in set(shape_support):
            raise ValueError(f"target shape must be one of {shape_support}")
    else:
        target_shape_id = str(rng.choice(shape_support))

    color_by_name = {str(entry.name): entry for entry in color_support}
    explicit_color = params.get("color_name", params.get("target_color_name"))
    explicit_fill_style = params.get("fill_style", params.get("target_fill_style"))
    target_color: _NamedColorEntry | None = None
    target_fill_style = ""
    if str(attribute_axis) == "color":
        if explicit_color is not None:
            target_color_name = str(explicit_color).strip().lower()
            if target_color_name not in color_by_name:
                raise ValueError(f"target color must be one of {tuple(color_by_name)}")
        else:
            target_color_name = str(rng.choice(color_support).name)
        target_color = color_by_name[str(target_color_name)]
        target_attribute_value = str(target_color.name)
        target_attribute_label = str(target_color.label)
        target_fill_style = ""
    else:
        if explicit_fill_style is not None:
            target_fill_style = str(explicit_fill_style).strip()
            if target_fill_style not in set(queryable_fill_style_support):
                raise ValueError(f"target fill style must be one of {queryable_fill_style_support}")
        else:
            target_fill_style = str(rng.choice(queryable_fill_style_support))
        target_attribute_value = str(target_fill_style)
        target_attribute_label = procedural_named_icon_fill_style_display_name(str(target_fill_style))

    min_required_counts = _initial_partition_counts(str(query_id), int(target_answer), rng)
    min_required_total = sum(int(value) for value in min_required_counts.values())
    min_object_count = max(int(object_min), int(min_required_total))
    answer_relative_object_max = int(target_answer) + int(object_max_answer_offset)
    dynamic_object_max = min(int(object_max), max(int(min_required_total), int(answer_relative_object_max)))
    if min_object_count > int(dynamic_object_max):
        raise ValueError("object_count range cannot support requested Boolean target")
    object_support = tuple(range(int(min_object_count), int(dynamic_object_max) + 1))
    explicit_object_count = params.get("object_count")
    if explicit_object_count is not None:
        object_count = int(explicit_object_count)
        if object_count < int(min_object_count) or object_count > int(dynamic_object_max):
            raise ValueError("object_count is outside configured support")
    else:
        object_count = int(rng.choice(object_support))

    partition_counts = _partition_counts_for_query(
        query_id=str(query_id),
        target_answer=int(target_answer),
        object_count=int(object_count),
        rng=rng,
    )
    semantic_specs = _semantic_specs_from_partitions(
        partition_counts=partition_counts,
        target_shape_id=str(target_shape_id),
        target_color_name=str(target_color.name) if target_color is not None else "",
        target_fill_style=str(target_fill_style),
        attribute_axis=str(attribute_axis),
        shape_support=shape_support,
        color_support=color_support,
        fill_style_support=fill_style_support,
        fill_style_probabilities=fill_style_probabilities,
        rng=rng,
    )

    explicit_arrangement = params.get("arrangement_mode", params.get("layout_mode"))
    if explicit_arrangement is not None:
        arrangement_mode = str(explicit_arrangement)
        if arrangement_mode not in set(arrangement_support):
            raise ValueError(f"Boolean named-icon counting only supports non-stack layouts: {arrangement_support}")
    else:
        arrangement_mode = str(rng.choice(arrangement_support))

    return _SampleSpec(
        query_id=str(query_id),
        target_shape_id=str(target_shape_id),
        target_shape_name=procedural_named_icon_display_name(str(target_shape_id)),
        target_attribute_axis=str(attribute_axis),
        target_attribute_value=str(target_attribute_value),
        target_attribute_label=str(target_attribute_label),
        target_color=target_color,
        target_fill_style=str(target_fill_style),
        target_fill_style_label=procedural_named_icon_fill_style_display_name(str(target_fill_style)) if target_fill_style else "",
        target_answer=int(target_answer),
        object_count=int(object_count),
        object_count_max_answer_offset=int(object_max_answer_offset),
        arrangement_mode=str(arrangement_mode),
        partition_counts=dict(partition_counts),
        semantic_specs=tuple(semantic_specs),
        query_probabilities=uniform_string_probability_map(query_support, selected=str(query_id) if explicit_query is not None else None),
        shape_probabilities=uniform_string_probability_map(shape_support, selected=str(target_shape_id) if explicit_shape is not None else None),
        color_probabilities=uniform_string_probability_map(tuple(color_by_name), selected=str(target_color.name) if explicit_color is not None and target_color is not None else None),
        fill_style_probabilities=dict(fill_style_probabilities),
        attribute_axis_probabilities=dict(attribute_axis_probabilities),
        target_count_probabilities=dict(uniform_probability_map(answer_support, selected=int(target_answer)) if explicit_target is not None else target_count_probabilities),
        object_count_probabilities=dict(uniform_probability_map(object_support, selected=int(object_count) if explicit_object_count is not None else None)),
        arrangement_mode_probabilities=uniform_string_probability_map(arrangement_support, selected=str(arrangement_mode) if explicit_arrangement is not None else None),
    )



def _build_scene_specs(
    *,
    sample: _SampleSpec,
    instance_seed: int,
    render_params: Mapping[str, Any],
    rng,
) -> Tuple[Tuple[NamedIconFieldSpec, ...], Tuple[Tuple[int, int, int], ...]]:
    color_by_name = {str(name): tuple(int(channel) for channel in rgb) for name, rgb in available_named_colors()}
    min_size = max(12, int(render_params["scene_icon_size_min_px"]))
    max_size = max(min_size, int(render_params["scene_icon_size_max_px"]))
    specs: list[NamedIconFieldSpec] = []
    for index, semantic_spec in enumerate(sample.semantic_specs):
        color_name = str(semantic_spec.color_name)
        tint_rgb = tuple(int(channel) for channel in color_by_name[str(color_name)])
        noise_edits, noise_seed = sample_icon_instance_noise(
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:named_icon_{int(index)}",
            render_params=render_params,
        )
        specs.append(
            NamedIconFieldSpec(
                shape_id=str(semantic_spec.shape_id),
                tint_rgb=tint_rgb,
                color_name=str(color_name),
                fill_style=str(semantic_spec.fill_style),
                nominal_size_px=int(rng.randint(int(min_size), int(max_size))),
                rotation_degrees=rotation_for_named_shape(rng, str(semantic_spec.shape_id)),
                placement_group="",
                noise_edits=tuple(noise_edits),
                noise_seed=int(noise_seed),
            )
        )
    sampled_palette_rgb = tuple(tuple(int(channel) for channel in rgb) for _name, rgb in available_named_colors())
    return tuple(specs), sampled_palette_rgb


def _attribute_matches(sample: _SampleSpec, instance: Any) -> bool:
    if str(sample.target_attribute_axis) == "color":
        if sample.target_color is None:
            raise RuntimeError("color-axis sample is missing target_color")
        return str(instance.color_name) == str(sample.target_color.name)
    if str(sample.target_attribute_axis) == "fill_style":
        return str(instance.fill_style) == str(sample.target_fill_style)
    raise ValueError(f"unsupported attribute axis: {sample.target_attribute_axis}")


def _counted_instance_ids(sample: _SampleSpec, instances: Sequence[Any]) -> Tuple[str, ...]:
    return tuple(
        str(instance.instance_id)
        for instance in instances
        if _predicate(
            str(sample.query_id),
            is_shape=str(instance.shape_id) == str(sample.target_shape_id),
            is_attribute=_attribute_matches(sample, instance),
        )
    )


def _evidence_bboxes(sample: _SampleSpec, instances: Sequence[Any]) -> list[list[int]]:
    return sort_bboxes_reading_order(
        tuple(
            instance.bbox_xyxy
            for instance in instances
            if _predicate(
                str(sample.query_id),
                is_shape=str(instance.shape_id) == str(sample.target_shape_id),
                is_attribute=_attribute_matches(sample, instance),
            )
        )
    )


def _complexity(sample: _SampleSpec, *, render_params: Mapping[str, Any]) -> TaskComplexity:
    visual_scan = (int(sample.object_count) - _DEFAULTS.object_count_min) / max(1, _DEFAULTS.object_count_max - _DEFAULTS.object_count_min)
    answer_load = (int(sample.target_answer) - _DEFAULTS.target_count_min) / max(1, _DEFAULTS.target_count_max - _DEFAULTS.target_count_min)
    logic_difficulty = {
        "shape_and_color_count": 0.35,
        "shape_and_not_color_count": 0.50,
        "color_and_not_shape_count": 0.50,
        "shape_or_color_count": 0.60,
        "neither_shape_nor_color_count": 0.70,
        "exactly_one_shape_or_color_count": 0.75,
    }[str(sample.query_id)]
    shape_diversity = len(set(spec.shape_id for spec in sample.semantic_specs)) / max(1.0, float(sample.object_count))
    color_diversity = len(set(spec.color_name for spec in sample.semantic_specs)) / max(1.0, float(sample.object_count))
    fill_style_diversity = len(set(spec.fill_style for spec in sample.semantic_specs)) / max(1.0, float(sample.object_count))
    attribute_diversity = color_diversity if str(sample.target_attribute_axis) == "color" else fill_style_diversity
    attribute_axis_difficulty = 0.10 if str(sample.target_attribute_axis) == "fill_style" else 0.0
    score = (
        0.30 * max(0.0, min(1.0, visual_scan))
        + 0.20 * max(0.0, min(1.0, answer_load))
        + 0.22 * float(logic_difficulty)
        + 0.15 * max(0.0, min(1.0, shape_diversity))
        + 0.10 * max(0.0, min(1.0, attribute_diversity))
        + 0.03 * float(attribute_axis_difficulty)
    )
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={
            "visual_scan": round(float(visual_scan), 6),
            "answer_load": round(float(answer_load), 6),
            "logic_difficulty": round(float(logic_difficulty), 6),
            "shape_diversity": round(float(shape_diversity), 6),
            "color_diversity": round(float(color_diversity), 6),
            "fill_style_diversity": round(float(fill_style_diversity), 6),
            "attribute_diversity": round(float(attribute_diversity), 6),
            "attribute_axis_difficulty": round(float(attribute_axis_difficulty), 6),
            "object_count": int(sample.object_count),
            "target_answer": int(sample.target_answer),
            "query_id": str(sample.query_id),
            "target_shape_id": str(sample.target_shape_id),
            "target_attribute_axis": str(sample.target_attribute_axis),
            "target_attribute_value": str(sample.target_attribute_value),
            "target_color_name": str(sample.target_color.name) if sample.target_color is not None else "",
            "target_fill_style": str(sample.target_fill_style),
            "arrangement_mode": str(sample.arrangement_mode),
            "scene_icon_size_min_px": int(render_params["scene_icon_size_min_px"]),
            "scene_icon_size_max_px": int(render_params["scene_icon_size_max_px"]),
        },
    )


def _attribute_phrase(sample: _SampleSpec) -> str:
    if str(sample.target_attribute_axis) == "color":
        return f"the color {sample.target_attribute_label}"
    if str(sample.target_attribute_axis) == "fill_style":
        return f"a {sample.target_attribute_label} fill style"
    raise ValueError(f"unsupported attribute axis: {sample.target_attribute_axis}")


def _attribute_expression(sample: _SampleSpec) -> str:
    if str(sample.target_attribute_axis) == "color":
        return "color_name == target_color_name"
    if str(sample.target_attribute_axis) == "fill_style":
        return "fill_style == target_fill_style"
    raise ValueError(f"unsupported attribute axis: {sample.target_attribute_axis}")


def _query_expression(sample: _SampleSpec) -> str:
    template = str(_QUERY_EXPRESSION_TEMPLATES[str(sample.query_id)])
    return template.format(attribute_expression=_attribute_expression(sample))


@register_task
class IconsCountingNamedShapeColorBooleanCountTask:
    """Count named shape plus color-or-fill-style Boolean predicates in a single icon field."""

    task_id = TASK_ID
    domain = "icons"
    task_group = "counting"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        last_error: Exception | None = None
        sample: _SampleSpec | None = None
        scene = None
        sampled_palette_rgb: Tuple[Tuple[int, int, int], ...] = ()
        render_params = resolve_icon_render_params(
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            fallback_defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        slot_padding_px = int(
            params.get(
                "named_icon_slot_padding_px",
                group_default(_RENDER_DEFAULTS, "named_icon_slot_padding_px", _DEFAULTS.named_icon_slot_padding_px),
            )
        )
        slot_jitter_px = int(
            params.get(
                "named_icon_slot_jitter_px",
                group_default(_RENDER_DEFAULTS, "named_icon_slot_jitter_px", _DEFAULTS.named_icon_slot_jitter_px),
            )
        )
        stack_gap_px = int(
            params.get(
                "named_icon_stack_gap_px",
                group_default(_RENDER_DEFAULTS, "named_icon_stack_gap_px", _DEFAULTS.named_icon_stack_gap_px),
            )
        )
        for attempt in range(max(1, int(max_attempts))):
            try:
                sample = _sample_spec(instance_seed=int(instance_seed), params=params)
                scene_rng = spawn_rng(int(instance_seed), f"{TASK_ID}:scene", int(attempt))
                icon_specs, sampled_palette_rgb = _build_scene_specs(
                    sample=sample,
                    instance_seed=int(instance_seed),
                    render_params=render_params,
                    rng=scene_rng,
                )
                scene = render_procedural_named_icon_field_scene(
                    rng=scene_rng,
                    instance_seed=int(instance_seed),
                    task_id=self.task_id,
                    icon_specs=icon_specs,
                    render_params=render_params,
                    layout_modes=(str(sample.arrangement_mode),),
                    slot_padding_px=int(slot_padding_px),
                    slot_jitter_px=int(slot_jitter_px),
                    stack_gap_px=int(stack_gap_px),
                )
                break
            except Exception as exc:  # pragma: no cover - exercised through smoke tests.
                last_error = exc
                sample = None
                scene = None
        if scene is None or sample is None:
            raise RuntimeError(f"could not generate {TASK_ID}: {last_error}") from last_error

        evidence_bboxes = _evidence_bboxes(sample, scene.instances)
        if len(evidence_bboxes) != int(sample.target_answer):
            raise RuntimeError("rendered Boolean named-icon count did not match target answer")
        evidence_artifacts = bbox_set_evidence(evidence_bboxes)

        question_key = f"question_text_{sample.query_id}"
        attribute_phrase = _attribute_phrase(sample)
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                question_key,
                "evidence_hint",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "question_text": str(prompt_defaults[question_key]).format(
                    shape_name=str(sample.target_shape_name),
                    color_label=str(sample.target_attribute_label),
                    attribute_phrase=str(attribute_phrase),
                ),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]).format(
                    shape_name=str(sample.target_shape_name),
                    color_label=str(sample.target_attribute_label),
                    attribute_phrase=str(attribute_phrase),
                ),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        serialized_instances = [serialize_named_icon_instance(instance) for instance in scene.instances]
        shape_counts = Counter(str(instance.shape_id) for instance in scene.instances)
        color_counts = Counter(str(instance.color_name) for instance in scene.instances)
        fill_style_counts = Counter(str(instance.fill_style) for instance in scene.instances)
        attribute_counts = color_counts if str(sample.target_attribute_axis) == "color" else fill_style_counts
        shape_attribute_counts = Counter(
            f"{instance.shape_id}|{instance.color_name if str(sample.target_attribute_axis) == 'color' else instance.fill_style}"
            for instance in scene.instances
        )
        counted_instance_ids = _counted_instance_ids(sample, scene.instances)
        entity_partition = {
            str(instance.instance_id): (
                "both"
                if str(instance.shape_id) == str(sample.target_shape_id) and _attribute_matches(sample, instance)
                else "shape_only"
                if str(instance.shape_id) == str(sample.target_shape_id)
                else "attribute_only"
                if _attribute_matches(sample, instance)
                else "neither"
            )
            for instance in scene.instances
        }
        query_expression = _query_expression(sample)
        trace_payload = {
            "scene_ir": {
                "scene_kind": "icons_named_shape_color_field",
                "scene_id": SCENE_ID,
                "entities": list(serialized_instances),
                "relations": {
                    "counting_rule": str(query_expression),
                    "target_shape_id": str(sample.target_shape_id),
                    "target_shape_name": str(sample.target_shape_name),
                    "target_attribute_axis": str(sample.target_attribute_axis),
                    "target_attribute_value": str(sample.target_attribute_value),
                    "target_attribute_label": str(sample.target_attribute_label),
                    "target_color_name": str(sample.target_color.name) if sample.target_color is not None else "",
                    "target_color_rgb": [int(channel) for channel in sample.target_color.rgb] if sample.target_color is not None else [],
                    "target_color_label": str(sample.target_color.label) if sample.target_color is not None else "",
                    "target_fill_style": str(sample.target_fill_style),
                    "target_fill_style_label": str(sample.target_fill_style_label),
                    "shape_counts": {str(key): int(value) for key, value in shape_counts.items()},
                    "color_counts": {str(key): int(value) for key, value in color_counts.items()},
                    "fill_style_counts": {str(key): int(value) for key, value in fill_style_counts.items()},
                    "attribute_counts": {str(key): int(value) for key, value in attribute_counts.items()},
                    "shape_attribute_counts": {str(key): int(value) for key, value in shape_attribute_counts.items()},
                    "partition_counts": {str(key): int(value) for key, value in sample.partition_counts.items()},
                    "arrangement_mode": str(sample.arrangement_mode),
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(scene.panel_geometry),
                },
            },
            "query_spec": {
                "query_id": str(sample.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "target_shape_id": str(sample.target_shape_id),
                    "target_shape_name": str(sample.target_shape_name),
                    "target_attribute_axis": str(sample.target_attribute_axis),
                    "target_attribute_value": str(sample.target_attribute_value),
                    "target_attribute_label": str(sample.target_attribute_label),
                    "target_color_name": str(sample.target_color.name) if sample.target_color is not None else "",
                    "target_color_rgb": [int(channel) for channel in sample.target_color.rgb] if sample.target_color is not None else [],
                    "target_color_label": str(sample.target_color.label) if sample.target_color is not None else "",
                    "target_fill_style": str(sample.target_fill_style),
                    "target_fill_style_label": str(sample.target_fill_style_label),
                    "target_answer": int(sample.target_answer),
                    "object_count": int(sample.object_count),
                    "object_count_max_answer_offset": int(sample.object_count_max_answer_offset),
                    "query_id": str(sample.query_id),
                    "boolean_expression": str(query_expression),
                    "partition_counts": {str(key): int(value) for key, value in sample.partition_counts.items()},
                    "arrangement_mode": str(sample.arrangement_mode),
                    "arrangement_mode_probabilities": dict(sample.arrangement_mode_probabilities),
                    "shape_id_support": list(_shape_support(params)),
                    "named_color_support": [str(entry.name) for entry in _color_support(params)],
                    "named_icon_fill_style_support": list(resolve_named_icon_fill_style_support(params, _GEN_DEFAULTS, fallback_support=_DEFAULTS.named_icon_fill_style_support, queryable_only=False, queryable_fallback_support=_DEFAULTS.queryable_named_icon_fill_style_support)),
                    "queryable_named_icon_fill_style_support": list(resolve_named_icon_fill_style_support(params, _GEN_DEFAULTS, fallback_support=_DEFAULTS.named_icon_fill_style_support, queryable_only=True, queryable_fallback_support=_DEFAULTS.queryable_named_icon_fill_style_support)),
                    "query_probabilities": dict(sample.query_probabilities),
                    "shape_probabilities": dict(sample.shape_probabilities),
                    "color_probabilities": dict(sample.color_probabilities),
                    "fill_style_probabilities": dict(sample.fill_style_probabilities),
                    "attribute_axis_probabilities": dict(sample.attribute_axis_probabilities),
                    "target_count_probabilities": dict(sample.target_count_probabilities),
                    "object_count_probabilities": dict(sample.object_count_probabilities),
                },
            },
            "render_spec": {
                "canvas_size": list(scene.panel_geometry["canvas_size"]),
                "coord_space": "pixel",
                "scene_id": SCENE_ID,
                "panel_geometry": dict(scene.panel_geometry),
                "style": {
                    **icon_render_style_trace(render_params=render_params, sampled_palette_rgb=sampled_palette_rgb),
                    "layout_mode": str(scene.layout_mode),
                    "named_icon_slot_padding_px": int(slot_padding_px),
                    "named_icon_slot_jitter_px": int(slot_jitter_px),
                    "named_icon_stack_gap_px": int(stack_gap_px),
                    "semantic_color_palette": [
                        {
                            "name": str(name),
                            "rgb": [int(channel) for channel in rgb],
                            "label": format_named_color_with_hex(str(name), rgb),
                        }
                        for name, rgb in available_named_colors()
                    ],
                    "semantic_fill_style_support": list(resolve_named_icon_fill_style_support(params, _GEN_DEFAULTS, fallback_support=_DEFAULTS.named_icon_fill_style_support, queryable_only=False, queryable_fallback_support=_DEFAULTS.queryable_named_icon_fill_style_support)),
                    "queryable_semantic_fill_style_support": list(resolve_named_icon_fill_style_support(params, _GEN_DEFAULTS, fallback_support=_DEFAULTS.named_icon_fill_style_support, queryable_only=True, queryable_fallback_support=_DEFAULTS.queryable_named_icon_fill_style_support)),
                },
            },
            "render_map": {
                "image_id": "img0",
                "object_bboxes_px": {
                    str(instance.instance_id): [int(value) for value in instance.bbox_xyxy]
                    for instance in scene.instances
                },
                "counted_instance_ids": list(counted_instance_ids),
                "entity_partition": dict(entity_partition),
            },
            "execution_trace": {
                "scene_variant": "single_panel_named_shape_color_field",
                "arrangement_mode": str(sample.arrangement_mode),
                "query_id": str(sample.query_id),
                "question_format": "count_named_shape_color_boolean_icons",
                "target_shape_id": str(sample.target_shape_id),
                "target_shape_name": str(sample.target_shape_name),
                "target_attribute_axis": str(sample.target_attribute_axis),
                "target_attribute_value": str(sample.target_attribute_value),
                "target_attribute_label": str(sample.target_attribute_label),
                "target_color_name": str(sample.target_color.name) if sample.target_color is not None else "",
                "target_color_rgb": [int(channel) for channel in sample.target_color.rgb] if sample.target_color is not None else [],
                "target_color_label": str(sample.target_color.label) if sample.target_color is not None else "",
                "target_fill_style": str(sample.target_fill_style),
                "target_fill_style_label": str(sample.target_fill_style_label),
                "target_answer": int(sample.target_answer),
                "object_count": int(sample.object_count),
                "boolean_expression": str(query_expression),
                "partition_counts": {str(key): int(value) for key, value in sample.partition_counts.items()},
                "shape_counts": {str(key): int(value) for key, value in shape_counts.items()},
                "color_counts": {str(key): int(value) for key, value in color_counts.items()},
                "fill_style_counts": {str(key): int(value) for key, value in fill_style_counts.items()},
                "attribute_counts": {str(key): int(value) for key, value in attribute_counts.items()},
                "shape_attribute_counts": {str(key): int(value) for key, value in shape_attribute_counts.items()},
                "scene_shape_ids": [str(instance.shape_id) for instance in scene.instances],
                "scene_color_names": [str(instance.color_name) for instance in scene.instances],
                "scene_fill_styles": [str(instance.fill_style) for instance in scene.instances],
                "counted_instance_ids": list(counted_instance_ids),
            },
            "witness_symbolic": {
                "target_shape_id": str(sample.target_shape_id),
                "target_shape_name": str(sample.target_shape_name),
                "target_attribute_axis": str(sample.target_attribute_axis),
                "target_attribute_value": str(sample.target_attribute_value),
                "target_attribute_label": str(sample.target_attribute_label),
                "target_color_name": str(sample.target_color.name) if sample.target_color is not None else "",
                "target_color_label": str(sample.target_color.label) if sample.target_color is not None else "",
                "target_fill_style": str(sample.target_fill_style),
                "target_fill_style_label": str(sample.target_fill_style_label),
                "answer": int(sample.target_answer),
                "counted_instance_ids": list(counted_instance_ids),
            },
            "projected_evidence": {
                **dict(evidence_artifacts["projected_evidence"]),
            },
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(sample.target_answer)),
            evidence_gt=TypedValue(
                type=str(evidence_artifacts["evidence_type"]),
                value=list(evidence_artifacts["evidence_value"]),
            ),
            image=scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_complexity(sample, render_params=render_params),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(sample.query_id),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
        )


__all__ = ["IconsCountingNamedShapeColorBooleanCountTask"]
