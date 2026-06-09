"""Physics circuit task for qualitative bulb-brightness reasoning."""

from __future__ import annotations

import json
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
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.drawing import draw_centered_text
from ...shared.font_assets import font_asset_version, get_font_family_record, sample_font_family
from ...shared.named_colors import named_color
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from ..shared.complexity import (
    build_physics_complexity,
    clamp_unit_interval,
    normalize_linear,
    resolve_physics_complexity_weights,
)
from ..shared.diagram_style import prepare_physics_diagram_style_and_background
from ..shared.style import SUPPORTED_PHYSICS_COLOR_NAMES
from ..shared.visual_defaults import load_physics_noise_defaults


FAMILY_ID = "physics_circuits_bulb_brightness_family"
SCENE_ID = "bulb_circuit"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = ("brightest_bulb_label", "dimmest_bulb_label")
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("series_unequal", "parallel_unequal", "mixed_branch")
BULB_LABELS: Tuple[str, ...] = ("B1", "B2", "B3", "B4", "B5")
DEFAULT_RESISTANCE_OPTIONS: Tuple[int, ...] = (2, 3, 4, 5, 6, 8, 10, 12)

_TASK_GROUP_DEFAULTS = get_task_group_defaults("physics", "circuits")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=FAMILY_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(task_group="circuits", apply_prob=0.5)


@dataclass(frozen=True)
class _BulbSpec:
    """One visible bulb with a computed relative power."""

    slot_id: str
    label: str
    resistance_ohm: int
    relative_power: float


@dataclass(frozen=True)
class _BulbScenario:
    """Resolved semantic circuit scenario."""

    query_id: str
    scene_variant: str
    accent_color_name: str
    branch_single_position: str
    bulbs: Tuple[_BulbSpec, ...]
    correct_label: str
    brightest_label: str
    dimmest_label: str
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    accent_color_name_probabilities: Dict[str, float]


def _bbox(values: Sequence[float]) -> List[float]:
    return [round(float(value), 3) for value in values]


def _union_bbox(*bboxes: Sequence[float]) -> List[float]:
    usable = [tuple(float(value) for value in bbox) for bbox in bboxes if len(bbox) == 4]
    if not usable:
        return [0.0, 0.0, 0.0, 0.0]
    return _bbox(
        (
            min(bbox[0] for bbox in usable),
            min(bbox[1] for bbox in usable),
            max(bbox[2] for bbox in usable),
            max(bbox[3] for bbox in usable),
        )
    )


def _clip_bbox(bbox: Sequence[float], *, width: int, height: int) -> List[float]:
    if len(bbox) != 4:
        raise ValueError("bbox must contain four values")
    x0, y0, x1, y1 = [float(value) for value in bbox]
    return _bbox(
        (
            max(0.0, min(float(width), min(x0, x1))),
            max(0.0, min(float(height), min(y0, y1))),
            max(0.0, min(float(width), max(x0, x1))),
            max(0.0, min(float(height), max(y0, y1))),
        )
    )


def _valid_probability_map(values: Sequence[str], weights: Mapping[str, Any]) -> Dict[str, float]:
    raw = {str(value): max(0.0, float(weights.get(str(value), 1.0))) for value in values}
    total = sum(raw.values())
    if total <= 0.0:
        return {str(value): 1.0 / float(len(values)) for value in values}
    return {str(value): float(raw[str(value)] / total) for value in values}


def _weighted_choice(
    values: Sequence[str],
    weights: Mapping[str, Any],
    *,
    instance_seed: int,
    namespace: str,
) -> Tuple[str, Dict[str, float]]:
    probabilities = _valid_probability_map(values, weights)
    raw = float(hash64(int(instance_seed), str(namespace), 0) % 1_000_000) / 1_000_000.0
    cursor = 0.0
    for value in values:
        cursor += float(probabilities[str(value)])
        if raw <= cursor:
            return str(value), dict(probabilities)
    return str(values[-1]), dict(probabilities)


def _resolve_query_id(instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    explicit = str(params.get("query_id") or "").strip()
    if explicit:
        if explicit not in set(SUPPORTED_QUERY_IDS):
            raise ValueError(f"unsupported query_id for {FAMILY_ID}: {explicit}")
        return explicit, {str(query_id): (1.0 if str(query_id) == explicit else 0.0) for query_id in SUPPORTED_QUERY_IDS}
    return _weighted_choice(
        SUPPORTED_QUERY_IDS,
        _GEN_DEFAULTS.get("query_id_weights", {}),
        instance_seed=int(instance_seed),
        namespace=f"{FAMILY_ID}.query_id",
    )


def _resolve_scene_variant(instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    explicit = str(params.get("scene_variant") or params.get("topology_variant") or "").strip()
    if explicit:
        if explicit not in set(SUPPORTED_SCENE_VARIANTS):
            raise ValueError(f"unsupported scene_variant for {FAMILY_ID}: {explicit}")
        return explicit, {str(variant): (1.0 if str(variant) == explicit else 0.0) for variant in SUPPORTED_SCENE_VARIANTS}
    return _weighted_choice(
        SUPPORTED_SCENE_VARIANTS,
        _GEN_DEFAULTS.get("scene_variant_weights", {}),
        instance_seed=int(instance_seed),
        namespace=f"{FAMILY_ID}.scene_variant",
    )


def _resolve_accent_color(instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    explicit = str(params.get("accent_color_name") or "").strip()
    if explicit:
        if explicit not in set(SUPPORTED_PHYSICS_COLOR_NAMES):
            raise ValueError(f"unsupported accent_color_name for {FAMILY_ID}: {explicit}")
        return explicit, {str(name): (1.0 if str(name) == explicit else 0.0) for name in SUPPORTED_PHYSICS_COLOR_NAMES}
    return _weighted_choice(
        SUPPORTED_PHYSICS_COLOR_NAMES,
        _GEN_DEFAULTS.get("accent_color_name_weights", {}),
        instance_seed=int(instance_seed),
        namespace=f"{FAMILY_ID}.accent_color_name",
    )


def _resolve_target_label(instance_seed: int, params: Mapping[str, Any]) -> str:
    explicit = str(params.get("target_label") or params.get("target_answer") or "").strip()
    if explicit:
        if explicit not in set(BULB_LABELS):
            raise ValueError(f"target label must be one of {BULB_LABELS}")
        return explicit
    index = int(hash64(int(instance_seed), f"{FAMILY_ID}.target_label", 0) % len(BULB_LABELS))
    return str(BULB_LABELS[index])


def _resistance_options(params: Mapping[str, Any]) -> Tuple[int, ...]:
    raw = params.get("resistance_options", group_default(_GEN_DEFAULTS, "resistance_options", DEFAULT_RESISTANCE_OPTIONS))
    if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
        raise ValueError("resistance_options must be a sequence of positive integers")
    values = tuple(dict.fromkeys(int(value) for value in raw))
    if len(values) < len(BULB_LABELS) or any(value <= 0 for value in values):
        raise ValueError("resistance_options must contain at least five positive integers")
    return values


def _power_values(scene_variant: str, resistances: Sequence[int]) -> Tuple[float, ...]:
    if str(scene_variant) == "series_unequal":
        total = sum(float(value) for value in resistances)
        return tuple(float(value) / (total * total) for value in resistances)
    if str(scene_variant) == "parallel_unequal":
        return tuple(1.0 / float(value) for value in resistances)
    if str(scene_variant) == "mixed_branch":
        first_branch = [float(value) for value in resistances[:2]]
        second_branch = [float(value) for value in resistances[2:]]
        first_total = sum(first_branch)
        second_total = sum(second_branch)
        return tuple(
            [value / (first_total * first_total) for value in first_branch]
            + [value / (second_total * second_total) for value in second_branch]
        )
    raise ValueError(f"unsupported scene_variant: {scene_variant}")


def _has_unique_powers(powers: Sequence[float]) -> bool:
    for idx, first in enumerate(powers):
        for second in powers[idx + 1 :]:
            if abs(float(first) - float(second)) <= 1e-9:
                return False
    return True


def _resolve_resistances(instance_seed: int, *, params: Mapping[str, Any], scene_variant: str) -> Tuple[int, ...]:
    explicit_raw = params.get("resistance_values")
    if explicit_raw is not None:
        if isinstance(explicit_raw, (str, bytes)) or not isinstance(explicit_raw, Sequence) or len(explicit_raw) != len(BULB_LABELS):
            raise ValueError("resistance_values must contain exactly five positive integers")
        values = tuple(int(value) for value in explicit_raw)
        if any(value <= 0 for value in values):
            raise ValueError("resistance_values must be positive")
        if not _has_unique_powers(_power_values(str(scene_variant), values)):
            raise ValueError("resistance_values must produce a unique brightness order")
        return values

    options = list(_resistance_options(params))
    rng = spawn_rng(int(instance_seed), f"{FAMILY_ID}.resistances.{str(scene_variant)}")
    for _ in range(200):
        values = tuple(int(value) for value in rng.sample(options, k=len(BULB_LABELS)))
        if _has_unique_powers(_power_values(str(scene_variant), values)):
            return values
    raise RuntimeError(f"failed to sample unique bulb powers for {scene_variant}")


def _make_scenario(instance_seed: int, params: Mapping[str, Any]) -> _BulbScenario:
    query_id, query_probs = _resolve_query_id(int(instance_seed), params)
    scene_variant, scene_probs = _resolve_scene_variant(int(instance_seed), params)
    accent_color_name, accent_probs = _resolve_accent_color(int(instance_seed), params)
    target_label = _resolve_target_label(int(instance_seed), params)
    resistances = _resolve_resistances(int(instance_seed), params=params, scene_variant=str(scene_variant))
    powers = _power_values(str(scene_variant), resistances)
    slots = tuple(f"slot_{index}" for index in range(len(BULB_LABELS)))
    sorted_slots = sorted(slots, key=lambda slot: float(powers[slots.index(slot)]), reverse=True)
    brightest_slot = str(sorted_slots[0])
    dimmest_slot = str(sorted_slots[-1])
    target_slot = brightest_slot if str(query_id) == "brightest_bulb_label" else dimmest_slot

    label_by_slot: Dict[str, str] = {str(target_slot): str(target_label)}
    remaining_slots = [slot for slot in slots if str(slot) != str(target_slot)]
    remaining_labels = [label for label in BULB_LABELS if str(label) != str(target_label)]
    rng = spawn_rng(int(instance_seed), f"{FAMILY_ID}.label_assignment")
    rng.shuffle(remaining_slots)
    rng.shuffle(remaining_labels)
    for slot, label in zip(remaining_slots, remaining_labels):
        label_by_slot[str(slot)] = str(label)

    bulbs = tuple(
        _BulbSpec(
            slot_id=str(slot),
            label=str(label_by_slot[str(slot)]),
            resistance_ohm=int(resistances[index]),
            relative_power=float(powers[index]),
        )
        for index, slot in enumerate(slots)
    )
    label_by_power = {str(spec.label): float(spec.relative_power) for spec in bulbs}
    brightest_label = max(label_by_power, key=label_by_power.get)
    dimmest_label = min(label_by_power, key=label_by_power.get)
    branch_single_position = "top" if int(hash64(int(instance_seed), f"{FAMILY_ID}.single_branch_position", 0) % 2) == 0 else "bottom"
    if params.get("branch_single_position") in {"top", "bottom"}:
        branch_single_position = str(params["branch_single_position"])
    return _BulbScenario(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        accent_color_name=str(accent_color_name),
        branch_single_position=str(branch_single_position),
        bulbs=bulbs,
        correct_label=str(brightest_label if str(query_id) == "brightest_bulb_label" else dimmest_label),
        brightest_label=str(brightest_label),
        dimmest_label=str(dimmest_label),
        query_id_probabilities=dict(query_probs),
        scene_variant_probabilities=dict(scene_probs),
        accent_color_name_probabilities=dict(accent_probs),
    )


def _draw_label_tag(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    center: Tuple[float, float],
    font: Any,
    style: Any,
) -> List[float]:
    text_bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=0)
    text_w = float(text_bbox[2] - text_bbox[0])
    text_h = float(text_bbox[3] - text_bbox[1])
    cx, cy = float(center[0]), float(center[1])
    pad_x = 10.0
    pad_y = 6.0
    tag = _bbox((cx - (text_w * 0.5) - pad_x, cy - (text_h * 0.5) - pad_y, cx + (text_w * 0.5) + pad_x, cy + (text_h * 0.5) + pad_y))
    draw.rounded_rectangle(
        tuple(float(value) for value in tag),
        radius=7,
        fill=tuple(int(value) for value in style.label_fill_rgb),
        outline=tuple(int(value) for value in style.label_border_rgb),
        width=2,
    )
    return draw_centered_text(
        draw,
        text=str(text),
        center=(cx, cy),
        font=font,
        fill=tuple(int(value) for value in style.stroke_rgb),
        stroke_fill=resolve_text_stroke_fill(style.stroke_rgb),
        stroke_width=1,
    )


def _draw_bulb(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    spec: _BulbSpec,
    style: Any,
    accent_rgb: Tuple[int, int, int],
    label_font: Any,
    label_offset: Tuple[float, float] | None = None,
) -> List[float]:
    cx, cy = float(center[0]), float(center[1])
    radius = 36.0
    stroke = tuple(int(value) for value in style.stroke_rgb)
    fill = tuple(int(value) for value in style.panel_alt_fill_rgb)
    glass = (
        min(255, int(fill[0]) + 12),
        min(255, int(fill[1]) + 10),
        min(255, int(fill[2]) + 4),
    )
    bulb_bbox = _bbox((cx - radius, cy - radius, cx + radius, cy + radius))
    draw.ellipse(tuple(float(value) for value in bulb_bbox), fill=glass, outline=stroke, width=4)
    base = _bbox((cx - 18.0, cy + 22.0, cx + 18.0, cy + 39.0))
    draw.rounded_rectangle(tuple(float(value) for value in base), radius=4, fill=tuple(int(value) for value in style.muted_fill_rgb), outline=stroke, width=3)
    filament_y = cy - 1.0
    filament_rgb = tuple(max(0, min(255, int((0.35 * accent_rgb[idx]) + (0.65 * stroke[idx])))) for idx in range(3))
    filament_points = [
        (cx - 20.0, filament_y + 8.0),
        (cx - 12.0, filament_y - 8.0),
        (cx - 4.0, filament_y + 8.0),
        (cx + 4.0, filament_y - 8.0),
        (cx + 12.0, filament_y + 8.0),
        (cx + 20.0, filament_y - 8.0),
    ]
    draw.line(filament_points, fill=filament_rgb, width=4, joint="curve")
    draw.line((cx - 15.0, cy + 20.0, cx - 20.0, filament_y + 8.0), fill=stroke, width=3)
    draw.line((cx + 15.0, cy + 20.0, cx + 20.0, filament_y - 8.0), fill=stroke, width=3)
    label_text = f"{spec.label}={int(spec.resistance_ohm)} ohm"
    if label_offset is None:
        label_offset = (0.0, radius + 28.0)
    label_bbox = _draw_label_tag(
        draw,
        text=label_text,
        center=(cx + float(label_offset[0]), cy + float(label_offset[1])),
        font=label_font,
        style=style,
    )
    return _union_bbox(bulb_bbox, base, label_bbox)


def _draw_battery(
    draw: ImageDraw.ImageDraw,
    *,
    x: float,
    y_top: float,
    y_bottom: float,
    style: Any,
    font: Any,
    wire_width: int,
) -> Dict[str, List[float]]:
    stroke = tuple(int(value) for value in style.stroke_rgb)
    guide = tuple(int(value) for value in style.guide_rgb)
    mid_y = (float(y_top) + float(y_bottom)) * 0.5
    plate_top = mid_y - 22.0
    plate_bottom = mid_y + 24.0
    draw.line((x, y_top, x, plate_top - 16.0), fill=stroke, width=int(wire_width))
    draw.line((x, plate_bottom + 16.0, x, y_bottom), fill=stroke, width=int(wire_width))
    draw.line((x - 38.0, plate_top, x + 38.0, plate_top), fill=stroke, width=max(3, int(wire_width) + 2))
    draw.line((x - 25.0, plate_bottom, x + 25.0, plate_bottom), fill=stroke, width=max(3, int(wire_width) + 2))
    plus_box = draw_centered_text(
        draw,
        text="+",
        center=(x + 58.0, plate_top - 2.0),
        font=font,
        fill=stroke,
        stroke_fill=resolve_text_stroke_fill(stroke),
        stroke_width=1,
    )
    minus_box = draw_centered_text(
        draw,
        text="-",
        center=(x + 58.0, plate_bottom),
        font=font,
        fill=guide,
        stroke_fill=resolve_text_stroke_fill(guide),
        stroke_width=1,
    )
    return {"battery": _union_bbox((x - 42.0, plate_top - 20.0, x + 66.0, plate_bottom + 20.0), plus_box, minus_box)}


def _draw_series_circuit(
    draw: ImageDraw.ImageDraw,
    *,
    scenario: _BulbScenario,
    style: Any,
    accent_rgb: Tuple[int, int, int],
    label_font: Any,
    battery_font: Any,
    render_defaults: Mapping[str, Any],
) -> Dict[str, List[float]]:
    wire_width = int(render_defaults.get("wire_width_px", 5))
    stroke = tuple(int(value) for value in style.stroke_rgb)
    left_x = 166.0
    right_x = 1108.0
    top_y = 250.0
    bottom_y = 510.0
    centers = [(304.0, top_y), (482.0, top_y), (660.0, top_y), (838.0, top_y), (1016.0, top_y)]
    _draw_battery(draw, x=left_x, y_top=top_y, y_bottom=bottom_y, style=style, font=battery_font, wire_width=wire_width)
    draw.line((left_x, bottom_y, right_x, bottom_y, right_x, top_y), fill=stroke, width=wire_width)
    draw.line((left_x, top_y, right_x, top_y), fill=stroke, width=wire_width)
    annotation: Dict[str, List[float]] = {}
    for spec, center in zip(scenario.bulbs, centers):
        annotation[str(spec.label)] = _draw_bulb(
            draw,
            center=center,
            spec=spec,
            style=style,
            accent_rgb=accent_rgb,
            label_font=label_font,
        )
    return annotation


def _draw_parallel_circuit(
    draw: ImageDraw.ImageDraw,
    *,
    scenario: _BulbScenario,
    style: Any,
    accent_rgb: Tuple[int, int, int],
    label_font: Any,
    battery_font: Any,
    render_defaults: Mapping[str, Any],
) -> Dict[str, List[float]]:
    wire_width = int(render_defaults.get("wire_width_px", 5))
    stroke = tuple(int(value) for value in style.stroke_rgb)
    left_x = 244.0
    right_x = 1080.0
    branch_ys = (156.0, 252.0, 348.0, 444.0, 540.0)
    _draw_battery(draw, x=left_x, y_top=branch_ys[0], y_bottom=branch_ys[-1], style=style, font=battery_font, wire_width=wire_width)
    draw.line((right_x, branch_ys[0], right_x, branch_ys[-1]), fill=stroke, width=wire_width)
    annotation: Dict[str, List[float]] = {}
    for spec, y in zip(scenario.bulbs, branch_ys):
        draw.line((left_x, y, right_x, y), fill=stroke, width=wire_width)
        annotation[str(spec.label)] = _draw_bulb(
            draw,
            center=((left_x + right_x) * 0.5, y),
            spec=spec,
            style=style,
            accent_rgb=accent_rgb,
            label_font=label_font,
            label_offset=(122.0, 0.0),
        )
    return annotation


def _draw_mixed_circuit(
    draw: ImageDraw.ImageDraw,
    *,
    scenario: _BulbScenario,
    style: Any,
    accent_rgb: Tuple[int, int, int],
    label_font: Any,
    battery_font: Any,
    render_defaults: Mapping[str, Any],
) -> Dict[str, List[float]]:
    wire_width = int(render_defaults.get("wire_width_px", 5))
    stroke = tuple(int(value) for value in style.stroke_rgb)
    left_x = 244.0
    right_x = 1080.0
    top_y = 238.0
    bottom_y = 480.0
    single_y = top_y if scenario.branch_single_position == "top" else bottom_y
    pair_y = bottom_y if scenario.branch_single_position == "top" else top_y
    short_specs = scenario.bulbs[:2]
    long_specs = scenario.bulbs[2:]
    _draw_battery(draw, x=left_x, y_top=top_y, y_bottom=bottom_y, style=style, font=battery_font, wire_width=wire_width)
    draw.line((right_x, top_y, right_x, bottom_y), fill=stroke, width=wire_width)
    draw.line((left_x, single_y, right_x, single_y), fill=stroke, width=wire_width)
    draw.line((left_x, pair_y, right_x, pair_y), fill=stroke, width=wire_width)
    annotation: Dict[str, List[float]] = {}
    for spec, x in zip(short_specs, (560.0, 764.0)):
        annotation[str(spec.label)] = _draw_bulb(
            draw,
            center=(x, single_y),
            spec=spec,
            style=style,
            accent_rgb=accent_rgb,
            label_font=label_font,
        )
    for spec, x in zip(long_specs, (438.0, 662.0, 886.0)):
        annotation[str(spec.label)] = _draw_bulb(
            draw,
            center=(x, pair_y),
            spec=spec,
            style=style,
            accent_rgb=accent_rgb,
            label_font=label_font,
        )
    return annotation


def _render_scene(
    *,
    image: Image.Image,
    scenario: _BulbScenario,
    font_family: str,
    style: Any,
    render_defaults: Mapping[str, Any],
) -> Tuple[Image.Image, Dict[str, List[float]], Dict[str, Any]]:
    draw = ImageDraw.Draw(image)
    canvas_width, canvas_height = image.size
    title_font = load_font(28, bold=True, font_family=font_family)
    label_font = load_font(int(render_defaults.get("bulb_label_font_size_px", 20)), bold=True, font_family=font_family)
    battery_font = load_font(24, bold=True, font_family=font_family)
    panel = (
        float(render_defaults.get("panel_left_px", 56)),
        float(render_defaults.get("panel_top_px", 58)),
        float(render_defaults.get("panel_right_px", canvas_width - 56)),
        float(render_defaults.get("panel_bottom_px", canvas_height - 58)),
    )
    draw.rounded_rectangle(
        panel,
        radius=20,
        fill=tuple(int(value) for value in style.panel_fill_rgb),
        outline=tuple(int(value) for value in style.panel_border_rgb),
        width=3,
    )
    text_rgb = tuple(int(value) for value in style.stroke_rgb)
    draw_centered_text(
        draw,
        text="Ideal battery with labeled bulbs",
        center=((panel[0] + panel[2]) * 0.5, panel[1] + 34.0),
        font=title_font,
        fill=text_rgb,
        stroke_fill=resolve_text_stroke_fill(text_rgb),
        stroke_width=1,
    )
    accent_rgb = named_color(str(scenario.accent_color_name))
    if scenario.scene_variant == "series_unequal":
        annotation_map = _draw_series_circuit(
            draw,
            scenario=scenario,
            style=style,
            accent_rgb=accent_rgb,
            label_font=label_font,
            battery_font=battery_font,
            render_defaults=render_defaults,
        )
    elif scenario.scene_variant == "parallel_unequal":
        annotation_map = _draw_parallel_circuit(
            draw,
            scenario=scenario,
            style=style,
            accent_rgb=accent_rgb,
            label_font=label_font,
            battery_font=battery_font,
            render_defaults=render_defaults,
        )
    else:
        annotation_map = _draw_mixed_circuit(
            draw,
            scenario=scenario,
            style=style,
            accent_rgb=accent_rgb,
            label_font=label_font,
            battery_font=battery_font,
            render_defaults=render_defaults,
        )
    annotation_map = {
        str(key): _clip_bbox(value, width=int(canvas_width), height=int(canvas_height))
        for key, value in sorted(annotation_map.items())
    }
    render_map = {
        "panel_bbox": _bbox(panel),
        "scene_variant": str(scenario.scene_variant),
        "branch_single_position": str(scenario.branch_single_position),
        "bulb_bboxes": dict(annotation_map),
        "bulb_specs": [
            {
                "slot_id": str(spec.slot_id),
                "label": str(spec.label),
                "resistance_ohm": int(spec.resistance_ohm),
                "relative_power": round(float(spec.relative_power), 8),
            }
            for spec in scenario.bulbs
        ],
        "correct_label": str(scenario.correct_label),
        "brightest_label": str(scenario.brightest_label),
        "dimmest_label": str(scenario.dimmest_label),
    }
    return image, annotation_map, render_map


def _build_prompt_examples() -> Tuple[str, str]:
    annotation_example = {
        "B1": [0, 0, 4, 3],
        "B2": [5, 0, 9, 3],
        "B3": [10, 0, 14, 3],
        "B4": [15, 0, 19, 3],
        "B5": [20, 0, 24, 3],
    }
    return (
        json.dumps({"annotation": annotation_example, "answer": "B2"}, ensure_ascii=False, separators=(",", ":")),
        json.dumps({"answer": "B2"}, ensure_ascii=False, separators=(",", ":")),
    )


def _build_complexity(*, scenario: _BulbScenario) -> TaskComplexity:
    weights = resolve_physics_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=FAMILY_ID)
    powers = [float(spec.relative_power) for spec in scenario.bulbs]
    sorted_powers = sorted(powers)
    min_gap = min(abs(sorted_powers[idx + 1] - sorted_powers[idx]) for idx in range(len(sorted_powers) - 1))
    topology_load = {"series_unequal": 0.38, "parallel_unequal": 0.48, "mixed_branch": 0.72}[str(scenario.scene_variant)]
    visual_scan = clamp_unit_interval(0.34 + (0.12 if scenario.scene_variant == "mixed_branch" else 0.0))
    brightness_reasoning = clamp_unit_interval(float(topology_load) + (0.06 if scenario.query_id == "dimmest_bulb_label" else 0.0))
    ambiguity = clamp_unit_interval(0.24 - (0.10 * normalize_linear(float(min_gap), min_value=0.005, max_value=0.08)))
    return build_physics_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "brightness_reasoning": float(brightness_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": 0.18,
        },
    )


@register_task
class PhysicsBulbCircuitBrightnessExtremumLabelTask:
    """Choose the brightest or dimmest labeled bulb in a visible circuit."""

    task_id = "task_physics__bulb_circuit__brightness_extremum_label"
    domain = "physics"
    task_group = "circuits"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        _ = int(max_attempts)
        params = dict(params or {})
        canvas_width = int(_RENDER_DEFAULTS.get("canvas_width", 1280))
        canvas_height = int(_RENDER_DEFAULTS.get("canvas_height", 720))
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
                "answer_hint_brightest_bulb_label",
                "answer_hint_dimmest_bulb_label",
                "annotation_hint_brightness_extremum",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        answer_gt = TypedValue(type="string", value=str(scenario.correct_label))
        annotation_gt = TypedValue(type="keyed_bbox_map", value={str(k): list(v) for k, v in annotation_map.items()})
        json_example, json_example_answer_only = _build_prompt_examples()
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(scenario.query_id),
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[f"answer_hint_{str(scenario.query_id)}"]),
                "annotation_hint": str(prompt_defaults["annotation_hint_brightness_extremum"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        projected_annotation = {
            "type": "keyed_bbox_map",
            "keyed_bbox_map": dict(annotation_gt.value),
            "pixel_keyed_bbox_map": dict(annotation_gt.value),
        }
        complexity = _build_complexity(scenario=scenario)
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"physics_bulb_circuit_{str(scenario.scene_variant)}",
                "entities": [
                    {
                        "entity_id": str(spec.label),
                        "entity_type": "bulb",
                        "slot_id": str(spec.slot_id),
                        "resistance_ohm": int(spec.resistance_ohm),
                        "relative_power": float(spec.relative_power),
                    }
                    for spec in scenario.bulbs
                ],
                "relations": {
                    "scene_variant": str(scenario.scene_variant),
                    "query_id": str(scenario.query_id),
                    "brightest_label": str(scenario.brightest_label),
                    "dimmest_label": str(scenario.dimmest_label),
                    "correct_label": str(scenario.correct_label),
                },
            },
            "query_spec": {
                "query_id": str(scenario.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "scene_variant": str(scenario.scene_variant),
                    "query_id": str(scenario.query_id),
                    "accent_color_name": str(scenario.accent_color_name),
                    "scene_variant_probabilities": dict(scenario.scene_variant_probabilities),
                    "query_id_probabilities": dict(scenario.query_id_probabilities),
                    "accent_color_name_probabilities": dict(scenario.accent_color_name_probabilities),
                    "target_answer": str(scenario.correct_label),
                },
            },
            "render_spec": {
                "scene_variant": str(scenario.scene_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "accent_color_name": str(scenario.accent_color_name),
                "font": {
                    "font_family": str(font_family),
                    "font_asset_version": font_asset_version(),
                    "font_asset": font_record.to_trace(),
                    "scope": "bulb_circuit_diagram",
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
                "scene_variant": str(scenario.scene_variant),
                "query_id": str(scenario.query_id),
                "accent_color_name": str(scenario.accent_color_name),
                "target_answer": str(scenario.correct_label),
                "brightest_label": str(scenario.brightest_label),
                "dimmest_label": str(scenario.dimmest_label),
                "bulb_specs": [
                    {
                        "slot_id": str(spec.slot_id),
                        "label": str(spec.label),
                        "resistance_ohm": int(spec.resistance_ohm),
                        "relative_power": float(spec.relative_power),
                    }
                    for spec in scenario.bulbs
                ],
                "annotation_entity_ids": sorted(annotation_gt.value.keys()),
            },
            "witness_symbolic": {
                "type": "object_map",
                "ids": sorted(annotation_gt.value.keys()),
                "key_to_entity_id": {str(key): str(key) for key in annotation_gt.value.keys()},
            },
            "projected_annotation": dict(projected_annotation),
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
            query_id=str(scenario.query_id),
            scene_id=SCENE_ID,
        )


__all__ = ["PhysicsBulbCircuitBrightnessExtremumLabelTask"]
