from ...registry import register_task
from ._lifecycle import NodeLinkObjectivePlan, run_node_link_plan
from .shared.sampling import sample_unique_extreme_degree_graph
TASK_ID = 'task_graph__node_link__degree_extremum_value'
SUPPORTED_QUERY_IDS = ('undirected_max_degree_value', 'undirected_min_degree_value', 'directed_max_in_degree_value', 'directed_max_out_degree_value')

_TARGET_DEGREE_SUPPORT_BY_QUERY = {
    'undirected_max_degree_value': (2, 3, 4, 5),
    'undirected_min_degree_value': (0, 1, 2, 3),
    'directed_max_in_degree_value': (1, 2, 3, 4),
    'directed_max_out_degree_value': (1, 2, 3, 4),
}

def _degree_mode(query_id):
    text = str(query_id)
    if text.startswith('undirected_'):
        return 'degree'
    if '_in_degree_' in text:
        return 'in_degree'
    if '_out_degree_' in text:
        return 'out_degree'
    return 'degree'

def _prompt_query_key(axes):
    return str(axes.query_id).removeprefix('undirected_').replace('directed_', '')

def _object_description_key(axes):
    return 'object_description_directed' if str(axes.query_id).startswith('directed') else 'object_description_undirected'

def _sample_graph(rng, axes, attempts):
    text = str(axes.query_id)
    directed = text.startswith('directed')
    extremum = 'min' if '_min_' in text else 'max'
    degree_mode = _degree_mode(text)
    raw_target = int(axes.values['target_degree'])
    support = _TARGET_DEGREE_SUPPORT_BY_QUERY.get(text)
    if not support:
        raise ValueError(f'unsupported degree-extremum query: {text}')
    target_degree = int(support[int(raw_target) % len(support)])
    directionality = 'directed' if directed else 'undirected'
    degree_cap = 5
    return sample_unique_extreme_degree_graph(rng, graph_directionality=directionality, degree_mode=degree_mode, extremum_mode=extremum, node_count=int(axes.node_count), target_degree=target_degree, max_degree=degree_cap, topology_profile=str(axes.topology_profile), label_variant=str(axes.label_variant), search_attempts=max(512, int(attempts) * 4))

def _build_objective_plan():
    return NodeLinkObjectivePlan(public_id=TASK_ID, class_name='GraphComparisonExtremeDegreeValueTask', supported_query_ids=SUPPORTED_QUERY_IDS, sample_graph=_sample_graph, answer_type='integer', answer_field='target_degree', annotation_type='point', annotation_kind='node_point', annotation_field='target_labels', prompt_query_key=_prompt_query_key, object_description_key=_object_description_key, annotation_hint_key=lambda axes: 'annotation_hint_' + _prompt_query_key(axes), graph_directionality=lambda axes: 'directed' if str(axes.query_id).startswith('directed') else 'undirected', scene_kind='graph_degree_extremum_value', question_format=lambda axes: str(axes.query_id), value_ranges={'target_degree': (0, 3)}, annotation_example=[180, 220], answer_example=3)

@register_task
class GraphComparisonExtremeDegreeValueTask:
    task_id = TASK_ID
    domain = 'graph'
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed, *, params, max_attempts):
        return run_node_link_plan(plan=_build_objective_plan(), instance_seed=int(instance_seed), params=dict(params), max_attempts=int(max_attempts))
__all__ = ['GraphComparisonExtremeDegreeValueTask', 'TASK_ID']
