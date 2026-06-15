"""Select the correctly arranged jigsaw reconstruction of a pixel village."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

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
    JIGSAW_BOARD_STYLES,
    compose_jigsaw_arrangement_options,
    piece_crops,
    sample_style,
    style_trace,
)
from ..shared.option_rendering import image_detail_score, sample_visual_label_font_trace
from .shared.output import pixel_village_scene_ir
from .shared.prompts import build_pixel_village_prompt_artifacts
from .shared.sampling import SCENE_ID
from .shared.source_images import build_pixel_village_source_spec, render_pixel_village_source_scene, source_panel_for_scene


TASK_ID = "task_illustrations__pixel_village__jigsaw_arrangement_label"
QUERY_ID = SINGLE_QUERY_ID
PROMPT_QUERY_KEY = "jigsaw_arrangement_label"
GRID_ROWS = 2
GRID_COLS = 2
OPTION_LABELS: Tuple[str, ...] = DEFAULT_OPTION_LABELS[:4]


@dataclass(frozen=True)
class _Defaults:
    source_width: int = 520
    source_height: int = 390
    min_tile_detail_score: float = 340.0


@dataclass(frozen=True)
class _SampleSpec:
    correct_index: int
    correct_index_probabilities: Dict[str, float]


_DEFAULTS = _Defaults()
_SCENE_DEFAULTS = get_scene_defaults("illustrations", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _float_value(params: Mapping[str, Any], key: str, fallback: float) -> float:
    return float(params.get(str(key), group_default(_GEN_DEFAULTS, str(key), float(fallback))))


def _sample_correct_index(*, params: Mapping[str, Any], instance_seed: int) -> Tuple[int, Dict[str, float]]:
    explicit = params.get("correct_index")
    if explicit is not None:
        value = int(explicit)
        if value < 0 or value >= len(OPTION_LABELS):
            raise ValueError("correct_index outside option label support")
        return int(value), {str(value): 1.0}
    if params.get("answer_label") is not None:
        label = str(params["answer_label"])
        if label not in set(OPTION_LABELS):
            raise ValueError("answer_label outside option label support")
        value = int(OPTION_LABELS.index(label))
        return int(value), {str(value): 1.0}
    if params.get("_sample_cursor") is not None:
        value = abs(int(params["_sample_cursor"])) % len(OPTION_LABELS)
        return int(value), dict(uniform_probability_map(tuple(range(len(OPTION_LABELS)))))
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:answer")
    selected = int(index) % len(OPTION_LABELS)
    return int(selected), dict(uniform_probability_map(tuple(range(len(OPTION_LABELS)))))


def _sample_spec(*, instance_seed: int, params: Mapping[str, Any], attempt_index: int) -> _SampleSpec:
    """Sample one correct option position for the jigsaw arrangement task."""

    correct_index, correct_index_probabilities = _sample_correct_index(params=params, instance_seed=int(instance_seed))
    return _SampleSpec(correct_index=int(correct_index), correct_index_probabilities=dict(correct_index_probabilities))


def _tile_detail_scores(source_image: Any) -> Tuple[float, ...]:
    pieces = piece_crops(source_image.convert("RGB"), rows=GRID_ROWS, cols=GRID_COLS)
    return tuple(float(image_detail_score(piece)) for piece, _box in pieces)


def _bbox_set(*boxes: Sequence[float]) -> list[list[float]]:
    return [[round(float(coord), 3) for coord in bbox[:4]] for bbox in boxes]


@register_task
class IllustrationsPixelVillageJigsawArrangementLabelTask:
    """Select the option that correctly arranges 2x2 pixel-village tiles."""

    task_id = TASK_ID
    domain = "illustrations"
    supported_query_ids = (QUERY_ID,)
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Render a source pixel village, build jigsaw MCQ options, and bind selected-option evidence."""

        last_error: Exception | None = None
        sample: _SampleSpec | None = None
        scene = None
        artifacts = None
        board_style = None
        label_font_trace: Dict[str, Any] | None = None
        tile_detail_scores: Tuple[float, ...] = tuple()
        min_tile_detail_score = _float_value(params, "min_tile_detail_score", _DEFAULTS.min_tile_detail_score)
        source_spec = build_pixel_village_source_spec(
            params=params,
            generation_defaults=_GEN_DEFAULTS,
            rendering_defaults=_RENDER_DEFAULTS,
            fallback_source_width=_DEFAULTS.source_width,
            fallback_source_height=_DEFAULTS.source_height,
        )

        for attempt in range(max(1, int(max_attempts))):
            try:
                sample = _sample_spec(instance_seed=int(instance_seed), params=params, attempt_index=int(attempt))
                scene = render_pixel_village_source_scene(
                    seed_namespace=TASK_ID,
                    instance_seed=int(instance_seed),
                    attempt_index=int(attempt),
                    source_spec=source_spec,
                )
                source_panel = source_panel_for_scene(scene, source_spec.source_size)
                tile_detail_scores = _tile_detail_scores(source_panel)
                if min(tile_detail_scores) < float(min_tile_detail_score):
                    raise ValueError("source scene has a weak jigsaw tile")
                option_rng = spawn_rng(int(instance_seed), f"{TASK_ID}:jigsaw_options", int(attempt))
                board_style = sample_style(option_rng, JIGSAW_BOARD_STYLES)
                label_font_trace = sample_visual_label_font_trace(
                    namespace_prefix=TASK_ID,
                    instance_seed=int(instance_seed),
                    params={**dict(_RENDER_DEFAULTS), **dict(params)},
                    namespace_suffix="jigsaw_option_labels",
                    explicit_key="jigsaw_label_font_family",
                    weights_key="jigsaw_label_font_weights",
                )
                artifacts = compose_jigsaw_arrangement_options(
                    source_image=source_panel,
                    rows=GRID_ROWS,
                    cols=GRID_COLS,
                    correct_index=int(sample.correct_index),
                    rng=option_rng,
                    board_style=board_style,
                    label_font_family=str(label_font_trace["font_family"]),
                    labels=OPTION_LABELS,
                )
                break
            except Exception as exc:  # pragma: no cover
                last_error = exc
                sample = None
                scene = None
                artifacts = None
                board_style = None
                label_font_trace = None
                tile_detail_scores = tuple()
        if sample is None or scene is None or artifacts is None or board_style is None or label_font_trace is None:
            raise RuntimeError(f"could not generate {TASK_ID}: {last_error}") from last_error

        answer_label = str(artifacts.selected_label)
        annotation_value = _bbox_set(artifacts.selected_option_bbox)
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_jigsaw_arrangement",
                "annotation_hint_jigsaw_arrangement",
                "json_example_jigsaw_arrangement",
                "json_example_answer_only_jigsaw_arrangement",
            ],
            context=f"prompt defaults for {TASK_ID}",
        )
        slots = {
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults["answer_hint_jigsaw_arrangement"]),
            "annotation_hint": str(prompt_defaults["annotation_hint_jigsaw_arrangement"]),
            "json_example": str(prompt_defaults["json_example_jigsaw_arrangement"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only_jigsaw_arrangement"]),
        }
        prompt_artifacts = build_pixel_village_prompt_artifacts(
            domain=self.domain,
            scene_id=SCENE_ID,
            prompt_defaults=prompt_defaults,
            prompt_query_key=PROMPT_QUERY_KEY,
            slots=slots,
            instance_seed=int(instance_seed),
        )
        option_permutations_by_label = {
            str(label): [int(value) for value in artifacts.option_permutations[index]]
            for index, label in enumerate(OPTION_LABELS)
        }
        trace_payload = {
            "scene_ir": pixel_village_scene_ir(
                domain=self.domain,
                scene_id=SCENE_ID,
                scene=scene,
                relations={
                    "query_id": QUERY_ID,
                    "prompt_query_key": PROMPT_QUERY_KEY,
                    "answer_label": answer_label,
                    "grid_shape": [GRID_ROWS, GRID_COLS],
                },
            ),
            "query_spec": {
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": QUERY_ID,
                "prompt_query_key": PROMPT_QUERY_KEY,
                "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": QUERY_ID,
                    "prompt_query_key": PROMPT_QUERY_KEY,
                    "correct_index": int(sample.correct_index),
                    "correct_index_probabilities": dict(sample.correct_index_probabilities),
                    "answer_label": answer_label,
                    "option_labels": list(OPTION_LABELS),
                    "grid_shape": [GRID_ROWS, GRID_COLS],
                    "source_size": [int(value) for value in source_spec.source_size],
                    "min_tile_detail_score": float(min_tile_detail_score),
                    "tile_detail_scores": [round(float(value), 3) for value in tile_detail_scores],
                },
            },
            "render_spec": {
                "canvas_size": [int(artifacts.image.width), int(artifacts.image.height)],
                "coord_space": "pixel",
                "scene_id": SCENE_ID,
                "source_scene_canvas_size": [int(scene.image.width), int(scene.image.height)],
                "style": {
                    "source_renderer_id": str(scene.trace.get("renderer_id", "")),
                    "source_theme_id": str(scene.trace.get("theme_id", "")),
                    "source_tile_px": int(scene.trace.get("tile_px", 0)),
                    "jigsaw_style": style_trace(board_style),
                    "jigsaw_label_font": dict(label_font_trace),
                },
            },
            "render_map": {
                "image_id": "img0",
                "option_bboxes_px_by_label": {str(key): list(value) for key, value in artifacts.option_bboxes.items()},
                "selected_option_bbox_px": list(artifacts.selected_option_bbox),
                "source_scene_canvas_size": [int(scene.image.width), int(scene.image.height)],
                "source_size": [int(value) for value in source_spec.source_size],
                "tile_source_boxes_px": [[int(coord) for coord in box] for box in artifacts.tile_source_boxes],
                "option_permutations_by_label": option_permutations_by_label,
                "correct_permutation": [int(value) for value in artifacts.correct_permutation],
                "grid_shape": [GRID_ROWS, GRID_COLS],
                "option_layout_shape": [int(artifacts.option_layout_shape[0]), int(artifacts.option_layout_shape[1])],
            },
            "execution_trace": {
                "query_id": QUERY_ID,
                "prompt_query_key": PROMPT_QUERY_KEY,
                "scene_id": SCENE_ID,
                "answer": answer_label,
                "answer_label": answer_label,
                "correct_index": int(sample.correct_index),
                "option_labels": list(OPTION_LABELS),
                "option_permutations_by_label": option_permutations_by_label,
                "correct_permutation": [int(value) for value in artifacts.correct_permutation],
                "grid_shape": [GRID_ROWS, GRID_COLS],
            },
            "witness_symbolic": {
                "selected_option_bbox": list(artifacts.selected_option_bbox),
                "answer_label": answer_label,
                "correct_index": int(sample.correct_index),
            },
            "projected_annotation": {
                "type": "bbox_set",
                "bbox_set": [list(bbox) for bbox in annotation_value],
                "pixel_bbox_set": [list(bbox) for bbox in annotation_value],
            },
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
            answer_gt=TypedValue(type="option_letter", value=answer_label),
            annotation_gt=TypedValue(type="bbox_set", value=[list(bbox) for bbox in annotation_value]),
            image=artifacts.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=QUERY_ID,
        )


__all__ = ["IllustrationsPixelVillageJigsawArrangementLabelTask", "TASK_ID", "_sample_spec"]
