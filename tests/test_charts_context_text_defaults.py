"""Chart-domain context-text wrapper tests."""

from __future__ import annotations

from trace.tasks import TASK_REGISTRY


def _output(task_id: str, *, seed: int, params: dict):
    output = TASK_REGISTRY[task_id]().generate(
        int(seed),
        params=dict(params),
        max_attempts=120,
    )
    return output


def _context_layer(task_id: str, *, seed: int, params: dict) -> dict:
    output = _output(task_id, seed=seed, params=params)
    return output.trace_payload["render_spec"]["context_text_layer"]


def _overlap(left: list[float], right: list[float]) -> bool:
    return not (
        float(left[2]) <= float(right[0])
        or float(left[0]) >= float(right[2])
        or float(left[3]) <= float(right[1])
        or float(left[1]) >= float(right[3])
    )


def test_chart_context_clean_mode_records_empty_layer() -> None:
    layer = _context_layer(
        "task_charts__histogram__interval_mass",
        seed=12345,
        params={"chart_context_mode": "clean"},
    )

    assert layer["enabled"] is True
    assert layer["layout_mode"] == "chart_context:clean"
    assert layer["element_count"] == 0
    assert layer["elements"] == []


def test_chart_context_minimal_and_paragraph_modes_draw_context() -> None:
    minimal = _context_layer(
        "task_charts__histogram__interval_mass",
        seed=12345,
        params={"chart_context_mode": "minimal"},
    )
    paragraph = _context_layer(
        "task_charts__area__interval_area_value",
        seed=12001,
        params={"chart_context_mode": "paragraph_box"},
    )

    assert minimal["layout_mode"] == "chart_context:minimal"
    assert minimal["element_count"] >= 1
    assert paragraph["layout_mode"] == "chart_context:paragraph_box"
    assert any(str(element["role"]).startswith("paragraph_box_") for element in paragraph["elements"])


def test_chart_context_wrapper_preserves_scene_specific_context_layer() -> None:
    output = TASK_REGISTRY["task_charts__dashboard__dual_condition_count"]().generate(
        12345,
        params={},
        max_attempts=120,
    )
    render_spec = output.trace_payload["render_spec"]

    assert render_spec["context_text_layer"]["layout_mode"].startswith("reserved_context:")
    assert render_spec["context_text_layer"]["element_count"] >= 1
    assert render_spec["chart_context_text_policy"]["domain_wrapper"] == "skipped_existing_context_text_layer"


def test_chart_context_records_and_avoids_protected_bboxes() -> None:
    output = _output(
        "task_charts__combo_mark__cross_mark_difference_value",
        seed=153456684567519,
        params={"query_id": "line_minus_primary_at_label", "chart_context_mode": "paragraph_box"},
    )
    render_map = output.trace_payload["render_map"]
    context_boxes = list(render_map["context_text_bboxes_px"].values())
    protected_boxes = list(render_map["context_protected_bboxes_px"].values())

    assert render_map["legend_bbox_px"] == render_map["context_protected_bboxes_px"]["legend"]
    assert context_boxes
    assert protected_boxes
    assert not any(_overlap(context_box, protected_box) for context_box in context_boxes for protected_box in protected_boxes)
