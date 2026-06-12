"""Public task for `task_charts__histogram__bin_count_between_values`."""

from __future__ import annotations

from typing import Any

from trace.core.seed import hash64
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.charts.histogram.shared.histogram_count import build_histogram_task_parts
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions


SCENE_ID = "histogram"
QUERY_IDS = ("bin_count_between_values",)
DEFAULT_QUERY_ID = "bin_count_between_values"


@register_task
class ChartsDistributionHistogramBinCountBetweenValuesTask:
    """Return the number of bins whose x-axis values fall inside an interval."""

    task_id = "task_charts__histogram__bin_count_between_values"
    domain = "charts"
    scene_id = SCENE_ID
    objective_contract = "bin_count_between_values"
    supported_query_ids = QUERY_IDS
    default_dataset_enabled = True

    def _generate_once(
        self,
        instance_seed: int,
        *,
        params: dict[str, Any],
        selected_query_id: str,
        query_probabilities: dict[str, float],
    ) -> TaskOutput:
        parts = build_histogram_task_parts(
            public_task_id=self.task_id,
            scene_id=SCENE_ID,
            selected_prompt_key=str(selected_query_id),
            prompt_key_probabilities=query_probabilities,
            params=params,
            instance_seed=int(instance_seed),
        )
        trace_payload = dict(parts["trace_payload"])
        trace_payload["scene_ir"]["relations"]["query_id"] = str(selected_query_id)
        trace_payload["query_spec"]["query_id"] = str(selected_query_id)
        trace_payload["query_spec"]["params"]["query_id"] = str(selected_query_id)
        trace_payload["query_spec"]["params"]["query_id_probabilities"] = dict(query_probabilities)
        trace_payload["execution_trace"]["query_id"] = str(selected_query_id)
        trace_payload["execution_trace"]["query_id_probabilities"] = dict(query_probabilities)
        return TaskOutput(
            prompt=str(parts["prompt"]),
            answer_gt=TypedValue(type=str(parts["answer_type"]), value=int(parts["answer_value"])),
            annotation_gt=TypedValue(type=str(parts["annotation_type"]), value=list(parts["annotation_value"])),
            image=parts["image"],
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(parts["prompt_key"]),
            prompt_variants=dict(parts["prompt_variants"]),
        )

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query_id, probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=self.supported_query_ids,
            default_query_id=DEFAULT_QUERY_ID,
            task_id=self.task_id,
        )
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_seed = int(instance_seed) if attempt_index == 0 else int(hash64(int(instance_seed), self.task_id, int(attempt_index)))
            try:
                return self._generate_once(
                    int(attempt_seed),
                    params=task_params,
                    selected_query_id=str(selected_query_id),
                    query_probabilities=dict(probabilities),
                )
            except Exception as exc:
                last_error = exc
        raise RuntimeError(f"failed to generate {self.task_id}: {last_error}") from last_error


__all__ = ["ChartsDistributionHistogramBinCountBetweenValuesTask"]
