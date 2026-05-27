"""Behavior tests for graph edge-attribute label relation task."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.core.seed import hash64
from trace.tasks import TASK_REGISTRY
from trace.tasks.graph.relation.edge_attribute_label import GraphRelationEdgeAttributeLabelTask
from tests.helpers import read_jsonl


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def test_graph_relation_edge_attribute_label_directed_contract_matches_trace() -> None:
    task = GraphRelationEdgeAttributeLabelTask()
    out = task.generate(
        20901,
        params={
            "graph_directionality": "directed",
            "target_edge_label": "feeds",
            "edge_label_support": ["feeds", "blocks", "joins", "routes", "checks", "updates"],
            "node_count": 7,
            "label_variant": "named",
            "edge_routing_variant": "mixed_arc",
            "layout_variant": "shell",
        },
        max_attempts=100,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    edge_entities = [
        entity for entity in trace["scene_ir"]["entities"] if entity["entity_kind"] == "graph_edge"
    ]

    assert "task_graph__node_link__edge_attribute_label" in TASK_REGISTRY
    assert out.scene_id == "node_link"
    assert out.query_id == "default"
    assert out.query_id == "directed_edge_between_nodes_label"
    assert out.answer_gt.type == "string"
    assert out.answer_gt.value == "feeds"
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == 1
    assert trace["scene_ir"]["scene_kind"] == "graph_edge_attribute_relation"
    assert execution["query_id"] == "default"
    assert execution["query_id"] == "directed_edge_between_nodes_label"
    assert execution["graph_directionality"] == "directed"
    assert execution["target_edge_label"] == "feeds"
    assert execution["question_format"] == "directed_edge_between_nodes_label"
    assert execution["layout_variant_requested"] == "shell"
    assert execution["edge_routing_variant"] == "mixed_arc"
    assert execution["label_variant"] == "named"
    assert 'node "' in str(out.prompt)

    query_edge = tuple(str(value) for value in execution["query_edge"])
    labels_by_edge = {
        tuple(str(value) for value in entry["edge"]): str(entry["edge_label"])
        for entry in execution["edge_attribute_labels_by_label_pair"]
    }
    assert labels_by_edge[query_edge] == "feeds"
    assert trace["witness_symbolic"]["edge"] == list(query_edge)
    assert trace["witness_symbolic"]["edge_label"] == "feeds"
    assert trace["projected_evidence"]["type"] == "bbox_set"
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert sum(1 for edge in edge_entities if bool(edge["is_query_edge"])) == 1
    query_entity = [edge for edge in edge_entities if bool(edge["is_query_edge"])][0]
    assert query_entity["edge_attribute_label"] == "feeds"
    assert query_entity["edge_label_bbox_xyxy"] == out.evidence_gt.value[0]
    assert all(edge["edge_label_bbox_xyxy"] is not None for edge in edge_entities)
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]


def test_graph_relation_edge_attribute_label_undirected_prompt_and_example_contract() -> None:
    task = GraphRelationEdgeAttributeLabelTask()
    out = task.generate(
        20902,
        params={
            "graph_directionality": "undirected",
            "target_edge_label": "blocks",
            "edge_label_support": ["feeds", "blocks", "joins", "routes", "checks", "updates"],
            "label_variant": "numbers",
        },
        max_attempts=100,
    )

    assert out.query_id == "edge_between_nodes_label"
    assert out.answer_gt.value == "blocks"
    assert "edge" in str(out.prompt)
    answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
    answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert answer_only == {"answer": "feeds"}
    assert list(answer_and_evidence.keys()) == ["evidence", "answer"]
    assert answer_and_evidence["evidence"] == [[240, 190, 308, 214]]
    assert answer_and_evidence["answer"] == "feeds"


def test_graph_relation_edge_attribute_label_shortest_path_first_edge_contract() -> None:
    task = GraphRelationEdgeAttributeLabelTask()
    out = task.generate(
        20903,
        params={
            "query_id": "shortest_path_first_edge_label",
            "graph_directionality": "directed",
            "target_edge_label": "routes",
            "edge_label_support": ["feeds", "blocks", "joins", "routes", "checks", "updates"],
            "target_shortest_path_length": 3,
            "label_variant": "letters",
        },
        max_attempts=100,
    )
    execution = out.trace_payload["execution_trace"]

    assert out.query_id == "shortest_path_first_edge_label"
    assert out.answer_gt.value == "routes"
    assert "unique shortest path" in str(out.prompt)
    assert "first arrow" in str(out.prompt)
    path_labels = tuple(str(label) for label in execution["query_path_labels"])
    assert len(path_labels) == 4
    assert tuple(execution["query_edge"]) == (path_labels[0], path_labels[1])
    assert execution["query_path_edge_index"] == 0
    assert execution["query_path_edge_position"] == "first"
    labels_by_edge = {
        tuple(str(value) for value in entry["edge"]): str(entry["edge_label"])
        for entry in execution["edge_attribute_labels_by_label_pair"]
    }
    assert labels_by_edge[tuple(execution["query_edge"])] == "routes"
    query_entity = [
        entity
        for entity in out.trace_payload["scene_ir"]["entities"]
        if entity["entity_kind"] == "graph_edge" and bool(entity["is_query_edge"])
    ][0]
    assert query_entity["edge_label_bbox_xyxy"] == out.evidence_gt.value[0]


def test_graph_relation_edge_attribute_label_balanced_sampling_covers_label_support() -> None:
    task = GraphRelationEdgeAttributeLabelTask()
    answers: Counter[str] = Counter()
    query_ids: Counter[str] = Counter()
    directionality: Counter[str] = Counter()
    label_variants: Counter[str] = Counter()
    edge_routing_variants: Counter[str] = Counter()
    for index in range(180):
        out = task.generate(
            hash64(20910, "graph_relation_edge_attribute_label", index),
            params={},
            max_attempts=100,
        )
        execution = out.trace_payload["execution_trace"]
        answers[str(out.answer_gt.value)] += 1
        query_ids[str(out.query_id)] += 1
        directionality[str(execution["graph_directionality"])] += 1
        label_variants[str(execution["label_variant"])] += 1
        edge_routing_variants[str(execution["edge_routing_variant"])] += 1
        query_edge = tuple(str(value) for value in execution["query_edge"])
        labels_by_edge = {
            tuple(str(value) for value in entry["edge"]): str(entry["edge_label"])
            for entry in execution["edge_attribute_labels_by_label_pair"]
        }
        assert labels_by_edge[query_edge] == str(out.answer_gt.value)
        assert str(out.answer_gt.value) in set(execution["edge_label_support"])
        assert execution["edge_label_source_kind"] == "shared_label_manifest"
        assert execution["edge_label_bucket"]
        assert execution["edge_label_manifest"]
        assert len(out.evidence_gt.value) == 1

    assert len(answers) > 12
    assert set(query_ids) == {
        "edge_between_nodes_label",
        "directed_edge_between_nodes_label",
        "shortest_path_first_edge_label",
    }
    assert all(count > 0 for count in query_ids.values())
    assert set(directionality) == {"undirected", "directed"}
    assert set(label_variants) == {"letters", "numbers", "named"}
    assert set(edge_routing_variants) == {"straight", "mixed_arc"}


def test_graph_relation_edge_attribute_label_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "graph_edge_attribute_label"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_graph_edge_attribute_label",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_graph__node_link__edge_attribute_label",
                count=4,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=100,
        sampling_seed=39,
    )
    final_path = build_dataset(config, code_hash="graph-relation-edge-attribute-label-smoke")
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 4
    assert all(record["domain"] == "graph" for record in train_records)
    assert all(record["task_group"] == "relation" for record in train_records)
    assert all(record["scene_id"] == "node_link" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"]["task_graph__node_link__edge_attribute_label"]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
