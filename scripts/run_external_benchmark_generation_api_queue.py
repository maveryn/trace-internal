#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import queue
import shutil
import sys
import threading
import time
from collections import Counter
from dataclasses import dataclass
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
    DEFAULT_QUEUE_ROOT,
    REPO_ROOT as LIB_REPO_ROOT,
    TRACE_CANDIDATE37_200_BENCHMARKS,
    BenchmarkSpec,
    benchmark_specs_for_run_set,
    effective_generation_batch_size,
    filter_benchmark_specs,
    json_default,
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


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}.{threading.get_ident()}")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, default=json_default) + "\n", encoding="utf-8")
    tmp.replace(path)


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


def _image_to_data_url(value: Any, *, image_format: str = "JPEG", quality: int = 95) -> str:
    if isinstance(value, str) and value.startswith("data:image/"):
        return value
    image = _load_image(value)
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


def _vlmeval_messages(handle: DatasetHandle, row: dict[str, Any]) -> list[dict[str, Any]]:
    runner, _ = _import_vlmeval_runner()
    row_series = pd.Series(row)
    # Some VLMEvalKit datasets materialize cached images in build_prompt. Keep that
    # per-dataset call serialized while allowing image encoding/API calls to run in parallel.
    with handle.lock:
        struct = runner.build_prompt_for_runner(handle.dataset, row_series, video_llm=handle.spec.video_llm)
    content: list[dict[str, Any]] = []
    for item in struct:
        typ = item.get("type")
        value = item.get("value")
        if typ == "image":
            content.append({"type": "image_url", "image_url": {"url": _image_to_data_url(value)}})
        elif typ == "video":
            raise NotImplementedError(f"OpenAI endpoint video prompts are not supported for {handle.spec.key}")
        else:
            text = "" if value is None else str(value)
            if text:
                content.append({"type": "text", "text": text})
    return [{"role": "user", "content": content or [{"type": "text", "text": ""}]}]


def _chartmuseum_messages(row: dict[str, Any]) -> list[dict[str, Any]]:
    image_path = row.get("image_path") or row.get("image")
    content: list[dict[str, Any]] = []
    if image_path:
        content.append({"type": "image_url", "image_url": {"url": _image_to_data_url(image_path)}})
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
    last_error: Exception | None = None
    for attempt in range(int(args.api_max_retries)):
        try:
            response = requests.post(
                _completion_url(endpoint),
                json=payload,
                headers=headers,
                timeout=float(args.api_timeout),
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            last_error = exc
            sleep_s = min(30.0, 1.5 * (attempt + 1))
            time.sleep(sleep_s)
    raise RuntimeError(f"{endpoint} failed after {args.api_max_retries} attempts: {last_error!r}")


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


def _prepare_handles_and_jobs(args: argparse.Namespace, specs: list[BenchmarkSpec]) -> tuple[dict[str, DatasetHandle], list[RowJob]]:
    runner, chartmuseum = _import_vlmeval_runner()
    from vlmeval.dataset import build_dataset

    handles: dict[str, DatasetHandle] = {}
    jobs_by_spec: list[list[RowJob]] = []
    for spec in specs:
        output_dir = run_dir(spec, args.model_slug, args.run_root)
        output_dir.mkdir(parents=True, exist_ok=True)
        row_result_dir = output_dir / "api_row_results"
        if args.no_resume and row_result_dir.exists():
            shutil.rmtree(row_result_dir)
        row_result_dir.mkdir(parents=True, exist_ok=True)

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
            dataset = build_dataset(spec.alias)
            if dataset is None:
                raise RuntimeError(f"VLMEvalKit could not build dataset {spec.alias}")
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
    jobs: "queue.Queue[RowJob | None]",
    errors: list[dict[str, Any]],
    error_lock: threading.Lock,
    progress: tqdm,
) -> None:
    while True:
        job = jobs.get()
        if job is None:
            jobs.task_done()
            return
        try:
            handle = handles[job.spec.key]
            messages = _chartmuseum_messages(job.row) if job.kind == "chartmuseum" else _vlmeval_messages(handle, job.row)
            response = _call_endpoint(args, endpoint, messages)
            result = _result_from_response(job, response, endpoint)
            _atomic_write_json(job.result_path, result)
        except Exception as exc:
            error = {
                "benchmark_key": job.spec.key,
                "index": str(job.row.get("index")),
                "row_key": job.row_key,
                "error": repr(exc),
                "endpoint": endpoint,
                "result_path": str(job.result_path),
            }
            _atomic_write_json(job.result_path, {**error, "prediction": "", "finish_reason": "error"})
            with error_lock:
                errors.append(error)
        finally:
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
        eval_file = output_dir / f"{handle.dataset.dataset_name}_predictions.xlsx"
        frame.to_excel(eval_file, index=False)
        table_jsonl = output_dir / f"{handle.dataset.dataset_name}_predictions_table.jsonl"
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
    handles, pending = _prepare_handles_and_jobs(args, specs)
    q: queue.Queue[RowJob | None] = queue.Queue()
    for job in pending:
        q.put(job)
    errors: list[dict[str, Any]] = []
    error_lock = threading.Lock()
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
                    },
                    daemon=True,
                )
                thread.start()
                workers.append(thread)
        for _ in workers:
            q.put(None)
        q.join()
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
    parser.add_argument("--api-max-retries", type=int, default=5)
    parser.add_argument("--parallelism-per-endpoint", type=int, default=4)
    parser.add_argument("--run-set", choices=["full", "remaining_base", "base_all", "trace_candidate37_200"], default="trace_candidate37_200")
    parser.add_argument("--trace-candidate37-200", action="store_true")
    parser.add_argument("--run-root", type=Path, default=LIB_REPO_ROOT / "runs")
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
    run(args)


if __name__ == "__main__":
    main()
