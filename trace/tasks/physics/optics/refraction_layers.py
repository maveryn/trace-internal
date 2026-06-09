"""Physics optics task for inferring medium speed order from refraction."""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import hash64, spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.drawing import draw_arrow, draw_centered_text, draw_dashed_line
from ...shared.font_assets import font_asset_version, get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import build_prompt_json_examples
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from ..shared.complexity import (
    build_physics_complexity,
    clamp_unit_interval,
    normalize_linear,
    resolve_physics_complexity_weights,
)
from ..shared.diagram_style import prepare_physics_diagram_style_and_background
from ..shared.visual_defaults import load_physics_noise_defaults


FAMILY_ID = "physics_optics_refraction_layers_family"
SCENE_ID = "refraction_layers"
QUERY_ID = "three_medium_speed_order"
OPTION_LABELS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")
MEDIUM_LABELS: Tuple[str, ...] = ("M1", "M2", "M3")
ALL_SPEED_ORDERS: Tuple[Tuple[str, str, str], ...] = tuple(itertools.permutations(MEDIUM_LABELS))
SPEED_VALUES_BY_RANK: Tuple[float, float, float] = (1.0, 0.76, 0.52)

_TASK_GROUP_DEFAULTS = get_task_group_defaults("physics", "optics")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=FAMILY_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(task_group="optics", apply_prob=0.5)


@dataclass(frozen=True)
class _RefractionScenario:
    orientation: str
    entry_side: str
    transverse_sign: int
    speed_order: Tuple[str, str, str]
    medium_speeds: Dict[str, float]
    angle_by_medium_deg: Dict[str, float]
    option_map: Dict[str, str]
    correct_label: str


@dataclass(frozen=True)
class _RayGeometry:
    points: Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float], Tuple[float, float]]
    bend_points: Tuple[Tuple[float, float], Tuple[float, float]]
    segment_mediums: Tuple[str, str, str]
    segment_angles_deg: Tuple[float, float, float]


def _bbox(values: Tuple[float, float, float, float]) -> List[float]:
    return [round(float(value), 3) for value in values]


def _clip_bbox(values: Tuple[float, float, float, float], *, width: int, height: int) -> List[float]:
    x0, y0, x1, y1 = [float(value) for value in values]
    return _bbox(
        (
            max(0.0, min(float(width), x0)),
            max(0.0, min(float(height), y0)),
            max(0.0, min(float(width), x1)),
            max(0.0, min(float(height), y1)),
        )
    )


def _blend_rgb(a: Sequence[int], b: Sequence[int], alpha: float) -> Tuple[int, int, int]:
    return tuple(
        int(round((float(1.0 - alpha) * int(a[idx])) + (float(alpha) * int(b[idx]))))
        for idx in range(3)
    )


def _order_text(order: Sequence[str]) -> str:
    return " > ".join(str(label) for label in order)


def _parse_speed_order(raw_value: Any) -> Tuple[str, str, str] | None:
    if raw_value is None:
        return None
    if isinstance(raw_value, str):
        tokens = [part.strip() for part in raw_value.replace(">", ",").split(",") if part.strip()]
    elif isinstance(raw_value, Sequence):
        tokens = [str(part).strip() for part in raw_value]
    else:
        return None
    candidate = tuple(tokens)
    if candidate in ALL_SPEED_ORDERS:
        return candidate  # type: ignore[return-value]
    return None


def _weighted_choice(
    values: Sequence[str],
    weights: Mapping[str, Any],
    *,
    instance_seed: int,
    namespace: str,
) -> str:
    active: List[Tuple[str, float]] = []
    for value in values:
        weight = float(weights.get(str(value), 1.0))
        if weight > 0.0:
            active.append((str(value), float(weight)))
    if not active:
        return str(values[int(hash64(int(instance_seed), str(namespace), 0) % len(values))])
    total = sum(weight for _, weight in active)
    raw = float(hash64(int(instance_seed), str(namespace), 0) % 1_000_000) / 1_000_000.0
    cursor = 0.0
    for value, weight in active:
        cursor += float(weight) / float(total)
        if raw <= cursor:
            return str(value)
    return str(active[-1][0])


def _make_scenario(instance_seed: int, params: Mapping[str, Any]) -> _RefractionScenario:
    orientation = str(params.get("layer_orientation") or params.get("orientation") or "").strip()
    if orientation not in {"horizontal", "vertical"}:
        orientation = _weighted_choice(
            ("horizontal", "vertical"),
            _GEN_DEFAULTS.get("layer_orientation_weights", {}),
            instance_seed=int(instance_seed),
            namespace=f"{FAMILY_ID}.orientation",
        )
    if orientation == "horizontal":
        entry_options = ("top", "bottom")
    else:
        entry_options = ("left", "right")
    entry_side = str(params.get("entry_side") or "").strip()
    if entry_side not in set(entry_options):
        entry_side = str(entry_options[int(hash64(int(instance_seed), f"{FAMILY_ID}.entry_side", 0) % 2)])
    transverse_sign = 1 if int(hash64(int(instance_seed), f"{FAMILY_ID}.transverse_sign", 0) % 2) == 0 else -1

    explicit_order = _parse_speed_order(params.get("speed_order") or params.get("target_order"))
    if explicit_order is None:
        order_index = int(hash64(int(instance_seed), f"{FAMILY_ID}.speed_order", 0) % len(ALL_SPEED_ORDERS))
        speed_order = tuple(ALL_SPEED_ORDERS[order_index])
    else:
        speed_order = explicit_order

    medium_speeds = {
        str(label): float(SPEED_VALUES_BY_RANK[rank])
        for rank, label in enumerate(speed_order)
    }
    max_angle_options = (40.0, 42.0, 44.0) if orientation == "horizontal" else (34.0, 36.0, 38.0)
    max_angle_deg = float(max_angle_options[int(hash64(int(instance_seed), f"{FAMILY_ID}.max_angle", 0) % len(max_angle_options))])
    invariant = math.sin(math.radians(max_angle_deg)) / max(medium_speeds.values())
    angle_by_medium_deg = {
        str(label): round(float(math.degrees(math.asin(max(-0.95, min(0.95, invariant * speed))))), 3)
        for label, speed in medium_speeds.items()
    }

    correct_index = int(hash64(int(instance_seed), f"{FAMILY_ID}.correct_option", 0) % len(OPTION_LABELS))
    distractor_orders = [order for order in ALL_SPEED_ORDERS if tuple(order) != tuple(speed_order)]
    rng = spawn_rng(int(instance_seed), f"{FAMILY_ID}.option_shuffle")
    rng.shuffle(distractor_orders)
    option_map: Dict[str, str] = {}
    distractor_index = 0
    for index, label in enumerate(OPTION_LABELS):
        if index == correct_index:
            option_map[str(label)] = _order_text(speed_order)
        else:
            option_map[str(label)] = _order_text(distractor_orders[distractor_index])
            distractor_index += 1

    return _RefractionScenario(
        orientation=str(orientation),
        entry_side=str(entry_side),
        transverse_sign=int(transverse_sign),
        speed_order=tuple(speed_order),
        medium_speeds=dict(medium_speeds),
        angle_by_medium_deg=dict(angle_by_medium_deg),
        option_map=dict(option_map),
        correct_label=str(OPTION_LABELS[correct_index]),
    )


def _ray_geometry(
    *,
    scenario: _RefractionScenario,
    medium_box: Tuple[float, float, float, float],
) -> _RayGeometry:
    left, top, right, bottom = [float(value) for value in medium_box]
    margin = 26.0
    if scenario.orientation == "horizontal":
        y1 = top + ((bottom - top) / 3.0)
        y2 = top + (2.0 * (bottom - top) / 3.0)
        if scenario.entry_side == "top":
            border_values = (top, y1, y2, bottom)
            segment_mediums = ("M1", "M2", "M3")
        else:
            border_values = (bottom, y2, y1, top)
            segment_mediums = ("M3", "M2", "M1")
        distances = [abs(border_values[idx + 1] - border_values[idx]) for idx in range(3)]
        tangents = [math.tan(math.radians(float(scenario.angle_by_medium_deg[label]))) for label in segment_mediums]
        sign = float(scenario.transverse_sign)
        coeffs = (
            -sign * distances[0] * tangents[0],
            0.0,
            sign * distances[1] * tangents[1],
            sign * ((distances[1] * tangents[1]) + (distances[2] * tangents[2])),
        )
        lower = left + margin
        upper = right - margin
        x_low = max(lower - coeff for coeff in coeffs)
        x_high = min(upper - coeff for coeff in coeffs)
        if x_high < x_low:
            x_mid = (left + right) * 0.5
        else:
            jitter_span = min(48.0, max(0.0, (x_high - x_low) * 0.34))
            raw = (float(hash64(int(round(left + right + top + bottom)), f"{FAMILY_ID}.x_jitter", 0) % 10_000) / 10_000.0) - 0.5
            x_mid = ((x_low + x_high) * 0.5) + (raw * 2.0 * jitter_span)
        points = tuple((float(x_mid + coeffs[idx]), float(border_values[idx])) for idx in range(4))
    else:
        x1 = left + ((right - left) / 3.0)
        x2 = left + (2.0 * (right - left) / 3.0)
        if scenario.entry_side == "left":
            border_values = (left, x1, x2, right)
            segment_mediums = ("M1", "M2", "M3")
        else:
            border_values = (right, x2, x1, left)
            segment_mediums = ("M3", "M2", "M1")
        distances = [abs(border_values[idx + 1] - border_values[idx]) for idx in range(3)]
        tangents = [math.tan(math.radians(float(scenario.angle_by_medium_deg[label]))) for label in segment_mediums]
        sign = float(scenario.transverse_sign)
        coeffs = (
            -sign * distances[0] * tangents[0],
            0.0,
            sign * distances[1] * tangents[1],
            sign * ((distances[1] * tangents[1]) + (distances[2] * tangents[2])),
        )
        lower = top + margin
        upper = bottom - margin
        y_low = max(lower - coeff for coeff in coeffs)
        y_high = min(upper - coeff for coeff in coeffs)
        if y_high < y_low:
            y_mid = (top + bottom) * 0.5
        else:
            jitter_span = min(36.0, max(0.0, (y_high - y_low) * 0.30))
            raw = (float(hash64(int(round(left + right + top + bottom)), f"{FAMILY_ID}.y_jitter", 0) % 10_000) / 10_000.0) - 0.5
            y_mid = ((y_low + y_high) * 0.5) + (raw * 2.0 * jitter_span)
        points = tuple((float(border_values[idx]), float(y_mid + coeffs[idx])) for idx in range(4))
    return _RayGeometry(
        points=points,  # type: ignore[arg-type]
        bend_points=(points[1], points[2]),
        segment_mediums=tuple(segment_mediums),
        segment_angles_deg=tuple(float(scenario.angle_by_medium_deg[label]) for label in segment_mediums),
    )


def _draw_media_regions(
    draw: ImageDraw.ImageDraw,
    *,
    scenario: _RefractionScenario,
    medium_box: Tuple[float, float, float, float],
    style: Any,
    font: Any,
    instance_seed: int,
) -> Dict[str, List[float]]:
    left, top, right, bottom = [float(value) for value in medium_box]
    fill_seeds = [
        (219, 238, 255),
        (225, 244, 225),
        (255, 237, 213),
        (239, 229, 255),
        (225, 246, 246),
        (255, 228, 233),
    ]
    rng = spawn_rng(int(instance_seed), f"{FAMILY_ID}.medium_fills")
    rng.shuffle(fill_seeds)
    label_bboxes: Dict[str, List[float]] = {}
    outline = tuple(int(v) for v in style.panel_border_rgb)
    text_rgb = tuple(int(v) for v in style.label_rgb)
    if scenario.orientation == "horizontal":
        y_values = [top, top + ((bottom - top) / 3.0), top + (2.0 * (bottom - top) / 3.0), bottom]
        for idx, label in enumerate(MEDIUM_LABELS):
            rect = (left, y_values[idx], right, y_values[idx + 1])
            fill = _blend_rgb(fill_seeds[idx], style.panel_fill_rgb, 0.18)
            draw.rectangle(rect, fill=fill, outline=outline, width=1)
            label_bboxes[str(label)] = draw_centered_text(
                draw,
                text=str(label),
                center=(left + 48.0, (rect[1] + rect[3]) * 0.5),
                font=font,
                fill=text_rgb,
                stroke_fill=resolve_text_stroke_fill(text_rgb),
                stroke_width=2,
            )
        for y in y_values[1:-1]:
            draw.line((left, y, right, y), fill=tuple(int(v) for v in style.stroke_rgb), width=3)
    else:
        x_values = [left, left + ((right - left) / 3.0), left + (2.0 * (right - left) / 3.0), right]
        for idx, label in enumerate(MEDIUM_LABELS):
            rect = (x_values[idx], top, x_values[idx + 1], bottom)
            fill = _blend_rgb(fill_seeds[idx], style.panel_fill_rgb, 0.18)
            draw.rectangle(rect, fill=fill, outline=outline, width=1)
            label_bboxes[str(label)] = draw_centered_text(
                draw,
                text=str(label),
                center=((rect[0] + rect[2]) * 0.5, top + 38.0),
                font=font,
                fill=text_rgb,
                stroke_fill=resolve_text_stroke_fill(text_rgb),
                stroke_width=2,
            )
        for x in x_values[1:-1]:
            draw.line((x, top, x, bottom), fill=tuple(int(v) for v in style.stroke_rgb), width=3)
    return label_bboxes


def _draw_ray_and_normals(
    draw: ImageDraw.ImageDraw,
    *,
    scenario: _RefractionScenario,
    geometry: _RayGeometry,
    style: Any,
) -> None:
    ray_rgb = tuple(int(v) for v in style.secondary_accent_rgb)
    guide_rgb = tuple(int(v) for v in style.guide_rgb)
    stroke_rgb = tuple(int(v) for v in style.stroke_rgb)
    normal_half = 74.0
    for point in geometry.bend_points:
        x, y = float(point[0]), float(point[1])
        if scenario.orientation == "horizontal":
            start = (x, y - normal_half)
            end = (x, y + normal_half)
        else:
            start = (x - normal_half, y)
            end = (x + normal_half, y)
        draw_dashed_line(draw, start=start, end=end, fill=guide_rgb, width=3, dash_px=9, gap_px=7)
    draw.line(list(geometry.points), fill=stroke_rgb, width=11)
    draw.line(list(geometry.points), fill=ray_rgb, width=7)
    for point in geometry.bend_points:
        x, y = float(point[0]), float(point[1])
        draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill=ray_rgb, outline=stroke_rgb, width=2)
    pre_end = geometry.points[-2]
    final_end = geometry.points[-1]
    arrow_start = (
        float(pre_end[0] + 0.52 * (final_end[0] - pre_end[0])),
        float(pre_end[1] + 0.52 * (final_end[1] - pre_end[1])),
    )
    draw_arrow(
        draw,
        start=arrow_start,
        end=final_end,
        fill=ray_rgb,
        width=7,
        head_length_px=18,
        head_width_px=17,
    )


def _draw_option_panel(
    draw: ImageDraw.ImageDraw,
    *,
    option_box: Tuple[float, float, float, float],
    scenario: _RefractionScenario,
    style: Any,
    title_font: Any,
    option_font: Any,
) -> Dict[str, List[float]]:
    left, top, right, bottom = [float(value) for value in option_box]
    draw.rounded_rectangle(
        option_box,
        radius=18,
        fill=tuple(int(v) for v in style.panel_fill_rgb),
        outline=tuple(int(v) for v in style.panel_border_rgb),
        width=3,
    )
    text_rgb = tuple(int(v) for v in style.label_rgb)
    draw_centered_text(
        draw,
        text="Fastest to slowest",
        center=((left + right) * 0.5, top + 34.0),
        font=title_font,
        fill=text_rgb,
        stroke_fill=resolve_text_stroke_fill(text_rgb),
        stroke_width=1,
    )
    option_bboxes: Dict[str, List[float]] = {}
    box_left = left + 22.0
    box_right = right - 22.0
    box_h = 66.0
    gap = 14.0
    y = top + 76.0
    for label in OPTION_LABELS:
        box = (box_left, y, box_right, y + box_h)
        draw.rounded_rectangle(
            box,
            radius=12,
            fill=tuple(int(v) for v in style.option_fill_rgb),
            outline=tuple(int(v) for v in style.panel_border_rgb),
            width=2,
        )
        draw_centered_text(
            draw,
            text=str(label),
            center=(box_left + 25.0, y + (box_h * 0.5)),
            font=option_font,
            fill=text_rgb,
            stroke_fill=resolve_text_stroke_fill(text_rgb),
            stroke_width=1,
        )
        draw_centered_text(
            draw,
            text=str(scenario.option_map[str(label)]),
            center=(box_left + 132.0, y + (box_h * 0.5)),
            font=option_font,
            fill=text_rgb,
            stroke_fill=resolve_text_stroke_fill(text_rgb),
            stroke_width=1,
        )
        option_bboxes[str(label)] = _bbox(box)
        y += box_h + gap
    return option_bboxes


def _render_scene(
    *,
    image: Image.Image,
    scenario: _RefractionScenario,
    font_family: str,
    style: Any,
    instance_seed: int,
    render_defaults: Mapping[str, Any],
) -> Tuple[Image.Image, Dict[str, List[float]], Dict[str, Any]]:
    draw = ImageDraw.Draw(image)
    canvas_width, canvas_height = image.size
    title_font = load_font(25, bold=True, font_family=font_family)
    label_font = load_font(24, bold=True, font_family=font_family)
    option_font = load_font(19, bold=True, font_family=font_family)

    diagram_box = (
        float(render_defaults.get("diagram_left_px", 54)),
        float(render_defaults.get("diagram_top_px", 54)),
        float(render_defaults.get("diagram_right_px", 744)),
        float(render_defaults.get("diagram_bottom_px", 646)),
    )
    option_box = (
        float(render_defaults.get("option_left_px", 774)),
        float(render_defaults.get("option_top_px", 64)),
        float(render_defaults.get("option_right_px", canvas_width - 50)),
        float(render_defaults.get("option_bottom_px", canvas_height - 64)),
    )
    draw.rounded_rectangle(
        diagram_box,
        radius=20,
        fill=tuple(int(v) for v in style.panel_fill_rgb),
        outline=tuple(int(v) for v in style.panel_border_rgb),
        width=3,
    )
    text_rgb = tuple(int(v) for v in style.label_rgb)
    draw_centered_text(
        draw,
        text="Refraction through labeled media",
        center=((diagram_box[0] + diagram_box[2]) * 0.5, diagram_box[1] + 30.0),
        font=title_font,
        fill=text_rgb,
        stroke_fill=resolve_text_stroke_fill(text_rgb),
        stroke_width=1,
    )
    medium_box = (
        diagram_box[0] + 36.0,
        diagram_box[1] + 68.0,
        diagram_box[2] - 36.0,
        diagram_box[3] - 32.0,
    )
    label_bboxes = _draw_media_regions(
        draw,
        scenario=scenario,
        medium_box=medium_box,
        style=style,
        font=label_font,
        instance_seed=int(instance_seed),
    )
    geometry = _ray_geometry(scenario=scenario, medium_box=medium_box)
    _draw_ray_and_normals(draw, scenario=scenario, geometry=geometry, style=style)
    option_bboxes = _draw_option_panel(
        draw,
        option_box=option_box,
        scenario=scenario,
        style=style,
        title_font=title_font,
        option_font=option_font,
    )
    annotation_map: Dict[str, List[float]] = {}
    for idx, point in enumerate(geometry.bend_points, start=1):
        x, y = float(point[0]), float(point[1])
        if scenario.orientation == "horizontal":
            box = (x - 72.0, y - 88.0, x + 72.0, y + 88.0)
        else:
            box = (x - 88.0, y - 72.0, x + 88.0, y + 72.0)
        annotation_map[f"interface_{idx}_bend"] = _clip_bbox(box, width=canvas_width, height=canvas_height)
    render_map = {
        "diagram_box": _bbox(diagram_box),
        "medium_box": _bbox(medium_box),
        "option_bboxes": option_bboxes,
        "medium_label_bboxes": label_bboxes,
        "ray_points": [[round(float(x), 3), round(float(y), 3)] for x, y in geometry.points],
        "bend_points": [[round(float(x), 3), round(float(y), 3)] for x, y in geometry.bend_points],
        "segment_mediums": list(geometry.segment_mediums),
        "segment_angles_deg": [round(float(value), 3) for value in geometry.segment_angles_deg],
        "medium_speeds": {str(k): round(float(v), 3) for k, v in scenario.medium_speeds.items()},
        "angle_by_medium_deg": {str(k): round(float(v), 3) for k, v in scenario.angle_by_medium_deg.items()},
        "speed_order": list(scenario.speed_order),
        "option_map": dict(scenario.option_map),
        "correct_label": str(scenario.correct_label),
    }
    return image, annotation_map, render_map


def _build_complexity(*, scenario: _RefractionScenario, bend_count: int) -> TaskComplexity:
    weights = resolve_physics_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=FAMILY_ID)
    angle_values = [float(value) for value in scenario.angle_by_medium_deg.values()]
    min_angle_gap = min(abs(a - b) for a, b in itertools.combinations(angle_values, 2))
    visual_scan = clamp_unit_interval(0.34 + (0.08 if scenario.orientation == "vertical" else 0.0))
    refraction_reasoning = clamp_unit_interval(0.56 + (0.18 * normalize_linear(float(bend_count), min_value=1.0, max_value=2.0)))
    ambiguity = clamp_unit_interval(0.28 - (0.12 * normalize_linear(float(min_angle_gap), min_value=6.0, max_value=16.0)))
    output_burden = 0.32
    return build_physics_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "refraction_reasoning": float(refraction_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


@register_task
class PhysicsRefractionLayersMediumSpeedOrderLabelTask:
    """Choose the fastest-to-slowest light-speed order from ray bending."""

    task_id = "task_physics__refraction_layers__medium_speed_order_label"
    domain = "physics"
    task_group = "optics"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        _ = int(max_attempts)
        params = dict(params or {})
        canvas_width = int(_RENDER_DEFAULTS.get("canvas_width", 1080))
        canvas_height = int(_RENDER_DEFAULTS.get("canvas_height", 700))
        background, background_meta, diagram_style, diagram_style_meta = prepare_physics_diagram_style_and_background(
            instance_seed=int(instance_seed),
            params=params,
            scene_id=SCENE_ID,
            task_group=self.task_group,
            canvas_width=canvas_width,
            canvas_height=canvas_height,
            require_grid=True,
        )
        font_family = sample_font_family(
            role="readout",
            instance_seed=int(instance_seed),
            namespace=f"{FAMILY_ID}.font",
            params=params,
        )
        font_record = get_font_family_record(str(font_family))
        scenario = _make_scenario(int(instance_seed), params)
        rendered, annotation_map, render_map = _render_scene(
            image=background,
            scenario=scenario,
            font_family=str(font_family),
            style=diagram_style,
            instance_seed=int(instance_seed),
            render_defaults=_RENDER_DEFAULTS,
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered,
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
                "object_description",
                f"answer_hint_{QUERY_ID}",
                f"annotation_hint_{QUERY_ID}",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        answer_gt = TypedValue(type="option_letter", value=str(scenario.correct_label))
        annotation_gt = TypedValue(type="keyed_bbox_map", value={str(k): list(v) for k, v in annotation_map.items()})
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
            query_key=QUERY_ID,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[f"answer_hint_{QUERY_ID}"]),
                "annotation_hint": str(prompt_defaults[f"annotation_hint_{QUERY_ID}"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        complexity = _build_complexity(scenario=scenario, bend_count=2)
        trace_payload = {
            "scene_ir": {
                "scene_kind": "physics_refraction_layers_three_media",
                "entities": [
                    {
                        "entity_id": str(label),
                        "entity_type": "medium_region",
                        "speed_rank_fastest_to_slowest": int(scenario.speed_order.index(str(label)) + 1),
                        "relative_speed": float(scenario.medium_speeds[str(label)]),
                    }
                    for label in MEDIUM_LABELS
                ],
                "relations": {
                    "query_id": QUERY_ID,
                    "orientation": str(scenario.orientation),
                    "entry_side": str(scenario.entry_side),
                    "speed_order": list(scenario.speed_order),
                    "correct_label": str(scenario.correct_label),
                },
            },
            "query_spec": {
                "query_id": QUERY_ID,
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": QUERY_ID,
                    "target_answer": str(scenario.correct_label),
                    "speed_order": list(scenario.speed_order),
                    "orientation": str(scenario.orientation),
                    "entry_side": str(scenario.entry_side),
                },
            },
            "render_spec": {
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "font": {
                    "font_family": str(font_family),
                    "font_asset_version": font_asset_version(),
                    "font_asset": font_record.to_trace(),
                    "scope": "refraction_layers_diagram",
                    "selection_policy": {
                        "pool": "global_approved_font_pool",
                        "include_tags": [],
                        "exclude_tags": [],
                        "exclusion_reason": "",
                    },
                },
                "technical_diagram_style": dict(diagram_style_meta),
                "background_style": background_meta,
                "post_image_noise": post_noise_meta,
            },
            "render_map": dict(render_map),
            "execution_trace": {
                "query_id": QUERY_ID,
                "orientation": str(scenario.orientation),
                "entry_side": str(scenario.entry_side),
                "speed_order": list(scenario.speed_order),
                "medium_speeds": {str(k): float(v) for k, v in scenario.medium_speeds.items()},
                "angle_by_medium_deg": {str(k): float(v) for k, v in scenario.angle_by_medium_deg.items()},
                "option_map": dict(scenario.option_map),
                "target_answer": str(scenario.correct_label),
                "annotation_entity_ids": sorted(annotation_gt.value.keys()),
            },
            "witness_symbolic": {
                "type": "object_map",
                "ids": sorted(annotation_gt.value.keys()),
            },
            "projected_annotation": {
                "type": "keyed_bbox_map",
                "keyed_bbox_map": {str(k): list(v) for k, v in annotation_gt.value.items()},
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
            query_id=QUERY_ID,
            scene_id=SCENE_ID,
        )


__all__ = ["PhysicsRefractionLayersMediumSpeedOrderLabelTask"]
