"""Public task for `task_charts__contour_density__nearest_region_option_label`."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.base import TaskOutput
from trace.tasks.charts.contour_density._lifecycle import ContourTaskPlan, contour_task_output_fields, run_contour_public_task
from trace.tasks.charts.contour_density.shared.defaults import DOMAIN, SCENE_NAMESPACE
from trace.tasks.charts.contour_density.shared.prompts import build_prompt_artifacts
from trace.tasks.charts.contour_density.shared.sampling import (
    balanced_choice,
    build_regions,
    distance_to_reference,
    option_count_support,
    option_labels_for_count,
    scene_variant,
)
from trace.tasks.charts.contour_density.shared.state import ContourDataset, QuerySelection, Reference
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id


QUERY_ID = "nearest_region_option_label"


def _build_task_output(materialized):
    return TaskOutput(**contour_task_output_fields(materialized))


@register_task
class ChartsContourDensityNearestRegionOptionLabelTask:
    """Choose the option region nearest to a marked reference point."""

    task_id = "task_charts__contour_density__nearest_region_option_label"
    domain = DOMAIN
    objective_contract = "nearest_region_option_label"
    supported_query_ids = (QUERY_ID,)
    default_dataset_enabled = True

    def _build_nearest_option_plan(self, instance_seed: int, params: Mapping[str, Any], selected_query_id: str) -> ContourTaskPlan:
        """Place the reference near the sampled answer option so nearest-region selection is unique."""

        scene_name, scene_probabilities = scene_variant(params, instance_seed=int(instance_seed))
        option_count = int(
            balanced_choice(
                option_count_support(params),
                params,
                instance_seed=int(instance_seed),
                namespace=f"{SCENE_NAMESPACE}.nearest_option.option_count",
            )
        )
        option_labels = option_labels_for_count(int(option_count))
        answer_option = str(
            balanced_choice(
                option_labels,
                params,
                instance_seed=int(instance_seed),
                namespace=f"{SCENE_NAMESPACE}.nearest_option.answer",
            )
        )
        answer_index = option_labels.index(str(answer_option))
        densities = [0.55 + (0.28 * float(index) / float(max(1, int(option_count) - 1))) for index in range(int(option_count))]
        regions = list(
            build_regions(
                count=int(option_count),
                labels=option_labels,
                option_labels=option_labels,
                densities=densities,
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{SCENE_NAMESPACE}.nearest_option.regions",
            )
        )
        answer_region = regions[int(answer_index)]
        reference = Reference(
            kind="point",
            x_value=max(5.0, min(95.0, float(answer_region.center_x) + 2.0)),
            y_value=max(5.0, min(95.0, float(answer_region.center_y) - 2.0)),
        )
        distances = {str(region.option_label): distance_to_reference(region, reference) for region in regions}
        if min(distances, key=lambda label: (distances[label], label)) != str(answer_option):
            raise RuntimeError("nearest-option construction lost unique answer")
        selection = QuerySelection(
            prompt_key=str(selected_query_id),
            answer=str(answer_option),
            answer_type="option_letter",
            annotation_type="keyed_bbox_map",
            annotation_roles={"reference_point": "reference", "selected_option_region": str(answer_region.region_id)},
            annotation_region_ids=(),
            trace={
                "option_count": int(option_count),
                "option_count_support": list(option_count_support(params)),
                "option_region_labels": list(option_labels),
                "reference_kind": "point",
                "reference_value": {"x": round(float(reference.x_value), 3), "y": round(float(reference.y_value), 3)},
                "distance_extremum": "nearest",
                "distances_by_option": {key: round(float(value), 3) for key, value in distances.items()},
                "scene_variant_probabilities": dict(scene_probabilities),
            },
        )
        dataset = ContourDataset(scene_variant=str(scene_name), regions=tuple(regions), query=selection, reference=reference)
        prompt_artifacts = build_prompt_artifacts(prompt_query_key=str(selected_query_id), dynamic_slots={}, instance_seed=int(instance_seed))
        return ContourTaskPlan(
            dataset=dataset,
            prompt_artifacts=prompt_artifacts,
            relations={
                "scene_variant": str(scene_name),
                "region_count": int(len(dataset.regions)),
                **dict(selection.trace),
            },
        )

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query_id, _probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=self.supported_query_ids,
            default_query_id=QUERY_ID,
            task_id=self.task_id,
        )
        return run_contour_public_task(
            instance_seed=int(instance_seed),
            params=task_params,
            max_attempts=int(max_attempts),
            selected_query_id=str(selected_query_id),
            failure_label=self.task_id,
            build_plan=self._build_nearest_option_plan,
            build_output=_build_task_output,
        )


__all__ = ["ChartsContourDensityNearestRegionOptionLabelTask"]
