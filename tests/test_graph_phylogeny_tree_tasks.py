"""Regression tests for graph-domain phylogeny tree tasks."""

from __future__ import annotations

from io import BytesIO

import trace.tasks  # noqa: F401
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks.graph.counting.phylogeny_tree_count import TASK_ID as CLADE_COUNT_TASK_ID
from trace.tasks.graph.relation.phylogeny_tree_relation import (
    MRCA_TASK_ID,
    SISTER_TASK_ID,
    TOPOLOGY_TASK_ID,
    GraphRelationPhylogenyMrcaCladeMembershipCountTask,
    GraphRelationPhylogenySisterLeafLabelTask,
    GraphRelationPhylogenyTopologyOutlierLabelTask,
)
from trace.tasks.graph.shared.phylogeny_tree_scene import sample_topology_outlier_options
from trace.tasks.registry import TASK_REGISTRY, create_task


PHYLOGENY_TASK_IDS = (
    CLADE_COUNT_TASK_ID,
    SISTER_TASK_ID,
    MRCA_TASK_ID,
    TOPOLOGY_TASK_ID,
)


def _png_bytes(output) -> bytes:
    buffer = BytesIO()
    output.image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_phylogeny_tasks_are_registered_and_taxonomized() -> None:
    for task_id in PHYLOGENY_TASK_IDS:
        assert task_id in TASK_REGISTRY
        taxonomy = resolve_task_taxonomy(task_id)
        assert taxonomy.domain == "graph"
        assert taxonomy.scene_id == "phylogeny_tree"
        assert taxonomy.source_domain == "graph"


def test_phylogeny_clade_leaf_count_contract() -> None:
    out = create_task(CLADE_COUNT_TASK_ID).generate(3101, params={}, max_attempts=200)
    trace = out.trace_payload
    expected_labels = trace["execution_trace"]["target_leaf_labels"]
    assert out.scene_id == "phylogeny_tree"
    assert out.query_id == "marked_clade_leaf_count"
    assert out.answer_gt.type == "integer"
    assert out.annotation_gt.type == "point_set"
    assert out.answer_gt.value == len(expected_labels)
    assert len(out.annotation_gt.value) == len(expected_labels)
    assert trace["projected_annotation"]["point_set"] == out.annotation_gt.value
    assert trace["scene_ir"]["relations"]["marked_clade_leaf_labels"] == expected_labels


def test_phylogeny_sister_leaf_label_contract() -> None:
    out = GraphRelationPhylogenySisterLeafLabelTask().generate(4102, params={}, max_attempts=200)
    trace = out.trace_payload
    assert out.query_id == "sister_leaf_label"
    assert out.answer_gt.type == "string"
    assert out.annotation_gt.type == "keyed_bbox_map"
    assert set(out.annotation_gt.value.keys()) == {"target_leaf", "sister_leaf", "shared_parent"}
    assert out.answer_gt.value == trace["execution_trace"]["sister_leaf_label"]
    assert trace["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value


def test_phylogeny_mrca_leaf_count_contract() -> None:
    out = GraphRelationPhylogenyMrcaCladeMembershipCountTask().generate(5103, params={}, max_attempts=240)
    trace = out.trace_payload
    expected_labels = trace["execution_trace"]["mrca_descendant_leaf_labels"]
    assert out.query_id == "mrca_leaf_count"
    assert out.answer_gt.type == "integer"
    assert out.annotation_gt.type == "keyed_bbox_map"
    assert set(out.annotation_gt.value.keys()) == {"query_leaf_1", "query_leaf_2", "mrca"}
    assert out.answer_gt.value == len(expected_labels)
    assert trace["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value


def test_phylogeny_topology_outlier_contract() -> None:
    out = GraphRelationPhylogenyTopologyOutlierLabelTask().generate(6104, params={}, max_attempts=240)
    trace = out.trace_payload
    assert out.query_id == "topology_outlier_label"
    assert out.answer_gt.type == "string"
    assert out.annotation_gt.type == "bbox_set"
    assert len(out.annotation_gt.value) == 1
    assert out.answer_gt.value in {"A", "B", "C", "D", "E", "F"}
    option_records = trace["execution_trace"]["option_records"]
    assert len(option_records) == 6
    assert [record["option_label"] for record in option_records] == list("ABCDEF")
    assert [record["role"] for record in option_records].count("outlier") == 1
    selected = [record for record in option_records if record["option_label"] == out.answer_gt.value][0]
    assert selected["role"] == "outlier"
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value


def test_phylogeny_generation_is_deterministic_for_same_seed() -> None:
    task = create_task(CLADE_COUNT_TASK_ID)
    out_a = task.generate(7105, params={}, max_attempts=200)
    out_b = task.generate(7105, params={}, max_attempts=200)
    assert out_a.answer_gt == out_b.answer_gt
    assert out_a.annotation_gt == out_b.annotation_gt
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert _png_bytes(out_a) == _png_bytes(out_b)


def test_phylogeny_topology_option_signatures_have_one_outlier() -> None:
    dataset = sample_topology_outlier_options(
        8106,
        leaf_count_min=6,
        leaf_count_max=8,
        option_count=6,
        max_attempts=200,
    )
    base_signature = tuple(dataset["base_sample"].canonical_signature)
    outlier_signature = tuple(dataset["outlier_sample"].canonical_signature)
    assert base_signature != outlier_signature
    roles = {str(spec["option_label"]): str(spec["role"]) for spec in dataset["option_specs"]}
    assert set(roles) == set("ABCDEF")
    assert list(roles.values()).count("outlier") == 1
    for spec in dataset["option_specs"]:
        signature = tuple(spec["canonical_signature"])
        if str(spec["role"]) == "outlier":
            assert signature == outlier_signature
        else:
            assert signature == base_signature
