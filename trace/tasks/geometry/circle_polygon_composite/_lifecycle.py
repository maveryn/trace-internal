"""Neutral scene lifecycle plumbing for circle-polygon-composite tasks."""

from __future__ import annotations

from typing import Any, Callable, Mapping


def render_with_layout_retry(
    *,
    instance_seed: int,
    task_params: Mapping[str, Any],
    max_attempts: int,
    build_context: Callable[[int, Mapping[str, Any]], Any],
    draw_scene: Callable[[Any, int], Any],
) -> tuple[Any, Any]:
    """Retry stochastic layout without choosing task/query behavior."""

    last_error: Exception | None = None
    for attempt in range(max(1, int(max_attempts))):
        attempt_params = dict(task_params)
        attempt_params["_render_attempt"] = int(attempt)
        attempt_seed = int(instance_seed) + int(attempt)
        try:
            render_context = build_context(attempt_seed, attempt_params)
            rendered = draw_scene(render_context, attempt_seed)
            return render_context, rendered
        except Exception as exc:
            last_error = exc
    raise RuntimeError("failed to render circle-polygon-composite scene") from last_error


def render_spec_payload(
    *,
    scene_id: str,
    task_id: str,
    query_id: str,
    image_size: tuple[int, int],
    render_context: Any,
    noise_meta: Mapping[str, Any],
    prompt_artifacts: Any,
) -> dict[str, Any]:
    """Serialize common render/style/prompt metadata without routing objectives."""

    return {
        "task_id": str(task_id),
        "scene_id": str(scene_id),
        "query_id": str(query_id),
        "canvas": {
            "width": int(image_size[0]),
            "height": int(image_size[1]),
        },
        "single_object_scene_rotation": render_context.scene_transform.metadata(),
        "style": {
            "technical_diagram": dict(render_context.diagram_style_meta),
            "background": dict(render_context.background_meta),
            "post_image_noise": dict(noise_meta),
        },
        "prompt": {
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
        },
    }


def projected_keyed_point_payload(annotation_value: Mapping[str, list[float]]) -> dict[str, Any]:
    """Return the common trace payload for keyed point annotations."""

    return {
        "type": "keyed_point_map",
        "keyed_point_map": dict(annotation_value),
        "pixel_keyed_point_map": dict(annotation_value),
    }


__all__ = [
    "projected_keyed_point_payload",
    "render_spec_payload",
    "render_with_layout_retry",
]
