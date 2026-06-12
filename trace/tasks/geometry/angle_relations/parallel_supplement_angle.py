from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from ._lifecycle import build_integer_angle_relation_trace, render_angle_relation_runtime, select_angle_relation_case
from .shared.construction import make_parallel_supplement_case
from .shared.state import DOMAIN, SCENE_ID
TASK_ID = 'task_geometry__angle_relations__parallel_supplement_angle'
PARALLEL_SUPPLEMENT_QUERY_ID = 'parallel_supplement_angle'
SUPPORTED_QUERY_IDS = (PARALLEL_SUPPLEMENT_QUERY_ID,)
PARALLEL_SUPPLEMENT_CASES = tuple((make_parallel_supplement_case(180 - answer_value) for answer_value in range(44, 86)))
_RENDER_DEFAULTS = load_scene_generation_rendering_prompt_defaults(DOMAIN, SCENE_ID, task_id=TASK_ID)[1]

@register_task
class GeometryAngleRelationsParallelSupplementAngleTask:
    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed, *, params, max_attempts) -> TaskOutput:
        selected_query, query_probabilities, task_params = select_task_query_id(instance_seed=int(instance_seed), params=params, supported_query_ids=SUPPORTED_QUERY_IDS, default_query_id=PARALLEL_SUPPLEMENT_QUERY_ID, task_id=TASK_ID)
        branch_name = str(selected_query)
        case, case_index = select_angle_relation_case(cases=PARALLEL_SUPPLEMENT_CASES, params=task_params, instance_seed=int(instance_seed), namespace=f'{TASK_ID}.case')
        runtime = render_angle_relation_runtime(case=case, case_index=int(case_index), prompt_query_key=branch_name, instance_seed=int(instance_seed), params=task_params, render_defaults=_RENDER_DEFAULTS, max_attempts=int(max_attempts))
        answer_gt = TypedValue(type='integer', value=int(runtime.rendered_context.rendered_scene.answer))
        annotation_gt = TypedValue(type=str(runtime.annotation_artifacts.annotation_type), value=runtime.annotation_artifacts.value)
        trace_payload = build_integer_angle_relation_trace(runtime=runtime, branch_name=branch_name, branch_probabilities=query_probabilities, answer_value=int(answer_gt.value))
        return TaskOutput(str(runtime.prompt_artifacts.prompt), answer_gt, annotation_gt, runtime.rendered_context.image, 'img0', trace_payload, default_task_versions(), SCENE_ID, branch_name, dict(runtime.prompt_artifacts.prompt_variants))
__all__ = ['GeometryAngleRelationsParallelSupplementAngleTask']
