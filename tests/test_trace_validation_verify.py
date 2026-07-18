from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from unittest import mock

import pytest
from PIL import Image

from evaluation.trace_validation import generate
from evaluation.trace_validation import prepare_dataset as prepare
from evaluation.trace_validation import score
from evaluation.trace_validation import verify


class FakeResponse:
    status_code = 200

    def __init__(self, payload: dict):
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self):
        self._lock = threading.Lock()
        self.calls = 0

    def post(self, _url, *, headers, json, timeout):
        del headers, timeout
        text = "".join(
            item.get("text", "")
            for item in json["messages"][1]["content"]
            if item.get("type") == "text"
        )
        match = re.search(r"question (\d+)", text)
        assert match
        row_index = int(match.group(1))
        if row_index == 1:
            content = "After considering the image, I settle on value 1."
        else:
            content = json_module.dumps({"answer": row_index})
        with self._lock:
            call_index = self.calls
            self.calls += 1
        return FakeResponse(
            {
                "id": f"response-{json['model']}-{call_index}",
                "model": json["model"],
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 4},
            }
        )


json_module = json


@dataclass
class Campaign:
    suite_path: Path
    manifest_path: Path
    parquet_path: Path
    generation_root: Path
    score_dir: Path
    judge_results: Path
    policy: verify.VerificationPolicy


def _png_bytes(index: int) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (9 + index, 7), (index * 40, 10, 20)).save(buffer, format="PNG")
    return buffer.getvalue()


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def _build_campaign(tmp_path: Path) -> Campaign:
    dataset_root = tmp_path / "prepared"
    parquet_path = tmp_path / "fixture.parquet"
    parquet_path.write_bytes(b"pinned-fixture-parquet")
    parquet_sha = prepare.sha256_file(parquet_path)
    rows = []
    for index in range(3):
        payload = _png_bytes(index)
        digest = prepare.sha256_bytes(payload)
        relative_path = f"media/sha256/{digest[:2]}/{digest}.png"
        image_path = dataset_root / relative_path
        image_path.parent.mkdir(parents=True, exist_ok=True)
        image_path.write_bytes(payload)
        rows.append(
            {
                "row_index": index,
                "instance_id": f"instance-{index}",
                "task": f"task_fixture__scene__objective_{index}",
                "domain": "fixture",
                "answer_type": "integer",
                "prompt_answer": f"<image>fixture question {index}",
                "answer_gt": {"type": "integer", "value": index},
                "images": [
                    {
                        "image_index": 0,
                        "sha256": digest,
                        "size_bytes": len(payload),
                        "width": 9 + index,
                        "height": 7,
                        "format": "PNG",
                        "mime_type": "image/png",
                        "relative_path": relative_path,
                    }
                ],
            }
        )
    manifest = {
        "schema_version": prepare.MANIFEST_SCHEMA,
        "dataset": {
            "repo_id": "fixture/trace",
            "revision": "a" * 40,
            "config": "default",
            "split": "validation",
            "file": "data/fixture.parquet",
            "file_sha256": parquet_sha,
            "file_size_bytes": parquet_path.stat().st_size,
            "row_count": 3,
        },
        "media": {
            "storage": prepare.MEDIA_STORAGE,
            "paths_relative_to": prepare.MANIFEST_NAME,
            "reencoded": False,
            "resized": False,
        },
        "rows": rows,
    }
    manifest_path = dataset_root / "manifest.json"
    prepare.atomic_write_json(manifest_path, manifest)

    model_pins = (
        verify.ModelPin("fixture-model-a", "fixture/model-a", "b" * 40),
        verify.ModelPin("fixture-model-b", "fixture/model-b", "c" * 40),
    )
    suite = {
        "schema_version": "trace-validation-suite-v1",
        "suite_id": "fixture-iid-suite",
        "dataset": {
            "repo_id": "fixture/trace",
            "revision": "a" * 40,
            "split": "validation",
            "file": "data/fixture.parquet",
            "sha256": parquet_sha,
            "rows": 3,
            "tasks": 3,
            "samples_per_task": 1,
            "distribution": "iid_same_tasks_nonoverlapping_samples",
            "prompt_key": "prompt_answer",
            "image_key": "images",
        },
        "prompt": {
            "system_prompt_file": "rlvr/examples/prompts/trace_vero_json_system_prompt_answer.txt",
            "system_prompt_sha256": verify.EXPECTED_SYSTEM_PROMPT_FILE_SHA256,
            "chat_template": "native_checkpoint_template",
            "add_generation_prompt": True,
        },
        "generation": {
            "seed": 42,
            "responses_per_prompt": 1,
            "temperature": 0.6,
            "top_p": 0.95,
            "top_k": -1,
            "presence_penalty": 0.0,
            "frequency_penalty": 0.0,
            "repetition_penalty": 1.0,
            "max_tokens": 2048,
            "min_image_pixels": 262144,
            "max_image_pixels": 4194304,
            "server_generation_config": "vllm",
        },
        "scoring": {
            "strict_contract": "trace-answer-exact-json-v1",
            "deterministic_extraction": verify.ANSWER_EXTRACTION_VERSION,
            "semantic_match": "trace-answer-exact-match-v0",
            "judge_only_on": ["missing", "ambiguous"],
            "unresolved_rows_score": 0,
            "drop_failed_rows": False,
        },
        "judge": {
            "repo_id": "Qwen/Qwen3-32B",
            "revision": "d" * 40,
            "served_model_name": "fixture-judge",
            "temperature": 0.0,
            "top_p": 1.0,
            "thinking": False,
            "max_token_retries": [128, 256, 512],
            "input_fields": ["raw_response", "answer_type"],
            "forbidden_fields": ["image", "question", "choices", "answer_gt_value"],
        },
        "models": [
            {
                "slug": pin.slug,
                "label": pin.slug.upper(),
                "repo_id": pin.repo_id,
                "revision": pin.revision,
            }
            for pin in model_pins
        ],
    }
    suite_path = tmp_path / "suite.json"
    suite_path.write_text(json.dumps(suite, indent=2) + "\n", encoding="utf-8")
    policy = verify.VerificationPolicy(
        suite_sha256=prepare.sha256_file(suite_path),
        dataset_manifest_sha256=prepare.sha256_file(manifest_path),
        dataset_file_sha256=parquet_sha,
        suite_id="fixture-iid-suite",
        dataset_repo_id="fixture/trace",
        dataset_revision="a" * 40,
        dataset_file="data/fixture.parquet",
        rows=3,
        tasks=3,
        samples_per_task=1,
        models=model_pins,
    )

    generation_root = tmp_path / "generation"
    session = FakeSession()
    for pin in model_pins:
        model_path = tmp_path / "models" / pin.slug
        model_path.mkdir(parents=True)
        (model_path / ".trace_model_revision.json").write_text(
            json.dumps(
                {
                    "schema_version": "trace-model-revision-v1",
                    "slug": pin.slug,
                    "source": pin.repo_id,
                    "resolved_commit": pin.revision,
                    "immutable_revision": pin.revision,
                }
            ),
            encoding="utf-8",
        )
        with mock.patch.object(generate, "_http_session", return_value=session):
            metadata = generate.run_generation(
                manifest_path=manifest_path,
                output_dir=generation_root / pin.slug,
                endpoint_url="http://127.0.0.1:9000/v1",
                served_model=pin.slug,
                model_slug=pin.slug,
                model_path=model_path,
                model_revision=pin.revision,
                media_transport="file-url",
                allowed_local_media_root=dataset_root,
                concurrency=2,
                retry_backoff_seconds=0,
                progress_every=0,
                expected_rows=3,
                require_pinned_manifest=False,
            )
        assert metadata["status"] == "complete"
    return Campaign(
        suite_path=suite_path,
        manifest_path=manifest_path,
        parquet_path=parquet_path,
        generation_root=generation_root,
        score_dir=tmp_path / "scoring" / "final",
        judge_results=tmp_path / "judge" / "judge_results.jsonl",
        policy=policy,
    )


@pytest.fixture
def campaign(tmp_path: Path) -> Campaign:
    return _build_campaign(tmp_path)


def _verify_generation(campaign: Campaign):
    return verify.verify_generation_phase(
        suite_path=campaign.suite_path,
        dataset_manifest=campaign.manifest_path,
        dataset_parquet=campaign.parquet_path,
        generation_root=campaign.generation_root,
        policy=campaign.policy,
    )


def test_generation_only_verifies_all_receipts_and_hashes(campaign: Campaign):
    suite, dataset, generation = _verify_generation(campaign)

    assert suite["suite_id"] == "fixture-iid-suite"
    assert len(dataset.rows) == 3
    assert len(generation.records) == 6
    assert set(generation.response_paths) == {"fixture-model-a", "fixture-model-b"}


def test_generation_only_rejects_decoding_drift(campaign: Campaign):
    metadata_path = campaign.generation_root / "fixture-model-a" / "run_metadata.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["decoding"]["top_k"] = 0
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(verify.VerificationError, match="decoding contract mismatch"):
        _verify_generation(campaign)


def test_generation_only_rejects_response_content_drift(campaign: Campaign):
    model_dir = campaign.generation_root / "fixture-model-a"
    responses_path = model_dir / "responses.jsonl"
    rows = [json.loads(line) for line in responses_path.read_text().splitlines()]
    rows[0]["raw_response"] = "tampered"
    _write_jsonl(responses_path, rows)
    metadata_path = model_dir / "run_metadata.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["responses_sha256"] = prepare.sha256_file(responses_path)
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(verify.VerificationError, match="raw response hash mismatch"):
        _verify_generation(campaign)


def _score_with_fixture_loader(
    campaign: Campaign,
    *,
    output_dir: Path,
    judge_results: Path | None,
) -> None:
    manifest = json.loads(campaign.manifest_path.read_text())
    generation_paths = [
        campaign.generation_root / pin.slug / "responses.jsonl"
        for pin in campaign.policy.models
    ]
    args = argparse.Namespace(
        dataset_manifest=campaign.manifest_path,
        suite=campaign.suite_path,
        generation_jsonl=generation_paths,
        judge_results=judge_results,
        output_dir=output_dir,
    )
    suite_document = json.loads(campaign.suite_path.read_text())
    suite_models = {model["slug"]: model for model in suite_document["models"]}
    with mock.patch.object(
        score,
        "_load_dataset_manifest",
        return_value=(manifest, manifest["rows"]),
    ), mock.patch.object(
        score,
        "_load_suite",
        return_value=(suite_document, suite_models),
    ):
        score.run(args)
    summary_path = output_dir / "summary.json"
    summary = json.loads(summary_path.read_text())
    summary["provenance"]["rows_per_model"] = campaign.policy.rows
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def _prepare_full_artifacts(campaign: Campaign) -> None:
    preliminary = campaign.score_dir.parent / "pre_judge"
    _score_with_fixture_loader(campaign, output_dir=preliminary, judge_results=None)
    pending = [json.loads(line) for line in (preliminary / "judge_pending.jsonl").read_text().splitlines()]
    assert len(pending) == 2
    judge_rows = []
    for pending_row in pending:
        rendered_prompt_sha256 = hashlib.sha256(
            f"prompt:{pending_row['model_slug']}:{pending_row['row_index']}".encode()
        ).hexdigest()
        tokenizer_template_sha256 = hashlib.sha256(b"template").hexdigest()
        request_contract = {
            "contract_version": verify.JUDGE_CONTRACT_VERSION,
            "model_slug": pending_row["model_slug"],
            "row_index": pending_row["row_index"],
            "instance_id": pending_row["instance_id"],
            "raw_response_sha256": pending_row["raw_response_sha256"],
            "answer_type": pending_row["answer_type"],
            "deterministic_status": pending_row["deterministic_status"],
            "deterministic_extraction_version": verify.ANSWER_EXTRACTION_VERSION,
            "judge_model": "fixture-judge",
            "judge_revision": "d" * 40,
            "tokenizer_model": "Qwen/Qwen3-32B",
            "system_prompt_sha256": verify.EXPECTED_JUDGE_SYSTEM_PROMPT_SHA256,
            "rendered_prompt_sha256": rendered_prompt_sha256,
            "tokenizer_template_sha256": tokenizer_template_sha256,
            "temperature": 0.0,
            "top_p": 1.0,
            "seed": 0,
            "retry_token_limits": [128, 256, 512],
        }
        request_hash = hashlib.sha256(
            json.dumps(
                request_contract,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        raw_output = '{"status":"ok","answer":1,"evidence":"value 1"}'
        result = {
            "schema_version": "trace-validation-judge-receipt-v1",
            "contract_version": verify.JUDGE_CONTRACT_VERSION,
            "request_hash": request_hash,
            "request_contract": request_contract,
            "raw_response_sha256": pending_row["raw_response_sha256"],
            "rendered_prompt_sha256": rendered_prompt_sha256,
            "system_prompt_sha256": verify.EXPECTED_JUDGE_SYSTEM_PROMPT_SHA256,
            "tokenizer_template_sha256": tokenizer_template_sha256,
            "tokenizer_model": "Qwen/Qwen3-32B",
            "judge_revision": "d" * 40,
            "judge_model": "fixture-judge",
            "model_slug": pending_row["model_slug"],
            "row_index": pending_row["row_index"],
            "instance_id": pending_row["instance_id"],
            "answer_type": pending_row["answer_type"],
            "deterministic_status": pending_row["deterministic_status"],
            "deterministic_extraction_version": verify.ANSWER_EXTRACTION_VERSION,
            "judge_status": "ok",
            "answer": 1,
            "evidence": "value 1",
            "attempts": [
                {
                    "retry_number": 0,
                    "max_tokens": 128,
                    "endpoint": "http://127.0.0.1:9100/v1",
                    "raw_output": raw_output,
                    "finish_reason": "stop",
                    "elapsed_seconds": 0.1,
                    "validation_error": None,
                }
            ],
        }
        receipt_path = campaign.judge_results.parent / "receipts" / f"{request_hash}.json"
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(result), encoding="utf-8")
        judge_rows.append(result)
    judge_rows.sort(key=lambda row: (row["model_slug"], row["row_index"]))
    _write_jsonl(campaign.judge_results, judge_rows)
    _score_with_fixture_loader(
        campaign,
        output_dir=campaign.score_dir,
        judge_results=campaign.judge_results,
    )


def _verify_full(campaign: Campaign):
    return verify.verify_full_phase(
        suite_path=campaign.suite_path,
        dataset_manifest=campaign.manifest_path,
        dataset_parquet=campaign.parquet_path,
        generation_root=campaign.generation_root,
        score_dir=campaign.score_dir,
        judge_results=campaign.judge_results,
        policy=campaign.policy,
    )


def test_full_phase_verifies_scoring_judge_and_summary(campaign: Campaign):
    _prepare_full_artifacts(campaign)

    report = _verify_full(campaign)

    assert report["status"] == "ok"
    assert report["generation_rows"] == 6
    assert report["scored_rows"] == 6
    assert report["judge_pending_rows"] == 2
    assert report["judge_result_rows"] == 2
    assert report["unresolved_rows"] == 0


def test_full_phase_rejects_missing_judge_result(campaign: Campaign):
    _prepare_full_artifacts(campaign)
    rows = campaign.judge_results.read_text().splitlines()
    campaign.judge_results.write_text(rows[0] + "\n", encoding="utf-8")

    with pytest.raises(verify.VerificationError, match="one-to-one with pending"):
        _verify_full(campaign)


def test_full_phase_rejects_stale_failed_fenced_attempt(campaign: Campaign):
    _prepare_full_artifacts(campaign)
    judge_rows = [
        json.loads(line) for line in campaign.judge_results.read_text().splitlines()
    ]
    stale = judge_rows[0]
    stale["judge_status"] = "failed"
    stale["answer"] = None
    stale["evidence"] = ""
    fenced_output = (
        "```json\n"
        '{"status":"missing","answer":null,"evidence":""}'
        "\n```"
    )
    stale["attempts"] = [
        {
            "retry_number": retry_number,
            "max_tokens": max_tokens,
            "endpoint": "http://127.0.0.1:9100/v1",
            "raw_output": fenced_output,
            "finish_reason": "stop",
            "elapsed_seconds": 0.1,
            "validation_error": "JudgeOutputError: judge output: invalid JSON",
        }
        for retry_number, max_tokens in enumerate((128, 256, 512))
    ]
    _write_jsonl(campaign.judge_results, judge_rows)
    receipt_path = (
        campaign.judge_results.parent
        / "receipts"
        / f"{stale['request_hash']}.json"
    )
    receipt_path.write_text(json.dumps(stale), encoding="utf-8")

    with pytest.raises(verify.VerificationError, match="valid attempt is marked as failed"):
        _verify_full(campaign)


def test_full_phase_rejects_inconsistent_summary(campaign: Campaign):
    _prepare_full_artifacts(campaign)
    summary_path = campaign.score_dir / "summary.json"
    summary = json.loads(summary_path.read_text())
    summary["overall"][0]["combined_semantic_accuracy"] = 0.123
    summary_path.write_text(json.dumps(summary), encoding="utf-8")

    with pytest.raises(verify.VerificationError, match="overall summary is inconsistent"):
        _verify_full(campaign)
