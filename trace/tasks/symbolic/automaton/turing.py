"""Turing tape automaton symbolic task."""

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
    TURING_SYMBOL_COUNT_TASK_ID,
    TURING_SCENE_ID,
    TURING_QUERY_IDS,
    _TURING_SYMBOLS,
    _TURING_MOVES,
    POST_IMAGE_NOISE_DEFAULTS,
    _RenderParams,
    _RenderedScene,
    _load_defaults,
    _resolve_render_params,
    _resolve_turing_style,
    _resolve_query,
    _decorrelated_selection_index,
    _grid_bbox,
    _cell_bbox,
    _decorate_panel,
    _build_prompt,
    _common_trace,
    _round_bboxes,
    _BaseAutomatonTask,
)


@dataclass(frozen=True)
class _TuringTransition:
    state: str
    read_symbol: str
    write_symbol: str
    move: str
    next_state: str


@dataclass(frozen=True)
class _TuringTrace:
    step: int
    state: str
    head_position: int
    read_symbol: str
    write_symbol: str
    move: str
    next_state: str


@dataclass(frozen=True)
class _TuringDataset:
    tape_length: int
    symbol_count: int
    symbols: Tuple[str, ...]
    query_id: str
    query_symbol: str
    steps: int
    states: Tuple[str, ...]
    start_state: str
    start_head: int
    initial_tape: Tuple[str, ...]
    final_tape: Tuple[str, ...]
    transitions: Tuple[_TuringTransition, ...]
    traces: Tuple[_TuringTrace, ...]
    answer_count: int


def _move_delta(move: str) -> int:
    return -1 if str(move) == "L" else 1


def _sample_turing_head_path(
    rng,
    *,
    tape_length: int,
    steps: int,
) -> Tuple[int, Tuple[str, ...], Tuple[int, ...]]:
    for _attempt in range(200):
        head = int(rng.randrange(1, max(2, int(tape_length) - 1)))
        positions: List[int] = []
        moves: List[str] = []
        for _step in range(int(steps)):
            allowed: List[str] = []
            if head > 0:
                allowed.append("L")
            if head < int(tape_length) - 1:
                allowed.append("R")
            move = str(rng.choice(allowed or list(_TURING_MOVES)))
            positions.append(int(head))
            moves.append(move)
            head += _move_delta(move)
        if len(set(positions)) >= min(3, int(steps)):
            return int(positions[0]), tuple(moves), tuple(positions)
    start = int(max(1, min(int(tape_length) - 2, int(tape_length) // 2)))
    positions = []
    moves = []
    head = start
    direction = 1
    for _step in range(int(steps)):
        positions.append(int(head))
        if head >= int(tape_length) - 2:
            direction = -1
        elif head <= 1:
            direction = 1
        move = "R" if direction > 0 else "L"
        moves.append(move)
        head += _move_delta(move)
    return int(start), tuple(moves), tuple(positions)


def _transition_key(transition: _TuringTransition) -> Tuple[str, str]:
    return (str(transition.state), str(transition.read_symbol))


def _simulate_turing(
    *,
    initial_tape: Sequence[str],
    start_state: str,
    start_head: int,
    transitions: Sequence[_TuringTransition],
    steps: int,
) -> Tuple[Tuple[str, ...], Tuple[_TuringTrace, ...]]:
    table = {_transition_key(transition): transition for transition in transitions}
    tape = [str(symbol) for symbol in initial_tape]
    state = str(start_state)
    head = int(start_head)
    traces: List[_TuringTrace] = []
    for step in range(1, int(steps) + 1):
        read_symbol = str(tape[head])
        transition = table[(state, read_symbol)]
        tape[head] = str(transition.write_symbol)
        traces.append(
            _TuringTrace(
                step=int(step),
                state=str(state),
                head_position=int(head),
                read_symbol=str(read_symbol),
                write_symbol=str(transition.write_symbol),
                move=str(transition.move),
                next_state=str(transition.next_state),
            )
        )
        head = max(0, min(len(tape) - 1, int(head + _move_delta(str(transition.move)))))
        state = str(transition.next_state)
    return tuple(tape), tuple(traces)


def _build_turing_dataset(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    query_id: str,
) -> _TuringDataset:
    rng = spawn_rng(int(instance_seed), f"{task_id}.turing")
    tape_min, tape_max = _get_range(params, gen_defaults, min_key="turing_tape_length_min", max_key="turing_tape_length_max", fallback_min=8, fallback_max=11)
    steps_min, steps_max = _get_range(params, gen_defaults, min_key="turing_steps_min", max_key="turing_steps_max", fallback_min=3, fallback_max=6)
    symbol_min, symbol_max = _get_range(params, gen_defaults, min_key="turing_symbol_count_min", max_key="turing_symbol_count_max", fallback_min=2, fallback_max=2)
    answer_min, answer_max = _get_range(params, gen_defaults, min_key="turing_answer_min", max_key="turing_answer_max", fallback_min=1, fallback_max=7)
    symbol_count = int(max(2, min(len(_TURING_SYMBOLS), rng.randint(symbol_min, symbol_max))))
    symbols = tuple(_TURING_SYMBOLS[:symbol_count])
    tape_length = int(rng.randint(tape_min, tape_max))
    max_answer = int(min(answer_max, tape_length - 1))
    answer_support = list(range(int(answer_min), int(max_answer) + 1))
    if not answer_support:
        answer_support = [max(0, min(tape_length, int(answer_min)))]
    desired_answer = int(
        answer_support[
            int(
                _decorrelated_selection_index(
                    params=params,
                    instance_seed=int(instance_seed),
                    namespace=f"{task_id}.{query_id}.desired_answer_count",
                )
            )
            % len(answer_support)
        ]
    )
    query_symbol = str(symbols[int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{task_id}.query_symbol")) % len(symbols)])
    steps = int(rng.randint(steps_min, steps_max))
    states = tuple(f"S{index}" for index in range(int(steps)))
    start_state = states[0]
    start_head, planned_moves, planned_positions = _sample_turing_head_path(rng, tape_length=tape_length, steps=steps)

    final_tape: List[str] = [str(rng.choice([symbol for symbol in symbols if symbol != query_symbol])) for _ in range(tape_length)]
    query_positions = list(range(tape_length))
    rng.shuffle(query_positions)
    for pos in query_positions[:desired_answer]:
        final_tape[int(pos)] = str(query_symbol)

    initial_tape = list(final_tape)
    first_visit_positions = []
    seen_positions: set[int] = set()
    for pos in planned_positions:
        if int(pos) not in seen_positions:
            first_visit_positions.append(int(pos))
            seen_positions.add(int(pos))
    for pos in first_visit_positions:
        if rng.random() < 0.65:
            alternatives = [symbol for symbol in symbols if str(symbol) != str(final_tape[pos])]
            initial_tape[pos] = str(rng.choice(alternatives))
    if first_visit_positions and all(str(initial_tape[pos]) == str(final_tape[pos]) for pos in first_visit_positions):
        pos = int(first_visit_positions[0])
        alternatives = [symbol for symbol in symbols if str(symbol) != str(final_tape[pos])]
        initial_tape[pos] = str(alternatives[0])

    transitions_by_key: Dict[Tuple[str, str], _TuringTransition] = {}
    tape = list(initial_tape)
    for step_index, (position, move) in enumerate(zip(planned_positions, planned_moves)):
        state = str(states[step_index])
        read_symbol = str(tape[int(position)])
        write_symbol = str(final_tape[int(position)])
        next_state = str(states[step_index + 1]) if step_index + 1 < len(states) else str(states[0])
        transition = _TuringTransition(
            state=state,
            read_symbol=read_symbol,
            write_symbol=write_symbol,
            move=str(move),
            next_state=next_state,
        )
        transitions_by_key[(state, read_symbol)] = transition
        tape[int(position)] = write_symbol

    for state in states:
        for symbol in symbols:
            key = (str(state), str(symbol))
            if key in transitions_by_key:
                continue
            transitions_by_key[key] = _TuringTransition(
                state=str(state),
                read_symbol=str(symbol),
                write_symbol=str(rng.choice(symbols)),
                move=str(rng.choice(_TURING_MOVES)),
                next_state=str(rng.choice(states)),
            )

    transitions = tuple(
        transitions_by_key[(str(state), str(symbol))]
        for state in states
        for symbol in symbols
    )
    simulated_final_tape, traces = _simulate_turing(
        initial_tape=initial_tape,
        start_state=start_state,
        start_head=start_head,
        transitions=transitions,
        steps=steps,
    )
    answer_count = int(sum(1 for symbol in simulated_final_tape if str(symbol) == str(query_symbol)))
    if answer_count != desired_answer:
        raise RuntimeError(f"constructed Turing tape answer mismatch: {answer_count} != {desired_answer}")
    return _TuringDataset(
        tape_length=int(tape_length),
        symbol_count=int(symbol_count),
        symbols=tuple(symbols),
        query_id=str(query_id),
        query_symbol=str(query_symbol),
        steps=int(steps),
        states=tuple(states),
        start_state=str(start_state),
        start_head=int(start_head),
        initial_tape=tuple(str(symbol) for symbol in initial_tape),
        final_tape=tuple(str(symbol) for symbol in simulated_final_tape),
        transitions=transitions,
        traces=traces,
        answer_count=int(answer_count),
    )


def _draw_turing_tape(
    draw: ImageDraw.ImageDraw,
    *,
    dataset: _TuringDataset,
    left: int,
    top: int,
    cell_size: int,
    gap: int,
    item_bboxes: Dict[str, Tuple[int, int, int, int]],
    style: SymbolicSceneStyle,
) -> Tuple[int, int, int, int]:
    font = load_font(max(16, int(cell_size * 0.42)), bold=True)
    small_font = load_font(max(11, int(cell_size * 0.22)), bold=True)
    symbol_to_color = {
        symbol: tuple(style.state_colors[index % len(style.state_colors)])
        for index, symbol in enumerate(dataset.symbols)
    }
    for index, symbol in enumerate(dataset.initial_tape):
        bbox = (
            int(left + index * (cell_size + gap)),
            int(top),
            int(left + index * (cell_size + gap) + cell_size),
            int(top + cell_size),
        )
        item_bboxes[f"tape_cell_{index}"] = bbox
        draw_symbolic_grid_cell(
            draw,
            bbox=bbox,
            fill=symbol_to_color[str(symbol)],
            style=style,
            outline=style.grid_rgb,
            width=2,
            selected=int(index) == int(dataset.start_head),
            selected_width=max(3, int(cell_size * 0.09)),
        )
        draw_centered_text(
            draw,
            text=str(symbol),
            center=((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0),
            font=font,
            fill=style.text_rgb,
            stroke_fill=style.text_stroke_rgb,
            stroke_width=1,
        )
        draw_centered_text(
            draw,
            text=str(index + 1),
            center=((bbox[0] + bbox[2]) / 2.0, bbox[3] + max(11, int(cell_size * 0.18))),
            font=small_font,
            fill=style.text_rgb,
            stroke_fill=style.text_stroke_rgb,
            stroke_width=1,
        )
    tape_bbox = _grid_bbox(left=left, top=top, rows=1, cols=int(dataset.tape_length), cell_size=cell_size, gap=gap)
    item_bboxes["source_tape"] = (int(tape_bbox[0]), int(tape_bbox[1]), int(tape_bbox[2]), int(tape_bbox[3] + max(18, int(cell_size * 0.30))))
    head_cell = _cell_bbox(left=left, top=top, row=0, col=int(dataset.start_head), cell_size=cell_size, gap=gap)
    head_cx = int((head_cell[0] + head_cell[2]) / 2)
    arrow_top = int(head_cell[1] - max(32, int(cell_size * 0.48)))
    arrow_end = int(head_cell[1] - 5)
    draw_arrow(
        draw,
        start=(head_cx, arrow_top),
        end=(head_cx, arrow_end),
        fill=style.agent_rgb,
        width=max(3, int(cell_size * 0.08)),
        head_length_px=max(12, int(cell_size * 0.22)),
        head_width_px=max(14, int(cell_size * 0.24)),
    )
    head_label_bbox = (
        int(head_cx - cell_size * 0.65),
        int(arrow_top - max(22, int(cell_size * 0.30))),
        int(head_cx + cell_size * 0.65),
        int(arrow_top - 2),
    )
    draw_rounded_rect(draw, head_label_bbox, radius=8, fill=style.panel_accent_rgb, outline=style.panel_border_rgb, width=1)
    draw_centered_text(
        draw,
        text=f"HEAD {dataset.start_state}",
        center=((head_label_bbox[0] + head_label_bbox[2]) / 2.0, (head_label_bbox[1] + head_label_bbox[3]) / 2.0),
        font=small_font,
        fill=style.text_rgb,
        stroke_fill=style.text_stroke_rgb,
        stroke_width=1,
    )
    item_bboxes["start_head"] = (
        int(min(head_label_bbox[0], head_cell[0])),
        int(head_label_bbox[1]),
        int(max(head_label_bbox[2], head_cell[2])),
        int(head_cell[1]),
    )
    return item_bboxes["source_tape"]


def _draw_turing_transition_table(
    draw: ImageDraw.ImageDraw,
    *,
    dataset: _TuringDataset,
    left: int,
    top: int,
    row_height: int,
    style: SymbolicSceneStyle,
) -> Tuple[int, int, int, int]:
    col_widths = (76, 70, 72, 70, 84)
    headers = ("State", "Read", "Write", "Move", "Next")
    table_width = int(sum(col_widths))
    header_font = load_font(max(12, int(row_height * 0.42)), bold=True)
    cell_font = load_font(max(12, int(row_height * 0.42)), bold=False)
    x = int(left)
    y = int(top)
    header_bbox = (x, y, x + table_width, y + row_height)
    draw_rounded_rect(draw, header_bbox, radius=10, fill=style.panel_accent_rgb, outline=style.panel_border_rgb, width=2)
    cursor = x
    for width, header in zip(col_widths, headers):
        draw_centered_text(
            draw,
            text=header,
            center=(cursor + width / 2, y + row_height / 2),
            font=header_font,
            fill=style.text_rgb,
            stroke_fill=style.text_stroke_rgb,
            stroke_width=1,
        )
        cursor += int(width)
    used_keys = {(trace.state, trace.read_symbol) for trace in dataset.traces}
    for row_index, transition in enumerate(dataset.transitions, 1):
        y0 = int(top + row_index * row_height)
        row_bbox = (x, y0, x + table_width, y0 + row_height)
        row_fill = style.option_marker_fill_rgb if (transition.state, transition.read_symbol) in used_keys else style.option_fill_rgb
        draw.rectangle(row_bbox, fill=row_fill, outline=style.grid_rgb, width=1)
        values = (
            transition.state,
            transition.read_symbol,
            transition.write_symbol,
            transition.move,
            transition.next_state,
        )
        cursor = x
        for width, value in zip(col_widths, values):
            draw_centered_text(
                draw,
                text=str(value),
                center=(cursor + width / 2, y0 + row_height / 2),
                font=cell_font,
                fill=style.text_rgb,
                stroke_fill=style.text_stroke_rgb,
                stroke_width=1,
            )
            cursor += int(width)
    return (x, y, x + table_width, int(top + (len(dataset.transitions) + 1) * row_height))


def _render_turing_scene(
    *,
    background: Image.Image,
    dataset: _TuringDataset,
    scene_variant: str,
    render_params: _RenderParams,
    style: SymbolicSceneStyle | None = None,
    style_meta: Mapping[str, Any] | None = None,
) -> _RenderedScene:
    image = background.copy()
    draw = ImageDraw.Draw(image)
    item_bboxes: Dict[str, Tuple[int, int, int, int]] = {}
    if style is None or style_meta is None:
        style, style_meta = _resolve_turing_style(scene_variant=str(scene_variant), render_params=render_params)
    cell = max(38, min(60, int(render_params.cell_size_px)))
    gap = max(2, int(render_params.grid_gap_px))
    tape_width = int(dataset.tape_length * cell + max(0, dataset.tape_length - 1) * gap)
    tape_left = int((render_params.canvas_width - tape_width) // 2)
    tape_top = max(96, int(render_params.panel_padding_px) + 72)
    machine_panel = (
        int(tape_left - render_params.panel_padding_px),
        int(tape_top - render_params.panel_padding_px - 62),
        int(tape_left + tape_width + render_params.panel_padding_px),
        int(tape_top + cell + render_params.panel_padding_px + 46),
    )
    _decorate_panel(
        draw,
        bbox=machine_panel,
        scene_variant=str(scene_variant),
        radius=int(render_params.panel_corner_radius_px),
        border_width=int(render_params.panel_border_width_px),
        style=style,
        chrome_mode=str(style_meta.get("panel_chrome_mode", "accent_frame")),
    )
    _draw_turing_tape(
        draw,
        dataset=dataset,
        left=tape_left,
        top=tape_top,
        cell_size=cell,
        gap=gap,
        item_bboxes=item_bboxes,
        style=style,
    )
    chip_font = load_font(max(13, int(render_params.small_font_size_px)), bold=True)
    chip_y = int(machine_panel[3] - render_params.panel_padding_px - 22)
    chips = (
        f"steps {dataset.steps}",
        f"count {dataset.query_symbol}",
    )
    chip_x = int(machine_panel[0] + render_params.panel_padding_px)
    query_chip_bbox = (0, 0, 0, 0)
    for chip in chips:
        chip_w = max(82, 16 + len(chip) * max(8, int(render_params.small_font_size_px * 0.52)))
        bbox = (chip_x, chip_y, int(chip_x + chip_w), int(chip_y + 28))
        draw_rounded_rect(draw, bbox, radius=10, fill=style.step_fill_rgb, outline=style.panel_border_rgb, width=1)
        draw_centered_text(
            draw,
            text=chip,
            center=((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2),
            font=chip_font,
            fill=style.text_rgb,
            stroke_fill=style.text_stroke_rgb,
            stroke_width=1,
        )
        if chip.startswith("count "):
            query_chip_bbox = bbox
        chip_x += int(chip_w + 12)
    item_bboxes["machine_panel"] = machine_panel
    item_bboxes["query_symbol"] = query_chip_bbox

    row_height = max(28, min(36, int(render_params.cell_size_px * 0.58)))
    table_width = 372
    table_left = int((render_params.canvas_width - table_width) // 2)
    table_top = int(machine_panel[3] + 34)
    table_bbox_raw = _draw_turing_transition_table(
        draw,
        dataset=dataset,
        left=table_left,
        top=table_top,
        row_height=row_height,
        style=style,
    )
    table_panel = (
        int(table_bbox_raw[0] - 18),
        int(table_bbox_raw[1] - 18),
        int(table_bbox_raw[2] + 18),
        int(table_bbox_raw[3] + 18),
    )
    table_crop = image.crop(table_bbox_raw)
    _decorate_panel(
        draw,
        bbox=table_panel,
        scene_variant=str(scene_variant),
        radius=int(render_params.panel_corner_radius_px),
        border_width=2,
        style=style,
        chrome_mode="plain_panel",
    )
    image.paste(table_crop, table_bbox_raw)
    item_bboxes["transition_table"] = table_panel
    scene_bbox = (
        int(min(machine_panel[0], table_panel[0])),
        int(min(machine_panel[1], table_panel[1])),
        int(max(machine_panel[2], table_panel[2])),
        int(max(machine_panel[3], table_panel[3])),
    )
    entities = tuple(
        {
            "entity_id": key,
            "bbox_px": list(value),
            "entity_type": "turing_machine_item",
        }
        for key, value in sorted(item_bboxes.items())
    )
    return _RenderedScene(
        image=image,
        scene_bbox_px=scene_bbox,
        item_bboxes=item_bboxes,
        entities=entities,
        layout_jitter={
            "enabled": False,
            "reason": "single_tape_and_table_layout",
            "canvas_size_px": [int(render_params.canvas_width), int(render_params.canvas_height)],
            "tape_cell_size_px": int(cell),
            "transition_row_height_px": int(row_height),
        },
        style_metadata=dict(style_meta),
    )


@register_task
class SymbolicAutomatonTuringWrittenSymbolCountTask(_BaseAutomatonTask):
    """Count a queried tape symbol after fixed-step Turing-style transitions."""

    task_id = TURING_SYMBOL_COUNT_TASK_ID
    supported_query_ids = TURING_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id, query_probabilities = _resolve_query(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
            supported_queries=TURING_QUERY_IDS,
        )
        scene_variant, scene_probs = self._scene_variant(params=params, gen_defaults=gen_defaults, instance_seed=int(instance_seed))
        dataset = _build_turing_dataset(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
            query_id=query_id,
        )
        render_params = _resolve_render_params(params, render_defaults, instance_seed=int(instance_seed))
        style, style_meta = _resolve_turing_style(scene_variant=str(scene_variant), render_params=render_params)
        background, background_meta = make_symbolic_scene_background(
            canvas_width=render_params.canvas_width,
            canvas_height=render_params.canvas_height,
            style=style,
        )
        rendered = _render_turing_scene(
            background=background,
            dataset=dataset,
            scene_variant=scene_variant,
            render_params=render_params,
            style=style,
            style_meta=style_meta,
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
            extra_slots={
                "query_symbol": str(dataset.query_symbol),
                "start_state": str(dataset.start_state),
            },
        )
        annotation_ids = ["machine_panel", "transition_table"]
        annotation_bboxes = _round_bboxes(projected_symbolic_bbox_annotation(rendered.item_bboxes, annotation_ids))
        answer_gt = TypedValue(type="integer", value=int(dataset.answer_count))
        annotation_gt = TypedValue(type="bbox_set", value=list(annotation_bboxes))
        execution_trace = {
            "steps": int(dataset.steps),
            "tape_length": int(dataset.tape_length),
            "symbol_count": int(dataset.symbol_count),
            "symbols": list(dataset.symbols),
            "query_symbol": str(dataset.query_symbol),
            "start_state": str(dataset.start_state),
            "start_head": int(dataset.start_head),
            "initial_tape": list(dataset.initial_tape),
            "final_tape": list(dataset.final_tape),
            "transitions": [
                {
                    "state": transition.state,
                    "read_symbol": transition.read_symbol,
                    "write_symbol": transition.write_symbol,
                    "move": transition.move,
                    "next_state": transition.next_state,
                }
                for transition in dataset.transitions
            ],
            "step_trace": [
                {
                    "step": trace.step,
                    "state": trace.state,
                    "head_position": trace.head_position,
                    "read_symbol": trace.read_symbol,
                    "write_symbol": trace.write_symbol,
                    "move": trace.move,
                    "next_state": trace.next_state,
                }
                for trace in dataset.traces
            ],
            "answer_count": int(dataset.answer_count),
            "supporting_item_ids": list(annotation_ids),
        }
        trace_payload = _common_trace(
            scene_id=TURING_SCENE_ID,
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
            answer_value=int(dataset.answer_count),
            execution_trace=execution_trace,
        )
        return TaskOutput(
            prompt=prompt,
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=TURING_SCENE_ID,
            query_id=query_id,
            prompt_variants=prompt_variants,
        )


__all__ = [
    'SymbolicAutomatonTuringWrittenSymbolCountTask',
]
