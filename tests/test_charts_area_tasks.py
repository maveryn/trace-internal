"""Contract smoke tests for area chart panel tasks."""

from __future__ import annotations

from trace.tasks import TASK_REGISTRY


AREA_TASKS = {
    "task_charts__area__interval_area_value": "interval_area_value",
    "task_charts__area__stacked_band_interval_sum_value": "stacked_band_interval_sum_value",
    "task_charts__area__stacked_band_dominance_label": "stacked_dominance_label",
}


def test_area_tasks_registered() -> None:
    assert set(AREA_TASKS).issubset(set(TASK_REGISTRY))


def test_area_tasks_generate_default_query_outputs() -> None:
    for seed_index, (task_id, query_id) in enumerate(sorted(AREA_TASKS.items())):
        task = TASK_REGISTRY[task_id]()
        output = task.generate(
            74_000 + seed_index,
            params={},
            max_attempts=80,
        )
        assert output.scene_id == "area"
        assert output.query_id == query_id
        assert output.trace_payload["query_spec"]["params"]["query_id"] == query_id
        assert output.answer_gt.type in {"integer", "string"}
        assert output.evidence_gt.type == "point_set"
        assert output.evidence_gt.value
        projected = output.trace_payload["projected_evidence"]
        assert projected["type"] == "point_set"
        assert projected["point_set"] == output.evidence_gt.value
        assert projected["pixel_point_set"] == output.evidence_gt.value
        assert "bbox_set" not in projected
        render_spec = output.trace_payload["render_spec"]
        assert render_spec["text_style"]["font_asset_version"]
        assert render_spec["text_style"]["chart_font_family"]
        assert render_spec["information_scene_style"]["kind"] == "information_scene_style"


def test_area_interval_evidence_uses_curve_marker_not_value_label() -> None:
    output = TASK_REGISTRY["task_charts__area__interval_area_value"]().generate(
        74_200,
        params={},
        max_attempts=80,
    )

    point_traces = output.trace_payload["render_map"]["point_traces"]
    queried_traces = [trace for trace in point_traces if bool(trace["queried"])]
    assert output.evidence_gt.value == [trace["mark_center_px"] for trace in queried_traces]
    assert queried_traces
    assert all(trace["mark_center_px"] != trace["value_center_px"] for trace in queried_traces)
