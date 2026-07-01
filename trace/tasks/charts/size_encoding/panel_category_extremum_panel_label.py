"""Select the panel containing a category's extremal size-encoded item."""

from __future__ import annotations

from trace.tasks.charts.size_encoding._lifecycle import package_size_encoding_plan as P, run_size_encoding_lifecycle as R
from trace.tasks.charts.size_encoding.shared.annotations import item_bbox as B
from trace.tasks.charts.size_encoding.shared.defaults import resolve_scene_variant as V
from trace.tasks.charts.size_encoding.shared.sampling import (
    build_size_encoding_dataset as DSET,
    enforce_panel_category_extreme_gap as GAP,
    select_panel_category_extreme_panel as SEL,
)
from trace.tasks.charts.size_encoding.shared.state import DOMAIN, PANEL_SCENE_VARIANTS
from trace.tasks.registry import register_task

T = "task_charts__size_encoding__panel_category_extremum_panel_label"
Q = {"largest_category_item_panel_label": "largest", "smallest_category_item_panel_label": "smallest"}
D = dict(
    panel_count_min=4,
    panel_count_max=4,
    panel_item_count_min=6,
    panel_item_count_max=8,
    total_item_count_min=24,
    total_item_count_max=32,
    panel_category_item_winner_gap_min=24,
    panel_category_item_winner_gap_max=36,
)
PGM = "select_label(panel(arg_extreme(filter(items, category=target_category), encoded_value(item), direction))); output=string_label; annotation=bbox(answer_item); scene=size_encoding; scope=panel_category_extremum_panel_label"


def _build_plan(params, seed, query_id, _probs):
    direction = Q[str(query_id)]
    variant, variant_probs = V(params, instance_seed=seed, supported_variants=PANEL_SCENE_VARIANTS)
    dataset = DSET(scene_variant=variant, params=params, instance_seed=seed, attempt_index=int(params.get("_attempt_index", 0)))
    dataset = GAP(dataset, direction=direction, params=params, instance_seed=seed)
    selection = SEL(dataset, direction=direction, params=params)
    return P(dataset=dataset, selection=selection, params=params, scene_variant=variant, scene_variant_probabilities=variant_probs, prompt_key=query_id, annotation_kind="answer_item_bbox", question_format="size_encoded_panel_label_comparison", program_code=PGM, reasoning_load=0.70)


def _bind_annotation(plan, rendered):
    box = B(rendered, plan.selection.annotation_item_ids[0])
    return "bbox", box, {"type": "bbox", "bbox": box, "pixel_bbox": box, "bbox_set": [box]}


@register_task
class ChartsSizeEncodingPanelCategoryExtremumPanelLabelTask:
    task_id = T
    domain = DOMAIN
    objective_contract = "panel_category_extremum_panel_label"
    supported_query_ids = tuple(Q)
    default_query_id = "largest_category_item_panel_label"
    default_dataset_enabled = True

    def generate(self, instance_seed, *, params, max_attempts):
        return R(task=self, instance_seed=instance_seed, params={**D, **dict(params)}, max_attempts=max_attempts, default_query_id=self.default_query_id, build_plan=_build_plan, bind_annotation=_bind_annotation)


__all__ = ["ChartsSizeEncodingPanelCategoryExtremumPanelLabelTask"]
