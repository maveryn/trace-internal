"""Behavior tests for graph shortest-path-length task."""

from __future__ import annotations

import json
from collections import Counter

from trace.core.seed import hash64
from trace.tasks.graph.path.shortest_path_length import GraphPathShortestPathLengthTask
from trace.tasks.shared.graph_algorithms import bfs_dist_count_by_adjacency, reconstruct_unique_shortest_path_by_adjacency
from trace.tasks.shared.named_colors import named_color


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def test_graph_path_shortest_path_length_contract_matches_trace() -> None:
    task = GraphPathShortestPathLengthTask()
    out = task.generate(
        19601,
        params={
            "node_count": 8,
            "target_shortest_path_length": 4,
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
    assert out.evidence_gt.type == "label_path"
    assert int(out.answer_gt.value) == len(out.evidence_gt.value) - 1
    assert trace["scene_ir"]["scene_kind"] == "graph_shortest_path_length"
    assert execution["question_format"] == "count_edges_in_unique_shortest_path"
    assert execution["graph_directionality"] == "undirected"
    assert 5 <= int(execution["node_count"]) <= 10
    assert 1 <= int(execution["target_shortest_path_length"]) <= 5
    assert str(execution["source_label"]) == str(out.evidence_gt.value[0])
    assert str(execution["goal_label"]) == str(out.evidence_gt.value[-1])
    assert len(node_entities) == 8
    assert len(edge_entities) == int(execution["edge_count"])
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert trace["query_spec"]["prompt_variant_active_key"] == "answer_and_evidence"
    assert set(out.complexity.complexity_components.keys()) == {
        "visual_scan",
        "topology_reasoning",
        "ambiguity",
        "clutter",
    }
    assert all(0.0 <= float(value) <= 1.0 for value in out.complexity.complexity_components.values())

    adjacency_by_label = {str(key): [str(value) for value in values] for key, values in execution["adjacency_by_label"].items()}
    dist_start, count_start = bfs_dist_count_by_adjacency(adjacency_by_label, start=str(execution["source_label"]))
    dist_goal, _ = bfs_dist_count_by_adjacency(adjacency_by_label, start=str(execution["goal_label"]))
    reconstructed = reconstruct_unique_shortest_path_by_adjacency(
        adjacency_by_label,
        start=str(execution["source_label"]),
        goal=str(execution["goal_label"]),
        dist_start=dist_start,
        dist_goal=dist_goal,
    )
    assert reconstructed == list(out.evidence_gt.value)
    assert int(dist_start[str(execution["goal_label"])]) == int(out.answer_gt.value)
    assert int(count_start[str(execution["goal_label"])]) == 1

    assert trace["projected_evidence"]["label_path"] == out.evidence_gt.value
    assert len(trace["projected_evidence"]["pixel_point_path"]) == len(out.evidence_gt.value)
    assert len(trace["projected_evidence"]["pixel_bbox_set"]) == len(out.evidence_gt.value)


def test_graph_path_directed_shortest_path_contract_matches_trace() -> None:
    task = GraphPathShortestPathLengthTask()
    out = task.generate(
        19611,
        params={
            "task_variant": "directed_shortest_path_length",
            "node_count": 9,
            "target_shortest_path_length": 4,
            "layout_variant": "shell",
            "topology_profile": "balanced",
            "label_variant": "letters",
        },
        max_attempts=80,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    scene_entities = trace["scene_ir"]["entities"]
    edge_entities = [entity for entity in scene_entities if entity["entity_kind"] == "graph_edge"]

    assert execution["graph_directionality"] == "directed"
    assert trace["query_spec"]["params"]["graph_directionality"] == "directed"
    assert trace["scene_ir"]["relations"]["graph_directionality"] == "directed"
    assert all(bool(edge["directed"]) for edge in edge_entities)
    assert 5 <= int(execution["node_count"]) <= 9
    assert 1 <= int(execution["target_shortest_path_length"]) <= 5
    assert int(out.answer_gt.value) == 4

    successors = {str(key): [str(value) for value in values] for key, values in trace["scene_ir"]["relations"]["adjacency_by_label"].items()}
    predecessors = {
        str(entity["label"]): [str(value) for value in entity["predecessors"]]
        for entity in scene_entities
        if entity["entity_kind"] == "graph_node"
    }
    dist_start, count_start = bfs_dist_count_by_adjacency(successors, start=str(execution["source_label"]))
    dist_goal, _ = bfs_dist_count_by_adjacency(predecessors, start=str(execution["goal_label"]))
    reconstructed = reconstruct_unique_shortest_path_by_adjacency(
        successors,
        start=str(execution["source_label"]),
        goal=str(execution["goal_label"]),
        dist_start=dist_start,
        dist_goal=dist_goal,
    )
    assert reconstructed == list(out.evidence_gt.value)
    assert int(dist_start[str(execution["goal_label"])]) == int(out.answer_gt.value)
    assert int(count_start[str(execution["goal_label"])]) == 1
    assert "following the direction of the arrows" in str(out.prompt)


def test_graph_path_shortest_path_prompt_examples_follow_label_variant() -> None:
    task = GraphPathShortestPathLengthTask()
    letters = task.generate(
        19602,
        params={"label_variant": "letters", "node_count": 8, "target_shortest_path_length": 3},
        max_attempts=80,
    )
    numbers = task.generate(
        19603,
        params={"label_variant": "numbers", "node_count": 8, "target_shortest_path_length": 3},
        max_attempts=80,
    )
    letters_example = _extract_prompt_json_example(letters.prompt_variants["answer_and_evidence"])
    numbers_example = _extract_prompt_json_example(numbers.prompt_variants["answer_and_evidence"])
    assert letters_example == {"evidence": ["B", "D", "H"], "answer": 2}
    assert numbers_example == {"evidence": ["2", "5", "8"], "answer": 2}


def test_graph_path_shortest_path_supports_numeric_labels_and_named_colors() -> None:
    task = GraphPathShortestPathLengthTask()
    out = task.generate(
        19604,
        params={
            "task_variant": "shortest_path_length",
            "node_count": 10,
            "target_shortest_path_length": 5,
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


def test_graph_path_shortest_path_balanced_sampling_defaults() -> None:
    task = GraphPathShortestPathLengthTask()
    task_variants: Counter[str] = Counter()
    target_lengths: Counter[int] = Counter()
    layout_variants: Counter[str] = Counter()
    topology_profiles: Counter[str] = Counter()
    label_variants: Counter[str] = Counter()
    node_shapes: Counter[str] = Counter()
    layout_transforms: Counter[str] = Counter()
    node_colors: Counter[str] = Counter()
    for index in range(50):
        out = task.generate(
            hash64(19605, "graph_path_shortest_path_length", index),
            params={"_sampling_index": index},
            max_attempts=80,
        )
        execution = out.trace_payload["execution_trace"]
        task_variants[str(execution["task_variant"])] += 1
        target_lengths[int(execution["target_shortest_path_length"])] += 1
        layout_variants[str(execution["layout_variant_requested"])] += 1
        topology_profiles[str(execution["topology_profile"])] += 1
        label_variants[str(execution["label_variant"])] += 1
        node_shapes[str(execution["node_shape_variant"])] += 1
        layout_transforms[str(execution["layout_transform_variant"])] += 1
        node_colors[str(execution["node_color_name"])] += 1
        if str(execution["graph_directionality"]) == "directed":
            assert 5 <= int(execution["node_count"]) <= 9
        else:
            assert 5 <= int(execution["node_count"]) <= 10
        assert 1 <= int(execution["target_shortest_path_length"]) <= 5
        assert int(execution["attachment_count"]) >= 1
        assert int(out.answer_gt.value) == int(execution["target_shortest_path_length"])
    assert set(task_variants.keys()) == {"shortest_path_length", "directed_shortest_path_length"}
    assert set(target_lengths.keys()) == {1, 2, 3, 4, 5}
    assert set(layout_variants.keys()) == {"circular", "shell", "spring"}
    assert set(topology_profiles.keys()) == {"balanced", "hub_heavy", "low_degree"}
    assert set(label_variants.keys()) == {"letters", "numbers"}
    assert set(node_shapes.keys()) == {"circle", "rounded_square", "hexagon"}
    assert set(layout_transforms.keys()) == {
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
