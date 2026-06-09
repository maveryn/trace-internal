"""Dataset construction for heatmap chart tasks."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ...shared.config_defaults import group_default, resolve_required_int_bounds
from ...shared.deterministic_sampling import resolve_selection_index
from ..shared.label_assets import resolve_chart_entity_labels
from ..shared.sampling_defaults import balanced_int_from_support as _balanced_int
from ..shared.unanswerable import (
    UNANSWERABLE_ANSWER,
    absence_proof,
    choose_missing_label,
    should_use_unanswerable_branch,
)
from .grid_common import (
    TASK_ID,
    _COLORBAR_THRESHOLD_QUERY_IDS,
    _GEN_DEFAULTS,
    _MISSING_CONDITION_PHRASES,
    _TITLE_OPTIONS,
    _condition_matches,
    _condition_phrase,
    _extremum_phrase,
    _is_continuous_colorbar_query,
)
from .grid_sampling import (
    _colorbar_interval_bounds,
    _colorbar_threshold_values,
    _colorbar_ticks,
    _labels_for_scene,
    _resolve_row_column_count,
)


def _longest_run(mask: Sequence[bool]) -> Tuple[int, int, int]:
    best_start = -1
    best_end = -1
    best_len = 0
    start = -1
    current = 0
    for index, active in enumerate(mask):
        if bool(active):
            if current == 0:
                start = int(index)
            current += 1
            if int(current) > int(best_len):
                best_len = int(current)
                best_start = int(start)
                best_end = int(index)
        else:
            current = 0
            start = -1
    return int(best_len), int(best_start), int(best_end)


def _make_cells(
    *,
    row_labels: Sequence[str],
    column_labels: Sequence[str],
    values: Sequence[Sequence[int]],
    bin_count: int,
) -> List[Dict[str, Any]]:
    cells: List[Dict[str, Any]] = []
    for row_index, row_label in enumerate(row_labels):
        for column_index, column_label in enumerate(column_labels):
            value = int(values[int(row_index)][int(column_index)])
            cells.append(
                {
                    "cell_id": f"cell_r{int(row_index)}_c{int(column_index)}",
                    "row_index": int(row_index),
                    "column_index": int(column_index),
                    "row_label": str(row_label),
                    "column_label": str(column_label),
                    "heat_level": int(value),
                    "numeric_value": int(value),
                    "heat_fraction": round(float(value) / float(max(1, int(bin_count) - 1)), 4),
                    "is_hot": bool(_condition_matches(value, condition_kind="hot", bin_count=int(bin_count))),
                    "is_cool": bool(_condition_matches(value, condition_kind="cool", bin_count=int(bin_count))),
                    "is_increase": bool(_condition_matches(value, condition_kind="increase", bin_count=int(bin_count))),
                    "is_decrease": bool(_condition_matches(value, condition_kind="decrease", bin_count=int(bin_count))),
                }
            )
    return cells


def _cells_by_position(cells: Sequence[Mapping[str, Any]]) -> Dict[Tuple[int, int], Dict[str, Any]]:
    return {
        (int(cell["row_index"]), int(cell["column_index"])): dict(cell)
        for cell in cells
    }


def _reading_order_cell_ids(cells: Sequence[Mapping[str, Any]]) -> List[str]:
    ordered = sorted(cells, key=lambda item: (int(item["row_index"]), int(item["column_index"])))
    return [str(item["cell_id"]) for item in ordered]


def _target_count_support(
    params: Mapping[str, Any],
    *,
    prefix: str,
    total_cells: int,
    fallback_min: int,
    fallback_max: int,
) -> Tuple[int, ...]:
    low, high = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key=f"{prefix}_answer_min",
        max_key=f"{prefix}_answer_max",
        fallback_min=int(fallback_min),
        fallback_max=int(fallback_max),
        context=f"{TASK_ID} {prefix} answer support",
    )
    upper = min(int(high), max(1, int(total_cells) - 1))
    lower = min(max(1, int(low)), int(upper))
    return tuple(range(int(lower), int(upper) + 1))


def _bounded_randint(rng, low: int, high: int) -> int:
    return int(rng.randint(max(0, int(low)), min(100, int(high))))


def _construct_continuous_colorbar_dataset(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Dict[str, Any]:
    row_count, column_count, row_probabilities, column_probabilities = _resolve_row_column_count(
        params,
        scene_variant="continuous_colorbar_heatmap",
        instance_seed=int(instance_seed),
    )
    total_cells = int(row_count) * int(column_count)
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.continuous_colorbar")
    row_labels, column_labels = _labels_for_scene(
        scene_variant="continuous_colorbar_heatmap",
        row_count=int(row_count),
        column_count=int(column_count),
        rng=rng,
    )
    positions = [(row, column) for row in range(int(row_count)) for column in range(int(column_count))]
    rng.shuffle(positions)

    if str(query_id) in set(_COLORBAR_THRESHOLD_QUERY_IDS):
        target_support = _target_count_support(
            params,
            prefix="colorbar_threshold",
            total_cells=int(total_cells),
            fallback_min=1,
            fallback_max=16,
        )
        target_count = _balanced_int(
            target_support,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{query_id}.target_count",
        )
        threshold = _balanced_int(
            _colorbar_threshold_values(params),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{query_id}.threshold",
        )
        gap = max(4, int(params.get("colorbar_value_margin", group_default(_GEN_DEFAULTS, "colorbar_value_margin", 6))))
        selected = set(positions[: int(target_count)])
        values: List[List[int]] = [[0 for _ in range(int(column_count))] for _ in range(int(row_count))]
        for row, column in positions:
            if str(query_id) == "colorbar_above_threshold_cell_count":
                value = _bounded_randint(rng, int(threshold) + int(gap), 100) if (row, column) in selected else _bounded_randint(rng, 0, int(threshold) - int(gap))
            else:
                value = _bounded_randint(rng, 0, int(threshold) - int(gap)) if (row, column) in selected else _bounded_randint(rng, int(threshold) + int(gap), 100)
            values[int(row)][int(column)] = int(value)
        predicate = "above" if str(query_id) == "colorbar_above_threshold_cell_count" else "below"
        question_params = {
            "colorbar_predicate": str(predicate),
            "threshold_value": int(threshold),
            "condition_phrase": f"{str(predicate)} {int(threshold)}",
            "answer_support": [int(value) for value in target_support],
        }
    elif str(query_id) == "colorbar_interval_cell_count":
        target_support = _target_count_support(
            params,
            prefix="colorbar_interval",
            total_cells=int(total_cells),
            fallback_min=1,
            fallback_max=14,
        )
        target_count = _balanced_int(
            target_support,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{query_id}.target_count",
        )
        bounds = _colorbar_interval_bounds(params)
        bound_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.{query_id}.bounds")
        lower, upper = bounds[int(bound_index) % len(bounds)]
        gap = max(4, int(params.get("colorbar_value_margin", group_default(_GEN_DEFAULTS, "colorbar_value_margin", 6))))
        selected = set(positions[: int(target_count)])
        values = [[0 for _ in range(int(column_count))] for _ in range(int(row_count))]
        for row, column in positions:
            if (row, column) in selected:
                value = _bounded_randint(rng, int(lower) + int(gap), int(upper) - int(gap))
            else:
                below_ok = int(lower) - int(gap) >= 0
                above_ok = int(upper) + int(gap) <= 100
                if bool(below_ok) and (not bool(above_ok) or (int(row) + int(column)) % 2 == 0):
                    value = _bounded_randint(rng, 0, int(lower) - int(gap))
                elif bool(above_ok):
                    value = _bounded_randint(rng, int(upper) + int(gap), 100)
                else:
                    raise ValueError(f"invalid colorbar interval bounds: {lower}, {upper}")
            values[int(row)][int(column)] = int(value)
        question_params = {
            "lower_bound": int(lower),
            "upper_bound": int(upper),
            "condition_phrase": f"from {int(lower)} to {int(upper)}, inclusive",
            "answer_support": [int(value) for value in target_support],
        }
    else:
        raise ValueError(f"unsupported continuous colorbar query id: {query_id}")

    cells = _make_cells(
        row_labels=row_labels,
        column_labels=column_labels,
        values=values,
        bin_count=101,
    )
    by_pos = _cells_by_position(cells)
    annotation_cells = [by_pos[(row, column)] for row, column in sorted(selected)]
    annotation_cell_ids = _reading_order_cell_ids(annotation_cells)
    return {
        "scene_title": str(_TITLE_OPTIONS[int(rng.randrange(len(_TITLE_OPTIONS)))]),
        "query_id": str(query_id),
        "scene_variant": "continuous_colorbar_heatmap",
        "query_axis": "",
        "condition_kind": "",
        "extremum_direction": "",
        "row_count": int(row_count),
        "column_count": int(column_count),
        "row_count_probabilities": dict(row_probabilities),
        "column_count_probabilities": dict(column_probabilities),
        "row_labels": list(row_labels),
        "column_labels": list(column_labels),
        "heat_bin_count": 101,
        "colorbar_value_min": 0,
        "colorbar_value_max": 100,
        "colorbar_ticks": [int(value) for value in _colorbar_ticks(params)],
        "values": [[int(value) for value in row] for row in values],
        "cells": [dict(cell) for cell in cells],
        "cells_by_id": {str(cell["cell_id"]): dict(cell) for cell in cells},
        "answer_value": int(target_count),
        "answer_type": "integer",
        "answer_row_index": -1,
        "answer_column_index": -1,
        "annotation_cell_ids": list(annotation_cell_ids),
        "question_params": dict(question_params),
        "is_unanswerable": False,
        "absence_proof": {},
    }

def _candidate_for_query(
    *,
    query_id: str,
    scene_variant: str,
    query_axis: str,
    condition_kind: str,
    extremum_direction: str,
    row_labels: Sequence[str],
    column_labels: Sequence[str],
    values: Sequence[Sequence[int]],
    cells: Sequence[Mapping[str, Any]],
    bin_count: int,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Dict[str, Any] | None:
    by_pos = _cells_by_position(cells)
    row_count = len(row_labels)
    column_count = len(column_labels)

    if str(query_id) == "axis_condition_extremum_label":
        if str(query_axis) == "row":
            counts = [
                sum(
                    1
                    for column_index in range(int(column_count))
                    if _condition_matches(
                        int(values[int(row_index)][int(column_index)]),
                        condition_kind=str(condition_kind),
                        bin_count=int(bin_count),
                    )
                )
                for row_index in range(int(row_count))
            ]
            label_pool = list(row_labels)
        elif str(query_axis) == "column":
            counts = [
                sum(
                    1
                    for row_index in range(int(row_count))
                    if _condition_matches(
                        int(values[int(row_index)][int(column_index)]),
                        condition_kind=str(condition_kind),
                        bin_count=int(bin_count),
                    )
                )
                for column_index in range(int(column_count))
            ]
            label_pool = list(column_labels)
        else:
            raise ValueError(f"unsupported query_axis: {query_axis}")
        maximum = max(counts)
        winners = [index for index, count in enumerate(counts) if int(count) == int(maximum)]
        if len(winners) != 1 or int(maximum) < 1:
            return None
        axis_index = int(winners[0])
        if str(query_axis) == "row":
            row_index = int(axis_index)
            column_index = -1
            annotation_cells = [
                by_pos[(row_index, col)]
                for col in range(int(column_count))
                if _condition_matches(
                    int(values[row_index][int(col)]),
                    condition_kind=str(condition_kind),
                    bin_count=int(bin_count),
                )
            ]
            condition_counts_key = "row_condition_counts"
        else:
            row_index = -1
            column_index = int(axis_index)
            annotation_cells = [
                by_pos[(row, column_index)]
                for row in range(int(row_count))
                if _condition_matches(
                    int(values[int(row)][column_index]),
                    condition_kind=str(condition_kind),
                    bin_count=int(bin_count),
                )
            ]
            condition_counts_key = "column_condition_counts"
        return {
            "answer_value": str(label_pool[axis_index]),
            "answer_type": "string",
            "answer_row_index": int(row_index),
            "answer_column_index": int(column_index),
            "annotation_cell_ids": _reading_order_cell_ids(annotation_cells),
            "question_params": {
                "query_axis": str(query_axis),
                "answer_axis": str(query_axis),
                "condition_kind": str(condition_kind),
                "condition_phrase": _condition_phrase(str(condition_kind), scene_variant=str(scene_variant)),
                condition_counts_key: {str(label_pool[index]): int(counts[index]) for index in range(len(label_pool))},
            },
        }

    if str(query_id) == "axis_cell_extremum_label" and str(query_axis) == "column":
        feasible_columns: List[int] = []
        for column_index in range(int(column_count)):
            column_values = [int(values[row_index][column_index]) for row_index in range(int(row_count))]
            target = max(column_values) if str(extremum_direction) == "hottest" else min(column_values)
            if sum(1 for value in column_values if int(value) == int(target)) == 1:
                feasible_columns.append(int(column_index))
        if not feasible_columns:
            return None
        column_index = _balanced_int(
            feasible_columns,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.selected_column",
        )
        column_values = [int(values[row_index][int(column_index)]) for row_index in range(int(row_count))]
        target = max(column_values) if str(extremum_direction) == "hottest" else min(column_values)
        row_index = int(column_values.index(int(target)))
        annotation_cells = [by_pos[(row, int(column_index))] for row in range(int(row_count))]
        return {
            "answer_value": str(row_labels[row_index]),
            "answer_type": "string",
            "answer_row_index": int(row_index),
            "answer_column_index": int(column_index),
            "annotation_cell_ids": _reading_order_cell_ids(annotation_cells),
            "question_params": {
                "query_axis": str(query_axis),
                "answer_axis": "row",
                "axis_label": str(column_labels[column_index]),
                "column_label": str(column_labels[column_index]),
                "selected_column_index": int(column_index),
                "extremum_direction": str(extremum_direction),
                "extremum_phrase": _extremum_phrase(str(extremum_direction), scene_variant=str(scene_variant)),
            },
        }

    if str(query_id) == "axis_cell_extremum_label" and str(query_axis) == "row":
        feasible_rows: List[int] = []
        for row_index in range(int(row_count)):
            row_values = [int(values[row_index][column_index]) for column_index in range(int(column_count))]
            target = max(row_values) if str(extremum_direction) == "hottest" else min(row_values)
            if sum(1 for value in row_values if int(value) == int(target)) == 1:
                feasible_rows.append(int(row_index))
        if not feasible_rows:
            return None
        row_index = _balanced_int(
            feasible_rows,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.selected_row",
        )
        row_values = [int(values[int(row_index)][column_index]) for column_index in range(int(column_count))]
        target = max(row_values) if str(extremum_direction) == "hottest" else min(row_values)
        column_index = int(row_values.index(int(target)))
        annotation_cells = [by_pos[(int(row_index), column)] for column in range(int(column_count))]
        return {
            "answer_value": str(column_labels[column_index]),
            "answer_type": "string",
            "answer_row_index": int(row_index),
            "answer_column_index": int(column_index),
            "annotation_cell_ids": _reading_order_cell_ids(annotation_cells),
            "question_params": {
                "query_axis": str(query_axis),
                "answer_axis": "column",
                "axis_label": str(row_labels[row_index]),
                "row_label": str(row_labels[row_index]),
                "selected_row_index": int(row_index),
                "extremum_direction": str(extremum_direction),
                "extremum_phrase": _extremum_phrase(str(extremum_direction), scene_variant=str(scene_variant)),
            },
        }

    if str(query_id) == "condition_run_extremum_label":
        run_specs: List[Tuple[int, int, int]] = []
        for row_index in range(int(row_count)):
            mask = [
                _condition_matches(
                    int(values[row_index][column_index]),
                    condition_kind=str(condition_kind),
                    bin_count=int(bin_count),
                )
                for column_index in range(int(column_count))
            ]
            run_specs.append(_longest_run(mask))
        longest = max(run_len for run_len, _, _ in run_specs)
        winners = [index for index, (run_len, _, _) in enumerate(run_specs) if int(run_len) == int(longest)]
        if len(winners) != 1 or int(longest) < 2:
            return None
        row_index = int(winners[0])
        _, start, end = run_specs[row_index]
        annotation_cells = [by_pos[(row_index, column_index)] for column_index in range(int(start), int(end) + 1)]
        return {
            "answer_value": str(row_labels[row_index]),
            "answer_type": "string",
            "answer_row_index": int(row_index),
            "answer_column_index": -1,
            "annotation_cell_ids": _reading_order_cell_ids(annotation_cells),
            "question_params": {
                "query_axis": "row",
                "answer_axis": "row",
                "condition_kind": str(condition_kind),
                "condition_phrase": _condition_phrase(str(condition_kind), scene_variant=str(scene_variant)),
                "longest_run_length": int(longest),
                "row_run_lengths": {str(row_labels[index]): int(run_specs[index][0]) for index in range(int(row_count))},
            },
        }

    raise ValueError(f"unsupported query_id: {query_id}")


def _candidate_for_unanswerable_query(
    *,
    query_id: str,
    query_axis: str,
    row_labels: Sequence[str],
    column_labels: Sequence[str],
    scene_variant: str,
    extremum_direction: str,
    instance_seed: int,
) -> Dict[str, Any] | None:
    if str(query_id) == "axis_cell_extremum_label":
        if str(query_axis) == "row":
            missing_label = choose_missing_label(
                visible_labels=row_labels,
                candidate_labels=resolve_chart_entity_labels(
                    spawn_rng(int(instance_seed), f"{TASK_ID}.axis_cell_missing_row_candidates"),
                    count=max(16, len(row_labels) + 8),
                    min_chars=2,
                    max_chars=7,
                    allow_spaces=False,
                ).labels,
                fallback_prefix="Row ",
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.axis_cell_missing_row",
            )
            return {
                "answer_value": UNANSWERABLE_ANSWER,
                "answer_type": "string",
                "answer_row_index": -1,
                "answer_column_index": -1,
                "annotation_cell_ids": [],
                "question_params": {
                    "query_axis": "row",
                    "answer_axis": "column",
                    "axis_label": str(missing_label),
                    "row_label": str(missing_label),
                    "extremum_direction": str(extremum_direction),
                    "extremum_phrase": _extremum_phrase(str(extremum_direction), scene_variant=str(scene_variant)),
                },
                "is_unanswerable": True,
                "absence_proof": absence_proof(
                    requested_item=str(missing_label),
                    visible_candidates=[str(label) for label in row_labels],
                    checked_scope="heatmap row labels",
                    absence_reason="requested row label is not visible in the heatmap",
                ),
            }
        missing_label = choose_missing_label(
            visible_labels=column_labels,
            candidate_labels=resolve_chart_entity_labels(
                spawn_rng(int(instance_seed), f"{TASK_ID}.axis_cell_missing_column_candidates"),
                count=max(16, len(column_labels) + 8),
                min_chars=2,
                max_chars=7,
                allow_spaces=False,
            ).labels,
            fallback_prefix="Column ",
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.axis_cell_missing_column",
        )
        return {
            "answer_value": UNANSWERABLE_ANSWER,
            "answer_type": "string",
            "answer_row_index": -1,
            "answer_column_index": -1,
            "annotation_cell_ids": [],
            "question_params": {
                "query_axis": "column",
                "answer_axis": "row",
                "axis_label": str(missing_label),
                "column_label": str(missing_label),
                "extremum_direction": str(extremum_direction),
                "extremum_phrase": _extremum_phrase(str(extremum_direction), scene_variant=str(scene_variant)),
            },
            "is_unanswerable": True,
            "absence_proof": absence_proof(
                requested_item=str(missing_label),
                visible_candidates=[str(label) for label in column_labels],
                checked_scope="heatmap column labels",
                absence_reason="requested column label is not visible in the heatmap",
            ),
        }

    if str(query_id) == "axis_condition_extremum_label":
        missing_condition = choose_missing_label(
            visible_labels=(
                "high-intensity",
                "low-intensity",
                "increase-colored",
                "decrease-colored",
                "high-activity",
                "low-activity",
            ),
            candidate_labels=_MISSING_CONDITION_PHRASES,
            fallback_prefix="missing condition ",
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.axis_condition_missing_condition",
        )
        visible_conditions = (
            ["high-activity", "low-activity"]
            if str(scene_variant) == "calendar_heatmap"
            else ["high-intensity", "low-intensity", "increase-colored", "decrease-colored"]
        )
        return {
            "answer_value": UNANSWERABLE_ANSWER,
            "answer_type": "string",
            "answer_row_index": -1,
            "answer_column_index": -1,
            "annotation_cell_ids": [],
            "question_params": {
                "query_axis": str(query_axis),
                "answer_axis": str(query_axis),
                "condition_phrase": str(missing_condition),
                "missing_condition_phrase": str(missing_condition),
            },
            "is_unanswerable": True,
            "absence_proof": absence_proof(
                requested_item=str(missing_condition),
                visible_candidates=visible_conditions,
                checked_scope="heatmap legend/color condition vocabulary",
                absence_reason="requested color condition is not represented by the heatmap legend",
            ),
        }

    return None


def _construct_dataset(
    *,
    query_id: str,
    scene_variant: str,
    query_axis: str,
    condition_kind: str,
    extremum_direction: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Dict[str, Any]:
    if _is_continuous_colorbar_query(str(query_id)):
        if str(scene_variant) != "continuous_colorbar_heatmap":
            raise ValueError("continuous colorbar heatmap queries require scene_variant='continuous_colorbar_heatmap'")
        return _construct_continuous_colorbar_dataset(
            query_id=str(query_id),
            params=params,
            instance_seed=int(instance_seed),
        )
    if str(scene_variant) == "continuous_colorbar_heatmap":
        raise ValueError("scene_variant='continuous_colorbar_heatmap' is only supported by colorbar count queries")

    bin_count = int(params.get("heat_bin_count", group_default(_GEN_DEFAULTS, "heat_bin_count", 5)))
    if int(bin_count) < 5:
        raise ValueError(f"{TASK_ID} requires heat_bin_count >= 5")
    row_count, column_count, row_probabilities, column_probabilities = _resolve_row_column_count(
        params,
        scene_variant=str(scene_variant),
        instance_seed=int(instance_seed),
    )
    for attempt in range(512):
        rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset.{attempt}")
        row_labels, column_labels = _labels_for_scene(
            scene_variant=str(scene_variant),
            row_count=int(row_count),
            column_count=int(column_count),
            rng=rng,
        )
        values = [
            [int(rng.randrange(int(bin_count))) for _ in range(int(column_count))]
            for _ in range(int(row_count))
        ]
        cells = _make_cells(
            row_labels=row_labels,
            column_labels=column_labels,
            values=values,
            bin_count=int(bin_count),
        )
        if should_use_unanswerable_branch(
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{query_id}",
            enabled=bool(params.get("_enable_unanswerable", False)),
        ):
            query = _candidate_for_unanswerable_query(
                query_id=str(query_id),
                query_axis=str(query_axis),
                row_labels=row_labels,
                column_labels=column_labels,
                scene_variant=str(scene_variant),
                extremum_direction=str(extremum_direction),
                instance_seed=int(instance_seed),
            )
        else:
            query = _candidate_for_query(
                query_id=str(query_id),
                scene_variant=str(scene_variant),
                query_axis=str(query_axis),
                condition_kind=str(condition_kind),
                extremum_direction=str(extremum_direction),
                row_labels=row_labels,
                column_labels=column_labels,
                values=values,
                cells=cells,
                bin_count=int(bin_count),
                params=params,
                instance_seed=int(instance_seed),
            )
        if query is None:
            continue
        query_condition_kind = str(dict(query["question_params"]).get("condition_kind", condition_kind))
        return {
            "scene_title": str(_TITLE_OPTIONS[int(rng.randrange(len(_TITLE_OPTIONS)))]),
            "query_id": str(query_id),
            "scene_variant": str(scene_variant),
            "query_axis": str(query_axis),
            "condition_kind": str(query_condition_kind),
            "extremum_direction": str(extremum_direction),
            "row_count": int(row_count),
            "column_count": int(column_count),
            "row_count_probabilities": dict(row_probabilities),
            "column_count_probabilities": dict(column_probabilities),
            "row_labels": list(row_labels),
            "column_labels": list(column_labels),
            "heat_bin_count": int(bin_count),
            "values": [[int(value) for value in row] for row in values],
            "cells": [dict(cell) for cell in cells],
            "cells_by_id": {str(cell["cell_id"]): dict(cell) for cell in cells},
            "answer_value": str(query["answer_value"]),
            "answer_type": str(query["answer_type"]),
            "answer_row_index": int(query["answer_row_index"]),
            "answer_column_index": int(query["answer_column_index"]),
            "annotation_cell_ids": [str(cell_id) for cell_id in query["annotation_cell_ids"]],
            "question_params": dict(query["question_params"]),
            "is_unanswerable": bool(query.get("is_unanswerable", False)),
            "absence_proof": dict(query.get("absence_proof", {})),
        }
    raise ValueError(f"could not construct unique-answer heatmap for {TASK_ID}")
