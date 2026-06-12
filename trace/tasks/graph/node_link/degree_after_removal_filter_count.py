from __future__ import annotations
from ...registry import register_task
from ._lifecycle import NodeLinkObjectivePlan, run_node_link_plan
from .shared.sampling import sample_degree_count_graph
TASK_ID = 'task_graph__node_link__degree_after_removal_filter_count'
SCENE_ID = 'node_link'
SUPPORTED_QUERY_IDS = ('undirected_degree_one_filter_remaining_count', 'directed_in_degree_one_filter_remaining_count', 'directed_out_degree_one_filter_remaining_count')

def _sample_graph(rng, axes, attempts):
    directed = str(axes.query_id).startswith('directed')
    degree_mode = 'in_degree' if 'in_degree' in str(axes.query_id) else 'out_degree' if 'out_degree' in str(axes.query_id) else None
    return sample_degree_count_graph(rng, query_id='directed_degree_count' if directed else 'degree_count', degree_mode=degree_mode, node_count=int(axes.node_count), query_degree=1, target_count=int(axes.values['target_count']), max_degree=4, topology_profile=str(axes.topology_profile), label_variant=str(axes.label_variant), search_attempts=int(attempts))

def _build_objective_plan():
    return NodeLinkObjectivePlan(public_id=TASK_ID, class_name='GraphCountingDegreeAfterRemovalFilterCountTask', supported_query_ids=SUPPORTED_QUERY_IDS, sample_graph=_sample_graph, answer_type='integer', answer_field='target_count', annotation_type='point_set', annotation_kind='node_point_set', annotation_field='target_labels', prompt_query_key=lambda axes: str(axes.query_id), annotation_hint_key=lambda axes: 'annotation_hint_' + str(axes.query_id), graph_directionality=lambda axes: 'directed' if str(axes.query_id).startswith('directed') else 'undirected', scene_kind='graph_degree_after_removal_filter_counting', question_format=lambda axes: str(axes.query_id), fixed_values={'query_degree': 1}, value_ranges={'target_count': (1, 5)}, prompt_bundle_id='graph_counting_v0', prompt_scene_key='single_graph_counting', prompt_task_key='node_count_after_degree_filter_query')

@register_task
class GraphCountingDegreeAfterRemovalFilterCountTask:
    task_id = TASK_ID
    domain = 'graph'
    supported_query_ids = SUPPORTED_QUERY_IDS

    def _build_objective_plan(self):
        return _build_objective_plan()

    def generate(self, instance_seed, *, params, max_attempts):
        return run_node_link_plan(plan=self._build_objective_plan(), instance_seed=int(instance_seed), params=dict(params), max_attempts=int(max_attempts))
__all__ = ['GraphCountingDegreeAfterRemovalFilterCountTask', 'TASK_ID']
