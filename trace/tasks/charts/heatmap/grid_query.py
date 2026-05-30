"""Heatmap grid query tasks for chart-domain visual reasoning."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.bbox_projection import bbox_union_raw as _bbox_union, round_bbox as _round_bbox
from ...shared.color_distance import coerce_rgb as _rgb
from ...shared.config_defaults import (
    group_default,
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
from ...shared.font_assets import font_asset_version, sample_font_family
from ...shared.render_variation import apply_layout_jitter_to_margins, resolve_render_rgb
from ...shared.text_rendering import fit_font_to_box, load_font
from ...shared.text_legibility import draw_text_traced
from ..shared.complexity import (
    build_chart_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_chart_complexity_weights,
)
from ..shared.fixed_query_task import FixedChartQueryVariantTaskMixin
from ..shared.label_assets import resolve_chart_entity_labels
from ..shared.labeled_chart_common import resolve_chart_axis_variant
from ..shared.unanswerable import (
    UNANSWERABLE_ANSWER,
    absence_proof,
    choose_missing_label,
    should_use_unanswerable_branch,
)
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults


TASK_ID = "charts_heatmap_query_base"
_SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "axis_condition_extremum_label",
    "axis_cell_extremum_label",
    "condition_run_extremum_label",
)
_SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "intensity_heatmap",
    "signed_change_heatmap",
    "calendar_heatmap",
)
_SUPPORTED_EXTREMUM_DIRECTIONS: Tuple[str, ...] = ("hottest", "coolest")
_SUPPORTED_QUERY_AXES: Tuple[str, ...] = ("row", "column")
_INTENSITY_CONDITIONS: Tuple[str, ...] = ("hot", "cool")
_SIGNED_CONDITIONS: Tuple[str, ...] = ("increase", "decrease")
SUPPORTED_QUERY_IDS = _SUPPORTED_QUERY_IDS
SUPPORTED_SCENE_VARIANTS = _SUPPORTED_SCENE_VARIANTS

_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "heatmap")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="heatmap")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="heatmap", apply_prob=0.0)

_MISSING_CONDITION_PHRASES: Tuple[str, ...] = (
    "purple-coded",
    "black-striped",
    "teal-outlined",
    "orange-dotted",
)
_WEEKDAY_LABELS: Tuple[str, ...] = ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")
_TITLE_OPTIONS: Tuple[str, ...] = (
    "Activity Heatmap",
    "Change Intensity Grid",
    "Category Heat Matrix",
    "Weekly Signal Heatmap",
    "Response Pattern Grid",
)
_INTENSITY_PALETTE: Tuple[Tuple[int, int, int], ...] = (
    (247, 252, 245),
    (199, 233, 192),
    (116, 196, 118),
    (49, 163, 84),
    (0, 109, 44),
)
_SIGNED_PALETTE: Tuple[Tuple[int, int, int], ...] = (
    (49, 117, 182),
    (171, 217, 233),
    (244, 244, 244),
    (253, 174, 97),
    (215, 48, 39),
)
_CALENDAR_PALETTE: Tuple[Tuple[int, int, int], ...] = (
    (246, 245, 252),
    (218, 218, 235),
    (188, 189, 220),
    (128, 125, 186),
    (84, 39, 143),
)
_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    "axis_condition_extremum_label": 0.70,
    "axis_cell_extremum_label": 0.60,
    "condition_run_extremum_label": 0.82,
}
_SCENE_LOAD_BY_VARIANT: Dict[str, float] = {
    "intensity_heatmap": 0.44,
    "signed_change_heatmap": 0.56,
    "calendar_heatmap": 0.50,
}


BBox = Tuple[float, float, float, float]


@dataclass(frozen=True)
class _HeatmapRenderParams:
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
    axis_font_size_px: int
    legend_font_size_px: int
    panel_fill_rgb: Tuple[int, int, int]
    panel_border_rgb: Tuple[int, int, int]
    title_rgb: Tuple[int, int, int]
    axis_text_rgb: Tuple[int, int, int]
    grid_border_rgb: Tuple[int, int, int]
    cell_border_rgb: Tuple[int, int, int]
    legend_text_rgb: Tuple[int, int, int]
    layout_offset_x_px: int
    layout_offset_y_px: int
    layout_jitter_meta: Dict[str, Any]
    font_family: str


@dataclass(frozen=True)
class _RenderedHeatmap:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    panel_bbox_px: List[float]
    title_bbox_px: List[float]
    grid_bbox_px: List[float]
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


def _resolve_render_params(params: Mapping[str, Any]) -> _HeatmapRenderParams:
    outer = _int_param(params, "outer_margin_px", 42)
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
    return _HeatmapRenderParams(
        canvas_width=_int_param(params, "canvas_width", 1260),
        canvas_height=_int_param(params, "canvas_height", 820),
        outer_margin_px=int(outer),
        panel_padding_px=_int_param(params, "panel_padding_px", 28),
        title_band_height_px=_int_param(params, "title_band_height_px", 68),
        legend_height_px=_int_param(params, "legend_height_px", 72),
        row_label_width_px=_int_param(params, "row_label_width_px", 150),
        col_label_height_px=_int_param(params, "col_label_height_px", 46),
        cell_gap_px=_int_param(params, "cell_gap_px", 4),
        cell_border_width_px=_int_param(params, "cell_border_width_px", 2),
        title_font_size_px=_int_param(params, "title_font_size_px", 30),
        axis_font_size_px=_int_param(params, "axis_font_size_px", 20),
        legend_font_size_px=_int_param(params, "legend_font_size_px", 18),
        panel_fill_rgb=_rgb_param(params, "panel_fill_rgb", (252, 253, 251)),
        panel_border_rgb=_rgb_param(params, "panel_border_rgb", (64, 74, 86)),
        title_rgb=_rgb_param(params, "title_rgb", (30, 38, 48)),
        axis_text_rgb=_rgb_param(params, "axis_text_rgb", (36, 44, 54)),
        grid_border_rgb=_rgb_param(params, "grid_border_rgb", (80, 92, 104)),
        cell_border_rgb=_rgb_param(params, "cell_border_rgb", (255, 255, 255)),
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


def _resolve_query_id(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_QUERY_IDS,
        task_id=TASK_ID,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )


def _resolve_scene_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_SCENE_VARIANTS,
        task_id=TASK_ID,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def _condition_support(scene_variant: str) -> Tuple[str, ...]:
    if str(scene_variant) == "signed_change_heatmap":
        return _SIGNED_CONDITIONS
    return _INTENSITY_CONDITIONS


def _resolve_condition_kind(
    params: Mapping[str, Any],
    *,
    scene_variant: str,
    instance_seed: int,
) -> Tuple[str, Dict[str, float]]:
    support = _condition_support(str(scene_variant))
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=support,
        task_id=TASK_ID,
        explicit_key="condition_kind",
        weights_key="condition_kind_weights",
        balance_flag_key="balanced_condition_kind_sampling",
        axis_namespace="condition_kind",
    )


def _resolve_extremum_direction(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_EXTREMUM_DIRECTIONS,
        task_id=TASK_ID,
        explicit_key="extremum_direction",
        weights_key="extremum_direction_weights",
        balance_flag_key="balanced_extremum_direction_sampling",
        axis_namespace="extremum_direction",
    )


def _resolve_query_axis(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_QUERY_AXES,
        task_id=TASK_ID,
        explicit_key="query_axis",
        weights_key="query_axis_weights",
        balance_flag_key="balanced_query_axis_sampling",
        axis_namespace="query_axis",
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


def _resolve_row_column_count(
    params: Mapping[str, Any],
    *,
    scene_variant: str,
    instance_seed: int,
) -> Tuple[int, int, Dict[str, float], Dict[str, float]]:
    if str(scene_variant) == "calendar_heatmap":
        row_min, row_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="calendar_row_count_min",
            max_key="calendar_row_count_max",
            fallback_min=5,
            fallback_max=8,
            context=f"{TASK_ID} calendar rows",
        )
        row_support = list(range(int(row_min), int(row_max) + 1))
        row_count = _balanced_int(
            row_support,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.calendar_row_count",
        )
        return (
            int(row_count),
            7,
            {str(value): 1.0 / float(len(row_support)) for value in row_support},
            {"7": 1.0},
        )

    row_min, row_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="row_count_min",
        max_key="row_count_max",
        fallback_min=6,
        fallback_max=10,
        context=f"{TASK_ID} rows",
    )
    col_min, col_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="column_count_min",
        max_key="column_count_max",
        fallback_min=8,
        fallback_max=12,
        context=f"{TASK_ID} columns",
    )
    row_support = list(range(int(row_min), int(row_max) + 1))
    col_support = list(range(int(col_min), int(col_max) + 1))
    row_count = _balanced_int(row_support, params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.row_count")
    col_count = _balanced_int(col_support, params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.column_count")
    return (
        int(row_count),
        int(col_count),
        {str(value): 1.0 / float(len(row_support)) for value in row_support},
        {str(value): 1.0 / float(len(col_support)) for value in col_support},
    )


def _labels_for_scene(
    *,
    scene_variant: str,
    row_count: int,
    column_count: int,
    rng,
) -> Tuple[List[str], List[str]]:
    if str(scene_variant) == "calendar_heatmap":
        return [f"Week {index + 1}" for index in range(int(row_count))], list(_WEEKDAY_LABELS[: int(column_count)])
    labels = list(
        resolve_chart_entity_labels(
            rng,
            count=int(row_count) + int(column_count),
            min_chars=2,
            max_chars=7,
            allow_spaces=False,
        ).labels
    )
    rows = labels[: int(row_count)]
    columns = labels[int(row_count) : int(row_count) + int(column_count)]
    return [str(label) for label in rows], [str(label) for label in columns]


def _value_palette(scene_variant: str) -> Tuple[Tuple[int, int, int], ...]:
    if str(scene_variant) == "signed_change_heatmap":
        return _SIGNED_PALETTE
    if str(scene_variant) == "calendar_heatmap":
        return _CALENDAR_PALETTE
    return _INTENSITY_PALETTE


def _condition_matches(value: int, *, condition_kind: str, bin_count: int) -> bool:
    midpoint = int(bin_count) // 2
    if str(condition_kind) == "hot":
        return int(value) >= max(0, int(bin_count) - 2)
    if str(condition_kind) == "cool":
        return int(value) <= 1
    if str(condition_kind) == "increase":
        return int(value) > int(midpoint)
    if str(condition_kind) == "decrease":
        return int(value) < int(midpoint)
    raise ValueError(f"unsupported condition_kind: {condition_kind}")


def _condition_phrase(condition_kind: str, *, scene_variant: str) -> str:
    if str(scene_variant) == "calendar_heatmap":
        phrases = {
            "hot": "high-activity (one of the two darkest color levels)",
            "cool": "low-activity (one of the two lightest color levels)",
        }
    else:
        phrases = {
            "hot": "high-intensity (one of the two darkest color levels)",
            "cool": "low-intensity (one of the two lightest color levels)",
            "increase": "increase-colored (one of the two strongest increase color levels)",
            "decrease": "decrease-colored (one of the two strongest decrease color levels)",
        }
    return str(phrases[str(condition_kind)])


def _extremum_phrase(extremum_direction: str, *, scene_variant: str) -> str:
    if str(scene_variant) == "signed_change_heatmap":
        if str(extremum_direction) == "hottest":
            return "strongest increase-colored"
        if str(extremum_direction) == "coolest":
            return "strongest decrease-colored"
    if str(scene_variant) == "calendar_heatmap":
        if str(extremum_direction) == "hottest":
            return "highest-activity"
        if str(extremum_direction) == "coolest":
            return "lowest-activity"
    if str(extremum_direction) == "hottest":
        return "highest-intensity"
    if str(extremum_direction) == "coolest":
        return "lowest-intensity"
    raise ValueError(f"unsupported extremum_direction: {extremum_direction}")


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
            evidence_cells = [
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
            evidence_cells = [
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
            "evidence_cell_ids": _reading_order_cell_ids(evidence_cells),
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
        evidence_cells = [by_pos[(row, int(column_index))] for row in range(int(row_count))]
        return {
            "answer_value": str(row_labels[row_index]),
            "answer_type": "string",
            "answer_row_index": int(row_index),
            "answer_column_index": int(column_index),
            "evidence_cell_ids": _reading_order_cell_ids(evidence_cells),
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
        evidence_cells = [by_pos[(int(row_index), column)] for column in range(int(column_count))]
        return {
            "answer_value": str(column_labels[column_index]),
            "answer_type": "string",
            "answer_row_index": int(row_index),
            "answer_column_index": int(column_index),
            "evidence_cell_ids": _reading_order_cell_ids(evidence_cells),
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
        evidence_cells = [by_pos[(row_index, column_index)] for column_index in range(int(start), int(end) + 1)]
        return {
            "answer_value": str(row_labels[row_index]),
            "answer_type": "string",
            "answer_row_index": int(row_index),
            "answer_column_index": -1,
            "evidence_cell_ids": _reading_order_cell_ids(evidence_cells),
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
                "evidence_cell_ids": [],
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
            "evidence_cell_ids": [],
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
            "evidence_cell_ids": [],
            "question_params": {
                "query_axis": str(query_axis),
                "answer_axis": str(query_axis),
                "condition_kind": "missing_condition",
                "condition_phrase": str(missing_condition),
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
            "evidence_cell_ids": [str(cell_id) for cell_id in query["evidence_cell_ids"]],
            "question_params": dict(query["question_params"]),
            "is_unanswerable": bool(query.get("is_unanswerable", False)),
            "absence_proof": dict(query.get("absence_proof", {})),
        }
    raise ValueError(f"could not construct unique-answer heatmap for {TASK_ID}")


def _draw_text_in_box(
    draw: ImageDraw.ImageDraw,
    text: str,
    bbox: Sequence[float],
    *,
    font_size: int,
    fill: Tuple[int, int, int],
    font_family: str | None = None,
    anchor: str = "center",
) -> None:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    font = fit_font_to_box(
        draw,
        text=str(text),
        max_width=float(x1 - x0),
        max_height=float(y1 - y0),
        min_size_px=8,
        max_size_px=max(8, int(font_size)),
        fill_ratio=0.9,
        font_family=font_family,
    )
    if str(anchor) == "left":
        draw_text_traced(draw,(x0, (y0 + y1) / 2.0), str(text), font=font, fill=fill, anchor="lm", role="readout", required=False)
    else:
        draw_text_traced(draw,((x0 + x1) / 2.0, (y0 + y1) / 2.0), str(text), font=font, fill=fill, anchor="mm", role="readout", required=False)


def _draw_signed_marker(
    draw: ImageDraw.ImageDraw,
    bbox: Sequence[float],
    *,
    value: int,
    bin_count: int,
) -> None:
    midpoint = int(bin_count) // 2
    if int(value) == int(midpoint):
        return
    x0, y0, x1, y1 = [float(value) for value in bbox]
    cx = (x0 + x1) / 2.0
    cy = (y0 + y1) / 2.0
    size = min(float(x1 - x0), float(y1 - y0)) * 0.22
    fill = (38, 48, 58)
    if int(value) > int(midpoint):
        points = [(cx, cy - size), (cx - size, cy + size), (cx + size, cy + size)]
    else:
        points = [(cx, cy + size), (cx - size, cy - size), (cx + size, cy - size)]
    draw.polygon(points, fill=fill)


def _render_legend(
    draw: ImageDraw.ImageDraw,
    *,
    scene_variant: str,
    legend_bbox: Sequence[float],
    render_params: _HeatmapRenderParams,
    palette: Sequence[Tuple[int, int, int]],
) -> None:
    x0, y0, x1, y1 = [float(value) for value in legend_bbox]
    font = load_font(max(8, int(render_params.legend_font_size_px)), font_family=render_params.font_family)
    label = "Legend"
    if str(scene_variant) == "signed_change_heatmap":
        label = "Legend: decrease to increase"
    elif str(scene_variant) == "calendar_heatmap":
        label = "Legend: low to high activity"
    else:
        label = "Legend: low to high intensity"
    draw_text_traced(draw,(x0, y0 + 8), label, font=font, fill=render_params.legend_text_rgb, anchor="la", role="readout", required=False)
    swatch_y0 = y0 + 34
    swatch_h = 20
    swatch_w = max(34.0, min(60.0, (x1 - x0 - 190.0) / float(max(1, len(palette)))))
    start_x = x0 + 82
    for index, color in enumerate(palette):
        sx0 = start_x + (float(index) * swatch_w)
        draw.rectangle([sx0, swatch_y0, sx0 + swatch_w, swatch_y0 + swatch_h], fill=tuple(color), outline=render_params.cell_border_rgb, width=1)
    draw_text_traced(draw,(start_x - 8, swatch_y0 + swatch_h / 2.0), "low", font=font, fill=render_params.legend_text_rgb, anchor="rm", role="readout", required=False)
    draw_text_traced(draw,(start_x + (len(palette) * swatch_w) + 8, swatch_y0 + swatch_h / 2.0), "high", font=font, fill=render_params.legend_text_rgb, anchor="lm", role="readout", required=False)


def _render_heatmap(
    image: Image.Image,
    *,
    scene_title: str,
    scene_variant: str,
    row_labels: Sequence[str],
    column_labels: Sequence[str],
    cells: Sequence[Mapping[str, Any]],
    render_params: _HeatmapRenderParams,
) -> _RenderedHeatmap:
    draw = ImageDraw.Draw(image)
    width, height = image.size
    offset_x = float(render_params.layout_offset_x_px)
    offset_y = float(render_params.layout_offset_y_px)
    panel_bbox = (
        float(render_params.outer_margin_px) + offset_x,
        float(render_params.outer_margin_px) + offset_y,
        float(width - render_params.outer_margin_px) + offset_x,
        float(height - render_params.outer_margin_px) + offset_y,
    )
    draw.rounded_rectangle(panel_bbox, radius=6, fill=render_params.panel_fill_rgb, outline=render_params.panel_border_rgb, width=2)
    title_bbox = (
        panel_bbox[0] + render_params.panel_padding_px,
        panel_bbox[1] + 12,
        panel_bbox[2] - render_params.panel_padding_px,
        panel_bbox[1] + render_params.title_band_height_px,
    )
    _draw_text_in_box(
        draw,
        str(scene_title),
        title_bbox,
        font_size=render_params.title_font_size_px,
        fill=render_params.title_rgb,
        font_family=render_params.font_family,
    )

    grid_left = panel_bbox[0] + render_params.panel_padding_px + render_params.row_label_width_px
    grid_top = panel_bbox[1] + render_params.title_band_height_px + render_params.col_label_height_px
    grid_right = panel_bbox[2] - render_params.panel_padding_px
    grid_bottom = panel_bbox[3] - render_params.panel_padding_px - render_params.legend_height_px
    grid_bbox = (grid_left, grid_top, grid_right, grid_bottom)
    row_count = len(row_labels)
    column_count = len(column_labels)
    gap = float(render_params.cell_gap_px)
    cell_w = (grid_right - grid_left - (gap * float(max(0, column_count - 1)))) / float(max(1, column_count))
    cell_h = (grid_bottom - grid_top - (gap * float(max(0, row_count - 1)))) / float(max(1, row_count))

    draw.rectangle(grid_bbox, outline=render_params.grid_border_rgb, width=2)
    palette = _value_palette(str(scene_variant))
    cell_bbox_map: Dict[str, List[float]] = {}
    row_label_bbox_map: Dict[str, List[float]] = {}
    column_label_bbox_map: Dict[str, List[float]] = {}
    entities: List[Dict[str, Any]] = [
        {
            "entity_id": "heatmap_panel",
            "entity_type": "chart_panel",
            "bbox_xyxy": _round_bbox(panel_bbox),
            "attrs": {"scene_variant": str(scene_variant)},
        },
        {
            "entity_id": "chart_title",
            "entity_type": "chart_title",
            "bbox_xyxy": _round_bbox(title_bbox),
            "attrs": {"title": str(scene_title)},
        },
    ]

    cell_by_pos = {(int(cell["row_index"]), int(cell["column_index"])): dict(cell) for cell in cells}
    for row_index, row_label in enumerate(row_labels):
        label_bbox = (
            panel_bbox[0] + render_params.panel_padding_px,
            grid_top + (float(row_index) * (cell_h + gap)),
            grid_left - 14,
            grid_top + (float(row_index) * (cell_h + gap)) + cell_h,
        )
        row_label_bbox_map[str(row_label)] = _round_bbox(label_bbox)
        _draw_text_in_box(
            draw,
            str(row_label),
            label_bbox,
            font_size=render_params.axis_font_size_px,
            fill=render_params.axis_text_rgb,
            font_family=render_params.font_family,
            anchor="left",
        )
        entities.append(
            {
                "entity_id": f"row_label_{row_index}",
                "entity_type": "row_label",
                "bbox_xyxy": _round_bbox(label_bbox),
                "attrs": {"row_index": int(row_index), "row_label": str(row_label)},
            }
        )

    for column_index, column_label in enumerate(column_labels):
        label_bbox = (
            grid_left + (float(column_index) * (cell_w + gap)),
            panel_bbox[1] + render_params.title_band_height_px,
            grid_left + (float(column_index) * (cell_w + gap)) + cell_w,
            grid_top - 8,
        )
        column_label_bbox_map[str(column_label)] = _round_bbox(label_bbox)
        _draw_text_in_box(
            draw,
            str(column_label),
            label_bbox,
            font_size=render_params.axis_font_size_px,
            fill=render_params.axis_text_rgb,
            font_family=render_params.font_family,
        )
        entities.append(
            {
                "entity_id": f"column_label_{column_index}",
                "entity_type": "column_label",
                "bbox_xyxy": _round_bbox(label_bbox),
                "attrs": {"column_index": int(column_index), "column_label": str(column_label)},
            }
        )

    for row_index in range(int(row_count)):
        for column_index in range(int(column_count)):
            cell = cell_by_pos[(int(row_index), int(column_index))]
            x0 = grid_left + (float(column_index) * (cell_w + gap))
            y0 = grid_top + (float(row_index) * (cell_h + gap))
            bbox = (x0, y0, x0 + cell_w, y0 + cell_h)
            color = palette[int(cell["heat_level"]) % len(palette)]
            draw.rectangle(bbox, fill=color, outline=render_params.cell_border_rgb, width=int(render_params.cell_border_width_px))
            if str(scene_variant) == "signed_change_heatmap":
                _draw_signed_marker(draw, bbox, value=int(cell["heat_level"]), bin_count=len(palette))
            cell_bbox = _round_bbox(bbox)
            cell_bbox_map[str(cell["cell_id"])] = list(cell_bbox)
            entities.append(
                {
                    "entity_id": str(cell["cell_id"]),
                    "entity_type": "heatmap_cell",
                    "bbox_xyxy": list(cell_bbox),
                    "attrs": {
                        "row_index": int(row_index),
                        "column_index": int(column_index),
                        "row_label": str(cell["row_label"]),
                        "column_label": str(cell["column_label"]),
                        "heat_level": int(cell["heat_level"]),
                    },
                }
            )

    legend_bbox = (
        panel_bbox[0] + render_params.panel_padding_px,
        panel_bbox[3] - render_params.panel_padding_px - render_params.legend_height_px + 12,
        panel_bbox[2] - render_params.panel_padding_px,
        panel_bbox[3] - render_params.panel_padding_px,
    )
    _render_legend(
        draw,
        scene_variant=str(scene_variant),
        legend_bbox=legend_bbox,
        render_params=render_params,
        palette=palette,
    )
    entities.append(
        {
            "entity_id": "heatmap",
            "entity_type": "heatmap",
            "bbox_xyxy": _round_bbox(grid_bbox),
            "attrs": {"row_count": int(row_count), "column_count": int(column_count)},
        }
    )
    entities.append(
        {
            "entity_id": "heatmap_legend",
            "entity_type": "heatmap_legend",
            "bbox_xyxy": _round_bbox(legend_bbox),
            "attrs": {"scene_variant": str(scene_variant)},
        }
    )
    return _RenderedHeatmap(
        image=image,
        entities=tuple(dict(item) for item in entities),
        panel_bbox_px=_round_bbox(panel_bbox),
        title_bbox_px=_round_bbox(title_bbox),
        grid_bbox_px=_round_bbox(grid_bbox),
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


class ChartsHeatmapGridQueryTask:
    """Answer label questions over color/intensity heatmap grids."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "heatmap"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, query_id_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
        support_params = _support_sampling_params(params, query_id_probabilities=query_id_probabilities)
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(support_params, instance_seed=int(instance_seed))
        query_axis = "row"
        query_axis_probabilities: Dict[str, float] = {}
        if str(query_id) in {"axis_condition_extremum_label", "axis_cell_extremum_label"}:
            query_axis, query_axis_probabilities = _resolve_query_axis(
                support_params,
                instance_seed=int(instance_seed),
            )
        condition_kind = ""
        condition_probabilities: Dict[str, float] = {}
        if str(query_id) in {"axis_condition_extremum_label", "condition_run_extremum_label"}:
            condition_params = _decoupled_sampling_params(
                support_params,
                divisor=2,
                explicit_keys=("condition_kind", "condition_kind_weights"),
            )
            condition_kind, condition_probabilities = _resolve_condition_kind(
                condition_params,
                scene_variant=str(scene_variant),
                instance_seed=int(instance_seed),
            )
        else:
            condition_kind = _condition_support(str(scene_variant))[0]
        extremum_direction = ""
        extremum_probabilities: Dict[str, float] = {}
        if str(query_id) == "axis_cell_extremum_label":
            extremum_params = _decoupled_sampling_params(
                support_params,
                divisor=2,
                explicit_keys=("extremum_direction", "extremum_direction_weights"),
            )
            extremum_direction, extremum_probabilities = _resolve_extremum_direction(
                extremum_params,
                instance_seed=int(instance_seed),
            )
        else:
            extremum_direction = "hottest"

        dataset_params = {**dict(support_params), "_enable_unanswerable": bool(getattr(self, "supports_unanswerable", False))}
        dataset = _construct_dataset(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            query_axis=str(query_axis),
            condition_kind=str(condition_kind),
            extremum_direction=str(extremum_direction),
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
        rendered_scene = _render_heatmap(
            background,
            scene_title=str(dataset["scene_title"]),
            scene_variant=str(scene_variant),
            row_labels=list(dataset["row_labels"]),
            column_labels=list(dataset["column_labels"]),
            cells=list(dataset["cells"]),
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
                "object_description_intensity_heatmap",
                "object_description_signed_change_heatmap",
                "object_description_calendar_heatmap",
                "answer_hint_label",
                "evidence_hint_axis_condition_extremum_label",
                "evidence_hint_axis_cell_extremum_label",
                "evidence_hint_condition_run_extremum_label",
                "json_example_axis_condition_extremum_label",
                "json_example_axis_cell_extremum_label",
                "json_example_condition_run_extremum_label",
                "json_example_answer_only_axis_condition_extremum_label",
                "json_example_answer_only_axis_cell_extremum_label",
                "json_example_answer_only_condition_run_extremum_label",
                "unanswerable_instruction",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _json_examples(str(query_id), prompt_defaults=prompt_defaults)
        qparams = dict(dataset["question_params"])
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
                "answer_hint": str(prompt_defaults["answer_hint_label"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "condition_phrase": str(qparams.get("condition_phrase", "")),
                "query_axis": str(qparams.get("query_axis", "")),
                "answer_axis": str(qparams.get("answer_axis", "")),
                "axis_label": str(qparams.get("axis_label", "")),
                "column_label": str(qparams.get("column_label", "")),
                "row_label": str(qparams.get("row_label", "")),
                "extremum_phrase": str(qparams.get("extremum_phrase", "")),
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
        evidence_bboxes = [list(rendered_scene.cell_bbox_map[str(cell_id)]) for cell_id in evidence_cell_ids]
        projected_evidence = {
            "bbox_set": list(evidence_bboxes),
            "bbox_map": {str(cell_id): list(rendered_scene.cell_bbox_map[str(cell_id)]) for cell_id in evidence_cell_ids},
            "cell_ids": list(evidence_cell_ids),
        }
        answer_gt = TypedValue(type=str(dataset["answer_type"]), value=dataset["answer_value"])
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        evidence_scan = normalize_int_with_bounds(len(evidence_cell_ids), [1, 16])
        grid_scan = normalize_int_with_bounds(int(dataset["row_count"]) * int(dataset["column_count"]), [35, 120])
        reasoning_load = clamp_unit_interval(
            float(_REASONING_LOAD_BY_VARIANT[str(query_id)])
            + (0.14 * float(evidence_scan))
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
            "query_id_probabilities": dict(query_id_probabilities),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "row_count": int(dataset["row_count"]),
            "column_count": int(dataset["column_count"]),
            "row_count_probabilities": dict(dataset["row_count_probabilities"]),
            "column_count_probabilities": dict(dataset["column_count_probabilities"]),
            "heat_bin_count": int(dataset["heat_bin_count"]),
            "query_axis": str(dataset["query_axis"]),
            **dict(qparams),
        }
        if condition_probabilities:
            query_params["condition_kind_probabilities"] = dict(condition_probabilities)
        if extremum_probabilities:
            query_params["extremum_direction_probabilities"] = dict(extremum_probabilities)
        if query_axis_probabilities:
            query_params["query_axis_probabilities"] = dict(query_axis_probabilities)

        trace_payload = {
            "scene_ir": {
                "scene_kind": "chart_heatmap",
                "entities": [dict(item) for item in rendered_scene.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "query_axis": str(query_axis),
                    "answer_value": dataset["answer_value"],
                    "answer_row_index": int(dataset["answer_row_index"]),
                    "answer_column_index": int(dataset["answer_column_index"]),
                    "evidence_cell_ids": list(evidence_cell_ids),
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
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "row_count": int(dataset["row_count"]),
                "column_count": int(dataset["column_count"]),
                "heat_bin_count": int(dataset["heat_bin_count"]),
                "cell_gap_px": int(render_params.cell_gap_px),
                "layout_jitter": dict(render_params.layout_jitter_meta),
                "font_assets": {
                    "asset_version": font_asset_version(),
                    "chart_font_family": str(render_params.font_family),
                },
                "post_image_noise": dict(post_noise_meta),
            },
            "render_map": {
                "panel_bbox_px": list(rendered_scene.panel_bbox_px),
                "title_bbox_px": list(rendered_scene.title_bbox_px),
                "grid_bbox_px": list(rendered_scene.grid_bbox_px),
                "legend_bbox_px": list(rendered_scene.legend_bbox_px),
                "cell_bboxes_px": dict(rendered_scene.cell_bbox_map),
                "row_label_bboxes_px": dict(rendered_scene.row_label_bbox_map),
                "column_label_bboxes_px": dict(rendered_scene.column_label_bbox_map),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "question_format": "heatmap_query",
                "scene_title": str(dataset["scene_title"]),
                "row_count": int(dataset["row_count"]),
                "column_count": int(dataset["column_count"]),
                "row_labels": list(dataset["row_labels"]),
                "column_labels": list(dataset["column_labels"]),
                "heat_bin_count": int(dataset["heat_bin_count"]),
                "values": [[int(value) for value in row] for row in dataset["values"]],
                "cells": [dict(cell) for cell in dataset["cells"]],
                "cells_by_id": {str(key): dict(value) for key, value in dict(dataset["cells_by_id"]).items()},
                "answer_value": dataset["answer_value"],
                "answer_type": str(dataset["answer_type"]),
                "answer_row_index": int(dataset["answer_row_index"]),
                "answer_column_index": int(dataset["answer_column_index"]),
                "evidence_cell_ids": list(evidence_cell_ids),
                "query_axis": str(query_axis),
                "condition_kind": str(dataset["condition_kind"]),
                "extremum_direction": str(extremum_direction),
                "evidence_semantics": str(query_id),
                "answerability": "unanswerable" if bool(dataset["is_unanswerable"]) else "answerable",
                **({"absence_proof": dict(dataset["absence_proof"])} if bool(dataset["is_unanswerable"]) else {}),
            },
            "witness_symbolic": {
                "type": "heatmap_witness",
                "candidate_cell_ids": list(evidence_cell_ids),
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
class ChartsHeatmapAxisConditionExtremumLabelTask(
    FixedChartQueryVariantTaskMixin,
    ChartsHeatmapGridQueryTask,
):
    """Return the row or column label with the most cells satisfying a color condition."""

    task_id = "task_charts__heatmap__axis_condition_extremum_label"
    fixed_query_id = "axis_condition_extremum_label"
    supports_unanswerable = True


@register_task
class ChartsHeatmapAxisCellExtremumLabelTask(
    FixedChartQueryVariantTaskMixin,
    ChartsHeatmapGridQueryTask,
):
    """Return the row or column label containing a requested cell extremum."""

    task_id = "task_charts__heatmap__axis_cell_extremum_label"
    fixed_query_id = "axis_cell_extremum_label"
    supports_unanswerable = True


@register_task
class ChartsHeatmapConditionRunExtremumLabelTask(
    FixedChartQueryVariantTaskMixin,
    ChartsHeatmapGridQueryTask,
):
    """Return the label with the longest consecutive run satisfying a color condition."""

    task_id = "task_charts__heatmap__condition_run_extremum_label"
    fixed_query_id = "condition_run_extremum_label"


__all__ = [
    "ChartsHeatmapAxisCellExtremumLabelTask",
    "ChartsHeatmapAxisConditionExtremumLabelTask",
    "ChartsHeatmapConditionRunExtremumLabelTask",
    "ChartsHeatmapGridQueryTask",
    "SUPPORTED_SCENE_VARIANTS",
    "SUPPORTED_QUERY_IDS",
]
