"""Compute the L1 composition shift between two panels."""

from __future__ import annotations

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.core.seed import spawn_rng
from trace.tasks.charts.small_multiple._lifecycle import package_small_multiple_plan as P, run_small_multiple_lifecycle as R
from trace.tasks.charts.small_multiple.shared.defaults import resolve_scene_variant as V
from trace.tasks.charts.small_multiple.shared.sampling import build_base_panels, package_dataset, sample_scene_frame
from trace.tasks.charts.small_multiple.shared.state import AnnotationRole, DOMAIN, SmallMultipleSelection
from trace.tasks.registry import register_task


T = "task_charts__small_multiple__composition_shift_l1_distance"
TASK_PARAM_DEFAULTS = {"panel_count_min": 4, "panel_count_max": 7, "segment_count_min": 5, "segment_count_max": 5}
PGM = "sum(abs(share(end_panel,segment)-share(start_panel,segment)) for segment in segments); output=integer_value; annotation=point_map(start_end_segment_points); scene=small_multiple; scope=composition_shift_l1_distance"
PROMPT_KEY = "composition_shift_l1_distance"
ANNOTATION_HINT = 'set "annotation" to an object using exactly these keys: {annotation_key_list}. Put [x,y] pixel points at the centers of the corresponding start/end panel segment percentage labels'
JSON_EXAMPLE = '{"annotation":{"start|2020|A":[240,250],"end|2023|A":[620,250],"start|2020|B":[240,310],"end|2023|B":[620,310]},"answer":28}'
JSON_EXAMPLE_ANSWER_ONLY = '{"answer":28}'


def _build_plan(params, seed, _query_id, _probs):
    """Build the two-panel L1 composition-shift objective plan."""

    task_params = {**TASK_PARAM_DEFAULTS, **dict(params)}
    variant, variant_probs = V(task_params, instance_seed=seed)
    frame = sample_scene_frame(task_params, instance_seed=seed)
    rng = spawn_rng(int(seed), f"{T}.objective")
    panels = build_base_panels(frame=frame, instance_seed=seed)
    dataset = package_dataset(frame, panels)
    start_label, end_label = rng.sample(list(frame.panel_labels), 2)
    by_label = {str(panel.label): panel for panel in panels}
    start_panel = by_label[str(start_label)]
    end_panel = by_label[str(end_label)]
    changes = tuple(
        abs(int(end_panel.shares_by_segment[str(segment)]) - int(start_panel.shares_by_segment[str(segment)]))
        for segment in frame.segment_labels
    )
    roles = tuple(
        AnnotationRole(str(role), str(panel_label), str(segment))
        for role, panel_label in (("start", str(start_panel.label)), ("end", str(end_panel.label)))
        for segment in frame.segment_labels
    )
    selection = SmallMultipleSelection(
        answer_value=int(sum(changes)),
        annotation_values=tuple(int(value) for value in changes),
        annotation_roles=roles,
        question_format="numeric_open",
        trace={
            "start_panel": str(start_panel.label),
            "end_panel": str(end_panel.label),
            "segment_changes": [int(value) for value in changes],
            "calculation": "sum_absolute_percentage_point_changes",
        },
    )
    return P(
        dataset=dataset,
        selection=selection,
        params=task_params,
        scene_variant=variant,
        scene_variant_probabilities=variant_probs,
        prompt_key=PROMPT_KEY,
        annotation_hint_template=ANNOTATION_HINT,
        json_example=JSON_EXAMPLE,
        json_example_answer_only=JSON_EXAMPLE_ANSWER_ONLY,
        program_code=PGM,
        reasoning_load=0.84,
    )


@register_task
class ChartsCompositionSmallMultiplesCompositionShiftL1DistanceTask:
    task_id = T
    domain = DOMAIN
    objective_contract = "composition_shift_l1_distance"
    supported_query_ids = (SINGLE_QUERY_ID,)
    default_query_id = SINGLE_QUERY_ID
    default_dataset_enabled = True

    def generate(self, instance_seed, *, params, max_attempts):
        return R(task=self, instance_seed=instance_seed, params={**TASK_PARAM_DEFAULTS, **dict(params)}, max_attempts=max_attempts, default_query_id=self.default_query_id, build_plan=_build_plan)


__all__ = ["ChartsCompositionSmallMultiplesCompositionShiftL1DistanceTask"]
