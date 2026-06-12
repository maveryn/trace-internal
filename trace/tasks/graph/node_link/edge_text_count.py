"""Count visible edge labels with a queried value."""
from __future__ import annotations
from typing import Any, Dict
from ...base import TaskOutput
from ...registry import register_task
from ._lifecycle import NodeLinkAxes, NodeLinkObjectivePlan, run_node_link_plan
from .shared.sampling import sample_edge_text_label_count_graph
TASK_ID = 'task_graph__node_link__edge_text_count'
SCENE_ID = 'node_link'
SUPPORTED_QUERY_IDS = ('edge_text_label_count',)
EDGE_LABEL_SUPPORT = ('alpha', 'beta', 'gamma', 'delta', 'sigma', 'theta')

def _sample_graph(rng: Any, axes: NodeLinkAxes, attempts: int) -> Any:
    """Sample a graph satisfying this public objective contract."""
    target_label = EDGE_LABEL_SUPPORT[int(axes.values['target_edge_label_index']) % len(EDGE_LABEL_SUPPORT)]
    return sample_edge_text_label_count_graph(rng, graph_directionality='undirected', node_count=max(int(axes.node_count), int(axes.values['target_count']) + 3), target_count=int(axes.values['target_count']), target_edge_label=str(target_label), edge_label_support=EDGE_LABEL_SUPPORT, topology_profile=str(axes.topology_profile), label_variant=str(axes.label_variant), max_degree=4)

def _build_objective_plan() -> NodeLinkObjectivePlan:
    """Bind query ids, sampler, answer, and annotation for this objective."""
    return NodeLinkObjectivePlan(public_id=TASK_ID, class_name='GraphCountingEdgeTextLabelCountTask', supported_query_ids=SUPPORTED_QUERY_IDS, sample_graph=_sample_graph, answer_type='integer', answer_field='target_count', annotation_type='bbox_set', annotation_kind='edge_label_bbox_set', annotation_field='target_edges', prompt_query_key='edge_text_label_count', scene_kind='graph_edge_text_counting', question_format='edge_text_label_count', value_ranges={'target_count': (1, 4), 'target_edge_label_index': (0, len(EDGE_LABEL_SUPPORT) - 1)}, annotation_example=[[180, 220, 230, 245]])

@register_task
class GraphCountingEdgeTextLabelCountTask:
    """Public owner for the node-link edge-text count objective."""
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
__all__ = ['GraphCountingEdgeTextLabelCountTask', 'TASK_ID']
