"""Physics mechanics task for inferring an incoming collision path from aftermath."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.bbox_projection import bbox_union_many as _bbox_union
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.drawing import draw_arrow, draw_centered_text, draw_rounded_rect
from ...shared.font_assets import font_asset_version, get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import resolve_prompt_json_examples
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.render_variation import resolve_layout_jitter, resolve_render_int
from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.diagram_style import prepare_physics_diagram_style_and_background
from ..shared.label_tags import draw_text_tag
from ..shared.style import SUPPORTED_PHYSICS_COLOR_NAMES, build_physics_collision_theme
from ..shared.visual_defaults import load_physics_noise_defaults


TASK_NAMESPACE = "physics_mechanics_collision_aftermath"
TASK_ID = "task_physics__collision__incoming_path_cause_choice"
SCENE_ID = "collision"
QUERY_ID = "incoming_path_cause_choice"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (QUERY_ID,)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "aftermath_table",
    "aftermath_gridded_table",
    "aftermath_compact_table",
)
OPTION_LETTERS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")
DIRECTION_NAMES: Tuple[str, ...] = (
    "east",
    "northeast",
    "north",
    "northwest",
    "west",
    "southwest",
    "south",
    "southeast",
)
DIRECTION_ANGLE_DEGREES: Dict[str, float] = {
    "east": 0.0,
    "northeast": 45.0,
    "north": 90.0,
    "northwest": 135.0,
    "west": 180.0,
    "southwest": 225.0,
    "south": 270.0,
    "southeast": 315.0,
}

_TASK_GROUP_DEFAULTS = get_scene_defaults("physics", "mechanics")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_NAMESPACE,
)
POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(scene_id="mechanics", apply_prob=0.5)


@dataclass(frozen=True)
class _TaskDefaults:
    canvas_width: int = 1180
    canvas_height: int = 760
    table_left_px: int = 52
    table_top_px: int = 52
    table_width_px: int = 1076
    table_height_px: int = 640
    table_corner_radius_px: int = 22
    impact_center_x_px: int = 590
    impact_center_y_px: int = 380
    compact_impact_center_y_px: int = 364
    puck_radius_px: int = 38
    impact_radius_px: int = 16
    target_distance_px: int = 156
    trail_start_gap_px: int = 18
    incoming_arrow_inner_gap_px: int = 58
    incoming_arrow_length_px: int = 210
    candidate_label_offset_px: int = 38
    motion_arrow_width_px: int = 8
    candidate_arrow_width_px: int = 6
    arrow_head_length_px: int = 23
    arrow_head_width_px: int = 19
    candidate_arrow_head_length_px: int = 20
    candidate_arrow_head_width_px: int = 17
    title_font_size_px: int = 27
    label_font_size_px: int = 23
    puck_font_size_px: int = 23
    label_stroke_width_px: int = 2
    grid_spacing_px: int = 44


@dataclass(frozen=True)
class _ResolvedAxes:
    scene_variant: str
    query_id: str
    final_motion_direction: str
    correct_option_letter: str
    accent_color_name: str
    scene_variant_probabilities: Dict[str, float]
    query_id_probabilities: Dict[str, float]
    final_motion_direction_probabilities: Dict[str, float]
    correct_option_letter_probabilities: Dict[str, float]
    accent_color_name_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _CollisionAftermathSpec:
    scene_variant: str
    query_id: str
    final_motion_direction: str
    correct_option_letter: str
    option_directions: Dict[str, str]
    option_angles_degrees: Dict[str, float]


@dataclass(frozen=True)
class _RenderedScene:
    image: Image.Image
    annotation_bbox_map: Dict[str, List[float]]
    scene_entities: List[Dict[str, Any]]
    render_map: Dict[str, Any]


_DEFAULTS = _TaskDefaults()


def _bbox(values: Sequence[float]) -> List[float]:
    return [round(float(value), 3) for value in values]


def _clip_bbox(bbox: Sequence[float], *, width: int, height: int) -> List[float]:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    return _bbox(
        (
            max(0.0, min(float(width), min(x0, x1))),
            max(0.0, min(float(height), min(y0, y1))),
            max(0.0, min(float(width), max(x0, x1))),
            max(0.0, min(float(height), max(y0, y1))),
        )
    )


def _direction_unit(direction: str) -> Tuple[float, float]:
    angle = math.radians(float(DIRECTION_ANGLE_DEGREES[str(direction)]))
    return (float(math.cos(angle)), float(-math.sin(angle)))


def _arrow_bbox(start: Tuple[float, float], end: Tuple[float, float], *, padding_px: float) -> List[float]:
    return _bbox(
        (
            min(float(start[0]), float(end[0])) - float(padding_px),
            min(float(start[1]), float(end[1])) - float(padding_px),
            max(float(start[0]), float(end[0])) + float(padding_px),
            max(float(start[1]), float(end[1])) + float(padding_px),
        )
    )


def _draw_grid(
    draw: ImageDraw.ImageDraw,
    *,
    table_bbox: Sequence[float],
    spacing_px: int,
    fill_rgb: Tuple[int, int, int],
) -> None:
    left, top, right, bottom = [float(value) for value in table_bbox]
    spacing = max(18.0, float(spacing_px))
    x = left + spacing
    while x < right - 1:
        draw.line((x, top, x, bottom), fill=fill_rgb, width=1)
        x += spacing
    y = top + spacing
    while y < bottom - 1:
        draw.line((left, y, right, y), fill=fill_rgb, width=1)
        y += spacing


def _draw_puck(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    radius_px: float,
    label: str,
    fill_rgb: Tuple[int, int, int],
    outline_rgb: Tuple[int, int, int],
    text_rgb: Tuple[int, int, int],
    font: Any,
) -> List[float]:
    cx, cy = float(center[0]), float(center[1])
    radius = float(radius_px)
    bbox = _bbox((cx - radius, cy - radius, cx + radius, cy + radius))
    draw.ellipse(tuple(float(value) for value in bbox), fill=fill_rgb, outline=outline_rgb, width=4)
    draw.ellipse((cx - radius * 0.42, cy - radius * 0.42, cx + radius * 0.42, cy + radius * 0.42), outline=outline_rgb, width=2)
    draw_centered_text(
        draw,
        text=str(label),
        center=(cx, cy),
        font=font,
        fill=text_rgb,
        stroke_fill=resolve_text_stroke_fill(text_rgb),
        stroke_width=1,
    )
    return bbox


def _resolve_scene_variant(instance_seed: int, *, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    selected, probabilities = resolve_variant(
        spawn_rng(int(instance_seed), f"{TASK_NAMESPACE}.scene_variant"),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_SCENE_VARIANTS,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=SUPPORTED_SCENE_VARIANTS,
        balance_flag_key="balanced_scene_variant_sampling",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        sampling_namespace=f"{TASK_NAMESPACE}.scene_variant",
    )
    return str(selected), {str(key): float(value) for key, value in probabilities.items()}


def _resolve_query_id(instance_seed: int, *, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    selected, probabilities = resolve_variant(
        spawn_rng(int(instance_seed), f"{TASK_NAMESPACE}.query_id"),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_QUERY_IDS,
        explicit_key="query_id",
        weights_key="query_id_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=SUPPORTED_QUERY_IDS,
        balance_flag_key="balanced_query_id_sampling",
        explicit_key="query_id",
        weights_key="query_id_weights",
        sampling_namespace=f"{TASK_NAMESPACE}.query_id",
    )
    return str(selected), {str(key): float(value) for key, value in probabilities.items()}


def _resolve_final_motion_direction(instance_seed: int, *, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    direction_params = dict(params)
    if params.get("aftermath_direction") is not None and params.get("final_motion_direction") is None:
        direction_params["final_motion_direction"] = str(params["aftermath_direction"])
    selected, probabilities = resolve_variant(
        spawn_rng(int(instance_seed), f"{TASK_NAMESPACE}.final_motion_direction"),
        params=direction_params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=DIRECTION_NAMES,
        explicit_key="final_motion_direction",
        weights_key="final_motion_direction_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=direction_params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=DIRECTION_NAMES,
        balance_flag_key="balanced_final_motion_direction_sampling",
        explicit_key="final_motion_direction",
        weights_key="final_motion_direction_weights",
        sampling_namespace=f"{TASK_NAMESPACE}.final_motion_direction",
    )
    return str(selected), {str(key): float(value) for key, value in probabilities.items()}


def _resolve_correct_option_letter(instance_seed: int, *, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    answer_params = dict(params)
    if params.get("target_answer") is not None and params.get("correct_option_letter") is None:
        answer_params["correct_option_letter"] = str(params["target_answer"])
    selected, probabilities = resolve_variant(
        spawn_rng(int(instance_seed), f"{TASK_NAMESPACE}.correct_option_letter"),
        params=answer_params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=OPTION_LETTERS,
        explicit_key="correct_option_letter",
        weights_key="correct_option_letter_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=answer_params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=OPTION_LETTERS,
        balance_flag_key="balanced_correct_option_letter_sampling",
        explicit_key="correct_option_letter",
        weights_key="correct_option_letter_weights",
        sampling_namespace=f"{TASK_NAMESPACE}.correct_option_letter",
    )
    return str(selected), {str(key): float(value) for key, value in probabilities.items()}


def _resolve_accent_color(instance_seed: int, *, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    selected, probabilities = resolve_variant(
        spawn_rng(int(instance_seed), f"{TASK_NAMESPACE}.accent_color_name"),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_PHYSICS_COLOR_NAMES,
        explicit_key="accent_color_name",
        weights_key="accent_color_name_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=SUPPORTED_PHYSICS_COLOR_NAMES,
        balance_flag_key="balanced_accent_color_name_sampling",
        explicit_key="accent_color_name",
        weights_key="accent_color_name_weights",
        sampling_namespace=f"{TASK_NAMESPACE}.accent_color_name",
    )
    return str(selected), {str(key): float(value) for key, value in probabilities.items()}


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    scene_variant, scene_probs = _resolve_scene_variant(int(instance_seed), params=params)
    query_id, query_probs = _resolve_query_id(int(instance_seed), params=params)
    direction, direction_probs = _resolve_final_motion_direction(int(instance_seed), params=params)
    correct_letter, letter_probs = _resolve_correct_option_letter(int(instance_seed), params=params)
    accent_color, accent_probs = _resolve_accent_color(int(instance_seed), params=params)
    return _ResolvedAxes(
        scene_variant=str(scene_variant),
        query_id=str(query_id),
        final_motion_direction=str(direction),
        correct_option_letter=str(correct_letter),
        accent_color_name=str(accent_color),
        scene_variant_probabilities=dict(scene_probs),
        query_id_probabilities=dict(query_probs),
        final_motion_direction_probabilities=dict(direction_probs),
        correct_option_letter_probabilities=dict(letter_probs),
        accent_color_name_probabilities=dict(accent_probs),
    )


def _option_directions(
    *,
    instance_seed: int,
    final_motion_direction: str,
    correct_option_letter: str,
) -> Dict[str, str]:
    correct_index = DIRECTION_NAMES.index(str(final_motion_direction))
    distractors = [
        direction
        for index, direction in enumerate(DIRECTION_NAMES)
        if index != correct_index and (abs(index - correct_index) % len(DIRECTION_NAMES)) not in {1, len(DIRECTION_NAMES) - 1}
    ]
    if len(distractors) != len(OPTION_LETTERS) - 1:
        raise ValueError("collision aftermath distractor construction requires exactly five distractors")
    rng = spawn_rng(int(instance_seed), f"{TASK_NAMESPACE}.option_directions")
    shuffled = list(distractors)
    rng.shuffle(shuffled)
    out: Dict[str, str] = {str(correct_option_letter): str(final_motion_direction)}
    other_letters = [letter for letter in OPTION_LETTERS if str(letter) != str(correct_option_letter)]
    for letter, direction in zip(other_letters, shuffled):
        out[str(letter)] = str(direction)
    return {letter: out[letter] for letter in OPTION_LETTERS}


def _make_spec(instance_seed: int, axes: _ResolvedAxes) -> _CollisionAftermathSpec:
    option_directions = _option_directions(
        instance_seed=int(instance_seed),
        final_motion_direction=str(axes.final_motion_direction),
        correct_option_letter=str(axes.correct_option_letter),
    )
    return _CollisionAftermathSpec(
        scene_variant=str(axes.scene_variant),
        query_id=str(axes.query_id),
        final_motion_direction=str(axes.final_motion_direction),
        correct_option_letter=str(axes.correct_option_letter),
        option_directions=dict(option_directions),
        option_angles_degrees={
            str(letter): float(DIRECTION_ANGLE_DEGREES[str(direction)])
            for letter, direction in option_directions.items()
        },
    )


def _resolve_render_defaults(params: Mapping[str, Any], *, instance_seed: int) -> Dict[str, int]:
    keys = (
        "table_left_px",
        "table_top_px",
        "table_width_px",
        "table_height_px",
        "table_corner_radius_px",
        "impact_center_x_px",
        "impact_center_y_px",
        "compact_impact_center_y_px",
        "puck_radius_px",
        "impact_radius_px",
        "target_distance_px",
        "trail_start_gap_px",
        "incoming_arrow_inner_gap_px",
        "incoming_arrow_length_px",
        "candidate_label_offset_px",
        "motion_arrow_width_px",
        "candidate_arrow_width_px",
        "arrow_head_length_px",
        "arrow_head_width_px",
        "candidate_arrow_head_length_px",
        "candidate_arrow_head_width_px",
        "title_font_size_px",
        "label_font_size_px",
        "puck_font_size_px",
        "label_stroke_width_px",
        "grid_spacing_px",
    )
    return {
        key: resolve_render_int(
            params,
            _RENDER_DEFAULTS,
            key,
            int(getattr(_DEFAULTS, key)),
            instance_seed=int(instance_seed),
            namespace=TASK_NAMESPACE,
        )
        for key in keys
    }


def _resolve_layout_placement(
    *,
    render_defaults: Mapping[str, Any],
    params: Mapping[str, Any],
    instance_seed: int,
    canvas_width: int,
    canvas_height: int,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    content_bbox = [
        float(render_defaults["table_left_px"]),
        float(render_defaults["table_top_px"]),
        float(render_defaults["table_left_px"]) + float(render_defaults["table_width_px"]),
        float(render_defaults["table_top_px"]) + float(render_defaults["table_height_px"]),
    ]
    base_bbox = [round(float(value), 3) for value in content_bbox]
    jitter = resolve_layout_jitter(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_NAMESPACE}.layout",
    )
    min_margin = int(jitter.get("min_margin_px", 24))
    requested_dx = int(jitter.get("requested_dx_px", 0))
    requested_dy = int(jitter.get("requested_dy_px", 0))
    min_dx = int(math.ceil(float(min_margin) - float(content_bbox[0])))
    max_dx = int(math.floor(float(canvas_width) - float(min_margin) - float(content_bbox[2])))
    min_dy = int(math.ceil(float(min_margin) - float(content_bbox[1])))
    max_dy = int(math.floor(float(canvas_height) - float(min_margin) - float(content_bbox[3])))
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
    for key in ("table_left_px", "impact_center_x_px"):
        adjusted[key] = int(round(float(adjusted[key]) + float(dx)))
    for key in ("table_top_px", "impact_center_y_px", "compact_impact_center_y_px"):
        adjusted[key] = int(round(float(adjusted[key]) + float(dy)))
    final_bbox = [
        round(float(content_bbox[0]) + float(dx), 3),
        round(float(content_bbox[1]) + float(dy), 3),
        round(float(content_bbox[2]) + float(dx), 3),
        round(float(content_bbox[3]) + float(dy), 3),
    ]
    placement = dict(jitter)
    placement.update(
        {
            "mode": "whole_collision_aftermath_offset",
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


def _render_scene(
    *,
    background: Image.Image,
    render_defaults: Mapping[str, int],
    accent_color_name: str,
    spec: _CollisionAftermathSpec,
    font_family: str,
    diagram_style: Any | None = None,
) -> _RenderedScene:
    image = background.copy()
    draw = ImageDraw.Draw(image)
    canvas_width, canvas_height = image.size
    theme = build_physics_collision_theme(str(accent_color_name), diagram_style=diagram_style)
    label_font = load_font(int(render_defaults["label_font_size_px"]), bold=True, font_family=font_family)
    puck_font = load_font(int(render_defaults["puck_font_size_px"]), bold=True, font_family=font_family)

    table_bbox = [
        float(render_defaults["table_left_px"]),
        float(render_defaults["table_top_px"]),
        float(render_defaults["table_left_px"]) + float(render_defaults["table_width_px"]),
        float(render_defaults["table_top_px"]) + float(render_defaults["table_height_px"]),
    ]
    draw_rounded_rect(
        draw,
        tuple(float(value) for value in table_bbox),
        radius=int(render_defaults["table_corner_radius_px"]),
        fill=tuple(int(value) for value in theme.table_fill_rgb),
        outline=tuple(int(value) for value in theme.table_outline_rgb),
        width=4,
    )
    if str(spec.scene_variant) == "aftermath_gridded_table":
        _draw_grid(
            draw,
            table_bbox=table_bbox,
            spacing_px=int(render_defaults["grid_spacing_px"]),
            fill_rgb=tuple(int(value) for value in theme.grid_rgb),
        )

    impact_center = (
        float(render_defaults["impact_center_x_px"]),
        float(render_defaults["compact_impact_center_y_px"] if str(spec.scene_variant) == "aftermath_compact_table" else render_defaults["impact_center_y_px"]),
    )
    final_unit = _direction_unit(str(spec.final_motion_direction))
    target_distance = float(render_defaults["target_distance_px"])
    if str(spec.scene_variant) == "aftermath_compact_table":
        target_distance -= 18.0
    target_center = (
        float(impact_center[0] + final_unit[0] * target_distance),
        float(impact_center[1] + final_unit[1] * target_distance),
    )

    option_bboxes: Dict[str, List[float]] = {}
    option_arrow_bboxes: Dict[str, List[float]] = {}
    scene_entities: List[Dict[str, Any]] = [
        {
            "entity_id": "collision_table",
            "entity_type": "collision_table",
            "bbox_px": [round(float(value), 3) for value in table_bbox],
            "meta": {"scene_variant": str(spec.scene_variant)},
        }
    ]

    candidate_stroke = tuple(int(value) for value in theme.option_arrow_rgb)
    for letter in OPTION_LETTERS:
        direction = str(spec.option_directions[str(letter)])
        unit = _direction_unit(direction)
        inner_gap = float(render_defaults["incoming_arrow_inner_gap_px"])
        arrow_length = float(render_defaults["incoming_arrow_length_px"])
        arrow_start = (
            float(impact_center[0] - unit[0] * (inner_gap + arrow_length)),
            float(impact_center[1] - unit[1] * (inner_gap + arrow_length)),
        )
        arrow_end = (
            float(impact_center[0] - unit[0] * inner_gap),
            float(impact_center[1] - unit[1] * inner_gap),
        )
        draw_arrow(
            draw,
            start=arrow_start,
            end=arrow_end,
            fill=candidate_stroke,
            width=int(render_defaults["candidate_arrow_width_px"]),
            head_length_px=float(render_defaults["candidate_arrow_head_length_px"]),
            head_width_px=float(render_defaults["candidate_arrow_head_width_px"]),
        )
        arrow_bbox = _arrow_bbox(
            arrow_start,
            arrow_end,
            padding_px=float(render_defaults["candidate_arrow_head_width_px"]),
        )
        label_center = (
            float(arrow_start[0] - unit[0] * float(render_defaults["candidate_label_offset_px"])),
            float(arrow_start[1] - unit[1] * float(render_defaults["candidate_label_offset_px"])),
        )
        letter_bbox = draw_text_tag(
            draw,
            text=str(letter),
            center=label_center,
            font=label_font,
            fill_rgb=tuple(int(value) for value in theme.label_fill_rgb),
            outline_rgb=tuple(int(value) for value in theme.option_outline_rgb),
            text_rgb=tuple(int(value) for value in theme.label_text_rgb),
            stroke_width_px=int(render_defaults["label_stroke_width_px"]),
        )
        option_bbox = _bbox_union(arrow_bbox, letter_bbox)
        option_bboxes[str(letter)] = _clip_bbox(option_bbox, width=canvas_width, height=canvas_height)
        option_arrow_bboxes[str(letter)] = _clip_bbox(arrow_bbox, width=canvas_width, height=canvas_height)
        scene_entities.append(
            {
                "entity_id": f"option_{str(letter)}",
                "entity_type": "candidate_incoming_path",
                "bbox_px": list(option_bboxes[str(letter)]),
                "meta": {
                    "option_letter": str(letter),
                    "incoming_direction": str(direction),
                    "angle_degrees": float(DIRECTION_ANGLE_DEGREES[str(direction)]),
                    "is_correct": str(letter) == str(spec.correct_option_letter),
                },
            }
        )

    impact_radius = float(render_defaults["impact_radius_px"])
    impact_bbox = _bbox(
        (
            impact_center[0] - impact_radius,
            impact_center[1] - impact_radius,
            impact_center[0] + impact_radius,
            impact_center[1] + impact_radius,
        )
    )
    impact_rgb = tuple(int(value) for value in theme.collision_outline_rgb)
    draw.ellipse(tuple(float(value) for value in impact_bbox), fill=tuple(int(value) for value in theme.table_fill_rgb), outline=impact_rgb, width=4)
    draw.line((impact_center[0] - 9.0, impact_center[1], impact_center[0] + 9.0, impact_center[1]), fill=impact_rgb, width=3)
    draw.line((impact_center[0], impact_center[1] - 9.0, impact_center[0], impact_center[1] + 9.0), fill=impact_rgb, width=3)

    trail_start = (
        float(impact_center[0] + final_unit[0] * float(render_defaults["trail_start_gap_px"])),
        float(impact_center[1] + final_unit[1] * float(render_defaults["trail_start_gap_px"])),
    )
    trail_end = (
        float(target_center[0] - final_unit[0] * (float(render_defaults["puck_radius_px"]) + 5.0)),
        float(target_center[1] - final_unit[1] * (float(render_defaults["puck_radius_px"]) + 5.0)),
    )
    draw.line(
        (trail_start[0], trail_start[1], trail_end[0], trail_end[1]),
        fill=tuple(int(value) for value in theme.grid_rgb),
        width=max(3, int(render_defaults["motion_arrow_width_px"]) - 3),
    )
    draw_arrow(
        draw,
        start=trail_start,
        end=trail_end,
        fill=tuple(int(value) for value in theme.motion_arrow_rgb),
        width=int(render_defaults["motion_arrow_width_px"]),
        head_length_px=float(render_defaults["arrow_head_length_px"]),
        head_width_px=float(render_defaults["arrow_head_width_px"]),
    )
    trail_bbox = _arrow_bbox(trail_start, trail_end, padding_px=float(render_defaults["arrow_head_width_px"]))
    target_bbox = _draw_puck(
        draw,
        center=target_center,
        radius_px=float(render_defaults["puck_radius_px"]),
        label="after",
        fill_rgb=tuple(int(value) for value in theme.collision_fill_rgb),
        outline_rgb=tuple(int(value) for value in theme.collision_outline_rgb),
        text_rgb=tuple(int(value) for value in theme.puck_text_rgb),
        font=puck_font,
    )
    aftermath_bbox = _bbox_union(target_bbox, trail_bbox)

    annotation_bbox_map = {
        "impact_point": _clip_bbox(impact_bbox, width=canvas_width, height=canvas_height),
        "target_after_motion": _clip_bbox(aftermath_bbox, width=canvas_width, height=canvas_height),
    }
    scene_entities.extend(
        [
            {
                "entity_id": "impact_point",
                "entity_type": "impact_marker",
                "bbox_px": list(annotation_bbox_map["impact_point"]),
                "point_px": [round(float(impact_center[0]), 3), round(float(impact_center[1]), 3)],
                "meta": {"role": "initial_target_location"},
            },
            {
                "entity_id": "target_after_motion",
                "entity_type": "target_puck_after_impact",
                "bbox_px": list(annotation_bbox_map["target_after_motion"]),
                "point_px": [round(float(target_center[0]), 3), round(float(target_center[1]), 3)],
                "meta": {
                    "final_motion_direction": str(spec.final_motion_direction),
                    "angle_degrees": float(DIRECTION_ANGLE_DEGREES[str(spec.final_motion_direction)]),
                },
            },
        ]
    )
    render_map = {
        "accent_color_name": str(accent_color_name),
        "technical_diagram_frame_mode": str(getattr(diagram_style, "frame_mode", "none")),
        "table_bbox_px": [round(float(value), 3) for value in table_bbox],
        "impact_center_px": [round(float(impact_center[0]), 3), round(float(impact_center[1]), 3)],
        "target_center_px": [round(float(target_center[0]), 3), round(float(target_center[1]), 3)],
        "target_bbox_px": list(_clip_bbox(target_bbox, width=canvas_width, height=canvas_height)),
        "trail_bbox_px": list(_clip_bbox(trail_bbox, width=canvas_width, height=canvas_height)),
        "impact_bbox_px": list(annotation_bbox_map["impact_point"]),
        "aftermath_bbox_px": list(annotation_bbox_map["target_after_motion"]),
        "final_motion_direction": str(spec.final_motion_direction),
        "final_motion_angle_degrees": float(DIRECTION_ANGLE_DEGREES[str(spec.final_motion_direction)]),
        "correct_option_letter": str(spec.correct_option_letter),
        "option_directions": dict(spec.option_directions),
        "option_angles_degrees": dict(spec.option_angles_degrees),
        "option_bboxes_px": {str(letter): list(bbox) for letter, bbox in option_bboxes.items()},
        "option_arrow_bboxes_px": {str(letter): list(bbox) for letter, bbox in option_arrow_bboxes.items()},
        "annotation_keyed_bboxes_px": {str(key): list(value) for key, value in annotation_bbox_map.items()},
    }
    return _RenderedScene(
        image=image,
        annotation_bbox_map={str(key): list(value) for key, value in annotation_bbox_map.items()},
        scene_entities=[dict(entity) for entity in scene_entities],
        render_map=dict(render_map),
    )




@register_task
class PhysicsCollisionIncomingPathCauseChoiceTask:
    """Choose which incoming path caused the shown collision aftermath."""

    task_id = TASK_ID
    domain = "physics"
    scene_id = "mechanics"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        axes = _resolve_axes(int(instance_seed), params=params)
        spec = _make_spec(int(instance_seed), axes)
        canvas_width = int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width)))
        canvas_height = int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height)))
        background, background_meta, diagram_style, diagram_style_meta = prepare_physics_diagram_style_and_background(
            scene_id=SCENE_ID,
            canvas_width=int(canvas_width),
            canvas_height=int(canvas_height),
            instance_seed=int(instance_seed),
            params=params,
        )
        font_family = sample_font_family(
            role="readout",
            instance_seed=int(instance_seed),
            namespace=f"{TASK_NAMESPACE}.render.font",
            params=params,
        )
        font_record = get_font_family_record(str(font_family))
        render_defaults = _resolve_render_defaults(params, instance_seed=int(instance_seed))
        render_defaults, layout_placement_meta = _resolve_layout_placement(
            render_defaults=render_defaults,
            params=params,
            instance_seed=int(instance_seed),
            canvas_width=int(canvas_width),
            canvas_height=int(canvas_height),
        )
        rendered_scene = _render_scene(
            background=background,
            render_defaults=render_defaults,
            accent_color_name=str(axes.accent_color_name),
            spec=spec,
            font_family=str(font_family),
            diagram_style=diagram_style,
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
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
                f"object_description_{str(spec.scene_variant)}",
                f"answer_hint_{QUERY_ID}",
                f"annotation_hint_{QUERY_ID}",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = resolve_prompt_json_examples(
            prompt_defaults,
            annotation_value={"impact_point": [10, 10, 28, 28], "target_after_motion": [40, 30, 130, 90]},
            answer_type="option_letter",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            scene_id=self.scene_id,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=QUERY_ID,
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults[f"object_description_{str(spec.scene_variant)}"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[f"answer_hint_{QUERY_ID}"]),
                "annotation_hint": str(prompt_defaults[f"annotation_hint_{QUERY_ID}"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="option_letter", value=str(spec.correct_option_letter))
        annotation_gt = TypedValue(
            type="keyed_bbox_map",
            value={str(key): list(value) for key, value in rendered_scene.annotation_bbox_map.items()},
        )
        scenario_payload = {
            "final_motion_direction": str(spec.final_motion_direction),
            "final_motion_angle_degrees": float(DIRECTION_ANGLE_DEGREES[str(spec.final_motion_direction)]),
            "correct_option_letter": str(spec.correct_option_letter),
            "correct_incoming_direction": str(spec.option_directions[str(spec.correct_option_letter)]),
            "option_directions": dict(spec.option_directions),
            "option_angles_degrees": dict(spec.option_angles_degrees),
            "candidate_rule": "incoming_path_vector_matches_observed_target_after_motion_vector",
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"physics_collision_aftermath_{str(spec.scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(spec.scene_variant),
                    "query_id": QUERY_ID,
                    "accent_color_name": str(axes.accent_color_name),
                    "scenario": dict(scenario_payload),
                    "annotation_entity_ids": ["impact_point", "target_after_motion"],
                },
            },
            "query_spec": {
                "query_id": QUERY_ID,
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "scene_variant": str(spec.scene_variant),
                    "query_id": QUERY_ID,
                    "final_motion_direction": str(spec.final_motion_direction),
                    "accent_color_name": str(axes.accent_color_name),
                    "correct_option_letter": str(spec.correct_option_letter),
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "final_motion_direction_probabilities": dict(axes.final_motion_direction_probabilities),
                    "correct_option_letter_probabilities": dict(axes.correct_option_letter_probabilities),
                    "accent_color_name_probabilities": dict(axes.accent_color_name_probabilities),
                },
            },
            "render_spec": {
                "scene_variant": str(spec.scene_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "accent_color_name": str(axes.accent_color_name),
                "font": {
                    "font_family": str(font_family),
                    "font_asset_version": font_asset_version(),
                    "font_asset": font_record.to_trace(),
                    "scope": "collision_aftermath_diagram",
                    "selection_policy": {
                        "pool": "global_approved_font_pool",
                        "include_tags": [],
                        "exclude_tags": [],
                        "exclusion_reason": "",
                    },
                },
                "technical_diagram_style": dict(diagram_style_meta),
                "background_style": background_meta,
                "layout_placement": dict(layout_placement_meta),
                "post_image_noise": post_noise_meta,
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(spec.scene_variant),
                "query_id": QUERY_ID,
                "final_motion_direction": str(spec.final_motion_direction),
                "accent_color_name": str(axes.accent_color_name),
                "correct_option_letter": str(spec.correct_option_letter),
                "answer_type": "option_letter",
                "option_letters": list(OPTION_LETTERS),
                "scenario": dict(scenario_payload),
                "annotation_entity_ids": ["impact_point", "target_after_motion"],
            },
            "witness_symbolic": {
                "type": "object_key_map",
                "ids": ["impact_point", "target_after_motion"],
                "keys": {"impact_point": "impact_point", "target_after_motion": "target_after_motion"},
            },
            "projected_annotation": {
                "type": "keyed_bbox_map",
                "keyed_bbox_map": {str(key): list(value) for key, value in rendered_scene.annotation_bbox_map.items()},
                "pixel_keyed_bbox_map": {str(key): list(value) for key, value in rendered_scene.annotation_bbox_map.items()},
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
            task_versions=default_task_versions(),
            query_id=QUERY_ID,
            scene_id=SCENE_ID,
        )


__all__ = [
    "PhysicsCollisionIncomingPathCauseChoiceTask",
    "_option_directions",
]
