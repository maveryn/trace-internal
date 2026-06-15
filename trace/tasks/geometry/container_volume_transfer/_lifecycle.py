"""Neutral render, prompt, and trace plumbing for container-transfer tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from PIL import Image

from trace.core.visual.noise import apply_post_image_noise
from trace.core.types import TypedValue
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec

from .shared.annotations import annotation_bbox_map
from .shared.defaults import DOMAIN, POST_IMAGE_NOISE_DEFAULTS, SCENE_ID, SCENE_KIND, load_container_volume_transfer_task_defaults
from .shared.measurements import bind_sampling_metadata, json_answer_value, support_from_cases
from .shared.prompts import container_volume_prompt_artifacts
from .shared.rendering import render_container_volume_transfer_with_retries
from .shared.state import RenderedScene, ResolvedProblem


@dataclass(frozen=True)
class ContainerVolumeTaskBinding:
    prompt_task_key: str
    annotation_keys: tuple[str, ...]
    answer_hint_key: str
    answer_type: str


@dataclass(frozen=True)
class ContainerVolumeQueryProgram:
    selector: Callable[..., tuple[tuple[int, ...], dict[str, float]]]
    resolver: Callable[[Sequence[int]], ResolvedProblem]
    support_cases: tuple[Sequence[int], ...]
    support_field: str
    namespace_suffix: str


def resolve_container_volume_problem(
    *,
    public_identifier: str,
    program: ContainerVolumeQueryProgram,
    query_probabilities: Mapping[str, float],
    instance_seed: int,
    params: Mapping[str, Any],
) -> ResolvedProblem:
    case, case_probabilities = program.selector(
        instance_seed=int(instance_seed),
        params=params,
        namespace=f"{public_identifier}.{program.namespace_suffix}.case",
    )
    return bind_sampling_metadata(
        program.resolver(case),
        query_probabilities=dict(query_probabilities),
        case_probabilities=dict(case_probabilities),
        answer_support_probabilities=support_from_cases(program.support_cases, program.resolver, program.support_field),
        params=dict(params),
    )


def _query_params(
    *,
    selected_query: str,
    internal_prompt_key: str,
    query_probabilities: Mapping[str, float],
    problem: ResolvedProblem,
) -> dict[str, Any]:
    return {
        "scene_id": SCENE_ID,
        "query_id": str(selected_query),
        "internal_query_id": str(internal_prompt_key),
        "query_id_probabilities": dict(query_probabilities),
        "case_probabilities": dict(problem.case_probabilities),
        "answer_support_probabilities": dict(problem.answer_support_probabilities),
        "source_shape": str(problem.source_shape),
        "target_shape": str(problem.target_shape),
        "source_base_area": int(problem.source_base_area),
        "source_height": int(problem.source_height),
        "source_volume": int(problem.source_volume),
        "target_base_area": int(problem.target_base_area),
        "target_length": int(problem.target_length),
        "target_width": int(problem.target_width),
        "target_height": int(problem.target_height),
        "target_volume": int(problem.target_volume),
        "fill_count": int(problem.fill_count),
        "pour_count": int(problem.pour_count),
        "resulting_height": float(problem.resulting_height),
    }


def _trace_payload(
    *,
    rendered: RenderedScene,
    prompt_artifacts: Any,
    selected_query: str,
    internal_prompt_key: str,
    query_probabilities: Mapping[str, float],
    problem: ResolvedProblem,
    annotation_keys: Sequence[str],
    annotation_value: Mapping[str, list[float]],
    render_meta: Mapping[str, Any],
    noise_meta: Mapping[str, Any],
    image_size: tuple[int, int],
) -> dict[str, Any]:
    """Build trace sections after the public task has bound problem identity."""

    query_params = _query_params(
        selected_query=str(selected_query),
        internal_prompt_key=str(internal_prompt_key),
        query_probabilities=query_probabilities,
        problem=problem,
    )
    query_spec = build_prompt_query_spec(
        prompt_artifacts=prompt_artifacts,
        query_id=str(selected_query),
        params=query_params,
    )
    query_spec["scene_id"] = SCENE_ID
    projected_annotation = {
        "type": "keyed_bbox_map",
        "keyed_bbox_map": dict(annotation_value),
        "pixel_keyed_bbox_map": dict(annotation_value),
    }
    return {
        "scene_ir": {
            "domain": DOMAIN,
            "scene_kind": SCENE_KIND,
            "scene_id": SCENE_ID,
            "entities": [dict(entity) for entity in rendered.scene_entities],
            "relations": {
                "type": str(problem.formula_family),
                "source_shape": str(problem.source_shape),
                "target_shape": str(problem.target_shape),
                "source_volume": int(problem.source_volume),
                "target_volume": int(problem.target_volume),
                "pour_count": int(problem.pour_count),
                "annotation_roles": list(annotation_keys),
            },
        },
        "query_spec": query_spec,
        "render_spec": {
            "canvas_size": [int(image_size[0]), int(image_size[1])],
            "coord_space": "pixel",
            "post_image_noise": dict(noise_meta),
            "prompt": {
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            },
            **dict(render_meta),
        },
        "render_map": dict(rendered.render_map),
        "execution_trace": {
            "scene_id": SCENE_ID,
            "query_id": str(selected_query),
            "internal_query_id": str(internal_prompt_key),
            "formula_family": str(problem.formula_family),
            "formula": str(problem.formula),
            "answer": json_answer_value(problem.answer),
            "annotation_roles": list(annotation_keys),
            **dict(query_params),
        },
        "witness_symbolic": {
            "type": "container_volume_transfer",
            "source_witness_type": "keyed_bbox_map",
            "original_annotation_value": dict(annotation_value),
            **dict(query_params),
        },
        "projected_annotation": projected_annotation,
    }


@dataclass(frozen=True)
class ContainerVolumeTransferTaskParts:
    prompt: str
    prompt_variants: dict[str, str]
    image: Image.Image
    annotation_value: dict[str, list[float]]
    trace_payload: dict[str, Any]
    task_versions: dict[str, str]
    scene_id: str

    def output_args(self, *, answer_type: str, answer_value: int | float, query_id: str) -> tuple[Any, ...]:
        return (
            self.prompt,
            TypedValue(type=str(answer_type), value=answer_value),
            TypedValue(type="keyed_bbox_map", value=dict(self.annotation_value)),
            self.image,
            "img0",
            self.trace_payload,
            self.task_versions,
            self.scene_id,
            str(query_id),
            dict(self.prompt_variants),
        )


def prepare_container_volume_transfer_task_parts(
    *,
    public_identifier: str,
    selected_query: str,
    internal_prompt_key: str,
    query_probabilities: Mapping[str, float],
    problem: ResolvedProblem,
    binding: ContainerVolumeTaskBinding,
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
) -> ContainerVolumeTransferTaskParts:
    """Prepare non-verifier output fields after the public task binds the answer."""

    render_defaults, prompt_defaults = load_container_volume_transfer_task_defaults(str(public_identifier))
    rendered, render_meta = render_container_volume_transfer_with_retries(
        problem=problem,
        instance_seed=int(instance_seed),
        params=params,
        render_defaults=render_defaults,
        max_attempts=int(max_attempts),
        random_namespace=f"{public_identifier}.render",
    )
    image, noise_meta = apply_post_image_noise(
        rendered.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    annotation_value = annotation_bbox_map(rendered, binding.annotation_keys)
    prompt_artifacts = container_volume_prompt_artifacts(
        prompt_defaults=prompt_defaults,
        task_key=str(binding.prompt_task_key),
        query_key=str(internal_prompt_key),
        annotation_keys=binding.annotation_keys,
        answer_hint_key=str(binding.answer_hint_key),
        answer=problem.answer,
        instance_seed=int(instance_seed),
    )
    trace_payload = _trace_payload(
        rendered=rendered,
        prompt_artifacts=prompt_artifacts,
        selected_query=str(selected_query),
        internal_prompt_key=str(internal_prompt_key),
        query_probabilities=query_probabilities,
        problem=problem,
        annotation_keys=binding.annotation_keys,
        annotation_value=annotation_value,
        render_meta=render_meta,
        noise_meta=noise_meta,
        image_size=(int(image.size[0]), int(image.size[1])),
    )
    return ContainerVolumeTransferTaskParts(
        prompt=str(prompt_artifacts.prompt),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
        image=image,
        annotation_value=dict(annotation_value),
        trace_payload=trace_payload,
        task_versions=default_task_versions(),
        scene_id=SCENE_ID,
    )


__all__ = [
    "ContainerVolumeQueryProgram",
    "ContainerVolumeTaskBinding",
    "ContainerVolumeTransferTaskParts",
    "prepare_container_volume_transfer_task_parts",
    "resolve_container_volume_problem",
]
