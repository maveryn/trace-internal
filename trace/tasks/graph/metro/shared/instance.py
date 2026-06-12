"""Scene-local metro-route instance builder."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

from .....core.seed import spawn_rng
from .....core.scene_config import get_scene_defaults
from .....core.visual.background import make_background_canvas
from .....core.visual.noise import apply_post_image_noise
from ....shared.config_defaults import group_default, required_group_defaults, split_scene_generation_rendering_prompt_defaults
from ....shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ....shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_scene_prompt_variants
from ...shared.style import SUPPORTED_NODE_COLOR_NAMES
from ...shared.task_support import format_graph_prompt_label, resolve_graph_named_variant, resolve_graph_render_params
from ...shared.visual_defaults import load_graph_scene_background_defaults, load_graph_scene_noise_defaults
from ...shared.graph_scene import GraphRenderParams
from .scene_common import (
    SUPPORTED_METRO_LABEL_VARIANTS,
    MetroRouteNetworkSample,
    RenderedMetroRouteScene,
    feasible_metro_answer_counts,
    projected_metro_station_point_annotation,
    render_metro_scene,
    sample_metro_query_network,
)


PUBLIC_METRO_SCENE_ID = "metro"


@dataclass(frozen=True)
class MetroRouteTaskDefaults:
    """Stable fallback defaults for metro-route graph tasks."""

    target_count_min: int = 1
    target_count_max: int = 6
    query_distance_min: int = 2
    query_distance_max: int = 3
    route_count_min: int = 3
    route_count_max: int = 5
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
    label_font_size_px: int = 18
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
class MetroRouteResolvedQuery:
    """Resolved support/style axes for one metro-route graph instance."""

    target_count: int
    route_count: int
    label_variant: str
    node_color_name: str
    query_distance: int = 0
    target_count_probabilities: Dict[str, float] | None = None
    route_count_probabilities: Dict[str, float] | None = None
    label_variant_probabilities: Dict[str, float] | None = None
    node_color_name_probabilities: Dict[str, float] | None = None


@dataclass(frozen=True)
class MetroRouteAnswerAnnotation:
    """Plain answer and annotation values for a metro-route instance."""

    answer_value: int
    annotation_type: str
    annotation_value: list[Any]
    witness_symbolic: Dict[str, Any]
    projected_annotation: Dict[str, Any]


@dataclass(frozen=True)
class MetroRouteInstanceBundle:
    """Prompt, image, trace, and bound values before public output assembly."""

    prompt: str
    image: Any
    answer_value: int
    annotation_type: str
    annotation_value: list[Any]
    trace_payload: Dict[str, Any]
    query_id: str
    prompt_variants: Dict[str, Any]


class MetroRouteInstanceBuilder:
    """Build deterministic metro-route graph instances for public tasks."""

    domain = "graph"
    instance_key = ""
    query_id = ""
    prompt_annotation_key = "annotation_hint"
    prompt_task_key_fallback = ""
    scene_title = "Metro Route Graph"
    _fallback_defaults = MetroRouteTaskDefaults()

    def __init__(
        self,
        *,
        instance_key: str,
        query_id: str,
        prompt_annotation_key: str,
        prompt_task_key_fallback: str,
        domain: str = "graph",
    ) -> None:
        self.domain = str(domain)
        self.instance_key = str(instance_key)
        self.query_id = str(query_id)
        self.prompt_annotation_key = str(prompt_annotation_key)
        self.prompt_task_key_fallback = str(prompt_task_key_fallback)

    def _load_defaults(self) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        group_defaults = get_scene_defaults(self.domain, PUBLIC_METRO_SCENE_ID)
        gen_defaults, render_defaults, prompt_defaults = split_scene_generation_rendering_prompt_defaults(
            group_defaults if isinstance(group_defaults, Mapping) else {},
            task_id=self.instance_key,
        )
        background_defaults = load_graph_scene_background_defaults(scene_id=PUBLIC_METRO_SCENE_ID)
        noise_defaults = load_graph_scene_noise_defaults(scene_id=PUBLIC_METRO_SCENE_ID, apply_prob=0.5)

    def _target_support(self, gen_defaults: Mapping[str, Any], params: Mapping[str, Any], *, query_distance: int = 0) -> Tuple[int, ...]:
        if self.query_id == "metro_shortest_path_length":
            low_key = "target_shortest_path_length_min"
            high_key = "target_shortest_path_length_max"
        else:
            low_key = "target_count_min"
            high_key = "target_count_max"
        low = int(params.get(low_key, group_default(gen_defaults, low_key, self._fallback_defaults.target_count_min)))
        high = int(params.get(high_key, group_default(gen_defaults, high_key, self._fallback_defaults.target_count_max)))
        if int(low) > int(high):
            raise ValueError("empty metro target support")
        route_low = int(params.get("route_count_min", group_default(gen_defaults, "route_count_min", self._fallback_defaults.route_count_min)))
        route_high = int(params.get("route_count_max", group_default(gen_defaults, "route_count_max", self._fallback_defaults.route_count_max)))
        feasible = set(
            feasible_metro_answer_counts(
                query_id=str(self.query_id),
                route_count_min=int(route_low),
                route_count_max=int(route_high),
                query_distance=int(query_distance),
            )
        )
        support = tuple(value for value in range(int(low), int(high) + 1) if int(value) in feasible)
        if not support:
            raise ValueError("no feasible metro target support")
        return tuple(int(value) for value in support)

    def _route_count_support(
        self,
        *,
        gen_defaults: Mapping[str, Any],
        params: Mapping[str, Any],
        target_count: int,
        query_distance: int = 0,
    ) -> Tuple[int, ...]:
        low = int(params.get("route_count_min", group_default(gen_defaults, "route_count_min", self._fallback_defaults.route_count_min)))
        high = int(params.get("route_count_max", group_default(gen_defaults, "route_count_max", self._fallback_defaults.route_count_max)))
        if int(low) > int(high):
            raise ValueError("empty metro route-count support")
        support = tuple(
            route_count
            for route_count in range(int(low), int(high) + 1)
            if int(target_count)
            in set(
                feasible_metro_answer_counts(
                    query_id=str(self.query_id),
                    route_count_min=int(route_count),
                    route_count_max=int(route_count),
                    query_distance=int(query_distance),
                )
            )
        )
        if not support:
            raise ValueError("no feasible metro route-count support for requested transfer count")
        return tuple(int(value) for value in support)

    def _resolve_query(self, instance_seed: int, *, params: Mapping[str, Any], gen_defaults: Mapping[str, Any]) -> MetroRouteResolvedQuery:
        query_distance = 0
        if self.query_id == "metro_exact_distance_count":
            distance_min = int(params.get("query_distance_min", group_default(gen_defaults, "query_distance_min", self._fallback_defaults.query_distance_min)))
            distance_max = int(params.get("query_distance_max", group_default(gen_defaults, "query_distance_max", self._fallback_defaults.query_distance_max)))
            distance_support = tuple(range(int(distance_min), int(distance_max) + 1))
            if not distance_support:
                raise ValueError("empty metro query-distance support")
            explicit_distance = params.get("query_distance")
            if explicit_distance is not None:
                query_distance = int(explicit_distance)
                if int(query_distance) not in distance_support:
                    raise ValueError("requested metro query distance is outside configured support")
            else:
                distance_index = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{self.instance_key}:query_distance_v0"))
                query_distance = int(distance_support[int(distance_index) % len(distance_support)])

        target_support = self._target_support(gen_defaults, params, query_distance=int(query_distance))
        explicit_target = params.get("target_count", params.get("target_transfer_count", params.get("target_shortest_path_length")))
        if explicit_target is not None:
            target_count = int(explicit_target)
            if int(target_count) not in target_support:
                raise ValueError("requested metro target is outside configured support")
        else:
            selection_index = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{self.instance_key}:target_support_v0"))
            target_count = int(target_support[int(selection_index) % len(target_support)])

        route_support = self._route_count_support(
            gen_defaults=gen_defaults,
            params=params,
            target_count=int(target_count),
            query_distance=int(query_distance),
        )
        explicit_route_count = params.get("route_count")
        if explicit_route_count is not None:
            route_count = int(explicit_route_count)
            if int(route_count) not in route_support:
                raise ValueError("requested metro route count is outside feasible support")
        else:
            route_selection_index = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{self.instance_key}:route_count_v0"))
            route_count = int(route_support[int(route_selection_index) % len(route_support)])

        label_rng = spawn_rng(int(instance_seed), f"{self.instance_key}.label_variant")
        label_variant, label_probs = resolve_graph_named_variant(
            label_rng,
            params=params,
            gen_defaults=gen_defaults,
            explicit_key="label_variant",
            weights_key="label_variant_weights",
            balance_flag_key="balanced_label_variant_sampling",
            supported=SUPPORTED_METRO_LABEL_VARIANTS,
            instance_seed=int(instance_seed),
            task_id=self.instance_key,
            namespace="label_variant",
        )
        color_rng = spawn_rng(int(instance_seed), f"{self.instance_key}.node_color_name")
        node_color_name, color_probs = resolve_graph_named_variant(
            color_rng,
            params=params,
            gen_defaults=gen_defaults,
            explicit_key="node_color_name",
            weights_key="node_color_name_weights",
            balance_flag_key="balanced_node_color_name_sampling",
            supported=SUPPORTED_NODE_COLOR_NAMES,
            instance_seed=int(instance_seed),
            task_id=self.instance_key,
            namespace="node_color_name",
        )
        return MetroRouteResolvedQuery(
            target_count=int(target_count),
            route_count=int(route_count),
            label_variant=str(label_variant),
            node_color_name=str(node_color_name),
            query_distance=int(query_distance),
            target_count_probabilities=dict(uniform_probability_map(tuple(target_support), selected=int(target_count) if explicit_target is not None else None)),
            route_count_probabilities=dict(uniform_probability_map(tuple(route_support), selected=int(route_count) if explicit_route_count is not None else None)),
            label_variant_probabilities=dict(label_probs),
            node_color_name_probabilities=dict(color_probs),
        )

    def _sample_network(self, instance_seed: int, query: MetroRouteResolvedQuery) -> MetroRouteNetworkSample:
        rng = spawn_rng(int(instance_seed), f"{self.instance_key}.metro_network")
        return sample_metro_query_network(
            rng,
            query_id=str(self.query_id),
            target_count=int(query.target_count),
            route_count_min=int(query.route_count),
            route_count_max=int(query.route_count),
            label_variant=str(query.label_variant),
            query_distance=int(query.query_distance),
        )

    def _build_prompt_json_examples(self) -> Tuple[str, str]:
        annotation: Any = [[180, 220], [310, 180]]
        answer = 2
        if self.query_id in {"metro_shortest_path_length", "metro_transfer_count"}:
            annotation = [[180, 220], [310, 180], [430, 260]]
        return (
            json.dumps({"annotation": annotation, "answer": answer}, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
            json.dumps({"answer": answer}, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
        )

    def _annotation_and_answer(
        self,
        metro_sample: MetroRouteNetworkSample,
        rendered_scene: RenderedMetroRouteScene,
    ) -> MetroRouteAnswerAnnotation:
        if self.query_id == "metro_shortest_path_length":
            annotation_labels = tuple(str(label) for label in metro_sample.target_labels)
            projection = projected_metro_station_point_annotation(rendered_scene, annotation_labels)
            annotation = [list(point) for point in projection["pixel_point_sequence"]]
            return MetroRouteAnswerAnnotation(
                answer_value=int(metro_sample.target_shortest_path_length),
                annotation_type="point_sequence",
                annotation_value=list(annotation),
                witness_symbolic={"type": "station_label_sequence", "labels": list(annotation_labels)},
                projected_annotation={"type": "point_sequence", **dict(projection)},
            )
        if self.query_id == "metro_transfer_count":
            annotation_labels = tuple(str(label) for label in metro_sample.target_labels)
            projection = projected_metro_station_point_annotation(rendered_scene, annotation_labels)
            annotation = [list(point) for point in projection["pixel_point_sequence"]]
            return MetroRouteAnswerAnnotation(
                answer_value=int(metro_sample.target_route_transfer_count),
                annotation_type="point_sequence",
                annotation_value=list(annotation),
                witness_symbolic={
                    "type": "station_label_sequence",
                    "labels": list(annotation_labels),
                    "route_sequence": list(metro_sample.target_route_sequence),
                    "route_change_station_labels": list(metro_sample.target_path_transfer_labels),
                },
                projected_annotation={"type": "point_sequence", **dict(projection)},
            )
        annotation_labels = tuple(
            str(label)
            for label in (
                metro_sample.transfer_labels
                if self.query_id == "metro_transfer_station_count"
                else metro_sample.target_labels
            )
        )
        projection = projected_metro_station_point_annotation(rendered_scene, annotation_labels)
        annotation = [list(point) for point in projection["pixel_point_set"]]
        if self.query_id == "metro_transfer_station_count":
            answer_value = int(metro_sample.target_transfer_count)
        elif self.query_id == "metro_single_route_station_count":
            answer_value = int(metro_sample.target_single_route_count)
        elif self.query_id == "metro_exact_distance_count":
            answer_value = int(metro_sample.target_exact_distance_count)
        else:
            raise ValueError(f"unsupported metro query_id: {self.query_id}")
        return MetroRouteAnswerAnnotation(
            answer_value=int(answer_value),
            annotation_type="point_set",
            annotation_value=list(annotation),
            witness_symbolic={"type": "station_label_set", "labels": list(annotation_labels)},
            projected_annotation={"type": "point_set", **dict(projection)},
        )


    def _build_trace_payload(
        self,
        *,
        prompt_defaults: Mapping[str, Any],
        prompt_artifacts: Any,
        query: MetroRouteResolvedQuery,
        metro_sample: MetroRouteNetworkSample,
        rendered_scene: RenderedMetroRouteScene,
        render_params: GraphRenderParams,
        background_meta: Mapping[str, Any],
        post_noise_meta: Mapping[str, Any],
        witness_symbolic: Mapping[str, Any],
        projected_annotation: Mapping[str, Any],
    ) -> Dict[str, Any]:
        target_label_set = {
            str(label)
            for label in (
                metro_sample.target_labels
                if metro_sample.target_labels
                else metro_sample.transfer_labels
            )
        }
        station_entities = [
            {
                "entity_id": f"station_{station.label}",
                "entity_kind": "metro_station",
                "label": str(station.label),
                "grid_point": list(station.grid_point),
                "route_ids": list(station.route_ids),
                "route_count": int(len(station.route_ids)),
                "is_transfer": bool(station.is_transfer),
                "is_witness_node": bool(str(station.label) in target_label_set),
                "is_query_node": bool(str(station.label) == str(metro_sample.query_label)),
                "is_source_node": bool(str(station.label) == str(metro_sample.source_label)),
                "is_via_node": bool(str(self.query_id) == "metro_transfer_count" and str(station.label) == str(metro_sample.query_label)),
                "is_goal_node": bool(str(station.label) == str(metro_sample.goal_label)),
                "center_px": list(station.center_xy),
                "bbox_xyxy": list(station.bbox_xyxy),
            }
            for station in rendered_scene.stations
        ]
        route_entities = [
            {
                "entity_id": f"route_{route.route_id}",
                "entity_kind": "metro_route",
                "route_id": str(route.route_id),
                "route_name": str(route.route_name),
                "color_rgb": list(route.color_rgb),
                "station_labels": list(route.station_labels),
                "polyline_px": [list(point) for point in route.polyline_px],
            }
            for route in rendered_scene.routes
        ]
        query_params: Dict[str, Any] = {
            "query_id": str(self.query_id),
            "scene_id": PUBLIC_METRO_SCENE_ID,
            "target_count": int(query.target_count),
            "target_count_probabilities": dict(query.target_count_probabilities or {}),
            "query_distance": int(query.query_distance),
            "route_count": int(query.route_count),
            "route_count_probabilities": dict(query.route_count_probabilities or {}),
            "station_count": int(metro_sample.station_count),
            "route_transfer_count": int(metro_sample.target_route_transfer_count),
            "route_sequence": list(metro_sample.target_route_sequence),
            "route_change_station_labels": list(metro_sample.target_path_transfer_labels),
            "label_variant": str(query.label_variant),
            "label_variant_probabilities": dict(query.label_variant_probabilities or {}),
            "node_color_name": str(query.node_color_name),
            "node_color_name_probabilities": dict(query.node_color_name_probabilities or {}),
        }
        return {
            "scene_ir": {
                "scene_kind": "metro",
                "domain": self.domain,
                "scene_id": PUBLIC_METRO_SCENE_ID,
                "task_id": self.instance_key,
                "query_id": str(self.query_id),
                "entities": [*station_entities, *route_entities],
                "relations": {
                    "graph_directionality": "undirected",
                    "route_semantics": "a transfer station is served by two or more colored routes",
                    "query_id": str(self.query_id),
                    "query_label": str(metro_sample.query_label),
                    "via_label": str(metro_sample.query_label) if str(self.query_id) == "metro_transfer_count" else "",
                    "source_label": str(metro_sample.source_label),
                    "goal_label": str(metro_sample.goal_label),
                    "matching_labels": list(metro_sample.target_labels or metro_sample.transfer_labels),
                    "route_transfer_count": int(metro_sample.target_route_transfer_count),
                    "route_sequence": list(metro_sample.target_route_sequence),
                    "route_change_station_labels": list(metro_sample.target_path_transfer_labels),
                    "transfer_station_labels": list(metro_sample.transfer_labels),
                    "single_route_station_labels": [
                        str(label)
                        for label, route_ids in metro_sample.station_route_ids_by_label.items()
                        if len(route_ids) == 1
                    ],
                    "terminal_station_labels": list(metro_sample.terminal_labels),
                    "route_station_labels": {str(key): list(values) for key, values in metro_sample.route_station_labels.items()},
                    "station_route_ids_by_label": {str(key): list(values) for key, values in metro_sample.station_route_ids_by_label.items()},
                    "adjacency_by_label": {str(key): list(values) for key, values in metro_sample.adjacency_by_label.items()},
                    "edge_labels": [list(edge) for edge in metro_sample.edge_labels],
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(rendered_scene.panel_geometry),
                },
            },
            "query_spec": {
                "query_id": str(self.query_id),
                "scene_id": PUBLIC_METRO_SCENE_ID,
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": query_params,
            },
            "render_spec": {
                "coord_space": "pixel",
                "scene_id": PUBLIC_METRO_SCENE_ID,
                "canvas_size": list(rendered_scene.panel_geometry["canvas_size"]),
                "panel_geometry": dict(rendered_scene.panel_geometry),
                "style": {
                    "theme_tone": str(render_params.theme_tone),
                    "panel_style_variant": str(render_params.panel_style_variant),
                    "background_color_rgb": list(render_params.background_color_rgb),
                    "panel_fill_rgb": list(render_params.panel_fill_rgb),
                    "panel_border_rgb": list(render_params.panel_border_rgb),
                    "title_color_rgb": list(render_params.title_color_rgb),
                    "route_line_width_px": int(rendered_scene.route_line_width_px),
                    "station_radius_px": int(rendered_scene.station_radius_px),
                    "transfer_station_radius_px": int(rendered_scene.transfer_station_radius_px),
                    "label_font_size_px": int(render_params.label_font_size_px),
                    "resolved_label_font_size_px": int(rendered_scene.resolved_label_font_size_px),
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
                "scene_variant": "metro",
                "scene_id": PUBLIC_METRO_SCENE_ID,
                "question_format": str(self.query_id),
                "target_count": int(query.target_count),
                "route_count": int(query.route_count),
                "station_count": int(metro_sample.station_count),
                "query_distance": int(query.query_distance),
                "query_label": str(metro_sample.query_label),
                "via_label": str(metro_sample.query_label) if str(self.query_id) == "metro_transfer_count" else "",
                "source_label": str(metro_sample.source_label),
                "goal_label": str(metro_sample.goal_label),
                "matching_labels": list(metro_sample.target_labels or metro_sample.transfer_labels),
                "route_transfer_count": int(metro_sample.target_route_transfer_count),
                "route_sequence": list(metro_sample.target_route_sequence),
                "route_change_station_labels": list(metro_sample.target_path_transfer_labels),
                "transfer_station_labels": list(metro_sample.transfer_labels),
                "single_route_station_labels": [
                    str(label)
                    for label, route_ids in metro_sample.station_route_ids_by_label.items()
                    if len(route_ids) == 1
                ],
                "terminal_station_labels": list(metro_sample.terminal_labels),
                "target_single_route_count": int(metro_sample.target_single_route_count),
                "target_exact_distance_count": int(metro_sample.target_exact_distance_count),
                "target_shortest_path_length": int(metro_sample.target_shortest_path_length),
                "target_route_transfer_count": int(metro_sample.target_route_transfer_count),
                "route_station_labels": {str(key): list(values) for key, values in metro_sample.route_station_labels.items()},
                "station_route_ids_by_label": {str(key): list(values) for key, values in metro_sample.station_route_ids_by_label.items()},
                "adjacency_by_label": {str(key): list(values) for key, values in metro_sample.adjacency_by_label.items()},
                "edge_labels": [list(edge) for edge in metro_sample.edge_labels],
                "label_variant": str(query.label_variant),
                "node_color_name": str(query.node_color_name),
            },
            "witness_symbolic": dict(witness_symbolic),
            "projected_annotation": dict(projected_annotation),
        }

    def build(self, instance_seed: int, *, params: Dict[str, Any]) -> MetroRouteInstanceBundle:
        """Build one deterministic metro-route graph task instance."""

        for selector_key in ("query_id", "query_variant"):
            requested = params.get(selector_key)
            if requested is not None and str(requested) not in {"", "default", str(self.query_id)}:
                raise ValueError(f"unsupported query_id for {self.instance_key}: {requested}")

        query = self._resolve_query(int(instance_seed), params=params, gen_defaults=gen_defaults)
        render_params = resolve_graph_render_params(
            params,
            instance_seed=int(instance_seed),
            task_id=self.instance_key,
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
        metro_sample = self._sample_network(int(instance_seed), query)
        rendered_scene = render_metro_scene(
            metro_sample=metro_sample,
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
            context=f"prompt defaults for {self.instance_key}",
        )
        prompt_json_example, prompt_json_example_answer_only = self._build_prompt_json_examples()
        question_slots = {
            "query_label": format_graph_prompt_label(str(metro_sample.query_label), label_variant=str(metro_sample.label_variant)),
            "source_label": format_graph_prompt_label(str(metro_sample.source_label), label_variant=str(metro_sample.label_variant)),
            "via_label": format_graph_prompt_label(str(metro_sample.query_label), label_variant=str(metro_sample.label_variant)),
            "goal_label": format_graph_prompt_label(str(metro_sample.goal_label), label_variant=str(metro_sample.label_variant)),
            "query_distance": int(query.query_distance),
        }
        annotation_hint = str(prompt_defaults_required[self.prompt_annotation_key]).format(**question_slots)
        prompt_selection = render_scene_prompt_variants(
            domain=self.domain,
            scene_id=PUBLIC_METRO_SCENE_ID,
            bundle_id=str(prompt_defaults_required["bundle_id"]),
            scene_key=str(prompt_defaults_required["scene_key"]),
            task_key=str(prompt_defaults_required.get("task_key") or self.prompt_task_key_fallback),
            query_key=str(self.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            dynamic_slots={
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
        answer_annotation = self._annotation_and_answer(metro_sample, rendered_scene)
        trace_payload = self._build_trace_payload(
            prompt_defaults=prompt_defaults_required,
            prompt_artifacts=prompt_artifacts,
            query=query,
            metro_sample=metro_sample,
            rendered_scene=rendered_scene,
            render_params=render_params,
            background_meta=background_meta,
            post_noise_meta=post_noise_meta,
            witness_symbolic=answer_annotation.witness_symbolic,
            projected_annotation=answer_annotation.projected_annotation,
        )
        return MetroRouteInstanceBundle(
            prompt=str(prompt_artifacts.prompt),
            image=image,
            answer_value=int(answer_annotation.answer_value),
            annotation_type=str(answer_annotation.annotation_type),
            annotation_value=list(answer_annotation.annotation_value),
            trace_payload=trace_payload,
            query_id=str(self.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


def build_metro_route_instance(
    *,
    instance_key: str,
    query_id: str,
    prompt_annotation_key: str,
    prompt_task_key_fallback: str,
    instance_seed: int,
    params: Dict[str, Any],
    domain: str = "graph",
) -> MetroRouteInstanceBundle:
    """Build one metro-route instance for a public task."""

    builder = MetroRouteInstanceBuilder(
        instance_key=str(instance_key),
        query_id=str(query_id),
        prompt_annotation_key=str(prompt_annotation_key),
        prompt_task_key_fallback=str(prompt_task_key_fallback),
        domain=str(domain),
    )
    return builder.build(int(instance_seed), params=dict(params))


__all__ = [
    "PUBLIC_METRO_SCENE_ID",
    "MetroRouteAnswerAnnotation",
    "MetroRouteInstanceBundle",
    "MetroRouteInstanceBuilder",
    "build_metro_route_instance",
]
