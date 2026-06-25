"""Scene-private prompt and trace assembly for graph-paper public tasks."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Callable, Mapping, Sequence

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec

from .shared.annotations import (
    bbox_set_artifacts,
    point_set_artifacts,
    scalar_bbox_artifacts,
    scalar_point_artifacts,
    scalar_segment_artifacts,
)
from .shared.construction import (
    concave_polygon,
    pi_expression,
    polygon_area,
    polygon_perimeter,
    rectangle_points,
    regular_polygon,
    right_triangle_points,
)
from .shared.defaults import split_defaults_for
from .shared.prompts import prompt_defaults as resolve_prompt_defaults
from .shared.prompts import render_prompt_artifacts
from .shared.rendering import (
    angle_points,
    draw_angle,
    draw_ellipse_or_circle,
    draw_measurement_guide,
    draw_polygon,
    draw_segment,
    make_context,
    object_color,
    random_center_for_radii,
    random_shift_points,
    render_metadata,
    slot_centers,
)
from .shared.sampling import (
    choose_from_seed,
    count_target,
    label_subset,
    make_class_sequence,
    reduced_slope,
    resolve_count,
    rng_for,
    unique_metric_values,
)
from .shared.state import GraphObject, GraphPaperContext, Point, PromptPlan, SCENE_ID


@dataclass(frozen=True)
class GraphPaperComponents:
    """Prompt, image, annotation, and trace sections before final TaskOutput."""

    prompt: str
    prompt_variants: Mapping[str, str]
    annotation_type: str
    annotation_value: Any
    image: Any
    trace_payload: Mapping[str, Any]


@dataclass(frozen=True)
class GraphPaperTaskPlan:
    """Public-file semantic plan consumed by scene-private lifecycle plumbing."""

    builder: Callable[
        [Mapping[str, Any], "GraphPaperTaskPlan"],
        tuple[GraphPaperComponents, TypedValue],
    ]
    prompt_key: str
    salt: str
    default_branch: str = "single"
    value_param: str = ""
    target_field: str = ""
    prompt_keys_by_branch: Mapping[str, str] = field(default_factory=dict)
    role_by_branch: Mapping[str, str] = field(default_factory=dict)
    target_class_by_branch: Mapping[str, str] = field(default_factory=dict)
    target_text_by_branch: Mapping[str, str] = field(default_factory=dict)

    def prompt_key_for(self, branch_name: str) -> str:
        """Return the public-file prompt key for a selected branch."""

        if self.prompt_keys_by_branch:
            return str(self.prompt_keys_by_branch[str(branch_name)])
        return str(self.prompt_key)

    def role_for(self, branch_name: str) -> str:
        """Return a non-public lifecycle role for a selected branch."""

        if self.role_by_branch:
            return str(self.role_by_branch[str(branch_name)])
        return str(branch_name)

    def target_class_for(self, branch_name: str, fallback: str) -> str:
        """Return the semantic target class owned by the selected branch."""

        if self.target_class_by_branch:
            return str(self.target_class_by_branch[str(branch_name)])
        return str(fallback)

    def target_text_for(self, branch_name: str, fallback: str) -> str:
        """Return the prompt-facing target phrase for the selected branch."""

        if self.target_text_by_branch:
            return str(self.target_text_by_branch[str(branch_name)])
        return str(fallback)


def graph_paper_prompt_plan(
    *,
    prompt_defaults: Mapping[str, Any],
    prompt_key: str,
    answer_hint: str,
    annotation_hint: str,
    json_example: str,
    json_example_answer_only: str,
    shape_text: str = "",
    metric_text: str = "",
    target_text: str = "",
) -> PromptPlan:
    """Create one prompt plan from config defaults and task-owned dynamic slots."""

    bundle_id, scene_key, task_key = resolve_prompt_defaults(prompt_defaults)
    return PromptPlan(
        bundle_id=str(bundle_id),
        scene_key=str(scene_key),
        task_key=str(task_key),
        prompt_key=str(prompt_key),
        answer_hint=str(answer_hint),
        annotation_hint=str(annotation_hint),
        json_example=str(json_example),
        json_example_answer_only=str(json_example_answer_only),
        shape_text=str(shape_text),
        metric_text=str(metric_text),
        target_text=str(target_text),
    )


def object_trace(entity: GraphObject) -> dict[str, Any]:
    """Serialize one graph object for scene trace metadata."""

    payload: dict[str, Any] = {
        "label": str(entity.label),
        "kind": str(entity.kind),
        "class_name": str(entity.class_name),
        "bbox_px": [round(float(value), 3) for value in entity.bbox_px],
        "points_px": [
            [round(float(coord), 3) for coord in point] for point in entity.points_px
        ],
        "metric_value": round(float(entity.metric_value), 6),
    }
    if entity.graph_points:
        payload["graph_points"] = [
            [round(float(coord), 3) for coord in point] for point in entity.graph_points
        ]
    if entity.extra:
        payload["extra"] = dict(entity.extra)
    return payload


def build_graph_paper_components(
    *,
    ctx: GraphPaperContext,
    prompt_plan: PromptPlan,
    instance_seed: int,
    branch_name: str,
    branch_probabilities: Mapping[str, float],
    task_name: str,
    answer_type: str,
    answer_value: Any,
    annotation_type: str,
    annotation_value: Any,
    projected_annotation: Mapping[str, Any],
    witness_symbolic: Mapping[str, Any],
    objects: Sequence[GraphObject],
    prompt_key: str,
    program_code: str,
    scene_kind: str,
    semantic_args: Mapping[str, Any],
    task_params: Mapping[str, Any],
    render_map: Mapping[str, Any] | None = None,
) -> GraphPaperComponents:
    """Assemble common graph-paper prompt and trace payload sections."""

    prompt_artifacts = render_prompt_artifacts(
        plan=prompt_plan, instance_seed=int(instance_seed)
    )
    probabilities = {
        str(key): float(value) for key, value in branch_probabilities.items()
    }
    query_spec = build_prompt_query_spec(
        prompt_artifacts=prompt_artifacts,
        query_id=str(branch_name),
        params={
            "scene_id": SCENE_ID,
            "query_id_probabilities": dict(probabilities),
            "prompt_key": str(prompt_key),
            "program_code": str(program_code),
            **{str(key): value for key, value in semantic_args.items()},
        },
    )
    render_spec = render_metadata(ctx)
    trace_payload = {
        "scene_ir": {
            "scene_id": SCENE_ID,
            "scene_kind": str(scene_kind),
            "entities": [object_trace(entity) for entity in objects],
            "relations": {
                "answer_value": answer_value,
                "answer_type": str(answer_type),
                "annotation_type": str(annotation_type),
                "program_code": str(program_code),
                **{str(key): value for key, value in semantic_args.items()},
            },
        },
        "query_spec": query_spec,
        "render_spec": render_spec,
        "render_map": dict(render_map or {}),
        "projected_annotation": dict(projected_annotation),
        "witness_symbolic": dict(witness_symbolic),
        "execution_trace": {
            "scene_id": SCENE_ID,
            "query_id": str(branch_name),
            "query_id_probabilities": dict(probabilities),
            "prompt_key": str(prompt_key),
            "program_code": str(program_code),
            "answer_type": str(answer_type),
            "answer_value": answer_value,
            "annotation_type": str(annotation_type),
            "task_params": {
                str(key): value
                for key, value in task_params.items()
                if not str(key).startswith("_")
            },
            **{str(key): value for key, value in semantic_args.items()},
        },
    }
    return GraphPaperComponents(
        prompt=str(prompt_artifacts.prompt),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
        annotation_type=str(annotation_type),
        annotation_value=annotation_value,
        image=ctx.image,
        trace_payload=trace_payload,
    )


def _final_output(
    *,
    components: GraphPaperComponents,
    answer_gt: TypedValue,
    branch_name: str,
) -> TaskOutput:
    """Build the final task output once a public entrypoint has selected semantics."""

    return TaskOutput(
        prompt=str(components.prompt),
        answer_gt=answer_gt,
        annotation_gt=TypedValue(
            type=str(components.annotation_type), value=components.annotation_value
        ),
        image=components.image,
        image_id="img_0",
        trace_payload=dict(components.trace_payload),
        task_versions=default_task_versions(),
        scene_id=SCENE_ID,
        query_id=str(branch_name),
        prompt_variants=dict(components.prompt_variants),
    )


def _select_branch(
    task: Any, instance_seed: int, params: Mapping[str, Any], default_branch: str
):
    """Resolve the public branch using the task-owned supported branch tuple."""

    return select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=tuple(str(value) for value in task.supported_query_ids),
        default_query_id=str(default_branch),
        task_id=str(task.task_id),
    )


def _task_defaults(
    task: Any,
) -> tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]:
    """Resolve scene defaults for the public entrypoint."""

    return split_defaults_for(str(task.task_id))


def _make_prompt(
    prompt_defaults: Mapping[str, Any],
    *,
    prompt_key: str,
    answer_hint: str,
    annotation_hint: str,
    json_example: str,
    json_example_answer_only: str,
    shape_text: str = "",
    metric_text: str = "",
    target_text: str = "",
) -> PromptPlan:
    """Bind task-specific prompt slots without embedding prompt templates in source."""

    return graph_paper_prompt_plan(
        prompt_defaults=prompt_defaults,
        prompt_key=str(prompt_key),
        answer_hint=str(answer_hint),
        annotation_hint=str(annotation_hint),
        json_example=str(json_example),
        json_example_answer_only=str(json_example_answer_only),
        shape_text=str(shape_text),
        metric_text=str(metric_text),
        target_text=str(target_text),
    )


def run_graph_paper_entry(
    task: Any,
    instance_seed: int,
    *,
    params: Mapping[str, Any],
    max_attempts: int,
    plan: GraphPaperTaskPlan,
) -> TaskOutput:
    """Run one graph-paper task from the semantic plan owned by the public file."""

    del max_attempts
    branch_name, branch_probabilities, task_params = _select_branch(
        task,
        int(instance_seed),
        params,
        str(plan.default_branch),
    )
    generation_defaults, rendering_defaults, prompt_defaults = _task_defaults(task)
    context = {
        "instance_seed": int(instance_seed),
        "branch_name": str(branch_name),
        "branch_probabilities": dict(branch_probabilities),
        "task_params": dict(task_params),
        "generation_defaults": generation_defaults,
        "rendering_defaults": rendering_defaults,
        "prompt_defaults": prompt_defaults,
    }
    components, answer_gt = plan.builder(context, plan)
    return _final_output(
        components=components, answer_gt=answer_gt, branch_name=str(branch_name)
    )


def _new_context(
    context: Mapping[str, Any], salt: str
) -> tuple[Any, GraphPaperContext]:
    """Create deterministic RNG and graph-paper context for one semantic role."""

    rng = rng_for(int(context["instance_seed"]), str(salt))
    ctx = make_context(
        instance_seed=int(context["instance_seed"]),
        params=dict(context["task_params"]),
        defaults=context["rendering_defaults"],
        theme_index=rng.randrange(0, 3),
    )
    return rng, ctx


def _component_payload(
    context: Mapping[str, Any],
    *,
    ctx: GraphPaperContext,
    prompt_plan: PromptPlan,
    answer_type: str,
    answer_value: Any,
    annotation_type: str,
    annotation_value: Any,
    projected_annotation: Mapping[str, Any],
    witness_symbolic: Mapping[str, Any],
    objects: Sequence[GraphObject],
    prompt_key: str,
    program_code: str,
    scene_kind: str,
    semantic_args: Mapping[str, Any],
) -> tuple[GraphPaperComponents, TypedValue]:
    """Create components plus the typed answer for one graph-paper objective."""

    components = build_graph_paper_components(
        ctx=ctx,
        prompt_plan=prompt_plan,
        instance_seed=int(context["instance_seed"]),
        branch_name=str(context["branch_name"]),
        branch_probabilities=context["branch_probabilities"],
        task_name="",
        answer_type=str(answer_type),
        answer_value=answer_value,
        annotation_type=str(annotation_type),
        annotation_value=annotation_value,
        projected_annotation=projected_annotation,
        witness_symbolic=witness_symbolic,
        objects=objects,
        prompt_key=str(prompt_key),
        program_code=str(program_code),
        scene_kind=str(scene_kind),
        semantic_args=semantic_args,
        task_params=context["task_params"],
    )
    return components, TypedValue(type=str(answer_type), value=answer_value)


def _integer_shift_points(
    ctx: GraphPaperContext,
    points: Sequence[Point],
    rng: Any,
    *,
    margin_units: float = 1.0,
) -> tuple[Point, ...]:
    """Translate integer graph points by an integer in-bounds offset."""

    return random_shift_points(
        ctx,
        points,
        rng,
        margin_units=float(margin_units),
        step=1.0,
    )


def _corner_rectangle_points(width: int, height: int) -> tuple[Point, ...]:
    """Return integer-lattice rectangle vertices from the origin corner."""

    return (
        (0.0, 0.0),
        (float(width), 0.0),
        (float(width), float(height)),
        (0.0, float(height)),
    )


def _corner_right_triangle_points(width: int, height: int) -> tuple[Point, ...]:
    """Return integer-lattice right-triangle vertices from the origin corner."""

    return ((0.0, 0.0), (float(width), 0.0), (0.0, float(height)))


def _corner_parallelogram_points(
    base_width: int,
    side_dx: int,
    side_dy: int,
) -> tuple[Point, ...]:
    """Return integer-lattice slanted parallelogram vertices from the origin."""

    return (
        (0.0, 0.0),
        (float(base_width), 0.0),
        (float(base_width + side_dx), float(side_dy)),
        (float(side_dx), float(side_dy)),
    )


def _translated_corner_shape(
    *,
    left: int,
    bottom: int,
    width: int,
    height: int,
    shape_kind: str,
) -> tuple[Point, ...]:
    """Return an integer-lattice rectangle or right triangle near a slot."""

    base = (
        _corner_right_triangle_points(width, height)
        if str(shape_kind) == "right_triangle"
        else _corner_rectangle_points(width, height)
    )
    return tuple(
        (float(point[0]) + float(left), float(point[1]) + float(bottom))
        for point in base
    )


def _slot_anchor(
    ctx: GraphPaperContext,
    center: Point,
    *,
    width: int,
    height: int,
    margin_units: float = 1.0,
) -> tuple[int, int]:
    """Snap a slot center to an integer-lattice lower-left anchor in bounds."""

    limit = int(float(ctx.graph_half_range) - float(margin_units))
    lower = -limit
    left = int(round(float(center[0]) - (float(width) / 2.0)))
    bottom = int(round(float(center[1]) - (float(height) / 2.0)))
    left = max(lower, min(limit - int(width), left))
    bottom = max(lower, min(limit - int(height), bottom))
    return left, bottom


def _build_line_slope_value(
    context: Mapping[str, Any], plan: GraphPaperTaskPlan
) -> tuple[GraphPaperComponents, TypedValue]:
    """Build and bind one segment slope measurement from grid rise/run."""

    task_params = dict(context["task_params"])
    rng, ctx = _new_context(context, plan.salt)
    dx = int(task_params.get("dx", rng.choice([2, 3, 4, 5, 6])))
    dy = int(task_params.get("dy", rng.choice([-5, -4, -3, -2, 2, 3, 4, 5])))
    if dy == 0:
        dy = 2
    reduced_dy, reduced_dx = reduced_slope(dy, dx)
    start, end = _integer_shift_points(
        ctx,
        ((0.0, 0.0), (float(dx), float(dy))),
        rng,
        margin_units=1.2,
    )
    segment = draw_segment(ctx, "", start, end, color=ctx.accent_color)
    annotation_value, projected = scalar_segment_artifacts(
        segment.points_px[0], segment.points_px[1]
    )
    answer_value = round(float(dy) / float(dx), 2)
    prompt_plan = _make_prompt(
        context["prompt_defaults"],
        prompt_key=plan.prompt_key_for(str(context["branch_name"])),
        answer_hint='set "answer" to the slope as a number',
        annotation_hint='set "annotation" to the line segment as [[x0,y0],[x1,y1]] in pixels',
        json_example='{"annotation":[[210,420],[460,250]],"answer":-1.5}',
        json_example_answer_only='{"answer":-1.5}',
        target_text="the line segment",
        metric_text="slope",
    )
    return _component_payload(
        context,
        ctx=ctx,
        prompt_plan=prompt_plan,
        answer_type="number",
        answer_value=float(answer_value),
        annotation_type="segment",
        annotation_value=annotation_value,
        projected_annotation=projected,
        witness_symbolic={
            "segment": [start, end],
            "reduced_slope": [int(reduced_dy), int(reduced_dx)],
        },
        objects=(segment,),
        prompt_key=plan.prompt_key_for(str(context["branch_name"])),
        program_code="single_segment.slope_value",
        scene_kind="geometry_graph_paper_single_segment",
        semantic_args={"dx": int(dx), "dy": int(dy)},
    )


def _build_circle_circumference_value(
    context: Mapping[str, Any], plan: GraphPaperTaskPlan
) -> tuple[GraphPaperComponents, TypedValue]:
    """Build the exact circle circumference objective."""

    task_params = dict(context["task_params"])
    rng, ctx = _new_context(context, plan.salt)
    radius = int(task_params.get("radius", rng.randint(2, 5)))
    answer_value = pi_expression(2 * radius)
    center = random_center_for_radii(
        ctx, radius, radius, rng, margin_units=1.2, step=1.0
    )
    radius_endpoint = (float(center[0]) + float(radius), float(center[1]))
    circle = draw_ellipse_or_circle(
        ctx,
        "",
        center,
        radius,
        radius,
        class_name="circle",
        color=ctx.accent_color,
        filled=False,
    )
    draw_measurement_guide(ctx, center, radius_endpoint)
    annotation_value, projected = scalar_bbox_artifacts(circle.bbox_px)
    prompt_plan = _make_prompt(
        context["prompt_defaults"],
        prompt_key=plan.prompt_key_for(str(context["branch_name"])),
        answer_hint='set "answer" to the exact circumference using π',
        annotation_hint='set "annotation" to the circle bounding box [x0,y0,x1,y1] in pixels',
        json_example='{"annotation":[180,180,540,540],"answer":"8π"}',
        json_example_answer_only='{"answer":"8π"}',
        target_text="the circle",
        metric_text="circumference",
    )
    return _component_payload(
        context,
        ctx=ctx,
        prompt_plan=prompt_plan,
        answer_type="string",
        answer_value=str(answer_value),
        annotation_type="bbox",
        annotation_value=annotation_value,
        projected_annotation=projected,
        witness_symbolic={
            "center": center,
            "radius_endpoint": radius_endpoint,
            "radius_units": int(radius),
        },
        objects=(circle,),
        prompt_key=plan.prompt_key_for(str(context["branch_name"])),
        program_code="circle.radius_to_circumference_exact_pi",
        scene_kind="geometry_graph_paper_single_circle",
        semantic_args={"radius_units": int(radius)},
    )


def _build_ellipse_area_value(
    context: Mapping[str, Any], plan: GraphPaperTaskPlan
) -> tuple[GraphPaperComponents, TypedValue]:
    """Build the exact ellipse area objective."""

    task_params = dict(context["task_params"])
    rng, ctx = _new_context(context, plan.salt)
    if "radius_x" in task_params and "radius_y" in task_params:
        radius_x = int(task_params["radius_x"])
        radius_y = int(task_params["radius_y"])
    else:
        candidate_pairs = [
            (radius_x, radius_y)
            for radius_x in range(2, 7)
            for radius_y in range(1, 6)
            if radius_x != radius_y
        ]
        candidate_products = sorted(
            {radius_x * radius_y for radius_x, radius_y in candidate_pairs}
        )
        target_product = int(rng.choice(candidate_products))
        radius_x, radius_y = rng.choice(
            [(rx, ry) for rx, ry in candidate_pairs if rx * ry == target_product]
        )
    answer_value = pi_expression(radius_x * radius_y)
    center = random_center_for_radii(
        ctx, radius_x, radius_y, rng, margin_units=1.2, step=1.0
    )
    major_axis = (
        (float(center[0]) - float(radius_x), float(center[1])),
        (float(center[0]) + float(radius_x), float(center[1])),
    )
    minor_axis = (
        (float(center[0]), float(center[1]) - float(radius_y)),
        (float(center[0]), float(center[1]) + float(radius_y)),
    )
    ellipse = draw_ellipse_or_circle(
        ctx,
        "",
        center,
        radius_x,
        radius_y,
        class_name="ellipse",
        color=ctx.accent_color,
        filled=False,
    )
    draw_measurement_guide(ctx, major_axis[0], major_axis[1])
    draw_measurement_guide(ctx, minor_axis[0], minor_axis[1])
    annotation_value, projected = scalar_bbox_artifacts(ellipse.bbox_px)
    prompt_plan = _make_prompt(
        context["prompt_defaults"],
        prompt_key=plan.prompt_key_for(str(context["branch_name"])),
        answer_hint='set "answer" to the exact area using π',
        annotation_hint='set "annotation" to the ellipse bounding box [x0,y0,x1,y1] in pixels',
        json_example='{"annotation":[160,230,560,500],"answer":"12π"}',
        json_example_answer_only='{"answer":"12π"}',
        target_text="the ellipse",
        metric_text="area",
    )
    return _component_payload(
        context,
        ctx=ctx,
        prompt_plan=prompt_plan,
        answer_type="string",
        answer_value=str(answer_value),
        annotation_type="bbox",
        annotation_value=annotation_value,
        projected_annotation=projected,
        witness_symbolic={
            "center": center,
            "major_axis": major_axis,
            "minor_axis": minor_axis,
            "radius_x_units": int(radius_x),
            "radius_y_units": int(radius_y),
        },
        objects=(ellipse,),
        prompt_key=plan.prompt_key_for(str(context["branch_name"])),
        program_code="ellipse.radii_to_area_exact_pi",
        scene_kind="geometry_graph_paper_single_ellipse",
        semantic_args={
            "radius_x_units": int(radius_x),
            "radius_y_units": int(radius_y),
        },
    )


def _single_polygon_points(
    context: Mapping[str, Any], *, salt: str, perimeter_mode: bool = False
):
    """Sample one graph-paper polygon for a measurement task."""

    task_params = dict(context["task_params"])
    rng = rng_for(int(context["instance_seed"]), str(salt))
    shapes = ("rectangle", "right_triangle", "parallelogram")
    shape_kind = str(
        task_params.get(
            "shape_kind",
            choose_from_seed(
                shapes, instance_seed=int(context["instance_seed"]), salt=str(salt)
            ),
        )
    )
    if shape_kind == "right_triangle_3_4_5":
        shape_kind = "right_triangle"
    if shape_kind == "parallelogram":
        base_width = int(task_params.get("base_width", rng.randint(3, 6)))
        side_dx, side_dy = (
            (3, 4)
            if int(rng.randrange(0, 2)) == 0
            else (4, 3)
        )
        if "side_dx" in task_params and "side_dy" in task_params:
            side_dx = int(task_params["side_dx"])
            side_dy = int(task_params["side_dy"])
        return (
            _corner_parallelogram_points(base_width, side_dx, side_dy),
            "parallelogram",
        )
    width = int(task_params.get("width", rng.randint(3, 6)))
    height = int(task_params.get("height", rng.randint(3, 6)))
    if shape_kind == "right_triangle":
        if perimeter_mode:
            scale = int(task_params.get("scale", rng.choice([1, 2])))
            return (
                _corner_right_triangle_points(3 * scale, 4 * scale),
                "right triangle",
            )
        for _ in range(20):
            if (width * height) % 2 == 0:
                break
            width = int(rng.randint(3, 6))
            height = int(rng.randint(3, 6))
        if (width * height) % 2 != 0:
            width += 1
        return _corner_right_triangle_points(width, height), "right triangle"
    return _corner_rectangle_points(width, height), "rectangle"


def _build_polygon_area_value(
    context: Mapping[str, Any], plan: GraphPaperTaskPlan
) -> tuple[GraphPaperComponents, TypedValue]:
    """Build and bind one lattice polygon area measurement objective."""

    rng, ctx = _new_context(context, plan.salt)
    points, shape_text = _single_polygon_points(context, salt="area_shape")
    points = _integer_shift_points(ctx, points, rng, margin_units=1.2)
    answer_value = int(round(polygon_area(points)))
    polygon = draw_polygon(
        ctx,
        "",
        points,
        class_name=shape_text.replace(" ", "_"),
        color=ctx.accent_color,
        filled=False,
    )
    annotation_value, projected = point_set_artifacts(polygon.points_px)
    prompt_plan = _make_prompt(
        context["prompt_defaults"],
        prompt_key=plan.prompt_key_for(str(context["branch_name"])),
        answer_hint='set "answer" to the integer area in square grid units',
        annotation_hint='set "annotation" to the polygon vertices as pixel points',
        json_example='{"annotation":[[250,420],[460,420],[250,270]],"answer":12}',
        json_example_answer_only='{"answer":12}',
        shape_text=shape_text,
        target_text="the polygon",
        metric_text="area",
    )
    return _component_payload(
        context,
        ctx=ctx,
        prompt_plan=prompt_plan,
        answer_type="integer",
        answer_value=int(answer_value),
        annotation_type="point_set",
        annotation_value=annotation_value,
        projected_annotation=projected,
        witness_symbolic={"shape_kind": shape_text, "vertices": points},
        objects=(polygon,),
        prompt_key=plan.prompt_key_for(str(context["branch_name"])),
        program_code="lattice_polygon.area_value",
        scene_kind="geometry_graph_paper_single_polygon",
        semantic_args={"shape_kind": shape_text},
    )


def _build_polygon_perimeter_value(
    context: Mapping[str, Any], plan: GraphPaperTaskPlan
) -> tuple[GraphPaperComponents, TypedValue]:
    """Build and bind one lattice polygon perimeter measurement objective."""

    rng, ctx = _new_context(context, plan.salt)
    points, shape_text = _single_polygon_points(
        context, salt="perim_shape", perimeter_mode=True
    )
    points = _integer_shift_points(ctx, points, rng, margin_units=1.2)
    answer_value = int(round(polygon_perimeter(points)))
    polygon = draw_polygon(
        ctx,
        "",
        points,
        class_name=shape_text.replace(" ", "_"),
        color=ctx.accent_color,
        filled=False,
    )
    annotation_value, projected = point_set_artifacts(polygon.points_px)
    prompt_plan = _make_prompt(
        context["prompt_defaults"],
        prompt_key=plan.prompt_key_for(str(context["branch_name"])),
        answer_hint='set "answer" to the integer perimeter in grid units',
        annotation_hint='set "annotation" to the polygon vertices as pixel points',
        json_example='{"annotation":[[250,420],[460,420],[250,270]],"answer":12}',
        json_example_answer_only='{"answer":12}',
        shape_text=shape_text,
        target_text="the polygon",
        metric_text="perimeter",
    )
    return _component_payload(
        context,
        ctx=ctx,
        prompt_plan=prompt_plan,
        answer_type="integer",
        answer_value=int(answer_value),
        annotation_type="point_set",
        annotation_value=annotation_value,
        projected_annotation=projected,
        witness_symbolic={"shape_kind": shape_text, "vertices": points},
        objects=(polygon,),
        prompt_key=plan.prompt_key_for(str(context["branch_name"])),
        program_code="lattice_polygon.perimeter_value",
        scene_kind="geometry_graph_paper_single_polygon",
        semantic_args={"shape_kind": shape_text},
    )


def _build_angle_extremum_label(
    context: Mapping[str, Any], plan: GraphPaperTaskPlan
) -> tuple[GraphPaperComponents, TypedValue]:
    """Render labeled angles and bind the selected extremum annotation."""

    rng, ctx = _new_context(context, plan.salt)
    object_count = min(
        6,
        resolve_count(
            context["task_params"], context["generation_defaults"], fallback=6
        ),
    )
    labels = label_subset(object_count)
    values = unique_metric_values(rng, count=object_count, low=35, high=150)
    objects = []
    for index, (label, value, center) in enumerate(
        zip(
            labels,
            values,
            slot_centers(ctx, object_count, rng=rng, footprint_units=2.0),
            strict=True,
        )
    ):
        obj = draw_angle(
            ctx,
            label,
            angle_points(center, float(value), radius=2.35),
            color=object_color(ctx, index),
        )
        objects.append(replace(obj, metric_value=float(value)))
    winner = (
        max(objects, key=lambda item: item.metric_value)
        if plan.role_for(str(context["branch_name"])) == "max"
        else min(objects, key=lambda item: item.metric_value)
    )
    annotation_value, projected = scalar_point_artifacts(winner.points_px[1])
    branch_name = str(context["branch_name"])
    prompt_plan = _make_prompt(
        context["prompt_defaults"],
        prompt_key=plan.prompt_key_for(branch_name),
        answer_hint='set "answer" to the selected angle label as a capital letter shown in the image',
        annotation_hint='set "annotation" to the selected angle vertex point [x,y] in pixels',
        json_example='{"annotation":[330,320],"answer":"B"}',
        json_example_answer_only='{"answer":"B"}',
        target_text=f"{branch_name} angle",
        metric_text="angle measure",
    )
    return _component_payload(
        context,
        ctx=ctx,
        prompt_plan=prompt_plan,
        answer_type="option_letter",
        answer_value=str(winner.label),
        annotation_type="point",
        annotation_value=annotation_value,
        projected_annotation=projected,
        witness_symbolic={
            "selected_label": str(winner.label),
            "angle_degrees": int(winner.metric_value),
        },
        objects=tuple(objects),
        prompt_key=plan.prompt_key_for(branch_name),
        program_code="labeled_angles.extremum_label",
        scene_kind="geometry_graph_paper_labeled_angles",
        semantic_args={"extremum": branch_name, "object_count": int(object_count)},
    )


def _build_length_extremum_label(
    context: Mapping[str, Any], plan: GraphPaperTaskPlan
) -> tuple[GraphPaperComponents, TypedValue]:
    """Build the labeled-segment length extremum objective."""

    rng, ctx = _new_context(context, plan.salt)
    object_count = min(
        6,
        resolve_count(
            context["task_params"], context["generation_defaults"], fallback=6
        ),
    )
    labels = label_subset(object_count)
    vector_candidates = [
        (2, 0),
        (3, 0),
        (4, 0),
        (0, 2),
        (0, 3),
        (0, 4),
        (2, 1),
        (1, 2),
        (3, 1),
        (1, 3),
        (2, 2),
        (3, 2),
        (2, 3),
        (4, 1),
        (1, 4),
        (4, 2),
        (2, 4),
    ]
    rng.shuffle(vector_candidates)
    values: list[tuple[int, int, int]] = []
    used_squares: set[int] = set()
    for dx, dy in vector_candidates:
        square = int(dx * dx + dy * dy)
        if square in used_squares:
            continue
        used_squares.add(square)
        values.append((int(dx), int(dy), square))
        if len(values) == object_count:
            break
    if values and not any(dx != 0 and dy != 0 for dx, dy, _square in values):
        for dx, dy in vector_candidates:
            square = int(dx * dx + dy * dy)
            if dx != 0 and dy != 0 and square not in {
                value[2] for value in values[:-1]
            }:
                values[-1] = (int(dx), int(dy), square)
                break
    objects = []
    for index, (label, (dx, dy, square)) in enumerate(
        zip(labels, values, strict=True)
    ):
        start, end = _integer_shift_points(
            ctx,
            ((0.0, 0.0), (float(dx), float(dy))),
            rng,
            margin_units=1.2,
        )
        obj = draw_segment(ctx, label, start, end, color=object_color(ctx, index))
        objects.append(
            replace(
                obj,
                metric_value=float(square),
                extra={"dx": int(dx), "dy": int(dy), "length_squared": int(square)},
            )
        )
    winner = (
        max(objects, key=lambda item: item.metric_value)
        if plan.role_for(str(context["branch_name"])) == "max"
        else min(objects, key=lambda item: item.metric_value)
    )
    annotation_value, projected = scalar_segment_artifacts(
        winner.points_px[0], winner.points_px[1]
    )
    branch_name = str(context["branch_name"])
    prompt_plan = _make_prompt(
        context["prompt_defaults"],
        prompt_key=plan.prompt_key_for(branch_name),
        answer_hint='set "answer" to the selected segment label as a capital letter shown in the image',
        annotation_hint='set "annotation" to the selected segment as [[x0,y0],[x1,y1]] in pixels',
        json_example='{"annotation":[[210,420],[460,420]],"answer":"B"}',
        json_example_answer_only='{"answer":"B"}',
        target_text=f"{branch_name} segment",
        metric_text="length",
    )
    return _component_payload(
        context,
        ctx=ctx,
        prompt_plan=prompt_plan,
        answer_type="option_letter",
        answer_value=str(winner.label),
        annotation_type="segment",
        annotation_value=annotation_value,
        projected_annotation=projected,
        witness_symbolic={
            "selected_label": str(winner.label),
            "relative_length_squared": int(winner.metric_value),
        },
        objects=tuple(objects),
        prompt_key=plan.prompt_key_for(branch_name),
        program_code="labeled_segments.length_extremum_label",
        scene_kind="geometry_graph_paper_labeled_segments",
        semantic_args={"extremum": branch_name, "object_count": int(object_count)},
    )


def _shape_extremum_objects(
    context: Mapping[str, Any], plan: GraphPaperTaskPlan, metric: str
):
    """Sample and render same-family shape objects for area/perimeter ranking."""

    rng, ctx = _new_context(context, plan.salt)
    object_count = min(
        6,
        resolve_count(
            context["task_params"], context["generation_defaults"], fallback=6
        ),
    )
    labels = label_subset(object_count)
    shape_kind = str(
        dict(context["task_params"]).get(
            "shape_kind",
            choose_from_seed(
                ("rectangle", "right_triangle"),
                instance_seed=int(context["instance_seed"]),
                salt=f"{metric}_extremum_shape",
            ),
        )
    )
    objects = []
    used_values: set[int] = set()
    for index, (label, center) in enumerate(
        zip(
            labels,
            slot_centers(ctx, object_count, rng=rng, footprint_units=2.4),
            strict=True,
        )
    ):
        for _ in range(30):
            width = int(rng.choice([2, 3, 4, 5]))
            height = int(rng.choice([2, 3, 4, 5]))
            left, bottom = _slot_anchor(ctx, center, width=width, height=height)
            points = _translated_corner_shape(
                left=left,
                bottom=bottom,
                width=width,
                height=height,
                shape_kind=shape_kind,
            )
            value = (
                polygon_area(points) if metric == "area" else polygon_perimeter(points)
            )
            encoded = int(round(value * 100))
            if encoded not in used_values:
                used_values.add(encoded)
                break
        obj = draw_polygon(
            ctx,
            label,
            points,
            class_name=shape_kind,
            color=object_color(ctx, index),
            filled=False,
        )
        objects.append(replace(obj, metric_value=float(encoded)))
    return ctx, shape_kind, object_count, tuple(objects)


def _build_shape_extremum(
    context: Mapping[str, Any], *, plan: GraphPaperTaskPlan, metric: str
) -> tuple[GraphPaperComponents, TypedValue]:
    """Build a labeled-shape area or perimeter extremum objective."""

    ctx, shape_kind, object_count, objects = _shape_extremum_objects(
        context, plan, metric
    )
    winner = (
        max(objects, key=lambda item: item.metric_value)
        if plan.role_for(str(context["branch_name"])) == "max"
        else min(objects, key=lambda item: item.metric_value)
    )
    annotation_value, projected = scalar_bbox_artifacts(winner.bbox_px)
    branch_name = str(context["branch_name"])
    prompt_key = plan.prompt_key_for(branch_name)
    prompt_plan = _make_prompt(
        context["prompt_defaults"],
        prompt_key=prompt_key,
        answer_hint='set "answer" to the selected shape label as a capital letter shown in the image',
        annotation_hint='set "annotation" to the selected shape bounding box [x0,y0,x1,y1] in pixels',
        json_example='{"annotation":[180,180,320,310],"answer":"B"}',
        json_example_answer_only='{"answer":"B"}',
        shape_text=shape_kind.replace("_", " "),
        target_text=f"{branch_name} {metric}",
        metric_text=metric,
    )
    return _component_payload(
        context,
        ctx=ctx,
        prompt_plan=prompt_plan,
        answer_type="option_letter",
        answer_value=str(winner.label),
        annotation_type="bbox",
        annotation_value=annotation_value,
        projected_annotation=projected,
        witness_symbolic={
            "selected_label": str(winner.label),
            f"relative_{metric}": int(winner.metric_value),
        },
        objects=objects,
        prompt_key=prompt_key,
        program_code=f"labeled_shapes.{metric}_extremum_label",
        scene_kind="geometry_graph_paper_labeled_shapes",
        semantic_args={
            "extremum": branch_name,
            "shape_kind": shape_kind,
            "object_count": int(object_count),
        },
    )


def _build_area_extremum_label(
    context: Mapping[str, Any], plan: GraphPaperTaskPlan
) -> tuple[GraphPaperComponents, TypedValue]:
    """Build the labeled-shape area extremum objective."""

    return _build_shape_extremum(context, plan=plan, metric="area")


def _build_perimeter_extremum_label(
    context: Mapping[str, Any], plan: GraphPaperTaskPlan
) -> tuple[GraphPaperComponents, TypedValue]:
    """Build the labeled-shape perimeter extremum objective."""

    return _build_shape_extremum(context, plan=plan, metric="perimeter")


ANGLE_CLASSES = ("acute", "right", "obtuse")
ANGLE_VALUE_BY_CLASS = {"acute": 45, "right": 90, "obtuse": 125}

TRIANGLE_CLASSES = ("equilateral", "right", "scalene", "non_equilateral_isosceles")
QUADRILATERAL_CLASSES = (
    "square",
    "non_square_rectangle",
    "non_square_rhombus",
    "slanted_parallelogram",
)
SHAPE_CLASSES = (
    "triangle",
    "quadrilateral",
    "pentagon",
    "hexagon",
    "circle",
    "ellipse",
)
CONVEXITY_CLASSES = ("convex", "concave")


def _triangle_points(center: Point, class_name: str) -> tuple[Point, ...]:
    """Return a compact triangle prototype for classification-count scenes."""

    cx, cy = float(center[0]), float(center[1])
    if class_name == "equilateral":
        return regular_polygon(center, 3, 0.9, phase=1.57)
    if class_name == "non_equilateral_isosceles":
        return ((cx - 0.9, cy - 0.7), (cx + 0.9, cy - 0.7), (cx, cy + 0.9))
    if class_name == "right":
        return right_triangle_points(center, 1.8, 1.2)
    return ((cx - 1.0, cy - 0.7), (cx + 0.8, cy - 0.45), (cx - 0.2, cy + 0.9))


def _quadrilateral_points(center: Point, class_name: str) -> tuple[Point, ...]:
    """Return a compact quadrilateral prototype for classification-count scenes."""

    cx, cy = float(center[0]), float(center[1])
    if class_name == "square":
        return rectangle_points(center, 1.6, 1.6)
    if class_name == "non_square_rectangle":
        return rectangle_points(center, 2.0, 1.2)
    if class_name == "non_square_rhombus":
        return ((cx, cy + 0.95), (cx + 1.0, cy), (cx, cy - 0.95), (cx - 1.0, cy))
    if class_name == "slanted_parallelogram":
        return (
            (cx - 0.9, cy - 0.65),
            (cx + 0.9, cy - 0.65),
            (cx + 1.2, cy + 0.65),
            (cx - 0.6, cy + 0.65),
        )
    return (
        (cx - 0.9, cy - 0.65),
        (cx + 0.9, cy - 0.65),
        (cx + 1.2, cy + 0.65),
        (cx - 0.6, cy + 0.65),
    )


def _count_setup(
    context: Mapping[str, Any],
    plan: GraphPaperTaskPlan,
    *,
    salt: str,
    target_field: str,
    classes: Sequence[str],
):
    """Resolve the target class, target count, and shuffled class sequence."""

    task_params = dict(context["task_params"])
    rng = rng_for(int(context["instance_seed"]), str(salt))
    object_count = min(
        9, resolve_count(task_params, context["generation_defaults"], fallback=8)
    )
    branch_name = str(context["branch_name"])
    fallback_target_class = str(
        task_params.get(
            str(target_field),
            choose_from_seed(
                tuple(str(value) for value in classes),
                instance_seed=int(context["instance_seed"]),
                salt=str(salt),
            ),
        )
    )
    target_class = plan.target_class_for(branch_name, fallback_target_class)
    target_total = count_target(
        task_params,
        context["generation_defaults"],
        object_count=object_count,
        instance_seed=int(context["instance_seed"]),
        salt=str(salt),
    )
    class_sequence = make_class_sequence(
        target_class=target_class,
        distractor_classes=[
            str(value) for value in classes if str(value) != target_class
        ],
        object_count=object_count,
        target_count=target_total,
        rng=rng,
    )
    return rng, object_count, target_class, target_total, class_sequence


def _count_components(
    context: Mapping[str, Any],
    *,
    ctx: GraphPaperContext,
    objects: Sequence[GraphObject],
    target_class: str,
    target_text: str,
    target_total: int,
    prompt_key: str,
    program_code: str,
    scene_kind: str,
    object_count: int,
    noun: str,
) -> tuple[GraphPaperComponents, TypedValue]:
    """Build shared count-task components once the public class family is rendered."""

    matching = [obj.bbox_px for obj in objects if obj.class_name == str(target_class)]
    annotation_value, projected = bbox_set_artifacts(matching)
    prompt_plan = _make_prompt(
        context["prompt_defaults"],
        prompt_key=str(prompt_key),
        answer_hint='set "answer" to the integer count',
        annotation_hint=f'set "annotation" to bounding boxes for every matching {noun}',
        json_example='{"annotation":[[120,120,210,210],[340,270,430,360]],"answer":2}',
        json_example_answer_only='{"answer":2}',
        target_text=str(target_text),
        metric_text="count",
    )
    return _component_payload(
        context,
        ctx=ctx,
        prompt_plan=prompt_plan,
        answer_type="integer",
        answer_value=int(target_total),
        annotation_type="bbox_set",
        annotation_value=annotation_value,
        projected_annotation=projected,
        witness_symbolic={
            "target_class": str(target_class),
            "target_text": str(target_text),
            "matching_count": int(target_total),
        },
        objects=tuple(objects),
        prompt_key=str(prompt_key),
        program_code=str(program_code),
        scene_kind=str(scene_kind),
        semantic_args={
            "target_class": str(target_class),
            "target_text": str(target_text),
            "object_count": int(object_count),
        },
    )


def _build_angle_type_count(
    context: Mapping[str, Any], plan: GraphPaperTaskPlan
) -> tuple[GraphPaperComponents, TypedValue]:
    """Render angle classes and bind matching-class count annotation."""

    rng, object_count, target_class, target_total, class_sequence = _count_setup(
        context,
        plan,
        salt=plan.salt,
        target_field=plan.target_field,
        classes=ANGLE_CLASSES,
    )
    ctx = make_context(
        instance_seed=int(context["instance_seed"]),
        params=context["task_params"],
        defaults=context["rendering_defaults"],
        theme_index=rng.randrange(0, 3),
    )
    objects = []
    for index, (cls_name, center) in enumerate(
        zip(
            class_sequence,
            slot_centers(ctx, object_count, rng=rng, footprint_units=1.9),
            strict=True,
        )
    ):
        obj = draw_angle(
            ctx,
            "",
            angle_points(center, ANGLE_VALUE_BY_CLASS[cls_name], radius=2.15),
            color=object_color(ctx, index),
        )
        objects.append(
            replace(
                obj,
                class_name=str(cls_name),
                metric_value=float(ANGLE_VALUE_BY_CLASS[cls_name]),
            )
        )
    return _count_components(
        context,
        ctx=ctx,
        objects=tuple(objects),
        target_class=target_class,
        target_text=plan.target_text_for(
            str(context["branch_name"]), f"{target_class} angles"
        ),
        target_total=target_total,
        prompt_key=plan.prompt_key_for(str(context["branch_name"])),
        program_code="angle_set.class_count",
        scene_kind="geometry_graph_paper_angle_set",
        object_count=object_count,
        noun="angle",
    )


def _build_triangle_type_count(
    context: Mapping[str, Any], plan: GraphPaperTaskPlan
) -> tuple[GraphPaperComponents, TypedValue]:
    """Render triangle classes and bind matching-class count annotation."""

    rng, object_count, target_class, target_total, class_sequence = _count_setup(
        context,
        plan,
        salt=plan.salt,
        target_field=plan.target_field,
        classes=TRIANGLE_CLASSES,
    )
    ctx = make_context(
        instance_seed=int(context["instance_seed"]),
        params=context["task_params"],
        defaults=context["rendering_defaults"],
        theme_index=rng.randrange(0, 3),
    )
    objects = []
    for index, (cls_name, center) in enumerate(
        zip(class_sequence, slot_centers(ctx, object_count, rng=rng), strict=True)
    ):
        obj = draw_polygon(
            ctx,
            "",
            _triangle_points(center, cls_name),
            class_name=str(cls_name),
            color=object_color(ctx, index),
            filled=False,
        )
        objects.append(replace(obj, class_name=str(cls_name)))
    return _count_components(
        context,
        ctx=ctx,
        objects=tuple(objects),
        target_class=target_class,
        target_text=plan.target_text_for(
            str(context["branch_name"]), f"{target_class.replace('_', ' ')} triangles"
        ),
        target_total=target_total,
        prompt_key=plan.prompt_key_for(str(context["branch_name"])),
        program_code="triangle_set.class_count",
        scene_kind="geometry_graph_paper_triangle_set",
        object_count=object_count,
        noun="triangle",
    )


def _build_quadrilateral_type_count(
    context: Mapping[str, Any], plan: GraphPaperTaskPlan
) -> tuple[GraphPaperComponents, TypedValue]:
    """Render quadrilateral classes and bind matching-class count annotation."""

    rng, object_count, target_class, target_total, class_sequence = _count_setup(
        context,
        plan,
        salt=plan.salt,
        target_field=plan.target_field,
        classes=QUADRILATERAL_CLASSES,
    )
    ctx = make_context(
        instance_seed=int(context["instance_seed"]),
        params=context["task_params"],
        defaults=context["rendering_defaults"],
        theme_index=rng.randrange(0, 3),
    )
    objects = []
    for index, (cls_name, center) in enumerate(
        zip(class_sequence, slot_centers(ctx, object_count, rng=rng), strict=True)
    ):
        obj = draw_polygon(
            ctx,
            "",
            _quadrilateral_points(center, cls_name),
            class_name=str(cls_name),
            color=object_color(ctx, index),
            filled=False,
        )
        objects.append(replace(obj, class_name=str(cls_name)))
    return _count_components(
        context,
        ctx=ctx,
        objects=tuple(objects),
        target_class=target_class,
        target_text=plan.target_text_for(
            str(context["branch_name"]),
            f"{target_class.replace('_', ' ')} quadrilaterals",
        ),
        target_total=target_total,
        prompt_key=plan.prompt_key_for(str(context["branch_name"])),
        program_code="quadrilateral_set.class_count",
        scene_kind="geometry_graph_paper_quadrilateral_set",
        object_count=object_count,
        noun="quadrilateral",
    )


def _build_shape_type_count(
    context: Mapping[str, Any], plan: GraphPaperTaskPlan
) -> tuple[GraphPaperComponents, TypedValue]:
    """Render mixed shape classes and bind matching-class count annotation."""

    rng, object_count, target_class, target_total, class_sequence = _count_setup(
        context,
        plan,
        salt=plan.salt,
        target_field=plan.target_field,
        classes=SHAPE_CLASSES,
    )
    ctx = make_context(
        instance_seed=int(context["instance_seed"]),
        params=context["task_params"],
        defaults=context["rendering_defaults"],
        theme_index=rng.randrange(0, 3),
    )
    objects = []
    for index, (cls_name, center) in enumerate(
        zip(class_sequence, slot_centers(ctx, object_count, rng=rng), strict=True)
    ):
        color = object_color(ctx, index)
        if cls_name == "triangle":
            obj = draw_polygon(
                ctx,
                "",
                right_triangle_points(center, 1.6, 1.5),
                class_name="triangle",
                color=color,
                filled=False,
            )
        elif cls_name == "quadrilateral":
            obj = draw_polygon(
                ctx,
                "",
                rectangle_points(center, 1.8, 1.3),
                class_name="quadrilateral",
                color=color,
                filled=False,
            )
        elif cls_name == "pentagon":
            obj = draw_polygon(
                ctx,
                "",
                regular_polygon(center, 5, 0.9),
                class_name="pentagon",
                color=color,
                filled=False,
            )
        elif cls_name == "hexagon":
            obj = draw_polygon(
                ctx,
                "",
                regular_polygon(center, 6, 0.9),
                class_name="hexagon",
                color=color,
                filled=False,
            )
        elif cls_name == "circle":
            obj = draw_ellipse_or_circle(
                ctx,
                "",
                center,
                0.75,
                0.75,
                class_name="circle",
                color=color,
                filled=False,
            )
        else:
            obj = draw_ellipse_or_circle(
                ctx,
                "",
                center,
                0.95,
                0.6,
                class_name="ellipse",
                color=color,
                filled=False,
            )
        objects.append(replace(obj, class_name=str(cls_name)))
    return _count_components(
        context,
        ctx=ctx,
        objects=tuple(objects),
        target_class=target_class,
        target_text=plan.target_text_for(
            str(context["branch_name"]), f"{target_class.replace('_', ' ')} shapes"
        ),
        target_total=target_total,
        prompt_key=plan.prompt_key_for(str(context["branch_name"])),
        program_code="shape_set.class_count",
        scene_kind="geometry_graph_paper_mixed_shape_set",
        object_count=object_count,
        noun="shape",
    )


def _build_polygon_convexity_count(
    context: Mapping[str, Any], plan: GraphPaperTaskPlan
) -> tuple[GraphPaperComponents, TypedValue]:
    """Render convexity classes and bind matching-polygon count annotation."""

    rng, object_count, target_class, target_total, class_sequence = _count_setup(
        context,
        plan,
        salt=plan.salt,
        target_field=plan.target_field,
        classes=CONVEXITY_CLASSES,
    )
    ctx = make_context(
        instance_seed=int(context["instance_seed"]),
        params=context["task_params"],
        defaults=context["rendering_defaults"],
        theme_index=rng.randrange(0, 3),
    )
    objects = []
    for index, (cls_name, center) in enumerate(
        zip(class_sequence, slot_centers(ctx, object_count, rng=rng), strict=True)
    ):
        points = (
            regular_polygon(center, 5, 0.9)
            if cls_name == "convex"
            else concave_polygon(center, 5, 0.95, rng)
        )
        obj = draw_polygon(
            ctx,
            "",
            points,
            class_name=str(cls_name),
            color=object_color(ctx, index),
            filled=False,
        )
        objects.append(replace(obj, class_name=str(cls_name)))
    return _count_components(
        context,
        ctx=ctx,
        objects=tuple(objects),
        target_class=target_class,
        target_text=plan.target_text_for(
            str(context["branch_name"]), f"{target_class} polygons"
        ),
        target_total=target_total,
        prompt_key=plan.prompt_key_for(str(context["branch_name"])),
        program_code="polygon_set.convexity_count",
        scene_kind="geometry_graph_paper_polygon_set",
        object_count=object_count,
        noun="polygon",
    )


__all__ = [
    "GraphPaperComponents",
    "GraphPaperTaskPlan",
    "build_graph_paper_components",
    "graph_paper_prompt_plan",
    "object_trace",
    "run_graph_paper_entry",
]
