"""Hero-callout task for reading one visible callout field value."""

from __future__ import annotations

from typing import Any, Dict

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.output_metadata import default_task_versions

from . import _lifecycle


TASK_ID = "task_pages__hero_callout_infographic__callout_field_value_label"
SUPPORTED_QUERY_IDS = (SINGLE_QUERY_ID,)
PROMPT_QUERY_KEY = "callout_field_value_label"
QUESTION_FORMAT = "hero_callout_infographic_callout_field_value_label"


def _build_prompt_slots(callout: Any, field: Any) -> Dict[str, str]:
    """Bind the resolved callout title and field label into prompt slots."""

    return {
        "callout_title": f'"{callout.title}"',
        "field_label": f'"{field.label}"',
    }


def _lookup_annotation(ctx: Any, callout: Any, field: Any) -> Dict[str, list[float]]:
    """Bind the card and row witnesses from the rendered geometry map."""

    callout_id = str(callout.callout_id)
    field_id = str(field.field_id)
    return {
        "target_callout_card": [float(value) for value in ctx.rendered.callout_bboxes_px[callout_id]],
        "target_field_row": [float(value) for value in ctx.rendered.field_row_bboxes_px[callout_id][field_id]],
    }


def _lookup_target_payload(callout: Any, field: Any) -> Dict[str, Any]:
    """Record the exact field value read by this direct lookup task."""

    return {
        "callout_id": str(callout.callout_id),
        "callout_title": str(callout.title),
        "field_id": str(field.field_id),
        "field_label": str(field.label),
        "visible_value": str(field.visible_value),
        "numeric_value": int(field.numeric_value),
        "answer_value": str(field.visible_value),
    }


@register_task
class PagesHeroCalloutFieldValueLabelTask:
    """Read one visible field value from a titled hero-callout card."""

    task_id = TASK_ID
    domain = "pages"
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one field-value lookup and bind its three bbox witnesses."""

        del max_attempts
        selected_branch, branch_probabilities, task_params = _lifecycle.select_public_branch(
            instance_seed=int(instance_seed),
            params=params,
            supported=SUPPORTED_QUERY_IDS,
            default=SINGLE_QUERY_ID,
            public_task=TASK_ID,
        )
        ctx = _lifecycle.resolve_scene_context(
            selected_branch=str(selected_branch),
            branch_probabilities=branch_probabilities,
            params=task_params,
            instance_seed=int(instance_seed),
        )
        callout, field, callout_probs, field_probs = _lifecycle.select_lookup_target(
            spec=ctx.spec,
            params=task_params,
            instance_seed=int(instance_seed),
        )
        annotation = _lookup_annotation(ctx, callout, field)
        prompt_artifacts = _lifecycle.render_prompt(
            prompt_query_key=PROMPT_QUERY_KEY,
            dynamic_slots=_build_prompt_slots(callout, field),
            instance_seed=int(instance_seed),
        )
        target = _lookup_target_payload(callout, field)
        trace_payload = _lifecycle._trace_payload(
            ctx=ctx,
            prompt_artifacts=prompt_artifacts,
            prompt_query_key=PROMPT_QUERY_KEY,
            question_format=QUESTION_FORMAT,
            target_payload=target,
            answer_value=str(field.visible_value),
            annotation_type="bbox_map",
            annotation_value=dict(annotation),
            annotation_keys=list(annotation.keys()),
            query_params_extra={
                "target_callout_index_probabilities": dict(callout_probs),
                "target_field_label_probabilities": dict(field_probs),
            },
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="string", value=str(field.visible_value)),
            annotation_gt=TypedValue(type="bbox_map", value=dict(annotation)),
            image=ctx.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=_lifecycle.SCENE_ID,
            query_id=str(ctx.selected_branch),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = [
    "PROMPT_QUERY_KEY",
    "QUESTION_FORMAT",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "PagesHeroCalloutFieldValueLabelTask",
]
