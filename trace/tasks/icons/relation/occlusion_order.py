"""Count scene-grid cells whose front-to-back icon order matches the Reference."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_generation_rendering_prompt_defaults,
)
from ...shared.counting_sampling import counting_complexity_score, resolve_counting_target_and_distractor_triplet
from ...shared.labeling import LABEL_POOL_A_L, assign_shuffled_labels
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.icon_assets import resolve_icon_pool
from ..shared.defaults import ICON_SHARED_DEFAULTS
from ..shared.icon_overlap_grid_scene import IconOverlapPairSpec, render_two_panel_icon_overlap_grid_scene
from ..shared.icon_scene import IconInstanceSpec, panel_geometry_to_trace
from ..shared.icon_task_rendering import resolve_icon_render_params, sample_icon_instance_noise
from ...shared.color_distance import color_distance
from ..shared.icon_style import icon_palette_meets_distance_constraints, sample_icon_palette
from ..shared.icon_noise import default_icon_noise_value_ranges


_ORDER_MATCH_VARIANT = "same_front_to_back_order"


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for occlusion-order counting scenes."""

    object_count_min: int = 2
    object_count_max: int = 12
    target_count_min: int = 0
    target_count_max: int = 6
    distractor_count_min: int = 1
    distractor_count_max: int = 6
    canvas_width: int = 1104
    canvas_height: int = 640
    reference_panel_width_px: int = 296
    panel_gap_px: int = ICON_SHARED_DEFAULTS.panel_gap_px
    outer_margin_px: int = ICON_SHARED_DEFAULTS.outer_margin_px
    panel_padding_px: int = ICON_SHARED_DEFAULTS.panel_padding_px
    panel_corner_radius_px: int = ICON_SHARED_DEFAULTS.panel_corner_radius_px
    scene_icon_size_min_px: int = ICON_SHARED_DEFAULTS.scene_icon_size_min_px
    scene_icon_size_max_px: int = ICON_SHARED_DEFAULTS.scene_icon_size_max_px
    reference_icon_size_px: int = 110
    panel_title_font_size_px: int = ICON_SHARED_DEFAULTS.panel_title_font_size_px
    cell_padding_px: int = 10
    cell_border_rgb: Tuple[int, int, int] = (218, 223, 233)
    cell_label_color_rgb: Tuple[int, int, int] = (52, 60, 77)
    cell_label_font_size_px: int = 22
    pool_manifest: str = "all_icons.txt"
    palette_size_min: int = 8
    palette_size_max: int = 12
    color_channel_min: int = 24
    color_channel_max: int = 220
    min_color_distance: float = 40.0
    pair_min_color_distance: float = 80.0
    color_distance_space: str = "lab"
    background_color_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.background_color_rgb
    panel_fill_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_fill_rgb
    panel_border_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_border_rgb
    header_text_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.header_text_rgb
    overlap_ratio_range: Tuple[float, float] = (0.40, 0.60)
    icon_noise_edit_types: Tuple[str, ...] = ICON_SHARED_DEFAULTS.icon_noise_edit_types
    icon_noise_edit_count_range: Tuple[int, int] = ICON_SHARED_DEFAULTS.icon_noise_edit_count_range
    icon_noise_value_ranges: Dict[str, Dict[str, Tuple[float, float]]] = field(
        default_factory=default_icon_noise_value_ranges
    )


@dataclass(frozen=True)
class _ScenePayload:
    """Trace-ready payload for one occlusion-order scene."""

    object_count: int
    target_count: int
    distractor_count: int
    reference_order_id: str
    icon_a_id: str
    icon_b_id: str
    cell_labels: Tuple[str, ...]
    matching_labels: Tuple[str, ...]
    cell_order_ids: Tuple[str, ...]
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...]
    panel_geometry: Dict[str, Any]
    reference_pair: Dict[str, Any]
    scene_cells: Tuple[Dict[str, Any], ...]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("icons", "relation")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id="task_icons_relation_occlusion_order",
)


def _resolve_render_params(params: Mapping[str, Any]) -> Dict[str, Any]:
    """Resolve render params for the occlusion-order grid task."""

    render_params = resolve_icon_render_params(
        params=params,
        render_defaults=_RENDER_DEFAULTS,
        fallback_defaults=_DEFAULTS,
    )
    render_params["cell_padding_px"] = int(
        params.get("cell_padding_px", group_default(_RENDER_DEFAULTS, "cell_padding_px", _DEFAULTS.cell_padding_px))
    )
    render_params["cell_border_rgb"] = tuple(
        params.get("cell_border_rgb", group_default(_RENDER_DEFAULTS, "cell_border_rgb", _DEFAULTS.cell_border_rgb))
    )
    render_params["cell_label_color_rgb"] = tuple(
        params.get(
            "cell_label_color_rgb",
            group_default(_RENDER_DEFAULTS, "cell_label_color_rgb", _DEFAULTS.cell_label_color_rgb),
        )
    )
    render_params["cell_label_font_size_px"] = int(
        params.get(
            "cell_label_font_size_px",
            group_default(_RENDER_DEFAULTS, "cell_label_font_size_px", _DEFAULTS.cell_label_font_size_px),
        )
    )
    render_params["pair_min_color_distance"] = float(
        params.get(
            "pair_min_color_distance",
            group_default(_RENDER_DEFAULTS, "pair_min_color_distance", _DEFAULTS.pair_min_color_distance),
        )
    )
    raw_overlap_range = params.get(
        "overlap_ratio_range",
        group_default(_RENDER_DEFAULTS, "overlap_ratio_range", list(_DEFAULTS.overlap_ratio_range)),
    )
    if not isinstance(raw_overlap_range, (list, tuple)) or len(raw_overlap_range) < 2:
        raise ValueError("overlap_ratio_range must contain two numeric bounds")
    overlap_min = max(0.0, min(0.95, float(raw_overlap_range[0])))
    overlap_max = max(overlap_min, min(0.95, float(raw_overlap_range[1])))
    render_params["overlap_ratio_range"] = (float(overlap_min), float(overlap_max))
    return render_params


def _sample_tint_pair(
    rng,
    *,
    palette: Sequence[Tuple[int, int, int]],
    pair_min_color_distance: float,
    distance_space: str,
) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    """Sample two distinct icon tints from one already-separated palette."""

    if len(palette) < 2:
        raise ValueError("occlusion task requires at least two palette colors")
    qualifying_pairs = [
        (left, right)
        for left_index, left in enumerate(palette)
        for right in palette[left_index + 1 :]
        if float(color_distance(left, right, distance_space=str(distance_space))) >= float(pair_min_color_distance)
    ]
    if not qualifying_pairs:
        raise ValueError("occlusion task palette resolved no pair with sufficient color separation")
    first, second = rng.choice(qualifying_pairs)
    if bool(rng.randint(0, 1)):
        first, second = second, first
    return tuple(int(channel) for channel in first), tuple(int(channel) for channel in second)


def _sample_overlap_offsets(
    rng,
    *,
    overlap_ratio_range: Sequence[float],
    max_offset_frac: float = 0.45,
) -> Tuple[float, float, float]:
    """Sample normalized icon offsets whose nominal overlap stays in the requested range."""

    overlap_min = max(0.0, min(0.95, float(overlap_ratio_range[0])))
    overlap_max = max(overlap_min, min(0.95, float(overlap_ratio_range[1])))
    for _ in range(120):
        dx_abs = float(rng.uniform(0.08, float(max_offset_frac)))
        dy_abs = float(rng.uniform(0.08, float(max_offset_frac)))
        overlap_ratio = float((1.0 - dx_abs) * (1.0 - dy_abs))
        if overlap_min <= overlap_ratio <= overlap_max:
            dx = dx_abs * float(rng.choice((-1.0, 1.0)))
            dy = dy_abs * float(rng.choice((-1.0, 1.0)))
            return float(dx), float(dy), float(overlap_ratio)
    target = 0.5 * float(overlap_min + overlap_max)
    dx_abs = min(float(max_offset_frac), max(0.08, 1.0 - target))
    dy_abs = min(float(max_offset_frac), max(0.08, 1.0 - (target / max(1e-6, 1.0 - dx_abs))))
    overlap_ratio = float((1.0 - dx_abs) * (1.0 - dy_abs))
    return (
        float(dx_abs * float(rng.choice((-1.0, 1.0)))),
        float(dy_abs * float(rng.choice((-1.0, 1.0)))),
        float(overlap_ratio),
    )


def _order_id_for_front_role(front_role: str) -> str:
    """Return a stable order id from one front-role token."""

    if str(front_role) == "a":
        return "a_over_b"
    if str(front_role) == "b":
        return "b_over_a"
    raise ValueError(f"unsupported front_role: {front_role}")


def _occlusion_style_trace(
    *,
    render_params: Mapping[str, Any],
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...],
) -> Dict[str, Any]:
    """Return the canonical render-style trace block for occlusion-order grids."""

    return {
        "background_color_rgb": list(render_params["background_color_rgb"]),
        "panel_fill_rgb": list(render_params["panel_fill_rgb"]),
        "panel_border_rgb": list(render_params["panel_border_rgb"]),
        "header_text_rgb": list(render_params["header_text_rgb"]),
        "sampled_palette_rgb": [list(color) for color in sampled_palette_rgb],
        "color_channel_min": int(render_params["color_channel_min"]),
        "color_channel_max": int(render_params["color_channel_max"]),
        "min_color_distance": float(render_params["min_color_distance"]),
        "pair_min_color_distance": float(render_params["pair_min_color_distance"]),
        "color_distance_space": str(render_params["color_distance_space"]),
        "overlap_ratio_range": [
            float(render_params["overlap_ratio_range"][0]),
            float(render_params["overlap_ratio_range"][1]),
        ],
        "cell_padding_px": int(render_params["cell_padding_px"]),
        "cell_border_rgb": list(render_params["cell_border_rgb"]),
        "cell_label_color_rgb": list(render_params["cell_label_color_rgb"]),
        "cell_label_font_size_px": int(render_params["cell_label_font_size_px"]),
        "icon_noise_edit_types": [str(value) for value in render_params["icon_noise_edit_types"]],
        "icon_noise_edit_count_range": [
            int(render_params["icon_noise_edit_count_range"][0]),
            int(render_params["icon_noise_edit_count_range"][1]),
        ],
        "icon_noise_value_ranges": {
            str(edit_type): {
                str(param): [float(bounds[0]), float(bounds[1])]
                for param, bounds in params.items()
            }
            for edit_type, params in render_params["icon_noise_value_ranges"].items()
        },
    }


def _sample_scene(
    rng,
    *,
    instance_seed: int,
    object_count: int,
    target_count: int,
    pool_manifest: str,
    render_params: Mapping[str, Any],
) -> Tuple[_ScenePayload, Any]:
    """Sample and render one occlusion-order counting scene."""

    pool = list(resolve_icon_pool(str(pool_manifest)))
    if len(pool) < 2:
        raise ValueError("icon pool is too small for occlusion-order scene")
    icon_a_id, icon_b_id = rng.sample(pool, 2)
    reference_front_role = str(rng.choice(("a", "b")))
    reference_order_id = _order_id_for_front_role(reference_front_role)
    labels = assign_shuffled_labels(rng, object_count=int(object_count), label_pool=LABEL_POOL_A_L)
    match_indices = set(rng.sample(list(range(int(object_count))), int(target_count)))

    palette_size = int(
        rng.randint(
            int(render_params["palette_size_min"]),
            int(render_params["palette_size_max"]),
        )
    )
    sampled_palette_rgb = tuple(
        tuple(int(channel) for channel in color)
        for color in sample_icon_palette(
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
    )
    if not icon_palette_meets_distance_constraints(
        palette=sampled_palette_rgb,
        anchor_colors=(
            tuple(int(v) for v in render_params["background_color_rgb"]),
            tuple(int(v) for v in render_params["panel_fill_rgb"]),
            tuple(int(v) for v in render_params["panel_border_rgb"]),
            tuple(int(v) for v in render_params["header_text_rgb"]),
        ),
        min_color_distance=float(render_params["min_color_distance"]),
        distance_space=str(render_params["color_distance_space"]),
        ):
        raise ValueError("sampled occlusion palette did not satisfy strict distance constraints")

    reference_a_tint, reference_b_tint = _sample_tint_pair(
        rng,
        palette=sampled_palette_rgb,
        pair_min_color_distance=float(render_params["pair_min_color_distance"]),
        distance_space=str(render_params["color_distance_space"]),
    )
    reference_dx_frac, reference_dy_frac, reference_overlap_ratio = _sample_overlap_offsets(
        rng,
        overlap_ratio_range=render_params["overlap_ratio_range"],
    )
    reference_a_noise_edits, reference_a_noise_seed = sample_icon_instance_noise(
        instance_seed=int(instance_seed),
        namespace=f"{IconsRelationOcclusionOrderTask.task_id}:reference_a",
        render_params=render_params,
    )
    reference_b_noise_edits, reference_b_noise_seed = sample_icon_instance_noise(
        instance_seed=int(instance_seed),
        namespace=f"{IconsRelationOcclusionOrderTask.task_id}:reference_b",
        render_params=render_params,
    )
    reference_pair = IconOverlapPairSpec(
        icon_a=IconInstanceSpec(
            icon_id=str(icon_a_id),
            tint_rgb=tuple(int(v) for v in reference_a_tint),
            noise_edits=tuple(reference_a_noise_edits),
            noise_seed=int(reference_a_noise_seed),
        ),
        icon_b=IconInstanceSpec(
            icon_id=str(icon_b_id),
            tint_rgb=tuple(int(v) for v in reference_b_tint),
            noise_edits=tuple(reference_b_noise_edits),
            noise_seed=int(reference_b_noise_seed),
        ),
        front_role=str(reference_front_role),
        offset_dx_frac=float(reference_dx_frac),
        offset_dy_frac=float(reference_dy_frac),
        overlap_ratio=float(reference_overlap_ratio),
    )

    scene_pairs: List[IconOverlapPairSpec] = []
    cell_order_ids: List[str] = []
    matching_labels: List[str] = []
    for index, label in enumerate(labels):
        front_role = str(reference_front_role if int(index) in match_indices else ("b" if str(reference_front_role) == "a" else "a"))
        if int(index) in match_indices:
            matching_labels.append(str(label))
        icon_a_tint, icon_b_tint = _sample_tint_pair(
            rng,
            palette=sampled_palette_rgb,
            pair_min_color_distance=float(render_params["pair_min_color_distance"]),
            distance_space=str(render_params["color_distance_space"]),
        )
        dx_frac, dy_frac, overlap_ratio = _sample_overlap_offsets(
            rng,
            overlap_ratio_range=render_params["overlap_ratio_range"],
        )
        icon_a_noise_edits, icon_a_noise_seed = sample_icon_instance_noise(
            instance_seed=int(instance_seed),
            namespace=f"{IconsRelationOcclusionOrderTask.task_id}:scene_{int(index)}_a",
            render_params=render_params,
        )
        icon_b_noise_edits, icon_b_noise_seed = sample_icon_instance_noise(
            instance_seed=int(instance_seed),
            namespace=f"{IconsRelationOcclusionOrderTask.task_id}:scene_{int(index)}_b",
            render_params=render_params,
        )
        scene_pairs.append(
            IconOverlapPairSpec(
                icon_a=IconInstanceSpec(
                    icon_id=str(icon_a_id),
                    tint_rgb=tuple(int(v) for v in icon_a_tint),
                    noise_edits=tuple(icon_a_noise_edits),
                    noise_seed=int(icon_a_noise_seed),
                ),
                icon_b=IconInstanceSpec(
                    icon_id=str(icon_b_id),
                    tint_rgb=tuple(int(v) for v in icon_b_tint),
                    noise_edits=tuple(icon_b_noise_edits),
                    noise_seed=int(icon_b_noise_seed),
                ),
                front_role=str(front_role),
                offset_dx_frac=float(dx_frac),
                offset_dy_frac=float(dy_frac),
                overlap_ratio=float(overlap_ratio),
            )
        )
        cell_order_ids.append(_order_id_for_front_role(front_role))

    rendered = render_two_panel_icon_overlap_grid_scene(
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
        cell_label_font_size_px=int(render_params["cell_label_font_size_px"]),
        panel_title_font_size_px=int(render_params["panel_title_font_size_px"]),
        background_rgb=tuple(int(v) for v in render_params["background_color_rgb"]),
        panel_fill_rgb=tuple(int(v) for v in render_params["panel_fill_rgb"]),
        panel_border_rgb=tuple(int(v) for v in render_params["panel_border_rgb"]),
        title_color_rgb=tuple(int(v) for v in render_params["header_text_rgb"]),
        cell_border_rgb=tuple(int(v) for v in render_params["cell_border_rgb"]),
        cell_label_color_rgb=tuple(int(v) for v in render_params["cell_label_color_rgb"]),
    )

    reference_payload = {
        "panel": "reference",
        "icon_a_id": str(rendered.reference_pair.icon_a_id),
        "icon_b_id": str(rendered.reference_pair.icon_b_id),
        "front_role": str(rendered.reference_pair.front_role),
        "order_id": str(reference_order_id),
        "overlap_ratio": float(rendered.reference_pair.overlap_ratio),
        "icon_a_bbox_xyxy": list(rendered.reference_pair.icon_a_bbox_xyxy),
        "icon_b_bbox_xyxy": list(rendered.reference_pair.icon_b_bbox_xyxy),
        "icon_a_tint_rgb": list(rendered.reference_pair.icon_a_tint_rgb),
        "icon_b_tint_rgb": list(rendered.reference_pair.icon_b_tint_rgb),
        "icon_a_noise_edits": [dict(edit) for edit in rendered.reference_pair.icon_a_noise_edits],
        "icon_a_noise_seed": None
        if rendered.reference_pair.icon_a_noise_seed is None
        else int(rendered.reference_pair.icon_a_noise_seed),
        "icon_b_noise_edits": [dict(edit) for edit in rendered.reference_pair.icon_b_noise_edits],
        "icon_b_noise_seed": None
        if rendered.reference_pair.icon_b_noise_seed is None
        else int(rendered.reference_pair.icon_b_noise_seed),
    }
    scene_cells = tuple(
        {
            "panel": "scene",
            "label": str(cell.label),
            "icon_a_id": str(cell.icon_a_id),
            "icon_b_id": str(cell.icon_b_id),
            "front_role": str(cell.front_role),
            "order_id": str(_order_id_for_front_role(str(cell.front_role))),
            "overlap_ratio": float(cell.overlap_ratio),
            "cell_bbox_xyxy": list(cell.cell_bbox_xyxy),
            "icon_a_bbox_xyxy": list(cell.icon_a_bbox_xyxy),
            "icon_b_bbox_xyxy": list(cell.icon_b_bbox_xyxy),
            "icon_a_tint_rgb": list(cell.icon_a_tint_rgb),
            "icon_b_tint_rgb": list(cell.icon_b_tint_rgb),
            "icon_a_noise_edits": [dict(edit) for edit in cell.icon_a_noise_edits],
            "icon_a_noise_seed": None if cell.icon_a_noise_seed is None else int(cell.icon_a_noise_seed),
            "icon_b_noise_edits": [dict(edit) for edit in cell.icon_b_noise_edits],
            "icon_b_noise_seed": None if cell.icon_b_noise_seed is None else int(cell.icon_b_noise_seed),
            "is_match": bool(str(cell.label) in set(matching_labels)),
            "index": int(index),
        }
        for index, cell in enumerate(rendered.scene_cells)
    )
    return _ScenePayload(
        object_count=int(object_count),
        target_count=int(target_count),
        distractor_count=int(object_count) - int(target_count),
        reference_order_id=str(reference_order_id),
        icon_a_id=str(icon_a_id),
        icon_b_id=str(icon_b_id),
        cell_labels=tuple(str(value) for value in labels),
        matching_labels=tuple(sorted(str(value) for value in matching_labels)),
        cell_order_ids=tuple(str(value) for value in cell_order_ids),
        sampled_palette_rgb=tuple(sampled_palette_rgb),
        panel_geometry=panel_geometry_to_trace(rendered.layout),
        reference_pair=reference_payload,
        scene_cells=scene_cells,
    ), rendered.image


@register_task
class IconsRelationOcclusionOrderTask:
    """Count labeled scene cells that match the Reference front-to-back icon order."""

    task_id = "task_icons_relation_occlusion_order"
    domain = "icons"
    task_group = "relation"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic icon occlusion-order instance."""

        scene_rng = spawn_rng(int(instance_seed), "scene")
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
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            fallback_total_min=_DEFAULTS.object_count_min,
            fallback_total_max=_DEFAULTS.object_count_max,
            fallback_target_min=_DEFAULTS.target_count_min,
            fallback_target_max=_DEFAULTS.target_count_max,
            fallback_distractor_min=_DEFAULTS.distractor_count_min,
            fallback_distractor_max=_DEFAULTS.distractor_count_max,
        )
        render_params = _resolve_render_params(params)
        pool_manifest = str(params.get("pool_manifest", group_default(_GEN_DEFAULTS, "pool_manifest", _DEFAULTS.pool_manifest)))

        scene_payload = None
        image = None
        last_error: Exception | None = None
        for _ in range(max(1, int(max_attempts))):
            try:
                scene_payload, image = _sample_scene(
                    scene_rng,
                    instance_seed=int(instance_seed),
                    object_count=int(object_count),
                    target_count=int(target_count),
                    pool_manifest=str(pool_manifest),
                    render_params=render_params,
                )
                break
            except Exception as exc:
                last_error = exc
                continue
        if scene_payload is None or image is None:
            raise RuntimeError("failed to generate task_icons_relation_occlusion_order instance") from last_error

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "task_family_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "question_text",
                "evidence_hint",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            task_family_key=str(prompt_defaults["task_family_key"]),
            task_key=str(prompt_defaults["task_key"]),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "question_text": str(prompt_defaults["question_text"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        evidence_labels = list(scene_payload.matching_labels)
        answer_gt = TypedValue(type="integer", value=int(scene_payload.target_count))
        evidence_gt = TypedValue(type="label_set", value=list(evidence_labels))
        trace_payload = {
            "scene_ir": {
                "scene_kind": "icons_reference_grid_occlusion_order_count",
                "entities": [dict(scene_payload.reference_pair), *[dict(item) for item in scene_payload.scene_cells]],
                "relations": {
                    "counting_target": "same_front_to_back_order_as_reference",
                    "reference_order_id": str(scene_payload.reference_order_id),
                    "matching_cell_labels": list(scene_payload.matching_labels),
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(scene_payload.panel_geometry),
                },
            },
            "query_spec": {
                "task_variant": _ORDER_MATCH_VARIANT,
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "object_count": int(object_count),
                    "object_count_probabilities": dict(object_count_probabilities),
                    "target_count": int(target_count),
                    "target_count_probabilities": dict(target_count_probabilities),
                    "distractor_count": int(distractor_count),
                    "distractor_count_probabilities": dict(distractor_count_probabilities),
                    "pool_manifest": str(pool_manifest),
                },
            },
            "render_spec": {
                "canvas_size": [int(render_params["canvas_width"]), int(render_params["canvas_height"])],
                "coord_space": "pixel",
                "panel_geometry": dict(scene_payload.panel_geometry),
                "style": _occlusion_style_trace(
                    render_params=render_params,
                    sampled_palette_rgb=scene_payload.sampled_palette_rgb,
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
                "scene_variant": "reference_overlap_grid",
                "task_variant": _ORDER_MATCH_VARIANT,
                "object_count": int(scene_payload.object_count),
                "object_count_probabilities": dict(object_count_probabilities),
                "target_count": int(scene_payload.target_count),
                "target_count_probabilities": dict(target_count_probabilities),
                "distractor_count": int(scene_payload.distractor_count),
                "distractor_count_probabilities": dict(distractor_count_probabilities),
                "reference_order_id": str(scene_payload.reference_order_id),
                "icon_a_id": str(scene_payload.icon_a_id),
                "icon_b_id": str(scene_payload.icon_b_id),
                "cell_labels": list(scene_payload.cell_labels),
                "matching_cell_labels": list(scene_payload.matching_labels),
                "cell_order_ids": list(scene_payload.cell_order_ids),
                "question_format": "count_scene_cells_matching_reference_occlusion_order",
            },
            "witness_symbolic": {
                "reference_order_id": str(scene_payload.reference_order_id),
                "matching_cell_labels": list(scene_payload.matching_labels),
            },
            "projected_evidence": {
                "label_set": list(scene_payload.matching_labels),
            },
        }
        complexity = TaskComplexity(
            complexity_score=counting_complexity_score(
                object_count=int(scene_payload.object_count),
                target_count=int(scene_payload.target_count),
            ),
            complexity_components={
                "object_count": int(scene_payload.object_count),
                "target_count": int(scene_payload.target_count),
                "task_variant": _ORDER_MATCH_VARIANT,
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
            task_variant=_ORDER_MATCH_VARIANT,
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["IconsRelationOcclusionOrderTask"]
