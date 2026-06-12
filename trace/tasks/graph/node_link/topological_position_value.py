"""Find a node position in the unique topological order."""
from __future__ import annotations
from typing import Any, Dict
from ...base import TaskOutput
from ...registry import register_task
from ._lifecycle import NodeLinkAxes, NodeLinkObjectivePlan, run_node_link_plan
from .shared.sampling import sample_topological_position_graph
TASK_ID = 'task_graph__node_link__topological_position_value'
SCENE_ID = 'node_link'
SUPPORTED_QUERY_IDS = ('topological_position',)

def _sample_graph(rng: Any, axes: NodeLinkAxes, attempts: int) -> Any:
    """Sample a graph satisfying this public objective contract."""
    target_position = max(1, min(int(axes.values['target_position']), int(axes.node_count)))
    return sample_topological_position_graph(rng, node_count=int(axes.node_count), target_position=target_position, topology_profile=str(axes.topology_profile), label_variant=str(axes.label_variant))

def _build_objective_plan() -> NodeLinkObjectivePlan:
    """Bind query ids, sampler, answer, and annotation for this objective."""
    return NodeLinkObjectivePlan(public_id=TASK_ID, class_name='GraphOrderTopologicalPositionTask', supported_query_ids=SUPPORTED_QUERY_IDS, sample_graph=_sample_graph, answer_type='integer', answer_field='target_position', annotation_type='point_sequence', annotation_kind='node_point_sequence', annotation_field='target_labels', prompt_query_key='topological_position', graph_directionality='directed', scene_kind='graph_topological_position', question_format='topological_position', value_ranges={'target_position': (1, 6)})

@register_task
class GraphOrderTopologicalPositionTask:
    """Public owner for the node-link topological-position value objective."""
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
__all__ = ['GraphOrderTopologicalPositionTask', 'TASK_ID']
