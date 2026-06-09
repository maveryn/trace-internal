"""Dataset construction for synthetic 3D chart panel tasks."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ...shared.config_defaults import group_default
from ...shared.deterministic_sampling import resolve_selection_index
from ..shared.label_assets import (
    resolve_chart_entity_labels,
    resolve_chart_panel_labels,
    validate_chart_label_namespaces,
)
from ..shared.labeled_chart_common import resolve_chart_axis_variant
from .panel_common import (
    _GEN_DEFAULTS,
    _PALETTE,
    _SUPPORTED_EXTREMA,
    _SUPPORTED_TRENDS,
    _TIME_POOL,
    TASK_ID,
    _Dataset,
    _Panel3D,
    _Point3D,
    _Query,
    _SurfaceCell,
    _gen_int,
)

def _choice_index(params: Mapping[str, Any], *, instance_seed: int, namespace: str) -> int:
    return int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace)))

def _balanced_int(
    *,
    low: int,
    high: int,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> int:
    if int(low) > int(high):
        raise ValueError(f"invalid integer support for {namespace}")
    return int(low) + (_choice_index(params, instance_seed=int(instance_seed), namespace=str(namespace)) % (int(high) - int(low) + 1))

def _balanced_choice(values: Sequence[Any], *, params: Mapping[str, Any], instance_seed: int, namespace: str) -> Any:
    support = list(values)
    if not support:
        raise ValueError(f"empty support for {namespace}")
    return support[_choice_index(params, instance_seed=int(instance_seed), namespace=str(namespace)) % len(support)]

def _resolve_extremum(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_EXTREMA,
        task_id=TASK_ID,
        explicit_key="extremum_direction",
        weights_key="extremum_direction_weights",
        balance_flag_key="balanced_extremum_direction_sampling",
        axis_namespace="extremum_direction",
    )

def _resolve_trend(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_TRENDS,
        task_id=TASK_ID,
        explicit_key="trend_direction",
        weights_key="trend_direction_weights",
        balance_flag_key="balanced_trend_direction_sampling",
        axis_namespace="trend_direction",
    )

def _sample_labels(count: int, *, instance_seed: int, namespace: str) -> Tuple[str, ...]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.{namespace}.labels")
    labels = resolve_chart_entity_labels(
        rng,
        count=int(count),
        min_chars=2,
        max_chars=6,
        allow_spaces=False,
    ).labels
    return tuple(str(label) for label in labels)

def _resolved_label_metadata(resolved: Any) -> Dict[str, Any]:
    return {
        "label_variant": str(resolved.label_variant),
        "label_pool_kind": str(resolved.label_pool_kind),
        "label_source_kind": str(resolved.label_source_kind),
        "label_bucket": str(resolved.label_bucket),
        "label_manifest": str(resolved.label_manifest),
        "label_filter": dict(resolved.label_filter),
        "label_bucket_probabilities": dict(resolved.label_bucket_probabilities),
    }

def _sample_panel_labels(
    count: int,
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    reserved_labels: Sequence[str] = (),
) -> Tuple[Tuple[str, ...], Dict[str, Any]]:
    resolved = resolve_chart_panel_labels(
        spawn_rng(int(instance_seed), f"{TASK_ID}.panel.labels"),
        count=int(count),
        min_chars=1,
        max_chars=10,
        allow_spaces=False,
        variant_weights=params.get(
            "panel_label_variant_weights",
            group_default(
                _GEN_DEFAULTS,
                "panel_label_variant_weights",
                {
                    "named_compact": 1.0,
                    "technical_topics": 1.0,
                    "condition_labels": 0.75,
                    "temporal_sequence": 0.25,
                    "report_topics": 0.5,
                },
            ),
        ),
        reserved_labels=tuple(str(label) for label in reserved_labels),
    )
    collision_check = validate_chart_label_namespaces(
        panel_labels=resolved.labels,
        other_label_groups={"reserved_labels": tuple(str(label) for label in reserved_labels)},
        context="3D panel labels",
    )
    return tuple(str(label) for label in resolved.labels), {
        "panel_label_resolution": _resolved_label_metadata(resolved),
        "panel_label_collision_check": dict(collision_check),
    }

def _dataset_reference_nearest(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    category_count = _balanced_int(
        low=_gen_int(params, "category_count_min", 5),
        high=_gen_int(params, "category_count_max", 8),
        params=params,
        instance_seed=instance_seed,
        namespace="nearest.category_count",
    )
    target_value = _balanced_int(low=25, high=75, params=params, instance_seed=instance_seed, namespace="nearest.target")
    labels = _sample_labels(int(category_count), instance_seed=instance_seed, namespace="nearest")
    answer_label = str(_balanced_choice(labels, params=params, instance_seed=instance_seed, namespace="nearest.answer_label"))
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.nearest.points")
    points: List[_Point3D] = []
    for index, label in enumerate(labels):
        if str(label) == answer_label:
            y_value = float(target_value + rng.choice([-2, -1, 1, 2]))
        else:
            offset = int(rng.choice([-1, 1])) * int(rng.randint(8, 31))
            y_value = float(max(5, min(95, int(target_value) + int(offset))))
            if abs(y_value - float(target_value)) <= 5:
                y_value = float(max(5, min(95, int(target_value) + (12 if offset >= 0 else -12))))
        points.append(
            _Point3D(
                point_id=f"point_{label}",
                label=str(label),
                x_value=float(rng.randint(8, 92)),
                y_value=float(y_value),
                z_value=float(rng.randint(8, 92)),
                color_rgb=_PALETTE[int(index) % len(_PALETTE)],
            )
        )
    distances = {str(point.label): round(abs(float(point.y_value) - float(target_value)), 3) for point in points}
    return _Dataset(
        scene_variant="three_d_scatter",
        points=tuple(points),
        surface_cells=(),
        panels=(),
        x_axis_label="Score",
        y_axis_label="Distance",
        z_axis_label="Volume",
        x_range=(0.0, 100.0),
        y_range=(0.0, 100.0),
        z_range=(0.0, 100.0),
        x_labels=(),
        y_labels=(),
        query=_Query(
            query_id="reference_nearest_label",
            scene_variant="three_d_scatter",
            answer=str(answer_label),
            answer_type="string",
            annotation_point_ids=(f"point_{answer_label}",),
            trace={
                "target_axis": "y",
                "target_axis_label": "Distance",
                "target_axis_value": int(target_value),
                "distances_from_target": dict(distances),
                "category_count": int(category_count),
            },
        ),
    )

def _dataset_surface_extremum(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    x_count = _balanced_int(low=_gen_int(params, "surface_x_count_min", 5), high=_gen_int(params, "surface_x_count_max", 7), params=params, instance_seed=instance_seed, namespace="surface.x_count")
    y_count = _balanced_int(low=_gen_int(params, "surface_y_count_min", 4), high=_gen_int(params, "surface_y_count_max", 6), params=params, instance_seed=instance_seed, namespace="surface.y_count")
    extremum, extremum_probabilities = _resolve_extremum(params, instance_seed=instance_seed)
    x_labels = _sample_labels(int(x_count), instance_seed=instance_seed, namespace="surface.x")
    y_labels = _sample_labels(int(y_count), instance_seed=instance_seed, namespace="surface.y")
    target_y = str(_balanced_choice(y_labels, params=params, instance_seed=instance_seed, namespace="surface.target_y"))
    answer_x = str(_balanced_choice(x_labels, params=params, instance_seed=instance_seed, namespace=f"surface.answer_x:{target_y}:{extremum}"))
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.surface.values")
    cells: List[_SurfaceCell] = []
    for y_index, y_label in enumerate(y_labels):
        row_values = [int(rng.randint(25, 74)) for _ in range(int(x_count))]
        if str(y_label) == target_y:
            answer_index = list(x_labels).index(answer_x)
            if str(extremum) == "highest":
                row_values = [int(min(value, 70)) for value in row_values]
                row_values[answer_index] = int(rng.randint(86, 96))
            else:
                row_values = [int(max(value, 30)) for value in row_values]
                row_values[answer_index] = int(rng.randint(7, 16))
        for x_index, x_label in enumerate(x_labels):
            cells.append(
                _SurfaceCell(
                    cell_id=f"cell_{x_label}_{y_label}",
                    x_label=str(x_label),
                    y_label=str(y_label),
                    x_index=int(x_index),
                    y_index=int(y_index),
                    value=int(row_values[x_index]),
                )
            )
    row_values_by_x = {str(cell.x_label): int(cell.value) for cell in cells if str(cell.y_label) == target_y}
    return _Dataset(
        scene_variant="three_d_surface",
        points=(),
        surface_cells=tuple(cells),
        panels=(),
        x_axis_label="Platform",
        y_axis_label="Group",
        z_axis_label="Value",
        x_range=(0.0, float(max(1, int(x_count) - 1))),
        y_range=(0.0, float(max(1, int(y_count) - 1))),
        z_range=(0.0, 100.0),
        x_labels=tuple(x_labels),
        y_labels=tuple(y_labels),
        query=_Query(
            query_id="surface_extremum_label",
            scene_variant="three_d_surface",
            answer=str(answer_x),
            answer_type="string",
            annotation_cell_ids=(f"cell_{answer_x}_{target_y}",),
            trace={
                "target_y_category": str(target_y),
                "extremum_direction": str(extremum),
                "extremum_direction_probabilities": dict(extremum_probabilities),
                "row_values_by_x": dict(row_values_by_x),
                "x_count": int(x_count),
                "y_count": int(y_count),
            },
        ),
    )

def _dataset_series_trend(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    series_count = _balanced_int(low=_gen_int(params, "series_count_min", 4), high=_gen_int(params, "series_count_max", 6), params=params, instance_seed=instance_seed, namespace="trend.series_count")
    time_count = _balanced_int(low=_gen_int(params, "time_count_min", 5), high=_gen_int(params, "time_count_max", 7), params=params, instance_seed=instance_seed, namespace="trend.time_count")
    trend_direction, trend_probabilities = _resolve_trend(params, instance_seed=instance_seed)
    labels = _sample_labels(int(series_count), instance_seed=instance_seed, namespace="trend.series")
    answer_label = str(_balanced_choice(labels, params=params, instance_seed=instance_seed, namespace=f"trend.answer:{trend_direction}"))
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.trend.values")
    points: List[_Point3D] = []
    deltas: Dict[str, int] = {}
    for series_index, label in enumerate(labels):
        if str(label) == answer_label:
            delta = int(rng.randint(38, 55)) * (1 if str(trend_direction) == "increase" else -1)
        else:
            delta = int(rng.randint(-24, 28))
            if str(trend_direction) == "increase":
                delta = min(int(delta), 24)
            else:
                delta = max(int(delta), -24)
        start_low = 18 if delta >= 0 else 58
        start_high = 38 if delta >= 0 else 82
        start = int(rng.randint(start_low, start_high))
        end = max(5, min(96, int(start) + int(delta)))
        deltas[str(label)] = int(end) - int(start)
        for time_index in range(int(time_count)):
            t = float(time_index) / float(max(1, int(time_count) - 1))
            value = float(start) + (float(end - start) * t) + rng.uniform(-3.0, 3.0)
            points.append(
                _Point3D(
                    point_id=f"series_{label}_{time_index}",
                    label=str(label),
                    x_value=float(time_index),
                    y_value=float(series_index),
                    z_value=max(0.0, min(100.0, float(value))),
                    color_rgb=_PALETTE[int(series_index) % len(_PALETTE)],
                )
            )
    return _Dataset(
        scene_variant="three_d_scatter",
        points=tuple(points),
        surface_cells=(),
        panels=(),
        x_axis_label="Year",
        y_axis_label="Series",
        z_axis_label="Value",
        x_range=(0.0, float(max(1, int(time_count) - 1))),
        y_range=(0.0, float(max(1, int(series_count) - 1))),
        z_range=(0.0, 100.0),
        x_labels=tuple(str(value) for value in _TIME_POOL[: int(time_count)]),
        y_labels=tuple(labels),
        query=_Query(
            query_id="series_trend_label",
            scene_variant="three_d_scatter",
            answer=str(answer_label),
            answer_type="string",
            annotation_point_ids=(
                f"series_{answer_label}_0",
                f"series_{answer_label}_{int(time_count) - 1}",
            ),
            trace={
                "trend_direction": str(trend_direction),
                "trend_direction_probabilities": dict(trend_probabilities),
                "series_count": int(series_count),
                "time_count": int(time_count),
                "deltas_by_series": dict(deltas),
            },
        ),
    )

def _dataset_panel_variation(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    panel_count = _balanced_int(low=_gen_int(params, "panel_count_min", 4), high=_gen_int(params, "panel_count_max", 6), params=params, instance_seed=instance_seed, namespace="panel.panel_count")
    time_count = _balanced_int(low=5, high=7, params=params, instance_seed=instance_seed, namespace="panel.time_count")
    labels, panel_label_meta = _sample_panel_labels(
        int(panel_count),
        params=params,
        instance_seed=instance_seed,
        reserved_labels=("Step", "Band", "Value"),
    )
    answer_label = str(_balanced_choice(labels, params=params, instance_seed=instance_seed, namespace="panel.answer"))
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.panel.values")
    panels: List[_Panel3D] = []
    ranges: Dict[str, int] = {}
    for index, label in enumerate(labels):
        if str(label) == answer_label:
            low = int(rng.randint(8, 20))
            high = int(rng.randint(80, 96))
        else:
            low = int(rng.randint(22, 42))
            high = int(rng.randint(55, 74))
        values = [int(round(low + (high - low) * (step / max(1, time_count - 1)) + rng.uniform(-5, 5))) for step in range(int(time_count))]
        if str(label) == answer_label:
            values[0] = low
            values[-1] = high
        values = [max(0, min(100, int(value))) for value in values]
        ranges[str(label)] = int(max(values) - min(values))
        panels.append(_Panel3D(panel_label=str(label), values=tuple(values), color_rgb=_PALETTE[int(index) % len(_PALETTE)]))
    return _Dataset(
        scene_variant="three_d_small_multiples",
        points=(),
        surface_cells=(),
        panels=tuple(panels),
        x_axis_label="Step",
        y_axis_label="Band",
        z_axis_label="Value",
        x_range=(0.0, float(max(1, int(time_count) - 1))),
        y_range=(0.0, 1.0),
        z_range=(0.0, 100.0),
        x_labels=(),
        y_labels=(),
        query=_Query(
            query_id="panel_variation_label",
            scene_variant="three_d_small_multiples",
            answer=str(answer_label),
            answer_type="string",
            annotation_panel_labels=(str(answer_label),),
            trace={
                "panel_count": int(panel_count),
                "time_count": int(time_count),
                "ranges_by_panel": dict(ranges),
                **dict(panel_label_meta),
            },
        ),
    )

def _build_dataset(query_id: str, params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    if str(query_id) == "reference_nearest_label":
        return _dataset_reference_nearest(params, instance_seed=int(instance_seed))
    if str(query_id) == "surface_extremum_label":
        return _dataset_surface_extremum(params, instance_seed=int(instance_seed))
    if str(query_id) == "series_trend_label":
        return _dataset_series_trend(params, instance_seed=int(instance_seed))
    if str(query_id) == "panel_variation_label":
        return _dataset_panel_variation(params, instance_seed=int(instance_seed))
    raise ValueError(f"unsupported 3D chart query id: {query_id}")
