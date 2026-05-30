"""Public trace sanitization for pixel-grounded evidence payloads."""

from __future__ import annotations

from typing import Any, Mapping

from .types import TypedValue


PUBLIC_IMAGE_EVIDENCE_TYPES = frozenset(
    {
        "bbox_sequence",
        "bbox_set",
        "keyed_bbox_map",
        "keyed_point_map",
        "point_pair_set",
        "point_sequence",
        "point_set",
    }
)

_SOURCE_EXECUTION_KEYS = frozenset(
    {
        "edge_set",
        "evidence_edges",
        "evidence_entity_ids",
        "evidence_graph_points",
        "evidence_labels",
        "graph_point",
        "graph_point_map",
        "graph_point_set",
        "grid_path",
        "grid_point",
        "grid_point_map",
        "grid_point_set",
        "grid_points",
        "id_path",
        "id_set",
        "label_path",
        "label_sequence",
        "label_set",
        "matching_ids",
        "matching_labels",
        "original_evidence_type",
        "original_evidence_value",
        "path_edge_labels",
        "path_ids",
        "path_labels",
        "reachable_ids",
        "reachable_target_ids",
        "shortest_path_ids",
        "violation_ids",
        "winner_path_ids",
        "winning_component_ids",
    }
)


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return [item for item in value]
    if isinstance(value, tuple):
        return [item for item in value]
    return []


def _as_string_keyed_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): item for key, item in value.items()}


def _evidence_count(value: Any) -> int:
    if isinstance(value, Mapping):
        return len(value)
    if isinstance(value, (list, tuple)):
        return len(value)
    return 1 if value is not None else 0


def public_projected_evidence(evidence: TypedValue) -> dict[str, Any]:
    """Return the exported projected-evidence payload for a public evidence value."""

    evidence_type = str(evidence.type)
    value = _as_list(evidence.value)
    if evidence_type == "bbox_set":
        return {
            "type": "bbox_set",
            "bbox_set": [list(item) for item in value],
        }
    if evidence_type == "bbox_sequence":
        return {
            "type": "bbox_sequence",
            "bbox_sequence": [list(item) for item in value],
        }
    if evidence_type == "keyed_bbox_map":
        keyed_bboxes = {key: list(item) for key, item in _as_string_keyed_mapping(evidence.value).items()}
        return {
            "type": "keyed_bbox_map",
            "keyed_bbox_map": keyed_bboxes,
        }
    if evidence_type == "point_set":
        points = [list(item) for item in value]
        return {
            "type": "point_set",
            "point_set": points,
            "pixel_point_set": points,
        }
    if evidence_type == "point_sequence":
        points = [list(item) for item in value]
        return {
            "type": "point_sequence",
            "point_sequence": points,
            "pixel_point_sequence": points,
        }
    if evidence_type == "keyed_point_map":
        keyed_points = {key: list(item) for key, item in _as_string_keyed_mapping(evidence.value).items()}
        return {
            "type": "keyed_point_map",
            "keyed_point_map": keyed_points,
            "pixel_keyed_point_map": keyed_points,
        }
    if evidence_type == "point_pair_set":
        pairs = [[list(endpoint) for endpoint in item] for item in value]
        return {
            "type": "point_pair_set",
            "point_pair_set": pairs,
        }
    return {
        "type": evidence_type,
        "value": evidence.value,
    }


def public_witness_summary(evidence: TypedValue) -> dict[str, Any]:
    """Return a non-symbolic witness summary for persisted traces."""

    return {
        "type": str(evidence.type),
        "count": _evidence_count(evidence.value),
    }


def _strip_source_execution_metadata(value: Any) -> Any:
    if isinstance(value, Mapping):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = str(key)
            if normalized_key in _SOURCE_EXECUTION_KEYS:
                continue
            if normalized_key.endswith("_ids") or normalized_key.endswith("_labels"):
                continue
            if normalized_key.endswith("_id") and normalized_key not in {"image_id"}:
                continue
            if normalized_key.endswith("_by_label"):
                continue
            cleaned[normalized_key] = _strip_source_execution_metadata(item)
        return cleaned
    if isinstance(value, list):
        return [_strip_source_execution_metadata(item) for item in value]
    if isinstance(value, tuple):
        return [_strip_source_execution_metadata(item) for item in value]
    return value


def sanitize_trace_payload_for_public_evidence(
    trace_payload: Mapping[str, Any],
    *,
    evidence_gt: TypedValue,
) -> dict[str, Any]:
    """Drop source symbolic/grid evidence from persisted trace payload fields."""

    sanitized = {str(key): value for key, value in dict(trace_payload).items()}
    sanitized["execution_trace"] = _strip_source_execution_metadata(sanitized.get("execution_trace", {}))
    sanitized["witness_symbolic"] = public_witness_summary(evidence_gt)
    sanitized["projected_evidence"] = public_projected_evidence(evidence_gt)
    return sanitized
