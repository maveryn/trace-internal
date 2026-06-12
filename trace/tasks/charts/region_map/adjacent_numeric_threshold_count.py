"""Count highlighted-region neighbors satisfying a numeric threshold."""

from __future__ import annotations

from typing import Any, Dict

from ....core.seed import hash64
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.fixed_query import select_task_query_id
from ...shared.output_metadata import default_task_versions
from .shared.choropleth_config import _resolve_scene_variant
from .shared.choropleth_region_label import build_region_map_task_components


QUERY_ID = "adjacent_numeric_threshold_count"
TASK_PARAM_DEFAULTS: Dict[str, Any] = {
    'count_answer_min': 1,
    'count_answer_max': 5,
    'legend_bin_count_min': 4,
    'legend_bin_count_max': 6,
    'geographic_selected_region_count_min': 10,
    'geographic_selected_region_count_max': 18,
    'adjacent_neighbor_count_min': 2,
    'adjacent_neighbor_count_max': 7,
    'adjacent_min_shared_length_deg': 0.15,
    'adjacent_reference_min_area_sqdeg': 0.0,
    'adjacent_neighbor_min_area_sqdeg': 0.0,
    'region_gap_px': 0,
}


@register_task
class ChartsMapAdjacentNumericThresholdCountTask:
    """Count highlighted-region neighbors satisfying a numeric threshold."""

    task_id = "task_charts__region_map__adjacent_numeric_threshold_count"
    domain = "charts"
    scene_id = "region_map"
    objective_contract = "adjacent_numeric_threshold_count"
    supported_query_ids = (QUERY_ID,)
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query_id, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params={**TASK_PARAM_DEFAULTS, **dict(params)},
            supported_query_ids=self.supported_query_ids,
            default_query_id=QUERY_ID,
            task_id=self.task_id,
        )
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_seed = int(instance_seed) if attempt_index == 0 else int(hash64(int(instance_seed), self.task_id, attempt_index))
            try:
                attempt_params = {**dict(task_params), "_attempt_index": int(attempt_index)}
                return self._generate_once(
                    int(attempt_seed),
                    params=attempt_params,
                    selected_query_id=str(selected_query_id),
                    query_probabilities=query_probabilities,
                )
            except ValueError as exc:
                last_error = exc
        raise RuntimeError(f"failed to generate {self.task_id}: {last_error}")

    def _generate_once(
        self,
        instance_seed: int,
        *,
        params: Dict[str, Any],
        selected_query_id: str,
        query_probabilities: Dict[str, float],
    ) -> TaskOutput:
        task_params = dict(params)
        task_params["scene_variant"] = "synthetic_region_map"
        scene_variant = "synthetic_region_map"
        scene_variant_probabilities = {"synthetic_region_map": 1.0}
        components = build_region_map_task_components(
            query_id=str(selected_query_id),
            scene_variant=str(scene_variant),
            query_id_probabilities=query_probabilities,
            scene_variant_probabilities=scene_variant_probabilities,
            instance_seed=int(instance_seed),
            params=task_params,
        )
        return TaskOutput(
            prompt=str(components.prompt),
            prompt_variants=dict(components.prompt_variants),
            answer_gt=TypedValue(type=str(components.answer_type), value=components.answer_value),
            annotation_gt=TypedValue(type=str(components.annotation_type), value=list(components.annotation_value)),
            image=components.image,
            image_id="img0",
            trace_payload=dict(components.trace_payload),
            task_versions=default_task_versions(),
            scene_id="region_map",
            query_id=str(components.query_id),
        )


__all__ = ["ChartsMapAdjacentNumericThresholdCountTask"]
