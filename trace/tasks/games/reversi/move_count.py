"""Games Reversi task for grounded move-count and flip-count queries."""

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
from ..shared.complexity import build_games_reversi_move_complexity
from ..shared.reversi_common import (
    BLACK,
    WHITE,
    Board,
    Coord,
    coord_to_cell_id,
    corner_coords,
    legal_moves_with_flips,
    player_name,
    simulate_random_state,
)
from ..shared.reversi_scene import ReversiRenderParams, render_reversi_board_scene
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_variant
from ..shared.style import SUPPORTED_GAMES_STYLE_VARIANTS
from ..shared.visual_defaults import load_games_background_defaults, load_games_noise_defaults


TASK_ID = "task_games_reversi_move_count"
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "compact_board",
    "classic_board",
)
SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = (
    "legal_move_count",
    "corner_move_count",
    "flip_count_for_marked_move",
)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for visible Reversi move-count scenes."""

    legal_move_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6)
    corner_move_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4)
    flip_count_support: Tuple[int, ...] = (1, 2, 3, 4, 5)
    canvas_width: int = 900
    canvas_height: int = 900
    panel_margin_px: int = 48
    player_badge_height_px: int = 52
    player_badge_width_px: int = 190
    header_gap_px: int = 18
    max_board_size_px: int = 720
    board_corner_radius_px: int = 24
    board_frame_width_px: int = 14
    cell_line_width_px: int = 3
    marked_square_outline_width_px: int = 6
    disc_inset_fraction: float = 0.14
    player_badge_font_size_px: int = 22


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one Reversi scene."""

    query_variant: str
    scene_variant: str
    style_variant: str
    target_answer: int
    target_answer_support: Tuple[int, ...]
    board_size: int
    query_variant_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _SampledReversiScene:
    """One sampled Reversi scene plus query-specific witness metadata."""

    board: Board
    current_player: int
    legal_moves: Dict[Coord, Tuple[Coord, ...]]
    evidence_coords: Tuple[Coord, ...]
    evidence_entity_ids: Tuple[str, ...]
    marked_move: Coord | None
    marked_move_flips: Tuple[Coord, ...]
    construction_mode: str


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "reversi")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_games_background_defaults(task_group="reversi")
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="reversi", apply_prob=0.0)


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
    """Resolve one balanced named axis for the Reversi task."""

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


def _target_support_key(query_variant: str) -> str:
    """Return the configured answer-support key for one query variant."""

    return {
        "legal_move_count": "legal_move_count_support",
        "corner_move_count": "corner_move_count_support",
        "flip_count_for_marked_move": "flip_count_support",
    }[str(query_variant)]


def _board_size_for_scene(scene_variant: str) -> int:
    """Return the visible board size for one Reversi scene family."""

    return 6 if str(scene_variant) == "compact_board" else 8


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve all semantic and visual sampling axes for one Reversi instance."""

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
        board_size=int(_board_size_for_scene(str(scene_variant))),
        query_variant_probabilities=dict(query_variant_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
    )


def _render_params(params: Mapping[str, Any]) -> ReversiRenderParams:
    """Resolve Reversi rendering parameters from config/defaults."""

    return ReversiRenderParams(
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
        cell_line_width_px=int(
            params.get("cell_line_width_px", group_default(_RENDER_DEFAULTS, "cell_line_width_px", _DEFAULTS.cell_line_width_px))
        ),
        marked_square_outline_width_px=int(
            params.get(
                "marked_square_outline_width_px",
                group_default(_RENDER_DEFAULTS, "marked_square_outline_width_px", _DEFAULTS.marked_square_outline_width_px),
            )
        ),
        disc_inset_fraction=float(
            params.get(
                "disc_inset_fraction",
                group_default(_RENDER_DEFAULTS, "disc_inset_fraction", _DEFAULTS.disc_inset_fraction),
            )
        ),
        player_badge_font_size_px=int(
            params.get(
                "player_badge_font_size_px",
                group_default(_RENDER_DEFAULTS, "player_badge_font_size_px", _DEFAULTS.player_badge_font_size_px),
            )
        ),
    )


def _empty_board(board_size: int) -> List[List[int]]:
    """Return one mutable empty board."""

    return [[0 for _ in range(int(board_size))] for _ in range(int(board_size))]


def _freeze_board(board: Sequence[Sequence[int]]) -> Board:
    """Freeze one mutable board into the canonical tuple form."""

    return tuple(tuple(int(cell) for cell in row) for row in board)


def _set_cell(board: List[List[int]], coord: Coord, value: int) -> None:
    """Write one board cell in-place."""

    board[int(coord[0])][int(coord[1])] = int(value)


def _resolve_current_player(rng, *, params: Mapping[str, Any]) -> int:
    """Resolve the current player for one scene."""

    explicit = params.get("current_player")
    if explicit is None:
        return int(BLACK if int(rng.randrange(2)) == 0 else WHITE)
    text = str(explicit).strip().lower()
    if text in {"black", "b", "1"}:
        return int(BLACK)
    if text in {"white", "w", "-1"}:
        return int(WHITE)
    raise ValueError(f"unsupported current_player: {explicit}")


def _construct_legal_move_board(*, rng, board_size: int, current_player: int, target_answer: int) -> _SampledReversiScene:
    """Search for one reachable board with an exact number of legal moves."""

    max_plies = max(int(board_size) + 2, (int(board_size) * int(board_size)) - 4)
    if int(target_answer) == 0:
        min_plies = max(int(board_size) + 6, int(0.65 * max_plies))
    elif int(target_answer) >= 5:
        min_plies = max(4, int(0.22 * max_plies))
        max_plies = max(min_plies + 4, int(0.62 * max_plies))
    else:
        min_plies = max(4, int(0.35 * max_plies))

    for _ in range(192):
        frozen_board = simulate_random_state(
            rng=rng,
            board_size=int(board_size),
            min_plies=int(min_plies),
            max_plies=int(max_plies),
        )
        legal_moves = legal_moves_with_flips(frozen_board, int(current_player))
        if int(len(legal_moves)) != int(target_answer):
            continue
        evidence_coords = tuple(sorted((int(row), int(col)) for row, col in legal_moves.keys()))
        return _SampledReversiScene(
            board=frozen_board,
            current_player=int(current_player),
            legal_moves=legal_moves,
            evidence_coords=evidence_coords,
            evidence_entity_ids=tuple(coord_to_cell_id(coord) for coord in evidence_coords),
            marked_move=None,
            marked_move_flips=tuple(),
            construction_mode="simulated_legal_count",
        )

    raise ValueError("failed to find a reachable board with the requested legal-move count")


def _construct_corner_move_board(*, rng, board_size: int, current_player: int, target_answer: int) -> _SampledReversiScene:
    """Construct one board with an exact number of legal corner moves."""

    board = _empty_board(int(board_size))
    opponent = int(WHITE if int(current_player) == int(BLACK) else BLACK)
    corners = list(corner_coords(int(board_size)))
    selected_corners = [] if int(target_answer) == 0 else list(rng.sample(corners, k=int(target_answer)))
    corner_pattern_specs = {
        (0, 0): ((0, 1), (0, 2)),
        (0, int(board_size) - 1): ((0, int(board_size) - 2), (0, int(board_size) - 3)),
        (int(board_size) - 1, 0): ((int(board_size) - 1, 1), (int(board_size) - 1, 2)),
        (
            int(board_size) - 1,
            int(board_size) - 1,
        ): ((int(board_size) - 1, int(board_size) - 2), (int(board_size) - 1, int(board_size) - 3)),
    }
    for corner in corners:
        if tuple(corner) in {tuple(item) for item in selected_corners}:
            adjacent_coord, terminal_coord = corner_pattern_specs[tuple(corner)]
            _set_cell(board, adjacent_coord, opponent)
            _set_cell(board, terminal_coord, current_player)
        else:
            _set_cell(board, tuple(corner), current_player if int(corner[0] + corner[1]) % 2 == 0 else opponent)
    frozen_board = _freeze_board(board)
    legal_moves = legal_moves_with_flips(frozen_board, int(current_player))
    evidence_coords = tuple(sorted(move for move in legal_moves if tuple(move) in set(corners)))
    if int(len(evidence_coords)) != int(target_answer):
        raise ValueError("constructed corner-move board did not match the target answer")
    return _SampledReversiScene(
        board=frozen_board,
        current_player=int(current_player),
        legal_moves=legal_moves,
        evidence_coords=evidence_coords,
        evidence_entity_ids=tuple(coord_to_cell_id(coord) for coord in evidence_coords),
        marked_move=None,
        marked_move_flips=tuple(),
        construction_mode="corner_patterns",
    )


def _flip_blueprints(target_answer: int) -> Tuple[Tuple[int, ...], ...]:
    """Return supported flip-length partitions for one marked-move target count."""

    return {
        1: ((1,),),
        2: ((2,), (1, 1)),
        3: ((3,), (2, 1), (1, 1, 1)),
        4: ((3, 1), (2, 2), (2, 1, 1)),
        5: ((3, 2), (2, 2, 1)),
    }[int(target_answer)]


def _construct_flip_count_board(*, rng, board_size: int, current_player: int, target_answer: int) -> _SampledReversiScene:
    """Construct one board with a marked move that flips an exact number of discs."""

    board = _empty_board(int(board_size))
    opponent = int(WHITE if int(current_player) == int(BLACK) else BLACK)
    anchor_specs = (
        ((1, 1), ((0, 1), (1, 0), (1, 1))),
        ((1, int(board_size) - 2), ((0, -1), (1, 0), (1, -1))),
        ((int(board_size) - 2, 1), ((0, 1), (-1, 0), (-1, 1))),
        ((int(board_size) - 2, int(board_size) - 2), ((0, -1), (-1, 0), (-1, -1))),
    )
    marked_move, supported_dirs = anchor_specs[int(rng.randrange(len(anchor_specs)))]
    blueprint = _flip_blueprints(int(target_answer))[int(rng.randrange(len(_flip_blueprints(int(target_answer)))))]
    shuffled_dirs = list(supported_dirs)
    rng.shuffle(shuffled_dirs)
    chosen_dirs = shuffled_dirs[: len(blueprint)]
    flipped_coords: List[Coord] = []
    for direction, length in zip(chosen_dirs, blueprint):
        row_delta, col_delta = int(direction[0]), int(direction[1])
        for step in range(1, int(length) + 1):
            flipped_coord = (
                int(marked_move[0] + (step * row_delta)),
                int(marked_move[1] + (step * col_delta)),
            )
            _set_cell(board, flipped_coord, opponent)
            flipped_coords.append(flipped_coord)
        terminal_coord = (
            int(marked_move[0] + ((int(length) + 1) * row_delta)),
            int(marked_move[1] + ((int(length) + 1) * col_delta)),
        )
        _set_cell(board, terminal_coord, current_player)
    frozen_board = _freeze_board(board)
    legal_moves = legal_moves_with_flips(frozen_board, int(current_player))
    marked_flips = tuple(sorted(legal_moves.get(tuple(marked_move), ())))
    if len(marked_flips) != int(target_answer):
        raise ValueError("constructed flip-count board did not match the target answer")
    return _SampledReversiScene(
        board=frozen_board,
        current_player=int(current_player),
        legal_moves=legal_moves,
        evidence_coords=marked_flips,
        evidence_entity_ids=tuple(coord_to_cell_id(coord) for coord in marked_flips),
        marked_move=tuple(int(value) for value in marked_move),
        marked_move_flips=marked_flips,
        construction_mode="marked_flip",
    )


def _sample_scene(*, rng, axes: _ResolvedAxes, params: Mapping[str, Any]) -> _SampledReversiScene:
    """Construct one Reversi scene consistent with the requested axes."""

    current_player = _resolve_current_player(rng, params=params)
    if str(axes.query_variant) == "legal_move_count":
        return _construct_legal_move_board(
            rng=rng,
            board_size=int(axes.board_size),
            current_player=int(current_player),
            target_answer=int(axes.target_answer),
        )
    if str(axes.query_variant) == "corner_move_count":
        return _construct_corner_move_board(
            rng=rng,
            board_size=int(axes.board_size),
            current_player=int(current_player),
            target_answer=int(axes.target_answer),
        )
    return _construct_flip_count_board(
        rng=rng,
        board_size=int(axes.board_size),
        current_player=int(current_player),
        target_answer=int(axes.target_answer),
    )


def _build_prompt_json_examples(*, query_variant: str) -> Tuple[str, str]:
    """Return deterministic prompt examples for the active Reversi query variant."""

    answer_value = 3 if str(query_variant) == "flip_count_for_marked_move" else 2
    evidence_value = (
        [[112, 184, 176, 248], [184, 184, 248, 248], [256, 184, 320, 248]]
        if str(query_variant) == "flip_count_for_marked_move"
        else [[112, 184, 176, 248], [184, 184, 248, 248]]
    )
    return (
        json.dumps({"evidence": evidence_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


@register_task
class GamesReversiMoveCountTask:
    """Return one grounded counting query over a visible Reversi board."""

    task_id = TASK_ID
    domain = "games"
    task_group = "reversi"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        render_params = _render_params(params)

        sampled_scene: _SampledReversiScene | None = None
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
        rendered_scene = render_reversi_board_scene(
            board=sampled_scene.board,
            background=background,
            scene_variant=str(axes.scene_variant),
            style_variant=str(axes.style_variant),
            current_player=int(sampled_scene.current_player),
            params=render_params,
            marked_move=sampled_scene.marked_move,
        )
        evidence_bboxes = [
            list(rendered_scene.render_map["cell_bboxes_px"][str(entity_id)])
            for entity_id in sampled_scene.evidence_entity_ids
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
                "object_description_compact_board",
                "object_description_classic_board",
                "legal_move_rule_text",
                "corner_rule_text",
                "marked_move_rule_text",
                "flip_rule_text",
                "answer_hint_legal_move_count",
                "answer_hint_corner_move_count",
                "answer_hint_flip_count_for_marked_move",
                "evidence_hint_legal_move_count",
                "evidence_hint_corner_move_count",
                "evidence_hint_flip_count_for_marked_move",
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
                "legal_move_rule_text": str(prompt_defaults["legal_move_rule_text"]),
                "corner_rule_text": str(prompt_defaults["corner_rule_text"]),
                "marked_move_rule_text": str(prompt_defaults["marked_move_rule_text"]),
                "flip_rule_text": str(prompt_defaults["flip_rule_text"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(axes.target_answer))
        evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in evidence_bboxes])
        complexity = build_games_reversi_move_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
            scene_variant=str(axes.scene_variant),
            query_variant=str(axes.query_variant),
            board_size=int(axes.board_size),
            legal_move_count=int(len(sampled_scene.legal_moves)),
            target_answer=int(axes.target_answer),
            evidence_count=len(sampled_scene.evidence_entity_ids),
        )

        legal_move_specs = [
            {
                "coord": [int(coord[0]), int(coord[1])],
                "cell_id": str(coord_to_cell_id(coord)),
                "flip_count": int(len(flips)),
            }
            for coord, flips in sorted(sampled_scene.legal_moves.items())
        ]
        board_rows = [[int(cell) for cell in row] for row in sampled_scene.board]
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_reversi_board_{str(axes.scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_variant": str(axes.query_variant),
                    "task_variant": str(axes.query_variant),
                    "style_variant": str(axes.style_variant),
                    "board_size": int(axes.board_size),
                    "current_player": str(current_player_name),
                    "target_answer": int(axes.target_answer),
                    "evidence_entity_ids": [str(entity_id) for entity_id in sampled_scene.evidence_entity_ids],
                    "marked_move_cell_id": None
                    if sampled_scene.marked_move is None
                    else str(coord_to_cell_id(sampled_scene.marked_move)),
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
                    "board_size": int(axes.board_size),
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
                "board_size": int(axes.board_size),
                "current_player": str(current_player_name),
                "target_answer": int(axes.target_answer),
                "target_answer_support": [int(value) for value in axes.target_answer_support],
                "board_rows": board_rows,
                "construction_mode": str(sampled_scene.construction_mode),
                "legal_move_count": int(len(sampled_scene.legal_moves)),
                "legal_move_specs": legal_move_specs,
                "marked_move": None
                if sampled_scene.marked_move is None
                else [int(sampled_scene.marked_move[0]), int(sampled_scene.marked_move[1])],
                "marked_move_cell_id": None
                if sampled_scene.marked_move is None
                else str(coord_to_cell_id(sampled_scene.marked_move)),
                "marked_move_flip_coords": [
                    [int(coord[0]), int(coord[1])] for coord in sampled_scene.marked_move_flips
                ],
                "evidence_coords": [[int(coord[0]), int(coord[1])] for coord in sampled_scene.evidence_coords],
                "evidence_entity_ids": [str(entity_id) for entity_id in sampled_scene.evidence_entity_ids],
            },
            "witness_symbolic": {
                "type": "id_set",
                "ids": [str(entity_id) for entity_id in sampled_scene.evidence_entity_ids],
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


__all__ = ["GamesReversiMoveCountTask"]
