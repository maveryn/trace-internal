"""Physics mechanics task for simple axis-aligned force diagrams."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.drawing import draw_arrow, draw_dashed_line, draw_rounded_rect
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import build_prompt_json_examples
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from ...shared.variant_sampling import resolve_compatible_scene_query_variants
from ..shared.complexity import build_physics_force_diagram_complexity
from ..shared.visual_defaults import load_physics_background_defaults, load_physics_noise_defaults


TASK_ID = "task_physics_mechanics_force_diagram"
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "free_body_box",
    "surface_block",
    "textured_block",
)
SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = (
    "net_horizontal_force",
    "net_vertical_force",
    "balancing_force_horizontal",
    "balancing_force_vertical",
)
COMPATIBILITY: Dict[str, Sequence[str]] = {
    "free_body_box": SUPPORTED_QUERY_VARIANTS,
    "surface_block": SUPPORTED_QUERY_VARIANTS,
    "textured_block": SUPPORTED_QUERY_VARIANTS,
}
_HORIZONTAL_QUERY_VARIANTS = {"net_horizontal_force", "balancing_force_horizontal"}
_VERTICAL_QUERY_VARIANTS = {"net_vertical_force", "balancing_force_vertical"}
_BALANCING_QUERY_VARIANTS = {"balancing_force_horizontal", "balancing_force_vertical"}
_QUERY_DIRECTION_TEXT = {
    "left": "leftward",
    "right": "rightward",
    "up": "upward",
    "down": "downward",
}
_AXIS_BY_DIRECTION = {
    "left": "horizontal",
    "right": "horizontal",
    "up": "vertical",
    "down": "vertical",
}
_OPPOSITE_DIRECTION = {
    "left": "right",
    "right": "left",
    "up": "down",
    "down": "up",
}
_ARROW_FILL = {
    "left": (58, 97, 174),
    "right": (58, 97, 174),
    "up": (206, 124, 39),
    "down": (206, 124, 39),
}
_SCENE_VARIANT_LOAD = {
    "free_body_box": 0.06,
    "surface_block": 0.14,
    "textured_block": 0.10,
}


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for mechanics force-diagram scenes."""

    canvas_width: int = 860
    canvas_height: int = 620
    outer_margin_px: int = 34
    object_base_side_min_px: int = 140
    object_base_side_max_px: int = 176
    object_min_side_px: int = 104
    object_aspect_ratio_support: Tuple[float, ...] = (0.5, 0.67, 0.8, 1.0, 1.0, 1.25, 1.5, 2.0)
    object_outline_width_px: int = 4
    object_corner_radius_px: int = 18
    arrow_length_px: int = 104
    arrow_width_px: int = 8
    arrow_head_length_px: int = 22
    arrow_head_width_px: int = 18
    arrow_gap_px: int = 18
    arrow_slot_gap_px: int = 34
    balancing_arrow_gap_extra_px: int = 54
    balancing_label_gap_extra_px: int = 10
    label_gap_px: int = 28
    label_font_size_px: int = 24
    label_stroke_width_px: int = 3
    label_box_padding_px: int = 6
    surface_line_width_px: int = 5
    texture_line_width_px: int = 3
    texture_spacing_px: int = 18
    target_force_support: Tuple[int, ...] = tuple(range(0, 13))
    balancing_force_support: Tuple[int, ...] = tuple(range(1, 13))
    force_magnitude_min: int = 1
    force_magnitude_max: int = 12
    relevant_arrow_count_min: int = 2
    relevant_arrow_count_max: int = 4
    distractor_arrow_count_min: int = 0
    distractor_arrow_count_max: int = 2


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved scene/query axes and target answer support for one instance."""

    scene_variant: str
    query_variant: str
    target_force: int
    scene_variant_probabilities: Dict[str, float]
    query_variant_probabilities: Dict[str, float]
    target_force_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _ArrowSpec:
    """One rendered force arrow with trace metadata."""

    arrow_id: str
    direction: str
    magnitude: int
    bbox_px: List[float]
    label_bbox_px: List[float]
    relevant: bool
    role: str


@dataclass(frozen=True)
class _RenderedScene:
    """Rendered mechanics scene with evidence and trace artifacts."""

    image: Image.Image
    arrow_specs: List[_ArrowSpec]
    placeholder_direction: str | None
    placeholder_bbox_px: List[float] | None
    object_bbox_px: List[float]
    object_width_px: int
    object_height_px: int
    surface_bbox_px: List[float] | None
    evidence_bboxes: List[List[float]]
    evidence_arrow_ids: List[str]
    render_map: Dict[str, Any]
    scene_entities: List[Dict[str, Any]]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("physics", "mechanics")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_physics_background_defaults(task_group="mechanics")
POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(task_group="mechanics", apply_prob=0.0)


def _query_axis(query_variant: str) -> str:
    """Return the queried axis for one query variant."""

    if str(query_variant) in _HORIZONTAL_QUERY_VARIANTS:
        return "horizontal"
    if str(query_variant) in _VERTICAL_QUERY_VARIANTS:
        return "vertical"
    raise ValueError(f"unsupported query_variant: {query_variant}")


def _is_balancing_query(query_variant: str) -> bool:
    """Return true when the query asks for a missing balancing force."""

    return str(query_variant) in _BALANCING_QUERY_VARIANTS


def _resolve_support(
    params: Mapping[str, Any],
    *,
    key: str,
    fallback: Sequence[int],
) -> Tuple[int, ...]:
    """Resolve one explicit integer support list."""

    raw_support = params.get(str(key), group_default(_GEN_DEFAULTS, str(key), tuple(int(value) for value in fallback)))
    support: List[int] = []
    for raw_value in raw_support:
        value = int(raw_value)
        if value not in support:
            support.append(int(value))
    if not support:
        raise ValueError(f"{key} must contain at least one integer")
    return tuple(sorted(support))


def _resolve_target_force(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    query_variant: str,
) -> Tuple[int, Dict[str, float]]:
    """Resolve the sampled target force with deterministic support cycling."""

    support = _resolve_support(
        params,
        key="balancing_force_support" if _is_balancing_query(str(query_variant)) else "target_force_support",
        fallback=_DEFAULTS.balancing_force_support if _is_balancing_query(str(query_variant)) else _DEFAULTS.target_force_support,
    )
    explicit = params.get("target_force")
    if explicit is not None:
        selected = int(explicit)
        if int(selected) not in set(support):
            raise ValueError(f"unsupported target_force: {selected}")
        return int(selected), uniform_probability_map(support, selected=int(selected))

    balanced_enabled = bool(params.get("balanced_target_force_sampling", group_default(_GEN_DEFAULTS, "balanced_target_force_sampling", True)))
    if bool(balanced_enabled):
        selection_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.target_force.{str(query_variant)}",
        )
        selected = int(support[int(selection_index) % len(support)])
    else:
        rng = spawn_rng(int(instance_seed), f"{TASK_ID}.target_force")
        selected = int(support[int(rng.randrange(len(support)))])
    return int(selected), uniform_probability_map(support)


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve one compatible scene/query pair plus target-force support."""

    axis_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.axes")
    scene_variant, scene_probs, query_variant, query_probs = resolve_compatible_scene_query_variants(
        axis_rng,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_scene_variants=SUPPORTED_SCENE_VARIANTS,
        supported_query_variants=SUPPORTED_QUERY_VARIANTS,
        compatibility=COMPATIBILITY,
        scene_sampling_namespace=f"{TASK_ID}.scene_variant",
        query_sampling_namespace=f"{TASK_ID}.query_variant",
    )
    target_force, target_force_probabilities = _resolve_target_force(
        instance_seed=int(instance_seed),
        params=params,
        query_variant=str(query_variant),
    )
    return _ResolvedAxes(
        scene_variant=str(scene_variant),
        query_variant=str(query_variant),
        target_force=int(target_force),
        scene_variant_probabilities=dict(scene_probs),
        query_variant_probabilities=dict(query_probs),
        target_force_probabilities=dict(target_force_probabilities),
    )


def _partition_sum(
    rng,
    *,
    total: int,
    count: int,
    min_value: int,
    max_value: int,
) -> List[int] | None:
    """Partition one integer total into `count` bounded positive parts."""

    if int(count) <= 0:
        return None
    if int(total) < int(count) * int(min_value) or int(total) > int(count) * int(max_value):
        return None
    remaining = int(total)
    parts: List[int] = []
    for index in range(int(count) - 1):
        remaining_slots = int(count - index - 1)
        lower = max(int(min_value), int(remaining - (remaining_slots * int(max_value))))
        upper = min(int(max_value), int(remaining - (remaining_slots * int(min_value))))
        if int(lower) > int(upper):
            return None
        value = int(rng.randint(int(lower), int(upper)))
        parts.append(int(value))
        remaining -= int(value)
    if not (int(min_value) <= int(remaining) <= int(max_value)):
        return None
    parts.append(int(remaining))
    rng.shuffle(parts)
    return parts


def _sample_axis_arrow_magnitudes(
    rng,
    *,
    axis: str,
    target_force: int,
    force_magnitude_min: int,
    force_magnitude_max: int,
) -> Tuple[List[Tuple[str, int]], str]:
    """Sample one multiset of axis-aligned force arrows that realizes `target_force`."""

    positive_direction, negative_direction = ("right", "left") if str(axis) == "horizontal" else ("up", "down")
    dominant_direction = str(positive_direction if rng.random() < 0.5 else negative_direction)
    opposing_direction = str(_OPPOSITE_DIRECTION[dominant_direction])

    for _ in range(80):
        dominant_count = int(rng.randint(_DEFAULTS.relevant_arrow_count_min // 2, 2))
        opposing_count = int(rng.randint(_DEFAULTS.relevant_arrow_count_min // 2, 2))
        if int(dominant_count + opposing_count) < int(_DEFAULTS.relevant_arrow_count_min):
            continue
        if int(dominant_count + opposing_count) > int(_DEFAULTS.relevant_arrow_count_max):
            continue

        if int(target_force) == 0:
            lower = max(int(dominant_count), int(opposing_count)) * int(force_magnitude_min)
            upper = min(int(dominant_count), int(opposing_count)) * int(force_magnitude_max)
            if int(lower) > int(upper):
                continue
            opposing_sum = int(rng.randint(int(lower), int(upper)))
            dominant_sum = int(opposing_sum)
        else:
            lower = max(
                int(opposing_count) * int(force_magnitude_min),
                int(dominant_count) * int(force_magnitude_min) - int(target_force),
            )
            upper = min(
                int(opposing_count) * int(force_magnitude_max),
                int(dominant_count) * int(force_magnitude_max) - int(target_force),
            )
            if int(lower) > int(upper):
                continue
            opposing_sum = int(rng.randint(int(lower), int(upper)))
            dominant_sum = int(opposing_sum + int(target_force))

        dominant_parts = _partition_sum(
            rng,
            total=int(dominant_sum),
            count=int(dominant_count),
            min_value=int(force_magnitude_min),
            max_value=int(force_magnitude_max),
        )
        opposing_parts = _partition_sum(
            rng,
            total=int(opposing_sum),
            count=int(opposing_count),
            min_value=int(force_magnitude_min),
            max_value=int(force_magnitude_max),
        )
        if dominant_parts is None or opposing_parts is None:
            continue
        arrows = [(str(dominant_direction), int(value)) for value in dominant_parts] + [
            (str(opposing_direction), int(value)) for value in opposing_parts
        ]
        rng.shuffle(arrows)
        return arrows, str(dominant_direction)
    raise ValueError(f"unable to sample axis arrows for {axis=} and {target_force=}")


def _sample_distractor_arrows(
    rng,
    *,
    scene_variant: str,
    axis: str,
    force_magnitude_min: int,
    force_magnitude_max: int,
) -> List[Tuple[str, int]]:
    """Sample non-query-axis distractor arrows for scene richness."""

    other_directions = ("up", "down") if str(axis) == "horizontal" else ("left", "right")
    if str(scene_variant) == "surface_block":
        return [
            (str(other_directions[0]), int(rng.randint(int(force_magnitude_min), int(force_magnitude_max)))),
            (str(other_directions[1]), int(rng.randint(int(force_magnitude_min), int(force_magnitude_max)))),
        ]

    distractor_count = int(rng.randint(_DEFAULTS.distractor_arrow_count_min, _DEFAULTS.distractor_arrow_count_max))
    arrows: List[Tuple[str, int]] = []
    for _ in range(int(distractor_count)):
        direction = str(other_directions[int(rng.randrange(len(other_directions)))])
        arrows.append(
            (direction, int(rng.randint(int(force_magnitude_min), int(force_magnitude_max))))
        )
    return arrows


def _union_bbox(*bboxes: Sequence[float]) -> List[float]:
    """Return one axis-aligned bbox covering every input bbox."""

    left = min(float(bbox[0]) for bbox in bboxes)
    top = min(float(bbox[1]) for bbox in bboxes)
    right = max(float(bbox[2]) for bbox in bboxes)
    bottom = max(float(bbox[3]) for bbox in bboxes)
    return [round(float(left), 3), round(float(top), 3), round(float(right), 3), round(float(bottom), 3)]


def _arrow_line_bbox(start_xy: Tuple[float, float], end_xy: Tuple[float, float], *, padding: float) -> List[float]:
    """Return one padded bbox around one arrow shaft/head span."""

    return [
        round(float(min(start_xy[0], end_xy[0]) - padding), 3),
        round(float(min(start_xy[1], end_xy[1]) - padding), 3),
        round(float(max(start_xy[0], end_xy[0]) + padding), 3),
        round(float(max(start_xy[1], end_xy[1]) + padding), 3),
    ]


def _label_center_for_direction(
    *,
    direction: str,
    end_xy: Tuple[float, float],
    label_gap_px: int,
) -> Tuple[float, float]:
    """Return one label center near the arrow tip direction."""

    end_x, end_y = float(end_xy[0]), float(end_xy[1])
    gap = float(label_gap_px)
    if str(direction) == "left":
        return (float(end_x - gap), float(end_y))
    if str(direction) == "right":
        return (float(end_x + gap), float(end_y))
    if str(direction) == "up":
        return (float(end_x), float(end_y - gap))
    return (float(end_x), float(end_y + gap))


def _draw_force_label(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    center_xy: Tuple[float, float],
    font,
    fill: Tuple[int, int, int],
    stroke_width_px: int,
) -> List[float]:
    """Draw one centered force label and return its bbox."""

    stroke_fill = resolve_text_stroke_fill(fill)
    bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=max(0, int(stroke_width_px)))
    left, top, right, bottom = [float(value) for value in bbox]
    center_x, center_y = float(center_xy[0]), float(center_xy[1])
    text_origin = (
        float(center_x - (0.5 * (left + right))),
        float(center_y - (0.5 * (top + bottom))),
    )
    draw.text(
        text_origin,
        str(text),
        font=font,
        fill=tuple(int(value) for value in fill),
        stroke_width=max(0, int(stroke_width_px)),
        stroke_fill=tuple(int(value) for value in stroke_fill),
    )
    return [
        round(float(text_origin[0] + left), 3),
        round(float(text_origin[1] + top), 3),
        round(float(text_origin[0] + right), 3),
        round(float(text_origin[1] + bottom), 3),
    ]


def _draw_placeholder_arrow(
    draw: ImageDraw.ImageDraw,
    *,
    start_xy: Tuple[float, float],
    end_xy: Tuple[float, float],
    width_px: int,
    head_length_px: int,
    head_width_px: int,
    color: Tuple[int, int, int],
) -> None:
    """Draw one dashed placeholder arrow used by balancing-force queries."""

    start_x, start_y = float(start_xy[0]), float(start_xy[1])
    end_x, end_y = float(end_xy[0]), float(end_xy[1])
    dx = float(end_x - start_x)
    dy = float(end_y - start_y)
    length = math.hypot(float(dx), float(dy))
    if float(length) <= 1e-6:
        return
    unit_x = float(dx / length)
    unit_y = float(dy / length)
    head_length = min(float(head_length_px), float(length) * 0.42)
    shaft_end = (
        float(end_x - (unit_x * head_length)),
        float(end_y - (unit_y * head_length)),
    )
    draw_dashed_line(
        draw,
        start=(float(start_x), float(start_y)),
        end=(float(shaft_end[0]), float(shaft_end[1])),
        fill=color,
        width=max(1, int(width_px)),
        dash_px=14.0,
        gap_px=10.0,
    )
    perp_x = float(-unit_y)
    perp_y = float(unit_x)
    half_head = 0.5 * float(head_width_px)
    head_points = [
        (float(end_x), float(end_y)),
        (
            float(shaft_end[0] + (perp_x * half_head)),
            float(shaft_end[1] + (perp_y * half_head)),
        ),
        (
            float(shaft_end[0] - (perp_x * half_head)),
            float(shaft_end[1] - (perp_y * half_head)),
        ),
    ]
    draw.line([head_points[0], head_points[1]], fill=color, width=max(1, int(width_px)))
    draw.line([head_points[0], head_points[2]], fill=color, width=max(1, int(width_px)))
    draw.line([head_points[1], head_points[2]], fill=color, width=max(1, int(width_px)))


def _object_bbox_for_scene(
    *,
    scene_variant: str,
    canvas_width: int,
    canvas_height: int,
    object_width_px: int,
    object_height_px: int,
) -> List[float]:
    """Return the primary block bbox for one scene variant."""

    center_x = float(canvas_width) * 0.42
    if str(scene_variant) == "surface_block":
        center_y = float(canvas_height) * 0.58
        return [
            round(float(center_x - (0.5 * float(object_width_px))), 3),
            round(float(center_y - (0.5 * float(object_height_px))), 3),
            round(float(center_x + (0.5 * float(object_width_px))), 3),
            round(float(center_y + (0.5 * float(object_height_px))), 3),
        ]
    center_y = float(canvas_height) * 0.50
    return [
        round(float(center_x - (0.5 * float(object_width_px))), 3),
        round(float(center_y - (0.5 * float(object_height_px))), 3),
        round(float(center_x + (0.5 * float(object_width_px))), 3),
        round(float(center_y + (0.5 * float(object_height_px))), 3),
    ]


def _slot_offsets_for_direction(*, count: int) -> List[float]:
    """Return deterministic perpendicular slot offsets for one direction count."""

    count_value = max(1, int(count))
    gap = float(_DEFAULTS.arrow_slot_gap_px)
    center_index = 0.5 * float(count_value - 1)
    return [
        float((float(index) - center_index) * gap)
        for index in range(int(count_value))
    ]


def _arrow_geometry_for_offset(
    *,
    object_bbox_px: Sequence[float],
    direction: str,
    perpendicular_offset_px: float,
    arrow_length_px: int,
    arrow_gap_px: int,
) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    """Return start/end coordinates for one arrow at an explicit perpendicular offset."""

    obj_left, obj_top, obj_right, obj_bottom = [float(value) for value in object_bbox_px]
    center_x = 0.5 * float(obj_left + obj_right)
    center_y = 0.5 * float(obj_top + obj_bottom)
    arrow_length = float(arrow_length_px)
    gap = float(arrow_gap_px)
    offset = float(perpendicular_offset_px)

    if str(direction) == "left":
        return (
            (float(obj_left - gap), float(center_y + offset)),
            (float(obj_left - gap - arrow_length), float(center_y + offset)),
        )
    if str(direction) == "right":
        return (
            (float(obj_right + gap), float(center_y + offset)),
            (float(obj_right + gap + arrow_length), float(center_y + offset)),
        )
    if str(direction) == "up":
        return (
            (float(center_x + offset), float(obj_top - gap)),
            (float(center_x + offset), float(obj_top - gap - arrow_length)),
        )
    return (
        (float(center_x + offset), float(obj_bottom + gap)),
        (float(center_x + offset), float(obj_bottom + gap + arrow_length)),
    )


def _sample_block_dimensions(
    rng,
    *,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
) -> Tuple[int, int]:
    """Sample one near-square block with aspect ratio between `1:2` and `2:1`."""

    base_side_min = int(
        params.get(
            "object_base_side_min_px",
            group_default(render_defaults, "object_base_side_min_px", _DEFAULTS.object_base_side_min_px),
        )
    )
    base_side_max = int(
        params.get(
            "object_base_side_max_px",
            group_default(render_defaults, "object_base_side_max_px", _DEFAULTS.object_base_side_max_px),
        )
    )
    if int(base_side_min) > int(base_side_max):
        raise ValueError("object_base_side_min_px must be <= object_base_side_max_px")
    aspect_support = params.get(
        "object_aspect_ratio_support",
        group_default(render_defaults, "object_aspect_ratio_support", _DEFAULTS.object_aspect_ratio_support),
    )
    aspect_values = [float(value) for value in aspect_support]
    if not aspect_values:
        raise ValueError("object_aspect_ratio_support must contain at least one value")
    min_side = int(
        params.get(
            "object_min_side_px",
            group_default(render_defaults, "object_min_side_px", _DEFAULTS.object_min_side_px),
        )
    )
    base_side = int(rng.randint(int(base_side_min), int(base_side_max)))
    aspect = float(aspect_values[int(rng.randrange(len(aspect_values)))])
    if float(aspect) <= 0.0:
        raise ValueError("object aspect ratios must be positive")
    width = int(round(float(base_side) * math.sqrt(float(aspect))))
    height = int(round(float(base_side) / math.sqrt(float(aspect))))
    return max(int(min_side), int(width)), max(int(min_side), int(height))


def _arrow_geometry_for_slot(
    *,
    scene_variant: str,
    object_bbox_px: Sequence[float],
    direction: str,
    slot_index: int,
    count_in_direction: int,
    arrow_length_px: int,
    arrow_gap_px: int,
) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    """Return start/end coordinates for one force arrow slot."""

    offsets = _slot_offsets_for_direction(count=int(count_in_direction))
    return _arrow_geometry_for_offset(
        object_bbox_px=object_bbox_px,
        direction=str(direction),
        perpendicular_offset_px=float(offsets[int(slot_index)]),
        arrow_length_px=int(arrow_length_px),
        arrow_gap_px=int(arrow_gap_px),
    )


def _placeholder_perpendicular_offset(
    *,
    axis: str,
    direction_to_specs: Mapping[str, Sequence[Tuple[int, bool]]],
    slot_gap_px: int,
) -> float:
    """Return one dedicated outer lane for the balancing-force placeholder arrow."""

    axis_directions = ("left", "right") if str(axis) == "horizontal" else ("up", "down")
    existing_offsets: List[float] = []
    for direction in axis_directions:
        count = len(direction_to_specs.get(str(direction), ()))
        if int(count) > 0:
            existing_offsets.extend(_slot_offsets_for_direction(count=int(count)))
    max_abs_offset = max((abs(float(value)) for value in existing_offsets), default=0.0)
    placeholder_offset = float(max_abs_offset + (2.0 * float(slot_gap_px)))
    if str(axis) == "horizontal":
        return float(-placeholder_offset)
    return float(placeholder_offset)


def _draw_block_texture(
    draw: ImageDraw.ImageDraw,
    *,
    object_bbox_px: Sequence[float],
    line_width_px: int,
    spacing_px: int,
    ink_rgb: Tuple[int, int, int],
) -> None:
    """Draw one subtle cross-hatch texture inside the block."""

    left, top, right, bottom = [float(value) for value in object_bbox_px]
    inset = 12.0
    inner_left = float(left + inset)
    inner_top = float(top + inset)
    inner_right = float(right - inset)
    inner_bottom = float(bottom - inset)
    spacing = max(10.0, float(spacing_px))
    y_value = float(inner_top + 0.5 * spacing)
    while float(y_value) < float(inner_bottom):
        draw.line(
            [(float(inner_left), float(y_value)), (float(inner_right), float(y_value))],
            fill=tuple(int(value) for value in ink_rgb),
            width=max(1, int(line_width_px)),
        )
        y_value += float(spacing)
    x_value = float(inner_left + 0.5 * spacing)
    while float(x_value) < float(inner_right):
        draw.line(
            [(float(x_value), float(inner_top)), (float(x_value), float(inner_bottom))],
            fill=tuple(int(value) for value in ink_rgb),
            width=max(1, max(1, int(line_width_px - 1))),
        )
        x_value += float(spacing)


def _render_force_scene(
    *,
    scene_variant: str,
    query_variant: str,
    axis_arrows: List[Tuple[str, int]],
    distractor_arrows: List[Tuple[str, int]],
    balancing_direction: str | None,
    render_defaults: Mapping[str, Any],
    background: Image.Image,
) -> _RenderedScene:
    """Render one finalized force-diagram scene and project evidence bboxes."""

    canvas = background.convert("RGB")
    draw = ImageDraw.Draw(canvas)
    canvas_width = int(render_defaults["canvas_width"])
    canvas_height = int(render_defaults["canvas_height"])
    scene_rng = spawn_rng(
        int(render_defaults.get("instance_seed", 0)),
        f"{TASK_ID}.block_shape.{str(scene_variant)}",
    )
    object_width_px, object_height_px = _sample_block_dimensions(
        scene_rng,
        params=render_defaults,
        render_defaults=render_defaults,
    )
    object_bbox_px = _object_bbox_for_scene(
        scene_variant=str(scene_variant),
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        object_width_px=int(object_width_px),
        object_height_px=int(object_height_px),
    )
    obj_left, obj_top, obj_right, obj_bottom = [float(value) for value in object_bbox_px]
    center_x = 0.5 * float(obj_left + obj_right)
    center_y = 0.5 * float(obj_top + obj_bottom)

    surface_bbox_px: List[float] | None = None
    if str(scene_variant) == "surface_block":
        surface_y = float(obj_bottom + 28.0)
        draw.line(
            [(float(obj_left - 180.0), float(surface_y)), (float(canvas_width - 80.0), float(surface_y))],
            fill=(112, 118, 129),
            width=max(1, int(render_defaults["surface_line_width_px"])),
        )
        surface_bbox_px = [
            round(float(obj_left - 180.0), 3),
            round(float(surface_y - (0.5 * float(render_defaults["surface_line_width_px"]))), 3),
            round(float(canvas_width - 80.0), 3),
            round(float(surface_y + (0.5 * float(render_defaults["surface_line_width_px"]))), 3),
        ]
        draw_rounded_rect(
            draw,
            tuple(float(value) for value in object_bbox_px),
            radius=int(render_defaults["object_corner_radius_px"]),
            fill=(239, 244, 252),
            outline=(58, 69, 84),
            width=max(1, int(render_defaults["object_outline_width_px"])),
        )
    else:
        draw_rounded_rect(
            draw,
            tuple(float(value) for value in object_bbox_px),
            radius=int(render_defaults["object_corner_radius_px"]),
            fill=(240, 244, 250),
            outline=(58, 69, 84),
            width=max(1, int(render_defaults["object_outline_width_px"])),
        )
        if str(scene_variant) == "textured_block":
            _draw_block_texture(
                draw,
                object_bbox_px=object_bbox_px,
                line_width_px=int(render_defaults["texture_line_width_px"]),
                spacing_px=int(render_defaults["texture_spacing_px"]),
                ink_rgb=(200, 209, 223),
            )

    relevant_axis = str(_query_axis(str(query_variant)))
    all_arrows = list(axis_arrows) + list(distractor_arrows)
    direction_to_specs: Dict[str, List[Tuple[int, bool]]] = {}
    for direction, magnitude in all_arrows:
        relevant = str(_AXIS_BY_DIRECTION[str(direction)]) == str(relevant_axis)
        direction_to_specs.setdefault(str(direction), []).append((int(magnitude), bool(relevant)))

    label_font = load_font(int(render_defaults["label_font_size_px"]), bold=True)
    arrow_specs: List[_ArrowSpec] = []
    scene_entities: List[Dict[str, Any]] = [
        {
            "entity_id": "force_object",
            "entity_type": "physics_object",
            "bbox_px": [round(float(value), 3) for value in object_bbox_px],
            "meta": {
                "scene_variant": str(scene_variant),
            },
        }
    ]
    if surface_bbox_px is not None:
        scene_entities.append(
            {
                "entity_id": "surface_line",
                "entity_type": "physics_surface",
                "bbox_px": list(surface_bbox_px),
            }
        )

    arrow_counter = 0
    evidence_bboxes: List[List[float]] = []
    evidence_arrow_ids: List[str] = []
    for direction in ("left", "right", "up", "down"):
        specs_for_direction = direction_to_specs.get(str(direction), [])
        for slot_index, (magnitude, relevant) in enumerate(specs_for_direction):
            start_xy, end_xy = _arrow_geometry_for_slot(
                scene_variant=str(scene_variant),
                object_bbox_px=object_bbox_px,
                direction=str(direction),
                slot_index=int(slot_index),
                count_in_direction=len(specs_for_direction),
                arrow_length_px=int(render_defaults["arrow_length_px"]),
                arrow_gap_px=int(render_defaults["arrow_gap_px"]),
            )
            arrow_fill = tuple(int(value) for value in _ARROW_FILL[str(direction)])
            draw_arrow(
                draw,
                start=start_xy,
                end=end_xy,
                fill=arrow_fill,
                width=max(1, int(render_defaults["arrow_width_px"])),
                head_length_px=float(render_defaults["arrow_head_length_px"]),
                head_width_px=float(render_defaults["arrow_head_width_px"]),
            )
            label_center = _label_center_for_direction(
                direction=str(direction),
                end_xy=end_xy,
                label_gap_px=int(render_defaults["label_gap_px"]),
            )
            label_bbox = _draw_force_label(
                draw,
                text=f"{int(magnitude)} N",
                center_xy=label_center,
                font=label_font,
                fill=(28, 33, 39),
                stroke_width_px=int(render_defaults["label_stroke_width_px"]),
            )
            arrow_bbox = _union_bbox(
                _arrow_line_bbox(
                    start_xy,
                    end_xy,
                    padding=max(
                        float(render_defaults["arrow_head_width_px"]),
                        float(render_defaults["label_box_padding_px"]),
                    ),
                ),
                label_bbox,
            )
            arrow_counter += 1
            arrow_id = f"force_arrow_{int(arrow_counter)}"
            spec = _ArrowSpec(
                arrow_id=str(arrow_id),
                direction=str(direction),
                magnitude=int(magnitude),
                bbox_px=list(arrow_bbox),
                label_bbox_px=list(label_bbox),
                relevant=bool(relevant),
                role="evidence" if bool(relevant) else "distractor",
            )
            arrow_specs.append(spec)
            scene_entities.append(
                {
                    "entity_id": str(arrow_id),
                    "entity_type": "physics_force_arrow",
                    "bbox_px": list(arrow_bbox),
                    "meta": {
                        "direction": str(direction),
                        "axis": str(_AXIS_BY_DIRECTION[str(direction)]),
                        "magnitude_n": int(magnitude),
                        "relevant_to_query": bool(relevant),
                    },
                }
            )
            if bool(relevant):
                evidence_bboxes.append(list(arrow_bbox))
                evidence_arrow_ids.append(str(arrow_id))

    placeholder_bbox_px: List[float] | None = None
    if balancing_direction is not None:
        placeholder_offset_px = _placeholder_perpendicular_offset(
            axis=str(relevant_axis),
            direction_to_specs=direction_to_specs,
            slot_gap_px=int(render_defaults["arrow_slot_gap_px"]),
        )
        placeholder_start_xy, placeholder_end_xy = _arrow_geometry_for_offset(
            object_bbox_px=object_bbox_px,
            direction=str(balancing_direction),
            perpendicular_offset_px=float(placeholder_offset_px),
            arrow_length_px=int(render_defaults["arrow_length_px"]),
            arrow_gap_px=int(render_defaults["arrow_gap_px"]) + int(render_defaults["balancing_arrow_gap_extra_px"]),
        )
        placeholder_color = (181, 52, 77)
        _draw_placeholder_arrow(
            draw,
            start_xy=placeholder_start_xy,
            end_xy=placeholder_end_xy,
            width_px=max(1, int(render_defaults["arrow_width_px"]) - 1),
            head_length_px=int(render_defaults["arrow_head_length_px"]),
            head_width_px=int(render_defaults["arrow_head_width_px"]),
            color=placeholder_color,
        )
        label_center = _label_center_for_direction(
            direction=str(balancing_direction),
            end_xy=placeholder_end_xy,
            label_gap_px=int(render_defaults["label_gap_px"]) + int(render_defaults["balancing_label_gap_extra_px"]),
        )
        label_bbox = _draw_force_label(
            draw,
            text="? N",
            center_xy=label_center,
            font=label_font,
            fill=placeholder_color,
            stroke_width_px=int(render_defaults["label_stroke_width_px"]),
        )
        placeholder_bbox_px = _union_bbox(
            _arrow_line_bbox(
                placeholder_start_xy,
                placeholder_end_xy,
                padding=max(
                    float(render_defaults["arrow_head_width_px"]),
                    float(render_defaults["label_box_padding_px"]),
                ),
            ),
            label_bbox,
        )
        scene_entities.append(
            {
                "entity_id": "balancing_force_marker",
                "entity_type": "physics_missing_force_marker",
                "bbox_px": list(placeholder_bbox_px),
                "meta": {
                    "direction": str(balancing_direction),
                    "axis": str(_AXIS_BY_DIRECTION[str(balancing_direction)]),
                },
            }
        )

    render_map = {
        "object_bbox_px": [round(float(value), 3) for value in object_bbox_px],
        "arrow_bboxes_px": {spec.arrow_id: list(spec.bbox_px) for spec in arrow_specs},
        "arrow_label_bboxes_px": {spec.arrow_id: list(spec.label_bbox_px) for spec in arrow_specs},
        "evidence_arrow_ids": list(evidence_arrow_ids),
        "scene_center_px": [round(float(center_x), 3), round(float(center_y), 3)],
    }
    if surface_bbox_px is not None:
        render_map["surface_bbox_px"] = list(surface_bbox_px)
    if placeholder_bbox_px is not None:
        render_map["balancing_force_marker_bbox_px"] = list(placeholder_bbox_px)
    render_map["object_width_px"] = int(object_width_px)
    render_map["object_height_px"] = int(object_height_px)
    render_map["object_aspect_ratio"] = round(float(object_width_px) / float(object_height_px), 4)

    return _RenderedScene(
        image=canvas,
        arrow_specs=list(arrow_specs),
        placeholder_direction=str(balancing_direction) if balancing_direction is not None else None,
        placeholder_bbox_px=list(placeholder_bbox_px) if placeholder_bbox_px is not None else None,
        object_bbox_px=[round(float(value), 3) for value in object_bbox_px],
        object_width_px=int(object_width_px),
        object_height_px=int(object_height_px),
        surface_bbox_px=list(surface_bbox_px) if surface_bbox_px is not None else None,
        evidence_bboxes=list(evidence_bboxes),
        evidence_arrow_ids=list(evidence_arrow_ids),
        render_map=render_map,
        scene_entities=list(scene_entities),
    )


@register_task
class PhysicsMechanicsForceDiagramTask:
    """Return one simple mechanics force-diagram question."""

    task_id = TASK_ID
    domain = "physics"
    task_group = "mechanics"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        query_axis = _query_axis(str(axes.query_variant))
        force_magnitude_min = int(params.get("force_magnitude_min", group_default(_GEN_DEFAULTS, "force_magnitude_min", _DEFAULTS.force_magnitude_min)))
        force_magnitude_max = int(params.get("force_magnitude_max", group_default(_GEN_DEFAULTS, "force_magnitude_max", _DEFAULTS.force_magnitude_max)))

        rendered_scene: _RenderedScene | None = None
        dominant_direction: str | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            axis_arrows, dominant_direction = _sample_axis_arrow_magnitudes(
                attempt_rng,
                axis=str(query_axis),
                target_force=int(axes.target_force),
                force_magnitude_min=int(force_magnitude_min),
                force_magnitude_max=int(force_magnitude_max),
            )
            distractor_arrows = _sample_distractor_arrows(
                attempt_rng,
                scene_variant=str(axes.scene_variant),
                axis=str(query_axis),
                force_magnitude_min=int(force_magnitude_min),
                force_magnitude_max=int(force_magnitude_max),
            )
            balancing_direction = None
            if _is_balancing_query(str(axes.query_variant)):
                if int(axes.target_force) <= 0:
                    continue
                balancing_direction = str(_OPPOSITE_DIRECTION[str(dominant_direction)])

            background, background_meta = make_background_canvas(
                canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
                canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
                instance_seed=int(instance_seed),
                params=params,
                default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
            )
            rendered_scene = _render_force_scene(
                scene_variant=str(axes.scene_variant),
                query_variant=str(axes.query_variant),
                axis_arrows=list(axis_arrows),
                distractor_arrows=list(distractor_arrows),
                balancing_direction=balancing_direction,
                render_defaults={
                    key: params.get(key, group_default(_RENDER_DEFAULTS, key, getattr(_DEFAULTS, key)))
                    for key in (
                        "canvas_width",
                        "canvas_height",
                        "outer_margin_px",
                        "object_base_side_min_px",
                        "object_base_side_max_px",
                        "object_min_side_px",
                        "object_aspect_ratio_support",
                        "object_outline_width_px",
                        "object_corner_radius_px",
                        "arrow_length_px",
                        "arrow_width_px",
                        "arrow_head_length_px",
                        "arrow_head_width_px",
                        "arrow_gap_px",
                        "arrow_slot_gap_px",
                        "balancing_arrow_gap_extra_px",
                        "balancing_label_gap_extra_px",
                        "label_gap_px",
                        "label_font_size_px",
                        "label_stroke_width_px",
                        "label_box_padding_px",
                        "surface_line_width_px",
                        "texture_line_width_px",
                        "texture_spacing_px",
                    )
                }
                | {"instance_seed": int(instance_seed)},
                background=background,
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
                    "task_family_key",
                    "task_key",
                    "json_output_contract",
                    "json_output_contract_answer_only",
                    "answer_hint",
                    "evidence_hint",
                    "object_description_free_body_box",
                    "object_description_surface_block",
                    "object_description_textured_block",
                ),
                context=f"prompt defaults for {self.task_id}",
            )
            json_example, json_example_answer_only = build_prompt_json_examples(
                evidence_value=list(rendered_scene.evidence_bboxes[:2] if rendered_scene.evidence_bboxes else [[120, 200, 240, 260], [430, 200, 548, 260]]),
                answer_type="integer",
            )
            prompt_selection = render_task_prompt_variants(
                domain=self.domain,
                task_group=self.task_group,
                bundle_id=str(prompt_defaults["bundle_id"]),
                task_family_key=str(prompt_defaults["task_family_key"]),
                task_key=str(prompt_defaults["task_key"]),
                task_variant_key=str(axes.query_variant),
                answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
                slots={
                    "object_description": str(prompt_defaults[f"object_description_{str(axes.scene_variant)}"]),
                    "marked_direction_label": str(_QUERY_DIRECTION_TEXT.get(str(rendered_scene.placeholder_direction), "marked")),
                    "json_output_contract": str(prompt_defaults["json_output_contract"]),
                    "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                    "evidence_hint": str(prompt_defaults["evidence_hint"]),
                    "answer_hint": str(prompt_defaults["answer_hint"]),
                    "json_example": str(json_example),
                    "json_example_answer_only": str(json_example_answer_only),
                },
                instance_seed=int(instance_seed),
            )
            prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

            answer_gt = TypedValue(type="integer", value=int(axes.target_force))
            evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in rendered_scene.evidence_bboxes])
            complexity = build_physics_force_diagram_complexity(
                task_group_defaults=_TASK_GROUP_DEFAULTS,
                task_id=self.task_id,
                scene_variant=str(axes.scene_variant),
                query_variant=str(axes.query_variant),
                arrow_count=len(rendered_scene.arrow_specs),
                relevant_arrow_count=len(rendered_scene.evidence_arrow_ids),
                target_force=int(axes.target_force),
            )
            trace_payload = {
                "scene_ir": {
                    "scene_kind": f"physics_force_diagram_{str(axes.scene_variant)}",
                    "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                    "relations": {
                        "scene_variant": str(axes.scene_variant),
                        "query_variant": str(axes.query_variant),
                        "task_variant": str(axes.query_variant),
                        "query_axis": str(query_axis),
                        "answer_force_n": int(axes.target_force),
                        "evidence_arrow_ids": list(rendered_scene.evidence_arrow_ids),
                        "object_aspect_ratio": round(
                            float(rendered_scene.object_width_px) / float(rendered_scene.object_height_px),
                            4,
                        ),
                    },
                },
                "query_spec": {
                    "task_variant": str(axes.query_variant),
                    "template_id": str(prompt_defaults["bundle_id"]),
                    "prompt_variant": dict(prompt_artifacts.prompt_variant),
                    "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                    "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                    "params": {
                        "scene_variant": str(axes.scene_variant),
                        "query_variant": str(axes.query_variant),
                        "task_variant": str(axes.query_variant),
                        "query_axis": str(query_axis),
                        "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                        "query_variant_probabilities": dict(axes.query_variant_probabilities),
                        "task_variant_probabilities": dict(axes.query_variant_probabilities),
                        "target_force": int(axes.target_force),
                        "target_force_probabilities": dict(axes.target_force_probabilities),
                    },
                },
                "render_spec": {
                    "scene_variant": str(axes.scene_variant),
                    "canvas_width": int(image.size[0]),
                    "canvas_height": int(image.size[1]),
                    "object_width_px": int(rendered_scene.object_width_px),
                    "object_height_px": int(rendered_scene.object_height_px),
                },
                "render_map": dict(rendered_scene.render_map),
                "execution_trace": {
                    "scene_variant": str(axes.scene_variant),
                    "query_variant": str(axes.query_variant),
                    "task_variant": str(axes.query_variant),
                    "query_axis": str(query_axis),
                    "answer_force_n": int(axes.target_force),
                    "target_force": int(axes.target_force),
                    "target_force_support": list(
                        _resolve_support(
                            params,
                            key="balancing_force_support" if _is_balancing_query(str(axes.query_variant)) else "target_force_support",
                            fallback=_DEFAULTS.balancing_force_support if _is_balancing_query(str(axes.query_variant)) else _DEFAULTS.target_force_support,
                        )
                    ),
                    "dominant_direction": str(dominant_direction),
                    "balancing_direction": str(rendered_scene.placeholder_direction) if rendered_scene.placeholder_direction is not None else None,
                    "object_width_px": int(rendered_scene.object_width_px),
                    "object_height_px": int(rendered_scene.object_height_px),
                    "object_aspect_ratio": round(
                        float(rendered_scene.object_width_px) / float(rendered_scene.object_height_px),
                        4,
                    ),
                    "arrow_specs": [
                        {
                            "arrow_id": str(spec.arrow_id),
                            "direction": str(spec.direction),
                            "axis": str(_AXIS_BY_DIRECTION[str(spec.direction)]),
                            "magnitude_n": int(spec.magnitude),
                            "relevant_to_query": bool(spec.relevant),
                            "role": str(spec.role),
                        }
                        for spec in rendered_scene.arrow_specs
                    ],
                    "evidence_arrow_ids": list(rendered_scene.evidence_arrow_ids),
                },
                "witness_symbolic": {
                    "type": "id_set",
                    "ids": [str(item) for item in rendered_scene.evidence_arrow_ids],
                },
                "projected_evidence": {
                    "bbox_set": [list(bbox) for bbox in rendered_scene.evidence_bboxes],
                },
                "background": background_meta,
                "post_image_noise": post_noise_meta,
            }
            return TaskOutput(
                prompt=str(prompt_artifacts.prompt),
                prompt_variants=dict(prompt_artifacts.prompt_variants),
                answer_gt=answer_gt,
                evidence_gt=evidence_gt,
                image=image,
                image_id="img0",
                trace_payload=trace_payload,
                complexity=complexity,
                task_versions=default_task_versions(),
                task_variant=str(axes.query_variant),
            )

        raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts")


__all__ = ["PhysicsMechanicsForceDiagramTask"]
