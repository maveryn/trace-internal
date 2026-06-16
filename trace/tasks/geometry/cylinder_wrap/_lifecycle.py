"""Neutral scene plumbing for cylinder-wrap task generation."""

from __future__ import annotations

from typing import Any, Callable, Dict, Mapping, TypeVar

from .shared.annotations import projected_keyed_annotation
from .shared.defaults import SCENE_ID, SCENE_KIND
from .shared.rendering import make_render_context
from .shared.state import RenderContext, RenderedCylinderWrapScene

ProblemT = TypeVar("ProblemT")


def render_with_attempts(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    max_attempts: int,
    problem: ProblemT,
    render_scene: Callable[[RenderContext, ProblemT, int], RenderedCylinderWrapScene],
) -> tuple[RenderedCylinderWrapScene, Dict[str, Any]]:
    """Run neutral render retries for one already-sampled scene problem."""

    last_error: Exception | None = None
    for attempt in range(max(1, int(max_attempts))):
        try:
            ctx, render_meta_attempt = make_render_context(
                instance_seed=int(instance_seed) + int(attempt),
                params=params,
                render_defaults=render_defaults,
            )
            layout_seed = int(instance_seed) + int(attempt)
            rendered = render_scene(ctx, problem, layout_seed=layout_seed)
            return rendered, dict(render_meta_attempt)
        except Exception as exc:
            last_error = exc
            continue
    raise RuntimeError("failed to render cylinder_wrap scene") from last_error


def build_trace_payload(
    *,
    scene_variant: str,
    formula_schema: str,
    selected_query: str,
    query_probabilities: Mapping[str, float],
    rendered: RenderedCylinderWrapScene,
    prompt_defaults: Mapping[str, Any],
    prompt_artifacts: Any,
    render_meta: Mapping[str, Any],
    noise_meta: Mapping[str, Any],
    image_size: tuple[int, int],
    annotation_value: Mapping[str, Any],
    answer_value: int | str,
    query_params: Mapping[str, Any],
) -> Dict[str, Any]:
    """Assemble the common trace envelope from task-owned semantic fields."""

    params = {
        "scene_id": SCENE_ID,
        "scene_variant": str(scene_variant),
        "query_id": str(selected_query),
        "query_id_probabilities": dict(query_probabilities),
        "formula_schema": str(formula_schema),
        **dict(query_params),
        **dict(rendered.witness),
    }
    return {
        "scene_ir": {
            "scene_kind": SCENE_KIND,
            "scene_id": SCENE_ID,
            "entities": [dict(entity) for entity in rendered.scene_entities],
            "relations": {
                "scene_variant": str(scene_variant),
                "query_id": str(selected_query),
                "formula_schema": str(formula_schema),
                "answer_value": answer_value,
                "annotation_roles": list(rendered.annotation_roles),
            },
        },
        "query_spec": {
            "scene_id": SCENE_ID,
            "query_id": str(selected_query),
            "template_id": str(prompt_defaults["bundle_id"]),
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": dict(params),
        },
        "render_spec": {
            "canvas_size": [int(image_size[0]), int(image_size[1])],
            "coord_space": "pixel",
            "post_image_noise": dict(noise_meta),
            **dict(render_meta),
        },
        "render_map": dict(rendered.render_map),
        "execution_trace": {
            "scene_id": SCENE_ID,
            "scene_variant": str(scene_variant),
            "query_id": str(selected_query),
            "formula_schema": str(formula_schema),
            "answer_type": str(rendered.answer_type),
            "answer_value": answer_value,
            "annotation_roles": list(rendered.annotation_roles),
            "reasoning_steps": 2,
            **dict(query_params),
            **dict(rendered.witness),
        },
        "witness_symbolic": {
            "type": str(formula_schema),
            "scene_id": SCENE_ID,
            "scene_variant": str(scene_variant),
            "query_id": str(selected_query),
            "source_witness_type": str(rendered.annotation_type),
            "original_annotation_value": list(rendered.annotation_roles),
            "answer_value": answer_value,
            **dict(rendered.witness),
        },
        "projected_annotation": projected_keyed_annotation(str(rendered.annotation_type), annotation_value),
    }


__all__ = ["build_trace_payload", "render_with_attempts"]
