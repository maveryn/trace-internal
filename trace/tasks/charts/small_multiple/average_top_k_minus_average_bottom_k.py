"""Compute the difference between top-k and bottom-k segment averages."""

from __future__ import annotations

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.core.seed import spawn_rng
from trace.tasks.charts.small_multiple._lifecycle import package_small_multiple_plan as P, run_small_multiple_lifecycle as R
from trace.tasks.charts.small_multiple.shared.defaults import resolve_scene_variant as V
from trace.tasks.charts.small_multiple.shared.sampling import build_base_panels, package_dataset, sample_scene_frame
from trace.tasks.charts.small_multiple.shared.state import AnnotationRole, DOMAIN, SmallMultipleSelection
from trace.tasks.registry import register_task


T = "task_charts__small_multiple__average_top_k_minus_average_bottom_k"
TASK_PARAM_DEFAULTS = {"panel_count_min": 4, "panel_count_max": 7, "segment_count_min": 5, "segment_count_max": 5}
PGM = "difference(mean(share(panel,target_segment) for panel in top_k(panels, share(panel,rank_segment), k)), mean(share(panel,target_segment) for panel in bottom_k(panels, share(panel,rank_segment), k))); output=integer_value; annotation=point_map(rank_segment,target_segment for top_bottom_panels); scene=small_multiple; scope=average_top_k_minus_average_bottom_k"
PROMPT_KEY = "average_top_k_minus_average_bottom_k"
ANNOTATION_HINT = 'set "annotation" to an object using exactly these keys: {annotation_key_list}. Put [x,y] pixel points at the centers of the corresponding highest/lowest panel percentage labels'
JSON_EXAMPLE = '{"annotation":{"rank|2020|A":[220,240],"target|2020|B":[240,260],"rank|2021|A":[460,260],"target|2021|B":[480,280],"rank|2022|A":[700,340],"target|2022|B":[720,360],"rank|2023|A":[940,360],"target|2023|B":[960,380]},"answer":20}'
JSON_EXAMPLE_ANSWER_ONLY = '{"answer":20}'


def _build_plan(params, seed, _query_id, _probs):
    """Build the top/bottom average-difference objective plan for this task."""

    task_params = {**TASK_PARAM_DEFAULTS, **dict(params)}
    variant, variant_probs = V(task_params, instance_seed=seed)
    frame = sample_scene_frame(task_params, instance_seed=seed)
    rng = spawn_rng(int(seed), f"{T}.objective")
    rank_segment, target_segment = rng.sample(list(frame.segment_labels), 2)
    k = 2
    rank_support = [10, 12, 14, 16, 18, 20, 22, 24, 26]
    rng.shuffle(rank_support)
    ordered_labels = list(frame.panel_labels)
    ranked_preview = sorted(
        [(str(label), int(rank_support[index])) for index, label in enumerate(ordered_labels)],
        key=lambda item: item[1],
        reverse=True,
    )
    top_labels = {label for label, _ in ranked_preview[:k]}
    bottom_labels = {label for label, _ in ranked_preview[-k:]}
    target_values_by_label: dict[str, int] = {}
    for label in ordered_labels:
        if str(label) in top_labels:
            target_values_by_label[str(label)] = int(rng.choice([26, 30, 34]))
        elif str(label) in bottom_labels:
            target_values_by_label[str(label)] = int(rng.choice([8, 12, 16, 20, 24]))
        else:
            target_values_by_label[str(label)] = int(rng.choice([14, 18, 22]))
    fixed_by_panel = {
        str(label): {
            str(rank_segment): int(rank_support[index]),
            str(target_segment): int(target_values_by_label[str(label)]),
        }
        for index, label in enumerate(ordered_labels)
    }
    panels = build_base_panels(frame=frame, instance_seed=seed, fixed_by_panel=fixed_by_panel)
    dataset = package_dataset(frame, panels)
    sorted_panels = tuple(sorted(panels, key=lambda panel: int(panel.shares_by_segment[str(rank_segment)]), reverse=True))
    top_panels = sorted_panels[:k]
    bottom_panels = sorted_panels[-k:]
    top_values = tuple(int(panel.shares_by_segment[str(target_segment)]) for panel in top_panels)
    bottom_values = tuple(int(panel.shares_by_segment[str(target_segment)]) for panel in bottom_panels)
    top_avg = int(sum(top_values) // k)
    bottom_avg = int(sum(bottom_values) // k)
    roles: list[AnnotationRole] = []
    for panel in (*top_panels, *bottom_panels):
        roles.extend(
            (
                AnnotationRole("rank", str(panel.label), str(rank_segment)),
                AnnotationRole("target", str(panel.label), str(target_segment)),
            )
        )
    selection = SmallMultipleSelection(
        answer_value=int(top_avg - bottom_avg),
        annotation_values=tuple(int(value) for value in (*top_values, *bottom_values)),
        annotation_roles=tuple(roles),
        question_format="numeric_open",
        trace={
            "rank_segment": str(rank_segment),
            "target_segment": str(target_segment),
            "top_k": int(k),
            "bottom_k": int(k),
            "top_panels": [str(panel.label) for panel in top_panels],
            "bottom_panels": [str(panel.label) for panel in bottom_panels],
            "top_target_percentages": [int(value) for value in top_values],
            "bottom_target_percentages": [int(value) for value in bottom_values],
            "top_average": int(top_avg),
            "bottom_average": int(bottom_avg),
            "calculation": "rank_panels_then_subtract_average_target_percentages",
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
        reasoning_load=0.88,
    )


@register_task
class ChartsCompositionSmallMultiplesAverageTopKMinusAverageBottomKTask:
    task_id = T
    domain = DOMAIN
    objective_contract = "average_top_k_minus_average_bottom_k"
    supported_query_ids = (SINGLE_QUERY_ID,)
    default_query_id = SINGLE_QUERY_ID
    default_dataset_enabled = True

    def generate(self, instance_seed, *, params, max_attempts):
        return R(task=self, instance_seed=instance_seed, params={**TASK_PARAM_DEFAULTS, **dict(params)}, max_attempts=max_attempts, default_query_id=self.default_query_id, build_plan=_build_plan)


__all__ = ["ChartsCompositionSmallMultiplesAverageTopKMinusAverageBottomKTask"]
