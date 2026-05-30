"""Games darts task for grounded score and count queries."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.font_assets import get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.support_sampling import resolve_integer_choice, resolve_integer_support
from ..shared.complexity import build_games_darts_score_complexity
from ..shared.darts_scene import (
    DARTBOARD_SAMPLE_RADIUS_FRACTIONS,
    STANDARD_DART_SECTORS,
    DartInstance,
    DartScoreOption,
    DartboardRenderParams,
    polar_to_xy,
    render_darts_scene,
    sample_dart_marker_color,
)
from ..shared.fixed_query_task import FixedQueryVariantTaskMixin, QuerySubsetTaskMixin
from ..shared.layout import apply_games_layout_jitter_to_bbox, resolve_games_layout_jitter
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_id
from ..shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from ..shared.style import SUPPORTED_DARTS_STYLE_VARIANTS
from ..shared.visual_defaults import load_games_noise_defaults


TASK_ID = "games_darts_score_count_base"
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("single_board",)
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "total_score",
    "ring_count",
    "threshold_score_count",
)
SUPPORTED_TARGET_RINGS: Tuple[str, ...] = ("single", "double", "triple", "bull")
SUPPORTED_THRESHOLDS: Tuple[int, ...] = (20, 25, 30, 40, 50)

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


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for visible dartboard scenes."""

    count_target_answer_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    total_score_dart_count_support: Tuple[int, ...] = (1,)
    count_query_dart_count_support: Tuple[int, ...] = (5, 6, 7, 8)
    canvas_width: int = 1040
    canvas_height: int = 980
    board_center_x_px: int = 520
    board_center_y_px: int = 464
    board_radius_px: int = 330
    marker_radius_px: int = 17
    number_font_size_px: int = 36
    title_font_size_px: int = 30


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one darts scene."""

    query_id: str
    scene_variant: str
    style_variant: str
    dart_count: int
    target_answer: int | None
    target_answer_support: Tuple[int, ...] | None
    target_ring: str | None
    target_threshold: int | None
    score_option_answer_label: str | None
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    dart_count_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float] | None


@dataclass(frozen=True)
class _ScoreSlot:
    """One scoring area on the board."""

    sector_value: int | None
    ring: str
    score: int


@dataclass(frozen=True)
class _SampledDartScene:
    """One sampled darts scene with query-specific witness metadata."""

    darts: Tuple[DartInstance, ...]
    evidence_dart_ids: Tuple[str, ...]
    total_score: int
    score_options: Tuple[DartScoreOption, ...] = ()
    answer_label: str | None = None


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "darts")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="darts", apply_prob=0.0)


def _resolve_query_id(*, instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced darts query id."""

    return resolve_games_query_id(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_QUERY_IDS,
    )


def _resolve_named_axis(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    supported: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced named axis for darts."""

    return resolve_games_named_axis(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        namespace=str(namespace),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        supported_variants=[str(item) for item in supported],
    )


def _uses_uniform_query_cycle(params: Mapping[str, Any], probabilities: Mapping[str, float]) -> bool:
    """Return true when the query axis is using the default balanced cycle."""

    if params.get("query_id") is not None or params.get("query_id") is not None:
        return False
    enabled = bool(
        params.get(
            "balanced_query_id_sampling",
            group_default(_GEN_DEFAULTS, "balanced_query_id_sampling", True),
        )
    )
    if not enabled:
        return False
    positives = [float(value) for value in probabilities.values() if float(value) > 0.0]
    if len(positives) != len(SUPPORTED_QUERY_IDS):
        return False
    return max(positives) - min(positives) <= 1e-9


def _params_for_query_occurrence_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    """Use a per-query occurrence index for balanced lower axes."""

    cycle_params = dict(params)
    sampling_index = params.get("_sample_cursor")
    if sampling_index is None:
        return cycle_params
    if not _uses_uniform_query_cycle(params, query_id_probabilities):
        return cycle_params
    cycle_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(SUPPORTED_QUERY_IDS))
    return cycle_params


def _dart_count_support_key(query_id: str) -> str:
    """Return the configured dart-count support key for one query id."""

    return "total_score_dart_count_support" if str(query_id) == "total_score" else "count_query_dart_count_support"


def _feasible_count_support(*, dart_count: int, raw_support: Sequence[int]) -> Tuple[int, ...]:
    """Return answer-count support feasible for the active dart count."""

    return tuple(int(value) for value in raw_support if 0 <= int(value) <= int(dart_count))


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve all semantic and visual axes for one darts scene."""

    query_id, query_id_probabilities = _resolve_query_id(instance_seed=int(instance_seed), params=params)
    cycle_params = _params_for_query_occurrence_cycle(
        params,
        query_id_probabilities=query_id_probabilities,
    )
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=cycle_params,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_DARTS_STYLE_VARIANTS,
    )

    dart_count_support_key = _dart_count_support_key(str(query_id))
    dart_count, dart_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=cycle_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=str(dart_count_support_key),
        explicit_key="dart_count",
        fallback_support=getattr(_DEFAULTS, dart_count_support_key),
        namespace=f"{TASK_ID}.dart_count.{str(query_id)}",
        balanced_flag_key="balanced_dart_count_sampling",
        namespace_support_permutation=True,
    )

    target_answer: int | None = None
    target_answer_support: Tuple[int, ...] | None = None
    target_answer_probabilities: Dict[str, float] | None = None
    if str(query_id) != "total_score":
        raw_support = resolve_integer_support(
            params,
            gen_defaults=_GEN_DEFAULTS,
            key="count_target_answer_support",
            fallback=_DEFAULTS.count_target_answer_support,
        )
        target_answer_support = _feasible_count_support(dart_count=int(dart_count), raw_support=raw_support)
        target_params = dict(cycle_params)
        target_params["count_target_answer_support"] = [int(value) for value in target_answer_support]
        target_answer, target_answer_probabilities = resolve_integer_choice(
            instance_seed=int(instance_seed),
            params=target_params,
            gen_defaults=_GEN_DEFAULTS,
            support_key="count_target_answer_support",
            explicit_key="target_answer",
            fallback_support=target_answer_support,
            namespace=f"{TASK_ID}.target_answer.{str(query_id)}",
            balanced_flag_key="balanced_target_answer_sampling",
            namespace_support_permutation=True,
        )

    target_ring: str | None = None
    target_threshold: int | None = None
    if str(query_id) == "ring_count":
        target_ring, _ = _resolve_named_axis(
            instance_seed=int(instance_seed),
            params=cycle_params,
            namespace="target_ring",
            explicit_key="target_ring",
            weights_key="target_ring_weights",
            balance_flag_key="balanced_target_ring_sampling",
            supported=SUPPORTED_TARGET_RINGS,
        )
    elif str(query_id) == "threshold_score_count":
        support = resolve_integer_support(
            params,
            gen_defaults=_GEN_DEFAULTS,
            key="target_threshold_support",
            fallback=SUPPORTED_THRESHOLDS,
        )
        target_threshold, _ = resolve_integer_choice(
            instance_seed=int(instance_seed),
            params=cycle_params,
            gen_defaults=_GEN_DEFAULTS,
            support_key="target_threshold_support",
            explicit_key="target_threshold",
            fallback_support=support,
            namespace=f"{TASK_ID}.target_threshold",
            balanced_flag_key="balanced_target_threshold_sampling",
            namespace_support_permutation=True,
        )

    score_option_answer_label: str | None = None
    if str(query_id) == "total_score":
        labels = ("A", "B", "C", "D", "E")
        sampling_index = params.get("_sample_cursor")
        if sampling_index is None:
            label_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.score_option_answer_label")
            score_option_answer_label = str(labels[int(label_rng.randrange(len(labels)))])
        else:
            score_option_answer_label = str(labels[abs(int(sampling_index)) % len(labels)])

    return _ResolvedAxes(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        dart_count=int(dart_count),
        target_answer=None if target_answer is None else int(target_answer),
        target_answer_support=None if target_answer_support is None else tuple(int(value) for value in target_answer_support),
        target_ring=None if target_ring is None else str(target_ring),
        target_threshold=None if target_threshold is None else int(target_threshold),
        score_option_answer_label=None if score_option_answer_label is None else str(score_option_answer_label),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        dart_count_probabilities=dict(dart_count_probabilities),
        target_answer_probabilities=None if target_answer_probabilities is None else dict(target_answer_probabilities),
    )


def _all_score_slots() -> Tuple[_ScoreSlot, ...]:
    """Return the supported dart scoring slots."""

    slots: List[_ScoreSlot] = [
        _ScoreSlot(sector_value=None, ring="inner_bull", score=50),
        _ScoreSlot(sector_value=None, ring="outer_bull", score=25),
    ]
    for sector_value in STANDARD_DART_SECTORS:
        slots.extend(
            (
                _ScoreSlot(sector_value=int(sector_value), ring="inner_single", score=int(sector_value)),
                _ScoreSlot(sector_value=int(sector_value), ring="outer_single", score=int(sector_value)),
                _ScoreSlot(sector_value=int(sector_value), ring="triple", score=int(sector_value) * 3),
                _ScoreSlot(sector_value=int(sector_value), ring="double", score=int(sector_value) * 2),
            )
        )
    return tuple(slots)


_SCORE_SLOTS = _all_score_slots()


def _slot_public_ring(slot: _ScoreSlot) -> str:
    """Return the prompt-facing ring family for one slot."""

    return _RING_SCORE_KIND[str(slot.ring)]


def _qualifies(slot: _ScoreSlot, *, axes: _ResolvedAxes) -> bool:
    """Return whether one score slot qualifies for the active count query."""

    if str(axes.query_id) == "total_score":
        return True
    if str(axes.query_id) == "ring_count":
        return str(_slot_public_ring(slot)) == str(axes.target_ring)
    if str(axes.query_id) == "threshold_score_count":
        return int(slot.score) >= int(axes.target_threshold)
    raise ValueError(f"unsupported darts query id: {axes.query_id}")


def _sample_slot(rng, slots: Sequence[_ScoreSlot]) -> _ScoreSlot:
    """Return one random score slot from a non-empty pool."""

    if not slots:
        raise ValueError("cannot sample from an empty dart score-slot pool")
    return slots[int(rng.randrange(len(slots)))]


def _slot_position(rng, *, slot: _ScoreSlot, params: DartboardRenderParams) -> Tuple[float, float]:
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
    slot: _ScoreSlot,
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


def _build_score_options(
    rng,
    *,
    correct_score: int,
    correct_label: str | None,
) -> Tuple[Tuple[DartScoreOption, ...], str]:
    """Return five visible unique score options and the correct option label."""

    labels = ("A", "B", "C", "D", "E")
    resolved_correct_label = str(correct_label) if correct_label in labels else str(labels[0])
    possible_scores = sorted({int(slot.score) for slot in _SCORE_SLOTS})
    distractor_pool = [int(value) for value in possible_scores if int(value) != int(correct_score)]
    nearby_scores = sorted(distractor_pool, key=lambda value: (abs(int(value) - int(correct_score)), int(value)))
    candidate_scores = list(nearby_scores[:14])
    rng.shuffle(candidate_scores)
    selected_scores = [int(value) for value in candidate_scores[:4]]
    if len(set(selected_scores)) != 4 or int(correct_score) in set(selected_scores):
        raise RuntimeError("failed to construct five unique darts score options")
    rng.shuffle(selected_scores)
    distractor_by_label = dict(zip([label for label in labels if label != resolved_correct_label], selected_scores[:4]))
    options = tuple(
        DartScoreOption(
            label=str(label),
            score=int(correct_score) if str(label) == resolved_correct_label else int(distractor_by_label[str(label)]),
            is_answer=bool(str(label) == resolved_correct_label),
        )
        for label in labels
    )
    return options, str(resolved_correct_label)


def _sample_scene(
    rng,
    *,
    axes: _ResolvedAxes,
    render_params: DartboardRenderParams,
) -> _SampledDartScene:
    """Sample one dartboard scene with exact query support where needed."""

    if str(axes.query_id) == "total_score":
        selected_slots = [_sample_slot(rng, _SCORE_SLOTS) for _ in range(int(axes.dart_count))]
        evidence_flags = [True for _ in selected_slots]
    else:
        target_answer = int(axes.target_answer or 0)
        qualifying_pool = [slot for slot in _SCORE_SLOTS if _qualifies(slot, axes=axes)]
        nonqualifying_pool = [slot for slot in _SCORE_SLOTS if not _qualifies(slot, axes=axes)]
        selected_slots = [
            _sample_slot(rng, qualifying_pool) for _ in range(int(target_answer))
        ] + [
            _sample_slot(rng, nonqualifying_pool) for _ in range(max(0, int(axes.dart_count) - int(target_answer)))
        ]
        evidence_flags = [True for _ in range(int(target_answer))] + [
            False for _ in range(max(0, int(axes.dart_count) - int(target_answer)))
        ]
        combined = list(zip(selected_slots, evidence_flags))
        rng.shuffle(combined)
        selected_slots = [slot for slot, _ in combined]
        evidence_flags = [flag for _, flag in combined]

    darts: List[DartInstance] = []
    evidence_ids: List[str] = []
    points: List[Tuple[float, float]] = []
    for index, slot in enumerate(selected_slots):
        dart_id = f"dart_{index + 1:02d}"
        x_px, y_px = _sample_position_without_overlap(rng, slot=slot, params=render_params, existing_points=points)
        points.append((float(x_px), float(y_px)))
        is_evidence = bool(evidence_flags[index])
        if is_evidence:
            evidence_ids.append(str(dart_id))
        darts.append(
            DartInstance(
                dart_id=str(dart_id),
                sector_value=None if slot.sector_value is None else int(slot.sector_value),
                ring=str(_slot_public_ring(slot)),
                score=int(slot.score),
                x_px=float(x_px),
                y_px=float(y_px),
                is_evidence=bool(is_evidence),
            )
        )
    total_score = int(sum(int(slot.score) for slot in selected_slots))
    score_options: Tuple[DartScoreOption, ...] = ()
    answer_label: str | None = None
    if str(axes.query_id) == "total_score":
        score_options, answer_label = _build_score_options(
            rng,
            correct_score=int(total_score),
            correct_label=axes.score_option_answer_label,
        )

    return _SampledDartScene(
        darts=tuple(darts),
        evidence_dart_ids=tuple(evidence_ids),
        total_score=int(total_score),
        score_options=tuple(score_options),
        answer_label=None if answer_label is None else str(answer_label),
    )


def _build_prompt_json_examples(*, query_id: str) -> Tuple[str, str]:
    """Return prompt JSON examples matching the active darts query semantics."""

    if str(query_id) == "total_score":
        answer_and_evidence = {"evidence": [[411, 219]], "answer": "C"}
        answer_only = {"answer": "C"}
    else:
        answer_and_evidence = {"evidence": [[411, 219], [525, 364]], "answer": 2}
        answer_only = {"answer": 2}
    return (
        json.dumps(answer_and_evidence, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
        json.dumps(answer_only, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
    )


def _target_ring_prompt_text(target_ring: str | None) -> str:
    """Return natural prompt text for one target dartboard ring family."""

    if target_ring is None:
        return ""
    return {
        "single": "single area",
        "double": "double ring",
        "triple": "triple ring",
        "bull": "bull area",
    }.get(str(target_ring), str(target_ring).replace("_", " "))


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> DartboardRenderParams:
    """Resolve darts rendering parameters from config/defaults."""

    canvas_width = int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width)))
    canvas_height = int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height)))
    board_center_x = int(
        params.get("board_center_x_px", group_default(_RENDER_DEFAULTS, "board_center_x_px", _DEFAULTS.board_center_x_px))
    )
    board_center_y = int(
        params.get("board_center_y_px", group_default(_RENDER_DEFAULTS, "board_center_y_px", _DEFAULTS.board_center_y_px))
    )
    board_radius = int(params.get("board_radius_px", group_default(_RENDER_DEFAULTS, "board_radius_px", _DEFAULTS.board_radius_px)))
    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace="games.darts.font_family",
        params=params,
    )
    requested_jitter = resolve_games_layout_jitter(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="games.darts.layout",
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
            params.get("marker_radius_px", group_default(_RENDER_DEFAULTS, "marker_radius_px", _DEFAULTS.marker_radius_px))
        ),
        number_font_size_px=int(
            params.get("number_font_size_px", group_default(_RENDER_DEFAULTS, "number_font_size_px", _DEFAULTS.number_font_size_px))
        ),
        title_font_size_px=int(
            params.get("title_font_size_px", group_default(_RENDER_DEFAULTS, "title_font_size_px", _DEFAULTS.title_font_size_px))
        ),
        font_family=str(font_family),
        layout_jitter_meta=dict(layout_jitter),
    )


class GamesDartsScoreCountTask:
    """Return one grounded score/count query over a visible dartboard."""

    task_id = TASK_ID
    domain = "games"
    task_group = "darts"
    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        render_params = _render_params(params, instance_seed=int(instance_seed))
        allowed_panel_treatments_raw = params.get(
            "panel_scene_treatments",
            group_default(_RENDER_DEFAULTS, "panel_scene_treatments", None),
        )
        if isinstance(allowed_panel_treatments_raw, str):
            allowed_panel_treatments = (str(allowed_panel_treatments_raw),)
        elif allowed_panel_treatments_raw is None:
            allowed_panel_treatments = None
        else:
            allowed_panel_treatments = tuple(str(item) for item in allowed_panel_treatments_raw)
        panel_style, panel_style_meta = resolve_game_panel_scene_style(
            instance_seed=int(instance_seed),
            namespace="games.darts.panel_scene_style",
            treatments=allowed_panel_treatments,
            treatment_weights=params.get(
                "panel_scene_treatment_weights",
                group_default(_RENDER_DEFAULTS, "panel_scene_treatment_weights", None),
            ),
            palette_weights=params.get(
                "panel_scene_palette_weights",
                group_default(_RENDER_DEFAULTS, "panel_scene_palette_weights", None),
            ),
        )
        color_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dart_color")
        dart_fill_color, dart_fill_min_lab_distance = sample_dart_marker_color(
            color_rng,
            style_variant=str(axes.style_variant),
            min_lab_distance=40.0,
        )

        sampled_scene: _SampledDartScene | None = None
        rendered_scene = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            sampled_scene = _sample_scene(attempt_rng, axes=axes, render_params=render_params)
            background, background_meta = make_panel_scene_background(
                canvas_width=int(render_params.canvas_width),
                canvas_height=int(render_params.canvas_height),
                style=panel_style,
            )
            rendered_scene = render_darts_scene(
                darts=list(sampled_scene.darts),
                background=background,
                style_variant=str(axes.style_variant),
                params=render_params,
                target_ring=str(axes.target_ring) if str(axes.query_id) == "ring_count" else None,
                dart_fill_color=dart_fill_color,
                dart_fill_min_lab_distance=float(dart_fill_min_lab_distance),
                score_options=tuple(sampled_scene.score_options),
                panel_style=panel_style,
            )
            break
        if sampled_scene is None or rendered_scene is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts")

        is_total_score = str(axes.query_id) == "total_score"
        answer_value: int | str = str(sampled_scene.answer_label) if is_total_score else int(axes.target_answer or 0)
        numeric_target_answer = int(sampled_scene.total_score) if is_total_score else int(axes.target_answer or 0)
        evidence_entity_ids = [str(dart_id) for dart_id in sampled_scene.evidence_dart_ids]
        evidence_bboxes = [
            list(rendered_scene.render_map["dart_bboxes_px"][str(dart_id)])
            for dart_id in sampled_scene.evidence_dart_ids
        ]
        evidence_points = [
            list(rendered_scene.render_map["dart_centers_px"][str(dart_id)])
            for dart_id in sampled_scene.evidence_dart_ids
        ]
        if is_total_score and sampled_scene.answer_label is None:
            raise RuntimeError("total_score scene missing answer option label")
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
                "object_description_single_board",
                "scoring_rule_text",
                "ring_rule_text",
                "answer_hint_total_score",
                "answer_hint_ring_count",
                "answer_hint_threshold_score_count",
                "evidence_hint_total_score",
                "evidence_hint_ring_count",
                "evidence_hint_threshold_score_count",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples(query_id=str(axes.query_id))
        prompt_slots = {
            "object_description": str(prompt_defaults[f"object_description_{str(axes.scene_variant)}"]),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_id)}"]),
            "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(axes.query_id)}"]),
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
            "scoring_rule_text": str(prompt_defaults["scoring_rule_text"]),
            "ring_rule_text": str(prompt_defaults["ring_rule_text"]),
            "target_ring_text": _target_ring_prompt_text(axes.target_ring),
            "target_threshold_text": "" if axes.target_threshold is None else str(axes.target_threshold),
        }
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(axes.query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots=prompt_slots,
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(
            type="string" if is_total_score else "integer",
            value=str(answer_value) if is_total_score else int(answer_value),
        )
        evidence_gt = TypedValue(type="point_set", value=[list(point) for point in evidence_points])
        text_style_meta = {
            "font_family": str(render_params.font_family),
            "font_asset": get_font_family_record(str(render_params.font_family)).to_trace(),
        }
        complexity = build_games_darts_score_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=TASK_ID,
            scene_variant=str(axes.scene_variant),
            query_id=str(axes.query_id),
            dart_count=int(axes.dart_count),
            target_answer=int(numeric_target_answer),
            evidence_count=len(evidence_entity_ids),
        )

        dart_specs = [
            {
                "dart_id": str(dart.dart_id),
                "sector_value": None if dart.sector_value is None else int(dart.sector_value),
                "ring": str(dart.ring),
                "score": int(dart.score),
                "is_evidence": bool(dart.is_evidence),
            }
            for dart in sampled_scene.darts
        ]
        score_options = [
            {
                "label": str(option.label),
                "score": int(option.score),
                "is_answer": bool(option.is_answer),
            }
            for option in sampled_scene.score_options
        ]
        execution_trace = {
            "scene_variant": str(axes.scene_variant),
            "query_id": str(axes.query_id),
            "style_variant": str(axes.style_variant),
            "dart_count": int(axes.dart_count),
            "target_answer": int(numeric_target_answer),
            "answer_label": None if sampled_scene.answer_label is None else str(sampled_scene.answer_label),
            "target_answer_support": None if axes.target_answer_support is None else [int(value) for value in axes.target_answer_support],
            "target_ring": None if axes.target_ring is None else str(axes.target_ring),
            "target_threshold": None if axes.target_threshold is None else int(axes.target_threshold),
            "total_score": int(sampled_scene.total_score),
            "score_options": list(score_options),
            "dart_fill_color": [int(v) for v in dart_fill_color],
            "dart_fill_min_lab_distance": round(float(dart_fill_min_lab_distance), 3),
            "dart_specs": list(dart_specs),
            "evidence_entity_ids": list(evidence_entity_ids),
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_darts_{str(axes.scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "style_variant": str(axes.style_variant),
                    "dart_count": int(axes.dart_count),
                    "target_answer": int(numeric_target_answer),
                    "answer_label": None if sampled_scene.answer_label is None else str(sampled_scene.answer_label),
                    "evidence_entity_ids": list(evidence_entity_ids),
                },
            },
            "query_spec": {
                "query_id": str(axes.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "style_variant": str(axes.style_variant),
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "dart_count": int(axes.dart_count),
                    "dart_count_probabilities": dict(axes.dart_count_probabilities),
                    "target_answer": int(numeric_target_answer),
                    "answer_label": None if sampled_scene.answer_label is None else str(sampled_scene.answer_label),
                    "score_options": list(score_options),
                    "target_answer_support": None if axes.target_answer_support is None else [int(value) for value in axes.target_answer_support],
                    "target_answer_probabilities": None
                    if axes.target_answer_probabilities is None
                    else dict(axes.target_answer_probabilities),
                    "target_ring": None if axes.target_ring is None else str(axes.target_ring),
                    "target_threshold": None if axes.target_threshold is None else int(axes.target_threshold),
                },
            },
            "render_spec": {
                "scene_variant": str(axes.scene_variant),
                "style_variant": str(axes.style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "dart_fill_color": [int(v) for v in dart_fill_color],
                "dart_fill_min_lab_distance": round(float(dart_fill_min_lab_distance), 3),
                "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
                "panel_scene_style": dict(panel_style_meta),
                "text_style": dict(text_style_meta),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": execution_trace,
            "witness_symbolic": {
                "type": "object_set",
                "ids": list(evidence_entity_ids),
            },
            "projected_evidence": {
                "type": "point_set",
                "point_set": [list(point) for point in evidence_points],
                "pixel_point_set": [list(point) for point in evidence_points],
                "pixel_bbox_set": [list(bbox) for bbox in evidence_bboxes],
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
            query_id=str(axes.query_id),
            scene_id="darts",
        )


@register_task
class GamesDartsTotalScoreTask(FixedQueryVariantTaskMixin, GamesDartsScoreCountTask):
    """Return the score of the shown dart throw."""

    task_id = "task_games__darts__total_score_option_label"
    fixed_query_id = "total_score"


@register_task
class GamesDartsConditionCountTask(QuerySubsetTaskMixin, GamesDartsScoreCountTask):
    """Count darts matching one sampled scoring condition."""

    task_id = "task_games__darts__condition_count"
    supported_query_ids = (
        "ring_count",
        "threshold_score_count",
    )


__all__ = [
    "GamesDartsConditionCountTask",
    "GamesDartsTotalScoreTask",
]
