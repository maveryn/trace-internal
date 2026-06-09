"""Agent misc automaton tasks."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import hash64, spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults
from ...shared.color_distance import color_distance
from ...shared.drawing import draw_arrow, draw_centered_text, draw_rounded_rect
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.font_assets import font_asset_version, sample_font_family
from ...shared.mcq import option_label_for_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_legibility import contrast_ratio
from ...shared.text_rendering import load_font, temporary_default_font_family
from ..shared.common import (
    get_int_param as _get_int,
    get_int_range as _get_range,
    load_misc_task_defaults,
    projected_misc_bbox_annotation,
    projected_misc_keyed_bbox_annotation,
    resolve_misc_axis_variant,
)
from ..shared.complexity import build_misc_complexity, normalize_int_with_bounds
from ..shared.scene_style import (
    DEFAULT_MISC_SCENE_STYLE,
    MISC_SCENE_TREATMENTS,
    MiscSceneStyle,
    draw_misc_chrome_by_mode,
    draw_misc_grid_cell,
    draw_misc_option_card,
    make_misc_scene_background,
    resolve_panel_chrome_mode,
    resolve_misc_scene_style,
)
from ..shared.unit_size_jitter import resolve_misc_unit_size_scale, scale_misc_px, with_misc_unit_size_jitter
from ..shared.visual_defaults import load_misc_background_defaults, load_misc_noise_defaults


from .shared import (
    AGENT_FINAL_TASK_ID,
    AGENT_FLIP_TASK_ID,
    AGENT_SCENE_ID,
    AGENT_FINAL_QUERY_IDS,
    AGENT_FLIP_QUERY_IDS,
    _DIRECTIONS,
    _DIR_VEC,
    _AGENT_RGB,
    _AGENT_BOARD_STYLES,
    POST_IMAGE_NOISE_DEFAULTS,
    _RenderParams,
    _RenderedScene,
    _load_defaults,
    _resolve_render_params,
    _style_meta_with_font,
    _resolve_agent_style,
    _resolve_axis,
    _resolve_query,
    _decorrelated_selection_index,
    _sample_grid,
    _rect_cells,
    _grid_bbox,
    _cell_bbox,
    _draw_cell_grid,
    _draw_option_card,
    _mark_region_bbox,
    _decorate_panel,
    _build_prompt,
    _common_trace,
    _round_bboxes,
    _round_keyed_bboxes,
    _BaseAutomatonTask,
)


@dataclass(frozen=True)
class _AgentTrace:
    step: int
    row: int
    col: int
    direction: int
    state_before: int
    state_after: int


@dataclass(frozen=True)
class _AgentDataset:
    rows: int
    cols: int
    state_count: int
    rule_variant: str
    query_id: str
    steps: int
    initial_grid: Tuple[Tuple[int, ...], ...]
    start_row: int
    start_col: int
    start_direction: int
    final_grid: Tuple[Tuple[int, ...], ...]
    final_row: int
    final_col: int
    final_direction: int
    traces: Tuple[_AgentTrace, ...]
    option_specs: Tuple[Dict[str, Any], ...]
    answer_label: str
    target_cells: Tuple[Tuple[int, int], ...]
    target_state: int | None
    flip_count: int


def _resolve_agent_board_style(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    return _resolve_axis(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        task_id=str(task_id),
        supported_variants=_AGENT_BOARD_STYLES,
        explicit_key="agent_board_style",
        weights_key="agent_board_style_weights",
        balance_flag_key="balanced_agent_board_style_sampling",
        axis_namespace="agent_board_style",
    )


def _style_meta_with_agent_board(
    style_meta: Mapping[str, Any],
    *,
    board_style: str,
    board_style_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    return {
        **dict(style_meta),
        "agent_board": {
            "board_style": str(board_style),
            "board_style_probabilities": {str(key): float(value) for key, value in board_style_probabilities.items()},
            "semantic_color_policy": {
                "state_colors_preserved_from_scene_style": True,
                "same_board_style_for_source_and_options": True,
            },
        },
    }


def _agent_option_vertical_gap(render_params: _RenderParams) -> int:
    unit_scale = float(render_params.unit_size_jitter.get("scale", 1.0))
    return scale_misc_px(58, unit_scale, min_px=34)


def _agent_content_metrics(
    *,
    dataset: _AgentDataset,
    render_params: _RenderParams,
) -> Dict[str, int]:
    rows, cols = int(dataset.rows), int(dataset.cols)
    cell = int(render_params.cell_size_px)
    gap = int(render_params.grid_gap_px)
    grid_bbox = _grid_bbox(left=0, top=0, rows=rows, cols=cols, cell_size=cell, gap=gap)
    grid_w = int(grid_bbox[2] - grid_bbox[0])
    grid_h = int(grid_bbox[3] - grid_bbox[1])
    panel_w = int(grid_w + 2 * int(render_params.panel_padding_px))
    panel_h = int(grid_h + 2 * int(render_params.panel_padding_px))
    option_w = 0
    option_h = 0
    option_gap_y = 0
    if dataset.option_specs:
        card_w = int(render_params.option_card_width_px)
        card_h = int(render_params.option_card_height_px)
        gap_x = int(render_params.option_gap_px)
        option_w = int(len(dataset.option_specs) * card_w + max(0, len(dataset.option_specs) - 1) * gap_x)
        option_h = int(card_h)
        option_gap_y = int(_agent_option_vertical_gap(render_params))
    content_w = int(max(panel_w, option_w))
    content_h = int(panel_h + (option_gap_y + option_h if option_h else 0))
    return {
        "grid_width_px": grid_w,
        "grid_height_px": grid_h,
        "panel_width_px": panel_w,
        "panel_height_px": panel_h,
        "option_width_px": option_w,
        "option_height_px": option_h,
        "option_vertical_gap_px": option_gap_y,
        "content_width_px": content_w,
        "content_height_px": content_h,
    }


def _fit_agent_render_params(
    *,
    dataset: _AgentDataset,
    render_params: _RenderParams,
) -> _RenderParams:
    metrics = _agent_content_metrics(dataset=dataset, render_params=render_params)
    rng = spawn_rng(instance_seed=int(render_params.layout_seed), namespace="agent_automaton_canvas")
    min_margin = max(28, int(round(render_params.panel_padding_px * 1.15)))
    max_margin = max(min_margin, int(round(render_params.panel_padding_px * 2.45)))
    left_margin = rng.randint(min_margin, max_margin)
    right_margin = rng.randint(min_margin, max_margin)
    top_margin = rng.randint(min_margin, max_margin)
    bottom_margin = rng.randint(min_margin, max_margin)
    min_canvas_w = 520 if dataset.option_specs else 420
    min_canvas_h = 420 if dataset.option_specs else 360
    target_w = int(metrics["content_width_px"] + left_margin + right_margin)
    target_h = int(metrics["content_height_px"] + top_margin + bottom_margin)
    canvas_w = min(int(render_params.canvas_width), max(int(min_canvas_w), target_w))
    canvas_h = min(int(render_params.canvas_height), max(int(min_canvas_h), target_h))
    return replace(render_params, canvas_width=int(canvas_w), canvas_height=int(canvas_h))


def _turn_offsets(rule_variant: str) -> Tuple[int, ...]:
    if str(rule_variant) == "three_state_rule":
        return (1, 0, -1)
    return (1, -1)


def _rule_variant_from_query(query_id: str) -> str:
    return "three_state_rule" if "three_state" in str(query_id) else "binary_rule"


def _simulate_agent(
    grid: Sequence[Sequence[int]],
    *,
    start_row: int,
    start_col: int,
    start_direction: int,
    steps: int,
    turn_offsets: Sequence[int],
) -> Tuple[Tuple[Tuple[int, ...], ...], int, int, int, Tuple[_AgentTrace, ...]]:
    state_count = len(turn_offsets)
    rows = len(grid)
    cols = len(grid[0])
    current = [list(row) for row in grid]
    row = int(start_row)
    col = int(start_col)
    direction = int(start_direction)
    traces: List[_AgentTrace] = []
    for step in range(1, int(steps) + 1):
        state_before = int(current[row][col])
        direction = int((direction + int(turn_offsets[state_before])) % 4)
        state_after = int((state_before + 1) % state_count)
        current[row][col] = state_after
        traces.append(
            _AgentTrace(
                step=int(step),
                row=int(row),
                col=int(col),
                direction=int(direction),
                state_before=int(state_before),
                state_after=int(state_after),
            )
        )
        dr, dc = _DIR_VEC[direction]
        row = int((row + dr) % rows)
        col = int((col + dc) % cols)
    return tuple(tuple(int(value) for value in row_values) for row_values in current), row, col, direction, tuple(traces)


def _option_pose_text(row: int, col: int, direction: int) -> str:
    return f"r{int(row) + 1}, c{int(col) + 1}, {_DIRECTIONS[int(direction)]}"


def _state_label(*, state: int, state_count: int) -> str:
    if int(state_count) == 2:
        return "light" if int(state) == 0 else "colored state"
    return f"state {int(state)}"


def _build_pose_options(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
    rows: int,
    cols: int,
    final_row: int,
    final_col: int,
    final_direction: int,
    option_count: int,
    rng,
) -> Tuple[Tuple[Dict[str, Any], ...], str]:
    correct = (int(final_row), int(final_col), int(final_direction))
    options = {correct}
    while len(options) < int(option_count):
        kind = int(rng.randrange(4))
        if kind == 0:
            candidate = (int((final_row + rng.choice([-2, -1, 1, 2])) % rows), int(final_col), int(final_direction))
        elif kind == 1:
            candidate = (int(final_row), int((final_col + rng.choice([-2, -1, 1, 2])) % cols), int(final_direction))
        elif kind == 2:
            candidate = (int(final_row), int(final_col), int((final_direction + rng.choice([1, 2, 3])) % 4))
        else:
            candidate = (int(rng.randrange(rows)), int(rng.randrange(cols)), int(rng.randrange(4)))
        options.add(candidate)
    distractors = [option for option in options if option != correct]
    rng.shuffle(distractors)
    correct_index = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))) % int(option_count)
    ordered: List[Tuple[int, int, int]] = []
    for index in range(int(option_count)):
        if index == correct_index:
            ordered.append(correct)
        else:
            ordered.append(distractors.pop())
    specs: List[Dict[str, Any]] = []
    answer_label = "A"
    for index, (row, col, direction) in enumerate(ordered):
        label = option_label_for_index(index)
        if (row, col, direction) == correct:
            answer_label = str(label)
        specs.append(
            {
                "option_id": f"option_{label}",
                "label": str(label),
                "row": int(row),
                "col": int(col),
                "direction": int(direction),
                "pose_text": _option_pose_text(row, col, direction),
                "is_correct": bool((row, col, direction) == correct),
            }
        )
    return tuple(specs), str(answer_label)


def _agent_visit_counts(traces: Sequence[_AgentTrace]) -> Dict[Tuple[int, int], int]:
    counts: Dict[Tuple[int, int], int] = {}
    for trace in traces:
        key = (int(trace.row), int(trace.col))
        counts[key] = int(counts.get(key, 0)) + 1
    return counts


def _build_agent_dataset(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    query_id: str,
    rule_variant: str | None = None,
) -> _AgentDataset:
    rng = spawn_rng(int(instance_seed), f"{task_id}.agent")
    rows_min, rows_max = _get_range(params, gen_defaults, min_key="agent_rows_min", max_key="agent_rows_max", fallback_min=6, fallback_max=9)
    cols_min, cols_max = _get_range(params, gen_defaults, min_key="agent_cols_min", max_key="agent_cols_max", fallback_min=6, fallback_max=9)
    steps_min, steps_max = _get_range(params, gen_defaults, min_key="agent_steps_min", max_key="agent_steps_max", fallback_min=5, fallback_max=14)
    rows = int(rng.randint(rows_min, rows_max))
    cols = int(rng.randint(cols_min, cols_max))
    steps = int(params.get("steps", rng.randint(steps_min, steps_max)))
    resolved_rule_variant = str(rule_variant or _rule_variant_from_query(str(query_id)))
    state_count = 3 if resolved_rule_variant == "three_state_rule" else 2
    grid = _sample_grid(rng, rows=rows, cols=cols, state_count=state_count, live_prob=0.38)
    start_row = int(rng.randrange(rows))
    start_col = int(rng.randrange(cols))
    start_direction = int(rng.randrange(4))
    final_grid, final_row, final_col, final_direction, traces = _simulate_agent(
        grid,
        start_row=start_row,
        start_col=start_col,
        start_direction=start_direction,
        steps=steps,
        turn_offsets=_turn_offsets(resolved_rule_variant),
    )
    option_specs: Tuple[Dict[str, Any], ...] = tuple()
    answer_label = ""
    target_cells: Tuple[Tuple[int, int], ...] = tuple()
    target_state: int | None = None
    flip_count = 0
    if str(task_id) == AGENT_FINAL_TASK_ID:
        option_count = _get_int(params, gen_defaults, "pose_option_count", 5)
        option_specs, answer_label = _build_pose_options(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.{query_id}.answer_option",
            rows=rows,
            cols=cols,
            final_row=final_row,
            final_col=final_col,
            final_direction=final_direction,
            option_count=option_count,
            rng=rng,
        )
    else:
        visit_counts = _agent_visit_counts(traces)
        if str(query_id) == "marked_line_flip_count":
            line_kind = "row" if int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{task_id}.{query_id}.line_kind")) % 2 == 0 else "column"
            candidates_by_score: Dict[int, List[Tuple[Tuple[int, int], ...]]] = {}
            if line_kind == "row":
                for row in range(rows):
                    cells = tuple((row, col) for col in range(cols))
                    score = int(sum(visit_counts.get((int(r), int(c)), 0) for r, c in cells))
                    if score > 0:
                        candidates_by_score.setdefault(score, []).append(cells)
            else:
                for col in range(cols):
                    cells = tuple((row, col) for row in range(rows))
                    score = int(sum(visit_counts.get((int(r), int(c)), 0) for r, c in cells))
                    if score > 0:
                        candidates_by_score.setdefault(score, []).append(cells)
            if candidates_by_score:
                scores = sorted(candidates_by_score)
                score_index = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{task_id}.{query_id}.answer_count")) % len(scores)
                selected_score = int(scores[score_index])
                target_cells = rng.choice(candidates_by_score[selected_score])
            else:
                target_cells = ((int(start_row), int(start_col)),)
            target_set = set(target_cells)
            flip_count = int(sum(1 for trace in traces if (int(trace.row), int(trace.col)) in target_set))
        elif str(query_id) == "marked_region_flip_count":
            candidates_by_score: Dict[int, List[Tuple[Tuple[int, int], ...]]] = {}
            for height, width in ((2, 2), (2, 3), (3, 2), (3, 3)):
                if height > rows or width > cols:
                    continue
                for row0 in range(rows - height + 1):
                    for col0 in range(cols - width + 1):
                        cells = _rect_cells(row0, col0, height, width)
                        score = int(sum(visit_counts.get((int(row), int(col)), 0) for row, col in cells))
                        if score > 0:
                            candidates_by_score.setdefault(score, []).append(cells)
            if candidates_by_score:
                scores = sorted(candidates_by_score)
                desired_max = max(1, min(int(steps), int(params.get("flip_answer_max", group_default(gen_defaults, "flip_answer_max", 8)))))
                desired = 1 + (
                    int(
                        _decorrelated_selection_index(
                            params=params,
                            instance_seed=int(instance_seed),
                            namespace=f"{task_id}.{query_id}.desired_answer_count",
                        )
                    )
                    % desired_max
                )
                selected_score = min(scores, key=lambda score: (abs(int(score) - int(desired)), int(score)))
                target_cells = rng.choice(candidates_by_score[selected_score])
            else:
                target_cells = ((int(start_row), int(start_col)),)
            target_set = set(target_cells)
            flip_count = int(sum(1 for trace in traces if (int(trace.row), int(trace.col)) in target_set))
        else:
            counts_by_state = {
                state: int(sum(1 for trace in traces if int(trace.state_before) == int(state)))
                for state in range(int(state_count))
            }
            states_by_count: Dict[int, List[int]] = {}
            for state, count in counts_by_state.items():
                if int(count) > 0:
                    states_by_count.setdefault(int(count), []).append(int(state))
            feasible_counts = sorted(states_by_count)
            count_index = int(
                _decorrelated_selection_index(
                    params=params,
                    instance_seed=int(instance_seed),
                    namespace=f"{task_id}.{query_id}.answer_count",
                )
            ) % len(feasible_counts)
            selected_count = int(feasible_counts[count_index])
            target_state = int(rng.choice(states_by_count[selected_count]))
            flip_count = int(sum(1 for trace in traces if int(trace.state_before) == int(target_state)))
    return _AgentDataset(
        rows=int(rows),
        cols=int(cols),
        state_count=int(state_count),
        rule_variant=str(resolved_rule_variant),
        query_id=str(query_id),
        steps=int(steps),
        initial_grid=grid,
        start_row=int(start_row),
        start_col=int(start_col),
        start_direction=int(start_direction),
        final_grid=final_grid,
        final_row=int(final_row),
        final_col=int(final_col),
        final_direction=int(final_direction),
        traces=traces,
        option_specs=option_specs,
        answer_label=str(answer_label),
        target_cells=target_cells,
        target_state=target_state,
        flip_count=int(flip_count),
    )


def _draw_agent_marker(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Sequence[int],
    direction: int,
    color: Sequence[int] = _AGENT_RGB,
    inner_fill: Sequence[int] = (255, 246, 236),
    width: int = 6,
) -> None:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    cx = 0.5 * (x0 + x1)
    cy = 0.5 * (y0 + y1)
    radius = 0.34 * min(x1 - x0, y1 - y0)
    dr, dc = _DIR_VEC[int(direction)]
    end = (float(cx + dc * radius), float(cy + dr * radius))
    start = (float(cx - dc * radius * 0.55), float(cy - dr * radius * 0.55))
    draw.ellipse(
        (cx - radius * 0.55, cy - radius * 0.55, cx + radius * 0.55, cy + radius * 0.55),
        fill=tuple(int(value) for value in inner_fill),
        outline=color,
        width=3,
    )
    draw_arrow(draw, start=start, end=end, fill=color, width=int(width), head_length_px=14, head_width_px=18)


def _draw_agent_pose_options(
    draw: ImageDraw.ImageDraw,
    *,
    option_specs: Sequence[Mapping[str, Any]],
    render_params: _RenderParams,
    top: int,
    item_bboxes: Dict[str, Tuple[int, int, int, int]],
    style: MiscSceneStyle = DEFAULT_MISC_SCENE_STYLE,
    cell_render_style: str = "classic_grid",
) -> Tuple[int, int, int, int]:
    card_w = int(render_params.option_card_width_px)
    card_h = int(render_params.option_card_height_px)
    gap = int(render_params.option_gap_px)
    count = len(option_specs)
    total_w = count * card_w + max(0, count - 1) * gap
    left = int((render_params.canvas_width - total_w) // 2)
    text_font = load_font(int(render_params.small_font_size_px), bold=False)
    for index, option in enumerate(option_specs):
        x0 = int(left + index * (card_w + gap))
        bbox = (x0, int(top), int(x0 + card_w), int(top + card_h))
        _draw_option_card(draw, bbox=bbox, label=str(option["label"]), fill=style.option_fill_rgb, style=style)
        item_bboxes[str(option["option_id"])] = bbox
        marker_side = max(24, min(int(card_w * 0.46), int(card_h * 0.42)))
        marker_left = int(x0 + (card_w - marker_side) / 2)
        marker_top = int(top + max(22, int(card_h * 0.22)))
        marker_bbox = (
            marker_left,
            marker_top,
            int(marker_left + marker_side),
            int(marker_top + marker_side),
        )
        _draw_cell_grid(
            draw,
            grid=((0,),),
            left=int(marker_bbox[0]),
            top=int(marker_bbox[1]),
            cell_size=int(marker_side),
            gap=1,
            state_colors=(style.option_marker_fill_rgb,),
            item_bboxes={},
            item_prefix="agent_option_marker",
            style=style,
            cell_render_style=str(cell_render_style),
        )
        _draw_agent_marker(
            draw,
            bbox=marker_bbox,
            direction=int(option["direction"]),
            color=style.agent_rgb,
            inner_fill=style.agent_inner_rgb,
            width=max(3, int(render_params.arrow_width_px) - 2),
        )
        draw_centered_text(
            draw,
            text=f"r{int(option['row']) + 1}, c{int(option['col']) + 1}",
            center=(x0 + card_w / 2, int(top) + card_h - max(14, int(card_h * 0.17))),
            font=text_font,
            fill=style.text_rgb,
            stroke_fill=style.text_stroke_rgb,
            stroke_width=1,
        )
    return (left, int(top), int(left + total_w), int(top + card_h))


def _render_agent_scene(
    *,
    background: Image.Image,
    dataset: _AgentDataset,
    scene_variant: str,
    render_params: _RenderParams,
    style: MiscSceneStyle | None = None,
    style_meta: Mapping[str, Any] | None = None,
    board_style: str = "classic_grid",
) -> _RenderedScene:
    image = background.copy()
    draw = ImageDraw.Draw(image)
    item_bboxes: Dict[str, Tuple[int, int, int, int]] = {}
    if style is None or style_meta is None:
        style, style_meta = _resolve_agent_style(scene_variant=str(scene_variant), render_params=render_params)
    rows, cols = int(dataset.rows), int(dataset.cols)
    cell = int(render_params.cell_size_px)
    gap = int(render_params.grid_gap_px)
    grid_bbox = _grid_bbox(left=0, top=0, rows=rows, cols=cols, cell_size=cell, gap=gap)
    grid_w = grid_bbox[2] - grid_bbox[0]
    grid_h = grid_bbox[3] - grid_bbox[1]
    metrics = _agent_content_metrics(dataset=dataset, render_params=render_params)
    layout_rng = spawn_rng(instance_seed=int(render_params.layout_seed), namespace="agent_automaton_panel_origin")
    safe_margin = max(18, int(round(render_params.panel_padding_px * 0.85)))
    panel_w = int(metrics["panel_width_px"])
    panel_h = int(metrics["panel_height_px"])
    content_h = int(metrics["content_height_px"])
    min_panel_left = int(safe_margin)
    max_panel_left = int(render_params.canvas_width - panel_w - safe_margin)
    if max_panel_left >= min_panel_left:
        available_x = int(max_panel_left - min_panel_left)
        offset_x = layout_rng.randint(0, available_x) if available_x > 0 else 0
        panel_left = int(min_panel_left + offset_x)
    else:
        available_x = 0
        offset_x = 0
        panel_left = max(0, int((render_params.canvas_width - panel_w) // 2))
    min_panel_top = int(safe_margin)
    max_panel_top = int(render_params.canvas_height - content_h - safe_margin)
    if max_panel_top >= min_panel_top:
        available_y = int(max_panel_top - min_panel_top)
        offset_y = layout_rng.randint(0, available_y) if available_y > 0 else 0
        panel_top = int(min_panel_top + offset_y)
    else:
        available_y = 0
        offset_y = 0
        panel_top = max(0, int((render_params.canvas_height - content_h) // 2))
    grid_left = int(panel_left + int(render_params.panel_padding_px))
    grid_top = int(panel_top + int(render_params.panel_padding_px))
    panel_bbox = (
        grid_left - int(render_params.panel_padding_px),
        grid_top - int(render_params.panel_padding_px),
        grid_left + grid_w + int(render_params.panel_padding_px),
        grid_top + grid_h + int(render_params.panel_padding_px),
    )
    _decorate_panel(
        draw,
        bbox=panel_bbox,
        scene_variant=str(scene_variant),
        radius=int(render_params.panel_corner_radius_px),
        border_width=int(render_params.panel_border_width_px),
        style=style,
        chrome_mode=str(style_meta.get("panel_chrome_mode", "accent_frame")),
    )
    _draw_cell_grid(
        draw,
        grid=dataset.initial_grid,
        left=grid_left,
        top=grid_top,
        cell_size=cell,
        gap=gap,
        state_colors=style.state_colors[: dataset.state_count],
        item_bboxes=item_bboxes,
        item_prefix="source",
        target_cells=dataset.target_cells,
        draw_labels=bool(dataset.state_count == 3),
        style=style,
        cell_render_style=str(board_style),
    )
    item_bboxes["source_grid"] = _grid_bbox(left=grid_left, top=grid_top, rows=rows, cols=cols, cell_size=cell, gap=gap)
    start_bbox = _cell_bbox(left=grid_left, top=grid_top, row=dataset.start_row, col=dataset.start_col, cell_size=cell, gap=gap)
    item_bboxes["initial_agent"] = start_bbox
    if not dataset.option_specs:
        step_font = load_font(max(10, int(cell * 0.24)), bold=True)
        for trace in dataset.traces:
            bbox = _cell_bbox(left=grid_left, top=grid_top, row=trace.row, col=trace.col, cell_size=cell, gap=gap)
            cx = int((bbox[0] + bbox[2]) / 2)
            cy = int((bbox[1] + bbox[3]) / 2)
            radius = max(8, int(cell * 0.19))
            draw.ellipse(
                (cx - radius, cy - radius, cx + radius, cy + radius),
                fill=style.step_fill_rgb,
                outline=style.agent_rgb,
                width=2,
            )
            draw_centered_text(
                draw,
                text=str(int(trace.step)),
                center=(cx, cy),
                font=step_font,
                fill=style.text_rgb,
                stroke_fill=style.text_stroke_rgb,
                stroke_width=1,
            )
    _draw_agent_marker(
        draw,
        bbox=start_bbox,
        direction=dataset.start_direction,
        color=style.agent_rgb,
        inner_fill=style.agent_inner_rgb,
        width=int(render_params.arrow_width_px),
    )
    if dataset.target_cells:
        item_bboxes["marked_region"] = _mark_region_bbox(
            cells=dataset.target_cells,
            grid_left=grid_left,
            grid_top=grid_top,
            cell_size=cell,
            gap=gap,
        )
    option_bbox = (0, 0, 0, 0)
    if dataset.option_specs:
        option_bbox = _draw_agent_pose_options(
            draw,
            option_specs=dataset.option_specs,
            render_params=render_params,
            top=int(panel_bbox[3] + _agent_option_vertical_gap(render_params)),
            item_bboxes=item_bboxes,
            style=style,
            cell_render_style=str(board_style),
        )
    scene_bbox = (
        min(panel_bbox[0], option_bbox[0]) if option_bbox[2] else panel_bbox[0],
        panel_bbox[1],
        max(panel_bbox[2], option_bbox[2]) if option_bbox[2] else panel_bbox[2],
        max(panel_bbox[3], option_bbox[3]) if option_bbox[2] else panel_bbox[3],
    )
    entities = tuple(
        {
            "entity_id": key,
            "bbox_px": list(value),
            "entity_type": "automaton_item",
        }
        for key, value in sorted(item_bboxes.items())
    )
    layout_jitter = {
        "enabled": True,
        "layout_seed": int(render_params.layout_seed),
        "canvas_size_px": [int(render_params.canvas_width), int(render_params.canvas_height)],
        "content_size_px": [int(metrics["content_width_px"]), int(metrics["content_height_px"])],
        "panel_size_px": [int(panel_w), int(panel_h)],
        "panel_origin_px": [int(panel_bbox[0]), int(panel_bbox[1])],
        "grid_bbox_px": [int(value) for value in item_bboxes["source_grid"]],
        "option_bbox_px": [int(value) for value in option_bbox] if option_bbox[2] else [],
        "available_offset_px": [int(available_x), int(available_y)],
        "sampled_offset_px": [int(offset_x), int(offset_y)],
        "safe_margin_px": int(safe_margin),
        "option_vertical_gap_px": int(_agent_option_vertical_gap(render_params)),
    }
    return _RenderedScene(
        image=image,
        scene_bbox_px=scene_bbox,
        item_bboxes=item_bboxes,
        entities=entities,
        layout_jitter=layout_jitter,
        style_metadata=style_meta,
    )


@register_task
class MiscAutomatonAgentFinalPoseLabelTask(_BaseAutomatonTask):
    """Choose the final agent pose after simulating a turning automaton."""

    task_id = AGENT_FINAL_TASK_ID

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        gen_defaults, render_defaults, prompt_defaults, complexity_weights = _load_defaults(self.task_id)
        query_id, query_probabilities = _resolve_query(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
            supported_queries=AGENT_FINAL_QUERY_IDS,
        )
        scene_variant, scene_probs = self._scene_variant(params=params, gen_defaults=gen_defaults, instance_seed=int(instance_seed))
        dataset = _build_agent_dataset(params=params, gen_defaults=gen_defaults, instance_seed=int(instance_seed), task_id=self.task_id, query_id=query_id)
        render_params = _resolve_render_params(params, render_defaults, instance_seed=int(instance_seed))
        render_params = _fit_agent_render_params(dataset=dataset, render_params=render_params)
        style, style_meta = _resolve_agent_style(scene_variant=str(scene_variant), render_params=render_params)
        agent_board_style, agent_board_probs = _resolve_agent_board_style(params=params, gen_defaults=gen_defaults, instance_seed=int(instance_seed), task_id=self.task_id)
        style_meta = _style_meta_with_font(style_meta, render_params)
        style_meta = _style_meta_with_agent_board(style_meta, board_style=agent_board_style, board_style_probabilities=agent_board_probs)
        background, background_meta = make_misc_scene_background(
            canvas_width=render_params.canvas_width,
            canvas_height=render_params.canvas_height,
            style=style,
        )
        with temporary_default_font_family(render_params.font_family):
            rendered = _render_agent_scene(
                background=background,
                dataset=dataset,
                scene_variant=scene_variant,
                render_params=render_params,
                style=style,
                style_meta=style_meta,
                board_style=agent_board_style,
            )
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        prompt, prompt_variants, prompt_meta = _build_prompt(
            prompt_defaults=prompt_defaults,
            scene_variant=scene_variant,
            query_id=query_id,
            steps=dataset.steps,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        correct_option = next(option for option in dataset.option_specs if bool(option["is_correct"]))
        annotation_role_item_ids = {
            "start_marker": "initial_agent",
            "selected_option": str(correct_option["option_id"]),
        }
        annotation_keyed_bboxes = _round_keyed_bboxes(
            projected_misc_keyed_bbox_annotation(rendered.item_bboxes, annotation_role_item_ids)
        )
        answer_gt = TypedValue(type="option_letter", value=str(dataset.answer_label))
        annotation_gt = TypedValue(type="keyed_bbox_map", value=dict(annotation_keyed_bboxes))
        execution_trace = {
            "rule_variant": str(dataset.rule_variant),
            "state_count": int(dataset.state_count),
            "steps": int(dataset.steps),
            "grid_rows": int(dataset.rows),
            "grid_cols": int(dataset.cols),
            "initial_grid": [list(row) for row in dataset.initial_grid],
            "final_grid": [list(row) for row in dataset.final_grid],
            "start_pose": {"row": int(dataset.start_row), "col": int(dataset.start_col), "direction": _DIRECTIONS[dataset.start_direction]},
            "final_pose": {"row": int(dataset.final_row), "col": int(dataset.final_col), "direction": _DIRECTIONS[dataset.final_direction]},
            "option_specs": [dict(option) for option in dataset.option_specs],
            "supporting_item_ids": list(annotation_role_item_ids.values()),
            "supporting_item_ids_by_role": dict(annotation_role_item_ids),
        }
        trace_payload = _common_trace(
            scene_id=AGENT_SCENE_ID,
            task_id=self.task_id,
            query_id=query_id,
            query_probabilities=query_probabilities,
            scene_variant=scene_variant,
            scene_variant_probabilities=scene_probs,
            prompt_meta=prompt_meta,
            render_params=render_params,
            rendered_scene=rendered,
            background_meta=background_meta,
            post_noise_meta=post_noise_meta,
            annotation_type="keyed_bbox_map",
            annotation_value=annotation_keyed_bboxes,
            answer_value=str(dataset.answer_label),
            execution_trace=execution_trace,
        )
        complexity = build_misc_complexity(
            weights=complexity_weights,
            components={
                "visual_scan": normalize_int_with_bounds(dataset.rows * dataset.cols, [36, 81]),
                "reasoning_load": normalize_int_with_bounds(dataset.steps, [5, 14]),
                "scene_variant_load": 0.20 if scene_variant == "clean_grid" else 0.30,
            },
        )
        return TaskOutput(
            prompt=prompt,
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=AGENT_SCENE_ID,
            query_id=query_id,
            prompt_variants=prompt_variants,
        )


@register_task
class MiscAutomatonAgentCellFlipCountTask(_BaseAutomatonTask):
    """Count how often a marked cell or region changes state under agent motion."""

    task_id = AGENT_FLIP_TASK_ID

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        gen_defaults, render_defaults, prompt_defaults, complexity_weights = _load_defaults(self.task_id)
        query_id, query_probabilities = _resolve_query(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
            supported_queries=AGENT_FLIP_QUERY_IDS,
        )
        scene_variant, scene_probs = self._scene_variant(params=params, gen_defaults=gen_defaults, instance_seed=int(instance_seed))
        rule_variant, rule_probs = _resolve_axis(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
            supported_variants=("binary_rule", "three_state_rule"),
            explicit_key="rule_variant",
            weights_key="rule_variant_weights",
            balance_flag_key="balanced_rule_variant_sampling",
            axis_namespace="rule_variant",
        )
        dataset = _build_agent_dataset(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
            query_id=query_id,
            rule_variant=rule_variant,
        )
        render_params = _resolve_render_params(params, render_defaults, instance_seed=int(instance_seed))
        render_params = _fit_agent_render_params(dataset=dataset, render_params=render_params)
        style, style_meta = _resolve_agent_style(scene_variant=str(scene_variant), render_params=render_params)
        agent_board_style, agent_board_probs = _resolve_agent_board_style(params=params, gen_defaults=gen_defaults, instance_seed=int(instance_seed), task_id=self.task_id)
        style_meta = _style_meta_with_font(style_meta, render_params)
        style_meta = _style_meta_with_agent_board(style_meta, board_style=agent_board_style, board_style_probabilities=agent_board_probs)
        background, background_meta = make_misc_scene_background(
            canvas_width=render_params.canvas_width,
            canvas_height=render_params.canvas_height,
            style=style,
        )
        with temporary_default_font_family(render_params.font_family):
            rendered = _render_agent_scene(
                background=background,
                dataset=dataset,
                scene_variant=scene_variant,
                render_params=render_params,
                style=style,
                style_meta=style_meta,
                board_style=agent_board_style,
            )
        image, post_noise_meta = apply_post_image_noise(rendered.image, instance_seed=int(instance_seed), params=params, default_config=POST_IMAGE_NOISE_DEFAULTS)
        prompt, prompt_variants, prompt_meta = _build_prompt(
            prompt_defaults=prompt_defaults,
            scene_variant=scene_variant,
            query_id=query_id,
            steps=dataset.steps,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
            rule_variant=rule_variant,
            extra_slots={
                "target_state_label": _state_label(state=int(dataset.target_state or 0), state_count=int(dataset.state_count)),
            }
            if query_id == "target_state_flip_count"
            else None,
        )
        annotation_ids = ["marked_region"]
        annotation_bboxes = _round_bboxes(projected_misc_bbox_annotation(rendered.item_bboxes, annotation_ids))
        answer_gt = TypedValue(type="integer", value=int(dataset.flip_count))
        annotation_gt = TypedValue(type="bbox_set", value=list(annotation_bboxes))
        execution_trace = {
            "rule_variant": str(rule_variant),
            "rule_variant_probabilities": dict(rule_probs),
            "state_count": int(dataset.state_count),
            "steps": int(dataset.steps),
            "grid_rows": int(dataset.rows),
            "grid_cols": int(dataset.cols),
            "initial_grid": [list(row) for row in dataset.initial_grid],
            "target_cells": [[int(row), int(col)] for row, col in dataset.target_cells],
            "target_state": (int(dataset.target_state) if dataset.target_state is not None else None),
            "target_state_label": (
                _state_label(state=int(dataset.target_state), state_count=int(dataset.state_count))
                if dataset.target_state is not None
                else ""
            ),
            "flip_count": int(dataset.flip_count),
            "path_trace": [
                {"step": trace.step, "row": trace.row, "col": trace.col, "state_before": trace.state_before, "state_after": trace.state_after}
                for trace in dataset.traces
            ],
            "supporting_item_ids": list(annotation_ids),
        }
        trace_payload = _common_trace(
            scene_id=AGENT_SCENE_ID,
            task_id=self.task_id,
            query_id=query_id,
            query_probabilities=query_probabilities,
            scene_variant=scene_variant,
            scene_variant_probabilities=scene_probs,
            prompt_meta=prompt_meta,
            render_params=render_params,
            rendered_scene=rendered,
            background_meta=background_meta,
            post_noise_meta=post_noise_meta,
            annotation_type="bbox_set",
            annotation_value=annotation_bboxes,
            answer_value=int(dataset.flip_count),
            execution_trace=execution_trace,
        )
        complexity = build_misc_complexity(
            weights=complexity_weights,
            components={
                "visual_scan": normalize_int_with_bounds(dataset.rows * dataset.cols, [36, 81]),
                "reasoning_load": normalize_int_with_bounds(dataset.steps + len(dataset.target_cells), [6, 24]),
                "scene_variant_load": 0.20 if scene_variant == "clean_grid" else 0.30,
            },
        )
        return TaskOutput(
            prompt=prompt,
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=AGENT_SCENE_ID,
            query_id=query_id,
            prompt_variants=prompt_variants,
        )


__all__ = [
    'MiscAutomatonAgentFinalPoseLabelTask',
    'MiscAutomatonAgentCellFlipCountTask',
]
