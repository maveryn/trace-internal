"""Infer the missing icon count in a single-panel arithmetic icon sequence."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.query_ids import SINGLE_QUERY_ID
from ....core.seed import spawn_rng
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, load_scene_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ..shared.defaults import ICON_SHARED_DEFAULTS
from ..shared.icon_scene import (
    IconInstanceSpec,
    serialize_rendered_icon_instance,
    single_panel_geometry_to_trace,
)
from .shared.annotations import scalar_bbox_artifacts
from .shared.rendering import (
    IconSequenceCellSpec,
    render_sequence_scene_from_params,
    validate_sequence_cell_box_bounds,
)
from .shared.prompts import render_sequence_strip_prompt_artifacts
from .shared.sampling import resolve_rotation_candidates, sample_sequence_icon_appearance
from .shared.output import bbox_anchor_render_map, sequence_render_spec
from ..shared.icon_task_rendering import (
    resolve_icon_cell_render_params,
    sample_icon_instance_noise,
)

TASK_ID = "task_icons__sequence_strip__missing_count_value"
DOMAIN = "icons"
SCENE_ID = "sequence_strip"
QUERY_ID = SINGLE_QUERY_ID
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (QUERY_ID,)
PROMPT_QUERY_KEY = "missing_count_value"


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for icon sequence missing-count scenes."""

    sequence_length_min: int = 4
    sequence_length_max: int = 6
    target_count_min: int = 0
    target_count_max: int = 10
    step_abs_min: int = 1
    step_abs_max: int = 3
    canvas_width: int = 1104
    canvas_height: int = ICON_SHARED_DEFAULTS.canvas_height
    outer_margin_px: int = ICON_SHARED_DEFAULTS.outer_margin_px
    panel_padding_px: int = ICON_SHARED_DEFAULTS.panel_padding_px
    panel_corner_radius_px: int = ICON_SHARED_DEFAULTS.panel_corner_radius_px
    scene_icon_size_min_px: int = 24
    scene_icon_size_max_px: int = 40
    cell_box_width_min_px: int = 112
    cell_box_width_max_px: int = 160
    cell_box_height_min_px: int = 96
    cell_box_height_max_px: int = 144
    scene_max_overlap_fraction: float = 0.20
    scene_placement_max_attempts: int = 160
    scene_size_shrink_rounds: int = ICON_SHARED_DEFAULTS.scene_size_shrink_rounds
    scene_size_shrink_factor: float = ICON_SHARED_DEFAULTS.scene_size_shrink_factor
    panel_title_font_size_px: int = ICON_SHARED_DEFAULTS.panel_title_font_size_px
    pool_manifest: str = "all_icons.txt"
    rotation_candidates_degrees: Tuple[int, ...] = (0, 90, 180, 270)
    palette_size_min: int = 1
    palette_size_max: int = 1
    color_channel_min: int = 24
    color_channel_max: int = 220
    min_color_distance: float = 40.0
    color_distance_space: str = "lab"
    background_color_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.background_color_rgb
    panel_fill_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_fill_rgb
    panel_border_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_border_rgb
    header_text_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.header_text_rgb
    cell_padding_px: int = 10
    cell_icon_padding_px: int = 8
    cell_corner_radius_px: int = 12
    cell_border_rgb: Tuple[int, int, int] = (218, 223, 233)
    missing_mark_font_size_px: int = 56
    missing_mark_color_rgb: Tuple[int, int, int] = (84, 96, 118)
    icon_noise_edit_types: Tuple[str, ...] = ICON_SHARED_DEFAULTS.icon_noise_edit_types
    icon_noise_edit_count_range: Tuple[int, int] = ICON_SHARED_DEFAULTS.icon_noise_edit_count_range
    icon_noise_value_ranges: Dict[str, Dict[str, Tuple[float, float]]] = field(
        default_factory=lambda: deepcopy(ICON_SHARED_DEFAULTS.icon_noise_value_ranges)
    )


@dataclass(frozen=True)
class _SequenceSpec:
    """One fully resolved sequence specification."""

    sequence_length: int
    target_count: int
    missing_cell_index: int
    step_delta: int
    step_delta_candidates: Tuple[int, ...]
    full_sequence_counts: Tuple[int, ...]
    sequence_length_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _ScenePayload:
    """Trace-ready payload for one icon sequence missing-count instance."""

    sequence_length: int
    target_count: int
    missing_cell_index: int
    step_delta: int
    full_sequence_counts: Tuple[int, ...]
    sequence_icon_id: str
    scene_rotations_by_cell: Tuple[Tuple[int, ...], ...]
    missing_cell_bbox: Tuple[int, int, int, int]
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...]
    cell_box_width_px: int
    cell_box_height_px: int
    panel_geometry: Dict[str, Any]
    scene_cells: Tuple[Dict[str, Any], ...]
    scene_icon_instances: Tuple[Dict[str, Any], ...]


_DEFAULTS = _TaskDefaults()
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_scene_generation_rendering_prompt_defaults(
    DOMAIN,
    SCENE_ID,
    task_id=TASK_ID,
)

def _step_delta_candidates(params: Mapping[str, Any]) -> Tuple[int, ...]:
    """Resolve candidate arithmetic count deltas."""

    raw = params.get("step_delta_candidates", group_default(_GEN_DEFAULTS, "step_delta_candidates", None))
    if raw is not None:
        if not isinstance(raw, (list, tuple)):
            raise ValueError("step_delta_candidates must be a sequence")
        candidates = tuple(dict.fromkeys(int(value) for value in raw))
        if not candidates:
            raise ValueError("step_delta_candidates must contain at least one integer")
        return candidates

    step_abs_min = int(params.get("step_abs_min", group_default(_GEN_DEFAULTS, "step_abs_min", _DEFAULTS.step_abs_min)))
    step_abs_max = int(params.get("step_abs_max", group_default(_GEN_DEFAULTS, "step_abs_max", _DEFAULTS.step_abs_max)))
    if step_abs_min < 1 or step_abs_min > step_abs_max:
        raise ValueError("step_abs_min must be positive and <= step_abs_max")
    return tuple(
        int(sign * step_abs)
        for step_abs in range(int(step_abs_min), int(step_abs_max) + 1)
        for sign in (-1, 1)
    )


def _resolve_sequence_spec(*, instance_seed: int, params: Mapping[str, Any]) -> _SequenceSpec:
    """Resolve one arithmetic count sequence with a single missing cell."""

    length_min = int(params.get("sequence_length_min", group_default(_GEN_DEFAULTS, "sequence_length_min", _DEFAULTS.sequence_length_min)))
    length_max = int(params.get("sequence_length_max", group_default(_GEN_DEFAULTS, "sequence_length_max", _DEFAULTS.sequence_length_max)))
    target_min = int(params.get("target_count_min", group_default(_GEN_DEFAULTS, "target_count_min", _DEFAULTS.target_count_min)))
    target_max = int(params.get("target_count_max", group_default(_GEN_DEFAULTS, "target_count_max", _DEFAULTS.target_count_max)))
    step_delta_support = _step_delta_candidates(params)
    if length_min > length_max:
        raise ValueError("sequence_length_min must be <= sequence_length_max")
    if target_min > target_max:
        raise ValueError("target_count_min must be <= target_count_max")

    length_support = tuple(range(int(length_min), int(length_max) + 1))
    target_support = tuple(range(int(target_min), int(target_max) + 1))
    base_index = int(resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace="task_icons__sequence_strip__missing_count_value:sequence_spec",
    ))
    explicit_target = params.get("target_count")
    if explicit_target is None:
        target_position = int(base_index % len(target_support))
        target_count = int(target_support[target_position])
        target_probabilities = uniform_probability_map(target_support)
    else:
        target_count = int(explicit_target)
        if target_count not in target_support:
            raise ValueError("explicit target_count is outside configured support")
        target_position = int(target_support.index(int(target_count)))
        target_probabilities = uniform_probability_map(target_support, selected=int(target_count))

    explicit_length = params.get("sequence_length")
    if explicit_length is None:
        length_index = int((base_index // max(1, len(target_support))) % len(length_support))
        sequence_length = int(length_support[length_index])
        length_probabilities = uniform_probability_map(length_support)
    else:
        sequence_length = int(explicit_length)
        if sequence_length not in length_support:
            raise ValueError("explicit sequence_length is outside configured support")
        length_probabilities = uniform_probability_map(length_support, selected=int(sequence_length))

    explicit_missing = params.get("missing_cell_index")
    explicit_step = params.get("step_delta")
    feasible_by_missing: Dict[int, List[Tuple[int, Tuple[int, ...]]]] = {}
    for missing_cell_index in range(int(sequence_length)):
        if explicit_missing is not None and int(explicit_missing) != int(missing_cell_index):
            continue
        for step_delta in step_delta_support:
            step_delta = int(step_delta)
            if explicit_step is not None and int(explicit_step) != int(step_delta):
                continue
            counts = tuple(
                int(target_count) + ((int(index) - int(missing_cell_index)) * int(step_delta))
                for index in range(int(sequence_length))
            )
            if all(int(target_min) <= int(value) <= int(target_max) for value in counts):
                feasible_by_missing.setdefault(int(missing_cell_index), []).append(
                    (int(step_delta), tuple(int(value) for value in counts))
                )
    if not feasible_by_missing:
        raise ValueError("no feasible arithmetic sequence support for the requested parameters")
    feasible_missing_indices = tuple(sorted(int(value) for value in feasible_by_missing))
    combo_offset = int(base_index // max(1, len(target_support) * len(length_support)))
    missing_index = int((target_position + combo_offset) % len(feasible_missing_indices))
    missing_cell_index = int(feasible_missing_indices[missing_index])
    step_options = tuple(feasible_by_missing[int(missing_cell_index)])
    step_index = int((base_index // max(1, len(feasible_missing_indices))) % len(step_options))
    step_delta, counts = step_options[int(step_index)]
    return _SequenceSpec(
        sequence_length=int(sequence_length),
        target_count=int(target_count),
        missing_cell_index=int(missing_cell_index),
        step_delta=int(step_delta),
        step_delta_candidates=tuple(int(value) for value in step_delta_support),
        full_sequence_counts=tuple(int(value) for value in counts),
        sequence_length_probabilities=dict(length_probabilities),
        target_count_probabilities=dict(target_probabilities),
    )

def _sample_scene(
    rng,
    *,
    instance_seed: int,
    sequence_spec: _SequenceSpec,
    pool_manifest: str,
    rotation_candidates: Tuple[int, ...],
    render_params: Mapping[str, Any],
) -> Tuple[_ScenePayload, Any]:
    """Sample and render one single-panel icon sequence missing-count scene."""

    appearance = sample_sequence_icon_appearance(
        rng,
        pool_manifest=str(pool_manifest),
        render_params=render_params,
        sequence_length=int(sequence_spec.sequence_length),
        empty_pool_message="sequence pool resolved no icons",
    )
    cell_specs: List[IconSequenceCellSpec] = []
    scene_rotations_by_cell: List[Tuple[int, ...]] = []
    for cell_index, count in enumerate(sequence_spec.full_sequence_counts):
        if int(cell_index) == int(sequence_spec.missing_cell_index):
            cell_specs.append(IconSequenceCellSpec(icon_instances=(), is_missing=True))
            scene_rotations_by_cell.append(())
            continue
        icon_specs: List[IconInstanceSpec] = []
        rotations: List[int] = []
        for icon_index in range(int(count)):
            rotation = int(rng.choice(rotation_candidates))
            noise_edits, noise_seed = sample_icon_instance_noise(
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}:scene_cell_{int(cell_index)}_icon_{int(icon_index)}",
                render_params=render_params,
            )
            icon_specs.append(
                IconInstanceSpec(
                    icon_id=str(appearance.sequence_icon_id),
                    rotation_degrees=int(rotation),
                    tint_rgb=tuple(int(value) for value in appearance.tint_rgb),
                    noise_edits=tuple(noise_edits),
                    noise_seed=int(noise_seed),
                )
            )
            rotations.append(int(rotation))
        cell_specs.append(IconSequenceCellSpec(icon_instances=tuple(icon_specs), is_missing=False))
        scene_rotations_by_cell.append(tuple(int(value) for value in rotations))

    rendered = render_sequence_scene_from_params(
        rng=rng,
        scene_cells=tuple(cell_specs),
        canvas_width=int(appearance.canvas_width),
        canvas_height=int(appearance.canvas_height),
        render_params=render_params,
    )

    scene_cells: List[Dict[str, Any]] = []
    scene_icon_instances: List[Dict[str, Any]] = []
    missing_cell_bbox = None
    for rendered_cell in rendered.scene_cells:
        cell_bbox = tuple(int(value) for value in rendered_cell.cell_bbox_xyxy)
        is_missing = bool(rendered_cell.is_missing)
        if is_missing:
            missing_cell_bbox = cell_bbox
        scene_cells.append(
            {
                "entity_kind": "sequence_cell",
                "panel": "scene",
                "cell_index": int(rendered_cell.cell_index),
                "cell_bbox_xyxy": list(cell_bbox),
                "is_missing": bool(is_missing),
                "target_icon_count": int(sequence_spec.full_sequence_counts[int(rendered_cell.cell_index)]),
                "rendered_icon_count": int(len(rendered_cell.icon_instances)),
            }
        )
        for instance in rendered_cell.icon_instances:
            scene_icon_instances.append(
                serialize_rendered_icon_instance(
                    instance,
                    entity_kind="scene_icon",
                    extra_fields={
                        "cell_index": int(rendered_cell.cell_index),
                        "cell_bbox_xyxy": list(cell_bbox),
                    },
                )
            )
    if missing_cell_bbox is None:
        raise ValueError("rendered sequence scene did not produce a missing cell bbox")

    return _ScenePayload(
        sequence_length=int(sequence_spec.sequence_length),
        target_count=int(sequence_spec.target_count),
        missing_cell_index=int(sequence_spec.missing_cell_index),
        step_delta=int(sequence_spec.step_delta),
        full_sequence_counts=tuple(int(value) for value in sequence_spec.full_sequence_counts),
        sequence_icon_id=str(appearance.sequence_icon_id),
        scene_rotations_by_cell=tuple(tuple(int(value) for value in rotations) for rotations in scene_rotations_by_cell),
        missing_cell_bbox=tuple(int(value) for value in missing_cell_bbox),
        sampled_palette_rgb=tuple(tuple(int(channel) for channel in color) for color in appearance.sampled_palette_rgb),
        cell_box_width_px=int(appearance.cell_box_width_px),
        cell_box_height_px=int(appearance.cell_box_height_px),
        panel_geometry=single_panel_geometry_to_trace(rendered.layout),
        scene_cells=tuple(scene_cells),
        scene_icon_instances=tuple(scene_icon_instances),
    ), rendered.image


@register_task
class IconsSequenceMissingCountTask:
    """Infer the missing icon count in a single-panel sequence row."""

    task_id = TASK_ID
    domain = DOMAIN
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic icon sequence missing-count instance."""

        scene_rng = spawn_rng(int(instance_seed), "scene")
        sequence_spec = _resolve_sequence_spec(instance_seed=int(instance_seed), params=params)
        render_params = resolve_icon_cell_render_params(
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            fallback_defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        validate_sequence_cell_box_bounds(render_params)
        pool_manifest = str(params.get("pool_manifest", group_default(_GEN_DEFAULTS, "pool_manifest", _DEFAULTS.pool_manifest)))
        rotation_candidates = resolve_rotation_candidates(
            params=params,
            generation_defaults=_GEN_DEFAULTS,
            fallback_candidates=_DEFAULTS.rotation_candidates_degrees,
        )

        scene_payload = None
        image = None
        last_error: Exception | None = None
        for _ in range(max(1, int(max_attempts))):
            try:
                scene_payload, image = _sample_scene(
                    scene_rng,
                    instance_seed=int(instance_seed),
                    sequence_spec=sequence_spec,
                    pool_manifest=str(pool_manifest),
                    rotation_candidates=rotation_candidates,
                    render_params=render_params,
                )
                break
            except Exception as exc:
                last_error = exc
                continue
        if scene_payload is None or image is None:
            raise RuntimeError("failed to generate task_icons__sequence_strip__missing_count_value instance") from last_error

        prompt_defaults, prompt_artifacts = render_sequence_strip_prompt_artifacts(
            instance_seed=int(instance_seed),
            prompt_defaults=_PROMPT_DEFAULTS,
            prompt_query_key=PROMPT_QUERY_KEY,
        )

        annotation_payload = scalar_bbox_artifacts(
            (scene_payload.missing_cell_bbox,),
            error_message="missing-count annotation must contain exactly one bbox",
        )
        query_id = QUERY_ID
        answer_gt = TypedValue(type="integer", value=int(scene_payload.target_count))
        annotation_gt = annotation_payload.annotation_gt
        common_ids = {
            "domain": DOMAIN,
            "scene_id": SCENE_ID,
            "task_id": str(self.task_id),
            "query_id": str(query_id),
        }
        trace_payload = {
            "scene_ir": {
                **common_ids,
                "scene_kind": "icons_sequence_missing_count",
                "entities": [
                    *[dict(cell) for cell in scene_payload.scene_cells],
                    *[dict(instance) for instance in scene_payload.scene_icon_instances],
                ],
                "relations": {
                    "sequence_rule": "arithmetic_progression",
                    "sequence_icon_id": str(scene_payload.sequence_icon_id),
                    "full_sequence_counts": list(scene_payload.full_sequence_counts),
                    "missing_cell_index": int(scene_payload.missing_cell_index),
                    "step_delta": int(scene_payload.step_delta),
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(scene_payload.panel_geometry),
                },
            },
            "query_spec": {
                **common_ids,
                "query_id": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "scene_id": SCENE_ID,
                    "sequence_rule": "arithmetic_progression",
                    "sequence_length": int(scene_payload.sequence_length),
                    "sequence_length_probabilities": dict(sequence_spec.sequence_length_probabilities),
                    "target_count": int(scene_payload.target_count),
                    "target_count_probabilities": dict(sequence_spec.target_count_probabilities),
                    "missing_cell_index": int(scene_payload.missing_cell_index),
                    "step_delta": int(scene_payload.step_delta),
                    "step_delta_candidates": [int(value) for value in sequence_spec.step_delta_candidates],
                    "pool_manifest": str(pool_manifest),
                    "rotation_candidates_degrees": [int(value) for value in rotation_candidates],
                    "cell_box_width_px": int(scene_payload.cell_box_width_px),
                    "cell_box_height_px": int(scene_payload.cell_box_height_px),
                },
            },
            "render_spec": sequence_render_spec(
                common_ids=common_ids,
                panel_geometry=scene_payload.panel_geometry,
                render_params=render_params,
                sampled_palette_rgb=scene_payload.sampled_palette_rgb,
                cell_box_width_px=int(scene_payload.cell_box_width_px),
                cell_box_height_px=int(scene_payload.cell_box_height_px),
                extra_style={
                    "missing_mark_font_size_px": int(render_params["missing_mark_font_size_px"]),
                    "missing_mark_color_rgb": list(render_params["missing_mark_color_rgb"]),
                },
            ),
            "render_map": bbox_anchor_render_map(
                anchor_name="missing_cell_bbox",
                bbox_xyxy=annotation_payload.value,
            ),
            "execution_trace": {
                **common_ids,
                "scene_variant": "single_panel_sequence_row",
                "query_id": str(query_id),
                "sequence_rule": "arithmetic_progression",
                "sequence_length": int(scene_payload.sequence_length),
                "sequence_length_probabilities": dict(sequence_spec.sequence_length_probabilities),
                "target_count": int(scene_payload.target_count),
                "target_count_probabilities": dict(sequence_spec.target_count_probabilities),
                "missing_cell_index": int(scene_payload.missing_cell_index),
                "step_delta": int(scene_payload.step_delta),
                "full_sequence_counts": list(scene_payload.full_sequence_counts),
                "sequence_icon_id": str(scene_payload.sequence_icon_id),
                "cell_box_width_px": int(scene_payload.cell_box_width_px),
                "cell_box_height_px": int(scene_payload.cell_box_height_px),
                "scene_rotations_degrees_by_cell": [list(rotations) for rotations in scene_payload.scene_rotations_by_cell],
                "question_format": "infer_missing_sequence_count",
            },
            "witness_symbolic": {
                "query_id": str(query_id),
                "sequence_rule": "arithmetic_progression",
                "full_sequence_counts": list(scene_payload.full_sequence_counts),
                "missing_cell_index": int(scene_payload.missing_cell_index),
                "step_delta": int(scene_payload.step_delta),
            },
            "projected_annotation": dict(annotation_payload.projected_annotation),
        }
        output = TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
        return output


__all__ = ["IconsSequenceMissingCountTask"]
