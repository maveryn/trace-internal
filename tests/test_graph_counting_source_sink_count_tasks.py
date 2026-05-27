"""Behavior tests for graph source/sink counting task."""

from __future__ import annotations

import json
from collections import Counter

from trace.core.seed import hash64
from trace.tasks import TASK_REGISTRY
from trace.tasks.graph.counting.source_sink_count import GraphCountingSourceSinkCountTask


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def test_graph_counting_source_count_contract_matches_trace() -> None:
    task = GraphCountingSourceSinkCountTask()
    out = task.generate(
        20501,
        params={
            "source_sink_mode": "source",
            "target_count": 2,
            "node_count": 8,
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

    assert "task_graph__node_link__degree_predicate_count" in TASK_REGISTRY
    assert out.scene_id == "node_link"
    assert out.query_variant == "default"
    assert out.query_id == "directed_source_count"
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "point_set"
    assert int(out.answer_gt.value) == 2
    assert trace["scene_ir"]["scene_kind"] == "graph_source_sink_counting"
    assert execution["query_variant"] == "default"
    assert execution["query_id"] == "directed_source_count"
    assert execution["graph_directionality"] == "directed"
    assert execution["source_sink_mode"] == "source"
    assert execution["degree_mode"] == "in_degree"
    assert execution["query_degree"] == 0
    assert execution["question_format"] == "source_count"
    assert execution["layout_variant_requested"] == "shell"
    assert execution["edge_routing_variant"] == "mixed_arc"
    assert execution["label_variant"] == "named"
    assert "no incoming" in str(out.prompt) or "in-degree 0" in str(out.prompt)

    in_degrees = {str(key): int(value) for key, value in execution["in_degrees_by_label"].items()}
    matching_labels = [str(label) for label in execution["matching_labels"]]
    assert sorted(label for label, value in in_degrees.items() if int(value) == 0) == sorted(matching_labels)
    assert int(out.answer_gt.value) == len(matching_labels) == len(out.evidence_gt.value)
    assert trace["witness_symbolic"]["labels"] == matching_labels
    assert trace["witness_symbolic"]["source_sink_mode"] == "source"
    assert trace["projected_evidence"]["type"] == "point_set"
    assert trace["projected_evidence"]["point_set"] == out.evidence_gt.value
    assert sum(1 for node in node_entities if bool(node["is_source_sink_node"])) == len(matching_labels)
    assert all(
        int(node["in_degree"]) == 0
        for node in node_entities
        if bool(node["is_source_sink_node"])
    )
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]


def test_graph_counting_sink_count_zero_answer_is_supported() -> None:
    task = GraphCountingSourceSinkCountTask()
    out = task.generate(
        20502,
        params={
            "source_sink_mode": "sink",
            "target_count": 0,
            "node_count": 7,
            "label_variant": "letters",
        },
        max_attempts=200,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    out_degrees = {str(key): int(value) for key, value in execution["out_degrees_by_label"].items()}

    assert out.query_id == "directed_sink_count"
    assert int(out.answer_gt.value) == 0
    assert out.evidence_gt.value == []
    assert execution["source_sink_mode"] == "sink"
    assert execution["degree_mode"] == "out_degree"
    assert execution["query_degree"] == 0
    assert execution["target_count"] == 0
    assert execution["matching_labels"] == []
    assert all(int(value) > 0 for value in out_degrees.values())
    assert "no outgoing" in str(out.prompt) or "out-degree 0" in str(out.prompt)


def test_graph_counting_source_sink_prompt_examples_match_contract() -> None:
    task = GraphCountingSourceSinkCountTask()
    out = task.generate(
        20503,
        params={
            "source_sink_mode": "source",
            "target_count": 2,
            "label_variant": "numbers",
        },
        max_attempts=200,
    )
    answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
    answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert answer_only == {"answer": 2}
    assert list(answer_and_evidence.keys()) == ["evidence", "answer"]
    assert answer_and_evidence["evidence"] == [[180, 220], [310, 180]]
    assert answer_and_evidence["answer"] == 2


def test_graph_counting_source_sink_balanced_sampling_includes_zero() -> None:
    task = GraphCountingSourceSinkCountTask()
    query_ids: Counter[str] = Counter()
    modes: Counter[str] = Counter()
    answers: Counter[int] = Counter()
    label_variants: Counter[str] = Counter()
    edge_routing_variants: Counter[str] = Counter()
    for index in range(100):
        out = task.generate(
            hash64(20510, "graph_counting_source_sink_count", index),
            params={},
            max_attempts=200,
        )
        execution = out.trace_payload["execution_trace"]
        query_ids[str(execution["query_id"])] += 1
        modes[str(execution["source_sink_mode"])] += 1
        answers[int(out.answer_gt.value)] += 1
        label_variants[str(execution["label_variant"])] += 1
        edge_routing_variants[str(execution["edge_routing_variant"])] += 1
        assert execution["graph_directionality"] == "directed"
        assert int(execution["query_degree"]) == 0
        assert int(out.answer_gt.value) == int(execution["target_count"])
        assert 0 <= int(out.answer_gt.value) <= 4

    assert set(query_ids) == {"directed_source_count", "directed_sink_count"}
    assert set(modes) == {"source", "sink"}
    assert set(answers) == set(range(0, 5))
    assert all(count > 0 for count in answers.values())
    assert set(label_variants) == {"letters", "numbers", "named"}
    assert set(edge_routing_variants) == {"straight", "mixed_arc"}
