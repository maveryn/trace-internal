"""Physics optics task for inferring a light source from a cast shadow."""

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
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.drawing import draw_centered_text
from ...shared.font_assets import font_asset_version, get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import build_prompt_json_examples
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.render_variation import resolve_render_int
from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.complexity import build_physics_complexity, resolve_physics_complexity_weights
from ..shared.diagram_style import prepare_physics_diagram_style_and_background
from ..shared.visual_defaults import load_physics_noise_defaults


TASK_ID = "task_physics__shadow_cause__light_source_label"
FAMILY_ID = "physics_optics_shadow_cause_family"
SCENE_ID = "shadow_cause"
QUERY_ID = "source_from_shadow_label"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (QUERY_ID,)
OPTION_LETTERS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")
SHADOW_DIRECTIONS: Tuple[str, ...] = (
    "east",
    "northeast",
    "north",
    "northwest",
    "west",
    "southwest",
    "south",
    "southeast",
)
OBJECT_SHAPES: Tuple[str, ...] = ("block", "cylinder", "sphere")
DIRECTION_VECTORS: Dict[str, Tuple[float, float]] = {
    "east": (1.0, 0.0),
    "northeast": (math.sqrt(0.5), -math.sqrt(0.5)),
    "north": (0.0, -1.0),
    "northwest": (-math.sqrt(0.5), -math.sqrt(0.5)),
    "west": (-1.0, 0.0),
    "southwest": (-math.sqrt(0.5), math.sqrt(0.5)),
    "south": (0.0, 1.0),
    "southeast": (math.sqrt(0.5), math.sqrt(0.5)),
}
OPPOSITE_DIRECTION: Dict[str, str] = {
    "east": "west",
    "northeast": "southwest",
    "north": "south",
    "northwest": "southeast",
    "west": "east",
    "southwest": "northeast",
    "south": "north",
    "southeast": "northwest",
}

_TASK_GROUP_DEFAULTS = get_task_group_defaults("physics", "optics")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=FAMILY_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(task_group="optics", apply_prob=0.5)


@dataclass(frozen=True)
class _TaskDefaults:
    canvas_width: int = 1120
    canvas_height: int = 760
    floor_left_px: int = 48
    floor_top_px: int = 50
    floor_right_margin_px: int = 48
    floor_bottom_margin_px: int = 48
    object_center_x_px: int = 560
    object_base_y_px: int = 430
    lamp_radius_x_px: int = 355
    lamp_radius_y_px: int = 238
    lamp_bulb_radius_px: int = 19
    lamp_label_font_size_px: int = 29
    label_stroke_width_px: int = 2
    title_font_size_px: int = 25
    shadow_length_px: int = 178
    shadow_length_px_min: int = 158
    shadow_length_px_max: int = 204
    shadow_base_width_px: int = 38
    shadow_tip_width_px: int = 78
    object_size_px: int = 88


@dataclass(frozen=True)
class _ResolvedAxes:
    query_id: str
    correct_option_letter: str
    shadow_direction: str
    object_shape: str
    query_id_probabilities: Dict[str, float]
    correct_option_letter_probabilities: Dict[str, float]
    shadow_direction_probabilities: Dict[str, float]
    object_shape_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _LampSpec:
    label: str
    direction: str
    center_px: Tuple[float, float]


@dataclass(frozen=True)
class _ShadowSceneSpec:
    query_id: str
    correct_option_letter: str
    shadow_direction: str
    source_direction: str
    object_shape: str
    object_fill_rgb: Tuple[int, int, int]
    lamps: Tuple[_LampSpec, ...]


@dataclass(frozen=True)
class _RenderedScene:
    image: Image.Image
    annotation_bbox_map: Dict[str, List[float]]
    scene_entities: List[Dict[str, Any]]
    render_map: Dict[str, Any]


_DEFAULTS = _TaskDefaults()
_OBJECT_PALETTES: Tuple[Tuple[int, int, int], ...] = (
    (68, 136, 201),
    (87, 156, 111),
    (191, 114, 73),
    (132, 112, 190),
    (195, 137, 64),
    (89, 150, 157),
)
_LAMP_GLOW_RGB = (255, 213, 91)
_LAMP_CORE_RGB = (255, 241, 173)
_LAMP_STROKE_RGB = (117, 86, 30)


def _bbox(values: Sequence[float]) -> List[float]:
    return [round(float(value), 3) for value in values]


def _clip_bbox(values: Sequence[float], *, width: int, height: int) -> List[float]:
    x0, y0, x1, y1 = [float(value) for value in values]
    return _bbox(
        (
            max(0.0, min(float(width), x0)),
            max(0.0, min(float(height), y0)),
            max(0.0, min(float(width), x1)),
            max(0.0, min(float(height), y1)),
        )
    )


def _expand_bbox(values: Sequence[float], padding: float) -> List[float]:
    return _bbox(
        (
            float(values[0]) - float(padding),
            float(values[1]) - float(padding),
            float(values[2]) + float(padding),
            float(values[3]) + float(padding),
        )
    )


def _bbox_union(boxes: Sequence[Sequence[float]]) -> List[float]:
    return _bbox(
        (
            min(float(box[0]) for box in boxes),
            min(float(box[1]) for box in boxes),
            max(float(box[2]) for box in boxes),
            max(float(box[3]) for box in boxes),
        )
    )


def _blend_rgb(a: Sequence[int], b: Sequence[int], amount: float) -> Tuple[int, int, int]:
    return tuple(
        int(round((1.0 - float(amount)) * int(a[idx]) + float(amount) * int(b[idx])))
        for idx in range(3)
    )


def _resolve_variant_axis(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    supported: Sequence[str],
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    namespace: str,
) -> Tuple[str, Dict[str, float]]:
    selected, probabilities = resolve_variant(
        spawn_rng(int(instance_seed), namespace),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=supported,
        explicit_key=explicit_key,
        weights_key=weights_key,
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=supported,
        balance_flag_key=balance_flag_key,
        explicit_key=explicit_key,
        weights_key=weights_key,
        sampling_namespace=namespace,
    )
    return str(selected), {str(key): float(value) for key, value in probabilities.items()}


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    query_id, query_probs = _resolve_variant_axis(
        instance_seed=int(instance_seed),
        params=params,
        supported=SUPPORTED_QUERY_IDS,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        namespace=f"{FAMILY_ID}.query_id",
    )
    correct_option_letter, letter_probs = _resolve_variant_axis(
        instance_seed=int(instance_seed),
        params=params,
        supported=OPTION_LETTERS,
        explicit_key="correct_option_letter",
        weights_key="correct_option_letter_weights",
        balance_flag_key="balanced_correct_option_letter_sampling",
        namespace=f"{FAMILY_ID}.correct_option_letter",
    )
    shadow_direction, shadow_probs = _resolve_variant_axis(
        instance_seed=int(instance_seed),
        params=params,
        supported=SHADOW_DIRECTIONS,
        explicit_key="shadow_direction",
        weights_key="shadow_direction_weights",
        balance_flag_key="balanced_shadow_direction_sampling",
        namespace=f"{FAMILY_ID}.shadow_direction",
    )
    object_shape, shape_probs = _resolve_variant_axis(
        instance_seed=int(instance_seed),
        params=params,
        supported=OBJECT_SHAPES,
        explicit_key="object_shape",
        weights_key="object_shape_weights",
        balance_flag_key="balanced_object_shape_sampling",
        namespace=f"{FAMILY_ID}.object_shape",
    )
    return _ResolvedAxes(
        query_id=str(query_id),
        correct_option_letter=str(correct_option_letter),
        shadow_direction=str(shadow_direction),
        object_shape=str(object_shape),
        query_id_probabilities=dict(query_probs),
        correct_option_letter_probabilities=dict(letter_probs),
        shadow_direction_probabilities=dict(shadow_probs),
        object_shape_probabilities=dict(shape_probs),
    )


def _resolve_render_defaults(params: Mapping[str, Any], *, instance_seed: int) -> Dict[str, int]:
    keys = (
        "floor_left_px",
        "floor_top_px",
        "floor_right_margin_px",
        "floor_bottom_margin_px",
        "object_center_x_px",
        "object_base_y_px",
        "lamp_radius_x_px",
        "lamp_radius_y_px",
        "lamp_bulb_radius_px",
        "lamp_label_font_size_px",
        "label_stroke_width_px",
        "title_font_size_px",
        "shadow_length_px",
        "shadow_base_width_px",
        "shadow_tip_width_px",
        "object_size_px",
    )
    return {
        key: resolve_render_int(
            params,
            _RENDER_DEFAULTS,
            key,
            int(getattr(_DEFAULTS, key)),
            instance_seed=int(instance_seed),
            namespace=FAMILY_ID,
        )
        for key in keys
    }


def _make_scene_spec(
    *,
    instance_seed: int,
    axes: _ResolvedAxes,
    render_defaults: Mapping[str, int],
) -> _ShadowSceneSpec:
    rng = spawn_rng(int(instance_seed), f"{FAMILY_ID}.scene")
    source_direction = OPPOSITE_DIRECTION[str(axes.shadow_direction)]
    distractor_directions = [direction for direction in SHADOW_DIRECTIONS if str(direction) != str(source_direction)]
    if str(axes.shadow_direction) in distractor_directions:
        distractor_directions.remove(str(axes.shadow_direction))
        distractor_directions = [str(axes.shadow_direction)] + distractor_directions
    tail = list(distractor_directions[1:])
    rng.shuffle(tail)
    distractor_directions = [distractor_directions[0], *tail]

    object_center = (
        float(render_defaults["object_center_x_px"]),
        float(render_defaults["object_base_y_px"]),
    )
    radius_x = float(render_defaults["lamp_radius_x_px"])
    radius_y = float(render_defaults["lamp_radius_y_px"])
    lamps: List[_LampSpec] = []
    distractor_index = 0
    for label in OPTION_LETTERS:
        direction = str(source_direction) if str(label) == str(axes.correct_option_letter) else str(distractor_directions[distractor_index])
        if str(label) != str(axes.correct_option_letter):
            distractor_index += 1
        vx, vy = DIRECTION_VECTORS[str(direction)]
        lamps.append(
            _LampSpec(
                label=str(label),
                direction=str(direction),
                center_px=(
                    float(object_center[0] + vx * radius_x),
                    float(object_center[1] + vy * radius_y),
                ),
            )
        )
    palette_index = int(abs(int(instance_seed)) % len(_OBJECT_PALETTES))
    return _ShadowSceneSpec(
        query_id=str(axes.query_id),
        correct_option_letter=str(axes.correct_option_letter),
        shadow_direction=str(axes.shadow_direction),
        source_direction=str(source_direction),
        object_shape=str(axes.object_shape),
        object_fill_rgb=tuple(int(value) for value in _OBJECT_PALETTES[palette_index]),
        lamps=tuple(lamps),
    )


def _draw_floor(
    draw: ImageDraw.ImageDraw,
    *,
    floor_bbox: Sequence[float],
    style: Any,
    font_family: str,
    render_defaults: Mapping[str, int],
) -> None:
    left, top, right, bottom = [float(value) for value in floor_bbox]
    draw.rounded_rectangle(
        floor_bbox,
        radius=22,
        fill=tuple(int(v) for v in style.panel_fill_rgb),
        outline=tuple(int(v) for v in style.panel_border_rgb),
        width=3,
    )
    grid_rgb = tuple(int(v) for v in style.grid_minor_rgb)
    for x in range(int(left) + 36, int(right), 56):
        draw.line([(float(x), top + 34.0), (float(x), bottom - 26.0)], fill=grid_rgb, width=1)
    for y in range(int(top) + 38, int(bottom), 48):
        draw.line([(left + 26.0, float(y)), (right - 26.0, float(y))], fill=grid_rgb, width=1)
    title_font = load_font(int(render_defaults["title_font_size_px"]), bold=True, font_family=font_family)
    label_rgb = tuple(int(v) for v in style.label_rgb)
    draw_centered_text(
        draw,
        text="light source candidates",
        center=((left + right) * 0.5, top + 28.0),
        font=title_font,
        fill=label_rgb,
        stroke_fill=resolve_text_stroke_fill(label_rgb),
        stroke_width=1,
    )


def _draw_shadow(
    image: Image.Image,
    *,
    object_base: Tuple[float, float],
    shadow_direction: str,
    render_defaults: Mapping[str, int],
) -> Tuple[Image.Image, List[float], Dict[str, Any]]:
    width, height = image.size
    dx, dy = DIRECTION_VECTORS[str(shadow_direction)]
    perp = (-float(dy), float(dx))
    length = float(render_defaults["shadow_length_px"])
    base_width = float(render_defaults["shadow_base_width_px"])
    tip_width = float(render_defaults["shadow_tip_width_px"])
    base_center = (
        float(object_base[0] + dx * 22.0),
        float(object_base[1] + dy * 22.0),
    )
    tip_center = (
        float(object_base[0] + dx * length),
        float(object_base[1] + dy * length),
    )
    polygon = [
        (base_center[0] + perp[0] * base_width * 0.5, base_center[1] + perp[1] * base_width * 0.5),
        (tip_center[0] + perp[0] * tip_width * 0.5, tip_center[1] + perp[1] * tip_width * 0.5),
        (tip_center[0] - perp[0] * tip_width * 0.5, tip_center[1] - perp[1] * tip_width * 0.5),
        (base_center[0] - perp[0] * base_width * 0.5, base_center[1] - perp[1] * base_width * 0.5),
    ]
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.polygon(polygon, fill=(32, 38, 44, 112))
    tip_ellipse = (
        tip_center[0] - tip_width * 0.58,
        tip_center[1] - tip_width * 0.36,
        tip_center[0] + tip_width * 0.58,
        tip_center[1] + tip_width * 0.36,
    )
    overlay_draw.ellipse(tip_ellipse, fill=(32, 38, 44, 102))
    composited = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    polygon_bbox = _bbox_union(
        [
            (
                min(point[0] for point in polygon),
                min(point[1] for point in polygon),
                max(point[0] for point in polygon),
                max(point[1] for point in polygon),
            ),
            tip_ellipse,
        ]
    )
    annotation_bbox = _clip_bbox(_expand_bbox(polygon_bbox, 5.0), width=width, height=height)
    return (
        composited,
        annotation_bbox,
        {
            "polygon_px": [[round(float(x), 3), round(float(y), 3)] for x, y in polygon],
            "tip_center_px": [round(float(tip_center[0]), 3), round(float(tip_center[1]), 3)],
            "length_px": round(float(length), 3),
        },
    )


def _draw_block_object(
    draw: ImageDraw.ImageDraw,
    *,
    base_center: Tuple[float, float],
    size: float,
    fill: Tuple[int, int, int],
    outline: Tuple[int, int, int],
) -> List[float]:
    cx, by = float(base_center[0]), float(base_center[1])
    front = (cx - size * 0.50, by - size * 0.72, cx + size * 0.50, by + size * 0.12)
    shift = (size * 0.24, -size * 0.22)
    top = [
        (front[0], front[1]),
        (front[0] + shift[0], front[1] + shift[1]),
        (front[2] + shift[0], front[1] + shift[1]),
        (front[2], front[1]),
    ]
    side = [
        (front[2], front[1]),
        (front[2] + shift[0], front[1] + shift[1]),
        (front[2] + shift[0], front[3] + shift[1]),
        (front[2], front[3]),
    ]
    draw.polygon(top, fill=_blend_rgb(fill, (255, 255, 255), 0.30), outline=outline)
    draw.polygon(side, fill=_blend_rgb(fill, (0, 0, 0), 0.16), outline=outline)
    draw.rounded_rectangle(front, radius=9, fill=fill, outline=outline, width=3)
    return _expand_bbox(_bbox_union([front, (front[0] + shift[0], front[1] + shift[1], front[2] + shift[0], front[3] + shift[1])]), 3.0)


def _draw_cylinder_object(
    draw: ImageDraw.ImageDraw,
    *,
    base_center: Tuple[float, float],
    size: float,
    fill: Tuple[int, int, int],
    outline: Tuple[int, int, int],
) -> List[float]:
    cx, by = float(base_center[0]), float(base_center[1])
    half_w = size * 0.44
    body_top = by - size * 0.92
    body_bottom = by + size * 0.08
    ellipse_h = size * 0.22
    body = (cx - half_w, body_top, cx + half_w, body_bottom)
    draw.rectangle(body, fill=fill, outline=outline, width=3)
    draw.ellipse((cx - half_w, body_top - ellipse_h * 0.5, cx + half_w, body_top + ellipse_h * 0.5), fill=_blend_rgb(fill, (255, 255, 255), 0.26), outline=outline, width=3)
    draw.arc((cx - half_w, body_bottom - ellipse_h * 0.5, cx + half_w, body_bottom + ellipse_h * 0.5), 0, 180, fill=outline, width=3)
    draw.arc((cx - half_w, body_bottom - ellipse_h * 0.5, cx + half_w, body_bottom + ellipse_h * 0.5), 180, 360, fill=_blend_rgb(outline, (255, 255, 255), 0.2), width=2)
    return _bbox((cx - half_w - 3.0, body_top - ellipse_h * 0.5 - 3.0, cx + half_w + 3.0, body_bottom + ellipse_h * 0.5 + 3.0))


def _draw_sphere_object(
    draw: ImageDraw.ImageDraw,
    *,
    base_center: Tuple[float, float],
    size: float,
    fill: Tuple[int, int, int],
    outline: Tuple[int, int, int],
) -> List[float]:
    cx, by = float(base_center[0]), float(base_center[1])
    radius = size * 0.48
    cy = by - radius * 0.70
    bbox = (cx - radius, cy - radius, cx + radius, cy + radius)
    draw.ellipse(bbox, fill=fill, outline=outline, width=3)
    highlight = (cx - radius * 0.46, cy - radius * 0.50, cx - radius * 0.04, cy - radius * 0.12)
    draw.ellipse(highlight, fill=_blend_rgb(fill, (255, 255, 255), 0.48))
    draw.arc((cx - radius * 0.72, cy - radius * 0.54, cx + radius * 0.70, cy + radius * 0.80), 208, 318, fill=_blend_rgb(outline, fill, 0.40), width=2)
    return _expand_bbox(bbox, 3.0)


def _draw_object(
    draw: ImageDraw.ImageDraw,
    *,
    spec: _ShadowSceneSpec,
    base_center: Tuple[float, float],
    render_defaults: Mapping[str, int],
    style: Any,
) -> List[float]:
    fill = tuple(int(value) for value in spec.object_fill_rgb)
    outline = tuple(max(0, int(value) - 70) for value in fill)
    size = float(render_defaults["object_size_px"])
    if spec.object_shape == "cylinder":
        return _draw_cylinder_object(draw, base_center=base_center, size=size, fill=fill, outline=outline)
    if spec.object_shape == "sphere":
        return _draw_sphere_object(draw, base_center=base_center, size=size, fill=fill, outline=outline)
    _ = style
    return _draw_block_object(draw, base_center=base_center, size=size, fill=fill, outline=outline)


def _draw_lamp(
    draw: ImageDraw.ImageDraw,
    *,
    lamp: _LampSpec,
    object_base: Tuple[float, float],
    style: Any,
    font_family: str,
    render_defaults: Mapping[str, int],
    canvas_width: int,
    canvas_height: int,
) -> Dict[str, Any]:
    cx, cy = float(lamp.center_px[0]), float(lamp.center_px[1])
    radius = float(render_defaults["lamp_bulb_radius_px"])
    label_font = load_font(int(render_defaults["lamp_label_font_size_px"]), bold=True, font_family=font_family)
    dx = float(cx - object_base[0])
    dy = float(cy - object_base[1])
    distance = max(1.0, math.hypot(dx, dy))
    unit_x = dx / distance
    unit_y = dy / distance
    stand_end = (cx - unit_x * (radius + 22.0), cy - unit_y * (radius + 22.0))
    draw.line([stand_end, (cx - unit_x * radius * 0.55, cy - unit_y * radius * 0.55)], fill=tuple(int(v) for v in style.stroke_rgb), width=4)
    glow_bbox = (cx - radius * 1.62, cy - radius * 1.62, cx + radius * 1.62, cy + radius * 1.62)
    draw.ellipse(glow_bbox, fill=(255, 230, 138), outline=None)
    bulb_bbox = (cx - radius, cy - radius, cx + radius, cy + radius)
    draw.ellipse(bulb_bbox, fill=_LAMP_GLOW_RGB, outline=_LAMP_STROKE_RGB, width=3)
    core_r = radius * 0.48
    draw.ellipse((cx - core_r, cy - core_r, cx + core_r, cy + core_r), fill=_LAMP_CORE_RGB)
    for angle in range(0, 360, 60):
        radians = math.radians(float(angle))
        start = (cx + math.cos(radians) * radius * 1.22, cy + math.sin(radians) * radius * 1.22)
        end = (cx + math.cos(radians) * radius * 1.58, cy + math.sin(radians) * radius * 1.58)
        draw.line([start, end], fill=_LAMP_STROKE_RGB, width=2)

    label_center = (
        max(34.0, min(float(canvas_width - 34), cx - unit_x * 44.0)),
        max(34.0, min(float(canvas_height - 34), cy - unit_y * 44.0)),
    )
    label_bbox = (
        label_center[0] - 23.0,
        label_center[1] - 21.0,
        label_center[0] + 23.0,
        label_center[1] + 21.0,
    )
    draw.rounded_rectangle(
        label_bbox,
        radius=10,
        fill=tuple(int(v) for v in style.label_fill_rgb),
        outline=tuple(int(v) for v in style.label_border_rgb),
        width=2,
    )
    text_rgb = tuple(int(v) for v in style.label_rgb)
    text_bbox = draw_centered_text(
        draw,
        text=str(lamp.label),
        center=label_center,
        font=label_font,
        fill=text_rgb,
        stroke_fill=resolve_text_stroke_fill(text_rgb),
        stroke_width=int(render_defaults["label_stroke_width_px"]),
    )
    lamp_bbox = _clip_bbox(_expand_bbox(_bbox_union([glow_bbox, bulb_bbox]), 4.0), width=canvas_width, height=canvas_height)
    return {
        "label": str(lamp.label),
        "direction": str(lamp.direction),
        "center_px": [round(float(cx), 3), round(float(cy), 3)],
        "lamp_bbox_px": lamp_bbox,
        "label_bbox_px": _clip_bbox(_bbox_union([label_bbox, text_bbox]), width=canvas_width, height=canvas_height),
    }


def _render_scene(
    *,
    image: Image.Image,
    spec: _ShadowSceneSpec,
    render_defaults: Mapping[str, int],
    font_family: str,
    style: Any,
) -> _RenderedScene:
    width, height = image.size
    draw = ImageDraw.Draw(image)
    floor_bbox = (
        float(render_defaults["floor_left_px"]),
        float(render_defaults["floor_top_px"]),
        float(width - int(render_defaults["floor_right_margin_px"])),
        float(height - int(render_defaults["floor_bottom_margin_px"])),
    )
    _draw_floor(
        draw,
        floor_bbox=floor_bbox,
        style=style,
        font_family=font_family,
        render_defaults=render_defaults,
    )

    object_base = (
        float(render_defaults["object_center_x_px"]),
        float(render_defaults["object_base_y_px"]),
    )
    image, shadow_bbox, shadow_meta = _draw_shadow(
        image,
        object_base=object_base,
        shadow_direction=str(spec.shadow_direction),
        render_defaults=render_defaults,
    )
    draw = ImageDraw.Draw(image)
    object_bbox = _clip_bbox(
        _draw_object(
            draw,
            spec=spec,
            base_center=object_base,
            render_defaults=render_defaults,
            style=style,
        ),
        width=width,
        height=height,
    )
    lamp_records = [
        _draw_lamp(
            draw,
            lamp=lamp,
            object_base=object_base,
            style=style,
            font_family=font_family,
            render_defaults=render_defaults,
            canvas_width=width,
            canvas_height=height,
        )
        for lamp in spec.lamps
    ]
    annotation_bbox_map = {
        "object": list(object_bbox),
        "shadow": list(shadow_bbox),
    }
    entities: List[Dict[str, Any]] = [
        {
            "entity_id": "shadow_object",
            "entity_type": f"{spec.object_shape}_object",
            "bbox_px": list(object_bbox),
            "meta": {
                "object_shape": str(spec.object_shape),
                "object_fill_rgb": list(spec.object_fill_rgb),
            },
        },
        {
            "entity_id": "cast_shadow",
            "entity_type": "cast_shadow",
            "bbox_px": list(shadow_bbox),
            "meta": {
                "shadow_direction": str(spec.shadow_direction),
                "source_direction": str(spec.source_direction),
            },
        },
    ]
    for record in lamp_records:
        entities.append(
            {
                "entity_id": f"lamp_{record['label']}",
                "entity_type": "candidate_light_source",
                "bbox_px": list(record["lamp_bbox_px"]),
                "meta": {
                    "option_letter": str(record["label"]),
                    "direction": str(record["direction"]),
                    "is_correct": str(record["label"]) == str(spec.correct_option_letter),
                },
            }
        )
    render_map = {
        "floor_bbox_px": _bbox(floor_bbox),
        "object_base_px": [round(float(object_base[0]), 3), round(float(object_base[1]), 3)],
        "object_bbox_px": list(object_bbox),
        "object_shape": str(spec.object_shape),
        "shadow_direction": str(spec.shadow_direction),
        "source_direction": str(spec.source_direction),
        "shadow_bbox_px": list(shadow_bbox),
        "shadow_geometry": dict(shadow_meta),
        "correct_option_letter": str(spec.correct_option_letter),
        "candidate_light_sources": {str(record["label"]): dict(record) for record in lamp_records},
        "candidate_directions": {str(record["label"]): str(record["direction"]) for record in lamp_records},
        "annotation_keyed_bboxes_px": dict(annotation_bbox_map),
    }
    return _RenderedScene(
        image=image,
        annotation_bbox_map={str(key): list(value) for key, value in annotation_bbox_map.items()},
        scene_entities=[dict(entity) for entity in entities],
        render_map=dict(render_map),
    )


def _build_complexity(*, spec: _ShadowSceneSpec) -> TaskComplexity:
    weights = resolve_physics_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=FAMILY_ID)
    diagonal = 1.0 if str(spec.shadow_direction) in {"northeast", "northwest", "southwest", "southeast"} else 0.0
    return build_physics_complexity(
        weights=weights,
        components={
            "visual_scan": 0.44,
            "light_shadow_reasoning": 0.46 + (0.06 * diagonal),
            "ambiguity": 0.18,
            "output_burden": 0.20,
        },
    )


@register_task
class PhysicsShadowCauseLightSourceLabelTask:
    """Choose which labeled light source caused the visible cast shadow."""

    task_id = TASK_ID
    domain = "physics"
    task_group = "optics"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        params = dict(params or {})
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_seed = int(instance_seed) + (attempt_index * 7919)
            try:
                axes = _resolve_axes(attempt_seed, params=params)
                render_defaults = _resolve_render_defaults(params, instance_seed=attempt_seed)
                spec = _make_scene_spec(
                    instance_seed=attempt_seed,
                    axes=axes,
                    render_defaults=render_defaults,
                )
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
                canvas_width=canvas_width,
                canvas_height=canvas_height,
                require_grid=True,
            )
            font_family = sample_font_family(
                role="readout",
                instance_seed=attempt_seed,
                namespace=f"{FAMILY_ID}.font",
                params=params,
            )
            font_record = get_font_family_record(str(font_family))
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
                    f"answer_hint_{QUERY_ID}",
                    f"annotation_hint_{QUERY_ID}",
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
                instance_seed=attempt_seed,
                answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            )
            prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
            complexity = _build_complexity(spec=spec)
            trace_payload = {
                "scene_ir": {
                    "scene_kind": "physics_shadow_cause_light_source_candidates",
                    "entities": [dict(entity) for entity in rendered.scene_entities],
                    "relations": {
                        "query_id": QUERY_ID,
                        "shadow_direction": str(spec.shadow_direction),
                        "source_direction": str(spec.source_direction),
                        "correct_option_letter": str(spec.correct_option_letter),
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
                        "target_answer": str(spec.correct_option_letter),
                        "answer_support": list(OPTION_LETTERS),
                        "shadow_direction": str(spec.shadow_direction),
                        "source_direction": str(spec.source_direction),
                        "object_shape": str(spec.object_shape),
                    },
                },
                "render_spec": {
                    "canvas_width": int(image.size[0]),
                    "canvas_height": int(image.size[1]),
                    "font": {
                        "font_family": str(font_family),
                        "font_asset_version": font_asset_version(),
                        "font_asset": font_record.to_trace(),
                        "scope": "shadow_cause_diagram",
                        "selection_policy": {
                            "pool": "global_approved_font_pool",
                            "include_tags": [],
                            "exclude_tags": [],
                            "exclusion_reason": "",
                        },
                    },
                    "technical_diagram_style": dict(diagram_style_meta),
                    "background_style": background_meta,
                    "render_defaults": dict(render_defaults),
                    "post_image_noise": post_noise_meta,
                },
                "render_map": dict(rendered.render_map),
                "execution_trace": {
                    "query_id": QUERY_ID,
                    "correct_option_letter": str(spec.correct_option_letter),
                    "shadow_direction": str(spec.shadow_direction),
                    "source_direction": str(spec.source_direction),
                    "candidate_directions": dict(rendered.render_map["candidate_directions"]),
                    "object_shape": str(spec.object_shape),
                    "annotation_entity_ids": sorted(annotation_gt.value.keys()),
                },
                "sampling": {
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "correct_option_letter_probabilities": dict(axes.correct_option_letter_probabilities),
                    "shadow_direction_probabilities": dict(axes.shadow_direction_probabilities),
                    "object_shape_probabilities": dict(axes.object_shape_probabilities),
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
                query_id=QUERY_ID,
            )
        raise RuntimeError(f"failed to generate shadow-cause instance after {max_attempts} attempts: {last_error}")


__all__ = ["PhysicsShadowCauseLightSourceLabelTask"]
