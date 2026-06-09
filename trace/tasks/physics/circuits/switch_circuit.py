"""Physics circuit task for mixed-switch current-flow bulb counting."""

from __future__ import annotations

import itertools
import json
from collections import deque
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

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
from ...shared.named_colors import named_color
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.render_variation import resolve_render_int
from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.complexity import build_physics_complexity, resolve_physics_complexity_weights
from ..shared.diagram_style import prepare_physics_diagram_style_and_background
from ..shared.style import SUPPORTED_PHYSICS_COLOR_NAMES
from ..shared.support_sampling import resolve_integer_choice
from ..shared.visual_defaults import load_physics_noise_defaults


TASK_ID = "task_physics__switch_circuit__lit_bulb_count"
FAMILY_ID = "physics_circuits_switch_circuit_family"
SCENE_ID = "switch_circuit"
QUERY_ID = "lit_bulb_count"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (QUERY_ID,)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("mixed_branch",)
SWITCH_LABELS: Tuple[str, ...] = ("S1", "S2", "S3", "S4", "S5")
BULB_LABELS: Tuple[str, ...] = ("B1", "B2", "B3", "B4", "B5")
TARGET_SUPPORT: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
POS_NODE = "P"
NEG_NODE = "N"

_TASK_GROUP_DEFAULTS = get_task_group_defaults("physics", "circuits")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=FAMILY_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(task_group="circuits", apply_prob=0.5)


@dataclass(frozen=True)
class _TaskDefaults:
    canvas_width: int = 1280
    canvas_height: int = 720
    panel_left_px: int = 56
    panel_top_px: int = 58
    panel_right_px: int = 1224
    panel_bottom_px: int = 662
    wire_width_px: int = 5
    bulb_radius_px: int = 27
    switch_width_px: int = 74
    switch_height_px: int = 46
    component_label_font_size_px: int = 20
    title_font_size_px: int = 28
    label_stroke_width_px: int = 2


@dataclass(frozen=True)
class _ResolvedAxes:
    query_id: str
    scene_variant: str
    target_answer: int
    accent_color_name: str
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]
    accent_color_name_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _CircuitEdge:
    edge_id: str
    kind: str
    node_a: str
    node_b: str
    label: str
    conductive: bool


@dataclass(frozen=True)
class _SwitchCircuitScenario:
    query_id: str
    scene_variant: str
    target_answer: int
    accent_color_name: str
    switch_states: Dict[str, bool]
    edges: Tuple[_CircuitEdge, ...]
    lit_bulbs: Tuple[str, ...]
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]
    accent_color_name_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RenderedScene:
    image: Image.Image
    annotation_bboxes: List[List[float]]
    scene_entities: List[Dict[str, Any]]
    render_map: Dict[str, Any]


_DEFAULTS = _TaskDefaults()


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
    probability = 1.0 / float(len(values)) if values else 0.0
    return {str(value): float(probability) for value in values}


def _resolve_query_id(params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    explicit = str(params.get("query_id") or "").strip()
    if explicit:
        if explicit != QUERY_ID:
            raise ValueError(f"unsupported query_id for {FAMILY_ID}: {explicit}")
        return QUERY_ID, _probability_map(SUPPORTED_QUERY_IDS, selected=QUERY_ID)
    return QUERY_ID, _probability_map(SUPPORTED_QUERY_IDS)


def _resolve_scene_variant(instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    selected, probabilities = resolve_variant(
        spawn_rng(int(instance_seed), f"{FAMILY_ID}.scene_variant"),
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
        sampling_namespace=f"{FAMILY_ID}.scene_variant",
    )
    return str(selected), {str(key): float(value) for key, value in probabilities.items()}


def _resolve_target_answer(instance_seed: int, params: Mapping[str, Any]) -> Tuple[int, Dict[str, float]]:
    return resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="target_answer_support",
        explicit_key="target_answer",
        fallback_support=TARGET_SUPPORT,
        namespace=f"{FAMILY_ID}.target_answer",
        balanced_flag_key="balanced_target_answer_sampling",
    )


def _resolve_accent_color(instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    selected, probabilities = resolve_variant(
        spawn_rng(int(instance_seed), f"{FAMILY_ID}.accent_color_name"),
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
        sampling_namespace=f"{FAMILY_ID}.accent_color_name",
    )
    return str(selected), {str(key): float(value) for key, value in probabilities.items()}


def _parse_switch_value(raw: Any, *, label: str) -> bool:
    if isinstance(raw, bool):
        return bool(raw)
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        if int(raw) in {0, 1}:
            return bool(int(raw))
    if isinstance(raw, str):
        text = str(raw).strip().lower()
        if text in {"closed", "close", "on", "true", "1", "yes", "y"}:
            return True
        if text in {"open", "off", "false", "0", "no", "n"}:
            return False
    raise ValueError(f"unsupported switch state for {label}: {raw!r}")


def _parse_switch_states(params: Mapping[str, Any]) -> Dict[str, bool] | None:
    raw = params.get("switch_states")
    if raw is None:
        return None
    if not isinstance(raw, Mapping):
        raise ValueError("switch_states must be a mapping from S1..S5 to open/closed values")
    missing = [label for label in SWITCH_LABELS if label not in raw]
    if missing:
        raise ValueError(f"switch_states is missing switch labels: {missing}")
    return {str(label): _parse_switch_value(raw[str(label)], label=str(label)) for label in SWITCH_LABELS}


def _make_edges(switch_states: Mapping[str, bool]) -> Tuple[_CircuitEdge, ...]:
    return (
        _CircuitEdge("S1", "switch", POS_NODE, "T0", "S1", bool(switch_states["S1"])),
        _CircuitEdge("B1", "bulb", "T0", "T1", "B1", True),
        _CircuitEdge("B2", "bulb", "T1", NEG_NODE, "B2", True),
        _CircuitEdge("S2", "switch", POS_NODE, "M0", "S2", bool(switch_states["S2"])),
        _CircuitEdge("B3", "bulb", "M0", "M1", "B3", True),
        _CircuitEdge("S3", "switch", "M1", "MJ", "S3", bool(switch_states["S3"])),
        _CircuitEdge("S4", "switch", "M0", "M2", "S4", bool(switch_states["S4"])),
        _CircuitEdge("B4", "bulb", "M2", "MJ", "B4", True),
        _CircuitEdge("W1", "wire", "MJ", NEG_NODE, "", True),
        _CircuitEdge("S5", "switch", POS_NODE, "D0", "S5", bool(switch_states["S5"])),
        _CircuitEdge("B5", "bulb", "D0", NEG_NODE, "B5", True),
    )


def _adjacency(edges: Iterable[_CircuitEdge], *, exclude_edge_id: str | None = None) -> Dict[str, List[str]]:
    adjacency: Dict[str, List[str]] = {}
    for edge in edges:
        if str(edge.edge_id) == str(exclude_edge_id):
            continue
        if not bool(edge.conductive):
            continue
        adjacency.setdefault(str(edge.node_a), []).append(str(edge.node_b))
        adjacency.setdefault(str(edge.node_b), []).append(str(edge.node_a))
    return adjacency


def _reachable_nodes(start: str, adjacency: Mapping[str, Sequence[str]]) -> set[str]:
    seen = {str(start)}
    queue: deque[str] = deque([str(start)])
    while queue:
        node = queue.popleft()
        for neighbor in adjacency.get(node, ()):
            neighbor = str(neighbor)
            if neighbor in seen:
                continue
            seen.add(neighbor)
            queue.append(neighbor)
    return seen


def _lit_bulbs_from_edges(edges: Sequence[_CircuitEdge]) -> Tuple[str, ...]:
    lit: List[str] = []
    for edge in edges:
        if edge.kind != "bulb":
            continue
        adjacency_without_bulb = _adjacency(edges, exclude_edge_id=str(edge.edge_id))
        from_a = _reachable_nodes(str(edge.node_a), adjacency_without_bulb)
        from_b = _reachable_nodes(str(edge.node_b), adjacency_without_bulb)
        a_to_pos_b_to_neg = POS_NODE in from_a and NEG_NODE in from_b
        a_to_neg_b_to_pos = NEG_NODE in from_a and POS_NODE in from_b
        if a_to_pos_b_to_neg or a_to_neg_b_to_pos:
            lit.append(str(edge.label))
    return tuple(label for label in BULB_LABELS if label in set(lit))


def _enumerate_switch_state_solutions(target_answer: int) -> List[Dict[str, bool]]:
    solutions: List[Dict[str, bool]] = []
    for values in itertools.product((False, True), repeat=len(SWITCH_LABELS)):
        states = {label: bool(values[index]) for index, label in enumerate(SWITCH_LABELS)}
        if len(_lit_bulbs_from_edges(_make_edges(states))) == int(target_answer):
            solutions.append(dict(states))
    return solutions


def _resolve_switch_states(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    target_answer: int,
) -> Tuple[Dict[str, bool], Tuple[str, ...]]:
    explicit_states = _parse_switch_states(params)
    if explicit_states is not None:
        edges = _make_edges(explicit_states)
        lit_bulbs = _lit_bulbs_from_edges(edges)
        if params.get("target_answer") is not None and len(lit_bulbs) != int(target_answer):
            raise ValueError("target_answer must match the lit-bulb count implied by switch_states")
        return dict(explicit_states), tuple(lit_bulbs)
    solutions = _enumerate_switch_state_solutions(int(target_answer))
    if not solutions:
        raise ValueError(f"no switch-state assignment can realize target_answer={target_answer}")
    rng = spawn_rng(int(instance_seed), f"{FAMILY_ID}.switch_states.{int(target_answer)}")
    selected = solutions[int(rng.randrange(len(solutions)))]
    lit_bulbs = _lit_bulbs_from_edges(_make_edges(selected))
    return dict(selected), tuple(lit_bulbs)


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    query_id, query_probs = _resolve_query_id(params)
    scene_variant, scene_probs = _resolve_scene_variant(int(instance_seed), params)
    target_answer, answer_probs = _resolve_target_answer(int(instance_seed), params)
    accent_color, accent_probs = _resolve_accent_color(int(instance_seed), params)
    return _ResolvedAxes(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        target_answer=int(target_answer),
        accent_color_name=str(accent_color),
        query_id_probabilities=dict(query_probs),
        scene_variant_probabilities=dict(scene_probs),
        target_answer_probabilities={str(key): float(value) for key, value in answer_probs.items()},
        accent_color_name_probabilities=dict(accent_probs),
    )


def _make_scenario(instance_seed: int, *, params: Mapping[str, Any]) -> _SwitchCircuitScenario:
    axes = _resolve_axes(int(instance_seed), params=params)
    switch_states, lit_bulbs = _resolve_switch_states(
        instance_seed=int(instance_seed),
        params=params,
        target_answer=int(axes.target_answer),
    )
    target_answer = len(lit_bulbs)
    if params.get("target_answer") is not None and int(params["target_answer"]) != int(target_answer):
        raise ValueError("target_answer must match the generated lit-bulb count")
    return _SwitchCircuitScenario(
        query_id=str(axes.query_id),
        scene_variant=str(axes.scene_variant),
        target_answer=int(target_answer),
        accent_color_name=str(axes.accent_color_name),
        switch_states=dict(switch_states),
        edges=_make_edges(switch_states),
        lit_bulbs=tuple(lit_bulbs),
        query_id_probabilities=dict(axes.query_id_probabilities),
        scene_variant_probabilities=dict(axes.scene_variant_probabilities),
        target_answer_probabilities=dict(axes.target_answer_probabilities),
        accent_color_name_probabilities=dict(axes.accent_color_name_probabilities),
    )


def _resolve_render_defaults(params: Mapping[str, Any], *, instance_seed: int) -> Dict[str, int]:
    keys = (
        "panel_left_px",
        "panel_top_px",
        "panel_right_px",
        "panel_bottom_px",
        "wire_width_px",
        "bulb_radius_px",
        "switch_width_px",
        "switch_height_px",
        "component_label_font_size_px",
        "title_font_size_px",
        "label_stroke_width_px",
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


def _draw_label_tag(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    center: Tuple[float, float],
    font: Any,
    style: Any,
    stroke_width: int,
) -> List[float]:
    text_bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=0)
    text_width = float(text_bbox[2] - text_bbox[0])
    text_height = float(text_bbox[3] - text_bbox[1])
    pad_x = 8.0
    pad_y = 5.0
    cx, cy = float(center[0]), float(center[1])
    tag_bbox = _bbox(
        (
            cx - text_width / 2.0 - pad_x,
            cy - text_height / 2.0 - pad_y,
            cx + text_width / 2.0 + pad_x,
            cy + text_height / 2.0 + pad_y,
        )
    )
    draw.rounded_rectangle(
        tag_bbox,
        radius=7,
        fill=tuple(int(value) for value in style.label_fill_rgb),
        outline=tuple(int(value) for value in style.label_border_rgb),
        width=2,
    )
    text_rgb = tuple(int(value) for value in style.label_rgb)
    text_draw_bbox = draw_centered_text(
        draw,
        text=str(text),
        center=(cx, cy),
        font=font,
        fill=text_rgb,
        stroke_fill=resolve_text_stroke_fill(text_rgb),
        stroke_width=max(0, int(stroke_width) - 1),
    )
    return _union_bbox(tag_bbox, text_draw_bbox)


def _draw_battery(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    font: Any,
    style: Any,
    wire_width: int,
) -> List[float]:
    cx, cy = float(center[0]), float(center[1])
    stroke = tuple(int(value) for value in style.stroke_rgb)
    label_rgb = tuple(int(value) for value in style.label_rgb)
    long_plate = (cx - 22.0, cy - 42.0, cx + 22.0, cy - 42.0)
    short_plate = (cx - 13.0, cy + 18.0, cx + 13.0, cy + 18.0)
    draw.line((cx, cy - 82.0, cx, cy - 42.0), fill=stroke, width=wire_width)
    draw.line((cx, cy + 18.0, cx, cy + 58.0), fill=stroke, width=wire_width)
    draw.line(long_plate, fill=stroke, width=wire_width + 2)
    draw.line(short_plate, fill=stroke, width=wire_width + 2)
    plus_bbox = draw_centered_text(
        draw,
        text="+",
        center=(cx + 42.0, cy - 42.0),
        font=font,
        fill=label_rgb,
        stroke_fill=resolve_text_stroke_fill(label_rgb),
        stroke_width=1,
    )
    minus_bbox = draw_centered_text(
        draw,
        text="-",
        center=(cx + 42.0, cy + 18.0),
        font=font,
        fill=label_rgb,
        stroke_fill=resolve_text_stroke_fill(label_rgb),
        stroke_width=1,
    )
    return _union_bbox((cx - 24.0, cy - 84.0, cx + 24.0, cy + 60.0), plus_bbox, minus_bbox)


def _draw_switch(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    label: str,
    closed: bool,
    font: Any,
    style: Any,
    render_defaults: Mapping[str, int],
    label_side: str = "above",
) -> List[float]:
    cx, cy = float(center[0]), float(center[1])
    width = float(render_defaults["switch_width_px"])
    height = float(render_defaults["switch_height_px"])
    half_w = width / 2.0
    contact_r = 4.8
    left_contact = (cx - half_w * 0.42, cy)
    right_contact = (cx + half_w * 0.42, cy)
    stroke = tuple(int(value) for value in style.stroke_rgb)
    switch_rgb = tuple(int(value) for value in style.secondary_accent_rgb)
    contact_fill = tuple(int(value) for value in style.panel_fill_rgb)
    erase_bbox = (cx - half_w * 0.56, cy - height * 0.50, cx + half_w * 0.56, cy + height * 0.30)
    draw.rounded_rectangle(erase_bbox, radius=8, fill=tuple(int(value) for value in style.panel_fill_rgb))
    draw.ellipse(
        (left_contact[0] - contact_r, left_contact[1] - contact_r, left_contact[0] + contact_r, left_contact[1] + contact_r),
        fill=contact_fill,
        outline=stroke,
        width=2,
    )
    draw.ellipse(
        (right_contact[0] - contact_r, right_contact[1] - contact_r, right_contact[0] + contact_r, right_contact[1] + contact_r),
        fill=contact_fill,
        outline=stroke,
        width=2,
    )
    if closed:
        draw.line((left_contact[0], left_contact[1], right_contact[0], right_contact[1]), fill=switch_rgb, width=5)
    else:
        draw.line((left_contact[0], left_contact[1], right_contact[0] - 7.0, right_contact[1] - height * 0.34), fill=switch_rgb, width=5)
    symbol_bbox = _bbox((cx - half_w * 0.50, cy - height * 0.45, cx + half_w * 0.50, cy + height * 0.22))
    label_dy = -height * 0.70 if str(label_side) == "above" else height * 0.72
    label_bbox = _draw_label_tag(
        draw,
        text=str(label),
        center=(cx, cy + label_dy),
        font=font,
        style=style,
        stroke_width=int(render_defaults["label_stroke_width_px"]),
    )
    return _union_bbox(symbol_bbox, label_bbox)


def _draw_bulb(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    label: str,
    font: Any,
    style: Any,
    accent_rgb: Tuple[int, int, int],
    render_defaults: Mapping[str, int],
    label_side: str = "below",
) -> List[float]:
    cx, cy = float(center[0]), float(center[1])
    radius = float(render_defaults["bulb_radius_px"])
    glass = tuple(int(value) for value in style.panel_alt_fill_rgb)
    outline = tuple(max(0, int(value) - 45) for value in accent_rgb)
    filament = tuple(int(value) for value in style.stroke_rgb)
    bulb_bbox = _bbox((cx - radius, cy - radius, cx + radius, cy + radius))
    draw.ellipse(tuple(float(value) for value in bulb_bbox), fill=glass, outline=outline, width=3)
    draw.arc((cx - radius * 0.45, cy - radius * 0.18, cx + radius * 0.45, cy + radius * 0.48), 205, 335, fill=filament, width=3)
    draw.line((cx - radius * 0.18, cy + radius * 0.48, cx + radius * 0.18, cy + radius * 0.48), fill=filament, width=3)
    label_dy = radius + 25.0 if str(label_side) == "below" else -(radius + 25.0)
    _draw_label_tag(
        draw,
        text=str(label),
        center=(cx, cy + label_dy),
        font=font,
        style=style,
        stroke_width=int(render_defaults["label_stroke_width_px"]),
    )
    # Annotation should point to the physical bulb symbol, not its nearby text label.
    return list(bulb_bbox)


def _draw_wire(draw: ImageDraw.ImageDraw, points: Sequence[Tuple[float, float]], *, style: Any, wire_width: int) -> None:
    draw.line([(float(x), float(y)) for x, y in points], fill=tuple(int(value) for value in style.stroke_rgb), width=int(wire_width))


def _render_scene(
    *,
    image: Image.Image,
    scenario: _SwitchCircuitScenario,
    font_family: str,
    style: Any,
    render_defaults: Mapping[str, int],
) -> _RenderedScene:
    draw = ImageDraw.Draw(image)
    canvas_width, canvas_height = image.size
    panel = (
        float(render_defaults["panel_left_px"]),
        float(render_defaults["panel_top_px"]),
        float(render_defaults["panel_right_px"]),
        float(render_defaults["panel_bottom_px"]),
    )
    draw.rounded_rectangle(
        panel,
        radius=20,
        fill=tuple(int(value) for value in style.panel_fill_rgb),
        outline=tuple(int(value) for value in style.panel_border_rgb),
        width=3,
    )
    title_font = load_font(int(render_defaults["title_font_size_px"]), bold=True, font_family=font_family)
    label_font = load_font(int(render_defaults["component_label_font_size_px"]), bold=True, font_family=font_family)
    text_rgb = tuple(int(value) for value in style.stroke_rgb)
    draw_centered_text(
        draw,
        text="mixed switch circuit",
        center=((panel[0] + panel[2]) * 0.5, panel[1] + 34.0),
        font=title_font,
        fill=text_rgb,
        stroke_fill=resolve_text_stroke_fill(text_rgb),
        stroke_width=1,
    )

    accent_rgb = named_color(str(scenario.accent_color_name))
    wire_width = int(render_defaults["wire_width_px"])
    left_x = 220.0
    right_x = 1080.0
    top_y = 205.0
    upper_mid_y = 318.0
    lower_mid_y = 418.0
    bottom_y = 545.0
    split_left_x = 390.0
    split_right_x = 910.0

    # Rails and branch wires are drawn first so component symbols sit on top.
    _draw_wire(draw, [(left_x, top_y), (left_x, bottom_y)], style=style, wire_width=wire_width)
    _draw_wire(draw, [(right_x, top_y), (right_x, bottom_y)], style=style, wire_width=wire_width)
    battery_bbox = _draw_battery(draw, center=(left_x - 78.0, (top_y + bottom_y) * 0.5), font=label_font, style=style, wire_width=wire_width)
    _draw_wire(draw, [(left_x - 78.0, top_y + 85.0), (left_x, top_y + 85.0)], style=style, wire_width=wire_width)
    _draw_wire(draw, [(left_x - 78.0, bottom_y - 85.0), (left_x, bottom_y - 85.0)], style=style, wire_width=wire_width)

    # Top branch: S1 -> B1 -> B2.
    _draw_wire(draw, [(left_x, top_y), (right_x, top_y)], style=style, wire_width=wire_width)
    # Middle mixed branch with local parallel split: S2 -> (B3/S3 || S4/B4).
    _draw_wire(draw, [(left_x, (upper_mid_y + lower_mid_y) * 0.5), (split_left_x, (upper_mid_y + lower_mid_y) * 0.5)], style=style, wire_width=wire_width)
    _draw_wire(draw, [(split_left_x, upper_mid_y), (split_right_x, upper_mid_y)], style=style, wire_width=wire_width)
    _draw_wire(draw, [(split_left_x, lower_mid_y), (split_right_x, lower_mid_y)], style=style, wire_width=wire_width)
    _draw_wire(draw, [(split_left_x, upper_mid_y), (split_left_x, lower_mid_y)], style=style, wire_width=wire_width)
    _draw_wire(draw, [(split_right_x, upper_mid_y), (split_right_x, lower_mid_y)], style=style, wire_width=wire_width)
    _draw_wire(draw, [(split_right_x, (upper_mid_y + lower_mid_y) * 0.5), (right_x, (upper_mid_y + lower_mid_y) * 0.5)], style=style, wire_width=wire_width)
    # Bottom branch: S5 -> B5.
    _draw_wire(draw, [(left_x, bottom_y), (right_x, bottom_y)], style=style, wire_width=wire_width)

    switch_bboxes = {
        "S1": _draw_switch(
            draw,
            center=(310.0, top_y),
            label="S1",
            closed=bool(scenario.switch_states["S1"]),
            font=label_font,
            style=style,
            render_defaults=render_defaults,
            label_side="above",
        ),
        "S2": _draw_switch(
            draw,
            center=(300.0, (upper_mid_y + lower_mid_y) * 0.5),
            label="S2",
            closed=bool(scenario.switch_states["S2"]),
            font=label_font,
            style=style,
            render_defaults=render_defaults,
            label_side="below",
        ),
        "S3": _draw_switch(
            draw,
            center=(760.0, upper_mid_y),
            label="S3",
            closed=bool(scenario.switch_states["S3"]),
            font=label_font,
            style=style,
            render_defaults=render_defaults,
            label_side="above",
        ),
        "S4": _draw_switch(
            draw,
            center=(550.0, lower_mid_y),
            label="S4",
            closed=bool(scenario.switch_states["S4"]),
            font=label_font,
            style=style,
            render_defaults=render_defaults,
            label_side="below",
        ),
        "S5": _draw_switch(
            draw,
            center=(310.0, bottom_y),
            label="S5",
            closed=bool(scenario.switch_states["S5"]),
            font=label_font,
            style=style,
            render_defaults=render_defaults,
            label_side="above",
        ),
    }
    bulb_bboxes = {
        "B1": _draw_bulb(
            draw,
            center=(555.0, top_y),
            label="B1",
            font=label_font,
            style=style,
            accent_rgb=accent_rgb,
            render_defaults=render_defaults,
            label_side="above",
        ),
        "B2": _draw_bulb(
            draw,
            center=(785.0, top_y),
            label="B2",
            font=label_font,
            style=style,
            accent_rgb=accent_rgb,
            render_defaults=render_defaults,
            label_side="above",
        ),
        "B3": _draw_bulb(
            draw,
            center=(555.0, upper_mid_y),
            label="B3",
            font=label_font,
            style=style,
            accent_rgb=accent_rgb,
            render_defaults=render_defaults,
            label_side="below",
        ),
        "B4": _draw_bulb(
            draw,
            center=(760.0, lower_mid_y),
            label="B4",
            font=label_font,
            style=style,
            accent_rgb=accent_rgb,
            render_defaults=render_defaults,
            label_side="below",
        ),
        "B5": _draw_bulb(
            draw,
            center=(655.0, bottom_y),
            label="B5",
            font=label_font,
            style=style,
            accent_rgb=accent_rgb,
            render_defaults=render_defaults,
            label_side="below",
        ),
    }
    bulb_bboxes = {key: _clip_bbox(value, width=canvas_width, height=canvas_height) for key, value in sorted(bulb_bboxes.items())}
    switch_bboxes = {key: _clip_bbox(value, width=canvas_width, height=canvas_height) for key, value in sorted(switch_bboxes.items())}
    annotation_bboxes = [list(bulb_bboxes[label]) for label in BULB_LABELS if label in set(scenario.lit_bulbs)]

    entities: List[Dict[str, Any]] = [
        {
            "entity_id": "battery",
            "entity_type": "ideal_battery",
            "bbox_px": _clip_bbox(battery_bbox, width=canvas_width, height=canvas_height),
            "meta": {"positive_node": POS_NODE, "negative_node": NEG_NODE},
        }
    ]
    for label in BULB_LABELS:
        entities.append(
            {
                "entity_id": str(label),
                "entity_type": "bulb",
                "bbox_px": list(bulb_bboxes[str(label)]),
                "meta": {
                    "label": str(label),
                    "is_lit": str(label) in set(scenario.lit_bulbs),
                },
            }
        )
    for label in SWITCH_LABELS:
        entities.append(
            {
                "entity_id": str(label),
                "entity_type": "switch",
                "bbox_px": list(switch_bboxes[str(label)]),
                "meta": {
                    "label": str(label),
                    "state": "closed" if bool(scenario.switch_states[str(label)]) else "open",
                    "conductive": bool(scenario.switch_states[str(label)]),
                },
            }
        )

    render_map = {
        "panel_bbox": _bbox(panel),
        "scene_variant": str(scenario.scene_variant),
        "battery_bbox": _clip_bbox(battery_bbox, width=canvas_width, height=canvas_height),
        "bulb_bboxes": dict(bulb_bboxes),
        "switch_bboxes": dict(switch_bboxes),
        "switch_states": {
            label: ("closed" if bool(scenario.switch_states[label]) else "open")
            for label in SWITCH_LABELS
        },
        "lit_bulbs": list(scenario.lit_bulbs),
        "annotation_bbox_set": [list(bbox) for bbox in annotation_bboxes],
    }
    return _RenderedScene(
        image=image,
        annotation_bboxes=[list(bbox) for bbox in annotation_bboxes],
        scene_entities=[dict(entity) for entity in entities],
        render_map=dict(render_map),
    )


def _build_complexity(scenario: _SwitchCircuitScenario) -> TaskComplexity:
    weights = resolve_physics_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=FAMILY_ID)
    closed_count = sum(1 for value in scenario.switch_states.values() if bool(value))
    return build_physics_complexity(
        weights=weights,
        components={
            "visual_scan": min(1.0, 0.34 + 0.04 * len(SWITCH_LABELS)),
            "connectivity_reasoning": min(1.0, 0.44 + 0.05 * closed_count),
            "ambiguity": 0.16,
            "output_burden": 0.20,
        },
    )


def _prompt_examples() -> Tuple[str, str]:
    return (
        json.dumps(
            {
                "annotation": [[120, 140, 180, 200], [240, 140, 300, 200]],
                "answer": 2,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        json.dumps({"answer": 2}, ensure_ascii=False, separators=(",", ":")),
    )


@register_task
class PhysicsSwitchCircuitLitBulbCountTask:
    """Count bulbs on in a mixed branch circuit with open and closed switches."""

    task_id = TASK_ID
    domain = "physics"
    task_group = "circuits"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        params = dict(params or {})
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_seed = int(instance_seed) + (attempt_index * 7919)
            try:
                scenario = _make_scenario(attempt_seed, params=params)
                render_defaults = _resolve_render_defaults(params, instance_seed=attempt_seed)
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
                scenario=scenario,
                font_family=str(font_family),
                style=diagram_style,
                render_defaults=render_defaults,
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
            answer_gt = TypedValue(type="integer", value=int(scenario.target_answer))
            annotation_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in rendered.annotation_bboxes])
            json_example, json_example_answer_only = _prompt_examples()
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
            complexity = _build_complexity(scenario)
            trace_payload = {
                "scene_ir": {
                    "scene_kind": "physics_switch_circuit_mixed_branch",
                    "entities": [dict(entity) for entity in rendered.scene_entities],
                    "relations": {
                        "query_id": QUERY_ID,
                        "positive_node": POS_NODE,
                        "negative_node": NEG_NODE,
                        "lit_bulb_count": int(scenario.target_answer),
                        "lit_bulbs": list(scenario.lit_bulbs),
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
                        "target_answer": int(scenario.target_answer),
                        "answer_support": list(TARGET_SUPPORT),
                        "scene_variant": str(scenario.scene_variant),
                    },
                },
                "render_spec": {
                    "canvas_width": int(image.size[0]),
                    "canvas_height": int(image.size[1]),
                    "font": {
                        "font_family": str(font_family),
                        "font_asset_version": font_asset_version(),
                        "font_asset": font_record.to_trace(),
                        "scope": "switch_circuit_diagram",
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
                    "target_answer": int(scenario.target_answer),
                    "lit_bulbs": list(scenario.lit_bulbs),
                    "switch_states": {
                        label: ("closed" if bool(scenario.switch_states[label]) else "open")
                        for label in SWITCH_LABELS
                    },
                    "edges": [
                        {
                            "edge_id": str(edge.edge_id),
                            "kind": str(edge.kind),
                            "node_a": str(edge.node_a),
                            "node_b": str(edge.node_b),
                            "label": str(edge.label),
                            "conductive": bool(edge.conductive),
                        }
                        for edge in scenario.edges
                    ],
                    "annotation_entity_ids": list(scenario.lit_bulbs),
                },
                "sampling": {
                    "query_id_probabilities": dict(scenario.query_id_probabilities),
                    "scene_variant_probabilities": dict(scenario.scene_variant_probabilities),
                    "target_answer_probabilities": dict(scenario.target_answer_probabilities),
                    "accent_color_name_probabilities": dict(scenario.accent_color_name_probabilities),
                },
                "witness_symbolic": {
                    "type": "bbox_set",
                    "entity_ids": list(scenario.lit_bulbs),
                },
                "projected_annotation": {
                    "type": "bbox_set",
                    "bbox_set": [list(bbox) for bbox in annotation_gt.value],
                    "pixel_bbox_set": [list(bbox) for bbox in annotation_gt.value],
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
        raise RuntimeError(f"failed to generate switch-circuit instance after {max_attempts} attempts: {last_error}")


__all__ = [
    "BULB_LABELS",
    "PhysicsSwitchCircuitLitBulbCountTask",
    "SWITCH_LABELS",
    "_lit_bulbs_from_edges",
    "_make_edges",
]
