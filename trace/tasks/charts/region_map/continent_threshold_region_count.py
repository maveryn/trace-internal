from __future__ import annotations

from ....core.types import TypedValue
from ...registry import register_task
from ._lifecycle import RegionMapBoundObjective, run_region_map_lifecycle, semantic_axis_probabilities
from .shared.annotations import region_bbox_set_bundle
from .shared.defaults import fixed_scene_variant_probabilities
from .shared.sampling import construct_continent_threshold_dataset


TASK_ID = "task_charts__region_map__continent_threshold_region_count"
GREATER_THAN_QUERY_ID = "greater_than_continent_threshold_region_count"
LESS_THAN_QUERY_ID = "less_than_continent_threshold_region_count"
SUPPORTED_QUERY_IDS = (GREATER_THAN_QUERY_ID, LESS_THAN_QUERY_ID)
DEFAULT_QUERY_ID = GREATER_THAN_QUERY_ID
THRESHOLD_DIRECTION_BY_QUERY_ID = {GREATER_THAN_QUERY_ID: "greater_than", LESS_THAN_QUERY_ID: "less_than"}


@register_task
class ChartsMapContinentThresholdRegionCountTask:
    task_id = TASK_ID
    domain = "charts"
    objective_contract = "continent_threshold_region_count"
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def _construct_continent_threshold_dataset(self, instance_seed, params, selected_query_id, query_probabilities):
        dataset = construct_continent_threshold_dataset(
            threshold_direction=THRESHOLD_DIRECTION_BY_QUERY_ID[str(selected_query_id)],
            threshold_direction_probabilities=semantic_axis_probabilities(
                query_probabilities,
                THRESHOLD_DIRECTION_BY_QUERY_ID,
            ),
            params=params,
            instance_seed=instance_seed,
        )
        dataset["_scene_variant_probabilities"] = fixed_scene_variant_probabilities("geographic_region_map")
        return dataset

    def _bind_continent_threshold_objective(self, dataset, rendered, selected_query_id):
        annotation = region_bbox_set_bundle(rendered, dataset["annotation_region_ids"])
        return RegionMapBoundObjective(
            answer_gt=TypedValue(type="integer", value=int(dataset["answer_value"])),
            annotation=annotation,
            relations={
                "query_id": str(selected_query_id),
                "continent_label": str(dataset["question_params"]["continent_label"]),
                "threshold_direction": str(dataset["question_params"]["threshold_direction"]),
                "threshold_value": int(dataset["question_params"]["threshold_value"]),
                "annotation_region_count": int(len(annotation.annotation_region_ids)),
            },
            witness_symbolic={
                "type": "region_map_continent_threshold_count_witness",
                "candidate_region_ids": list(annotation.annotation_region_ids),
                "answer_value": int(dataset["answer_value"]),
            },
        )

    def generate(self, instance_seed, *, params, max_attempts):
        return run_region_map_lifecycle(
            task=self,
            instance_seed=instance_seed,
            params={**dict(params), "scene_variant": "geographic_region_map", "geographic_map_variant": "world_countries"},
            max_attempts=max_attempts,
            default_query_id=DEFAULT_QUERY_ID,
            prompt_query_key="continent_threshold_region_count",
            answer_type="integer",
            question_format="map_region_count",
            categorical=False,
            show_region_value_labels=False,
            build_dataset=self._construct_continent_threshold_dataset,
            bind_objective=self._bind_continent_threshold_objective,
        )
