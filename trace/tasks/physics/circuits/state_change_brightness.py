"""Physics circuit task for bulb-brightness changes after a switch action."""

from __future__ import annotations

import json
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
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.complexity import build_physics_complexity, resolve_physics_complexity_weights
from ..shared.diagram_style import prepare_physics_diagram_style_and_background
from ..shared.style import SUPPORTED_PHYSICS_COLOR_NAMES
from ..shared.visual_defaults import load_physics_noise_defaults


TASK_ID = "task_physics__circuit_state_change__bulb_brightness_change_label"
FAMILY_ID = "physics_circuits_state_change_bulb_brightness_family"
SCENE_ID = "circuit_state_change"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "brightens_after_switch_change",
    "dims_after_switch_change",
    "turns_on_after_switch_change",
    "turns_off_after_switch_change",
)
BULB_LABELS: Tuple[str, ...] = ("B1", "B2", "B3", "B4", "B5")
BULB_ROLES: Tuple[str, ...] = (
    "series_bulb",
    "main_branch_bulb",
    "switched_branch_bulb",
    "reference_branch_bulb_1",
    "reference_branch_bulb_2",
)
DEFAULT_RESISTANCE_OPTIONS: Tuple[int, ...] = (2, 3, 4, 5, 6, 8, 10, 12)
EPS = 1e-9

_TASK_GROUP_DEFAULTS = get_task_group_defaults("physics", "circuits")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=FAMILY_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(task_group="circuits", apply_prob=0.5)


@dataclass(frozen=True)
class _BulbSpec:
    role: str
    label: str
    resistance_ohm: int
    power_before: float
    power_after: float
    change_class: str


@dataclass(frozen=True)
class _Scenario:
    query_id: str
    switch_action: str
    accent_color_name: str
    target_label: str
    bulbs: Tuple[_BulbSpec, ...]
    correct_label: str
    query_id_probabilities: Dict[str, float]
    switch_action_probabilities: Dict[str, float]
    accent_color_name_probabilities: Dict[str, float]
    target_label_probabilities: Dict[str, float]


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


def _resolve_query_id(instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    selected, probabilities = resolve_variant(
        spawn_rng(int(instance_seed), f"{FAMILY_ID}.query_id"),
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
        sampling_namespace=f"{FAMILY_ID}.query_id",
    )
    return str(selected), {str(key): float(value) for key, value in probabilities.items()}


def _allowed_switch_actions(query_id: str) -> Tuple[str, ...]:
    if str(query_id) == "turns_on_after_switch_change":
        return ("closes",)
    if str(query_id) == "turns_off_after_switch_change":
        return ("opens",)
    return ("closes", "opens")


def _resolve_switch_action(instance_seed: int, params: Mapping[str, Any], *, query_id: str) -> Tuple[str, Dict[str, float]]:
    allowed = _allowed_switch_actions(str(query_id))
    explicit = str(params.get("switch_action") or "").strip().lower()
    if explicit:
        if explicit in {"close", "closed"}:
            explicit = "closes"
        if explicit in {"open", "opened"}:
            explicit = "opens"
        if explicit not in set(allowed):
            raise ValueError(f"switch_action={explicit!r} is incompatible with query_id={query_id!r}")
        return str(explicit), _probability_map(allowed, selected=str(explicit))
    if len(allowed) == 1:
        return str(allowed[0]), _probability_map(allowed, selected=str(allowed[0]))
    index = int(hash64(int(instance_seed), f"{FAMILY_ID}.switch_action", 0) % len(allowed))
    return str(allowed[index]), _probability_map(allowed)


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


def _resolve_target_label(instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    explicit = str(params.get("target_label") or params.get("target_answer") or "").strip()
    if explicit:
        if explicit not in set(BULB_LABELS):
            raise ValueError(f"target label must be one of {BULB_LABELS}")
        return str(explicit), _probability_map(BULB_LABELS, selected=str(explicit))
    index = int(hash64(int(instance_seed), f"{FAMILY_ID}.target_label", 0) % len(BULB_LABELS))
    return str(BULB_LABELS[index]), _probability_map(BULB_LABELS)


def _resistance_options(params: Mapping[str, Any]) -> Tuple[int, ...]:
    raw = params.get("resistance_options", group_default(_GEN_DEFAULTS, "resistance_options", DEFAULT_RESISTANCE_OPTIONS))
    if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
        raise ValueError("resistance_options must be a sequence of positive integers")
    values = tuple(dict.fromkeys(int(value) for value in raw))
    if len(values) < len(BULB_ROLES) or any(value <= 0 for value in values):
        raise ValueError(f"resistance_options must contain at least {len(BULB_ROLES)} positive integers")
    return values


def _resolve_resistances(instance_seed: int, params: Mapping[str, Any]) -> Dict[str, int]:
    explicit_raw = params.get("resistance_values")
    if explicit_raw is not None:
        if isinstance(explicit_raw, Mapping):
            values = {str(role): int(explicit_raw[str(role)]) for role in BULB_ROLES}
        else:
            if (
                isinstance(explicit_raw, (str, bytes))
                or not isinstance(explicit_raw, Sequence)
                or len(explicit_raw) != len(BULB_ROLES)
            ):
                raise ValueError(f"resistance_values must be a role mapping or a {len(BULB_ROLES)}-value sequence")
            values = {str(role): int(value) for role, value in zip(BULB_ROLES, explicit_raw)}
        if any(value <= 0 for value in values.values()):
            raise ValueError("resistance_values must be positive")
        return dict(values)
    options = list(_resistance_options(params))
    rng = spawn_rng(int(instance_seed), f"{FAMILY_ID}.resistances")
    sampled = rng.sample(options, k=len(BULB_ROLES))
    return {str(role): int(value) for role, value in zip(BULB_ROLES, sampled)}


def _powers_for_state(resistances: Mapping[str, int], *, switch_closed: bool) -> Dict[str, float]:
    r_series = float(resistances["series_bulb"])
    r_main = float(resistances["main_branch_bulb"])
    r_switched = float(resistances["switched_branch_bulb"])
    r_reference_1 = float(resistances["reference_branch_bulb_1"])
    r_reference_2 = float(resistances["reference_branch_bulb_2"])
    reference_current = 1.0 / (r_reference_1 + r_reference_2)
    reference_powers = {
        "reference_branch_bulb_1": float(reference_current * reference_current * r_reference_1),
        "reference_branch_bulb_2": float(reference_current * reference_current * r_reference_2),
    }
    if not bool(switch_closed):
        current = 1.0 / (r_series + r_main)
        return {
            "series_bulb": float(current * current * r_series),
            "main_branch_bulb": float(current * current * r_main),
            "switched_branch_bulb": 0.0,
            **reference_powers,
        }
    parallel = (r_main * r_switched) / (r_main + r_switched)
    total_current = 1.0 / (r_series + parallel)
    branch_voltage = total_current * parallel
    return {
        "series_bulb": float(total_current * total_current * r_series),
        "main_branch_bulb": float(branch_voltage * branch_voltage / r_main),
        "switched_branch_bulb": float(branch_voltage * branch_voltage / r_switched),
        **reference_powers,
    }


def _change_class(before: float, after: float) -> str:
    if float(before) <= EPS and float(after) > EPS:
        return "turns_on"
    if float(before) > EPS and float(after) <= EPS:
        return "turns_off"
    if float(before) > EPS and float(after) > float(before) + EPS:
        return "brightens"
    if float(after) > EPS and float(after) + EPS < float(before):
        return "dims"
    return "unchanged"


def _target_change_class(query_id: str) -> str:
    return {
        "brightens_after_switch_change": "brightens",
        "dims_after_switch_change": "dims",
        "turns_on_after_switch_change": "turns_on",
        "turns_off_after_switch_change": "turns_off",
    }[str(query_id)]


def _make_scenario(instance_seed: int, params: Mapping[str, Any]) -> _Scenario:
    query_id, query_probs = _resolve_query_id(int(instance_seed), params)
    switch_action, switch_probs = _resolve_switch_action(int(instance_seed), params, query_id=str(query_id))
    accent_color_name, accent_probs = _resolve_accent_color(int(instance_seed), params)
    target_label, target_label_probs = _resolve_target_label(int(instance_seed), params)
    resistances = _resolve_resistances(int(instance_seed), params)
    before_closed = str(switch_action) == "opens"
    after_closed = str(switch_action) == "closes"
    powers_before = _powers_for_state(resistances, switch_closed=before_closed)
    powers_after = _powers_for_state(resistances, switch_closed=after_closed)
    role_changes = {
        str(role): _change_class(float(powers_before[str(role)]), float(powers_after[str(role)]))
        for role in BULB_ROLES
    }
    target_change = _target_change_class(str(query_id))
    answer_roles = [role for role, change in role_changes.items() if str(change) == str(target_change)]
    if len(answer_roles) != 1:
        raise RuntimeError(f"state-change circuit must produce one answer, got {answer_roles}")
    answer_role = str(answer_roles[0])

    label_by_role = {str(answer_role): str(target_label)}
    remaining_roles = [role for role in BULB_ROLES if str(role) != str(answer_role)]
    remaining_labels = [label for label in BULB_LABELS if str(label) != str(target_label)]
    rng = spawn_rng(int(instance_seed), f"{FAMILY_ID}.label_assignment")
    rng.shuffle(remaining_roles)
    rng.shuffle(remaining_labels)
    for role, label in zip(remaining_roles, remaining_labels):
        label_by_role[str(role)] = str(label)

    bulbs = tuple(
        _BulbSpec(
            role=str(role),
            label=str(label_by_role[str(role)]),
            resistance_ohm=int(resistances[str(role)]),
            power_before=float(powers_before[str(role)]),
            power_after=float(powers_after[str(role)]),
            change_class=str(role_changes[str(role)]),
        )
        for role in BULB_ROLES
    )
    correct_label = next(str(spec.label) for spec in bulbs if str(spec.change_class) == str(target_change))
    return _Scenario(
        query_id=str(query_id),
        switch_action=str(switch_action),
        accent_color_name=str(accent_color_name),
        target_label=str(target_label),
        bulbs=bulbs,
        correct_label=str(correct_label),
        query_id_probabilities=dict(query_probs),
        switch_action_probabilities=dict(switch_probs),
        accent_color_name_probabilities=dict(accent_probs),
        target_label_probabilities=dict(target_label_probs),
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
    tag = _bbox((cx - text_w * 0.5 - pad_x, cy - text_h * 0.5 - pad_y, cx + text_w * 0.5 + pad_x, cy + text_h * 0.5 + pad_y))
    draw.rounded_rectangle(
        tuple(float(value) for value in tag),
        radius=7,
        fill=tuple(int(value) for value in style.label_fill_rgb),
        outline=tuple(int(value) for value in style.label_border_rgb),
        width=2,
    )
    text_box = draw_centered_text(
        draw,
        text=str(text),
        center=(cx, cy),
        font=font,
        fill=tuple(int(value) for value in style.stroke_rgb),
        stroke_fill=resolve_text_stroke_fill(style.stroke_rgb),
        stroke_width=1,
    )
    return _union_bbox(tag, text_box)


def _draw_bulb(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    spec: _BulbSpec,
    style: Any,
    accent_rgb: Tuple[int, int, int],
    label_font: Any,
    label_offset: Tuple[float, float],
) -> List[float]:
    cx, cy = float(center[0]), float(center[1])
    radius = 34.0
    stroke = tuple(int(value) for value in style.stroke_rgb)
    fill = tuple(int(value) for value in style.panel_alt_fill_rgb)
    glass = (min(255, int(fill[0]) + 12), min(255, int(fill[1]) + 10), min(255, int(fill[2]) + 4))
    bulb_bbox = _bbox((cx - radius, cy - radius, cx + radius, cy + radius))
    draw.ellipse(tuple(float(value) for value in bulb_bbox), fill=glass, outline=stroke, width=4)
    base = _bbox((cx - 17.0, cy + 21.0, cx + 17.0, cy + 38.0))
    draw.rounded_rectangle(tuple(float(value) for value in base), radius=4, fill=tuple(int(value) for value in style.muted_fill_rgb), outline=stroke, width=3)
    filament_rgb = tuple(max(0, min(255, int((0.35 * accent_rgb[idx]) + (0.65 * stroke[idx])))) for idx in range(3))
    filament_y = cy - 1.0
    filament_points = [
        (cx - 19.0, filament_y + 7.0),
        (cx - 11.0, filament_y - 7.0),
        (cx - 3.5, filament_y + 7.0),
        (cx + 4.0, filament_y - 7.0),
        (cx + 12.0, filament_y + 7.0),
        (cx + 19.0, filament_y - 7.0),
    ]
    draw.line(filament_points, fill=filament_rgb, width=4, joint="curve")
    draw.line((cx - 15.0, cy + 20.0, cx - 19.0, filament_y + 7.0), fill=stroke, width=3)
    draw.line((cx + 15.0, cy + 20.0, cx + 19.0, filament_y - 7.0), fill=stroke, width=3)
    label_box = _draw_label_tag(
        draw,
        text=f"{spec.label}={int(spec.resistance_ohm)} ohm",
        center=(cx + float(label_offset[0]), cy + float(label_offset[1])),
        font=label_font,
        style=style,
    )
    return _union_bbox(bulb_bbox, base, label_box)


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
    return _union_bbox((x - 42.0, plate_top - 20.0, x + 66.0, plate_bottom + 20.0), plus_box, minus_box)


def _draw_switch(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    closed: bool,
    action_text: str,
    style: Any,
    font: Any,
    wire_width: int,
) -> List[float]:
    cx, cy = float(center[0]), float(center[1])
    stroke = tuple(int(value) for value in style.stroke_rgb)
    red = (204, 48, 48)
    left_contact = (cx - 38.0, cy)
    right_contact = (cx + 38.0, cy)
    draw.line((cx - 82.0, cy, left_contact[0], cy), fill=stroke, width=int(wire_width))
    draw.line((right_contact[0], cy, cx + 82.0, cy), fill=stroke, width=int(wire_width))
    for contact in (left_contact, right_contact):
        draw.ellipse((contact[0] - 5.5, contact[1] - 5.5, contact[0] + 5.5, contact[1] + 5.5), fill=stroke)
    if bool(closed):
        draw.line((left_contact[0], left_contact[1], right_contact[0], right_contact[1]), fill=tuple(int(value) for value in style.secondary_accent_rgb), width=5)
    else:
        draw.line((left_contact[0], left_contact[1], right_contact[0] - 8.0, right_contact[1] - 32.0), fill=tuple(int(value) for value in style.secondary_accent_rgb), width=5)
    switch_box = _bbox((cx - 48.0, cy - 38.0, cx + 48.0, cy + 16.0))
    action_box = _draw_label_tag(draw, text=str(action_text), center=(cx, cy - 68.0), font=font, style=style)
    outline_box = _union_bbox(switch_box, action_box)
    draw.rounded_rectangle(tuple(float(value) for value in outline_box), radius=10, outline=red, width=4)
    return _union_bbox(outline_box, (cx - 82.0, cy - 8.0, cx + 82.0, cy + 8.0))


def _render_scene(
    *,
    image: Image.Image,
    scenario: _Scenario,
    font_family: str,
    style: Any,
    render_defaults: Mapping[str, Any],
) -> Tuple[Image.Image, Dict[str, List[float]], List[Dict[str, Any]], Dict[str, Any]]:
    draw = ImageDraw.Draw(image)
    canvas_width, canvas_height = image.size
    title_font = load_font(int(render_defaults.get("title_font_size_px", 28)), bold=True, font_family=font_family)
    label_font = load_font(int(render_defaults.get("component_label_font_size_px", 20)), bold=True, font_family=font_family)
    battery_font = load_font(24, bold=True, font_family=font_family)
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
        text="Switch action in an ideal bulb circuit",
        center=((panel[0] + panel[2]) * 0.5, panel[1] + 34.0),
        font=title_font,
        fill=text_rgb,
        stroke_fill=resolve_text_stroke_fill(text_rgb),
        stroke_width=1,
    )

    stroke = tuple(int(value) for value in style.stroke_rgb)
    accent_rgb = named_color(str(scenario.accent_color_name))
    y_top = 188.0
    y_return = 628.0
    x_battery = 172.0
    x_series = 386.0
    x_split = 560.0
    x_right = 1064.0
    y_main = 324.0
    y_switched = 456.0
    y_reference = 586.0
    x_main_bulb = 804.0
    x_switch = 654.0
    x_switched_bulb = 884.0
    x_reference_left = 252.0
    x_reference_bulb_1 = 420.0
    x_reference_bulb_2 = 760.0

    _draw_battery(draw, x=x_battery, y_top=y_top, y_bottom=y_return, style=style, font=battery_font, wire_width=wire_width)
    draw.line((x_battery, y_top, x_split, y_top), fill=stroke, width=wire_width)
    draw.line((x_split, y_top, x_split, y_switched), fill=stroke, width=wire_width)
    draw.line((x_split, y_main, x_right, y_main), fill=stroke, width=wire_width)
    draw.line((x_split, y_switched, x_right, y_switched), fill=stroke, width=wire_width)
    draw.line((x_right, y_main, x_right, y_return), fill=stroke, width=wire_width)
    draw.line((x_battery, y_return, x_right, y_return), fill=stroke, width=wire_width)
    draw.line((x_reference_left, y_top, x_reference_left, y_reference), fill=stroke, width=wire_width)
    draw.line((x_reference_left, y_reference, x_right, y_reference), fill=stroke, width=wire_width)

    spec_by_role = {str(spec.role): spec for spec in scenario.bulbs}
    bulb_bboxes = {
        str(spec_by_role["series_bulb"].label): _draw_bulb(
            draw,
            center=(x_series, y_top),
            spec=spec_by_role["series_bulb"],
            style=style,
            accent_rgb=accent_rgb,
            label_font=label_font,
            label_offset=(0.0, -58.0),
        ),
        str(spec_by_role["main_branch_bulb"].label): _draw_bulb(
            draw,
            center=(x_main_bulb, y_main),
            spec=spec_by_role["main_branch_bulb"],
            style=style,
            accent_rgb=accent_rgb,
            label_font=label_font,
            label_offset=(0.0, -62.0),
        ),
        str(spec_by_role["switched_branch_bulb"].label): _draw_bulb(
            draw,
            center=(x_switched_bulb, y_switched),
            spec=spec_by_role["switched_branch_bulb"],
            style=style,
            accent_rgb=accent_rgb,
            label_font=label_font,
            label_offset=(0.0, -62.0),
        ),
        str(spec_by_role["reference_branch_bulb_1"].label): _draw_bulb(
            draw,
            center=(x_reference_bulb_1, y_reference),
            spec=spec_by_role["reference_branch_bulb_1"],
            style=style,
            accent_rgb=accent_rgb,
            label_font=label_font,
            label_offset=(0.0, -58.0),
        ),
        str(spec_by_role["reference_branch_bulb_2"].label): _draw_bulb(
            draw,
            center=(x_reference_bulb_2, y_reference),
            spec=spec_by_role["reference_branch_bulb_2"],
            style=style,
            accent_rgb=accent_rgb,
            label_font=label_font,
            label_offset=(0.0, -58.0),
        ),
    }
    before_switch_closed = str(scenario.switch_action) == "opens"
    action_text = "S opens" if str(scenario.switch_action) == "opens" else "S closes"
    changed_switch_bbox = _draw_switch(
        draw,
        center=(x_switch, y_switched),
        closed=bool(before_switch_closed),
        action_text=str(action_text),
        style=style,
        font=label_font,
        wire_width=wire_width,
    )

    annotation_map = {"changed_switch": _clip_bbox(changed_switch_bbox, width=canvas_width, height=canvas_height)}
    for label, bbox in sorted(bulb_bboxes.items()):
        annotation_map[str(label)] = _clip_bbox(bbox, width=canvas_width, height=canvas_height)

    scene_entities: List[Dict[str, Any]] = [
        {
            "entity_id": "changed_switch",
            "entity_type": "switch",
            "bbox_px": list(annotation_map["changed_switch"]),
            "meta": {
                "switch_action": str(scenario.switch_action),
                "state_before": "closed" if bool(before_switch_closed) else "open",
                "state_after": "open" if bool(before_switch_closed) else "closed",
            },
        }
    ]
    for spec in scenario.bulbs:
        scene_entities.append(
            {
                "entity_id": str(spec.label),
                "entity_type": "bulb",
                "bbox_px": list(annotation_map[str(spec.label)]),
                "meta": {
                    "role": str(spec.role),
                    "resistance_ohm": int(spec.resistance_ohm),
                    "power_before": float(spec.power_before),
                    "power_after": float(spec.power_after),
                    "change_class": str(spec.change_class),
                },
            }
        )

    render_map = {
        "panel_bbox": _bbox(panel),
        "bulb_bboxes": {str(label): list(bbox) for label, bbox in sorted(bulb_bboxes.items())},
        "changed_switch_bbox": list(annotation_map["changed_switch"]),
        "correct_label": str(scenario.correct_label),
        "switch_action": str(scenario.switch_action),
        "state_before": "closed" if bool(before_switch_closed) else "open",
        "state_after": "open" if bool(before_switch_closed) else "closed",
        "bulb_specs": [
            {
                "role": str(spec.role),
                "label": str(spec.label),
                "resistance_ohm": int(spec.resistance_ohm),
                "power_before": round(float(spec.power_before), 8),
                "power_after": round(float(spec.power_after), 8),
                "change_class": str(spec.change_class),
            }
            for spec in scenario.bulbs
        ],
    }
    return image, dict(annotation_map), [dict(entity) for entity in scene_entities], dict(render_map)


def _build_prompt_examples() -> Tuple[str, str]:
    annotation_example = {
        "changed_switch": [40, 40, 120, 95],
        "B1": [130, 40, 210, 120],
        "B2": [220, 40, 300, 120],
        "B3": [310, 40, 390, 120],
        "B4": [400, 40, 480, 120],
        "B5": [490, 40, 570, 120],
    }
    return (
        json.dumps({"annotation": annotation_example, "answer": "B2"}, ensure_ascii=False, separators=(",", ":")),
        json.dumps({"answer": "B2"}, ensure_ascii=False, separators=(",", ":")),
    )


def _build_complexity(scenario: _Scenario) -> TaskComplexity:
    weights = resolve_physics_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=FAMILY_ID)
    return build_physics_complexity(
        weights=weights,
        components={
            "visual_scan": 0.42,
            "state_change_reasoning": 0.46,
            "ambiguity": 0.12,
            "output_burden": 0.10,
        },
    )


@register_task
class PhysicsCircuitStateChangeBulbBrightnessLabelTask:
    """Select the bulb whose brightness changes in the requested way after a switch action."""

    task_id = TASK_ID
    domain = "physics"
    task_group = "circuits"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        _ = int(max_attempts)
        params = dict(params or {})
        canvas_width = int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", 1280)))
        canvas_height = int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", 720)))
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
        rendered, annotation_map, scene_entities, render_map = _render_scene(
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
                "annotation_hint_state_change_brightness",
                f"answer_hint_{scenario.query_id}",
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
                "answer_hint": str(prompt_defaults[f"answer_hint_{scenario.query_id}"]),
                "annotation_hint": str(prompt_defaults["annotation_hint_state_change_brightness"]),
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
        trace_payload = {
            "scene_ir": {
                "scene_kind": "physics_circuit_state_change_switch_branch",
                "entities": [dict(entity) for entity in scene_entities],
                "relations": {
                    "query_id": str(scenario.query_id),
                    "switch_action": str(scenario.switch_action),
                    "correct_label": str(scenario.correct_label),
                    "target_change_class": str(_target_change_class(scenario.query_id)),
                },
            },
            "query_spec": {
                "query_id": str(scenario.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(scenario.query_id),
                    "switch_action": str(scenario.switch_action),
                    "accent_color_name": str(scenario.accent_color_name),
                    "target_label": str(scenario.target_label),
                    "target_answer": str(scenario.correct_label),
                    "target_change_class": str(_target_change_class(scenario.query_id)),
                    "query_id_probabilities": dict(scenario.query_id_probabilities),
                    "switch_action_probabilities": dict(scenario.switch_action_probabilities),
                    "target_label_probabilities": dict(scenario.target_label_probabilities),
                    "accent_color_name_probabilities": dict(scenario.accent_color_name_probabilities),
                },
            },
            "render_spec": {
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "accent_color_name": str(scenario.accent_color_name),
                "font": {
                    "font_family": str(font_family),
                    "font_asset_version": font_asset_version(),
                    "font_asset": font_record.to_trace(),
                    "scope": "circuit_state_change_diagram",
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
                "query_id": str(scenario.query_id),
                "switch_action": str(scenario.switch_action),
                "accent_color_name": str(scenario.accent_color_name),
                "target_label": str(scenario.target_label),
                "target_answer": str(scenario.correct_label),
                "target_change_class": str(_target_change_class(scenario.query_id)),
                "bulb_specs": [
                    {
                        "role": str(spec.role),
                        "label": str(spec.label),
                        "resistance_ohm": int(spec.resistance_ohm),
                        "power_before": float(spec.power_before),
                        "power_after": float(spec.power_after),
                        "change_class": str(spec.change_class),
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
            complexity=_build_complexity(scenario),
            task_versions=default_task_versions(),
            query_id=str(scenario.query_id),
            scene_id=SCENE_ID,
        )


__all__ = ["PhysicsCircuitStateChangeBulbBrightnessLabelTask"]
