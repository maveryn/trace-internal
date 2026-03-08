"""Shared contract tests for single-object geometry measurement tasks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Type

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.geometry.measurement.angle import GeometryAngleMeasure2DTask
from trace.tasks.geometry.measurement.area import GeometryAreaMeasure2DTask
from trace.tasks.geometry.measurement.length import GeometryLengthMeasure2DTask
from trace.tasks.geometry.measurement.perimeter import GeometryPerimeterMeasure2DTask
from tests.helpers import read_jsonl


_TASK_CASES: list[tuple[str, Type[Any], Dict[str, Any], int]] = [
    (
        "task_geometry_measurement_angle",
        GeometryAngleMeasure2DTask,
        {"query_type": "measure"},
        180,
    ),
    (
        "task_geometry_measurement_area",
        GeometryAreaMeasure2DTask,
        {"query_type": "measure"},
        180,
    ),
    (
        "task_geometry_measurement_perimeter",
        GeometryPerimeterMeasure2DTask,
        {"query_type": "measure"},
        180,
    ),
    (
        "task_geometry_measurement_length",
        GeometryLengthMeasure2DTask,
        {"query_type": "measure"},
        180,
    ),
]


def test_geometry_measurement_task_contract_deterministic() -> None:
    group_cfg = get_task_group_defaults("geometry", "measurement")
    render_shared = (
        group_cfg.get("rendering", {}).get("shared", {})
        if isinstance(group_cfg, dict)
        else {}
    )
    canvas_min = int(render_shared.get("canvas_size_min", 1))
    canvas_max = int(render_shared.get("canvas_size_max", max(1, canvas_min)))
    graph_cells_min = int(render_shared.get("graph_cells_min", 1))
    graph_cells_max = int(render_shared.get("graph_cells_max", max(1, graph_cells_min)))

    for task_id, task_cls, params, max_attempts in _TASK_CASES:
        task = task_cls()
        assert task.supported_query_types({}) == ["measure"]

        out_a = task.generate(53123, params=dict(params), max_attempts=int(max_attempts))
        out_b = task.generate(53123, params=dict(params), max_attempts=int(max_attempts))

        assert out_a.query_type == "measure"
        if str(task_id) == "task_geometry_measurement_angle":
            assert out_a.answer_gt.type == "option_letter"
            assert str(out_a.answer_gt.value) in {"A", "B", "C", "D", "E"}
        else:
            assert out_a.answer_gt.type in {"integer", "pi_expression"}
            if out_a.answer_gt.type == "integer":
                assert isinstance(out_a.answer_gt.value, int)
            else:
                assert isinstance(out_a.answer_gt.value, str)
                assert str(out_a.answer_gt.value).endswith("π")
        assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
        assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
        assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
        assert out_a.image.tobytes() == out_b.image.tobytes()

        assert sorted(out_a.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert out_a.prompt == out_a.prompt_variants["answer_and_evidence"]
        prompt_variants_meta = out_a.trace_payload["query_spec"]["prompt_variants"]
        assert sorted(prompt_variants_meta.keys()) == ["answer_and_evidence", "answer_only"]
        assert out_a.trace_payload["query_spec"]["prompt_variant_active_key"] == "answer_and_evidence"

        background_meta = out_a.trace_payload["render_spec"]["background_style"]
        assert background_meta["selected_style"] == "graph_paper"
        style_spec = background_meta["style_spec"]
        spacing = int(style_spec["spacing"])
        assert spacing >= 4
        canvas_size = int(out_a.trace_payload["render_spec"]["canvas_size"])
        assert canvas_min <= canvas_size <= canvas_max

        graph_frame = out_a.trace_payload["render_spec"]["graph_coordinate_frame"]
        assert graph_frame["coord_space"] == "graph_unit"
        assert int(graph_frame["target_cells_x"]) == int(graph_frame["target_cells_y"])
        assert graph_cells_min <= int(graph_frame["target_cells_x"]) <= graph_cells_max
        origin_x, origin_y = (int(graph_frame["origin_pixel"][0]), int(graph_frame["origin_pixel"][1]))
        inset = int(style_spec.get("outer_margin_px", 0))
        left = max(0, int(inset))
        top = max(0, int(inset))
        right = max(int(left), int(canvas_size) - 1 - int(inset))
        bottom = max(int(top), int(canvas_size) - 1 - int(inset))
        assert left <= int(origin_x) <= right
        assert top <= int(origin_y) <= bottom
        expected_center_x = (float(left) + float(right)) / 2.0
        expected_center_y = (float(top) + float(bottom)) / 2.0
        assert abs(float(origin_x) - float(expected_center_x)) <= 0.5 + 1e-9
        assert abs(float(origin_y) - float(expected_center_y)) <= 0.5 + 1e-9


def test_geometry_measurement_task_build_smoke(tmp_path: Path) -> None:
    for task_id, _task_cls, params, max_attempts in _TASK_CASES:
        output_root = tmp_path / task_id
        config = BuildConfig(
            output_root=str(output_root),
            dataset_name=f"build_smoke_{task_id}",
            instance_version="v1",
            image_format="png",
            tasks=[
                BuildTaskConfig(
                    task_id=str(task_id),
                    count=4,
                    params=dict(params),
                )
            ],
            strict_repro=False,
            max_attempts_per_instance=int(max_attempts),
            sampling_seed=17,
        )

        final_path = build_dataset(config, code_hash=f"{task_id}-smoke")
        assert final_path.exists()

        train_records = read_jsonl(final_path / "train_instances.jsonl")
        assert len(train_records) == 4
        assert all(record["task_group"] == "measurement" for record in train_records)

        build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
        query_counts = build_report["query_type_accepted_counts_by_task"][str(task_id)]
        assert sum(int(value) for value in query_counts.values()) == 4
        assert set(query_counts.keys()) == {"measure"}

        validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
        assert validation["total_errors"] == 0
