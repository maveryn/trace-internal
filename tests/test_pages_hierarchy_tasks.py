"""Behavior tests for pages hierarchy tasks."""

from __future__ import annotations

from collections import Counter, defaultdict

from trace.core.seed import hash64
from trace.tasks.pages.hierarchy.tree_count import (
    PagesHierarchyPathLengthCountTask,
    PagesHierarchySubtreeDescendantCountTask,
    PagesHierarchySubtreeLeafCountTask,
)
from tests.helpers import extract_prompt_json_example


def test_pages_hierarchy_tree_count_contract_matches_counted_annotation() -> None:
    task_cases = (
        (PagesHierarchySubtreeDescendantCountTask(), "subtree_descendant_count"),
        (PagesHierarchySubtreeLeafCountTask(), "subtree_leaf_count"),
        (PagesHierarchyPathLengthCountTask(), "path_length_between_two_nodes"),
    )

    for query_id_index, (task, query_id) in enumerate(task_cases):
        out = task.generate(
            61400 + query_id_index,
            params={"query_id": query_id, "scene_variant": "rooted_tree"},
            max_attempts=10,
        )
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]
        render_map = trace["render_map"]
        annotation_bboxes = [[float(value) for value in bbox] for bbox in out.annotation_gt.value]
        annotation_bbox_ids = [str(bbox_id) for bbox_id in execution["annotation_node_bbox_ids"]]

        assert out.answer_gt.type == "integer"
        expected_annotation_type = "bbox_sequence" if str(query_id) == "path_length_between_two_nodes" else "bbox_set"
        assert out.annotation_gt.type == expected_annotation_type
        assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
        assert str(out.query_id) == str(query_id)
        assert str(execution["query_id"]) == str(query_id)
        assert str(execution["source_query_id"]) == str(query_id)
        assert str(execution["scene_variant"]) == "rooted_tree"
        assert str(execution["question_format"]) == "hierarchy_tree_count"
        assert str(execution["view_family"]) == "rooted_tree_diagram"
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        if str(expected_annotation_type) == "bbox_sequence":
            assert trace["projected_annotation"]["type"] == "bbox_sequence"
            assert trace["projected_annotation"]["bbox_sequence"] == annotation_bboxes
        else:
            assert trace["projected_annotation"]["bbox_set"] == annotation_bboxes
        assert int(out.answer_gt.value) == int(execution["answer_count"])
        assert 16 <= int(execution["tree_node_count"]) <= 30
        assert 4 <= int(execution["tree_depth"]) <= 8
        for label in execution["query_node_labels"]:
            assert f'"{label}"' in str(execution["question_text"])

        expected_bboxes = [
            [float(value) for value in render_map["node_bboxes_px"][str(bbox_id)]]
            for bbox_id in annotation_bbox_ids
        ]
        assert annotation_bboxes == expected_bboxes
        assert [str(item) for item in execution["supporting_node_bbox_ids"]] == annotation_bbox_ids
        assert len(execution["node_specs"]) == int(execution["tree_node_count"])
        assert len(render_map["node_bboxes_px"]) == int(execution["tree_node_count"])
        assert len(render_map["edge_bboxes_px"]) == len(execution["edge_specs"])

        if str(query_id) == "subtree_descendant_count":
            assert int(execution["answer_count"]) == int(execution["descendant_count"])
            assert len(execution["annotation_node_ids"]) == int(execution["answer_count"])
            assert str(execution["annotation_semantics"]) == "descendant_nodes_unordered"
        elif str(query_id) == "subtree_leaf_count":
            assert int(execution["answer_count"]) == int(execution["leaf_descendant_count"])
            assert len(execution["annotation_node_ids"]) == int(execution["answer_count"])
            assert str(execution["annotation_semantics"]) == "leaf_descendant_nodes_unordered"
        else:
            assert int(execution["answer_count"]) == int(execution["path_length_between_nodes"])
            assert len(execution["annotation_node_ids"]) == int(execution["answer_count"]) + 1
            assert execution["annotation_node_ids"] == execution["path_node_ids"]
            assert len(execution["query_node_ids"]) == 2
            assert str(execution["annotation_node_ids"][0]) == str(execution["query_node_ids"][0])
            assert str(execution["annotation_node_ids"][-1]) == str(execution["query_node_ids"][1])
            assert str(execution["annotation_semantics"]) == "path_nodes_between_query_nodes_ordered"


def test_pages_hierarchy_tree_count_prompt_examples_match_integer_contract() -> None:
    expected = (
        (PagesHierarchySubtreeDescendantCountTask(), "subtree_descendant_count", 4),
        (PagesHierarchySubtreeLeafCountTask(), "subtree_leaf_count", 3),
        (PagesHierarchyPathLengthCountTask(), "path_length_between_two_nodes", 4),
    )

    for index, (task, query_id, expected_answer) in enumerate(expected, start=61460):
        out = task.generate(index, params={"query_id": query_id, "scene_variant": "rooted_tree"}, max_attempts=10)
        answer_and_annotation = extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert int(answer_and_annotation["answer"]) == int(expected_answer)
        assert int(answer_only["answer"]) == int(expected_answer)
        assert isinstance(answer_and_annotation["annotation"], list)


def test_pages_hierarchy_tree_count_is_deterministic() -> None:
    task = PagesHierarchySubtreeLeafCountTask()
    params = {"query_id": "subtree_leaf_count", "scene_variant": "rooted_tree"}
    out_a = task.generate(61510, params=params, max_attempts=10)
    out_b = task.generate(61510, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_pages_hierarchy_tree_count_balanced_sampling_covers_variants_and_answers() -> None:
    tasks = (
        PagesHierarchySubtreeDescendantCountTask(),
        PagesHierarchySubtreeLeafCountTask(),
        PagesHierarchyPathLengthCountTask(),
    )
    query_ids: Counter[str] = Counter()
    answers_by_variant: dict[str, set[int]] = defaultdict(set)

    for task in tasks:
        for index in range(15):
            out = task.generate(
                hash64(61540, task.task_id, index),
                params={},
                max_attempts=10,
            )
            execution = out.trace_payload["execution_trace"]
            query_id = str(execution["query_id"])
            query_ids[query_id] += 1
            answers_by_variant[query_id].add(int(execution["answer_count"]))

    assert set(query_ids.keys()) == {
        "subtree_descendant_count",
        "subtree_leaf_count",
        "path_length_between_two_nodes",
    }
    assert query_ids["path_length_between_two_nodes"] == 15
    assert query_ids["subtree_descendant_count"] >= 6
    assert query_ids["subtree_leaf_count"] >= 6
    assert all(len(values) >= 3 for values in answers_by_variant.values())


def test_pages_hierarchy_tree_count_layout_keeps_same_depth_nodes_separated() -> None:
    task = PagesHierarchySubtreeDescendantCountTask()

    for index in range(100):
        out = task.generate(
            hash64(61580, "pages_hierarchy_tree_count_layout_v0", index),
            params={},
            max_attempts=10,
        )
        execution = out.trace_payload["execution_trace"]
        node_bboxes = out.trace_payload["render_map"]["node_bboxes_px"]
        nodes_by_depth: dict[int, list[tuple[str, list[float]]]] = defaultdict(list)
        for node_spec in execution["node_specs"]:
            bbox = [float(value) for value in node_bboxes[str(node_spec["node_bbox_id"])]]
            nodes_by_depth[int(node_spec["depth"])].append((str(node_spec["node_id"]), bbox))

        for depth_nodes in nodes_by_depth.values():
            ordered = sorted(depth_nodes, key=lambda item: item[1][0])
            for left, right in zip(ordered, ordered[1:]):
                assert float(right[1][0]) - float(left[1][2]) >= 8.0
