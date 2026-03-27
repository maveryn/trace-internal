"""Shared dataset and config helpers for table tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ...shared.config_defaults import group_default, resolve_required_int_bounds
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.name_assets import load_short_name_manifest
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from .table_scene import SUPPORTED_TABLE_SCENE_VARIANTS, TableRenderParams


_DEFAULT_HEADER_POOL: Tuple[str, ...] = (
    "Age",
    "Cost",
    "Dist",
    "Gain",
    "Mass",
    "Pts",
    "Rate",
    "Rank",
    "Score",
    "Temp",
    "Time",
    "Wins",
)


@dataclass(frozen=True)
class TableDefaults:
    """Stable fallback defaults shared by table tasks."""

    row_count_min: int = 5
    row_count_max: int = 10
    numeric_column_count_min: int = 3
    numeric_column_count_max: int = 5
    value_min: int = 1
    value_max: int = 32
    canvas_width: int = 940
    canvas_height: int = 640
    table_margin_left_px: int = 52
    table_margin_right_px: int = 52
    table_margin_top_px: int = 56
    table_margin_bottom_px: int = 52
    row_label_width_fraction: float = 0.28
    label_font_size_px: int = 24
    value_font_size_px: int = 22
    border_width_px: int = 2
    grid_width_px: int = 1
    rounded_corner_radius_px: int = 18
    cell_padding_px: int = 14
    balanced_task_variant_sampling: bool = True
    balanced_scene_variant_sampling: bool = True


def resolve_table_axis_variant(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    supported_variants: Sequence[str],
    task_id: str,
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    axis_namespace: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced table task/scene variant axis."""

    variant_rng = spawn_rng(int(instance_seed), f"{task_id}.{axis_namespace}")
    selected_variant, probabilities = resolve_variant(
        variant_rng,
        params=params,
        gen_defaults=gen_defaults,
        supported_variants=supported_variants,
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
    )
    variant = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        selected_variant=str(selected_variant),
        variant_probabilities=probabilities,
        supported_variants=supported_variants,
        balance_flag_key=str(balance_flag_key),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        sampling_namespace=f"{task_id}:{axis_namespace}",
    )
    return str(variant), {str(key): float(value) for key, value in sorted(probabilities.items())}


def resolve_row_count_bounds(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    defaults: TableDefaults,
    task_id: str,
) -> Tuple[int, int]:
    """Resolve inclusive row-count bounds."""

    return resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="row_count_min",
        max_key="row_count_max",
        fallback_min=int(defaults.row_count_min),
        fallback_max=int(defaults.row_count_max),
        context=f"generation defaults for {task_id}",
    )


def resolve_numeric_column_count_bounds(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    defaults: TableDefaults,
    task_id: str,
) -> Tuple[int, int]:
    """Resolve inclusive numeric-column-count bounds."""

    return resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="numeric_column_count_min",
        max_key="numeric_column_count_max",
        fallback_min=int(defaults.numeric_column_count_min),
        fallback_max=int(defaults.numeric_column_count_max),
        context=f"generation defaults for {task_id}",
    )


def resolve_value_bounds(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    defaults: TableDefaults,
    task_id: str,
) -> Tuple[int, int]:
    """Resolve inclusive numeric cell-value bounds."""

    return resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="value_min",
        max_key="value_max",
        fallback_min=int(defaults.value_min),
        fallback_max=int(defaults.value_max),
        context=f"generation defaults for {task_id}",
    )


def sample_table_row_labels(*, count: int, instance_seed: int, namespace: str = "tables.row_labels") -> Tuple[str, ...]:
    """Sample one tuple of unique short row-label names."""

    pool = load_short_name_manifest()
    if int(count) <= 0:
        raise ValueError("row count must be positive")
    if int(count) > len(pool):
        raise ValueError("row count exceeds the supported name pool")
    rng = spawn_rng(int(instance_seed), str(namespace))
    candidates = list(pool)
    rng.shuffle(candidates)
    return tuple(str(value) for value in candidates[: int(count)])


def sample_numeric_column_headers(
    *,
    count: int,
    instance_seed: int,
    namespace: str = "tables.numeric_headers",
) -> Tuple[str, ...]:
    """Sample one tuple of unique short numeric-column headers."""

    if int(count) <= 0:
        raise ValueError("numeric column count must be positive")
    if int(count) > len(_DEFAULT_HEADER_POOL):
        raise ValueError("numeric column count exceeds the supported header pool")
    rng = spawn_rng(int(instance_seed), str(namespace))
    candidates = list(_DEFAULT_HEADER_POOL)
    rng.shuffle(candidates)
    return tuple(str(value) for value in candidates[: int(count)])


def resolve_table_render_params(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
    defaults: TableDefaults,
) -> TableRenderParams:
    """Resolve one normalized table-render parameter block."""

    def _rgb(key: str, fallback: Sequence[int]) -> Tuple[int, int, int]:
        raw = params.get(key, group_default(render_defaults, key, list(fallback)))
        return (
            int(raw[0]),
            int(raw[1]),
            int(raw[2]),
        )

    return TableRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(render_defaults, "canvas_width", defaults.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(render_defaults, "canvas_height", defaults.canvas_height))),
        table_margin_left_px=int(
            params.get("table_margin_left_px", group_default(render_defaults, "table_margin_left_px", defaults.table_margin_left_px))
        ),
        table_margin_right_px=int(
            params.get("table_margin_right_px", group_default(render_defaults, "table_margin_right_px", defaults.table_margin_right_px))
        ),
        table_margin_top_px=int(
            params.get("table_margin_top_px", group_default(render_defaults, "table_margin_top_px", defaults.table_margin_top_px))
        ),
        table_margin_bottom_px=int(
            params.get("table_margin_bottom_px", group_default(render_defaults, "table_margin_bottom_px", defaults.table_margin_bottom_px))
        ),
        row_label_width_fraction=float(
            params.get(
                "row_label_width_fraction",
                group_default(render_defaults, "row_label_width_fraction", defaults.row_label_width_fraction),
            )
        ),
        header_fill_rgb=_rgb("header_fill_rgb", (232, 236, 243)),
        zebra_row_fill_rgb=_rgb("zebra_row_fill_rgb", (247, 249, 252)),
        card_fill_rgb=_rgb("card_fill_rgb", (250, 250, 252)),
        border_color_rgb=_rgb("border_color_rgb", (92, 98, 109)),
        grid_color_rgb=_rgb("grid_color_rgb", (204, 209, 218)),
        text_color_rgb=_rgb("text_color_rgb", (36, 39, 45)),
        text_stroke_rgb=_rgb("text_stroke_rgb", (255, 255, 255)),
        label_font_size_px=int(
            params.get("label_font_size_px", group_default(render_defaults, "label_font_size_px", defaults.label_font_size_px))
        ),
        value_font_size_px=int(
            params.get("value_font_size_px", group_default(render_defaults, "value_font_size_px", defaults.value_font_size_px))
        ),
        border_width_px=int(
            params.get("border_width_px", group_default(render_defaults, "border_width_px", defaults.border_width_px))
        ),
        grid_width_px=int(
            params.get("grid_width_px", group_default(render_defaults, "grid_width_px", defaults.grid_width_px))
        ),
        rounded_corner_radius_px=int(
            params.get(
                "rounded_corner_radius_px",
                group_default(render_defaults, "rounded_corner_radius_px", defaults.rounded_corner_radius_px),
            )
        ),
        cell_padding_px=int(
            params.get("cell_padding_px", group_default(render_defaults, "cell_padding_px", defaults.cell_padding_px))
        ),
    )


def build_summary_label_dataset_for_variant(
    *,
    task_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: TableDefaults,
    task_id: str,
) -> Dict[str, Any]:
    """Construct one deterministic table dataset for argmax/argmin row-label queries."""

    if str(task_variant) not in {"argmax", "argmin"}:
        raise ValueError(f"unsupported table summary-label variant: {task_variant}")

    row_count_min, row_count_max = resolve_row_count_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    numeric_col_count_min, numeric_col_count_max = resolve_numeric_column_count_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    value_min, value_max = resolve_value_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )

    rng = spawn_rng(int(instance_seed), f"{task_id}.dataset")
    row_count = int(rng.randint(int(row_count_min), int(row_count_max)))
    numeric_column_count = int(rng.randint(int(numeric_col_count_min), int(numeric_col_count_max)))
    row_labels = list(sample_table_row_labels(count=int(row_count), instance_seed=int(instance_seed)))
    column_headers = list(sample_numeric_column_headers(count=int(numeric_column_count), instance_seed=int(instance_seed)))

    query_col_index = int(resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}:query_column",
    )) % int(numeric_column_count)
    answer_row_index = int(resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}:answer_row",
    )) % int(row_count)
    query_column = str(column_headers[int(query_col_index)])
    answer_row_label = str(row_labels[int(answer_row_index)])

    if int(value_max) - int(value_min) + 1 < int(row_count):
        raise ValueError("table value range must support unique column extrema")
    unique_query_values = rng.sample(range(int(value_min), int(value_max) + 1), int(row_count))
    winning_value = max(unique_query_values) if str(task_variant) == "argmax" else min(unique_query_values)
    remaining_values = [int(value) for value in unique_query_values if int(value) != int(winning_value)]
    rng.shuffle(remaining_values)

    query_values_by_row: Dict[str, int] = {str(answer_row_label): int(winning_value)}
    remaining_rows = [str(label) for label in row_labels if str(label) != str(answer_row_label)]
    for row_label, value in zip(remaining_rows, remaining_values):
        query_values_by_row[str(row_label)] = int(value)

    values_by_row: Dict[str, Dict[str, int]] = {}
    for row_label in row_labels:
        row_values: Dict[str, int] = {}
        for header in column_headers:
            if str(header) == str(query_column):
                row_values[str(header)] = int(query_values_by_row[str(row_label)])
            else:
                row_values[str(header)] = int(rng.randint(int(value_min), int(value_max)))
        values_by_row[str(row_label)] = dict(row_values)

    answer_value = int(values_by_row[str(answer_row_label)][str(query_column)])
    return {
        "row_count": int(row_count),
        "numeric_column_count": int(numeric_column_count),
        "row_count_range": [int(row_count_min), int(row_count_max)],
        "numeric_column_count_range": [int(numeric_col_count_min), int(numeric_col_count_max)],
        "value_range": [int(value_min), int(value_max)],
        "row_labels": [str(label) for label in row_labels],
        "column_headers": [str(header) for header in column_headers],
        "query_column": str(query_column),
        "values_by_row": dict(values_by_row),
        "answer_row_label": str(answer_row_label),
        "answer_value": int(answer_value),
        "answer_row_index": int(answer_row_index),
        "query_column_index": int(query_col_index),
    }


def projected_table_bbox_evidence(
    rendered_scene,
    cell_ids: Sequence[str],
) -> Dict[str, Any]:
    """Project one ordered table-cell id list into `bbox_set` evidence."""

    requested = [str(cell_id) for cell_id in cell_ids]
    bbox_by_cell = {
        str(cell_trace["cell_id"]): [float(value) for value in cell_trace["bbox_px"]]
        for cell_trace in rendered_scene.cell_traces
    }
    return {
        "bbox_set": [
            list(bbox_by_cell[str(cell_id)])
            for cell_id in requested
            if str(cell_id) in bbox_by_cell
        ]
    }


__all__ = [
    "SUPPORTED_TABLE_SCENE_VARIANTS",
    "TableDefaults",
    "build_summary_label_dataset_for_variant",
    "projected_table_bbox_evidence",
    "resolve_numeric_column_count_bounds",
    "resolve_row_count_bounds",
    "resolve_table_axis_variant",
    "resolve_table_render_params",
    "sample_numeric_column_headers",
    "sample_table_row_labels",
]
