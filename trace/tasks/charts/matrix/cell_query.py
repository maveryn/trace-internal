"""Annotated matrix-cell query tasks for chart-domain visual reasoning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.bbox_projection import round_bbox as _round_bbox
from ...shared.color_distance import coerce_rgb as _rgb
from ...shared.config_defaults import (
    required_group_defaults,
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.render_variation import apply_layout_jitter_to_margins, resolve_render_rgb
from ...shared.text_rendering import fit_font_to_box, load_font
from ..shared.complexity import (
    build_chart_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_chart_complexity_weights,
)
from ..shared.fixed_query_task import FixedChartQueryVariantTaskMixin, MergedChartQueryVariantTaskMixin
from ..shared.labeled_chart_common import resolve_chart_axis_variant
from ..shared.unanswerable import (
    UNANSWERABLE_ANSWER,
    absence_proof,
    choose_missing_label,
    should_use_unanswerable_branch,
)
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

_SHORT_LABELS: Tuple[str, ...] = tuple("ABCDEFGHIJKLMNPQRSTUVWXYZ")
_ROW_NAME_POOL: Tuple[str, ...] = (
    "Atlas",
    "Beacon",
    "Cedar",
    "Delta",
    "Ember",
    "Fjord",
    "Grove",
    "Harbor",
    "Iris",
    "Juno",
    "Kite",
    "Lumen",
)
_COL_NAME_POOL: Tuple[str, ...] = (
    "M1",
    "M2",
    "M3",
    "M4",
    "M5",
    "M6",
    "M7",
    "M8",
    "M9",
    "M10",
    "M11",
    "M12",
)
_MISSING_ROW_LABEL_POOL: Tuple[str, ...] = ("Ridge", "Tango", "Vale", "Zenith", "North", "South")
_MISSING_COLUMN_LABEL_POOL: Tuple[str, ...] = ("N1", "N2", "N3", "QX", "QY", "QZ")
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


def _label_list(prefix: str, count: int) -> List[str]:
    if str(prefix) == "letter":
        return [str(label) for label in _SHORT_LABELS[: int(count)]]
    return [f"{prefix}{index + 1}" for index in range(int(count))]


def _labels_for_scene(scene_variant: str, row_count: int, column_count: int) -> Tuple[List[str], List[str]]:
    if str(scene_variant) == "confusion_matrix_counts":
        labels = _label_list("C", int(row_count))
        return labels, list(labels)
    if str(scene_variant) == "annotated_heatmap_table":
        return list(_ROW_NAME_POOL[: int(row_count)]), list(_COL_NAME_POOL[: int(column_count)])
    if str(scene_variant) == "correlation_matrix_signed":
        labels = _label_list("V", int(row_count))
        return labels, list(labels)
    if str(scene_variant) == "triangular_pairwise_matrix":
        labels = _label_list("P", int(row_count))
        return labels, list(labels)
    row_labels = [f"G{(index // 3) + 1}-{(index % 3) + 1}" for index in range(int(row_count))]
    column_labels = [f"B{(index // 3) + 1}-{(index % 3) + 1}" for index in range(int(column_count))]
    return row_labels, column_labels


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


def _choose_axis_extremum(
    *,
    values: List[List[int | None]],
    row_labels: Sequence[str],
    column_labels: Sequence[str],
    query_axis: str,
    extremum_direction: str,
    instance_seed: int,
) -> Dict[str, Any]:
    target_rank = 2
    line_count = len(values) if str(query_axis) == "row" else len(values[0])
    candidates: List[Tuple[int, List[str], int]] = []
    for axis_index in range(int(line_count)):
        cell_ids = _line_cell_ids(values, query_axis=str(query_axis), axis_index=int(axis_index))
        if len(cell_ids) < int(target_rank):
            continue
        line_values = [int(values[int(cell_id.split("_c")[0][1:])][int(cell_id.split("_c")[1])]) for cell_id in cell_ids]
        ranked_distinct_values = sorted(
            {int(value) for value in line_values},
            reverse=str(extremum_direction) == "highest",
        )
        if len(ranked_distinct_values) < int(target_rank):
            continue
        target = int(ranked_distinct_values[int(target_rank) - 1])
        if line_values.count(int(target)) == 1:
            candidates.append((int(axis_index), list(cell_ids), int(target)))
    if not candidates:
        raise ValueError("could not find unique axis extremum candidate")
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.query.axis_extremum")
    axis_index, cell_ids, target_value = candidates[int(rng.randrange(len(candidates)))]
    winning_cell_id = [
        cell_id
        for cell_id in cell_ids
        if int(values[int(cell_id.split("_c")[0][1:])][int(cell_id.split("_c")[1])]) == int(target_value)
    ][0]
    row_index = int(winning_cell_id.split("_c")[0][1:])
    column_index = int(winning_cell_id.split("_c")[1])
    answer_value = str(column_labels[column_index] if str(query_axis) == "row" else row_labels[row_index])
    selected_header = _row_header_key(axis_index) if str(query_axis) == "row" else _column_header_key(axis_index)
    answer_header = _column_header_key(column_index) if str(query_axis) == "row" else _row_header_key(row_index)
    answer_axis = "column" if str(query_axis) == "row" else "row"
    axis_label = str(row_labels[axis_index] if str(query_axis) == "row" else column_labels[axis_index])
    return {
        "answer_value": answer_value,
        "answer_type": "string",
        "answer_row_index": row_index,
        "answer_column_index": column_index,
        "evidence_cell_ids": list(cell_ids),
        "evidence_header_keys": [selected_header, answer_header],
        "question_params": {
            "query_axis": str(query_axis),
            "axis_label": axis_label,
            "answer_axis": answer_axis,
            "extremum_rank": int(target_rank),
            "extremum_phrase": "second-highest printed value" if str(extremum_direction) == "highest" else "second-lowest printed value",
        },
        "extremum_rank": int(target_rank),
    }


def _choose_unanswerable_axis_extremum(
    *,
    row_labels: Sequence[str],
    column_labels: Sequence[str],
    query_axis: str,
    extremum_direction: str,
    instance_seed: int,
) -> Dict[str, Any]:
    if str(query_axis) == "row":
        missing_label = choose_missing_label(
            visible_labels=row_labels,
            candidate_labels=tuple(_ROW_NAME_POOL) + _MISSING_ROW_LABEL_POOL,
            fallback_prefix="Row ",
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.missing_row",
        )
        checked_scope = "matrix row labels"
        visible = [str(label) for label in row_labels]
        answer_axis = "column"
    else:
        missing_label = choose_missing_label(
            visible_labels=column_labels,
            candidate_labels=tuple(_COL_NAME_POOL) + _MISSING_COLUMN_LABEL_POOL,
            fallback_prefix="Column ",
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.missing_column",
        )
        checked_scope = "matrix column labels"
        visible = [str(label) for label in column_labels]
        answer_axis = "row"
    return {
        "answer_value": UNANSWERABLE_ANSWER,
        "answer_type": "string",
        "answer_row_index": -1,
        "answer_column_index": -1,
        "evidence_cell_ids": [],
        "evidence_header_keys": [],
        "question_params": {
            "query_axis": str(query_axis),
            "axis_label": str(missing_label),
            "answer_axis": str(answer_axis),
            "extremum_rank": 2,
            "extremum_phrase": "second-highest printed value" if str(extremum_direction) == "highest" else "second-lowest printed value",
        },
        "extremum_rank": 2,
        "is_unanswerable": True,
        "absence_proof": absence_proof(
            requested_item=str(missing_label),
            visible_candidates=visible,
            checked_scope=checked_scope,
            absence_reason=f"requested {str(query_axis)} label is not visible in the matrix",
        ),
    }


def _choose_off_diagonal_confusion(
    *,
    values: List[List[int | None]],
    row_labels: Sequence[str],
    column_labels: Sequence[str],
    instance_seed: int,
) -> Dict[str, Any]:
    row_count = len(values)
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.query.off_diagonal")
    row_index = int(rng.randrange(row_count))
    winning_columns = [index for index in range(row_count) if index != row_index]
    column_index = int(winning_columns[int(rng.randrange(len(winning_columns)))])
    other_values = [int(values[row_index][c] or 0) for c in range(row_count) if c != row_index and c != column_index]
    values[row_index][column_index] = int(max(other_values + [0]) + 3)
    cell_ids = [f"r{row_index}_c{c}" for c in range(row_count) if c != row_index]
    return {
        "answer_value": str(column_labels[column_index]),
        "answer_type": "string",
        "answer_row_index": row_index,
        "answer_column_index": column_index,
        "evidence_cell_ids": list(cell_ids),
        "evidence_header_keys": [_row_header_key(row_index), _column_header_key(column_index)],
        "question_params": {
            "row_label": str(row_labels[row_index]),
            "answer_axis": "predicted column",
        },
    }


def _threshold_options(values: Sequence[int], *, comparison: str) -> List[Tuple[int, int]]:
    if not values:
        return []
    options: List[Tuple[int, int]] = []
    for threshold in sorted(set(int(value) for value in values)):
        if str(comparison) == "at_least":
            count = sum(1 for value in values if int(value) >= int(threshold))
        else:
            count = sum(1 for value in values if int(value) <= int(threshold))
        if 2 <= int(count) <= max(2, min(9, len(values) - 1)):
            options.append((int(threshold), int(count)))
    return options


def _choose_threshold_count(
    *,
    values: List[List[int | None]],
    row_labels: Sequence[str],
    column_labels: Sequence[str],
    cells_by_id: Mapping[str, Dict[str, Any]],
    query_axis: str,
    comparison: str,
    instance_seed: int,
) -> Dict[str, Any]:
    line_count = len(values) if str(query_axis) == "row" else len(values[0])
    candidates: List[Tuple[int, int, int, List[str]]] = []
    for axis_index in range(int(line_count)):
        cell_ids = _line_cell_ids(values, query_axis=str(query_axis), axis_index=int(axis_index))
        line_values = [int(cells_by_id[cell_id]["value"]) for cell_id in cell_ids]
        for threshold, count in _threshold_options(line_values, comparison=str(comparison)):
            candidates.append((int(axis_index), int(threshold), int(count), list(cell_ids)))
    if not candidates:
        raise ValueError("could not find threshold-count candidate")
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.query.threshold_count")
    axis_index, threshold, count, cell_ids = candidates[int(rng.randrange(len(candidates)))]
    if str(comparison) == "at_least":
        matching = [cell_id for cell_id in cell_ids if int(cells_by_id[cell_id]["value"]) >= int(threshold)]
        comparison_phrase = f"at least {int(threshold)}"
    else:
        matching = [cell_id for cell_id in cell_ids if int(cells_by_id[cell_id]["value"]) <= int(threshold)]
        comparison_phrase = f"at most {int(threshold)}"
    selected_header = _row_header_key(axis_index) if str(query_axis) == "row" else _column_header_key(axis_index)
    row_index = int(cells_by_id[matching[0]]["row_index"])
    column_index = int(cells_by_id[matching[0]]["column_index"])
    axis_label = str(row_labels[axis_index] if str(query_axis) == "row" else column_labels[axis_index])
    return {
        "answer_value": int(count),
        "answer_type": "integer",
        "answer_row_index": row_index,
        "answer_column_index": column_index,
        "evidence_cell_ids": list(matching),
        "evidence_header_keys": [selected_header] + _header_keys_for_cells(matching, cells_by_id),
        "question_params": {
            "query_axis": str(query_axis),
            "axis_label": axis_label,
            "comparison_phrase": str(comparison_phrase),
            "threshold_value": int(threshold),
        },
    }


def _construct_dataset(
    *,
    query_id: str,
    scene_variant: str,
    query_axis: str,
    extremum_direction: str,
    comparison: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Dict[str, Any]:
    row_min, row_max = _matrix_size_support(params)
    col_min, col_max = _column_size_support(params)
    size_params = _decoupled_sampling_params(params, divisor=2, explicit_keys=("row_count_min", "row_count_max"))
    row_count = _balanced_int(
        tuple(range(int(row_min), int(row_max) + 1)),
        params=size_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.row_count",
    )
    if str(scene_variant) in {"confusion_matrix_counts", "correlation_matrix_signed", "triangular_pairwise_matrix"}:
        column_count = int(row_count)
    else:
        col_params = _decoupled_sampling_params(params, divisor=3, explicit_keys=("column_count_min", "column_count_max"))
        column_count = _balanced_int(
            tuple(range(int(col_min), int(col_max) + 1)),
            params=col_params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.column_count",
        )
    row_labels, column_labels = _labels_for_scene(str(scene_variant), int(row_count), int(column_count))
    values, scene_meta = _generate_values(
        scene_variant=str(scene_variant),
        row_count=int(row_count),
        column_count=int(column_count),
        instance_seed=int(instance_seed),
    )
    cells, cells_by_id = _cells_from_values(values, row_labels=row_labels, column_labels=column_labels)
    if str(query_id) == "axis_extremum_label" and should_use_unanswerable_branch(
        params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{query_id}",
        enabled=bool(params.get("_enable_unanswerable", False)),
    ):
        query = _choose_unanswerable_axis_extremum(
            row_labels=row_labels,
            column_labels=column_labels,
            query_axis=str(query_axis),
            extremum_direction=str(extremum_direction),
            instance_seed=int(instance_seed),
        )
    elif str(query_id) == "axis_extremum_label":
        query = _choose_axis_extremum(
            values=values,
            row_labels=row_labels,
            column_labels=column_labels,
            query_axis=str(query_axis),
            extremum_direction=str(extremum_direction),
            instance_seed=int(instance_seed),
        )
    elif str(query_id) == "off_diagonal_confusion_label":
        query = _choose_off_diagonal_confusion(
            values=values,
            row_labels=row_labels,
            column_labels=column_labels,
            instance_seed=int(instance_seed),
        )
        cells, cells_by_id = _cells_from_values(values, row_labels=row_labels, column_labels=column_labels)
    elif str(query_id) == "threshold_cell_count":
        query = _choose_threshold_count(
            values=values,
            row_labels=row_labels,
            column_labels=column_labels,
            cells_by_id=cells_by_id,
            query_axis=str(query_axis),
            comparison=str(comparison),
            instance_seed=int(instance_seed),
        )
    else:
        raise ValueError(f"unsupported query_id: {query_id}")
    # Recreate the ordered cell list after query-time highlighting or value edits.
    cells = [dict(cells_by_id[f"r{r}_c{c}"]) for r in range(int(row_count)) for c in range(int(column_count))]
    active_values = _active_values(values)
    scene_title_options = _SCENE_TITLES[str(scene_variant)]
    title_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.title")
    scene_title = str(scene_title_options[int(title_rng.randrange(len(scene_title_options)))])
    return {
        "scene_title": scene_title,
        "row_count": int(row_count),
        "column_count": int(column_count),
        "row_labels": list(row_labels),
        "column_labels": list(column_labels),
        "values": values,
        "cells": list(cells),
        "cells_by_id": {str(key): dict(value) for key, value in cells_by_id.items()},
        "value_min": int(min(active_values)),
        "value_max": int(max(active_values)),
        "scene_meta": dict(scene_meta),
        "query_axis": str(query_axis),
        "extremum_direction": str(extremum_direction),
        "comparison": str(comparison),
        "is_unanswerable": bool(query.get("is_unanswerable", False)),
        "absence_proof": dict(query.get("absence_proof", {})),
        **dict(query),
    }


def _text_bbox(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> Tuple[float, float]:
    bbox = draw.textbbox((0, 0), str(text), font=font)
    return float(bbox[2] - bbox[0]), float(bbox[3] - bbox[1])


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    *,
    box: Sequence[float],
    text: str,
    font: ImageFont.ImageFont,
    fill: Tuple[int, int, int],
    stroke_fill: Tuple[int, int, int] | None = None,
    stroke_width: int = 0,
) -> None:
    x1, y1, x2, y2 = [float(value) for value in box]
    width, height = _text_bbox(draw, str(text), font)
    xy = (float(x1 + ((x2 - x1 - width) / 2.0)), float(y1 + ((y2 - y1 - height) / 2.0) - 1.0))
    draw.text(
        xy,
        str(text),
        font=font,
        fill=fill,
        stroke_width=max(0, int(stroke_width)),
        stroke_fill=stroke_fill if stroke_fill is not None else fill,
    )


def _draw_rotated_text(
    image: Image.Image,
    *,
    box: Sequence[float],
    text: str,
    font: ImageFont.ImageFont,
    fill: Tuple[int, int, int],
) -> None:
    x1, y1, x2, y2 = [int(round(float(value))) for value in box]
    patch_w = max(1, int(x2 - x1))
    patch_h = max(1, int(y2 - y1))
    patch = Image.new("RGBA", (patch_h, patch_w), (255, 255, 255, 0))
    draw = ImageDraw.Draw(patch)
    width, height = _text_bbox(draw, str(text), font)
    draw.text(
        ((patch_h - width) / 2.0, (patch_w - height) / 2.0),
        str(text),
        font=font,
        fill=fill + (255,),
    )
    rotated = patch.rotate(90, expand=True)
    image.alpha_composite(rotated, (x1, y1))


def _render_matrix(
    background: Image.Image,
    *,
    scene_title: str,
    scene_variant: str,
    palette_variant: str,
    header_layout: str,
    grid_style: str,
    row_labels: Sequence[str],
    column_labels: Sequence[str],
    cells: Sequence[Mapping[str, Any]],
    value_min: int,
    value_max: int,
    scene_meta: Mapping[str, Any],
    render_params: _MatrixRenderParams,
) -> _RenderedMatrix:
    image = background.convert("RGBA")
    draw = ImageDraw.Draw(image)
    p = render_params
    offset_x = float(p.layout_offset_x_px)
    offset_y = float(p.layout_offset_y_px)
    panel_bbox = (
        float(p.outer_margin_px) + offset_x,
        float(p.outer_margin_px) + offset_y,
        float(p.canvas_width - p.outer_margin_px) + offset_x,
        float(p.canvas_height - p.outer_margin_px) + offset_y,
    )
    draw.rounded_rectangle(panel_bbox, radius=8, fill=p.panel_fill_rgb, outline=p.panel_border_rgb, width=2)
    title_bbox = (
        panel_bbox[0] + p.panel_padding_px,
        panel_bbox[1] + p.panel_padding_px,
        panel_bbox[2] - p.panel_padding_px,
        panel_bbox[1] + p.panel_padding_px + p.title_band_height_px,
    )
    title_font = load_font(p.title_font_size_px, bold=True)
    _draw_centered_text(draw, box=title_bbox, text=str(scene_title), font=title_font, fill=p.title_rgb)

    row_count = len(row_labels)
    column_count = len(column_labels)
    header_h = p.col_label_height_px
    label_w = p.row_label_width_px
    matrix_left = panel_bbox[0] + p.panel_padding_px + label_w
    matrix_top = title_bbox[3] + header_h
    matrix_right = panel_bbox[2] - p.panel_padding_px - (44 if str(header_layout) == "dual_headers" else 0)
    matrix_bottom = panel_bbox[3] - p.panel_padding_px - p.legend_height_px - (34 if str(header_layout) == "dual_headers" else 0)
    gap = p.cell_gap_px if str(grid_style) == "gapped_tiles" else 0
    cell_w = max(24.0, (float(matrix_right - matrix_left) - (float(gap) * (column_count - 1))) / float(column_count))
    cell_h = max(24.0, (float(matrix_bottom - matrix_top) - (float(gap) * (row_count - 1))) / float(row_count))
    matrix_width = (cell_w * column_count) + (gap * (column_count - 1))
    matrix_height = (cell_h * row_count) + (gap * (row_count - 1))
    matrix_bbox = (matrix_left, matrix_top, matrix_left + matrix_width, matrix_top + matrix_height)

    header_font = load_font(p.header_font_size_px, bold=True)
    cell_bbox_map: Dict[str, List[float]] = {}
    row_label_bbox_map: Dict[str, List[float]] = {}
    column_label_bbox_map: Dict[str, List[float]] = {}
    entities: List[Dict[str, Any]] = []

    row_axis_box = (panel_bbox[0] + 10, matrix_top, panel_bbox[0] + p.panel_padding_px + 24, matrix_bbox[3])
    col_axis_box = (matrix_left, title_bbox[3], matrix_bbox[2], title_bbox[3] + 28)
    axis_font = load_font(18, bold=True)
    _draw_centered_text(draw, box=col_axis_box, text=str(scene_meta.get("column_axis_title", "Column")), font=axis_font, fill=p.header_text_rgb)
    _draw_rotated_text(image, box=row_axis_box, text=str(scene_meta.get("row_axis_title", "Row")), font=axis_font, fill=p.header_text_rgb)

    for r, label in enumerate(row_labels):
        y1 = matrix_top + (r * (cell_h + gap))
        bbox = (panel_bbox[0] + p.panel_padding_px, y1, matrix_left - 8, y1 + cell_h)
        row_label_bbox_map[_row_header_key(r)] = _round_bbox(bbox)
        row_font = fit_font_to_box(draw, text=str(label), max_width=bbox[2] - bbox[0], max_height=bbox[3] - bbox[1], bold=True, max_size_px=p.header_font_size_px)
        _draw_centered_text(draw, box=bbox, text=str(label), font=row_font, fill=p.header_text_rgb)
        entities.append(
            {
                "entity_id": _row_header_key(r),
                "entity_type": "matrix_row_header",
                "label": str(label),
                "row_index": int(r),
                "bbox_px": _round_bbox(bbox),
            }
        )
        if str(header_layout) == "dual_headers":
            dup_bbox = (matrix_bbox[2] + 8, y1, panel_bbox[2] - p.panel_padding_px, y1 + cell_h)
            _draw_centered_text(draw, box=dup_bbox, text=str(label), font=row_font, fill=p.header_text_rgb)

    for c, label in enumerate(column_labels):
        x1 = matrix_left + (c * (cell_w + gap))
        bbox = (x1, title_bbox[3] + 28, x1 + cell_w, matrix_top - 6)
        column_label_bbox_map[_column_header_key(c)] = _round_bbox(bbox)
        col_font = fit_font_to_box(draw, text=str(label), max_width=bbox[2] - bbox[0], max_height=bbox[3] - bbox[1], bold=True, max_size_px=p.header_font_size_px)
        if str(header_layout) == "top_rotated_columns":
            _draw_rotated_text(image, box=bbox, text=str(label), font=col_font, fill=p.header_text_rgb)
        else:
            _draw_centered_text(draw, box=bbox, text=str(label), font=col_font, fill=p.header_text_rgb)
        entities.append(
            {
                "entity_id": _column_header_key(c),
                "entity_type": "matrix_column_header",
                "label": str(label),
                "column_index": int(c),
                "bbox_px": _round_bbox(bbox),
            }
        )
        if str(header_layout) == "dual_headers":
            dup_bbox = (x1, matrix_bbox[3] + 4, x1 + cell_w, matrix_bbox[3] + 32)
            _draw_centered_text(draw, box=dup_bbox, text=str(label), font=col_font, fill=p.header_text_rgb)

    cell_by_id = {str(cell["cell_id"]): dict(cell) for cell in cells}
    for r in range(row_count):
        for c in range(column_count):
            cell_id = f"r{r}_c{c}"
            cell = cell_by_id[cell_id]
            x1 = matrix_left + (c * (cell_w + gap))
            y1 = matrix_top + (r * (cell_h + gap))
            bbox = (x1, y1, x1 + cell_w, y1 + cell_h)
            cell_bbox_map[cell_id] = _round_bbox(bbox)
            active = bool(cell.get("active", False))
            if active:
                fill = _cell_fill_rgb(
                    value=int(cell["value"]),
                    value_min=int(value_min),
                    value_max=int(value_max),
                    palette_variant=str(palette_variant),
                    scene_variant=str(scene_variant),
                )
            else:
                fill = p.inactive_cell_rgb
            outline = p.grid_rgb if str(grid_style) != "minimal_grid" else fill
            draw.rectangle(bbox, fill=fill, outline=outline, width=max(0, int(p.cell_border_width_px)))
            if bool(cell.get("highlighted", False)):
                draw.rectangle(
                    (bbox[0] + 2, bbox[1] + 2, bbox[2] - 2, bbox[3] - 2),
                    outline=p.highlight_rgb,
                    width=5,
                )
            if active:
                text = str(cell.get("display_value", ""))
                cell_font = fit_font_to_box(
                    draw,
                    text=text,
                    max_width=float(cell_w),
                    max_height=float(cell_h),
                    bold=True,
                    min_size_px=9,
                    max_size_px=p.cell_font_size_px,
                    fill_ratio=0.72,
                )
                text_fill = _text_rgb_for_fill(fill)
                _draw_centered_text(
                    draw,
                    box=bbox,
                    text=text,
                    font=cell_font,
                    fill=text_fill,
                    stroke_fill=(255, 255, 255) if text_fill != (255, 255, 255) else (24, 30, 38),
                    stroke_width=1 if min(cell_w, cell_h) >= 42 else 0,
                )
            entities.append(
                {
                    "entity_id": cell_id,
                    "entity_type": "matrix_cell",
                    "row_index": int(r),
                    "column_index": int(c),
                    "row_label": str(row_labels[r]),
                    "column_label": str(column_labels[c]),
                    "value": None if cell.get("value") is None else int(cell["value"]),
                    "active": bool(active),
                    "highlighted": bool(cell.get("highlighted", False)),
                    "bbox_px": _round_bbox(bbox),
                }
            )

    if str(grid_style) == "heavy_block_lines":
        block_size = int(scene_meta.get("block_size", 3))
        for c in range(block_size, column_count, block_size):
            x = matrix_left + (c * (cell_w + gap)) - (gap / 2.0)
            draw.line((x, matrix_top, x, matrix_bbox[3]), fill=(38, 45, 55), width=4)
        for r in range(block_size, row_count, block_size):
            y = matrix_top + (r * (cell_h + gap)) - (gap / 2.0)
            draw.line((matrix_left, y, matrix_bbox[2], y), fill=(38, 45, 55), width=4)
    draw.rectangle(matrix_bbox, outline=p.panel_border_rgb, width=2)

    legend_bbox = (
        matrix_bbox[0],
        matrix_bbox[3] + 8,
        matrix_bbox[2],
        panel_bbox[3] - p.panel_padding_px,
    )
    legend_font = load_font(p.legend_font_size_px, bold=False)
    legend_text = "Cell color encodes the printed value; use the printed numbers as the source of truth."
    _draw_centered_text(draw, box=legend_bbox, text=legend_text, font=legend_font, fill=p.legend_text_rgb)
    return _RenderedMatrix(
        image=image.convert("RGB"),
        entities=tuple(entities),
        panel_bbox_px=_round_bbox(panel_bbox),
        title_bbox_px=_round_bbox(title_bbox),
        matrix_bbox_px=_round_bbox(matrix_bbox),
        legend_bbox_px=_round_bbox(legend_bbox),
        cell_bbox_map=dict(cell_bbox_map),
        row_label_bbox_map=dict(row_label_bbox_map),
        column_label_bbox_map=dict(column_label_bbox_map),
    )


def _json_examples(query_id: str, *, prompt_defaults: Mapping[str, Any]) -> Tuple[str, str]:
    return (
        str(prompt_defaults[f"json_example_{str(query_id)}"]),
        str(prompt_defaults[f"json_example_answer_only_{str(query_id)}"]),
    )


def _evidence_bboxes(
    *,
    rendered_scene: _RenderedMatrix,
    evidence_cell_ids: Sequence[str],
    evidence_header_keys: Sequence[str],
) -> Tuple[List[List[float]], List[Dict[str, Any]]]:
    bboxes: List[List[float]] = []
    entries: List[Dict[str, Any]] = []
    seen_headers: set[str] = set()
    for key in evidence_header_keys:
        header_key = str(key)
        if header_key in seen_headers:
            continue
        seen_headers.add(header_key)
        if header_key.startswith("row:"):
            bbox = list(rendered_scene.row_label_bbox_map[header_key])
            role = "row_header"
        else:
            bbox = list(rendered_scene.column_label_bbox_map[header_key])
            role = "column_header"
        bboxes.append(list(bbox))
        entries.append({"role": role, "id": header_key, "bbox": list(bbox)})
    for cell_id in evidence_cell_ids:
        bbox = list(rendered_scene.cell_bbox_map[str(cell_id)])
        bboxes.append(list(bbox))
        entries.append({"role": "cell", "id": str(cell_id), "bbox": list(bbox)})
    return bboxes, entries


class ChartsMatrixCellQueryTask:
    """Answer questions over printed values in annotated matrix charts."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "matrix"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                return self._generate_once(int(instance_seed) + int(attempt), params=params)
            except ValueError as exc:
                last_error = exc
                continue
        raise ValueError(f"could not construct unique-answer matrix task for {self.task_id}: {last_error}")

    def _generate_once(self, instance_seed: int, *, params: Dict[str, Any]) -> TaskOutput:
        query_id, query_id_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
        support_params = _support_sampling_params(params, query_id_probabilities=query_id_probabilities)
        scene_params = _decoupled_sampling_params(support_params, divisor=2, explicit_keys=("scene_variant", "scene_variant_weights"))
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(
            scene_params,
            query_id=str(query_id),
            instance_seed=int(instance_seed),
        )
        palette_params = _decoupled_sampling_params(support_params, divisor=3, explicit_keys=("palette_variant", "palette_variant_weights"))
        palette_variant, palette_variant_probabilities = _resolve_palette_variant(palette_params, instance_seed=int(instance_seed))
        header_params = _decoupled_sampling_params(support_params, divisor=5, explicit_keys=("header_layout", "header_layout_weights"))
        header_layout, header_layout_probabilities = _resolve_header_layout(header_params, instance_seed=int(instance_seed))
        grid_params = _decoupled_sampling_params(support_params, divisor=7, explicit_keys=("grid_style", "grid_style_weights"))
        grid_style, grid_style_probabilities = _resolve_grid_style(grid_params, instance_seed=int(instance_seed))

        query_axis = "row"
        query_axis_probabilities: Dict[str, float] = {}
        if str(query_id) in {"axis_extremum_label", "threshold_cell_count"}:
            axis_params = _decoupled_sampling_params(support_params, divisor=11, explicit_keys=("query_axis", "query_axis_weights"))
            query_axis, query_axis_probabilities = _resolve_query_axis(axis_params, instance_seed=int(instance_seed))
        extremum_direction = "highest"
        extremum_probabilities: Dict[str, float] = {}
        if str(query_id) == "axis_extremum_label":
            extremum_params = _decoupled_sampling_params(
                support_params,
                divisor=13,
                explicit_keys=("extremum_direction", "extremum_direction_weights"),
            )
            extremum_direction, extremum_probabilities = _resolve_extremum_direction(
                extremum_params,
                instance_seed=int(instance_seed),
            )
        comparison = "at_least"
        comparison_probabilities: Dict[str, float] = {}
        if str(query_id) == "threshold_cell_count":
            comparison_params = _decoupled_sampling_params(
                support_params,
                divisor=17,
                explicit_keys=("comparison", "comparison_weights"),
            )
            comparison, comparison_probabilities = _resolve_comparison(comparison_params, instance_seed=int(instance_seed))

        dataset_params = {**dict(support_params), "_enable_unanswerable": bool(getattr(self, "supports_unanswerable", False))}
        dataset = _construct_dataset(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            query_axis=str(query_axis),
            extremum_direction=str(extremum_direction),
            comparison=str(comparison),
            params=dataset_params,
            instance_seed=int(instance_seed),
        )
        render_style_params = {**dict(params), "_render_style_seed": int(instance_seed)}
        render_params = _resolve_render_params(render_style_params)
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered_scene = _render_matrix(
            background,
            scene_title=str(dataset["scene_title"]),
            scene_variant=str(scene_variant),
            palette_variant=str(palette_variant),
            header_layout=str(header_layout),
            grid_style=str(grid_style),
            row_labels=list(dataset["row_labels"]),
            column_labels=list(dataset["column_labels"]),
            cells=list(dataset["cells"]),
            value_min=int(dataset["value_min"]),
            value_max=int(dataset["value_max"]),
            scene_meta=dict(dataset["scene_meta"]),
            render_params=render_params,
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description_confusion_matrix_counts",
                "object_description_annotated_heatmap_table",
                "object_description_correlation_matrix_signed",
                "object_description_triangular_pairwise_matrix",
                "object_description_clustered_block_matrix",
                "answer_hint_integer",
                "answer_hint_label",
                "evidence_hint_axis_extremum_label",
                "evidence_hint_off_diagonal_confusion_label",
                "evidence_hint_threshold_cell_count",
                "json_example_axis_extremum_label",
                "json_example_off_diagonal_confusion_label",
                "json_example_threshold_cell_count",
                "json_example_answer_only_axis_extremum_label",
                "json_example_answer_only_off_diagonal_confusion_label",
                "json_example_answer_only_threshold_cell_count",
                "unanswerable_instruction",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _json_examples(str(query_id), prompt_defaults=prompt_defaults)
        qparams = dict(dataset["question_params"])
        answer_hint = (
            str(prompt_defaults["answer_hint_label"])
            if str(dataset["answer_type"]) == "string"
            else str(prompt_defaults["answer_hint_integer"])
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults[f"object_description_{str(scene_variant)}"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(query_id)}"]),
                "answer_hint": answer_hint,
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "row_label": str(qparams.get("row_label", "")),
                "column_label": str(qparams.get("column_label", "")),
                "query_axis": str(qparams.get("query_axis", "")),
                "axis_label": str(qparams.get("axis_label", "")),
                "answer_axis": str(qparams.get("answer_axis", "")),
                "extremum_phrase": str(qparams.get("extremum_phrase", "")),
                "selection_phrase": str(qparams.get("selection_phrase", "")),
                "comparison_phrase": str(qparams.get("comparison_phrase", "")),
                "threshold_value": str(qparams.get("threshold_value", "")),
                "unanswerable_instruction": (
                    str(prompt_defaults["unanswerable_instruction"])
                    if bool(getattr(self, "supports_unanswerable", False))
                    else ""
                ),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        evidence_cell_ids = [str(cell_id) for cell_id in dataset["evidence_cell_ids"]]
        evidence_header_keys = [str(key) for key in dataset["evidence_header_keys"]]
        evidence_bboxes, evidence_entries = _evidence_bboxes(
            rendered_scene=rendered_scene,
            evidence_cell_ids=evidence_cell_ids,
            evidence_header_keys=evidence_header_keys,
        )
        projected_evidence = {
            "bbox_set": list(evidence_bboxes),
            "entries": [dict(entry) for entry in evidence_entries],
            "cell_ids": list(evidence_cell_ids),
            "header_keys": list(evidence_header_keys),
        }
        answer_gt = TypedValue(type=str(dataset["answer_type"]), value=dataset["answer_value"])
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        cell_count = int(dataset["row_count"]) * int(dataset["column_count"])
        active_cell_count = len([cell for cell in dataset["cells"] if bool(cell["active"])])
        evidence_scan = normalize_int_with_bounds(len(evidence_bboxes), [3, 28])
        grid_scan = normalize_int_with_bounds(int(cell_count), [36, 144])
        reasoning_load = clamp_unit_interval(
            float(_REASONING_LOAD_BY_VARIANT[str(query_id)])
            + (0.10 * float(evidence_scan))
            + (0.08 * normalize_int_with_bounds(active_cell_count, [36, 144]))
        )
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": float(grid_scan),
                "reasoning_load": float(reasoning_load),
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(scene_variant)]),
            },
        )
        query_params = {
            "query_id": str(query_id),
            "scene_variant": str(scene_variant),
            "palette_variant": str(palette_variant),
            "header_layout": str(header_layout),
            "grid_style": str(grid_style),
            "query_id_probabilities": dict(query_id_probabilities),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "palette_variant_probabilities": dict(palette_variant_probabilities),
            "header_layout_probabilities": dict(header_layout_probabilities),
            "grid_style_probabilities": dict(grid_style_probabilities),
            "row_count": int(dataset["row_count"]),
            "column_count": int(dataset["column_count"]),
            "query_axis": str(query_axis),
            **dict(qparams),
        }
        if query_axis_probabilities:
            query_params["query_axis_probabilities"] = dict(query_axis_probabilities)
        if extremum_probabilities:
            query_params["extremum_direction_probabilities"] = dict(extremum_probabilities)
        if comparison_probabilities:
            query_params["comparison_probabilities"] = dict(comparison_probabilities)

        trace_payload = {
            "scene_ir": {
                "scene_kind": "chart_annotated_matrix",
                "entities": [dict(item) for item in rendered_scene.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "answer_value": dataset["answer_value"],
                    "answer_row_index": int(dataset["answer_row_index"]),
                    "answer_column_index": int(dataset["answer_column_index"]),
                    "evidence_cell_ids": list(evidence_cell_ids),
                    "evidence_header_keys": list(evidence_header_keys),
                    "answerability": "unanswerable" if bool(dataset["is_unanswerable"]) else "answerable",
                    **({"absence_proof": dict(dataset["absence_proof"])} if bool(dataset["is_unanswerable"]) else {}),
                },
            },
            "query_spec": {
                "query_id": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": dict(query_params),
            },
            "render_spec": {
                "scene_variant": str(scene_variant),
                "palette_variant": str(palette_variant),
                "header_layout": str(header_layout),
                "grid_style": str(grid_style),
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "row_count": int(dataset["row_count"]),
                "column_count": int(dataset["column_count"]),
                "value_min": int(dataset["value_min"]),
                "value_max": int(dataset["value_max"]),
                "layout_jitter": dict(render_params.layout_jitter_meta),
                "post_image_noise": dict(post_noise_meta),
            },
            "render_map": {
                "panel_bbox_px": list(rendered_scene.panel_bbox_px),
                "title_bbox_px": list(rendered_scene.title_bbox_px),
                "matrix_bbox_px": list(rendered_scene.matrix_bbox_px),
                "legend_bbox_px": list(rendered_scene.legend_bbox_px),
                "cell_bboxes_px": dict(rendered_scene.cell_bbox_map),
                "row_label_bboxes_px": dict(rendered_scene.row_label_bbox_map),
                "column_label_bboxes_px": dict(rendered_scene.column_label_bbox_map),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "question_format": "matrix_cell_query",
                "scene_title": str(dataset["scene_title"]),
                "row_count": int(dataset["row_count"]),
                "column_count": int(dataset["column_count"]),
                "row_labels": list(dataset["row_labels"]),
                "column_labels": list(dataset["column_labels"]),
                "values": [
                    [None if value is None else int(value) for value in row]
                    for row in dataset["values"]
                ],
                "cells": [dict(cell) for cell in dataset["cells"]],
                "cells_by_id": {str(key): dict(value) for key, value in dict(dataset["cells_by_id"]).items()},
                "answer_value": dataset["answer_value"],
                "answer_type": str(dataset["answer_type"]),
                "answer_row_index": int(dataset["answer_row_index"]),
                "answer_column_index": int(dataset["answer_column_index"]),
                "evidence_cell_ids": list(evidence_cell_ids),
                "evidence_header_keys": list(evidence_header_keys),
                "query_axis": str(query_axis),
                "extremum_direction": str(extremum_direction),
                "comparison": str(comparison),
                "extremum_rank": int(dataset.get("extremum_rank", 0)),
                "scene_meta": dict(dataset["scene_meta"]),
                "evidence_semantics": str(query_id),
                "answerability": "unanswerable" if bool(dataset["is_unanswerable"]) else "answerable",
                **({"absence_proof": dict(dataset["absence_proof"])} if bool(dataset["is_unanswerable"]) else {}),
            },
            "witness_symbolic": {
                "type": "matrix_cell_witness",
                "candidate_cell_ids": list(evidence_cell_ids),
                "header_keys": list(evidence_header_keys),
                "answer_value": dataset["answer_value"],
                "answer_row_index": int(dataset["answer_row_index"]),
                "answer_column_index": int(dataset["answer_column_index"]),
                "answerability": "unanswerable" if bool(dataset["is_unanswerable"]) else "answerable",
                **({"absence_proof": dict(dataset["absence_proof"])} if bool(dataset["is_unanswerable"]) else {}),
            },
            "projected_evidence": dict(projected_evidence),
            "background": background_meta,
            "post_image_noise": dict(post_noise_meta),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_id=str(query_id),
        )


@register_task
class ChartsMatrixAxisExtremumLabelTask(MergedChartQueryVariantTaskMixin, ChartsMatrixCellQueryTask):
    """Return a matrix row/column label from extremum-style cell queries."""

    task_id = "task_charts__matrix__axis_extremum_label"
    allowed_query_ids = ("axis_extremum_label", "off_diagonal_confusion_label")
    supports_unanswerable = True


@register_task
class ChartsMatrixThresholdCellCountTask(FixedChartQueryVariantTaskMixin, ChartsMatrixCellQueryTask):
    """Count matrix cells satisfying a threshold condition."""

    task_id = "task_charts__matrix__threshold_cell_count"
    fixed_query_id = "threshold_cell_count"


__all__ = [
    "ChartsMatrixAxisExtremumLabelTask",
    "ChartsMatrixCellQueryTask",
    "ChartsMatrixThresholdCellCountTask",
    "SUPPORTED_SCENE_VARIANTS",
    "SUPPORTED_QUERY_IDS",
]
