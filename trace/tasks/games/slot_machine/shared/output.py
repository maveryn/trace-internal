"""Trace assembly helpers for slot-machine games tasks."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .rendering import RenderedSlotMachineScene
from .state import SlotMachineAxes, SlotMachineScene, cell_grid


def build_slot_machine_common_trace_params(
    *,
    axes: SlotMachineAxes,
    extra_params: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return scene-axis trace params plus task-owned params."""

    params = {
        "scene_variant": str(axes.scene_variant),
        "style_variant": str(axes.style_variant),
        "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
        "style_variant_probabilities": dict(axes.style_variant_probabilities),
    }
    params.update(dict(extra_params or {}))
    return params


def build_slot_machine_trace_payload(
    *,
    axes: SlotMachineAxes,
    scene: SlotMachineScene,
    rendered_scene: RenderedSlotMachineScene,
    annotation_artifacts: Any,
    annotation_payline_rows: Sequence[int],
    query_spec: Mapping[str, Any],
    answer_value: int,
    execution_extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble slot-machine trace sections after task-specific binding."""

    return {
        "scene_ir": {
            "scene_kind": f"games_slot_machine_{str(axes.scene_variant)}",
            "entities": [dict(entity) for entity in rendered_scene.scene_entities],
            "relations": {
                "scene_variant": str(axes.scene_variant),
                "style_variant": str(axes.style_variant),
                "winning_rows": [int(row) for row in scene.winning_rows],
                "annotation_payline_rows": [int(row) for row in annotation_payline_rows],
            },
        },
        "query_spec": dict(query_spec),
        "render_spec": {
            "scene_variant": str(axes.scene_variant),
            "style_variant": str(axes.style_variant),
            "canvas_width": int(rendered_scene.image.size[0]),
            "canvas_height": int(rendered_scene.image.size[1]),
            "panel_scene_style": dict(rendered_scene.panel_style_meta),
        },
        "render_map": dict(rendered_scene.render_map),
        "execution_trace": {
            "scene_variant": str(axes.scene_variant),
            "style_variant": str(axes.style_variant),
            "symbol_grid": [list(row) for row in cell_grid(scene)],
            "winning_rows": [int(row) for row in scene.winning_rows],
            "answer": int(answer_value),
            "annotation_payline_rows": [int(row) for row in annotation_payline_rows],
            **dict(execution_extra or {}),
        },
        "witness_symbolic": {
            "type": "payline_segment_set",
            "rows": [int(row) for row in annotation_payline_rows],
        },
        "projected_annotation": dict(annotation_artifacts.projected_annotation),
        "background": dict(rendered_scene.background_meta),
        "post_image_noise": dict(rendered_scene.post_noise_meta),
    }


__all__ = [
    "build_slot_machine_common_trace_params",
    "build_slot_machine_trace_payload",
]
