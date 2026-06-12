"""Identity-free semantic sampling primitives for darts scene tasks."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from trace.core.seed import spawn_rng
from trace.tasks.games.shared.layout import apply_games_layout_jitter_to_bbox, resolve_games_layout_jitter
from trace.tasks.games.shared.style import SUPPORTED_DARTS_STYLE_VARIANTS
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.shared.font_assets import sample_font_family
from trace.tasks.shared.support_sampling import resolve_integer_choice, resolve_integer_support
from trace.tasks.shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant

from .rendering import (
    DARTBOARD_SAMPLE_RADIUS_FRACTIONS,
    STANDARD_DART_SECTORS,
    DartInstance,
    DartScoreOption,
    DartboardRenderParams,
    polar_to_xy,
)
from .state import (
    DARTS_NAMESPACE,
    DEFAULTS,
    SUPPORTED_DARTS_SCENE_VARIANTS,
    SUPPORTED_DARTS_TARGET_RINGS,
    SUPPORTED_DARTS_THRESHOLDS,
    DartsIntegerAxis,
    DartsSampledScene,
    DartsSceneAxes,
    DartsScoreSlot,
)


_SECTOR_TO_INDEX = {int(value): int(index) for index, value in enumerate(STANDARD_DART_SECTORS)}
_RING_RADIUS_FRACTIONS: Mapping[str, Tuple[float, float]] = DARTBOARD_SAMPLE_RADIUS_FRACTIONS
_RING_SCORE_KIND = {
    "inner_bull": "bull",
    "outer_bull": "bull",
    "inner_single": "single",
    "outer_single": "single",
    "triple": "triple",
    "double": "double",
}


def _resolve_named_axis(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    namespace: str,
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    supported: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one named semantic or visual axis without task identity."""

    rng = spawn_rng(int(instance_seed), f"{DARTS_NAMESPACE}.{str(namespace)}")
    selected, probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=gen_defaults,
        supported_variants=[str(item) for item in supported],
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=[str(item) for item in supported],
        balance_flag_key=str(balance_flag_key),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        sampling_namespace=f"{DARTS_NAMESPACE}.{str(namespace)}",
    )
    return str(selected), dict(probabilities)


def resolve_darts_scene_axes(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> DartsSceneAxes:
    """Resolve scene and style axes common to darts tasks."""

    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_DARTS_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_DARTS_STYLE_VARIANTS,
    )
    return DartsSceneAxes(
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
    )


def resolve_darts_integer_axis(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    support_key: str,
    explicit_key: str,
    fallback_support: Sequence[int],
    namespace: str,
    balanced_flag_key: str,
) -> DartsIntegerAxis:
    """Resolve one task-owned integer axis."""

    support = resolve_integer_support(
        params,
        gen_defaults=gen_defaults,
        key=str(support_key),
        fallback=tuple(int(value) for value in fallback_support),
    )
    value, probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        support_key=str(support_key),
        explicit_key=str(explicit_key),
        fallback_support=support,
        namespace=f"{DARTS_NAMESPACE}.{str(namespace)}",
        balanced_flag_key=str(balanced_flag_key),
        namespace_support_permutation=True,
    )
    return DartsIntegerAxis(
        value=int(value),
        support=tuple(int(item) for item in support),
        probabilities=dict(probabilities),
    )


def feasible_count_support(*, dart_count: int, raw_support: Sequence[int]) -> Tuple[int, ...]:
    """Return answer-count support feasible for the active dart count."""

    return tuple(int(value) for value in raw_support if 0 <= int(value) <= int(dart_count))


def resolve_darts_count_target_axis(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    dart_count: int,
    namespace: str,
) -> DartsIntegerAxis:
    """Resolve the answer-count target for a count-style darts task."""

    raw_support = resolve_integer_support(
        params,
        gen_defaults=gen_defaults,
        key="count_target_answer_support",
        fallback=DEFAULTS.count_target_answer_support,
    )
    support = feasible_count_support(dart_count=int(dart_count), raw_support=raw_support)
    target_params = dict(params)
    target_params["count_target_answer_support"] = [int(value) for value in support]
    return resolve_darts_integer_axis(
        instance_seed=int(instance_seed),
        params=target_params,
        gen_defaults=gen_defaults,
        support_key="count_target_answer_support",
        explicit_key="target_answer",
        fallback_support=support,
        namespace=str(namespace),
        balanced_flag_key="balanced_target_answer_sampling",
    )


def resolve_darts_target_ring(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
    """Resolve the requested dartboard ring family."""

    return _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        namespace="target_ring",
        explicit_key="target_ring",
        weights_key="target_ring_weights",
        balance_flag_key="balanced_target_ring_sampling",
        supported=SUPPORTED_DARTS_TARGET_RINGS,
    )


def resolve_darts_target_threshold(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> DartsIntegerAxis:
    """Resolve the requested dart score threshold."""

    return resolve_darts_integer_axis(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        support_key="target_threshold_support",
        explicit_key="target_threshold",
        fallback_support=SUPPORTED_DARTS_THRESHOLDS,
        namespace="target_threshold",
        balanced_flag_key="balanced_target_threshold_sampling",
    )


def score_slot_public_ring(slot: DartsScoreSlot) -> str:
    """Return the prompt-facing ring family for one slot."""

    return _RING_SCORE_KIND[str(slot.ring)]


def score_slot_in_ring(slot: DartsScoreSlot, *, target_ring: str) -> bool:
    """Return whether one score slot belongs to the requested public ring."""

    return str(score_slot_public_ring(slot)) == str(target_ring)


def score_slot_at_least(slot: DartsScoreSlot, *, threshold: int) -> bool:
    """Return whether one score slot meets a score threshold."""

    return int(slot.score) >= int(threshold)


def _all_score_slots() -> Tuple[DartsScoreSlot, ...]:
    """Return the supported dart scoring slots."""

    slots: List[DartsScoreSlot] = [
        DartsScoreSlot(sector_value=None, ring="inner_bull", score=50),
        DartsScoreSlot(sector_value=None, ring="outer_bull", score=25),
    ]
    for sector_value in STANDARD_DART_SECTORS:
        slots.extend(
            (
                DartsScoreSlot(sector_value=int(sector_value), ring="inner_single", score=int(sector_value)),
                DartsScoreSlot(sector_value=int(sector_value), ring="outer_single", score=int(sector_value)),
                DartsScoreSlot(sector_value=int(sector_value), ring="triple", score=int(sector_value) * 3),
                DartsScoreSlot(sector_value=int(sector_value), ring="double", score=int(sector_value) * 2),
            )
        )
    return tuple(slots)


SCORE_SLOTS = _all_score_slots()


def _sample_slot(rng, slots: Sequence[DartsScoreSlot]) -> DartsScoreSlot:
    """Return one random score slot from a non-empty pool."""

    if not slots:
        raise ValueError("cannot sample from an empty dart score-slot pool")
    return slots[int(rng.randrange(len(slots)))]


def _slot_position(rng, *, slot: DartsScoreSlot, params: DartboardRenderParams) -> Tuple[float, float]:
    """Sample a visible non-overlapping point inside one scoring slot."""

    board_radius = float(params.board_radius_px)
    if slot.sector_value is None:
        angle = float(rng.uniform(-180.0, 180.0))
        radius_min, radius_max = _RING_RADIUS_FRACTIONS[str(slot.ring)]
        radius = float(rng.uniform(float(radius_min), float(radius_max)) * board_radius)
        return polar_to_xy(
            cx=float(params.board_center_x_px),
            cy=float(params.board_center_y_px),
            radius=float(radius),
            angle_deg=float(angle),
        )

    sector_index = _SECTOR_TO_INDEX[int(slot.sector_value)]
    center_angle = float(sector_index * 18.0)
    angle = float(rng.uniform(center_angle - 6.4, center_angle + 6.4))
    radius_min, radius_max = _RING_RADIUS_FRACTIONS[str(slot.ring)]
    radius = float(rng.uniform(float(radius_min), float(radius_max)) * board_radius)
    return polar_to_xy(
        cx=float(params.board_center_x_px),
        cy=float(params.board_center_y_px),
        radius=float(radius),
        angle_deg=float(angle),
    )


def _sample_position_without_overlap(
    rng,
    *,
    slot: DartsScoreSlot,
    params: DartboardRenderParams,
    existing_points: Sequence[Tuple[float, float]],
) -> Tuple[float, float]:
    """Sample one marker center with a minimum distance from existing darts."""

    min_distance = float(max(24, int(params.marker_radius_px) * 2 + 8))
    for _ in range(96):
        point = _slot_position(rng, slot=slot, params=params)
        if all(((point[0] - x) ** 2 + (point[1] - y) ** 2) ** 0.5 >= min_distance for x, y in existing_points):
            return point
    return _slot_position(rng, slot=slot, params=params)


def build_darts_score_options(
    rng,
    *,
    correct_score: int,
    correct_label: str | None,
    option_count: int,
) -> Tuple[Tuple[DartScoreOption, ...], str]:
    """Return visible unique score options and the correct option label."""

    labels = ("A", "B", "C", "D", "E", "F")[: int(option_count)]
    if len(labels) < 2:
        raise ValueError("darts score option count must be at least 2")
    resolved_correct_label = str(correct_label) if correct_label in labels else str(labels[0])
    possible_scores = sorted({int(slot.score) for slot in SCORE_SLOTS})
    distractor_pool = [int(value) for value in possible_scores if int(value) != int(correct_score)]
    nearby_scores = sorted(distractor_pool, key=lambda value: (abs(int(value) - int(correct_score)), int(value)))
    candidate_scores = list(nearby_scores[:14])
    rng.shuffle(candidate_scores)
    distractor_count = int(len(labels) - 1)
    selected_scores = [int(value) for value in candidate_scores[:distractor_count]]
    if len(set(selected_scores)) != distractor_count or int(correct_score) in set(selected_scores):
        raise RuntimeError("failed to construct unique darts score options")
    rng.shuffle(selected_scores)
    distractor_by_label = dict(zip([label for label in labels if label != resolved_correct_label], selected_scores[:distractor_count]))
    options = tuple(
        DartScoreOption(
            label=str(label),
            score=int(correct_score) if str(label) == resolved_correct_label else int(distractor_by_label[str(label)]),
            is_answer=bool(str(label) == resolved_correct_label),
        )
        for label in labels
    )
    return options, str(resolved_correct_label)


def sample_darts_for_count(
    rng,
    *,
    dart_count: int,
    target_answer: int,
    render_params: DartboardRenderParams,
    qualifying_slots: Sequence[DartsScoreSlot],
    nonqualifying_slots: Sequence[DartsScoreSlot],
) -> DartsSampledScene:
    """Sample darts with an exact count of qualifying score slots."""

    selected_slots = [
        _sample_slot(rng, qualifying_slots) for _ in range(int(target_answer))
    ] + [
        _sample_slot(rng, nonqualifying_slots) for _ in range(max(0, int(dart_count) - int(target_answer)))
    ]
    annotation_flags = [True for _ in range(int(target_answer))] + [
        False for _ in range(max(0, int(dart_count) - int(target_answer)))
    ]
    combined = list(zip(selected_slots, annotation_flags))
    rng.shuffle(combined)
    return _sample_darts_from_slots(
        rng,
        render_params=render_params,
        selected_slots=[slot for slot, _ in combined],
        annotation_flags=[flag for _, flag in combined],
    )


def sample_darts_for_score_options(
    rng,
    *,
    dart_count: int,
    render_params: DartboardRenderParams,
    option_count: int,
    correct_label: str | None,
) -> DartsSampledScene:
    """Sample darts and visible total-score options."""

    selected_slots = [_sample_slot(rng, SCORE_SLOTS) for _ in range(int(dart_count))]
    sampled = _sample_darts_from_slots(
        rng,
        render_params=render_params,
        selected_slots=selected_slots,
        annotation_flags=[True for _ in selected_slots],
    )
    score_options, answer_label = build_darts_score_options(
        rng,
        correct_score=int(sampled.total_score),
        correct_label=correct_label,
        option_count=int(option_count),
    )
    return DartsSampledScene(
        darts=tuple(sampled.darts),
        annotation_dart_ids=tuple(sampled.annotation_dart_ids),
        total_score=int(sampled.total_score),
        score_options=tuple(score_options),
        answer_label=str(answer_label),
    )


def _sample_darts_from_slots(
    rng,
    *,
    render_params: DartboardRenderParams,
    selected_slots: Sequence[DartsScoreSlot],
    annotation_flags: Sequence[bool],
) -> DartsSampledScene:
    """Project sampled score slots to visible dart markers."""

    darts: List[DartInstance] = []
    annotation_ids: List[str] = []
    points: List[Tuple[float, float]] = []
    for index, slot in enumerate(selected_slots):
        dart_id = f"dart_{index + 1:02d}"
        x_px, y_px = _sample_position_without_overlap(rng, slot=slot, params=render_params, existing_points=points)
        points.append((float(x_px), float(y_px)))
        is_annotation = bool(annotation_flags[index])
        if is_annotation:
            annotation_ids.append(str(dart_id))
        darts.append(
            DartInstance(
                dart_id=str(dart_id),
                sector_value=None if slot.sector_value is None else int(slot.sector_value),
                ring=str(score_slot_public_ring(slot)),
                score=int(slot.score),
                x_px=float(x_px),
                y_px=float(y_px),
                is_annotation=bool(is_annotation),
            )
        )
    return DartsSampledScene(
        darts=tuple(darts),
        annotation_dart_ids=tuple(annotation_ids),
        total_score=int(sum(int(slot.score) for slot in selected_slots)),
    )


def resolve_score_option_answer_label(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    option_count: int,
) -> str:
    """Resolve the correct score-option label for a total-score task."""

    labels = ("A", "B", "C", "D", "E", "F")[: int(option_count)]
    sampling_index = params.get("_sample_cursor")
    if sampling_index is None:
        label_rng = spawn_rng(int(instance_seed), f"{DARTS_NAMESPACE}.score_option_answer_label")
        return str(labels[int(label_rng.randrange(len(labels)))])
    return str(labels[abs(int(sampling_index)) % len(labels)])


def resolve_darts_render_params(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
    instance_seed: int,
) -> DartboardRenderParams:
    """Resolve darts rendering parameters from config/defaults."""

    canvas_width = int(params.get("canvas_width", group_default(render_defaults, "canvas_width", DEFAULTS.canvas_width)))
    canvas_height = int(params.get("canvas_height", group_default(render_defaults, "canvas_height", DEFAULTS.canvas_height)))
    board_center_x = int(
        params.get("board_center_x_px", group_default(render_defaults, "board_center_x_px", DEFAULTS.board_center_x_px))
    )
    board_center_y = int(
        params.get("board_center_y_px", group_default(render_defaults, "board_center_y_px", DEFAULTS.board_center_y_px))
    )
    board_radius = int(params.get("board_radius_px", group_default(render_defaults, "board_radius_px", DEFAULTS.board_radius_px)))
    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"{DARTS_NAMESPACE}.font_family",
        params=params,
    )
    requested_jitter = resolve_games_layout_jitter(
        params,
        render_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{DARTS_NAMESPACE}.layout",
    )
    _board_bbox, dx, dy, layout_jitter = apply_games_layout_jitter_to_bbox(
        bbox_px=(
            float(board_center_x - board_radius),
            float(board_center_y - board_radius),
            float(board_center_x + board_radius),
            float(board_center_y + board_radius),
        ),
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        jitter=requested_jitter,
    )
    return DartboardRenderParams(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        board_center_x_px=int(round(float(board_center_x + dx))),
        board_center_y_px=int(round(float(board_center_y + dy))),
        board_radius_px=int(board_radius),
        marker_radius_px=int(
            params.get("marker_radius_px", group_default(render_defaults, "marker_radius_px", DEFAULTS.marker_radius_px))
        ),
        number_font_size_px=int(
            params.get("number_font_size_px", group_default(render_defaults, "number_font_size_px", DEFAULTS.number_font_size_px))
        ),
        title_font_size_px=int(
            params.get("title_font_size_px", group_default(render_defaults, "title_font_size_px", DEFAULTS.title_font_size_px))
        ),
        font_family=str(font_family),
        layout_jitter_meta=dict(layout_jitter),
    )


__all__ = [
    "SCORE_SLOTS",
    "build_darts_score_options",
    "feasible_count_support",
    "resolve_darts_count_target_axis",
    "resolve_darts_integer_axis",
    "resolve_darts_render_params",
    "resolve_darts_scene_axes",
    "resolve_darts_target_ring",
    "resolve_darts_target_threshold",
    "resolve_score_option_answer_label",
    "sample_darts_for_count",
    "sample_darts_for_score_options",
    "score_slot_at_least",
    "score_slot_in_ring",
    "score_slot_public_ring",
]
