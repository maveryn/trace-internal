#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from collections import Counter
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pandas as pd
from tqdm import tqdm

try:
    from PIL import ImageFile

    ImageFile.LOAD_TRUNCATED_IMAGES = True
except Exception:
    pass

from benchmark_queue_lib import (
    BASE_MODEL_SPEC,
    DEFAULT_QUEUE_ROOT,
    REPO_ROOT,
    VLMEVAL_ROOT,
    BenchmarkSpec,
    benchmark_specs_for_run_set,
    claim_next_job,
    effective_generation_batch_size,
    json_default,
    mark_job,
    run_dir,
    spec_by_key,
    write_json,
)


def _import_vlmeval_runner():
    scripts_root = VLMEVAL_ROOT / "scripts"
    for path in (VLMEVAL_ROOT, scripts_root):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    import batched_vlmevalkit_qwen3vl as runner
    import batched_chartmuseum_vllm as chartmuseum

    return runner, chartmuseum


def _limit_frame(frame: pd.DataFrame, limit: int | None, seed: int) -> pd.DataFrame:
    if limit is not None and limit < len(frame):
        return frame.sample(n=limit, random_state=seed).sort_values("index").reset_index(drop=True)
    return frame


def _effective_max_tokens(spec: BenchmarkSpec, max_tokens_override: int | None) -> int:
    if max_tokens_override is not None and max_tokens_override > 0:
        return min(spec.max_tokens, max_tokens_override)
    return spec.max_tokens


def _sampling_params_for_spec(spec: BenchmarkSpec, max_tokens_override: int | None):
    from vllm import SamplingParams

    max_tokens = _effective_max_tokens(spec, max_tokens_override)
    return SamplingParams(
        temperature=spec.temperature,
        top_p=spec.top_p,
        top_k=spec.top_k,
        presence_penalty=spec.presence_penalty,
        repetition_penalty=spec.repetition_penalty,
        max_tokens=max_tokens,
    )


def _prepare_vlmeval_batch(
    *,
    runner: Any,
    dataset: Any,
    processor: Any,
    spec: BenchmarkSpec,
    batch: pd.DataFrame,
) -> tuple[list[Any], list[dict[str, Any]]]:
    rows = [row for _, row in batch.iterrows()]
    requests: list[dict[str, Any]] = []
    for row in rows:
        struct = runner.build_prompt_for_runner(dataset, row, video_llm=spec.video_llm)
        requests.append(
            runner.make_vllm_request(
                processor,
                struct,
                max_pixels=spec.max_pixels,
                total_pixels=spec.total_pixels,
            )
        )
    return rows, requests


def _prepare_chartmuseum_batch(
    *,
    chartmuseum: Any,
    processor: Any,
    spec: BenchmarkSpec,
    batch: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    return batch, chartmuseum.make_vl_requests(processor, batch, max_pixels=spec.max_pixels)


def _generate_vlmeval_spec(
    *,
    spec: BenchmarkSpec,
    model_path: str,
    model_slug: str,
    llm: Any,
    processor: Any,
    output_dir: Path,
    batch_size: int,
    max_tokens_override: int | None,
    limit: int | None,
    sample_seed: int,
    no_resume: bool,
    prefetch_workers: int,
    prefetch_batches: int,
) -> dict[str, Any]:
    runner, _ = _import_vlmeval_runner()
    from vlmeval.dataset import build_dataset

    output_dir.mkdir(parents=True, exist_ok=True)
    pred_jsonl = output_dir / "predictions.jsonl"
    if no_resume and pred_jsonl.exists():
        pred_jsonl.unlink()

    dataset = build_dataset(spec.alias)
    if dataset is None:
        raise RuntimeError(f"VLMEvalKit could not build dataset {spec.alias}")
    dataset.data = _limit_frame(dataset.data, limit, sample_seed)

    existing = {} if no_resume else runner.load_jsonl_by_index(pred_jsonl)
    pending = dataset.data[~dataset.data["index"].astype(str).isin(existing)].copy()
    max_tokens = _effective_max_tokens(spec, max_tokens_override)
    print(
        "[generate:vlmeval] "
        f"dataset={spec.alias} rows={len(dataset.data)} existing={len(existing)} pending={len(pending)} "
        f"batch_size={batch_size} max_tokens={max_tokens} output={output_dir}"
    )

    t0 = time.time()
    sampling = _sampling_params_for_spec(spec, max_tokens_override)
    total_batches = math.ceil(len(pending) / batch_size) if len(pending) else 0
    starts = list(range(0, len(pending), batch_size))
    max_workers = max(1, int(prefetch_workers))
    max_prefetch = max(1, int(prefetch_batches))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures: dict[int, Future[tuple[list[Any], list[dict[str, Any]]]]] = {}
        next_submit = 0

        def submit_until_full() -> None:
            nonlocal next_submit
            while next_submit < len(starts) and len(futures) < max_prefetch:
                start = starts[next_submit]
                batch = pending.iloc[start:start + batch_size].copy()
                futures[next_submit] = executor.submit(
                    _prepare_vlmeval_batch,
                    runner=runner,
                    dataset=dataset,
                    processor=processor,
                    spec=spec,
                    batch=batch,
                )
                next_submit += 1

        submit_until_full()
        for batch_i in tqdm(range(total_batches), total=total_batches, desc=f"{spec.alias} generate"):
            rows, requests = futures.pop(batch_i).result()
            submit_until_full()
            outputs = llm.generate(requests, sampling_params=sampling, use_tqdm=False)
            written = []
            for row, out in zip(rows, outputs):
                written.append(
                    {
                        "index": str(row["index"]),
                        "prediction": out.outputs[0].text,
                        "finish_reason": out.outputs[0].finish_reason,
                        "output_token_count": len(out.outputs[0].token_ids),
                    }
                )
            runner.append_jsonl(pred_jsonl, written)

    pred_map = runner.load_jsonl_by_index(pred_jsonl)
    eval_xlsx = runner.write_eval_files(dataset, pred_map, output_dir)
    finish_reasons = Counter(str(v.get("finish_reason")) for v in pred_map.values())
    token_counts = [int(v.get("output_token_count") or 0) for v in pred_map.values()]
    summary = {
        "dataset": spec.alias,
        "display": spec.display,
        "model": model_path,
        "model_slug": model_slug,
        "rows": len(pred_map),
        "generation_elapsed_sec": time.time() - t0,
        "generation": {
            "temperature": spec.temperature,
            "top_p": spec.top_p,
            "top_k": spec.top_k,
            "presence_penalty": spec.presence_penalty,
            "repetition_penalty": spec.repetition_penalty,
            "max_tokens": max_tokens,
            "configured_max_tokens": spec.max_tokens,
            "video_llm": spec.video_llm,
            "prefetch_workers": max_workers,
            "prefetch_batches": max_prefetch,
        },
        "finish_reason": dict(finish_reasons),
        "output_token_stats": {
            "mean": sum(token_counts) / len(token_counts) if token_counts else 0,
            "max": max(token_counts) if token_counts else 0,
            "length_cap_fraction": finish_reasons.get("length", 0) / len(pred_map) if pred_map else 0,
        },
        "artifacts": {"predictions_jsonl": str(pred_jsonl), "eval_xlsx": str(eval_xlsx)},
    }
    write_json(output_dir / "generation_summary.json", summary)
    return summary


def _generate_chartmuseum_spec(
    *,
    spec: BenchmarkSpec,
    model_path: str,
    model_slug: str,
    llm: Any,
    processor: Any,
    output_dir: Path,
    batch_size: int,
    max_tokens_override: int | None,
    limit: int | None,
    sample_seed: int,
    no_resume: bool,
    prefetch_workers: int,
    prefetch_batches: int,
) -> dict[str, Any]:
    _, chartmuseum = _import_vlmeval_runner()
    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = output_dir / "predictions.jsonl"
    if no_resume and jsonl_path.exists():
        jsonl_path.unlink()
    existing = {} if no_resume else chartmuseum.load_existing(jsonl_path)

    split = spec.split or "test"
    rows = chartmuseum.load_chartmuseum_rows(split, chartmuseum.DEFAULT_DATA_ROOT, limit, sample_seed)
    pending = [r for r in rows if str(r["index"]) not in existing]
    max_tokens = _effective_max_tokens(spec, max_tokens_override)
    print(
        "[generate:chartmuseum] "
        f"split={split} rows={len(rows)} existing={len(existing)} pending={len(pending)} "
        f"batch_size={batch_size} max_tokens={max_tokens} output={output_dir}"
    )

    t0 = time.time()
    sampling = _sampling_params_for_spec(spec, max_tokens_override)
    total_batches = math.ceil(len(pending) / batch_size) if pending else 0
    starts = list(range(0, len(pending), batch_size))
    max_workers = max(1, int(prefetch_workers))
    max_prefetch = max(1, int(prefetch_batches))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures: dict[int, Future[tuple[list[dict[str, Any]], list[dict[str, Any]]]]] = {}
        next_submit = 0

        def submit_until_full() -> None:
            nonlocal next_submit
            while next_submit < len(starts) and len(futures) < max_prefetch:
                start = starts[next_submit]
                batch = list(pending[start:start + batch_size])
                futures[next_submit] = executor.submit(
                    _prepare_chartmuseum_batch,
                    chartmuseum=chartmuseum,
                    processor=processor,
                    spec=spec,
                    batch=batch,
                )
                next_submit += 1

        submit_until_full()
        for batch_i in tqdm(range(total_batches), total=total_batches, desc="ChartMuseum generate"):
            batch, requests = futures.pop(batch_i).result()
            submit_until_full()
            outputs = llm.generate(requests, sampling_params=sampling, use_tqdm=False)
            written = []
            for row, out in zip(batch, outputs):
                raw = out.outputs[0].text
                written.append(
                    {
                        "index": str(row["index"]),
                        "hash": row.get("hash"),
                        "question": row["question"],
                        "answer": str(row["answer"]),
                        "reasoning_type": row.get("reasoning_type"),
                        "source": row.get("source"),
                        "raw_prediction": raw,
                        "prediction": chartmuseum.extract_answer(raw),
                        "finish_reason": out.outputs[0].finish_reason,
                        "output_token_count": len(out.outputs[0].token_ids),
                    }
                )
            chartmuseum.append_jsonl(jsonl_path, written)

    results = list(chartmuseum.load_existing(jsonl_path).values())
    results.sort(key=lambda x: int(x["index"]))
    result_df = pd.DataFrame(results)
    result_df.to_json(output_dir / "predictions.json", orient="records", force_ascii=False, indent=2)
    result_df.to_excel(output_dir / "predictions.xlsx", index=False)
    with (output_dir / "official_predictions.json").open("w", encoding="utf-8") as f:
        json.dump(result_df["raw_prediction"].tolist(), f, ensure_ascii=False, indent=2)

    finish_reasons = Counter(str(v.get("finish_reason")) for v in results)
    token_counts = [int(v.get("output_token_count") or 0) for v in results]
    summary = {
        "dataset": "ChartMuseum",
        "display": spec.display,
        "split": split,
        "model": model_path,
        "model_slug": model_slug,
        "rows": len(results),
        "generation_elapsed_sec": time.time() - t0,
        "generation": {
            "temperature": spec.temperature,
            "top_p": spec.top_p,
            "top_k": spec.top_k,
            "presence_penalty": spec.presence_penalty,
            "repetition_penalty": spec.repetition_penalty,
            "max_tokens": max_tokens,
            "configured_max_tokens": spec.max_tokens,
            "prefetch_workers": max_workers,
            "prefetch_batches": max_prefetch,
        },
        "finish_reason": dict(finish_reasons),
        "output_token_stats": {
            "mean": sum(token_counts) / len(token_counts) if token_counts else 0,
            "max": max(token_counts) if token_counts else 0,
            "length_cap_fraction": finish_reasons.get("length", 0) / len(results) if results else 0,
        },
        "artifacts": {"predictions_jsonl": str(jsonl_path), "predictions_xlsx": str(output_dir / "predictions.xlsx")},
    }
    write_json(output_dir / "generation_summary.json", summary)
    return summary


def run_worker(args: argparse.Namespace) -> None:
    if args.gpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu
    os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")
    os.environ.setdefault("VLLM_ATTENTION_BACKEND", args.attention_backend)

    specs = benchmark_specs_for_run_set(args.run_set, model_slug=args.model_slug)
    if args.only:
        keep = set(args.only)
        specs = [spec for spec in specs if spec.key in keep or spec.alias in keep]
    if args.exclude:
        drop = set(args.exclude)
        specs = [spec for spec in specs if spec.key not in drop and spec.alias not in drop]

    queue_path = args.queue_root / f"generation_{args.queue_name or args.model_slug + '_' + args.run_set}.json"
    jobs = [(spec.key, run_dir(spec, args.model_slug, args.run_root) / "generation_summary.json") for spec in specs]
    print(
        "[worker:init] "
        f"model={args.model} slug={args.model_slug} gpu={os.environ.get('CUDA_VISIBLE_DEVICES', '')} "
        f"run_set={args.run_set} jobs={len(jobs)} queue={queue_path}"
    )

    from transformers import AutoProcessor
    from vllm import LLM

    processor = AutoProcessor.from_pretrained(args.model, trust_remote_code=True)
    llm_kwargs: dict[str, Any] = {
        "model": args.model,
        "tensor_parallel_size": args.tensor_parallel_size,
        "gpu_memory_utilization": args.gpu_memory_utilization,
        "max_num_seqs": args.max_num_seqs,
        "max_num_batched_tokens": args.max_num_batched_tokens,
        "attention_backend": args.attention_backend,
        "limit_mm_per_prompt": {"image": args.max_images, "video": args.max_videos},
        "trust_remote_code": True,
        "seed": 0,
    }
    if args.max_model_len is not None:
        llm_kwargs["max_model_len"] = args.max_model_len
    llm = LLM(**llm_kwargs)

    runner, _ = _import_vlmeval_runner()
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
                print("[worker:done] no remaining generation jobs")
                break
            spec = spec_by_key(job_id)
            output_dir = run_dir(spec, args.model_slug, args.run_root)
            job_batch_size = effective_generation_batch_size(spec, args.batch_size, args.max_tokens_override)
            print(
                f"[worker:claim] {job_id} -> {output_dir} "
                f"batch_size={job_batch_size} requested_batch_size={args.batch_size}"
            )
            try:
                if spec.kind == "chartmuseum":
                    summary = _generate_chartmuseum_spec(
                        spec=spec,
                        model_path=args.model,
                        model_slug=args.model_slug,
                        llm=llm,
                        processor=processor,
                        output_dir=output_dir,
                        batch_size=job_batch_size,
                        max_tokens_override=args.max_tokens_override,
                        limit=args.limit,
                        sample_seed=args.sample_seed,
                        no_resume=args.no_resume,
                        prefetch_workers=args.prefetch_workers,
                        prefetch_batches=args.prefetch_batches,
                    )
                else:
                    summary = _generate_vlmeval_spec(
                        spec=spec,
                        model_path=args.model,
                        model_slug=args.model_slug,
                        llm=llm,
                        processor=processor,
                        output_dir=output_dir,
                        batch_size=job_batch_size,
                        max_tokens_override=args.max_tokens_override,
                        limit=args.limit,
                        sample_seed=args.sample_seed,
                        no_resume=args.no_resume,
                        prefetch_workers=args.prefetch_workers,
                        prefetch_batches=args.prefetch_batches,
                    )
                mark_job(queue_path, job_id, "done", worker=args.worker_id, output_dir=str(output_dir), rows=summary.get("rows"))
            except Exception as exc:
                mark_job(queue_path, job_id, "failed", worker=args.worker_id, output_dir=str(output_dir), error=repr(exc))
                if args.stop_on_error:
                    raise
                print(f"[worker:error] {job_id} failed and will be skipped by this worker: {exc!r}", file=sys.stderr)
    finally:
        runner.cleanup_vllm_engine(llm)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=BASE_MODEL_SPEC.path)
    parser.add_argument("--model-slug", default=BASE_MODEL_SPEC.slug)
    parser.add_argument("--run-set", choices=["full", "remaining_base", "base_all"], default="remaining_base")
    parser.add_argument("--gpu", default=os.environ.get("CUDA_VISIBLE_DEVICES", ""))
    parser.add_argument("--worker-id", default=f"generation-{os.getpid()}")
    parser.add_argument("--queue-name", default="")
    parser.add_argument("--queue-root", type=Path, default=DEFAULT_QUEUE_ROOT)
    parser.add_argument("--run-root", type=Path, default=REPO_ROOT / "runs")
    parser.add_argument("--only", nargs="*", default=[])
    parser.add_argument("--exclude", nargs="*", default=[])
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--sample-seed", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--tensor-parallel-size", type=int, default=1)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.90)
    parser.add_argument("--max-model-len", type=int, default=32768)
    parser.add_argument("--max-num-seqs", type=int, default=256)
    parser.add_argument("--max-num-batched-tokens", type=int, default=65536)
    parser.add_argument("--max-tokens-override", type=int, default=None)
    parser.add_argument("--prefetch-workers", type=int, default=2)
    parser.add_argument("--prefetch-batches", type=int, default=2)
    parser.add_argument("--max-images", type=int, default=24)
    parser.add_argument("--max-videos", type=int, default=3)
    parser.add_argument("--attention-backend", default="FLASH_ATTN")
    parser.add_argument("--stale-after-sec", type=float, default=900)
    parser.add_argument("--max-attempts", type=int, default=2)
    parser.add_argument("--stop-on-error", action="store_true")
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args()
    run_worker(args)


if __name__ == "__main__":
    main()
