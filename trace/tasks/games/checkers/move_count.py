"""Games Checkers task for grounded move-count queries."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
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
from ..shared.checkers_common import (
    BLACK,
    BOARD_SIZE,
    RED,
    Board,
    CheckersMove,
    Coord,
    allowed_non_king_row,
    coord_to_cell_id,
    empty_board,
    enumerate_legal_moves,
    freeze_board,
    occupied_piece_count,
    opponent,
    playable_coords,
    player_name,
)
from ..shared.checkers_scene import CheckersRenderParams, render_checkers_board_scene
from ..shared.complexity import build_games_checkers_move_complexity
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_variant
from ..shared.style import SUPPORTED_GAMES_STYLE_VARIANTS
from ..shared.visual_defaults import load_games_background_defaults, load_games_noise_defaults


TASK_ID = "task_games_checkers_move_count"
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "midgame_board",
    "crowded_board",
)
SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = (
    "legal_move_count",
    "capture_move_count",
)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for visible Checkers move-count scenes."""

    legal_move_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    capture_move_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4)
    midgame_min_occupied_count: int = 8
    midgame_max_occupied_count: int = 12
    crowded_min_occupied_count: int = 13
    crowded_max_occupied_count: int = 17
    canvas_width: int = 980
    canvas_height: int = 920
    panel_margin_px: int = 48
    player_badge_height_px: int = 52
    player_badge_width_px: int = 230
    header_gap_px: int = 18
    max_board_size_px: int = 780
    board_corner_radius_px: int = 26
    board_frame_width_px: int = 10
    piece_inset_fraction: float = 0.17
    player_badge_font_size_px: int = 22


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one Checkers scene."""

    query_variant: str
    scene_variant: str
    style_variant: str
    target_answer: int
    target_answer_support: Tuple[int, ...]
    query_variant_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _SceneEvaluation:
    """Query-specific evaluation payload derived from one finalized board."""

    answer: int
    legal_moves: Tuple[CheckersMove, ...]
    capture_moves: Tuple[CheckersMove, ...]
    evidence_coords: Tuple[Coord, ...]
    evidence_entity_ids: Tuple[str, ...]


@dataclass(frozen=True)
class _SampledCheckersScene:
    """One sampled Checkers scene plus query-specific witness metadata."""

    board: Board
    current_player: int
    evaluation: _SceneEvaluation
    occupied_count: int
    construction_mode: str


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "checkers")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_games_background_defaults(task_group="checkers")
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="checkers", apply_prob=0.0)


def _target_support_key(query_variant: str) -> str:
    """Return the configured answer-support key for one query variant."""

    return {
        "legal_move_count": "legal_move_count_support",
        "capture_move_count": "capture_move_count_support",
    }[str(query_variant)]


def _resolve_query_variant(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced semantic query variant, honoring `task_variant` as an alias."""

    alias_params = dict(params)
    if alias_params.get("query_variant") is None and alias_params.get("task_variant") is not None:
        alias_params["query_variant"] = alias_params["task_variant"]
    return resolve_games_query_variant(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=alias_params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_QUERY_VARIANTS,
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
    """Resolve one balanced named axis for the Checkers task."""

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


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve all semantic and visual sampling axes for one Checkers instance."""

    query_variant, query_variant_probabilities = _resolve_query_variant(
        instance_seed=int(instance_seed),
        params=params,
    )
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
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
        supported=SUPPORTED_GAMES_STYLE_VARIANTS,
    )
    target_support_key = _target_support_key(str(query_variant))
    target_answer, target_answer_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=str(target_support_key),
        explicit_key="target_answer",
        fallback_support=getattr(_DEFAULTS, target_support_key),
        namespace=f"{TASK_ID}.target_answer.{str(query_variant)}",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_explicit_sampling_index=True,
    )
    target_answer_support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key=str(target_support_key),
        fallback=getattr(_DEFAULTS, target_support_key),
    )
    return _ResolvedAxes(
        query_variant=str(query_variant),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        target_answer=int(target_answer),
        target_answer_support=tuple(int(value) for value in target_answer_support),
        query_variant_probabilities=dict(query_variant_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
    )


def _render_params(params: Mapping[str, Any]) -> CheckersRenderParams:
    """Resolve Checkers rendering parameters from config/defaults."""

    return CheckersRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
        panel_margin_px=int(params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px))),
        player_badge_height_px=int(
            params.get(
                "player_badge_height_px",
                group_default(_RENDER_DEFAULTS, "player_badge_height_px", _DEFAULTS.player_badge_height_px),
            )
        ),
        player_badge_width_px=int(
            params.get(
                "player_badge_width_px",
                group_default(_RENDER_DEFAULTS, "player_badge_width_px", _DEFAULTS.player_badge_width_px),
            )
        ),
        header_gap_px=int(params.get("header_gap_px", group_default(_RENDER_DEFAULTS, "header_gap_px", _DEFAULTS.header_gap_px))),
        max_board_size_px=int(
            params.get("max_board_size_px", group_default(_RENDER_DEFAULTS, "max_board_size_px", _DEFAULTS.max_board_size_px))
        ),
        board_corner_radius_px=int(
            params.get(
                "board_corner_radius_px",
                group_default(_RENDER_DEFAULTS, "board_corner_radius_px", _DEFAULTS.board_corner_radius_px),
            )
        ),
        board_frame_width_px=int(
            params.get(
                "board_frame_width_px",
                group_default(_RENDER_DEFAULTS, "board_frame_width_px", _DEFAULTS.board_frame_width_px),
            )
        ),
        piece_inset_fraction=float(
            params.get(
                "piece_inset_fraction",
                group_default(_RENDER_DEFAULTS, "piece_inset_fraction", _DEFAULTS.piece_inset_fraction),
            )
        ),
        player_badge_font_size_px=int(
            params.get(
                "player_badge_font_size_px",
                group_default(_RENDER_DEFAULTS, "player_badge_font_size_px", _DEFAULTS.player_badge_font_size_px),
            )
        ),
    )


def _resolve_current_player(rng, *, params: Mapping[str, Any]) -> int:
    """Resolve the current player for one scene."""

    explicit = params.get("current_player")
    if explicit is None:
        return int(RED if int(rng.randrange(2)) == 0 else BLACK)
    text = str(explicit).strip().lower()
    if text in {"red", "r", "1"}:
        return int(RED)
    if text in {"black", "b", "-1"}:
        return int(BLACK)
    raise ValueError(f"unsupported current_player: {explicit}")


def _scene_occupied_range(scene_variant: str) -> Tuple[int, int]:
    """Return the target occupied-piece range for one scene family."""

    if str(scene_variant) == "crowded_board":
        return (int(_DEFAULTS.crowded_min_occupied_count), int(_DEFAULTS.crowded_max_occupied_count))
    return (int(_DEFAULTS.midgame_min_occupied_count), int(_DEFAULTS.midgame_max_occupied_count))


def _quiet_slots(player: int) -> Tuple[Tuple[Coord, Coord], ...]:
    """Return non-overlapping one-step edge move templates for one player."""

    if int(player) == int(RED):
        return (
            ((1, 0), (0, 1)),
            ((1, 6), (0, 7)),
            ((3, 0), (2, 1)),
            ((3, 6), (2, 7)),
            ((5, 0), (4, 1)),
            ((5, 6), (4, 7)),
        )
    return (
        ((0, 7), (1, 6)),
        ((1, 0), (2, 1)),
        ((2, 7), (3, 6)),
        ((3, 0), (4, 1)),
        ((4, 7), (5, 6)),
        ((5, 0), (6, 1)),
    )


def _capture_slots(player: int) -> Tuple[Tuple[Coord, Coord, Coord], ...]:
    """Return non-overlapping single-jump edge capture templates for one player."""

    if int(player) == int(RED):
        return (
            ((3, 0), (2, 1), (1, 2)),
            ((5, 0), (4, 1), (3, 2)),
            ((7, 0), (6, 1), (5, 2)),
            ((2, 7), (1, 6), (0, 5)),
            ((4, 7), (3, 6), (2, 5)),
            ((6, 7), (5, 6), (4, 5)),
        )
    return (
        ((0, 7), (1, 6), (2, 5)),
        ((1, 0), (2, 1), (3, 2)),
        ((2, 7), (3, 6), (4, 5)),
        ((3, 0), (4, 1), (5, 2)),
        ((4, 7), (5, 6), (6, 5)),
        ((5, 0), (6, 1), (7, 2)),
    )


def _evaluate_board(*, board: Board, current_player: int, query_variant: str) -> _SceneEvaluation | None:
    """Evaluate one finalized board under the active query semantics."""

    legal_moves = tuple(enumerate_legal_moves(board, int(current_player)))
    capture_moves = tuple(move for move in legal_moves if move.captured is not None)
    relevant_moves = legal_moves if str(query_variant) == "legal_move_count" else capture_moves
    destinations = tuple((int(move.landing[0]), int(move.landing[1])) for move in relevant_moves)
    if len(set(destinations)) != len(destinations):
        return None
    evidence_coords = tuple(sorted(set(destinations)))
    return _SceneEvaluation(
        answer=int(len(relevant_moves)),
        legal_moves=legal_moves,
        capture_moves=capture_moves,
        evidence_coords=evidence_coords,
        evidence_entity_ids=tuple(coord_to_cell_id(coord) for coord in evidence_coords),
    )


def _base_board_for_axes(*, rng, current_player: int, query_variant: str, target_answer: int) -> Tuple[Board, str]:
    """Construct one sparse base board that already meets the requested answer."""

    mutable = [list(int(cell) for cell in row) for row in empty_board()]
    if str(query_variant) == "legal_move_count":
        if int(target_answer) > 0:
            selected_slots = list(rng.sample(_quiet_slots(int(current_player)), k=int(target_answer)))
            for origin, _landing in selected_slots:
                mutable[int(origin[0])][int(origin[1])] = int(current_player)
            return freeze_board(mutable), "quiet_edge_templates"
        return freeze_board(mutable), "empty_zero_legal"

    if int(target_answer) > 0:
        selected_slots = list(rng.sample(_capture_slots(int(current_player)), k=int(target_answer)))
        for origin, captured, _landing in selected_slots:
            mutable[int(origin[0])][int(origin[1])] = int(current_player)
            mutable[int(captured[0])][int(captured[1])] = int(opponent(int(current_player)))
        return freeze_board(mutable), "capture_edge_templates"

    quiet_slots = _quiet_slots(int(current_player))
    quiet_count = min(len(quiet_slots), max(1, int(rng.randint(2, 4))))
    selected_slots = list(rng.sample(quiet_slots, k=int(quiet_count)))
    for origin, _landing in selected_slots:
        mutable[int(origin[0])][int(origin[1])] = int(current_player)
    return freeze_board(mutable), "quiet_zero_capture"


def _try_add_fillers(
    *,
    rng,
    board: Board,
    current_player: int,
    query_variant: str,
    target_answer: int,
    scene_variant: str,
) -> Tuple[Board, _SceneEvaluation, int]:
    """Add non-semantic filler pieces while preserving the requested answer."""

    min_occupied, max_occupied = _scene_occupied_range(str(scene_variant))
    desired_occupied = int(rng.randint(int(min_occupied), int(max_occupied)))
    mutable = [list(int(cell) for cell in row) for row in board]
    current_occupied = int(occupied_piece_count(mutable))
    evaluation = _evaluate_board(board=freeze_board(mutable), current_player=int(current_player), query_variant=str(query_variant))
    if evaluation is None or int(evaluation.answer) != int(target_answer):
        raise ValueError("base board did not satisfy the requested checkers answer")

    playable = list(playable_coords())
    attempts = 0
    while int(current_occupied) < int(desired_occupied) and attempts < 640:
        attempts += 1
        row, col = playable[int(rng.randrange(len(playable)))]
        if int(mutable[row][col]) != 0:
            continue
        piece_player = int(current_player if float(rng.random()) < 0.36 else opponent(int(current_player)))
        if not allowed_non_king_row(int(piece_player), int(row)):
            continue
        mutable[row][col] = int(piece_player)
        frozen = freeze_board(mutable)
        candidate = _evaluate_board(
            board=frozen,
            current_player=int(current_player),
            query_variant=str(query_variant),
        )
        if candidate is None or int(candidate.answer) != int(target_answer):
            mutable[row][col] = 0
            continue
        evaluation = candidate
        current_occupied = int(occupied_piece_count(mutable))

    frozen = freeze_board(mutable)
    evaluation = _evaluate_board(
        board=frozen,
        current_player=int(current_player),
        query_variant=str(query_variant),
    )
    final_occupied = int(occupied_piece_count(frozen))
    if evaluation is None or int(evaluation.answer) != int(target_answer):
        raise ValueError("failed to preserve the requested checkers answer after filler placement")
    if not (int(min_occupied) <= int(final_occupied) <= int(max_occupied)):
        raise ValueError("failed to reach the requested scene-density range for checkers")
    return frozen, evaluation, final_occupied


def _sample_scene(*, rng, axes: _ResolvedAxes, params: Mapping[str, Any]) -> _SampledCheckersScene:
    """Construct one Checkers scene consistent with the requested axes."""

    current_player = _resolve_current_player(rng, params=params)
    base_board, base_mode = _base_board_for_axes(
        rng=rng,
        current_player=int(current_player),
        query_variant=str(axes.query_variant),
        target_answer=int(axes.target_answer),
    )
    board, evaluation, occupied_count = _try_add_fillers(
        rng=rng,
        board=base_board,
        current_player=int(current_player),
        query_variant=str(axes.query_variant),
        target_answer=int(axes.target_answer),
        scene_variant=str(axes.scene_variant),
    )
    return _SampledCheckersScene(
        board=board,
        current_player=int(current_player),
        evaluation=evaluation,
        occupied_count=int(occupied_count),
        construction_mode=str(base_mode),
    )


def _build_prompt_json_examples(*, query_variant: str) -> Tuple[str, str]:
    """Return deterministic prompt examples for the active Checkers query variant."""

    answer_value = 2 if str(query_variant) == "capture_move_count" else 3
    evidence_value = [[132, 188, 196, 252], [204, 188, 268, 252]]
    return (
        json.dumps({"evidence": evidence_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


def _movement_rule_text(current_player: int) -> str:
    """Return the prompt-facing forward-movement rule text."""

    if int(current_player) == int(RED):
        return "Only the dark squares are used. All shown pieces are ordinary men, not kings. Red pieces move diagonally upward toward the top edge, and Black pieces move diagonally downward toward the bottom edge."
    return "Only the dark squares are used. All shown pieces are ordinary men, not kings. Black pieces move diagonally downward toward the bottom edge, and Red pieces move diagonally upward toward the top edge."


@register_task
class GamesCheckersMoveCountTask:
    """Return one grounded counting query over a visible Checkers board."""

    task_id = TASK_ID
    domain = "games"
    task_group = "checkers"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        render_params = _render_params(params)

        sampled_scene: _SampledCheckersScene | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sampled_scene = _sample_scene(rng=attempt_rng, axes=axes, params=params)
            except ValueError:
                continue
            break
        if sampled_scene is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts")

        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered_scene = render_checkers_board_scene(
            board=sampled_scene.board,
            background=background,
            scene_variant=str(axes.scene_variant),
            style_variant=str(axes.style_variant),
            current_player=int(sampled_scene.current_player),
            params=render_params,
        )
        evidence_bboxes = [
            list(rendered_scene.render_map["cell_bboxes_px"][str(entity_id)])
            for entity_id in sampled_scene.evaluation.evidence_entity_ids
        ]
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
                "object_description_midgame_board",
                "object_description_crowded_board",
                "capture_rule_text",
                "single_jump_rule_text",
                "legal_move_rule_text",
                "answer_hint_legal_move_count",
                "answer_hint_capture_move_count",
                "evidence_hint_legal_move_count",
                "evidence_hint_capture_move_count",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples(query_variant=str(axes.query_variant))
        current_player_name = player_name(int(sampled_scene.current_player))
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
                "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_variant)}"]),
                "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(axes.query_variant)}"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "current_player_name": str(current_player_name),
                "movement_rule_text": str(_movement_rule_text(int(sampled_scene.current_player))),
                "capture_rule_text": str(prompt_defaults["capture_rule_text"]),
                "single_jump_rule_text": str(prompt_defaults["single_jump_rule_text"]),
                "legal_move_rule_text": str(prompt_defaults["legal_move_rule_text"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(axes.target_answer))
        evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in evidence_bboxes])
        complexity = build_games_checkers_move_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
            scene_variant=str(axes.scene_variant),
            query_variant=str(axes.query_variant),
            occupied_count=int(sampled_scene.occupied_count),
            target_answer=int(axes.target_answer),
            evidence_count=len(sampled_scene.evaluation.evidence_entity_ids),
        )

        legal_move_specs = [
            {
                "origin": [int(move.origin[0]), int(move.origin[1])],
                "landing": [int(move.landing[0]), int(move.landing[1])],
                "captured": None if move.captured is None else [int(move.captured[0]), int(move.captured[1])],
                "landing_cell_id": str(coord_to_cell_id(move.landing)),
            }
            for move in sorted(
                sampled_scene.evaluation.legal_moves,
                key=lambda move: (move.origin[0], move.origin[1], move.landing[0], move.landing[1]),
            )
        ]
        board_rows = [[int(cell) for cell in row] for row in sampled_scene.board]
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_checkers_board_{str(axes.scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_variant": str(axes.query_variant),
                    "task_variant": str(axes.query_variant),
                    "style_variant": str(axes.style_variant),
                    "board_size": int(BOARD_SIZE),
                    "current_player": str(current_player_name),
                    "target_answer": int(axes.target_answer),
                    "evidence_entity_ids": [str(entity_id) for entity_id in sampled_scene.evaluation.evidence_entity_ids],
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
                    "style_variant": str(axes.style_variant),
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_variant_probabilities": dict(axes.query_variant_probabilities),
                    "task_variant_probabilities": dict(axes.query_variant_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "board_size": int(BOARD_SIZE),
                    "current_player": str(current_player_name),
                    "target_answer": int(axes.target_answer),
                    "target_answer_support": [int(value) for value in axes.target_answer_support],
                    "target_answer_probabilities": dict(axes.target_answer_probabilities),
                },
            },
            "render_spec": {
                "scene_variant": str(axes.scene_variant),
                "style_variant": str(axes.style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(axes.scene_variant),
                "query_variant": str(axes.query_variant),
                "task_variant": str(axes.query_variant),
                "style_variant": str(axes.style_variant),
                "board_size": int(BOARD_SIZE),
                "current_player": str(current_player_name),
                "target_answer": int(axes.target_answer),
                "target_answer_support": [int(value) for value in axes.target_answer_support],
                "board_rows": board_rows,
                "construction_mode": str(sampled_scene.construction_mode),
                "occupied_count": int(sampled_scene.occupied_count),
                "legal_move_count": int(len(sampled_scene.evaluation.legal_moves)),
                "capture_move_count": int(len(sampled_scene.evaluation.capture_moves)),
                "legal_move_specs": legal_move_specs,
                "evidence_coords": [
                    [int(coord[0]), int(coord[1])] for coord in sampled_scene.evaluation.evidence_coords
                ],
                "evidence_entity_ids": [str(entity_id) for entity_id in sampled_scene.evaluation.evidence_entity_ids],
            },
            "witness_symbolic": {
                "type": "id_set",
                "ids": [str(entity_id) for entity_id in sampled_scene.evaluation.evidence_entity_ids],
            },
            "projected_evidence": {
                "bbox_set": [list(bbox) for bbox in evidence_bboxes],
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


__all__ = ["GamesCheckersMoveCountTask"]
