"""Solve algebraic angle relations on parallel-line transversal diagrams."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions

from ._lifecycle import build_integer_angle_relation_trace, render_angle_relation_runtime, select_angle_relation_case
from .shared.construction import make_parallel_algebraic_case
from .shared.state import DOMAIN, SCENE_ID, AngleRelationCase


TASK_ID = "task_geometry__angle_relations__parallel_algebraic_angle_value"
TARGET_ANGLE_VALUE_QUERY_ID = "target_angle_value"
VARIABLE_X_VALUE_QUERY_ID = "variable_x_value"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (TARGET_ANGLE_VALUE_QUERY_ID, VARIABLE_X_VALUE_QUERY_ID)
TASK_PROMPT_KEY = "parallel_algebraic_angle_value"
PROMPT_QUERY_KEYS = {
    TARGET_ANGLE_VALUE_QUERY_ID: "parallel_target_angle_value",
    VARIABLE_X_VALUE_QUERY_ID: "parallel_variable_x_value",
}

_GEN_DEFAULTS_UNUSED, _RENDER_DEFAULTS, _PROMPT_DEFAULTS_UNUSED = (
    load_scene_generation_rendering_prompt_defaults(DOMAIN, SCENE_ID, task_id=TASK_ID)
)


def _parallel_algebraic_case_support() -> tuple[AngleRelationCase, ...]:
    """Build deterministic support cases for parallel-line algebra."""

    cases: list[AngleRelationCase] = []
    seen: set[tuple[str, int, int, int, int]] = set()
    for relation_id in ("corresponding_equal", "same_side_supplementary"):
        for x_value in range(6, 29):
            for target_coeff in (2, 3, 4, 5):
                for target_const in range(-18, 25):
                    target_angle = (int(target_coeff) * int(x_value)) + int(target_const)
                    if not 35 <= target_angle <= 135:
                        continue
                    support_angle = target_angle if relation_id == "corresponding_equal" else 180 - target_angle
                    if not 35 <= support_angle <= 135:
                        continue
                    key = (relation_id, int(support_angle), int(x_value), int(target_coeff), int(target_const))
                    if key in seen:
                        continue
                    seen.add(key)
                    cases.append(
                        make_parallel_algebraic_case(
                            relation_id=relation_id,
                            support_angle=int(support_angle),
                            x_value=int(x_value),
                            target_coeff=int(target_coeff),
                            target_const=int(target_const),
                        )
                    )
    return tuple(cases)


PARALLEL_ALGEBRAIC_CASES = _parallel_algebraic_case_support()


def _answer_probability_map(values: tuple[int, ...]) -> dict[str, float]:
    """Return a compact uniform probability map for trace metadata."""

    support = tuple(sorted(set(int(value) for value in values)))
    if not support:
        return {}
    weight = 1.0 / float(len(support))
    return {str(value): weight for value in support}


def _answer_for_query(*, selected_query: str, witness: Mapping[str, Any]) -> tuple[int, str, dict[str, float]]:
    """Bind the requested output from the rendered parallel algebra trace."""

    if str(selected_query) == TARGET_ANGLE_VALUE_QUERY_ID:
        values = tuple(int(case.answer) for case in PARALLEL_ALGEBRAIC_CASES)
        return int(witness["target_angle_measure"]), "target_angle_value", _answer_probability_map(values)
    if str(selected_query) == VARIABLE_X_VALUE_QUERY_ID:
        x_support = tuple(range(6, 29))
        return int(witness["x"]), "variable_x_value", _answer_probability_map(x_support)
    raise ValueError(f"unsupported query_id for {TASK_ID}: {selected_query}")


@register_task
class GeometryAngleRelationsParallelAlgebraicAngleValueTask:
    """Solve a parallel-line algebra relation and return the requested integer."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Select a semantic output query, sample a case, and bind answer plus annotation."""

        selected_query, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=TARGET_ANGLE_VALUE_QUERY_ID,
            task_id=TASK_ID,
        )
        case, case_index = select_angle_relation_case(
            cases=PARALLEL_ALGEBRAIC_CASES,
            params=task_params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.case",
        )
        runtime = render_angle_relation_runtime(
            case=case,
            case_index=int(case_index),
            prompt_query_key=str(PROMPT_QUERY_KEYS[str(selected_query)]),
            prompt_task_key=TASK_PROMPT_KEY,
            instance_seed=int(instance_seed),
            params=task_params,
            render_defaults=_RENDER_DEFAULTS,
            max_attempts=int(max_attempts),
        )
        witness = runtime.rendered_context.rendered_scene.witness
        answer_value, answer_role, answer_probabilities = _answer_for_query(
            selected_query=str(selected_query),
            witness=witness,
        )
        trace_payload = build_integer_angle_relation_trace(
            runtime=runtime,
            branch_name=str(selected_query),
            branch_probabilities=query_probabilities,
            answer_value=int(answer_value),
            query_params={
                "answer_support_probabilities": dict(answer_probabilities),
                "target_angle_value": int(witness["target_angle_measure"]),
                "variable_x_value": int(witness["x"]),
                "answer_role": str(answer_role),
            },
            scene_relation_fields={
                "answer_role": str(answer_role),
                "relation_id": str(witness["relation_id"]),
            },
            execution_fields_extra={
                "answer_role": str(answer_role),
                "target_angle_value": int(witness["target_angle_measure"]),
                "variable_x_value": int(witness["x"]),
            },
            witness_fields_extra={
                "answer_role": str(answer_role),
                "target_angle_value": int(witness["target_angle_measure"]),
                "variable_x_value": int(witness["x"]),
            },
        )
        return TaskOutput(
            prompt=str(runtime.prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(answer_value)),
            annotation_gt=TypedValue(
                type=str(runtime.annotation_artifacts.annotation_type),
                value=runtime.annotation_artifacts.value,
            ),
            image=runtime.rendered_context.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(selected_query),
            prompt_variants=dict(runtime.prompt_artifacts.prompt_variants),
        )


__all__ = [
    "GeometryAngleRelationsParallelAlgebraicAngleValueTask",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
]
