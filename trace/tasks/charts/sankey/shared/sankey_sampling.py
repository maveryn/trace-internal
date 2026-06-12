"""Sampling and dataset construction for Sankey flow chart tasks."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from .....core.seed import spawn_rng
from ....shared.config_defaults import resolve_required_int_bounds
from ...shared.label_assets import resolve_chart_entity_labels
from ...shared.sampling_defaults import balanced_int_from_support as _balanced_int
from .sankey_common import (
    NODE_SIDE_TOTAL_QUERY_IDS,
    TASK_ID,
    _GEN_DEFAULTS,
    _TITLE_OPTIONS,
    _gen_int_param,
)

def _resolve_count(
    params: Mapping[str, Any],
    *,
    min_key: str,
    max_key: str,
    explicit_key: str,
    fallback_min: int,
    fallback_max: int,
    instance_seed: int,
    namespace: str,
) -> Tuple[int, Tuple[int, int]]:
    lower, upper = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key=str(min_key),
        max_key=str(max_key),
        fallback_min=int(fallback_min),
        fallback_max=int(fallback_max),
        context=f"{TASK_ID} {explicit_key}",
    )
    explicit = params.get(str(explicit_key))
    support = [int(value) for value in range(int(lower), int(upper) + 1)]
    if explicit is not None:
        selected = int(explicit)
        if int(selected) not in set(support):
            raise ValueError(f"{explicit_key} must be in {lower}..{upper}")
        return int(selected), (int(lower), int(upper))
    return (
        _balanced_int(support, params=params, instance_seed=int(instance_seed), namespace=str(namespace)),
        (int(lower), int(upper)),
    )


def _node_specs(labels: Sequence[str], *, prefix: str, column: str) -> List[Dict[str, Any]]:
    return [
        {
            "node_id": f"{prefix}_{index}",
            "label": str(label),
            "column": str(column),
            "index": int(index),
        }
        for index, label in enumerate(labels)
    ]


def _path_record(
    *,
    path_id: str,
    source: Mapping[str, Any],
    middle: Mapping[str, Any],
    target: Mapping[str, Any],
    first_value: int,
    second_value: int,
) -> Dict[str, Any]:
    bottleneck = min(int(first_value), int(second_value))
    difference = abs(int(first_value) - int(second_value))
    return {
        "path_id": str(path_id),
        "source_id": str(source["node_id"]),
        "source_label": str(source["label"]),
        "middle_id": str(middle["node_id"]),
        "middle_label": str(middle["label"]),
        "target_id": str(target["node_id"]),
        "target_label": str(target["label"]),
        "first_value": int(first_value),
        "second_value": int(second_value),
        "bottleneck_value": int(bottleneck),
        "absolute_difference": int(difference),
    }


def _sample_labels(rng, *, source_count: int, middle_count: int, target_count: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    labels = list(
        resolve_chart_entity_labels(
            rng,
            count=int(source_count) + int(middle_count) + int(target_count),
            min_chars=2,
            max_chars=6,
            allow_spaces=False,
        ).labels
    )
    source_labels = [str(label) for label in labels[: int(source_count)]]
    middle_start = int(source_count)
    target_start = int(source_count) + int(middle_count)
    middle_labels = [str(label) for label in labels[middle_start:target_start]]
    target_labels = [str(label) for label in labels[target_start : target_start + int(target_count)]]
    return (
        _node_specs(source_labels, prefix="source", column="source"),
        _node_specs(middle_labels, prefix="middle", column="middle"),
        _node_specs(target_labels, prefix="target", column="target"),
    )


def _sample_paths(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
    rng,
    sources: Sequence[Mapping[str, Any]],
    middles: Sequence[Mapping[str, Any]],
    targets: Sequence[Mapping[str, Any]],
    path_count: int,
    value_min: int,
    value_max: int,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    all_triples = [
        (source, middle, target)
        for source in sources
        for middle in middles
        for target in targets
    ]
    selected_triples: List[Tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]] = []
    query_seed_params: Dict[str, Any] = {}

    if str(query_id) == "source_to_target_total_flow":
        source_target_pairs = [(source, target) for source in sources for target in targets]
        pair_index = _balanced_int(
            list(range(len(source_target_pairs))),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.source_target_pair",
        )
        query_source, query_target = source_target_pairs[int(pair_index)]
        route_min, route_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="source_target_route_count_min",
            max_key="source_target_route_count_max",
            fallback_min=2,
            fallback_max=3,
            context=f"{TASK_ID} source-target route count",
        )
        route_max = min(int(route_max), len(middles), int(path_count))
        route_min = min(int(route_min), int(route_max))
        route_count = _balanced_int(
            list(range(int(route_min), int(route_max) + 1)),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.source_target_route_count",
        )
        selected_middles = [middles[index] for index in rng.sample(list(range(len(middles))), int(route_count))]
        selected_triples.extend((query_source, middle, query_target) for middle in selected_middles)
        excluded_pair = (str(query_source["node_id"]), str(query_target["node_id"]))
        remaining = [
            triple
            for triple in all_triples
            if (str(triple[0]["node_id"]), str(triple[2]["node_id"])) != excluded_pair
            and str(triple[0]["node_id"]) != str(query_source["node_id"])
            and str(triple[2]["node_id"]) != str(query_target["node_id"])
        ]
        rng.shuffle(remaining)
        needed_remaining = max(0, int(path_count) - len(selected_triples))
        if len(remaining) < int(needed_remaining):
            raise ValueError(f"not enough uncrowded distractor paths for {TASK_ID}")
        selected_triples.extend(remaining[: int(needed_remaining)])
        query_seed_params = {
            "source_id": str(query_source["node_id"]),
            "source_label": str(query_source["label"]),
            "target_id": str(query_target["node_id"]),
            "target_label": str(query_target["label"]),
            "route_count": int(route_count),
        }
    else:
        selected_triples = rng.sample(list(all_triples), k=int(path_count))

    paths: List[Dict[str, Any]] = []
    for index, (source, middle, target) in enumerate(selected_triples):
        first_value = int(rng.randint(int(value_min), int(value_max)))
        second_value = int(rng.randint(int(value_min), int(value_max)))
        paths.append(
            _path_record(
                path_id=f"path_{index}",
                source=source,
                middle=middle,
                target=target,
                first_value=int(first_value),
                second_value=int(second_value),
            )
        )
    return list(paths), dict(query_seed_params)


def _path_side_counts(paths: Sequence[Mapping[str, Any]]) -> Dict[str, Dict[str, int]]:
    source_out: Counter[str] = Counter()
    middle_in: Counter[str] = Counter()
    middle_out: Counter[str] = Counter()
    target_in: Counter[str] = Counter()
    for path in paths:
        source_out[str(path["source_id"])] += 1
        middle_in[str(path["middle_id"])] += 1
        middle_out[str(path["middle_id"])] += 1
        target_in[str(path["target_id"])] += 1
    return {
        "source_out": dict(source_out),
        "middle_in": dict(middle_in),
        "middle_out": dict(middle_out),
        "target_in": dict(target_in),
    }


def _paths_respect_side_limit(paths: Sequence[Mapping[str, Any]], *, max_paths_per_node_side: int) -> bool:
    if int(max_paths_per_node_side) <= 0:
        return True
    for counts in _path_side_counts(paths).values():
        if counts and max(int(value) for value in counts.values()) > int(max_paths_per_node_side):
            return False
    return True


def _choose_query(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
    rng,
    paths: Sequence[Mapping[str, Any]],
    query_seed_params: Mapping[str, Any],
) -> Dict[str, Any]:
    if str(query_id) == "source_to_target_total_flow":
        source_id = str(query_seed_params["source_id"])
        target_id = str(query_seed_params["target_id"])
        matching = [
            dict(path)
            for path in paths
            if str(path["source_id"]) == source_id and str(path["target_id"]) == target_id
        ]
        if len(matching) < 2:
            raise ValueError(f"{TASK_ID} requires at least two source-target routes")
        matching = sorted(matching, key=lambda path: (str(path["middle_label"]), str(path["path_id"])))
        answer = sum(int(path["bottleneck_value"]) for path in matching)
        answer_min, answer_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="source_target_answer_min",
            max_key="source_target_answer_max",
            fallback_min=10,
            fallback_max=90,
            context=f"{TASK_ID} source-target answer",
        )
        if int(answer) < int(answer_min) or int(answer) > int(answer_max):
            raise ValueError(f"source-target total {answer} outside configured support")
        annotation_segment_ids = [
            segment_id
            for path in matching
            for segment_id in (f"{path['path_id']}:source_middle", f"{path['path_id']}:middle_target")
        ]
        return {
            "answer_value": int(answer),
            "query_path_ids": [str(path["path_id"]) for path in matching],
            "annotation_segment_ids": list(annotation_segment_ids),
            "source_label": str(query_seed_params["source_label"]),
            "target_label": str(query_seed_params["target_label"]),
            "middle_label": "",
            "route_count": int(len(matching)),
            "expression": " + ".join(str(int(path["bottleneck_value"])) for path in matching),
            "path_details": [dict(path) for path in matching],
        }

    if str(query_id) == "path_bottleneck_value":
        eligible = [dict(path) for path in paths]
        selected = dict(eligible[int(rng.randrange(len(eligible)))])
        answer = int(selected["bottleneck_value"])
        annotation_segment_ids = [
            f"{selected['path_id']}:source_middle",
            f"{selected['path_id']}:middle_target",
        ]
        return {
            "answer_value": int(answer),
            "query_path_ids": [str(selected["path_id"])],
            "annotation_segment_ids": list(annotation_segment_ids),
            "source_label": str(selected["source_label"]),
            "middle_label": str(selected["middle_label"]),
            "target_label": str(selected["target_label"]),
            "route_count": 1,
            "expression": f"min({int(selected['first_value'])}, {int(selected['second_value'])})",
            "path_details": [dict(selected)],
        }

    if str(query_id) == "path_flow_difference":
        diff_min, diff_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="path_difference_min",
            max_key="path_difference_max",
            fallback_min=2,
            fallback_max=25,
            context=f"{TASK_ID} path difference",
        )
        eligible = [
            dict(path)
            for path in paths
            if int(diff_min) <= int(path["absolute_difference"]) <= int(diff_max)
        ]
        if not eligible:
            raise ValueError(f"no eligible path difference for {TASK_ID}")
        selected = dict(eligible[int(rng.randrange(len(eligible)))])
        answer = int(selected["absolute_difference"])
        annotation_segment_ids = [
            f"{selected['path_id']}:source_middle",
            f"{selected['path_id']}:middle_target",
        ]
        return {
            "answer_value": int(answer),
            "query_path_ids": [str(selected["path_id"])],
            "annotation_segment_ids": list(annotation_segment_ids),
            "source_label": str(selected["source_label"]),
            "middle_label": str(selected["middle_label"]),
            "target_label": str(selected["target_label"]),
            "route_count": 1,
            "expression": f"abs({int(selected['first_value'])} - {int(selected['second_value'])})",
            "path_details": [dict(selected)],
        }

    if str(query_id) in NODE_SIDE_TOTAL_QUERY_IDS:
        answer_min, answer_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="node_side_total_answer_min",
            max_key="node_side_total_answer_max",
            fallback_min=10,
            fallback_max=90,
            context=f"{TASK_ID} node-side total answer",
        )
        connected_min, connected_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="node_side_total_connected_min",
            max_key="node_side_total_connected_max",
            fallback_min=2,
            fallback_max=3,
            context=f"{TASK_ID} node-side connected path count",
        )

        if str(query_id) == "source_outgoing_total_flow":
            source_groups: Dict[str, List[Dict[str, Any]]] = {}
            for path in paths:
                source_groups.setdefault(str(path["source_id"]), []).append(dict(path))
            eligible_sources: List[Tuple[str, str, int, List[Dict[str, Any]]]] = []
            for source_id, group in sorted(source_groups.items()):
                ordered_group = sorted(
                    group,
                    key=lambda path: (str(path["middle_label"]), str(path["target_label"]), str(path["path_id"])),
                )
                if not (int(connected_min) <= len(ordered_group) <= int(connected_max)):
                    continue
                answer = sum(int(path["first_value"]) for path in ordered_group)
                if int(answer_min) <= int(answer) <= int(answer_max):
                    eligible_sources.append((str(source_id), str(ordered_group[0]["source_label"]), int(answer), ordered_group))
            if not eligible_sources:
                raise ValueError(f"no eligible source outgoing total for {TASK_ID}")
            selected_node_id, source_label, answer, selected_paths = eligible_sources[int(rng.randrange(len(eligible_sources)))]
            annotation_segment_ids = [f"{path['path_id']}:source_middle" for path in selected_paths]
            terms = " + ".join(str(int(path["first_value"])) for path in selected_paths)
            return {
                "answer_value": int(answer),
                "query_path_ids": [str(path["path_id"]) for path in selected_paths],
                "annotation_segment_ids": list(annotation_segment_ids),
                "source_id": str(selected_node_id),
                "source_label": str(source_label),
                "middle_label": "",
                "target_label": "",
                "node_side": "source_outgoing",
                "connected_count": int(len(selected_paths)),
                "node_side_total": int(answer),
                "route_count": int(len(selected_paths)),
                "expression": str(terms),
                "path_details": [dict(path) for path in selected_paths],
            }

        if str(query_id) == "target_incoming_total_flow":
            target_groups: Dict[str, List[Dict[str, Any]]] = {}
            for path in paths:
                target_groups.setdefault(str(path["target_id"]), []).append(dict(path))
            eligible_targets: List[Tuple[str, str, int, List[Dict[str, Any]]]] = []
            for target_id, group in sorted(target_groups.items()):
                ordered_group = sorted(
                    group,
                    key=lambda path: (str(path["source_label"]), str(path["middle_label"]), str(path["path_id"])),
                )
                if not (int(connected_min) <= len(ordered_group) <= int(connected_max)):
                    continue
                answer = sum(int(path["second_value"]) for path in ordered_group)
                if int(answer_min) <= int(answer) <= int(answer_max):
                    eligible_targets.append((str(target_id), str(ordered_group[0]["target_label"]), int(answer), ordered_group))
            if not eligible_targets:
                raise ValueError(f"no eligible target incoming total for {TASK_ID}")
            selected_node_id, target_label, answer, selected_paths = eligible_targets[int(rng.randrange(len(eligible_targets)))]
            annotation_segment_ids = [f"{path['path_id']}:middle_target" for path in selected_paths]
            terms = " + ".join(str(int(path["second_value"])) for path in selected_paths)
            return {
                "answer_value": int(answer),
                "query_path_ids": [str(path["path_id"]) for path in selected_paths],
                "annotation_segment_ids": list(annotation_segment_ids),
                "source_label": "",
                "middle_label": "",
                "target_id": str(selected_node_id),
                "target_label": str(target_label),
                "node_side": "target_incoming",
                "connected_count": int(len(selected_paths)),
                "node_side_total": int(answer),
                "route_count": int(len(selected_paths)),
                "expression": str(terms),
                "path_details": [dict(path) for path in selected_paths],
            }

    raise ValueError(f"unsupported query_id: {query_id}")


def _construct_dataset(
    *,
    query_id: str,
    scene_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Dict[str, Any]:
    if str(scene_variant) != "three_column_sankey":
        raise ValueError(f"unsupported scene_variant: {scene_variant}")

    source_count, source_count_bounds = _resolve_count(
        params,
        min_key="source_count_min",
        max_key="source_count_max",
        explicit_key="source_count",
        fallback_min=3,
        fallback_max=4,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.source_count",
    )
    middle_count, middle_count_bounds = _resolve_count(
        params,
        min_key="middle_count_min",
        max_key="middle_count_max",
        explicit_key="middle_count",
        fallback_min=3,
        fallback_max=5,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.middle_count",
    )
    target_count, target_count_bounds = _resolve_count(
        params,
        min_key="target_count_min",
        max_key="target_count_max",
        explicit_key="target_count",
        fallback_min=3,
        fallback_max=4,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.target_count",
    )
    path_count, path_count_bounds = _resolve_count(
        params,
        min_key="path_count_min",
        max_key="path_count_max",
        explicit_key="path_count",
        fallback_min=9,
        fallback_max=14,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.path_count",
    )
    value_min, value_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="link_value_min",
        max_key="link_value_max",
        fallback_min=5,
        fallback_max=35,
        context=f"{TASK_ID} link values",
    )
    if int(path_count) > int(source_count) * int(middle_count) * int(target_count):
        raise ValueError(f"path_count {path_count} exceeds possible unique paths")
    max_paths_per_node_side = max(0, _gen_int_param(params, "max_paths_per_node_side", 2))

    for attempt in range(80):
        rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset_attempt", int(attempt))
        sources, middles, targets = _sample_labels(
            rng,
            source_count=int(source_count),
            middle_count=int(middle_count),
            target_count=int(target_count),
        )
        try:
            paths, query_seed_params = _sample_paths(
                query_id=str(query_id),
                params=params,
                instance_seed=int(instance_seed),
                rng=rng,
                sources=sources,
                middles=middles,
                targets=targets,
                path_count=int(path_count),
                value_min=int(value_min),
                value_max=int(value_max),
            )
        except ValueError:
            continue
        if not _paths_respect_side_limit(paths, max_paths_per_node_side=int(max_paths_per_node_side)):
            continue
        try:
            query = _choose_query(
                query_id=str(query_id),
                params=params,
                instance_seed=int(instance_seed),
                rng=rng,
                paths=paths,
                query_seed_params=query_seed_params,
            )
        except ValueError:
            continue
        return {
            "scene_title": str(rng.choice(_TITLE_OPTIONS)),
            "query_id": str(query_id),
            "scene_variant": str(scene_variant),
            "sources": [dict(node) for node in sources],
            "middles": [dict(node) for node in middles],
            "targets": [dict(node) for node in targets],
            "paths": [dict(path) for path in paths],
            "paths_by_id": {str(path["path_id"]): dict(path) for path in paths},
            "source_count": int(source_count),
            "middle_count": int(middle_count),
            "target_count": int(target_count),
            "path_count": int(path_count),
            "max_paths_per_node_side": int(max_paths_per_node_side),
            "path_side_counts": _path_side_counts(paths),
            "source_count_bounds": tuple(int(value) for value in source_count_bounds),
            "middle_count_bounds": tuple(int(value) for value in middle_count_bounds),
            "target_count_bounds": tuple(int(value) for value in target_count_bounds),
            "path_count_bounds": tuple(int(value) for value in path_count_bounds),
            "value_min": int(value_min),
            "value_max": int(value_max),
            "answer_value": int(query["answer_value"]),
            "query": dict(query),
        }
    raise ValueError(f"failed to construct feasible {TASK_ID} instance")
