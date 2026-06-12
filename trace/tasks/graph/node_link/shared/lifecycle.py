"""Scene-private output plumbing for migrated node-link tasks.

The public task files own their objective/query sampling, answer binding, and
annotation binding. This module only carries neutral bundle metadata rewriting
and final ``TaskOutput`` assembly that is identical for every node-link task.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Mapping

from trace.core.seed import hash64, spawn_rng
from trace.core.types import TypedValue
from trace.core.visual.background import make_background_canvas
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.base import TaskOutput
from trace.tasks.graph.shared.graph_sampling import SUPPORTED_TOPOLOGY_PROFILES, graph_label_sort_key
from trace.tasks.graph.shared.graph_scene import (
    projected_edge_label_bbox_annotation,
    projected_edge_pair_annotation,
    projected_node_point_annotation,
    render_graph_scene,
)
from trace.tasks.graph.shared.graph_visual_axes import resolve_node_link_visual_axes
from trace.tasks.graph.shared.prompt_examples import build_graph_prompt_json_examples
from trace.tasks.graph.shared.task_support import resolve_graph_named_variant, resolve_graph_render_params
from trace.tasks.graph.shared.visual_defaults import load_graph_scene_background_defaults, load_graph_scene_noise_defaults
from trace.tasks.shared.config_defaults import group_default, required_group_defaults, split_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.deterministic_sampling import resolve_selection_index
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)


@dataclass(frozen=True)
class NodeLinkTaskBundle:
    """Built node-link instance before public TaskOutput assembly."""

    prompt: str
    answer_gt: TypedValue
    annotation_gt: TypedValue
    image: Any
    image_id: str
    trace_payload: dict[str, Any]
    prompt_variants: dict[str, Any]
    scene_id: str = "node_link"
    query_id: str = ""


@dataclass(frozen=True)
class NodeLinkDefaults:
    """Fallback scene defaults used by compact public objective plans."""

    node_count_min: int = 5
    node_count_max: int = 10
    target_count_min: int = 1
    target_count_max: int = 5
    query_degree_min: int = 0
    query_degree_max: int = 4
    path_length_min: int = 2
    path_length_max: int = 5
    cycle_size_min: int = 3
    cycle_size_max: int = 6
    component_count_min: int = 2
    component_count_max: int = 4
    extra_edge_count_min: int = 1
    extra_edge_count_max: int = 4
    edge_weight_min: int = 1
    edge_weight_max: int = 9
    degree_sequence_max_degree: int = 5
    directed_degree_sequence_max_degree: int = 4
    graph_search_attempts: int = 600
    canvas_width: int = 864
    canvas_height: int = 640
    outer_margin_px: int = 28
    panel_padding_px: int = 24
    panel_corner_radius_px: int = 20
    panel_title_font_size_px: int = 24
    node_shape_variant: str = "circle"
    node_radius_min_px: int = 18
    node_radius_max_px: int = 24
    edge_width_px: int = 4
    arrow_length_px: int = 12
    arrow_width_px: int = 7
    node_border_width_px: int = 2
    label_font_size_px: int = 20


@dataclass(frozen=True)
class NodeLinkAxes:
    """Resolved query, semantic support, and non-semantic visual axes."""

    query_id: str
    node_count: int
    values: dict[str, Any]
    topology_profile: str
    layout_variant: str
    label_variant: str
    node_shape_variant: str
    layout_transform_variant: str
    edge_routing_variant: str
    node_color_name: str
    probabilities: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NodeLinkObjectivePlan:
    """Task-owned semantic plan consumed by neutral scene lifecycle code."""

    public_id: str
    class_name: str
    supported_query_ids: tuple[str, ...]
    sample_graph: Callable[[Any, NodeLinkAxes, int], Any]
    answer_type: str
    answer_field: str
    annotation_type: str
    annotation_kind: str
    annotation_field: str
    prompt_query_key: Callable[[NodeLinkAxes], str] | str
    object_description_key: Callable[[NodeLinkAxes], str] | str = "object_description_undirected"
    annotation_hint_key: Callable[[NodeLinkAxes], str] | str = "annotation_hint"
    answer_hint_key: str = "answer_hint"
    prompt_bundle_id: str = ""
    prompt_scene_key: str = ""
    prompt_task_key: str = ""
    graph_directionality: Callable[[NodeLinkAxes], str] | str = "undirected"
    question_format: Callable[[NodeLinkAxes], str] | str = ""
    scene_kind: str = "node_link_graph"
    value_ranges: dict[str, tuple[int, int]] = field(default_factory=dict)
    fixed_values: dict[str, Any] = field(default_factory=dict)
    semantic_colors: tuple[str, ...] = ("red", "blue", "green", "yellow", "orange", "purple")
    annotation_example: Any = field(default_factory=lambda: [[180, 220], [310, 180]])
    answer_example: Any = 2


def _resolve_slot(value: Callable[[NodeLinkAxes], str] | str, axes: NodeLinkAxes) -> str:
    """Resolve a plan slot that may depend on query axes."""

    if callable(value):
        return str(value(axes))
    return str(value)


def _resolve_int_axis(
    *,
    key: str,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    fallback: tuple[int, int],
    instance_seed: int,
    task_id: str,
) -> tuple[int, dict[str, float]]:
    """Resolve one integer axis with deterministic cycling over support."""

    if key in params:
        value = int(params[key])
        return value, {str(value): 1.0}
    lower = int(params.get(f"{key}_min", group_default(gen_defaults, f"{key}_min", int(fallback[0]))))
    upper = int(params.get(f"{key}_max", group_default(gen_defaults, f"{key}_max", int(fallback[1]))))
    if upper < lower:
        raise ValueError(f"{key} support is empty")
    support = tuple(range(lower, upper + 1))
    sample_cursor = params.get("_sample_cursor")
    if sample_cursor is not None:
        offset = abs(int(hash64(0, f"{task_id}:{key}:axis_offset", 0))) % len(support)
        cursor = abs(int(sample_cursor)) + int(offset)
    else:
        cursor = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}:{key}",
        )
    value = int(support[int(cursor) % len(support)])
    return value, {str(item): 1.0 / float(len(support)) for item in support}


def _resolve_axes(
    *,
    plan: NodeLinkObjectivePlan,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    defaults: NodeLinkDefaults,
    instance_seed: int,
) -> NodeLinkAxes:
    """Resolve task-supplied query ids, numeric supports, and visual axes."""

    query_rng = spawn_rng(int(instance_seed), f"{plan.public_id}.query")
    selected_query, query_probabilities = resolve_graph_named_variant(
        query_rng,
        params=params,
        gen_defaults=gen_defaults,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        supported=tuple(plan.supported_query_ids),
        instance_seed=int(instance_seed),
        task_id=str(plan.public_id),
        namespace="query_id",
    )
    node_count, node_probabilities = _resolve_int_axis(
        key="node_count",
        params=params,
        gen_defaults=gen_defaults,
        fallback=(defaults.node_count_min, defaults.node_count_max),
        instance_seed=int(instance_seed),
        task_id=str(plan.public_id),
    )
    values: dict[str, Any] = dict(plan.fixed_values)
    probabilities: dict[str, Any] = {
        "query_id_probabilities": dict(query_probabilities),
        "node_count_probabilities": dict(node_probabilities),
    }
    fallback_ranges = {
        "target_count": (defaults.target_count_min, defaults.target_count_max),
        "query_degree": (defaults.query_degree_min, defaults.query_degree_max),
        "target_component_size": (defaults.target_count_min, defaults.target_count_max),
        "component_count": (defaults.component_count_min, defaults.component_count_max),
        "target_cycle_size": (defaults.cycle_size_min, defaults.cycle_size_max),
        "target_shortest_path_length": (defaults.path_length_min, defaults.path_length_max),
        "target_longest_path_length": (defaults.path_length_min, defaults.path_length_max),
        "target_position": (1, max(1, int(node_count))),
        "extra_edge_count": (defaults.extra_edge_count_min, defaults.extra_edge_count_max),
        "target_degree": (defaults.query_degree_min, defaults.query_degree_max),
    }
    for key, fallback in {**fallback_ranges, **plan.value_ranges}.items():
        if key in values:
            continue
        selected_value, selected_probabilities = _resolve_int_axis(
            key=key,
            params=params,
            gen_defaults=gen_defaults,
            fallback=tuple(int(item) for item in fallback),
            instance_seed=int(instance_seed),
            task_id=str(plan.public_id),
        )
        values[key] = int(selected_value)
        probabilities[f"{key}_probabilities"] = dict(selected_probabilities)

    topology_rng = spawn_rng(int(instance_seed), f"{plan.public_id}.topology")
    topology_profile, topology_probabilities = resolve_graph_named_variant(
        topology_rng,
        params=params,
        gen_defaults=gen_defaults,
        explicit_key="topology_profile",
        weights_key="topology_profile_weights",
        balance_flag_key="balanced_topology_profile_sampling",
        supported=SUPPORTED_TOPOLOGY_PROFILES,
        instance_seed=int(instance_seed),
        task_id=str(plan.public_id),
        namespace="topology_profile",
    )
    visual_axes = resolve_node_link_visual_axes(
        int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        task_id=str(plan.public_id),
    )
    return NodeLinkAxes(
        query_id=str(selected_query),
        node_count=int(node_count),
        values=values,
        topology_profile=str(topology_profile),
        layout_variant=str(visual_axes.layout_variant),
        label_variant=str(visual_axes.label_variant),
        node_shape_variant=str(visual_axes.node_shape_variant),
        layout_transform_variant=str(visual_axes.layout_transform_variant),
        edge_routing_variant=str(visual_axes.edge_routing_variant),
        node_color_name=str(visual_axes.node_color_name),
        probabilities={
            **probabilities,
            "topology_profile_probabilities": dict(topology_probabilities),
            "layout_variant_probabilities": dict(visual_axes.layout_variant_probabilities),
            "label_variant_probabilities": dict(visual_axes.label_variant_probabilities),
            "node_shape_variant_probabilities": dict(visual_axes.node_shape_variant_probabilities),
            "layout_transform_variant_probabilities": dict(visual_axes.layout_transform_variant_probabilities),
            "edge_routing_variant_probabilities": dict(visual_axes.edge_routing_variant_probabilities),
            "node_color_name_probabilities": dict(visual_axes.node_color_name_probabilities),
        },
    )


def _labels_from_sample(sample: Any, field_name: str) -> tuple[str, ...]:
    """Read one label sequence from a graph sample field."""

    raw = getattr(sample, str(field_name))
    if isinstance(raw, str):
        return (str(raw),)
    return tuple(str(item) for item in raw)


def _edges_from_sample(sample: Any, field_name: str) -> tuple[tuple[str, str], ...]:
    """Read one edge-label sequence from a graph sample field."""

    raw = getattr(sample, str(field_name))
    if raw and isinstance(raw[0], str):
        return (tuple(str(item) for item in raw[:2]),)
    return tuple(tuple(str(item) for item in edge[:2]) for edge in raw)


def _answer_value(sample: Any, plan: NodeLinkObjectivePlan) -> Any:
    """Resolve the typed answer value from the public task plan."""

    if hasattr(sample, str(plan.answer_field)):
        value = getattr(sample, str(plan.answer_field))
    elif hasattr(sample, "target_labels"):
        value = len(getattr(sample, "target_labels"))
    elif hasattr(sample, "target_edges"):
        value = len(getattr(sample, "target_edges"))
    else:
        raise AttributeError(f"sample has no answer field {plan.answer_field!r}")
    if str(plan.answer_type) == "integer":
        return int(value)
    return str(value)


def _annotation_value(sample: Any, rendered_scene: Any, plan: NodeLinkObjectivePlan) -> tuple[TypedValue, dict[str, Any], dict[str, Any]]:
    """Project task-selected minimal witnesses into pixel annotation space."""

    kind = str(plan.annotation_kind)
    if kind in {"node_point_set", "node_point_sequence"}:
        labels = _labels_from_sample(sample, str(plan.annotation_field))
        projection = projected_node_point_annotation(rendered_scene, labels)
        points = [list(point) for point in projection["pixel_point_set"]]
        annotation_type = "point_sequence" if kind == "node_point_sequence" else "point_set"
        return (
            TypedValue(type=annotation_type, value=list(points)),
            {"type": annotation_type, annotation_type: list(points), **dict(projection)},
            {"type": "object_sequence" if kind == "node_point_sequence" else "object_set", "labels": list(labels)},
        )
    if kind == "edge_point_pair_set":
        edges = _edges_from_sample(sample, str(plan.annotation_field))
        projection = projected_edge_pair_annotation(rendered_scene, edges)
        pairs = [[list(pair[0]), list(pair[1])] for pair in projection["point_pair_set"]]
        return (
            TypedValue(type="point_pair_set", value=list(pairs)),
            {"type": "point_pair_set", "point_pair_set": list(pairs), **dict(projection)},
            {"type": "edge_set", "edge_labels": [list(edge) for edge in edges]},
        )
    if kind == "edge_label_bbox_set":
        edges = _edges_from_sample(sample, str(plan.annotation_field))
        boxes: list[list[float]] = []
        projections: list[dict[str, Any]] = []
        for edge in edges:
            projection = projected_edge_label_bbox_annotation(rendered_scene, edge)
            boxes.extend([list(box) for box in projection["pixel_bbox_set"]])
            projections.append(dict(projection))
        return (
            TypedValue(type="bbox_set", value=list(boxes)),
            {"type": "bbox_set", "bbox_set": list(boxes), "edge_label_projections": projections},
            {"type": "edge_label_set", "edge_labels": [list(edge) for edge in edges]},
        )
    raise ValueError(f"unsupported node-link annotation kind: {kind}")


def _node_entities(rendered_scene: Any) -> list[dict[str, Any]]:
    """Return generic rendered-node entities for trace inspection."""

    return [
        {
            "entity_id": f"node_{node.label}",
            "entity_kind": "graph_node",
            "label": str(node.label),
            "degree": int(node.degree),
            "neighbors": list(node.neighbors),
            "successors": list(node.successors),
            "predecessors": list(node.predecessors),
            "center_px": list(node.center_xy),
            "bbox_xyxy": list(node.bbox_xyxy),
        }
        for node in rendered_scene.nodes
    ]


def _edge_entities(rendered_scene: Any, sample: Any) -> list[dict[str, Any]]:
    """Return generic rendered-edge entities for trace inspection."""

    labels_by_edge = getattr(sample, "edge_attribute_labels_by_label", {})
    colors_by_edge = getattr(sample, "edge_color_names_by_label", {})
    weights_by_edge = getattr(sample, "edge_weights_by_label", {})
    return [
        {
            "entity_id": str(edge.edge_id),
            "entity_kind": "graph_edge",
            "node_u_label": str(edge.node_u_label),
            "node_v_label": str(edge.node_v_label),
            "directed": bool(edge.directed),
            "segment_px": [list(edge.segment_px[0]), list(edge.segment_px[1])],
            "route_variant": str(edge.route_variant),
            "control_px": list(edge.control_px) if edge.control_px is not None else None,
            "edge_text_label": labels_by_edge.get((str(edge.node_u_label), str(edge.node_v_label))),
            "edge_color_name": colors_by_edge.get((str(edge.node_u_label), str(edge.node_v_label))),
            "edge_weight": weights_by_edge.get((str(edge.node_u_label), str(edge.node_v_label))),
        }
        for edge in rendered_scene.edges
    ]




def run_node_link_plan(
    *,
    plan: NodeLinkObjectivePlan,
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
) -> TaskOutput:
    """Generate one node-link task from public-owned objective hooks."""

    scene_id = "node_link"
    scene_id_defaults = {}
    from trace.core.scene_config import get_scene_defaults

    loaded_defaults = get_scene_defaults("graph", scene_id)
    if isinstance(loaded_defaults, Mapping):
        scene_id_defaults = dict(loaded_defaults)
    gen_defaults, render_defaults, prompt_defaults = split_scene_generation_rendering_prompt_defaults(
        scene_id_defaults,
        task_id=str(plan.public_id),
    )
    if not prompt_defaults and str(plan.prompt_bundle_id):
        prompt_defaults = {
            "bundle_id": str(plan.prompt_bundle_id),
            "scene_key": str(plan.prompt_scene_key or "single_graph_counting"),
            "task_key": str(plan.prompt_task_key),
            "json_output_contract": 'Use a valid JSON object with keys "annotation" and "answer" in that order for the final answer.',
            "json_output_contract_answer_only": 'Use a valid JSON object with key "answer" for the final answer.',
            "object_description": "a labeled graph",
            "annotation_hint": 'set "annotation" to the requested pixel-space witnesses for the answer',
            "answer_hint": 'set "answer" to the requested value',
        }
    defaults = NodeLinkDefaults()
    axes = _resolve_axes(
        plan=plan,
        params=params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        instance_seed=int(instance_seed),
    )
    render_params = resolve_graph_render_params(
        params,
        instance_seed=int(instance_seed),
        task_id=str(plan.public_id),
        render_defaults=render_defaults,
        fallback_defaults=defaults,
        node_color_name=str(axes.node_color_name),
        node_shape_variant=str(axes.node_shape_variant),
        edge_routing_variant=str(axes.edge_routing_variant),
    )
    background_defaults = load_graph_scene_background_defaults(scene_id=scene_id)
    noise_defaults = load_graph_scene_noise_defaults(scene_id=scene_id, apply_prob=0.5)
    search_attempts = int(params.get("graph_search_attempts", group_default(gen_defaults, "graph_search_attempts", defaults.graph_search_attempts)))

    sample = None
    rendered_scene = None
    image = None
    background_meta: dict[str, Any] = {}
    post_noise_meta: dict[str, Any] = {}
    last_error: Exception | None = None
    graph_rng = spawn_rng(int(instance_seed), "graph_structure")
    for attempt in range(max(1, int(max_attempts))):
        try:
            sample = plan.sample_graph(graph_rng, axes, max(80, int(search_attempts) // max(1, int(max_attempts)) + 80))
            background, background_meta = make_background_canvas(
                canvas_width=int(render_params.canvas_width),
                canvas_height=int(render_params.canvas_height),
                instance_seed=int(instance_seed),
                params=params,
                default_config=background_defaults,
            )
            directionality = _resolve_slot(plan.graph_directionality, axes)
            rendered_scene = render_graph_scene(
                graph_sample=sample,
                layout_variant=str(axes.layout_variant),
                layout_transform_variant=str(axes.layout_transform_variant),
                render_params=render_params,
                layout_seed=int(instance_seed + attempt),
                scene_title="Graph",
                directed=str(directionality) == "directed",
                base_image=background,
            )
            image, post_noise_meta = apply_post_image_noise(
                rendered_scene.image,
                instance_seed=int(instance_seed),
                params=params,
                default_config=noise_defaults,
            )
            break
        except Exception as exc:  # pragma: no cover - retry loop depends on random graph feasibility
            last_error = exc
            continue
    else:
        raise RuntimeError(f"failed to generate node-link task instance for {plan.class_name}") from last_error

    answer_gt = TypedValue(type=str(plan.answer_type), value=_answer_value(sample, plan))
    annotation_gt, projected_annotation, witness_symbolic = _annotation_value(sample, rendered_scene, plan)
    object_description_key = _resolve_slot(plan.object_description_key, axes)
    if object_description_key not in prompt_defaults and "object_description" in prompt_defaults:
        object_description_key = "object_description"
    annotation_hint_key = _resolve_slot(plan.annotation_hint_key, axes)
    query_annotation_hint_key = f"annotation_hint_{axes.query_id}"
    if annotation_hint_key not in prompt_defaults and query_annotation_hint_key in prompt_defaults:
        annotation_hint_key = query_annotation_hint_key
    if annotation_hint_key not in prompt_defaults and "annotation_hint" in prompt_defaults:
        annotation_hint_key = "annotation_hint"
    prompt_defaults_required = required_group_defaults(
        prompt_defaults,
        (
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            str(object_description_key),
            str(annotation_hint_key),
            str(plan.answer_hint_key),
        ),
        context=f"prompt defaults for {plan.public_id}",
    )
    prompt_json_example, prompt_json_example_answer_only = build_graph_prompt_json_examples(
        annotation_value=plan.annotation_example,
        answer_value=plan.answer_example,
    )
    prompt_selection = render_scene_prompt_variants(
        domain="graph",
        scene_id=scene_id,
        bundle_id=str(prompt_defaults_required["bundle_id"]),
        scene_key=str(prompt_defaults_required["scene_key"]),
        task_key=str(prompt_defaults_required["task_key"]),
        query_key=_resolve_slot(plan.prompt_query_key, axes),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        slots={
            "object_description": str(prompt_defaults_required[str(object_description_key)]),
            "json_output_contract": str(prompt_defaults_required["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults_required["json_output_contract_answer_only"]),
            "annotation_hint": str(prompt_defaults_required[str(annotation_hint_key)]),
            "answer_hint": str(prompt_defaults_required[str(plan.answer_hint_key)]),
            "json_example": str(prompt_json_example),
            "json_example_answer_only": str(prompt_json_example_answer_only),
            "query_node_label": str(getattr(sample, "query_label", "")),
            "query_label": str(getattr(sample, "query_label", "")),
            "query_node_label_a": str(getattr(sample, "query_label_a", "")),
            "query_node_label_b": str(getattr(sample, "query_label_b", "")),
            "query_label_a": str(getattr(sample, "query_label_a", "")),
            "query_label_b": str(getattr(sample, "query_label_b", "")),
            "source_node_label": str(getattr(sample, "source_label", "")),
            "target_node_label": str(getattr(sample, "goal_label", "")),
            "source_label": str(getattr(sample, "source_label", getattr(sample, "query_edge", ("", ""))[0])),
            "target_label": str(getattr(sample, "goal_label", getattr(sample, "query_edge", ("", ""))[1])),
            "goal_label": str(getattr(sample, "goal_label", "")),
            "edit_label_a": str(getattr(sample, "edit_edge", ("", ""))[0]),
            "edit_label_b": str(getattr(sample, "edit_edge", ("", ""))[1]),
            "orientation_start_label": str(getattr(sample, "orientation_start_label", "")),
            "orientation_next_label": str(getattr(sample, "orientation_next_label", "")),
            "query_degree": int(axes.values.get("query_degree", axes.values.get("target_degree", 0))),
            "target_color": str(getattr(sample, "target_color_name", axes.values.get("target_color_name", ""))),
            "target_color_label": str(getattr(sample, "target_color_name", axes.values.get("target_color_name", ""))),
            "source_color": str(getattr(sample, "source_color_name", axes.values.get("source_color_name", ""))),
            "source_color_label": str(getattr(sample, "source_color_name", axes.values.get("source_color_name", ""))),
            "target_edge_label": str(getattr(sample, "target_edge_label", "")),
            "path_edge_term": str(getattr(sample, "query_path_edge_position", "edge") or "edge"),
            "path_follow_clause": " following arrow direction" if str(directionality) == "directed" else "",
        },
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
    directionality = _resolve_slot(plan.graph_directionality, axes)
    query_params = {
        "query_id": str(axes.query_id),
        "graph_directionality": str(directionality),
        "node_count": int(axes.node_count),
        "edge_count": int(getattr(sample, "edge_count", 0)),
        **{str(key): value for key, value in axes.values.items()},
        **dict(axes.probabilities),
    }
    trace_payload = {
        "scene_ir": {
            "scene_kind": str(plan.scene_kind),
            "scene_id": scene_id,
            "entities": [*_node_entities(rendered_scene), *_edge_entities(rendered_scene, sample)],
            "relations": {
                "graph_directionality": str(directionality),
                "adjacency_by_label": {str(key): list(values) for key, values in getattr(sample, "adjacency_by_label", {}).items()},
                "successors_by_label": {str(key): list(values) for key, values in getattr(sample, "successors_by_label", {}).items()},
                "predecessors_by_label": {str(key): list(values) for key, values in getattr(sample, "predecessors_by_label", {}).items()},
                "edge_labels": [list(edge) for edge in getattr(sample, "edge_labels", ())],
            },
            "frames": {
                "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                "panels": dict(rendered_scene.panel_geometry),
            },
        },
        "query_spec": {
            "query_id": str(axes.query_id),
            "template_id": str(prompt_defaults_required["bundle_id"]),
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": query_params,
        },
        "render_spec": {
            "canvas_size": list(rendered_scene.panel_geometry["canvas_size"]),
            "coord_space": "pixel",
            "panel_geometry": dict(rendered_scene.panel_geometry),
            "style": {
                "node_color_name": str(axes.node_color_name),
                "node_shape_variant": str(render_params.node_shape_variant),
                "edge_routing_variant": str(rendered_scene.edge_routing_variant),
                "theme_tone": str(render_params.theme_tone),
                "panel_style_variant": str(render_params.panel_style_variant),
                "background_meta": dict(background_meta),
                "post_image_noise_meta": dict(post_noise_meta),
            },
        },
        "render_map": {"image_id": "img0", "anchors": {}},
        "execution_trace": {
            "query_id": str(axes.query_id),
            "scene_id": scene_id,
            "question_format": _resolve_slot(plan.question_format, axes) or str(axes.query_id),
            "graph_directionality": str(directionality),
            "node_count": int(axes.node_count),
            "edge_count": int(getattr(sample, "edge_count", 0)),
            "layout_variant_used": str(rendered_scene.layout_variant),
            "layout_transform_variant": str(rendered_scene.layout_transform_variant),
            "edge_routing_variant": str(rendered_scene.edge_routing_variant),
            "label_variant": str(getattr(sample, "label_variant", axes.label_variant)),
            "matching_labels": list(getattr(sample, "target_labels", ())),
            "matching_edges": [list(edge) for edge in getattr(sample, "target_edges", ())],
        },
        "witness_symbolic": dict(witness_symbolic),
        "projected_annotation": dict(projected_annotation),
    }
    bundle = NodeLinkTaskBundle(
        prompt=str(prompt_artifacts.prompt),
        answer_gt=answer_gt,
        annotation_gt=annotation_gt,
        image=image,
        image_id="img0",
        trace_payload=trace_payload,
        prompt_variants=dict(prompt_artifacts.prompt_variants),
        query_id=str(axes.query_id),
    )
    return task_output_from_bundle(
        bundle,
        public_task_id=str(plan.public_id),
        scene_id=scene_id,
        query_id=str(axes.query_id),
    )


def rewrite_node_link_bundle_query_id(
    bundle: NodeLinkTaskBundle,
    *,
    query_id: str,
    query_id_probabilities: Mapping[str, float] | None = None,
) -> NodeLinkTaskBundle:
    """Return a copy of ``bundle`` with query metadata set consistently."""

    trace_payload = dict(bundle.trace_payload)
    query_spec = dict(trace_payload.get("query_spec") or {})
    query_spec["query_id"] = str(query_id)
    params = dict(query_spec.get("params") or {})
    params["query_id"] = str(query_id)
    if query_id_probabilities is not None:
        params["query_id_probabilities"] = {
            str(key): float(value)
            for key, value in query_id_probabilities.items()
        }
    query_spec["params"] = params
    trace_payload["query_spec"] = query_spec
    execution_trace = dict(trace_payload.get("execution_trace") or {})
    execution_trace["query_id"] = str(query_id)
    trace_payload["execution_trace"] = execution_trace
    return NodeLinkTaskBundle(
        prompt=str(bundle.prompt),
        answer_gt=bundle.answer_gt,
        annotation_gt=bundle.annotation_gt,
        image=bundle.image,
        image_id=str(bundle.image_id),
        trace_payload=trace_payload,
        prompt_variants=dict(bundle.prompt_variants),
        scene_id=str(bundle.scene_id),
        query_id=str(query_id),
    )


def bundle_query_id(bundle: NodeLinkTaskBundle, *, fallback_query_id: str) -> str:
    """Return the query id selected during task-owned sampling."""

    selected_key = str(getattr(bundle, "query_id", ""))
    if selected_key:
        return selected_key
    trace = bundle.trace_payload if isinstance(bundle.trace_payload, Mapping) else {}
    query_spec = trace.get("query_spec") if isinstance(trace, Mapping) else {}
    if isinstance(query_spec, Mapping) and str(query_spec.get("query_id", "")):
        return str(query_spec["query_id"])
    execution_trace = trace.get("execution_trace") if isinstance(trace, Mapping) else {}
    if isinstance(execution_trace, Mapping) and str(execution_trace.get("query_id", "")):
        return str(execution_trace["query_id"])
    return str(fallback_query_id)


def trace_with_public_task_id(trace_payload: Mapping[str, Any], *, public_task_id: str) -> dict[str, Any]:
    """Attach the public task id to task-owned trace sections."""

    trace = dict(trace_payload)
    for section in ("scene_ir", "query_spec", "execution_trace"):
        if isinstance(trace.get(section), Mapping):
            trace[section] = {**dict(trace[section]), "task_id": str(public_task_id)}
    return trace


def task_output_from_bundle(
    bundle: NodeLinkTaskBundle,
    *,
    public_task_id: str,
    scene_id: str,
    query_id: str,
) -> TaskOutput:
    """Assemble the final TaskOutput from public-owned answer and annotation."""

    answer_gt = TypedValue(type=str(bundle.answer_gt.type), value=bundle.answer_gt.value)
    annotation_gt = TypedValue(type=str(bundle.annotation_gt.type), value=bundle.annotation_gt.value)
    return TaskOutput(
        prompt=str(bundle.prompt),
        answer_gt=answer_gt,
        annotation_gt=annotation_gt,
        image=bundle.image,
        image_id=str(bundle.image_id),
        trace_payload=trace_with_public_task_id(bundle.trace_payload, public_task_id=str(public_task_id)),
        task_versions=default_task_versions(),
        scene_id=str(scene_id),
        query_id=str(query_id),
        prompt_variants=dict(bundle.prompt_variants),
    )
