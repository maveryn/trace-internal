"""Games match-3 one-swap tasks."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.task_group_config import resolve_task_group_section_defaults
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
from ...shared.support_sampling import resolve_integer_choice
from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from ..shared.complexity import build_games_complexity, normalize_linear, resolve_games_complexity_weights
from ..shared.layout import (
    apply_games_layout_jitter_to_bbox,
    attach_games_unit_size_jitter,
    resolve_games_layout_jitter,
    resolve_games_unit_size_scale,
    scale_games_px,
)
from ..shared.sampling import resolve_games_named_axis
from ..shared.scene_style import draw_panel_grid_cell, draw_panel_scene_chrome, make_panel_scene_background, resolve_game_panel_scene_style
from ..shared.visual_defaults import load_games_noise_defaults


TASK_GROUP = "match3"
SCENE_ID = "match3"
QUERY_CLEARED_COUNT = "cleared_count_after_marked_swap"
QUERY_CREATED_RUN_COUNT = "created_run_count_after_marked_swap"
QUERY_MAX_CLEAR_LABEL = "max_clear_swap_label"
QUERY_TARGET_CLEAR_LABEL = "target_clear_swap_label"
SUPPORTED_EFFECT_VALUE_QUERIES: Tuple[str, ...] = (QUERY_CLEARED_COUNT, QUERY_CREATED_RUN_COUNT)
SUPPORTED_BEST_SWAP_QUERIES: Tuple[str, ...] = (QUERY_MAX_CLEAR_LABEL, QUERY_TARGET_CLEAR_LABEL)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("square_board", "wide_board", "tall_board")
SUPPORTED_STYLE_VARIANTS: Tuple[str, ...] = ("panel_scene",)
OPTION_LABELS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F", "G", "H")
GEM_KEYS: Tuple[str, ...] = ("red", "blue", "green", "yellow", "purple", "cyan")
GEM_RGB: Dict[str, Tuple[int, int, int]] = {
    "red": (222, 65, 73),
    "blue": (55, 121, 219),
    "green": (45, 166, 105),
    "yellow": (238, 190, 52),
    "purple": (146, 93, 208),
    "cyan": (38, 169, 204),
}

Coord = Tuple[int, int]
Board = Tuple[Tuple[str, ...], ...]


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for match-3 tasks."""

    row_count_support: Tuple[int, ...] = (5, 6, 7)
    col_count_support: Tuple[int, ...] = (5, 6, 7)
    gem_type_count_support: Tuple[int, ...] = (5, 6)
    option_count_support: Tuple[int, ...] = (5, 6, 7, 8)
    target_clear_count_support: Tuple[int, ...] = (0, 3, 4, 5, 6)
    target_run_count_support: Tuple[int, ...] = (0, 1, 2)
    canvas_width: int = 760
    canvas_height: int = 720
    panel_margin_px: int = 42
    board_inner_margin_px: int = 38
    index_margin_px: int = 34
    cell_size_px: int = 78
    cell_gap_px: int = 8
    gem_inset_px: int = 10
    label_font_size_px: int = 21
    index_font_size_px: int = 18
    arrow_width_px: int = 7


@dataclass(frozen=True)
class _Move:
    """One adjacent jewel swap."""

    a: Coord
    b: Coord

    @property
    def key(self) -> Tuple[Coord, Coord]:
        return (tuple(self.a), tuple(self.b)) if tuple(self.a) <= tuple(self.b) else (tuple(self.b), tuple(self.a))


@dataclass(frozen=True)
class _MoveOutcome:
    """Immediate post-swap clear outcome."""

    move: _Move
    clear_count: int
    run_count: int
    cleared_cells: Tuple[Coord, ...]
    runs: Tuple[Tuple[Coord, ...], ...]


@dataclass(frozen=True)
class _SwapOption:
    """One labeled swap option drawn on the board."""

    label: str
    outcome: _MoveOutcome
    is_answer: bool

    @property
    def entity_id(self) -> str:
        return f"swap_option_{str(self.label).lower()}"


@dataclass(frozen=True)
class _Sample:
    """Constructed match-3 board and query witness."""

    query_id: str
    scene_variant: str
    board: Board
    answer: int | str
    answer_type: str
    option_specs: Tuple[_SwapOption, ...]
    marked_outcome: _MoveOutcome | None
    target_clear_count: int | None
    target_run_count: int | None
    evidence_entity_ids: Tuple[str, ...]
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class _RenderedScene:
    """Rendered match-3 scene and trace maps."""

    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]
    style_meta: Dict[str, Any]
    background_meta: Dict[str, Any]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", TASK_GROUP)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id="games_match3_base",
)
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group=TASK_GROUP, apply_prob=0.5)


def _task_effective_params(task_id: str, params: Mapping[str, Any]) -> Dict[str, Any]:
    """Overlay task-specific config defaults into params for shared helpers."""

    effective: Dict[str, Any] = {}
    for section in ("generation", "rendering"):
        section_defaults = resolve_task_group_section_defaults(
            _TASK_GROUP_DEFAULTS,
            str(section),
            task_id=str(task_id),
        )
        effective.update(dict(section_defaults))
    effective.update(dict(params))
    return effective


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


def _sample_scene_variant(*, task_id: str, instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    return _sample_named_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_SCENE_VARIANTS,
    )


def _sample_style_variant(*, task_id: str, instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    return _sample_named_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_STYLE_VARIANTS,
    )


def _sample_query_variant(
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    supported: Sequence[str],
    weights_key: str,
) -> Tuple[str, Dict[str, float]]:
    return _sample_named_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        namespace="query_variant",
        explicit_key="query_variant",
        weights_key=str(weights_key),
        balance_flag_key="balanced_query_variant_sampling",
        supported=tuple(str(item) for item in supported),
    )


def _sample_dimensions(
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    scene_variant: str,
) -> Tuple[int, int, Dict[str, float], Dict[str, float]]:
    rows, row_probabilities = _sample_integer_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        support_key="row_count_support",
        explicit_key="row_count",
        fallback_support=_DEFAULTS.row_count_support,
        namespace="row_count",
        balanced_flag_key="balanced_row_count_sampling",
    )
    cols, col_probabilities = _sample_integer_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        support_key="col_count_support",
        explicit_key="col_count",
        fallback_support=_DEFAULTS.col_count_support,
        namespace="col_count",
        balanced_flag_key="balanced_col_count_sampling",
    )
    if str(scene_variant) == "wide_board":
        cols = max(int(cols), int(rows))
    elif str(scene_variant) == "tall_board":
        rows = max(int(rows), int(cols))
    else:
        cols = rows
    return int(rows), int(cols), dict(row_probabilities), dict(col_probabilities)


def _sample_gem_keys(rng, *, gem_type_count: int) -> Tuple[str, ...]:
    values = list(GEM_KEYS)
    rng.shuffle(values)
    return tuple(values[: int(gem_type_count)])


def _would_make_run(board_rows: Sequence[Sequence[str]], row: int, col: int, color: str) -> bool:
    if int(col) >= 2 and str(board_rows[row][col - 1]) == str(color) and str(board_rows[row][col - 2]) == str(color):
        return True
    if int(row) >= 2 and str(board_rows[row - 1][col]) == str(color) and str(board_rows[row - 2][col]) == str(color):
        return True
    return False


def _generate_board(rng, *, rows: int, cols: int, gem_keys: Sequence[str]) -> Board:
    board: List[List[str]] = []
    keys = [str(key) for key in gem_keys]
    for row in range(int(rows)):
        values: List[str] = []
        board.append(values)
        for col in range(int(cols)):
            choices = list(keys)
            rng.shuffle(choices)
            selected = None
            for choice in choices:
                if not _would_make_run(board, int(row), int(col), str(choice)):
                    selected = str(choice)
                    break
            values.append(str(selected if selected is not None else choices[0]))
    return tuple(tuple(str(value) for value in row) for row in board)


def _find_runs(board: Board) -> Tuple[Tuple[Coord, ...], ...]:
    rows = len(board)
    cols = len(board[0]) if rows else 0
    runs: List[Tuple[Coord, ...]] = []
    for row in range(rows):
        col = 0
        while col < cols:
            end = col + 1
            while end < cols and str(board[row][end]) == str(board[row][col]):
                end += 1
            if int(end - col) >= 3:
                runs.append(tuple((int(row), int(c)) for c in range(col, end)))
            col = end
    for col in range(cols):
        row = 0
        while row < rows:
            end = row + 1
            while end < rows and str(board[end][col]) == str(board[row][col]):
                end += 1
            if int(end - row) >= 3:
                runs.append(tuple((int(r), int(col)) for r in range(row, end)))
            row = end
    return tuple(runs)


def _swap_board(board: Board, move: _Move) -> Board:
    rows = [list(row) for row in board]
    ar, ac = move.a
    br, bc = move.b
    rows[ar][ac], rows[br][bc] = rows[br][bc], rows[ar][ac]
    return tuple(tuple(str(value) for value in row) for row in rows)


def _simulate_move(board: Board, move: _Move) -> _MoveOutcome:
    after = _swap_board(board, move)
    runs = _find_runs(after)
    cleared = sorted({coord for run in runs for coord in run})
    return _MoveOutcome(
        move=move,
        clear_count=int(len(cleared)),
        run_count=int(len(runs)),
        cleared_cells=tuple((int(row), int(col)) for row, col in cleared),
        runs=tuple(tuple((int(row), int(col)) for row, col in run) for run in runs),
    )


def _all_move_outcomes(board: Board) -> Tuple[_MoveOutcome, ...]:
    rows = len(board)
    cols = len(board[0]) if rows else 0
    outcomes: List[_MoveOutcome] = []
    for row in range(rows):
        for col in range(cols):
            for dr, dc in ((0, 1), (1, 0)):
                other = (int(row + dr), int(col + dc))
                if other[0] >= rows or other[1] >= cols:
                    continue
                if str(board[row][col]) == str(board[other[0]][other[1]]):
                    continue
                outcomes.append(_simulate_move(board, _Move(a=(int(row), int(col)), b=other)))
    return tuple(outcomes)


def _cell_entity_id(coord: Coord) -> str:
    return f"gem_r{int(coord[0]) + 1}_c{int(coord[1]) + 1}"


def _move_neighbor_ids(outcome: _MoveOutcome) -> Tuple[str, ...]:
    return (_cell_entity_id(outcome.move.a), _cell_entity_id(outcome.move.b))


def _evidence_for_outcome(*, arrow_entity_id: str, outcome: _MoveOutcome) -> Tuple[str, ...]:
    if outcome.cleared_cells:
        return tuple([str(arrow_entity_id)] + [_cell_entity_id(coord) for coord in outcome.cleared_cells])
    return tuple([str(arrow_entity_id)] + list(_move_neighbor_ids(outcome)))


def _resolve_target_answer(
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    query_id: str,
) -> Tuple[int, Dict[str, float]]:
    if str(query_id) in {QUERY_CLEARED_COUNT, QUERY_MAX_CLEAR_LABEL, QUERY_TARGET_CLEAR_LABEL}:
        return _sample_integer_axis(
            task_id=str(task_id),
            instance_seed=int(instance_seed),
            params=params,
            support_key="target_clear_count_support",
            explicit_key="target_answer",
            fallback_support=_DEFAULTS.target_clear_count_support,
            namespace=f"{str(query_id)}.target_clear_count",
            balanced_flag_key="balanced_target_answer_sampling",
        )
    return _sample_integer_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        support_key="target_run_count_support",
        explicit_key="target_answer",
        fallback_support=_DEFAULTS.target_run_count_support,
        namespace=f"{str(query_id)}.target_run_count",
        balanced_flag_key="balanced_target_answer_sampling",
    )


def _select_random(outcomes: Sequence[_MoveOutcome], rng, *, count: int) -> Tuple[_MoveOutcome, ...]:
    values = list(outcomes)
    rng.shuffle(values)
    return tuple(values[: int(count)])


def _make_base_board(
    rng,
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    scene_variant: str,
) -> Tuple[Board, Tuple[str, ...], int, int, Dict[str, Any]]:
    rows, cols, row_probs, col_probs = _sample_dimensions(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        scene_variant=str(scene_variant),
    )
    gem_count, gem_count_probs = _sample_integer_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        support_key="gem_type_count_support",
        explicit_key="gem_type_count",
        fallback_support=_DEFAULTS.gem_type_count_support,
        namespace="gem_type_count",
        balanced_flag_key="balanced_gem_type_count_sampling",
    )
    gem_keys = _sample_gem_keys(rng, gem_type_count=int(gem_count))
    board = _generate_board(rng, rows=int(rows), cols=int(cols), gem_keys=gem_keys)
    if _find_runs(board):
        raise ValueError("generated board contains a pre-existing run")
    metadata = {
        "rows": int(rows),
        "cols": int(cols),
        "gem_type_count": int(gem_count),
        "gem_keys": [str(key) for key in gem_keys],
        "row_count_probabilities": dict(row_probs),
        "col_count_probabilities": dict(col_probs),
        "gem_type_count_probabilities": dict(gem_count_probs),
    }
    return board, gem_keys, int(rows), int(cols), dict(metadata)


def _sample_effect_value(
    rng,
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    scene_variant: str,
    query_id: str,
) -> _Sample:
    target_answer, target_probs = _resolve_target_answer(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        query_id=str(query_id),
    )
    board, _gem_keys, _rows, _cols, metadata = _make_base_board(
        rng,
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        scene_variant=str(scene_variant),
    )
    outcomes = _all_move_outcomes(board)
    if str(query_id) == QUERY_CLEARED_COUNT:
        candidates = [outcome for outcome in outcomes if int(outcome.clear_count) == int(target_answer)]
        answer = int(target_answer)
        target_clear = int(target_answer)
        target_run = None
    else:
        candidates = [outcome for outcome in outcomes if int(outcome.run_count) == int(target_answer)]
        answer = int(target_answer)
        target_clear = None
        target_run = int(target_answer)
    if not candidates:
        raise ValueError(f"no marked swap candidate for {query_id}={target_answer}")
    marked = rng.choice(tuple(candidates))
    evidence_ids = _evidence_for_outcome(arrow_entity_id="marked_swap_arrow", outcome=marked)
    metadata.update(
        {
            "target_answer": int(target_answer),
            "target_answer_probabilities": dict(target_probs),
            "move_count": int(len(outcomes)),
            "clear_count_histogram": _histogram(int(outcome.clear_count) for outcome in outcomes),
            "run_count_histogram": _histogram(int(outcome.run_count) for outcome in outcomes),
        }
    )
    return _Sample(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        board=board,
        answer=int(answer),
        answer_type="integer",
        option_specs=(),
        marked_outcome=marked,
        target_clear_count=target_clear,
        target_run_count=target_run,
        evidence_entity_ids=tuple(evidence_ids),
        metadata=dict(metadata),
    )


def _histogram(values: Sequence[int] | Any) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for value in values:
        key = str(int(value))
        out[key] = int(out.get(key, 0) + 1)
    return dict(sorted(out.items(), key=lambda item: int(item[0])))


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


def _sample_best_swap_label(
    rng,
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    scene_variant: str,
    query_id: str,
) -> _Sample:
    option_count, option_probs = _sample_integer_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        support_key="option_count_support",
        explicit_key="option_count",
        fallback_support=_DEFAULTS.option_count_support,
        namespace="option_count",
        balanced_flag_key="balanced_option_count_sampling",
    )
    answer_slot = _sample_answer_slot(int(option_count), instance_seed=int(instance_seed), task_id=str(task_id), params=params)
    board, _gem_keys, _rows, _cols, metadata = _make_base_board(
        rng,
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        scene_variant=str(scene_variant),
    )
    outcomes = tuple(_all_move_outcomes(board))
    if len(outcomes) < int(option_count):
        raise ValueError("not enough legal swaps")

    target_clear_count = None
    if str(query_id) == QUERY_MAX_CLEAR_LABEL:
        positive = [outcome for outcome in outcomes if int(outcome.clear_count) > 0]
        rng.shuffle(positive)
        answer_outcome = None
        distractors: List[_MoveOutcome] = []
        for candidate in sorted(positive, key=lambda item: int(item.clear_count), reverse=True):
            lower = [outcome for outcome in outcomes if outcome.move.key != candidate.move.key and int(outcome.clear_count) < int(candidate.clear_count)]
            if len(lower) >= int(option_count) - 1:
                answer_outcome = candidate
                distractors = list(_select_random(lower, rng, count=int(option_count) - 1))
                break
        if answer_outcome is None:
            raise ValueError("no unique max-clear option set")
    else:
        target_clear_count, target_probs = _resolve_target_answer(
            task_id=str(task_id),
            instance_seed=int(instance_seed),
            params=params,
            query_id=str(query_id),
        )
        matching = [outcome for outcome in outcomes if int(outcome.clear_count) == int(target_clear_count)]
        nonmatching = [outcome for outcome in outcomes if int(outcome.clear_count) != int(target_clear_count)]
        if not matching or len(nonmatching) < int(option_count) - 1:
            raise ValueError(f"no unique target-clear option set for {target_clear_count}")
        answer_outcome = rng.choice(tuple(matching))
        nonmatching = [outcome for outcome in nonmatching if outcome.move.key != answer_outcome.move.key]
        distractors = list(_select_random(nonmatching, rng, count=int(option_count) - 1))
        metadata["target_answer"] = int(target_clear_count)
        metadata["target_answer_probabilities"] = dict(target_probs)

    option_outcomes = list(distractors)
    option_outcomes.insert(int(answer_slot), answer_outcome)
    labels = OPTION_LABELS[: int(option_count)]
    option_specs = tuple(
        _SwapOption(label=str(label), outcome=outcome, is_answer=(int(index) == int(answer_slot)))
        for index, (label, outcome) in enumerate(zip(labels, option_outcomes))
    )
    answer_label = str(option_specs[int(answer_slot)].label)
    evidence_ids = _evidence_for_outcome(arrow_entity_id=option_specs[int(answer_slot)].entity_id, outcome=answer_outcome)
    metadata.update(
        {
            "option_count": int(option_count),
            "option_count_probabilities": dict(option_probs),
            "answer_option_index": int(answer_slot),
            "answer_label": str(answer_label),
            "move_count": int(len(outcomes)),
            "clear_count_histogram": _histogram(int(outcome.clear_count) for outcome in outcomes),
            "run_count_histogram": _histogram(int(outcome.run_count) for outcome in outcomes),
        }
    )
    return _Sample(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        board=board,
        answer=str(answer_label),
        answer_type="string",
        option_specs=tuple(option_specs),
        marked_outcome=None,
        target_clear_count=None if target_clear_count is None else int(target_clear_count),
        target_run_count=None,
        evidence_entity_ids=tuple(evidence_ids),
        metadata=dict(metadata),
    )


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    bbox: Tuple[float, float, float, float],
    text: str,
    *,
    font,
    fill: Tuple[int, int, int],
    stroke_width: int = 1,
) -> None:
    text_bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=int(stroke_width))
    text_w = float(text_bbox[2] - text_bbox[0])
    text_h = float(text_bbox[3] - text_bbox[1])
    x0, y0, x1, y1 = bbox
    draw.text(
        (float(x0 + ((x1 - x0) - text_w) / 2.0), float(y0 + ((y1 - y0) - text_h) / 2.0)),
        str(text),
        font=font,
        fill=tuple(fill),
        stroke_width=int(stroke_width),
        stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(fill)),
    )


def _gem_polygon(cx: float, cy: float, radius: float) -> Tuple[Tuple[float, float], ...]:
    return (
        (float(cx), float(cy - radius)),
        (float(cx + radius * 0.90), float(cy - radius * 0.08)),
        (float(cx + radius * 0.42), float(cy + radius * 0.86)),
        (float(cx - radius * 0.42), float(cy + radius * 0.86)),
        (float(cx - radius * 0.90), float(cy - radius * 0.08)),
    )


def _draw_gem(
    draw: ImageDraw.ImageDraw,
    bbox: Tuple[float, float, float, float],
    *,
    fill_rgb: Tuple[int, int, int],
    outline_rgb: Tuple[int, int, int],
) -> None:
    x0, y0, x1, y1 = bbox
    cx = float((x0 + x1) / 2.0)
    cy = float((y0 + y1) / 2.0)
    radius = float(min(x1 - x0, y1 - y0) / 2.0)
    polygon = _gem_polygon(cx, cy, radius)
    draw.polygon(polygon, fill=tuple(fill_rgb), outline=tuple(outline_rgb))
    inner = _gem_polygon(cx, cy - radius * 0.08, radius * 0.50)
    highlight = tuple(min(255, int(value + 42)) for value in fill_rgb)
    draw.polygon(inner, fill=highlight)
    shadow = tuple(max(0, int(value * 0.70)) for value in fill_rgb)
    draw.line([polygon[2], polygon[3], polygon[4]], fill=shadow, width=2)


def _draw_arrow(
    draw: ImageDraw.ImageDraw,
    start: Tuple[float, float],
    end: Tuple[float, float],
    *,
    line_rgb: Tuple[int, int, int],
    label: str | None,
    label_font,
    text_rgb: Tuple[int, int, int],
    label_fill_rgb: Tuple[int, int, int],
    label_outline_rgb: Tuple[int, int, int],
    width: int,
) -> List[float]:
    sx, sy = float(start[0]), float(start[1])
    ex, ey = float(end[0]), float(end[1])
    dx = float(ex - sx)
    dy = float(ey - sy)
    length = max(1.0, math.hypot(dx, dy))
    ux = dx / length
    uy = dy / length
    start_trim = 0.18 * length
    end_trim = 0.18 * length
    x0 = sx + ux * start_trim
    y0 = sy + uy * start_trim
    x1 = ex - ux * end_trim
    y1 = ey - uy * end_trim
    stroke = tuple(int(value) for value in resolve_text_stroke_fill(line_rgb))
    draw.line((x0, y0, x1, y1), fill=stroke, width=int(width + 4))
    draw.line((x0, y0, x1, y1), fill=tuple(line_rgb), width=int(width))
    head_len = max(12.0, float(width) * 2.4)
    head_w = max(10.0, float(width) * 2.0)
    px, py = -uy, ux
    head = (
        (x1, y1),
        (x1 - ux * head_len + px * head_w / 2.0, y1 - uy * head_len + py * head_w / 2.0),
        (x1 - ux * head_len - px * head_w / 2.0, y1 - uy * head_len - py * head_w / 2.0),
    )
    draw.polygon(head, fill=tuple(line_rgb), outline=stroke)
    bbox = [
        min(x0, x1) - float(width + head_w),
        min(y0, y1) - float(width + head_w),
        max(x0, x1) + float(width + head_w),
        max(y0, y1) + float(width + head_w),
    ]
    if label is not None:
        mid_x = float((sx + ex) / 2.0)
        mid_y = float((sy + ey) / 2.0)
        radius = max(14.0, float(width) * 2.5)
        label_bbox = (mid_x - radius, mid_y - radius, mid_x + radius, mid_y + radius)
        draw.ellipse(label_bbox, fill=tuple(label_fill_rgb), outline=tuple(label_outline_rgb), width=2)
        _draw_centered_text(draw, label_bbox, str(label), font=label_font, fill=text_rgb, stroke_width=0)
        bbox = [
            min(bbox[0], label_bbox[0]),
            min(bbox[1], label_bbox[1]),
            max(bbox[2], label_bbox[2]),
            max(bbox[3], label_bbox[3]),
        ]
    return [round(float(value), 3) for value in bbox]


def _render_scene(
    *,
    sample: _Sample,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
) -> _RenderedScene:
    canvas_width = _int_default(params, "canvas_width", _DEFAULTS.canvas_width)
    canvas_height = _int_default(params, "canvas_height", _DEFAULTS.canvas_height)
    style, style_meta = resolve_game_panel_scene_style(
        instance_seed=int(instance_seed),
        namespace=f"{str(task_id)}.match3_panel_style",
        treatment_weights=group_default(_GEN_DEFAULTS, "panel_treatment_weights", {}),
        palette_weights=group_default(_GEN_DEFAULTS, "panel_palette_weights", {}),
    )
    image, background_meta = make_panel_scene_background(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        style=style,
    )
    image = image.convert("RGBA")
    draw = ImageDraw.Draw(image)
    layout_jitter = resolve_games_layout_jitter(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace=f"{str(task_id)}.match3.layout",
    )
    unit_scale, unit_meta = resolve_games_unit_size_scale(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace=f"{str(task_id)}.match3.unit_size",
    )

    rows = len(sample.board)
    cols = len(sample.board[0]) if rows else 0
    cell = scale_games_px(_int_default(params, "cell_size_px", _DEFAULTS.cell_size_px), float(unit_scale), min_px=28)
    gap = scale_games_px(_int_default(params, "cell_gap_px", _DEFAULTS.cell_gap_px), float(unit_scale), min_px=2)
    gem_inset = scale_games_px(_int_default(params, "gem_inset_px", _DEFAULTS.gem_inset_px), float(unit_scale), min_px=4)
    index_margin = scale_games_px(_int_default(params, "index_margin_px", _DEFAULTS.index_margin_px), float(unit_scale), min_px=20)
    inner_margin = scale_games_px(_int_default(params, "board_inner_margin_px", _DEFAULTS.board_inner_margin_px), float(unit_scale), min_px=20)
    grid_width = int(cols * cell + max(0, cols - 1) * gap)
    grid_height = int(rows * cell + max(0, rows - 1) * gap)
    panel_width = int(grid_width + index_margin + inner_margin * 2)
    panel_height = int(grid_height + index_margin + inner_margin * 2)
    panel_width = min(int(panel_width), int(canvas_width - 2 * _int_default(params, "panel_margin_px", _DEFAULTS.panel_margin_px)))
    panel_height = min(int(panel_height), int(canvas_height - 2 * _int_default(params, "panel_margin_px", _DEFAULTS.panel_margin_px)))
    base_panel = (
        float((canvas_width - panel_width) / 2.0),
        float((canvas_height - panel_height) / 2.0),
        float((canvas_width + panel_width) / 2.0),
        float((canvas_height + panel_height) / 2.0),
    )
    panel_bbox, _dx, _dy, resolved_jitter = apply_games_layout_jitter_to_bbox(
        bbox_px=base_panel,
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        jitter=layout_jitter,
    )
    panel_bbox_i = tuple(int(round(value)) for value in panel_bbox)
    draw_panel_scene_chrome(draw, bbox=panel_bbox_i, style=style, radius=18, border_width=3)
    grid_left = int(round(panel_bbox[0])) + inner_margin + index_margin
    grid_top = int(round(panel_bbox[1])) + inner_margin + index_margin

    label_font = load_font(_int_default(params, "label_font_size_px", _DEFAULTS.label_font_size_px), bold=True)
    index_font = load_font(_int_default(params, "index_font_size_px", _DEFAULTS.index_font_size_px), bold=True)
    text_rgb = tuple(int(value) for value in style.text_rgb)
    border_rgb = tuple(int(value) for value in style.panel_border_rgb)
    cell_fill = tuple(int(round((int(style.panel_fill_rgb[i]) * 0.78) + (int(style.background_rgb[i]) * 0.22))) for i in range(3))
    mark_rgb = tuple(int(value) for value in style.mark_rgb)

    entities: List[Dict[str, Any]] = []
    entity_bboxes: Dict[str, List[float]] = {}
    gem_specs: List[Dict[str, Any]] = []
    cell_centers: Dict[Coord, Tuple[float, float]] = {}
    for col in range(cols):
        x0 = grid_left + col * (cell + gap)
        bbox = (x0, grid_top - index_margin + 2, x0 + cell, grid_top - 6)
        _draw_centered_text(draw, bbox, str(col + 1), font=index_font, fill=text_rgb, stroke_width=1)
    for row in range(rows):
        y0 = grid_top + row * (cell + gap)
        bbox = (grid_left - index_margin + 2, y0, grid_left - 6, y0 + cell)
        _draw_centered_text(draw, bbox, str(row + 1), font=index_font, fill=text_rgb, stroke_width=1)
    for row in range(rows):
        for col in range(cols):
            x0 = grid_left + col * (cell + gap)
            y0 = grid_top + row * (cell + gap)
            cell_bbox = (int(x0), int(y0), int(x0 + cell), int(y0 + cell))
            draw_panel_grid_cell(draw, bbox=cell_bbox, fill=cell_fill, style=style, outline=style.grid_rgb, width=1)
            gem_bbox = (
                float(x0 + gem_inset),
                float(y0 + gem_inset),
                float(x0 + cell - gem_inset),
                float(y0 + cell - gem_inset),
            )
            color_key = str(sample.board[row][col])
            _draw_gem(draw, gem_bbox, fill_rgb=GEM_RGB[str(color_key)], outline_rgb=border_rgb)
            entity_id = _cell_entity_id((int(row), int(col)))
            bbox_list = [round(float(value), 3) for value in gem_bbox]
            entity_bboxes[entity_id] = list(bbox_list)
            cell_centers[(int(row), int(col))] = (float(x0 + cell / 2.0), float(y0 + cell / 2.0))
            spec = {
                "entity_id": str(entity_id),
                "entity_type": "match3_gem",
                "row": int(row + 1),
                "col": int(col + 1),
                "color_key": str(color_key),
                "bbox_px": list(bbox_list),
            }
            gem_specs.append(dict(spec))
            entities.append(dict(spec))

    option_specs: List[Dict[str, Any]] = []
    arrow_width = scale_games_px(_int_default(params, "arrow_width_px", _DEFAULTS.arrow_width_px), float(unit_scale), min_px=4)
    for option in sample.option_specs:
        start = cell_centers[tuple(option.outcome.move.a)]
        end = cell_centers[tuple(option.outcome.move.b)]
        bbox = _draw_arrow(
            draw,
            start,
            end,
            line_rgb=mark_rgb,
            label=str(option.label),
            label_font=label_font,
            text_rgb=text_rgb,
            label_fill_rgb=tuple(style.option_marker_fill_rgb),
            label_outline_rgb=mark_rgb,
            width=int(arrow_width),
        )
        entity_bboxes[str(option.entity_id)] = [float(value) for value in bbox]
        spec = {
            "entity_id": str(option.entity_id),
            "entity_type": "match3_swap_option_arrow",
            "label": str(option.label),
            "from_cell": [int(option.outcome.move.a[0] + 1), int(option.outcome.move.a[1] + 1)],
            "to_cell": [int(option.outcome.move.b[0] + 1), int(option.outcome.move.b[1] + 1)],
            "clear_count": int(option.outcome.clear_count),
            "run_count": int(option.outcome.run_count),
            "cleared_cells": [[int(row + 1), int(col + 1)] for row, col in option.outcome.cleared_cells],
            "is_answer": bool(option.is_answer),
            "bbox_px": [float(value) for value in bbox],
        }
        option_specs.append(dict(spec))
        entities.append(dict(spec))

    marked_spec = None
    if sample.marked_outcome is not None:
        start = cell_centers[tuple(sample.marked_outcome.move.a)]
        end = cell_centers[tuple(sample.marked_outcome.move.b)]
        bbox = _draw_arrow(
            draw,
            start,
            end,
            line_rgb=mark_rgb,
            label=None,
            label_font=label_font,
            text_rgb=text_rgb,
            label_fill_rgb=tuple(style.option_marker_fill_rgb),
            label_outline_rgb=mark_rgb,
            width=int(arrow_width + 2),
        )
        entity_bboxes["marked_swap_arrow"] = [float(value) for value in bbox]
        marked_spec = {
            "entity_id": "marked_swap_arrow",
            "entity_type": "marked_match3_swap_arrow",
            "from_cell": [int(sample.marked_outcome.move.a[0] + 1), int(sample.marked_outcome.move.a[1] + 1)],
            "to_cell": [int(sample.marked_outcome.move.b[0] + 1), int(sample.marked_outcome.move.b[1] + 1)],
            "clear_count": int(sample.marked_outcome.clear_count),
            "run_count": int(sample.marked_outcome.run_count),
            "cleared_cells": [[int(row + 1), int(col + 1)] for row, col in sample.marked_outcome.cleared_cells],
            "bbox_px": [float(value) for value in bbox],
        }
        entities.append(dict(marked_spec))

    render_map = {
        "entity_bboxes_px": dict(entity_bboxes),
        "gem_bboxes_px": {str(spec["entity_id"]): [float(value) for value in spec["bbox_px"]] for spec in gem_specs},
        "swap_arrow_bboxes_px": {str(spec["entity_id"]): [float(value) for value in spec["bbox_px"]] for spec in option_specs},
        "marked_swap_arrow_bbox_px": None if marked_spec is None else [float(value) for value in marked_spec["bbox_px"]],
        "grid_bbox_px": [float(grid_left), float(grid_top), float(grid_left + grid_width), float(grid_top + grid_height)],
        "scene_variant": str(sample.scene_variant),
        "style": dict(style_meta),
        "layout_jitter": attach_games_unit_size_jitter(resolved_jitter, unit_meta),
        "effective_cell_size_px": int(cell),
        "effective_cell_gap_px": int(gap),
    }
    return _RenderedScene(
        image=image.convert("RGB"),
        entities=tuple(entities),
        render_map=dict(render_map),
        style_meta=dict(style_meta),
        background_meta=dict(background_meta),
    )


def _json_examples(query_id: str) -> Tuple[str, str]:
    if str(query_id) in SUPPORTED_BEST_SWAP_QUERIES:
        answer_and_evidence = {"evidence": [[410, 240, 520, 330], [448, 224, 502, 278]], "answer": "C"}
        answer_only = {"answer": "C"}
    else:
        answer_and_evidence = {"evidence": [[410, 240, 520, 330], [448, 224, 502, 278]], "answer": 4}
        answer_only = {"answer": 4}
    return (
        json.dumps(answer_and_evidence, ensure_ascii=True, allow_nan=False, separators=(",", ":")),
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
            "object_description_match3_grid",
            f"answer_hint_{str(sample.query_id)}",
            f"evidence_hint_{str(sample.query_id)}",
            "match3_rule_text",
        ),
        context=f"prompt defaults for {str(sample.query_id)}",
    )
    json_example, json_example_answer_only = _json_examples(str(sample.query_id))
    slots = {
        "object_description": str(prompt_defaults["object_description_match3_grid"]),
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "answer_hint": str(prompt_defaults[f"answer_hint_{str(sample.query_id)}"]),
        "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(sample.query_id)}"]),
        "json_example": str(json_example),
        "json_example_answer_only": str(json_example_answer_only),
        "match3_rule_text": str(prompt_defaults["match3_rule_text"]),
        "target_clear_count": "" if sample.target_clear_count is None else str(int(sample.target_clear_count)),
    }
    prompt_selection = render_task_prompt_variants(
        domain="games",
        task_group=TASK_GROUP,
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(prompt_defaults["task_key"]),
        query_key=str(sample.query_id),
        answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
        slots=slots,
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
    return str(prompt_artifacts.prompt), dict(prompt_artifacts.prompt_variants), {
        "bundle_id": str(prompt_defaults["bundle_id"]),
        "prompt_variant": dict(prompt_artifacts.prompt_variant),
        "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
        "prompt_variants_for_trace": dict(prompt_artifacts.prompt_variants_for_trace),
    }


def _build_complexity(*, task_id: str, sample: _Sample, evidence_count: int) -> Any:
    weights = resolve_games_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=str(task_id))
    rows = len(sample.board)
    cols = len(sample.board[0]) if rows else 0
    query_reasoning = {
        QUERY_CLEARED_COUNT: 0.48,
        QUERY_CREATED_RUN_COUNT: 0.58,
        QUERY_MAX_CLEAR_LABEL: 0.72,
        QUERY_TARGET_CLEAR_LABEL: 0.68,
    }[str(sample.query_id)]
    option_load = len(sample.option_specs) if sample.option_specs else 1
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": normalize_linear(float(rows * cols), min_value=25.0, max_value=49.0),
            "state_reasoning": float(query_reasoning),
            "ambiguity": normalize_linear(float(option_load), min_value=1.0, max_value=8.0),
            "output_burden": normalize_linear(float(evidence_count), min_value=1.0, max_value=10.0),
        },
    )


class _Match3Task:
    """Shared generator for public match-3 tasks."""

    domain = "games"
    task_group = TASK_GROUP
    default_dataset_enabled = True
    supported_queries: Tuple[str, ...]
    query_weights_key: str

    def _sample(self, rng, *, task_id: str, instance_seed: int, params: Mapping[str, Any], scene_variant: str, query_id: str) -> _Sample:
        if str(query_id) in SUPPORTED_EFFECT_VALUE_QUERIES:
            return _sample_effect_value(
                rng,
                task_id=str(task_id),
                instance_seed=int(instance_seed),
                params=params,
                scene_variant=str(scene_variant),
                query_id=str(query_id),
            )
        return _sample_best_swap_label(
            rng,
            task_id=str(task_id),
            instance_seed=int(instance_seed),
            params=params,
            scene_variant=str(scene_variant),
            query_id=str(query_id),
        )

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        params = _task_effective_params(str(self.task_id), params)
        scene_variant, scene_variant_probabilities = _sample_scene_variant(
            task_id=str(self.task_id),
            instance_seed=int(instance_seed),
            params=params,
        )
        style_variant, style_variant_probabilities = _sample_style_variant(
            task_id=str(self.task_id),
            instance_seed=int(instance_seed),
            params=params,
        )
        query_id, query_probabilities = _sample_query_variant(
            task_id=str(self.task_id),
            instance_seed=int(instance_seed),
            params=params,
            supported=tuple(self.supported_queries),
            weights_key=str(self.query_weights_key),
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
                    scene_variant=str(scene_variant),
                    query_id=str(query_id),
                )
                break
            except ValueError:
                continue
        if sample is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid match-3 scene after {max_attempts} attempts")

        rendered = _render_scene(
            sample=sample,
            task_id=str(self.task_id),
            instance_seed=int(instance_seed),
            params=params,
        )
        evidence_bboxes = [
            list(rendered.render_map["entity_bboxes_px"][str(entity_id)])
            for entity_id in sample.evidence_entity_ids
            if str(entity_id) in rendered.render_map["entity_bboxes_px"]
        ]
        prompt, prompt_variants, prompt_meta = _build_prompt(sample, instance_seed=int(instance_seed))
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        answer_gt = TypedValue(type=str(sample.answer_type), value=sample.answer)
        evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in evidence_bboxes])
        complexity = _build_complexity(task_id=str(self.task_id), sample=sample, evidence_count=len(evidence_bboxes))
        option_trace = [
            {
                "label": str(option.label),
                "entity_id": str(option.entity_id),
                "from_cell": [int(option.outcome.move.a[0] + 1), int(option.outcome.move.a[1] + 1)],
                "to_cell": [int(option.outcome.move.b[0] + 1), int(option.outcome.move.b[1] + 1)],
                "clear_count": int(option.outcome.clear_count),
                "run_count": int(option.outcome.run_count),
                "cleared_cells": [[int(row + 1), int(col + 1)] for row, col in option.outcome.cleared_cells],
                "runs": [[[int(row + 1), int(col + 1)] for row, col in run] for run in option.outcome.runs],
                "is_answer": bool(option.is_answer),
            }
            for option in sample.option_specs
        ]
        marked_trace = None
        if sample.marked_outcome is not None:
            marked_trace = {
                "from_cell": [int(sample.marked_outcome.move.a[0] + 1), int(sample.marked_outcome.move.a[1] + 1)],
                "to_cell": [int(sample.marked_outcome.move.b[0] + 1), int(sample.marked_outcome.move.b[1] + 1)],
                "clear_count": int(sample.marked_outcome.clear_count),
                "run_count": int(sample.marked_outcome.run_count),
                "cleared_cells": [[int(row + 1), int(col + 1)] for row, col in sample.marked_outcome.cleared_cells],
                "runs": [[[int(row + 1), int(col + 1)] for row, col in run] for run in sample.marked_outcome.runs],
            }
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_match3_{str(sample.scene_variant)}",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "scene_variant": str(sample.scene_variant),
                    "query_id": str(sample.query_id),
                    "query_variant": str(sample.query_id),
                    "query_variant": "default",
                    "style_variant": str(style_variant),
                    "rows": int(len(sample.board)),
                    "cols": int(len(sample.board[0]) if sample.board else 0),
                    "evidence_entity_ids": [str(entity_id) for entity_id in sample.evidence_entity_ids],
                },
            },
            "query_spec": {
                "query_variant": "default",
                "query_id": str(sample.query_id),
                "query_variant": str(sample.query_id),
                "template_id": str(prompt_meta["bundle_id"]),
                "prompt_variant": dict(prompt_meta["prompt_variant"]),
                "prompt_variant_active_key": str(prompt_meta["prompt_variant_active_key"]),
                "prompt_variants": dict(prompt_meta["prompt_variants_for_trace"]),
                "params": {
                    "scene_variant": str(sample.scene_variant),
                    "query_id": str(sample.query_id),
                    "query_variant": str(sample.query_id),
                    "query_variant": "default",
                    "style_variant": str(style_variant),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "query_variant_probabilities": dict(query_probabilities),
                    "query_variant_probabilities": {"default": 1.0},
                    "style_variant_probabilities": dict(style_variant_probabilities),
                    **dict(sample.metadata),
                },
            },
            "render_spec": {
                "scene_variant": str(sample.scene_variant),
                "style_variant": str(style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "layout_jitter": dict(rendered.render_map.get("layout_jitter", {})),
                "panel_scene_style": dict(rendered.style_meta),
                "effective_cell_size_px": rendered.render_map.get("effective_cell_size_px"),
            },
            "render_map": dict(rendered.render_map),
            "execution_trace": {
                "scene_variant": str(sample.scene_variant),
                "query_id": str(sample.query_id),
                "query_variant": str(sample.query_id),
                "query_variant": "default",
                "style_variant": str(style_variant),
                "board_before": [list(row) for row in sample.board],
                "swap_options": option_trace,
                "marked_outcome": marked_trace,
                "target_clear_count": None if sample.target_clear_count is None else int(sample.target_clear_count),
                "target_run_count": None if sample.target_run_count is None else int(sample.target_run_count),
                "answer": sample.answer,
                "evidence_entity_ids": [str(entity_id) for entity_id in sample.evidence_entity_ids],
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(entity_id) for entity_id in sample.evidence_entity_ids],
            },
            "projected_evidence": {
                "bbox_set": [list(bbox) for bbox in evidence_bboxes],
            },
            "background": dict(rendered.background_meta),
            "post_image_noise": dict(post_noise_meta),
        }
        return TaskOutput(
            prompt=str(prompt),
            prompt_variants=dict(prompt_variants),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_variant="default",
            scene_id=SCENE_ID,
            query_id=str(sample.query_id),
        )


@register_task
class GamesMatch3SwapEffectValueTask(_Match3Task):
    """Compute a numeric effect of one marked match-3 swap."""

    task_id = "task_games__match3__swap_effect_value"
    supported_queries = SUPPORTED_EFFECT_VALUE_QUERIES
    query_weights_key = "effect_value_query_variant_weights"


@register_task
class GamesMatch3BestSwapLabelTask(_Match3Task):
    """Choose a labeled match-3 swap by immediate clear effect."""

    task_id = "task_games__match3__best_swap_label"
    supported_queries = SUPPORTED_BEST_SWAP_QUERIES
    query_weights_key = "best_swap_query_variant_weights"


__all__ = [
    "GamesMatch3BestSwapLabelTask",
    "GamesMatch3SwapEffectValueTask",
]
