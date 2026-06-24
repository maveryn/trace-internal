"""Select the category with the extremal total size-encoded value."""

from __future__ import annotations

from trace.tasks.charts.size_encoding._lifecycle import package_size_encoding_plan as P, run_size_encoding_lifecycle as R
from trace.tasks.charts.size_encoding.shared.annotations import item_bbox_set as BSET
from trace.tasks.charts.size_encoding.shared.defaults import resolve_scene_variant as V
from trace.tasks.charts.size_encoding.shared.sampling import build_size_encoding_dataset as DSET, select_extreme_category_total as SEL
from trace.tasks.charts.size_encoding.shared.state import DOMAIN
from trace.tasks.registry import register_task

T = "task_charts__size_encoding__category_total_extremum_label"
Q = {"largest_category_total_label": "largest", "smallest_category_total_label": "smallest"}
PGM = "select_label(arg_extreme(categories, sum(encoded_value(items_in_category)), direction)); output=string_label; annotation=bbox_set(answer_category_items); scene=size_encoding; scope=category_total_extremum_label"


def _build_plan(params, seed, query_id, _probs):
    direction = Q[str(query_id)]
    variant, variant_probs = V(params, instance_seed=seed)
    dataset = DSET(scene_variant=variant, params=params, instance_seed=seed, attempt_index=int(params.get("_attempt_index", 0)))
    selection = SEL(dataset, direction=direction, params=params)
    return P(dataset=dataset, selection=selection, params=params, scene_variant=variant, scene_variant_probabilities=variant_probs, prompt_key=query_id, annotation_kind="answer_category_bbox_set", question_format="size_encoded_label_comparison", program_code=PGM, reasoning_load=0.86)


def _bind_annotation(plan, rendered):
    boxes = BSET(rendered, tuple(plan.selection.annotation_item_ids))
    return "bbox_set", boxes, {"type": "bbox_set", "bbox_set": boxes}


@register_task
class ChartsSizeEncodingCategoryTotalExtremumLabelTask:
    task_id = T
    domain = DOMAIN
    objective_contract = "category_total_extremum_label"
    supported_query_ids = tuple(Q)
    default_query_id = "largest_category_total_label"
    default_dataset_enabled = True

    def generate(self, instance_seed, *, params, max_attempts):
        return R(task=self, instance_seed=instance_seed, params=dict(params), max_attempts=max_attempts, default_query_id=self.default_query_id, build_plan=_build_plan, bind_annotation=_bind_annotation)


__all__ = ["ChartsSizeEncodingCategoryTotalExtremumLabelTask"]
