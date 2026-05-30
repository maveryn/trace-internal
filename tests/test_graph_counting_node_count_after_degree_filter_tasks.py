"""Behavior tests for graph degree-filter remaining-node counting."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.core.seed import hash64
from trace.tasks import TASK_REGISTRY
from trace.tasks.graph.counting.node_count_after_degree_filter import GraphCountingNodeCountAfterDegreeFilterTask
from tests.helpers import read_jsonl


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def test_graph_counting_node_count_after_degree_filter_contract_matches_trace() -> None:
    task = GraphCountingNodeCountAfterDegreeFilterTask()
    out = task.generate(
        22001,
        params={
            "graph_directionality": "directed",
            "degree_mode": "in_degree",
            "target_count": 3,
            "node_count": 8,
            "label_variant": "named",
            "edge_routing_variant": "mixed_arc",
            "layout_variant": "shell",
        },
        max_attempts=100,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    node_entities = [
        entity for entity in trace["scene_ir"]["entities"] if entity["entity_kind"] == "graph_node"
    ]

    assert "task_graph__node_link__degree_predicate_count" in TASK_REGISTRY
    assert out.scene_id == "node_link"
    assert out.query_id == "directed_in_degree_one_filter_remaining_count"
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "point_set"
    assert int(out.answer_gt.value) == 3
    assert trace["scene_ir"]["scene_kind"] == "graph_degree_filter_remaining_counting"
    assert execution["query_id"] == "directed_in_degree_one_filter_remaining_count"
    assert execution["graph_directionality"] == "directed"
    assert execution["degree_mode"] == "in_degree"
    assert execution["filter_degree"] == 1
    assert execution["layout_variant_requested"] == "shell"
    assert execution["edge_routing_variant"] == "mixed_arc"
    assert execution["label_variant"] == "named"

    remaining_labels = [str(label) for label in execution["remaining_labels"]]
    removed_labels = [str(label) for label in execution["removed_labels"]]
    queried_degrees = {str(label): int(value) for label, value in execution["queried_degrees_by_label"].items()}
    assert len(remaining_labels) == int(out.answer_gt.value) == len(out.evidence_gt.value)
    assert len(removed_labels) == int(execution["removed_count"])
    assert len(remaining_labels) + len(removed_labels) == int(execution["node_count"])
    assert all(queried_degrees[label] != 1 for label in remaining_labels)
    assert all(queried_degrees[label] == 1 for label in removed_labels)
    assert trace["witness_symbolic"]["labels"] == remaining_labels
    assert trace["witness_symbolic"]["removed_labels"] == removed_labels
    assert sum(1 for node in node_entities if bool(node["is_remaining_after_filter"])) == 3
    assert sum(1 for node in node_entities if bool(node["is_removed_by_filter"])) == int(execution["removed_count"])
    assert trace["projected_evidence"]["type"] == "point_set"
    assert trace["projected_evidence"]["point_set"] == out.evidence_gt.value
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]


def test_graph_counting_node_count_after_degree_filter_zero_answer() -> None:
    task = GraphCountingNodeCountAfterDegreeFilterTask()
    out = task.generate(
        22002,
        params={
            "graph_directionality": "undirected",
            "target_count": 0,
            "node_count": 6,
            "label_variant": "letters",
        },
        max_attempts=100,
    )
    execution = out.trace_payload["execution_trace"]

    assert out.query_id == "undirected_degree_one_filter_remaining_count"
    assert int(out.answer_gt.value) == 0
    assert out.evidence_gt.value == []
    assert execution["remaining_labels"] == []
    assert len(execution["removed_labels"]) == int(execution["node_count"])
    assert all(int(value) == 1 for value in execution["queried_degrees_by_label"].values())


def test_graph_counting_node_count_after_degree_filter_prompt_examples_match_contract() -> None:
    task = GraphCountingNodeCountAfterDegreeFilterTask()
    out = task.generate(
        22003,
        params={"graph_directionality": "directed", "degree_mode": "out_degree", "target_count": 3},
        max_attempts=100,
    )
    answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
    answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert answer_only == {"answer": 3}
    assert list(answer_and_evidence.keys()) == ["evidence", "answer"]
    assert answer_and_evidence["evidence"] == [[180, 220], [310, 180], [430, 260]]
    assert answer_and_evidence["answer"] == 3


def test_graph_counting_node_count_after_degree_filter_balanced_sampling_includes_zero() -> None:
    task = GraphCountingNodeCountAfterDegreeFilterTask()
    answers: Counter[int] = Counter()
    directionality: Counter[str] = Counter()
    query_ids: Counter[str] = Counter()
    label_variants: Counter[str] = Counter()
    edge_routing_variants: Counter[str] = Counter()
    for index in range(70):
        out = task.generate(
            hash64(22010, "graph_counting_node_count_after_degree_filter", index),
            params={},
            max_attempts=100,
        )
        execution = out.trace_payload["execution_trace"]
        answers[int(out.answer_gt.value)] += 1
        directionality[str(execution["graph_directionality"])] += 1
        query_ids[str(execution["query_id"])] += 1
        label_variants[str(execution["label_variant"])] += 1
        edge_routing_variants[str(execution["edge_routing_variant"])] += 1
        assert int(out.answer_gt.value) == int(execution["target_count"])
        assert 0 <= int(out.answer_gt.value) <= 6

    assert set(answers) == set(range(0, 7))
    assert all(count > 0 for count in answers.values())
    assert set(directionality) == {"undirected", "directed"}
    assert set(query_ids) == {
        "undirected_degree_one_filter_remaining_count",
        "directed_in_degree_one_filter_remaining_count",
        "directed_out_degree_one_filter_remaining_count",
    }
    assert set(label_variants) == {"letters", "numbers", "named"}
    assert set(edge_routing_variants) == {"straight", "mixed_arc"}


def test_graph_counting_node_count_after_degree_filter_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "graph_node_count_after_degree_filter"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_graph_node_count_after_degree_filter",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_graph__node_link__degree_predicate_count",
                count=4,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=100,
        sampling_seed=37,
    )
    final_path = build_dataset(config, code_hash="graph-node-count-after-degree-filter-smoke")
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 4
    assert all(record["domain"] == "graph" for record in train_records)
    assert all(record["task_group"] == "counting" for record in train_records)
    assert all(record["scene_id"] == "node_link" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"]["task_graph__node_link__degree_predicate_count"]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
