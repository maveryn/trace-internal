"""Games tasks with explicit rule overrides over small board-game panels."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.font_assets import get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.support_sampling import resolve_integer_choice, resolve_integer_support
from ...shared.text_legibility import draw_centered_traced_text
from ...shared.text_rendering import fit_font_to_box, load_font
from ..shared.complexity import build_games_complexity, normalize_linear, resolve_games_complexity_weights
from ..shared.layout import (
    apply_games_layout_jitter_to_bbox,
    attach_games_unit_size_jitter,
    resolve_games_layout_jitter,
    resolve_games_unit_size_scale,
    scale_games_px,
)
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_id
from ..shared.scene_style import draw_panel_scene_chrome, make_panel_scene_background, resolve_game_panel_scene_style
from ..shared.visual_defaults import load_games_noise_defaults


TASK_GROUP = "rule_override_board"
SCENE_ID = "rule_override_board"
BASE_TASK_ID = "games_rule_override_board_base"

LINE_WIN_QUERY_ID = "line_override_win_count"
LINE_LOSS_QUERY_ID = "line_override_loss_count"
PIECE_WIN_QUERY_ID = "piece_override_win_count"
PIECE_LOSS_QUERY_ID = "piece_override_loss_count"

SUPPORTED_LINE_QUERY_IDS: Tuple[str, ...] = (LINE_WIN_QUERY_ID, LINE_LOSS_QUERY_ID)
SUPPORTED_PIECE_QUERY_IDS: Tuple[str, ...] = (PIECE_WIN_QUERY_ID, PIECE_LOSS_QUERY_ID)
SUPPORTED_BOARD_STYLES: Tuple[str, ...] = (
    "classic",
    "paper",
    "chalkboard",
    "arcade",
    "wood",
)
LINE_PLAYERS: Tuple[str, ...] = ("X", "O")
PIECE_PLAYERS: Tuple[str, ...] = ("Black", "White")


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for rule-override board scenes."""

    board_count_support: Tuple[int, ...] = (4, 5, 6)
    target_answer_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6)
    line_board_size_support: Tuple[int, ...] = (3, 4)
    piece_board_size_support: Tuple[int, ...] = (4, 5)
    canvas_width: int = 1040
    canvas_height: int = 760
    cell_size_px: int = 56
    board_gap_px: int = 22
    board_padding_px: int = 14
    board_label_height_px: int = 38
    content_margin_px: int = 56
    panel_radius_px: int = 18
    panel_border_width_px: int = 2
    board_border_width_px: int = 3
    grid_width_px: int = 3
    board_label_font_size_px: int = 20
    mark_font_size_px: int = 34


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one rule-override scene."""

    board_family: str
    query_id: str
    board_style: str
    target_player: str
    board_count: int
    board_size: int
    target_answer: int
    query_id_probabilities: Dict[str, float]
    board_style_probabilities: Dict[str, float]
    target_player_probabilities: Dict[str, float]
    board_count_probabilities: Dict[str, float]
    board_size_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RenderParams:
    """Resolved rendering parameters for one rule-override scene."""

    canvas_width: int
    canvas_height: int
    cell_size_px: int
    board_gap_px: int
    board_padding_px: int
    board_label_height_px: int
    content_margin_px: int
    panel_radius_px: int
    panel_border_width_px: int
    board_border_width_px: int
    grid_width_px: int
    board_label_font_size_px: int
    mark_font_size_px: int
    font_family: str
    layout_jitter_meta: Dict[str, Any]
    unit_size_meta: Dict[str, Any]


@dataclass(frozen=True)
class _BoardPanel:
    """One rendered mini-board and its symbolic outcome."""

    board_id: str
    label: str
    cells: Tuple[Tuple[str, ...], ...]
    counted: bool
    result: str
    target_player: str
    target_stat: int
    opponent_stat: int


@dataclass(frozen=True)
class _SceneSample:
    """Complete sampled rule-override scene."""

    board_family: str
    query_id: str
    board_style: str
    target_player: str
    board_size: int
    answer: int
    rule_text: str
    boards: Tuple[_BoardPanel, ...]
    evidence_entity_ids: Tuple[str, ...]


@dataclass(frozen=True)
class _RenderedScene:
    """Rendered scene plus projection metadata."""

    image: Image.Image
    render_map: Dict[str, Any]
    scene_entities: Tuple[Dict[str, Any], ...]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", TASK_GROUP)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=BASE_TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group=TASK_GROUP, apply_prob=0.5)


def _board_grid_dimensions(board_count: int) -> tuple[int, int]:
    """Return display columns/rows for one mini-board collection."""

    count = max(1, int(board_count))
    cols = 2 if count <= 4 else 3
    rows = int(math.ceil(float(count) / float(cols)))
    return int(cols), int(rows)


def _query_is_win(query_id: str) -> bool:
    return str(query_id) in {LINE_WIN_QUERY_ID, PIECE_WIN_QUERY_ID}


def _query_is_line(query_id: str) -> bool:
    return str(query_id) in {LINE_WIN_QUERY_ID, LINE_LOSS_QUERY_ID}


def _opponent(player: str) -> str:
    if str(player) == "X":
        return "O"
    if str(player) == "O":
        return "X"
    if str(player) == "Black":
        return "White"
    if str(player) == "White":
        return "Black"
    raise ValueError(f"unsupported player: {player}")


def _resolve_axes(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    task_id: str,
    board_family: str,
    supported_query_ids: Sequence[str],
) -> _ResolvedAxes:
    """Resolve all sampled axes for one public rule-override task."""

    query_id, query_id_probabilities = resolve_games_query_id(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=tuple(str(item) for item in supported_query_ids),
    )
    board_style, board_style_probabilities = resolve_games_named_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        namespace="board_style",
        explicit_key="board_style",
        weights_key="board_style_weights",
        balance_flag_key="balanced_board_style_sampling",
        supported_variants=SUPPORTED_BOARD_STYLES,
    )
    player_support = LINE_PLAYERS if str(board_family) == "line" else PIECE_PLAYERS
    target_player, target_player_probabilities = resolve_games_named_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        namespace="target_player",
        explicit_key="target_player",
        weights_key=f"{str(board_family)}_target_player_weights",
        balance_flag_key="balanced_target_player_sampling",
        supported_variants=player_support,
    )
    board_count, board_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="board_count_support",
        explicit_key="board_count",
        fallback_support=_DEFAULTS.board_count_support,
        namespace=f"{BASE_TASK_ID}.board_count",
        balanced_flag_key="balanced_board_count_sampling",
        namespace_support_permutation=True,
    )
    size_key = "line_board_size_support" if str(board_family) == "line" else "piece_board_size_support"
    size_fallback = _DEFAULTS.line_board_size_support if str(board_family) == "line" else _DEFAULTS.piece_board_size_support
    board_size, board_size_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=size_key,
        explicit_key="board_size",
        fallback_support=size_fallback,
        namespace=f"{BASE_TASK_ID}.{str(board_family)}.board_size",
        balanced_flag_key="balanced_board_size_sampling",
        namespace_support_permutation=True,
    )
    raw_answer_support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key="target_answer_support",
        fallback=_DEFAULTS.target_answer_support,
    )
    conditional_answer_support = tuple(
        int(value)
        for value in raw_answer_support
        if 0 <= int(value) <= int(board_count)
    )
    if not conditional_answer_support:
        conditional_answer_support = tuple(range(0, int(board_count) + 1))
    answer_params = {
        **dict(params),
        "target_answer_support": conditional_answer_support,
    }
    target_answer, target_answer_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=answer_params,
        gen_defaults={},
        support_key="target_answer_support",
        explicit_key="target_answer",
        fallback_support=conditional_answer_support,
        namespace=f"{BASE_TASK_ID}.{str(board_family)}.answer",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_support_permutation=True,
    )
    return _ResolvedAxes(
        board_family=str(board_family),
        query_id=str(query_id),
        board_style=str(board_style),
        target_player=str(target_player),
        board_count=int(board_count),
        board_size=int(board_size),
        target_answer=int(target_answer),
        query_id_probabilities=dict(query_id_probabilities),
        board_style_probabilities=dict(board_style_probabilities),
        target_player_probabilities=dict(target_player_probabilities),
        board_count_probabilities=dict(board_count_probabilities),
        board_size_probabilities=dict(board_size_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
    )


def _resolve_render_params(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    axes: _ResolvedAxes,
) -> _RenderParams:
    """Resolve dynamic rendering parameters for one sampled scene."""

    unit_scale, unit_scale_meta = resolve_games_unit_size_scale(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="games.rule_override_board.unit_size",
    )
    layout_jitter = attach_games_unit_size_jitter(
        resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.rule_override_board.layout",
        ),
        unit_scale_meta,
    )
    cell_size = scale_games_px(
        params.get("cell_size_px", group_default(_RENDER_DEFAULTS, "cell_size_px", _DEFAULTS.cell_size_px)),
        unit_scale,
        min_px=28,
    )
    board_gap = scale_games_px(
        params.get("board_gap_px", group_default(_RENDER_DEFAULTS, "board_gap_px", _DEFAULTS.board_gap_px)),
        unit_scale,
        min_px=14,
    )
    board_padding = scale_games_px(
        params.get("board_padding_px", group_default(_RENDER_DEFAULTS, "board_padding_px", _DEFAULTS.board_padding_px)),
        unit_scale,
        min_px=9,
    )
    board_label_height = scale_games_px(
        params.get(
            "board_label_height_px",
            group_default(_RENDER_DEFAULTS, "board_label_height_px", _DEFAULTS.board_label_height_px),
        ),
        unit_scale,
        min_px=27,
    )
    cols, rows = _board_grid_dimensions(int(axes.board_count))
    board_panel_w = (int(axes.board_size) * int(cell_size)) + (2 * int(board_padding))
    board_panel_h = int(board_label_height) + (int(axes.board_size) * int(cell_size)) + int(board_padding)
    content_w = (int(cols) * int(board_panel_w)) + ((int(cols) - 1) * int(board_gap))
    content_h = (int(rows) * int(board_panel_h)) + ((int(rows) - 1) * int(board_gap))
    content_margin = int(group_default(_RENDER_DEFAULTS, "content_margin_px", _DEFAULTS.content_margin_px))
    canvas_width = int(params.get("canvas_width", max(_DEFAULTS.canvas_width, content_w + (2 * content_margin))))
    canvas_height = int(params.get("canvas_height", max(_DEFAULTS.canvas_height, content_h + (2 * content_margin))))
    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace="games.rule_override_board.font_family",
        params=params,
    )
    return _RenderParams(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        cell_size_px=int(cell_size),
        board_gap_px=int(board_gap),
        board_padding_px=int(board_padding),
        board_label_height_px=int(board_label_height),
        content_margin_px=int(content_margin),
        panel_radius_px=scale_games_px(
            params.get("panel_radius_px", group_default(_RENDER_DEFAULTS, "panel_radius_px", _DEFAULTS.panel_radius_px)),
            unit_scale,
            min_px=8,
        ),
        panel_border_width_px=scale_games_px(
            params.get(
                "panel_border_width_px",
                group_default(_RENDER_DEFAULTS, "panel_border_width_px", _DEFAULTS.panel_border_width_px),
            ),
            unit_scale,
            min_px=1,
        ),
        board_border_width_px=scale_games_px(
            params.get(
                "board_border_width_px",
                group_default(_RENDER_DEFAULTS, "board_border_width_px", _DEFAULTS.board_border_width_px),
            ),
            unit_scale,
            min_px=2,
        ),
        grid_width_px=scale_games_px(
            params.get("grid_width_px", group_default(_RENDER_DEFAULTS, "grid_width_px", _DEFAULTS.grid_width_px)),
            unit_scale,
            min_px=1,
        ),
        board_label_font_size_px=scale_games_px(
            params.get(
                "board_label_font_size_px",
                group_default(_RENDER_DEFAULTS, "board_label_font_size_px", _DEFAULTS.board_label_font_size_px),
            ),
            unit_scale,
            min_px=15,
        ),
        mark_font_size_px=scale_games_px(
            params.get("mark_font_size_px", group_default(_RENDER_DEFAULTS, "mark_font_size_px", _DEFAULTS.mark_font_size_px)),
            unit_scale,
            min_px=23,
        ),
        font_family=str(font_family),
        layout_jitter_meta=dict(layout_jitter),
        unit_size_meta=dict(unit_scale_meta),
    )


def _has_line(cells: Sequence[Sequence[str]], player: str) -> bool:
    size = len(cells)
    target = str(player)
    for row in cells:
        if all(str(value) == target for value in row):
            return True
    for col in range(size):
        if all(str(cells[row][col]) == target for row in range(size)):
            return True
    if all(str(cells[index][index]) == target for index in range(size)):
        return True
    if all(str(cells[index][size - 1 - index]) == target for index in range(size)):
        return True
    return False


def _line_cells_with_condition(*, rng, size: int, target_player: str, has_target_line: bool) -> Tuple[Tuple[str, ...], ...]:
    """Sample an X/O board with or without a full target-player line."""

    target = str(target_player)
    other = _opponent(target)
    if bool(has_target_line):
        cells = [["" for _ in range(int(size))] for _ in range(int(size))]
        line_type = str(rng.choice(("row", "col", "diag_down", "diag_up")))
        line_index = int(rng.randrange(0, int(size)))
        for index in range(int(size)):
            if line_type == "row":
                cells[line_index][index] = target
            elif line_type == "col":
                cells[index][line_index] = target
            elif line_type == "diag_down":
                cells[index][index] = target
            else:
                cells[index][int(size) - 1 - index] = target
        for row in range(int(size)):
            for col in range(int(size)):
                if cells[row][col]:
                    continue
                cells[row][col] = str(rng.choices(("", target, other), weights=(0.30, 0.18, 0.52), k=1)[0])
        return tuple(tuple(value for value in row) for row in cells)

    for _attempt in range(500):
        cells = []
        for _row in range(int(size)):
            cells.append(
                tuple(
                    str(rng.choices(("", target, other), weights=(0.35, 0.22, 0.43), k=1)[0])
                    for _col in range(int(size))
                )
            )
        if not _has_line(cells, target):
            return tuple(cells)
    raise ValueError("failed to sample line board without target line")


def _piece_cells_with_condition(*, rng, size: int, target_player: str, target_has_fewer: bool) -> Tuple[Tuple[str, ...], ...]:
    """Sample a token board where the target player has fewer or more pieces."""

    target = str(target_player)
    other = _opponent(target)
    total_cells = int(size) * int(size)
    if bool(target_has_fewer):
        target_count = int(rng.randrange(2, max(3, min(7, total_cells // 2))))
        other_count = int(rng.randrange(target_count + 1, min(total_cells - target_count, target_count + 6) + 1))
    else:
        other_count = int(rng.randrange(2, max(3, min(7, total_cells // 2))))
        target_count = int(rng.randrange(other_count + 1, min(total_cells - other_count, other_count + 6) + 1))
    positions = [(row, col) for row in range(int(size)) for col in range(int(size))]
    rng.shuffle(positions)
    cells = [["" for _ in range(int(size))] for _ in range(int(size))]
    for row, col in positions[:target_count]:
        cells[int(row)][int(col)] = target
    for row, col in positions[target_count : target_count + other_count]:
        cells[int(row)][int(col)] = other
    return tuple(tuple(value for value in row) for row in cells)


def _sample_scene(*, rng, axes: _ResolvedAxes, prompt_defaults: Mapping[str, Any]) -> _SceneSample:
    """Sample one complete scene with exact target answer cardinality."""

    board_count = int(axes.board_count)
    target_answer = int(axes.target_answer)
    counted_flags = [True] * int(target_answer) + [False] * int(board_count - target_answer)
    rng.shuffle(counted_flags)
    is_win_query = _query_is_win(str(axes.query_id))
    boards: list[_BoardPanel] = []
    evidence_ids: list[str] = []
    for index, counted in enumerate(counted_flags):
        board_id = f"board_{int(index) + 1:02d}"
        label = f"Board {int(index) + 1}"
        if str(axes.board_family) == "line":
            target_has_line = (not bool(counted)) if bool(is_win_query) else bool(counted)
            cells = _line_cells_with_condition(
                rng=rng,
                size=int(axes.board_size),
                target_player=str(axes.target_player),
                has_target_line=bool(target_has_line),
            )
            result = "loss" if bool(target_has_line) else "win"
            target_stat = 1 if bool(target_has_line) else 0
            opponent_stat = 1 if _has_line(cells, _opponent(str(axes.target_player))) else 0
        else:
            target_has_fewer = bool(counted) if bool(is_win_query) else not bool(counted)
            cells = _piece_cells_with_condition(
                rng=rng,
                size=int(axes.board_size),
                target_player=str(axes.target_player),
                target_has_fewer=bool(target_has_fewer),
            )
            flat = [value for row in cells for value in row]
            target_stat = sum(1 for value in flat if str(value) == str(axes.target_player))
            opponent_stat = sum(1 for value in flat if str(value) == _opponent(str(axes.target_player)))
            result = "win" if int(target_stat) < int(opponent_stat) else "loss"
        if bool(counted):
            evidence_ids.append(board_id)
        boards.append(
            _BoardPanel(
                board_id=str(board_id),
                label=str(label),
                cells=tuple(tuple(str(value) for value in row) for row in cells),
                counted=bool(counted),
                result=str(result),
                target_player=str(axes.target_player),
                target_stat=int(target_stat),
                opponent_stat=int(opponent_stat),
            )
        )
    rule_text_key = "line_rule_text" if str(axes.board_family) == "line" else "piece_rule_text"
    sample = _SceneSample(
        board_family=str(axes.board_family),
        query_id=str(axes.query_id),
        board_style=str(axes.board_style),
        target_player=str(axes.target_player),
        board_size=int(axes.board_size),
        answer=int(target_answer),
        rule_text=str(prompt_defaults[rule_text_key]),
        boards=tuple(boards),
        evidence_entity_ids=tuple(evidence_ids),
    )
    actual_answer = sum(1 for board in sample.boards if bool(board.counted))
    if int(actual_answer) != int(target_answer):
        raise ValueError("sampled answer does not match requested target answer")
    return sample


def _theme(style_name: str) -> Dict[str, Tuple[int, int, int]]:
    """Return local board colors for one nonsemantic board style."""

    themes = {
        "classic": {
            "panel": (244, 239, 223),
            "grid": (45, 49, 58),
            "cell_a": (250, 247, 238),
            "cell_b": (231, 224, 205),
            "x": (45, 91, 188),
            "o": (201, 67, 70),
            "black": (36, 39, 48),
            "white": (244, 245, 238),
            "accent": (80, 118, 88),
        },
        "paper": {
            "panel": (248, 250, 244),
            "grid": (86, 94, 105),
            "cell_a": (255, 255, 250),
            "cell_b": (235, 241, 246),
            "x": (35, 82, 121),
            "o": (140, 55, 92),
            "black": (50, 54, 60),
            "white": (249, 250, 244),
            "accent": (106, 133, 167),
        },
        "chalkboard": {
            "panel": (35, 67, 55),
            "grid": (219, 236, 219),
            "cell_a": (44, 83, 68),
            "cell_b": (40, 75, 62),
            "x": (243, 230, 118),
            "o": (248, 182, 143),
            "black": (24, 31, 30),
            "white": (232, 235, 218),
            "accent": (231, 237, 198),
        },
        "arcade": {
            "panel": (24, 30, 56),
            "grid": (87, 219, 237),
            "cell_a": (31, 39, 72),
            "cell_b": (39, 48, 87),
            "x": (255, 95, 158),
            "o": (93, 232, 155),
            "black": (20, 22, 36),
            "white": (232, 246, 255),
            "accent": (252, 220, 88),
        },
        "wood": {
            "panel": (168, 116, 74),
            "grid": (79, 50, 36),
            "cell_a": (218, 170, 107),
            "cell_b": (188, 132, 82),
            "x": (44, 74, 127),
            "o": (126, 38, 45),
            "black": (34, 29, 25),
            "white": (245, 232, 198),
            "accent": (91, 62, 42),
        },
    }
    return dict(themes.get(str(style_name), themes["classic"]))


def _draw_line_board(
    draw: ImageDraw.ImageDraw,
    *,
    board: _BoardPanel,
    grid_bbox: Tuple[int, int, int, int],
    cell_size: int,
    grid_width: int,
    colors: Mapping[str, Tuple[int, int, int]],
    font_family: str,
    mark_font_size: int,
) -> None:
    size = len(board.cells)
    mark_font = fit_font_to_box(
        draw,
        text="X",
        max_width=float(cell_size),
        max_height=float(cell_size),
        bold=True,
        font_family=font_family,
        min_size_px=max(12, int(mark_font_size) // 2),
        max_size_px=int(mark_font_size),
        fill_ratio=0.74,
    )
    for row in range(size):
        for col in range(size):
            x0 = int(grid_bbox[0] + (col * int(cell_size)))
            y0 = int(grid_bbox[1] + (row * int(cell_size)))
            x1 = int(x0 + int(cell_size))
            y1 = int(y0 + int(cell_size))
            fill = colors["cell_a"] if (row + col) % 2 == 0 else colors["cell_b"]
            draw.rectangle((x0, y0, x1, y1), fill=fill)
            value = str(board.cells[row][col])
            if value:
                color = colors["x"] if value == "X" else colors["o"]
                draw_centered_traced_text(
                    draw,
                    center=((x0 + x1) / 2.0, (y0 + y1) / 2.0),
                    text=value,
                    font=mark_font,
                    fill_rgb=color,
                    stroke_rgb=colors["panel"],
                    stroke_width=1,
                    role="board_mark",
                    required=False,
                    extra_metadata={"board_id": str(board.board_id), "cell": [int(row), int(col)]},
                )
    for index in range(size + 1):
        x = int(grid_bbox[0] + (index * int(cell_size)))
        y = int(grid_bbox[1] + (index * int(cell_size)))
        draw.line((x, grid_bbox[1], x, grid_bbox[3]), fill=colors["grid"], width=int(grid_width))
        draw.line((grid_bbox[0], y, grid_bbox[2], y), fill=colors["grid"], width=int(grid_width))


def _draw_piece_board(
    draw: ImageDraw.ImageDraw,
    *,
    board: _BoardPanel,
    grid_bbox: Tuple[int, int, int, int],
    cell_size: int,
    grid_width: int,
    colors: Mapping[str, Tuple[int, int, int]],
) -> None:
    size = len(board.cells)
    for row in range(size):
        for col in range(size):
            x0 = int(grid_bbox[0] + (col * int(cell_size)))
            y0 = int(grid_bbox[1] + (row * int(cell_size)))
            x1 = int(x0 + int(cell_size))
            y1 = int(y0 + int(cell_size))
            fill = colors["cell_a"] if (row + col) % 2 == 0 else colors["cell_b"]
            draw.rectangle((x0, y0, x1, y1), fill=fill)
            value = str(board.cells[row][col])
            if value:
                inset = max(5, int(round(float(cell_size) * 0.18)))
                piece_bbox = (x0 + inset, y0 + inset, x1 - inset, y1 - inset)
                piece_fill = colors["black"] if value == "Black" else colors["white"]
                piece_outline = colors["white"] if value == "Black" else colors["black"]
                draw.ellipse(piece_bbox, fill=piece_fill, outline=piece_outline, width=max(2, int(grid_width)))
    for index in range(size + 1):
        x = int(grid_bbox[0] + (index * int(cell_size)))
        y = int(grid_bbox[1] + (index * int(cell_size)))
        draw.line((x, grid_bbox[1], x, grid_bbox[3]), fill=colors["grid"], width=int(grid_width))
        draw.line((grid_bbox[0], y, grid_bbox[2], y), fill=colors["grid"], width=int(grid_width))


def _render_scene(
    *,
    sample: _SceneSample,
    params: _RenderParams,
    panel_style: Any,
    background: Image.Image,
) -> _RenderedScene:
    """Render one complete rule-override board scene."""

    image = background.copy()
    draw = ImageDraw.Draw(image)
    colors = _theme(str(sample.board_style))
    cols, rows = _board_grid_dimensions(len(sample.boards))
    board_panel_w = (int(sample.board_size) * int(params.cell_size_px)) + (2 * int(params.board_padding_px))
    board_panel_h = int(params.board_label_height_px) + (int(sample.board_size) * int(params.cell_size_px)) + int(params.board_padding_px)
    content_w = (cols * board_panel_w) + ((cols - 1) * int(params.board_gap_px))
    content_h = (rows * board_panel_h) + ((rows - 1) * int(params.board_gap_px))
    natural_bbox = (
        int(params.content_margin_px),
        int(params.content_margin_px),
        int(params.content_margin_px + content_w),
        int(params.content_margin_px + content_h),
    )
    content_bbox, dx, dy, jitter_meta = apply_games_layout_jitter_to_bbox(
        bbox_px=natural_bbox,
        canvas_width=int(params.canvas_width),
        canvas_height=int(params.canvas_height),
        jitter=params.layout_jitter_meta,
    )
    content_bbox_i = tuple(int(round(value)) for value in content_bbox)
    outer_bbox = (
        content_bbox_i[0] - 18,
        content_bbox_i[1] - 18,
        content_bbox_i[2] + 18,
        content_bbox_i[3] + 18,
    )
    draw_panel_scene_chrome(
        draw,
        bbox=outer_bbox,
        style=panel_style,
        radius=int(params.panel_radius_px),
        border_width=int(params.panel_border_width_px),
    )
    entity_bboxes: dict[str, list[float]] = {}
    entities: list[dict[str, Any]] = []
    label_font = load_font(int(params.board_label_font_size_px), bold=True, font_family=str(params.font_family))
    grid_top0 = int(content_bbox_i[1])
    for index, board in enumerate(sample.boards):
        row = index // cols
        col = index % cols
        row_item_count = min(int(cols), max(0, len(sample.boards) - (int(row) * int(cols))))
        row_width = (int(row_item_count) * int(board_panel_w)) + ((int(row_item_count) - 1) * int(params.board_gap_px))
        row_offset = int(round((float(content_w) - float(row_width)) / 2.0))
        left = int(content_bbox_i[0] + row_offset + (col * (board_panel_w + int(params.board_gap_px))))
        top = int(grid_top0 + (row * (board_panel_h + int(params.board_gap_px))))
        panel_bbox = (left, top, left + board_panel_w, top + board_panel_h)
        draw.rounded_rectangle(
            panel_bbox,
            radius=12,
            fill=colors["panel"],
            outline=colors["accent"],
            width=int(params.board_border_width_px),
        )
        draw_centered_traced_text(
            draw,
            center=((panel_bbox[0] + panel_bbox[2]) / 2.0, panel_bbox[1] + (int(params.board_label_height_px) / 2.0)),
            text=str(board.label),
            font=label_font,
            fill_rgb=colors["grid"],
            stroke_rgb=colors["panel"],
            stroke_width=1,
            role="mini_board_label",
            required=False,
            extra_metadata={"board_id": str(board.board_id)},
        )
        grid_bbox = (
            int(left + int(params.board_padding_px)),
            int(top + int(params.board_label_height_px)),
            int(left + int(params.board_padding_px) + (int(sample.board_size) * int(params.cell_size_px))),
            int(top + int(params.board_label_height_px) + (int(sample.board_size) * int(params.cell_size_px))),
        )
        if str(sample.board_family) == "line":
            _draw_line_board(
                draw,
                board=board,
                grid_bbox=grid_bbox,
                cell_size=int(params.cell_size_px),
                grid_width=int(params.grid_width_px),
                colors=colors,
                font_family=str(params.font_family),
                mark_font_size=int(params.mark_font_size_px),
            )
        else:
            _draw_piece_board(
                draw,
                board=board,
                grid_bbox=grid_bbox,
                cell_size=int(params.cell_size_px),
                grid_width=int(params.grid_width_px),
                colors=colors,
            )
        entity_bboxes[str(board.board_id)] = [float(value) for value in panel_bbox]
        entities.append(
            {
                "entity_id": str(board.board_id),
                "entity_type": "mini_board",
                "label": str(board.label),
                "bbox_px": [float(value) for value in panel_bbox],
                "grid_bbox_px": [float(value) for value in grid_bbox],
                "counted": bool(board.counted),
                "result": str(board.result),
            }
        )
    return _RenderedScene(
        image=image,
        render_map={
            "entity_bboxes_px": entity_bboxes,
            "layout_jitter": {
                **dict(jitter_meta),
                "dx_px": round(float(dx), 3),
                "dy_px": round(float(dy), 3),
                "unit_size_jitter": dict(params.unit_size_meta),
            },
            "board_style": str(sample.board_style),
            "text_style": {"font_family": str(params.font_family)},
        },
        scene_entities=tuple(entities),
    )


def _build_json_examples() -> Tuple[str, str]:
    evidence = [[80, 170, 258, 378], [286, 170, 464, 378], [492, 170, 670, 378]]
    answer = 3
    return (
        json.dumps({"evidence": evidence, "answer": answer}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer}, separators=(",", ":"), ensure_ascii=False),
    )


def _build_complexity(*, task_id: str, sample: _SceneSample) -> TaskComplexity:
    weights = resolve_games_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=str(task_id))
    board_count = len(sample.boards)
    board_size = int(sample.board_size)
    visual_scan = (
        0.55 * normalize_linear(float(board_count), min_value=4.0, max_value=8.0)
        + 0.45 * normalize_linear(float(board_size * board_size), min_value=9.0, max_value=25.0)
    )
    rule_reasoning = 0.62 if str(sample.board_family) == "line" else 0.54
    output_burden = normalize_linear(float(sample.answer), min_value=1.0, max_value=6.0)
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "rule_override_reasoning": float(rule_reasoning),
            "output_burden": float(output_burden),
        },
    )


class GamesRuleOverrideBoardTask:
    """Base generator for rule-override mini-board count tasks."""

    task_id = BASE_TASK_ID
    domain = "games"
    task_group = TASK_GROUP
    board_family = "line"
    supported_query_ids: Tuple[str, ...] = SUPPORTED_LINE_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description_rule_override_board",
                "line_rule_text",
                "piece_rule_text",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        axes = _resolve_axes(
            instance_seed=int(instance_seed),
            params=params,
            task_id=str(self.task_id),
            board_family=str(self.board_family),
            supported_query_ids=tuple(self.supported_query_ids),
        )
        sampled_scene: _SceneSample | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"{self.task_id}.attempt.{int(attempt_index)}")
            try:
                sampled_scene = _sample_scene(rng=rng, axes=axes, prompt_defaults=prompt_defaults)
            except ValueError:
                continue
            break
        if sampled_scene is None:
            raise RuntimeError(f"{self.task_id} failed to generate after {max_attempts} attempts")

        render_params = _resolve_render_params(instance_seed=int(instance_seed), params=params, axes=axes)
        panel_style, panel_style_meta = resolve_game_panel_scene_style(
            instance_seed=int(instance_seed),
            namespace="games.rule_override_board.panel_scene",
            treatment_weights=group_default(_GEN_DEFAULTS, "panel_treatment_weights", {}),
            palette_weights=group_default(_GEN_DEFAULTS, "panel_palette_weights", {}),
        )
        background, background_meta = make_panel_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=panel_style,
        )
        rendered = _render_scene(
            sample=sampled_scene,
            params=render_params,
            panel_style=panel_style,
            background=background,
        )
        evidence_bboxes = [
            list(rendered.render_map["entity_bboxes_px"][str(entity_id)])
            for entity_id in sampled_scene.evidence_entity_ids
        ]
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        answer_hint_key = f"answer_hint_{str(sampled_scene.query_id)}"
        evidence_hint_key = f"evidence_hint_{str(sampled_scene.query_id)}"
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description_rule_override_board",
                answer_hint_key,
                evidence_hint_key,
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_json_examples()
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(sampled_scene.query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_rule_override_board"]),
                "target_player": str(sampled_scene.target_player),
                "rule_text": str(sampled_scene.rule_text),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[answer_hint_key]),
                "evidence_hint": str(prompt_defaults[evidence_hint_key]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        board_trace = [
            {
                "board_id": str(board.board_id),
                "label": str(board.label),
                "cells": [list(row) for row in board.cells],
                "counted": bool(board.counted),
                "result_for_target_player": str(board.result),
                "target_stat": int(board.target_stat),
                "opponent_stat": int(board.opponent_stat),
            }
            for board in sampled_scene.boards
        ]
        answer_gt = TypedValue(type="integer", value=int(sampled_scene.answer))
        evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in evidence_bboxes])
        trace_payload = {
            "scene_ir": {
                "scene_kind": "games_rule_override_board",
                "entities": [dict(entity) for entity in rendered.scene_entities],
                "relations": {
                    "query_id": str(sampled_scene.query_id),
                    "board_family": str(sampled_scene.board_family),
                    "board_style": str(sampled_scene.board_style),
                    "target_player": str(sampled_scene.target_player),
                    "rule_text": str(sampled_scene.rule_text),
                    "evidence_entity_ids": [str(entity_id) for entity_id in sampled_scene.evidence_entity_ids],
                },
            },
            "query_spec": {
                "query_id": str(sampled_scene.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(sampled_scene.query_id),
                    "board_family": str(sampled_scene.board_family),
                    "board_style": str(sampled_scene.board_style),
                    "target_player": str(sampled_scene.target_player),
                    "board_count": int(len(sampled_scene.boards)),
                    "board_size": int(sampled_scene.board_size),
                    "target_answer": int(sampled_scene.answer),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "board_style_probabilities": dict(axes.board_style_probabilities),
                    "target_player_probabilities": dict(axes.target_player_probabilities),
                    "board_count_probabilities": dict(axes.board_count_probabilities),
                    "board_size_probabilities": dict(axes.board_size_probabilities),
                    "target_answer_probabilities": dict(axes.target_answer_probabilities),
                },
            },
            "render_spec": {
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "board_style": str(sampled_scene.board_style),
                "layout_jitter": dict(rendered.render_map.get("layout_jitter", {})),
                "panel_scene_style": dict(panel_style_meta),
                "text_style": dict(rendered.render_map.get("text_style", {})),
                "font_asset": get_font_family_record(str(render_params.font_family)).to_trace(),
            },
            "render_map": dict(rendered.render_map),
            "execution_trace": {
                "query_id": str(sampled_scene.query_id),
                "board_family": str(sampled_scene.board_family),
                "board_style": str(sampled_scene.board_style),
                "target_player": str(sampled_scene.target_player),
                "opponent_player": _opponent(str(sampled_scene.target_player)),
                "rule_text": str(sampled_scene.rule_text),
                "answer": int(sampled_scene.answer),
                "boards": board_trace,
                "evidence_entity_ids": [str(entity_id) for entity_id in sampled_scene.evidence_entity_ids],
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(entity_id) for entity_id in sampled_scene.evidence_entity_ids],
            },
            "projected_evidence": {
                "bbox_set": [list(bbox) for bbox in evidence_bboxes],
            },
            "background": background_meta,
            "panel_scene_style": dict(panel_style_meta),
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
            complexity=_build_complexity(task_id=str(self.task_id), sample=sampled_scene),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(sampled_scene.query_id),
        )


@register_task
class GamesRuleOverrideLineResultCountTask(GamesRuleOverrideBoardTask):
    """Count line-rule wins or losses under an explicit anti-line rule."""

    task_id = "task_games__rule_override_board__line_result_count"
    board_family = "line"
    supported_query_ids = SUPPORTED_LINE_QUERY_IDS


@register_task
class GamesRuleOverridePieceResultCountTask(GamesRuleOverrideBoardTask):
    """Count piece-count wins or losses under an explicit fewer-pieces rule."""

    task_id = "task_games__rule_override_board__piece_result_count"
    board_family = "piece"
    supported_query_ids = SUPPORTED_PIECE_QUERY_IDS


__all__ = [
    "GamesRuleOverrideBoardTask",
    "GamesRuleOverrideLineResultCountTask",
    "GamesRuleOverridePieceResultCountTask",
    "LINE_LOSS_QUERY_ID",
    "LINE_WIN_QUERY_ID",
    "PIECE_LOSS_QUERY_ID",
    "PIECE_WIN_QUERY_ID",
]
