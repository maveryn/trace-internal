"""Identity-free output helpers for wire-shape-conversion diagrams."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from PIL import Image

from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.shared.prompt_variants import PromptTraceArtifacts

from .annotations import annotation_bbox_map
from .defaults import DOMAIN, POST_IMAGE_NOISE_DEFAULTS, SCENE_ID
from .prompts import wire_shape_prompt_artifacts
from .rendering import render_wire_shape_with_retries
from .state import RenderedScene, ResolvedProblem


@dataclass(frozen=True)
class PreparedWireShapeArtifacts:
    """Rendered diagram artifacts after a public task binds objective data."""

    image: Image.Image
    rendered: RenderedScene
    annotation_value: dict[str, list[float]]
    prompt_artifacts: PromptTraceArtifacts
    noise_meta: dict[str, Any]


def prepare_wire_shape_artifacts(
    *,
    problem: ResolvedProblem,
    render_scene: Callable[..., RenderedScene],
    annotation_keys: Sequence[str],
    prompt_task_key: str,
    prompt_branch_key: str,
    answer: int,
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
    render_defaults: Mapping[str, Any],
    prompt_defaults: Mapping[str, Any],
    random_namespace: str,
) -> PreparedWireShapeArtifacts:
    """Render, annotate, and compose prompts without choosing task semantics."""

    rendered = render_wire_shape_with_retries(
        problem=problem,
        render_scene=render_scene,
        instance_seed=int(instance_seed),
        params=params,
        render_defaults=render_defaults,
        max_attempts=int(max_attempts),
        random_namespace=str(random_namespace),
    )
    image, noise_meta = apply_post_image_noise(
        rendered.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    annotation_value = annotation_bbox_map(rendered, annotation_keys)
    _prompt_defaults, prompt_artifacts = wire_shape_prompt_artifacts(
        prompt_defaults=prompt_defaults,
        prompt_task_key=str(prompt_task_key),
        prompt_branch_key=str(prompt_branch_key),
        annotation_keys=annotation_keys,
        answer=int(answer),
        instance_seed=int(instance_seed),
    )
    return PreparedWireShapeArtifacts(
        image=image,
        rendered=rendered,
        annotation_value=dict(annotation_value),
        prompt_artifacts=prompt_artifacts,
        noise_meta=dict(noise_meta),
    )


def common_trace_sections(
    *,
    problem: ResolvedProblem,
    rendered: RenderedScene,
    annotation_keys: Sequence[str],
    noise_meta: Mapping[str, Any],
    image_size: tuple[int, int],
) -> dict[str, Any]:
    """Build scene-level trace sections before a public task binds identity."""

    render_style = dict(rendered.render_map.get("style", {}))
    if render_style:
        render_style["post_image_noise"] = dict(noise_meta)
    return {
        "scene_ir": {
            "domain": DOMAIN,
            "scene_id": SCENE_ID,
            "entities": [dict(entity) for entity in rendered.scene_entities],
            "relations": {
                "type": str(problem.formula_family),
                "source_wire_length": int(problem.source_values["wire_length"]),
                "annotation_roles": [str(key) for key in annotation_keys],
            },
        },
        "render_spec": {
            "scene_id": SCENE_ID,
            "canvas": {"width": int(image_size[0]), "height": int(image_size[1])},
            "style": render_style,
        },
        "render_map": dict(rendered.render_map),
        "execution_trace": {
            "scene_id": SCENE_ID,
            "formula_family": str(problem.formula_family),
            "formula": str(problem.formula),
            "source_shape": str(problem.source_shape),
            "target_shape": str(problem.target_shape),
            "source_values": dict(problem.source_values),
            "target_values": dict(problem.target_values),
            "annotation_roles": [str(key) for key in annotation_keys],
        },
    }


def trace_with_prompt_sections(
    *,
    problem: ResolvedProblem,
    rendered: RenderedScene,
    annotation_keys: Sequence[str],
    noise_meta: Mapping[str, Any],
    image_size: tuple[int, int],
    prompt_artifacts: PromptTraceArtifacts,
) -> dict[str, Any]:
    """Attach prompt metadata to scene trace sections without public identity."""

    trace_payload = common_trace_sections(
        problem=problem,
        rendered=rendered,
        annotation_keys=annotation_keys,
        noise_meta=noise_meta,
        image_size=image_size,
    )
    trace_payload["render_spec"]["prompt"] = prompt_render_spec(prompt_artifacts)
    return trace_payload


def conversion_problem_metadata(problem: ResolvedProblem) -> dict[str, Any]:
    """Serialize source/target values common to same-wire conversion objectives."""

    return {
        "case_probabilities": dict(problem.case_probabilities),
        "answer_support_probabilities": dict(problem.answer_support_probabilities),
        "source_shape": str(problem.source_shape),
        "target_shape": str(problem.target_shape),
        "source_values": dict(problem.source_values),
        "target_values": dict(problem.target_values),
        "source_wire_length": int(problem.source_values["wire_length"]),
    }


def prompt_render_spec(prompt_artifacts: PromptTraceArtifacts) -> dict[str, Any]:
    """Serialize prompt variant metadata for a render spec."""

    return {
        "prompt_variant": dict(prompt_artifacts.prompt_variant),
        "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
        "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
    }


__all__ = [
    "PreparedWireShapeArtifacts",
    "common_trace_sections",
    "conversion_problem_metadata",
    "prepare_wire_shape_artifacts",
    "prompt_render_spec",
    "trace_with_prompt_sections",
]
