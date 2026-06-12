"""Public task for `task_charts__candlestick__counterfactual_close_value`."""

from __future__ import annotations

from typing import Any

from trace.core.seed import hash64
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.charts.candlestick.shared.annotations import annotation_boxes_and_points
from trace.tasks.charts.candlestick.shared.defaults import (
    GENERATION_DEFAULTS,
    DOMAIN,
    SCENE_NAMESPACE,
    SCENE_ID,
)
from trace.tasks.charts.candlestick.shared.output import build_trace_scaffold
from trace.tasks.charts.candlestick.shared.prompts import build_prompt_artifacts
from trace.tasks.charts.candlestick.shared.rendering import render_dataset
from trace.tasks.charts.candlestick.shared.sampling import sample_candles, select_semantic_branch
from trace.tasks.charts.candlestick.shared.state import Dataset, Selection
from trace.tasks.registry import register_task
from trace.tasks.shared.annotation_artifacts import bbox_set_annotation_artifacts
from trace.tasks.shared.config_defaults import resolve_required_int_bounds
from trace.tasks.shared.deterministic_sampling import resolve_selection_index
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec


COUNTERFACTUAL_QUERY_ID = "close_after_body_change_value"


def _build_counterfactual_close_dataset(
    *,
    params: dict[str, Any],
    instance_seed: int,
    change_direction: str,
) -> Dataset:
    """Select the target candle and bind the counterfactual close objective."""

    candles = sample_candles(params, instance_seed=int(instance_seed))
    change_min, change_max = resolve_required_int_bounds(
        params,
        GENERATION_DEFAULTS,
        min_key="counterfactual_change_min",
        max_key="counterfactual_change_max",
        fallback_min=2,
        fallback_max=6,
        context="candlestick counterfactual body-size change",
    )
    increase = str(change_direction) == "increase"
    if str(change_direction) not in {"increase", "decrease"}:
        raise ValueError(f"unsupported body-size change direction: {change_direction}")
    index_seed = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.counterfactual.target",
    )
    candidates = list(candles)
    start_index = int(index_seed) % len(candidates)
    candidates = candidates[start_index:] + candidates[:start_index]
    for candidate in candidates:
        current_body = int(candidate.body_size)
        if increase:
            max_change = min(int(change_max), 96 - max(int(candidate.open_value), int(candidate.close_value)))
        else:
            max_change = min(int(change_max), int(current_body) - 1)
        if int(max_change) < int(change_min):
            continue
        change = int(change_min) + int(index_seed % (int(max_change) - int(change_min) + 1))
        new_body = int(current_body) + int(change) if increase else int(current_body) - int(change)
        answer = (
            int(candidate.open_value) + int(new_body)
            if str(candidate.direction) == "up"
            else int(candidate.open_value) - int(new_body)
        )
        if 1 <= int(answer) <= 99:
            selection = Selection(
                answer=int(answer),
                answer_type="integer",
                annotation_candle_ids=(str(candidate.candle_id),),
                annotation_label_ids=(
                    f"x_label:{candidate.candle_id}",
                    f"{candidate.candle_id}:open",
                    f"{candidate.candle_id}:close",
                ),
                annotation_roles=("target_body",),
                trace={
                    "target_candle_id": str(candidate.candle_id),
                    "target_label": str(candidate.label),
                    "target_direction": str(candidate.direction),
                    "change_value": int(change),
                    "change_direction": str(change_direction),
                    "change_phrase": "increased" if increase else "decreased",
                    "change_verb": "increase" if increase else "decrease",
                    "change_past_phrase": "increased" if increase else "decreased",
                    "current_body_size": int(current_body),
                    "new_body_size": int(new_body),
                    "candle_count": int(len(candles)),
                },
            )
            return Dataset(candles=tuple(candles), selection=selection)
    raise ValueError("no feasible counterfactual close target")


@register_task
class ChartsCandlestickCounterfactualCloseValueTask:
    """Compute a counterfactual close after changing one candle body size."""

    task_id = "task_charts__candlestick__counterfactual_close_value"
    domain = DOMAIN
    objective_contract = "counterfactual_close_value"
    supported_query_ids = (COUNTERFACTUAL_QUERY_ID,)
    default_dataset_enabled = True

    def _generate_once(self, instance_seed: int, *, params: dict[str, Any], selected_query_id: str) -> TaskOutput:
        """Generate one counterfactual-close instance with task-owned answer binding."""

        change_direction, direction_probabilities, branch_params = select_semantic_branch(
            params,
            branch_key="change_direction",
            support=("increase", "decrease"),
            instance_seed=int(instance_seed),
            namespace="charts.candlestick.change_direction",
        )
        dataset = _build_counterfactual_close_dataset(
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
