"""Identify the rotated tile in a top-down RPG dungeon illustration grid."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.core.scene_config import get_scene_defaults
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.annotation_artifacts import bbox_annotation_artifacts
from trace.tasks.shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_scene_generation_rendering_prompt_defaults,
)
from trace.tasks.shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.illustrations.shared.canvas_profiles import (
    MAX_RECONSTRUCTION_OUTPUT_PIXELS,
    reconstruction_option_labels,
)
from trace.tasks.illustrations.shared.cutouts import (
    FRAMELESS_ILLUSTRATION_ROTATED_GRID_STYLE,
    compose_rotated_tile_grid,
    downscale_rotated_tile_artifacts,
    piece_crops,
    style_trace,
    tile_is_usable,
)
from trace.tasks.illustrations.shared.option_rendering import sample_visual_label_font_trace
from trace.tasks.illustrations.shared.rpg_tile_profiles import rpg_rotated_tile_grid_for_size

from .shared.output import rpg_dungeon_scene_ir
from .shared.prompts import build_rpg_dungeon_prompt_artifacts
from .shared.rendering import SCENE_ID
from .shared.source_images import (
    render_rpg_dungeon_source_scene,
    rpg_dungeon_source_style_trace,
    sample_rpg_dungeon_source_scene_spec,
)


TASK_ID = "task_illustrations__rpg_dungeon__rotated_tile_label"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (SINGLE_QUERY_ID,)
PROMPT_QUERY_KEY = "rotated_tile_label"
ROTATION_SUPPORT: Tuple[int, ...] = (90, 270)


@dataclass(frozen=True)
class _Defaults:
    source_chest_count_min: int = 5
    source_chest_count_max: int = 6
    min_tile_detail_score: float = 80.0
    min_rotation_delta: float = 6.0


@dataclass(frozen=True)
class _SampleSpec:
    query_id: str
    rotation_degrees: int
    source_chest_count: int
    source_reachable_chest_count: int
    source_monster_count: int
    source_size: Tuple[int, int]
    source_profile_trace: Dict[str, Any]
    query_probabilities: Dict[str, float]
    rotation_probabilities: Dict[str, float]
    source_chest_count_probabilities: Dict[str, float]
    source_reachable_chest_count_probabilities: Dict[str, float]
    source_monster_count_probabilities: Dict[str, float]


_DEFAULTS = _Defaults()
_SCENE_DEFAULTS = get_scene_defaults("illustrations", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _float_value(params: Mapping[str, Any], defaults: Mapping[str, Any], key: str, fallback: float) -> float:
    return float(params.get(str(key), group_default(defaults, str(key), float(fallback))))


def _rotation_support(params: Mapping[str, Any]) -> Tuple[int, ...]:
    raw = params.get("rotation_degrees_support", group_default(_GEN_DEFAULTS, "rotation_degrees_support", ROTATION_SUPPORT))
    if isinstance(raw, int):
        values = (int(raw),)
    elif isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        values = tuple(int(value) for value in raw)
    else:
        values = ROTATION_SUPPORT
    support = tuple(dict.fromkeys(value for value in values if value in set(ROTATION_SUPPORT)))
    if not support:
        raise ValueError("rotation_degrees_support must include 90 or 270")
    return support


def _sample_rotation(*, params: Mapping[str, Any], instance_seed: int) -> Tuple[int, Dict[str, float]]:
    support = _rotation_support(params)
    explicit = params.get("rotation_degrees")
    if explicit is not None:
        value = int(explicit)
        if value not in set(support):
            raise ValueError(f"rotation_degrees must be one of {support}")
        return int(value), {str(value): 1.0}
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:rotation_degrees",
    )
    value = int(support[int(index) % len(support)])
    probability = 1.0 / float(len(support))
    return int(value), {str(item): float(probability) for item in support}


def _sample_spec(*, instance_seed: int, params: Mapping[str, Any]) -> _SampleSpec:
    query_id, query_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=SUPPORTED_QUERY_IDS,
        default_query_id=SINGLE_QUERY_ID,
        task_id=TASK_ID,
        namespace=f"{TASK_ID}:query",
    )
    rotation_degrees, rotation_probabilities = _sample_rotation(
        params=task_params,
        instance_seed=int(instance_seed),
    )
    source = sample_rpg_dungeon_source_scene_spec(
        seed_namespace=TASK_ID,
        instance_seed=int(instance_seed),
        params=task_params,
        generation_defaults=_GEN_DEFAULTS,
        source_chest_count_min=_DEFAULTS.source_chest_count_min,
        source_chest_count_max=_DEFAULTS.source_chest_count_max,
    )
    return _SampleSpec(
        query_id=str(query_id),
        rotation_degrees=int(rotation_degrees),
        source_chest_count=int(source.source_chest_count),
        source_reachable_chest_count=int(source.source_reachable_chest_count),
        source_monster_count=int(source.source_monster_count),
        source_size=tuple(source.source_size),
        source_profile_trace=dict(source.source_profile_trace),
        query_probabilities=dict(query_probabilities),
        rotation_probabilities=dict(rotation_probabilities),
        source_chest_count_probabilities=dict(source.source_chest_count_probabilities),
        source_reachable_chest_count_probabilities=dict(source.source_reachable_chest_count_probabilities),
        source_monster_count_probabilities=dict(source.source_monster_count_probabilities),
    )


def _usable_tile_indices(
    *,
    source_image: Image.Image,
    rotation_degrees: int,
    min_detail_score: float,
    min_rotation_delta: float,
    rows: int,
    cols: int,
) -> Tuple[int, ...]:
    pieces = piece_crops(source_image.convert("RGB"), rows=int(rows), cols=int(cols))
    usable: list[int] = []
    for index, (piece, _source_box) in enumerate(pieces):
        rotated = piece.rotate(-int(rotation_degrees), expand=False, resample=Image.Resampling.BICUBIC)
        if tile_is_usable(
            piece,
            rotated,
            min_detail_score=float(min_detail_score),
            min_rotation_delta=float(min_rotation_delta),
        ):
            usable.append(int(index))
    return tuple(usable)


def _select_correct_index(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    attempt_index: int,
    usable_indices: Sequence[int],
    tile_labels: Sequence[str],
) -> Tuple[int, Dict[str, float]]:
    usable = tuple(int(index) for index in usable_indices)
    if not usable:
        raise ValueError("no visually usable RPG dungeon tile for rotation")
    explicit = params.get("correct_index")
    if explicit is not None:
        value = int(explicit)
        if value < 0 or value >= len(tile_labels):
            raise ValueError("correct_index outside tile label support")
        if value not in set(usable):
            raise ValueError("explicit correct_index is not visually usable for rotation")
        return int(value), {str(value): 1.0}
    if params.get("_sample_cursor") is not None:
        value = abs(int(params["_sample_cursor"])) % len(tile_labels)
        if value not in set(usable):
            raise ValueError("sample-cursor selected tile is not visually usable for rotation")
        return int(value), dict(uniform_probability_map(tuple(range(len(tile_labels)))))
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:answer:{attempt_index}",
    )
    selected = int(usable[int(index) % len(usable)])
    return int(selected), dict(uniform_probability_map(usable))


@register_task
class IllustrationsRpgDungeonRotatedTileLabelTask:
    """Select the lettered RPG dungeon tile that has been rotated."""

    task_id = TASK_ID
    domain = "illustrations"
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one tiled dungeon scene and bind tile-level annotation."""

        last_error: Exception | None = None
        sample: _SampleSpec | None = None
        source_scene = None
        artifacts = None
        grid_style = {"style_id": "frameless_illustration", **dict(FRAMELESS_ILLUSTRATION_ROTATED_GRID_STYLE)}
        label_font_trace: Dict[str, Any] | None = None
        correct_index = None
        correct_index_probabilities: Dict[str, float] | None = None
        usable_indices: Tuple[int, ...] = tuple()
        min_tile_detail_score = _float_value(params, _GEN_DEFAULTS, "min_tile_detail_score", _DEFAULTS.min_tile_detail_score)
        min_rotation_delta = _float_value(params, _GEN_DEFAULTS, "min_rotation_delta", _DEFAULTS.min_rotation_delta)

        for attempt in range(max(1, int(max_attempts))):
            try:
                sample = _sample_spec(instance_seed=int(instance_seed), params=params)
                source_spec = sample_rpg_dungeon_source_scene_spec(
                    seed_namespace=TASK_ID,
                    instance_seed=int(instance_seed),
                    params={
                        **dict(params),
                        "source_chest_count": int(sample.source_chest_count),
                        "source_reachable_chest_count": int(sample.source_reachable_chest_count),
                        "source_monster_count": int(sample.source_monster_count),
                    },
                    generation_defaults=_GEN_DEFAULTS,
                    source_chest_count_min=_DEFAULTS.source_chest_count_min,
                    source_chest_count_max=_DEFAULTS.source_chest_count_max,
                )
                source_scene = render_rpg_dungeon_source_scene(
                    seed_namespace=TASK_ID,
                    instance_seed=int(instance_seed),
                    attempt_index=int(attempt),
                    source=source_spec,
                    params={
                        **dict(params),
                        "source_chest_count": int(sample.source_chest_count),
                        "source_reachable_chest_count": int(sample.source_reachable_chest_count),
                        "source_monster_count": int(sample.source_monster_count),
                    },
                    render_defaults=_RENDER_DEFAULTS,
                )
                source_panel = source_scene.image.convert("RGB")
                grid_rows, grid_cols = rpg_rotated_tile_grid_for_size(source_panel.width, source_panel.height)
                tile_labels = reconstruction_option_labels(grid_rows, grid_cols)
                usable_indices = _usable_tile_indices(
                    source_image=source_panel,
                    rotation_degrees=int(sample.rotation_degrees),
                    min_detail_score=float(min_tile_detail_score),
                    min_rotation_delta=float(min_rotation_delta),
                    rows=int(grid_rows),
                    cols=int(grid_cols),
                )
                correct_index, correct_index_probabilities = _select_correct_index(
                    params=params,
                    instance_seed=int(instance_seed),
                    attempt_index=int(attempt),
                    usable_indices=usable_indices,
                    tile_labels=tile_labels,
                )
                label_font_trace = sample_visual_label_font_trace(
                    namespace_prefix=TASK_ID,
                    instance_seed=int(instance_seed),
                    params={**dict(_RENDER_DEFAULTS), **dict(params)},
                    namespace_suffix="tile_labels",
                    explicit_key="tile_label_font_family",
                    weights_key="tile_label_font_weights",
                )
                artifacts = compose_rotated_tile_grid(
                    source_image=source_panel,
                    correct_index=int(correct_index),
                    rotation_degrees=int(sample.rotation_degrees),
                    grid_style=grid_style,
                    label_font_family=str(label_font_trace["font_family"]),
                    rows=int(grid_rows),
                    cols=int(grid_cols),
                    labels=tile_labels,
                    render_margin=0,
                )
                artifacts = downscale_rotated_tile_artifacts(
                    artifacts,
                    max_pixels=MAX_RECONSTRUCTION_OUTPUT_PIXELS,
                )
                break
            except Exception as exc:  # pragma: no cover - retry surface is seed/layout dependent.
                last_error = exc
                sample = None
                source_scene = None
                artifacts = None
                label_font_trace = None
                correct_index = None
                correct_index_probabilities = None
                usable_indices = tuple()

        if (
            sample is None
            or source_scene is None
            or artifacts is None
            or label_font_trace is None
            or correct_index is None
            or correct_index_probabilities is None
        ):
            raise RuntimeError(f"could not generate {TASK_ID}: {last_error}") from last_error

        answer_label = str(artifacts.selected_label)
        grid_rows, grid_cols = int(artifacts.grid_shape[0]), int(artifacts.grid_shape[1])
        tile_labels = reconstruction_option_labels(grid_rows, grid_cols)
        annotation_artifacts = bbox_annotation_artifacts(artifacts.selected_bbox)
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_rotated_tile",
                "annotation_hint_rotated_tile",
                "json_example_rotated_tile",
                "json_example_answer_only_rotated_tile",
            ],
            context=f"prompt defaults for {TASK_ID}",
        )
        prompt_artifacts = build_rpg_dungeon_prompt_artifacts(
            domain=self.domain,
            scene_id=SCENE_ID,
            prompt_defaults=prompt_defaults,
            prompt_query_key=PROMPT_QUERY_KEY,
            slots={
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults["answer_hint_rotated_tile"]),
                "annotation_hint": str(prompt_defaults["annotation_hint_rotated_tile"]),
                "json_example": str(prompt_defaults["json_example_rotated_tile"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only_rotated_tile"]),
            },
            instance_seed=int(instance_seed),
        )
        trace_payload = {
            "scene_ir": rpg_dungeon_scene_ir(
                domain=self.domain,
                scene_id=SCENE_ID,
                scene=source_scene,
                relations={
                    "query_id": str(sample.query_id),
                    "prompt_query_key": PROMPT_QUERY_KEY,
                    "rotated_tile_label": answer_label,
                    "rotated_tile_index": int(correct_index),
                    "rotation_degrees": int(sample.rotation_degrees),
                },
            ),
            "query_spec": {
                "task_id": TASK_ID,
                "query_id": str(sample.query_id),
                "prompt_query_key": PROMPT_QUERY_KEY,
                "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(sample.query_id),
                    "query_id_probabilities": dict(sample.query_probabilities),
                    "prompt_query_key": PROMPT_QUERY_KEY,
                    "source_chest_count": int(sample.source_chest_count),
                    "source_chest_count_probabilities": dict(sample.source_chest_count_probabilities),
                    "source_reachable_chest_count": int(sample.source_reachable_chest_count),
                    "source_reachable_chest_count_probabilities": dict(sample.source_reachable_chest_count_probabilities),
                    "source_monster_count": int(sample.source_monster_count),
                    "source_monster_count_probabilities": dict(sample.source_monster_count_probabilities),
                    "rotation_degrees": int(sample.rotation_degrees),
                    "rotation_degrees_support": [int(value) for value in _rotation_support(params)],
                    "rotation_degrees_probabilities": dict(sample.rotation_probabilities),
                    "grid_shape": [grid_rows, grid_cols],
                    "option_labels": list(tile_labels),
                    "usable_tile_indices": [int(index) for index in usable_indices],
                    "answer_label": answer_label,
                    "correct_index": int(correct_index),
                    "correct_index_probabilities": dict(correct_index_probabilities),
                    "source_size": [int(sample.source_size[0]), int(sample.source_size[1])],
                    **dict(sample.source_profile_trace),
                    "min_tile_detail_score": float(min_tile_detail_score),
                    "min_rotation_delta": float(min_rotation_delta),
                },
            },
            "render_spec": {
                "canvas_size": [int(artifacts.image.width), int(artifacts.image.height)],
                "coord_space": "pixel",
                "scene_id": SCENE_ID,
                "source_scene_canvas_size": [int(source_scene.image.width), int(source_scene.image.height)],
                "source_profile": dict(sample.source_profile_trace),
                "style": {
                    **rpg_dungeon_source_style_trace(source_scene),
                    "grid_style": style_trace(grid_style),
                    "tile_label_font": dict(label_font_trace),
                },
            },
            "render_map": {
                "image_id": "img0",
                "tile_bboxes_px_by_label": {str(key): list(value) for key, value in artifacts.tile_bboxes.items()},
                "rotated_tile_bbox_px": list(artifacts.selected_bbox),
                "selected_tile_bbox_px": list(artifacts.selected_bbox),
                "source_scene_canvas_size": [int(source_scene.image.width), int(source_scene.image.height)],
                "source_tile_index": int(correct_index),
                "source_size": [int(sample.source_size[0]), int(sample.source_size[1])],
                "grid_shape": [grid_rows, grid_cols],
                "pre_downscale_canvas_size": [int(value) for value in artifacts.pre_downscale_canvas_size],
                "output_scale_xy": [float(value) for value in artifacts.output_scale_xy],
            },
            "execution_trace": {
                "query_id": str(sample.query_id),
                "prompt_query_key": PROMPT_QUERY_KEY,
                "scene_id": SCENE_ID,
                "answer": answer_label,
                "answer_label": answer_label,
                "rotated_tile_label": answer_label,
                "rotated_tile_index": int(correct_index),
                "rotation_degrees": int(sample.rotation_degrees),
                "grid_shape": [grid_rows, grid_cols],
                "tile_labels": list(tile_labels),
                "usable_tile_indices": [int(index) for index in usable_indices],
                "source_scene": dict(source_scene.trace),
            },
            "witness_symbolic": {
                "rotated_tile_label": answer_label,
                "rotated_tile_index": int(correct_index),
                "rotated_tile_bbox": list(artifacts.selected_bbox),
                "rotation_degrees": int(sample.rotation_degrees),
            },
            "projected_annotation": dict(annotation_artifacts.projected_annotation),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
            answer_gt=TypedValue(type="option_letter", value=answer_label),
            annotation_gt=annotation_artifacts.annotation_gt,
            image=artifacts.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(sample.query_id),
        )


__all__ = [
    "IllustrationsRpgDungeonRotatedTileLabelTask",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
]
