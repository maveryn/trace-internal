"""Neutral scene lifecycle helpers for migrated function-graph tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions

from .shared.rendering import (
    finalize_graph_image,
    graph_context_and_canvas,
    graph_render_spec,
    render_count_graph,
    style_and_widths,
)
from .shared.prompts import function_object_description, prompt_artifacts_for_scene
from .shared.sampling import resolve_family_for_target, resolve_numeric_target, support_union
from .shared.state import RenderedFunctionGraph, SampledFunctionGraph


@dataclass(frozen=True)
class CountRenderArtifacts:
    """Rendered graph-count scene parts before public answer binding."""

    image: Any
    rendered_scene: RenderedFunctionGraph
    render_spec: Dict[str, Any]


@dataclass(frozen=True)
class CountOutputComponents:
    """Prompt, image, trace, and rendered scene before public TypedValue binding."""

    prompt: str
    prompt_variants: Dict[str, Any]
    image: Any
    rendered_scene: RenderedFunctionGraph
    trace_payload: Dict[str, Any]


@dataclass(frozen=True)
class FunctionGraphCountObjectivePlan:
    """Task-prepared objective plan consumed by neutral lifecycle plumbing."""

    family: str
    prompt_template_key: str
    prompt_defaults: Mapping[str, Any]
    prompt_slots: Mapping[str, Any]
    query_params: Mapping[str, Any]
    scene_relations: Mapping[str, Any]
    sampled_scene: SampledFunctionGraph
    execution_extra: Mapping[str, Any]


CountObjectivePreparer = Callable[
    [int, Mapping[str, Any], str, Mapping[str, float]],
    FunctionGraphCountObjectivePlan,
]
PromptSlotBuilder = Callable[[Mapping[str, Any], str, int], Mapping[str, Any]]
SampleBuilder = Callable[[Any, str, int], SampledFunctionGraph]
RelationBuilder = Callable[[str, int], Mapping[str, Any]]

REFERENCE_COUNT_PROMPT_KEYS = (
    "bundle_id",
    "scene_key",
    "task_key",
    "json_output_contract",
    "json_output_contract_answer_only",
    "answer_hint_integer",
    "annotation_hint_reference_line_crossing_count",
    "json_example_reference_line_crossing_count",
    "json_example_answer_only_reference_line_crossing_count",
    "reference_line_description_x_axis",
    "reference_line_description_horizontal_line",
)
TURNING_COUNT_PROMPT_KEYS = (
    "bundle_id",
    "scene_key",
    "task_key",
    "json_output_contract",
    "json_output_contract_answer_only",
    "answer_hint_integer",
    "annotation_hint_turning_point_count",
    "json_example_turning_point_count",
    "json_example_answer_only_turning_point_count",
)
LOCAL_EXTREMUM_PROMPT_KEYS = (
    "bundle_id",
    "scene_key",
    "task_key",
    "json_output_contract",
    "json_output_contract_answer_only",
    "answer_hint_integer",
    "annotation_hint_local_extremum_count",
    "json_example_local_extremum_count",
    "json_example_answer_only_local_extremum_count",
    "extremum_kind_adjective_minimum",
    "extremum_kind_adjective_maximum",
    "extremum_visual_description_minimum",
    "extremum_visual_description_maximum",
)

def render_count_scene_artifacts(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    sampled_scene: SampledFunctionGraph,
    family: str,
) -> CountRenderArtifacts:
    """Render one sampled graph scene without making task-specific decisions."""

    rng = spawn_rng(int(instance_seed), "function_graph.count.render")
    context, image, draw, background_meta = graph_context_and_canvas(
        rng,
        instance_seed=int(instance_seed),
        params=params,
    )
    line_width, guide_line_width, label_font_size_px, shape_style = style_and_widths(
        rng,
        params=params,
        context=context,
        background_meta=background_meta,
    )
    rendered_scene = render_count_graph(
        draw,
        context=context,
        sampled_scene=sampled_scene,
        shape_style=shape_style,
        line_width=int(line_width),
        guide_line_width=int(guide_line_width),
        label_font_size_px=int(label_font_size_px),
    )
    image, background_meta_final, post_noise_meta = finalize_graph_image(
        image,
        instance_seed=int(instance_seed),
        context=context,
        background_meta=background_meta,
    )
    return CountRenderArtifacts(
        image=image,
        rendered_scene=rendered_scene,
        render_spec=graph_render_spec(
            context=context,
            background_meta=background_meta_final,
            post_noise_meta=post_noise_meta,
            shape_style=shape_style,
            family=str(family),
        ),
    )


def count_trace_payload(
    *,
    scene_relations: Mapping[str, Any],
    branch_name: str,
    template_id: str,
    prompt_artifacts,
    query_params: Mapping[str, Any],
    render_spec: Mapping[str, Any],
    rendered_scene: RenderedFunctionGraph,
    execution_trace: Mapping[str, Any],
) -> Dict[str, Any]:
    """Assemble graph-count trace metadata from public task-owned fields."""

    return {
        "scene_ir": {
            "scene_id": "function_graph",
            "scene_kind": "geometry_function_graph",
            "entities": list(rendered_scene.scene_entities),
            "relations": dict(scene_relations),
        },
        "query_spec": {
            "query_id": str(branch_name),
            "template_id": str(template_id),
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": dict(query_params),
        },
        "render_spec": dict(render_spec),
        "render_map": dict(rendered_scene.render_map),
        "execution_trace": dict(execution_trace),
        "witness_symbolic": dict(rendered_scene.witness_symbolic),
        "projected_annotation": dict(rendered_scene.projected_annotation),
    }


def count_output_components(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    sampled_scene: SampledFunctionGraph,
    family: str,
    defaults: Mapping[str, Any],
    prompt_template_key: str,
    prompt_slots: Mapping[str, Any],
    branch_name: str,
    query_params: Mapping[str, Any],
    scene_relations: Mapping[str, Any],
    execution_trace: Mapping[str, Any],
) -> CountOutputComponents:
    """Render prompt/image/trace from public task-selected semantic fields."""

    render_artifacts = render_count_scene_artifacts(
        instance_seed=int(instance_seed),
        params=params,
        sampled_scene=sampled_scene,
        family=str(family),
    )
    prompt_artifacts = prompt_artifacts_for_scene(
        defaults=defaults,
        prompt_template_key=str(prompt_template_key),
        slots=prompt_slots,
        instance_seed=int(instance_seed),
    )
    trace_payload = count_trace_payload(
        scene_relations=scene_relations,
        branch_name=str(branch_name),
        template_id=str(defaults["bundle_id"]),
        prompt_artifacts=prompt_artifacts,
        query_params=query_params,
        render_spec=render_artifacts.render_spec,
        rendered_scene=render_artifacts.rendered_scene,
        execution_trace=execution_trace,
    )
    return CountOutputComponents(
        prompt=str(prompt_artifacts.prompt),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
        image=render_artifacts.image,
        rendered_scene=render_artifacts.rendered_scene,
        trace_payload=trace_payload,
    )


def run_function_graph_count_entry(
    *,
    task_id: str,
    supported_query_ids: tuple[str, ...],
    default_query_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
    prepare_objective: CountObjectivePreparer,
) -> TaskOutput:
    """Run a public count task from a task-owned objective plan."""

    del max_attempts
    branch_name, branch_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=supported_query_ids,
        default_query_id=str(default_query_id),
        task_id=str(task_id),
    )
    plan = prepare_objective(int(instance_seed), task_params, str(branch_name), branch_probabilities)
    components = count_output_components(
        instance_seed=int(instance_seed),
        params=task_params,
        sampled_scene=plan.sampled_scene,
        family=str(plan.family),
        defaults=plan.prompt_defaults,
        prompt_template_key=str(plan.prompt_template_key),
        prompt_slots=plan.prompt_slots,
        branch_name=str(branch_name),
        query_params=plan.query_params,
        scene_relations=plan.scene_relations,
        execution_trace={
            "query_id": str(branch_name),
            "answer_type": "integer",
            "answer_value": int(plan.sampled_scene.object_count),
            **dict(plan.query_params),
            **dict(plan.sampled_scene.execution_trace),
            **dict(plan.execution_extra),
        },
    )
    rendered_scene = components.rendered_scene
    answer_gt = TypedValue(type="integer", value=int(rendered_scene.answer_value))
    annotation_gt = TypedValue(
        type=str(rendered_scene.annotation_type),
        value=[list(point) for point in rendered_scene.annotation_value],
    )
    components.trace_payload["execution_trace"]["answer_value"] = int(answer_gt.value)
    components.trace_payload["execution_trace"]["required_annotation_labels"] = list(rendered_scene.required_annotation_labels)
    return TaskOutput(
        prompt=components.prompt,
        answer_gt=answer_gt,
        annotation_gt=annotation_gt,
        image=components.image,
        image_id="img0",
        trace_payload=components.trace_payload,
        task_versions=default_task_versions(),
        query_id=str(branch_name),
        prompt_variants=dict(components.prompt_variants),
    )


def prepare_function_graph_count_plan(
    *,
    instance_seed: int,
    task_params: Mapping[str, Any],
    task_id: str,
    branch_name: str,
    branch_probabilities: Mapping[str, float],
    support_by_family: Mapping[str, tuple[int, ...]],
    prompt_template_key: str,
    prompt_default_keys: tuple[str, ...],
    build_prompt_slots: PromptSlotBuilder,
    sample_scene: SampleBuilder,
    build_scene_relations: RelationBuilder,
    extra_query_params: Mapping[str, Any] | None = None,
    extra_execution: Mapping[str, Any] | None = None,
) -> FunctionGraphCountObjectivePlan:
    """Resolve common count target/family axes from task-provided semantics."""

    target_count, target_probs = resolve_numeric_target(
        instance_seed=int(instance_seed),
        params=task_params,
        support=support_union(support_by_family),
        namespace=f"{task_id}.target_count",
    )
    family, family_probs = resolve_family_for_target(
        instance_seed=int(instance_seed),
        params=task_params,
        support_by_family=support_by_family,
        target_count=int(target_count),
        namespace=f"{task_id}.family",
    )
    defaults = prompt_defaults_for_plan(tuple(prompt_default_keys), task_id=str(task_id))
    query_params = {
        "query_id": str(branch_name),
        "query_id_probabilities": dict(branch_probabilities),
        "target_count": int(target_count),
        "target_count_probabilities": dict(target_probs),
        "scene_variant": str(family),
        "scene_variant_probabilities": dict(family_probs),
        **dict(extra_query_params or {}),
    }
    return FunctionGraphCountObjectivePlan(
        family=str(family),
        prompt_template_key=str(prompt_template_key),
        prompt_defaults=defaults,
        prompt_slots=build_prompt_slots(defaults, str(family), int(target_count)),
        query_params=query_params,
        scene_relations=build_scene_relations(str(family), int(target_count)),
        sampled_scene=sample_scene(spawn_rng(int(instance_seed), f"{task_id}.scene"), str(family), int(target_count)),
        execution_extra={"target_count": int(target_count), **dict(extra_execution or {})},
    )


def prompt_defaults_for_plan(keys: tuple[str, ...], *, task_id: str) -> Mapping[str, Any]:
    """Load prompt defaults for a public function-graph task plan."""

    from .shared.prompts import prompt_defaults

    return prompt_defaults(keys, context=f"prompt defaults for {task_id}")


def integer_count_prompt_slots(
    defaults: Mapping[str, Any],
    *,
    object_description: str,
    annotation_hint: str,
    json_example: str,
    json_example_answer_only: str,
    reference_line_description: str = "",
    query_line_equation: str = "",
    extra_slots: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    """Assemble common integer-count prompt slots from task-owned semantics."""

    return {
        "object_description": str(object_description),
        "reference_line_description": str(reference_line_description),
        "query_line_equation": str(query_line_equation),
        "json_output_contract": str(defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(defaults["json_output_contract_answer_only"]),
        "annotation_hint": str(annotation_hint),
        "answer_hint": str(defaults["answer_hint_integer"]),
        "json_example": str(json_example),
        "json_example_answer_only": str(json_example_answer_only),
        **dict(extra_slots or {}),
    }


def local_extremum_count_prompt_slots(
    defaults: Mapping[str, Any],
    *,
    family: str,
    extremum_kind: str,
) -> Mapping[str, Any]:
    """Assemble local-extremum prompt slots from a task-selected extremum kind."""

    extremum_slots = {
        "extremum_kind_adjective": str(defaults[f"extremum_kind_adjective_{extremum_kind}"]),
        "extremum_visual_description": str(defaults[f"extremum_visual_description_{extremum_kind}"]),
    }
    return integer_count_prompt_slots(
        defaults,
        object_description=function_object_description(defaults=defaults, family=str(family), has_guide_line=False),
        annotation_hint=str(defaults["annotation_hint_local_extremum_count"]).format(**dict(extremum_slots)),
        json_example=str(defaults["json_example_local_extremum_count"]),
        json_example_answer_only=str(defaults["json_example_answer_only_local_extremum_count"]),
        extra_slots=extremum_slots,
    )
