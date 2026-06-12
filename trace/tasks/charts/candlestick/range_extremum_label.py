"""Public task for `task_charts__candlestick__range_extremum_label`."""

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
    range_extremum_dataset,
    render_dataset,
)
from trace.tasks.charts.candlestick.shared.prompts import build_prompt_artifacts
from trace.tasks.registry import register_task
from trace.tasks.shared.annotation_artifacts import point_set_annotation_artifacts
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec


WICK_QUERY_ID = "wick_range_extremum_label"
BODY_QUERY_ID = "body_range_extremum_label"


def _range_kind(selected_query_id: str) -> str:
    if str(selected_query_id) == WICK_QUERY_ID:
        return "wick"
    if str(selected_query_id) == BODY_QUERY_ID:
        return "body"
    raise ValueError(f"unsupported candlestick range query: {selected_query_id}")


def _select_extremum(params: dict[str, Any], *, instance_seed: int) -> tuple[str, dict[str, float], dict[str, Any]]:
    support = ("largest", "smallest")
    requested = params.get("extremum")
    if requested is not None:
        selected = str(requested)
        if selected not in support:
            raise ValueError(f"unsupported extremum: {selected}; supported: {support}")
        branch_params = dict(params)
        branch_params.pop("extremum", None)
        return selected, {value: (1.0 if value == selected else 0.0) for value in support}, branch_params
    sample_cursor = params.get("_sample_cursor")
    if sample_cursor is not None:
        cursor = abs(int(sample_cursor))
        selected = support[cursor % len(support)]
        branch_params = dict(params)
        branch_params["_sample_cursor"] = cursor // len(support)
        return selected, {value: 0.5 for value in support}, branch_params
    selected = support[int(hash64(int(instance_seed), "charts.candlestick.extremum")) % len(support)]
    return selected, {value: 0.5 for value in support}, dict(params)


@register_task
class ChartsCandlestickRangeExtremumLabelTask:
    """Return the period label with an extremal wick or body range."""

    task_id = "task_charts__candlestick__range_extremum_label"
    domain = DOMAIN
    scene_id = SCENE_ID
    objective_contract = "range_extremum_label"
    supported_query_ids = (WICK_QUERY_ID, BODY_QUERY_ID)
    default_dataset_enabled = True

    def _generate_once(self, instance_seed: int, *, params: dict[str, Any], selected_query_id: str) -> TaskOutput:
        extremum, extremum_probabilities, branch_params = _select_extremum(
            params,
            instance_seed=int(instance_seed),
        )
        dataset = range_extremum_dataset(
            params=branch_params,
            instance_seed=int(instance_seed),
            range_kind=_range_kind(str(selected_query_id)),
            extremum=str(extremum),
        )
        artifacts = render_dataset(dataset=dataset, params=branch_params, instance_seed=int(instance_seed))
        _boxes, annotation_points = annotation_boxes_and_points(
            rendered=artifacts.rendered,
            selection=dataset.selection,
        )
        annotation = point_set_annotation_artifacts(annotation_points)
        prompt_artifacts = build_prompt_artifacts(
            prompt_query_key=str(selected_query_id),
            dynamic_slots={
                "range_kind_phrase": str(dataset.selection.trace["range_kind_phrase"]),
                "extremum_phrase": str(dataset.selection.trace["extremum_phrase"]),
            },
            instance_seed=int(instance_seed),
        )
        answer_value = str(dataset.selection.answer)
        relations: dict[str, Any] = {
            **dict(dataset.selection.trace),
            "answer": answer_value,
            "annotation_candle_ids": list(dataset.selection.annotation_candle_ids),
            "support_label_ids": list(dataset.selection.annotation_label_ids),
            "annotation_roles": list(dataset.selection.annotation_roles),
            "extremum_probabilities": dict(extremum_probabilities),
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
                "answer": answer_value,
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
            answer_gt=TypedValue(type="string", value=answer_value),
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
            default_query_id=WICK_QUERY_ID,
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


__all__ = ["ChartsCandlestickRangeExtremumLabelTask"]
