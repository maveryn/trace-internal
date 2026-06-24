"""Compute a conditioned panel sum from percent composition values."""

from __future__ import annotations

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.core.seed import spawn_rng
from trace.tasks.charts.small_multiple._lifecycle import (
    package_panel_segment_sum_selection as S,
    package_small_multiple_plan as P,
    run_small_multiple_lifecycle as R,
)
from trace.tasks.charts.small_multiple.shared.defaults import GEN_DEFAULTS, resolve_scene_variant as V
from trace.tasks.charts.small_multiple.shared.sampling import (
    balanced_int,
    build_base_panels,
    package_dataset,
    sample_scene_frame,
)
from trace.tasks.charts.small_multiple.shared.state import DOMAIN
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import group_default


T = "task_charts__small_multiple__conditioned_panel_sum_from_percent"
PGM = "sum(count(panel,target_segment) for panel in filter(panels, share(panel,condition_segment) > threshold)); output=integer_value; annotation=point_map(condition_segment,target_segment,total for selected_panels); scene=small_multiple; scope=conditioned_panel_sum_from_percent"
PROMPT_KEY = "conditioned_panel_sum_from_percent"
ANNOTATION_HINT = 'set "annotation" to an object using exactly these keys: {annotation_key_list}. Put [x,y] pixel points at the centers of the corresponding selected-panel percentage labels or total-count text'
JSON_EXAMPLE = '{"annotation":{"condition|2020|A":[210,260],"target|2020|B":[240,290],"total|2020":[225,110],"condition|2021|A":[450,280],"target|2021|B":[480,310],"total|2021":[465,112]},"answer":720}'
JSON_EXAMPLE_ANSWER_ONLY = '{"answer":720}'


def _condition_share_fixtures(frame, *, condition_segment, threshold, selected_count, rng):
    chosen = set(rng.sample(list(frame.panel_labels), int(selected_count)))
    fixtures = {}
    for label in frame.panel_labels:
        if str(label) in chosen:
            value = int(rng.randint(int(threshold) + 5, 56))
        else:
            value = int(rng.randint(10, max(12, int(threshold) - 5)))
        fixtures[str(label)] = {str(condition_segment): int(value)}
    return fixtures


def _build_plan(params, seed, _query_id, _probs):
    """Build the filter-then-sum objective plan for this public task."""

    variant, variant_probs = V(params, instance_seed=seed)
    frame = sample_scene_frame(params, instance_seed=seed)
    rng = spawn_rng(int(seed), f"{T}.objective")
    condition_segment, target_segment = rng.sample(list(frame.segment_labels), 2)
    threshold_values = tuple(int(value) for value in params.get("condition_threshold_values", group_default(GEN_DEFAULTS, "condition_threshold_values", [32, 35, 38])))
    threshold = balanced_int(threshold_values, params=params, instance_seed=seed, namespace=f"{T}.threshold")
    selected_count_values = [value for value in range(2, len(frame.panel_labels)) if value < len(frame.panel_labels)]
    selected_count = balanced_int(selected_count_values, params=params, instance_seed=seed, namespace=f"{T}.selected_count")
    fixed_by_panel = _condition_share_fixtures(
        frame,
        condition_segment=str(condition_segment),
        threshold=int(threshold),
        selected_count=int(selected_count),
        rng=rng,
    )
    panels = build_base_panels(frame=frame, instance_seed=seed, fixed_by_panel=fixed_by_panel)
    dataset = package_dataset(frame, panels)
    selected = tuple(panel for panel in panels if int(panel.shares_by_segment[str(condition_segment)]) > int(threshold))
    selection = S(
        selected_panels=selected,
        target_segment=str(target_segment),
        role_segments=(("condition", str(condition_segment)), ("target", str(target_segment))),
        include_total=True,
        trace={
            "condition_segment": str(condition_segment),
            "target_segment": str(target_segment),
            "threshold": int(threshold),
            "selected_panels": [str(panel.label) for panel in selected],
            "calculation": "filter_panels_by_percentage_then_sum_target_counts",
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
        reasoning_load=0.78,
    )


@register_task
class ChartsCompositionSmallMultiplesConditionedPanelSumFromPercentTask:
    task_id = T
    domain = DOMAIN
    objective_contract = "conditioned_panel_sum_from_percent"
    supported_query_ids = (SINGLE_QUERY_ID,)
    default_query_id = SINGLE_QUERY_ID
    default_dataset_enabled = True

    def generate(self, instance_seed, *, params, max_attempts):
        return R(task=self, instance_seed=instance_seed, params=dict(params), max_attempts=max_attempts, default_query_id=self.default_query_id, build_plan=_build_plan)


__all__ = ["ChartsCompositionSmallMultiplesConditionedPanelSumFromPercentTask"]
