"""Select the lettered ground tile inside a named pixel-village territory."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import ImageDraw

from ....core.query_ids import SINGLE_QUERY_ID
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.annotation_artifacts import bbox_annotation_artifacts
from ...shared.config_defaults import required_group_defaults, split_scene_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ..shared.cutouts import DEFAULT_OPTION_LABELS
from ..shared.option_rendering import draw_label_badge, sample_visual_label_font_trace
from .shared.output import pixel_village_render_spec, pixel_village_scene_ir
from .shared.prompts import build_pixel_village_prompt_artifacts
from .shared.sampling import (
    SCENE_ID,
    _DEFAULTS,
    _entity_bbox_map,
    _render_metadata,
    _render_scene,
    _scene_entities,
    _scene_territories,
)


TASK_ID = "task_illustrations__pixel_village__territory_tile_membership_label"
QUERY_ID = SINGLE_QUERY_ID
PROMPT_QUERY_KEY = "territory_tile_membership_label"
OPTION_LABELS: Tuple[str, ...] = DEFAULT_OPTION_LABELS[:4]
TERRITORY_SUPPORT: Tuple[str, ...] = ("cemetery", "orchard")
TERRITORY_NAMES: Dict[str, str] = {"cemetery": "cemetery", "orchard": "orchard"}
TERRITORY_FORCE_PARAM: Dict[str, str] = {"cemetery": "cemetery_mode", "orchard": "orchard_mode"}
MAX_DISTRACTOR_TERRITORY_DISTANCE = 4


@dataclass(frozen=True)
class _SampleSpec:
    territory_type: str
    territory_name: str
    correct_index: int
    territory_probabilities: Dict[str, float]
    correct_index_probabilities: Dict[str, float]


_SCENE_DEFAULTS = get_scene_defaults("illustrations", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _territory_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get("target_territory_support", _GEN_DEFAULTS.get("target_territory_support", TERRITORY_SUPPORT))
    if isinstance(raw, str):
        values = (raw,)
    elif isinstance(raw, Sequence):
        values = tuple(raw)
    else:
        values = TERRITORY_SUPPORT
    support = tuple(dict.fromkeys(_normalize_territory(value) for value in values))
    invalid = [value for value in support if value not in set(TERRITORY_SUPPORT)]
    if invalid:
        raise ValueError(f"unsupported pixel-village territory targets: {invalid}")
    if not support:
        raise ValueError("target_territory_support must include cemetery or orchard")
    return support


def _normalize_territory(value: Any) -> str:
    text = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "graveyard": "cemetery",
        "churchyard": "cemetery",
        "fruit_orchard": "orchard",
    }
    return aliases.get(text, text)


def _sample_territory(*, params: Mapping[str, Any], instance_seed: int) -> Tuple[str, Dict[str, float]]:
    support = _territory_support(params)
    explicit = params.get("target_territory")
    if explicit is None:
        explicit = params.get("territory_type", params.get("territory_name"))
    if explicit is not None:
        value = _normalize_territory(explicit)
        if value not in set(support):
            raise ValueError("target_territory is outside configured support")
        return str(value), {str(item): (1.0 if str(item) == str(value) else 0.0) for item in support}
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:target_territory",
    )
    selected = support[int(index) % len(support)]
    probability = 1.0 / float(len(support))
    return str(selected), {str(value): float(probability) for value in support}


def _sample_correct_index(*, params: Mapping[str, Any], instance_seed: int) -> Tuple[int, Dict[str, float]]:
    explicit = params.get("correct_index")
    if explicit is not None:
        value = int(explicit)
        if value < 0 or value >= len(OPTION_LABELS):
            raise ValueError("correct_index outside option support")
        return int(value), {str(value): 1.0}
    if params.get("answer_label") is not None:
        label = str(params["answer_label"])
        if label not in set(OPTION_LABELS):
            raise ValueError("answer_label outside option support")
        value = int(OPTION_LABELS.index(label))
        return int(value), {str(value): 1.0}
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:correct_index",
    )
    selected = int(index) % len(OPTION_LABELS)
    return int(selected), dict(uniform_probability_map(tuple(range(len(OPTION_LABELS)))))


def _sample_spec(*, instance_seed: int, params: Mapping[str, Any]) -> _SampleSpec:
    territory_type, territory_probabilities = _sample_territory(params=params, instance_seed=int(instance_seed))
    correct_index, correct_index_probabilities = _sample_correct_index(params=params, instance_seed=int(instance_seed))
    return _SampleSpec(
        territory_type=str(territory_type),
        territory_name=str(TERRITORY_NAMES[str(territory_type)]),
        correct_index=int(correct_index),
        territory_probabilities=dict(territory_probabilities),
        correct_index_probabilities=dict(correct_index_probabilities),
    )


def _tile_bbox(tile_xy: Sequence[int], *, scene: Any) -> list[float]:
    x, y = int(tile_xy[0]), int(tile_xy[1])
    tile_px = int(scene.trace.get("tile_px", _DEFAULTS.tile_px))
    offset = scene.trace.get("map_offset_xy", [0, 0]) or [0, 0]
    ox, oy = int(offset[0]), int(offset[1])
    return [
        round(float(ox + x * tile_px), 3),
        round(float(oy + y * tile_px), 3),
        round(float(ox + (x + 1) * tile_px), 3),
        round(float(oy + (y + 1) * tile_px), 3),
    ]


def _entity_footprint(entity: Any) -> set[tuple[int, int]]:
    x, y, w, h = [int(value) for value in entity.tile_xywh]
    return {(tx, ty) for tx in range(x, x + w) for ty in range(y, y + h)}


def _territory_footprint(territory: Any) -> set[tuple[int, int]]:
    x, y, w, h = [int(value) for value in territory.tile_xywh]
    return {(tx, ty) for tx in range(x, x + w) for ty in range(y, y + h)}


def _interior_tiles(territory: Any) -> tuple[tuple[int, int], ...]:
    x, y, w, h = [int(value) for value in territory.tile_xywh]
    return tuple((tx, ty) for tx in range(x + 1, x + w - 1) for ty in range(y + 1, y + h - 1))


def _candidate_tile_support(scene: Any, *, territory_type: str) -> Tuple[Any, Tuple[tuple[int, int], ...], Tuple[tuple[int, int], ...]]:
    target = next((territory for territory in scene.territories if str(territory.territory_type) == str(territory_type)), None)
    if target is None:
        raise ValueError(f"rendered scene does not contain target territory: {territory_type}")

    occupied: set[tuple[int, int]] = set()
    for entity in scene.entities:
        occupied.update(_entity_footprint(entity))
    path_tiles = {tuple(int(v) for v in tile) for tile in scene.trace.get("path_tiles", [])}
    water_tiles = {tuple(int(v) for v in tile) for tile in scene.trace.get("water_tiles", [])}
    blocked = occupied | path_tiles | water_tiles
    all_territory_tiles: set[tuple[int, int]] = set()
    for territory in scene.territories:
        all_territory_tiles.update(_territory_footprint(territory))

    inside = tuple(tile for tile in _interior_tiles(target) if tile not in blocked)
    if not inside:
        raise ValueError("target territory has no empty interior ground tile")

    cols = int(scene.trace.get("grid_cols", 0))
    rows = int(scene.trace.get("grid_rows", 0))
    outside: list[tuple[int, int]] = []
    for y in range(1, max(1, rows - 1)):
        for x in range(1, max(1, cols - 1)):
            tile = (int(x), int(y))
            if tile in blocked or tile in all_territory_tiles:
                continue
            outside.append(tile)
    if len(outside) < len(OPTION_LABELS) - 1:
        raise ValueError("not enough empty outside ground tiles for distractors")
    return target, inside, tuple(outside)


def _distance_to_territory(tile: tuple[int, int], territory_tiles: set[tuple[int, int]]) -> int:
    x, y = int(tile[0]), int(tile[1])
    return min(abs(x - tx) + abs(y - ty) for tx, ty in territory_tiles)


def _select_option_tiles(
    *,
    scene: Any,
    target_territory: Any,
    inside_candidates: Sequence[tuple[int, int]],
    outside_candidates: Sequence[tuple[int, int]],
    correct_index: int,
    instance_seed: int,
    attempt_index: int,
) -> Tuple[Tuple[tuple[int, int], ...], tuple[int, int]]:
    """Choose one interior answer tile and nearby outside distractors with unique membership."""

    territory_tiles = _territory_footprint(target_territory)
    inside_index = resolve_selection_index(
        params={},
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:inside_tile:{attempt_index}",
    )
    correct_tile = tuple(inside_candidates[int(inside_index) % len(inside_candidates)])

    near = [
        tile
        for tile in outside_candidates
        if _distance_to_territory(tile, territory_tiles) <= MAX_DISTRACTOR_TERRITORY_DISTANCE
    ]
    near.sort(key=lambda tile: (_distance_to_territory(tile, territory_tiles), tile[1], tile[0]))
    if len(near) < len(OPTION_LABELS) - 1:
        raise ValueError("not enough near outside ground tiles for distractors")
    offset = resolve_selection_index(
        params={},
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:outside_tiles:{attempt_index}",
    )
    ordered_pool = tuple(near)
    distractors: list[tuple[int, int]] = []
    cursor = int(offset) % len(ordered_pool)
    while len(distractors) < len(OPTION_LABELS) - 1:
        tile = tuple(ordered_pool[cursor % len(ordered_pool)])
        if tile != correct_tile and tile not in set(distractors):
            distractors.append(tile)
        cursor += 1

    option_tiles: list[tuple[int, int]] = []
    distractor_iter = iter(distractors)
    for index in range(len(OPTION_LABELS)):
        if int(index) == int(correct_index):
            option_tiles.append(correct_tile)
        else:
            option_tiles.append(next(distractor_iter))
    return tuple(option_tiles), correct_tile


def _candidate_membership_by_label(option_tiles: Sequence[tuple[int, int]], target_territory: Any) -> Dict[str, bool]:
    territory_tiles = _territory_footprint(target_territory)
    return {
        str(OPTION_LABELS[index]): tuple(tile) in territory_tiles
        for index, tile in enumerate(option_tiles)
    }


def _candidate_distance_by_label(option_tiles: Sequence[tuple[int, int]], target_territory: Any) -> Dict[str, int]:
    territory_tiles = _territory_footprint(target_territory)
    return {
        str(OPTION_LABELS[index]): int(_distance_to_territory(tuple(tile), territory_tiles))
        for index, tile in enumerate(option_tiles)
    }


def _draw_candidate_labels(scene: Any, option_tiles: Sequence[tuple[int, int]], *, font_family: str) -> tuple[Any, Dict[str, list[float]], Dict[str, list[float]]]:
    image = scene.image.convert("RGB").copy()
    draw = ImageDraw.Draw(image)
    tile_px = int(scene.trace.get("tile_px", _DEFAULTS.tile_px))
    badge_w = max(28, min(38, int(round(tile_px * 0.70))))
    badge_h = max(24, min(34, int(round(tile_px * 0.60))))
    tile_bboxes: Dict[str, list[float]] = {}
    label_bboxes: Dict[str, list[float]] = {}
    for index, tile in enumerate(option_tiles):
        label = str(OPTION_LABELS[index])
        tile_box = _tile_bbox(tile, scene=scene)
        tile_bboxes[label] = tile_box
        cx = 0.5 * (float(tile_box[0]) + float(tile_box[2]))
        cy = 0.5 * (float(tile_box[1]) + float(tile_box[3]))
        label_box = [
            round(cx - badge_w * 0.5, 3),
            round(cy - badge_h * 0.5, 3),
            round(cx + badge_w * 0.5, 3),
            round(cy + badge_h * 0.5, 3),
        ]
        label_bboxes[label] = label_box
        draw_label_badge(
            draw,
            label,
            label_box,
            font_family=str(font_family),
            fill=(255, 255, 255),
            outline=(30, 46, 62),
            text_fill=(16, 24, 34),
            radius=4,
            width=2,
        )
    return image, tile_bboxes, label_bboxes


@register_task
class IllustrationsPixelVillageTerritoryTileMembershipLabelTask:
    """Select the lettered ground tile inside a named fenced territory."""

    task_id = TASK_ID
    domain = "illustrations"
    supported_query_ids = (QUERY_ID,)
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Render a territory-present village, bind one membership label, and emit tile-bbox annotation."""

        sample = _sample_spec(instance_seed=int(instance_seed), params=params)
        last_error: Exception | None = None
        scene = None
        target_territory = None
        option_tiles: Tuple[tuple[int, int], ...] = tuple()
        correct_tile: tuple[int, int] | None = None
        label_font_trace: Dict[str, Any] | None = None
        image = None
        candidate_tile_bboxes: Dict[str, list[float]] = {}
        candidate_label_bboxes: Dict[str, list[float]] = {}

        for attempt in range(max(1, int(max_attempts))):
            try:
                render_params = {
                    **dict(params),
                    TERRITORY_FORCE_PARAM[str(sample.territory_type)]: "force",
                }
                scene = _render_scene(
                    namespace=TASK_ID,
                    instance_seed=int(instance_seed),
                    params=render_params,
                    render_defaults=_RENDER_DEFAULTS,
                    attempt_index=int(attempt),
                    path_person_count=0,
                )
                target_territory, inside_candidates, outside_candidates = _candidate_tile_support(
                    scene,
                    territory_type=str(sample.territory_type),
                )
                option_tiles, correct_tile = _select_option_tiles(
                    scene=scene,
                    target_territory=target_territory,
                    inside_candidates=inside_candidates,
                    outside_candidates=outside_candidates,
                    correct_index=int(sample.correct_index),
                    instance_seed=int(instance_seed),
                    attempt_index=int(attempt),
                )
                label_font_trace = sample_visual_label_font_trace(
                    namespace_prefix=TASK_ID,
                    instance_seed=int(instance_seed),
                    params={**dict(_RENDER_DEFAULTS), **dict(params)},
                    namespace_suffix="candidate_tile_labels",
                    explicit_key="candidate_tile_label_font_family",
                    weights_key="candidate_tile_label_font_weights",
                )
                image, candidate_tile_bboxes, candidate_label_bboxes = _draw_candidate_labels(
                    scene,
                    option_tiles,
                    font_family=str(label_font_trace["font_family"]),
                )
                break
            except Exception as exc:  # pragma: no cover - retry surface depends on sampled map geometry.
                last_error = exc
                scene = None
                target_territory = None
                option_tiles = tuple()
                correct_tile = None
                label_font_trace = None
                image = None
                candidate_tile_bboxes = {}
                candidate_label_bboxes = {}

        if scene is None or target_territory is None or correct_tile is None or label_font_trace is None or image is None:
            raise RuntimeError(f"could not generate {TASK_ID}: {last_error}") from last_error

        answer_label = str(OPTION_LABELS[int(sample.correct_index)])
        selected_bbox = list(candidate_tile_bboxes[answer_label])
        annotation_artifacts = bbox_annotation_artifacts(selected_bbox)
        entity_bboxes = _entity_bbox_map(scene, pad=0.0)
        candidate_tiles_by_label = {
            str(OPTION_LABELS[index]): [int(tile[0]), int(tile[1])]
            for index, tile in enumerate(option_tiles)
        }
        membership_by_label = _candidate_membership_by_label(option_tiles, target_territory)
        distance_by_label = _candidate_distance_by_label(option_tiles, target_territory)
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_territory_tile_membership",
                "annotation_hint_territory_tile_membership",
                "json_example_territory_tile_membership",
                "json_example_answer_only_territory_tile_membership",
            ],
            context=f"prompt defaults for {TASK_ID}",
        )
        slots = {
            "territory_name": str(sample.territory_name),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults["answer_hint_territory_tile_membership"]),
            "annotation_hint": str(prompt_defaults["annotation_hint_territory_tile_membership"]),
            "json_example": str(prompt_defaults["json_example_territory_tile_membership"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only_territory_tile_membership"]),
        }
        prompt_artifacts = build_pixel_village_prompt_artifacts(
            domain=self.domain,
            scene_id=SCENE_ID,
            prompt_defaults=prompt_defaults,
            prompt_query_key=PROMPT_QUERY_KEY,
            slots=slots,
            instance_seed=int(instance_seed),
        )
        render_spec = pixel_village_render_spec(scene, scene_id=SCENE_ID)
        render_spec["style"] = {
            **dict(render_spec["style"]),
            "candidate_tile_label_font": dict(label_font_trace),
        }
        trace_payload = {
            "scene_ir": pixel_village_scene_ir(
                domain=self.domain,
                scene_id=SCENE_ID,
                scene=scene,
                relations={
                    "query_id": QUERY_ID,
                    "prompt_query_key": PROMPT_QUERY_KEY,
                    "target_territory": str(sample.territory_type),
                    "answer_label": answer_label,
                    "candidate_membership_by_label": dict(membership_by_label),
                },
            ),
            "query_spec": {
                "task_id": self.task_id,
                "query_id": QUERY_ID,
                "prompt_query_key": PROMPT_QUERY_KEY,
                "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": QUERY_ID,
                    "prompt_query_key": PROMPT_QUERY_KEY,
                    "target_territory": str(sample.territory_type),
                    "territory_name": str(sample.territory_name),
                    "target_territory_probabilities": dict(sample.territory_probabilities),
                    "correct_index": int(sample.correct_index),
                    "correct_index_probabilities": dict(sample.correct_index_probabilities),
                    "answer_label": answer_label,
                    "option_labels": list(OPTION_LABELS),
                    "candidate_tiles_by_label": dict(candidate_tiles_by_label),
                    "candidate_membership_by_label": dict(membership_by_label),
                    "candidate_distance_to_target_territory_by_label": dict(distance_by_label),
                    "selected_tile": [int(correct_tile[0]), int(correct_tile[1])],
                    "target_territory_tile_xywh": [int(value) for value in target_territory.tile_xywh],
                    "target_territory_bbox_px": [round(float(value), 3) for value in target_territory.bbox_xyxy],
                    "render_constraints": {str(TERRITORY_FORCE_PARAM[str(sample.territory_type)]): "force"},
                    "distractor_distance_to_target_territory_max": int(MAX_DISTRACTOR_TERRITORY_DISTANCE),
                    "renderer": _render_metadata(scene),
                },
            },
            "render_spec": render_spec,
            "render_map": {
                "image_id": "img0",
                "entity_bboxes_px": {str(key): [round(float(v), 3) for v in value] for key, value in entity_bboxes.items()},
                "candidate_tile_bboxes_px_by_label": {str(key): list(value) for key, value in candidate_tile_bboxes.items()},
                "candidate_label_bboxes_px_by_label": {str(key): list(value) for key, value in candidate_label_bboxes.items()},
                "selected_tile_bbox_px": selected_bbox,
                "candidate_tiles_by_label": dict(candidate_tiles_by_label),
                "candidate_membership_by_label": dict(membership_by_label),
                "candidate_distance_to_target_territory_by_label": dict(distance_by_label),
                "target_territory_bbox_px": [round(float(value), 3) for value in target_territory.bbox_xyxy],
                "target_territory_tile_xywh": [int(value) for value in target_territory.tile_xywh],
                "path_tiles": list(scene.trace.get("path_tiles", [])),
                "water_tiles": list(scene.trace.get("water_tiles", [])),
            },
            "execution_trace": {
                "query_id": QUERY_ID,
                "prompt_query_key": PROMPT_QUERY_KEY,
                "scene_id": SCENE_ID,
                "target_territory": str(sample.territory_type),
                "territory_name": str(sample.territory_name),
                "answer": answer_label,
                "answer_label": answer_label,
                "candidate_tiles_by_label": dict(candidate_tiles_by_label),
                "candidate_membership_by_label": dict(membership_by_label),
                "candidate_distance_to_target_territory_by_label": dict(distance_by_label),
                "selected_tile": [int(correct_tile[0]), int(correct_tile[1])],
                "entities": _scene_entities(scene),
                "territories": _scene_territories(scene),
                "renderer": _render_metadata(scene),
            },
            "witness_symbolic": {
                "answer_label": answer_label,
                "target_territory": str(sample.territory_type),
                "selected_tile": [int(correct_tile[0]), int(correct_tile[1])],
                "selected_tile_bbox": selected_bbox,
                "candidate_membership_by_label": dict(membership_by_label),
                "candidate_distance_to_target_territory_by_label": dict(distance_by_label),
            },
            "projected_annotation": {
                **dict(annotation_artifacts.projected_annotation),
            },
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
            answer_gt=TypedValue(type="option_letter", value=answer_label),
            annotation_gt=annotation_artifacts.annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=QUERY_ID,
        )


__all__ = ["IllustrationsPixelVillageTerritoryTileMembershipLabelTask", "TASK_ID", "_sample_spec"]
