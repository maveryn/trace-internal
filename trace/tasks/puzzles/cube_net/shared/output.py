"""Trace payload assembly helpers for cube-net puzzle tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from .state import NET_COORDS, SCENE_ID, SurfacePathDataset


def json_ready(value: Any) -> Any:
    """Convert tuples and nested mappings into JSON-friendly containers."""

    if isinstance(value, Mapping):
        return {str(key): json_ready(inner) for key, inner in value.items()}
    if isinstance(value, tuple):
        return [json_ready(inner) for inner in value]
    if isinstance(value, list):
        return [json_ready(inner) for inner in value]
    return value


def build_cube_net_trace_payload(
    *,
    scene_ir: Mapping[str, Any],
    query_spec: Mapping[str, Any],
    render_spec: Mapping[str, Any],
    render_map: Mapping[str, Any],
    execution_trace: Mapping[str, Any],
    witness_symbolic: Mapping[str, Any],
    projected_annotation: Mapping[str, Any],
    answer_gt: Mapping[str, Any],
    annotation_gt: Mapping[str, Any],
    prompt_defaults: Mapping[str, Any],
    prompt_artifacts: Any,
) -> Dict[str, Any]:
    """Assemble one trace payload from task-owned semantic dictionaries."""

    return {
        "scene_ir": json_ready(dict(scene_ir)),
        "query_spec": json_ready(dict(query_spec)),
        "render_spec": json_ready(dict(render_spec)),
        "render_map": json_ready(dict(render_map)),
        "execution_trace": json_ready(dict(execution_trace)),
        "witness_symbolic": json_ready(dict(witness_symbolic)),
        "projected_annotation": json_ready(dict(projected_annotation)),
        "answer_gt": json_ready(dict(answer_gt)),
        "annotation_gt": json_ready(dict(annotation_gt)),
        "prompt_spec": {
            "defaults": json_ready(dict(prompt_defaults)),
            "active": json_ready(dict(prompt_artifacts.prompt_variant)),
        },
    }


def surface_path_trace_parts(
    *,
    dataset: SurfacePathDataset,
    option_specs: list[dict[str, Any]],
    scene_variant: str,
    answer_value: str,
) -> Dict[str, Any]:
    """Return common folded-path trace sections after task answer binding."""

    face_entities = [
        {
            "entity_id": f"face_{face}",
            "kind": "cube_net_face",
            "face_id": str(face),
            "face_label": str(label),
        }
        for face, label in sorted(dataset.face_labels.items())
    ]
    relations = {
        "scene_variant": str(scene_variant),
        "start_face": str(dataset.start_face),
        "path_sides": [str(side) for side in dataset.path_sides],
        "face_sequence": [str(face) for face in dataset.face_sequence],
        "endpoint_face": str(dataset.endpoint_face),
        "correct_option_label": str(answer_value),
    }
    execution_trace = {
        "scene_id": SCENE_ID,
        "scene_variant": str(scene_variant),
        "face_labels": dict(dataset.face_labels),
        "net_coords": {
            str(face): [int(coord[0]), int(coord[1])]
            for face, coord in NET_COORDS.items()
        },
        "start_face": str(dataset.start_face),
        "path_sides": [str(side) for side in dataset.path_sides],
        "face_sequence": [str(face) for face in dataset.face_sequence],
        "face_label_sequence": [
            str(dataset.face_labels[str(face)])
            for face in dataset.face_sequence
        ],
        "endpoint_face": str(dataset.endpoint_face),
        "endpoint_face_label": str(dataset.face_labels[str(dataset.endpoint_face)]),
        "option_specs": list(option_specs),
        "answer_value": str(answer_value),
    }
    return {
        "entities": face_entities,
        "relations": relations,
        "execution_trace": execution_trace,
        "witness_symbolic": {
            "type": "folded_surface_net_path",
            "value": {
                "path_sides": [str(side) for side in dataset.path_sides],
                "face_sequence": [str(face) for face in dataset.face_sequence],
                "endpoint_face": str(dataset.endpoint_face),
                "correct_option_label": str(answer_value),
            },
        },
    }


__all__ = ["build_cube_net_trace_payload", "json_ready", "surface_path_trace_parts"]
