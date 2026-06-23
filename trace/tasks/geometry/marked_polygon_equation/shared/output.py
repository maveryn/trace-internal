"""Neutral visual artifact preparation for marked polygon equation tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from PIL import Image

from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.geometry.shared.annotation_values import PixelAnnotationArtifacts
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import PromptTraceArtifacts

from .annotations import marked_equation_point_annotation
from .defaults import POST_IMAGE_NOISE_DEFAULTS
from .prompts import marked_equation_prompt_artifacts
from .rendering import render_marked_equation_with_retries
from .state import MarkedEquationCase, RenderedMarkedEquationScene


@dataclass(frozen=True)
class MarkedEquationTaskParts:
    """Prepared non-verifier output fields for one task-owned case."""

    prompt: str
    prompt_variants: dict[str, str]
    image: Image.Image
    prompt_artifacts: PromptTraceArtifacts
    rendered: RenderedMarkedEquationScene
    annotation_artifacts: PixelAnnotationArtifacts
    render_meta: dict[str, Any]
    noise_meta: dict[str, Any]
    task_versions: dict[str, str]


def prepare_marked_equation_parts(
    *,
    case: MarkedEquationCase,
    prompt_task_key: str,
    prompt_question_key: str,
    rendering_defaults: Mapping[str, Any],
    prompt_defaults: Mapping[str, Any],
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
) -> MarkedEquationTaskParts:
    """Prepare image, prompt, and annotation artifacts after task case binding."""

    rendered, render_meta = render_marked_equation_with_retries(
        case=case,
        instance_seed=int(instance_seed),
        params=params,
        rendering_defaults=rendering_defaults,
        max_attempts=int(max_attempts),
    )
    image, noise_meta = apply_post_image_noise(
        rendered.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    annotation_artifacts = marked_equation_point_annotation(rendered)
    _prompt_defaults, prompt_artifacts = marked_equation_prompt_artifacts(
        prompt_defaults=prompt_defaults,
        prompt_task_key=str(prompt_task_key),
        prompt_question_key=str(prompt_question_key),
        annotation_keys=tuple(annotation_artifacts.value.keys()),
        target_name=str(case.target_name),
        variable_name=str(case.variable_name),
        answer=case.answer,
        instance_seed=int(instance_seed),
    )
    return MarkedEquationTaskParts(
        prompt=str(prompt_artifacts.prompt),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
        image=image,
        prompt_artifacts=prompt_artifacts,
        rendered=rendered,
        annotation_artifacts=annotation_artifacts,
        render_meta=dict(render_meta),
        noise_meta=dict(noise_meta),
        task_versions=default_task_versions(),
    )


__all__ = ["MarkedEquationTaskParts", "prepare_marked_equation_parts"]
