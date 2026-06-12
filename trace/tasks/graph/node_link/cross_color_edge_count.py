"""Count edges connecting two semantic node colors."""
from __future__ import annotations
from typing import Any, Dict
from ...base import TaskOutput
from ...registry import register_task
from .shared.lifecycle import NodeLinkAxes, NodeLinkObjectivePlan, run_node_link_plan
from ..shared.graph_sampling import sample_cross_color_edge_count_graph
TASK_ID = 'task_graph__node_link__cross_color_edge_count'
SCENE_ID = 'node_link'
SUPPORTED_QUERY_IDS = ('cross_color_edge_count', 'directed_cross_color_edge_count')

def _sample_graph(rng: Any, axes: NodeLinkAxes, attempts: int) -> Any:
    """Sample a graph satisfying this public objective contract."""
    directionality = 'directed' if str(axes.query_id).startswith('directed') else 'undirected'
    return sample_cross_color_edge_count_graph(rng, graph_directionality=directionality, node_count=max(int(axes.node_count), int(axes.values['target_count']) + 4), target_count=int(axes.values['target_count']), source_color_name='red', target_color_name='blue', color_support=('red', 'blue', 'green', 'yellow', 'orange', 'purple'), topology_profile=str(axes.topology_profile), label_variant=str(axes.label_variant), max_degree=4)

def _build_objective_plan() -> NodeLinkObjectivePlan:
    """Bind query ids, sampler, answer, and annotation for this objective."""
    return NodeLinkObjectivePlan(public_id=TASK_ID, class_name='GraphCountingCrossColorEdgeCountTask', supported_query_ids=SUPPORTED_QUERY_IDS, sample_graph=_sample_graph, answer_type='integer', answer_field='target_count', annotation_type='point_pair_set', annotation_kind='edge_point_pair_set', annotation_field='target_edges', prompt_query_key=lambda axes: str(axes.query_id), graph_directionality=lambda axes: 'directed' if str(axes.query_id).startswith('directed') else 'undirected', scene_kind='graph_cross_color_edge_counting', question_format=lambda axes: str(axes.query_id), value_ranges={'target_count': (1, 4)}, annotation_example=[[[180, 220], [310, 180]]])

@register_task
class GraphCountingCrossColorEdgeCountTask:
    """Public owner for the node-link cross-color edge count objective."""
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
__all__ = ['GraphCountingCrossColorEdgeCountTask', 'TASK_ID']
