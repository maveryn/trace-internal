"""Lights-Out-style toggle grid puzzle tasks."""

from __future__ import annotations

from dataclasses import dataclass
from string import ascii_uppercase
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.drawing import draw_centered_text, draw_rounded_rect
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_rendering import load_font
from ..shared.common import resolve_puzzle_axis_variant
from ..shared.complexity import build_puzzle_complexity, clamp_unit_interval, normalize_int_with_bounds, resolve_puzzle_complexity_weights
from ..shared.scene_style import make_puzzle_scene_background, resolve_puzzle_scene_style
from ..shared.visual_defaults import load_puzzle_noise_defaults


TOGGLE_RESULT_TASK_ID = "task_puzzles__toggle_grid__toggle_result_label"
TOGGLE_REPAIR_TASK_ID = "task_puzzles__toggle_grid__toggle_repair_switch_label"
SCENE_ID = "toggle_grid"
RESULT_QUERY_ID = "toggle_result_label"
REPAIR_QUERY_ID = "toggle_repair_switch_label"
SCENE_VARIANTS: Tuple[str, ...] = ("toggle_clean", "toggle_notebook", "toggle_console")


GridState = Tuple[Tuple[int, ...], ...]
Cell = Tuple[int, int]


@dataclass(frozen=True)
class ResultOption:
    option_label: str
    state: GridState
    is_correct: bool


@dataclass(frozen=True)
class SwitchOption:
    option_label: str
    row: int
    col: int
    is_correct: bool


@dataclass(frozen=True)
class ToggleDataset:
    query_id: str
    rows: int
    cols: int
    start_state: GridState
    target_state: GridState
    pressed_cells: Tuple[Cell, ...]
    result_options: Tuple[ResultOption, ...]
    switch_options: Tuple[SwitchOption, ...]
    correct_option_label: str
    scene_variant: str


@dataclass(frozen=True)
class ToggleDefaults:
    canvas_width: int = 1120
    canvas_height: int = 860
    grid_rows_min: int = 4
    grid_rows_max: int = 5
    grid_cols_min: int = 4
    grid_cols_max: int = 5
    result_press_count_min: int = 2
    result_press_count_max: int = 4
    option_count: int = 5
    main_cell_size_px: int = 72
    mini_cell_size_px: int = 28
    panel_title_font_size_px: int = 22
    option_font_size_px: int = 22


_DEFAULTS = ToggleDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "logic")
_GEN_DEFAULTS_RESULT, _RENDER_DEFAULTS_RESULT, _PROMPT_DEFAULTS_RESULT = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TOGGLE_RESULT_TASK_ID,
)
_GEN_DEFAULTS_REPAIR, _RENDER_DEFAULTS_REPAIR, _PROMPT_DEFAULTS_REPAIR = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TOGGLE_REPAIR_TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_puzzle_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TOGGLE_RESULT_TASK_ID)
POST_IMAGE_NOISE_DEFAULTS = load_puzzle_noise_defaults(task_group="logic", apply_prob=0.0)


def _get_int(params: Mapping[str, Any], defaults: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), group_default(defaults, str(key), int(fallback))))


def _resolve_scene_variant(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    task_id: str,
    instance_seed: int,
) -> Tuple[str, Dict[str, float]]:
    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SCENE_VARIANTS,
        task_id=str(task_id),
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def _state_signature(state: GridState) -> Tuple[Tuple[int, ...], ...]:
    return tuple(tuple(int(value) for value in row) for row in state)


def _random_state(*, rows: int, cols: int, instance_seed: int, namespace: str) -> GridState:
    rng = spawn_rng(int(instance_seed), str(namespace))
    state = tuple(tuple(int(rng.randrange(2)) for _ in range(int(cols))) for _ in range(int(rows)))
    if sum(sum(row) for row in state) in {0, int(rows) * int(cols)}:
        mutable = [list(row) for row in state]
        mutable[0][0] = 1 - int(mutable[0][0])
        state = tuple(tuple(row) for row in mutable)
    return _state_signature(state)


def _toggle_once(state: GridState, cell: Cell) -> GridState:
    rows = len(state)
    cols = len(state[0])
    mutable = [list(row) for row in state]
    row, col = int(cell[0]), int(cell[1])
    for rr, cc in ((row, col), (row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)):
        if 0 <= rr < rows and 0 <= cc < cols:
            mutable[rr][cc] = 1 - int(mutable[rr][cc])
    return _state_signature(tuple(tuple(row) for row in mutable))


def _apply_toggles(state: GridState, cells: Sequence[Cell]) -> GridState:
    current = _state_signature(state)
    for cell in cells:
        current = _toggle_once(current, tuple(cell))
    return current


def _all_cells(rows: int, cols: int) -> Tuple[Cell, ...]:
    return tuple((row, col) for row in range(int(rows)) for col in range(int(cols)))


def _sample_grid_size(*, params: Mapping[str, Any], defaults: Mapping[str, Any], instance_seed: int, task_id: str) -> Tuple[int, int]:
    row_min = _get_int(params, defaults, "grid_rows_min", _DEFAULTS.grid_rows_min)
    row_max = _get_int(params, defaults, "grid_rows_max", _DEFAULTS.grid_rows_max)
    col_min = _get_int(params, defaults, "grid_cols_min", _DEFAULTS.grid_cols_min)
    col_max = _get_int(params, defaults, "grid_cols_max", _DEFAULTS.grid_cols_max)
    rows = int(row_min + (resolve_selection_index(params={}, instance_seed=int(instance_seed), namespace=f"{task_id}.rows") % max(1, row_max - row_min + 1)))
    cols = int(col_min + (resolve_selection_index(params={}, instance_seed=int(instance_seed), namespace=f"{task_id}.cols") % max(1, col_max - col_min + 1)))
    return rows, cols


def _result_options(
    *,
    target_state: GridState,
    instance_seed: int,
    option_count: int,
) -> Tuple[Tuple[ResultOption, ...], str]:
    rows = len(target_state)
    cols = len(target_state[0])
    rng = spawn_rng(int(instance_seed), f"{TOGGLE_RESULT_TASK_ID}.options")
    correct_index = resolve_selection_index(params={}, instance_seed=int(instance_seed), namespace=f"{TOGGLE_RESULT_TASK_ID}.correct_option_index") % int(option_count)
    states: List[GridState] = [target_state]
    cells = list(_all_cells(rows, cols))
    while len(states) < int(option_count):
        mutated = _toggle_once(target_state, cells[int(rng.randrange(len(cells)))])
        if mutated not in states:
            states.append(mutated)
    correct = states.pop(0)
    rng.shuffle(states)
    states.insert(int(correct_index), correct)
    labels = tuple(ascii_uppercase[index] for index in range(int(option_count)))
    return tuple(ResultOption(str(label), state, state == target_state) for label, state in zip(labels, states)), str(labels[int(correct_index)])


def _sample_result_dataset(*, params: Mapping[str, Any], instance_seed: int) -> ToggleDataset:
    scene_variant, _ = _resolve_scene_variant(params=params, gen_defaults=_GEN_DEFAULTS_RESULT, task_id=TOGGLE_RESULT_TASK_ID, instance_seed=int(instance_seed))
    rows, cols = _sample_grid_size(params=params, defaults=_GEN_DEFAULTS_RESULT, instance_seed=int(instance_seed), task_id=TOGGLE_RESULT_TASK_ID)
    press_min = _get_int(params, _GEN_DEFAULTS_RESULT, "result_press_count_min", _DEFAULTS.result_press_count_min)
    press_max = _get_int(params, _GEN_DEFAULTS_RESULT, "result_press_count_max", _DEFAULTS.result_press_count_max)
    option_count = _get_int(params, _GEN_DEFAULTS_RESULT, "option_count", _DEFAULTS.option_count)
    rng = spawn_rng(int(instance_seed), f"{TOGGLE_RESULT_TASK_ID}.dataset")
    start_state = _random_state(rows=rows, cols=cols, instance_seed=int(instance_seed), namespace=f"{TOGGLE_RESULT_TASK_ID}.start")
    press_count = int(press_min + (resolve_selection_index(params={}, instance_seed=int(instance_seed), namespace=f"{TOGGLE_RESULT_TASK_ID}.press_count") % max(1, press_max - press_min + 1)))
    pressed_cells = tuple(rng.sample(list(_all_cells(rows, cols)), int(press_count)))
    target_state = _apply_toggles(start_state, pressed_cells)
    options, correct_label = _result_options(target_state=target_state, instance_seed=int(instance_seed), option_count=int(option_count))
    return ToggleDataset(
        query_id=RESULT_QUERY_ID,
        rows=int(rows),
        cols=int(cols),
        start_state=start_state,
        target_state=target_state,
        pressed_cells=tuple((int(r), int(c)) for r, c in pressed_cells),
        result_options=tuple(options),
        switch_options=tuple(),
        correct_option_label=str(correct_label),
        scene_variant=str(scene_variant),
    )


def _sample_repair_dataset(*, params: Mapping[str, Any], instance_seed: int) -> ToggleDataset:
    scene_variant, _ = _resolve_scene_variant(params=params, gen_defaults=_GEN_DEFAULTS_REPAIR, task_id=TOGGLE_REPAIR_TASK_ID, instance_seed=int(instance_seed))
    rows, cols = _sample_grid_size(params=params, defaults=_GEN_DEFAULTS_REPAIR, instance_seed=int(instance_seed), task_id=TOGGLE_REPAIR_TASK_ID)
    option_count = _get_int(params, _GEN_DEFAULTS_REPAIR, "option_count", _DEFAULTS.option_count)
    rng = spawn_rng(int(instance_seed), f"{TOGGLE_REPAIR_TASK_ID}.dataset")
    start_state = _random_state(rows=rows, cols=cols, instance_seed=int(instance_seed), namespace=f"{TOGGLE_REPAIR_TASK_ID}.start")
    all_cells = list(_all_cells(rows, cols))
    correct_cell = tuple(all_cells[int(rng.randrange(len(all_cells)))])
    target_state = _toggle_once(start_state, correct_cell)
    candidates = [correct_cell]
    rng.shuffle(all_cells)
    for cell in all_cells:
        if tuple(cell) not in candidates:
            candidates.append(tuple(cell))
        if len(candidates) >= int(option_count):
            break
    correct_index = resolve_selection_index(params={}, instance_seed=int(instance_seed), namespace=f"{TOGGLE_REPAIR_TASK_ID}.correct_option_index") % int(option_count)
    correct = candidates.pop(0)
    rng.shuffle(candidates)
    candidates.insert(int(correct_index), correct)
    labels = tuple(ascii_uppercase[index] for index in range(int(option_count)))
    options = tuple(
        SwitchOption(option_label=str(label), row=int(cell[0]), col=int(cell[1]), is_correct=tuple(cell) == tuple(correct_cell))
        for label, cell in zip(labels, candidates)
    )
    return ToggleDataset(
        query_id=REPAIR_QUERY_ID,
        rows=int(rows),
        cols=int(cols),
        start_state=start_state,
        target_state=target_state,
        pressed_cells=(tuple(correct_cell),),
        result_options=tuple(),
        switch_options=tuple(options),
        correct_option_label=str(labels[int(correct_index)]),
        scene_variant=str(scene_variant),
    )


def _state_colors(style: Any) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    colors = tuple(tuple(int(v) for v in color) for color in tuple(style.state_colors))
    on = colors[0] if colors else (77, 137, 201)
    off = tuple(int(v) for v in style.option_fill_rgb)
    return off, on


def _draw_grid(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Sequence[float],
    title: str,
    state: GridState,
    style: Any,
    pressed_cells: Sequence[Cell] = (),
    switch_options: Sequence[SwitchOption] = (),
    cell_size: int | None = None,
) -> Tuple[List[float], Dict[str, List[float]]]:
    x0, y0, x1, y1 = [int(round(float(value))) for value in bbox]
    draw_rounded_rect(draw, (x0, y0, x1, y1), radius=18, fill=tuple(style.panel_fill_rgb), outline=tuple(style.panel_border_rgb), width=2)
    draw_centered_text(
        draw,
        text=str(title),
        center=(0.5 * (x0 + x1), y0 + 30),
        font=load_font(_DEFAULTS.panel_title_font_size_px, bold=True),
        fill=tuple(style.text_rgb),
        stroke_fill=tuple(style.text_stroke_rgb),
        stroke_width=1,
    )
    rows = len(state)
    cols = len(state[0])
    max_cell = int(min((x1 - x0 - 58) / cols, (y1 - y0 - 92) / rows))
    cell = int(min(cell_size or max_cell, max_cell))
    grid_w = cell * cols
    grid_h = cell * rows
    gx0 = int(round(0.5 * (x0 + x1 - grid_w)))
    gy0 = int(round(y0 + 62 + max(0, (y1 - y0 - 80 - grid_h) * 0.5)))
    off_rgb, on_rgb = _state_colors(style)
    pressed_lookup = {tuple(cell_value): index + 1 for index, cell_value in enumerate(pressed_cells)}
    switch_lookup = {(int(opt.row), int(opt.col)): str(opt.option_label) for opt in switch_options}
    cell_bboxes: Dict[str, List[float]] = {}
    for row in range(rows):
        for col in range(cols):
            cx0 = gx0 + col * cell
            cy0 = gy0 + row * cell
            cx1 = cx0 + cell
            cy1 = cy0 + cell
            fill = on_rgb if int(state[row][col]) else off_rgb
            draw.rectangle((cx0, cy0, cx1, cy1), fill=fill, outline=tuple(style.grid_rgb), width=2)
            key = f"cell_{row}_{col}"
            cell_bboxes[key] = [float(cx0), float(cy0), float(cx1), float(cy1)]
            if (row, col) in pressed_lookup:
                radius = max(10, int(cell * 0.24))
                center = (0.5 * (cx0 + cx1), 0.5 * (cy0 + cy1))
                draw.ellipse((center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius), outline=tuple(style.mark_rgb), width=4)
                draw_centered_text(
                    draw,
                    text=str(pressed_lookup[(row, col)]),
                    center=center,
                    font=load_font(max(14, int(cell * 0.28)), bold=True),
                    fill=tuple(style.text_rgb),
                    stroke_fill=tuple(style.text_stroke_rgb),
                    stroke_width=2,
                )
            if (row, col) in switch_lookup:
                bx0 = cx0 + 6
                by0 = cy0 + 6
                bx1 = min(cx1 - 6, bx0 + max(24, int(cell * 0.38)))
                by1 = min(cy1 - 6, by0 + max(24, int(cell * 0.38)))
                draw_rounded_rect(draw, (bx0, by0, bx1, by1), radius=7, fill=tuple(style.option_marker_fill_rgb), outline=tuple(style.panel_border_rgb), width=1)
                draw_centered_text(
                    draw,
                    text=switch_lookup[(row, col)],
                    center=(0.5 * (bx0 + bx1), 0.5 * (by0 + by1)),
                    font=load_font(max(13, int(cell * 0.22)), bold=True),
                    fill=tuple(style.text_rgb),
                    stroke_fill=tuple(style.text_stroke_rgb),
                    stroke_width=1,
                )
    return [float(x0), float(y0), float(x1), float(y1)], cell_bboxes


def _draw_result_options(
    draw: ImageDraw.ImageDraw,
    *,
    panel_bbox: Sequence[float],
    dataset: ToggleDataset,
    style: Any,
) -> Dict[str, List[float]]:
    x0, y0, x1, y1 = [int(round(float(value))) for value in panel_bbox]
    draw_rounded_rect(draw, (x0, y0, x1, y1), radius=18, fill=tuple(style.panel_fill_rgb), outline=tuple(style.panel_border_rgb), width=2)
    draw_centered_text(
        draw,
        text="Result options",
        center=(0.5 * (x0 + x1), y0 + 26),
        font=load_font(20, bold=True),
        fill=tuple(style.text_rgb),
        stroke_fill=tuple(style.text_stroke_rgb),
        stroke_width=1,
    )
    option_count = len(dataset.result_options)
    gap = 16
    pad = 22
    card_w = int((x1 - x0 - 2 * pad - (option_count - 1) * gap) / option_count)
    card_h = y1 - y0 - 72
    top = y0 + 52
    bboxes: Dict[str, List[float]] = {}
    for index, option in enumerate(dataset.result_options):
        bx0 = x0 + pad + index * (card_w + gap)
        by0 = top
        bx1 = bx0 + card_w
        by1 = top + card_h
        draw_rounded_rect(draw, (bx0, by0, bx1, by1), radius=12, fill=tuple(style.option_fill_rgb), outline=tuple(style.panel_border_rgb), width=2)
        draw_centered_text(
            draw,
            text=str(option.option_label),
            center=(bx0 + 20, by0 + 20),
            font=load_font(17, bold=True),
            fill=tuple(style.text_rgb),
            stroke_fill=tuple(style.text_stroke_rgb),
            stroke_width=1,
        )
        _draw_grid(
            draw,
            bbox=(bx0 + 10, by0 + 34, bx1 - 10, by1 - 10),
            title="",
            state=option.state,
            style=style,
            cell_size=_DEFAULTS.mini_cell_size_px,
        )
        bboxes[f"option_{option.option_label}"] = [float(bx0), float(by0), float(bx1), float(by1)]
    return bboxes


def _render_toggle_result_scene(*, dataset: ToggleDataset, params: Mapping[str, Any], instance_seed: int) -> Tuple[Image.Image, Dict[str, Any]]:
    width = _get_int(params, _RENDER_DEFAULTS_RESULT, "canvas_width", _DEFAULTS.canvas_width)
    height = _get_int(params, _RENDER_DEFAULTS_RESULT, "canvas_height", _DEFAULTS.canvas_height)
    style, style_meta = resolve_puzzle_scene_style(instance_seed=int(instance_seed), namespace=f"{TOGGLE_RESULT_TASK_ID}.toggle_grid")
    image, background_meta = make_puzzle_scene_background(canvas_width=int(width), canvas_height=int(height), style=style)
    draw = ImageDraw.Draw(image)
    start_bbox, start_cell_bboxes = _draw_grid(
        draw,
        bbox=(54, 54, int(width) - 54, 486),
        title="Start grid: press numbered switches",
        state=dataset.start_state,
        style=style,
        pressed_cells=dataset.pressed_cells,
        cell_size=_get_int(params, _RENDER_DEFAULTS_RESULT, "main_cell_size_px", _DEFAULTS.main_cell_size_px),
    )
    option_bboxes = _draw_result_options(draw, panel_bbox=(54, 532, int(width) - 54, int(height) - 54), dataset=dataset, style=style)
    return image, {
        "background_style": dict(background_meta),
        "scene_style": dict(style_meta),
        "start_grid_bbox_px": list(start_bbox),
        "start_cell_bboxes_px": dict(start_cell_bboxes),
        "option_panel_bboxes_px": dict(option_bboxes),
    }


def _render_toggle_repair_scene(*, dataset: ToggleDataset, params: Mapping[str, Any], instance_seed: int) -> Tuple[Image.Image, Dict[str, Any]]:
    width = _get_int(params, _RENDER_DEFAULTS_REPAIR, "canvas_width", _DEFAULTS.canvas_width)
    height = _get_int(params, _RENDER_DEFAULTS_REPAIR, "canvas_height", _DEFAULTS.canvas_height)
    style, style_meta = resolve_puzzle_scene_style(instance_seed=int(instance_seed), namespace=f"{TOGGLE_REPAIR_TASK_ID}.toggle_grid")
    image, background_meta = make_puzzle_scene_background(canvas_width=int(width), canvas_height=int(height), style=style)
    draw = ImageDraw.Draw(image)
    start_bbox, start_cell_bboxes = _draw_grid(
        draw,
        bbox=(54, 74, 540, int(height) - 74),
        title="Start grid: candidate switches",
        state=dataset.start_state,
        style=style,
        switch_options=dataset.switch_options,
        cell_size=_get_int(params, _RENDER_DEFAULTS_REPAIR, "main_cell_size_px", _DEFAULTS.main_cell_size_px),
    )
    target_bbox, target_cell_bboxes = _draw_grid(
        draw,
        bbox=(580, 74, int(width) - 54, int(height) - 74),
        title="Target grid after one press",
        state=dataset.target_state,
        style=style,
        cell_size=_get_int(params, _RENDER_DEFAULTS_REPAIR, "main_cell_size_px", _DEFAULTS.main_cell_size_px),
    )
    return image, {
        "background_style": dict(background_meta),
        "scene_style": dict(style_meta),
        "start_grid_bbox_px": list(start_bbox),
        "target_grid_bbox_px": list(target_bbox),
        "start_cell_bboxes_px": dict(start_cell_bboxes),
        "target_cell_bboxes_px": dict(target_cell_bboxes),
    }


def _prompt_defaults(task_id: str) -> Mapping[str, Any]:
    defaults = _PROMPT_DEFAULTS_RESULT if str(task_id) == TOGGLE_RESULT_TASK_ID else _PROMPT_DEFAULTS_REPAIR
    return required_group_defaults(
        defaults,
        (
            "bundle_id",
            "scene_key",
            "task_key",
            "object_description",
            "json_output_contract",
            "json_output_contract_answer_only",
            "answer_hint_option_letter",
            "annotation_hint",
            "json_example",
            "json_example_answer_only",
        ),
        context=f"prompt defaults for {task_id}",
    )


def _option_specs_for_result(options: Sequence[ResultOption]) -> List[Dict[str, Any]]:
    return [
        {
            "option_label": str(option.option_label),
            "state": [[int(value) for value in row] for row in option.state],
            "is_correct": bool(option.is_correct),
        }
        for option in options
    ]


def _option_specs_for_repair(options: Sequence[SwitchOption]) -> List[Dict[str, Any]]:
    return [
        {
            "option_label": str(option.option_label),
            "row": int(option.row),
            "col": int(option.col),
            "is_correct": bool(option.is_correct),
        }
        for option in options
    ]


class _ToggleBaseTask:
    domain = "puzzles"
    task_group = "logic"
    default_dataset_enabled = True
    task_id: str
    query_id: str

    def _prompt(self, *, prompt_defaults: Mapping[str, Any], instance_seed: int) -> Any:
        return build_prompt_trace_artifacts(
            render_task_prompt_variants(
                domain=self.domain,
                task_group=self.task_group,
                bundle_id=str(prompt_defaults["bundle_id"]),
                scene_key=str(prompt_defaults["scene_key"]),
                task_key=str(prompt_defaults["task_key"]),
                query_key=str(self.query_id),
                answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
                slots={
                    "object_description": str(prompt_defaults["object_description"]),
                    "json_output_contract": str(prompt_defaults["json_output_contract"]),
                    "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                    "annotation_hint": str(prompt_defaults["annotation_hint"]),
                    "answer_hint": str(prompt_defaults["answer_hint_option_letter"]),
                    "json_example": str(prompt_defaults["json_example"]),
                    "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
                },
                instance_seed=int(instance_seed),
            )
        )

    def _complexity(self, dataset: ToggleDataset) -> Any:
        grid_norm = normalize_int_with_bounds(int(dataset.rows) * int(dataset.cols), (16, 25))
        step_norm = normalize_int_with_bounds(len(dataset.pressed_cells), (1, 4))
        return build_puzzle_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": clamp_unit_interval(0.45 + 0.35 * grid_norm),
                "reasoning_load": clamp_unit_interval(0.50 + 0.30 * step_norm),
                "scene_variant_load": {"toggle_clean": 0.18, "toggle_notebook": 0.24, "toggle_console": 0.28}.get(str(dataset.scene_variant), 0.2),
            },
        )


@register_task
class PuzzlesLogicToggleResultLabelTask(_ToggleBaseTask):
    """Choose the result grid after pressing numbered toggle switches."""

    task_id = TOGGLE_RESULT_TASK_ID
    query_id = RESULT_QUERY_ID

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        dataset = _sample_result_dataset(params=params, instance_seed=int(instance_seed))
        image, render_meta = _render_toggle_result_scene(dataset=dataset, params=params, instance_seed=int(instance_seed))
        image, post_noise_meta = apply_post_image_noise(image, instance_seed=int(instance_seed), params=params, default_config=POST_IMAGE_NOISE_DEFAULTS)
        prompt_defaults = _prompt_defaults(self.task_id)
        prompt_artifacts = self._prompt(prompt_defaults=prompt_defaults, instance_seed=int(instance_seed))
        option_bbox = render_meta["option_panel_bboxes_px"][f"option_{dataset.correct_option_label}"]
        annotation_bboxes = [
            [round(float(value), 3) for value in render_meta["start_grid_bbox_px"]],
            [round(float(value), 3) for value in option_bbox],
        ]
        answer_gt = TypedValue(type="option_letter", value=str(dataset.correct_option_label))
        annotation_gt = TypedValue(type="bbox_set", value=list(annotation_bboxes))
        complexity = self._complexity(dataset)
        option_specs = _option_specs_for_result(dataset.result_options)
        trace_payload = {
            "scene_ir": {"scene_kind": "puzzle_toggle_grid", "scene_id": SCENE_ID, "task_id": self.task_id},
            "query_spec": {
                "scene_id": SCENE_ID,
                "query_id": RESULT_QUERY_ID,
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {"query_id": RESULT_QUERY_ID, "scene_variant": str(dataset.scene_variant)},
            },
            "render_spec": {
                "canvas_width": int(image.width),
                "canvas_height": int(image.height),
                "coord_space": "pixel",
                "scene_id": SCENE_ID,
                "query_id": RESULT_QUERY_ID,
                "scene_variant": str(dataset.scene_variant),
                "post_image_noise": dict(post_noise_meta),
                **dict(render_meta),
            },
            "render_map": {"image_id": "img0", **dict(render_meta), "annotation_source": "start_grid_bbox_px+option_panel_bboxes_px"},
            "execution_trace": {
                "scene_id": SCENE_ID,
                "query_id": RESULT_QUERY_ID,
                "scene_variant": str(dataset.scene_variant),
                "rows": int(dataset.rows),
                "cols": int(dataset.cols),
                "start_state": [[int(value) for value in row] for row in dataset.start_state],
                "pressed_cells": [[int(row), int(col)] for row, col in dataset.pressed_cells],
                "target_state": [[int(value) for value in row] for row in dataset.target_state],
                "option_specs": option_specs,
                "answer_value": str(dataset.correct_option_label),
                "toggle_rule": "pressing a switch toggles that cell and its orthogonal neighbors",
            },
            "witness_symbolic": {"type": "toggle_grid_result", "value": {"pressed_cells": [[int(r), int(c)] for r, c in dataset.pressed_cells]}},
            "projected_annotation": {"bbox_set": list(annotation_bboxes)},
            "answer_gt": answer_gt.to_dict(),
            "annotation_gt": annotation_gt.to_dict(),
            "complexity": complexity.to_dict(),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=RESULT_QUERY_ID,
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class PuzzlesLogicToggleRepairSwitchLabelTask(_ToggleBaseTask):
    """Choose the one candidate switch that turns the start grid into the target grid."""

    task_id = TOGGLE_REPAIR_TASK_ID
    query_id = REPAIR_QUERY_ID

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        dataset = _sample_repair_dataset(params=params, instance_seed=int(instance_seed))
        image, render_meta = _render_toggle_repair_scene(dataset=dataset, params=params, instance_seed=int(instance_seed))
        image, post_noise_meta = apply_post_image_noise(image, instance_seed=int(instance_seed), params=params, default_config=POST_IMAGE_NOISE_DEFAULTS)
        prompt_defaults = _prompt_defaults(self.task_id)
        prompt_artifacts = self._prompt(prompt_defaults=prompt_defaults, instance_seed=int(instance_seed))
        correct = next(option for option in dataset.switch_options if bool(option.is_correct))
        switch_bbox = render_meta["start_cell_bboxes_px"][f"cell_{correct.row}_{correct.col}"]
        annotation_bboxes = [
            [round(float(value), 3) for value in render_meta["start_grid_bbox_px"]],
            [round(float(value), 3) for value in render_meta["target_grid_bbox_px"]],
            [round(float(value), 3) for value in switch_bbox],
        ]
        answer_gt = TypedValue(type="option_letter", value=str(dataset.correct_option_label))
        annotation_gt = TypedValue(type="bbox_set", value=list(annotation_bboxes))
        complexity = self._complexity(dataset)
        option_specs = _option_specs_for_repair(dataset.switch_options)
        trace_payload = {
            "scene_ir": {"scene_kind": "puzzle_toggle_grid", "scene_id": SCENE_ID, "task_id": self.task_id},
            "query_spec": {
                "scene_id": SCENE_ID,
                "query_id": REPAIR_QUERY_ID,
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {"query_id": REPAIR_QUERY_ID, "scene_variant": str(dataset.scene_variant)},
            },
            "render_spec": {
                "canvas_width": int(image.width),
                "canvas_height": int(image.height),
                "coord_space": "pixel",
                "scene_id": SCENE_ID,
                "query_id": REPAIR_QUERY_ID,
                "scene_variant": str(dataset.scene_variant),
                "post_image_noise": dict(post_noise_meta),
                **dict(render_meta),
            },
            "render_map": {"image_id": "img0", **dict(render_meta), "annotation_source": "start_grid_bbox_px+target_grid_bbox_px+start_cell_bboxes_px"},
            "execution_trace": {
                "scene_id": SCENE_ID,
                "query_id": REPAIR_QUERY_ID,
                "scene_variant": str(dataset.scene_variant),
                "rows": int(dataset.rows),
                "cols": int(dataset.cols),
                "start_state": [[int(value) for value in row] for row in dataset.start_state],
                "target_state": [[int(value) for value in row] for row in dataset.target_state],
                "candidate_switch_specs": option_specs,
                "pressed_cells": [[int(row), int(col)] for row, col in dataset.pressed_cells],
                "answer_value": str(dataset.correct_option_label),
                "toggle_rule": "pressing a switch toggles that cell and its orthogonal neighbors",
            },
            "witness_symbolic": {"type": "toggle_grid_repair_switch", "value": {"correct_cell": [int(correct.row), int(correct.col)]}},
            "projected_annotation": {"bbox_set": list(annotation_bboxes)},
            "answer_gt": answer_gt.to_dict(),
            "annotation_gt": annotation_gt.to_dict(),
            "complexity": complexity.to_dict(),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=REPAIR_QUERY_ID,
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
