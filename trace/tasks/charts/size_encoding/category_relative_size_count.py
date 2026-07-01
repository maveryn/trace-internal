"""Count same-category items larger or smaller than a reference item."""

from __future__ import annotations

from ._lifecycle import package_size_encoding_plan as P, run_size_encoding_lifecycle as R
from .shared.annotations import item_bbox_set_map as ANN
from .shared.defaults import resolve_scene_variant as V
from .shared.sampling import (
    build_size_encoding_dataset as DSET,
    enforce_relative_size_reference_gap as GAP,
    select_category_relative_size_count as SEL,
)
from .shared.state import DOMAIN, SINGLE_PANEL_SCENE_VARIANTS
from trace.tasks.registry import register_task

T = "task_charts__size_encoding__category_relative_size_count"
Q = {"larger_than_reference_in_category_count": "larger", "smaller_than_reference_in_category_count": "smaller"}
D = dict(relative_size_reference_gap_min=20, relative_size_answer_count_min=1, relative_size_answer_count_max=5)
PGM = "count(filter(items, category=target_category and encoded_value(item) comparison reference_item)); comparison={larger,smaller}; output=integer_value; annotation=bbox_set_map(reference_item,counted_items); scene=size_encoding; scope=category_relative_size_count"


def _build_plan(params, seed, query_id, _probs):
    direction = Q[str(query_id)]
    variant, variant_probs = V(params, instance_seed=seed, supported_variants=SINGLE_PANEL_SCENE_VARIANTS)
    dataset = DSET(scene_variant=variant, params=params, instance_seed=seed, attempt_index=int(params.get("_attempt_index", 0)))
    dataset = GAP(dataset, direction=direction, params=params, instance_seed=seed)
    selection = SEL(dataset, direction=direction, params=params)
    return P(dataset=dataset, selection=selection, params=params, scene_variant=variant, scene_variant_probabilities=variant_probs, prompt_key=query_id, annotation_kind="reference_counted_bbox_set_map", question_format="size_encoded_relative_count", program_code=PGM, reasoning_load=0.56, answer_type="integer", answer_hint='set "answer" to the requested number of items as an integer')


def _bind_annotation(plan, rendered):
    return ANN(rendered, {"reference_item": (str(plan.selection.trace["reference_item_id"]),), "counted_items": tuple(plan.selection.trace["counted_item_ids"])})


@register_task
class ChartsSizeEncodingCategoryRelativeSizeCountTask:
    task_id = T
    domain = DOMAIN
    objective_contract = "category_relative_size_count"
    supported_query_ids = tuple(Q)
    default_query_id = "larger_than_reference_in_category_count"
    default_dataset_enabled = True

    def generate(self, instance_seed, *, params, max_attempts):
        return R(task=self, instance_seed=instance_seed, params={**D, **dict(params)}, max_attempts=max_attempts, default_query_id=self.default_query_id, build_plan=_build_plan, bind_annotation=_bind_annotation)


__all__ = ["ChartsSizeEncodingCategoryRelativeSizeCountTask"]
