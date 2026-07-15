#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import inspect
import io
import json
import os
import queue
import shutil
import sys
import threading
import time
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from PIL import Image
from tqdm import tqdm

try:
    from PIL import ImageFile

    ImageFile.LOAD_TRUNCATED_IMAGES = True
except Exception:
    pass

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from benchmark_queue_lib import (  # noqa: E402
    BENCHMARK_RUN_SETS,
    DEFAULT_QUEUE_ROOT,
    REPO_ROOT as LIB_REPO_ROOT,
    TRACE_CANDIDATE37_200_BENCHMARKS,
    TRACE_GROUNDING_BENCHMARKS,
    TRACE_GROUNDING_SUBSET_ROOT,
    BenchmarkSpec,
    benchmark_specs_for_run_set,
    build_vlmeval_dataset,
    effective_generation_batch_size,
    filter_benchmark_specs,
    json_default,
    materialize_grounding_benchmark_files,
    run_dir,
    write_json,
)
from run_external_benchmark_generation_queue import (  # noqa: E402
    _apply_subset_frame,
    _apply_subset_rows,
    _import_vlmeval_runner,
    _limit_frame,
    _row_hash,
    _subset_entries,
    _subset_manifest_path,
)


@dataclass(frozen=True)
class RowJob:
    spec: BenchmarkSpec
    row: dict[str, Any]
    rank: int
    row_key: str
    output_dir: Path
    result_path: Path
    kind: str
    mirror_result_path: Path | None = None
    attempted_endpoints: tuple[str, ...] = ()
    attempt_count: int = 0


class PermanentAPIError(RuntimeError):
    """A request error caused by the row payload rather than endpoint health."""

    def __init__(self, endpoint: str, status_code: int, detail: str):
        self.endpoint = endpoint
        self.status_code = int(status_code)
        self.detail = detail
        super().__init__(f"{endpoint} returned HTTP {status_code}: {detail}")


class RetryableAPIError(RuntimeError):
    """A transport or server error that may succeed on another endpoint."""

    def __init__(self, endpoint: str, detail: str, *, affects_health: bool = True):
        self.endpoint = endpoint
        self.detail = detail
        self.affects_health = bool(affects_health)
        super().__init__(f"{endpoint} failed: {detail}")


class EndpointHealth:
    """Track endpoint failures and quarantine unhealthy workers for this run."""

    def __init__(self, endpoints: list[str], failure_threshold: int):
        self.endpoints = tuple(endpoints)
        self.failure_threshold = max(1, int(failure_threshold))
        self.failure_streak = {endpoint: 0 for endpoint in self.endpoints}
        self.failure_count = {endpoint: 0 for endpoint in self.endpoints}
        self.disabled: set[str] = set()
        self.lock = threading.Lock()

    def is_disabled(self, endpoint: str) -> bool:
        with self.lock:
            return endpoint in self.disabled

    def should_defer(self, endpoint: str, attempted_endpoints: tuple[str, ...]) -> bool:
        attempted = set(attempted_endpoints)
        if endpoint not in attempted:
            return False
        with self.lock:
            return any(candidate not in self.disabled and candidate not in attempted for candidate in self.endpoints)

    def record_success(self, endpoint: str) -> None:
        with self.lock:
            self.failure_streak[endpoint] = 0

    def record_failure(self, endpoint: str) -> bool:
        """Record a retriable failure and return whether the endpoint was newly disabled."""

        with self.lock:
            self.failure_count[endpoint] += 1
            self.failure_streak[endpoint] += 1
            if self.failure_streak[endpoint] < self.failure_threshold:
                return False
            # Keep one endpoint available so queued rows terminate with explicit
            # errors instead of leaving queue.join() blocked when the whole pool
            # is unavailable.
            if endpoint in self.disabled or len(self.disabled) >= len(self.endpoints) - 1:
                return False
            self.disabled.add(endpoint)
            return True

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                "failure_threshold": self.failure_threshold,
                "disabled_endpoints": sorted(self.disabled),
                "failure_count": dict(self.failure_count),
            }


class DatasetHandle:
    def __init__(self, spec: BenchmarkSpec, dataset: Any = None, rows: list[dict[str, Any]] | None = None):
        self.spec = spec
        self.dataset = dataset
        self.rows = rows
        self.lock = threading.Lock()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _safe_result_name(index: Any) -> str:
    text = str(index)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in text)[:80]
    return f"{safe}.{digest}.json"


def _row_key(row: dict[str, Any], rank: int) -> str:
    row_hash = _row_hash(row)[:16]
    return f"{int(rank):08d}:{row.get('index')}:{row_hash}"


def _safe_result_name_for_row(row: dict[str, Any], rank: int) -> str:
    index = str(row.get("index"))
    safe_index = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in index)[:64]
    digest = hashlib.sha256(_row_key(row, rank).encode("utf-8")).hexdigest()[:16]
    return f"{int(rank):08d}.{safe_index}.{digest}.json"


def _atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}.{threading.get_ident()}")
    tmp.write_bytes(payload)
    tmp.replace(path)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    encoded = (json.dumps(payload, ensure_ascii=False, default=json_default) + "\n").encode("utf-8")
    _atomic_write_bytes(path, encoded)


def _write_job_result(job: RowJob, payload: dict[str, Any]) -> None:
    """Atomically write the canonical result and its optional persistent mirror."""

    encoded = (json.dumps(payload, ensure_ascii=False, default=json_default) + "\n").encode("utf-8")
    _atomic_write_bytes(job.result_path, encoded)
    if job.mirror_result_path is not None:
        _atomic_write_bytes(job.mirror_result_path, encoded)


def _persist_worker_result(
    job: RowJob,
    payload: dict[str, Any],
    errors: list[dict[str, Any]],
    error_lock: threading.Lock,
) -> None:
    """Persist a final row result and surface storage failures in the suite result."""

    try:
        _write_job_result(job, payload)
    except OSError as exc:
        error = {
            "benchmark_key": job.spec.key,
            "index": str(job.row.get("index")),
            "row_key": job.row_key,
            "error": f"result persistence failed: {exc!r}",
            "result_path": str(job.result_path),
            "mirror_result_path": str(job.mirror_result_path) if job.mirror_result_path is not None else None,
        }
        with error_lock:
            errors.append(error)
        print(f"[api-generate:persistence-error] row_key={job.row_key} error={exc!r}")


def _load_image(value: Any) -> Image.Image:
    if isinstance(value, Image.Image):
        return value.convert("RGB")
    if isinstance(value, (str, Path)):
        text = str(value)
        if text.startswith("data:image/"):
            _, data = text.split(",", 1)
            return Image.open(io.BytesIO(base64.b64decode(data))).convert("RGB")
        return Image.open(value).convert("RGB")
    if hasattr(value, "convert"):
        return value.convert("RGB")
    raise TypeError(f"Unsupported image value type: {type(value)!r}")


def _image_to_data_url(
    value: Any,
    *,
    image_format: str = "JPEG",
    quality: int = 85,
    max_pixels: int = 1_000_000,
    max_side: int = 1280,
) -> str:
    image = _load_image(value)
    width, height = image.size
    scales = [1.0]
    if max_pixels > 0 and width * height > max_pixels:
        scales.append((max_pixels / float(width * height)) ** 0.5)
    if max_side > 0 and max(width, height) > max_side:
        scales.append(max_side / float(max(width, height)))
    scale = min(scales)
    if scale < 1.0:
        image = image.resize(
            (max(1, int(width * scale)), max(1, int(height * scale))),
            Image.Resampling.LANCZOS,
        )
    buf = io.BytesIO()
    fmt = image_format.upper()
    if fmt in {"JPG", "JPEG"}:
        image = image.convert("RGB")
        mime = "image/jpeg"
        image.save(buf, format="JPEG", quality=quality)
    elif fmt == "PNG":
        mime = "image/png"
        image.save(buf, format="PNG")
    else:
        raise ValueError(f"Unsupported image format: {image_format}")
    return f"data:{mime};base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"


def _vlmeval_messages(args: argparse.Namespace, handle: DatasetHandle, row: dict[str, Any]) -> list[dict[str, Any]]:
    runner, _ = _import_vlmeval_runner()
    row_series = pd.Series(row)
    # Some VLMEvalKit datasets materialize cached images in build_prompt. Keep that
    # per-dataset call serialized while allowing image encoding/API calls to run in parallel.
    with handle.lock:
        parameters = inspect.signature(handle.dataset.build_prompt).parameters
        if "video_llm" in parameters:
            struct = handle.dataset.build_prompt(row_series, handle.spec.video_llm)
        else:
            struct = runner.build_prompt_for_runner(handle.dataset, row_series, video_llm=handle.spec.video_llm)
    content: list[dict[str, Any]] = []
    for item in struct:
        typ = item.get("type")
        value = item.get("value")
        if typ == "image":
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": _image_to_data_url(
                            value,
                            quality=int(args.image_jpeg_quality),
                            max_pixels=int(args.max_image_pixels),
                            max_side=int(args.max_image_side),
                        )
                    },
                }
            )
        elif typ == "video":
            raise NotImplementedError(f"OpenAI endpoint video prompts are not supported for {handle.spec.key}")
        else:
            text = "" if value is None else str(value)
            if text:
                content.append({"type": "text", "text": text})
    return [{"role": "user", "content": content or [{"type": "text", "text": ""}]}]


def _chartmuseum_messages(args: argparse.Namespace, row: dict[str, Any]) -> list[dict[str, Any]]:
    image_path = row.get("image_path") or row.get("image")
    content: list[dict[str, Any]] = []
    if image_path:
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": _image_to_data_url(
                        image_path,
                        quality=int(args.image_jpeg_quality),
                        max_pixels=int(args.max_image_pixels),
                        max_side=int(args.max_image_side),
                    )
                },
            }
        )
    content.append({"type": "text", "text": str(row.get("question", ""))})
    return [{"role": "user", "content": content}]


def _completion_url(endpoint: str) -> str:
    endpoint = endpoint.rstrip("/")
    if endpoint.endswith("/v1"):
        return endpoint + "/chat/completions"
    return endpoint + "/v1/chat/completions"


def _call_endpoint(args: argparse.Namespace, endpoint: str, messages: list[dict[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": args.api_model,
        "messages": messages,
        "temperature": float(args.temperature),
        "top_p": float(args.top_p),
        "max_tokens": int(args.max_tokens),
        "presence_penalty": float(args.presence_penalty),
        "stream": False,
    }
    if args.top_k is not None:
        payload["top_k"] = int(args.top_k)
    if args.repetition_penalty is not None:
        payload["repetition_penalty"] = float(args.repetition_penalty)
    if args.seed is not None:
        payload["seed"] = int(args.seed)
    headers = {"Authorization": f"Bearer {args.api_key}"}
    try:
        response = requests.post(
            _completion_url(endpoint),
            json=payload,
            headers=headers,
            timeout=float(args.api_timeout),
        )
    except requests.RequestException as exc:
        raise RetryableAPIError(endpoint, repr(exc)) from exc

    detail = response.text[:2000].strip()
    if 400 <= response.status_code < 500 and response.status_code != 429:
        raise PermanentAPIError(endpoint, response.status_code, detail)
    if response.status_code >= 400:
        raise RetryableAPIError(
            endpoint,
            f"HTTP {response.status_code}: {detail}",
            affects_health=response.status_code != 429,
        )
    try:
        return response.json()
    except ValueError as exc:
        raise RetryableAPIError(endpoint, f"invalid JSON response: {detail}") from exc


def _result_from_response(job: RowJob, response: dict[str, Any], endpoint: str) -> dict[str, Any]:
    choice = response.get("choices", [{}])[0]
    message = choice.get("message") or {}
    usage = response.get("usage") or {}
    text = message.get("content") or ""
    return {
        "index": str(job.row["index"]),
        "row_key": job.row_key,
        "prediction": text,
        "finish_reason": choice.get("finish_reason"),
        "output_token_count": usage.get("completion_tokens"),
        "prompt_token_count": usage.get("prompt_tokens"),
        "api_endpoint": endpoint,
        "rank": int(job.rank),
        "benchmark_key": job.spec.key,
    }


def _load_existing_result_paths(output_dir: Path) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for path in (output_dir / "api_row_results").glob("*.json"):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        key = row.get("row_key")
        if key is None and row.get("index") is not None:
            key = str(row["index"])
        if key is not None and not row.get("error"):
            out[str(key)] = path
    return out


def _restore_mirrored_row_results(row_result_dir: Path, mirror_row_result_dir: Path | None) -> None:
    """Restore missing canonical row files from a persistent result mirror."""

    if mirror_row_result_dir is None or not mirror_row_result_dir.exists():
        return
    row_result_dir.mkdir(parents=True, exist_ok=True)
    restored = 0
    for source in mirror_row_result_dir.glob("*.json"):
        target = row_result_dir / source.name
        if target.exists():
            continue
        shutil.copy2(source, target)
        restored += 1
    if restored:
        print(f"[api-generate:restore] rows={restored} source={mirror_row_result_dir}")


def _prepare_handles_and_jobs(args: argparse.Namespace, specs: list[BenchmarkSpec]) -> tuple[dict[str, DatasetHandle], list[RowJob]]:
    runner, chartmuseum = _import_vlmeval_runner()

    handles: dict[str, DatasetHandle] = {}
    jobs_by_spec: list[list[RowJob]] = []
    for spec in specs:
        output_dir = run_dir(spec, args.model_slug, args.run_root)
        output_dir.mkdir(parents=True, exist_ok=True)
        row_result_dir = output_dir / "api_row_results"
        mirror_output_dir = (
            run_dir(spec, args.model_slug, args.result_mirror_root) if args.result_mirror_root is not None else None
        )
        mirror_row_result_dir = mirror_output_dir / "api_row_results" if mirror_output_dir is not None else None
        if args.no_resume and row_result_dir.exists():
            shutil.rmtree(row_result_dir)
        if args.no_resume and mirror_row_result_dir is not None and mirror_row_result_dir.exists():
            shutil.rmtree(mirror_row_result_dir)
        row_result_dir.mkdir(parents=True, exist_ok=True)
        _restore_mirrored_row_results(row_result_dir, mirror_row_result_dir)

        subset_manifest = _subset_manifest_path(args.subset_root, spec) if args.subset_root else None
        subset_entries = _subset_entries(subset_manifest, spec) if subset_manifest else []

        if spec.kind == "chartmuseum" or spec.key == "chartmuseum":
            rows = chartmuseum.load_chartmuseum_rows(spec.split or "test", chartmuseum.DEFAULT_DATA_ROOT, args.limit, args.sample_seed)
            if subset_manifest:
                rows = _apply_subset_rows(rows, subset_entries)
            handle = DatasetHandle(spec=spec, rows=rows)
            row_records = rows
            kind = "chartmuseum"
        else:
            dataset = build_vlmeval_dataset(spec)
            if subset_manifest:
                dataset.data = _apply_subset_frame(dataset.data, subset_entries)
            else:
                dataset.data = _limit_frame(dataset.data, args.limit, args.sample_seed)
            handle = DatasetHandle(spec=spec, dataset=dataset)
            row_records = [row.to_dict() for _, row in dataset.data.iterrows()]
            kind = "vlmeval"
        handles[spec.key] = handle

        existing = {} if args.no_resume else _load_existing_result_paths(output_dir)
        pending = 0
        spec_jobs: list[RowJob] = []
        for rank, row in enumerate(row_records):
            row_key = _row_key(row, rank)
            legacy_index = str(row["index"])
            if row_key in existing or legacy_index in existing:
                continue
            spec_jobs.append(
                RowJob(
                    spec=spec,
                    row=row,
                    rank=rank,
                    row_key=row_key,
                    output_dir=output_dir,
                    result_path=row_result_dir / _safe_result_name_for_row(row, rank),
                    kind=kind,
                    mirror_result_path=(
                        mirror_row_result_dir / _safe_result_name_for_row(row, rank)
                        if mirror_row_result_dir is not None
                        else None
                    ),
                )
            )
            pending += 1
        jobs_by_spec.append(spec_jobs)
        print(
            "[api-generate:prepare] "
            f"{spec.key} rows={len(row_records)} existing={len(existing)} pending={pending} output={output_dir}"
        )
    jobs: list[RowJob] = []
    max_len = max((len(spec_jobs) for spec_jobs in jobs_by_spec), default=0)
    for offset in range(max_len):
        for spec_jobs in jobs_by_spec:
            if offset < len(spec_jobs):
                jobs.append(spec_jobs[offset])
    return handles, jobs


def _worker_loop(
    *,
    args: argparse.Namespace,
    endpoint: str,
    handles: dict[str, DatasetHandle],
    jobs: "queue.Queue[RowJob]",
    errors: list[dict[str, Any]],
    error_lock: threading.Lock,
    progress: tqdm,
    endpoint_health: EndpointHealth,
    stop_event: threading.Event,
) -> None:
    while not stop_event.is_set():
        if endpoint_health.is_disabled(endpoint):
            return
        try:
            job = jobs.get(timeout=0.25)
        except queue.Empty:
            continue
        finalized = False
        try:
            if endpoint_health.should_defer(endpoint, job.attempted_endpoints):
                jobs.put(job)
                time.sleep(0.005)
                continue
            handle = handles[job.spec.key]
            messages = (
                _chartmuseum_messages(args, job.row)
                if job.kind == "chartmuseum"
                else _vlmeval_messages(args, handle, job.row)
            )
            response = _call_endpoint(args, endpoint, messages)
            endpoint_health.record_success(endpoint)
            result = _result_from_response(job, response, endpoint)
            _persist_worker_result(job, result, errors, error_lock)
            finalized = True
        except PermanentAPIError as exc:
            error = {
                "benchmark_key": job.spec.key,
                "index": str(job.row.get("index")),
                "row_key": job.row_key,
                "error": repr(exc),
                "endpoint": endpoint,
                "result_path": str(job.result_path),
            }
            _persist_worker_result(job, {**error, "prediction": "", "finish_reason": "error"}, errors, error_lock)
            with error_lock:
                errors.append(error)
            finalized = True
        except RetryableAPIError as exc:
            disabled = endpoint_health.record_failure(endpoint) if exc.affects_health else False
            if disabled:
                print(f"[api-generate:endpoint-disabled] endpoint={endpoint} reason={exc.detail}")
            next_job = replace(
                job,
                attempted_endpoints=tuple(dict.fromkeys((*job.attempted_endpoints, endpoint))),
                attempt_count=job.attempt_count + 1,
            )
            if next_job.attempt_count < int(args.api_max_retries):
                jobs.put(next_job)
            else:
                error = {
                    "benchmark_key": job.spec.key,
                    "index": str(job.row.get("index")),
                    "row_key": job.row_key,
                    "error": repr(exc),
                    "endpoint": endpoint,
                    "result_path": str(job.result_path),
                }
                _persist_worker_result(job, {**error, "prediction": "", "finish_reason": "error"}, errors, error_lock)
                with error_lock:
                    errors.append(error)
                finalized = True
            if next_job.attempt_count < int(args.api_max_retries):
                time.sleep(min(5.0, 0.25 * next_job.attempt_count))
        except Exception as exc:
            # Dataset decoding and prompt construction errors are row-local and
            # must not quarantine a healthy model endpoint.
            error = {
                "benchmark_key": job.spec.key,
                "index": str(job.row.get("index")),
                "row_key": job.row_key,
                "error": repr(exc),
                "endpoint": endpoint,
                "result_path": str(job.result_path),
            }
            _persist_worker_result(job, {**error, "prediction": "", "finish_reason": "error"}, errors, error_lock)
            with error_lock:
                errors.append(error)
            finalized = True
        finally:
            if finalized:
                progress.update(1)
            jobs.task_done()


def _prediction_map_from_row_results(output_dir: Path) -> dict[str, dict[str, Any]]:
    pred_map: dict[str, dict[str, Any]] = {}
    for path in sorted((output_dir / "api_row_results").glob("*.json")):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        key = row.get("row_key")
        if key is None and row.get("index") is not None:
            key = str(row["index"])
        if key is not None and not row.get("error"):
            pred_map[str(key)] = row
    return pred_map


def _token_stats(pred_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    vals = sorted(int(v.get("output_token_count") or 0) for v in pred_map.values())
    if not vals:
        return {"mean": 0, "median": 0, "max": 0, "length_cap_fraction": 0}
    finish = Counter(str(v.get("finish_reason")) for v in pred_map.values())
    n = len(vals)
    median = vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2.0
    return {
        "mean": sum(vals) / n,
        "median": median,
        "max": max(vals),
        "length_cap_fraction": finish.get("length", 0) / n,
    }


def _finalize_spec(args: argparse.Namespace, handle: DatasetHandle) -> dict[str, Any]:
    runner, chartmuseum = _import_vlmeval_runner()
    spec = handle.spec
    output_dir = run_dir(spec, args.model_slug, args.run_root)
    pred_map = _prediction_map_from_row_results(output_dir)
    if spec.kind == "chartmuseum" or spec.key == "chartmuseum":
        # Keep the exact row order used when jobs were created. The row key
        # includes the per-run rank, so sorting here breaks resume/finalize for
        # shuffled subset manifests.
        rows = list(handle.rows or [])
        records = []
        for rank, row in enumerate(rows):
            pred = pred_map.get(_row_key(row, rank), pred_map.get(str(row["index"]), {}))
            raw = pred.get("prediction", "")
            records.append(
                {
                    "index": str(row["index"]),
                    "hash": row.get("hash"),
                    "question": row["question"],
                    "answer": str(row["answer"]),
                    "reasoning_type": row.get("reasoning_type"),
                    "source": row.get("source"),
                    "raw_prediction": raw,
                    "prediction": chartmuseum.extract_answer(raw),
                    "finish_reason": pred.get("finish_reason"),
                    "output_token_count": pred.get("output_token_count"),
                }
            )
        frame = pd.DataFrame(records)
        pred_jsonl = output_dir / "predictions.jsonl"
        with pred_jsonl.open("w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False, default=json_default) + "\n")
        frame.to_json(output_dir / "predictions.json", orient="records", force_ascii=False, indent=2)
        frame.to_excel(output_dir / "predictions.xlsx", index=False)
        with (output_dir / "official_predictions.json").open("w", encoding="utf-8") as f:
            json.dump(frame["raw_prediction"].tolist(), f, ensure_ascii=False, indent=2)
        eval_file = output_dir / "predictions.xlsx"
        expected_rows = len(rows)
    else:
        pred_jsonl = output_dir / "predictions.jsonl"
        records = []
        with pred_jsonl.open("w", encoding="utf-8") as f:
            for rank, (_, row) in enumerate(handle.dataset.data.iterrows()):
                row_dict = row.to_dict()
                pred = pred_map.get(_row_key(row_dict, rank), pred_map.get(str(row_dict["index"]), {}))
                record = {
                    "index": str(row_dict["index"]),
                    "prediction": pred.get("prediction", ""),
                    "finish_reason": pred.get("finish_reason", ""),
                    "output_token_count": pred.get("output_token_count"),
                    "prompt_token_count": pred.get("prompt_token_count"),
                }
                records.append({**row_dict, **record})
                f.write(json.dumps(record, ensure_ascii=False, default=json_default) + "\n")
        frame = pd.DataFrame(records)
        # VLMEvalKit's evaluator resolves the prediction table from the alias
        # requested by the run (for example ``QBench_Video_8frame``). Some
        # dataset implementations expose a shorter internal ``dataset_name``
        # (for example ``QBench_Video``), which is not evaluator-compatible.
        eval_file = output_dir / f"{spec.alias}_predictions.xlsx"
        frame.to_excel(eval_file, index=False)
        table_jsonl = output_dir / f"{spec.alias}_predictions_table.jsonl"
        with table_jsonl.open("w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False, default=json_default) + "\n")
        expected_rows = len(handle.dataset.data)

    finish_reasons = Counter(str(v.get("finish_reason")) for v in pred_map.values())
    summary = {
        "dataset": spec.alias,
        "display": spec.display,
        "model": args.model,
        "model_slug": args.model_slug,
        "rows": len(pred_map),
        "expected_rows": expected_rows,
        "generation": {
            "backend": "openai_compatible_vllm_endpoint_pool",
            "temperature": float(args.temperature),
            "top_p": float(args.top_p),
            "top_k": int(args.top_k) if args.top_k is not None else None,
            "presence_penalty": float(args.presence_penalty),
            "repetition_penalty": float(args.repetition_penalty) if args.repetition_penalty is not None else None,
            "max_tokens": int(args.max_tokens),
            "seed": int(args.seed) if args.seed is not None else None,
            "api_model": args.api_model,
            "endpoint_count": len(args.api_bases),
            "parallelism_per_endpoint": int(args.parallelism_per_endpoint),
            "max_image_pixels": int(args.max_image_pixels),
            "max_image_side": int(args.max_image_side),
            "image_jpeg_quality": int(args.image_jpeg_quality),
        },
        "subset_manifest": str(_subset_manifest_path(args.subset_root, spec)) if args.subset_root else None,
        "finish_reason": dict(finish_reasons),
        "output_token_stats": _token_stats(pred_map),
        "artifacts": {"predictions_jsonl": str(pred_jsonl), "eval_file": str(eval_file)},
    }
    if len(pred_map) != expected_rows:
        summary["warning"] = f"missing {expected_rows - len(pred_map)} predictions"
    write_json(output_dir / "generation_summary.json", summary)
    print(
        "[api-generate:finalize] "
        f"{spec.key} rows={len(pred_map)}/{expected_rows} "
        f"mean_tokens={summary['output_token_stats']['mean']:.1f} "
        f"cap_hit={summary['output_token_stats']['length_cap_fraction']:.3f}"
    )
    return summary


def run(args: argparse.Namespace) -> None:
    specs = benchmark_specs_for_run_set(args.run_set, model_slug=args.model_slug)
    if args.exact_only and args.only:
        keep = {str(key) for key in args.only}
        specs = [spec for spec in specs if spec.key in keep]
        specs = filter_benchmark_specs(specs, exclude=args.exclude)
    else:
        specs = filter_benchmark_specs(specs, only=args.only, exclude=args.exclude)
    if not specs:
        raise ValueError("No benchmark specs selected")
    materialize_grounding_benchmark_files(specs)
    handles, pending = _prepare_handles_and_jobs(args, specs)
    q: queue.Queue[RowJob] = queue.Queue()
    for job in pending:
        q.put(job)
    errors: list[dict[str, Any]] = []
    error_lock = threading.Lock()
    endpoint_health = EndpointHealth(args.api_bases, args.endpoint_failure_threshold)
    stop_event = threading.Event()
    workers = []
    total_workers = len(args.api_bases) * int(args.parallelism_per_endpoint)
    print(
        "[api-generate:start] "
        f"model={args.model} slug={args.model_slug} specs={len(specs)} pending_rows={len(pending)} "
        f"endpoints={len(args.api_bases)} workers={total_workers} run_root={args.run_root}"
    )
    with tqdm(total=len(pending), desc=f"{args.model_slug} api generate") as progress:
        for endpoint in args.api_bases:
            for _ in range(int(args.parallelism_per_endpoint)):
                thread = threading.Thread(
                    target=_worker_loop,
                    kwargs={
                        "args": args,
                        "endpoint": endpoint,
                        "handles": handles,
                        "jobs": q,
                        "errors": errors,
                        "error_lock": error_lock,
                        "progress": progress,
                        "endpoint_health": endpoint_health,
                        "stop_event": stop_event,
                    },
                    daemon=True,
                )
                thread.start()
                workers.append(thread)
        q.join()
        stop_event.set()
        for thread in workers:
            thread.join(timeout=5)

    summaries = [_finalize_spec(args, handles[spec.key]) for spec in specs]
    suite_summary = {
        "model": args.model,
        "model_slug": args.model_slug,
        "run_root": str(args.run_root),
        "benchmarks": summaries,
        "errors": errors[:100],
        "error_count": len(errors),
        "endpoint_health": endpoint_health.snapshot(),
    }
    write_json(args.run_root / f"{args.model_slug}_api_generation_suite_summary.json", suite_summary)
    if errors:
        raise RuntimeError(f"{len(errors)} row generation errors; first error: {errors[0]}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--model-slug", required=True)
    parser.add_argument("--api-model", required=True)
    parser.add_argument("--api-base", action="append", dest="api_bases", required=True)
    parser.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY", "EMPTY"))
    parser.add_argument("--api-timeout", type=float, default=300.0)
    parser.add_argument(
        "--api-max-retries",
        type=int,
        default=5,
        help="Maximum total attempts for a row across the endpoint pool; permanent HTTP 4xx errors are not retried.",
    )
    parser.add_argument(
        "--endpoint-failure-threshold",
        type=int,
        default=2,
        help="Consecutive transport/server failures before an endpoint is quarantined for the remainder of the run.",
    )
    parser.add_argument("--parallelism-per-endpoint", type=int, default=4)
    parser.add_argument(
        "--run-set",
        choices=BENCHMARK_RUN_SETS,
        default="trace_candidate37_200",
    )
    parser.add_argument("--trace-candidate37-200", action="store_true")
    parser.add_argument("--run-root", type=Path, default=LIB_REPO_ROOT / "runs")
    parser.add_argument(
        "--result-mirror-root",
        type=Path,
        default=None,
        help="Optional persistent run root that mirrors every atomic per-row result and restores missing rows on resume.",
    )
    parser.add_argument("--queue-root", type=Path, default=DEFAULT_QUEUE_ROOT)
    parser.add_argument("--only", nargs="*", default=[])
    parser.add_argument("--exclude", nargs="*", default=[])
    parser.add_argument(
        "--exact-only",
        action="store_true",
        help="Interpret --only as exact BenchmarkSpec.key values, not aliases or aggregate groups.",
    )
    parser.add_argument("--subset-root", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--sample-seed", type=int, default=0)
    parser.add_argument("--max-image-pixels", type=int, default=1_000_000)
    parser.add_argument("--max-image-side", type=int, default=1280)
    parser.add_argument("--image-jpeg-quality", type=int, default=85)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument("--top-k", type=int, default=-1)
    parser.add_argument("--presence-penalty", type=float, default=0.0)
    parser.add_argument("--repetition-penalty", type=float, default=1.0)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args()
    if args.trace_candidate37_200:
        args.run_set = "trace_candidate37_200"
        if not args.only:
            args.only = list(TRACE_CANDIDATE37_200_BENCHMARKS)
    if args.run_set == "trace_grounding" and not args.only:
        args.only = list(TRACE_GROUNDING_BENCHMARKS)
    if args.run_set == "trace_grounding" and args.subset_root is None:
        args.subset_root = TRACE_GROUNDING_SUBSET_ROOT
    run(args)


if __name__ == "__main__":
    main()
