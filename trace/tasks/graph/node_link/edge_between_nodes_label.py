"""Read the visible label on a queried edge."""
from __future__ import annotations
from typing import Any, Dict
from ...base import TaskOutput
from ...registry import register_task
from .shared.lifecycle import NodeLinkAxes, NodeLinkObjectivePlan, run_node_link_plan
from ..shared.graph_sampling import sample_edge_attribute_label_graph
TASK_ID = 'task_graph__node_link__edge_between_nodes_label'
SCENE_ID = 'node_link'
SUPPORTED_QUERY_IDS = ('edge_between_nodes_label', 'directed_edge_between_nodes_label')
EDGE_LABEL_SUPPORT = ('alpha', 'beta', 'gamma', 'delta', 'sigma', 'theta')

def _sample_graph(rng: Any, axes: NodeLinkAxes, attempts: int) -> Any:
    """Sample a graph satisfying this public objective contract."""
    directionality = 'directed' if str(axes.query_id).startswith('directed') else 'undirected'
    target_label = EDGE_LABEL_SUPPORT[int(axes.values['target_edge_label_index']) % len(EDGE_LABEL_SUPPORT)]
    return sample_edge_attribute_label_graph(rng, graph_directionality=directionality, node_count=int(axes.node_count), target_edge_label=str(target_label), edge_label_support=EDGE_LABEL_SUPPORT, topology_profile=str(axes.topology_profile), label_variant=str(axes.label_variant), max_degree=4)

def _build_objective_plan() -> NodeLinkObjectivePlan:
    """Bind query ids, sampler, answer, and annotation for this objective."""
    return NodeLinkObjectivePlan(public_id=TASK_ID, class_name='GraphRelationEdgeBetweenNodesLabelTask', supported_query_ids=SUPPORTED_QUERY_IDS, sample_graph=_sample_graph, answer_type='string', answer_field='target_edge_label', annotation_type='bbox_set', annotation_kind='edge_label_bbox_set', annotation_field='query_edge', prompt_query_key=lambda axes: str(axes.query_id), annotation_hint_key=lambda axes: 'annotation_hint_' + str(axes.query_id), graph_directionality=lambda axes: 'directed' if str(axes.query_id).startswith('directed') else 'undirected', scene_kind='graph_edge_label_lookup', question_format=lambda axes: str(axes.query_id), value_ranges={'target_edge_label_index': (0, len(EDGE_LABEL_SUPPORT) - 1)}, annotation_example=[[180, 220, 230, 245]], answer_example='alpha')

@register_task
class GraphRelationEdgeBetweenNodesLabelTask:
    """Public owner for the node-link edge label lookup objective."""
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
__all__ = ['GraphRelationEdgeBetweenNodesLabelTask', 'TASK_ID']
