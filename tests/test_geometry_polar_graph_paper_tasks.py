from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from trace.tasks.geometry.polar_graph_paper.readout_value import (
    QUERY_IDS,
    TASK_ID,
    PolarGraphPaperReadoutValueTask,
)


def _task() -> PolarGraphPaperReadoutValueTask:
    return PolarGraphPaperReadoutValueTask()


@pytest.mark.parametrize("query_id", QUERY_IDS)
def test_polar_graph_paper_readout_generates_each_query(query_id: str) -> None:
    output = _task().generate(
        17,
        params={"query_id": query_id, "radius": 5, "theta_degrees": 120},
        max_attempts=1,
    )

    assert output.trace_payload["scene_ir"]["task_id"] == TASK_ID
    assert output.answer_gt.type == "integer"
    expected = 5 if query_id == "radius_readout_value" else 120
    assert output.answer_gt.value == expected
    assert output.annotation_gt.type == "point"
    assert len(output.annotation_gt.value) == 2
    assert output.query_id == query_id
    assert output.scene_id == "polar_graph_paper"

    render_map = output.trace_payload["render_map"]
    assert "option_values_by_label" not in render_map
    assert output.trace_payload["execution_trace"]["correct_value"] == output.answer_gt.value


def test_polar_graph_paper_generation_is_deterministic() -> None:
    first = _task().generate(23, params={"query_id": "angle_readout_value"}, max_attempts=1)
    second = _task().generate(23, params={"query_id": "angle_readout_value"}, max_attempts=1)

    assert first.answer_gt == second.answer_gt
    assert first.annotation_gt == second.annotation_gt
    assert first.trace_payload["execution_trace"] == second.trace_payload["execution_trace"]


def test_polar_graph_paper_invalid_query_id_raises() -> None:
    with pytest.raises(ValueError):
        _task().generate(1, params={"query_id": "x_component"}, max_attempts=1)


def test_polar_graph_paper_config_has_no_query_routing() -> None:
    config = yaml.safe_load(Path("configs/domains/geometry/polar_graph_paper.yaml").read_text())
    assert "query_weights" not in str(config)
    assert "queries" not in config.get("prompt", {}).get("shared", {})
