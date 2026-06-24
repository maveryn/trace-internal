"""Find a missing target angle in a split-triangle angle-chase diagram."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from PIL import Image

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.base import TaskOutput
from trace.tasks.geometry.shared.annotation_values import PixelAnnotationArtifacts
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec

from .shared.annotations import split_triangle_point_annotation
from .shared.defaults import (
    DOMAIN,
    POST_IMAGE_NOISE_DEFAULTS,
    SCENE_ID,
    SCENE_KIND,
    TASK_PROMPT_KEY,
    load_split_triangle_defaults,
)
from .shared.prompts import build_split_triangle_prompt_artifacts
from .shared.rendering import (
    RENDER_SHARED_VERTEX,
    RENDER_SINGLE_CEVIAN,
    RENDER_TWO_STEP_ADJACENT,
    create_render_context,
    draw_split_triangle_scene,
)
from .shared.state import DEGREE_SYMBOL, RenderContext, RenderedSplitTriangleScene, SplitTriangleAngleCase

TASK_ID = "task_geometry__split_triangle_angle_chase__target_angle_value"
SUPPORTED_QUERY_IDS: tuple[str, ...] = (
    "single_cevian_triangle_angle_sum",
    "shared_vertex_split_angle_sum",
    "two_step_adjacent_triangle_angle_sum",
)


@dataclass(frozen=True)
class ResolvedAngleProblem:
    """Task-bound theorem case selected by query branch and answer support."""

    branch_key: str
    case: SplitTriangleAngleCase
    branch_probabilities: dict[str, float]
    answer_probabilities: dict[str, float]
    case_index: int


@dataclass(frozen=True)
class RenderedAttempt:
    """Rendered scene fields that must stay bound to one execution trace."""

    context: RenderContext
    rendered: RenderedSplitTriangleScene
    image: Image.Image
    noise_meta: dict[str, Any]
    annotation_artifacts: PixelAnnotationArtifacts


def _case(
    *,
    render_kind: str,
    answer: int,
    target_name: str,
    labels: Mapping[str, str],
    values: Mapping[str, float | int | str],
) -> SplitTriangleAngleCase:
    return SplitTriangleAngleCase(
        render_kind=str(render_kind),
        relation="split_triangle_angle_sum",
        answer=int(answer),
        target_name=str(target_name),
        labels=dict(labels),
        values=dict(values),
    )


def _build_cases() -> dict[str, tuple[SplitTriangleAngleCase, ...]]:
    """Build finite theorem cases, grouped by the public task's branch keys."""

    rows = (
        ("single_cevian_triangle_angle_sum", 42, 72, 66),
        ("single_cevian_triangle_angle_sum", 55, 47, 78),
        ("single_cevian_triangle_angle_sum", 38, 84, 58),
        ("single_cevian_triangle_angle_sum", 63, 46, 71),
        ("single_cevian_triangle_angle_sum", 48, 69, 63),
        ("single_cevian_triangle_angle_sum", 36, 92, 52),
        ("single_cevian_triangle_angle_sum", 44, 62, 74),
        ("single_cevian_triangle_angle_sum", 50, 46, 84),
        ("single_cevian_triangle_angle_sum", 67, 58, 55),
        ("single_cevian_triangle_angle_sum", 39, 72, 69),
        ("shared_vertex_split_angle_sum", 51, 57, 72),
        ("shared_vertex_split_angle_sum", 44, 68, 68),
        ("shared_vertex_split_angle_sum", 62, 41, 77),
        ("shared_vertex_split_angle_sum", 35, 83, 62),
        ("shared_vertex_split_angle_sum", 58, 52, 70),
        ("two_step_adjacent_triangle_angle_sum", 51, 49, 33),
        ("two_step_adjacent_triangle_angle_sum", 42, 66, 38),
        ("two_step_adjacent_triangle_angle_sum", 55, 35, 47),
        ("two_step_adjacent_triangle_angle_sum", 48, 54, 39),
        ("two_step_adjacent_triangle_angle_sum", 60, 42, 36),
        ("two_step_adjacent_triangle_angle_sum", 46, 58, 26),
        ("two_step_adjacent_triangle_angle_sum", 38, 63, 23),
        ("two_step_adjacent_triangle_angle_sum", 44, 51, 21),
        ("two_step_adjacent_triangle_angle_sum", 57, 48, 38),
        ("two_step_adjacent_triangle_angle_sum", 49, 57, 29),
    )
    grouped: dict[str, list[SplitTriangleAngleCase]] = defaultdict(list)
    for branch_key, angle_a, angle_b, angle_c in rows:
        if branch_key == "two_step_adjacent_triangle_angle_sum":
            left_unknown = 180 - int(angle_a) - int(angle_b)
            straight_supplement = 180 - int(left_unknown)
            answer = 180 - int(straight_supplement) - int(angle_c)
            grouped[branch_key].append(
                _case(
                    render_kind=RENDER_TWO_STEP_ADJACENT,
                    answer=int(answer),
                    target_name="the marked angle",
                    labels={
                        "given_left_A": f"{int(angle_a)}{DEGREE_SYMBOL}",
                        "given_left_D": f"{int(angle_b)}{DEGREE_SYMBOL}",
                        "given_right_C": f"{int(angle_c)}{DEGREE_SYMBOL}",
                        "target": "?",
                    },
                    values={
                        "angle_a": int(angle_a),
                        "angle_b": int(angle_b),
                        "angle_c": int(angle_c),
                        "left_triangle_missing_angle": int(left_unknown),
                        "straight_angle_supplement": int(straight_supplement),
                        "answer": int(answer),
                    },
                )
            )
        elif branch_key == "shared_vertex_split_angle_sum":
            grouped[branch_key].append(
                _case(
                    render_kind=RENDER_SHARED_VERTEX,
                    answer=int(angle_c),
                    target_name="the marked angle",
                    labels={
                        "given_left_A": f"{int(angle_a)}{DEGREE_SYMBOL}",
                        "given_left_D": f"{int(angle_b)}{DEGREE_SYMBOL}",
                        "target": "?",
                    },
                    values={
                        "angle_a": int(angle_a),
                        "angle_b": int(angle_b),
                        "angle_c": int(angle_c),
                        "answer": int(angle_c),
                    },
                )
            )
        else:
            grouped[branch_key].append(
                _case(
                    render_kind=RENDER_SINGLE_CEVIAN,
                    answer=int(angle_c),
                    target_name="the marked angle",
                    labels={
                        "given_left_A": f"{int(angle_a)}{DEGREE_SYMBOL}",
                        "given_left_B": f"{int(angle_b)}{DEGREE_SYMBOL}",
                        "target": "?",
                    },
                    values={
                        "angle_a": int(angle_a),
                        "angle_b": int(angle_b),
                        "angle_c": int(angle_c),
                        "answer": int(angle_c),
                    },
                )
            )
    return {str(key): tuple(value) for key, value in grouped.items()}


_CASES_BY_BRANCH = _build_cases()


def _probability_map(values: Sequence[int], selected: int | None = None) -> dict[str, float]:
    resolved = tuple(int(value) for value in values)
    if not resolved:
        return {}
    if selected is not None:
        return {str(value): (1.0 if int(value) == int(selected) else 0.0) for value in resolved}
    weight = 1.0 / float(len(resolved))
    return {str(value): float(weight) for value in resolved}


def _select_case_from_answer_support(
    *,
    cases: Sequence[SplitTriangleAngleCase],
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> tuple[SplitTriangleAngleCase, int, dict[str, float]]:
    """Choose a target answer uniformly, then choose one compatible case."""

    grouped: dict[int, list[tuple[int, SplitTriangleAngleCase]]] = defaultdict(list)
    for index, case in enumerate(cases):
        grouped[int(case.answer)].append((int(index), case))
    if not grouped:
        raise ValueError("split-triangle angle case support must be non-empty")

    answer_support = tuple(sorted(grouped))
    forced_answer = params.get("answer")
    rng = spawn_rng(int(instance_seed), str(namespace))
    if forced_answer is not None:
        answer = int(forced_answer)
        if answer not in grouped:
            raise ValueError(f"unsupported split-triangle angle answer: {answer}")
        answer_probabilities = _probability_map(answer_support, selected=answer)
    else:
        answer = int(answer_support[int(rng.randrange(len(answer_support)))])
        answer_probabilities = _probability_map(answer_support)

    compatible = tuple(grouped[answer])
    selected_index, selected_case = compatible[int(rng.randrange(len(compatible)))]
    return selected_case, int(selected_index), dict(answer_probabilities)


def _prepare_problem(
    *,
    branch_key: str,
    branch_probabilities: Mapping[str, float],
    params: Mapping[str, Any],
    instance_seed: int,
) -> ResolvedAngleProblem:
    """Bind the selected semantic branch to one answer-supported theorem case."""

    cases = _CASES_BY_BRANCH.get(str(branch_key))
    if not cases:
        raise ValueError(f"unsupported split-triangle angle branch: {branch_key}")
    case, case_index, answer_probabilities = _select_case_from_answer_support(
        cases=cases,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{branch_key}.case",
    )
    return ResolvedAngleProblem(
        branch_key=str(branch_key),
        case=case,
        branch_probabilities={str(key): float(value) for key, value in branch_probabilities.items()},
        answer_probabilities=dict(answer_probabilities),
        case_index=int(case_index),
    )


def _render_attempt(
    *,
    problem: ResolvedAngleProblem,
    render_defaults: Mapping[str, Any],
    params: Mapping[str, Any],
    instance_seed: int,
    max_attempts: int,
) -> RenderedAttempt:
    """Render one case with retries while preserving one final trace binding."""

    last_error: Exception | None = None
    for attempt in range(max(1, int(max_attempts))):
        try:
            attempt_seed = int(instance_seed) + int(attempt)
            context = create_render_context(
                instance_seed=int(attempt_seed),
                params=params,
                render_defaults=render_defaults,
            )
            rendered = draw_split_triangle_scene(
                case=problem.case,
                ctx=context,
                instance_seed=int(attempt_seed),
            )
            image, noise_meta = apply_post_image_noise(
                rendered.image,
                instance_seed=int(instance_seed),
                params=params,
                default_config=POST_IMAGE_NOISE_DEFAULTS,
            )
            annotation_artifacts = split_triangle_point_annotation(rendered)
            return RenderedAttempt(
                context=context,
                rendered=rendered,
                image=image,
                noise_meta=dict(noise_meta),
                annotation_artifacts=annotation_artifacts,
            )
        except Exception as exc:
            last_error = exc
            continue
    raise RuntimeError(f"failed to render {TASK_ID}") from last_error


def _trace_payload(
    *,
    problem: ResolvedAngleProblem,
    rendered_attempt: RenderedAttempt,
    prompt_artifacts: Any,
) -> dict[str, Any]:
    """Build trace sections from task-bound answer and annotation artifacts."""

    case = problem.case
    annotation_roles = [str(role) for role in rendered_attempt.annotation_artifacts.value.keys()]
    query_spec = build_prompt_query_spec(
        prompt_artifacts=prompt_artifacts,
        query_id=str(problem.branch_key),
        params={
            "scene_id": SCENE_ID,
            "query_id_probabilities": dict(problem.branch_probabilities),
            "answer_support_probabilities": dict(problem.answer_probabilities),
            "case_index": int(problem.case_index),
            "render_kind": str(case.render_kind),
            "relation": str(case.relation),
        },
    )
    query_spec["task_id"] = TASK_ID
    query_spec["scene_id"] = SCENE_ID
    trace_values = {
        "scene_id": SCENE_ID,
        "query_id": str(problem.branch_key),
        "query_id_probabilities": dict(problem.branch_probabilities),
        "answer_support_probabilities": dict(problem.answer_probabilities),
        "case_index": int(problem.case_index),
        "render_kind": str(case.render_kind),
        "relation": str(case.relation),
        "target_name": str(case.target_name),
        "variable_name": str(case.variable_name),
        "labels": dict(case.labels),
        "values": dict(case.values),
        "answer_type": "integer",
        "answer": int(case.answer),
        "annotation_roles": list(annotation_roles),
    }
    return {
        "scene_ir": {
            "domain": DOMAIN,
            "scene_kind": SCENE_KIND,
            "scene_id": SCENE_ID,
            "task_id": TASK_ID,
            "query_id": str(problem.branch_key),
            "entities": [
                {
                    "type": "split_triangle_diagram",
                    "scene_id": SCENE_ID,
                    "render_map": dict(rendered_attempt.rendered.render_map),
                },
            ],
            "relations": {
                "type": str(case.relation),
                "query_id": str(problem.branch_key),
                "answer_value": int(case.answer),
            },
        },
        "query_spec": query_spec,
        "render_spec": {
            "task_id": TASK_ID,
            "scene_id": SCENE_ID,
            "query_id": str(problem.branch_key),
            "canvas": {
                "width": int(rendered_attempt.context.width),
                "height": int(rendered_attempt.context.height),
            },
            "single_object_scene_rotation": dict(rendered_attempt.rendered.render_map.get("single_object_scene_rotation", {})),
            "style": {
                **dict(rendered_attempt.rendered.render_map.get("style", {})),
                "post_image_noise": dict(rendered_attempt.noise_meta),
            },
            "prompt": {
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            },
        },
        "render_map": dict(rendered_attempt.rendered.render_map),
        "execution_trace": dict(trace_values),
        "witness_symbolic": {
            "type": "split_triangle_angle_chase",
            "task_id": TASK_ID,
            **dict(trace_values),
        },
        "projected_annotation": dict(rendered_attempt.annotation_artifacts.projected_annotation),
    }


@register_task
class GeometrySplitTriangleAngleChaseTargetAngleValueTask:
    """Find the missing angle in one split-triangle theorem diagram."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        """Select the theorem branch, bind answer/annotation, and return output."""

        _generation_defaults, render_defaults, prompt_defaults = load_split_triangle_defaults(TASK_ID)
        branch_key, branch_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=SUPPORTED_QUERY_IDS[0],
            task_id=TASK_ID,
            namespace=f"{TASK_ID}.query",
        )
        problem = _prepare_problem(
            branch_key=str(branch_key),
            branch_probabilities=branch_probabilities,
            params=task_params,
            instance_seed=int(instance_seed),
        )
        rendered_attempt = _render_attempt(
            problem=problem,
            render_defaults=render_defaults,
            params=task_params,
            instance_seed=int(instance_seed),
            max_attempts=int(max_attempts),
        )
        prompt_artifacts = build_split_triangle_prompt_artifacts(
            prompt_defaults=prompt_defaults,
            prompt_branch_key=str(problem.branch_key),
            target_name=str(problem.case.target_name),
            annotation_roles=tuple(rendered_attempt.annotation_artifacts.value.keys()),
            answer_value=int(problem.case.answer),
            instance_seed=int(instance_seed),
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(problem.case.answer)),
            annotation_gt=TypedValue(
                type=rendered_attempt.annotation_artifacts.annotation_type,
                value=rendered_attempt.annotation_artifacts.value,
            ),
            image=rendered_attempt.image,
            image_id="img0",
            trace_payload=_trace_payload(
                problem=problem,
                rendered_attempt=rendered_attempt,
                prompt_artifacts=prompt_artifacts,
            ),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(problem.branch_key),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = [
    "GeometrySplitTriangleAngleChaseTargetAngleValueTask",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
]
