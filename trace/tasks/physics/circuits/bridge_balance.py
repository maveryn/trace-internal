"""Physics bridge-circuit task for balanced Wheatstone resistance solves."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
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
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.diagram_style import prepare_physics_diagram_style_and_background
from ..shared.style import SUPPORTED_PHYSICS_COLOR_NAMES
from ..shared.support_sampling import resolve_integer_choice
from ..shared.visual_defaults import load_physics_noise_defaults


TASK_NAMESPACE = "physics_circuits_bridge_missing_resistance"
SCENE_ID = "bridge_circuit"
QUERY_ID = "missing_bridge_resistance"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (QUERY_ID,)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("rectangular_bridge",)
RESISTOR_LABELS: Tuple[str, ...] = ("R1", "R2", "R3", "R4")
DEFAULT_TARGET_SUPPORT: Tuple[int, ...] = tuple(range(1, 21))
DEFAULT_MAX_RESISTANCE = 60

_TASK_GROUP_DEFAULTS = get_scene_defaults("physics", "circuits")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_NAMESPACE,
)
POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(scene_id="circuits", apply_prob=0.5)


@dataclass(frozen=True)
class _BridgeResistor:
    """One semantic bridge resistor."""

    label: str
    value_ohm: int
    is_missing: bool


@dataclass(frozen=True)
class _BridgeScenario:
    """Resolved bridge-circuit scenario."""

    query_id: str
    scene_variant: str
    accent_color_name: str
    missing_resistor: str
    target_answer: int
    resistors: Tuple[_BridgeResistor, ...]
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    accent_color_name_probabilities: Dict[str, float]
    missing_resistor_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


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
    x0, y0, x1, y1 = [float(value) for value in bbox]
    return _bbox(
        (
            max(0.0, min(float(width), min(x0, x1))),
            max(0.0, min(float(height), min(y0, y1))),
            max(0.0, min(float(width), max(x0, x1))),
            max(0.0, min(float(height), max(y0, y1))),
        )
    )


def _probability_map(values: Sequence[str], selected: str | None = None) -> Dict[str, float]:
    if selected is not None:
        return {str(value): (1.0 if str(value) == str(selected) else 0.0) for value in values}
    if not values:
        return {}
    probability = 1.0 / float(len(values))
    return {str(value): float(probability) for value in values}


def _resolve_query_id(params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    explicit = str(params.get("query_id") or "").strip()
    if explicit:
        if explicit != QUERY_ID:
            raise ValueError(f"unsupported query_id for {TASK_NAMESPACE}: {explicit}")
        return QUERY_ID, _probability_map(SUPPORTED_QUERY_IDS, selected=QUERY_ID)
    return QUERY_ID, _probability_map(SUPPORTED_QUERY_IDS)


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


def _resolve_accent_color(instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    rng = spawn_rng(int(instance_seed), f"{TASK_NAMESPACE}.accent_color_name")
    selected, probabilities = resolve_variant(
        rng,
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


def _resolve_missing_resistor(instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    rng = spawn_rng(int(instance_seed), f"{TASK_NAMESPACE}.missing_resistor")
    selected, probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=RESISTOR_LABELS,
        explicit_key="missing_resistor",
        weights_key="missing_resistor_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=RESISTOR_LABELS,
        balance_flag_key="balanced_missing_resistor_sampling",
        explicit_key="missing_resistor",
        weights_key="missing_resistor_weights",
        sampling_namespace=f"{TASK_NAMESPACE}.missing_resistor",
    )
    return str(selected), {str(key): float(value) for key, value in probabilities.items()}


def _resolve_target_answer(instance_seed: int, params: Mapping[str, Any]) -> Tuple[int, Dict[str, float]]:
    explicit = params.get("target_resistance_ohm", params.get("target_answer"))
    support_key = "target_answer_support"
    if explicit is not None:
        params = dict(params)
        params["target_answer"] = int(explicit)
    target, probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=support_key,
        explicit_key="target_answer",
        fallback_support=DEFAULT_TARGET_SUPPORT,
        namespace=f"{TASK_NAMESPACE}.target_answer",
        balanced_flag_key="balanced_target_answer_sampling",
    )
    return int(target), {str(key): float(value) for key, value in probabilities.items()}


def _balance_holds(values_by_label: Mapping[str, int]) -> bool:
    return int(values_by_label["R1"]) * int(values_by_label["R4"]) == int(values_by_label["R2"]) * int(values_by_label["R3"])


def _explicit_resistor_values(params: Mapping[str, Any]) -> Dict[str, int] | None:
    raw = params.get("resistor_values")
    if raw is None:
        return None
    if isinstance(raw, Mapping):
        values = {label: int(raw[label]) for label in RESISTOR_LABELS}
    elif not isinstance(raw, (str, bytes)) and isinstance(raw, Sequence) and len(raw) == len(RESISTOR_LABELS):
        values = {label: int(raw[index]) for index, label in enumerate(RESISTOR_LABELS)}
    else:
        raise ValueError("resistor_values must be a mapping with R1..R4 or a four-value sequence")
    if any(int(value) <= 0 for value in values.values()):
        raise ValueError("resistor_values must contain positive integers")
    if not _balance_holds(values):
        raise ValueError("resistor_values must satisfy the balanced bridge equation R1*R4 = R2*R3")
    return dict(values)


def _construct_balanced_values(
    *,
    instance_seed: int,
    missing_resistor: str,
    target_answer: int,
    params: Mapping[str, Any],
) -> Dict[str, int]:
    explicit_values = _explicit_resistor_values(params)
    if explicit_values is not None:
        if int(explicit_values[str(missing_resistor)]) != int(target_answer):
            raise ValueError("target_answer must match the value of the selected missing_resistor")
        return explicit_values

    max_resistance = int(params.get("component_value_max", group_default(_GEN_DEFAULTS, "component_value_max", DEFAULT_MAX_RESISTANCE)))
    if int(max_resistance) < int(target_answer):
        raise ValueError("component_value_max must be at least the target answer")

    pair_options = [(2, 3), (2, 5), (2, 7), (2, 9), (3, 2), (3, 4), (3, 5), (3, 7), (3, 8)]
    rng = spawn_rng(int(instance_seed), f"{TASK_NAMESPACE}.bridge_values.{str(missing_resistor)}.{int(target_answer)}")
    shuffled = list(pair_options)
    rng.shuffle(shuffled)
    fallback: Dict[str, int] | None = None
    for multiplier, base in shuffled:
        t = int(target_answer)
        c = int(multiplier)
        r = int(base)
        if str(missing_resistor) == "R1":
            values = {"R1": t, "R2": c * t, "R3": r, "R4": c * r}
        elif str(missing_resistor) == "R2":
            values = {"R1": c * t, "R2": t, "R3": c * r, "R4": r}
        elif str(missing_resistor) == "R3":
            values = {"R1": r, "R2": c * r, "R3": t, "R4": c * t}
        elif str(missing_resistor) == "R4":
            values = {"R1": c * r, "R2": r, "R3": c * t, "R4": t}
        else:
            raise ValueError(f"unsupported missing resistor: {missing_resistor}")
        if max(values.values()) > int(max_resistance):
            continue
        if not _balance_holds(values):
            raise RuntimeError("bridge construction produced an unbalanced resistor set")
        if fallback is None and len(set(values.values())) >= 3:
            fallback = dict(values)
        if len(set(values.values())) == 4:
            return dict(values)
    if fallback is not None:
        return dict(fallback)
    raise RuntimeError("failed to construct a balanced bridge resistor set")


def _make_scenario(instance_seed: int, params: Mapping[str, Any]) -> _BridgeScenario:
    query_id, query_probs = _resolve_query_id(params)
    scene_variant, scene_probs = _resolve_scene_variant(int(instance_seed), params)
    accent_color_name, accent_probs = _resolve_accent_color(int(instance_seed), params)
    missing_resistor, missing_probs = _resolve_missing_resistor(int(instance_seed), params)
    target_answer, target_probs = _resolve_target_answer(int(instance_seed), params)
    values = _construct_balanced_values(
        instance_seed=int(instance_seed),
        missing_resistor=str(missing_resistor),
        target_answer=int(target_answer),
        params=params,
    )
    resistors = tuple(
        _BridgeResistor(
            label=str(label),
            value_ohm=int(values[str(label)]),
            is_missing=str(label) == str(missing_resistor),
        )
        for label in RESISTOR_LABELS
    )
    return _BridgeScenario(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        accent_color_name=str(accent_color_name),
        missing_resistor=str(missing_resistor),
        target_answer=int(target_answer),
        resistors=resistors,
        query_id_probabilities=dict(query_probs),
        scene_variant_probabilities=dict(scene_probs),
        accent_color_name_probabilities=dict(accent_probs),
        missing_resistor_probabilities=dict(missing_probs),
        target_answer_probabilities=dict(target_probs),
    )


def _draw_label_tag(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    center: Tuple[float, float],
    font: Any,
    style: Any,
    fill_rgb: Tuple[int, int, int] | None = None,
    outline_rgb: Tuple[int, int, int] | None = None,
    text_rgb: Tuple[int, int, int] | None = None,
) -> List[float]:
    text_bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=0)
    text_w = float(text_bbox[2] - text_bbox[0])
    text_h = float(text_bbox[3] - text_bbox[1])
    cx, cy = float(center[0]), float(center[1])
    pad_x = 10.0
    pad_y = 6.0
    tag = _bbox((cx - (text_w * 0.5) - pad_x, cy - (text_h * 0.5) - pad_y, cx + (text_w * 0.5) + pad_x, cy + (text_h * 0.5) + pad_y))
    fill = tuple(int(value) for value in (fill_rgb or style.label_fill_rgb))
    outline = tuple(int(value) for value in (outline_rgb or style.label_border_rgb))
    text_color = tuple(int(value) for value in (text_rgb or style.stroke_rgb))
    draw.rounded_rectangle(tuple(float(value) for value in tag), radius=7, fill=fill, outline=outline, width=2)
    text_box = draw_centered_text(
        draw,
        text=str(text),
        center=(cx, cy),
        font=font,
        fill=text_color,
        stroke_fill=resolve_text_stroke_fill(text_color),
        stroke_width=1,
    )
    return _union_bbox(tag, text_box)


def _draw_vertical_resistor(
    draw: ImageDraw.ImageDraw,
    *,
    center_x: float,
    y0: float,
    y1: float,
    style: Any,
    wire_width: int,
) -> List[float]:
    stroke = tuple(int(value) for value in style.stroke_rgb)
    top = float(min(y0, y1))
    bottom = float(max(y0, y1))
    lead = 20.0
    zig_top = top + lead
    zig_bottom = bottom - lead
    amplitude = 20.0
    points: List[Tuple[float, float]] = [(float(center_x), top), (float(center_x), zig_top)]
    segment_count = 8
    for index in range(segment_count + 1):
        y_value = zig_top + ((zig_bottom - zig_top) * index / float(segment_count))
        if index == 0 or index == segment_count:
            x_value = float(center_x)
        else:
            x_value = float(center_x) + (amplitude if index % 2 else -amplitude)
        points.append((float(x_value), float(y_value)))
    points.append((float(center_x), bottom))
    draw.line(points, fill=stroke, width=max(2, int(wire_width)), joint="curve")
    return _bbox((float(center_x) - amplitude - wire_width, top, float(center_x) + amplitude + wire_width, bottom))


def _draw_battery(
    draw: ImageDraw.ImageDraw,
    *,
    x: float,
    y_top: float,
    y_bottom: float,
    style: Any,
    font: Any,
    wire_width: int,
) -> List[float]:
    stroke = tuple(int(value) for value in style.stroke_rgb)
    guide = tuple(int(value) for value in style.guide_rgb)
    mid_y = (float(y_top) + float(y_bottom)) * 0.5
    plate_top = mid_y - 25.0
    plate_bottom = mid_y + 25.0
    draw.line((x, y_top, x, plate_top - 18.0), fill=stroke, width=int(wire_width))
    draw.line((x, plate_bottom + 18.0, x, y_bottom), fill=stroke, width=int(wire_width))
    draw.line((x - 42.0, plate_top, x + 42.0, plate_top), fill=stroke, width=max(3, int(wire_width) + 2))
    draw.line((x - 28.0, plate_bottom, x + 28.0, plate_bottom), fill=stroke, width=max(3, int(wire_width) + 2))
    plus_box = draw_centered_text(
        draw,
        text="+",
        center=(x + 62.0, plate_top - 2.0),
        font=font,
        fill=stroke,
        stroke_fill=resolve_text_stroke_fill(stroke),
        stroke_width=1,
    )
    minus_box = draw_centered_text(
        draw,
        text="-",
        center=(x + 62.0, plate_bottom),
        font=font,
        fill=guide,
        stroke_fill=resolve_text_stroke_fill(guide),
        stroke_width=1,
    )
    return _union_bbox((x - 46.0, plate_top - 24.0, x + 70.0, plate_bottom + 24.0), plus_box, minus_box)


def _draw_meter(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    style: Any,
    accent_rgb: Tuple[int, int, int],
    label_font: Any,
    wire_width: int,
) -> List[float]:
    cx, cy = float(center[0]), float(center[1])
    stroke = tuple(int(value) for value in style.stroke_rgb)
    fill = tuple(int(value) for value in style.panel_alt_fill_rgb)
    radius = 34.0
    circle = _bbox((cx - radius, cy - radius, cx + radius, cy + radius))
    draw.ellipse(tuple(float(value) for value in circle), fill=fill, outline=stroke, width=3)
    draw.arc((cx - 21.0, cy - 18.0, cx + 21.0, cy + 24.0), start=205, end=335, fill=tuple(int(value) for value in style.guide_rgb), width=2)
    draw.line((cx, cy + 10.0, cx, cy - 14.0), fill=accent_rgb, width=max(2, int(wire_width) - 1))
    letter_box = draw_centered_text(
        draw,
        text="G",
        center=(cx, cy + 14.0),
        font=label_font,
        fill=stroke,
        stroke_fill=resolve_text_stroke_fill(stroke),
        stroke_width=1,
    )
    readout_box = _draw_label_tag(
        draw,
        text="G=0",
        center=(cx, cy + 60.0),
        font=label_font,
        style=style,
    )
    return _union_bbox(circle, letter_box, readout_box)


def _render_scene(
    *,
    image: Image.Image,
    scenario: _BridgeScenario,
    font_family: str,
    style: Any,
    render_defaults: Mapping[str, Any],
) -> Tuple[Image.Image, Dict[str, List[float]], Dict[str, Any]]:
    draw = ImageDraw.Draw(image)
    canvas_width, canvas_height = image.size
    title_font = load_font(28, bold=True, font_family=font_family)
    label_font = load_font(int(render_defaults.get("component_label_font_size_px", 20)), bold=True, font_family=font_family)
    small_font = load_font(22, bold=True, font_family=font_family)
    wire_width = int(render_defaults.get("wire_width_px", 5))
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
        text="Balanced bridge circuit",
        center=((panel[0] + panel[2]) * 0.5, panel[1] + 34.0),
        font=title_font,
        fill=text_rgb,
        stroke_fill=resolve_text_stroke_fill(text_rgb),
        stroke_width=1,
    )

    stroke = tuple(int(value) for value in style.stroke_rgb)
    accent_rgb = named_color(str(scenario.accent_color_name))
    target_rgb = named_color("red")
    target_fill = (255, 236, 236)

    top_y = 152.0
    bottom_y = 560.0
    mid_y = (top_y + bottom_y) * 0.5
    source_x = 238.0
    left_branch_x = 520.0
    right_branch_x = 850.0
    right_bus_x = 1006.0
    meter_center = ((left_branch_x + right_branch_x) * 0.5, mid_y)

    _draw_battery(draw, x=source_x, y_top=top_y, y_bottom=bottom_y, style=style, font=small_font, wire_width=wire_width)
    draw.line((source_x, top_y, right_bus_x, top_y), fill=stroke, width=wire_width)
    draw.line((source_x, bottom_y, right_bus_x, bottom_y), fill=stroke, width=wire_width)
    draw.line((right_bus_x, top_y, right_bus_x, bottom_y), fill=stroke, width=wire_width)

    positions = {
        "R1": (left_branch_x, top_y + 42.0, mid_y - 34.0, left_branch_x - 112.0, (top_y + mid_y) * 0.5),
        "R2": (left_branch_x, mid_y + 34.0, bottom_y - 42.0, left_branch_x - 112.0, (mid_y + bottom_y) * 0.5),
        "R3": (right_branch_x, top_y + 42.0, mid_y - 34.0, right_branch_x + 112.0, (top_y + mid_y) * 0.5),
        "R4": (right_branch_x, mid_y + 34.0, bottom_y - 42.0, right_branch_x + 112.0, (mid_y + bottom_y) * 0.5),
    }
    annotation: Dict[str, List[float]] = {}
    resistor_bboxes: Dict[str, List[float]] = {}
    resistor_label_bboxes: Dict[str, List[float]] = {}
    resistor_symbol_bboxes: Dict[str, List[float]] = {}
    for spec in scenario.resistors:
        x, y0, y1, label_x, label_y = positions[str(spec.label)]
        if str(spec.label) in {"R1", "R3"}:
            draw.line((float(x), top_y, float(x), float(y0)), fill=stroke, width=wire_width)
            draw.line((float(x), float(y1), float(x), mid_y), fill=stroke, width=wire_width)
        else:
            draw.line((float(x), mid_y, float(x), float(y0)), fill=stroke, width=wire_width)
            draw.line((float(x), float(y1), float(x), bottom_y), fill=stroke, width=wire_width)
        symbol_box = _draw_vertical_resistor(
            draw,
            center_x=float(x),
            y0=float(y0),
            y1=float(y1),
            style=style,
            wire_width=wire_width,
        )
        label_text = f"{spec.label}=?" if bool(spec.is_missing) else f"{spec.label}={int(spec.value_ohm)} ohm"
        label_box = _draw_label_tag(
            draw,
            text=label_text,
            center=(float(label_x), float(label_y)),
            font=label_font,
            style=style,
            fill_rgb=target_fill if bool(spec.is_missing) else None,
            outline_rgb=target_rgb if bool(spec.is_missing) else None,
            text_rgb=target_rgb if bool(spec.is_missing) else None,
        )
        full_box = _union_bbox(symbol_box, label_box)
        resistor_bboxes[str(spec.label)] = list(full_box)
        resistor_label_bboxes[str(spec.label)] = list(label_box)
        resistor_symbol_bboxes[str(spec.label)] = list(symbol_box)
        if bool(spec.is_missing):
            annotation["target_resistor"] = list(full_box)
        else:
            annotation[str(spec.label)] = list(full_box)

    draw.line((left_branch_x, mid_y, meter_center[0] - 38.0, mid_y), fill=stroke, width=wire_width)
    draw.line((meter_center[0] + 38.0, mid_y, right_branch_x, mid_y), fill=stroke, width=wire_width)
    zero_meter_bbox = _draw_meter(
        draw,
        center=meter_center,
        style=style,
        accent_rgb=accent_rgb,
        label_font=small_font,
        wire_width=wire_width,
    )
    annotation["zero_meter"] = list(zero_meter_bbox)
    for node in ((left_branch_x, mid_y), (right_branch_x, mid_y), (left_branch_x, top_y), (right_branch_x, top_y), (left_branch_x, bottom_y), (right_branch_x, bottom_y)):
        cx, cy = float(node[0]), float(node[1])
        draw.ellipse((cx - 5.0, cy - 5.0, cx + 5.0, cy + 5.0), fill=stroke)

    annotation = {
        str(key): _clip_bbox(value, width=int(canvas_width), height=int(canvas_height))
        for key, value in sorted(annotation.items())
    }
    render_map = {
        "panel_bbox": _bbox(panel),
        "scene_variant": str(scenario.scene_variant),
        "missing_resistor": str(scenario.missing_resistor),
        "target_answer": int(scenario.target_answer),
        "resistor_values": {str(spec.label): int(spec.value_ohm) for spec in scenario.resistors},
        "resistor_bboxes": {str(key): _clip_bbox(value, width=int(canvas_width), height=int(canvas_height)) for key, value in resistor_bboxes.items()},
        "resistor_symbol_bboxes": {str(key): _clip_bbox(value, width=int(canvas_width), height=int(canvas_height)) for key, value in resistor_symbol_bboxes.items()},
        "resistor_label_bboxes": {str(key): _clip_bbox(value, width=int(canvas_width), height=int(canvas_height)) for key, value in resistor_label_bboxes.items()},
        "zero_meter_bbox": _clip_bbox(zero_meter_bbox, width=int(canvas_width), height=int(canvas_height)),
        "annotation_bbox_map": dict(annotation),
        "bridge_equation": "R1*R4 = R2*R3",
        "wire_segments": {
            "top_bus": _bbox((source_x, top_y, right_bus_x, top_y)),
            "bottom_bus": _bbox((source_x, bottom_y, right_bus_x, bottom_y)),
            "right_bus": _bbox((right_bus_x, top_y, right_bus_x, bottom_y)),
            "meter_branch": _bbox((left_branch_x, mid_y, right_branch_x, mid_y)),
        },
    }
    return image, annotation, render_map


def _build_prompt_examples() -> Tuple[str, str]:
    annotation_example = {
        "R1": [0, 0, 4, 3],
        "R2": [5, 0, 9, 3],
        "R4": [10, 0, 14, 3],
        "target_resistor": [15, 0, 19, 3],
        "zero_meter": [20, 0, 24, 3],
    }
    return (
        json.dumps({"annotation": annotation_example, "answer": 6}, ensure_ascii=False, separators=(",", ":")),
        json.dumps({"answer": 6}, ensure_ascii=False, separators=(",", ":")),
    )




@register_task
class PhysicsBridgeCircuitMissingResistanceValueTask:
    """Solve a missing resistance from a balanced bridge circuit."""

    task_id = "task_physics__bridge_circuit__bridge_missing_resistance_value"
    domain = "physics"
    scene_id = "circuits"
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
            canvas_width=canvas_width,
            canvas_height=canvas_height,
            require_grid=True,
        )
        font_family = sample_font_family(
            role="readout",
            instance_seed=int(instance_seed),
            namespace=f"{TASK_NAMESPACE}.font",
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
                "answer_hint_missing_bridge_resistance",
                "annotation_hint_missing_bridge_resistance",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        answer_gt = TypedValue(type="integer", value=int(scenario.target_answer))
        annotation_gt = TypedValue(type="keyed_bbox_map", value={str(key): list(value) for key, value in annotation_map.items()})
        json_example, json_example_answer_only = _build_prompt_examples()
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            scene_id=self.scene_id,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(scenario.query_id),
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults["answer_hint_missing_bridge_resistance"]),
                "annotation_hint": str(prompt_defaults["annotation_hint_missing_bridge_resistance"]),
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
        resistor_values = {str(spec.label): int(spec.value_ohm) for spec in scenario.resistors}
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"physics_bridge_circuit_{str(scenario.scene_variant)}",
                "entities": [
                    {
                        "entity_id": str(spec.label),
                        "entity_type": "bridge_resistor",
                        "label": str(spec.label),
                        "value_ohm": int(spec.value_ohm),
                        "is_missing": bool(spec.is_missing),
                    }
                    for spec in scenario.resistors
                ],
                "relations": {
                    "bridge_equation": "R1*R4 = R2*R3",
                    "zero_meter_reading": 0,
                    "missing_resistor": str(scenario.missing_resistor),
                    "target_answer": int(scenario.target_answer),
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
                    "missing_resistor": str(scenario.missing_resistor),
                    "target_answer": int(scenario.target_answer),
                    "scene_variant_probabilities": dict(scenario.scene_variant_probabilities),
                    "query_id_probabilities": dict(scenario.query_id_probabilities),
                    "accent_color_name_probabilities": dict(scenario.accent_color_name_probabilities),
                    "missing_resistor_probabilities": dict(scenario.missing_resistor_probabilities),
                    "target_answer_probabilities": dict(scenario.target_answer_probabilities),
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
                    "scope": "bridge_circuit_diagram",
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
                "resistor_values": dict(resistor_values),
                "missing_resistor": str(scenario.missing_resistor),
                "target_answer": int(scenario.target_answer),
                "bridge_balance_product_left": int(resistor_values["R1"]) * int(resistor_values["R4"]),
                "bridge_balance_product_right": int(resistor_values["R2"]) * int(resistor_values["R3"]),
                "zero_meter_reading": 0,
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
            task_versions=default_task_versions(),
            query_id=str(scenario.query_id),
            scene_id=SCENE_ID,
        )


__all__ = ["PhysicsBridgeCircuitMissingResistanceValueTask"]
