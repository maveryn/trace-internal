"""Balance-scale logic puzzles with one missing object weight."""

from __future__ import annotations

from itertools import product
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import required_group_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.font_assets import font_asset_version, get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_rendering import temporary_default_font_family
from ..shared.balance_scale_scene import (
    SUPPORTED_BALANCE_SCALE_SCENE_VARIANTS,
    BalanceScaleRenderParams,
    render_balance_scale_scene,
)
from ..shared.common import (
    get_int_param as _get_int,
    get_int_range as _get_range,
    load_puzzle_task_defaults,
    projected_puzzle_keyed_bbox_annotation,
    resolve_puzzle_axis_variant,
)
from ..shared.scene_style import make_puzzle_scene_background, resolve_puzzle_scene_style
from ..shared.symbol_rendering import PUZZLE_OBJECT_COLOR_BY_TYPE, PUZZLE_OBJECT_TYPES
from ..shared.unit_size_jitter import resolve_puzzle_unit_size_scale, scale_puzzle_px, with_puzzle_unit_size_jitter
from ..shared.visual_defaults import load_puzzle_noise_defaults


SCENE_ID = "balance_scale"
MISSING_OBJECT_WEIGHT_TASK_ID = "task_puzzles__balance_scale__missing_object_weight_value"
EQUIVALENT_OBJECT_COUNT_TASK_ID = "task_puzzles__balance_scale__equivalent_object_count_value"
WEIGHT_ORDER_TASK_ID = "task_puzzles__balance_scale__weight_order_label"
MISSING_OBJECT_WEIGHT_QUERY_ID = "missing_object_weight_value"
EQUIVALENT_OBJECT_COUNT_QUERY_ID = "equivalent_object_count_value"
HEAVIEST_OBJECT_LABEL_QUERY_ID = "heaviest_object_label"
LIGHTEST_OBJECT_LABEL_QUERY_ID = "lightest_object_label"
WEIGHT_ORDER_QUERY_IDS: Tuple[str, ...] = (HEAVIEST_OBJECT_LABEL_QUERY_ID, LIGHTEST_OBJECT_LABEL_QUERY_ID)
TASK_ID = MISSING_OBJECT_WEIGHT_TASK_ID
QUERY_ID = MISSING_OBJECT_WEIGHT_QUERY_ID
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    MISSING_OBJECT_WEIGHT_QUERY_ID,
    EQUIVALENT_OBJECT_COUNT_QUERY_ID,
    *WEIGHT_ORDER_QUERY_IDS,
)
SUPPORTED_TARGET_CUE_MODES: Tuple[str, ...] = (
    "query_row_only",
    "query_row_and_highlight",
)
OBJECT_LABELS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")

_TASK_GROUP_DEFAULTS = get_scene_defaults("puzzles", "logic")
POST_IMAGE_NOISE_DEFAULTS = load_puzzle_noise_defaults(scene_id="logic", apply_prob=0.15)
_SCENE_LOAD_BY_VARIANT = {
    "balance_sheet": 0.18,
    "balance_card": 0.24,
    "balance_outline": 0.20,
}


def _load_defaults(task_id: str) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, float]]:
    return load_puzzle_task_defaults(_TASK_GROUP_DEFAULTS, task_id=str(task_id))


def _resolve_scene_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_BALANCE_SCALE_SCENE_VARIANTS,
        task_id=str(task_id),
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def _resolve_target_cue_mode(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_TARGET_CUE_MODES,
        task_id=str(task_id),
        explicit_key="target_cue_mode",
        weights_key="target_cue_mode_weights",
        balance_flag_key="balanced_target_cue_mode_sampling",
        axis_namespace="target_cue_mode",
    )


def _resolve_query_id(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    supported_query_ids: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    effective_params = dict(params)
    if effective_params.get("query_id") is None and effective_params.get("query_variant") is not None:
        effective_params["query_id"] = str(effective_params["query_variant"])
    return resolve_puzzle_axis_variant(
        params=effective_params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=[str(query_id) for query_id in supported_query_ids],
        task_id=str(task_id),
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )


def _resolve_answer_value(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    query_id: str,
    fallback_min: int,
    fallback_max: int,
) -> Tuple[int, List[int]]:
    low, high = _get_range(
        params,
        gen_defaults,
        min_key="answer_min",
        max_key="answer_max",
        fallback_min=int(fallback_min),
        fallback_max=int(fallback_max),
    )
    support = [int(value) for value in range(int(low), int(high) + 1)]
    if not support:
        raise ValueError("balance-scale answer support cannot be empty")
    selection = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.{query_id}.answer",
    )
    return int(support[int(selection % len(support))]), support


def _resolve_panel_count(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> int:
    low, high = _get_range(
        params,
        gen_defaults,
        min_key="scale_panel_count_min",
        max_key="scale_panel_count_max",
        fallback_min=2,
        fallback_max=3,
    )
    support = [int(value) for value in range(int(low), int(high) + 1)]
    selection = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.scale_panel_count",
    )
    return int(support[int(selection % len(support))])


def _resolve_render_params(
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    *,
    instance_seed: int,
    task_id: str,
) -> BalanceScaleRenderParams:
    unit_scale, unit_meta = resolve_puzzle_unit_size_scale(
        params,
        render_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.unit_size",
    )
    return BalanceScaleRenderParams(
        canvas_width=_get_int(params, render_defaults, "canvas_width", 1120),
        canvas_height=_get_int(params, render_defaults, "canvas_height", 840),
        scene_margin_left_px=_get_int(params, render_defaults, "scene_margin_left_px", 54),
        scene_margin_right_px=_get_int(params, render_defaults, "scene_margin_right_px", 54),
        scene_margin_top_px=_get_int(params, render_defaults, "scene_margin_top_px", 48),
        scene_margin_bottom_px=_get_int(params, render_defaults, "scene_margin_bottom_px", 48),
        panel_padding_px=scale_puzzle_px(_get_int(params, render_defaults, "panel_padding_px", 26), unit_scale, min_px=16),
        panel_corner_radius_px=scale_puzzle_px(_get_int(params, render_defaults, "panel_corner_radius_px", 20), unit_scale, min_px=8),
        panel_border_width_px=_get_int(params, render_defaults, "panel_border_width_px", 3),
        scale_panel_gap_px=scale_puzzle_px(_get_int(params, render_defaults, "scale_panel_gap_px", 20), unit_scale, min_px=12),
        query_row_height_px=scale_puzzle_px(_get_int(params, render_defaults, "query_row_height_px", 116), unit_scale, min_px=82),
        beam_width_px=scale_puzzle_px(_get_int(params, render_defaults, "beam_width_px", 620), unit_scale, min_px=420),
        pan_width_px=scale_puzzle_px(_get_int(params, render_defaults, "pan_width_px", 230), unit_scale, min_px=170),
        pan_height_px=scale_puzzle_px(_get_int(params, render_defaults, "pan_height_px", 82), unit_scale, min_px=58),
        token_size_px=scale_puzzle_px(_get_int(params, render_defaults, "token_size_px", 46), unit_scale, min_px=34),
        token_gap_px=scale_puzzle_px(_get_int(params, render_defaults, "token_gap_px", 8), unit_scale, min_px=5),
        line_width_px=_get_int(params, render_defaults, "line_width_px", 3),
        value_font_size_px=scale_puzzle_px(_get_int(params, render_defaults, "value_font_size_px", 24), unit_scale, min_px=18),
        label_font_size_px=scale_puzzle_px(_get_int(params, render_defaults, "label_font_size_px", 22), unit_scale, min_px=16),
        query_font_size_px=scale_puzzle_px(_get_int(params, render_defaults, "query_font_size_px", 30), unit_scale, min_px=22),
        unit_size_jitter=dict(unit_meta),
    )


def _side_total(terms: Sequence[Mapping[str, Any]], weights: Mapping[str, int]) -> int:
    total = 0
    for term in terms:
        if str(term["kind"]) == "object":
            total += int(term["count"]) * int(weights[str(term["object_label"])])
        else:
            total += int(term["value"])
    return int(total)


def _expand_terms(
    terms: Sequence[Mapping[str, Any]],
    *,
    panel_id: str,
    side_name: str,
    weights: Mapping[str, int],
) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for term_index, term in enumerate(terms):
        if str(term["kind"]) == "object":
            label = str(term["object_label"])
            for copy_index in range(int(term["count"])):
                items.append(
                    {
                        "item_id": f"{panel_id}_{side_name}_object_{term_index}_{copy_index}",
                        "kind": "object",
                        "object_label": label,
                        "object_weight": int(weights[label]),
                    }
                )
        else:
            items.append(
                {
                    "item_id": f"{panel_id}_{side_name}_weight_{term_index}",
                    "kind": "numeric",
                    "value": int(term["value"]),
                }
            )
    return items


def _make_panel(
    *,
    panel_index: int,
    left_terms: Sequence[Mapping[str, Any]],
    right_terms: Sequence[Mapping[str, Any]],
    weights: Mapping[str, int],
    require_balanced: bool = True,
) -> Dict[str, Any]:
    panel_id = f"scale_{int(panel_index)}"
    left_total = _side_total(left_terms, weights)
    right_total = _side_total(right_terms, weights)
    if bool(require_balanced) and int(left_total) != int(right_total):
        raise RuntimeError(f"unbalanced generated scale panel: {left_total} != {right_total}")
    if int(left_total) == int(right_total):
        balance_state = "balanced"
        heavier_side = "none"
    elif int(left_total) > int(right_total):
        balance_state = "left_heavier"
        heavier_side = "left"
    else:
        balance_state = "right_heavier"
        heavier_side = "right"
    return {
        "panel_id": panel_id,
        "panel_label": f"Scale {int(panel_index)}",
        "left_terms": [dict(term) for term in left_terms],
        "right_terms": [dict(term) for term in right_terms],
        "left_items": _expand_terms(left_terms, panel_id=panel_id, side_name="left", weights=weights),
        "right_items": _expand_terms(right_terms, panel_id=panel_id, side_name="right", weights=weights),
        "left_total": int(left_total),
        "right_total": int(right_total),
        "is_balanced": bool(left_total == right_total),
        "balance_state": str(balance_state),
        "heavier_side": str(heavier_side),
    }


def _term_coefficients(terms: Sequence[Mapping[str, Any]], labels: Sequence[str]) -> Tuple[Dict[str, int], int]:
    coeffs = {str(label): 0 for label in labels}
    constant = 0
    for term in terms:
        if str(term["kind"]) == "object":
            coeffs[str(term["object_label"])] += int(term["count"])
        else:
            constant += int(term["value"])
    return coeffs, int(constant)


def _unique_target_values(
    *,
    equations: Sequence[Mapping[str, Any]],
    labels: Sequence[str],
    target_label: str,
    support: Sequence[int],
) -> List[int]:
    target_values: set[int] = set()
    label_list = [str(label) for label in labels]
    for values in product([int(value) for value in support], repeat=len(label_list)):
        assignment = {label: int(value) for label, value in zip(label_list, values)}
        valid = True
        for equation in equations:
            left_coeffs, left_constant = _term_coefficients(equation["left_terms"], label_list)
            right_coeffs, right_constant = _term_coefficients(equation["right_terms"], label_list)
            left_total = int(left_constant) + sum(int(left_coeffs[label]) * int(assignment[label]) for label in label_list)
            right_total = int(right_constant) + sum(int(right_coeffs[label]) * int(assignment[label]) for label in label_list)
            if int(left_total) != int(right_total):
                valid = False
                break
        if valid:
            target_values.add(int(assignment[str(target_label)]))
    return sorted(int(value) for value in target_values)


def _unique_equivalent_counts(
    *,
    equations: Sequence[Mapping[str, Any]],
    labels: Sequence[str],
    source_label: str,
    repeated_label: str,
    count_support: Sequence[int],
    weight_support: Sequence[int],
) -> List[int]:
    counts: set[int] = set()
    label_list = [str(label) for label in labels]
    weight_values = [int(value) for value in weight_support]
    supported_counts = {int(value) for value in count_support}
    for values in product(weight_values, repeat=len(label_list)):
        assignment = {label: int(value) for label, value in zip(label_list, values)}
        valid = True
        for equation in equations:
            left_coeffs, left_constant = _term_coefficients(equation["left_terms"], label_list)
            right_coeffs, right_constant = _term_coefficients(equation["right_terms"], label_list)
            left_total = int(left_constant) + sum(int(left_coeffs[label]) * int(assignment[label]) for label in label_list)
            right_total = int(right_constant) + sum(int(right_coeffs[label]) * int(assignment[label]) for label in label_list)
            if int(left_total) != int(right_total):
                valid = False
                break
        if not valid:
            continue
        repeated_weight = int(assignment[str(repeated_label)])
        source_weight = int(assignment[str(source_label)])
        if repeated_weight <= 0 or source_weight % repeated_weight != 0:
            continue
        count = int(source_weight // repeated_weight)
        if count in supported_counts:
            counts.add(int(count))
    return sorted(int(value) for value in counts)


def _unique_weight_order_labels(
    *,
    comparisons: Sequence[Mapping[str, Any]],
    labels: Sequence[str],
    query_id: str,
) -> List[str]:
    label_list = [str(label) for label in labels]
    heavier_than: Dict[str, set[str]] = {label: set() for label in label_list}
    for comparison in comparisons:
        heavier = str(comparison["heavier_label"])
        lighter = str(comparison["lighter_label"])
        if heavier in heavier_than and lighter in heavier_than:
            heavier_than[heavier].add(lighter)

    changed = True
    while changed:
        changed = False
        for label in label_list:
            expanded = set(heavier_than[label])
            for lighter in list(heavier_than[label]):
                expanded.update(heavier_than.get(lighter, set()))
            if expanded != heavier_than[label]:
                heavier_than[label] = expanded
                changed = True

    if str(query_id) == HEAVIEST_OBJECT_LABEL_QUERY_ID:
        return sorted(label for label in label_list if len(heavier_than[label]) == len(label_list) - 1)
    if str(query_id) == LIGHTEST_OBJECT_LABEL_QUERY_ID:
        return sorted(
            label
            for label in label_list
            if all(label == other or label in heavier_than[other] for other in label_list)
        )
    raise ValueError(f"unsupported weight-order query id: {query_id}")


def _maybe_swap_sides(
    left_terms: Sequence[Mapping[str, Any]],
    right_terms: Sequence[Mapping[str, Any]],
    *,
    rng,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    left = [dict(term) for term in left_terms]
    right = [dict(term) for term in right_terms]
    if rng.random() < 0.5:
        return right, left
    return left, right


def _object_specs_for_labels(labels: Sequence[str], *, offset: int) -> Dict[str, Dict[str, Any]]:
    specs: Dict[str, Dict[str, Any]] = {}
    object_types = tuple(str(item) for item in PUZZLE_OBJECT_TYPES)
    for index, label in enumerate(labels):
        object_type = object_types[(int(offset) + int(index)) % len(object_types)]
        specs[str(label)] = {
            "object_label": str(label),
            "object_type": object_type,
            "fill_rgb": list(PUZZLE_OBJECT_COLOR_BY_TYPE[object_type]),
        }
    return specs


def _build_missing_object_weight_dataset(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    answer_value: int,
    answer_support: Sequence[int],
    scene_variant: str,
    target_cue_mode: str,
) -> Dict[str, Any]:
    task_id = MISSING_OBJECT_WEIGHT_TASK_ID
    query_id = MISSING_OBJECT_WEIGHT_QUERY_ID
    rng = spawn_rng(int(instance_seed), f"{task_id}.dataset")
    target_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.target_label",
    ) % len(OBJECT_LABELS)
    target_label = str(OBJECT_LABELS[int(target_index)])
    helper_label = str(OBJECT_LABELS[(int(target_index) + 1 + int(rng.randrange(len(OBJECT_LABELS) - 1))) % len(OBJECT_LABELS)])
    labels = (target_label, helper_label)
    object_type_offset = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.object_type_offset",
    )
    object_specs = _object_specs_for_labels(labels, offset=int(object_type_offset))
    panel_count = _resolve_panel_count(params, gen_defaults=gen_defaults, instance_seed=int(instance_seed), task_id=task_id)
    max_numeric_value = _get_int(params, gen_defaults, "numeric_weight_max", 80)

    for _attempt in range(500):
        helper_value = int(rng.randint(1, 20))
        if int(helper_value) == int(answer_value):
            continue
        weights = {
            target_label: int(answer_value),
            helper_label: int(helper_value),
        }
        target_count = int(rng.randint(1, 2))
        helper_use_count = int(rng.randint(1, 2))
        helper_solve_count = int(rng.randint(1, 3))
        target_total = int(target_count * int(answer_value) + helper_use_count * helper_value)
        helper_total = int(helper_solve_count * helper_value)
        if int(target_total) > int(max_numeric_value) or int(helper_total) > int(max_numeric_value):
            continue
        target_left = [
            {"kind": "object", "object_label": target_label, "count": int(target_count)},
            {"kind": "object", "object_label": helper_label, "count": int(helper_use_count)},
        ]
        target_right = [{"kind": "numeric", "value": int(target_total)}]
        helper_left = [{"kind": "object", "object_label": helper_label, "count": int(helper_solve_count)}]
        helper_right = [{"kind": "numeric", "value": int(helper_total)}]
        target_left, target_right = _maybe_swap_sides(target_left, target_right, rng=rng)
        helper_left, helper_right = _maybe_swap_sides(helper_left, helper_right, rng=rng)
        equations: List[Dict[str, Any]] = [
            {
                "equation_id": "target_constraint",
                "left_terms": [dict(term) for term in target_left],
                "right_terms": [dict(term) for term in target_right],
            },
            {
                "equation_id": "helper_constraint",
                "left_terms": [dict(term) for term in helper_left],
                "right_terms": [dict(term) for term in helper_right],
            },
        ]
        panels = [
            _make_panel(panel_index=1, left_terms=target_left, right_terms=target_right, weights=weights),
            _make_panel(panel_index=2, left_terms=helper_left, right_terms=helper_right, weights=weights),
        ]
        if int(panel_count) >= 3:
            helper_repeat = int(rng.randint(1, 2))
            added_weight = int(rng.randint(1, 12))
            redundant_total = int(helper_repeat * helper_value + added_weight)
            if redundant_total > int(max_numeric_value):
                continue
            extra_left = [
                {"kind": "object", "object_label": helper_label, "count": int(helper_repeat)},
                {"kind": "numeric", "value": int(added_weight)},
            ]
            extra_right = [{"kind": "numeric", "value": int(redundant_total)}]
            extra_left, extra_right = _maybe_swap_sides(extra_left, extra_right, rng=rng)
            equations.append(
                {
                    "equation_id": "extra_helper_constraint",
                    "left_terms": [dict(term) for term in extra_left],
                    "right_terms": [dict(term) for term in extra_right],
                }
            )
            panels.append(_make_panel(panel_index=3, left_terms=extra_left, right_terms=extra_right, weights=weights))

        unique_values = _unique_target_values(
            equations=equations,
            labels=labels,
            target_label=target_label,
            support=answer_support,
        )
        if unique_values != [int(answer_value)]:
            continue
        return {
            "query_id": query_id,
            "scene_id": SCENE_ID,
            "scene_variant": str(scene_variant),
            "query_row_kind": query_id,
            "target_cue_mode": str(target_cue_mode),
            "target_label": target_label,
            "helper_label": helper_label,
            "object_labels": list(labels),
            "object_specs": object_specs,
            "object_weights": dict(weights),
            "panels": panels,
            "equations": equations,
            "answer_value": int(answer_value),
            "answer_range": [int(min(answer_support)), int(max(answer_support))],
            "target_answer_support": [int(value) for value in answer_support],
            "supporting_role_item_ids": {
                "query_object": "query_object",
                "missing_value_box": "missing_value_box",
            },
        }
    raise RuntimeError("failed to construct a uniquely solvable balance-scale puzzle")


def _build_equivalent_object_count_dataset(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    answer_value: int,
    answer_support: Sequence[int],
    scene_variant: str,
    target_cue_mode: str,
) -> Dict[str, Any]:
    task_id = EQUIVALENT_OBJECT_COUNT_TASK_ID
    query_id = EQUIVALENT_OBJECT_COUNT_QUERY_ID
    rng = spawn_rng(int(instance_seed), f"{task_id}.dataset")
    source_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.source_label",
    ) % len(OBJECT_LABELS)
    source_label = str(OBJECT_LABELS[int(source_index)])
    repeated_label = str(OBJECT_LABELS[(int(source_index) + 1 + int(rng.randrange(len(OBJECT_LABELS) - 1))) % len(OBJECT_LABELS)])
    labels = (source_label, repeated_label)
    object_type_offset = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.object_type_offset",
    )
    object_specs = _object_specs_for_labels(labels, offset=int(object_type_offset))
    panel_count = _resolve_panel_count(params, gen_defaults=gen_defaults, instance_seed=int(instance_seed), task_id=task_id)
    max_numeric_value = _get_int(params, gen_defaults, "numeric_weight_max", 80)
    repeated_weight_max = _get_int(params, gen_defaults, "repeated_object_weight_max", 10)
    weight_support = [int(value) for value in range(1, int(max_numeric_value) + 1)]

    for _attempt in range(500):
        repeated_weight = int(rng.randint(1, max(1, int(repeated_weight_max))))
        source_weight = int(answer_value) * int(repeated_weight)
        if source_weight > int(max_numeric_value):
            continue
        repeated_solve_count = int(rng.randint(2, 3))
        repeated_total = int(repeated_solve_count) * int(repeated_weight)
        if repeated_total > int(max_numeric_value):
            continue
        weights = {
            source_label: int(source_weight),
            repeated_label: int(repeated_weight),
        }
        source_left = [{"kind": "object", "object_label": source_label, "count": 1}]
        source_right = [{"kind": "numeric", "value": int(source_weight)}]
        repeated_left = [{"kind": "object", "object_label": repeated_label, "count": int(repeated_solve_count)}]
        repeated_right = [{"kind": "numeric", "value": int(repeated_total)}]
        source_left, source_right = _maybe_swap_sides(source_left, source_right, rng=rng)
        repeated_left, repeated_right = _maybe_swap_sides(repeated_left, repeated_right, rng=rng)
        equations: List[Dict[str, Any]] = [
            {
                "equation_id": "source_weight_constraint",
                "left_terms": [dict(term) for term in source_left],
                "right_terms": [dict(term) for term in source_right],
            },
            {
                "equation_id": "repeated_weight_constraint",
                "left_terms": [dict(term) for term in repeated_left],
                "right_terms": [dict(term) for term in repeated_right],
            },
        ]
        panels = [
            _make_panel(panel_index=1, left_terms=source_left, right_terms=source_right, weights=weights),
            _make_panel(panel_index=2, left_terms=repeated_left, right_terms=repeated_right, weights=weights),
        ]
        if int(panel_count) >= 3:
            added_weight = int(rng.randint(1, 12))
            extra_left = [
                {"kind": "object", "object_label": repeated_label, "count": 1},
                {"kind": "numeric", "value": int(added_weight)},
            ]
            extra_right = [{"kind": "numeric", "value": int(repeated_weight + added_weight)}]
            if int(repeated_weight + added_weight) > int(max_numeric_value):
                continue
            extra_left, extra_right = _maybe_swap_sides(extra_left, extra_right, rng=rng)
            equations.append(
                {
                    "equation_id": "extra_repeated_constraint",
                    "left_terms": [dict(term) for term in extra_left],
                    "right_terms": [dict(term) for term in extra_right],
                }
            )
            panels.append(_make_panel(panel_index=3, left_terms=extra_left, right_terms=extra_right, weights=weights))

        unique_counts = _unique_equivalent_counts(
            equations=equations,
            labels=labels,
            source_label=source_label,
            repeated_label=repeated_label,
            count_support=answer_support,
            weight_support=weight_support,
        )
        if unique_counts != [int(answer_value)]:
            continue
        return {
            "query_id": query_id,
            "scene_id": SCENE_ID,
            "scene_variant": str(scene_variant),
            "query_row_kind": query_id,
            "target_cue_mode": str(target_cue_mode),
            "target_label": source_label,
            "source_label": source_label,
            "repeated_label": repeated_label,
            "object_labels": list(labels),
            "object_specs": object_specs,
            "object_weights": dict(weights),
            "panels": panels,
            "equations": equations,
            "answer_value": int(answer_value),
            "answer_range": [int(min(answer_support)), int(max(answer_support))],
            "target_answer_support": [int(value) for value in answer_support],
            "supporting_role_item_ids": {
                "source_object": "source_object",
                "repeated_object": "repeated_object",
                "missing_count_box": "missing_count_box",
            },
        }
    raise RuntimeError("failed to construct a uniquely solvable balance-scale equivalent-count puzzle")


def _build_weight_order_dataset(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    query_id: str,
    scene_variant: str,
) -> Dict[str, Any]:
    task_id = WEIGHT_ORDER_TASK_ID
    rng = spawn_rng(int(instance_seed), f"{task_id}.dataset")
    low, high = _get_range(
        params,
        gen_defaults,
        min_key="object_count_min",
        max_key="object_count_max",
        fallback_min=3,
        fallback_max=4,
    )
    object_count_support = [int(value) for value in range(int(low), int(high) + 1)]
    object_count = int(object_count_support[int(rng.randrange(len(object_count_support)))])
    labels = list(OBJECT_LABELS)
    rng.shuffle(labels)
    labels = sorted(str(label) for label in labels[:object_count])
    object_type_offset = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.object_type_offset",
    )
    object_specs = _object_specs_for_labels(labels, offset=int(object_type_offset))

    weight_pool = list(range(2, 2 + object_count * 3))
    rng.shuffle(weight_pool)
    sampled_weights = sorted(int(value) for value in weight_pool[:object_count])
    order_labels = list(labels)
    rng.shuffle(order_labels)
    weights = {label: int(weight) for label, weight in zip(order_labels, sampled_weights)}
    sorted_by_weight = sorted(order_labels, key=lambda label: int(weights[str(label)]))

    raw_comparisons: List[Dict[str, Any]] = []
    for index in range(len(sorted_by_weight) - 1):
        lighter_label = str(sorted_by_weight[index])
        heavier_label = str(sorted_by_weight[index + 1])
        raw_comparisons.append(
            {
                "comparison_id": f"comparison_{index + 1}",
                "lighter_label": lighter_label,
                "heavier_label": heavier_label,
            }
        )
    rng.shuffle(raw_comparisons)

    panels: List[Dict[str, Any]] = []
    comparisons: List[Dict[str, Any]] = []
    for panel_index, comparison in enumerate(raw_comparisons, start=1):
        heavier_label = str(comparison["heavier_label"])
        lighter_label = str(comparison["lighter_label"])
        left_terms = [{"kind": "object", "object_label": heavier_label, "count": 1}]
        right_terms = [{"kind": "object", "object_label": lighter_label, "count": 1}]
        if rng.random() < 0.5:
            left_terms, right_terms = right_terms, left_terms
        panel = _make_panel(
            panel_index=panel_index,
            left_terms=left_terms,
            right_terms=right_terms,
            weights=weights,
            require_balanced=False,
        )
        panel["comparison_id"] = str(comparison["comparison_id"])
        panels.append(panel)
        comparisons.append(
            {
                **dict(comparison),
                "panel_id": str(panel["panel_id"]),
                "left_label": str(left_terms[0]["object_label"]),
                "right_label": str(right_terms[0]["object_label"]),
                "heavier_side": str(panel["heavier_side"]),
            }
        )

    unique_answers = _unique_weight_order_labels(comparisons=comparisons, labels=labels, query_id=str(query_id))
    if len(unique_answers) != 1:
        raise RuntimeError("failed to construct a uniquely ordered balance-scale puzzle")
    answer_label = str(unique_answers[0])
    supporting_role_item_ids = {
        f"comparison_scale_{index}": str(panel["panel_id"])
        for index, panel in enumerate(panels, start=1)
    }
    supporting_role_item_ids["selected_object"] = f"candidate_{answer_label}"

    return {
        "query_id": str(query_id),
        "scene_id": SCENE_ID,
        "scene_variant": str(scene_variant),
        "query_row_kind": "weight_order_label",
        "target_cue_mode": "query_row_only",
        "target_label": answer_label,
        "object_labels": list(labels),
        "candidate_labels": list(labels),
        "object_specs": object_specs,
        "object_weights": dict(weights),
        "panels": panels,
        "equations": [],
        "comparisons": comparisons,
        "answer_type": "string",
        "answer_value": answer_label,
        "answer_labels": list(labels),
        "answer_range": list(labels),
        "target_answer_support": list(labels),
        "supporting_role_item_ids": supporting_role_item_ids,
    }


def _build_prompt(
    *,
    task_id: str,
    query_id: str,
    scene_variant: str,
    prompt_defaults: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
    required_keys = (
        "bundle_id",
        "scene_key",
        "task_key",
        "json_output_contract",
        "json_output_contract_answer_only",
        "answer_hint",
        f"object_description_{scene_variant}",
        f"annotation_hint_{query_id}",
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
        scene_id="logic",
        bundle_id=str(prompt_config["bundle_id"]),
        scene_key=str(prompt_config["scene_key"]),
        task_key=str(prompt_config["task_key"]),
        query_key=str(query_id),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        slots={
            "object_description": str(prompt_config[f"object_description_{scene_variant}"]),
            "json_output_contract": str(prompt_config["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_config["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_config["answer_hint"]),
            "annotation_hint": str(prompt_config[f"annotation_hint_{query_id}"]),
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


class _BalanceScaleBaseTask:
    """Shared output assembly for balance-scale logic tasks."""

    domain = "puzzles"
    scene_id = "logic"
    default_dataset_enabled = True
    task_id: str
    query_id: str
    query_ids: Tuple[str, ...] = ()
    answer_fallback_min: int
    answer_fallback_max: int
    reasoning_load: float
    uses_numeric_answer_sampling: bool = True
    uses_target_cue_mode: bool = True

    def _resolve_task_query_id(
        self,
        *,
        params: Mapping[str, Any],
        gen_defaults: Mapping[str, Any],
        instance_seed: int,
        task_id: str,
    ) -> Tuple[str, Dict[str, float]]:
        supported = tuple(str(query_id) for query_id in (self.query_ids or (self.query_id,)))
        if len(supported) == 1:
            return str(supported[0]), {str(supported[0]): 1.0}
        return _resolve_query_id(
            params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=str(task_id),
            supported_query_ids=supported,
        )

    def _resolve_task_answer_seed(
        self,
        *,
        params: Mapping[str, Any],
        gen_defaults: Mapping[str, Any],
        instance_seed: int,
        task_id: str,
        query_id: str,
    ) -> Tuple[Any, Sequence[Any]]:
        if not bool(self.uses_numeric_answer_sampling):
            return None, []
        return _resolve_answer_value(
            params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=str(task_id),
            query_id=str(query_id),
            fallback_min=int(self.answer_fallback_min),
            fallback_max=int(self.answer_fallback_max),
        )

    def _build_dataset(
        self,
        *,
        params: Mapping[str, Any],
        gen_defaults: Mapping[str, Any],
        instance_seed: int,
        query_id: str,
        answer_value: int,
        answer_support: Sequence[int],
        scene_variant: str,
        target_cue_mode: str,
    ) -> Dict[str, Any]:
        raise NotImplementedError

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        task_id = str(self.task_id)
        query_id, query_id_probabilities = self._resolve_task_query_id(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=task_id,
        )
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(
            params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=task_id,
        )
        if bool(self.uses_target_cue_mode):
            target_cue_mode, target_cue_mode_probabilities = _resolve_target_cue_mode(
                params,
                gen_defaults=gen_defaults,
                instance_seed=int(instance_seed),
                task_id=task_id,
            )
        else:
            target_cue_mode, target_cue_mode_probabilities = "query_row_only", {"query_row_only": 1.0}
        answer_value, answer_support = self._resolve_task_answer_seed(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=task_id,
            query_id=query_id,
        )

        dataset: Dict[str, Any] | None = None
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            try:
                dataset = self._build_dataset(
                    params=params,
                    gen_defaults=gen_defaults,
                    instance_seed=int(instance_seed) + int(attempt_index),
                    query_id=str(query_id),
                    answer_value=answer_value,
                    answer_support=answer_support,
                    scene_variant=str(scene_variant),
                    target_cue_mode=str(target_cue_mode),
                )
                break
            except RuntimeError as exc:
                last_error = exc
        if dataset is None:
            raise RuntimeError("failed to generate balance-scale puzzle") from last_error

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
            "selection_scope": "balance_scale_panel",
            "include_tags": [],
            "exclude_tags": [],
        }
        background, background_meta = make_puzzle_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=scene_style,
        )
        with temporary_default_font_family(str(font_family)):
            rendered_scene = render_balance_scale_scene(
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
            task_id=task_id,
            query_id=query_id,
            scene_variant=str(scene_variant),
            prompt_defaults=prompt_defaults,
            instance_seed=int(instance_seed),
        )
        annotation_projection = projected_puzzle_keyed_bbox_annotation(
            rendered_scene.item_bbox_map,
            dataset["supporting_role_item_ids"],
        )
        annotation_bboxes = {
            str(key): [round(float(value), 3) for value in bbox]
            for key, bbox in annotation_projection["keyed_bbox_map"].items()
        }
        answer_type = str(dataset.get("answer_type", "integer"))
        raw_answer_value = dataset["answer_value"]
        answer_payload: int | str
        if answer_type == "integer":
            answer_payload = int(raw_answer_value)
        else:
            answer_payload = str(raw_answer_value)
        answer_gt = TypedValue(type=answer_type, value=answer_payload)
        annotation_gt = TypedValue(type="keyed_bbox_map", value=dict(annotation_bboxes))

        query_params = {
            "query_id": query_id,
            "query_id_probabilities": dict(query_id_probabilities),
            "scene_id": SCENE_ID,
            "scene_variant": str(scene_variant),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "target_cue_mode": str(target_cue_mode),
            "target_cue_mode_probabilities": dict(target_cue_mode_probabilities),
            "answer_type": answer_type,
        }
        if "answer_range" in dataset:
            query_params["answer_range"] = list(dataset["answer_range"])
        if "target_answer_support" in dataset:
            query_params["target_answer_support"] = list(dataset["target_answer_support"])
        if "answer_labels" in dataset:
            query_params["answer_labels"] = list(dataset["answer_labels"])
        trace_payload = {
            "scene_ir": {
                "scene_kind": SCENE_ID,
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": query_id,
                    "scene_id": SCENE_ID,
                    "scene_variant": str(scene_variant),
                    "target_label": str(dataset["target_label"]),
                    "answer_value": answer_payload,
                },
            },
            "query_spec": {
                "query_id": query_id,
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
                    "label_font_size_px": int(render_params.label_font_size_px),
                    "query_font_size_px": int(render_params.query_font_size_px),
                },
                "unit_size_jitter": dict(render_params.unit_size_jitter),
            },
            "render_map": with_puzzle_unit_size_jitter(
                {
                    "image_id": "img0",
                    "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                    "item_bboxes_px": {str(key): list(value) for key, value in rendered_scene.item_bbox_map.items()},
                    "keyed_item_bboxes_px": dict(annotation_bboxes),
                    "annotation_source": "keyed_item_bboxes_px",
                },
                render_params.unit_size_jitter,
            ),
            "execution_trace": {
                **dict(query_params),
                "answer_value": answer_payload,
                "target_label": str(dataset["target_label"]),
                **({"helper_label": str(dataset["helper_label"])} if "helper_label" in dataset else {}),
                **({"source_label": str(dataset["source_label"])} if "source_label" in dataset else {}),
                **({"repeated_label": str(dataset["repeated_label"])} if "repeated_label" in dataset else {}),
                "object_labels": list(dataset["object_labels"]),
                "object_specs": dict(dataset["object_specs"]),
                "object_weights": dict(dataset["object_weights"]),
                "panels": [dict(panel) for panel in dataset["panels"]],
                "equations": [dict(equation) for equation in dataset["equations"]],
                **({"comparisons": [dict(comparison) for comparison in dataset["comparisons"]]} if "comparisons" in dataset else {}),
                "supporting_role_item_ids": dict(dataset["supporting_role_item_ids"]),
                "question_format": query_id,
            },
            "witness_symbolic": {
                "type": "keyed_bbox_map",
                "value": dict(annotation_bboxes),
            },
            "projected_annotation": {
                "type": "keyed_bbox_map",
                "keyed_bbox_map": dict(annotation_bboxes),
                "pixel_keyed_bbox_map": dict(annotation_bboxes),
                "value": dict(annotation_bboxes),
            },
        }
        visual_items = sum(len(panel["left_items"]) + len(panel["right_items"]) for panel in dataset["panels"])
        return TaskOutput(
            prompt=str(prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=query_id,
            prompt_variants=dict(prompt_variants),
        )


@register_task
class PuzzlesLogicMissingObjectWeightValueTask(_BalanceScaleBaseTask):
    """Solve one missing object weight from balanced pan-scale equations."""

    task_id = MISSING_OBJECT_WEIGHT_TASK_ID
    query_id = MISSING_OBJECT_WEIGHT_QUERY_ID
    answer_fallback_min = 1
    answer_fallback_max = 20
    reasoning_load = 0.62

    def _build_dataset(
        self,
        *,
        params: Mapping[str, Any],
        gen_defaults: Mapping[str, Any],
        instance_seed: int,
        query_id: str,
        answer_value: int,
        answer_support: Sequence[int],
        scene_variant: str,
        target_cue_mode: str,
    ) -> Dict[str, Any]:
        _ = query_id
        return _build_missing_object_weight_dataset(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            answer_value=int(answer_value),
            answer_support=answer_support,
            scene_variant=str(scene_variant),
            target_cue_mode=str(target_cue_mode),
        )


@register_task
class PuzzlesLogicEquivalentObjectCountValueTask(_BalanceScaleBaseTask):
    """Solve how many repeated objects equal one source object."""

    task_id = EQUIVALENT_OBJECT_COUNT_TASK_ID
    query_id = EQUIVALENT_OBJECT_COUNT_QUERY_ID
    answer_fallback_min = 2
    answer_fallback_max = 8
    reasoning_load = 0.64

    def _build_dataset(
        self,
        *,
        params: Mapping[str, Any],
        gen_defaults: Mapping[str, Any],
        instance_seed: int,
        query_id: str,
        answer_value: int,
        answer_support: Sequence[int],
        scene_variant: str,
        target_cue_mode: str,
    ) -> Dict[str, Any]:
        _ = query_id
        return _build_equivalent_object_count_dataset(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            answer_value=int(answer_value),
            answer_support=answer_support,
            scene_variant=str(scene_variant),
            target_cue_mode=str(target_cue_mode),
        )


@register_task
class PuzzlesLogicWeightOrderLabelTask(_BalanceScaleBaseTask):
    """Infer the heaviest or lightest object from tilted balance scales."""

    task_id = WEIGHT_ORDER_TASK_ID
    query_id = HEAVIEST_OBJECT_LABEL_QUERY_ID
    query_ids = WEIGHT_ORDER_QUERY_IDS
    answer_fallback_min = 0
    answer_fallback_max = 0
    reasoning_load = 0.58
    uses_numeric_answer_sampling = False
    uses_target_cue_mode = False

    def _build_dataset(
        self,
        *,
        params: Mapping[str, Any],
        gen_defaults: Mapping[str, Any],
        instance_seed: int,
        query_id: str,
        answer_value: int,
        answer_support: Sequence[int],
        scene_variant: str,
        target_cue_mode: str,
    ) -> Dict[str, Any]:
        _ = answer_value
        _ = answer_support
        _ = target_cue_mode
        return _build_weight_order_dataset(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            query_id=str(query_id),
            scene_variant=str(scene_variant),
        )


__all__ = [
    "EQUIVALENT_OBJECT_COUNT_QUERY_ID",
    "EQUIVALENT_OBJECT_COUNT_TASK_ID",
    "HEAVIEST_OBJECT_LABEL_QUERY_ID",
    "LIGHTEST_OBJECT_LABEL_QUERY_ID",
    "MISSING_OBJECT_WEIGHT_QUERY_ID",
    "MISSING_OBJECT_WEIGHT_TASK_ID",
    "QUERY_ID",
    "SCENE_ID",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "WEIGHT_ORDER_QUERY_IDS",
    "WEIGHT_ORDER_TASK_ID",
    "PuzzlesLogicEquivalentObjectCountValueTask",
    "PuzzlesLogicMissingObjectWeightValueTask",
    "PuzzlesLogicWeightOrderLabelTask",
    "_unique_equivalent_counts",
    "_unique_target_values",
    "_unique_weight_order_labels",
]
