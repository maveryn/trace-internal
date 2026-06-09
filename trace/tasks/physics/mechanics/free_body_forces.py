"""Physics mechanics task for choosing a net-force direction from force arrows."""

from __future__ import annotations

import json
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
from ...shared.bbox_projection import bbox_union_many
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.drawing import draw_arrow, draw_centered_text
from ...shared.font_assets import font_asset_version, get_font_family_record, sample_font_family
from ...shared.named_colors import named_color
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.complexity import build_physics_complexity, clamp_unit_interval, normalize_linear, resolve_physics_complexity_weights
from ..shared.diagram_style import prepare_physics_diagram_style_and_background
from ..shared.label_tags import draw_text_tag
from ..shared.style import SUPPORTED_PHYSICS_COLOR_NAMES
from ..shared.visual_defaults import load_physics_noise_defaults


TASK_ID = "task_physics__free_body_forces__net_force_direction_choice"
FAMILY_ID = "physics_mechanics_free_body_forces_family"
SCENE_ID = "free_body_forces"
QUERY_ID = "net_force_direction_choice"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (QUERY_ID,)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("clean_table", "gridded_table", "lab_card")
OPTION_LETTERS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F", "G", "H")
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
DIRECTION_VECTORS: Dict[str, Tuple[int, int]] = {
    "east": (1, 0),
    "northeast": (1, 1),
    "north": (0, 1),
    "northwest": (-1, 1),
    "west": (-1, 0),
    "southwest": (-1, -1),
    "south": (0, -1),
    "southeast": (1, -1),
}
CARDINAL_VECTORS: Dict[str, Tuple[int, int]] = {
    "east": (1, 0),
    "west": (-1, 0),
    "north": (0, 1),
    "south": (0, -1),
}
VECTOR_TO_DIRECTION = {value: key for key, value in DIRECTION_VECTORS.items()}
FORCE_SLOT_ORDER: Tuple[str, ...] = ("east", "north", "west", "south", "northeast", "northwest", "southwest", "southeast")

_TASK_GROUP_DEFAULTS = get_task_group_defaults("physics", "mechanics")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=FAMILY_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(task_group="mechanics", apply_prob=0.5)


@dataclass(frozen=True)
class _ForceSpec:
    force_id: str
    direction: str
    magnitude_n: int
    vector: Tuple[int, int]


@dataclass(frozen=True)
class _Axes:
    scene_variant: str
    query_id: str
    net_force_direction: str
    correct_option_letter: str
    accent_color_name: str
    scene_variant_probabilities: Dict[str, float]
    query_id_probabilities: Dict[str, float]
    net_force_direction_probabilities: Dict[str, float]
    correct_option_letter_probabilities: Dict[str, float]
    accent_color_name_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _Scenario:
    scene_variant: str
    query_id: str
    net_force_direction: str
    correct_option_letter: str
    option_directions: Dict[str, str]
    force_specs: Tuple[_ForceSpec, ...]
    resultant_vector: Tuple[int, int]


@dataclass(frozen=True)
class _RenderedScene:
    image: Image.Image
    annotation_bboxes: List[List[float]]
    scene_entities: List[Dict[str, Any]]
    render_map: Dict[str, Any]


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


def _unit_from_direction(direction: str) -> Tuple[float, float]:
    x, y_up = DIRECTION_VECTORS[str(direction)]
    length = math.hypot(float(x), float(y_up))
    return (float(x) / float(length), -float(y_up) / float(length))


def _vector_direction(vector: Tuple[int, int]) -> str:
    x, y = int(vector[0]), int(vector[1])
    sx = 0 if x == 0 else (1 if x > 0 else -1)
    sy = 0 if y == 0 else (1 if y > 0 else -1)
    if (sx, sy) == (0, 0):
        raise ValueError("zero resultant force has no direction")
    if sx != 0 and sy != 0 and abs(int(x)) != abs(int(y)):
        raise ValueError(f"diagonal resultant must use equal components, got {(x, y)}")
    return str(VECTOR_TO_DIRECTION[(sx, sy)])


def _resolve_axis(
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


def _resolve_axes(instance_seed: int, params: Mapping[str, Any]) -> _Axes:
    scene_variant, scene_probs = _resolve_axis(
        instance_seed=int(instance_seed),
        params=params,
        supported=SUPPORTED_SCENE_VARIANTS,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        namespace=f"{FAMILY_ID}.scene_variant",
    )
    query_id, query_probs = _resolve_axis(
        instance_seed=int(instance_seed),
        params=params,
        supported=SUPPORTED_QUERY_IDS,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        namespace=f"{FAMILY_ID}.query_id",
    )
    net_direction, net_probs = _resolve_axis(
        instance_seed=int(instance_seed),
        params=params,
        supported=DIRECTION_NAMES,
        explicit_key="net_force_direction",
        weights_key="net_force_direction_weights",
        balance_flag_key="balanced_net_force_direction_sampling",
        namespace=f"{FAMILY_ID}.net_force_direction",
    )
    correct_letter, letter_probs = _resolve_axis(
        instance_seed=int(instance_seed),
        params=params,
        supported=OPTION_LETTERS,
        explicit_key="correct_option_letter",
        weights_key="correct_option_letter_weights",
        balance_flag_key="balanced_correct_option_letter_sampling",
        namespace=f"{FAMILY_ID}.correct_option_letter",
    )
    accent_color, accent_probs = _resolve_axis(
        instance_seed=int(instance_seed),
        params=params,
        supported=SUPPORTED_PHYSICS_COLOR_NAMES,
        explicit_key="accent_color_name",
        weights_key="accent_color_name_weights",
        balance_flag_key="balanced_accent_color_name_sampling",
        namespace=f"{FAMILY_ID}.accent_color_name",
    )
    return _Axes(
        scene_variant=str(scene_variant),
        query_id=str(query_id),
        net_force_direction=str(net_direction),
        correct_option_letter=str(correct_letter),
        accent_color_name=str(accent_color),
        scene_variant_probabilities=dict(scene_probs),
        query_id_probabilities=dict(query_probs),
        net_force_direction_probabilities=dict(net_probs),
        correct_option_letter_probabilities=dict(letter_probs),
        accent_color_name_probabilities=dict(accent_probs),
    )


def _option_directions(*, instance_seed: int, net_force_direction: str, correct_option_letter: str) -> Dict[str, str]:
    remaining_directions = [direction for direction in DIRECTION_NAMES if str(direction) != str(net_force_direction)]
    rng = spawn_rng(int(instance_seed), f"{FAMILY_ID}.option_directions")
    rng.shuffle(remaining_directions)
    mapping: Dict[str, str] = {}
    cursor = 0
    for letter in OPTION_LETTERS:
        if str(letter) == str(correct_option_letter):
            mapping[str(letter)] = str(net_force_direction)
        else:
            mapping[str(letter)] = str(remaining_directions[cursor])
            cursor += 1
    return dict(mapping)


def _make_force_specs(instance_seed: int, params: Mapping[str, Any], *, net_force_direction: str) -> Tuple[_ForceSpec, ...]:
    explicit = params.get("force_specs")
    if explicit is not None:
        if isinstance(explicit, (str, bytes)) or not isinstance(explicit, Sequence):
            raise ValueError("force_specs must be a sequence of mappings")
        specs: List[_ForceSpec] = []
        for index, raw_spec in enumerate(explicit):
            if not isinstance(raw_spec, Mapping):
                raise ValueError("each force spec must be a mapping")
            direction = str(raw_spec["direction"])
            magnitude = int(raw_spec["magnitude_n"])
            if direction not in CARDINAL_VECTORS:
                raise ValueError("v0 force_specs support cardinal directions only")
            if magnitude <= 0:
                raise ValueError("force magnitudes must be positive")
            unit = CARDINAL_VECTORS[direction]
            specs.append(
                _ForceSpec(
                    force_id=f"F{index + 1}",
                    direction=str(direction),
                    magnitude_n=int(magnitude),
                    vector=(int(unit[0]) * int(magnitude), int(unit[1]) * int(magnitude)),
                )
            )
        resultant = (sum(spec.vector[0] for spec in specs), sum(spec.vector[1] for spec in specs))
        if _vector_direction(resultant) != str(net_force_direction):
            raise ValueError("explicit force_specs do not match net_force_direction")
        return tuple(specs)

    rng = spawn_rng(int(instance_seed), f"{FAMILY_ID}.force_specs")
    dx_sign, dy_sign = DIRECTION_VECTORS[str(net_force_direction)]
    residual_options = tuple(int(value) for value in group_default(_GEN_DEFAULTS, "resultant_component_support", (2, 3, 4, 5, 6)))
    base_options = tuple(int(value) for value in group_default(_GEN_DEFAULTS, "base_force_support", (2, 3, 4, 5, 6, 7, 8)))
    pair_options = tuple(int(value) for value in group_default(_GEN_DEFAULTS, "canceling_pair_support", (1, 2, 3, 4)))
    residual = int(rng.choice(residual_options))
    if int(dx_sign) == 0:
        east = west = int(rng.choice(base_options))
    elif int(dx_sign) > 0:
        west = int(rng.choice(base_options))
        east = int(west + residual)
    else:
        east = int(rng.choice(base_options))
        west = int(east + residual)
    if int(dy_sign) == 0:
        north = south = int(rng.choice(base_options))
    elif int(dy_sign) > 0:
        south = int(rng.choice(base_options))
        north = int(south + residual)
    else:
        north = int(rng.choice(base_options))
        south = int(north + residual)

    magnitudes = {"east": int(east), "north": int(north), "west": int(west), "south": int(south)}
    specs = [
        _ForceSpec(
            force_id=f"F{index + 1}",
            direction=str(direction),
            magnitude_n=int(magnitudes[str(direction)]),
            vector=(
                int(CARDINAL_VECTORS[str(direction)][0]) * int(magnitudes[str(direction)]),
                int(CARDINAL_VECTORS[str(direction)][1]) * int(magnitudes[str(direction)]),
            ),
        )
        for index, direction in enumerate(("east", "north", "west", "south"))
    ]
    if bool(params.get("include_extra_canceling_pair", rng.random() < 0.65)):
        pair_direction = str(rng.choice(("east_west", "north_south")))
        magnitude = int(rng.choice(pair_options))
        for direction in (("east", "west") if pair_direction == "east_west" else ("north", "south")):
            specs.append(
                _ForceSpec(
                    force_id=f"F{len(specs) + 1}",
                    direction=str(direction),
                    magnitude_n=int(magnitude),
                    vector=(
                        int(CARDINAL_VECTORS[str(direction)][0]) * int(magnitude),
                        int(CARDINAL_VECTORS[str(direction)][1]) * int(magnitude),
                    ),
                )
            )
    rng.shuffle(specs)
    relabeled = tuple(
        _ForceSpec(
            force_id=f"F{index + 1}",
            direction=str(spec.direction),
            magnitude_n=int(spec.magnitude_n),
            vector=tuple(spec.vector),
        )
        for index, spec in enumerate(specs)
    )
    resultant = (sum(spec.vector[0] for spec in relabeled), sum(spec.vector[1] for spec in relabeled))
    if _vector_direction(resultant) != str(net_force_direction):
        raise RuntimeError("constructed force specs do not match requested net direction")
    return tuple(relabeled)


def _make_scenario(instance_seed: int, axes: _Axes, params: Mapping[str, Any]) -> _Scenario:
    forces = _make_force_specs(int(instance_seed), params, net_force_direction=str(axes.net_force_direction))
    resultant = (sum(spec.vector[0] for spec in forces), sum(spec.vector[1] for spec in forces))
    return _Scenario(
        scene_variant=str(axes.scene_variant),
        query_id=str(axes.query_id),
        net_force_direction=str(_vector_direction(resultant)),
        correct_option_letter=str(axes.correct_option_letter),
        option_directions=_option_directions(
            instance_seed=int(instance_seed),
            net_force_direction=str(_vector_direction(resultant)),
            correct_option_letter=str(axes.correct_option_letter),
        ),
        force_specs=tuple(forces),
        resultant_vector=tuple(resultant),
    )


def _draw_grid(draw: ImageDraw.ImageDraw, *, bbox: Sequence[float], spacing_px: int, fill_rgb: Tuple[int, int, int]) -> None:
    left, top, right, bottom = [float(value) for value in bbox]
    spacing = max(24.0, float(spacing_px))
    x = left + spacing
    while x < right:
        draw.line((x, top, x, bottom), fill=fill_rgb, width=1)
        x += spacing
    y = top + spacing
    while y < bottom:
        draw.line((left, y, right, y), fill=fill_rgb, width=1)
        y += spacing


def _draw_force_arrow(
    draw: ImageDraw.ImageDraw,
    *,
    force: _ForceSpec,
    object_center: Tuple[float, float],
    object_radius: float,
    arrow_length_px: float,
    font: Any,
    style: Any,
    force_rgb: Tuple[int, int, int],
    lateral_offset_px: float,
    stroke_width_px: int,
    head_length_px: float,
    head_width_px: float,
) -> Tuple[List[float], List[float], Dict[str, Any]]:
    unit_x, unit_y = _unit_from_direction(force.direction)
    perp_x, perp_y = -unit_y, unit_x
    start = (
        float(object_center[0] + unit_x * (float(object_radius) + 9.0) + perp_x * float(lateral_offset_px)),
        float(object_center[1] + unit_y * (float(object_radius) + 9.0) + perp_y * float(lateral_offset_px)),
    )
    end = (
        float(start[0] + unit_x * float(arrow_length_px)),
        float(start[1] + unit_y * float(arrow_length_px)),
    )
    draw_arrow(
        draw,
        start=start,
        end=end,
        fill=force_rgb,
        width=max(1, int(stroke_width_px)),
        head_length_px=float(head_length_px),
        head_width_px=float(head_width_px),
    )
    arrow_bbox = _bbox(
        (
            min(start[0], end[0]) - 18.0,
            min(start[1], end[1]) - 18.0,
            max(start[0], end[0]) + 18.0,
            max(start[1], end[1]) + 18.0,
        )
    )
    label_center = (
        float(end[0] + unit_x * 28.0 + perp_x * float(lateral_offset_px) * 3.0),
        float(end[1] + unit_y * 28.0 + perp_y * float(lateral_offset_px) * 3.0),
    )
    label_bbox = draw_text_tag(
        draw,
        text=f"{force.force_id}={force.magnitude_n} N",
        center=label_center,
        font=font,
        fill_rgb=tuple(int(value) for value in style.label_fill_rgb),
        outline_rgb=tuple(int(value) for value in style.label_border_rgb),
        text_rgb=tuple(int(value) for value in style.stroke_rgb),
        stroke_width_px=1,
    )
    annotation_bbox = bbox_union_many(arrow_bbox, label_bbox)
    return annotation_bbox, label_bbox, {"start": [round(start[0], 3), round(start[1], 3)], "end": [round(end[0], 3), round(end[1], 3)]}


def _render_scene(
    *,
    image: Image.Image,
    scenario: _Scenario,
    axes: _Axes,
    font_family: str,
    style: Any,
    render_defaults: Mapping[str, Any],
) -> _RenderedScene:
    draw = ImageDraw.Draw(image)
    width, height = image.size
    title_font = load_font(int(render_defaults.get("title_font_size_px", 27)), bold=True, font_family=font_family)
    label_font = load_font(int(render_defaults.get("label_font_size_px", 22)), bold=True, font_family=font_family)
    option_font = load_font(int(render_defaults.get("option_font_size_px", 22)), bold=True, font_family=font_family)
    stroke_rgb = tuple(int(value) for value in style.stroke_rgb)
    guide_rgb = tuple(int(value) for value in style.guide_rgb)
    accent_rgb = named_color(str(axes.accent_color_name))
    force_rgb = tuple(max(0, min(255, int(0.72 * accent_rgb[index] + 0.28 * stroke_rgb[index]))) for index in range(3))
    panel = (
        float(render_defaults.get("panel_left_px", 52)),
        float(render_defaults.get("panel_top_px", 52)),
        float(render_defaults.get("panel_right_px", width - 52)),
        float(render_defaults.get("panel_bottom_px", height - 52)),
    )
    draw.rounded_rectangle(
        panel,
        radius=int(render_defaults.get("panel_corner_radius_px", 22)),
        fill=tuple(int(value) for value in style.panel_fill_rgb),
        outline=tuple(int(value) for value in style.panel_border_rgb),
        width=3,
    )
    if str(scenario.scene_variant) in {"gridded_table", "lab_card"}:
        _draw_grid(
            draw,
            bbox=panel,
            spacing_px=int(render_defaults.get("grid_spacing_px", 44)),
            fill_rgb=tuple(int(value) for value in style.guide_rgb),
        )
    title_text = "Applied forces on one object"
    title_center = ((panel[0] + panel[2]) * 0.5, panel[1] + 34.0)
    title_bbox = draw.textbbox((0, 0), title_text, font=title_font, stroke_width=1)
    title_width = float(title_bbox[2] - title_bbox[0])
    title_height = float(title_bbox[3] - title_bbox[1])
    title_backdrop = (
        title_center[0] - title_width * 0.5 - 14.0,
        title_center[1] - title_height * 0.5 - 8.0,
        title_center[0] + title_width * 0.5 + 14.0,
        title_center[1] + title_height * 0.5 + 8.0,
    )
    draw.rounded_rectangle(
        title_backdrop,
        radius=9,
        fill=tuple(int(value) for value in style.panel_fill_rgb),
    )
    draw_centered_text(
        draw,
        text=title_text,
        center=title_center,
        font=title_font,
        fill=stroke_rgb,
        stroke_fill=resolve_text_stroke_fill(stroke_rgb),
        stroke_width=1,
    )

    object_center = (
        float(render_defaults.get("object_center_x_px", 590)),
        float(render_defaults.get("object_center_y_px", 340)),
    )
    object_width = float(render_defaults.get("object_width_px", 148))
    object_height = float(render_defaults.get("object_height_px", 104))
    object_bbox = _bbox(
        (
            object_center[0] - object_width * 0.5,
            object_center[1] - object_height * 0.5,
            object_center[0] + object_width * 0.5,
            object_center[1] + object_height * 0.5,
        )
    )
    draw.rounded_rectangle(
        tuple(object_bbox),
        radius=18,
        fill=tuple(int(value) for value in style.panel_alt_fill_rgb),
        outline=stroke_rgb,
        width=4,
    )
    draw_centered_text(
        draw,
        text="object",
        center=object_center,
        font=label_font,
        fill=stroke_rgb,
        stroke_fill=resolve_text_stroke_fill(stroke_rgb),
        stroke_width=1,
    )

    annotation_bboxes: List[List[float]] = []
    force_entities: List[Dict[str, Any]] = []
    force_arrow_map: Dict[str, Any] = {}
    direction_counts = {direction: sum(1 for spec in scenario.force_specs if spec.direction == direction) for direction in CARDINAL_VECTORS}
    direction_seen = {direction: 0 for direction in CARDINAL_VECTORS}
    for force in scenario.force_specs:
        count_for_direction = max(1, int(direction_counts.get(str(force.direction), 1)))
        seen_for_direction = int(direction_seen.get(str(force.direction), 0))
        direction_seen[str(force.direction)] = seen_for_direction + 1
        lateral_offset = (float(seen_for_direction) - (float(count_for_direction) - 1.0) * 0.5) * 28.0
        annotation_bbox, label_bbox, arrow_points = _draw_force_arrow(
            draw,
            force=force,
            object_center=object_center,
            object_radius=max(object_width, object_height) * 0.5,
            arrow_length_px=float(render_defaults.get("force_arrow_length_px", 112)),
            font=label_font,
            style=style,
            force_rgb=force_rgb,
            lateral_offset_px=float(lateral_offset),
            stroke_width_px=int(render_defaults.get("force_arrow_width_px", 8)),
            head_length_px=float(render_defaults.get("force_arrow_head_length_px", 24)),
            head_width_px=float(render_defaults.get("force_arrow_head_width_px", 20)),
        )
        clipped_annotation = _clip_bbox(annotation_bbox, width=width, height=height)
        clipped_label = _clip_bbox(label_bbox, width=width, height=height)
        annotation_bboxes.append(clipped_annotation)
        force_arrow_map[str(force.force_id)] = {
            "direction": str(force.direction),
            "magnitude_n": int(force.magnitude_n),
            "vector": [int(force.vector[0]), int(force.vector[1])],
            "bbox_px": list(clipped_annotation),
            "label_bbox_px": list(clipped_label),
            **arrow_points,
        }
        force_entities.append(
            {
                "entity_id": str(force.force_id),
                "entity_type": "applied_force",
                "bbox_px": list(clipped_annotation),
                "meta": {
                    "direction": str(force.direction),
                    "magnitude_n": int(force.magnitude_n),
                    "vector": [int(force.vector[0]), int(force.vector[1])],
                },
            }
        )

    option_panel_top = float(render_defaults.get("option_panel_top_px", 594))
    option_cell_left = float(render_defaults.get("option_cell_left_px", 58))
    option_cell_width = float(render_defaults.get("option_cell_width_px", 132))
    option_cell_height = float(render_defaults.get("option_cell_height_px", 92))
    option_arrow_length = float(render_defaults.get("option_arrow_length_px", 54))
    option_arrow_rgb = tuple(int(value) for value in style.secondary_accent_rgb)
    option_bboxes: Dict[str, List[float]] = {}
    for index, letter in enumerate(OPTION_LETTERS):
        left = option_cell_left + index * option_cell_width
        cell = _bbox((left, option_panel_top, left + option_cell_width - 12.0, option_panel_top + option_cell_height))
        draw.rounded_rectangle(tuple(cell), radius=12, fill=tuple(int(value) for value in style.panel_alt_fill_rgb), outline=guide_rgb, width=2)
        draw_centered_text(
            draw,
            text=str(letter),
            center=(cell[0] + 22.0, cell[1] + 22.0),
            font=option_font,
            fill=stroke_rgb,
            stroke_fill=resolve_text_stroke_fill(stroke_rgb),
            stroke_width=1,
        )
        direction = str(scenario.option_directions[str(letter)])
        unit_x, unit_y = _unit_from_direction(direction)
        center = ((cell[0] + cell[2]) * 0.5 + 10.0, (cell[1] + cell[3]) * 0.5 + 10.0)
        start = (center[0] - unit_x * option_arrow_length * 0.5, center[1] - unit_y * option_arrow_length * 0.5)
        end = (center[0] + unit_x * option_arrow_length * 0.5, center[1] + unit_y * option_arrow_length * 0.5)
        draw_arrow(
            draw,
            start=start,
            end=end,
            fill=option_arrow_rgb,
            width=int(render_defaults.get("option_arrow_width_px", 6)),
            head_length_px=float(render_defaults.get("option_arrow_head_length_px", 18)),
            head_width_px=float(render_defaults.get("option_arrow_head_width_px", 16)),
        )
        option_bboxes[str(letter)] = list(cell)

    scene_entities = [
        {
            "entity_id": "object",
            "entity_type": "body",
            "bbox_px": _clip_bbox(object_bbox, width=width, height=height),
            "meta": {"role": "object_with_applied_forces"},
        },
        *force_entities,
    ]
    render_map = {
        "panel_bbox_px": _bbox(panel),
        "object_bbox_px": _clip_bbox(object_bbox, width=width, height=height),
        "force_arrows": dict(force_arrow_map),
        "annotation_bbox_set": [list(bbox) for bbox in annotation_bboxes],
        "option_bboxes_px": {str(letter): list(bbox) for letter, bbox in sorted(option_bboxes.items())},
        "option_directions": dict(scenario.option_directions),
        "correct_option_letter": str(scenario.correct_option_letter),
        "net_force_direction": str(scenario.net_force_direction),
        "resultant_vector": [int(scenario.resultant_vector[0]), int(scenario.resultant_vector[1])],
    }
    return _RenderedScene(
        image=image,
        annotation_bboxes=[list(bbox) for bbox in annotation_bboxes],
        scene_entities=[dict(entity) for entity in scene_entities],
        render_map=dict(render_map),
    )


def _build_complexity(scenario: _Scenario) -> TaskComplexity:
    weights = resolve_physics_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=FAMILY_ID)
    force_count = len(scenario.force_specs)
    visual_scan = clamp_unit_interval(0.28 + 0.12 * normalize_linear(float(force_count), min_value=4.0, max_value=6.0))
    vector_reasoning = clamp_unit_interval(0.42 + (0.12 if scenario.net_force_direction in {"northeast", "northwest", "southwest", "southeast"} else 0.0))
    ambiguity = clamp_unit_interval(0.16 + 0.03 * normalize_linear(float(force_count), min_value=4.0, max_value=6.0))
    output_burden = 0.18
    return build_physics_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "vector_reasoning": float(vector_reasoning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


def _prompt_examples() -> Tuple[str, str]:
    return (
        json.dumps({"annotation": [[100, 110, 220, 150], [260, 210, 310, 340]], "answer": "C"}, ensure_ascii=False, separators=(",", ":")),
        json.dumps({"answer": "C"}, ensure_ascii=False, separators=(",", ":")),
    )


@register_task
class PhysicsFreeBodyForcesNetForceDirectionChoiceTask:
    """Choose the candidate arrow showing the resultant of visible applied forces."""

    task_id = TASK_ID
    domain = "physics"
    task_group = "mechanics"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        params = dict(params or {})
        axes = _resolve_axes(int(instance_seed), params)
        scenario = _make_scenario(int(instance_seed), axes, params)
        canvas_width = int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", 1180)))
        canvas_height = int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", 760)))
        background, background_meta, diagram_style, diagram_style_meta = prepare_physics_diagram_style_and_background(
            scene_id=SCENE_ID,
            task_group=self.task_group,
            canvas_width=int(canvas_width),
            canvas_height=int(canvas_height),
            instance_seed=int(instance_seed),
            params=params,
        )
        font_family = sample_font_family(
            role="readout",
            instance_seed=int(instance_seed),
            namespace=f"{FAMILY_ID}.font",
            params=params,
        )
        font_record = get_font_family_record(str(font_family))
        rendered = _render_scene(
            image=background,
            scenario=scenario,
            axes=axes,
            font_family=str(font_family),
            style=diagram_style,
            render_defaults=_RENDER_DEFAULTS,
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
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
                f"object_description_{scenario.scene_variant}",
                f"answer_hint_{QUERY_ID}",
                f"annotation_hint_{QUERY_ID}",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _prompt_examples()
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=QUERY_ID,
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults[f"object_description_{scenario.scene_variant}"]),
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
        answer_gt = TypedValue(type="option_letter", value=str(scenario.correct_option_letter))
        annotation_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in rendered.annotation_bboxes])
        projected_annotation = {
            "type": "bbox_set",
            "bbox_set": [list(bbox) for bbox in rendered.annotation_bboxes],
            "pixel_bbox_set": [list(bbox) for bbox in rendered.annotation_bboxes],
        }
        force_payload = [
            {
                "force_id": str(spec.force_id),
                "direction": str(spec.direction),
                "magnitude_n": int(spec.magnitude_n),
                "vector": [int(spec.vector[0]), int(spec.vector[1])],
            }
            for spec in scenario.force_specs
        ]
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"physics_free_body_forces_{scenario.scene_variant}",
                "entities": [dict(entity) for entity in rendered.scene_entities],
                "relations": {
                    "scene_variant": str(scenario.scene_variant),
                    "query_id": QUERY_ID,
                    "net_force_direction": str(scenario.net_force_direction),
                    "resultant_vector": [int(scenario.resultant_vector[0]), int(scenario.resultant_vector[1])],
                    "correct_option_letter": str(scenario.correct_option_letter),
                    "option_directions": dict(scenario.option_directions),
                    "annotation_entity_ids": [str(spec.force_id) for spec in scenario.force_specs],
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
                    "net_force_direction": str(scenario.net_force_direction),
                    "correct_option_letter": str(scenario.correct_option_letter),
                    "accent_color_name": str(axes.accent_color_name),
                    "target_answer": str(scenario.correct_option_letter),
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "net_force_direction_probabilities": dict(axes.net_force_direction_probabilities),
                    "correct_option_letter_probabilities": dict(axes.correct_option_letter_probabilities),
                    "accent_color_name_probabilities": dict(axes.accent_color_name_probabilities),
                },
            },
            "render_spec": {
                "scene_variant": str(scenario.scene_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "accent_color_name": str(axes.accent_color_name),
                "font": {
                    "font_family": str(font_family),
                    "font_asset_version": font_asset_version(),
                    "font_asset": font_record.to_trace(),
                    "scope": "free_body_force_diagram",
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
            "render_map": dict(rendered.render_map),
            "execution_trace": {
                "scene_variant": str(scenario.scene_variant),
                "query_id": QUERY_ID,
                "net_force_direction": str(scenario.net_force_direction),
                "resultant_vector": [int(scenario.resultant_vector[0]), int(scenario.resultant_vector[1])],
                "correct_option_letter": str(scenario.correct_option_letter),
                "option_letters": list(OPTION_LETTERS),
                "option_directions": dict(scenario.option_directions),
                "force_specs": list(force_payload),
                "annotation_entity_ids": [str(spec.force_id) for spec in scenario.force_specs],
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(spec.force_id) for spec in scenario.force_specs],
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
            query_id=QUERY_ID,
            scene_id=SCENE_ID,
        )


__all__ = [
    "DIRECTION_NAMES",
    "OPTION_LETTERS",
    "PhysicsFreeBodyForcesNetForceDirectionChoiceTask",
]
