"""Return the total weight of the unique minimum spanning tree in a weighted graph."""

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
    SUPPORTED_LABEL_VARIANTS,
    SUPPORTED_LAYOUT_VARIANTS,
    SUPPORTED_OPTIMIZATION_QUERY_IDS,
    SUPPORTED_TOPOLOGY_PROFILES,
    canonicalize_graph_edge_label,
    feasible_extra_edge_counts_for_minimum_spanning_tree,
    sample_minimum_spanning_tree_weight_graph,
)
from ..shared.graph_scene import (
    GraphRenderParams,
    SUPPORTED_LAYOUT_TRANSFORM_VARIANTS,
    SUPPORTED_NODE_SHAPE_VARIANTS,
    projected_edge_pair_evidence,
    render_graph_scene,
)
from ..shared.fixed_query_task import rewrite_graph_query_output
from ..shared.style import SUPPORTED_NODE_COLOR_NAMES
from ..shared.task_support import resolve_graph_named_variant, resolve_graph_render_params
from ..shared.visual_defaults import load_graph_background_defaults, load_graph_noise_defaults


TASK_ID = "task_graph__node_link__mst_weight"


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for weighted graph MST scenes."""

    node_count_min: int = 5
    node_count_max: int = 8
    extra_edge_count_min: int = 1
    extra_edge_count_max: int = 2
    edge_weight_min: int = 1
    edge_weight_max: int = 9
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
    edge_weight_label_font_size_px: int = 20
    edge_weight_label_offset_px: int = 20
    edge_weight_label_padding_px: int = 6


@dataclass(frozen=True)
class _ResolvedQuery:
    """Resolved support and style axes for one MST-weight instance."""

    query_id: str
    node_count: int
    extra_edge_count: int
    edge_weight_min: int
    edge_weight_max: int
    topology_profile: str
    layout_variant: str
    label_variant: str
    node_shape_variant: str
    layout_transform_variant: str
    node_color_name: str
    query_id_probabilities: Dict[str, float]
    node_count_probabilities: Dict[str, float]
    extra_edge_count_probabilities: Dict[str, float]
    topology_profile_probabilities: Dict[str, float]
    layout_variant_probabilities: Dict[str, float]
    label_variant_probabilities: Dict[str, float]
    node_shape_variant_probabilities: Dict[str, float]
    layout_transform_variant_probabilities: Dict[str, float]
    node_color_name_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("graph", "optimization")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_graph_background_defaults(task_group="optimization")
POST_IMAGE_NOISE_DEFAULTS = load_graph_noise_defaults(task_group="optimization", apply_prob=0.0)
_COMPLEXITY_WEIGHTS = resolve_graph_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)


def _build_prompt_json_examples(*, label_variant: str) -> Tuple[str, str]:
    """Return prompt examples that match the pixel-space edge evidence format."""

    example_evidence = [[[180, 220], [310, 180]], [[310, 180], [430, 260]], [[430, 260], [520, 340]]]
    return (
        json.dumps({"evidence": example_evidence, "answer": 12}, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
        json.dumps({"answer": 12}, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
    )


def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    """Resolve balanced support for one weighted MST query."""

    variant_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.query_id")
    query_id, query_id_probabilities = resolve_graph_named_variant(
        variant_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        supported=SUPPORTED_OPTIMIZATION_QUERY_IDS,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace="query_id",
    )
    node_count_min = int(params.get("node_count_min", group_default(_GEN_DEFAULTS, "node_count_min", _DEFAULTS.node_count_min)))
    node_count_max = int(params.get("node_count_max", group_default(_GEN_DEFAULTS, "node_count_max", _DEFAULTS.node_count_max)))
    extra_edge_count_min = int(
        params.get("extra_edge_count_min", group_default(_GEN_DEFAULTS, "extra_edge_count_min", _DEFAULTS.extra_edge_count_min))
    )
    extra_edge_count_max = int(
        params.get("extra_edge_count_max", group_default(_GEN_DEFAULTS, "extra_edge_count_max", _DEFAULTS.extra_edge_count_max))
    )
    edge_weight_min = int(params.get("edge_weight_min", group_default(_GEN_DEFAULTS, "edge_weight_min", _DEFAULTS.edge_weight_min)))
    edge_weight_max = int(params.get("edge_weight_max", group_default(_GEN_DEFAULTS, "edge_weight_max", _DEFAULTS.edge_weight_max)))

    node_support = tuple(range(int(node_count_min), int(node_count_max) + 1))
    if not node_support:
        raise ValueError("node_count support is empty for graph MST optimization")

    selection_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:query_support",
        )
    )
    explicit_node_count = params.get("node_count")
    if explicit_node_count is not None:
        node_count = int(explicit_node_count)
        if int(node_count) not in node_support:
            raise ValueError("requested node_count is outside configured support for graph MST optimization")
    else:
        node_count = int(node_support[int(selection_index % len(node_support))])

    extra_edge_support = feasible_extra_edge_counts_for_minimum_spanning_tree(
        node_count=int(node_count),
        extra_edge_count_min=int(extra_edge_count_min),
        extra_edge_count_max=int(extra_edge_count_max),
        edge_weight_min=int(edge_weight_min),
        edge_weight_max=int(edge_weight_max),
    )
    if not extra_edge_support:
        raise ValueError("no feasible extra-edge support exists for graph MST optimization")
    explicit_extra_edge_count = params.get("extra_edge_count")
    if explicit_extra_edge_count is not None:
        extra_edge_count = int(explicit_extra_edge_count)
        if int(extra_edge_count) not in extra_edge_support:
            raise ValueError("requested extra_edge_count is infeasible for graph MST optimization")
    else:
        extra_edge_count = int(extra_edge_support[(int(selection_index) // max(1, len(node_support))) % len(extra_edge_support)])

    topology_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.topology_profile")
    topology_profile, topology_profile_probabilities = resolve_graph_named_variant(
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
    layout_variant, layout_variant_probabilities = resolve_graph_named_variant(
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
        query_id=str(query_id),
        node_count=int(node_count),
        extra_edge_count=int(extra_edge_count),
        edge_weight_min=int(edge_weight_min),
        edge_weight_max=int(edge_weight_max),
        topology_profile=str(topology_profile),
        layout_variant=str(layout_variant),
        label_variant=str(label_variant),
        node_shape_variant=str(node_shape_variant),
        layout_transform_variant=str(layout_transform_variant),
        node_color_name=str(node_color_name),
        query_id_probabilities=dict(query_id_probabilities),
        node_count_probabilities=dict(
            uniform_probability_map(
                tuple(int(value) for value in node_support),
                selected=int(node_count) if explicit_node_count is not None else None,
            )
        ),
        extra_edge_count_probabilities=dict(
            uniform_probability_map(
                tuple(int(value) for value in extra_edge_support),
                selected=int(extra_edge_count) if explicit_extra_edge_count is not None else None,
            )
        ),
        topology_profile_probabilities=dict(topology_profile_probabilities),
        layout_variant_probabilities=dict(layout_variant_probabilities),
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
    crossing_norm = normalize_float_with_bounds(
        float(rendered_scene.crossing_count),
        (0.0, min(10.0, max(1.0, float(max_edges)))),
    )
    edge_count_norm = normalize_int_with_bounds(int(edge_count), (4, int(query.edge_weight_max)))
    extra_edge_norm = normalize_int_with_bounds(
        int(query.extra_edge_count),
        (int(_DEFAULTS.extra_edge_count_min), int(_DEFAULTS.extra_edge_count_max)),
    )
    node_count_norm = normalize_int_with_bounds(int(node_count), (_DEFAULTS.node_count_min, _DEFAULTS.node_count_max))
    node_radius_norm = normalize_int_with_bounds(
        int(render_params.node_radius_px),
        (_DEFAULTS.node_radius_min_px, _DEFAULTS.node_radius_max_px),
    )

    target_edge_set = {tuple(edge) for edge in graph_sample.target_edges}
    tree_weights = [int(weight) for edge, weight in graph_sample.edge_weights_by_label.items() if tuple(edge) in target_edge_set]
    non_tree_weights = [int(weight) for edge, weight in graph_sample.edge_weights_by_label.items() if tuple(edge) not in target_edge_set]
    max_tree_weight = max(tree_weights) if tree_weights else int(query.edge_weight_min)
    min_non_tree_gap = min((int(weight) - int(max_tree_weight)) for weight in non_tree_weights) if non_tree_weights else int(query.edge_weight_max)
    weight_span = max(graph_sample.edge_weights_by_label.values()) - min(graph_sample.edge_weights_by_label.values())
    ambiguity = 1.0 - normalize_int_with_bounds(
        int(min_non_tree_gap),
        (1, max(1, int(query.edge_weight_max) - int(query.edge_weight_min))),
    )

    mst_edge_norm = normalize_int_with_bounds(max(0, int(node_count) - 1), (4, _DEFAULTS.node_count_max - 1))
    components = {
        "visual_scan": (0.45 * float(node_count_norm)) + (0.45 * float(edge_count_norm)) + (0.10 * float(mst_edge_norm)),
        "topology_reasoning": (0.45 * float(edge_count_norm))
        + (0.30 * float(node_count_norm))
        + (0.25 * normalize_int_with_bounds(int(weight_span), (0, int(query.edge_weight_max) - int(query.edge_weight_min)))),
        "ambiguity": (0.70 * float(ambiguity)) + (0.30 * float(extra_edge_norm)),
        "clutter": float(crossing_norm),
    }
    return build_graph_complexity(weights=_COMPLEXITY_WEIGHTS, components=components)


@register_task
class GraphOptimizationMinimumSpanningTreeWeightTask:
    """Return the total weight of the unique minimum spanning tree."""

    task_id = TASK_ID
    domain = "graph"
    task_group = "optimization"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic weighted-graph MST instance."""

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
        edge_weight_label_font_size_px = int(
            params.get(
                "edge_weight_label_font_size_px",
                group_default(_RENDER_DEFAULTS, "edge_weight_label_font_size_px", _DEFAULTS.edge_weight_label_font_size_px),
            )
        )
        edge_weight_label_offset_px = int(
            params.get(
                "edge_weight_label_offset_px",
                group_default(_RENDER_DEFAULTS, "edge_weight_label_offset_px", _DEFAULTS.edge_weight_label_offset_px),
            )
        )
        edge_weight_label_padding_px = int(
            params.get(
                "edge_weight_label_padding_px",
                group_default(_RENDER_DEFAULTS, "edge_weight_label_padding_px", _DEFAULTS.edge_weight_label_padding_px),
            )
        )

        graph_rng = spawn_rng(int(instance_seed), "graph_structure")
        last_error: Exception | None = None
        graph_sample = None
        rendered_scene = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                graph_sample = sample_minimum_spanning_tree_weight_graph(
                    graph_rng,
                    node_count=int(query.node_count),
                    extra_edge_count=int(query.extra_edge_count),
                    topology_profile=str(query.topology_profile),
                    label_variant=str(query.label_variant),
                    edge_weight_min=int(query.edge_weight_min),
                    edge_weight_max=int(query.edge_weight_max),
                )
                background, background_meta = make_background_canvas(
                    canvas_width=int(render_params.canvas_width),
                    canvas_height=int(render_params.canvas_height),
                    instance_seed=int(instance_seed),
                    params=params,
                    default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
                )
                rendered_scene = render_graph_scene(
                    graph_sample=graph_sample,
                    layout_variant=str(query.layout_variant),
                    layout_transform_variant=str(query.layout_transform_variant),
                    render_params=render_params,
                    layout_seed=int(instance_seed + attempt),
                    scene_title="Weighted Graph",
                    directed=False,
                    base_image=background,
                    edge_weights_by_label=dict(graph_sample.edge_weights_by_label),
                    edge_weight_label_font_size_px=int(edge_weight_label_font_size_px),
                    edge_weight_label_offset_px=int(edge_weight_label_offset_px),
                    edge_weight_label_padding_px=int(edge_weight_label_padding_px),
                )
                image, post_noise_meta = apply_post_image_noise(
                    rendered_scene.image,
                    instance_seed=int(instance_seed),
                    params=params,
                    default_config=POST_IMAGE_NOISE_DEFAULTS,
                )
                break
            except Exception as exc:  # pragma: no cover - exercised through retry loop
                last_error = exc
                continue
        else:
            raise RuntimeError("failed to generate task_graph__node_link__mst_weight instance") from last_error

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description_undirected",
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
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key="minimum_spanning_tree_weight",
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_undirected"]),
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

        evidence_edges = tuple((str(left), str(right)) for left, right in graph_sample.target_edges)
        evidence_edge_set = {tuple(edge) for edge in evidence_edges}
        answer_gt = TypedValue(type="integer", value=int(graph_sample.target_total_weight))
        evidence_projection = projected_edge_pair_evidence(rendered_scene, evidence_edges)
        evidence_point_pairs = [[list(point) for point in pair] for pair in evidence_projection["point_pair_set"]]
        evidence_gt = TypedValue(type="point_pair_set", value=list(evidence_point_pairs))

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
                "weight": int(edge.weight) if edge.weight is not None else None,
                "weight_label_bbox_xyxy": list(edge.weight_label_bbox_xyxy) if edge.weight_label_bbox_xyxy is not None else None,
                "is_in_minimum_spanning_tree": bool(
                    canonicalize_graph_edge_label(str(edge.node_u_label), str(edge.node_v_label), directed=False)
                    in evidence_edge_set
                ),
            }
            for edge in rendered_scene.edges
        ]
        edge_weights_trace = [
            {"endpoints": [str(left), str(right)], "weight": int(weight)}
            for (left, right), weight in sorted(
                graph_sample.edge_weights_by_label.items(),
                key=lambda item: (
                    int(item[0][0]) if str(item[0][0]).isdigit() else str(item[0][0]),
                    int(item[0][1]) if str(item[0][1]).isdigit() else str(item[0][1]),
                ),
            )
        ]
        complexity = _build_complexity(
            graph_sample=graph_sample,
            query=query,
            render_params=render_params,
            rendered_scene=rendered_scene,
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "graph_minimum_spanning_tree_weight",
                "entities": [*node_entities, *edge_entities],
                "relations": {
                    "question_rule": "sum_minimum_spanning_tree_weights",
                    "graph_directionality": "undirected",
                    "edge_weights_by_label": list(edge_weights_trace),
                    "minimum_spanning_tree_edges": [list(edge) for edge in evidence_edges],
                    "adjacency_by_label": {str(key): list(values) for key, values in graph_sample.adjacency_by_label.items()},
                    "degrees_by_label": {str(key): int(value) for key, value in graph_sample.degrees_by_label.items()},
                    "edge_labels": [list(edge) for edge in graph_sample.edge_labels],
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(rendered_scene.panel_geometry),
                },
            },
            "query_spec": {
                "query_id": str(query.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "graph_directionality": "undirected",
                    "query_id_probabilities": dict(query.query_id_probabilities),
                    "node_count": int(query.node_count),
                    "edge_count": int(graph_sample.edge_count),
                    "extra_edge_count": int(query.extra_edge_count),
                    "edge_weight_min": int(query.edge_weight_min),
                    "edge_weight_max": int(query.edge_weight_max),
                    "node_count_probabilities": dict(query.node_count_probabilities),
                    "extra_edge_count_probabilities": dict(query.extra_edge_count_probabilities),
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
                    "node_border_width_px": int(render_params.node_border_width_px),
                    "label_font_size_px": int(render_params.label_font_size_px),
                    "resolved_label_font_size_px": int(rendered_scene.resolved_label_font_size_px),
                    "label_stroke_width_px": int(rendered_scene.resolved_label_stroke_width_px),
                    "edge_weight_label_font_size_px": int(edge_weight_label_font_size_px),
                    "edge_weight_label_offset_px": int(edge_weight_label_offset_px),
                    "edge_weight_label_padding_px": int(edge_weight_label_padding_px),
                    "background_meta": dict(background_meta),
                    "post_image_noise_meta": dict(post_noise_meta),
                },
            },
            "render_map": {"image_id": "img0", "anchors": {}},
            "execution_trace": {
                "query_id": str(query.query_id),
                "scene_variant": str(rendered_scene.layout_variant),
                "question_format": "sum_unique_mst_weights",
                "graph_directionality": "undirected",
                "node_count": int(query.node_count),
                "edge_count": int(graph_sample.edge_count),
                "extra_edge_count": int(query.extra_edge_count),
                "edge_weight_min": int(query.edge_weight_min),
                "edge_weight_max": int(query.edge_weight_max),
                "minimum_spanning_tree_total_weight": int(graph_sample.target_total_weight),
                "minimum_spanning_tree_edges": [list(edge) for edge in evidence_edges],
                "edge_weights_by_label": list(edge_weights_trace),
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
            },
            "witness_symbolic": {
                "type": "edge_pair_set",
                "edges": [list(edge) for edge in evidence_edges],
            },
            "projected_evidence": {
                "type": "point_pair_set",
                **dict(evidence_projection),
            },
        }

        return rewrite_graph_query_output(
            TaskOutput(
                prompt=str(prompt_artifacts.prompt),
                answer_gt=answer_gt,
                evidence_gt=evidence_gt,
                image=image,
                image_id="img0",
                trace_payload=trace_payload,
                complexity=complexity,
                task_versions=default_task_versions(),
                prompt_variants=dict(prompt_artifacts.prompt_variants),
            ),
            query_id="minimum_spanning_tree_weight",
        )


__all__ = ["GraphOptimizationMinimumSpanningTreeWeightTask"]
