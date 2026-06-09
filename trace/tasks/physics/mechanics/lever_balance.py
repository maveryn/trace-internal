"""Physics mechanics task for simple lever-balance diagrams."""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import combinations
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.drawing import draw_centered_text_with_auto_stroke as _draw_centered_text
from ...shared.drawing import draw_rounded_rect
from ...shared.font_assets import font_asset_version, get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import build_prompt_json_examples
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.render_variation import resolve_layout_jitter, resolve_render_int
from ...shared.text_rendering import load_font
from ...shared.variant_sampling import (
    apply_balanced_variant_sampling,
    resolve_compatible_scene_query_ids,
    resolve_variant,
)
from ..shared.complexity import build_physics_lever_balance_complexity
from ..shared.diagram_style import prepare_physics_diagram_style_and_background
from ..shared.fixed_query_task import FixedPhysicsQueryVariantTaskMixin
from ..shared.style import SUPPORTED_PHYSICS_COLOR_NAMES, build_physics_lever_theme
from ..shared.support_sampling import resolve_integer_choice, resolve_integer_support
from ..shared.visual_defaults import load_physics_noise_defaults


TASK_ID = "physics_mechanics_lever_balance_family"
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "center_fulcrum",
    "offset_fulcrum",
    "textured_beam",
)
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "left_torque",
    "right_torque",
    "missing_weight_to_balance",
)
SUPPORTED_PUBLIC_QUERY_IDS: Tuple[str, ...] = (
    "side_torque",
    "missing_weight_to_balance",
)
MISSING_WEIGHT_SCENE_VARIANTS: Tuple[str, ...] = (
    "center_fulcrum",
    "textured_beam",
)
_SOURCE_TORQUE_SIDE_BY_QUERY_ID = {
    "left_torque": "left",
    "right_torque": "right",
}
_SUPPORTED_TORQUE_SIDES: Tuple[str, ...] = ("left", "right")
COMPATIBILITY: Dict[str, Sequence[str]] = {
    "center_fulcrum": SUPPORTED_QUERY_IDS,
    "offset_fulcrum": SUPPORTED_QUERY_IDS,
    "textured_beam": SUPPORTED_QUERY_IDS,
}


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for lever-balance scenes."""

    canvas_width: int = 1280
    canvas_height: int = 640
    beam_width_px: int = 1140
    beam_height_px: int = 22
    beam_corner_radius_px: int = 10
    beam_center_y_px: int = 350
    fulcrum_width_px: int = 110
    fulcrum_height_px: int = 84
    fulcrum_offset_px: int = 76
    slot_spacing_px: int = 66
    distance_support: Tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7, 8)
    weight_box_width_px: int = 58
    weight_box_height_px: int = 52
    weight_box_gap_px: int = 8
    weight_font_size_px: int = 26
    distance_font_size_px: int = 22
    label_stroke_width_px: int = 3
    texture_line_width_px: int = 2
    texture_spacing_px: int = 18
    torque_answer_support: Tuple[int, ...] = tuple(range(2, 25))
    missing_weight_support: Tuple[int, ...] = tuple(range(1, 7))
    weight_value_min: int = 1
    weight_value_max: int = 9
    max_side_weights: int = 4
    missing_weight_max_side_weights: int = 2


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved scene/query axes and answer support for one instance."""

    scene_variant: str
    query_id: str
    public_query_id: str
    torque_side: str | None
    accent_color_name: str
    target_answer: int
    scene_variant_probabilities: Dict[str, float]
    query_id_probabilities: Dict[str, float]
    torque_side_probabilities: Dict[str, float]
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
    """Rendered lever-balance scene plus prompt-facing annotation metadata."""

    image: Image.Image
    beam_bbox_px: List[float]
    fulcrum_bbox_px: List[float]
    weight_specs: List[_WeightPlacement]
    placeholder_bbox_px: List[float] | None
    relevant_weight_bboxes: List[List[float]]
    relevant_weight_ids: List[str]
    annotation_bboxes: List[List[float]]
    annotation_keyed_bbox_set_map: Dict[str, List[List[float]]]
    annotation_entity_ids: List[str]
    witness_entity_ids: List[str]
    render_map: Dict[str, Any]
    scene_entities: List[Dict[str, Any]]
    max_distance_units: int


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("physics", "mechanics")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(task_group="mechanics", apply_prob=0.5)
LEVER_SEMANTIC_COLORS: Tuple[Tuple[int, int, int], ...] = (
    (255, 238, 240),
    (192, 62, 84),
    (196, 56, 79),
)


def _is_missing_weight_query(query_id: str) -> bool:
    """Return true when the query asks for one missing balancing weight."""

    return str(query_id) == "missing_weight_to_balance"


def _with_sampling_divisor(params: Mapping[str, Any], *, divisor: int, explicit_keys: Sequence[str]) -> Mapping[str, Any]:
    """No-op hook for axis-decoupling call sites."""

    _ = int(divisor), explicit_keys
    return params


def _resolve_public_query_id(
    rng,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
    """Resolve the public query family, accepting old side-specific names as aliases."""

    explicit_query = params.get("query_id")
    if explicit_query is not None and str(explicit_query) in _SOURCE_TORQUE_SIDE_BY_QUERY_ID:
        return "side_torque", {
            key: (1.0 if key == "side_torque" else 0.0)
            for key in SUPPORTED_PUBLIC_QUERY_IDS
        }
    if explicit_query is not None and str(explicit_query) in SUPPORTED_PUBLIC_QUERY_IDS:
        selected = str(explicit_query)
        return selected, {
            key: (1.0 if key == selected else 0.0)
            for key in SUPPORTED_PUBLIC_QUERY_IDS
        }

    selected, probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_PUBLIC_QUERY_IDS,
        explicit_key="query_id",
        weights_key="query_id_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=SUPPORTED_PUBLIC_QUERY_IDS,
        balance_flag_key="balanced_query_id_sampling",
        explicit_key="query_id",
        weights_key="query_id_weights",
        sampling_namespace=f"{TASK_ID}.query_id",
    )
    return str(selected), {str(key): float(value) for key, value in sorted(probabilities.items())}


def _resolve_torque_side(
    rng,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
    """Resolve the side for a side-torque query."""

    explicit_query = params.get("query_id")
    if explicit_query is not None and str(explicit_query) in _SOURCE_TORQUE_SIDE_BY_QUERY_ID:
        selected = str(_SOURCE_TORQUE_SIDE_BY_QUERY_ID[str(explicit_query)])
        return selected, {key: (1.0 if key == selected else 0.0) for key in _SUPPORTED_TORQUE_SIDES}

    explicit_side = params.get("torque_side", params.get("query_side"))
    if explicit_side is not None:
        selected = str(explicit_side).strip().lower()
        if selected not in _SUPPORTED_TORQUE_SIDES:
            raise ValueError(f"unsupported torque_side: {explicit_side}")
        return selected, {key: (1.0 if key == selected else 0.0) for key in _SUPPORTED_TORQUE_SIDES}

    side_params = _with_sampling_divisor(
        params,
        divisor=len(SUPPORTED_PUBLIC_QUERY_IDS),
        explicit_keys=("torque_side", "query_side"),
    )
    selected, probabilities = resolve_variant(
        rng,
        params=side_params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=_SUPPORTED_TORQUE_SIDES,
        explicit_key="torque_side",
        weights_key="torque_side_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=side_params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=_SUPPORTED_TORQUE_SIDES,
        balance_flag_key="balanced_torque_side_sampling",
        explicit_key="torque_side",
        weights_key="torque_side_weights",
        sampling_namespace=f"{TASK_ID}.torque_side",
    )
    return str(selected), {str(key): float(value) for key, value in sorted(probabilities.items())}


def _resolve_target_answer(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    query_id: str,
) -> Tuple[int, Dict[str, float]]:
    """Resolve the sampled answer support for one lever-balance query."""

    target_params = dict(params)
    return resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=target_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="missing_weight_support" if _is_missing_weight_query(str(query_id)) else "torque_answer_support",
        explicit_key="target_answer",
        fallback_support=_DEFAULTS.missing_weight_support if _is_missing_weight_query(str(query_id)) else _DEFAULTS.torque_answer_support,
        namespace=f"{TASK_ID}.target_answer.{str(query_id)}",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_support_permutation=True,
    )


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve one compatible scene/query pair plus answer support."""

    axis_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.axes")
    public_query_id, query_probs = _resolve_public_query_id(
        axis_rng,
        instance_seed=int(instance_seed),
        params=params,
    )
    torque_side: str | None = None
    torque_side_probabilities: Dict[str, float] = {}
    if str(public_query_id) == "side_torque":
        torque_side, torque_side_probabilities = _resolve_torque_side(
            axis_rng,
            instance_seed=int(instance_seed),
            params=params,
        )
        query_id = f"{str(torque_side)}_torque"
    else:
        query_id = str(public_query_id)

    if _is_missing_weight_query(str(query_id)) and params.get("scene_variant") is None:
        scene_supported_variants = MISSING_WEIGHT_SCENE_VARIANTS
        scene_weights_key = "missing_weight_scene_variant_weights"
    else:
        scene_supported_variants = SUPPORTED_SCENE_VARIANTS
        scene_weights_key = "scene_variant_weights"
    scene_params = _with_sampling_divisor(
        params,
        divisor=len(SUPPORTED_QUERY_IDS),
        explicit_keys=("scene_variant",),
    )
    scene_variant, scene_probs = resolve_variant(
        axis_rng,
        params=scene_params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=scene_supported_variants,
        explicit_key="scene_variant",
        weights_key=scene_weights_key,
    )
    scene_variant = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=scene_params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(scene_variant),
        variant_probabilities=scene_probs,
        supported_variants=scene_supported_variants,
        balance_flag_key="balanced_scene_variant_sampling",
        explicit_key="scene_variant",
        weights_key=scene_weights_key,
        sampling_namespace=f"{TASK_ID}.scene_variant",
    )
    target_answer, target_answer_probabilities = _resolve_target_answer(
        instance_seed=int(instance_seed),
        params=params,
        query_id=str(query_id),
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
        query_id=str(query_id),
        public_query_id=str(public_query_id),
        torque_side=(str(torque_side) if torque_side is not None else None),
        accent_color_name=str(accent_color_name),
        target_answer=int(target_answer),
        scene_variant_probabilities=dict(scene_probs),
        query_id_probabilities=dict(query_probs),
        torque_side_probabilities=dict(torque_side_probabilities),
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
    max_count = min(int(max_weights), len(distances))

    def _search(
        *,
        distance_combo: Tuple[int, ...],
        combo_index: int,
        remaining_torque: int,
        prefix: List[Tuple[int, int]],
    ) -> None:
        distance = int(distance_combo[int(combo_index)])
        remaining_slots = int(len(distance_combo) - combo_index - 1)
        if int(remaining_slots) == 0:
            if int(remaining_torque) % int(distance) != 0:
                return
            weight = int(remaining_torque) // int(distance)
            if int(weight_min) <= int(weight) <= int(weight_max):
                candidates.append(list(prefix) + [(int(distance), int(weight))])
            return

        tail_distances = [int(value) for value in distance_combo[int(combo_index) + 1 :]]
        min_tail_torque = sum(int(value) * int(weight_min) for value in tail_distances)
        max_tail_torque = sum(int(value) * int(weight_max) for value in tail_distances)
        for weight in range(int(weight_min), int(weight_max) + 1):
            next_remaining = int(remaining_torque) - (int(distance) * int(weight))
            if int(next_remaining) < int(min_tail_torque) or int(next_remaining) > int(max_tail_torque):
                continue
            _search(
                distance_combo=distance_combo,
                combo_index=int(combo_index) + 1,
                remaining_torque=int(next_remaining),
                prefix=list(prefix) + [(int(distance), int(weight))],
            )

    for count in range(1, int(max_count) + 1):
        for distance_combo in combinations(distances, int(count)):
            min_possible = sum(int(distance) * int(weight_min) for distance in distance_combo)
            max_possible = sum(int(distance) * int(weight_max) for distance in distance_combo)
            if int(target_torque) < int(min_possible) or int(target_torque) > int(max_possible):
                continue
            _search(
                distance_combo=tuple(int(value) for value in distance_combo),
                combo_index=0,
                remaining_torque=int(target_torque),
                prefix=[],
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
    max_side_weights: int,
) -> List[Tuple[int, int]]:
    """Sample extra shown weights on the placeholder side."""

    remaining_distances = [int(value) for value in distance_support if int(value) != int(placeholder_distance)]
    max_extra_weights = min(max(0, int(max_side_weights) - 1), len(remaining_distances))
    if not remaining_distances or int(max_extra_weights) <= 0:
        return []
    count = int(rng.randint(0, int(max_extra_weights)))
    if int(count) <= 0:
        return []
    chosen_distances = sorted(rng.sample(remaining_distances, int(count)))
    return [
        (int(distance), int(rng.randint(int(weight_min), int(weight_max))))
        for distance in chosen_distances
    ]


def _sample_weight_layout(
    rng,
    *,
    query_id: str,
    target_answer: int,
    params: Mapping[str, Any],
) -> Tuple[List[Tuple[str, int, int | None, bool, bool]], Dict[str, Any]]:
    """Sample one full lever layout satisfying the requested answer."""

    distance_support = _distance_support(params)
    weight_min = int(params.get("weight_value_min", group_default(_GEN_DEFAULTS, "weight_value_min", _DEFAULTS.weight_value_min)))
    weight_max = int(params.get("weight_value_max", group_default(_GEN_DEFAULTS, "weight_value_max", _DEFAULTS.weight_value_max)))
    max_weights_key = "missing_weight_max_side_weights" if _is_missing_weight_query(str(query_id)) else "max_side_weights"
    max_weights = int(
        params.get(
            max_weights_key,
            group_default(
                _GEN_DEFAULTS,
                max_weights_key,
                group_default(_GEN_DEFAULTS, "max_side_weights", _DEFAULTS.missing_weight_max_side_weights if _is_missing_weight_query(str(query_id)) else _DEFAULTS.max_side_weights),
            ),
        )
    )

    if str(query_id) in {"left_torque", "right_torque"}:
        relevant_side = "left" if str(query_id) == "left_torque" else "right"
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
            max_side_weights=int(max_weights),
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


def _lever_content_bbox(
    *,
    render_defaults: Mapping[str, Any],
    scene_variant: str,
    placements: Sequence[Tuple[str, int, int | None, bool, bool]],
) -> List[float]:
    """Return a conservative bbox for the whole lever diagram before placement offset."""

    canvas_width = int(render_defaults["canvas_width"])
    scene_rng = spawn_rng(int(render_defaults.get("instance_seed", 0)), f"{TASK_ID}.scene_layout.{str(scene_variant)}")
    beam_center_x = _beam_center_x(scene_rng, scene_variant=str(scene_variant), canvas_width=int(canvas_width))
    beam_center_y = float(render_defaults["beam_center_y_px"])
    beam_width = float(render_defaults["beam_width_px"])
    beam_height = float(render_defaults["beam_height_px"])
    beam_bbox_px = [
        float(beam_center_x - (0.5 * beam_width)),
        float(beam_center_y - (0.5 * beam_height)),
        float(beam_center_x + (0.5 * beam_width)),
        float(beam_center_y + (0.5 * beam_height)),
    ]
    fulcrum_width = float(render_defaults["fulcrum_width_px"])
    fulcrum_height = float(render_defaults["fulcrum_height_px"])
    fulcrum_bbox_px = [
        float(beam_center_x - (0.5 * fulcrum_width)),
        float(beam_bbox_px[3]),
        float(beam_center_x + (0.5 * fulcrum_width)),
        float(beam_bbox_px[3] + fulcrum_height),
    ]
    left = min(float(beam_bbox_px[0]), float(fulcrum_bbox_px[0]))
    top = min(float(beam_bbox_px[1] - 36.0), float(fulcrum_bbox_px[1]))
    right = max(float(beam_bbox_px[2]), float(fulcrum_bbox_px[2]))
    bottom = max(float(beam_bbox_px[3] + 50.0), float(fulcrum_bbox_px[3]))
    slot_spacing = float(render_defaults["slot_spacing_px"])
    box_width = float(render_defaults["weight_box_width_px"])
    box_height = float(render_defaults["weight_box_height_px"])
    for side, distance_units, _value, _missing, _relevant in placements:
        sign = -1.0 if str(side) == "left" else 1.0
        center_x = float(beam_center_x + (sign * float(distance_units) * slot_spacing))
        box_left = float(center_x - (0.5 * box_width) - 8.0)
        box_top = float(beam_bbox_px[1] - float(render_defaults["weight_box_gap_px"]) - box_height - 8.0)
        box_right = float(center_x + (0.5 * box_width) + 8.0)
        box_bottom = float(beam_bbox_px[1] - float(render_defaults["weight_box_gap_px"]) + 8.0)
        left = min(left, box_left)
        top = min(top, box_top)
        right = max(right, box_right)
        bottom = max(bottom, box_bottom)
    return [round(float(left), 3), round(float(top), 3), round(float(right), 3), round(float(bottom), 3)]


def _resolve_lever_layout_placement(
    *,
    render_defaults: Mapping[str, Any],
    params: Mapping[str, Any],
    instance_seed: int,
    scene_variant: str,
    placements: Sequence[Tuple[str, int, int | None, bool, bool]],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Resolve whole-diagram placement before rendering and annotation projection."""

    canvas_width = int(render_defaults["canvas_width"])
    canvas_height = int(render_defaults["canvas_height"])
    content_bbox = _lever_content_bbox(
        render_defaults=render_defaults,
        scene_variant=str(scene_variant),
        placements=placements,
    )
    content_left, content_top, content_right, content_bottom = [float(value) for value in content_bbox]
    jitter = resolve_layout_jitter(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.lever_layout",
    )
    min_margin = int(jitter.get("min_margin_px", 18))
    requested_dx = int(jitter.get("requested_dx_px", 0))
    requested_dy = int(jitter.get("requested_dy_px", 0))
    min_dx = int(math.ceil(float(min_margin) - float(content_left)))
    max_dx = int(math.floor(float(canvas_width) - float(min_margin) - float(content_right)))
    min_dy = int(math.ceil(float(min_margin) - float(content_top)))
    max_dy = int(math.floor(float(canvas_height) - float(min_margin) - float(content_bottom)))
    if int(min_dx) > int(max_dx):
        min_dx = 0
        max_dx = 0
    if int(min_dy) > int(max_dy):
        min_dy = 0
        max_dy = 0
    if not bool(jitter.get("enabled", False)):
        requested_dx = 0
        requested_dy = 0
    dx = max(int(min_dx), min(int(max_dx), int(requested_dx)))
    dy = max(int(min_dy), min(int(max_dy), int(requested_dy)))

    adjusted = dict(render_defaults)
    adjusted["layout_offset_x_px"] = int(dx)
    adjusted["layout_offset_y_px"] = int(dy)

    content_width = round(float(content_right) - float(content_left), 3)
    content_height = round(float(content_bottom) - float(content_top), 3)
    final_bbox = [
        round(float(content_left) + float(dx), 3),
        round(float(content_top) + float(dy), 3),
        round(float(content_right) + float(dx), 3),
        round(float(content_bottom) + float(dy), 3),
    ]
    placement = dict(jitter)
    placement.update(
        {
            "mode": "whole_lever_diagram_offset",
            "content_bbox_px": list(content_bbox),
            "content_size_px": [float(content_width), float(content_height)],
            "final_content_bbox_px": list(final_bbox),
            "canvas_size_px": [int(canvas_width), int(canvas_height)],
            "free_space_px": [
                round(float(canvas_width) - float(content_width), 3),
                round(float(canvas_height) - float(content_height), 3),
            ],
            "available_offset_x_px": [int(min_dx), int(max_dx)],
            "available_offset_y_px": [int(min_dy), int(max_dy)],
            "sampled_offset_px": [int(requested_dx), int(requested_dy)],
            "final_offset_px": [int(dx), int(dy)],
            "default_origin_px": [round(float(content_left), 3), round(float(content_top), 3)],
            "final_origin_px": [round(float(content_left) + float(dx), 3), round(float(content_top) + float(dy), 3)],
            "dx_px": int(dx),
            "dy_px": int(dy),
        }
    )
    return adjusted, placement


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


def _render_scene(
    *,
    scene_variant: str,
    query_id: str,
    accent_color_name: str,
    placements: Sequence[Tuple[str, int, int | None, bool, bool]],
    render_defaults: Mapping[str, Any],
    background: Image.Image,
    diagram_style: Any | None = None,
    font_family: str | None = None,
) -> _RenderedScene:
    """Render one finalized lever-balance scene."""

    canvas = background.convert("RGB")
    draw = ImageDraw.Draw(canvas)
    canvas_width = int(render_defaults["canvas_width"])
    lever_theme = build_physics_lever_theme(str(accent_color_name), diagram_style=diagram_style)
    scene_rng = spawn_rng(int(render_defaults.get("instance_seed", 0)), f"{TASK_ID}.scene_layout.{str(scene_variant)}")
    beam_center_x = _beam_center_x(scene_rng, scene_variant=str(scene_variant), canvas_width=int(canvas_width)) + float(
        render_defaults.get("layout_offset_x_px", 0)
    )
    beam_center_y = float(render_defaults["beam_center_y_px"]) + float(render_defaults.get("layout_offset_y_px", 0))
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
    resolved_font_family = None if font_family is None else str(font_family)
    distance_font = load_font(int(render_defaults["distance_font_size_px"]), bold=True, font_family=resolved_font_family)
    weight_font = load_font(int(render_defaults["weight_font_size_px"]), bold=True, font_family=resolved_font_family)
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

    annotation_bboxes = [list(bbox) for bbox in relevant_weight_bboxes]
    annotation_keyed_bbox_set_map = {
        "known_weights": [list(spec.bbox_px) for spec in weight_specs if bool(spec.relevant) and not bool(spec.missing)],
        "target_weight": [list(spec.bbox_px) for spec in weight_specs if bool(spec.relevant) and bool(spec.missing)],
    }
    witness_entity_ids = [str(item) for item in relevant_weight_ids]
    annotation_entity_ids = (
        list(annotation_keyed_bbox_set_map.keys())
        if _is_missing_weight_query(str(query_id))
        else list(witness_entity_ids)
    )

    render_map = {
        "accent_color_name": str(accent_color_name),
        "technical_diagram_frame_mode": str(getattr(diagram_style, "frame_mode", "none")),
        "beam_bbox_px": list(beam_bbox_px),
        "fulcrum_bbox_px": list(fulcrum_bbox_px),
        "weight_bboxes_px": {spec.weight_id: list(spec.bbox_px) for spec in weight_specs},
        "relevant_weight_ids": list(relevant_weight_ids),
        "annotation_entity_ids": list(annotation_entity_ids),
        "witness_entity_ids": list(witness_entity_ids),
        "annotation_keyed_bbox_set_map_px": dict(annotation_keyed_bbox_set_map),
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
        annotation_bboxes=list(annotation_bboxes),
        annotation_keyed_bbox_set_map=dict(annotation_keyed_bbox_set_map),
        annotation_entity_ids=list(annotation_entity_ids),
        witness_entity_ids=list(witness_entity_ids),
        render_map=render_map,
        scene_entities=list(scene_entities),
        max_distance_units=int(max_distance_units),
    )


class _PhysicsMechanicsLeverBalanceBaseTask:
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
                    query_id=str(axes.query_id),
                    target_answer=int(axes.target_answer),
                    params=params,
                )
            except ValueError:
                continue

            canvas_width = int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width)))
            canvas_height = int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height)))
            background, background_meta, diagram_style, diagram_style_meta = prepare_physics_diagram_style_and_background(
                scene_id="lever",
                task_group=self.task_group,
                canvas_width=int(canvas_width),
                canvas_height=int(canvas_height),
                instance_seed=int(instance_seed),
                params=params,
                protected_colors=LEVER_SEMANTIC_COLORS,
            )
            font_family = sample_font_family(
                role="readout",
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.render.font_family",
                params=params,
            )
            font_record = get_font_family_record(str(font_family))
            render_defaults = {
                key: (
                    params.get(key, group_default(_RENDER_DEFAULTS, key, getattr(_DEFAULTS, key)))
                    if key == "distance_support"
                    else resolve_render_int(
                        params,
                        _RENDER_DEFAULTS,
                        key,
                        int(getattr(_DEFAULTS, key)),
                        instance_seed=int(instance_seed),
                        namespace=TASK_ID,
                    )
                )
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
            } | {"instance_seed": int(instance_seed)}
            render_defaults, layout_placement_meta = _resolve_lever_layout_placement(
                render_defaults=render_defaults,
                params=params,
                instance_seed=int(instance_seed),
                scene_variant=str(axes.scene_variant),
                placements=list(placements),
            )
            rendered_scene = _render_scene(
                scene_variant=str(axes.scene_variant),
                query_id=str(axes.query_id),
                accent_color_name=str(axes.accent_color_name),
                placements=list(placements),
                render_defaults=render_defaults,
                background=background,
                diagram_style=diagram_style,
                font_family=str(font_family),
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
                    "scene_key",
                    "task_key",
                    "json_output_contract",
                    "json_output_contract_answer_only",
                    "answer_hint",
                    "annotation_hint_torque",
                    "annotation_hint_missing_weight",
                    "object_description_center_fulcrum",
                    "object_description_offset_fulcrum",
                    "object_description_textured_beam",
                ),
                context=f"prompt defaults for {self.task_id}",
            )
            is_missing_weight_query = _is_missing_weight_query(str(axes.query_id))
            annotation_value = (
                dict(rendered_scene.annotation_keyed_bbox_set_map)
                if is_missing_weight_query
                else list(rendered_scene.annotation_bboxes)
            )
            json_example, json_example_answer_only = build_prompt_json_examples(
                annotation_value=annotation_value or [[220, 140, 280, 194]],
                answer_type="integer",
            )
            prompt_selection = render_task_prompt_variants(
                domain=self.domain,
                task_group=self.task_group,
                bundle_id=str(prompt_defaults["bundle_id"]),
                scene_key=str(prompt_defaults["scene_key"]),
                task_key=str(prompt_defaults["task_key"]),
                query_key=str(axes.public_query_id),
                answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
                slots={
                    "object_description": str(prompt_defaults[f"object_description_{str(axes.scene_variant)}"]),
                    "torque_side": str(axes.torque_side or ""),
                    "json_output_contract": str(prompt_defaults["json_output_contract"]),
                    "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                    "annotation_hint": str(
                        prompt_defaults["annotation_hint_missing_weight"]
                        if is_missing_weight_query
                        else prompt_defaults["annotation_hint_torque"]
                    ),
                    "answer_hint": str(prompt_defaults["answer_hint"]),
                    "json_example": str(json_example),
                    "json_example_answer_only": str(json_example_answer_only),
                },
                instance_seed=int(instance_seed),
            )
            prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

            answer_gt = TypedValue(type="integer", value=int(axes.target_answer))
            annotation_gt = (
                TypedValue(type="keyed_bbox_set_map", value=dict(rendered_scene.annotation_keyed_bbox_set_map))
                if is_missing_weight_query
                else TypedValue(type="bbox_set", value=[list(bbox) for bbox in rendered_scene.annotation_bboxes])
            )
            complexity = build_physics_lever_balance_complexity(
                task_group_defaults=_TASK_GROUP_DEFAULTS,
                task_id=TASK_ID,
                scene_variant=str(axes.scene_variant),
                query_id=str(axes.query_id),
                weight_count=len(rendered_scene.weight_specs),
                relevant_weight_count=len(rendered_scene.relevant_weight_ids),
                max_distance=int(rendered_scene.max_distance_units),
                target_answer=int(axes.target_answer),
            )
            target_support_key = "missing_weight_support" if _is_missing_weight_query(str(axes.query_id)) else "torque_answer_support"
            trace_payload = {
                "scene_ir": {
                    "scene_kind": f"physics_lever_balance_{str(axes.scene_variant)}",
                    "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                    "relations": {
                        "scene_variant": str(axes.scene_variant),
                        "query_id": str(axes.public_query_id),
                        "internal_query_id": str(axes.query_id),
                        "torque_side": axes.torque_side,
                        "accent_color_name": str(axes.accent_color_name),
                        "target_answer": int(axes.target_answer),
                        "relevant_weight_ids": list(rendered_scene.relevant_weight_ids),
                        "annotation_entity_ids": list(rendered_scene.annotation_entity_ids),
                        "witness_entity_ids": list(rendered_scene.witness_entity_ids),
                    },
                },
                "query_spec": {
                    "query_id": str(axes.public_query_id),
                    "template_id": str(prompt_defaults["bundle_id"]),
                    "prompt_variant": dict(prompt_artifacts.prompt_variant),
                    "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                    "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                    "params": {
                        "scene_variant": str(axes.scene_variant),
                        "query_id": str(axes.public_query_id),
                        "internal_query_id": str(axes.query_id),
                        "torque_side": axes.torque_side,
                        "accent_color_name": str(axes.accent_color_name),
                        "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                        "query_id_probabilities": dict(axes.query_id_probabilities),
                        "torque_side_probabilities": dict(axes.torque_side_probabilities),
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
                    "font": {
                        "font_family": str(font_family),
                        "font_asset_version": font_asset_version(),
                        "font_asset": font_record.to_trace(),
                        "scope": "lever_balance_diagram",
                        "selection_policy": {
                            "pool": "global_approved_font_pool",
                            "include_tags": [],
                            "exclude_tags": [],
                            "exclusion_reason": "",
                        },
                    },
                    "technical_diagram_style": dict(diagram_style_meta),
                    "background_style": background_meta,
                    "layout_placement": dict(layout_placement_meta),
                    "post_image_noise": post_noise_meta,
                },
                "render_map": dict(rendered_scene.render_map),
                "execution_trace": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.public_query_id),
                    "internal_query_id": str(axes.query_id),
                    "torque_side": axes.torque_side,
                    "accent_color_name": str(axes.accent_color_name),
                    "target_answer": int(axes.target_answer),
                    "target_answer_support": list(
                        resolve_integer_support(
                            params,
                            gen_defaults=_GEN_DEFAULTS,
                            key=str(target_support_key),
                            fallback=_DEFAULTS.missing_weight_support if _is_missing_weight_query(str(axes.query_id)) else _DEFAULTS.torque_answer_support,
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
                    "annotation_entity_ids": list(rendered_scene.annotation_entity_ids),
                    "witness_entity_ids": list(rendered_scene.witness_entity_ids),
                },
                "witness_symbolic": {
                    "type": "object_set",
                    "ids": [str(item) for item in rendered_scene.witness_entity_ids],
                },
                "projected_annotation": {
                    "type": "keyed_bbox_set_map" if is_missing_weight_query else "bbox_set",
                    "bbox_set": [list(bbox) for bbox in rendered_scene.annotation_bboxes],
                    "keyed_bbox_set_map": dict(rendered_scene.annotation_keyed_bbox_set_map),
                    "pixel_keyed_bbox_set_map": dict(rendered_scene.annotation_keyed_bbox_set_map),
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
                query_id=str(axes.public_query_id),
                scene_id="lever",
            )

        raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts")


@register_task
class PhysicsMechanicsSideTorqueValueTask(
    FixedPhysicsQueryVariantTaskMixin,
    _PhysicsMechanicsLeverBalanceBaseTask,
):
    """Return the total torque on a queried side of a lever."""

    task_id = "task_physics__lever__side_torque_value"
    fixed_query_id = "side_torque"


@register_task
class PhysicsMechanicsMissingWeightBalanceValueTask(
    FixedPhysicsQueryVariantTaskMixin,
    _PhysicsMechanicsLeverBalanceBaseTask,
):
    """Return the missing weight needed to balance a lever."""

    task_id = "task_physics__lever__missing_weight_balance_value"
    fixed_query_id = "missing_weight_to_balance"


__all__ = [
    "PhysicsMechanicsMissingWeightBalanceValueTask",
    "PhysicsMechanicsSideTorqueValueTask",
]
