"""Games Connect Four task for grounded move-count queries."""

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
from ..shared.complexity import build_games_connect_four_move_complexity
from ..shared.connect_four_common import (
    Board,
    COLUMNS,
    Coord,
    RED,
    ROWS,
    YELLOW,
    coord_to_cell_id,
    drop_disc,
    empty_board,
    has_connect_four,
    legal_drop_rows,
    occupied_cell_count,
    opponent,
    player_name,
    winning_drop_map,
)
from ..shared.connect_four_scene import ConnectFourRenderParams, render_connect_four_board_scene
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_variant
from ..shared.style import SUPPORTED_GAMES_STYLE_VARIANTS
from ..shared.visual_defaults import load_games_background_defaults, load_games_noise_defaults


TASK_ID = "task_games_connect_four_move_count"
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "midgame_board",
    "crowded_board",
)
SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = (
    "winning_move_count",
    "safe_move_count",
)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for visible Connect Four move-count scenes."""

    winning_move_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4)
    safe_move_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    midgame_min_occupied_count: int = 10
    midgame_max_occupied_count: int = 22
    crowded_min_occupied_count: int = 22
    crowded_max_occupied_count: int = 34
    canvas_width: int = 980
    canvas_height: int = 900
    panel_margin_px: int = 48
    player_badge_height_px: int = 52
    player_badge_width_px: int = 220
    header_gap_px: int = 18
    max_board_width_px: int = 780
    board_corner_radius_px: int = 30
    board_frame_width_px: int = 16
    disc_inset_fraction: float = 0.14
    player_badge_font_size_px: int = 22
    marked_square_outline_width_px: int = 6


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one Connect Four scene."""

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
class _QueryEvaluation:
    """Query-specific evaluation payload derived from one finalized board."""

    answer: int
    evidence_coords: Tuple[Coord, ...]
    evidence_entity_ids: Tuple[str, ...]
    winning_move_coords: Tuple[Coord, ...]
    safe_move_coords: Tuple[Coord, ...]


@dataclass(frozen=True)
class _SampledConnectFourScene:
    """One sampled Connect Four scene plus query-specific witness metadata."""

    board: Board
    current_player: int
    evaluation: _QueryEvaluation
    occupied_count: int
    construction_mode: str


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "connect_four")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_games_background_defaults(task_group="connect_four")
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="connect_four", apply_prob=0.0)


def _target_support_key(query_variant: str) -> str:
    """Return the configured answer-support key for one query variant."""

    return {
        "winning_move_count": "winning_move_count_support",
        "safe_move_count": "safe_move_count_support",
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
    """Resolve one balanced named axis for the Connect Four task."""

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
    """Resolve all semantic and visual sampling axes for one Connect Four instance."""

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


def _render_params(params: Mapping[str, Any]) -> ConnectFourRenderParams:
    """Resolve Connect Four rendering parameters from config/defaults."""

    return ConnectFourRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
        canvas_height=int(
            params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))
        ),
        panel_margin_px=int(
            params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px))
        ),
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
        max_board_width_px=int(
            params.get(
                "max_board_width_px",
                group_default(_RENDER_DEFAULTS, "max_board_width_px", _DEFAULTS.max_board_width_px),
            )
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
        marked_square_outline_width_px=int(
            params.get(
                "marked_square_outline_width_px",
                group_default(_RENDER_DEFAULTS, "marked_square_outline_width_px", _DEFAULTS.marked_square_outline_width_px),
            )
        ),
    )


def _mutable_board(board: Board | None = None) -> List[List[int]]:
    """Return one mutable board copy."""

    if board is None:
        board = empty_board()
    return [list(int(cell) for cell in row) for row in board]


def _freeze_board(board: Sequence[Sequence[int]]) -> Board:
    """Freeze one mutable board into the canonical tuple form."""

    return tuple(tuple(int(cell) for cell in row) for row in board)


def _resolve_current_player(rng, *, params: Mapping[str, Any]) -> int:
    """Resolve the current player for one scene."""

    explicit = params.get("current_player")
    if explicit is None:
        return int(RED if int(rng.randrange(2)) == 0 else YELLOW)
    text = str(explicit).strip().lower()
    if text in {"red", "r", "1"}:
        return int(RED)
    if text in {"yellow", "y", "-1"}:
        return int(YELLOW)
    raise ValueError(f"unsupported current_player: {explicit}")


def _safe_move_coords(board: Board, *, current_player: int) -> Tuple[Coord, ...]:
    """Return every legal landing square that leaves the opponent without an immediate win."""

    coords: List[Coord] = []
    opposing_player = int(opponent(int(current_player)))
    for col in sorted(legal_drop_rows(board).keys()):
        next_board, landing_coord = drop_disc(board, int(current_player), int(col))
        if has_connect_four(next_board, int(current_player)):
            continue
        if not winning_drop_map(next_board, int(opposing_player)):
            coords.append(tuple(landing_coord))
    return tuple(sorted(tuple(coord) for coord in coords))


def _evaluate_query(
    *,
    board: Board,
    current_player: int,
    query_variant: str,
) -> _QueryEvaluation | None:
    """Evaluate one query variant on one visible board."""

    current_wins = winning_drop_map(board, int(current_player))
    winning_coords = tuple(sorted(tuple(coord) for coord, _ in current_wins.values()))
    safe_coords = _safe_move_coords(board, current_player=int(current_player))

    if str(query_variant) == "winning_move_count":
        evidence_coords = winning_coords
    elif str(query_variant) == "safe_move_count":
        evidence_coords = safe_coords
    else:
        return None

    return _QueryEvaluation(
        answer=int(len(evidence_coords)),
        evidence_coords=tuple(tuple(coord) for coord in evidence_coords),
        evidence_entity_ids=tuple(coord_to_cell_id(coord) for coord in evidence_coords),
        winning_move_coords=winning_coords,
        safe_move_coords=safe_coords,
    )


def _construct_vertical_threat_base(
    *,
    rng,
    current_player: int,
    target_answer: int,
) -> Tuple[Board, str]:
    """Construct one sparse vertical-threat base board for immediate-win counting."""

    board = _mutable_board()
    candidate_columns = (0, 2, 4, 6)
    selected_columns = [] if int(target_answer) == 0 else list(rng.sample(candidate_columns, k=int(target_answer)))
    for col in selected_columns:
        for row in (5, 4, 3):
            board[int(row)][int(col)] = int(current_player)
    return _freeze_board(board), "vertical_threats"


def _occupancy_bounds(scene_variant: str) -> Tuple[int, int]:
    """Return occupied-cell lower and upper bounds for one scene variant."""

    if str(scene_variant) == "crowded_board":
        return (int(_DEFAULTS.crowded_min_occupied_count), int(_DEFAULTS.crowded_max_occupied_count))
    return (int(_DEFAULTS.midgame_min_occupied_count), int(_DEFAULTS.midgame_max_occupied_count))


def _augment_board_density(
    *,
    rng,
    board: Board,
    current_player: int,
    query_variant: str,
    target_answer: int,
    scene_variant: str,
) -> Board:
    """Densify one valid board while preserving the query answer."""

    minimum_occupied, maximum_occupied = _occupancy_bounds(str(scene_variant))
    current_board = board
    if int(occupied_cell_count(current_board)) > int(maximum_occupied):
        raise ValueError("base board already exceeds the requested scene occupancy bound")
    if int(occupied_cell_count(current_board)) >= int(minimum_occupied):
        return current_board

    opposing_player = int(opponent(int(current_player)))
    for _ in range(320):
        if int(occupied_cell_count(current_board)) >= int(minimum_occupied):
            break
        landing_rows = legal_drop_rows(current_board)
        candidate_columns = [int(col) for col in sorted(landing_rows.keys())]
        if not candidate_columns:
            break
        success = False
        for _ in range(96):
            candidate_column = int(candidate_columns[int(rng.randrange(len(candidate_columns)))])
            filler_player = int(current_player) if float(rng.random()) < 0.35 else int(opposing_player)
            next_board, _ = drop_disc(current_board, int(filler_player), int(candidate_column))
            if int(occupied_cell_count(next_board)) > int(maximum_occupied):
                continue
            if has_connect_four(next_board, int(current_player)) or has_connect_four(next_board, int(opposing_player)):
                continue
            evaluation = _evaluate_query(
                board=next_board,
                current_player=int(current_player),
                query_variant=str(query_variant),
            )
            if evaluation is None or int(evaluation.answer) != int(target_answer):
                continue
            current_board = next_board
            success = True
            break
        if not success:
            break
    if int(occupied_cell_count(current_board)) < int(minimum_occupied):
        raise ValueError("failed to densify Connect Four board into the requested scene variant range")
    return current_board


def _sample_column_heights(*, rng, occupied: int) -> List[int]:
    """Sample one gravity-consistent column-height composition for the requested occupancy."""

    heights = [0] * COLUMNS
    columns = list(range(COLUMNS))
    rng.shuffle(columns)
    remaining = int(occupied)
    for index, col in enumerate(columns):
        remaining_columns = int(COLUMNS - index - 1)
        min_height = max(0, int(remaining - (remaining_columns * ROWS)))
        max_height = min(int(ROWS), int(remaining))
        height = int(rng.randint(min_height, max_height))
        heights[int(col)] = int(height)
        remaining -= int(height)
    return heights


def _random_gravity_board(
    *,
    rng,
    minimum_occupied: int,
    maximum_occupied: int,
    current_player: int,
) -> Board:
    """Return one random gravity-consistent non-terminal board."""

    feasible_occupied = []
    for occupied in range(int(minimum_occupied), int(maximum_occupied) + 1):
        if occupied >= int(ROWS * COLUMNS):
            continue
        if int(current_player) == int(RED) and int(occupied) % 2 == 0:
            feasible_occupied.append(int(occupied))
        if int(current_player) == int(YELLOW) and int(occupied) % 2 == 1:
            feasible_occupied.append(int(occupied))
    if not feasible_occupied:
        raise ValueError("no feasible occupied counts match the requested current-player parity")

    for _ in range(1024):
        occupied = int(feasible_occupied[int(rng.randrange(len(feasible_occupied)))])
        heights = _sample_column_heights(rng=rng, occupied=int(occupied))
        if max(heights) == 0:
            continue
        if int(current_player) == int(RED):
            red_count = yellow_count = int(occupied // 2)
        else:
            red_count = int((occupied + 1) // 2)
            yellow_count = int((occupied - 1) // 2)
        colors = [int(RED)] * int(red_count) + [int(YELLOW)] * int(yellow_count)
        rng.shuffle(colors)
        board = _mutable_board()
        color_index = 0
        for col in range(COLUMNS):
            for offset in range(int(heights[col])):
                row = int(ROWS - 1 - offset)
                board[row][col] = int(colors[color_index])
                color_index += 1
        frozen = _freeze_board(board)
        if has_connect_four(frozen, int(RED)) or has_connect_four(frozen, int(YELLOW)):
            continue
        return frozen
    raise ValueError("failed to sample one gravity-consistent Connect Four board")


def _construct_safe_move_board(
    *,
    rng,
    current_player: int,
    target_answer: int,
    scene_variant: str,
) -> Tuple[Board, str]:
    """Construct one board whose safe-move count matches the requested answer."""

    minimum_occupied, maximum_occupied = _occupancy_bounds(str(scene_variant))
    for _ in range(4096):
        board = _random_gravity_board(
            rng=rng,
            minimum_occupied=int(minimum_occupied),
            maximum_occupied=int(maximum_occupied),
            current_player=int(current_player),
        )
        if winning_drop_map(board, int(current_player)):
            continue
        evaluation = _evaluate_query(
            board=board,
            current_player=int(current_player),
            query_variant="safe_move_count",
        )
        if evaluation is None or int(evaluation.answer) != int(target_answer):
            continue
        return board, "safe_move_search"
    raise ValueError("failed to construct one safe-move Connect Four board")


def _sample_scene(*, rng, axes: _ResolvedAxes, params: Mapping[str, Any]) -> _SampledConnectFourScene:
    """Construct one Connect Four scene consistent with the requested axes."""

    current_player = _resolve_current_player(rng, params=params)
    if str(axes.query_variant) == "winning_move_count":
        base_board, construction_mode = _construct_vertical_threat_base(
            rng=rng,
            current_player=int(current_player),
            target_answer=int(axes.target_answer),
        )
        board = _augment_board_density(
            rng=rng,
            board=base_board,
            current_player=int(current_player),
            query_variant=str(axes.query_variant),
            target_answer=int(axes.target_answer),
            scene_variant=str(axes.scene_variant),
        )
    else:
        board, construction_mode = _construct_safe_move_board(
            rng=rng,
            current_player=int(current_player),
            target_answer=int(axes.target_answer),
            scene_variant=str(axes.scene_variant),
        )

    evaluation = _evaluate_query(
        board=board,
        current_player=int(current_player),
        query_variant=str(axes.query_variant),
    )
    if evaluation is None or int(evaluation.answer) != int(axes.target_answer):
        raise ValueError("final Connect Four board does not match the requested target answer")
    return _SampledConnectFourScene(
        board=board,
        current_player=int(current_player),
        evaluation=evaluation,
        occupied_count=int(occupied_cell_count(board)),
        construction_mode=str(construction_mode),
    )


def _build_prompt_json_examples() -> Tuple[str, str]:
    """Return deterministic prompt examples for Connect Four JSON output."""

    answer_value = 2
    evidence_value = [[210, 340, 300, 430], [390, 340, 480, 430]]
    return (
        json.dumps({"evidence": evidence_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


@register_task
class GamesConnectFourMoveCountTask:
    """Return one grounded counting query over a visible Connect Four board."""

    task_id = TASK_ID
    domain = "games"
    task_group = "connect_four"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        render_params = _render_params(params)

        sampled_scene: _SampledConnectFourScene | None = None
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
        rendered_scene = render_connect_four_board_scene(
            board=sampled_scene.board,
            background=background,
            scene_variant=str(axes.scene_variant),
            style_variant=str(axes.style_variant),
            current_player=int(sampled_scene.current_player),
            params=render_params,
            marked_square=None,
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
                "legal_drop_rule_text",
                "winning_rule_text",
                "safety_rule_text",
                "answer_hint_winning_move_count",
                "answer_hint_safe_move_count",
                "evidence_hint_winning_move_count",
                "evidence_hint_safe_move_count",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples()
        current_player_name = player_name(int(sampled_scene.current_player))
        opponent_player_name = player_name(int(opponent(int(sampled_scene.current_player))))
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
                "opponent_player_name": str(opponent_player_name),
                "legal_drop_rule_text": str(prompt_defaults["legal_drop_rule_text"]),
                "winning_rule_text": str(prompt_defaults["winning_rule_text"]),
                "safety_rule_text": str(prompt_defaults["safety_rule_text"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(sampled_scene.evaluation.answer))
        evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in evidence_bboxes])
        complexity = build_games_connect_four_move_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
            scene_variant=str(axes.scene_variant),
            query_variant=str(axes.query_variant),
            occupied_count=int(sampled_scene.occupied_count),
            target_answer=int(axes.target_answer),
            evidence_count=len(sampled_scene.evaluation.evidence_entity_ids),
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_connect_four_board_{str(axes.scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_variant": str(axes.query_variant),
                    "task_variant": str(axes.query_variant),
                    "style_variant": str(axes.style_variant),
                    "current_player": str(current_player_name),
                    "target_answer": int(sampled_scene.evaluation.answer),
                    "occupied_count": int(sampled_scene.occupied_count),
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
                    "current_player": str(current_player_name),
                    "opponent_player": str(opponent_player_name),
                    "target_answer": int(sampled_scene.evaluation.answer),
                    "target_answer_support": [int(value) for value in axes.target_answer_support],
                    "target_answer_probabilities": dict(axes.target_answer_probabilities),
                    "occupied_count": int(sampled_scene.occupied_count),
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
                "current_player": str(current_player_name),
                "opponent_player": str(opponent_player_name),
                "target_answer": int(sampled_scene.evaluation.answer),
                "target_answer_support": [int(value) for value in axes.target_answer_support],
                "occupied_count": int(sampled_scene.occupied_count),
                "construction_mode": str(sampled_scene.construction_mode),
                "board_rows": [[int(cell) for cell in row] for row in sampled_scene.board],
                "winning_move_coords": [[int(coord[0]), int(coord[1])] for coord in sampled_scene.evaluation.winning_move_coords],
                "safe_move_coords": [[int(coord[0]), int(coord[1])] for coord in sampled_scene.evaluation.safe_move_coords],
                "evidence_coords": [[int(coord[0]), int(coord[1])] for coord in sampled_scene.evaluation.evidence_coords],
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


__all__ = ["GamesConnectFourMoveCountTask"]
