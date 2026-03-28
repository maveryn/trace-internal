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


def table_value_cell_id(*, data_row_index: int, numeric_column_index: int) -> str:
    """Return the rendered cell id for one numeric-value table cell."""

    return f"cell_r{int(data_row_index) + 1}_c{int(numeric_column_index) + 1}"


def _build_values_by_row(
    *,
    row_labels: Sequence[str],
    column_headers: Sequence[str],
    rng,
    value_min: int,
    value_max: int,
    query_column: str | None = None,
    query_values_by_row: Mapping[str, int] | None = None,
) -> Dict[str, Dict[str, int]]:
    """Populate one deterministic numeric table, optionally fixing one queried column."""

    if (query_column is None) != (query_values_by_row is None):
        raise ValueError("query_column and query_values_by_row must be provided together")

    values_by_row: Dict[str, Dict[str, int]] = {}
    for row_label in row_labels:
        resolved_row_label = str(row_label)
        row_values: Dict[str, int] = {}
        for header in column_headers:
            resolved_header = str(header)
            if query_values_by_row is not None and resolved_header == str(query_column):
                row_values[resolved_header] = int(query_values_by_row[resolved_row_label])
            else:
                row_values[resolved_header] = int(rng.randint(int(value_min), int(value_max)))
        values_by_row[resolved_row_label] = dict(row_values)
    return values_by_row


def _sample_values_with_total(*, count: int, target_total: int, min_value: int, max_value: int, rng) -> List[int]:
    """Sample `count` bounded integers whose sum equals `target_total`."""

    values: List[int] = []
    remaining_total = int(target_total)
    for index in range(int(count)):
        slots_left = int(count) - int(index) - 1
        min_here = max(int(min_value), int(remaining_total - (slots_left * int(max_value))))
        max_here = min(int(max_value), int(remaining_total - (slots_left * int(min_value))))
        if int(min_here) > int(max_here):
            raise ValueError("failed to construct bounded values for requested total")
        values.append(int(rng.randint(int(min_here), int(max_here))))
        remaining_total -= int(values[-1])
    rng.shuffle(values)
    return [int(value) for value in values]


def _resolve_base_table_schema(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: TableDefaults,
    task_id: str,
    odd_row_count_required: bool = False,
) -> Dict[str, Any]:
    """Resolve one reusable base table schema and queried numeric column."""

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
    if bool(odd_row_count_required):
        odd_counts = [
            int(value)
            for value in range(int(row_count_min), int(row_count_max) + 1)
            if int(value) % 2 == 1
        ]
        if not odd_counts:
            raise ValueError("table row-count bounds must include an odd count for this variant")
        row_count = int(odd_counts[int(rng.randint(0, len(odd_counts) - 1))])
    else:
        row_count = int(rng.randint(int(row_count_min), int(row_count_max)))
    numeric_column_count = int(rng.randint(int(numeric_col_count_min), int(numeric_col_count_max)))
    row_labels = list(sample_table_row_labels(count=int(row_count), instance_seed=int(instance_seed)))
    column_headers = list(sample_numeric_column_headers(count=int(numeric_column_count), instance_seed=int(instance_seed)))

    query_col_index = int(resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}:query_column",
    )) % int(numeric_column_count)
    query_column = str(column_headers[int(query_col_index)])
    return {
        "rng": rng,
        "row_count": int(row_count),
        "numeric_column_count": int(numeric_column_count),
        "row_count_range": [int(row_count_min), int(row_count_max)],
        "numeric_column_count_range": [int(numeric_col_count_min), int(numeric_col_count_max)],
        "value_range": [int(value_min), int(value_max)],
        "value_min": int(value_min),
        "value_max": int(value_max),
        "row_labels": [str(label) for label in row_labels],
        "column_headers": [str(header) for header in column_headers],
        "query_column": str(query_column),
        "query_column_index": int(query_col_index),
    }


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

    base = _resolve_base_table_schema(
        params=params,
        instance_seed=int(instance_seed),
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    rng = base["rng"]
    row_count = int(base["row_count"])
    numeric_column_count = int(base["numeric_column_count"])
    row_labels = list(base["row_labels"])
    column_headers = list(base["column_headers"])
    query_col_index = int(base["query_column_index"])
    answer_row_index = int(resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}:answer_row",
    )) % int(row_count)
    query_column = str(base["query_column"])
    answer_row_label = str(row_labels[int(answer_row_index)])
    value_min = int(base["value_min"])
    value_max = int(base["value_max"])

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

    values_by_row = _build_values_by_row(
        row_labels=row_labels,
        column_headers=column_headers,
        rng=rng,
        value_min=int(value_min),
        value_max=int(value_max),
        query_column=str(query_column),
        query_values_by_row=query_values_by_row,
    )

    answer_value = int(values_by_row[str(answer_row_label)][str(query_column)])
    return {
        "row_count": int(row_count),
        "numeric_column_count": int(numeric_column_count),
        "row_count_range": list(base["row_count_range"]),
        "numeric_column_count_range": list(base["numeric_column_count_range"]),
        "value_range": list(base["value_range"]),
        "row_labels": [str(label) for label in row_labels],
        "column_headers": [str(header) for header in column_headers],
        "query_column": str(query_column),
        "values_by_row": dict(values_by_row),
        "answer_row_label": str(answer_row_label),
        "answer_value": int(answer_value),
        "answer_row_index": int(answer_row_index),
        "query_column_index": int(query_col_index),
    }


def build_summary_value_dataset_for_variant(
    *,
    task_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: TableDefaults,
    task_id: str,
) -> Dict[str, Any]:
    """Construct one deterministic table dataset for column-summary numeric queries."""

    if str(task_variant) not in {"column_sum", "column_mean", "column_median"}:
        raise ValueError(f"unsupported table summary-value variant: {task_variant}")

    base = _resolve_base_table_schema(
        params=params,
        instance_seed=int(instance_seed),
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
        odd_row_count_required=(str(task_variant) == "column_median"),
    )
    rng = base["rng"]
    row_count = int(base["row_count"])
    numeric_column_count = int(base["numeric_column_count"])
    row_labels = list(base["row_labels"])
    column_headers = list(base["column_headers"])
    query_col_index = int(base["query_column_index"])
    query_column = str(base["query_column"])
    value_min = int(base["value_min"])
    value_max = int(base["value_max"])

    if str(task_variant) == "column_sum":
        target_sum = int(rng.randint(int(row_count * value_min), int(row_count * value_max)))
        query_values = _sample_values_with_total(
            count=int(row_count),
            target_total=int(target_sum),
            min_value=int(value_min),
            max_value=int(value_max),
            rng=rng,
        )
        answer_value = int(target_sum)
    elif str(task_variant) == "column_mean":
        target_mean = int(rng.randint(int(value_min), int(value_max)))
        query_values = _sample_values_with_total(
            count=int(row_count),
            target_total=int(row_count * target_mean),
            min_value=int(value_min),
            max_value=int(value_max),
            rng=rng,
        )
        answer_value = int(target_mean)
    else:
        if int(value_max) - int(value_min) < 2:
            raise ValueError("table value range must support strict lower/upper values around the median")
        target_median = int(rng.randint(int(value_min + 1), int(value_max - 1)))
        lower_count = int(row_count // 2)
        upper_count = int(row_count // 2)
        lower_values = [int(rng.randint(int(value_min), int(target_median - 1))) for _ in range(int(lower_count))]
        upper_values = [int(rng.randint(int(target_median + 1), int(value_max))) for _ in range(int(upper_count))]
        query_values = [*lower_values, int(target_median), *upper_values]
        rng.shuffle(query_values)
        answer_value = int(target_median)

    query_values_by_row = {
        str(row_label): int(query_values[int(row_index)])
        for row_index, row_label in enumerate(row_labels)
    }
    values_by_row = _build_values_by_row(
        row_labels=row_labels,
        column_headers=column_headers,
        rng=rng,
        value_min=int(value_min),
        value_max=int(value_max),
        query_column=str(query_column),
        query_values_by_row=query_values_by_row,
    )

    return {
        "row_count": int(row_count),
        "numeric_column_count": int(numeric_column_count),
        "row_count_range": list(base["row_count_range"]),
        "numeric_column_count_range": list(base["numeric_column_count_range"]),
        "value_range": list(base["value_range"]),
        "row_labels": [str(label) for label in row_labels],
        "column_headers": [str(header) for header in column_headers],
        "query_column": str(query_column),
        "values_by_row": dict(values_by_row),
        "answer_value": int(answer_value),
        "query_column_index": int(query_col_index),
    }


def build_row_summary_value_dataset_for_variant(
    *,
    task_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: TableDefaults,
    task_id: str,
) -> Dict[str, Any]:
    """Construct one deterministic table dataset for row-summary numeric queries."""

    if str(task_variant) not in {"row_sum", "row_mean"}:
        raise ValueError(f"unsupported table row-summary variant: {task_variant}")

    base = _resolve_base_table_schema(
        params=params,
        instance_seed=int(instance_seed),
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    rng = base["rng"]
    row_count = int(base["row_count"])
    numeric_column_count = int(base["numeric_column_count"])
    row_labels = list(base["row_labels"])
    column_headers = list(base["column_headers"])
    value_min = int(base["value_min"])
    value_max = int(base["value_max"])
    query_row_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}:query_row",
        )
    ) % int(row_count)
    query_row_label = str(row_labels[int(query_row_index)])

    if str(task_variant) == "row_sum":
        target_sum = int(rng.randint(int(numeric_column_count * value_min), int(numeric_column_count * value_max)))
        query_row_values = _sample_values_with_total(
            count=int(numeric_column_count),
            target_total=int(target_sum),
            min_value=int(value_min),
            max_value=int(value_max),
            rng=rng,
        )
        answer_value = int(target_sum)
    else:
        target_mean = int(rng.randint(int(value_min), int(value_max)))
        query_row_values = _sample_values_with_total(
            count=int(numeric_column_count),
            target_total=int(numeric_column_count * target_mean),
            min_value=int(value_min),
            max_value=int(value_max),
            rng=rng,
        )
        answer_value = int(target_mean)

    values_by_row = _build_values_by_row(
        row_labels=row_labels,
        column_headers=column_headers,
        rng=rng,
        value_min=int(value_min),
        value_max=int(value_max),
    )
    values_by_row[str(query_row_label)] = {
        str(header): int(query_row_values[int(column_index)])
        for column_index, header in enumerate(column_headers)
    }
    return {
        "row_count": int(row_count),
        "numeric_column_count": int(numeric_column_count),
        "row_count_range": list(base["row_count_range"]),
        "numeric_column_count_range": list(base["numeric_column_count_range"]),
        "value_range": list(base["value_range"]),
        "row_labels": [str(label) for label in row_labels],
        "column_headers": [str(header) for header in column_headers],
        "query_row_label": str(query_row_label),
        "query_row_index": int(query_row_index),
        "values_by_row": dict(values_by_row),
        "answer_value": int(answer_value),
    }


def build_counting_value_dataset_for_variant(
    *,
    task_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: TableDefaults,
    task_id: str,
) -> Dict[str, Any]:
    """Construct one deterministic table dataset for column-filter counting queries."""

    supported_variants = {"above_threshold", "below_threshold", "in_interval"}
    if str(task_variant) not in supported_variants:
        raise ValueError(f"unsupported table counting variant: {task_variant}")

    base = _resolve_base_table_schema(
        params=params,
        instance_seed=int(instance_seed),
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    rng = base["rng"]
    row_count = int(base["row_count"])
    numeric_column_count = int(base["numeric_column_count"])
    row_labels = list(base["row_labels"])
    column_headers = list(base["column_headers"])
    query_col_index = int(base["query_column_index"])
    query_column = str(base["query_column"])
    value_min = int(base["value_min"])
    value_max = int(base["value_max"])
    target_count = int(resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}:target_count",
    )) % int(row_count + 1)

    def _sample_values(*, count: int, low: int, high: int) -> List[int]:
        if int(count) <= 0:
            return []
        if int(low) > int(high):
            raise ValueError("invalid bounded sampling range")
        return [int(rng.randint(int(low), int(high))) for _ in range(int(count))]

    metadata: Dict[str, Any] = {}
    if str(task_variant) == "above_threshold":
        if int(target_count) == int(row_count):
            threshold_value = int(value_min - 1)
            query_values = _sample_values(count=int(row_count), low=int(value_min), high=int(value_max))
        elif int(target_count) == 0:
            threshold_value = int(value_max)
            query_values = _sample_values(count=int(row_count), low=int(value_min), high=int(value_max))
        else:
            threshold_value = int(rng.randint(int(value_min), int(value_max - 1)))
            query_values = [
                *_sample_values(count=int(target_count), low=int(threshold_value + 1), high=int(value_max)),
                *_sample_values(count=int(row_count - target_count), low=int(value_min), high=int(threshold_value)),
            ]
        rng.shuffle(query_values)
        metadata["threshold_value"] = int(threshold_value)

        def _matches(value: int) -> bool:
            return int(value) > int(threshold_value)

    elif str(task_variant) == "below_threshold":
        if int(target_count) == int(row_count):
            threshold_value = int(value_max + 1)
            query_values = _sample_values(count=int(row_count), low=int(value_min), high=int(value_max))
        elif int(target_count) == 0:
            threshold_value = int(value_min)
            query_values = _sample_values(count=int(row_count), low=int(value_min), high=int(value_max))
        else:
            threshold_value = int(rng.randint(int(value_min + 1), int(value_max)))
            query_values = [
                *_sample_values(count=int(target_count), low=int(value_min), high=int(threshold_value - 1)),
                *_sample_values(count=int(row_count - target_count), low=int(threshold_value), high=int(value_max)),
            ]
        rng.shuffle(query_values)
        metadata["threshold_value"] = int(threshold_value)

        def _matches(value: int) -> bool:
            return int(value) < int(threshold_value)

    else:
        if int(target_count) == int(row_count):
            interval_min = int(value_min)
            interval_max = int(value_max)
            query_values = _sample_values(count=int(row_count), low=int(value_min), high=int(value_max))
        else:
            while True:
                interval_min = int(rng.randint(int(value_min), int(value_max)))
                interval_max = int(rng.randint(int(interval_min), int(value_max)))
                inside_values = list(range(int(interval_min), int(interval_max) + 1))
                outside_values = [
                    int(value)
                    for value in range(int(value_min), int(value_max) + 1)
                    if int(value) < int(interval_min) or int(value) > int(interval_max)
                ]
                if int(target_count) == 0 and outside_values:
                    query_values = [int(outside_values[int(rng.randint(0, len(outside_values) - 1))]) for _ in range(int(row_count))]
                    break
                if int(target_count) > 0 and inside_values and outside_values:
                    query_values = [
                        *[
                            int(inside_values[int(rng.randint(0, len(inside_values) - 1))])
                            for _ in range(int(target_count))
                        ],
                        *[
                            int(outside_values[int(rng.randint(0, len(outside_values) - 1))])
                            for _ in range(int(row_count - target_count))
                        ],
                    ]
                    break
        rng.shuffle(query_values)
        metadata["interval_min"] = int(interval_min)
        metadata["interval_max"] = int(interval_max)

        def _matches(value: int) -> bool:
            return int(interval_min) <= int(value) <= int(interval_max)

    query_values_by_row = {
        str(row_label): int(query_values[int(row_index)])
        for row_index, row_label in enumerate(row_labels)
    }
    values_by_row = _build_values_by_row(
        row_labels=row_labels,
        column_headers=column_headers,
        rng=rng,
        value_min=int(value_min),
        value_max=int(value_max),
        query_column=str(query_column),
        query_values_by_row=query_values_by_row,
    )
    matching_row_indices = [
        int(row_index)
        for row_index, row_label in enumerate(row_labels)
        if _matches(int(values_by_row[str(row_label)][str(query_column)]))
    ]
    matching_row_labels = [str(row_labels[int(row_index)]) for row_index in matching_row_indices]
    return {
        "row_count": int(row_count),
        "numeric_column_count": int(numeric_column_count),
        "row_count_range": list(base["row_count_range"]),
        "numeric_column_count_range": list(base["numeric_column_count_range"]),
        "value_range": list(base["value_range"]),
        "row_labels": [str(label) for label in row_labels],
        "column_headers": [str(header) for header in column_headers],
        "query_column": str(query_column),
        "values_by_row": dict(values_by_row),
        "answer_value": int(len(matching_row_indices)),
        "query_column_index": int(query_col_index),
        "matching_row_indices": [int(row_index) for row_index in matching_row_indices],
        "matching_row_labels": [str(label) for label in matching_row_labels],
        **metadata,
    }


def build_readout_cell_dataset(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: TableDefaults,
    task_id: str,
) -> Dict[str, Any]:
    """Construct one deterministic table dataset for exact cell-value lookup."""

    base = _resolve_base_table_schema(
        params=params,
        instance_seed=int(instance_seed),
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    rng = base["rng"]
    row_count = int(base["row_count"])
    numeric_column_count = int(base["numeric_column_count"])
    row_labels = list(base["row_labels"])
    column_headers = list(base["column_headers"])
    query_col_index = int(base["query_column_index"])
    query_column = str(base["query_column"])
    value_min = int(base["value_min"])
    value_max = int(base["value_max"])
    query_row_index = int(resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}:query_row",
    )) % int(row_count)
    query_row_label = str(row_labels[int(query_row_index)])
    answer_value = int(rng.randint(int(value_min), int(value_max)))

    values_by_row = _build_values_by_row(
        row_labels=row_labels,
        column_headers=column_headers,
        rng=rng,
        value_min=int(value_min),
        value_max=int(value_max),
    )
    values_by_row[str(query_row_label)][str(query_column)] = int(answer_value)
    return {
        "row_count": int(row_count),
        "numeric_column_count": int(numeric_column_count),
        "row_count_range": list(base["row_count_range"]),
        "numeric_column_count_range": list(base["numeric_column_count_range"]),
        "value_range": list(base["value_range"]),
        "row_labels": [str(label) for label in row_labels],
        "column_headers": [str(header) for header in column_headers],
        "query_row_label": str(query_row_label),
        "query_row_index": int(query_row_index),
        "query_column": str(query_column),
        "query_column_index": int(query_col_index),
        "values_by_row": dict(values_by_row),
        "answer_value": int(answer_value),
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


def projected_table_region_bbox_evidence(
    rendered_scene,
    *,
    row_labels: Sequence[str] = (),
    column_headers: Sequence[str] = (),
) -> Dict[str, Any]:
    """Project ordered row/column table regions into `bbox_set` evidence."""

    requested_rows = [str(row_label) for row_label in row_labels]
    requested_columns = [str(header) for header in column_headers]
    row_bbox_map = {
        str(row_label): [float(value) for value in bbox]
        for row_label, bbox in rendered_scene.row_region_bboxes.items()
    }
    column_bbox_map = {
        str(header): [float(value) for value in bbox]
        for header, bbox in rendered_scene.column_region_bboxes.items()
    }
    return {
        "bbox_set": [
            *[
                list(row_bbox_map[str(row_label)])
                for row_label in requested_rows
                if str(row_label) in row_bbox_map
            ],
            *[
                list(column_bbox_map[str(header)])
                for header in requested_columns
                if str(header) in column_bbox_map
            ],
        ]
    }


__all__ = [
    "SUPPORTED_TABLE_SCENE_VARIANTS",
    "TableDefaults",
    "build_counting_value_dataset_for_variant",
    "build_readout_cell_dataset",
    "build_row_summary_value_dataset_for_variant",
    "build_summary_label_dataset_for_variant",
    "build_summary_value_dataset_for_variant",
    "projected_table_bbox_evidence",
    "projected_table_region_bbox_evidence",
    "resolve_numeric_column_count_bounds",
    "resolve_row_count_bounds",
    "resolve_table_axis_variant",
    "resolve_table_render_params",
    "sample_numeric_column_headers",
    "sample_table_row_labels",
    "table_value_cell_id",
]
