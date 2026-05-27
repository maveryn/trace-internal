"""Behavior tests for graph extreme-degree comparison task."""

from __future__ import annotations

import json
from collections import Counter

from trace.core.seed import hash64
from trace.tasks import TASK_REGISTRY
from trace.tasks.graph.comparison.extreme_degree_value import GraphComparisonExtremeDegreeValueTask


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def _observed_extreme(values: dict[str, int], *, extremum_mode: str) -> int:
    return max(values.values()) if str(extremum_mode) == "max" else min(values.values())


def test_graph_comparison_extreme_degree_value_undirected_contract_matches_trace() -> None:
    task = GraphComparisonExtremeDegreeValueTask()
    out = task.generate(
        20401,
        params={
            "graph_directionality": "undirected",
            "degree_mode": "degree",
            "extremum_mode": "max",
            "node_count": 7,
            "target_degree": 2,
            "label_variant": "named",
            "edge_routing_variant": "mixed_arc",
            "layout_variant": "shell",
        },
        max_attempts=200,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    node_entities = [
        entity for entity in trace["scene_ir"]["entities"] if entity["entity_kind"] == "graph_node"
    ]

    assert "task_graph__node_link__degree_extremum_value" in TASK_REGISTRY
    assert out.scene_id == "node_link"
    assert out.query_id == "default"
    assert out.query_id == "undirected_max_degree_value"
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "point_set"
    assert int(out.answer_gt.value) == 2
    assert trace["scene_ir"]["scene_kind"] == "graph_extreme_degree_comparison"
    assert execution["query_id"] == "default"
    assert execution["query_id"] == "undirected_max_degree_value"
    assert execution["graph_directionality"] == "undirected"
    assert execution["degree_mode"] == "degree"
    assert execution["extremum_mode"] == "max"
    assert execution["question_format"] == "max_degree_value"
    assert execution["layout_variant_requested"] == "shell"
    assert execution["edge_routing_variant"] == "mixed_arc"
    assert execution["label_variant"] == "named"

    queried = {str(label): int(value) for label, value in execution["queried_degrees_by_label"].items()}
    matching_labels = [str(label) for label in execution["matching_labels"]]
    assert _observed_extreme(queried, extremum_mode="max") == int(out.answer_gt.value)
    assert matching_labels == trace["witness_symbolic"]["labels"]
    assert all(queried[str(label)] == int(out.answer_gt.value) for label in matching_labels)
    assert sorted(
        label for label, degree in queried.items() if int(degree) == int(out.answer_gt.value)
    ) == sorted(matching_labels)
    assert len(out.evidence_gt.value) == len(matching_labels)
    assert trace["projected_evidence"]["type"] == "point_set"
    assert trace["projected_evidence"]["point_set"] == out.evidence_gt.value
    assert sum(1 for node in node_entities if bool(node["is_extreme_degree_node"])) == len(matching_labels)
    assert all(
        int(node["queried_degree"]) == int(out.answer_gt.value)
        for node in node_entities
        if bool(node["is_extreme_degree_node"])
    )
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert 0.0 <= float(out.complexity.complexity_score) <= 1.0


def test_graph_comparison_extreme_degree_value_directed_modes_use_correct_degree_map() -> None:
    task = GraphComparisonExtremeDegreeValueTask()
    for index, (degree_mode, extremum_mode) in enumerate(
        (
            ("in_degree", "max"),
            ("in_degree", "min"),
            ("out_degree", "max"),
            ("out_degree", "min"),
            ("total_degree", "max"),
            ("total_degree", "min"),
        )
    ):
        out = task.generate(
            20410 + index,
            params={
                "graph_directionality": "directed",
                "degree_mode": degree_mode,
                "extremum_mode": extremum_mode,
                "node_count": 8,
                "target_degree": 2,
                "label_variant": "letters",
            },
            max_attempts=200,
        )
        trace = out.trace_payload
        execution = trace["execution_trace"]
        queried = {str(label): int(value) for label, value in execution["queried_degrees_by_label"].items()}
        expected_query_id = f"directed_{extremum_mode}_{degree_mode.replace('_degree', '')}_degree_value"
        if degree_mode == "total_degree":
            expected_query_id = f"directed_{extremum_mode}_total_degree_value"

        assert out.query_id == expected_query_id
        assert execution["query_id"] == expected_query_id
        assert execution["graph_directionality"] == "directed"
        assert execution["degree_mode"] == degree_mode
        assert execution["extremum_mode"] == extremum_mode
        assert int(out.answer_gt.value) == _observed_extreme(queried, extremum_mode=extremum_mode)
        assert int(out.answer_gt.value) == 2
        assert len(out.evidence_gt.value) == len(execution["matching_labels"])
        assert all(
            queried[str(label)] == int(out.answer_gt.value)
            for label in execution["matching_labels"]
        )
        assert any(
            bool(entity["directed"])
            for entity in trace["scene_ir"]["entities"]
            if entity["entity_kind"] == "graph_edge"
        ) or int(execution["edge_count"]) == 0


def test_graph_comparison_extreme_degree_value_prompt_examples_match_contract() -> None:
    task = GraphComparisonExtremeDegreeValueTask()
    out = task.generate(
        20420,
        params={
            "graph_directionality": "undirected",
            "extremum_mode": "min",
            "node_count": 8,
            "target_degree": 1,
            "label_variant": "letters",
        },
        max_attempts=200,
    )
    answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
    answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert answer_only == {"answer": 3}
    assert list(answer_and_evidence.keys()) == ["evidence", "answer"]
    assert answer_and_evidence["evidence"] == [[180, 220], [310, 180]]
    assert answer_and_evidence["answer"] == 3


def test_graph_comparison_extreme_degree_value_balanced_sampling_defaults() -> None:
    task = GraphComparisonExtremeDegreeValueTask()
    query_ids: Counter[str] = Counter()
    directionality: Counter[str] = Counter()
    degree_modes: Counter[str] = Counter()
    extrema: Counter[str] = Counter()
    target_degrees: Counter[int] = Counter()
    label_variants: Counter[str] = Counter()
    edge_routing_variants: Counter[str] = Counter()
    for index in range(160):
        out = task.generate(
            hash64(20430, "graph_comparison_extreme_degree_value", index),
            params={},
            max_attempts=200,
        )
        execution = out.trace_payload["execution_trace"]
        query_ids[str(execution["query_id"])] += 1
        directionality[str(execution["graph_directionality"])] += 1
        degree_modes[str(execution["degree_mode"])] += 1
        extrema[str(execution["extremum_mode"])] += 1
        target_degrees[int(execution["target_degree"])] += 1
        label_variants[str(execution["label_variant"])] += 1
        edge_routing_variants[str(execution["edge_routing_variant"])] += 1
        assert 5 <= int(execution["node_count"]) <= 10
        assert 0 <= int(execution["target_degree"]) <= 4
        assert int(out.answer_gt.value) == int(execution["target_degree"])
    assert set(query_ids) == {
        "undirected_max_degree_value",
        "undirected_min_degree_value",
        "directed_max_in_degree_value",
        "directed_min_in_degree_value",
        "directed_max_out_degree_value",
        "directed_min_out_degree_value",
        "directed_max_total_degree_value",
        "directed_min_total_degree_value",
    }
    assert set(directionality) == {"undirected", "directed"}
    assert set(degree_modes) == {"degree", "in_degree", "out_degree", "total_degree"}
    assert set(extrema) == {"max", "min"}
    assert set(target_degrees) == set(range(0, 5))
    assert set(label_variants) == {"letters", "numbers", "named"}
    assert set(edge_routing_variants) == {"straight", "mixed_arc"}
