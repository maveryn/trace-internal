"""Neutral materialization helpers for named-field icon tasks.

Public task files own task ids, public query ids, objective selection, and
final ``TaskOutput`` construction. This module only materializes task-owned
semantic plans into rendered named-field scenes and trace fragments.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Mapping, Sequence, Tuple

from .....core.seed import spawn_rng
from .....core.types import TypedValue
from ....shared.color_format import format_named_color_with_hex
from ....shared.config_defaults import (
    group_default,
    required_group_defaults,
)
from ....shared.deterministic_sampling import uniform_probability_map
from ....shared.named_colors import available_named_colors, named_color
from ....shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ....shared.weighted_sampling import sample_weighted_value, weighted_probability_map
from ...shared.annotation import bbox_set_annotation
from ...shared.icon_scene import sort_bboxes_reading_order
from ...shared.icon_style import sample_icon_palette
from ...shared.icon_task_rendering import (
    icon_render_style_trace,
    resolve_icon_render_params,
    sample_icon_instance_noise,
)
from ...shared.procedural_named_icon_field_scene import (
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
from ...shared.procedural_named_icons import (
    PROCEDURAL_NAMED_ICON_SHAPES,
    procedural_named_icon_display_name,
    procedural_named_icon_fill_style_display_name,
    sample_procedural_named_icon_fill_style,
)
from .defaults import (
    BOOLEAN_DEFAULTS as _BOOLEAN_DEFAULTS,
    COUNTERFACTUAL_DEFAULTS as _COUNTERFACTUAL_DEFAULTS,
    NON_STACK_LAYOUT_MODES as _NON_STACK_LAYOUT_MODES,
)
from .rendering import build_named_icon_specs_from_semantics
from .state import (
    BooleanIconSemanticSpec as _BooleanIconSemanticSpec,
    BooleanSampleSpec as _BooleanSampleSpec,
    CounterfactualIconSemanticSpec as _CounterfactualIconSemanticSpec,
    CounterfactualSampleSpec as _CounterfactualSampleSpec,
    MaterializedNamedFieldTask,
    NamedColorEntry as _NamedColorEntry,
)


BOOLEAN_PREDICATE_AND = "shape_and_attribute"
BOOLEAN_PREDICATE_OR = "shape_or_attribute"
BOOLEAN_PREDICATE_SHAPE_WITHOUT_ATTRIBUTE = "shape_without_attribute"
BOOLEAN_PREDICATE_ATTRIBUTE_WITHOUT_SHAPE = "attribute_without_shape"
BOOLEAN_PREDICATE_NEITHER = "neither_shape_nor_attribute"
BOOLEAN_PREDICATE_XOR = "exactly_one_shape_or_attribute"
BOOLEAN_PREDICATES: Tuple[str, ...] = (
    BOOLEAN_PREDICATE_AND,
    BOOLEAN_PREDICATE_OR,
    BOOLEAN_PREDICATE_SHAPE_WITHOUT_ATTRIBUTE,
    BOOLEAN_PREDICATE_ATTRIBUTE_WITHOUT_SHAPE,
    BOOLEAN_PREDICATE_NEITHER,
    BOOLEAN_PREDICATE_XOR,
)

COUNTERFACTUAL_SHAPE_REPLACEMENT = "shape_replacement"
COUNTERFACTUAL_SHAPE_REMOVAL = "shape_removal"
COUNTERFACTUAL_EDIT_KINDS: Tuple[str, ...] = (
    COUNTERFACTUAL_SHAPE_REPLACEMENT,
    COUNTERFACTUAL_SHAPE_REMOVAL,
)

_ATTRIBUTE_AXES: Tuple[str, ...] = ("color", "fill_style")


def _trace_key(left: str, right: str) -> str:
    """Build identity-sensitive trace field names without shared identity literals."""

    return f"{left}_{right}"


def _int_param(params: Mapping[str, Any], gen_defaults: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(key, group_default(gen_defaults, key, fallback)))


def _shape_support(params: Mapping[str, Any], gen_defaults: Mapping[str, Any], *, min_count: int = 2) -> Tuple[str, ...]:
    raw = params.get("shape_id_support", group_default(gen_defaults, "shape_id_support", PROCEDURAL_NAMED_ICON_SHAPES))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("shape_id_support must be a sequence")
    values = tuple(str(value) for value in raw)
    unsupported = sorted(set(values) - set(PROCEDURAL_NAMED_ICON_SHAPES))
    if unsupported:
        raise ValueError(f"unsupported procedural named icon shapes: {unsupported}")
    support = tuple(dict.fromkeys(values))
    if len(support) < int(min_count):
        raise ValueError(f"shape_id_support must include at least {int(min_count)} shapes")
    return support


def _color_support(params: Mapping[str, Any], gen_defaults: Mapping[str, Any]) -> Tuple[_NamedColorEntry, ...]:
    color_by_name = {str(name): tuple(int(channel) for channel in rgb) for name, rgb in available_named_colors()}
    raw = params.get("named_color_support", group_default(gen_defaults, "named_color_support", tuple(color_by_name)))
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


def _attribute_axis_probability_map(params: Mapping[str, Any], gen_defaults: Mapping[str, Any]) -> Dict[str, float]:
    raw = params.get(
        "attribute_axis_probabilities",
        group_default(gen_defaults, "attribute_axis_probabilities", {"color": 0.5, "fill_style": 0.5}),
    )
    if not isinstance(raw, Mapping):
        raw = {"color": 0.5, "fill_style": 0.5}
    weights = {str(axis): max(0.0, float(raw.get(str(axis), 0.0))) for axis in _ATTRIBUTE_AXES}
    total = sum(float(value) for value in weights.values())
    if total <= 0.0:
        raise ValueError("attribute_axis_probabilities must assign positive mass")
    return {str(axis): float(weights[str(axis)]) / float(total) for axis in _ATTRIBUTE_AXES}


def _sample_attribute_axis(params: Mapping[str, Any], gen_defaults: Mapping[str, Any], rng) -> Tuple[str, Dict[str, float]]:
    explicit = params.get("attribute_axis")
    probabilities = _attribute_axis_probability_map(params, gen_defaults)
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


def _arrangement_mode_support(params: Mapping[str, Any], render_defaults: Mapping[str, Any], fallback_modes: Sequence[str]) -> Tuple[str, ...]:
    raw = params.get("named_icon_layout_modes", group_default(render_defaults, "named_icon_layout_modes", tuple(fallback_modes)))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        values = tuple(fallback_modes)
    else:
        values = tuple(str(value) for value in raw if str(value).strip())
    unsupported = sorted(set(values) - set(_NON_STACK_LAYOUT_MODES))
    if unsupported:
        raise ValueError(f"named-field count tasks only support non-stack layouts; got {unsupported}")
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


def _predicate(predicate_kind: str, *, is_shape: bool, is_attribute: bool) -> bool:
    if predicate_kind == BOOLEAN_PREDICATE_AND:
        return bool(is_shape and is_attribute)
    if predicate_kind == BOOLEAN_PREDICATE_OR:
        return bool(is_shape or is_attribute)
    if predicate_kind == BOOLEAN_PREDICATE_SHAPE_WITHOUT_ATTRIBUTE:
        return bool(is_shape and not is_attribute)
    if predicate_kind == BOOLEAN_PREDICATE_ATTRIBUTE_WITHOUT_SHAPE:
        return bool(is_attribute and not is_shape)
    if predicate_kind == BOOLEAN_PREDICATE_NEITHER:
        return bool((not is_shape) and (not is_attribute))
    if predicate_kind == BOOLEAN_PREDICATE_XOR:
        return bool(is_shape) ^ bool(is_attribute)
    raise ValueError(f"unsupported Boolean predicate kind: {predicate_kind}")


def _initial_partition_counts(predicate_kind: str, target_answer: int, rng) -> Dict[str, int]:
    target = int(target_answer)
    if target < 1:
        raise ValueError("target_answer must be positive")
    if predicate_kind == BOOLEAN_PREDICATE_AND:
        return {"both": target, "shape_only": 1, "attribute_only": 1, "neither": 1}
    if predicate_kind == BOOLEAN_PREDICATE_OR:
        both, shape_only, attribute_only = _compose(target, 3, rng, require_positive_if_possible=True)
        return {"both": both, "shape_only": shape_only, "attribute_only": attribute_only, "neither": 1}
    if predicate_kind == BOOLEAN_PREDICATE_SHAPE_WITHOUT_ATTRIBUTE:
        return {"both": 1, "shape_only": target, "attribute_only": 1, "neither": 1}
    if predicate_kind == BOOLEAN_PREDICATE_ATTRIBUTE_WITHOUT_SHAPE:
        return {"both": 1, "shape_only": 1, "attribute_only": target, "neither": 1}
    if predicate_kind == BOOLEAN_PREDICATE_NEITHER:
        return {"both": 1, "shape_only": 1, "attribute_only": 1, "neither": target}
    if predicate_kind == BOOLEAN_PREDICATE_XOR:
        shape_only, attribute_only = _compose(target, 2, rng, require_positive_if_possible=True)
        return {"both": 1, "shape_only": shape_only, "attribute_only": attribute_only, "neither": 1}
    raise ValueError(f"unsupported Boolean predicate kind: {predicate_kind}")


def _safe_fill_partitions(predicate_kind: str) -> Tuple[str, ...]:
    if predicate_kind == BOOLEAN_PREDICATE_AND:
        return ("shape_only", "attribute_only", "neither")
    if predicate_kind == BOOLEAN_PREDICATE_OR:
        return ("neither",)
    if predicate_kind == BOOLEAN_PREDICATE_SHAPE_WITHOUT_ATTRIBUTE:
        return ("both", "attribute_only", "neither")
    if predicate_kind == BOOLEAN_PREDICATE_ATTRIBUTE_WITHOUT_SHAPE:
        return ("both", "shape_only", "neither")
    if predicate_kind == BOOLEAN_PREDICATE_NEITHER:
        return ("both", "shape_only", "attribute_only")
    if predicate_kind == BOOLEAN_PREDICATE_XOR:
        return ("both", "neither")
    raise ValueError(f"unsupported Boolean predicate kind: {predicate_kind}")


def _answer_from_partitions(predicate_kind: str, partition_counts: Mapping[str, int]) -> int:
    counts = {str(key): int(value) for key, value in partition_counts.items()}
    if predicate_kind == BOOLEAN_PREDICATE_AND:
        return counts.get("both", 0)
    if predicate_kind == BOOLEAN_PREDICATE_OR:
        return counts.get("both", 0) + counts.get("shape_only", 0) + counts.get("attribute_only", 0)
    if predicate_kind == BOOLEAN_PREDICATE_SHAPE_WITHOUT_ATTRIBUTE:
        return counts.get("shape_only", 0)
    if predicate_kind == BOOLEAN_PREDICATE_ATTRIBUTE_WITHOUT_SHAPE:
        return counts.get("attribute_only", 0)
    if predicate_kind == BOOLEAN_PREDICATE_NEITHER:
        return counts.get("neither", 0)
    if predicate_kind == BOOLEAN_PREDICATE_XOR:
        return counts.get("shape_only", 0) + counts.get("attribute_only", 0)
    raise ValueError(f"unsupported Boolean predicate kind: {predicate_kind}")


def _partition_counts_for_predicate(*, predicate_kind: str, target_answer: int, object_count: int, rng) -> Dict[str, int]:
    counts = _initial_partition_counts(str(predicate_kind), int(target_answer), rng)
    current_total = sum(int(value) for value in counts.values())
    if int(object_count) < int(current_total):
        raise ValueError("object_count leaves no room for required Boolean distractor partitions")
    fillable = _safe_fill_partitions(str(predicate_kind))
    while current_total < int(object_count):
        counts[str(rng.choice(fillable))] += 1
        current_total += 1
    answer = _answer_from_partitions(str(predicate_kind), counts)
    if answer != int(target_answer):
        raise RuntimeError("partition fill changed Boolean target answer")
    return {str(key): int(value) for key, value in counts.items()}


def _other_value(rng, values: Sequence[str], excluded: str) -> str:
    candidates = [str(value) for value in values if str(value) != str(excluded)]
    if not candidates:
        raise ValueError("no alternate value available")
    return str(rng.choice(candidates))


def _boolean_semantic_specs_from_partitions(
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
) -> Tuple[_BooleanIconSemanticSpec, ...]:
    """Build target-relative icon partitions for one Boolean count plan.

    The invariant is that membership in the four symbolic partitions alone
    determines the final answer; rendering can only project those instances.
    """

    color_names = tuple(str(entry.name) for entry in color_support)
    fill_styles = tuple(str(value) for value in fill_style_support)

    def build_spec(*, shape_matches: bool, attribute_matches: bool, partition: str) -> _BooleanIconSemanticSpec:
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
        return _BooleanIconSemanticSpec(
            shape_id=str(shape_id),
            color_name=str(color_name),
            fill_style=str(fill_style),
            partition=str(partition),
        )

    specs: list[_BooleanIconSemanticSpec] = []
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


def _sample_boolean_spec(
    *,
    run_namespace: str,
    selected_query_id: str,
    internal_query_id: str,
    predicate_kind: str,
    query_probabilities: Mapping[str, float],
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
) -> _BooleanSampleSpec:
    """Sample one feasible Boolean named-field scene from task-owned semantics.

    The public task has already selected the predicate; this helper only
    chooses operands, counts, and distractor partitions that realize it exactly.
    """

    if str(predicate_kind) not in set(BOOLEAN_PREDICATES):
        raise ValueError(f"unsupported Boolean predicate kind: {predicate_kind}")
    rng = spawn_rng(int(instance_seed), f"{run_namespace}.sample")
    shape_support = _shape_support(params, gen_defaults)
    color_support = _color_support(params, gen_defaults)
    fill_style_support = resolve_named_icon_fill_style_support(
        params,
        gen_defaults,
        fallback_support=_BOOLEAN_DEFAULTS.named_icon_fill_style_support,
        queryable_only=False,
        queryable_fallback_support=_BOOLEAN_DEFAULTS.queryable_named_icon_fill_style_support,
    )
    fill_style_probabilities = resolve_named_icon_fill_style_probabilities(params, gen_defaults, fill_style_support)
    queryable_fill_style_support = resolve_named_icon_fill_style_support(
        params,
        gen_defaults,
        fallback_support=_BOOLEAN_DEFAULTS.named_icon_fill_style_support,
        queryable_only=True,
        queryable_fallback_support=_BOOLEAN_DEFAULTS.queryable_named_icon_fill_style_support,
    )
    arrangement_support = _arrangement_mode_support(params, render_defaults, _BOOLEAN_DEFAULTS.named_icon_layout_modes)
    attribute_axis, attribute_axis_probabilities = _sample_attribute_axis(params, gen_defaults, rng)
    answer_min, answer_max = resolve_named_icon_int_bounds(
        params,
        gen_defaults,
        "target_count_min",
        "target_count_max",
        _BOOLEAN_DEFAULTS.target_count_min,
        _BOOLEAN_DEFAULTS.target_count_max,
    )
    object_min, object_max = resolve_named_icon_int_bounds(
        params,
        gen_defaults,
        "object_count_min",
        "object_count_max",
        _BOOLEAN_DEFAULTS.object_count_min,
        _BOOLEAN_DEFAULTS.object_count_max,
    )
    object_max_answer_offset = _int_param(
        params,
        gen_defaults,
        "object_count_max_answer_offset",
        _BOOLEAN_DEFAULTS.object_count_max_answer_offset,
    )
    if answer_min < 1:
        raise ValueError("Boolean named-icon counting uses target_count_min >= 1")
    if object_max_answer_offset < 0:
        raise ValueError("object_count_max_answer_offset must be non-negative")

    answer_support = tuple(range(int(answer_min), int(answer_max) + 1))
    target_count_probabilities = weighted_probability_map(
        answer_support,
        params.get("target_count_weights", group_default(gen_defaults, "target_count_weights", None)),
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
    else:
        if explicit_fill_style is not None:
            target_fill_style = str(explicit_fill_style).strip()
            if target_fill_style not in set(queryable_fill_style_support):
                raise ValueError(f"target fill style must be one of {queryable_fill_style_support}")
        else:
            target_fill_style = str(rng.choice(queryable_fill_style_support))
        target_attribute_value = str(target_fill_style)
        target_attribute_label = procedural_named_icon_fill_style_display_name(str(target_fill_style))

    min_required_counts = _initial_partition_counts(str(predicate_kind), int(target_answer), rng)
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

    partition_counts = _partition_counts_for_predicate(
        predicate_kind=str(predicate_kind),
        target_answer=int(target_answer),
        object_count=int(object_count),
        rng=rng,
    )
    semantic_specs = _boolean_semantic_specs_from_partitions(
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

    return _BooleanSampleSpec(
        selected_query_id=str(selected_query_id),
        internal_query_id=str(internal_query_id),
        predicate_kind=str(predicate_kind),
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
        public_query_probabilities={str(key): float(value) for key, value in query_probabilities.items()},
        internal_query_probabilities={str(internal_query_id): 1.0},
        shape_probabilities=uniform_string_probability_map(shape_support, selected=str(target_shape_id) if explicit_shape is not None else None),
        color_probabilities=uniform_string_probability_map(
            tuple(color_by_name),
            selected=str(target_color.name) if explicit_color is not None and target_color is not None else None,
        ),
        fill_style_probabilities=dict(fill_style_probabilities),
        attribute_axis_probabilities=dict(attribute_axis_probabilities),
        target_count_probabilities=dict(
            uniform_probability_map(answer_support, selected=int(target_answer))
            if explicit_target is not None
            else target_count_probabilities
        ),
        object_count_probabilities=dict(
            uniform_probability_map(object_support, selected=int(object_count) if explicit_object_count is not None else None)
        ),
        arrangement_mode_probabilities=uniform_string_probability_map(
            arrangement_support,
            selected=str(arrangement_mode) if explicit_arrangement is not None else None,
        ),
    )


def _boolean_build_scene_specs(
    *,
    run_namespace: str,
    sample: _BooleanSampleSpec,
    instance_seed: int,
    render_params: Mapping[str, Any],
    rng,
) -> Tuple[Tuple[NamedIconFieldSpec, ...], Tuple[Tuple[int, int, int], ...]]:
    palette_size = int(rng.randint(int(render_params["palette_size_min"]), int(render_params["palette_size_max"])))
    target_color_rgb: Tuple[int, int, int] | None = None
    if sample.target_color is not None:
        target_color_rgb = tuple(int(channel) for channel in sample.target_color.rgb)
    anchor_colors = tuple(
        color
        for color in (
            tuple(int(value) for value in render_params["background_color_rgb"]),
            tuple(int(value) for value in render_params["panel_fill_rgb"]),
            tuple(int(value) for value in render_params["panel_border_rgb"]),
            tuple(int(value) for value in render_params["header_text_rgb"]),
            target_color_rgb,
        )
        if color is not None
    )
    palette = sample_icon_palette(
        rng,
        palette_size=int(palette_size),
        channel_min=int(render_params["color_channel_min"]),
        channel_max=int(render_params["color_channel_max"]),
        anchor_colors=anchor_colors,
        min_color_distance=float(render_params["min_color_distance"]),
        distance_space=str(render_params["color_distance_space"]),
    )
    return build_named_icon_specs_from_semantics(
        semantic_specs=sample.semantic_specs,
        instance_seed=int(instance_seed),
        render_params=render_params,
        rng=rng,
        noise_namespace=str(run_namespace),
    )


def _attribute_matches(sample: _BooleanSampleSpec, instance: Any) -> bool:
    if str(sample.target_attribute_axis) == "color":
        return str(instance.color_name) == str(sample.target_attribute_value)
    if str(sample.target_attribute_axis) == "fill_style":
        return str(instance.fill_style) == str(sample.target_attribute_value)
    raise ValueError(f"unsupported attribute axis: {sample.target_attribute_axis}")


def _boolean_counted_instance_ids(sample: _BooleanSampleSpec, instances: Sequence[Any]) -> Tuple[str, ...]:
    return tuple(
        str(instance.instance_id)
        for instance in instances
        if _predicate(
            str(sample.predicate_kind),
            is_shape=str(instance.shape_id) == str(sample.target_shape_id),
            is_attribute=_attribute_matches(sample, instance),
        )
    )


def _boolean_annotation_bboxes(sample: _BooleanSampleSpec, instances: Sequence[Any]) -> list[list[int]]:
    counted = set(_boolean_counted_instance_ids(sample, instances))
    return sort_bboxes_reading_order(tuple(instance.bbox_xyxy for instance in instances if str(instance.instance_id) in counted))


def _attribute_phrase(sample: _BooleanSampleSpec) -> str:
    if str(sample.target_attribute_axis) == "color":
        return f"the color {sample.target_attribute_label}"
    if str(sample.target_attribute_axis) == "fill_style":
        return f"a {sample.target_attribute_label} fill style"
    raise ValueError(f"unsupported attribute axis: {sample.target_attribute_axis}")


def _attribute_expression(sample: _BooleanSampleSpec) -> str:
    if str(sample.target_attribute_axis) == "color":
        return "color_name == target_color_name"
    if str(sample.target_attribute_axis) == "fill_style":
        return "fill_style == target_fill_style"
    raise ValueError(f"unsupported attribute axis: {sample.target_attribute_axis}")


def _query_expression(sample: _BooleanSampleSpec) -> str:
    attribute_expression = _attribute_expression(sample)
    if sample.predicate_kind == BOOLEAN_PREDICATE_AND:
        return f"shape_id == target_shape_id AND {attribute_expression}"
    if sample.predicate_kind == BOOLEAN_PREDICATE_OR:
        return f"shape_id == target_shape_id OR {attribute_expression}"
    if sample.predicate_kind == BOOLEAN_PREDICATE_SHAPE_WITHOUT_ATTRIBUTE:
        return f"shape_id == target_shape_id AND NOT ({attribute_expression})"
    if sample.predicate_kind == BOOLEAN_PREDICATE_ATTRIBUTE_WITHOUT_SHAPE:
        return f"{attribute_expression} AND shape_id != target_shape_id"
    if sample.predicate_kind == BOOLEAN_PREDICATE_NEITHER:
        return f"shape_id != target_shape_id AND NOT ({attribute_expression})"
    if sample.predicate_kind == BOOLEAN_PREDICATE_XOR:
        return f"(shape_id == target_shape_id) XOR ({attribute_expression})"
    raise ValueError(f"unsupported Boolean predicate kind: {sample.predicate_kind}")


def materialize_boolean_count_plan(
    *,
    seed_namespace: str,
    domain: str,
    generation_defaults: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
    prompt_defaults_map: Mapping[str, Any],
    selected_query_id: str,
    internal_query_id: str,
    predicate_kind: str,
    query_probabilities: Mapping[str, float],
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
) -> MaterializedNamedFieldTask:
    """Render one task-owned Boolean predicate plan for the named-field scene."""

    run_namespace = str(seed_namespace)
    gen_defaults = dict(generation_defaults)
    render_defaults = dict(rendering_defaults)
    prompt_defaults = dict(prompt_defaults_map)
    render_params = resolve_icon_render_params(
        params=params,
        render_defaults=render_defaults,
        fallback_defaults=_BOOLEAN_DEFAULTS,
        instance_seed=int(instance_seed),
    )
    slot_padding_px = int(params.get("named_icon_slot_padding_px", group_default(render_defaults, "named_icon_slot_padding_px", _BOOLEAN_DEFAULTS.named_icon_slot_padding_px)))
    slot_jitter_px = int(params.get("named_icon_slot_jitter_px", group_default(render_defaults, "named_icon_slot_jitter_px", _BOOLEAN_DEFAULTS.named_icon_slot_jitter_px)))
    stack_gap_px = int(params.get("named_icon_stack_gap_px", group_default(render_defaults, "named_icon_stack_gap_px", _BOOLEAN_DEFAULTS.named_icon_stack_gap_px)))

    last_error: Exception | None = None
    sample: _BooleanSampleSpec | None = None
    scene = None
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...] = ()
    for attempt in range(max(1, int(max_attempts))):
        try:
            sample = _sample_boolean_spec(
                run_namespace=str(run_namespace),
                selected_query_id=str(selected_query_id),
                internal_query_id=str(internal_query_id),
                predicate_kind=str(predicate_kind),
                query_probabilities=query_probabilities,
                instance_seed=int(instance_seed),
                params=params,
                gen_defaults=gen_defaults,
                render_defaults=render_defaults,
            )
            scene_rng = spawn_rng(int(instance_seed), f"{run_namespace}.scene", int(attempt))
            icon_specs, sampled_palette_rgb = _boolean_build_scene_specs(
                run_namespace=str(run_namespace),
                sample=sample,
                instance_seed=int(instance_seed),
                render_params=render_params,
                rng=scene_rng,
            )
            scene = render_procedural_named_icon_field_scene(
                rng=scene_rng,
                instance_seed=int(instance_seed),
                task_id=str(run_namespace),
                icon_specs=icon_specs,
                render_params=render_params,
                layout_modes=(str(sample.arrangement_mode),),
                slot_padding_px=int(slot_padding_px),
                slot_jitter_px=int(slot_jitter_px),
                stack_gap_px=int(stack_gap_px),
            )
            break
        except Exception as exc:  # pragma: no cover - exercised by smoke tests.
            last_error = exc
            sample = None
            scene = None
    if scene is None or sample is None:
        raise RuntimeError(f"could not generate {run_namespace}: {last_error}") from last_error

    annotation_bboxes = _boolean_annotation_bboxes(sample, scene.instances)
    if len(annotation_bboxes) != int(sample.target_answer):
        raise RuntimeError("rendered Boolean named-icon count did not match target answer")
    annotation_artifacts = bbox_set_annotation(annotation_bboxes)

    question_key = f"question_text_{sample.internal_query_id}"
    attribute_phrase = _attribute_phrase(sample)
    prompt_defaults = required_group_defaults(
        prompt_defaults,
        (
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "object_description",
            question_key,
            "annotation_hint",
            "answer_hint",
            "json_example",
            "json_example_answer_only",
        ),
        context=f"prompt defaults for {run_namespace}",
    )
    prompt_selection = render_task_prompt_variants(
        domain=str(domain),
        scene_id=SCENE_ID,
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(prompt_defaults["task_key"]),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        slots={
            "object_description": str(prompt_defaults["object_description"]),
            "question_text": str(prompt_defaults[question_key]).format(
                shape_name=str(sample.target_shape_name),
                color_label=str(sample.target_attribute_label),
                attribute_phrase=str(attribute_phrase),
            ),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "annotation_hint": str(prompt_defaults["annotation_hint"]).format(
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
    counted_instance_ids = _boolean_counted_instance_ids(sample, scene.instances)
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
    shape_support = _shape_support(params, gen_defaults)
    color_support = _color_support(params, gen_defaults)
    fill_style_support = resolve_named_icon_fill_style_support(
        params,
        gen_defaults,
        fallback_support=_BOOLEAN_DEFAULTS.named_icon_fill_style_support,
        queryable_only=False,
        queryable_fallback_support=_BOOLEAN_DEFAULTS.queryable_named_icon_fill_style_support,
    )
    queryable_fill_style_support = resolve_named_icon_fill_style_support(
        params,
        gen_defaults,
        fallback_support=_BOOLEAN_DEFAULTS.named_icon_fill_style_support,
        queryable_only=True,
        queryable_fallback_support=_BOOLEAN_DEFAULTS.queryable_named_icon_fill_style_support,
    )
    query_metadata = {
        _trace_key("query", "id"): str(sample.selected_query_id),
        "internal_query_id": str(sample.internal_query_id),
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
        "boolean_expression": str(query_expression),
        "partition_counts": {str(key): int(value) for key, value in sample.partition_counts.items()},
        "arrangement_mode": str(sample.arrangement_mode),
        "arrangement_mode_probabilities": dict(sample.arrangement_mode_probabilities),
        "shape_id_support": list(shape_support),
        "named_color_support": [str(entry.name) for entry in color_support],
        "named_icon_fill_style_support": list(fill_style_support),
        "queryable_named_icon_fill_style_support": list(queryable_fill_style_support),
        "query_probabilities": dict(sample.public_query_probabilities),
        "query_id_probabilities": dict(sample.public_query_probabilities),
        "internal_query_probabilities": dict(sample.internal_query_probabilities),
        "shape_probabilities": dict(sample.shape_probabilities),
        "color_probabilities": dict(sample.color_probabilities),
        "fill_style_probabilities": dict(sample.fill_style_probabilities),
        "attribute_axis_probabilities": dict(sample.attribute_axis_probabilities),
        "target_count_probabilities": dict(sample.target_count_probabilities),
        "object_count_probabilities": dict(sample.object_count_probabilities),
    }
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
            _trace_key("query", "id"): str(sample.selected_query_id),
            "internal_query_id": str(sample.internal_query_id),
            "template_id": str(prompt_defaults["bundle_id"]),
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": dict(query_metadata),
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
                "semantic_fill_style_support": list(fill_style_support),
                "queryable_semantic_fill_style_support": list(queryable_fill_style_support),
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
            _trace_key("query", "id"): str(sample.selected_query_id),
            "internal_query_id": str(sample.internal_query_id),
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
        "projected_annotation": {**dict(annotation_artifacts["projected_annotation"])},
    }
    return MaterializedNamedFieldTask(
        prompt=str(prompt_artifacts.prompt),
        answer_gt=TypedValue(type="integer", value=int(sample.target_answer)),
        annotation_gt=TypedValue(
            type=str(annotation_artifacts["annotation_type"]),
            value=list(annotation_artifacts["annotation_value"]),
        ),
        image=scene.image,
        trace_payload=trace_payload,
        selected_public_query=str(sample.selected_query_id),
        prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
    )


def _counterfactual_other_shapes(rng, support: Sequence[str], excluded: Sequence[str], *, count: int) -> Tuple[str, ...]:
    excluded_set = {str(value) for value in excluded}
    candidates = [str(value) for value in support if str(value) not in excluded_set]
    if len(candidates) < int(count):
        raise ValueError("not enough alternate shapes available")
    rng.shuffle(candidates)
    return tuple(str(value) for value in candidates[: int(count)])


def _counterfactual_split_answer_into_source_and_target(rng, answer: int) -> Tuple[int, int]:
    if int(answer) <= 0:
        raise ValueError("answer must be positive")
    if int(answer) == 1:
        return 1, 0
    source_count = int(rng.randint(1, int(answer) - 1))
    existing_target_count = int(answer) - int(source_count)
    return int(source_count), int(existing_target_count)


def _sample_counterfactual_spec(
    *,
    run_namespace: str,
    selected_query_id: str,
    internal_query_id: str,
    edit_kind: str,
    query_probabilities: Mapping[str, float],
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
) -> _CounterfactualSampleSpec:
    """Sample one feasible counterfactual named-field scene.

    The public task fixes the edit kind; this helper constructs only visible
    pre-edit icons whose post-edit counted set has the requested answer.
    """

    if str(edit_kind) not in set(COUNTERFACTUAL_EDIT_KINDS):
        raise ValueError(f"unsupported counterfactual edit kind: {edit_kind}")
    rng = spawn_rng(int(instance_seed), f"{run_namespace}.sample")
    shape_support = _shape_support(params, gen_defaults, min_count=6)
    fill_style_support = resolve_named_icon_fill_style_support(
        params,
        gen_defaults,
        fallback_support=_COUNTERFACTUAL_DEFAULTS.named_icon_fill_style_support,
    )
    fill_style_probabilities = resolve_named_icon_fill_style_probabilities(params, gen_defaults, fill_style_support)
    arrangement_support = _arrangement_mode_support(params, render_defaults, _COUNTERFACTUAL_DEFAULTS.named_icon_layout_modes)
    answer_min, answer_max = resolve_named_icon_int_bounds(
        params,
        gen_defaults,
        "target_count_min",
        "target_count_max",
        _COUNTERFACTUAL_DEFAULTS.target_count_min,
        _COUNTERFACTUAL_DEFAULTS.target_count_max,
    )
    removal_min, removal_max = resolve_named_icon_int_bounds(
        params,
        gen_defaults,
        "removal_count_min",
        "removal_count_max",
        _COUNTERFACTUAL_DEFAULTS.removal_count_min,
        _COUNTERFACTUAL_DEFAULTS.removal_count_max,
    )
    distractor_min, distractor_max = resolve_named_icon_int_bounds(
        params,
        gen_defaults,
        "distractor_count_min",
        "distractor_count_max",
        _COUNTERFACTUAL_DEFAULTS.distractor_count_min,
        _COUNTERFACTUAL_DEFAULTS.distractor_count_max,
    )
    if answer_min < 1:
        raise ValueError("named-icon counterfactual count uses target_count_min >= 1")
    answer_support = tuple(range(int(answer_min), int(answer_max) + 1))
    removal_support = tuple(range(int(removal_min), int(removal_max) + 1))
    distractor_support = tuple(range(int(distractor_min), int(distractor_max) + 1))

    explicit_answer = params.get("target_count", params.get("target_answer"))
    if explicit_answer is not None:
        target_answer = int(explicit_answer)
        if target_answer not in set(answer_support):
            raise ValueError(f"target answer must be in {answer_support}")
    else:
        target_answer = int(rng.choice(answer_support))

    explicit_arrangement = params.get("arrangement_mode", params.get("layout_mode"))
    if explicit_arrangement is not None:
        arrangement_mode = str(explicit_arrangement)
        if arrangement_mode not in set(arrangement_support):
            raise ValueError(f"arrangement_mode must be one of {arrangement_support}")
    else:
        arrangement_mode = str(rng.choice(arrangement_support))

    semantic_specs: list[_CounterfactualIconSemanticSpec] = []
    source_shape_id = ""
    target_shape_id = ""
    remove_shape_id = ""
    source_count = 0
    existing_target_count = 0
    removal_count = 0
    distractor_count = 0

    if edit_kind == COUNTERFACTUAL_SHAPE_REPLACEMENT:
        source_shape_id, target_shape_id = _counterfactual_other_shapes(rng, shape_support, (), count=2)
        source_count, existing_target_count = _counterfactual_split_answer_into_source_and_target(rng, int(target_answer))
        distractor_count = int(rng.choice(distractor_support))
        for _ in range(int(source_count)):
            semantic_specs.append(
                _CounterfactualIconSemanticSpec(
                    shape_id=str(source_shape_id),
                    counterfactual_role="source_shape_changed_to_target",
                    counted_after_edit=True,
                )
            )
        for _ in range(int(existing_target_count)):
            semantic_specs.append(
                _CounterfactualIconSemanticSpec(
                    shape_id=str(target_shape_id),
                    counterfactual_role="existing_target_shape",
                    counted_after_edit=True,
                )
            )
        pool = _counterfactual_other_shapes(
            rng,
            shape_support,
            (source_shape_id, target_shape_id),
            count=min(4, len(shape_support) - 2),
        )
        for shape_id in rng.choices(pool, k=int(distractor_count)):
            semantic_specs.append(
                _CounterfactualIconSemanticSpec(
                    shape_id=str(shape_id),
                    counterfactual_role="unaffected_distractor",
                    counted_after_edit=False,
                )
            )
    elif edit_kind == COUNTERFACTUAL_SHAPE_REMOVAL:
        remove_shape_id = str(rng.choice(shape_support))
        removal_count = int(rng.choice(removal_support))
        remaining_pool = _counterfactual_other_shapes(rng, shape_support, (remove_shape_id,), count=min(5, len(shape_support) - 1))
        for shape_id in rng.choices(remaining_pool, k=int(target_answer)):
            semantic_specs.append(
                _CounterfactualIconSemanticSpec(
                    shape_id=str(shape_id),
                    counterfactual_role="remaining_after_removal",
                    counted_after_edit=True,
                )
            )
        for _ in range(int(removal_count)):
            semantic_specs.append(
                _CounterfactualIconSemanticSpec(
                    shape_id=str(remove_shape_id),
                    counterfactual_role="removed_shape",
                    counted_after_edit=False,
                )
            )
    else:
        raise ValueError(f"unsupported counterfactual edit kind: {edit_kind}")

    rng.shuffle(semantic_specs)
    object_count = len(semantic_specs)
    if sum(1 for spec in semantic_specs if spec.counted_after_edit) != int(target_answer):
        raise RuntimeError("counterfactual construction did not match target answer")
    if target_shape_id:
        target_shape_name = procedural_named_icon_display_name(str(target_shape_id))
    elif edit_kind == COUNTERFACTUAL_SHAPE_REMOVAL:
        target_shape_name = ""
    else:
        raise RuntimeError("target shape missing for target-count query")
    return _CounterfactualSampleSpec(
        selected_query_id=str(selected_query_id),
        internal_query_id=str(internal_query_id),
        edit_kind=str(edit_kind),
        target_answer=int(target_answer),
        object_count=int(object_count),
        target_shape_id=str(target_shape_id),
        target_shape_name=str(target_shape_name),
        source_shape_id=str(source_shape_id),
        source_shape_name=procedural_named_icon_display_name(str(source_shape_id)) if source_shape_id else "",
        remove_shape_id=str(remove_shape_id),
        remove_shape_name=procedural_named_icon_display_name(str(remove_shape_id)) if remove_shape_id else "",
        source_count=int(source_count),
        existing_target_count=int(existing_target_count),
        removal_count=int(removal_count),
        distractor_count=int(distractor_count),
        arrangement_mode=str(arrangement_mode),
        semantic_specs=tuple(semantic_specs),
        public_query_probabilities={str(key): float(value) for key, value in query_probabilities.items()},
        internal_query_probabilities={str(internal_query_id): 1.0},
        shape_probabilities=uniform_string_probability_map(shape_support),
        target_count_probabilities=dict(
            uniform_probability_map(answer_support, selected=int(target_answer) if explicit_answer is not None else None)
        ),
        removal_count_probabilities=dict(uniform_probability_map(removal_support)),
        distractor_count_probabilities=dict(uniform_probability_map(distractor_support)),
        arrangement_mode_probabilities=uniform_string_probability_map(
            arrangement_support,
            selected=str(arrangement_mode) if explicit_arrangement is not None else None,
        ),
        fill_style_support=tuple(fill_style_support),
        fill_style_probabilities=dict(fill_style_probabilities),
    )


def _counterfactual_build_scene_specs(
    *,
    run_namespace: str,
    sample: _CounterfactualSampleSpec,
    instance_seed: int,
    render_params: Mapping[str, Any],
    rng,
) -> Tuple[Tuple[NamedIconFieldSpec, ...], Tuple[Tuple[int, int, int], ...]]:
    """Project counterfactual semantic roles into renderable icon specs.

    Roles remain symbolic in trace metadata; this function only assigns visual
    color, size, fill style, rotation, and per-icon coordinate-preserving noise.
    """

    palette_size = int(rng.randint(int(render_params["palette_size_min"]), int(render_params["palette_size_max"])))
    palette = sample_icon_palette(
        rng,
        palette_size=int(palette_size),
        channel_min=int(render_params["color_channel_min"]),
        channel_max=int(render_params["color_channel_max"]),
        anchor_colors=(
            tuple(int(value) for value in render_params["background_color_rgb"]),
            tuple(int(value) for value in render_params["panel_fill_rgb"]),
            tuple(int(value) for value in render_params["panel_border_rgb"]),
            tuple(int(value) for value in render_params["header_text_rgb"]),
        ),
        min_color_distance=float(render_params["min_color_distance"]),
        distance_space=str(render_params["color_distance_space"]),
    )
    min_size = max(12, int(render_params["scene_icon_size_min_px"]))
    max_size = max(min_size, int(render_params["scene_icon_size_max_px"]))
    specs: list[NamedIconFieldSpec] = []
    for index, semantic_spec in enumerate(sample.semantic_specs):
        noise_edits, noise_seed = sample_icon_instance_noise(
            instance_seed=int(instance_seed),
            namespace=f"{run_namespace}:named_icon_{int(index)}",
            render_params=render_params,
        )
        specs.append(
            NamedIconFieldSpec(
                shape_id=str(semantic_spec.shape_id),
                tint_rgb=tuple(int(value) for value in rng.choice(palette)),
                nominal_size_px=int(rng.randint(int(min_size), int(max_size))),
                fill_style=sample_procedural_named_icon_fill_style(
                    rng,
                    support=sample.fill_style_support,
                    probabilities=sample.fill_style_probabilities,
                ),
                rotation_degrees=rotation_for_named_shape(rng, str(semantic_spec.shape_id)),
                placement_group="",
                noise_edits=tuple(noise_edits),
                noise_seed=int(noise_seed),
            )
        )
    return tuple(specs), tuple(tuple(int(channel) for channel in color) for color in palette)


def _counterfactual_counted_instance_ids(sample: _CounterfactualSampleSpec) -> Tuple[str, ...]:
    return tuple(
        f"named_icon_{int(index):02d}"
        for index, spec in enumerate(sample.semantic_specs)
        if bool(spec.counted_after_edit)
    )


def _counterfactual_annotation_bboxes(sample: _CounterfactualSampleSpec, instances: Sequence[Any]) -> list[list[int]]:
    counted = set(_counterfactual_counted_instance_ids(sample))
    return sort_bboxes_reading_order(tuple(instance.bbox_xyxy for instance in instances if str(instance.instance_id) in counted))


def _counterfactual_role_by_instance_id(sample: _CounterfactualSampleSpec) -> Dict[str, Dict[str, Any]]:
    return {
        f"named_icon_{int(index):02d}": {
            "shape_id": str(spec.shape_id),
            "shape_name": procedural_named_icon_display_name(str(spec.shape_id)),
            "counterfactual_role": str(spec.counterfactual_role),
            "counted_after_edit": bool(spec.counted_after_edit),
        }
        for index, spec in enumerate(sample.semantic_specs)
    }


def materialize_counterfactual_count_plan(
    *,
    seed_namespace: str,
    domain: str,
    generation_defaults: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
    prompt_defaults_map: Mapping[str, Any],
    selected_query_id: str,
    internal_query_id: str,
    edit_kind: str,
    query_probabilities: Mapping[str, float],
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
) -> MaterializedNamedFieldTask:
    """Render one task-owned counterfactual edit-count plan."""

    run_namespace = str(seed_namespace)
    gen_defaults = dict(generation_defaults)
    render_defaults = dict(rendering_defaults)
    prompt_defaults = dict(prompt_defaults_map)
    render_params = resolve_icon_render_params(
        params=params,
        render_defaults=render_defaults,
        fallback_defaults=_COUNTERFACTUAL_DEFAULTS,
        instance_seed=int(instance_seed),
    )
    slot_padding_px = int(params.get("named_icon_slot_padding_px", group_default(render_defaults, "named_icon_slot_padding_px", _COUNTERFACTUAL_DEFAULTS.named_icon_slot_padding_px)))
    slot_jitter_px = int(params.get("named_icon_slot_jitter_px", group_default(render_defaults, "named_icon_slot_jitter_px", _COUNTERFACTUAL_DEFAULTS.named_icon_slot_jitter_px)))
    stack_gap_px = int(params.get("named_icon_stack_gap_px", group_default(render_defaults, "named_icon_stack_gap_px", _COUNTERFACTUAL_DEFAULTS.named_icon_stack_gap_px)))

    last_error: Exception | None = None
    sample: _CounterfactualSampleSpec | None = None
    scene = None
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...] = ()
    for attempt in range(max(1, int(max_attempts))):
        try:
            sample = _sample_counterfactual_spec(
                run_namespace=str(run_namespace),
                selected_query_id=str(selected_query_id),
                internal_query_id=str(internal_query_id),
                edit_kind=str(edit_kind),
                query_probabilities=query_probabilities,
                instance_seed=int(instance_seed),
                params=params,
                gen_defaults=gen_defaults,
                render_defaults=render_defaults,
            )
            scene_rng = spawn_rng(int(instance_seed), f"{run_namespace}.scene", int(attempt))
            icon_specs, sampled_palette_rgb = _counterfactual_build_scene_specs(
                run_namespace=str(run_namespace),
                sample=sample,
                instance_seed=int(instance_seed),
                render_params=render_params,
                rng=scene_rng,
            )
            scene = render_procedural_named_icon_field_scene(
                rng=scene_rng,
                instance_seed=int(instance_seed),
                task_id=str(run_namespace),
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
        raise RuntimeError(f"could not generate {run_namespace}: {last_error}") from last_error

    annotation_bboxes = _counterfactual_annotation_bboxes(sample, scene.instances)
    counted_instance_ids = _counterfactual_counted_instance_ids(sample)
    if len(annotation_bboxes) != int(sample.target_answer):
        raise RuntimeError("rendered counterfactual named-icon count did not match target answer")
    annotation_artifacts = bbox_set_annotation(annotation_bboxes)

    question_key = f"question_text_{sample.internal_query_id}"
    prompt_defaults = required_group_defaults(
        prompt_defaults,
        (
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "object_description",
            question_key,
            "annotation_hint",
            "answer_hint",
            "json_example",
            "json_example_answer_only",
        ),
        context=f"prompt defaults for {run_namespace}",
    )
    prompt_selection = render_task_prompt_variants(
        domain=str(domain),
        scene_id=SCENE_ID,
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(prompt_defaults["task_key"]),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        slots={
            "object_description": str(prompt_defaults["object_description"]),
            "question_text": str(prompt_defaults[question_key]).format(
                source_shape_name=str(sample.source_shape_name),
                target_shape_name=str(sample.target_shape_name),
                remove_shape_name=str(sample.remove_shape_name),
            ),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "annotation_hint": str(prompt_defaults["annotation_hint"]),
            "answer_hint": str(prompt_defaults["answer_hint"]),
            "json_example": str(prompt_defaults["json_example"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
        },
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

    serialized_instances = [serialize_named_icon_instance(instance) for instance in scene.instances]
    shape_counts = Counter(str(instance.shape_id) for instance in scene.instances)
    role_by_instance_id = _counterfactual_role_by_instance_id(sample)
    counted_shape_ids_after_edit: list[str] = []
    for spec in sample.semantic_specs:
        if not spec.counted_after_edit:
            continue
        if str(spec.counterfactual_role) == "source_shape_changed_to_target":
            counted_shape_ids_after_edit.append(str(sample.target_shape_id))
        else:
            counted_shape_ids_after_edit.append(str(spec.shape_id))
    final_target_shape_count = int(sample.target_answer)
    query_metadata = {
        _trace_key("query", "id"): str(sample.selected_query_id),
        "internal_query_id": str(sample.internal_query_id),
        "target_answer": int(sample.target_answer),
        "object_count": int(sample.object_count),
        "target_shape_id": str(sample.target_shape_id),
        "target_shape_name": str(sample.target_shape_name),
        "source_shape_id": str(sample.source_shape_id),
        "source_shape_name": str(sample.source_shape_name),
        "remove_shape_id": str(sample.remove_shape_id),
        "remove_shape_name": str(sample.remove_shape_name),
        "source_count": int(sample.source_count),
        "existing_target_count": int(sample.existing_target_count),
        "removal_count": int(sample.removal_count),
        "distractor_count": int(sample.distractor_count),
        "shape_id_support": list(_shape_support(params, gen_defaults, min_count=6)),
        "query_probabilities": dict(sample.public_query_probabilities),
        "query_id_probabilities": dict(sample.public_query_probabilities),
        "internal_query_probabilities": dict(sample.internal_query_probabilities),
        "shape_probabilities": dict(sample.shape_probabilities),
        "target_count_probabilities": dict(sample.target_count_probabilities),
        "removal_count_probabilities": dict(sample.removal_count_probabilities),
        "distractor_count_probabilities": dict(sample.distractor_count_probabilities),
        "arrangement_mode": str(sample.arrangement_mode),
        "arrangement_mode_probabilities": dict(sample.arrangement_mode_probabilities),
        "named_icon_fill_style_support": list(sample.fill_style_support),
        "fill_style_probabilities": dict(sample.fill_style_probabilities),
    }
    trace_payload = {
        "scene_ir": {
            "scene_kind": "icons_named_shape_counterfactual_field",
            "scene_id": SCENE_ID,
            "entities": list(serialized_instances),
            "relations": {
                "counting_rule": "apply_hypothetical_icon_removal_or_replacement_then_count",
                _trace_key("query", "id"): str(sample.selected_query_id),
                "internal_query_id": str(sample.internal_query_id),
                "target_shape_id": str(sample.target_shape_id),
                "target_shape_name": str(sample.target_shape_name),
                "source_shape_id": str(sample.source_shape_id),
                "source_shape_name": str(sample.source_shape_name),
                "remove_shape_id": str(sample.remove_shape_id),
                "remove_shape_name": str(sample.remove_shape_name),
                "source_count": int(sample.source_count),
                "existing_target_count": int(sample.existing_target_count),
                "removal_count": int(sample.removal_count),
                "distractor_count": int(sample.distractor_count),
                "shape_counts": {str(key): int(value) for key, value in shape_counts.items()},
                "role_by_instance_id": dict(role_by_instance_id),
                "arrangement_mode": str(sample.arrangement_mode),
            },
            "frames": {
                "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                "panels": dict(scene.panel_geometry),
            },
        },
        "query_spec": {
            _trace_key("query", "id"): str(sample.selected_query_id),
            "internal_query_id": str(sample.internal_query_id),
            "template_id": str(prompt_defaults["bundle_id"]),
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": dict(query_metadata),
        },
        "render_spec": {
            "canvas_size": list(scene.panel_geometry["canvas_size"]),
            "coord_space": "pixel",
            "scene_id": SCENE_ID,
            "panel_geometry": dict(scene.panel_geometry),
            "style": {
                **icon_render_style_trace(render_params=render_params, sampled_palette_rgb=sampled_palette_rgb),
                "layout_mode": str(scene.layout_mode),
                "named_icon_fill_style_support": list(sample.fill_style_support),
                "named_icon_slot_padding_px": int(slot_padding_px),
                "named_icon_slot_jitter_px": int(slot_jitter_px),
                "named_icon_stack_gap_px": int(stack_gap_px),
            },
        },
        "render_map": {
            "image_id": "img0",
            "object_bboxes_px": {
                str(instance.instance_id): [int(value) for value in instance.bbox_xyxy]
                for instance in scene.instances
            },
            "counted_instance_ids": list(counted_instance_ids),
            "role_by_instance_id": dict(role_by_instance_id),
        },
        "execution_trace": {
            "scene_variant": "single_panel_named_shape_counterfactual_field",
            "arrangement_mode": str(sample.arrangement_mode),
            _trace_key("query", "id"): str(sample.selected_query_id),
            "internal_query_id": str(sample.internal_query_id),
            "question_format": "count_named_shape_icons_after_hypothetical_edit",
            "target_answer": int(sample.target_answer),
            "object_count": int(sample.object_count),
            "target_shape_id": str(sample.target_shape_id),
            "target_shape_name": str(sample.target_shape_name),
            "source_shape_id": str(sample.source_shape_id),
            "source_shape_name": str(sample.source_shape_name),
            "remove_shape_id": str(sample.remove_shape_id),
            "remove_shape_name": str(sample.remove_shape_name),
            "source_count": int(sample.source_count),
            "existing_target_count": int(sample.existing_target_count),
            "removal_count": int(sample.removal_count),
            "distractor_count": int(sample.distractor_count),
            "shape_counts": {str(key): int(value) for key, value in shape_counts.items()},
            "final_counted_shape_ids_after_edit": list(counted_shape_ids_after_edit),
            "final_target_shape_count": int(final_target_shape_count),
            "counted_instance_ids": list(counted_instance_ids),
            "role_by_instance_id": dict(role_by_instance_id),
        },
        "witness_symbolic": {
            "answer": int(sample.target_answer),
            "counted_instance_ids": list(counted_instance_ids),
            _trace_key("query", "id"): str(sample.selected_query_id),
            "internal_query_id": str(sample.internal_query_id),
            "target_shape_id": str(sample.target_shape_id),
            "target_shape_name": str(sample.target_shape_name),
            "source_shape_id": str(sample.source_shape_id),
            "source_shape_name": str(sample.source_shape_name),
            "remove_shape_id": str(sample.remove_shape_id),
            "remove_shape_name": str(sample.remove_shape_name),
        },
        "projected_annotation": {**dict(annotation_artifacts["projected_annotation"])},
    }
    return MaterializedNamedFieldTask(
        prompt=str(prompt_artifacts.prompt),
        answer_gt=TypedValue(type="integer", value=int(sample.target_answer)),
        annotation_gt=TypedValue(
            type=str(annotation_artifacts["annotation_type"]),
            value=list(annotation_artifacts["annotation_value"]),
        ),
        image=scene.image,
        trace_payload=trace_payload,
        selected_public_query=str(sample.selected_query_id),
        prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
    )


__all__ = [
    "BOOLEAN_PREDICATE_AND",
    "BOOLEAN_PREDICATE_ATTRIBUTE_WITHOUT_SHAPE",
    "BOOLEAN_PREDICATE_NEITHER",
    "BOOLEAN_PREDICATE_OR",
    "BOOLEAN_PREDICATE_SHAPE_WITHOUT_ATTRIBUTE",
    "BOOLEAN_PREDICATE_XOR",
    "COUNTERFACTUAL_SHAPE_REMOVAL",
    "COUNTERFACTUAL_SHAPE_REPLACEMENT",
    "MaterializedNamedFieldTask",
    "materialize_boolean_count_plan",
    "materialize_counterfactual_count_plan",
]
