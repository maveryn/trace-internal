"""Shared constants, defaults, and helpers for matrix chart tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ...shared.config_defaults import (
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.font_assets import sample_font_family
from ...shared.render_variation import apply_layout_jitter_to_margins, resolve_render_rgb
from ..shared.complexity import resolve_chart_complexity_weights
from ..shared.label_assets import resolve_chart_entity_labels
from ..shared.labeled_chart_common import resolve_chart_axis_variant
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults


TASK_ID = "charts_matrix_cell_query_base"
_SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "axis_extremum_label",
    "off_diagonal_confusion_label",
    "threshold_cell_count",
)
_SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "confusion_matrix_counts",
    "annotated_heatmap_table",
    "correlation_matrix_signed",
    "triangular_pairwise_matrix",
    "clustered_block_matrix",
)
_SUPPORTED_PALETTE_VARIANTS: Tuple[str, ...] = (
    "blue_sequential",
    "viridis",
    "yellow_purple",
    "red_blue_diverging",
    "gray_print",
    "high_contrast",
)
_SUPPORTED_HEADER_LAYOUTS: Tuple[str, ...] = (
    "top_rotated_columns",
    "top_horizontal_columns",
    "dual_headers",
)
_SUPPORTED_GRID_STYLES: Tuple[str, ...] = (
    "thin_grid",
    "gapped_tiles",
    "heavy_block_lines",
    "minimal_grid",
)
_SUPPORTED_QUERY_AXES: Tuple[str, ...] = ("row", "column")
_SUPPORTED_EXTREMUM_DIRECTIONS: Tuple[str, ...] = ("highest", "lowest")
_SUPPORTED_COMPARISONS: Tuple[str, ...] = ("at_least", "at_most")

SUPPORTED_QUERY_IDS = _SUPPORTED_QUERY_IDS
SUPPORTED_SCENE_VARIANTS = _SUPPORTED_SCENE_VARIANTS

_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "matrix")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="matrix")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="matrix", apply_prob=0.0)

_SCENE_LOAD_BY_VARIANT: Dict[str, float] = {
    "confusion_matrix_counts": 0.60,
    "annotated_heatmap_table": 0.50,
    "correlation_matrix_signed": 0.70,
    "triangular_pairwise_matrix": 0.68,
    "clustered_block_matrix": 0.76,
}
_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    "axis_extremum_label": 0.74,
    "off_diagonal_confusion_label": 0.74,
    "threshold_cell_count": 0.62,
}

_SCENE_TITLES: Dict[str, Tuple[str, ...]] = {
    "confusion_matrix_counts": ("Model Confusion Matrix", "Actual vs Predicted Counts"),
    "annotated_heatmap_table": ("Annotated Metric Matrix", "Category Score Matrix"),
    "correlation_matrix_signed": ("Signed Association Matrix", "Pairwise Effect Matrix"),
    "triangular_pairwise_matrix": ("Pairwise Distance Matrix", "Lower-Triangle Comparison Matrix"),
    "clustered_block_matrix": ("Clustered Block Matrix", "Grouped Response Matrix"),
}

BBox = Tuple[float, float, float, float]


@dataclass(frozen=True)
class _MatrixRenderParams:
    canvas_width: int
    canvas_height: int
    outer_margin_px: int
    panel_padding_px: int
    title_band_height_px: int
    legend_height_px: int
    row_label_width_px: int
    col_label_height_px: int
    cell_gap_px: int
    cell_border_width_px: int
    title_font_size_px: int
    header_font_size_px: int
    cell_font_size_px: int
    legend_font_size_px: int
    panel_fill_rgb: Tuple[int, int, int]
    panel_border_rgb: Tuple[int, int, int]
    title_rgb: Tuple[int, int, int]
    header_text_rgb: Tuple[int, int, int]
    grid_rgb: Tuple[int, int, int]
    inactive_cell_rgb: Tuple[int, int, int]
    highlight_rgb: Tuple[int, int, int]
    legend_text_rgb: Tuple[int, int, int]
    layout_offset_x_px: int
    layout_offset_y_px: int
    layout_jitter_meta: Dict[str, Any]
    font_family: str


@dataclass(frozen=True)
class _RenderedMatrix:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    panel_bbox_px: List[float]
    title_bbox_px: List[float]
    matrix_bbox_px: List[float]
    legend_bbox_px: List[float]
    cell_bbox_map: Dict[str, List[float]]
    row_label_bbox_map: Dict[str, List[float]]
    column_label_bbox_map: Dict[str, List[float]]


def _render_style_seed(params: Mapping[str, Any]) -> int:
    try:
        return int(params.get("_render_style_seed", params.get("_sample_cursor", 0)) or 0)
    except Exception:
        return 0


def _rgb_param(params: Mapping[str, Any], key: str, fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
    return resolve_render_rgb(
        params,
        _RENDER_DEFAULTS,
        str(key),
        fallback,
        instance_seed=_render_style_seed(params),
        namespace=TASK_ID,
    )


def _int_param(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), _RENDER_DEFAULTS.get(str(key), int(fallback))))


def _resolve_render_params(params: Mapping[str, Any]) -> _MatrixRenderParams:
    outer = _int_param(params, "outer_margin_px", 44)
    jitter_left, _jitter_right, jitter_top, _jitter_bottom, layout_jitter_meta = apply_layout_jitter_to_margins(
        left_px=int(outer),
        right_px=int(outer),
        top_px=int(outer),
        bottom_px=int(outer),
        params=params,
        defaults=_RENDER_DEFAULTS,
        instance_seed=_render_style_seed(params),
        namespace=f"{TASK_ID}.layout",
    )
    return _MatrixRenderParams(
        canvas_width=_int_param(params, "canvas_width", 1500),
        canvas_height=_int_param(params, "canvas_height", 1050),
        outer_margin_px=int(outer),
        panel_padding_px=_int_param(params, "panel_padding_px", 30),
        title_band_height_px=_int_param(params, "title_band_height_px", 66),
        legend_height_px=_int_param(params, "legend_height_px", 62),
        row_label_width_px=_int_param(params, "row_label_width_px", 178),
        col_label_height_px=_int_param(params, "col_label_height_px", 98),
        cell_gap_px=_int_param(params, "cell_gap_px", 2),
        cell_border_width_px=_int_param(params, "cell_border_width_px", 1),
        title_font_size_px=_int_param(params, "title_font_size_px", 32),
        header_font_size_px=_int_param(params, "header_font_size_px", 20),
        cell_font_size_px=_int_param(params, "cell_font_size_px", 22),
        legend_font_size_px=_int_param(params, "legend_font_size_px", 18),
        panel_fill_rgb=_rgb_param(params, "panel_fill_rgb", (252, 253, 252)),
        panel_border_rgb=_rgb_param(params, "panel_border_rgb", (56, 64, 74)),
        title_rgb=_rgb_param(params, "title_rgb", (28, 34, 44)),
        header_text_rgb=_rgb_param(params, "header_text_rgb", (32, 40, 50)),
        grid_rgb=_rgb_param(params, "grid_rgb", (86, 94, 106)),
        inactive_cell_rgb=_rgb_param(params, "inactive_cell_rgb", (245, 246, 248)),
        highlight_rgb=_rgb_param(params, "highlight_rgb", (236, 180, 34)),
        legend_text_rgb=_rgb_param(params, "legend_text_rgb", (36, 44, 54)),
        layout_offset_x_px=int(jitter_left) - int(outer),
        layout_offset_y_px=int(jitter_top) - int(outer),
        layout_jitter_meta=dict(layout_jitter_meta),
        font_family=sample_font_family(
            role="readout",
            instance_seed=_render_style_seed(params),
            namespace=f"{TASK_ID}.chart_font",
            params=params,
            exclude_tags=("display",),
            explicit_key="chart_font_family",
            weights_key="chart_font_family_weights",
        ),
    )


def _uses_uniform_query_id_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> bool:
    if params.get("query_id") is not None or params.get("query_id_weights") is not None:
        return False
    enabled = bool(params.get("balanced_query_id_sampling", _GEN_DEFAULTS.get("balanced_query_id_sampling", True)))
    if not enabled:
        return False
    positives = [float(value) for value in query_id_probabilities.values() if float(value) > 0.0]
    if len(positives) != len(_SUPPORTED_QUERY_IDS):
        return False
    return max(positives) - min(positives) <= 1e-9


def _support_sampling_params(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    support_params = dict(params)
    sampling_index = support_params.get("_sample_cursor")
    if sampling_index is None:
        return support_params
    if not _uses_uniform_query_id_cycle(params, query_id_probabilities=query_id_probabilities):
        return support_params
    support_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(_SUPPORTED_QUERY_IDS))
    return support_params


def _decoupled_sampling_params(params: Mapping[str, Any], *, divisor: int, explicit_keys: Sequence[str]) -> Dict[str, Any]:
    resolved = dict(params)
    sampling_index = resolved.get("_sample_cursor")
    if sampling_index is None or any(resolved.get(str(key)) is not None for key in explicit_keys):
        return resolved
    resolved["_sample_cursor"] = abs(int(sampling_index)) // max(1, int(divisor))
    return resolved


def _balanced_int(
    support: Sequence[int],
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> int:
    ordered = [int(value) for value in support]
    if not ordered:
        raise ValueError(f"empty support for {namespace}")
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    return int(ordered[int(index) % len(ordered)])


def _resolve_axis_variant(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    supported_variants: Sequence[str],
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    axis_namespace: str,
) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=supported_variants,
        task_id=TASK_ID,
        explicit_key=explicit_key,
        weights_key=weights_key,
        balance_flag_key=balance_flag_key,
        axis_namespace=axis_namespace,
    )


def _resolve_query_id(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return _resolve_axis_variant(
        params,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_QUERY_IDS,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )


def _compatible_scene_variants(query_id: str) -> Tuple[str, ...]:
    if str(query_id) == "off_diagonal_confusion_label":
        return ("confusion_matrix_counts",)
    return _SUPPORTED_SCENE_VARIANTS


def _resolve_scene_variant(
    params: Mapping[str, Any],
    *,
    query_id: str,
    instance_seed: int,
) -> Tuple[str, Dict[str, float]]:
    supported = _compatible_scene_variants(str(query_id))
    return _resolve_axis_variant(
        params,
        instance_seed=int(instance_seed),
        supported_variants=supported,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def _resolve_palette_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return _resolve_axis_variant(
        params,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_PALETTE_VARIANTS,
        explicit_key="palette_variant",
        weights_key="palette_variant_weights",
        balance_flag_key="balanced_palette_variant_sampling",
        axis_namespace="palette_variant",
    )


def _resolve_header_layout(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return _resolve_axis_variant(
        params,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_HEADER_LAYOUTS,
        explicit_key="header_layout",
        weights_key="header_layout_weights",
        balance_flag_key="balanced_header_layout_sampling",
        axis_namespace="header_layout",
    )


def _resolve_grid_style(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return _resolve_axis_variant(
        params,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_GRID_STYLES,
        explicit_key="grid_style",
        weights_key="grid_style_weights",
        balance_flag_key="balanced_grid_style_sampling",
        axis_namespace="grid_style",
    )


def _resolve_query_axis(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return _resolve_axis_variant(
        params,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_QUERY_AXES,
        explicit_key="query_axis",
        weights_key="query_axis_weights",
        balance_flag_key="balanced_query_axis_sampling",
        axis_namespace="query_axis",
    )


def _resolve_extremum_direction(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return _resolve_axis_variant(
        params,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_EXTREMUM_DIRECTIONS,
        explicit_key="extremum_direction",
        weights_key="extremum_direction_weights",
        balance_flag_key="balanced_extremum_direction_sampling",
        axis_namespace="extremum_direction",
    )


def _resolve_comparison(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return _resolve_axis_variant(
        params,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_COMPARISONS,
        explicit_key="comparison",
        weights_key="comparison_weights",
        balance_flag_key="balanced_comparison_sampling",
        axis_namespace="comparison",
    )


def _matrix_size_support(params: Mapping[str, Any]) -> Tuple[int, int]:
    row_min, row_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="row_count_min",
        max_key="row_count_max",
        fallback_min=6,
        fallback_max=12,
        context=f"generation defaults for {TASK_ID}",
    )
    row_min = max(6, int(row_min))
    row_max = min(12, int(row_max))
    if row_min > row_max:
        raise ValueError("matrix row_count support must overlap 6..12")
    return int(row_min), int(row_max)


def _column_size_support(params: Mapping[str, Any]) -> Tuple[int, int]:
    col_min, col_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="column_count_min",
        max_key="column_count_max",
        fallback_min=6,
        fallback_max=12,
        context=f"generation defaults for {TASK_ID}",
    )
    col_min = max(6, int(col_min))
    col_max = min(12, int(col_max))
    if col_min > col_max:
        raise ValueError("matrix column_count support must overlap 6..12")
    return int(col_min), int(col_max)


def _sample_matrix_labels(*, count: int, instance_seed: int, namespace: str) -> List[str]:
    labels = resolve_chart_entity_labels(
        spawn_rng(int(instance_seed), f"{TASK_ID}.{namespace}.labels"),
        count=int(count),
        min_chars=2,
        max_chars=7,
        allow_spaces=False,
    ).labels
    return [str(label) for label in labels]


def _labels_for_scene(scene_variant: str, row_count: int, column_count: int, *, instance_seed: int) -> Tuple[List[str], List[str]]:
    if str(scene_variant) == "confusion_matrix_counts":
        labels = _sample_matrix_labels(count=int(row_count), instance_seed=int(instance_seed), namespace="confusion")
        return labels, list(labels)
    if str(scene_variant) == "annotated_heatmap_table":
        labels = _sample_matrix_labels(
            count=int(row_count) + int(column_count),
            instance_seed=int(instance_seed),
            namespace="annotated_heatmap",
        )
        return list(labels[: int(row_count)]), list(labels[int(row_count) : int(row_count) + int(column_count)])
    if str(scene_variant) == "correlation_matrix_signed":
        labels = _sample_matrix_labels(count=int(row_count), instance_seed=int(instance_seed), namespace="correlation")
        return labels, list(labels)
    if str(scene_variant) == "triangular_pairwise_matrix":
        labels = _sample_matrix_labels(count=int(row_count), instance_seed=int(instance_seed), namespace="triangular")
        return labels, list(labels)
    labels = _sample_matrix_labels(
        count=int(row_count) + int(column_count),
        instance_seed=int(instance_seed),
        namespace="clustered_block",
    )
    return list(labels[: int(row_count)]), list(labels[int(row_count) : int(row_count) + int(column_count)])


def _interpolate_rgb(a: Tuple[int, int, int], b: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    t_clamped = max(0.0, min(1.0, float(t)))
    return tuple(int(round(float(a[index]) + ((float(b[index]) - float(a[index])) * t_clamped))) for index in range(3))


def _cell_fill_rgb(
    *,
    value: int,
    value_min: int,
    value_max: int,
    palette_variant: str,
    scene_variant: str,
) -> Tuple[int, int, int]:
    if int(value_max) == int(value_min):
        t = 0.5
    else:
        t = (float(value) - float(value_min)) / float(int(value_max) - int(value_min))
    t = max(0.0, min(1.0, float(t)))
    if str(palette_variant) == "gray_print":
        return _interpolate_rgb((246, 246, 246), (74, 74, 74), t)
    if str(palette_variant) == "yellow_purple":
        return _interpolate_rgb((255, 247, 188), (94, 60, 153), t)
    if str(palette_variant) == "viridis":
        if t < 0.5:
            return _interpolate_rgb((68, 1, 84), (35, 144, 140), t * 2.0)
        return _interpolate_rgb((35, 144, 140), (253, 231, 37), (t - 0.5) * 2.0)
    if str(palette_variant) == "red_blue_diverging" or str(scene_variant) == "correlation_matrix_signed":
        if int(value) < 0:
            local_t = 1.0 - (abs(float(value)) / max(1.0, abs(float(value_min))))
            return _interpolate_rgb((50, 104, 173), (245, 245, 245), local_t)
        local_t = float(value) / max(1.0, abs(float(value_max)))
        return _interpolate_rgb((245, 245, 245), (202, 72, 58), local_t)
    if str(palette_variant) == "high_contrast":
        return _interpolate_rgb((232, 245, 233), (0, 104, 120), t)
    return _interpolate_rgb((239, 246, 255), (37, 99, 184), t)


def _text_rgb_for_fill(fill: Tuple[int, int, int]) -> Tuple[int, int, int]:
    luminance = ((0.2126 * fill[0]) + (0.7152 * fill[1]) + (0.0722 * fill[2])) / 255.0
    return (255, 255, 255) if luminance < 0.43 else (24, 30, 38)


def _active_values(values: Sequence[Sequence[int | None]]) -> List[int]:
    resolved: List[int] = []
    for row in values:
        for value in row:
            if value is not None:
                resolved.append(int(value))
    return resolved


def _generate_values(
    *,
    scene_variant: str,
    row_count: int,
    column_count: int,
    instance_seed: int,
) -> Tuple[List[List[int | None]], Dict[str, Any]]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.values.{scene_variant}")
    values: List[List[int | None]] = [[None for _ in range(int(column_count))] for _ in range(int(row_count))]
    meta: Dict[str, Any] = {}
    if str(scene_variant) == "confusion_matrix_counts":
        for r in range(int(row_count)):
            for c in range(int(column_count)):
                values[r][c] = int(rng.randint(0, 12))
            values[r][r] = int(rng.randint(28, 88))
        meta["row_axis_title"] = "Actual"
        meta["column_axis_title"] = "Predicted"
        return values, meta
    if str(scene_variant) == "correlation_matrix_signed":
        for r in range(int(row_count)):
            for c in range(r, int(column_count)):
                if r == c:
                    value = 0
                else:
                    value = int(rng.choice([v for v in range(-9, 10) if v != 0]))
                values[r][c] = value
                values[c][r] = value
        meta["row_axis_title"] = "Variable"
        meta["column_axis_title"] = "Variable"
        return values, meta
    if str(scene_variant) == "triangular_pairwise_matrix":
        orientation = "lower" if int(rng.randint(0, 1)) == 0 else "upper"
        for r in range(int(row_count)):
            for c in range(int(column_count)):
                active = (r > c) if orientation == "lower" else (c > r)
                values[r][c] = int(rng.randint(1, 90)) if active else None
        meta["triangle_orientation"] = orientation
        meta["row_axis_title"] = "Item"
        meta["column_axis_title"] = "Item"
        return values, meta
    if str(scene_variant) == "clustered_block_matrix":
        for r in range(int(row_count)):
            for c in range(int(column_count)):
                same_block = (r // 3) == (c // 3)
                values[r][c] = int(rng.randint(35, 95) if same_block else rng.randint(0, 45))
        meta["row_axis_title"] = "Cluster row"
        meta["column_axis_title"] = "Cluster column"
        meta["block_size"] = 3
        return values, meta
    for r in range(int(row_count)):
        for c in range(int(column_count)):
            values[r][c] = int(rng.randint(0, 99))
    meta["row_axis_title"] = "Category"
    meta["column_axis_title"] = "Metric"
    return values, meta


def _cells_from_values(
    values: Sequence[Sequence[int | None]],
    *,
    row_labels: Sequence[str],
    column_labels: Sequence[str],
) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    cells: List[Dict[str, Any]] = []
    cells_by_id: Dict[str, Dict[str, Any]] = {}
    for r, row in enumerate(values):
        for c, value in enumerate(row):
            cell_id = f"r{r}_c{c}"
            cell = {
                "cell_id": cell_id,
                "row_index": int(r),
                "column_index": int(c),
                "row_label": str(row_labels[r]),
                "column_label": str(column_labels[c]),
                "value": None if value is None else int(value),
                "display_value": "" if value is None else str(int(value)),
                "active": value is not None,
                "highlighted": False,
            }
            cells.append(cell)
            cells_by_id[cell_id] = cell
    return cells, cells_by_id


def _line_cell_ids(values: Sequence[Sequence[int | None]], *, query_axis: str, axis_index: int) -> List[str]:
    if str(query_axis) == "row":
        return [f"r{int(axis_index)}_c{c}" for c, value in enumerate(values[int(axis_index)]) if value is not None]
    return [f"r{r}_c{int(axis_index)}" for r, row in enumerate(values) if row[int(axis_index)] is not None]


def _axis_label(labels: Sequence[str], index: int) -> str:
    return str(labels[int(index)])


def _row_header_key(index: int) -> str:
    return f"row:{int(index)}"


def _column_header_key(index: int) -> str:
    return f"column:{int(index)}"


def _header_keys_for_cells(cell_ids: Sequence[str], cells_by_id: Mapping[str, Mapping[str, Any]]) -> List[str]:
    row_indices = sorted({int(cells_by_id[str(cell_id)]["row_index"]) for cell_id in cell_ids})
    col_indices = sorted({int(cells_by_id[str(cell_id)]["column_index"]) for cell_id in cell_ids})
    return [_row_header_key(index) for index in row_indices] + [_column_header_key(index) for index in col_indices]
