from __future__ import annotations
from ...registry import register_task
from ._lifecycle import NodeLinkObjectivePlan, run_node_link_plan
from .shared.sampling import sample_cross_color_edge_count_graph
TASK_ID = 'task_graph__node_link__cross_color_edge_count'
SUPPORTED_QUERY_IDS = ('cross_color_edge_count', 'directed_cross_color_edge_count')

def _sample_graph(rng, axes, attempts):
    directionality = 'directed' if str(axes.query_id).startswith('directed') else 'undirected'
    return sample_cross_color_edge_count_graph(rng, graph_directionality=directionality, node_count=max(int(axes.node_count), int(axes.values['target_count']) + 4), target_count=int(axes.values['target_count']), source_color_name='red', target_color_name='blue', color_support=('red', 'blue', 'green', 'yellow', 'orange', 'purple'), topology_profile=str(axes.topology_profile), label_variant=str(axes.label_variant), max_degree=4)

def _build_objective_plan():
    return NodeLinkObjectivePlan(public_id=TASK_ID, class_name='GraphCountingCrossColorEdgeCountTask', supported_query_ids=SUPPORTED_QUERY_IDS, sample_graph=_sample_graph, answer_type='integer', answer_field='target_count', annotation_type='point_pair_set', annotation_kind='edge_point_pair_set', annotation_field='target_edges', prompt_query_key=lambda axes: str(axes.query_id), graph_directionality=lambda axes: 'directed' if str(axes.query_id).startswith('directed') else 'undirected', scene_kind='graph_cross_color_edge_counting', question_format=lambda axes: str(axes.query_id), value_ranges={'target_count': (1, 4)}, annotation_example=[[[180, 220], [310, 180]]])

@register_task
class GraphCountingCrossColorEdgeCountTask:
    task_id = TASK_ID
    domain = 'graph'
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed, *, params, max_attempts):
        return run_node_link_plan(plan=_build_objective_plan(), instance_seed=int(instance_seed), params=dict(params), max_attempts=int(max_attempts))
__all__ = ['GraphCountingCrossColorEdgeCountTask', 'TASK_ID']
