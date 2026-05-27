"""Contract tests for named original-attribute paired icon relation."""

from __future__ import annotations

from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks.icons.relation.named_original_attribute_label import (
    QUERY_IDS,
    TASK_ID,
    IconsRelationNamedOriginalAttributeLabelTask,
)


def _matches(record: dict, query_id: str, target: dict) -> bool:
    original = dict(record["original"])
    if str(original["shape_id"]) != str(target["shape_id"]):
        return False
    if query_id == "original_color_shape_label":
        return str(original["color_name"]) == str(target["color_name"])
    if query_id == "original_fill_shape_label":
        return str(original["fill_style"]) == str(target["fill_style"])
    return True


def test_icons_relation_named_original_attribute_contract_all_queries() -> None:
    task = IconsRelationNamedOriginalAttributeLabelTask()
    for index, query_id in enumerate(QUERY_IDS):
        out = task.generate(
            260524300 + int(index),
            params={"query_id": query_id, "answer_label": "C", "distractor_count": 5},
            max_attempts=120,
        )
        trace = out.trace_payload["execution_trace"]
        answer = str(out.answer_gt.value)
        records = list(trace["pair_records"])
        answer_record = next(record for record in records if str(record["label"]) == answer)
        target = dict(answer_record["original"])

        assert out.scene_id == "paired_canvas"
        assert out.query_id == query_id
        assert out.answer_gt.type == "option_letter"
        assert answer == "C"
        assert out.evidence_gt.type == "bbox_set"
        assert len(out.evidence_gt.value) == 2
        assert int(trace["tracked_count"]) == 6
        assert int(trace["distractor_count"]) == 5
        assert sum(1 for record in records if _matches(record, query_id, target)) == 1
        assert bool(answer_record["is_answer"])


def test_icons_relation_named_original_attribute_taxonomy() -> None:
    taxonomy = resolve_task_taxonomy(TASK_ID)
    assert taxonomy.domain == "icons"
    assert taxonomy.scene_id == "paired_canvas"
    assert taxonomy.source_task_group == "relation"
