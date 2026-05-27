"""Count post-edit directed reachability after one hypothetical arrow edit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

from ....core.seed import hash64, spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.graph_algorithms import bfs_dist_count_by_adjacency
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.prompt_examples import build_graph_prompt_json_examples
from ..shared.complexity import (
    build_graph_complexity,
    normalize_float_with_bounds,
    normalize_int_with_bounds,
    resolve_graph_complexity_weights,
)
from ..shared.graph_sampling import (
    SUPPORTED_LAYOUT_VARIANTS,
    SUPPORTED_NODE_LINK_LABEL_VARIANTS,
    SUPPORTED_REACHABLE_EDGE_EDIT_MODES,
    SUPPORTED_TOPOLOGY_PROFILES,
    feasible_node_counts_for_reachable_count_after_edge_edit,
    graph_label_sort_key,
    sample_reachable_count_after_edge_edit_graph,
)
from ..shared.graph_scene import (
    GraphRenderParams,
    SUPPORTED_EDGE_ROUTING_VARIANTS,
    SUPPORTED_LAYOUT_TRANSFORM_VARIANTS,
    SUPPORTED_NODE_SHAPE_VARIANTS,
    projected_node_point_evidence,
    render_graph_scene,
)
from ..shared.style import SUPPORTED_NODE_COLOR_NAMES
from ..shared.task_support import (
    format_graph_prompt_label,
    graph_query_probabilities_from_alias_map,
    resolve_forced_graph_edit_operation,
    resolve_graph_named_variant,
    resolve_graph_render_params,
)
from ..shared.visual_defaults import load_graph_background_defaults, load_graph_noise_defaults


TASK_ID = "graph_node_link_reachable_count_after_edge_edit_internal"
SCENE_ID = "node_link"

QUERY_ID_BY_OPERATION = {
    "edge_removal": "reachable_count_after_edge_removal",
    "edge_addition": "reachable_count_after_edge_addition",
}
PROMPT_QUERY_KEY_BY_OPERATION = {
    "edge_removal": "reachable_count_after_edge_removal",
    "edge_addition": "reachable_count_after_edge_addition",
}
RELATION_RULE_BY_OPERATION = {
    "edge_removal": "post_removal_reachable_from_query_node_following_arrows_including_query",
    "edge_addition": "post_addition_reachable_from_query_node_following_arrows_including_query",
}


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for reachable-count-after-edge-edit scenes."""

    node_count_min: int = 5
    directed_node_count_max: int = 10
    target_reachable_count_min: int = 1
    target_reachable_count_max: int = 8
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
    """Resolved support and style axes for one edge-edit reachability query."""

    edit_operation: str
    query_id: str
    prompt_query_key: str
    node_count: int
    target_reachable_count: int
    topology_profile: str
    layout_variant: str
    label_variant: str
    node_shape_variant: str
    layout_transform_variant: str
    edge_routing_variant: str
    node_color_name: str
    edit_operation_probabilities: Dict[str, float]
    query_id_probabilities: Dict[str, float]
    node_count_probabilities: Dict[str, float]
    target_reachable_count_probabilities: Dict[str, float]
    topology_profile_probabilities: Dict[str, float]
    layout_variant_probabilities: Dict[str, float]
    label_variant_probabilities: Dict[str, float]
    node_shape_variant_probabilities: Dict[str, float]
    layout_transform_variant_probabilities: Dict[str, float]
    edge_routing_variant_probabilities: Dict[str, float]
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


def _operation_from_query_alias(value: Any) -> str | None:
    """Return an edge-edit operation encoded by public query aliases."""

    text = str(value or "").strip()
    aliases = {
        "edge_removal": "edge_removal",
        "remove_edge": "edge_removal",
        "arrow_removal": "edge_removal",
        "remove_arrow": "edge_removal",
        "reachable_count_after_edge_removal": "edge_removal",
        "reachable_count_after_edge_removed": "edge_removal",
        "edge_addition": "edge_addition",
        "add_edge": "edge_addition",
        "arrow_addition": "edge_addition",
        "add_arrow": "edge_addition",
        "reachable_count_after_edge_addition": "edge_addition",
        "reachable_count_after_edge_added": "edge_addition",
    }
    return aliases.get(text)




def _node_count_selection_index(
    instance_seed: int,
    *,
    selection_index: int,
    edit_operation: str,
    target_reachable_count: int,
    topology_profile: str,
) -> int:
    """Return an independent node-count index for the resolved query support."""

    namespace = (
        f"{TASK_ID}:node_count:"
        f"{str(edit_operation)}:{int(target_reachable_count)}:{str(topology_profile)}"
    )
    return int(hash64(int(instance_seed), namespace, int(selection_index)))


def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    """Resolve one directed edge-edit reachable-count query."""

    explicit_directionality = params.get("graph_directionality")
    if explicit_directionality is not None and str(explicit_directionality).strip() != "directed":
        raise ValueError("reachable-count-after-edge-edit supports only directed graphs")

    forced_operation = resolve_forced_graph_edit_operation(params, operation_from_query_alias=_operation_from_query_alias)
    if forced_operation is None:
        operation_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.edit_operation")
        edit_operation, edit_operation_probabilities = resolve_graph_named_variant(
            operation_rng,
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            explicit_key="edit_operation",
            weights_key="edge_edit_operation_weights",
            balance_flag_key="balanced_edge_edit_operation_sampling",
            supported=SUPPORTED_REACHABLE_EDGE_EDIT_MODES,
            instance_seed=int(instance_seed),
            task_id=TASK_ID,
            namespace="edit_operation",
        )
    else:
        edit_operation = str(forced_operation)
        edit_operation_probabilities = {
            str(operation): (1.0 if str(operation) == str(edit_operation) else 0.0)
            for operation in SUPPORTED_REACHABLE_EDGE_EDIT_MODES
        }

    selection_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:query_support",
        )
    )
    operation_axis_size = 1 if forced_operation is not None else len(SUPPORTED_REACHABLE_EDGE_EDIT_MODES)
    target_selection_index = int(selection_index // max(1, int(operation_axis_size)))

    node_count_min = int(params.get("node_count_min", group_default(_GEN_DEFAULTS, "node_count_min", _DEFAULTS.node_count_min)))
    node_count_max = int(
        params.get(
            "directed_node_count_max",
            params.get(
                "node_count_max",
                group_default(_GEN_DEFAULTS, "directed_node_count_max", _DEFAULTS.directed_node_count_max),
            ),
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

    feasible_targets = []
    feasible_node_support_by_target: Dict[int, Tuple[int, ...]] = {}
    for target_count in range(int(target_count_min), int(target_count_max) + 1):
        feasible_nodes = feasible_node_counts_for_reachable_count_after_edge_edit(
            edit_operation=str(edit_operation),
            target_reachable_count=int(target_count),
            node_count_min=int(node_count_min),
            node_count_max=int(node_count_max),
        )
        if feasible_nodes:
            feasible_targets.append(int(target_count))
            feasible_node_support_by_target[int(target_count)] = tuple(int(value) for value in feasible_nodes)
    if not feasible_targets:
        raise ValueError("no feasible support exists for reachable-count-after-edge-edit")

    explicit_target_count = params.get("target_reachable_count")
    if explicit_target_count is not None:
        target_reachable_count = int(explicit_target_count)
        if int(target_reachable_count) not in feasible_targets:
            raise ValueError("target_reachable_count is outside feasible support for reachable-count-after-edge-edit")
    else:
        if bool(
            params.get(
                "balanced_target_reachable_count_sampling",
                group_default(_GEN_DEFAULTS, "balanced_target_reachable_count_sampling", True),
            )
        ):
            target_reachable_count = int(feasible_targets[int(target_selection_index % len(feasible_targets))])
        else:
            target_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.target_reachable_count")
            target_reachable_count = int(feasible_targets[int(target_rng.randrange(len(feasible_targets)))])

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

    feasible_node_support = feasible_node_support_by_target[int(target_reachable_count)]
    explicit_node_count = params.get("node_count")
    if explicit_node_count is not None:
        node_count = int(explicit_node_count)
    else:
        node_index = _node_count_selection_index(
            int(instance_seed),
            selection_index=int(selection_index),
            edit_operation=str(edit_operation),
            target_reachable_count=int(target_reachable_count),
            topology_profile=str(topology_profile),
        )
        node_count = int(feasible_node_support[int(node_index % len(feasible_node_support))])
    if int(node_count) not in feasible_node_support:
        raise ValueError("node_count is outside feasible support for reachable-count-after-edge-edit")

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

    query_probabilities = graph_query_probabilities_from_alias_map(edit_operation_probabilities, QUERY_ID_BY_OPERATION)
    return _ResolvedQuery(
        edit_operation=str(edit_operation),
        query_id=str(QUERY_ID_BY_OPERATION[str(edit_operation)]),
        prompt_query_key=str(PROMPT_QUERY_KEY_BY_OPERATION[str(edit_operation)]),
        node_count=int(node_count),
        target_reachable_count=int(target_reachable_count),
        topology_profile=str(topology_profile),
        layout_variant=str(layout_variant),
        label_variant=str(label_variant),
        node_shape_variant=str(node_shape_variant),
        layout_transform_variant=str(layout_transform_variant),
        edge_routing_variant=str(edge_routing_variant),
        node_color_name=str(node_color_name),
        edit_operation_probabilities={str(key): float(value) for key, value in edit_operation_probabilities.items()},
        query_id_probabilities=dict(query_probabilities),
        node_count_probabilities=dict(
            uniform_probability_map(
                tuple(int(value) for value in feasible_node_support),
                selected=int(node_count) if explicit_node_count is not None else None,
            )
        ),
        target_reachable_count_probabilities=dict(
            uniform_probability_map(
                tuple(int(value) for value in feasible_targets),
                selected=int(target_reachable_count) if explicit_target_count is not None else None,
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


def _build_complexity(
    *,
    graph_sample: Any,
    query: _ResolvedQuery,
    render_params: GraphRenderParams,
    rendered_scene: Any,
) -> Any:
    """Build one within-task normalized complexity record."""

    node_count = int(query.node_count)
    max_edge_count = max(1, int(node_count) * (int(node_count) - 1))
    edge_density = float(graph_sample.edge_count) / float(max_edge_count)
    crossing_norm = normalize_float_with_bounds(
        float(rendered_scene.crossing_count),
        (0.0, max(1.0, float(graph_sample.edge_count))),
    )
    post_count = int(query.target_reachable_count)
    pre_count = int(len(graph_sample.pre_edit_reachable_labels))
    delta_count = abs(int(pre_count) - int(post_count))
    unreachable_count = max(0, int(node_count) - int(post_count))
    edit_bonus = 1.0 if str(query.edit_operation) == "edge_addition" else 0.9
    components = {
        "visual_scan": (0.55 * normalize_int_with_bounds(int(node_count), (_DEFAULTS.node_count_min, _DEFAULTS.directed_node_count_max)))
        + (0.25 * normalize_float_with_bounds(float(edge_density), (0.0, 1.0)))
        + (0.20 * normalize_int_with_bounds(int(unreachable_count), (0, _DEFAULTS.directed_node_count_max - 1))),
        "topology_reasoning": (0.55 * normalize_int_with_bounds(
            int(post_count),
            (_DEFAULTS.target_reachable_count_min, _DEFAULTS.target_reachable_count_max),
        ))
        + (0.30 * normalize_int_with_bounds(int(delta_count), (1, _DEFAULTS.directed_node_count_max - 1)))
        + (0.15 * float(edit_bonus)),
        "ambiguity": (0.45 * normalize_int_with_bounds(int(pre_count + post_count), (2, _DEFAULTS.directed_node_count_max * 2)))
        + (0.35 * normalize_int_with_bounds(int(unreachable_count), (0, _DEFAULTS.directed_node_count_max - 1)))
        + (0.20 * normalize_int_with_bounds(int(len(graph_sample.post_edit_edge_labels)), (0, max_edge_count))),
        "clutter": (0.60 * normalize_float_with_bounds(float(edge_density), (0.0, 1.0)))
        + (0.25 * crossing_norm)
        + (0.15 * normalize_int_with_bounds(
            int(render_params.node_radius_px),
            (_DEFAULTS.node_radius_min_px, _DEFAULTS.node_radius_max_px),
        )),
    }
    return build_graph_complexity(weights=_COMPLEXITY_WEIGHTS, components=components)


class GraphRelationReachableCountAfterEdgeEditTask:
    """Count nodes reachable from a query node after one hypothetical arrow edit."""

    task_id = TASK_ID
    domain = "graph"
    task_group = "relation"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic directed edge-edit reachable-count instance."""

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

        graph_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.graph")
        last_error: Exception | None = None
        graph_sample = None
        rendered_scene = None
        image = None
        background_meta = {}
        post_noise_meta = {}
        for attempt in range(max(1, int(max_attempts))):
            try:
                graph_sample = sample_reachable_count_after_edge_edit_graph(
                    graph_rng,
                    edit_operation=str(query.edit_operation),
                    node_count=int(query.node_count),
                    target_reachable_count=int(query.target_reachable_count),
                    topology_profile=str(query.topology_profile),
                    label_variant=str(query.label_variant),
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
                    scene_title="Directed Graph",
                    directed=True,
                    base_image=background,
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
            raise RuntimeError("failed to generate graph reachable-count-after-edge-edit instance") from last_error
        if graph_sample is None or rendered_scene is None or image is None:
            raise RuntimeError("failed to generate graph reachable-count-after-edge-edit instance")

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description_directed",
                "evidence_hint",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_json_example, prompt_json_example_answer_only = build_graph_prompt_json_examples(evidence_value=[[180, 220], [310, 180], [430, 260]], answer_value=3)
        prompt_query_label = format_graph_prompt_label(
            str(graph_sample.query_label),
            label_variant=str(query.label_variant),
        )
        prompt_edit_label_a = format_graph_prompt_label(
            str(graph_sample.edit_edge[0]),
            label_variant=str(query.label_variant),
        )
        prompt_edit_label_b = format_graph_prompt_label(
            str(graph_sample.edit_edge[1]),
            label_variant=str(query.label_variant),
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query.prompt_query_key),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_directed"]),
                "query_label": str(prompt_query_label),
                "edit_label_a": str(prompt_edit_label_a),
                "edit_label_b": str(prompt_edit_label_b),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]).format(query_label=str(prompt_query_label)),
                "answer_hint": str(prompt_defaults["answer_hint"]).format(query_label=str(prompt_query_label)),
                "json_example": str(prompt_json_example),
                "json_example_answer_only": str(prompt_json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        evidence_labels = tuple(sorted((str(label) for label in graph_sample.target_labels), key=graph_label_sort_key))
        answer_gt = TypedValue(type="integer", value=int(len(evidence_labels)))
        evidence_projection = projected_node_point_evidence(rendered_scene, evidence_labels)
        evidence_points = [list(point) for point in evidence_projection["pixel_point_set"]]
        evidence_gt = TypedValue(type="point_set", value=list(evidence_points))
        target_label_set = {str(label) for label in evidence_labels}
        pre_reachable_label_set = {str(label) for label in graph_sample.pre_edit_reachable_labels}
        edit_edge = tuple(str(label) for label in graph_sample.edit_edge)
        edge_label_set = {(str(edge.node_u_label), str(edge.node_v_label)) for edge in rendered_scene.edges}
        edit_edge_visible = bool(tuple(edit_edge) in edge_label_set)

        post_successors_by_label = {
            str(key): tuple(str(value) for value in values)
            for key, values in graph_sample.post_edit_successors_by_label.items()
        }
        dist_start, _ = bfs_dist_count_by_adjacency(post_successors_by_label, start=str(graph_sample.query_label))
        reachable_labels = tuple(sorted((str(label) for label in dist_start.keys()), key=graph_label_sort_key))
        if tuple(reachable_labels) != tuple(evidence_labels):
            raise ValueError("reachable edge-edit sampler failed to preserve the requested post-edit reachable set")

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
                "is_pre_edit_reachable": bool(str(node.label) in pre_reachable_label_set),
                "is_post_edit_reachable": bool(str(node.label) in target_label_set),
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
                "is_edit_edge": bool((str(edge.node_u_label), str(edge.node_v_label)) == tuple(edit_edge)),
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
                "scene_kind": "graph_reachable_count_after_edge_edit",
                "entities": [*node_entities, *edge_entities],
                "relations": {
                    "query_id": str(query.query_id),
                    "relation_rule": str(RELATION_RULE_BY_OPERATION[str(query.edit_operation)]),
                    "graph_directionality": "directed",
                    "edit_operation": str(query.edit_operation),
                    "edit_edge": list(edit_edge),
                    "edit_edge_visible_in_rendered_graph": bool(edit_edge_visible),
                    "query_label": str(graph_sample.query_label),
                    "matching_labels": list(evidence_labels),
                    "unreachable_labels": list(graph_sample.unreachable_labels),
                    "pre_edit_reachable_labels": list(graph_sample.pre_edit_reachable_labels),
                    "post_edit_reachable_labels": list(graph_sample.post_edit_reachable_labels),
                    "pre_edit_successors_by_label": {str(key): list(values) for key, values in graph_sample.pre_edit_successors_by_label.items()},
                    "post_edit_successors_by_label": {str(key): list(values) for key, values in graph_sample.post_edit_successors_by_label.items()},
                    "pre_edit_predecessors_by_label": {str(key): list(values) for key, values in graph_sample.pre_edit_predecessors_by_label.items()},
                    "post_edit_predecessors_by_label": {str(key): list(values) for key, values in graph_sample.post_edit_predecessors_by_label.items()},
                    "in_degrees_by_label": {str(key): int(value) for key, value in graph_sample.in_degrees_by_label.items()},
                    "out_degrees_by_label": {str(key): int(value) for key, value in graph_sample.out_degrees_by_label.items()},
                    "edge_labels": [list(edge) for edge in graph_sample.edge_labels],
                    "post_edit_edge_labels": [list(edge) for edge in graph_sample.post_edit_edge_labels],
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
                    "query_id": str(query.query_id),
                    "internal_query_id": str(query.query_id),
                    "query_id_probabilities": dict(query.query_id_probabilities),
                    "graph_directionality": "directed",
                    "edit_operation": str(query.edit_operation),
                    "edit_operation_probabilities": dict(query.edit_operation_probabilities),
                    "node_count": int(query.node_count),
                    "edge_count": int(graph_sample.edge_count),
                    "target_reachable_count": int(query.target_reachable_count),
                    "query_label": str(graph_sample.query_label),
                    "edit_edge": list(edit_edge),
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
            "render_map": {
                "image_id": "img0",
                "anchors": {},
            },
            "execution_trace": {
                "query_id": str(query.query_id),
                "internal_query_id": str(query.query_id),
                "query_id_probabilities": dict(query.query_id_probabilities),
                "scene_variant": str(rendered_scene.layout_variant),
                "question_format": str(query.query_id),
                "graph_directionality": "directed",
                "edit_operation": str(query.edit_operation),
                "edit_edge": list(edit_edge),
                "edit_edge_visible_in_rendered_graph": bool(edit_edge_visible),
                "node_count": int(query.node_count),
                "edge_count": int(graph_sample.edge_count),
                "post_edit_edge_count": int(len(graph_sample.post_edit_edge_labels)),
                "target_reachable_count": int(query.target_reachable_count),
                "answer": int(len(evidence_labels)),
                "query_label": str(graph_sample.query_label),
                "matching_labels": list(evidence_labels),
                "unreachable_labels": list(graph_sample.unreachable_labels),
                "pre_edit_reachable_labels": list(graph_sample.pre_edit_reachable_labels),
                "post_edit_reachable_labels": list(graph_sample.post_edit_reachable_labels),
                "pre_edit_successors_by_label": {str(key): list(values) for key, values in graph_sample.pre_edit_successors_by_label.items()},
                "post_edit_successors_by_label": {str(key): list(values) for key, values in graph_sample.post_edit_successors_by_label.items()},
                "pre_edit_predecessors_by_label": {str(key): list(values) for key, values in graph_sample.pre_edit_predecessors_by_label.items()},
                "post_edit_predecessors_by_label": {str(key): list(values) for key, values in graph_sample.post_edit_predecessors_by_label.items()},
                "successors_by_label": {str(key): list(values) for key, values in graph_sample.successors_by_label.items()},
                "predecessors_by_label": {str(key): list(values) for key, values in graph_sample.predecessors_by_label.items()},
                "edge_labels": [list(edge) for edge in graph_sample.edge_labels],
                "post_edit_edge_labels": [list(edge) for edge in graph_sample.post_edit_edge_labels],
                "in_degrees_by_label": {str(key): int(value) for key, value in graph_sample.in_degrees_by_label.items()},
                "out_degrees_by_label": {str(key): int(value) for key, value in graph_sample.out_degrees_by_label.items()},
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
                "type": "object_set",
                "labels": list(evidence_labels),
                "query_label": str(graph_sample.query_label),
                "edit_edge": list(edit_edge),
                "edit_operation": str(query.edit_operation),
            },
            "projected_evidence": {
                "type": "point_set",
                "point_set": list(evidence_points),
                **dict(evidence_projection),
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
            query_id=str(query.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["GraphRelationReachableCountAfterEdgeEditTask"]
