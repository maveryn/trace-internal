"""Sampling primitives for the sunburst chart scene."""

from __future__ import annotations

import colorsys
import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from trace.core.seed import spawn_rng

from .defaults import generation_value, int_sequence, resolve_bounds
from .state import RGB, SunburstNode, SunburstTree


_THEMES: tuple[dict[str, Any], ...] = (
    {
        "parent": "Healthcare",
        "subgroups": {
            "Clinics": ("Mobile", "Rural", "Urgent", "Remote"),
            "Telehealth": ("Video", "Phone", "Portal", "Nurse"),
            "Outreach": ("Home", "Wellness", "Screening", "Transit"),
        },
    },
    {
        "parent": "Transport",
        "subgroups": {
            "Shuttles": ("North", "South", "Evening", "Market"),
            "Rides": ("Medical", "Senior", "Rural", "Weekend"),
            "Drivers": ("Volunteer", "Taxi", "Van", "Rapid"),
        },
    },
    {
        "parent": "Commercial",
        "subgroups": {
            "Cafes": ("Olde", "Market", "Roaster", "Corner"),
            "Markets": ("Farmers", "Craft", "Night", "River"),
            "Retail": ("Books", "Gallery", "Florist", "Depot"),
        },
    },
    {
        "parent": "Historical",
        "subgroups": {
            "War": ("Square", "Marker", "Memorial", "Trail"),
            "Colonial": ("Hall", "Church", "Mansion", "Bridge"),
            "Industry": ("Mill", "Forge", "Depot", "Canal"),
        },
    },
    {
        "parent": "Athletics",
        "subgroups": {
            "Medals": ("Gold", "Silver", "Bronze", "Podium"),
            "Teams": ("National", "Youth", "Club", "League"),
            "Events": ("Track", "Judo", "Table", "Swimming"),
        },
    },
    {
        "parent": "Culture",
        "subgroups": {
            "Museums": ("Local", "Art", "History", "Science"),
            "Music": ("Jazz", "Pop", "Classic", "Folk"),
            "Festivals": ("Spring", "Summer", "Autumn", "Winter"),
        },
    },
    {
        "parent": "Natural",
        "subgroups": {
            "Parks": ("Riverside", "Founders", "Hill", "Lake"),
            "Trails": ("Ridge", "Creek", "Forest", "Valley"),
            "Views": ("Lookout", "Garden", "Harbor", "Sunset"),
        },
    },
    {
        "parent": "Education",
        "subgroups": {
            "Schools": ("Primary", "Middle", "High", "Adult"),
            "Libraries": ("Central", "Branch", "Mobile", "Digital"),
            "Training": ("Career", "STEM", "Language", "Arts"),
        },
    },
)


def lighten(color: RGB, amount: float) -> RGB:
    return tuple(
        max(0, min(255, int(round(float(channel) + (255.0 - float(channel)) * float(amount)))))
        for channel in color
    )


def parent_nodes(tree: SunburstTree) -> tuple[SunburstNode, ...]:
    nodes = nodes_by_id(tree)
    return tuple(nodes[str(parent_id)] for parent_id in tree.parent_ids)


def nodes_by_id(tree: SunburstTree) -> dict[str, SunburstNode]:
    return {str(node.node_id): node for node in tree.nodes}


def descendant_leaf_ids(node_lookup: Mapping[str, SunburstNode], node_ref: str) -> tuple[str, ...]:
    node = node_lookup[str(node_ref)]
    if node.level == "leaf":
        return (str(node_ref),)
    leaves: list[str] = []
    for child_id in node.child_ids:
        leaves.extend(descendant_leaf_ids(node_lookup, str(child_id)))
    return tuple(leaves)


def hierarchy_rows(tree: SunburstTree) -> list[dict[str, Any]]:
    return [
        {
            "node_id": str(node.node_id),
            "label": str(node.label),
            "level": str(node.level),
            "parent_id": str(node.parent_id) if node.parent_id is not None else None,
            "value": int(node.value),
            "child_ids": [str(child_id) for child_id in node.child_ids],
        }
        for node in tree.nodes
    ]


def sample_tree(params: Mapping[str, Any], *, instance_seed: int) -> SunburstTree:
    """Build a balanced hierarchy with unique leaf values for deterministic tasks."""

    parent_min, parent_max = resolve_bounds(
        params,
        min_key="sunburst_parent_count_min",
        max_key="sunburst_parent_count_max",
        fallback_min=4,
        fallback_max=5,
    )
    subgroup_min, subgroup_max = resolve_bounds(
        params,
        min_key="sunburst_subgroup_count_min",
        max_key="sunburst_subgroup_count_max",
        fallback_min=2,
        fallback_max=3,
    )
    leaf_min, leaf_max = resolve_bounds(
        params,
        min_key="sunburst_leaf_count_min",
        max_key="sunburst_leaf_count_max",
        fallback_min=1,
        fallback_max=2,
    )
    value_min, value_max = resolve_bounds(
        params,
        min_key="sunburst_leaf_value_min",
        max_key="sunburst_leaf_value_max",
        fallback_min=5,
        fallback_max=40,
    )
    value_step = max(1, int(generation_value(params, "sunburst_leaf_value_step", 5)))
    rng = spawn_rng(int(instance_seed), "charts.sunburst.tree")
    parent_count = int(rng.randint(int(parent_min), int(parent_max)))
    themes = _sample_parent_themes(count=int(parent_count), instance_seed=int(instance_seed))

    built_nodes: dict[str, SunburstNode] = {}
    parent_ids: list[str] = []
    subgroup_ids: list[str] = []
    leaf_ids: list[str] = []
    leaf_value_low = int(math.ceil(int(value_min) / int(value_step)))
    leaf_value_high = int(math.floor(int(value_max) / int(value_step)))
    if leaf_value_low > leaf_value_high:
        raise ValueError("sunburst leaf value range is incompatible with value step")

    for parent_index, theme in enumerate(themes):
        parent_id = f"parent_{parent_index}"
        parent_ids.append(parent_id)
        parent_color = _parent_color(parent_index, parent_count, instance_seed=int(instance_seed))
        raw_subgroups = list(dict(theme["subgroups"]).items())
        rng.shuffle(raw_subgroups)
        subgroup_count = int(rng.randint(int(subgroup_min), min(int(subgroup_max), len(raw_subgroups))))
        value_units = list(range(int(leaf_value_low), int(leaf_value_high) + 1))
        rng.shuffle(value_units)
        parent_child_ids: list[str] = []
        parent_value = 0
        for subgroup_index, (subgroup_label, leaf_pool) in enumerate(raw_subgroups[:subgroup_count]):
            subgroup_id = f"{parent_id}_subgroup_{subgroup_index}"
            subgroup_ids.append(subgroup_id)
            parent_child_ids.append(subgroup_id)
            leaf_labels = [str(item) for item in leaf_pool]
            rng.shuffle(leaf_labels)
            leaf_count = int(rng.randint(int(leaf_min), min(int(leaf_max), len(leaf_labels))))
            subgroup_child_ids: list[str] = []
            subgroup_value = 0
            for leaf_index, leaf_label in enumerate(leaf_labels[:leaf_count]):
                leaf_id = f"{subgroup_id}_leaf_{leaf_index}"
                if value_units:
                    value_unit = int(value_units.pop())
                else:
                    value_unit = int(rng.randint(leaf_value_low, leaf_value_high))
                value = int(value_unit * int(value_step))
                leaf_ids.append(leaf_id)
                subgroup_child_ids.append(leaf_id)
                subgroup_value += int(value)
                built_nodes[leaf_id] = SunburstNode(
                    node_id=leaf_id,
                    label=str(leaf_label),
                    level="leaf",
                    parent_id=subgroup_id,
                    value=int(value),
                    child_ids=(),
                    color_rgb=lighten(parent_color, 0.20 + 0.08 * (leaf_index % 3)),
                )
            parent_value += int(subgroup_value)
            built_nodes[subgroup_id] = SunburstNode(
                node_id=subgroup_id,
                label=str(subgroup_label),
                level="subgroup",
                parent_id=parent_id,
                value=int(subgroup_value),
                child_ids=tuple(subgroup_child_ids),
                color_rgb=lighten(parent_color, 0.08),
            )
        built_nodes[parent_id] = SunburstNode(
            node_id=parent_id,
            label=str(theme["parent"]),
            level="parent",
            parent_id="root",
            value=int(parent_value),
            child_ids=tuple(parent_child_ids),
            color_rgb=parent_color,
        )

    root_value = int(sum(int(built_nodes[parent_id].value) for parent_id in parent_ids))
    built_nodes["root"] = SunburstNode(
        node_id="root",
        label="Total",
        level="root",
        parent_id=None,
        value=int(root_value),
        child_ids=tuple(parent_ids),
        color_rgb=(224, 232, 190),
    )

    ordered_nodes = [built_nodes["root"]]
    for parent_id in parent_ids:
        ordered_nodes.append(built_nodes[parent_id])
        for subgroup_id in built_nodes[parent_id].child_ids:
            ordered_nodes.append(built_nodes[subgroup_id])
            for leaf_id in built_nodes[subgroup_id].child_ids:
                ordered_nodes.append(built_nodes[leaf_id])

    return SunburstTree(
        nodes=tuple(ordered_nodes),
        root_id="root",
        parent_ids=tuple(parent_ids),
        subgroup_ids=tuple(subgroup_ids),
        leaf_ids=tuple(leaf_ids),
        generation_ranges={
            "parent_count_range": [int(parent_min), int(parent_max)],
            "subgroup_count_range": [int(subgroup_min), int(subgroup_max)],
            "leaf_count_range": [int(leaf_min), int(leaf_max)],
            "leaf_value_range": [int(value_min), int(value_max)],
            "leaf_value_step": int(value_step),
        },
    )


def choose_parent(tree: SunburstTree, *, instance_seed: int, namespace: str) -> SunburstNode:
    parents = parent_nodes(tree)
    if not parents:
        raise ValueError("sunburst tree contains no parent nodes")
    rng = spawn_rng(int(instance_seed), str(namespace))
    return parents[int(rng.randrange(len(parents)))]


def unique_extreme_parent(tree: SunburstTree, *, direction: str) -> SunburstNode:
    parents = parent_nodes(tree)
    totals = [int(parent.value) for parent in parents]
    if len(set(totals)) != len(totals):
        raise ValueError("sunburst parent totals must be unique for extremum task")
    if str(direction) == "highest":
        return max(parents, key=lambda node: int(node.value))
    if str(direction) == "lowest":
        return min(parents, key=lambda node: int(node.value))
    raise ValueError(f"unsupported sunburst extremum direction: {direction}")


def threshold_leaf_case(
    tree: SunburstTree,
    *,
    comparator: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> dict[str, Any]:
    """Choose one parent and threshold with a nontrivial matching-leaf count."""

    node_lookup = nodes_by_id(tree)
    rng = spawn_rng(int(instance_seed), f"charts.sunburst.threshold.{comparator}")
    count_support = [int(value) for value in int_sequence(params, "sunburst_condition_count_support", (1, 2, 3, 4, 5))]
    ordered_counts = _ordered_count_support(count_support, params=params, rng=rng)
    parent_order = list(str(parent_id) for parent_id in tree.parent_ids)
    rng.shuffle(parent_order)
    comparison = str(comparator)
    if comparison not in {"above", "below"}:
        raise ValueError(f"unsupported threshold comparator: {comparator}")
    for parent_id in parent_order:
        leaf_ids = descendant_leaf_ids(node_lookup, str(parent_id))
        values = [int(node_lookup[leaf_id].value) for leaf_id in leaf_ids]
        if len(values) < 3:
            continue
        candidates_by_count: dict[int, list[int]] = defaultdict(list)
        for threshold in range(min(values), max(values) + 1):
            if comparison == "above":
                count = sum(1 for value in values if int(value) > int(threshold))
            else:
                count = sum(1 for value in values if int(value) < int(threshold))
            if 1 <= int(count) <= len(values) - 1:
                candidates_by_count[int(count)].append(int(threshold))
        available_counts = [count for count in ordered_counts if count in candidates_by_count]
        if not available_counts:
            continue
        answer = int(available_counts[0])
        thresholds = candidates_by_count[int(answer)]
        threshold = int(thresholds[int(rng.randrange(len(thresholds)))])
        return {
            "parent_id": str(parent_id),
            "parent_label": str(node_lookup[parent_id].label),
            "comparison_phrase": comparison,
            "threshold_value": int(threshold),
            "leaf_ids": tuple(str(leaf_id) for leaf_id in leaf_ids),
            "leaf_values": values,
            "answer": int(answer),
        }
    raise ValueError("unable to build nontrivial sunburst threshold count case")


def range_leaf_case(
    tree: SunburstTree,
    *,
    params: Mapping[str, Any],
    instance_seed: int,
) -> dict[str, Any]:
    """Choose one parent and inclusive range with a nontrivial leaf count."""

    node_lookup = nodes_by_id(tree)
    rng = spawn_rng(int(instance_seed), "charts.sunburst.range")
    count_support = [int(value) for value in int_sequence(params, "sunburst_condition_count_support", (1, 2, 3, 4, 5))]
    ordered_counts = _ordered_count_support(count_support, params=params, rng=rng)
    parent_order = list(str(parent_id) for parent_id in tree.parent_ids)
    rng.shuffle(parent_order)
    for parent_id in parent_order:
        leaf_ids = descendant_leaf_ids(node_lookup, str(parent_id))
        values = sorted(int(node_lookup[leaf_id].value) for leaf_id in leaf_ids)
        unique_values = sorted(set(values))
        if len(unique_values) < 3:
            continue
        candidates_by_count: dict[int, list[tuple[int, int]]] = defaultdict(list)
        for low_index, low in enumerate(unique_values):
            for high in unique_values[low_index:]:
                count = sum(1 for value in values if int(low) <= int(value) <= int(high))
                if 1 <= int(count) <= len(values) - 1:
                    candidates_by_count[int(count)].append((int(low), int(high)))
        available_counts = [count for count in ordered_counts if count in candidates_by_count]
        if not available_counts:
            continue
        answer = int(available_counts[0])
        ranges = candidates_by_count[int(answer)]
        lower, upper = ranges[int(rng.randrange(len(ranges)))]
        return {
            "parent_id": str(parent_id),
            "parent_label": str(node_lookup[parent_id].label),
            "lower_value": int(lower),
            "upper_value": int(upper),
            "leaf_ids": tuple(str(leaf_id) for leaf_id in leaf_ids),
            "leaf_values": [int(node_lookup[str(leaf_id)].value) for leaf_id in leaf_ids],
            "answer": int(answer),
        }
    raise ValueError("unable to build nontrivial sunburst range count case")


def threshold_matching_leaf_ids(case: Mapping[str, Any], node_lookup: Mapping[str, SunburstNode]) -> tuple[str, ...]:
    """Return leaves whose values satisfy the sampled one-bound predicate."""

    threshold = int(case["threshold_value"])
    comparison = str(case["comparison_phrase"])
    matched = tuple(
        str(leaf_id)
        for leaf_id in tuple(str(item) for item in case["leaf_ids"])
        if (
            (comparison == "above" and int(node_lookup[str(leaf_id)].value) > threshold)
            or (comparison == "below" and int(node_lookup[str(leaf_id)].value) < threshold)
        )
    )
    if not matched:
        raise ValueError("sunburst threshold case produced zero matching leaves")
    return matched


def range_matching_leaf_ids(case: Mapping[str, Any], node_lookup: Mapping[str, SunburstNode]) -> tuple[str, ...]:
    """Return leaves whose values fall inside the sampled inclusive range."""

    lower = int(case["lower_value"])
    upper = int(case["upper_value"])
    matched = tuple(
        str(leaf_id)
        for leaf_id in tuple(str(item) for item in case["leaf_ids"])
        if lower <= int(node_lookup[str(leaf_id)].value) <= upper
    )
    if not matched:
        raise ValueError("sunburst range case produced zero matching leaves")
    return matched


def _sample_parent_themes(*, count: int, instance_seed: int) -> tuple[dict[str, Any], ...]:
    rng = spawn_rng(int(instance_seed), "charts.sunburst.themes")
    themes = list(_THEMES)
    rng.shuffle(themes)
    if int(count) > len(themes):
        raise ValueError("sunburst parent_count exceeds theme pool")
    return tuple(dict(theme) for theme in themes[: int(count)])


def _parent_color(index: int, count: int, *, instance_seed: int) -> RGB:
    rng = spawn_rng(int(instance_seed), "charts.sunburst.palette")
    offset = rng.random()
    hue = (float(offset) + float(index) / max(1.0, float(count))) % 1.0
    sat = 0.48 + 0.14 * rng.random()
    val = 0.76 + 0.12 * rng.random()
    red, green, blue = colorsys.hsv_to_rgb(float(hue), float(sat), float(val))
    return int(red * 255), int(green * 255), int(blue * 255)


def _ordered_count_support(count_support: Sequence[int], *, params: Mapping[str, Any], rng: Any) -> list[int]:
    support = [int(value) for value in count_support]
    if not support:
        return []
    if params.get("_sample_cursor") is not None:
        target = support[abs(int(params["_sample_cursor"])) % len(support)]
        return [int(target)] + [int(value) for value in support if int(value) != int(target)]
    rng.shuffle(support)
    return list(support)


__all__ = [
    "choose_parent",
    "descendant_leaf_ids",
    "hierarchy_rows",
    "nodes_by_id",
    "parent_nodes",
    "range_leaf_case",
    "range_matching_leaf_ids",
    "sample_tree",
    "threshold_leaf_case",
    "threshold_matching_leaf_ids",
    "unique_extreme_parent",
]
