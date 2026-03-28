"""Count nodes in the unique cycle of one undirected graph."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

import networkx as nx

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
    SUPPORTED_CYCLE_TASK_VARIANTS,
    SUPPORTED_LABEL_VARIANTS,
    SUPPORTED_LAYOUT_VARIANTS,
    SUPPORTED_TOPOLOGY_PROFILES,
    feasible_node_counts_for_unique_cycle_size,
    graph_label_sort_key,
    sample_unique_cycle_graph,
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


TASK_ID = "task_graph_relation_unique_cycle_size"


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for graph unique-cycle scenes."""

    node_count_min: int = 5
    node_count_max: int = 10
    target_cycle_size_min: int = 3
    target_cycle_size_max: int = 10
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
class _ResolvedQuery:
    """Resolved support and style axes for one unique-cycle instance."""

    task_variant: str
    node_count: int
    target_cycle_size: int
    topology_profile: str
    layout_variant: str
    label_variant: str
    node_shape_variant: str
    layout_transform_variant: str
    node_color_name: str
    task_variant_probabilities: Dict[str, float]
    node_count_probabilities: Dict[str, float]
    target_cycle_size_probabilities: Dict[str, float]
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

    example_evidence = ["2", "5", "7", "9"] if str(label_variant) == "numbers" else ["B", "D", "H", "J"]
    return (
        json.dumps({"evidence": example_evidence, "answer": 4}, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
        json.dumps({"answer": 4}, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
    )


def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    """Resolve balanced support for one unique-cycle-size query."""

    variant_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.task_variant")
    task_variant, task_variant_probabilities = resolve_graph_named_variant(
        variant_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key="task_variant",
        weights_key="task_variant_weights",
        balance_flag_key="balanced_task_variant_sampling",
        supported=SUPPORTED_CYCLE_TASK_VARIANTS,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace="task_variant",
    )
    node_count_min = int(params.get("node_count_min", group_default(_GEN_DEFAULTS, "node_count_min", _DEFAULTS.node_count_min)))
    node_count_max = int(params.get("node_count_max", group_default(_GEN_DEFAULTS, "node_count_max", _DEFAULTS.node_count_max)))
    target_cycle_size_min = int(
        params.get("target_cycle_size_min", group_default(_GEN_DEFAULTS, "target_cycle_size_min", _DEFAULTS.target_cycle_size_min))
    )
    target_cycle_size_max = int(
        params.get("target_cycle_size_max", group_default(_GEN_DEFAULTS, "target_cycle_size_max", _DEFAULTS.target_cycle_size_max))
    )
    target_support = tuple(range(int(target_cycle_size_min), int(target_cycle_size_max) + 1))
    if not target_support:
        raise ValueError("target_cycle_size support is empty for graph unique-cycle relation")

    selection_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:query_support",
        )
    )

    feasible_targets = []
    feasible_node_support_by_target: Dict[int, Tuple[int, ...]] = {}
    for target_cycle_size in target_support:
        feasible_nodes = feasible_node_counts_for_unique_cycle_size(
            target_cycle_size=int(target_cycle_size),
            node_count_min=int(node_count_min),
            node_count_max=int(node_count_max),
        )
        if feasible_nodes:
            feasible_targets.append(int(target_cycle_size))
            feasible_node_support_by_target[int(target_cycle_size)] = tuple(int(value) for value in feasible_nodes)
    if not feasible_targets:
        raise ValueError("no feasible graph unique-cycle support exists for the configured ranges")

    explicit_target_cycle_size = params.get("target_cycle_size")
    explicit_node_count = params.get("node_count")
    if explicit_target_cycle_size is not None:
        target_cycle_size = int(explicit_target_cycle_size)
        if int(target_cycle_size) not in feasible_targets:
            raise ValueError("requested target_cycle_size is infeasible")
    else:
        target_cycle_size = int(feasible_targets[int(selection_index % len(feasible_targets))])

    feasible_node_support = feasible_node_support_by_target[int(target_cycle_size)]
    if explicit_node_count is not None:
        node_count = int(explicit_node_count)
        if int(node_count) not in feasible_node_support:
            raise ValueError("node_count is outside feasible support for the requested unique-cycle query")
    else:
        node_count = int(feasible_node_support[(int(selection_index) // max(1, len(feasible_targets))) % len(feasible_node_support)])

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
        target_cycle_size=int(target_cycle_size),
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
        target_cycle_size_probabilities=dict(
            uniform_probability_map(
                tuple(int(value) for value in feasible_targets),
                selected=int(target_cycle_size) if explicit_target_cycle_size is not None else None,
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
    edge_count = int(graph_sample.edge_count)
    max_edges = int((node_count * (node_count - 1)) // 2)
    edge_density = 0.0 if int(max_edges) <= 0 else float(edge_count) / float(max_edges)
    crossing_norm = normalize_float_with_bounds(float(rendered_scene.crossing_count), (0.0, max(1.0, float(max_edges))))
    attachment_count = int(graph_sample.attachment_count)
    cycle_norm = normalize_int_with_bounds(int(query.target_cycle_size), (3, _DEFAULTS.target_cycle_size_max))
    cycle_midrange = max(0.0, 1.0 - abs((2.0 * float(cycle_norm)) - 1.0))
    cycle_labels = set(str(label) for label in graph_sample.target_labels)
    non_cycle_degree_two_or_more = sum(
        1
        for label, degree in graph_sample.degrees_by_label.items()
        if str(label) not in cycle_labels and int(degree) >= 2
    )

    components = {
        "visual_scan": (0.60 * normalize_int_with_bounds(int(node_count), (_DEFAULTS.node_count_min, _DEFAULTS.node_count_max)))
        + (0.25 * normalize_int_with_bounds(int(attachment_count), (0, _DEFAULTS.node_count_max - 3)))
        + (0.15 * normalize_float_with_bounds(float(edge_density), (0.0, 1.0))),
        "topology_reasoning": (0.55 * normalize_int_with_bounds(int(query.target_cycle_size), (3, _DEFAULTS.target_cycle_size_max)))
        + (0.45 * normalize_int_with_bounds(int(attachment_count), (0, _DEFAULTS.node_count_max - 3))),
        "ambiguity": (0.55 * normalize_int_with_bounds(int(non_cycle_degree_two_or_more), (0, _DEFAULTS.node_count_max - 3)))
        + (0.45 * float(cycle_midrange)),
        "clutter": (0.55 * normalize_float_with_bounds(float(edge_density), (0.0, 1.0)))
        + (0.25 * crossing_norm)
        + (0.20 * normalize_int_with_bounds(int(render_params.node_radius_px), (_DEFAULTS.node_radius_min_px, _DEFAULTS.node_radius_max_px))),
    }
    return build_graph_complexity(weights=_COMPLEXITY_WEIGHTS, components=components)


@register_task
class GraphRelationUniqueCycleSizeTask:
    """Count nodes in the unique cycle of one labeled graph."""

    task_id = TASK_ID
    domain = "graph"
    task_group = "relation"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic unique-cycle graph instance."""

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
        graph_sample = sample_unique_cycle_graph(
            graph_rng,
            node_count=int(query.node_count),
            target_cycle_size=int(query.target_cycle_size),
            topology_profile=str(query.topology_profile),
            label_variant=str(query.label_variant),
        )
        rendered_scene = render_graph_scene(
            graph_sample=graph_sample,
            layout_variant=str(query.layout_variant),
            layout_transform_variant=str(query.layout_transform_variant),
            render_params=render_params,
            layout_seed=int(instance_seed),
            scene_title="Graph",
            directed=False,
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
                "object_description",
                "question_text_unique_cycle_size",
                "evidence_hint",
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
                "object_description": str(prompt_defaults["object_description"]),
                "question_text": str(prompt_defaults["question_text_unique_cycle_size"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]),
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
                "is_cycle_node": bool(str(node.label) in evidence_labels),
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
        cycle_basis = nx.cycle_basis(graph_sample.graph)
        cycle_labels_by_basis = [
            tuple(
                sorted(
                    (
                        next(
                            str(label)
                            for original_node, label in zip(graph_sample.graph.nodes(), graph_sample.node_labels)
                            if int(original_node) == int(node)
                        )
                        for node in cycle
                    ),
                    key=graph_label_sort_key,
                )
            )
            for cycle in cycle_basis
        ]
        complexity = _build_complexity(
            graph_sample=graph_sample,
            query=query,
            render_params=render_params,
            rendered_scene=rendered_scene,
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "graph_unique_cycle_relation",
                "entities": [*node_entities, *edge_entities],
                "relations": {
                    "relation_rule": "node_belongs_to_unique_cycle",
                    "graph_directionality": "undirected",
                    "matching_labels": list(evidence_labels),
                    "adjacency_by_label": {str(key): list(values) for key, values in graph_sample.adjacency_by_label.items()},
                    "degrees_by_label": {str(key): int(value) for key, value in graph_sample.degrees_by_label.items()},
                    "edge_labels": [list(edge) for edge in graph_sample.edge_labels],
                    "cycle_basis_by_label": [list(cycle) for cycle in cycle_labels_by_basis],
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
                    "graph_directionality": "undirected",
                    "task_variant_probabilities": dict(query.task_variant_probabilities),
                    "node_count": int(query.node_count),
                    "edge_count": int(graph_sample.edge_count),
                    "target_cycle_size": int(query.target_cycle_size),
                    "node_count_probabilities": dict(query.node_count_probabilities),
                    "target_cycle_size_probabilities": dict(query.target_cycle_size_probabilities),
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
            "render_map": {"image_id": "img0", "anchors": {}},
            "execution_trace": {
                "task_variant": str(query.task_variant),
                "scene_variant": str(rendered_scene.layout_variant),
                "question_format": "count_nodes_in_unique_cycle",
                "graph_directionality": "undirected",
                "node_count": int(query.node_count),
                "edge_count": int(graph_sample.edge_count),
                "target_cycle_size": int(graph_sample.target_cycle_size),
                "attachment_count": int(graph_sample.attachment_count),
                "matching_labels": list(evidence_labels),
                "degrees_by_label": {str(key): int(value) for key, value in graph_sample.degrees_by_label.items()},
                "adjacency_by_label": {str(key): list(values) for key, values in graph_sample.adjacency_by_label.items()},
                "topology_profile": str(graph_sample.topology_profile),
                "label_variant": str(graph_sample.label_variant),
                "node_shape_variant": str(render_params.node_shape_variant),
                "layout_variant_requested": str(query.layout_variant),
                "layout_variant_used": str(rendered_scene.layout_variant),
                "layout_transform_variant": str(rendered_scene.layout_transform_variant),
                "node_color_name": str(query.node_color_name),
                "crossing_count": int(rendered_scene.crossing_count),
                "cycle_basis_by_label": [list(cycle) for cycle in cycle_labels_by_basis],
            },
            "witness_symbolic": {
                "type": "label_set",
                "label_set": list(evidence_labels),
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
