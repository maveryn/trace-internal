"""Spinner probability symbolic tasks."""

from __future__ import annotations

from collections import Counter
from dataclasses import replace
from math import gcd
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import required_group_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ..shared.common import (
    get_int_param as _get_int,
    get_int_range as _get_range,
    load_symbolic_task_defaults,
    projected_symbolic_bbox_annotation,
    resolve_symbolic_axis_variant,
)
from ..shared.spinner_scene import (
    SUPPORTED_SPINNER_SCENE_VARIANTS,
    SpinnerRenderParams,
    render_spinner_probability_scene,
)
from ..shared.scene_style import make_symbolic_scene_background, resolve_symbolic_scene_style
from ..shared.visual_defaults import load_symbolic_noise_defaults


SCENE_ID = "spinner_probability"
SINGLE_ATTRIBUTE_TASK_ID = "task_symbolic__spinner_probability__single_attribute_probability"
MULTI_ATTRIBUTE_AND_TASK_ID = "task_symbolic__spinner_probability__multi_attribute_and_probability"
MULTI_ATTRIBUTE_OR_TASK_ID = "task_symbolic__spinner_probability__multi_attribute_or_probability"
PAIR_TASK_ID = "task_symbolic__spinner_probability__spinner_pair_event_value"

SINGLE_QUERY_IDS: Tuple[str, ...] = (
    "single_color_probability",
    "single_shape_probability",
    "single_color_and_shape_probability",
    "single_color_or_shape_probability",
)
SINGLE_ATTRIBUTE_QUERY_IDS: Tuple[str, ...] = ("single_color_probability", "single_shape_probability")
MULTI_ATTRIBUTE_AND_QUERY_IDS: Tuple[str, ...] = ("single_color_and_shape_probability",)
MULTI_ATTRIBUTE_OR_QUERY_IDS: Tuple[str, ...] = ("single_color_or_shape_probability",)
PAIR_QUERY_IDS: Tuple[str, ...] = (
    "pair_both_target_color_probability",
    "pair_at_least_one_target_color_probability",
    "pair_same_color_probability",
)

COLOR_PALETTE: Tuple[Tuple[str, Tuple[int, int, int]], ...] = (
    ("red", (213, 76, 76)),
    ("blue", (58, 112, 194)),
    ("green", (55, 151, 103)),
    ("yellow", (232, 184, 57)),
    ("purple", (139, 101, 201)),
    ("orange", (220, 126, 58)),
    ("teal", (42, 154, 166)),
    ("pink", (207, 88, 143)),
)
SHAPE_POOL: Tuple[str, ...] = ("circle", "triangle", "square", "diamond", "star")

_SCENE_LOAD = {
    "spinner_clean": 0.16,
    "spinner_card": 0.22,
    "spinner_notebook": 0.24,
}
_REASONING_LOAD = {
    "single_color_probability": 0.26,
    "single_shape_probability": 0.30,
    "single_color_and_shape_probability": 0.42,
    "single_color_or_shape_probability": 0.45,
    "pair_both_target_color_probability": 0.42,
    "pair_at_least_one_target_color_probability": 0.50,
    "pair_same_color_probability": 0.54,
}

_TASK_GROUP_DEFAULTS = get_scene_defaults("symbolic", "probability")
POST_IMAGE_NOISE_DEFAULTS = load_symbolic_noise_defaults(scene_id="probability", apply_prob=0.15)


def _load_defaults(task_id: str) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, float]]:
    return load_symbolic_task_defaults(_TASK_GROUP_DEFAULTS, task_id=str(task_id))


def _resolve_scene_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    return resolve_symbolic_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_SPINNER_SCENE_VARIANTS,
        task_id=str(task_id),
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def _resolve_query_id(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    supported_queries: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    effective_params = dict(params)
    if effective_params.get("query_id") is None and effective_params.get("query_variant") is not None:
        effective_params["query_id"] = str(effective_params["query_variant"])
    return resolve_symbolic_axis_variant(
        params=effective_params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=[str(query) for query in supported_queries],
        task_id=str(task_id),
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )


def _resolve_render_params(render_defaults: Mapping[str, Any]) -> SpinnerRenderParams:
    return SpinnerRenderParams(
        canvas_width=int(render_defaults.get("canvas_width", 1100)),
        canvas_height=int(render_defaults.get("canvas_height", 780)),
        single_center_x_px=int(render_defaults.get("single_center_x_px", 550)),
        single_center_y_px=int(render_defaults.get("single_center_y_px", 360)),
        single_radius_px=int(render_defaults.get("single_radius_px", 235)),
        pair_left_center_x_px=int(render_defaults.get("pair_left_center_x_px", 350)),
        pair_right_center_x_px=int(render_defaults.get("pair_right_center_x_px", 750)),
        pair_center_y_px=int(render_defaults.get("pair_center_y_px", 360)),
        pair_radius_px=int(render_defaults.get("pair_radius_px", 180)),
        panel_padding_px=int(render_defaults.get("panel_padding_px", 34)),
        panel_corner_radius_px=int(render_defaults.get("panel_corner_radius_px", 22)),
        sector_outline_width_px=int(render_defaults.get("sector_outline_width_px", 3)),
        pointer_width_px=int(render_defaults.get("pointer_width_px", 5)),
        hub_radius_px=int(render_defaults.get("hub_radius_px", 18)),
        badge_width_px=int(render_defaults.get("badge_width_px", 54)),
        badge_height_px=int(render_defaults.get("badge_height_px", 46)),
        number_font_size_px=int(render_defaults.get("number_font_size_px", 21)),
        title_font_size_px=int(render_defaults.get("title_font_size_px", 28)),
        subtitle_font_size_px=int(render_defaults.get("subtitle_font_size_px", 17)),
    )


def _format_fraction(numerator: int, denominator: int) -> str:
    if int(denominator) <= 0:
        raise ValueError("probability denominator must be positive")
    common = gcd(abs(int(numerator)), abs(int(denominator)))
    return f"{int(numerator) // common}/{int(denominator) // common}"


def _sample_spinner_sectors(
    *,
    spinner_id: str,
    sector_count: int,
    rng,
    color_pool_size: int,
    number_min: int,
    number_max: int,
    show_number: bool = True,
    show_shape: bool = True,
) -> List[Dict[str, Any]]:
    color_pool = list(COLOR_PALETTE[: max(3, min(len(COLOR_PALETTE), int(color_pool_size)))])
    sectors: List[Dict[str, Any]] = []
    for index in range(int(sector_count)):
        color_name, color_rgb = color_pool[int(rng.randrange(len(color_pool)))]
        shape = str(SHAPE_POOL[int(rng.randrange(len(SHAPE_POOL)))])
        number = int(rng.randint(int(number_min), int(number_max)))
        sectors.append(
            {
                "sector_id": f"{spinner_id}_sector_{index}",
                "spinner_id": str(spinner_id),
                "sector_index": int(index),
                "color_name": str(color_name),
                "color_rgb": [int(value) for value in color_rgb],
                "shape": str(shape),
                "number": int(number),
                "show_number": bool(show_number),
                "show_shape": bool(show_shape),
            }
        )
    return sectors


def _color_names(sectors: Sequence[Mapping[str, Any]]) -> List[str]:
    return sorted({str(sector["color_name"]) for sector in sectors})


def _shape_names(sectors: Sequence[Mapping[str, Any]]) -> List[str]:
    return sorted({str(sector["shape"]) for sector in sectors})


def _valid_favorable_count(count: int, total: int, *, min_count: int, max_count: int) -> bool:
    return int(min_count) <= int(count) <= min(int(total) - 1, int(max_count))


def _choose_single_event(
    *,
    query_id: str,
    sectors: Sequence[Mapping[str, Any]],
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    rng,
) -> Dict[str, Any]:
    total = len(sectors)
    min_count = _get_int(params, gen_defaults, "single_favorable_count_min", 2)
    max_count = _get_int(params, gen_defaults, "single_favorable_count_max", max(2, int(total) - 2))
    candidates: List[Dict[str, Any]] = []
    colors = _color_names(sectors)
    shapes = _shape_names(sectors)

    if str(query_id) == "single_color_probability":
        for color in colors:
            favorable = [
                str(sector["sector_id"])
                for sector in sectors
                if str(sector["color_name"]) == str(color)
            ]
            if _valid_favorable_count(len(favorable), int(total), min_count=int(min_count), max_count=int(max_count)):
                candidates.append(
                    {
                        "event_description": str(color),
                        "target_color": str(color),
                        "favorable_sector_ids": list(favorable),
                    }
                )
    elif str(query_id) == "single_shape_probability":
        for shape in shapes:
            favorable = [
                str(sector["sector_id"])
                for sector in sectors
                if str(sector["shape"]) == str(shape)
            ]
            if _valid_favorable_count(len(favorable), int(total), min_count=int(min_count), max_count=int(max_count)):
                candidates.append(
                    {
                        "event_description": f"marked with a {shape}",
                        "target_shape": str(shape),
                        "favorable_sector_ids": list(favorable),
                    }
                )
    elif str(query_id) in {"single_color_and_shape_probability", "single_color_or_shape_probability"}:
        for color in colors:
            for shape in shapes:
                if str(query_id) == "single_color_and_shape_probability":
                    favorable = [
                        str(sector["sector_id"])
                        for sector in sectors
                        if str(sector["color_name"]) == str(color) and str(sector["shape"]) == str(shape)
                    ]
                    description = f"{color} and marked with a {shape}"
                elif str(query_id) == "single_color_or_shape_probability":
                    favorable = [
                        str(sector["sector_id"])
                        for sector in sectors
                        if str(sector["color_name"]) == str(color) or str(sector["shape"]) == str(shape)
                    ]
                    description = f"{color} or marked with a {shape}"
                if _valid_favorable_count(len(favorable), int(total), min_count=int(min_count), max_count=int(max_count)):
                    candidates.append(
                        {
                            "event_description": description,
                            "target_color": str(color),
                            "target_shape": str(shape),
                            "favorable_sector_ids": list(favorable),
                        }
                    )
    else:
        raise RuntimeError(f"unsupported single-spinner probability query: {query_id}")

    if not candidates:
        raise RuntimeError("failed to choose a nontrivial single-spinner probability event")
    rng.shuffle(candidates)
    selected = dict(candidates[0])
    selected["favorable_outcome_count"] = int(len(selected["favorable_sector_ids"]))
    selected["total_outcome_count"] = int(total)
    selected["answer_value"] = _format_fraction(int(selected["favorable_outcome_count"]), int(total))
    return selected


def _choose_pair_event(
    *,
    query_id: str,
    sectors_a: Sequence[Mapping[str, Any]],
    sectors_b: Sequence[Mapping[str, Any]],
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    rng,
) -> Dict[str, Any]:
    total = int(len(sectors_a) * len(sectors_b))
    min_count = _get_int(params, gen_defaults, "pair_favorable_count_min", 3)
    max_count = _get_int(params, gen_defaults, "pair_favorable_count_max", max(3, int(total) - 3))
    candidates: List[Dict[str, Any]] = []

    if str(query_id) == "pair_both_target_color_probability":
        shared_colors = sorted(set(_color_names(sectors_a)) & set(_color_names(sectors_b)))
        for color in shared_colors:
            favorable_pairs = [
                [str(a["sector_id"]), str(b["sector_id"])]
                for a in sectors_a
                for b in sectors_b
                if str(a["color_name"]) == str(color) and str(b["color_name"]) == str(color)
            ]
            if _valid_favorable_count(len(favorable_pairs), total, min_count=min_count, max_count=max_count):
                supporting = [
                    str(sector["sector_id"])
                    for sector in [*sectors_a, *sectors_b]
                    if str(sector["color_name"]) == str(color)
                ]
                candidates.append(
                    {
                        "event_description": f"Spinner A lands on {color} and Spinner B lands on {color}",
                        "target_color": str(color),
                        "favorable_pairs": list(favorable_pairs),
                        "supporting_sector_ids": list(supporting),
                    }
                )
    elif str(query_id) == "pair_at_least_one_target_color_probability":
        colors = sorted(set(_color_names(sectors_a)) | set(_color_names(sectors_b)))
        for color in colors:
            favorable_pairs = [
                [str(a["sector_id"]), str(b["sector_id"])]
                for a in sectors_a
                for b in sectors_b
                if str(a["color_name"]) == str(color) or str(b["color_name"]) == str(color)
            ]
            if _valid_favorable_count(len(favorable_pairs), total, min_count=min_count, max_count=max_count):
                supporting = [
                    str(sector["sector_id"])
                    for sector in [*sectors_a, *sectors_b]
                    if str(sector["color_name"]) == str(color)
                ]
                candidates.append(
                    {
                        "event_description": f"at least one spinner lands on {color}",
                        "target_color": str(color),
                        "favorable_pairs": list(favorable_pairs),
                        "supporting_sector_ids": list(supporting),
                    }
                )
    elif str(query_id) == "pair_same_color_probability":
        shared_colors = sorted(set(_color_names(sectors_a)) & set(_color_names(sectors_b)))
        favorable_pairs = [
            [str(a["sector_id"]), str(b["sector_id"])]
            for a in sectors_a
            for b in sectors_b
            if str(a["color_name"]) == str(b["color_name"])
        ]
        if _valid_favorable_count(len(favorable_pairs), total, min_count=min_count, max_count=max_count):
            supporting = [
                str(sector["sector_id"])
                for sector in [*sectors_a, *sectors_b]
                if str(sector["color_name"]) in set(shared_colors)
            ]
            candidates.append(
                {
                    "event_description": "both spinners show the same color",
                    "favorable_pairs": list(favorable_pairs),
                    "supporting_sector_ids": list(supporting),
                }
            )
    else:
        raise RuntimeError(f"unsupported pair-spinner probability query: {query_id}")

    if not candidates:
        raise RuntimeError("failed to choose a nontrivial pair-spinner probability event")
    rng.shuffle(candidates)
    selected = dict(candidates[0])
    selected["favorable_outcome_count"] = int(len(selected["favorable_pairs"]))
    selected["total_outcome_count"] = int(total)
    selected["answer_value"] = _format_fraction(int(selected["favorable_outcome_count"]), int(total))
    return selected


def _build_single_dataset(
    *,
    query_id: str,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{task_id}.single_dataset")
    sector_min, sector_max = _get_range(
        params,
        gen_defaults,
        min_key="single_sector_count_min",
        max_key="single_sector_count_max",
        fallback_min=6,
        fallback_max=10,
    )
    color_pool_size = _get_int(params, gen_defaults, "single_color_pool_size", 6)
    number_min, number_max = _get_range(
        params,
        gen_defaults,
        min_key="number_min",
        max_key="number_max",
        fallback_min=1,
        fallback_max=12,
    )
    for _attempt in range(300):
        sector_count = int(params.get("single_sector_count", rng.randint(int(sector_min), int(sector_max))))
        sectors = _sample_spinner_sectors(
            spinner_id="spinner",
            sector_count=int(sector_count),
            rng=rng,
            color_pool_size=int(color_pool_size),
            number_min=int(number_min),
            number_max=int(number_max),
            show_number=False,
            show_shape=True,
        )
        try:
            event = _choose_single_event(
                query_id=str(query_id),
                sectors=sectors,
                params=params,
                gen_defaults=gen_defaults,
                rng=rng,
            )
            return {
                "mode": "single",
                "spinner_specs": [{"spinner_id": "spinner", "title": "Spinner", "sectors": sectors}],
                "sector_count": int(sector_count),
                "sector_count_range": [int(sector_min), int(sector_max)],
                "event": dict(event),
                "answer_value": str(event["answer_value"]),
                "calculation_supporting_item_ids": list(event["favorable_sector_ids"]),
                "annotation_item_ids": ["spinner_panel"],
            }
        except RuntimeError:
            continue
    raise RuntimeError("failed to build single-spinner probability dataset")


def _build_pair_dataset(
    *,
    query_id: str,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{task_id}.pair_dataset")
    sector_min, sector_max = _get_range(
        params,
        gen_defaults,
        min_key="pair_sector_count_min",
        max_key="pair_sector_count_max",
        fallback_min=4,
        fallback_max=6,
    )
    color_pool_size = _get_int(params, gen_defaults, "pair_color_pool_size", 5)
    number_min, number_max = _get_range(
        params,
        gen_defaults,
        min_key="number_min",
        max_key="number_max",
        fallback_min=1,
        fallback_max=12,
    )
    for _attempt in range(500):
        count_a = int(params.get("pair_sector_count_a", rng.randint(int(sector_min), int(sector_max))))
        count_b = int(params.get("pair_sector_count_b", rng.randint(int(sector_min), int(sector_max))))
        sectors_a = _sample_spinner_sectors(
            spinner_id="spinner_a",
            sector_count=int(count_a),
            rng=rng,
            color_pool_size=int(color_pool_size),
            number_min=int(number_min),
            number_max=int(number_max),
            show_number=False,
            show_shape=False,
        )
        sectors_b = _sample_spinner_sectors(
            spinner_id="spinner_b",
            sector_count=int(count_b),
            rng=rng,
            color_pool_size=int(color_pool_size),
            number_min=int(number_min),
            number_max=int(number_max),
            show_number=False,
            show_shape=False,
        )
        try:
            event = _choose_pair_event(
                query_id=str(query_id),
                sectors_a=sectors_a,
                sectors_b=sectors_b,
                params=params,
                gen_defaults=gen_defaults,
                rng=rng,
            )
            return {
                "mode": "pair",
                "spinner_specs": [
                    {"spinner_id": "spinner_a", "title": "Spinner A", "sectors": sectors_a},
                    {"spinner_id": "spinner_b", "title": "Spinner B", "sectors": sectors_b},
                ],
                "sector_count_a": int(count_a),
                "sector_count_b": int(count_b),
                "sector_count_range": [int(sector_min), int(sector_max)],
                "event": dict(event),
                "answer_value": str(event["answer_value"]),
                "calculation_supporting_item_ids": list(event["supporting_sector_ids"]),
                "annotation_item_ids": ["spinner_a_panel", "spinner_b_panel"],
            }
        except RuntimeError:
            continue
    raise RuntimeError("failed to build pair-spinner probability dataset")


def _build_prompt(
    *,
    task_id: str,
    query_id: str,
    scene_variant: str,
    prompt_defaults: Mapping[str, Any],
    instance_seed: int,
    event_description: str,
) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
    prompt_values = required_group_defaults(
        prompt_defaults,
        (
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            f"object_description_{scene_variant}",
            "answer_hint",
            f"annotation_hint_{query_id}",
            f"json_example_{query_id}",
            f"json_example_answer_only_{query_id}",
        ),
        context=f"prompt defaults for {task_id}",
    )
    prompt_selection = render_task_prompt_variants(
        domain="symbolic",
        scene_id="probability",
        bundle_id=str(prompt_values["bundle_id"]),
        scene_key=str(prompt_values["scene_key"]),
        task_key=str(prompt_values["task_key"]),
        query_key=str(query_id),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        slots={
            "object_description": str(prompt_values[f"object_description_{scene_variant}"]),
            "event_description": str(event_description),
            "json_output_contract": str(prompt_values["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_values["json_output_contract_answer_only"]),
            "annotation_hint": str(prompt_values[f"annotation_hint_{query_id}"]),
            "answer_hint": str(prompt_values["answer_hint"]),
            "json_example": str(prompt_values[f"json_example_{query_id}"]),
            "json_example_answer_only": str(prompt_values[f"json_example_answer_only_{query_id}"]),
        },
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
    return str(prompt_artifacts.prompt), dict(prompt_artifacts.prompt_variants), {
        "prompt_variant": dict(prompt_artifacts.prompt_variant),
        "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
        "prompt_variants_for_trace": dict(prompt_artifacts.prompt_variants_for_trace),
        "bundle_id": str(prompt_values["bundle_id"]),
    }


class _SpinnerProbabilityBaseTask:
    """Base generator for spinner probability tasks."""

    domain = "symbolic"
    scene_id = "probability"
    default_dataset_enabled = True
    supported_query_ids: Tuple[str, ...]
    dataset_family: str

    def _build_dataset(
        self,
        *,
        query_id: str,
        params: Mapping[str, Any],
        gen_defaults: Mapping[str, Any],
        instance_seed: int,
    ) -> Dict[str, Any]:
        if str(self.dataset_family) == "single":
            return _build_single_dataset(
                query_id=str(query_id),
                params=params,
                gen_defaults=gen_defaults,
                instance_seed=int(instance_seed),
                task_id=str(self.task_id),
            )
        if str(self.dataset_family) != "pair":
            raise ValueError(f"unsupported spinner probability dataset_family: {self.dataset_family!r}")
        return _build_pair_dataset(
            query_id=str(query_id),
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=str(self.task_id),
        )

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, query_id_probabilities = _resolve_query_id(
            params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=str(self.task_id),
            supported_queries=self.supported_query_ids,
        )
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(
            params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=str(self.task_id),
        )
        dataset = self._build_dataset(
            query_id=str(query_id),
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
        )
        render_params = _resolve_render_params(render_defaults)
        scene_style, scene_style_meta = resolve_symbolic_scene_style(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.spinner_probability_background",
        )
        render_params = replace(
            render_params,
            style_overrides={
                "panel_fill": tuple(int(value) for value in scene_style.panel_fill_rgb),
                "panel_outline": tuple(int(value) for value in scene_style.panel_border_rgb),
                "sector_outline": tuple(int(value) for value in scene_style.grid_rgb),
                "text": tuple(int(value) for value in scene_style.text_rgb),
                "muted_text": tuple(int(value) for value in scene_style.text_rgb),
                "text_stroke": tuple(int(value) for value in scene_style.text_stroke_rgb),
                "badge_fill": tuple(int(value) for value in scene_style.option_fill_rgb),
                "badge_outline": tuple(int(value) for value in scene_style.panel_border_rgb),
                "shape_fill": tuple(int(value) for value in scene_style.text_rgb),
                "shape_outline": tuple(int(value) for value in scene_style.text_stroke_rgb),
                "hub_fill": tuple(int(value) for value in scene_style.option_fill_rgb),
                "pointer": tuple(int(value) for value in scene_style.mark_rgb),
            },
        )
        background, background_meta = make_symbolic_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=scene_style,
        )
        rendered_scene = render_spinner_probability_scene(
            background,
            scene_variant=str(scene_variant),
            mode=str(dataset["mode"]),
            spinner_specs=list(dataset["spinner_specs"]),
            render_params=render_params,
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        event = dict(dataset["event"])
        prompt, prompt_variants, prompt_meta = _build_prompt(
            task_id=str(self.task_id),
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            prompt_defaults=prompt_defaults,
            instance_seed=int(instance_seed),
            event_description=str(event["event_description"]),
        )
        annotation_item_ids = [str(item_id) for item_id in dataset["annotation_item_ids"]]
        calculation_supporting_item_ids = [str(item_id) for item_id in dataset["calculation_supporting_item_ids"]]
        annotation_projection = projected_symbolic_bbox_annotation(rendered_scene.item_bbox_map, annotation_item_ids)
        annotation_bboxes = [
            [round(float(value), 3) for value in bbox]
            for bbox in annotation_projection["bbox_set"]
        ]
        if len(annotation_bboxes) != len(annotation_item_ids):
            raise ValueError("spinner probability annotation projection dropped panel boxes")

        answer_value = str(dataset["answer_value"])
        answer_gt = TypedValue(type="string", value=str(answer_value))
        annotation_gt = TypedValue(type="bbox_set", value=list(annotation_bboxes))
        spinner_specs = [dict(spinner) for spinner in dataset["spinner_specs"]]
        all_sectors = [
            dict(sector)
            for spinner in spinner_specs
            for sector in spinner["sectors"]
        ]
        visual_scan_count = len(all_sectors)
        visual_scan_bounds = [6, 10] if str(dataset["mode"]) == "single" else [8, 12]
        outcome_count = int(event["total_outcome_count"])
        outcome_bounds = [6, 10] if str(dataset["mode"]) == "single" else [16, 36]
        visual_scan = normalize_int_with_bounds(int(visual_scan_count), visual_scan_bounds)
        outcome_load = normalize_int_with_bounds(int(outcome_count), outcome_bounds)
        reasoning_load = min(1.0, float(_REASONING_LOAD[str(query_id)]) + (0.12 * float(outcome_load)))

        trace_payload = {
            "scene_ir": {
                "scene_kind": "symbolic_probability_spinner_panel",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "scene_id": SCENE_ID,
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "answer_value": str(answer_value),
                    "event_description": str(event["event_description"]),
                },
            },
            "query_spec": {
                "query_id": str(query_id),
                "template_id": str(prompt_meta["bundle_id"]),
                "prompt_variant": dict(prompt_meta["prompt_variant"]),
                "prompt_variant_active_key": str(prompt_meta["prompt_variant_active_key"]),
                "prompt_variants": dict(prompt_meta["prompt_variants_for_trace"]),
                "params": {
                    "scene_id": SCENE_ID,
                    "query_id": str(query_id),
                    "query_id_probabilities": dict(query_id_probabilities),
                    "scene_variant": str(scene_variant),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "mode": str(dataset["mode"]),
                    "event_description": str(event["event_description"]),
                    "favorable_outcome_count": int(event["favorable_outcome_count"]),
                    "total_outcome_count": int(event["total_outcome_count"]),
                },
            },
            "render_spec": {
                "scene_id": SCENE_ID,
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "scene_style": dict(scene_style_meta),
                "post_image_noise": dict(post_noise_meta),
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "layout": str(dataset["mode"]),
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "sector_bboxes_px": {str(key): list(value) for key, value in rendered_scene.sector_bbox_map.items()},
                "panel_bboxes_px": {str(key): list(value) for key, value in rendered_scene.panel_bbox_map.items()},
                "item_bboxes_px": {str(key): list(value) for key, value in rendered_scene.item_bbox_map.items()},
                "annotation_source": "panel_bboxes_px",
            },
            "execution_trace": {
                "query_id": str(query_id),
                "query_id_probabilities": dict(query_id_probabilities),
                "scene_id": SCENE_ID,
                "scene_variant": str(scene_variant),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "mode": str(dataset["mode"]),
                "spinner_specs": spinner_specs,
                "sector_specs": all_sectors,
                "sector_attribute_counts": {
                    "color": dict(Counter(str(sector["color_name"]) for sector in all_sectors)),
                    "shape": dict(Counter(str(sector["shape"]) for sector in all_sectors)),
                },
                "event": dict(event),
                "event_description": str(event["event_description"]),
                "favorable_outcome_count": int(event["favorable_outcome_count"]),
                "total_outcome_count": int(event["total_outcome_count"]),
                "answer_value": str(answer_value),
                "annotation_item_ids": list(annotation_item_ids),
                "calculation_supporting_item_ids": list(calculation_supporting_item_ids),
                "question_format": str(query_id),
            },
            "witness_symbolic": {
                "type": "bbox_set",
                "value": list(annotation_bboxes),
            },
            "projected_annotation": dict(annotation_projection),
            "answer_gt": answer_gt.to_dict(),
            "annotation_gt": annotation_gt.to_dict(),
        }
        if str(dataset["mode"]) == "single":
            trace_payload["execution_trace"]["sector_count"] = int(dataset["sector_count"])
            trace_payload["execution_trace"]["sector_count_range"] = list(dataset["sector_count_range"])
        else:
            trace_payload["execution_trace"]["sector_count_a"] = int(dataset["sector_count_a"])
            trace_payload["execution_trace"]["sector_count_b"] = int(dataset["sector_count_b"])
            trace_payload["execution_trace"]["sector_count_range"] = list(dataset["sector_count_range"])

        return TaskOutput(
            prompt=str(prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
            prompt_variants=dict(prompt_variants),
        )


@register_task
class SymbolicProbabilitySpinnerSingleAttributeProbabilityTask(_SpinnerProbabilityBaseTask):
    """Compute one single-attribute probability from a single equal-sector spinner."""

    task_id = SINGLE_ATTRIBUTE_TASK_ID
    supported_query_ids = SINGLE_ATTRIBUTE_QUERY_IDS
    dataset_family = "single"


@register_task
class SymbolicProbabilitySpinnerMultiAttributeAndProbabilityTask(_SpinnerProbabilityBaseTask):
    """Compute a color-and-shape probability from a single equal-sector spinner."""

    task_id = MULTI_ATTRIBUTE_AND_TASK_ID
    supported_query_ids = MULTI_ATTRIBUTE_AND_QUERY_IDS
    dataset_family = "single"


@register_task
class SymbolicProbabilitySpinnerMultiAttributeOrProbabilityTask(_SpinnerProbabilityBaseTask):
    """Compute a color-or-shape probability from a single equal-sector spinner."""

    task_id = MULTI_ATTRIBUTE_OR_TASK_ID
    supported_query_ids = MULTI_ATTRIBUTE_OR_QUERY_IDS
    dataset_family = "single"


@register_task
class SymbolicProbabilitySpinnerPairEventValueTask(_SpinnerProbabilityBaseTask):
    """Compute one product-space probability from two independent equal-sector spinners."""

    task_id = PAIR_TASK_ID
    supported_query_ids = PAIR_QUERY_IDS
    dataset_family = "pair"


__all__ = [
    "MULTI_ATTRIBUTE_AND_QUERY_IDS",
    "MULTI_ATTRIBUTE_AND_TASK_ID",
    "MULTI_ATTRIBUTE_OR_QUERY_IDS",
    "MULTI_ATTRIBUTE_OR_TASK_ID",
    "SINGLE_ATTRIBUTE_QUERY_IDS",
    "SINGLE_ATTRIBUTE_TASK_ID",
    "SymbolicProbabilitySpinnerMultiAttributeAndProbabilityTask",
    "SymbolicProbabilitySpinnerMultiAttributeOrProbabilityTask",
    "SymbolicProbabilitySpinnerPairEventValueTask",
    "SymbolicProbabilitySpinnerSingleAttributeProbabilityTask",
]
