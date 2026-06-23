"""Sampling helpers for scatter-facet-grid chart scenes."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from trace.core.sampling import normalize_positive_weights, weighted_choice
from trace.core.seed import spawn_rng
from trace.tasks.charts.shared.label_assets import (
    resolve_chart_panel_labels,
    validate_chart_label_namespaces,
)

from .defaults import GEN_DEFAULTS, RENDER_DEFAULTS, gen_float, gen_int, group_default
from .state import (
    REGION_PHRASE_BY_REGION,
    SUPPORTED_LAYOUTS,
    TARGET_REGIONS,
    Dataset,
    Panel,
    Point,
    Query,
    RGB,
    SCENE_NAMESPACE,
)


def as_rgb(value: Any, fallback: RGB) -> RGB:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) < 3:
        return tuple(int(channel) for channel in fallback)
    return tuple(max(0, min(255, int(channel))) for channel in value[:3])  # type: ignore[index]


def region_bounds(region: str) -> tuple[float, float, float, float]:
    if str(region) == "upper_right":
        return (60.0, 60.0, 100.0, 100.0)
    if str(region) == "upper_left":
        return (0.0, 60.0, 40.0, 100.0)
    if str(region) == "lower_right":
        return (60.0, 0.0, 100.0, 40.0)
    if str(region) == "lower_left":
        return (0.0, 0.0, 40.0, 40.0)
    raise ValueError(f"unsupported scatter facet region: {region}")


def resolve_layout(params: Mapping[str, Any], *, instance_seed: int) -> tuple[str, int, int, dict[str, float]]:
    raw_weights = params.get("facet_layout_weights", group_default(GEN_DEFAULTS, "facet_layout_weights", {}))
    if not isinstance(raw_weights, Mapping):
        raw_weights = {}
    probabilities = normalize_positive_weights(
        {str(key): float(value) for key, value in raw_weights.items()},
        default_keys=SUPPORTED_LAYOUTS,
    )
    rng = spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.layout")
    layout_id = weighted_choice(rng, probabilities, sort_keys=True)
    rows_text, cols_text = str(layout_id).split("x", 1)
    return str(layout_id), int(rows_text), int(cols_text), dict(probabilities)


def outside_region_center(rng: Any, region: str) -> tuple[float, float]:
    if "upper" in str(region):
        y = float(rng.uniform(18.0, 42.0))
    else:
        y = float(rng.uniform(58.0, 82.0))
    if "right" in str(region):
        x = float(rng.uniform(18.0, 42.0))
    else:
        x = float(rng.uniform(58.0, 82.0))
    return x, y


def sample_point_in_panel(
    rng: Any,
    *,
    panel_label: str,
    point_id: str,
    center_x: float,
    center_y: float,
    spread: float,
    layer: str,
    x_bounds: tuple[float, float] = (2.0, 98.0),
    y_bounds: tuple[float, float] = (2.0, 98.0),
) -> Point:
    x = max(float(x_bounds[0]), min(float(x_bounds[1]), float(rng.gauss(float(center_x), float(spread)))))
    y = max(float(y_bounds[0]), min(float(y_bounds[1]), float(rng.gauss(float(center_y), float(spread)))))
    return Point(
        point_id=str(point_id),
        panel_label=str(panel_label),
        x_value=float(x),
        y_value=float(y),
        layer=str(layer),
    )


def panel_density_score(*, target_point_count: int, target_spread: float) -> float:
    return float(target_point_count) / max(1.0, float(target_spread) ** 2)


def density_profile_scores(rng: Any, *, panel_count: int, answer_index: int, params: Mapping[str, Any]) -> list[float]:
    gap_min = gen_float(params, "facet_density_winner_gap_min", 0.16)
    gap_max = gen_float(params, "facet_density_winner_gap_max", 0.28)
    runner_score = 1.0 / (1.0 + float(rng.uniform(gap_min, gap_max)))
    scores = [float(rng.uniform(0.42, min(0.74, runner_score - 0.06))) for _ in range(int(panel_count))]
    scores[int(answer_index)] = 1.0
    runner_candidates = [index for index in range(int(panel_count)) if int(index) != int(answer_index)]
    runner_index = int(rng.choice(runner_candidates))
    scores[runner_index] = float(runner_score)
    return scores


def build_dataset(params: Mapping[str, Any], *, instance_seed: int, target_region: str) -> Dataset:
    """Sample one facet grid with a unique densest panel in the requested quadrant."""

    if str(target_region) not in TARGET_REGIONS:
        raise ValueError(f"unsupported scatter facet target region: {target_region}")

    layout_id, rows, cols, layout_probabilities = resolve_layout(params, instance_seed=int(instance_seed))
    capacity = int(rows) * int(cols)
    panel_min = max(1, gen_int(params, "facet_panel_count_min", 6))
    panel_max = max(panel_min, gen_int(params, "facet_panel_count_max", 12))
    empty_slot_max = int(params.get("facet_layout_empty_slot_max", group_default(GEN_DEFAULTS, "facet_layout_empty_slot_max", 2)))
    low = max(panel_min, min(capacity, capacity - max(0, empty_slot_max)))
    high = min(panel_max, capacity)
    if low > high:
        low = high

    rng = spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.dataset")
    panel_count = int(rng.randint(int(low), int(high)))
    x0, y0, x1, y1 = region_bounds(str(target_region))
    labels_resolution = resolve_chart_panel_labels(
        rng,
        count=int(panel_count),
        min_chars=int(params.get("facet_label_min_chars", group_default(GEN_DEFAULTS, "facet_label_min_chars", 3))),
        max_chars=int(params.get("facet_label_max_chars", group_default(GEN_DEFAULTS, "facet_label_max_chars", 10))),
        allow_spaces=bool(params.get("facet_label_allow_spaces", group_default(GEN_DEFAULTS, "facet_label_allow_spaces", False))),
        variant_weights=params.get(
            "panel_label_variant_weights",
            group_default(
                GEN_DEFAULTS,
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
    )
    labels = tuple(str(label) for label in labels_resolution.labels)
    panel_label_collision_check = validate_chart_label_namespaces(
        panel_labels=labels,
        other_label_groups={},
        context="scatter facet-grid panel labels",
    )
    answer_index = int(rng.randrange(int(panel_count)))
    density_shape_scores = density_profile_scores(
        rng,
        panel_count=int(panel_count),
        answer_index=int(answer_index),
        params=params,
    )

    palette_raw = params.get("facet_palette_rgb", group_default(RENDER_DEFAULTS, "facet_palette_rgb", ()))
    palette = (
        tuple(as_rgb(value, (79, 103, 185)) for value in palette_raw)
        if isinstance(palette_raw, Sequence) and not isinstance(palette_raw, (str, bytes))
        else ()
    )
    if not palette:
        palette = ((79, 103, 185), (173, 73, 126), (52, 133, 91), (210, 128, 44), (113, 82, 171), (48, 145, 165))

    background_min = gen_int(params, "facet_background_points_min", 28)
    background_max = max(background_min, gen_int(params, "facet_background_points_max", 42))
    distractor_min = gen_int(params, "facet_distractor_points_min", 10)
    distractor_max = max(distractor_min, gen_int(params, "facet_distractor_points_max", 18))
    panels: list[Panel] = []
    for index, label in enumerate(labels):
        shape_score = float(density_shape_scores[int(index)])
        target_count = int(round(18.0 + (8.0 * shape_score)))
        target_spread = float(5.0 + (2.4 * (1.0 - shape_score)))
        center_x = float(rng.uniform(x0 + 11.0, x1 - 11.0))
        center_y = float(rng.uniform(y0 + 11.0, y1 - 11.0))
        background_points = tuple(
            Point(
                point_id=f"{label}.bg{point_index}",
                panel_label=str(label),
                x_value=float(rng.uniform(2.0, 98.0)),
                y_value=float(rng.uniform(2.0, 98.0)),
                layer="background",
            )
            for point_index in range(int(rng.randint(background_min, background_max)))
        )
        target_points = tuple(
            sample_point_in_panel(
                rng,
                panel_label=str(label),
                point_id=f"{label}.target{point_index}",
                center_x=center_x,
                center_y=center_y,
                spread=target_spread,
                layer="target",
                x_bounds=(float(x0) + 2.0, float(x1) - 2.0),
                y_bounds=(float(y0) + 2.0, float(y1) - 2.0),
            )
            for point_index in range(int(target_count))
        )
        distractor_center_x, distractor_center_y = outside_region_center(rng, str(target_region))
        distractor_points = tuple(
            sample_point_in_panel(
                rng,
                panel_label=str(label),
                point_id=f"{label}.dist{point_index}",
                center_x=distractor_center_x,
                center_y=distractor_center_y,
                spread=float(rng.uniform(5.8, 8.2)),
                layer="distractor",
            )
            for point_index in range(int(rng.randint(distractor_min, distractor_max)))
        )
        panels.append(
            Panel(
                label=str(label),
                color_rgb=tuple(palette[int(index) % len(palette)]),
                background_points=tuple(background_points),
                target_points=tuple(target_points),
                distractor_points=tuple(distractor_points),
                target_density_score=panel_density_score(target_point_count=int(target_count), target_spread=float(target_spread)),
                target_point_count=int(target_count),
                target_spread=float(target_spread),
            )
        )

    density_by_label = {str(panel.label): float(panel.target_density_score) for panel in panels}
    answer_label = max(sorted(density_by_label), key=lambda label: (density_by_label[label], label))
    if str(answer_label) != str(labels[int(answer_index)]):
        raise RuntimeError("scatter facet density construction failed to keep unique answer")
    ordered = sorted(density_by_label, key=lambda label: (-density_by_label[label], label))
    winner_gap = (
        (density_by_label[ordered[0]] - density_by_label[ordered[1]]) / max(1e-9, density_by_label[ordered[0]])
        if len(ordered) > 1
        else 1.0
    )
    query_trace = {
        "target_region": str(target_region),
        "target_region_phrase": str(REGION_PHRASE_BY_REGION[str(target_region)]),
        "density_by_panel_label": {str(label): round(float(value), 5) for label, value in density_by_label.items()},
        "density_order_high_to_low": list(ordered),
        "density_winner_relative_gap": round(float(winner_gap), 5),
        "panel_count": int(panel_count),
        "layout_id": str(layout_id),
        "layout_rows": int(rows),
        "layout_cols": int(cols),
        "layout_probabilities": dict(layout_probabilities),
        "panel_label_resolution": {
            key: list(value) if isinstance(value, tuple) else dict(value) if isinstance(value, Mapping) else value
            for key, value in dict(labels_resolution.__dict__).items()
        },
        "panel_label_collision_check": dict(panel_label_collision_check),
    }
    answer_panel = next(panel for panel in panels if str(panel.label) == str(answer_label))
    return Dataset(
        panels=tuple(panels),
        query=Query(
            target_region=str(target_region),
            answer_label=str(answer_label),
            annotation_point_ids=tuple(str(point.point_id) for point in answer_panel.target_points),
            trace=dict(query_trace),
        ),
        rows=int(rows),
        cols=int(cols),
        layout_id=str(layout_id),
        label_resolution=labels_resolution,
    )


__all__ = ["as_rgb", "build_dataset", "region_bounds", "resolve_layout"]
