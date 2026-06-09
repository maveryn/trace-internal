"""Regression tests for pages calendar event-grid tasks."""

from __future__ import annotations

from typing import Mapping

from trace.tasks import create_task


DATE_SLOT_TASK_ID = "task_pages__calendar_event_grid__date_slot_category_label"
CATEGORY_COUNT_TASK_ID = "task_pages__calendar_event_grid__category_slot_day_count"
DATE_FOR_CATEGORY_SLOT_TASK_ID = "task_pages__calendar_event_grid__date_for_category_slot_label"


def _event_records(output) -> list[Mapping[str, object]]:
    execution = output.trace_payload["execution_trace"]
    return [dict(record) for record in execution["event_chip_records"]]


def test_calendar_event_grid_date_slot_lookup_contract() -> None:
    output = create_task(DATE_SLOT_TASK_ID).generate(51001, params={}, max_attempts=1)

    assert output.scene_id == "calendar_event_grid"
    assert output.query_id == "date_slot_category_label"
    assert output.answer_gt.type == "string"
    assert output.annotation_gt.type == "keyed_bbox_map"
    assert sorted(output.annotation_gt.value.keys()) == ["date_cell", "event_chip"]

    trace = output.trace_payload["execution_trace"]
    target_key = f"date_{int(trace['target_date'])}__slot_{trace['slot_id']}"
    matching_records = [record for record in _event_records(output) if record["chip_key"] == target_key]
    assert len(matching_records) == 1
    assert output.answer_gt.value == matching_records[0]["category_label"]
    assert output.annotation_gt.value["event_chip"] == matching_records[0]["bbox_px"]
    assert output.trace_payload["render_map"]["calendar_panel_bbox_px"]
    assert output.trace_payload["render_spec"]["calendar_event_grid_style"]["panel_layout"]["layout_placement"]["mode"] == "fractional_free_area"


def test_calendar_event_grid_category_slot_count_matches_rendered_chips() -> None:
    output = create_task(CATEGORY_COUNT_TASK_ID).generate(51002, params={}, max_attempts=1)

    assert output.scene_id == "calendar_event_grid"
    assert output.query_id == "category_slot_day_count"
    assert output.answer_gt.type == "integer"
    assert output.annotation_gt.type == "bbox_set"

    trace = output.trace_payload["execution_trace"]
    category_label = str(trace["category_label"])
    slot_id = str(trace["slot_id"])
    rendered_matches = [
        record
        for record in _event_records(output)
        if str(record["category_label"]) == category_label and str(record["slot_id"]) == slot_id
    ]
    assert output.answer_gt.value == len(rendered_matches)
    assert len(output.annotation_gt.value) == len(rendered_matches)
    assert output.annotation_gt.value == [record["bbox_px"] for record in rendered_matches]


def test_calendar_event_grid_date_for_category_slot_contract() -> None:
    output = create_task(DATE_FOR_CATEGORY_SLOT_TASK_ID).generate(51004, params={}, max_attempts=1)

    assert output.scene_id == "calendar_event_grid"
    assert output.query_id == "date_for_category_slot_label"
    assert output.answer_gt.type == "integer"
    assert output.annotation_gt.type == "keyed_bbox_map"
    assert sorted(output.annotation_gt.value.keys()) == ["date_cell", "event_chip"]

    trace = output.trace_payload["execution_trace"]
    category_label = str(trace["category_label"])
    slot_id = str(trace["slot_id"])
    rendered_matches = [
        record
        for record in _event_records(output)
        if str(record["category_label"]) == category_label and str(record["slot_id"]) == slot_id
    ]
    assert len(rendered_matches) == 1
    matching_record = rendered_matches[0]
    assert output.answer_gt.value == int(matching_record["date_number"])
    assert output.answer_gt.value == int(trace["target_date"])
    assert output.annotation_gt.value["event_chip"] == matching_record["bbox_px"]
    assert output.annotation_gt.value["date_cell"] == output.trace_payload["render_map"]["date_cells_by_day"][
        str(output.answer_gt.value)
    ]


def test_calendar_event_grid_generation_is_deterministic() -> None:
    task = create_task(DATE_FOR_CATEGORY_SLOT_TASK_ID)
    first = task.generate(51003, params={}, max_attempts=1)
    second = task.generate(51003, params={}, max_attempts=1)

    assert first.prompt == second.prompt
    assert first.answer_gt == second.answer_gt
    assert first.annotation_gt == second.annotation_gt
    assert first.trace_payload["execution_trace"] == second.trace_payload["execution_trace"]
