"""Public task for `task_charts__contour_density__density_extremum_region_label`."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.base import TaskOutput
from trace.tasks.charts.contour_density._lifecycle import ContourTaskPlan, contour_task_output_fields, run_contour_public_task
from trace.tasks.charts.contour_density.shared.defaults import DOMAIN, SCENE_NAMESPACE, SUPPORTED_DENSITY_EXTREMA
from trace.tasks.charts.contour_density.shared.prompts import build_prompt_artifacts
from trace.tasks.charts.contour_density.shared.sampling import balanced_choice, build_regions, region_count, region_labels, resolve_semantic_axis, scene_variant
from trace.tasks.charts.contour_density.shared.state import ContourDataset, QuerySelection
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id


QUERY_ID = "density_extremum_region_label"


def _build_task_output(materialized):
    return TaskOutput(**contour_task_output_fields(materialized))


@register_task
class ChartsContourDensityDensityExtremumRegionLabelTask:
    """Return the region label with the highest or lowest density."""

    task_id = "task_charts__contour_density__density_extremum_region_label"
    domain = DOMAIN
    objective_contract = "density_extremum_region_label"
    supported_query_ids = (QUERY_ID,)
    default_dataset_enabled = True

    def _build_density_extremum_plan(self, instance_seed: int, params: Mapping[str, Any], selected_query_id: str) -> ContourTaskPlan:
        """Bind the unique density extremum before neutral rendering projects the selected region."""

        scene_name, scene_probabilities = scene_variant(params, instance_seed=int(instance_seed))
        extremum, extremum_probabilities = resolve_semantic_axis(
            params,
            instance_seed=int(instance_seed),
            supported=SUPPORTED_DENSITY_EXTREMA,
            explicit_key="density_extremum",
            weights_key="density_extremum_weights",
            balance_key="balanced_density_extremum_sampling",
            namespace="density_extremum",
        )
        count = region_count(params, instance_seed=int(instance_seed))
        labels = region_labels(int(count), instance_seed=int(instance_seed))
        answer_index = int(
            balanced_choice(
                list(range(int(count))),
                params,
                instance_seed=int(instance_seed),
                namespace=f"{SCENE_NAMESPACE}.density_extremum.answer",
            )
        )
        densities = [0.42 + (0.05 * index) for index in range(int(count))]
        if str(extremum) == "highest":
            densities[int(answer_index)] = 0.98
            for index in range(int(count)):
                if int(index) != int(answer_index):
                    densities[int(index)] = min(0.78, densities[int(index)])
        else:
            densities[int(answer_index)] = 0.28
            for index in range(int(count)):
                if int(index) != int(answer_index):
                    densities[int(index)] = max(0.48, densities[int(index)])
        regions = build_regions(
            count=int(count),
            labels=labels,
            option_labels=(),
            densities=densities,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.density_extremum.regions",
        )
        density_by_label = {str(region.label): float(region.density) for region in regions}
        answer_label = max(density_by_label, key=lambda label: (density_by_label[label], label)) if str(extremum) == "highest" else min(density_by_label, key=lambda label: (density_by_label[label], label))
        answer_region = next(region for region in regions if str(region.label) == str(answer_label))
        selection = QuerySelection(
            prompt_key=str(selected_query_id),
            answer=str(answer_label),
            answer_type="string",
            annotation_type="keyed_bbox_map",
            annotation_roles={"answer_region": str(answer_region.region_id)},
            annotation_region_ids=(),
            trace={
                "density_extremum": str(extremum),
                "density_extremum_phrase": "highest" if str(extremum) == "highest" else "lowest",
                "density_by_region_label": {key: round(float(value), 3) for key, value in density_by_label.items()},
                "density_extremum_probabilities": dict(extremum_probabilities),
                "scene_variant_probabilities": dict(scene_probabilities),
            },
        )
        dataset = ContourDataset(scene_variant=str(scene_name), regions=tuple(regions), query=selection, reference=None)
        prompt_artifacts = build_prompt_artifacts(
            prompt_query_key=str(selected_query_id),
            dynamic_slots={"density_extremum_phrase": str(selection.trace["density_extremum_phrase"])},
            instance_seed=int(instance_seed),
        )
        return ContourTaskPlan(
            dataset=dataset,
            prompt_artifacts=prompt_artifacts,
            relations={"scene_variant": str(scene_name), "region_count": int(len(dataset.regions)), **dict(selection.trace)},
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
            build_plan=self._build_density_extremum_plan,
            build_output=_build_task_output,
        )

__all__ = ["ChartsContourDensityDensityExtremumRegionLabelTask"]
