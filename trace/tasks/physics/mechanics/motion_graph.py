"""Physics mechanics task for kinematics graph state interpretation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.bbox_projection import bbox_union_many as _bbox_union
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.drawing import draw_centered_text
from ...shared.font_assets import font_asset_version, get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import build_prompt_json_examples
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.render_variation import resolve_layout_jitter, resolve_render_int
from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_compatible_scene_query_ids, resolve_variant
from ..shared.diagram_style import prepare_physics_diagram_style_and_background
from ..shared.option_cards import draw_lettered_option_cards
from ..shared.visual_defaults import load_physics_noise_defaults


FAMILY_ID = "physics_mechanics_motion_graph_family"
INTERVAL_FAMILY_ID = "physics_mechanics_motion_graph_interval_displacement_family"
INTERVAL_TASK_ID = "task_physics__motion_graph__interval_displacement_value"
SCENE_ID = "motion_graph"
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "clean_grid",
    "paper_grid",
    "bold_grid",
)
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "velocity_sign_choice",
    "speed_change_state_choice",
)
INTERVAL_QUERY_IDS: Tuple[str, ...] = (
    "constant_velocity_interval_displacement",
    "constant_acceleration_interval_displacement",
)
OPTION_LETTERS: Tuple[str, ...] = ("A", "B", "C", "D")
VELOCITY_SIGN_STATES: Tuple[str, ...] = ("moving_right", "moving_left", "stationary")
SPEEDING_STATES: Tuple[str, ...] = ("speeding_up", "slowing_down", "constant_speed")
STATE_LABELS: Dict[str, str] = {
    "moving_right": "moving right",
    "moving_left": "moving left",
    "stationary": "stationary",
    "speeding_up": "speeding up",
    "slowing_down": "slowing down",
    "constant_speed": "constant speed",
    "changing_direction": "changing direction",
}
COMPATIBILITY: Dict[str, Sequence[str]] = {
    "clean_grid": SUPPORTED_QUERY_IDS,
    "paper_grid": SUPPORTED_QUERY_IDS,
    "bold_grid": SUPPORTED_QUERY_IDS,
}
INTERVAL_COMPATIBILITY: Dict[str, Sequence[str]] = {
    "clean_grid": INTERVAL_QUERY_IDS,
    "paper_grid": INTERVAL_QUERY_IDS,
    "bold_grid": INTERVAL_QUERY_IDS,
}

_TASK_GROUP_DEFAULTS = get_task_group_defaults("physics", "mechanics")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=FAMILY_ID,
)
_INTERVAL_GEN_DEFAULTS, _INTERVAL_RENDER_DEFAULTS, _INTERVAL_PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=INTERVAL_FAMILY_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(task_group="mechanics", apply_prob=0.5)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for motion graph scenes."""

    canvas_width: int = 1120
    canvas_height: int = 760
    plot_left_px: int = 132
    plot_top_px: int = 74
    plot_width_px: int = 856
    plot_height_px: int = 500
    option_panel_top_px: int = 610
    option_cell_left_px: int = 70
    option_cell_width_px: int = 468
    option_cell_height_px: int = 66
    option_cell_gap_x_px: int = 24
    option_cell_gap_y_px: int = 14
    axis_width_px: int = 5
    curve_width_px: int = 7
    grid_line_width_px: int = 1
    bold_grid_line_width_px: int = 2
    label_font_size_px: int = 25
    tick_font_size_px: int = 18
    option_font_size_px: int = 22
    title_font_size_px: int = 28
    label_stroke_width_px: int = 2
    point_radius_px: int = 5
    y_min: int = -5
    y_max: int = 5
    t_min: int = 0
    t_max: int = 6


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved scene/query/state/answer axes for one instance."""

    scene_variant: str
    query_id: str
    motion_state: str
    correct_option_letter: str
    scene_variant_probabilities: Dict[str, float]
    query_id_probabilities: Dict[str, float]
    motion_state_probabilities: Dict[str, float]
    correct_option_letter_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _GraphSpec:
    """Symbolic kinematics graph and queried segment."""

    scene_variant: str
    query_id: str
    graph_kind: str
    motion_state: str
    correct_option_letter: str
    option_map: Dict[str, str]
    t_values: Tuple[int, ...]
    y_values: Tuple[int, ...]
    query_segment_index: int
    y_axis_label: str
    title: str


@dataclass(frozen=True)
class _IntervalAxes:
    """Resolved axes for one interval-displacement graph instance."""

    scene_variant: str
    query_id: str
    scene_variant_probabilities: Dict[str, float]
    query_id_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _IntervalGraphSpec:
    """Symbolic velocity-time graph for interval displacement."""

    scene_variant: str
    query_id: str
    graph_kind: str
    t_values: Tuple[int, ...]
    velocity_values: Tuple[int, ...]
    t_start: int
    t_end: int
    v_start: int
    v_end: int
    displacement_m: int
    y_axis_label: str
    title: str


@dataclass(frozen=True)
class _RenderedScene:
    """Rendered motion graph scene plus prompt-facing annotation metadata."""

    image: Image.Image
    annotation_bbox_map: Dict[str, List[float]]
    scene_entities: List[Dict[str, Any]]
    render_map: Dict[str, Any]


_DEFAULTS = _TaskDefaults()


def _states_for_query(query_id: str) -> Tuple[str, ...]:
    if str(query_id) == "velocity_sign_choice":
        return VELOCITY_SIGN_STATES
    if str(query_id) == "speed_change_state_choice":
        return SPEEDING_STATES
    raise ValueError(f"unsupported query_id: {query_id}")


def _resolve_motion_state(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    query_id: str,
) -> Tuple[str, Dict[str, float]]:
    states = _states_for_query(str(query_id))
    explicit_state = params.get("motion_state", params.get("target_state", params.get("target_answer")))
    state_params = dict(params)
    if explicit_state is not None:
        state_params["motion_state"] = str(explicit_state)
    selected, probabilities = resolve_variant(
        spawn_rng(int(instance_seed), f"{FAMILY_ID}.motion_state"),
        params=state_params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=states,
        explicit_key="motion_state",
        weights_key=f"{str(query_id)}_state_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=state_params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=states,
        balance_flag_key="balanced_motion_state_sampling",
        explicit_key="motion_state",
        weights_key=f"{str(query_id)}_state_weights",
        sampling_namespace=f"{FAMILY_ID}.motion_state.{str(query_id)}",
    )
    return str(selected), {str(key): float(value) for key, value in probabilities.items()}


def _resolve_correct_option_letter(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
    selected, probabilities = resolve_variant(
        spawn_rng(int(instance_seed), f"{FAMILY_ID}.correct_option_letter"),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=OPTION_LETTERS,
        explicit_key="correct_option_letter",
        weights_key="correct_option_letter_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=OPTION_LETTERS,
        balance_flag_key="balanced_correct_option_letter_sampling",
        explicit_key="correct_option_letter",
        weights_key="correct_option_letter_weights",
        sampling_namespace=f"{FAMILY_ID}.correct_option_letter",
    )
    return str(selected), {str(key): float(value) for key, value in probabilities.items()}


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    rng = spawn_rng(int(instance_seed), f"{FAMILY_ID}.axes")
    scene_variant, scene_probs, query_id, query_probs = resolve_compatible_scene_query_ids(
        rng,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_scene_variants=SUPPORTED_SCENE_VARIANTS,
        supported_query_ids=SUPPORTED_QUERY_IDS,
        compatibility=COMPATIBILITY,
        scene_sampling_namespace=f"{FAMILY_ID}.scene_variant",
        query_sampling_namespace=f"{FAMILY_ID}.query_id",
    )
    motion_state, state_probs = _resolve_motion_state(
        instance_seed=int(instance_seed),
        params=params,
        query_id=str(query_id),
    )
    correct_option_letter, option_probs = _resolve_correct_option_letter(
        instance_seed=int(instance_seed),
        params=params,
    )
    return _ResolvedAxes(
        scene_variant=str(scene_variant),
        query_id=str(query_id),
        motion_state=str(motion_state),
        correct_option_letter=str(correct_option_letter),
        scene_variant_probabilities=dict(scene_probs),
        query_id_probabilities=dict(query_probs),
        motion_state_probabilities=dict(state_probs),
        correct_option_letter_probabilities=dict(option_probs),
    )


def _target_segment_values(rng, *, query_id: str, motion_state: str) -> Tuple[int, int]:
    if str(query_id) == "velocity_sign_choice":
        if str(motion_state) == "moving_right":
            delta = int(rng.choice([2, 3]))
            y0 = int(rng.choice([-4, -3, -2, -1, 0, 1]))
            return y0, y0 + delta
        if str(motion_state) == "moving_left":
            delta = int(rng.choice([-3, -2]))
            y0 = int(rng.choice([-1, 0, 1, 2, 3, 4]))
            return y0, y0 + delta
        if str(motion_state) == "stationary":
            y0 = int(rng.choice([-4, -3, -2, -1, 1, 2, 3, 4]))
            return y0, y0
    else:
        sign = int(rng.choice([-1, 1]))
        if str(motion_state) == "speeding_up":
            start_abs, end_abs = rng.choice([(1, 3), (1, 4), (2, 4)])
            return sign * int(start_abs), sign * int(end_abs)
        if str(motion_state) == "slowing_down":
            start_abs, end_abs = rng.choice([(4, 2), (4, 1), (3, 1)])
            return sign * int(start_abs), sign * int(end_abs)
        if str(motion_state) == "constant_speed":
            value = sign * int(rng.choice([2, 3, 4]))
            return value, value
    raise ValueError(f"unsupported motion state {motion_state} for {query_id}")


def _extend_values(rng, *, values: List[int], fixed_index: int, y_min: int, y_max: int) -> Tuple[int, ...]:
    deltas = [-2, -1, 0, 1, 2]
    for index in range(int(fixed_index) - 1, -1, -1):
        current = int(values[index + 1])
        feasible = [delta for delta in deltas if int(y_min) <= current - int(delta) <= int(y_max)]
        values[index] = int(current - int(rng.choice(feasible)))
    for index in range(int(fixed_index) + 2, len(values)):
        current = int(values[index - 1])
        feasible = [delta for delta in deltas if int(y_min) <= current + int(delta) <= int(y_max)]
        values[index] = int(current + int(rng.choice(feasible)))
    return tuple(int(value) for value in values)


def _build_option_map(
    *,
    instance_seed: int,
    query_id: str,
    motion_state: str,
    correct_option_letter: str,
) -> Dict[str, str]:
    states = list(_states_for_query(str(query_id))) + ["changing_direction"]
    remaining = [state for state in states if str(state) != str(motion_state)]
    rng = spawn_rng(int(instance_seed), f"{FAMILY_ID}.option_map")
    rng.shuffle(remaining)
    option_map: Dict[str, str] = {}
    for letter in OPTION_LETTERS:
        if str(letter) == str(correct_option_letter):
            option_map[str(letter)] = str(motion_state)
    remaining_letters = [letter for letter in OPTION_LETTERS if str(letter) != str(correct_option_letter)]
    for letter, state in zip(remaining_letters, remaining):
        option_map[str(letter)] = str(state)
    return {str(letter): str(option_map[str(letter)]) for letter in OPTION_LETTERS}


def _make_graph_spec(instance_seed: int, *, axes: _ResolvedAxes, params: Mapping[str, Any]) -> _GraphSpec:
    rng = spawn_rng(int(instance_seed), f"{FAMILY_ID}.graph_spec")
    y_min = int(params.get("y_min", group_default(_RENDER_DEFAULTS, "y_min", _DEFAULTS.y_min)))
    y_max = int(params.get("y_max", group_default(_RENDER_DEFAULTS, "y_max", _DEFAULTS.y_max)))
    t_min = int(params.get("t_min", group_default(_RENDER_DEFAULTS, "t_min", _DEFAULTS.t_min)))
    t_max = int(params.get("t_max", group_default(_RENDER_DEFAULTS, "t_max", _DEFAULTS.t_max)))
    t_values = tuple(range(int(t_min), int(t_max) + 1))
    if len(t_values) < 5:
        raise ValueError("motion graph needs at least five time samples")
    query_segment_index = int(params.get("query_segment_index", rng.choice([1, 2, 3, 4])))
    query_segment_index = max(1, min(len(t_values) - 2, int(query_segment_index)))
    y0, y1 = _target_segment_values(rng, query_id=axes.query_id, motion_state=axes.motion_state)
    if not (int(y_min) <= int(y0) <= int(y_max) and int(y_min) <= int(y1) <= int(y_max)):
        raise ValueError("target motion segment values out of bounds")
    y_values: List[int] = [0 for _ in t_values]
    y_values[query_segment_index] = int(y0)
    y_values[query_segment_index + 1] = int(y1)
    y_values = list(
        _extend_values(
            rng,
            values=y_values,
            fixed_index=int(query_segment_index),
            y_min=int(y_min),
            y_max=int(y_max),
        )
    )
    graph_kind = "position_time" if str(axes.query_id) == "velocity_sign_choice" else "velocity_time"
    return _GraphSpec(
        scene_variant=str(axes.scene_variant),
        query_id=str(axes.query_id),
        graph_kind=str(graph_kind),
        motion_state=str(axes.motion_state),
        correct_option_letter=str(axes.correct_option_letter),
        option_map=_build_option_map(
            instance_seed=int(instance_seed),
            query_id=str(axes.query_id),
            motion_state=str(axes.motion_state),
            correct_option_letter=str(axes.correct_option_letter),
        ),
        t_values=tuple(int(value) for value in t_values),
        y_values=tuple(int(value) for value in y_values),
        query_segment_index=int(query_segment_index),
        y_axis_label="x (m)" if str(graph_kind) == "position_time" else "v (m/s)",
        title="position-time graph" if str(graph_kind) == "position_time" else "velocity-time graph",
    )


def _bbox_from_points(points: Sequence[Tuple[float, float]], padding: float = 0.0) -> List[float]:
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return [
        round(min(xs) - float(padding), 3),
        round(min(ys) - float(padding), 3),
        round(max(xs) + float(padding), 3),
        round(max(ys) + float(padding), 3),
    ]


def _text_bbox(draw: ImageDraw.ImageDraw, text: str, center: Tuple[float, float], font: Any, padding: float = 5.0) -> List[float]:
    bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=0)
    width = float(bbox[2] - bbox[0])
    height = float(bbox[3] - bbox[1])
    return [
        round(float(center[0]) - width / 2.0 - float(padding), 3),
        round(float(center[1]) - height / 2.0 - float(padding), 3),
        round(float(center[0]) + width / 2.0 + float(padding), 3),
        round(float(center[1]) + height / 2.0 + float(padding), 3),
    ]


def _render_scene(
    *,
    image: Image.Image,
    spec: _GraphSpec,
    render_defaults: Mapping[str, Any],
    font_family: str,
    style: Any,
) -> _RenderedScene:
    draw = ImageDraw.Draw(image)
    width, height = image.size
    plot_left = float(render_defaults["plot_left_px"])
    plot_top = float(render_defaults["plot_top_px"])
    plot_width = float(render_defaults["plot_width_px"])
    plot_height = float(render_defaults["plot_height_px"])
    plot_right = plot_left + plot_width
    plot_bottom = plot_top + plot_height
    y_min = int(render_defaults["y_min"])
    y_max = int(render_defaults["y_max"])
    t_min = int(render_defaults["t_min"])
    t_max = int(render_defaults["t_max"])

    title_font = load_font(int(render_defaults["title_font_size_px"]), bold=True, font_family=font_family)
    label_font = load_font(int(render_defaults["label_font_size_px"]), bold=True, font_family=font_family)
    tick_font = load_font(int(render_defaults["tick_font_size_px"]), bold=False, font_family=font_family)
    option_font = load_font(int(render_defaults["option_font_size_px"]), bold=True, font_family=font_family)

    panel_bbox = [48, 40, width - 48, int(render_defaults["option_panel_top_px"]) - 24]
    draw.rounded_rectangle(
        panel_bbox,
        radius=18,
        fill=tuple(int(v) for v in style.panel_fill_rgb),
        outline=tuple(int(v) for v in style.panel_border_rgb),
        width=3,
    )
    plot_fill = tuple(int(v) for v in (style.panel_alt_fill_rgb if str(spec.scene_variant) == "paper_grid" else style.panel_fill_rgb))
    draw.rounded_rectangle(
        [plot_left - 18, plot_top - 22, plot_right + 28, plot_bottom + 42],
        radius=14,
        fill=plot_fill,
        outline=tuple(int(v) for v in style.panel_border_rgb),
        width=2,
    )

    def x_px(t_value: float) -> float:
        return float(plot_left + ((float(t_value) - t_min) / max(1.0, t_max - t_min)) * plot_width)

    def y_px(y_value: float) -> float:
        return float(plot_bottom - ((float(y_value) - y_min) / max(1.0, y_max - y_min)) * plot_height)

    grid_width = int(render_defaults["bold_grid_line_width_px"] if str(spec.scene_variant) == "bold_grid" else render_defaults["grid_line_width_px"])
    for t_value in range(t_min, t_max + 1):
        x = x_px(float(t_value))
        draw.line([(x, plot_top), (x, plot_bottom)], fill=tuple(int(v) for v in style.grid_minor_rgb), width=grid_width)
        draw_centered_text(
            draw,
            text=str(t_value),
            center=(x, plot_bottom + 23),
            font=tick_font,
            fill=tuple(int(v) for v in style.label_rgb),
            stroke_fill=resolve_text_stroke_fill(tuple(int(v) for v in style.label_rgb)),
            stroke_width=1,
        )
    for y_value in range(y_min, y_max + 1):
        y = y_px(float(y_value))
        line_width = int(render_defaults["bold_grid_line_width_px"] if y_value == 0 else grid_width)
        line_fill = tuple(int(v) for v in (style.axis_rgb if y_value == 0 else style.grid_minor_rgb))
        draw.line([(plot_left, y), (plot_right, y)], fill=line_fill, width=line_width)
        if y_value % 2 == 0:
            draw_centered_text(
                draw,
                text=str(y_value),
                center=(plot_left - 28, y),
                font=tick_font,
                fill=tuple(int(v) for v in style.label_rgb),
                stroke_fill=resolve_text_stroke_fill(tuple(int(v) for v in style.label_rgb)),
                stroke_width=1,
            )

    axis_rgb = tuple(int(v) for v in style.axis_rgb)
    draw.line([(plot_left, plot_bottom), (plot_right + 14, plot_bottom)], fill=axis_rgb, width=int(render_defaults["axis_width_px"]))
    draw.line([(plot_left, plot_top - 14), (plot_left, plot_bottom)], fill=axis_rgb, width=int(render_defaults["axis_width_px"]))
    draw.polygon([(plot_right + 14, plot_bottom), (plot_right - 5, plot_bottom - 9), (plot_right - 5, plot_bottom + 9)], fill=axis_rgb)
    draw.polygon([(plot_left, plot_top - 14), (plot_left - 9, plot_top + 5), (plot_left + 9, plot_top + 5)], fill=axis_rgb)
    label_rgb = tuple(int(v) for v in style.label_rgb)
    draw_centered_text(draw, text="t (s)", center=(plot_right + 52, plot_bottom + 18), font=label_font, fill=label_rgb, stroke_fill=resolve_text_stroke_fill(label_rgb), stroke_width=1)
    draw_centered_text(draw, text=str(spec.y_axis_label), center=(plot_left + 8, plot_top - 42), font=label_font, fill=label_rgb, stroke_fill=resolve_text_stroke_fill(label_rgb), stroke_width=1)
    draw_centered_text(draw, text=str(spec.title), center=(width * 0.5, panel_bbox[1] + 28), font=title_font, fill=label_rgb, stroke_fill=resolve_text_stroke_fill(label_rgb), stroke_width=1)

    points = [(x_px(t), y_px(y)) for t, y in zip(spec.t_values, spec.y_values)]
    seg_start = points[spec.query_segment_index]
    seg_end = points[spec.query_segment_index + 1]
    band_left = x_px(spec.t_values[spec.query_segment_index])
    band_right = x_px(spec.t_values[spec.query_segment_index + 1])
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    accent = tuple(int(v) for v in style.accent_rgb)
    overlay_draw.rectangle(
        [band_left, plot_top, band_right, plot_bottom],
        fill=(accent[0], accent[1], accent[2], 46),
        outline=(accent[0], accent[1], accent[2], 180),
        width=3,
    )
    image.alpha_composite(overlay) if image.mode == "RGBA" else image.paste(Image.alpha_composite(image.convert("RGBA"), overlay).convert(image.mode))
    draw = ImageDraw.Draw(image)

    curve_rgb = tuple(int(v) for v in style.stroke_rgb)
    draw.line(points, fill=curve_rgb, width=int(render_defaults["curve_width_px"]), joint="curve")
    highlight_rgb = tuple(int(v) for v in style.accent_rgb)
    draw.line([seg_start, seg_end], fill=highlight_rgb, width=int(render_defaults["curve_width_px"]) + 3)
    for point in points:
        radius = float(render_defaults["point_radius_px"])
        draw.ellipse([point[0] - radius, point[1] - radius, point[0] + radius, point[1] + radius], fill=curve_rgb, outline=tuple(int(v) for v in style.panel_fill_rgb), width=2)

    bracket_y = plot_top + 18.0
    draw.line([(band_left, bracket_y), (band_right, bracket_y)], fill=highlight_rgb, width=4)
    draw.line([(band_left, bracket_y - 10), (band_left, bracket_y + 10)], fill=highlight_rgb, width=4)
    draw.line([(band_right, bracket_y - 10), (band_right, bracket_y + 10)], fill=highlight_rgb, width=4)
    draw_centered_text(
        draw,
        text="marked interval",
        center=((band_left + band_right) / 2.0, bracket_y + 24.0),
        font=tick_font,
        fill=highlight_rgb,
        stroke_fill=resolve_text_stroke_fill(highlight_rgb),
        stroke_width=1,
    )

    scene_entities: List[Dict[str, Any]] = []
    query_region_bbox = [round(float(band_left), 3), round(float(plot_top), 3), round(float(band_right), 3), round(float(plot_bottom), 3)]
    curve_segment_bbox = _bbox_from_points([seg_start, seg_end], padding=float(render_defaults["curve_width_px"]) + 6.0)
    scene_entities.extend(
        [
            {
                "entity_id": "query_region",
                "entity_type": "marked_time_interval",
                "bbox_px": list(query_region_bbox),
                "meta": {"t_start": int(spec.t_values[spec.query_segment_index]), "t_end": int(spec.t_values[spec.query_segment_index + 1])},
            },
            {
                "entity_id": "curve_segment",
                "entity_type": "queried_graph_segment",
                "bbox_px": list(curve_segment_bbox),
                "meta": {
                    "y_start": int(spec.y_values[spec.query_segment_index]),
                    "y_end": int(spec.y_values[spec.query_segment_index + 1]),
                    "motion_state": str(spec.motion_state),
                },
            },
        ]
    )

    option_top = float(render_defaults["option_panel_top_px"])
    option_left = float(render_defaults["option_cell_left_px"])
    option_width = float(render_defaults["option_cell_width_px"])
    option_height = float(render_defaults["option_cell_height_px"])
    option_gap_x = float(render_defaults["option_cell_gap_x_px"])
    option_gap_y = float(render_defaults["option_cell_gap_y_px"])
    option_cards = draw_lettered_option_cards(
        draw,
        options=[(str(letter), STATE_LABELS[str(spec.option_map[str(letter)])]) for letter in OPTION_LETTERS],
        option_left=option_left,
        option_top=option_top,
        card_width=option_width,
        card_height=option_height,
        card_gap_x=option_gap_x,
        card_gap_y=option_gap_y,
        columns=2,
        option_font=option_font,
        letter_font=option_font,
        text_rgb=label_rgb,
        card_fill_rgb=tuple(int(v) for v in style.panel_alt_fill_rgb),
        card_outline_rgb=tuple(int(v) for v in style.panel_border_rgb),
        label_fill_rgb=tuple(int(v) for v in style.label_fill_rgb),
        label_outline_rgb=tuple(int(v) for v in style.label_border_rgb),
        label_text_rgb=tuple(int(v) for v in style.label_rgb),
        label_stroke_width_px=int(render_defaults["label_stroke_width_px"]),
        text_stroke_width_px=1,
        panel_fill_rgb=tuple(int(v) for v in style.panel_fill_rgb),
        panel_outline_rgb=tuple(int(v) for v in style.panel_border_rgb),
        panel_padding_px=20.0,
        panel_radius_px=16.0,
        panel_outline_width_px=3,
    )
    option_bboxes = option_cards.option_bboxes
    option_letter_bboxes = option_cards.option_letter_bboxes
    option_text_bboxes = option_cards.option_text_bboxes
    for letter in OPTION_LETTERS:
        label = STATE_LABELS[str(spec.option_map[str(letter)])]
        option_bbox = option_bboxes[str(letter)]
        scene_entities.append(
            {
                "entity_id": f"option_{str(letter)}",
                "entity_type": "motion_state_option",
                "bbox_px": list(option_bbox),
                "meta": {
                    "option_letter": str(letter),
                    "motion_state": str(spec.option_map[str(letter)]),
                    "option_text": str(label),
                    "is_correct": str(letter) == str(spec.correct_option_letter),
                },
            }
        )

    annotation_bbox_map = {
        "query_region": list(query_region_bbox),
        "curve_segment": list(curve_segment_bbox),
    }
    render_map = {
        "plot_bbox_px": [round(plot_left, 3), round(plot_top, 3), round(plot_right, 3), round(plot_bottom, 3)],
        "graph_kind": str(spec.graph_kind),
        "query_id": str(spec.query_id),
        "motion_state": str(spec.motion_state),
        "correct_option_letter": str(spec.correct_option_letter),
        "option_map": dict(spec.option_map),
        "option_text_map": {str(letter): STATE_LABELS[str(state)] for letter, state in spec.option_map.items()},
        "option_bboxes_px": {str(letter): list(bbox) for letter, bbox in option_bboxes.items()},
        "option_letter_bboxes_px": {str(letter): list(bbox) for letter, bbox in option_letter_bboxes.items()},
        "option_text_bboxes_px": {str(letter): list(bbox) for letter, bbox in option_text_bboxes.items()},
        "t_values": [int(value) for value in spec.t_values],
        "y_values": [int(value) for value in spec.y_values],
        "points_px": [[round(float(x), 3), round(float(y), 3)] for x, y in points],
        "query_segment_index": int(spec.query_segment_index),
        "query_region_bbox_px": list(query_region_bbox),
        "curve_segment_bbox_px": list(curve_segment_bbox),
        "annotation_keyed_bboxes_px": dict(annotation_bbox_map),
    }
    return _RenderedScene(
        image=image,
        annotation_bbox_map={str(key): list(value) for key, value in annotation_bbox_map.items()},
        scene_entities=[dict(entity) for entity in scene_entities],
        render_map=dict(render_map),
    )


def _resolve_layout_placement(
    *,
    render_defaults: Mapping[str, Any],
    params: Mapping[str, Any],
    instance_seed: int,
    canvas_width: int,
    canvas_height: int,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    content_left = 48.0
    content_top = 40.0
    content_right = max(
        float(render_defaults["plot_left_px"]) + float(render_defaults["plot_width_px"]) + 80.0,
        float(render_defaults["option_cell_left_px"])
        + (float(render_defaults["option_cell_width_px"]) * 2.0)
        + float(render_defaults["option_cell_gap_x_px"])
        + 22.0,
    )
    content_bottom = (
        float(render_defaults["option_panel_top_px"])
        + (float(render_defaults["option_cell_height_px"]) * 2.0)
        + float(render_defaults["option_cell_gap_y_px"])
        + 20.0
    )
    base_bbox = [round(content_left, 3), round(content_top, 3), round(content_right, 3), round(content_bottom, 3)]
    jitter = resolve_layout_jitter(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace=f"{FAMILY_ID}.layout",
    )
    min_margin = int(jitter.get("min_margin_px", 18))
    requested_dx = int(jitter.get("requested_dx_px", 0))
    requested_dy = int(jitter.get("requested_dy_px", 0))
    min_dx = int(math.ceil(float(min_margin) - float(content_left)))
    max_dx = int(math.floor(float(canvas_width) - float(min_margin) - float(content_right)))
    min_dy = int(math.ceil(float(min_margin) - float(content_top)))
    max_dy = int(math.floor(float(canvas_height) - float(min_margin) - float(content_bottom)))
    if int(min_dx) > int(max_dx):
        min_dx = 0
        max_dx = 0
    if int(min_dy) > int(max_dy):
        min_dy = 0
        max_dy = 0
    if not bool(jitter.get("enabled", False)):
        requested_dx = 0
        requested_dy = 0
    dx = max(int(min_dx), min(int(max_dx), int(requested_dx)))
    dy = max(int(min_dy), min(int(max_dy), int(requested_dy)))

    adjusted = dict(render_defaults)
    for key in ("plot_left_px", "option_cell_left_px"):
        adjusted[key] = int(adjusted[key]) + int(dx)
    for key in ("plot_top_px", "option_panel_top_px"):
        adjusted[key] = int(adjusted[key]) + int(dy)
    final_bbox = [
        round(float(content_left) + float(dx), 3),
        round(float(content_top) + float(dy), 3),
        round(float(content_right) + float(dx), 3),
        round(float(content_bottom) + float(dy), 3),
    ]
    placement = dict(jitter)
    placement.update(
        {
            "mode": "whole_motion_graph_offset",
            "content_bbox_px": base_bbox,
            "final_content_bbox_px": final_bbox,
            "canvas_size_px": [int(canvas_width), int(canvas_height)],
            "available_offset_x_px": [int(min_dx), int(max_dx)],
            "available_offset_y_px": [int(min_dy), int(max_dy)],
            "sampled_offset_px": [int(requested_dx), int(requested_dy)],
            "final_offset_px": [int(dx), int(dy)],
            "dx_px": int(dx),
            "dy_px": int(dy),
        }
    )
    return adjusted, placement


def _resolve_interval_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _IntervalAxes:
    rng = spawn_rng(int(instance_seed), f"{INTERVAL_FAMILY_ID}.axes")
    scene_variant, scene_probs, query_id, query_probs = resolve_compatible_scene_query_ids(
        rng,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_INTERVAL_GEN_DEFAULTS,
        supported_scene_variants=SUPPORTED_SCENE_VARIANTS,
        supported_query_ids=INTERVAL_QUERY_IDS,
        compatibility=INTERVAL_COMPATIBILITY,
        scene_sampling_namespace=f"{INTERVAL_FAMILY_ID}.scene_variant",
        query_sampling_namespace=f"{INTERVAL_FAMILY_ID}.query_id",
    )
    return _IntervalAxes(
        scene_variant=str(scene_variant),
        query_id=str(query_id),
        scene_variant_probabilities={str(key): float(value) for key, value in scene_probs.items()},
        query_id_probabilities={str(key): float(value) for key, value in query_probs.items()},
    )


def _resolve_interval_render_defaults(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Dict[str, int]:
    defaults = {
        key: resolve_render_int(
            params,
            _INTERVAL_RENDER_DEFAULTS,
            key,
            int(getattr(_DEFAULTS, key)),
            instance_seed=int(instance_seed),
            namespace=INTERVAL_FAMILY_ID,
        )
        for key in (
            "plot_left_px",
            "plot_top_px",
            "plot_width_px",
            "plot_height_px",
            "axis_width_px",
            "curve_width_px",
            "grid_line_width_px",
            "bold_grid_line_width_px",
            "label_font_size_px",
            "tick_font_size_px",
            "option_font_size_px",
            "title_font_size_px",
            "label_stroke_width_px",
            "point_radius_px",
            "y_min",
            "y_max",
            "t_min",
            "t_max",
        )
    }
    # These keys are not semantically option-related for this task; they are
    # reused as generic label sizing defaults from the motion graph renderer.
    defaults["option_panel_top_px"] = int(group_default(_INTERVAL_RENDER_DEFAULTS, "option_panel_top_px", _DEFAULTS.option_panel_top_px))
    defaults["option_cell_left_px"] = int(group_default(_INTERVAL_RENDER_DEFAULTS, "option_cell_left_px", _DEFAULTS.option_cell_left_px))
    defaults["option_cell_width_px"] = int(group_default(_INTERVAL_RENDER_DEFAULTS, "option_cell_width_px", _DEFAULTS.option_cell_width_px))
    defaults["option_cell_height_px"] = int(group_default(_INTERVAL_RENDER_DEFAULTS, "option_cell_height_px", _DEFAULTS.option_cell_height_px))
    return defaults


def _resolve_interval_layout_placement(
    *,
    render_defaults: Mapping[str, Any],
    params: Mapping[str, Any],
    instance_seed: int,
    canvas_width: int,
    canvas_height: int,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    content_left = 48.0
    content_top = 40.0
    content_right = float(render_defaults["plot_left_px"]) + float(render_defaults["plot_width_px"]) + 86.0
    content_bottom = float(render_defaults["plot_top_px"]) + float(render_defaults["plot_height_px"]) + 72.0
    base_bbox = [round(content_left, 3), round(content_top, 3), round(content_right, 3), round(content_bottom, 3)]
    jitter = resolve_layout_jitter(
        params,
        _INTERVAL_RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace=f"{INTERVAL_FAMILY_ID}.layout",
    )
    min_margin = int(jitter.get("min_margin_px", 18))
    requested_dx = int(jitter.get("requested_dx_px", 0))
    requested_dy = int(jitter.get("requested_dy_px", 0))
    min_dx = int(math.ceil(float(min_margin) - float(content_left)))
    max_dx = int(math.floor(float(canvas_width) - float(min_margin) - float(content_right)))
    min_dy = int(math.ceil(float(min_margin) - float(content_top)))
    max_dy = int(math.floor(float(canvas_height) - float(min_margin) - float(content_bottom)))
    if int(min_dx) > int(max_dx):
        min_dx = 0
        max_dx = 0
    if int(min_dy) > int(max_dy):
        min_dy = 0
        max_dy = 0
    if not bool(jitter.get("enabled", False)):
        requested_dx = 0
        requested_dy = 0
    dx = max(int(min_dx), min(int(max_dx), int(requested_dx)))
    dy = max(int(min_dy), min(int(max_dy), int(requested_dy)))
    adjusted = dict(render_defaults)
    adjusted["plot_left_px"] = int(adjusted["plot_left_px"]) + int(dx)
    adjusted["plot_top_px"] = int(adjusted["plot_top_px"]) + int(dy)
    final_bbox = [
        round(float(content_left) + float(dx), 3),
        round(float(content_top) + float(dy), 3),
        round(float(content_right) + float(dx), 3),
        round(float(content_bottom) + float(dy), 3),
    ]
    placement = dict(jitter)
    placement.update(
        {
            "mode": "whole_motion_graph_interval_offset",
            "content_bbox_px": base_bbox,
            "final_content_bbox_px": final_bbox,
            "canvas_size_px": [int(canvas_width), int(canvas_height)],
            "available_offset_x_px": [int(min_dx), int(max_dx)],
            "available_offset_y_px": [int(min_dy), int(max_dy)],
            "sampled_offset_px": [int(requested_dx), int(requested_dy)],
            "final_offset_px": [int(dx), int(dy)],
            "dx_px": int(dx),
            "dy_px": int(dy),
        }
    )
    return adjusted, placement


def _make_interval_graph_spec(
    instance_seed: int,
    *,
    axes: _IntervalAxes,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
) -> _IntervalGraphSpec:
    rng = spawn_rng(int(instance_seed), f"{INTERVAL_FAMILY_ID}.graph_spec")
    t_min = int(params.get("t_min", render_defaults["t_min"]))
    t_max = int(params.get("t_max", render_defaults["t_max"]))
    y_min = int(params.get("y_min", render_defaults["y_min"]))
    y_max = int(params.get("y_max", render_defaults["y_max"]))
    if int(y_min) > 0:
        raise ValueError("interval displacement graph y_min must include zero velocity")
    if int(t_max) - int(t_min) < 5:
        raise ValueError("interval displacement graph needs at least six time ticks")

    explicit_t_start = params.get("t_start")
    explicit_t_end = params.get("t_end")
    if explicit_t_start is not None or explicit_t_end is not None:
        if explicit_t_start is None or explicit_t_end is None:
            raise ValueError("t_start and t_end must be provided together")
        t_start = int(explicit_t_start)
        t_end = int(explicit_t_end)
    else:
        width_support = (
            "constant_velocity_interval_width_support"
            if str(axes.query_id) == "constant_velocity_interval_displacement"
            else "constant_acceleration_interval_width_support"
        )
        interval_widths = [int(value) for value in group_default(_INTERVAL_GEN_DEFAULTS, width_support, (2, 3, 4))]
        interval_widths = [value for value in interval_widths if 1 <= value <= int(t_max) - int(t_min) - 1]
        if not interval_widths:
            raise ValueError("no feasible interval widths for motion graph interval displacement")
        dt = int(rng.choice(interval_widths))
        min_start = int(t_min) + 1
        max_start = int(t_max) - int(dt) - 1
        if min_start > max_start:
            min_start = int(t_min)
            max_start = int(t_max) - int(dt)
        t_start = int(rng.randint(min_start, max_start))
        t_end = int(t_start + dt)
    if int(t_start) < int(t_min) or int(t_end) > int(t_max) or int(t_start) >= int(t_end):
        raise ValueError("invalid marked interval bounds")
    dt = int(t_end) - int(t_start)

    explicit_v_start = params.get("v_start", params.get("velocity_value"))
    explicit_v_end = params.get("v_end", explicit_v_start if str(axes.query_id) == "constant_velocity_interval_displacement" else None)
    if explicit_v_start is not None or explicit_v_end is not None:
        if explicit_v_start is None or explicit_v_end is None:
            raise ValueError("v_start and v_end must be provided together")
        v_start = int(explicit_v_start)
        v_end = int(explicit_v_end)
    elif str(axes.query_id) == "constant_velocity_interval_displacement":
        velocity_support = [int(value) for value in group_default(_INTERVAL_GEN_DEFAULTS, "constant_velocity_support", (1, 2, 3, 4, 5, 6, 7))]
        feasible = [value for value in velocity_support if int(y_min) <= int(value) <= int(y_max)]
        if not feasible:
            raise ValueError("no feasible constant velocities")
        v_start = v_end = int(rng.choice(feasible))
    else:
        velocity_support = [int(value) for value in group_default(_INTERVAL_GEN_DEFAULTS, "acceleration_endpoint_velocity_support", (1, 2, 3, 4, 5, 6, 7, 8))]
        slope_support = [int(value) for value in group_default(_INTERVAL_GEN_DEFAULTS, "constant_acceleration_slope_support", (-2, -1, 1, 2))]
        feasible_pairs: List[Tuple[int, int]] = []
        for start in velocity_support:
            for slope in slope_support:
                end = int(start) + int(slope) * int(dt)
                if int(y_min) <= int(end) <= int(y_max) and int(end) != int(start):
                    if ((int(start) + int(end)) * int(dt)) % 2 == 0:
                        feasible_pairs.append((int(start), int(end)))
        if not feasible_pairs:
            raise ValueError("no feasible acceleration endpoint velocities")
        v_start, v_end = rng.choice(feasible_pairs)

    if not (int(y_min) <= int(v_start) <= int(y_max) and int(y_min) <= int(v_end) <= int(y_max)):
        raise ValueError("velocity endpoints out of graph bounds")
    if str(axes.query_id) == "constant_velocity_interval_displacement" and int(v_start) != int(v_end):
        raise ValueError("constant-velocity displacement requires equal endpoint velocities")
    if str(axes.query_id) == "constant_acceleration_interval_displacement" and int(v_start) == int(v_end):
        raise ValueError("constant-acceleration displacement requires a sloped velocity segment")
    if (int(v_end) - int(v_start)) % int(dt) != 0:
        raise ValueError("interval endpoint velocities must give integer tick values")
    displacement_numer = (int(v_start) + int(v_end)) * int(dt)
    if displacement_numer % 2 != 0:
        raise ValueError("interval displacement must be an integer")
    displacement = int(displacement_numer // 2)

    slope = int((int(v_end) - int(v_start)) // int(dt))
    velocity_by_t: Dict[int, int] = {
        int(t): int(v_start) + int(slope) * (int(t) - int(t_start))
        for t in range(int(t_start), int(t_end) + 1)
    }
    for t_value in range(int(t_start) - 1, int(t_min) - 1, -1):
        next_value = int(velocity_by_t[int(t_value) + 1])
        feasible_values = [value for value in range(max(int(y_min), next_value - 2), min(int(y_max), next_value + 2) + 1)]
        velocity_by_t[int(t_value)] = int(rng.choice(feasible_values))
    for t_value in range(int(t_end) + 1, int(t_max) + 1):
        prev_value = int(velocity_by_t[int(t_value) - 1])
        feasible_values = [value for value in range(max(int(y_min), prev_value - 2), min(int(y_max), prev_value + 2) + 1)]
        velocity_by_t[int(t_value)] = int(rng.choice(feasible_values))

    t_values = tuple(range(int(t_min), int(t_max) + 1))
    velocity_values = tuple(int(velocity_by_t[int(t)]) for t in t_values)
    return _IntervalGraphSpec(
        scene_variant=str(axes.scene_variant),
        query_id=str(axes.query_id),
        graph_kind="velocity_time",
        t_values=tuple(int(value) for value in t_values),
        velocity_values=tuple(int(value) for value in velocity_values),
        t_start=int(t_start),
        t_end=int(t_end),
        v_start=int(v_start),
        v_end=int(v_end),
        displacement_m=int(displacement),
        y_axis_label="v (m/s)",
        title="velocity-time graph",
    )


def _render_interval_scene(
    *,
    image: Image.Image,
    spec: _IntervalGraphSpec,
    render_defaults: Mapping[str, Any],
    font_family: str,
    style: Any,
) -> _RenderedScene:
    width, height = image.size
    plot_left = float(render_defaults["plot_left_px"])
    plot_top = float(render_defaults["plot_top_px"])
    plot_width = float(render_defaults["plot_width_px"])
    plot_height = float(render_defaults["plot_height_px"])
    plot_right = plot_left + plot_width
    plot_bottom = plot_top + plot_height
    y_min = int(render_defaults["y_min"])
    y_max = int(render_defaults["y_max"])
    t_min = int(render_defaults["t_min"])
    t_max = int(render_defaults["t_max"])

    draw = ImageDraw.Draw(image)
    title_font = load_font(int(render_defaults["title_font_size_px"]), bold=True, font_family=font_family)
    label_font = load_font(int(render_defaults["label_font_size_px"]), bold=True, font_family=font_family)
    tick_font = load_font(int(render_defaults["tick_font_size_px"]), bold=False, font_family=font_family)
    small_font = load_font(max(14, int(render_defaults["tick_font_size_px"]) - 1), bold=True, font_family=font_family)

    panel_bbox = [48, 40, width - 48, min(height - 42, int(plot_bottom + 64))]
    draw.rounded_rectangle(
        panel_bbox,
        radius=18,
        fill=tuple(int(v) for v in style.panel_fill_rgb),
        outline=tuple(int(v) for v in style.panel_border_rgb),
        width=3,
    )
    plot_fill = tuple(int(v) for v in (style.panel_alt_fill_rgb if str(spec.scene_variant) == "paper_grid" else style.panel_fill_rgb))
    draw.rounded_rectangle(
        [plot_left - 18, plot_top - 22, plot_right + 30, plot_bottom + 42],
        radius=14,
        fill=plot_fill,
        outline=tuple(int(v) for v in style.panel_border_rgb),
        width=2,
    )

    def x_px(t_value: float) -> float:
        return float(plot_left + ((float(t_value) - t_min) / max(1.0, t_max - t_min)) * plot_width)

    def y_px(y_value: float) -> float:
        return float(plot_bottom - ((float(y_value) - y_min) / max(1.0, y_max - y_min)) * plot_height)

    label_rgb = tuple(int(v) for v in style.label_rgb)
    grid_width = int(render_defaults["bold_grid_line_width_px"] if str(spec.scene_variant) == "bold_grid" else render_defaults["grid_line_width_px"])
    tick_label_bboxes: List[List[float]] = []
    for t_value in range(t_min, t_max + 1):
        x = x_px(float(t_value))
        draw.line([(x, plot_top), (x, plot_bottom)], fill=tuple(int(v) for v in style.grid_minor_rgb), width=grid_width)
        center = (x, plot_bottom + 23)
        draw_centered_text(
            draw,
            text=str(t_value),
            center=center,
            font=tick_font,
            fill=label_rgb,
            stroke_fill=resolve_text_stroke_fill(label_rgb),
            stroke_width=1,
        )
        tick_label_bboxes.append(_text_bbox(draw, str(t_value), center, tick_font, padding=4.0))
    for y_value in range(y_min, y_max + 1):
        y = y_px(float(y_value))
        line_width = int(render_defaults["bold_grid_line_width_px"] if y_value == 0 else grid_width)
        line_fill = tuple(int(v) for v in (style.axis_rgb if y_value == 0 else style.grid_minor_rgb))
        draw.line([(plot_left, y), (plot_right, y)], fill=line_fill, width=line_width)
        center = (plot_left - 28, y)
        draw_centered_text(
            draw,
            text=str(y_value),
            center=center,
            font=tick_font,
            fill=label_rgb,
            stroke_fill=resolve_text_stroke_fill(label_rgb),
            stroke_width=1,
        )
        tick_label_bboxes.append(_text_bbox(draw, str(y_value), center, tick_font, padding=4.0))

    axis_rgb = tuple(int(v) for v in style.axis_rgb)
    zero_y = y_px(0.0)
    draw.line([(plot_left, zero_y), (plot_right + 14, zero_y)], fill=axis_rgb, width=int(render_defaults["axis_width_px"]))
    draw.line([(plot_left, plot_top - 14), (plot_left, plot_bottom)], fill=axis_rgb, width=int(render_defaults["axis_width_px"]))
    draw.polygon([(plot_right + 14, zero_y), (plot_right - 5, zero_y - 9), (plot_right - 5, zero_y + 9)], fill=axis_rgb)
    draw.polygon([(plot_left, plot_top - 14), (plot_left - 9, plot_top + 5), (plot_left + 9, plot_top + 5)], fill=axis_rgb)
    x_label_center = (plot_right + 52, plot_bottom + 18)
    y_label_center = (plot_left + 8, plot_top - 42)
    draw_centered_text(draw, text="t (s)", center=x_label_center, font=label_font, fill=label_rgb, stroke_fill=resolve_text_stroke_fill(label_rgb), stroke_width=1)
    draw_centered_text(draw, text=str(spec.y_axis_label), center=y_label_center, font=label_font, fill=label_rgb, stroke_fill=resolve_text_stroke_fill(label_rgb), stroke_width=1)
    tick_label_bboxes.append(_text_bbox(draw, "t (s)", x_label_center, label_font, padding=5.0))
    tick_label_bboxes.append(_text_bbox(draw, str(spec.y_axis_label), y_label_center, label_font, padding=5.0))
    draw_centered_text(draw, text=str(spec.title), center=(width * 0.5, panel_bbox[1] + 28), font=title_font, fill=label_rgb, stroke_fill=resolve_text_stroke_fill(label_rgb), stroke_width=1)

    points = [(x_px(t), y_px(v)) for t, v in zip(spec.t_values, spec.velocity_values)]
    start_index = int(spec.t_start) - int(t_min)
    end_index = int(spec.t_end) - int(t_min)
    interval_points = points[start_index : end_index + 1]
    band_left = x_px(spec.t_start)
    band_right = x_px(spec.t_end)
    accent = tuple(int(v) for v in style.accent_rgb)

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle(
        [band_left, plot_top, band_right, plot_bottom],
        fill=(accent[0], accent[1], accent[2], 35),
        outline=(accent[0], accent[1], accent[2], 155),
        width=3,
    )
    area_polygon = [(band_left, zero_y), *interval_points, (band_right, zero_y)]
    overlay_draw.polygon(area_polygon, fill=(accent[0], accent[1], accent[2], 70))
    combined = Image.alpha_composite(image.convert("RGBA"), overlay).convert(image.mode)
    image.paste(combined)
    draw = ImageDraw.Draw(image)

    curve_rgb = tuple(int(v) for v in style.stroke_rgb)
    draw.line(points, fill=curve_rgb, width=int(render_defaults["curve_width_px"]), joint="curve")
    highlight_rgb = tuple(int(v) for v in style.accent_rgb)
    draw.line(interval_points, fill=highlight_rgb, width=int(render_defaults["curve_width_px"]) + 3, joint="curve")
    for point in points:
        radius = float(render_defaults["point_radius_px"])
        draw.ellipse([point[0] - radius, point[1] - radius, point[0] + radius, point[1] + radius], fill=curve_rgb, outline=tuple(int(v) for v in style.panel_fill_rgb), width=2)

    bracket_y = plot_top + 18.0
    draw.line([(band_left, bracket_y), (band_right, bracket_y)], fill=highlight_rgb, width=4)
    draw.line([(band_left, bracket_y - 10), (band_left, bracket_y + 10)], fill=highlight_rgb, width=4)
    draw.line([(band_right, bracket_y - 10), (band_right, bracket_y + 10)], fill=highlight_rgb, width=4)
    draw_centered_text(
        draw,
        text="marked interval",
        center=((band_left + band_right) / 2.0, bracket_y + 24.0),
        font=small_font,
        fill=highlight_rgb,
        stroke_fill=resolve_text_stroke_fill(highlight_rgb),
        stroke_width=1,
    )

    marked_interval_bbox = [
        round(float(band_left), 3),
        round(float(plot_top), 3),
        round(float(band_right), 3),
        round(float(plot_bottom), 3),
    ]
    velocity_segment_bbox = _bbox_from_points(interval_points, padding=float(render_defaults["curve_width_px"]) + 8.0)
    axis_scale_bbox = _bbox_union(
        [plot_left - 58.0, plot_top - 50.0, plot_left + 10.0, plot_bottom + 34.0],
        [plot_left - 8.0, plot_bottom - 8.0, plot_right + 64.0, plot_bottom + 40.0],
        *tick_label_bboxes,
        padding=2.0,
    )
    annotation_bbox_map = {
        "marked_interval": list(marked_interval_bbox),
        "velocity_segment": list(velocity_segment_bbox),
        "axis_scale": list(axis_scale_bbox),
    }
    scene_entities = [
        {
            "entity_id": "marked_interval",
            "entity_type": "marked_time_interval",
            "bbox_px": list(marked_interval_bbox),
            "meta": {"t_start": int(spec.t_start), "t_end": int(spec.t_end)},
        },
        {
            "entity_id": "velocity_segment",
            "entity_type": "queried_velocity_segment",
            "bbox_px": list(velocity_segment_bbox),
            "meta": {"v_start": int(spec.v_start), "v_end": int(spec.v_end)},
        },
        {
            "entity_id": "axis_scale",
            "entity_type": "axis_scale",
            "bbox_px": list(axis_scale_bbox),
            "meta": {"t_unit": "s", "velocity_unit": "m/s"},
        },
    ]
    render_map = {
        "plot_bbox_px": [round(plot_left, 3), round(plot_top, 3), round(plot_right, 3), round(plot_bottom, 3)],
        "graph_kind": str(spec.graph_kind),
        "query_id": str(spec.query_id),
        "t_values": [int(value) for value in spec.t_values],
        "velocity_values": [int(value) for value in spec.velocity_values],
        "points_px": [[round(float(x), 3), round(float(y), 3)] for x, y in points],
        "t_start": int(spec.t_start),
        "t_end": int(spec.t_end),
        "delta_t_s": int(spec.t_end) - int(spec.t_start),
        "v_start_m_s": int(spec.v_start),
        "v_end_m_s": int(spec.v_end),
        "displacement_m": int(spec.displacement_m),
        "marked_interval_bbox_px": list(marked_interval_bbox),
        "velocity_segment_bbox_px": list(velocity_segment_bbox),
        "axis_scale_bbox_px": list(axis_scale_bbox),
        "annotation_keyed_bboxes_px": dict(annotation_bbox_map),
    }
    return _RenderedScene(
        image=image,
        annotation_bbox_map={str(key): list(value) for key, value in annotation_bbox_map.items()},
        scene_entities=[dict(entity) for entity in scene_entities],
        render_map=dict(render_map),
    )


class _PhysicsMotionGraphStateChoiceTaskBase:
    """Choose the motion state represented by a marked interval on a kinematics graph."""

    task_id = ""
    domain = "physics"
    task_group = "mechanics"
    default_dataset_enabled = True
    forced_query_id = ""

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        params = dict(params or {})
        forced_query_id = str(getattr(self, "forced_query_id", "") or "")
        if forced_query_id:
            explicit_query_id = params.get("query_id")
            if explicit_query_id is not None and str(explicit_query_id) != forced_query_id:
                raise ValueError(f"{self.task_id} only supports query_id={forced_query_id!r}")
            params["query_id"] = forced_query_id
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_seed = int(instance_seed) + (attempt_index * 7919)
            try:
                axes = _resolve_axes(attempt_seed, params=params)
                spec = _make_graph_spec(attempt_seed, axes=axes, params=params)
            except Exception as exc:  # pragma: no cover - surfaced if all attempts fail.
                last_error = exc
                continue

            canvas_width = int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width)))
            canvas_height = int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height)))
            background, background_meta, diagram_style, diagram_style_meta = prepare_physics_diagram_style_and_background(
                instance_seed=attempt_seed,
                params=params,
                scene_id=SCENE_ID,
                task_group=self.task_group,
                canvas_width=int(canvas_width),
                canvas_height=int(canvas_height),
                require_grid=True,
            )
            font_family = sample_font_family(
                role="readout",
                instance_seed=attempt_seed,
                namespace=f"{FAMILY_ID}.font",
                params=params,
            )
            font_record = get_font_family_record(str(font_family))
            render_defaults = {
                key: resolve_render_int(
                    params,
                    _RENDER_DEFAULTS,
                    key,
                    int(getattr(_DEFAULTS, key)),
                    instance_seed=attempt_seed,
                    namespace=FAMILY_ID,
                )
                for key in (
                    "plot_left_px",
                    "plot_top_px",
                    "plot_width_px",
                    "plot_height_px",
                    "option_panel_top_px",
                    "option_cell_left_px",
                    "option_cell_width_px",
                    "option_cell_height_px",
                    "option_cell_gap_x_px",
                    "option_cell_gap_y_px",
                    "axis_width_px",
                    "curve_width_px",
                    "grid_line_width_px",
                    "bold_grid_line_width_px",
                    "label_font_size_px",
                    "tick_font_size_px",
                    "option_font_size_px",
                    "title_font_size_px",
                    "label_stroke_width_px",
                    "point_radius_px",
                    "y_min",
                    "y_max",
                    "t_min",
                    "t_max",
                )
            }
            render_defaults, layout_placement_meta = _resolve_layout_placement(
                render_defaults=render_defaults,
                params=params,
                instance_seed=attempt_seed,
                canvas_width=int(canvas_width),
                canvas_height=int(canvas_height),
            )
            rendered = _render_scene(
                image=background,
                spec=spec,
                render_defaults=render_defaults,
                font_family=str(font_family),
                style=diagram_style,
            )
            image, post_noise_meta = apply_post_image_noise(
                rendered.image,
                instance_seed=attempt_seed,
                params=params,
                default_config=POST_IMAGE_NOISE_DEFAULTS,
            )
            prompt_defaults = required_group_defaults(
                _PROMPT_DEFAULTS,
                (
                    "bundle_id",
                    "scene_key",
                    "task_key",
                    "json_output_contract",
                    "json_output_contract_answer_only",
                    "object_description",
                    f"answer_hint_{str(spec.query_id)}",
                    f"annotation_hint_{str(spec.query_id)}",
                ),
                context=f"prompt defaults for {self.task_id}",
            )
            answer_gt = TypedValue(type="option_letter", value=str(spec.correct_option_letter))
            annotation_gt = TypedValue(type="keyed_bbox_map", value={str(key): list(value) for key, value in rendered.annotation_bbox_map.items()})
            json_example, json_example_answer_only = build_prompt_json_examples(
                annotation_value=annotation_gt.value,
                answer_type=str(answer_gt.type),
            )
            prompt_selection = render_task_prompt_variants(
                domain=self.domain,
                task_group=self.task_group,
                bundle_id=str(prompt_defaults["bundle_id"]),
                scene_key=str(prompt_defaults["scene_key"]),
                task_key=str(prompt_defaults["task_key"]),
                query_key=str(spec.query_id),
                slots={
                    "object_description": str(prompt_defaults["object_description"]),
                    "json_output_contract": str(prompt_defaults["json_output_contract"]),
                    "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                    "answer_hint": str(prompt_defaults[f"answer_hint_{str(spec.query_id)}"]),
                    "annotation_hint": str(prompt_defaults[f"annotation_hint_{str(spec.query_id)}"]),
                    "json_example": str(json_example),
                    "json_example_answer_only": str(json_example_answer_only),
                },
                instance_seed=attempt_seed,
                answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            )
            prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
            is_velocity_sign = str(spec.query_id) == "velocity_sign_choice"
            complexity = TaskComplexity(
                complexity_score=0.50 if is_velocity_sign else 0.58,
                complexity_components={
                    "visual_scan": 0.24,
                    "graph_reasoning": 0.48 if is_velocity_sign else 0.56,
                    "ambiguity": 0.12,
                    "output_burden": 0.10,
                },
            )
            trace_payload = {
                "scene_ir": {
                    "scene_kind": f"physics_motion_graph_{str(spec.graph_kind)}",
                    "entities": [dict(entity) for entity in rendered.scene_entities],
                    "relations": {
                        "scene_variant": str(spec.scene_variant),
                        "query_id": str(spec.query_id),
                        "graph_kind": str(spec.graph_kind),
                        "motion_state": str(spec.motion_state),
                        "correct_option_letter": str(spec.correct_option_letter),
                    },
                },
                "query_spec": {
                    "query_id": str(spec.query_id),
                    "template_id": str(prompt_defaults["bundle_id"]),
                    "prompt_variant": dict(prompt_artifacts.prompt_variant),
                    "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                    "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                    "params": {
                        "scene_variant": str(spec.scene_variant),
                        "query_id": str(spec.query_id),
                        "graph_kind": str(spec.graph_kind),
                        "motion_state": str(spec.motion_state),
                        "target_answer": str(spec.correct_option_letter),
                        "answer_support": list(OPTION_LETTERS),
                    },
                },
                "render_spec": {
                    "canvas_width": int(image.size[0]),
                    "canvas_height": int(image.size[1]),
                    "font": {
                        "font_family": str(font_family),
                        "font_asset_version": font_asset_version(),
                        "font_asset": font_record.to_trace(),
                        "scope": "motion_graph_diagram",
                    },
                    "technical_diagram_style": dict(diagram_style_meta),
                    "background_style": background_meta,
                    "layout_placement": dict(layout_placement_meta),
                    "post_image_noise": post_noise_meta,
                },
                "render_map": dict(rendered.render_map),
                "execution_trace": {
                    "query_id": str(spec.query_id),
                    "graph_kind": str(spec.graph_kind),
                    "motion_state": str(spec.motion_state),
                    "option_map": dict(spec.option_map),
                    "correct_option_letter": str(spec.correct_option_letter),
                    "target_segment": {
                        "index": int(spec.query_segment_index),
                        "t_start": int(spec.t_values[spec.query_segment_index]),
                        "t_end": int(spec.t_values[spec.query_segment_index + 1]),
                        "y_start": int(spec.y_values[spec.query_segment_index]),
                        "y_end": int(spec.y_values[spec.query_segment_index + 1]),
                    },
                },
                "sampling": {
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "motion_state_probabilities": dict(axes.motion_state_probabilities),
                    "correct_option_letter_probabilities": dict(axes.correct_option_letter_probabilities),
                },
                "witness_symbolic": {
                    "type": "keyed_bbox_map",
                    "keys": sorted(annotation_gt.value.keys()),
                },
                "projected_annotation": {
                    "type": "keyed_bbox_map",
                    "keyed_bbox_map": dict(annotation_gt.value),
                    "pixel_keyed_bbox_map": dict(annotation_gt.value),
                },
                "background": background_meta,
                "post_image_noise": post_noise_meta,
            }
            return TaskOutput(
                prompt=str(prompt_artifacts.prompt),
                prompt_variants=dict(prompt_artifacts.prompt_variants),
                answer_gt=answer_gt,
                annotation_gt=annotation_gt,
                image=image,
                image_id="img0",
                trace_payload=trace_payload,
                complexity=complexity,
                task_versions=default_task_versions(),
                scene_id=SCENE_ID,
                query_id=str(spec.query_id),
            )
        raise RuntimeError(f"failed to generate motion graph instance after {max_attempts} attempts: {last_error}")


@register_task
class PhysicsMotionGraphVelocitySignChoiceTask(_PhysicsMotionGraphStateChoiceTaskBase):
    """Choose whether the marked position-time segment moves right, left, or stays stationary."""

    task_id = "task_physics__motion_graph__velocity_sign_choice"
    forced_query_id = "velocity_sign_choice"


@register_task
class PhysicsMotionGraphSpeedChangeStateChoiceTask(_PhysicsMotionGraphStateChoiceTaskBase):
    """Choose whether the marked velocity-time segment speeds up, slows down, or keeps constant speed."""

    task_id = "task_physics__motion_graph__speed_change_state_choice"
    forced_query_id = "speed_change_state_choice"


@register_task
class PhysicsMotionGraphIntervalDisplacementValueTask:
    """Compute displacement over a marked interval of a velocity-time graph."""

    task_id = INTERVAL_TASK_ID
    domain = "physics"
    task_group = "mechanics"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        params = dict(params or {})
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_seed = int(instance_seed) + (attempt_index * 7919)
            try:
                axes = _resolve_interval_axes(attempt_seed, params=params)
                canvas_width = int(params.get("canvas_width", group_default(_INTERVAL_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width)))
                canvas_height = int(params.get("canvas_height", group_default(_INTERVAL_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height)))
                render_defaults = _resolve_interval_render_defaults(params=params, instance_seed=attempt_seed)
                render_defaults, layout_placement_meta = _resolve_interval_layout_placement(
                    render_defaults=render_defaults,
                    params=params,
                    instance_seed=attempt_seed,
                    canvas_width=int(canvas_width),
                    canvas_height=int(canvas_height),
                )
                spec = _make_interval_graph_spec(
                    attempt_seed,
                    axes=axes,
                    params=params,
                    render_defaults=render_defaults,
                )
            except Exception as exc:  # pragma: no cover - surfaced if all attempts fail.
                last_error = exc
                continue

            background, background_meta, diagram_style, diagram_style_meta = prepare_physics_diagram_style_and_background(
                instance_seed=attempt_seed,
                params=params,
                scene_id=SCENE_ID,
                task_group=self.task_group,
                canvas_width=int(canvas_width),
                canvas_height=int(canvas_height),
                require_grid=True,
            )
            font_family = sample_font_family(
                role="readout",
                instance_seed=attempt_seed,
                namespace=f"{INTERVAL_FAMILY_ID}.font",
                params=params,
            )
            font_record = get_font_family_record(str(font_family))
            rendered = _render_interval_scene(
                image=background,
                spec=spec,
                render_defaults=render_defaults,
                font_family=str(font_family),
                style=diagram_style,
            )
            image, post_noise_meta = apply_post_image_noise(
                rendered.image,
                instance_seed=attempt_seed,
                params=params,
                default_config=POST_IMAGE_NOISE_DEFAULTS,
            )
            prompt_defaults = required_group_defaults(
                _INTERVAL_PROMPT_DEFAULTS,
                (
                    "bundle_id",
                    "scene_key",
                    "task_key",
                    "json_output_contract",
                    "json_output_contract_answer_only",
                    "object_description",
                    f"answer_hint_{str(spec.query_id)}",
                    f"annotation_hint_{str(spec.query_id)}",
                ),
                context=f"prompt defaults for {self.task_id}",
            )
            answer_gt = TypedValue(type="integer", value=int(spec.displacement_m))
            annotation_gt = TypedValue(
                type="keyed_bbox_map",
                value={str(key): list(value) for key, value in rendered.annotation_bbox_map.items()},
            )
            json_example, json_example_answer_only = build_prompt_json_examples(
                annotation_value=annotation_gt.value,
                answer_type=str(answer_gt.type),
            )
            prompt_selection = render_task_prompt_variants(
                domain=self.domain,
                task_group=self.task_group,
                bundle_id=str(prompt_defaults["bundle_id"]),
                scene_key=str(prompt_defaults["scene_key"]),
                task_key=str(prompt_defaults["task_key"]),
                query_key=str(spec.query_id),
                slots={
                    "object_description": str(prompt_defaults["object_description"]),
                    "json_output_contract": str(prompt_defaults["json_output_contract"]),
                    "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                    "answer_hint": str(prompt_defaults[f"answer_hint_{str(spec.query_id)}"]),
                    "annotation_hint": str(prompt_defaults[f"annotation_hint_{str(spec.query_id)}"]),
                    "json_example": str(json_example),
                    "json_example_answer_only": str(json_example_answer_only),
                },
                instance_seed=attempt_seed,
                answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            )
            prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
            is_accelerating = str(spec.query_id) == "constant_acceleration_interval_displacement"
            complexity = TaskComplexity(
                complexity_score=0.58 if not is_accelerating else 0.64,
                complexity_components={
                    "visual_scan": 0.26,
                    "graph_reasoning": 0.48 if not is_accelerating else 0.54,
                    "arithmetic": 0.18 if not is_accelerating else 0.24,
                    "ambiguity": 0.08,
                    "output_burden": 0.08,
                },
            )
            trace_payload = {
                "scene_ir": {
                    "scene_kind": "physics_motion_graph_velocity_time_interval_displacement",
                    "entities": [dict(entity) for entity in rendered.scene_entities],
                    "relations": {
                        "scene_variant": str(spec.scene_variant),
                        "query_id": str(spec.query_id),
                        "graph_kind": str(spec.graph_kind),
                        "displacement_m": int(spec.displacement_m),
                    },
                },
                "query_spec": {
                    "query_id": str(spec.query_id),
                    "template_id": str(prompt_defaults["bundle_id"]),
                    "prompt_variant": dict(prompt_artifacts.prompt_variant),
                    "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                    "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                    "params": {
                        "scene_variant": str(spec.scene_variant),
                        "query_id": str(spec.query_id),
                        "graph_kind": str(spec.graph_kind),
                        "target_answer": int(spec.displacement_m),
                    },
                },
                "render_spec": {
                    "canvas_width": int(image.size[0]),
                    "canvas_height": int(image.size[1]),
                    "font": {
                        "font_family": str(font_family),
                        "font_asset_version": font_asset_version(),
                        "font_asset": font_record.to_trace(),
                        "scope": "motion_graph_interval_diagram",
                    },
                    "technical_diagram_style": dict(diagram_style_meta),
                    "background_style": background_meta,
                    "layout_placement": dict(layout_placement_meta),
                    "post_image_noise": post_noise_meta,
                },
                "render_map": dict(rendered.render_map),
                "execution_trace": {
                    "query_id": str(spec.query_id),
                    "graph_kind": str(spec.graph_kind),
                    "t_start_s": int(spec.t_start),
                    "t_end_s": int(spec.t_end),
                    "delta_t_s": int(spec.t_end) - int(spec.t_start),
                    "v_start_m_s": int(spec.v_start),
                    "v_end_m_s": int(spec.v_end),
                    "displacement_m": int(spec.displacement_m),
                    "t_values": [int(value) for value in spec.t_values],
                    "velocity_values_m_s": [int(value) for value in spec.velocity_values],
                    "area_formula": "v * delta_t" if not is_accelerating else "((v_start + v_end) / 2) * delta_t",
                },
                "sampling": {
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                },
                "witness_symbolic": {
                    "type": "keyed_bbox_map",
                    "keys": sorted(annotation_gt.value.keys()),
                },
                "projected_annotation": {
                    "type": "keyed_bbox_map",
                    "keyed_bbox_map": dict(annotation_gt.value),
                    "pixel_keyed_bbox_map": dict(annotation_gt.value),
                },
                "background": background_meta,
                "post_image_noise": post_noise_meta,
            }
            return TaskOutput(
                prompt=str(prompt_artifacts.prompt),
                prompt_variants=dict(prompt_artifacts.prompt_variants),
                answer_gt=answer_gt,
                annotation_gt=annotation_gt,
                image=image,
                image_id="img0",
                trace_payload=trace_payload,
                complexity=complexity,
                task_versions=default_task_versions(),
                scene_id=SCENE_ID,
                query_id=str(spec.query_id),
            )
        raise RuntimeError(f"failed to generate motion graph interval instance after {max_attempts} attempts: {last_error}")
