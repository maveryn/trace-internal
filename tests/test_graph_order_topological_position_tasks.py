"""Behavior tests for graph topological-position task."""

from __future__ import annotations

import json
from collections import Counter

from trace.core.seed import hash64
from trace.tasks.graph.order.topological_position import GraphOrderTopologicalPositionTask
from trace.tasks.shared.graph_algorithms import unique_topological_order_by_adjacency
from trace.tasks.shared.named_colors import named_color


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def test_graph_order_topological_position_contract_matches_trace() -> None:
    task = GraphOrderTopologicalPositionTask()
    out = task.generate(
        19640,
        params={
            "node_count": 7,
            "target_position": 4,
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
    assert out.evidence_gt.type == "label_sequence"
    assert trace["scene_ir"]["scene_kind"] == "graph_topological_position"
    assert execution["question_format"] == "query_topological_position_of_node"
    assert execution["graph_directionality"] == "directed"
    assert int(execution["node_count"]) == 7
    assert len(node_entities) == 7
    assert len(edge_entities) == int(execution["edge_count"])
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert set(out.complexity.complexity_components.keys()) == {
        "topology_reasoning",
        "visual_scan",
        "ambiguity",
        "clutter",
    }
    assert all(0.0 <= float(value) <= 1.0 for value in out.complexity.complexity_components.values())

    successors_by_label = {
        str(key): tuple(str(value) for value in values)
        for key, values in trace["execution_trace"]["successors_by_label"].items()
    }
    evidence_labels = tuple(str(label) for label in out.evidence_gt.value)
    verified_order = unique_topological_order_by_adjacency(successors_by_label, node_order=evidence_labels)
    assert verified_order is not None
    assert tuple(str(label) for label in verified_order) == evidence_labels
    assert int(out.answer_gt.value) == int(evidence_labels.index(str(execution["query_label"])) + 1)
    assert int(out.answer_gt.value) == int(execution["target_position"])
    assert trace["projected_evidence"]["label_sequence"] == out.evidence_gt.value
    assert len(trace["projected_evidence"]["pixel_point_path"]) == len(out.evidence_gt.value)
    assert len(trace["projected_evidence"]["pixel_bbox_set"]) == len(out.evidence_gt.value)
    assert sum(1 for node in node_entities if bool(node["is_query_node"])) == 1


def test_graph_order_topological_position_prompt_examples_follow_label_variant() -> None:
    task = GraphOrderTopologicalPositionTask()
    letters = task.generate(
        19641,
        params={"label_variant": "letters", "node_count": 7, "target_position": 3},
        max_attempts=80,
    )
    numbers = task.generate(
        19642,
        params={"label_variant": "numbers", "node_count": 7, "target_position": 3},
        max_attempts=80,
    )
    letters_example = _extract_prompt_json_example(letters.prompt_variants["answer_and_evidence"])
    numbers_example = _extract_prompt_json_example(numbers.prompt_variants["answer_and_evidence"])
    assert letters_example == {"evidence": ["B", "D", "H", "J"], "answer": 3}
    assert numbers_example == {"evidence": ["2", "5", "8", "9"], "answer": 3}


def test_graph_order_topological_position_supports_numeric_labels_and_named_colors() -> None:
    task = GraphOrderTopologicalPositionTask()
    out = task.generate(
        19643,
        params={
            "node_count": 7,
            "target_position": 5,
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


def test_graph_order_topological_position_balanced_sampling_defaults() -> None:
    task = GraphOrderTopologicalPositionTask()
    node_counts: Counter[int] = Counter()
    target_positions: Counter[int] = Counter()
    label_variants: Counter[str] = Counter()
    node_shape_variants: Counter[str] = Counter()
    layout_variants: Counter[str] = Counter()
    topology_profiles: Counter[str] = Counter()
    node_colors: Counter[str] = Counter()
    for index in range(54):
        out = task.generate(
            hash64(19644, "graph_order_topological_position", index),
            params={"_sampling_index": index},
            max_attempts=80,
        )
        execution = out.trace_payload["execution_trace"]
        node_counts[int(execution["node_count"])] += 1
        target_positions[int(execution["target_position"])] += 1
        label_variants[str(execution["label_variant"])] += 1
        node_shape_variants[str(execution["node_shape_variant"])] += 1
        layout_variants[str(execution["layout_variant_requested"])] += 1
        topology_profiles[str(execution["topology_profile"])] += 1
        node_colors[str(execution["node_color_name"])] += 1
        assert 5 <= int(execution["node_count"]) <= 7
        assert 1 <= int(execution["target_position"]) <= int(execution["node_count"])
    assert set(node_counts.keys()) == {5, 6, 7}
    assert set(label_variants.keys()) == {"letters", "numbers"}
    assert set(node_shape_variants.keys()) == {"circle", "rounded_square", "hexagon"}
    assert set(layout_variants.keys()) == {"circular", "shell", "spring"}
    assert set(topology_profiles.keys()) == {"balanced", "hub_heavy", "low_degree"}
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
    assert min(target_positions.keys()) == 1
