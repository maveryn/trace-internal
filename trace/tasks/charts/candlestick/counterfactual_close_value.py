"""Public task for `task_charts__candlestick__counterfactual_close_value`."""

from __future__ import annotations

from typing import Any

from trace.core.seed import hash64
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.charts.candlestick.shared.ohlc import (
    DOMAIN,
    SCENE_ID,
    annotation_boxes_and_points,
    build_trace_scaffold,
    counterfactual_close_dataset,
    render_dataset,
)
from trace.tasks.charts.candlestick.shared.prompts import build_prompt_artifacts
from trace.tasks.registry import register_task
from trace.tasks.shared.annotation_artifacts import bbox_set_annotation_artifacts
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec


COUNTERFACTUAL_QUERY_ID = "close_after_body_change_value"


def _select_change_direction(params: dict[str, Any], *, instance_seed: int) -> tuple[str, dict[str, float], dict[str, Any]]:
    support = ("increase", "decrease")
    requested = params.get("change_direction")
    if requested is not None:
        selected = str(requested)
        if selected not in support:
            raise ValueError(f"unsupported change_direction: {selected}; supported: {support}")
        branch_params = dict(params)
        branch_params.pop("change_direction", None)
        return selected, {value: (1.0 if value == selected else 0.0) for value in support}, branch_params
    sample_cursor = params.get("_sample_cursor")
    if sample_cursor is not None:
        cursor = abs(int(sample_cursor))
        selected = support[cursor % len(support)]
        branch_params = dict(params)
        branch_params["_sample_cursor"] = cursor // len(support)
        return selected, {value: 0.5 for value in support}, branch_params
    selected = support[int(hash64(int(instance_seed), "charts.candlestick.change_direction")) % len(support)]
    return selected, {value: 0.5 for value in support}, dict(params)


@register_task
class ChartsCandlestickCounterfactualCloseValueTask:
    """Compute a counterfactual close after changing one candle body size."""

    task_id = "task_charts__candlestick__counterfactual_close_value"
    domain = DOMAIN
    scene_id = SCENE_ID
    objective_contract = "counterfactual_close_value"
    supported_query_ids = (COUNTERFACTUAL_QUERY_ID,)
    default_dataset_enabled = True

    def _generate_once(self, instance_seed: int, *, params: dict[str, Any], selected_query_id: str) -> TaskOutput:
        change_direction, direction_probabilities, branch_params = _select_change_direction(
            params,
            instance_seed=int(instance_seed),
        )
        dataset = counterfactual_close_dataset(
            params=branch_params,
            instance_seed=int(instance_seed),
            change_direction=str(change_direction),
        )
        artifacts = render_dataset(dataset=dataset, params=branch_params, instance_seed=int(instance_seed))
        annotation_boxes, _points = annotation_boxes_and_points(
            rendered=artifacts.rendered,
            selection=dataset.selection,
        )
        annotation = bbox_set_annotation_artifacts(annotation_boxes)
        prompt_artifacts = build_prompt_artifacts(
            prompt_query_key=str(selected_query_id),
            dynamic_slots={
                "target_label": f'"{dataset.selection.trace["target_label"]}"',
                "change_verb": str(dataset.selection.trace["change_verb"]),
                "change_past_phrase": str(dataset.selection.trace["change_past_phrase"]),
                "change_value": str(dataset.selection.trace["change_value"]),
            },
            instance_seed=int(instance_seed),
        )
        answer_value = int(dataset.selection.answer)
        relations: dict[str, Any] = {
            **dict(dataset.selection.trace),
            "answer": int(answer_value),
            "annotation_candle_ids": list(dataset.selection.annotation_candle_ids),
            "support_label_ids": list(dataset.selection.annotation_label_ids),
            "annotation_roles": list(dataset.selection.annotation_roles),
            "change_direction_probabilities": dict(direction_probabilities),
        }
        trace_payload = build_trace_scaffold(
            dataset=dataset,
            artifacts=artifacts,
            relations=relations,
            witness_symbolic={
                "type": "candlestick_ohlc_witness",
                "candle_ids": list(dataset.selection.annotation_candle_ids),
                "roles": list(dataset.selection.annotation_roles),
                "support_label_ids": list(dataset.selection.annotation_label_ids),
                "answer": int(answer_value),
            },
            projected_annotation={
                **annotation.projected_annotation,
                "candle_ids": list(dataset.selection.annotation_candle_ids),
                "roles": list(dataset.selection.annotation_roles),
            },
        )
        trace_payload["scene_ir"]["relations"]["query_id"] = str(selected_query_id)
        trace_payload["query_spec"] = build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(selected_query_id),
            params={"query_id": str(selected_query_id), **relations},
        )
        trace_payload["execution_trace"]["query_id"] = str(selected_query_id)
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(answer_value)),
            annotation_gt=annotation.annotation_gt,
            image=artifacts.rendered.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(selected_query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query_id, _probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=self.supported_query_ids,
            default_query_id=COUNTERFACTUAL_QUERY_ID,
            task_id=self.task_id,
        )
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            attempt_seed = (
                int(instance_seed)
                if attempt == 0
                else int(hash64(int(instance_seed), "charts.candlestick.retry", int(attempt)))
            )
            try:
                return self._generate_once(
                    int(attempt_seed),
                    params=task_params,
                    selected_query_id=str(selected_query_id),
                )
            except ValueError as exc:
                last_error = exc
        raise RuntimeError(f"failed to generate {self.task_id}: {last_error}")


__all__ = ["ChartsCandlestickCounterfactualCloseValueTask"]
