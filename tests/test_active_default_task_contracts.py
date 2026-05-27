"""Contract smoke tests for every active default TRACE task."""

from __future__ import annotations

import pytest

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
    "projected_evidence",
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
        except Exception as exc:  # pragma: no cover - only used for unlucky generated seeds.
            last_exc = exc
    pytest.fail(f"failed to generate active task {task_id}: {last_exc}")


@pytest.mark.parametrize("task_id", list_default_task_ids())
def test_active_default_task_public_contract(task_id: str) -> None:
    task = create_task(task_id)
    output = _generate_first_successful_output(task_id)
    taxonomy = resolve_task_taxonomy(task_id)
    query_id = str(
        output.query_id
        or resolve_task_query_id(query_id=output.query_id, trace_payload=output.trace_payload)
    )
    trace_payload = inject_taxonomy_metadata(
        output.trace_payload,
        task_id=task_id,
        taxonomy=taxonomy,
        query_id=query_id,
        registered_domain=str(getattr(task, "domain", "")),
        registered_task_group=str(getattr(task, "task_group", "")),
    )

    assert taxonomy.domain in ACTIVE_DOMAINS
    assert str(output.query_id) == "default"
    assert query_id
    assert str(output.answer_gt.type)
    assert str(output.evidence_gt.type)
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
    assert trace_taxonomy["registered"] == {
        "task_id": task_id,
        "domain": str(getattr(task, "domain", "")),
        "task_group": str(getattr(task, "task_group", "")),
    }
    assert trace_taxonomy["source"]["implementation_task_id"]
    assert trace_taxonomy["source"]["implementation_domain"]
    assert trace_taxonomy["source"]["implementation_task_group"]
    assert trace_taxonomy["source"]["config_domain"] == str(getattr(task, "domain", ""))
    assert trace_taxonomy["source"]["config_task_group"] == str(getattr(task, "task_group", ""))
    assert trace_taxonomy["source"]["prompt_domain"]
    assert trace_taxonomy["source"]["prompt_task_group"]
