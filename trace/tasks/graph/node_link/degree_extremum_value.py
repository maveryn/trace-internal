from ...registry import register_task
from ._lifecycle import NodeLinkObjectivePlan, run_node_link_plan
from .shared.sampling import feasible_node_counts_for_extreme_degree_value, sample_extreme_degree_graph
TASK_ID = 'task_graph__node_link__degree_extremum_value'
SUPPORTED_QUERY_IDS = ('undirected_max_degree_value', 'undirected_min_degree_value', 'directed_max_in_degree_value', 'directed_min_in_degree_value', 'directed_max_out_degree_value', 'directed_min_out_degree_value', 'directed_max_total_degree_value', 'directed_min_total_degree_value')

def _degree_mode(query_id):
    text = str(query_id)
    if text.startswith('undirected_'):
        return 'degree'
    if '_in_degree_' in text:
        return 'in_degree'
    if '_out_degree_' in text:
        return 'out_degree'
    if '_total_degree_' in text:
        return 'total_degree'
    return 'degree'

def _sample_graph(rng, axes, attempts):
    text = str(axes.query_id)
    directed = text.startswith('directed')
    extremum = 'min' if '_min_' in text else 'max'
    degree_mode = _degree_mode(text)
    raw_target = int(axes.values['target_degree'])
    target_degree = int(raw_target if extremum == 'min' else raw_target + 1)
    directionality = 'directed' if directed else 'undirected'
    degree_cap = 5
    feasible_nodes = feasible_node_counts_for_extreme_degree_value(graph_directionality=directionality, degree_mode=degree_mode, extremum_mode=extremum, target_degree=target_degree, node_count_min=5, node_count_max=max(8, int(axes.node_count)), max_degree=degree_cap)
    if not feasible_nodes:
        raise ValueError('no feasible node count for degree-extremum query')
    node_count = int(axes.node_count) if int(axes.node_count) in feasible_nodes and target_degree < 4 else int(feasible_nodes[-1])
    return sample_extreme_degree_graph(rng, graph_directionality=directionality, degree_mode=degree_mode, extremum_mode=extremum, node_count=node_count, target_degree=target_degree, max_degree=degree_cap, topology_profile=str(axes.topology_profile), label_variant=str(axes.label_variant))

def _build_objective_plan():
    return NodeLinkObjectivePlan(public_id=TASK_ID, class_name='GraphComparisonExtremeDegreeValueTask', supported_query_ids=SUPPORTED_QUERY_IDS, sample_graph=_sample_graph, answer_type='integer', answer_field='target_degree', annotation_type='point_set', annotation_kind='node_point_set', annotation_field='target_labels', prompt_query_key=lambda axes: str(axes.query_id).removeprefix('undirected_').replace('directed_', ''), graph_directionality=lambda axes: 'directed' if str(axes.query_id).startswith('directed') else 'undirected', scene_kind='graph_degree_extremum_value', question_format=lambda axes: str(axes.query_id), value_ranges={'target_degree': (0, 3)})

@register_task
class GraphComparisonExtremeDegreeValueTask:
    task_id = TASK_ID
    domain = 'graph'
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed, *, params, max_attempts):
        return run_node_link_plan(plan=_build_objective_plan(), instance_seed=int(instance_seed), params=dict(params), max_attempts=int(max_attempts))
__all__ = ['GraphComparisonExtremeDegreeValueTask', 'TASK_ID']
