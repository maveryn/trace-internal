"""Dataset and query sampling for scientific style-legend chart tasks."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from .....core.seed import spawn_rng
from ....shared.config_defaults import group_default
from ...shared.label_assets import resolve_chart_axis_labels, resolve_chart_entity_labels
from .style_legend_common import (
    GAP_QUERY_IDS,
    EXTREMUM_QUERY_IDS,
    THRESHOLD_QUERY_IDS,
    TASK_ID,
    RGB,
    _Dataset,
    _GEN_DEFAULTS,
    _LINE_STYLES,
    _MARKER_FILLS,
    _MARKER_SHAPES,
    _Query,
    _Series,
    _SeriesStyle,
    _balanced_choice,
    _count_from_range,
    _gen_int,
    _point_id,
    _resolve_legend_position,
    _resolve_palette_mode,
    _selection_index,
)

def _series_labels(params: Mapping[str, Any], *, instance_seed: int, count: int) -> Tuple[Tuple[str, ...], Dict[str, Any]]:
    weights = params.get("series_label_bucket_weights", group_default(_GEN_DEFAULTS, "series_label_bucket_weights", None))
    resolved = resolve_chart_entity_labels(
        spawn_rng(int(instance_seed), f"{TASK_ID}.series_labels"),
        count=int(count),
        min_chars=int(_gen_int(params, "series_label_min_chars", 2)),
        max_chars=int(_gen_int(params, "series_label_max_chars", 7)),
        allow_spaces=False,
        bucket_weights=weights if isinstance(weights, Mapping) else None,
    )
    return tuple(str(label) for label in resolved.labels), {
        "label_variant": str(resolved.label_variant),
        "label_pool_kind": str(resolved.label_pool_kind),
        "label_source_kind": str(resolved.label_source_kind),
        "label_bucket": str(resolved.label_bucket),
        "label_manifest": str(resolved.label_manifest),
        "label_filter": dict(resolved.label_filter),
        "label_bucket_probabilities": dict(resolved.label_bucket_probabilities),
    }

def _x_labels(params: Mapping[str, Any], *, instance_seed: int, count: int) -> Tuple[Tuple[str, ...], Dict[str, Any]]:
    weights = params.get("x_label_bucket_weights", group_default(_GEN_DEFAULTS, "x_label_bucket_weights", None))
    resolved = resolve_chart_axis_labels(
        spawn_rng(int(instance_seed), f"{TASK_ID}.x_labels"),
        count=int(count),
        min_chars=int(_gen_int(params, "x_label_min_chars", 2)),
        max_chars=int(_gen_int(params, "x_label_max_chars", 6)),
        bucket_weights=weights if isinstance(weights, Mapping) else None,
    )
    return tuple(str(label) for label in resolved.labels), {
        "label_variant": str(resolved.label_variant),
        "label_pool_kind": str(resolved.label_pool_kind),
        "label_source_kind": str(resolved.label_source_kind),
        "label_bucket": str(resolved.label_bucket),
        "label_manifest": str(resolved.label_manifest),
        "label_filter": dict(resolved.label_filter),
        "label_bucket_probabilities": dict(resolved.label_bucket_probabilities),
    }

def _colors_for_mode(mode: str, count: int) -> Tuple[RGB, ...]:
    if str(mode) == "grayscale":
        base = (32, 48, 64, 82, 104, 126)
        return tuple((value, value, value) for value in base[: int(count)])
    if str(mode) == "muted_color":
        palette = ((64, 92, 134), (132, 89, 71), (78, 121, 94), (116, 92, 137), (148, 124, 68), (72, 124, 134))
        return tuple(palette[index % len(palette)] for index in range(int(count)))
    palette = ((0, 114, 178), (213, 94, 0), (0, 158, 115), (204, 121, 167), (230, 159, 0), (86, 180, 233))
    return tuple(palette[index % len(palette)] for index in range(int(count)))

def _styles_for_series(*, count: int, palette_mode: str, instance_seed: int) -> Tuple[_SeriesStyle, ...]:
    colors = list(_colors_for_mode(str(palette_mode), int(count)))
    style_tuples = [
        (line, marker, fill)
        for line in _LINE_STYLES
        for marker in _MARKER_SHAPES
        for fill in _MARKER_FILLS
    ]
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.style_tuples")
    rng.shuffle(style_tuples)
    styles: List[_SeriesStyle] = []
    used: set[Tuple[str, str, str]] = set()
    for index in range(int(count)):
        line_style, marker_shape, marker_fill = style_tuples[int(index)]
        key = (str(line_style), str(marker_shape), str(marker_fill))
        if key in used:
            raise ValueError("duplicate style tuple")
        used.add(key)
        styles.append(
            _SeriesStyle(
                color_rgb=tuple(colors[int(index) % len(colors)]),
                line_style=str(line_style),
                marker_shape=str(marker_shape),
                marker_fill=str(marker_fill),
                line_width_px=2 + (int(index) % 2),
            )
        )
    return tuple(styles)

def _random_values(*, count: int, rng: Any, min_value: int, max_value: int) -> List[int]:
    current = int(rng.randint(28, 72))
    values: List[int] = []
    for _ in range(int(count)):
        current += int(rng.randint(-16, 16))
        current = max(int(min_value) + 5, min(int(max_value) - 5, int(current)))
        values.append(int(current))
    return values

def _base_series(
    *,
    labels: Sequence[str],
    x_count: int,
    styles: Sequence[_SeriesStyle],
    instance_seed: int,
    value_min: int,
    value_max: int,
) -> List[_Series]:
    series: List[_Series] = []
    for index, label in enumerate(labels):
        values = _random_values(
            count=int(x_count),
            rng=spawn_rng(int(instance_seed), f"{TASK_ID}.values.s{int(index)}"),
            min_value=int(value_min),
            max_value=int(value_max),
        )
        series.append(
            _Series(
                series_id=f"s{int(index)}",
                label=str(label),
                values=tuple(int(value) for value in values),
                style=styles[int(index)],
            )
        )
    return series

def _replace_series_value(series: _Series, *, x_index: int, value: int) -> _Series:
    values = list(series.values)
    values[int(x_index)] = int(value)
    return _Series(series_id=str(series.series_id), label=str(series.label), values=tuple(values), style=series.style)

def _common_setup(params: Mapping[str, Any], *, instance_seed: int, min_series_count: int = 4) -> Tuple[int, int, Tuple[str, ...], Dict[str, Any], Tuple[str, ...], Dict[str, Any], str, Dict[str, float], str, Dict[str, float], Tuple[_SeriesStyle, ...]]:
    x_count = _count_from_range(
        params,
        min_key="style_legend_x_count_min",
        max_key="style_legend_x_count_max",
        fallback_min=5,
        fallback_max=9,
        instance_seed=int(instance_seed),
        namespace="x_count",
    )
    series_count = _count_from_range(
        params,
        min_key="style_legend_series_count_min",
        max_key="style_legend_series_count_max",
        fallback_min=4,
        fallback_max=6,
        instance_seed=int(instance_seed),
        namespace="series_count",
    )
    series_count = max(int(min_series_count), int(series_count))
    x_labels, x_meta = _x_labels(params, instance_seed=int(instance_seed), count=int(x_count))
    labels, label_meta = _series_labels(params, instance_seed=int(instance_seed), count=int(series_count))
    palette_mode, palette_probs = _resolve_palette_mode(params, instance_seed=int(instance_seed))
    legend_position, legend_probs = _resolve_legend_position(params, instance_seed=int(instance_seed))
    styles = _styles_for_series(count=int(series_count), palette_mode=str(palette_mode), instance_seed=int(instance_seed))
    return (
        int(x_count),
        int(series_count),
        tuple(x_labels),
        dict(x_meta),
        tuple(labels),
        dict(label_meta),
        str(palette_mode),
        dict(palette_probs),
        str(legend_position),
        dict(legend_probs),
        tuple(styles),
    )

def _build_extremum_dataset(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    query_id: str,
    query_probabilities: Mapping[str, float],
) -> _Dataset:
    x_count, series_count, x_labels, x_meta, labels, label_meta, palette_mode, palette_probs, legend_position, legend_probs, styles = _common_setup(
        params,
        instance_seed=int(instance_seed),
    )
    value_min = int(_gen_int(params, "style_legend_value_min", 0))
    value_max = int(_gen_int(params, "style_legend_value_max", 100))
    if int(value_min) >= int(value_max):
        raise ValueError("style_legend_value_min must be lower than style_legend_value_max")
    x_index = int(
        _balanced_choice(
            tuple(range(1, max(2, int(x_count) - 1))),
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.extremum.x_index",
        )
    )
    answer_index = int(
        _balanced_choice(
            tuple(range(int(series_count))),
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.extremum.answer_series",
        )
    )
    series = _base_series(
        labels=labels,
        x_count=int(x_count),
        styles=styles,
        instance_seed=int(instance_seed),
        value_min=int(value_min),
        value_max=int(value_max),
    )
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.extremum.force")
    direction = "highest" if str(query_id) == "x_position_highest_series_label" else "lowest"
    target_value = int(rng.randint(72, 92)) if direction == "highest" else int(rng.randint(8, 28))
    gap_min = max(3, int(_gen_int(params, "style_legend_extremum_gap_min", 8)))
    gap_max = max(int(gap_min), int(_gen_int(params, "style_legend_extremum_gap_max", 26)))
    updated: List[_Series] = []
    for index, item in enumerate(series):
        if int(index) == int(answer_index):
            value = int(target_value)
        elif direction == "highest":
            value = max(int(value_min) + 3, int(target_value) - int(rng.randint(int(gap_min), int(gap_max))))
        else:
            value = min(int(value_max) - 3, int(target_value) + int(rng.randint(int(gap_min), int(gap_max))))
        updated.append(_replace_series_value(item, x_index=int(x_index), value=int(value)))
    answer_series = updated[int(answer_index)]
    annotation_ids = (_point_id(str(answer_series.series_id), int(x_index)),)
    query = _Query(
        query_id=str(query_id),
        answer=str(answer_series.label),
        answer_type="string",
        annotation_point_ids=annotation_ids,
        params={
            "x_label": str(x_labels[int(x_index)]),
            "extremum_direction": str(direction),
            "answer_support": [str(label) for label in labels],
        },
    )
    return _Dataset(
        x_labels=tuple(x_labels),
        x_label_meta=dict(x_meta),
        series=tuple(updated),
        series_label_meta=dict(label_meta),
        query=query,
        target_x_index=int(x_index),
        threshold_value=None,
        pair_series_ids=(),
        palette_mode=str(palette_mode),
        palette_mode_probabilities=dict(palette_probs),
        legend_position=str(legend_position),
        legend_position_probabilities=dict(legend_probs),
        query_id_probabilities=dict(query_probabilities),
    )

def _build_gap_dataset(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    query_id: str,
    query_probabilities: Mapping[str, float],
) -> _Dataset:
    x_count, series_count, x_labels, x_meta, labels, label_meta, palette_mode, palette_probs, legend_position, legend_probs, styles = _common_setup(
        params,
        instance_seed=int(instance_seed),
    )
    value_min = int(_gen_int(params, "style_legend_value_min", 0))
    value_max = int(_gen_int(params, "style_legend_value_max", 100))
    x_index = int(
        _balanced_choice(
            tuple(range(1, max(2, int(x_count) - 1))),
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.gap.x_index",
        )
    )
    left_index = int(
        _balanced_choice(
            tuple(range(int(series_count))),
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.gap.left_series",
        )
    )
    right_index = (int(left_index) + 1 + int(_selection_index(params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.gap.right_offset")) % (int(series_count) - 1)) % int(series_count)
    gap_min = int(_gen_int(params, "style_legend_gap_answer_min", 8))
    gap_max = max(int(gap_min), int(_gen_int(params, "style_legend_gap_answer_max", 36)))
    gap_support = tuple(range(int(gap_min), int(gap_max) + 1))
    gap = int(_balanced_choice(gap_support, params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.gap.answer"))
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.gap.force")
    low = int(rng.randint(max(int(value_min) + 5, 8), max(int(value_min) + 5, int(value_max) - int(gap) - 5)))
    high = int(low + gap)
    if rng.random() < 0.5:
        left_value, right_value = int(high), int(low)
    else:
        left_value, right_value = int(low), int(high)
    series = _base_series(
        labels=labels,
        x_count=int(x_count),
        styles=styles,
        instance_seed=int(instance_seed),
        value_min=int(value_min),
        value_max=int(value_max),
    )
    updated = list(series)
    updated[int(left_index)] = _replace_series_value(updated[int(left_index)], x_index=int(x_index), value=int(left_value))
    updated[int(right_index)] = _replace_series_value(updated[int(right_index)], x_index=int(x_index), value=int(right_value))
    left_series = updated[int(left_index)]
    right_series = updated[int(right_index)]
    query = _Query(
        query_id=str(query_id),
        answer=int(gap),
        answer_type="integer",
        annotation_point_ids=(
            _point_id(str(left_series.series_id), int(x_index)),
            _point_id(str(right_series.series_id), int(x_index)),
        ),
        params={
            "x_label": str(x_labels[int(x_index)]),
            "left_series_label": str(left_series.label),
            "right_series_label": str(right_series.label),
        },
    )
    return _Dataset(
        x_labels=tuple(x_labels),
        x_label_meta=dict(x_meta),
        series=tuple(updated),
        series_label_meta=dict(label_meta),
        query=query,
        target_x_index=int(x_index),
        threshold_value=None,
        pair_series_ids=(str(left_series.series_id), str(right_series.series_id)),
        palette_mode=str(palette_mode),
        palette_mode_probabilities=dict(palette_probs),
        legend_position=str(legend_position),
        legend_position_probabilities=dict(legend_probs),
        query_id_probabilities=dict(query_probabilities),
    )

def _build_threshold_dataset(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    query_id: str,
    query_probabilities: Mapping[str, float],
) -> _Dataset:
    answer_min = int(_gen_int(params, "style_legend_threshold_answer_min", 0))
    answer_max = int(_gen_int(params, "style_legend_threshold_answer_max", 5))
    answer_support = tuple(range(int(answer_min), int(answer_max) + 1))
    target_count = int(_balanced_choice(answer_support, params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.threshold.answer"))
    x_count, series_count, x_labels, x_meta, labels, label_meta, palette_mode, palette_probs, legend_position, legend_probs, styles = _common_setup(
        params,
        instance_seed=int(instance_seed),
        min_series_count=max(4, int(target_count)),
    )
    if int(target_count) > int(series_count):
        raise ValueError("threshold target count exceeds series count")
    value_min = int(_gen_int(params, "style_legend_value_min", 0))
    value_max = int(_gen_int(params, "style_legend_value_max", 100))
    x_index = int(
        _balanced_choice(
            tuple(range(1, max(2, int(x_count) - 1))),
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.threshold.x_index",
        )
    )
    threshold_values = params.get("style_legend_threshold_values", group_default(_GEN_DEFAULTS, "style_legend_threshold_values", (40, 50, 60)))
    threshold_support = tuple(int(value) for value in threshold_values) if isinstance(threshold_values, Sequence) and not isinstance(threshold_values, (str, bytes)) else (40, 50, 60)
    threshold = int(
        _balanced_choice(
            threshold_support,
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.threshold.value",
        )
    )
    direction = "above" if str(query_id) == "above_threshold_series_count" else "below"
    selected_indices = set(range(int(target_count)))
    series = _base_series(
        labels=labels,
        x_count=int(x_count),
        styles=styles,
        instance_seed=int(instance_seed),
        value_min=int(value_min),
        value_max=int(value_max),
    )
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.threshold.force")
    updated: List[_Series] = []
    annotation_ids: List[str] = []
    for index, item in enumerate(series):
        if int(index) in selected_indices:
            value = int(rng.randint(int(threshold) + 8, min(int(value_max) - 3, int(threshold) + 34))) if direction == "above" else int(rng.randint(max(int(value_min) + 3, int(threshold) - 34), int(threshold) - 8))
            annotation_ids.append(_point_id(str(item.series_id), int(x_index)))
        else:
            value = int(rng.randint(max(int(value_min) + 3, int(threshold) - 34), int(threshold) - 8)) if direction == "above" else int(rng.randint(int(threshold) + 8, min(int(value_max) - 3, int(threshold) + 34)))
        updated.append(_replace_series_value(item, x_index=int(x_index), value=int(value)))
    query = _Query(
        query_id=str(query_id),
        answer=int(target_count),
        answer_type="integer",
        annotation_point_ids=tuple(annotation_ids),
        params={
            "x_label": str(x_labels[int(x_index)]),
            "threshold_value": int(threshold),
            "threshold_direction": str(direction),
            "threshold_relation_phrase": "above" if direction == "above" else "below",
            "answer_support": [int(value) for value in answer_support],
        },
    )
    return _Dataset(
        x_labels=tuple(x_labels),
        x_label_meta=dict(x_meta),
        series=tuple(updated),
        series_label_meta=dict(label_meta),
        query=query,
        target_x_index=int(x_index),
        threshold_value=int(threshold),
        pair_series_ids=(),
        palette_mode=str(palette_mode),
        palette_mode_probabilities=dict(palette_probs),
        legend_position=str(legend_position),
        legend_position_probabilities=dict(legend_probs),
        query_id_probabilities=dict(query_probabilities),
    )

def _build_dataset(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    query_id: str,
    query_probabilities: Mapping[str, float],
) -> _Dataset:
    if str(query_id) in set(EXTREMUM_QUERY_IDS):
        return _build_extremum_dataset(params, instance_seed=int(instance_seed), query_id=str(query_id), query_probabilities=query_probabilities)
    if str(query_id) in set(GAP_QUERY_IDS):
        return _build_gap_dataset(params, instance_seed=int(instance_seed), query_id=str(query_id), query_probabilities=query_probabilities)
    if str(query_id) in set(THRESHOLD_QUERY_IDS):
        return _build_threshold_dataset(params, instance_seed=int(instance_seed), query_id=str(query_id), query_probabilities=query_probabilities)
    raise ValueError(f"unsupported query_id: {query_id}")

def _style_support_trace(series: Sequence[_Series]) -> List[Dict[str, Any]]:
    return [
        {
            "series_id": str(item.series_id),
            "label": str(item.label),
            "values": [int(value) for value in item.values],
            "style": {
                "color_rgb": [int(channel) for channel in item.style.color_rgb],
                "line_style": str(item.style.line_style),
                "marker_shape": str(item.style.marker_shape),
                "marker_fill": str(item.style.marker_fill),
                "line_width_px": int(item.style.line_width_px),
            },
        }
        for item in series
    ]
