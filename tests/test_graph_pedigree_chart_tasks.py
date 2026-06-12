"""Regression tests for graph-domain pedigree chart tasks."""

from __future__ import annotations

from io import BytesIO

import trace.tasks  # noqa: F401
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks.graph.pedigree_chart.relatedness_coefficient_label import RELATEDNESS_TASK_ID
from trace.tasks.graph.pedigree_chart.relationship_label import RELATIONSHIP_TASK_ID
from trace.tasks.registry import TASK_REGISTRY, create_task


RETIRED_PEDIGREE_TASK_IDS = {
    "task_graph__pedigree_chart__affected_count",
    "task_graph__pedigree_chart__affected_generation_extremum_label",
    "task_graph__pedigree_chart__carrier_candidate_label",
    "task_graph__pedigree_chart__inheritance_pattern_label",
    "task_graph__pedigree_chart__offspring_risk_label",
}


def _png_bytes(output) -> bytes:
    buffer = BytesIO()
    output.image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_pedigree_public_task_set_is_relationship_and_relatedness_only() -> None:
    active = {task_id for task_id in TASK_REGISTRY if "__pedigree_chart__" in str(task_id)}
    assert active == {RELATIONSHIP_TASK_ID, RELATEDNESS_TASK_ID}
    assert not RETIRED_PEDIGREE_TASK_IDS.intersection(TASK_REGISTRY)

    for task_id in active:
        taxonomy = resolve_task_taxonomy(task_id)
        assert taxonomy.domain == "graph"
        assert taxonomy.scene_id == "pedigree_chart"
        assert taxonomy.source_domain == "graph"
        assert taxonomy.source_scene_id == "pedigree_chart"


def test_pedigree_relationship_label_branches() -> None:
    task = create_task(RELATIONSHIP_TASK_ID)
    for index, relationship in enumerate(("parent", "child", "sibling", "partner", "grandparent", "grandchild")):
        out = task.generate(
            1500 + index,
            params={"target_relationship": relationship},
            max_attempts=240,
        )
        execution = out.trace_payload["execution_trace"]
        option_values = execution["option_values_by_label"]
        assert out.answer_gt.type == "option_letter"
        assert out.answer_gt.value in {"A", "B", "C", "D", "E", "F"}
        assert option_values[out.answer_gt.value] == relationship
        assert execution["answer_relationship"] == relationship
        assert len(option_values) == 6
        assert len(set(option_values.values())) == 6
        assert out.annotation_gt.type == "keyed_bbox_map"
        assert {"person_a", "person_b"}.issubset(set(out.annotation_gt.value))
        assert "selected_option" not in out.annotation_gt.value
        assert execution["answer"] == out.answer_gt.value


def test_pedigree_relatedness_coefficient_label_branches() -> None:
    task = create_task(RELATEDNESS_TASK_ID)
    for index, relatedness in enumerate(("0", "1/8", "1/4", "3/8", "1/2")):
        out = task.generate(
            2000 + index,
            params={"target_relatedness_label": relatedness},
            max_attempts=300,
        )
        execution = out.trace_payload["execution_trace"]
        option_values = execution["option_values_by_label"]
        assert out.answer_gt.type == "option_letter"
        assert out.answer_gt.value in {"A", "B", "C", "D", "E", "F"}
        assert execution["answer_fraction"] == relatedness
        assert option_values[out.answer_gt.value] == relatedness
        assert len(option_values) == 6
        assert len(set(option_values.values())) == 6
        assert out.annotation_gt.type == "keyed_bbox_map"
        assert {"person_a", "person_b"}.issubset(set(out.annotation_gt.value))
        assert "selected_option" not in out.annotation_gt.value
        assert out.query_id == "relatedness_coefficient_between_two_people"


def test_pedigree_relatedness_is_deterministic_for_same_seed() -> None:
    task = create_task(RELATEDNESS_TASK_ID)
    params = {"target_relatedness_label": "3/8"}
    out_a = task.generate(2401, params=params, max_attempts=300)
    out_b = task.generate(2401, params=params, max_attempts=300)
    assert out_a.answer_gt == out_b.answer_gt
    assert out_a.annotation_gt == out_b.annotation_gt
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert _png_bytes(out_a) == _png_bytes(out_b)
