"""Neutral dashboard scene sampling primitives."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from trace.core.seed import spawn_rng
from trace.tasks.shared.config_defaults import resolve_required_int_bounds
from trace.tasks.charts.shared.label_assets import resolve_chart_category_labels, resolve_chart_panel_labels, validate_chart_label_namespaces

from .defaults import generation_default, resolve_render_params
from .metrics import balanced_support_choice, join_labels
from .state import Category, DashboardBaseSample, Panel, PANEL_KIND_NAMES, SCENE_NAMESPACE, SUPPORTED_PANEL_KINDS, RenderParams


def sample_categories(params: Mapping[str, Any], *, instance_seed: int, render_params: RenderParams) -> Tuple[Category, ...]:
    category_min, category_max = resolve_required_int_bounds(
        params,
        {},
        min_key="category_count_min",
        max_key="category_count_max",
        fallback_min=int(generation_default("category_count_min", 5)),
        fallback_max=int(generation_default("category_count_max", 10)),
        context=SCENE_NAMESPACE,
    )
    if int(category_min) < 4:
        raise ValueError("category_count_min must be at least 4 for dashboard charts")
    category_max = min(int(category_max), len(render_params.category_palette_rgb))
    if int(category_min) > int(category_max):
        raise ValueError("category_count_min exceeds feasible palette/label support")
    explicit_category_count = params.get("category_count")
    if explicit_category_count is not None:
        category_count = int(explicit_category_count)
        if category_count < int(category_min) or category_count > int(category_max):
            raise ValueError("category_count must be within category_count_min..category_count_max")
    else:
        category_count = balanced_support_choice(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.category_count",
            support=tuple(range(int(category_min), int(category_max) + 1)),
        )
    rng = spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.categories")
    labels = list(resolve_chart_category_labels(rng, count=int(category_count), min_chars=2, max_chars=8, allow_spaces=False).labels)
    color_pool = list(render_params.category_palette_rgb)
    rng.shuffle(color_pool)
    return tuple(
        Category(category_id=f"cat_{index}", label=str(labels[index]), color_rgb=tuple(color_pool[index]))
        for index in range(int(category_count))
    )


def sample_panel_title_labels(params: Mapping[str, Any], *, count: int, instance_seed: int, namespace: str, reserved_labels: Sequence[str] = ()) -> Tuple[Tuple[str, ...], Dict[str, Any]]:
    """Sample compact unique labels for dashboard panel titles."""

    resolved = resolve_chart_panel_labels(
        spawn_rng(int(instance_seed), str(namespace)),
        count=int(count),
        min_chars=2,
        max_chars=10,
        allow_spaces=False,
        variant_weights=params.get(
            "panel_label_variant_weights",
            generation_default("panel_label_variant_weights", {"named_compact": 1.0, "report_topics": 1.0, "technical_topics": 1.0, "condition_labels": 0.75, "temporal_sequence": 0.25}),
        ),
        reserved_labels=reserved_labels,
    )
    collision_check = validate_chart_label_namespaces(
        panel_labels=resolved.labels,
        other_label_groups={"category_labels": tuple(str(label) for label in reserved_labels)},
        context="dashboard panel titles",
    )
    return tuple(str(label) for label in resolved.labels), {
        "panel_label_resolution": {
            "label_variant": str(resolved.label_variant),
            "label_pool_kind": str(resolved.label_pool_kind),
            "label_source_kind": str(resolved.label_source_kind),
            "label_bucket": str(resolved.label_bucket),
            "label_manifest": str(resolved.label_manifest),
            "label_filter": dict(resolved.label_filter),
            "label_bucket_probabilities": dict(resolved.label_bucket_probabilities),
        },
        "panel_label_collision_check": dict(collision_check),
    }


def sample_panels(params: Mapping[str, Any], *, instance_seed: int, categories: Sequence[Category]) -> Tuple[Tuple[Panel, ...], Dict[str, Any]]:
    """Sample panel titles, chart kinds, and values while category labels stay shared."""

    panel_count_min, panel_count_max = resolve_required_int_bounds(
        params,
        {},
        min_key="panel_count_min",
        max_key="panel_count_max",
        fallback_min=int(generation_default("panel_count_min", 4)),
        fallback_max=int(generation_default("panel_count_max", 9)),
        context=SCENE_NAMESPACE,
    )
    if int(panel_count_min) < 2:
        raise ValueError("panel_count_min must be at least 2")
    explicit_panel_count = params.get("panel_count")
    if explicit_panel_count is not None:
        panel_count = int(explicit_panel_count)
        if panel_count < int(panel_count_min) or panel_count > int(panel_count_max):
            raise ValueError("panel_count must be within panel_count_min..panel_count_max")
    else:
        panel_count = balanced_support_choice(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.panel_count",
            support=tuple(range(int(panel_count_min), int(panel_count_max) + 1)),
        )
    rng = spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.panels")
    kind_weights = params.get("panel_kind_weights", generation_default("panel_kind_weights", {kind: 1.0 for kind in SUPPORTED_PANEL_KINDS}))
    if not isinstance(kind_weights, Mapping):
        raise ValueError("panel_kind_weights must be a mapping")
    available_kinds = [kind for kind in SUPPORTED_PANEL_KINDS if float(kind_weights.get(kind, 0.0)) > 0.0]
    if not available_kinds:
        raise ValueError("panel_kind_weights leaves no supported panel kinds")
    category_labels = tuple(str(category.label) for category in categories)
    panel_labels, panel_label_meta = sample_panel_title_labels(
        params,
        count=int(panel_count),
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.panel_titles",
        reserved_labels=category_labels,
    )
    value_min = int(params.get("value_min", generation_default("value_min", 12)))
    value_max = int(params.get("value_max", generation_default("value_max", 92)))
    panels: list[Panel] = []
    for index in range(int(panel_count)):
        kind = str(available_kinds[int(rng.randrange(len(available_kinds)))])
        panel_name = f"{panel_labels[index]} {PANEL_KIND_NAMES.get(kind, kind).rstrip('s')}"
        values = {
            str(category.category_id): int(rng.randint(int(value_min), int(value_max)))
            for category in categories
        }
        panels.append(Panel(panel_id=f"panel_{index}", kind=str(kind), name=str(panel_name), values_by_category_id=values))
    return tuple(panels), dict(panel_label_meta)


def build_dashboard_base_sample(params: Mapping[str, Any], *, instance_seed: int) -> DashboardBaseSample:
    """Sample the shared visual dashboard before a public task binds its objective."""

    render_params = resolve_render_params({**dict(params), "_render_style_seed": int(instance_seed)})
    categories = sample_categories(params, instance_seed=int(instance_seed), render_params=render_params)
    panels, panel_label_meta = sample_panels(params, instance_seed=int(instance_seed), categories=categories)
    common_params = {
        "panel_count": int(len(panels)),
        "category_count": int(len(categories)),
        "panel_name_list": join_labels([str(panel.name) for panel in panels]),
        "panel_kind_list": join_labels([str(panel.kind) for panel in panels]),
        **dict(panel_label_meta),
    }
    return DashboardBaseSample(categories=tuple(categories), panels=tuple(panels), common_params=dict(common_params))


__all__ = [
    "build_dashboard_base_sample",
    "sample_categories",
    "sample_panel_title_labels",
    "sample_panels",
]
