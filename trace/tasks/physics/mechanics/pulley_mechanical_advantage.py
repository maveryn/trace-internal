"""Physics mechanics task for ideal pulley mechanical-advantage diagrams."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.bbox_projection import bbox_union_many as _bbox_union
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.drawing import draw_arrow, draw_centered_text, draw_rounded_rect
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import build_prompt_json_examples
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.render_variation import resolve_render_int
from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from ...shared.variant_sampling import (
    apply_balanced_variant_sampling,
    resolve_compatible_scene_query_ids,
    resolve_variant,
)
from ..shared.complexity import build_physics_pulley_mechanical_advantage_complexity
from ..shared.diagram_style import prepare_physics_diagram_style_and_background
from ..shared.fixed_query_task import rewrite_physics_query_output
from ..shared.style import SUPPORTED_PHYSICS_COLOR_NAMES, build_physics_pulley_theme
from ..shared.support_sampling import resolve_integer_choice, resolve_integer_support
from ..shared.visual_defaults import load_physics_noise_defaults


TASK_ID = "task_physics__pulley__pulley_mechanical_advantage"
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "open_block",
    "compact_block",
    "tall_block",
)
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "effort_force_for_load",
    "load_force_from_effort",
)
SUPPORTED_PUBLIC_QUERY_IDS: Tuple[str, ...] = ("force_relation",)
_SOLVE_FOR_BY_QUERY_ID = {
    "effort_force_for_load": "effort_force",
    "load_force_from_effort": "load_force",
}
_QUERY_ID_BY_SOLVE_FOR = {
    "effort_force": "effort_force_for_load",
    "load_force": "load_force_from_effort",
}
_SUPPORTED_SOLVE_FOR_TARGETS: Tuple[str, ...] = ("effort_force", "load_force")
COMPATIBILITY: Dict[str, Sequence[str]] = {
    "open_block": SUPPORTED_QUERY_IDS,
    "compact_block": SUPPORTED_QUERY_IDS,
    "tall_block": SUPPORTED_QUERY_IDS,
}
_LOAD_FORCE_SUPPORT: Tuple[int, ...] = (
    8,
    10,
    12,
    14,
    15,
    16,
    18,
    20,
    21,
    22,
    24,
    25,
    26,
    27,
    28,
    30,
    32,
    33,
    34,
    35,
    36,
    39,
    40,
    42,
    44,
    45,
    48,
    50,
    51,
    52,
    54,
    55,
    56,
    60,
    64,
    65,
    66,
    68,
    70,
    72,
    75,
    78,
    80,
    84,
    85,
    90,
    96,
    102,
    108,
)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for pulley-system scenes."""

    canvas_width: int = 1280
    canvas_height: int = 760
    top_block_x_px: int = 250
    top_block_y_px: int = 94
    top_block_width_px: int = 780
    top_block_height_px: int = 72
    lower_block_y_px: int = 430
    compact_lower_block_y_px: int = 390
    tall_lower_block_y_px: int = 470
    lower_block_height_px: int = 72
    support_segment_gap_px: int = 48
    rope_width_px: int = 7
    pulley_radius_px: int = 20
    pulley_hub_radius_px: int = 6
    load_width_px: int = 170
    load_height_px: int = 74
    load_top_gap_px: int = 34
    connector_width_px: int = 5
    effort_arrow_x_gap_px: int = 92
    effort_arrow_length_px: int = 144
    label_font_size_px: int = 28
    small_label_font_size_px: int = 24
    label_stroke_width_px: int = 3
    texture_line_width_px: int = 2
    texture_spacing_px: int = 18
    cut_endpoint_radius_px: int = 6
    connected_support_count_support: Tuple[int, ...] = (2, 3, 4, 5, 6)
    disconnected_segment_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4)
    effort_force_support: Tuple[int, ...] = tuple(range(4, 19))
    load_force_support: Tuple[int, ...] = _LOAD_FORCE_SUPPORT
    effort_force_min: int = 4
    effort_force_max: int = 18


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved scene/query axes and answer support for one instance."""

    scene_variant: str
    query_id: str
    public_query_id: str
    solve_for: str
    accent_color_name: str
    target_answer: int
    scene_variant_probabilities: Dict[str, float]
    query_id_probabilities: Dict[str, float]
    solve_for_probabilities: Dict[str, float]
    accent_color_name_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _CutSegmentSpec:
    """One visible rope segment that is not connected all the way through."""

    segment_id: str
    attach_side: str
    x_order: int
    cut_fraction: float


@dataclass(frozen=True)
class _SceneSpec:
    """Symbolic pulley system that realizes one query answer."""

    scene_variant: str
    query_id: str
    support_segment_count: int
    disconnected_segment_count: int
    connected_slot_indices: Tuple[int, ...]
    cut_segments: Tuple[_CutSegmentSpec, ...]
    effort_force_value: int
    load_force_value: int
    shown_effort_force_value: int | None
    shown_load_force_value: int | None
    target_answer: int
    evidence_entity_ids: Tuple[str, ...]


@dataclass(frozen=True)
class _RenderedScene:
    """Rendered pulley scene plus prompt-facing evidence metadata."""

    image: Image.Image
    evidence_bboxes: List[List[float]]
    evidence_entity_ids: List[str]
    scene_entities: List[Dict[str, Any]]
    render_map: Dict[str, Any]
    support_segment_bboxes: List[List[float]]
    cut_segment_bboxes: List[List[float]]
    load_label_bbox: List[float]
    effort_label_bbox: List[float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("physics", "mechanics")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(task_group="mechanics", apply_prob=0.5)


def _answer_support_key(query_id: str) -> str:
    """Return the configured answer-support key for one pulley query."""

    if str(query_id) == "effort_force_for_load":
        return "effort_force_support"
    return "load_force_support"


def _fallback_support(query_id: str) -> Tuple[int, ...]:
    """Return fallback answer support for one pulley query."""

    if str(query_id) == "effort_force_for_load":
        return _DEFAULTS.effort_force_support
    return _DEFAULTS.load_force_support


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
    """Resolve the public pulley query family, accepting old inverse names as aliases."""

    explicit_query = params.get("query_id")
    if explicit_query is not None and str(explicit_query) in _SOLVE_FOR_BY_QUERY_ID:
        return "force_relation", {"force_relation": 1.0}
    if explicit_query is not None and str(explicit_query) in SUPPORTED_PUBLIC_QUERY_IDS:
        return str(explicit_query), {str(explicit_query): 1.0}

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


def _normalize_solve_for(value: Any) -> str:
    normalized = str(value).strip().lower()
    if normalized in {"effort", "effort_force"}:
        return "effort_force"
    if normalized in {"load", "load_force"}:
        return "load_force"
    raise ValueError(f"unsupported solve_for: {value}")


def _resolve_solve_for(
    rng,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
    """Resolve whether the unknown pulley force is effort or load."""

    explicit_query = params.get("query_id")
    if explicit_query is not None and str(explicit_query) in _SOLVE_FOR_BY_QUERY_ID:
        selected = str(_SOLVE_FOR_BY_QUERY_ID[str(explicit_query)])
        return selected, {key: (1.0 if key == selected else 0.0) for key in _SUPPORTED_SOLVE_FOR_TARGETS}

    explicit_solve_for = params.get("solve_for")
    if explicit_solve_for is not None:
        selected = _normalize_solve_for(explicit_solve_for)
        return selected, {key: (1.0 if key == selected else 0.0) for key in _SUPPORTED_SOLVE_FOR_TARGETS}

    selected, probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=_SUPPORTED_SOLVE_FOR_TARGETS,
        explicit_key="solve_for",
        weights_key="solve_for_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=_SUPPORTED_SOLVE_FOR_TARGETS,
        balance_flag_key="balanced_solve_for_sampling",
        explicit_key="solve_for",
        weights_key="solve_for_weights",
        sampling_namespace=f"{TASK_ID}.solve_for",
    )
    return str(selected), {str(key): float(value) for key, value in sorted(probabilities.items())}


def _resolve_target_answer(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    query_id: str,
) -> Tuple[int, Dict[str, float]]:
    """Resolve one balanced answer target for the active pulley query."""

    target_params = dict(params)
    return resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=target_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=_answer_support_key(str(query_id)),
        explicit_key="target_answer",
        fallback_support=_fallback_support(str(query_id)),
        namespace=f"{TASK_ID}.target_answer.{str(query_id)}",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_support_permutation=True,
    )


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve one compatible scene/query pair, color, and answer target."""

    axis_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.axes")
    public_query_id, query_probs = _resolve_public_query_id(
        axis_rng,
        instance_seed=int(instance_seed),
        params=params,
    )
    solve_for, solve_for_probabilities = _resolve_solve_for(
        axis_rng,
        instance_seed=int(instance_seed),
        params=params,
    )
    query_id = str(_QUERY_ID_BY_SOLVE_FOR[str(solve_for)])
    scene_params = _with_sampling_divisor(
        params,
        divisor=len(_SUPPORTED_SOLVE_FOR_TARGETS),
        explicit_keys=("scene_variant",),
    )
    scene_variant, scene_probs = resolve_variant(
        axis_rng,
        params=scene_params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_SCENE_VARIANTS,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
    )
    scene_variant = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=scene_params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(scene_variant),
        variant_probabilities=scene_probs,
        supported_variants=SUPPORTED_SCENE_VARIANTS,
        balance_flag_key="balanced_scene_variant_sampling",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        sampling_namespace=f"{TASK_ID}.scene_variant",
    )
    target_answer, target_answer_probabilities = _resolve_target_answer(
        instance_seed=int(instance_seed),
        params=params,
        query_id=str(query_id),
    )
    color_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.accent_color_name")
    accent_color_name, accent_probs = resolve_variant(
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
        variant_probabilities=accent_probs,
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
        solve_for=str(solve_for),
        accent_color_name=str(accent_color_name),
        target_answer=int(target_answer),
        scene_variant_probabilities=dict(scene_probs),
        query_id_probabilities=dict(query_probs),
        solve_for_probabilities=dict(solve_for_probabilities),
        accent_color_name_probabilities=dict(accent_probs),
        target_answer_probabilities=dict(target_answer_probabilities),
    )


def _connected_support_count_support(params: Mapping[str, Any]) -> Tuple[int, ...]:
    """Return the active support for connected full-length strands."""

    return resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key="connected_support_count_support",
        fallback=_DEFAULTS.connected_support_count_support,
    )


def _disconnected_segment_count_support(params: Mapping[str, Any]) -> Tuple[int, ...]:
    """Return the active support for cut non-supporting strands."""

    return resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key="disconnected_segment_count_support",
        fallback=_DEFAULTS.disconnected_segment_count_support,
    )


def _effort_force_bounds(params: Mapping[str, Any]) -> Tuple[int, int]:
    """Return inclusive effort-force bounds used for feasible pulley scenes."""

    effort_min = int(params.get("effort_force_min", group_default(_GEN_DEFAULTS, "effort_force_min", _DEFAULTS.effort_force_min)))
    effort_max = int(params.get("effort_force_max", group_default(_GEN_DEFAULTS, "effort_force_max", _DEFAULTS.effort_force_max)))
    if int(effort_min) > int(effort_max):
        raise ValueError("effort_force_min must be <= effort_force_max")
    return int(effort_min), int(effort_max)


def _choose_count_from_support(
    rng,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    support: Sequence[int],
    explicit_keys: Sequence[str],
    namespace: str,
    balanced_flag_key: str,
    feasible_values: Sequence[int] | None = None,
) -> int:
    """Choose one integer count from support while respecting explicit overrides."""

    support_set = {int(value) for value in support}
    feasible_set = set(support_set if feasible_values is None else {int(value) for value in feasible_values})
    feasible = tuple(sorted(int(value) for value in support_set.intersection(feasible_set)))
    if not feasible:
        raise ValueError(f"no feasible values for {namespace}")
    for explicit_key in explicit_keys:
        raw_value = params.get(str(explicit_key))
        if raw_value is None:
            continue
        selected = int(raw_value)
        if int(selected) not in support_set:
            raise ValueError(f"unsupported {explicit_key}: {selected}")
        if int(selected) not in feasible:
            raise ValueError(f"infeasible {explicit_key}: {selected}")
        return int(selected)

    balanced_enabled = bool(params.get(str(balanced_flag_key), group_default(_GEN_DEFAULTS, str(balanced_flag_key), True)))
    if bool(balanced_enabled):
        selection_index = abs(int(instance_seed))
        return int(feasible[int(selection_index) % len(feasible)])
    return int(feasible[int(rng.randrange(len(feasible)))])


def _resolve_disconnected_segment_count(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> int:
    """Resolve how many cut non-supporting strands to draw."""

    support = _disconnected_segment_count_support(params)
    selected, _ = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="disconnected_segment_count_support",
        explicit_key="disconnected_segment_count",
        fallback_support=support,
        namespace=f"{TASK_ID}.disconnected_segment_count",
        balanced_flag_key="balanced_disconnected_segment_count_sampling",
        namespace_support_permutation=True,
    )
    return int(selected)


def _resolve_support_count_for_query(
    rng,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    query_id: str,
    target_answer: int,
    effort_min: int,
    effort_max: int,
) -> int:
    """Resolve a connected strand count that can realize the queried force."""

    support = _connected_support_count_support(params)
    if str(query_id) == "load_force_from_effort":
        feasible = tuple(
            int(count)
            for count in support
            if int(count) > 0
            and int(target_answer) % int(count) == 0
            and int(effort_min) <= int(target_answer) // int(count) <= int(effort_max)
        )
    else:
        feasible = tuple(int(value) for value in support)
    return _choose_count_from_support(
        rng,
        instance_seed=int(instance_seed),
        params=params,
        support=support,
        explicit_keys=("connected_support_count", "support_segment_count"),
        namespace=f"{TASK_ID}.connected_support_count.{str(query_id)}",
        balanced_flag_key="balanced_connected_support_count_sampling",
        feasible_values=feasible,
    )


def _sample_cut_segments(rng, *, disconnected_segment_count: int, cut_slot_indices: Sequence[int]) -> Tuple[_CutSegmentSpec, ...]:
    """Sample cut-strand attachment sides and cut fractions."""

    side_cycle = ["top" if index % 2 == 0 else "bottom" for index in range(int(disconnected_segment_count))]
    rng.shuffle(side_cycle)
    segments: List[_CutSegmentSpec] = []
    for segment_index, (slot_index, attach_side) in enumerate(zip(cut_slot_indices, side_cycle), start=1):
        segments.append(
            _CutSegmentSpec(
                segment_id=f"cut_segment_{int(segment_index)}",
                attach_side=str(attach_side),
                x_order=int(slot_index),
                cut_fraction=round(float(rng.uniform(0.25, 0.75)), 3),
            )
        )
    return tuple(segments)


def _sample_scene_spec(
    rng,
    *,
    instance_seed: int,
    scene_variant: str,
    query_id: str,
    target_answer: int,
    params: Mapping[str, Any],
) -> _SceneSpec:
    """Sample one symbolic pulley system that realizes the target answer."""

    query_id = str(query_id)
    target_answer = int(target_answer)
    effort_min, effort_max = _effort_force_bounds(params)
    support_count = _resolve_support_count_for_query(
        rng,
        instance_seed=int(instance_seed),
        params=params,
        query_id=str(query_id),
        target_answer=int(target_answer),
        effort_min=int(effort_min),
        effort_max=int(effort_max),
    )
    disconnected_count = _resolve_disconnected_segment_count(instance_seed=int(instance_seed), params=params)

    if query_id == "effort_force_for_load":
        effort_value = int(target_answer)
        load_value = int(effort_value) * int(support_count)
        shown_effort = None
        shown_load = int(load_value)
    else:
        if int(target_answer) % int(support_count) != 0:
            raise ValueError("load-force target is not divisible by connected support count")
        effort_value = int(target_answer) // int(support_count)
        if int(effort_value) < int(effort_min) or int(effort_value) > int(effort_max):
            raise ValueError("load-force target implies effort outside configured bounds")
        load_value = int(target_answer)
        shown_effort = int(effort_value)
        shown_load = None

    total_slots = int(support_count) + int(disconnected_count)
    slot_indices = list(range(int(total_slots)))
    rng.shuffle(slot_indices)
    connected_slot_indices = tuple(sorted(int(slot_index) for slot_index in slot_indices[: int(support_count)]))
    cut_slot_indices = tuple(sorted(int(slot_index) for slot_index in slot_indices[int(support_count) :]))
    cut_segments = _sample_cut_segments(
        rng,
        disconnected_segment_count=int(disconnected_count),
        cut_slot_indices=cut_slot_indices,
    )
    evidence_entity_ids: List[str] = [
        f"support_segment_{index}" for index in range(1, int(support_count) + 1)
    ]
    if query_id == "effort_force_for_load":
        evidence_entity_ids.extend(["load_force_label", "effort_force_label"])
    else:
        evidence_entity_ids.extend(["effort_force_label", "load_force_label"])

    return _SceneSpec(
        scene_variant=str(scene_variant),
        query_id=str(query_id),
        support_segment_count=int(support_count),
        disconnected_segment_count=int(disconnected_count),
        connected_slot_indices=tuple(int(slot_index) for slot_index in connected_slot_indices),
        cut_segments=tuple(cut_segments),
        effort_force_value=int(effort_value),
        load_force_value=int(load_value),
        shown_effort_force_value=None if shown_effort is None else int(shown_effort),
        shown_load_force_value=None if shown_load is None else int(shown_load),
        target_answer=int(target_answer),
        evidence_entity_ids=tuple(str(entity_id) for entity_id in evidence_entity_ids),
    )


def _draw_block_texture(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Sequence[float],
    line_rgb: Tuple[int, int, int],
    spacing_px: int,
    width_px: int,
) -> None:
    """Draw subtle diagonal hatching inside one pulley block."""

    left, top, right, bottom = [float(value) for value in bbox]
    span = int(bottom - top)
    offset = -span
    while offset < int(right - left) + span:
        draw.line(
            [(float(left + offset), float(top)), (float(left + offset + span), float(bottom))],
            fill=tuple(int(value) for value in line_rgb),
            width=max(1, int(width_px)),
        )
        offset += max(8, int(spacing_px))


def _draw_pulley(
    draw: ImageDraw.ImageDraw,
    *,
    center_x: float,
    center_y: float,
    radius_px: int,
    hub_radius_px: int,
    fill_rgb: Tuple[int, int, int],
    outline_rgb: Tuple[int, int, int],
    width_px: int,
) -> List[float]:
    """Draw one pulley wheel and return its bbox."""

    radius = float(radius_px)
    bbox = [
        round(float(center_x - radius), 3),
        round(float(center_y - radius), 3),
        round(float(center_x + radius), 3),
        round(float(center_y + radius), 3),
    ]
    draw.ellipse(
        tuple(float(value) for value in bbox),
        fill=tuple(int(value) for value in fill_rgb),
        outline=tuple(int(value) for value in outline_rgb),
        width=max(2, int(width_px)),
    )
    hub_radius = float(hub_radius_px)
    draw.ellipse(
        (
            float(center_x - hub_radius),
            float(center_y - hub_radius),
            float(center_x + hub_radius),
            float(center_y + hub_radius),
        ),
        fill=tuple(int(value) for value in outline_rgb),
        outline=tuple(int(value) for value in outline_rgb),
    )
    return list(bbox)


def _draw_text_tag(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    center: Tuple[float, float],
    font,
    fill_rgb: Tuple[int, int, int],
    outline_rgb: Tuple[int, int, int],
    text_rgb: Tuple[int, int, int],
    stroke_width_px: int,
) -> List[float]:
    """Draw one rounded label tag and return its outer bbox."""

    text_bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=max(0, int(stroke_width_px)))
    text_width = float(text_bbox[2] - text_bbox[0])
    text_height = float(text_bbox[3] - text_bbox[1])
    pad_x = 14.0
    pad_y = 9.0
    center_x, center_y = float(center[0]), float(center[1])
    tag_bbox = [
        round(float(center_x - (0.5 * text_width) - pad_x), 3),
        round(float(center_y - (0.5 * text_height) - pad_y), 3),
        round(float(center_x + (0.5 * text_width) + pad_x), 3),
        round(float(center_y + (0.5 * text_height) + pad_y), 3),
    ]
    draw_rounded_rect(
        draw,
        tuple(float(value) for value in tag_bbox),
        radius=10,
        fill=tuple(int(value) for value in fill_rgb),
        outline=tuple(int(value) for value in outline_rgb),
        width=max(2, int(stroke_width_px)),
    )
    text_draw_bbox = draw_centered_text(
        draw,
        text=str(text),
        center=(float(center_x), float(center_y)),
        font=font,
        fill=tuple(int(value) for value in text_rgb),
        stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(text_rgb)),
        stroke_width=max(1, int(stroke_width_px)),
    )
    return _bbox_union(tag_bbox, text_draw_bbox)


def _render_scene(
    *,
    background: Image.Image,
    render_defaults: Mapping[str, Any],
    accent_color_name: str,
    scene_spec: _SceneSpec,
    diagram_style: Any | None = None,
) -> _RenderedScene:
    """Render one single-system pulley diagram and return trace metadata."""

    image = background.copy()
    draw = ImageDraw.Draw(image)
    theme = build_physics_pulley_theme(str(accent_color_name), diagram_style=diagram_style)

    top_left = float(render_defaults["top_block_x_px"])
    top_y = float(render_defaults["top_block_y_px"])
    top_width = float(render_defaults["top_block_width_px"])
    top_height = float(render_defaults["top_block_height_px"])
    top_bbox = [
        round(float(top_left), 3),
        round(float(top_y), 3),
        round(float(top_left + top_width), 3),
        round(float(top_y + top_height), 3),
    ]
    top_center_x = float((top_bbox[0] + top_bbox[2]) / 2.0)
    if str(scene_spec.scene_variant) == "compact_block":
        lower_y = float(render_defaults["compact_lower_block_y_px"])
    elif str(scene_spec.scene_variant) == "tall_block":
        lower_y = float(render_defaults["tall_lower_block_y_px"])
    else:
        lower_y = float(render_defaults["lower_block_y_px"])

    segment_gap = float(render_defaults["support_segment_gap_px"])
    total_slots = int(scene_spec.support_segment_count) + int(scene_spec.disconnected_segment_count)
    lower_width = max(250.0, ((int(total_slots) - 1) * segment_gap) + 130.0)
    lower_height = float(render_defaults["lower_block_height_px"])
    lower_bbox = [
        round(float(top_center_x - (0.5 * lower_width)), 3),
        round(float(lower_y), 3),
        round(float(top_center_x + (0.5 * lower_width)), 3),
        round(float(lower_y + lower_height), 3),
    ]

    scene_entities: List[Dict[str, Any]] = [
        {
            "entity_id": "fixed_upper_block",
            "entity_type": "fixed_pulley_block",
            "bbox_px": list(top_bbox),
            "meta": {"scene_variant": str(scene_spec.scene_variant)},
        },
        {
            "entity_id": "moving_lower_block",
            "entity_type": "moving_pulley_block",
            "bbox_px": list(lower_bbox),
            "meta": {
                "support_segment_count": int(scene_spec.support_segment_count),
                "disconnected_segment_count": int(scene_spec.disconnected_segment_count),
            },
        },
    ]

    for block_bbox in (top_bbox, lower_bbox):
        draw_rounded_rect(
            draw,
            tuple(float(value) for value in block_bbox),
            radius=14,
            fill=tuple(int(value) for value in theme.frame_fill_rgb),
            outline=tuple(int(value) for value in theme.frame_outline_rgb),
            width=4,
        )

    slot_xs = {
        int(slot_index): float(top_center_x + ((int(slot_index) - ((int(total_slots) - 1) / 2.0)) * segment_gap))
        for slot_index in range(int(total_slots))
    }
    rope_width = int(render_defaults["rope_width_px"])
    pulley_radius = int(render_defaults["pulley_radius_px"])
    hub_radius = int(render_defaults["pulley_hub_radius_px"])
    top_pulley_y = float((top_bbox[1] + top_bbox[3]) / 2.0)
    lower_pulley_y = float((lower_bbox[1] + lower_bbox[3]) / 2.0)
    rope_top_y = float(top_bbox[3] + 2.0)
    rope_bottom_y = float(lower_bbox[1] - 2.0)
    span = float(rope_bottom_y - rope_top_y)

    support_segment_bboxes: List[List[float]] = []
    support_segment_map: Dict[str, List[float]] = {}
    cut_segment_bboxes: List[List[float]] = []
    cut_segment_map: Dict[str, List[float]] = {}
    pulley_bboxes: List[List[float]] = []
    connected_slots = set(int(slot_index) for slot_index in scene_spec.connected_slot_indices)
    top_cut_slots = {int(segment.x_order) for segment in scene_spec.cut_segments if str(segment.attach_side) == "top"}
    bottom_cut_slots = {int(segment.x_order) for segment in scene_spec.cut_segments if str(segment.attach_side) == "bottom"}

    for support_index, slot_index in enumerate(sorted(connected_slots), start=1):
        x_value = float(slot_xs[int(slot_index)])
        segment_bbox = [
            round(float(x_value - (rope_width / 2.0)), 3),
            round(float(rope_top_y), 3),
            round(float(x_value + (rope_width / 2.0)), 3),
            round(float(rope_bottom_y), 3),
        ]
        draw.line(
            [(float(x_value), float(rope_top_y)), (float(x_value), float(rope_bottom_y))],
            fill=tuple(int(value) for value in theme.rope_rgb),
            width=max(2, int(rope_width)),
        )
        entity_id = f"support_segment_{int(support_index)}"
        support_segment_bboxes.append(list(segment_bbox))
        support_segment_map[entity_id] = list(segment_bbox)
        scene_entities.append(
            {
                "entity_id": entity_id,
                "entity_type": "supporting_rope_segment",
                "bbox_px": list(segment_bbox),
                "meta": {
                    "slot_index": int(slot_index),
                    "segment_index": int(support_index),
                    "supports_moving_block": True,
                    "connects_upper_and_lower_blocks": True,
                },
            }
        )

    cap_radius = float(render_defaults["cut_endpoint_radius_px"])
    for cut_segment in scene_spec.cut_segments:
        x_value = float(slot_xs[int(cut_segment.x_order)])
        cut_y = float(rope_top_y + (span * float(cut_segment.cut_fraction)))
        if str(cut_segment.attach_side) == "top":
            start_y, end_y = float(rope_top_y), float(cut_y)
            cap_y = float(end_y)
        else:
            start_y, end_y = float(cut_y), float(rope_bottom_y)
            cap_y = float(start_y)
        draw.line(
            [(float(x_value), float(start_y)), (float(x_value), float(end_y))],
            fill=tuple(int(value) for value in theme.rope_rgb),
            width=max(2, int(rope_width)),
        )
        draw.line(
            [(float(x_value - (cap_radius * 1.7)), float(cap_y)), (float(x_value + (cap_radius * 1.7)), float(cap_y))],
            fill=tuple(int(value) for value in theme.missing_outline_rgb),
            width=max(2, int(rope_width) - 1),
        )
        segment_bbox = [
            round(float(x_value - max(rope_width / 2.0, cap_radius * 1.7)), 3),
            round(float(min(start_y, end_y) - 1.0), 3),
            round(float(x_value + max(rope_width / 2.0, cap_radius * 1.7)), 3),
            round(float(max(start_y, end_y) + 1.0), 3),
        ]
        cut_segment_bboxes.append(list(segment_bbox))
        cut_segment_map[str(cut_segment.segment_id)] = list(segment_bbox)
        scene_entities.append(
            {
                "entity_id": str(cut_segment.segment_id),
                "entity_type": "cut_non_supporting_rope_segment",
                "bbox_px": list(segment_bbox),
                "meta": {
                    "slot_index": int(cut_segment.x_order),
                    "attach_side": str(cut_segment.attach_side),
                    "cut_fraction": float(cut_segment.cut_fraction),
                    "supports_moving_block": False,
                    "connects_upper_and_lower_blocks": False,
                },
            }
        )

    for slot_index in sorted(connected_slots.union(top_cut_slots)):
        x_value = float(slot_xs[int(slot_index)])
        pulley_bbox = _draw_pulley(
            draw,
            center_x=float(x_value),
            center_y=float(top_pulley_y),
            radius_px=int(pulley_radius),
            hub_radius_px=int(hub_radius),
            fill_rgb=tuple(int(value) for value in theme.pulley_fill_rgb),
            outline_rgb=tuple(int(value) for value in theme.pulley_outline_rgb),
            width_px=3,
        )
        pulley_bboxes.append(list(pulley_bbox))
        scene_entities.append(
            {
                "entity_id": f"upper_pulley_slot_{int(slot_index)}",
                "entity_type": "pulley_wheel",
                "bbox_px": list(pulley_bbox),
                "meta": {"block": "fixed_upper_block", "slot_index": int(slot_index)},
            }
        )
    for slot_index in sorted(connected_slots.union(bottom_cut_slots)):
        x_value = float(slot_xs[int(slot_index)])
        pulley_bbox = _draw_pulley(
            draw,
            center_x=float(x_value),
            center_y=float(lower_pulley_y),
            radius_px=int(pulley_radius),
            hub_radius_px=int(hub_radius),
            fill_rgb=tuple(int(value) for value in theme.pulley_fill_rgb),
            outline_rgb=tuple(int(value) for value in theme.pulley_outline_rgb),
            width_px=3,
        )
        pulley_bboxes.append(list(pulley_bbox))
        scene_entities.append(
            {
                "entity_id": f"lower_pulley_slot_{int(slot_index)}",
                "entity_type": "pulley_wheel",
                "bbox_px": list(pulley_bbox),
                "meta": {"block": "moving_lower_block", "slot_index": int(slot_index)},
            }
        )

    connector_x = float((lower_bbox[0] + lower_bbox[2]) / 2.0)
    load_top = float(lower_bbox[3] + int(render_defaults["load_top_gap_px"]))
    load_width = float(render_defaults["load_width_px"])
    load_height = float(render_defaults["load_height_px"])
    load_bbox = [
        round(float(connector_x - (0.5 * load_width)), 3),
        round(float(load_top), 3),
        round(float(connector_x + (0.5 * load_width)), 3),
        round(float(load_top + load_height), 3),
    ]
    draw.line(
        [(float(connector_x), float(lower_bbox[3])), (float(connector_x), float(load_bbox[1]))],
        fill=tuple(int(value) for value in theme.rope_rgb),
        width=max(2, int(render_defaults["connector_width_px"])),
    )
    draw_rounded_rect(
        draw,
        tuple(float(value) for value in load_bbox),
        radius=12,
        fill=tuple(int(value) for value in theme.load_fill_rgb)
        if scene_spec.shown_load_force_value is not None
        else tuple(int(value) for value in theme.missing_fill_rgb),
        outline=tuple(int(value) for value in theme.load_outline_rgb)
        if scene_spec.shown_load_force_value is not None
        else tuple(int(value) for value in theme.missing_outline_rgb),
        width=4,
    )
    if scene_spec.shown_load_force_value is None:
        load_text = "load ? N"
        load_text_fill = tuple(int(value) for value in theme.missing_text_rgb)
    else:
        load_text = f"load {int(scene_spec.shown_load_force_value)} N"
        load_text_fill = tuple(int(value) for value in theme.load_text_rgb)
    load_text_bbox = draw_centered_text(
        draw,
        text=str(load_text),
        center=(float(connector_x), float((load_bbox[1] + load_bbox[3]) / 2.0)),
        font=load_font(int(render_defaults["label_font_size_px"]), bold=True),
        fill=tuple(int(value) for value in load_text_fill),
        stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(load_text_fill)),
        stroke_width=max(1, int(render_defaults["label_stroke_width_px"])),
    )
    load_label_bbox = _bbox_union(load_bbox, load_text_bbox)

    effort_x = min(
        float(image.size[0] - 120.0),
        float(lower_bbox[2] + int(render_defaults["effort_arrow_x_gap_px"])),
    )
    arrow_start_y = float(top_bbox[3] + 24.0)
    arrow_end_y = min(
        float(lower_bbox[1] - 24.0),
        float(arrow_start_y + int(render_defaults["effort_arrow_length_px"])),
    )
    if arrow_end_y <= arrow_start_y + 30.0:
        arrow_end_y = float(arrow_start_y + 30.0)
    draw_arrow(
        draw,
        start=(float(effort_x), float(arrow_start_y)),
        end=(float(effort_x), float(arrow_end_y)),
        fill=tuple(int(value) for value in theme.effort_rgb),
        width=max(3, int(rope_width)),
        head_length_px=20.0,
        head_width_px=18.0,
    )
    effort_arrow_bbox = [
        round(float(effort_x - 12.0), 3),
        round(float(arrow_start_y), 3),
        round(float(effort_x + 12.0), 3),
        round(float(arrow_end_y), 3),
    ]
    if scene_spec.shown_effort_force_value is None:
        effort_text = "effort ? N"
        effort_missing = True
    else:
        effort_text = f"effort {int(scene_spec.shown_effort_force_value)} N"
        effort_missing = False
    effort_tag_bbox = _draw_text_tag(
        draw,
        text=str(effort_text),
        center=(float(min(image.size[0] - 96.0, effort_x + 52.0)), float((arrow_start_y + arrow_end_y) / 2.0)),
        font=load_font(int(render_defaults["small_label_font_size_px"]), bold=True),
        fill_rgb=tuple(int(value) for value in theme.missing_fill_rgb) if effort_missing else (255, 255, 255),
        outline_rgb=tuple(int(value) for value in theme.missing_outline_rgb)
        if effort_missing
        else tuple(int(value) for value in theme.effort_rgb),
        text_rgb=tuple(int(value) for value in theme.missing_text_rgb)
        if effort_missing
        else tuple(int(value) for value in theme.load_text_rgb),
        stroke_width_px=int(render_defaults["label_stroke_width_px"]),
    )
    effort_label_bbox = _bbox_union(effort_arrow_bbox, effort_tag_bbox)

    scene_entities.extend(
        [
            {
                "entity_id": "load_force_label",
                "entity_type": "load_force_label",
                "bbox_px": list(load_label_bbox),
                "meta": {
                    "shown_value": None if scene_spec.shown_load_force_value is None else int(scene_spec.shown_load_force_value),
                    "true_value": int(scene_spec.load_force_value),
                },
            },
            {
                "entity_id": "effort_force_label",
                "entity_type": "effort_force_label",
                "bbox_px": list(effort_label_bbox),
                "meta": {
                    "shown_value": None if scene_spec.shown_effort_force_value is None else int(scene_spec.shown_effort_force_value),
                    "true_value": int(scene_spec.effort_force_value),
                },
            },
        ]
    )

    entity_bbox_map = {
        str(entity["entity_id"]): list(entity["bbox_px"])
        for entity in scene_entities
        if entity.get("bbox_px") is not None
    }
    evidence_bboxes = [
        list(entity_bbox_map[entity_id])
        for entity_id in scene_spec.evidence_entity_ids
        if str(entity_id) in entity_bbox_map
    ]

    render_map = {
        "accent_color_name": str(accent_color_name),
        "technical_diagram_frame_mode": str(getattr(diagram_style, "frame_mode", "none")),
        "fixed_upper_block_bbox_px": list(top_bbox),
        "moving_lower_block_bbox_px": list(lower_bbox),
        "support_segment_count": int(scene_spec.support_segment_count),
        "disconnected_segment_count": int(scene_spec.disconnected_segment_count),
        "connected_slot_indices": [int(value) for value in scene_spec.connected_slot_indices],
        "support_segment_bboxes_px": dict(support_segment_map),
        "cut_segment_bboxes_px": dict(cut_segment_map),
        "pulley_bboxes_px": [list(bbox) for bbox in pulley_bboxes],
        "load_force_label_bbox_px": list(load_label_bbox),
        "effort_force_label_bbox_px": list(effort_label_bbox),
        "evidence_entity_ids": list(scene_spec.evidence_entity_ids),
    }

    return _RenderedScene(
        image=image,
        evidence_bboxes=[list(bbox) for bbox in evidence_bboxes],
        evidence_entity_ids=list(scene_spec.evidence_entity_ids),
        scene_entities=[dict(entity) for entity in scene_entities],
        render_map=dict(render_map),
        support_segment_bboxes=[list(bbox) for bbox in support_segment_bboxes],
        cut_segment_bboxes=[list(bbox) for bbox in cut_segment_bboxes],
        load_label_bbox=list(load_label_bbox),
        effort_label_bbox=list(effort_label_bbox),
    )


def _build_prompt_examples(_: str) -> Tuple[str, str]:
    """Return one stable prompt JSON example for pulley force queries."""

    evidence = [
        [420, 166, 427, 428],
        [468, 166, 475, 428],
        [516, 166, 523, 428],
        [649, 538, 819, 612],
        [1036, 190, 1196, 350],
    ]
    return build_prompt_json_examples(evidence_value=evidence, answer_type="integer")


@register_task
class PhysicsMechanicsPulleyMechanicalAdvantageTask:
    """Return one ideal pulley mechanical-advantage question."""

    task_id = TASK_ID
    domain = "physics"
    task_group = "mechanics"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        rendered_scene: _RenderedScene | None = None
        scene_spec: _SceneSpec | None = None

        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                scene_spec = _sample_scene_spec(
                    attempt_rng,
                    instance_seed=int(instance_seed),
                    scene_variant=str(axes.scene_variant),
                    query_id=str(axes.query_id),
                    target_answer=int(axes.target_answer),
                    params=params,
                )
            except ValueError:
                continue

            background, background_meta, diagram_style, diagram_style_meta = prepare_physics_diagram_style_and_background(
                scene_id="pulley",
                task_group=self.task_group,
                canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
                canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
                instance_seed=int(instance_seed),
                params=params,
            )
            rendered_scene = _render_scene(
                background=background,
                render_defaults={
                    key: resolve_render_int(
                        params,
                        _RENDER_DEFAULTS,
                        key,
                        int(getattr(_DEFAULTS, key)),
                        instance_seed=int(instance_seed),
                        namespace=TASK_ID,
                    )
                    for key in (
                        "top_block_x_px",
                        "top_block_y_px",
                        "top_block_width_px",
                        "top_block_height_px",
                        "lower_block_y_px",
                        "compact_lower_block_y_px",
                        "tall_lower_block_y_px",
                        "lower_block_height_px",
                        "support_segment_gap_px",
                        "rope_width_px",
                        "pulley_radius_px",
                        "pulley_hub_radius_px",
                        "load_width_px",
                        "load_height_px",
                        "load_top_gap_px",
                        "connector_width_px",
                        "effort_arrow_x_gap_px",
                        "effort_arrow_length_px",
                        "label_font_size_px",
                        "small_label_font_size_px",
                        "label_stroke_width_px",
                        "texture_line_width_px",
                        "texture_spacing_px",
                        "cut_endpoint_radius_px",
                    )
                },
                accent_color_name=str(axes.accent_color_name),
                scene_spec=scene_spec,
                diagram_style=diagram_style,
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
                    "object_description_open_block",
                    "object_description_compact_block",
                    "object_description_tall_block",
                    "evidence_hint_effort_force",
                    "evidence_hint_load_force",
                ),
                context=f"prompt defaults for {self.task_id}",
            )
            json_example, json_example_answer_only = _build_prompt_examples(str(axes.query_id))
            prompt_selection = render_task_prompt_variants(
                domain=self.domain,
                task_group=self.task_group,
                bundle_id=str(prompt_defaults["bundle_id"]),
                scene_key=str(prompt_defaults["scene_key"]),
                task_key=str(prompt_defaults["task_key"]),
                query_key=str(axes.public_query_id),
                answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
                slots={
                    "object_description": str(prompt_defaults[f"object_description_{str(axes.scene_variant)}"]),
                    "solve_for": str(axes.solve_for).replace("_", " "),
                    "json_output_contract": str(prompt_defaults["json_output_contract"]),
                    "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                    "answer_hint": str(prompt_defaults["answer_hint"]),
                    "json_example": str(json_example),
                    "json_example_answer_only": str(json_example_answer_only),
                    "evidence_hint": str(
                        prompt_defaults["evidence_hint_effort_force"]
                        if str(axes.query_id) == "effort_force_for_load"
                        else prompt_defaults["evidence_hint_load_force"]
                    ),
                },
                instance_seed=int(instance_seed),
            )
            prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

            answer_gt = TypedValue(type="integer", value=int(axes.target_answer))
            evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in rendered_scene.evidence_bboxes])
            target_support_key = _answer_support_key(str(axes.query_id))
            complexity = build_physics_pulley_mechanical_advantage_complexity(
                task_group_defaults=_TASK_GROUP_DEFAULTS,
                task_id=self.task_id,
                scene_variant=str(axes.scene_variant),
                query_id=str(axes.query_id),
                support_segment_count=int(scene_spec.support_segment_count),
                disconnected_segment_count=int(scene_spec.disconnected_segment_count),
                target_answer=int(axes.target_answer),
                evidence_count=len(rendered_scene.evidence_bboxes),
            )
            cut_segment_payload = [
                {
                    "segment_id": str(segment.segment_id),
                    "attach_side": str(segment.attach_side),
                    "slot_index": int(segment.x_order),
                    "cut_fraction": float(segment.cut_fraction),
                    "supports_moving_block": False,
                }
                for segment in scene_spec.cut_segments
            ]
            trace_payload = {
                "scene_ir": {
                    "scene_kind": f"physics_pulley_mechanical_advantage_{str(axes.scene_variant)}",
                    "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                    "relations": {
                        "scene_variant": str(axes.scene_variant),
                        "query_id": str(axes.public_query_id),
                        "internal_query_id": str(axes.query_id),
                        "solve_for": str(axes.solve_for),
                        "accent_color_name": str(axes.accent_color_name),
                        "support_segment_count": int(scene_spec.support_segment_count),
                        "connected_support_count": int(scene_spec.support_segment_count),
                        "disconnected_segment_count": int(scene_spec.disconnected_segment_count),
                        "effort_force_value": int(scene_spec.effort_force_value),
                        "load_force_value": int(scene_spec.load_force_value),
                        "shown_effort_force_value": None
                        if scene_spec.shown_effort_force_value is None
                        else int(scene_spec.shown_effort_force_value),
                        "shown_load_force_value": None
                        if scene_spec.shown_load_force_value is None
                        else int(scene_spec.shown_load_force_value),
                        "connected_slot_indices": [int(value) for value in scene_spec.connected_slot_indices],
                        "cut_segments": [dict(item) for item in cut_segment_payload],
                        "target_answer": int(axes.target_answer),
                        "evidence_entity_ids": list(rendered_scene.evidence_entity_ids),
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
                        "solve_for": str(axes.solve_for),
                        "accent_color_name": str(axes.accent_color_name),
                        "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                        "query_id_probabilities": dict(axes.query_id_probabilities),
                        "solve_for_probabilities": dict(axes.solve_for_probabilities),
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
                    "technical_diagram_style": dict(diagram_style_meta),
                    "background_style": background_meta,
                    "post_image_noise": post_noise_meta,
                },
                "render_map": dict(rendered_scene.render_map),
                "execution_trace": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.public_query_id),
                    "internal_query_id": str(axes.query_id),
                    "solve_for": str(axes.solve_for),
                    "accent_color_name": str(axes.accent_color_name),
                    "target_answer": int(axes.target_answer),
                    "target_answer_support": list(
                        resolve_integer_support(
                            params,
                            gen_defaults=_GEN_DEFAULTS,
                            key=str(target_support_key),
                            fallback=_fallback_support(str(axes.query_id)),
                        )
                    ),
                    "connected_support_count_support": list(_connected_support_count_support(params)),
                    "disconnected_segment_count_support": list(_disconnected_segment_count_support(params)),
                    "effort_force_min": int(_effort_force_bounds(params)[0]),
                    "effort_force_max": int(_effort_force_bounds(params)[1]),
                    "support_segment_count": int(scene_spec.support_segment_count),
                    "connected_support_count": int(scene_spec.support_segment_count),
                    "disconnected_segment_count": int(scene_spec.disconnected_segment_count),
                    "effort_force_value": int(scene_spec.effort_force_value),
                    "load_force_value": int(scene_spec.load_force_value),
                    "shown_effort_force_value": None
                    if scene_spec.shown_effort_force_value is None
                    else int(scene_spec.shown_effort_force_value),
                    "shown_load_force_value": None
                    if scene_spec.shown_load_force_value is None
                    else int(scene_spec.shown_load_force_value),
                    "connected_slot_indices": [int(value) for value in scene_spec.connected_slot_indices],
                    "cut_segments": [dict(item) for item in cut_segment_payload],
                    "evidence_entity_ids": list(rendered_scene.evidence_entity_ids),
                },
                "witness_symbolic": {
                    "type": "object_set",
                    "ids": [str(item) for item in rendered_scene.evidence_entity_ids],
                },
                "projected_evidence": {
                    "bbox_set": [list(bbox) for bbox in rendered_scene.evidence_bboxes],
                },
                "background": background_meta,
                "post_image_noise": post_noise_meta,
            }
            return rewrite_physics_query_output(
                TaskOutput(
                    prompt=str(prompt_artifacts.prompt),
                    prompt_variants=dict(prompt_artifacts.prompt_variants),
                    answer_gt=answer_gt,
                    evidence_gt=evidence_gt,
                    image=image,
                    image_id="img0",
                    trace_payload=trace_payload,
                    complexity=complexity,
                    task_versions=default_task_versions(),
                    scene_id="pulley",
                ),
                query_id=str(axes.public_query_id),
            )

        raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts")


__all__ = ["PhysicsMechanicsPulleyMechanicalAdvantageTask"]
