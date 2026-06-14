"""Count nodes reachable from one directed start node."""
from __future__ import annotations
from dataclasses import replace
from typing import Any, Dict
from ...base import TaskOutput
from ...registry import register_task
from ._lifecycle import NodeLinkAxes, NodeLinkObjectivePlan, run_node_link_plan
from .shared.sampling import sample_reachable_count_graph
TASK_ID = 'task_graph__node_link__reachable_count'
SCENE_ID = 'node_link'
SUPPORTED_QUERY_IDS = ('single',)

def _sample_graph(rng: Any, axes: NodeLinkAxes, attempts: int) -> Any:
    """Sample a graph satisfying this public objective contract."""
    requested_non_start_count = int(axes.values['target_count'])
    sample = sample_reachable_count_graph(
        rng,
        node_count=int(axes.node_count),
        target_reachable_count=int(requested_non_start_count) + 1,
        topology_profile=str(axes.topology_profile),
        label_variant=str(axes.label_variant),
    )
    non_start_labels = tuple(
        str(label)
        for label in sample.target_labels
        if str(label) != str(sample.query_label)
    )
    if len(non_start_labels) != int(requested_non_start_count):
        raise ValueError("reachable-count sampler produced an unexpected non-start reachable count")
    return replace(
        sample,
        target_labels=non_start_labels,
        annotation_labels=non_start_labels,
        target_reachable_count=int(requested_non_start_count),
    )

def _build_objective_plan() -> NodeLinkObjectivePlan:
    """Bind query ids, sampler, answer, and annotation for this objective."""
    return NodeLinkObjectivePlan(public_id=TASK_ID, class_name='GraphRelationReachableCountTask', supported_query_ids=SUPPORTED_QUERY_IDS, sample_graph=_sample_graph, answer_type='integer', answer_field='target_reachable_count', annotation_type='point_set', annotation_kind='node_point_set', annotation_field='annotation_labels', prompt_query_key='reachable_count', annotation_hint_key='annotation_hint_reachable_count', graph_directionality='directed', scene_kind='graph_reachable_count', question_format='reachable_count', value_ranges={'target_count': (1, 6)})

@register_task
class GraphRelationReachableCountTask:
    """Public owner for the node-link reachable-node count objective."""
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
__all__ = ['GraphRelationReachableCountTask', 'TASK_ID']
