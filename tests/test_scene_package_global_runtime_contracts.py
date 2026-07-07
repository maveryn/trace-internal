"""Global runtime-record contracts for source-layout source layout.

These checks are intentionally not part of the per-scene handoff gate in
``tests/test_source_layout_contracts.py``. They cover dataset ABI
shape across exported records, so a failure here should block global source-layout
cleanup, not review artifact generation for one otherwise isolated scene.
"""

from __future__ import annotations

import pytest

import trace.core.source_layout_policy as source_layout_policy
from trace.core.reward_contracts import resolve_reward_contract
from trace.core.taxonomy import TaxonomyEntry, inject_taxonomy_metadata
from trace.core.types import CurriculumIndex, ImageRecord, TraceRef, TrainInstance, TypedValue


FORBIDDEN_SOURCE_LAYOUT_EXPORT_KEYS = ("scene_id", "source_scene_id", "scene_sampling_probabilities")


def test_scene_package_runtime_records_omit_scene_id_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    task_id = "task_dummy__scene_package_demo__integer_count"
    monkeypatch.setattr(source_layout_policy, "SCENE_PACKAGE_SOURCE_LAYOUT_DOMAINS", frozenset({"dummy"}))
    assert source_layout_policy.is_scene_package_task(task_id, domain="dummy")
    train_record = TrainInstance(
        instance_version="v0",
        instance_id="dummy_instance",
        instance_seed=123,
        domain="dummy",
        task=task_id,
        scene_id="scene_package_demo",
        query_id="integer_count",
        prompt="How many marked dots are visible?",
        images=[
            ImageRecord(
                image_id="dummy_image",
                format="png",
                image_hash="abc",
                path="images/dummy.png",
            )
        ],
        answer_gt=TypedValue(type="integer", value=1),
        annotation_gt=TypedValue(type="point_set", value=[[8.0, 8.0]]),
        reward_contract=resolve_reward_contract(answer_type="integer", annotation_type="point_set"),
        trace_ref=TraceRef(shard_id="trace_shard_0001.jsonl.zst", line_index=0, trace_record_hash="abc"),
        versions={"renderer_version": "v0"},
    ).to_dict()
    curriculum_record = CurriculumIndex(
        instance_id="dummy_instance",
        domain="dummy",
        task=task_id,
        scene_id="scene_package_demo",
        query_id="integer_count",
    ).to_dict()
    trace_record = inject_taxonomy_metadata(
        {"scene_ir": {}, "query_spec": {}, "render_spec": {}, "execution_trace": {}},
        task_id=task_id,
        taxonomy=TaxonomyEntry(
            domain="dummy",
            scene_id="scene_package_demo",
            source_domain="dummy",
            source_scene_id="scene_package_demo",
        ),
        query_id="integer_count",
        registered_domain="dummy",
        registered_scene_id=None,
    )
    for record in (train_record, curriculum_record, trace_record):
        for key in FORBIDDEN_SOURCE_LAYOUT_EXPORT_KEYS:
            assert key not in record
    taxonomy = trace_record["taxonomy"]
    assert "scene_id" not in taxonomy["registered"]
    assert "implementation_scene_id" not in taxonomy["source"]
    assert "config_scene_id" not in taxonomy["source"]
    assert "prompt_scene_id" not in taxonomy["source"]
