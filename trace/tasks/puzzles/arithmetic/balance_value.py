"""Puzzle arithmetic task that solves an explicit query row from equality panels."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.arithmetic_common import (
    projected_puzzle_bbox_evidence,
    resolve_arithmetic_answer_bounds,
    resolve_puzzle_axis_variant,
)
from ..shared.balance_scene import (
    PuzzleBalanceRenderParams,
    SUPPORTED_PUZZLE_BALANCE_SCENE_VARIANTS,
    render_puzzle_balance_scene,
)
from ..shared.complexity import build_puzzle_complexity, normalize_int_with_bounds, resolve_puzzle_complexity_weights
from ..shared.visual_defaults import load_puzzle_background_defaults, load_puzzle_noise_defaults


TASK_ID = "task_puzzles_arithmetic_balance_value"
_SUPPORTED_TASK_VARIANTS: Tuple[str, ...] = (
    "sum_pair_unknown",
    "two_panel_chain_unknown",
    "three_panel_chain_unknown",
)
_REASONING_LOAD_BASE_BY_VARIANT = {
    "sum_pair_unknown": 0.32,
    "two_panel_chain_unknown": 0.46,
    "three_panel_chain_unknown": 0.62,
}
_SCENE_LOAD_BY_VARIANT = {
    "balance_strip": 0.16,
    "balance_card": 0.24,
    "balance_outline": 0.2,
}
_OBJECT_TYPES: Tuple[str, ...] = ("circle", "triangle", "diamond", "square", "hexagon", "star")


@dataclass(frozen=True)
class PuzzleBalanceDefaults:
    """Stable fallback defaults for the first arithmetic equality-panel puzzle task."""

    answer_min: int = 1
    answer_max: int = 24
    object_value_min: int = 1
    object_value_max: int = 12
    max_visible_value: int = 32
    canvas_width: int = 1024
    canvas_height: int = 720
    scene_margin_left_px: int = 72
    scene_margin_right_px: int = 72
    scene_margin_top_px: int = 64
    scene_margin_bottom_px: int = 64
    item_box_width_px: int = 96
    item_box_height_px: int = 96
    item_gap_px: int = 56
    scale_side_gap_px: int = 14
    relation_gap_jitter_min_px: int = -2
    relation_gap_jitter_max_px: int = 2
    panel_gap_px: int = 54
    query_gap_px: int = 44
    query_box_width_px: int = 112
    query_box_height_px: int = 112
    scale_width_px: int = 96
    scale_height_px: int = 88
    slot_corner_radius_px: int = 18
    border_width_px: int = 3
    panel_padding_px: int = 28
    panel_corner_radius_px: int = 28
    value_font_size_px: int = 44


_DEFAULTS = PuzzleBalanceDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "arithmetic")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_puzzle_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_puzzle_background_defaults(task_group="arithmetic")
POST_IMAGE_NOISE_DEFAULTS = load_puzzle_noise_defaults(task_group="arithmetic", apply_prob=0.0)


def _resolve_task_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the semantic balance-puzzle variant."""

    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_TASK_VARIANTS,
        task_id=TASK_ID,
        explicit_key="task_variant",
        weights_key="task_variant_weights",
        balance_flag_key="balanced_task_variant_sampling",
        axis_namespace="task_variant",
    )


def _resolve_scene_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the visual balance-puzzle scene variant."""

    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_PUZZLE_BALANCE_SCENE_VARIANTS,
        task_id=TASK_ID,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def _resolve_balance_render_params(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
    defaults: PuzzleBalanceDefaults,
) -> PuzzleBalanceRenderParams:
    """Resolve one reusable balance-scene render-parameter record."""

    def _triple(key: str, fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
        raw = params.get(str(key), group_default(render_defaults, str(key), list(fallback)))
        if not isinstance(raw, Sequence) or len(raw) != 3:
            raise ValueError(f"{key} must be a length-3 RGB sequence")
        return tuple(int(value) for value in raw)

    return PuzzleBalanceRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(render_defaults, "canvas_width", int(defaults.canvas_width)))),
        canvas_height=int(params.get("canvas_height", group_default(render_defaults, "canvas_height", int(defaults.canvas_height)))),
        scene_margin_left_px=int(params.get("scene_margin_left_px", group_default(render_defaults, "scene_margin_left_px", int(defaults.scene_margin_left_px)))),
        scene_margin_right_px=int(params.get("scene_margin_right_px", group_default(render_defaults, "scene_margin_right_px", int(defaults.scene_margin_right_px)))),
        scene_margin_top_px=int(params.get("scene_margin_top_px", group_default(render_defaults, "scene_margin_top_px", int(defaults.scene_margin_top_px)))),
        scene_margin_bottom_px=int(params.get("scene_margin_bottom_px", group_default(render_defaults, "scene_margin_bottom_px", int(defaults.scene_margin_bottom_px)))),
        item_box_width_px=int(params.get("item_box_width_px", group_default(render_defaults, "item_box_width_px", int(defaults.item_box_width_px)))),
        item_box_height_px=int(params.get("item_box_height_px", group_default(render_defaults, "item_box_height_px", int(defaults.item_box_height_px)))),
        item_gap_px=int(params.get("item_gap_px", group_default(render_defaults, "item_gap_px", int(defaults.item_gap_px)))),
        scale_side_gap_px=int(params.get("scale_side_gap_px", group_default(render_defaults, "scale_side_gap_px", int(defaults.scale_side_gap_px)))),
        relation_gap_jitter_min_px=int(params.get("relation_gap_jitter_min_px", group_default(render_defaults, "relation_gap_jitter_min_px", int(defaults.relation_gap_jitter_min_px)))),
        relation_gap_jitter_max_px=int(params.get("relation_gap_jitter_max_px", group_default(render_defaults, "relation_gap_jitter_max_px", int(defaults.relation_gap_jitter_max_px)))),
        panel_gap_px=int(params.get("panel_gap_px", group_default(render_defaults, "panel_gap_px", int(defaults.panel_gap_px)))),
        query_gap_px=int(params.get("query_gap_px", group_default(render_defaults, "query_gap_px", int(defaults.query_gap_px)))),
        query_box_width_px=int(params.get("query_box_width_px", group_default(render_defaults, "query_box_width_px", int(defaults.query_box_width_px)))),
        query_box_height_px=int(params.get("query_box_height_px", group_default(render_defaults, "query_box_height_px", int(defaults.query_box_height_px)))),
        scale_width_px=int(params.get("scale_width_px", group_default(render_defaults, "scale_width_px", int(defaults.scale_width_px)))),
        scale_height_px=int(params.get("scale_height_px", group_default(render_defaults, "scale_height_px", int(defaults.scale_height_px)))),
        slot_corner_radius_px=int(params.get("slot_corner_radius_px", group_default(render_defaults, "slot_corner_radius_px", int(defaults.slot_corner_radius_px)))),
        border_width_px=int(params.get("border_width_px", group_default(render_defaults, "border_width_px", int(defaults.border_width_px)))),
        panel_padding_px=int(params.get("panel_padding_px", group_default(render_defaults, "panel_padding_px", int(defaults.panel_padding_px)))),
        panel_corner_radius_px=int(params.get("panel_corner_radius_px", group_default(render_defaults, "panel_corner_radius_px", int(defaults.panel_corner_radius_px)))),
        value_font_size_px=int(params.get("value_font_size_px", group_default(render_defaults, "value_font_size_px", int(defaults.value_font_size_px)))),
        panel_fill_rgb=_triple("panel_fill_rgb", (248, 249, 252)),
        box_fill_rgb=_triple("box_fill_rgb", (252, 252, 255)),
        query_box_fill_rgb=_triple("query_box_fill_rgb", (243, 247, 255)),
        border_color_rgb=_triple("border_color_rgb", (86, 94, 108)),
        text_color_rgb=_triple("text_color_rgb", (30, 34, 40)),
        text_stroke_rgb=_triple("text_stroke_rgb", (255, 255, 255)),
        accent_color_rgb=_triple("accent_color_rgb", (54, 102, 180)),
    )


def _number_item(*, box_id: str, value: int) -> Dict[str, Any]:
    """Build one numeric witness box for a balance panel."""

    return {
        "box_id": str(box_id),
        "kind": "number",
        "text": str(int(value)),
        "value": int(value),
    }


def _object_item(*, box_id: str, object_type: str) -> Dict[str, Any]:
    """Build one symbolic object box for a balance panel."""

    return {
        "box_id": str(box_id),
        "kind": "object",
        "object_type": str(object_type),
        "value": None,
    }


def _sample_object_types(count: int, *, rng) -> Sequence[str]:
    """Sample distinct symbolic object types deterministically for one instance."""

    object_types = list(_OBJECT_TYPES)
    rng.shuffle(object_types)
    return [str(object_type) for object_type in object_types[: int(count)]]


def _build_balance_dataset(
    *,
    task_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: PuzzleBalanceDefaults,
    task_id: str,
) -> Dict[str, Any]:
    """Construct one deterministic balance-puzzle dataset with an explicit query row."""

    selected_variant = str(task_variant)
    if selected_variant not in set(_SUPPORTED_TASK_VARIANTS):
        raise ValueError(f"unsupported equality-panel puzzle variant: {task_variant}")

    rng = spawn_rng(int(instance_seed), f"{task_id}.dataset")
    answer_min, answer_max = resolve_arithmetic_answer_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    object_value_min = int(params.get("object_value_min", group_default(gen_defaults, "object_value_min", int(defaults.object_value_min))))
    object_value_max = int(params.get("object_value_max", group_default(gen_defaults, "object_value_max", int(defaults.object_value_max))))
    max_visible_value = int(params.get("max_visible_value", group_default(gen_defaults, "max_visible_value", int(defaults.max_visible_value))))

    panel_specs: list[Dict[str, Any]] | None = None
    object_values: Dict[str, int] | None = None
    query_object_type: str | None = None
    answer_value: int | None = None

    for _ in range(512):
        if selected_variant == "sum_pair_unknown":
            object_a, object_b = _sample_object_types(2, rng=rng)
            value_a = int(rng.randint(int(object_value_min), min(int(object_value_max), int(answer_max))))
            value_b = int(rng.randint(int(object_value_min), min(int(object_value_max), int(answer_max))))
            sum_total = int(value_a + value_b)
            double_a = int(2 * value_a)
            if int(sum_total) > int(max_visible_value) or int(double_a) > int(max_visible_value):
                continue
            query_object_type = str(object_a if int(rng.randint(0, 1)) == 0 else object_b)
            answer_value = int(value_a if query_object_type == object_a else value_b)
            object_values = {str(object_a): int(value_a), str(object_b): int(value_b)}
            panel_specs = [
                {
                    "panel_id": "panel_0",
                    "left_items": [
                        _object_item(box_id="panel_0_left_0", object_type=object_a),
                        _object_item(box_id="panel_0_left_1", object_type=object_b),
                    ],
                    "right_items": [
                        _number_item(box_id="panel_0_right_0", value=sum_total),
                    ],
                },
                {
                    "panel_id": "panel_1",
                    "left_items": [
                        _object_item(box_id="panel_1_left_0", object_type=object_a),
                        _object_item(box_id="panel_1_left_1", object_type=object_a),
                    ],
                    "right_items": [
                        _number_item(box_id="panel_1_right_0", value=double_a),
                    ],
                },
            ]
        elif selected_variant == "two_panel_chain_unknown":
            object_a, object_b = _sample_object_types(2, rng=rng)
            max_a = min(int(object_value_max), int(answer_max // 2), max(1, int(max_visible_value // 3)))
            if int(max_a) < int(object_value_min):
                continue
            value_a = int(rng.randint(int(object_value_min), int(max_a)))
            value_b = int(2 * value_a)
            total_value = int(value_b + value_a)
            if int(value_b) > int(answer_max) or int(total_value) > int(max_visible_value):
                continue
            query_object_type = str(object_a if int(rng.randint(0, 1)) == 0 else object_b)
            answer_value = int(value_a if query_object_type == object_a else value_b)
            object_values = {str(object_a): int(value_a), str(object_b): int(value_b)}
            panel_specs = [
                {
                    "panel_id": "panel_0",
                    "left_items": [
                        _object_item(box_id="panel_0_left_0", object_type=object_a),
                        _object_item(box_id="panel_0_left_1", object_type=object_a),
                    ],
                    "right_items": [
                        _object_item(box_id="panel_0_right_0", object_type=object_b),
                    ],
                },
                {
                    "panel_id": "panel_1",
                    "left_items": [
                        _object_item(box_id="panel_1_left_0", object_type=object_b),
                        _object_item(box_id="panel_1_left_1", object_type=object_a),
                    ],
                    "right_items": [
                        _number_item(box_id="panel_1_right_0", value=total_value),
                    ],
                },
            ]
        else:
            object_a, object_b, object_c = _sample_object_types(3, rng=rng)
            max_a = min(int(object_value_max), int(answer_max // 2), max(1, int(max_visible_value // 3)))
            max_c = min(int(object_value_max), int(answer_max), max(1, int(max_visible_value // 2)))
            if int(max_a) < int(object_value_min) or int(max_c) < int(object_value_min):
                continue
            value_a = int(rng.randint(int(object_value_min), int(max_a)))
            value_c = int(rng.randint(int(object_value_min), int(max_c)))
            value_b = int(2 * value_a)
            total_c = int(2 * value_c)
            total_mix = int(value_b + value_c)
            if int(value_b) > int(answer_max):
                continue
            if max(int(total_c), int(total_mix)) > int(max_visible_value):
                continue
            query_index = int(rng.randint(0, 2))
            query_object_type = [str(object_a), str(object_b), str(object_c)][int(query_index)]
            answer_value = {
                str(object_a): int(value_a),
                str(object_b): int(value_b),
                str(object_c): int(value_c),
            }[str(query_object_type)]
            object_values = {
                str(object_a): int(value_a),
                str(object_b): int(value_b),
                str(object_c): int(value_c),
            }
            panel_specs = [
                {
                    "panel_id": "panel_0",
                    "left_items": [
                        _object_item(box_id="panel_0_left_0", object_type=object_a),
                        _object_item(box_id="panel_0_left_1", object_type=object_a),
                    ],
                    "right_items": [
                        _object_item(box_id="panel_0_right_0", object_type=object_b),
                    ],
                },
                {
                    "panel_id": "panel_1",
                    "left_items": [
                        _object_item(box_id="panel_1_left_0", object_type=object_c),
                        _object_item(box_id="panel_1_left_1", object_type=object_c),
                    ],
                    "right_items": [
                        _number_item(box_id="panel_1_right_0", value=total_c),
                    ],
                },
                {
                    "panel_id": "panel_2",
                    "left_items": [
                        _object_item(box_id="panel_2_left_0", object_type=object_b),
                        _object_item(box_id="panel_2_left_1", object_type=object_c),
                    ],
                    "right_items": [
                        _number_item(box_id="panel_2_right_0", value=total_mix),
                    ],
                },
            ]

        if int(answer_value) < int(answer_min) or int(answer_value) > int(answer_max):
            continue
        break

    if panel_specs is None or object_values is None or query_object_type is None or answer_value is None:
        raise ValueError(f"{task_id} could not construct a valid equality puzzle for variant={selected_variant}")

    total_box_count = int(sum(len(panel["left_items"]) + len(panel["right_items"]) for panel in panel_specs) + 2)
    query_box_id = "query_answer_box"
    query_object_box_id = "query_object_box"
    return {
        "task_variant": str(selected_variant),
        "panel_specs": list(panel_specs),
        "query_spec": {
            "query_object_box_id": str(query_object_box_id),
            "query_box_id": str(query_box_id),
            "object_type": str(query_object_type),
        },
        "answer_value": int(answer_value),
        "query_box_id": str(query_box_id),
        "query_object_box_id": str(query_object_box_id),
        "query_object_type": str(query_object_type),
        "panel_count": int(len(panel_specs)),
        "panel_count_range": [2, 3],
        "total_box_count": int(total_box_count),
        "total_box_count_range": [8, 11],
        "answer_range": [int(answer_min), int(answer_max)],
        "max_visible_value": int(max_visible_value),
        "solver_trace": {
            "object_values": {str(key): int(value) for key, value in object_values.items()},
            "query_object_type": str(query_object_type),
            "panel_count": int(len(panel_specs)),
        },
    }


@register_task
class PuzzlesArithmeticBalanceValueTask:
    """Return the integer that fills the explicit query row in one equality puzzle."""

    task_id = TASK_ID
    domain = "puzzles"
    task_group = "arithmetic"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        task_variant, task_variant_probabilities = _resolve_task_variant(params, instance_seed=int(instance_seed))
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(params, instance_seed=int(instance_seed))
        dataset = _build_balance_dataset(
            task_variant=str(task_variant),
            params=params,
            instance_seed=int(instance_seed),
            gen_defaults=_GEN_DEFAULTS,
            defaults=_DEFAULTS,
            task_id=self.task_id,
        )

        render_params = _resolve_balance_render_params(
            params,
            render_defaults=_RENDER_DEFAULTS,
            defaults=_DEFAULTS,
        )
        jitter_min = int(render_params.relation_gap_jitter_min_px)
        jitter_max = int(render_params.relation_gap_jitter_max_px)
        if int(jitter_min) > int(jitter_max):
            raise ValueError("relation_gap_jitter_min_px must be <= relation_gap_jitter_max_px")
        layout_rng = spawn_rng(int(instance_seed), f"{self.task_id}.layout")
        panel_relation_gap_offsets = [
            int(layout_rng.randint(int(jitter_min), int(jitter_max)))
            for _ in dataset["panel_specs"]
        ]
        panel_specs_for_render = []
        for panel_spec, relation_gap_offset in zip(dataset["panel_specs"], panel_relation_gap_offsets):
            panel_copy = dict(panel_spec)
            panel_copy["relation_gap_offset_px"] = int(relation_gap_offset)
            panel_specs_for_render.append(panel_copy)
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered_scene = render_puzzle_balance_scene(
            background,
            scene_variant=str(scene_variant),
            panel_specs=list(panel_specs_for_render),
            query_spec=dict(dataset["query_spec"]),
            render_params=render_params,
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
                "answer_hint",
                "object_description_balance_strip",
                "object_description_balance_card",
                "object_description_balance_outline",
                "evidence_hint_sum_pair_unknown",
                "evidence_hint_two_panel_chain_unknown",
                "evidence_hint_three_panel_chain_unknown",
                "json_example_sum_pair_unknown",
                "json_example_two_panel_chain_unknown",
                "json_example_three_panel_chain_unknown",
                "json_example_answer_only_sum_pair_unknown",
                "json_example_answer_only_two_panel_chain_unknown",
                "json_example_answer_only_three_panel_chain_unknown",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        object_description = str(prompt_defaults[f"object_description_{str(scene_variant)}"])
        evidence_hint = str(prompt_defaults[f"evidence_hint_{str(task_variant)}"])
        json_example = str(prompt_defaults[f"json_example_{str(task_variant)}"])
        json_example_answer_only = str(prompt_defaults[f"json_example_answer_only_{str(task_variant)}"])

        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            task_family_key=str(prompt_defaults["task_family_key"]),
            task_key=str(prompt_defaults["task_key"]),
            task_variant_key=str(task_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(object_description),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(evidence_hint),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        query_box_id = str(dataset["query_box_id"])
        evidence_projection = projected_puzzle_bbox_evidence(rendered_scene.box_bbox_map, [str(query_box_id)])
        evidence_bboxes = [
            [round(float(value), 3) for value in bbox]
            for bbox in evidence_projection["bbox_set"]
        ]
        answer_value = int(dataset["answer_value"])
        answer_gt = TypedValue(type="integer", value=int(answer_value))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"puzzle_balance_{str(scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "task_variant": str(task_variant),
                    "scene_variant": str(scene_variant),
                    "answer_value": int(answer_value),
                    "query_box_id": str(query_box_id),
                    "query_object_box_id": str(dataset["query_object_box_id"]),
                    "query_object_type": str(dataset["query_object_type"]),
                },
            },
            "query_spec": {
                "task_variant": str(task_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "task_variant": str(task_variant),
                    "scene_variant": str(scene_variant),
                    "task_variant_probabilities": dict(task_variant_probabilities),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "panel_count": int(dataset["panel_count"]),
                    "panel_count_range": list(dataset["panel_count_range"]),
                    "total_box_count": int(dataset["total_box_count"]),
                    "total_box_count_range": list(dataset["total_box_count_range"]),
                    "answer_range": list(dataset["answer_range"]),
                    "relation_gap_jitter_range_px": [int(jitter_min), int(jitter_max)],
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "text_style": {
                    "value_font_size_px": int(render_params.value_font_size_px),
                },
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "box_bboxes_px": {str(key): list(value) for key, value in rendered_scene.box_bbox_map.items()},
            },
            "execution_trace": {
                "task_variant": str(task_variant),
                "scene_variant": str(scene_variant),
                "answer_value": int(answer_value),
                "query_box_id": str(query_box_id),
                "query_object_box_id": str(dataset["query_object_box_id"]),
                "query_object_type": str(dataset["query_object_type"]),
                "panel_specs": list(dataset["panel_specs"]),
                "panel_relation_gap_offsets_px": list(panel_relation_gap_offsets),
                "solver_trace": dict(dataset["solver_trace"]),
                "panel_count": int(dataset["panel_count"]),
                "panel_count_range": list(dataset["panel_count_range"]),
                "total_box_count": int(dataset["total_box_count"]),
                "total_box_count_range": list(dataset["total_box_count_range"]),
                "answer_range": list(dataset["answer_range"]),
                "max_visible_value": int(dataset["max_visible_value"]),
                "relation_gap_jitter_range_px": [int(jitter_min), int(jitter_max)],
                "task_variant_probabilities": dict(task_variant_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "supporting_box_ids": [str(query_box_id)],
                "question_format": "query_answer_box_balance",
            },
            "witness_symbolic": {
                "type": "bbox_set",
                "value": list(evidence_bboxes),
            },
            "projected_evidence": {
                "bbox_set": list(evidence_bboxes),
            },
        }

        object_values = {str(key): int(value) for key, value in dataset["solver_trace"]["object_values"].items()}
        implied_panel_count_norm = normalize_int_with_bounds(int(dataset["panel_count"]), list(dataset["panel_count_range"]))
        total_box_count_norm = normalize_int_with_bounds(int(dataset["total_box_count"]), list(dataset["total_box_count_range"]))
        reasoning_load = min(
            1.0,
            float(_REASONING_LOAD_BASE_BY_VARIANT[str(task_variant)])
            + (0.15 * float(implied_panel_count_norm))
            + (0.08 * float(len(object_values) - 2)),
        )

        complexity = build_puzzle_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": float(total_box_count_norm),
                "reasoning_load": float(reasoning_load),
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(scene_variant)]),
            },
        )

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            task_variant=str(task_variant),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["PuzzlesArithmeticBalanceValueTask"]
