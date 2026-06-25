"""Neutral render, prompt, and trace plumbing for volume-equivalence tasks."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from PIL import Image

from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec

from .shared.annotations import annotation_bbox_map, projected_annotation
from .shared.construction import solid_volume
from .shared.defaults import DOMAIN, POST_IMAGE_NOISE_DEFAULTS, SCENE_ID, load_volume_equivalence_defaults
from .shared.prompts import volume_equivalence_prompt_artifacts
from .shared.rendering import render_volume_equivalence_with_retries
from .shared.state import RenderContext, RenderedScene, ResolvedProblem


@dataclass(frozen=True)
class VolumeEquivalenceTaskBinding:
    prompt_task_key: str
    annotation_keys: tuple[str, ...]
    answer_hint_key: str
    answer_type: str
    render_scene: Callable[[RenderContext, ResolvedProblem], RenderedScene]


@dataclass(frozen=True)
class VolumeEquivalenceTaskParts:
    prompt: str
    prompt_variants: dict[str, str]
    image: Image.Image
    annotation_value: dict[str, list[float]]
    trace_payload: dict[str, Any]
    task_versions: dict[str, str]
    scene_id: str


def _json_answer(problem: ResolvedProblem) -> int | str:
    return str(problem.answer) if problem.answer_schema == "option_letter" else int(problem.answer)


def _query_params(
    *,
    public_identifier: str,
    branch_key: str,
    branch_probabilities: Mapping[str, float],
    problem: ResolvedProblem,
) -> dict[str, Any]:
    return {
        "task_id": str(public_identifier),
        "scene_id": SCENE_ID,
        "query_id": str(branch_key),
        "query_id_probabilities": dict(branch_probabilities),
        "case_probabilities": dict(problem.case_probabilities),
        "answer_support_probabilities": dict(problem.answer_support_probabilities),
        "option_count_probabilities": dict(problem.option_count_probabilities),
        "source_shape": problem.source.shape,
        "target_shape": problem.target.shape,
        "source_volume": int(solid_volume(problem.source)),
        "target_volume": int(solid_volume(problem.target)),
        "target_unknown_role": str(problem.target_unknown_role),
        "selected_option_label": str(problem.selected_option_label),
    }


def _trace_payload(
    *,
    public_identifier: str,
    branch_key: str,
    branch_probabilities: Mapping[str, float],
    problem: ResolvedProblem,
    rendered: RenderedScene,
    prompt_artifacts: Any,
    annotation_keys: Sequence[str],
    annotation_value: Mapping[str, list[float]],
    noise_meta: Mapping[str, Any],
    image_size: tuple[int, int],
) -> dict[str, Any]:
    """Build trace sections after the public task has resolved the objective."""

    params = _query_params(
        public_identifier=str(public_identifier),
        branch_key=str(branch_key),
        branch_probabilities=branch_probabilities,
        problem=problem,
    )
    query_spec = build_prompt_query_spec(
        prompt_artifacts=prompt_artifacts,
        query_id=str(branch_key),
        params=params,
    )
    query_spec["scene_id"] = SCENE_ID
    render_style = dict(rendered.render_meta.get("style", {}))
    if render_style:
        render_style["post_image_noise"] = dict(noise_meta)
    return {
        "scene_ir": {
            "domain": DOMAIN,
            "scene_id": SCENE_ID,
            "task_id": str(public_identifier),
            "query_id": str(branch_key),
            "entities": [dict(entity) for entity in rendered.scene_entities],
            "relations": {
                "type": str(problem.formula_family),
                "source_volume": int(solid_volume(problem.source)),
                "target_volume": int(solid_volume(problem.target)),
                "annotation_roles": list(annotation_keys),
            },
        },
        "query_spec": query_spec,
        "render_spec": {
            "task_id": str(public_identifier),
            "scene_id": SCENE_ID,
            "query_id": str(branch_key),
            "canvas": {"width": int(image_size[0]), "height": int(image_size[1])},
            "option_count": int(len(problem.option_specs)) if problem.option_specs else 0,
            "option_count_probabilities": dict(problem.option_count_probabilities),
            "style": render_style,
            "prompt": {
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            },
        },
        "render_map": {"query_id": str(branch_key), **dict(rendered.render_map)},
        "execution_trace": {
            "task_id": str(public_identifier),
            "scene_id": SCENE_ID,
            "query_id": str(branch_key),
            "formula_family": str(problem.formula_family),
            "formula": str(problem.formula),
            "source_shape": problem.source.shape,
            "target_shape": problem.target.shape,
            "source_volume": int(solid_volume(problem.source)),
            "target_volume": int(solid_volume(problem.target)),
            "target_unknown_role": str(problem.target_unknown_role),
            "selected_option_label": str(problem.selected_option_label),
            "option_count_probabilities": dict(problem.option_count_probabilities),
            "answer": _json_answer(problem),
            "annotation_roles": list(annotation_keys),
        },
        "witness_symbolic": dict(params),
        "projected_annotation": projected_annotation(dict(annotation_value)),
    }


def prepare_volume_equivalence_task_parts(
    *,
    public_identifier: str,
    branch_key: str,
    branch_probabilities: Mapping[str, float],
    problem: ResolvedProblem,
    binding: VolumeEquivalenceTaskBinding,
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
) -> VolumeEquivalenceTaskParts:
    """Prepare shared output fields after the public task binds the objective."""

    _generation_defaults, render_defaults, prompt_defaults = load_volume_equivalence_defaults(str(public_identifier))
    rendered = render_volume_equivalence_with_retries(
        problem=problem,
        render_scene=binding.render_scene,
        instance_seed=int(instance_seed),
        params=params,
        render_defaults=render_defaults,
        max_attempts=int(max_attempts),
        random_namespace=str(public_identifier),
    )
    image, noise_meta = apply_post_image_noise(
        rendered.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    annotation_value = annotation_bbox_map(rendered, binding.annotation_keys)
    _prompt_defaults, prompt_artifacts = volume_equivalence_prompt_artifacts(
        prompt_defaults=prompt_defaults,
        prompt_task_key=str(binding.prompt_task_key),
        prompt_branch_key=str(branch_key),
        annotation_keys=binding.annotation_keys,
        answer=_json_answer(problem),
        instance_seed=int(instance_seed),
    )
    trace_payload = _trace_payload(
        public_identifier=str(public_identifier),
        branch_key=str(branch_key),
        branch_probabilities=branch_probabilities,
        problem=problem,
        rendered=rendered,
        prompt_artifacts=prompt_artifacts,
        annotation_keys=binding.annotation_keys,
        annotation_value=annotation_value,
        noise_meta=noise_meta,
        image_size=image.size,
    )
    return VolumeEquivalenceTaskParts(
        prompt=str(prompt_artifacts.prompt),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
        image=image,
        annotation_value=dict(annotation_value),
        trace_payload=trace_payload,
        task_versions=default_task_versions(),
        scene_id=SCENE_ID,
    )


__all__ = [
    "VolumeEquivalenceTaskBinding",
    "VolumeEquivalenceTaskParts",
    "prepare_volume_equivalence_task_parts",
]
