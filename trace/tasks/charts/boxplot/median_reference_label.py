"""Public task for `task_charts__boxplot__median_reference_label`."""

from __future__ import annotations

from typing import Any

from trace.core.seed import hash64
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.charts.boxplot.shared.annotations import keyed_point_artifacts
from trace.tasks.charts.boxplot.shared.branches import choose_branch
from trace.tasks.charts.boxplot.shared.defaults import (
    BOXPLOT_DEFAULTS,
    DOMAIN,
    GENERATION_DEFAULTS,
    SCENE_ID,
    merge_task_defaults,
)
from trace.tasks.charts.boxplot.shared.prompts import (
    SINGLE_SCENE_PROMPT_KEY,
    build_prompt_artifacts,
)
from trace.tasks.charts.boxplot.shared.rendering import (
    build_trace_scaffold,
    point_map_for_labels,
    render_single_boxplot_scene,
    resolve_mark_style,
)
from trace.tasks.charts.shared.distribution_chart_common import build_boxplot_dataset_for_variant
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import DEFAULT_QUERY_ID, select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec


DIRECTION_BRANCHES = ("above_reference_q3", "below_reference_q1")


def _construction_variant(direction: str) -> str:
    if str(direction) == "above_reference_q3":
        return "median_above_reference_q3"
    if str(direction) == "below_reference_q1":
        return "median_below_reference_q1"
    raise ValueError(f"unsupported median reference direction: {direction}")


def _prompt_slots(direction: str, reference_label: str) -> dict[str, str]:
    if str(direction) == "above_reference_q3":
        return {
            "reference_label": f'"{reference_label}"',
            "median_reference_direction_word": "above",
            "reference_quartile_name": "upper quartile",
            "median_reference_gap_phrase": "between its median and the reference upper quartile",
        }
    if str(direction) == "below_reference_q1":
        return {
            "reference_label": f'"{reference_label}"',
            "median_reference_direction_word": "below",
            "reference_quartile_name": "lower quartile",
            "median_reference_gap_phrase": "between the reference lower quartile and its median",
        }
    raise ValueError(f"unsupported median reference direction: {direction}")


@register_task
class ChartsDistributionBoxplotMedianReferenceLabelTask:
    """Select the boxplot whose median is farthest from a reference quartile."""

    task_id = "task_charts__boxplot__median_reference_label"
    domain = DOMAIN
    scene_id = SCENE_ID
    objective_contract = "median_reference_label"
    supported_query_ids = (DEFAULT_QUERY_ID,)
    default_dataset_enabled = True

    def _generate_once(self, instance_seed: int, *, params: dict[str, Any], selected_query_id: str) -> TaskOutput:
        direction, direction_probabilities, branch_params = choose_branch(
            params=params,
            branch_key="median_reference_direction",
            support=DIRECTION_BRANCHES,
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.median_reference_direction",
        )
        effective_params = merge_task_defaults(branch_params, {})
        mark_style = resolve_mark_style(effective_params, instance_seed=int(instance_seed), mark_count=1)
        boxplots, answer_label, annotation_value, trace_extras = build_boxplot_dataset_for_variant(
            query_id=_construction_variant(str(direction)),
            params=effective_params,
            instance_seed=int(instance_seed),
            gen_defaults=GENERATION_DEFAULTS,
            defaults=BOXPLOT_DEFAULTS,
            task_id=self.task_id,
            mark_style=mark_style,
        )
        artifacts = render_single_boxplot_scene(
            boxplots=boxplots,
            params=effective_params,
            mark_style=mark_style,
            instance_seed=int(instance_seed),
        )
        reference_label = str(trace_extras["reference_label"])
        role_to_label = {
            "reference_boxplot": reference_label,
            "answer_boxplot": str(answer_label),
        }
        label_to_point = point_map_for_labels(artifacts.rendered_scene, role_to_label.values())
        role_to_point = {
            str(role): label_to_point[str(label)]
            for role, label in role_to_label.items()
        }
        annotation, witness_symbolic = keyed_point_artifacts(role_to_point, role_to_label)
        prompt_artifacts = build_prompt_artifacts(
            scene_key=SINGLE_SCENE_PROMPT_KEY,
            prompt_query_key=self.objective_contract,
            dynamic_slots=_prompt_slots(str(direction), reference_label),
            instance_seed=int(instance_seed),
        )
        relations: dict[str, Any] = {
            **dict(trace_extras),
            "answer_label": str(answer_label),
            "annotation_value": int(annotation_value),
            "median_reference_direction": str(direction),
            "median_reference_direction_probabilities": dict(direction_probabilities),
        }
        trace_payload = build_trace_scaffold(
            artifacts=artifacts,
            relations=relations,
            question_format="label_open",
            witness_symbolic=witness_symbolic,
            projected_annotation=annotation.projected_annotation,
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
            answer_gt=TypedValue(type="string", value=str(answer_label)),
            annotation_gt=annotation.annotation_gt,
            image=artifacts.rendered_scene.image,
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
            default_query_id=DEFAULT_QUERY_ID,
            task_id=self.task_id,
        )
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            attempt_seed = (
                int(instance_seed)
                if attempt == 0
                else int(hash64(int(instance_seed), "charts.boxplot.retry", int(attempt)))
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


__all__ = ["ChartsDistributionBoxplotMedianReferenceLabelTask"]
