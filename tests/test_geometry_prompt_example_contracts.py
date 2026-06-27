"""Prompt-example regressions for geometry tasks."""

from __future__ import annotations

from typing import Any

import pytest

from trace.core.prompt_annotation_contract_audit import _audit_annotation_prompt
from trace.core.seed import hash64
from trace.core.task_review_sampling import collect_query_id_samples


_AFFECTED_KEYED_POINT_TASKS = (
    "task_geometry__marked_polygon_equation__equal_angle_measure_value",
    "task_geometry__marked_polygon_equation__angle_variable_value",
    "task_geometry__marked_polygon_equation__polygon_angle_sum_angle_value",
    "task_geometry__marked_polygon_equation__polygon_angle_sum_variable_value",
    "task_geometry__marked_polygon_equation__side_length_value",
    "task_geometry__marked_polygon_equation__side_variable_value",
    "task_geometry__regular_polygon_decomposition__central_angle_value",
    "task_geometry__regular_polygon_decomposition__perimeter_value",
    "task_geometry__regular_polygon_decomposition__piece_area_value",
    "task_geometry__regular_polygon_decomposition__side_length_value",
    "task_geometry__right_triangle_altitude_theorem__altitude_to_hypotenuse_value",
    "task_geometry__right_triangle_altitude_theorem__leg_projection_length_value",
    "task_geometry__similar_figure_measure_transfer__area_scale_side_length_value",
    "task_geometry__similar_figure_measure_transfer__corresponding_side_value",
    "task_geometry__similar_figure_measure_transfer__scale_factor_value",
    "task_geometry__similar_figure_measure_transfer__side_length_from_expression_value",
    "task_geometry__similar_figure_measure_transfer__variable_value",
    "task_geometry__special_quadrilateral__algebraic_angle_value",
    "task_geometry__special_quadrilateral__diagonal_angle_value",
    "task_geometry__special_quadrilateral__segment_length_value",
    "task_geometry__triangle_congruence_correspondence__algebraic_side_value",
    "task_geometry__triangle_congruence_correspondence__corresponding_angle_value",
    "task_geometry__triangle_congruence_correspondence__corresponding_side_value",
)

_AFFECTED_SEGMENT_SET_TASKS = (
    "task_geometry__parallel_segment_proportion__segment_length_value",
    "task_geometry__parallel_segment_proportion__variable_value",
)


def _prompt_record(output: Any, _instance_seed: int) -> dict[str, Any]:
    return {
        "annotation_type": str(output.annotation_gt.type),
        "prompt": str(output.prompt_variants["answer_and_annotation"]),
    }


@pytest.mark.parametrize("task_id", _AFFECTED_KEYED_POINT_TASKS)
def test_geometry_keyed_point_prompt_examples_are_not_degenerate(task_id: str) -> None:
    collected = collect_query_id_samples(
        task_id=str(task_id),
        target_count_per_query_id=1,
        seed=int(hash64(20260609, f"geometry.prompt_examples.{task_id}", 0)),
        max_attempts_per_instance=200,
        max_total_samples_per_task=2000,
        workers=1,
        collector=_prompt_record,
    )

    assert collected["incomplete_query_ids"] == []
    offenders: list[str] = []
    for query_id, samples in collected["samples_by_query_id"].items():
        for sample in samples:
            issues = _audit_annotation_prompt(
                str(sample["prompt"]),
                annotation_type=str(sample["annotation_type"]),
                mode="answer_and_annotation",
            )
            if any(issue["code"] == "degenerate_example_points" for issue in issues):
                offenders.append(str(query_id))

    assert not offenders, f"{task_id} has degenerate point examples for query ids: {sorted(offenders)}"


@pytest.mark.parametrize("task_id", _AFFECTED_SEGMENT_SET_TASKS)
def test_geometry_segment_set_prompt_examples_are_valid(task_id: str) -> None:
    collected = collect_query_id_samples(
        task_id=str(task_id),
        target_count_per_query_id=1,
        seed=int(hash64(20260609, f"geometry.prompt_examples.{task_id}", 0)),
        max_attempts_per_instance=200,
        max_total_samples_per_task=2000,
        workers=1,
        collector=_prompt_record,
    )

    assert collected["incomplete_query_ids"] == []
    offenders: list[str] = []
    for query_id, samples in collected["samples_by_query_id"].items():
        for sample in samples:
            issues = _audit_annotation_prompt(
                str(sample["prompt"]),
                annotation_type=str(sample["annotation_type"]),
                mode="answer_and_annotation",
            )
            if issues:
                offenders.extend(f"{query_id}:{issue['code']}" for issue in issues)

    assert not offenders, f"{task_id} has invalid segment-set prompt examples: {sorted(offenders)}"


def test_survey_traverse_bearing_prompt_uses_query_specific_annotation_keys() -> None:
    forward = collect_query_id_samples(
        task_id="task_geometry__survey_traverse__forward_bearing_from_back_bearing_value",
        target_count_per_query_id=1,
        seed=int(hash64(20260609, "geometry.prompt_examples.survey_traverse_forward_bearing", 0)),
        max_attempts_per_instance=200,
        max_total_samples_per_task=800,
        workers=1,
        collector=_prompt_record,
    )
    outgoing = collect_query_id_samples(
        task_id="task_geometry__survey_traverse__outgoing_bearing_from_turn_value",
        target_count_per_query_id=1,
        seed=int(hash64(20260609, "geometry.prompt_examples.survey_traverse_outgoing_bearing", 0)),
        max_attempts_per_instance=200,
        max_total_samples_per_task=800,
        workers=1,
        collector=_prompt_record,
    )

    assert forward["incomplete_query_ids"] == []
    assert outgoing["incomplete_query_ids"] == []
    forward_prompt = str(forward["samples_by_query_id"]["single"][0]["prompt"])
    outgoing_prompt = str(outgoing["samples_by_query_id"]["single"][0]["prompt"])
    assert "turn_vertex" not in forward_prompt
    assert "turn_vertex" in outgoing_prompt


def test_rectangular_solid_open_box_prompt_uses_query_specific_answer_hint() -> None:
    collected = collect_query_id_samples(
        task_id="task_geometry__rectangular_solid__open_box_net_dimension_value",
        target_count_per_query_id=1,
        seed=int(hash64(20260609, "geometry.prompt_examples.rectangular_solid_open_box", 0)),
        max_attempts_per_instance=200,
        max_total_samples_per_task=800,
        workers=1,
        collector=_prompt_record,
    )

    assert collected["incomplete_query_ids"] == []
    prompts = {
        str(query_id): str(samples[0]["prompt"])
        for query_id, samples in collected["samples_by_query_id"].items()
    }
    assert "dimension or volume" not in prompts["open_box_dimension_from_corner_cut"]
    assert "dimension or volume" not in prompts["open_box_volume_from_net"]
    assert "base dimension" in prompts["open_box_dimension_from_corner_cut"]
    assert "volume" in prompts["open_box_volume_from_net"]
