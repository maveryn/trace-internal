"""Behavior tests for graph reachable-count relation task."""

from __future__ import annotations

import json
from collections import Counter

from trace.core.seed import hash64
from trace.tasks.graph.relation.reachable_count import GraphRelationReachableCountTask
from trace.tasks.shared.graph_algorithms import bfs_dist_count_by_adjacency
from trace.tasks.shared.named_colors import named_color


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def test_graph_relation_reachable_count_contract_matches_trace() -> None:
    task = GraphRelationReachableCountTask()
    out = task.generate(
        19701,
        params={
            "node_count": 8,
            "target_reachable_count": 4,
            "layout_variant": "shell",
            "topology_profile": "balanced",
            "label_variant": "letters",
        },
        max_attempts=80,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    scene_entities = trace["scene_ir"]["entities"]
    node_entities = [entity for entity in scene_entities if entity["entity_kind"] == "graph_node"]
    edge_entities = [entity for entity in scene_entities if entity["entity_kind"] == "graph_edge"]

    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "label_set"
    assert int(out.answer_gt.value) == len(out.evidence_gt.value)
    assert trace["scene_ir"]["scene_kind"] == "graph_reachable_relation"
    assert execution["question_format"] == "count_reachable_nodes_including_query"
    assert execution["graph_directionality"] == "directed"
    assert 5 <= int(execution["node_count"]) <= 9
    assert 1 <= int(execution["target_reachable_count"]) <= 7
    assert len(node_entities) == 8
    assert len(edge_entities) == int(execution["edge_count"])
    assert all(bool(edge["directed"]) for edge in edge_entities)
    assert str(execution["query_label"]) in set(out.evidence_gt.value)
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert "including node" in str(out.prompt).lower()
    assert "following the direction of the arrows" in str(out.prompt)
    assert set(out.complexity.complexity_components.keys()) == {
        "visual_scan",
        "topology_reasoning",
        "ambiguity",
        "clutter",
    }
    assert all(0.0 <= float(value) <= 1.0 for value in out.complexity.complexity_components.values())

    successors = {str(key): [str(value) for value in values] for key, values in execution["successors_by_label"].items()}
    dist_start, _ = bfs_dist_count_by_adjacency(successors, start=str(execution["query_label"]))
    reachable_labels = sorted((str(label) for label in dist_start.keys()), key=lambda value: int(value) if str(value).isdigit() else str(value))
    assert reachable_labels == list(out.evidence_gt.value)
    assert reachable_labels == [str(value) for value in execution["matching_labels"]]
    assert trace["projected_evidence"]["label_set"] == out.evidence_gt.value
    assert len(trace["projected_evidence"]["pixel_point_set"]) == len(out.evidence_gt.value)
    assert len(trace["projected_evidence"]["pixel_bbox_set"]) == len(out.evidence_gt.value)


def test_graph_relation_reachable_count_prompt_examples_follow_label_variant() -> None:
    task = GraphRelationReachableCountTask()
    letters = task.generate(
        19702,
        params={"label_variant": "letters", "node_count": 8, "target_reachable_count": 4},
        max_attempts=80,
    )
    numbers = task.generate(
        19703,
        params={"label_variant": "numbers", "node_count": 8, "target_reachable_count": 4},
        max_attempts=80,
    )
    letters_example = _extract_prompt_json_example(letters.prompt_variants["answer_and_evidence"])
    numbers_example = _extract_prompt_json_example(numbers.prompt_variants["answer_and_evidence"])
    assert letters_example == {"evidence": ["B", "D", "H"], "answer": 3}
    assert numbers_example == {"evidence": ["2", "5", "8"], "answer": 3}


def test_graph_relation_reachable_count_supports_numeric_labels_and_named_colors() -> None:
    task = GraphRelationReachableCountTask()
    out = task.generate(
        19704,
        params={
            "node_count": 9,
            "target_reachable_count": 5,
            "label_variant": "numbers",
            "node_shape_variant": "hexagon",
            "layout_transform_variant": "rotate_90",
            "node_color_name": "orange",
        },
        max_attempts=80,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    labels = [entity["label"] for entity in trace["scene_ir"]["entities"] if entity["entity_kind"] == "graph_node"]
    assert all(str(label).isdigit() for label in labels)
    assert out.evidence_gt.value == sorted(out.evidence_gt.value, key=lambda value: int(str(value)))
    assert execution["label_variant"] == "numbers"
    assert execution["node_shape_variant"] == "hexagon"
    assert execution["layout_transform_variant"] == "rotate_90"
    assert execution["node_color_name"] == "orange"
    assert tuple(trace["render_spec"]["style"]["node_fill_rgb"]) == tuple(named_color("orange"))


def test_graph_relation_reachable_count_balanced_sampling_defaults() -> None:
    task = GraphRelationReachableCountTask()
    target_counts: Counter[int] = Counter()
    label_variants: Counter[str] = Counter()
    node_shape_variants: Counter[str] = Counter()
    layout_variants: Counter[str] = Counter()
    topology_profiles: Counter[str] = Counter()
    for index in range(48):
        out = task.generate(
            hash64(19705, "graph_relation_reachable_count", index),
            params={"_sampling_index": index},
            max_attempts=80,
        )
        execution = out.trace_payload["execution_trace"]
        target_counts[int(execution["target_reachable_count"])] += 1
        label_variants[str(execution["label_variant"])] += 1
        node_shape_variants[str(execution["node_shape_variant"])] += 1
        layout_variants[str(execution["layout_variant_requested"])] += 1
        topology_profiles[str(execution["topology_profile"])] += 1
        assert 5 <= int(execution["node_count"]) <= 9
        assert 1 <= int(execution["target_reachable_count"]) <= 7
        assert int(execution["target_reachable_count"]) <= int(execution["node_count"]) - 1
        assert str(execution["query_label"]) in set(execution["matching_labels"])
    assert set(label_variants.keys()) == {"letters", "numbers"}
    assert set(node_shape_variants.keys()) == {"circle", "rounded_square", "hexagon"}
    assert set(layout_variants.keys()) == {"circular", "shell", "spring"}
    assert set(topology_profiles.keys()) == {"balanced", "hub_heavy", "low_degree"}
    assert min(target_counts.keys()) >= 1
    assert max(target_counts.keys()) <= 7
