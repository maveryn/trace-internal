"""Physics mechanics task for simple lever-balance diagrams."""

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
from ...shared.drawing import draw_rounded_rect
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import build_prompt_json_examples
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from ...shared.variant_sampling import (
    apply_balanced_variant_sampling,
    resolve_compatible_scene_query_variants,
    resolve_variant,
)
from ..shared.complexity import build_physics_lever_balance_complexity
from ..shared.style import SUPPORTED_PHYSICS_COLOR_NAMES, build_physics_lever_theme
from ..shared.support_sampling import resolve_integer_choice, resolve_integer_support
from ..shared.visual_defaults import load_physics_background_defaults, load_physics_noise_defaults


TASK_ID = "task_physics_mechanics_lever_balance"
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "center_fulcrum",
    "offset_fulcrum",
    "textured_beam",
)
SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = (
    "left_torque",
    "right_torque",
    "missing_weight_to_balance",
)
COMPATIBILITY: Dict[str, Sequence[str]] = {
    "center_fulcrum": SUPPORTED_QUERY_VARIANTS,
    "offset_fulcrum": SUPPORTED_QUERY_VARIANTS,
    "textured_beam": SUPPORTED_QUERY_VARIANTS,
}


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for lever-balance scenes."""

    canvas_width: int = 920
    canvas_height: int = 560
    beam_width_px: int = 580
    beam_height_px: int = 22
    beam_corner_radius_px: int = 10
    beam_center_y_px: int = 306
    fulcrum_width_px: int = 110
    fulcrum_height_px: int = 84
    fulcrum_offset_px: int = 76
    slot_spacing_px: int = 62
    distance_support: Tuple[int, ...] = (1, 2, 3, 4)
    weight_box_width_px: int = 58
    weight_box_height_px: int = 52
    weight_box_gap_px: int = 8
    weight_font_size_px: int = 26
    distance_font_size_px: int = 22
    label_stroke_width_px: int = 3
    texture_line_width_px: int = 2
    texture_spacing_px: int = 18
    torque_answer_support: Tuple[int, ...] = tuple(range(2, 25))
    missing_weight_support: Tuple[int, ...] = tuple(range(1, 13))
    weight_value_min: int = 1
    weight_value_max: int = 9
    max_side_weights: int = 2


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved scene/query axes and answer support for one instance."""

    scene_variant: str
    query_variant: str
    accent_color_name: str
    target_answer: int
    scene_variant_probabilities: Dict[str, float]
    query_variant_probabilities: Dict[str, float]
    accent_color_name_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _WeightPlacement:
    """One weight or placeholder attached to the lever."""

    weight_id: str
    side: str
    distance_units: int
    value: int | None
    missing: bool
    relevant: bool
    bbox_px: List[float]


@dataclass(frozen=True)
class _RenderedScene:
    """Rendered lever-balance scene plus prompt-facing evidence metadata."""

    image: Image.Image
    beam_bbox_px: List[float]
    fulcrum_bbox_px: List[float]
    weight_specs: List[_WeightPlacement]
    placeholder_bbox_px: List[float] | None
    relevant_weight_bboxes: List[List[float]]
    relevant_weight_ids: List[str]
    evidence_bboxes: List[List[float]]
    evidence_entity_ids: List[str]
    render_map: Dict[str, Any]
    scene_entities: List[Dict[str, Any]]
    max_distance_units: int


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("physics", "mechanics")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_physics_background_defaults(task_group="mechanics")
POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(task_group="mechanics", apply_prob=0.0)


def _is_missing_weight_query(query_variant: str) -> bool:
    """Return true when the query asks for one missing balancing weight."""

    return str(query_variant) == "missing_weight_to_balance"


def _resolve_target_answer(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    query_variant: str,
) -> Tuple[int, Dict[str, float]]:
    """Resolve the sampled answer support for one lever-balance query."""

    return resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="missing_weight_support" if _is_missing_weight_query(str(query_variant)) else "torque_answer_support",
        explicit_key="target_answer",
        fallback_support=_DEFAULTS.missing_weight_support if _is_missing_weight_query(str(query_variant)) else _DEFAULTS.torque_answer_support,
        namespace=f"{TASK_ID}.target_answer.{str(query_variant)}",
        balanced_flag_key="balanced_target_answer_sampling",
    )


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve one compatible scene/query pair plus answer support."""

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
    target_answer, target_answer_probabilities = _resolve_target_answer(
        instance_seed=int(instance_seed),
        params=params,
        query_variant=str(query_variant),
    )
    color_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.accent_color_name")
    accent_color_name, accent_color_name_probabilities = resolve_variant(
        color_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_PHYSICS_COLOR_NAMES,
        explicit_key="accent_color_name",
        weights_key="accent_color_name_weights",
    )
    accent_color_name = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(accent_color_name),
        variant_probabilities=accent_color_name_probabilities,
        supported_variants=SUPPORTED_PHYSICS_COLOR_NAMES,
        balance_flag_key="balanced_accent_color_name_sampling",
        explicit_key="accent_color_name",
        weights_key="accent_color_name_weights",
        sampling_namespace=f"{TASK_ID}.accent_color_name",
    )
    return _ResolvedAxes(
        scene_variant=str(scene_variant),
        query_variant=str(query_variant),
        accent_color_name=str(accent_color_name),
        target_answer=int(target_answer),
        scene_variant_probabilities=dict(scene_probs),
        query_variant_probabilities=dict(query_probs),
        accent_color_name_probabilities=dict(accent_color_name_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
    )


def _distance_support(params: Mapping[str, Any]) -> Tuple[int, ...]:
    """Return the active integer distance slots available on each side."""

    return resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key="distance_support",
        fallback=_DEFAULTS.distance_support,
    )


def _candidate_side_configs_for_torque(
    *,
    target_torque: int,
    distance_support: Sequence[int],
    weight_min: int,
    weight_max: int,
    max_weights: int,
) -> List[List[Tuple[int, int]]]:
    """Enumerate feasible `(distance, weight)` sets that match one target torque."""

    distances = [int(value) for value in distance_support]
    candidates: List[List[Tuple[int, int]]] = []
    for distance in distances:
        if int(target_torque) % int(distance) != 0:
            continue
        weight = int(target_torque) // int(distance)
        if int(weight_min) <= int(weight) <= int(weight_max):
            candidates.append([(int(distance), int(weight))])

    if int(max_weights) >= 2:
        for first_index, first_distance in enumerate(distances):
            for second_distance in distances[first_index + 1 :]:
                for first_weight in range(int(weight_min), int(weight_max) + 1):
                    remaining = int(target_torque) - (int(first_distance) * int(first_weight))
                    if int(remaining) <= 0 or int(remaining) % int(second_distance) != 0:
                        continue
                    second_weight = int(remaining) // int(second_distance)
                    if int(weight_min) <= int(second_weight) <= int(weight_max):
                        candidates.append(
                            [
                                (int(first_distance), int(first_weight)),
                                (int(second_distance), int(second_weight)),
                            ]
                        )
    deduped: List[List[Tuple[int, int]]] = []
    seen: set[Tuple[Tuple[int, int], ...]] = set()
    for candidate in candidates:
        canonical = tuple(sorted((int(distance), int(weight)) for distance, weight in candidate))
        if canonical in seen:
            continue
        seen.add(canonical)
        deduped.append([(int(distance), int(weight)) for distance, weight in canonical])
    return deduped


def _sample_random_side_config(
    rng,
    *,
    distance_support: Sequence[int],
    weight_min: int,
    weight_max: int,
    max_weights: int,
) -> List[Tuple[int, int]]:
    """Sample one random visible weight set for the non-queried side."""

    distances = [int(value) for value in distance_support]
    count = int(rng.randint(1, min(int(max_weights), len(distances))))
    chosen_distances = sorted(rng.sample(distances, count))
    return [
        (int(distance), int(rng.randint(int(weight_min), int(weight_max))))
        for distance in chosen_distances
    ]


def _sample_same_side_known_weights(
    rng,
    *,
    placeholder_distance: int,
    distance_support: Sequence[int],
    weight_min: int,
    weight_max: int,
) -> List[Tuple[int, int]]:
    """Sample zero or one extra shown weight on the placeholder side."""

    remaining_distances = [int(value) for value in distance_support if int(value) != int(placeholder_distance)]
    if not remaining_distances or rng.random() < 0.55:
        return []
    chosen_distance = int(remaining_distances[int(rng.randrange(len(remaining_distances)))])
    return [(int(chosen_distance), int(rng.randint(int(weight_min), int(weight_max))))]


def _sample_weight_layout(
    rng,
    *,
    query_variant: str,
    target_answer: int,
    params: Mapping[str, Any],
) -> Tuple[List[Tuple[str, int, int | None, bool, bool]], Dict[str, Any]]:
    """Sample one full lever layout satisfying the requested answer."""

    distance_support = _distance_support(params)
    weight_min = int(params.get("weight_value_min", group_default(_GEN_DEFAULTS, "weight_value_min", _DEFAULTS.weight_value_min)))
    weight_max = int(params.get("weight_value_max", group_default(_GEN_DEFAULTS, "weight_value_max", _DEFAULTS.weight_value_max)))
    max_weights = int(params.get("max_side_weights", group_default(_GEN_DEFAULTS, "max_side_weights", _DEFAULTS.max_side_weights)))

    if str(query_variant) in {"left_torque", "right_torque"}:
        relevant_side = "left" if str(query_variant) == "left_torque" else "right"
        distractor_side = "right" if str(relevant_side) == "left" else "left"
        relevant_candidates = _candidate_side_configs_for_torque(
            target_torque=int(target_answer),
            distance_support=distance_support,
            weight_min=int(weight_min),
            weight_max=int(weight_max),
            max_weights=int(max_weights),
        )
        if not relevant_candidates:
            raise ValueError(f"unable to build side config for torque target {target_answer}")
        relevant_config = relevant_candidates[int(rng.randrange(len(relevant_candidates)))]
        distractor_config = _sample_random_side_config(
            rng,
            distance_support=distance_support,
            weight_min=int(weight_min),
            weight_max=int(weight_max),
            max_weights=int(max_weights),
        )
        placements = [
            (str(relevant_side), int(distance), int(weight), False, True)
            for distance, weight in relevant_config
        ] + [
            (str(distractor_side), int(distance), int(weight), False, False)
            for distance, weight in distractor_config
        ]
        metadata = {
            "query_side": str(relevant_side),
            "known_torque_left": sum(int(distance) * int(weight) for side, distance, weight, _, _ in placements if side == "left" and weight is not None),
            "known_torque_right": sum(int(distance) * int(weight) for side, distance, weight, _, _ in placements if side == "right" and weight is not None),
            "placeholder_side": None,
        }
        return placements, metadata

    placeholder_side = "left" if rng.random() < 0.5 else "right"
    opposite_side = "right" if str(placeholder_side) == "left" else "left"
    for _ in range(120):
        placeholder_distance = int(distance_support[int(rng.randrange(len(distance_support)))])
        same_side_known = _sample_same_side_known_weights(
            rng,
            placeholder_distance=int(placeholder_distance),
            distance_support=distance_support,
            weight_min=int(weight_min),
            weight_max=int(weight_max),
        )
        same_side_torque = sum(int(distance) * int(weight) for distance, weight in same_side_known)
        opposite_target_torque = int(same_side_torque + (int(target_answer) * int(placeholder_distance)))
        opposite_candidates = _candidate_side_configs_for_torque(
            target_torque=int(opposite_target_torque),
            distance_support=distance_support,
            weight_min=int(weight_min),
            weight_max=int(weight_max),
            max_weights=int(max_weights),
        )
        if not opposite_candidates:
            continue
        opposite_config = opposite_candidates[int(rng.randrange(len(opposite_candidates)))]
        placements = [
            (str(placeholder_side), int(placeholder_distance), None, True, True),
        ] + [
            (str(placeholder_side), int(distance), int(weight), False, True)
            for distance, weight in same_side_known
        ] + [
            (str(opposite_side), int(distance), int(weight), False, True)
            for distance, weight in opposite_config
        ]
        metadata = {
            "query_side": None,
            "known_torque_left": sum(int(distance) * int(weight) for side, distance, weight, missing, _ in placements if side == "left" and weight is not None and not missing),
            "known_torque_right": sum(int(distance) * int(weight) for side, distance, weight, missing, _ in placements if side == "right" and weight is not None and not missing),
            "placeholder_side": str(placeholder_side),
            "placeholder_distance_units": int(placeholder_distance),
        }
        return placements, metadata
    raise ValueError("unable to sample missing-weight lever layout")


def _beam_center_x(
    rng,
    *,
    scene_variant: str,
    canvas_width: int,
) -> float:
    """Return the horizontal fulcrum center for one scene variant."""

    center_x = 0.5 * float(canvas_width)
    if str(scene_variant) != "offset_fulcrum":
        return float(center_x)
    direction = -1.0 if rng.random() < 0.5 else 1.0
    offset_px = float(
        group_default(
            _RENDER_DEFAULTS,
            "fulcrum_offset_px",
            _DEFAULTS.fulcrum_offset_px,
        )
    )
    return float(center_x + (direction * offset_px))


def _draw_beam_texture(
    draw: ImageDraw.ImageDraw,
    *,
    beam_bbox_px: Sequence[float],
    line_width_px: int,
    spacing_px: int,
    ink_rgb: Tuple[int, int, int],
) -> None:
    """Draw one subtle wood-like texture inside the beam."""

    left, top, right, bottom = [float(value) for value in beam_bbox_px]
    y_value = float(top + (0.5 * spacing_px))
    while float(y_value) < float(bottom):
        draw.line(
            [(float(left + 8.0), float(y_value)), (float(right - 8.0), float(y_value))],
            fill=ink_rgb,
            width=max(1, int(line_width_px)),
        )
        y_value += float(spacing_px)


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    center_xy: Tuple[float, float],
    font,
    fill: Tuple[int, int, int],
    stroke_width_px: int,
) -> List[float]:
    """Draw centered text and return the rendered bbox."""

    stroke_fill = resolve_text_stroke_fill(fill)
    bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=max(0, int(stroke_width_px)))
    left, top, right, bottom = [float(value) for value in bbox]
    center_x, center_y = float(center_xy[0]), float(center_xy[1])
    origin = (
        float(center_x - (0.5 * (left + right))),
        float(center_y - (0.5 * (top + bottom))),
    )
    draw.text(
        origin,
        str(text),
        font=font,
        fill=tuple(int(value) for value in fill),
        stroke_width=max(0, int(stroke_width_px)),
        stroke_fill=tuple(int(value) for value in stroke_fill),
    )
    return [
        round(float(origin[0] + left), 3),
        round(float(origin[1] + top), 3),
        round(float(origin[0] + right), 3),
        round(float(origin[1] + bottom), 3),
    ]


def _render_scene(
    *,
    scene_variant: str,
    query_variant: str,
    accent_color_name: str,
    placements: Sequence[Tuple[str, int, int | None, bool, bool]],
    render_defaults: Mapping[str, Any],
    background: Image.Image,
) -> _RenderedScene:
    """Render one finalized lever-balance scene."""

    canvas = background.convert("RGB")
    draw = ImageDraw.Draw(canvas)
    canvas_width = int(render_defaults["canvas_width"])
    lever_theme = build_physics_lever_theme(str(accent_color_name))
    scene_rng = spawn_rng(int(render_defaults.get("instance_seed", 0)), f"{TASK_ID}.scene_layout.{str(scene_variant)}")
    beam_center_x = _beam_center_x(scene_rng, scene_variant=str(scene_variant), canvas_width=int(canvas_width))
    beam_center_y = float(render_defaults["beam_center_y_px"])
    beam_width = float(render_defaults["beam_width_px"])
    beam_height = float(render_defaults["beam_height_px"])
    beam_bbox_px = [
        round(float(beam_center_x - (0.5 * beam_width)), 3),
        round(float(beam_center_y - (0.5 * beam_height)), 3),
        round(float(beam_center_x + (0.5 * beam_width)), 3),
        round(float(beam_center_y + (0.5 * beam_height)), 3),
    ]
    fulcrum_width = float(render_defaults["fulcrum_width_px"])
    fulcrum_height = float(render_defaults["fulcrum_height_px"])
    fulcrum_bbox_px = [
        round(float(beam_center_x - (0.5 * fulcrum_width)), 3),
        round(float(beam_bbox_px[3]), 3),
        round(float(beam_center_x + (0.5 * fulcrum_width)), 3),
        round(float(beam_bbox_px[3] + fulcrum_height), 3),
    ]

    draw_rounded_rect(
        draw,
        tuple(float(value) for value in beam_bbox_px),
        radius=int(render_defaults["beam_corner_radius_px"]),
        fill=tuple(int(channel) for channel in lever_theme.beam_fill_rgb),
        outline=tuple(int(channel) for channel in lever_theme.beam_outline_rgb),
        width=3,
    )
    if str(scene_variant) == "textured_beam":
        _draw_beam_texture(
            draw,
            beam_bbox_px=beam_bbox_px,
            line_width_px=int(render_defaults["texture_line_width_px"]),
            spacing_px=int(render_defaults["texture_spacing_px"]),
            ink_rgb=tuple(int(channel) for channel in lever_theme.texture_rgb),
        )

    draw.polygon(
        [
            (float(beam_center_x), float(fulcrum_bbox_px[1] + 6.0)),
            (float(fulcrum_bbox_px[0]), float(fulcrum_bbox_px[3])),
            (float(fulcrum_bbox_px[2]), float(fulcrum_bbox_px[3])),
        ],
        fill=tuple(int(channel) for channel in lever_theme.fulcrum_fill_rgb),
        outline=tuple(int(channel) for channel in lever_theme.fulcrum_outline_rgb),
    )

    distance_support = _distance_support(render_defaults)
    slot_spacing = float(render_defaults["slot_spacing_px"])
    distance_font = load_font(int(render_defaults["distance_font_size_px"]), bold=True)
    weight_font = load_font(int(render_defaults["weight_font_size_px"]), bold=True)
    for distance_units in distance_support:
        for side, sign in (("left", -1.0), ("right", 1.0)):
            tick_x = float(beam_center_x + (sign * float(distance_units) * slot_spacing))
            draw.line(
                [(float(tick_x), float(beam_bbox_px[1] - 8.0)), (float(tick_x), float(beam_bbox_px[3] + 8.0))],
                fill=tuple(int(channel) for channel in lever_theme.beam_tick_rgb),
                width=2,
            )
            _draw_centered_text(
                draw,
                text=str(int(distance_units)),
                center_xy=(float(tick_x), float(beam_bbox_px[3] + 22.0)),
                font=distance_font,
                fill=tuple(int(channel) for channel in lever_theme.distance_text_rgb),
                stroke_width_px=max(0, int(render_defaults["label_stroke_width_px"]) - 1),
            )

    weight_specs: List[_WeightPlacement] = []
    relevant_weight_bboxes: List[List[float]] = []
    relevant_weight_ids: List[str] = []
    scene_entities: List[Dict[str, Any]] = [
        {
            "entity_id": "lever_beam",
            "entity_type": "physics_lever_beam",
            "bbox_px": list(beam_bbox_px),
            "meta": {"scene_variant": str(scene_variant)},
        },
        {
            "entity_id": "lever_fulcrum",
            "entity_type": "physics_fulcrum",
            "bbox_px": list(fulcrum_bbox_px),
        },
    ]
    placeholder_bbox_px: List[float] | None = None
    max_distance_units = 0
    for index, (side, distance_units, value, missing, relevant) in enumerate(placements, start=1):
        sign = -1.0 if str(side) == "left" else 1.0
        center_x = float(beam_center_x + (sign * float(distance_units) * slot_spacing))
        box_width = float(render_defaults["weight_box_width_px"])
        box_height = float(render_defaults["weight_box_height_px"])
        box_left = float(center_x - (0.5 * box_width))
        box_top = float(beam_bbox_px[1] - float(render_defaults["weight_box_gap_px"]) - box_height)
        box_bbox = [
            round(float(box_left), 3),
            round(float(box_top), 3),
            round(float(box_left + box_width), 3),
            round(float(box_top + box_height), 3),
        ]
        fill_rgb = (
            tuple(int(channel) for channel in lever_theme.weight_fill_rgb)
            if not missing
            else (255, 238, 240)
        )
        outline_rgb = (
            tuple(int(channel) for channel in lever_theme.weight_outline_rgb)
            if not missing
            else (192, 62, 84)
        )
        draw_rounded_rect(
            draw,
            tuple(float(value_px) for value_px in box_bbox),
            radius=10,
            fill=fill_rgb,
            outline=outline_rgb,
            width=3,
        )
        label_bbox = _draw_centered_text(
            draw,
            text="?" if missing else str(int(value)),
            center_xy=(float(center_x), float(box_top + (0.5 * box_height))),
            font=weight_font,
            fill=(196, 56, 79) if missing else tuple(int(channel) for channel in lever_theme.weight_text_rgb),
            stroke_width_px=int(render_defaults["label_stroke_width_px"]),
        )
        weight_bbox = [
            round(float(min(box_bbox[0], label_bbox[0])), 3),
            round(float(min(box_bbox[1], label_bbox[1])), 3),
            round(float(max(box_bbox[2], label_bbox[2])), 3),
            round(float(max(box_bbox[3], label_bbox[3])), 3),
        ]
        weight_id = "missing_weight_marker" if missing else f"lever_weight_{int(index)}"
        spec = _WeightPlacement(
            weight_id=str(weight_id),
            side=str(side),
            distance_units=int(distance_units),
            value=int(value) if value is not None else None,
            missing=bool(missing),
            relevant=bool(relevant),
            bbox_px=list(weight_bbox),
        )
        weight_specs.append(spec)
        scene_entities.append(
            {
                "entity_id": str(weight_id),
                "entity_type": "physics_missing_weight_marker" if missing else "physics_lever_weight",
                "bbox_px": list(weight_bbox),
                "meta": {
                    "side": str(side),
                    "distance_units": int(distance_units),
                    "value": int(value) if value is not None else None,
                    "missing": bool(missing),
                    "relevant_to_query": bool(relevant),
                },
            }
        )
        max_distance_units = max(int(max_distance_units), int(distance_units))
        if bool(relevant):
            relevant_weight_bboxes.append(list(weight_bbox))
            relevant_weight_ids.append(str(weight_id))
        if bool(missing):
            placeholder_bbox_px = list(weight_bbox)

    if _is_missing_weight_query(str(query_variant)) and placeholder_bbox_px is not None:
        evidence_bboxes = [list(placeholder_bbox_px)]
        evidence_entity_ids = ["missing_weight_marker"]
    else:
        evidence_bboxes = [list(bbox) for bbox in relevant_weight_bboxes]
        evidence_entity_ids = [str(item) for item in relevant_weight_ids]

    render_map = {
        "accent_color_name": str(accent_color_name),
        "beam_bbox_px": list(beam_bbox_px),
        "fulcrum_bbox_px": list(fulcrum_bbox_px),
        "weight_bboxes_px": {spec.weight_id: list(spec.bbox_px) for spec in weight_specs},
        "relevant_weight_ids": list(relevant_weight_ids),
        "evidence_entity_ids": list(evidence_entity_ids),
        "beam_center_px": [round(float(beam_center_x), 3), round(float(beam_center_y), 3)],
        "max_distance_units": int(max_distance_units),
    }
    if placeholder_bbox_px is not None:
        render_map["missing_weight_marker_bbox_px"] = list(placeholder_bbox_px)

    return _RenderedScene(
        image=canvas,
        beam_bbox_px=list(beam_bbox_px),
        fulcrum_bbox_px=list(fulcrum_bbox_px),
        weight_specs=list(weight_specs),
        placeholder_bbox_px=list(placeholder_bbox_px) if placeholder_bbox_px is not None else None,
        relevant_weight_bboxes=list(relevant_weight_bboxes),
        relevant_weight_ids=list(relevant_weight_ids),
        evidence_bboxes=list(evidence_bboxes),
        evidence_entity_ids=list(evidence_entity_ids),
        render_map=render_map,
        scene_entities=list(scene_entities),
        max_distance_units=int(max_distance_units),
    )


@register_task
class PhysicsMechanicsLeverBalanceTask:
    """Return one simple lever-balance mechanics question."""

    task_id = TASK_ID
    domain = "physics"
    task_group = "mechanics"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        rendered_scene: _RenderedScene | None = None
        layout_metadata: Dict[str, Any] | None = None

        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                placements, layout_metadata = _sample_weight_layout(
                    attempt_rng,
                    query_variant=str(axes.query_variant),
                    target_answer=int(axes.target_answer),
                    params=params,
                )
            except ValueError:
                continue

            background, background_meta = make_background_canvas(
                canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
                canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
                instance_seed=int(instance_seed),
                params=params,
                default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
            )
            rendered_scene = _render_scene(
                scene_variant=str(axes.scene_variant),
                query_variant=str(axes.query_variant),
                accent_color_name=str(axes.accent_color_name),
                placements=list(placements),
                render_defaults={
                    key: params.get(key, group_default(_RENDER_DEFAULTS, key, getattr(_DEFAULTS, key)))
                    for key in (
                        "canvas_width",
                        "canvas_height",
                        "beam_width_px",
                        "beam_height_px",
                        "beam_corner_radius_px",
                        "beam_center_y_px",
                        "fulcrum_width_px",
                        "fulcrum_height_px",
                        "fulcrum_offset_px",
                        "slot_spacing_px",
                        "distance_support",
                        "weight_box_width_px",
                        "weight_box_height_px",
                        "weight_box_gap_px",
                        "weight_font_size_px",
                        "distance_font_size_px",
                        "label_stroke_width_px",
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
                    "evidence_hint_torque",
                    "evidence_hint_missing_weight",
                    "object_description_center_fulcrum",
                    "object_description_offset_fulcrum",
                    "object_description_textured_beam",
                ),
                context=f"prompt defaults for {self.task_id}",
            )
            json_example, json_example_answer_only = build_prompt_json_examples(
                evidence_value=list(rendered_scene.evidence_bboxes[:2] if rendered_scene.evidence_bboxes else [[220, 140, 280, 194]]),
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
                    "json_output_contract": str(prompt_defaults["json_output_contract"]),
                    "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                    "evidence_hint": str(
                        prompt_defaults["evidence_hint_missing_weight"]
                        if _is_missing_weight_query(str(axes.query_variant))
                        else prompt_defaults["evidence_hint_torque"]
                    ),
                    "answer_hint": str(prompt_defaults["answer_hint"]),
                    "json_example": str(json_example),
                    "json_example_answer_only": str(json_example_answer_only),
                },
                instance_seed=int(instance_seed),
            )
            prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

            answer_gt = TypedValue(type="integer", value=int(axes.target_answer))
            evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in rendered_scene.evidence_bboxes])
            complexity = build_physics_lever_balance_complexity(
                task_group_defaults=_TASK_GROUP_DEFAULTS,
                task_id=self.task_id,
                scene_variant=str(axes.scene_variant),
                query_variant=str(axes.query_variant),
                weight_count=len(rendered_scene.weight_specs),
                relevant_weight_count=len(rendered_scene.relevant_weight_ids),
                max_distance=int(rendered_scene.max_distance_units),
                target_answer=int(axes.target_answer),
            )
            target_support_key = "missing_weight_support" if _is_missing_weight_query(str(axes.query_variant)) else "torque_answer_support"
            trace_payload = {
                "scene_ir": {
                    "scene_kind": f"physics_lever_balance_{str(axes.scene_variant)}",
                    "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                    "relations": {
                        "scene_variant": str(axes.scene_variant),
                        "query_variant": str(axes.query_variant),
                        "task_variant": str(axes.query_variant),
                        "accent_color_name": str(axes.accent_color_name),
                        "target_answer": int(axes.target_answer),
                        "relevant_weight_ids": list(rendered_scene.relevant_weight_ids),
                        "evidence_entity_ids": list(rendered_scene.evidence_entity_ids),
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
                        "accent_color_name": str(axes.accent_color_name),
                        "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                        "query_variant_probabilities": dict(axes.query_variant_probabilities),
                        "task_variant_probabilities": dict(axes.query_variant_probabilities),
                        "accent_color_name_probabilities": dict(axes.accent_color_name_probabilities),
                        "target_answer": int(axes.target_answer),
                        "target_answer_probabilities": dict(axes.target_answer_probabilities),
                    },
                },
                "render_spec": {
                    "scene_variant": str(axes.scene_variant),
                    "canvas_width": int(image.size[0]),
                    "canvas_height": int(image.size[1]),
                    "accent_color_name": str(axes.accent_color_name),
                },
                "render_map": dict(rendered_scene.render_map),
                "execution_trace": {
                    "scene_variant": str(axes.scene_variant),
                    "query_variant": str(axes.query_variant),
                    "task_variant": str(axes.query_variant),
                    "accent_color_name": str(axes.accent_color_name),
                    "target_answer": int(axes.target_answer),
                    "target_answer_support": list(
                        resolve_integer_support(
                            params,
                            gen_defaults=_GEN_DEFAULTS,
                            key=str(target_support_key),
                            fallback=_DEFAULTS.missing_weight_support if _is_missing_weight_query(str(axes.query_variant)) else _DEFAULTS.torque_answer_support,
                        )
                    ),
                    "query_side": None if layout_metadata is None else layout_metadata.get("query_side"),
                    "placeholder_side": None if layout_metadata is None else layout_metadata.get("placeholder_side"),
                    "placeholder_distance_units": None if layout_metadata is None else layout_metadata.get("placeholder_distance_units"),
                    "known_torque_left": 0 if layout_metadata is None else int(layout_metadata["known_torque_left"]),
                    "known_torque_right": 0 if layout_metadata is None else int(layout_metadata["known_torque_right"]),
                    "weight_specs": [
                        {
                            "weight_id": str(spec.weight_id),
                            "side": str(spec.side),
                            "distance_units": int(spec.distance_units),
                            "value": None if spec.value is None else int(spec.value),
                            "missing": bool(spec.missing),
                            "relevant_to_query": bool(spec.relevant),
                        }
                        for spec in rendered_scene.weight_specs
                    ],
                    "relevant_weight_ids": list(rendered_scene.relevant_weight_ids),
                    "evidence_entity_ids": list(rendered_scene.evidence_entity_ids),
                },
                "witness_symbolic": {
                    "type": "id_set",
                    "ids": [str(item) for item in rendered_scene.evidence_entity_ids],
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


__all__ = ["PhysicsMechanicsLeverBalanceTask"]
