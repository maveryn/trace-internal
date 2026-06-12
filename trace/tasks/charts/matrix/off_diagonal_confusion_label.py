"""Select the largest off-diagonal predicted label in a confusion matrix."""

from __future__ import annotations

from typing import Any, Dict

from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.output_metadata import default_task_versions
from .shared.cell_common import (
    SCENE_ID,
    _decoupled_sampling_params,
    _resolve_grid_style,
    _resolve_header_layout,
    _resolve_palette_variant,
)
from .shared.cell_sampling import construct_off_diagonal_confusion_dataset
from .shared.output import build_trace_payload
from .shared.prompts import build_prompt_artifacts, dynamic_slots
from .shared.runtime import annotation_bboxes, render_matrix_scene


@register_task
class ChartsMatrixOffDiagonalConfusionLabelTask:
    """Return the predicted-column label with the largest off-diagonal count."""

    task_id = "task_charts__matrix__off_diagonal_confusion_label"
    domain = "charts"
    scene_id = SCENE_ID
    objective_contract = "off_diagonal_confusion_label"
    supported_query_ids = ("off_diagonal_confusion_label",)
    default_dataset_enabled = True
    supports_unanswerable = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                return self._generate_once(int(instance_seed) + int(attempt), params=params)
            except ValueError as exc:
                last_error = exc
                continue
        raise ValueError(f"could not construct unique-answer matrix off-diagonal task: {last_error}")

    def _generate_once(self, instance_seed: int, *, params: Dict[str, Any]) -> TaskOutput:
        scene_variant = "confusion_matrix_counts"
        scene_variant_probabilities = {"confusion_matrix_counts": 1.0}
        palette_params = _decoupled_sampling_params(params, divisor=3, explicit_keys=("palette_variant", "palette_variant_weights"))
        palette_variant, palette_variant_probabilities = _resolve_palette_variant(palette_params, instance_seed=int(instance_seed))
        header_params = _decoupled_sampling_params(params, divisor=5, explicit_keys=("header_layout", "header_layout_weights"))
        header_layout, header_layout_probabilities = _resolve_header_layout(header_params, instance_seed=int(instance_seed))
        grid_params = _decoupled_sampling_params(params, divisor=7, explicit_keys=("grid_style", "grid_style_weights"))
        grid_style, grid_style_probabilities = _resolve_grid_style(grid_params, instance_seed=int(instance_seed))
        dataset = construct_off_diagonal_confusion_dataset(params=params, instance_seed=int(instance_seed))
        rendered = render_matrix_scene(
            dataset=dataset,
            scene_variant=scene_variant,
            palette_variant=str(palette_variant),
            header_layout=str(header_layout),
            grid_style=str(grid_style),
            params=params,
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_artifacts(
            prompt_query_key=self.objective_contract,
            dynamic_slot_values=dynamic_slots(dataset, scene_variant=scene_variant, supports_unanswerable=False),
            instance_seed=int(instance_seed),
        )
        annotation_cell_ids = [str(cell_id) for cell_id in dataset["annotation_cell_ids"]]
        support_header_keys = [str(key) for key in dataset["annotation_header_keys"]]
        boxes, entries = annotation_bboxes(rendered_scene=rendered.rendered_scene, annotation_cell_ids=annotation_cell_ids)
        answer_value = str(dataset["answer_value"])
        trace_payload = build_trace_payload(
            objective_contract=self.objective_contract,
            dataset=dataset,
            rendered=rendered,
            prompt_artifacts=prompt_artifacts,
            scene_variant=scene_variant,
            palette_variant=str(palette_variant),
            header_layout=str(header_layout),
            grid_style=str(grid_style),
            probabilities={
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "palette_variant_probabilities": dict(palette_variant_probabilities),
                "header_layout_probabilities": dict(header_layout_probabilities),
                "grid_style_probabilities": dict(grid_style_probabilities),
            },
            annotation_cell_ids=annotation_cell_ids,
            support_header_keys=support_header_keys,
            annotation_bboxes=boxes,
            annotation_entries=entries,
            answer_value=answer_value,
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=TypedValue(type="string", value=answer_value),
            annotation_gt=TypedValue(type="bbox_set", value=list(boxes)),
            image=rendered.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=self.objective_contract,
        )


__all__ = ["ChartsMatrixOffDiagonalConfusionLabelTask"]
