"""Behavior tests for graph bridge-edge counting task."""

from __future__ import annotations

import json
from collections import Counter

import networkx as nx

from trace.core.seed import hash64
from trace.tasks.graph.counting.bridge_count import GraphCountingBridgeCountTask
from trace.tasks.shared.named_colors import named_color


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def _graph_from_trace_adjacency(adjacency_by_label: dict[str, list[str]]) -> nx.Graph:
    graph = nx.Graph()
    for label, neighbors in adjacency_by_label.items():
        graph.add_node(str(label))
        for neighbor in neighbors:
            graph.add_edge(str(label), str(neighbor))
    return graph


def test_graph_counting_bridge_count_contract_matches_trace() -> None:
    task = GraphCountingBridgeCountTask()
    out = task.generate(
        19601,
        params={
            "node_count": 9,
            "target_count": 3,
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
    assert out.evidence_gt.type == "edge_set"
    assert int(out.answer_gt.value) == len(out.evidence_gt.value)
    assert trace["scene_ir"]["scene_kind"] == "graph_bridge_counting"
    assert execution["question_format"] == "count_bridge_edges"
    assert execution["graph_directionality"] == "undirected"
    assert int(execution["target_count"]) == len(out.evidence_gt.value)
    assert len(node_entities) == 9
    assert len(edge_entities) == int(execution["edge_count"])
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert set(out.complexity.complexity_components.keys()) == {
        "visual_scan",
        "topology_reasoning",
        "ambiguity",
        "clutter",
    }
    assert all(0.0 <= float(value) <= 1.0 for value in out.complexity.complexity_components.values())

    adjacency_by_label = {str(key): [str(value) for value in values] for key, values in execution["adjacency_by_label"].items()}
    graph = _graph_from_trace_adjacency(adjacency_by_label)
    bridge_edges = sorted(
        (tuple(sorted((str(left), str(right)), key=lambda value: int(value) if str(value).isdigit() else str(value))) for left, right in nx.bridges(graph)),
        key=lambda pair: (
            int(pair[0]) if str(pair[0]).isdigit() else str(pair[0]),
            int(pair[1]) if str(pair[1]).isdigit() else str(pair[1]),
        ),
    )
    evidence_edges = [tuple(str(value) for value in edge) for edge in out.evidence_gt.value]
    assert bridge_edges == evidence_edges
    assert bridge_edges == [tuple(str(value) for value in edge) for edge in execution["matching_edges"]]
    assert trace["projected_evidence"]["edge_set"] == out.evidence_gt.value
    assert len(trace["projected_evidence"]["pixel_edge_set"]) == len(out.evidence_gt.value)
    assert sum(1 for edge in edge_entities if bool(edge["is_bridge"])) == len(out.evidence_gt.value)


def test_graph_counting_bridge_count_prompt_examples_follow_label_variant() -> None:
    task = GraphCountingBridgeCountTask()
    letters = task.generate(
        19602,
        params={"label_variant": "letters", "node_count": 9, "target_count": 2},
        max_attempts=80,
    )
    numbers = task.generate(
        19603,
        params={"label_variant": "numbers", "node_count": 9, "target_count": 2},
        max_attempts=80,
    )
    letters_example = _extract_prompt_json_example(letters.prompt_variants["answer_and_evidence"])
    numbers_example = _extract_prompt_json_example(numbers.prompt_variants["answer_and_evidence"])
    assert letters_example == {"evidence": [["B", "D"], ["D", "G"]], "answer": 2}
    assert numbers_example == {"evidence": [["2", "5"], ["5", "8"]], "answer": 2}


def test_graph_counting_bridge_count_supports_numeric_labels_and_named_colors() -> None:
    task = GraphCountingBridgeCountTask()
    out = task.generate(
        19604,
        params={
            "node_count": 10,
            "target_count": 5,
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
    assert execution["label_variant"] == "numbers"
    assert execution["node_shape_variant"] == "hexagon"
    assert execution["layout_transform_variant"] == "rotate_90"
    assert execution["node_color_name"] == "orange"
    assert tuple(trace["render_spec"]["style"]["node_fill_rgb"]) == tuple(named_color("orange"))


def test_graph_counting_bridge_count_balanced_sampling_defaults() -> None:
    task = GraphCountingBridgeCountTask()
    target_counts: Counter[int] = Counter()
    label_variants: Counter[str] = Counter()
    node_shape_variants: Counter[str] = Counter()
    layout_variants: Counter[str] = Counter()
    topology_profiles: Counter[str] = Counter()
    for index in range(54):
        out = task.generate(
            hash64(19605, "graph_counting_bridge_count", index),
            params={"_sampling_index": index},
            max_attempts=80,
        )
        execution = out.trace_payload["execution_trace"]
        target_counts[int(execution["target_count"])] += 1
        label_variants[str(execution["label_variant"])] += 1
        node_shape_variants[str(execution["node_shape_variant"])] += 1
        layout_variants[str(execution["layout_variant_requested"])] += 1
        topology_profiles[str(execution["topology_profile"])] += 1
        assert 5 <= int(execution["node_count"]) <= 10
        assert 0 <= int(execution["target_count"]) <= 8
    assert set(target_counts.keys()) == set(range(0, 9))
    assert set(label_variants.keys()) == {"letters", "numbers"}
    assert set(node_shape_variants.keys()) == {"circle", "rounded_square", "hexagon"}
    assert set(layout_variants.keys()) == {"circular", "shell", "spring"}
    assert set(topology_profiles.keys()) == {"balanced", "hub_heavy", "low_degree"}
