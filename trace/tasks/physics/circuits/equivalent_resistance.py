"""Physics circuits task for equivalent-resistance reasoning from resistor diagrams."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.variant_sampling import (
    apply_balanced_variant_sampling,
    resolve_compatible_scene_query_variants,
    resolve_variant,
)
from ..shared.circuit_scene import RenderedCircuitScene, render_resistor_network_scene
from ..shared.complexity import build_physics_circuit_resistance_complexity
from ..shared.style import SUPPORTED_PHYSICS_COLOR_NAMES
from ..shared.support_sampling import resolve_integer_choice, resolve_integer_support
from ..shared.visual_defaults import load_physics_background_defaults, load_physics_noise_defaults


TASK_ID = "task_physics_circuits_equivalent_resistance"
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "parallel",
    "simple_series_parallel",
)
SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = ("total_resistance",)
COMPATIBILITY: Dict[str, Sequence[str]] = {
    "parallel": SUPPORTED_QUERY_VARIANTS,
    "simple_series_parallel": SUPPORTED_QUERY_VARIANTS,
}


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for resistor-network scenes."""

    canvas_width: int = 940
    canvas_height: int = 560
    terminal_left_x_px: int = 104
    terminal_radius_px: int = 12
    terminal_font_size_px: int = 24
    wire_width_px: int = 5
    resistor_box_width_px: int = 96
    resistor_box_height_px: int = 46
    resistor_font_size_px: int = 24
    label_stroke_width_px: int = 3
    parallel_rail_left_x_px: int = 268
    parallel_branch_top_y_px: int = 190
    parallel_branch_bottom_y_px: int = 430
    series_parallel_branch_left_x_px: int = 360
    resistor_value_min: int = 1
    resistor_value_max: int = 12
    parallel_target_answer_support: Tuple[int, ...] = (1, 2, 3, 4, 5, 6)
    simple_series_parallel_target_answer_support: Tuple[int, ...] = tuple(range(2, 19))


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved scene/query axes and answer support for one instance."""

    scene_variant: str
    query_variant: str
    accent_color_name: str
    target_answer: int
    scene_variant_probabilities: Dict[str, float]
    query_variant_probabilities: Dict[str, float]
    accent_color_name_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _CircuitLayout:
    """One sampled resistor network satisfying the requested total."""

    scene_variant: str
    series_values: Tuple[int, ...]
    parallel_values: Tuple[int, ...]
    target_answer: int
    series_parallel_orientation: str | None


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("physics", "circuits")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_physics_background_defaults(task_group="circuits")
POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(task_group="circuits", apply_prob=0.0)


def _target_support_key(scene_variant: str) -> str:
    """Return the config support key for one scene variant."""

    return {
        "parallel": "parallel_target_answer_support",
        "simple_series_parallel": "simple_series_parallel_target_answer_support",
    }[str(scene_variant)]


def _resolve_target_answer(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    scene_variant: str,
) -> Tuple[int, Dict[str, float]]:
    """Resolve the sampled target resistance support for one scene family."""

    support_key = _target_support_key(str(scene_variant))
    fallback = getattr(_DEFAULTS, support_key)
    return resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=str(support_key),
        explicit_key="target_answer",
        fallback_support=fallback,
        namespace=f"{TASK_ID}.target_answer.{str(scene_variant)}",
        balanced_flag_key="balanced_target_answer_sampling",
    )


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve one compatible scene/query pair plus answer support."""

    axis_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.axes")
    scene_variant, scene_probs, query_variant, query_probs = resolve_compatible_scene_query_variants(
        axis_rng,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_scene_variants=SUPPORTED_SCENE_VARIANTS,
        supported_query_variants=SUPPORTED_QUERY_VARIANTS,
        compatibility=COMPATIBILITY,
        scene_sampling_namespace=f"{TASK_ID}.scene_variant",
        query_sampling_namespace=f"{TASK_ID}.query_variant",
    )
    target_answer, target_answer_probabilities = _resolve_target_answer(
        instance_seed=int(instance_seed),
        params=params,
        scene_variant=str(scene_variant),
    )
    color_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.accent_color_name")
    accent_color_name, accent_color_name_probabilities = resolve_variant(
        color_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_PHYSICS_COLOR_NAMES,
        explicit_key="accent_color_name",
        weights_key="accent_color_name_weights",
    )
    accent_color_name = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(accent_color_name),
        variant_probabilities=accent_color_name_probabilities,
        supported_variants=SUPPORTED_PHYSICS_COLOR_NAMES,
        balance_flag_key="balanced_accent_color_name_sampling",
        explicit_key="accent_color_name",
        weights_key="accent_color_name_weights",
        sampling_namespace=f"{TASK_ID}.accent_color_name",
    )
    return _ResolvedAxes(
        scene_variant=str(scene_variant),
        query_variant=str(query_variant),
        accent_color_name=str(accent_color_name),
        target_answer=int(target_answer),
        scene_variant_probabilities=dict(scene_probs),
        query_variant_probabilities=dict(query_probs),
        accent_color_name_probabilities=dict(accent_color_name_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
    )


def _sorted_int_tuple(*values: int) -> Tuple[int, ...]:
    """Return a canonical sorted integer tuple."""

    return tuple(sorted(int(value) for value in values))


def _series_chain_candidates_for_total(
    *,
    target_total: int,
    resistor_count: int,
    resistor_value_min: int,
    resistor_value_max: int,
) -> List[Tuple[int, ...]]:
    """Enumerate feasible fixed-length series chains for one target total."""

    candidates: List[Tuple[int, ...]] = []
    if int(resistor_count) == 1:
        if int(resistor_value_min) <= int(target_total) <= int(resistor_value_max):
            return [(int(target_total),)]
        return []
    if int(resistor_count) == 2:
        for first in range(int(resistor_value_min), int(resistor_value_max) + 1):
            second = int(target_total) - int(first)
            if int(first) <= int(second) <= int(resistor_value_max):
                candidates.append(_sorted_int_tuple(int(first), int(second)))
        return candidates
    if int(resistor_count) != 3:
        raise ValueError("series-chain candidates only support counts 1..3")
    for first in range(int(resistor_value_min), int(resistor_value_max) + 1):
        for second in range(int(first), int(resistor_value_max) + 1):
            third = int(target_total) - int(first) - int(second)
            if int(second) <= int(third) <= int(resistor_value_max):
                candidates.append(_sorted_int_tuple(int(first), int(second), int(third)))
    deduped: List[Tuple[int, ...]] = []
    seen: set[Tuple[int, ...]] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        deduped.append(candidate)
    return deduped


def _parallel_bank_candidates_for_total(
    *,
    target_answer: int,
    resistor_count: int,
    resistor_value_min: int,
    resistor_value_max: int,
) -> List[Tuple[int, ...]]:
    """Enumerate feasible fixed-length parallel resistor banks for one target total."""

    from fractions import Fraction

    if int(resistor_count) < 2:
        raise ValueError("parallel banks require at least two resistors")
    values = range(int(resistor_value_min), int(resistor_value_max) + 1)
    candidates: List[Tuple[int, ...]] = []

    def search(prefix: Tuple[int, ...], start_value: int) -> None:
        if len(prefix) == int(resistor_count):
            reciprocal_sum = sum(Fraction(1, int(value)) for value in prefix)
            if reciprocal_sum == Fraction(1, int(target_answer)):
                candidates.append(tuple(int(value) for value in prefix))
            return
        for value in range(int(start_value), int(resistor_value_max) + 1):
            search(prefix + (int(value),), int(value))

    search(tuple(), int(resistor_value_min))
    deduped: List[Tuple[int, ...]] = []
    seen: set[Tuple[int, ...]] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        deduped.append(candidate)
    return deduped


def _series_parallel_candidates_for_total(
    *,
    target_answer: int,
    resistor_value_min: int,
    resistor_value_max: int,
) -> List[Tuple[Tuple[int, ...], Tuple[int, ...]]]:
    """Enumerate feasible series-plus-parallel layouts with at least four resistors."""

    candidates: List[Tuple[Tuple[int, ...], Tuple[int, ...]]] = []
    for series_count, parallel_count in ((1, 3), (2, 2), (2, 3)):
        min_series_total = int(series_count) * int(resistor_value_min)
        max_series_total = int(series_count) * int(resistor_value_max)
        for series_total in range(int(min_series_total), int(max_series_total) + 1):
            parallel_target = int(target_answer) - int(series_total)
            if int(parallel_target) < 1:
                continue
            series_candidates = _series_chain_candidates_for_total(
                target_total=int(series_total),
                resistor_count=int(series_count),
                resistor_value_min=int(resistor_value_min),
                resistor_value_max=int(resistor_value_max),
            )
            if not series_candidates:
                continue
            parallel_candidates = _parallel_bank_candidates_for_total(
                target_answer=int(parallel_target),
                resistor_count=int(parallel_count),
                resistor_value_min=int(resistor_value_min),
                resistor_value_max=int(resistor_value_max),
            )
            if not parallel_candidates:
                continue
            for series_values in series_candidates:
                for parallel_values in parallel_candidates:
                    candidates.append(
                        (
                            tuple(int(value) for value in series_values),
                            tuple(int(value) for value in parallel_values),
                        )
                    )
    return candidates


def _sample_layout(
    rng,
    *,
    scene_variant: str,
    target_answer: int,
    params: Mapping[str, Any],
) -> _CircuitLayout:
    """Sample one resistor network that realizes the requested total."""

    resistor_value_min = int(
        params.get("resistor_value_min", group_default(_GEN_DEFAULTS, "resistor_value_min", _DEFAULTS.resistor_value_min))
    )
    resistor_value_max = int(
        params.get("resistor_value_max", group_default(_GEN_DEFAULTS, "resistor_value_max", _DEFAULTS.resistor_value_max))
    )
    if str(scene_variant) == "parallel":
        branch_counts = [3, 4]
        rng.shuffle(branch_counts)
        candidates: List[Tuple[int, ...]] = []
        for branch_count in branch_counts:
            candidates = _parallel_bank_candidates_for_total(
                target_answer=int(target_answer),
                resistor_count=int(branch_count),
                resistor_value_min=int(resistor_value_min),
                resistor_value_max=int(resistor_value_max),
            )
            if candidates:
                break
        if not candidates:
            raise ValueError(f"no parallel candidates for target {target_answer}")
        chosen = list(candidates[int(rng.randrange(len(candidates)))])
        rng.shuffle(chosen)
        return _CircuitLayout(
            scene_variant=str(scene_variant),
            series_values=tuple(),
            parallel_values=tuple(int(value) for value in chosen),
            target_answer=int(target_answer),
            series_parallel_orientation=None,
        )
    candidates = _series_parallel_candidates_for_total(
        target_answer=int(target_answer),
        resistor_value_min=int(resistor_value_min),
        resistor_value_max=int(resistor_value_max),
    )
    if not candidates:
        raise ValueError(f"no series_parallel candidates for target {target_answer}")
    chosen = list(candidates[int(rng.randrange(len(candidates)))])
    series_values = list(chosen[0])
    branch_values = list(chosen[1])
    rng.shuffle(series_values)
    rng.shuffle(branch_values)
    orientation = "series_then_parallel" if rng.random() < 0.5 else "parallel_then_series"
    return _CircuitLayout(
        scene_variant=str(scene_variant),
        series_values=tuple(int(value) for value in series_values),
        parallel_values=tuple(int(value) for value in branch_values),
        target_answer=int(target_answer),
        series_parallel_orientation=str(orientation),
    )


def _build_prompt_json_examples() -> Tuple[str, str]:
    """Return prompt JSON examples for resistor-network count answers."""

    answer_and_evidence = {
        "evidence": [
            [322, 167, 418, 213],
            [322, 257, 418, 303],
            [322, 347, 418, 393]
        ],
        "answer": 2,
    }
    answer_only = {"answer": 2}
    return (
        json.dumps(answer_and_evidence, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
        json.dumps(answer_only, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
    )


@register_task
class PhysicsCircuitsEquivalentResistanceTask:
    """Return one simple equivalent-resistance question from a resistor diagram."""

    task_id = TASK_ID
    domain = "physics"
    task_group = "circuits"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        rendered_scene: RenderedCircuitScene | None = None
        layout: _CircuitLayout | None = None

        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                layout = _sample_layout(
                    attempt_rng,
                    scene_variant=str(axes.scene_variant),
                    target_answer=int(axes.target_answer),
                    params=params,
                )
            except ValueError:
                continue

            background, background_meta = make_background_canvas(
                canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
                canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
                instance_seed=int(instance_seed),
                params=params,
                default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
            )
            rendered_scene = render_resistor_network_scene(
                scene_variant=str(layout.scene_variant),
                series_values=list(layout.series_values),
                parallel_values=list(layout.parallel_values),
                background=background,
                render_defaults={
                    key: params.get(key, group_default(_RENDER_DEFAULTS, key, getattr(_DEFAULTS, key)))
                    for key in (
                        "canvas_width",
                        "canvas_height",
                        "terminal_left_x_px",
                        "terminal_radius_px",
                        "terminal_font_size_px",
                        "wire_width_px",
                        "resistor_box_width_px",
                        "resistor_box_height_px",
                        "resistor_font_size_px",
                        "label_stroke_width_px",
                        "parallel_rail_left_x_px",
                        "parallel_branch_top_y_px",
                        "parallel_branch_bottom_y_px",
                        "series_parallel_branch_left_x_px",
                    )
                },
                accent_color_name=str(axes.accent_color_name),
                series_parallel_orientation=(
                    str(layout.series_parallel_orientation)
                    if layout.series_parallel_orientation is not None
                    else "series_then_parallel"
                ),
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
                    "evidence_hint_total_resistance",
                    "object_description_parallel",
                    "object_description_simple_series_parallel",
                ),
                context=f"prompt defaults for {self.task_id}",
            )
            json_example, json_example_answer_only = _build_prompt_json_examples()
            prompt_selection = render_task_prompt_variants(
                domain=self.domain,
                task_group=self.task_group,
                bundle_id=str(prompt_defaults["bundle_id"]),
                task_family_key=str(prompt_defaults["task_family_key"]),
                task_key=str(prompt_defaults["task_key"]),
                task_variant_key=str(axes.query_variant),
                answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
                slots={
                    "object_description": str(prompt_defaults[f"object_description_{str(axes.scene_variant)}"]),
                    "json_output_contract": str(prompt_defaults["json_output_contract"]),
                    "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                    "evidence_hint": str(prompt_defaults["evidence_hint_total_resistance"]),
                    "answer_hint": str(prompt_defaults["answer_hint"]),
                    "json_example": str(json_example),
                    "json_example_answer_only": str(json_example_answer_only),
                },
                instance_seed=int(instance_seed),
            )
            prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

            answer_gt = TypedValue(type="integer", value=int(axes.target_answer))
            evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in rendered_scene.evidence_bboxes])
            complexity = build_physics_circuit_resistance_complexity(
                task_group_defaults=_TASK_GROUP_DEFAULTS,
                task_id=self.task_id,
                scene_variant=str(axes.scene_variant),
                resistor_count=len(rendered_scene.resistor_specs),
                target_answer=int(axes.target_answer),
            )
            support_key = _target_support_key(str(axes.scene_variant))
            trace_payload = {
                "scene_ir": {
                    "scene_kind": f"physics_resistor_network_{str(axes.scene_variant)}",
                    "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                    "relations": {
                        "scene_variant": str(axes.scene_variant),
                        "query_variant": str(axes.query_variant),
                        "task_variant": str(axes.query_variant),
                        "target_answer": int(axes.target_answer),
                        "accent_color_name": str(axes.accent_color_name),
                        "evidence_entity_ids": list(rendered_scene.evidence_entity_ids),
                    },
                },
                "query_spec": {
                    "task_variant": str(axes.query_variant),
                    "template_id": str(prompt_defaults["bundle_id"]),
                    "prompt_variant": dict(prompt_artifacts.prompt_variant),
                    "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                    "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                    "params": {
                        "scene_variant": str(axes.scene_variant),
                        "query_variant": str(axes.query_variant),
                        "task_variant": str(axes.query_variant),
                        "accent_color_name": str(axes.accent_color_name),
                        "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                        "query_variant_probabilities": dict(axes.query_variant_probabilities),
                        "task_variant_probabilities": dict(axes.query_variant_probabilities),
                        "accent_color_name_probabilities": dict(axes.accent_color_name_probabilities),
                        "target_answer": int(axes.target_answer),
                        "target_answer_probabilities": dict(axes.target_answer_probabilities),
                    },
                },
                "render_spec": {
                    "scene_variant": str(axes.scene_variant),
                    "canvas_width": int(image.size[0]),
                    "canvas_height": int(image.size[1]),
                    "accent_color_name": str(axes.accent_color_name),
                },
                "render_map": dict(rendered_scene.render_map),
                "execution_trace": {
                    "scene_variant": str(axes.scene_variant),
                    "query_variant": str(axes.query_variant),
                    "task_variant": str(axes.query_variant),
                    "accent_color_name": str(axes.accent_color_name),
                    "target_answer": int(axes.target_answer),
                    "target_answer_support": list(
                        resolve_integer_support(
                            params,
                            gen_defaults=_GEN_DEFAULTS,
                            key=str(support_key),
                            fallback=getattr(_DEFAULTS, support_key),
                        )
                    ),
                    "series_parallel_orientation": None if layout is None else layout.series_parallel_orientation,
                    "series_values": [] if layout is None else [int(value) for value in layout.series_values],
                    "parallel_values": [] if layout is None else [int(value) for value in layout.parallel_values],
                    "resistor_specs": [
                        {
                            "resistor_id": str(spec.resistor_id),
                            "value": int(spec.value),
                        }
                        for spec in rendered_scene.resistor_specs
                    ],
                    "evidence_entity_ids": list(rendered_scene.evidence_entity_ids),
                },
                "witness_symbolic": {
                    "type": "id_set",
                    "ids": [str(item) for item in rendered_scene.evidence_entity_ids],
                },
                "projected_evidence": {
                    "bbox_set": [list(bbox) for bbox in rendered_scene.evidence_bboxes],
                },
                "background": background_meta,
                "post_image_noise": post_noise_meta,
            }
            return TaskOutput(
                prompt=str(prompt_artifacts.prompt),
                prompt_variants=dict(prompt_artifacts.prompt_variants),
                answer_gt=answer_gt,
                evidence_gt=evidence_gt,
                image=image,
                image_id="img0",
                trace_payload=trace_payload,
                complexity=complexity,
                task_versions=default_task_versions(),
                task_variant=str(axes.query_variant),
            )

        raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts")


__all__ = ["PhysicsCircuitsEquivalentResistanceTask"]
