"""Infer a corresponding side length from congruent triangles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from trace.tasks.registry import register_task

from ._lifecycle import TriangleCongruenceObjectivePlan, run_triangle_congruence_public_entry
from .shared.construction import build_side_case, side_endpoint_labels
from .shared.rendering import render_triangle_congruence_scene
from .shared.sampling import choose_case_by_answer
from .shared.state import DOMAIN, TriangleCongruenceCase, TriangleCongruenceProblem


TASK_ID = "task_geometry__triangle_congruence_correspondence__corresponding_side_value"
TASK_PROMPT_KEY = "corresponding_side_value_query"
ANSWER_HINT_KEY = "answer_hint_integer_length"
SUPPORTED_QUERY_IDS: tuple[str, ...] = (
    "tick_mark_side_transfer",
    "congruence_statement_side_transfer",
    "overlapping_triangle_side_transfer",
)


@dataclass(frozen=True)
class SideTransferSpec:
    """Task-local side transfer branch resolved from the public query."""

    diagram_layout: str
    source_endpoint_indices: tuple[int, int]
    target_endpoint_indices: tuple[int, int]
    statement_visible: bool
    cue_label: str
    length_support: tuple[int, ...]


_SIDE_TRANSFER_BRANCHES: dict[str, SideTransferSpec] = {
    "tick_mark_side_transfer": SideTransferSpec(
        diagram_layout="separated",
        source_endpoint_indices=(0, 1),
        target_endpoint_indices=(0, 1),
        statement_visible=False,
        cue_label="matching_side_tick_marks",
        length_support=tuple(range(7, 38)),
    ),
    "congruence_statement_side_transfer": SideTransferSpec(
        diagram_layout="statement",
        source_endpoint_indices=(1, 2),
        target_endpoint_indices=(1, 2),
        statement_visible=True,
        cue_label="visible_congruence_statement",
        length_support=tuple(range(8, 40)),
    ),
    "overlapping_triangle_side_transfer": SideTransferSpec(
        diagram_layout="overlap",
        source_endpoint_indices=(0, 1),
        target_endpoint_indices=(0, 1),
        statement_visible=True,
        cue_label="overlapping_congruent_triangles",
        length_support=tuple(range(7, 38)),
    ),
}


def _side_transfer_spec(selected_branch: str) -> SideTransferSpec:
    try:
        return _SIDE_TRANSFER_BRANCHES[str(selected_branch)]
    except KeyError as exc:
        raise ValueError(f"unsupported query_id for {TASK_ID}: {selected_branch}") from exc


def _side_cases(selected_branch: str) -> tuple[TriangleCongruenceCase, ...]:
    """Build side-transfer cases for the selected semantic branch."""

    spec = _side_transfer_spec(str(selected_branch))
    return tuple(
        build_side_case(
            layout_kind=spec.diagram_layout,
            value=int(length_value),
            source_side=spec.source_endpoint_indices,
            target_side=spec.target_endpoint_indices,
            show_statement=spec.statement_visible,
        )
        for length_value in spec.length_support
    )


def _prepare_corresponding_side_value(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    selected_branch: str,
    branch_probabilities: Mapping[str, float],
) -> TriangleCongruenceObjectivePlan:
    """Bind a CPCTC side-length transfer from task-owned query semantics."""

    spec = _side_transfer_spec(str(selected_branch))
    case, answer_probabilities = choose_case_by_answer(
        cases=_side_cases(str(selected_branch)),
        answer_fn=lambda item: int(item.answer),
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{selected_branch}",
    )
    annotation_labels = side_endpoint_labels(
        case.layout_kind,
        source_side=case.source_side,
        target_side=case.target_side,
    )
    trace_values = {
        "formula_family": "cpctc_side_equality",
        "formula": "target side length = corresponding source side length",
        "cue_family": spec.cue_label,
        "layout_kind": str(case.layout_kind),
        "target_side_labels": list(annotation_labels[:2]),
        "source_side_labels": list(annotation_labels[2:]),
        "source_target_side_value": int(case.source_target_side_value or 0),
        "target_target_side_value": int(case.target_target_side_value or 0),
        "target_support_probabilities": dict(answer_probabilities),
        "query_id_probabilities": dict(branch_probabilities),
    }
    return TriangleCongruenceObjectivePlan(
        prompt_key=TASK_PROMPT_KEY,
        answer_hint_key=ANSWER_HINT_KEY,
        problem=TriangleCongruenceProblem(
            case=case,
            reasoning_steps=1,
            layout_seed=int(instance_seed),
            answer_support_probabilities=dict(answer_probabilities),
        ),
        render_scene=render_triangle_congruence_scene,
        answer_value=int(case.answer),
        annotation_labels=annotation_labels,
        query_params=trace_values,
        trace_values=trace_values,
    )


@register_task
class GeometryTriangleCongruenceCorrespondenceSideValueTask:
    """Infer a corresponding side length from congruent triangles."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_query_id = SUPPORTED_QUERY_IDS[0]
    prepare_objective = staticmethod(_prepare_corresponding_side_value)

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        return run_triangle_congruence_public_entry(self, int(instance_seed), params=params, max_attempts=int(max_attempts))


__all__ = ["GeometryTriangleCongruenceCorrespondenceSideValueTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
