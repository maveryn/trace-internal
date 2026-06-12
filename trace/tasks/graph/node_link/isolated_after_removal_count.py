"""Count nodes isolated after removing one node."""
from __future__ import annotations
from typing import Any, Dict
from ...base import TaskOutput
from ...registry import register_task
from .shared.lifecycle import NodeLinkAxes, NodeLinkObjectivePlan, run_node_link_plan
from ..shared.graph_sampling import feasible_node_counts_for_isolated_node_count_after_node_removal, sample_isolated_node_count_after_node_removal_graph
TASK_ID = 'task_graph__node_link__isolated_after_removal_count'
SCENE_ID = 'node_link'
SUPPORTED_QUERY_IDS = ('isolated_node_count_after_node_removal',)

def _sample_graph(rng: Any, axes: NodeLinkAxes, attempts: int) -> Any:
    """Sample a graph satisfying this public objective contract."""
    target_count = max(1, min(4, int(axes.values['target_count'])))
    feasible_nodes = feasible_node_counts_for_isolated_node_count_after_node_removal(graph_directionality='undirected', target_count=target_count, node_count_min=5, node_count_max=max(5, int(axes.node_count)))
    node_count = int(axes.node_count) if int(axes.node_count) in feasible_nodes else int(feasible_nodes[-1])
    return sample_isolated_node_count_after_node_removal_graph(rng, graph_directionality='undirected', node_count=node_count, target_count=target_count, topology_profile=str(axes.topology_profile), label_variant=str(axes.label_variant))

def _build_objective_plan() -> NodeLinkObjectivePlan:
    """Bind query ids, sampler, answer, and annotation for this objective."""
    return NodeLinkObjectivePlan(public_id=TASK_ID, class_name='GraphCountingIsolatedNodeCountAfterNodeRemovalTask', supported_query_ids=SUPPORTED_QUERY_IDS, sample_graph=_sample_graph, answer_type='integer', answer_field='target_count', annotation_type='point_set', annotation_kind='node_point_set', annotation_field='target_labels', prompt_query_key='isolated_node_count_after_node_removal', scene_kind='graph_isolated_after_removal_counting', question_format='isolated_node_count_after_node_removal', value_ranges={'target_count': (1, 4)})

@register_task
class GraphCountingIsolatedNodeCountAfterNodeRemovalTask:
    """Public owner for the node-link isolated-after-removal count objective."""
    task_id = TASK_ID
    domain = 'graph'
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def _build_objective_plan(self) -> NodeLinkObjectivePlan:
        """Return this task's local objective plan."""
        return _build_objective_plan()

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one task instance through neutral scene lifecycle plumbing."""
        return run_node_link_plan(plan=self._build_objective_plan(), instance_seed=int(instance_seed), params=dict(params), max_attempts=int(max_attempts))
__all__ = ['GraphCountingIsolatedNodeCountAfterNodeRemovalTask', 'TASK_ID']
