"""Find a target side length in a split-triangle trig-chain diagram."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import math
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

from .shared.annotations import split_triangle_trig_point_annotation
from .shared.defaults import (
    DOMAIN,
    POST_IMAGE_NOISE_DEFAULTS,
    SCENE_ID,
    SCENE_KIND,
    load_split_triangle_trig_defaults,
)
from .shared.prompts import build_split_triangle_trig_prompt_artifacts
from .shared.rendering import (
    RENDER_ALTITUDE_WITH_TWO_ANGLES,
    RENDER_ISOSCELES_ALTITUDE,
    RENDER_SIDE_TO_HYPOTENUSE,
    create_render_context,
    draw_split_triangle_trig_scene,
)
from .shared.state import DEGREE_SYMBOL, RenderContext, RenderedSplitTriangleTrigScene, SplitTriangleTrigCase

TASK_ID = "task_geometry__split_triangle_trig_chain__side_length_value"
SUPPORTED_QUERY_IDS: tuple[str, ...] = (
    "shared_altitude_two_angles_side",
    "shared_altitude_side_then_hypotenuse",
    "isosceles_altitude_trig_side",
)


@dataclass(frozen=True)
class ResolvedTrigProblem:
    """Task-bound trig case selected by query branch and answer support."""

    branch_key: str
    case: SplitTriangleTrigCase
    branch_probabilities: dict[str, float]
    answer_probabilities: dict[str, float]
    case_index: int


@dataclass(frozen=True)
class RenderedAttempt:
    """Rendered scene fields that must stay bound to one execution trace."""

    context: RenderContext
    rendered: RenderedSplitTriangleTrigScene
    image: Image.Image
    noise_meta: dict[str, Any]
    annotation_artifacts: PixelAnnotationArtifacts


def _num(value: float | int) -> float | int:
    rounded = round(float(value), 1)
    if abs(rounded - round(rounded)) < 1e-9:
        return int(round(rounded))
    return float(rounded)


def _answer_key(value: float | int) -> str:
    return f"{round(float(value), 1):.1f}"


def _angle_text(value: float | int) -> str:
    return f"{int(round(float(value)))}{DEGREE_SYMBOL}"


def _case(
    *,
    render_kind: str,
    answer: float,
    target_name: str,
    labels: Mapping[str, str],
    values: Mapping[str, float | int | str],
) -> SplitTriangleTrigCase:
    return SplitTriangleTrigCase(
        render_kind=str(render_kind),
        relation="split_triangle_trig_chain",
        answer=float(round(float(answer), 1)),
        target_name=str(target_name),
        labels=dict(labels),
        values=dict(values),
    )


def _add_unique_case(
    grouped: dict[str, list[SplitTriangleTrigCase]],
    seen_answers: set[str],
    *,
    branch_key: str,
    render_kind: str,
    answer: float,
    target_name: str,
    labels: Mapping[str, str],
    values: Mapping[str, float | int | str],
) -> None:
    """Append a construction only when it contributes a new rounded answer."""

    rounded_answer = float(round(float(answer), 1))
    if rounded_answer <= 0.0:
        return
    key = _answer_key(rounded_answer)
    if key in seen_answers:
        return
    seen_answers.add(key)
    grouped[str(branch_key)].append(
        _case(
            render_kind=str(render_kind),
            answer=rounded_answer,
            target_name=str(target_name),
            labels=dict(labels),
            values={**dict(values), "answer": rounded_answer},
        )
    )


def _build_cases() -> dict[str, tuple[SplitTriangleTrigCase, ...]]:
    """Build answer-supported trig cases, grouped by semantic branch."""

    grouped: dict[str, list[SplitTriangleTrigCase]] = defaultdict(list)
    seen_by_branch: dict[str, set[str]] = defaultdict(set)
    max_cases_per_branch = 80

    branch_key = "shared_altitude_two_angles_side"
    for known_base in range(7, 26):
        for left_angle in range(32, 68, 3):
            for right_angle in range(35, 68, 4):
                if len(grouped[branch_key]) >= max_cases_per_branch:
                    break
                altitude = float(known_base) * math.tan(math.radians(float(left_angle)))
                answer = altitude / math.sin(math.radians(float(right_angle)))
                if not 6.0 <= answer <= 80.0:
                    continue
                _add_unique_case(
                    grouped,
                    seen_by_branch[branch_key],
                    branch_key=branch_key,
                    render_kind=RENDER_ALTITUDE_WITH_TWO_ANGLES,
                    answer=answer,
                    target_name="AC",
                    labels={
                        "BD": str(_num(known_base)),
                        "angle_B": _angle_text(left_angle),
                        "angle_C": _angle_text(right_angle),
                        "AC": "?",
                    },
                    values={
                        "known_segment": "BD",
                        "known_value": int(known_base),
                        "left_angle": int(left_angle),
                        "right_angle": int(right_angle),
                        "altitude": round(float(altitude), 4),
                        "target_side": "AC",
                    },
                )
            if len(grouped[branch_key]) >= max_cases_per_branch:
                break
        if len(grouped[branch_key]) >= max_cases_per_branch:
            break

    branch_key = "shared_altitude_side_then_hypotenuse"
    for known_side in range(10, 34):
        for left_angle in range(32, 69, 4):
            for right_angle in range(35, 69, 5):
                if len(grouped[branch_key]) >= max_cases_per_branch:
                    break
                altitude = float(known_side) * math.sin(math.radians(float(left_angle)))
                answer = altitude / math.sin(math.radians(float(right_angle)))
                if not 5.0 <= answer <= 70.0:
                    continue
                _add_unique_case(
                    grouped,
                    seen_by_branch[branch_key],
                    branch_key=branch_key,
                    render_kind=RENDER_SIDE_TO_HYPOTENUSE,
                    answer=answer,
                    target_name="AC",
                    labels={
                        "AB": str(_num(known_side)),
                        "angle_B": _angle_text(left_angle),
                        "angle_C": _angle_text(right_angle),
                        "AC": "?",
                    },
                    values={
                        "known_segment": "AB",
                        "known_value": int(known_side),
                        "left_angle": int(left_angle),
                        "right_angle": int(right_angle),
                        "altitude": round(float(altitude), 4),
                        "target_side": "AC",
                    },
                )
            if len(grouped[branch_key]) >= max_cases_per_branch:
                break
        if len(grouped[branch_key]) >= max_cases_per_branch:
            break

    branch_key = "isosceles_altitude_trig_side"
    for half_base in range(5, 28):
        for base_angle in range(34, 69, 3):
            if len(grouped[branch_key]) >= max_cases_per_branch:
                break
            answer = float(half_base) / math.cos(math.radians(float(base_angle)))
            if not 6.0 <= answer <= 75.0:
                continue
            _add_unique_case(
                grouped,
                seen_by_branch[branch_key],
                branch_key=branch_key,
                render_kind=RENDER_ISOSCELES_ALTITUDE,
                answer=answer,
                target_name="AB",
                labels={
                    "BD": str(_num(half_base)),
                    "angle_B": _angle_text(base_angle),
                    "AB": "?",
                },
                values={
                    "known_segment": "BD",
                    "known_value": int(half_base),
                    "left_angle": int(base_angle),
                    "right_angle": int(base_angle),
                    "target_side": "AB",
                },
            )
        if len(grouped[branch_key]) >= max_cases_per_branch:
            break

    return {str(key): tuple(value) for key, value in grouped.items()}


_CASES_BY_BRANCH = _build_cases()


def _probability_map(values: Sequence[str], selected: str | None = None) -> dict[str, float]:
    resolved = tuple(str(value) for value in values)
    if not resolved:
        return {}
    if selected is not None:
        return {value: (1.0 if value == str(selected) else 0.0) for value in resolved}
    weight = 1.0 / float(len(resolved))
    return {value: float(weight) for value in resolved}


def _select_case_from_answer_support(
    *,
    cases: Sequence[SplitTriangleTrigCase],
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> tuple[SplitTriangleTrigCase, int, dict[str, float]]:
    """Choose a rounded target answer uniformly, then one compatible case."""

    grouped: dict[str, list[tuple[int, SplitTriangleTrigCase]]] = defaultdict(list)
    for index, case in enumerate(cases):
        grouped[_answer_key(case.answer)].append((int(index), case))
    if not grouped:
        raise ValueError("split-triangle trig case support must be non-empty")

    answer_support = tuple(sorted(grouped, key=lambda value: float(value)))
    forced_answer = params.get("answer")
    rng = spawn_rng(int(instance_seed), str(namespace))
    if forced_answer is not None:
        answer_key = _answer_key(float(forced_answer))
        if answer_key not in grouped:
            raise ValueError(f"unsupported split-triangle trig answer: {forced_answer}")
        answer_probabilities = _probability_map(answer_support, selected=answer_key)
    else:
        answer_key = answer_support[int(rng.randrange(len(answer_support)))]
        answer_probabilities = _probability_map(answer_support)

    compatible = tuple(grouped[answer_key])
    selected_index, selected_case = compatible[int(rng.randrange(len(compatible)))]
    return selected_case, int(selected_index), dict(answer_probabilities)


def _prepare_problem(
    *,
    branch_key: str,
    branch_probabilities: Mapping[str, float],
    params: Mapping[str, Any],
    instance_seed: int,
) -> ResolvedTrigProblem:
    """Bind the selected semantic branch to one answer-supported trig case."""

    cases = _CASES_BY_BRANCH.get(str(branch_key))
    if not cases:
        raise ValueError(f"unsupported split-triangle trig branch: {branch_key}")
    case, case_index, answer_probabilities = _select_case_from_answer_support(
        cases=cases,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{branch_key}.case",
    )
    return ResolvedTrigProblem(
        branch_key=str(branch_key),
        case=case,
        branch_probabilities={str(key): float(value) for key, value in branch_probabilities.items()},
        answer_probabilities=dict(answer_probabilities),
        case_index=int(case_index),
    )


def _render_attempt(
    *,
    problem: ResolvedTrigProblem,
    render_defaults: Mapping[str, Any],
    params: Mapping[str, Any],
    instance_seed: int,
    max_attempts: int,
) -> RenderedAttempt:
    """Render one trig case with retries while preserving trace binding."""

    last_error: Exception | None = None
    for attempt in range(max(1, int(max_attempts))):
        try:
            attempt_seed = int(instance_seed) + int(attempt)
            context = create_render_context(
                instance_seed=int(attempt_seed),
                params=params,
                render_defaults=render_defaults,
            )
            rendered = draw_split_triangle_trig_scene(
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
            annotation_artifacts = split_triangle_trig_point_annotation(rendered)
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
    problem: ResolvedTrigProblem,
    rendered_attempt: RenderedAttempt,
    prompt_artifacts: Any,
    answer_value: float | int,
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
        "answer_type": "number",
        "answer": answer_value,
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
                    "type": "split_triangle_trig_diagram",
                    "scene_id": SCENE_ID,
                    "render_map": dict(rendered_attempt.rendered.render_map),
                },
            ],
            "relations": {
                "type": str(case.relation),
                "query_id": str(problem.branch_key),
                "answer_value": answer_value,
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
            "type": "split_triangle_trig_chain",
            "task_id": TASK_ID,
            **dict(trace_values),
        },
        "projected_annotation": dict(rendered_attempt.annotation_artifacts.projected_annotation),
    }


@register_task
class GeometrySplitTriangleTrigChainSideLengthValueTask:
    """Find a side length from one split-triangle trigonometric construction."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        """Select the trig branch, bind answer/annotation, and return output."""

        _generation_defaults, render_defaults, prompt_defaults = load_split_triangle_trig_defaults(TASK_ID)
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
        answer_value = _num(problem.case.answer)
        prompt_artifacts = build_split_triangle_trig_prompt_artifacts(
            prompt_defaults=prompt_defaults,
            prompt_branch_key=str(problem.branch_key),
            target_name=str(problem.case.target_name),
            annotation_roles=tuple(rendered_attempt.annotation_artifacts.value.keys()),
            answer_value=answer_value,
            instance_seed=int(instance_seed),
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="number", value=answer_value),
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
                answer_value=answer_value,
            ),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(problem.branch_key),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = [
    "GeometrySplitTriangleTrigChainSideLengthValueTask",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
]
