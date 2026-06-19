"""Select which right-panel named icon had a queried original attribute."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.scene_config import get_scene_defaults
from ....core.seed import spawn_rng
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.color_format import format_named_color_with_hex
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.fixed_query import select_task_query_id
from ...shared.labeling import LABEL_POOL_A_L
from ...shared.named_colors import available_named_colors, named_color
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_legibility import resolve_readable_text_style, text_legibility_summary_from_records
from ...shared.text_rendering import draw_text_centered, load_font
from ..shared.defaults import ICON_SHARED_DEFAULTS
from ..shared.annotation import icon_bbox_map_annotation
from ..shared.icon_noise import serialize_icon_noise_edits
from ..shared.icon_scene import (
    BBox,
    draw_two_panel_panels,
    max_overlap_with_existing,
    panel_geometry_to_trace,
    resolve_two_panel_layout,
)
from ..shared.icon_task_rendering import icon_render_style_trace, resolve_icon_render_params, sample_icon_instance_noise
from ..shared.procedural_named_icon_field_scene import (
    resolve_named_icon_fill_style_probabilities,
)
from ..shared.procedural_named_icons import (
    DEFAULT_PROCEDURAL_NAMED_ICON_FILL_STYLE_WEIGHTS,
    PROCEDURAL_NAMED_ICON_FILL_STYLES,
    PROCEDURAL_NAMED_ICON_SHAPES,
    procedural_named_icon_display_name,
    procedural_named_icon_fill_style_probability_map,
    render_procedural_named_icon_rgba,
    sample_procedural_named_icon_fill_style,
    validate_procedural_named_icon_fill_style_support,
)


TASK_ID = "task_icons__paired_canvas__original_attribute_label"
SCENE_ID = "paired_canvas"

QUERY_IDS: Tuple[str, ...] = (
    "original_shape_label",
    "original_color_shape_label",
)
OPTION_LABELS: Tuple[str, ...] = tuple(str(label) for label in LABEL_POOL_A_L[:6])


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable defaults for paired named-icon original-state queries."""

    tracked_count: int = 6
    distractor_count_min: int = 4
    distractor_count_max: int = 8
    canvas_width: int = 1120
    canvas_height: int = 640
    outer_margin_px: int = ICON_SHARED_DEFAULTS.outer_margin_px
    panel_padding_px: int = ICON_SHARED_DEFAULTS.panel_padding_px
    panel_corner_radius_px: int = ICON_SHARED_DEFAULTS.panel_corner_radius_px
    panel_title_font_size_px: int = ICON_SHARED_DEFAULTS.panel_title_font_size_px
    reference_panel_width_px: int = 516
    panel_gap_px: int = 24
    scene_icon_size_min_px: int = 44
    scene_icon_size_max_px: int = 66
    reference_icon_size_px: int = 66
    reference_icon_size_min_px: int = 44
    reference_icon_size_max_px: int = 66
    scene_max_overlap_fraction: float = 0.0
    scene_placement_max_attempts: int = 420
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
    icon_noise_value_ranges: Dict[str, Dict[str, Tuple[float, float]]] | None = None
    named_icon_fill_style_support: Tuple[str, ...] = PROCEDURAL_NAMED_ICON_FILL_STYLES
    named_icon_fill_style_weights: Dict[str, float] | None = None
    candidate_label_font_size_px: int = 24
    candidate_label_padding_px: int = 5
    candidate_label_color_rgb: Tuple[int, int, int] = (52, 60, 77)
    candidate_label_background_rgb: Tuple[int, int, int] = (255, 255, 255)
    candidate_label_border_rgb: Tuple[int, int, int] = (172, 183, 204)
    candidate_label_gap_px: int = 6
    icon_collision_gap_px: int = 8
    paired_position_jitter_px: int = 14


@dataclass(frozen=True)
class _NamedColorEntry:
    name: str
    rgb: Tuple[int, int, int]
    label: str


@dataclass(frozen=True)
class _IconState:
    shape_id: str
    color_name: str
    tint_rgb: Tuple[int, int, int]
    fill_style: str
    nominal_size_px: int
    rotation_degrees: int
    noise_edits: Tuple[Any, ...] = ()
    noise_seed: int | None = None


@dataclass(frozen=True)
class _PairPlan:
    pair_id: str
    label: str
    tracked: bool
    original: _IconState
    current: _IconState
    center_fraction_xy: Tuple[float, float]


@dataclass(frozen=True)
class _RenderedPanelIcon:
    instance_id: str
    pair_id: str
    panel: str
    label: str
    tracked: bool
    shape_id: str
    shape_name: str
    color_name: str
    tint_rgb: Tuple[int, int, int]
    fill_style: str
    bbox_xyxy: Tuple[int, int, int, int]
    center_xy: Tuple[float, float]
    nominal_size_px: int
    rotation_degrees: int
    noise_edits: Tuple[Dict[str, Any], ...]
    noise_seed: int | None


@dataclass(frozen=True)
class _ScenePayload:
    query_id: str
    answer_label: str
    answer_pair_id: str
    target_shape_id: str
    target_shape_name: str
    target_color: _NamedColorEntry | None
    target_description: str
    pairs: Tuple[_PairPlan, ...]
    original_icons: Tuple[_RenderedPanelIcon, ...]
    right_icons: Tuple[_RenderedPanelIcon, ...]
    panel_geometry: Dict[str, Any]
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...]
    distractor_count: int
    false_positive_label: str


_DEFAULTS = _TaskDefaults()
_SCENE_DEFAULTS = get_scene_defaults("icons", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _select_query(instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float], Dict[str, Any]]:
    """Select and validate one semantic original-attribute query branch."""

    return select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=QUERY_IDS,
        default_query_id=QUERY_IDS[0],
        task_id=TASK_ID,
        namespace=f"{TASK_ID}.query",
    )


def _resolve_answer_label(rng, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    explicit = str(params.get("answer_label", "")).strip().upper()
    if explicit:
        if explicit not in OPTION_LABELS:
            raise ValueError(f"unsupported answer_label: {explicit}")
        return explicit, {label: (1.0 if label == explicit else 0.0) for label in OPTION_LABELS}
    label = str(OPTION_LABELS[int(rng.randrange(len(OPTION_LABELS)))])
    return label, {option: 1.0 / float(len(OPTION_LABELS)) for option in OPTION_LABELS}


def _resolve_distractor_count(rng, params: Mapping[str, Any]) -> Tuple[int, Dict[str, float]]:
    low = int(params.get("distractor_count_min", group_default(_GEN_DEFAULTS, "distractor_count_min", _DEFAULTS.distractor_count_min)))
    high = int(params.get("distractor_count_max", group_default(_GEN_DEFAULTS, "distractor_count_max", _DEFAULTS.distractor_count_max)))
    if low < 0 or high < low:
        raise ValueError("invalid distractor_count_min/distractor_count_max")
    value = int(params.get("distractor_count", rng.randint(int(low), int(high))))
    if value < low or value > high:
        raise ValueError("distractor_count is outside configured bounds")
    prob = 1.0 / float((int(high) - int(low)) + 1)
    return int(value), {str(count): prob for count in range(int(low), int(high) + 1)}


def _shape_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get("shape_id_support", group_default(_GEN_DEFAULTS, "shape_id_support", PROCEDURAL_NAMED_ICON_SHAPES))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("shape_id_support must be a sequence")
    values = tuple(dict.fromkeys(str(value) for value in raw if str(value).strip()))
    unsupported = sorted(set(values) - set(PROCEDURAL_NAMED_ICON_SHAPES))
    if unsupported:
        raise ValueError(f"unsupported procedural named icon shapes: {unsupported}")
    if len(values) < 12:
        raise ValueError("paired named-icon task needs at least twelve supported icon shapes")
    return values


def _color_support(params: Mapping[str, Any]) -> Tuple[_NamedColorEntry, ...]:
    available = {str(name): tuple(int(channel) for channel in rgb) for name, rgb in available_named_colors()}
    raw = params.get("named_color_support", group_default(_GEN_DEFAULTS, "named_color_support", tuple(available)))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("named_color_support must be a sequence")
    names = tuple(dict.fromkeys(str(value).strip().lower() for value in raw if str(value).strip()))
    unsupported = sorted(set(names) - set(available))
    if unsupported:
        raise ValueError(f"unsupported named colors: {unsupported}")
    if len(names) < 4:
        raise ValueError("paired named-icon task needs at least four named colors")
    return tuple(
        _NamedColorEntry(
            name=str(name),
            rgb=tuple(int(channel) for channel in named_color(str(name))),
            label=format_named_color_with_hex(str(name), named_color(str(name))),
        )
        for name in names
    )


def _fill_style_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    key = "named_icon_fill_style_support"
    fallback = _DEFAULTS.named_icon_fill_style_support
    raw = params.get(key, group_default(_GEN_DEFAULTS, key, fallback))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raw = fallback
    return validate_procedural_named_icon_fill_style_support(tuple(str(value) for value in raw))



def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> Dict[str, Any]:
    """Resolve scene render knobs and candidate-label legibility metadata."""

    render_params = resolve_icon_render_params(
        params=params,
        render_defaults=_RENDER_DEFAULTS,
        fallback_defaults=_DEFAULTS,
        instance_seed=int(instance_seed),
    )
    for key in (
        "candidate_label_font_size_px",
        "candidate_label_padding_px",
        "candidate_label_gap_px",
        "icon_collision_gap_px",
        "paired_position_jitter_px",
    ):
        render_params[key] = int(params.get(key, group_default(_RENDER_DEFAULTS, key, getattr(_DEFAULTS, key))))
    for key in ("candidate_label_color_rgb", "candidate_label_background_rgb", "candidate_label_border_rgb"):
        raw = params.get(key, group_default(_RENDER_DEFAULTS, key, getattr(_DEFAULTS, key)))
        render_params[key] = tuple(int(value) for value in raw)
    candidate_label_style = resolve_readable_text_style(
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:candidate_label_text",
        role="paired_canvas_candidate_label_text",
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
    previous_legibility = render_params.get("text_legibility")
    previous_records = []
    if isinstance(previous_legibility, Mapping) and isinstance(previous_legibility.get("records"), list):
        previous_records = [dict(record) for record in previous_legibility["records"] if isinstance(record, Mapping)]
    render_params["text_legibility"] = text_legibility_summary_from_records(
        [*previous_records, candidate_label_record]
    )
    return render_params


def _random_color(rng, colors: Sequence[_NamedColorEntry]) -> _NamedColorEntry:
    return colors[int(rng.randrange(len(colors)))]


def _random_fill(rng, support: Sequence[str], probabilities: Mapping[str, float]) -> str:
    return sample_procedural_named_icon_fill_style(rng, support=support, probabilities=dict(probabilities))


def _random_state(
    rng,
    *,
    colors: Sequence[_NamedColorEntry],
    shapes: Sequence[str],
    fill_support: Sequence[str],
    fill_probabilities: Mapping[str, float],
    size_min: int,
    size_max: int,
) -> _IconState:
    color = _random_color(rng, colors)
    return _IconState(
        shape_id=str(shapes[int(rng.randrange(len(shapes)))]),
        color_name=str(color.name),
        tint_rgb=tuple(int(value) for value in color.rgb),
        fill_style=_random_fill(rng, fill_support, fill_probabilities),
        nominal_size_px=int(rng.randint(int(size_min), int(size_max))),
        rotation_degrees=int(rng.choice((0, 90, 180, 270))),
    )


def _matches_descriptor(
    state: _IconState,
    *,
    query_id: str,
    target_shape_id: str,
    target_color_name: str | None,
) -> bool:
    if str(state.shape_id) != str(target_shape_id):
        return False
    if str(query_id) == "original_color_shape_label":
        return str(state.color_name) == str(target_color_name)
    return True


def _state_avoiding_descriptor(
    rng,
    *,
    colors: Sequence[_NamedColorEntry],
    shapes: Sequence[str],
    fill_support: Sequence[str],
    fill_probabilities: Mapping[str, float],
    size_min: int,
    size_max: int,
    query_id: str,
    target_shape_id: str,
    target_color_name: str | None,
) -> _IconState:
    for _ in range(200):
        state = _random_state(
            rng,
            colors=colors,
            shapes=shapes,
            fill_support=fill_support,
            fill_probabilities=fill_probabilities,
            size_min=int(size_min),
            size_max=int(size_max),
        )
        if not _matches_descriptor(
            state,
            query_id=str(query_id),
            target_shape_id=str(target_shape_id),
            target_color_name=target_color_name,
        ):
            return state
    raise ValueError("failed to sample non-matching original named icon")


def _state_with_descriptor(
    base: _IconState,
    *,
    query_id: str,
    target_shape_id: str,
    target_color: _NamedColorEntry | None,
) -> _IconState:
    color_name = str(base.color_name)
    tint_rgb = tuple(int(value) for value in base.tint_rgb)
    if str(query_id) == "original_color_shape_label" and target_color is not None:
        color_name = str(target_color.name)
        tint_rgb = tuple(int(value) for value in target_color.rgb)
    return replace(base, shape_id=str(target_shape_id), color_name=color_name, tint_rgb=tint_rgb)


def _change_shape(rng, state: _IconState, shapes: Sequence[str], *, avoid: str) -> _IconState:
    choices = [str(shape) for shape in shapes if str(shape) != str(avoid)]
    return replace(state, shape_id=str(choices[int(rng.randrange(len(choices)))]))


def _change_color(rng, state: _IconState, colors: Sequence[_NamedColorEntry], *, avoid: str) -> _IconState:
    choices = [color for color in colors if str(color.name) != str(avoid)]
    color = choices[int(rng.randrange(len(choices)))]
    return replace(state, color_name=str(color.name), tint_rgb=tuple(int(value) for value in color.rgb))


def _change_fill(rng, state: _IconState, fill_support: Sequence[str], *, avoid: str) -> _IconState:
    choices = [str(fill) for fill in fill_support if str(fill) != str(avoid)]
    return replace(state, fill_style=str(choices[int(rng.randrange(len(choices)))]))


def _force_state_away_from_descriptor(
    rng,
    state: _IconState,
    *,
    query_id: str,
    colors: Sequence[_NamedColorEntry],
    shapes: Sequence[str],
    fill_support: Sequence[str],
    target_shape_id: str,
    target_color_name: str | None,
) -> _IconState:
    if not _matches_descriptor(
        state,
        query_id=str(query_id),
        target_shape_id=str(target_shape_id),
        target_color_name=target_color_name,
    ):
        return state
    if str(query_id) == "original_color_shape_label" and int(rng.randrange(2)) == 0 and target_color_name is not None:
        return _change_color(rng, state, colors, avoid=str(target_color_name))
    return _change_shape(rng, state, shapes, avoid=str(target_shape_id))


def _mutate_state(
    rng,
    state: _IconState,
    *,
    colors: Sequence[_NamedColorEntry],
    shapes: Sequence[str],
    fill_support: Sequence[str],
) -> _IconState:
    axis = str(rng.choice(("none", "shape", "color", "fill_style")))
    if axis == "shape":
        return _change_shape(rng, state, shapes, avoid=str(state.shape_id))
    if axis == "color":
        return _change_color(rng, state, colors, avoid=str(state.color_name))
    if axis == "fill_style":
        return _change_fill(rng, state, fill_support, avoid=str(state.fill_style))
    return state


def _descriptor_text(
    *,
    query_id: str,
    target_shape_name: str,
    target_color: _NamedColorEntry | None,
) -> str:
    quoted_shape = f'"{target_shape_name}"'
    if str(query_id) == "original_color_shape_label" and target_color is not None:
        return f"{target_color.label} {quoted_shape}"
    return str(quoted_shape)


def _sample_pairs(
    rng,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    render_params: Mapping[str, Any],
    query_id: str,
    answer_label: str,
    distractor_count: int,
) -> Tuple[Tuple[_PairPlan, ...], Dict[str, Any]]:
    """Create one-to-one icon pair plans with a unique original-state answer."""

    shapes = _shape_support(params)
    colors = _color_support(params)
    fill_support = _fill_style_support(params)
    fill_probabilities = resolve_named_icon_fill_style_probabilities(params, _GEN_DEFAULTS, fill_support, default_weights=DEFAULT_PROCEDURAL_NAMED_ICON_FILL_STYLE_WEIGHTS)
    size_min = int(render_params["scene_icon_size_min_px"])
    size_max = int(render_params["scene_icon_size_max_px"])
    target_shape_id = str(shapes[int(rng.randrange(len(shapes)))])
    target_color = _random_color(rng, colors) if str(query_id) == "original_color_shape_label" else None
    target_color_name = None if target_color is None else str(target_color.name)

    answer_original = _random_state(
        rng,
        colors=colors,
        shapes=shapes,
        fill_support=fill_support,
        fill_probabilities=fill_probabilities,
        size_min=size_min,
        size_max=size_max,
    )
    answer_original = _state_with_descriptor(
        answer_original,
        query_id=str(query_id),
        target_shape_id=str(target_shape_id),
        target_color=target_color,
    )
    answer_current = _force_state_away_from_descriptor(
        rng,
        answer_original,
        query_id=str(query_id),
        colors=colors,
        shapes=shapes,
        fill_support=fill_support,
        target_shape_id=str(target_shape_id),
        target_color_name=target_color_name,
    )

    false_positive_label = str(rng.choice([label for label in OPTION_LABELS if str(label) != str(answer_label)]))
    plans: List[_PairPlan] = []
    total_count = len(OPTION_LABELS) + int(distractor_count)
    for index in range(total_count):
        tracked = int(index) < len(OPTION_LABELS)
        label = str(OPTION_LABELS[int(index)]) if tracked else ""
        pair_id = f"pair_{int(index):02d}"
        if tracked and label == str(answer_label):
            original = answer_original
            current = answer_current
        else:
            original = _state_avoiding_descriptor(
                rng,
                colors=colors,
                shapes=shapes,
                fill_support=fill_support,
                fill_probabilities=fill_probabilities,
                size_min=size_min,
                size_max=size_max,
                query_id=str(query_id),
                target_shape_id=str(target_shape_id),
                target_color_name=target_color_name,
            )
            current = _mutate_state(rng, original, colors=colors, shapes=shapes, fill_support=fill_support)
            if tracked and label == str(false_positive_label):
                current = _state_with_descriptor(
                    current,
                    query_id=str(query_id),
                    target_shape_id=str(target_shape_id),
                    target_color=target_color,
                )
        plans.append(
            _PairPlan(
                pair_id=pair_id,
                label=label,
                tracked=bool(tracked),
                original=original,
                current=current,
                center_fraction_xy=(0.5, 0.5),
            )
        )

    changed_tracked = [
        index
        for index, plan in enumerate(plans[: len(OPTION_LABELS)])
        if (
            plan.original.shape_id != plan.current.shape_id
            or plan.original.color_name != plan.current.color_name
            or plan.original.fill_style != plan.current.fill_style
        )
    ]
    for index in range(len(OPTION_LABELS)):
        if len(changed_tracked) >= 3:
            break
        if int(index) in changed_tracked:
            continue
        plan = plans[int(index)]
        current = _change_shape(rng, plan.current, shapes, avoid=str(plan.current.shape_id))
        plans[int(index)] = replace(plan, current=current)
        changed_tracked.append(int(index))

    metadata = {
        "target_shape_id": str(target_shape_id),
        "target_shape_name": procedural_named_icon_display_name(str(target_shape_id)),
        "target_color": target_color,
        "target_description": _descriptor_text(
            query_id=str(query_id),
            target_shape_name=procedural_named_icon_display_name(str(target_shape_id)),
            target_color=target_color,
        ),
        "shape_probabilities": {str(shape): 1.0 / float(len(shapes)) for shape in shapes},
        "color_probabilities": {str(color.name): 1.0 / float(len(colors)) for color in colors},
        "fill_style_probabilities": dict(fill_probabilities),
        "false_positive_label": str(false_positive_label),
    }
    return tuple(plans), metadata


def _bbox_from_center(center_x: float, center_y: float, size: int, content_bbox: BBox) -> BBox:
    half = float(size) / 2.0
    x0 = int(round(float(center_x) - half))
    y0 = int(round(float(center_y) - half))
    x1 = int(x0 + int(size))
    y1 = int(y0 + int(size))
    cx0, cy0, cx1, cy1 = tuple(int(value) for value in content_bbox)
    if x0 < cx0 or y0 < cy0 or x1 > cx1 or y1 > cy1:
        raise ValueError("icon bbox is outside panel content")
    return (int(x0), int(y0), int(x1), int(y1))


def _place_pairs(
    rng,
    pairs: Sequence[_PairPlan],
    *,
    left_content: BBox,
    right_content: BBox,
    gap_px: int,
    right_jitter_px: int,
    attempts: int,
) -> Tuple[_PairPlan, ...]:
    """Place linked Original/Right icon pairs without overlap in either panel."""

    for _ in range(max(1, int(attempts))):
        placed: List[_PairPlan] = []
        left_bboxes: List[BBox] = []
        right_bboxes: List[BBox] = []
        ok = True
        for plan in pairs:
            size = int(plan.original.nominal_size_px)
            for _inner in range(250):
                lx0, ly0, lx1, ly1 = tuple(int(value) for value in left_content)
                rx0, ry0, rx1, ry1 = tuple(int(value) for value in right_content)
                left_cx = float(rng.randint(lx0 + size // 2, lx1 - size // 2))
                left_cy = float(rng.randint(ly0 + size // 2, ly1 - size // 2))
                frac_x = (left_cx - float(lx0)) / max(1.0, float(lx1 - lx0))
                frac_y = (left_cy - float(ly0)) / max(1.0, float(ly1 - ly0))
                right_cx = float(rx0) + float(frac_x) * float(rx1 - rx0)
                right_cy = float(ry0) + float(frac_y) * float(ry1 - ry0)
                right_cx += float(rng.randint(-int(right_jitter_px), int(right_jitter_px)))
                right_cy += float(rng.randint(-int(right_jitter_px), int(right_jitter_px)))
                try:
                    left_bbox = _bbox_from_center(left_cx, left_cy, size, left_content)
                    right_bbox = _bbox_from_center(right_cx, right_cy, size, right_content)
                except ValueError:
                    continue
                if float(max_overlap_with_existing(left_bbox, left_bboxes)) > 0.0:
                    continue
                if float(max_overlap_with_existing(right_bbox, right_bboxes)) > 0.0:
                    continue
                if _overlaps_with_gap(left_bbox, left_bboxes, gap_px=gap_px):
                    continue
                if _overlaps_with_gap(right_bbox, right_bboxes, gap_px=gap_px):
                    continue
                left_bboxes.append(left_bbox)
                right_bboxes.append(right_bbox)
                placed.append(replace(plan, center_fraction_xy=(float(frac_x), float(frac_y))))
                break
            else:
                ok = False
                break
        if ok and len(placed) == len(pairs):
            return tuple(placed)
    raise ValueError("failed to place paired named icons")


def _overlaps_with_gap(bbox: BBox, existing: Sequence[BBox], *, gap_px: int) -> bool:
    x0, y0, x1, y1 = tuple(int(value) for value in bbox)
    gap = max(0, int(gap_px))
    for other in existing:
        ox0, oy0, ox1, oy1 = tuple(int(value) for value in other)
        if x0 < ox1 + gap and x1 + gap > ox0 and y0 < oy1 + gap and y1 + gap > oy0:
            return True
    return False


def _draw_label_badge(
    image: Image.Image,
    *,
    label: str,
    icon_bbox: BBox,
    label_bounds: BBox,
    render_params: Mapping[str, Any],
) -> None:
    """Draw a right-panel option label near the icon without covering it."""

    draw = ImageDraw.Draw(image)
    font = load_font(int(render_params["candidate_label_font_size_px"]), bold=True)
    text_bbox = draw.textbbox((0, 0), str(label), font=font, stroke_width=0)
    text_w = int(text_bbox[2] - text_bbox[0])
    text_h = int(text_bbox[3] - text_bbox[1])
    pad = int(render_params["candidate_label_padding_px"])
    gap = int(render_params["candidate_label_gap_px"])
    badge_w = int(text_w + (2 * pad))
    badge_h = int(text_h + (2 * pad))
    bounds = tuple(int(value) for value in label_bounds)
    icon = tuple(int(value) for value in icon_bbox)
    icon_cx = 0.5 * float(icon[0] + icon[2])
    icon_cy = 0.5 * float(icon[1] + icon[3])

    def _clamp(value: int, low: int, high: int) -> int:
        return int(max(int(low), min(int(high), int(value))))

    def _fits(candidate: BBox) -> bool:
        return (
            int(candidate[0]) >= int(bounds[0])
            and int(candidate[1]) >= int(bounds[1])
            and int(candidate[2]) <= int(bounds[2])
            and int(candidate[3]) <= int(bounds[3])
        )

    def _overlaps(a: BBox, b: BBox) -> bool:
        return int(a[0]) < int(b[2]) and int(a[2]) > int(b[0]) and int(a[1]) < int(b[3]) and int(a[3]) > int(b[1])

    centered_x = _clamp(int(round(icon_cx - (float(badge_w) / 2.0))), bounds[0], bounds[2] - badge_w)
    centered_y = _clamp(int(round(icon_cy - (float(badge_h) / 2.0))), bounds[1], bounds[3] - badge_h)
    candidates: Tuple[BBox, ...] = (
        (centered_x, int(icon[1] - gap - badge_h), centered_x + badge_w, int(icon[1] - gap)),
        (centered_x, int(icon[3] + gap), centered_x + badge_w, int(icon[3] + gap + badge_h)),
        (int(icon[0] - gap - badge_w), centered_y, int(icon[0] - gap), centered_y + badge_h),
        (int(icon[2] + gap), centered_y, int(icon[2] + gap + badge_w), centered_y + badge_h),
    )
    badge_bbox = next(
        (
            candidate
            for candidate in candidates
            if _fits(candidate) and not _overlaps(candidate, icon)
        ),
        None,
    )
    if badge_bbox is None:
        loose_bounds = (0, 0, int(image.width), int(image.height))
        badge_bbox = next(
            (
                candidate
                for candidate in candidates
                if int(candidate[0]) >= 0
                and int(candidate[1]) >= 0
                and int(candidate[2]) <= int(loose_bounds[2])
                and int(candidate[3]) <= int(loose_bounds[3])
                and not _overlaps(candidate, icon)
            ),
            (centered_x, int(icon[3] + gap), centered_x + badge_w, int(icon[3] + gap + badge_h)),
        )
    x0, y0, x1, y1 = tuple(int(value) for value in badge_bbox)
    draw.rounded_rectangle(
        (x0, y0, x1, y1),
        radius=max(3, int(pad)),
        fill=tuple(int(value) for value in render_params["candidate_label_background_rgb"]),
        outline=tuple(int(value) for value in render_params["candidate_label_border_rgb"]),
        width=1,
    )
    draw_text_centered(
        draw,
        text=str(label),
        center=((float(x0 + x1) / 2.0), (float(y0 + y1) / 2.0) - 1.0),
        font=font,
        fill=tuple(int(value) for value in render_params["candidate_label_color_rgb"]),
        stroke_fill=tuple(int(value) for value in render_params["candidate_label_stroke_rgb"]),
        stroke_width=1,
    )


def _draw_icon(
    image: Image.Image,
    *,
    state: _IconState,
    bbox: BBox,
) -> None:
    sprite = render_procedural_named_icon_rgba(
        shape_id=str(state.shape_id),
        size_px=int(state.nominal_size_px),
        tint_rgb=tuple(int(value) for value in state.tint_rgb),
        fill_style=str(state.fill_style),
        rotation_degrees=int(state.rotation_degrees),
        mirror_x=False,
        noise_edits=tuple(state.noise_edits),
        noise_seed=state.noise_seed,
    )
    image.alpha_composite(sprite, (int(bbox[0]), int(bbox[1])))


def _serialize_rendered_icon(icon: _RenderedPanelIcon) -> Dict[str, Any]:
    return {
        "entity_kind": "procedural_named_icon",
        "instance_id": str(icon.instance_id),
        "pair_id": str(icon.pair_id),
        "panel": str(icon.panel),
        "label": str(icon.label),
        "tracked": bool(icon.tracked),
        "shape_id": str(icon.shape_id),
        "shape_name": str(icon.shape_name),
        "color_name": str(icon.color_name),
        "tint_rgb": [int(value) for value in icon.tint_rgb],
        "fill_style": str(icon.fill_style),
        "bbox_xyxy": [int(value) for value in icon.bbox_xyxy],
        "center_xy": [float(icon.center_xy[0]), float(icon.center_xy[1])],
        "nominal_size_px": int(icon.nominal_size_px),
        "rotation_degrees": int(icon.rotation_degrees),
        "noise_edits": [dict(edit) for edit in icon.noise_edits],
        "noise_seed": None if icon.noise_seed is None else int(icon.noise_seed),
    }


def _render_scene(
    *,
    rng,
    instance_seed: int,
    query_id: str,
    answer_label: str,
    distractor_count: int,
    params: Mapping[str, Any],
    render_params: Mapping[str, Any],
) -> Tuple[_ScenePayload, Image.Image]:
    """Render the paired original/current icon panels from task-owned pair plans."""

    pairs, meta = _sample_pairs(
        rng,
        instance_seed=int(instance_seed),
        params=params,
        render_params=render_params,
        query_id=str(query_id),
        answer_label=str(answer_label),
        distractor_count=int(distractor_count),
    )
    layout = resolve_two_panel_layout(
        canvas_width=int(render_params["canvas_width"]),
        canvas_height=int(render_params["canvas_height"]),
        reference_panel_width_px=int(render_params["reference_panel_width_px"]),
        outer_margin_px=int(render_params["outer_margin_px"]),
        panel_gap_px=int(render_params["panel_gap_px"]),
        panel_padding_px=int(render_params["panel_padding_px"]),
        title_font_size_px=int(render_params["panel_title_font_size_px"]),
    )
    pairs = _place_pairs(
        rng,
        pairs,
        left_content=tuple(int(value) for value in layout.reference_content_xyxy),
        right_content=tuple(int(value) for value in layout.scene_content_xyxy),
        gap_px=int(render_params["icon_collision_gap_px"]),
        right_jitter_px=int(render_params["paired_position_jitter_px"]),
        attempts=int(render_params["scene_placement_max_attempts"]),
    )

    image = Image.new("RGBA", (int(layout.canvas_width), int(layout.canvas_height)))
    draw_two_panel_panels(
        image=image,
        layout=layout,
        background_rgb=tuple(int(value) for value in render_params["background_color_rgb"]),
        panel_fill_rgb=tuple(int(value) for value in render_params["panel_fill_rgb"]),
        panel_border_rgb=tuple(int(value) for value in render_params["panel_border_rgb"]),
        title_color_rgb=tuple(int(value) for value in render_params["header_text_rgb"]),
        corner_radius_px=int(render_params["panel_corner_radius_px"]),
        title_font_size_px=int(render_params["panel_title_font_size_px"]),
        reference_title="Original",
        scene_title="Right",
        icon_canvas_style=render_params.get("_icon_canvas_style_object"),
    )

    original_icons: List[_RenderedPanelIcon] = []
    right_icons: List[_RenderedPanelIcon] = []
    for index, plan in enumerate(pairs):
        size = int(plan.original.nominal_size_px)
        lx0, ly0, lx1, ly1 = tuple(int(value) for value in layout.reference_content_xyxy)
        rx0, ry0, rx1, ry1 = tuple(int(value) for value in layout.scene_content_xyxy)
        frac_x, frac_y = float(plan.center_fraction_xy[0]), float(plan.center_fraction_xy[1])
        left_cx = float(lx0) + frac_x * float(lx1 - lx0)
        left_cy = float(ly0) + frac_y * float(ly1 - ly0)
        right_cx = float(rx0) + frac_x * float(rx1 - rx0)
        right_cy = float(ry0) + frac_y * float(ry1 - ry0)
        left_bbox = _bbox_from_center(left_cx, left_cy, size, tuple(int(value) for value in layout.reference_content_xyxy))
        right_bbox = _bbox_from_center(right_cx, right_cy, size, tuple(int(value) for value in layout.scene_content_xyxy))

        left_noise, left_noise_seed = sample_icon_instance_noise(
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:{plan.pair_id}:left",
            render_params=render_params,
        )
        right_noise, right_noise_seed = sample_icon_instance_noise(
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:{plan.pair_id}:right",
            render_params=render_params,
        )
        original_state = replace(plan.original, noise_edits=tuple(left_noise), noise_seed=int(left_noise_seed))
        current_state = replace(plan.current, noise_edits=tuple(right_noise), noise_seed=int(right_noise_seed))
        _draw_icon(image, state=original_state, bbox=left_bbox)
        _draw_icon(image, state=current_state, bbox=right_bbox)
        if plan.tracked:
            _draw_label_badge(
                image,
                label=str(plan.label),
                icon_bbox=right_bbox,
                label_bounds=tuple(int(value) for value in layout.scene_content_xyxy),
                render_params=render_params,
            )

        original_icons.append(
            _RenderedPanelIcon(
                instance_id=f"original_{int(index):02d}",
                pair_id=str(plan.pair_id),
                panel="original",
                label="",
                tracked=bool(plan.tracked),
                shape_id=str(original_state.shape_id),
                shape_name=procedural_named_icon_display_name(str(original_state.shape_id)),
                color_name=str(original_state.color_name),
                tint_rgb=tuple(int(value) for value in original_state.tint_rgb),
                fill_style=str(original_state.fill_style),
                bbox_xyxy=tuple(int(value) for value in left_bbox),
                center_xy=(float((left_bbox[0] + left_bbox[2]) / 2.0), float((left_bbox[1] + left_bbox[3]) / 2.0)),
                nominal_size_px=int(original_state.nominal_size_px),
                rotation_degrees=int(original_state.rotation_degrees) % 360,
                noise_edits=serialize_icon_noise_edits(tuple(original_state.noise_edits)),
                noise_seed=int(original_state.noise_seed),
            )
        )
        right_icons.append(
            _RenderedPanelIcon(
                instance_id=f"right_{int(index):02d}",
                pair_id=str(plan.pair_id),
                panel="right",
                label=str(plan.label),
                tracked=bool(plan.tracked),
                shape_id=str(current_state.shape_id),
                shape_name=procedural_named_icon_display_name(str(current_state.shape_id)),
                color_name=str(current_state.color_name),
                tint_rgb=tuple(int(value) for value in current_state.tint_rgb),
                fill_style=str(current_state.fill_style),
                bbox_xyxy=tuple(int(value) for value in right_bbox),
                center_xy=(float((right_bbox[0] + right_bbox[2]) / 2.0), float((right_bbox[1] + right_bbox[3]) / 2.0)),
                nominal_size_px=int(current_state.nominal_size_px),
                rotation_degrees=int(current_state.rotation_degrees) % 360,
                noise_edits=serialize_icon_noise_edits(tuple(current_state.noise_edits)),
                noise_seed=int(current_state.noise_seed),
            )
        )

    answer_pair_id = next(str(plan.pair_id) for plan in pairs if str(plan.label) == str(answer_label))
    payload = _ScenePayload(
        query_id=str(query_id),
        answer_label=str(answer_label),
        answer_pair_id=str(answer_pair_id),
        target_shape_id=str(meta["target_shape_id"]),
        target_shape_name=str(meta["target_shape_name"]),
        target_color=meta["target_color"],
        target_description=str(meta["target_description"]),
        pairs=tuple(pairs),
        original_icons=tuple(original_icons),
        right_icons=tuple(right_icons),
        panel_geometry=panel_geometry_to_trace(layout),
        sampled_palette_rgb=tuple(color.rgb for color in _color_support(params)),
        distractor_count=int(distractor_count),
        false_positive_label=str(meta["false_positive_label"]),
    )
    return payload, image.convert("RGB")




@register_task
class IconsRelationNamedOriginalAttributeLabelTask:
    """Select the labeled right-panel icon by its original named-icon attributes."""

    task_id = TASK_ID
    domain = "icons"
    supported_query_ids = QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one original-attribute option-label instance and verifier payload."""

        sample_rng = spawn_rng(int(instance_seed), f"{TASK_ID}:sample")
        query_id, query_probabilities, task_params = _select_query(int(instance_seed), params)
        answer_label, answer_label_probabilities = _resolve_answer_label(sample_rng, params=task_params)
        distractor_count, distractor_count_probabilities = _resolve_distractor_count(sample_rng, params=task_params)
        render_params = _render_params(task_params, instance_seed=int(instance_seed))

        scene_payload = None
        image = None
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            try:
                scene_rng = spawn_rng(int(instance_seed), f"{TASK_ID}:scene", int(attempt_index))
                scene_payload, image = _render_scene(
                    rng=scene_rng,
                    instance_seed=int(instance_seed),
                    query_id=str(query_id),
                    answer_label=str(answer_label),
                    distractor_count=int(distractor_count),
                    params=task_params,
                    render_params=render_params,
                )
                break
            except Exception as exc:
                last_error = exc
                continue
        if scene_payload is None or image is None:
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
            target_description=str(scene_payload.target_description)
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            scene_id=SCENE_ID,
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

        original_by_pair = {str(icon.pair_id): icon for icon in scene_payload.original_icons}
        right_by_pair = {str(icon.pair_id): icon for icon in scene_payload.right_icons}
        answer_original = original_by_pair[str(scene_payload.answer_pair_id)]
        answer_right = right_by_pair[str(scene_payload.answer_pair_id)]
        annotation_artifacts = icon_bbox_map_annotation(
            {
                "original_icon": answer_original.bbox_xyxy,
                "right_icon": answer_right.bbox_xyxy,
            }
        )

        serialized_originals = [_serialize_rendered_icon(icon) for icon in scene_payload.original_icons]
        serialized_rights = [_serialize_rendered_icon(icon) for icon in scene_payload.right_icons]
        pair_records = [
            {
                "pair_id": str(plan.pair_id),
                "label": str(plan.label),
                "tracked": bool(plan.tracked),
                "original": {
                    "shape_id": str(plan.original.shape_id),
                    "shape_name": procedural_named_icon_display_name(str(plan.original.shape_id)),
                    "color_name": str(plan.original.color_name),
                    "fill_style": str(plan.original.fill_style),
                },
                "right": {
                    "shape_id": str(plan.current.shape_id),
                    "shape_name": procedural_named_icon_display_name(str(plan.current.shape_id)),
                    "color_name": str(plan.current.color_name),
                    "fill_style": str(plan.current.fill_style),
                },
                "is_answer": str(plan.label) == str(scene_payload.answer_label),
            }
            for plan in scene_payload.pairs
        ]

        trace_payload = {
            "scene_ir": {
                "scene_kind": "icons_paired_named_original_attribute",
                "entities": [*serialized_originals, *serialized_rights],
                "relations": {
                    "target": "right_labeled_icon_by_original_named_attribute",
                    "query_id": str(scene_payload.query_id),
                    "target_description": str(scene_payload.target_description),
                    "answer_label": str(scene_payload.answer_label),
                    "answer_pair_id": str(scene_payload.answer_pair_id),
                    "candidate_labels": [str(label) for label in OPTION_LABELS],
                    "false_positive_label": str(scene_payload.false_positive_label),
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(scene_payload.panel_geometry),
                },
            },
            "query_spec": {
                "query_id": str(scene_payload.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(scene_payload.query_id),
                    "query_id_probabilities": dict(query_probabilities),
                    "original_attribute_query": str(scene_payload.query_id),
                    "original_attribute_query_probabilities": dict(query_probabilities),
                    "answer_label": str(scene_payload.answer_label),
                    "answer_label_probabilities": dict(answer_label_probabilities),
                    "distractor_count": int(scene_payload.distractor_count),
                    "distractor_count_probabilities": dict(distractor_count_probabilities),
                    "target_description": str(scene_payload.target_description),
                },
            },
            "render_spec": {
                "canvas_size": [int(render_params["canvas_width"]), int(render_params["canvas_height"])],
                "coord_space": "pixel",
                "panel_geometry": dict(scene_payload.panel_geometry),
                "style": {
                    **icon_render_style_trace(
                        render_params=render_params,
                        sampled_palette_rgb=tuple(scene_payload.sampled_palette_rgb),
                    ),
                    "candidate_label_font_size_px": int(render_params["candidate_label_font_size_px"]),
                    "candidate_label_color_rgb": [int(value) for value in render_params["candidate_label_color_rgb"]],
                    "candidate_label_stroke_rgb": [int(value) for value in render_params["candidate_label_stroke_rgb"]],
                    "candidate_label_background_rgb": [int(value) for value in render_params["candidate_label_background_rgb"]],
                    "candidate_label_border_rgb": [int(value) for value in render_params["candidate_label_border_rgb"]],
                    "candidate_label_padding_px": int(render_params["candidate_label_padding_px"]),
                    "candidate_label_gap_px": int(render_params["candidate_label_gap_px"]),
                    "paired_position_jitter_px": int(render_params["paired_position_jitter_px"]),
                },
            },
            "render_map": {
                "image_id": "img0",
                "anchors": {
                    "original_icons": serialized_originals,
                    "right_icons": serialized_rights,
                    "answer_label": str(scene_payload.answer_label),
                    "answer_original": _serialize_rendered_icon(answer_original),
                    "answer_right": _serialize_rendered_icon(answer_right),
                },
            },
            "execution_trace": {
                "scene_variant": "paired_canvas_original_to_right",
                "query_id": str(scene_payload.query_id),
                "original_attribute_query": str(scene_payload.query_id),
                "original_attribute_query_probabilities": dict(query_probabilities),
                "answer_label": str(scene_payload.answer_label),
                "answer_label_probabilities": dict(answer_label_probabilities),
                "answer_pair_id": str(scene_payload.answer_pair_id),
                "candidate_labels": [str(label) for label in OPTION_LABELS],
                "tracked_count": int(len(OPTION_LABELS)),
                "distractor_count": int(scene_payload.distractor_count),
                "distractor_count_probabilities": dict(distractor_count_probabilities),
                "target_description": str(scene_payload.target_description),
                "pair_records": pair_records,
                "question_format": "select_labeled_right_icon_by_original_named_attribute",
            },
            "witness_symbolic": {
                "query_id": str(scene_payload.query_id),
                "target_description": str(scene_payload.target_description),
                "answer_label": str(scene_payload.answer_label),
                "answer_pair_id": str(scene_payload.answer_pair_id),
                "annotation_roles": {
                    "original_icon": str(answer_original.instance_id),
                    "right_icon": str(answer_right.instance_id),
                },
            },
            "projected_annotation": {
                **dict(annotation_artifacts["projected_annotation"]),
                "items": [
                    {"role": "original_icon", "instance_id": str(answer_original.instance_id), "bbox_xyxy": list(answer_original.bbox_xyxy)},
                    {"role": "right_icon", "instance_id": str(answer_right.instance_id), "bbox_xyxy": list(answer_right.bbox_xyxy)},
                ],
            },
        }
        output = TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=TypedValue(type="option_letter", value=str(scene_payload.answer_label)),
            annotation_gt=TypedValue(
                type=str(annotation_artifacts["annotation_type"]),
                value=dict(annotation_artifacts["annotation_value"]),
            ),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(scene_payload.query_id),
        )
        return output


__all__ = [
    "IconsRelationNamedOriginalAttributeLabelTask",
    "QUERY_IDS",
    "TASK_ID",
]
