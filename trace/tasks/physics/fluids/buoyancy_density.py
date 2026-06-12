"""Physics fluids task for floating-object buoyancy density diagrams."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import hash64, spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.bbox_projection import bbox_union_many as _bbox_union
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.drawing import draw_centered_text
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.font_assets import font_asset_version, get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import build_prompt_json_examples
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.render_variation import resolve_layout_jitter, resolve_render_int
from ...shared.text_legibility import draw_traced_text
from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.diagram_style import prepare_physics_diagram_style_and_background
from ..shared.visual_defaults import load_physics_noise_defaults


TASK_NAMESPACE = "physics_fluids_buoyancy_density"
SCENE_ID = "buoyancy_density"
TASK_ID = "task_physics__buoyancy_density__object_density_value"
QUERY_ID = "floating_object_density_value"
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "rectangular_tank",
    "beaker_tank",
    "wide_tank",
)
SUPPORTED_OBJECT_SHAPES: Tuple[str, ...] = (
    "block",
    "rounded_block",
    "capsule_block",
)
DEFAULT_FRACTIONS: Tuple[Tuple[int, int], ...] = (
    (1, 4),
    (1, 2),
    (2, 3),
    (3, 4),
    (4, 5),
    (9, 10),
)

POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(scene_id="fluids", apply_prob=0.5)
_TASK_GROUP_DEFAULTS = get_scene_defaults("physics", "fluids")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_NAMESPACE,
)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for buoyancy-density scenes."""

    canvas_width: int = 1120
    canvas_height: int = 720
    panel_left_px: int = 54
    panel_top_px: int = 52
    panel_right_margin_px: int = 54
    panel_bottom_margin_px: int = 58
    tank_left_px: int = 172
    tank_top_px: int = 160
    tank_width_px: int = 700
    tank_height_px: int = 410
    waterline_y_px: int = 346
    object_center_x_px: int = 520
    object_width_px: int = 118
    object_part_height_px: int = 44
    label_font_size_px: int = 25
    small_font_size_px: int = 20
    title_font_size_px: int = 28
    label_stroke_width_px: int = 2
    marker_width_px: int = 4


@dataclass(frozen=True)
class _BuoyancyScenario:
    """Symbolic floating-object scenario."""

    scene_variant: str
    object_shape: str
    fraction_num: int
    fraction_den: int
    liquid_density_tenths: int
    object_density_tenths: int
    target_answer: float
    answer_support: Tuple[float, ...]
    target_answer_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    object_shape_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RenderedScene:
    """Rendered buoyancy scene plus annotation metadata."""

    image: Image.Image
    annotation_bbox_map: Dict[str, List[float]]
    scene_entities: List[Dict[str, Any]]
    render_map: Dict[str, Any]


_DEFAULTS = _TaskDefaults()


def _bbox(values: Sequence[float]) -> List[float]:
    return [round(float(value), 3) for value in values]


def _format_density(tenths: int) -> str:
    value = float(int(tenths)) / 10.0
    return f"{value:.1f}"


def _fraction_support(params: Mapping[str, Any]) -> Tuple[Tuple[int, int], ...]:
    raw = params.get("submerged_fraction_support", group_default(_GEN_DEFAULTS, "submerged_fraction_support", None))
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        out: List[Tuple[int, int]] = []
        for item in raw:
            if isinstance(item, str) and "/" in item:
                a, b = item.split("/", 1)
                out.append((int(a), int(b)))
            elif isinstance(item, Sequence) and not isinstance(item, (str, bytes)) and len(item) == 2:
                out.append((int(item[0]), int(item[1])))
        if out:
            return tuple(out)
    return DEFAULT_FRACTIONS


def _liquid_density_support_tenths(params: Mapping[str, Any]) -> Tuple[int, ...]:
    raw = params.get(
        "liquid_density_tenths_support",
        group_default(_GEN_DEFAULTS, "liquid_density_tenths_support", list(range(8, 31))),
    )
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        return tuple(int(value) for value in raw)
    return tuple(range(8, 31))


def _feasible_scenarios(params: Mapping[str, Any]) -> Tuple[Tuple[int, int, int, int], ...]:
    scenarios: List[Tuple[int, int, int, int]] = []
    explicit_fraction = params.get("submerged_fraction")
    explicit_liquid = params.get("liquid_density_tenths")
    fraction_values = _fraction_support(params)
    if explicit_fraction is not None:
        if isinstance(explicit_fraction, str) and "/" in explicit_fraction:
            a, b = explicit_fraction.split("/", 1)
            fraction_values = ((int(a), int(b)),)
        elif isinstance(explicit_fraction, Sequence) and not isinstance(explicit_fraction, (str, bytes)):
            fraction_values = ((int(explicit_fraction[0]), int(explicit_fraction[1])),)
    liquid_values = _liquid_density_support_tenths(params)
    if explicit_liquid is not None:
        liquid_values = (int(explicit_liquid),)
    for num, den in fraction_values:
        if int(num) <= 0 or int(den) <= 0 or int(num) >= int(den):
            continue
        for liquid_tenths in liquid_values:
            numerator = int(liquid_tenths) * int(num)
            if numerator % int(den) != 0:
                continue
            object_tenths = int(numerator // int(den))
            if object_tenths <= 0:
                continue
            scenarios.append((int(num), int(den), int(liquid_tenths), int(object_tenths)))
    if not scenarios:
        raise ValueError("no feasible buoyancy-density scenarios for configured supports")
    return tuple(scenarios)


def _answer_support_tenths(params: Mapping[str, Any]) -> Tuple[int, ...]:
    explicit_support = params.get("target_answer_tenths_support")
    if isinstance(explicit_support, Sequence) and not isinstance(explicit_support, (str, bytes)):
        return tuple(sorted({int(value) for value in explicit_support}))
    return tuple(sorted({int(item[3]) for item in _feasible_scenarios(params)}))


def _resolve_scene_variant(instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    rng = spawn_rng(int(instance_seed), f"{TASK_NAMESPACE}.scene_variant")
    selected, probabilities = resolve_variant(
        rng,
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


def _resolve_object_shape(instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    rng = spawn_rng(int(instance_seed), f"{TASK_NAMESPACE}.object_shape")
    selected, probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_OBJECT_SHAPES,
        explicit_key="object_shape",
        weights_key="object_shape_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=SUPPORTED_OBJECT_SHAPES,
        balance_flag_key="balanced_object_shape_sampling",
        explicit_key="object_shape",
        weights_key="object_shape_weights",
        sampling_namespace=f"{TASK_NAMESPACE}.object_shape",
    )
    return str(selected), {str(key): float(value) for key, value in probabilities.items()}


def _resolve_target_answer_tenths(instance_seed: int, params: Mapping[str, Any]) -> Tuple[int, Dict[str, float]]:
    scenarios = _feasible_scenarios(params)
    support = _answer_support_tenths(params)
    explicit_answer = params.get("target_answer", params.get("object_density"))
    if explicit_answer is not None:
        selected = int(round(float(explicit_answer) * 10.0))
        if selected not in support:
            raise ValueError(f"target_answer {float(explicit_answer)} is not feasible for buoyancy-density supports")
        return selected, {str(float(value) / 10.0): (1.0 if int(value) == selected else 0.0) for value in support}
    feasible_answers = sorted({int(item[3]) for item in scenarios if int(item[3]) in set(support)})
    if not feasible_answers:
        raise ValueError("no feasible target answers for configured buoyancy-density supports")
    if bool(params.get("balanced_target_answer_sampling", group_default(_GEN_DEFAULTS, "balanced_target_answer_sampling", True))):
        index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_NAMESPACE}.target_answer")
        selected = int(feasible_answers[index % len(feasible_answers)])
    else:
        rng = spawn_rng(int(instance_seed), f"{TASK_NAMESPACE}.target_answer")
        selected = int(rng.choice(feasible_answers))
    probability = 1.0 / float(len(feasible_answers))
    return selected, {str(float(value) / 10.0): float(probability) for value in feasible_answers}


def _make_scenario(instance_seed: int, *, params: Mapping[str, Any]) -> _BuoyancyScenario:
    scene_variant, scene_probs = _resolve_scene_variant(int(instance_seed), params)
    object_shape, shape_probs = _resolve_object_shape(int(instance_seed), params)
    target_tenths, target_probs = _resolve_target_answer_tenths(int(instance_seed), params)
    matching = [item for item in _feasible_scenarios(params) if int(item[3]) == int(target_tenths)]
    if not matching:
        raise ValueError("target answer has no matching buoyancy scenario")
    choice_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_NAMESPACE}.scenario") % len(matching)
    num, den, liquid_tenths, object_tenths = matching[int(choice_index)]
    answer_support = tuple(float(value) / 10.0 for value in _answer_support_tenths(params))
    return _BuoyancyScenario(
        scene_variant=str(scene_variant),
        object_shape=str(object_shape),
        fraction_num=int(num),
        fraction_den=int(den),
        liquid_density_tenths=int(liquid_tenths),
        object_density_tenths=int(object_tenths),
        target_answer=float(object_tenths) / 10.0,
        answer_support=answer_support,
        target_answer_probabilities=dict(target_probs),
        scene_variant_probabilities=dict(scene_probs),
        object_shape_probabilities=dict(shape_probs),
    )


def _draw_label(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[float, float],
    text: str,
    font: Any,
    fill: Tuple[int, int, int],
) -> List[float]:
    bbox = draw.textbbox((float(xy[0]), float(xy[1])), str(text), font=font, stroke_width=1)
    draw_traced_text(
        draw,
        xy=(float(xy[0]), float(xy[1])),
        text=str(text),
        font=font,
        fill_rgb=fill,
        stroke_width=1,
        stroke_rgb=resolve_text_stroke_fill(fill),
        role="readout",
        required=True,
    )
    return _bbox(tuple(float(value) for value in bbox))


def _object_geometry(render_defaults: Mapping[str, Any], scenario: _BuoyancyScenario) -> Dict[str, float]:
    den = int(scenario.fraction_den)
    configured_part_height = float(render_defaults["object_part_height_px"])
    max_height = 282.0
    part_height = min(configured_part_height, max_height / float(max(1, den)))
    object_height = float(part_height * den)
    waterline_y = float(render_defaults["waterline_y_px"])
    top = float(waterline_y - ((den - int(scenario.fraction_num)) * part_height))
    bottom = float(top + object_height)
    center_x = float(render_defaults["object_center_x_px"])
    width = float(render_defaults["object_width_px"])
    return {
        "left": float(center_x - width / 2.0),
        "right": float(center_x + width / 2.0),
        "top": float(top),
        "bottom": float(bottom),
        "width": float(width),
        "height": float(object_height),
        "part_height": float(part_height),
        "waterline_y": float(waterline_y),
    }


def _draw_floating_object(
    draw: ImageDraw.ImageDraw,
    *,
    scenario: _BuoyancyScenario,
    geometry: Mapping[str, float],
    style: Any,
    object_rgb: Tuple[int, int, int],
) -> Dict[str, Any]:
    left = float(geometry["left"])
    right = float(geometry["right"])
    top = float(geometry["top"])
    bottom = float(geometry["bottom"])
    waterline_y = float(geometry["waterline_y"])
    part_height = float(geometry["part_height"])
    radius = 8
    if str(scenario.object_shape) == "rounded_block":
        radius = 18
    elif str(scenario.object_shape) == "capsule_block":
        radius = int(min(float(geometry["width"]) / 2.0, 32.0))

    outline = tuple(int(value) for value in style.stroke_rgb)
    submerged_rgb = tuple(max(0, int(value) - 38) for value in object_rgb)
    draw.rounded_rectangle((left, top, right, bottom), radius=radius, fill=object_rgb, outline=outline, width=4)
    draw.rectangle((left + 3, waterline_y, right - 3, bottom - 3), fill=submerged_rgb)
    draw.rounded_rectangle((left, top, right, bottom), radius=radius, outline=outline, width=4)
    for index in range(1, int(scenario.fraction_den)):
        y = float(top + index * part_height)
        draw.line((left + 5, y, right - 5, y), fill=outline, width=2)

    marker_x = right + 22.0
    marker_rgb = tuple(int(value) for value in style.accent_rgb)
    draw.line((marker_x, top, marker_x, bottom), fill=marker_rgb, width=4)
    for index in range(0, int(scenario.fraction_den) + 1):
        y = float(top + index * part_height)
        draw.line((marker_x - 10, y, marker_x + 10, y), fill=marker_rgb, width=3)
    draw.line((marker_x - 13, waterline_y, marker_x + 13, waterline_y), fill=marker_rgb, width=5)
    return {
        "floating_object_bbox": _bbox((left, top, right, bottom)),
        "fraction_marker_bbox": _bbox((marker_x - 16, top - 4, marker_x + 16, bottom + 4)),
        "object_geometry": {
            "left": round(left, 3),
            "right": round(right, 3),
            "top": round(top, 3),
            "bottom": round(bottom, 3),
            "waterline_y": round(waterline_y, 3),
            "part_height": round(part_height, 3),
        },
    }


def _render_scene(
    *,
    background: Image.Image,
    scenario: _BuoyancyScenario,
    render_defaults: Mapping[str, Any],
    font_family: str,
    style: Any,
) -> _RenderedScene:
    image = background
    draw = ImageDraw.Draw(image)
    canvas_width, canvas_height = image.size
    label_font = load_font(int(render_defaults["label_font_size_px"]), bold=True, font_family=font_family)
    small_font = load_font(int(render_defaults["small_font_size_px"]), bold=True, font_family=font_family)
    title_font = load_font(int(render_defaults["title_font_size_px"]), bold=True, font_family=font_family)
    text_rgb = tuple(int(value) for value in style.label_rgb)
    stroke_rgb = tuple(int(value) for value in style.stroke_rgb)
    guide_rgb = tuple(int(value) for value in style.guide_rgb)

    panel = (
        float(render_defaults["panel_left_px"]),
        float(render_defaults["panel_top_px"]),
        float(canvas_width - int(render_defaults["panel_right_margin_px"])),
        float(canvas_height - int(render_defaults["panel_bottom_margin_px"])),
    )
    draw.rounded_rectangle(panel, radius=18, fill=tuple(style.panel_fill_rgb), outline=tuple(style.panel_border_rgb), width=3)

    tank_left = float(render_defaults["tank_left_px"])
    tank_top = float(render_defaults["tank_top_px"])
    tank_width = float(render_defaults["tank_width_px"])
    tank_height = float(render_defaults["tank_height_px"])
    if str(scenario.scene_variant) == "wide_tank":
        tank_left -= 40
        tank_width += 86
    elif str(scenario.scene_variant) == "beaker_tank":
        tank_left += 20
        tank_width -= 42
    tank_right = float(tank_left + tank_width)
    tank_bottom = float(tank_top + tank_height)
    waterline_y = float(render_defaults["waterline_y_px"])
    liquid_palette = (
        (92, 169, 219),
        (83, 184, 160),
        (118, 154, 224),
        (105, 181, 203),
    )
    object_palette = (
        (225, 151, 75),
        (211, 118, 93),
        (177, 139, 221),
        (219, 180, 82),
    )
    color_index = int(hash64(int(scenario.object_density_tenths), f"{TASK_NAMESPACE}.color", int(scenario.liquid_density_tenths)) % len(liquid_palette))
    liquid_rgb = liquid_palette[color_index]
    object_rgb = object_palette[int(hash64(int(scenario.liquid_density_tenths), f"{TASK_NAMESPACE}.object_color", 0) % len(object_palette))]

    if str(scenario.scene_variant) == "beaker_tank":
        lip = 34.0
        beaker_points = [
            (tank_left + lip, tank_top),
            (tank_right - lip, tank_top),
            (tank_right - 10, tank_bottom),
            (tank_left + 10, tank_bottom),
        ]
        draw.polygon(beaker_points, fill=(239, 248, 252), outline=stroke_rgb)
        draw.line((tank_left + lip, tank_top, tank_right - lip, tank_top), fill=stroke_rgb, width=5)
        liquid_points = [
            (tank_left + 22, waterline_y),
            (tank_right - 22, waterline_y),
            (tank_right - 14, tank_bottom - 10),
            (tank_left + 14, tank_bottom - 10),
        ]
        draw.polygon(liquid_points, fill=liquid_rgb)
        draw.line((tank_left + 22, waterline_y, tank_right - 22, waterline_y), fill=tuple(max(0, v - 45) for v in liquid_rgb), width=5)
        tank_bbox = _bbox((tank_left + 8, tank_top, tank_right - 8, tank_bottom))
        waterline_bbox = _bbox((tank_left + 22, waterline_y - 7, tank_right - 22, waterline_y + 7))
    else:
        draw.rounded_rectangle((tank_left, tank_top, tank_right, tank_bottom), radius=20, fill=(239, 248, 252), outline=stroke_rgb, width=5)
        draw.rectangle((tank_left + 10, waterline_y, tank_right - 10, tank_bottom - 10), fill=liquid_rgb)
        draw.line((tank_left + 10, waterline_y, tank_right - 10, waterline_y), fill=tuple(max(0, v - 45) for v in liquid_rgb), width=5)
        tank_bbox = _bbox((tank_left, tank_top, tank_right, tank_bottom))
        waterline_bbox = _bbox((tank_left + 10, waterline_y - 7, tank_right - 10, waterline_y + 7))

    for offset in (0.25, 0.50, 0.75):
        y = tank_top + tank_height * offset
        draw.line((tank_left + 16, y, tank_right - 16, y), fill=guide_rgb, width=1)

    obj_geometry = _object_geometry(render_defaults, scenario)
    object_render = _draw_floating_object(
        draw,
        scenario=scenario,
        geometry=obj_geometry,
        style=style,
        object_rgb=object_rgb,
    )
    draw.line(
        (
            max(tank_left + 12, float(obj_geometry["left"]) - 38),
            waterline_y,
            min(tank_right - 12, float(obj_geometry["right"]) + 68),
            waterline_y,
        ),
        fill=tuple(max(0, v - 55) for v in liquid_rgb),
        width=3,
    )

    draw_centered_text(
        draw,
        text="floating object",
        center=((float(obj_geometry["left"]) + float(obj_geometry["right"])) / 2.0, float(obj_geometry["top"]) - 28),
        font=small_font,
        fill=text_rgb,
        stroke_fill=resolve_text_stroke_fill(text_rgb),
        stroke_width=1,
    )
    title_bbox = draw_centered_text(
        draw,
        text="Buoyancy density diagram",
        center=(canvas_width * 0.5, panel[1] + 32),
        font=title_font,
        fill=text_rgb,
        stroke_fill=resolve_text_stroke_fill(text_rgb),
        stroke_width=1,
    )
    density_text = f"rho_liquid = {_format_density(scenario.liquid_density_tenths)} g/cm^3"
    density_bbox = _draw_label(
        draw,
        (tank_right - 290, tank_top - 56),
        density_text,
        label_font,
        text_rgb,
    )
    draw_centered_text(
        draw,
        text="liquid surface",
        center=(tank_left + 92, waterline_y - 22),
        font=small_font,
        fill=tuple(max(0, v - 45) for v in liquid_rgb),
        stroke_fill=resolve_text_stroke_fill(tuple(max(0, v - 45) for v in liquid_rgb)),
        stroke_width=1,
    )

    annotation_bbox_map = {
        "floating_object": list(object_render["floating_object_bbox"]),
        "waterline": list(waterline_bbox),
        "fluid_density_label": list(density_bbox),
        "submerged_fraction_marker": list(object_render["fraction_marker_bbox"]),
    }
    scene_entities = [
        {"entity_id": "tank", "entity_type": "container", "bbox_px": tank_bbox},
        {"entity_id": "floating_object", "entity_type": "floating_object", "bbox_px": list(object_render["floating_object_bbox"])},
        {"entity_id": "waterline", "entity_type": "liquid_surface", "bbox_px": list(waterline_bbox)},
        {"entity_id": "fluid_density_label", "entity_type": "density_label", "bbox_px": list(density_bbox)},
        {"entity_id": "submerged_fraction_marker", "entity_type": "fraction_marker", "bbox_px": list(object_render["fraction_marker_bbox"])},
    ]
    render_map = {
        "scene_variant": str(scenario.scene_variant),
        "object_shape": str(scenario.object_shape),
        "tank_bbox_px": list(tank_bbox),
        "title_bbox_px": list(title_bbox),
        "waterline_bbox_px": list(waterline_bbox),
        "floating_object_bbox_px": list(object_render["floating_object_bbox"]),
        "fraction_marker_bbox_px": list(object_render["fraction_marker_bbox"]),
        "fluid_density_label_bbox_px": list(density_bbox),
        "object_geometry": dict(object_render["object_geometry"]),
        "submerged_fraction": {
            "numerator": int(scenario.fraction_num),
            "denominator": int(scenario.fraction_den),
            "value": float(scenario.fraction_num) / float(scenario.fraction_den),
        },
        "liquid_density_g_cm3": float(scenario.liquid_density_tenths) / 10.0,
        "object_density_g_cm3": float(scenario.object_density_tenths) / 10.0,
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
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    content_left = float(render_defaults["panel_left_px"])
    content_top = float(render_defaults["panel_top_px"])
    content_right = float(canvas_width - int(render_defaults["panel_right_margin_px"]))
    content_bottom = float(canvas_height - int(render_defaults["panel_bottom_margin_px"]))
    jitter = resolve_layout_jitter(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_NAMESPACE}.layout",
    )
    min_margin = int(jitter.get("min_margin_px", 18))
    requested_dx = int(jitter.get("requested_dx_px", 0))
    requested_dy = int(jitter.get("requested_dy_px", 0))
    min_dx = int(math.ceil(float(min_margin) - content_left))
    max_dx = int(math.floor(float(canvas_width) - float(min_margin) - content_right))
    min_dy = int(math.ceil(float(min_margin) - content_top))
    max_dy = int(math.floor(float(canvas_height) - float(min_margin) - content_bottom))
    if min_dx > max_dx:
        min_dx = max_dx = 0
    if min_dy > max_dy:
        min_dy = max_dy = 0
    if not bool(jitter.get("enabled", False)):
        requested_dx = 0
        requested_dy = 0
    dx = max(min_dx, min(max_dx, requested_dx))
    dy = max(min_dy, min(max_dy, requested_dy))
    adjusted = dict(render_defaults)
    for key in ("panel_left_px", "tank_left_px", "object_center_x_px"):
        adjusted[key] = int(adjusted[key]) + int(dx)
    for key in ("panel_top_px", "tank_top_px", "waterline_y_px"):
        adjusted[key] = int(adjusted[key]) + int(dy)
    placement = dict(jitter)
    placement.update(
        {
            "mode": "whole_buoyancy_diagram_offset",
            "content_bbox_px": _bbox((content_left, content_top, content_right, content_bottom)),
            "final_content_bbox_px": _bbox((content_left + dx, content_top + dy, content_right + dx, content_bottom + dy)),
            "canvas_size_px": [int(canvas_width), int(canvas_height)],
            "available_offset_x_px": [int(min_dx), int(max_dx)],
            "available_offset_y_px": [int(min_dy), int(max_dy)],
            "sampled_offset_px": [int(requested_dx), int(requested_dy)],
            "final_offset_px": [int(dx), int(dy)],
        }
    )
    return adjusted, placement


@register_task
class PhysicsBuoyancyDensityObjectDensityValueTask:
    """Compute object density from visible submerged fraction and liquid density."""

    task_id = TASK_ID
    domain = "physics"
    scene_id = "fluids"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        params = dict(params or {})
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_seed = int(instance_seed) + (7919 * int(attempt_index))
            try:
                scenario = _make_scenario(attempt_seed, params=params)
            except Exception as exc:  # pragma: no cover - surfaced if all attempts fail.
                last_error = exc
                continue

            canvas_width = int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width)))
            canvas_height = int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height)))
            background, background_meta, diagram_style, diagram_style_meta = prepare_physics_diagram_style_and_background(
                instance_seed=attempt_seed,
                params=params,
                scene_id=SCENE_ID,
                canvas_width=canvas_width,
                canvas_height=canvas_height,
                require_grid=True,
            )
            font_family = sample_font_family(
                role="readout",
                instance_seed=attempt_seed,
                namespace=f"{TASK_NAMESPACE}.font",
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
                    namespace=TASK_NAMESPACE,
                )
                for key in (
                    "panel_left_px",
                    "panel_top_px",
                    "panel_right_margin_px",
                    "panel_bottom_margin_px",
                    "tank_left_px",
                    "tank_top_px",
                    "tank_width_px",
                    "tank_height_px",
                    "waterline_y_px",
                    "object_center_x_px",
                    "object_width_px",
                    "object_part_height_px",
                    "label_font_size_px",
                    "small_font_size_px",
                    "title_font_size_px",
                    "label_stroke_width_px",
                    "marker_width_px",
                )
            }
            render_defaults, layout_placement_meta = _resolve_layout_placement(
                render_defaults=render_defaults,
                params=params,
                instance_seed=attempt_seed,
                canvas_width=canvas_width,
                canvas_height=canvas_height,
            )
            rendered = _render_scene(
                background=background,
                scenario=scenario,
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
            answer_gt = TypedValue(type="number", value=float(scenario.target_answer))
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
                scene_id=self.scene_id,
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
            trace_payload = {
                "scene_ir": {
                    "scene_kind": f"physics_buoyancy_density_{str(scenario.scene_variant)}",
                    "entities": [dict(entity) for entity in rendered.scene_entities],
                    "relations": {
                        "scene_variant": str(scenario.scene_variant),
                        "query_id": QUERY_ID,
                        "object_shape": str(scenario.object_shape),
                        "submerged_fraction": [int(scenario.fraction_num), int(scenario.fraction_den)],
                        "liquid_density_tenths": int(scenario.liquid_density_tenths),
                        "object_density_tenths": int(scenario.object_density_tenths),
                        "target_answer": float(scenario.target_answer),
                    },
                },
                "query_spec": {
                    "query_id": QUERY_ID,
                    "template_id": str(prompt_defaults["bundle_id"]),
                    "prompt_variant": dict(prompt_artifacts.prompt_variant),
                    "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                    "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                    "params": {
                        "scene_variant": str(scenario.scene_variant),
                        "query_id": QUERY_ID,
                        "object_shape": str(scenario.object_shape),
                        "target_answer": float(scenario.target_answer),
                        "answer_support": list(scenario.answer_support),
                        "scene_variant_probabilities": dict(scenario.scene_variant_probabilities),
                        "object_shape_probabilities": dict(scenario.object_shape_probabilities),
                        "target_answer_probabilities": dict(scenario.target_answer_probabilities),
                    },
                },
                "render_spec": {
                    "canvas_width": int(image.size[0]),
                    "canvas_height": int(image.size[1]),
                    "font": {
                        "font_family": str(font_family),
                        "font_asset_version": font_asset_version(),
                        "font_asset": font_record.to_trace(),
                        "scope": "buoyancy_density_diagram",
                    },
                    "technical_diagram_style": dict(diagram_style_meta),
                    "background_style": background_meta,
                    "layout_placement": dict(layout_placement_meta),
                    "post_image_noise": post_noise_meta,
                },
                "render_map": dict(rendered.render_map),
                "execution_trace": {
                    "query_id": QUERY_ID,
                    "scene_variant": str(scenario.scene_variant),
                    "object_shape": str(scenario.object_shape),
                    "submerged_fraction_num": int(scenario.fraction_num),
                    "submerged_fraction_den": int(scenario.fraction_den),
                    "liquid_density_g_cm3": float(scenario.liquid_density_tenths) / 10.0,
                    "object_density_g_cm3": float(scenario.target_answer),
                    "target_answer": float(scenario.target_answer),
                    "answer_support": list(scenario.answer_support),
                    "annotation_entity_ids": sorted(annotation_gt.value.keys()),
                },
                "witness_symbolic": {
                    "type": "object_map",
                    "ids": sorted(annotation_gt.value.keys()),
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
                task_versions=default_task_versions(),
                scene_id=SCENE_ID,
                query_id=QUERY_ID,
            )
        raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts: {last_error}")


__all__ = ["PhysicsBuoyancyDensityObjectDensityValueTask"]
