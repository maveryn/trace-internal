"""Neutral render lifecycle for parallel-segment proportion tasks."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from PIL import Image

from trace.core.visual.noise import apply_post_image_noise

from .shared.annotations import point_set_annotation_artifacts
from .shared.defaults import POST_IMAGE_NOISE_DEFAULTS
from .shared.rendering import make_render_context, render_parallel_proportion_scene
from .shared.state import ParallelProportionPlan, RenderedParallelProportionScene
from ..shared.annotation_values import PixelAnnotationArtifacts


PlanResolver = Callable[[int, Mapping[str, Any]], tuple[ParallelProportionPlan, dict[str, float]]]


@dataclass(frozen=True)
class ParallelSceneArtifacts:
    """Rendered scene and verifier fragments shared by public task files."""

    plan: ParallelProportionPlan
    construction_probabilities: dict[str, float]
    rendered: RenderedParallelProportionScene
    render_meta: dict[str, Any]
    image: Image.Image
    noise_meta: dict[str, Any]
    annotation_artifacts: PixelAnnotationArtifacts


def prepare_parallel_scene_artifacts(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
    max_attempts: int,
    resolve_plan: PlanResolver,
) -> ParallelSceneArtifacts:
    """Resolve one task-owned plan, then render/noise/project from that same trace."""

    rendered: RenderedParallelProportionScene | None = None
    render_meta: dict[str, Any] | None = None
    plan: ParallelProportionPlan | None = None
    construction_probabilities: dict[str, float] | None = None
    last_error: Exception | None = None
    for attempt in range(max(1, int(max_attempts))):
        attempt_seed = int(instance_seed) + int(attempt)
        try:
            plan, construction_probabilities = resolve_plan(attempt_seed, params)
            ctx, render_meta_attempt = make_render_context(
                instance_seed=attempt_seed,
                params=params,
                rendering_defaults=rendering_defaults,
            )
            rendered = render_parallel_proportion_scene(ctx, plan, instance_seed=attempt_seed)
            render_meta = dict(render_meta_attempt)
            render_meta["single_object_scene_rotation"] = ctx.scene_transform.metadata()
            break
        except ValueError:
            raise
        except Exception as exc:
            last_error = exc
    if rendered is None or render_meta is None or plan is None or construction_probabilities is None:
        raise RuntimeError("failed to render parallel segment proportion scene") from last_error

    image, noise_meta = apply_post_image_noise(
        rendered.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    return ParallelSceneArtifacts(
        plan=plan,
        construction_probabilities=dict(construction_probabilities),
        rendered=rendered,
        render_meta=dict(render_meta),
        image=image,
        noise_meta=dict(noise_meta),
        annotation_artifacts=point_set_annotation_artifacts(rendered.annotation_points),
    )


__all__ = ["ParallelSceneArtifacts", "PlanResolver", "prepare_parallel_scene_artifacts"]
