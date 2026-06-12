"""Ultimate Tic-Tac-Toe board-status and local-tactic tasks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_scene_generation_rendering_prompt_defaults
from ...shared.font_assets import get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_scene_prompt_variants
from ...shared.support_sampling import resolve_integer_choice
from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from ..shared.text import draw_game_text_traced as draw_text_traced
from ..shared.layout import (
    apply_games_layout_jitter_to_bbox,
    attach_games_unit_size_jitter,
    resolve_games_layout_jitter,
    resolve_games_unit_size_scale,
    scale_games_px,
)
from ..shared.sampling import resolve_games_named_axis
from ..shared.scene_style import draw_panel_grid_cell, draw_panel_scene_chrome, make_panel_scene_background, resolve_game_panel_scene_style
from ..shared.visual_defaults import load_games_scene_noise_defaults


SCENE_ID = "ultimate_tictactoe"
SCENE_ID = "ultimate_tictactoe"
QUERY_X_WON_COUNT = "x_won_board_count"
QUERY_O_WON_COUNT = "o_won_board_count"
QUERY_NEITHER_WON_COUNT = "neither_won_board_count"
QUERY_DRAWN_COUNT = "drawn_board_count"
QUERY_X_WIN_MOVE = "x_winning_move_label"
QUERY_O_WIN_MOVE = "o_winning_move_label"
QUERY_X_BLOCK_MOVE = "x_blocking_move_label"
QUERY_O_BLOCK_MOVE = "o_blocking_move_label"
QUERY_X_IMMEDIATE_WIN_BOARD_COUNT = "x_immediate_win_board_count"
QUERY_O_IMMEDIATE_WIN_BOARD_COUNT = "o_immediate_win_board_count"
STATUS_QUERIES: Tuple[str, ...] = (
    QUERY_X_WON_COUNT,
    QUERY_O_WON_COUNT,
    QUERY_NEITHER_WON_COUNT,
    QUERY_DRAWN_COUNT,
)
TACTIC_QUERIES: Tuple[str, ...] = (
    QUERY_X_WIN_MOVE,
    QUERY_O_WIN_MOVE,
    QUERY_X_BLOCK_MOVE,
    QUERY_O_BLOCK_MOVE,
)
MACRO_THREAT_QUERIES: Tuple[str, ...] = (
    QUERY_X_IMMEDIATE_WIN_BOARD_COUNT,
    QUERY_O_IMMEDIATE_WIN_BOARD_COUNT,
)
SUPPORTED_STYLE_VARIANTS: Tuple[str, ...] = (
    "classic_grid",
    "soft_marker",
    "paper_grid",
    "neon_board",
    "tournament_board",
)
LOCAL_LINES: Tuple[Tuple[int, int, int], ...] = (
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 3, 6),
    (1, 4, 7),
    (2, 5, 8),
    (0, 4, 8),
    (2, 4, 6),
)
MACRO_LABELS: Tuple[str, ...] = tuple("ABCDEFGHI")
OPTION_LABELS: Tuple[str, ...] = tuple("ABCDEFGH")


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for Ultimate Tic-Tac-Toe tasks."""

    won_board_count_support: Tuple[int, ...] = (1, 2, 3, 4, 5)
    drawn_board_count_support: Tuple[int, ...] = (1, 2, 3, 4, 5)
    neither_won_board_count_support: Tuple[int, ...] = (2, 3, 4, 5, 6)
    macro_threat_board_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    option_count_support: Tuple[int, ...] = (5,)
    canvas_width: int = 820
    canvas_height: int = 820
    panel_margin_px: int = 42
    board_inner_margin_px: int = 48
    local_cell_size_px: int = 58
    local_gap_px: int = 3
    macro_gap_px: int = 10
    symbol_font_size_px: int = 33
    option_font_size_px: int = 18
    label_font_size_px: int = 18
    small_board_border_width_px: int = 8
    highlight_width_px: int = 6


Board = Tuple[Tuple[str, ...], ...]
BBox = Tuple[float, float, float, float]


@dataclass(frozen=True)
class _LocalBoard:
    """One local 3x3 board inside the Ultimate board."""

    cells: Tuple[str, ...]
    status: str
    winning_line: Tuple[int, int, int] | None = None


@dataclass(frozen=True)
class _Sample:
    """Constructed Ultimate Tic-Tac-Toe scene and query witness."""

    query_id: str
    board: Tuple[_LocalBoard, ...]
    answer: int | str
    answer_type: str
    target_answer: int | None
    highlighted_board_index: int | None
    option_cells: Tuple[int, ...]
    answer_cell: int | None
    support_cells: Tuple[int, ...]
    annotation_entity_ids: Tuple[str, ...]
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class _RenderedScene:
    """Rendered Ultimate Tic-Tac-Toe scene and trace maps."""

    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]
    style_meta: Dict[str, Any]
    background_meta: Dict[str, Any]


@dataclass(frozen=True)
class _BoardVisualStyle:
    """Resolved nonsemantic board styling for one Ultimate Tic-Tac-Toe render."""

    cell_fill_rgb: Tuple[int, int, int]
    board_fill_rgb: Tuple[int, int, int]
    grid_rgb: Tuple[int, int, int]
    border_rgb: Tuple[int, int, int]
    highlight_rgb: Tuple[int, int, int]
    x_rgb: Tuple[int, int, int]
    o_rgb: Tuple[int, int, int]
    option_fill_rgb: Tuple[int, int, int]
    option_outline_rgb: Tuple[int, int, int]
    option_text_rgb: Tuple[int, int, int]


_DEFAULTS = _TaskDefaults()
_SCENE_DEFAULTS = get_scene_defaults("games", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id="games_ultimate_tictactoe_base",
)
POST_IMAGE_NOISE_DEFAULTS = load_games_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.5)


def _int_default(params: Mapping[str, Any], key: str, fallback: int) -> int:
    if str(key) in params:
        return int(params[str(key)])
    return int(group_default(_RENDER_DEFAULTS, str(key), int(fallback)))


def _sample_integer_axis(
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    support_key: str,
    explicit_key: str,
    fallback_support: Sequence[int],
    namespace: str,
    balanced_flag_key: str,
) -> Tuple[int, Dict[str, float]]:
    value, probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=str(support_key),
        explicit_key=str(explicit_key),
        fallback_support=tuple(int(item) for item in fallback_support),
        namespace=f"{str(task_id)}.{str(namespace)}",
        balanced_flag_key=str(balanced_flag_key),
        namespace_support_permutation=True,
    )
    return int(value), dict(probabilities)


def _sample_named_axis(
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    supported: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    return resolve_games_named_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        namespace=str(namespace),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        supported_variants=tuple(str(item) for item in supported),
    )


def _query_params_for_inner_cycle(
    params: Mapping[str, Any],
    *,
    query_count: int,
) -> Dict[str, Any]:
    resolved = dict(params)
    sampling_index = params.get("_sample_cursor")
    if sampling_index is None or params.get("query_id") is not None or params.get("query_variant") is not None:
        return resolved
    resolved["_sample_cursor"] = abs(int(sampling_index)) // max(1, int(query_count))
    return resolved


def _board_entity_id(index: int) -> str:
    return f"small_board_{MACRO_LABELS[int(index)].lower()}"


def _cell_entity_id(board_index: int, cell_index: int) -> str:
    return f"{_board_entity_id(int(board_index))}_cell_{int(cell_index) + 1}"


def _status_of(cells: Sequence[str]) -> Tuple[str, Tuple[int, int, int] | None]:
    for line in LOCAL_LINES:
        values = [str(cells[index]) for index in line]
        if values[0] and values[0] == values[1] == values[2]:
            return f"{values[0]}_won", tuple(int(item) for item in line)
    if all(str(value) for value in cells):
        return "drawn", None
    return "open", None


def _immediate_winning_cells(cells: Sequence[str], player: str) -> Tuple[int, ...]:
    wins: List[int] = []
    for line in LOCAL_LINES:
        values = [str(cells[index]) for index in line]
        if values.count(str(player)) == 2 and values.count("") == 1:
            wins.append(int(line[values.index("")]))
    return tuple(sorted(set(wins)))


def _drawn_cells() -> Tuple[str, ...]:
    return ("X", "O", "X", "X", "O", "O", "O", "X", "X")


def _won_cells(rng, player: str) -> Tuple[Tuple[str, ...], Tuple[int, int, int]]:
    line = tuple(rng.choice(LOCAL_LINES))
    cells = [""] * 9
    for index in line:
        cells[int(index)] = str(player)
    available = [index for index in range(9) if index not in set(line)]
    rng.shuffle(available)
    fill_count = int(rng.randrange(1, 4))
    opponent = "O" if str(player) == "X" else "X"
    for index in available[:fill_count]:
        cells[int(index)] = str(opponent if rng.random() < 0.7 else player)
        status, winner_line = _status_of(cells)
        if str(status) != f"{str(player)}_won":
            cells[int(index)] = opponent
        elif winner_line is not None and set(winner_line) != set(line):
            cells[int(index)] = opponent
    return tuple(cells), tuple(int(item) for item in line)


def _open_cells(rng) -> Tuple[str, ...]:
    for _attempt in range(200):
        cells = [""] * 9
        indices = list(range(9))
        rng.shuffle(indices)
        fill_count = int(rng.randrange(3, 6))
        for idx, cell_index in enumerate(indices[:fill_count]):
            cells[int(cell_index)] = "X" if idx % 2 == 0 else "O"
        status, _line = _status_of(cells)
        if status == "open":
            return tuple(cells)
    return ("X", "", "O", "", "X", "", "O", "", "")


def _open_cells_without_immediate_win(rng, *, player: str) -> Tuple[str, ...]:
    """Sample an open local board where the requested player has no one-move win."""

    target_player = str(player)
    for _attempt in range(400):
        cells = _open_cells(rng)
        if not _immediate_winning_cells(cells, target_player):
            return tuple(cells)
    fallback = ("X", "O", "", "", "X", "O", "O", "", "")
    if target_player == "X":
        fallback = ("O", "X", "", "", "O", "X", "X", "", "")
    if _immediate_winning_cells(fallback, target_player):
        raise ValueError("failed to construct open board without immediate win")
    return tuple(fallback)


def _local_board_for_status(rng, status: str) -> _LocalBoard:
    if str(status) == "X_won":
        cells, line = _won_cells(rng, "X")
        return _LocalBoard(cells=tuple(cells), status="X_won", winning_line=tuple(line))
    if str(status) == "O_won":
        cells, line = _won_cells(rng, "O")
        return _LocalBoard(cells=tuple(cells), status="O_won", winning_line=tuple(line))
    if str(status) == "drawn":
        return _LocalBoard(cells=_drawn_cells(), status="drawn", winning_line=None)
    return _LocalBoard(cells=_open_cells(rng), status="open", winning_line=None)


def _macro_threat_player(query_id: str) -> str:
    """Return the player whose immediate-win boards are counted."""

    if str(query_id) == QUERY_X_IMMEDIATE_WIN_BOARD_COUNT:
        return "X"
    if str(query_id) == QUERY_O_IMMEDIATE_WIN_BOARD_COUNT:
        return "O"
    raise ValueError(f"unsupported macro-threat query: {query_id}")


def _matching_macro_threat_indices(board: Sequence[_LocalBoard], query_id: str) -> Tuple[int, ...]:
    """Return small-board indices where the queried player can win in one move."""

    player = _macro_threat_player(str(query_id))
    return tuple(
        int(index)
        for index, local in enumerate(board)
        if local.status == "open" and bool(_immediate_winning_cells(local.cells, player))
    )


def _matching_status_indices(board: Sequence[_LocalBoard], query_id: str) -> Tuple[int, ...]:
    if str(query_id) == QUERY_X_WON_COUNT:
        return tuple(index for index, local in enumerate(board) if local.status == "X_won")
    if str(query_id) == QUERY_O_WON_COUNT:
        return tuple(index for index, local in enumerate(board) if local.status == "O_won")
    if str(query_id) == QUERY_DRAWN_COUNT:
        return tuple(index for index, local in enumerate(board) if local.status == "drawn")
    return tuple(index for index, local in enumerate(board) if local.status in {"drawn", "open"})


def _target_support_for_status_query(query_id: str) -> Tuple[str, Tuple[int, ...]]:
    if str(query_id) in {QUERY_X_WON_COUNT, QUERY_O_WON_COUNT}:
        return "won_board_count_support", _DEFAULTS.won_board_count_support
    if str(query_id) == QUERY_DRAWN_COUNT:
        return "drawn_board_count_support", _DEFAULTS.drawn_board_count_support
    return "neither_won_board_count_support", _DEFAULTS.neither_won_board_count_support


def _counts_for_query_target(rng, *, query_id: str, target_answer: int) -> Dict[str, int]:
    counts = {"X_won": 0, "O_won": 0, "drawn": 0, "open": 0}
    if str(query_id) == QUERY_X_WON_COUNT:
        counts["X_won"] = int(target_answer)
        remaining = 9 - int(target_answer)
        counts["O_won"] = int(rng.randrange(1, min(4, remaining) + 1))
        remaining -= counts["O_won"]
        counts["drawn"] = int(rng.randrange(0, min(3, remaining) + 1))
        counts["open"] = remaining - counts["drawn"]
    elif str(query_id) == QUERY_O_WON_COUNT:
        counts["O_won"] = int(target_answer)
        remaining = 9 - int(target_answer)
        counts["X_won"] = int(rng.randrange(1, min(4, remaining) + 1))
        remaining -= counts["X_won"]
        counts["drawn"] = int(rng.randrange(0, min(3, remaining) + 1))
        counts["open"] = remaining - counts["drawn"]
    elif str(query_id) == QUERY_DRAWN_COUNT:
        counts["drawn"] = int(target_answer)
        remaining = 9 - int(target_answer)
        if remaining < 2:
            raise ValueError("drawn-board target leaves no room for both winners")
        counts["X_won"] = int(rng.randrange(1, min(4, remaining - 1) + 1))
        remaining -= counts["X_won"]
        counts["O_won"] = int(rng.randrange(1, min(4, remaining) + 1))
        remaining -= counts["O_won"]
        counts["open"] = remaining
    else:
        neither = int(target_answer)
        counts["drawn"] = int(rng.randrange(0, min(3, neither) + 1))
        counts["open"] = neither - counts["drawn"]
        remaining = 9 - neither
        counts["X_won"] = int(rng.randrange(0, remaining + 1))
        counts["O_won"] = remaining - counts["X_won"]
    return counts


def _sample_status_count(
    rng,
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    query_id: str,
) -> _Sample:
    support_key, fallback = _target_support_for_status_query(str(query_id))
    target_answer, target_probabilities = _sample_integer_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=_query_params_for_inner_cycle(params, query_count=len(STATUS_QUERIES)),
        support_key=str(support_key),
        explicit_key="target_answer",
        fallback_support=fallback,
        namespace=f"{str(query_id)}.target_answer",
        balanced_flag_key="balanced_target_answer_sampling",
    )
    counts = _counts_for_query_target(rng, query_id=str(query_id), target_answer=int(target_answer))
    statuses: List[str] = []
    for status, count in counts.items():
        statuses.extend([str(status)] * int(count))
    if len(statuses) != 9:
        raise ValueError(f"status count construction produced {len(statuses)} boards")
    rng.shuffle(statuses)
    board = tuple(_local_board_for_status(rng, status) for status in statuses)
    matching = _matching_status_indices(board, str(query_id))
    if len(matching) != int(target_answer):
        raise ValueError("status target count mismatch")
    annotation_ids = tuple(_board_entity_id(index) for index in matching)
    return _Sample(
        query_id=str(query_id),
        board=tuple(board),
        answer=int(target_answer),
        answer_type="integer",
        target_answer=int(target_answer),
        highlighted_board_index=None,
        option_cells=(),
        answer_cell=None,
        support_cells=(),
        annotation_entity_ids=tuple(annotation_ids),
        metadata={
            "target_answer": int(target_answer),
            "target_answer_probabilities": dict(target_probabilities),
            "status_counts": dict(counts),
            "matching_small_boards": [MACRO_LABELS[index] for index in matching],
        },
    )


def _sample_non_threat_board(rng, *, player: str) -> _LocalBoard:
    """Sample one non-counted small board for the macro-threat task."""

    status = str(rng.choice(("X_won", "O_won", "drawn", "open_no_target_threat")))
    if status == "open_no_target_threat":
        return _LocalBoard(
            cells=_open_cells_without_immediate_win(rng, player=str(player)),
            status="open",
            winning_line=None,
        )
    return _local_board_for_status(rng, status)


def _sample_macro_threat_count(
    rng,
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    query_id: str,
) -> _Sample:
    """Sample an Ultimate board with an exact count of immediate-win local boards."""

    target_answer, target_probabilities = _sample_integer_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=_query_params_for_inner_cycle(params, query_count=len(MACRO_THREAT_QUERIES)),
        support_key="macro_threat_board_count_support",
        explicit_key="target_answer",
        fallback_support=_DEFAULTS.macro_threat_board_count_support,
        namespace=f"{str(query_id)}.target_answer",
        balanced_flag_key="balanced_target_answer_sampling",
    )
    player = _macro_threat_player(str(query_id))
    tactic_query = QUERY_X_WIN_MOVE if str(player) == "X" else QUERY_O_WIN_MOVE
    boards: List[_LocalBoard] = []
    for _index in range(int(target_answer)):
        cells, _answer_cell, _support_cells, _threat_player = _make_tactic_cells(rng, query_id=str(tactic_query))
        boards.append(_LocalBoard(cells=tuple(cells), status="open", winning_line=None))
    while len(boards) < 9:
        boards.append(_sample_non_threat_board(rng, player=str(player)))
    rng.shuffle(boards)
    board = tuple(boards)
    matching = _matching_macro_threat_indices(board, str(query_id))
    if len(matching) != int(target_answer):
        raise ValueError("macro-threat target count mismatch")
    annotation_ids = tuple(_board_entity_id(index) for index in matching)
    return _Sample(
        query_id=str(query_id),
        board=tuple(board),
        answer=int(target_answer),
        answer_type="integer",
        target_answer=int(target_answer),
        highlighted_board_index=None,
        option_cells=(),
        answer_cell=None,
        support_cells=(),
        annotation_entity_ids=tuple(annotation_ids),
        metadata={
            "target_answer": int(target_answer),
            "target_answer_probabilities": dict(target_probabilities),
            "threat_player": str(player),
            "matching_small_boards": [MACRO_LABELS[index] for index in matching],
        },
    )


def _sample_answer_slot(option_count: int, *, instance_seed: int, task_id: str, params: Mapping[str, Any]) -> int:
    explicit = params.get("answer_option_index")
    if explicit is not None:
        value = int(explicit)
        if 0 <= value < int(option_count):
            return int(value)
        raise ValueError("answer_option_index outside option_count")
    sampling_index = params.get("_sample_cursor")
    if sampling_index is not None:
        return abs(int(sampling_index)) % int(option_count)
    rng = spawn_rng(int(instance_seed), f"{str(task_id)}.answer_option_index")
    return int(rng.randrange(int(option_count)))


def _make_tactic_cells(rng, *, query_id: str) -> Tuple[Tuple[str, ...], int, Tuple[int, int], str]:
    if str(query_id) in {QUERY_X_WIN_MOVE, QUERY_O_WIN_MOVE}:
        player = "X" if str(query_id) == QUERY_X_WIN_MOVE else "O"
        threat_player = player
    else:
        player = "X" if str(query_id) == QUERY_X_BLOCK_MOVE else "O"
        threat_player = "O" if str(query_id) == QUERY_X_BLOCK_MOVE else "X"
    opponent = "O" if str(threat_player) == "X" else "X"
    for _attempt in range(800):
        line = tuple(rng.choice(LOCAL_LINES))
        answer_cell = int(rng.choice(line))
        support = tuple(int(index) for index in line if int(index) != int(answer_cell))
        cells = [""] * 9
        for index in support:
            cells[int(index)] = str(threat_player)
        available = [index for index in range(9) if index not in set(line)]
        rng.shuffle(available)
        for index in available[:2]:
            cells[int(index)] = str(opponent if rng.random() < 0.75 else threat_player)
        status, _winner_line = _status_of(cells)
        if status != "open":
            continue
        wins = _immediate_winning_cells(cells, str(threat_player))
        if tuple(wins) != (int(answer_cell),):
            continue
        if str(query_id) in {QUERY_X_BLOCK_MOVE, QUERY_O_BLOCK_MOVE} and _immediate_winning_cells(cells, str(player)):
            continue
        empties = [index for index, value in enumerate(cells) if not value]
        if len(empties) < 5:
            continue
        return tuple(cells), int(answer_cell), tuple(support), str(threat_player)
    raise ValueError("failed to construct unique local tactic")


def _sample_local_tactic(
    rng,
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    query_id: str,
) -> _Sample:
    option_count, option_probabilities = _sample_integer_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        support_key="option_count_support",
        explicit_key="option_count",
        fallback_support=_DEFAULTS.option_count_support,
        namespace="option_count",
        balanced_flag_key="balanced_target_answer_sampling",
    )
    tactic_cells, answer_cell, support_cells, threat_player = _make_tactic_cells(rng, query_id=str(query_id))
    empties = [index for index, value in enumerate(tactic_cells) if not value]
    distractors = [index for index in empties if int(index) != int(answer_cell)]
    rng.shuffle(distractors)
    answer_slot = _sample_answer_slot(
        int(option_count),
        instance_seed=int(instance_seed),
        task_id=str(task_id),
        params=params,
    )
    option_cells = distractors[: int(option_count) - 1]
    option_cells.insert(int(answer_slot), int(answer_cell))
    highlighted = int(rng.randrange(9))
    status_options = ["X_won", "O_won", "drawn", "open"]
    board_values: List[_LocalBoard] = []
    for index in range(9):
        if int(index) == int(highlighted):
            board_values.append(_LocalBoard(cells=tuple(tactic_cells), status="open", winning_line=None))
        else:
            board_values.append(_local_board_for_status(rng, str(rng.choice(status_options))))
    answer_label = OPTION_LABELS[int(answer_slot)]
    annotation_ids = tuple(
        [_cell_entity_id(int(highlighted), int(answer_cell))]
        + [_cell_entity_id(int(highlighted), int(cell_index)) for cell_index in support_cells]
    )
    return _Sample(
        query_id=str(query_id),
        board=tuple(board_values),
        answer=str(answer_label),
        answer_type="string",
        target_answer=None,
        highlighted_board_index=int(highlighted),
        option_cells=tuple(int(cell) for cell in option_cells),
        answer_cell=int(answer_cell),
        support_cells=tuple(int(cell) for cell in support_cells),
        annotation_entity_ids=tuple(annotation_ids),
        metadata={
            "highlighted_small_board": MACRO_LABELS[int(highlighted)],
            "option_count": int(option_count),
            "option_count_probabilities": dict(option_probabilities),
            "answer_option_index": int(answer_slot),
            "answer_label": str(answer_label),
            "answer_cell": int(answer_cell) + 1,
            "support_cells": [int(cell) + 1 for cell in support_cells],
            "threat_player": str(threat_player),
            "option_cells": [int(cell) + 1 for cell in option_cells],
        },
    )


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    bbox: Sequence[float],
    text: str,
    *,
    font,
    fill: Tuple[int, int, int],
    stroke_width: int = 1,
) -> None:
    text_bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=int(stroke_width))
    text_w = float(text_bbox[2] - text_bbox[0])
    text_h = float(text_bbox[3] - text_bbox[1])
    x0, y0, x1, y1 = [float(value) for value in bbox]
    draw_text_traced(draw,
        (float(x0 + ((x1 - x0) - text_w) / 2.0), float(y0 + ((y1 - y0) - text_h) / 2.0)),
        str(text),
        font=font,
        fill=tuple(fill),
        stroke_width=int(stroke_width),
        stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(fill)),
     role="readout", required=False,)


def _rgb(values: Sequence[int]) -> Tuple[int, int, int]:
    return tuple(max(0, min(255, int(value))) for value in values[:3])  # type: ignore[return-value]


def _blend_rgb(a: Sequence[int], b: Sequence[int], alpha: float) -> Tuple[int, int, int]:
    t = max(0.0, min(1.0, float(alpha)))
    return tuple(int(round((float(a[index]) * (1.0 - t)) + (float(b[index]) * t))) for index in range(3))


def _resolve_board_visual_style(style_variant: str, panel_style) -> Tuple[_BoardVisualStyle, Dict[str, Any]]:
    """Resolve scene-local board colors independent of the shared panel background."""

    panel_fill = _rgb(panel_style.panel_fill_rgb)
    panel_background = _rgb(panel_style.background_rgb)
    default_board = _blend_rgb(panel_fill, panel_background, 0.12)
    styles: Dict[str, _BoardVisualStyle] = {
        "classic_grid": _BoardVisualStyle(
            cell_fill_rgb=_blend_rgb(panel_fill, (255, 255, 255), 0.22),
            board_fill_rgb=default_board,
            grid_rgb=(116, 132, 158),
            border_rgb=(46, 61, 92),
            highlight_rgb=(232, 162, 42),
            x_rgb=(42, 92, 205),
            o_rgb=(203, 58, 68),
            option_fill_rgb=(255, 232, 102),
            option_outline_rgb=(48, 63, 95),
            option_text_rgb=(32, 36, 45),
        ),
        "soft_marker": _BoardVisualStyle(
            cell_fill_rgb=(238, 244, 247),
            board_fill_rgb=(226, 235, 239),
            grid_rgb=(133, 152, 158),
            border_rgb=(86, 103, 112),
            highlight_rgb=(78, 158, 151),
            x_rgb=(44, 118, 172),
            o_rgb=(190, 91, 101),
            option_fill_rgb=(239, 220, 143),
            option_outline_rgb=(65, 101, 109),
            option_text_rgb=(36, 45, 48),
        ),
        "paper_grid": _BoardVisualStyle(
            cell_fill_rgb=(248, 241, 222),
            board_fill_rgb=(237, 226, 202),
            grid_rgb=(166, 133, 94),
            border_rgb=(95, 68, 48),
            highlight_rgb=(185, 108, 54),
            x_rgb=(45, 82, 130),
            o_rgb=(157, 64, 62),
            option_fill_rgb=(252, 218, 128),
            option_outline_rgb=(113, 79, 45),
            option_text_rgb=(52, 40, 31),
        ),
        "neon_board": _BoardVisualStyle(
            cell_fill_rgb=(28, 34, 56),
            board_fill_rgb=(18, 23, 42),
            grid_rgb=(87, 119, 169),
            border_rgb=(73, 232, 237),
            highlight_rgb=(252, 211, 64),
            x_rgb=(87, 229, 244),
            o_rgb=(255, 99, 182),
            option_fill_rgb=(255, 224, 76),
            option_outline_rgb=(255, 255, 255),
            option_text_rgb=(28, 31, 39),
        ),
        "tournament_board": _BoardVisualStyle(
            cell_fill_rgb=(224, 235, 227),
            board_fill_rgb=(207, 224, 211),
            grid_rgb=(94, 128, 104),
            border_rgb=(40, 91, 64),
            highlight_rgb=(216, 158, 59),
            x_rgb=(32, 93, 164),
            o_rgb=(181, 58, 55),
            option_fill_rgb=(247, 230, 134),
            option_outline_rgb=(36, 92, 67),
            option_text_rgb=(26, 44, 35),
        ),
    }
    resolved_variant = str(style_variant) if str(style_variant) in styles else "classic_grid"
    resolved = styles[resolved_variant]
    return resolved, {
        "style_variant": str(resolved_variant),
        "available_styles": list(SUPPORTED_STYLE_VARIANTS),
        "board_style_policy": "scene_local_ultimate_tictactoe_board_palette",
    }


def _render_scene(
    *,
    sample: _Sample,
    task_id: str,
    style_variant: str,
    instance_seed: int,
    params: Mapping[str, Any],
) -> _RenderedScene:
    base_canvas_width = _int_default(params, "canvas_width", _DEFAULTS.canvas_width)
    base_canvas_height = _int_default(params, "canvas_height", _DEFAULTS.canvas_height)
    style, style_meta = resolve_game_panel_scene_style(
        instance_seed=int(instance_seed),
        namespace=f"{str(task_id)}.ultimate_tictactoe_panel_style",
        treatment_weights=group_default(_GEN_DEFAULTS, "panel_treatment_weights", {}),
        palette_weights=group_default(_GEN_DEFAULTS, "panel_palette_weights", {}),
    )
    layout_jitter = resolve_games_layout_jitter(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace=f"{str(task_id)}.ultimate_tictactoe.layout",
    )
    unit_scale, unit_meta = resolve_games_unit_size_scale(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace=f"{str(task_id)}.ultimate_tictactoe.unit_size",
    )
    local_cell = scale_games_px(_int_default(params, "local_cell_size_px", _DEFAULTS.local_cell_size_px), unit_scale, min_px=32)
    local_gap = scale_games_px(_int_default(params, "local_gap_px", _DEFAULTS.local_gap_px), unit_scale, min_px=2)
    macro_gap = scale_games_px(_int_default(params, "macro_gap_px", _DEFAULTS.macro_gap_px), unit_scale, min_px=6)
    inner_margin = scale_games_px(_int_default(params, "board_inner_margin_px", _DEFAULTS.board_inner_margin_px), unit_scale, min_px=28)
    local_size = int(3 * local_cell + 2 * local_gap)
    grid_size = int(3 * local_size + 2 * macro_gap)
    raw_panel_size = int(grid_size + 2 * inner_margin)
    dynamic_canvas_enabled = bool(
        params.get(
            "dynamic_canvas_size_enabled",
            group_default(_RENDER_DEFAULTS, "dynamic_canvas_size_enabled", True),
        )
    )
    canvas_width = int(base_canvas_width)
    canvas_height = int(base_canvas_height)
    if dynamic_canvas_enabled and params.get("canvas_width") is None:
        side_padding = _int_default(params, "canvas_side_padding_px", 72)
        canvas_width = min(
            int(base_canvas_width),
            max(_int_default(params, "canvas_min_width_px", 560), int(raw_panel_size + (2 * side_padding))),
        )
    if dynamic_canvas_enabled and params.get("canvas_height") is None:
        side_padding = _int_default(params, "canvas_side_padding_px", 72)
        canvas_height = min(
            int(base_canvas_height),
            max(_int_default(params, "canvas_min_height_px", 560), int(raw_panel_size + (2 * side_padding))),
        )
    panel_size = int(raw_panel_size)
    panel_size = min(
        int(panel_size),
        int(min(canvas_width, canvas_height) - 2 * _int_default(params, "panel_margin_px", _DEFAULTS.panel_margin_px)),
    )
    image, background_meta = make_panel_scene_background(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        style=style,
    )
    image = image.convert("RGBA")
    draw = ImageDraw.Draw(image)
    base_panel = (
        float((canvas_width - panel_size) / 2.0),
        float((canvas_height - panel_size) / 2.0),
        float((canvas_width + panel_size) / 2.0),
        float((canvas_height + panel_size) / 2.0),
    )
    panel_bbox, _dx, _dy, resolved_jitter = apply_games_layout_jitter_to_bbox(
        bbox_px=base_panel,
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        jitter=layout_jitter,
    )
    panel_bbox_i = tuple(int(round(value)) for value in panel_bbox)
    draw_panel_scene_chrome(draw, bbox=panel_bbox_i, style=style, radius=18, border_width=3)
    grid_left = int(round(panel_bbox[0])) + inner_margin
    grid_top = int(round(panel_bbox[1])) + inner_margin

    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"{str(task_id)}.ultimate_tictactoe.font_family",
        params=params,
    )
    symbol_font = load_font(
        scale_games_px(_int_default(params, "symbol_font_size_px", _DEFAULTS.symbol_font_size_px), unit_scale, min_px=18),
        bold=True,
        font_family=str(font_family),
    )
    option_font = load_font(
        scale_games_px(_int_default(params, "option_font_size_px", _DEFAULTS.option_font_size_px), unit_scale, min_px=13),
        bold=True,
        font_family=str(font_family),
    )
    board_style, board_style_meta = _resolve_board_visual_style(str(style_variant), style)
    grid_rgb = tuple(int(value) for value in board_style.grid_rgb)
    border_rgb = tuple(int(value) for value in board_style.border_rgb)
    mark_rgb = tuple(int(value) for value in board_style.option_outline_rgb)
    open_rgb = tuple(int(value) for value in board_style.cell_fill_rgb)
    board_fill_rgb = tuple(int(value) for value in board_style.board_fill_rgb)
    x_rgb = tuple(int(value) for value in board_style.x_rgb)
    o_rgb = tuple(int(value) for value in board_style.o_rgb)
    highlight_rgb = tuple(int(value) for value in board_style.highlight_rgb)
    small_board_border_width = scale_games_px(
        _int_default(params, "small_board_border_width_px", _DEFAULTS.small_board_border_width_px),
        unit_scale,
        min_px=5,
    )

    entities: List[Dict[str, Any]] = []
    entity_bboxes: Dict[str, List[float]] = {}
    small_board_bboxes: Dict[str, List[float]] = {}
    cell_bboxes_all: Dict[str, List[float]] = {}
    board_cell_bboxes: Dict[int, Dict[int, BBox]] = {}

    for board_index, local in enumerate(sample.board):
        macro_row = int(board_index // 3)
        macro_col = int(board_index % 3)
        bx0 = int(grid_left + macro_col * (local_size + macro_gap))
        by0 = int(grid_top + macro_row * (local_size + macro_gap))
        board_bbox = (float(bx0), float(by0), float(bx0 + local_size), float(by0 + local_size))
        board_id = _board_entity_id(int(board_index))
        fill = board_fill_rgb
        draw.rounded_rectangle(board_bbox, radius=6, fill=fill, outline=None)
        board_bbox_list = [round(float(value), 3) for value in board_bbox]
        entity_bboxes[board_id] = list(board_bbox_list)
        small_board_bboxes[board_id] = list(board_bbox_list)
        entities.append(
            {
                "entity_id": str(board_id),
                "entity_type": "ultimate_tictactoe_small_board",
                "label": MACRO_LABELS[int(board_index)],
                "status": str(local.status),
                "bbox_px": list(board_bbox_list),
            }
        )
        board_cell_bboxes[int(board_index)] = {}
        for cell_index, value in enumerate(local.cells):
            row = int(cell_index // 3)
            col = int(cell_index % 3)
            x0 = int(bx0 + col * (local_cell + local_gap))
            y0 = int(by0 + row * (local_cell + local_gap))
            cell_bbox = (float(x0), float(y0), float(x0 + local_cell), float(y0 + local_cell))
            draw_panel_grid_cell(draw, bbox=tuple(int(round(v)) for v in cell_bbox), fill=open_rgb, style=style, outline=grid_rgb, width=1)
            cell_id = _cell_entity_id(int(board_index), int(cell_index))
            board_cell_bboxes[int(board_index)][int(cell_index)] = tuple(cell_bbox)
            cell_bbox_list = [round(float(v), 3) for v in cell_bbox]
            entity_bboxes[cell_id] = list(cell_bbox_list)
            cell_bboxes_all[cell_id] = list(cell_bbox_list)
            entities.append(
                {
                    "entity_id": str(cell_id),
                    "entity_type": "ultimate_tictactoe_cell",
                    "small_board": MACRO_LABELS[int(board_index)],
                    "cell_index": int(cell_index + 1),
                    "mark": str(value),
                    "bbox_px": list(cell_bbox_list),
                }
            )
            if value:
                _draw_centered_text(
                    draw,
                    cell_bbox,
                    str(value),
                    font=symbol_font,
                    fill=x_rgb if str(value) == "X" else o_rgb,
                    stroke_width=1,
                )
        draw.rounded_rectangle(board_bbox, radius=6, fill=None, outline=border_rgb, width=int(small_board_border_width))
        if sample.highlighted_board_index is not None and int(board_index) == int(sample.highlighted_board_index):
            hw = scale_games_px(_int_default(params, "highlight_width_px", _DEFAULTS.highlight_width_px), unit_scale, min_px=4)
            draw.rounded_rectangle(
                (board_bbox[0] - 5, board_bbox[1] - 5, board_bbox[2] + 5, board_bbox[3] + 5),
                radius=9,
                outline=highlight_rgb,
                width=int(hw),
            )
    if sample.highlighted_board_index is not None:
        for option_index, cell_index in enumerate(sample.option_cells):
            label = OPTION_LABELS[int(option_index)]
            bbox = board_cell_bboxes[int(sample.highlighted_board_index)][int(cell_index)]
            radius = max(9.0, local_cell * 0.23)
            label_bbox = (bbox[2] - 2 * radius - 3, bbox[1] + 3, bbox[2] - 3, bbox[1] + 2 * radius + 3)
            draw.ellipse(label_bbox, fill=tuple(board_style.option_fill_rgb), outline=mark_rgb, width=2)
            _draw_centered_text(draw, label_bbox, label, font=option_font, fill=tuple(board_style.option_text_rgb), stroke_width=0)

    render_map = {
        "entity_bboxes_px": dict(entity_bboxes),
        "small_board_bboxes_px": dict(small_board_bboxes),
        "cell_bboxes_px": dict(cell_bboxes_all),
        "grid_bbox_px": [float(grid_left), float(grid_top), float(grid_left + grid_size), float(grid_top + grid_size)],
        "style": dict(style_meta),
        "panel_scene_style": dict(style_meta),
        "ultimate_tictactoe_board_style": dict(board_style_meta),
        "font_family": str(font_family),
        "text_style": {"font_family": str(font_family)},
        "layout_jitter": attach_games_unit_size_jitter(resolved_jitter, unit_meta),
        "effective_local_cell_size_px": int(local_cell),
        "effective_local_gap_px": int(local_gap),
        "dynamic_canvas": {
            "enabled": bool(dynamic_canvas_enabled),
            "base_canvas_width": int(base_canvas_width),
            "base_canvas_height": int(base_canvas_height),
            "raw_panel_size_px": int(raw_panel_size),
            "resolved_canvas_width": int(canvas_width),
            "resolved_canvas_height": int(canvas_height),
        },
    }
    return _RenderedScene(
        image=image.convert("RGB"),
        entities=tuple(entities),
        render_map=dict(render_map),
        style_meta={
            "panel_scene_style": dict(style_meta),
            "ultimate_tictactoe_board_style": dict(board_style_meta),
            "text_style": {
                "font_family": str(font_family),
                "font_asset": get_font_family_record(str(font_family)).to_trace(),
            },
        },
        background_meta=dict(background_meta),
    )


def _json_examples(query_id: str) -> Tuple[str, str]:
    if str(query_id) in TACTIC_QUERIES:
        answer_and_annotation = {
            "annotation": [[410, 240, 470, 300], [350, 240, 410, 300], [470, 240, 530, 300]],
            "answer": "C",
        }
        answer_only = {"answer": "C"}
    elif str(query_id) in MACRO_THREAT_QUERIES:
        answer_and_annotation = {"annotation": [[110, 110, 260, 260], [450, 280, 600, 430]], "answer": 2}
        answer_only = {"answer": 2}
    else:
        answer_and_annotation = {"annotation": [[110, 110, 260, 260], [450, 280, 600, 430]], "answer": 2}
        answer_only = {"answer": 2}
    return (
        json.dumps(answer_and_annotation, ensure_ascii=True, allow_nan=False, separators=(",", ":")),
        json.dumps(answer_only, ensure_ascii=True, allow_nan=False, separators=(",", ":")),
    )


def _build_prompt(sample: _Sample, *, instance_seed: int) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
    prompt_defaults = required_group_defaults(
        _PROMPT_DEFAULTS,
        (
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "object_description_ultimate_tictactoe_board",
            f"answer_hint_{str(sample.query_id)}",
            f"annotation_hint_{str(sample.query_id)}",
            "ultimate_tictactoe_status_rule_text",
            "ultimate_tictactoe_tactic_rule_text",
            "ultimate_tictactoe_macro_threat_rule_text",
        ),
        context=f"prompt defaults for {str(sample.query_id)}",
    )
    json_example, json_example_answer_only = _json_examples(str(sample.query_id))
    dynamic_slots = {
        "object_description": str(prompt_defaults["object_description_ultimate_tictactoe_board"]),
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "answer_hint": str(prompt_defaults[f"answer_hint_{str(sample.query_id)}"]),
        "annotation_hint": str(prompt_defaults[f"annotation_hint_{str(sample.query_id)}"]),
        "json_example": str(json_example),
        "json_example_answer_only": str(json_example_answer_only),
        "status_rule_text": str(prompt_defaults["ultimate_tictactoe_status_rule_text"]),
        "tactic_rule_text": str(prompt_defaults["ultimate_tictactoe_tactic_rule_text"]),
        "macro_threat_rule_text": str(prompt_defaults["ultimate_tictactoe_macro_threat_rule_text"]),
    }
    prompt_selection = render_scene_prompt_variants(
        domain="games",
        scene_id=SCENE_ID,
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(prompt_defaults["task_key"]),
        query_key=str(sample.query_id),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        dynamic_slots=dynamic_slots,
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
    return str(prompt_artifacts.prompt), dict(prompt_artifacts.prompt_variants), {
        "bundle_id": str(prompt_defaults["bundle_id"]),
        "prompt_variant": dict(prompt_artifacts.prompt_variant),
        "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
        "prompt_variants_for_trace": dict(prompt_artifacts.prompt_variants_for_trace),
    }




class _UltimateTicTacToeTask:
    """Shared generator for public Ultimate Tic-Tac-Toe tasks."""

    domain = "games"
    scene_id = SCENE_ID
    default_dataset_enabled = True
    supported_queries: Tuple[str, ...]
    query_weights_key: str

    def _sample(self, rng, *, task_id: str, instance_seed: int, params: Mapping[str, Any], query_id: str) -> _Sample:
        if str(query_id) in STATUS_QUERIES:
            return _sample_status_count(
                rng,
                task_id=str(task_id),
                instance_seed=int(instance_seed),
                params=params,
                query_id=str(query_id),
            )
        if str(query_id) in MACRO_THREAT_QUERIES:
            return _sample_macro_threat_count(
                rng,
                task_id=str(task_id),
                instance_seed=int(instance_seed),
                params=params,
                query_id=str(query_id),
            )
        return _sample_local_tactic(
            rng,
            task_id=str(task_id),
            instance_seed=int(instance_seed),
            params=params,
            query_id=str(query_id),
        )

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        style_variant, style_variant_probabilities = _sample_named_axis(
            task_id=str(self.task_id),
            instance_seed=int(instance_seed),
            params=params,
            namespace="style_variant",
            explicit_key="style_variant",
            weights_key="style_variant_weights",
            balance_flag_key="balanced_style_variant_sampling",
            supported=SUPPORTED_STYLE_VARIANTS,
        )
        query_id, query_probabilities = _sample_named_axis(
            task_id=str(self.task_id),
            instance_seed=int(instance_seed),
            params=params,
            namespace="query_id",
            explicit_key="query_id",
            weights_key=str(self.query_weights_key),
            balance_flag_key="balanced_query_id_sampling",
            supported=tuple(self.supported_queries),
        )
        sample: _Sample | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"{str(self.task_id)}.attempt.{int(attempt_index)}")
            try:
                sample = self._sample(
                    rng,
                    task_id=str(self.task_id),
                    instance_seed=int(instance_seed),
                    params=params,
                    query_id=str(query_id),
                )
                break
            except ValueError:
                continue
        if sample is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid Ultimate Tic-Tac-Toe scene after {max_attempts} attempts")

        rendered = _render_scene(
            sample=sample,
            task_id=str(self.task_id),
            style_variant=str(style_variant),
            instance_seed=int(instance_seed),
            params=params,
        )
        annotation_bboxes = [
            list(rendered.render_map["entity_bboxes_px"][str(entity_id)])
            for entity_id in sample.annotation_entity_ids
            if str(entity_id) in rendered.render_map["entity_bboxes_px"]
        ]
        if len(annotation_bboxes) != len(sample.annotation_entity_ids):
            raise RuntimeError("missing rendered annotation bbox")
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        prompt, prompt_variants, prompt_meta = _build_prompt(sample, instance_seed=int(instance_seed))
        answer_gt = TypedValue(type=str(sample.answer_type), value=sample.answer)
        annotation_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in annotation_bboxes])

        board_trace = []
        for index, local in enumerate(sample.board):
            board_trace.append(
                {
                    "label": MACRO_LABELS[int(index)],
                    "status": str(local.status),
                    "cells": [str(value) for value in local.cells],
                    "winning_line": None if local.winning_line is None else [int(cell) + 1 for cell in local.winning_line],
                }
            )
        trace_payload = {
            "scene_ir": {
                "scene_kind": "games_ultimate_tictactoe_board",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "query_id": str(sample.query_id),
                    "style_variant": str(style_variant),
                    "annotation_entity_ids": [str(entity_id) for entity_id in sample.annotation_entity_ids],
                },
            },
            "query_spec": {
                "query_id": str(sample.query_id),
                "template_id": str(prompt_meta["bundle_id"]),
                "prompt_variant": dict(prompt_meta["prompt_variant"]),
                "prompt_variant_active_key": str(prompt_meta["prompt_variant_active_key"]),
                "prompt_variants": dict(prompt_meta["prompt_variants_for_trace"]),
                "params": {
                    "query_id": str(sample.query_id),
                    "style_variant": str(style_variant),
                    "query_id_probabilities": dict(query_probabilities),
                    "style_variant_probabilities": dict(style_variant_probabilities),
                    **dict(sample.metadata),
                },
            },
            "render_spec": {
                "style_variant": str(style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "layout_jitter": dict(rendered.render_map.get("layout_jitter", {})),
                "panel_scene_style": dict(rendered.style_meta.get("panel_scene_style", {})),
                "ultimate_tictactoe_board_style": dict(rendered.style_meta.get("ultimate_tictactoe_board_style", {})),
                "text_style": dict(rendered.style_meta.get("text_style", {})),
                "effective_local_cell_size_px": rendered.render_map.get("effective_local_cell_size_px"),
            },
            "render_map": dict(rendered.render_map),
            "execution_trace": {
                "query_id": str(sample.query_id),
                "style_variant": str(style_variant),
                "small_boards": board_trace,
                "target_answer": sample.target_answer,
                "highlighted_small_board": None
                if sample.highlighted_board_index is None
                else MACRO_LABELS[int(sample.highlighted_board_index)],
                "option_cells": [int(cell) + 1 for cell in sample.option_cells],
                "answer_cell": None if sample.answer_cell is None else int(sample.answer_cell) + 1,
                "support_cells": [int(cell) + 1 for cell in sample.support_cells],
                "answer": sample.answer,
                "annotation_entity_ids": [str(entity_id) for entity_id in sample.annotation_entity_ids],
                "matching_small_boards": list(sample.metadata.get("matching_small_boards", [])),
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(entity_id) for entity_id in sample.annotation_entity_ids],
            },
            "projected_annotation": {
                "type": "bbox_set",
                "bbox_set": [list(bbox) for bbox in annotation_bboxes],
                "pixel_bbox_set": [list(bbox) for bbox in annotation_bboxes],
            },
            "background": dict(rendered.background_meta),
            "post_image_noise": dict(post_noise_meta),
        }
        return TaskOutput(
            prompt=str(prompt),
            prompt_variants=dict(prompt_variants),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(sample.query_id),
        )


@register_task
class GamesUltimateTicTacToeSmallBoardStatusCountTask(_UltimateTicTacToeTask):
    """Count local-board status categories on an Ultimate Tic-Tac-Toe board."""

    task_id = "task_games__ultimate_tictactoe__small_board_status_count"
    supported_queries = STATUS_QUERIES
    query_weights_key = "status_count_query_id_weights"


class GamesUltimateTicTacToeLineCompletionMoveLabelTask(_UltimateTicTacToeTask):
    """Choose the local winning or blocking line-completion move."""

    task_id = "task_games__ultimate_tictactoe__line_completion_move_label"
    supported_queries = TACTIC_QUERIES
    query_weights_key = "local_tactic_query_id_weights"


class GamesUltimateTicTacToeMacroThreatBoardCountTask(_UltimateTicTacToeTask):
    """Count local boards where one player has an immediate winning move."""

    task_id = "task_games__ultimate_tictactoe__macro_threat_board_count"
    supported_queries = MACRO_THREAT_QUERIES
    query_weights_key = "macro_threat_query_id_weights"
