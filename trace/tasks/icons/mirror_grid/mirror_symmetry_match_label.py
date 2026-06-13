"""Select the option cell whose mirror symmetry matches a Reference cell."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    load_scene_generation_rendering_prompt_defaults,
    required_group_defaults,
)
from ...shared.fixed_query import select_task_query_id
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_query_spec,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from ..shared.annotation import keyed_bbox_map_annotation

from .shared.defaults import MirrorGridDefaults
from .shared.rendering import sample_and_render_mirror_grid_scene
from .shared.sampling import fixed_grid_labels
from .shared.state import MirrorGridScenePayload
from .shared.styles import mirror_grid_style_trace, resolve_mirror_grid_render_params


TASK_ID = "task_icons__mirror_grid__mirror_symmetry_match_label"
DOMAIN = "icons"
SCENE_ID = "mirror_grid"
QUERY_ID = "mirror_symmetry_match_label"
MIRROR_VERTICAL_QUERY_ID = "mirror_vertical"
MIRROR_HORIZONTAL_QUERY_ID = "mirror_horizontal"
MIRROR_DIAGONAL_MAIN_QUERY_ID = "mirror_diagonal_main"
MIRROR_DIAGONAL_ANTI_QUERY_ID = "mirror_diagonal_anti"
MIRROR_BOTH_AXES_QUERY_ID = "mirror_both_axes"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    MIRROR_VERTICAL_QUERY_ID,
    MIRROR_HORIZONTAL_QUERY_ID,
    MIRROR_DIAGONAL_MAIN_QUERY_ID,
    MIRROR_DIAGONAL_ANTI_QUERY_ID,
    MIRROR_BOTH_AXES_QUERY_ID,
)
NOISE_NAMESPACE = "mirror_grid_symmetry_match_label"

_QUERY_TO_SYMMETRY_KIND: Dict[str, str] = {
    MIRROR_VERTICAL_QUERY_ID: "vertical",
    MIRROR_HORIZONTAL_QUERY_ID: "horizontal",
    MIRROR_DIAGONAL_MAIN_QUERY_ID: "diagonal_main",
    MIRROR_DIAGONAL_ANTI_QUERY_ID: "diagonal_anti",
    MIRROR_BOTH_AXES_QUERY_ID: "both_axes",
}
_SYMMETRY_KIND_TO_QUERY: Dict[str, str] = {
    str(kind): str(query) for query, kind in _QUERY_TO_SYMMETRY_KIND.items()
}


_DEFAULTS = MirrorGridDefaults()
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_scene_generation_rendering_prompt_defaults(
    DOMAIN,
    SCENE_ID,
    task_id=TASK_ID,
)


def _probability_map(values: Sequence[str | int], *, selected: str | int | None = None) -> Dict[str, float]:
    """Return a JSON-stable probability map for one finite support."""

    support = tuple(str(value) for value in values)
    if not support:
        return {}
    if selected is not None:
        selected_text = str(selected)
        return {str(value): (1.0 if str(value) == selected_text else 0.0) for value in support}
    probability = 1.0 / float(len(support))
    return {str(value): float(probability) for value in support}


def _option_count_choices(params: Mapping[str, Any]) -> Tuple[int, ...]:
    """Resolve supported option counts for the scene."""

    raw = params.get(
        "option_count_choices",
        group_default(_GEN_DEFAULTS, "option_count_choices", _DEFAULTS.option_count_choices),
    )
    if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
        raise ValueError("option_count_choices must be a sequence of integers")
    choices = tuple(dict.fromkeys(int(value) for value in raw))
    if not choices:
        raise ValueError("option_count_choices must not be empty")
    if any(int(value) not in (4, 6) for value in choices):
        raise ValueError("mirror-grid option_count_choices currently supports only 4 or 6")
    return choices


def _select_mirror_query(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float], Dict[str, Any]]:
    """Select the public mirror-symmetry branch using the shared task policy."""

    return select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=SUPPORTED_QUERY_IDS,
        default_query_id=MIRROR_VERTICAL_QUERY_ID,
        task_id=TASK_ID,
        namespace=f"{TASK_ID}.public_query",
    )


def _symmetry_kind_for_query(public_query_id: str) -> str:
    """Translate a public query branch into the neutral scene symmetry kind."""

    try:
        return str(_QUERY_TO_SYMMETRY_KIND[str(public_query_id)])
    except KeyError as exc:
        raise ValueError(f"unsupported query_id for {TASK_ID}: {public_query_id}") from exc


def _public_symmetry_id(symmetry_kind: str) -> str:
    """Translate a neutral scene symmetry kind into public trace vocabulary."""

    if str(symmetry_kind) == "none":
        return "none"
    try:
        return str(_SYMMETRY_KIND_TO_QUERY[str(symmetry_kind)])
    except KeyError as exc:
        raise ValueError(f"unsupported symmetry kind in {TASK_ID}: {symmetry_kind}") from exc


def _public_cell_payload(cell: Mapping[str, Any]) -> Dict[str, Any]:
    """Return one trace cell payload with public and neutral symmetry fields."""

    payload = dict(cell)
    symmetry_kind = str(payload.get("symmetry_kind", ""))
    payload["symmetry_id"] = _public_symmetry_id(symmetry_kind)
    return payload


def _public_scene_payload(scene_payload: MirrorGridScenePayload) -> Tuple[Dict[str, Any], Tuple[Dict[str, Any], ...]]:
    """Return public trace entities for the reference cell and option cells."""

    reference_cell = _public_cell_payload(scene_payload.reference_cell)
    scene_cells = tuple(_public_cell_payload(cell) for cell in scene_payload.scene_cells)
    return dict(reference_cell), tuple(dict(cell) for cell in scene_cells)


def _scene_cell_public_symmetry_ids(scene_payload: MirrorGridScenePayload) -> Tuple[str, ...]:
    """Return public symmetry ids for every visible option cell."""

    return tuple(_public_symmetry_id(str(kind)) for kind in scene_payload.scene_cell_symmetry_kinds)


def _resolve_option_count(
    rng,
    *,
    params: Mapping[str, Any],
    explicit_answer_label: str,
) -> Tuple[int, Dict[str, float]]:
    """Select 4 or 6 visible option cells."""

    choices = _option_count_choices(params)
    explicit_count = params.get("option_count")
    if explicit_count is not None:
        count = int(explicit_count)
        if count not in choices:
            raise ValueError(f"unsupported option_count for {TASK_ID}: {count}; supported: {choices}")
        if explicit_answer_label and explicit_answer_label not in fixed_grid_labels(int(count)):
            raise ValueError(f"answer_label {explicit_answer_label!r} is not visible with option_count={count}")
        return count, _probability_map(choices, selected=count)

    feasible_choices = choices
    if explicit_answer_label:
        feasible_choices = tuple(count for count in choices if explicit_answer_label in fixed_grid_labels(int(count)))
        if not feasible_choices:
            raise ValueError(f"answer_label {explicit_answer_label!r} is not visible in any supported option count")

    count = int(rng.choice(feasible_choices))
    return count, _probability_map(feasible_choices)


def _resolve_answer_label(
    rng,
    *,
    params: Mapping[str, Any],
    option_labels: Sequence[str],
) -> Tuple[str, int, Dict[str, float]]:
    """Select the single matching option label."""

    labels = tuple(str(label) for label in option_labels)
    explicit_label = str(params.get("answer_label", "") or params.get("correct_option_label", "")).strip().upper()
    if explicit_label:
        if explicit_label not in labels:
            raise ValueError(f"unsupported answer_label for visible options {labels}: {explicit_label}")
        return explicit_label, int(labels.index(explicit_label)), _probability_map(labels, selected=explicit_label)
    answer_label = str(rng.choice(labels))
    return answer_label, int(labels.index(answer_label)), _probability_map(labels)


def _prompt_artifacts(*, instance_seed: int, prompt_defaults: Mapping[str, Any]):
    """Render answer-only and answer-with-annotation prompt variants."""

    prompt_selection = render_scene_prompt_variants(
        domain=DOMAIN,
        scene_id=SCENE_ID,
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(prompt_defaults["task_key"]),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        dynamic_slots={
            "object_description": str(prompt_defaults["object_description"]),
            "question_text": str(prompt_defaults["question_text"]),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "annotation_hint": str(prompt_defaults["annotation_hint"]),
            "answer_hint": str(prompt_defaults["answer_hint"]),
            "json_example": str(prompt_defaults["json_example"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
        },
        instance_seed=int(instance_seed),
    )
    return build_prompt_trace_artifacts(prompt_selection)


def _cell_by_label(scene_cells: Sequence[Mapping[str, Any]], label: str) -> Dict[str, Any]:
    """Return one option cell payload by visible label."""

    for cell in scene_cells:
        if str(cell.get("label")) == str(label):
            return dict(cell)
    raise RuntimeError(f"missing option cell for answer label {label!r}")


@register_task
class IconsMirrorGridMirrorSymmetryMatchLabelTask:
    """Select the labeled option cell matching the Reference cell's mirror symmetry."""

    task_id = TASK_ID
    domain = DOMAIN
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic mirror-grid option-match instance."""

        selected_query_id, query_probabilities, task_params = _select_mirror_query(
            instance_seed=int(instance_seed),
            params=params,
        )
        reference_symmetry_kind = _symmetry_kind_for_query(str(selected_query_id))
        scene_rng = spawn_rng(int(instance_seed), "scene")
        explicit_answer_label = str(
            task_params.get("answer_label", "") or task_params.get("correct_option_label", "")
        ).strip().upper()
        option_count, option_count_probabilities = _resolve_option_count(
            scene_rng,
            params=task_params,
            explicit_answer_label=str(explicit_answer_label),
        )
        option_labels = fixed_grid_labels(int(option_count))
        answer_label, answer_index, answer_label_probabilities = _resolve_answer_label(
            scene_rng,
            params=task_params,
            option_labels=option_labels,
        )
        distractor_count = int(option_count) - 1
        distractor_count_probabilities = {str(distractor_count): 1.0}
        render_params = resolve_mirror_grid_render_params(
            task_params,
            render_defaults=_RENDER_DEFAULTS,
            defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        pool_manifest = str(
            task_params.get(
                "pool_manifest",
                group_default(_GEN_DEFAULTS, "pool_manifest", _DEFAULTS.pool_manifest),
            )
        )

        scene_payload = None
        image = None
        last_error: Exception | None = None
        for _ in range(max(1, int(max_attempts))):
            try:
                scene_payload, image = sample_and_render_mirror_grid_scene(
                    scene_rng,
                    instance_seed=int(instance_seed),
                    reference_symmetry_kind=str(reference_symmetry_kind),
                    object_count=int(option_count),
                    target_count=1,
                    matching_indices=(int(answer_index),),
                    render_params=render_params,
                    pool_manifest=str(pool_manifest),
                    noise_namespace=f"{NOISE_NAMESPACE}:{selected_query_id}:{answer_label}",
                )
                break
            except Exception as exc:  # pragma: no cover - exercised through retry loop
                last_error = exc
                continue
        if scene_payload is None or image is None:
            raise RuntimeError(f"failed to generate {TASK_ID} instance") from last_error

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
                "annotation_hint",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_artifacts = _prompt_artifacts(
            instance_seed=int(instance_seed),
            prompt_defaults=prompt_defaults,
        )

        reference_cell, scene_cells = _public_scene_payload(scene_payload)
        matching_labels = tuple(str(label) for label in scene_payload.matching_labels)
        if matching_labels != (str(answer_label),):
            raise RuntimeError(
                f"mirror-grid answer mismatch: expected {answer_label!r}, got {matching_labels!r}"
            )
        matching_cell = _cell_by_label(scene_cells, str(answer_label))
        annotation_artifacts = keyed_bbox_map_annotation(
            {
                "reference_cell": reference_cell["cell_bbox_xyxy"],
                "matching_option_cell": matching_cell["cell_bbox_xyxy"],
            }
        )
        answer_gt = TypedValue(type="option_letter", value=str(answer_label))
        annotation_gt = TypedValue(
            type=str(annotation_artifacts["annotation_type"]),
            value=dict(annotation_artifacts["annotation_value"]),
        )
        scene_cell_symmetry_ids = _scene_cell_public_symmetry_ids(scene_payload)
        query_spec = build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(selected_query_id),
            params={
                "task_id": str(self.task_id),
                "scene_id": SCENE_ID,
                "query_id_probabilities": dict(query_probabilities),
                "option_count": int(option_count),
                "option_count_probabilities": dict(option_count_probabilities),
                "option_labels": list(option_labels),
                "answer_label": str(answer_label),
                "answer_label_probabilities": dict(answer_label_probabilities),
                "distractor_count": int(distractor_count),
                "distractor_count_probabilities": dict(distractor_count_probabilities),
                "pool_manifest": str(pool_manifest),
                "mirror_signature": str(selected_query_id),
                "reference_symmetry_kind": str(scene_payload.reference_symmetry_kind),
            },
        )
        common_ids = {
            "task_id": str(self.task_id),
            "scene_id": SCENE_ID,
            "query_id": str(selected_query_id),
        }
        trace_payload = {
            "scene_ir": {
                **common_ids,
                "scene_kind": "icons_reference_grid_mirror_symmetry_match_label",
                "entities": [dict(reference_cell), *[dict(item) for item in scene_cells]],
                "relations": {
                    "target": "option_cell_matching_reference_mirror_symmetry",
                    "reference_symmetry_id": str(selected_query_id),
                    "reference_symmetry_kind": str(scene_payload.reference_symmetry_kind),
                    "mirror_signature": str(selected_query_id),
                    "matching_cell_label": str(answer_label),
                    "answer_label": str(answer_label),
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(scene_payload.panel_geometry),
                },
            },
            "query_spec": query_spec,
            "render_spec": {
                **common_ids,
                "canvas_size": [int(render_params["canvas_width"]), int(render_params["canvas_height"])],
                "coord_space": "pixel",
                "panel_geometry": dict(scene_payload.panel_geometry),
                "style": mirror_grid_style_trace(
                    render_params=render_params,
                    sampled_palette_rgb=scene_payload.sampled_palette_rgb,
                ),
            },
            "render_map": {
                "image_id": "img0",
                "anchors": {
                    "reference_cell": dict(reference_cell),
                    "matching_option_cell": dict(matching_cell),
                    "answer_label": str(answer_label),
                    "option_cells": [dict(item) for item in scene_cells],
                },
            },
            "execution_trace": {
                **common_ids,
                "scene_variant": "reference_with_labeled_option_cells",
                "query_id_probabilities": dict(query_probabilities),
                "mirror_signature": str(selected_query_id),
                "reference_symmetry_kind": str(scene_payload.reference_symmetry_kind),
                "option_count": int(scene_payload.object_count),
                "option_count_probabilities": dict(option_count_probabilities),
                "option_labels": list(scene_payload.cell_labels),
                "answer_label": str(answer_label),
                "matching_cell_label": str(answer_label),
                "distractor_count": int(scene_payload.distractor_count),
                "distractor_count_probabilities": dict(distractor_count_probabilities),
                "scene_cell_symmetry_ids": list(scene_cell_symmetry_ids),
                "scene_cell_symmetry_kinds": list(scene_payload.scene_cell_symmetry_kinds),
                "question_format": "select_option_cell_matching_reference_mirror_symmetry",
                "annotation_roles": ["reference_cell", "matching_option_cell"],
            },
            "witness_symbolic": {
                "answer_label": str(answer_label),
                "reference_symmetry_id": str(selected_query_id),
                "reference_symmetry_kind": str(scene_payload.reference_symmetry_kind),
                "mirror_signature": str(selected_query_id),
                "reference_cell_bbox": list(reference_cell["cell_bbox_xyxy"]),
                "matching_option_cell_bbox": list(matching_cell["cell_bbox_xyxy"]),
            },
            "projected_annotation": dict(annotation_artifacts["projected_annotation"]),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(selected_query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["IconsMirrorGridMirrorSymmetryMatchLabelTask", "TASK_ID"]
