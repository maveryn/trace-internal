"""Measure longest or shortest consecutive runs of named icons in a row."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, load_scene_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ...shared.variant_sampling import resolve_variant
from ..shared.icon_task_rendering import resolve_icon_cell_render_params
from ..shared.procedural_named_icons import (
    procedural_named_icon_display_name,
)
from .shared.annotations import selected_run_bbox_set_annotation
from .shared.defaults import DEFAULT_RENDER, DOMAIN, SCENE_ID
from .shared.output import named_strip_render_map, named_strip_render_spec
from .shared.prompts import render_named_strip_prompt_artifacts
from .shared.rendering import render_named_strip_scene, serialize_named_strip_icon
from .shared.sampling import (
    build_named_strip_icon_plans,
    named_strip_fill_style_probabilities,
    named_strip_fill_style_support,
    named_strip_shape_support,
    target_run_lengths as named_strip_target_run_lengths,
    target_runs as named_strip_target_runs,
)
from .shared.state import NamedStripScenePayload


TASK_ID = "task_icons__named_strip__shape_run_length"

QUERY_IDS: Tuple[str, ...] = (
    "longest_shape_run_length",
    "shortest_shape_run_length",
)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for named-icon run rows."""

    strip_length_min: int = 12
    strip_length_max: int = 16
    longest_run_length_min: int = 2
    longest_run_length_max: int = 6
    shortest_run_length_min: int = 1
    shortest_run_length_max: int = 5


@dataclass(frozen=True)
class _SampleSpec:
    """Symbolic sample for one named-icon run row."""

    query_id: str
    target_shape_id: str
    target_shape_name: str
    answer: int
    strip_length: int
    shape_ids: Tuple[str, ...]
    selected_run_indices: Tuple[int, ...]
    target_runs: Tuple[Tuple[int, int], ...]
    query_probabilities: Dict[str, float]
    answer_probabilities: Dict[str, float]
    strip_length_probabilities: Dict[str, float]
    shape_probabilities: Dict[str, float]
    fill_style_support: Tuple[str, ...]
    fill_style_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_scene_generation_rendering_prompt_defaults(
    DOMAIN,
    SCENE_ID,
    task_id=TASK_ID,
)


def _shape_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    return named_strip_shape_support(params, _GEN_DEFAULTS)


def _fill_style_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    return named_strip_fill_style_support(params, _GEN_DEFAULTS)


def _int_bounds(
    params: Mapping[str, Any],
    low_key: str,
    high_key: str,
    fallback_low: int,
    fallback_high: int,
) -> Tuple[int, int]:
    low = int(params.get(low_key, group_default(_GEN_DEFAULTS, low_key, fallback_low)))
    high = int(params.get(high_key, group_default(_GEN_DEFAULTS, high_key, fallback_high)))
    if low < 0 or high < low:
        raise ValueError(f"invalid {low_key}/{high_key} bounds")
    return int(low), int(high)


def _answer_support(params: Mapping[str, Any], query_id: str) -> Tuple[int, ...]:
    if str(query_id) == "longest_shape_run_length":
        low, high = _int_bounds(
            params,
            "longest_run_length_min",
            "longest_run_length_max",
            _DEFAULTS.longest_run_length_min,
            _DEFAULTS.longest_run_length_max,
        )
    elif str(query_id) == "shortest_shape_run_length":
        low, high = _int_bounds(
            params,
            "shortest_run_length_min",
            "shortest_run_length_max",
            _DEFAULTS.shortest_run_length_min,
            _DEFAULTS.shortest_run_length_max,
        )
    else:
        raise ValueError(f"unsupported query_id: {query_id}")
    if str(query_id) == "longest_shape_run_length" and low < 2:
        raise ValueError("longest run support starts at 2 so the task is not a singleton-detection branch")
    return tuple(range(int(low), int(high) + 1))


def _target_runs(shape_ids: Sequence[str], *, target_shape_id: str) -> Tuple[Tuple[int, int], ...]:
    return named_strip_target_runs(shape_ids, target_shape_id=str(target_shape_id))


def _target_run_lengths(runs: Sequence[Tuple[int, int]]) -> Tuple[int, ...]:
    return named_strip_target_run_lengths(runs)


def _build_runs_for_query(rng, *, query_id: str, answer: int, strip_length: int) -> Tuple[Tuple[int, bool], ...]:
    """Return target-run lengths, marking the run that witnesses the answer."""

    run_blocks: List[Tuple[int, bool]] = [(int(answer), True)]
    if str(query_id) == "longest_shape_run_length":
        optional_candidates = tuple(range(1, int(answer)))
        desired_optional_count = int(rng.randint(1, 4)) if optional_candidates else 0
        for _ in range(int(desired_optional_count)):
            candidate = int(rng.choice(optional_candidates))
            tentative = run_blocks + [(candidate, False)]
            min_needed = sum(length for length, _ in tentative) + max(0, len(tentative) - 1)
            if int(min_needed) <= int(strip_length):
                run_blocks.append((int(candidate), False))
    elif str(query_id) == "shortest_shape_run_length":
        max_other = min(6, int(strip_length) - int(answer) - 1)
        if max_other <= int(answer):
            raise ValueError("strip length leaves no room for a longer target-shape run")
        run_blocks.append((int(rng.randint(int(answer) + 1, int(max_other))), False))
        desired_optional_count = int(rng.randint(0, 3))
        for _ in range(int(desired_optional_count)):
            candidate = int(rng.randint(int(answer) + 1, 6))
            tentative = run_blocks + [(candidate, False)]
            min_needed = sum(length for length, _ in tentative) + max(0, len(tentative) - 1)
            if int(min_needed) <= int(strip_length):
                run_blocks.append((int(candidate), False))
    else:
        raise ValueError(f"unsupported query_id: {query_id}")
    rng.shuffle(run_blocks)
    return tuple((int(length), bool(selected)) for length, selected in run_blocks)


def _construct_shape_row(
    rng,
    *,
    support: Sequence[str],
    target_shape_id: str,
    query_id: str,
    answer: int,
    strip_length: int,
) -> Tuple[Tuple[str, ...], Tuple[int, ...], Tuple[Tuple[int, int], ...]]:
    """Construct one row with a unique target-shape extremum run."""

    run_blocks = list(
        _build_runs_for_query(
            rng,
            query_id=str(query_id),
            answer=int(answer),
            strip_length=int(strip_length),
        )
    )
    min_needed = sum(length for length, _ in run_blocks) + max(0, len(run_blocks) - 1)
    if int(min_needed) > int(strip_length):
        raise ValueError("target runs do not fit strip length")
    gaps = [0] + ([1] * max(0, len(run_blocks) - 1)) + [0]
    remaining = int(strip_length) - int(min_needed)
    for _ in range(max(0, int(remaining))):
        gaps[int(rng.randint(0, len(gaps) - 1))] += 1

    distractor_support = tuple(str(value) for value in support if str(value) != str(target_shape_id))
    if not distractor_support:
        raise ValueError("target row needs at least one distractor shape")

    row: List[str] = []
    selected_indices: List[int] = []
    for run_index, (run_length, selected) in enumerate(run_blocks):
        for _ in range(int(gaps[int(run_index)])):
            row.append(str(rng.choice(distractor_support)))
        run_start = len(row)
        for _ in range(int(run_length)):
            row.append(str(target_shape_id))
        if bool(selected):
            selected_indices.extend(range(int(run_start), int(run_start) + int(run_length)))
    for _ in range(int(gaps[-1])):
        row.append(str(rng.choice(distractor_support)))

    runs = _target_runs(row, target_shape_id=str(target_shape_id))
    lengths = _target_run_lengths(runs)
    selected_run_length = int(len(selected_indices))
    if str(query_id) == "longest_shape_run_length":
        if selected_run_length != max(lengths) or lengths.count(int(selected_run_length)) != 1:
            raise ValueError("constructed row does not have a unique longest target run")
    elif str(query_id) == "shortest_shape_run_length":
        if selected_run_length != min(lengths) or lengths.count(int(selected_run_length)) != 1:
            raise ValueError("constructed row does not have a unique shortest target run")
    return tuple(str(value) for value in row), tuple(int(index) for index in selected_indices), tuple(runs)


def _sample_spec(*, instance_seed: int, params: Mapping[str, Any]) -> _SampleSpec:
    """Sample the task-owned run-length program before rendering.

    This owns the semantic query branch, target shape, answer support, strip
    length, and unique witness-run construction. Scene helpers only receive the
    resolved row and visual style arguments.
    """

    rng = spawn_rng(int(instance_seed), f"{TASK_ID}:sample")
    query_id, query_probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=QUERY_IDS,
        explicit_key="query_id",
        weights_key="query_id_weights",
    )
    support = _shape_support(params)
    explicit_shape = params.get("shape_id", params.get("target_shape_id"))
    if explicit_shape is not None:
        target_shape_id = str(explicit_shape)
        if target_shape_id not in set(support):
            raise ValueError(f"target shape must be one of {support}")
        shape_probabilities = {str(value): (1.0 if str(value) == str(target_shape_id) else 0.0) for value in support}
    else:
        target_shape_id = str(rng.choice(support))
        probability = 1.0 / float(len(support))
        shape_probabilities = {str(value): float(probability) for value in support}

    answer_support = _answer_support(params, str(query_id))
    explicit_answer = params.get("target_run_length", params.get("answer", params.get("run_length")))
    if explicit_answer is not None:
        answer = int(explicit_answer)
        if int(answer) not in set(answer_support):
            raise ValueError("explicit run length is outside configured support")
        answer_probabilities = uniform_probability_map(answer_support, selected=int(answer))
    else:
        answer = int(rng.choice(answer_support))
        answer_probabilities = uniform_probability_map(answer_support)

    strip_min, strip_max = _int_bounds(
        params,
        "strip_length_min",
        "strip_length_max",
        _DEFAULTS.strip_length_min,
        _DEFAULTS.strip_length_max,
    )
    if int(strip_min) < int(answer):
        strip_min = int(answer)
    if str(query_id) == "shortest_shape_run_length":
        strip_min = max(int(strip_min), (2 * int(answer)) + 2)
    if int(strip_min) > int(strip_max):
        raise ValueError("strip length range cannot support the requested run-length query")
    strip_support = tuple(range(int(strip_min), int(strip_max) + 1))
    explicit_strip_length = params.get("strip_length")
    if explicit_strip_length is not None:
        strip_length = int(explicit_strip_length)
        if int(strip_length) not in set(strip_support):
            raise ValueError("explicit strip_length is outside configured support")
        strip_length_probabilities = uniform_probability_map(strip_support, selected=int(strip_length))
    else:
        strip_length = int(rng.choice(strip_support))
        strip_length_probabilities = uniform_probability_map(strip_support)

    fill_style_support = _fill_style_support(params)
    fill_style_probabilities = named_strip_fill_style_probabilities(params, _GEN_DEFAULTS, fill_style_support)
    shape_ids, selected_indices, target_runs = _construct_shape_row(
        rng,
        support=support,
        target_shape_id=str(target_shape_id),
        query_id=str(query_id),
        answer=int(answer),
        strip_length=int(strip_length),
    )
    return _SampleSpec(
        query_id=str(query_id),
        target_shape_id=str(target_shape_id),
        target_shape_name=procedural_named_icon_display_name(str(target_shape_id)),
        answer=int(answer),
        strip_length=int(strip_length),
        shape_ids=tuple(str(value) for value in shape_ids),
        selected_run_indices=tuple(int(index) for index in selected_indices),
        target_runs=tuple((int(start), int(end)) for start, end in target_runs),
        query_probabilities=dict(query_probabilities),
        answer_probabilities=dict(answer_probabilities),
        strip_length_probabilities=dict(strip_length_probabilities),
        shape_probabilities=dict(shape_probabilities),
        fill_style_support=tuple(fill_style_support),
        fill_style_probabilities=dict(fill_style_probabilities),
    )


@register_task
class IconsNamedStripShapeRunLengthTask:
    """Ask for longest/shortest consecutive run length of a named icon shape."""

    task_id = TASK_ID
    domain = DOMAIN
    supported_query_ids = QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one run-length task instance from a sampled symbolic row.

        The task file owns answer and annotation binding from the same rendered
        selected run; shared code only supplies scene rendering, prompt, and
        trace serialization primitives.
        """

        render_params = resolve_icon_cell_render_params(
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            fallback_defaults=DEFAULT_RENDER,
            instance_seed=int(instance_seed),
        )
        if int(render_params["cell_box_width_min_px"]) > int(render_params["cell_box_width_max_px"]):
            raise ValueError("cell_box_width_min_px must be <= cell_box_width_max_px")
        if int(render_params["cell_box_height_min_px"]) > int(render_params["cell_box_height_max_px"]):
            raise ValueError("cell_box_height_min_px must be <= cell_box_height_max_px")
        last_error: Exception | None = None
        sample: _SampleSpec | None = None
        scene: NamedStripScenePayload | None = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                sample = _sample_spec(instance_seed=int(instance_seed), params=params)
                scene_rng = spawn_rng(int(instance_seed), f"{TASK_ID}:scene", int(attempt))
                plans, sampled_palette_rgb = build_named_strip_icon_plans(
                    shape_ids=sample.shape_ids,
                    fill_style_support=sample.fill_style_support,
                    fill_style_probabilities=sample.fill_style_probabilities,
                    instance_seed=int(instance_seed),
                    render_params=render_params,
                    rng=scene_rng,
                )
                scene = render_named_strip_scene(
                    strip_length=int(sample.strip_length),
                    target_shape_id=str(sample.target_shape_id),
                    selected_run_indices=sample.selected_run_indices,
                    plans=plans,
                    render_params=render_params,
                    rng=scene_rng,
                    sampled_palette_rgb=sampled_palette_rgb,
                )
                break
            except Exception as exc:  # pragma: no cover - exercised by smoke tests.
                last_error = exc
                sample = None
                scene = None
        if sample is None or scene is None:
            raise RuntimeError(f"could not generate {TASK_ID}: {last_error}") from last_error

        annotation_payload = selected_run_bbox_set_annotation(scene.icons, expected_count=int(sample.answer))
        selected_instance_ids = tuple(
            str(icon.instance_id)
            for icon in scene.icons
            if bool(icon.is_selected_run_member)
        )
        shape_counts = dict(Counter(str(icon.shape_id) for icon in scene.icons))

        prompt_defaults, prompt_artifacts = render_named_strip_prompt_artifacts(
            instance_seed=int(instance_seed),
            prompt_defaults=_PROMPT_DEFAULTS,
            prompt_query_key=str(sample.query_id),
            target_shape_name=str(sample.target_shape_name),
        )

        serialized_icons = [serialize_named_strip_icon(icon) for icon in scene.icons]
        target_run_lengths = _target_run_lengths(sample.target_runs)
        trace_payload = {
            "scene_ir": {
                "scene_kind": "icons_named_strip_run_length",
                "scene_id": SCENE_ID,
                "entities": [
                    *[dict(cell) for cell in scene.cells],
                    *serialized_icons,
                ],
                "relations": {
                    "row_rule": "consecutive_target_shape_runs",
                    "target_shape_id": str(sample.target_shape_id),
                    "target_shape_name": str(sample.target_shape_name),
                    "shape_counts": {str(key): int(value) for key, value in shape_counts.items()},
                    "target_runs": [
                        {"start_index": int(start), "end_index": int(end), "length": int(end) - int(start) + 1}
                        for start, end in sample.target_runs
                    ],
                    "selected_run_indices": [int(index) for index in sample.selected_run_indices],
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(scene.panel_geometry),
                },
            },
            "query_spec": {
                "query_id": str(sample.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "target_shape_id": str(sample.target_shape_id),
                    "target_shape_name": str(sample.target_shape_name),
                    "answer": int(sample.answer),
                    "strip_length": int(sample.strip_length),
                    "query_id_probabilities": dict(sample.query_probabilities),
                    "answer_probabilities": dict(sample.answer_probabilities),
                    "strip_length_probabilities": dict(sample.strip_length_probabilities),
                    "shape_id_support": list(_shape_support(params)),
                    "shape_probabilities": dict(sample.shape_probabilities),
                    "named_icon_fill_style_support": list(sample.fill_style_support),
                    "fill_style_probabilities": dict(sample.fill_style_probabilities),
                },
            },
            "render_spec": named_strip_render_spec(
                render_params=render_params,
                panel_geometry=scene.panel_geometry,
                sampled_palette_rgb=scene.sampled_palette_rgb,
                cell_box_width_px=int(scene.cell_box_width_px),
                cell_box_height_px=int(scene.cell_box_height_px),
                fill_style_support=sample.fill_style_support,
            ),
            "render_map": named_strip_render_map(icons=scene.icons, selected_instance_ids=selected_instance_ids),
            "execution_trace": {
                "scene_variant": "single_panel_named_strip_row",
                "query_id": str(sample.query_id),
                "question_format": "named_shape_run_length",
                "target_shape_id": str(sample.target_shape_id),
                "target_shape_name": str(sample.target_shape_name),
                "strip_length": int(sample.strip_length),
                "shape_ids_by_cell": [str(value) for value in sample.shape_ids],
                "target_runs": [
                    {"start_index": int(start), "end_index": int(end), "length": int(end) - int(start) + 1}
                    for start, end in sample.target_runs
                ],
                "target_run_lengths": [int(value) for value in target_run_lengths],
                "selected_run_indices": [int(index) for index in sample.selected_run_indices],
                "selected_run_instance_ids": list(selected_instance_ids),
                "answer": int(sample.answer),
            },
            "witness_symbolic": {
                "query_id": str(sample.query_id),
                "target_shape_id": str(sample.target_shape_id),
                "target_shape_name": str(sample.target_shape_name),
                "answer": int(sample.answer),
                "selected_run_indices": [int(index) for index in sample.selected_run_indices],
                "selected_run_instance_ids": list(selected_instance_ids),
            },
            "projected_annotation": dict(annotation_payload["projected_annotation"]),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(sample.answer)),
            annotation_gt=TypedValue(type=str(annotation_payload["annotation_type"]), value=list(annotation_payload["annotation_value"])),
            image=scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(sample.query_id),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
        )


__all__ = ["IconsNamedStripShapeRunLengthTask"]
