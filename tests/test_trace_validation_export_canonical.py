from __future__ import annotations

import json
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from evaluation.trace_validation import export_canonical as exporter
from scripts import trace_eval_public_export as public


MODEL_SLUG = "qwen25vl3b-base"
MODEL_SPECS = tuple(exporter.PUBLIC_MODEL_IDS.items())
MODEL_REVISION = "1" * 40
JUDGE_REVISION = "2" * 40
DATASET_SHA = "3" * 64
IMAGE_HASHES = ("4" * 64, "5" * 64)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


def _receipt(row: dict, response: str, *, model_slug: str) -> dict:
    response_sha = public.response_sha256(response)
    return {
        "schema_version": "trace-validation-generation-receipt-v1",
        "status": "complete",
        "error": None,
        "row_index": row["row_index"],
        "instance_id": row["instance_id"],
        "task": row["task"],
        "domain": row["domain"],
        "answer_type": row["answer_type"],
        "model_slug": model_slug,
        "request_hash": public.canonical_sha256(
            {"private_transport_payload": row["row_index"]}
        ),
        "request": {
            "prompt_sha256": public.prompt_sha256(row["prompt_answer"]),
            "ordered_image_sha256": [image["sha256"] for image in row["images"]],
        },
        "raw_response": response,
        "raw_response_sha256": response_sha,
        "finish_reason": "stop",
        "api_response": {
            "usage": {
                "prompt_tokens": 100 + row["row_index"],
                "completion_tokens": 10 + row["row_index"],
            },
            "private_api_envelope": "/dev/shm/must-not-leak",
        },
    }


def _scored(
    row: dict, receipt: dict, *, model_slug: str, judged: bool
) -> dict:
    if judged:
        deterministic = {
            "status": "missing",
            "route": "missing",
            "typed_candidate": None,
            "candidate_provenance": [],
        }
        judge_status = "ok"
        judge_answer = "B"
        final_route = "judge"
    else:
        deterministic = {
            "status": "found",
            "route": "balanced_object",
            "typed_candidate": 4,
            "candidate_provenance": [
                {
                    "accepted": True,
                    "typed_candidate": 4,
                    "route": "balanced_object",
                }
            ],
        }
        judge_status = None
        judge_answer = None
        final_route = "deterministic:balanced_object"
    return {
        "schema_version": "trace-validation-scored-row-v1",
        "scoring_contract_version": "trace-validation-answer-scoring-v2",
        "model_slug": model_slug,
        "row_index": row["row_index"],
        "instance_id": row["instance_id"],
        "task": row["task"],
        "domain": row["domain"],
        "answer_type": row["answer_type"],
        "raw_response_sha256": receipt["raw_response_sha256"],
        "generation_request_hash": receipt["request_hash"],
        "deterministic_extraction": deterministic,
        "deterministic_extraction_version": "trace-validation-answer-extraction-v1",
        "deterministic_found": int(not judged),
        "judge_requested": int(judged),
        "judge_status": judge_status,
        "judge_answer": judge_answer,
        "judge_resolved": int(judged),
        "final_extraction_route": final_route,
        "combined_semantic_correct": 1,
        # This intentionally private source field must never appear in output.
        "answer_gt": row["answer_gt"],
    }


def _source_fixture(root: Path) -> Path:
    source = root / "private_source"
    rows = [
        {
            "row_index": 0,
            "instance_id": "instance-0",
            "task": "task_test__scene__integer",
            "domain": "test",
            "answer_type": "integer",
            "prompt_answer": "PRIVATE PROMPT ZERO",
            "answer_gt": {"type": "integer", "value": 4},
            "images": [{"sha256": IMAGE_HASHES[0], "relative_path": "/private/a.png"}],
        },
        {
            "row_index": 1,
            "instance_id": "instance-1",
            "task": "task_test__scene__option",
            "domain": "test",
            "answer_type": "option_letter",
            "prompt_answer": "PRIVATE PROMPT ONE",
            "answer_gt": {"type": "option_letter", "value": "B"},
            "images": [{"sha256": IMAGE_HASHES[1], "relative_path": "/private/b.png"}],
        },
    ]
    _write_json(
        source / "dataset" / "manifest.json",
        {
            "schema_version": "trace-validation-dataset-manifest-v1",
            "dataset": {
                "repo_id": "example/private-dataset",
                "revision": "6" * 40,
                "config": "default",
                "split": "validation",
                "file": "private.parquet",
                "file_sha256": DATASET_SHA,
                "file_size_bytes": 1,
                "row_count": len(rows),
            },
            "media": {
                "storage": "content-addressed-original-encoded-bytes",
                "reencoded": False,
                "resized": False,
            },
            "rows": rows,
        },
    )
    suite_path = root / "suite.json"
    _write_json(
        suite_path,
        {
            "models": [
                {
                    "slug": model_slug,
                    "label": f"Fixture {public_model_id}",
                    "repo_id": f"example/{public_model_id}",
                    "revision": MODEL_REVISION,
                }
                for model_slug, public_model_id in MODEL_SPECS
            ],
            "judge": {
                "repo_id": "Qwen/Qwen3-32B",
                "revision": JUDGE_REVISION,
                "served_model_name": "fixture-judge",
            },
        },
    )

    responses_by_model: dict[str, list[dict]] = {}
    for model_slug, _public_model_id in MODEL_SPECS:
        responses = [
            _receipt(rows[0], 'Analysis. {"answer":4}', model_slug=model_slug),
            _receipt(rows[1], "The final selection is B.", model_slug=model_slug),
        ]
        responses_by_model[model_slug] = responses
        response_path = source / "generation" / model_slug / "responses.jsonl"
        _write_jsonl(response_path, responses)
        _write_json(
            source / "generation" / model_slug / "run_metadata.json",
            {
                "schema_version": "trace-validation-generation-run-v1",
                "status": "complete",
                "model_slug": model_slug,
                "model_revision": MODEL_REVISION,
                "responses_sha256": public.sha256_file(response_path),
                "media_transport": "file-url",
                "mm_processor_kwargs": {
                    "min_pixels": 262144,
                    "max_pixels": 4194304,
                },
                "decoding": {
                    "temperature": 0.6,
                    "top_p": 0.95,
                    "top_k": -1,
                    "max_tokens": 2048,
                    "seed": 42,
                    "presence_penalty": 0.0,
                    "repetition_penalty": 1.0,
                },
                "model_path": "/dev/shm/private-model",
            },
        )
    scored_rows = [
        _scored(
            rows[row_index],
            responses_by_model[model_slug][row_index],
            model_slug=model_slug,
            judged=bool(row_index),
        )
        for model_slug, _public_model_id in MODEL_SPECS
        for row_index in range(2)
    ]
    _write_jsonl(
        source / "scoring" / "scored_rows.jsonl",
        scored_rows,
    )
    _write_json(
        source / "scoring" / "summary.json",
        {"private_path": "/dev/shm/private-score", "overall": []},
    )
    _write_jsonl(
        source / "judge" / "judge_results.jsonl",
        [
            {
                "model_slug": model_slug,
                "row_index": 1,
                "instance_id": "instance-1",
                "raw_response_sha256": responses_by_model[model_slug][1][
                    "raw_response_sha256"
                ],
                "judge_status": "ok",
                "answer": "B",
                "attempts": [
                    {
                        "raw_output": '```json\n{"status":"ok","answer":"B","evidence":"selection is B"}\n```',
                        "endpoint": "http://127.0.0.1:9999/v1",
                    }
                ],
            }
            for model_slug, _public_model_id in MODEL_SPECS
        ],
    )
    (source / "code_snapshot").mkdir(parents=True, exist_ok=True)
    (source / "code_snapshot" / "evaluator.py").write_text(
        "# immutable fixture evaluator\n", encoding="utf-8"
    )
    (source / "code_snapshot" / "README.md").write_text(
        "fixture snapshot\n", encoding="utf-8"
    )
    (source / "provenance").mkdir(parents=True, exist_ok=True)
    (source / "provenance" / "git_head.txt").write_text(
        "8" * 40 + "\n", encoding="utf-8"
    )
    return suite_path


def test_canonical_export_uses_exact_contracts_and_omits_private_source(tmp_path: Path) -> None:
    suite_path = _source_fixture(tmp_path)
    source = tmp_path / "private_source"
    output = tmp_path / "canonical"
    private_plan = tmp_path / "private" / "export-plan.json"
    kwargs = {
        "source_root": source,
        "suite_path": suite_path,
        "output_root": output,
        "run_id": "test-iid-run-v1",
        "suite_id": "test_iid_suite_v1",
        "benchmark_id": "test_iid_validation",
        "seed": 42,
        "public_model_ids": exporter.PUBLIC_MODEL_IDS,
        "verification_report": {"phase": "full", "status": "ok"},
        "private_plan_output": private_plan,
        "evaluation_harness_revision": "7" * 40,
    }
    verified = exporter._build_verified_export(**kwargs)
    rebuilt = exporter._build_verified_export(**kwargs)

    assert verified.manifest_sha256 == rebuilt.manifest_sha256
    assert len(verified.files) == 61
    assert len(verified.manifest["artifacts"]) == 24
    assert public.load_and_verify_public_export(output, expected_artifacts=24)
    assert private_plan.stat().st_mode & 0o777 == 0o600
    plan = public.load_export_plan(private_plan)
    assert plan.expected_identities == {
        (config, model_id, 42, "test_iid_validation")
        for config in public.CONFIG_NAMES
        for model_id in exporter.PUBLIC_MODEL_IDS.values()
    }

    all_rows: dict[str, list[dict]] = {}
    expected_counts = {"responses": 16, "extractions": 16, "scores": 24}
    for config, expected_count in expected_counts.items():
        files = list((output / "data" / config).rglob("*.parquet"))
        assert len(files) == 8
        rows: list[dict] = []
        for path in files:
            parquet = pq.ParquetFile(path)
            assert parquet.schema_arrow == public.PUBLIC_SCHEMAS[config]
            rows.extend(parquet.read().to_pylist())
        assert len(rows) == expected_count
        all_rows[config] = rows

    serialized = json.dumps(all_rows, ensure_ascii=False, sort_keys=True)
    for secret in (
        "PRIVATE PROMPT ZERO",
        "PRIVATE PROMPT ONE",
        '"answer_gt"',
        '"api_response"',
        "/dev/shm/",
        "/private/a.png",
        "127.0.0.1:9999",
    ):
        assert secret not in serialized

    assert sum(row["used_judge"] for row in all_rows["extractions"]) == 8
    assert {row["extraction_status"] for row in all_rows["extractions"]} == {
        "resolved"
    }
    aggregates = [row for row in all_rows["scores"] if row["score_scope"] == "aggregate"]
    assert len(aggregates) == 8
    assert {row["score_value"] for row in aggregates} == {100.0}
    part_manifests = list((output / "metadata" / "parts").rglob("*.json"))
    assert len(part_manifests) == 24
    for path in part_manifests:
        provenance = json.loads(path.read_text(encoding="utf-8"))["provenance"]
        assert provenance["evaluation_harness_revision"] == "7" * 40
        assert provenance["producer_code_revision"] == "8" * 40
        assert provenance["producer_code_sha256"] == exporter._code_snapshot_sha256(
            source / "code_snapshot"
        )


def test_production_export_runs_full_verifier_before_reading_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    class VerificationStopped(RuntimeError):
        pass

    def stop_verification(**_kwargs):
        calls.append("verify")
        raise VerificationStopped("verification gate")

    monkeypatch.setattr(
        exporter.campaign_verify, "verify_full_phase", stop_verification
    )
    with pytest.raises(VerificationStopped, match="verification gate"):
        exporter.export_iid_validation(
            source_root=tmp_path / "bundle-does-not-exist",
            output_root=tmp_path / "output",
        )
    assert calls == ["verify"]
    assert not (tmp_path / "output").exists()


def test_export_rejects_private_path_in_opaque_judge_output(tmp_path: Path) -> None:
    suite_path = _source_fixture(tmp_path)
    source = tmp_path / "private_source"
    judge_path = source / "judge" / "judge_results.jsonl"
    judge_rows = [json.loads(line) for line in judge_path.read_text().splitlines()]
    judge_rows[0]["attempts"][-1]["raw_output"] += "\n/dev/shm/private-leak"
    _write_jsonl(judge_path, judge_rows)

    with pytest.raises(public.PublicExportError, match="local path leaked"):
        exporter._build_verified_export(
            source,
            suite_path,
            tmp_path / "canonical",
            run_id="test-iid-run-v1",
            suite_id="test_iid_suite_v1",
            benchmark_id="test_iid_validation",
            seed=42,
            public_model_ids=exporter.PUBLIC_MODEL_IDS,
            evaluation_harness_revision="7" * 40,
        )


def test_public_verifier_rejects_tampered_part_and_bad_harness_revision(
    tmp_path: Path,
) -> None:
    suite_path = _source_fixture(tmp_path)
    source = tmp_path / "private_source"
    output = tmp_path / "canonical"
    exporter._build_verified_export(
        source,
        suite_path,
        output,
        run_id="test-iid-run-v1",
        suite_id="test_iid_suite_v1",
        benchmark_id="test_iid_validation",
        seed=42,
        public_model_ids=exporter.PUBLIC_MODEL_IDS,
        evaluation_harness_revision="7" * 40,
    )
    parquet = next((output / "data" / "responses").rglob("*.parquet"))
    parquet.write_bytes(parquet.read_bytes() + b"tamper")
    with pytest.raises(public.PublicExportIntegrityError, match="digest mismatch"):
        public.load_and_verify_public_export(output, expected_artifacts=24)

    with pytest.raises(
        exporter.CanonicalExportError, match="40- or 64-hex revision"
    ):
        exporter._evaluation_harness_revision("main")
