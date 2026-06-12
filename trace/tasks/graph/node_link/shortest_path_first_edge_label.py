"""Read the visible label on the first edge of a shortest path."""
from __future__ import annotations
from typing import Any, Dict
from ...base import TaskOutput
from ...registry import register_task
from .shared.lifecycle import NodeLinkAxes, NodeLinkObjectivePlan, run_node_link_plan
from ..shared.graph_sampling import sample_edge_attribute_path_label_graph
TASK_ID = 'task_graph__node_link__shortest_path_first_edge_label'
SCENE_ID = 'node_link'
SUPPORTED_QUERY_IDS = ('shortest_path_first_edge_label',)
EDGE_LABEL_SUPPORT = ('alpha', 'beta', 'gamma', 'delta', 'sigma', 'theta')

def _sample_graph(rng: Any, axes: NodeLinkAxes, attempts: int) -> Any:
    """Sample a graph satisfying this public objective contract."""
    target_label = EDGE_LABEL_SUPPORT[int(axes.values['target_edge_label_index']) % len(EDGE_LABEL_SUPPORT)]
    return sample_edge_attribute_path_label_graph(rng, graph_directionality='undirected', node_count=int(axes.node_count), target_shortest_path_length=int(axes.values['target_shortest_path_length']), target_edge_label=str(target_label), edge_label_support=EDGE_LABEL_SUPPORT, topology_profile=str(axes.topology_profile), label_variant=str(axes.label_variant))

def _build_objective_plan() -> NodeLinkObjectivePlan:
    """Bind query ids, sampler, answer, and annotation for this objective."""
    return NodeLinkObjectivePlan(public_id=TASK_ID, class_name='GraphRelationShortestPathFirstEdgeLabelTask', supported_query_ids=SUPPORTED_QUERY_IDS, sample_graph=_sample_graph, answer_type='string', answer_field='target_edge_label', annotation_type='bbox_set', annotation_kind='edge_label_bbox_set', annotation_field='query_edge', prompt_query_key='shortest_path_first_edge_label', annotation_hint_key='annotation_hint_shortest_path_first_edge_label', scene_kind='graph_shortest_path_edge_label_lookup', question_format='shortest_path_first_edge_label', value_ranges={'target_shortest_path_length': (2, 4), 'target_edge_label_index': (0, len(EDGE_LABEL_SUPPORT) - 1)}, annotation_example=[[180, 220, 230, 245]], answer_example='alpha')

@register_task
class GraphRelationShortestPathFirstEdgeLabelTask:
    """Public owner for the node-link shortest-path first-edge label objective."""
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
__all__ = ['GraphRelationShortestPathFirstEdgeLabelTask', 'TASK_ID']
