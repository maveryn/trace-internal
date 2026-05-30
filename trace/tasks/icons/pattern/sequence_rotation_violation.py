"""Identify the numbered cell that breaks a constant-rotation icon sequence."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.taxonomy import resolve_task_taxonomy
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
from ..shared.complexity import build_icons_sequence_rotation_violation_complexity
from ..shared.defaults import ICON_SHARED_DEFAULTS
from ..shared.evidence import bbox_set_evidence
from ..shared.icon_assets import resolve_icon_pool
from ..shared.icon_scene import (
    IconInstanceSpec,
    serialize_rendered_icon_instance,
    single_panel_geometry_to_trace,
    sort_bboxes_reading_order,
)
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


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for icon sequence rotation-violation rows."""

    sequence_length_min: int = 5
    sequence_length_max: int = 7
    answer_index_min: int = 1
    answer_index_max: int = 7
    canvas_width: int = 1104
    canvas_height: int = ICON_SHARED_DEFAULTS.canvas_height
    outer_margin_px: int = ICON_SHARED_DEFAULTS.outer_margin_px
    panel_padding_px: int = ICON_SHARED_DEFAULTS.panel_padding_px
    panel_corner_radius_px: int = ICON_SHARED_DEFAULTS.panel_corner_radius_px
    scene_icon_size_min_px: int = 48
    scene_icon_size_max_px: int = 72
    cell_box_width_min_px: int = 96
    cell_box_width_max_px: int = 136
    cell_box_height_min_px: int = 96
    cell_box_height_max_px: int = 136
    scene_max_overlap_fraction: float = 0.20
    scene_placement_max_attempts: int = 120
    scene_size_shrink_rounds: int = ICON_SHARED_DEFAULTS.scene_size_shrink_rounds
    scene_size_shrink_factor: float = ICON_SHARED_DEFAULTS.scene_size_shrink_factor
    panel_title_font_size_px: int = ICON_SHARED_DEFAULTS.panel_title_font_size_px
    pool_manifest: str = "non_symmetry.txt"
    rotation_candidates_degrees: Tuple[int, ...] = (0, 90, 180, 270)
    step_candidates_degrees: Tuple[int, ...] = (90, 270)
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
    cell_label_font_size_px: int = 22
    cell_label_color_rgb: Tuple[int, int, int] = (52, 60, 77)
    missing_mark_font_size_px: int = 56
    missing_mark_color_rgb: Tuple[int, int, int] = (84, 96, 118)
    icon_noise_edit_types: Tuple[str, ...] = ICON_SHARED_DEFAULTS.icon_noise_edit_types
    icon_noise_edit_count_range: Tuple[int, int] = ICON_SHARED_DEFAULTS.icon_noise_edit_count_range
    icon_noise_value_ranges: Dict[str, Dict[str, Tuple[float, float]]] = field(
        default_factory=lambda: deepcopy(ICON_SHARED_DEFAULTS.icon_noise_value_ranges)
    )


@dataclass(frozen=True)
class _SequenceSpec:
    """One fully resolved constant-rotation sequence with a single violating cell."""

    sequence_length: int
    answer_index: int
    violation_cell_index: int
    start_rotation_degrees: int
    step_delta_degrees: int
    violation_rotation_degrees: int
    expected_sequence_rotations_degrees: Tuple[int, ...]
    observed_sequence_rotations_degrees: Tuple[int, ...]
    answer_index_probabilities: Dict[str, float]
    sequence_length_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _ScenePayload:
    """Trace-ready payload for one icon sequence rotation-violation instance."""

    sequence_length: int
    answer_index: int
    violation_cell_index: int
    start_rotation_degrees: int
    step_delta_degrees: int
    violation_rotation_degrees: int
    expected_sequence_rotations_degrees: Tuple[int, ...]
    observed_sequence_rotations_degrees: Tuple[int, ...]
    sequence_icon_id: str
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...]
    cell_box_width_px: int
    cell_box_height_px: int
    panel_geometry: Dict[str, Any]
    scene_cells: Tuple[Dict[str, Any], ...]
    scene_icon_instances: Tuple[Dict[str, Any], ...]
    violating_cell_bbox: Tuple[int, int, int, int]


_DEFAULTS = _TaskDefaults()
TASK_ID = "task_icons__sequence_strip__rotation_sequence_violation_index"
QUERY_ID = "row_rotation_violation"

_TASK_GROUP_DEFAULTS = get_task_group_defaults("icons", "pattern")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
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


def _step_candidates(params: Mapping[str, Any]) -> Tuple[int, ...]:
    """Resolve supported constant rotation steps."""

    raw = params.get(
        "step_candidates_degrees",
        group_default(_GEN_DEFAULTS, "step_candidates_degrees", list(_DEFAULTS.step_candidates_degrees)),
    )
    if not isinstance(raw, (list, tuple)):
        raise ValueError("step_candidates_degrees must be a sequence")
    steps = tuple(int(value) % 360 for value in raw)
    if not steps:
        raise ValueError("step_candidates_degrees must contain at least one rotation step")
    return steps


def _rotation_sequence(*, start_rotation_degrees: int, step_delta_degrees: int, sequence_length: int) -> Tuple[int, ...]:
    """Return one constant-step rotation sequence modulo 360 degrees."""

    return tuple(
        int((int(start_rotation_degrees) + (int(index) * int(step_delta_degrees))) % 360)
        for index in range(int(sequence_length))
    )


def _minimal_rotation_difference_degrees(left: int, right: int) -> int:
    """Return the smallest absolute angular distance between two rotations."""

    diff = abs((int(left) - int(right)) % 360)
    return int(min(diff, 360 - diff))


def _rotation_violation_explanations(
    observed_rotations_degrees: Sequence[int],
    *,
    rotation_candidates: Sequence[int],
    step_candidates: Sequence[int],
) -> Tuple[bool, set[int]]:
    """Return whether the row is already valid and which single-violation indices remain plausible."""

    exact_match = False
    plausible_indices: set[int] = set()
    observed = tuple(int(value) % 360 for value in observed_rotations_degrees)
    for start_rotation_degrees in rotation_candidates:
        for step_delta_degrees in step_candidates:
            expected = _rotation_sequence(
                start_rotation_degrees=int(start_rotation_degrees),
                step_delta_degrees=int(step_delta_degrees),
                sequence_length=len(observed),
            )
            mismatches = [
                int(index)
                for index, (observed_rotation, expected_rotation) in enumerate(zip(observed, expected))
                if int(observed_rotation) != int(expected_rotation)
            ]
            if not mismatches:
                exact_match = True
            elif len(mismatches) == 1:
                plausible_indices.add(int(mismatches[0]))
    return bool(exact_match), plausible_indices


def _resolve_sequence_spec(*, instance_seed: int, params: Mapping[str, Any]) -> _SequenceSpec:
    """Resolve one constant-rotation row with a unique violating position."""

    sequence_length_min = int(
        params.get("sequence_length_min", group_default(_GEN_DEFAULTS, "sequence_length_min", _DEFAULTS.sequence_length_min))
    )
    sequence_length_max = int(
        params.get("sequence_length_max", group_default(_GEN_DEFAULTS, "sequence_length_max", _DEFAULTS.sequence_length_max))
    )
    answer_index_min = int(
        params.get("answer_index_min", group_default(_GEN_DEFAULTS, "answer_index_min", _DEFAULTS.answer_index_min))
    )
    answer_index_max = int(
        params.get("answer_index_max", group_default(_GEN_DEFAULTS, "answer_index_max", _DEFAULTS.answer_index_max))
    )
    if sequence_length_min > sequence_length_max:
        raise ValueError("sequence_length_min must be <= sequence_length_max")
    if answer_index_min < 1 or answer_index_min > answer_index_max:
        raise ValueError("answer_index_min must be in [1, answer_index_max]")
    if answer_index_max > sequence_length_max:
        raise ValueError("answer_index_max must be <= sequence_length_max")

    rotation_candidates = _rotation_candidates(params)
    step_candidates = _step_candidates(params)
    length_support = tuple(range(int(sequence_length_min), int(sequence_length_max) + 1))
    answer_support = tuple(range(int(answer_index_min), int(answer_index_max) + 1))
    base_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:sequence_spec",
        )
    )

    explicit_answer_index = params.get("answer_index")
    explicit_violation_cell_index = params.get("violation_cell_index")
    if explicit_answer_index is not None and explicit_violation_cell_index is not None:
        if int(explicit_answer_index) != int(explicit_violation_cell_index) + 1:
            raise ValueError("answer_index must equal violation_cell_index + 1 when both are provided")

    if explicit_answer_index is not None:
        answer_index = int(explicit_answer_index)
    elif explicit_violation_cell_index is not None:
        answer_index = int(explicit_violation_cell_index) + 1
    else:
        answer_index = int(answer_support[int(base_index % len(answer_support))])
    if answer_index not in answer_support:
        raise ValueError("answer_index is outside configured support")
    violation_cell_index = int(answer_index - 1)

    feasible_length_support = tuple(int(value) for value in length_support if int(value) >= int(answer_index))
    explicit_sequence_length = params.get("sequence_length")
    if explicit_sequence_length is None:
        length_index = int((base_index // max(1, len(answer_support))) % len(feasible_length_support))
        sequence_length = int(feasible_length_support[length_index])
        sequence_length_probabilities = uniform_probability_map(feasible_length_support)
    else:
        sequence_length = int(explicit_sequence_length)
        if sequence_length not in feasible_length_support:
            raise ValueError("explicit sequence_length is outside the feasible support for the chosen answer index")
        sequence_length_probabilities = uniform_probability_map(feasible_length_support, selected=int(sequence_length))

    explicit_start_rotation = params.get("start_rotation_degrees")
    explicit_step_delta = params.get("step_delta_degrees")
    explicit_violation_rotation = params.get("violation_rotation_degrees")
    feasible_sequences: List[Tuple[int, int, int, Tuple[int, ...], Tuple[int, ...]]] = []
    for start_rotation_degrees in rotation_candidates:
        if explicit_start_rotation is not None and int(start_rotation_degrees) != int(explicit_start_rotation) % 360:
            continue
        for step_delta_degrees in step_candidates:
            if explicit_step_delta is not None and int(step_delta_degrees) != int(explicit_step_delta) % 360:
                continue
            expected = _rotation_sequence(
                start_rotation_degrees=int(start_rotation_degrees),
                step_delta_degrees=int(step_delta_degrees),
                sequence_length=int(sequence_length),
            )
            expected_rotation = int(expected[violation_cell_index])
            for violation_rotation_degrees in rotation_candidates:
                if explicit_violation_rotation is not None and int(violation_rotation_degrees) != int(explicit_violation_rotation) % 360:
                    continue
                if int(violation_rotation_degrees) == int(expected_rotation):
                    continue
                observed = list(int(value) for value in expected)
                observed[int(violation_cell_index)] = int(violation_rotation_degrees)
                exact_match, plausible_indices = _rotation_violation_explanations(
                    tuple(observed),
                    rotation_candidates=rotation_candidates,
                    step_candidates=step_candidates,
                )
                if exact_match:
                    continue
                if plausible_indices != {int(violation_cell_index)}:
                    continue
                feasible_sequences.append(
                    (
                        int(start_rotation_degrees),
                        int(step_delta_degrees),
                        int(violation_rotation_degrees),
                        tuple(int(value) for value in expected),
                        tuple(int(value) for value in observed),
                    )
                )
    if not feasible_sequences:
        raise ValueError("no unambiguous rotation-violation sequence is feasible for the requested parameters")

    combo_index = int(base_index // max(1, len(answer_support) * len(feasible_length_support))) % len(feasible_sequences)
    (
        start_rotation_degrees,
        step_delta_degrees,
        violation_rotation_degrees,
        expected_sequence_rotations_degrees,
        observed_sequence_rotations_degrees,
    ) = feasible_sequences[int(combo_index)]
    answer_index_probabilities = uniform_probability_map(
        answer_support,
        selected=int(answer_index) if explicit_answer_index is not None or explicit_violation_cell_index is not None else None,
    )

    return _SequenceSpec(
        sequence_length=int(sequence_length),
        answer_index=int(answer_index),
        violation_cell_index=int(violation_cell_index),
        start_rotation_degrees=int(start_rotation_degrees),
        step_delta_degrees=int(step_delta_degrees),
        violation_rotation_degrees=int(violation_rotation_degrees),
        expected_sequence_rotations_degrees=tuple(int(value) for value in expected_sequence_rotations_degrees),
        observed_sequence_rotations_degrees=tuple(int(value) for value in observed_sequence_rotations_degrees),
        answer_index_probabilities=dict(answer_index_probabilities),
        sequence_length_probabilities=dict(sequence_length_probabilities),
    )


def _sample_scene(
    rng,
    *,
    instance_seed: int,
    sequence_spec: _SequenceSpec,
    pool_manifest: str,
    render_params: Mapping[str, Any],
) -> Tuple[_ScenePayload, Any]:
    """Sample and render one single-panel rotation-violation sequence row."""

    pool = list(resolve_icon_pool(str(pool_manifest)))
    if not pool:
        raise ValueError("rotation sequence pool resolved no icons")
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
    for cell_index, observed_rotation_degrees in enumerate(sequence_spec.observed_sequence_rotations_degrees):
        noise_edits, noise_seed = sample_icon_instance_noise(
            instance_seed=int(instance_seed),
            namespace=f"{IconsPatternSequenceRotationViolationTask.task_id}:scene_cell_{int(cell_index)}_icon_0",
            render_params=render_params,
        )
        cell_specs.append(
            IconSequenceCellSpec(
                icon_instances=(
                    IconInstanceSpec(
                        icon_id=str(sequence_icon_id),
                        rotation_degrees=int(observed_rotation_degrees),
                        tint_rgb=tuple(int(value) for value in tint_rgb),
                        noise_edits=tuple(noise_edits),
                        noise_seed=int(noise_seed),
                    ),
                ),
                is_missing=False,
                cell_label_text=str(int(cell_index) + 1),
            )
        )

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
        cell_label_font_size_px=int(render_params["cell_label_font_size_px"]),
        cell_label_color_rgb=tuple(int(v) for v in render_params["cell_label_color_rgb"]),
        scene_title="Sequence",
        icon_canvas_style=render_params.get("_icon_canvas_style_object"),
    )

    scene_cells: List[Dict[str, Any]] = []
    scene_icon_instances: List[Dict[str, Any]] = []
    violating_cell_bbox = None
    for rendered_cell in rendered.scene_cells:
        cell_index = int(rendered_cell.cell_index)
        cell_bbox = tuple(int(value) for value in rendered_cell.cell_bbox_xyxy)
        if int(cell_index) == int(sequence_spec.violation_cell_index):
            violating_cell_bbox = cell_bbox
        scene_cells.append(
            {
                "entity_kind": "sequence_cell",
                "panel": "scene",
                "cell_index": int(cell_index),
                "cell_label_text": str(rendered_cell.cell_label_text or str(int(cell_index) + 1)),
                "cell_bbox_xyxy": list(cell_bbox),
                "is_violation": bool(int(cell_index) == int(sequence_spec.violation_cell_index)),
                "expected_rotation_degrees": int(sequence_spec.expected_sequence_rotations_degrees[cell_index]),
                "observed_rotation_degrees": int(sequence_spec.observed_sequence_rotations_degrees[cell_index]),
                "rendered_icon_count": int(len(rendered_cell.icon_instances)),
            }
        )
        for instance in rendered_cell.icon_instances:
            scene_icon_instances.append(
                serialize_rendered_icon_instance(
                    instance,
                    entity_kind="scene_icon",
                    extra_fields={
                        "cell_index": int(cell_index),
                        "cell_bbox_xyxy": list(cell_bbox),
                        "cell_label_text": str(rendered_cell.cell_label_text or str(int(cell_index) + 1)),
                    },
                )
            )
    if violating_cell_bbox is None:
        raise ValueError("rendered sequence scene did not produce the violating cell bbox")

    return _ScenePayload(
        sequence_length=int(sequence_spec.sequence_length),
        answer_index=int(sequence_spec.answer_index),
        violation_cell_index=int(sequence_spec.violation_cell_index),
        start_rotation_degrees=int(sequence_spec.start_rotation_degrees),
        step_delta_degrees=int(sequence_spec.step_delta_degrees),
        violation_rotation_degrees=int(sequence_spec.violation_rotation_degrees),
        expected_sequence_rotations_degrees=tuple(int(value) for value in sequence_spec.expected_sequence_rotations_degrees),
        observed_sequence_rotations_degrees=tuple(int(value) for value in sequence_spec.observed_sequence_rotations_degrees),
        sequence_icon_id=str(sequence_icon_id),
        sampled_palette_rgb=tuple(tuple(int(channel) for channel in color) for color in sampled_palette_rgb),
        cell_box_width_px=int(cell_box_width_px),
        cell_box_height_px=int(cell_box_height_px),
        panel_geometry=single_panel_geometry_to_trace(rendered.layout),
        scene_cells=tuple(scene_cells),
        scene_icon_instances=tuple(scene_icon_instances),
        violating_cell_bbox=tuple(int(value) for value in violating_cell_bbox),
    ), rendered.image


@register_task
class IconsPatternSequenceRotationViolationTask:
    """Identify the numbered cell that breaks a constant-rotation sequence."""

    task_id = TASK_ID
    domain = "icons"
    task_group = "pattern"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic icon sequence rotation-violation instance."""

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
                    render_params=render_params,
                )
                break
            except Exception as exc:  # pragma: no cover - exercised through retry loop
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

        evidence_bboxes = sort_bboxes_reading_order((scene_payload.violating_cell_bbox,))
        evidence_payload = bbox_set_evidence(evidence_bboxes)
        taxonomy = resolve_task_taxonomy(str(self.task_id))
        query_id = QUERY_ID
        answer_gt = TypedValue(type="integer", value=int(scene_payload.answer_index))
        evidence_gt = TypedValue(
            type=str(evidence_payload["evidence_type"]),
            value=list(evidence_payload["evidence_value"]),
        )
        common_ids = {
            "domain": taxonomy.domain,
            "scene_id": taxonomy.scene_id,
            "task_id": str(self.task_id),
            "query_id": str(query_id),
        }
        trace_payload = {
            "taxonomy": {
                "domain": taxonomy.domain,
                "scene_id": taxonomy.scene_id,
                "task_id": str(self.task_id),
                "source_domain": taxonomy.source_domain,
                "source_task_group": taxonomy.source_task_group,
                "query_id": str(query_id),
            },
            "scene_ir": {
                **common_ids,
                "scene_kind": "icons_pattern_sequence_rotation_violation",
                "entities": [
                    *[dict(cell) for cell in scene_payload.scene_cells],
                    *[dict(instance) for instance in scene_payload.scene_icon_instances],
                ],
                "relations": {
                    "query_id": str(query_id),
                    "sequence_rule": "constant_rotation_step",
                    "sequence_icon_id": str(scene_payload.sequence_icon_id),
                    "start_rotation_degrees": int(scene_payload.start_rotation_degrees),
                    "step_delta_degrees": int(scene_payload.step_delta_degrees),
                    "expected_sequence_rotations_degrees": list(scene_payload.expected_sequence_rotations_degrees),
                    "observed_sequence_rotations_degrees": list(scene_payload.observed_sequence_rotations_degrees),
                    "violation_cell_index": int(scene_payload.violation_cell_index),
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(scene_payload.panel_geometry),
                },
            },
            "query_spec": {
                **common_ids,
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "scene_id": taxonomy.scene_id,
                    "query_id": str(query_id),
                    "query_id_probabilities": {str(query_id): 1.0},
                    "sequence_length": int(scene_payload.sequence_length),
                    "sequence_length_probabilities": dict(sequence_spec.sequence_length_probabilities),
                    "answer_index": int(scene_payload.answer_index),
                    "answer_index_probabilities": dict(sequence_spec.answer_index_probabilities),
                    "violation_cell_index": int(scene_payload.violation_cell_index),
                    "start_rotation_degrees": int(scene_payload.start_rotation_degrees),
                    "step_delta_degrees": int(scene_payload.step_delta_degrees),
                    "violation_rotation_degrees": int(scene_payload.violation_rotation_degrees),
                    "pool_manifest": str(pool_manifest),
                    "rotation_candidates_degrees": [int(value) for value in _rotation_candidates(params)],
                    "step_candidates_degrees": [int(value) for value in _step_candidates(params)],
                    "cell_box_width_px": int(scene_payload.cell_box_width_px),
                    "cell_box_height_px": int(scene_payload.cell_box_height_px),
                },
            },
            "render_spec": {
                **common_ids,
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
                    "cell_label_font_size_px": int(render_params["cell_label_font_size_px"]),
                    "cell_label_color_rgb": list(render_params["cell_label_color_rgb"]),
                },
            },
            "render_map": {
                "image_id": "img0",
                "anchors": {
                    "violating_cell_bbox": list(evidence_payload["evidence_value"][0]),
                },
            },
            "execution_trace": {
                **common_ids,
                "scene_variant": "sequence_row",
                "query_id_probabilities": {str(query_id): 1.0},
                "sequence_length": int(scene_payload.sequence_length),
                "answer_index": int(scene_payload.answer_index),
                "violation_cell_index": int(scene_payload.violation_cell_index),
                "start_rotation_degrees": int(scene_payload.start_rotation_degrees),
                "step_delta_degrees": int(scene_payload.step_delta_degrees),
                "violation_rotation_degrees": int(scene_payload.violation_rotation_degrees),
                "expected_sequence_rotations_degrees": list(scene_payload.expected_sequence_rotations_degrees),
                "observed_sequence_rotations_degrees": list(scene_payload.observed_sequence_rotations_degrees),
                "sequence_icon_id": str(scene_payload.sequence_icon_id),
                "cell_box_width_px": int(scene_payload.cell_box_width_px),
                "cell_box_height_px": int(scene_payload.cell_box_height_px),
                "question_format": "identify_rotation_sequence_violation",
            },
            "witness_symbolic": {
                "sequence_rule": "constant_rotation_step",
                "start_rotation_degrees": int(scene_payload.start_rotation_degrees),
                "step_delta_degrees": int(scene_payload.step_delta_degrees),
                "expected_sequence_rotations_degrees": list(scene_payload.expected_sequence_rotations_degrees),
                "observed_sequence_rotations_degrees": list(scene_payload.observed_sequence_rotations_degrees),
                "violation_cell_index": int(scene_payload.violation_cell_index),
            },
            "projected_evidence": dict(evidence_payload["projected_evidence"]),
        }
        expected_rotation = int(scene_payload.expected_sequence_rotations_degrees[scene_payload.violation_cell_index])
        violation_rotation_difference_degrees = _minimal_rotation_difference_degrees(
            int(expected_rotation),
            int(scene_payload.violation_rotation_degrees),
        )
        complexity = build_icons_sequence_rotation_violation_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
            sequence_length=int(scene_payload.sequence_length),
            sequence_length_min=int(group_default(_GEN_DEFAULTS, "sequence_length_min", _DEFAULTS.sequence_length_min)),
            sequence_length_max=int(group_default(_GEN_DEFAULTS, "sequence_length_max", _DEFAULTS.sequence_length_max)),
            violation_cell_index=int(scene_payload.violation_cell_index),
            violation_rotation_difference_degrees=int(violation_rotation_difference_degrees),
            scene_icon_instances=scene_payload.scene_icon_instances,
            render_params=render_params,
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
            scene_id=taxonomy.scene_id,
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["IconsPatternSequenceRotationViolationTask"]
