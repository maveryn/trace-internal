"""Scene-package-v2 contracts for geometry angle-relations tasks."""

from __future__ import annotations

from pathlib import Path

import pytest

from trace.tasks import TASK_REGISTRY, create_task


ACTIVE_TASK_IDS = {
    "task_geometry__angle_relations__algebraic_angle_value",
    "task_geometry__angle_relations__parallel_supplement_angle",
    "task_geometry__angle_relations__triangle_exterior_angle",
}
RETIRED_TASK_IDS = {
    "task_geometry__angle_relations__algebraic_angle_value_triangle_double_extension_expression",
    "task_geometry__angle_relations__algebraic_angle_value_triangle_single_extension_expression",
}


def test_angle_relations_registry_surface_is_merged() -> None:
    """The algebraic single/double extension branches are query ids, not tasks."""

    assert ACTIVE_TASK_IDS <= set(TASK_REGISTRY)
    assert RETIRED_TASK_IDS.isdisjoint(TASK_REGISTRY)


def test_angle_relations_scene_has_no_wrapper_only_modules() -> None:
    """The first geometry v2 scene should not keep legacy wrapper/base files."""

    scene_dir = Path("trace/tasks/geometry/angle_relations")
    public_files = {
        path.name
        for path in scene_dir.glob("*.py")
        if path.name not in {"__init__.py", "_lifecycle.py"}
    }
    assert public_files == {
        "algebraic_angle_value.py",
        "parallel_supplement_angle.py",
        "triangle_exterior_angle.py",
    }
    assert not (scene_dir / "shared" / "task_base.py").exists()
    assert not (scene_dir / "shared" / "cases.py").exists()


@pytest.mark.parametrize(
    ("task_id", "query_ids"),
    (
        ("task_geometry__angle_relations__algebraic_angle_value", ("triangle_single_extension_expression", "triangle_double_extension_expression")),
        ("task_geometry__angle_relations__parallel_supplement_angle", ("parallel_supplement_angle",)),
        ("task_geometry__angle_relations__triangle_exterior_angle", ("triangle_exterior_angle",)),
    ),
)
def test_angle_relations_tasks_generate_keyed_angle_points(task_id: str, query_ids: tuple[str, ...]) -> None:
    task = create_task(task_id)
    assert tuple(task.supported_query_ids) == query_ids
    for query_id in query_ids:
        output = task.generate(20260610, params={"query_id": query_id, "case_index": 0}, max_attempts=20)
        assert output.scene_id == "angle_relations"
        assert output.query_id == query_id
        assert output.answer_gt.type == "integer"
        assert output.annotation_gt.type == "keyed_point_map"
        assert output.trace_payload["projected_annotation"]["type"] == "keyed_point_map"
        assert set(output.annotation_gt.value) == set(output.trace_payload["execution_trace"]["annotation_roles"])
        width, height = output.image.size
        for point in output.annotation_gt.value.values():
            assert len(point) == 2
            assert 0.0 <= float(point[0]) <= float(width)
            assert 0.0 <= float(point[1]) <= float(height)


def test_parallel_supplement_uses_aef_given_angle_and_cfe_target() -> None:
    task = create_task("task_geometry__angle_relations__parallel_supplement_angle")
    output = task.generate(
        20260612,
        params={"query_id": "parallel_supplement_angle", "case_index": 0},
        max_attempts=20,
    )

    assert set(output.annotation_gt.value) == {"AEF", "CFE"}
    assert "given_angle_AEF" in output.trace_payload["execution_trace"]
    assert "given_angle_BEF" not in output.trace_payload["execution_trace"]
    assert "What is the measure of angle \"CFE\"?" in output.prompt
    assert "Lines \"AB\" and \"CD\" are parallel" not in output.prompt
