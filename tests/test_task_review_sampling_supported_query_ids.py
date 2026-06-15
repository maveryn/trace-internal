"""Regression tests for task-review query-id sampling."""

from __future__ import annotations

from types import SimpleNamespace

from trace.core import task_review_sampling


def test_collect_query_id_samples_uses_declared_supported_query_ids(monkeypatch) -> None:
    class DeclaredQueryTask:
        supported_query_ids = ("left_branch", "right_branch")

        def generate(self, instance_seed: int, *, params: dict[str, object], max_attempts: int) -> object:
            query_id = str(params.get("query_id") or "left_branch")
            return SimpleNamespace(
                query_id=query_id,
                trace_payload={
                    "query_spec": {
                        "query_id": query_id,
                        "params": {
                            "query_id_probabilities": {query_id: 1.0},
                        },
                    },
                },
            )

    monkeypatch.setattr(task_review_sampling, "create_task", lambda task_id: DeclaredQueryTask())

    collected = task_review_sampling.collect_query_id_samples(
        task_id="task_dummy__review__declared_query",
        target_count_per_query_id=3,
        seed=11,
        max_attempts_per_instance=5,
        max_total_samples_per_task=12,
        workers=1,
        collector=lambda output, instance_seed: {
            "instance_seed": int(instance_seed),
            "generation_params": {},
            "query_id": str(output.query_id),
        },
    )

    assert collected["expected_query_ids"] == ["left_branch", "right_branch"]
    assert collected["collected_query_id_counts"] == {"left_branch": 3, "right_branch": 3}
    assert collected["incomplete_query_ids"] == []
