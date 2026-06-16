"""Count arithmetic over two prompt-named procedural icon groups."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import uniform_probability_map
from ...shared.named_colors import named_color
from ...shared.fixed_query import select_task_query_id
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.weighted_sampling import sample_weighted_value, weighted_probability_map
from ..shared.defaults import ICON_SHARED_DEFAULTS
from ..shared.icon_task_rendering import resolve_icon_render_params, sample_icon_instance_noise
from ..shared.procedural_named_icon_field_scene import (
    SCENE_ID,
    NamedIconFieldSpec,
    render_procedural_named_icon_field_scene,
    resolve_named_icon_fill_style_probabilities,
    resolve_named_icon_int_bounds,
    rotation_for_named_shape,
    uniform_string_probability_map,
)
from .shared.output import build_pair_arithmetic_trace_payload
from .shared.rendering import build_named_icon_specs_from_semantics
from ..shared.procedural_named_icons import (
    PROCEDURAL_NAMED_ICON_FILL_STYLES,
    PROCEDURAL_NAMED_ICON_SHAPES,
    procedural_named_icon_display_name,
    procedural_named_icon_fill_style_probability_map,
    sample_procedural_named_icon_fill_style,
    validate_procedural_named_icon_fill_style_support,
)
from .shared.defaults import PAIR_ARITHMETIC_DEFAULTS as _DEFAULTS
from .shared.annotations import point_set_from_bboxes
from .shared.metrics import pair_arithmetic_counted_instance_ids, pair_arithmetic_role_by_instance_id
from .shared.sampling import color_support as _shared_color_support
from .shared.sampling import sample_pair_arithmetic_spec, shape_support as _shared_shape_support


TASK_ID = "task_icons__named_field__count_arithmetic"

QUERY_IDS: Tuple[str, ...] = (
    "two_shape_total_count",
    "two_shape_difference_count",
    "two_bound_color_total_count",
    "two_bound_color_difference_count",
)
TOTAL_QUERY_IDS: Tuple[str, ...] = (
    "two_shape_total_count",
    "two_bound_color_total_count",
)
DIFFERENCE_QUERY_IDS: Tuple[str, ...] = (
    "two_shape_difference_count",
    "two_bound_color_difference_count",
)

_NON_STACK_LAYOUT_MODES: Tuple[str, ...] = (
    "jittered_grid",
    "ordered_grid",
    "shelf_rows",
    "free_scatter",
)
_TASK_GROUP_DEFAULTS = get_scene_defaults("icons", "named_field")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)




def _shape_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    return _shared_shape_support(params, _GEN_DEFAULTS, min_count=3)


def _color_support(params: Mapping[str, Any]):
    return _shared_color_support(params, _GEN_DEFAULTS)


def _operation_for_query(query_key: str) -> str:
    if str(query_key).endswith("_total_count"):
        return "total"
    if str(query_key).endswith("_difference_count"):
        return "absolute_difference"
    raise ValueError(f"unsupported pair-arithmetic query branch: {query_key}")


def _uses_color_binding(query_key: str) -> bool:
    return "bound_color" in str(query_key)


def _instance_bbox_sort_key(instance: Any) -> tuple[int, int, int, int]:
    bbox = [int(value) for value in instance.bbox_xyxy]
    return (bbox[1], bbox[0], bbox[3], bbox[2])


def _counted_annotation_maps(
    *,
    instances: Sequence[Any],
    counted_instance_ids: Sequence[str],
) -> tuple[list[list[int]], list[str]]:
    counted_ids = {str(instance_id) for instance_id in counted_instance_ids}
    counted_instances = sorted(
        [instance for instance in instances if str(instance.instance_id) in counted_ids],
        key=_instance_bbox_sort_key,
    )
    missing_ids = sorted(counted_ids - {str(instance.instance_id) for instance in counted_instances})
    if missing_ids:
        raise RuntimeError(f"missing rendered counted instances for annotation: {missing_ids}")
    return (
        [[int(value) for value in instance.bbox_xyxy] for instance in counted_instances],
        [str(instance.instance_id) for instance in counted_instances],
    )




def _question_text(prompt_defaults: Mapping[str, Any], sample: Any) -> str:
    question_key = f"question_text_{sample.query_key}"
    return str(prompt_defaults[question_key]).format(
        left_shape_name=str(sample.left_operand.shape_name),
        right_shape_name=str(sample.right_operand.shape_name),
        left_operand_label=str(sample.left_operand.label),
        right_operand_label=str(sample.right_operand.label),
    )


class _IconsNamedShapePairArithmeticCountTaskBase:
    """Shared implementation for two named-icon group arithmetic tasks."""

    task_id = TASK_ID
    domain = "icons"
    query_ids: Tuple[str, ...] = QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one task instance by binding sampling, rendering, prompt, answer, and annotation."""
        selected_query_key, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=tuple(self.query_ids),
            default_query_id=str(self.query_ids[0]),
            task_id=str(self.task_id),
        )
        operation = _operation_for_query(str(selected_query_key))
        uses_color_binding = _uses_color_binding(str(selected_query_key))
        last_error: Exception | None = None
        sample: Any | None = None
        scene = None
        sampled_palette_rgb: Tuple[Tuple[int, int, int], ...] = ()
        render_params = resolve_icon_render_params(
            params=task_params,
            render_defaults=_RENDER_DEFAULTS,
            fallback_defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        slot_padding_px = int(
            task_params.get(
                "named_icon_slot_padding_px",
                group_default(_RENDER_DEFAULTS, "named_icon_slot_padding_px", _DEFAULTS.named_icon_slot_padding_px),
            )
        )
        slot_jitter_px = int(
            task_params.get(
                "named_icon_slot_jitter_px",
                group_default(_RENDER_DEFAULTS, "named_icon_slot_jitter_px", _DEFAULTS.named_icon_slot_jitter_px),
            )
        )
        stack_gap_px = int(
            task_params.get(
                "named_icon_stack_gap_px",
                group_default(_RENDER_DEFAULTS, "named_icon_stack_gap_px", _DEFAULTS.named_icon_stack_gap_px),
            )
        )
        for attempt in range(max(1, int(max_attempts))):
            try:
                sample = sample_pair_arithmetic_spec(
                    run_namespace=str(self.task_id),
                    query_key=str(selected_query_key),
                    operation=str(operation),
                    uses_color_binding=bool(uses_color_binding),
                    query_probabilities=query_probabilities,
                    instance_seed=int(instance_seed),
                    params=task_params,
                    gen_defaults=_GEN_DEFAULTS,
                    render_defaults=_RENDER_DEFAULTS,
                )
                scene_rng = spawn_rng(int(instance_seed), f"{self.task_id}:scene", int(attempt))
                icon_specs, sampled_palette_rgb = build_named_icon_specs_from_semantics(
                    semantic_specs=sample.semantic_specs,
                    instance_seed=int(instance_seed),
                    render_params=render_params,
                    rng=scene_rng,
                    noise_namespace=str(self.task_id),
                )
                scene = render_procedural_named_icon_field_scene(
                    rng=scene_rng,
                    instance_seed=int(instance_seed),
                    task_id=self.task_id,
                    icon_specs=icon_specs,
                    render_params=render_params,
                    layout_modes=(str(sample.arrangement_mode),),
                    slot_padding_px=int(slot_padding_px),
                    slot_jitter_px=int(slot_jitter_px),
                    stack_gap_px=int(stack_gap_px),
                )
                break
            except Exception as exc:  # pragma: no cover - exercised through smoke tests.
                last_error = exc
                sample = None
                scene = None
        if scene is None or sample is None:
            raise RuntimeError(f"could not generate {self.task_id}: {last_error}") from last_error

        counted_instance_ids = pair_arithmetic_counted_instance_ids(sample, scene.instances)

        _, _, active_prompt_defaults = split_generation_rendering_prompt_defaults(
            _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
            task_id=str(self.task_id),
        )
        question_key = f"question_text_{sample.query_key}"
        prompt_defaults = required_group_defaults(
            active_prompt_defaults,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                question_key,
                "annotation_hint",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            scene_id=SCENE_ID,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "question_text": _question_text(active_prompt_defaults, sample),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint"]).format(
                    left_operand_label=str(sample.left_operand.label),
                    right_operand_label=str(sample.right_operand.label),
                ),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        role_by_instance_id = pair_arithmetic_role_by_instance_id(sample)
        left_instance_ids = tuple(
            str(instance_id)
            for instance_id in counted_instance_ids
            if role_by_instance_id.get(str(instance_id)) == "left_operand"
        )
        right_instance_ids = tuple(
            str(instance_id)
            for instance_id in counted_instance_ids
            if role_by_instance_id.get(str(instance_id)) == "right_operand"
        )
        if len(left_instance_ids) != int(sample.left_count) or len(right_instance_ids) != int(sample.right_count):
            raise RuntimeError("operand role counts do not match sampled counts")
        annotation_bboxes, annotation_instance_ids = _counted_annotation_maps(
            instances=scene.instances,
            counted_instance_ids=counted_instance_ids,
        )
        annotation_bbox_count = len(annotation_bboxes)
        if annotation_bbox_count != int(sample.left_count) + int(sample.right_count):
            raise RuntimeError("rendered named-icon pair arithmetic annotation did not match operand counts")
        annotation_artifacts = point_set_from_bboxes(annotation_bboxes)
        trace_payload = build_pair_arithmetic_trace_payload(
            sample=sample,
            scene=scene,
            render_params=render_params,
            sampled_palette_rgb=sampled_palette_rgb,
            prompt_defaults=prompt_defaults,
            prompt_artifacts=prompt_artifacts,
            annotation_artifacts=annotation_artifacts,
            counted_instance_ids=counted_instance_ids,
            left_instance_ids=left_instance_ids,
            right_instance_ids=right_instance_ids,
            role_by_instance_id=role_by_instance_id,
            annotation_instance_ids=tuple(annotation_instance_ids),
            query_ids=tuple(self.query_ids),
            shape_support=_shape_support(task_params),
            color_support=_color_support(task_params),
            fill_style_support=tuple(sample.fill_style_support),
            slot_padding_px=slot_padding_px,
            slot_jitter_px=slot_jitter_px,
            stack_gap_px=stack_gap_px,
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(sample.target_answer)),
            annotation_gt=TypedValue(
                type=str(annotation_artifacts["annotation_type"]),
                value=list(annotation_artifacts["annotation_value"]),
            ),
            image=scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(sample.query_key),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
        )


@register_task
class IconsNamedFieldShapePairArithmeticCountTask(_IconsNamedShapePairArithmeticCountTaskBase):
    """Count total or absolute difference over two named icon groups."""

    task_id = TASK_ID
    query_ids = QUERY_IDS
    supported_query_ids = QUERY_IDS

    def _build_arithmetic_query_ids(self) -> Tuple[str, ...]:
        """Bind this public objective to total and difference query branches."""

        return QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one named-field arithmetic counting instance."""

        query_ids = self._build_arithmetic_query_ids()
        if tuple(query_ids) != QUERY_IDS:
            raise RuntimeError("named-field arithmetic query support changed unexpectedly")
        merged_params = dict(params)
        return super().generate(int(instance_seed), params=merged_params, max_attempts=int(max_attempts))


__all__ = [
    "DIFFERENCE_QUERY_IDS",
    "IconsNamedFieldShapePairArithmeticCountTask",
    "QUERY_IDS",
    "TOTAL_QUERY_IDS",
]
