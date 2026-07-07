"""Contract smoke tests for every active default TRACE task."""

from __future__ import annotations

import pytest

from trace.core.annotation_sanitization import (
    sanitize_trace_payload_for_public_annotation,
)
from trace.core.prompt_annotation_contract_audit import (
    _normalize_jsonable,
    _validate_annotation_value,
)
from trace.core.source_layout_policy import is_scene_package_task
from trace.core.seed import hash64
from trace.core.taxonomy import (
    ACTIVE_DOMAINS,
    inject_taxonomy_metadata,
    resolve_task_query_id,
    resolve_task_taxonomy,
)
from trace.tasks import create_task
from trace.tasks.registry import list_default_task_ids

REQUIRED_TRACE_KEYS = {
    "scene_ir",
    "query_spec",
    "render_spec",
    "render_map",
    "execution_trace",
    "witness_symbolic",
    "projected_annotation",
}

COUNT_CARDINALITY_SOURCE_KEYS = {
    "counted_ids",
    "counted_entity_ids",
    "counted_object_ids",
    "counted_item_ids",
    "counted_cell_ids",
    "counted_cells",
    "counted_piece_ids",
    "counted_box_ids",
    "counted_edge_ids",
    "counted_labels",
    "matching_ids",
    "matching_entity_ids",
    "matching_object_ids",
    "matching_item_ids",
    "matching_cell_ids",
    "matching_labels",
}

EXACT_ANNOTATION_SOURCE_KEYS = {
    "annotation_ids",
    "annotation_cell_edges",
    "annotation_state_path_labels",
    "accepting_path_labels",
}

SET_ANNOTATION_TYPES = {
    "bbox_set",
    "bbox_map",
    "point_map",
    "segment_set",
    "point_set",
}


def _generate_first_successful_output(task_id: str):
    task = create_task(task_id)
    last_exc: Exception | None = None
    for seed_index in range(8):
        instance_seed = int(hash64(0, f"{task_id}:active_default_contract", seed_index))
        try:
            return task.generate(
                instance_seed,
                params={},
                max_attempts=120,
            )
        except (
            Exception
        ) as exc:  # pragma: no cover - only used for unlucky generated seeds.
            last_exc = exc
    pytest.fail(f"failed to generate active task {task_id}: {last_exc}")


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _unwrap_typed_value(value):
    if isinstance(value, dict) and "type" in value and "value" in value:
        return value["value"]
    return value


def _values_equal(left, right) -> bool:
    left_value = _unwrap_typed_value(left)
    right_value = _unwrap_typed_value(right)
    if _is_number(left_value) and _is_number(right_value):
        return abs(float(left_value) - float(right_value)) < 1e-6
    return str(left_value) == str(right_value)


def _annotation_cardinality(value, *, annotation_type: str = "") -> int:
    if str(annotation_type) in {"bbox", "point", "segment"}:
        return 1 if value is not None else 0
    if isinstance(value, dict):
        return len(value)
    if isinstance(value, (list, tuple)):
        return len(value)
    return 1 if value is not None else 0


def _iter_nested_lists(value, *, prefix: str = ""):
    if not isinstance(value, dict):
        return
    for key, item in value.items():
        full_key = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(item, list):
            yield full_key, item
        elif isinstance(item, dict):
            yield from _iter_nested_lists(item, prefix=full_key)


def _projected_value_for_type(projected: dict, annotation_type: str):
    value = projected.get(annotation_type)
    if value is None and annotation_type == "point":
        value = projected.get("pixel_point")
    if value is None and annotation_type == "bbox":
        value = projected.get("pixel_bbox")
    if value is None and annotation_type == "point_set":
        value = projected.get("pixel_point_set")
    if value is None and annotation_type == "point_sequence":
        value = projected.get("pixel_point_sequence")
    if value is None and annotation_type == "point_map":
        value = projected.get("pixel_point_map")
    if value is None and annotation_type == "bbox_map":
        value = projected.get("pixel_bbox_map")
    return value


def _assert_answer_annotation_consistency(
    output, *, task_id: str, query_id: str
) -> None:
    """Check domain-agnostic answer/annotation invariants for one generated output."""

    annotation_type = str(output.annotation_gt.type)
    annotation_value = _normalize_jsonable(output.annotation_gt.value)
    annotation_len = _annotation_cardinality(
        annotation_value, annotation_type=annotation_type
    )
    image_size = tuple(output.image.size) if output.image is not None else None

    annotation_errors = _validate_annotation_value(
        annotation_type,
        annotation_value,
        image_size=image_size,
        field="annotation_gt",
    )
    assert annotation_errors == [], (task_id, query_id, annotation_errors)

    sanitized = sanitize_trace_payload_for_public_annotation(
        output.trace_payload,
        annotation_gt=output.annotation_gt,
    )
    projected = sanitized.get("projected_annotation", {})
    assert isinstance(projected, dict), (task_id, query_id, projected)
    assert str(projected.get("type", "")) == annotation_type, (
        task_id,
        query_id,
        projected,
    )
    projected_value = _projected_value_for_type(projected, annotation_type)
    assert projected_value is not None, (task_id, query_id, projected)
    projected_value = _normalize_jsonable(projected_value)
    assert projected_value == annotation_value, (
        task_id,
        query_id,
        projected_value,
        annotation_value,
    )
    projected_errors = _validate_annotation_value(
        annotation_type,
        projected_value,
        image_size=image_size,
        field="projected_annotation",
    )
    assert projected_errors == [], (task_id, query_id, projected_errors)

    execution_trace = output.trace_payload.get("execution_trace", {})
    assert isinstance(execution_trace, dict), (task_id, query_id, execution_trace)
    if "answer" in execution_trace:
        assert _values_equal(output.answer_gt.value, execution_trace["answer"]), (
            task_id,
            query_id,
            output.answer_gt.value,
            execution_trace["answer"],
        )

    witness = output.trace_payload.get("witness_symbolic", {})
    if isinstance(witness, dict) and _is_number(witness.get("count")):
        assert int(witness["count"]) == annotation_len, (
            task_id,
            query_id,
            witness,
            annotation_len,
        )

    for source_key, source_value in _iter_nested_lists(execution_trace):
        leaf_key = source_key.split(".")[-1]
        if leaf_key in EXACT_ANNOTATION_SOURCE_KEYS:
            assert len(source_value) == annotation_len, (
                task_id,
                query_id,
                source_key,
                len(source_value),
                annotation_len,
            )

    count_like_query = (
        "count" in str(query_id).lower() or "number" in str(query_id).lower()
    )
    if (
        str(output.answer_gt.type) == "integer"
        and annotation_type in SET_ANNOTATION_TYPES
        and count_like_query
    ):
        for source_key, source_value in _iter_nested_lists(execution_trace):
            leaf_key = source_key.split(".")[-1]
            if (
                leaf_key in COUNT_CARDINALITY_SOURCE_KEYS
                and len(source_value) == annotation_len
            ):
                assert int(output.answer_gt.value) == len(source_value), (
                    task_id,
                    query_id,
                    source_key,
                    output.answer_gt.value,
                    len(source_value),
                    annotation_len,
                )


@pytest.mark.parametrize("task_id", list_default_task_ids())
def test_active_default_task_public_contract(task_id: str) -> None:
    task = create_task(task_id)
    output = _generate_first_successful_output(task_id)
    taxonomy = resolve_task_taxonomy(task_id)
    migrated_task = is_scene_package_task(
        task_id, domain=str(getattr(task, "domain", ""))
    )
    registered_scene_id = None if migrated_task else str(getattr(task, "scene_id", ""))
    query_id = str(
        output.query_id
        or resolve_task_query_id(
            query_id=output.query_id, trace_payload=output.trace_payload
        )
    )
    trace_payload = inject_taxonomy_metadata(
        output.trace_payload,
        task_id=task_id,
        taxonomy=taxonomy,
        query_id=query_id,
        registered_domain=str(getattr(task, "domain", "")),
        registered_scene_id=registered_scene_id,
    )

    assert taxonomy.domain in ACTIVE_DOMAINS
    assert str(output.query_id) == query_id
    assert query_id
    assert str(output.answer_gt.type)
    assert str(output.annotation_gt.type)
    assert REQUIRED_TRACE_KEYS.issubset(set(output.trace_payload))

    trace_taxonomy = trace_payload["taxonomy"]
    assert trace_taxonomy["domain"] == taxonomy.domain
    assert trace_taxonomy["scene_id"] == taxonomy.scene_id
    assert trace_taxonomy["task_id"] == task_id
    assert trace_taxonomy["query_id"] == query_id
    assert trace_taxonomy["metadata_schema_version"] == "v0"
    assert trace_taxonomy["public"] == {
        "domain": taxonomy.domain,
        "scene_id": taxonomy.scene_id,
        "task_id": task_id,
        "query_id": query_id,
    }
    expected_registered = {
        "task_id": task_id,
        "domain": str(getattr(task, "domain", "")),
    }
    if not migrated_task:
        expected_registered["scene_id"] = str(registered_scene_id)
    assert trace_taxonomy["registered"] == expected_registered
    assert trace_taxonomy["source"]["implementation_task_id"]
    assert trace_taxonomy["source"]["implementation_domain"]
    assert trace_taxonomy["source"]["config_domain"] == str(getattr(task, "domain", ""))
    assert trace_taxonomy["source"]["prompt_domain"]
    if migrated_task:
        assert "implementation_scene_id" not in trace_taxonomy["source"]
        assert "config_scene_id" not in trace_taxonomy["source"]
        assert "prompt_scene_id" not in trace_taxonomy["source"]
    else:
        assert trace_taxonomy["source"]["implementation_scene_id"]
        assert trace_taxonomy["source"]["config_scene_id"] == str(registered_scene_id)
        assert trace_taxonomy["source"]["prompt_scene_id"]
    _assert_answer_annotation_consistency(output, task_id=task_id, query_id=query_id)
