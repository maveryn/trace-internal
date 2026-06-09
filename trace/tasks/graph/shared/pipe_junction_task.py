"""Shared public task base for pipe-junction graph tasks."""

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
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ..shared.complexity import (
    build_graph_complexity,
    normalize_float_with_bounds,
    normalize_int_with_bounds,
    resolve_graph_complexity_weights,
)
from ..shared.style import SUPPORTED_NODE_COLOR_NAMES
from ..shared.task_support import format_graph_prompt_label, resolve_graph_named_variant, resolve_graph_render_params
from ..shared.visual_defaults import load_graph_background_defaults, load_graph_noise_defaults
from .graph_scene import GraphRenderParams
from .pipe_junction_scene import (
    SUPPORTED_PIPE_GRID_SHAPE_VARIANTS,
    SUPPORTED_PIPE_LABEL_VARIANTS,
    PipeJunctionNetworkSample,
    RenderedPipeJunctionScene,
    feasible_pipe_node_counts,
    projected_pipe_edge_pair_annotation,
    projected_pipe_node_point_annotation,
    render_pipe_network_scene,
    sample_pipe_bridge_network,
    sample_pipe_exact_distance_network,
    sample_pipe_reachable_network,
    sample_pipe_shortest_path_network,
)


PUBLIC_PIPE_SCENE_ID = "pipe_network"


@dataclass(frozen=True)
class PipeJunctionTaskDefaults:
    """Stable fallback defaults for pipe-junction graph tasks."""

    node_count_min: int = 6
    node_count_max: int = 13
    target_shortest_path_length_min: int = 2
    target_shortest_path_length_max: int = 6
    target_reachable_count_min: int = 3
    target_reachable_count_max: int = 8
    target_count_min: int = 0
    target_count_max: int = 7
    query_distance_min: int = 2
    query_distance_max: int = 3
    target_exact_distance_count_min: int = 1
    target_exact_distance_count_max: int = 5
    canvas_width: int = 864
    canvas_height: int = 640
    outer_margin_px: int = 28
    panel_padding_px: int = 24
    panel_corner_radius_px: int = 20
    panel_title_font_size_px: int = 24
    node_shape_variant: str = "circle"
    node_radius_min_px: int = 19
    node_radius_max_px: int = 24
    edge_width_px: int = 4
    arrow_length_px: int = 12
    arrow_width_px: int = 7
    node_border_width_px: int = 2
    label_font_size_px: int = 21
    background_color_rgb: Tuple[int, int, int] = (247, 248, 251)
    panel_fill_rgb: Tuple[int, int, int] = (255, 255, 255)
    panel_border_rgb: Tuple[int, int, int] = (205, 212, 224)
    title_color_rgb: Tuple[int, int, int] = (70, 78, 96)
    edge_color_rgb: Tuple[int, int, int] = (64, 111, 166)
    node_fill_rgb: Tuple[int, int, int] = (72, 116, 183)
    node_border_rgb: Tuple[int, int, int] = (38, 67, 118)
    label_text_rgb: Tuple[int, int, int] = (255, 255, 255)
    label_stroke_rgb: Tuple[int, int, int] = (38, 67, 118)


@dataclass(frozen=True)
class PipeJunctionResolvedQuery:
    """Resolved support/style axes for one pipe-junction graph instance."""

    node_count: int
    grid_shape_variant: str
    label_variant: str
    node_color_name: str
    target_shortest_path_length: int = 0
    target_reachable_count: int = 0
    target_count: int = 0
    query_distance: int = 0
    target_exact_distance_count: int = 0
    node_count_probabilities: Dict[str, float] | None = None
    grid_shape_variant_probabilities: Dict[str, float] | None = None
    label_variant_probabilities: Dict[str, float] | None = None
    node_color_name_probabilities: Dict[str, float] | None = None
    target_shortest_path_length_probabilities: Dict[str, float] | None = None
    target_reachable_count_probabilities: Dict[str, float] | None = None
    target_count_probabilities: Dict[str, float] | None = None
    query_distance_probabilities: Dict[str, float] | None = None
    target_exact_distance_count_probabilities: Dict[str, float] | None = None


def _feasible_pipe_bridge_target_counts(node_count: int, configured_targets: Tuple[int, ...]) -> Tuple[int, ...]:
    """Return bridge-count targets realizable by the grid pipe sampler for this node count."""

    if int(node_count) <= 6:
        support = (0, 2, 5)
    elif int(node_count) == 7:
        support = (0, 1, 3)
    elif int(node_count) == 8:
        support = (0, 1, 2, 4)
    elif int(node_count) == 9:
        support = (0, 1, 2, 3, 5)
    elif int(node_count) == 10:
        support = (0, 1, 2, 3, 4)
    else:
        support = tuple(range(0, max(configured_targets or (0,)) + 1))
    configured = {int(value) for value in configured_targets}
    return tuple(int(value) for value in support if int(value) in configured)


class PipeJunctionGraphTaskBase:
    """Shared generator for public pipe-junction graph tasks."""

    domain = "graph"
    task_group = ""
    task_id = ""
    query_id = ""
    prompt_question_key = ""
    prompt_annotation_key = "annotation_hint"
    prompt_task_key_fallback = ""
    scene_title = "Pipe Junction Board"
    _fallback_defaults = PipeJunctionTaskDefaults()

    def _load_defaults(self) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        group_defaults = get_task_group_defaults(self.domain, self.task_group)
        gen_defaults, render_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
            group_defaults if isinstance(group_defaults, Mapping) else {},
            task_id=self.task_id,
        )
        background_defaults = load_graph_background_defaults(task_group=self.task_group)
        noise_defaults = load_graph_noise_defaults(task_group=self.task_group, apply_prob=0.5)
        complexity_weights = resolve_graph_complexity_weights(group_defaults, task_id=self.task_id)
        return gen_defaults, render_defaults, prompt_defaults, background_defaults, noise_defaults, complexity_weights

    def _target_support(self, gen_defaults: Mapping[str, Any], params: Mapping[str, Any]) -> tuple[Tuple[int, ...], str]:
        if self.query_id == "pipe_shortest_path_length":
            low_key, high_key = "target_shortest_path_length_min", "target_shortest_path_length_max"
        elif self.query_id == "pipe_reachable_junction_count":
            low_key, high_key = "target_reachable_count_min", "target_reachable_count_max"
        elif self.query_id == "pipe_bridge_count":
            low_key, high_key = "target_count_min", "target_count_max"
        elif self.query_id == "pipe_exact_distance_count":
            low_key, high_key = "target_exact_distance_count_min", "target_exact_distance_count_max"
        else:
            raise ValueError(f"unsupported pipe query_id: {self.query_id}")
        low = int(params.get(low_key, group_default(gen_defaults, low_key, getattr(self._fallback_defaults, low_key))))
        high = int(params.get(high_key, group_default(gen_defaults, high_key, getattr(self._fallback_defaults, high_key))))
        if int(low) > int(high):
            raise ValueError(f"empty support for {self.task_id}:{low_key}/{high_key}")
        return tuple(range(int(low), int(high) + 1)), str(low_key[:-4] if low_key.endswith("_min") else low_key)

    def _resolve_query(self, instance_seed: int, *, params: Mapping[str, Any], gen_defaults: Mapping[str, Any]) -> PipeJunctionResolvedQuery:
        selection_index = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{self.task_id}:query_support"))
        target_namespace = f"{self.task_id}:query_support"
        if self.query_id == "pipe_shortest_path_length":
            target_namespace = f"{self.task_id}:target_support_v0"
        elif self.query_id == "pipe_exact_distance_count":
            target_namespace = f"{self.task_id}:target_support_v0"
        target_selection_index = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=target_namespace))
        grid_rng = spawn_rng(int(instance_seed), f"{self.task_id}.grid_shape_variant")
        grid_shape_variant, grid_shape_probs = resolve_graph_named_variant(
            grid_rng,
            params=params,
            gen_defaults=gen_defaults,
            explicit_key="grid_shape_variant",
            weights_key="grid_shape_variant_weights",
            balance_flag_key="balanced_grid_shape_variant_sampling",
            supported=SUPPORTED_PIPE_GRID_SHAPE_VARIANTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
            namespace="grid_shape_variant",
        )
        label_rng = spawn_rng(int(instance_seed), f"{self.task_id}.label_variant")
        label_variant, label_probs = resolve_graph_named_variant(
            label_rng,
            params=params,
            gen_defaults=gen_defaults,
            explicit_key="label_variant",
            weights_key="label_variant_weights",
            balance_flag_key="balanced_label_variant_sampling",
            supported=SUPPORTED_PIPE_LABEL_VARIANTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
            namespace="label_variant",
        )
        color_rng = spawn_rng(int(instance_seed), f"{self.task_id}.node_color_name")
        node_color_name, color_probs = resolve_graph_named_variant(
            color_rng,
            params=params,
            gen_defaults=gen_defaults,
            explicit_key="node_color_name",
            weights_key="node_color_name_weights",
            balance_flag_key="balanced_node_color_name_sampling",
            supported=SUPPORTED_NODE_COLOR_NAMES,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
            namespace="node_color_name",
        )

        node_count_min = int(params.get("node_count_min", group_default(gen_defaults, "node_count_min", self._fallback_defaults.node_count_min)))
        node_count_max = int(params.get("node_count_max", group_default(gen_defaults, "node_count_max", self._fallback_defaults.node_count_max)))
        target_support, target_axis = self._target_support(gen_defaults, params)

        explicit_target = None
        if target_axis in params:
            explicit_target = int(params[target_axis])
        elif self.query_id == "pipe_bridge_count" and "target_count" in params:
            explicit_target = int(params["target_count"])

        filtered_targets = [int(value) for value in target_support if explicit_target is None or int(value) == int(explicit_target)]
        if not filtered_targets:
            raise ValueError("requested pipe target is outside configured support")
        target_value = int(filtered_targets[int(target_selection_index % len(filtered_targets))]) if explicit_target is None else int(explicit_target)

        query_distance_support: Tuple[int, ...] = ()
        query_distance = 0
        if self.query_id == "pipe_exact_distance_count":
            distance_min = int(params.get("query_distance_min", group_default(gen_defaults, "query_distance_min", self._fallback_defaults.query_distance_min)))
            distance_max = int(params.get("query_distance_max", group_default(gen_defaults, "query_distance_max", self._fallback_defaults.query_distance_max)))
            query_distance_support = tuple(range(int(distance_min), int(distance_max) + 1))
            if not query_distance_support:
                raise ValueError("query_distance support is empty")
            explicit_distance = params.get("query_distance")
            if explicit_distance is not None:
                query_distance = int(explicit_distance)
                if int(query_distance) not in query_distance_support:
                    raise ValueError("requested query_distance is outside configured support")
            else:
                query_distance = int(query_distance_support[(int(selection_index) // max(1, len(filtered_targets))) % len(query_distance_support)])

        feasible_nodes = feasible_pipe_node_counts(
            node_count_min=int(node_count_min),
            node_count_max=int(node_count_max),
            grid_shape_variant=str(grid_shape_variant),
        )
        if self.query_id == "pipe_shortest_path_length":
            feasible_nodes = tuple(int(value) for value in feasible_nodes if int(value) >= int(target_value) + 2)
        elif self.query_id == "pipe_reachable_junction_count":
            feasible_nodes = tuple(int(value) for value in feasible_nodes if int(value) >= int(target_value) + 1)
        elif self.query_id == "pipe_bridge_count":
            feasible_nodes = tuple(int(value) for value in feasible_nodes if int(value) >= max(4, int(target_value) + 1))
        elif self.query_id == "pipe_exact_distance_count":
            feasible_nodes = tuple(int(value) for value in feasible_nodes if int(value) >= max(5, int(target_value) + int(query_distance) + 1))
        if not feasible_nodes:
            raise ValueError("no feasible pipe node-count support for requested query")

        explicit_node_count = params.get("node_count")
        if explicit_node_count is not None:
            node_count = int(explicit_node_count)
            if int(node_count) not in feasible_nodes:
                raise ValueError("node_count is outside feasible pipe support")
        else:
            node_count = int(feasible_nodes[(int(selection_index) // max(1, len(filtered_targets))) % len(feasible_nodes)])

        feasible_bridge_targets: Tuple[int, ...] = tuple(filtered_targets)
        if self.query_id == "pipe_bridge_count":
            feasible_bridge_targets = _feasible_pipe_bridge_target_counts(int(node_count), tuple(filtered_targets))
            if not feasible_bridge_targets:
                raise ValueError("no feasible pipe bridge-count target support for selected node count")
            if explicit_target is not None:
                if int(target_value) not in set(feasible_bridge_targets):
                    raise ValueError("requested pipe bridge-count target is infeasible for selected node count")
            else:
                target_value = int(feasible_bridge_targets[int(target_selection_index % len(feasible_bridge_targets))])

        kwargs: Dict[str, Any] = {
            "node_count": int(node_count),
            "grid_shape_variant": str(grid_shape_variant),
            "label_variant": str(label_variant),
            "node_color_name": str(node_color_name),
            "node_count_probabilities": dict(uniform_probability_map(tuple(int(value) for value in feasible_nodes), selected=int(node_count) if explicit_node_count is not None else None)),
            "grid_shape_variant_probabilities": dict(grid_shape_probs),
            "label_variant_probabilities": dict(label_probs),
            "node_color_name_probabilities": dict(color_probs),
        }
        if self.query_id == "pipe_shortest_path_length":
            kwargs["target_shortest_path_length"] = int(target_value)
            kwargs["target_shortest_path_length_probabilities"] = dict(uniform_probability_map(tuple(filtered_targets), selected=int(target_value) if explicit_target is not None else None))
        elif self.query_id == "pipe_reachable_junction_count":
            kwargs["target_reachable_count"] = int(target_value)
            kwargs["target_reachable_count_probabilities"] = dict(uniform_probability_map(tuple(filtered_targets), selected=int(target_value) if explicit_target is not None else None))
        elif self.query_id == "pipe_bridge_count":
            kwargs["target_count"] = int(target_value)
            kwargs["target_count_probabilities"] = dict(uniform_probability_map(tuple(feasible_bridge_targets), selected=int(target_value) if explicit_target is not None else None))
        elif self.query_id == "pipe_exact_distance_count":
            kwargs["query_distance"] = int(query_distance)
            kwargs["target_exact_distance_count"] = int(target_value)
            kwargs["query_distance_probabilities"] = dict(uniform_probability_map(tuple(query_distance_support), selected=int(query_distance) if params.get("query_distance") is not None else None))
            kwargs["target_exact_distance_count_probabilities"] = dict(uniform_probability_map(tuple(filtered_targets), selected=int(target_value) if explicit_target is not None else None))
        return PipeJunctionResolvedQuery(**kwargs)

    def _sample_network(self, instance_seed: int, query: PipeJunctionResolvedQuery, *, max_attempts: int) -> PipeJunctionNetworkSample:
        rng = spawn_rng(int(instance_seed), f"{self.task_id}.pipe_network")
        if self.query_id == "pipe_shortest_path_length":
            return sample_pipe_shortest_path_network(
                rng,
                node_count=int(query.node_count),
                target_shortest_path_length=int(query.target_shortest_path_length),
                grid_shape_variant=str(query.grid_shape_variant),
                label_variant=str(query.label_variant),
                max_attempts=max(200, int(max_attempts)),
            )
        if self.query_id == "pipe_reachable_junction_count":
            return sample_pipe_reachable_network(
                rng,
                node_count=int(query.node_count),
                target_reachable_count=int(query.target_reachable_count),
                grid_shape_variant=str(query.grid_shape_variant),
                label_variant=str(query.label_variant),
                max_attempts=max(200, int(max_attempts)),
            )
        if self.query_id == "pipe_bridge_count":
            return sample_pipe_bridge_network(
                rng,
                node_count=int(query.node_count),
                target_bridge_count=int(query.target_count),
                grid_shape_variant=str(query.grid_shape_variant),
                label_variant=str(query.label_variant),
                max_attempts=max(400, int(max_attempts) * 2),
            )
        if self.query_id == "pipe_exact_distance_count":
            return sample_pipe_exact_distance_network(
                rng,
                node_count=int(query.node_count),
                query_distance=int(query.query_distance),
                target_exact_distance_count=int(query.target_exact_distance_count),
                grid_shape_variant=str(query.grid_shape_variant),
                label_variant=str(query.label_variant),
                max_attempts=max(400, int(max_attempts) * 2),
            )
        raise ValueError(f"unsupported pipe query_id: {self.query_id}")

    def _build_prompt_json_examples(self) -> Tuple[str, str]:
        if self.query_id == "pipe_bridge_count":
            annotation = [[[180, 220], [310, 220]], [[310, 220], [430, 300]]]
            answer = 2
        elif self.query_id == "pipe_shortest_path_length":
            annotation = [[180, 220], [310, 220], [430, 300]]
            answer = 2
        else:
            annotation = [[180, 220], [310, 220], [430, 300]]
            answer = 3
        return (
            json.dumps({"annotation": annotation, "answer": answer}, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
            json.dumps({"answer": answer}, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
        )

    def _question_slots(self, pipe_sample: PipeJunctionNetworkSample) -> Dict[str, Any]:
        return {
            "source_label": format_graph_prompt_label(str(pipe_sample.source_label), label_variant=str(pipe_sample.label_variant)),
            "goal_label": format_graph_prompt_label(str(pipe_sample.goal_label), label_variant=str(pipe_sample.label_variant)),
            "query_label": format_graph_prompt_label(str(pipe_sample.query_label), label_variant=str(pipe_sample.label_variant)),
            "query_distance": int(pipe_sample.query_distance),
        }

    def _annotation_and_answer(self, pipe_sample: PipeJunctionNetworkSample, rendered_scene: RenderedPipeJunctionScene) -> tuple[TypedValue, TypedValue, Dict[str, Any], Dict[str, Any]]:
        if self.query_id == "pipe_shortest_path_length":
            annotation_labels = tuple(str(label) for label in pipe_sample.target_labels)
            projection = projected_pipe_node_point_annotation(rendered_scene, annotation_labels)
            annotation = [list(point) for point in projection["pixel_point_sequence"]]
            return (
                TypedValue(type="integer", value=int(pipe_sample.target_shortest_path_length)),
                TypedValue(type="point_sequence", value=list(annotation)),
                {"type": "node_label_sequence", "labels": list(annotation_labels)},
                {"type": "point_sequence", **dict(projection)},
            )
        if self.query_id == "pipe_bridge_count":
            annotation_edges = tuple((str(left), str(right)) for left, right in pipe_sample.target_edges)
            projection = projected_pipe_edge_pair_annotation(rendered_scene, annotation_edges)
            annotation = [[list(point) for point in pair] for pair in projection["point_pair_set"]]
            return (
                TypedValue(type="integer", value=int(pipe_sample.target_bridge_count)),
                TypedValue(type="point_pair_set", value=list(annotation)),
                {"type": "edge_pair_set", "edges": [list(edge) for edge in annotation_edges]},
                {"type": "point_pair_set", **dict(projection)},
            )
        annotation_labels = tuple(str(label) for label in pipe_sample.target_labels)
        projection = projected_pipe_node_point_annotation(rendered_scene, annotation_labels)
        annotation = [list(point) for point in projection["pixel_point_set"]]
        answer_value = (
            int(pipe_sample.target_reachable_count)
            if self.query_id == "pipe_reachable_junction_count"
            else int(pipe_sample.target_exact_distance_count)
        )
        return (
            TypedValue(type="integer", value=int(answer_value)),
            TypedValue(type="point_set", value=list(annotation)),
            {"type": "node_label_set", "labels": list(annotation_labels)},
            {"type": "point_set", **dict(projection)},
        )

    def _build_complexity(
        self,
        *,
        query: PipeJunctionResolvedQuery,
        pipe_sample: PipeJunctionNetworkSample,
        render_params: GraphRenderParams,
        complexity_weights: Mapping[str, float],
    ) -> Any:
        node_count = int(query.node_count)
        open_edge_count = int(len(pipe_sample.open_edges))
        blocked_edge_count = int(len(pipe_sample.blocked_edges))
        max_edges = max(1, (int(node_count) * 2))
        if self.query_id == "pipe_shortest_path_length":
            target_value = int(pipe_sample.target_shortest_path_length)
            target_bounds = (self._fallback_defaults.target_shortest_path_length_min, self._fallback_defaults.target_shortest_path_length_max)
        elif self.query_id == "pipe_reachable_junction_count":
            target_value = int(pipe_sample.target_reachable_count)
            target_bounds = (self._fallback_defaults.target_reachable_count_min, self._fallback_defaults.target_reachable_count_max)
        elif self.query_id == "pipe_bridge_count":
            target_value = int(pipe_sample.target_bridge_count)
            target_bounds = (self._fallback_defaults.target_count_min, self._fallback_defaults.target_count_max)
        else:
            target_value = int(pipe_sample.target_exact_distance_count + pipe_sample.query_distance)
            target_bounds = (
                self._fallback_defaults.target_exact_distance_count_min + self._fallback_defaults.query_distance_min,
                self._fallback_defaults.target_exact_distance_count_max + self._fallback_defaults.query_distance_max,
            )
        components = {
            "visual_scan": (0.70 * normalize_int_with_bounds(int(node_count), (self._fallback_defaults.node_count_min, self._fallback_defaults.node_count_max)))
            + (0.30 * normalize_int_with_bounds(int(blocked_edge_count), (0, 6))),
            "topology_reasoning": (0.65 * normalize_int_with_bounds(int(target_value), target_bounds))
            + (0.35 * normalize_float_with_bounds(float(open_edge_count) / float(max_edges), (0.0, 1.0))),
            "ambiguity": (0.55 * normalize_int_with_bounds(int(blocked_edge_count), (0, 6)))
            + (0.45 * normalize_float_with_bounds(float(open_edge_count) / float(max_edges), (0.0, 1.0))),
            "clutter": (0.65 * normalize_float_with_bounds(float(open_edge_count + blocked_edge_count) / float(max_edges), (0.0, 1.0)))
            + (0.35 * normalize_int_with_bounds(int(render_params.node_radius_px), (self._fallback_defaults.node_radius_min_px, self._fallback_defaults.node_radius_max_px))),
        }
        return build_graph_complexity(weights=complexity_weights, components=components)

    def _build_trace_payload(
        self,
        *,
        prompt_defaults: Mapping[str, Any],
        prompt_artifacts: Any,
        query: PipeJunctionResolvedQuery,
        pipe_sample: PipeJunctionNetworkSample,
        rendered_scene: RenderedPipeJunctionScene,
        render_params: GraphRenderParams,
        background_meta: Mapping[str, Any],
        post_noise_meta: Mapping[str, Any],
        witness_symbolic: Mapping[str, Any],
        projected_annotation: Mapping[str, Any],
    ) -> Dict[str, Any]:
        target_node_set = {str(label) for label in pipe_sample.target_labels}
        target_edge_set = {tuple(edge) for edge in pipe_sample.target_edges}
        node_entities = [
            {
                "entity_id": f"junction_{node.label}",
                "entity_kind": "pipe_junction",
                "label": str(node.label),
                "open_degree": int(node.open_degree),
                "grid_cell": list(node.grid_cell),
                "open_neighbors": list(node.open_neighbors),
                "center_px": list(node.center_xy),
                "bbox_xyxy": list(node.bbox_xyxy),
                "is_query_node": bool(str(node.label) == str(pipe_sample.query_label)),
                "is_source_node": bool(str(node.label) == str(pipe_sample.source_label)),
                "is_goal_node": bool(str(node.label) == str(pipe_sample.goal_label)),
                "is_witness_node": bool(str(node.label) in target_node_set),
            }
            for node in rendered_scene.nodes
        ]
        edge_entities = [
            {
                "entity_id": str(edge.edge_id),
                "entity_kind": "pipe_segment",
                "node_u_label": str(edge.node_u_label),
                "node_v_label": str(edge.node_v_label),
                "pipe_state": str(edge.pipe_state),
                "segment_px": [list(edge.segment_px[0]), list(edge.segment_px[1])],
                "is_open": bool(str(edge.pipe_state) == "open"),
                "is_blocked": bool(str(edge.pipe_state) == "blocked"),
                "is_witness_edge": bool((str(edge.node_u_label), str(edge.node_v_label)) in target_edge_set),
            }
            for edge in rendered_scene.edges
        ]
        query_params: Dict[str, Any] = {
            "query_id": str(self.query_id),
            "scene_id": PUBLIC_PIPE_SCENE_ID,
            "node_count": int(query.node_count),
            "open_edge_count": int(len(pipe_sample.open_edges)),
            "blocked_edge_count": int(len(pipe_sample.blocked_edges)),
            "grid_shape_variant": str(query.grid_shape_variant),
            "grid_shape_variant_probabilities": dict(query.grid_shape_variant_probabilities or {}),
            "label_variant": str(query.label_variant),
            "label_variant_probabilities": dict(query.label_variant_probabilities or {}),
            "node_color_name": str(query.node_color_name),
            "node_color_name_probabilities": dict(query.node_color_name_probabilities or {}),
            "node_count_probabilities": dict(query.node_count_probabilities or {}),
        }
        for key in (
            "target_shortest_path_length",
            "target_reachable_count",
            "target_count",
            "query_distance",
            "target_exact_distance_count",
        ):
            value = getattr(query, key)
            active_zero_key = (
                (key == "target_count" and self.query_id == "pipe_bridge_count")
                or (key == "query_distance" and self.query_id == "pipe_exact_distance_count")
            )
            if int(value) != 0 or bool(active_zero_key):
                query_params[key] = int(value)
        for key in (
            "target_shortest_path_length_probabilities",
            "target_reachable_count_probabilities",
            "target_count_probabilities",
            "query_distance_probabilities",
            "target_exact_distance_count_probabilities",
        ):
            value = getattr(query, key)
            if isinstance(value, Mapping) and value:
                query_params[key] = dict(value)

        return {
            "scene_ir": {
                "scene_kind": "pipe_network",
                "domain": self.domain,
                "scene_id": PUBLIC_PIPE_SCENE_ID,
                "task_id": self.task_id,
                "query_id": str(self.query_id),
                "entities": [*node_entities, *edge_entities],
                "relations": {
                    "graph_directionality": "undirected",
                    "pipe_semantics": "only open pipes are traversable; blocked pipes are visible distractors",
                    "query_id": str(self.query_id),
                    "query_label": str(pipe_sample.query_label),
                    "source_label": str(pipe_sample.source_label),
                    "goal_label": str(pipe_sample.goal_label),
                    "matching_labels": list(pipe_sample.target_labels),
                    "matching_edges": [list(edge) for edge in pipe_sample.target_edges],
                    "open_adjacency_by_label": {str(key): list(values) for key, values in pipe_sample.adjacency_by_label.items()},
                    "open_edge_labels": [list(edge) for edge in pipe_sample.open_edge_labels],
                    "blocked_edge_labels": [list(edge) for edge in pipe_sample.blocked_edge_labels],
                    "degrees_by_label": {str(key): int(value) for key, value in pipe_sample.degrees_by_label.items()},
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(rendered_scene.panel_geometry),
                },
            },
            "query_spec": {
                "query_id": str(self.query_id),
                "scene_id": PUBLIC_PIPE_SCENE_ID,
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": query_params,
            },
            "render_spec": {
                "coord_space": "pixel",
                "scene_id": PUBLIC_PIPE_SCENE_ID,
                "canvas_size": list(rendered_scene.panel_geometry["canvas_size"]),
                "panel_geometry": dict(rendered_scene.panel_geometry),
                "style": {
                    "theme_tone": str(render_params.theme_tone),
                    "panel_style_variant": str(render_params.panel_style_variant),
                    "node_color_name": str(query.node_color_name),
                    "background_color_rgb": list(render_params.background_color_rgb),
                    "panel_fill_rgb": list(render_params.panel_fill_rgb),
                    "panel_border_rgb": list(render_params.panel_border_rgb),
                    "title_color_rgb": list(render_params.title_color_rgb),
                    "open_pipe_color_rgb": list(render_params.edge_color_rgb),
                    "node_fill_rgb": list(render_params.node_fill_rgb),
                    "node_border_rgb": list(render_params.node_border_rgb),
                    "label_text_rgb": list(render_params.label_text_rgb),
                    "label_stroke_rgb": list(render_params.label_stroke_rgb),
                    "node_radius_px": int(render_params.node_radius_px),
                    "open_pipe_width_px": int(rendered_scene.open_pipe_width_px),
                    "blocked_pipe_width_px": int(rendered_scene.blocked_pipe_width_px),
                    "label_font_size_px": int(render_params.label_font_size_px),
                    "resolved_label_font_size_px": int(rendered_scene.resolved_label_font_size_px),
                    "label_stroke_width_px": int(rendered_scene.resolved_label_stroke_width_px),
                    "font_family": str(render_params.font_family or ""),
                    "font_asset": dict(render_params.font_asset) if isinstance(render_params.font_asset, Mapping) else {},
                    "font_asset_version": str(render_params.font_asset_version or ""),
                    "font_exclusion_reason": str(render_params.font_exclusion_reason),
                    "context_text_elements": list(rendered_scene.panel_geometry.get("context_text_elements", [])),
                    "background_meta": dict(background_meta),
                    "post_image_noise_meta": dict(post_noise_meta),
                },
            },
            "render_map": {"image_id": "img0", "anchors": {}},
            "execution_trace": {
                "query_id": str(self.query_id),
                "scene_variant": str(rendered_scene.grid_shape_variant),
                "scene_id": PUBLIC_PIPE_SCENE_ID,
                "question_format": str(self.query_id),
                "node_count": int(query.node_count),
                "open_edge_count": int(len(pipe_sample.open_edges)),
                "blocked_edge_count": int(len(pipe_sample.blocked_edges)),
                "query_label": str(pipe_sample.query_label),
                "source_label": str(pipe_sample.source_label),
                "goal_label": str(pipe_sample.goal_label),
                "query_distance": int(pipe_sample.query_distance),
                "matching_labels": list(pipe_sample.target_labels),
                "matching_edges": [list(edge) for edge in pipe_sample.target_edges],
                "open_adjacency_by_label": {str(key): list(values) for key, values in pipe_sample.adjacency_by_label.items()},
                "open_edge_labels": [list(edge) for edge in pipe_sample.open_edge_labels],
                "blocked_edge_labels": [list(edge) for edge in pipe_sample.blocked_edge_labels],
                "grid_shape_variant": str(query.grid_shape_variant),
                "label_variant": str(query.label_variant),
                "node_color_name": str(query.node_color_name),
            },
            "witness_symbolic": dict(witness_symbolic),
            "projected_annotation": dict(projected_annotation),
        }

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic pipe-junction graph task instance."""

        gen_defaults, render_defaults, prompt_defaults, background_defaults, noise_defaults, complexity_weights = self._load_defaults()
        query = self._resolve_query(int(instance_seed), params=params, gen_defaults=gen_defaults)
        render_params = resolve_graph_render_params(
            params,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
            render_defaults=render_defaults,
            fallback_defaults=self._fallback_defaults,
            node_color_name=str(query.node_color_name),
            node_shape_variant="circle",
        )
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=background_defaults,
        )
        pipe_sample = self._sample_network(int(instance_seed), query, max_attempts=int(max_attempts))
        rendered_scene = render_pipe_network_scene(
            pipe_sample=pipe_sample,
            render_params=render_params,
            base_image=background,
            scene_title=self.scene_title,
            layout_seed=int(instance_seed),
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=noise_defaults,
        )

        prompt_defaults_required = required_group_defaults(
            prompt_defaults,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                self.prompt_annotation_key,
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_json_example, prompt_json_example_answer_only = self._build_prompt_json_examples()
        question_slots = self._question_slots(pipe_sample)
        annotation_hint = str(prompt_defaults_required[self.prompt_annotation_key]).format(**question_slots)
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults_required["bundle_id"]),
            scene_key=str(prompt_defaults_required["scene_key"]),
            task_key=str(prompt_defaults_required.get("task_key") or self.prompt_task_key_fallback),
            query_key=str(self.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults_required["object_description"]),
                **dict(question_slots),
                "json_output_contract": str(prompt_defaults_required["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults_required["json_output_contract_answer_only"]),
                "annotation_hint": str(annotation_hint),
                "answer_hint": str(prompt_defaults_required["answer_hint"]),
                "json_example": str(prompt_json_example),
                "json_example_answer_only": str(prompt_json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        answer_gt, annotation_gt, witness_symbolic, projected_annotation = self._annotation_and_answer(pipe_sample, rendered_scene)
        complexity = self._build_complexity(
            query=query,
            pipe_sample=pipe_sample,
            render_params=render_params,
            complexity_weights=complexity_weights,
        )
        trace_payload = self._build_trace_payload(
            prompt_defaults=prompt_defaults_required,
            prompt_artifacts=prompt_artifacts,
            query=query,
            pipe_sample=pipe_sample,
            rendered_scene=rendered_scene,
            render_params=render_params,
            background_meta=background_meta,
            post_noise_meta=post_noise_meta,
            witness_symbolic=witness_symbolic,
            projected_annotation=projected_annotation,
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=PUBLIC_PIPE_SCENE_ID,
            query_id=str(self.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = [
    "PUBLIC_PIPE_SCENE_ID",
    "PipeJunctionGraphTaskBase",
]
