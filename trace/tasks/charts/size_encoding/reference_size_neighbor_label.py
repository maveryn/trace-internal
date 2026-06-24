"""Select the nearest size-encoded neighbor of a reference item."""

from __future__ import annotations

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks.charts.size_encoding._lifecycle import package_size_encoding_plan as P, run_size_encoding_lifecycle as R
from trace.tasks.charts.size_encoding.shared.annotations import reference_answer_bbox_map as MAP
from trace.tasks.charts.size_encoding.shared.defaults import resolve_scene_variant as V
from trace.tasks.charts.size_encoding.shared.sampling import build_size_encoding_dataset as DSET, select_nearest_size_neighbor as SEL
from trace.tasks.charts.size_encoding.shared.state import DOMAIN
from trace.tasks.registry import register_task

T = "task_charts__size_encoding__reference_size_neighbor_label"
PGM = "select_label(argmin(filter(items, category=target_category and item != reference_item), abs(encoded_value(item) - encoded_value(reference_item)))); output=string_label; annotation=bbox_map(reference_item,answer_item); scene=size_encoding; scope=reference_size_neighbor_label"


def _build_plan(params, seed, _query_id, _probs):
    variant, variant_probs = V(params, instance_seed=seed)
    dataset = DSET(scene_variant=variant, params=params, instance_seed=seed, attempt_index=int(params.get("_attempt_index", 0)))
    selection = SEL(dataset, params=params, instance_seed=seed)
    return P(dataset=dataset, selection=selection, params=params, scene_variant=variant, scene_variant_probabilities=variant_probs, prompt_key="reference_size_neighbor_label", annotation_kind="reference_answer_bbox_map", question_format="size_encoded_label_comparison", program_code=PGM, reasoning_load=0.72)


def _bind_annotation(plan, rendered):
    reference_id, answer_id = tuple(plan.selection.annotation_item_ids)
    boxes = MAP(rendered, reference_item_id=reference_id, answer_item_id=answer_id)
    return "bbox_map", boxes, {"type": "bbox_map", "bbox_map": boxes, "pixel_bbox_map": boxes, "bbox_set": list(boxes.values())}


@register_task
class ChartsSizeEncodingReferenceSizeNeighborLabelTask:
    task_id = T
    domain = DOMAIN
    objective_contract = "reference_size_neighbor_label"
    supported_query_ids = (SINGLE_QUERY_ID,)
    default_query_id = SINGLE_QUERY_ID
    default_dataset_enabled = True

    def generate(self, instance_seed, *, params, max_attempts):
        return R(task=self, instance_seed=instance_seed, params=dict(params), max_attempts=max_attempts, default_query_id=self.default_query_id, build_plan=_build_plan, bind_annotation=_bind_annotation)


__all__ = ["ChartsSizeEncodingReferenceSizeNeighborLabelTask"]
