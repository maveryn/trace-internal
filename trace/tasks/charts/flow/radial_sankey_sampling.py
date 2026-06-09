"""Dataset and query construction for radial Sankey chart tasks."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ...shared.config_defaults import resolve_required_int_bounds
from ..shared.label_assets import resolve_chart_entity_labels
from ..shared.sampling_defaults import balanced_int_from_support as _balanced_int
from .radial_sankey_common import (
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


def _node_specs(labels: Sequence[str], *, prefix: str, role: str) -> List[Dict[str, Any]]:
    return [
        {
            "node_id": f"{prefix}_{index}",
            "label": str(label),
            "role": str(role),
            "index": int(index),
        }
        for index, label in enumerate(labels)
    ]


def _sample_nodes(rng, *, source_count: int, target_count: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    labels = list(
        resolve_chart_entity_labels(
            rng,
            count=int(source_count) + int(target_count),
            min_chars=2,
            max_chars=6,
            allow_spaces=False,
        ).labels
    )
    source_labels = [str(label) for label in labels[: int(source_count)]]
    target_labels = [str(label) for label in labels[int(source_count) : int(source_count) + int(target_count)]]
    return (
        _node_specs(source_labels, prefix="source", role="source"),
        _node_specs(target_labels, prefix="target", role="target"),
    )


def _link_record(
    *,
    link_id: str,
    source: Mapping[str, Any],
    target: Mapping[str, Any],
    value: int,
) -> Dict[str, Any]:
    return {
        "link_id": str(link_id),
        "source_id": str(source["node_id"]),
        "source_label": str(source["label"]),
        "target_id": str(target["node_id"]),
        "target_label": str(target["label"]),
        "value": int(value),
    }


def _sample_links(
    *,
    rng,
    sources: Sequence[Mapping[str, Any]],
    targets: Sequence[Mapping[str, Any]],
    link_count: int,
    value_min: int,
    value_max: int,
) -> List[Dict[str, Any]]:
    all_pairs = [(source, target) for source in sources for target in targets]
    if int(link_count) > len(all_pairs):
        raise ValueError("link_count exceeds unique radial Sankey source-target pairs")
    selected_pairs = rng.sample(list(all_pairs), k=int(link_count))
    links: List[Dict[str, Any]] = []
    for index, (source, target) in enumerate(selected_pairs):
        links.append(
            _link_record(
                link_id=f"link_{index}",
                source=source,
                target=target,
                value=int(rng.randint(int(value_min), int(value_max))),
            )
        )
    return links


def _link_side_counts(links: Sequence[Mapping[str, Any]]) -> Dict[str, Dict[str, int]]:
    source_out: Counter[str] = Counter()
    target_in: Counter[str] = Counter()
    for link in links:
        source_out[str(link["source_id"])] += 1
        target_in[str(link["target_id"])] += 1
    return {"source_out": dict(source_out), "target_in": dict(target_in)}


def _links_respect_side_limit(links: Sequence[Mapping[str, Any]], *, max_links_per_node_side: int) -> bool:
    if int(max_links_per_node_side) <= 0:
        return True
    for counts in _link_side_counts(links).values():
        if counts and max(int(value) for value in counts.values()) > int(max_links_per_node_side):
            return False
    return True


def _join_quoted(labels: Sequence[str]) -> str:
    quoted = [f'"{str(label)}"' for label in labels]
    if len(quoted) <= 1:
        return quoted[0] if quoted else ""
    if len(quoted) == 2:
        return f"{quoted[0]} and {quoted[1]}"
    return f"{', '.join(quoted[:-1])}, and {quoted[-1]}"


def _choose_query(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
    rng,
    links: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    group_min, group_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="radial_group_size_min",
        max_key="radial_group_size_max",
        fallback_min=2,
        fallback_max=3,
        context=f"{TASK_ID} radial grouped endpoint count",
    )
    answer_min, answer_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="radial_transfer_answer_min",
        max_key="radial_transfer_answer_max",
        fallback_min=16,
        fallback_max=100,
        context=f"{TASK_ID} radial transfer answer",
    )

    if str(query_id) == "source_to_targets_total":
        group_size = _balanced_int(
            list(range(int(group_min), int(group_max) + 1)),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.source_target_group_size",
        )
        by_source: Dict[str, List[Dict[str, Any]]] = {}
        for link in links:
            by_source.setdefault(str(link["source_id"]), []).append(dict(link))
        eligible: List[Tuple[str, List[Dict[str, Any]]]] = []
        for source_id, group in sorted(by_source.items()):
            ordered = sorted(group, key=lambda item: (str(item["target_label"]), str(item["link_id"])))
            if len(ordered) < int(group_size):
                continue
            for start in range(0, len(ordered) - int(group_size) + 1):
                subset = ordered[start : start + int(group_size)]
                answer = sum(int(item["value"]) for item in subset)
                if int(answer_min) <= int(answer) <= int(answer_max):
                    eligible.append((str(source_id), subset))
        if not eligible:
            raise ValueError(f"no eligible source grouped transfer for {TASK_ID}")
        _source_id, selected_links = eligible[int(rng.randrange(len(eligible)))]
        source_label = str(selected_links[0]["source_label"])
        target_labels = [str(link["target_label"]) for link in selected_links]
        answer = sum(int(link["value"]) for link in selected_links)
        return {
            "answer_value": int(answer),
            "answer_type": "integer",
            "source_label": str(source_label),
            "source_labels": [],
            "source_labels_joined": "",
            "target_label": "",
            "target_labels": list(target_labels),
            "target_labels_joined": _join_quoted(target_labels),
            "query_link_ids": [str(link["link_id"]) for link in selected_links],
            "comparison_link_ids": [],
            "annotation_link_ids": [str(link["link_id"]) for link in selected_links],
            "annotation_node_ids": [],
            "group_size": int(len(selected_links)),
            "expression": " + ".join(str(int(link["value"])) for link in selected_links),
            "link_details": [dict(link) for link in selected_links],
        }

    if str(query_id) == "sources_to_target_total":
        group_size = _balanced_int(
            list(range(int(group_min), int(group_max) + 1)),
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.target_source_group_size",
        )
        by_target: Dict[str, List[Dict[str, Any]]] = {}
        for link in links:
            by_target.setdefault(str(link["target_id"]), []).append(dict(link))
        eligible: List[Tuple[str, List[Dict[str, Any]]]] = []
        for target_id, group in sorted(by_target.items()):
            ordered = sorted(group, key=lambda item: (str(item["source_label"]), str(item["link_id"])))
            if len(ordered) < int(group_size):
                continue
            for start in range(0, len(ordered) - int(group_size) + 1):
                subset = ordered[start : start + int(group_size)]
                answer = sum(int(item["value"]) for item in subset)
                if int(answer_min) <= int(answer) <= int(answer_max):
                    eligible.append((str(target_id), subset))
        if not eligible:
            raise ValueError(f"no eligible target grouped transfer for {TASK_ID}")
        _target_id, selected_links = eligible[int(rng.randrange(len(eligible)))]
        target_label = str(selected_links[0]["target_label"])
        source_labels = [str(link["source_label"]) for link in selected_links]
        answer = sum(int(link["value"]) for link in selected_links)
        return {
            "answer_value": int(answer),
            "answer_type": "integer",
            "source_label": "",
            "source_labels": list(source_labels),
            "source_labels_joined": _join_quoted(source_labels),
            "target_label": str(target_label),
            "target_labels": [],
            "target_labels_joined": "",
            "query_link_ids": [str(link["link_id"]) for link in selected_links],
            "comparison_link_ids": [],
            "annotation_link_ids": [str(link["link_id"]) for link in selected_links],
            "annotation_node_ids": [],
            "group_size": int(len(selected_links)),
            "expression": " + ".join(str(int(link["value"])) for link in selected_links),
            "link_details": [dict(link) for link in selected_links],
        }

    if str(query_id) == "largest_target_for_source":
        by_source: Dict[str, List[Dict[str, Any]]] = {}
        for link in links:
            by_source.setdefault(str(link["source_id"]), []).append(dict(link))
        eligible_sources: List[List[Dict[str, Any]]] = []
        for group in by_source.values():
            ordered = sorted(group, key=lambda item: (-int(item["value"]), str(item["target_label"]), str(item["link_id"])))
            values = [int(item["value"]) for item in ordered]
            if len(ordered) >= 2 and len(set(values)) == len(values):
                eligible_sources.append(ordered)
        if not eligible_sources:
            raise ValueError(f"no eligible largest target query for {TASK_ID}")
        selected_group = eligible_sources[int(rng.randrange(len(eligible_sources)))]
        winner = dict(selected_group[0])
        return {
            "answer_value": str(winner["target_label"]),
            "answer_type": "string",
            "source_label": str(winner["source_label"]),
            "source_labels": [],
            "source_labels_joined": "",
            "target_label": "",
            "target_labels": [],
            "target_labels_joined": "",
            "query_link_ids": [str(link["link_id"]) for link in selected_group],
            "comparison_link_ids": [str(link["link_id"]) for link in selected_group],
            "annotation_link_ids": [str(link["link_id"]) for link in selected_group],
            "annotation_node_ids": [str(winner["target_id"])],
            "group_size": int(len(selected_group)),
            "expression": f"argmax target for {winner['source_label']}",
            "link_details": [dict(link) for link in selected_group],
        }

    if str(query_id) == "largest_source_for_target":
        by_target: Dict[str, List[Dict[str, Any]]] = {}
        for link in links:
            by_target.setdefault(str(link["target_id"]), []).append(dict(link))
        eligible_targets: List[List[Dict[str, Any]]] = []
        for group in by_target.values():
            ordered = sorted(group, key=lambda item: (-int(item["value"]), str(item["source_label"]), str(item["link_id"])))
            values = [int(item["value"]) for item in ordered]
            if len(ordered) >= 2 and len(set(values)) == len(values):
                eligible_targets.append(ordered)
        if not eligible_targets:
            raise ValueError(f"no eligible largest source query for {TASK_ID}")
        selected_group = eligible_targets[int(rng.randrange(len(eligible_targets)))]
        winner = dict(selected_group[0])
        return {
            "answer_value": str(winner["source_label"]),
            "answer_type": "string",
            "source_label": "",
            "source_labels": [],
            "source_labels_joined": "",
            "target_label": str(winner["target_label"]),
            "target_labels": [],
            "target_labels_joined": "",
            "query_link_ids": [str(link["link_id"]) for link in selected_group],
            "comparison_link_ids": [str(link["link_id"]) for link in selected_group],
            "annotation_link_ids": [str(link["link_id"]) for link in selected_group],
            "annotation_node_ids": [str(winner["source_id"])],
            "group_size": int(len(selected_group)),
            "expression": f"argmax source for {winner['target_label']}",
            "link_details": [dict(link) for link in selected_group],
        }

    raise ValueError(f"unsupported query_id: {query_id}")


def _construct_dataset(
    *,
    query_id: str,
    scene_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Dict[str, Any]:
    if str(scene_variant) != "radial_chord_sankey":
        raise ValueError(f"unsupported scene_variant: {scene_variant}")

    source_count, source_count_bounds = _resolve_count(
        params,
        min_key="radial_source_count_min",
        max_key="radial_source_count_max",
        explicit_key="radial_source_count",
        fallback_min=4,
        fallback_max=5,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.source_count",
    )
    target_count, target_count_bounds = _resolve_count(
        params,
        min_key="radial_target_count_min",
        max_key="radial_target_count_max",
        explicit_key="radial_target_count",
        fallback_min=4,
        fallback_max=5,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.target_count",
    )
    link_count, link_count_bounds = _resolve_count(
        params,
        min_key="radial_link_count_min",
        max_key="radial_link_count_max",
        explicit_key="radial_link_count",
        fallback_min=7,
        fallback_max=9,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.link_count",
    )
    value_min, value_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="radial_link_value_min",
        max_key="radial_link_value_max",
        fallback_min=8,
        fallback_max=35,
        context=f"{TASK_ID} radial link values",
    )
    max_links_per_node_side = max(0, _gen_int_param(params, "radial_max_links_per_node_side", 4))

    for attempt in range(120):
        rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset_attempt", int(attempt))
        sources, targets = _sample_nodes(
            rng,
            source_count=int(source_count),
            target_count=int(target_count),
        )
        try:
            links = _sample_links(
                rng=rng,
                sources=sources,
                targets=targets,
                link_count=int(link_count),
                value_min=int(value_min),
                value_max=int(value_max),
            )
        except ValueError:
            continue
        if not _links_respect_side_limit(links, max_links_per_node_side=int(max_links_per_node_side)):
            continue
        try:
            query = _choose_query(
                query_id=str(query_id),
                params=params,
                instance_seed=int(instance_seed),
                rng=rng,
                links=links,
            )
        except ValueError:
            continue
        return {
            "scene_title": str(rng.choice(_TITLE_OPTIONS)),
            "query_id": str(query_id),
            "scene_variant": str(scene_variant),
            "sources": [dict(node) for node in sources],
            "targets": [dict(node) for node in targets],
            "links": [dict(link) for link in links],
            "links_by_id": {str(link["link_id"]): dict(link) for link in links},
            "source_count": int(source_count),
            "target_count": int(target_count),
            "link_count": int(link_count),
            "max_links_per_node_side": int(max_links_per_node_side),
            "link_side_counts": _link_side_counts(links),
            "source_count_bounds": tuple(int(value) for value in source_count_bounds),
            "target_count_bounds": tuple(int(value) for value in target_count_bounds),
            "link_count_bounds": tuple(int(value) for value in link_count_bounds),
            "value_min": int(value_min),
            "value_max": int(value_max),
            "answer_value": query["answer_value"],
            "answer_type": str(query["answer_type"]),
            "query": dict(query),
        }
    raise ValueError(f"failed to construct feasible {TASK_ID} instance")
