"""Count arithmetic over two prompt-named procedural icon groups."""

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
    procedural_named_icon_display_name,
    procedural_named_icon_fill_style_probability_map,
    sample_procedural_named_icon_fill_style,
    validate_procedural_named_icon_fill_style_support,
)


TOTAL_TASK_ID = "task_icons__named_field__shape_pair_total_count"
DIFFERENCE_TASK_ID = "task_icons__named_field__shape_pair_difference_count"
TASK_ID = TOTAL_TASK_ID

QUERY_IDS: Tuple[str, ...] = (
    "two_shape_total_count",
    "two_shape_difference_count",
    "two_bound_color_total_count",
    "two_bound_color_difference_count",
)
TOTAL_QUERY_IDS: Tuple[str, ...] = (
    "two_shape_total_count",
    "two_bound_color_total_count",
)
DIFFERENCE_QUERY_IDS: Tuple[str, ...] = (
    "two_shape_difference_count",
    "two_bound_color_difference_count",
)

_NON_STACK_LAYOUT_MODES: Tuple[str, ...] = (
    "jittered_grid",
    "ordered_grid",
    "shelf_rows",
    "free_scatter",
)


@dataclass(frozen=True)
class _TaskDefaults:
    operand_count_min: int = 1
    operand_count_max: int = 6
    total_answer_min: int = 2
    total_answer_max: int = 10
    difference_answer_min: int = 0
    difference_answer_max: int = 5
    distractor_count_min: int = 4
    distractor_count_max: int = 8
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


@dataclass(frozen=True)
class _NamedColorEntry:
    name: str
    rgb: Tuple[int, int, int]
    label: str


@dataclass(frozen=True)
class _OperandSpec:
    shape_id: str
    shape_name: str
    color_name: str
    color_label: str
    label: str


@dataclass(frozen=True)
class _IconSemanticSpec:
    shape_id: str
    color_name: str
    fill_style: str
    role: str


@dataclass(frozen=True)
class _SampleSpec:
    query_id: str
    operation: str
    uses_color_binding: bool
    left_operand: _OperandSpec
    right_operand: _OperandSpec
    left_count: int
    right_count: int
    target_answer: int
    distractor_count: int
    object_count: int
    arrangement_mode: str
    semantic_specs: Tuple[_IconSemanticSpec, ...]
    query_probabilities: Dict[str, float]
    shape_probabilities: Dict[str, float]
    color_probabilities: Dict[str, float]
    answer_probabilities: Dict[str, float]
    operand_count_probabilities: Dict[str, float]
    distractor_count_probabilities: Dict[str, float]
    fill_style_support: Tuple[str, ...]
    fill_style_probabilities: Dict[str, float]
    arrangement_mode_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("icons", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)



def _shape_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get("shape_id_support", group_default(_GEN_DEFAULTS, "shape_id_support", PROCEDURAL_NAMED_ICON_SHAPES))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("shape_id_support must be a sequence")
    values = tuple(dict.fromkeys(str(value) for value in raw if str(value).strip()))
    unsupported = sorted(set(values) - set(PROCEDURAL_NAMED_ICON_SHAPES))
    if unsupported:
        raise ValueError(f"unsupported procedural named icon shapes: {unsupported}")
    if len(values) < 3:
        raise ValueError("shape_id_support must include at least three shapes")
    return values


def _color_support(params: Mapping[str, Any]) -> Tuple[_NamedColorEntry, ...]:
    color_by_name = {str(name): tuple(int(channel) for channel in rgb) for name, rgb in available_named_colors()}
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




def _query_support(params: Mapping[str, Any], *, default_query_ids: Sequence[str] = QUERY_IDS) -> Tuple[str, ...]:
    raw = params.get("pair_arithmetic_query_ids", tuple(str(value) for value in default_query_ids))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("pair_arithmetic_query_ids must be a sequence")
    values = tuple(dict.fromkeys(str(value) for value in raw if str(value).strip()))
    unsupported = sorted(set(values) - set(QUERY_IDS))
    if unsupported:
        raise ValueError(f"unsupported named-icon pair-arithmetic query ids: {unsupported}")
    if not values:
        raise ValueError("pair_arithmetic_query_ids resolved no query ids")
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
        raise ValueError(f"named-icon pair arithmetic only supports non-stack layouts; got {unsupported}")
    modes = tuple(dict.fromkeys(values))
    if not modes:
        raise ValueError("named_icon_layout_modes resolved no supported non-stack layouts")
    return modes



def _choose_other(rng, values: Sequence[str], excluded: Sequence[str]) -> str:
    excluded_set = {str(value) for value in excluded}
    candidates = [str(value) for value in values if str(value) not in excluded_set]
    if not candidates:
        raise ValueError("no alternate value available")
    return str(rng.choice(candidates))


def _operation_for_query(query_id: str) -> str:
    if str(query_id).endswith("_total_count"):
        return "total"
    if str(query_id).endswith("_difference_count"):
        return "absolute_difference"
    raise ValueError(f"unsupported pair-arithmetic query id: {query_id}")


def _answer_support(params: Mapping[str, Any], *, operation: str) -> Tuple[int, ...]:
    if str(operation) == "total":
        low, high = resolve_named_icon_int_bounds(params, _GEN_DEFAULTS, "total_answer_min", "total_answer_max", _DEFAULTS.total_answer_min, _DEFAULTS.total_answer_max)
    elif str(operation) == "absolute_difference":
        low, high = resolve_named_icon_int_bounds(params, _GEN_DEFAULTS,
            "difference_answer_min",
            "difference_answer_max",
            _DEFAULTS.difference_answer_min,
            _DEFAULTS.difference_answer_max,
        )
    else:
        raise ValueError(f"unsupported operation: {operation}")
    return tuple(range(int(low), int(high) + 1))


def _feasible_operand_pairs(
    *,
    operation: str,
    target_answer: int,
    operand_min: int,
    operand_max: int,
) -> Tuple[Tuple[int, int], ...]:
    pairs: list[Tuple[int, int]] = []
    for left in range(int(operand_min), int(operand_max) + 1):
        for right in range(int(operand_min), int(operand_max) + 1):
            if str(operation) == "total" and int(left) + int(right) == int(target_answer):
                pairs.append((int(left), int(right)))
            elif str(operation) == "absolute_difference" and abs(int(left) - int(right)) == int(target_answer):
                pairs.append((int(left), int(right)))
    return tuple(pairs)


def _sample_operand_counts(
    *,
    params: Mapping[str, Any],
    rng,
    operation: str,
) -> Tuple[int, int, int, Dict[str, float], Dict[str, float]]:
    operand_min, operand_max = resolve_named_icon_int_bounds(params, _GEN_DEFAULTS,
        "operand_count_min",
        "operand_count_max",
        _DEFAULTS.operand_count_min,
        _DEFAULTS.operand_count_max,
    )
    if operand_min < 1:
        raise ValueError("named-icon pair arithmetic uses operand_count_min >= 1")
    answer_support = _answer_support(params, operation=str(operation))
    feasible_answer_support = tuple(
        int(answer)
        for answer in answer_support
        if _feasible_operand_pairs(
            operation=str(operation),
            target_answer=int(answer),
            operand_min=int(operand_min),
            operand_max=int(operand_max),
        )
    )
    if not feasible_answer_support:
        raise ValueError("answer support has no feasible operand-count pairs")
    answer_probabilities = weighted_probability_map(
        feasible_answer_support,
        params.get("answer_weights", group_default(_GEN_DEFAULTS, "answer_weights", None)),
    )
    explicit_answer = params.get("target_answer", params.get("answer"))
    if explicit_answer is not None:
        target_answer = int(explicit_answer)
        if target_answer not in set(feasible_answer_support):
            raise ValueError(f"target_answer must be in feasible support {feasible_answer_support}")
    else:
        target_answer = int(sample_weighted_value(rng, feasible_answer_support, answer_probabilities))

    explicit_left = params.get("left_count")
    explicit_right = params.get("right_count")
    if explicit_left is not None or explicit_right is not None:
        if explicit_left is None or explicit_right is None:
            raise ValueError("left_count and right_count must be provided together")
        left_count = int(explicit_left)
        right_count = int(explicit_right)
        if not (int(operand_min) <= left_count <= int(operand_max) and int(operand_min) <= right_count <= int(operand_max)):
            raise ValueError("left_count/right_count outside operand count support")
        expected = left_count + right_count if str(operation) == "total" else abs(left_count - right_count)
        if int(expected) != int(target_answer):
            raise ValueError("left_count/right_count do not match target_answer")
    else:
        pairs = _feasible_operand_pairs(
            operation=str(operation),
            target_answer=int(target_answer),
            operand_min=int(operand_min),
            operand_max=int(operand_max),
        )
        left_count, right_count = tuple(int(value) for value in rng.choice(pairs))

    operand_support = tuple(range(int(operand_min), int(operand_max) + 1))
    return (
        int(left_count),
        int(right_count),
        int(target_answer),
        dict(uniform_probability_map(feasible_answer_support, selected=int(target_answer)) if explicit_answer is not None else answer_probabilities),
        dict(uniform_probability_map(operand_support)),
    )


def _sample_operands(
    *,
    params: Mapping[str, Any],
    rng,
    shape_support: Sequence[str],
    color_support: Sequence[_NamedColorEntry],
    uses_color_binding: bool,
) -> Tuple[_OperandSpec, _OperandSpec, Dict[str, float], Dict[str, float]]:
    explicit_left_shape = params.get("left_shape_id")
    explicit_right_shape = params.get("right_shape_id")
    if explicit_left_shape is not None:
        left_shape_id = str(explicit_left_shape)
        if left_shape_id not in set(shape_support):
            raise ValueError(f"left_shape_id must be one of {tuple(shape_support)}")
    else:
        left_shape_id = str(rng.choice(tuple(shape_support)))
    if explicit_right_shape is not None:
        right_shape_id = str(explicit_right_shape)
        if right_shape_id not in set(shape_support):
            raise ValueError(f"right_shape_id must be one of {tuple(shape_support)}")
        if right_shape_id == left_shape_id:
            raise ValueError("left_shape_id and right_shape_id must be distinct")
    else:
        right_shape_id = _choose_other(rng, shape_support, (left_shape_id,))

    color_by_name = {str(entry.name): entry for entry in color_support}
    color_names = tuple(color_by_name)
    explicit_left_color = params.get("left_color_name")
    explicit_right_color = params.get("right_color_name")
    if uses_color_binding:
        if explicit_left_color is not None:
            left_color_name = str(explicit_left_color).strip().lower()
            if left_color_name not in color_by_name:
                raise ValueError(f"left_color_name must be one of {color_names}")
        else:
            left_color_name = str(rng.choice(color_support).name)
        if explicit_right_color is not None:
            right_color_name = str(explicit_right_color).strip().lower()
            if right_color_name not in color_by_name:
                raise ValueError(f"right_color_name must be one of {color_names}")
            if right_color_name == left_color_name:
                raise ValueError("left_color_name and right_color_name must be distinct for color-bound queries")
        else:
            right_color_name = _choose_other(rng, color_names, (left_color_name,))
    else:
        left_color_name = ""
        right_color_name = ""

    def make_operand(shape_id: str, color_name: str) -> _OperandSpec:
        shape_name = procedural_named_icon_display_name(str(shape_id))
        if str(color_name):
            color_label = str(color_by_name[str(color_name)].label)
            label = f"{color_label} {shape_name}"
        else:
            color_label = ""
            label = str(shape_name)
        return _OperandSpec(
            shape_id=str(shape_id),
            shape_name=str(shape_name),
            color_name=str(color_name),
            color_label=str(color_label),
            label=str(label),
        )

    return (
        make_operand(str(left_shape_id), str(left_color_name)),
        make_operand(str(right_shape_id), str(right_color_name)),
        uniform_string_probability_map(shape_support),
        uniform_string_probability_map(color_names),
    )


def _matches_operand(spec: _IconSemanticSpec, operand: _OperandSpec, *, uses_color_binding: bool) -> bool:
    if str(spec.shape_id) != str(operand.shape_id):
        return False
    if bool(uses_color_binding):
        return str(spec.color_name) == str(operand.color_name)
    return True


def _semantic_specs(
    *,
    params: Mapping[str, Any],
    rng,
    left_operand: _OperandSpec,
    right_operand: _OperandSpec,
    left_count: int,
    right_count: int,
    distractor_count: int,
    uses_color_binding: bool,
    shape_support: Sequence[str],
    color_support: Sequence[_NamedColorEntry],
    fill_style_support: Sequence[str],
    fill_style_probabilities: Mapping[str, float],
) -> Tuple[_IconSemanticSpec, ...]:
    color_names = tuple(str(entry.name) for entry in color_support)
    specs: list[_IconSemanticSpec] = []

    def random_fill_style() -> str:
        return sample_procedural_named_icon_fill_style(
            rng,
            support=fill_style_support,
            probabilities=dict(fill_style_probabilities),
        )

    def random_color(excluded: Sequence[str] = ()) -> str:
        return _choose_other(rng, color_names, tuple(str(value) for value in excluded))

    for _ in range(int(left_count)):
        specs.append(
            _IconSemanticSpec(
                shape_id=str(left_operand.shape_id),
                color_name=str(left_operand.color_name or random_color()),
                fill_style=random_fill_style(),
                role="left_operand",
            )
        )
    for _ in range(int(right_count)):
        specs.append(
            _IconSemanticSpec(
                shape_id=str(right_operand.shape_id),
                color_name=str(right_operand.color_name or random_color()),
                fill_style=random_fill_style(),
                role="right_operand",
            )
        )

    for _ in range(int(distractor_count)):
        if bool(uses_color_binding):
            shape_id = str(rng.choice(tuple(shape_support)))
            color_name = str(rng.choice(color_names))
            for _attempt in range(40):
                candidate = _IconSemanticSpec(
                    shape_id=str(shape_id),
                    color_name=str(color_name),
                    fill_style=random_fill_style(),
                    role="distractor",
                )
                if not _matches_operand(candidate, left_operand, uses_color_binding=True) and not _matches_operand(
                    candidate,
                    right_operand,
                    uses_color_binding=True,
                ):
                    specs.append(candidate)
                    break
                shape_id = str(rng.choice(tuple(shape_support)))
                color_name = str(rng.choice(color_names))
            else:
                raise RuntimeError("could not sample color-bound distractor")
        else:
            specs.append(
                _IconSemanticSpec(
                    shape_id=_choose_other(rng, shape_support, (left_operand.shape_id, right_operand.shape_id)),
                    color_name=str(rng.choice(color_names)),
                    fill_style=random_fill_style(),
                    role="distractor",
                )
            )

    rng.shuffle(specs)
    return tuple(specs)


def _sample_spec(
    *,
    task_id: str,
    query_ids: Sequence[str],
    instance_seed: int,
    params: Mapping[str, Any],
) -> _SampleSpec:
    rng = spawn_rng(int(instance_seed), f"{task_id}:sample")
    shape_support = _shape_support(params)
    color_support = _color_support(params)
    fill_style_support = resolve_named_icon_fill_style_support(params, _GEN_DEFAULTS, fallback_support=_DEFAULTS.named_icon_fill_style_support)
    fill_style_probabilities = resolve_named_icon_fill_style_probabilities(params, _GEN_DEFAULTS, fill_style_support)
    query_support = _query_support(params, default_query_ids=query_ids)
    arrangement_support = _arrangement_mode_support(params)

    explicit_query = params.get("query_id", params.get("pair_arithmetic_query_id"))
    if explicit_query is not None:
        query_id = str(explicit_query)
        if query_id not in query_support:
            raise ValueError(f"query_id must be one of {query_support}")
    else:
        query_probabilities = weighted_probability_map(
            query_support,
            params.get("query_weights", group_default(_GEN_DEFAULTS, "query_weights", None)),
        )
        query_id = str(sample_weighted_value(rng, query_support, query_probabilities))
    operation = _operation_for_query(str(query_id))
    uses_color_binding = "bound_color" in str(query_id)

    left_count, right_count, target_answer, answer_probabilities, operand_count_probabilities = _sample_operand_counts(
        params=params,
        rng=rng,
        operation=str(operation),
    )
    left_operand, right_operand, shape_probabilities, color_probabilities = _sample_operands(
        params=params,
        rng=rng,
        shape_support=shape_support,
        color_support=color_support,
        uses_color_binding=bool(uses_color_binding),
    )

    distractor_min, distractor_max = resolve_named_icon_int_bounds(params, _GEN_DEFAULTS,
        "distractor_count_min",
        "distractor_count_max",
        _DEFAULTS.distractor_count_min,
        _DEFAULTS.distractor_count_max,
    )
    explicit_distractor_count = params.get("distractor_count")
    distractor_support = tuple(range(int(distractor_min), int(distractor_max) + 1))
    if explicit_distractor_count is not None:
        distractor_count = int(explicit_distractor_count)
        if distractor_count not in set(distractor_support):
            raise ValueError(f"distractor_count must be in {distractor_support}")
    else:
        distractor_count = int(rng.choice(distractor_support))

    semantic_specs = _semantic_specs(
        params=params,
        rng=rng,
        left_operand=left_operand,
        right_operand=right_operand,
        left_count=int(left_count),
        right_count=int(right_count),
        distractor_count=int(distractor_count),
        uses_color_binding=bool(uses_color_binding),
        shape_support=shape_support,
        color_support=color_support,
        fill_style_support=fill_style_support,
        fill_style_probabilities=fill_style_probabilities,
    )

    explicit_arrangement = params.get("arrangement_mode", params.get("layout_mode"))
    if explicit_arrangement is not None:
        arrangement_mode = str(explicit_arrangement)
        if arrangement_mode not in set(arrangement_support):
            raise ValueError(f"named-icon pair arithmetic only supports non-stack layouts: {arrangement_support}")
    else:
        arrangement_mode = str(rng.choice(arrangement_support))

    return _SampleSpec(
        query_id=str(query_id),
        operation=str(operation),
        uses_color_binding=bool(uses_color_binding),
        left_operand=left_operand,
        right_operand=right_operand,
        left_count=int(left_count),
        right_count=int(right_count),
        target_answer=int(target_answer),
        distractor_count=int(distractor_count),
        object_count=int(len(semantic_specs)),
        arrangement_mode=str(arrangement_mode),
        semantic_specs=tuple(semantic_specs),
        query_probabilities=(
            {str(query_id): 1.0}
            if explicit_query is not None
            else dict(weighted_probability_map(query_support, params.get("query_weights", group_default(_GEN_DEFAULTS, "query_weights", None))))
        ),
        shape_probabilities=dict(shape_probabilities),
        color_probabilities=dict(color_probabilities),
        answer_probabilities=dict(answer_probabilities),
        operand_count_probabilities=dict(operand_count_probabilities),
        distractor_count_probabilities=dict(uniform_probability_map(distractor_support, selected=int(distractor_count) if explicit_distractor_count is not None else None)),
        fill_style_support=tuple(fill_style_support),
        fill_style_probabilities=dict(fill_style_probabilities),
        arrangement_mode_probabilities=uniform_string_probability_map(arrangement_support, selected=str(arrangement_mode) if explicit_arrangement is not None else None),
    )



def _build_scene_specs(
    *,
    sample: _SampleSpec,
    instance_seed: int,
    render_params: Mapping[str, Any],
    task_id: str,
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
            namespace=f"{task_id}:named_icon_{int(index)}",
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


def _counted_instance_ids(sample: _SampleSpec, instances: Sequence[Any]) -> Tuple[str, ...]:
    left_ids = []
    right_ids = []
    for instance in instances:
        spec = _IconSemanticSpec(
            shape_id=str(instance.shape_id),
            color_name=str(instance.color_name),
            fill_style=str(instance.fill_style),
            role="",
        )
        if _matches_operand(spec, sample.left_operand, uses_color_binding=bool(sample.uses_color_binding)):
            left_ids.append(str(instance.instance_id))
        elif _matches_operand(spec, sample.right_operand, uses_color_binding=bool(sample.uses_color_binding)):
            right_ids.append(str(instance.instance_id))
    return tuple(left_ids + right_ids)


def _role_by_instance_id(sample: _SampleSpec) -> Dict[str, str]:
    return {
        f"named_icon_{int(index):02d}": str(semantic_spec.role)
        for index, semantic_spec in enumerate(sample.semantic_specs)
    }


def _evidence_bboxes(sample: _SampleSpec, instances: Sequence[Any]) -> list[list[int]]:
    counted_ids = set(_counted_instance_ids(sample, instances))
    return sort_bboxes_reading_order(tuple(instance.bbox_xyxy for instance in instances if str(instance.instance_id) in counted_ids))


def _complexity(sample: _SampleSpec, *, render_params: Mapping[str, Any]) -> TaskComplexity:
    visual_scan = (int(sample.object_count) - 6) / max(1, 20 - 6)
    answer_load = (
        float(sample.target_answer) / 10.0
        if str(sample.operation) == "total"
        else float(sample.target_answer) / max(1.0, float(_DEFAULTS.difference_answer_max))
    )
    operation_difficulty = 0.35 if str(sample.operation) == "total" else 0.65
    attribute_binding = 0.40 if bool(sample.uses_color_binding) else 0.0
    shape_diversity = len(set(spec.shape_id for spec in sample.semantic_specs)) / max(1.0, float(sample.object_count))
    color_diversity = len(set(spec.color_name for spec in sample.semantic_specs)) / max(1.0, float(sample.object_count))
    score = (
        0.26 * max(0.0, min(1.0, visual_scan))
        + 0.20 * max(0.0, min(1.0, answer_load))
        + 0.24 * float(operation_difficulty)
        + 0.16 * float(attribute_binding)
        + 0.08 * max(0.0, min(1.0, shape_diversity))
        + 0.06 * max(0.0, min(1.0, color_diversity))
    )
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={
            "visual_scan": round(float(visual_scan), 6),
            "answer_load": round(float(answer_load), 6),
            "operation_difficulty": round(float(operation_difficulty), 6),
            "attribute_binding": round(float(attribute_binding), 6),
            "shape_diversity": round(float(shape_diversity), 6),
            "color_diversity": round(float(color_diversity), 6),
            "object_count": int(sample.object_count),
            "target_answer": int(sample.target_answer),
            "left_count": int(sample.left_count),
            "right_count": int(sample.right_count),
            "operation": str(sample.operation),
            "query_id": str(sample.query_id),
            "uses_color_binding": bool(sample.uses_color_binding),
            "arrangement_mode": str(sample.arrangement_mode),
            "scene_icon_size_min_px": int(render_params["scene_icon_size_min_px"]),
            "scene_icon_size_max_px": int(render_params["scene_icon_size_max_px"]),
        },
    )


def _question_text(prompt_defaults: Mapping[str, Any], sample: _SampleSpec) -> str:
    question_key = f"question_text_{sample.query_id}"
    return str(prompt_defaults[question_key]).format(
        left_shape_name=str(sample.left_operand.shape_name),
        right_shape_name=str(sample.right_operand.shape_name),
        left_operand_label=str(sample.left_operand.label),
        right_operand_label=str(sample.right_operand.label),
    )


class _IconsNamedShapePairArithmeticCountTaskBase:
    """Shared implementation for two named-icon group arithmetic tasks."""

    task_id = TASK_ID
    domain = "icons"
    task_group = "counting"
    query_ids: Tuple[str, ...] = QUERY_IDS

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
                sample = _sample_spec(
                    task_id=str(self.task_id),
                    query_ids=tuple(self.query_ids),
                    instance_seed=int(instance_seed),
                    params=params,
                )
                scene_rng = spawn_rng(int(instance_seed), f"{self.task_id}:scene", int(attempt))
                icon_specs, sampled_palette_rgb = _build_scene_specs(
                    sample=sample,
                    instance_seed=int(instance_seed),
                    render_params=render_params,
                    task_id=str(self.task_id),
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
            raise RuntimeError(f"could not generate {self.task_id}: {last_error}") from last_error

        counted_instance_ids = _counted_instance_ids(sample, scene.instances)
        evidence_bboxes = _evidence_bboxes(sample, scene.instances)
        if len(evidence_bboxes) != int(sample.left_count) + int(sample.right_count):
            raise RuntimeError("rendered named-icon pair arithmetic evidence did not match operand counts")

        _, _, active_prompt_defaults = split_generation_rendering_prompt_defaults(
            _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
            task_id=str(self.task_id),
        )
        question_key = f"question_text_{sample.query_id}"
        prompt_defaults = required_group_defaults(
            active_prompt_defaults,
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
                "question_text": _question_text(active_prompt_defaults, sample),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]).format(
                    left_operand_label=str(sample.left_operand.label),
                    right_operand_label=str(sample.right_operand.label),
                ),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        role_by_instance_id = _role_by_instance_id(sample)
        serialized_instances = []
        for instance in scene.instances:
            entity = serialize_named_icon_instance(instance)
            entity["operand_role"] = str(role_by_instance_id.get(str(instance.instance_id), ""))
            serialized_instances.append(entity)
        shape_counts = Counter(str(instance.shape_id) for instance in scene.instances)
        color_counts = Counter(str(instance.color_name) for instance in scene.instances)
        shape_color_counts = Counter(f"{instance.shape_id}|{instance.color_name}" for instance in scene.instances)
        left_instance_ids = tuple(
            str(instance_id)
            for instance_id in counted_instance_ids
            if role_by_instance_id.get(str(instance_id)) == "left_operand"
        )
        right_instance_ids = tuple(
            str(instance_id)
            for instance_id in counted_instance_ids
            if role_by_instance_id.get(str(instance_id)) == "right_operand"
        )
        if len(left_instance_ids) != int(sample.left_count) or len(right_instance_ids) != int(sample.right_count):
            raise RuntimeError("operand role counts do not match sampled counts")

        trace_payload = {
            "scene_ir": {
                "scene_kind": "icons_named_shape_pair_arithmetic_field",
                "scene_id": SCENE_ID,
                "entities": list(serialized_instances),
                "relations": {
                    "counting_rule": "two_operand_total_or_absolute_difference",
                    "operation": str(sample.operation),
                    "uses_color_binding": bool(sample.uses_color_binding),
                    "left_operand": {
                        "shape_id": str(sample.left_operand.shape_id),
                        "shape_name": str(sample.left_operand.shape_name),
                        "color_name": str(sample.left_operand.color_name),
                        "color_label": str(sample.left_operand.color_label),
                        "label": str(sample.left_operand.label),
                    },
                    "right_operand": {
                        "shape_id": str(sample.right_operand.shape_id),
                        "shape_name": str(sample.right_operand.shape_name),
                        "color_name": str(sample.right_operand.color_name),
                        "color_label": str(sample.right_operand.color_label),
                        "label": str(sample.right_operand.label),
                    },
                    "left_count": int(sample.left_count),
                    "right_count": int(sample.right_count),
                    "target_answer": int(sample.target_answer),
                    "shape_counts": {str(key): int(value) for key, value in shape_counts.items()},
                    "color_counts": {str(key): int(value) for key, value in color_counts.items()},
                    "shape_color_counts": {str(key): int(value) for key, value in shape_color_counts.items()},
                    "arrangement_mode": str(sample.arrangement_mode),
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(scene.panel_geometry),
                },
            },
            "query_spec": {
                "query_variant": "default",
                "query_id": str(sample.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(sample.query_id),
                    "operation": str(sample.operation),
                    "uses_color_binding": bool(sample.uses_color_binding),
                    "left_operand": {
                        "shape_id": str(sample.left_operand.shape_id),
                        "shape_name": str(sample.left_operand.shape_name),
                        "color_name": str(sample.left_operand.color_name),
                        "color_label": str(sample.left_operand.color_label),
                        "label": str(sample.left_operand.label),
                    },
                    "right_operand": {
                        "shape_id": str(sample.right_operand.shape_id),
                        "shape_name": str(sample.right_operand.shape_name),
                        "color_name": str(sample.right_operand.color_name),
                        "color_label": str(sample.right_operand.color_label),
                        "label": str(sample.right_operand.label),
                    },
                    "left_count": int(sample.left_count),
                    "right_count": int(sample.right_count),
                    "target_answer": int(sample.target_answer),
                    "distractor_count": int(sample.distractor_count),
                    "object_count": int(sample.object_count),
                    "arrangement_mode": str(sample.arrangement_mode),
                    "pair_arithmetic_query_ids": list(_query_support(params, default_query_ids=tuple(self.query_ids))),
                    "query_probabilities": dict(sample.query_probabilities),
                    "shape_id_support": list(_shape_support(params)),
                    "named_color_support": [str(entry.name) for entry in _color_support(params)],
                    "shape_probabilities": dict(sample.shape_probabilities),
                    "color_probabilities": dict(sample.color_probabilities),
                    "answer_probabilities": dict(sample.answer_probabilities),
                    "operand_count_probabilities": dict(sample.operand_count_probabilities),
                    "distractor_count_probabilities": dict(sample.distractor_count_probabilities),
                    "named_icon_fill_style_support": list(sample.fill_style_support),
                    "fill_style_probabilities": dict(sample.fill_style_probabilities),
                    "arrangement_mode_probabilities": dict(sample.arrangement_mode_probabilities),
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
                    "semantic_fill_style_support": list(resolve_named_icon_fill_style_support(params, _GEN_DEFAULTS, fallback_support=_DEFAULTS.named_icon_fill_style_support)),
                },
            },
            "render_map": {
                "image_id": "img0",
                "object_bboxes_px": {
                    str(instance.instance_id): [int(value) for value in instance.bbox_xyxy]
                    for instance in scene.instances
                },
                "counted_instance_ids": list(counted_instance_ids),
                "left_operand_instance_ids": list(left_instance_ids),
                "right_operand_instance_ids": list(right_instance_ids),
                "entity_partition": {
                    str(instance.instance_id): str(role_by_instance_id.get(str(instance.instance_id), ""))
                    for instance in scene.instances
                },
            },
            "execution_trace": {
                "scene_variant": "single_panel_named_shape_pair_arithmetic_field",
                "arrangement_mode": str(sample.arrangement_mode),
                "query_variant": "default",
                "query_id": str(sample.query_id),
                "question_format": "count_named_shape_pair_arithmetic_icons",
                "operation": str(sample.operation),
                "uses_color_binding": bool(sample.uses_color_binding),
                "left_operand": {
                    "shape_id": str(sample.left_operand.shape_id),
                    "shape_name": str(sample.left_operand.shape_name),
                    "color_name": str(sample.left_operand.color_name),
                    "color_label": str(sample.left_operand.color_label),
                    "label": str(sample.left_operand.label),
                },
                "right_operand": {
                    "shape_id": str(sample.right_operand.shape_id),
                    "shape_name": str(sample.right_operand.shape_name),
                    "color_name": str(sample.right_operand.color_name),
                    "color_label": str(sample.right_operand.color_label),
                    "label": str(sample.right_operand.label),
                },
                "left_count": int(sample.left_count),
                "right_count": int(sample.right_count),
                "target_answer": int(sample.target_answer),
                "distractor_count": int(sample.distractor_count),
                "object_count": int(sample.object_count),
                "shape_counts": {str(key): int(value) for key, value in shape_counts.items()},
                "color_counts": {str(key): int(value) for key, value in color_counts.items()},
                "shape_color_counts": {str(key): int(value) for key, value in shape_color_counts.items()},
                "scene_shape_ids": [str(instance.shape_id) for instance in scene.instances],
                "scene_color_names": [str(instance.color_name) for instance in scene.instances],
                "scene_fill_styles": [str(instance.fill_style) for instance in scene.instances],
                "counted_instance_ids": list(counted_instance_ids),
                "left_operand_instance_ids": list(left_instance_ids),
                "right_operand_instance_ids": list(right_instance_ids),
            },
            "witness_symbolic": {
                "operation": str(sample.operation),
                "uses_color_binding": bool(sample.uses_color_binding),
                "left_operand": {
                    "shape_id": str(sample.left_operand.shape_id),
                    "shape_name": str(sample.left_operand.shape_name),
                    "color_name": str(sample.left_operand.color_name),
                    "color_label": str(sample.left_operand.color_label),
                    "label": str(sample.left_operand.label),
                },
                "right_operand": {
                    "shape_id": str(sample.right_operand.shape_id),
                    "shape_name": str(sample.right_operand.shape_name),
                    "color_name": str(sample.right_operand.color_name),
                    "color_label": str(sample.right_operand.color_label),
                    "label": str(sample.right_operand.label),
                },
                "left_count": int(sample.left_count),
                "right_count": int(sample.right_count),
                "answer": int(sample.target_answer),
                "counted_instance_ids": list(counted_instance_ids),
                "left_operand_instance_ids": list(left_instance_ids),
                "right_operand_instance_ids": list(right_instance_ids),
            },
            "projected_evidence": {
                "bbox_set": list(evidence_bboxes),
            },
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(sample.target_answer)),
            evidence_gt=TypedValue(type="bbox_set", value=list(evidence_bboxes)),
            image=scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_complexity(sample, render_params=render_params),
            task_versions=default_task_versions(),
            query_variant="default",
            scene_id=SCENE_ID,
            query_id=str(sample.query_id),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
        )


@register_task
class IconsNamedFieldShapePairTotalCountTask(_IconsNamedShapePairArithmeticCountTaskBase):
    """Count the total across two named icon groups."""

    task_id = TOTAL_TASK_ID
    query_ids = TOTAL_QUERY_IDS


@register_task
class IconsNamedFieldShapePairDifferenceCountTask(_IconsNamedShapePairArithmeticCountTaskBase):
    """Count the absolute difference between two named icon groups."""

    task_id = DIFFERENCE_TASK_ID
    query_ids = DIFFERENCE_QUERY_IDS


__all__ = [
    "DIFFERENCE_QUERY_IDS",
    "IconsNamedFieldShapePairDifferenceCountTask",
    "IconsNamedFieldShapePairTotalCountTask",
    "QUERY_IDS",
    "TOTAL_QUERY_IDS",
]
