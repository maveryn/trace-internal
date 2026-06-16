"""Count labeled scene cells that follow the same icon-pair attribute edit."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.sampling import normalize_positive_weights, weighted_choice
from ....core.seed import spawn_rng
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    load_scene_generation_rendering_prompt_defaults,
    required_group_defaults,
)
from ...shared.counting_sampling import resolve_counting_target_and_distractor_triplet
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.fixed_query import select_task_query_id
from ...shared.labeling import LABEL_POOL_A_L
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_query_spec,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from ..shared.defaults import ICON_SHARED_DEFAULTS
from ..shared.annotation import matching_scene_cell_point_annotation
from ..shared.icon_assets import resolve_icon_pool
from ..shared.icon_style import sample_icon_palette
from ..shared.icon_task_rendering import sample_icon_instance_noise
from ..shared.icon_transform import IDENTITY_TRANSFORM_ID

from .shared.rendering import panel_geometry_to_trace, render_two_panel_icon_pair_grid_scene
from .shared.state import IconPairSpec
from .shared.styles import pair_grid_style_trace, resolve_pair_grid_render_params


_ATTRIBUTE_RULES: Tuple[str, ...] = (
    "color_only_change",
    "size_only_change",
    "color_and_size_change",
)
_RULE_ATTRIBUTES: Dict[str, Tuple[str, ...]] = {
    "color_only_change": ("color",),
    "size_only_change": ("size",),
    "color_and_size_change": ("color", "size"),
}


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for icon pair attribute-rule counting."""

    object_count_min: int = 4
    object_count_max: int = 9
    target_count_min: int = 0
    target_count_max: int = 4
    distractor_count_min: int = 1
    distractor_count_max: int = 9
    canvas_width: int = 1104
    canvas_height: int = 640
    reference_panel_width_px: int = 296
    panel_gap_px: int = ICON_SHARED_DEFAULTS.panel_gap_px
    outer_margin_px: int = ICON_SHARED_DEFAULTS.outer_margin_px
    panel_padding_px: int = ICON_SHARED_DEFAULTS.panel_padding_px
    panel_corner_radius_px: int = ICON_SHARED_DEFAULTS.panel_corner_radius_px
    scene_icon_size_min_px: int = 40
    scene_icon_size_max_px: int = 88
    reference_icon_size_px: int = 96
    panel_title_font_size_px: int = ICON_SHARED_DEFAULTS.panel_title_font_size_px
    background_color_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.background_color_rgb
    panel_fill_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_fill_rgb
    panel_border_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_border_rgb
    header_text_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.header_text_rgb
    cell_border_rgb: Tuple[int, int, int] = (218, 223, 233)
    cell_label_color_rgb: Tuple[int, int, int] = (52, 60, 77)
    arrow_color_rgb: Tuple[int, int, int] = (84, 96, 118)
    cell_padding_px: int = 10
    pair_arrow_stroke_px: int = 4
    cell_label_font_size_px: int = 22
    pool_manifest: str = "all_icons.txt"
    attribute_rule_weights: Dict[str, float] = field(default_factory=lambda: {rule: 1.0 for rule in _ATTRIBUTE_RULES})
    balanced_attribute_rule_sampling: bool = True
    size_scale_small: float = 0.76
    size_scale_large: float = 1.16
    palette_size_min: int = 5
    palette_size_max: int = 5
    color_channel_min: int = 24
    color_channel_max: int = 220
    min_color_distance: float = 42.0
    color_distance_space: str = "lab"
    icon_noise_edit_types: Tuple[str, ...] = ICON_SHARED_DEFAULTS.icon_noise_edit_types
    icon_noise_edit_count_range: Tuple[int, int] = ICON_SHARED_DEFAULTS.icon_noise_edit_count_range
    icon_noise_value_ranges: Dict[str, Dict[str, Tuple[float, float]]] = field(
        default_factory=lambda: deepcopy(ICON_SHARED_DEFAULTS.icon_noise_value_ranges)
    )


@dataclass(frozen=True)
class _ScenePayload:
    """Trace-ready payload for one attribute-rule pair-grid scene."""

    object_count: int
    target_count: int
    distractor_count: int
    attribute_rule: str
    size_direction: str
    reference_icon_id: str
    cell_labels: Tuple[str, ...]
    matching_labels: Tuple[str, ...]
    cell_icon_ids: Tuple[str, ...]
    cell_attribute_rules: Tuple[str, ...]
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...]
    panel_geometry: Dict[str, Any]
    reference_pair: Dict[str, Any]
    scene_cells: Tuple[Dict[str, Any], ...]


_DEFAULTS = _TaskDefaults()
TASK_ID = "task_icons__pair_grid__attribute_delta_pair_count"
DOMAIN = "icons"
SCENE_ID = "pair_grid"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = ("single",)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_scene_generation_rendering_prompt_defaults(
    DOMAIN,
    SCENE_ID,
    task_id=TASK_ID,
)


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _select_query(instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float], Dict[str, Any]]:
    """Select and validate the single public query contract."""

    return select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=SUPPORTED_QUERY_IDS,
        default_query_id="single",
        task_id=TASK_ID,
        namespace=f"{TASK_ID}.query",
    )


def _resolve_attribute_rule(rng, *, params: Mapping[str, Any], instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the trace-only color/size attribute rule for this instance."""

    supported = tuple(str(rule) for rule in _ATTRIBUTE_RULES)
    explicit = params.get("attribute_rule")
    if explicit is not None:
        selected = str(explicit).strip()
        if selected not in set(supported):
            raise ValueError(f"unsupported attribute_rule: {selected}")
        return selected, {rule: (1.0 if rule == selected else 0.0) for rule in supported}

    raw_weights = params.get(
        "attribute_rule_weights",
        group_default(_GEN_DEFAULTS, "attribute_rule_weights", _DEFAULTS.attribute_rule_weights),
    )
    if not isinstance(raw_weights, Mapping):
        raise ValueError("attribute_rule_weights must be a mapping when provided")
    probabilities = normalize_positive_weights(
        {str(key): float(value) for key, value in raw_weights.items() if str(key) in set(supported)},
        default_keys=supported,
    )
    selected = str(weighted_choice(rng, probabilities, sort_keys=True))
    enabled = bool(
        params.get(
            "balanced_attribute_rule_sampling",
            group_default(_GEN_DEFAULTS, "balanced_attribute_rule_sampling", _DEFAULTS.balanced_attribute_rule_sampling),
        )
    )
    overridden = any(
        key in params and params.get(key) is not None
        for key in (
            "attribute_rule",
            "attribute_rule_weights",
        )
    )
    if bool(enabled) and (not overridden):
        positives = [rule for rule in supported if float(probabilities.get(rule, 0.0)) > 0.0]
        if positives and max(probabilities[rule] for rule in positives) - min(probabilities[rule] for rule in positives) <= 1e-9:
            selection_index = resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace="icons_attribute_rule",
            )
            selected = str(positives[int(selection_index) % len(positives)])
    return selected, {str(key): float(value) for key, value in sorted(probabilities.items())}


def _choose_color_pair(rng, *, palette: Sequence[Tuple[int, int, int]], changes_color: bool) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    left = tuple(int(channel) for channel in rng.choice(tuple(palette)))
    if not bool(changes_color):
        return left, left
    right_options = [tuple(int(channel) for channel in color) for color in palette if tuple(int(channel) for channel in color) != left]
    if not right_options:
        raise ValueError("color-changing attribute rule needs at least two palette colors")
    return left, tuple(int(channel) for channel in rng.choice(right_options))


def _size_scale_pair(
    *,
    changes_size: bool,
    size_direction: str,
    size_scale_small: float,
    size_scale_large: float,
) -> Tuple[float, float]:
    if not bool(changes_size):
        return 1.0, 1.0
    if str(size_direction) == "shrink":
        return float(size_scale_large), float(size_scale_small)
    return float(size_scale_small), float(size_scale_large)


def _make_pair_spec(
    rng,
    *,
    icon_id: str,
    attribute_rule: str,
    palette: Sequence[Tuple[int, int, int]],
    size_direction: str,
    size_scale_small: float,
    size_scale_large: float,
    instance_seed: int,
    namespace: str,
    render_params: Mapping[str, Any],
) -> IconPairSpec:
    """Build one rendered pair whose visual delta exactly matches a rule."""

    changed = set(_RULE_ATTRIBUTES[str(attribute_rule)])
    left_tint, right_tint = _choose_color_pair(rng, palette=palette, changes_color="color" in changed)
    left_scale, right_scale = _size_scale_pair(
        changes_size="size" in changed,
        size_direction=str(size_direction),
        size_scale_small=float(size_scale_small),
        size_scale_large=float(size_scale_large),
    )
    left_noise_edits, left_noise_seed = sample_icon_instance_noise(
        instance_seed=int(instance_seed),
        namespace=f"{namespace}:left",
        render_params=render_params,
    )
    right_noise_edits, right_noise_seed = sample_icon_instance_noise(
        instance_seed=int(instance_seed),
        namespace=f"{namespace}:right",
        render_params=render_params,
    )
    return IconPairSpec(
        icon_id=str(icon_id),
        transform_id=IDENTITY_TRANSFORM_ID,
        tint_rgb=tuple(int(v) for v in left_tint),
        left_tint_rgb=tuple(int(v) for v in left_tint),
        right_tint_rgb=tuple(int(v) for v in right_tint),
        left_size_scale=float(left_scale),
        right_size_scale=float(right_scale),
        left_noise_edits=tuple(left_noise_edits),
        left_noise_seed=int(left_noise_seed),
        right_noise_edits=tuple(right_noise_edits),
        right_noise_seed=int(right_noise_seed),
    )


def _pair_payload(
    rendered_pair: Any,
    *,
    panel: str,
    attribute_rule: str,
    is_match: bool | None = None,
    index: int | None = None,
) -> Dict[str, Any]:
    payload = {
        "panel": str(panel),
        "icon_id": str(rendered_pair.icon_id),
        "transform_id": str(rendered_pair.transform_id),
        "attribute_rule": str(attribute_rule),
        "changed_attributes": list(_RULE_ATTRIBUTES[str(attribute_rule)]),
        "tint_rgb": list(rendered_pair.tint_rgb),
        "left_tint_rgb": list(rendered_pair.left_tint_rgb),
        "right_tint_rgb": list(rendered_pair.right_tint_rgb),
        "left_size_scale": float(rendered_pair.left_size_scale),
        "right_size_scale": float(rendered_pair.right_size_scale),
        "left_bbox_xyxy": list(rendered_pair.left_bbox_xyxy),
        "right_bbox_xyxy": list(rendered_pair.right_bbox_xyxy),
        "left_noise_edits": [dict(edit) for edit in rendered_pair.left_noise_edits],
        "left_noise_seed": None if rendered_pair.left_noise_seed is None else int(rendered_pair.left_noise_seed),
        "right_noise_edits": [dict(edit) for edit in rendered_pair.right_noise_edits],
        "right_noise_seed": None if rendered_pair.right_noise_seed is None else int(rendered_pair.right_noise_seed),
    }
    if hasattr(rendered_pair, "label"):
        payload["label"] = str(rendered_pair.label)
    if hasattr(rendered_pair, "cell_bbox_xyxy"):
        payload["cell_bbox_xyxy"] = list(rendered_pair.cell_bbox_xyxy)
    if is_match is not None:
        payload["is_match"] = bool(is_match)
    if index is not None:
        payload["index"] = int(index)
    return payload


def _sample_scene(
    rng,
    *,
    instance_seed: int,
    attribute_rule: str,
    object_count: int,
    target_count: int,
    pool_manifest: str,
    render_params: Mapping[str, Any],
    size_scale_small: float,
    size_scale_large: float,
) -> Tuple[_ScenePayload, Any]:
    """Sample and render one reference-pair attribute-rule counting scene."""

    pool = list(resolve_icon_pool(str(pool_manifest)))
    if len(pool) < int(object_count) + 1:
        raise ValueError("icon pool is too small for requested attribute-rule scene")
    rng.shuffle(pool)
    reference_icon_id = str(pool[0])
    scene_icon_ids = [str(icon_id) for icon_id in pool[1 : 1 + int(object_count)]]
    labels = tuple(str(value) for value in LABEL_POOL_A_L[: int(object_count)])
    match_indices = set(rng.sample(list(range(int(object_count))), int(target_count)))
    size_direction = str(rng.choice(("grow", "shrink")))

    palette_size_min = max(2, int(render_params["palette_size_min"]))
    palette_size_max = max(palette_size_min, int(render_params["palette_size_max"]))
    palette_size = int(rng.randint(palette_size_min, palette_size_max))
    palette = sample_icon_palette(
        rng,
        palette_size=int(palette_size),
        channel_min=int(render_params["color_channel_min"]),
        channel_max=int(render_params["color_channel_max"]),
        anchor_colors=(
            tuple(int(v) for v in render_params["background_color_rgb"]),
            tuple(int(v) for v in render_params["panel_fill_rgb"]),
            tuple(int(v) for v in render_params["panel_border_rgb"]),
            tuple(int(v) for v in render_params["header_text_rgb"]),
        ),
        min_color_distance=float(render_params["min_color_distance"]),
        distance_space=str(render_params["color_distance_space"]),
    )

    reference_pair = _make_pair_spec(
        rng,
        icon_id=str(reference_icon_id),
        attribute_rule=str(attribute_rule),
        palette=palette,
        size_direction=str(size_direction),
        size_scale_small=float(size_scale_small),
        size_scale_large=float(size_scale_large),
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:reference",
        render_params=render_params,
    )

    alternate_rules = [rule for rule in _ATTRIBUTE_RULES if str(rule) != str(attribute_rule)]
    rng.shuffle(alternate_rules)
    scene_pairs: List[IconPairSpec] = []
    cell_attribute_rules: List[str] = []
    matching_labels: List[str] = []
    distractor_index = 0
    for index, (label, icon_id) in enumerate(zip(labels, scene_icon_ids)):
        if int(index) in match_indices:
            cell_rule = str(attribute_rule)
            matching_labels.append(str(label))
        else:
            cell_rule = str(alternate_rules[int(distractor_index) % len(alternate_rules)])
            distractor_index += 1
        cell_attribute_rules.append(str(cell_rule))
        scene_pairs.append(
            _make_pair_spec(
                rng,
                icon_id=str(icon_id),
                attribute_rule=str(cell_rule),
                palette=palette,
                size_direction=str(size_direction),
                size_scale_small=float(size_scale_small),
                size_scale_large=float(size_scale_large),
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}:scene_{int(index)}",
                render_params=render_params,
            )
        )

    rendered = render_two_panel_icon_pair_grid_scene(
        reference_pair=reference_pair,
        scene_pairs=scene_pairs,
        scene_labels=labels,
        canvas_width=int(render_params["canvas_width"]),
        canvas_height=int(render_params["canvas_height"]),
        reference_panel_width_px=int(render_params["reference_panel_width_px"]),
        outer_margin_px=int(render_params["outer_margin_px"]),
        panel_gap_px=int(render_params["panel_gap_px"]),
        panel_padding_px=int(render_params["panel_padding_px"]),
        panel_corner_radius_px=int(render_params["panel_corner_radius_px"]),
        cell_padding_px=int(render_params["cell_padding_px"]),
        scene_icon_size_min_px=int(render_params["scene_icon_size_min_px"]),
        scene_icon_size_max_px=int(render_params["scene_icon_size_max_px"]),
        reference_icon_size_px=int(render_params["reference_icon_size_px"]),
        pair_arrow_stroke_px=int(render_params["pair_arrow_stroke_px"]),
        cell_label_font_size_px=int(render_params["cell_label_font_size_px"]),
        panel_title_font_size_px=int(render_params["panel_title_font_size_px"]),
        background_rgb=tuple(int(v) for v in render_params["background_color_rgb"]),
        panel_fill_rgb=tuple(int(v) for v in render_params["panel_fill_rgb"]),
        panel_border_rgb=tuple(int(v) for v in render_params["panel_border_rgb"]),
        title_color_rgb=tuple(int(v) for v in render_params["header_text_rgb"]),
        cell_border_rgb=tuple(int(v) for v in render_params["cell_border_rgb"]),
        cell_label_color_rgb=tuple(int(v) for v in render_params["cell_label_color_rgb"]),
        cell_label_stroke_rgb=tuple(int(v) for v in render_params["cell_label_stroke_rgb"]),
        cell_label_stroke_width_px=1,
        arrow_color_rgb=tuple(int(v) for v in render_params["arrow_color_rgb"]),
        icon_canvas_style=render_params.get("_icon_canvas_style_object"),
    )

    reference_payload = _pair_payload(
        rendered.reference_pair,
        panel="reference",
        attribute_rule=str(attribute_rule),
    )
    matching_set = set(str(label) for label in matching_labels)
    scene_cells = tuple(
        {
            **_pair_payload(
                cell,
                panel="scene",
                attribute_rule=str(cell_attribute_rules[index]),
                is_match=bool(str(cell.label) in matching_set),
                index=int(index),
            )
        }
        for index, cell in enumerate(rendered.scene_cells)
    )
    return _ScenePayload(
        object_count=int(object_count),
        target_count=int(target_count),
        distractor_count=int(object_count) - int(target_count),
        attribute_rule=str(attribute_rule),
        size_direction=str(size_direction),
        reference_icon_id=str(reference_icon_id),
        cell_labels=tuple(str(value) for value in labels),
        matching_labels=tuple(sorted(str(value) for value in matching_labels)),
        cell_icon_ids=tuple(str(value) for value in scene_icon_ids),
        cell_attribute_rules=tuple(str(value) for value in cell_attribute_rules),
        sampled_palette_rgb=tuple(tuple(int(channel) for channel in color) for color in palette),
        panel_geometry=panel_geometry_to_trace(rendered.layout),
        reference_pair=reference_payload,
        scene_cells=scene_cells,
    ), rendered.image




@register_task
class IconsPairGridAttributeDeltaPairCountTask:
    """Count scene cells that match the Reference pair's color/size edit rule."""

    task_id = TASK_ID
    domain = DOMAIN
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic icon attribute-rule pair-count instance."""

        query_id, query_probabilities, task_params = _select_query(int(instance_seed), params)
        scene_rng = spawn_rng(int(instance_seed), "scene")
        attribute_rule, attribute_rule_probabilities = _resolve_attribute_rule(
            scene_rng,
            params=task_params,
            instance_seed=int(instance_seed),
        )
        (
            object_count,
            object_count_probabilities,
            target_count,
            target_count_probabilities,
            distractor_count,
            distractor_count_probabilities,
        ) = resolve_counting_target_and_distractor_triplet(
            scene_rng,
            instance_seed=int(instance_seed),
            params=task_params,
            gen_defaults=_GEN_DEFAULTS,
            fallback_total_min=_DEFAULTS.object_count_min,
            fallback_total_max=_DEFAULTS.object_count_max,
            fallback_target_min=_DEFAULTS.target_count_min,
            fallback_target_max=_DEFAULTS.target_count_max,
            fallback_distractor_min=_DEFAULTS.distractor_count_min,
            fallback_distractor_max=_DEFAULTS.distractor_count_max,
        )
        render_params = resolve_pair_grid_render_params(
            params=task_params,
            render_defaults=_RENDER_DEFAULTS,
            fallback_defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        pool_manifest = str(task_params.get("pool_manifest", group_default(_GEN_DEFAULTS, "pool_manifest", _DEFAULTS.pool_manifest)))
        size_scale_small = float(task_params.get("size_scale_small", group_default(_GEN_DEFAULTS, "size_scale_small", _DEFAULTS.size_scale_small)))
        size_scale_large = float(task_params.get("size_scale_large", group_default(_GEN_DEFAULTS, "size_scale_large", _DEFAULTS.size_scale_large)))
        if not (0.25 <= float(size_scale_small) < 1.0 < float(size_scale_large) <= 2.0):
            raise ValueError("size_scale_small/size_scale_large must straddle 1.0")

        scene_payload = None
        image = None
        last_error: Exception | None = None
        for _ in range(max(1, int(max_attempts))):
            try:
                scene_payload, image = _sample_scene(
                    scene_rng,
                    instance_seed=int(instance_seed),
                    attribute_rule=str(attribute_rule),
                    object_count=int(object_count),
                    target_count=int(target_count),
                    pool_manifest=str(pool_manifest),
                    render_params=render_params,
                    size_scale_small=float(size_scale_small),
                    size_scale_large=float(size_scale_large),
                )
                break
            except Exception as exc:
                last_error = exc
                continue
        if scene_payload is None or image is None:
            raise RuntimeError(f"failed to generate {self.task_id} instance") from last_error

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "question_text",
                "annotation_hint",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_selection = render_scene_prompt_variants(
            domain=self.domain,
            scene_id=SCENE_ID,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            dynamic_slots={
                "object_description": str(prompt_defaults["object_description"]),
                "question_text": str(prompt_defaults["question_text"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        annotation_artifacts = matching_scene_cell_point_annotation(
            scene_cells=scene_payload.scene_cells,
            matching_labels=list(scene_payload.matching_labels),
        )
        answer_gt = TypedValue(type="integer", value=int(scene_payload.target_count))
        annotation_gt = TypedValue(
            type=str(annotation_artifacts["annotation_type"]),
            value=list(annotation_artifacts["annotation_value"]),
        )

        query_spec = build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(query_id),
            params={
                "task_id": str(self.task_id),
                "scene_id": SCENE_ID,
                "query_id_probabilities": dict(query_probabilities),
                "attribute_rule": str(attribute_rule),
                "attribute_rule_probabilities": dict(attribute_rule_probabilities),
                "object_count": int(object_count),
                "object_count_probabilities": dict(object_count_probabilities),
                "target_count": int(target_count),
                "target_count_probabilities": dict(target_count_probabilities),
                "distractor_count": int(distractor_count),
                "distractor_count_probabilities": dict(distractor_count_probabilities),
                "pool_manifest": str(pool_manifest),
                "size_scale_small": float(size_scale_small),
                "size_scale_large": float(size_scale_large),
            },
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "icons_reference_pair_attribute_rule_count",
                "task_id": str(self.task_id),
                "scene_id": SCENE_ID,
                "query_id": str(query_id),
                "entities": [dict(scene_payload.reference_pair), *[dict(item) for item in scene_payload.scene_cells]],
                "relations": {
                    "counting_target": "same_color_size_attribute_rule_as_reference",
                    "attribute_rule": str(scene_payload.attribute_rule),
                    "changed_attributes": list(_RULE_ATTRIBUTES[str(scene_payload.attribute_rule)]),
                    "size_direction": str(scene_payload.size_direction),
                    "matching_cell_labels": list(scene_payload.matching_labels),
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(scene_payload.panel_geometry),
                },
            },
            "query_spec": dict(query_spec),
            "render_spec": {
                "task_id": str(self.task_id),
                "scene_id": SCENE_ID,
                "query_id": str(query_id),
                "canvas_size": [int(render_params["canvas_width"]), int(render_params["canvas_height"])],
                "coord_space": "pixel",
                "panel_geometry": dict(scene_payload.panel_geometry),
                "style": pair_grid_style_trace(
                    render_params=render_params,
                    sampled_palette_rgb=scene_payload.sampled_palette_rgb,
                    size_scale_small=float(size_scale_small),
                    size_scale_large=float(size_scale_large),
                ),
            },
            "render_map": {
                "image_id": "img0",
                "anchors": {
                    "reference_pair": dict(scene_payload.reference_pair),
                    "matching_cell_labels": list(scene_payload.matching_labels),
                    "scene_cells": [dict(item) for item in scene_payload.scene_cells],
                },
            },
            "execution_trace": {
                "scene_variant": "reference_pair_grid",
                "task_id": str(self.task_id),
                "scene_id": SCENE_ID,
                "query_id": str(query_id),
                "query_id_probabilities": dict(query_probabilities),
                "attribute_rule": str(scene_payload.attribute_rule),
                "changed_attributes": list(_RULE_ATTRIBUTES[str(scene_payload.attribute_rule)]),
                "attribute_rule_probabilities": dict(attribute_rule_probabilities),
                "size_direction": str(scene_payload.size_direction),
                "object_count": int(object_count),
                "object_count_probabilities": dict(object_count_probabilities),
                "target_count": int(target_count),
                "target_count_probabilities": dict(target_count_probabilities),
                "distractor_count": int(distractor_count),
                "distractor_count_probabilities": dict(distractor_count_probabilities),
                "reference_icon_id": str(scene_payload.reference_icon_id),
                "cell_labels": list(scene_payload.cell_labels),
                "matching_cell_labels": list(scene_payload.matching_labels),
                "cell_icon_ids": list(scene_payload.cell_icon_ids),
                "cell_attribute_rules": list(scene_payload.cell_attribute_rules),
                "question_format": "count_scene_cells_matching_reference_attribute_rule",
            },
            "witness_symbolic": {
                "attribute_rule": str(scene_payload.attribute_rule),
                "changed_attributes": list(_RULE_ATTRIBUTES[str(scene_payload.attribute_rule)]),
                **dict(annotation_artifacts["witness_symbolic"]),
            },
            "projected_annotation": dict(annotation_artifacts["projected_annotation"]),
        }
        output = TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
        return output


__all__ = ["IconsPairGridAttributeDeltaPairCountTask"]
