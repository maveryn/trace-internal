"""Trace payload scaffolds for named-field icon tasks.

Public task files own target selection, answer binding, annotation binding, and
final ``TaskOutput`` construction. These helpers only serialize scene state and
task-supplied semantic fields into TRACE payload sections.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence, Tuple

from ....shared.color_format import format_named_color_with_hex
from ....shared.config_defaults import group_default
from ....shared.named_colors import available_named_colors
from ...shared.icon_task_rendering import icon_render_style_trace
from ...shared.procedural_named_icon_field_scene import SCENE_ID, serialize_named_icon_instance

from .metrics import (
    BOOLEAN_PREDICATE_AND,
    BOOLEAN_PREDICATE_ATTRIBUTE_WITHOUT_SHAPE,
    BOOLEAN_PREDICATE_NEITHER,
    BOOLEAN_PREDICATE_OR,
    BOOLEAN_PREDICATE_SHAPE_WITHOUT_ATTRIBUTE,
    BOOLEAN_PREDICATE_XOR,
    COUNTERFACTUAL_SHAPE_REMOVAL,
    COUNTERFACTUAL_SHAPE_REPLACEMENT,
    boolean_entity_partition,
    counterfactual_counted_shape_ids_after_edit,
    counterfactual_role_by_instance_id,
    trace_key,
)


def render_slot_params(params: Mapping[str, Any], render_defaults: Mapping[str, Any], fallback_defaults: Any) -> tuple[int, int, int]:
    """Resolve shared named-icon slot rendering knobs."""

    return (
        int(
            params.get(
                "named_icon_slot_padding_px",
                group_default(render_defaults, "named_icon_slot_padding_px", fallback_defaults.named_icon_slot_padding_px),
            )
        ),
        int(
            params.get(
                "named_icon_slot_jitter_px",
                group_default(render_defaults, "named_icon_slot_jitter_px", fallback_defaults.named_icon_slot_jitter_px),
            )
        ),
        int(
            params.get(
                "named_icon_stack_gap_px",
                group_default(render_defaults, "named_icon_stack_gap_px", fallback_defaults.named_icon_stack_gap_px),
            )
        ),
    )


def object_bboxes(instances: Sequence[Any]) -> dict[str, list[int]]:
    """Return visible object bboxes keyed by rendered instance id."""

    return {str(instance.instance_id): [int(value) for value in instance.bbox_xyxy] for instance in instances}


def shape_counted_instance_ids(sample: Any, instances: Sequence[Any]) -> tuple[str, ...]:
    """Return rendered instance ids matching a direct shape-count target."""

    return tuple(str(instance.instance_id) for instance in instances if str(instance.shape_id) == str(sample.target_shape_id))


def semantic_color_palette() -> list[dict[str, Any]]:
    """Serialize the named-color support visible to semantic color tasks."""

    return [
        {
            "name": str(name),
            "rgb": [int(channel) for channel in rgb],
            "label": format_named_color_with_hex(str(name), rgb),
        }
        for name, rgb in available_named_colors()
    ]


def build_shape_count_query_metadata(
    *,
    sample: Any,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    shape_support: Sequence[str],
) -> dict[str, Any]:
    """Serialize sampled non-public axes for direct shape counting."""

    return {
        "target_shape_id": str(sample.target_shape_id),
        "target_shape_name": str(sample.target_shape_name),
        "target_count": int(sample.target_count),
        "object_count": int(sample.object_count),
        "arrangement_mode": str(sample.arrangement_mode),
        "arrangement_mode_probabilities": dict(sample.arrangement_mode_probabilities),
        "arrangement_details": dict(sample.arrangement_details),
        "shape_id_support": list(shape_support),
        "shape_probabilities": dict(sample.shape_probabilities),
        "target_count_probabilities": dict(sample.target_count_probabilities),
        "object_count_probabilities": dict(sample.object_count_probabilities),
        "named_icon_fill_style_support": list(sample.fill_style_support),
        "fill_style_probabilities": dict(sample.fill_style_probabilities),
    }


def build_boolean_query_metadata(
    *,
    sample: Any,
    query_expression: str,
    public_query_id: str,
    public_query_probabilities: Mapping[str, float],
    shape_support: Sequence[str],
    color_support: Sequence[Any],
    fill_style_support: Sequence[str],
    queryable_fill_style_support: Sequence[str],
) -> dict[str, Any]:
    """Serialize sampled non-public axes for a Boolean count task."""

    return {
        trace_key("query", "id"): str(public_query_id),
        "prompt_query_key": str(sample.prompt_query_key),
        "internal_query_id": str(sample.prompt_query_key),
        "target_shape_id": str(sample.target_shape_id),
        "target_shape_name": str(sample.target_shape_name),
        "target_attribute_axis": str(sample.target_attribute_axis),
        "target_attribute_value": str(sample.target_attribute_value),
        "target_attribute_label": str(sample.target_attribute_label),
        "target_color_name": str(sample.target_color.name) if sample.target_color is not None else "",
        "target_color_rgb": [int(channel) for channel in sample.target_color.rgb] if sample.target_color is not None else [],
        "target_color_label": str(sample.target_color.label) if sample.target_color is not None else "",
        "target_fill_style": str(sample.target_fill_style),
        "target_fill_style_label": str(sample.target_fill_style_label),
        "target_answer": int(sample.target_answer),
        "object_count": int(sample.object_count),
        "object_count_max_answer_offset": int(sample.object_count_max_answer_offset),
        "boolean_expression": str(query_expression),
        "partition_counts": {str(key): int(value) for key, value in sample.partition_counts.items()},
        "arrangement_mode": str(sample.arrangement_mode),
        "arrangement_mode_probabilities": dict(sample.arrangement_mode_probabilities),
        "shape_id_support": list(shape_support),
        "named_color_support": [str(entry.name) for entry in color_support],
        "named_icon_fill_style_support": list(fill_style_support),
        "queryable_named_icon_fill_style_support": list(queryable_fill_style_support),
        "query_probabilities": {str(key): float(value) for key, value in public_query_probabilities.items()},
        "query_id_probabilities": {str(key): float(value) for key, value in public_query_probabilities.items()},
        "shape_probabilities": dict(sample.shape_probabilities),
        "color_probabilities": dict(sample.color_probabilities),
        "fill_style_probabilities": dict(sample.fill_style_probabilities),
        "attribute_axis_probabilities": dict(sample.attribute_axis_probabilities),
        "target_count_probabilities": dict(sample.target_count_probabilities),
        "object_count_probabilities": dict(sample.object_count_probabilities),
    }


def build_counterfactual_query_metadata(
    *,
    sample: Any,
    public_query_id: str,
    public_query_probabilities: Mapping[str, float],
    shape_support: Sequence[str],
) -> dict[str, Any]:
    """Serialize sampled non-public axes for a counterfactual count task."""

    return {
        trace_key("query", "id"): str(public_query_id),
        "prompt_query_key": str(sample.prompt_query_key),
        "internal_query_id": str(sample.prompt_query_key),
        "target_answer": int(sample.target_answer),
        "object_count": int(sample.object_count),
        "target_shape_id": str(sample.target_shape_id),
        "target_shape_name": str(sample.target_shape_name),
        "source_shape_id": str(sample.source_shape_id),
        "source_shape_name": str(sample.source_shape_name),
        "remove_shape_id": str(sample.remove_shape_id),
        "remove_shape_name": str(sample.remove_shape_name),
        "source_count": int(sample.source_count),
        "existing_target_count": int(sample.existing_target_count),
        "removal_count": int(sample.removal_count),
        "distractor_count": int(sample.distractor_count),
        "shape_id_support": list(shape_support),
        "query_probabilities": {str(key): float(value) for key, value in public_query_probabilities.items()},
        "query_id_probabilities": {str(key): float(value) for key, value in public_query_probabilities.items()},
        "shape_probabilities": dict(sample.shape_probabilities),
        "target_count_probabilities": dict(sample.target_count_probabilities),
        "removal_count_probabilities": dict(sample.removal_count_probabilities),
        "distractor_count_probabilities": dict(sample.distractor_count_probabilities),
        "arrangement_mode": str(sample.arrangement_mode),
        "arrangement_mode_probabilities": dict(sample.arrangement_mode_probabilities),
        "named_icon_fill_style_support": list(sample.fill_style_support),
        "fill_style_probabilities": dict(sample.fill_style_probabilities),
    }


def build_shape_count_trace_payload(
    *,
    sample: Any,
    scene: Any,
    render_params: Mapping[str, Any],
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...],
    prompt_defaults: Mapping[str, Any],
    prompt_artifacts: Any,
    annotation_artifacts: Mapping[str, Any],
    counted_instance_ids: Tuple[str, ...],
    query_metadata: Mapping[str, Any],
    public_query_id: str,
    slot_padding_px: int,
    slot_jitter_px: int,
    stack_gap_px: int,
) -> dict[str, Any]:
    """Build trace sections for a direct named-shape count."""

    serialized_instances = [serialize_named_icon_instance(instance) for instance in scene.instances]
    shape_counts = dict(Counter(str(instance.shape_id) for instance in scene.instances))
    return {
        "scene_ir": {
            "scene_kind": "icons_named_shape_field",
            "scene_id": SCENE_ID,
            "entities": list(serialized_instances),
            "relations": {
                "counting_rule": "shape_id_equals_target",
                "target_shape_id": str(sample.target_shape_id),
                "target_shape_name": str(sample.target_shape_name),
                "shape_counts": {str(key): int(value) for key, value in shape_counts.items()},
                "arrangement_mode": str(sample.arrangement_mode),
                "arrangement_details": dict(sample.arrangement_details),
            },
            "frames": {"pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"}, "panels": dict(scene.panel_geometry)},
        },
        "query_spec": {
            trace_key("query", "id"): str(public_query_id),
            "template_id": str(prompt_defaults["bundle_id"]),
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": dict(query_metadata),
        },
        "render_spec": {
            "canvas_size": list(scene.panel_geometry["canvas_size"]),
            "coord_space": "pixel",
            "scene_id": SCENE_ID,
            "panel_geometry": dict(scene.panel_geometry),
            "style": {
                **icon_render_style_trace(render_params=render_params, sampled_palette_rgb=sampled_palette_rgb),
                "layout_mode": str(scene.layout_mode),
                "named_icon_fill_style_support": list(sample.fill_style_support),
                "named_icon_slot_padding_px": int(slot_padding_px),
                "named_icon_slot_jitter_px": int(slot_jitter_px),
                "named_icon_stack_gap_px": int(stack_gap_px),
            },
        },
        "render_map": {"image_id": "img0", "object_bboxes_px": object_bboxes(scene.instances), "counted_instance_ids": list(counted_instance_ids)},
        "execution_trace": {
            "scene_variant": "single_panel_named_shape_field",
            "arrangement_mode": str(sample.arrangement_mode),
            trace_key("query", "id"): str(public_query_id),
            "question_format": "count_named_shape_icons",
            "target_shape_id": str(sample.target_shape_id),
            "target_shape_name": str(sample.target_shape_name),
            "target_count": int(sample.target_count),
            "object_count": int(sample.object_count),
            "shape_counts": {str(key): int(value) for key, value in shape_counts.items()},
            "arrangement_details": dict(sample.arrangement_details),
            "scene_shape_ids": [str(instance.shape_id) for instance in scene.instances],
            "counted_instance_ids": list(counted_instance_ids),
        },
        "witness_symbolic": {
            "target_shape_id": str(sample.target_shape_id),
            "target_shape_name": str(sample.target_shape_name),
            "answer": int(sample.target_count),
            "counted_instance_ids": list(counted_instance_ids),
        },
        "projected_annotation": {**dict(annotation_artifacts["projected_annotation"])},
    }


def build_boolean_trace_payload(
    *,
    sample: Any,
    scene: Any,
    render_params: Mapping[str, Any],
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...],
    prompt_defaults: Mapping[str, Any],
    prompt_artifacts: Any,
    annotation_artifacts: Mapping[str, Any],
    counted_instance_ids: Tuple[str, ...],
    query_expression: str,
    query_metadata: Mapping[str, Any],
    public_query_id: str,
    slot_padding_px: int,
    slot_jitter_px: int,
    stack_gap_px: int,
    fill_style_support: Tuple[str, ...],
    queryable_fill_style_support: Tuple[str, ...],
) -> dict[str, Any]:
    """Build trace sections for a Boolean named-field count."""

    serialized_instances = [serialize_named_icon_instance(instance) for instance in scene.instances]
    shape_counts = Counter(str(instance.shape_id) for instance in scene.instances)
    color_counts = Counter(str(instance.color_name) for instance in scene.instances)
    fill_style_counts = Counter(str(instance.fill_style) for instance in scene.instances)
    attribute_counts = color_counts if str(sample.target_attribute_axis) == "color" else fill_style_counts
    shape_attribute_counts = Counter(
        f"{instance.shape_id}|{instance.color_name if str(sample.target_attribute_axis) == 'color' else instance.fill_style}"
        for instance in scene.instances
    )
    entity_partition = boolean_entity_partition(sample, scene.instances)
    return {
        "scene_ir": {
            "scene_kind": "icons_named_shape_color_field",
            "scene_id": SCENE_ID,
            "entities": list(serialized_instances),
            "relations": {
                "counting_rule": str(query_expression),
                "target_shape_id": str(sample.target_shape_id),
                "target_shape_name": str(sample.target_shape_name),
                "target_attribute_axis": str(sample.target_attribute_axis),
                "target_attribute_value": str(sample.target_attribute_value),
                "target_attribute_label": str(sample.target_attribute_label),
                "target_color_name": str(sample.target_color.name) if sample.target_color is not None else "",
                "target_color_rgb": [int(channel) for channel in sample.target_color.rgb] if sample.target_color is not None else [],
                "target_color_label": str(sample.target_color.label) if sample.target_color is not None else "",
                "target_fill_style": str(sample.target_fill_style),
                "target_fill_style_label": str(sample.target_fill_style_label),
                "shape_counts": {str(key): int(value) for key, value in shape_counts.items()},
                "color_counts": {str(key): int(value) for key, value in color_counts.items()},
                "fill_style_counts": {str(key): int(value) for key, value in fill_style_counts.items()},
                "attribute_counts": {str(key): int(value) for key, value in attribute_counts.items()},
                "shape_attribute_counts": {str(key): int(value) for key, value in shape_attribute_counts.items()},
                "partition_counts": {str(key): int(value) for key, value in sample.partition_counts.items()},
                "arrangement_mode": str(sample.arrangement_mode),
            },
            "frames": {"pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"}, "panels": dict(scene.panel_geometry)},
        },
        "query_spec": {
            trace_key("query", "id"): str(public_query_id),
            "prompt_query_key": str(sample.prompt_query_key),
            "internal_query_id": str(sample.prompt_query_key),
            "template_id": str(prompt_defaults["bundle_id"]),
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": dict(query_metadata),
        },
        "render_spec": {
            "canvas_size": list(scene.panel_geometry["canvas_size"]),
            "coord_space": "pixel",
            "scene_id": SCENE_ID,
            "panel_geometry": dict(scene.panel_geometry),
            "style": {
                **icon_render_style_trace(render_params=render_params, sampled_palette_rgb=sampled_palette_rgb),
                "layout_mode": str(scene.layout_mode),
                "named_icon_slot_padding_px": int(slot_padding_px),
                "named_icon_slot_jitter_px": int(slot_jitter_px),
                "named_icon_stack_gap_px": int(stack_gap_px),
                "semantic_color_palette": semantic_color_palette(),
                "semantic_fill_style_support": list(fill_style_support),
                "queryable_semantic_fill_style_support": list(queryable_fill_style_support),
            },
        },
        "render_map": {
            "image_id": "img0",
            "object_bboxes_px": object_bboxes(scene.instances),
            "counted_instance_ids": list(counted_instance_ids),
            "entity_partition": dict(entity_partition),
        },
        "execution_trace": {
            "scene_variant": "single_panel_named_shape_color_field",
            "arrangement_mode": str(sample.arrangement_mode),
            trace_key("query", "id"): str(public_query_id),
            "prompt_query_key": str(sample.prompt_query_key),
            "internal_query_id": str(sample.prompt_query_key),
            "question_format": "count_named_shape_color_boolean_icons",
            "target_shape_id": str(sample.target_shape_id),
            "target_shape_name": str(sample.target_shape_name),
            "target_attribute_axis": str(sample.target_attribute_axis),
            "target_attribute_value": str(sample.target_attribute_value),
            "target_attribute_label": str(sample.target_attribute_label),
            "target_color_name": str(sample.target_color.name) if sample.target_color is not None else "",
            "target_color_rgb": [int(channel) for channel in sample.target_color.rgb] if sample.target_color is not None else [],
            "target_color_label": str(sample.target_color.label) if sample.target_color is not None else "",
            "target_fill_style": str(sample.target_fill_style),
            "target_fill_style_label": str(sample.target_fill_style_label),
            "target_answer": int(sample.target_answer),
            "object_count": int(sample.object_count),
            "boolean_expression": str(query_expression),
            "partition_counts": {str(key): int(value) for key, value in sample.partition_counts.items()},
            "shape_counts": {str(key): int(value) for key, value in shape_counts.items()},
            "color_counts": {str(key): int(value) for key, value in color_counts.items()},
            "fill_style_counts": {str(key): int(value) for key, value in fill_style_counts.items()},
            "attribute_counts": {str(key): int(value) for key, value in attribute_counts.items()},
            "shape_attribute_counts": {str(key): int(value) for key, value in shape_attribute_counts.items()},
            "scene_shape_ids": [str(instance.shape_id) for instance in scene.instances],
            "scene_color_names": [str(instance.color_name) for instance in scene.instances],
            "scene_fill_styles": [str(instance.fill_style) for instance in scene.instances],
            "counted_instance_ids": list(counted_instance_ids),
        },
        "witness_symbolic": {
            "target_shape_id": str(sample.target_shape_id),
            "target_shape_name": str(sample.target_shape_name),
            "target_attribute_axis": str(sample.target_attribute_axis),
            "target_attribute_value": str(sample.target_attribute_value),
            "target_attribute_label": str(sample.target_attribute_label),
            "target_color_name": str(sample.target_color.name) if sample.target_color is not None else "",
            "target_color_label": str(sample.target_color.label) if sample.target_color is not None else "",
            "target_fill_style": str(sample.target_fill_style),
            "target_fill_style_label": str(sample.target_fill_style_label),
            "answer": int(sample.target_answer),
            "counted_instance_ids": list(counted_instance_ids),
        },
        "projected_annotation": {**dict(annotation_artifacts["projected_annotation"])},
    }


def build_counterfactual_trace_payload(
    *,
    sample: Any,
    scene: Any,
    render_params: Mapping[str, Any],
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...],
    prompt_defaults: Mapping[str, Any],
    prompt_artifacts: Any,
    annotation_artifacts: Mapping[str, Any],
    counted_instance_ids: Tuple[str, ...],
    query_metadata: Mapping[str, Any],
    public_query_id: str,
    slot_padding_px: int,
    slot_jitter_px: int,
    stack_gap_px: int,
) -> dict[str, Any]:
    """Build trace sections for a counterfactual named-field count."""

    serialized_instances = [serialize_named_icon_instance(instance) for instance in scene.instances]
    shape_counts = Counter(str(instance.shape_id) for instance in scene.instances)
    role_by_instance_id = counterfactual_role_by_instance_id(sample)
    counted_shape_ids_after_edit = counterfactual_counted_shape_ids_after_edit(sample)
    return {
        "scene_ir": {
            "scene_kind": "icons_named_shape_counterfactual_field",
            "scene_id": SCENE_ID,
            "entities": list(serialized_instances),
            "relations": {
                "counting_rule": "apply_hypothetical_icon_removal_or_replacement_then_count",
                trace_key("query", "id"): str(public_query_id),
                "prompt_query_key": str(sample.prompt_query_key),
                "target_shape_id": str(sample.target_shape_id),
                "target_shape_name": str(sample.target_shape_name),
                "source_shape_id": str(sample.source_shape_id),
                "source_shape_name": str(sample.source_shape_name),
                "remove_shape_id": str(sample.remove_shape_id),
                "remove_shape_name": str(sample.remove_shape_name),
                "source_count": int(sample.source_count),
                "existing_target_count": int(sample.existing_target_count),
                "removal_count": int(sample.removal_count),
                "distractor_count": int(sample.distractor_count),
                "shape_counts": {str(key): int(value) for key, value in shape_counts.items()},
                "role_by_instance_id": dict(role_by_instance_id),
                "arrangement_mode": str(sample.arrangement_mode),
            },
            "frames": {"pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"}, "panels": dict(scene.panel_geometry)},
        },
        "query_spec": {
            trace_key("query", "id"): str(public_query_id),
            "prompt_query_key": str(sample.prompt_query_key),
            "internal_query_id": str(sample.prompt_query_key),
            "template_id": str(prompt_defaults["bundle_id"]),
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": dict(query_metadata),
        },
        "render_spec": {
            "canvas_size": list(scene.panel_geometry["canvas_size"]),
            "coord_space": "pixel",
            "scene_id": SCENE_ID,
            "panel_geometry": dict(scene.panel_geometry),
            "style": {
                **icon_render_style_trace(render_params=render_params, sampled_palette_rgb=sampled_palette_rgb),
                "layout_mode": str(scene.layout_mode),
                "named_icon_fill_style_support": list(sample.fill_style_support),
                "named_icon_slot_padding_px": int(slot_padding_px),
                "named_icon_slot_jitter_px": int(slot_jitter_px),
                "named_icon_stack_gap_px": int(stack_gap_px),
            },
        },
        "render_map": {
            "image_id": "img0",
            "object_bboxes_px": object_bboxes(scene.instances),
            "counted_instance_ids": list(counted_instance_ids),
            "role_by_instance_id": dict(role_by_instance_id),
        },
        "execution_trace": {
            "scene_variant": "single_panel_named_shape_counterfactual_field",
            "arrangement_mode": str(sample.arrangement_mode),
            trace_key("query", "id"): str(public_query_id),
            "prompt_query_key": str(sample.prompt_query_key),
            "internal_query_id": str(sample.prompt_query_key),
            "question_format": "count_named_shape_icons_after_hypothetical_edit",
            "target_answer": int(sample.target_answer),
            "object_count": int(sample.object_count),
            "target_shape_id": str(sample.target_shape_id),
            "target_shape_name": str(sample.target_shape_name),
            "source_shape_id": str(sample.source_shape_id),
            "source_shape_name": str(sample.source_shape_name),
            "remove_shape_id": str(sample.remove_shape_id),
            "remove_shape_name": str(sample.remove_shape_name),
            "source_count": int(sample.source_count),
            "existing_target_count": int(sample.existing_target_count),
            "removal_count": int(sample.removal_count),
            "distractor_count": int(sample.distractor_count),
            "shape_counts": {str(key): int(value) for key, value in shape_counts.items()},
            "final_counted_shape_ids_after_edit": list(counted_shape_ids_after_edit),
            "final_target_shape_count": int(sample.target_answer),
            "counted_instance_ids": list(counted_instance_ids),
            "role_by_instance_id": dict(role_by_instance_id),
        },
        "witness_symbolic": {
            "answer": int(sample.target_answer),
            "counted_instance_ids": list(counted_instance_ids),
            trace_key("query", "id"): str(public_query_id),
            "prompt_query_key": str(sample.prompt_query_key),
            "internal_query_id": str(sample.prompt_query_key),
            "target_shape_id": str(sample.target_shape_id),
            "target_shape_name": str(sample.target_shape_name),
            "source_shape_id": str(sample.source_shape_id),
            "source_shape_name": str(sample.source_shape_name),
            "remove_shape_id": str(sample.remove_shape_id),
            "remove_shape_name": str(sample.remove_shape_name),
        },
        "projected_annotation": {**dict(annotation_artifacts["projected_annotation"])},
    }


__all__ = [
    "BOOLEAN_PREDICATE_AND",
    "BOOLEAN_PREDICATE_ATTRIBUTE_WITHOUT_SHAPE",
    "BOOLEAN_PREDICATE_NEITHER",
    "BOOLEAN_PREDICATE_OR",
    "BOOLEAN_PREDICATE_SHAPE_WITHOUT_ATTRIBUTE",
    "BOOLEAN_PREDICATE_XOR",
    "COUNTERFACTUAL_SHAPE_REMOVAL",
    "COUNTERFACTUAL_SHAPE_REPLACEMENT",
    "build_boolean_query_metadata",
    "build_boolean_trace_payload",
    "build_counterfactual_query_metadata",
    "build_counterfactual_trace_payload",
    "build_shape_count_query_metadata",
    "build_shape_count_trace_payload",
    "object_bboxes",
    "render_slot_params",
    "semantic_color_palette",
    "shape_counted_instance_ids",
]
