"""Select the option graph with the same structure as the reference graph."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.fixed_query import force_query_id_params, select_task_query_id
from ...shared.output_metadata import default_task_versions
from .shared.structure_match import SCENE_ID, build_structure_match_instance


TASK_ID = "task_graph__graph_options__same_structure_label"
QUERY_ID = "same_structure_label"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (QUERY_ID,)


def _with_public_task_id(trace_payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(trace_payload)
    for section in ("scene_ir", "query_spec", "execution_trace"):
        if isinstance(payload.get(section), dict):
            payload[section] = {**payload[section], "task_id": TASK_ID}
    return payload


@register_task
class GraphRelationGraphOptionsSameStructureLabelTask:
    """Select the option graph with the same structure as the reference graph."""

    task_id = TASK_ID
    domain = "graph"
    scene_id = SCENE_ID
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_ID,
            task_id=TASK_ID,
            namespace=f"{TASK_ID}.query",
        )
        bundle = build_structure_match_instance(
            domain=self.domain,
            query_id=str(query_id),
            query_id_probabilities=dict(query_probabilities),
            params=force_query_id_params(task_params, query_id=str(query_id)),
            instance_seed=int(instance_seed),
            max_attempts=int(max_attempts),
        )
        answer_gt = TypedValue(type="option_letter", value=str(bundle.answer_value))
        annotation_gt = TypedValue(type="bbox_set", value=list(bundle.annotation_bboxes))
        trace_payload = _with_public_task_id(dict(bundle.trace_payload))
        prompt_variants = dict(bundle.prompt_variants)
        return TaskOutput(
            prompt=str(bundle.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=bundle.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(bundle.query_id),
            prompt_variants=prompt_variants,
        )


__all__ = ["GraphRelationGraphOptionsSameStructureLabelTask", "TASK_ID"]
