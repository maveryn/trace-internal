"""Behavior tests for diagrams hierarchy tasks."""

from __future__ import annotations

from collections import Counter

from trace.core.seed import hash64
from trace.tasks.diagrams.hierarchy.ancestor_label import DiagramsHierarchyAncestorLabelTask
from tests.helpers import extract_prompt_json_example


def test_diagrams_hierarchy_ancestor_label_contract_matches_answer_node_bbox() -> None:
    task = DiagramsHierarchyAncestorLabelTask()
    task_variants = ("parent_of_node", "lowest_common_ancestor_of_two_nodes")

    for variant_index, task_variant in enumerate(task_variants):
        seed = 61100 + variant_index
        out = task.generate(seed, params={"task_variant": task_variant, "scene_variant": "org_chart"}, max_attempts=10)
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]
        render_map = trace["render_map"]
        evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]

        assert out.answer_gt.type == "string"
        assert out.evidence_gt.type == "bbox_set"
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert str(out.task_variant) == str(task_variant)
        assert str(execution["task_variant"]) == str(task_variant)
        assert str(execution["scene_variant"]) == "org_chart"
        assert str(execution["question_format"]) == "hierarchy_ancestor_label"
        assert str(execution["view_family"]) == "org_chart_diagram"
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        assert len(evidence_bboxes) == 1
        assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes
        assert str(out.answer_gt.value) == str(execution["answer_node_label"])

        expected_bbox = [
            float(value)
            for value in render_map["node_bboxes_px"][str(execution["answer_node_bbox_id"])]
        ]
        assert evidence_bboxes == [expected_bbox]
        assert [str(item) for item in execution["supporting_node_bbox_ids"]] == [str(execution["answer_node_bbox_id"])]
        assert len(execution["node_specs"]) == int(execution["tree_node_count"])
        assert len(render_map["node_bboxes_px"]) == int(execution["tree_node_count"])
        assert len(render_map["edge_bboxes_px"]) == len(execution["edge_specs"])

        if str(task_variant) == "parent_of_node":
            assert str(execution["query_relationship"]) == "parent"
            assert len(execution["query_node_ids"]) == 1
            assert str(execution["answer_node_id"]) not in {str(node_id) for node_id in execution["query_node_ids"]}
        else:
            assert str(execution["query_relationship"]) == "lowest_common_ancestor"
            assert len(execution["query_node_ids"]) == 2
            assert int(execution["lca_span"]) >= 2
            assert str(execution["answer_node_id"]) not in {str(node_id) for node_id in execution["query_node_ids"]}


def test_diagrams_hierarchy_prompt_examples_match_variant_contract() -> None:
    task = DiagramsHierarchyAncestorLabelTask()
    expected = {
        "parent_of_node": (
            {"evidence": [[926, 352, 1090, 424]], "answer": "Walt"},
            {"answer": "Walt"},
        ),
        "lowest_common_ancestor_of_two_nodes": (
            {"evidence": [[558, 530, 722, 602]], "answer": "Cott"},
            {"answer": "Cott"},
        ),
    }

    for index, (task_variant, (expected_answer_and_evidence, expected_answer_only)) in enumerate(expected.items(), start=61160):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected_answer_and_evidence
        assert answer_only == expected_answer_only


def test_diagrams_hierarchy_ancestor_label_is_deterministic() -> None:
    task = DiagramsHierarchyAncestorLabelTask()
    params = {"task_variant": "lowest_common_ancestor_of_two_nodes", "scene_variant": "org_chart"}
    out_a = task.generate(61210, params=params, max_attempts=10)
    out_b = task.generate(61210, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_diagrams_hierarchy_balanced_sampling_defaults_cover_variants() -> None:
    task = DiagramsHierarchyAncestorLabelTask()
    task_variants: Counter[str] = Counter()
    scene_variants: Counter[str] = Counter()

    for index in range(12):
        out = task.generate(hash64(61240, "diagrams_hierarchy", index), params={"_sampling_index": index}, max_attempts=10)
        execution = out.trace_payload["execution_trace"]
        task_variants[str(execution["task_variant"])] += 1
        scene_variants[str(execution["scene_variant"])] += 1

    assert set(task_variants.keys()) == {"parent_of_node", "lowest_common_ancestor_of_two_nodes"}
    assert set(scene_variants.keys()) == {"org_chart"}


def test_diagrams_hierarchy_lca_reasoning_load_exceeds_parent_reasoning_load() -> None:
    task = DiagramsHierarchyAncestorLabelTask()
    parent = task.generate(61310, params={"task_variant": "parent_of_node", "scene_variant": "org_chart"}, max_attempts=10)
    lca = task.generate(
        61310,
        params={"task_variant": "lowest_common_ancestor_of_two_nodes", "scene_variant": "org_chart"},
        max_attempts=10,
    )

    assert float(lca.complexity.complexity_components["reasoning_load"]) > float(
        parent.complexity.complexity_components["reasoning_load"]
    )


def test_diagrams_hierarchy_uses_short_name_labels_and_supports_depth_four() -> None:
    task = DiagramsHierarchyAncestorLabelTask()
    out = task.generate(61160, params={"task_variant": "parent_of_node", "scene_variant": "org_chart"}, max_attempts=10)
    execution = out.trace_payload["execution_trace"]

    assert int(execution["tree_depth"]) == 4
    for node_spec in execution["node_specs"]:
        label = str(node_spec["node_label"])
        assert " " not in label
        assert 2 <= len(label) <= 8
