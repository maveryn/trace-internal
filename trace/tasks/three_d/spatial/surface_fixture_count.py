"""Count repeated surface elements in a synthetic 3D fixture."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import (
    get_domain_defaults,
    get_task_group_defaults,
    resolve_task_group_section_defaults,
)
from ....core.types import TaskComplexity, TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.object_scene import _resolve_render_params
from ..shared.task_support import normalize_unit as _normalize_unit
from ..shared.task_support import resolve_axis_variant as _shared_resolve_axis_variant
from .surface_fixture_rendering import layout_surface_element_grid, render_surface_fixture


TASK_ID = "task_three_d__surface_fixture__repeated_element_count"
SCENE_ID = "surface_fixture"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = ("element_type_count",)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "wall_tile_panel",
    "perforated_panel",
    "slot_board",
    "compartment_tray",
    "vent_panel",
    "window_grid",
    "door_bank",
    "drawer_pull_panel",
)
ELEMENT_TYPE_BY_SCENE_VARIANT: Mapping[str, str] = {
    "wall_tile_panel": "tile",
    "perforated_panel": "hole",
    "slot_board": "slot",
    "compartment_tray": "compartment",
    "vent_panel": "vent",
    "window_grid": "window",
    "door_bank": "door",
    "drawer_pull_panel": "drawer_pull",
}
SCENE_VARIANT_BY_ELEMENT_TYPE: Mapping[str, str] = {
    str(element_type): str(scene_variant)
    for scene_variant, element_type in ELEMENT_TYPE_BY_SCENE_VARIANT.items()
}
ELEMENT_DISPLAY_NAME: Mapping[str, str] = {
    "tile": "tile",
    "hole": "hole",
    "slot": "slot",
    "compartment": "compartment",
    "vent": "vent",
    "window": "window",
    "door": "door",
    "drawer_pull": "drawer pull",
}
ELEMENT_PLURAL: Mapping[str, str] = {
    "tile": "tiles",
    "hole": "holes",
    "slot": "slots",
    "compartment": "compartments",
    "vent": "vents",
    "window": "windows",
    "door": "doors",
    "drawer_pull": "drawer pulls",
}


def _one_hot_probability_map(values: Sequence[str], selected: str) -> Dict[str, float]:
    return {str(value): (1.0 if str(value) == str(selected) else 0.0) for value in values}


def _uniform_probability_map(values: Sequence[int], *, selected: int | None = None) -> Dict[str, float]:
    support = tuple(int(value) for value in values)
    if selected is not None:
        return {str(value): (1.0 if int(value) == int(selected) else 0.0) for value in support}
    probability = 1.0 / float(max(1, len(support)))
    return {str(value): float(probability) for value in support}


def _configured_int(params: Mapping[str, Any], gen_defaults: Mapping[str, Any], key: str, default: int) -> int:
    return int(params.get(str(key), group_default(gen_defaults, str(key), int(default))))


def _resolve_count(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[int, Dict[str, float]]:
    minimum = max(4, min(32, _configured_int(params, gen_defaults, "target_count_min", 8)))
    maximum = max(minimum, min(32, _configured_int(params, gen_defaults, "target_count_max", 24)))
    support = tuple(range(int(minimum), int(maximum) + 1))
    explicit = params.get("target_count", params.get("element_count"))
    if explicit is not None:
        selected = int(explicit)
        if selected not in set(support):
            raise ValueError(f"unsupported target_count: {selected}")
        return int(selected), _uniform_probability_map(support, selected=int(selected))
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.target_count")
    selected = int(support[int(rng.randrange(len(support)))])
    return int(selected), _uniform_probability_map(support)


def _resolve_scene_and_element(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[str, Dict[str, float], str, Dict[str, float]]:
    explicit_element = params.get("target_element_type", params.get("element_type"))
    explicit_scene = params.get("scene_variant")
    supported_elements = tuple(str(item) for item in SCENE_VARIANT_BY_ELEMENT_TYPE.keys())
    if explicit_element is not None:
        element_type = str(explicit_element)
        if element_type not in set(supported_elements):
            raise ValueError(f"unsupported target_element_type: {element_type}")
        expected_scene = str(SCENE_VARIANT_BY_ELEMENT_TYPE[element_type])
        if explicit_scene is not None and str(explicit_scene) != expected_scene:
            raise ValueError(f"{element_type} fixtures require scene_variant={expected_scene}")
        return (
            expected_scene,
            _one_hot_probability_map(SUPPORTED_SCENE_VARIANTS, expected_scene),
            element_type,
            _one_hot_probability_map(supported_elements, element_type),
        )

    scene_variant, scene_probabilities = _shared_resolve_axis_variant(
        params,
        task_id=TASK_ID,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_SCENE_VARIANTS,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )
    element_type = str(ELEMENT_TYPE_BY_SCENE_VARIANT[str(scene_variant)])
    return (
        str(scene_variant),
        dict(scene_probabilities),
        str(element_type),
        _one_hot_probability_map(supported_elements, str(element_type)) if explicit_scene is not None else {
            str(ELEMENT_TYPE_BY_SCENE_VARIANT[str(scene)]): float(scene_probabilities[str(scene)])
            for scene in SUPPORTED_SCENE_VARIANTS
        },
    )


def _build_surface_dataset(
    *,
    query_id: str,
    scene_variant: str,
    element_type: str,
    target_count: int,
) -> Dict[str, Any]:
    target_ids = [f"{str(element_type)}_{index:02d}" for index in range(int(target_count))]
    rows, cols = layout_surface_element_grid(int(target_count))
    return {
        "query_id": str(query_id),
        "scene_variant": str(scene_variant),
        "target_element_type": str(element_type),
        "target_element_name": str(ELEMENT_DISPLAY_NAME[str(element_type)]),
        "target_element_plural": str(ELEMENT_PLURAL[str(element_type)]),
        "target_count": int(target_count),
        "answer_value": int(target_count),
        "target_element_ids": list(target_ids),
        "layout_rows": int(rows),
        "layout_columns": int(cols),
        "surface_world_corners": [
            [-2.0, 1.35, 2.55],
            [2.0, 1.35, 2.55],
            [2.0, 1.35, 0.15],
            [-2.0, 1.35, 0.15],
        ],
        "solver_trace": {
            "count_predicate": "element_type == target_element_type",
            "target_element_type": str(element_type),
            "target_element_plural": str(ELEMENT_PLURAL[str(element_type)]),
            "target_count": int(target_count),
            "element_count": int(target_count),
            "unique_integer_answer": True,
        },
    }


def _build_complexity(
    *,
    target_count: int,
    scene_variant: str,
    complexity_defaults: Mapping[str, Any],
) -> TaskComplexity:
    raw_weights = complexity_defaults.get("criteria_weights", {})
    if not isinstance(raw_weights, Mapping):
        raw_weights = {}
    weights = {
        "visual_scan": float(raw_weights.get("visual_scan", 0.46)),
        "target_count": float(raw_weights.get("target_count", 0.30)),
        "surface_perspective": float(raw_weights.get("surface_perspective", 0.16)),
        "element_detail": float(raw_weights.get("element_detail", 0.08)),
    }
    total = sum(max(0.0, float(value)) for value in weights.values()) or 1.0
    components = {
        "visual_scan": _normalize_unit(int(target_count), 4, 32),
        "target_count": _normalize_unit(int(target_count), 4, 32),
        "surface_perspective": {
            "wall_tile_panel": 0.48,
            "perforated_panel": 0.58,
            "slot_board": 0.54,
            "compartment_tray": 0.56,
            "vent_panel": 0.56,
            "window_grid": 0.60,
            "door_bank": 0.57,
            "drawer_pull_panel": 0.59,
        }.get(str(scene_variant), 0.50),
        "element_detail": {
            "wall_tile_panel": 0.38,
            "perforated_panel": 0.52,
            "slot_board": 0.58,
            "compartment_tray": 0.62,
            "vent_panel": 0.64,
            "window_grid": 0.66,
            "door_bank": 0.60,
            "drawer_pull_panel": 0.68,
        }.get(str(scene_variant), 0.46),
    }
    score = sum(float(components[key]) * max(0.0, float(weights[key])) for key in weights) / float(total)
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={key: round(float(value), 6) for key, value in components.items()},
    )


_TASK_GROUP_DEFAULTS = get_task_group_defaults("three_d", "spatial")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_DEFAULTS = resolve_task_group_section_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    "complexity",
    task_id=TASK_ID,
)
_DOMAIN_DEFAULTS = get_domain_defaults("three_d")
_VISUAL_DEFAULTS = _DOMAIN_DEFAULTS.get("visual", {}) if isinstance(_DOMAIN_DEFAULTS, Mapping) else {}
_BACKGROUND_DEFAULTS = _VISUAL_DEFAULTS.get("background", {}) if isinstance(_VISUAL_DEFAULTS, Mapping) else {}
_NOISE_DEFAULTS = _VISUAL_DEFAULTS.get("noise", {}) if isinstance(_VISUAL_DEFAULTS, Mapping) else {}


@register_task
class ThreeDSurfaceFixtureRepeatedElementCountTask:
    """Count repeated elements on a projected fixture surface."""

    task_id = TASK_ID
    domain = "three_d"
    task_group = "spatial"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_seed = (
                int(instance_seed)
                if attempt_index == 0
                else int(spawn_rng(int(instance_seed), f"{TASK_ID}.attempt_seed.{attempt_index}").randrange(1, 2**62))
            )
            try:
                return self._generate_once(int(attempt_seed), params=params)
            except Exception as exc:  # pragma: no cover - retained for parity with sampled 3D tasks.
                last_error = exc
        raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts: {last_error}")

    def _generate_once(self, instance_seed: int, *, params: Dict[str, Any]) -> TaskOutput:
        query_id, query_probabilities = _shared_resolve_axis_variant(
            params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            supported_variants=SUPPORTED_QUERY_IDS,
            explicit_key="query_id",
            weights_key="query_id_weights",
            balance_flag_key="balanced_query_id_sampling",
            axis_namespace="query_id",
        )
        scene_variant, scene_probabilities, element_type, element_probabilities = _resolve_scene_and_element(
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        target_count, target_count_probabilities = _resolve_count(
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
        )

        render_params = _resolve_render_params(params, render_defaults=_RENDER_DEFAULTS)
        dataset = _build_surface_dataset(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            element_type=str(element_type),
            target_count=int(target_count),
        )
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=_BACKGROUND_DEFAULTS,
        )
        rendered = render_surface_fixture(background, dataset=dataset, render_params=render_params)
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=_NOISE_DEFAULTS,
        )
        target_element_ids = [str(element_id) for element_id in dataset["target_element_ids"]]
        annotation_bboxes = [list(rendered.element_bboxes_px[str(element_id)]) for element_id in target_element_ids]

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "answer_hint",
                "annotation_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "target_element_name": str(dataset["target_element_name"]),
                "target_element_plural": str(dataset["target_element_plural"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "annotation_hint": str(prompt_defaults["annotation_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_value = int(dataset["answer_value"])
        answer_gt = TypedValue(type="integer", value=int(answer_value))
        annotation_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in annotation_bboxes])
        solver_trace = dict(dataset["solver_trace"])
        solver_trace.update(
            {
                "answer_value": int(answer_value),
                "target_element_ids": list(target_element_ids),
                "target_element_bboxes_px": {
                    str(element_id): list(rendered.element_bboxes_px[str(element_id)])
                    for element_id in target_element_ids
                },
            }
        )
        complexity = _build_complexity(
            target_count=int(answer_value),
            scene_variant=str(scene_variant),
            complexity_defaults=_COMPLEXITY_DEFAULTS,
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "three_d_surface_fixture_repeated_element_count",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "scene_variant": str(scene_variant),
                    "target_element_type": str(dataset["target_element_type"]),
                    "target_element_name": str(dataset["target_element_name"]),
                    "target_element_plural": str(dataset["target_element_plural"]),
                    "target_count": int(answer_value),
                    "target_element_ids": list(target_element_ids),
                    "element_count": int(answer_value),
                    "layout_rows": int(dataset["layout_rows"]),
                    "layout_columns": int(dataset["layout_columns"]),
                },
            },
            "query_spec": {
                "query_id": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(query_id),
                    "query_id_probabilities": dict(query_probabilities),
                    "scene_variant": str(scene_variant),
                    "scene_variant_probabilities": dict(scene_probabilities),
                    "target_element_type": str(dataset["target_element_type"]),
                    "target_element_type_probabilities": dict(element_probabilities),
                    "target_count": int(answer_value),
                    "target_count_probabilities": dict(target_count_probabilities),
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "projection_model": "synthetic_perspective_panel_v0",
                "surface_world_corners": [list(point) for point in dataset["surface_world_corners"]],
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": list(rendered.scene_bbox_px),
                "fixture_bbox_px": list(rendered.fixture_bbox_px),
                "element_bboxes_px": dict(rendered.element_bboxes_px),
                "element_centers_px": dict(rendered.element_centers_px),
                "target_element_bboxes_px": {
                    str(element_id): list(rendered.element_bboxes_px[str(element_id)])
                    for element_id in target_element_ids
                },
                "target_element_centers_px": {
                    str(element_id): list(rendered.element_centers_px[str(element_id)])
                    for element_id in target_element_ids
                },
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "answer_value": int(answer_value),
                "target_element_type": str(dataset["target_element_type"]),
                "target_element_name": str(dataset["target_element_name"]),
                "target_element_plural": str(dataset["target_element_plural"]),
                "target_element_ids": list(target_element_ids),
                "target_element_bboxes_px": {
                    str(element_id): list(rendered.element_bboxes_px[str(element_id)])
                    for element_id in target_element_ids
                },
                "layout_rows": int(dataset["layout_rows"]),
                "layout_columns": int(dataset["layout_columns"]),
                "question_format": str(query_id),
                "solver_trace": dict(solver_trace),
            },
            "witness_symbolic": {
                "type": "counted_surface_element_set",
                "element_ids": list(target_element_ids),
                "target_element_type": str(dataset["target_element_type"]),
                "answer_value": int(answer_value),
            },
            "projected_annotation": {
                "type": "bbox_set",
                "bbox_set": [list(bbox) for bbox in annotation_bboxes],
                "pixel_bbox_set": [list(bbox) for bbox in annotation_bboxes],
            },
            "background": dict(background_meta),
            "post_image_noise": dict(post_noise_meta),
        }

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
        )


__all__ = ["ThreeDSurfaceFixtureRepeatedElementCountTask"]
