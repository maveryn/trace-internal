"""Count graph edges with a specified visible text label."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import hash64, spawn_rng
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
    SUPPORTED_EDGE_ATTRIBUTE_LABEL_DIRECTIONS,
    SUPPORTED_LAYOUT_VARIANTS,
    SUPPORTED_NODE_LINK_LABEL_VARIANTS,
    SUPPORTED_TOPOLOGY_PROFILES,
    sample_edge_text_label_count_graph,
)
from ..shared.graph_scene import (
    GraphRenderParams,
    SUPPORTED_EDGE_ROUTING_VARIANTS,
    SUPPORTED_LAYOUT_TRANSFORM_VARIANTS,
    SUPPORTED_NODE_SHAPE_VARIANTS,
    projected_edge_label_bbox_evidence,
    render_graph_scene,
)
from ..shared.style import SUPPORTED_NODE_COLOR_NAMES
from ..shared.task_support import (
    graph_edge_label_entries,
    graph_uniform_label_probability_map,
    resolve_graph_balanced_node_color_name,
    resolve_graph_edge_label_support_from_params,
    resolve_graph_named_variant,
    resolve_graph_render_params,
)
from ..shared.visual_defaults import load_graph_background_defaults, load_graph_noise_defaults


TASK_ID = "task_graph__node_link__edge_text_count"
SCENE_ID = "node_link"
QUERY_ID = "edge_text_label_count"


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for graph edge-text-label count scenes."""

    node_count_min: int = 5
    node_count_max: int = 9
    directed_node_count_max: int = 9
    target_count_min: int = 1
    target_count_max: int = 5
    degree_sequence_max_degree: int = 4
    directed_degree_sequence_max_degree: int = 4
    edge_label_support_size: int = 6
    edge_label_min_chars: int = 3
    edge_label_max_chars: int = 10
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
    node_color_name: str = "blue"


@dataclass(frozen=True)
class _ResolvedQuery:
    """Resolved support and visual axes for one edge-text-label count query."""

    graph_directionality: str
    node_count: int
    target_count: int
    target_edge_label: str
    edge_label_support: Tuple[str, ...]
    edge_label_source_kind: str
    edge_label_bucket: str
    edge_label_manifest: str
    edge_label_filter: Mapping[str, Any]
    edge_label_bucket_probabilities: Dict[str, float]
    node_color_name: str
    topology_profile: str
    layout_variant: str
    label_variant: str
    node_shape_variant: str
    layout_transform_variant: str
    edge_routing_variant: str
    graph_directionality_probabilities: Dict[str, float]
    node_count_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    target_edge_label_probabilities: Dict[str, float]
    node_color_name_probabilities: Dict[str, float]
    topology_profile_probabilities: Dict[str, float]
    layout_variant_probabilities: Dict[str, float]
    label_variant_probabilities: Dict[str, float]
    node_shape_variant_probabilities: Dict[str, float]
    layout_transform_variant_probabilities: Dict[str, float]
    edge_routing_variant_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("graph", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_graph_background_defaults(task_group="counting")
POST_IMAGE_NOISE_DEFAULTS = load_graph_noise_defaults(task_group="counting", apply_prob=0.0)
_COMPLEXITY_WEIGHTS = resolve_graph_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)


def _build_prompt_json_examples() -> Tuple[str, str]:
    """Return prompt examples that match edge-label bbox evidence."""

    example_evidence = [[240, 190, 308, 214], [412, 238, 480, 262]]
    return (
        json.dumps({"evidence": example_evidence, "answer": 2}, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
        json.dumps({"answer": 2}, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
    )



def _node_count_selection_index(
    instance_seed: int,
    *,
    selection_index: int,
    graph_directionality: str,
    target_count: int,
    target_edge_label: str,
    topology_profile: str,
) -> int:
    """Return an independent node-count index for one edge-text-label query."""

    namespace = (
        f"{TASK_ID}:node_count:"
        f"{str(graph_directionality)}:{int(target_count)}:{str(target_edge_label)}:{str(topology_profile)}"
    )
    return int(hash64(int(instance_seed), namespace, int(selection_index)))



def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    """Resolve one visible edge-text-label counting query."""

    direction_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.graph_directionality")
    graph_directionality, graph_directionality_probabilities = resolve_graph_named_variant(
        direction_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key="graph_directionality",
        weights_key="graph_directionality_weights",
        balance_flag_key="balanced_graph_directionality_sampling",
        supported=SUPPORTED_EDGE_ATTRIBUTE_LABEL_DIRECTIONS,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace="graph_directionality",
    )
    edge_label_support, edge_label_metadata = resolve_graph_edge_label_support_from_params(
        int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        task_id=TASK_ID,
        default_support_size=_DEFAULTS.edge_label_support_size,
        default_min_chars=_DEFAULTS.edge_label_min_chars,
        default_max_chars=_DEFAULTS.edge_label_max_chars,
    )

    target_label_selection_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:target_edge_label",
        )
    )
    explicit_target_label = params.get("target_edge_label")
    if explicit_target_label is not None:
        target_edge_label = str(explicit_target_label).strip().lower()
        if str(target_edge_label) not in set(edge_label_support):
            raise ValueError("target_edge_label is outside edge_label_support")
    else:
        if bool(params.get("balanced_target_edge_label_sampling", group_default(_GEN_DEFAULTS, "balanced_target_edge_label_sampling", True))):
            target_edge_label = str(edge_label_support[int(target_label_selection_index % len(edge_label_support))])
        else:
            label_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.target_edge_label")
            target_edge_label = str(edge_label_support[int(label_rng.randrange(len(edge_label_support)))])

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

    node_count_min = int(params.get("node_count_min", group_default(_GEN_DEFAULTS, "node_count_min", _DEFAULTS.node_count_min)))
    node_count_max_key = "directed_node_count_max" if str(graph_directionality) == "directed" else "node_count_max"
    node_count_max_fallback = _DEFAULTS.directed_node_count_max if str(graph_directionality) == "directed" else _DEFAULTS.node_count_max
    node_count_max = int(params.get(node_count_max_key, group_default(_GEN_DEFAULTS, node_count_max_key, node_count_max_fallback)))
    target_count_min = int(params.get("target_count_min", group_default(_GEN_DEFAULTS, "target_count_min", _DEFAULTS.target_count_min)))
    target_count_max = int(params.get("target_count_max", group_default(_GEN_DEFAULTS, "target_count_max", _DEFAULTS.target_count_max)))

    max_target_by_node_support = max(0, int(node_count_max) - 1)
    feasible_targets = tuple(
        int(value)
        for value in range(int(target_count_min), int(target_count_max) + 1)
        if 0 <= int(value) <= int(max_target_by_node_support)
    )
    if not feasible_targets:
        raise ValueError("no feasible target_count support exists for edge-text-label count")
    target_count_selection_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:target_count",
        )
    )
    explicit_target_count = params.get("target_count")
    if explicit_target_count is not None:
        target_count = int(explicit_target_count)
        if int(target_count) not in set(feasible_targets):
            raise ValueError("target_count is outside feasible support for edge-text-label count")
    else:
        target_count = int(feasible_targets[int(target_count_selection_index % len(feasible_targets))])

    min_nodes_for_edges = int(target_count) + 1 if int(target_count) > 0 else int(node_count_min)
    feasible_node_support = tuple(
        int(value)
        for value in range(max(int(node_count_min), int(min_nodes_for_edges)), int(node_count_max) + 1)
    )
    if not feasible_node_support:
        raise ValueError("no feasible node_count support exists for edge-text-label count")
    explicit_node_count = params.get("node_count")
    if explicit_node_count is not None:
        node_count = int(explicit_node_count)
        if int(node_count) not in set(feasible_node_support):
            raise ValueError("node_count is outside feasible support for edge-text-label count")
    else:
        node_index = _node_count_selection_index(
            int(instance_seed),
            selection_index=int(target_count_selection_index),
            graph_directionality=str(graph_directionality),
            target_count=int(target_count),
            target_edge_label=str(target_edge_label),
            topology_profile=str(topology_profile),
        )
        node_count = int(feasible_node_support[int(node_index % len(feasible_node_support))])

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
        supported=SUPPORTED_NODE_LINK_LABEL_VARIANTS,
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
    edge_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.edge_routing_variant")
    edge_routing_variant, edge_routing_variant_probabilities = resolve_graph_named_variant(
        edge_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key="edge_routing_variant",
        weights_key="edge_routing_variant_weights",
        balance_flag_key="balanced_edge_routing_variant_sampling",
        supported=SUPPORTED_EDGE_ROUTING_VARIANTS,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace="edge_routing_variant",
    )
    node_color_name, node_color_name_probabilities = resolve_graph_balanced_node_color_name(
        int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        task_id=TASK_ID,
        supported=SUPPORTED_NODE_COLOR_NAMES,
    )

    return _ResolvedQuery(
        graph_directionality=str(graph_directionality),
        node_count=int(node_count),
        target_count=int(target_count),
        target_edge_label=str(target_edge_label),
        edge_label_support=tuple(str(label) for label in edge_label_support),
        edge_label_source_kind=str(edge_label_metadata["edge_label_source_kind"]),
        edge_label_bucket=str(edge_label_metadata["edge_label_bucket"]),
        edge_label_manifest=str(edge_label_metadata["edge_label_manifest"]),
        edge_label_filter=dict(edge_label_metadata["edge_label_filter"]),
        edge_label_bucket_probabilities=dict(edge_label_metadata["edge_label_bucket_probabilities"]),
        node_color_name=str(node_color_name),
        topology_profile=str(topology_profile),
        layout_variant=str(layout_variant),
        label_variant=str(label_variant),
        node_shape_variant=str(node_shape_variant),
        layout_transform_variant=str(layout_transform_variant),
        edge_routing_variant=str(edge_routing_variant),
        graph_directionality_probabilities=dict(graph_directionality_probabilities),
        node_count_probabilities=dict(
            uniform_probability_map(
                tuple(int(value) for value in feasible_node_support),
                selected=int(node_count) if explicit_node_count is not None else None,
            )
        ),
        target_count_probabilities=dict(
            uniform_probability_map(
                tuple(int(value) for value in feasible_targets),
                selected=int(target_count) if explicit_target_count is not None else None,
            )
        ),
        target_edge_label_probabilities=dict(
            graph_uniform_label_probability_map(
                edge_label_support,
                selected=str(target_edge_label) if explicit_target_label is not None else None,
            )
        ),
        node_color_name_probabilities=dict(node_color_name_probabilities),
        topology_profile_probabilities=dict(topology_probabilities),
        layout_variant_probabilities=dict(layout_probabilities),
        label_variant_probabilities=dict(label_variant_probabilities),
        node_shape_variant_probabilities=dict(node_shape_variant_probabilities),
        layout_transform_variant_probabilities=dict(layout_transform_variant_probabilities),
        edge_routing_variant_probabilities=dict(edge_routing_variant_probabilities),
    )



def _project_edge_label_bboxes(rendered_scene: Any, edges: Sequence[Tuple[str, str]]) -> Dict[str, Any]:
    """Project multiple rendered edge-label boxes into one evidence payload."""

    bbox_set = []
    pixel_bbox_set = []
    for edge in edges:
        projection = projected_edge_label_bbox_evidence(rendered_scene, edge)
        bboxes = projection.get("bbox_set", [])
        if not bboxes:
            raise ValueError("target edge label bbox was not rendered")
        bbox = [float(value) for value in bboxes[0]]
        bbox_set.append(list(bbox))
        pixel_bbox_set.append(list(bbox))
    return {"bbox_set": bbox_set, "pixel_bbox_set": pixel_bbox_set}


def _build_complexity(
    *,
    graph_sample: Any,
    query: _ResolvedQuery,
    render_params: GraphRenderParams,
    rendered_scene: Any,
) -> Any:
    """Build one within-task normalized complexity record."""

    node_count = int(query.node_count)
    edge_count = int(graph_sample.edge_count)
    max_edges = int(node_count * (node_count - 1))
    if str(query.graph_directionality) == "undirected":
        max_edges = int(max_edges // 2)
    edge_density = 0.0 if int(max_edges) <= 0 else float(edge_count) / float(max_edges)
    crossing_norm = normalize_float_with_bounds(float(rendered_scene.crossing_count), (0.0, max(1.0, float(edge_count))))
    target_density = 0.0 if int(edge_count) <= 0 else float(query.target_count) / float(edge_count)
    density_ambiguity = 1.0 - min(1.0, abs(float(target_density) - 0.5) * 2.0)
    directionality_bonus = 1.0 if str(query.graph_directionality) == "directed" else 0.0
    observed_label_count = sum(1 for value in graph_sample.edge_label_counts_by_value.values() if int(value) > 0)

    components = {
        "visual_scan": (0.40 * normalize_int_with_bounds(int(edge_count), (max(1, _DEFAULTS.node_count_min - 1), max(1, max_edges))))
        + (0.30 * normalize_int_with_bounds(int(observed_label_count), (2, max(2, len(query.edge_label_support)))))
        + (0.20 * normalize_int_with_bounds(int(query.target_count), (_DEFAULTS.target_count_min, _DEFAULTS.target_count_max)))
        + (0.10 * float(directionality_bonus)),
        "topology_reasoning": (0.55 * normalize_float_with_bounds(float(edge_density), (0.0, 1.0)))
        + (0.25 * normalize_int_with_bounds(int(node_count), (_DEFAULTS.node_count_min, _DEFAULTS.directed_node_count_max)))
        + (0.20 * float(directionality_bonus)),
        "ambiguity": (0.70 * float(density_ambiguity))
        + (0.30 * normalize_int_with_bounds(int(observed_label_count), (2, max(2, len(query.edge_label_support))))),
        "clutter": (0.45 * normalize_float_with_bounds(float(edge_density), (0.0, 1.0)))
        + (0.35 * crossing_norm)
        + (0.20 * normalize_int_with_bounds(int(render_params.node_radius_px), (_DEFAULTS.node_radius_min_px, _DEFAULTS.node_radius_max_px))),
    }
    return build_graph_complexity(weights=_COMPLEXITY_WEIGHTS, components=components)


@register_task
class GraphCountingEdgeTextLabelCountTask:
    """Count edges whose visible text label matches the queried label."""

    task_id = TASK_ID
    domain = "graph"
    task_group = "counting"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic edge-text-label count instance."""

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
        max_degree_key = "directed_degree_sequence_max_degree" if str(query.graph_directionality) == "directed" else "degree_sequence_max_degree"
        max_degree_fallback = (
            _DEFAULTS.directed_degree_sequence_max_degree if str(query.graph_directionality) == "directed" else _DEFAULTS.degree_sequence_max_degree
        )
        max_degree = int(params.get(max_degree_key, group_default(_GEN_DEFAULTS, max_degree_key, max_degree_fallback)))

        graph_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.graph")
        last_error: Exception | None = None
        graph_sample = None
        rendered_scene = None
        image = None
        background_meta = {}
        post_noise_meta = {}
        evidence_projection = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                graph_sample = sample_edge_text_label_count_graph(
                    graph_rng,
                    graph_directionality=str(query.graph_directionality),
                    node_count=int(query.node_count),
                    target_count=int(query.target_count),
                    target_edge_label=str(query.target_edge_label),
                    edge_label_support=tuple(str(label) for label in query.edge_label_support),
                    topology_profile=str(query.topology_profile),
                    label_variant=str(query.label_variant),
                    max_degree=int(max_degree),
                )
                background, background_meta = make_background_canvas(
                    canvas_width=int(render_params.canvas_width),
                    canvas_height=int(render_params.canvas_height),
                    instance_seed=int(instance_seed),
                    params=params,
                    default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
                )
                directed = str(query.graph_directionality) == "directed"
                rendered_scene = render_graph_scene(
                    graph_sample=graph_sample,
                    layout_variant=str(query.layout_variant),
                    layout_transform_variant=str(query.layout_transform_variant),
                    render_params=render_params,
                    layout_seed=int(instance_seed + attempt),
                    scene_title="Directed Graph" if bool(directed) else "Graph",
                    directed=bool(directed),
                    base_image=background,
                    edge_text_labels_by_label=graph_sample.edge_attribute_labels_by_label,
                    edge_text_label_font_size_px=max(13, int(render_params.label_font_size_px) - 4),
                )
                evidence_projection = _project_edge_label_bboxes(rendered_scene, graph_sample.target_edges)
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
            raise RuntimeError("failed to generate graph edge-text-label count instance") from last_error
        if graph_sample is None or rendered_scene is None or image is None or evidence_projection is None:
            raise RuntimeError("failed to generate graph edge-text-label count instance")

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description_undirected",
                "object_description_directed",
                "evidence_hint",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_json_example, prompt_json_example_answer_only = _build_prompt_json_examples()
        object_description_key = "object_description_directed" if str(query.graph_directionality) == "directed" else "object_description_undirected"
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=QUERY_ID,
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults[object_description_key]),
                "target_edge_label": str(query.target_edge_label),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]).format(target_edge_label=str(query.target_edge_label)),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_json_example),
                "json_example_answer_only": str(prompt_json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        evidence_edges = tuple((str(left), str(right)) for left, right in graph_sample.target_edges)
        evidence_bboxes = [[int(round(float(value))) for value in bbox] for bbox in evidence_projection["bbox_set"]]
        answer_gt = TypedValue(type="integer", value=int(len(evidence_edges)))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))
        target_edge_set = {tuple(edge) for edge in evidence_edges}
        edge_label_entries = graph_edge_label_entries(graph_sample.edge_attribute_labels_by_label)
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
                "edge_attribute_label": str(graph_sample.edge_attribute_labels_by_label[(str(edge.node_u_label), str(edge.node_v_label))]),
                "edge_label_bbox_xyxy": list(edge.edge_label_bbox_xyxy) if edge.edge_label_bbox_xyxy is not None else None,
                "is_target_edge_label": bool((str(edge.node_u_label), str(edge.node_v_label)) in target_edge_set),
                "segment_px": [list(edge.segment_px[0]), list(edge.segment_px[1])],
                "route_variant": str(edge.route_variant),
                "control_px": list(edge.control_px) if edge.control_px is not None else None,
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
                "scene_kind": "graph_edge_text_label_counting",
                "entities": [*node_entities, *edge_entities],
                "relations": {
                    "query_id": QUERY_ID,
                    "counting_rule": "edges_whose_visible_text_label_matches_target_label",
                    "graph_directionality": str(query.graph_directionality),
                    "target_edge_label": str(query.target_edge_label),
                    "matching_edges": [list(edge) for edge in evidence_edges],
                    "edge_label_support": list(query.edge_label_support),
                    "edge_label_source_kind": str(query.edge_label_source_kind),
                    "edge_label_bucket": str(query.edge_label_bucket),
                    "edge_label_manifest": str(query.edge_label_manifest),
                    "edge_label_filter": dict(query.edge_label_filter),
                    "edge_label_bucket_probabilities": dict(query.edge_label_bucket_probabilities),
                    "edge_attribute_labels_by_label_pair": list(edge_label_entries),
                    "edge_label_counts_by_value": dict(graph_sample.edge_label_counts_by_value),
                    "target_edge_label_probabilities": dict(query.target_edge_label_probabilities),
                    "graph_directionality_probabilities": dict(query.graph_directionality_probabilities),
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
                    "graph_directionality": str(query.graph_directionality),
                    "graph_directionality_probabilities": dict(query.graph_directionality_probabilities),
                    "node_count": int(query.node_count),
                    "edge_count": int(graph_sample.edge_count),
                    "target_count": int(query.target_count),
                    "target_edge_label": str(query.target_edge_label),
                    "target_edge_label_probabilities": dict(query.target_edge_label_probabilities),
                    "edge_label_support": list(query.edge_label_support),
                    "edge_label_source_kind": str(query.edge_label_source_kind),
                    "edge_label_bucket": str(query.edge_label_bucket),
                    "edge_label_manifest": str(query.edge_label_manifest),
                    "edge_label_filter": dict(query.edge_label_filter),
                    "edge_label_bucket_probabilities": dict(query.edge_label_bucket_probabilities),
                    "node_count_probabilities": dict(query.node_count_probabilities),
                    "target_count_probabilities": dict(query.target_count_probabilities),
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
                    max_degree_key: int(max_degree),
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
                    "semantic_edge_text_labels_by_label_pair": list(edge_label_entries),
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
            "render_map": {
                "image_id": "img0",
                "anchors": {},
            },
            "execution_trace": {
                "query_id": QUERY_ID,
                "internal_query_id": QUERY_ID,
                "query_id_probabilities": {QUERY_ID: 1.0},
                "scene_variant": str(rendered_scene.layout_variant),
                "question_format": QUERY_ID,
                "graph_directionality": str(query.graph_directionality),
                "node_count": int(query.node_count),
                "edge_count": int(graph_sample.edge_count),
                "target_count": int(query.target_count),
                "answer": int(len(evidence_edges)),
                "target_edge_label": str(query.target_edge_label),
                "target_edge_label_probabilities": dict(query.target_edge_label_probabilities),
                "matching_edges": [list(edge) for edge in evidence_edges],
                "edge_label_support": list(query.edge_label_support),
                "edge_label_source_kind": str(query.edge_label_source_kind),
                "edge_label_bucket": str(query.edge_label_bucket),
                "edge_label_manifest": str(query.edge_label_manifest),
                "edge_label_filter": dict(query.edge_label_filter),
                "edge_label_bucket_probabilities": dict(query.edge_label_bucket_probabilities),
                "edge_attribute_labels_by_label_pair": list(edge_label_entries),
                "edge_label_counts_by_value": dict(graph_sample.edge_label_counts_by_value),
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
                "type": "edge_set",
                "edges": [list(edge) for edge in evidence_edges],
                "target_edge_label": str(query.target_edge_label),
            },
            "projected_evidence": {
                "type": "bbox_set",
                "bbox_set": list(evidence_bboxes),
                "pixel_bbox_set": list(evidence_bboxes),
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
            scene_id=SCENE_ID,
            query_id=QUERY_ID,
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["GraphCountingEdgeTextLabelCountTask"]
