"""Identify the rotated tile in an indoor-room illustration grid."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image

from ....core.query_ids import SINGLE_QUERY_ID
from ....core.scene_config import get_scene_defaults
from ....core.seed import spawn_rng
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_scene_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ..shared.cutouts import (
    DEFAULT_OPTION_LABELS,
    ROTATED_GRID_STYLES,
    compose_rotated_tile_grid,
    piece_crops,
    sample_style,
    style_trace,
    tile_is_usable,
)
from ..shared.option_rendering import fit_source_image, sample_visual_label_font_trace
from ..shared.task_support import bounds as _shared_bounds
from ..shared.task_support import sample_count as _shared_sample_count
from .shared.annotations import serialize_indoor_scene
from .shared.output import object_type_map, render_fallback_from_defaults
from .shared.prompts import build_indoor_prompt_artifacts, indoor_setting_name
from .shared.rendering import indoor_scene_entities, render_indoor_scene_from_specs
from .shared.sampling import support_choice, theme_support, typed_support
from .shared.state import (
    INDOOR_CONTAINER_TYPES,
    INDOOR_OBJECT_TYPES,
    INDOOR_SURFACE_TYPES,
    IndoorObjectSpec,
)


TASK_ID = "task_illustrations__indoor_room__rotated_tile_label"
SCENE_ID = "indoor_room"
QUERY_ID = SINGLE_QUERY_ID
PROMPT_QUERY_KEY = "rotated_tile_label"
GRID_ROWS = 2
GRID_COLS = 3
TILE_LABELS: Tuple[str, ...] = DEFAULT_OPTION_LABELS[: GRID_ROWS * GRID_COLS]
ROTATION_SUPPORT: Tuple[int, ...] = (90, 270)


@dataclass(frozen=True)
class _Defaults:
    source_object_count_min: int = 12
    source_object_count_max: int = 18
    source_width: int = 960
    source_height: int = 640
    canvas_width: int = 1280
    canvas_height: int = 840
    object_size_min_px: int = 52
    object_size_max_px: int = 86
    render_scale: int = 2
    min_tile_detail_score: float = 150.0
    min_rotation_delta: float = 7.0


@dataclass(frozen=True)
class _SampleSpec:
    theme_id: str
    source_object_count: int
    rotation_degrees: int
    source_size: Tuple[int, int]
    specs: Tuple[IndoorObjectSpec, ...]
    theme_probabilities: Dict[str, float]
    source_object_count_probabilities: Dict[str, float]
    rotation_probabilities: Dict[str, float]


_DEFAULTS = _Defaults()
_SCENE_DEFAULTS = get_scene_defaults("illustrations", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _int_value(params: Mapping[str, Any], defaults: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), group_default(defaults, str(key), int(fallback))))


def _float_value(params: Mapping[str, Any], defaults: Mapping[str, Any], key: str, fallback: float) -> float:
    return float(params.get(str(key), group_default(defaults, str(key), float(fallback))))


def _rotation_support(params: Mapping[str, Any]) -> Tuple[int, ...]:
    raw = params.get("rotation_degrees_support", group_default(_GEN_DEFAULTS, "rotation_degrees_support", ROTATION_SUPPORT))
    values = (raw,) if isinstance(raw, int) else tuple(raw if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)) else ())
    support = tuple(dict.fromkeys(int(value) for value in values if int(value) in set(ROTATION_SUPPORT)))
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
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:rotation_degrees")
    value = int(support[int(index) % len(support)])
    probability = 1.0 / float(len(support))
    return int(value), {str(item): float(probability) for item in support}


def _sample_spec(*, instance_seed: int, params: Mapping[str, Any], attempt_index: int) -> _SampleSpec:
    """Sample a dense indoor source scene and a non-semantic rotation angle."""

    theme_id, theme_probabilities = support_choice(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:theme",
        support=theme_support(params, _GEN_DEFAULTS),
        explicit_key="theme_id",
    )
    object_support = typed_support(
        params,
        _GEN_DEFAULTS,
        param_key="object_type_support",
        default_key="indoor_object_type_support",
        fallback=INDOOR_OBJECT_TYPES,
        error_name="object_type_support",
    )
    object_min, object_max = _shared_bounds(
        params,
        _GEN_DEFAULTS,
        "source_object_count_min",
        "source_object_count_max",
        _DEFAULTS.source_object_count_min,
        _DEFAULTS.source_object_count_max,
    )
    source_object_count, object_count_probabilities = _shared_sample_count(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:source_object_count",
        low=int(object_min),
        high=int(object_max),
        explicit_key="source_object_count",
    )
    rotation_degrees, rotation_probabilities = _sample_rotation(params=params, instance_seed=int(instance_seed))

    rng = spawn_rng(int(instance_seed), f"{TASK_ID}:spec", int(attempt_index))
    base_targets: list[Tuple[str, str]] = [
        ("surface", str(surface_type))
        for surface_type in INDOOR_SURFACE_TYPES
    ]
    base_targets.extend(("container", str(container_type)) for container_type in INDOOR_CONTAINER_TYPES)
    base_targets.extend(
        (
            ("region", "table:left"),
            ("region", "table:right"),
            ("region", "table:above"),
            ("region", "table:below"),
            ("region", "sofa:above"),
            ("region", "sofa:below"),
            ("region", "cabinet:above"),
            ("region", "cabinet:below"),
        )
    )
    rng.shuffle(base_targets)
    specs: list[IndoorObjectSpec] = []
    for index in range(int(source_object_count)):
        if index < len(base_targets):
            placement_kind, target_type = base_targets[index]
        else:
            placement_kind, target_type = rng.choice(base_targets)
        specs.append(
            IndoorObjectSpec(
                object_type=str(rng.choice(object_support)),
                placement_kind=str(placement_kind),
                target_type=str(target_type),
                role="source",
            )
        )
    rng.shuffle(specs)
    return _SampleSpec(
        theme_id=str(theme_id),
        source_object_count=int(source_object_count),
        rotation_degrees=int(rotation_degrees),
        source_size=(
            _int_value(params, _GEN_DEFAULTS, "source_width", _DEFAULTS.source_width),
            _int_value(params, _GEN_DEFAULTS, "source_height", _DEFAULTS.source_height),
        ),
        specs=tuple(specs),
        theme_probabilities=dict(theme_probabilities),
        source_object_count_probabilities=dict(object_count_probabilities),
        rotation_probabilities=dict(rotation_probabilities),
    )


def _usable_tile_indices(
    *,
    source_image: Image.Image,
    rotation_degrees: int,
    min_detail_score: float,
    min_rotation_delta: float,
) -> Tuple[int, ...]:
    pieces = piece_crops(source_image.convert("RGB"), rows=GRID_ROWS, cols=GRID_COLS)
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
) -> Tuple[int, Dict[str, float]]:
    usable = tuple(int(index) for index in usable_indices)
    if not usable:
        raise ValueError("no visually usable indoor-room tile for rotation")
    explicit = params.get("correct_index")
    if explicit is not None:
        value = int(explicit)
        if value < 0 or value >= len(TILE_LABELS):
            raise ValueError("correct_index outside tile label support")
        if value not in set(usable):
            raise ValueError("explicit correct_index is not visually usable for rotation")
        return int(value), {str(value): 1.0}
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:answer:{attempt_index}",
    )
    selected = int(usable[int(index) % len(usable)])
    return int(selected), dict(uniform_probability_map(usable))


def _keyed_bbox_map(value: Mapping[str, Sequence[float]]) -> Dict[str, list[float]]:
    return {
        str(key): [round(float(coord), 3) for coord in bbox[:4]]
        for key, bbox in value.items()
    }


@register_task
class IllustrationsIndoorRoomRotatedTileLabelTask:
    """Select the lettered tile that has been rotated inside a room grid."""

    task_id = TASK_ID
    domain = "illustrations"
    supported_query_ids = (QUERY_ID,)
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one tiled indoor-room scene and bind tile-level evidence."""

        last_error: Exception | None = None
        sample: _SampleSpec | None = None
        scene = None
        artifacts = None
        grid_style = None
        label_font_trace: Dict[str, Any] | None = None
        correct_index = None
        correct_index_probabilities: Dict[str, float] | None = None
        usable_indices: Tuple[int, ...] = tuple()
        fallback = render_fallback_from_defaults(_DEFAULTS)
        for attempt in range(max(1, int(max_attempts))):
            try:
                sample = _sample_spec(instance_seed=int(instance_seed), params=params, attempt_index=int(attempt))
                scene = render_indoor_scene_from_specs(
                    render_namespace="rotated_tile_label",
                    instance_seed=int(instance_seed),
                    attempt_index=int(attempt),
                    specs=sample.specs,
                    theme_id=str(sample.theme_id),
                    params=params,
                    render_defaults=_RENDER_DEFAULTS,
                    fallback=fallback,
                )
                source_panel = fit_source_image(
                    scene.image,
                    width=int(sample.source_size[0]),
                    height=int(sample.source_size[1]),
                )
                usable_indices = _usable_tile_indices(
                    source_image=source_panel,
                    rotation_degrees=int(sample.rotation_degrees),
                    min_detail_score=_float_value(params, _GEN_DEFAULTS, "min_tile_detail_score", _DEFAULTS.min_tile_detail_score),
                    min_rotation_delta=_float_value(params, _GEN_DEFAULTS, "min_rotation_delta", _DEFAULTS.min_rotation_delta),
                )
                correct_index, correct_index_probabilities = _select_correct_index(
                    params=params,
                    instance_seed=int(instance_seed),
                    attempt_index=int(attempt),
                    usable_indices=usable_indices,
                )
                option_rng = spawn_rng(int(instance_seed), f"{TASK_ID}:tile_grid", int(attempt))
                grid_style = sample_style(option_rng, ROTATED_GRID_STYLES)
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
                    rows=GRID_ROWS,
                    cols=GRID_COLS,
                    labels=TILE_LABELS,
                )
                break
            except Exception as exc:  # pragma: no cover
                last_error = exc
                sample = None
                scene = None
                artifacts = None
                grid_style = None
                label_font_trace = None
                correct_index = None
                correct_index_probabilities = None
                usable_indices = tuple()
        if (
            sample is None
            or scene is None
            or artifacts is None
            or grid_style is None
            or label_font_trace is None
            or correct_index is None
            or correct_index_probabilities is None
        ):
            raise RuntimeError(f"could not generate {TASK_ID}: {last_error}") from last_error

        serialized_objects, object_bboxes, part_bboxes = serialize_indoor_scene(scene)
        answer_label = str(artifacts.selected_label)
        annotation_value = _keyed_bbox_map({"rotated_tile": artifacts.selected_bbox})
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
        prompt_artifacts = build_indoor_prompt_artifacts(
            domain=self.domain,
            scene_id=SCENE_ID,
            prompt_defaults=prompt_defaults,
            prompt_query_key=PROMPT_QUERY_KEY,
            slots={
                "room_setting": indoor_setting_name(str(scene.theme_id)),
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
            "scene_ir": {
                "domain": self.domain,
                "scene_id": SCENE_ID,
                "entities": indoor_scene_entities(scene),
                "relations": {
                    "query_id": QUERY_ID,
                    "rotated_tile_label": answer_label,
                    "rotated_tile_index": int(correct_index),
                    "rotation_degrees": int(sample.rotation_degrees),
                },
            },
            "query_spec": {
                "task_id": self.task_id,
                "query_id": QUERY_ID,
                "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "theme": str(sample.theme_id),
                    "theme_id": str(sample.theme_id),
                    "source_object_count": int(len(scene.placements)),
                    "requested_source_object_count": int(sample.source_object_count),
                    "source_object_count_probabilities": dict(sample.source_object_count_probabilities),
                    "rotation_degrees": int(sample.rotation_degrees),
                    "rotation_degrees_support": [int(value) for value in _rotation_support(params)],
                    "rotation_degrees_probabilities": dict(sample.rotation_probabilities),
                    "grid_shape": [GRID_ROWS, GRID_COLS],
                    "option_labels": list(TILE_LABELS),
                    "usable_tile_indices": [int(index) for index in usable_indices],
                    "answer_label": answer_label,
                    "correct_index": int(correct_index),
                    "correct_index_probabilities": dict(correct_index_probabilities),
                    "source_size": [int(sample.source_size[0]), int(sample.source_size[1])],
                    "theme_probabilities": dict(sample.theme_probabilities),
                },
            },
            "render_spec": {
                "canvas_size": [int(artifacts.image.width), int(artifacts.image.height)],
                "coord_space": "pixel",
                "scene_id": SCENE_ID,
                "source_scene_canvas_size": [int(scene.canvas_width), int(scene.canvas_height)],
                "style": {
                    "source_theme_id": str(scene.theme_id),
                    "source_style_id": str(scene.style_id),
                    "render_scale": int(scene.render_scale),
                    "grid_style": style_trace(grid_style),
                    "tile_label_font": dict(label_font_trace),
                },
            },
            "render_map": {
                "image_id": "img0",
                "tile_bboxes_px_by_label": {str(key): list(value) for key, value in artifacts.tile_bboxes.items()},
                "rotated_tile_bbox_px": list(artifacts.selected_bbox),
                "selected_tile_bbox_px": list(artifacts.selected_bbox),
                "source_object_bboxes_px": object_bboxes,
                "source_part_bboxes_px": part_bboxes,
                "source_scene_canvas_size": [int(scene.canvas_width), int(scene.canvas_height)],
                "source_tile_index": int(correct_index),
                "source_size": [int(sample.source_size[0]), int(sample.source_size[1])],
                "grid_shape": [GRID_ROWS, GRID_COLS],
            },
            "execution_trace": {
                "query_id": QUERY_ID,
                "scene_id": SCENE_ID,
                "theme_id": str(scene.theme_id),
                "theme": str(scene.theme_id),
                "answer": answer_label,
                "answer_label": answer_label,
                "rotated_tile_label": answer_label,
                "rotated_tile_index": int(correct_index),
                "rotation_degrees": int(sample.rotation_degrees),
                "grid_shape": [GRID_ROWS, GRID_COLS],
                "tile_labels": list(TILE_LABELS),
                "usable_tile_indices": [int(index) for index in usable_indices],
                "source_object_count": int(len(scene.placements)),
                "object_types": object_type_map(serialized_objects),
            },
            "witness_symbolic": {
                "rotated_tile_label": answer_label,
                "rotated_tile_index": int(correct_index),
                "rotated_tile_bbox": list(artifacts.selected_bbox),
                "rotation_degrees": int(sample.rotation_degrees),
            },
            "projected_annotation": {
                "type": "keyed_bbox_map",
                "keyed_bbox_map": dict(annotation_value),
                "pixel_keyed_bbox_map": dict(annotation_value),
            },
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
            answer_gt=TypedValue(type="option_letter", value=answer_label),
            annotation_gt=TypedValue(type="keyed_bbox_map", value=dict(annotation_value)),
            image=artifacts.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=QUERY_ID,
        )


__all__ = ["IllustrationsIndoorRoomRotatedTileLabelTask"]
