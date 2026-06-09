"""Dataset construction for scatter cluster chart tasks."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from .cluster_common import (
    TASK_ID,
    RGB,
    _AREA_RANK_BY_QUERY_ID,
    _AREA_RANK_PHRASE_BY_QUERY_ID,
    _AreaEnvelope,
    _Cluster,
    _Dataset,
    _OptionMarker,
    _Point,
    _Query,
    _clamp,
    _gen_float,
    _palette,
)

def _cluster_centers(labels: Sequence[str], *, rng: Any) -> Dict[str, Tuple[float, float]]:
    base = [
        (31.0, 34.0),
        (32.0, 66.0),
        (50.0, 48.0),
        (68.0, 34.0),
        (69.0, 66.0),
        (50.0, 78.0),
        (82.0, 48.0),
        (18.0, 48.0),
    ]
    return {
        str(label): (
            _clamp(float(center[0]) + rng.uniform(-3.0, 3.0), 14.0, 86.0),
            _clamp(float(center[1]) + rng.uniform(-3.0, 3.0), 26.0, 80.0),
        )
        for label, center in zip([str(item) for item in labels], base)
    }


def _make_points(
    *,
    cluster_label: str,
    center: Tuple[float, float],
    slope: float,
    spread_x: float,
    spread_y: float,
    count: int,
    instance_seed: int,
    x_jitter: float = 0.9,
    y_jitter: float = 0.9,
    y_jitter_scale: float = 0.28,
    flat_y_jitter_scale: float = 1.0,
) -> Tuple[_Point, ...]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.points.{cluster_label}")
    offsets = [((float(index) - ((float(count) - 1.0) / 2.0)) / max(1.0, (float(count) - 1.0) / 2.0)) for index in range(int(count))]
    rng.shuffle(offsets)
    points: List[_Point] = []
    for index, raw_offset in enumerate(offsets):
        x_offset = float(raw_offset) * float(spread_x) + rng.uniform(-float(x_jitter), float(x_jitter))
        y_offset = (float(slope) * float(raw_offset) * float(spread_y)) + rng.uniform(-float(y_jitter), float(y_jitter)) * max(1.0, float(spread_y) * float(y_jitter_scale))
        if abs(float(slope)) < 0.12:
            y_offset += rng.uniform(-1.0, 1.0) * float(spread_y) * float(flat_y_jitter_scale)
        x_value = _clamp(float(center[0]) + x_offset, 4.0, 96.0)
        y_value = _clamp(float(center[1]) + y_offset, 4.0, 96.0)
        points.append(
            _Point(
                point_id=f"{str(cluster_label)}_{int(index):02d}",
                cluster_label=str(cluster_label),
                x_value=float(x_value),
                y_value=float(y_value),
            )
        )
    return tuple(points)


def _build_clusters(
    *,
    labels: Sequence[str],
    palette: Sequence[RGB],
    centers: Mapping[str, Tuple[float, float]],
    slopes: Mapping[str, float],
    spreads: Mapping[str, Tuple[float, float]],
    points_per_cluster: int,
    instance_seed: int,
    point_jitter_by_label: Mapping[str, Mapping[str, float]] | None = None,
    area_envelopes: Mapping[str, _AreaEnvelope] | None = None,
) -> Tuple[_Cluster, ...]:
    clusters: List[_Cluster] = []
    for index, label in enumerate(labels):
        spread = spreads[str(label)]
        slope = float(slopes[str(label)])
        center = centers[str(label)]
        jitter = dict(point_jitter_by_label.get(str(label), {})) if point_jitter_by_label else {}
        points = _make_points(
            cluster_label=str(label),
            center=center,
            slope=slope,
            spread_x=float(spread[0]),
            spread_y=float(spread[1]),
            count=int(points_per_cluster),
            instance_seed=int(instance_seed),
            x_jitter=float(jitter.get("x_jitter", 0.9)),
            y_jitter=float(jitter.get("y_jitter", 0.9)),
            y_jitter_scale=float(jitter.get("y_jitter_scale", 0.28)),
            flat_y_jitter_scale=float(jitter.get("flat_y_jitter_scale", 1.0)),
        )
        clusters.append(
            _Cluster(
                cluster_label=str(label),
                color_rgb=tuple(palette[int(index) % len(palette)]),
                center_x=float(center[0]),
                center_y=float(center[1]),
                slope=float(slope),
                spread_x=float(spread[0]),
                spread_y=float(spread[1]),
                points=tuple(points),
                area_envelope=area_envelopes.get(str(label)) if area_envelopes is not None else None,
            )
        )
    return tuple(clusters)


def _dataset_for_trend(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    labels: Sequence[str],
    answer_label: str,
    points_per_cluster: int,
    trend_direction: str,
    trend_direction_probabilities: Mapping[str, float],
) -> _Dataset:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.trend")
    centers = _cluster_centers(labels, rng=rng)
    distractor_count = max(0, len(labels) - 1)
    target_abs_slope_min = _gen_float(params, "trend_target_abs_slope_min", 1.35)
    target_abs_slope_max = max(float(target_abs_slope_min), _gen_float(params, "trend_target_abs_slope_max", 1.9))
    margin_min = _gen_float(params, "trend_slope_margin_min", 0.55)
    margin_max = max(float(margin_min), _gen_float(params, "trend_slope_margin_max", 1.1))
    same_direction_floor = _gen_float(params, "trend_same_direction_abs_slope_floor", 0.18)
    target_abs_slope = rng.uniform(float(target_abs_slope_min), float(target_abs_slope_max))
    max_margin_for_target = max(float(margin_min), float(target_abs_slope) - float(same_direction_floor))
    trend_slope_margin_target = rng.uniform(float(margin_min), min(float(margin_max), float(max_margin_for_target)))
    same_direction_peak = max(float(same_direction_floor), float(target_abs_slope) - float(trend_slope_margin_target))
    same_direction_count = rng.randint(2, 4)
    same_direction_candidates = [float(same_direction_peak)]
    for _ in range(max(0, int(same_direction_count) - 1)):
        same_direction_candidates.append(rng.uniform(0.08, max(0.09, float(same_direction_peak) - 0.08)))
    opposite_direction_count = rng.randint(3, 5)
    opposite_slope_min = _gen_float(params, "trend_opposite_abs_slope_min", 0.35)
    opposite_slope_max = max(float(opposite_slope_min), _gen_float(params, "trend_opposite_abs_slope_max", 1.2))
    opposite_direction_candidates = [rng.uniform(float(opposite_slope_min), float(opposite_slope_max)) for _ in range(int(opposite_direction_count))]
    neutral_candidates = [rng.uniform(-0.12, 0.12) for _ in range(2)]
    signed_same_direction_peak = float(same_direction_peak)
    distractor_abs_slopes = same_direction_candidates[1:] + [-float(value) for value in opposite_direction_candidates] + neutral_candidates
    if str(trend_direction) == "downward":
        signed_same_direction_peak = -float(signed_same_direction_peak)
        distractor_abs_slopes = [-value for value in distractor_abs_slopes]
    rng.shuffle(distractor_abs_slopes)
    other_slopes = [round(float(signed_same_direction_peak), 3)] + [
        round(float(value), 3) for value in distractor_abs_slopes[: max(0, int(distractor_count) - 1)]
    ]
    while len(other_slopes) < distractor_count:
        filler = rng.uniform(-float(opposite_slope_max), float(opposite_slope_max))
        same_direction_ceiling = max(0.08, float(target_abs_slope) - float(trend_slope_margin_target))
        if str(trend_direction) == "upward" and filler >= float(same_direction_ceiling):
            filler = rng.uniform(0.08, float(same_direction_ceiling))
        if str(trend_direction) == "downward" and filler <= -float(same_direction_ceiling):
            filler = -rng.uniform(0.08, float(same_direction_ceiling))
        other_slopes.append(round(float(filler), 3))
    slopes: Dict[str, float] = {}
    for label in labels:
        if str(label) == str(answer_label):
            slopes[str(label)] = round(float(target_abs_slope), 3) if str(trend_direction) == "upward" else -round(float(target_abs_slope), 3)
        else:
            slopes[str(label)] = float(other_slopes.pop())
    if str(trend_direction) == "upward":
        strongest_distractor = max(float(value) for key, value in slopes.items() if str(key) != str(answer_label))
        trend_slope_margin = float(slopes[str(answer_label)]) - strongest_distractor
    else:
        strongest_distractor = min(float(value) for key, value in slopes.items() if str(key) != str(answer_label))
        trend_slope_margin = strongest_distractor - float(slopes[str(answer_label)])
    spreads = {str(label): ((10.0, 8.2) if str(label) == str(answer_label) else (8.6, 7.4)) for label in labels}
    answer_x_jitter = _gen_float(params, "trend_answer_x_jitter", 0.45)
    answer_y_jitter = _gen_float(params, "trend_answer_y_jitter", 0.55)
    answer_y_jitter_scale = _gen_float(params, "trend_answer_y_jitter_scale", 0.16)
    distractor_x_jitter = _gen_float(params, "trend_distractor_x_jitter", 0.65)
    distractor_y_jitter = _gen_float(params, "trend_distractor_y_jitter", 0.75)
    distractor_y_jitter_scale = _gen_float(params, "trend_distractor_y_jitter_scale", 0.20)
    point_jitter = {
        str(label): {
            "x_jitter": float(answer_x_jitter) if str(label) == str(answer_label) else float(distractor_x_jitter),
            "y_jitter": float(answer_y_jitter) if str(label) == str(answer_label) else float(distractor_y_jitter),
            "y_jitter_scale": float(answer_y_jitter_scale) if str(label) == str(answer_label) else float(distractor_y_jitter_scale),
            "flat_y_jitter_scale": 0.35,
        }
        for label in labels
    }
    clusters = _build_clusters(
        labels=labels,
        palette=_palette(params),
        centers=centers,
        slopes=slopes,
        spreads=spreads,
        points_per_cluster=int(points_per_cluster),
        instance_seed=int(instance_seed),
        point_jitter_by_label=point_jitter,
    )
    return _Dataset(
        scene_variant="single_scatter",
        clusters=clusters,
        query=_Query(
            query_id="cluster_trend_direction_label",
            answer_label=str(answer_label),
            answer_type="string",
            annotation_cluster_labels=(str(answer_label),),
            trace={
                "trend_direction": str(trend_direction),
                "trend_direction_probabilities": dict(trend_direction_probabilities),
                "cluster_slopes": {str(key): round(float(value), 4) for key, value in slopes.items()},
                "trend_slope_margin": round(float(trend_slope_margin), 4),
                "target_abs_slope_range": [round(float(target_abs_slope_min), 4), round(float(target_abs_slope_max), 4)],
                "trend_slope_margin_range": [round(float(margin_min), 4), round(float(margin_max), 4)],
                "trend_slope_margin_target": round(float(trend_slope_margin_target), 4),
                "trend_point_jitter": {
                    "answer": {
                        "x_jitter": round(float(answer_x_jitter), 4),
                        "y_jitter": round(float(answer_y_jitter), 4),
                        "y_jitter_scale": round(float(answer_y_jitter_scale), 4),
                    },
                    "distractor": {
                        "x_jitter": round(float(distractor_x_jitter), 4),
                        "y_jitter": round(float(distractor_y_jitter), 4),
                        "y_jitter_scale": round(float(distractor_y_jitter_scale), 4),
                    },
                },
            },
        ),
    )


def _dataset_for_separation(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    labels: Sequence[str],
    answer_label: str,
    points_per_cluster: int,
    separation_extremum: str,
    separation_extremum_probabilities: Mapping[str, float],
) -> _Dataset:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.separation")
    label_list = [str(label) for label in labels]
    answer_index = label_list.index(str(answer_label))
    reference_label = label_list[(int(answer_index) + 2) % len(label_list)]
    remaining = [label for label in label_list if label not in {str(answer_label), str(reference_label)}]
    centers: Dict[str, Tuple[float, float]] = {str(reference_label): (50.0, 50.0)}
    if str(separation_extremum) == "closest":
        centers[str(answer_label)] = (59.0, 54.0)
        candidate_centers = [(37.0, 42.0), (44.0, 67.0), (66.0, 42.0), (67.0, 65.0), (32.0, 57.0), (58.0, 70.0)]
    else:
        centers[str(answer_label)] = (29.0, 34.0)
        candidate_centers = [(43.0, 46.0), (61.0, 43.0), (48.0, 68.0), (66.0, 62.0), (35.0, 58.0), (58.0, 32.0)]
    rng.shuffle(candidate_centers)
    for label, center in zip(remaining, candidate_centers):
        centers[str(label)] = (float(center[0]) + rng.uniform(-1.5, 1.5), float(center[1]) + rng.uniform(-1.5, 1.5))
    slopes = {str(label): 0.0 for label in labels}
    spreads = {str(label): (6.0, 6.0) for label in labels}
    clusters = _build_clusters(
        labels=labels,
        palette=_palette(params),
        centers=centers,
        slopes=slopes,
        spreads=spreads,
        points_per_cluster=int(points_per_cluster),
        instance_seed=int(instance_seed),
    )
    distances = {
        str(label): round(math.hypot(float(centers[str(label)][0]) - float(centers[str(reference_label)][0]), float(centers[str(label)][1]) - float(centers[str(reference_label)][1])), 4)
        for label in label_list
        if str(label) != str(reference_label)
    }
    return _Dataset(
        scene_variant="single_scatter",
        clusters=clusters,
        query=_Query(
            query_id="cluster_separation_extremum_label",
            answer_label=str(answer_label),
            answer_type="string",
            annotation_cluster_labels=(str(reference_label), str(answer_label)),
            trace={
                "reference_cluster_label": str(reference_label),
                "separation_extremum": str(separation_extremum),
                "separation_extremum_probabilities": dict(separation_extremum_probabilities),
                "centroid_distances_from_reference": dict(distances),
            },
        ),
    )


def _spread_metric(spread: Tuple[float, float], axis: str) -> float:
    if str(axis) == "horizontal":
        return float(spread[0])
    if str(axis) == "vertical":
        return float(spread[1])
    return math.hypot(float(spread[0]), float(spread[1]))


def _dataset_for_spread(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    labels: Sequence[str],
    answer_label: str,
    points_per_cluster: int,
    spread_axis: str,
    spread_extremum: str,
    spread_axis_probabilities: Mapping[str, float],
    spread_extremum_probabilities: Mapping[str, float],
) -> _Dataset:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.spread")
    centers = _cluster_centers(labels, rng=rng)
    other_large = [(7.2, 5.6), (5.6, 7.2), (7.0, 7.0), (6.4, 6.0), (6.0, 6.8), (7.7, 5.4), (5.4, 7.7)]
    other_small = [(4.0, 3.4), (3.4, 4.0), (4.2, 3.6), (3.6, 4.2), (4.0, 4.0), (3.2, 3.8), (4.3, 3.2)]
    rng.shuffle(other_large)
    rng.shuffle(other_small)
    spreads: Dict[str, Tuple[float, float]] = {}
    for label in labels:
        if str(label) == str(answer_label):
            if str(spread_extremum) == "largest":
                if str(spread_axis) == "horizontal":
                    spreads[str(label)] = (13.5, 2.9)
                elif str(spread_axis) == "vertical":
                    spreads[str(label)] = (2.9, 13.5)
                else:
                    spreads[str(label)] = (10.2, 10.2)
            else:
                if str(spread_axis) == "horizontal":
                    spreads[str(label)] = (2.0, 4.2)
                elif str(spread_axis) == "vertical":
                    spreads[str(label)] = (4.2, 2.0)
                else:
                    spreads[str(label)] = (2.4, 2.4)
        else:
            spreads[str(label)] = tuple(other_small.pop() if str(spread_extremum) == "largest" else other_large.pop())
    slopes = {str(label): 0.0 for label in labels}
    clusters = _build_clusters(
        labels=labels,
        palette=_palette(params),
        centers=centers,
        slopes=slopes,
        spreads=spreads,
        points_per_cluster=int(points_per_cluster),
        instance_seed=int(instance_seed),
    )
    metrics = {str(label): round(_spread_metric(spreads[str(label)], str(spread_axis)), 4) for label in labels}
    return _Dataset(
        scene_variant="single_scatter",
        clusters=clusters,
        query=_Query(
            query_id="cluster_spread_extremum_label",
            answer_label=str(answer_label),
            answer_type="string",
            annotation_cluster_labels=(str(answer_label),),
            trace={
                "spread_axis": str(spread_axis),
                "spread_extremum": str(spread_extremum),
                "spread_axis_probabilities": dict(spread_axis_probabilities),
                "spread_extremum_probabilities": dict(spread_extremum_probabilities),
                "cluster_spread_metrics": dict(metrics),
            },
        ),
    )


def _make_area_envelope_points(
    *,
    cluster_label: str,
    envelope: _AreaEnvelope,
    count: int,
    instance_seed: int,
) -> Tuple[_Point, ...]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.area_points.{cluster_label}")
    angle = math.radians(float(envelope.angle_degrees))
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    points: List[_Point] = []
    for index in range(int(count)):
        theta = (2.0 * math.pi * (float(index) / max(1.0, float(count)))) + rng.uniform(-0.42, 0.42)
        radius_scale = math.sqrt(rng.uniform(0.10, 0.86))
        local_x = float(envelope.radius_x) * radius_scale * math.cos(theta)
        local_y = float(envelope.radius_y) * radius_scale * math.sin(theta)
        x_value = _clamp(float(envelope.center_x) + local_x * cos_a - local_y * sin_a, 3.0, 97.0)
        y_value = _clamp(float(envelope.center_y) + local_x * sin_a + local_y * cos_a, 3.0, 97.0)
        points.append(
            _Point(
                point_id=f"{str(cluster_label)}_{int(index):02d}",
                cluster_label=str(cluster_label),
                x_value=float(x_value),
                y_value=float(y_value),
            )
        )
    return tuple(points)


def _nearest_rank_relative_gap(metrics: Mapping[str, float], *, answer_label: str) -> float:
    ordered = sorted(metrics, key=lambda label: (-float(metrics[str(label)]), str(label)))
    answer_index = ordered.index(str(answer_label))
    neighbors: List[str] = []
    if answer_index > 0:
        neighbors.append(str(ordered[int(answer_index) - 1]))
    if answer_index < len(ordered) - 1:
        neighbors.append(str(ordered[int(answer_index) + 1]))
    if not neighbors:
        return 0.0
    answer_value = float(metrics[str(answer_label)])
    nearest_value = min(
        (float(metrics[str(label)]) for label in neighbors),
        key=lambda value: abs(value - answer_value),
    )
    return abs(float(answer_value) - float(nearest_value)) / max(abs(float(answer_value)), abs(float(nearest_value)), 1e-9)


def _dataset_for_area_rank(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    labels: Sequence[str],
    points_per_cluster: int,
    query_id: str,
) -> _Dataset:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.area_rank")
    centers = _cluster_centers(labels, rng=rng)
    label_list = [str(label) for label in labels]
    base_min = _gen_float(params, "area_rank_product_min", 34.0)
    base_max = max(float(base_min), _gen_float(params, "area_rank_product_max", 42.0))
    gap_min = max(0.04, _gen_float(params, "area_rank_adjacent_gap_min", 0.12))
    gap_max = max(float(gap_min), _gen_float(params, "area_rank_adjacent_gap_max", 0.20))
    max_ratio = max(1.2, _gen_float(params, "area_rank_max_min_ratio", 2.8))
    if len(label_list) > 1:
        gap_max = min(float(gap_max), max(0.06, float(max_ratio) ** (1.0 / float(len(label_list) - 1)) - 1.0))
    gap_min = min(float(gap_min), float(gap_max))
    products = [rng.uniform(float(base_min), float(base_max))]
    for _ in range(1, len(label_list)):
        products.append(float(products[-1]) * (1.0 + rng.uniform(float(gap_min), float(gap_max))))
    products = [round(float(value), 4) for value in products]
    assigned_products = list(products)
    rng.shuffle(assigned_products)
    aspect_min = max(0.45, _gen_float(params, "area_rank_aspect_ratio_min", 0.72))
    aspect_max = max(float(aspect_min), _gen_float(params, "area_rank_aspect_ratio_max", 1.38))
    angle_min = _gen_float(params, "area_rank_angle_min_degrees", -38.0)
    angle_max = max(float(angle_min), _gen_float(params, "area_rank_angle_max_degrees", 38.0))
    area_envelopes: Dict[str, _AreaEnvelope] = {}
    clusters: List[_Cluster] = []
    palette = _palette(params)
    for index, label in enumerate(label_list):
        area_product = float(assigned_products[int(index)])
        aspect = rng.uniform(float(aspect_min), float(aspect_max))
        radius_x = math.sqrt(float(area_product) * float(aspect))
        radius_y = math.sqrt(float(area_product) / float(aspect))
        center_x, center_y = centers[str(label)]
        envelope = _AreaEnvelope(
            center_x=float(center_x),
            center_y=float(center_y),
            radius_x=float(radius_x),
            radius_y=float(radius_y),
            angle_degrees=rng.uniform(float(angle_min), float(angle_max)),
            area_value=round(float(area_product), 4),
        )
        area_envelopes[str(label)] = envelope
        points = _make_area_envelope_points(
            cluster_label=str(label),
            envelope=envelope,
            count=int(points_per_cluster),
            instance_seed=int(instance_seed),
        )
        clusters.append(
            _Cluster(
                cluster_label=str(label),
                color_rgb=tuple(palette[int(index) % len(palette)]),
                center_x=float(center_x),
                center_y=float(center_y),
                slope=0.0,
                spread_x=float(radius_x),
                spread_y=float(radius_y),
                points=tuple(points),
                area_envelope=envelope,
            )
        )
    metrics = {str(label): float(area_envelopes[str(label)].area_value) for label in label_list}
    largest_to_smallest = sorted(label_list, key=lambda label: (-float(metrics[str(label)]), str(label)))
    smallest_to_largest = list(reversed(largest_to_smallest))
    rank_name = str(_AREA_RANK_BY_QUERY_ID[str(query_id)])
    if rank_name == "second_largest":
        answer_label = str(largest_to_smallest[1])
    elif rank_name == "smallest":
        answer_label = str(smallest_to_largest[0])
    else:
        answer_label = str(largest_to_smallest[0])
    return _Dataset(
        scene_variant="area_envelope_scatter",
        clusters=tuple(clusters),
        query=_Query(
            query_id=str(query_id),
            answer_label=str(answer_label),
            answer_type="string",
            annotation_cluster_labels=(str(answer_label),),
            trace={
                "area_rank": str(rank_name),
                "area_rank_phrase": str(_AREA_RANK_PHRASE_BY_QUERY_ID[str(query_id)]),
                "cluster_area_metrics": {str(label): round(float(value), 4) for label, value in metrics.items()},
                "cluster_area_order_largest_to_smallest": list(largest_to_smallest),
                "cluster_area_nearest_relative_gap": round(
                    _nearest_rank_relative_gap(metrics, answer_label=str(answer_label)),
                    4,
                ),
                "area_rank_product_range": [round(float(base_min), 4), round(float(base_max), 4)],
                "area_rank_adjacent_gap_range": [round(float(gap_min), 4), round(float(gap_max), 4)],
                "area_rank_max_min_ratio": round(float(max_ratio), 4),
            },
        ),
    )


def _cluster_centroid(cluster: _Cluster) -> Tuple[float, float]:
    x_values = [float(point.x_value) for point in cluster.points]
    y_values = [float(point.y_value) for point in cluster.points]
    return (sum(x_values) / max(1, len(x_values)), sum(y_values) / max(1, len(y_values)))


def _dataset_for_centroid_option(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    labels: Sequence[str],
    target_cluster_label: str,
    points_per_cluster: int,
    answer_option_label: str,
    option_labels: Sequence[str],
) -> _Dataset:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.centroid_option")
    centers = _cluster_centers(labels, rng=rng)
    slopes = {str(label): rng.uniform(-0.18, 0.18) for label in labels}
    spreads = {
        str(label): (
            rng.uniform(6.2, 8.8) if str(label) == str(target_cluster_label) else rng.uniform(5.4, 8.0),
            rng.uniform(6.2, 8.8) if str(label) == str(target_cluster_label) else rng.uniform(5.4, 8.0),
        )
        for label in labels
    }
    clusters = _build_clusters(
        labels=labels,
        palette=_palette(params),
        centers=centers,
        slopes=slopes,
        spreads=spreads,
        points_per_cluster=int(points_per_cluster),
        instance_seed=int(instance_seed),
    )
    target_cluster = next(cluster for cluster in clusters if str(cluster.cluster_label) == str(target_cluster_label))
    centroid_x, centroid_y = _cluster_centroid(target_cluster)
    answer_radius_min = _gen_float(params, "centroid_option_answer_radius_min", 1.2)
    answer_radius_max = max(float(answer_radius_min), _gen_float(params, "centroid_option_answer_radius_max", 2.8))
    distractor_radius_min = _gen_float(params, "centroid_option_distractor_radius_min", 8.0)
    distractor_radius_max = max(float(distractor_radius_min), _gen_float(params, "centroid_option_distractor_radius_max", 17.0))
    minimum_margin = _gen_float(params, "centroid_option_distance_margin_min", 4.0)
    angle_offset = rng.uniform(0.0, 2.0 * math.pi)
    answer_angle = angle_offset + rng.uniform(-0.18, 0.18)
    answer_radius = rng.uniform(float(answer_radius_min), float(answer_radius_max))
    option_positions: Dict[str, Tuple[float, float]] = {
        str(answer_option_label): (
            _clamp(float(centroid_x) + math.cos(answer_angle) * float(answer_radius), 4.0, 96.0),
            _clamp(float(centroid_y) + math.sin(answer_angle) * float(answer_radius), 4.0, 96.0),
        )
    }
    active_option_labels = tuple(str(label) for label in option_labels)
    distractor_labels = [label for label in active_option_labels if str(label) != str(answer_option_label)]
    for index, option_label in enumerate(distractor_labels):
        angle = angle_offset + (2.0 * math.pi * (float(index) + 1.0) / float(len(active_option_labels))) + rng.uniform(-0.22, 0.22)
        radius = rng.uniform(float(distractor_radius_min), float(distractor_radius_max))
        option_positions[str(option_label)] = (
            _clamp(float(centroid_x) + math.cos(angle) * float(radius), 4.0, 96.0),
            _clamp(float(centroid_y) + math.sin(angle) * float(radius), 4.0, 96.0),
        )
    distances = {
        str(label): math.hypot(float(position[0]) - float(centroid_x), float(position[1]) - float(centroid_y))
        for label, position in option_positions.items()
    }
    answer_distance = float(distances[str(answer_option_label)])
    min_distractor_distance = min(float(value) for label, value in distances.items() if str(label) != str(answer_option_label))
    if min_distractor_distance <= answer_distance + float(minimum_margin):
        raise ValueError("centroid option markers do not satisfy the unique-answer distance margin")
    option_markers = tuple(
        _OptionMarker(option_label=str(label), x_value=float(option_positions[str(label)][0]), y_value=float(option_positions[str(label)][1]))
        for label in active_option_labels
    )
    return _Dataset(
        scene_variant="single_scatter",
        clusters=clusters,
        option_markers=option_markers,
        query=_Query(
            query_id="centroid_option_selection_label",
            answer_label=str(answer_option_label),
            answer_type="option_letter",
            annotation_cluster_labels=(str(target_cluster_label),),
            trace={
                "target_cluster_label": str(target_cluster_label),
                "target_cluster_centroid": [round(float(centroid_x), 4), round(float(centroid_y), 4)],
                "option_count": int(len(active_option_labels)),
                "option_count_support": [4, 6],
                "option_labels": list(active_option_labels),
                "option_positions": {
                    str(label): [round(float(position[0]), 4), round(float(position[1]), 4)]
                    for label, position in option_positions.items()
                },
                "option_distances_to_centroid": {
                    str(label): round(float(distance), 4)
                    for label, distance in distances.items()
                },
                "minimum_distance_margin": round(float(minimum_margin), 4),
            },
        ),
    )
