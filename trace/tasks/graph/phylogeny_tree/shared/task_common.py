"""Relation tasks over rooted phylogeny cladograms."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

from .....core.seed import spawn_rng
from .....core.scene_config import get_scene_defaults
from .....core.visual.background import make_background_canvas
from .....core.visual.noise import apply_post_image_noise
from ....shared.config_defaults import group_default, required_group_defaults, split_scene_generation_rendering_prompt_defaults
from ....shared.deterministic_sampling import uniform_probability_map
from ....shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_scene_prompt_variants
from ....shared.variant_sampling import resolve_variant
from .scene_common import (
    SUPPORTED_PHYLOGENY_SCENE_VARIANTS,
    descendant_leaf_labels,
    phylogeny_scene_entities,
    projected_keyed_phylogeny_annotation,
    render_phylogeny_option_scene,
    render_phylogeny_tree_scene,
    sample_phylogeny_with_cherry,
    sample_phylogeny_with_mrca_size,
    sample_topology_outlier_options,
)
from ...shared.style import SUPPORTED_NODE_COLOR_NAMES
from ...shared.task_support import resolve_graph_render_params
from ...shared.visual_defaults import load_graph_scene_background_defaults, load_graph_scene_noise_defaults


SCENE_ID = "phylogeny_tree"
SISTER_QUERY_ID = "sister_leaf_label"
MRCA_QUERY_ID = "mrca_leaf_count"
TOPOLOGY_QUERY_ID = "topology_outlier_label"


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable relation fallbacks for phylogeny tasks."""

    leaf_count_min: int = 6
    leaf_count_max: int = 12
    target_mrca_leaf_count_min: int = 2
    target_mrca_leaf_count_max: int = 8
    option_leaf_count_min: int = 6
    option_leaf_count_max: int = 8
    option_count: int = 6
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
class _ResolvedStyle:
    """Resolved nonsemantic scene and color axes."""

    scene_variant: str
    scene_variant_probabilities: Dict[str, float]
    node_color_name: str
    node_color_name_probabilities: Dict[str, float]


@dataclass(frozen=True)
class PhylogenyTaskBundle:
    """Trace-ready fields for one public phylogeny task output."""

    prompt: str
    answer_type: str
    answer_value: Any
    annotation_type: str
    annotation_value: Any
    image: Any
    trace_payload: Dict[str, Any]
    query_id: str
    prompt_variants: Dict[str, Any]


_DEFAULTS = _TaskDefaults()
_SCENE_DEFAULTS = get_scene_defaults("graph", SCENE_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_graph_scene_background_defaults(scene_id=SCENE_ID)
POST_IMAGE_NOISE_DEFAULTS = load_graph_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.5)


def _sections_for_task(
    task_identifier: str,
    *,
    annotation_hint_key: str | None = None,
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    gen_defaults, render_defaults, prompt_defaults = split_scene_generation_rendering_prompt_defaults(
        _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
        task_id=str(task_identifier),
    )
    if annotation_hint_key:
        prompt_required = required_group_defaults(
            prompt_defaults,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "object_description",
                "json_output_contract",
                "json_output_contract_answer_only",
                str(annotation_hint_key),
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {task_identifier}",
        )
        prompt_defaults = {
            **dict(prompt_defaults),
            "bundle_id": prompt_required["bundle_id"],
            "scene_key": prompt_required["scene_key"],
            "task_key": prompt_required["task_key"],
            "object_description": prompt_required["object_description"],
            "json_output_contract": prompt_required["json_output_contract"],
            "json_output_contract_answer_only": prompt_required["json_output_contract_answer_only"],
            "annotation_hint": prompt_required[str(annotation_hint_key)],
            "answer_hint": prompt_required["answer_hint"],
            "json_example": prompt_required["json_example"],
            "json_example_answer_only": prompt_required["json_example_answer_only"],
        }
    return gen_defaults, render_defaults, prompt_defaults


def _int_support(
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    key: str,
    fallback_min: int,
    fallback_max: int,
) -> Tuple[int, ...]:
    low = int(params.get(f"{key}_min", group_default(gen_defaults, f"{key}_min", int(fallback_min))))
    high = int(params.get(f"{key}_max", group_default(gen_defaults, f"{key}_max", int(fallback_max))))
    if int(high) < int(low):
        raise ValueError(f"{key}_min must be <= {key}_max")
    return tuple(range(int(low), int(high) + 1))


def _resolve_style(
    instance_seed: int,
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    task_id: str,
) -> _ResolvedStyle:
    scene_rng = spawn_rng(int(instance_seed), f"{task_id}.scene_variant")
    scene_variant, scene_probs = resolve_variant(
        scene_rng,
        params=params,
        gen_defaults=gen_defaults,
        supported_variants=SUPPORTED_PHYLOGENY_SCENE_VARIANTS,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
    )
    color_rng = spawn_rng(int(instance_seed), f"{task_id}.node_color_name")
    node_color_name, color_probs = resolve_variant(
        color_rng,
        params=params,
        gen_defaults=gen_defaults,
        supported_variants=SUPPORTED_NODE_COLOR_NAMES,
        explicit_key="node_color_name",
        weights_key="node_color_name_weights",
    )
    return _ResolvedStyle(
        scene_variant=str(scene_variant),
        scene_variant_probabilities=dict(scene_probs),
        node_color_name=str(node_color_name),
        node_color_name_probabilities=dict(color_probs),
    )


def _leaf_node_id(sample, label: str) -> str:
    for node in sample.nodes:
        if node.leaf_label == str(label):
            return str(node.node_id)
    raise ValueError(f"missing leaf label: {label}")


def _render_single_tree(
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    style: _ResolvedStyle,
    sample,
    marked_node_id: str | None = None,
):
    render_params = resolve_graph_render_params(
        params,
        instance_seed=int(instance_seed),
        task_id=str(task_id),
        render_defaults=render_defaults,
        fallback_defaults=_DEFAULTS,
        node_color_name=str(style.node_color_name),
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
    rendered_scene = render_phylogeny_tree_scene(
        sample=sample,
        render_params=render_params,
        scene_variant=str(style.scene_variant),
        scene_title="Phylogeny",
        layout_seed=int(instance_seed),
        base_image=image,
        marked_node_id=marked_node_id,
    )
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    return image, rendered_scene, render_params, background_meta, post_noise_meta


def _prompt_artifacts(
    *,
    domain: str,
    scene_id: str,
    prompt_defaults: Mapping[str, Any],
    query_id: str,
    slots: Mapping[str, Any],
    instance_seed: int,
):
    prompt_defaults_required = required_group_defaults(
        prompt_defaults,
        ("bundle_id", "scene_key", "task_key"),
        context=f"prompt defaults for {scene_id}:{query_id}",
    )
    prompt_selection = render_scene_prompt_variants(
        domain=str(domain),
        scene_id=str(scene_id),
        bundle_id=str(prompt_defaults_required["bundle_id"]),
        scene_key=str(prompt_defaults_required["scene_key"]),
        task_key=str(prompt_defaults_required["task_key"]),
        query_key=str(query_id),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        slots=dict(slots),
        instance_seed=int(instance_seed),
    )
    return build_prompt_trace_artifacts(prompt_selection)


def _common_single_trace(
    *,
    task_id: str,
    query_id: str,
    prompt_defaults: Mapping[str, Any],
    prompt_artifacts,
    sample,
    rendered_scene,
    render_params,
    style: _ResolvedStyle,
    background_meta: Mapping[str, Any],
    post_noise_meta: Mapping[str, Any],
    query_params: Mapping[str, Any],
    execution_trace: Mapping[str, Any],
    witness_symbolic: Mapping[str, Any],
    projected_annotation: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        "scene_ir": {
            "task_id": str(task_id),
            "scene_id": SCENE_ID,
            "scene_kind": "phylogeny_tree",
            "entities": list(phylogeny_scene_entities(sample, rendered_scene)),
            "relations": {
                "root_id": str(sample.root_id),
                "leaf_labels": list(sample.leaf_labels),
                "canonical_signature": [list(item) for item in sample.canonical_signature],
            },
            "frames": {
                "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                "panels": dict(rendered_scene.panel_geometry),
            },
        },
        "query_spec": {
            "task_id": str(task_id),
            "query_id": str(query_id),
            "template_id": str(prompt_defaults["bundle_id"]),
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": dict(query_params),
        },
        "render_spec": {
            "canvas_size": list(rendered_scene.panel_geometry["canvas_size"]),
            "coord_space": "pixel",
            "panel_geometry": dict(rendered_scene.panel_geometry),
            "style": {
                "scene_variant": str(style.scene_variant),
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
        "execution_trace": dict(execution_trace),
        "witness_symbolic": dict(witness_symbolic),
        "projected_annotation": dict(projected_annotation),
    }


def _json_examples_for_keyed(answer: Any) -> Tuple[str, str]:
    annotation = {
        "target_leaf": [720, 180, 746, 204],
        "sister_leaf": [720, 248, 746, 272],
        "shared_parent": [510, 208, 528, 226],
    }
    return (
        json.dumps({"annotation": annotation, "answer": answer}, separators=(",", ":")),
        json.dumps({"answer": answer}, separators=(",", ":")),
    )




class PhylogenySisterLeafLabelBuilder:
    """Build trace-ready fields for a sister-taxon query."""

    def build(
        self,
        instance_seed: int,
        *,
        task_identifier: str,
        domain: str,
        params: Dict[str, Any],
        max_attempts: int,
    ) -> PhylogenyTaskBundle:
        gen_defaults, render_defaults, prompt_defaults = _sections_for_task(str(task_identifier))
        style = _resolve_style(int(instance_seed), params=params, gen_defaults=gen_defaults, task_id=str(task_identifier))
        sample, (target_leaf, sister_leaf, shared_parent_id) = sample_phylogeny_with_cherry(
            int(instance_seed),
            leaf_count_min=int(group_default(gen_defaults, "leaf_count_min", _DEFAULTS.leaf_count_min)),
            leaf_count_max=int(group_default(gen_defaults, "leaf_count_max", _DEFAULTS.leaf_count_max)),
            max_attempts=max(40, int(max_attempts)),
        )
        image, rendered_scene, render_params, background_meta, post_noise_meta = _render_single_tree(
            task_id=str(task_identifier),
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=gen_defaults,
            render_defaults=render_defaults,
            style=style,
            sample=sample,
        )
        role_to_node_id = {
            "target_leaf": _leaf_node_id(sample, str(target_leaf)),
            "sister_leaf": _leaf_node_id(sample, str(sister_leaf)),
            "shared_parent": str(shared_parent_id),
        }
        annotation_projection = projected_keyed_phylogeny_annotation(rendered_scene, role_to_node_id=role_to_node_id)
        answer_value = str(sister_leaf)
        annotation_value = dict(annotation_projection["keyed_bbox_map"])
        json_example, json_example_answer_only = _json_examples_for_keyed("B")
        prompt_artifacts = _prompt_artifacts(
            domain=str(domain),
            scene_id=SCENE_ID,
            prompt_defaults=prompt_defaults,
            query_id=SISTER_QUERY_ID,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "query_label": str(target_leaf),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        query_params = {
            "scene_variant": str(style.scene_variant),
            "scene_variant_probabilities": dict(style.scene_variant_probabilities),
            "leaf_count": int(sample.leaf_count),
            "node_color_name": str(style.node_color_name),
            "node_color_name_probabilities": dict(style.node_color_name_probabilities),
        }
        execution_trace = {
            "task_id": str(task_identifier),
            "scene_id": SCENE_ID,
            "query_id": SISTER_QUERY_ID,
            "query_leaf_label": str(target_leaf),
            "answer": str(sister_leaf),
            "sister_leaf_label": str(sister_leaf),
            "shared_parent_id": str(shared_parent_id),
            "annotation_role_to_node_id": dict(role_to_node_id),
        }
        trace_payload = _common_single_trace(
            task_id=str(task_identifier),
            query_id=SISTER_QUERY_ID,
            prompt_defaults=prompt_defaults,
            prompt_artifacts=prompt_artifacts,
            sample=sample,
            rendered_scene=rendered_scene,
            render_params=render_params,
            style=style,
            background_meta=background_meta,
            post_noise_meta=post_noise_meta,
            query_params=query_params,
            execution_trace=execution_trace,
            witness_symbolic={
                "type": "phylogeny_sister_leaf",
                "query_leaf_label": str(target_leaf),
                "sister_leaf_label": str(sister_leaf),
                "shared_parent_id": str(shared_parent_id),
            },
            projected_annotation={"type": "keyed_bbox_map", **dict(annotation_projection)},
        )
        return PhylogenyTaskBundle(
            prompt=str(prompt_artifacts.prompt),
            answer_type="string",
            answer_value=answer_value,
            annotation_type="keyed_bbox_map",
            annotation_value=annotation_value,
            image=image,
            trace_payload=trace_payload,
            query_id=SISTER_QUERY_ID,
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


class PhylogenyMrcaCladeMembershipCountBuilder:
    """Build trace-ready fields for an MRCA clade-size query."""

    def build(
        self,
        instance_seed: int,
        *,
        task_identifier: str,
        domain: str,
        params: Dict[str, Any],
        max_attempts: int,
    ) -> PhylogenyTaskBundle:
        gen_defaults, render_defaults, prompt_defaults = _sections_for_task(str(task_identifier))
        style = _resolve_style(int(instance_seed), params=params, gen_defaults=gen_defaults, task_id=str(task_identifier))
        answer_support = _int_support(
            params,
            gen_defaults,
            "target_mrca_leaf_count",
            _DEFAULTS.target_mrca_leaf_count_min,
            _DEFAULTS.target_mrca_leaf_count_max,
        )
        explicit = params.get("target_mrca_leaf_count")
        if explicit is not None:
            target_count = int(explicit)
            if target_count not in set(answer_support):
                raise ValueError("target_mrca_leaf_count outside configured support")
        else:
            target_count = int(spawn_rng(int(instance_seed), f"{task_identifier}.target_mrca_leaf_count").choice(list(answer_support)))
        sample, mrca_id, leaf_pair = sample_phylogeny_with_mrca_size(
            int(instance_seed),
            target_size=int(target_count),
            leaf_count_min=int(group_default(gen_defaults, "leaf_count_min", _DEFAULTS.leaf_count_min)),
            leaf_count_max=int(group_default(gen_defaults, "leaf_count_max", _DEFAULTS.leaf_count_max)),
            max_attempts=max(60, int(max_attempts)),
        )
        image, rendered_scene, render_params, background_meta, post_noise_meta = _render_single_tree(
            task_id=str(task_identifier),
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=gen_defaults,
            render_defaults=render_defaults,
            style=style,
            sample=sample,
            marked_node_id=str(mrca_id),
        )
        role_to_node_id = {
            "query_leaf_1": _leaf_node_id(sample, str(leaf_pair[0])),
            "query_leaf_2": _leaf_node_id(sample, str(leaf_pair[1])),
            "mrca": str(mrca_id),
        }
        annotation_projection = projected_keyed_phylogeny_annotation(rendered_scene, role_to_node_id=role_to_node_id)
        mrca_leaf_labels = descendant_leaf_labels(sample, str(mrca_id))
        answer_value = int(len(mrca_leaf_labels))
        annotation_value = dict(annotation_projection["keyed_bbox_map"])
        example_annotation = {
            "query_leaf_1": [720, 180, 746, 204],
            "query_leaf_2": [720, 360, 746, 384],
            "mrca": [440, 250, 458, 268],
        }
        json_example = json.dumps({"annotation": example_annotation, "answer": 4}, separators=(",", ":"))
        json_example_answer_only = json.dumps({"answer": 4}, separators=(",", ":"))
        prompt_artifacts = _prompt_artifacts(
            domain=str(domain),
            scene_id=SCENE_ID,
            prompt_defaults=prompt_defaults,
            query_id=MRCA_QUERY_ID,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "query_label_a": str(leaf_pair[0]),
                "query_label_b": str(leaf_pair[1]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        query_params = {
            "scene_variant": str(style.scene_variant),
            "scene_variant_probabilities": dict(style.scene_variant_probabilities),
            "target_mrca_leaf_count": int(target_count),
            "target_count_probabilities": uniform_probability_map(answer_support, selected=int(target_count) if explicit is not None else None),
            "leaf_count": int(sample.leaf_count),
            "node_color_name": str(style.node_color_name),
            "node_color_name_probabilities": dict(style.node_color_name_probabilities),
        }
        execution_trace = {
            "task_id": str(task_identifier),
            "scene_id": SCENE_ID,
            "query_id": MRCA_QUERY_ID,
            "query_leaf_labels": [str(leaf_pair[0]), str(leaf_pair[1])],
            "answer": int(len(mrca_leaf_labels)),
            "mrca_node_id": str(mrca_id),
            "mrca_descendant_leaf_labels": list(mrca_leaf_labels),
            "annotation_role_to_node_id": dict(role_to_node_id),
        }
        trace_payload = _common_single_trace(
            task_id=str(task_identifier),
            query_id=MRCA_QUERY_ID,
            prompt_defaults=prompt_defaults,
            prompt_artifacts=prompt_artifacts,
            sample=sample,
            rendered_scene=rendered_scene,
            render_params=render_params,
            style=style,
            background_meta=background_meta,
            post_noise_meta=post_noise_meta,
            query_params=query_params,
            execution_trace=execution_trace,
            witness_symbolic={
                "type": "phylogeny_mrca_leaf_count",
                "query_leaf_labels": [str(leaf_pair[0]), str(leaf_pair[1])],
                "mrca_node_id": str(mrca_id),
                "mrca_descendant_leaf_labels": list(mrca_leaf_labels),
            },
            projected_annotation={"type": "keyed_bbox_map", **dict(annotation_projection)},
        )
        return PhylogenyTaskBundle(
            prompt=str(prompt_artifacts.prompt),
            answer_type="integer",
            answer_value=answer_value,
            annotation_type="keyed_bbox_map",
            annotation_value=annotation_value,
            image=image,
            trace_payload=trace_payload,
            query_id=MRCA_QUERY_ID,
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


class PhylogenyTopologyOutlierLabelBuilder:
    """Build trace-ready fields for a topology-outlier option query."""

    def build(
        self,
        instance_seed: int,
        *,
        task_identifier: str,
        domain: str,
        params: Dict[str, Any],
        max_attempts: int,
    ) -> PhylogenyTaskBundle:
        gen_defaults, render_defaults, prompt_defaults = _sections_for_task(str(task_identifier))
        style = _resolve_style(int(instance_seed), params=params, gen_defaults=gen_defaults, task_id=str(task_identifier))
        option_dataset = sample_topology_outlier_options(
            int(instance_seed),
            leaf_count_min=int(group_default(gen_defaults, "option_leaf_count_min", _DEFAULTS.option_leaf_count_min)),
            leaf_count_max=int(group_default(gen_defaults, "option_leaf_count_max", _DEFAULTS.option_leaf_count_max)),
            option_count=int(group_default(gen_defaults, "option_count", _DEFAULTS.option_count)),
            max_attempts=max(100, int(max_attempts)),
        )
        render_params = resolve_graph_render_params(
            params,
            instance_seed=int(instance_seed),
            task_id=str(task_identifier),
            render_defaults=render_defaults,
            fallback_defaults=_DEFAULTS,
            node_color_name=str(style.node_color_name),
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
        rendered_scene = render_phylogeny_option_scene(
            option_specs=option_dataset["option_specs"],
            render_params=render_params,
            scene_variant=str(style.scene_variant),
            layout_seed=int(instance_seed),
            base_image=image,
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        answer_label = str(option_dataset["answer_option_label"])
        selected_bbox = [round(float(value), 3) for value in rendered_scene.option_panel_bboxes[answer_label]]
        answer_value = str(answer_label)
        annotation_value = [list(selected_bbox)]
        json_example = json.dumps({"annotation": [[472, 520, 828, 742]], "answer": "D"}, separators=(",", ":"))
        json_example_answer_only = json.dumps({"answer": "D"}, separators=(",", ":"))
        prompt_artifacts = _prompt_artifacts(
            domain=str(domain),
            scene_id=SCENE_ID,
            prompt_defaults=prompt_defaults,
            query_id=TOPOLOGY_QUERY_ID,
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
        option_records = []
        for spec in option_dataset["option_specs"]:
            option_records.append(
                {
                    "option_label": str(spec["option_label"]),
                    "role": str(spec["role"]),
                    "canonical_signature": [list(item) for item in spec["canonical_signature"]],
                    "panel_bbox_xyxy": list(rendered_scene.option_panel_bboxes[str(spec["option_label"])]),
                }
            )
        trace_payload = {
            "scene_ir": {
                "task_id": str(task_identifier),
                "scene_id": SCENE_ID,
                "scene_kind": "phylogeny_topology_options",
                "entities": [
                    {
                        "entity_id": f"option_{record['option_label']}",
                        "entity_kind": "phylogeny_option_panel",
                        **record,
                    }
                    for record in option_records
                ],
                "relations": {
                    "option_count": 6,
                    "leaf_count": int(option_dataset["leaf_count"]),
                    "leaf_labels": list(option_dataset["base_sample"].leaf_labels),
                    "base_canonical_signature": [list(item) for item in option_dataset["base_sample"].canonical_signature],
                    "outlier_canonical_signature": [list(item) for item in option_dataset["outlier_sample"].canonical_signature],
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(rendered_scene.panel_geometry),
                },
            },
            "query_spec": {
                "task_id": str(task_identifier),
                "query_id": TOPOLOGY_QUERY_ID,
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "scene_variant": str(style.scene_variant),
                    "scene_variant_probabilities": dict(style.scene_variant_probabilities),
                    "option_count": 6,
                    "answer_option_label": str(answer_label),
                    "leaf_count": int(option_dataset["leaf_count"]),
                    "node_color_name": str(style.node_color_name),
                    "node_color_name_probabilities": dict(style.node_color_name_probabilities),
                },
            },
            "render_spec": {
                "canvas_size": list(rendered_scene.panel_geometry["canvas_size"]),
                "coord_space": "pixel",
                "panel_geometry": dict(rendered_scene.panel_geometry),
                "style": {
                    "scene_variant": str(style.scene_variant),
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
                "task_id": str(task_identifier),
                "scene_id": SCENE_ID,
                "query_id": TOPOLOGY_QUERY_ID,
                "answer": str(answer_label),
                "answer_option_label": str(answer_label),
                "correct_option_index": int(option_dataset["correct_option_index"]),
                "option_records": list(option_records),
            },
            "witness_symbolic": {
                "type": "phylogeny_topology_outlier_option",
                "answer_option_label": str(answer_label),
                "rule": "same rooted clades, child order and layout ignored",
            },
            "projected_annotation": {
                "type": "bbox_set",
                "bbox_set": [list(selected_bbox)],
                "pixel_bbox_set": [list(selected_bbox)],
            },
        }
        return PhylogenyTaskBundle(
            prompt=str(prompt_artifacts.prompt),
            answer_type="string",
            answer_value=answer_value,
            annotation_type="bbox_set",
            annotation_value=annotation_value,
            image=image,
            trace_payload=trace_payload,
            query_id=TOPOLOGY_QUERY_ID,
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = [
    "MRCA_QUERY_ID",
    "PhylogenyMrcaCladeMembershipCountBuilder",
    "PhylogenySisterLeafLabelBuilder",
    "PhylogenyTaskBundle",
    "PhylogenyTopologyOutlierLabelBuilder",
    "SCENE_ID",
    "SISTER_QUERY_ID",
    "TOPOLOGY_QUERY_ID",
]
