"""MRCA clade-membership count task over phylogeny trees."""

from __future__ import annotations

from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.output_metadata import default_task_versions
from .shared.task_common import (
    MRCA_QUERY_ID,
    PhylogenyMrcaCladeMembershipCountBuilder,
    SCENE_ID,
)


MRCA_TASK_ID = "task_graph__phylogeny_tree__mrca_clade_membership_count"


@register_task
class GraphRelationPhylogenyMrcaCladeMembershipCountTask:
    """Count leaves descending from the MRCA of two queried taxa."""

    task_id = MRCA_TASK_ID
    domain = "graph"
    scene_id = "phylogeny_tree"
    supported_query_ids = (MRCA_QUERY_ID,)

    def generate(self, instance_seed, *, params, max_attempts) -> TaskOutput:
        for selector_key in ("query_id", "query_variant"):
            requested = params.get(selector_key)
            if requested is not None and str(requested) not in {"", "default", MRCA_QUERY_ID}:
                raise ValueError(f"unsupported query_id for {self.task_id}: {requested}")
        bundle = PhylogenyMrcaCladeMembershipCountBuilder().build(
            int(instance_seed),
            task_identifier=self.task_id,
            domain=self.domain,
            params=params,
            max_attempts=int(max_attempts),
        )
        answer_gt = TypedValue(type=str(bundle.answer_type), value=bundle.answer_value)
        annotation_gt = TypedValue(type=str(bundle.annotation_type), value=bundle.annotation_value)
        return TaskOutput(
            prompt=str(bundle.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=bundle.image,
            image_id="img0",
            trace_payload=dict(bundle.trace_payload),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(bundle.query_id),
            prompt_variants=dict(bundle.prompt_variants),
        )


__all__ = ["GraphRelationPhylogenyMrcaCladeMembershipCountTask", "MRCA_TASK_ID"]
