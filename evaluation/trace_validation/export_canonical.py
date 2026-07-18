#!/usr/bin/env python3
"""Export the verified TRACE IID campaign as a sanitized ``trace_eval_v1`` run.

The production campaign is first checked with :mod:`evaluation.trace_validation.verify`.
Only then are the byte-identical release inputs in the repository result bundle read.
The output uses the same response, extraction, score, part-manifest, and release-
manifest contracts as the other canonical Trace evaluation runs.

Prompts, reference answers, API envelopes, receipts, machine paths, logs, and code
snapshots are deliberately not copied into the canonical tree.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from evaluation.trace_validation import verify as campaign_verify
from scripts import trace_eval_public_export as public


REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_ID = "trace-iid-validation-2000-answer-seed42-8models-v1"
SUITE_ID = "trace_validation_iid2000_v1"
BENCHMARK_ID = "trace_validation_iid2000"
SEED = 42
EXPECTED_ROWS = 2_000
EXPECTED_MODELS = 8
SOURCE_CONTRACT_VERSION = "trace-validation-iid-canonical-source-v1"

DEFAULT_SOURCE_ROOT = (
    REPO_ROOT / "results" / "trace_validation_iid2000_seed42_8models_20260718"
)
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "results" / "canonical" / "trace_eval_v1" / RUN_ID
DEFAULT_PRIVATE_PLAN_OUTPUT = (
    REPO_ROOT
    / "results"
    / "canonical"
    / "private"
    / f"{RUN_ID}.export-plan.json"
)

PUBLIC_MODEL_IDS = {
    "qwen25vl3b-base": "qwen2.5-vl-3b-base",
    "trace-qwen25vl3b-answer-step500-20260716": "trace-qwen2.5-vl-3b",
    "qwen25vl7b-base": "qwen2.5-vl-7b-base",
    "trace-qwen25vl7b-answer-step500-rerun-20260715": "trace-qwen2.5-vl-7b",
    "game-rl-qwen25vl7b": "game-rl-qwen2.5-vl-7b",
    "sphinx-qwen7b-500": "sphinx-qwen2.5-vl-7b",
    "pcgrpo-qwen25vl7b-jigsaw-care": "pcgrpo-qwen2.5-vl-7b",
    "vero-qwen25-7b": "vero-qwen2.5-vl-7b",
}

_SCORING_FILES = (
    "scored_rows.jsonl",
    "summary.json",
    "by_task.jsonl",
    "summary.md",
    "judge_pending.jsonl",
)


class CanonicalExportError(RuntimeError):
    """The verified campaign cannot be represented by the canonical contract."""


@dataclass(frozen=True)
class SourceFile:
    path: Path
    sha256: str
    size: int


@dataclass(frozen=True)
class LoadedSource:
    dataset_manifest: dict[str, Any]
    dataset_manifest_file: SourceFile
    suite: dict[str, Any]
    suite_file: SourceFile
    models: tuple[public.ModelMapping, ...]
    generation_rows: dict[str, list[dict[str, Any]]]
    generation_metadata: dict[str, dict[str, Any]]
    generation_files: dict[str, tuple[SourceFile, SourceFile]]
    scored_rows: dict[tuple[str, int], dict[str, Any]]
    scored_file: SourceFile
    score_summary_file: SourceFile
    judge_rows: dict[tuple[str, int], dict[str, Any]]
    judge_file: SourceFile
    producer_revision: str | None
    producer_code_sha256: str


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CanonicalExportError(message)


def _sha256_file(path: Path) -> str:
    return public.sha256_file(path)


def _source_file(path: Path) -> SourceFile:
    _require(path.is_file(), f"required source artifact is missing: {path}")
    return SourceFile(path=path, sha256=_sha256_file(path), size=path.stat().st_size)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CanonicalExportError(f"cannot load JSON artifact {path}: {error}") from error
    _require(isinstance(value, dict), f"JSON artifact is not an object: {path}")
    return value


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        handle = path.open(encoding="utf-8")
    except OSError as error:
        raise CanonicalExportError(f"cannot open JSONL artifact {path}: {error}") from error
    with handle:
        for line_number, line in enumerate(handle, start=1):
            _require(bool(line.strip()), f"blank JSONL line at {path}:{line_number}")
            try:
                value = json.loads(line)
            except json.JSONDecodeError as error:
                raise CanonicalExportError(
                    f"invalid JSON at {path}:{line_number}: {error}"
                ) from error
            _require(
                isinstance(value, dict),
                f"JSONL row is not an object at {path}:{line_number}",
            )
            rows.append(value)
    return rows


def _same_file(left: Path, right: Path, label: str) -> None:
    left_file = _source_file(left)
    right_file = _source_file(right)
    _require(
        (left_file.sha256, left_file.size) == (right_file.sha256, right_file.size),
        f"release bundle differs from the fully verified production artifact: {label}",
    )


def _attest_release_bundle(
    source_root: Path,
    *,
    verified_dataset_manifest: Path,
    verified_generation_root: Path,
    verified_score_dir: Path,
    verified_judge_results: Path,
) -> None:
    """Bind every release input to the production tree accepted by the full verifier."""

    _same_file(
        source_root / "dataset" / "manifest.json",
        verified_dataset_manifest,
        "dataset manifest",
    )
    for slug in PUBLIC_MODEL_IDS:
        for filename in ("responses.jsonl", "run_metadata.json"):
            _same_file(
                source_root / "generation" / slug / filename,
                verified_generation_root / slug / filename,
                f"generation/{slug}/{filename}",
            )
    for filename in _SCORING_FILES:
        _same_file(
            source_root / "scoring" / filename,
            verified_score_dir / filename,
            f"scoring/{filename}",
        )
    _same_file(
        source_root / "judge" / "judge_results.jsonl",
        verified_judge_results,
        "judge/judge_results.jsonl",
    )
    snapshot_root = source_root / "code_snapshot"
    _require(snapshot_root.is_dir(), "release bundle has no code snapshot")
    source_files = [
        path
        for path in sorted(snapshot_root.rglob("*"))
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
        and (path.suffix == ".py" or path.name == "suite.v1.json")
    ]
    _require(source_files, "release bundle code snapshot is empty")
    for snapshot_path in source_files:
        relative = snapshot_path.relative_to(snapshot_root)
        _same_file(
            snapshot_path,
            REPO_ROOT / relative,
            f"code_snapshot/{relative.as_posix()}",
        )


def _code_snapshot_sha256(snapshot_root: Path) -> str:
    _require(snapshot_root.is_dir(), "source code snapshot is missing")
    files: list[dict[str, Any]] = []
    for path in sorted(snapshot_root.rglob("*")):
        if (
            not path.is_file()
            or "__pycache__" in path.parts
            or path.suffix == ".pyc"
        ):
            continue
        relative = path.relative_to(snapshot_root).as_posix()
        files.append(
            {
                "path": relative,
                "sha256": _sha256_file(path),
                "size": path.stat().st_size,
            }
        )
    _require(files, "source code snapshot has no eligible files")
    return public.canonical_sha256(
        {
            "contract_version": "trace-validation-code-snapshot-v1",
            "files": files,
        }
    )


def _evaluation_harness_revision(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    _require(
        re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", normalized) is not None,
        "evaluation harness revision must be an immutable 40- or 64-hex revision",
    )
    return normalized


def _model_mappings(
    suite: Mapping[str, Any], public_model_ids: Mapping[str, str]
) -> tuple[public.ModelMapping, ...]:
    raw_models = suite.get("models")
    _require(isinstance(raw_models, list) and raw_models, "suite has no model roster")
    models: list[public.ModelMapping] = []
    for ordinal, raw in enumerate(raw_models):
        _require(isinstance(raw, Mapping), f"suite model {ordinal} is not an object")
        slug = str(raw.get("slug") or "")
        _require(slug in public_model_ids, f"suite model has no public id mapping: {slug!r}")
        repository_revision = str(raw.get("revision") or "")
        runtime_revision = str(raw.get("runtime_view_revision") or repository_revision)
        mapping = public.ModelMapping(
            source_model_id=slug,
            source_revision=runtime_revision,
            model_id=str(public_model_ids[slug]),
            model_revision=runtime_revision,
            display_name=str(raw.get("label") or slug),
            repository_id=str(raw.get("repo_id") or ""),
            repository_revision=repository_revision,
        )
        # Reuse the canonical plan parser as the strict id/revision validator.
        public._require_public_id(mapping.model_id, "public model id")
        public._require_revision(mapping.model_revision, "runtime model revision")
        public._require_repository_id(mapping.repository_id, "model repository id")
        public._require_revision(mapping.repository_revision, "repository revision")
        models.append(mapping)
    _require(
        len({model.model_id for model in models}) == len(models),
        "public model ids are not unique",
    )
    return tuple(models)


def _load_source(
    source_root: Path,
    suite_path: Path,
    *,
    public_model_ids: Mapping[str, str],
) -> LoadedSource:
    dataset_path = source_root / "dataset" / "manifest.json"
    dataset_file = _source_file(dataset_path)
    dataset = _load_json(dataset_path)
    _require(
        dataset.get("schema_version") == campaign_verify.DATASET_MANIFEST_SCHEMA,
        "source dataset manifest contract mismatch",
    )
    dataset_identity = dataset.get("dataset")
    rows = dataset.get("rows")
    _require(isinstance(dataset_identity, Mapping), "dataset identity is missing")
    _require(isinstance(rows, list) and rows, "dataset rows are missing")
    _require(
        int(dataset_identity.get("row_count", -1)) == len(rows),
        "dataset row count is inconsistent",
    )
    _require(
        [row.get("row_index") for row in rows if isinstance(row, Mapping)]
        == list(range(len(rows))),
        "dataset row indices are not exact and ordered",
    )

    suite_file = _source_file(suite_path)
    suite = _load_json(suite_path)
    models = _model_mappings(suite, public_model_ids)

    generation_rows: dict[str, list[dict[str, Any]]] = {}
    generation_metadata: dict[str, dict[str, Any]] = {}
    generation_files: dict[str, tuple[SourceFile, SourceFile]] = {}
    for model in models:
        model_root = source_root / "generation" / model.source_model_id
        response_path = model_root / "responses.jsonl"
        metadata_path = model_root / "run_metadata.json"
        response_file = _source_file(response_path)
        metadata_file = _source_file(metadata_path)
        response_rows = _load_jsonl(response_path)
        metadata = _load_json(metadata_path)
        _require(
            metadata.get("schema_version") == campaign_verify.GENERATION_RUN_SCHEMA,
            f"generation metadata contract mismatch for {model.source_model_id}",
        )
        _require(metadata.get("status") == "complete", f"generation is incomplete for {model.source_model_id}")
        _require(metadata.get("model_slug") == model.source_model_id, "generation model slug mismatch")
        _require(metadata.get("model_revision") == model.model_revision, "generation revision mismatch")
        _require(metadata.get("responses_sha256") == response_file.sha256, "generation response hash mismatch")
        _require(len(response_rows) == len(rows), f"generation row count mismatch for {model.source_model_id}")
        generation_rows[model.source_model_id] = response_rows
        generation_metadata[model.source_model_id] = metadata
        generation_files[model.source_model_id] = (metadata_file, response_file)

    scored_path = source_root / "scoring" / "scored_rows.jsonl"
    scored_file = _source_file(scored_path)
    score_summary_file = _source_file(source_root / "scoring" / "summary.json")
    scored_rows: dict[tuple[str, int], dict[str, Any]] = {}
    for row in _load_jsonl(scored_path):
        key = (str(row.get("model_slug") or ""), int(row.get("row_index", -1)))
        _require(key not in scored_rows, f"duplicate scored row: {key}")
        scored_rows[key] = row
    expected_scored = {
        (model.source_model_id, row_index)
        for model in models
        for row_index in range(len(rows))
    }
    _require(
        set(scored_rows) == expected_scored,
        "scored-row coverage does not exactly match model and dataset coverage",
    )
    for key, row in scored_rows.items():
        _require(
            row.get("schema_version") == "trace-validation-scored-row-v1"
            and row.get("scoring_contract_version")
            == campaign_verify.SCORING_CONTRACT_VERSION,
            f"scored-row contract mismatch: {key}",
        )

    judge_path = source_root / "judge" / "judge_results.jsonl"
    judge_file = _source_file(judge_path)
    judge_rows: dict[tuple[str, int], dict[str, Any]] = {}
    for row in _load_jsonl(judge_path):
        key = (str(row.get("model_slug") or ""), int(row.get("row_index", -1)))
        _require(key not in judge_rows, f"duplicate judge row: {key}")
        judge_rows[key] = row
    expected_judged = {
        key for key, row in scored_rows.items() if bool(row.get("judge_requested"))
    }
    _require(
        set(judge_rows) == expected_judged,
        "judge-result coverage does not exactly match judge-requested rows",
    )

    revision_path = source_root / "provenance" / "git_head.txt"
    producer_revision: str | None = None
    if revision_path.is_file():
        candidate = revision_path.read_text(encoding="utf-8").strip().lower()
        if len(candidate) == 40 and all(character in "0123456789abcdef" for character in candidate):
            producer_revision = candidate
    producer_code_sha256 = _code_snapshot_sha256(source_root / "code_snapshot")

    return LoadedSource(
        dataset_manifest=dataset,
        dataset_manifest_file=dataset_file,
        suite=suite,
        suite_file=suite_file,
        models=models,
        generation_rows=generation_rows,
        generation_metadata=generation_metadata,
        generation_files=generation_files,
        scored_rows=scored_rows,
        scored_file=scored_file,
        score_summary_file=score_summary_file,
        judge_rows=judge_rows,
        judge_file=judge_file,
        producer_revision=producer_revision,
        producer_code_sha256=producer_code_sha256,
    )


def _media_inputs(source: LoadedSource) -> dict[str, Any]:
    contracts: set[str] = set()
    values: set[str] = set()
    for model in source.models:
        metadata = source.generation_metadata[model.source_model_id]
        contract = {
            "media_transport": metadata.get("media_transport"),
            "mm_processor_kwargs": metadata.get("mm_processor_kwargs"),
            "source_storage": source.dataset_manifest.get("media"),
        }
        contracts.add(public.canonical_json(contract))
        kwargs = metadata.get("mm_processor_kwargs")
        _require(isinstance(kwargs, Mapping), "generation MM processor settings are missing")
        value = {
            "media_contract_version": public.MEDIA_CONTRACT_VERSION,
            "source_media_contract_sha256": public.canonical_sha256(contract),
            "media_transport": str(metadata.get("media_transport") or ""),
            "min_image_pixels": int(kwargs.get("min_pixels", -1)),
            "max_image_pixels": int(kwargs.get("max_pixels", -1)),
            "max_image_side": None,
            "image_jpeg_quality": None,
        }
        public._media_inputs_from_settings(value)
        values.add(public.canonical_json(value))
    _require(len(contracts) == 1 and len(values) == 1, "model media contracts differ")
    return json.loads(next(iter(values)))


def _usage_tokens(receipt: Mapping[str, Any]) -> tuple[int | None, int | None]:
    envelope = receipt.get("api_response")
    usage = envelope.get("usage") if isinstance(envelope, Mapping) else None
    if not isinstance(usage, Mapping):
        return None, None

    def optional_int(value: Any) -> int | None:
        if value is None:
            return None
        result = int(value)
        _require(result >= 0, "token count is negative")
        return result

    return optional_int(usage.get("prompt_tokens")), optional_int(usage.get("completion_tokens"))


def _common_response_rows(
    source: LoadedSource,
    model: public.ModelMapping,
    *,
    run_id: str,
    benchmark_id: str,
    seed: int,
    media_inputs: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]], dict[str, Any]]:
    dataset = source.dataset_manifest["dataset"]
    dataset_rows = source.dataset_manifest["rows"]
    dataset_sha = public._require_sha256(dataset["file_sha256"], "dataset file SHA-256")
    dataset_revision = public._dataset_revision(dataset_sha)
    metadata = source.generation_metadata[model.source_model_id]
    settings = public.normalize_generation_settings(
        metadata["decoding"], model_id=model.model_id, media_inputs=media_inputs
    )
    settings_json = public.canonical_json(settings)

    receipts: dict[int, dict[str, Any]] = {}
    for receipt in source.generation_rows[model.source_model_id]:
        row_index = int(receipt.get("row_index", -1))
        _require(row_index not in receipts, f"duplicate generation row {model.source_model_id}/{row_index}")
        receipts[row_index] = receipt
    _require(set(receipts) == set(range(len(dataset_rows))), f"generation coverage mismatch for {model.source_model_id}")

    public_rows: list[dict[str, Any]] = []
    by_ordinal: dict[int, dict[str, Any]] = {}
    for ordinal, raw_dataset_row in enumerate(dataset_rows):
        _require(isinstance(raw_dataset_row, Mapping), f"dataset row {ordinal} is invalid")
        dataset_row = dict(raw_dataset_row)
        receipt = receipts[ordinal]
        _require(receipt.get("schema_version") == campaign_verify.GENERATION_RECEIPT_SCHEMA, "generation receipt contract mismatch")
        _require(receipt.get("status") == "complete" and receipt.get("error") is None, "generation receipt is not successful")
        for name in ("instance_id", "task", "domain", "answer_type"):
            _require(receipt.get(name) == dataset_row.get(name), f"generation row {ordinal} differs on {name}")
        _require(receipt.get("model_slug") == model.source_model_id, "receipt model mismatch")

        request = receipt.get("request")
        _require(isinstance(request, Mapping), f"generation row {ordinal} has no request binding")
        ordered_media = [str(image["sha256"]) for image in dataset_row["images"]]
        _require(request.get("ordered_image_sha256") == ordered_media, f"generation row {ordinal} media hashes mismatch")
        prompt_digest = public.prompt_sha256(str(dataset_row["prompt_answer"]))
        _require(request.get("prompt_sha256") == prompt_digest, f"generation row {ordinal} prompt hash mismatch")

        response = receipt.get("raw_response")
        _require(isinstance(response, str), f"generation row {ordinal} response is not text")
        response_digest = public.response_sha256(response)
        _require(receipt.get("raw_response_sha256") == response_digest, f"generation row {ordinal} response hash mismatch")
        media_digest = public.media_set_sha256(ordered_media)
        source_row_digest = public.canonical_sha256(dataset_row)
        source_record_digest = public.source_record_sha256(source_row_digest, media_digest)
        request_digest = public.public_request_sha256_from_hashes(
            prompt_digest=prompt_digest,
            ordered_media_sha256=ordered_media,
            generation_settings=settings,
        )
        prompt_contract_digest = public.prompt_contract_sha256(
            dataset_sha256=dataset_sha,
            source_row_sha256=source_row_digest,
            source_record_digest=source_record_digest,
            media_digest=media_digest,
            prompt_digest=prompt_digest,
            request_digest=request_digest,
        )
        source_index = str(dataset_row["instance_id"])
        sample_id = public._sample_id(
            run_id=run_id,
            model_id=model.model_id,
            model_revision=model.model_revision,
            seed=seed,
            benchmark_id=benchmark_id,
            source_index=source_index,
            source_ordinal=ordinal,
            source_row_sha256=source_row_digest,
        )
        response_id = public._response_id(sample_id, response_digest)
        prompt_tokens, completion_tokens = _usage_tokens(receipt)
        row = {
            "schema_version": public.SCHEMA_VERSION,
            "run_id": run_id,
            "model_id": model.model_id,
            "model_revision": model.model_revision,
            "seed": seed,
            "benchmark_id": benchmark_id,
            "dataset_split": str(dataset["split"]),
            "dataset_revision": dataset_revision,
            "sample_id": sample_id,
            "response_id": response_id,
            "source_index": source_index,
            "source_ordinal": ordinal,
            "dataset_sha256": dataset_sha,
            "source_row_sha256": source_row_digest,
            "source_record_sha256": source_record_digest,
            "media_set_sha256": media_digest,
            "ordered_media_sha256": ordered_media,
            "prompt_sha256": prompt_digest,
            "request_sha256": request_digest,
            "prompt_contract_sha256": prompt_contract_digest,
            "response_sha256": response_digest,
            "contract_version": public.RESPONSE_CONTRACT_VERSION,
            "response_text": response,
            "finish_reason": receipt.get("finish_reason"),
            "generation_settings_json": settings_json,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }
        public_rows.append(row)
        by_ordinal[ordinal] = row
    return public_rows, by_ordinal, settings


def _unique_candidates(extraction: Mapping[str, Any]) -> list[Any]:
    candidates: list[Any] = []
    seen: set[str] = set()
    provenance = extraction.get("candidate_provenance")
    if isinstance(provenance, list):
        for item in provenance:
            if not isinstance(item, Mapping) or item.get("accepted") is not True:
                continue
            value = item.get("typed_candidate")
            if value is None:
                continue
            key = public.canonical_json(value)
            if key not in seen:
                seen.add(key)
                candidates.append(value)
    value = extraction.get("typed_candidate")
    if value is not None and public.canonical_json(value) not in seen:
        candidates.append(value)
    return candidates


def _extraction_row(
    source: LoadedSource,
    model: public.ModelMapping,
    ordinal: int,
    response: Mapping[str, Any],
) -> dict[str, Any]:
    key = (model.source_model_id, ordinal)
    scored = source.scored_rows.get(key)
    _require(scored is not None, f"missing scored row: {key}")
    _require(scored.get("instance_id") == response["source_index"], f"scored row instance mismatch: {key}")
    _require(scored.get("raw_response_sha256") == response["response_sha256"], f"scored row response mismatch: {key}")
    deterministic = scored.get("deterministic_extraction")
    _require(isinstance(deterministic, Mapping), f"scored row has no deterministic extraction: {key}")

    used_judge = bool(scored.get("judge_requested"))
    judge = source.judge_rows.get(key)
    if used_judge:
        _require(judge is not None, f"judge-requested row has no judge result: {key}")
        _require(judge.get("raw_response_sha256") == response["response_sha256"], f"judge response mismatch: {key}")
        _require(
            judge.get("judge_status") == scored.get("judge_status")
            and judge.get("answer") == scored.get("judge_answer"),
            f"judge result and final scoring decision differ: {key}",
        )
        attempts = judge.get("attempts")
        _require(isinstance(attempts, list) and attempts, f"judge result has no attempts: {key}")
        final_attempt = attempts[-1]
        _require(isinstance(final_attempt, Mapping), f"judge final attempt is invalid: {key}")
        judge_output = final_attempt.get("raw_output")
        _require(isinstance(judge_output, str) and judge_output, f"judge output is empty: {key}")
        retry_count = max(0, len(attempts) - 1)
    else:
        _require(judge is None, f"deterministic row unexpectedly has a judge result: {key}")
        judge_output = None
        retry_count = 0

    deterministic_found = deterministic.get("status") == "found"
    if deterministic_found:
        value = deterministic.get("typed_candidate")
        candidates = _unique_candidates(deterministic)
        status = "resolved"
        method = "deterministic_parser"
    elif scored.get("judge_status") == "ok":
        value = scored.get("judge_answer")
        candidates = [value]
        status = "resolved"
        method = "judge"
    else:
        value = None
        candidates = []
        status = "ambiguous" if scored.get("judge_status") == "ambiguous" else "invalid"
        method = "judge"

    material = {
        "contract_version": public.EXTRACTION_CONTRACT_VERSION,
        "sample_id": response["sample_id"],
        "status": status,
        "value": value,
        "candidates": candidates,
    }
    common = {field.name: response[field.name] for field in public.COMMON_SAMPLE_FIELDS}
    return {
        **common,
        "contract_version": public.EXTRACTION_CONTRACT_VERSION,
        "extraction_status": status,
        "extraction_value_type": public._json_value_type(value),
        "extraction_value_json": public.canonical_json(value),
        "extraction_candidates_json": public.canonical_json(candidates),
        "extraction_sha256": public.canonical_sha256(material),
        "extraction_method": method,
        "used_judge": used_judge,
        "judge_model_id": source.suite["judge"]["repo_id"] if used_judge else None,
        "judge_model_revision": source.suite["judge"]["revision"] if used_judge else None,
        "judge_output": judge_output,
        "judge_output_sha256": (
            public.sha256_bytes(judge_output.encode("utf-8"))
            if judge_output is not None
            else None
        ),
        "retry_count": retry_count,
    }


def _score_rows(
    source: LoadedSource,
    model: public.ModelMapping,
    responses: Mapping[int, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    first = responses[0]
    identity = {
        "run_id": first["run_id"],
        "model_id": model.model_id,
        "model_revision": model.model_revision,
        "seed": first["seed"],
        "benchmark_id": first["benchmark_id"],
        "dataset_split": first["dataset_split"],
    }
    scorer_id = f"{first['benchmark_id']}-primary-v1"
    rows: list[dict[str, Any]] = []
    correct_values: list[int] = []
    for ordinal, response in sorted(responses.items()):
        scored = source.scored_rows[(model.source_model_id, ordinal)]
        correct = int(scored.get("combined_semantic_correct", -1))
        _require(correct in {0, 1}, f"invalid primary score for {model.source_model_id}/{ordinal}")
        correct_values.append(correct)
        sample_id = response["sample_id"]
        rows.append(
            {
                "schema_version": public.SCHEMA_VERSION,
                **identity,
                "dataset_revision": response["dataset_revision"],
                "score_id": public._score_id(identity, scope="row", sample_id=sample_id),
                "score_scope": "row",
                "sample_id": sample_id,
                "response_id": response["response_id"],
                "source_index": response["source_index"],
                "source_ordinal": response["source_ordinal"],
                "dataset_sha256": response["dataset_sha256"],
                "source_row_sha256": response["source_row_sha256"],
                "source_record_sha256": response["source_record_sha256"],
                "media_set_sha256": response["media_set_sha256"],
                "prompt_sha256": response["prompt_sha256"],
                "request_sha256": response["request_sha256"],
                "prompt_contract_sha256": response["prompt_contract_sha256"],
                "response_sha256": response["response_sha256"],
                "contract_version": public.SCORE_CONTRACT_VERSION,
                "scorer_id": scorer_id,
                "metric_id": "primary",
                "score_unit": "fraction",
                "score_value": float(correct),
                "score_value_json": public.canonical_json(correct),
                "excluded": False,
                "evaluated_rows": None,
            }
        )
    aggregate = math.fsum(correct_values) * 100.0 / len(correct_values)
    aggregate_row = {
        "schema_version": public.SCHEMA_VERSION,
        **identity,
        "dataset_revision": first["dataset_revision"],
        "score_id": public._score_id(identity, scope="aggregate", sample_id=None),
        "score_scope": "aggregate",
        "sample_id": None,
        "response_id": None,
        "source_index": None,
        "source_ordinal": None,
        "dataset_sha256": first["dataset_sha256"],
        "source_row_sha256": None,
        "source_record_sha256": None,
        "media_set_sha256": None,
        "prompt_sha256": None,
        "request_sha256": None,
        "prompt_contract_sha256": None,
        "response_sha256": None,
        "contract_version": public.SCORE_CONTRACT_VERSION,
        "scorer_id": scorer_id,
        "metric_id": "primary",
        "score_unit": "percent",
        "score_value": aggregate,
        "score_value_json": public.canonical_json(aggregate),
        "excluded": False,
        "evaluated_rows": len(correct_values),
    }
    rows.append(aggregate_row)
    return rows, aggregate_row


def _provenance(
    source: LoadedSource,
    model: public.ModelMapping,
    config_name: str,
    dataset_sha256: str,
    evaluation_harness_revision: str | None,
) -> dict[str, Any]:
    if config_name == "responses":
        manifest_file, part_file = source.generation_files[model.source_model_id]
        contract = campaign_verify.GENERATION_RECEIPT_SCHEMA
    elif config_name == "extractions":
        manifest_file, part_file = source.score_summary_file, source.scored_file
        contract = campaign_verify.ANSWER_EXTRACTION_VERSION
    else:
        manifest_file, part_file = source.score_summary_file, source.scored_file
        contract = campaign_verify.SCORING_CONTRACT_VERSION
    return {
        "source_archive_manifest_sha256": manifest_file.sha256,
        "source_archive_manifest_size": manifest_file.size,
        "source_archive_part_sha256": part_file.sha256,
        "source_archive_part_size": part_file.size,
        "source_payload_sha256": part_file.sha256,
        "source_contract_sha256": public.sha256_bytes(contract.encode("utf-8")),
        "campaign_config_sha256": source.suite_file.sha256,
        "producer_code_revision": source.producer_revision,
        "evaluation_harness_revision": evaluation_harness_revision,
        "producer_code_sha256": source.producer_code_sha256,
        "dataset_sha256": dataset_sha256,
    }


def _source_binding_records(
    source: LoadedSource,
    *,
    benchmark_id: str,
    seed: int,
    evaluation_harness_revision: str | None,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for config_name in public.CONFIG_NAMES:
        for model in source.models:
            provenance = _provenance(
                source,
                model,
                config_name,
                str(source.dataset_manifest["dataset"]["file_sha256"]),
                evaluation_harness_revision,
            )
            records.append(
                {
                    "config_name": config_name,
                    "model_id": model.model_id,
                    "seed": seed,
                    "benchmark_id": benchmark_id,
                    "manifest": {
                        "sha256": provenance["source_archive_manifest_sha256"],
                        "size": provenance["source_archive_manifest_size"],
                    },
                    "parquet": {
                        "sha256": provenance["source_archive_part_sha256"],
                        "size": provenance["source_archive_part_size"],
                    },
                }
            )
    return records


def _atomic_publish(temporary: Path, destination: Path, expected_artifacts: int) -> public.VerifiedPublicExport:
    public.load_and_verify_public_export(temporary, expected_artifacts=expected_artifacts)
    if destination.exists():
        existing = public.load_and_verify_public_export(
            destination, expected_artifacts=expected_artifacts
        )
        _require(
            public._tree_files(temporary) == public._tree_files(destination),
            "existing canonical export is valid but differs from the deterministic rebuild",
        )
        shutil.rmtree(temporary)
        return existing
    temporary.replace(destination)
    return public.load_and_verify_public_export(
        destination, expected_artifacts=expected_artifacts
    )


def _build_verified_export(
    source_root: Path,
    suite_path: Path,
    output_root: Path,
    *,
    run_id: str,
    suite_id: str,
    benchmark_id: str,
    seed: int,
    public_model_ids: Mapping[str, str],
    verification_report: Mapping[str, Any] | None = None,
    private_plan_output: Path | None = None,
    evaluation_harness_revision: str | None = None,
) -> public.VerifiedPublicExport:
    source = _load_source(
        source_root.resolve(), suite_path.resolve(), public_model_ids=public_model_ids
    )
    media_inputs = _media_inputs(source)
    harness_revision = _evaluation_harness_revision(evaluation_harness_revision)
    source_bindings = _source_binding_records(
        source,
        benchmark_id=benchmark_id,
        seed=seed,
        evaluation_harness_revision=harness_revision,
    )
    slice_set_sha = public.source_slice_set_sha256(source_bindings)
    selection_sha = public.canonical_sha256(
        {
            "contract_version": SOURCE_CONTRACT_VERSION,
            "suite_sha256": source.suite_file.sha256,
            "dataset_manifest_sha256": source.dataset_manifest_file.sha256,
            "source_slice_set_sha256": slice_set_sha,
            "run_id": run_id,
            "suite_id": suite_id,
            "benchmark_id": benchmark_id,
            "seed": seed,
            "models": [model.model_id for model in source.models],
        }
    )
    judge = public.JudgeMapping(
        source_model_id=str(source.suite["judge"]["served_model_name"]),
        model_id=str(source.suite["judge"]["repo_id"]),
        model_revision=str(source.suite["judge"]["revision"]),
    )
    plan = public.ExportPlan(
        source_run_id=source_root.name,
        source_selection_sha256=selection_sha,
        source_slice_set_sha256=slice_set_sha,
        run_id=run_id,
        suite_id=suite_id,
        benchmarks=(benchmark_id,),
        categories=(("TRACE IID validation", (benchmark_id,)),),
        seeds=(seed,),
        models=source.models,
        judge=judge,
    )

    destination = output_root.expanduser().resolve()
    private_plan_path = (
        private_plan_output.expanduser().resolve()
        if private_plan_output is not None
        else None
    )
    if private_plan_path is not None:
        _require(
            private_plan_path != destination
            and destination not in private_plan_path.parents
            and private_plan_path not in destination.parents,
            "private export plan must be outside the canonical public tree",
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=".trace-validation-canonical-", dir=destination.parent)
    )
    try:
        artifacts: list[dict[str, Any]] = []
        aggregates: list[dict[str, Any]] = []
        generation_settings: set[str] = set()
        config_stats = {
            config: {"rows": 0, "parts": 0, "placeholder_records_removed": 0}
            for config in public.CONFIG_NAMES
        }
        for model in source.models:
            response_rows, responses, settings = _common_response_rows(
                source,
                model,
                run_id=run_id,
                benchmark_id=benchmark_id,
                seed=seed,
                media_inputs=media_inputs,
            )
            generation_settings.add(public.canonical_json(settings))
            extraction_rows = [
                _extraction_row(source, model, ordinal, responses[ordinal])
                for ordinal in sorted(responses)
            ]
            score_rows, aggregate_row = _score_rows(source, model, responses)
            aggregates.append(aggregate_row)
            rows_by_config = {
                "responses": response_rows,
                "extractions": extraction_rows,
                "scores": score_rows,
            }
            for config_name in public.CONFIG_NAMES:
                rows = rows_by_config[config_name]
                identity = public._part_identity(rows[0])
                parquet = public._write_public_parquet(
                    temporary,
                    config_name=config_name,
                    identity=identity,
                    rows=rows,
                    private_run_id=source_root.name,
                )
                part_manifest = public._write_part_manifest(
                    temporary,
                    config_name=config_name,
                    identity=identity,
                    rows=len(rows),
                    parquet_path=parquet[0],
                    parquet_sha256=parquet[1],
                    parquet_size=parquet[2],
                    provenance=_provenance(
                        source,
                        model,
                        config_name,
                        str(source.dataset_manifest["dataset"]["file_sha256"]),
                        harness_revision,
                    ),
                    scoring_scope=(
                        "row_and_aggregate" if config_name == "scores" else None
                    ),
                    evaluated_rows=(len(responses) if config_name == "scores" else None),
                )
                artifacts.append(
                    public._artifact_entry(
                        config_name=config_name,
                        identity=identity,
                        rows=len(rows),
                        parquet=parquet,
                        part_manifest=part_manifest,
                        scoring_scope=(
                            "row_and_aggregate" if config_name == "scores" else None
                        ),
                        evaluated_rows=(len(responses) if config_name == "scores" else None),
                    )
                )
                config_stats[config_name]["rows"] += len(rows)
                config_stats[config_name]["parts"] += 1

        artifacts.sort(
            key=lambda item: (
                public.CONFIG_NAMES.index(item["config_name"]),
                item["model_id"],
            )
        )
        metadata_files: list[dict[str, Any]] = []
        metadata_files.append(
            public._metadata_file(
                temporary,
                f"metadata/suites/{suite_id}.json",
                {
                    "schema_version": public.SUITE_METADATA_VERSION,
                    "suite_id": suite_id,
                    "benchmark_count": 1,
                    "benchmark_ids": [benchmark_id],
                    "categories": [
                        {
                            "category_id": public._slug("TRACE IID validation"),
                            "category_name": "TRACE IID validation",
                            "benchmark_ids": [benchmark_id],
                        }
                    ],
                },
            )
        )
        for model in source.models:
            metadata_files.append(
                public._metadata_file(
                    temporary,
                    f"metadata/models/{model.model_id}.json",
                    {
                        "schema_version": public.MODEL_METADATA_VERSION,
                        "model_id": model.model_id,
                        "model_revision": model.model_revision,
                        "display_name": model.display_name,
                        "repository_id": model.repository_id,
                        "repository_revision": model.repository_revision,
                    },
                )
            )
        run_metadata: dict[str, Any] = {
            "schema_version": public.RUN_METADATA_VERSION,
            "run_id": run_id,
            "suite_id": suite_id,
            "model_ids": [model.model_id for model in source.models],
            "seeds": [seed],
            "generation_settings": [
                json.loads(item) for item in sorted(generation_settings)
            ],
            "media_inputs": dict(media_inputs),
            "judge_model": {
                "model_id": judge.model_id,
                "model_revision": judge.model_revision,
            },
            "source_selection_sha256": selection_sha,
            "source_slice_set_sha256": slice_set_sha,
            "prompt_reconstruction": {
                "verification_supported": True,
                "dataset_reconstruction_status": "external_release_gate",
            },
            "evaluation_contracts": {
                "deterministic_extraction": campaign_verify.ANSWER_EXTRACTION_VERSION,
                "judge_extraction": campaign_verify.JUDGE_CONTRACT_VERSION,
                "scoring": campaign_verify.SCORING_CONTRACT_VERSION,
            },
            "evaluation_harness_revision": harness_revision,
            "producer_code_revision": source.producer_revision,
            "producer_code_sha256": source.producer_code_sha256,
        }
        if verification_report is not None:
            run_metadata["campaign_verification"] = dict(verification_report)
        metadata_files.append(
            public._metadata_file(
                temporary, f"metadata/runs/{run_id}.json", run_metadata
            )
        )
        metadata_files.append(
            public._metadata_file(
                temporary,
                "metadata/results/benchmark_scores.json",
                public.build_results(plan, aggregates),
            )
        )

        readme_path = temporary / "README.md"
        readme_path.write_text(public._readme(plan, config_stats), encoding="utf-8")
        release_files = [
            {
                "path": "README.md",
                "sha256": _sha256_file(readme_path),
                "size": readme_path.stat().st_size,
            }
        ]
        manifest = {
            "schema_version": public.EXPORT_MANIFEST_VERSION,
            "suite_id": suite_id,
            "run_ids": [run_id],
            "neutralized": True,
            "source_selection_sha256": selection_sha,
            "source_slice_set_sha256": slice_set_sha,
            "configs": [
                {
                    "config_name": config,
                    "contract_version": public.PUBLIC_CONTRACTS[config],
                    **config_stats[config],
                }
                for config in public.CONFIG_NAMES
            ],
            "artifacts": artifacts,
            "metadata_files": sorted(metadata_files, key=lambda item: item["path"]),
            "release_files": release_files,
        }
        public._assert_no_internal_markers(
            manifest, dynamic_markers=(source_root.name,)
        )
        public._write_json(temporary / "metadata" / "manifest.json", manifest)
        public.load_and_verify_public_export(
            temporary, expected_artifacts=len(source.models) * 3
        )
        if private_plan_path is not None:
            plan_document = public._export_plan_document(
                source_run_id=plan.source_run_id,
                source_selection_sha256=plan.source_selection_sha256,
                source_slice_set_sha256=plan.source_slice_set_sha256,
                public_run_id=plan.run_id,
                suite={
                    "suite_id": suite_id,
                    "benchmarks": [benchmark_id],
                    "categories": {"TRACE IID validation": [benchmark_id]},
                },
                seeds=[seed],
                models=source.models,
                judge=judge,
            )
            _require(
                public.ExportPlan.from_mapping(plan_document) == plan,
                "private export plan does not round-trip to the built public plan",
            )
            public._write_private_plan(private_plan_path, plan_document)
        return _atomic_publish(temporary, destination, len(source.models) * 3)
    except BaseException:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise


def export_iid_validation(
    *,
    source_root: Path = DEFAULT_SOURCE_ROOT,
    suite_path: Path = campaign_verify.DEFAULT_SUITE,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    private_plan_output: Path = DEFAULT_PRIVATE_PLAN_OUTPUT,
    evaluation_harness_revision: str | None = None,
    verified_dataset_manifest: Path = campaign_verify.DEFAULT_DATASET_MANIFEST,
    verified_dataset_parquet: Path = campaign_verify.DEFAULT_DATASET_PARQUET,
    verified_generation_root: Path = campaign_verify.DEFAULT_CAMPAIGN_ROOT / "generation",
    verified_score_dir: Path = campaign_verify.DEFAULT_CAMPAIGN_ROOT / "scoring" / "final",
    verified_judge_results: Path = campaign_verify.DEFAULT_CAMPAIGN_ROOT / "judge" / "judge_results.jsonl",
) -> public.VerifiedPublicExport:
    """Full-verify production, attest the release copy, then build the public run."""

    # This gate intentionally runs before the release bundle is opened. The copied
    # bundle is relocatable for publication, while the original verifier validates
    # receipts, media, source parquet, and absolute production provenance in place.
    report = campaign_verify.verify_full_phase(
        suite_path=suite_path,
        dataset_manifest=verified_dataset_manifest,
        dataset_parquet=verified_dataset_parquet,
        generation_root=verified_generation_root,
        score_dir=verified_score_dir,
        judge_results=verified_judge_results,
    )
    _require(report.get("status") == "ok" and report.get("phase") == "full", "full campaign verification did not pass")
    _require(int(report.get("models", -1)) == EXPECTED_MODELS, "verified model count mismatch")
    _require(int(report.get("rows_per_model", -1)) == EXPECTED_ROWS, "verified row count mismatch")
    _attest_release_bundle(
        source_root,
        verified_dataset_manifest=verified_dataset_manifest,
        verified_generation_root=verified_generation_root,
        verified_score_dir=verified_score_dir,
        verified_judge_results=verified_judge_results,
    )
    public_report = {
        key: report[key]
        for key in (
            "phase",
            "status",
            "suite_sha256",
            "dataset_manifest_sha256",
            "models",
            "rows_per_model",
            "generation_rows",
            "scored_rows",
            "judge_pending_rows",
            "judge_result_rows",
            "unresolved_rows",
            "summary_sha256",
        )
    }
    return _build_verified_export(
        source_root,
        suite_path,
        output_root,
        run_id=RUN_ID,
        suite_id=SUITE_ID,
        benchmark_id=BENCHMARK_ID,
        seed=SEED,
        public_model_ids=PUBLIC_MODEL_IDS,
        verification_report=public_report,
        private_plan_output=private_plan_output,
        evaluation_harness_revision=evaluation_harness_revision,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--suite", type=Path, default=campaign_verify.DEFAULT_SUITE)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument(
        "--private-plan-output", type=Path, default=DEFAULT_PRIVATE_PLAN_OUTPUT
    )
    parser.add_argument(
        "--evaluation-harness-revision",
        help="immutable Git/content revision containing this canonical exporter",
    )
    parser.add_argument(
        "--verified-dataset-manifest",
        type=Path,
        default=campaign_verify.DEFAULT_DATASET_MANIFEST,
    )
    parser.add_argument(
        "--verified-dataset-parquet",
        type=Path,
        default=campaign_verify.DEFAULT_DATASET_PARQUET,
    )
    parser.add_argument(
        "--verified-generation-root",
        type=Path,
        default=campaign_verify.DEFAULT_CAMPAIGN_ROOT / "generation",
    )
    parser.add_argument(
        "--verified-score-dir",
        type=Path,
        default=campaign_verify.DEFAULT_CAMPAIGN_ROOT / "scoring" / "final",
    )
    parser.add_argument(
        "--verified-judge-results",
        type=Path,
        default=campaign_verify.DEFAULT_CAMPAIGN_ROOT / "judge" / "judge_results.jsonl",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = export_iid_validation(
        source_root=args.source_root,
        suite_path=args.suite,
        output_root=args.output_root,
        private_plan_output=args.private_plan_output,
        evaluation_harness_revision=args.evaluation_harness_revision,
        verified_dataset_manifest=args.verified_dataset_manifest,
        verified_dataset_parquet=args.verified_dataset_parquet,
        verified_generation_root=args.verified_generation_root,
        verified_score_dir=args.verified_score_dir,
        verified_judge_results=args.verified_judge_results,
    )
    print(
        public.canonical_json(
            {
                "verified": True,
                "root": str(args.output_root.expanduser().resolve()),
                "private_plan": str(args.private_plan_output.expanduser().resolve()),
                "private_plan_sha256": _sha256_file(args.private_plan_output),
                "manifest_sha256": result.manifest_sha256,
                "files": len(result.files),
                "artifacts": len(result.manifest["artifacts"]),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
