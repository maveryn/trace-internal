"""Objective-neutral trace assembly for darts games tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

from .rendering import RenderedDartsTaskContext
from .state import DartsSampledScene, DartsSceneAxes


def _dart_specs_for_trace(sample: DartsSampledScene) -> list[Dict[str, Any]]:
    """Return JSON-friendly dart specs for trace payloads."""

    return [
        {
            "dart_id": str(dart.dart_id),
            "sector_value": None if dart.sector_value is None else int(dart.sector_value),
            "ring": str(dart.ring),
            "score": int(dart.score),
            "is_annotation": bool(dart.is_annotation),
        }
        for dart in sample.darts
    ]


def _score_options_for_trace(sample: DartsSampledScene) -> list[Dict[str, Any]]:
    """Return JSON-friendly score options for trace payloads."""

    return [
        {
            "label": str(option.label),
            "score": int(option.score),
            "is_answer": bool(option.is_answer),
        }
        for option in sample.score_options
    ]


def build_darts_common_trace_params(
    *,
    axes: DartsSceneAxes,
    extra_params: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Return shared darts prompt params plus task-owned params."""

    params: Dict[str, Any] = {
        "scene_variant": str(axes.scene_variant),
        "style_variant": str(axes.style_variant),
        "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
        "style_variant_probabilities": dict(axes.style_variant_probabilities),
    }
    if extra_params:
        params.update(dict(extra_params))
    return params


def build_darts_trace_payload(
    *,
    annotation_artifacts: Any,
    annotation_entity_ids: Sequence[str],
    axes: DartsSceneAxes,
    sample: DartsSampledScene,
    rendered_context: RenderedDartsTaskContext,
    prompt_defaults: Mapping[str, Any],
    prompt_artifacts: Any,
    query_spec: Mapping[str, Any],
    answer_value: int | str,
    execution_extra: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Assemble darts trace sections after task-specific answer binding."""

    rendered_scene = rendered_context.rendered_scene
    score_options = _score_options_for_trace(sample)
    return {
        "scene_ir": {
            "scene_kind": f"games_darts_{str(axes.scene_variant)}",
            "entities": [dict(entity) for entity in rendered_scene.scene_entities],
            "relations": {
                "scene_variant": str(axes.scene_variant),
                "style_variant": str(axes.style_variant),
                "score_option_count": int(len(sample.score_options)),
                "annotation_entity_ids": [str(entity_id) for entity_id in annotation_entity_ids],
            },
        },
        "query_spec": dict(query_spec),
        "render_spec": {
            "scene_variant": str(axes.scene_variant),
            "style_variant": str(axes.style_variant),
            "canvas_width": int(rendered_context.image.size[0]),
            "canvas_height": int(rendered_context.image.size[1]),
            "dart_fill_color": list(rendered_scene.render_map.get("dart_fill_color") or []),
            "dart_fill_min_lab_distance": rendered_scene.render_map.get("dart_fill_min_lab_distance"),
            "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
            "panel_scene_style": dict(rendered_context.panel_style_meta),
            "text_style": dict(rendered_context.text_style_meta),
        },
        "render_map": dict(rendered_scene.render_map),
        "execution_trace": {
            "scene_variant": str(axes.scene_variant),
            "style_variant": str(axes.style_variant),
            "answer": answer_value,
            "score_options": list(score_options),
            "score_option_count": int(len(score_options)),
            "dart_specs": _dart_specs_for_trace(sample),
            "annotation_entity_ids": [str(entity_id) for entity_id in annotation_entity_ids],
            **dict(execution_extra or {}),
        },
        "witness_symbolic": {
            "type": "object_set",
            "ids": [str(entity_id) for entity_id in annotation_entity_ids],
        },
        "projected_annotation": dict(annotation_artifacts.projected_annotation),
        "background": dict(rendered_context.background_meta),
        "post_image_noise": dict(rendered_context.post_noise_meta),
        "prompt_metadata": {"bundle_id": str(prompt_defaults["bundle_id"])},
    }


__all__ = ["build_darts_common_trace_params", "build_darts_trace_payload"]
