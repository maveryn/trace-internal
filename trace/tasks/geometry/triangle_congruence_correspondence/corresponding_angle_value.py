"""Infer a corresponding angle measure from congruent triangles."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.registry import register_task

from ._lifecycle import run_triangle_congruence_public_entry
from .shared.construction import angle_witness_labels, build_angle_case
from .shared.rendering import render_triangle_congruence_scene
from .shared.sampling import choose_case_by_answer
from .shared.state import DOMAIN, TriangleCongruenceCase, TriangleCongruenceProblem


TASK_ID = "task_geometry__triangle_congruence_correspondence__corresponding_angle_value"
TASK_PROMPT_KEY = "corresponding_angle_value_query"
ANSWER_HINT_KEY = "answer_hint_integer_angle"
SUPPORTED_QUERY_IDS: tuple[str, ...] = (
    "angle_mark_transfer",
    "congruence_statement_angle_transfer",
    "overlapping_triangle_angle_transfer",
)

_BRANCH_CONFIGS = {
    "angle_mark_transfer": {
        "layout_kind": "separated",
        "source_index": 0,
        "target_index": 0,
        "show_statement": False,
        "cue_family": "matching_angle_marks",
        "values": tuple(range(25, 111, 5)),
    },
    "congruence_statement_angle_transfer": {
        "layout_kind": "statement",
        "source_index": 1,
        "target_index": 1,
        "show_statement": True,
        "cue_family": "visible_congruence_statement",
        "values": tuple(range(30, 116, 5)),
    },
    "overlapping_triangle_angle_transfer": {
        "layout_kind": "overlap",
        "source_index": 0,
        "target_index": 0,
        "show_statement": True,
        "cue_family": "overlapping_congruent_triangles",
        "values": tuple(range(25, 111, 5)),
    },
}


def _angle_cases(selected_branch: str) -> tuple[TriangleCongruenceCase, ...]:
    """Build angle-transfer cases for the selected semantic branch."""

    if str(selected_branch) not in _BRANCH_CONFIGS:
        raise ValueError(f"unsupported query_id for {TASK_ID}: {selected_branch}")
    config = _BRANCH_CONFIGS[str(selected_branch)]
    return tuple(
        build_angle_case(
            layout_kind=str(config["layout_kind"]),
            value=int(value),
            source_index=int(config["source_index"]),
            target_index=int(config["target_index"]),
            show_statement=bool(config["show_statement"]),
        )
        for value in config["values"]  # type: ignore[union-attr]
    )


def _prepare_corresponding_angle_value(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    selected_branch: str,
    branch_probabilities: Mapping[str, float],
) -> tuple[TriangleCongruenceProblem, int, tuple[str, ...], dict[str, Any]]:
    """Bind a CPCTC angle-measure transfer from task-owned query semantics."""

    config = _BRANCH_CONFIGS[str(selected_branch)]
    case, answer_probabilities = choose_case_by_answer(
        cases=_angle_cases(str(selected_branch)),
        answer_fn=lambda item: int(item.answer),
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{selected_branch}",
    )
    annotation_labels = angle_witness_labels(
        case.layout_kind,
        source_angle_index=case.source_angle_index,
        target_angle_index=case.target_angle_index,
    )
    trace_values = {
        "formula_family": "cpctc_angle_equality",
        "formula": "target angle measure = corresponding source angle measure",
        "cue_family": str(config["cue_family"]),
        "layout_kind": str(case.layout_kind),
        "angle_witness_labels": list(annotation_labels),
        "source_angle_value": int(case.source_angle_value or 0),
        "target_angle_value": int(case.target_angle_value or 0),
        "target_support_probabilities": dict(answer_probabilities),
    }
    problem = TriangleCongruenceProblem(
        case=case,
        reasoning_steps=1,
        layout_seed=int(instance_seed),
        answer_support_probabilities=dict(answer_probabilities),
    )
    return problem, int(case.answer), annotation_labels, trace_values


@register_task
class GeometryTriangleCongruenceCorrespondenceAngleValueTask:
    """Infer a corresponding angle measure from congruent triangles."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_query_id = SUPPORTED_QUERY_IDS[0]
    task_prompt_key = TASK_PROMPT_KEY
    answer_hint_key = ANSWER_HINT_KEY
    render_scene = staticmethod(render_triangle_congruence_scene)
    prepare_objective = staticmethod(_prepare_corresponding_angle_value)

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        return run_triangle_congruence_public_entry(self, int(instance_seed), params=params, max_attempts=int(max_attempts))


__all__ = ["GeometryTriangleCongruenceCorrespondenceAngleValueTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
