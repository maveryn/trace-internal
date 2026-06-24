"""Select panels by one segment ranking and sum another segment count."""

from __future__ import annotations

from trace.core.query_ids import SINGLE_QUERY_ID as Q
from trace.core.seed import spawn_rng
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import group_default

from ._lifecycle import package_panel_segment_sum_selection as S, package_small_multiple_plan as P, run_small_multiple_lifecycle as R
from .shared.defaults import GEN_DEFAULTS, resolve_scene_variant as V
from .shared.sampling import (
    balanced_int,
    build_base_panels,
    package_dataset,
    ranked_share_fixtures,
    sample_scene_frame,
    top_panels_by_share,
)
from .shared.state import DOMAIN


T = "task_charts__small_multiple__top_k_by_segment_then_sum_other_segment_count"
PGM = "sum(count(panel,target_segment) for panel in top_k(panels, share(panel,rank_segment), k)); output=integer_count; annotation=point_map(rank_segment,target_segment,total for selected_panels); scene=small_multiple; scope=top_k_by_segment_then_sum_other_segment_count"
PROMPT_KEY = "top_k_by_segment_then_sum_other_segment_count"
ANNOTATION_HINT = 'set "annotation" to an object using exactly these keys: {annotation_key_list}. Put [x,y] pixel points at the centers of the corresponding selected-panel percentage labels or total-count text'
JSON_EXAMPLE = '{"annotation":{"rank|2020|A":[230,250],"target|2020|B":[260,280],"total|2020":[245,110],"rank|2021|A":[500,255],"target|2021|B":[520,300],"total|2021":[505,112]},"answer":780}'
JSON_EXAMPLE_ANSWER_ONLY = '{"answer":780}'


def _build_plan(params, seed, _query_id, _probs):
    """Build the rank-then-sum objective plan for this public task."""

    variant, variant_probs = V(params, instance_seed=seed)
    frame = sample_scene_frame(params, instance_seed=seed)
    rng = spawn_rng(int(seed), f"{T}.objective")
    rank_segment, target_segment = rng.sample(list(frame.segment_labels), 2)
    top_k_values = tuple(int(value) for value in params.get("top_k_values", group_default(GEN_DEFAULTS, "top_k_values", [2, 3])))
    feasible_k = [value for value in top_k_values if 1 < int(value) < len(frame.panel_labels)]
    top_k = balanced_int(feasible_k, params=params, instance_seed=seed, namespace=f"{T}.top_k")
    fixed_by_panel = ranked_share_fixtures(
        frame.panel_labels,
        segment=str(rank_segment),
        support_values=[16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56],
        rng=rng,
    )
    panels = build_base_panels(frame=frame, instance_seed=seed, fixed_by_panel=fixed_by_panel)
    dataset = package_dataset(frame, panels)
    selected = top_panels_by_share(panels, segment=str(rank_segment), k=int(top_k))
    selection = S(
        selected_panels=selected,
        target_segment=str(target_segment),
        role_segments=(("rank", str(rank_segment)), ("target", str(target_segment))),
        include_total=True,
        trace={
            "rank_segment": str(rank_segment),
            "target_segment": str(target_segment),
            "top_k": int(top_k),
            "selected_panels": [str(panel.label) for panel in selected],
            "calculation": "rank_panels_then_sum_target_counts",
        },
    )
    return P(
        dataset=dataset,
        selection=selection,
        params=params,
        scene_variant=variant,
        scene_variant_probabilities=variant_probs,
        prompt_key=PROMPT_KEY,
        annotation_hint_template=ANNOTATION_HINT,
        json_example=JSON_EXAMPLE,
        json_example_answer_only=JSON_EXAMPLE_ANSWER_ONLY,
        program_code=PGM,
        reasoning_load=0.82,
    )


@register_task
class ChartsCompositionSmallMultiplesTopKBySegmentThenSumOtherSegmentCountTask:
    task_id = T
    domain = DOMAIN
    objective_contract = "top_k_by_segment_then_sum_other_segment_count"
    supported_query_ids = (Q,)
    default_query_id = Q
    default_dataset_enabled = True

    def generate(self, instance_seed, *, params, max_attempts):
        return R(task=self, instance_seed=instance_seed, params=dict(params), max_attempts=max_attempts, default_query_id=self.default_query_id, build_plan=_build_plan)


__all__ = ["ChartsCompositionSmallMultiplesTopKBySegmentThenSumOtherSegmentCountTask"]
