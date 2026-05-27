"""Infer the missing icon count in a single-panel arithmetic icon sequence."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.defaults import ICON_SHARED_DEFAULTS
from ..shared.icon_assets import resolve_icon_pool
from ..shared.icon_scene import (
    IconInstanceSpec,
    serialize_rendered_icon_instance,
    single_panel_geometry_to_trace,
    sort_bboxes_reading_order,
)
from ..shared.complexity import build_icons_sequence_missing_count_complexity
from ..shared.icon_sequence_scene import (
    IconSequenceCellSpec,
    render_icon_sequence_scene,
    resolve_sequence_canvas_size,
)
from ..shared.icon_style import sample_single_icon_tint
from ..shared.icon_task_rendering import (
    icon_render_style_trace,
    resolve_icon_cell_render_params,
    sample_icon_instance_noise,
)
from ..shared.public_query_task import rewrite_icons_query_output
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
_TASK_GROUP_DEFAULTS = get_task_group_defaults("icons", "sequence")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id="task_icons__sequence_strip__missing_count_value",
)

def _rotation_candidates(params: Mapping[str, Any]) -> Tuple[int, ...]:
    """Resolve the supported icon rotations."""

    raw = params.get(
        "rotation_candidates_degrees",
        group_default(_GEN_DEFAULTS, "rotation_candidates_degrees", list(_DEFAULTS.rotation_candidates_degrees)),
    )
    if not isinstance(raw, (list, tuple)):
        raise ValueError("rotation_candidates_degrees must be a sequence")
    rotations = tuple(int(value) % 360 for value in raw)
    if not rotations:
        raise ValueError("rotation_candidates_degrees must contain at least one rotation")
    return rotations


def _resolve_sequence_spec(*, instance_seed: int, params: Mapping[str, Any]) -> _SequenceSpec:
    """Resolve one arithmetic count sequence with a single missing cell."""

    length_min = int(params.get("sequence_length_min", group_default(_GEN_DEFAULTS, "sequence_length_min", _DEFAULTS.sequence_length_min)))
    length_max = int(params.get("sequence_length_max", group_default(_GEN_DEFAULTS, "sequence_length_max", _DEFAULTS.sequence_length_max)))
    target_min = int(params.get("target_count_min", group_default(_GEN_DEFAULTS, "target_count_min", _DEFAULTS.target_count_min)))
    target_max = int(params.get("target_count_max", group_default(_GEN_DEFAULTS, "target_count_max", _DEFAULTS.target_count_max)))
    step_abs_min = int(params.get("step_abs_min", group_default(_GEN_DEFAULTS, "step_abs_min", _DEFAULTS.step_abs_min)))
    step_abs_max = int(params.get("step_abs_max", group_default(_GEN_DEFAULTS, "step_abs_max", _DEFAULTS.step_abs_max)))
    if length_min > length_max:
        raise ValueError("sequence_length_min must be <= sequence_length_max")
    if target_min > target_max:
        raise ValueError("target_count_min must be <= target_count_max")
    if step_abs_min < 1 or step_abs_min > step_abs_max:
        raise ValueError("step_abs_min must be positive and <= step_abs_max")

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
        for step_abs in range(int(step_abs_min), int(step_abs_max) + 1):
            for sign in (-1, 1):
                step_delta = int(sign * step_abs)
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

    pool = list(resolve_icon_pool(str(pool_manifest)))
    if not pool:
        raise ValueError("sequence pool resolved no icons")
    sequence_icon_id = str(rng.choice(pool))
    tint_rgb, sampled_palette_rgb = sample_single_icon_tint(
        rng,
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
    cell_box_width_px = int(
        rng.randint(
            int(render_params["cell_box_width_min_px"]),
            int(render_params["cell_box_width_max_px"]),
        )
    )
    cell_box_height_px = int(
        rng.randint(
            int(render_params["cell_box_height_min_px"]),
            int(render_params["cell_box_height_max_px"]),
        )
    )
    canvas_width, canvas_height = resolve_sequence_canvas_size(
        sequence_length=int(sequence_spec.sequence_length),
        cell_box_width_px=int(cell_box_width_px),
        cell_box_height_px=int(cell_box_height_px),
        render_params=render_params,
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
                namespace=f"{IconsSequenceMissingCountTask.task_id}:scene_cell_{int(cell_index)}_icon_{int(icon_index)}",
                render_params=render_params,
            )
            icon_specs.append(
                IconInstanceSpec(
                    icon_id=str(sequence_icon_id),
                    rotation_degrees=int(rotation),
                    tint_rgb=tuple(int(value) for value in tint_rgb),
                    noise_edits=tuple(noise_edits),
                    noise_seed=int(noise_seed),
                )
            )
            rotations.append(int(rotation))
        cell_specs.append(IconSequenceCellSpec(icon_instances=tuple(icon_specs), is_missing=False))
        scene_rotations_by_cell.append(tuple(int(value) for value in rotations))

    rendered = render_icon_sequence_scene(
        rng=rng,
        scene_cells=tuple(cell_specs),
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        outer_margin_px=int(render_params["outer_margin_px"]),
        panel_padding_px=int(render_params["panel_padding_px"]),
        panel_corner_radius_px=int(render_params["panel_corner_radius_px"]),
        cell_padding_px=int(render_params["cell_padding_px"]),
        cell_icon_padding_px=int(render_params["cell_icon_padding_px"]),
        cell_corner_radius_px=int(render_params["cell_corner_radius_px"]),
        scene_icon_size_min_px=int(render_params["scene_icon_size_min_px"]),
        scene_icon_size_max_px=int(render_params["scene_icon_size_max_px"]),
        scene_max_overlap_fraction=float(render_params["scene_max_overlap_fraction"]),
        scene_placement_max_attempts=int(render_params["scene_placement_max_attempts"]),
        scene_size_shrink_rounds=int(render_params["scene_size_shrink_rounds"]),
        scene_size_shrink_factor=float(render_params["scene_size_shrink_factor"]),
        panel_title_font_size_px=int(render_params["panel_title_font_size_px"]),
        missing_mark_font_size_px=int(render_params["missing_mark_font_size_px"]),
        background_rgb=tuple(int(v) for v in render_params["background_color_rgb"]),
        panel_fill_rgb=tuple(int(v) for v in render_params["panel_fill_rgb"]),
        panel_border_rgb=tuple(int(v) for v in render_params["panel_border_rgb"]),
        title_color_rgb=tuple(int(v) for v in render_params["header_text_rgb"]),
        cell_border_rgb=tuple(int(v) for v in render_params["cell_border_rgb"]),
        missing_mark_color_rgb=tuple(int(v) for v in render_params["missing_mark_color_rgb"]),
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
        sequence_icon_id=str(sequence_icon_id),
        scene_rotations_by_cell=tuple(tuple(int(value) for value in rotations) for rotations in scene_rotations_by_cell),
        missing_cell_bbox=tuple(int(value) for value in missing_cell_bbox),
        sampled_palette_rgb=tuple(tuple(int(channel) for channel in color) for color in sampled_palette_rgb),
        cell_box_width_px=int(cell_box_width_px),
        cell_box_height_px=int(cell_box_height_px),
        panel_geometry=single_panel_geometry_to_trace(rendered.layout),
        scene_cells=tuple(scene_cells),
        scene_icon_instances=tuple(scene_icon_instances),
    ), rendered.image


@register_task
class IconsSequenceMissingCountTask:
    """Infer the missing icon count in a single-panel sequence row."""

    task_id = "task_icons__sequence_strip__missing_count_value"
    domain = "icons"
    task_group = "sequence"

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
        if int(render_params["cell_box_width_min_px"]) > int(render_params["cell_box_width_max_px"]):
            raise ValueError("cell_box_width_min_px must be <= cell_box_width_max_px")
        if int(render_params["cell_box_height_min_px"]) > int(render_params["cell_box_height_max_px"]):
            raise ValueError("cell_box_height_min_px must be <= cell_box_height_max_px")
        pool_manifest = str(params.get("pool_manifest", group_default(_GEN_DEFAULTS, "pool_manifest", _DEFAULTS.pool_manifest)))
        rotation_candidates = _rotation_candidates(params)

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
            scene_key=str(prompt_defaults["scene_key"]),
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

        evidence_bboxes = sort_bboxes_reading_order((scene_payload.missing_cell_bbox,))
        query_variant = "arithmetic_progression"
        answer_gt = TypedValue(type="integer", value=int(scene_payload.target_count))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))
        trace_payload = {
            "scene_ir": {
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
                "query_variant": str(query_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "sequence_length": int(scene_payload.sequence_length),
                    "sequence_length_probabilities": dict(sequence_spec.sequence_length_probabilities),
                    "target_count": int(scene_payload.target_count),
                    "target_count_probabilities": dict(sequence_spec.target_count_probabilities),
                    "missing_cell_index": int(scene_payload.missing_cell_index),
                    "step_delta": int(scene_payload.step_delta),
                    "pool_manifest": str(pool_manifest),
                    "rotation_candidates_degrees": [int(value) for value in rotation_candidates],
                    "cell_box_width_px": int(scene_payload.cell_box_width_px),
                    "cell_box_height_px": int(scene_payload.cell_box_height_px),
                },
            },
            "render_spec": {
                "canvas_size": list(scene_payload.panel_geometry["canvas_size"]),
                "coord_space": "pixel",
                "panel_geometry": dict(scene_payload.panel_geometry),
                "style": {
                    **icon_render_style_trace(
                        render_params=render_params,
                        sampled_palette_rgb=scene_payload.sampled_palette_rgb,
                    ),
                    "cell_padding_px": int(render_params["cell_padding_px"]),
                    "cell_icon_padding_px": int(render_params["cell_icon_padding_px"]),
                    "cell_corner_radius_px": int(render_params["cell_corner_radius_px"]),
                    "cell_box_width_range_px": [
                        int(render_params["cell_box_width_min_px"]),
                        int(render_params["cell_box_width_max_px"]),
                    ],
                    "cell_box_height_range_px": [
                        int(render_params["cell_box_height_min_px"]),
                        int(render_params["cell_box_height_max_px"]),
                    ],
                    "sampled_cell_box_size_px": [
                        int(scene_payload.cell_box_width_px),
                        int(scene_payload.cell_box_height_px),
                    ],
                    "missing_mark_font_size_px": int(render_params["missing_mark_font_size_px"]),
                    "missing_mark_color_rgb": list(render_params["missing_mark_color_rgb"]),
                },
            },
            "render_map": {
                "image_id": "img0",
                "anchors": {
                    "missing_cell_bbox": list(scene_payload.missing_cell_bbox),
                },
            },
            "execution_trace": {
                "scene_variant": "single_panel_sequence_row",
                "query_variant": str(query_variant),
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
                "sequence_rule": "arithmetic_progression",
                "full_sequence_counts": list(scene_payload.full_sequence_counts),
                "missing_cell_index": int(scene_payload.missing_cell_index),
                "step_delta": int(scene_payload.step_delta),
            },
            "projected_evidence": {
                "bbox_set": list(evidence_bboxes),
            },
        }
        complexity = build_icons_sequence_missing_count_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
            sequence_length=int(scene_payload.sequence_length),
            sequence_length_min=int(group_default(_GEN_DEFAULTS, "sequence_length_min", _DEFAULTS.sequence_length_min)),
            sequence_length_max=int(group_default(_GEN_DEFAULTS, "sequence_length_max", _DEFAULTS.sequence_length_max)),
            target_count=int(scene_payload.target_count),
            target_count_max=int(group_default(_GEN_DEFAULTS, "target_count_max", _DEFAULTS.target_count_max)),
            missing_cell_index=int(scene_payload.missing_cell_index),
            step_delta=int(scene_payload.step_delta),
            scene_icon_instances=scene_payload.scene_icon_instances,
            render_params=render_params,
        )
        output = TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_variant=str(query_variant),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
        return rewrite_icons_query_output(
            output,
            query_id=str(query_variant),
            scene_id="sequence_strip",
        )


__all__ = ["IconsSequenceMissingCountTask"]
