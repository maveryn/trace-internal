"""Behavior tests for graph same-component relation task."""

from __future__ import annotations

import json
from collections import Counter

from trace.core.seed import hash64
from trace.tasks.graph.relation.same_component_count import GraphRelationSameComponentCountTask
from trace.tasks.shared.named_colors import named_color


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def test_graph_relation_same_component_count_contract_matches_trace() -> None:
    task = GraphRelationSameComponentCountTask()
    out = task.generate(
        19201,
        params={
            "node_count": 8,
            "component_count": 3,
            "target_component_size": 3,
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
    assert trace["scene_ir"]["scene_kind"] == "graph_same_component_relation"
    assert execution["question_format"] == "count_nodes_in_same_component_including_query"
    assert execution["graph_directionality"] == "undirected"
    assert 2 <= int(execution["component_count"]) <= 4
    assert int(execution["target_component_size"]) == len(out.evidence_gt.value)
    assert str(execution["query_label"]) in out.evidence_gt.value
    assert len(node_entities) == 8
    assert len(edge_entities) == int(execution["edge_count"])
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert "including node" in str(out.prompt_variants["answer_only"]).lower()
    assert set(out.complexity.complexity_components.keys()) == {
        "visual_scan",
        "topology_reasoning",
        "ambiguity",
        "clutter",
    }
    assert all(0.0 <= float(value) <= 1.0 for value in out.complexity.complexity_components.values())

    adjacency_by_label = {str(key): [str(value) for value in values] for key, values in execution["adjacency_by_label"].items()}
    components = [tuple(component) for component in execution["components_by_label"]]
    query_label = str(execution["query_label"])
    matching_labels = [str(value) for value in execution["matching_labels"]]
    matching_component = next(component for component in components if query_label in component)
    assert tuple(matching_labels) == matching_component
    assert matching_labels == list(out.evidence_gt.value)
    assert trace["projected_evidence"]["label_set"] == out.evidence_gt.value
    assert len(trace["projected_evidence"]["pixel_point_set"]) == len(out.evidence_gt.value)
    assert len(trace["projected_evidence"]["pixel_bbox_set"]) == len(out.evidence_gt.value)
    for label in matching_labels:
        assert str(label) in adjacency_by_label


def test_graph_relation_same_component_prompt_examples_follow_label_variant() -> None:
    task = GraphRelationSameComponentCountTask()
    letters = task.generate(
        19202,
        params={"label_variant": "letters", "node_count": 8, "component_count": 3, "target_component_size": 3},
        max_attempts=80,
    )
    numbers = task.generate(
        19203,
        params={"label_variant": "numbers", "node_count": 8, "component_count": 3, "target_component_size": 3},
        max_attempts=80,
    )
    letters_example = _extract_prompt_json_example(letters.prompt_variants["answer_and_evidence"])
    numbers_example = _extract_prompt_json_example(numbers.prompt_variants["answer_and_evidence"])
    assert letters_example == {"evidence": ["B", "F", "H"], "answer": 3}
    assert numbers_example == {"evidence": ["2", "7", "9"], "answer": 3}


def test_graph_relation_same_component_supports_numeric_labels_and_named_colors() -> None:
    task = GraphRelationSameComponentCountTask()
    out = task.generate(
        19204,
        params={
            "node_count": 10,
            "component_count": 4,
            "target_component_size": 4,
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


def test_graph_relation_same_component_balanced_sampling_defaults() -> None:
    task = GraphRelationSameComponentCountTask()
    component_counts: Counter[int] = Counter()
    target_sizes: Counter[int] = Counter()
    label_variants: Counter[str] = Counter()
    node_shape_variants: Counter[str] = Counter()
    layout_variants: Counter[str] = Counter()
    topology_profiles: Counter[str] = Counter()
    for index in range(48):
        out = task.generate(
            hash64(19205, "graph_relation_same_component_count", index),
            params={"_sampling_index": index},
            max_attempts=80,
        )
        execution = out.trace_payload["execution_trace"]
        component_counts[int(execution["component_count"])] += 1
        target_sizes[int(execution["target_component_size"])] += 1
        label_variants[str(execution["label_variant"])] += 1
        node_shape_variants[str(execution["node_shape_variant"])] += 1
        layout_variants[str(execution["layout_variant_requested"])] += 1
        topology_profiles[str(execution["topology_profile"])] += 1
        assert 5 <= int(execution["node_count"]) <= 10
        assert 2 <= int(execution["component_count"]) <= 4
        assert 1 <= int(execution["target_component_size"]) <= 6
    assert set(component_counts.keys()) == {2, 3, 4}
    assert set(target_sizes.keys()) == {1, 2, 3, 4, 5, 6}
    assert set(label_variants.keys()) == {"letters", "numbers"}
    assert set(node_shape_variants.keys()) == {"circle", "rounded_square", "hexagon"}
    assert set(layout_variants.keys()) == {"circular", "shell", "spring"}
    assert set(topology_profiles.keys()) == {"balanced", "hub_heavy", "low_degree"}
