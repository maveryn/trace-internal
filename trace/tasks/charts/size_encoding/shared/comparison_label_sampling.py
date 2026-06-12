"""Dataset and query sampling for size-encoded chart comparison tasks."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from .....core.seed import spawn_rng
from ....shared.config_defaults import group_default, resolve_required_int_bounds
from ...shared.label_assets import (
    resolve_chart_category_labels,
    resolve_chart_entity_labels,
    resolve_chart_panel_labels,
    validate_chart_label_namespaces,
)
from .comparison_label_common import TASK_ID, _GEN_DEFAULTS, _Dataset, _Item, _Query, _resolve_int

def _items_by_category(items: Sequence[_Item]) -> Dict[str, List[_Item]]:
    grouped: Dict[str, List[_Item]] = {}
    for item in items:
        grouped.setdefault(str(item.category), []).append(item)
    return grouped

def _choose_index(length: int, *, params: Mapping[str, Any], instance_seed: int, namespace: str) -> int:
    if int(length) <= 0:
        raise ValueError(f"empty support for {namespace}")
    if params.get("_sample_cursor") is not None:
        return abs(int(params["_sample_cursor"])) % int(length)
    rng = spawn_rng(int(instance_seed), str(namespace))
    return int(rng.randrange(0, int(length)))

def _extreme(items: Sequence[_Item], direction: str) -> Tuple[_Item, int]:
    ordered = sorted(items, key=lambda item: (int(item.value), str(item.label)))
    if str(direction) == "largest":
        winner = ordered[-1]
        runner_up = ordered[-2]
    elif str(direction) == "smallest":
        winner = ordered[0]
        runner_up = ordered[1]
    else:
        raise ValueError(f"unsupported extremum direction: {direction}")
    return winner, abs(int(winner.value) - int(runner_up.value))

def _outside_extreme_count(*, items: Sequence[_Item], winner: _Item, direction: str) -> int:
    if str(direction) == "largest":
        return sum(1 for item in items if str(item.category) != str(winner.category) and int(item.value) > int(winner.value))
    if str(direction) == "smallest":
        return sum(1 for item in items if str(item.category) != str(winner.category) and int(item.value) < int(winner.value))
    raise ValueError(f"unsupported extremum direction: {direction}")

def _sample_categories(*, count: int, instance_seed: int) -> Tuple[str, ...]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.categories")
    values = resolve_chart_category_labels(
        rng,
        count=int(count),
        min_chars=2,
        max_chars=8,
        allow_spaces=False,
    ).labels
    return tuple(str(value) for value in values)

def _sample_labels(*, count: int, instance_seed: int) -> Tuple[str, ...]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.item_labels")
    values = resolve_chart_entity_labels(
        rng,
        count=int(count),
        min_chars=2,
        max_chars=6,
        allow_spaces=False,
    ).labels
    return tuple(str(value) for value in values)

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

def _panel_labels(
    panel_count: int,
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    reserved_labels: Sequence[str],
) -> Tuple[Tuple[str, ...], Dict[str, Any]]:
    if int(panel_count) <= 1:
        collision_check = validate_chart_label_namespaces(
            panel_labels=("Overall",),
            other_label_groups={"category_labels": tuple(str(label) for label in reserved_labels)},
            context="size-encoding panel labels",
        )
        return ("Overall",), {"panel_label_collision_check": dict(collision_check)}
    resolved = resolve_chart_panel_labels(
        spawn_rng(int(instance_seed), f"{TASK_ID}.panel_labels"),
        count=int(panel_count),
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
                    "temporal_sequence": 0.5,
                    "report_topics": 0.5,
                },
            ),
        ),
        reserved_labels=tuple(str(label) for label in reserved_labels),
    )
    collision_check = validate_chart_label_namespaces(
        panel_labels=resolved.labels,
        other_label_groups={"category_labels": tuple(str(label) for label in reserved_labels)},
        context="size-encoding panel labels",
    )
    return tuple(str(label) for label in resolved.labels), {
        "panel_label_resolution": _resolved_label_metadata(resolved),
        "panel_label_collision_check": dict(collision_check),
    }

def _sample_items(
    *,
    categories: Sequence[str],
    panels: Sequence[str],
    item_count_by_panel: Mapping[str, int],
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[_Item, ...]:
    value_min, value_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="value_min",
        max_key="value_max",
        fallback_min=12,
        fallback_max=99,
        context=f"generation defaults for {TASK_ID}",
    )
    total_items = int(sum(int(value) for value in item_count_by_panel.values()))
    labels = _sample_labels(count=int(total_items), instance_seed=int(instance_seed))
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.items")
    items: List[_Item] = []
    label_index = 0
    for panel_index, panel in enumerate(panels):
        count = int(item_count_by_panel[str(panel)])
        panel_categories = list(categories)
        rng.shuffle(panel_categories)
        assigned_categories = [panel_categories[index % len(panel_categories)] for index in range(count)]
        rng.shuffle(assigned_categories)
        for local_index in range(count):
            items.append(
                _Item(
                    item_id=f"item_{len(items):02d}",
                    label=str(labels[label_index]),
                    category=str(assigned_categories[local_index]),
                    panel=str(panel),
                    value=int(rng.randint(int(value_min), int(value_max))),
                )
            )
            label_index += 1
        # Nudge one item per category in each panel so small groups are less likely to tie.
        del panel_index
    return tuple(items)

def _build_query(
    *,
    items: Sequence[_Item],
    categories: Sequence[str],
    panels: Sequence[str],
    query_id: str,
    extremum_direction: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> _Query:
    winner_gap_min = _resolve_int(params, "winner_gap_min", 8)
    neighbor_gap_min = _resolve_int(params, "neighbor_gap_min", 5)
    category_total_gap_min = _resolve_int(params, "category_total_gap_min", 18)

    if str(query_id) == "filtered_item_extremum_label":
        filtered_gap_min = _resolve_int(params, "filtered_item_winner_gap_min", int(winner_gap_min))
        filtered_gap_max = _resolve_int(params, "filtered_item_winner_gap_max", 10_000)
        outside_extreme_min = _resolve_int(params, "filtered_item_outside_extreme_min", 0)
        feasible: List[Tuple[str, List[_Item], _Item, int, int]] = []
        for category, group in sorted(_items_by_category(items).items()):
            if len(group) < 2:
                continue
            candidate_winner, candidate_gap = _extreme(group, str(extremum_direction))
            if int(candidate_gap) < int(filtered_gap_min) or int(candidate_gap) > int(filtered_gap_max):
                continue
            candidate_outside_extreme_count = _outside_extreme_count(
                items=items,
                winner=candidate_winner,
                direction=str(extremum_direction),
            )
            if int(candidate_outside_extreme_count) < int(outside_extreme_min):
                continue
            feasible.append(
                (
                    str(category),
                    list(group),
                    candidate_winner,
                    int(candidate_gap),
                    int(candidate_outside_extreme_count),
                )
            )
        if not feasible:
            raise ValueError("no feasible filtered extremum category")
        category, group, winner, gap, outside_extreme_count = feasible[
            _choose_index(
                len(feasible),
                params=params,
                instance_seed=instance_seed,
                namespace=f"{TASK_ID}.filtered_category",
            )
        ]
        return _Query(
            query_id=str(query_id),
            answer=str(winner.label),
            annotation_item_ids=(str(winner.item_id),),
            annotation_panel_labels=(),
            annotation_category_labels=(),
            category_label=str(category),
            panel_label="",
            reference_label="",
            extremum_direction=str(extremum_direction),
            trace={
                "winner_gap": int(gap),
                "candidate_count": int(len(group)),
                "outside_extreme_count": int(outside_extreme_count),
            },
        )

    if str(query_id) == "reference_size_neighbor_label":
        feasible_categories: List[Tuple[str, List[Tuple[_Item, List[Tuple[int, str, _Item]]]]]] = []
        for category, group in sorted(_items_by_category(items).items()):
            if len(group) < 3:
                continue
            feasible_references: List[Tuple[_Item, List[Tuple[int, str, _Item]]]] = []
            for reference in group:
                candidates = [item for item in group if str(item.item_id) != str(reference.item_id)]
                distances = sorted(
                    ((abs(int(item.value) - int(reference.value)), str(item.label), item) for item in candidates),
                    key=lambda row: (int(row[0]), str(row[1])),
                )
                if len(distances) >= 2 and int(distances[1][0]) - int(distances[0][0]) >= int(neighbor_gap_min):
                    feasible_references.append((reference, distances))
            if feasible_references:
                feasible_categories.append((str(category), feasible_references))
        if not feasible_categories:
            raise ValueError("reference-neighbor gap too small")
        category, feasible_references = feasible_categories[
            _choose_index(
                len(feasible_categories),
                params=params,
                instance_seed=instance_seed,
                namespace=f"{TASK_ID}.neighbor_category",
            )
        ]
        reference, distances = feasible_references[
            _choose_index(
                len(feasible_references),
                params=params,
                instance_seed=instance_seed,
                namespace=f"{TASK_ID}.neighbor_reference",
            )
        ]
        answer_item = distances[0][2]
        return _Query(
            query_id=str(query_id),
            answer=str(answer_item.label),
            annotation_item_ids=(str(reference.item_id), str(answer_item.item_id)),
            annotation_panel_labels=(),
            annotation_category_labels=(),
            category_label=str(category),
            panel_label="",
            reference_label=str(reference.label),
            extremum_direction="closest",
            trace={
                "reference_label": str(reference.label),
                "reference_value": int(reference.value),
                "nearest_distance": int(distances[0][0]),
                "nearest_gap": int(distances[1][0]) - int(distances[0][0]),
                "candidate_count": int(len(distances)),
            },
        )
    if str(query_id) == "category_total_extremum_label":
        totals = {
            str(category): int(sum(int(item.value) for item in items if str(item.category) == str(category)))
            for category in categories
        }
        ordered = sorted(totals.items(), key=lambda row: (int(row[1]), str(row[0])))
        if str(extremum_direction) == "largest":
            answer_category, answer_total = ordered[-1]
            runner_total = ordered[-2][1]
        elif str(extremum_direction) == "smallest":
            answer_category, answer_total = ordered[0]
            runner_total = ordered[1][1]
        else:
            raise ValueError(f"unsupported extremum direction: {extremum_direction}")
        gap = abs(int(answer_total) - int(runner_total))
        if int(gap) < int(category_total_gap_min):
            raise ValueError("category-total gap too small")
        annotation_ids = tuple(str(item.item_id) for item in items if str(item.category) == str(answer_category))
        return _Query(
            query_id=str(query_id),
            answer=str(answer_category),
            annotation_item_ids=annotation_ids,
            annotation_panel_labels=(),
            annotation_category_labels=(str(answer_category),),
            category_label=str(answer_category),
            panel_label="",
            reference_label="",
            extremum_direction=str(extremum_direction),
            trace={"category_totals": dict(totals), "winner_gap": int(gap), "winner_total": int(answer_total)},
        )

    raise ValueError(f"unsupported query id: {query_id}")

def _build_dataset(
    *,
    query_id: str,
    scene_variant: str,
    extremum_direction: str,
    params: Mapping[str, Any],
    instance_seed: int,
    attempt_index: int,
) -> _Dataset:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset.{int(attempt_index)}")
    cat_min, cat_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="category_count_min",
        max_key="category_count_max",
        fallback_min=3,
        fallback_max=5,
        context=f"generation defaults for {TASK_ID}",
    )
    category_count = int(rng.randint(int(cat_min), int(cat_max)))
    categories = _sample_categories(count=int(category_count), instance_seed=int(instance_seed) + int(attempt_index))
    panel_label_meta: Dict[str, Any] = {}

    if str(scene_variant) == "small_multiple_bubble_cloud":
        panel_min, panel_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="panel_count_min",
            max_key="panel_count_max",
            fallback_min=2,
            fallback_max=4,
            context=f"generation defaults for {TASK_ID}",
        )
        item_min, item_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="panel_item_count_min",
            max_key="panel_item_count_max",
            fallback_min=7,
            fallback_max=10,
            context=f"generation defaults for {TASK_ID}",
        )
        panel_count = int(rng.randint(int(panel_min), int(panel_max)))
        panels, panel_label_meta = _panel_labels(
            int(panel_count),
            params=params,
            instance_seed=int(instance_seed),
            reserved_labels=categories,
        )
        item_count_by_panel = {str(panel): int(rng.randint(int(item_min), int(item_max))) for panel in panels}
    else:
        item_min, item_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="item_count_min",
            max_key="item_count_max",
            fallback_min=18,
            fallback_max=30,
            context=f"generation defaults for {TASK_ID}",
        )
        panels = ("Overall",)
        item_count_by_panel = {"Overall": int(rng.randint(int(item_min), int(item_max)))}

    total_item_count_min = _resolve_int(params, "total_item_count_min", 1)
    total_item_count_max = _resolve_int(params, "total_item_count_max", 10_000)
    total_item_count = int(sum(int(value) for value in item_count_by_panel.values()))
    if int(total_item_count) < int(total_item_count_min):
        raise ValueError("total item count below minimum")
    if int(total_item_count) > int(total_item_count_max):
        raise ValueError("total item count above maximum")

    items = _sample_items(
        categories=categories,
        panels=panels,
        item_count_by_panel=item_count_by_panel,
        params=params,
        instance_seed=int(instance_seed) + (997 * int(attempt_index)),
    )
    query = _build_query(
        items=items,
        categories=categories,
        panels=panels,
        query_id=str(query_id),
        extremum_direction=str(extremum_direction),
        params=params,
        instance_seed=int(instance_seed) + (131 * int(attempt_index)),
    )
    query = _Query(
        query_id=str(query.query_id),
        answer=str(query.answer),
        annotation_item_ids=tuple(query.annotation_item_ids),
        annotation_panel_labels=tuple(query.annotation_panel_labels),
        annotation_category_labels=tuple(query.annotation_category_labels),
        category_label=str(query.category_label),
        panel_label=str(query.panel_label),
        reference_label=str(query.reference_label),
        extremum_direction=str(query.extremum_direction),
        trace={**dict(panel_label_meta), **dict(query.trace)},
    )
    return _Dataset(items=tuple(items), categories=tuple(categories), panels=tuple(panels), query=query)
