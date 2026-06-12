"""Shared primitives for symbolic automaton tasks."""

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

AGENT_FINAL_TASK_ID = "task_symbolic__agent_automaton__agent_final_pose_label"

AGENT_FLIP_TASK_ID = "task_symbolic__agent_automaton__agent_cell_flip_count"

LIFE_GRID_TASK_ID = "task_symbolic__life_automaton__life_future_grid_label"

LIFE_POP_TASK_ID = "task_symbolic__life_automaton__life_population_count"

TURING_SYMBOL_COUNT_TASK_ID = "task_symbolic__turing_tape__turing_written_symbol_count"

AGENT_SCENE_ID = "agent_automaton"

LIFE_SCENE_ID = "life_automaton"

TURING_SCENE_ID = "turing_tape"

AGENT_FINAL_QUERY_IDS: Tuple[str, ...] = ("binary_rule_final_pose", "three_state_rule_final_pose")

AGENT_FLIP_QUERY_IDS: Tuple[str, ...] = ("marked_region_flip_count",)

LIFE_GRID_QUERY_IDS: Tuple[str, ...] = ("one_step_future_grid", "two_step_future_grid")

LIFE_POP_QUERY_IDS: Tuple[str, ...] = ("marked_line_live_count",)

TURING_QUERY_IDS: Tuple[str, ...] = ("written_symbol_count",)

_SCENE_VARIANTS: Tuple[str, ...] = ("clean_grid", "lab_panel", "notebook_grid")

_DIRECTIONS: Tuple[str, ...] = ("up", "right", "down", "left")

_DIR_VEC: Tuple[Tuple[int, int], ...] = ((-1, 0), (0, 1), (1, 0), (0, -1))

_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

_TURING_SYMBOLS: Tuple[str, ...] = ("0", "1", "2")

_TURING_MOVES: Tuple[str, str] = ("L", "R")

_AGENT_STATE_COLORS: Tuple[Tuple[int, int, int], ...] = (
    (246, 248, 252),
    (84, 134, 207),
    (82, 169, 116),
)

_LIFE_DEAD_RGB = (247, 248, 250)

_LIFE_ALIVE_RGB = (35, 42, 54)

_GRID_RGB = (87, 96, 111)

_PANEL_RGB = (251, 252, 254)

_PANEL_BORDER_RGB = (87, 96, 111)

_TEXT_RGB = (28, 33, 42)

_TEXT_STROKE_RGB = (255, 255, 255)

_MARK_RGB = (235, 91, 66)

_AGENT_RGB = (218, 58, 74)

_OPTION_FILL_RGB = (250, 251, 254)

_OPTION_SELECTED_RGB = (239, 246, 255)

_AGENT_STYLE_TREATMENTS: Tuple[str, ...] = tuple(SYMBOLIC_SCENE_TREATMENTS)

_AGENT_BOARD_STYLES: Tuple[str, ...] = (
    "classic_grid",
    "rounded_tiles",
    "inset_cells",
    "lab_matrix",
    "notebook_cells",
)

_LIFE_BOARD_STYLES: Tuple[str, ...] = (
    "classic_grid",
    "rounded_tiles",
    "inset_tiles",
    "lab_matrix",
    "notebook_cells",
    "terminal_cells",
)

_LIFE_CELL_PALETTES: Dict[str, Dict[str, Tuple[int, int, int]]] = {
    "mono_ink": {
        "dead": (247, 248, 250),
        "alive": (35, 42, 54),
        "grid": (90, 101, 116),
        "edge": (68, 79, 94),
        "mark": (230, 73, 82),
        "accent": (188, 201, 218),
    },
    "blueprint_cells": {
        "dead": (239, 247, 254),
        "alive": (19, 55, 96),
        "grid": (73, 111, 150),
        "edge": (36, 82, 126),
        "mark": (230, 94, 55),
        "accent": (171, 203, 232),
    },
    "forest_cells": {
        "dead": (240, 249, 243),
        "alive": (20, 76, 58),
        "grid": (82, 129, 105),
        "edge": (44, 97, 77),
        "mark": (205, 69, 88),
        "accent": (180, 216, 194),
    },
    "plum_cells": {
        "dead": (250, 244, 251),
        "alive": (72, 35, 88),
        "grid": (126, 94, 141),
        "edge": (94, 63, 110),
        "mark": (35, 135, 168),
        "accent": (218, 193, 226),
    },
    "sepia_cells": {
        "dead": (252, 247, 236),
        "alive": (78, 51, 34),
        "grid": (142, 114, 82),
        "edge": (105, 82, 58),
        "mark": (202, 70, 61),
        "accent": (224, 204, 170),
    },
    "teal_cells": {
        "dead": (238, 250, 248),
        "alive": (16, 78, 85),
        "grid": (72, 132, 136),
        "edge": (36, 100, 106),
        "mark": (211, 70, 92),
        "accent": (172, 219, 218),
    },
    "burgundy_cells": {
        "dead": (252, 243, 245),
        "alive": (96, 30, 48),
        "grid": (145, 85, 100),
        "edge": (113, 55, 71),
        "mark": (0, 128, 158),
        "accent": (228, 192, 201),
    },
    "carbon_cells": {
        "dead": (246, 246, 242),
        "alive": (19, 22, 26),
        "grid": (92, 96, 101),
        "edge": (61, 66, 73),
        "mark": (226, 78, 66),
        "accent": (199, 202, 202),
    },
}

_TASK_GROUP_DEFAULTS = get_scene_defaults("symbolic", "automaton")

POST_IMAGE_BACKGROUND_DEFAULTS = load_symbolic_background_defaults(scene_id="automaton")

POST_IMAGE_NOISE_DEFAULTS = load_symbolic_noise_defaults(scene_id="automaton", apply_prob=0.5)

@dataclass(frozen=True)
class _RenderParams:
    canvas_width: int
    canvas_height: int
    cell_size_px: int
    grid_gap_px: int
    panel_padding_px: int
    panel_corner_radius_px: int
    panel_border_width_px: int
    grid_line_width_px: int
    option_card_width_px: int
    option_card_height_px: int
    option_gap_px: int
    option_grid_cell_px: int
    label_font_size_px: int
    small_font_size_px: int
    arrow_width_px: int
    unit_size_jitter: Dict[str, Any]
    layout_seed: int
    font_family: str

@dataclass(frozen=True)
class _RenderedScene:
    image: Image.Image
    scene_bbox_px: Tuple[int, int, int, int]
    item_bboxes: Dict[str, Tuple[int, int, int, int]]
    entities: Tuple[Dict[str, Any], ...]
    layout_jitter: Dict[str, Any]
    style_metadata: Dict[str, Any]

def _load_defaults(task_id: str) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, float]]:
    return load_symbolic_task_defaults(_TASK_GROUP_DEFAULTS, task_id=str(task_id))

def _resolve_render_params(
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    *,
    instance_seed: int,
) -> _RenderParams:
    # Preserve legacy puzzle seed namespaces so domain-split cleanup does not
    # change already-calibrated symbolic automaton samples for the same seed.
    unit_scale, unit_meta = resolve_symbolic_unit_size_scale(
        params,
        render_defaults,
        instance_seed=int(instance_seed),
        namespace="puzzles.automaton.unit_size",
    )
    font_params = {**dict(render_defaults), **dict(params)}
    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace="puzzles.automaton.font",
        params=font_params,
    )
    return _RenderParams(
        canvas_width=int(group_default(render_defaults, "canvas_width", 1040)),
        canvas_height=int(group_default(render_defaults, "canvas_height", 880)),
        cell_size_px=scale_symbolic_px(group_default(render_defaults, "cell_size_px", 54), unit_scale, min_px=28),
        grid_gap_px=scale_symbolic_px(group_default(render_defaults, "grid_gap_px", 2), unit_scale, min_px=1),
        panel_padding_px=scale_symbolic_px(group_default(render_defaults, "panel_padding_px", 28), unit_scale, min_px=12),
        panel_corner_radius_px=scale_symbolic_px(group_default(render_defaults, "panel_corner_radius_px", 22), unit_scale, min_px=8),
        panel_border_width_px=scale_symbolic_px(group_default(render_defaults, "panel_border_width_px", 3), unit_scale, min_px=1),
        grid_line_width_px=scale_symbolic_px(group_default(render_defaults, "grid_line_width_px", 2), unit_scale, min_px=1),
        option_card_width_px=scale_symbolic_px(group_default(render_defaults, "option_card_width_px", 150), unit_scale, min_px=80),
        option_card_height_px=scale_symbolic_px(group_default(render_defaults, "option_card_height_px", 116), unit_scale, min_px=70),
        option_gap_px=scale_symbolic_px(group_default(render_defaults, "option_gap_px", 18), unit_scale, min_px=8),
        option_grid_cell_px=scale_symbolic_px(group_default(render_defaults, "option_grid_cell_px", 24), unit_scale, min_px=9),
        label_font_size_px=scale_symbolic_px(group_default(render_defaults, "label_font_size_px", 22), unit_scale, min_px=12),
        small_font_size_px=scale_symbolic_px(group_default(render_defaults, "small_font_size_px", 16), unit_scale, min_px=10),
        arrow_width_px=scale_symbolic_px(group_default(render_defaults, "arrow_width_px", 6), unit_scale, min_px=2),
        unit_size_jitter=dict(unit_meta),
        layout_seed=int(hash64(int(instance_seed), "puzzles.automaton.layout", 0)),
        font_family=str(font_family),
    )

def _style_meta_with_font(style_meta: Mapping[str, Any], render_params: _RenderParams) -> Dict[str, Any]:
    """Attach the sampled readout font metadata used by rendered scene text."""

    return {
        **dict(style_meta),
        "font_family": str(render_params.font_family),
        "font": {
            "source": "global_font_pool",
            "font_family": str(render_params.font_family),
            "font_asset_version": font_asset_version(),
            "scope": "single_automaton_panel",
        },
    }

def _resolve_agent_style(
    *,
    scene_variant: str,
    render_params: _RenderParams,
) -> Tuple[SymbolicSceneStyle, Dict[str, Any]]:
    """Resolve one non-semantic scene-level style pack for the agent board."""

    style, metadata = resolve_symbolic_scene_style(
        instance_seed=int(render_params.layout_seed),
        namespace=f"agent_automaton.{scene_variant}",
        treatments=_AGENT_STYLE_TREATMENTS,
    )
    chrome_mode, chrome_metadata = resolve_panel_chrome_mode(
        instance_seed=int(render_params.layout_seed),
        namespace=f"agent_automaton.{scene_variant}",
    )
    return style, {
        **dict(metadata),
        "scene_variant": str(scene_variant),
        "panel_chrome": dict(chrome_metadata),
        "panel_chrome_mode": str(chrome_mode),
    }

def _resolve_turing_style(
    *,
    scene_variant: str,
    render_params: _RenderParams,
) -> Tuple[SymbolicSceneStyle, Dict[str, Any]]:
    """Resolve one non-semantic scene-level style pack for the tape machine."""

    style, metadata = resolve_symbolic_scene_style(
        instance_seed=int(render_params.layout_seed),
        namespace=f"turing_tape.{scene_variant}",
        treatments=_AGENT_STYLE_TREATMENTS,
    )
    chrome_mode, chrome_metadata = resolve_panel_chrome_mode(
        instance_seed=int(render_params.layout_seed),
        namespace=f"turing_tape.{scene_variant}",
    )
    return style, {
        **dict(metadata),
        "scene_variant": str(scene_variant),
        "panel_chrome": dict(chrome_metadata),
        "panel_chrome_mode": str(chrome_mode),
    }

def _resolve_axis(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    supported_variants: Sequence[str],
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    axis_namespace: str,
) -> Tuple[str, Dict[str, float]]:
    return resolve_symbolic_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=[str(item) for item in supported_variants],
        task_id=str(task_id),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        axis_namespace=str(axis_namespace),
    )

def _resolve_query(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    supported_queries: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    effective_params = dict(params)
    if effective_params.get("query_id") is None and effective_params.get("query_variant") is not None:
        effective_params["query_id"] = str(effective_params["query_variant"])
    return _resolve_axis(
        params=effective_params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        task_id=str(task_id),
        supported_variants=supported_queries,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )

def _decorrelated_selection_index(*, params: Mapping[str, Any], instance_seed: int, namespace: str) -> int:
    return resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))

def _sample_grid(rng, *, rows: int, cols: int, state_count: int, live_prob: float = 0.34) -> Tuple[Tuple[int, ...], ...]:
    values: List[Tuple[int, ...]] = []
    for _row in range(int(rows)):
        row_values: List[int] = []
        for _col in range(int(cols)):
            if int(state_count) == 2:
                row_values.append(1 if float(rng.random()) < float(live_prob) else 0)
            else:
                row_values.append(int(rng.randrange(int(state_count))))
        values.append(tuple(row_values))
    return tuple(values)

def _rect_cells(row0: int, col0: int, height: int, width: int) -> Tuple[Tuple[int, int], ...]:
    return tuple((int(row), int(col)) for row in range(row0, row0 + height) for col in range(col0, col0 + width))

def _grid_bbox(
    *,
    left: int,
    top: int,
    rows: int,
    cols: int,
    cell_size: int,
    gap: int,
) -> Tuple[int, int, int, int]:
    width = int(cols * cell_size + max(0, cols - 1) * gap)
    height = int(rows * cell_size + max(0, rows - 1) * gap)
    return (int(left), int(top), int(left + width), int(top + height))

def _cell_bbox(
    *,
    left: int,
    top: int,
    row: int,
    col: int,
    cell_size: int,
    gap: int,
) -> Tuple[int, int, int, int]:
    x0 = int(left + col * (cell_size + gap))
    y0 = int(top + row * (cell_size + gap))
    return (x0, y0, int(x0 + cell_size), int(y0 + cell_size))

def _inset_bbox(bbox: Sequence[int], inset: int) -> Tuple[int, int, int, int]:
    x0, y0, x1, y1 = [int(value) for value in bbox]
    inset_px = max(0, int(inset))
    return (
        min(x1, x0 + inset_px),
        min(y1, y0 + inset_px),
        max(x0, x1 - inset_px),
        max(y0, y1 - inset_px),
    )

def _blend_rgb(color_a: Sequence[int], color_b: Sequence[int], alpha_b: float) -> Tuple[int, int, int]:
    alpha = max(0.0, min(1.0, float(alpha_b)))
    return tuple(
        int(round((float(color_a[index]) * (1.0 - alpha)) + (float(color_b[index]) * alpha)))
        for index in range(3)
    )

def _draw_cell_grid(
    draw: ImageDraw.ImageDraw,
    *,
    grid: Sequence[Sequence[int]],
    left: int,
    top: int,
    cell_size: int,
    gap: int,
    state_colors: Sequence[Sequence[int]],
    item_bboxes: Dict[str, Tuple[int, int, int, int]],
    item_prefix: str,
    target_cells: Sequence[Tuple[int, int]] = tuple(),
    draw_labels: bool = False,
    style: SymbolicSceneStyle = DEFAULT_SYMBOLIC_SCENE_STYLE,
    cell_render_style: str = "classic_grid",
) -> None:
    target_set = {(int(row), int(col)) for row, col in target_cells}
    rows = len(grid)
    cols = len(grid[0])
    font = load_font(max(10, int(cell_size * 0.28)), bold=True)
    for row in range(rows):
        for col in range(cols):
            bbox = _cell_bbox(left=left, top=top, row=row, col=col, cell_size=cell_size, gap=gap)
            state = int(grid[row][col])
            fill = tuple(int(value) for value in state_colors[state % len(state_colors)])
            cell_id = f"{item_prefix}_cell_{row}_{col}"
            item_bboxes[cell_id] = bbox
            selected = (row, col) in target_set
            render_style = str(cell_render_style)
            if render_style == "rounded_tiles":
                draw_rounded_rect(
                    draw,
                    bbox=bbox,
                    radius=max(3, int(round(cell_size * 0.10))),
                    fill=fill,
                    outline=style.grid_rgb,
                    width=max(1, int(round(cell_size * 0.035))),
                )
            elif render_style == "inset_cells":
                draw.rectangle(bbox, fill=style.grid_rgb)
                inner = _inset_bbox(bbox, max(1, int(round(cell_size * 0.08))))
                draw_rounded_rect(
                    draw,
                    bbox=inner,
                    radius=max(3, int(round(cell_size * 0.10))),
                    fill=fill,
                    outline=style.panel_border_rgb,
                    width=1,
                )
            elif render_style == "lab_matrix":
                draw.rectangle(bbox, fill=fill, outline=style.panel_border_rgb, width=max(1, int(round(cell_size * 0.04))))
                highlight = _blend_rgb(fill, (255, 255, 255), 0.32)
                draw.line((bbox[0] + 2, bbox[1] + 2, bbox[2] - 3, bbox[1] + 2), fill=highlight, width=1)
                draw.line((bbox[0] + 2, bbox[1] + 2, bbox[0] + 2, bbox[3] - 3), fill=highlight, width=1)
            elif render_style == "notebook_cells":
                draw.rectangle(bbox, fill=fill, outline=style.grid_rgb, width=1)
                draw.line(
                    (bbox[0] + 4, bbox[1] + max(4, int(cell_size * 0.28)), bbox[2] - 4, bbox[1] + max(4, int(cell_size * 0.28))),
                    fill=style.notebook_line_rgb,
                    width=1,
                )
            else:
                draw_symbolic_grid_cell(
                    draw,
                    bbox=bbox,
                    fill=fill,
                    style=style,
                    outline=style.grid_rgb,
                    width=1,
                    selected=False,
                )
            if selected:
                draw.rectangle(
                    bbox,
                    outline=style.mark_rgb,
                    width=max(3, int(cell_size * 0.10)),
                )
            if draw_labels:
                draw_centered_text(
                    draw,
                    text=str(state),
                    center=((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0),
                    font=font,
                    fill=style.text_rgb if state == 0 else style.text_stroke_rgb,
                    stroke_fill=style.text_stroke_rgb if state == 0 else style.text_rgb,
                    stroke_width=1,
                )

def _draw_option_card(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Tuple[int, int, int, int],
    label: str,
    fill: Sequence[int] = _OPTION_FILL_RGB,
    style: SymbolicSceneStyle = DEFAULT_SYMBOLIC_SCENE_STYLE,
) -> None:
    draw_symbolic_option_card(
        draw,
        bbox=bbox,
        style=style,
        fill=fill,
        radius=14,
        border_width=2,
    )
    font = load_font(20, bold=True)
    draw_centered_text(
        draw,
        text=str(label),
        center=(bbox[0] + 20, bbox[1] + 20),
        font=font,
        fill=style.text_rgb,
        stroke_fill=style.text_stroke_rgb,
        stroke_width=1,
    )

def _mark_region_bbox(
    *,
    cells: Sequence[Tuple[int, int]],
    grid_left: int,
    grid_top: int,
    cell_size: int,
    gap: int,
) -> Tuple[int, int, int, int]:
    boxes = [
        _cell_bbox(left=grid_left, top=grid_top, row=int(row), col=int(col), cell_size=cell_size, gap=gap)
        for row, col in cells
    ]
    return (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )

def _decorate_panel(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Tuple[int, int, int, int],
    scene_variant: str,
    radius: int = 22,
    border_width: int = 3,
    style: SymbolicSceneStyle = DEFAULT_SYMBOLIC_SCENE_STYLE,
    chrome_mode: str = "accent_frame",
) -> None:
    draw_symbolic_chrome_by_mode(
        draw,
        bbox=bbox,
        style=style,
        radius=int(radius),
        border_width=int(border_width),
        mode=str(chrome_mode),
    )

def _build_prompt(
    *,
    prompt_defaults: Mapping[str, Any],
    scene_variant: str,
    query_id: str,
    steps: int,
    instance_seed: int,
    task_id: str,
    scene_id: str = "automaton",
    rule_variant: str | None = None,
    extra_slots: Mapping[str, Any] | None = None,
) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
    required_keys = (
        "bundle_id",
        "scene_key",
        "task_key",
        f"object_description_{scene_variant}",
        f"query_instruction_{query_id}",
        "json_output_contract",
        "json_output_contract_answer_only",
        "annotation_hint",
        "answer_hint",
        "json_example",
        "json_example_answer_only",
    )
    if rule_variant is not None:
        required_keys = (*required_keys, f"rule_instruction_{rule_variant}")
    values = required_group_defaults(prompt_defaults, required_keys, context=f"prompt defaults for {task_id}")
    slots = {
        "object_description": str(values[f"object_description_{scene_variant}"]),
        "query_instruction": str(values[f"query_instruction_{query_id}"]),
        "steps": int(steps),
        "json_output_contract": str(values["json_output_contract"]),
        "json_output_contract_answer_only": str(values["json_output_contract_answer_only"]),
        "annotation_hint": str(values["annotation_hint"]),
        "answer_hint": str(values["answer_hint"]),
        "json_example": str(values["json_example"]),
        "json_example_answer_only": str(values["json_example_answer_only"]),
    }
    if rule_variant is not None:
        slots["rule_instruction"] = str(values[f"rule_instruction_{rule_variant}"])
    if isinstance(extra_slots, Mapping):
        slots.update({str(key): value for key, value in extra_slots.items()})
    selection = render_task_prompt_variants(
        domain="symbolic",
        scene_id=str(scene_id),
        bundle_id=str(values["bundle_id"]),
        scene_key=str(values["scene_key"]),
        task_key=str(values["task_key"]),
        query_key=str(query_id),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        slots=slots,
        instance_seed=int(instance_seed),
    )
    artifacts = build_prompt_trace_artifacts(selection)
    return str(artifacts.prompt), dict(artifacts.prompt_variants), {
        "prompt_variant": dict(artifacts.prompt_variant),
        "prompt_variant_active_key": str(artifacts.prompt_variant_active_key),
        "prompt_variants_for_trace": dict(artifacts.prompt_variants_for_trace),
        "bundle_id": str(values["bundle_id"]),
    }

def _common_trace(
    *,
    scene_id: str,
    task_id: str,
    query_id: str,
    query_probabilities: Mapping[str, float],
    scene_variant: str,
    scene_variant_probabilities: Mapping[str, float],
    prompt_meta: Mapping[str, Any],
    render_params: _RenderParams,
    rendered_scene: _RenderedScene,
    background_meta: Mapping[str, Any],
    post_noise_meta: Mapping[str, Any],
    annotation_type: str,
    annotation_value: Any,
    answer_value: Any,
    execution_trace: Mapping[str, Any],
) -> Dict[str, Any]:
    query_params = {
        "query_id": str(query_id),
        "query_id_probabilities": {str(key): float(value) for key, value in query_probabilities.items()},
        "scene_id": str(scene_id),
        "scene_variant": str(scene_variant),
        "scene_variant_probabilities": {str(key): float(value) for key, value in scene_variant_probabilities.items()},
    }
    witness_symbolic, projected_annotation = _annotation_trace_payload(
        annotation_type=str(annotation_type),
        annotation_value=annotation_value,
    )
    return {
        "scene_ir": {
            "scene_kind": str(scene_id),
            "entities": [dict(entity) for entity in rendered_scene.entities],
            "relations": dict(query_params),
        },
        "query_spec": {
            "query_id": str(query_id),
            "template_id": str(prompt_meta["bundle_id"]),
            "prompt_variant": dict(prompt_meta["prompt_variant"]),
            "prompt_variant_active_key": str(prompt_meta["prompt_variant_active_key"]),
            "prompt_variants": dict(prompt_meta["prompt_variants_for_trace"]),
            "params": dict(query_params),
        },
        "render_spec": {
            "scene_id": str(scene_id),
            "canvas_width": int(render_params.canvas_width),
            "canvas_height": int(render_params.canvas_height),
            "coord_space": "pixel",
            "scene_variant": str(scene_variant),
            "background_style": dict(background_meta),
            "post_image_noise": dict(post_noise_meta),
            "scene_bbox_px": [int(value) for value in rendered_scene.scene_bbox_px],
            "render_params": {
                "cell_size_px": int(render_params.cell_size_px),
                "grid_gap_px": int(render_params.grid_gap_px),
                "option_card_width_px": int(render_params.option_card_width_px),
                "option_card_height_px": int(render_params.option_card_height_px),
                "option_grid_cell_px": int(render_params.option_grid_cell_px),
            },
            "unit_size_jitter": dict(render_params.unit_size_jitter),
            "layout_jitter": dict(rendered_scene.layout_jitter),
            "scene_style": dict(rendered_scene.style_metadata),
        },
        "render_map": with_symbolic_unit_size_jitter({
            "image_id": "img0",
            "scene_bbox_px": [int(value) for value in rendered_scene.scene_bbox_px],
            "item_bboxes_px": {str(key): list(value) for key, value in rendered_scene.item_bboxes.items()},
            "annotation_source": "item_bboxes_px",
            "layout_jitter": dict(rendered_scene.layout_jitter),
            "scene_style": dict(rendered_scene.style_metadata),
        }, render_params.unit_size_jitter),
        "execution_trace": {
            **dict(query_params),
            "question_format": str(query_id),
            "task_id": str(task_id),
            "answer_value": answer_value,
            **dict(execution_trace),
        },
        "witness_symbolic": dict(witness_symbolic),
        "projected_annotation": dict(projected_annotation),
    }

def _round_bboxes(annotation_projection: Mapping[str, Any]) -> List[List[float]]:
    return [[round(float(value), 3) for value in bbox] for bbox in annotation_projection.get("bbox_set", [])]

def _round_keyed_bboxes(annotation_projection: Mapping[str, Any]) -> Dict[str, List[float]]:
    return {
        str(key): [round(float(value), 3) for value in bbox]
        for key, bbox in dict(annotation_projection.get("keyed_bbox_map", {})).items()
    }

def _annotation_trace_payload(*, annotation_type: str, annotation_value: Any) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if str(annotation_type) == "keyed_bbox_map":
        keyed = {
            str(key): [round(float(value), 3) for value in bbox]
            for key, bbox in dict(annotation_value).items()
        }
        return (
            {"type": "keyed_bbox_map", "value": dict(keyed)},
            {
                "type": "keyed_bbox_map",
                "keyed_bbox_map": dict(keyed),
                "pixel_keyed_bbox_map": dict(keyed),
                "value": dict(keyed),
            },
        )
    bbox_set = [[round(float(value), 3) for value in bbox] for bbox in list(annotation_value)]
    return (
        {"type": "bbox_set", "value": [list(bbox) for bbox in bbox_set]},
        {
            "type": "bbox_set",
            "bbox_set": [list(bbox) for bbox in bbox_set],
            "pixel_bbox_set": [list(bbox) for bbox in bbox_set],
            "value": [list(bbox) for bbox in bbox_set],
        },
    )

class _BaseAutomatonTask:
    domain = "symbolic"
    scene_id = "automaton"
    default_dataset_enabled = True

    def _scene_variant(
        self,
        *,
        params: Mapping[str, Any],
        gen_defaults: Mapping[str, Any],
        instance_seed: int,
    ) -> Tuple[str, Dict[str, float]]:
        return _resolve_axis(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=str(self.task_id),
            supported_variants=_SCENE_VARIANTS,
            explicit_key="scene_variant",
            weights_key="scene_variant_weights",
            balance_flag_key="balanced_scene_variant_sampling",
            axis_namespace="scene_variant",
        )

__all__ = [
    'AGENT_FINAL_TASK_ID',
    'AGENT_FLIP_TASK_ID',
    'LIFE_GRID_TASK_ID',
    'LIFE_POP_TASK_ID',
    'TURING_SYMBOL_COUNT_TASK_ID',
    'AGENT_SCENE_ID',
    'LIFE_SCENE_ID',
    'TURING_SCENE_ID',
    'AGENT_FINAL_QUERY_IDS',
    'AGENT_FLIP_QUERY_IDS',
    'LIFE_GRID_QUERY_IDS',
    'LIFE_POP_QUERY_IDS',
    'TURING_QUERY_IDS',
    '_SCENE_VARIANTS',
    '_DIRECTIONS',
    '_DIR_VEC',
    '_LETTERS',
    '_TURING_SYMBOLS',
    '_TURING_MOVES',
    '_AGENT_STATE_COLORS',
    '_LIFE_DEAD_RGB',
    '_LIFE_ALIVE_RGB',
    '_GRID_RGB',
    '_PANEL_RGB',
    '_PANEL_BORDER_RGB',
    '_TEXT_RGB',
    '_TEXT_STROKE_RGB',
    '_MARK_RGB',
    '_AGENT_RGB',
    '_OPTION_FILL_RGB',
    '_OPTION_SELECTED_RGB',
    '_AGENT_STYLE_TREATMENTS',
    '_AGENT_BOARD_STYLES',
    '_LIFE_BOARD_STYLES',
    '_LIFE_CELL_PALETTES',
    '_TASK_GROUP_DEFAULTS',
    'POST_IMAGE_BACKGROUND_DEFAULTS',
    'POST_IMAGE_NOISE_DEFAULTS',
    '_RenderParams',
    '_RenderedScene',
    '_load_defaults',
    '_resolve_render_params',
    '_style_meta_with_font',
    '_resolve_agent_style',
    '_resolve_turing_style',
    '_resolve_axis',
    '_resolve_query',
    '_decorrelated_selection_index',
    '_sample_grid',
    '_rect_cells',
    '_grid_bbox',
    '_cell_bbox',
    '_inset_bbox',
    '_blend_rgb',
    '_draw_cell_grid',
    '_draw_option_card',
    '_mark_region_bbox',
    '_decorate_panel',
    '_build_prompt',
    '_common_trace',
    '_round_bboxes',
    '_round_keyed_bboxes',
    '_annotation_trace_payload',
    '_BaseAutomatonTask',
]
