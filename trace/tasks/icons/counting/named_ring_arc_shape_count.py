"""Count named icons strictly between two markers along a directed ring arc."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_legibility import resolve_readable_text_style, text_legibility_summary_from_records
from ...shared.text_rendering import draw_text_centered, load_font
from ...shared.variant_sampling import resolve_variant
from ..shared.complexity import build_icon_task_complexity
from ..shared.defaults import ICON_SHARED_DEFAULTS
from ..shared.annotation import bbox_set_annotation
from ..shared.icon_noise import serialize_icon_noise_edits
from ..shared.icon_scene import BBox, draw_single_panel, resolve_single_panel_layout, single_panel_geometry_to_trace, sort_bboxes_reading_order
from ..shared.icon_style import sample_icon_palette
from ..shared.icon_task_rendering import icon_render_style_trace, resolve_icon_render_params, resolve_icon_rgb_param, sample_icon_instance_noise
from ..shared.procedural_named_icon_field_scene import bbox_center_float
from ..shared.procedural_named_icons import (
    PROCEDURAL_NAMED_ICON_FILL_STYLES,
    PROCEDURAL_NAMED_ICON_SHAPES,
    procedural_named_icon_display_name,
    render_procedural_named_icon_rgba,
    sample_procedural_named_icon_fill_style,
    validate_procedural_named_icon_fill_style_support,
)


TASK_ID = "task_icons__named_ring__scoped_attribute_count"
SCENE_ID = "named_ring"
QUERY_IDS: Tuple[str, ...] = ("clockwise_arc_shape_count", "counterclockwise_arc_shape_count")


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for named-ring arc counting."""

    ring_icon_count_min: int = 12
    ring_icon_count_max: int = 22
    answer_count_min: int = 0
    answer_count_max: int = 6
    arc_span_min: int = 3
    arc_span_max: int = 12
    off_arc_target_count_min: int = 1
    off_arc_target_count_max: int = 4
    canvas_width: int = 880
    canvas_height: int = 680
    outer_margin_px: int = ICON_SHARED_DEFAULTS.outer_margin_px
    panel_padding_px: int = ICON_SHARED_DEFAULTS.panel_padding_px
    panel_corner_radius_px: int = ICON_SHARED_DEFAULTS.panel_corner_radius_px
    panel_title_font_size_px: int = ICON_SHARED_DEFAULTS.panel_title_font_size_px
    reference_panel_width_px: int = ICON_SHARED_DEFAULTS.reference_panel_width_px
    reference_icon_size_px: int = ICON_SHARED_DEFAULTS.reference_icon_size_px
    reference_icon_size_min_px: int = ICON_SHARED_DEFAULTS.reference_icon_size_px
    reference_icon_size_max_px: int = ICON_SHARED_DEFAULTS.reference_icon_size_px
    panel_gap_px: int = ICON_SHARED_DEFAULTS.panel_gap_px
    scene_icon_size_min_px: int = 44
    scene_icon_size_max_px: int = 62
    scene_max_overlap_fraction: float = 0.0
    scene_placement_max_attempts: int = ICON_SHARED_DEFAULTS.scene_placement_max_attempts
    scene_size_shrink_rounds: int = ICON_SHARED_DEFAULTS.scene_size_shrink_rounds
    scene_size_shrink_factor: float = ICON_SHARED_DEFAULTS.scene_size_shrink_factor
    palette_size_min: int = 8
    palette_size_max: int = 12
    color_channel_min: int = 24
    color_channel_max: int = 220
    min_color_distance: float = 40.0
    color_distance_space: str = "lab"
    background_color_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.background_color_rgb
    panel_fill_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_fill_rgb
    panel_border_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_border_rgb
    header_text_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.header_text_rgb
    icon_noise_edit_types: Tuple[str, ...] = ICON_SHARED_DEFAULTS.icon_noise_edit_types
    icon_noise_edit_count_range: Tuple[int, int] = ICON_SHARED_DEFAULTS.icon_noise_edit_count_range
    icon_noise_value_ranges: Dict[str, Dict[str, Tuple[float, float]]] = field(
        default_factory=lambda: dict(ICON_SHARED_DEFAULTS.icon_noise_value_ranges)
    )
    named_icon_fill_style_support: Tuple[str, ...] = PROCEDURAL_NAMED_ICON_FILL_STYLES
    ring_margin_px: int = 86
    ring_stroke_width_px: int = 4
    ring_outline_rgb: Tuple[int, int, int] = (142, 154, 178)
    ring_stop_radius_px: int = 4
    ring_stop_fill_rgb: Tuple[int, int, int] = (255, 255, 255)
    ring_stop_outline_rgb: Tuple[int, int, int] = (122, 136, 164)
    marker_label_font_size_px: int = 24
    marker_label_radius_px: int = 18
    marker_label_gap_px: int = 8
    marker_label_background_rgb: Tuple[int, int, int] = (255, 255, 255)
    marker_label_border_rgb: Tuple[int, int, int] = (56, 70, 98)
    marker_label_color_rgb: Tuple[int, int, int] = (39, 50, 72)


@dataclass(frozen=True)
class _SampleSpec:
    """Symbolic named-ring arc-count sample."""

    query_id: str
    direction: str
    target_shape_id: str
    target_shape_name: str
    answer_count: int
    ring_icon_count: int
    arc_span_count: int
    start_index: int
    end_index: int
    arc_indices: Tuple[int, ...]
    counted_indices: Tuple[int, ...]
    off_arc_target_indices: Tuple[int, ...]
    shape_ids_by_index: Tuple[str, ...]
    query_probabilities: Dict[str, float]
    answer_probabilities: Dict[str, float]
    ring_icon_count_probabilities: Dict[str, float]
    arc_span_probabilities: Dict[str, float]
    off_arc_target_count_probabilities: Dict[str, float]
    shape_probabilities: Dict[str, float]
    fill_style_support: Tuple[str, ...]
    fill_style_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RenderedRingIcon:
    """Rendered named-ring icon metadata."""

    instance_id: str
    ring_index: int
    clockwise_position_number: int
    role: str
    marker_label: str
    shape_id: str
    shape_name: str
    bbox_xyxy: Tuple[int, int, int, int]
    center_xy: Tuple[float, float]
    nominal_size_px: int
    tint_rgb: Tuple[int, int, int]
    fill_style: str
    noise_edits: Tuple[Dict[str, Any], ...]
    noise_seed: int | None
    is_target_shape: bool
    is_arc_member: bool
    is_counted: bool


@dataclass(frozen=True)
class _ScenePayload:
    """Trace-ready rendered named-ring scene payload."""

    image: Image.Image
    panel_geometry: Dict[str, Any]
    ring_bbox_xyxy: Tuple[int, int, int, int]
    ring_center_xy: Tuple[float, float]
    ring_radius_xy: Tuple[float, float]
    icons: Tuple[_RenderedRingIcon, ...]
    marker_label_bboxes: Dict[str, Tuple[int, int, int, int]]
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("icons", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _string_probability_map(values: Sequence[str], *, selected: str | None = None) -> Dict[str, float]:
    support = tuple(str(value) for value in values)
    if not support:
        return {}
    if selected is not None:
        return {str(value): (1.0 if str(value) == str(selected) else 0.0) for value in support}
    probability = 1.0 / float(len(support))
    return {str(value): float(probability) for value in support}


def _int_bounds(params: Mapping[str, Any], low_key: str, high_key: str, fallback_low: int, fallback_high: int) -> Tuple[int, int]:
    low = int(params.get(low_key, group_default(_GEN_DEFAULTS, low_key, fallback_low)))
    high = int(params.get(high_key, group_default(_GEN_DEFAULTS, high_key, fallback_high)))
    if low < 0 or high < low:
        raise ValueError(f"invalid {low_key}/{high_key} bounds")
    return int(low), int(high)


def _shape_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get("shape_id_support", group_default(_GEN_DEFAULTS, "shape_id_support", PROCEDURAL_NAMED_ICON_SHAPES))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("shape_id_support must be a sequence")
    values = tuple(dict.fromkeys(str(value).strip() for value in raw if str(value).strip()))
    unsupported = sorted(set(values) - set(PROCEDURAL_NAMED_ICON_SHAPES))
    if unsupported:
        raise ValueError(f"unsupported procedural named icon shapes: {unsupported}")
    if len(values) < 8:
        raise ValueError("named-ring arc task needs at least eight supported named shapes")
    return values


def _fill_style_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get(
        "named_icon_fill_style_support",
        group_default(_GEN_DEFAULTS, "named_icon_fill_style_support", _DEFAULTS.named_icon_fill_style_support),
    )
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raw = _DEFAULTS.named_icon_fill_style_support
    return validate_procedural_named_icon_fill_style_support(tuple(str(value) for value in raw))


def _fill_style_probability_map(params: Mapping[str, Any], support: Sequence[str]) -> Dict[str, float]:
    raw = params.get(
        "named_icon_fill_style_weights",
        group_default(_GEN_DEFAULTS, "named_icon_fill_style_weights", None),
    )
    if not isinstance(raw, Mapping):
        probability = 1.0 / float(len(tuple(support)))
        return {str(value): float(probability) for value in support}
    weights = {str(value): max(0.0, float(raw.get(str(value), 0.0))) for value in support}
    total = sum(float(value) for value in weights.values())
    if total <= 0.0:
        probability = 1.0 / float(len(tuple(support)))
        return {str(value): float(probability) for value in support}
    return {str(value): float(weights[str(value)]) / float(total) for value in support}


def _query_direction(query_id: str) -> str:
    query = str(query_id)
    if query == "clockwise_arc_shape_count":
        return "clockwise"
    if query == "counterclockwise_arc_shape_count":
        return "counterclockwise"
    raise ValueError(f"unsupported named-ring arc query_id: {query_id}")


def _resolve_target_shape(rng, *, params: Mapping[str, Any], support: Sequence[str]) -> Tuple[str, Dict[str, float]]:
    explicit_shape = params.get("shape_id", params.get("target_shape_id"))
    if explicit_shape is not None:
        target_shape_id = str(explicit_shape)
        if target_shape_id not in set(support):
            raise ValueError(f"target shape must be one of {support}")
        return str(target_shape_id), _string_probability_map(tuple(str(value) for value in support), selected=str(target_shape_id))
    target_shape_id = str(rng.choice(tuple(str(value) for value in support)))
    return str(target_shape_id), _string_probability_map(tuple(str(value) for value in support))


def _choose_ring_icon_count(rng, *, params: Mapping[str, Any], answer_count: int) -> Tuple[int, Dict[str, float]]:
    low, high = _int_bounds(params, "ring_icon_count_min", "ring_icon_count_max", _DEFAULTS.ring_icon_count_min, _DEFAULTS.ring_icon_count_max)
    low = max(int(low), int(answer_count) + 6)
    explicit = params.get("ring_icon_count", params.get("object_count"))
    support = tuple(range(int(low), int(high) + 1))
    if not support:
        raise ValueError("ring_icon_count support is empty")
    if explicit is not None:
        value = int(explicit)
        if value not in set(support):
            raise ValueError("ring_icon_count is outside configured support")
        return int(value), uniform_probability_map(support, selected=int(value))
    value = int(rng.choice(support))
    return int(value), uniform_probability_map(support)


def _choose_answer_count(rng, *, params: Mapping[str, Any]) -> Tuple[int, Dict[str, float]]:
    low, high = _int_bounds(params, "answer_count_min", "answer_count_max", _DEFAULTS.answer_count_min, _DEFAULTS.answer_count_max)
    explicit = params.get("answer_count", params.get("target_count", params.get("answer")))
    support = tuple(range(int(low), int(high) + 1))
    if not support:
        raise ValueError("answer_count support is empty")
    if explicit is not None:
        value = int(explicit)
        if value not in set(support):
            raise ValueError("answer_count is outside configured support")
        return int(value), uniform_probability_map(support, selected=int(value))
    value = int(rng.choice(support))
    return int(value), uniform_probability_map(support)


def _arc_indices_between(start_index: int, end_index: int, *, count: int, direction: str) -> Tuple[int, ...]:
    step = 1 if str(direction) == "clockwise" else -1
    values: List[int] = []
    cursor = (int(start_index) + int(step)) % int(count)
    while int(cursor) != int(end_index):
        values.append(int(cursor))
        cursor = (int(cursor) + int(step)) % int(count)
        if len(values) >= int(count):
            raise ValueError("invalid arc endpoints for ring traversal")
    return tuple(values)


def _choose_arc(
    rng,
    *,
    params: Mapping[str, Any],
    direction: str,
    ring_icon_count: int,
    answer_count: int,
) -> Tuple[int, int, int, Tuple[int, ...], Dict[str, float]]:
    low, high = _int_bounds(params, "arc_span_min", "arc_span_max", _DEFAULTS.arc_span_min, _DEFAULTS.arc_span_max)
    low = max(int(low), int(answer_count))
    high = min(int(high), int(ring_icon_count) - 4)
    if high < low:
        raise ValueError("arc_span support is empty")
    support = tuple(range(int(low), int(high) + 1))
    explicit_span = params.get("arc_span_count", params.get("arc_length"))
    if explicit_span is not None:
        arc_span_count = int(explicit_span)
        if arc_span_count not in set(support):
            raise ValueError("arc_span_count is outside configured support")
    else:
        arc_span_count = int(rng.choice(support))
    explicit_start = params.get("start_index")
    start_index = int(explicit_start) % int(ring_icon_count) if explicit_start is not None else int(rng.randrange(int(ring_icon_count)))
    if str(direction) == "clockwise":
        end_index = (int(start_index) + int(arc_span_count) + 1) % int(ring_icon_count)
    else:
        end_index = (int(start_index) - int(arc_span_count) - 1) % int(ring_icon_count)
    explicit_end = params.get("end_index")
    if explicit_end is not None:
        end_index = int(explicit_end) % int(ring_icon_count)
        arc_indices = _arc_indices_between(int(start_index), int(end_index), count=int(ring_icon_count), direction=str(direction))
        if len(arc_indices) != int(arc_span_count):
            raise ValueError("explicit end_index does not match arc_span_count")
    else:
        arc_indices = _arc_indices_between(int(start_index), int(end_index), count=int(ring_icon_count), direction=str(direction))
    return int(start_index), int(end_index), int(arc_span_count), tuple(int(value) for value in arc_indices), uniform_probability_map(support, selected=int(arc_span_count) if explicit_span is not None else None)


def _choose_off_arc_target_count(
    rng,
    *,
    params: Mapping[str, Any],
    feasible_count: int,
) -> Tuple[int, Dict[str, float]]:
    low, high = _int_bounds(
        params,
        "off_arc_target_count_min",
        "off_arc_target_count_max",
        _DEFAULTS.off_arc_target_count_min,
        _DEFAULTS.off_arc_target_count_max,
    )
    high = min(int(high), int(feasible_count))
    low = min(int(low), int(high))
    explicit = params.get("off_arc_target_count")
    support = tuple(range(int(low), int(high) + 1)) if int(high) >= int(low) else (0,)
    if explicit is not None:
        value = int(explicit)
        if value < 0 or value > int(feasible_count):
            raise ValueError("off_arc_target_count is outside feasible support")
        return int(value), uniform_probability_map(support, selected=int(value) if value in set(support) else None)
    if not support:
        return 0, {"0": 1.0}
    value = int(rng.choice(support))
    return int(value), uniform_probability_map(support)


def _sample_spec(*, instance_seed: int, params: Mapping[str, Any]) -> _SampleSpec:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}:sample")
    query_id, query_probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=QUERY_IDS,
        explicit_key="query_id",
        weights_key="query_id_weights",
    )
    direction = _query_direction(str(query_id))
    answer_count, answer_probabilities = _choose_answer_count(rng, params=params)
    ring_icon_count, ring_icon_count_probabilities = _choose_ring_icon_count(rng, params=params, answer_count=int(answer_count))
    start_index, end_index, arc_span_count, arc_indices, arc_span_probabilities = _choose_arc(
        rng,
        params=params,
        direction=str(direction),
        ring_icon_count=int(ring_icon_count),
        answer_count=int(answer_count),
    )
    shape_support = _shape_support(params)
    target_shape_id, shape_probabilities = _resolve_target_shape(rng, params=params, support=shape_support)

    arc_pool = list(int(value) for value in arc_indices)
    rng.shuffle(arc_pool)
    counted_indices = tuple(sorted(arc_pool[: int(answer_count)]))
    blocked = set(arc_indices) | {int(start_index), int(end_index)}
    off_arc_candidates = [index for index in range(int(ring_icon_count)) if int(index) not in blocked]
    off_arc_count, off_arc_probabilities = _choose_off_arc_target_count(
        rng,
        params=params,
        feasible_count=len(off_arc_candidates),
    )
    rng.shuffle(off_arc_candidates)
    off_arc_target_indices = tuple(sorted(int(value) for value in off_arc_candidates[: int(off_arc_count)]))

    target_indices = set(counted_indices) | set(off_arc_target_indices)
    distractor_support = tuple(str(value) for value in shape_support if str(value) != str(target_shape_id))
    shape_ids: List[str] = []
    for index in range(int(ring_icon_count)):
        if int(index) in target_indices:
            shape_ids.append(str(target_shape_id))
        else:
            shape_ids.append(str(rng.choice(distractor_support)))
    for index in (int(start_index), int(end_index)):
        if str(shape_ids[int(index)]) == str(target_shape_id):
            shape_ids[int(index)] = str(rng.choice(distractor_support))

    realized_count = sum(1 for index in arc_indices if str(shape_ids[int(index)]) == str(target_shape_id))
    if int(realized_count) != int(answer_count):
        raise RuntimeError("constructed named-ring arc does not realize requested answer")

    fill_style_support = _fill_style_support(params)
    fill_style_probabilities = _fill_style_probability_map(params, fill_style_support)
    return _SampleSpec(
        query_id=str(query_id),
        direction=str(direction),
        target_shape_id=str(target_shape_id),
        target_shape_name=procedural_named_icon_display_name(str(target_shape_id)),
        answer_count=int(answer_count),
        ring_icon_count=int(ring_icon_count),
        arc_span_count=int(arc_span_count),
        start_index=int(start_index),
        end_index=int(end_index),
        arc_indices=tuple(int(value) for value in arc_indices),
        counted_indices=tuple(int(value) for value in counted_indices),
        off_arc_target_indices=tuple(int(value) for value in off_arc_target_indices),
        shape_ids_by_index=tuple(str(value) for value in shape_ids),
        query_probabilities=dict(query_probabilities),
        answer_probabilities=dict(answer_probabilities),
        ring_icon_count_probabilities=dict(ring_icon_count_probabilities),
        arc_span_probabilities=dict(arc_span_probabilities),
        off_arc_target_count_probabilities=dict(off_arc_probabilities),
        shape_probabilities=dict(shape_probabilities),
        fill_style_support=tuple(fill_style_support),
        fill_style_probabilities=dict(fill_style_probabilities),
    )


def _render_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(key, group_default(_RENDER_DEFAULTS, key, fallback)))


def _render_rgb(params: Mapping[str, Any], key: str, fallback: Sequence[int]) -> Tuple[int, int, int]:
    raw = params.get(key, group_default(_RENDER_DEFAULTS, key, tuple(fallback)))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or len(raw) < 3:
        raw = tuple(fallback)
    return tuple(int(value) for value in raw[:3])


def _previous_text_legibility_records(render_params: Mapping[str, Any]) -> List[Dict[str, Any]]:
    previous_legibility = render_params.get("text_legibility")
    if not isinstance(previous_legibility, Mapping) or not isinstance(previous_legibility.get("records"), list):
        return []
    return [dict(record) for record in previous_legibility["records"] if isinstance(record, Mapping)]


def _resolve_named_ring_rgb(
    *,
    params: Mapping[str, Any],
    key: str,
    fallback: Sequence[int],
    instance_seed: int,
) -> Tuple[int, int, int]:
    return resolve_icon_rgb_param(
        params=params,
        render_defaults=_RENDER_DEFAULTS,
        key=str(key),
        fallback=tuple(int(value) for value in fallback),
        instance_seed=int(instance_seed),
    )


def _resolve_named_ring_render_params(*, params: Mapping[str, Any], instance_seed: int) -> Dict[str, Any]:
    """Resolve named-ring render params and readable marker-label text."""

    render_params = resolve_icon_render_params(
        params=params,
        render_defaults=_RENDER_DEFAULTS,
        fallback_defaults=_DEFAULTS,
        instance_seed=int(instance_seed),
    )
    for key in (
        "ring_margin_px",
        "ring_stroke_width_px",
        "ring_stop_radius_px",
        "marker_label_font_size_px",
        "marker_label_radius_px",
        "marker_label_gap_px",
    ):
        render_params[key] = int(params.get(key, group_default(_RENDER_DEFAULTS, key, getattr(_DEFAULTS, key))))
    for key in (
        "ring_outline_rgb",
        "ring_stop_fill_rgb",
        "ring_stop_outline_rgb",
        "marker_label_background_rgb",
        "marker_label_border_rgb",
        "marker_label_color_rgb",
    ):
        render_params[key] = _resolve_named_ring_rgb(
            params=params,
            key=str(key),
            fallback=getattr(_DEFAULTS, str(key)),
            instance_seed=int(instance_seed),
        )

    marker_label_style = resolve_readable_text_style(
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:marker_label_text",
        role="named_ring_marker_label_text",
        surface_rgbs=(
            tuple(int(value) for value in render_params["marker_label_background_rgb"]),
            tuple(int(value) for value in render_params["panel_fill_rgb"]),
            tuple(int(value) for value in render_params["background_color_rgb"]),
        ),
        preferred_rgbs=(tuple(int(value) for value in render_params["marker_label_color_rgb"]),),
    )
    render_params["marker_label_color_rgb"] = tuple(int(value) for value in marker_label_style.fill_rgb)
    render_params["marker_label_stroke_rgb"] = tuple(
        int(value) for value in render_params["marker_label_background_rgb"]
    )
    marker_label_record = marker_label_style.metadata()
    marker_label_record["stroke_rgb"] = list(render_params["marker_label_stroke_rgb"])
    render_params["text_legibility"] = text_legibility_summary_from_records(
        [*_previous_text_legibility_records(render_params), marker_label_record]
    )
    return render_params


def _named_ring_style_trace(render_params: Mapping[str, Any]) -> Dict[str, Any]:
    """Return named-ring-specific render style metadata."""

    return {
        "ring_margin_px": int(render_params["ring_margin_px"]),
        "ring_stroke_width_px": int(render_params["ring_stroke_width_px"]),
        "ring_outline_rgb": [int(value) for value in render_params["ring_outline_rgb"]],
        "ring_stop_radius_px": int(render_params["ring_stop_radius_px"]),
        "ring_stop_fill_rgb": [int(value) for value in render_params["ring_stop_fill_rgb"]],
        "ring_stop_outline_rgb": [int(value) for value in render_params["ring_stop_outline_rgb"]],
        "marker_label_font_size_px": int(render_params["marker_label_font_size_px"]),
        "marker_label_radius_px": int(render_params["marker_label_radius_px"]),
        "marker_label_gap_px": int(render_params["marker_label_gap_px"]),
        "marker_label_background_rgb": [int(value) for value in render_params["marker_label_background_rgb"]],
        "marker_label_border_rgb": [int(value) for value in render_params["marker_label_border_rgb"]],
        "marker_label_color_rgb": [int(value) for value in render_params["marker_label_color_rgb"]],
        "marker_label_stroke_rgb": [int(value) for value in render_params["marker_label_stroke_rgb"]],
    }


def _icon_bbox(center_xy: Sequence[float], size_px: int) -> Tuple[int, int, int, int]:
    cx, cy = float(center_xy[0]), float(center_xy[1])
    size = int(size_px)
    x0 = int(round(cx - 0.5 * float(size)))
    y0 = int(round(cy - 0.5 * float(size)))
    return (int(x0), int(y0), int(x0 + size), int(y0 + size))


def _marker_label_bbox(
    *,
    icon_center_xy: Tuple[float, float],
    ring_center_xy: Tuple[float, float],
    content_bbox: BBox,
    label_radius_px: int,
    gap_px: int,
    icon_size_px: int,
) -> Tuple[int, int, int, int]:
    dx = float(icon_center_xy[0]) - float(ring_center_xy[0])
    dy = float(icon_center_xy[1]) - float(ring_center_xy[1])
    norm = max(1e-6, math.hypot(dx, dy))
    offset = (0.5 * float(icon_size_px)) + float(gap_px) + float(label_radius_px)
    cx = float(icon_center_xy[0]) + offset * dx / norm
    cy = float(icon_center_xy[1]) + offset * dy / norm
    radius = int(label_radius_px)
    x0 = int(round(cx - radius))
    y0 = int(round(cy - radius))
    x0 = max(int(content_bbox[0]), min(int(content_bbox[2]) - 2 * radius, x0))
    y0 = max(int(content_bbox[1]), min(int(content_bbox[3]) - 2 * radius, y0))
    return (int(x0), int(y0), int(x0 + 2 * radius), int(y0 + 2 * radius))


def _render_scene(
    *,
    sample: _SampleSpec,
    instance_seed: int,
    render_params: Mapping[str, Any],
    params: Mapping[str, Any],
    rng,
) -> _ScenePayload:
    layout = resolve_single_panel_layout(
        canvas_width=int(render_params["canvas_width"]),
        canvas_height=int(render_params["canvas_height"]),
        outer_margin_px=int(render_params["outer_margin_px"]),
        panel_padding_px=int(render_params["panel_padding_px"]),
        title_font_size_px=int(render_params["panel_title_font_size_px"]),
    )
    image = Image.new("RGBA", (int(layout.canvas_width), int(layout.canvas_height)))
    draw_single_panel(
        image=image,
        layout=layout,
        background_rgb=tuple(int(value) for value in render_params["background_color_rgb"]),
        panel_fill_rgb=tuple(int(value) for value in render_params["panel_fill_rgb"]),
        panel_border_rgb=tuple(int(value) for value in render_params["panel_border_rgb"]),
        title_color_rgb=tuple(int(value) for value in render_params["header_text_rgb"]),
        corner_radius_px=int(render_params["panel_corner_radius_px"]),
        title_font_size_px=int(render_params["panel_title_font_size_px"]),
        scene_title="Ring",
        icon_canvas_style=render_params.get("_icon_canvas_style_object"),
    )

    content_bbox = tuple(int(value) for value in layout.scene_content_xyxy)
    min_icon_size = max(16, int(render_params["scene_icon_size_min_px"]))
    max_icon_size = max(min_icon_size, int(render_params["scene_icon_size_max_px"]))
    ring_margin_px = int(render_params.get("ring_margin_px", _render_int(params, "ring_margin_px", _DEFAULTS.ring_margin_px)))
    marker_radius = int(render_params.get("marker_label_radius_px", _render_int(params, "marker_label_radius_px", _DEFAULTS.marker_label_radius_px)))
    marker_gap = int(render_params.get("marker_label_gap_px", _render_int(params, "marker_label_gap_px", _DEFAULTS.marker_label_gap_px)))
    safe_margin = max(int(ring_margin_px), int(0.5 * max_icon_size) + marker_radius + marker_gap + 8)
    cx = 0.5 * float(content_bbox[0] + content_bbox[2])
    cy = 0.5 * float(content_bbox[1] + content_bbox[3])
    rx = 0.5 * float(content_bbox[2] - content_bbox[0]) - float(safe_margin)
    ry = 0.5 * float(content_bbox[3] - content_bbox[1]) - float(safe_margin)
    if rx < 120.0 or ry < 90.0:
        raise ValueError("named-ring content area is too small")
    ring_bbox = (int(round(cx - rx)), int(round(cy - ry)), int(round(cx + rx)), int(round(cy + ry)))

    draw = ImageDraw.Draw(image)
    ring_outline = tuple(int(value) for value in render_params.get("ring_outline_rgb", _render_rgb(params, "ring_outline_rgb", _DEFAULTS.ring_outline_rgb)))
    stop_fill = tuple(int(value) for value in render_params.get("ring_stop_fill_rgb", _render_rgb(params, "ring_stop_fill_rgb", _DEFAULTS.ring_stop_fill_rgb)))
    stop_outline = tuple(int(value) for value in render_params.get("ring_stop_outline_rgb", _render_rgb(params, "ring_stop_outline_rgb", _DEFAULTS.ring_stop_outline_rgb)))
    draw.ellipse(
        ring_bbox,
        outline=ring_outline + (210,),
        width=max(1, int(render_params.get("ring_stroke_width_px", _render_int(params, "ring_stroke_width_px", _DEFAULTS.ring_stroke_width_px)))),
    )

    start_angle = float(rng.uniform(-18.0, 18.0))
    centers: List[Tuple[float, float]] = []
    for index in range(int(sample.ring_icon_count)):
        angle = math.radians(float(start_angle) + (360.0 * float(index) / float(sample.ring_icon_count)))
        center = (float(cx + rx * math.cos(angle)), float(cy + ry * math.sin(angle)))
        centers.append(center)
        stop_radius = int(render_params.get("ring_stop_radius_px", _render_int(params, "ring_stop_radius_px", _DEFAULTS.ring_stop_radius_px)))
        draw.ellipse(
            (
                float(center[0] - stop_radius),
                float(center[1] - stop_radius),
                float(center[0] + stop_radius),
                float(center[1] + stop_radius),
            ),
            fill=stop_fill + (230,),
            outline=stop_outline + (240,),
            width=1,
        )

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
    counted_set = set(int(value) for value in sample.counted_indices)
    arc_set = set(int(value) for value in sample.arc_indices)
    icons: List[_RenderedRingIcon] = []
    for index, center in enumerate(centers):
        shape_id = str(sample.shape_ids_by_index[int(index)])
        fill_style = sample_procedural_named_icon_fill_style(
            rng,
            support=sample.fill_style_support,
            probabilities=sample.fill_style_probabilities,
        )
        tint_rgb = tuple(int(value) for value in rng.choice(palette))
        nominal_size_px = int(rng.randint(int(min_icon_size), int(max_icon_size)))
        noise_edits, noise_seed = sample_icon_instance_noise(
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:ring_icon_{int(index)}",
            render_params=render_params,
        )
        sprite = render_procedural_named_icon_rgba(
            shape_id=str(shape_id),
            size_px=int(nominal_size_px),
            tint_rgb=tuple(int(value) for value in tint_rgb),
            fill_style=str(fill_style),
            rotation_degrees=0,
            noise_edits=tuple(noise_edits),
            noise_seed=int(noise_seed),
        )
        bbox = _icon_bbox(center, int(sprite.size[0]))
        image.alpha_composite(sprite, (int(bbox[0]), int(bbox[1])))
        marker_label = "A" if int(index) == int(sample.start_index) else "B" if int(index) == int(sample.end_index) else ""
        role = "start_marker" if marker_label == "A" else "end_marker" if marker_label == "B" else "arc_icon" if int(index) in arc_set else "outside_arc_icon"
        icons.append(
            _RenderedRingIcon(
                instance_id=f"ring_icon_{int(index):02d}",
                ring_index=int(index),
                clockwise_position_number=int(index) + 1,
                role=str(role),
                marker_label=str(marker_label),
                shape_id=str(shape_id),
                shape_name=procedural_named_icon_display_name(str(shape_id)),
                bbox_xyxy=tuple(int(value) for value in bbox),
                center_xy=(float(center[0]), float(center[1])),
                nominal_size_px=int(nominal_size_px),
                tint_rgb=tuple(int(value) for value in tint_rgb),
                fill_style=str(fill_style),
                noise_edits=tuple(serialize_icon_noise_edits(noise_edits)),
                noise_seed=int(noise_seed),
                is_target_shape=str(shape_id) == str(sample.target_shape_id),
                is_arc_member=int(index) in arc_set,
                is_counted=int(index) in counted_set,
            )
        )

    label_font = load_font(int(render_params.get("marker_label_font_size_px", _render_int(params, "marker_label_font_size_px", _DEFAULTS.marker_label_font_size_px))), bold=True)
    label_bg = tuple(int(value) for value in render_params.get("marker_label_background_rgb", _render_rgb(params, "marker_label_background_rgb", _DEFAULTS.marker_label_background_rgb)))
    label_border = tuple(int(value) for value in render_params.get("marker_label_border_rgb", _render_rgb(params, "marker_label_border_rgb", _DEFAULTS.marker_label_border_rgb)))
    label_color = tuple(int(value) for value in render_params.get("marker_label_color_rgb", _render_rgb(params, "marker_label_color_rgb", _DEFAULTS.marker_label_color_rgb)))
    label_stroke = tuple(int(value) for value in render_params.get("marker_label_stroke_rgb", label_bg))
    marker_label_bboxes: Dict[str, Tuple[int, int, int, int]] = {}
    for marker_label, marker_index in (("A", int(sample.start_index)), ("B", int(sample.end_index))):
        marker_icon = icons[int(marker_index)]
        label_bbox = _marker_label_bbox(
            icon_center_xy=marker_icon.center_xy,
            ring_center_xy=(float(cx), float(cy)),
            content_bbox=content_bbox,
            label_radius_px=int(marker_radius),
            gap_px=int(marker_gap),
            icon_size_px=int(marker_icon.nominal_size_px),
        )
        draw.rounded_rectangle(
            label_bbox,
            radius=int(marker_radius),
            fill=label_bg + (245,),
            outline=label_border + (255,),
            width=2,
        )
        draw_text_centered(
            draw,
            text=str(marker_label),
            center=bbox_center_float(label_bbox),
            font=label_font,
            fill=label_color,
            stroke_fill=label_stroke,
            stroke_width=1,
        )
        marker_label_bboxes[str(marker_label)] = tuple(int(value) for value in label_bbox)

    return _ScenePayload(
        image=image.convert("RGB"),
        panel_geometry=single_panel_geometry_to_trace(layout),
        ring_bbox_xyxy=tuple(int(value) for value in ring_bbox),
        ring_center_xy=(float(cx), float(cy)),
        ring_radius_xy=(float(rx), float(ry)),
        icons=tuple(icons),
        marker_label_bboxes={str(key): tuple(int(value) for value in bbox) for key, bbox in marker_label_bboxes.items()},
        sampled_palette_rgb=tuple(tuple(int(channel) for channel in color) for color in palette),
    )


def _serialize_icon(icon: _RenderedRingIcon) -> Dict[str, Any]:
    return {
        "entity_kind": "named_icon",
        "instance_id": str(icon.instance_id),
        "ring_index": int(icon.ring_index),
        "clockwise_position_number": int(icon.clockwise_position_number),
        "role": str(icon.role),
        "marker_label": str(icon.marker_label),
        "shape_id": str(icon.shape_id),
        "shape_name": str(icon.shape_name),
        "bbox_xyxy": [int(value) for value in icon.bbox_xyxy],
        "center_xy": [float(icon.center_xy[0]), float(icon.center_xy[1])],
        "nominal_size_px": int(icon.nominal_size_px),
        "tint_rgb": [int(value) for value in icon.tint_rgb],
        "fill_style": str(icon.fill_style),
        "noise_edits": [dict(value) for value in icon.noise_edits],
        "noise_seed": None if icon.noise_seed is None else int(icon.noise_seed),
        "is_target_shape": bool(icon.is_target_shape),
        "is_arc_member": bool(icon.is_arc_member),
        "is_counted": bool(icon.is_counted),
    }


def _complexity(sample: _SampleSpec, *, scene: _ScenePayload, render_params: Mapping[str, Any]) -> TaskComplexity:
    visual_scan = (float(sample.ring_icon_count) - float(_DEFAULTS.ring_icon_count_min)) / max(1.0, float(_DEFAULTS.ring_icon_count_max - _DEFAULTS.ring_icon_count_min))
    arc_scan = float(sample.arc_span_count) / max(1.0, float(sample.ring_icon_count - 2))
    answer_load = float(sample.answer_count) / max(1.0, float(_DEFAULTS.answer_count_max))
    noise_cap = max((int(value) for value in render_params["icon_noise_edit_count_range"]), default=0)
    clutter = (
        min(1.0, sum(len(icon.noise_edits) for icon in scene.icons) / float(max(1, len(scene.icons) * noise_cap)))
        if int(noise_cap) > 0
        else 0.0
    )
    return build_icon_task_complexity(
        task_group_defaults=_TASK_GROUP_DEFAULTS,
        task_id=TASK_ID,
        criterion_values={
            "semantic_match": 0.50,
            "visual_scan": max(0.0, min(1.0, visual_scan)),
            "ambiguity": max(0.0, min(1.0, (0.55 * arc_scan) + (0.45 * answer_load))),
            "clutter": max(0.0, min(1.0, clutter)),
        },
    )


@register_task
class IconsCountingNamedRingArcShapeCountTask:
    """Count named icons on a directed arc between markers A and B."""

    task_id = TASK_ID
    domain = "icons"
    task_group = "counting"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        render_params = _resolve_named_ring_render_params(params=params, instance_seed=int(instance_seed))
        last_error: Exception | None = None
        sample: _SampleSpec | None = None
        scene: _ScenePayload | None = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                sample = _sample_spec(instance_seed=int(instance_seed), params=params)
                scene_rng = spawn_rng(int(instance_seed), f"{TASK_ID}:scene", int(attempt))
                scene = _render_scene(
                    sample=sample,
                    instance_seed=int(instance_seed),
                    render_params=render_params,
                    params=params,
                    rng=scene_rng,
                )
                break
            except Exception as exc:  # pragma: no cover - covered by smoke tests.
                last_error = exc
                sample = None
                scene = None
        if sample is None or scene is None:
            raise RuntimeError(f"could not generate {TASK_ID}: {last_error}") from last_error

        counted_icons = tuple(icon for icon in scene.icons if bool(icon.is_counted))
        annotation_bboxes = sort_bboxes_reading_order(icon.bbox_xyxy for icon in counted_icons)
        if len(annotation_bboxes) != int(sample.answer_count):
            raise RuntimeError("rendered named-ring annotation count does not match answer")
        annotation_payload = bbox_set_annotation(annotation_bboxes)

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "question_text_clockwise_arc_shape_count",
                "question_text_counterclockwise_arc_shape_count",
                "annotation_hint",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        question_key = f"question_text_{sample.query_id}"
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "question_text": str(prompt_defaults[question_key]).format(target_shape_name=str(sample.target_shape_name)),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint"]).format(
                    target_shape_name=str(sample.target_shape_name),
                    direction=str(sample.direction),
                ),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        serialized_icons = [_serialize_icon(icon) for icon in scene.icons]
        counted_instance_ids = tuple(str(icon.instance_id) for icon in counted_icons)
        shape_counts = dict(Counter(str(icon.shape_id) for icon in scene.icons))
        marker_indices = {"A": int(sample.start_index), "B": int(sample.end_index)}
        trace_payload = {
            "scene_ir": {
                "scene_kind": "icons_named_ring_arc_shape_count",
                "scene_id": SCENE_ID,
                "entities": list(serialized_icons),
                "relations": {
                    "counting_rule": "named_shape_on_directed_arc_between_markers",
                    "target_shape_id": str(sample.target_shape_id),
                    "target_shape_name": str(sample.target_shape_name),
                    "direction": str(sample.direction),
                    "start_marker": "A",
                    "end_marker": "B",
                    "marker_indices": dict(marker_indices),
                    "answer_count": int(sample.answer_count),
                    "ring_icon_count": int(sample.ring_icon_count),
                    "arc_span_count": int(sample.arc_span_count),
                    "shape_counts": {str(key): int(value) for key, value in shape_counts.items()},
                    "clockwise_order_shape_ids": [str(value) for value in sample.shape_ids_by_index],
                    "arc_indices": [int(value) for value in sample.arc_indices],
                    "counted_indices": [int(value) for value in sample.counted_indices],
                    "off_arc_target_indices": [int(value) for value in sample.off_arc_target_indices],
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
                    "answer_count": int(sample.answer_count),
                    "ring_icon_count": int(sample.ring_icon_count),
                    "arc_span_count": int(sample.arc_span_count),
                    "direction": str(sample.direction),
                    "query_id_probabilities": dict(sample.query_probabilities),
                    "answer_probabilities": dict(sample.answer_probabilities),
                    "ring_icon_count_probabilities": dict(sample.ring_icon_count_probabilities),
                    "arc_span_probabilities": dict(sample.arc_span_probabilities),
                    "off_arc_target_count_probabilities": dict(sample.off_arc_target_count_probabilities),
                    "shape_id_support": list(_shape_support(params)),
                    "shape_probabilities": dict(sample.shape_probabilities),
                    "named_icon_fill_style_support": list(sample.fill_style_support),
                    "fill_style_probabilities": dict(sample.fill_style_probabilities),
                },
            },
            "render_spec": {
                "canvas_size": list(scene.panel_geometry["canvas_size"]),
                "coord_space": "pixel",
                "scene_id": SCENE_ID,
                "panel_geometry": dict(scene.panel_geometry),
                "ring_bbox_xyxy": [int(value) for value in scene.ring_bbox_xyxy],
                "ring_center_xy": [float(scene.ring_center_xy[0]), float(scene.ring_center_xy[1])],
                "ring_radius_xy": [float(scene.ring_radius_xy[0]), float(scene.ring_radius_xy[1])],
                "style": {
                    **icon_render_style_trace(render_params=render_params, sampled_palette_rgb=scene.sampled_palette_rgb),
                    **_named_ring_style_trace(render_params),
                },
            },
            "render_map": {
                "image_id": "img0",
                "object_bboxes_px": {
                    str(icon.instance_id): [int(value) for value in icon.bbox_xyxy]
                    for icon in scene.icons
                },
                "marker_label_bboxes_px": {
                    str(label): [int(value) for value in bbox]
                    for label, bbox in scene.marker_label_bboxes.items()
                },
                "counted_instance_ids": list(counted_instance_ids),
            },
            "execution_trace": {
                "scene_variant": "single_panel_named_ring",
                "query_id": str(sample.query_id),
                "question_format": "count_named_shape_icons_strictly_between_ring_markers",
                "target_shape_id": str(sample.target_shape_id),
                "target_shape_name": str(sample.target_shape_name),
                "answer": int(sample.answer_count),
                "direction": str(sample.direction),
                "start_marker": "A",
                "end_marker": "B",
                "start_index": int(sample.start_index),
                "end_index": int(sample.end_index),
                "ring_icon_count": int(sample.ring_icon_count),
                "arc_span_count": int(sample.arc_span_count),
                "clockwise_order_shape_ids": [str(value) for value in sample.shape_ids_by_index],
                "arc_indices": [int(value) for value in sample.arc_indices],
                "counted_indices": [int(value) for value in sample.counted_indices],
                "off_arc_target_indices": [int(value) for value in sample.off_arc_target_indices],
                "counted_instance_ids": list(counted_instance_ids),
            },
            "witness_symbolic": {
                "query_id": str(sample.query_id),
                "target_shape_id": str(sample.target_shape_id),
                "target_shape_name": str(sample.target_shape_name),
                "answer": int(sample.answer_count),
                "direction": str(sample.direction),
                "marker_indices": dict(marker_indices),
                "counted_indices": [int(value) for value in sample.counted_indices],
                "counted_instance_ids": list(counted_instance_ids),
            },
            "projected_annotation": dict(annotation_payload["projected_annotation"]),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(sample.answer_count)),
            annotation_gt=TypedValue(type=str(annotation_payload["annotation_type"]), value=list(annotation_payload["annotation_value"])),
            image=scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_complexity(sample, scene=scene, render_params=render_params),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(sample.query_id),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
        )


__all__ = ["IconsCountingNamedRingArcShapeCountTask"]
