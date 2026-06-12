"""Violin task for `task_charts__violin__support_width_extremum_label`."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from ....core.seed import hash64
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.fixed_query import select_task_query_id
from ...shared.output_metadata import default_task_versions
from ..shared.distribution_chart_common import build_density_dataset_for_variant
from .shared.violin_label import (
    BASE_CONFIG_ID,
    DISTRIBUTION_DEFAULTS,
    GEN_DEFAULTS,
    SCENE_ID,
    SCENE_VARIANT,
    annotation_bboxes_for_label,
    build_violin_prompt,
    build_violin_render_artifacts,
    label_centers,
    normalize_support_trace,
    render_spec_from_artifacts,
    resolve_violin_mark_style,
)


TASK_ID = "task_charts__violin__support_width_extremum_label"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = ("widest_support", "narrowest_support")
DEFAULT_QUERY_ID = "widest_support"
REASONING_LOAD_BY_QUERY: Dict[str, float] = {
    "widest_support": 0.60,
    "narrowest_support": 0.60,
}


def _support_answer(query_id: str, support_by_label: Mapping[str, Mapping[str, Any]]) -> tuple[str, list[int]]:
    span_by_label = {
        str(label): int(values["support_span"])
        for label, values in support_by_label.items()
    }
    if str(query_id) == "widest_support":
        target_span = max(span_by_label.values())
    elif str(query_id) == "narrowest_support":
        target_span = min(span_by_label.values())
    else:
        raise ValueError(f"unsupported violin support query: {query_id}")
    winners = [label for label, span in span_by_label.items() if int(span) == int(target_span)]
    if len(winners) != 1:
        raise ValueError("violin support-width extremum answer is not unique")
    winner = str(winners[0])
    values = support_by_label[winner]
    return winner, [int(values["support_min"]), int(values["support_max"])]


def _build_trace_payload(
    *,
    query_id: str,
    query_probabilities: Mapping[str, float],
    prompt_artifacts: Any,
    artifacts: Any,
    support_by_label: Mapping[str, Mapping[str, Any]],
    trace_extras: Mapping[str, Any],
    answer_label: str,
    annotation_values: list[int],
    annotation_bboxes: list[list[float]],
) -> Dict[str, Any]:
    rendered_scene = artifacts.rendered_scene
    mode_values_by_label = {
        str(label): [int(value) for value in values["mode_values"]]
        for label, values in support_by_label.items()
    }
    support_span_by_label = {
        str(label): int(values["support_span"])
        for label, values in support_by_label.items()
    }
    return {
        "scene_ir": {
            "scene_kind": "chart_violin_distribution",
            "entities": [dict(entity) for entity in rendered_scene.entities],
            "relations": {
                "query_id": str(query_id),
                "scene_variant": SCENE_VARIANT,
                "answer_label": str(answer_label),
                "annotation_label": str(answer_label),
                "annotation_values": [int(value) for value in annotation_values],
                "generation_profile": str(trace_extras.get("generation_profile", "")),
            },
        },
        "query_spec": {
            "query_id": str(query_id),
            "template_id": str(prompt_artifacts.prompt_variant.get("bundle_id", "")),
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": {
                "query_id": str(query_id),
                "scene_variant": SCENE_VARIANT,
                "query_id_probabilities": dict(query_probabilities),
                "category_count": int(trace_extras["category_count"]),
                "category_count_range": list(trace_extras["category_count_range"]),
                "value_range": list(trace_extras["value_range"]),
                "answer_label": str(answer_label),
                "annotation_values": [int(value) for value in annotation_values],
                "generation_profile": str(trace_extras.get("generation_profile", "")),
            },
        },
        "render_spec": render_spec_from_artifacts(artifacts),
        "render_map": {
            "image_id": "img0",
            "plot_bbox_px": list(rendered_scene.plot_bbox_px),
            "label_centers_px": label_centers(rendered_scene),
        },
        "execution_trace": {
            "query_id": str(query_id),
            "scene_variant": SCENE_VARIANT,
            "answer_label": str(answer_label),
            "annotation_label": str(answer_label),
            "annotation_values": [int(value) for value in annotation_values],
            "labels": [str(mark["label"]) for mark in rendered_scene.mark_traces],
            "mode_values_by_label": dict(mode_values_by_label),
            "support_span_by_label": dict(support_span_by_label),
            "support_by_label": dict(support_by_label),
            "category_count": int(trace_extras["category_count"]),
            "category_count_range": list(trace_extras["category_count_range"]),
            "value_range": list(trace_extras["value_range"]),
            "query_id_probabilities": dict(query_probabilities),
            "question_format": "label_open",
            "mark_color_sampling_policy": str(artifacts.mark_style["sampling_policy"]),
            "mark_fill_rgb": list(artifacts.mark_style["mark_fill_rgb"]),
            "mark_outline_rgb": list(artifacts.mark_style["mark_outline_rgb"]),
        },
        "witness_symbolic": {
            "type": "object_set",
            "value": [str(answer_label)],
        },
        "projected_annotation": {
            "type": "bbox_set",
            "bbox_set": list(annotation_bboxes),
        },
    }


@register_task
class ChartsDistributionViolinSupportWidthExtremumLabelTask:
    """Return the violin label with the widest or narrowest support."""

    task_id = TASK_ID
    domain = "charts"
    scene_id = SCENE_ID
    objective_contract = "support_width_extremum_label"
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query_id, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=dict(params),
            supported_query_ids=self.supported_query_ids,
            default_query_id=DEFAULT_QUERY_ID,
            task_id=self.task_id,
        )
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_seed = int(instance_seed) if attempt_index == 0 else int(hash64(int(instance_seed), self.task_id, attempt_index))
            try:
                mark_style = resolve_violin_mark_style(task_params, instance_seed=int(attempt_seed))
                violins, _, _, trace_extras = build_density_dataset_for_variant(
                    query_id=str(selected_query_id),
                    params=task_params,
                    instance_seed=int(attempt_seed),
                    gen_defaults=GEN_DEFAULTS,
                    defaults=DISTRIBUTION_DEFAULTS,
                    task_id=BASE_CONFIG_ID,
                    mark_style=mark_style,
                )
                support_by_label = normalize_support_trace(trace_extras)
                answer_label, annotation_values = _support_answer(str(selected_query_id), support_by_label)
                artifacts = build_violin_render_artifacts(
                    violins=violins,
                    params=task_params,
                    instance_seed=int(attempt_seed),
                    mark_style=mark_style,
                )
                prompt_artifacts = build_violin_prompt(
                    prompt_query_key=str(selected_query_id),
                    instance_seed=int(attempt_seed),
                )
                annotation_bboxes = annotation_bboxes_for_label(artifacts.rendered_scene, str(answer_label))
                return TaskOutput(
                    prompt=str(prompt_artifacts.prompt),
                    answer_gt=TypedValue(type="string", value=str(answer_label)),
                    annotation_gt=TypedValue(type="bbox_set", value=list(annotation_bboxes)),
                    image=artifacts.image,
                    image_id="img0",
                    trace_payload=_build_trace_payload(
                        query_id=str(selected_query_id),
                        query_probabilities=query_probabilities,
                        prompt_artifacts=prompt_artifacts,
                        artifacts=artifacts,
                        support_by_label=support_by_label,
                        trace_extras=trace_extras,
                        answer_label=str(answer_label),
                        annotation_values=list(annotation_values),
                        annotation_bboxes=list(annotation_bboxes),
                    ),
                    task_versions=default_task_versions(),
                    query_id=str(selected_query_id),
                    scene_id=SCENE_ID,
                    prompt_variants=dict(prompt_artifacts.prompt_variants),
                )
            except Exception as exc:
                last_error = exc
        raise RuntimeError(f"failed to generate {self.task_id}: {last_error}")


__all__ = ["ChartsDistributionViolinSupportWidthExtremumLabelTask"]
