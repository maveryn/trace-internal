"""Count edges in the unique longest directed path of a DAG."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.complexity import (
    build_graph_complexity,
    normalize_float_with_bounds,
    normalize_int_with_bounds,
    resolve_graph_complexity_weights,
)
from ..shared.graph_sampling import (
    SUPPORTED_TOPOLOGY_PROFILES,
    canonicalize_graph_edge_label,
    feasible_node_counts_for_longest_path_length,
    graph_label_sort_key,
    sample_longest_path_length_graph,
)
from ..shared.graph_scene import (
    GraphRenderParams,
    projected_node_point_annotation,
    render_graph_scene,
)
from ..shared.node_link_axes import resolve_node_link_visual_axes
from ..shared.task_scaffolding import graph_hashed_axis_selection_index
from ..shared.task_support import resolve_graph_named_variant, resolve_graph_render_params
from ..shared.visual_defaults import load_graph_background_defaults, load_graph_noise_defaults


TASK_ID = "task_graph__node_link__longest_path_length"
SCENE_ID = "node_link"
QUERY_ID = "directed_longest_path_length"


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for graph longest-path scenes."""

    node_count_min: int = 5
    directed_node_count_max: int = 10
    target_longest_path_length_min: int = 2
    target_longest_path_length_max: int = 6
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
    label_variant: str = "letters"
    layout_transform_variant: str = "identity"
    node_color_name: str = "blue"
    background_color_rgb: Tuple[int, int, int] = (247, 248, 251)
    panel_fill_rgb: Tuple[int, int, int] = (255, 255, 255)
    panel_border_rgb: Tuple[int, int, int] = (205, 212, 224)
    title_color_rgb: Tuple[int, int, int] = (70, 78, 96)
    edge_color_rgb: Tuple[int, int, int] = (118, 128, 145)
    node_fill_rgb: Tuple[int, int, int] = (92, 124, 250)
    node_border_rgb: Tuple[int, int, int] = (52, 73, 144)
    label_text_rgb: Tuple[int, int, int] = (255, 255, 255)
    label_stroke_rgb: Tuple[int, int, int] = (52, 73, 144)


@dataclass(frozen=True)
class _ResolvedQuery:
    """Resolved support and style axes for one longest-path query."""

    node_count: int
    target_longest_path_length: int
    topology_profile: str
    layout_variant: str
    label_variant: str
    node_shape_variant: str
    layout_transform_variant: str
    edge_routing_variant: str
    node_color_name: str
    node_count_probabilities: Dict[str, float]
    target_longest_path_length_probabilities: Dict[str, float]
    topology_profile_probabilities: Dict[str, float]
    layout_variant_probabilities: Dict[str, float]
    label_variant_probabilities: Dict[str, float]
    node_shape_variant_probabilities: Dict[str, float]
    layout_transform_variant_probabilities: Dict[str, float]
    edge_routing_variant_probabilities: Dict[str, float]
    node_color_name_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("graph", "path")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_graph_background_defaults(task_group="path")
POST_IMAGE_NOISE_DEFAULTS = load_graph_noise_defaults(task_group="path", apply_prob=0.0)
_COMPLEXITY_WEIGHTS = resolve_graph_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)


def _build_prompt_json_examples() -> Tuple[str, str]:
    """Return prompt examples that match the pixel-space annotation format."""

    example_annotation = [[180, 220], [310, 180], [430, 260]]
    return (
        json.dumps({"annotation": example_annotation, "answer": 2}, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
        json.dumps({"answer": 2}, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
    )


def _node_count_selection_index(
    instance_seed: int,
    *,
    selection_index: int,
    target_longest_path_length: int,
    topology_profile: str,
) -> int:
    """Return an independent node-count index for the resolved query support."""

    return graph_hashed_axis_selection_index(
        int(instance_seed),
        task_id=TASK_ID,
        axis_name="node_count",
        selection_index=int(selection_index),
        axis_values=(
            str(target_longest_path_length),
            str(topology_profile),
        ),
    )


def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    """Resolve balanced support for one graph longest-path query."""

    node_count_min = int(params.get("node_count_min", group_default(_GEN_DEFAULTS, "node_count_min", _DEFAULTS.node_count_min)))
    node_count_max = int(
        params.get(
            "directed_node_count_max",
            group_default(_GEN_DEFAULTS, "directed_node_count_max", _DEFAULTS.directed_node_count_max),
        )
    )
    target_length_min = int(
        params.get(
            "target_longest_path_length_min",
            group_default(
                _GEN_DEFAULTS,
                "target_longest_path_length_min",
                _DEFAULTS.target_longest_path_length_min,
            ),
        )
    )
    target_length_max = int(
        params.get(
            "target_longest_path_length_max",
            group_default(
                _GEN_DEFAULTS,
                "target_longest_path_length_max",
                _DEFAULTS.target_longest_path_length_max,
            ),
        )
    )

    selection_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:query_support",
        )
    )

    target_support = tuple(range(int(target_length_min), int(target_length_max) + 1))
    if not target_support:
        raise ValueError("target_longest_path_length support is empty for graph longest-path tasks")

    feasible_support_by_target: Dict[int, Tuple[int, ...]] = {}
    feasible_targets = []
    for target_longest_path_length in target_support:
        feasible_nodes = feasible_node_counts_for_longest_path_length(
            target_longest_path_length=int(target_longest_path_length),
            node_count_min=int(node_count_min),
            node_count_max=int(node_count_max),
        )
        if feasible_nodes:
            feasible_targets.append(int(target_longest_path_length))
            feasible_support_by_target[int(target_longest_path_length)] = tuple(int(value) for value in feasible_nodes)
    if not feasible_targets:
        raise ValueError("no feasible graph longest-path support exists for the configured ranges")

    explicit_target_length = params.get("target_longest_path_length")
    explicit_node_count = params.get("node_count")
    if explicit_target_length is not None:
        target_longest_path_length = int(explicit_target_length)
        if int(target_longest_path_length) not in feasible_targets:
            raise ValueError("target_longest_path_length is outside feasible support")
    elif bool(
        params.get(
            "balanced_target_longest_path_length_sampling",
            group_default(_GEN_DEFAULTS, "balanced_target_longest_path_length_sampling", True),
        )
    ):
        target_longest_path_length = int(feasible_targets[int(selection_index % len(feasible_targets))])
    else:
        target_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.target_longest_path_length")
        target_longest_path_length = int(feasible_targets[int(target_rng.randrange(len(feasible_targets)))])

    feasible_node_support = feasible_support_by_target[int(target_longest_path_length)]
    topology_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.topology_profile")
    topology_profile, topology_probabilities = resolve_graph_named_variant(
        topology_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key="topology_profile",
        weights_key="topology_profile_weights",
        balance_flag_key="balanced_topology_profile_sampling",
        supported=SUPPORTED_TOPOLOGY_PROFILES,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace="topology_profile",
    )

    if explicit_node_count is not None:
        node_count = int(explicit_node_count)
        if int(node_count) not in feasible_node_support:
            raise ValueError("node_count is outside feasible support for the requested graph longest-path query")
    else:
        node_index = _node_count_selection_index(
            int(instance_seed),
            selection_index=int(selection_index),
            target_longest_path_length=int(target_longest_path_length),
            topology_profile=str(topology_profile),
        )
        node_count = int(feasible_node_support[int(node_index % len(feasible_node_support))])

    visual_axes = resolve_node_link_visual_axes(
        int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        task_id=TASK_ID,
    )
    layout_variant = visual_axes.layout_variant
    label_variant = visual_axes.label_variant
    node_shape_variant = visual_axes.node_shape_variant
    layout_transform_variant = visual_axes.layout_transform_variant
    edge_routing_variant = visual_axes.edge_routing_variant
    node_color_name = visual_axes.node_color_name
    layout_probabilities = visual_axes.layout_variant_probabilities
    label_variant_probabilities = visual_axes.label_variant_probabilities
    node_shape_variant_probabilities = visual_axes.node_shape_variant_probabilities
    layout_transform_variant_probabilities = visual_axes.layout_transform_variant_probabilities
    edge_routing_variant_probabilities = visual_axes.edge_routing_variant_probabilities
    node_color_name_probabilities = visual_axes.node_color_name_probabilities

    return _ResolvedQuery(
        node_count=int(node_count),
        target_longest_path_length=int(target_longest_path_length),
        topology_profile=str(topology_profile),
        layout_variant=str(layout_variant),
        label_variant=str(label_variant),
        node_shape_variant=str(node_shape_variant),
        layout_transform_variant=str(layout_transform_variant),
        edge_routing_variant=str(edge_routing_variant),
        node_color_name=str(node_color_name),
        node_count_probabilities=dict(
            uniform_probability_map(
                tuple(int(value) for value in feasible_node_support),
                selected=int(node_count) if explicit_node_count is not None else None,
            )
        ),
        target_longest_path_length_probabilities=dict(
            uniform_probability_map(
                tuple(int(value) for value in feasible_targets),
                selected=int(target_longest_path_length) if explicit_target_length is not None else None,
            )
        ),
        topology_profile_probabilities=dict(topology_probabilities),
        layout_variant_probabilities=dict(layout_probabilities),
        label_variant_probabilities=dict(label_variant_probabilities),
        node_shape_variant_probabilities=dict(node_shape_variant_probabilities),
        layout_transform_variant_probabilities=dict(layout_transform_variant_probabilities),
        edge_routing_variant_probabilities=dict(edge_routing_variant_probabilities),
        node_color_name_probabilities=dict(node_color_name_probabilities),
    )


def _unique_longest_path_by_successors(successors_by_label: Mapping[str, Tuple[str, ...] | list[str]]) -> Tuple[str, ...] | None:
    """Return the unique longest path over a labeled DAG successor map."""

    node_order = tuple(sorted((str(label) for label in successors_by_label.keys()), key=graph_label_sort_key))
    indegree = {str(label): 0 for label in node_order}
    for values in successors_by_label.values():
        for value in values:
            indegree[str(value)] = int(indegree.get(str(value), 0)) + 1
    queue = sorted((label for label, degree in indegree.items() if int(degree) == 0), key=graph_label_sort_key)
    topo_order: list[str] = []
    while queue:
        label = queue.pop(0)
        topo_order.append(str(label))
        for successor in sorted((str(value) for value in successors_by_label.get(str(label), ())), key=graph_label_sort_key):
            indegree[str(successor)] -= 1
            if int(indegree[str(successor)]) == 0:
                queue.append(str(successor))
                queue.sort(key=graph_label_sort_key)
    if len(topo_order) != len(indegree):
        return None
    best_length = {str(label): 0 for label in topo_order}
    best_count = {str(label): 1 for label in topo_order}
    best_path = {str(label): (str(label),) for label in topo_order}
    for source in topo_order:
        for target in sorted((str(value) for value in successors_by_label.get(str(source), ())), key=graph_label_sort_key):
            candidate_length = int(best_length[str(source)]) + 1
            if int(candidate_length) > int(best_length[str(target)]):
                best_length[str(target)] = int(candidate_length)
                best_count[str(target)] = int(best_count[str(source)])
                best_path[str(target)] = (*best_path[str(source)], str(target))
            elif int(candidate_length) == int(best_length[str(target)]):
                best_count[str(target)] += int(best_count[str(source)])
    max_length = max(int(value) for value in best_length.values())
    endpoints = [str(label) for label in topo_order if int(best_length[str(label)]) == int(max_length)]
    if sum(int(best_count[str(label)]) for label in endpoints) != 1:
        return None
    endpoint = next(str(label) for label in endpoints if int(best_count[str(label)]) == 1)
    return tuple(str(label) for label in best_path[str(endpoint)])


def _build_complexity(
    *,
    graph_sample: Any,
    query: _ResolvedQuery,
    render_params: GraphRenderParams,
    rendered_scene: Any,
) -> Any:
    """Build one within-task normalized complexity record."""

    node_count = int(query.node_count)
    path_length = int(query.target_longest_path_length)
    path_label_set = {str(label) for label in graph_sample.target_labels}
    off_path_count = max(0, int(node_count) - len(path_label_set))
    max_edge_count = max(1, int(node_count) * (int(node_count) - 1))
    edge_density = float(graph_sample.edge_count) / float(max_edge_count)
    crossing_norm = normalize_float_with_bounds(float(rendered_scene.crossing_count), (0.0, max(1.0, float(graph_sample.edge_count))))
    off_path_touch_count = sum(
        1
        for label, neighbors in graph_sample.adjacency_by_label.items()
        if str(label) not in path_label_set and any(str(neighbor) in path_label_set for neighbor in neighbors)
    )
    components = {
        "visual_scan": (0.55 * normalize_int_with_bounds(int(node_count), (_DEFAULTS.node_count_min, _DEFAULTS.directed_node_count_max)))
        + (0.25 * normalize_float_with_bounds(float(edge_density), (0.0, 1.0)))
        + (0.20 * normalize_int_with_bounds(int(off_path_count), (1, _DEFAULTS.directed_node_count_max - 3))),
        "topology_reasoning": (0.70 * normalize_int_with_bounds(
            int(path_length),
            (_DEFAULTS.target_longest_path_length_min, _DEFAULTS.target_longest_path_length_max),
        ))
        + (0.20 * normalize_int_with_bounds(int(graph_sample.extra_edge_count), (0, 4)))
        + (0.10 * normalize_int_with_bounds(int(graph_sample.attachment_count), (1, max(1, int(off_path_count))))),
        "ambiguity": (0.55 * normalize_int_with_bounds(int(off_path_touch_count), (1, max(1, int(off_path_count)))))
        + (0.45 * normalize_int_with_bounds(int(graph_sample.extra_edge_count), (0, 4))),
        "clutter": (0.60 * normalize_float_with_bounds(float(edge_density), (0.0, 1.0)))
        + (0.25 * crossing_norm)
        + (0.15 * normalize_int_with_bounds(int(render_params.node_radius_px), (_DEFAULTS.node_radius_min_px, _DEFAULTS.node_radius_max_px))),
    }
    return build_graph_complexity(weights=_COMPLEXITY_WEIGHTS, components=components)


@register_task
class GraphPathLongestPathLengthTask:
    """Count edges in the unique longest directed path of a DAG."""

    task_id = TASK_ID
    domain = "graph"
    task_group = "path"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic graph longest-path instance."""

        query = _resolve_query(int(instance_seed), params=params)
        render_params = resolve_graph_render_params(
            params,
            instance_seed=int(instance_seed),
            task_id=TASK_ID,
            render_defaults=_RENDER_DEFAULTS,
            fallback_defaults=_DEFAULTS,
            node_color_name=str(query.node_color_name),
            node_shape_variant=str(query.node_shape_variant),
            edge_routing_variant=str(query.edge_routing_variant),
        )
        image, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )

        graph_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.graph")
        graph_sample = sample_longest_path_length_graph(
            graph_rng,
            node_count=int(query.node_count),
            target_longest_path_length=int(query.target_longest_path_length),
            topology_profile=str(query.topology_profile),
            label_variant=str(query.label_variant),
        )
        rendered_scene = render_graph_scene(
            graph_sample=graph_sample,
            layout_variant=str(query.layout_variant),
            layout_transform_variant=str(query.layout_transform_variant),
            render_params=render_params,
            layout_seed=int(instance_seed),
            scene_title="Directed Graph",
            directed=True,
            base_image=image,
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description_directed",
                "annotation_hint",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_json_example, prompt_json_example_answer_only = _build_prompt_json_examples()
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=QUERY_ID,
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_directed"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_json_example),
                "json_example_answer_only": str(prompt_json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        annotation_labels = tuple(str(label) for label in graph_sample.target_labels)
        answer_gt = TypedValue(type="integer", value=int(len(annotation_labels) - 1))
        annotation_projection = projected_node_point_annotation(rendered_scene, annotation_labels)
        annotation_path = [list(point) for point in annotation_projection["pixel_point_sequence"]]
        annotation_gt = TypedValue(type="point_sequence", value=list(annotation_path))
        path_edge_labels = tuple(
            canonicalize_graph_edge_label(str(left), str(right), directed=True)
            for left, right in zip(annotation_labels[:-1], annotation_labels[1:])
        )
        path_label_set = {str(label) for label in annotation_labels}
        path_edge_set = {tuple(edge) for edge in path_edge_labels}
        successors_by_label = {str(key): tuple(str(value) for value in values) for key, values in graph_sample.successors_by_label.items()}
        reconstructed_path = _unique_longest_path_by_successors(successors_by_label)
        if reconstructed_path is None or tuple(str(label) for label in reconstructed_path) != annotation_labels:
            raise ValueError("graph longest-path sampler failed to preserve the requested unique longest path")

        node_entities = [
            {
                "entity_id": f"node_{node.label}",
                "entity_kind": "graph_node",
                "label": str(node.label),
                "degree": int(node.degree),
                "in_degree": int(graph_sample.in_degrees_by_label[str(node.label)]),
                "out_degree": int(graph_sample.out_degrees_by_label[str(node.label)]),
                "neighbors": list(node.neighbors),
                "successors": list(node.successors),
                "predecessors": list(node.predecessors),
                "center_px": list(node.center_xy),
                "bbox_xyxy": list(node.bbox_xyxy),
                "is_source_node": bool(str(node.label) == str(graph_sample.source_label)),
                "is_goal_node": bool(str(node.label) == str(graph_sample.goal_label)),
                "is_on_longest_path": bool(str(node.label) in path_label_set),
            }
            for node in rendered_scene.nodes
        ]
        edge_entities = [
            {
                "entity_id": str(edge.edge_id),
                "entity_kind": "graph_edge",
                "node_u_label": str(edge.node_u_label),
                "node_v_label": str(edge.node_v_label),
                "directed": bool(edge.directed),
                "segment_px": [list(edge.segment_px[0]), list(edge.segment_px[1])],
                "route_variant": str(edge.route_variant),
                "control_px": list(edge.control_px) if edge.control_px is not None else None,
                "is_on_longest_path": bool(
                    canonicalize_graph_edge_label(str(edge.node_u_label), str(edge.node_v_label), directed=True) in path_edge_set
                ),
            }
            for edge in rendered_scene.edges
        ]
        complexity = _build_complexity(
            graph_sample=graph_sample,
            query=query,
            render_params=render_params,
            rendered_scene=rendered_scene,
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "graph_longest_path_length",
                "entities": [*node_entities, *edge_entities],
                "relations": {
                    "query_id": QUERY_ID,
                    "relation_rule": "unique_global_longest_directed_path_in_dag",
                    "graph_directionality": "directed",
                    "source_label": str(graph_sample.source_label),
                    "goal_label": str(graph_sample.goal_label),
                    "longest_path_labels": list(annotation_labels),
                    "longest_path_edge_labels": [list(edge) for edge in path_edge_labels],
                    "longest_path_length": int(len(annotation_labels) - 1),
                    "successors_by_label": {str(key): list(values) for key, values in graph_sample.successors_by_label.items()},
                    "predecessors_by_label": {str(key): list(values) for key, values in graph_sample.predecessors_by_label.items()},
                    "adjacency_by_label": {str(key): list(values) for key, values in graph_sample.adjacency_by_label.items()},
                    "degrees_by_label": {str(key): int(value) for key, value in graph_sample.degrees_by_label.items()},
                    "in_degrees_by_label": {str(key): int(value) for key, value in graph_sample.in_degrees_by_label.items()},
                    "out_degrees_by_label": {str(key): int(value) for key, value in graph_sample.out_degrees_by_label.items()},
                    "edge_labels": [list(edge) for edge in graph_sample.edge_labels],
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(rendered_scene.panel_geometry),
                },
            },
            "query_spec": {
                "query_id": QUERY_ID,
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": QUERY_ID,
                    "internal_query_id": QUERY_ID,
                    "query_id_probabilities": {QUERY_ID: 1.0},
                    "graph_directionality": "directed",
                    "node_count": int(query.node_count),
                    "edge_count": int(graph_sample.edge_count),
                    "target_longest_path_length": int(query.target_longest_path_length),
                    "source_label": str(graph_sample.source_label),
                    "goal_label": str(graph_sample.goal_label),
                    "node_count_probabilities": dict(query.node_count_probabilities),
                    "target_longest_path_length_probabilities": dict(query.target_longest_path_length_probabilities),
                    "topology_profile": str(query.topology_profile),
                    "topology_profile_probabilities": dict(query.topology_profile_probabilities),
                    "layout_variant": str(query.layout_variant),
                    "layout_variant_probabilities": dict(query.layout_variant_probabilities),
                    "label_variant": str(query.label_variant),
                    "label_variant_probabilities": dict(query.label_variant_probabilities),
                    "node_shape_variant": str(query.node_shape_variant),
                    "node_shape_variant_probabilities": dict(query.node_shape_variant_probabilities),
                    "layout_transform_variant": str(query.layout_transform_variant),
                    "layout_transform_variant_probabilities": dict(query.layout_transform_variant_probabilities),
                    "edge_routing_variant": str(query.edge_routing_variant),
                    "edge_routing_variant_probabilities": dict(query.edge_routing_variant_probabilities),
                    "node_color_name": str(query.node_color_name),
                    "node_color_name_probabilities": dict(query.node_color_name_probabilities),
                },
            },
            "render_spec": {
                "canvas_size": list(rendered_scene.panel_geometry["canvas_size"]),
                "coord_space": "pixel",
                "panel_geometry": dict(rendered_scene.panel_geometry),
                "style": {
                    "node_color_name": str(query.node_color_name),
                    "theme_tone": str(render_params.theme_tone),
                    "panel_style_variant": str(render_params.panel_style_variant),
                    "background_color_rgb": list(render_params.background_color_rgb),
                    "panel_fill_rgb": list(render_params.panel_fill_rgb),
                    "panel_border_rgb": list(render_params.panel_border_rgb),
                    "title_color_rgb": list(render_params.title_color_rgb),
                    "edge_color_rgb": list(render_params.edge_color_rgb),
                    "node_fill_rgb": list(render_params.node_fill_rgb),
                    "node_border_rgb": list(render_params.node_border_rgb),
                    "label_text_rgb": list(render_params.label_text_rgb),
                    "label_stroke_rgb": list(render_params.label_stroke_rgb),
                    "node_shape_variant": str(render_params.node_shape_variant),
                    "node_radius_px": int(render_params.node_radius_px),
                    "edge_width_px": int(render_params.edge_width_px),
                    "edge_routing_variant": str(rendered_scene.edge_routing_variant),
                    "arrow_length_px": int(render_params.arrow_length_px),
                    "arrow_width_px": int(render_params.arrow_width_px),
                    "node_border_width_px": int(render_params.node_border_width_px),
                    "label_font_size_px": int(render_params.label_font_size_px),
                    "resolved_label_font_size_px": int(rendered_scene.resolved_label_font_size_px),
                    "label_stroke_width_px": int(rendered_scene.resolved_label_stroke_width_px),
                    "background_meta": dict(background_meta),
                    "post_image_noise_meta": dict(post_noise_meta),
                },
            },
            "render_map": {"image_id": "img0", "anchors": {}},
            "execution_trace": {
                "query_id": QUERY_ID,
                "internal_query_id": QUERY_ID,
                "query_id_probabilities": {QUERY_ID: 1.0},
                "scene_variant": str(rendered_scene.layout_variant),
                "question_format": "directed_longest_path_length",
                "graph_directionality": "directed",
                "node_count": int(query.node_count),
                "edge_count": int(graph_sample.edge_count),
                "target_longest_path_length": int(graph_sample.target_longest_path_length),
                "source_label": str(graph_sample.source_label),
                "goal_label": str(graph_sample.goal_label),
                "longest_path_labels": list(annotation_labels),
                "longest_path_edge_labels": [list(edge) for edge in path_edge_labels],
                "attachment_count": int(graph_sample.attachment_count),
                "extra_edge_count": int(graph_sample.extra_edge_count),
                "degrees_by_label": {str(key): int(value) for key, value in graph_sample.degrees_by_label.items()},
                "in_degrees_by_label": {str(key): int(value) for key, value in graph_sample.in_degrees_by_label.items()},
                "out_degrees_by_label": {str(key): int(value) for key, value in graph_sample.out_degrees_by_label.items()},
                "adjacency_by_label": {str(key): list(values) for key, values in graph_sample.adjacency_by_label.items()},
                "successors_by_label": {str(key): list(values) for key, values in graph_sample.successors_by_label.items()},
                "predecessors_by_label": {str(key): list(values) for key, values in graph_sample.predecessors_by_label.items()},
                "topology_profile": str(graph_sample.topology_profile),
                "topology_profile_probabilities": dict(query.topology_profile_probabilities),
                "label_variant": str(graph_sample.label_variant),
                "node_shape_variant": str(render_params.node_shape_variant),
                "layout_variant_requested": str(query.layout_variant),
                "layout_variant_used": str(rendered_scene.layout_variant),
                "layout_transform_variant": str(rendered_scene.layout_transform_variant),
                "edge_routing_variant": str(rendered_scene.edge_routing_variant),
                "node_color_name": str(query.node_color_name),
                "crossing_count": int(rendered_scene.crossing_count),
            },
            "witness_symbolic": {
                "type": "node_path",
                "nodes": list(annotation_labels),
                "source_label": str(graph_sample.source_label),
                "goal_label": str(graph_sample.goal_label),
            },
            "projected_annotation": {
                "type": "point_sequence",
                "point_sequence": list(annotation_path),
                **dict(annotation_projection),
            },
        }

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=QUERY_ID,
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["GraphPathLongestPathLengthTask"]
