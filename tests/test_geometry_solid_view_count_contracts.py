"""Contract tests for the geometry solid-view counting task."""

from __future__ import annotations

import pytest

from trace.tasks.geometry.shared.solid_scene import CubeStack, projected_view_cells, view_grid_dimensions
from trace.tasks.geometry.solid.view_count import GeometrySolidViewCountTask


@pytest.mark.parametrize(
    ("params", "expected_answer"),
    (
        ({"scene_variant": "cube_stack", "query_variant": "top_view_visible_count", "target_count": 3}, 3),
        ({"scene_variant": "cube_stack", "query_variant": "front_view_visible_count", "target_count": 4}, 4),
        ({"scene_variant": "cube_stack", "task_variant": "right_view_visible_count", "target_count": 5}, 5),
    ),
)
def test_geometry_solid_view_count_emits_expected_contract(
    params: dict[str, int | str],
    expected_answer: int,
) -> None:
    out = GeometrySolidViewCountTask().generate(23301, params=params, max_attempts=60)
    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(expected_answer)
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == int(expected_answer)
    assert out.trace_payload["query_spec"]["params"]["task_variant"] == out.task_variant
    assert out.trace_payload["execution_trace"]["target_count"] == int(expected_answer)
    query_grid_dims = out.trace_payload["projected_evidence"]["query_grid_dimensions"]
    assert int(out.answer_gt.value) < int(query_grid_dims[0]) * int(query_grid_dims[1])

    query_panel_bbox = out.trace_payload["projected_evidence"]["query_panel_bbox"]
    for bbox in out.evidence_gt.value:
        assert len(bbox) == 4
        assert float(bbox[0]) >= float(query_panel_bbox[0])
        assert float(bbox[1]) >= float(query_panel_bbox[1])
        assert float(bbox[2]) <= float(query_panel_bbox[2])
        assert float(bbox[3]) <= float(query_panel_bbox[3])


def test_geometry_solid_view_count_is_deterministic() -> None:
    params = {"scene_variant": "cube_stack", "query_variant": "front_view_visible_count", "target_count": 4}
    task = GeometrySolidViewCountTask()
    out_a = task.generate(23311, params=params, max_attempts=60)
    out_b = task.generate(23311, params=params, max_attempts=60)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_geometry_solid_view_count_rejects_unsupported_scene_variant() -> None:
    with pytest.raises(ValueError):
        GeometrySolidViewCountTask().generate(
            23321,
            params={"scene_variant": "cylinder_stack", "query_variant": "top_view_visible_count"},
            max_attempts=20,
        )


def test_geometry_solid_view_count_rejects_unsupported_query_variant() -> None:
    with pytest.raises(ValueError):
        GeometrySolidViewCountTask().generate(
            23322,
            params={"scene_variant": "cube_stack", "query_variant": "volume"},
            max_attempts=20,
        )


def test_front_view_grid_crops_to_occupied_projection_support() -> None:
    stack = CubeStack(
        width=3,
        depth=4,
        heights={
            (2, 0): 1,
            (2, 1): 2,
            (2, 2): 1,
            (2, 3): 1,
        },
    )

    assert projected_view_cells(stack, query_variant="front_view_visible_count") == ((0, 0), (0, 1))
    assert view_grid_dimensions(stack, query_variant="front_view_visible_count") == (1, 2)


@pytest.mark.parametrize(
    ("query_variant", "expected_snippet"),
    (
        ("front_view_visible_count", "left vertical face"),
        ("right_view_visible_count", "right vertical face"),
    ),
)
def test_solid_view_prompts_clarify_front_and_right_conventions(
    query_variant: str,
    expected_snippet: str,
) -> None:
    out = GeometrySolidViewCountTask().generate(
        23331,
        params={"scene_variant": "cube_stack", "query_variant": query_variant, "target_count": 4},
        max_attempts=60,
    )

    assert expected_snippet in out.prompt
