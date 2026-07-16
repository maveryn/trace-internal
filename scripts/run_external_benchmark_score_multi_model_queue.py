#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from benchmark_queue_lib import (  # noqa: E402
    BENCHMARK_RUN_SETS,
    DEFAULT_BENCHMARK_ROOT,
    DEFAULT_QUEUE_ROOT,
    REPO_ROOT as LIB_REPO_ROOT,
    TRACE_CANDIDATE37_200_BENCHMARKS,
    TRACE_GROUNDING_BENCHMARKS,
    benchmark_specs_for_run_set,
    claim_next_job,
    file_lock,
    filter_benchmark_specs,
    json_default,
    load_json,
    mark_job,
    materialize_grounding_benchmark_files,
    spec_by_key,
    write_json,
)
from run_external_benchmark_score_queue import (  # noqa: E402
    PERSISTENT_JUDGE_CACHE_CONTRACT_VERSION,
    PersistentJudge,
    _maybe_write_screenspot_aggregate,
    _run_score_for_spec,
)
from trace_final25_contract import DIRECT_SCORE_KEYS  # noqa: E402


def _parse_model(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("--model-entry must be slug=path_or_hf_id")
    slug, path = value.split("=", 1)
    slug = slug.strip()
    path = path.strip()
    if not slug or not path:
        raise argparse.ArgumentTypeError("--model-entry must be slug=path_or_hf_id")
    return slug, path


def _sentinel_path(root: Path, queue_name: str, job_id: str) -> Path:
    return root / "_multi_model_score_sentinels" / queue_name / f"{job_id}.json"


def _score_job(args: argparse.Namespace, job_id: str, judge: PersistentJudge) -> dict[str, Any]:
    spec = spec_by_key(job_id)
    model_results: list[dict[str, Any]] = []
    for slug, model_path in args.model_entries:
        print(f"[score-multi:model] benchmark={job_id} slug={slug}")
        summary = _run_score_for_spec(args, spec, model_path, slug, judge)
        model_results.append(
            {
                "model_slug": slug,
                "model": model_path,
                "benchmark_score_path": summary.get("benchmark_score_path"),
                "rows": summary.get("rows"),
                "score": summary.get("score"),
                "scores": summary.get("scores"),
                "archive_descriptors": summary.get("archive_descriptors", []),
            }
        )
        _maybe_write_screenspot_aggregate(slug, args.benchmark_root)
    sentinel = {
        "benchmark_key": job_id,
        "models": model_results,
        "queue_name": args.queue_name,
        "updated_at": time.time(),
    }
    path = _sentinel_path(args.benchmark_root, args.queue_name, job_id)
    write_json(path, sentinel)
    return sentinel


def _archive_sentinel_current(args: argparse.Namespace, path: Path, benchmark_key: str) -> bool:
    spool_root = str(os.environ.get("TRACE_FINAL25_HF_SPOOL_ROOT", "")).strip()
    if not spool_root:
        return path.exists()
    try:
        sentinel = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    expected_models = {slug for slug, _ in args.model_entries}
    models = sentinel.get("models")
    if not isinstance(models, list) or {str(item.get("model_slug")) for item in models} != expected_models:
        return False
    expected_run = str(os.environ.get("TRACE_FINAL25_RUN_ID", "")).strip()
    expected_campaign = str(os.environ.get("TRACE_FINAL25_CAMPAIGN_CONFIG_HASH", "")).strip()
    expected_dataset = str(os.environ.get("TRACE_FINAL25_DATASET_REVISION", "")).strip()
    for model in models:
        slug = str(model.get("model_slug"))
        descriptors = model.get("archive_descriptors")
        if not isinstance(descriptors, list) or len(descriptors) != 2:
            return False
        seen_stages: set[str] = set()
        for descriptor_text in descriptors:
            descriptor_path = Path(str(descriptor_text))
            try:
                descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return False
            identity = descriptor.get("identity") or {}
            provenance = descriptor.get("provenance") or {}
            try:
                descriptor_seed = int(identity.get("seed", -1))
            except (TypeError, ValueError):
                return False
            if (
                str(identity.get("run_id")) != expected_run
                or str(identity.get("model_slug")) != slug
                or descriptor_seed != int(args.seed)
                or str(identity.get("benchmark")) != benchmark_key
                or str(identity.get("dataset_revision")) != expected_dataset
                or str(provenance.get("campaign_config_hash")) != expected_campaign
            ):
                return False
            seen_stages.add(str(identity.get("stage")))
        if seen_stages != {"extraction", "score"}:
            return False
    return True


def _repair_stale_archive_sentinels(
    args: argparse.Namespace,
    queue_path: Path,
    jobs: list[tuple[str, Path]],
) -> None:
    if not str(os.environ.get("TRACE_FINAL25_HF_SPOOL_ROOT", "")).strip():
        return
    lock_path = queue_path.with_suffix(queue_path.suffix + ".lock")
    with file_lock(lock_path):
        state = load_json(queue_path, {"jobs": {}})
        state_jobs = state.setdefault("jobs", {})
        changed = False
        for job_id, sentinel in jobs:
            if _archive_sentinel_current(args, sentinel, job_id):
                continue
            info = state_jobs.get(job_id, {})
            if info.get("status") == "running":
                try:
                    os.kill(int(info.get("pid")), 0)
                except (OSError, TypeError, ValueError):
                    pass
                else:
                    continue
            sentinel.unlink(missing_ok=True)
            state_jobs[job_id] = {"status": "pending", "attempts": 0, "reason": "archive_backfill"}
            changed = True
        if changed:
            write_json(queue_path, state)


def _terminal_failed_jobs(
    queue_path: Path,
    jobs: list[tuple[str, Path]],
    max_attempts: int,
) -> list[tuple[str, str]]:
    state = load_json(queue_path, {"jobs": {}})
    terminal = []
    for job_id, sentinel in jobs:
        info = (state.get("jobs") or {}).get(job_id, {})
        if sentinel.exists() or info.get("status") == "done":
            continue
        if info.get("status") == "failed" and int(info.get("attempts") or 0) >= max_attempts:
            terminal.append((job_id, str(info.get("error") or "unknown error")))
    return terminal


def run_worker(args: argparse.Namespace) -> None:
    if args.gpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu
    os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")
    os.environ.setdefault("VLLM_ATTENTION_BACKEND", args.attention_backend)
    os.environ.setdefault("VLLM_DISABLE_COMPILE_CACHE", "1")

    specs = benchmark_specs_for_run_set(args.run_set)
    if args.exact_only and args.only:
        keep = {str(key) for key in args.only}
        specs = [spec for spec in specs if spec.key in keep]
        specs = filter_benchmark_specs(specs, exclude=args.exclude)
    else:
        specs = filter_benchmark_specs(specs, only=args.only, exclude=args.exclude)
    if args.run_set == "trace_final25":
        unsupported = [spec.key for spec in specs if spec.key not in DIRECT_SCORE_KEYS]
        if args.only and unsupported:
            raise ValueError(
                "The Final25 multi-model direct scorer only accepts DIRECT_SCORE_KEYS; "
                f"route these separately: {unsupported}"
            )
        specs = [spec for spec in specs if spec.key in DIRECT_SCORE_KEYS]
    materialize_grounding_benchmark_files(specs)
    queue_path = args.queue_root / f"score_multi_{args.queue_name}.json"
    jobs = [(spec.key, _sentinel_path(args.benchmark_root, args.queue_name, spec.key)) for spec in specs]
    _repair_stale_archive_sentinels(args, queue_path, jobs)
    print(
        "[score-multi:init] "
        f"gpu={os.environ.get('CUDA_VISIBLE_DEVICES', '')} jobs={len(jobs)} "
        f"models={[slug for slug, _ in args.model_entries]} queue={queue_path}"
    )
    judge = PersistentJudge(args)
    try:
        while True:
            job_id = claim_next_job(
                queue_path=queue_path,
                jobs=jobs,
                worker_id=args.worker_id,
                stale_after_sec=args.stale_after_sec,
                max_attempts=args.max_attempts,
            )
            if job_id is None:
                terminal_failures = _terminal_failed_jobs(queue_path, jobs, args.max_attempts)
                if terminal_failures:
                    details = "; ".join(f"{job_id}: {error}" for job_id, error in terminal_failures[:5])
                    raise RuntimeError(
                        f"{len(terminal_failures)} score jobs exhausted max attempts: {details}"
                    )
                print("[score-multi:done] no remaining score jobs")
                break
            try:
                print(f"[score-multi:claim] {job_id}")
                summary = _score_job(args, job_id, judge)
                mark_job(
                    queue_path,
                    job_id,
                    "done",
                    worker=args.worker_id,
                    output_dir=str(_sentinel_path(args.benchmark_root, args.queue_name, job_id)),
                    rows={item["model_slug"]: item.get("rows") for item in summary["models"]},
                )
            except Exception as exc:
                mark_job(queue_path, job_id, "failed", worker=args.worker_id, error=repr(exc))
                if args.stop_on_error:
                    raise
                print(f"[score-multi:error] {job_id} failed and will be skipped by this worker: {exc!r}", file=sys.stderr)
    finally:
        judge.cleanup()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-entry", action="append", type=_parse_model, dest="model_entries", required=True)
    parser.add_argument(
        "--run-set",
        choices=BENCHMARK_RUN_SETS,
        default="trace_candidate37_200",
    )
    parser.add_argument("--trace-candidate37-200", action="store_true")
    parser.add_argument("--gpu", default=os.environ.get("CUDA_VISIBLE_DEVICES", ""))
    parser.add_argument("--worker-id", default=f"score-multi-{os.getpid()}")
    parser.add_argument("--queue-name", required=True)
    parser.add_argument("--seed", type=int, default=int(os.environ.get("TRACE_FINAL25_SEED", "42")))
    parser.add_argument("--queue-root", type=Path, default=DEFAULT_QUEUE_ROOT)
    parser.add_argument("--run-root", type=Path, default=LIB_REPO_ROOT / "runs")
    parser.add_argument("--benchmark-root", type=Path, default=DEFAULT_BENCHMARK_ROOT)
    parser.add_argument("--only", nargs="*", default=[])
    parser.add_argument("--exclude", nargs="*", default=[])
    parser.add_argument("--exact-only", action="store_true")
    parser.add_argument("--eval-judge-model", default="exact_matching")
    parser.add_argument("--eval-nproc", type=int, default=16)
    parser.add_argument("--judge-model", default="Qwen/Qwen3-32B")
    parser.add_argument("--judge-batch-size", type=int, default=1024)
    parser.add_argument("--judge-tensor-parallel-size", type=int, default=1)
    parser.add_argument("--judge-gpu-memory-utilization", type=float, default=0.90)
    parser.add_argument("--judge-max-model-len", type=int, default=8192)
    parser.add_argument("--judge-max-num-seqs", type=int, default=1024)
    parser.add_argument("--judge-max-num-batched-tokens", type=int, default=65536)
    parser.add_argument("--judge-max-tokens", type=int, default=256)
    parser.add_argument("--judge-api-base", action="append", dest="judge_api_bases")
    parser.add_argument("--judge-api-model", default="qwen3-32b-judge")
    parser.add_argument("--judge-api-tokenizer-model", default="Qwen/Qwen3-32B")
    parser.add_argument("--judge-api-parallelism", type=int, default=128)
    parser.add_argument(
        "--judge-api-batch-size",
        type=int,
        default=1,
        help="Prompts per /completions request; one preserves the historical request shape.",
    )
    parser.add_argument("--judge-api-batches-per-endpoint", type=int, default=1)
    parser.add_argument("--judge-api-max-batch-chars", type=int, default=100_000)
    parser.add_argument("--judge-api-endpoint-failure-threshold", type=int, default=3)
    parser.add_argument("--judge-api-endpoint-cooldown-seconds", type=float, default=30.0)
    parser.add_argument("--judge-api-timeout", type=float, default=120.0)
    parser.add_argument("--judge-api-max-retries", type=int, default=5)
    parser.add_argument("--judge-cache-contract-version", default=PERSISTENT_JUDGE_CACHE_CONTRACT_VERSION)
    parser.add_argument("--attention-backend", default="FLASH_ATTN")
    parser.add_argument("--stale-after-sec", type=float, default=900)
    parser.add_argument("--max-attempts", type=int, default=2)
    parser.add_argument("--stop-on-error", action="store_true")
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args()
    if args.trace_candidate37_200:
        args.run_set = "trace_candidate37_200"
        if not args.only:
            args.only = list(TRACE_CANDIDATE37_200_BENCHMARKS)
    if args.run_set == "trace_grounding" and not args.only:
        args.only = list(TRACE_GROUNDING_BENCHMARKS)
    run_worker(args)


if __name__ == "__main__":
    main()
