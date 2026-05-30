"""Arithmetic-constraint diagram puzzles with one marked integer target."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.bbox_projection import round_bbox as _round_bbox
from ...shared.config_defaults import required_group_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.font_assets import font_asset_version, get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_rendering import load_font, temporary_default_font_family
from ..shared.common import (
    get_int_param as _get_int,
    get_int_range as _get_range,
    load_puzzle_task_defaults,
    projected_puzzle_bbox_evidence,
    resolve_puzzle_axis_variant,
)
from ..shared.complexity import build_puzzle_complexity, normalize_int_with_bounds
from ..shared.drawing import draw_centered_text, draw_rounded_rect
from ..shared.scene_style import draw_puzzle_panel_chrome, make_puzzle_scene_background, resolve_puzzle_scene_style
from ..shared.unit_size_jitter import resolve_puzzle_unit_size_scale, scale_puzzle_px, with_puzzle_unit_size_jitter
from ..shared.visual_defaults import load_puzzle_noise_defaults


SCENE_ID = "arithmetic_constraint"
TASK_ID = "task_puzzles__arithmetic_constraint__arithmetic_constraint_value"
CRYPTARITHM_TASK_ID = "task_puzzles__arithmetic_constraint__cryptarithm_digit_value"
OPERATOR_GRID_TASK_ID = "task_puzzles__arithmetic_constraint__operator_grid_value"
NUMBER_WALL_TASK_ID = "task_puzzles__arithmetic_constraint__number_wall_value"
ARITHMETIC_CONSTRAINT_QUERY_IDS: Tuple[str, ...] = (
    "equal_sum_line_constraint_value",
    "paired_cluster_sum_relation_value",
    "consecutive_window_sum_value",
)
CRYPTARITHM_QUERY_IDS: Tuple[str, ...] = (
    "hidden_addition_digit_value",
    "hidden_subtraction_digit_value",
    "letter_digit_value",
)
OPERATOR_GRID_QUERY_IDS: Tuple[str, ...] = (
    "row_column_total_missing_value",
    "operation_table_cell_value",
)
NUMBER_WALL_QUERY_IDS: Tuple[str, ...] = (
    "addition_wall_missing_value",
    "difference_wall_missing_value",
    "multiplication_pyramid_value",
)
SUPPORTED_QUERY_IDS: Tuple[str, ...] = ARITHMETIC_CONSTRAINT_QUERY_IDS
SUPPORTED_QUERY_IDS_BY_TASK_ID: Dict[str, Tuple[str, ...]] = {
    TASK_ID: ARITHMETIC_CONSTRAINT_QUERY_IDS,
    CRYPTARITHM_TASK_ID: CRYPTARITHM_QUERY_IDS,
    OPERATOR_GRID_TASK_ID: OPERATOR_GRID_QUERY_IDS,
    NUMBER_WALL_TASK_ID: NUMBER_WALL_QUERY_IDS,
}
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "constraint_sheet",
    "constraint_card",
    "constraint_outline",
)
_REASONING_LOAD_BY_QUERY = {
    "equal_sum_line_constraint_value": 0.50,
    "paired_cluster_sum_relation_value": 0.54,
    "consecutive_window_sum_value": 0.46,
    "hidden_addition_digit_value": 0.58,
    "hidden_subtraction_digit_value": 0.60,
    "letter_digit_value": 0.68,
    "row_column_total_missing_value": 0.54,
    "operation_table_cell_value": 0.50,
    "addition_wall_missing_value": 0.52,
    "difference_wall_missing_value": 0.56,
    "multiplication_pyramid_value": 0.56,
}
_SCENE_LOAD_BY_VARIANT = {
    "constraint_sheet": 0.18,
    "constraint_card": 0.24,
    "constraint_outline": 0.21,
}
_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "logic")
POST_IMAGE_NOISE_DEFAULTS = load_puzzle_noise_defaults(task_group="logic", apply_prob=0.15)


@dataclass(frozen=True)
class ArithmeticRenderParams:
    """Resolved rendering knobs for arithmetic-constraint scenes."""

    canvas_width: int
    canvas_height: int
    panel_padding_px: int
    panel_corner_radius_px: int
    panel_border_width_px: int
    node_radius_px: int
    cell_width_px: int
    cell_height_px: int
    line_width_px: int
    value_font_size_px: int
    note_font_size_px: int
    symbol_font_size_px: int
    unit_size_jitter: Dict[str, Any]


@dataclass(frozen=True)
class RenderedArithmeticScene:
    """Rendered arithmetic scene plus traceable item geometry."""

    image: Image.Image
    entities: List[Dict[str, Any]]
    scene_bbox_px: List[float]
    item_bbox_map: Dict[str, List[float]]


def _sample_int_from_range(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    *,
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
    rng,
) -> int:
    low, high = _get_range(
        params,
        defaults,
        min_key=str(min_key),
        max_key=str(max_key),
        fallback_min=int(fallback_min),
        fallback_max=int(fallback_max),
    )
    return int(rng.randint(int(low), int(high)))


def _load_defaults(task_id: str = TASK_ID) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, float]]:
    return load_puzzle_task_defaults(_TASK_GROUP_DEFAULTS, task_id=str(task_id))


def _resolve_query_id(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str = TASK_ID,
    supported_query_ids: Sequence[str] = SUPPORTED_QUERY_IDS,
) -> Tuple[str, Dict[str, float]]:
    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=tuple(str(item) for item in supported_query_ids),
        task_id=str(task_id),
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )


def _resolve_scene_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str = TASK_ID,
) -> Tuple[str, Dict[str, float]]:
    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_SCENE_VARIANTS,
        task_id=str(task_id),
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def _resolve_answer_value(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    query_id: str,
    task_id: str = TASK_ID,
) -> Tuple[int, List[int]]:
    query_min_key = f"{query_id}_answer_min"
    query_max_key = f"{query_id}_answer_max"
    min_key = str(query_min_key) if str(query_min_key) in params or str(query_min_key) in gen_defaults else "answer_min"
    max_key = str(query_max_key) if str(query_max_key) in params or str(query_max_key) in gen_defaults else "answer_max"
    low, high = _get_range(
        params,
        gen_defaults,
        min_key=min_key,
        max_key=max_key,
        fallback_min=1,
        fallback_max=24,
    )
    support = [int(value) for value in range(int(low), int(high) + 1)]
    if not support:
        raise ValueError("arithmetic-constraint answer support cannot be empty")
    selection = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.{query_id}.answer",
        )
    )
    return int(support[int(selection % len(support))]), support


def _sample_positive_parts(
    total: int,
    count: int,
    *,
    min_value: int,
    max_value: int,
    rng,
) -> List[int] | None:
    if int(count) <= 0:
        return [] if int(total) == 0 else None
    if int(total) < int(count) * int(min_value) or int(total) > int(count) * int(max_value):
        return None
    for _attempt in range(500):
        remaining = int(total)
        parts: List[int] = []
        feasible = True
        for index in range(int(count)):
            remaining_slots = int(count) - int(index) - 1
            low = max(int(min_value), int(remaining) - (remaining_slots * int(max_value)))
            high = min(int(max_value), int(remaining) - (remaining_slots * int(min_value)))
            if int(low) > int(high):
                feasible = False
                break
            value = int(rng.randint(int(low), int(high)))
            parts.append(int(value))
            remaining -= int(value)
        if feasible and int(remaining) == 0:
            rng.shuffle(parts)
            return parts
    return None


def _build_equal_sum_dataset(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    answer_value: int,
    answer_support: Sequence[int],
    task_id: str = TASK_ID,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{task_id}.equal_sum")
    value_min, value_max = _get_range(
        params,
        gen_defaults,
        min_key="visible_value_min",
        max_key="visible_value_max",
        fallback_min=1,
        fallback_max=18,
    )
    side_count_options = [3, 4, 5]
    shape_index = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{task_id}.equal_sum.shape")) % len(side_count_options)
    side_count = int(side_count_options[shape_index])
    hidden_side = int(rng.randrange(side_count))
    for _attempt in range(500):
        corners = [int(rng.randint(int(value_min), int(value_max))) for _ in range(side_count)]
        side_total = int(answer_value) + int(corners[hidden_side]) + int(corners[(hidden_side + 1) % side_count])
        if side_total <= max(corners) * 2:
            continue
        midpoints: List[int] = []
        valid = True
        for side_index in range(side_count):
            if int(side_index) == int(hidden_side):
                midpoint = int(answer_value)
            else:
                midpoint = int(side_total) - int(corners[side_index]) - int(corners[(side_index + 1) % side_count])
            if int(side_index) != int(hidden_side) and not int(value_min) <= int(midpoint) <= int(value_max):
                valid = False
                break
            midpoints.append(int(midpoint))
        if not valid:
            continue
        nodes: List[Dict[str, Any]] = []
        for index, value in enumerate(corners):
            nodes.append({"node_id": f"corner_{index}", "kind": "corner", "index": int(index), "value": int(value), "hidden": False})
        for index, value in enumerate(midpoints):
            nodes.append({"node_id": f"side_mid_{index}", "kind": "side_mid", "index": int(index), "value": int(value), "hidden": bool(index == hidden_side)})
        return {
            "query_id": "equal_sum_line_constraint_value",
            "layout_style": {3: "triangle", 4: "square", 5: "pentagon"}[side_count],
            "side_count": int(side_count),
            "side_total": int(side_total),
            "nodes": nodes,
            "answer_value": int(answer_value),
            "answer_range": [int(min(answer_support)), int(max(answer_support))],
            "target_answer_support": [int(value) for value in answer_support],
            "supporting_item_ids": [f"side_mid_{hidden_side}"],
        }
    raise RuntimeError("failed to build equal-sum arithmetic constraint")


def _build_cluster_dataset(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    answer_value: int,
    answer_support: Sequence[int],
    task_id: str = TASK_ID,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{task_id}.cluster")
    value_min, value_max = _get_range(
        params,
        gen_defaults,
        min_key="visible_value_min",
        max_key="visible_value_max",
        fallback_min=1,
        fallback_max=18,
    )
    layout_styles = ("flower", "rosette", "star", "bead_ring", "polygon_cluster")
    relation_styles = ("double", "offset")
    layout_style = str(layout_styles[int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{task_id}.cluster.layout")) % len(layout_styles)])
    relation_style = str(relation_styles[int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{task_id}.cluster.relation")) % len(relation_styles)])
    leaf_count = int(rng.randint(4, 6))
    for _attempt in range(700):
        left_values = [int(rng.randint(int(value_min), min(int(value_max), 10))) for _ in range(int(leaf_count))]
        left_total = int(sum(left_values))
        if relation_style == "double":
            relation_multiplier = 2
            relation_offset = 0
        else:
            relation_multiplier = 1
            relation_offset = int(rng.randint(7, 18))
        right_total = int((relation_multiplier * left_total) + relation_offset)
        visible_right_sum = int(right_total) - int(answer_value)
        visible_right = _sample_positive_parts(
            visible_right_sum,
            int(leaf_count) - 1,
            min_value=int(value_min),
            max_value=int(value_max),
            rng=rng,
        )
        if visible_right is None:
            continue
        hidden_index = int(rng.randrange(leaf_count))
        right_values = list(visible_right)
        right_values.insert(hidden_index, int(answer_value))
        relation_text = (
            "Right total = 2 x Left total"
            if relation_style == "double"
            else f"Right total = Left total + {relation_offset}"
        )
        return {
            "query_id": "paired_cluster_sum_relation_value",
            "layout_style": str(layout_style),
            "relation_style": str(relation_style),
            "relation_multiplier": int(relation_multiplier),
            "relation_offset": int(relation_offset),
            "relation_text": str(relation_text),
            "left_values": [int(value) for value in left_values],
            "right_values": [int(value) for value in right_values],
            "hidden_side": "right",
            "hidden_index": int(hidden_index),
            "left_total": int(left_total),
            "right_total": int(right_total),
            "answer_value": int(answer_value),
            "answer_range": [int(min(answer_support)), int(max(answer_support))],
            "target_answer_support": [int(value) for value in answer_support],
            "supporting_item_ids": [f"right_leaf_{hidden_index}"],
        }
    raise RuntimeError("failed to build paired-cluster arithmetic constraint")


def _build_consecutive_dataset(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    answer_value: int,
    answer_support: Sequence[int],
    task_id: str = TASK_ID,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{task_id}.consecutive")
    value_min, value_max = _get_range(
        params,
        gen_defaults,
        min_key="visible_value_min",
        max_key="visible_value_max",
        fallback_min=1,
        fallback_max=18,
    )
    length_min, length_max = _get_range(
        params,
        gen_defaults,
        min_key="window_sequence_length_min",
        max_key="window_sequence_length_max",
        fallback_min=6,
        fallback_max=9,
    )
    window_size = 3
    length = int(rng.randint(int(length_min), int(length_max)))
    hidden_phase = int(rng.randrange(window_size))
    for _attempt in range(300):
        base = [int(rng.randint(int(value_min), int(value_max))) for _ in range(window_size)]
        base[hidden_phase] = int(answer_value)
        if len(set(base)) < 2:
            continue
        values = [int(base[index % window_size]) for index in range(int(length))]
        possible_hidden = [index for index, value in enumerate(values) if int(index % window_size) == int(hidden_phase) and int(value) == int(answer_value)]
        if not possible_hidden:
            continue
        hidden_index = int(possible_hidden[int(rng.randrange(len(possible_hidden)))])
        window_total = int(sum(base))
        layout_style = "cell_strip" if int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{task_id}.consecutive.layout")) % 2 == 0 else "bead_arc"
        return {
            "query_id": "consecutive_window_sum_value",
            "layout_style": str(layout_style),
            "window_size": int(window_size),
            "window_total": int(window_total),
            "sequence_values": [int(value) for value in values],
            "hidden_index": int(hidden_index),
            "answer_value": int(answer_value),
            "answer_range": [int(min(answer_support)), int(max(answer_support))],
            "target_answer_support": [int(value) for value in answer_support],
            "supporting_item_ids": [f"cell_{hidden_index}"],
        }
    raise RuntimeError("failed to build consecutive-window arithmetic constraint")


def _nonleading_digit_positions(value: int, *, width: int) -> List[int]:
    digits = f"{int(value):0{int(width)}d}"
    return [index for index in range(int(width)) if not (index == 0 and digits[index] == "0")]


def _digits_for_value(value: int, *, width: int) -> List[int]:
    return [int(char) for char in f"{int(value):0{int(width)}d}"]


def _sample_hidden_arithmetic_problem(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    answer_value: int,
    operator: str,
    query_id: str,
    task_id: str,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{task_id}.{query_id}")
    width = _sample_int_from_range(
        params,
        gen_defaults,
        min_key="hidden_number_width_min",
        max_key="hidden_number_width_max",
        fallback_min=2,
        fallback_max=4,
        rng=rng,
    )
    addend_count = _sample_int_from_range(
        params,
        gen_defaults,
        min_key="hidden_addend_count_min",
        max_key="hidden_addend_count_max",
        fallback_min=2,
        fallback_max=3,
        rng=rng,
    )
    target_digit = int(answer_value)
    for _attempt in range(900):
        if str(operator) == "+":
            lower = 10 ** (int(width) - 1)
            upper = (10 ** int(width)) - 1
            result = int(rng.randint(int(addend_count) * int(lower), int(upper)))
            addends = _sample_positive_parts(
                int(result),
                int(addend_count),
                min_value=int(lower),
                max_value=int(upper),
                rng=rng,
            )
            if addends is None:
                continue
            rows = []
            for addend_index, addend in enumerate(addends):
                rows.append(
                    {
                        "row_id": f"addend_{addend_index}",
                        "role": "addend",
                        "value": int(addend),
                        "digits": _digits_for_value(int(addend), width=int(width)),
                        "prefix": "" if int(addend_index) == 0 else "+",
                    }
                )
            rows.append({"row_id": "result", "role": "result", "value": int(result), "digits": _digits_for_value(result, width=int(width)), "prefix": ""})
        else:
            lower = 10 ** (int(width) - 1)
            upper = (10 ** int(width)) - 1
            top = int(rng.randint(2 * int(lower), int(upper)))
            bottom = int(rng.randint(int(lower), max(int(lower), int(top) - int(lower))))
            result = int(top - bottom)
            if result < int(lower):
                continue
            rows = [
                {"row_id": "minuend", "role": "minuend", "value": int(top), "digits": _digits_for_value(top, width=int(width)), "prefix": ""},
                {"row_id": "subtrahend", "role": "subtrahend", "value": int(bottom), "digits": _digits_for_value(bottom, width=int(width)), "prefix": "-"},
                {"row_id": "result", "role": "result", "value": int(result), "digits": _digits_for_value(result, width=int(width)), "prefix": ""},
            ]
        candidates: List[Tuple[int, int]] = []
        for row_index, row in enumerate(rows):
            allowed_positions = _nonleading_digit_positions(int(row["value"]), width=width)
            for col_index in allowed_positions:
                if int(row["digits"][col_index]) == int(target_digit):
                    candidates.append((int(row_index), int(col_index)))
        if not candidates:
            continue
        hidden_row_index, hidden_col_index = candidates[int(rng.randrange(len(candidates)))]
        hidden_row = rows[int(hidden_row_index)]
        return {
            "query_id": str(query_id),
            "layout_style": "vertical_addition" if str(operator) == "+" else "vertical_subtraction",
            "operator": str(operator),
            "number_width": int(width),
            "addend_count": int(addend_count) if str(operator) == "+" else 1,
            "rows": rows,
            "hidden_row_index": int(hidden_row_index),
            "hidden_col_index": int(hidden_col_index),
            "hidden_row_id": str(hidden_row["row_id"]),
            "hidden_cell_id": f"{hidden_row['row_id']}_digit_{hidden_col_index}",
            "answer_value": int(target_digit),
            "answer_range": [0, 9],
            "target_answer_support": list(range(10)),
            "supporting_item_ids": [f"{hidden_row['row_id']}_digit_{hidden_col_index}"],
        }
    raise RuntimeError(f"failed to build hidden arithmetic problem for {query_id}")


def _build_letter_digit_dataset(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    answer_value: int,
    answer_support: Sequence[int],
    task_id: str = CRYPTARITHM_TASK_ID,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{task_id}.letter_digit")
    letter_count = _sample_int_from_range(
        params,
        gen_defaults,
        min_key="letter_count_min",
        max_key="letter_count_max",
        fallback_min=3,
        fallback_max=5,
        rng=rng,
    )
    letter_count = max(3, min(8, int(letter_count)))
    letters = [chr(ord("A") + index) for index in range(int(letter_count))]
    target_letter = str(letters[int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{task_id}.letter_digit.target")) % len(letters)])
    values: Dict[str, int] = {target_letter: int(answer_value)}
    available = [value for value in range(0, 10) if int(value) != int(answer_value)]
    rng.shuffle(available)
    for letter in letters:
        if letter not in values:
            values[letter] = int(available.pop())
    anchor_letters = [letter for letter in letters if str(letter) != str(target_letter)]
    rng.shuffle(anchor_letters)
    core_letters = [str(target_letter), str(anchor_letters[0]), str(anchor_letters[1])]
    core_pairs = [
        (core_letters[0], core_letters[1]),
        (core_letters[0], core_letters[2]),
        (core_letters[1], core_letters[2]),
    ]
    equations = [{"left": [left, right], "op": "+", "total": int(values[left] + values[right])} for left, right in core_pairs]
    extra_min, extra_max = _get_range(
        params,
        gen_defaults,
        min_key="letter_extra_equation_count_min",
        max_key="letter_extra_equation_count_max",
        fallback_min=0,
        fallback_max=1,
    )
    possible_extra_pairs = [
        (left, right)
        for left_index, left in enumerate(letters)
        for right in letters[left_index + 1 :]
        if (str(left), str(right)) not in core_pairs and (str(right), str(left)) not in core_pairs
    ]
    rng.shuffle(possible_extra_pairs)
    extra_count = min(len(possible_extra_pairs), int(rng.randint(int(extra_min), int(extra_max))))
    for left, right in possible_extra_pairs[:extra_count]:
        equations.append({"left": [str(left), str(right)], "op": "+", "total": int(values[str(left)] + values[str(right)])})
    rng.shuffle(equations)
    return {
        "query_id": "letter_digit_value",
        "layout_style": "letter_equations",
        "letters": list(letters),
        "letter_count": int(letter_count),
        "letter_values": dict(values),
        "equations": equations,
        "equation_count": len(equations),
        "core_equation_pairs": [[str(left), str(right)] for left, right in core_pairs],
        "target_letter": str(target_letter),
        "answer_value": int(answer_value),
        "answer_range": [int(min(answer_support)), int(max(answer_support))],
        "target_answer_support": [int(value) for value in answer_support],
        "supporting_item_ids": [f"letter_{target_letter}"],
    }


def _build_cryptarithm_dataset(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    query_id: str,
    task_id: str,
) -> Dict[str, Any]:
    answer_value, answer_support = _resolve_answer_value(
        params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        query_id=str(query_id),
        task_id=str(task_id),
    )
    if str(query_id) == "hidden_addition_digit_value":
        return _sample_hidden_arithmetic_problem(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            answer_value=int(answer_value),
            operator="+",
            query_id=str(query_id),
            task_id=str(task_id),
        )
    if str(query_id) == "hidden_subtraction_digit_value":
        return _sample_hidden_arithmetic_problem(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            answer_value=int(answer_value),
            operator="-",
            query_id=str(query_id),
            task_id=str(task_id),
        )
    if str(query_id) == "letter_digit_value":
        return _build_letter_digit_dataset(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            answer_value=int(answer_value),
            answer_support=answer_support,
            task_id=str(task_id),
        )
    raise ValueError(f"unsupported cryptarithm query_id: {query_id}")


def _build_row_column_total_dataset(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    answer_value: int,
    answer_support: Sequence[int],
    task_id: str = OPERATOR_GRID_TASK_ID,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{task_id}.row_column_total")
    value_min, value_max = _get_range(
        params,
        gen_defaults,
        min_key="operator_grid_value_min",
        max_key="operator_grid_value_max",
        fallback_min=1,
        fallback_max=9,
    )
    row_count = _sample_int_from_range(
        params,
        gen_defaults,
        min_key="sum_grid_rows_min",
        max_key="sum_grid_rows_max",
        fallback_min=3,
        fallback_max=5,
        rng=rng,
    )
    col_count = _sample_int_from_range(
        params,
        gen_defaults,
        min_key="sum_grid_cols_min",
        max_key="sum_grid_cols_max",
        fallback_min=3,
        fallback_max=5,
        rng=rng,
    )
    target_row = int(rng.randrange(int(row_count)))
    target_col = int(rng.randrange(int(col_count)))
    grid: List[List[int]] = []
    for row in range(int(row_count)):
        row_values: List[int] = []
        for col in range(int(col_count)):
            if int(row) == int(target_row) and int(col) == int(target_col):
                row_values.append(int(answer_value))
            else:
                row_values.append(int(rng.randint(int(value_min), int(value_max))))
        grid.append(row_values)
    row_totals = [int(sum(row)) for row in grid]
    col_totals = [int(sum(grid[row][col] for row in range(int(row_count)))) for col in range(int(col_count))]
    target_cell_id = f"grid_cell_{target_row}_{target_col}"
    return {
        "query_id": "row_column_total_missing_value",
        "layout_style": "sum_grid",
        "grid": grid,
        "row_count": int(row_count),
        "col_count": int(col_count),
        "target_row": int(target_row),
        "target_col": int(target_col),
        "target_cell_id": str(target_cell_id),
        "row_totals": row_totals,
        "col_totals": col_totals,
        "answer_value": int(answer_value),
        "answer_range": [int(min(answer_support)), int(max(answer_support))],
        "target_answer_support": [int(value) for value in answer_support],
        "supporting_item_ids": [str(target_cell_id)],
    }


def _factor_pairs_for_answer(answer_value: int, *, max_factor: int) -> List[Tuple[int, int]]:
    pairs: List[Tuple[int, int]] = []
    for left in range(1, int(max_factor) + 1):
        if int(answer_value) % int(left) != 0:
            continue
        right = int(answer_value) // int(left)
        if 1 <= int(right) <= int(max_factor):
            pairs.append((int(left), int(right)))
    return pairs


def _compute_wall_levels(base: Sequence[int], *, operator: str) -> List[List[int]]:
    levels: List[List[int]] = [[int(value) for value in base]]
    while len(levels[-1]) > 1:
        previous = levels[-1]
        if str(operator) == "x":
            levels.append([int(previous[index] * previous[index + 1]) for index in range(len(previous) - 1)])
        elif str(operator) == "diff":
            levels.append([abs(int(previous[index]) - int(previous[index + 1])) for index in range(len(previous) - 1)])
        else:
            levels.append([int(previous[index] + previous[index + 1]) for index in range(len(previous) - 1)])
    return levels


def _build_operation_table_dataset(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    answer_value: int,
    answer_support: Sequence[int],
    task_id: str = OPERATOR_GRID_TASK_ID,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{task_id}.operation_table")
    max_header = _get_int(params, gen_defaults, "operation_table_header_max", 12)
    candidate_ops: List[str] = []
    if 2 <= int(answer_value) <= (2 * int(max_header)):
        candidate_ops.append("+")
    if _factor_pairs_for_answer(int(answer_value), max_factor=int(max_header)):
        candidate_ops.append("x")
    if not candidate_ops:
        raise RuntimeError("failed to build operation table with supported headers")
    operator = str(candidate_ops[int(rng.randrange(len(candidate_ops)))])
    if operator == "x":
        pair_options = _factor_pairs_for_answer(int(answer_value), max_factor=int(max_header))
        row_target, col_target = pair_options[int(rng.randrange(len(pair_options)))]
    else:
        low = max(1, int(answer_value) - int(max_header))
        high = min(int(max_header), int(answer_value) - 1)
        if int(low) > int(high):
            low, high = 1, int(max_header)
        row_target = int(rng.randint(int(low), int(high)))
        col_target = int(answer_value) - int(row_target)
        if int(col_target) < 1 or int(col_target) > int(max_header):
            col_target = max(1, min(int(max_header), int(col_target)))
            row_target = int(answer_value) - int(col_target)
    row_count = _sample_int_from_range(
        params,
        gen_defaults,
        min_key="operation_table_rows_min",
        max_key="operation_table_rows_max",
        fallback_min=2,
        fallback_max=4,
        rng=rng,
    )
    col_count = _sample_int_from_range(
        params,
        gen_defaults,
        min_key="operation_table_cols_min",
        max_key="operation_table_cols_max",
        fallback_min=2,
        fallback_max=4,
        rng=rng,
    )
    row_headers = [int(row_target)]
    col_headers = [int(col_target)]
    while len(row_headers) < int(row_count):
        value = int(rng.randint(1, int(max_header)))
        if value not in row_headers:
            row_headers.append(value)
    while len(col_headers) < int(col_count):
        value = int(rng.randint(1, int(max_header)))
        if value not in col_headers:
            col_headers.append(value)
    rng.shuffle(row_headers)
    rng.shuffle(col_headers)
    target_row = int(row_headers.index(int(row_target)))
    target_col = int(col_headers.index(int(col_target)))
    def cell_value(left: int, right: int) -> int:
        return int(left * right) if operator == "x" else int(left + right)
    grid = [[cell_value(left, right) for right in col_headers] for left in row_headers]
    target_cell_id = f"grid_cell_{target_row}_{target_col}"
    return {
        "query_id": "operation_table_cell_value",
        "layout_style": "operation_table",
        "operator": str(operator),
        "row_headers": [int(value) for value in row_headers],
        "col_headers": [int(value) for value in col_headers],
        "grid": grid,
        "row_count": int(row_count),
        "col_count": int(col_count),
        "target_row": int(target_row),
        "target_col": int(target_col),
        "target_cell_id": str(target_cell_id),
        "answer_value": int(answer_value),
        "answer_range": [int(min(answer_support)), int(max(answer_support))],
        "target_answer_support": [int(value) for value in answer_support],
        "supporting_item_ids": [str(target_cell_id)],
    }


def _build_operator_grid_dataset(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    query_id: str,
    task_id: str,
) -> Dict[str, Any]:
    answer_value, answer_support = _resolve_answer_value(
        params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        query_id=str(query_id),
        task_id=str(task_id),
    )
    if str(query_id) == "row_column_total_missing_value":
        return _build_row_column_total_dataset(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            answer_value=int(answer_value),
            answer_support=answer_support,
            task_id=str(task_id),
        )
    if str(query_id) == "operation_table_cell_value":
        return _build_operation_table_dataset(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            answer_value=int(answer_value),
            answer_support=answer_support,
            task_id=str(task_id),
        )
    raise ValueError(f"unsupported operator-grid query_id: {query_id}")


def _build_addition_wall_dataset(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    answer_value: int,
    answer_support: Sequence[int],
    task_id: str = NUMBER_WALL_TASK_ID,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{task_id}.addition_wall")
    value_min, value_max = _get_range(
        params,
        gen_defaults,
        min_key="wall_base_value_min",
        max_key="wall_base_value_max",
        fallback_min=1,
        fallback_max=18,
    )
    base_count = _sample_int_from_range(
        params,
        gen_defaults,
        min_key="addition_wall_base_count_min",
        max_key="addition_wall_base_count_max",
        fallback_min=3,
        fallback_max=5,
        rng=rng,
    )
    base_count = max(3, int(base_count))
    for _attempt in range(700):
        left = int(rng.randint(int(value_min), min(int(value_max), max(int(value_min), int(answer_value) - 1))))
        right = int(answer_value) - int(left)
        if not int(value_min) <= int(right) <= int(value_max):
            continue
        target_index = int(rng.randrange(int(base_count) - 1))
        base = [int(rng.randint(int(value_min), int(value_max))) for _ in range(int(base_count))]
        base[int(target_index)] = int(left)
        base[int(target_index) + 1] = int(right)
        levels = _compute_wall_levels(base, operator="+")
        target_cell_id = f"wall_cell_1_{target_index}"
        return {
            "query_id": "addition_wall_missing_value",
            "layout_style": "addition_wall",
            "operator": "+",
            "levels": levels,
            "base_count": int(base_count),
            "target_level": 1,
            "target_index": int(target_index),
            "target_cell_id": str(target_cell_id),
            "answer_value": int(answer_value),
            "answer_range": [int(min(answer_support)), int(max(answer_support))],
            "target_answer_support": [int(value) for value in answer_support],
            "supporting_item_ids": [str(target_cell_id)],
        }
    raise RuntimeError("failed to build addition-wall puzzle")


def _build_difference_wall_dataset(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    answer_value: int,
    answer_support: Sequence[int],
    task_id: str = NUMBER_WALL_TASK_ID,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{task_id}.difference_wall")
    value_min, value_max = _get_range(
        params,
        gen_defaults,
        min_key="difference_wall_base_value_min",
        max_key="difference_wall_base_value_max",
        fallback_min=1,
        fallback_max=18,
    )
    base_count = _sample_int_from_range(
        params,
        gen_defaults,
        min_key="difference_wall_base_count_min",
        max_key="difference_wall_base_count_max",
        fallback_min=4,
        fallback_max=5,
        rng=rng,
    )
    base_count = max(4, int(base_count))
    if int(answer_value) <= 0 or int(answer_value) > int(value_max) - int(value_min):
        raise RuntimeError("difference-wall answer is outside constructible support")
    for _attempt in range(700):
        low = int(value_min)
        high = int(value_max) - int(answer_value)
        if low > high:
            break
        left = int(rng.randint(low, high))
        right = int(left + int(answer_value))
        if int(rng.randrange(2)) == 0:
            left, right = right, left
        target_index = int(rng.randrange(int(base_count) - 1))
        base = [int(rng.randint(int(value_min), int(value_max))) for _ in range(int(base_count))]
        base[int(target_index)] = int(left)
        base[int(target_index) + 1] = int(right)
        levels = _compute_wall_levels(base, operator="diff")
        target_cell_id = f"wall_cell_1_{target_index}"
        return {
            "query_id": "difference_wall_missing_value",
            "layout_style": "difference_wall",
            "operator": "diff",
            "levels": levels,
            "base_count": int(base_count),
            "target_level": 1,
            "target_index": int(target_index),
            "target_cell_id": str(target_cell_id),
            "answer_value": int(answer_value),
            "answer_range": [int(min(answer_support)), int(max(answer_support))],
            "target_answer_support": [int(value) for value in answer_support],
            "supporting_item_ids": [str(target_cell_id)],
        }
    raise RuntimeError("failed to build difference-wall puzzle")


def _build_multiplication_pyramid_dataset(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    answer_value: int,
    answer_support: Sequence[int],
    task_id: str = NUMBER_WALL_TASK_ID,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{task_id}.multiplication_pyramid")
    max_factor = _get_int(params, gen_defaults, "pyramid_factor_max", 12)
    filler_max = _get_int(params, gen_defaults, "pyramid_filler_factor_max", 2)
    visible_max = _get_int(params, gen_defaults, "pyramid_visible_value_max", 99999)
    base_count = _sample_int_from_range(
        params,
        gen_defaults,
        min_key="multiplication_pyramid_base_count_min",
        max_key="multiplication_pyramid_base_count_max",
        fallback_min=3,
        fallback_max=4,
        rng=rng,
    )
    base_count = max(3, int(base_count))
    factors = _factor_pairs_for_answer(int(answer_value), max_factor=int(max_factor))
    if not factors:
        factors = [(1, int(answer_value))]
    for _attempt in range(700):
        left, right = factors[int(rng.randrange(len(factors)))]
        target_index = int(rng.randrange(int(base_count) - 1))
        base = [int(rng.randint(1, max(1, int(filler_max)))) for _ in range(int(base_count))]
        base[int(target_index)] = int(left)
        base[int(target_index) + 1] = int(right)
        levels = _compute_wall_levels(base, operator="x")
        if max(int(value) for row in levels for value in row) > int(visible_max):
            continue
        target_cell_id = f"wall_cell_1_{target_index}"
        return {
            "query_id": "multiplication_pyramid_value",
            "layout_style": "multiplication_pyramid",
            "operator": "x",
            "levels": levels,
            "base_count": int(base_count),
            "target_level": 1,
            "target_index": int(target_index),
            "target_cell_id": str(target_cell_id),
            "answer_value": int(answer_value),
            "answer_range": [int(min(answer_support)), int(max(answer_support))],
            "target_answer_support": [int(value) for value in answer_support],
            "supporting_item_ids": [str(target_cell_id)],
        }
    raise RuntimeError("failed to build multiplication-pyramid puzzle")


def _build_number_wall_dataset(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    query_id: str,
    task_id: str,
) -> Dict[str, Any]:
    answer_value, answer_support = _resolve_answer_value(
        params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        query_id=str(query_id),
        task_id=str(task_id),
    )
    if str(query_id) == "addition_wall_missing_value":
        return _build_addition_wall_dataset(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            answer_value=int(answer_value),
            answer_support=answer_support,
            task_id=str(task_id),
        )
    if str(query_id) == "difference_wall_missing_value":
        return _build_difference_wall_dataset(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            answer_value=int(answer_value),
            answer_support=answer_support,
            task_id=str(task_id),
        )
    if str(query_id) == "multiplication_pyramid_value":
        return _build_multiplication_pyramid_dataset(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            answer_value=int(answer_value),
            answer_support=answer_support,
            task_id=str(task_id),
        )
    raise ValueError(f"unsupported number-wall query_id: {query_id}")


def _build_dataset(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    query_id: str,
    task_id: str = TASK_ID,
) -> Dict[str, Any]:
    if str(task_id) == CRYPTARITHM_TASK_ID:
        return _build_cryptarithm_dataset(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            query_id=str(query_id),
            task_id=str(task_id),
        )
    if str(task_id) == OPERATOR_GRID_TASK_ID:
        return _build_operator_grid_dataset(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            query_id=str(query_id),
            task_id=str(task_id),
        )
    if str(task_id) == NUMBER_WALL_TASK_ID:
        return _build_number_wall_dataset(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            query_id=str(query_id),
            task_id=str(task_id),
        )
    answer_value, answer_support = _resolve_answer_value(
        params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        query_id=str(query_id),
        task_id=str(task_id),
    )
    if str(query_id) == "equal_sum_line_constraint_value":
        return _build_equal_sum_dataset(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            answer_value=int(answer_value),
            answer_support=answer_support,
            task_id=str(task_id),
        )
    if str(query_id) == "paired_cluster_sum_relation_value":
        return _build_cluster_dataset(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            answer_value=int(answer_value),
            answer_support=answer_support,
            task_id=str(task_id),
        )
    if str(query_id) == "consecutive_window_sum_value":
        return _build_consecutive_dataset(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            answer_value=int(answer_value),
            answer_support=answer_support,
            task_id=str(task_id),
        )
    raise ValueError(f"unsupported arithmetic constraint query_id: {query_id}")


def _resolve_render_params(
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    *,
    instance_seed: int,
    task_id: str = TASK_ID,
) -> ArithmeticRenderParams:
    unit_scale, unit_meta = resolve_puzzle_unit_size_scale(
        params,
        render_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.unit_size",
    )
    return ArithmeticRenderParams(
        canvas_width=int(render_defaults.get("canvas_width", 1080)),
        canvas_height=int(render_defaults.get("canvas_height", 760)),
        panel_padding_px=scale_puzzle_px(render_defaults.get("panel_padding_px", 26), unit_scale, min_px=14),
        panel_corner_radius_px=scale_puzzle_px(render_defaults.get("panel_corner_radius_px", 22), unit_scale, min_px=8),
        panel_border_width_px=scale_puzzle_px(render_defaults.get("panel_border_width_px", 3), unit_scale, min_px=2),
        node_radius_px=scale_puzzle_px(render_defaults.get("node_radius_px", 38), unit_scale, min_px=22),
        cell_width_px=scale_puzzle_px(render_defaults.get("cell_width_px", 84), unit_scale, min_px=48),
        cell_height_px=scale_puzzle_px(render_defaults.get("cell_height_px", 72), unit_scale, min_px=42),
        line_width_px=scale_puzzle_px(render_defaults.get("line_width_px", 4), unit_scale, min_px=2),
        value_font_size_px=scale_puzzle_px(render_defaults.get("value_font_size_px", 34), unit_scale, min_px=18),
        note_font_size_px=scale_puzzle_px(render_defaults.get("note_font_size_px", 25), unit_scale, min_px=15),
        symbol_font_size_px=scale_puzzle_px(render_defaults.get("symbol_font_size_px", 30), unit_scale, min_px=17),
        unit_size_jitter=dict(unit_meta),
    )


def _panel_bbox(render_params: ArithmeticRenderParams) -> Tuple[int, int, int, int]:
    margin_x = max(28, int(0.07 * int(render_params.canvas_width)))
    margin_y = max(28, int(0.08 * int(render_params.canvas_height)))
    return (
        int(margin_x),
        int(margin_y),
        int(render_params.canvas_width) - int(margin_x),
        int(render_params.canvas_height) - int(margin_y),
    )


def _draw_note(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    center: Tuple[float, float],
    font,
    fill: Sequence[int],
    stroke_fill: Sequence[int],
    max_width_px: int,
) -> List[float]:
    words = str(text).split()
    lines: List[str] = []
    current = ""
    for word in words:
        candidate = str(word) if not current else f"{current} {word}"
        bbox = draw.textbbox((0, 0), candidate, font=font, stroke_width=1)
        if bbox[2] - bbox[0] <= int(max_width_px) or not current:
            current = candidate
        else:
            lines.append(current)
            current = str(word)
    if current:
        lines.append(current)
    line_height = max(1, int(font.size * 1.12) if hasattr(font, "size") else 24)
    total_h = int(line_height * len(lines))
    cx, cy = float(center[0]), float(center[1])
    bboxes: List[List[float]] = []
    for index, line in enumerate(lines):
        y = float(cy - (total_h / 2.0) + (index * line_height) + (line_height / 2.0))
        bboxes.append(
            draw_centered_text(
                draw,
                text=str(line),
                center=(cx, y),
                font=font,
                fill=fill,
                stroke_fill=stroke_fill,
                stroke_width=1,
            )
        )
    return [
        min(bbox[0] for bbox in bboxes),
        min(bbox[1] for bbox in bboxes),
        max(bbox[2] for bbox in bboxes),
        max(bbox[3] for bbox in bboxes),
    ]


def _draw_number_node(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    radius: float,
    value: int | str,
    hidden: bool,
    fill: Sequence[int],
    outline: Sequence[int],
    mark: Sequence[int],
    text_fill: Sequence[int],
    stroke_fill: Sequence[int],
    font,
    line_width: int,
) -> List[float]:
    cx, cy = float(center[0]), float(center[1])
    radius = float(radius)
    bbox = (cx - radius, cy - radius, cx + radius, cy + radius)
    node_fill = tuple(int(value) for value in (fill if not hidden else (255, 245, 178)))
    outline_rgb = tuple(int(value) for value in (mark if hidden else outline))
    draw.ellipse(bbox, fill=node_fill, outline=outline_rgb, width=max(1, int(line_width)))
    if hidden:
        draw.ellipse(
            (bbox[0] - 5, bbox[1] - 5, bbox[2] + 5, bbox[3] + 5),
            outline=tuple(int(value) for value in mark),
            width=max(3, int(line_width) + 1),
        )
    draw_centered_text(
        draw,
        text="?" if hidden else str(value),
        center=(cx, cy),
        font=font,
        fill=text_fill,
        stroke_fill=stroke_fill,
        stroke_width=1,
    )
    return _round_bbox(bbox)


def _draw_boxed_value(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Tuple[float, float, float, float],
    text: str,
    hidden: bool,
    fill: Sequence[int],
    outline: Sequence[int],
    mark: Sequence[int],
    text_fill: Sequence[int],
    stroke_fill: Sequence[int],
    font,
    radius: int,
    line_width: int,
) -> List[float]:
    draw_rounded_rect(
        draw,
        tuple(float(value) for value in bbox),
        radius=int(radius),
        fill=(255, 245, 178) if hidden else fill,
        outline=mark if hidden else outline,
        width=max(1, int(line_width)),
    )
    if hidden:
        draw.rounded_rectangle(
            (bbox[0] - 4, bbox[1] - 4, bbox[2] + 4, bbox[3] + 4),
            radius=int(radius) + 4,
            outline=tuple(int(value) for value in mark),
            width=max(3, int(line_width) + 1),
        )
    draw_centered_text(
        draw,
        text=str(text),
        center=((float(bbox[0]) + float(bbox[2])) / 2.0, (float(bbox[1]) + float(bbox[3])) / 2.0),
        font=font,
        fill=text_fill,
        stroke_fill=stroke_fill,
        stroke_width=1,
    )
    return _round_bbox(bbox)


def _draw_disabled_table_corner(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Tuple[float, float, float, float],
    fill: Sequence[int],
    panel_fill: Sequence[int],
    outline: Sequence[int],
    radius: int,
    line_width: int,
) -> List[float]:
    disabled_fill = tuple(
        int((0.58 * int(fill[index])) + (0.42 * int(panel_fill[index])))
        for index in range(3)
    )
    draw_rounded_rect(
        draw,
        tuple(float(value) for value in bbox),
        radius=int(radius),
        fill=disabled_fill,
        outline=outline,
        width=max(1, int(line_width)),
    )
    inset = max(7, int(min(float(bbox[2]) - float(bbox[0]), float(bbox[3]) - float(bbox[1])) * 0.18))
    hatch_width = max(1, int(line_width))
    draw.line(
        [(float(bbox[0]) + inset, float(bbox[3]) - inset), (float(bbox[2]) - inset, float(bbox[1]) + inset)],
        fill=outline,
        width=hatch_width,
    )
    return _round_bbox(bbox)


def _render_equal_sum(
    draw: ImageDraw.ImageDraw,
    *,
    dataset: Mapping[str, Any],
    panel_bbox: Tuple[int, int, int, int],
    render_params: ArithmeticRenderParams,
    colors: Mapping[str, Tuple[int, int, int]],
    item_bbox_map: Dict[str, List[float]],
    entities: List[Dict[str, Any]],
) -> None:
    value_font = load_font(int(render_params.value_font_size_px), bold=True)
    note_font = load_font(int(render_params.note_font_size_px), bold=True)
    side_count = int(dataset["side_count"])
    cx = (panel_bbox[0] + panel_bbox[2]) / 2.0
    cy = panel_bbox[1] + (0.54 * (panel_bbox[3] - panel_bbox[1]))
    radius = min(panel_bbox[2] - panel_bbox[0], panel_bbox[3] - panel_bbox[1]) * 0.285
    if side_count == 3:
        angle0 = -math.pi / 2.0
    elif side_count == 4:
        angle0 = -math.pi / 4.0
    else:
        angle0 = -math.pi / 2.0
    corners = [
        (cx + (radius * math.cos(angle0 + (2.0 * math.pi * index / side_count))), cy + (radius * math.sin(angle0 + (2.0 * math.pi * index / side_count))))
        for index in range(side_count)
    ]
    midpoints = [
        ((corners[index][0] + corners[(index + 1) % side_count][0]) / 2.0, (corners[index][1] + corners[(index + 1) % side_count][1]) / 2.0)
        for index in range(side_count)
    ]
    draw.line(corners + [corners[0]], fill=colors["line"], width=max(2, int(render_params.line_width_px)))
    note_bbox = _draw_note(
        draw,
        text=f"Each side total = {int(dataset['side_total'])}",
        center=(cx, panel_bbox[1] + int(render_params.panel_padding_px) + 22),
        font=note_font,
        fill=colors["text"],
        stroke_fill=colors["stroke"],
        max_width_px=int(panel_bbox[2] - panel_bbox[0] - 90),
    )
    item_bbox_map["constraint_note"] = _round_bbox(note_bbox)
    for node in dataset["nodes"]:
        node_id = str(node["node_id"])
        pos = corners[int(node["index"])] if str(node["kind"]) == "corner" else midpoints[int(node["index"])]
        bbox = _draw_number_node(
            draw,
            center=pos,
            radius=float(render_params.node_radius_px),
            value=int(node["value"]),
            hidden=bool(node["hidden"]),
            fill=colors["node_fill"],
            outline=colors["line"],
            mark=colors["mark"],
            text_fill=colors["text"],
            stroke_fill=colors["stroke"],
            font=value_font,
            line_width=int(render_params.line_width_px),
        )
        item_bbox_map[node_id] = list(bbox)
        entities.append(
            {
                "entity_id": str(node_id),
                "entity_type": "arithmetic_side_node",
                "bbox_px": list(bbox),
                "value": int(node["value"]),
                "hidden": bool(node["hidden"]),
            }
        )


def _cluster_positions(
    *,
    center: Tuple[float, float],
    leaf_count: int,
    radius: float,
    layout_style: str,
) -> List[Tuple[float, float]]:
    cx, cy = float(center[0]), float(center[1])
    if str(layout_style) == "star":
        angle0 = -math.pi / 2.0
    elif str(layout_style) == "polygon_cluster":
        angle0 = -math.pi / 3.0
    else:
        angle0 = -math.pi / 2.0
    return [
        (cx + radius * math.cos(angle0 + (2.0 * math.pi * index / int(leaf_count))), cy + radius * math.sin(angle0 + (2.0 * math.pi * index / int(leaf_count))))
        for index in range(int(leaf_count))
    ]


def _render_cluster(
    draw: ImageDraw.ImageDraw,
    *,
    dataset: Mapping[str, Any],
    panel_bbox: Tuple[int, int, int, int],
    render_params: ArithmeticRenderParams,
    colors: Mapping[str, Tuple[int, int, int]],
    item_bbox_map: Dict[str, List[float]],
    entities: List[Dict[str, Any]],
) -> None:
    value_font = load_font(int(render_params.value_font_size_px), bold=True)
    note_font = load_font(int(render_params.note_font_size_px), bold=True)
    left_center = (panel_bbox[0] + (0.31 * (panel_bbox[2] - panel_bbox[0])), panel_bbox[1] + (0.56 * (panel_bbox[3] - panel_bbox[1])))
    right_center = (panel_bbox[0] + (0.69 * (panel_bbox[2] - panel_bbox[0])), panel_bbox[1] + (0.56 * (panel_bbox[3] - panel_bbox[1])))
    leaf_count = len(dataset["left_values"])
    orbit = max(float(render_params.node_radius_px) * 2.25, min(panel_bbox[2] - panel_bbox[0], panel_bbox[3] - panel_bbox[1]) * 0.145)
    note_bbox = _draw_note(
        draw,
        text=str(dataset["relation_text"]),
        center=((panel_bbox[0] + panel_bbox[2]) / 2.0, panel_bbox[1] + int(render_params.panel_padding_px) + 28),
        font=note_font,
        fill=colors["text"],
        stroke_fill=colors["stroke"],
        max_width_px=int(panel_bbox[2] - panel_bbox[0] - 90),
    )
    item_bbox_map["constraint_note"] = _round_bbox(note_bbox)
    for side_name, center, values in (("left", left_center, list(dataset["left_values"])), ("right", right_center, list(dataset["right_values"]))):
        positions = _cluster_positions(center=center, leaf_count=leaf_count, radius=float(orbit), layout_style=str(dataset["layout_style"]))
        for position in positions:
            draw.line([center, position], fill=colors["line"], width=max(1, int(render_params.line_width_px) - 1))
        center_bbox = _draw_number_node(
            draw,
            center=center,
            radius=float(render_params.node_radius_px) * 0.75,
            value="L" if side_name == "left" else "R",
            hidden=False,
            fill=colors["center_fill"],
            outline=colors["line"],
            mark=colors["mark"],
            text_fill=colors["text"],
            stroke_fill=colors["stroke"],
            font=load_font(max(14, int(render_params.note_font_size_px)), bold=True),
            line_width=max(1, int(render_params.line_width_px) - 1),
        )
        item_bbox_map[f"{side_name}_cluster_center"] = list(center_bbox)
        for index, value in enumerate(values):
            node_id = f"{side_name}_leaf_{index}"
            hidden = bool(side_name == str(dataset["hidden_side"]) and int(index) == int(dataset["hidden_index"]))
            bbox = _draw_number_node(
                draw,
                center=positions[int(index)],
                radius=float(render_params.node_radius_px),
                value=int(value),
                hidden=hidden,
                fill=colors["node_fill"],
                outline=colors["line"],
                mark=colors["mark"],
                text_fill=colors["text"],
                stroke_fill=colors["stroke"],
                font=value_font,
                line_width=int(render_params.line_width_px),
            )
            item_bbox_map[node_id] = list(bbox)
            entities.append(
                {
                    "entity_id": str(node_id),
                    "entity_type": "arithmetic_cluster_leaf",
                    "bbox_px": list(bbox),
                    "cluster": str(side_name),
                    "value": int(value),
                    "hidden": bool(hidden),
                }
            )


def _render_consecutive(
    draw: ImageDraw.ImageDraw,
    *,
    dataset: Mapping[str, Any],
    panel_bbox: Tuple[int, int, int, int],
    render_params: ArithmeticRenderParams,
    colors: Mapping[str, Tuple[int, int, int]],
    item_bbox_map: Dict[str, List[float]],
    entities: List[Dict[str, Any]],
) -> None:
    value_font = load_font(int(render_params.value_font_size_px), bold=True)
    note_font = load_font(int(render_params.note_font_size_px), bold=True)
    values = [int(value) for value in dataset["sequence_values"]]
    length = len(values)
    note_bbox = _draw_note(
        draw,
        text=f"Every {int(dataset['window_size'])} adjacent cells total {int(dataset['window_total'])}",
        center=((panel_bbox[0] + panel_bbox[2]) / 2.0, panel_bbox[1] + int(render_params.panel_padding_px) + 28),
        font=note_font,
        fill=colors["text"],
        stroke_fill=colors["stroke"],
        max_width_px=int(panel_bbox[2] - panel_bbox[0] - 90),
    )
    item_bbox_map["constraint_note"] = _round_bbox(note_bbox)
    if str(dataset["layout_style"]) == "bead_arc":
        cx = (panel_bbox[0] + panel_bbox[2]) / 2.0
        cy = panel_bbox[1] + (0.62 * (panel_bbox[3] - panel_bbox[1]))
        arc_radius = min(panel_bbox[2] - panel_bbox[0], panel_bbox[3] - panel_bbox[1]) * 0.32
        angles = [math.pi * (1.1 + (0.8 * index / max(1, length - 1))) for index in range(length)]
        positions = [(cx + arc_radius * math.cos(angle), cy + arc_radius * math.sin(angle)) for angle in angles]
        draw.line(positions, fill=colors["line"], width=max(2, int(render_params.line_width_px)))
        for index, value in enumerate(values):
            bbox = _draw_number_node(
                draw,
                center=positions[index],
                radius=float(render_params.node_radius_px),
                value=int(value),
                hidden=bool(index == int(dataset["hidden_index"])),
                fill=colors["node_fill"],
                outline=colors["line"],
                mark=colors["mark"],
                text_fill=colors["text"],
                stroke_fill=colors["stroke"],
                font=value_font,
                line_width=int(render_params.line_width_px),
            )
            item_bbox_map[f"cell_{index}"] = list(bbox)
            entities.append({"entity_id": f"cell_{index}", "entity_type": "arithmetic_window_cell", "bbox_px": list(bbox), "value": int(value), "hidden": bool(index == int(dataset["hidden_index"]))})
        return

    total_w = int(length) * int(render_params.cell_width_px)
    x0 = int((panel_bbox[0] + panel_bbox[2] - total_w) / 2.0)
    y0 = int(panel_bbox[1] + (0.54 * (panel_bbox[3] - panel_bbox[1])))
    for index, value in enumerate(values):
        bbox = (
            x0 + (index * int(render_params.cell_width_px)),
            y0,
            x0 + ((index + 1) * int(render_params.cell_width_px)),
            y0 + int(render_params.cell_height_px),
        )
        cell_bbox = _draw_boxed_value(
            draw,
            bbox=bbox,
            text="?" if int(index) == int(dataset["hidden_index"]) else str(value),
            hidden=bool(index == int(dataset["hidden_index"])),
            fill=colors["node_fill"],
            outline=colors["line"],
            mark=colors["mark"],
            text_fill=colors["text"],
            stroke_fill=colors["stroke"],
            font=value_font,
            radius=max(5, int(render_params.panel_corner_radius_px) // 2),
            line_width=int(render_params.line_width_px),
        )
        item_bbox_map[f"cell_{index}"] = list(cell_bbox)
        entities.append({"entity_id": f"cell_{index}", "entity_type": "arithmetic_window_cell", "bbox_px": list(cell_bbox), "value": int(value), "hidden": bool(index == int(dataset["hidden_index"]))})


def _render_cryptarithm(
    draw: ImageDraw.ImageDraw,
    *,
    dataset: Mapping[str, Any],
    panel_bbox: Tuple[int, int, int, int],
    render_params: ArithmeticRenderParams,
    colors: Mapping[str, Tuple[int, int, int]],
    item_bbox_map: Dict[str, List[float]],
    entities: List[Dict[str, Any]],
) -> None:
    value_font = load_font(int(render_params.value_font_size_px), bold=True)
    note_font = load_font(int(render_params.note_font_size_px), bold=True)
    query_id = str(dataset["query_id"])
    if query_id == "letter_digit_value":
        note_bbox = _draw_note(
            draw,
            text="Different letters stand for different digits",
            center=((panel_bbox[0] + panel_bbox[2]) / 2.0, panel_bbox[1] + int(render_params.panel_padding_px) + 28),
            font=note_font,
            fill=colors["text"],
            stroke_fill=colors["stroke"],
            max_width_px=int(panel_bbox[2] - panel_bbox[0] - 90),
        )
        item_bbox_map["constraint_note"] = _round_bbox(note_bbox)
        equations = list(dataset["equations"])
        row_h = int(render_params.cell_height_px)
        box_w = max(70, int(render_params.cell_width_px))
        gap = 18
        total_w = (3 * box_w) + (3 * gap) + 90
        x0 = int((panel_bbox[0] + panel_bbox[2] - total_w) / 2.0)
        y0 = int(panel_bbox[1] + 0.31 * (panel_bbox[3] - panel_bbox[1]))
        target_letter = str(dataset["target_letter"])
        target_letter_highlighted = False
        for row_index, equation in enumerate(equations):
            y = y0 + (row_index * (row_h + 16))
            left_letters = [str(item) for item in equation["left"]]
            tokens = [left_letters[0], str(equation["op"]), left_letters[1], "=", str(equation["total"])]
            x = x0
            for token_index, token in enumerate(tokens):
                if token_index in {1, 3}:
                    draw_centered_text(
                        draw,
                        text=str(token),
                        center=(x + gap, y + (row_h / 2.0)),
                        font=note_font,
                        fill=colors["text"],
                        stroke_fill=colors["stroke"],
                        stroke_width=1,
                    )
                    x += 2 * gap
                    continue
                bbox = (x, y, x + box_w, y + row_h)
                is_target = str(token) == target_letter and not target_letter_highlighted
                cell_bbox = _draw_boxed_value(
                    draw,
                    bbox=bbox,
                    text=str(token),
                    hidden=False,
                    fill=(255, 245, 178) if is_target else colors["node_fill"],
                    outline=colors["line"],
                    mark=colors["mark"],
                    text_fill=colors["text"],
                    stroke_fill=colors["stroke"],
                    font=value_font,
                    radius=max(5, int(render_params.panel_corner_radius_px) // 2),
                    line_width=int(render_params.line_width_px),
                )
                if is_target:
                    target_letter_highlighted = True
                    item_bbox_map[f"letter_{target_letter}"] = list(cell_bbox)
                    entities.append(
                        {
                            "entity_id": f"letter_{target_letter}",
                            "entity_type": "cryptarithm_target_letter",
                            "bbox_px": list(cell_bbox),
                            "letter": str(target_letter),
                            "value": int(dataset["answer_value"]),
                        }
                    )
                x += box_w + gap
        target_note_bbox = _draw_note(
            draw,
            text=f"What digit is {target_letter}?",
            center=((panel_bbox[0] + panel_bbox[2]) / 2.0, panel_bbox[3] - int(render_params.panel_padding_px) - 28),
            font=note_font,
            fill=colors["text"],
            stroke_fill=colors["stroke"],
            max_width_px=int(panel_bbox[2] - panel_bbox[0] - 90),
        )
        item_bbox_map["target_note"] = _round_bbox(target_note_bbox)
        return

    rows = list(dataset["rows"])
    width = len(rows[0]["digits"])
    cell_w = int(render_params.cell_width_px)
    cell_h = int(render_params.cell_height_px)
    row_gap = 12
    total_w = (width * cell_w) + 68
    x0 = int((panel_bbox[0] + panel_bbox[2] - total_w) / 2.0)
    y0 = int(panel_bbox[1] + 0.28 * (panel_bbox[3] - panel_bbox[1]))
    note_text = "Fill the missing digit so the addition is correct" if str(dataset["operator"]) == "+" else "Fill the missing digit so the subtraction is correct"
    note_bbox = _draw_note(
        draw,
        text=note_text,
        center=((panel_bbox[0] + panel_bbox[2]) / 2.0, panel_bbox[1] + int(render_params.panel_padding_px) + 28),
        font=note_font,
        fill=colors["text"],
        stroke_fill=colors["stroke"],
        max_width_px=int(panel_bbox[2] - panel_bbox[0] - 90),
    )
    item_bbox_map["constraint_note"] = _round_bbox(note_bbox)
    hidden_row_index = int(dataset["hidden_row_index"])
    hidden_col_index = int(dataset["hidden_col_index"])
    for row_index, row in enumerate(rows):
        y = y0 + (row_index * (cell_h + row_gap))
        prefix = str(row.get("prefix", ""))
        if prefix:
            draw_centered_text(
                draw,
                text=prefix,
                center=(x0 + 24, y + (cell_h / 2.0)),
                font=value_font,
                fill=colors["text"],
                stroke_fill=colors["stroke"],
                stroke_width=1,
            )
        for col_index, digit in enumerate(row["digits"]):
            hidden = bool(row_index == hidden_row_index and col_index == hidden_col_index)
            bbox = (
                x0 + 52 + (col_index * cell_w),
                y,
                x0 + 52 + ((col_index + 1) * cell_w),
                y + cell_h,
            )
            cell_id = f"{row['row_id']}_digit_{col_index}"
            cell_bbox = _draw_boxed_value(
                draw,
                bbox=bbox,
                text="?" if hidden else str(digit),
                hidden=hidden,
                fill=colors["node_fill"],
                outline=colors["line"],
                mark=colors["mark"],
                text_fill=colors["text"],
                stroke_fill=colors["stroke"],
                font=value_font,
                radius=max(5, int(render_params.panel_corner_radius_px) // 2),
                line_width=int(render_params.line_width_px),
            )
            item_bbox_map[str(cell_id)] = list(cell_bbox)
            entities.append(
                {
                    "entity_id": str(cell_id),
                    "entity_type": "cryptarithm_digit_cell",
                    "bbox_px": list(cell_bbox),
                    "row_id": str(row["row_id"]),
                    "col_index": int(col_index),
                    "value": int(digit),
                    "hidden": bool(hidden),
                }
            )
    line_y = y0 + ((len(rows) - 1) * (cell_h + row_gap)) - int(row_gap / 2)
    draw.line(
        [(x0 + 44, line_y), (x0 + 52 + width * cell_w, line_y)],
        fill=colors["line"],
        width=max(2, int(render_params.line_width_px)),
    )


def _render_operator_grid(
    draw: ImageDraw.ImageDraw,
    *,
    dataset: Mapping[str, Any],
    panel_bbox: Tuple[int, int, int, int],
    render_params: ArithmeticRenderParams,
    colors: Mapping[str, Tuple[int, int, int]],
    item_bbox_map: Dict[str, List[float]],
    entities: List[Dict[str, Any]],
) -> None:
    value_font = load_font(int(render_params.value_font_size_px), bold=True)
    note_font = load_font(int(render_params.note_font_size_px), bold=True)
    grid = [[int(value) for value in row] for row in dataset["grid"]]
    row_count = len(grid)
    col_count = len(grid[0]) if grid else 0
    cell_w = int(render_params.cell_width_px)
    cell_h = int(render_params.cell_height_px)
    query_id = str(dataset["query_id"])
    note_text = "Find the missing grid value"
    note_bbox = _draw_note(
        draw,
        text=note_text,
        center=((panel_bbox[0] + panel_bbox[2]) / 2.0, panel_bbox[1] + int(render_params.panel_padding_px) + 28),
        font=note_font,
        fill=colors["text"],
        stroke_fill=colors["stroke"],
        max_width_px=int(panel_bbox[2] - panel_bbox[0] - 90),
    )
    item_bbox_map["constraint_note"] = _round_bbox(note_bbox)
    extra_left = cell_w if query_id == "operation_table_cell_value" else 0
    extra_top = cell_h if query_id == "operation_table_cell_value" else 0
    extra_right = cell_w if query_id == "row_column_total_missing_value" else 0
    extra_bottom = cell_h if query_id == "row_column_total_missing_value" else 0
    total_w = extra_left + (col_count * cell_w) + extra_right
    total_h = extra_top + (row_count * cell_h) + extra_bottom
    x0 = int((panel_bbox[0] + panel_bbox[2] - total_w) / 2.0)
    y0 = int(panel_bbox[1] + 0.30 * (panel_bbox[3] - panel_bbox[1]))
    if query_id == "operation_table_cell_value":
        op_bbox = (x0, y0, x0 + cell_w, y0 + cell_h)
        _draw_disabled_table_corner(
            draw,
            bbox=op_bbox,
            fill=colors["center_fill"],
            panel_fill=colors["panel_fill"],
            outline=colors["line"],
            radius=max(5, int(render_params.panel_corner_radius_px) // 2),
            line_width=int(render_params.line_width_px),
        )
        for col, value in enumerate(dataset["col_headers"]):
            _draw_boxed_value(
                draw,
                bbox=(x0 + extra_left + col * cell_w, y0, x0 + extra_left + (col + 1) * cell_w, y0 + cell_h),
                text=str(value),
                hidden=False,
                fill=colors["center_fill"],
                outline=colors["line"],
                mark=colors["mark"],
                text_fill=colors["text"],
                stroke_fill=colors["stroke"],
                font=value_font,
                radius=max(5, int(render_params.panel_corner_radius_px) // 2),
                line_width=int(render_params.line_width_px),
            )
        for row, value in enumerate(dataset["row_headers"]):
            _draw_boxed_value(
                draw,
                bbox=(x0, y0 + extra_top + row * cell_h, x0 + cell_w, y0 + extra_top + (row + 1) * cell_h),
                text=str(value),
                hidden=False,
                fill=colors["center_fill"],
                outline=colors["line"],
                mark=colors["mark"],
                text_fill=colors["text"],
                stroke_fill=colors["stroke"],
                font=value_font,
                radius=max(5, int(render_params.panel_corner_radius_px) // 2),
                line_width=int(render_params.line_width_px),
            )
    target_row = int(dataset["target_row"])
    target_col = int(dataset["target_col"])
    for row in range(row_count):
        for col in range(col_count):
            hidden = bool(row == target_row and col == target_col)
            cell_id = f"grid_cell_{row}_{col}"
            bbox = (
                x0 + extra_left + col * cell_w,
                y0 + extra_top + row * cell_h,
                x0 + extra_left + (col + 1) * cell_w,
                y0 + extra_top + (row + 1) * cell_h,
            )
            cell_bbox = _draw_boxed_value(
                draw,
                bbox=bbox,
                text="?" if hidden else str(grid[row][col]),
                hidden=hidden,
                fill=colors["node_fill"],
                outline=colors["line"],
                mark=colors["mark"],
                text_fill=colors["text"],
                stroke_fill=colors["stroke"],
                font=value_font,
                radius=max(5, int(render_params.panel_corner_radius_px) // 2),
                line_width=int(render_params.line_width_px),
            )
            item_bbox_map[str(cell_id)] = list(cell_bbox)
            entities.append(
                {
                    "entity_id": str(cell_id),
                    "entity_type": "operator_grid_cell",
                    "bbox_px": list(cell_bbox),
                    "row": int(row),
                    "col": int(col),
                    "value": int(grid[row][col]),
                    "hidden": bool(hidden),
                }
            )
    if query_id == "row_column_total_missing_value":
        for row, value in enumerate(dataset["row_totals"]):
            _draw_boxed_value(
                draw,
                bbox=(x0 + col_count * cell_w, y0 + row * cell_h, x0 + (col_count + 1) * cell_w, y0 + (row + 1) * cell_h),
                text=str(value),
                hidden=False,
                fill=colors["center_fill"],
                outline=colors["line"],
                mark=colors["mark"],
                text_fill=colors["text"],
                stroke_fill=colors["stroke"],
                font=value_font,
                radius=max(5, int(render_params.panel_corner_radius_px) // 2),
                line_width=int(render_params.line_width_px),
            )
        for col, value in enumerate(dataset["col_totals"]):
            _draw_boxed_value(
                draw,
                bbox=(x0 + col * cell_w, y0 + row_count * cell_h, x0 + (col + 1) * cell_w, y0 + (row_count + 1) * cell_h),
                text=str(value),
                hidden=False,
                fill=colors["center_fill"],
                outline=colors["line"],
                mark=colors["mark"],
                text_fill=colors["text"],
                stroke_fill=colors["stroke"],
                font=value_font,
                radius=max(5, int(render_params.panel_corner_radius_px) // 2),
                line_width=int(render_params.line_width_px),
            )
        _draw_disabled_table_corner(
            draw,
            bbox=(x0 + col_count * cell_w, y0 + row_count * cell_h, x0 + (col_count + 1) * cell_w, y0 + (row_count + 1) * cell_h),
            fill=colors["center_fill"],
            panel_fill=colors["panel_fill"],
            outline=colors["line"],
            radius=max(5, int(render_params.panel_corner_radius_px) // 2),
            line_width=int(render_params.line_width_px),
        )


def _render_number_wall(
    draw: ImageDraw.ImageDraw,
    *,
    dataset: Mapping[str, Any],
    panel_bbox: Tuple[int, int, int, int],
    render_params: ArithmeticRenderParams,
    colors: Mapping[str, Tuple[int, int, int]],
    item_bbox_map: Dict[str, List[float]],
    entities: List[Dict[str, Any]],
) -> None:
    value_font = load_font(int(render_params.value_font_size_px), bold=True)
    note_font = load_font(int(render_params.note_font_size_px), bold=True)
    note_text = "Find the missing brick value"
    note_bbox = _draw_note(
        draw,
        text=note_text,
        center=((panel_bbox[0] + panel_bbox[2]) / 2.0, panel_bbox[1] + int(render_params.panel_padding_px) + 28),
        font=note_font,
        fill=colors["text"],
        stroke_fill=colors["stroke"],
        max_width_px=int(panel_bbox[2] - panel_bbox[0] - 90),
    )
    item_bbox_map["constraint_note"] = _round_bbox(note_bbox)
    levels = [[int(value) for value in row] for row in dataset["levels"]]
    base_count = len(levels[0])
    cell_w = int(render_params.cell_width_px) + 18
    cell_h = int(render_params.cell_height_px)
    vertical_gap = 12
    total_w = base_count * cell_w
    total_h = len(levels) * cell_h + (len(levels) - 1) * vertical_gap
    x_base = int((panel_bbox[0] + panel_bbox[2] - total_w) / 2.0)
    y_top = int(panel_bbox[1] + 0.34 * (panel_bbox[3] - panel_bbox[1]))
    target_level = int(dataset["target_level"])
    target_index = int(dataset["target_index"])
    for level_index, values in enumerate(reversed(levels)):
        original_level = len(levels) - 1 - int(level_index)
        y = y_top + (level_index * (cell_h + vertical_gap))
        row_w = len(values) * cell_w
        x0 = x_base + int((total_w - row_w) / 2.0)
        for index, value in enumerate(values):
            hidden = bool(original_level == target_level and index == target_index)
            cell_id = f"wall_cell_{original_level}_{index}"
            bbox = (x0 + index * cell_w, y, x0 + (index + 1) * cell_w, y + cell_h)
            cell_bbox = _draw_boxed_value(
                draw,
                bbox=bbox,
                text="?" if hidden else str(value),
                hidden=hidden,
                fill=colors["node_fill"],
                outline=colors["line"],
                mark=colors["mark"],
                text_fill=colors["text"],
                stroke_fill=colors["stroke"],
                font=value_font,
                radius=max(5, int(render_params.panel_corner_radius_px) // 2),
                line_width=int(render_params.line_width_px),
            )
            item_bbox_map[str(cell_id)] = list(cell_bbox)
            entities.append(
                {
                    "entity_id": str(cell_id),
                    "entity_type": "number_wall_cell",
                    "bbox_px": list(cell_bbox),
                    "level": int(original_level),
                    "index": int(index),
                    "value": int(value),
                    "hidden": bool(hidden),
                }
            )


def _render_arithmetic_scene(
    image: Image.Image,
    *,
    dataset: Mapping[str, Any],
    scene_variant: str,
    render_params: ArithmeticRenderParams,
    scene_style,
) -> RenderedArithmeticScene:
    draw = ImageDraw.Draw(image)
    panel_bbox = _panel_bbox(render_params)
    item_bbox_map: Dict[str, List[float]] = {"diagram_panel": _round_bbox(panel_bbox)}
    entities: List[Dict[str, Any]] = [
        {
            "entity_id": "diagram_panel",
            "entity_type": "arithmetic_constraint_panel",
            "bbox_px": _round_bbox(panel_bbox),
            "scene_variant": str(scene_variant),
            "query_id": str(dataset["query_id"]),
            "layout_style": str(dataset["layout_style"]),
        }
    ]
    colors = {
        "panel_fill": tuple(int(value) for value in scene_style.panel_fill_rgb),
        "line": tuple(int(value) for value in scene_style.panel_border_rgb),
        "text": tuple(int(value) for value in scene_style.text_rgb),
        "stroke": tuple(int(value) for value in scene_style.text_stroke_rgb),
        "mark": tuple(int(value) for value in scene_style.mark_rgb),
        "node_fill": tuple(int(value) for value in scene_style.option_fill_rgb),
        "center_fill": tuple(int(value) for value in scene_style.step_fill_rgb),
        "shape_a": tuple(int(value) for value in scene_style.state_colors[0]),
        "shape_b": tuple(int(value) for value in scene_style.state_colors[1]),
        "shape_c": tuple(int(value) for value in scene_style.state_colors[2]),
    }
    if str(scene_variant) == "constraint_outline":
        draw.rounded_rectangle(panel_bbox, radius=int(render_params.panel_corner_radius_px), outline=colors["line"], width=int(render_params.panel_border_width_px))
    elif str(scene_variant) == "constraint_card":
        draw_puzzle_panel_chrome(
            draw,
            bbox=panel_bbox,
            style=scene_style,
            radius=int(render_params.panel_corner_radius_px),
            border_width=int(render_params.panel_border_width_px),
        )
    else:
        draw_rounded_rect(
            draw,
            panel_bbox,
            radius=int(render_params.panel_corner_radius_px),
            fill=colors["panel_fill"],
            outline=colors["line"],
            width=int(render_params.panel_border_width_px),
        )

    query_id = str(dataset["query_id"])
    if query_id == "equal_sum_line_constraint_value":
        _render_equal_sum(draw, dataset=dataset, panel_bbox=panel_bbox, render_params=render_params, colors=colors, item_bbox_map=item_bbox_map, entities=entities)
    elif query_id == "paired_cluster_sum_relation_value":
        _render_cluster(draw, dataset=dataset, panel_bbox=panel_bbox, render_params=render_params, colors=colors, item_bbox_map=item_bbox_map, entities=entities)
    elif query_id == "consecutive_window_sum_value":
        _render_consecutive(draw, dataset=dataset, panel_bbox=panel_bbox, render_params=render_params, colors=colors, item_bbox_map=item_bbox_map, entities=entities)
    elif query_id in CRYPTARITHM_QUERY_IDS:
        _render_cryptarithm(draw, dataset=dataset, panel_bbox=panel_bbox, render_params=render_params, colors=colors, item_bbox_map=item_bbox_map, entities=entities)
    elif query_id in OPERATOR_GRID_QUERY_IDS:
        _render_operator_grid(draw, dataset=dataset, panel_bbox=panel_bbox, render_params=render_params, colors=colors, item_bbox_map=item_bbox_map, entities=entities)
    elif query_id in NUMBER_WALL_QUERY_IDS:
        _render_number_wall(draw, dataset=dataset, panel_bbox=panel_bbox, render_params=render_params, colors=colors, item_bbox_map=item_bbox_map, entities=entities)
    else:
        raise ValueError(f"unsupported arithmetic render query_id: {query_id}")
    return RenderedArithmeticScene(
        image=image,
        entities=entities,
        scene_bbox_px=_round_bbox(panel_bbox),
        item_bbox_map={str(key): list(value) for key, value in item_bbox_map.items()},
    )


def _build_prompt(
    *,
    query_id: str,
    scene_variant: str,
    prompt_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str = TASK_ID,
) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
    required_keys = (
        "bundle_id",
        "scene_key",
        "task_key",
        "json_output_contract",
        "json_output_contract_answer_only",
        "answer_hint",
        f"object_description_{scene_variant}",
        f"evidence_hint_{query_id}",
        f"json_example_{query_id}",
        f"json_example_answer_only_{query_id}",
    )
    prompt_config = required_group_defaults(
        prompt_defaults,
        required_keys,
        context=f"prompt defaults for {task_id}",
    )
    selection = render_task_prompt_variants(
        domain="puzzles",
        task_group="logic",
        bundle_id=str(prompt_config["bundle_id"]),
        scene_key=str(prompt_config["scene_key"]),
        task_key=str(prompt_config["task_key"]),
        query_key=str(query_id),
        answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
        slots={
            "object_description": str(prompt_config[f"object_description_{scene_variant}"]),
            "json_output_contract": str(prompt_config["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_config["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_config["answer_hint"]),
            "evidence_hint": str(prompt_config[f"evidence_hint_{query_id}"]),
            "json_example": str(prompt_config[f"json_example_{query_id}"]),
            "json_example_answer_only": str(prompt_config[f"json_example_answer_only_{query_id}"]),
        },
        instance_seed=int(instance_seed),
    )
    artifacts = build_prompt_trace_artifacts(selection)
    return str(artifacts.prompt), dict(artifacts.prompt_variants), {
        "bundle_id": str(prompt_config["bundle_id"]),
        "prompt_variant": dict(artifacts.prompt_variant),
        "prompt_variant_active_key": str(artifacts.prompt_variant_active_key),
        "prompt_variants_for_trace": dict(artifacts.prompt_variants_for_trace),
    }


class _ArithmeticConstraintSceneTask:
    """Base class for integer arithmetic puzzles rendered in the shared scene."""

    task_id = TASK_ID
    domain = "puzzles"
    task_group = "logic"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        task_id = str(self.task_id)
        supported_query_ids = tuple(str(item) for item in self.supported_query_ids)
        gen_defaults, render_defaults, prompt_defaults, complexity_weights = _load_defaults(task_id=task_id)
        query_id, query_id_probabilities = _resolve_query_id(
            params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=task_id,
            supported_query_ids=supported_query_ids,
        )
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(
            params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=task_id,
        )
        dataset: Dict[str, Any] | None = None
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            try:
                dataset = _build_dataset(
                    params=params,
                    gen_defaults=gen_defaults,
                    instance_seed=int(instance_seed) + int(attempt_index),
                    query_id=str(query_id),
                    task_id=task_id,
                )
                break
            except RuntimeError as exc:
                last_error = exc
        if dataset is None:
            raise RuntimeError("failed to generate arithmetic constraint puzzle") from last_error

        render_params = _resolve_render_params(params, render_defaults, instance_seed=int(instance_seed), task_id=task_id)
        scene_style, scene_style_meta = resolve_puzzle_scene_style(
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.scene_style",
        )
        font_family = sample_font_family(
            role="readout",
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.font_family",
            params={**dict(render_defaults), **dict(params)},
        )
        font_meta = {
            **get_font_family_record(str(font_family)).to_trace(),
            "font_asset_version": font_asset_version(),
            "selection_scope": "arithmetic_constraint_panel",
            "include_tags": [],
            "exclude_tags": [],
        }
        background, background_meta = make_puzzle_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=scene_style,
        )
        with temporary_default_font_family(str(font_family)):
            rendered_scene = _render_arithmetic_scene(
                background,
                dataset=dataset,
                scene_variant=str(scene_variant),
                render_params=render_params,
                scene_style=scene_style,
            )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        prompt, prompt_variants, prompt_meta = _build_prompt(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            prompt_defaults=prompt_defaults,
            instance_seed=int(instance_seed),
            task_id=task_id,
        )
        evidence_projection = projected_puzzle_bbox_evidence(
            rendered_scene.item_bbox_map,
            [str(item_id) for item_id in dataset["supporting_item_ids"]],
        )
        evidence_bboxes = [
            [round(float(value), 3) for value in bbox]
            for bbox in evidence_projection["bbox_set"]
        ]
        answer_value = int(dataset["answer_value"])
        answer_gt = TypedValue(type="integer", value=int(answer_value))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        query_params = {
            "query_id": str(query_id),
            "query_id_probabilities": dict(query_id_probabilities),
            "scene_id": SCENE_ID,
            "scene_variant": str(scene_variant),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "layout_style": str(dataset["layout_style"]),
            "answer_range": list(dataset["answer_range"]),
            "target_answer_support": list(dataset["target_answer_support"]),
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": SCENE_ID,
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_id": SCENE_ID,
                    "scene_variant": str(scene_variant),
                    "layout_style": str(dataset["layout_style"]),
                    "answer_value": int(answer_value),
                },
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
                "scene_id": SCENE_ID,
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "scene_style": dict(scene_style_meta),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "text_style": {
                    "font": dict(font_meta),
                    "value_font_size_px": int(render_params.value_font_size_px),
                    "note_font_size_px": int(render_params.note_font_size_px),
                    "symbol_font_size_px": int(render_params.symbol_font_size_px),
                },
                "unit_size_jitter": dict(render_params.unit_size_jitter),
            },
            "render_map": with_puzzle_unit_size_jitter(
                {
                    "image_id": "img0",
                    "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                    "item_bboxes_px": {str(key): list(value) for key, value in rendered_scene.item_bbox_map.items()},
                    "evidence_source": "item_bboxes_px",
                },
                render_params.unit_size_jitter,
            ),
            "execution_trace": {
                **dict(query_params),
                "answer_value": int(answer_value),
                "supporting_item_ids": [str(item_id) for item_id in dataset["supporting_item_ids"]],
                "question_format": str(query_id),
                "constraint_data": {
                    key: value
                    for key, value in dataset.items()
                    if key not in {"supporting_item_ids", "target_answer_support"}
                },
            },
            "witness_symbolic": {
                "type": "bbox_set",
                "value": list(evidence_bboxes),
            },
            "projected_evidence": {
                "type": "bbox_set",
                "bbox_set": list(evidence_bboxes),
                "value": list(evidence_bboxes),
            },
        }
        visual_scan_units = {
            "equal_sum_line_constraint_value": int(dataset.get("side_count", 3)) * 2,
            "paired_cluster_sum_relation_value": len(dataset.get("left_values", [])) + len(dataset.get("right_values", [])),
            "consecutive_window_sum_value": len(dataset.get("sequence_values", [])),
            "hidden_addition_digit_value": len(dataset.get("rows", [])) * int(dataset.get("number_width", 3)),
            "hidden_subtraction_digit_value": len(dataset.get("rows", [])) * int(dataset.get("number_width", 3)),
            "letter_digit_value": len(dataset.get("equations", [])) * 3,
            "row_column_total_missing_value": (int(dataset.get("row_count", 3)) * int(dataset.get("col_count", 3))) + int(dataset.get("row_count", 3)) + int(dataset.get("col_count", 3)),
            "operation_table_cell_value": (int(dataset.get("row_count", 3)) * int(dataset.get("col_count", 3))) + int(dataset.get("row_count", 3)) + int(dataset.get("col_count", 3)) + 1,
            "addition_wall_missing_value": sum(len(row) for row in dataset.get("levels", [])),
            "difference_wall_missing_value": sum(len(row) for row in dataset.get("levels", [])),
            "multiplication_pyramid_value": sum(len(row) for row in dataset.get("levels", [])),
        }[str(query_id)]
        complexity = build_puzzle_complexity(
            weights=complexity_weights,
            components={
                "visual_scan": normalize_int_with_bounds(int(visual_scan_units), [6, 12]),
                "reasoning_load": float(_REASONING_LOAD_BY_QUERY[str(query_id)]),
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(scene_variant)]),
            },
        )
        return TaskOutput(
            prompt=str(prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
            prompt_variants=dict(prompt_variants),
        )


@register_task
class PuzzlesLogicArithmeticConstraintValueTask(_ArithmeticConstraintSceneTask):
    """Solve one integer in a compact arithmetic-constraint diagram."""

    task_id = TASK_ID
    supported_query_ids = ARITHMETIC_CONSTRAINT_QUERY_IDS


@register_task
class PuzzlesLogicCryptarithmDigitValueTask(_ArithmeticConstraintSceneTask):
    """Solve one hidden digit in a compact cryptarithm diagram."""

    task_id = CRYPTARITHM_TASK_ID
    supported_query_ids = CRYPTARITHM_QUERY_IDS


@register_task
class PuzzlesLogicOperatorGridValueTask(_ArithmeticConstraintSceneTask):
    """Solve one hidden value in an operator-grid arithmetic puzzle."""

    task_id = OPERATOR_GRID_TASK_ID
    supported_query_ids = OPERATOR_GRID_QUERY_IDS


@register_task
class PuzzlesLogicNumberWallValueTask(_ArithmeticConstraintSceneTask):
    """Solve one hidden value in a number-wall arithmetic puzzle."""

    task_id = NUMBER_WALL_TASK_ID
    supported_query_ids = NUMBER_WALL_QUERY_IDS


__all__ = [
    "ARITHMETIC_CONSTRAINT_QUERY_IDS",
    "CRYPTARITHM_QUERY_IDS",
    "CRYPTARITHM_TASK_ID",
    "NUMBER_WALL_QUERY_IDS",
    "NUMBER_WALL_TASK_ID",
    "OPERATOR_GRID_QUERY_IDS",
    "OPERATOR_GRID_TASK_ID",
    "SCENE_ID",
    "SUPPORTED_QUERY_IDS",
    "SUPPORTED_QUERY_IDS_BY_TASK_ID",
    "TASK_ID",
    "PuzzlesLogicCryptarithmDigitValueTask",
    "PuzzlesLogicArithmeticConstraintValueTask",
    "PuzzlesLogicNumberWallValueTask",
    "PuzzlesLogicOperatorGridValueTask",
]
