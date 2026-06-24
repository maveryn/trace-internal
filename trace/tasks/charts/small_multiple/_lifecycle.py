"""Private materialization lifecycle for small-multiple chart tasks."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from trace.core.seed import hash64
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.charts.shared.visual_defaults import chart_font_asset_metadata, sample_chart_font_family
from trace.tasks.charts.small_multiple.shared.annotations import (
    point_map_for_roles,
    point_map_payload,
    roles_for_panel_segments,
)
from trace.tasks.charts.small_multiple.shared.defaults import SCENE_VARIANT_LOADS
from trace.tasks.charts.small_multiple.shared.prompts import prompt_slots, render_prompt_artifacts
from trace.tasks.charts.small_multiple.shared.rendering import panel_trace_payload, render_small_multiples
from trace.tasks.charts.small_multiple.shared.sampling import counts_for_panel, segment_counts_for_panels
from trace.tasks.charts.small_multiple.shared.state import (
    PanelSpec,
    SCENE_ID,
    SmallMultipleDataset,
    SmallMultipleSelection,
)
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec
from trace.tasks.shared.text_rendering import temporary_default_font_family


@dataclass(frozen=True)
class SmallMultipleObjectivePlan:
    """Task-owned plan; lifecycle only renders and packages this fixed contract."""

    dataset: SmallMultipleDataset
    selection: SmallMultipleSelection
    params: Mapping[str, Any]
    scene_variant: str
    scene_variant_probabilities: Mapping[str, float]
    prompt_key: str
    annotation_hint_template: str
    json_example: str
    json_example_answer_only: str
    program_code: str
    reasoning_load: float


PlanBuilder = Callable[[Mapping[str, Any], int, str, Mapping[str, float]], SmallMultipleObjectivePlan]


def package_small_multiple_plan(
    *,
    dataset: SmallMultipleDataset,
    selection: SmallMultipleSelection,
    params: Mapping[str, Any],
    scene_variant: str,
    scene_variant_probabilities: Mapping[str, float],
    prompt_key: str,
    annotation_hint_template: str,
    json_example: str,
    json_example_answer_only: str,
    program_code: str,
    reasoning_load: float,
) -> SmallMultipleObjectivePlan:
    return SmallMultipleObjectivePlan(
        dataset=dataset,
        selection=selection,
        params=dict(params),
        scene_variant=str(scene_variant),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        prompt_key=str(prompt_key),
        annotation_hint_template=str(annotation_hint_template),
        json_example=str(json_example),
        json_example_answer_only=str(json_example_answer_only),
        program_code=str(program_code),
        reasoning_load=float(reasoning_load),
    )


def package_panel_segment_sum_selection(
    *,
    selected_panels: tuple[PanelSpec, ...],
    target_segment: str,
    role_segments: tuple[tuple[str, str], ...],
    include_total: bool,
    trace: Mapping[str, Any],
) -> SmallMultipleSelection:
    counts = segment_counts_for_panels(selected_panels, str(target_segment))
    trace_payload = dict(trace)
    trace_payload.setdefault("selected_target_counts", [int(value) for value in counts])
    return SmallMultipleSelection(
        answer_value=int(sum(counts)),
        annotation_values=tuple(int(value) for value in counts),
        annotation_roles=roles_for_panel_segments(
            selected_panels,
            role_segments,
            include_total=bool(include_total),
        ),
        question_format="numeric_open",
        trace=dict(trace_payload),
    )


def run_small_multiple_lifecycle(
    *,
    task: Any,
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
    default_query_id: str,
    build_plan: PlanBuilder,
) -> TaskOutput:
    """Render and package a task-owned small-multiple plan.

    Key invariant: this lifecycle never chooses the public objective. The task
    file supplies the sampled objective plan, annotation roles, prompt key, and
    program code; this function only applies shared rendering/projection/output
    plumbing.
    """

    selected_query_id, query_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=dict(params),
        supported_query_ids=tuple(task.supported_query_ids),
        default_query_id=str(default_query_id),
        task_id=str(task.task_id),
    )

    last_error: Exception | None = None
    for attempt_index in range(max(1, int(max_attempts))):
        attempt_seed = int(instance_seed) if attempt_index == 0 else int(hash64(int(instance_seed), str(task.task_id), attempt_index))
        attempt_params = {**dict(task_params), "_attempt_index": int(attempt_index)}
        try:
            plan = build_plan(dict(attempt_params), int(attempt_seed), str(selected_query_id), dict(query_probabilities))
            chart_font_family = sample_chart_font_family(
                instance_seed=int(attempt_seed),
                namespace=f"{task.task_id}.chart_font",
                params=attempt_params,
            )
            with temporary_default_font_family(str(chart_font_family)):
                rendered = render_small_multiples(
                    plan.dataset,
                    scene_variant=str(plan.scene_variant),
                    params=attempt_params,
                    instance_seed=int(attempt_seed),
                )

            annotation_points = point_map_for_roles(rendered, plan.selection.annotation_roles)
            projected_annotation = point_map_payload(annotation_points)
            prompt_artifacts = render_prompt_artifacts(
                prompt_key=str(plan.prompt_key),
                dynamic_slot_values=prompt_slots(
                    prompt_key=str(plan.prompt_key),
                    scene_variant=str(plan.scene_variant),
                    dataset=plan.dataset,
                    selection=plan.selection,
                    annotation_points=annotation_points,
                    annotation_hint_template=str(plan.annotation_hint_template),
                    json_example=str(plan.json_example),
                    json_example_answer_only=str(plan.json_example_answer_only),
                ),
                instance_seed=int(attempt_seed),
            )

            panels_trace = panel_trace_payload(plan.dataset)
            selection_trace = dict(plan.selection.trace)
            dataset_trace = dict(plan.dataset.trace)
            query_params = {
                "query_id": str(selected_query_id),
                "scene_variant": str(plan.scene_variant),
                "query_id_probabilities": dict(query_probabilities),
                "scene_variant_probabilities": dict(plan.scene_variant_probabilities),
                "panel_count": int(dataset_trace["panel_count"]),
                "segment_count": int(dataset_trace["segment_count"]),
                "question_format": str(plan.selection.question_format),
                "program_code": str(plan.program_code),
                **{
                    str(key): value
                    for key, value in selection_trace.items()
                    if str(key)
                    in {
                        "rank_segment",
                        "target_segment",
                        "condition_segment",
                        "threshold",
                        "top_k",
                        "bottom_k",
                        "start_panel",
                        "end_panel",
                    }
                },
            }
            prompt_query_spec = build_prompt_query_spec(
                prompt_artifacts=prompt_artifacts,
                query_id=str(selected_query_id),
                params=query_params,
            )
            annotation_roles_trace = [
                {
                    "role": str(role.role),
                    "panel": str(role.panel),
                    **({} if role.segment is None else {"segment": str(role.segment)}),
                }
                for role in plan.selection.annotation_roles
            ]
            trace_payload = {
                "scene_ir": {
                    "scene_kind": f"chart_{str(plan.scene_variant)}_composition_small_multiples",
                    "entities": [dict(entity) for entity in rendered.entities],
                    "relations": {
                        "query_id": str(selected_query_id),
                        "scene_variant": str(plan.scene_variant),
                        "segment_labels": [str(label) for label in plan.dataset.segment_labels],
                    },
                },
                "query_spec": prompt_query_spec,
                "render_spec": {
                    "canvas_width": int(rendered.image.size[0]),
                    "canvas_height": int(rendered.image.size[1]),
                    "coord_space": "pixel",
                    "scene_variant": str(plan.scene_variant),
                    "font_assets": chart_font_asset_metadata(str(chart_font_family)),
                    "layout_jitter": dict(rendered.layout_jitter_meta),
                    "plot_bbox_px": list(rendered.plot_bbox_px),
                    **dict(rendered.render_meta),
                },
                "render_map": {
                    "image_id": "img0",
                    "plot_bbox_px": list(rendered.plot_bbox_px),
                    "legend_bbox_px": list(rendered.legend_bbox_px),
                    "legend_item_bboxes_px": {
                        str(segment): list(bbox)
                        for segment, bbox in rendered.legend_item_bboxes_px.items()
                    },
                    "context_protected_bboxes_px": {
                        "plot": list(rendered.plot_bbox_px),
                        **({"legend": list(rendered.legend_bbox_px)} if rendered.legend_bbox_px else {}),
                    },
                    "panel_traces": [dict(panel) for panel in rendered.panel_traces],
                    "annotation_bbox_by_key": {
                        f"{panel}:{segment}": list(bbox)
                        for (panel, segment), bbox in rendered.annotation_bbox_by_key.items()
                    },
                    "total_bbox_by_panel": {
                        str(panel): list(bbox)
                        for panel, bbox in rendered.total_bbox_by_panel.items()
                    },
                },
                "execution_trace": {
                    "query_id": str(selected_query_id),
                    "scene_variant": str(plan.scene_variant),
                    "answer_value": int(plan.selection.answer_value),
                    "annotation_values": [int(value) for value in plan.selection.annotation_values],
                    "annotation_roles": list(annotation_roles_trace),
                    "annotation_point_keys": list(annotation_points.keys()),
                    "segment_labels": [str(label) for label in plan.dataset.segment_labels],
                    "panels": panels_trace,
                    "question_format": str(plan.selection.question_format),
                    "query_id_probabilities": dict(query_probabilities),
                    "scene_variant_probabilities": dict(plan.scene_variant_probabilities),
                    "program_code": str(plan.program_code),
                    "reasoning_load": float(plan.reasoning_load)
                    + float(SCENE_VARIANT_LOADS.get(str(plan.scene_variant), 0.0)),
                    **dict(dataset_trace),
                    **dict(selection_trace),
                },
                "witness_symbolic": {
                    "type": "small_multiple_aggregate",
                    "query_id": str(selected_query_id),
                    "answer_value": int(plan.selection.answer_value),
                    "annotation_values": [int(value) for value in plan.selection.annotation_values],
                    "annotation_point_keys": list(annotation_points.keys()),
                    "calculation": dict(selection_trace),
                },
                "projected_annotation": dict(projected_annotation),
            }
            return TaskOutput(
                prompt=str(prompt_artifacts.prompt),
                prompt_variants=dict(prompt_artifacts.prompt_variants),
                answer_gt=TypedValue(type="integer", value=int(plan.selection.answer_value)),
                annotation_gt=TypedValue(type="point_map", value=dict(annotation_points)),
                image=rendered.image,
                image_id="img0",
                trace_payload=trace_payload,
                task_versions=default_task_versions(),
                scene_id=SCENE_ID,
                query_id=str(selected_query_id),
            )
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"failed to generate {task.task_id}: {last_error}") from last_error


def counts_by_panel_label(dataset: SmallMultipleDataset) -> dict[str, dict[str, int]]:
    return {str(panel.label): counts_for_panel(panel) for panel in dataset.panels}
