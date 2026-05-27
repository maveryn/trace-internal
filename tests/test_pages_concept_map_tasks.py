"""Behavior tests for pages concept-map diagram tasks."""

from __future__ import annotations

from collections import Counter

from trace.core.seed import hash64
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks.pages.concept_map.diagram_tasks import (
    BRANCH_ITEM_COUNT_TASK_ID,
    FILTERED_NODE_COUNT_TASK_ID,
    ORDERED_CHILD_LABEL_TASK_ID,
    PagesConceptMapBranchItemCountTask,
    PagesConceptMapFilteredNodeCountTask,
    PagesConceptMapOrderedChildLabelTask,
)


def _assert_bboxes_inside_image(out) -> None:
    width, height = out.image.size
    for bbox in out.evidence_gt.value:
        x0, y0, x1, y1 = [float(value) for value in bbox]
        assert 0.0 <= x0 <= x1 <= float(width)
        assert 0.0 <= y0 <= y1 <= float(height)


def test_pages_concept_map_tasks_are_registered_in_public_taxonomy() -> None:
    for task_id in [BRANCH_ITEM_COUNT_TASK_ID, ORDERED_CHILD_LABEL_TASK_ID, FILTERED_NODE_COUNT_TASK_ID]:
        taxonomy = resolve_task_taxonomy(task_id)
        assert taxonomy.domain == "pages"
        assert taxonomy.scene_id == "concept_map"
        assert taxonomy.source_task_group == "concept_map"


def test_pages_concept_map_branch_item_count_contract() -> None:
    task = PagesConceptMapBranchItemCountTask()
    out = task.generate(95100, params={"query_id": "branch_child_count", "layout_variant": "radial_mind_map"}, max_attempts=10)
    trace = out.trace_payload
    query = trace["execution_trace"]["query"]
    expected = [
        trace["render_map"]["node_bboxes_px"][str(node_id)]
        for node_id in query["evidence_node_ids"]
    ]

    assert out.scene_id == "concept_map"
    assert out.query_id == "default"
    assert out.query_id == "branch_child_count"
    assert trace["execution_trace"]["node_shape_profile"] in {"mixed_hub_circle", "oval_branch_mix", "mixed_cards_ovals"}
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "bbox_set"
    assert int(out.answer_gt.value) == int(query["answer"])
    assert len(out.evidence_gt.value) == int(out.answer_gt.value)
    assert out.evidence_gt.value == expected
    assert sorted(out.prompt_variants) == ["answer_and_evidence", "answer_only"]
    _assert_bboxes_inside_image(out)


def test_pages_concept_map_ordered_child_label_contract() -> None:
    task = PagesConceptMapOrderedChildLabelTask()
    out = task.generate(95140, params={"query_id": "nth_child_label", "layout_variant": "left_right_map"}, max_attempts=10)
    trace = out.trace_payload
    query = trace["execution_trace"]["query"]
    expected = [
        trace["render_map"]["node_bboxes_px"][str(node_id)]
        for node_id in query["evidence_node_ids"]
    ]

    assert out.scene_id == "concept_map"
    assert out.query_id == "default"
    assert out.query_id == "nth_child_label"
    assert out.answer_gt.type == "string"
    assert 2 <= int(query["rank"]) <= 5
    assert str(query["rank_ordinal"]) in out.prompt
    assert str(out.answer_gt.value) == str(query["answer"])
    assert out.evidence_gt.value == expected
    _assert_bboxes_inside_image(out)


def test_pages_concept_map_filtered_node_count_contract() -> None:
    task = PagesConceptMapFilteredNodeCountTask()
    out = task.generate(95180, params={"query_id": "marked_child_count", "layout_variant": "clustered_map"}, max_attempts=10)
    trace = out.trace_payload
    query = trace["execution_trace"]["query"]
    expected = [
        trace["render_map"]["node_bboxes_px"][str(node_id)]
        for node_id in query["evidence_node_ids"]
    ]

    assert out.scene_id == "concept_map"
    assert out.query_id == "default"
    assert out.query_id == "marked_child_count"
    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(query["answer"])
    assert len(out.evidence_gt.value) == int(out.answer_gt.value)
    assert out.evidence_gt.value == expected
    assert str(query["marker_label"]) in out.prompt
    _assert_bboxes_inside_image(out)


def test_pages_concept_map_generation_is_deterministic() -> None:
    task = PagesConceptMapFilteredNodeCountTask()
    params = {"query_id": "marked_child_count", "layout_variant": "radial_mind_map", "style_variant": "bright_notes"}
    out_a = task.generate(95220, params=params, max_attempts=10)
    out_b = task.generate(95220, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_pages_concept_map_sampling_covers_visual_and_text_axes() -> None:
    task = PagesConceptMapOrderedChildLabelTask()
    layouts: Counter[str] = Counter()
    styles: Counter[str] = Counter()
    shape_profiles: Counter[str] = Counter()
    node_shapes: Counter[str] = Counter()
    contexts: Counter[str] = Counter()
    queries: Counter[str] = Counter()

    for index in range(24):
        out = task.generate(hash64(95260, "concept_map_axes", index), params={}, max_attempts=10)
        execution = out.trace_payload["execution_trace"]
        layouts[str(execution["layout_variant"])] += 1
        styles[str(execution["style_variant"])] += 1
        shape_profiles[str(execution["node_shape_profile"])] += 1
        contexts[str(execution["context_id"])] += 1
        queries[str(execution["query_id"])] += 1
        for branch in execution["branches"]:
            node_shapes[str(branch["shape"])] += 1
            node_shapes.update(str(shape) for shape in branch["child_node_shapes"].values())

    assert set(layouts) == {"radial_mind_map", "left_right_map", "clustered_map"}
    assert set(styles) == {"bright_notes", "ink_outline", "soft_cards", "technical_pastel"}
    assert set(shape_profiles) == {"mixed_hub_circle", "oval_branch_mix", "mixed_cards_ovals"}
    assert {"rounded_rect", "ellipse", "pill"}.issubset(set(node_shapes))
    assert "circle" in set(node_shapes)
    assert len(contexts) >= 5
    assert set(queries) == {"nth_child_label"}
