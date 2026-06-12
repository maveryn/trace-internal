from __future__ import annotations
from ...registry import register_task
from .shared.lifecycle import NodeLinkObjectivePlan, run_node_link_plan
from ..shared.graph_sampling import feasible_node_counts_for_named_node_degree_value, sample_named_node_degree_graph
TASK_ID = 'task_graph__node_link__named_node_degree_value'
SCENE_ID = 'node_link'
SUPPORTED_QUERY_IDS = ('undirected_named_node_degree_value', 'directed_named_node_in_degree_value', 'directed_named_node_out_degree_value', 'directed_named_node_total_degree_value')

def _sample_graph(rng, axes, attempts):
    text = str(axes.query_id)
    directionality = 'directed' if text.startswith('directed') else 'undirected'
    degree_mode = 'in_degree' if 'in_degree' in text else 'out_degree' if 'out_degree' in text else 'total_degree' if 'total_degree' in text else 'degree'
    target_degree = int(axes.values['target_degree'])
    feasible_nodes = feasible_node_counts_for_named_node_degree_value(graph_directionality=directionality, degree_mode=degree_mode, target_degree=target_degree, node_count_min=5, node_count_max=max(5, int(axes.node_count)), max_degree=4)
    if not feasible_nodes:
        raise ValueError('no feasible node count for named-node degree query')
    node_count = int(axes.node_count) if int(axes.node_count) in feasible_nodes else int(feasible_nodes[-1])
    return sample_named_node_degree_graph(rng, graph_directionality=directionality, degree_mode=degree_mode, node_count=node_count, target_degree=target_degree, max_degree=4, topology_profile=str(axes.topology_profile), label_variant=str(axes.label_variant))

def _build_objective_plan():
    return NodeLinkObjectivePlan(public_id=TASK_ID, class_name='GraphCountingNamedNodeDegreeValueTask', supported_query_ids=SUPPORTED_QUERY_IDS, sample_graph=_sample_graph, answer_type='integer', answer_field='target_degree', annotation_type='point_pair_set', annotation_kind='edge_point_pair_set', annotation_field='target_edges', annotation_hint_key='annotation_hint_degree_count', prompt_query_key=lambda axes: 'named_node_in_degree_value' if 'in_degree' in str(axes.query_id) else 'named_node_out_degree_value' if 'out_degree' in str(axes.query_id) else 'named_node_total_degree_value' if 'total_degree' in str(axes.query_id) else 'named_node_degree_value', graph_directionality=lambda axes: 'directed' if str(axes.query_id).startswith('directed') else 'undirected', scene_kind='graph_named_node_degree_value', question_format=lambda axes: str(axes.query_id), value_ranges={'target_degree': (0, 3)}, annotation_example=[[[180, 220], [310, 180]]])

@register_task
class GraphCountingNamedNodeDegreeValueTask:
    task_id = TASK_ID
    domain = 'graph'
    supported_query_ids = SUPPORTED_QUERY_IDS

    def _build_objective_plan(self):
        return _build_objective_plan()

    def generate(self, instance_seed, *, params, max_attempts):
        return run_node_link_plan(plan=self._build_objective_plan(), instance_seed=int(instance_seed), params=dict(params), max_attempts=int(max_attempts))
__all__ = ['GraphCountingNamedNodeDegreeValueTask', 'TASK_ID']
