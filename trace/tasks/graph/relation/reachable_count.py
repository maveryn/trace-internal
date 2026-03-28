"""Count directed-graph nodes reachable from one queried source node."""

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
from ...shared.graph_algorithms import bfs_dist_count_by_adjacency
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
    SUPPORTED_LABEL_VARIANTS,
    SUPPORTED_LAYOUT_VARIANTS,
    SUPPORTED_REACHABLE_TASK_VARIANTS,
    SUPPORTED_TOPOLOGY_PROFILES,
    feasible_node_counts_for_reachable_count,
    graph_label_sort_key,
    sample_reachable_count_graph,
)
from ..shared.graph_scene import (
    GraphRenderParams,
    SUPPORTED_LAYOUT_TRANSFORM_VARIANTS,
    SUPPORTED_NODE_SHAPE_VARIANTS,
    render_graph_scene,
)
from ..shared.style import SUPPORTED_NODE_COLOR_NAMES
from ..shared.task_support import resolve_graph_named_variant, resolve_graph_render_params
from ..shared.visual_defaults import load_graph_background_defaults, load_graph_noise_defaults


TASK_ID = "task_graph_relation_reachable_count"


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for graph reachable-count scenes."""

    node_count_min: int = 5
    directed_node_count_max: int = 9
    target_reachable_count_min: int = 1
    target_reachable_count_max: int = 7
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
    """Resolved support and style axes for one reachable-count instance."""

    task_variant: str
    node_count: int
    target_reachable_count: int
    topology_profile: str
    layout_variant: str
    label_variant: str
    node_shape_variant: str
    layout_transform_variant: str
    node_color_name: str
    task_variant_probabilities: Dict[str, float]
    node_count_probabilities: Dict[str, float]
    target_reachable_count_probabilities: Dict[str, float]
    topology_profile_probabilities: Dict[str, float]
    layout_variant_probabilities: Dict[str, float]
    label_variant_probabilities: Dict[str, float]
    node_shape_variant_probabilities: Dict[str, float]
    layout_transform_variant_probabilities: Dict[str, float]
    node_color_name_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("graph", "relation")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_graph_background_defaults(task_group="relation")
POST_IMAGE_NOISE_DEFAULTS = load_graph_noise_defaults(task_group="relation", apply_prob=0.0)
_COMPLEXITY_WEIGHTS = resolve_graph_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)


def _build_prompt_json_examples(*, label_variant: str) -> Tuple[str, str]:
    """Return prompt examples that match the active node-label format."""

    example_evidence = ["2", "5", "8"] if str(label_variant) == "numbers" else ["B", "D", "H"]
    return (
        json.dumps({"evidence": example_evidence, "answer": 3}, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
        json.dumps({"answer": 3}, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
    )


def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    """Resolve balanced support for one directed reachable-count query."""

    variant_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.task_variant")
    task_variant, task_variant_probabilities = resolve_graph_named_variant(
        variant_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key="task_variant",
        weights_key="task_variant_weights",
        balance_flag_key="balanced_task_variant_sampling",
        supported=SUPPORTED_REACHABLE_TASK_VARIANTS,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace="task_variant",
    )
    node_count_min = int(params.get("node_count_min", group_default(_GEN_DEFAULTS, "node_count_min", _DEFAULTS.node_count_min)))
    node_count_max = int(
        params.get(
            "directed_node_count_max",
            group_default(_GEN_DEFAULTS, "directed_node_count_max", _DEFAULTS.directed_node_count_max),
        )
    )
    target_count_min = int(
        params.get(
            "target_reachable_count_min",
            group_default(_GEN_DEFAULTS, "target_reachable_count_min", _DEFAULTS.target_reachable_count_min),
        )
    )
    target_count_max = int(
        params.get(
            "target_reachable_count_max",
            group_default(_GEN_DEFAULTS, "target_reachable_count_max", _DEFAULTS.target_reachable_count_max),
        )
    )

    target_support = tuple(range(int(target_count_min), int(target_count_max) + 1))
    if not target_support:
        raise ValueError("target_reachable_count support is empty for graph reachable counting")

    selection_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:query_support",
        )
    )

    feasible_support_by_target: Dict[int, Tuple[int, ...]] = {}
    feasible_targets = []
    for target_reachable_count in target_support:
        feasible_nodes = feasible_node_counts_for_reachable_count(
            target_reachable_count=int(target_reachable_count),
            node_count_min=int(node_count_min),
            node_count_max=int(node_count_max),
        )
        if feasible_nodes:
            feasible_targets.append(int(target_reachable_count))
            feasible_support_by_target[int(target_reachable_count)] = tuple(int(value) for value in feasible_nodes)
    if not feasible_targets:
        raise ValueError("no feasible graph reachable-count support exists for the configured ranges")

    explicit_target_count = params.get("target_reachable_count")
    explicit_node_count = params.get("node_count")
    target_reachable_count = int(explicit_target_count) if explicit_target_count is not None else None

    filtered_targets = [
        int(target) for target in feasible_targets if target_reachable_count is None or int(target) == int(target_reachable_count)
    ]
    if not filtered_targets:
        raise ValueError("requested reachable-count target is infeasible for the configured node-count range")

    if target_reachable_count is None:
        target_reachable_count = int(filtered_targets[int(selection_index % len(filtered_targets))])

    feasible_node_support = feasible_support_by_target[int(target_reachable_count)]
    if explicit_node_count is not None:
        node_count = int(explicit_node_count)
        if int(node_count) not in feasible_node_support:
            raise ValueError("node_count is outside feasible support for the requested graph reachable query")
    else:
        node_count = int(feasible_node_support[int(selection_index % len(feasible_node_support))])

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
    layout_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.layout_variant")
    layout_variant, layout_probabilities = resolve_graph_named_variant(
        layout_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key="layout_variant",
        weights_key="layout_variant_weights",
        balance_flag_key="balanced_layout_variant_sampling",
        supported=SUPPORTED_LAYOUT_VARIANTS,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace="layout_variant",
    )
    label_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.label_variant")
    label_variant, label_variant_probabilities = resolve_graph_named_variant(
        label_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key="label_variant",
        weights_key="label_variant_weights",
        balance_flag_key="balanced_label_variant_sampling",
        supported=SUPPORTED_LABEL_VARIANTS,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace="label_variant",
    )
    shape_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.node_shape_variant")
    node_shape_variant, node_shape_variant_probabilities = resolve_graph_named_variant(
        shape_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key="node_shape_variant",
        weights_key="node_shape_variant_weights",
        balance_flag_key="balanced_node_shape_variant_sampling",
        supported=SUPPORTED_NODE_SHAPE_VARIANTS,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace="node_shape_variant",
    )
    transform_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.layout_transform_variant")
    layout_transform_variant, layout_transform_variant_probabilities = resolve_graph_named_variant(
        transform_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key="layout_transform_variant",
        weights_key="layout_transform_variant_weights",
        balance_flag_key="balanced_layout_transform_variant_sampling",
        supported=SUPPORTED_LAYOUT_TRANSFORM_VARIANTS,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace="layout_transform_variant",
    )
    color_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.node_color_name")
    node_color_name, node_color_name_probabilities = resolve_graph_named_variant(
        color_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key="node_color_name",
        weights_key="node_color_name_weights",
        balance_flag_key="balanced_node_color_name_sampling",
        supported=SUPPORTED_NODE_COLOR_NAMES,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace="node_color_name",
    )

    return _ResolvedQuery(
        task_variant=str(task_variant),
        node_count=int(node_count),
        target_reachable_count=int(target_reachable_count),
        topology_profile=str(topology_profile),
        layout_variant=str(layout_variant),
        label_variant=str(label_variant),
        node_shape_variant=str(node_shape_variant),
        layout_transform_variant=str(layout_transform_variant),
        node_color_name=str(node_color_name),
        task_variant_probabilities=dict(task_variant_probabilities),
        node_count_probabilities=dict(
            uniform_probability_map(
                tuple(int(value) for value in feasible_node_support),
                selected=int(node_count) if explicit_node_count is not None else None,
            )
        ),
        target_reachable_count_probabilities=dict(
            uniform_probability_map(
                tuple(int(value) for value in filtered_targets),
                selected=int(target_reachable_count) if explicit_target_count is not None else None,
            )
        ),
        topology_profile_probabilities=dict(topology_probabilities),
        layout_variant_probabilities=dict(layout_probabilities),
        label_variant_probabilities=dict(label_variant_probabilities),
        node_shape_variant_probabilities=dict(node_shape_variant_probabilities),
        layout_transform_variant_probabilities=dict(layout_transform_variant_probabilities),
        node_color_name_probabilities=dict(node_color_name_probabilities),
    )


def _build_complexity(
    *,
    graph_sample,
    query: _ResolvedQuery,
    render_params: GraphRenderParams,
    rendered_scene,
) -> Any:
    """Build one within-task normalized complexity record."""

    node_count = int(query.node_count)
    reachable_count = int(query.target_reachable_count)
    unreachable_count = max(0, int(node_count) - int(reachable_count))
    max_edge_count = max(1, int(node_count) * (int(node_count) - 1))
    edge_density = float(graph_sample.edge_count) / float(max_edge_count)
    crossing_norm = normalize_float_with_bounds(
        float(rendered_scene.crossing_count),
        (0.0, max(1.0, float(graph_sample.edge_count))),
    )
    reachable_label_set = {str(label) for label in graph_sample.target_labels}
    boundary_touch_count = sum(
        1
        for label, neighbors in graph_sample.successors_by_label.items()
        if str(label) not in reachable_label_set and any(str(neighbor) in reachable_label_set for neighbor in neighbors)
    )
    source_out_degree = int(graph_sample.out_degrees_by_label[str(graph_sample.query_label)])
    components = {
        "visual_scan": (0.55 * normalize_int_with_bounds(int(node_count), (_DEFAULTS.node_count_min, _DEFAULTS.directed_node_count_max)))
        + (0.20 * normalize_float_with_bounds(float(edge_density), (0.0, 1.0)))
        + (0.25 * normalize_int_with_bounds(int(unreachable_count), (1, _DEFAULTS.directed_node_count_max - 1))),
        "topology_reasoning": (0.65 * normalize_int_with_bounds(
            int(reachable_count),
            (_DEFAULTS.target_reachable_count_min, _DEFAULTS.target_reachable_count_max),
        ))
        + (0.20 * normalize_int_with_bounds(int(graph_sample.reachable_edge_count), (0, _DEFAULTS.directed_node_count_max + 2)))
        + (0.15 * normalize_int_with_bounds(int(source_out_degree), (0, _DEFAULTS.directed_node_count_max - 1))),
        "ambiguity": (0.55 * normalize_int_with_bounds(int(boundary_touch_count), (0, _DEFAULTS.directed_node_count_max - 1)))
        + (0.25 * normalize_int_with_bounds(int(unreachable_count), (1, _DEFAULTS.directed_node_count_max - 1)))
        + (0.20 * normalize_int_with_bounds(int(graph_sample.unreachable_edge_count), (0, _DEFAULTS.directed_node_count_max + 2))),
        "clutter": (0.60 * normalize_float_with_bounds(float(edge_density), (0.0, 1.0)))
        + (0.25 * crossing_norm)
        + (0.15 * normalize_int_with_bounds(
            int(render_params.node_radius_px),
            (_DEFAULTS.node_radius_min_px, _DEFAULTS.node_radius_max_px),
        )),
    }
    return build_graph_complexity(weights=_COMPLEXITY_WEIGHTS, components=components)


@register_task
class GraphRelationReachableCountTask:
    """Count directed-graph nodes reachable from one queried source node."""

    task_id = TASK_ID
    domain = "graph"
    task_group = "relation"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic reachable-count graph instance."""

        query = _resolve_query(int(instance_seed), params=params)
        render_params = resolve_graph_render_params(
            params,
            instance_seed=int(instance_seed),
            task_id=TASK_ID,
            render_defaults=_RENDER_DEFAULTS,
            fallback_defaults=_DEFAULTS,
            node_color_name=str(query.node_color_name),
            node_shape_variant=str(query.node_shape_variant),
        )
        image, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )

        graph_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.graph")
        graph_sample = sample_reachable_count_graph(
            graph_rng,
            node_count=int(query.node_count),
            target_reachable_count=int(query.target_reachable_count),
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
                "task_family_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description_directed",
                "question_text_reachable_count",
                "evidence_hint_reachable_count",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_json_example, prompt_json_example_answer_only = _build_prompt_json_examples(
            label_variant=str(query.label_variant)
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            task_family_key=str(prompt_defaults["task_family_key"]),
            task_key=str(prompt_defaults["task_key"]),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_directed"]),
                "question_text": str(prompt_defaults["question_text_reachable_count"]).format(
                    query_label=str(graph_sample.query_label)
                ),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint_reachable_count"]).format(
                    query_label=str(graph_sample.query_label)
                ),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_json_example),
                "json_example_answer_only": str(prompt_json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        evidence_labels = tuple(sorted((str(label) for label in graph_sample.target_labels), key=graph_label_sort_key))
        answer_gt = TypedValue(type="integer", value=int(len(evidence_labels)))
        evidence_gt = TypedValue(type="label_set", value=list(evidence_labels))
        node_entities = [
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
                "is_query_node": bool(str(node.label) == str(graph_sample.query_label)),
                "is_reachable": bool(str(node.label) in set(evidence_labels)),
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
            }
            for edge in rendered_scene.edges
        ]
        evidence_node_bboxes = [
            list(next(node.bbox_xyxy for node in rendered_scene.nodes if str(node.label) == str(label)))
            for label in evidence_labels
        ]
        evidence_node_centers = [
            list(next(node.center_xy for node in rendered_scene.nodes if str(node.label) == str(label)))
            for label in evidence_labels
        ]
        successors_by_label = {
            str(key): tuple(str(value) for value in values)
            for key, values in graph_sample.successors_by_label.items()
        }
        dist_start, _ = bfs_dist_count_by_adjacency(successors_by_label, start=str(graph_sample.query_label))
        reachable_labels = tuple(sorted((str(label) for label in dist_start.keys()), key=graph_label_sort_key))
        if tuple(reachable_labels) != tuple(evidence_labels):
            raise ValueError("reachable-count sampler failed to preserve the requested reachable set")

        complexity = _build_complexity(
            graph_sample=graph_sample,
            query=query,
            render_params=render_params,
            rendered_scene=rendered_scene,
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "graph_reachable_relation",
                "entities": [*node_entities, *edge_entities],
                "relations": {
                    "relation_rule": "reachable_from_query_node_following_arrow_direction_including_query",
                    "graph_directionality": "directed",
                    "query_label": str(graph_sample.query_label),
                    "matching_labels": list(evidence_labels),
                    "unreachable_labels": list(graph_sample.unreachable_labels),
                    "adjacency_by_label": {str(key): list(values) for key, values in graph_sample.successors_by_label.items()},
                    "successors_by_label": {str(key): list(values) for key, values in graph_sample.successors_by_label.items()},
                    "predecessors_by_label": {str(key): list(values) for key, values in graph_sample.predecessors_by_label.items()},
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
                "task_variant": str(query.task_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "graph_directionality": "directed",
                    "task_variant_probabilities": dict(query.task_variant_probabilities),
                    "node_count": int(query.node_count),
                    "edge_count": int(graph_sample.edge_count),
                    "target_reachable_count": int(query.target_reachable_count),
                    "query_label": str(graph_sample.query_label),
                    "node_count_probabilities": dict(query.node_count_probabilities),
                    "target_reachable_count_probabilities": dict(query.target_reachable_count_probabilities),
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
            "render_map": {
                "image_id": "img0",
                "anchors": {},
            },
            "execution_trace": {
                "task_variant": str(query.task_variant),
                "scene_variant": str(rendered_scene.layout_variant),
                "question_format": "count_reachable_nodes_including_query",
                "graph_directionality": "directed",
                "node_count": int(query.node_count),
                "edge_count": int(graph_sample.edge_count),
                "target_reachable_count": int(graph_sample.target_reachable_count),
                "query_label": str(graph_sample.query_label),
                "matching_labels": list(evidence_labels),
                "unreachable_labels": list(graph_sample.unreachable_labels),
                "successors_by_label": {str(key): list(values) for key, values in graph_sample.successors_by_label.items()},
                "predecessors_by_label": {str(key): list(values) for key, values in graph_sample.predecessors_by_label.items()},
                "topology_profile": str(graph_sample.topology_profile),
                "label_variant": str(graph_sample.label_variant),
                "node_shape_variant": str(render_params.node_shape_variant),
                "layout_variant_requested": str(query.layout_variant),
                "layout_variant_used": str(rendered_scene.layout_variant),
                "layout_transform_variant": str(rendered_scene.layout_transform_variant),
                "node_color_name": str(query.node_color_name),
                "crossing_count": int(rendered_scene.crossing_count),
                "reachable_edge_count": int(graph_sample.reachable_edge_count),
                "unreachable_edge_count": int(graph_sample.unreachable_edge_count),
            },
            "witness_symbolic": {
                "type": "label_set",
                "label_set": list(evidence_labels),
                "query_label": str(graph_sample.query_label),
            },
            "projected_evidence": {
                "type": "label_set",
                "label_set": list(evidence_labels),
                "pixel_point_set": list(evidence_node_centers),
                "pixel_bbox_set": list(evidence_node_bboxes),
            },
        }

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            task_variant=str(query.task_variant),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
