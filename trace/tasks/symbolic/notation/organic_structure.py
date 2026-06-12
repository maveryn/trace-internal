"""Organic-structure notation bond-order count task."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Dict, Mapping, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.bbox_projection import round_bbox as _round_bbox
from ...shared.config_defaults import group_default, required_group_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.render_variation import resolve_render_int
from ..shared.common import (
    get_int_param as _get_int,
    get_int_range as _get_range,
    load_symbolic_task_defaults,
    resolve_symbolic_axis_variant,
)
from ..shared.organic_structure_scene import (
    ORGANIC_STRUCTURE_MAX_BRANCH_POINT_COUNT,
    ORGANIC_STRUCTURE_MAX_BOND_ORDER_COUNT,
    ORGANIC_STRUCTURE_MAX_RING_SIZE_COUNT,
    SUPPORTED_BOND_ORDERS,
    SUPPORTED_ORGANIC_RING_SIZES,
    OrganicStructureSpec,
    build_constrained_organic_branch_structure,
    build_constrained_organic_ring_size_structure,
    build_constrained_organic_structure,
    draw_organic_structure,
    organic_branch_point_atom_indices,
    organic_ring_item_ids,
    project_organic_structure,
    validate_organic_structure,
)
from ..shared.scene_style import make_symbolic_scene_background, resolve_symbolic_scene_style
from ..shared.unit_size_jitter import resolve_symbolic_unit_size_scale, scale_symbolic_px, with_symbolic_unit_size_jitter
from ..shared.visual_defaults import load_symbolic_noise_defaults


SCENE_ID = "organic_structure"
BOND_ORDER_COUNT_TASK_ID = "task_symbolic__organic_structure__bond_order_count"
BRANCH_POINT_COUNT_TASK_ID = "task_symbolic__organic_structure__branch_point_count"
RING_SIZE_COUNT_TASK_ID = "task_symbolic__organic_structure__ring_size_count"
TASK_ID = BOND_ORDER_COUNT_TASK_ID

BOND_ORDER_COUNT_QUERY_ID = "bond_order_count"
BRANCH_POINT_COUNT_QUERY_ID = "branch_point_count"
RING_SIZE_COUNT_QUERY_ID = "ring_size_count"
BOND_ORDER_QUERY_IDS: Tuple[str, ...] = (BOND_ORDER_COUNT_QUERY_ID,)
BRANCH_POINT_QUERY_IDS: Tuple[str, ...] = (BRANCH_POINT_COUNT_QUERY_ID,)
RING_SIZE_QUERY_IDS: Tuple[str, ...] = (RING_SIZE_COUNT_QUERY_ID,)
QUERY_IDS: Tuple[str, ...] = BOND_ORDER_QUERY_IDS
TARGET_BOND_ORDERS: Tuple[str, ...] = ("double", "triple")
TARGET_RING_SIZES: Tuple[int, ...] = SUPPORTED_ORGANIC_RING_SIZES
SCENE_VARIANTS: Tuple[str, ...] = ("clean_worksheet", "exam_scan", "notebook_problem")

_TASK_GROUP_DEFAULTS = get_scene_defaults("symbolic", "notation")
POST_IMAGE_NOISE_DEFAULTS = load_symbolic_noise_defaults(scene_id="notation", apply_prob=0.5)


@dataclass(frozen=True)
class _RenderParams:
    canvas_width: int
    canvas_height: int
    panel_padding_px: int
    panel_corner_radius_px: int
    panel_border_width_px: int
    bond_width_px: int
    bond_gap_px: int
    structure_width_px: int
    structure_height_px: int
    unit_size_jitter: Dict[str, Any]
    panel_fill_rgb: Tuple[int, int, int]
    panel_border_rgb: Tuple[int, int, int]
    bond_rgb: Tuple[int, int, int]
    annotation_rgb: Tuple[int, int, int]


@dataclass(frozen=True)
class _Dataset:
    query_id: str
    target_bond_order: str
    answer_value: int
    structure: OrganicStructureSpec
    annotation_item_ids: Tuple[str, ...]
    scene_variant: str
    target_answer_support: Tuple[int, ...]
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class _RenderedScene:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    scene_bbox_px: Tuple[float, float, float, float]
    item_bboxes: Dict[str, Tuple[float, float, float, float]]
    item_point_pairs: Dict[str, Tuple[Tuple[float, float], Tuple[float, float]]]
    item_points: Dict[str, Tuple[float, float]]
    layout_jitter: Dict[str, Any]
    style_metadata: Dict[str, Any]


def _load_defaults(task_id: str = TASK_ID) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, float]]:
    return load_symbolic_task_defaults(_TASK_GROUP_DEFAULTS, task_id=str(task_id))


def _resolve_query_id(
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    *,
    instance_seed: int,
    task_id: str = TASK_ID,
    supported_query_ids: Tuple[str, ...] = QUERY_IDS,
) -> Tuple[str, Dict[str, float]]:
    effective_params = dict(params)
    if effective_params.get("query_id") is None and effective_params.get("query_variant") is not None:
        effective_params["query_id"] = str(effective_params["query_variant"])
    return resolve_symbolic_axis_variant(
        params=effective_params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=supported_query_ids,
        task_id=str(task_id),
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )


def _resolve_target_bond_order(
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    *,
    instance_seed: int,
    task_id: str = TASK_ID,
) -> Tuple[str, Dict[str, float]]:
    return resolve_symbolic_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=TARGET_BOND_ORDERS,
        task_id=str(task_id),
        explicit_key="target_bond_order",
        weights_key="target_bond_order_weights",
        balance_flag_key="balanced_target_bond_order_sampling",
        axis_namespace="target_bond_order",
    )


def _resolve_target_ring_size(
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    *,
    instance_seed: int,
    task_id: str = RING_SIZE_COUNT_TASK_ID,
) -> Tuple[int, Dict[str, float]]:
    selected, probabilities = resolve_symbolic_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=[str(item) for item in TARGET_RING_SIZES],
        task_id=str(task_id),
        explicit_key="target_ring_size",
        weights_key="target_ring_size_weights",
        balance_flag_key="balanced_target_ring_size_sampling",
        axis_namespace="target_ring_size",
    )
    return int(selected), {str(key): float(value) for key, value in probabilities.items()}


def _resolve_scene_variant(
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    *,
    instance_seed: int,
    task_id: str = TASK_ID,
) -> Tuple[str, Dict[str, float]]:
    return resolve_symbolic_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SCENE_VARIANTS,
        task_id=str(task_id),
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def _resolve_render_params(params: Mapping[str, Any], defaults: Mapping[str, Any], *, instance_seed: int, task_id: str = TASK_ID) -> _RenderParams:
    unit_scale, unit_meta = resolve_symbolic_unit_size_scale(
        params,
        defaults,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.unit_size",
        fallback_min=0.5,
        fallback_max=1.0,
    )
    effective_scale_min = float(params.get("organic_effective_unit_size_scale_min", group_default(defaults, "organic_effective_unit_size_scale_min", 0.85)))
    unit_scale = max(float(unit_scale), float(effective_scale_min))
    unit_meta = dict(unit_meta)
    unit_meta["effective_scale"] = float(unit_scale)
    unit_meta["effective_scale_min"] = float(effective_scale_min)
    canvas_width = int(params.get("canvas_width", group_default(defaults, "canvas_width", 1180)))
    canvas_height = int(params.get("canvas_height", group_default(defaults, "canvas_height", 820)))
    bond_width = resolve_render_int(params, defaults, "organic_bond_width_px", 4, instance_seed=int(instance_seed), namespace=f"{task_id}.bond_width")
    return _RenderParams(
        canvas_width=canvas_width,
        canvas_height=canvas_height,
        panel_padding_px=scale_symbolic_px(_get_int(params, defaults, "panel_padding_px", 34), unit_scale, min_px=18),
        panel_corner_radius_px=scale_symbolic_px(_get_int(params, defaults, "panel_corner_radius_px", 18), unit_scale, min_px=8),
        panel_border_width_px=max(1, scale_symbolic_px(_get_int(params, defaults, "panel_border_width_px", 2), unit_scale, min_px=1)),
        bond_width_px=max(2, scale_symbolic_px(bond_width, unit_scale, min_px=2)),
        bond_gap_px=max(6, scale_symbolic_px(_get_int(params, defaults, "organic_bond_gap_px", 10), unit_scale, min_px=6)),
        structure_width_px=scale_symbolic_px(_get_int(params, defaults, "organic_structure_width_px", 860), unit_scale, min_px=620),
        structure_height_px=scale_symbolic_px(_get_int(params, defaults, "organic_structure_height_px", 540), unit_scale, min_px=400),
        unit_size_jitter=dict(unit_meta),
        panel_fill_rgb=(253, 253, 249),
        panel_border_rgb=(80, 86, 92),
        bond_rgb=(28, 30, 34),
        annotation_rgb=(160, 164, 168),
    )


def _build_dataset(*, params: Mapping[str, Any], gen_defaults: Mapping[str, Any], instance_seed: int, scene_variant: str) -> _Dataset:
    query_id, _query_probabilities = _resolve_query_id(
        params,
        gen_defaults,
        instance_seed=int(instance_seed),
        task_id=BOND_ORDER_COUNT_TASK_ID,
        supported_query_ids=BOND_ORDER_QUERY_IDS,
    )
    target_bond_order, _order_probabilities = _resolve_target_bond_order(
        params,
        gen_defaults,
        instance_seed=int(instance_seed),
        task_id=BOND_ORDER_COUNT_TASK_ID,
    )
    rng = spawn_rng(int(instance_seed), f"{BOND_ORDER_COUNT_TASK_ID}.dataset")
    answer_min, answer_max = _get_range(
        params,
        gen_defaults,
        min_key="target_answer_min",
        max_key="target_answer_max",
        fallback_min=1,
        fallback_max=ORGANIC_STRUCTURE_MAX_BOND_ORDER_COUNT,
    )
    if int(answer_min) < 1 or int(answer_max) > ORGANIC_STRUCTURE_MAX_BOND_ORDER_COUNT:
        raise RuntimeError(f"{BOND_ORDER_COUNT_TASK_ID} supports target_answer_min/max only within 1..{ORGANIC_STRUCTURE_MAX_BOND_ORDER_COUNT}")
    support = tuple(range(int(answer_min), int(answer_max) + 1))
    if "answer_value" in params:
        answer_count = int(params["answer_value"])
        if answer_count not in support:
            raise RuntimeError(f"answer_value={answer_count} is outside configured support {support}")
    else:
        answer_count = int(rng.choice(support))

    structure = build_constrained_organic_structure(
        rng,
        target_bond_order=str(target_bond_order),
        answer_count=int(answer_count),
    )
    constraint_report = validate_organic_structure(structure)
    annotation_ids = tuple(bond.item_id for bond in structure.bonds if bond.order == str(target_bond_order))
    if len(annotation_ids) != int(answer_count):
        raise RuntimeError("constrained organic structure did not preserve requested answer value")
    metadata = {
        "target_bond_order": str(target_bond_order),
        "target_bond_order_support": list(TARGET_BOND_ORDERS),
        "bond_order_support": list(SUPPORTED_BOND_ORDERS),
        "scaffold_id": str(structure.scaffold_id),
        "scaffold_family": str(structure.scaffold_family),
        "constraint_policy": str(structure.constraint_policy),
        "constraint_report": constraint_report.to_metadata(),
        "chemical_validity_policy": "basic carbon valence and line-angle geometry constraints are enforced; molecule identity is not required",
        "text_label_policy": "atom and group letters are not rendered for this task",
    }
    return _Dataset(
        query_id=str(query_id),
        target_bond_order=str(target_bond_order),
        answer_value=int(len(annotation_ids)),
        structure=structure,
        annotation_item_ids=tuple(annotation_ids),
        scene_variant=str(scene_variant),
        target_answer_support=tuple(support),
        metadata=dict(metadata),
    )


def _build_branch_point_dataset(*, params: Mapping[str, Any], gen_defaults: Mapping[str, Any], instance_seed: int, scene_variant: str) -> _Dataset:
    query_id, _query_probabilities = _resolve_query_id(
        params,
        gen_defaults,
        instance_seed=int(instance_seed),
        task_id=BRANCH_POINT_COUNT_TASK_ID,
        supported_query_ids=BRANCH_POINT_QUERY_IDS,
    )
    rng = spawn_rng(int(instance_seed), f"{BRANCH_POINT_COUNT_TASK_ID}.dataset")
    answer_min, answer_max = _get_range(
        params,
        gen_defaults,
        min_key="target_answer_min",
        max_key="target_answer_max",
        fallback_min=0,
        fallback_max=ORGANIC_STRUCTURE_MAX_BRANCH_POINT_COUNT,
    )
    if int(answer_min) < 0 or int(answer_max) > ORGANIC_STRUCTURE_MAX_BRANCH_POINT_COUNT:
        raise RuntimeError(f"{BRANCH_POINT_COUNT_TASK_ID} supports target_answer_min/max only within 0..{ORGANIC_STRUCTURE_MAX_BRANCH_POINT_COUNT}")
    support = tuple(range(int(answer_min), int(answer_max) + 1))
    if "answer_value" in params:
        answer_count = int(params["answer_value"])
        if answer_count not in support:
            raise RuntimeError(f"answer_value={answer_count} is outside configured support {support}")
    else:
        answer_count = int(rng.choice(support))

    structure = build_constrained_organic_branch_structure(rng, answer_count=int(answer_count))
    constraint_report = validate_organic_structure(structure)
    branch_indices = organic_branch_point_atom_indices(structure)
    annotation_ids = tuple(structure.atoms[idx].item_id for idx in branch_indices)
    if len(annotation_ids) != int(answer_count):
        raise RuntimeError("constrained organic branch structure did not preserve requested answer value")
    metadata = {
        "target_property": "branch_point",
        "branch_point_definition": "line-angle vertex where three or more drawn bonds meet",
        "branch_point_support": list(range(0, ORGANIC_STRUCTURE_MAX_BRANCH_POINT_COUNT + 1)),
        "bond_order_support": list(SUPPORTED_BOND_ORDERS),
        "scaffold_id": str(structure.scaffold_id),
        "scaffold_family": str(structure.scaffold_family),
        "constraint_policy": str(structure.constraint_policy),
        "constraint_report": constraint_report.to_metadata(),
        "chemical_validity_policy": "basic carbon valence and line-angle geometry constraints are enforced; molecule identity is not required",
        "text_label_policy": "atom and group letters are not rendered for this task",
    }
    return _Dataset(
        query_id=str(query_id),
        target_bond_order="not_applicable",
        answer_value=int(len(annotation_ids)),
        structure=structure,
        annotation_item_ids=tuple(annotation_ids),
        scene_variant=str(scene_variant),
        target_answer_support=tuple(support),
        metadata=dict(metadata),
    )


def _ring_size_name(ring_size: int) -> str:
    return "pentagonal" if int(ring_size) == 5 else "hexagonal"


def _build_ring_size_dataset(*, params: Mapping[str, Any], gen_defaults: Mapping[str, Any], instance_seed: int, scene_variant: str) -> _Dataset:
    query_id, _query_probabilities = _resolve_query_id(
        params,
        gen_defaults,
        instance_seed=int(instance_seed),
        task_id=RING_SIZE_COUNT_TASK_ID,
        supported_query_ids=RING_SIZE_QUERY_IDS,
    )
    target_ring_size, _ring_size_probabilities = _resolve_target_ring_size(
        params,
        gen_defaults,
        instance_seed=int(instance_seed),
        task_id=RING_SIZE_COUNT_TASK_ID,
    )
    rng = spawn_rng(int(instance_seed), f"{RING_SIZE_COUNT_TASK_ID}.dataset")
    answer_min, answer_max = _get_range(
        params,
        gen_defaults,
        min_key="target_answer_min",
        max_key="target_answer_max",
        fallback_min=0,
        fallback_max=ORGANIC_STRUCTURE_MAX_RING_SIZE_COUNT,
    )
    if int(answer_min) < 0 or int(answer_max) > ORGANIC_STRUCTURE_MAX_RING_SIZE_COUNT:
        raise RuntimeError(f"{RING_SIZE_COUNT_TASK_ID} supports target_answer_min/max only within 0..{ORGANIC_STRUCTURE_MAX_RING_SIZE_COUNT}")
    support = tuple(range(int(answer_min), int(answer_max) + 1))
    if "answer_value" in params:
        answer_count = int(params["answer_value"])
        if answer_count not in support:
            raise RuntimeError(f"answer_value={answer_count} is outside configured support {support}")
    else:
        answer_count = int(rng.choice(support))

    structure = build_constrained_organic_ring_size_structure(
        rng,
        target_ring_size=int(target_ring_size),
        answer_count=int(answer_count),
    )
    constraint_report = validate_organic_structure(structure)
    annotation_ids = organic_ring_item_ids(structure, int(target_ring_size))
    if len(annotation_ids) != int(answer_count):
        raise RuntimeError("constrained organic ring-size structure did not preserve requested answer value")
    metadata = {
        "target_property": "ring_size",
        "target_ring_size": int(target_ring_size),
        "target_ring_name": _ring_size_name(int(target_ring_size)),
        "target_ring_size_support": list(TARGET_RING_SIZES),
        "ring_size_support": list(SUPPORTED_ORGANIC_RING_SIZES),
        "ring_count_support": list(range(0, ORGANIC_STRUCTURE_MAX_RING_SIZE_COUNT + 1)),
        "scaffold_id": str(structure.scaffold_id),
        "scaffold_family": str(structure.scaffold_family),
        "constraint_policy": str(structure.constraint_policy),
        "constraint_report": constraint_report.to_metadata(),
        "chemical_validity_policy": "basic carbon valence and line-angle geometry constraints are enforced; molecule identity is not required",
        "ring_layout_policy": "rings are separated and connected by single bonds; fused-ring counting is outside this task",
        "text_label_policy": "atom and group letters are not rendered for this task",
    }
    return _Dataset(
        query_id=str(query_id),
        target_bond_order="not_applicable",
        answer_value=int(len(annotation_ids)),
        structure=structure,
        annotation_item_ids=tuple(annotation_ids),
        scene_variant=str(scene_variant),
        target_answer_support=tuple(support),
        metadata=dict(metadata),
    )


def _draw_scene_variant_marks(draw: ImageDraw.ImageDraw, *, panel_bbox: Tuple[int, int, int, int], scene_variant: str, render_params: _RenderParams) -> Dict[str, Any]:
    x0, y0, x1, y1 = panel_bbox
    if str(scene_variant) == "notebook_problem":
        for y in range(y0 + 68, y1 - 22, 34):
            draw.line((x0 + 22, y, x1 - 22, y), fill=(225, 233, 239), width=1)
        draw.line((x0 + 86, y0 + 24, x0 + 86, y1 - 24), fill=(238, 199, 199), width=1)
        return {"variant_marks": "notebook_lines"}
    if str(scene_variant) == "exam_scan":
        draw.rectangle((x0 + 26, y0 + 24, x0 + 92, y0 + 52), outline=render_params.annotation_rgb, width=1)
        draw.line((x0 + 110, y0 + 38, x1 - 34, y0 + 38), fill=(220, 222, 224), width=1)
        return {"variant_marks": "exam_header_rule"}
    return {"variant_marks": "clean_panel"}


def _render_scene(
    base_image: Image.Image,
    *,
    dataset: _Dataset,
    render_params: _RenderParams,
    instance_seed: int,
    task_id: str = TASK_ID,
) -> _RenderedScene:
    image = base_image.copy()
    draw = ImageDraw.Draw(image)
    panel_x0 = int(render_params.panel_padding_px)
    panel_y0 = int(render_params.panel_padding_px)
    panel_x1 = int(render_params.canvas_width - render_params.panel_padding_px)
    panel_y1 = int(render_params.canvas_height - render_params.panel_padding_px)
    panel_bbox = (panel_x0, panel_y0, panel_x1, panel_y1)
    draw.rounded_rectangle(
        panel_bbox,
        radius=int(render_params.panel_corner_radius_px),
        fill=render_params.panel_fill_rgb,
        outline=render_params.panel_border_rgb,
        width=int(render_params.panel_border_width_px),
    )
    style_meta = _draw_scene_variant_marks(draw, panel_bbox=panel_bbox, scene_variant=dataset.scene_variant, render_params=render_params)
    projection = project_organic_structure(
        spec=dataset.structure,
        panel_bbox=panel_bbox,
        structure_width_px=int(render_params.structure_width_px),
        structure_height_px=int(render_params.structure_height_px),
        instance_seed=int(instance_seed),
        namespace=str(task_id),
    )
    rendered_structure = draw_organic_structure(
        draw,
        spec=dataset.structure,
        projection=projection,
        bond_rgb=render_params.bond_rgb,
        bond_width_px=int(render_params.bond_width_px),
        bond_gap_px=int(render_params.bond_gap_px),
    )
    return _RenderedScene(
        image=image,
        entities=tuple(rendered_structure.entities),
        scene_bbox_px=_round_bbox(panel_bbox),
        item_bboxes=dict(rendered_structure.item_bboxes),
        item_point_pairs=dict(rendered_structure.item_point_pairs),
        item_points=dict(rendered_structure.item_points),
        layout_jitter=dict(projection.metadata),
        style_metadata={**dict(style_meta), **dict(rendered_structure.metadata)},
    )


def _build_prompt(*, dataset: _Dataset, prompt_defaults: Mapping[str, Any], instance_seed: int, task_id: str = TASK_ID) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
    query_id = str(dataset.query_id)
    scene_variant = str(dataset.scene_variant)
    required_keys = (
        "bundle_id",
        "scene_key",
        "task_key",
        "json_output_contract",
        "json_output_contract_answer_only",
        f"object_description_{scene_variant}",
        f"answer_hint_{query_id}",
        f"annotation_hint_{query_id}",
        f"json_example_{query_id}",
        f"json_example_answer_only_{query_id}",
    )
    prompt_values = required_group_defaults(prompt_defaults, required_keys, context=f"prompt defaults for {task_id}")
    slots = {
        "object_description": str(prompt_values[f"object_description_{scene_variant}"]),
        "target_bond_order": str(dataset.target_bond_order),
        "target_ring_name": str(dataset.metadata.get("target_ring_name", "")),
        "target_ring_size": str(dataset.metadata.get("target_ring_size", "")),
        "json_output_contract": str(prompt_values["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_values["json_output_contract_answer_only"]),
        "annotation_hint": str(prompt_values[f"annotation_hint_{query_id}"]),
        "answer_hint": str(prompt_values[f"answer_hint_{query_id}"]),
        "json_example": str(prompt_values[f"json_example_{query_id}"]),
        "json_example_answer_only": str(prompt_values[f"json_example_answer_only_{query_id}"]),
    }
    prompt_selection = render_task_prompt_variants(
        domain="symbolic",
        scene_id="notation",
        bundle_id=str(prompt_values["bundle_id"]),
        scene_key=str(prompt_values["scene_key"]),
        task_key=str(prompt_values["task_key"]),
        query_key=str(query_id),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        slots=slots,
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
    return str(prompt_artifacts.prompt), dict(prompt_artifacts.prompt_variants), {
        "prompt_variant": dict(prompt_artifacts.prompt_variant),
        "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
        "prompt_variants_for_trace": dict(prompt_artifacts.prompt_variants_for_trace),
        "bundle_id": str(prompt_values["bundle_id"]),
    }


@register_task
class SymbolicBondOrderCountTask:
    """Count double or triple bonds in an organic-structure notation panel."""

    task_id = BOND_ORDER_COUNT_TASK_ID
    domain = "symbolic"
    scene_id = "notation"
    supported_query_ids = BOND_ORDER_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(
            params,
            gen_defaults,
            instance_seed=int(instance_seed),
            task_id=BOND_ORDER_COUNT_TASK_ID,
        )
        dataset: _Dataset | None = None
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            try:
                dataset = _build_dataset(
                    params=params,
                    gen_defaults=gen_defaults,
                    instance_seed=int(instance_seed) + int(attempt_index),
                    scene_variant=str(scene_variant),
                )
                break
            except RuntimeError as exc:
                last_error = exc
        if dataset is None:
            raise RuntimeError("failed to generate organic-structure bond-order instance") from last_error

        query_id, query_id_probabilities = _resolve_query_id(
            params,
            gen_defaults,
            instance_seed=int(instance_seed),
            task_id=BOND_ORDER_COUNT_TASK_ID,
            supported_query_ids=BOND_ORDER_QUERY_IDS,
        )
        target_bond_order, target_bond_order_probabilities = _resolve_target_bond_order(
            params,
            gen_defaults,
            instance_seed=int(instance_seed),
            task_id=BOND_ORDER_COUNT_TASK_ID,
        )
        render_params = _resolve_render_params(params, render_defaults, instance_seed=int(instance_seed), task_id=BOND_ORDER_COUNT_TASK_ID)
        scene_style, scene_style_meta = resolve_symbolic_scene_style(
            instance_seed=int(instance_seed),
            namespace=f"{BOND_ORDER_COUNT_TASK_ID}.organic_structure_background",
        )
        render_params = replace(
            render_params,
            panel_fill_rgb=(253, 252, 247),
            panel_border_rgb=(88, 88, 88),
            bond_rgb=(24, 25, 27),
            annotation_rgb=(160, 164, 168),
        )
        background, background_meta = make_symbolic_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=scene_style,
        )
        rendered_scene = _render_scene(
            background,
            dataset=dataset,
            render_params=render_params,
            instance_seed=int(instance_seed),
            task_id=BOND_ORDER_COUNT_TASK_ID,
        )
        image, post_noise_meta = apply_post_image_noise(rendered_scene.image, instance_seed=int(instance_seed), params=params, default_config=POST_IMAGE_NOISE_DEFAULTS)
        prompt, prompt_variants, prompt_meta = _build_prompt(
            dataset=dataset,
            prompt_defaults=prompt_defaults,
            instance_seed=int(instance_seed),
            task_id=BOND_ORDER_COUNT_TASK_ID,
        )
        annotation_point_pairs = [
            [[round(float(value), 3) for value in point] for point in rendered_scene.item_point_pairs[str(item_id)]]
            for item_id in dataset.annotation_item_ids
        ]
        answer_gt = TypedValue(type="integer", value=int(dataset.answer_value))
        annotation_gt = TypedValue(type="point_pair_set", value=list(annotation_point_pairs))

        query_params = {
            "query_id": str(query_id),
            "query_id_probabilities": dict(query_id_probabilities),
            "scene_id": SCENE_ID,
            "scene_variant": str(scene_variant),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "target_bond_order": str(target_bond_order),
            "target_bond_order_probabilities": dict(target_bond_order_probabilities),
            "answer_support": list(dataset.target_answer_support),
            "target_answer_support": list(dataset.target_answer_support),
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": SCENE_ID,
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(dataset.query_id),
                    "internal_query_id": str(dataset.query_id),
                    "scene_id": SCENE_ID,
                    "scene_variant": str(scene_variant),
                    "target_bond_order": str(dataset.target_bond_order),
                    "answer_value": int(dataset.answer_value),
                    "scaffold_id": str(dataset.structure.scaffold_id),
                    "scaffold_family": str(dataset.structure.scaffold_family),
                },
            },
            "query_spec": {
                "query_id": str(dataset.query_id),
                "internal_query_id": str(dataset.query_id),
                "template_id": str(prompt_meta["bundle_id"]),
                "prompt_variant": dict(prompt_meta["prompt_variant"]),
                "prompt_variant_active_key": str(prompt_meta["prompt_variant_active_key"]),
                "prompt_variants": dict(prompt_meta["prompt_variants_for_trace"]),
                "params": dict(query_params),
            },
            "render_spec": {
                "scene_id": SCENE_ID,
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "scene_style": dict(scene_style_meta),
                "organic_style": dict(rendered_scene.style_metadata),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "unit_size_jitter": dict(render_params.unit_size_jitter),
                "layout_jitter": dict(rendered_scene.layout_jitter),
            },
            "render_map": with_symbolic_unit_size_jitter(
                {
                    "image_id": "img0",
                    "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                    "item_bboxes_px": {str(key): list(value) for key, value in rendered_scene.item_bboxes.items()},
                    "bond_point_pairs_px": {
                        str(key): [list(point) for point in value]
                        for key, value in rendered_scene.item_point_pairs.items()
                    },
                    "atom_points_px": {str(key): list(value) for key, value in rendered_scene.item_points.items()},
                    "annotation_source": "bond_point_pairs_px",
                    "layout_jitter": dict(rendered_scene.layout_jitter),
                },
                render_params.unit_size_jitter,
            ),
            "execution_trace": {
                **dict(query_params),
                "answer_value": int(dataset.answer_value),
                "answer_type": "integer",
                "annotation_item_ids": [str(item) for item in dataset.annotation_item_ids],
                "organic_metadata": dict(dataset.metadata),
                "atoms": [
                    {
                        "item_id": atom.item_id,
                        "element": atom.element,
                        "implicit": bool(atom.implicit),
                        "x": round(float(atom.x), 6),
                        "y": round(float(atom.y), 6),
                    }
                    for atom in dataset.structure.atoms
                ],
                "bonds": [
                    {
                        "item_id": bond.item_id,
                        "from_vertex": int(bond.atom_a),
                        "to_vertex": int(bond.atom_b),
                        "from_atom": int(bond.atom_a),
                        "to_atom": int(bond.atom_b),
                        "bond_order": bond.order,
                        "bond_role": bond.role,
                        "ring_index": None if bond.ring_index is None else int(bond.ring_index),
                    }
                    for bond in dataset.structure.bonds
                ],
                "ring_vertex_sets": [[int(idx) for idx in ring] for ring in dataset.structure.ring_atom_sets],
                "question_format": str(dataset.query_id),
            },
            "witness_symbolic": {"type": "point_pair_set", "value": list(annotation_point_pairs)},
            "projected_annotation": {"type": "point_pair_set", "point_pair_set": list(annotation_point_pairs), "value": list(annotation_point_pairs)},
            "answer_gt": answer_gt.to_dict(),
            "annotation_gt": annotation_gt.to_dict(),
        }
        return TaskOutput(
            prompt=str(prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(dataset.query_id),
            prompt_variants=dict(prompt_variants),
        )


@register_task
class SymbolicBranchPointCountTask:
    """Count skeletal branch points in an organic-structure notation panel."""

    task_id = BRANCH_POINT_COUNT_TASK_ID
    domain = "symbolic"
    scene_id = "notation"
    supported_query_ids = BRANCH_POINT_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(
            params,
            gen_defaults,
            instance_seed=int(instance_seed),
            task_id=BRANCH_POINT_COUNT_TASK_ID,
        )
        dataset: _Dataset | None = None
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            try:
                dataset = _build_branch_point_dataset(
                    params=params,
                    gen_defaults=gen_defaults,
                    instance_seed=int(instance_seed) + int(attempt_index),
                    scene_variant=str(scene_variant),
                )
                break
            except RuntimeError as exc:
                last_error = exc
        if dataset is None:
            raise RuntimeError("failed to generate organic-structure branch-point instance") from last_error

        query_id, query_id_probabilities = _resolve_query_id(
            params,
            gen_defaults,
            instance_seed=int(instance_seed),
            task_id=BRANCH_POINT_COUNT_TASK_ID,
            supported_query_ids=BRANCH_POINT_QUERY_IDS,
        )
        render_params = _resolve_render_params(params, render_defaults, instance_seed=int(instance_seed), task_id=BRANCH_POINT_COUNT_TASK_ID)
        scene_style, scene_style_meta = resolve_symbolic_scene_style(
            instance_seed=int(instance_seed),
            namespace=f"{BRANCH_POINT_COUNT_TASK_ID}.organic_structure_background",
        )
        render_params = replace(
            render_params,
            panel_fill_rgb=(253, 252, 247),
            panel_border_rgb=(88, 88, 88),
            bond_rgb=(24, 25, 27),
            annotation_rgb=(160, 164, 168),
        )
        background, background_meta = make_symbolic_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=scene_style,
        )
        rendered_scene = _render_scene(
            background,
            dataset=dataset,
            render_params=render_params,
            instance_seed=int(instance_seed),
            task_id=BRANCH_POINT_COUNT_TASK_ID,
        )
        image, post_noise_meta = apply_post_image_noise(rendered_scene.image, instance_seed=int(instance_seed), params=params, default_config=POST_IMAGE_NOISE_DEFAULTS)
        prompt, prompt_variants, prompt_meta = _build_prompt(
            dataset=dataset,
            prompt_defaults=prompt_defaults,
            instance_seed=int(instance_seed),
            task_id=BRANCH_POINT_COUNT_TASK_ID,
        )
        annotation_points = [
            [round(float(value), 3) for value in rendered_scene.item_points[str(item_id)]]
            for item_id in dataset.annotation_item_ids
        ]
        answer_gt = TypedValue(type="integer", value=int(dataset.answer_value))
        annotation_gt = TypedValue(type="point_set", value=list(annotation_points))

        atom_degrees = {str(atom.item_id): 0 for atom in dataset.structure.atoms}
        for bond in dataset.structure.bonds:
            atom_degrees[str(dataset.structure.atoms[int(bond.atom_a)].item_id)] += 1
            atom_degrees[str(dataset.structure.atoms[int(bond.atom_b)].item_id)] += 1

        query_params = {
            "query_id": str(query_id),
            "query_id_probabilities": dict(query_id_probabilities),
            "scene_id": SCENE_ID,
            "scene_variant": str(scene_variant),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "answer_support": list(dataset.target_answer_support),
            "target_answer_support": list(dataset.target_answer_support),
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": SCENE_ID,
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(dataset.query_id),
                    "internal_query_id": str(dataset.query_id),
                    "scene_id": SCENE_ID,
                    "scene_variant": str(scene_variant),
                    "answer_value": int(dataset.answer_value),
                    "scaffold_id": str(dataset.structure.scaffold_id),
                    "scaffold_family": str(dataset.structure.scaffold_family),
                },
            },
            "query_spec": {
                "query_id": str(dataset.query_id),
                "internal_query_id": str(dataset.query_id),
                "template_id": str(prompt_meta["bundle_id"]),
                "prompt_variant": dict(prompt_meta["prompt_variant"]),
                "prompt_variant_active_key": str(prompt_meta["prompt_variant_active_key"]),
                "prompt_variants": dict(prompt_meta["prompt_variants_for_trace"]),
                "params": dict(query_params),
            },
            "render_spec": {
                "scene_id": SCENE_ID,
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "scene_style": dict(scene_style_meta),
                "organic_style": dict(rendered_scene.style_metadata),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "unit_size_jitter": dict(render_params.unit_size_jitter),
                "layout_jitter": dict(rendered_scene.layout_jitter),
            },
            "render_map": with_symbolic_unit_size_jitter(
                {
                    "image_id": "img0",
                    "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                    "item_bboxes_px": {str(key): list(value) for key, value in rendered_scene.item_bboxes.items()},
                    "bond_point_pairs_px": {
                        str(key): [list(point) for point in value]
                        for key, value in rendered_scene.item_point_pairs.items()
                    },
                    "atom_points_px": {str(key): list(value) for key, value in rendered_scene.item_points.items()},
                    "annotation_source": "atom_points_px",
                    "layout_jitter": dict(rendered_scene.layout_jitter),
                },
                render_params.unit_size_jitter,
            ),
            "execution_trace": {
                **dict(query_params),
                "answer_value": int(dataset.answer_value),
                "answer_type": "integer",
                "annotation_item_ids": [str(item) for item in dataset.annotation_item_ids],
                "branch_point_item_ids": [str(item) for item in dataset.annotation_item_ids],
                "organic_metadata": dict(dataset.metadata),
                "atoms": [
                    {
                        "item_id": atom.item_id,
                        "element": atom.element,
                        "implicit": bool(atom.implicit),
                        "degree": int(atom_degrees[str(atom.item_id)]),
                        "is_branch_point": str(atom.item_id) in set(dataset.annotation_item_ids),
                        "x": round(float(atom.x), 6),
                        "y": round(float(atom.y), 6),
                    }
                    for atom in dataset.structure.atoms
                ],
                "bonds": [
                    {
                        "item_id": bond.item_id,
                        "from_vertex": int(bond.atom_a),
                        "to_vertex": int(bond.atom_b),
                        "from_atom": int(bond.atom_a),
                        "to_atom": int(bond.atom_b),
                        "bond_order": bond.order,
                        "bond_role": bond.role,
                        "ring_index": None if bond.ring_index is None else int(bond.ring_index),
                    }
                    for bond in dataset.structure.bonds
                ],
                "ring_vertex_sets": [[int(idx) for idx in ring] for ring in dataset.structure.ring_atom_sets],
                "question_format": str(dataset.query_id),
            },
            "witness_symbolic": {"type": "point_set", "value": list(annotation_points)},
            "projected_annotation": {"type": "point_set", "point_set": list(annotation_points), "value": list(annotation_points)},
            "answer_gt": answer_gt.to_dict(),
            "annotation_gt": annotation_gt.to_dict(),
        }
        return TaskOutput(
            prompt=str(prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(dataset.query_id),
            prompt_variants=dict(prompt_variants),
        )


@register_task
class SymbolicRingSizeCountTask:
    """Count pentagonal or hexagonal rings in an organic-structure notation panel."""

    task_id = RING_SIZE_COUNT_TASK_ID
    domain = "symbolic"
    scene_id = "notation"
    supported_query_ids = RING_SIZE_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(
            params,
            gen_defaults,
            instance_seed=int(instance_seed),
            task_id=RING_SIZE_COUNT_TASK_ID,
        )
        dataset: _Dataset | None = None
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            try:
                dataset = _build_ring_size_dataset(
                    params=params,
                    gen_defaults=gen_defaults,
                    instance_seed=int(instance_seed) + int(attempt_index),
                    scene_variant=str(scene_variant),
                )
                break
            except RuntimeError as exc:
                last_error = exc
        if dataset is None:
            raise RuntimeError("failed to generate organic-structure ring-size instance") from last_error

        query_id, query_id_probabilities = _resolve_query_id(
            params,
            gen_defaults,
            instance_seed=int(instance_seed),
            task_id=RING_SIZE_COUNT_TASK_ID,
            supported_query_ids=RING_SIZE_QUERY_IDS,
        )
        target_ring_size, target_ring_size_probabilities = _resolve_target_ring_size(
            params,
            gen_defaults,
            instance_seed=int(instance_seed),
            task_id=RING_SIZE_COUNT_TASK_ID,
        )
        render_params = _resolve_render_params(params, render_defaults, instance_seed=int(instance_seed), task_id=RING_SIZE_COUNT_TASK_ID)
        scene_style, scene_style_meta = resolve_symbolic_scene_style(
            instance_seed=int(instance_seed),
            namespace=f"{RING_SIZE_COUNT_TASK_ID}.organic_structure_background",
        )
        render_params = replace(
            render_params,
            panel_fill_rgb=(253, 252, 247),
            panel_border_rgb=(88, 88, 88),
            bond_rgb=(24, 25, 27),
            annotation_rgb=(160, 164, 168),
        )
        background, background_meta = make_symbolic_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=scene_style,
        )
        rendered_scene = _render_scene(
            background,
            dataset=dataset,
            render_params=render_params,
            instance_seed=int(instance_seed),
            task_id=RING_SIZE_COUNT_TASK_ID,
        )
        image, post_noise_meta = apply_post_image_noise(rendered_scene.image, instance_seed=int(instance_seed), params=params, default_config=POST_IMAGE_NOISE_DEFAULTS)
        prompt, prompt_variants, prompt_meta = _build_prompt(
            dataset=dataset,
            prompt_defaults=prompt_defaults,
            instance_seed=int(instance_seed),
            task_id=RING_SIZE_COUNT_TASK_ID,
        )
        annotation_bboxes = [
            [round(float(value), 3) for value in rendered_scene.item_bboxes[str(item_id)]]
            for item_id in dataset.annotation_item_ids
        ]
        answer_gt = TypedValue(type="integer", value=int(dataset.answer_value))
        annotation_gt = TypedValue(type="bbox_set", value=list(annotation_bboxes))

        ring_bboxes = {
            f"ring_{ring_index + 1:02d}": list(rendered_scene.item_bboxes[f"ring_{ring_index + 1:02d}"])
            for ring_index in range(len(dataset.structure.ring_atom_sets))
        }
        query_params = {
            "query_id": str(query_id),
            "query_id_probabilities": dict(query_id_probabilities),
            "scene_id": SCENE_ID,
            "scene_variant": str(scene_variant),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "target_ring_size": int(target_ring_size),
            "target_ring_name": _ring_size_name(int(target_ring_size)),
            "target_ring_size_probabilities": dict(target_ring_size_probabilities),
            "answer_support": list(dataset.target_answer_support),
            "target_answer_support": list(dataset.target_answer_support),
        }
        annotation_set = set(dataset.annotation_item_ids)
        trace_payload = {
            "scene_ir": {
                "scene_kind": SCENE_ID,
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(dataset.query_id),
                    "internal_query_id": str(dataset.query_id),
                    "scene_id": SCENE_ID,
                    "scene_variant": str(scene_variant),
                    "target_ring_size": int(target_ring_size),
                    "answer_value": int(dataset.answer_value),
                    "scaffold_id": str(dataset.structure.scaffold_id),
                    "scaffold_family": str(dataset.structure.scaffold_family),
                },
            },
            "query_spec": {
                "query_id": str(dataset.query_id),
                "internal_query_id": str(dataset.query_id),
                "template_id": str(prompt_meta["bundle_id"]),
                "prompt_variant": dict(prompt_meta["prompt_variant"]),
                "prompt_variant_active_key": str(prompt_meta["prompt_variant_active_key"]),
                "prompt_variants": dict(prompt_meta["prompt_variants_for_trace"]),
                "params": dict(query_params),
            },
            "render_spec": {
                "scene_id": SCENE_ID,
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "scene_style": dict(scene_style_meta),
                "organic_style": dict(rendered_scene.style_metadata),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "unit_size_jitter": dict(render_params.unit_size_jitter),
                "layout_jitter": dict(rendered_scene.layout_jitter),
            },
            "render_map": with_symbolic_unit_size_jitter(
                {
                    "image_id": "img0",
                    "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                    "item_bboxes_px": {str(key): list(value) for key, value in rendered_scene.item_bboxes.items()},
                    "ring_bboxes_px": dict(ring_bboxes),
                    "bond_point_pairs_px": {
                        str(key): [list(point) for point in value]
                        for key, value in rendered_scene.item_point_pairs.items()
                    },
                    "atom_points_px": {str(key): list(value) for key, value in rendered_scene.item_points.items()},
                    "annotation_source": "item_bboxes_px",
                    "layout_jitter": dict(rendered_scene.layout_jitter),
                },
                render_params.unit_size_jitter,
            ),
            "execution_trace": {
                **dict(query_params),
                "answer_value": int(dataset.answer_value),
                "answer_type": "integer",
                "annotation_item_ids": [str(item) for item in dataset.annotation_item_ids],
                "matching_ring_item_ids": [str(item) for item in dataset.annotation_item_ids],
                "organic_metadata": dict(dataset.metadata),
                "atoms": [
                    {
                        "item_id": atom.item_id,
                        "element": atom.element,
                        "implicit": bool(atom.implicit),
                        "x": round(float(atom.x), 6),
                        "y": round(float(atom.y), 6),
                    }
                    for atom in dataset.structure.atoms
                ],
                "bonds": [
                    {
                        "item_id": bond.item_id,
                        "from_vertex": int(bond.atom_a),
                        "to_vertex": int(bond.atom_b),
                        "from_atom": int(bond.atom_a),
                        "to_atom": int(bond.atom_b),
                        "bond_order": bond.order,
                        "bond_role": bond.role,
                        "ring_index": None if bond.ring_index is None else int(bond.ring_index),
                    }
                    for bond in dataset.structure.bonds
                ],
                "rings": [
                    {
                        "item_id": f"ring_{ring_index + 1:02d}",
                        "ring_size": int(len(ring_atoms)),
                        "atom_ids": [str(dataset.structure.atoms[int(idx)].item_id) for idx in ring_atoms],
                        "atom_indices": [int(idx) for idx in ring_atoms],
                        "is_target_ring": f"ring_{ring_index + 1:02d}" in annotation_set,
                    }
                    for ring_index, ring_atoms in enumerate(dataset.structure.ring_atom_sets)
                ],
                "ring_vertex_sets": [[int(idx) for idx in ring] for ring in dataset.structure.ring_atom_sets],
                "question_format": str(dataset.query_id),
            },
            "witness_symbolic": {"type": "bbox_set", "value": list(annotation_bboxes)},
            "projected_annotation": {
                "type": "bbox_set",
                "bbox_set": list(annotation_bboxes),
                "pixel_bbox_set": list(annotation_bboxes),
                "value": list(annotation_bboxes),
            },
            "answer_gt": answer_gt.to_dict(),
            "annotation_gt": annotation_gt.to_dict(),
        }
        return TaskOutput(
            prompt=str(prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(dataset.query_id),
            prompt_variants=dict(prompt_variants),
        )


__all__ = [
    "BOND_ORDER_COUNT_QUERY_ID",
    "BOND_ORDER_COUNT_TASK_ID",
    "BRANCH_POINT_COUNT_QUERY_ID",
    "BRANCH_POINT_COUNT_TASK_ID",
    "SymbolicBranchPointCountTask",
    "SymbolicBondOrderCountTask",
    "SymbolicRingSizeCountTask",
    "RING_SIZE_COUNT_QUERY_ID",
    "RING_SIZE_COUNT_TASK_ID",
    "SCENE_ID",
    "TARGET_BOND_ORDERS",
    "TARGET_RING_SIZES",
    "TASK_ID",
]
