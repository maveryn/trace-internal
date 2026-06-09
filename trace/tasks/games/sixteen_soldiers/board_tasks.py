"""Sixteen Soldiers line-movement tasks for the games domain."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.support_sampling import resolve_integer_choice, resolve_integer_support
from ..shared.complexity import build_games_complexity, normalize_linear, resolve_games_complexity_weights
from ..shared.fixed_query_task import FixedQueryVariantTaskMixin
from ..shared.layout import attach_games_unit_size_jitter, resolve_games_layout_jitter, resolve_games_unit_size_scale, scale_games_px
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_id
from ..shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from ..shared.sixteen_soldiers_common import (
    BLUE,
    EMPTY,
    JUMP_SPECS,
    NEIGHBORS,
    RED,
    SUPPORTED_SIXTEEN_SOLDIERS_QUERY_IDS,
    SUPPORTED_SIXTEEN_SOLDIERS_SCENE_VARIANTS,
    SUPPORTED_SIXTEEN_SOLDIERS_STYLE_VARIANTS,
    Board,
    JumpSpec,
    PointId,
    SixteenSoldiersSample,
    all_point_ids,
    board_to_dict,
    capturable_opponent_points,
    capture_lines,
    freeze_board,
    jump_specs_from,
    legal_destinations,
    opponent,
    piece_to_entity_id,
    player_name,
    point_coord,
    validate_sixteen_soldiers_sample,
    visible_board_trace,
)
from ..shared.sixteen_soldiers_scene import SixteenSoldiersRenderParams, render_sixteen_soldiers_scene
from ..shared.visual_defaults import load_games_noise_defaults


TASK_ID = "games_sixteen_soldiers_base"
MARKED_DESTINATION_TASK_ID = "task_games__sixteen_soldiers__marked_piece_destination_count"
MARKED_CAPTURE_TASK_ID = "task_games__sixteen_soldiers__marked_piece_capture_count"
MARKED_DESTINATION_QUERY_ID = "marked_piece_destination_count"
MARKED_CAPTURE_QUERY_ID = "marked_piece_capture_count"


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for Sixteen Soldiers scenes."""

    marked_piece_destination_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6)
    marked_piece_capture_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4)
    piece_count_per_side_support: Tuple[int, ...] = (8, 9, 10, 11, 12, 13, 14)
    canvas_width: int = 760
    canvas_height: int = 900
    panel_margin_px: int = 52
    max_board_width_px: int = 500
    max_board_height_px: int = 680
    edge_width_px: int = 5
    point_radius_px: int = 8
    piece_radius_px: int = 21
    marker_width_px: int = 5
    dynamic_canvas_size_enabled: bool = True
    canvas_min_width_px: int = 560
    canvas_min_height_px: int = 760
    canvas_side_padding_px: int = 168
    canvas_vertical_padding_px: int = 136


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one Sixteen Soldiers instance."""

    query_id: str
    scene_variant: str
    style_variant: str
    target_answer: int
    target_answer_support: Tuple[int, ...]
    marked_piece_color: int
    piece_count_per_side: int
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]
    marked_piece_color_probabilities: Dict[str, float]
    piece_count_per_side_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "sixteen_soldiers")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="sixteen_soldiers", apply_prob=0.5)


def _resolve_query_id(*, instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced internal Sixteen Soldiers query id."""

    return resolve_games_query_id(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_SIXTEEN_SOLDIERS_QUERY_IDS,
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
    """Resolve one balanced named axis."""

    return resolve_games_named_axis(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        namespace=str(namespace),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        supported_variants=tuple(str(value) for value in supported),
    )


def _resolve_marked_piece_color(*, instance_seed: int, params: Mapping[str, Any]) -> Tuple[int, Dict[str, float]]:
    """Resolve red/blue color for the marked piece."""

    color_name, probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="marked_piece_color",
        explicit_key="marked_piece_color",
        weights_key="marked_piece_color_weights",
        balance_flag_key="balanced_marked_piece_color_sampling",
        supported=("red", "blue"),
    )
    return (RED if str(color_name) == "red" else BLUE), dict(probabilities)


def _target_support_key(query_id: str) -> str:
    """Return configured answer-support key for one query id."""

    if str(query_id) == MARKED_CAPTURE_QUERY_ID:
        return "marked_piece_capture_count_support"
    return "marked_piece_destination_count_support"


def _target_support_fallback(query_id: str) -> Tuple[int, ...]:
    """Return fallback answer support for one query id."""

    if str(query_id) == MARKED_CAPTURE_QUERY_ID:
        return _DEFAULTS.marked_piece_capture_count_support
    return _DEFAULTS.marked_piece_destination_count_support


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve semantic and visual axes for one instance."""

    query_id, query_id_probabilities = _resolve_query_id(instance_seed=int(instance_seed), params=params)
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_SIXTEEN_SOLDIERS_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_SIXTEEN_SOLDIERS_STYLE_VARIANTS,
    )
    target_answer, target_answer_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=_target_support_key(str(query_id)),
        explicit_key="target_answer",
        fallback_support=_target_support_fallback(str(query_id)),
        namespace=f"{TASK_ID}.{str(query_id)}.target_answer",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_support_permutation=True,
    )
    target_answer_support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key=_target_support_key(str(query_id)),
        fallback=_target_support_fallback(str(query_id)),
    )
    marked_piece_color, marked_piece_color_probabilities = _resolve_marked_piece_color(
        instance_seed=int(instance_seed),
        params=params,
    )
    piece_count_per_side, piece_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="piece_count_per_side_support",
        explicit_key="piece_count_per_side",
        fallback_support=_DEFAULTS.piece_count_per_side_support,
        namespace=f"{TASK_ID}.piece_count_per_side",
        balanced_flag_key="balanced_piece_count_per_side_sampling",
        namespace_support_permutation=True,
    )
    return _ResolvedAxes(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        target_answer=int(target_answer),
        target_answer_support=tuple(int(value) for value in target_answer_support),
        marked_piece_color=int(marked_piece_color),
        piece_count_per_side=int(piece_count_per_side),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
        marked_piece_color_probabilities=dict(marked_piece_color_probabilities),
        piece_count_per_side_probabilities=dict(piece_count_probabilities),
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> SixteenSoldiersRenderParams:
    """Resolve render parameters from config/defaults."""

    unit_scale, unit_scale_meta = resolve_games_unit_size_scale(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="games.sixteen_soldiers.unit_size",
    )
    layout_jitter = attach_games_unit_size_jitter(
        resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.sixteen_soldiers.layout",
        ),
        unit_scale_meta,
    )
    base_canvas_width = int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width)))
    base_canvas_height = int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height)))
    max_board_width_px = scale_games_px(
        params.get("max_board_width_px", group_default(_RENDER_DEFAULTS, "max_board_width_px", _DEFAULTS.max_board_width_px)),
        unit_scale,
        min_px=280,
    )
    max_board_height_px = scale_games_px(
        params.get("max_board_height_px", group_default(_RENDER_DEFAULTS, "max_board_height_px", _DEFAULTS.max_board_height_px)),
        unit_scale,
        min_px=520,
    )
    dynamic_canvas_enabled = bool(
        params.get(
            "dynamic_canvas_size_enabled",
            group_default(_RENDER_DEFAULTS, "dynamic_canvas_size_enabled", _DEFAULTS.dynamic_canvas_size_enabled),
        )
    )
    canvas_width = int(base_canvas_width)
    canvas_height = int(base_canvas_height)
    if dynamic_canvas_enabled and params.get("canvas_width") is None:
        canvas_width = min(
            int(base_canvas_width),
            max(
                int(params.get("canvas_min_width_px", group_default(_RENDER_DEFAULTS, "canvas_min_width_px", _DEFAULTS.canvas_min_width_px))),
                int(
                    round(
                        float(max_board_width_px)
                        + (
                            2.0
                            * float(
                                params.get(
                                    "canvas_side_padding_px",
                                    group_default(_RENDER_DEFAULTS, "canvas_side_padding_px", _DEFAULTS.canvas_side_padding_px),
                                )
                            )
                        )
                    )
                ),
            ),
        )
    if dynamic_canvas_enabled and params.get("canvas_height") is None:
        canvas_height = min(
            int(base_canvas_height),
            max(
                int(params.get("canvas_min_height_px", group_default(_RENDER_DEFAULTS, "canvas_min_height_px", _DEFAULTS.canvas_min_height_px))),
                int(
                    round(
                        float(max_board_height_px)
                        + (
                            2.0
                            * float(
                                params.get(
                                    "canvas_vertical_padding_px",
                                    group_default(_RENDER_DEFAULTS, "canvas_vertical_padding_px", _DEFAULTS.canvas_vertical_padding_px),
                                )
                            )
                        )
                    )
                ),
            ),
        )
    return SixteenSoldiersRenderParams(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        panel_margin_px=int(params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px))),
        max_board_width_px=int(max_board_width_px),
        max_board_height_px=int(max_board_height_px),
        edge_width_px=scale_games_px(params.get("edge_width_px", group_default(_RENDER_DEFAULTS, "edge_width_px", _DEFAULTS.edge_width_px)), unit_scale, min_px=2),
        point_radius_px=scale_games_px(params.get("point_radius_px", group_default(_RENDER_DEFAULTS, "point_radius_px", _DEFAULTS.point_radius_px)), unit_scale, min_px=4),
        piece_radius_px=scale_games_px(params.get("piece_radius_px", group_default(_RENDER_DEFAULTS, "piece_radius_px", _DEFAULTS.piece_radius_px)), unit_scale, min_px=13),
        marker_width_px=scale_games_px(params.get("marker_width_px", group_default(_RENDER_DEFAULTS, "marker_width_px", _DEFAULTS.marker_width_px)), unit_scale, min_px=3),
        layout_jitter_meta=layout_jitter,
        instance_seed=int(instance_seed),
    )


def _marked_candidate_points(scene_variant: str) -> Tuple[PointId, ...]:
    """Return preferred marked-piece points for one scene variant."""

    all_points = all_point_ids()
    if str(scene_variant) == "center_crossroads_midgame":
        candidates = [
            point_id
            for point_id in all_points
            if 2 <= int(point_coord(point_id)[0]) <= 6
            and 1 <= int(point_coord(point_id)[1]) <= 3
            and len(NEIGHBORS[str(point_id)]) >= 5
        ]
        return tuple(candidates) or all_points
    if str(scene_variant) == "triangle_wing_midgame":
        candidates = [
            point_id
            for point_id in all_points
            if int(point_coord(point_id)[0]) in {0, 1, 2, 6, 7, 8}
        ]
        return tuple(candidates) or all_points
    return all_points


def _build_board_from_values(values: Mapping[PointId, int]) -> Board:
    """Build a frozen board from point values."""

    return freeze_board({point_id: int(values.get(point_id, EMPTY)) for point_id in all_point_ids()})


def _fill_board_to_piece_counts(
    *,
    rng: Any,
    forced_values: Mapping[PointId, int],
    piece_count_per_side: int,
) -> Board | None:
    """Fill unspecified points while preserving forced local values."""

    values = {point_id: EMPTY for point_id in all_point_ids()}
    for point_id, value in forced_values.items():
        values[str(point_id)] = int(value)
    red_count = sum(1 for value in values.values() if int(value) == RED)
    blue_count = sum(1 for value in values.values() if int(value) == BLUE)
    if red_count > int(piece_count_per_side) or blue_count > int(piece_count_per_side):
        return None

    fillable = [
        point_id
        for point_id in all_point_ids()
        if str(point_id) not in forced_values
    ]
    rng.shuffle(fillable)
    while red_count < int(piece_count_per_side) and fillable:
        point_id = str(fillable.pop())
        values[point_id] = RED
        red_count += 1
    while blue_count < int(piece_count_per_side) and fillable:
        point_id = str(fillable.pop())
        values[point_id] = BLUE
        blue_count += 1
    if red_count != int(piece_count_per_side) or blue_count != int(piece_count_per_side):
        return None
    return _build_board_from_values(values)


def _try_sample_marked_destination_scene(*, rng: Any, axes: _ResolvedAxes) -> SixteenSoldiersSample:
    """Construct a board where the marked piece has exactly target destinations."""

    target = int(axes.target_answer)
    target_color = int(axes.marked_piece_color)
    candidates = [
        point_id
        for point_id in _marked_candidate_points(str(axes.scene_variant))
        if len(NEIGHBORS[str(point_id)]) >= target
    ]
    rng.shuffle(candidates)
    for marked_point_id in candidates:
        neighbors = list(NEIGHBORS[str(marked_point_id)])
        rng.shuffle(neighbors)
        empty_destinations = set(neighbors[:target])
        forced: dict[PointId, int] = {str(marked_point_id): target_color}
        for blocker in neighbors[target:]:
            red_remaining = int(axes.piece_count_per_side) - sum(1 for value in forced.values() if int(value) == RED)
            blue_remaining = int(axes.piece_count_per_side) - sum(1 for value in forced.values() if int(value) == BLUE)
            if red_remaining <= 0 and blue_remaining <= 0:
                break
            if red_remaining <= 0:
                forced[str(blocker)] = BLUE
            elif blue_remaining <= 0:
                forced[str(blocker)] = RED
            elif rng.random() < 0.5:
                forced[str(blocker)] = RED
            else:
                forced[str(blocker)] = BLUE
        for destination in empty_destinations:
            forced[str(destination)] = EMPTY

        board = _fill_board_to_piece_counts(
            rng=rng,
            forced_values=forced,
            piece_count_per_side=int(axes.piece_count_per_side),
        )
        if board is None:
            continue
        annotation = tuple(sorted(legal_destinations(board, marked_point_id), key=lambda point_id: point_coord(point_id)))
        if len(annotation) != target:
            continue
        sample = SixteenSoldiersSample(
            query_id=str(axes.query_id),
            scene_variant=str(axes.scene_variant),
            style_variant=str(axes.style_variant),
            board=board,
            answer=int(len(annotation)),
            target_answer=int(target),
            annotation_point_ids=tuple(annotation),
            target_color=int(target_color),
            marked_point_id=str(marked_point_id),
            construction_mode="marked_piece_adjacent_destination_template",
        )
        validate_sixteen_soldiers_sample(sample)
        return sample
    raise ValueError("failed to construct marked-destination Sixteen Soldiers scene")


def _select_capture_specs(
    *,
    rng: Any,
    specs: Sequence[JumpSpec],
    target: int,
) -> Tuple[JumpSpec, ...] | None:
    """Select target capture lines with unique opponent and landing points."""

    if int(target) == 0:
        return tuple()
    shuffled = list(specs)
    rng.shuffle(shuffled)
    selected: list[JumpSpec] = []
    used_middles: set[PointId] = set()
    used_landings: set[PointId] = set()
    for spec in shuffled:
        if spec.middle_id in used_middles or spec.landing_id in used_landings:
            continue
        selected.append(spec)
        used_middles.add(spec.middle_id)
        used_landings.add(spec.landing_id)
        if len(selected) == int(target):
            return tuple(selected)
    return None


def _try_sample_marked_capture_scene(*, rng: Any, axes: _ResolvedAxes) -> SixteenSoldiersSample:
    """Construct a board where the marked piece has exactly target captures."""

    target = int(axes.target_answer)
    target_color = int(axes.marked_piece_color)
    opponent_color = opponent(target_color)
    candidates = [
        point_id
        for point_id in _marked_candidate_points(str(axes.scene_variant))
        if len(jump_specs_from(point_id)) >= target
    ]
    rng.shuffle(candidates)
    for marked_point_id in candidates:
        candidate_specs = list(jump_specs_from(marked_point_id))
        selected_specs = _select_capture_specs(rng=rng, specs=candidate_specs, target=target)
        if selected_specs is None:
            continue

        forced: dict[PointId, int] = {str(marked_point_id): target_color}
        selected_middles = {spec.middle_id for spec in selected_specs}
        selected_landings = {spec.landing_id for spec in selected_specs}
        for spec in selected_specs:
            forced[str(spec.middle_id)] = opponent_color
            forced[str(spec.landing_id)] = EMPTY

        conflict = False
        for spec in candidate_specs:
            if spec in selected_specs:
                continue
            if spec.middle_id in selected_middles:
                if forced.get(str(spec.landing_id), None) == EMPTY:
                    conflict = True
                    break
                forced.setdefault(str(spec.landing_id), target_color)
            elif spec.landing_id in selected_landings:
                if forced.get(str(spec.middle_id), None) == opponent_color:
                    conflict = True
                    break
                forced.setdefault(str(spec.middle_id), target_color)
            else:
                forced.setdefault(str(spec.middle_id), target_color)
        if conflict:
            continue

        board = _fill_board_to_piece_counts(
            rng=rng,
            forced_values=forced,
            piece_count_per_side=int(axes.piece_count_per_side),
        )
        if board is None:
            continue
        annotation = tuple(sorted(capturable_opponent_points(board, marked_point_id), key=lambda point_id: point_coord(point_id)))
        if len(annotation) != target:
            continue
        sample = SixteenSoldiersSample(
            query_id=str(axes.query_id),
            scene_variant=str(axes.scene_variant),
            style_variant=str(axes.style_variant),
            board=board,
            answer=int(len(annotation)),
            target_answer=int(target),
            annotation_point_ids=tuple(annotation),
            target_color=int(target_color),
            marked_point_id=str(marked_point_id),
            construction_mode="marked_piece_immediate_capture_template",
        )
        validate_sixteen_soldiers_sample(sample)
        return sample
    raise ValueError("failed to construct marked-capture Sixteen Soldiers scene")


def _sample_scene(*, rng: Any, axes: _ResolvedAxes) -> SixteenSoldiersSample:
    """Construct one scene for the resolved axes."""

    if str(axes.query_id) == MARKED_CAPTURE_QUERY_ID:
        return _try_sample_marked_capture_scene(rng=rng, axes=axes)
    return _try_sample_marked_destination_scene(rng=rng, axes=axes)


def _build_prompt_json_examples() -> Tuple[str, str]:
    """Return deterministic JSON examples for prompt templates."""

    answer = 2
    annotation = [[180.0, 220.0], [268.0, 308.0]]
    return (
        json.dumps({"annotation": annotation, "answer": answer}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer}, separators=(",", ":"), ensure_ascii=False),
    )


def _build_complexity(*, query_id: str, target_answer: int, annotation_count: int) -> Any:
    """Build normalized complexity for Sixteen Soldiers counting tasks."""

    weights = resolve_games_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
    movement_reasoning = 0.52 if str(query_id) == MARKED_DESTINATION_QUERY_ID else 0.68
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": 0.62,
            "movement_reasoning": float(movement_reasoning),
            "ambiguity": normalize_linear(float(target_answer), min_value=0.0, max_value=6.0),
            "output_burden": normalize_linear(float(annotation_count), min_value=0.0, max_value=6.0),
        },
    )


class GamesSixteenSoldiersTask:
    """Generate one grounded Sixteen Soldiers line-movement query."""

    task_id = TASK_ID
    domain = "games"
    task_group = "sixteen_soldiers"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        render_params = _render_params(params, instance_seed=int(instance_seed))

        sampled_scene: SixteenSoldiersSample | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sampled_scene = _sample_scene(rng=attempt_rng, axes=axes)
            except ValueError:
                continue
            break
        if sampled_scene is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts")

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
            namespace="games.sixteen_soldiers.panel_scene_style",
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
        background, background_meta = make_panel_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=panel_style,
        )
        rendered_scene = render_sixteen_soldiers_scene(
            board=sampled_scene.board,
            background=background,
            style_variant=str(axes.style_variant),
            params=render_params,
            marked_point_id=str(sampled_scene.marked_point_id),
            panel_style=panel_style,
        )

        if str(sampled_scene.query_id) == MARKED_DESTINATION_QUERY_ID:
            annotation_entity_ids = tuple(str(point_id) for point_id in sampled_scene.annotation_point_ids)
            annotation_points = [
                list(rendered_scene.render_map["point_centers_px"][entity_id])
                for entity_id in annotation_entity_ids
            ]
            annotation_symbolic_type = "empty_destination_point"
        else:
            annotation_entity_ids = tuple(piece_to_entity_id(point_id) for point_id in sampled_scene.annotation_point_ids)
            annotation_points = [
                list(rendered_scene.render_map["piece_centers_px"][entity_id])
                for entity_id in annotation_entity_ids
            ]
            annotation_symbolic_type = "capturable_opponent_piece"

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
                "object_description_balanced_midgame",
                "object_description_center_crossroads_midgame",
                "object_description_triangle_wing_midgame",
                "move_rule_text",
                "capture_rule_text",
                "answer_hint_marked_piece_destination_count",
                "answer_hint_marked_piece_capture_count",
                "annotation_hint_marked_piece_destination_count",
                "annotation_hint_marked_piece_capture_count",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples()
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(axes.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults[f"object_description_{str(axes.scene_variant)}"]),
                "move_rule_text": str(prompt_defaults["move_rule_text"]),
                "capture_rule_text": str(prompt_defaults["capture_rule_text"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_id)}"]),
                "annotation_hint": str(prompt_defaults[f"annotation_hint_{str(axes.query_id)}"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(sampled_scene.answer))
        annotation_gt = TypedValue(type="point_set", value=[list(point) for point in annotation_points])
        complexity = _build_complexity(
            query_id=str(axes.query_id),
            target_answer=int(sampled_scene.answer),
            annotation_count=len(annotation_entity_ids),
        )

        values = board_to_dict(sampled_scene.board)
        marked_capture_lines = capture_lines(sampled_scene.board, sampled_scene.marked_point_id)
        trace_payload = {
            "scene_ir": {
                "scene_kind": "games_sixteen_soldiers_board",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "style_variant": str(axes.style_variant),
                    "target_answer": int(sampled_scene.answer),
                    "target_color": player_name(int(sampled_scene.target_color)),
                    "marked_point_id": str(sampled_scene.marked_point_id),
                    "annotation_entity_ids": [str(entity_id) for entity_id in annotation_entity_ids],
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
                    "target_answer": int(sampled_scene.answer),
                    "target_answer_support": [int(value) for value in axes.target_answer_support],
                    "target_answer_probabilities": dict(axes.target_answer_probabilities),
                    "marked_piece_color": player_name(int(axes.marked_piece_color)),
                    "marked_piece_color_probabilities": dict(axes.marked_piece_color_probabilities),
                    "piece_count_per_side": int(axes.piece_count_per_side),
                    "piece_count_per_side_probabilities": dict(axes.piece_count_per_side_probabilities),
                },
            },
            "render_spec": {
                "scene_variant": str(axes.scene_variant),
                "style_variant": str(axes.style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
                "panel_scene_style": dict(panel_style_meta),
                "effective_board_height_px": float(rendered_scene.render_map["board_bbox_px"][3])
                - float(rendered_scene.render_map["board_bbox_px"][1]),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(axes.scene_variant),
                "query_id": str(axes.query_id),
                "style_variant": str(axes.style_variant),
                "point_values": [
                    {
                        "point_id": str(point_id),
                        "coord": [int(value) for value in point_coord(point_id)],
                        "state": "empty"
                        if int(values[point_id]) == EMPTY
                        else "red"
                        if int(values[point_id]) == RED
                        else "blue",
                    }
                    for point_id in all_point_ids()
                ],
                "visible_board": visible_board_trace(sampled_scene.board),
                "construction_mode": str(sampled_scene.construction_mode),
                "target_answer": int(sampled_scene.answer),
                "target_answer_support": [int(value) for value in axes.target_answer_support],
                "target_color": player_name(int(sampled_scene.target_color)),
                "marked_point_id": str(sampled_scene.marked_point_id),
                "marked_coord": [int(value) for value in point_coord(sampled_scene.marked_point_id)],
                "marked_piece_id": piece_to_entity_id(sampled_scene.marked_point_id),
                "piece_count_per_side": int(axes.piece_count_per_side),
                "annotation_kind": str(annotation_symbolic_type),
                "annotation_point_ids": [str(point_id) for point_id in sampled_scene.annotation_point_ids],
                "annotation_entity_ids": [str(entity_id) for entity_id in annotation_entity_ids],
                "legal_destinations_for_marked_piece": [
                    str(point_id) for point_id in legal_destinations(sampled_scene.board, sampled_scene.marked_point_id)
                ],
                "capture_lines_for_marked_piece": [dict(item) for item in marked_capture_lines],
                "all_jump_specs": [
                    {
                        "origin_id": str(spec.origin_id),
                        "middle_id": str(spec.middle_id),
                        "landing_id": str(spec.landing_id),
                    }
                    for spec in JUMP_SPECS
                ],
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(entity_id) for entity_id in annotation_entity_ids],
            },
            "projected_annotation": {
                "type": "point_set",
                "point_set": [list(point) for point in annotation_points],
                "pixel_point_set": [list(point) for point in annotation_points],
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
            scene_id="sixteen_soldiers",
            query_id=str(axes.query_id),
        )


@register_task
class GamesSixteenSoldiersMarkedPieceDestinationCountTask(FixedQueryVariantTaskMixin, GamesSixteenSoldiersTask):
    """Count adjacent empty destinations for one marked Sixteen Soldiers piece."""

    task_id = MARKED_DESTINATION_TASK_ID
    fixed_query_id = MARKED_DESTINATION_QUERY_ID


@register_task
class GamesSixteenSoldiersMarkedPieceCaptureCountTask(FixedQueryVariantTaskMixin, GamesSixteenSoldiersTask):
    """Count immediate captures for one marked Sixteen Soldiers piece."""

    task_id = MARKED_CAPTURE_TASK_ID
    fixed_query_id = MARKED_CAPTURE_QUERY_ID


__all__ = [
    "GamesSixteenSoldiersMarkedPieceCaptureCountTask",
    "GamesSixteenSoldiersMarkedPieceDestinationCountTask",
]
