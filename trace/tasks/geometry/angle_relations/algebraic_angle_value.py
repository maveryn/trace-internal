"""Solve an algebraic angle value in a triangle extension diagram."""
from __future__ import annotations
from typing import Any, Dict, Tuple
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.deterministic_sampling import resolve_selection_index
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from ._lifecycle import build_integer_angle_relation_trace, render_angle_relation_runtime
from .shared.construction import make_algebraic_double_extension_case, make_algebraic_single_extension_case
from .shared.sampling import algebraic_case_parameters_for_answer, select_indexed_case
from .shared.state import DOMAIN, SCENE_ID, AngleRelationCase
TASK_ID = 'task_geometry__angle_relations__algebraic_angle_value'
TRIANGLE_SINGLE_EXTENSION_QUERY_ID = 'triangle_single_extension_expression'
TRIANGLE_DOUBLE_EXTENSION_QUERY_ID = 'triangle_double_extension_expression'
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (TRIANGLE_SINGLE_EXTENSION_QUERY_ID, TRIANGLE_DOUBLE_EXTENSION_QUERY_ID)
ALGEBRAIC_SINGLE_EXTENSION_CASE_SUPPORT: Tuple[Tuple[int, int, int, int, int], ...] = tuple((algebraic_case_parameters_for_answer(answer_value, variant_index=3) for answer_value in range(44, 87)))
ALGEBRAIC_DOUBLE_EXTENSION_CASE_SUPPORT: Tuple[Tuple[int, int, int, int, int], ...] = tuple((algebraic_case_parameters_for_answer(answer_value, variant_index=19) for answer_value in range(45, 88)))
_GEN_DEFAULTS_UNUSED, _RENDER_DEFAULTS, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(DOMAIN, SCENE_ID, task_id=TASK_ID)

def _cases_for_branch(selected_query: str) -> tuple[AngleRelationCase, ...]:
    if str(selected_query) == TRIANGLE_SINGLE_EXTENSION_QUERY_ID:
        return tuple((make_algebraic_single_extension_case(*values) for values in ALGEBRAIC_SINGLE_EXTENSION_CASE_SUPPORT))
    if str(selected_query) == TRIANGLE_DOUBLE_EXTENSION_QUERY_ID:
        return tuple((make_algebraic_double_extension_case(*values) for values in ALGEBRAIC_DOUBLE_EXTENSION_CASE_SUPPORT))
    raise ValueError(f'unsupported query_id for {TASK_ID}: {selected_query}')

@register_task
class GeometryAngleRelationsAlgebraicAngleValueTask:
    """Solve x from angle expressions, then return the target angle measure."""
    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Select an algebraic extension case and bind its solved target angle."""
        selected_query, query_probabilities, task_params = select_task_query_id(instance_seed=int(instance_seed), params=params, supported_query_ids=SUPPORTED_QUERY_IDS, default_query_id=TRIANGLE_SINGLE_EXTENSION_QUERY_ID, task_id=TASK_ID)
        selection_index = resolve_selection_index(params=task_params, instance_seed=int(instance_seed), namespace=f'{TASK_ID}.case.{selected_query}')
        case, case_index = select_indexed_case(cases=_cases_for_branch(str(selected_query)), params=task_params, selection_index=int(selection_index))
        runtime = render_angle_relation_runtime(case=case, case_index=int(case_index), prompt_query_key=str(selected_query), instance_seed=int(instance_seed), params=task_params, render_defaults=_RENDER_DEFAULTS, max_attempts=int(max_attempts))
        answer_gt = TypedValue(type='integer', value=int(runtime.rendered_context.rendered_scene.answer))
        annotation_gt = TypedValue(type=str(runtime.annotation_artifacts.annotation_type), value=runtime.annotation_artifacts.value)
        trace_payload = build_integer_angle_relation_trace(runtime=runtime, branch_name=str(selected_query), branch_probabilities=query_probabilities, answer_value=int(answer_gt.value))
        return TaskOutput(prompt=str(runtime.prompt_artifacts.prompt), answer_gt=answer_gt, annotation_gt=annotation_gt, image=runtime.rendered_context.image, image_id='img0', trace_payload=trace_payload, task_versions=default_task_versions(), scene_id=SCENE_ID, query_id=str(selected_query), prompt_variants=dict(runtime.prompt_artifacts.prompt_variants))
__all__ = ['GeometryAngleRelationsAlgebraicAngleValueTask']
