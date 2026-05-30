"""Games Sudoku-grid tasks for digit placement, candidates, missing digits, and rule violations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

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
from ..shared.complexity import build_games_sudoku_grid_complexity
from ..shared.fixed_query_task import FixedQueryVariantTaskMixin
from ..shared.layout import attach_games_unit_size_jitter, resolve_games_layout_jitter, resolve_games_unit_size_scale, scale_games_px
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_id
from ..shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from ..shared.style import SUPPORTED_SUDOKU_STYLE_VARIANTS
from ..shared.sudoku_common import (
    DIGITS,
    SIZE,
    SUPPORTED_SUDOKU_QUERY_IDS,
    SUPPORTED_SUDOKU_SCENE_VARIANTS,
    SUPPORTED_SUDOKU_UNIT_TYPES,
    Board,
    Coord,
    SudokuSample,
    add_random_solution_givens,
    build_sudoku_solution,
    candidate_digits,
    coord_to_cell_id,
    coords_with_solution_value,
    freeze_board,
    missing_digits_in_unit,
    mutable_empty_board,
    peer_coords,
    repeated_digits_in_unit,
    unit_coords,
    visible_cell_count,
)
from ..shared.sudoku_scene import SudokuRenderParams, render_sudoku_grid_scene
from ..shared.visual_defaults import load_games_noise_defaults


TASK_ID = "games_sudoku_grid_base"


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for visible Sudoku-grid scenes."""

    marked_cell_value_support: Tuple[int, ...] = tuple(DIGITS)
    marked_cell_candidate_count_support: Tuple[int, ...] = (1, 2, 3, 4, 5)
    unit_missing_digits_count_support: Tuple[int, ...] = (2, 3, 4, 5, 6)
    repeated_digit_count_support: Tuple[int, ...] = (1, 2, 3, 4)
    sparse_min_visible_count: int = 18
    sparse_max_visible_count: int = 26
    filled_min_visible_count: int = 28
    filled_max_visible_count: int = 42
    canvas_width: int = 900
    canvas_height: int = 900
    panel_margin_px: int = 48
    max_board_size_px: int = 760
    board_border_width_px: int = 5
    grid_line_width_px: int = 2
    box_line_width_px: int = 5
    cell_padding_px: int = 5
    digit_font_size_px: int = 48
    marked_cell_outline_width_px: int = 7


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one Sudoku-grid scene."""

    query_id: str
    scene_variant: str
    unit_type: str
    style_variant: str
    target_answer: int
    target_answer_support: Tuple[int, ...]
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    unit_type_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "sudoku")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="sudoku", apply_prob=0.5)


def _target_support_key(query_id: str) -> str:
    """Return the configured answer-support key for one Sudoku query."""

    return {
        "marked_cell_value": "marked_cell_value_support",
        "marked_cell_candidate_count": "marked_cell_candidate_count_support",
        "unit_missing_digits_count": "unit_missing_digits_count_support",
        "repeated_digit_count": "repeated_digit_count_support",
    }[str(query_id)]


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
    if len(positives) != len(SUPPORTED_SUDOKU_QUERY_IDS):
        return False
    return max(positives) - min(positives) <= 1e-9


def _params_for_query_occurrence_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    """Use a per-query occurrence index for balanced inner axes."""

    cycle_params = dict(params)
    sampling_index = params.get("_sample_cursor")
    if sampling_index is None:
        return cycle_params
    if not _uses_uniform_query_cycle(params, query_id_probabilities):
        return cycle_params
    cycle_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(SUPPORTED_SUDOKU_QUERY_IDS))
    return cycle_params


def _resolve_query_id(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced Sudoku query id."""

    return resolve_games_query_id(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_SUDOKU_QUERY_IDS,
    )


def _resolve_named_axis(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    supported: Tuple[str, ...],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced named Sudoku axis."""

    return resolve_games_named_axis(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        namespace=str(namespace),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        supported_variants=supported,
    )


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve all semantic and visual axes for one Sudoku instance."""

    query_id, query_id_probabilities = _resolve_query_id(
        instance_seed=int(instance_seed),
        params=params,
    )
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
        supported=SUPPORTED_SUDOKU_SCENE_VARIANTS,
    )
    unit_type, unit_type_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=cycle_params,
        namespace="unit_type",
        explicit_key="unit_type",
        weights_key="unit_type_weights",
        balance_flag_key="balanced_unit_type_sampling",
        supported=SUPPORTED_SUDOKU_UNIT_TYPES,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=cycle_params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_SUDOKU_STYLE_VARIANTS,
    )
    support_key = _target_support_key(str(query_id))
    target_answer, target_answer_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=cycle_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=str(support_key),
        explicit_key="target_answer",
        fallback_support=getattr(_DEFAULTS, support_key),
        namespace=f"{TASK_ID}.target_answer.{str(query_id)}",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_support_permutation=True,
    )
    target_answer_support = resolve_integer_support(
        cycle_params,
        gen_defaults=_GEN_DEFAULTS,
        key=str(support_key),
        fallback=getattr(_DEFAULTS, support_key),
    )
    return _ResolvedAxes(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        unit_type=str(unit_type),
        style_variant=str(style_variant),
        target_answer=int(target_answer),
        target_answer_support=tuple(int(value) for value in target_answer_support),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        unit_type_probabilities=dict(unit_type_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> SudokuRenderParams:
    """Resolve Sudoku rendering parameters from config/defaults."""

    unit_scale, unit_scale_meta = resolve_games_unit_size_scale(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="games.sudoku.unit_size",
    )
    layout_jitter = attach_games_unit_size_jitter(
        resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.sudoku.layout",
        ),
        unit_scale_meta,
    )
    max_board_size_px = scale_games_px(
        params.get("max_board_size_px", group_default(_RENDER_DEFAULTS, "max_board_size_px", _DEFAULTS.max_board_size_px)),
        unit_scale,
        min_px=380,
    )
    default_canvas_width = int(group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))
    default_canvas_height = int(group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))
    canvas_size = int(max(540, min(max(default_canvas_width, default_canvas_height), int(max_board_size_px) + 160)))
    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace="games.sudoku.font_family",
        params=params,
    )
    return SudokuRenderParams(
        canvas_width=int(params.get("canvas_width", canvas_size)),
        canvas_height=int(params.get("canvas_height", canvas_size)),
        panel_margin_px=int(params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px))),
        max_board_size_px=int(max_board_size_px),
        board_border_width_px=scale_games_px(params.get("board_border_width_px", group_default(_RENDER_DEFAULTS, "board_border_width_px", _DEFAULTS.board_border_width_px)), unit_scale, min_px=2),
        grid_line_width_px=scale_games_px(params.get("grid_line_width_px", group_default(_RENDER_DEFAULTS, "grid_line_width_px", _DEFAULTS.grid_line_width_px)), unit_scale, min_px=1),
        box_line_width_px=scale_games_px(params.get("box_line_width_px", group_default(_RENDER_DEFAULTS, "box_line_width_px", _DEFAULTS.box_line_width_px)), unit_scale, min_px=2),
        cell_padding_px=scale_games_px(params.get("cell_padding_px", group_default(_RENDER_DEFAULTS, "cell_padding_px", _DEFAULTS.cell_padding_px)), unit_scale, min_px=3),
        digit_font_size_px=scale_games_px(params.get("digit_font_size_px", group_default(_RENDER_DEFAULTS, "digit_font_size_px", _DEFAULTS.digit_font_size_px)), unit_scale, min_px=18),
        marked_cell_outline_width_px=scale_games_px(params.get("marked_cell_outline_width_px", group_default(_RENDER_DEFAULTS, "marked_cell_outline_width_px", _DEFAULTS.marked_cell_outline_width_px)), unit_scale, min_px=3),
        font_family=str(font_family),
        layout_jitter_meta=layout_jitter,
    )


def _visible_count_bounds(scene_variant: str) -> Tuple[int, int]:
    """Return total visible-cell bounds for one Sudoku scene variant."""

    if str(scene_variant) == "filled_grid":
        return int(_DEFAULTS.filled_min_visible_count), int(_DEFAULTS.filled_max_visible_count)
    return int(_DEFAULTS.sparse_min_visible_count), int(_DEFAULTS.sparse_max_visible_count)


def _target_visible_count(*, rng, scene_variant: str, minimum_floor: int = 0) -> int:
    """Sample one total visible-cell count, respecting required visible cells."""

    low, high = _visible_count_bounds(str(scene_variant))
    lower = max(int(low), int(minimum_floor))
    upper = max(int(lower), int(high))
    return int(rng.randint(int(lower), int(upper)))


def _sample_marked_cell_value(*, rng, solution: Board, axes: _ResolvedAxes) -> SudokuSample:
    """Construct one board where the marked cell has a unique valid value."""

    target_digit = int(axes.target_answer)
    marked_cell = tuple(rng.choice(coords_with_solution_value(solution, target_digit)))
    board = mutable_empty_board()
    filled_peer_coords: set[Coord] = set()
    peers = peer_coords(marked_cell)
    for digit in DIGITS:
        if int(digit) == int(target_digit):
            continue
        candidates = [coord for coord in peers if int(solution[coord[0]][coord[1]]) == int(digit)]
        if not candidates:
            raise ValueError(f"missing Sudoku peer witness for digit {digit}")
        coord = tuple(rng.choice(candidates))
        board[coord[0]][coord[1]] = int(digit)
        filled_peer_coords.add(coord)
    excluded = set(filled_peer_coords)
    excluded.add(marked_cell)
    target_visible = _target_visible_count(
        rng=rng,
        scene_variant=str(axes.scene_variant),
        minimum_floor=len(filled_peer_coords),
    )
    add_random_solution_givens(
        rng=rng,
        board=board,
        solution=solution,
        excluded_coords=excluded,
        target_visible_count=int(target_visible),
    )
    frozen = freeze_board(board)
    candidates = candidate_digits(frozen, marked_cell)
    if candidates != (int(target_digit),):
        raise ValueError("constructed Sudoku marked cell is not uniquely solved")
    visible_peers = [
        coord
        for coord in peer_coords(marked_cell)
        if int(frozen[coord[0]][coord[1]]) != 0
    ]
    evidence_coords = tuple([marked_cell] + sorted(visible_peers))
    return SudokuSample(
        board=frozen,
        solution=solution,
        query_id=str(axes.query_id),
        answer=int(target_digit),
        evidence_coords=evidence_coords,
        marked_cell=marked_cell,
        highlighted_unit_type=None,
        highlighted_unit_index=None,
        repeated_digit_values=(),
        missing_digit_values=(),
        visible_count=int(visible_cell_count(frozen)),
        construction_mode="unique_marked_cell",
    )


def _sample_marked_cell_candidate_count(*, rng, solution: Board, axes: _ResolvedAxes) -> SudokuSample:
    """Construct one board where the marked cell has exactly the target candidate count."""

    target_count = int(axes.target_answer)
    if target_count < 1 or target_count > len(DIGITS):
        raise ValueError(f"unsupported Sudoku candidate count: {target_count}")
    marked_cell = (int(rng.randrange(SIZE)), int(rng.randrange(SIZE)))
    solution_digit = int(solution[marked_cell[0]][marked_cell[1]])
    eliminable_digits = [int(digit) for digit in DIGITS if int(digit) != int(solution_digit)]
    eliminated_digits = set(int(digit) for digit in rng.sample(eliminable_digits, k=int(len(DIGITS) - target_count)))

    board = mutable_empty_board()
    filled_peer_coords: set[Coord] = set()
    peers = peer_coords(marked_cell)
    for digit in sorted(eliminated_digits):
        candidates = [coord for coord in peers if int(solution[coord[0]][coord[1]]) == int(digit)]
        if not candidates:
            raise ValueError(f"missing Sudoku peer witness for digit {digit}")
        coord = tuple(rng.choice(candidates))
        board[coord[0]][coord[1]] = int(digit)
        filled_peer_coords.add(coord)

    excluded = set(peers)
    excluded.add(marked_cell)
    target_visible = _target_visible_count(
        rng=rng,
        scene_variant=str(axes.scene_variant),
        minimum_floor=len(filled_peer_coords),
    )
    add_random_solution_givens(
        rng=rng,
        board=board,
        solution=solution,
        excluded_coords=excluded,
        target_visible_count=int(target_visible),
    )
    frozen = freeze_board(board)
    candidates = candidate_digits(frozen, marked_cell)
    if len(candidates) != int(target_count):
        raise ValueError("constructed Sudoku marked cell has wrong candidate count")
    evidence_coords = tuple([marked_cell] + sorted(filled_peer_coords))
    return SudokuSample(
        board=frozen,
        solution=solution,
        query_id=str(axes.query_id),
        answer=int(target_count),
        evidence_coords=evidence_coords,
        marked_cell=marked_cell,
        highlighted_unit_type=None,
        highlighted_unit_index=None,
        repeated_digit_values=(),
        missing_digit_values=(),
        visible_count=int(visible_cell_count(frozen)),
        construction_mode="marked_cell_candidate_count",
    )


def _sample_unit_missing_digits(*, rng, solution: Board, axes: _ResolvedAxes) -> SudokuSample:
    """Construct one board with a highlighted unit missing exactly the target digits."""

    unit_type = str(axes.unit_type)
    unit_index = int(rng.randrange(SIZE))
    unit = unit_coords(unit_type, unit_index)
    missing_digits = tuple(sorted(rng.sample(list(DIGITS), k=int(axes.target_answer))))
    missing_digit_set = {int(digit) for digit in missing_digits}
    board = mutable_empty_board()
    for row, col in unit:
        value = int(solution[row][col])
        if value not in missing_digit_set:
            board[row][col] = int(value)
    target_visible = _target_visible_count(
        rng=rng,
        scene_variant=str(axes.scene_variant),
        minimum_floor=int(visible_cell_count(board)),
    )
    add_random_solution_givens(
        rng=rng,
        board=board,
        solution=solution,
        excluded_coords=unit,
        target_visible_count=int(target_visible),
    )
    frozen = freeze_board(board)
    missing = missing_digits_in_unit(frozen, unit_type=unit_type, unit_index=unit_index)
    if tuple(missing) != tuple(missing_digits):
        raise ValueError("constructed Sudoku unit does not match requested missing digits")
    evidence_coords = tuple(
        coord
        for coord in unit
        if int(frozen[coord[0]][coord[1]]) != 0
    )
    return SudokuSample(
        board=frozen,
        solution=solution,
        query_id=str(axes.query_id),
        answer=int(len(missing_digits)),
        evidence_coords=tuple(evidence_coords),
        marked_cell=None,
        highlighted_unit_type=unit_type,
        highlighted_unit_index=int(unit_index),
        repeated_digit_values=(),
        missing_digit_values=tuple(int(value) for value in missing_digits),
        visible_count=int(visible_cell_count(frozen)),
        construction_mode="unit_missing_digits",
    )


def _sample_repeated_digit_count(*, rng, solution: Board, axes: _ResolvedAxes) -> SudokuSample:
    """Construct one highlighted unit with exactly the target number of repeated digit types."""

    unit_type = str(axes.unit_type)
    unit_index = int(rng.randrange(SIZE))
    unit = list(unit_coords(unit_type, unit_index))
    rng.shuffle(unit)
    repeated_digits = tuple(sorted(rng.sample(list(DIGITS), k=int(axes.target_answer))))
    board = mutable_empty_board()
    cursor = 0
    for digit in repeated_digits:
        for _ in range(2):
            row, col = unit[cursor]
            cursor += 1
            board[row][col] = int(digit)
    remaining_cells = unit[cursor:]
    singleton_digits = [digit for digit in DIGITS if int(digit) not in set(repeated_digits)]
    rng.shuffle(singleton_digits)
    max_singletons = min(len(remaining_cells), len(singleton_digits))
    min_singletons = 0 if int(axes.target_answer) >= 4 else 1
    singleton_count = int(rng.randint(int(min_singletons), int(max_singletons))) if int(max_singletons) > 0 else 0
    for index in range(singleton_count):
        row, col = remaining_cells[index]
        board[row][col] = int(singleton_digits[index])
    target_visible = _target_visible_count(
        rng=rng,
        scene_variant=str(axes.scene_variant),
        minimum_floor=int(visible_cell_count(board)),
    )
    add_random_solution_givens(
        rng=rng,
        board=board,
        solution=solution,
        excluded_coords=unit,
        target_visible_count=int(target_visible),
    )
    frozen = freeze_board(board)
    repeated = repeated_digits_in_unit(frozen, unit_type=unit_type, unit_index=unit_index)
    if tuple(repeated) != tuple(repeated_digits):
        raise ValueError("constructed Sudoku highlighted unit has wrong repeated digit count")
    evidence_coords = tuple(
        coord
        for coord in unit_coords(unit_type, unit_index)
        if int(frozen[coord[0]][coord[1]]) in set(repeated_digits)
    )
    return SudokuSample(
        board=frozen,
        solution=solution,
        query_id=str(axes.query_id),
        answer=int(len(repeated_digits)),
        evidence_coords=tuple(evidence_coords),
        marked_cell=None,
        highlighted_unit_type=unit_type,
        highlighted_unit_index=int(unit_index),
        repeated_digit_values=tuple(int(value) for value in repeated_digits),
        missing_digit_values=(),
        visible_count=int(visible_cell_count(frozen)),
        construction_mode="highlighted_unit_repeats",
    )


def _sample_scene(*, rng, axes: _ResolvedAxes) -> SudokuSample:
    """Construct one Sudoku scene for the requested axes."""

    solution = build_sudoku_solution(rng)
    if str(axes.query_id) == "marked_cell_value":
        return _sample_marked_cell_value(rng=rng, solution=solution, axes=axes)
    if str(axes.query_id) == "marked_cell_candidate_count":
        return _sample_marked_cell_candidate_count(rng=rng, solution=solution, axes=axes)
    if str(axes.query_id) == "unit_missing_digits_count":
        return _sample_unit_missing_digits(rng=rng, solution=solution, axes=axes)
    if str(axes.query_id) == "repeated_digit_count":
        return _sample_repeated_digit_count(rng=rng, solution=solution, axes=axes)
    raise ValueError(f"unsupported Sudoku query_id: {axes.query_id}")


def _unit_scope_text(prompt_defaults: Mapping[str, Any], unit_type: str | None) -> str:
    """Return the prompt-facing phrase for one highlighted unit type."""

    if unit_type is None:
        return ""
    return str(prompt_defaults[f"unit_scope_text_{str(unit_type)}"])


def _build_prompt_json_examples(query_id: str) -> Tuple[str, str]:
    """Return deterministic prompt examples for Sudoku JSON output."""

    answer_value = 7 if str(query_id) == "marked_cell_value" else 3
    evidence_value = [[140, 220, 210, 290], [210, 220, 280, 290], [280, 220, 350, 290]]
    return (
        json.dumps({"evidence": evidence_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


class GamesSudokuGridTask:
    """Return one grounded query over a visible Sudoku grid."""

    task_id = TASK_ID
    domain = "games"
    task_group = "sudoku"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        render_params = _render_params(params, instance_seed=int(instance_seed))

        sampled_scene: SudokuSample | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sampled_scene = _sample_scene(rng=attempt_rng, axes=axes)
            except ValueError:
                continue
            break
        if sampled_scene is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts")

        panel_style, panel_style_meta = resolve_game_panel_scene_style(
            instance_seed=int(instance_seed),
            namespace="games.sudoku.panel_scene_style",
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
        rendered_scene = render_sudoku_grid_scene(
            board=sampled_scene.board,
            background=background,
            style_variant=str(axes.style_variant),
            params=render_params,
            highlighted_unit_type=sampled_scene.highlighted_unit_type,
            highlighted_unit_index=sampled_scene.highlighted_unit_index,
            marked_cell=sampled_scene.marked_cell,
            conflict_coords=sampled_scene.evidence_coords if str(axes.query_id) == "repeated_digit_count" else (),
            panel_style=panel_style,
        )
        evidence_entity_ids = [coord_to_cell_id(coord) for coord in sampled_scene.evidence_coords]
        evidence_bboxes = [
            list(rendered_scene.render_map["cell_bboxes_px"][str(entity_id)])
            for entity_id in evidence_entity_ids
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
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description_sparse_grid",
                "object_description_filled_grid",
                "sudoku_rule_text",
                "marked_cell_rule_text",
                "highlighted_unit_rule_text",
                "unit_scope_text_row",
                "unit_scope_text_column",
                "unit_scope_text_box",
                "answer_hint_marked_cell_value",
                "answer_hint_marked_cell_candidate_count",
                "answer_hint_unit_missing_digits_count",
                "answer_hint_repeated_digit_count",
                "evidence_hint_marked_cell_value",
                "evidence_hint_marked_cell_candidate_count",
                "evidence_hint_unit_missing_digits_count",
                "evidence_hint_repeated_digit_count",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples(str(axes.query_id))
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(axes.query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults[f"object_description_{str(axes.scene_variant)}"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_id)}"]),
                "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(axes.query_id)}"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "sudoku_rule_text": str(prompt_defaults["sudoku_rule_text"]),
                "marked_cell_rule_text": str(prompt_defaults["marked_cell_rule_text"]),
                "highlighted_unit_rule_text": str(prompt_defaults["highlighted_unit_rule_text"]),
                "unit_scope_text": _unit_scope_text(prompt_defaults, sampled_scene.highlighted_unit_type),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(sampled_scene.answer))
        evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in evidence_bboxes])
        text_style_meta = {
            "font_family": str(render_params.font_family),
            "font_asset": get_font_family_record(str(render_params.font_family)).to_trace(),
        }
        complexity = build_games_sudoku_grid_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=TASK_ID,
            scene_variant=str(axes.scene_variant),
            query_id=str(axes.query_id),
            visible_count=int(sampled_scene.visible_count),
            target_answer=int(sampled_scene.answer),
            evidence_count=len(evidence_entity_ids),
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_sudoku_grid_{str(axes.scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "unit_type": sampled_scene.highlighted_unit_type,
                    "unit_index": sampled_scene.highlighted_unit_index,
                    "style_variant": str(axes.style_variant),
                    "target_answer": int(sampled_scene.answer),
                    "visible_count": int(sampled_scene.visible_count),
                    "evidence_entity_ids": [str(entity_id) for entity_id in evidence_entity_ids],
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
                    "unit_type": sampled_scene.highlighted_unit_type,
                    "unit_index": sampled_scene.highlighted_unit_index,
                    "style_variant": str(axes.style_variant),
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "unit_type_probabilities": dict(axes.unit_type_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "target_answer": int(sampled_scene.answer),
                    "target_answer_support": [int(value) for value in axes.target_answer_support],
                    "target_answer_probabilities": dict(axes.target_answer_probabilities),
                    "visible_count": int(sampled_scene.visible_count),
                },
            },
            "render_spec": {
                "scene_variant": str(axes.scene_variant),
                "style_variant": str(axes.style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
                "panel_scene_style": dict(panel_style_meta),
                "text_style": dict(text_style_meta),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(axes.scene_variant),
                "query_id": str(axes.query_id),
                "style_variant": str(axes.style_variant),
                "target_answer": int(sampled_scene.answer),
                "target_answer_support": [int(value) for value in axes.target_answer_support],
                "visible_count": int(sampled_scene.visible_count),
                "construction_mode": str(sampled_scene.construction_mode),
                "board_rows": [[int(cell) for cell in row] for row in sampled_scene.board],
                "solution_rows": [[int(cell) for cell in row] for row in sampled_scene.solution],
                "marked_cell": list(sampled_scene.marked_cell) if sampled_scene.marked_cell is not None else None,
                "candidate_digit_values": [
                    int(value)
                    for value in (
                        candidate_digits(sampled_scene.board, sampled_scene.marked_cell)
                        if sampled_scene.marked_cell is not None
                        else ()
                    )
                ],
                "highlighted_unit_type": sampled_scene.highlighted_unit_type,
                "highlighted_unit_index": sampled_scene.highlighted_unit_index,
                "highlighted_unit_coords": [
                    [int(row), int(col)]
                    for row, col in (
                        unit_coords(sampled_scene.highlighted_unit_type, int(sampled_scene.highlighted_unit_index))
                        if sampled_scene.highlighted_unit_type is not None and sampled_scene.highlighted_unit_index is not None
                        else ()
                    )
                ],
                "missing_digit_values": [int(value) for value in sampled_scene.missing_digit_values],
                "repeated_digit_values": [int(value) for value in sampled_scene.repeated_digit_values],
                "evidence_coords": [[int(row), int(col)] for row, col in sampled_scene.evidence_coords],
                "evidence_entity_ids": [str(entity_id) for entity_id in evidence_entity_ids],
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(entity_id) for entity_id in evidence_entity_ids],
            },
            "projected_evidence": {
                "type": "bbox_set",
                "bbox_set": [list(bbox) for bbox in evidence_bboxes],
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
            scene_id="sudoku",
            query_id=str(axes.query_id),
        )


@register_task
class GamesSudokuMarkedCellValueTask(FixedQueryVariantTaskMixin, GamesSudokuGridTask):
    """Find the unique digit for a marked empty Sudoku cell."""

    task_id = "task_games__sudoku__marked_cell_value"
    fixed_query_id = "marked_cell_value"


@register_task
class GamesSudokuMarkedCellCandidateCountTask(FixedQueryVariantTaskMixin, GamesSudokuGridTask):
    """Count legal candidate digits for a marked empty Sudoku cell."""

    task_id = "task_games__sudoku__marked_cell_candidate_count"
    fixed_query_id = "marked_cell_candidate_count"


@register_task
class GamesSudokuUnitMissingDigitsCountTask(FixedQueryVariantTaskMixin, GamesSudokuGridTask):
    """Count missing digit values in a highlighted Sudoku unit."""

    task_id = "task_games__sudoku__unit_missing_digits_count"
    fixed_query_id = "unit_missing_digits_count"


@register_task
class GamesSudokuRepeatedDigitCountTask(FixedQueryVariantTaskMixin, GamesSudokuGridTask):
    """Count repeated digit values in a highlighted Sudoku unit."""

    task_id = "task_games__sudoku__repeated_digit_count"
    fixed_query_id = "repeated_digit_count"


__all__ = [
    "GamesSudokuGridTask",
    "GamesSudokuMarkedCellCandidateCountTask",
    "GamesSudokuMarkedCellValueTask",
    "GamesSudokuRepeatedDigitCountTask",
    "GamesSudokuUnitMissingDigitsCountTask",
]
