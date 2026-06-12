"""Life symbolic automaton tasks."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import hash64, spawn_rng
from ....core.scene_config import get_scene_defaults
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
    load_symbolic_task_defaults,
    projected_symbolic_bbox_annotation,
    projected_symbolic_keyed_bbox_annotation,
    resolve_symbolic_axis_variant,
)
from ..shared.scene_style import (
    DEFAULT_SYMBOLIC_SCENE_STYLE,
    SYMBOLIC_SCENE_TREATMENTS,
    SymbolicSceneStyle,
    draw_symbolic_chrome_by_mode,
    draw_symbolic_grid_cell,
    draw_symbolic_option_card,
    make_symbolic_scene_background,
    resolve_panel_chrome_mode,
    resolve_symbolic_scene_style,
)
from ..shared.unit_size_jitter import resolve_symbolic_unit_size_scale, scale_symbolic_px, with_symbolic_unit_size_jitter
from ..shared.visual_defaults import load_symbolic_background_defaults, load_symbolic_noise_defaults


from .shared import (
    LIFE_GRID_TASK_ID,
    LIFE_POP_TASK_ID,
    LIFE_SCENE_ID,
    LIFE_GRID_QUERY_IDS,
    LIFE_POP_QUERY_IDS,
    _LIFE_DEAD_RGB,
    _LIFE_ALIVE_RGB,
    _LIFE_BOARD_STYLES,
    _LIFE_CELL_PALETTES,
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
    _inset_bbox,
    _blend_rgb,
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
class _LifeDataset:
    rows: int
    cols: int
    query_id: str
    steps: int
    initial_grid: Tuple[Tuple[int, ...], ...]
    future_grid: Tuple[Tuple[int, ...], ...]
    option_specs: Tuple[Dict[str, Any], ...]
    answer_label: str
    target_cells: Tuple[Tuple[int, int], ...]
    live_count: int


@dataclass(frozen=True)
class _LifeBoardVisual:
    board_style: str
    cell_palette_id: str
    dead_rgb: Tuple[int, int, int]
    alive_rgb: Tuple[int, int, int]
    grid_rgb: Tuple[int, int, int]
    edge_rgb: Tuple[int, int, int]
    mark_rgb: Tuple[int, int, int]
    accent_rgb: Tuple[int, int, int]
    board_style_probabilities: Dict[str, float]
    cell_palette_probabilities: Dict[str, float]


def _resolve_life_board_visual(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> _LifeBoardVisual:
    board_style, board_probs = _resolve_axis(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        task_id=str(task_id),
        supported_variants=_LIFE_BOARD_STYLES,
        explicit_key="life_board_style",
        weights_key="life_board_style_weights",
        balance_flag_key="balanced_life_board_style_sampling",
        axis_namespace="life_board_style",
    )
    palette_id, palette_probs = _resolve_axis(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        task_id=str(task_id),
        supported_variants=tuple(_LIFE_CELL_PALETTES),
        explicit_key="life_cell_palette",
        weights_key="life_cell_palette_weights",
        balance_flag_key="balanced_life_cell_palette_sampling",
        axis_namespace="life_cell_palette",
    )
    palette = _LIFE_CELL_PALETTES[str(palette_id)]
    return _LifeBoardVisual(
        board_style=str(board_style),
        cell_palette_id=str(palette_id),
        dead_rgb=tuple(int(value) for value in palette["dead"]),
        alive_rgb=tuple(int(value) for value in palette["alive"]),
        grid_rgb=tuple(int(value) for value in palette["grid"]),
        edge_rgb=tuple(int(value) for value in palette["edge"]),
        mark_rgb=tuple(int(value) for value in palette["mark"]),
        accent_rgb=tuple(int(value) for value in palette["accent"]),
        board_style_probabilities={str(key): float(value) for key, value in board_probs.items()},
        cell_palette_probabilities={str(key): float(value) for key, value in palette_probs.items()},
    )


def _life_board_visual_metadata(life_visual: _LifeBoardVisual) -> Dict[str, Any]:
    alive_dead_lab = float(color_distance(life_visual.alive_rgb, life_visual.dead_rgb, distance_space="lab"))
    alive_dead_contrast = float(contrast_ratio(life_visual.alive_rgb, life_visual.dead_rgb))
    mark_contrast = min(
        float(contrast_ratio(life_visual.mark_rgb, life_visual.dead_rgb)),
        float(contrast_ratio(life_visual.mark_rgb, life_visual.alive_rgb)),
    )
    mark_lab = min(
        float(color_distance(life_visual.mark_rgb, life_visual.dead_rgb, distance_space="lab")),
        float(color_distance(life_visual.mark_rgb, life_visual.alive_rgb, distance_space="lab")),
    )
    return {
        "board_style": str(life_visual.board_style),
        "board_style_probabilities": dict(life_visual.board_style_probabilities),
        "cell_palette_id": str(life_visual.cell_palette_id),
        "cell_palette_probabilities": dict(life_visual.cell_palette_probabilities),
        "resolved_rgb": {
            "dead": list(life_visual.dead_rgb),
            "alive": list(life_visual.alive_rgb),
            "grid": list(life_visual.grid_rgb),
            "edge": list(life_visual.edge_rgb),
            "mark": list(life_visual.mark_rgb),
            "accent": list(life_visual.accent_rgb),
        },
        "semantic_color_policy": {
            "alive_cells_remain_dark": True,
            "empty_cells_remain_light": True,
            "same_style_and_palette_for_source_and_options": True,
        },
        "contrast_checks": {
            "alive_dead_contrast_ratio": round(alive_dead_contrast, 3),
            "alive_dead_lab_distance": round(alive_dead_lab, 3),
            "alive_dead_pass": bool(alive_dead_contrast >= 4.5 and alive_dead_lab >= 45.0),
            "mark_min_cell_contrast_ratio": round(mark_contrast, 3),
            "mark_min_cell_lab_distance": round(mark_lab, 3),
            "mark_pass": bool(mark_contrast >= 2.0 and mark_lab >= 30.0),
        },
    }


def _style_meta_with_life_board(
    style_meta: Mapping[str, Any],
    *,
    life_visual: _LifeBoardVisual,
) -> Dict[str, Any]:
    return {
        **dict(style_meta),
        "life_board": _life_board_visual_metadata(life_visual),
    }


def _life_option_vertical_gap(render_params: _RenderParams) -> int:
    unit_scale = float(render_params.unit_size_jitter.get("scale", 1.0))
    return scale_symbolic_px(50, unit_scale, min_px=28)


def _life_option_grid_gap(render_params: _RenderParams) -> int:
    return max(1, int(render_params.grid_gap_px))


def _life_option_card_size(
    *,
    rows: int,
    cols: int,
    render_params: _RenderParams,
) -> Tuple[int, int]:
    cell = int(render_params.option_grid_cell_px)
    gap = _life_option_grid_gap(render_params)
    grid_w = int(cols * cell + max(0, cols - 1) * gap)
    grid_h = int(rows * cell + max(0, rows - 1) * gap)
    pad_x = max(10, int(round(render_params.panel_padding_px * 0.45)))
    header_h = max(30, int(round(render_params.label_font_size_px * 1.45)))
    pad_bottom = max(10, int(round(render_params.panel_padding_px * 0.40)))
    return (
        max(int(render_params.option_card_width_px), int(grid_w + 2 * pad_x)),
        max(int(render_params.option_card_height_px) + 38, int(header_h + grid_h + pad_bottom)),
    )


def _life_content_metrics(
    *,
    dataset: _LifeDataset,
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
        card_w, card_h = _life_option_card_size(rows=rows, cols=cols, render_params=render_params)
        gap_x = int(render_params.option_gap_px)
        option_w = int(len(dataset.option_specs) * card_w + max(0, len(dataset.option_specs) - 1) * gap_x)
        option_h = int(card_h)
        option_gap_y = int(_life_option_vertical_gap(render_params))
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


def _fit_life_render_params(
    *,
    dataset: _LifeDataset,
    render_params: _RenderParams,
) -> _RenderParams:
    if dataset.option_specs:
        safe_margin = max(18, int(round(render_params.panel_padding_px * 0.85)))
        min_cell = max(18, min(int(render_params.cell_size_px), 22))
        for cell in range(int(render_params.cell_size_px), min_cell - 1, -1):
            candidate = replace(render_params, cell_size_px=int(cell), option_grid_cell_px=int(cell))
            candidate_metrics = _life_content_metrics(dataset=dataset, render_params=candidate)
            if (
                int(candidate_metrics["content_width_px"]) <= int(render_params.canvas_width - 2 * safe_margin)
                and int(candidate_metrics["content_height_px"]) <= int(render_params.canvas_height - 2 * safe_margin)
            ):
                render_params = candidate
                break
        else:
            render_params = replace(render_params, cell_size_px=int(min_cell), option_grid_cell_px=int(min_cell))
    metrics = _life_content_metrics(dataset=dataset, render_params=render_params)
    rng = spawn_rng(instance_seed=int(render_params.layout_seed), namespace="life_automaton_canvas")
    min_margin = max(24, int(round(render_params.panel_padding_px * 1.05)))
    max_margin = max(min_margin, int(round(render_params.panel_padding_px * 2.25)))
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


def _simulate_life(grid: Sequence[Sequence[int]], *, steps: int) -> Tuple[Tuple[int, ...], ...]:
    current = tuple(tuple(int(value) for value in row) for row in grid)
    rows = len(current)
    cols = len(current[0])
    for _ in range(int(steps)):
        next_rows: List[Tuple[int, ...]] = []
        for row in range(rows):
            values: List[int] = []
            for col in range(cols):
                neighbors = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr = row + dr
                        cc = col + dc
                        if 0 <= rr < rows and 0 <= cc < cols:
                            neighbors += int(current[rr][cc])
                alive = int(current[row][col])
                values.append(1 if (neighbors == 3 or (alive and neighbors == 2)) else 0)
            next_rows.append(tuple(values))
        current = tuple(next_rows)
    return current


def _grid_live_count(grid: Sequence[Sequence[int]], cells: Sequence[Tuple[int, int]] | None = None) -> int:
    if cells is None:
        return int(sum(int(value) for row in grid for value in row))
    return int(sum(int(grid[int(row)][int(col)]) for row, col in cells))


def _build_life_options(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
    future_grid: Sequence[Sequence[int]],
    option_count: int,
    rng,
) -> Tuple[Tuple[Dict[str, Any], ...], str]:
    rows = len(future_grid)
    cols = len(future_grid[0])
    correct = tuple(tuple(int(value) for value in row) for row in future_grid)
    options = {correct}
    while len(options) < int(option_count):
        candidate = [list(row) for row in correct]
        flips = int(rng.randint(1, 4))
        for _ in range(flips):
            row = int(rng.randrange(rows))
            col = int(rng.randrange(cols))
            candidate[row][col] = 1 - int(candidate[row][col])
        options.add(tuple(tuple(int(value) for value in row) for row in candidate))
    distractors = [option for option in options if option != correct]
    rng.shuffle(distractors)
    correct_index = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))) % int(option_count)
    ordered = []
    for index in range(int(option_count)):
        if index == correct_index:
            ordered.append(correct)
        else:
            ordered.append(distractors.pop())
    specs: List[Dict[str, Any]] = []
    answer_label = "A"
    for index, option_grid in enumerate(ordered):
        label = option_label_for_index(index)
        if option_grid == correct:
            answer_label = str(label)
        specs.append(
            {
                "option_id": f"option_{label}",
                "label": str(label),
                "grid": [list(row) for row in option_grid],
                "is_correct": bool(option_grid == correct),
            }
        )
    return tuple(specs), str(answer_label)


def _build_life_dataset(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    query_id: str,
) -> _LifeDataset:
    rng = spawn_rng(int(instance_seed), f"{task_id}.life")
    rows_min, rows_max = _get_range(params, gen_defaults, min_key="life_rows_min", max_key="life_rows_max", fallback_min=5, fallback_max=8)
    cols_min, cols_max = _get_range(params, gen_defaults, min_key="life_cols_min", max_key="life_cols_max", fallback_min=5, fallback_max=8)
    rows = int(rng.randint(rows_min, rows_max))
    cols = int(rng.randint(cols_min, cols_max))
    density = float(params.get("live_density", group_default(gen_defaults, "live_density", 0.36)))
    grid = _sample_grid(rng, rows=rows, cols=cols, state_count=2, live_prob=density)
    if str(query_id) == "two_step_future_grid":
        steps = 2
    elif str(query_id) == "one_step_future_grid":
        steps = 1
    else:
        steps_min, steps_max = _get_range(params, gen_defaults, min_key="life_steps_min", max_key="life_steps_max", fallback_min=1, fallback_max=3)
        steps = int(params.get("steps", rng.randint(steps_min, steps_max)))
    future_grid = _simulate_life(grid, steps=steps)
    option_specs: Tuple[Dict[str, Any], ...] = tuple()
    answer_label = ""
    target_cells: Tuple[Tuple[int, int], ...] = tuple((row, col) for row in range(rows) for col in range(cols))
    if str(task_id) == LIFE_GRID_TASK_ID:
        option_count = _get_int(params, gen_defaults, "grid_option_count", 5)
        option_specs, answer_label = _build_life_options(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.{query_id}.answer_option",
            future_grid=future_grid,
            option_count=option_count,
            rng=rng,
        )
    elif str(query_id) == "marked_line_live_count":
        candidates_by_count: Dict[int, List[Tuple[Tuple[int, int], ...]]] = {}
        for row in range(rows):
            cells = tuple((row, col) for col in range(cols))
            count = _grid_live_count(future_grid, cells)
            candidates_by_count.setdefault(int(count), []).append(cells)
        for col in range(cols):
            cells = tuple((row, col) for row in range(rows))
            count = _grid_live_count(future_grid, cells)
            candidates_by_count.setdefault(int(count), []).append(cells)
        counts = sorted(candidates_by_count)
        desired = int(
            _decorrelated_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{task_id}.{query_id}.desired_answer_count",
            )
        ) % (min(rows, cols) + 1)
        selected_count = int(min(counts, key=lambda count: (abs(int(count) - int(desired)), int(count))))
        target_cells = rng.choice(candidates_by_count[selected_count])
    elif str(query_id) == "marked_region_live_count":
        candidates_by_count: Dict[int, List[Tuple[Tuple[int, int], ...]]] = {}
        for height, width in ((2, 2), (2, 3), (3, 2), (3, 3)):
            if height > rows or width > cols:
                continue
            for row0 in range(rows - height + 1):
                for col0 in range(cols - width + 1):
                    cells = _rect_cells(row0, col0, height, width)
                    count = _grid_live_count(future_grid, cells)
                    candidates_by_count.setdefault(int(count), []).append(cells)
        counts = sorted(candidates_by_count)
        count_index = int(
            resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{task_id}.{query_id}.answer_count",
            )
        ) % len(counts)
        selected_count = int(counts[count_index])
        target_cells = rng.choice(candidates_by_count[selected_count])
    live_count = _grid_live_count(future_grid, target_cells if str(query_id) in {"marked_line_live_count", "marked_region_live_count"} else None)
    return _LifeDataset(
        rows=int(rows),
        cols=int(cols),
        query_id=str(query_id),
        steps=int(steps),
        initial_grid=grid,
        future_grid=future_grid,
        option_specs=option_specs,
        answer_label=str(answer_label),
        target_cells=target_cells,
        live_count=int(live_count),
    )


def _draw_life_cell_grid(
    draw: ImageDraw.ImageDraw,
    *,
    grid: Sequence[Sequence[int]],
    left: int,
    top: int,
    cell_size: int,
    gap: int,
    item_bboxes: Dict[str, Tuple[int, int, int, int]],
    item_prefix: str,
    target_cells: Sequence[Tuple[int, int]] = tuple(),
    style: SymbolicSceneStyle = DEFAULT_SYMBOLIC_SCENE_STYLE,
    life_visual: _LifeBoardVisual,
) -> None:
    target_set = {(int(row), int(col)) for row, col in target_cells}
    rows = len(grid)
    cols = len(grid[0])
    board_bbox = _grid_bbox(left=left, top=top, rows=rows, cols=cols, cell_size=cell_size, gap=gap)
    board_style = str(life_visual.board_style)
    if board_style in {"inset_tiles", "terminal_cells"}:
        draw_rounded_rect(
            draw,
            bbox=board_bbox,
            radius=max(4, int(cell_size * 0.14)),
            fill=life_visual.grid_rgb,
            outline=life_visual.edge_rgb,
            width=max(1, int(round(cell_size * 0.04))),
        )
    for row in range(rows):
        for col in range(cols):
            bbox = _cell_bbox(left=left, top=top, row=row, col=col, cell_size=cell_size, gap=gap)
            state = int(grid[row][col])
            fill = life_visual.alive_rgb if state else life_visual.dead_rgb
            cell_id = f"{item_prefix}_cell_{row}_{col}"
            item_bboxes[cell_id] = bbox
            if board_style == "classic_grid":
                draw.rectangle(
                    bbox,
                    fill=fill,
                    outline=life_visual.grid_rgb,
                    width=max(1, int(round(cell_size * 0.035))),
                )
            elif board_style == "rounded_tiles":
                draw_rounded_rect(
                    draw,
                    bbox=bbox,
                    radius=max(3, int(cell_size * 0.10)),
                    fill=fill,
                    outline=life_visual.grid_rgb,
                    width=max(1, int(round(cell_size * 0.035))),
                )
            elif board_style == "inset_tiles":
                inner = _inset_bbox(bbox, max(1, int(round(cell_size * 0.08))))
                draw_rounded_rect(
                    draw,
                    bbox=inner,
                    radius=max(3, int(cell_size * 0.12)),
                    fill=fill,
                    outline=life_visual.edge_rgb,
                    width=1,
                )
            elif board_style == "lab_matrix":
                draw.rectangle(
                    bbox,
                    fill=fill,
                    outline=life_visual.edge_rgb,
                    width=max(1, int(round(cell_size * 0.04))),
                )
                highlight = _blend_rgb(fill, (255, 255, 255), 0.24 if state else 0.42)
                draw.line((bbox[0] + 2, bbox[1] + 2, bbox[2] - 3, bbox[1] + 2), fill=highlight, width=1)
                draw.line((bbox[0] + 2, bbox[1] + 2, bbox[0] + 2, bbox[3] - 3), fill=highlight, width=1)
            elif board_style == "notebook_cells":
                draw.rectangle(bbox, fill=fill, outline=life_visual.grid_rgb, width=1)
                if not state:
                    line_y = int(round((bbox[1] + bbox[3]) / 2.0))
                    draw.line((bbox[0] + 4, line_y, bbox[2] - 4, line_y), fill=life_visual.accent_rgb, width=1)
                else:
                    draw.line((bbox[0] + 3, bbox[1] + 3, bbox[2] - 4, bbox[1] + 3), fill=life_visual.accent_rgb, width=1)
            elif board_style == "terminal_cells":
                draw.rectangle(bbox, fill=life_visual.grid_rgb)
                inner = _inset_bbox(bbox, max(1, int(round(cell_size * 0.06))))
                draw.rectangle(inner, fill=fill, outline=life_visual.edge_rgb, width=1)
                if state:
                    glow = _blend_rgb(fill, life_visual.accent_rgb, 0.20)
                    draw.rectangle(_inset_bbox(inner, max(2, int(round(cell_size * 0.22)))), fill=glow)
            else:
                draw_symbolic_grid_cell(
                    draw,
                    bbox=bbox,
                    fill=fill,
                    style=style,
                    outline=life_visual.grid_rgb,
                    width=1,
                    selected=False,
                )
            if (row, col) in target_set:
                draw.rectangle(
                    bbox,
                    outline=life_visual.mark_rgb,
                    width=max(3, int(cell_size * 0.10)),
                )


def _draw_life_option_grid(
    draw: ImageDraw.ImageDraw,
    *,
    option_grid: Sequence[Sequence[int]],
    bbox: Tuple[int, int, int, int],
    label: str,
    render_params: _RenderParams,
    style: SymbolicSceneStyle = DEFAULT_SYMBOLIC_SCENE_STYLE,
    life_visual: _LifeBoardVisual,
) -> None:
    _draw_option_card(draw, bbox=bbox, label=label, fill=style.option_fill_rgb, style=style)
    rows = len(option_grid)
    cols = len(option_grid[0])
    cell = int(render_params.option_grid_cell_px)
    gap = _life_option_grid_gap(render_params)
    grid_w = cols * cell + max(0, cols - 1) * gap
    grid_h = rows * cell + max(0, rows - 1) * gap
    header_h = max(30, int(round(render_params.label_font_size_px * 1.45)))
    left = int(bbox[0] + (bbox[2] - bbox[0] - grid_w) / 2)
    top = int(bbox[1] + header_h + max(0, (bbox[3] - bbox[1] - header_h - grid_h) / 2))
    dummy: Dict[str, Tuple[int, int, int, int]] = {}
    _draw_life_cell_grid(
        draw,
        grid=option_grid,
        left=left,
        top=top,
        cell_size=cell,
        gap=gap,
        item_bboxes=dummy,
        item_prefix="option_preview",
        style=style,
        life_visual=life_visual,
    )


def _draw_life_options(
    draw: ImageDraw.ImageDraw,
    *,
    option_specs: Sequence[Mapping[str, Any]],
    render_params: _RenderParams,
    top: int,
    item_bboxes: Dict[str, Tuple[int, int, int, int]],
    style: SymbolicSceneStyle = DEFAULT_SYMBOLIC_SCENE_STYLE,
    life_visual: _LifeBoardVisual,
    left: int | None = None,
) -> Tuple[int, int, int, int]:
    rows = len(option_specs[0]["grid"]) if option_specs else 0
    cols = len(option_specs[0]["grid"][0]) if option_specs else 0
    card_w, card_h = _life_option_card_size(rows=rows, cols=cols, render_params=render_params)
    gap = int(render_params.option_gap_px)
    count = len(option_specs)
    total_w = count * card_w + max(0, count - 1) * gap
    if left is None:
        left = int((render_params.canvas_width - total_w) // 2)
    else:
        left = int(left)
    for index, option in enumerate(option_specs):
        x0 = int(left + index * (card_w + gap))
        bbox = (x0, int(top), int(x0 + card_w), int(top + card_h))
        _draw_life_option_grid(
            draw,
            option_grid=option["grid"],
            bbox=bbox,
            label=str(option["label"]),
            render_params=render_params,
            style=style,
            life_visual=life_visual,
        )
        item_bboxes[str(option["option_id"])] = bbox
    return (left, int(top), int(left + total_w), int(top + card_h))


def _render_life_scene(
    *,
    background: Image.Image,
    dataset: _LifeDataset,
    scene_variant: str,
    render_params: _RenderParams,
    style: SymbolicSceneStyle | None = None,
    style_meta: Mapping[str, Any] | None = None,
    life_visual: _LifeBoardVisual | None = None,
) -> _RenderedScene:
    image = background.copy()
    draw = ImageDraw.Draw(image)
    item_bboxes: Dict[str, Tuple[int, int, int, int]] = {}
    if style is None or style_meta is None:
        style, style_meta = _resolve_agent_style(scene_variant=str(scene_variant), render_params=render_params)
    if life_visual is None:
        life_visual = _LifeBoardVisual(
            board_style="classic_grid",
            cell_palette_id="mono_ink",
            dead_rgb=_LIFE_DEAD_RGB,
            alive_rgb=_LIFE_ALIVE_RGB,
            grid_rgb=style.grid_rgb,
            edge_rgb=style.grid_rgb,
            mark_rgb=style.mark_rgb,
            accent_rgb=style.panel_accent_rgb,
            board_style_probabilities={"classic_grid": 1.0},
            cell_palette_probabilities={"mono_ink": 1.0},
        )
    rows, cols = int(dataset.rows), int(dataset.cols)
    cell = int(render_params.cell_size_px)
    gap = int(render_params.grid_gap_px)
    grid_bbox = _grid_bbox(left=0, top=0, rows=rows, cols=cols, cell_size=cell, gap=gap)
    grid_w = grid_bbox[2] - grid_bbox[0]
    grid_h = grid_bbox[3] - grid_bbox[1]
    is_population_count = not bool(dataset.option_specs)
    metrics = _life_content_metrics(dataset=dataset, render_params=render_params)
    layout_rng = spawn_rng(instance_seed=int(render_params.layout_seed), namespace="life_automaton_panel_origin")
    safe_margin = max(18, int(round(render_params.panel_padding_px * 0.85)))
    content_w = int(metrics["content_width_px"])
    content_h = int(metrics["content_height_px"])
    panel_w = int(metrics["panel_width_px"])
    panel_h = int(metrics["panel_height_px"])
    min_content_left = int(safe_margin)
    max_content_left = int(render_params.canvas_width - content_w - safe_margin)
    if max_content_left >= min_content_left:
        available_x = int(max_content_left - min_content_left)
        offset_x = layout_rng.randint(0, available_x) if available_x > 0 else 0
        content_left = int(min_content_left + offset_x)
    else:
        available_x = 0
        offset_x = 0
        content_left = max(0, int((render_params.canvas_width - content_w) // 2))
    min_content_top = int(safe_margin)
    max_content_top = int(render_params.canvas_height - content_h - safe_margin)
    if max_content_top >= min_content_top:
        available_y = int(max_content_top - min_content_top)
        offset_y = layout_rng.randint(0, available_y) if available_y > 0 else 0
        content_top = int(min_content_top + offset_y)
    else:
        available_y = 0
        offset_y = 0
        content_top = max(0, int((render_params.canvas_height - content_h) // 2))
    panel_left = int(content_left + max(0, content_w - panel_w) // 2)
    panel_top = int(content_top)
    grid_left = int(panel_left + int(render_params.panel_padding_px))
    future_left = grid_left
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
        style=style,
        chrome_mode=str(style_meta.get("panel_chrome_mode", "accent_frame")),
    )
    target_cells = dataset.target_cells if str(dataset.query_id) in {"marked_line_live_count", "marked_region_live_count"} else tuple()
    if is_population_count:
        _draw_life_cell_grid(
            draw,
            grid=dataset.future_grid,
            left=future_left,
            top=grid_top,
            cell_size=cell,
            gap=gap,
            item_bboxes=item_bboxes,
            item_prefix="future",
            target_cells=target_cells,
            style=style,
            life_visual=life_visual,
        )
        item_bboxes["future_grid"] = _grid_bbox(left=future_left, top=grid_top, rows=rows, cols=cols, cell_size=cell, gap=gap)
    else:
        _draw_life_cell_grid(
            draw,
            grid=dataset.initial_grid,
            left=grid_left,
            top=grid_top,
            cell_size=cell,
            gap=gap,
            item_bboxes=item_bboxes,
            item_prefix="source",
            target_cells=tuple(),
            style=style,
            life_visual=life_visual,
        )
        item_bboxes["source_grid"] = _grid_bbox(left=grid_left, top=grid_top, rows=rows, cols=cols, cell_size=cell, gap=gap)
    if target_cells:
        item_bboxes["marked_region"] = _mark_region_bbox(
            cells=target_cells,
            grid_left=future_left if is_population_count else grid_left,
            grid_top=grid_top,
            cell_size=cell,
            gap=gap,
        )
    option_bbox = (0, 0, 0, 0)
    if dataset.option_specs:
        option_left = int(content_left + max(0, content_w - int(metrics["option_width_px"])) // 2)
        option_bbox = _draw_life_options(
            draw,
            option_specs=dataset.option_specs,
            render_params=render_params,
            top=int(panel_bbox[3] + int(metrics["option_vertical_gap_px"])),
            item_bboxes=item_bboxes,
            style=style,
            life_visual=life_visual,
            left=option_left,
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
    return _RenderedScene(
        image=image,
        scene_bbox_px=scene_bbox,
        item_bboxes=item_bboxes,
        entities=entities,
        layout_jitter={
            "enabled": True,
            "mode": "safe_margin_free_area",
            "canvas_size_px": [int(render_params.canvas_width), int(render_params.canvas_height)],
            "content_size_px": [int(content_w), int(content_h)],
            "panel_size_px": [int(panel_w), int(panel_h)],
            "panel_origin_px": [int(panel_bbox[0]), int(panel_bbox[1])],
            "grid_bbox_px": [int(value) for value in (item_bboxes["future_grid"] if is_population_count else item_bboxes["source_grid"])],
            "option_bbox_px": [int(value) for value in option_bbox] if option_bbox[2] else [],
            "free_space_px": [
                int(render_params.canvas_width - content_w),
                int(render_params.canvas_height - content_h),
            ],
            "available_offset_px": [int(available_x), int(available_y)],
            "sampled_offset_px": [int(offset_x), int(offset_y)],
            "sampled_fraction": [
                round(float(offset_x) / float(available_x), 6) if available_x > 0 else 0.5,
                round(float(offset_y) / float(available_y), 6) if available_y > 0 else 0.5,
            ],
            "content_origin_px": [int(content_left), int(content_top)],
            "centered_content_origin_px": [
                int((render_params.canvas_width - content_w) // 2),
                int((render_params.canvas_height - content_h) // 2),
            ],
            "dx_dy_from_center_px": [
                int(content_left - int((render_params.canvas_width - content_w) // 2)),
                int(content_top - int((render_params.canvas_height - content_h) // 2)),
            ],
            "safe_margin_px": int(safe_margin),
            "option_vertical_gap_px": int(metrics["option_vertical_gap_px"]),
        },
        style_metadata=dict(style_meta),
    )


@register_task
class SymbolicAutomatonLifeFutureGridLabelTask(_BaseAutomatonTask):
    """Choose the future grid after one or two Life updates."""

    task_id = LIFE_GRID_TASK_ID
    supported_query_ids = LIFE_GRID_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id, query_probabilities = _resolve_query(params=params, gen_defaults=gen_defaults, instance_seed=int(instance_seed), task_id=self.task_id, supported_queries=LIFE_GRID_QUERY_IDS)
        scene_variant, scene_probs = self._scene_variant(params=params, gen_defaults=gen_defaults, instance_seed=int(instance_seed))
        dataset = _build_life_dataset(params=params, gen_defaults=gen_defaults, instance_seed=int(instance_seed), task_id=self.task_id, query_id=query_id)
        render_params = _resolve_render_params(params, render_defaults, instance_seed=int(instance_seed))
        render_params = _fit_life_render_params(dataset=dataset, render_params=render_params)
        style, style_meta = _resolve_agent_style(scene_variant=str(scene_variant), render_params=render_params)
        life_visual = _resolve_life_board_visual(params=params, gen_defaults=gen_defaults, instance_seed=int(instance_seed), task_id=self.task_id)
        style_meta = _style_meta_with_font(style_meta, render_params)
        style_meta = _style_meta_with_life_board(style_meta, life_visual=life_visual)
        background, background_meta = make_symbolic_scene_background(canvas_width=render_params.canvas_width, canvas_height=render_params.canvas_height, style=style)
        with temporary_default_font_family(render_params.font_family):
            rendered = _render_life_scene(background=background, dataset=dataset, scene_variant=scene_variant, render_params=render_params, style=style, style_meta=style_meta, life_visual=life_visual)
        image, post_noise_meta = apply_post_image_noise(rendered.image, instance_seed=int(instance_seed), params=params, default_config=POST_IMAGE_NOISE_DEFAULTS)
        prompt, prompt_variants, prompt_meta = _build_prompt(prompt_defaults=prompt_defaults, scene_variant=scene_variant, query_id=query_id, steps=dataset.steps, instance_seed=int(instance_seed), task_id=self.task_id)
        correct_option = next(option for option in dataset.option_specs if bool(option["is_correct"]))
        annotation_role_item_ids = {
            "source_grid": "source_grid",
            "selected_option": str(correct_option["option_id"]),
        }
        annotation_keyed_bboxes = _round_keyed_bboxes(
            projected_symbolic_keyed_bbox_annotation(rendered.item_bboxes, annotation_role_item_ids)
        )
        answer_gt = TypedValue(type="option_letter", value=str(dataset.answer_label))
        annotation_gt = TypedValue(type="keyed_bbox_map", value=dict(annotation_keyed_bboxes))
        execution_trace = {
            "steps": int(dataset.steps),
            "grid_rows": int(dataset.rows),
            "grid_cols": int(dataset.cols),
            "initial_grid": [list(row) for row in dataset.initial_grid],
            "future_grid": [list(row) for row in dataset.future_grid],
            "option_specs": [dict(option) for option in dataset.option_specs],
            "supporting_item_ids": list(annotation_role_item_ids.values()),
            "supporting_item_ids_by_role": dict(annotation_role_item_ids),
        }
        trace_payload = _common_trace(scene_id=LIFE_SCENE_ID, task_id=self.task_id, query_id=query_id, query_probabilities=query_probabilities, scene_variant=scene_variant, scene_variant_probabilities=scene_probs, prompt_meta=prompt_meta, render_params=render_params, rendered_scene=rendered, background_meta=background_meta, post_noise_meta=post_noise_meta, annotation_type="keyed_bbox_map", annotation_value=annotation_keyed_bboxes, answer_value=str(dataset.answer_label), execution_trace=execution_trace)
        return TaskOutput(prompt=prompt, answer_gt=answer_gt, annotation_gt=annotation_gt, image=image, image_id="img0", trace_payload=trace_payload,  task_versions=default_task_versions(), scene_id=LIFE_SCENE_ID, query_id=query_id, prompt_variants=prompt_variants)


@register_task
class SymbolicAutomatonLifePopulationCountTask(_BaseAutomatonTask):
    """Count live cells after Life updates."""

    task_id = LIFE_POP_TASK_ID
    supported_query_ids = LIFE_POP_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id, query_probabilities = _resolve_query(params=params, gen_defaults=gen_defaults, instance_seed=int(instance_seed), task_id=self.task_id, supported_queries=LIFE_POP_QUERY_IDS)
        scene_variant, scene_probs = self._scene_variant(params=params, gen_defaults=gen_defaults, instance_seed=int(instance_seed))
        dataset = _build_life_dataset(params=params, gen_defaults=gen_defaults, instance_seed=int(instance_seed), task_id=self.task_id, query_id=query_id)
        render_params = _resolve_render_params(params, render_defaults, instance_seed=int(instance_seed))
        render_params = _fit_life_render_params(dataset=dataset, render_params=render_params)
        style, style_meta = _resolve_agent_style(scene_variant=str(scene_variant), render_params=render_params)
        life_visual = _resolve_life_board_visual(params=params, gen_defaults=gen_defaults, instance_seed=int(instance_seed), task_id=self.task_id)
        style_meta = _style_meta_with_font(style_meta, render_params)
        style_meta = _style_meta_with_life_board(style_meta, life_visual=life_visual)
        background, background_meta = make_symbolic_scene_background(canvas_width=render_params.canvas_width, canvas_height=render_params.canvas_height, style=style)
        with temporary_default_font_family(render_params.font_family):
            rendered = _render_life_scene(background=background, dataset=dataset, scene_variant=scene_variant, render_params=render_params, style=style, style_meta=style_meta, life_visual=life_visual)
        image, post_noise_meta = apply_post_image_noise(rendered.image, instance_seed=int(instance_seed), params=params, default_config=POST_IMAGE_NOISE_DEFAULTS)
        prompt, prompt_variants, prompt_meta = _build_prompt(prompt_defaults=prompt_defaults, scene_variant=scene_variant, query_id=query_id, steps=dataset.steps, instance_seed=int(instance_seed), task_id=self.task_id)
        annotation_ids = ["marked_region"] if query_id in {"marked_line_live_count", "marked_region_live_count"} else ["source_grid"]
        annotation_bboxes = _round_bboxes(projected_symbolic_bbox_annotation(rendered.item_bboxes, annotation_ids))
        answer_gt = TypedValue(type="integer", value=int(dataset.live_count))
        annotation_gt = TypedValue(type="bbox_set", value=list(annotation_bboxes))
        execution_trace = {
            "steps": int(dataset.steps),
            "grid_rows": int(dataset.rows),
            "grid_cols": int(dataset.cols),
            "initial_grid": [list(row) for row in dataset.initial_grid],
            "future_grid": [list(row) for row in dataset.future_grid],
            "target_cells": [[int(row), int(col)] for row, col in dataset.target_cells],
            "live_count": int(dataset.live_count),
            "supporting_item_ids": list(annotation_ids),
        }
        trace_payload = _common_trace(scene_id=LIFE_SCENE_ID, task_id=self.task_id, query_id=query_id, query_probabilities=query_probabilities, scene_variant=scene_variant, scene_variant_probabilities=scene_probs, prompt_meta=prompt_meta, render_params=render_params, rendered_scene=rendered, background_meta=background_meta, post_noise_meta=post_noise_meta, annotation_type="bbox_set", annotation_value=annotation_bboxes, answer_value=int(dataset.live_count), execution_trace=execution_trace)
        return TaskOutput(prompt=prompt, answer_gt=answer_gt, annotation_gt=annotation_gt, image=image, image_id="img0", trace_payload=trace_payload,  task_versions=default_task_versions(), scene_id=LIFE_SCENE_ID, query_id=query_id, prompt_variants=prompt_variants)


__all__ = [
    'SymbolicAutomatonLifeFutureGridLabelTask',
    'SymbolicAutomatonLifePopulationCountTask',
]
