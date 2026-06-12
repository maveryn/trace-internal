"""Select the labeled icon adjacent to a named icon along a marked path."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import uniform_probability_map
from ...shared.labeling import LABEL_POOL_A_L
from ...shared.named_colors import available_named_colors, named_color
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_legibility import resolve_readable_text_style, text_legibility_summary_from_records
from ...shared.text_rendering import draw_text_centered, load_font
from ...shared.variant_sampling import resolve_variant
from ..shared.defaults import ICON_SHARED_DEFAULTS
from ..shared.icon_noise import serialize_icon_noise_edits
from ..shared.annotation import keyed_bbox_map_annotation
from ..shared.icon_scene import BBox, draw_single_panel, resolve_single_panel_layout, single_panel_geometry_to_trace
from ..shared.icon_task_rendering import icon_render_style_trace, resolve_icon_render_params, resolve_icon_rgb_param, sample_icon_instance_noise
from ..shared.procedural_named_icon_field_scene import (
    bbox_center_float,
    bbox_from_center_dimensions,
    bbox_inside,
    boxes_overlap,
    label_bbox_for_icon,
    render_planned_named_icon_sprite,
    resolve_named_icon_fill_style_probabilities,
    rotation_for_named_shape,
    union_bbox,
)
from ..shared.procedural_named_icons import (
    DEFAULT_PROCEDURAL_NAMED_ICON_FILL_STYLE_WEIGHTS,
    PROCEDURAL_NAMED_ICON_FILL_STYLES,
    PROCEDURAL_NAMED_ICON_SHAPES,
    procedural_named_icon_display_name,
    sample_procedural_named_icon_fill_style,
    validate_procedural_named_icon_fill_style_support,
)
from ..shared.public_query_task import rewrite_icons_query_output


TASK_ID = "task_icons__named_path__path_neighbor_label"
SCENE_ID = "named_path"
PUBLIC_QUERY_ID = "path_neighbor_label"

QUERY_IDS: Tuple[str, ...] = (
    "after_first_shape_label",
    "before_first_shape_label",
    "after_last_shape_label",
    "before_last_shape_label",
    "after_second_shape_label",
    "before_second_shape_label",
)
OPTION_LABELS: Tuple[str, ...] = tuple(str(label) for label in LABEL_POOL_A_L[:6])


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable defaults for the named path-neighbor task."""

    candidate_count: int = 6
    distractor_count_min: int = 4
    distractor_count_max: int = 8
    target_occurrence_count_min: int = 2
    target_occurrence_count_max: int = 4
    canvas_width: int = 1280
    canvas_height: int = 720
    outer_margin_px: int = ICON_SHARED_DEFAULTS.outer_margin_px
    panel_padding_px: int = ICON_SHARED_DEFAULTS.panel_padding_px
    panel_corner_radius_px: int = ICON_SHARED_DEFAULTS.panel_corner_radius_px
    panel_title_font_size_px: int = ICON_SHARED_DEFAULTS.panel_title_font_size_px
    scene_icon_size_min_px: int = 44
    scene_icon_size_max_px: int = 60
    reference_panel_width_px: int = ICON_SHARED_DEFAULTS.reference_panel_width_px
    reference_icon_size_px: int = ICON_SHARED_DEFAULTS.reference_icon_size_px
    reference_icon_size_min_px: int = ICON_SHARED_DEFAULTS.reference_icon_size_px
    reference_icon_size_max_px: int = ICON_SHARED_DEFAULTS.reference_icon_size_px
    panel_gap_px: int = ICON_SHARED_DEFAULTS.panel_gap_px
    scene_max_overlap_fraction: float = 0.0
    scene_placement_max_attempts: int = 200
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
        default_factory=lambda: {
            "blur": {"radius": (0.2, 0.6)},
            "downsample": {"scale": (0.85, 0.95)},
            "jpeg": {"quality": (70.0, 90.0)},
            "noise": {"alpha": (0.03, 0.08)},
        }
    )
    named_icon_fill_style_support: Tuple[str, ...] = PROCEDURAL_NAMED_ICON_FILL_STYLES
    path_stroke_width_px: int = 7
    path_stop_radius_px: int = 6
    path_horizontal_margin_px: int = 72
    path_vertical_margin_px: int = 92
    path_amplitude_min_px: int = 72
    path_amplitude_max_px: int = 136
    icon_collision_gap_px: int = 6
    candidate_label_font_size_px: int = 24
    candidate_label_padding_px: int = 5
    candidate_label_gap_px: int = 5
    candidate_label_color_rgb: Tuple[int, int, int] = (52, 60, 77)
    candidate_label_background_rgb: Tuple[int, int, int] = (255, 255, 255)
    candidate_label_border_rgb: Tuple[int, int, int] = (172, 183, 204)
    path_color_rgb: Tuple[int, int, int] = (92, 108, 134)
    stop_fill_rgb: Tuple[int, int, int] = (255, 255, 255)
    stop_outline_rgb: Tuple[int, int, int] = (92, 108, 134)
    endpoint_label_font_size_px: int = 18
    endpoint_label_color_rgb: Tuple[int, int, int] = (58, 68, 86)
    endpoint_label_background_rgb: Tuple[int, int, int] = (255, 255, 255)


@dataclass(frozen=True)
class _IconPlan:
    """Semantic plan for one path stop icon."""

    position_index: int
    role: str
    label: str
    shape_id: str
    color_name: str
    tint_rgb: Tuple[int, int, int]
    fill_style: str
    nominal_size_px: int
    rotation_degrees: int
    noise_edits: Tuple[Any, ...]
    noise_seed: int | None


@dataclass(frozen=True)
class _RenderedPathIcon:
    """Rendered path-stop icon metadata."""

    instance_id: str
    position_index: int
    role: str
    label: str
    shape_id: str
    shape_name: str
    color_name: str
    tint_rgb: Tuple[int, int, int]
    fill_style: str
    bbox_xyxy: Tuple[int, int, int, int]
    center_xy: Tuple[float, float]
    nominal_size_px: int
    rotation_degrees: int
    target_occurrence_rank: int | None
    is_query_occurrence: bool
    is_answer_neighbor: bool
    noise_edits: Tuple[Dict[str, Any], ...]
    noise_seed: int | None


@dataclass(frozen=True)
class _SampleSpec:
    """Symbolic path-neighbor sample before rendering."""

    query_id: str
    answer_label: str
    target_shape_id: str
    target_shape_name: str
    target_occurrence_count: int
    stop_count: int
    distractor_count: int
    target_positions: Tuple[int, ...]
    query_position_index: int
    answer_position_index: int
    neighbor_direction: str
    option_positions: Tuple[int, ...]
    labels_by_position: Dict[int, str]
    query_probabilities: Dict[str, float]
    answer_label_probabilities: Dict[str, float]
    target_occurrence_count_probabilities: Dict[str, float]
    distractor_count_probabilities: Dict[str, float]
    shape_probabilities: Dict[str, float]
    fill_style_support: Tuple[str, ...]
    fill_style_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _ScenePayload:
    """Trace-ready payload for one named path-neighbor scene."""

    query_id: str
    answer_label: str
    target_shape_id: str
    target_shape_name: str
    target_occurrence_count: int
    stop_count: int
    distractor_count: int
    query_position_index: int
    answer_position_index: int
    neighbor_direction: str
    target_positions: Tuple[int, ...]
    option_positions: Tuple[int, ...]
    labels_by_position: Dict[int, str]
    path_points_xy: Tuple[Tuple[float, float], ...]
    icons: Tuple[_RenderedPathIcon, ...]
    panel_geometry: Dict[str, Any]
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_scene_defaults("icons", "relation")
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
    if len(values) < 12:
        raise ValueError("named-path neighbor task needs at least twelve supported icon shapes")
    return values


def _color_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    available = {str(name): tuple(int(channel) for channel in rgb) for name, rgb in available_named_colors()}
    raw = params.get("named_color_support", group_default(_GEN_DEFAULTS, "named_color_support", tuple(available)))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("named_color_support must be a sequence")
    values = tuple(dict.fromkeys(str(value).strip().lower() for value in raw if str(value).strip()))
    unsupported = sorted(set(values) - set(available))
    if unsupported:
        raise ValueError(f"unsupported named colors: {unsupported}")
    if len(values) < 4:
        raise ValueError("named-path neighbor task needs at least four named colors")
    return values


def _fill_style_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get(
        "named_icon_fill_style_support",
        group_default(_GEN_DEFAULTS, "named_icon_fill_style_support", _DEFAULTS.named_icon_fill_style_support),
    )
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raw = _DEFAULTS.named_icon_fill_style_support
    return validate_procedural_named_icon_fill_style_support(tuple(str(value) for value in raw))


def _uniform_string_probability_map(values: Sequence[str], *, selected: str | None = None) -> Dict[str, float]:
    support = tuple(str(value) for value in values)
    if not support:
        return {}
    if selected is not None:
        return {str(value): (1.0 if str(value) == str(selected) else 0.0) for value in support}
    probability = 1.0 / float(len(support))
    return {str(value): probability for value in support}


def _resolve_query(rng, *, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    query_params = dict(params)
    explicit_variant = str(query_params.get("query_id", "") or "").strip()
    if query_params.get("path_neighbor_query") is None and explicit_variant in set(QUERY_IDS):
        query_params["path_neighbor_query"] = explicit_variant
    if explicit_variant == PUBLIC_QUERY_ID:
        query_params.pop("query_id", None)
    query_id, probabilities = resolve_variant(
        rng,
        params=query_params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=QUERY_IDS,
        explicit_key="path_neighbor_query",
        weights_key="path_neighbor_query_weights",
    )
    return str(query_id), dict(probabilities)


def _resolve_answer_label(rng, *, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    explicit_label = params.get("answer_label")
    if explicit_label is not None:
        value = str(explicit_label).strip().upper()
        if value not in set(OPTION_LABELS):
            raise ValueError(f"answer_label must be one of {OPTION_LABELS}")
        return value, _uniform_string_probability_map(OPTION_LABELS, selected=value)
    explicit_index = params.get("answer_index")
    if explicit_index is not None:
        index = int(explicit_index)
        if index < 0 or index >= len(OPTION_LABELS):
            raise ValueError("answer_index must be in 0..5")
        value = str(OPTION_LABELS[index])
        return value, _uniform_string_probability_map(OPTION_LABELS, selected=value)
    value = str(rng.choice(OPTION_LABELS))
    return value, _uniform_string_probability_map(OPTION_LABELS)


def _resolve_int_support(
    rng,
    *,
    params: Mapping[str, Any],
    low_key: str,
    high_key: str,
    explicit_key: str,
    fallback_low: int,
    fallback_high: int,
) -> Tuple[int, Dict[str, float]]:
    low = int(params.get(low_key, group_default(_GEN_DEFAULTS, low_key, fallback_low)))
    high = int(params.get(high_key, group_default(_GEN_DEFAULTS, high_key, fallback_high)))
    if low < 0 or high < low:
        raise ValueError(f"invalid {low_key}/{high_key}")
    support = tuple(range(int(low), int(high) + 1))
    explicit = params.get(explicit_key)
    if explicit is not None:
        value = int(explicit)
        if value not in set(support):
            raise ValueError(f"{explicit_key} is outside configured support")
        return value, dict(uniform_probability_map(support, selected=value))
    value = int(rng.choice(support))
    return value, dict(uniform_probability_map(support))


def _occurrence_rank_for_query(query_id: str, occurrence_count: int) -> int:
    if "second" in str(query_id):
        return 1
    if "last" in str(query_id):
        return int(occurrence_count) - 1
    return 0


def _direction_for_query(query_id: str) -> str:
    return "after" if str(query_id).startswith("after_") else "before"


def _sample_target_positions(
    rng,
    *,
    stop_count: int,
    target_occurrence_count: int,
    query_id: str,
) -> Tuple[Tuple[int, ...], int, int, str]:
    occurrence_rank = _occurrence_rank_for_query(str(query_id), int(target_occurrence_count))
    direction = _direction_for_query(str(query_id))
    if occurrence_rank < 0 or occurrence_rank >= int(target_occurrence_count):
        raise ValueError("query occurrence rank is outside target occurrence support")
    all_positions = tuple(range(1, int(stop_count) - 1))
    for _ in range(1000):
        target_positions = tuple(sorted(int(value) for value in rng.sample(all_positions, int(target_occurrence_count))))
        if any(int(b) - int(a) <= 1 for a, b in zip(target_positions, target_positions[1:])):
            continue
        query_position = int(target_positions[int(occurrence_rank)])
        if str(direction) == "before" and query_position <= 1:
            continue
        if str(direction) == "after" and query_position >= int(stop_count) - 2:
            continue
        answer_position = int(query_position + (1 if str(direction) == "after" else -1))
        if answer_position < 0 or answer_position >= int(stop_count):
            continue
        if answer_position in (0, int(stop_count) - 1):
            continue
        if answer_position in set(target_positions):
            continue
        return target_positions, query_position, answer_position, str(direction)
    raise RuntimeError("failed to sample non-adjacent target positions for named path")


def _sample_spec(*, instance_seed: int, params: Mapping[str, Any]) -> _SampleSpec:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}:sample")
    query_id, query_probabilities = _resolve_query(rng, params=params)
    answer_label, answer_label_probabilities = _resolve_answer_label(rng, params=params)
    candidate_count = int(params.get("candidate_count", group_default(_GEN_DEFAULTS, "candidate_count", _DEFAULTS.candidate_count)))
    if int(candidate_count) != len(OPTION_LABELS):
        raise ValueError("named-path neighbor task requires candidate_count=6")
    distractor_count, distractor_count_probabilities = _resolve_int_support(
        rng,
        params=params,
        low_key="distractor_count_min",
        high_key="distractor_count_max",
        explicit_key="distractor_count",
        fallback_low=_DEFAULTS.distractor_count_min,
        fallback_high=_DEFAULTS.distractor_count_max,
    )
    target_occurrence_count, target_occurrence_count_probabilities = _resolve_int_support(
        rng,
        params=params,
        low_key="target_occurrence_count_min",
        high_key="target_occurrence_count_max",
        explicit_key="target_occurrence_count",
        fallback_low=_DEFAULTS.target_occurrence_count_min,
        fallback_high=_DEFAULTS.target_occurrence_count_max,
    )
    if int(target_occurrence_count) < 2:
        raise ValueError("named-path neighbor task requires at least two target occurrences")
    support = _shape_support(params)
    explicit_shape = params.get("shape_id", params.get("target_shape_id"))
    if explicit_shape is not None:
        target_shape_id = str(explicit_shape)
        if target_shape_id not in set(support):
            raise ValueError(f"unsupported target shape: {target_shape_id}")
    else:
        target_shape_id = str(rng.choice(support))
    fill_style_support = _fill_style_support(params)
    fill_style_probabilities = resolve_named_icon_fill_style_probabilities(
        params,
        _GEN_DEFAULTS,
        fill_style_support,
        default_weights=DEFAULT_PROCEDURAL_NAMED_ICON_FILL_STYLE_WEIGHTS,
    )
    stop_count = int(candidate_count) + int(distractor_count) + int(target_occurrence_count)
    target_positions, query_position, answer_position, direction = _sample_target_positions(
        rng,
        stop_count=int(stop_count),
        target_occurrence_count=int(target_occurrence_count),
        query_id=str(query_id),
    )
    non_target_positions = [index for index in range(int(stop_count)) if index not in set(target_positions)]
    endpoint_positions = {0, int(stop_count) - 1}
    other_option_positions = [
        index
        for index in non_target_positions
        if int(index) != int(answer_position) and int(index) not in endpoint_positions
    ]
    rng.shuffle(other_option_positions)
    option_positions = tuple(sorted([int(answer_position), *[int(value) for value in other_option_positions[:5]]]))
    if len(option_positions) != len(OPTION_LABELS):
        raise RuntimeError("failed to assign six path option positions")
    remaining_labels = [str(label) for label in OPTION_LABELS if str(label) != str(answer_label)]
    rng.shuffle(remaining_labels)
    labels_by_position: Dict[int, str] = {}
    for position in option_positions:
        labels_by_position[int(position)] = str(answer_label) if int(position) == int(answer_position) else str(remaining_labels.pop())
    return _SampleSpec(
        query_id=str(query_id),
        answer_label=str(answer_label),
        target_shape_id=str(target_shape_id),
        target_shape_name=procedural_named_icon_display_name(str(target_shape_id)),
        target_occurrence_count=int(target_occurrence_count),
        stop_count=int(stop_count),
        distractor_count=int(distractor_count),
        target_positions=tuple(int(value) for value in target_positions),
        query_position_index=int(query_position),
        answer_position_index=int(answer_position),
        neighbor_direction=str(direction),
        option_positions=tuple(int(value) for value in option_positions),
        labels_by_position=dict(labels_by_position),
        query_probabilities=dict(query_probabilities),
        answer_label_probabilities=dict(answer_label_probabilities),
        target_occurrence_count_probabilities=dict(target_occurrence_count_probabilities),
        distractor_count_probabilities=dict(distractor_count_probabilities),
        shape_probabilities=_uniform_string_probability_map(support, selected=str(target_shape_id) if explicit_shape is not None else None),
        fill_style_support=tuple(fill_style_support),
        fill_style_probabilities=dict(fill_style_probabilities),
    )


def _resolve_render_params(params: Mapping[str, Any], *, instance_seed: int) -> Dict[str, Any]:
    render_params = resolve_icon_render_params(
        params=params,
        render_defaults=_RENDER_DEFAULTS,
        fallback_defaults=_DEFAULTS,
        instance_seed=int(instance_seed),
    )
    for key in (
        "path_stroke_width_px",
        "path_stop_radius_px",
        "path_horizontal_margin_px",
        "path_vertical_margin_px",
        "path_amplitude_min_px",
        "path_amplitude_max_px",
        "icon_collision_gap_px",
        "candidate_label_font_size_px",
        "candidate_label_padding_px",
        "candidate_label_gap_px",
        "endpoint_label_font_size_px",
    ):
        render_params[key] = int(params.get(key, group_default(_RENDER_DEFAULTS, key, getattr(_DEFAULTS, key))))
    for key in (
        "candidate_label_color_rgb",
        "candidate_label_background_rgb",
        "candidate_label_border_rgb",
        "path_color_rgb",
        "stop_fill_rgb",
        "stop_outline_rgb",
        "endpoint_label_color_rgb",
        "endpoint_label_background_rgb",
    ):
        render_params[key] = resolve_icon_rgb_param(
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            key=key,
            fallback=getattr(_DEFAULTS, key),
            instance_seed=int(instance_seed),
        )
    previous_legibility = render_params.get("text_legibility")
    previous_records = []
    if isinstance(previous_legibility, Mapping) and isinstance(previous_legibility.get("records"), list):
        previous_records = [dict(record) for record in previous_legibility["records"] if isinstance(record, Mapping)]

    candidate_label_style = resolve_readable_text_style(
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:candidate_label_text",
        role="named_path_candidate_label_text",
        surface_rgbs=(
            tuple(int(value) for value in render_params["candidate_label_background_rgb"]),
            tuple(int(value) for value in render_params["panel_fill_rgb"]),
            tuple(int(value) for value in render_params["background_color_rgb"]),
        ),
        preferred_rgbs=(tuple(int(value) for value in render_params["candidate_label_color_rgb"]),),
    )
    render_params["candidate_label_color_rgb"] = tuple(int(value) for value in candidate_label_style.fill_rgb)
    render_params["candidate_label_stroke_rgb"] = tuple(
        int(value) for value in render_params["candidate_label_background_rgb"]
    )
    candidate_label_record = candidate_label_style.metadata()
    candidate_label_record["stroke_rgb"] = list(render_params["candidate_label_stroke_rgb"])

    endpoint_label_style = resolve_readable_text_style(
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:endpoint_label_text",
        role="named_path_endpoint_label_text",
        surface_rgbs=(
            tuple(int(value) for value in render_params["endpoint_label_background_rgb"]),
            tuple(int(value) for value in render_params["panel_fill_rgb"]),
            tuple(int(value) for value in render_params["background_color_rgb"]),
        ),
        preferred_rgbs=(tuple(int(value) for value in render_params["endpoint_label_color_rgb"]),),
    )
    render_params["endpoint_label_color_rgb"] = tuple(int(value) for value in endpoint_label_style.fill_rgb)
    render_params["endpoint_label_stroke_rgb"] = tuple(
        int(value) for value in render_params["endpoint_label_background_rgb"]
    )
    endpoint_label_record = endpoint_label_style.metadata()
    endpoint_label_record["stroke_rgb"] = list(render_params["endpoint_label_stroke_rgb"])
    render_params["text_legibility"] = text_legibility_summary_from_records(
        [*previous_records, candidate_label_record, endpoint_label_record]
    )
    return render_params


def _sample_size(rng, *, render_params: Mapping[str, Any]) -> int:
    low = int(render_params["scene_icon_size_min_px"])
    high = int(render_params["scene_icon_size_max_px"])
    return int(rng.randint(min(low, high), max(low, high)))


def _build_icon_plans(
    *,
    sample: _SampleSpec,
    instance_seed: int,
    params: Mapping[str, Any],
    render_params: Mapping[str, Any],
    rng,
) -> Tuple[Tuple[_IconPlan, ...], Tuple[Tuple[int, int, int], ...]]:
    shape_support = _shape_support(params)
    color_support = _color_support(params)
    distractor_shape_support = tuple(str(value) for value in shape_support if str(value) != str(sample.target_shape_id))
    if len(distractor_shape_support) < 8:
        raise ValueError("named-path neighbor task needs at least eight non-target shapes")
    plans: List[_IconPlan] = []
    target_occurrence_ranks = {int(position): int(rank) for rank, position in enumerate(sample.target_positions)}
    for position in range(int(sample.stop_count)):
        role = "distractor"
        if int(position) in target_occurrence_ranks:
            role = "query_occurrence" if int(position) == int(sample.query_position_index) else "target_occurrence"
            shape_id = str(sample.target_shape_id)
        else:
            role = "answer_option" if int(position) == int(sample.answer_position_index) else ("option" if int(position) in sample.labels_by_position else "distractor")
            shape_id = str(rng.choice(distractor_shape_support))
        color_name = str(rng.choice(color_support))
        noise_edits, noise_seed = sample_icon_instance_noise(
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:path_stop:{int(position)}",
            render_params=render_params,
        )
        plans.append(
            _IconPlan(
                position_index=int(position),
                role=str(role),
                label=str(sample.labels_by_position.get(int(position), "")),
                shape_id=str(shape_id),
                color_name=str(color_name),
                tint_rgb=tuple(int(channel) for channel in named_color(str(color_name))),
                fill_style=sample_procedural_named_icon_fill_style(
                    rng,
                    support=sample.fill_style_support,
                    probabilities=sample.fill_style_probabilities,
                ),
                nominal_size_px=_sample_size(rng, render_params=render_params),
                rotation_degrees=rotation_for_named_shape(rng, str(shape_id)),
                noise_edits=tuple(noise_edits),
                noise_seed=int(noise_seed),
            )
        )
    sampled_palette_rgb = tuple(tuple(int(channel) for channel in named_color(color_name)) for color_name in color_support)
    return tuple(plans), sampled_palette_rgb


def _route_points(
    *,
    rng,
    stop_count: int,
    content_bbox: BBox,
    render_params: Mapping[str, Any],
) -> Tuple[Tuple[float, float], ...]:
    x0, y0, x1, y1 = tuple(int(value) for value in content_bbox)
    horizontal_margin = max(30, int(render_params["path_horizontal_margin_px"]))
    vertical_margin = max(40, int(render_params["path_vertical_margin_px"]))
    left = float(x0 + horizontal_margin)
    right = float(x1 - horizontal_margin)
    if right <= left:
        raise ValueError("content panel is too narrow for path route")
    top = float(y0 + vertical_margin)
    bottom = float(y1 - vertical_margin)
    if bottom <= top:
        raise ValueError("content panel is too short for path route")
    mid_y = 0.5 * (top + bottom)
    max_amplitude = min(0.42 * (bottom - top), float(render_params["path_amplitude_max_px"]))
    min_amplitude = min(max_amplitude, float(render_params["path_amplitude_min_px"]))
    amplitude = float(rng.uniform(float(min_amplitude), float(max_amplitude))) if max_amplitude > 0 else 0.0
    phase = float(rng.uniform(0.0, 2.0 * math.pi))
    secondary_phase = float(rng.uniform(0.0, 2.0 * math.pi))
    points: List[Tuple[float, float]] = []
    for index in range(int(stop_count)):
        t = 0.0 if int(stop_count) <= 1 else float(index) / float(int(stop_count) - 1)
        x = left + t * (right - left)
        y = mid_y + amplitude * math.sin((2.0 * math.pi * 1.15 * t) + phase)
        y += 0.28 * amplitude * math.sin((2.0 * math.pi * 2.25 * t) + secondary_phase)
        y = max(top, min(bottom, y))
        points.append((float(x), float(y)))
    return tuple(points)


def _draw_label_badge(
    *,
    image: Image.Image,
    icon_bbox: BBox,
    label: str,
    content_bbox: BBox,
    label_font,
    render_params: Mapping[str, Any],
) -> BBox:
    label_bbox = label_bbox_for_icon(
        icon_bbox=tuple(int(value) for value in icon_bbox),
        label=str(label),
        content_bbox=tuple(int(value) for value in content_bbox),
        font=label_font,
        padding_px=int(render_params["candidate_label_padding_px"]),
        gap_px=int(render_params["candidate_label_gap_px"]),
    )
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        label_bbox,
        radius=max(4, int(round(0.28 * float(label_bbox[3] - label_bbox[1])))),
        fill=tuple(int(value) for value in render_params["candidate_label_background_rgb"]) + (240,),
        outline=tuple(int(value) for value in render_params["candidate_label_border_rgb"]) + (255,),
        width=1,
    )
    draw_text_centered(
        draw,
        text=str(label),
        center=bbox_center_float(label_bbox),
        font=label_font,
        fill=tuple(int(value) for value in render_params["candidate_label_color_rgb"]),
        stroke_fill=tuple(int(value) for value in render_params["candidate_label_stroke_rgb"]),
        stroke_width=1,
    )
    return tuple(int(value) for value in label_bbox)


def _label_occupancy_bbox(
    *,
    icon_bbox: BBox,
    label: str,
    content_bbox: BBox,
    label_font,
    render_params: Mapping[str, Any],
) -> BBox:
    if not str(label):
        return tuple(int(value) for value in icon_bbox)
    label_bbox = label_bbox_for_icon(
        icon_bbox=tuple(int(value) for value in icon_bbox),
        label=str(label),
        content_bbox=tuple(int(value) for value in content_bbox),
        font=label_font,
        padding_px=int(render_params["candidate_label_padding_px"]),
        gap_px=int(render_params["candidate_label_gap_px"]),
    )
    return union_bbox(tuple(int(value) for value in icon_bbox), tuple(int(value) for value in label_bbox))


def _draw_endpoint_label(
    *,
    image: Image.Image,
    text: str,
    center_xy: Tuple[float, float],
    content_bbox: BBox,
    font,
    render_params: Mapping[str, Any],
) -> None:
    draw = ImageDraw.Draw(image)
    text_bbox = draw.textbbox((0, 0), str(text), font=font)
    width = int(text_bbox[2] - text_bbox[0]) + 12
    height = int(text_bbox[3] - text_bbox[1]) + 8
    x0 = int(round(float(center_xy[0]) - 0.5 * float(width)))
    y0 = int(round(float(center_xy[1]) - 42.0))
    x0 = max(int(content_bbox[0]), min(int(content_bbox[2]) - width, x0))
    y0 = max(int(content_bbox[1]), min(int(content_bbox[3]) - height, y0))
    box = (int(x0), int(y0), int(x0 + width), int(y0 + height))
    draw.rounded_rectangle(
        box,
        radius=6,
        fill=tuple(int(value) for value in render_params["endpoint_label_background_rgb"]) + (230,),
        outline=tuple(int(value) for value in render_params["stop_outline_rgb"]) + (255,),
        width=1,
    )
    draw_text_centered(
        draw,
        text=str(text),
        center=bbox_center_float(box),
        font=font,
        fill=tuple(int(value) for value in render_params["endpoint_label_color_rgb"]),
        stroke_fill=tuple(int(value) for value in render_params["endpoint_label_stroke_rgb"]),
        stroke_width=1,
    )


def _draw_path_underlay(
    *,
    image: Image.Image,
    points: Sequence[Tuple[float, float]],
    content_bbox: BBox,
    render_params: Mapping[str, Any],
) -> None:
    draw = ImageDraw.Draw(image)
    path_color = tuple(int(value) for value in render_params["path_color_rgb"]) + (230,)
    draw.line([(float(x), float(y)) for x, y in points], fill=path_color, width=int(render_params["path_stroke_width_px"]), joint="curve")
    radius = max(2, int(render_params["path_stop_radius_px"]))
    for cx, cy in points:
        box = (int(round(cx - radius)), int(round(cy - radius)), int(round(cx + radius)), int(round(cy + radius)))
        draw.ellipse(
            box,
            fill=tuple(int(value) for value in render_params["stop_fill_rgb"]) + (255,),
            outline=tuple(int(value) for value in render_params["stop_outline_rgb"]) + (255,),
            width=2,
        )
    endpoint_font = load_font(int(render_params["endpoint_label_font_size_px"]), bold=True)
    _draw_endpoint_label(image=image, text="START", center_xy=tuple(points[0]), content_bbox=content_bbox, font=endpoint_font, render_params=render_params)
    _draw_endpoint_label(image=image, text="END", center_xy=tuple(points[-1]), content_bbox=content_bbox, font=endpoint_font, render_params=render_params)


def _render_scene(
    *,
    rng,
    instance_seed: int,
    sample: _SampleSpec,
    plans: Sequence[_IconPlan],
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...],
    render_params: Mapping[str, Any],
) -> Tuple[_ScenePayload, Image.Image]:
    layout = resolve_single_panel_layout(
        canvas_width=int(render_params["canvas_width"]),
        canvas_height=int(render_params["canvas_height"]),
        outer_margin_px=int(render_params["outer_margin_px"]),
        panel_padding_px=int(render_params["panel_padding_px"]),
        title_font_size_px=int(render_params["panel_title_font_size_px"]),
    )
    content_bbox = tuple(int(value) for value in layout.scene_content_xyxy)
    label_font = load_font(int(render_params["candidate_label_font_size_px"]), bold=True)
    sprites = [render_planned_named_icon_sprite(plan) for plan in plans]
    path_points = _route_points(rng=rng, stop_count=int(sample.stop_count), content_bbox=content_bbox, render_params=render_params)
    occupancy: List[BBox] = []
    icon_bboxes: List[BBox] = []
    for plan, sprite in zip(plans, sprites):
        center = tuple(float(value) for value in path_points[int(plan.position_index)])
        bbox = bbox_from_center_dimensions(center, width=int(sprite.size[0]), height=int(sprite.size[1]))
        occupancy_bbox = _label_occupancy_bbox(
            icon_bbox=bbox,
            label=str(plan.label),
            content_bbox=content_bbox,
            label_font=label_font,
            render_params=render_params,
        )
        if not bbox_inside(occupancy_bbox, content_bbox):
            raise ValueError("path stop icon or label is outside content panel")
        if any(boxes_overlap(occupancy_bbox, other, gap_px=int(render_params["icon_collision_gap_px"])) for other in occupancy):
            raise ValueError("path stop icon placement overlaps")
        occupancy.append(tuple(int(value) for value in occupancy_bbox))
        icon_bboxes.append(tuple(int(value) for value in bbox))

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
        scene_title="Path",
        icon_canvas_style=render_params.get("_icon_canvas_style_object"),
    )
    _draw_path_underlay(image=image, points=path_points, content_bbox=content_bbox, render_params=render_params)
    for plan, sprite, bbox in zip(plans, sprites, icon_bboxes):
        image.alpha_composite(sprite, (int(bbox[0]), int(bbox[1])))
    for plan, bbox in zip(plans, icon_bboxes):
        if str(plan.label):
            _draw_label_badge(
                image=image,
                icon_bbox=tuple(int(value) for value in bbox),
                label=str(plan.label),
                content_bbox=content_bbox,
                label_font=label_font,
                render_params=render_params,
            )

    target_rank_by_position = {int(position): int(rank) for rank, position in enumerate(sample.target_positions)}
    rendered_icons: List[_RenderedPathIcon] = []
    for plan, bbox in zip(plans, icon_bboxes):
        rendered_icons.append(
            _RenderedPathIcon(
                instance_id=f"path_stop_{int(plan.position_index):02d}",
                position_index=int(plan.position_index),
                role=str(plan.role),
                label=str(plan.label),
                shape_id=str(plan.shape_id),
                shape_name=procedural_named_icon_display_name(str(plan.shape_id)),
                color_name=str(plan.color_name),
                tint_rgb=tuple(int(channel) for channel in plan.tint_rgb),
                fill_style=str(plan.fill_style),
                bbox_xyxy=tuple(int(value) for value in bbox),
                center_xy=bbox_center_float(bbox),
                nominal_size_px=int(plan.nominal_size_px),
                rotation_degrees=int(plan.rotation_degrees),
                target_occurrence_rank=(
                    int(target_rank_by_position[int(plan.position_index)])
                    if int(plan.position_index) in target_rank_by_position
                    else None
                ),
                is_query_occurrence=int(plan.position_index) == int(sample.query_position_index),
                is_answer_neighbor=int(plan.position_index) == int(sample.answer_position_index),
                noise_edits=tuple(serialize_icon_noise_edits(plan.noise_edits)),
                noise_seed=plan.noise_seed,
            )
        )
    payload = _ScenePayload(
        query_id=str(sample.query_id),
        answer_label=str(sample.answer_label),
        target_shape_id=str(sample.target_shape_id),
        target_shape_name=str(sample.target_shape_name),
        target_occurrence_count=int(sample.target_occurrence_count),
        stop_count=int(sample.stop_count),
        distractor_count=int(sample.distractor_count),
        query_position_index=int(sample.query_position_index),
        answer_position_index=int(sample.answer_position_index),
        neighbor_direction=str(sample.neighbor_direction),
        target_positions=tuple(int(value) for value in sample.target_positions),
        option_positions=tuple(int(value) for value in sample.option_positions),
        labels_by_position={int(key): str(value) for key, value in sample.labels_by_position.items()},
        path_points_xy=tuple((float(x), float(y)) for x, y in path_points),
        icons=tuple(sorted(rendered_icons, key=lambda icon: int(icon.position_index))),
        panel_geometry=single_panel_geometry_to_trace(layout),
        sampled_palette_rgb=tuple(sampled_palette_rgb),
    )
    return payload, image.convert("RGB")


def _serialize_path_icon(icon: _RenderedPathIcon) -> Dict[str, Any]:
    return {
        "entity_kind": "procedural_named_icon",
        "instance_id": str(icon.instance_id),
        "position_index": int(icon.position_index),
        "role": str(icon.role),
        "label": str(icon.label),
        "shape_id": str(icon.shape_id),
        "shape_name": str(icon.shape_name),
        "color_name": str(icon.color_name),
        "tint_rgb": [int(value) for value in icon.tint_rgb],
        "fill_style": str(icon.fill_style),
        "bbox_xyxy": [int(value) for value in icon.bbox_xyxy],
        "center_xy": [float(icon.center_xy[0]), float(icon.center_xy[1])],
        "nominal_size_px": int(icon.nominal_size_px),
        "rotation_degrees": int(icon.rotation_degrees),
        "target_occurrence_rank": None if icon.target_occurrence_rank is None else int(icon.target_occurrence_rank),
        "is_query_occurrence": bool(icon.is_query_occurrence),
        "is_answer_neighbor": bool(icon.is_answer_neighbor),
        "noise_edits": [dict(edit) for edit in icon.noise_edits],
        "noise_seed": None if icon.noise_seed is None else int(icon.noise_seed),
    }




@register_task
class IconsRelationNamedPathNeighborLabelTask:
    """Select the labeled icon immediately before/after a named shape along a path."""

    task_id = TASK_ID
    domain = "icons"
    scene_id = "relation"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic named-path neighbor instance."""

        render_params = _resolve_render_params(params, instance_seed=int(instance_seed))
        sample: _SampleSpec | None = None
        scene_payload: _ScenePayload | None = None
        image: Image.Image | None = None
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                sample = _sample_spec(instance_seed=int(instance_seed), params=params)
                scene_rng = spawn_rng(int(instance_seed), f"{TASK_ID}:scene", int(attempt))
                plans, sampled_palette_rgb = _build_icon_plans(
                    sample=sample,
                    instance_seed=int(instance_seed),
                    params=params,
                    render_params=render_params,
                    rng=scene_rng,
                )
                scene_payload, image = _render_scene(
                    rng=scene_rng,
                    instance_seed=int(instance_seed),
                    sample=sample,
                    plans=plans,
                    sampled_palette_rgb=tuple(sampled_palette_rgb),
                    render_params=render_params,
                )
                break
            except Exception as exc:
                last_error = exc
                sample = None
                scene_payload = None
                image = None
                continue
        if sample is None or scene_payload is None or image is None:
            raise RuntimeError(f"failed to generate {TASK_ID} instance") from last_error

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                f"question_text_{scene_payload.query_id}",
                "annotation_hint",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        question_text = str(prompt_defaults[f"question_text_{scene_payload.query_id}"]).format(
            target_shape_name=str(scene_payload.target_shape_name)
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            scene_id=self.scene_id,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "question_text": str(question_text),
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

        icons_by_position = {int(icon.position_index): icon for icon in scene_payload.icons}
        query_icon = icons_by_position[int(scene_payload.query_position_index)]
        answer_icon = icons_by_position[int(scene_payload.answer_position_index)]
        if str(answer_icon.label) != str(scene_payload.answer_label):
            raise RuntimeError("rendered answer icon label does not match answer label")
        annotation_artifacts = keyed_bbox_map_annotation(
            {
                "queried_icon": query_icon.bbox_xyxy,
                "selected_neighbor": answer_icon.bbox_xyxy,
            }
        )
        serialized_icons = [_serialize_path_icon(icon) for icon in scene_payload.icons]
        answer_gt = TypedValue(type="option_letter", value=str(scene_payload.answer_label))
        annotation_gt = TypedValue(
            type=str(annotation_artifacts["annotation_type"]),
            value=dict(annotation_artifacts["annotation_value"]),
        )
        trace_payload = {
            "scene_ir": {
                "scene_kind": "icons_named_path_neighbor",
                "scene_id": SCENE_ID,
                "entities": list(serialized_icons),
                "relations": {
                    "target": "labeled_neighbor_of_named_shape_occurrence_along_path",
                    "query_id": str(scene_payload.query_id),
                    "target_shape_id": str(scene_payload.target_shape_id),
                    "target_shape_name": str(scene_payload.target_shape_name),
                    "target_positions": [int(value) for value in scene_payload.target_positions],
                    "query_position_index": int(scene_payload.query_position_index),
                    "answer_position_index": int(scene_payload.answer_position_index),
                    "neighbor_direction": str(scene_payload.neighbor_direction),
                    "answer_label": str(scene_payload.answer_label),
                    "candidate_labels": [str(label) for label in OPTION_LABELS],
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(scene_payload.panel_geometry),
                    "path": {"order": "start_to_end", "points_xy": [[float(x), float(y)] for x, y in scene_payload.path_points_xy]},
                },
            },
            "query_spec": {
                "query_id": str(PUBLIC_QUERY_ID),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "path_neighbor_query": str(scene_payload.query_id),
                    "path_neighbor_query_probabilities": dict(sample.query_probabilities),
                    "target_shape_id": str(scene_payload.target_shape_id),
                    "target_shape_name": str(scene_payload.target_shape_name),
                    "shape_probabilities": dict(sample.shape_probabilities),
                    "answer_label": str(scene_payload.answer_label),
                    "answer_label_probabilities": dict(sample.answer_label_probabilities),
                    "candidate_count": int(len(OPTION_LABELS)),
                    "distractor_count": int(scene_payload.distractor_count),
                    "distractor_count_probabilities": dict(sample.distractor_count_probabilities),
                    "target_occurrence_count": int(scene_payload.target_occurrence_count),
                    "target_occurrence_count_probabilities": dict(sample.target_occurrence_count_probabilities),
                    "stop_count": int(scene_payload.stop_count),
                    "named_icon_fill_style_support": list(sample.fill_style_support),
                    "fill_style_probabilities": dict(sample.fill_style_probabilities),
                },
            },
            "render_spec": {
                "canvas_size": [int(render_params["canvas_width"]), int(render_params["canvas_height"])],
                "coord_space": "pixel",
                "scene_id": SCENE_ID,
                "panel_geometry": dict(scene_payload.panel_geometry),
                "style": {
                    **icon_render_style_trace(
                        render_params=render_params,
                        sampled_palette_rgb=tuple(scene_payload.sampled_palette_rgb),
                    ),
                    "path_stroke_width_px": int(render_params["path_stroke_width_px"]),
                    "path_color_rgb": [int(value) for value in render_params["path_color_rgb"]],
                    "path_stop_radius_px": int(render_params["path_stop_radius_px"]),
                    "candidate_label_font_size_px": int(render_params["candidate_label_font_size_px"]),
                    "candidate_label_color_rgb": [int(value) for value in render_params["candidate_label_color_rgb"]],
                    "candidate_label_stroke_rgb": [
                        int(value) for value in render_params["candidate_label_stroke_rgb"]
                    ],
                    "candidate_label_background_rgb": [
                        int(value) for value in render_params["candidate_label_background_rgb"]
                    ],
                    "candidate_label_border_rgb": [int(value) for value in render_params["candidate_label_border_rgb"]],
                    "candidate_label_padding_px": int(render_params["candidate_label_padding_px"]),
                    "candidate_label_gap_px": int(render_params["candidate_label_gap_px"]),
                    "endpoint_label_font_size_px": int(render_params["endpoint_label_font_size_px"]),
                    "endpoint_label_color_rgb": [int(value) for value in render_params["endpoint_label_color_rgb"]],
                    "endpoint_label_stroke_rgb": [int(value) for value in render_params["endpoint_label_stroke_rgb"]],
                    "endpoint_label_background_rgb": [
                        int(value) for value in render_params["endpoint_label_background_rgb"]
                    ],
                    "stop_fill_rgb": [int(value) for value in render_params["stop_fill_rgb"]],
                    "stop_outline_rgb": [int(value) for value in render_params["stop_outline_rgb"]],
                },
            },
            "render_map": {
                "image_id": "img0",
                "object_bboxes_px": {
                    str(icon.instance_id): [int(value) for value in icon.bbox_xyxy]
                    for icon in scene_payload.icons
                },
                "path_points_xy": [[float(x), float(y)] for x, y in scene_payload.path_points_xy],
                "query_occurrence": _serialize_path_icon(query_icon),
                "answer_option": _serialize_path_icon(answer_icon),
                "labels_by_position": {str(key): str(value) for key, value in scene_payload.labels_by_position.items()},
            },
            "execution_trace": {
                "scene_variant": "single_panel_named_path",
                "query_id": str(scene_payload.query_id),
                "question_format": "select_labeled_neighbor_of_named_icon_along_start_to_end_path",
                "target_shape_id": str(scene_payload.target_shape_id),
                "target_shape_name": str(scene_payload.target_shape_name),
                "target_occurrence_count": int(scene_payload.target_occurrence_count),
                "target_positions": [int(value) for value in scene_payload.target_positions],
                "query_position_index": int(scene_payload.query_position_index),
                "answer_position_index": int(scene_payload.answer_position_index),
                "neighbor_direction": str(scene_payload.neighbor_direction),
                "answer_label": str(scene_payload.answer_label),
                "candidate_labels": [str(label) for label in OPTION_LABELS],
                "option_positions": [int(value) for value in scene_payload.option_positions],
                "labels_by_position": {str(key): str(value) for key, value in scene_payload.labels_by_position.items()},
                "stop_count": int(scene_payload.stop_count),
                "distractor_count": int(scene_payload.distractor_count),
            },
            "witness_symbolic": {
                "query_id": str(scene_payload.query_id),
                "target_shape_id": str(scene_payload.target_shape_id),
                "target_shape_name": str(scene_payload.target_shape_name),
                "query_instance_id": str(query_icon.instance_id),
                "query_position_index": int(scene_payload.query_position_index),
                "answer_instance_id": str(answer_icon.instance_id),
                "answer_position_index": int(scene_payload.answer_position_index),
                "answer_label": str(scene_payload.answer_label),
                "annotation_roles": {
                    "queried_icon": str(query_icon.instance_id),
                    "selected_neighbor": str(answer_icon.instance_id),
                },
            },
            "projected_annotation": {
                **dict(annotation_artifacts["projected_annotation"]),
                "items": [
                    {"role": "query_occurrence", "instance_id": str(query_icon.instance_id), "bbox_xyxy": list(query_icon.bbox_xyxy)},
                    {"role": "answer_option", "instance_id": str(answer_icon.instance_id), "bbox_xyxy": list(answer_icon.bbox_xyxy)},
                ],
            },
        }
        output = TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            query_id=str(PUBLIC_QUERY_ID),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
        )
        return rewrite_icons_query_output(
            output,
            query_id=str(scene_payload.query_id),
            scene_id=SCENE_ID,
            query_probabilities=sample.query_probabilities,
        )


__all__ = ["IconsRelationNamedPathNeighborLabelTask"]
