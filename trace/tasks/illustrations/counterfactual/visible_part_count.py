"""Counterfactual visible-part counting for single illustration objects."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants


TASK_ID = "task_illustrations__single_object_figure__visible_part_count"
SCENE_ID = "single_object_figure"
BIRD_VARIANT = "bird_visible_leg_count"
QUADRUPED_VARIANT = "quadruped_visible_leg_count"
AIRPLANE_VARIANT = "airplane_visible_wing_count"
BUTTERFLY_VARIANT = "butterfly_visible_wing_count"
BICYCLE_VARIANT = "bicycle_visible_wheel_count"
TRAFFIC_LIGHT_VARIANT = "traffic_light_visible_lens_count"
CLOVER_VARIANT = "clover_visible_leaf_count"
STAR_VARIANT = "star_visible_point_count"
GLOVE_VARIANT = "glove_visible_finger_count"
FORK_VARIANT = "fork_visible_tine_count"
SNOWFLAKE_VARIANT = "snowflake_visible_arm_count"
CHAIR_VARIANT = "chair_visible_leg_count"
SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = (
    BIRD_VARIANT,
    QUADRUPED_VARIANT,
    AIRPLANE_VARIANT,
    BUTTERFLY_VARIANT,
    BICYCLE_VARIANT,
    TRAFFIC_LIGHT_VARIANT,
    CLOVER_VARIANT,
    STAR_VARIANT,
    GLOVE_VARIANT,
    FORK_VARIANT,
    SNOWFLAKE_VARIANT,
    CHAIR_VARIANT,
)
CANONICAL_BIAS_ANSWER: Dict[str, int] = {
    BIRD_VARIANT: 2,
    QUADRUPED_VARIANT: 4,
    AIRPLANE_VARIANT: 2,
    BUTTERFLY_VARIANT: 4,
    BICYCLE_VARIANT: 2,
    TRAFFIC_LIGHT_VARIANT: 3,
    CLOVER_VARIANT: 3,
    STAR_VARIANT: 5,
    GLOVE_VARIANT: 5,
    FORK_VARIANT: 4,
    SNOWFLAKE_VARIANT: 6,
    CHAIR_VARIANT: 4,
}
OBJECT_DESCRIPTION: Dict[str, str] = {
    BIRD_VARIANT: "a stylized bird",
    QUADRUPED_VARIANT: "a stylized four-legged animal",
    AIRPLANE_VARIANT: "a stylized airplane",
    BUTTERFLY_VARIANT: "a stylized butterfly",
    BICYCLE_VARIANT: "a stylized bicycle",
    TRAFFIC_LIGHT_VARIANT: "a stylized traffic light",
    CLOVER_VARIANT: "a stylized clover",
    STAR_VARIANT: "a stylized star",
    GLOVE_VARIANT: "a stylized glove",
    FORK_VARIANT: "a stylized fork",
    SNOWFLAKE_VARIANT: "a stylized snowflake",
    CHAIR_VARIANT: "a stylized chair",
}
COUNTED_PART_KIND: Dict[str, str] = {
    BIRD_VARIANT: "leg",
    QUADRUPED_VARIANT: "leg",
    AIRPLANE_VARIANT: "wing",
    BUTTERFLY_VARIANT: "wing",
    BICYCLE_VARIANT: "wheel",
    TRAFFIC_LIGHT_VARIANT: "lens",
    CLOVER_VARIANT: "leaf",
    STAR_VARIANT: "point",
    GLOVE_VARIANT: "finger",
    FORK_VARIANT: "tine",
    SNOWFLAKE_VARIANT: "arm",
    CHAIR_VARIANT: "leg",
}
STYLE_SUPPORT: Dict[str, Tuple[str, ...]] = {
    BIRD_VARIANT: ("round_bird", "duck", "long_neck"),
    QUADRUPED_VARIANT: ("canine", "horse", "rabbit"),
    AIRPLANE_VARIANT: ("jet", "propeller", "glider"),
    BUTTERFLY_VARIANT: ("rounded", "pointed", "longwing"),
    BICYCLE_VARIANT: ("city_bike", "step_through", "cargo"),
    TRAFFIC_LIGHT_VARIANT: ("vertical", "rounded", "signal_post"),
    CLOVER_VARIANT: ("round_leaf", "heart_leaf", "wide_leaf"),
    STAR_VARIANT: ("classic", "sharp", "soft"),
    GLOVE_VARIANT: ("cartoon", "work", "sport"),
    FORK_VARIANT: ("dinner", "rounded", "wide"),
    SNOWFLAKE_VARIANT: ("simple", "branched", "crystal"),
    CHAIR_VARIANT: ("dining", "wooden", "cushioned"),
}
OBJECT_COLOR_PALETTE: Tuple[Tuple[Tuple[int, int, int], Tuple[int, int, int]], ...] = (
    ((82, 125, 176), (232, 157, 83)),
    ((174, 102, 94), (237, 195, 92)),
    ((90, 151, 126), (211, 120, 156)),
    ((133, 105, 170), (102, 174, 209)),
)
TRAFFIC_LIGHT_COLOR_PALETTE: Tuple[Dict[str, Tuple[int, int, int]], ...] = (
    {"traffic_casing": (65, 72, 80), "traffic_pole": (96, 104, 112), "traffic_hood": (44, 50, 56)},
    {"traffic_casing": (74, 64, 58), "traffic_pole": (105, 96, 88), "traffic_hood": (52, 45, 41)},
    {"traffic_casing": (50, 74, 78), "traffic_pole": (83, 108, 112), "traffic_hood": (37, 54, 57)},
    {"traffic_casing": (78, 58, 70), "traffic_pole": (106, 88, 99), "traffic_hood": (57, 42, 51)},
)
TRAFFIC_LENS_COLORS: Tuple[Tuple[int, int, int], ...] = (
    (216, 70, 69),
    (235, 185, 61),
    (62, 171, 99),
    (75, 143, 210),
    (158, 93, 181),
)
CLOVER_COLOR_PALETTE: Tuple[Dict[str, Tuple[int, int, int]], ...] = (
    {"clover_fill": (79, 161, 89), "clover_accent": (46, 125, 65), "clover_outline": (42, 82, 50), "clover_vein": (54, 132, 68)},
    {"clover_fill": (94, 174, 91), "clover_accent": (61, 137, 65), "clover_outline": (45, 89, 48), "clover_vein": (67, 145, 67)},
    {"clover_fill": (68, 149, 105), "clover_accent": (45, 116, 83), "clover_outline": (38, 83, 62), "clover_vein": (51, 126, 88)},
    {"clover_fill": (112, 164, 70), "clover_accent": (78, 128, 49), "clover_outline": (57, 85, 39), "clover_vein": (83, 137, 55)},
)
SNOWFLAKE_COLOR_PALETTE: Tuple[Tuple[Tuple[int, int, int], Tuple[int, int, int], Tuple[int, int, int]], ...] = (
    ((101, 174, 214), (198, 232, 244), (39, 86, 114)),
    ((83, 151, 189), (214, 239, 247), (33, 79, 106)),
    ((94, 172, 174), (204, 237, 230), (38, 91, 91)),
    ((126, 154, 213), (222, 231, 249), (57, 79, 128)),
)


@dataclass(frozen=True)
class _Defaults:
    canvas_width: int = 960
    canvas_height: int = 720
    render_scale: int = 2
    evidence_padding_px: float = 7.0
    object_scale_min: float = 0.94
    object_scale_max: float = 1.10


@dataclass(frozen=True)
class _PartSpec:
    part_id: str
    part_kind: str
    bbox: Tuple[float, float, float, float]


@dataclass(frozen=True)
class _SampleSpec:
    query_variant: str
    visible_count: int
    style_id: str
    query_variant_probabilities: Dict[str, float]
    visible_count_probabilities: Dict[str, float]
    style_probabilities: Dict[str, float]


_DEFAULTS = _Defaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("illustrations", "counterfactual")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _scale_bbox(box: Sequence[float], scale: int) -> Tuple[int, int, int, int]:
    return tuple(int(round(float(value) * int(scale))) for value in box)  # type: ignore[return-value]


def _scale_points(points: Sequence[Tuple[float, float]], scale: int) -> list[Tuple[int, int]]:
    return [(int(round(float(x) * int(scale))), int(round(float(y) * int(scale)))) for x, y in points]


def _bbox(points: Sequence[Tuple[float, float]], *, padding: float = 0.0) -> Tuple[float, float, float, float]:
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    pad = max(0.0, float(padding))
    return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)


def _rel(box: Sequence[float], x0: float, y0: float, x1: float, y1: float) -> Tuple[float, float, float, float]:
    bx0, by0, bx1, by1 = [float(value) for value in box]
    width = bx1 - bx0
    height = by1 - by0
    return (bx0 + x0 * width, by0 + y0 * height, bx0 + x1 * width, by0 + y1 * height)


def _expand(box: Sequence[float], pad: float) -> Tuple[float, float, float, float]:
    return (float(box[0]) - pad, float(box[1]) - pad, float(box[2]) + pad, float(box[3]) + pad)


def _line(draw: ImageDraw.ImageDraw, points: Sequence[Tuple[float, float]], *, fill: Tuple[int, int, int], width: int, scale: int) -> None:
    draw.line(_scale_points(points, int(scale)), fill=fill, width=max(1, int(width) * int(scale)), joint="curve")


def _ellipse(draw: ImageDraw.ImageDraw, box: Sequence[float], *, fill: Tuple[int, int, int], outline: Tuple[int, int, int], width: int, scale: int) -> None:
    draw.ellipse(_scale_bbox(box, int(scale)), fill=fill, outline=outline, width=max(1, int(width) * int(scale)))


def _rect(draw: ImageDraw.ImageDraw, box: Sequence[float], *, fill: Tuple[int, int, int], outline: Tuple[int, int, int], width: int, scale: int, radius: float = 0.0) -> None:
    scaled = _scale_bbox(box, int(scale))
    if radius > 0:
        draw.rounded_rectangle(scaled, radius=int(round(float(radius) * int(scale))), fill=fill, outline=outline, width=max(1, int(width) * int(scale)))
    else:
        draw.rectangle(scaled, fill=fill, outline=outline, width=max(1, int(width) * int(scale)))


def _poly(draw: ImageDraw.ImageDraw, points: Sequence[Tuple[float, float]], *, fill: Tuple[int, int, int], outline: Tuple[int, int, int], width: int, scale: int) -> None:
    draw.polygon(_scale_points(points, int(scale)), fill=fill)
    draw.line(_scale_points([*points, points[0]], int(scale)), fill=outline, width=max(1, int(width) * int(scale)), joint="curve")


def _support_for_variant(query_variant: str, params: Mapping[str, Any]) -> Tuple[int, ...]:
    if query_variant == BIRD_VARIANT:
        low_key, high_key, fallback = "bird_leg_count_min", "bird_leg_count_max", (1, 5)
    elif query_variant == QUADRUPED_VARIANT:
        low_key, high_key, fallback = "quadruped_leg_count_min", "quadruped_leg_count_max", (2, 6)
    elif query_variant == AIRPLANE_VARIANT:
        low_key, high_key, fallback = "airplane_wing_count_min", "airplane_wing_count_max", (1, 5)
    elif query_variant == BUTTERFLY_VARIANT:
        low_key, high_key, fallback = "butterfly_wing_count_min", "butterfly_wing_count_max", (2, 6)
    elif query_variant == BICYCLE_VARIANT:
        low_key, high_key, fallback = "bicycle_wheel_count_min", "bicycle_wheel_count_max", (1, 4)
    elif query_variant == TRAFFIC_LIGHT_VARIANT:
        low_key, high_key, fallback = "traffic_light_lens_count_min", "traffic_light_lens_count_max", (1, 5)
    elif query_variant == CLOVER_VARIANT:
        low_key, high_key, fallback = "clover_leaf_count_min", "clover_leaf_count_max", (2, 6)
    elif query_variant == STAR_VARIANT:
        low_key, high_key, fallback = "star_point_count_min", "star_point_count_max", (3, 8)
    elif query_variant == GLOVE_VARIANT:
        low_key, high_key, fallback = "glove_finger_count_min", "glove_finger_count_max", (3, 7)
    elif query_variant == FORK_VARIANT:
        low_key, high_key, fallback = "fork_tine_count_min", "fork_tine_count_max", (2, 6)
    elif query_variant == SNOWFLAKE_VARIANT:
        low_key, high_key, fallback = "snowflake_arm_count_min", "snowflake_arm_count_max", (3, 8)
    else:
        low_key, high_key, fallback = "chair_leg_count_min", "chair_leg_count_max", (2, 6)
    low = int(params.get(low_key, group_default(_GEN_DEFAULTS, low_key, fallback[0])))
    high = int(params.get(high_key, group_default(_GEN_DEFAULTS, high_key, fallback[1])))
    if low < 1 or high < low:
        raise ValueError(f"invalid visible count support for {query_variant}")
    return tuple(range(low, high + 1))


def _resolve_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    explicit = params.get("query_variant", params.get("query_id"))
    if explicit is not None:
        value = str(explicit)
        if value not in set(SUPPORTED_QUERY_VARIANTS):
            raise ValueError(f"query_variant must be one of {SUPPORTED_QUERY_VARIANTS}")
        return value, {value: 1.0}
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:query_variant")
    value = str(SUPPORTED_QUERY_VARIANTS[int(index) % len(SUPPORTED_QUERY_VARIANTS)])
    return value, {variant: 1.0 / float(len(SUPPORTED_QUERY_VARIANTS)) for variant in SUPPORTED_QUERY_VARIANTS}


def _resolve_visible_count(query_variant: str, params: Mapping[str, Any], *, instance_seed: int) -> Tuple[int, Dict[str, float]]:
    support = _support_for_variant(str(query_variant), params)
    explicit = params.get("target_answer", params.get("visible_count"))
    if explicit is not None:
        selected = int(explicit)
        if selected not in set(support):
            raise ValueError(f"visible_count must be one of {support}")
        return selected, uniform_probability_map(support, selected=selected)
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:{query_variant}:visible_count")
    selected = int(support[int(index) % len(support)])
    return selected, uniform_probability_map(support)


def _resolve_style(query_variant: str, params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    support = STYLE_SUPPORT[str(query_variant)]
    explicit = params.get("style_id")
    if explicit is not None:
        style = str(explicit)
        if style not in set(support):
            raise ValueError(f"style_id must be one of {support}")
        return style, {style: 1.0}
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}:style:{query_variant}")
    style = str(support[int(rng.randint(0, len(support) - 1))])
    return style, {value: 1.0 / float(len(support)) for value in support}


def _sample_spec(*, instance_seed: int, params: Mapping[str, Any]) -> _SampleSpec:
    query_variant, variant_probs = _resolve_variant(params, instance_seed=int(instance_seed))
    visible_count, count_probs = _resolve_visible_count(str(query_variant), params, instance_seed=int(instance_seed))
    style_id, style_probs = _resolve_style(str(query_variant), params, instance_seed=int(instance_seed))
    return _SampleSpec(
        query_variant=str(query_variant),
        visible_count=int(visible_count),
        style_id=str(style_id),
        query_variant_probabilities=dict(variant_probs),
        visible_count_probabilities={str(key): float(value) for key, value in count_probs.items()},
        style_probabilities=dict(style_probs),
    )


def _sample_colors(query_variant: str, rng: Any) -> Dict[str, Tuple[int, int, int]]:
    if query_variant == TRAFFIC_LIGHT_VARIANT:
        palette = TRAFFIC_LIGHT_COLOR_PALETTE[int(rng.randint(0, len(TRAFFIC_LIGHT_COLOR_PALETTE) - 1))]
        return {
            "primary": tuple(palette["traffic_casing"]),
            "accent": tuple(palette["traffic_pole"]),
            "outline": (38, 42, 50),
            "leg": (92, 69, 48),
            **{str(key): tuple(value) for key, value in palette.items()},
        }
    if query_variant == CLOVER_VARIANT:
        palette = CLOVER_COLOR_PALETTE[int(rng.randint(0, len(CLOVER_COLOR_PALETTE) - 1))]
        return {
            "primary": tuple(palette["clover_fill"]),
            "accent": tuple(palette["clover_accent"]),
            "outline": tuple(palette["clover_outline"]),
            "leg": (92, 69, 48),
            **{str(key): tuple(value) for key, value in palette.items()},
        }
    if query_variant == SNOWFLAKE_VARIANT:
        primary, accent, outline = SNOWFLAKE_COLOR_PALETTE[int(rng.randint(0, len(SNOWFLAKE_COLOR_PALETTE) - 1))]
        return {
            "primary": tuple(primary),
            "accent": tuple(accent),
            "outline": tuple(outline),
            "leg": (92, 69, 48),
        }
    primary, accent = OBJECT_COLOR_PALETTE[int(rng.randint(0, len(OBJECT_COLOR_PALETTE) - 1))]
    return {
        "primary": tuple(primary),
        "accent": tuple(accent),
        "outline": (38, 42, 50),
        "leg": (92, 69, 48),
    }


def _colors_for_trace(colors: Mapping[str, Tuple[int, int, int]]) -> Dict[str, list[int]]:
    return {
        str(key): [int(channel) for channel in value]
        for key, value in sorted(colors.items())
    }


def _draw_leg(
    draw: ImageDraw.ImageDraw,
    *,
    hip: Tuple[float, float],
    length: float,
    slant: float,
    part_id: str,
    color: Tuple[int, int, int],
    scale: int,
    pad: float,
    toe_span: float = 15.0,
    leg_width: int = 5,
    toe_width: int = 3,
) -> _PartSpec:
    knee = (hip[0] + float(slant) * 0.38, hip[1] + float(length) * 0.48)
    foot = (hip[0] + float(slant), hip[1] + float(length))
    _line(draw, [hip, knee, foot], fill=color, width=int(leg_width), scale=scale)
    toe_left = (foot[0] - float(toe_span), foot[1] + 2.0)
    toe_right = (foot[0] + float(toe_span), foot[1] + 2.0)
    _line(draw, [toe_left, foot, toe_right], fill=color, width=int(toe_width), scale=scale)
    return _PartSpec(part_id=str(part_id), part_kind="leg", bbox=_bbox([hip, knee, foot, toe_left, toe_right], padding=float(pad)))


def _draw_bird(draw: ImageDraw.ImageDraw, *, box: Sequence[float], style: str, visible_count: int, scale: int, pad: float, colors: Mapping[str, Tuple[int, int, int]]) -> Tuple[list[_PartSpec], Tuple[float, float, float, float]]:
    primary, accent, outline, leg_color = colors["primary"], colors["accent"], colors["outline"], colors["leg"]
    box_w = float(box[2] - box[0])
    box_h = float(box[3] - box[1])
    body = _rel(box, 0.18, 0.36, 0.74, 0.70)
    head = _rel(box, 0.65, 0.20, 0.87, 0.42)
    if style == "long_neck":
        head = _rel(box, 0.68, 0.10, 0.86, 0.28)
        _line(draw, [(body[2] - 0.042 * box_w, body[1] + 0.023 * box_h), (head[0] + 0.035 * box_w, head[3] - 0.009 * box_h)], fill=primary, width=18, scale=scale)
    wing = _rel(box, 0.38, 0.43, 0.62, 0.62)
    tail = ((box[0] + 0.20 * (box[2] - box[0]), box[1] + 0.48 * (box[3] - box[1])), (box[0] + 0.02 * (box[2] - box[0]), box[1] + 0.34 * (box[3] - box[1])), (box[0] + 0.06 * (box[2] - box[0]), box[1] + 0.62 * (box[3] - box[1])))
    beak_len = max(7.0, min(30.0, 0.055 * box_w))
    head_h = float(head[3] - head[1])
    beak_y = float(head[1] + 0.52 * head_h)
    beak_half_h = max(3.0, min(7.0, 0.08 * head_h))
    beak = ((head[2] - 2.0, beak_y - beak_half_h), (head[2] + beak_len, beak_y), (head[2] - 2.0, beak_y + beak_half_h))
    _poly(draw, tail, fill=primary, outline=outline, width=3, scale=scale)
    _ellipse(draw, body, fill=primary, outline=outline, width=3, scale=scale)
    _ellipse(draw, wing, fill=accent, outline=outline, width=2, scale=scale)
    _ellipse(draw, head, fill=primary, outline=outline, width=3, scale=scale)
    _poly(draw, beak, fill=(232, 157, 60), outline=outline, width=2, scale=scale)
    _ellipse(draw, _rel(head, 0.55, 0.32, 0.64, 0.42), fill=(20, 22, 26), outline=(20, 22, 26), width=1, scale=scale)
    parts: list[_PartSpec] = []
    span = (box[2] - box[0]) * min(0.50, 0.22 + 0.055 * int(visible_count))
    base_y = body[3] - 10.0
    for index in range(int(visible_count)):
        t = (index + 0.5) / float(visible_count)
        hip_x = (body[0] + body[2]) * 0.5 - span * 0.5 + span * t
        leg_length = box_h * (0.23 if style != "duck" else 0.19)
        leg_slant = box_w * (-0.035 + 0.070 * t)
        toe_span = max(4.0, min(10.0, 0.020 * box_w))
        parts.append(_draw_leg(draw, hip=(hip_x, base_y), length=leg_length, slant=leg_slant, part_id=f"part_{index:02d}", color=leg_color, scale=scale, pad=pad, toe_span=toe_span, leg_width=4, toe_width=3))
    return parts, _bbox([(box[0], box[1]), (box[2], box[3]), *beak], padding=8.0)


def _draw_quadruped(draw: ImageDraw.ImageDraw, *, box: Sequence[float], style: str, visible_count: int, scale: int, pad: float, colors: Mapping[str, Tuple[int, int, int]]) -> Tuple[list[_PartSpec], Tuple[float, float, float, float]]:
    primary, accent, outline, leg_color = colors["primary"], colors["accent"], colors["outline"], colors["leg"]
    box_w = float(box[2] - box[0])
    box_h = float(box[3] - box[1])
    body = _rel(box, 0.16, 0.35, 0.78, 0.64)
    head = _rel(box, 0.70, 0.22, 0.93, 0.48)
    _rect(draw, body, fill=primary, outline=outline, width=3, scale=scale, radius=28)
    _ellipse(draw, head, fill=primary, outline=outline, width=3, scale=scale)
    if style == "rabbit":
        for ear in (_rel(box, 0.75, 0.02, 0.82, 0.27), _rel(box, 0.84, 0.04, 0.91, 0.29)):
            _ellipse(draw, ear, fill=primary, outline=outline, width=2, scale=scale)
    else:
        ear_w = max(12.0, min(22.0, 0.045 * box_w))
        ear_h = max(16.0, min(28.0, 0.070 * box_h))
        ear_base_y = head[1] + 0.18 * (head[3] - head[1])
        for ear_cx in (head[0] + 0.30 * (head[2] - head[0]), head[0] + 0.56 * (head[2] - head[0])):
            ear = [(ear_cx - 0.50 * ear_w, ear_base_y), (ear_cx, ear_base_y - ear_h), (ear_cx + 0.50 * ear_w, ear_base_y)]
            _poly(draw, ear, fill=accent, outline=outline, width=2, scale=scale)
    _ellipse(draw, _rel(head, 0.56, 0.36, 0.65, 0.45), fill=(20, 22, 26), outline=(20, 22, 26), width=1, scale=scale)
    nose = _rel(box, 0.88, 0.35, 0.98, 0.45)
    _ellipse(draw, nose, fill=accent, outline=outline, width=2, scale=scale)
    tail = _rel(box, 0.05, 0.42, 0.18, 0.55)
    _ellipse(draw, tail, fill=accent, outline=outline, width=2, scale=scale)
    parts: list[_PartSpec] = []
    span = body[2] - body[0] - 30.0
    base_y = body[3] - 6.0
    for index in range(int(visible_count)):
        t = (index + 0.5) / float(visible_count)
        hip_x = body[0] + 15.0 + span * t
        leg_length = box_h * 0.25
        leg_slant = box_w * (-0.045 + 0.090 * t)
        toe_span = max(5.0, min(11.0, 0.021 * box_w))
        parts.append(_draw_leg(draw, hip=(hip_x, base_y), length=leg_length, slant=leg_slant, part_id=f"part_{index:02d}", color=leg_color, scale=scale, pad=pad, toe_span=toe_span, leg_width=5, toe_width=3))
    return parts, _bbox([(box[0], box[1]), (box[2], box[3])], padding=8.0)


def _draw_airplane(draw: ImageDraw.ImageDraw, *, box: Sequence[float], style: str, visible_count: int, scale: int, pad: float, colors: Mapping[str, Tuple[int, int, int]]) -> Tuple[list[_PartSpec], Tuple[float, float, float, float]]:
    primary, accent, outline = colors["primary"], colors["accent"], colors["outline"]
    body = _rel(box, 0.08, 0.42, 0.92, 0.58)
    nose = [(body[2] - 8, body[1]), (box[2], (body[1] + body[3]) * 0.5), (body[2] - 8, body[3])]
    _ellipse(draw, body, fill=primary, outline=outline, width=3, scale=scale)
    _poly(draw, nose, fill=primary, outline=outline, width=3, scale=scale)
    wing_boxes = (
        _rel(box, 0.35, 0.14, 0.61, 0.43),
        _rel(box, 0.41, 0.57, 0.67, 0.86),
        _rel(box, 0.56, 0.20, 0.76, 0.43),
        _rel(box, 0.59, 0.57, 0.79, 0.80),
        _rel(box, 0.20, 0.24, 0.42, 0.43),
    )
    parts: list[_PartSpec] = []
    for index, wing_box in enumerate(wing_boxes[: int(visible_count)]):
        if index % 2 == 0:
            points = [(wing_box[2], wing_box[3]), (wing_box[0], wing_box[1]), (wing_box[0] + 0.30 * (wing_box[2] - wing_box[0]), wing_box[3])]
        else:
            points = [(wing_box[2], wing_box[1]), (wing_box[0], wing_box[3]), (wing_box[0] + 0.30 * (wing_box[2] - wing_box[0]), wing_box[1])]
        _poly(draw, points, fill=accent, outline=outline, width=3, scale=scale)
        parts.append(_PartSpec(part_id=f"part_{index:02d}", part_kind="wing", bbox=_expand(wing_box, pad)))
    for index in range(4):
        win = _rel(box, 0.47 + 0.07 * index, 0.46, 0.51 + 0.07 * index, 0.51)
        _ellipse(draw, win, fill=(215, 237, 247), outline=outline, width=1, scale=scale)
    return parts, _bbox([(box[0], box[1]), (box[2], box[3])], padding=8.0)


def _draw_butterfly(draw: ImageDraw.ImageDraw, *, box: Sequence[float], style: str, visible_count: int, scale: int, pad: float, colors: Mapping[str, Tuple[int, int, int]]) -> Tuple[list[_PartSpec], Tuple[float, float, float, float]]:
    primary, accent, outline = colors["primary"], colors["accent"], colors["outline"]
    candidates = (
        _rel(box, 0.09, 0.10, 0.44, 0.45),
        _rel(box, 0.56, 0.10, 0.91, 0.45),
        _rel(box, 0.15, 0.47, 0.45, 0.84),
        _rel(box, 0.55, 0.47, 0.85, 0.84),
        _rel(box, 0.02, 0.34, 0.35, 0.65),
        _rel(box, 0.65, 0.34, 0.98, 0.65),
    )
    parts: list[_PartSpec] = []
    for index, wing_box in enumerate(candidates[: int(visible_count)]):
        if style == "pointed":
            cx = (wing_box[0] + wing_box[2]) * 0.5
            points = [(cx, wing_box[1]), (wing_box[2], (wing_box[1] + wing_box[3]) * 0.5), (cx, wing_box[3]), (wing_box[0], (wing_box[1] + wing_box[3]) * 0.5)]
            _poly(draw, points, fill=accent, outline=outline, width=3, scale=scale)
        else:
            _ellipse(draw, wing_box, fill=accent, outline=outline, width=3, scale=scale)
        parts.append(_PartSpec(part_id=f"part_{index:02d}", part_kind="wing", bbox=_expand(wing_box, pad)))
    body = _rel(box, 0.45, 0.18, 0.55, 0.84)
    head = _rel(box, 0.43, 0.10, 0.57, 0.24)
    _ellipse(draw, body, fill=primary, outline=outline, width=3, scale=scale)
    _ellipse(draw, head, fill=primary, outline=outline, width=3, scale=scale)
    _line(draw, [(head[0] + 14, head[1] + 8), (head[0] - 18, head[1] - 26)], fill=outline, width=3, scale=scale)
    _line(draw, [(head[2] - 14, head[1] + 8), (head[2] + 18, head[1] - 26)], fill=outline, width=3, scale=scale)
    return parts, _bbox([(box[0], box[1]), (box[2], box[3])], padding=8.0)


def _draw_bicycle(draw: ImageDraw.ImageDraw, *, box: Sequence[float], style: str, visible_count: int, scale: int, pad: float, colors: Mapping[str, Tuple[int, int, int]]) -> Tuple[list[_PartSpec], Tuple[float, float, float, float]]:
    primary, accent, outline = colors["primary"], colors["accent"], colors["outline"]
    x0, y0, x1, y1 = [float(value) for value in box]
    width = x1 - x0
    height = y1 - y0
    wheel_count = max(1, int(visible_count))
    wheel_r = min(44.0, max(22.0, width / (2.7 * float(wheel_count))), height * 0.18)
    base_y = y0 + 0.72 * height
    if wheel_count == 1:
        centers = [x0 + 0.50 * width]
    else:
        margin = max(0.12 * width, wheel_r + 16.0)
        step = (width - 2.0 * margin) / float(wheel_count - 1)
        centers = [x0 + margin + step * index for index in range(wheel_count)]

    parts: list[_PartSpec] = []
    for index, cx in enumerate(centers):
        wheel_box = (cx - wheel_r, base_y - wheel_r, cx + wheel_r, base_y + wheel_r)
        _ellipse(draw, wheel_box, fill=(231, 239, 242), outline=outline, width=4, scale=scale)
        inner = (cx - 0.55 * wheel_r, base_y - 0.55 * wheel_r, cx + 0.55 * wheel_r, base_y + 0.55 * wheel_r)
        _ellipse(draw, inner, fill=(248, 251, 252), outline=(102, 112, 122), width=2, scale=scale)
        for angle in (0.0, math.pi / 3.0, 2.0 * math.pi / 3.0):
            dx = math.cos(angle) * wheel_r * 0.78
            dy = math.sin(angle) * wheel_r * 0.78
            _line(draw, [(cx - dx, base_y - dy), (cx + dx, base_y + dy)], fill=(116, 126, 136), width=1, scale=scale)
        parts.append(_PartSpec(part_id=f"part_{index:02d}", part_kind="wheel", bbox=_expand(wheel_box, pad)))

    frame_left = min(centers) if len(centers) > 1 else x0 + 0.30 * width
    frame_right = max(centers) if len(centers) > 1 else x0 + 0.70 * width
    mid = (frame_left + frame_right) * 0.5
    seat = (mid - 0.06 * width, y0 + 0.38 * height)
    handle = (frame_right + 0.08 * width, y0 + 0.34 * height)
    fork_top = (frame_right - 0.08 * width, y0 + 0.45 * height)
    crank = (mid, y0 + 0.58 * height)
    _line(draw, [(frame_left, base_y), seat, (frame_right, base_y), crank, (frame_left, base_y)], fill=primary, width=5, scale=scale)
    _line(draw, [seat, crank, fork_top, handle], fill=primary, width=5, scale=scale)
    _line(draw, [(seat[0] - 0.055 * width, seat[1] - 0.018 * height), (seat[0] + 0.055 * width, seat[1] - 0.018 * height)], fill=outline, width=5, scale=scale)
    _line(draw, [handle, (handle[0] + 0.045 * width, handle[1] - 0.020 * height)], fill=accent, width=4, scale=scale)
    if style == "cargo":
        basket = (frame_right + 0.04 * width, y0 + 0.39 * height, frame_right + 0.20 * width, y0 + 0.54 * height)
        _rect(draw, basket, fill=accent, outline=outline, width=2, scale=scale, radius=5)
    elif style == "step_through":
        _line(draw, [(frame_left, base_y), (mid - 0.03 * width, y0 + 0.50 * height), (frame_right, base_y)], fill=accent, width=4, scale=scale)
    return parts, _bbox([(box[0], box[1]), (box[2], box[3])], padding=8.0)


def _draw_traffic_light(draw: ImageDraw.ImageDraw, *, box: Sequence[float], style: str, visible_count: int, scale: int, pad: float, colors: Mapping[str, Tuple[int, int, int]]) -> Tuple[list[_PartSpec], Tuple[float, float, float, float]]:
    outline = tuple(colors.get("outline", (38, 42, 50)))
    casing_fill = tuple(colors.get("traffic_casing", (65, 72, 80)))
    pole_fill = tuple(colors.get("traffic_pole", (96, 104, 112)))
    hood_fill = tuple(colors.get("traffic_hood", (44, 50, 56)))
    x0, y0, x1, y1 = [float(value) for value in box]
    width = x1 - x0
    height = y1 - y0
    lens_count = max(1, int(visible_count))
    cx = (x0 + x1) * 0.5
    gap_factor = 0.12
    casing_pad_y = max(14.0, min(22.0, 0.12 * height))
    usable_h = 0.88 * height
    stack_factor = float(lens_count) + gap_factor * float(max(0, lens_count - 1))
    fit_d = max(9.0, (usable_h - casing_pad_y) / max(1.0, stack_factor))
    lens_d = min(width * 0.72, fit_d, 52.0)
    gap = lens_d * gap_factor
    casing_h = lens_count * lens_d + max(0, lens_count - 1) * gap + casing_pad_y
    casing_w = lens_d * 1.85
    top = y0 + 0.04 * height
    bottom = top + casing_h
    casing = (cx - casing_w * 0.5, top, cx + casing_w * 0.5, bottom)
    pole_bottom = max(bottom + 10.0, min(y1 - 0.10 * height, bottom + 0.18 * height))
    pole = (cx - 8.0, bottom - 2.0, cx + 8.0, pole_bottom)
    _rect(draw, pole, fill=pole_fill, outline=outline, width=2, scale=scale, radius=3)
    if style == "signal_post":
        _line(draw, [(cx, top + 0.20 * casing_h), (x0 + 0.18 * width, top + 0.20 * casing_h)], fill=pole_fill, width=6, scale=scale)
    _rect(draw, casing, fill=casing_fill, outline=outline, width=4, scale=scale, radius=18 if style == "rounded" else 8)
    parts: list[_PartSpec] = []
    start_y = top + 0.5 * casing_pad_y + lens_d * 0.5
    for index in range(lens_count):
        cy = start_y + index * (lens_d + gap)
        lens_box = (cx - lens_d * 0.5, cy - lens_d * 0.5, cx + lens_d * 0.5, cy + lens_d * 0.5)
        hood = (lens_box[0] - 8.0, lens_box[1] - 5.0, lens_box[2] + 8.0, lens_box[1] + 0.24 * lens_d)
        _rect(draw, hood, fill=hood_fill, outline=outline, width=1, scale=scale, radius=5)
        _ellipse(draw, lens_box, fill=TRAFFIC_LENS_COLORS[index % len(TRAFFIC_LENS_COLORS)], outline=outline, width=3, scale=scale)
        highlight = (lens_box[0] + 0.18 * lens_d, lens_box[1] + 0.18 * lens_d, lens_box[0] + 0.40 * lens_d, lens_box[1] + 0.40 * lens_d)
        _ellipse(draw, highlight, fill=(249, 241, 210), outline=(249, 241, 210), width=1, scale=scale)
        parts.append(_PartSpec(part_id=f"part_{index:02d}", part_kind="lens", bbox=_expand(lens_box, pad)))
    return parts, _bbox([(box[0], box[1]), (box[2], box[3])], padding=8.0)


def _draw_clover_leaf(
    draw: ImageDraw.ImageDraw,
    *,
    leaf_box: Sequence[float],
    style: str,
    angle: float,
    fill: Tuple[int, int, int],
    outline: Tuple[int, int, int],
    scale: int,
) -> None:
    x0, y0, x1, y1 = [float(value) for value in leaf_box]
    if style == "heart_leaf":
        cx = (x0 + x1) * 0.5
        cy = (y0 + y1) * 0.5
        width = x1 - x0
        height = y1 - y0
        ux = math.cos(float(angle))
        uy = math.sin(float(angle))
        px = -uy
        py = ux
        point = (cx - ux * 0.46 * height, cy - uy * 0.46 * height)
        outer = (cx + ux * 0.20 * height, cy + uy * 0.20 * height)
        lobe_r = min(0.25 * width, 0.25 * height)
        lobe_a = (outer[0] + px * 0.22 * width, outer[1] + py * 0.22 * width)
        lobe_b = (outer[0] - px * 0.22 * width, outer[1] - py * 0.22 * width)
        bridge = (outer[0] + ux * 0.20 * height, outer[1] + uy * 0.20 * height)
        _ellipse(draw, (lobe_a[0] - lobe_r, lobe_a[1] - lobe_r, lobe_a[0] + lobe_r, lobe_a[1] + lobe_r), fill=fill, outline=outline, width=2, scale=scale)
        _ellipse(draw, (lobe_b[0] - lobe_r, lobe_b[1] - lobe_r, lobe_b[0] + lobe_r, lobe_b[1] + lobe_r), fill=fill, outline=outline, width=2, scale=scale)
        _poly(draw, [lobe_a, bridge, lobe_b, point], fill=fill, outline=outline, width=2, scale=scale)
    elif style == "wide_leaf":
        _ellipse(draw, (x0 - 0.10 * (x1 - x0), y0 + 0.10 * (y1 - y0), x1 + 0.10 * (x1 - x0), y1 - 0.04 * (y1 - y0)), fill=fill, outline=outline, width=2, scale=scale)
    else:
        _ellipse(draw, leaf_box, fill=fill, outline=outline, width=2, scale=scale)


def _draw_clover(draw: ImageDraw.ImageDraw, *, box: Sequence[float], style: str, visible_count: int, scale: int, pad: float, colors: Mapping[str, Tuple[int, int, int]]) -> Tuple[list[_PartSpec], Tuple[float, float, float, float]]:
    x0, y0, x1, y1 = [float(value) for value in box]
    width = x1 - x0
    height = y1 - y0
    leaf_count = max(1, int(visible_count))
    outline = tuple(colors.get("clover_outline", (42, 82, 50)))
    fill = tuple(colors.get("clover_fill", (79, 161, 89)))
    accent = tuple(colors.get("clover_accent", (46, 125, 65)))
    vein = tuple(colors.get("clover_vein", (54, 132, 68)))
    center = ((x0 + x1) * 0.5, y0 + 0.48 * height)
    stem_end = (center[0] + 0.10 * width, y1 - 0.10 * height)
    _line(draw, [center, stem_end], fill=accent, width=6, scale=scale)
    leaf_w = min(86.0, width * (0.26 if leaf_count <= 4 else 0.22))
    leaf_h = min(78.0, height * (0.24 if leaf_count <= 4 else 0.20))
    radius_x = width * (0.20 if leaf_count <= 4 else 0.22)
    radius_y = height * (0.18 if leaf_count <= 4 else 0.20)
    parts: list[_PartSpec] = []
    for index in range(leaf_count):
        angle = -math.pi / 2.0 + 2.0 * math.pi * float(index) / float(leaf_count)
        cx = center[0] + math.cos(angle) * radius_x
        cy = center[1] + math.sin(angle) * radius_y
        leaf_box = (cx - leaf_w * 0.5, cy - leaf_h * 0.5, cx + leaf_w * 0.5, cy + leaf_h * 0.5)
        _draw_clover_leaf(draw, leaf_box=leaf_box, style=style, angle=angle, fill=fill, outline=outline, scale=scale)
        vein_end = (cx, cy)
        _line(draw, [center, vein_end], fill=vein, width=2, scale=scale)
        parts.append(_PartSpec(part_id=f"part_{index:02d}", part_kind="leaf", bbox=_expand(leaf_box, pad)))
    _ellipse(draw, (center[0] - 9.0, center[1] - 9.0, center[0] + 9.0, center[1] + 9.0), fill=accent, outline=outline, width=2, scale=scale)
    return parts, _bbox([(box[0], box[1]), (box[2], box[3])], padding=8.0)


def _draw_star(draw: ImageDraw.ImageDraw, *, box: Sequence[float], style: str, visible_count: int, scale: int, pad: float, colors: Mapping[str, Tuple[int, int, int]]) -> Tuple[list[_PartSpec], Tuple[float, float, float, float]]:
    primary, accent, outline = colors["primary"], colors["accent"], colors["outline"]
    x0, y0, x1, y1 = [float(value) for value in box]
    width = x1 - x0
    height = y1 - y0
    point_count = max(3, int(visible_count))
    center = ((x0 + x1) * 0.5, y0 + 0.52 * height)
    outer_r = min(width, height) * (0.43 if style != "sharp" else 0.46)
    inner_r = outer_r * (0.34 if style == "sharp" else 0.42)
    parts: list[_PartSpec] = []

    def point(radius: float, angle: float) -> Tuple[float, float]:
        return (center[0] + math.cos(angle) * radius, center[1] + math.sin(angle) * radius)

    for index in range(point_count):
        angle = -math.pi / 2.0 + 2.0 * math.pi * float(index) / float(point_count)
        half_width = math.pi / float(point_count) * (0.54 if style == "sharp" else 0.62)
        tip = point(outer_r, angle)
        left = point(inner_r, angle - half_width)
        right = point(inner_r, angle + half_width)
        _poly(draw, [tip, left, right], fill=accent, outline=outline, width=3, scale=scale)
        if style == "soft":
            tip_dot_r = outer_r * 0.050
            _ellipse(draw, (tip[0] - tip_dot_r, tip[1] - tip_dot_r, tip[0] + tip_dot_r, tip[1] + tip_dot_r), fill=accent, outline=outline, width=1, scale=scale)
        parts.append(_PartSpec(part_id=f"part_{index:02d}", part_kind="point", bbox=_bbox([tip, left, right], padding=pad)))

    if style == "classic":
        center_poly = [point(inner_r * 0.92, -math.pi / 2.0 + 2.0 * math.pi * float(index) / float(point_count)) for index in range(point_count)]
        _poly(draw, center_poly, fill=primary, outline=outline, width=3, scale=scale)
    else:
        body_r = inner_r * (0.90 if style == "sharp" else 1.05)
        _ellipse(draw, (center[0] - body_r, center[1] - body_r, center[0] + body_r, center[1] + body_r), fill=primary, outline=outline, width=3, scale=scale)
    return parts, _bbox([(x0, y0), (x1, y1)], padding=8.0)


def _draw_glove(draw: ImageDraw.ImageDraw, *, box: Sequence[float], style: str, visible_count: int, scale: int, pad: float, colors: Mapping[str, Tuple[int, int, int]]) -> Tuple[list[_PartSpec], Tuple[float, float, float, float]]:
    primary, accent, outline = colors["primary"], colors["accent"], colors["outline"]
    x0, y0, x1, y1 = [float(value) for value in box]
    width = x1 - x0
    height = y1 - y0
    finger_count = max(1, int(visible_count))
    palm = (x0 + 0.22 * width, y0 + 0.38 * height, x1 - 0.20 * width, y0 + 0.79 * height)
    cuff = (x0 + 0.29 * width, y0 + 0.76 * height, x1 - 0.27 * width, y0 + 0.93 * height)
    finger_span = palm[2] - palm[0]
    gap = finger_span * 0.018
    finger_w = min(width * 0.13, max(width * 0.060, (finger_span - gap * float(finger_count - 1)) / float(finger_count + 0.35)))
    base_y = palm[1] + 0.10 * height
    top_base = y0 + (0.08 if style == "sport" else 0.10) * height
    centers: list[float]
    if finger_count == 1:
        centers = [(palm[0] + palm[2]) * 0.5]
    else:
        usable = finger_span - finger_w
        centers = [palm[0] + finger_w * 0.5 + usable * float(index) / float(finger_count - 1) for index in range(finger_count)]
    parts: list[_PartSpec] = []
    for index, cx in enumerate(centers):
        centered = 1.0 - abs((float(index) + 0.5) / float(finger_count) - 0.5) * 1.65
        finger_h = height * (0.27 + 0.065 * max(0.0, centered))
        top = top_base + height * 0.03 * (float(index % 2) if style == "work" else 0.0)
        finger_box = (cx - finger_w * 0.5, min(base_y - finger_h, top), cx + finger_w * 0.5, base_y + 0.03 * height)
        _rect(draw, finger_box, fill=primary, outline=outline, width=3, scale=scale, radius=finger_w * (0.42 if style != "work" else 0.24))
        if style == "sport":
            stripe_y = finger_box[1] + 0.30 * (finger_box[3] - finger_box[1])
            _line(draw, [(finger_box[0] + 0.15 * finger_w, stripe_y), (finger_box[2] - 0.15 * finger_w, stripe_y)], fill=accent, width=2, scale=scale)
        parts.append(_PartSpec(part_id=f"part_{index:02d}", part_kind="finger", bbox=_expand(finger_box, pad)))

    _rect(draw, palm, fill=primary, outline=outline, width=3, scale=scale, radius=24 if style != "work" else 12)
    if style == "cartoon":
        _ellipse(draw, _rel(palm, 0.34, 0.20, 0.67, 0.50), fill=accent, outline=outline, width=2, scale=scale)
    elif style == "work":
        _line(draw, [(palm[0] + 0.14 * finger_span, palm[1] + 0.25 * height), (palm[2] - 0.14 * finger_span, palm[1] + 0.25 * height)], fill=accent, width=3, scale=scale)
    else:
        _ellipse(draw, _rel(palm, 0.40, 0.18, 0.64, 0.42), fill=accent, outline=outline, width=2, scale=scale)
    _rect(draw, cuff, fill=accent, outline=outline, width=3, scale=scale, radius=10)
    return parts, _bbox([(x0, y0), (x1, y1)], padding=8.0)


def _draw_fork(draw: ImageDraw.ImageDraw, *, box: Sequence[float], style: str, visible_count: int, scale: int, pad: float, colors: Mapping[str, Tuple[int, int, int]]) -> Tuple[list[_PartSpec], Tuple[float, float, float, float]]:
    primary, accent, outline = colors["primary"], colors["accent"], colors["outline"]
    x0, y0, x1, y1 = [float(value) for value in box]
    width = x1 - x0
    height = y1 - y0
    tine_count = max(1, int(visible_count))
    cx = (x0 + x1) * 0.5
    handle = (cx - 0.065 * width, y0 + 0.42 * height, cx + 0.065 * width, y1 - 0.06 * height)
    neck = (cx - 0.20 * width, y0 + 0.36 * height, cx + 0.20 * width, y0 + 0.50 * height)
    _rect(draw, handle, fill=primary, outline=outline, width=3, scale=scale, radius=14)
    _rect(draw, neck, fill=primary, outline=outline, width=3, scale=scale, radius=8)
    head_w = width * (0.58 if style != "wide" else 0.70)
    gap = head_w * 0.045
    tine_w = min(width * 0.095, max(width * 0.038, (head_w - gap * float(tine_count - 1)) / float(tine_count)))
    total_w = tine_w * float(tine_count) + gap * float(max(0, tine_count - 1))
    start_x = cx - total_w * 0.5
    tine_top = y0 + 0.08 * height
    tine_bottom = y0 + 0.41 * height
    parts: list[_PartSpec] = []
    for index in range(tine_count):
        tx0 = start_x + float(index) * (tine_w + gap)
        tine_box = (tx0, tine_top, tx0 + tine_w, tine_bottom)
        radius = tine_w * (0.45 if style == "rounded" else 0.16)
        _rect(draw, tine_box, fill=accent, outline=outline, width=2, scale=scale, radius=radius)
        parts.append(_PartSpec(part_id=f"part_{index:02d}", part_kind="tine", bbox=_expand(tine_box, pad)))
    return parts, _bbox([(x0, y0), (x1, y1)], padding=8.0)


def _draw_snowflake(draw: ImageDraw.ImageDraw, *, box: Sequence[float], style: str, visible_count: int, scale: int, pad: float, colors: Mapping[str, Tuple[int, int, int]]) -> Tuple[list[_PartSpec], Tuple[float, float, float, float]]:
    primary, accent, outline = colors["primary"], colors["accent"], colors["outline"]
    x0, y0, x1, y1 = [float(value) for value in box]
    width = x1 - x0
    height = y1 - y0
    arm_count = max(3, int(visible_count))
    center = ((x0 + x1) * 0.5, y0 + 0.52 * height)
    radius = min(width, height) * 0.42
    inner_radius = radius * 0.19
    parts: list[_PartSpec] = []
    for index in range(arm_count):
        angle = -math.pi / 2.0 + 2.0 * math.pi * float(index) / float(arm_count)
        end = (center[0] + math.cos(angle) * radius, center[1] + math.sin(angle) * radius)
        root = (center[0] + math.cos(angle) * inner_radius, center[1] + math.sin(angle) * inner_radius)
        _line(draw, [center, end], fill=outline, width=7, scale=scale)
        _line(draw, [center, end], fill=primary, width=4, scale=scale)
        arm_points = [center, root, end]
        branch_sets = {
            "simple": (0.66,),
            "branched": (0.48, 0.70),
            "crystal": (0.42, 0.62, 0.80),
        }.get(style, (0.62,))
        for frac in branch_sets:
            branch_base = (center[0] + (end[0] - center[0]) * float(frac), center[1] + (end[1] - center[1]) * float(frac))
            branch_len = radius * (0.14 if style == "simple" else (0.17 if style == "branched" else 0.13))
            for sign in (-1.0, 1.0):
                branch_angle = angle + sign * math.radians(45.0)
                branch_end = (branch_base[0] + math.cos(branch_angle) * branch_len, branch_base[1] + math.sin(branch_angle) * branch_len)
                _line(draw, [branch_base, branch_end], fill=outline, width=4, scale=scale)
                _line(draw, [branch_base, branch_end], fill=accent, width=2, scale=scale)
                arm_points.append(branch_end)
        tip_r = radius * (0.045 if style != "crystal" else 0.035)
        if style == "crystal":
            side_r = radius * 0.050
            side_a = angle + math.pi * 0.5
            diamond = [
                (end[0] + math.cos(angle) * side_r, end[1] + math.sin(angle) * side_r),
                (end[0] + math.cos(side_a) * side_r, end[1] + math.sin(side_a) * side_r),
                (end[0] - math.cos(angle) * side_r, end[1] - math.sin(angle) * side_r),
                (end[0] - math.cos(side_a) * side_r, end[1] - math.sin(side_a) * side_r),
            ]
            _poly(draw, diamond, fill=accent, outline=outline, width=1, scale=scale)
            arm_points.extend(diamond)
        else:
            _ellipse(draw, (end[0] - tip_r, end[1] - tip_r, end[0] + tip_r, end[1] + tip_r), fill=accent, outline=outline, width=1, scale=scale)
            arm_points.extend([(end[0] - tip_r, end[1] - tip_r), (end[0] + tip_r, end[1] + tip_r)])
        parts.append(_PartSpec(part_id=f"part_{index:02d}", part_kind="arm", bbox=_bbox(arm_points, padding=pad)))
    center_r = radius * 0.13
    _ellipse(draw, (center[0] - center_r, center[1] - center_r, center[0] + center_r, center[1] + center_r), fill=accent, outline=outline, width=2, scale=scale)
    hub_r = radius * 0.055
    _ellipse(draw, (center[0] - hub_r, center[1] - hub_r, center[0] + hub_r, center[1] + hub_r), fill=primary, outline=outline, width=1, scale=scale)
    return parts, _bbox([(x0, y0), (x1, y1)], padding=8.0)


def _draw_chair(draw: ImageDraw.ImageDraw, *, box: Sequence[float], style: str, visible_count: int, scale: int, pad: float, colors: Mapping[str, Tuple[int, int, int]]) -> Tuple[list[_PartSpec], Tuple[float, float, float, float]]:
    primary, accent, outline, leg_color = colors["primary"], colors["accent"], colors["outline"], colors["leg"]
    x0, y0, x1, y1 = [float(value) for value in box]
    width = x1 - x0
    height = y1 - y0
    leg_count = max(1, int(visible_count))
    back = (x0 + 0.20 * width, y0 + 0.13 * height, x1 - 0.20 * width, y0 + 0.51 * height)
    seat = (x0 + 0.15 * width, y0 + 0.48 * height, x1 - 0.15 * width, y0 + 0.64 * height)
    leg_top_y = seat[3] - 0.02 * height
    leg_bottom_y = y1 - 0.08 * height
    span = seat[2] - seat[0]
    if leg_count == 1:
        centers = [(seat[0] + seat[2]) * 0.5]
    else:
        centers = [seat[0] + 0.10 * span + 0.80 * span * float(index) / float(leg_count - 1) for index in range(leg_count)]
    parts: list[_PartSpec] = []
    for index, lx in enumerate(centers):
        t = (float(index) + 0.5) / float(leg_count)
        foot_x = lx + (t - 0.5) * 0.11 * width
        knee = ((lx + foot_x) * 0.5, leg_top_y + 0.45 * (leg_bottom_y - leg_top_y))
        foot = (foot_x, leg_bottom_y)
        _line(draw, [(lx, leg_top_y), knee, foot], fill=leg_color, width=7, scale=scale)
        _line(draw, [(foot[0] - 0.035 * width, foot[1]), (foot[0] + 0.035 * width, foot[1])], fill=leg_color, width=4, scale=scale)
        parts.append(_PartSpec(part_id=f"part_{index:02d}", part_kind="leg", bbox=_bbox([(lx, leg_top_y), knee, foot, (foot[0] - 0.035 * width, foot[1]), (foot[0] + 0.035 * width, foot[1])], padding=pad)))

    if style == "wooden":
        for rail_x in (back[0] + 0.18 * (back[2] - back[0]), back[2] - 0.18 * (back[2] - back[0])):
            _line(draw, [(rail_x, back[1]), (rail_x, back[3])], fill=accent, width=8, scale=scale)
        _rect(draw, (back[0], back[1], back[2], back[1] + 0.18 * height), fill=primary, outline=outline, width=3, scale=scale, radius=8)
    else:
        _rect(draw, back, fill=primary, outline=outline, width=3, scale=scale, radius=18 if style == "cushioned" else 9)
        if style == "cushioned":
            _rect(draw, _rel(back, 0.12, 0.14, 0.88, 0.82), fill=accent, outline=outline, width=2, scale=scale, radius=14)
    _rect(draw, seat, fill=primary, outline=outline, width=3, scale=scale, radius=14 if style == "cushioned" else 7)
    if style == "cushioned":
        _rect(draw, _rel(seat, 0.08, 0.18, 0.92, 0.78), fill=accent, outline=outline, width=2, scale=scale, radius=10)
    return parts, _bbox([(x0, y0), (x1, y1)], padding=8.0)


def _render_scene(sample: _SampleSpec, *, instance_seed: int, params: Mapping[str, Any]) -> Tuple[Image.Image, list[_PartSpec], Dict[str, Any], Tuple[float, float, float, float]]:
    width = int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width)))
    height = int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height)))
    scale = int(params.get("render_scale", group_default(_RENDER_DEFAULTS, "render_scale", _DEFAULTS.render_scale)))
    pad = float(params.get("evidence_padding_px", group_default(_RENDER_DEFAULTS, "evidence_padding_px", _DEFAULTS.evidence_padding_px)))
    scale_min = float(params.get("object_scale_min", group_default(_RENDER_DEFAULTS, "object_scale_min", _DEFAULTS.object_scale_min)))
    scale_max = float(params.get("object_scale_max", group_default(_RENDER_DEFAULTS, "object_scale_max", _DEFAULTS.object_scale_max)))
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}:render:{sample.query_variant}:{sample.visible_count}:{sample.style_id}")
    image = Image.new("RGB", (width * scale, height * scale), (238, 246, 252))
    draw = ImageDraw.Draw(image)
    horizon = int(height * float(rng.uniform(0.68, 0.76)))
    draw.rectangle((0, horizon * scale, width * scale, height * scale), fill=(222, 232, 218))
    for x in range(0, width, 120):
        draw.ellipse((int((x + 18) * scale), int((horizon + 28) * scale), int((x + 74) * scale), int((horizon + 56) * scale)), fill=(205, 222, 198))
    object_scale = float(rng.uniform(scale_min, scale_max))
    if sample.query_variant == AIRPLANE_VARIANT:
        base_w, base_h = 520.0, 360.0
    elif sample.query_variant == BUTTERFLY_VARIANT:
        base_w, base_h = 430.0, 430.0
    elif sample.query_variant == BICYCLE_VARIANT:
        base_w, base_h = 560.0, 360.0
    elif sample.query_variant == TRAFFIC_LIGHT_VARIANT:
        base_w, base_h = 300.0, 500.0
    elif sample.query_variant == CLOVER_VARIANT:
        base_w, base_h = 430.0, 430.0
    elif sample.query_variant == STAR_VARIANT:
        base_w, base_h = 440.0, 440.0
    elif sample.query_variant == GLOVE_VARIANT:
        base_w, base_h = 430.0, 470.0
    elif sample.query_variant == FORK_VARIANT:
        base_w, base_h = 340.0, 520.0
    elif sample.query_variant == SNOWFLAKE_VARIANT:
        base_w, base_h = 460.0, 460.0
    elif sample.query_variant == CHAIR_VARIANT:
        base_w, base_h = 430.0, 500.0
    else:
        base_w, base_h = 520.0, 430.0
    box_w = base_w * object_scale
    box_h = base_h * object_scale
    cx = width * float(rng.uniform(0.49, 0.53))
    cy = height * float(rng.uniform(0.44, 0.48))
    box = (cx - box_w * 0.5, cy - box_h * 0.5, cx + box_w * 0.5, cy + box_h * 0.5)
    colors = _sample_colors(str(sample.query_variant), rng)
    if sample.query_variant == BIRD_VARIANT:
        parts, object_bbox = _draw_bird(draw, box=box, style=sample.style_id, visible_count=sample.visible_count, scale=scale, pad=pad, colors=colors)
    elif sample.query_variant == QUADRUPED_VARIANT:
        parts, object_bbox = _draw_quadruped(draw, box=box, style=sample.style_id, visible_count=sample.visible_count, scale=scale, pad=pad, colors=colors)
    elif sample.query_variant == AIRPLANE_VARIANT:
        parts, object_bbox = _draw_airplane(draw, box=box, style=sample.style_id, visible_count=sample.visible_count, scale=scale, pad=pad, colors=colors)
    elif sample.query_variant == BUTTERFLY_VARIANT:
        parts, object_bbox = _draw_butterfly(draw, box=box, style=sample.style_id, visible_count=sample.visible_count, scale=scale, pad=pad, colors=colors)
    elif sample.query_variant == BICYCLE_VARIANT:
        parts, object_bbox = _draw_bicycle(draw, box=box, style=sample.style_id, visible_count=sample.visible_count, scale=scale, pad=pad, colors=colors)
    elif sample.query_variant == TRAFFIC_LIGHT_VARIANT:
        parts, object_bbox = _draw_traffic_light(draw, box=box, style=sample.style_id, visible_count=sample.visible_count, scale=scale, pad=pad, colors=colors)
    elif sample.query_variant == CLOVER_VARIANT:
        parts, object_bbox = _draw_clover(draw, box=box, style=sample.style_id, visible_count=sample.visible_count, scale=scale, pad=pad, colors=colors)
    elif sample.query_variant == STAR_VARIANT:
        parts, object_bbox = _draw_star(draw, box=box, style=sample.style_id, visible_count=sample.visible_count, scale=scale, pad=pad, colors=colors)
    elif sample.query_variant == GLOVE_VARIANT:
        parts, object_bbox = _draw_glove(draw, box=box, style=sample.style_id, visible_count=sample.visible_count, scale=scale, pad=pad, colors=colors)
    elif sample.query_variant == FORK_VARIANT:
        parts, object_bbox = _draw_fork(draw, box=box, style=sample.style_id, visible_count=sample.visible_count, scale=scale, pad=pad, colors=colors)
    elif sample.query_variant == SNOWFLAKE_VARIANT:
        parts, object_bbox = _draw_snowflake(draw, box=box, style=sample.style_id, visible_count=sample.visible_count, scale=scale, pad=pad, colors=colors)
    else:
        parts, object_bbox = _draw_chair(draw, box=box, style=sample.style_id, visible_count=sample.visible_count, scale=scale, pad=pad, colors=colors)
    small = image.resize((width, height), Image.Resampling.LANCZOS)
    render_meta = {
        "canvas_width": int(width),
        "canvas_height": int(height),
        "render_scale": int(scale),
        "style_id": str(sample.style_id),
        "object_scale": round(float(object_scale), 4),
        "horizon_y_px": int(horizon),
        "colors_rgb": _colors_for_trace(colors),
    }
    if sample.query_variant == TRAFFIC_LIGHT_VARIANT:
        render_meta["traffic_lens_color_policy"] = "fixed_signal_order"
        render_meta["traffic_lens_colors_rgb"] = [
            [int(channel) for channel in TRAFFIC_LENS_COLORS[index % len(TRAFFIC_LENS_COLORS)]]
            for index in range(int(sample.visible_count))
        ]
    return small, sorted(parts, key=lambda part: (part.bbox[0], part.bbox[1])), render_meta, object_bbox


def _build_complexity(sample: _SampleSpec) -> TaskComplexity:
    support = _support_for_variant(sample.query_variant, {})
    answer_load = (int(sample.visible_count) - min(support)) / max(1, max(support) - min(support))
    return TaskComplexity(
        complexity_score=round(0.36 + 0.30 * float(answer_load), 3),
        complexity_components={
            "single_object": 1.0,
            "visible_count": float(sample.visible_count),
            "answer_load": round(float(answer_load), 3),
        },
    )


@register_task
class IllustrationsCounterfactualVisiblePartCountTask:
    """Count visible parts on a single counterfactual illustration object."""

    task_id = TASK_ID
    domain = "illustrations"
    task_group = "counterfactual"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        sample = _sample_spec(instance_seed=int(instance_seed), params=params)
        image, parts, render_meta, object_bbox = _render_scene(sample, instance_seed=int(instance_seed), params=params)
        evidence_boxes = [[round(float(value), 3) for value in part.bbox] for part in parts]
        part_records = [
            {
                "entity_id": str(part.part_id),
                "entity_type": f"visible_{part.part_kind}",
                "part_kind": str(part.part_kind),
                "bbox": [round(float(value), 3) for value in part.bbox],
                "reading_order_index": int(index),
            }
            for index, part in enumerate(parts)
        ]
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
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
            query_key=str(sample.query_variant),
            slots={
                "object_description": OBJECT_DESCRIPTION[str(sample.query_variant)],
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            preferred_mode="answer_and_evidence",
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        canonical = int(CANONICAL_BIAS_ANSWER[str(sample.query_variant)])
        trace_payload = {
            "scene_ir": {
                "domain": self.domain,
                "scene_id": SCENE_ID,
                "entities": {
                    "object": {
                        "entity_id": "object_0",
                        "entity_type": "counterfactual_object",
                        "object_description": OBJECT_DESCRIPTION[str(sample.query_variant)],
                        "style_id": str(sample.style_id),
                        "bbox": [round(float(value), 3) for value in object_bbox],
                    },
                    "parts": list(part_records),
                },
                "relations": {
                    "query_variant": str(sample.query_variant),
                    "query_id": str(sample.query_variant),
                    "counted_part_kind": str(COUNTED_PART_KIND[str(sample.query_variant)]),
                },
            },
            "query_spec": {
                "task_id": self.task_id,
                "query_variant": str(sample.query_variant),
                "query_id": str(sample.query_variant),
                "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "visible_count": int(sample.visible_count),
                    "style_id": str(sample.style_id),
                    "canonical_bias_answer": int(canonical),
                    "counterfactual_delta": int(sample.visible_count) - int(canonical),
                    "query_variant_probabilities": dict(sample.query_variant_probabilities),
                    "visible_count_probabilities": dict(sample.visible_count_probabilities),
                    "style_probabilities": dict(sample.style_probabilities),
                },
            },
            "render_spec": {
                "canvas_width": int(image.width),
                "canvas_height": int(image.height),
                "coord_space": "pixel",
                "scene_id": SCENE_ID,
                "style": dict(render_meta),
            },
            "render_map": {
                "object_bbox_px": [round(float(value), 3) for value in object_bbox],
                "part_bboxes_px": {str(part.part_id): [round(float(value), 3) for value in part.bbox] for part in parts},
                "evidence_part_ids": [str(part.part_id) for part in parts],
            },
            "execution_trace": {
                "query_variant": str(sample.query_variant),
                "query_id": str(sample.query_variant),
                "answer": int(sample.visible_count),
                "visible_part_count": int(sample.visible_count),
                "counted_part_kind": str(COUNTED_PART_KIND[str(sample.query_variant)]),
                "canonical_bias_answer": int(canonical),
                "counterfactual_delta": int(sample.visible_count) - int(canonical),
                "counterfactual_edit_type": "visible_part_count_changed",
                "is_counterfactual": bool(int(sample.visible_count) != int(canonical)),
                "evidence_part_ids": [str(part.part_id) for part in parts],
            },
            "witness_symbolic": {
                "answer": int(sample.visible_count),
                "counted_part_ids": [str(part.part_id) for part in parts],
            },
            "projected_evidence": {"bbox_set": list(evidence_boxes)},
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
            answer_gt=TypedValue(type="integer", value=int(sample.visible_count)),
            evidence_gt=TypedValue(type="bbox_set", value=list(evidence_boxes)),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_build_complexity(sample),
            task_versions=default_task_versions(),
            query_variant=str(sample.query_variant),
            scene_id=SCENE_ID,
            query_id=str(sample.query_variant),
        )


__all__ = [
    "AIRPLANE_VARIANT",
    "BICYCLE_VARIANT",
    "BIRD_VARIANT",
    "BUTTERFLY_VARIANT",
    "CHAIR_VARIANT",
    "CLOVER_VARIANT",
    "FORK_VARIANT",
    "GLOVE_VARIANT",
    "QUADRUPED_VARIANT",
    "SNOWFLAKE_VARIANT",
    "STAR_VARIANT",
    "SUPPORTED_QUERY_VARIANTS",
    "TRAFFIC_LIGHT_VARIANT",
    "IllustrationsCounterfactualVisiblePartCountTask",
]
