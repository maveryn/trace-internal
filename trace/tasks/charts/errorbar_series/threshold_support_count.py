"""Public task for `task_charts__errorbar_series__threshold_support_count`."""

from __future__ import annotations

from typing import Any

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.charts.errorbar_series._lifecycle import ErrorbarSeriesTaskPlan, run_errorbar_series_plan
from trace.tasks.charts.errorbar_series.shared.defaults import (
    GEN_DEFAULTS,
    choose_from_values,
)
from trace.tasks.charts.errorbar_series.shared.prompts import build_prompt_artifacts, dynamic_slots
from trace.tasks.charts.errorbar_series.shared.sampling import (
    make_series,
    palette,
    random_series_triples,
    sample_base_scene,
)
from trace.tasks.charts.errorbar_series.shared.state import DOMAIN, ErrorbarDataset, ErrorbarQuery, SCENE_ID, SCENE_NAMESPACE
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import resolve_required_int_bounds


TASK_ID = "task_charts__errorbar_series__threshold_support_count"
OBJECTIVE_CONTRACT = "threshold_support_count"
QUERY_IDS = (
    "entirely_above_threshold_count",
    "entirely_below_threshold_count",
    "contains_threshold_count",
)
DEFAULT_QUERY_ID = "entirely_above_threshold_count"
_QUERY_PHRASES = {
    "entirely_above_threshold_count": "entirely above",
    "entirely_below_threshold_count": "entirely below",
    "contains_threshold_count": "containing",
}


@register_task
class ChartsErrorbarSeriesThresholdSupportCountTask:
    """Count x positions whose error bars support a threshold relation."""

    task_id = TASK_ID
    domain = DOMAIN
    objective_contract = OBJECTIVE_CONTRACT
    supported_query_ids = QUERY_IDS
    default_dataset_enabled = True

    def _build_plan(self, instance_seed: int, *, params: dict[str, Any], selected_query_id: str) -> ErrorbarSeriesTaskPlan:
        """Bind the threshold-count objective for one relation query."""

        if str(selected_query_id) not in _QUERY_PHRASES:
            raise ValueError(f"unsupported query_id: {selected_query_id}")
        rng = spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.threshold")
        base = sample_base_scene(params, instance_seed=int(instance_seed), series_mode="standard")
        threshold_low, threshold_high = resolve_required_int_bounds(
            params,
            GEN_DEFAULTS,
            min_key="threshold_value_min",
            max_key="threshold_value_max",
            fallback_min=38,
            fallback_max=62,
            context=f"generation defaults for {SCENE_NAMESPACE}",
        )
        threshold = int(
            choose_from_values(
                params,
                values=tuple(range(int(threshold_low), int(threshold_high) + 1)),
                instance_seed=int(instance_seed),
                namespace=f"{SCENE_NAMESPACE}.threshold_value",
            )
        )
        answer_min, answer_max = resolve_required_int_bounds(
            params,
            GEN_DEFAULTS,
            min_key="threshold_answer_count_min",
            max_key="threshold_answer_count_max",
            fallback_min=1,
            fallback_max=5,
            context=f"generation defaults for {SCENE_NAMESPACE}",
        )
        max_answer = min(int(answer_max), int(base.x_count))
        answer_count = int(
            choose_from_values(
                params,
                values=tuple(range(int(answer_min), int(max_answer) + 1)),
                instance_seed=int(instance_seed),
                namespace=f"{SCENE_NAMESPACE}.threshold_answer_count",
            )
        )
        target_series_index = int(
            choose_from_values(
                params,
                values=tuple(range(int(base.series_count))),
                instance_seed=int(instance_seed),
                namespace=f"{SCENE_NAMESPACE}.threshold.target_series",
            )
        )
        answer_indices = set(rng.sample(list(range(int(base.x_count))), k=int(answer_count)))
        colors = palette(params)
        series_rows = []
        for series_index in range(int(base.series_count)):
            triples = random_series_triples(rng, x_count=int(base.x_count))
            if int(series_index) == int(target_series_index):
                triples = self._threshold_triples(
                    rng,
                    prompt_key=str(selected_query_id),
                    x_count=int(base.x_count),
                    answer_indices=answer_indices,
                    threshold=int(threshold),
                )
            series_rows.append(
                make_series(
                    series_id=f"series_{series_index}",
                    label=str(base.series_labels[int(series_index)]),
                    color_rgb=colors[int(series_index) % len(colors)],
                    triples=triples,
                )
            )
        target = series_rows[int(target_series_index)]
        annotation_keys = tuple(f"{target.label}:{base.x_labels[index]}" for index in sorted(answer_indices))
        relation_params = {
            "query_id": str(selected_query_id),
            "scene_id": SCENE_ID,
            "scene_variant": str(base.scene_variant),
            "scene_variant_probabilities": dict(base.scene_variant_probabilities),
            "x_count": int(base.x_count),
            "series_count": int(base.series_count),
            "target_series_id": str(target.series_id),
            "target_series_label": str(target.label),
            "threshold_value": int(threshold),
            "threshold_relation": str(selected_query_id).replace("_threshold_count", ""),
            "answer_x_indices": sorted(int(index) for index in answer_indices),
            "answer_value": int(answer_count),
        }
        dataset = ErrorbarDataset(
            x_labels=tuple(base.x_labels),
            x_label_meta=dict(base.x_label_meta),
            series=tuple(series_rows),
            series_label_meta=dict(base.series_label_meta),
            scene_variant=str(base.scene_variant),
            scene_variant_probabilities=dict(base.scene_variant_probabilities),
            prompt_key=str(selected_query_id),
            prompt_key_probabilities={str(selected_query_id): 1.0},
            threshold_value=int(threshold),
            target_series_id=str(target.series_id),
            target_x_index=None,
            title=str(base.title),
            query=ErrorbarQuery(
                prompt_key=str(selected_query_id),
                answer=int(answer_count),
                answer_type="integer",
                annotation_kind="bbox_set",
                annotation_item_keys=tuple(annotation_keys),
                params=dict(relation_params),
            ),
        )
        prompt_artifacts = build_prompt_artifacts(
            prompt_query_key=str(selected_query_id),
            dynamic_slot_values=dynamic_slots(
                dataset,
                threshold_relation_phrase=str(_QUERY_PHRASES[str(selected_query_id)]),
            ),
            instance_seed=int(instance_seed),
        )
        return ErrorbarSeriesTaskPlan(
            dataset=dataset,
            params=dict(params),
            answer_gt=TypedValue(type="integer", value=int(answer_count)),
            prompt_artifacts=prompt_artifacts,
            relation_params=relation_params,
        )

    @staticmethod
    def _threshold_triples(
        rng: Any,
        *,
        prompt_key: str,
        x_count: int,
        answer_indices: set[int],
        threshold: int,
    ) -> list[tuple[int, int, int]]:
        """Construct intervals so the selected x positions exactly match the predicate."""

        adjusted: list[tuple[int, int, int]] = []
        for x_index in range(int(x_count)):
            selected = int(x_index) in answer_indices
            if str(prompt_key) == "entirely_above_threshold_count":
                if selected:
                    lower = min(92, int(threshold) + int(rng.randint(6, 18)))
                    upper = min(100, lower + int(rng.randint(6, 16)))
                elif rng.random() < 0.55:
                    lower = max(0, int(threshold) - int(rng.randint(8, 18)))
                    upper = int(threshold) + int(rng.randint(2, 10))
                else:
                    upper = max(2, int(threshold) - int(rng.randint(2, 13)))
                    lower = max(0, upper - int(rng.randint(6, 16)))
            elif str(prompt_key) == "entirely_below_threshold_count":
                if selected:
                    upper = max(8, int(threshold) - int(rng.randint(6, 18)))
                    lower = max(0, upper - int(rng.randint(6, 16)))
                elif rng.random() < 0.55:
                    lower = max(0, int(threshold) - int(rng.randint(8, 18)))
                    upper = int(threshold) + int(rng.randint(2, 10))
                else:
                    lower = min(92, int(threshold) + int(rng.randint(2, 13)))
                    upper = min(100, lower + int(rng.randint(6, 16)))
            else:
                if selected:
                    lower = max(0, int(threshold) - int(rng.randint(6, 18)))
                    upper = min(100, int(threshold) + int(rng.randint(6, 18)))
                elif rng.random() < 0.5:
                    upper = max(3, int(threshold) - int(rng.randint(3, 16)))
                    lower = max(0, upper - int(rng.randint(6, 16)))
                else:
                    lower = min(94, int(threshold) + int(rng.randint(3, 16)))
                    upper = min(100, lower + int(rng.randint(6, 16)))
            mid = int(round((int(lower) + int(upper)) / 2))
            adjusted.append((int(lower), int(mid), int(upper)))
        return adjusted

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        return run_errorbar_series_plan(
            task_id=self.task_id,
            supported_query_ids=self.supported_query_ids,
            default_query_id=DEFAULT_QUERY_ID,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
            build_plan=self._build_plan,
        )


__all__ = ["ChartsErrorbarSeriesThresholdSupportCountTask"]
