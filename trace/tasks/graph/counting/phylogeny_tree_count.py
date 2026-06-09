"""Counting tasks over rooted phylogeny cladograms."""

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
from ...shared.config_defaults import group_default, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.variant_sampling import resolve_variant
from ..shared.complexity import build_graph_complexity, normalize_int_with_bounds, resolve_graph_complexity_weights
from ..shared.phylogeny_tree_scene import (
    SUPPORTED_PHYLOGENY_SCENE_VARIANTS,
    descendant_leaf_labels,
    phylogeny_scene_entities,
    projected_leaf_point_annotation,
    render_phylogeny_tree_scene,
    sample_phylogeny_with_clade_size,
)
from ..shared.style import SUPPORTED_NODE_COLOR_NAMES
from ..shared.task_support import resolve_graph_render_params
from ..shared.visual_defaults import load_graph_background_defaults, load_graph_noise_defaults


TASK_ID = "task_graph__phylogeny_tree__clade_leaf_count"
SCENE_ID = "phylogeny_tree"
QUERY_ID = "marked_clade_leaf_count"


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallbacks for phylogeny counting."""

    leaf_count_min: int = 6
    leaf_count_max: int = 12
    target_clade_leaf_count_min: int = 2
    target_clade_leaf_count_max: int = 6
    canvas_width: int = 920
    canvas_height: int = 660
    outer_margin_px: int = 28
    panel_padding_px: int = 24
    panel_corner_radius_px: int = 20
    panel_title_font_size_px: int = 24
    node_shape_variant: str = "circle"
    edge_routing_variant: str = "straight"
    node_radius_min_px: int = 18
    node_radius_max_px: int = 24
    edge_width_px: int = 4
    arrow_length_px: int = 12
    arrow_width_px: int = 7
    node_border_width_px: int = 2
    label_font_size_px: int = 22
    node_color_name: str = "blue"
    background_color_rgb: Tuple[int, int, int] = (247, 248, 251)
    panel_fill_rgb: Tuple[int, int, int] = (255, 255, 255)
    panel_border_rgb: Tuple[int, int, int] = (205, 212, 224)
    title_color_rgb: Tuple[int, int, int] = (70, 78, 96)
    edge_color_rgb: Tuple[int, int, int] = (92, 104, 126)
    node_fill_rgb: Tuple[int, int, int] = (92, 124, 250)
    node_border_rgb: Tuple[int, int, int] = (52, 73, 144)
    label_text_rgb: Tuple[int, int, int] = (20, 26, 36)
    label_stroke_rgb: Tuple[int, int, int] = (255, 255, 255)


@dataclass(frozen=True)
class _ResolvedQuery:
    """Resolved nonsemantic axes and target support."""

    scene_variant: str
    target_clade_leaf_count: int
    scene_variant_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    node_color_name: str
    node_color_name_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("graph", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_graph_background_defaults(task_group="counting")
POST_IMAGE_NOISE_DEFAULTS = load_graph_noise_defaults(task_group="counting", apply_prob=0.5)
_COMPLEXITY_WEIGHTS = resolve_graph_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)


def _int_support(params: Mapping[str, Any], key: str, fallback_min: int, fallback_max: int) -> Tuple[int, ...]:
    low = int(params.get(f"{key}_min", group_default(_GEN_DEFAULTS, f"{key}_min", int(fallback_min))))
    high = int(params.get(f"{key}_max", group_default(_GEN_DEFAULTS, f"{key}_max", int(fallback_max))))
    if int(high) < int(low):
        raise ValueError(f"{key}_min must be <= {key}_max")
    return tuple(range(int(low), int(high) + 1))


def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    scene_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.scene_variant")
    scene_variant, scene_probs = resolve_variant(
        scene_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_PHYLOGENY_SCENE_VARIANTS,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
    )
    color_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.node_color_name")
    node_color_name, color_probs = resolve_variant(
        color_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_NODE_COLOR_NAMES,
        explicit_key="node_color_name",
        weights_key="node_color_name_weights",
    )
    support = _int_support(
        params,
        "target_clade_leaf_count",
        _DEFAULTS.target_clade_leaf_count_min,
        _DEFAULTS.target_clade_leaf_count_max,
    )
    explicit = params.get("target_clade_leaf_count")
    if explicit is not None:
        target = int(explicit)
        if target not in set(support):
            raise ValueError("target_clade_leaf_count outside configured support")
    else:
        target_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.target_clade_leaf_count")
        target = int(target_rng.choice(list(support)))
    return _ResolvedQuery(
        scene_variant=str(scene_variant),
        target_clade_leaf_count=int(target),
        scene_variant_probabilities=dict(scene_probs),
        target_count_probabilities=uniform_probability_map(support, selected=int(target) if explicit is not None else None),
        node_color_name=str(node_color_name),
        node_color_name_probabilities=dict(color_probs),
    )


def _build_prompt_json_examples() -> Tuple[str, str]:
    return (
        json.dumps({"annotation": [[742, 188], [742, 282], [742, 376]], "answer": 3}, separators=(",", ":")),
        json.dumps({"answer": 3}, separators=(",", ":")),
    )


def _build_complexity(*, leaf_count: int, answer: int) -> Any:
    leaf_norm = normalize_int_with_bounds(int(leaf_count), (_DEFAULTS.leaf_count_min, _DEFAULTS.leaf_count_max))
    answer_norm = normalize_int_with_bounds(int(answer), (_DEFAULTS.target_clade_leaf_count_min, _DEFAULTS.target_clade_leaf_count_max))
    return build_graph_complexity(
        weights=_COMPLEXITY_WEIGHTS,
        components={
            "topology_reasoning": (0.60 * answer_norm) + (0.40 * leaf_norm),
            "visual_scan": leaf_norm,
            "ambiguity": 0.42,
            "clutter": leaf_norm,
        },
    )


@register_task
class GraphCountingPhylogenyCladeLeafCountTask:
    """Count descendant taxa in a marked phylogeny clade."""

    task_id = TASK_ID
    domain = "graph"
    task_group = "counting"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query = _resolve_query(int(instance_seed), params=params)
        render_params = resolve_graph_render_params(
            params,
            instance_seed=int(instance_seed),
            task_id=TASK_ID,
            render_defaults=_RENDER_DEFAULTS,
            fallback_defaults=_DEFAULTS,
            node_color_name=str(query.node_color_name),
            node_shape_variant="circle",
            edge_routing_variant="straight",
        )
        image, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        sample, target_node_id = sample_phylogeny_with_clade_size(
            int(instance_seed),
            target_size=int(query.target_clade_leaf_count),
            leaf_count_min=int(group_default(_GEN_DEFAULTS, "leaf_count_min", _DEFAULTS.leaf_count_min)),
            leaf_count_max=int(group_default(_GEN_DEFAULTS, "leaf_count_max", _DEFAULTS.leaf_count_max)),
            max_attempts=max(40, int(max_attempts)),
        )
        rendered_scene = render_phylogeny_tree_scene(
            sample=sample,
            render_params=render_params,
            scene_variant=str(query.scene_variant),
            scene_title="Phylogeny",
            layout_seed=int(instance_seed),
            base_image=image,
            marked_node_id=str(target_node_id),
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        target_leaf_labels = descendant_leaf_labels(sample, str(target_node_id))
        annotation_projection = projected_leaf_point_annotation(rendered_scene, target_leaf_labels)
        annotation_points = [[int(point[0]), int(point[1])] for point in annotation_projection["pixel_point_set"]]
        answer_gt = TypedValue(type="integer", value=int(len(target_leaf_labels)))
        annotation_gt = TypedValue(type="point_set", value=list(annotation_points))

        prompt_defaults = dict(_PROMPT_DEFAULTS)
        json_example, json_example_answer_only = _build_prompt_json_examples()
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=QUERY_ID,
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        target_leaf_set = set(str(label) for label in target_leaf_labels)
        target_entities = []
        for entity in phylogeny_scene_entities(sample, rendered_scene):
            if entity["entity_kind"] == "phylogeny_leaf":
                entity = dict(entity)
                entity["is_counted"] = str(entity["leaf_label"]) in target_leaf_set
            target_entities.append(entity)

        trace_payload = {
            "scene_ir": {
                "task_id": TASK_ID,
                "scene_id": SCENE_ID,
                "scene_kind": "phylogeny_tree",
                "entities": list(target_entities),
                "relations": {
                    "root_id": str(sample.root_id),
                    "leaf_labels": list(sample.leaf_labels),
                    "canonical_signature": [list(item) for item in sample.canonical_signature],
                    "marked_clade_node_id": str(target_node_id),
                    "marked_clade_leaf_labels": list(target_leaf_labels),
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(rendered_scene.panel_geometry),
                },
            },
            "query_spec": {
                "task_id": TASK_ID,
                "query_id": QUERY_ID,
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "scene_variant": str(query.scene_variant),
                    "scene_variant_probabilities": dict(query.scene_variant_probabilities),
                    "target_clade_leaf_count": int(query.target_clade_leaf_count),
                    "target_count_probabilities": dict(query.target_count_probabilities),
                    "leaf_count": int(sample.leaf_count),
                    "node_color_name": str(query.node_color_name),
                    "node_color_name_probabilities": dict(query.node_color_name_probabilities),
                },
            },
            "render_spec": {
                "canvas_size": list(rendered_scene.panel_geometry["canvas_size"]),
                "coord_space": "pixel",
                "panel_geometry": dict(rendered_scene.panel_geometry),
                "style": {
                    "scene_variant": str(query.scene_variant),
                    "theme_tone": str(render_params.theme_tone),
                    "panel_style_variant": str(render_params.panel_style_variant),
                    "background_color_rgb": list(render_params.background_color_rgb),
                    "panel_fill_rgb": list(render_params.panel_fill_rgb),
                    "panel_border_rgb": list(render_params.panel_border_rgb),
                    "title_color_rgb": list(render_params.title_color_rgb),
                    "edge_color_rgb": list(render_params.edge_color_rgb),
                    "edge_width_px": int(render_params.edge_width_px),
                    "label_font_size_px": int(render_params.label_font_size_px),
                    "resolved_label_font_size_px": int(rendered_scene.resolved_label_font_size_px),
                    "label_stroke_width_px": int(rendered_scene.resolved_label_stroke_width_px),
                    "background_meta": dict(background_meta),
                    "post_image_noise_meta": dict(post_noise_meta),
                },
            },
            "render_map": {"image_id": "img0", "anchors": {}},
            "execution_trace": {
                "task_id": TASK_ID,
                "scene_id": SCENE_ID,
                "query_id": QUERY_ID,
                "answer": int(len(target_leaf_labels)),
                "marked_clade_node_id": str(target_node_id),
                "target_leaf_labels": list(target_leaf_labels),
                "leaf_count": int(sample.leaf_count),
            },
            "witness_symbolic": {
                "type": "phylogeny_leaf_label_set",
                "labels": list(target_leaf_labels),
                "marked_clade_node_id": str(target_node_id),
            },
            "projected_annotation": {
                "type": "point_set",
                "point_set": list(annotation_points),
                "pixel_point_set": list(annotation_points),
                "leaf_label_bbox_map": dict(annotation_projection["leaf_label_bbox_map"]),
            },
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_build_complexity(leaf_count=int(sample.leaf_count), answer=int(len(target_leaf_labels))),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=QUERY_ID,
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["GraphCountingPhylogenyCladeLeafCountTask"]
