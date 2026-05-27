"""Shared config, generation, and evidence helpers for arithmetic puzzle tasks."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.config_defaults import group_default, resolve_required_int_bounds
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.text_rendering import load_font
from .common import decouple_axis_sampling, projected_puzzle_bbox_evidence, resolve_puzzle_axis_variant
from .arithmetic_scene import PuzzleArithmeticRenderParams, SUPPORTED_PUZZLE_ARITHMETIC_SCENE_VARIANTS
from .grid_scene import PuzzleGridRenderParams, SUPPORTED_PUZZLE_GRID_SCENE_VARIANTS
from ....core.seed import spawn_rng


_OPERATOR_DISPLAY_CHOICES: Tuple[str, ...] = ("+", "+", "-", "-", "×")


@dataclass(frozen=True)
class PuzzleArithmeticDefaults:
    """Stable fallback defaults shared by arithmetic puzzle tasks."""

    answer_min: int = 1
    answer_max: int = 24
    operand_count_min: int = 2
    operand_count_max: int = 5
    operand_value_min: int = 1
    operand_value_max: int = 12
    max_visible_value: int = 48
    canvas_width: int = 960
    canvas_height: int = 540
    scene_margin_left_px: int = 72
    scene_margin_right_px: int = 72
    scene_margin_top_px: int = 72
    scene_margin_bottom_px: int = 72
    slot_width_px: int = 120
    slot_height_px: int = 96
    token_gap_px: int = 26
    row_gap_px: int = 72
    slot_corner_radius_px: int = 18
    border_width_px: int = 3
    panel_padding_px: int = 28
    panel_corner_radius_px: int = 28
    value_font_size_px: int = 46
    operator_font_size_px: int = 54
    balanced_query_id_sampling: bool = True
    balanced_scene_variant_sampling: bool = True


@dataclass(frozen=True)
class PuzzleArithmeticGridDefaults:
    """Stable fallback defaults shared by arithmetic puzzle-grid tasks."""

    answer_min: int = 1
    answer_max: int = 24
    row_count_min: int = 3
    row_count_max: int = 5
    col_count: int = 3
    cell_value_min: int = 1
    cell_value_max: int = 24
    max_visible_value: int = 24
    canvas_width: int = 960
    canvas_height: int = 760
    scene_margin_left_px: int = 72
    scene_margin_right_px: int = 72
    scene_margin_top_px: int = 64
    scene_margin_bottom_px: int = 64
    cell_width_px: int = 120
    cell_height_px: int = 100
    cell_gap_px: int = 24
    slot_corner_radius_px: int = 18
    border_width_px: int = 3
    panel_padding_px: int = 28
    panel_corner_radius_px: int = 28
    value_font_size_px: int = 46
    balanced_query_id_sampling: bool = True
    balanced_scene_variant_sampling: bool = True

def resolve_arithmetic_render_params(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
    defaults: PuzzleArithmeticDefaults,
) -> PuzzleArithmeticRenderParams:
    """Resolve one reusable arithmetic puzzle render-parameter record."""

    def _triple(key: str, fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
        raw = params.get(str(key), group_default(render_defaults, str(key), list(fallback)))
        if not isinstance(raw, Sequence) or len(raw) != 3:
            raise ValueError(f"{key} must be a length-3 RGB sequence")
        return tuple(int(value) for value in raw)

    return PuzzleArithmeticRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(render_defaults, "canvas_width", int(defaults.canvas_width)))),
        canvas_height=int(params.get("canvas_height", group_default(render_defaults, "canvas_height", int(defaults.canvas_height)))),
        scene_margin_left_px=int(params.get("scene_margin_left_px", group_default(render_defaults, "scene_margin_left_px", int(defaults.scene_margin_left_px)))),
        scene_margin_right_px=int(params.get("scene_margin_right_px", group_default(render_defaults, "scene_margin_right_px", int(defaults.scene_margin_right_px)))),
        scene_margin_top_px=int(params.get("scene_margin_top_px", group_default(render_defaults, "scene_margin_top_px", int(defaults.scene_margin_top_px)))),
        scene_margin_bottom_px=int(params.get("scene_margin_bottom_px", group_default(render_defaults, "scene_margin_bottom_px", int(defaults.scene_margin_bottom_px)))),
        slot_width_px=int(params.get("slot_width_px", group_default(render_defaults, "slot_width_px", int(defaults.slot_width_px)))),
        slot_height_px=int(params.get("slot_height_px", group_default(render_defaults, "slot_height_px", int(defaults.slot_height_px)))),
        token_gap_px=int(params.get("token_gap_px", group_default(render_defaults, "token_gap_px", int(defaults.token_gap_px)))),
        row_gap_px=int(params.get("row_gap_px", group_default(render_defaults, "row_gap_px", int(defaults.row_gap_px)))),
        slot_corner_radius_px=int(params.get("slot_corner_radius_px", group_default(render_defaults, "slot_corner_radius_px", int(defaults.slot_corner_radius_px)))),
        border_width_px=int(params.get("border_width_px", group_default(render_defaults, "border_width_px", int(defaults.border_width_px)))),
        panel_padding_px=int(params.get("panel_padding_px", group_default(render_defaults, "panel_padding_px", int(defaults.panel_padding_px)))),
        panel_corner_radius_px=int(params.get("panel_corner_radius_px", group_default(render_defaults, "panel_corner_radius_px", int(defaults.panel_corner_radius_px)))),
        value_font_size_px=int(params.get("value_font_size_px", group_default(render_defaults, "value_font_size_px", int(defaults.value_font_size_px)))),
        operator_font_size_px=int(params.get("operator_font_size_px", group_default(render_defaults, "operator_font_size_px", int(defaults.operator_font_size_px)))),
        slot_fill_rgb=_triple("slot_fill_rgb", (252, 252, 255)),
        unknown_slot_fill_rgb=_triple("unknown_slot_fill_rgb", (242, 246, 255)),
        panel_fill_rgb=_triple("panel_fill_rgb", (248, 249, 252)),
        border_color_rgb=_triple("border_color_rgb", (86, 94, 108)),
        text_color_rgb=_triple("text_color_rgb", (30, 34, 40)),
        text_stroke_rgb=_triple("text_stroke_rgb", (255, 255, 255)),
        accent_color_rgb=_triple("accent_color_rgb", (54, 102, 180)),
    )


def resolve_grid_render_params(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
    defaults: PuzzleArithmeticGridDefaults,
) -> PuzzleGridRenderParams:
    """Resolve one reusable arithmetic-grid render-parameter record."""

    def _triple(key: str, fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
        raw = params.get(str(key), group_default(render_defaults, str(key), list(fallback)))
        if not isinstance(raw, Sequence) or len(raw) != 3:
            raise ValueError(f"{key} must be a length-3 RGB sequence")
        return tuple(int(value) for value in raw)

    return PuzzleGridRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(render_defaults, "canvas_width", int(defaults.canvas_width)))),
        canvas_height=int(params.get("canvas_height", group_default(render_defaults, "canvas_height", int(defaults.canvas_height)))),
        scene_margin_left_px=int(params.get("scene_margin_left_px", group_default(render_defaults, "scene_margin_left_px", int(defaults.scene_margin_left_px)))),
        scene_margin_right_px=int(params.get("scene_margin_right_px", group_default(render_defaults, "scene_margin_right_px", int(defaults.scene_margin_right_px)))),
        scene_margin_top_px=int(params.get("scene_margin_top_px", group_default(render_defaults, "scene_margin_top_px", int(defaults.scene_margin_top_px)))),
        scene_margin_bottom_px=int(params.get("scene_margin_bottom_px", group_default(render_defaults, "scene_margin_bottom_px", int(defaults.scene_margin_bottom_px)))),
        cell_width_px=int(params.get("cell_width_px", group_default(render_defaults, "cell_width_px", int(defaults.cell_width_px)))),
        cell_height_px=int(params.get("cell_height_px", group_default(render_defaults, "cell_height_px", int(defaults.cell_height_px)))),
        cell_gap_px=int(params.get("cell_gap_px", group_default(render_defaults, "cell_gap_px", int(defaults.cell_gap_px)))),
        slot_corner_radius_px=int(params.get("slot_corner_radius_px", group_default(render_defaults, "slot_corner_radius_px", int(defaults.slot_corner_radius_px)))),
        border_width_px=int(params.get("border_width_px", group_default(render_defaults, "border_width_px", int(defaults.border_width_px)))),
        panel_padding_px=int(params.get("panel_padding_px", group_default(render_defaults, "panel_padding_px", int(defaults.panel_padding_px)))),
        panel_corner_radius_px=int(params.get("panel_corner_radius_px", group_default(render_defaults, "panel_corner_radius_px", int(defaults.panel_corner_radius_px)))),
        value_font_size_px=int(params.get("value_font_size_px", group_default(render_defaults, "value_font_size_px", int(defaults.value_font_size_px)))),
        panel_fill_rgb=_triple("panel_fill_rgb", (248, 249, 252)),
        cell_fill_rgb=_triple("cell_fill_rgb", (252, 252, 255)),
        unknown_cell_fill_rgb=_triple("unknown_cell_fill_rgb", (242, 246, 255)),
        border_color_rgb=_triple("border_color_rgb", (86, 94, 108)),
        text_color_rgb=_triple("text_color_rgb", (30, 34, 40)),
        text_stroke_rgb=_triple("text_stroke_rgb", (255, 255, 255)),
        accent_color_rgb=_triple("accent_color_rgb", (54, 102, 180)),
    )


def adjust_render_params_for_equation_rows(
    render_params: PuzzleArithmeticRenderParams,
    *,
    equation_rows: Sequence[Sequence[Mapping[str, Any]]],
) -> PuzzleArithmeticRenderParams:
    """Widen the canvas when longer equation rows need more horizontal room."""

    probe_image = Image.new("RGB", (32, 32), color=(255, 255, 255))
    probe_draw = ImageDraw.Draw(probe_image)
    operator_font = load_font(int(render_params.operator_font_size_px), bold=True)
    max_row_width = 0
    for row in equation_rows:
        token_widths = []
        for token in row:
            if str(token.get("kind")) == "slot":
                token_widths.append(int(render_params.slot_width_px))
                continue
            text_bbox = probe_draw.textbbox(
                (0, 0),
                str(token.get("text", "")),
                font=operator_font,
                stroke_width=1,
            )
            text_width = float(text_bbox[2] - text_bbox[0])
            token_widths.append(int(max(float(text_width + 20.0), 40.0)))
        row_width = int(sum(token_widths) + max(0, len(token_widths) - 1) * int(render_params.token_gap_px))
        max_row_width = max(int(max_row_width), int(row_width))
    horizontal_buffer = max(40, int(render_params.token_gap_px) + 16)
    required_width = int(
        max_row_width
        + int(render_params.scene_margin_left_px)
        + int(render_params.scene_margin_right_px)
        + int(horizontal_buffer)
    )
    if int(required_width) <= int(render_params.canvas_width):
        return render_params
    return replace(render_params, canvas_width=int(required_width))


def resolve_arithmetic_answer_bounds(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    defaults: PuzzleArithmeticDefaults,
    task_id: str,
) -> Tuple[int, int]:
    """Resolve inclusive answer bounds for arithmetic puzzle tasks."""

    return resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="answer_min",
        max_key="answer_max",
        fallback_min=int(defaults.answer_min),
        fallback_max=int(defaults.answer_max),
        context=f"{task_id} answer bounds",
    )


def _resolve_operand_count_bounds(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    defaults: PuzzleArithmeticDefaults,
    task_id: str,
) -> Tuple[int, int]:
    """Resolve inclusive left-side operand-count bounds for arithmetic puzzle tasks."""

    return resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="operand_count_min",
        max_key="operand_count_max",
        fallback_min=int(defaults.operand_count_min),
        fallback_max=int(defaults.operand_count_max),
        context=f"{task_id} operand-count bounds",
    )


def _resolve_grid_row_count_bounds(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    defaults: PuzzleArithmeticGridDefaults,
    task_id: str,
) -> Tuple[int, int]:
    """Resolve inclusive row-count bounds for arithmetic grid puzzles."""

    return resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="row_count_min",
        max_key="row_count_max",
        fallback_min=int(defaults.row_count_min),
        fallback_max=int(defaults.row_count_max),
        context=f"{task_id} row-count bounds",
    )


def _int_from_support(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    namespace: str,
    lower: int,
    upper: int,
) -> int:
    """Pick one deterministic integer from an inclusive feasible support."""

    if int(lower) > int(upper):
        raise ValueError(f"{task_id} received empty support for {namespace}")
    index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}:{namespace}",
        )
    )
    return int(lower + (abs(int(index)) % (int(upper) - int(lower) + 1)))


def _evaluate_expression(operand_values: Sequence[int], operator_symbols: Sequence[str]) -> int:
    """Evaluate one flat arithmetic expression using standard precedence for multiplication."""

    if len(operand_values) != len(operator_symbols) + 1:
        raise ValueError("operand/operator counts do not form a valid flat expression")
    collapsed_terms = [int(operand_values[0])]
    additive_ops: list[str] = []
    for operator_symbol, operand_value in zip(operator_symbols, operand_values[1:]):
        if str(operator_symbol) == "×":
            collapsed_terms[-1] = int(collapsed_terms[-1] * int(operand_value))
        elif str(operator_symbol) in {"+", "-"}:
            additive_ops.append(str(operator_symbol))
            collapsed_terms.append(int(operand_value))
        else:
            raise ValueError(f"unsupported arithmetic operator: {operator_symbol}")
    total = int(collapsed_terms[0])
    for operator_symbol, term_value in zip(additive_ops, collapsed_terms[1:]):
        if str(operator_symbol) == "+":
            total += int(term_value)
        else:
            total -= int(term_value)
    return int(total)


def _sample_operator_symbols(operator_count: int, *, rng) -> list[str]:
    """Sample one weighted operator sequence with occasional multiplication."""

    return [
        str(_OPERATOR_DISPLAY_CHOICES[int(rng.randint(0, len(_OPERATOR_DISPLAY_CHOICES) - 1))])
        for _ in range(int(operator_count))
    ]


def _evaluate_grid_rule(*, left_value: int, right_value: int, operator_symbol: str) -> int:
    """Evaluate one binary row rule for an arithmetic puzzle grid."""

    if str(operator_symbol) == "+":
        return int(left_value + right_value)
    if str(operator_symbol) == "-":
        return int(left_value - right_value)
    if str(operator_symbol) == "×":
        return int(left_value * right_value)
    raise ValueError(f"unsupported arithmetic grid operator: {operator_symbol}")


def _sample_grid_row(
    *,
    operator_symbol: str,
    rng,
    value_min: int,
    value_max: int,
    max_visible_value: int,
) -> Tuple[int, int, int]:
    """Sample one visible arithmetic-grid row that avoids cross-operator ambiguity."""

    support_max = int(min(value_max, max_visible_value))
    if int(support_max) < int(value_min):
        raise ValueError("arithmetic grid support is empty")

    for _ in range(512):
        if str(operator_symbol) == "+":
            left_value = int(rng.randint(int(value_min), max(int(value_min), int(support_max) - 1)))
            max_right = int(support_max - left_value)
            if int(max_right) < int(value_min):
                continue
            right_value = int(rng.randint(int(value_min), int(max_right)))
        elif str(operator_symbol) == "-":
            right_value = int(rng.randint(int(value_min), max(int(value_min), int(support_max) - 1)))
            max_result = int(support_max - right_value)
            if int(max_result) < int(value_min):
                continue
            result_value = int(rng.randint(int(value_min), int(max_result)))
            left_value = int(right_value + result_value)
            row = (int(left_value), int(right_value), int(result_value))
            if int(row[2]) == _evaluate_grid_rule(left_value=row[0], right_value=row[1], operator_symbol="+"):
                continue
            if int(row[2]) == _evaluate_grid_rule(left_value=row[0], right_value=row[1], operator_symbol="×"):
                continue
            return row
        elif str(operator_symbol) == "×":
            max_left = int(max(2, min(support_max, int(support_max // 2) if support_max >= 4 else support_max)))
            if int(max_left) < 2:
                continue
            left_value = int(rng.randint(2, int(max_left)))
            max_right = int(min(support_max // left_value, support_max))
            if int(max_right) < 2:
                continue
            right_value = int(rng.randint(2, int(max_right)))
        else:
            raise ValueError(f"unsupported arithmetic grid operator: {operator_symbol}")

        result_value = int(_evaluate_grid_rule(left_value=int(left_value), right_value=int(right_value), operator_symbol=str(operator_symbol)))
        if not (int(value_min) <= int(result_value) <= int(support_max)):
            continue
        if str(operator_symbol) != "+" and int(result_value) == _evaluate_grid_rule(left_value=int(left_value), right_value=int(right_value), operator_symbol="+"):
            continue
        if str(operator_symbol) != "-" and int(result_value) == _evaluate_grid_rule(left_value=int(left_value), right_value=int(right_value), operator_symbol="-"):
            continue
        if str(operator_symbol) != "×" and int(result_value) == _evaluate_grid_rule(left_value=int(left_value), right_value=int(right_value), operator_symbol="×"):
            continue
        return int(left_value), int(right_value), int(result_value)
    raise ValueError(f"could not sample a valid arithmetic grid row for operator={operator_symbol}")


def _operator_fits_rows(rows: Sequence[Sequence[int]], *, operator_symbol: str) -> bool:
    """Return whether one operator is consistent with every fully visible grid row."""

    return all(
        int(row[2]) == _evaluate_grid_rule(
            left_value=int(row[0]),
            right_value=int(row[1]),
            operator_symbol=str(operator_symbol),
        )
        for row in rows
    )


def _build_grid_rows(
    *,
    row_values: Sequence[Sequence[int]],
    query_row_index: int,
    query_col_index: int,
) -> list[list[Mapping[str, Any]]]:
    """Build rendered grid rows with one explicit unknown cell."""

    grid_rows: list[list[Mapping[str, Any]]] = []
    for row_index, row in enumerate(row_values):
        rendered_row: list[Mapping[str, Any]] = []
        for col_index, value in enumerate(row):
            cell_id = f"cell_r{int(row_index)}_c{int(col_index)}"
            is_unknown = int(row_index) == int(query_row_index) and int(col_index) == int(query_col_index)
            rendered_row.append(
                {
                    "cell_id": str(cell_id),
                    "text": "?" if is_unknown else str(int(value)),
                    "value": None if is_unknown else int(value),
                    "is_unknown": bool(is_unknown),
                }
            )
        grid_rows.append(rendered_row)
    return grid_rows


def _build_equation_row(
    *,
    operand_values: Sequence[int],
    operator_symbols: Sequence[str],
    result_value: int,
    query_slot_id: str,
) -> list[Mapping[str, Any]]:
    """Build one rendered equation row from operands, operators, and result."""

    row: list[Mapping[str, Any]] = []
    for operand_index, operand_value in enumerate(operand_values):
        if operand_index:
            row.append({"kind": "operator", "text": str(operator_symbols[int(operand_index - 1)])})
        slot_id = f"slot_operand_{int(operand_index)}"
        is_unknown = str(slot_id) == str(query_slot_id)
        row.append(
            {
                "kind": "slot",
                "slot_id": str(slot_id),
                "text": "?" if is_unknown else str(int(operand_value)),
                "value": None if is_unknown else int(operand_value),
                "is_unknown": bool(is_unknown),
            }
        )
    row.append({"kind": "operator", "text": "="})
    result_unknown = str(query_slot_id) == "slot_result"
    row.append(
        {
            "kind": "slot",
            "slot_id": "slot_result",
            "text": "?" if result_unknown else str(int(result_value)),
            "value": None if result_unknown else int(result_value),
            "is_unknown": bool(result_unknown),
        }
    )
    return row


def build_arithmetic_equation_dataset_for_variant(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: PuzzleArithmeticDefaults,
    task_id: str,
) -> Dict[str, Any]:
    """Construct one deterministic one-row arithmetic puzzle dataset with one unknown slot."""

    supported = {"result_unknown", "operand_unknown"}
    selected_variant = str(query_id)
    if selected_variant not in supported:
        raise ValueError(f"unsupported arithmetic puzzle variant: {query_id}")

    rng = spawn_rng(int(instance_seed), f"{task_id}.dataset")
    answer_min, answer_max = resolve_arithmetic_answer_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    operand_count_min, operand_count_max = _resolve_operand_count_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    operand_value_min = int(params.get("operand_value_min", group_default(gen_defaults, "operand_value_min", int(defaults.operand_value_min))))
    operand_value_max = int(params.get("operand_value_max", group_default(gen_defaults, "operand_value_max", int(defaults.operand_value_max))))
    max_visible_value = int(params.get("max_visible_value", group_default(gen_defaults, "max_visible_value", int(defaults.max_visible_value))))

    operand_count = _int_from_support(
        params=params,
        instance_seed=int(instance_seed),
        task_id=task_id,
        namespace=f"{selected_variant}:operand_count",
        lower=max(2, int(operand_count_min)),
        upper=max(2, int(operand_count_max)),
    )
    hidden_operand_index = None
    if selected_variant == "operand_unknown":
        hidden_operand_index = _int_from_support(
            params=params,
            instance_seed=int(instance_seed),
            task_id=task_id,
            namespace=f"{selected_variant}:hidden_operand_index",
            lower=0,
            upper=max(0, int(operand_count - 1)),
        )
    query_slot_id = "slot_result" if selected_variant == "result_unknown" else f"slot_operand_{int(hidden_operand_index)}"

    operand_values: list[int] | None = None
    operator_symbols: list[str] | None = None
    result_value: int | None = None
    for _ in range(512):
        sampled_operands = [
            int(rng.randint(int(operand_value_min), int(operand_value_max)))
            for _ in range(int(operand_count))
        ]
        sampled_operators = _sample_operator_symbols(int(operand_count - 1), rng=rng)
        evaluated_result = int(_evaluate_expression(sampled_operands, sampled_operators))
        if int(evaluated_result) <= 0:
            continue
        if selected_variant == "result_unknown":
            if not (int(answer_min) <= int(evaluated_result) <= int(answer_max)):
                continue
        else:
            if not (int(answer_min) <= int(sampled_operands[int(hidden_operand_index)]) <= int(answer_max)):
                continue
            if int(evaluated_result) > int(max_visible_value):
                continue
        operand_values = [int(value) for value in sampled_operands]
        operator_symbols = [str(symbol) for symbol in sampled_operators]
        result_value = int(evaluated_result)
        break
    if operand_values is None or operator_symbols is None or result_value is None:
        raise ValueError(f"{task_id} could not construct a valid arithmetic puzzle for variant={selected_variant}")

    slot_count = int(operand_count + 1)
    equation_rows = [
        _build_equation_row(
            operand_values=operand_values,
            operator_symbols=operator_symbols,
            result_value=int(result_value),
            query_slot_id=str(query_slot_id),
        )
    ]
    answer_value = int(result_value if selected_variant == "result_unknown" else operand_values[int(hidden_operand_index)])
    operator_variety = int(len(set(operator_symbols)))

    return {
        "query_id": selected_variant,
        "equation_rows": [[dict(token) for token in row] for row in equation_rows],
        "answer_value": int(answer_value),
        "query_slot_id": str(query_slot_id),
        "slot_count": int(slot_count),
        "slot_count_range": [int(operand_count_min + 1), int(operand_count_max + 1)],
        "operand_count": int(operand_count),
        "operand_count_range": [int(operand_count_min), int(operand_count_max)],
        "step_count": 1,
        "solver_trace": {
            "operand_values": [int(value) for value in operand_values],
            "operator_symbols": [str(symbol) for symbol in operator_symbols],
            "operator_count": int(len(operator_symbols)),
            "operator_variety": int(operator_variety),
            "result_value": int(result_value),
            "hidden_operand_index": None if hidden_operand_index is None else int(hidden_operand_index),
            "unknown_side": "right" if selected_variant == "result_unknown" else "left",
        },
        "answer_range": [int(answer_min), int(answer_max)],
        "max_visible_value": int(max_visible_value),
    }


def build_arithmetic_grid_dataset_for_variant(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: PuzzleArithmeticGridDefaults,
    task_id: str,
) -> Dict[str, Any]:
    """Construct one deterministic arithmetic-grid puzzle with a single unknown cell."""

    operator_by_variant = {
        "sum_rule_missing": "+",
        "difference_rule_missing": "-",
        "product_rule_missing": "×",
    }
    selected_variant = str(query_id)
    if selected_variant not in operator_by_variant:
        raise ValueError(f"unsupported arithmetic grid puzzle variant: {query_id}")
    operator_symbol = str(operator_by_variant[str(selected_variant)])

    rng = spawn_rng(int(instance_seed), f"{task_id}.dataset")
    answer_min, answer_max = resolve_arithmetic_answer_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    row_count_min, row_count_max = _resolve_grid_row_count_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    col_count = int(params.get("col_count", group_default(gen_defaults, "col_count", int(defaults.col_count))))
    if int(col_count) != 3:
        raise ValueError(f"{task_id} currently requires col_count=3")
    cell_value_min = int(params.get("cell_value_min", group_default(gen_defaults, "cell_value_min", int(defaults.cell_value_min))))
    cell_value_max = int(params.get("cell_value_max", group_default(gen_defaults, "cell_value_max", int(defaults.cell_value_max))))
    max_visible_value = int(params.get("max_visible_value", group_default(gen_defaults, "max_visible_value", int(defaults.max_visible_value))))

    row_count = _int_from_support(
        params=params,
        instance_seed=int(instance_seed),
        task_id=task_id,
        namespace=f"{selected_variant}:row_count",
        lower=max(3, int(row_count_min)),
        upper=max(3, int(row_count_max)),
    )
    query_row_index = _int_from_support(
        params=params,
        instance_seed=int(instance_seed),
        task_id=task_id,
        namespace=f"{selected_variant}:query_row_index",
        lower=0,
        upper=max(0, int(row_count - 1)),
    )
    query_col_index = _int_from_support(
        params=params,
        instance_seed=int(instance_seed),
        task_id=task_id,
        namespace=f"{selected_variant}:query_col_index",
        lower=0,
        upper=2,
    )

    row_values: list[Tuple[int, int, int]] | None = None
    for _ in range(512):
        sampled_rows = [
            _sample_grid_row(
                operator_symbol=str(operator_symbol),
                rng=rng,
                value_min=int(cell_value_min),
                value_max=int(min(cell_value_max, answer_max)),
                max_visible_value=int(min(max_visible_value, answer_max)),
            )
            for _ in range(int(row_count))
        ]
        complete_rows = [
            tuple(int(value) for value in row)
            for row_index, row in enumerate(sampled_rows)
            if int(row_index) != int(query_row_index)
        ]
        matching_symbols = [
            symbol
            for symbol in ("+", "-", "×")
            if _operator_fits_rows(complete_rows, operator_symbol=str(symbol))
        ]
        if matching_symbols != [str(operator_symbol)]:
            continue
        answer_value = int(sampled_rows[int(query_row_index)][int(query_col_index)])
        if not (int(answer_min) <= int(answer_value) <= int(answer_max)):
            continue
        row_values = [tuple(int(value) for value in row) for row in sampled_rows]
        break
    if row_values is None:
        raise ValueError(f"{task_id} could not construct a valid arithmetic grid puzzle for variant={selected_variant}")

    grid_rows = _build_grid_rows(
        row_values=list(row_values),
        query_row_index=int(query_row_index),
        query_col_index=int(query_col_index),
    )
    query_cell_id = f"cell_r{int(query_row_index)}_c{int(query_col_index)}"
    answer_value = int(row_values[int(query_row_index)][int(query_col_index)])
    visible_example_rows = [
        [int(value) for value in row]
        for row_index, row in enumerate(row_values)
        if int(row_index) != int(query_row_index)
    ]

    return {
        "query_id": str(selected_variant),
        "operator_symbol": str(operator_symbol),
        "grid_rows": [[dict(cell) for cell in row] for row in grid_rows],
        "row_values": [[int(value) for value in row] for row in row_values],
        "visible_example_rows": [list(row) for row in visible_example_rows],
        "answer_value": int(answer_value),
        "query_cell_id": str(query_cell_id),
        "query_row_index": int(query_row_index),
        "query_col_index": int(query_col_index),
        "row_count": int(row_count),
        "row_count_range": [int(row_count_min), int(row_count_max)],
        "col_count": int(col_count),
        "cell_count": int(row_count * col_count),
        "cell_count_range": [int(row_count_min * col_count), int(row_count_max * col_count)],
        "answer_range": [int(answer_min), int(answer_max)],
        "max_visible_value": int(min(max_visible_value, answer_max)),
        "solver_trace": {
            "operator_symbol": str(operator_symbol),
            "query_row_index": int(query_row_index),
            "query_col_index": int(query_col_index),
            "hidden_position_kind": "result" if int(query_col_index) == 2 else "operand",
            "visible_example_row_count": int(len(visible_example_rows)),
            "complete_rows_unique_operator": True,
        },
    }

__all__ = [
    "PuzzleArithmeticDefaults",
    "PuzzleArithmeticGridDefaults",
    "SUPPORTED_PUZZLE_ARITHMETIC_SCENE_VARIANTS",
    "SUPPORTED_PUZZLE_GRID_SCENE_VARIANTS",
    "adjust_render_params_for_equation_rows",
    "build_arithmetic_equation_dataset_for_variant",
    "build_arithmetic_grid_dataset_for_variant",
    "projected_puzzle_bbox_evidence",
    "resolve_arithmetic_answer_bounds",
    "resolve_arithmetic_render_params",
    "resolve_grid_render_params",
    "resolve_puzzle_axis_variant",
]
