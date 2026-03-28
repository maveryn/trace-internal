"""Behavior tests for graph degree-count counting task."""

from __future__ import annotations

import json
from collections import Counter

from trace.core.seed import hash64
from trace.tasks.graph.counting.degree_count import GraphCountingDegreeCountTask
from trace.tasks.shared.named_colors import named_color


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def test_graph_counting_degree_count_contract_matches_trace() -> None:
    task = GraphCountingDegreeCountTask()
    out = task.generate(
        19101,
        params={
            "node_count": 7,
            "query_degree": 2,
            "target_count": 2,
            "layout_variant": "shell",
            "topology_profile": "balanced",
        },
        max_attempts=80,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    scene_entities = trace["scene_ir"]["entities"]
    node_entities = [entity for entity in scene_entities if entity["entity_kind"] == "graph_node"]
    edge_entities = [entity for entity in scene_entities if entity["entity_kind"] == "graph_edge"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == 2
    assert out.evidence_gt.type == "label_set"
    assert out.evidence_gt.value == sorted(out.evidence_gt.value)
    assert len(out.evidence_gt.value) == 2
    assert trace["scene_ir"]["scene_kind"] == "graph_degree_counting"
    assert execution["question_format"] == "count_nodes_with_degree"
    assert int(execution["node_count"]) == 7
    assert int(execution["query_degree"]) == 2
    assert int(execution["target_count"]) == 2
    assert execution["layout_variant_requested"] == "shell"
    assert execution["topology_profile"] == "balanced"
    assert execution["label_variant"] in {"letters", "numbers"}
    assert execution["node_shape_variant"] in {"circle", "rounded_square", "hexagon"}
    assert execution["layout_transform_variant"] in {
        "identity",
        "rotate_90",
        "rotate_180",
        "rotate_270",
        "mirror_left_right",
        "mirror_up_down",
    }
    assert execution["node_color_name"]
    assert len(node_entities) == 7
    assert len(edge_entities) == int(execution["edge_count"])
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert trace["query_spec"]["prompt_variant_active_key"] == "answer_and_evidence"
    assert 0.0 <= float(out.complexity.complexity_score) <= 1.0
    assert set(out.complexity.complexity_components.keys()) == {
        "visual_scan",
        "topology_reasoning",
        "ambiguity",
        "clutter",
    }
    assert all(0.0 <= float(value) <= 1.0 for value in out.complexity.complexity_components.values())

    degrees_by_label = {str(key): int(value) for key, value in execution["degrees_by_label"].items()}
    adjacency_by_label = {str(key): [str(value) for value in values] for key, values in execution["adjacency_by_label"].items()}
    assert sorted(degrees_by_label.keys()) == sorted(entity["label"] for entity in node_entities)
    for label, degree in degrees_by_label.items():
        assert int(degree) == len(adjacency_by_label[str(label)])
        for neighbor in adjacency_by_label[str(label)]:
            assert str(label) in adjacency_by_label[str(neighbor)]

    matching_labels = [str(value) for value in execution["matching_labels"]]
    assert matching_labels == list(out.evidence_gt.value)
    assert all(int(degrees_by_label[str(label)]) == 2 for label in matching_labels)
    assert trace["projected_evidence"]["label_set"] == out.evidence_gt.value
    assert len(trace["projected_evidence"]["pixel_point_set"]) == 2
    assert len(trace["projected_evidence"]["pixel_bbox_set"]) == 2
    assert trace["render_spec"]["style"]["node_shape_variant"] == execution["node_shape_variant"]
    assert trace["render_spec"]["style"]["node_color_name"] == execution["node_color_name"]


def test_graph_counting_degree_count_prompt_example_matches_contract() -> None:
    task = GraphCountingDegreeCountTask()
    out = task.generate(19102, params={"node_count": 8, "query_degree": 1, "target_count": 2}, max_attempts=80)
    answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
    answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert answer_only == {"answer": 2}
    assert list(answer_and_evidence.keys()) == ["evidence", "answer"]
    assert answer_and_evidence["evidence"] == ["B", "F"]
    assert answer_and_evidence["answer"] == 2


def test_graph_counting_degree_count_supports_numeric_labels_and_named_colors() -> None:
    task = GraphCountingDegreeCountTask()
    out = task.generate(
        19104,
        params={
            "node_count": 10,
            "query_degree": 1,
            "target_count": 3,
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
    assert trace["render_spec"]["style"]["node_shape_variant"] == "hexagon"
    assert tuple(trace["render_spec"]["style"]["node_fill_rgb"]) == tuple(named_color("orange"))


def test_graph_counting_degree_count_balanced_sampling_defaults() -> None:
    task = GraphCountingDegreeCountTask()
    target_counts: Counter[int] = Counter()
    query_degrees: Counter[int] = Counter()
    layout_variants: Counter[str] = Counter()
    topology_profiles: Counter[str] = Counter()
    label_variants: Counter[str] = Counter()
    node_shape_variants: Counter[str] = Counter()
    layout_transform_variants: Counter[str] = Counter()
    node_colors: Counter[str] = Counter()
    for index in range(60):
        out = task.generate(
            hash64(19103, "graph_counting_degree_count", index),
            params={"_sampling_index": index},
            max_attempts=80,
        )
        execution = out.trace_payload["execution_trace"]
        target_counts[int(execution["target_count"])] += 1
        query_degrees[int(execution["query_degree"])] += 1
        layout_variants[str(execution["layout_variant_requested"])] += 1
        topology_profiles[str(execution["topology_profile"])] += 1
        label_variants[str(execution["label_variant"])] += 1
        node_shape_variants[str(execution["node_shape_variant"])] += 1
        layout_transform_variants[str(execution["layout_transform_variant"])] += 1
        node_colors[str(execution["node_color_name"])] += 1
        assert 5 <= int(execution["node_count"]) <= 10
        assert 0 <= int(execution["query_degree"]) <= 4
        assert 0 <= int(execution["target_count"]) <= 5
    assert set(target_counts.keys()) == set(range(0, 6))
    assert set(query_degrees.keys()) == set(range(0, 5))
    assert set(layout_variants.keys()) == {"circular", "shell", "spring"}
    assert set(topology_profiles.keys()) == {"balanced", "hub_heavy", "low_degree"}
    assert set(label_variants.keys()) == {"letters", "numbers"}
    assert set(node_shape_variants.keys()) == {"circle", "rounded_square", "hexagon"}
    assert set(layout_transform_variants.keys()) == {
        "identity",
        "rotate_90",
        "rotate_180",
        "rotate_270",
        "mirror_left_right",
        "mirror_up_down",
    }
    assert set(node_colors.keys()) == {
        "red",
        "blue",
        "green",
        "yellow",
        "orange",
        "purple",
        "brown",
        "cyan",
        "magenta",
        "maroon",
    }
