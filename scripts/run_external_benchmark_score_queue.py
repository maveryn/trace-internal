#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd
from tqdm import tqdm

from benchmark_queue_lib import (
    BASE_MODEL_SPEC,
    DEFAULT_BENCHMARK_ROOT,
    DEFAULT_QUEUE_ROOT,
    REPO_ROOT,
    VLMEVAL_ROOT,
    BenchmarkSpec,
    aggregate_score_path,
    benchmark_dir,
    benchmark_specs_for_run_set,
    claim_next_job,
    extract_score_and_rows,
    filter_benchmark_specs,
    json_default,
    local_judge_eval_mode,
    mark_job,
    run_dir,
    score_path,
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


class PersistentJudge:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.llm = None
        self.tokenizer = None

    def _ensure_loaded(self) -> None:
        if self.llm is not None:
            return
        if self.args.gpu:
            os.environ["CUDA_VISIBLE_DEVICES"] = self.args.gpu
        os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")
        os.environ.setdefault("VLLM_ATTENTION_BACKEND", self.args.attention_backend)

        from transformers import AutoTokenizer
        from vllm import LLM

        print(
            "[judge:init] "
            f"model={self.args.judge_model} gpu={os.environ.get('CUDA_VISIBLE_DEVICES', '')} "
            f"batch_size={self.args.judge_batch_size}"
        )
        self.tokenizer = AutoTokenizer.from_pretrained(self.args.judge_model, trust_remote_code=True)
        kwargs: dict[str, Any] = {
            "model": self.args.judge_model,
            "tensor_parallel_size": self.args.judge_tensor_parallel_size,
            "gpu_memory_utilization": self.args.judge_gpu_memory_utilization,
            "max_num_seqs": self.args.judge_max_num_seqs,
            "max_num_batched_tokens": self.args.judge_max_num_batched_tokens,
            "attention_backend": self.args.attention_backend,
            "trust_remote_code": True,
            "seed": 0,
        }
        if self.args.judge_max_model_len is not None:
            kwargs["max_model_len"] = self.args.judge_max_model_len
        self.llm = LLM(**kwargs)

    def chat_prompt(self, prompt: str) -> str:
        self._ensure_loaded()
        assert self.tokenizer is not None
        messages = [{"role": "user", "content": prompt}]
        try:
            return self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
        except TypeError:
            return self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    def run_cached(
        self,
        *,
        output_dir: Path,
        prompts: list[tuple[str, str]],
        cache_name: str,
        max_tokens: int | None = None,
        temperature: float = 0.0,
        top_p: float = 1.0,
        no_resume: bool = False,
        desc: str = "local judge",
    ) -> dict[str, dict[str, Any]]:
        runner, _ = _import_vlmeval_runner()
        from vllm import SamplingParams

        output_dir.mkdir(parents=True, exist_ok=True)
        cache_path = output_dir / cache_name
        if no_resume and cache_path.exists():
            cache_path.unlink()
        existing = {} if no_resume else runner.load_jsonl_by_index(cache_path)
        pending = [(idx, prompt) for idx, prompt in prompts if str(idx) not in existing]
        print(
            "[judge:cached] "
            f"cache={cache_path} rows={len(prompts)} existing={len(existing)} pending={len(pending)}"
        )
        if pending:
            self._ensure_loaded()
            assert self.llm is not None
            sampling = SamplingParams(
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens if max_tokens is not None else self.args.judge_max_tokens,
            )
            total_batches = math.ceil(len(pending) / self.args.judge_batch_size)
            for start in tqdm(range(0, len(pending), self.args.judge_batch_size), total=total_batches, desc=desc):
                batch = pending[start:start + self.args.judge_batch_size]
                llm_prompts = [self.chat_prompt(prompt) for _, prompt in batch]
                outputs = self.llm.generate(llm_prompts, sampling_params=sampling, use_tqdm=False)
                rows = []
                for (idx, _), out in zip(batch, outputs):
                    rows.append(
                        {
                            "index": str(idx),
                            "judge_output": out.outputs[0].text.strip(),
                            "judge_finish_reason": out.outputs[0].finish_reason,
                            "judge_output_token_count": len(out.outputs[0].token_ids),
                        }
                    )
                runner.append_jsonl(cache_path, rows)
        return runner.load_jsonl_by_index(cache_path)

    def cleanup(self) -> None:
        runner, _ = _import_vlmeval_runner()
        runner.cleanup_vllm_engine(self.llm)
        self.llm = None
        self.tokenizer = None


def _namespace_for_spec(args: argparse.Namespace, spec: BenchmarkSpec, output_dir: Path, model_path: str) -> SimpleNamespace:
    return SimpleNamespace(
        dataset=spec.alias,
        model=model_path,
        output_dir=output_dir,
        no_resume=args.no_resume,
        eval_judge_model=args.eval_judge_model,
        eval_nproc=args.eval_nproc,
        judge_model=args.judge_model,
        judge_gpu=args.gpu,
        judge_tensor_parallel_size=args.judge_tensor_parallel_size,
        judge_gpu_memory_utilization=args.judge_gpu_memory_utilization,
        judge_max_model_len=args.judge_max_model_len,
        judge_max_num_seqs=args.judge_max_num_seqs,
        judge_max_num_batched_tokens=args.judge_max_num_batched_tokens,
        judge_batch_size=args.judge_batch_size,
        judge_max_tokens=args.judge_max_tokens,
        attention_backend=args.attention_backend,
    )


def _copy_score_to_benchmark(spec: BenchmarkSpec, model_slug: str, run_output_dir: Path, benchmark_root: Path) -> Path:
    src = run_output_dir / "scores.json"
    if not src.exists():
        raise FileNotFoundError(src)
    dst = score_path(spec, model_slug, benchmark_root)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst


def _run_direct_vlmeval(args: argparse.Namespace, spec: BenchmarkSpec, model_path: str, output_dir: Path) -> dict[str, Any]:
    runner, _ = _import_vlmeval_runner()
    ns = _namespace_for_spec(args, spec, output_dir, model_path)
    return runner.run_vlmeval_evaluate(ns)


def _run_local_math_like(
    args: argparse.Namespace,
    spec: BenchmarkSpec,
    model_path: str,
    output_dir: Path,
    judge: PersistentJudge,
) -> dict[str, Any]:
    runner, _ = _import_vlmeval_runner()
    ns = _namespace_for_spec(args, spec, output_dir, model_path)
    old = runner._run_local_text_judge

    def persistent_text_judge(call_args, *, prompts, cache_name, max_tokens=None, temperature=0.0, top_p=1.0):
        return judge.run_cached(
            output_dir=call_args.output_dir,
            prompts=prompts,
            cache_name=cache_name,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            no_resume=call_args.no_resume,
            desc=f"{call_args.dataset} local judge",
        )

    runner._run_local_text_judge = persistent_text_judge
    try:
        mode = local_judge_eval_mode(spec)
        if mode == "mathv_local_judge":
            return runner.run_mathv_local_judge(ns)
        if mode == "mathvista_local_judge":
            return runner.run_mathvista_local_judge(ns)
        if mode == "mathverse_local_judge":
            return runner.run_mathverse_local_judge(ns)
        if mode == "logicvista_local_judge":
            return runner.run_logicvista_local_judge(ns)
        raise ValueError(f"Unsupported math-like local judge mode for {spec.key}: {mode}")
    finally:
        runner._run_local_text_judge = old


def _run_charxiv_local_judge(
    args: argparse.Namespace,
    spec: BenchmarkSpec,
    model_path: str,
    output_dir: Path,
    judge: PersistentJudge,
) -> dict[str, Any]:
    runner, _ = _import_vlmeval_runner()
    from vlmeval.dataset import build_dataset
    from vlmeval.dataset.charxiv import qid2category
    from vlmeval.smp import load

    pred_table = output_dir / f"{spec.alias}_predictions.xlsx"
    if not pred_table.exists():
        raise FileNotFoundError(pred_table)
    data = load(str(pred_table))
    _ = build_dataset(spec.alias)
    judge_jsonl = output_dir / "judge_qwen3_32b.jsonl"
    if args.no_resume and judge_jsonl.exists():
        judge_jsonl.unlink()
    existing = {} if args.no_resume else runner.load_jsonl_by_index(judge_jsonl)
    pending = data[~data["index"].astype(str).isin(existing)].copy()

    print(f"[charxiv judge] dataset={spec.alias} rows={len(data)} existing={len(existing)} pending={len(pending)}")
    prompts: list[tuple[str, str]] = []
    for _, row in pending.iterrows():
        prompts.append((str(row["index"]), str(row["grading_query"]).replace("{PREDICTION}", str(row["prediction"]))))
    raw = judge.run_cached(
        output_dir=output_dir,
        prompts=prompts,
        cache_name="judge_qwen3_32b.jsonl",
        max_tokens=args.judge_max_tokens,
        temperature=0.0,
        top_p=1.0,
        no_resume=False,
        desc=f"{spec.alias} judge",
    )
    judged_map = {**existing, **raw}
    for idx, item in list(judged_map.items()):
        if "score" not in item:
            parsed = runner._parse_charxiv_judge(str(item.get("judge_output", "")))
            item["score"] = parsed["score"]
            item["extract_answer"] = parsed["extract_answer"]
            judged_map[idx] = item
    data["score"] = [float(judged_map[str(x)]["score"]) for x in data["index"]]
    data["extract_answer"] = [judged_map[str(x)]["extract_answer"] for x in data["index"]]
    judged_xlsx = output_dir / f"{spec.alias}_judged_qwen3_32b.xlsx"
    data.to_excel(judged_xlsx, index=False)

    mode = "descriptive" if "descriptive" in spec.alias else "reasoning"
    category_map, index_col = qid2category(mode)
    buckets: dict[str, list[float]] = defaultdict(list)
    for _, row in data.iterrows():
        buckets[str(category_map[row[index_col]])].append(float(row["score"]))
    scores = {k: sum(v) / len(v) for k, v in sorted(buckets.items())}
    scores["Overall"] = sum(float(x) for x in data["score"]) / len(data)
    summary = {
        "dataset": spec.alias,
        "model": model_path,
        "judge_model": args.judge_model,
        "rows": len(data),
        "scores": scores,
        "judge": {"temperature": 0.0, "top_p": 1.0, "max_tokens": args.judge_max_tokens, "thinking": "disabled via chat template enable_thinking=False when supported"},
        "artifacts": {"prediction_table": str(pred_table), "judge_jsonl": str(judge_jsonl), "judged_xlsx": str(judged_xlsx)},
    }
    write_json(output_dir / "scores.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=json_default))
    return summary


def _run_chartmuseum_local_judge(
    args: argparse.Namespace,
    spec: BenchmarkSpec,
    model_path: str,
    output_dir: Path,
    judge: PersistentJudge,
) -> dict[str, Any]:
    _, chartmuseum = _import_vlmeval_runner()
    jsonl_path = output_dir / "predictions.jsonl"
    if not jsonl_path.exists():
        raise FileNotFoundError(jsonl_path)
    rows = list(chartmuseum.load_existing(jsonl_path).values())
    rows.sort(key=lambda x: int(x["index"]))
    judge_path = output_dir / "judge_qwen32b.jsonl"
    if args.no_resume and judge_path.exists():
        judge_path.unlink()
    existing = {} if args.no_resume else chartmuseum.load_existing(judge_path)
    pending = [r for r in rows if str(r["index"]) not in existing]
    print(f"[chartmuseum judge] rows={len(rows)} existing={len(existing)} pending={len(pending)}")

    prompts = [(str(item["index"]), chartmuseum.format_compare_prompt(item["question"], item["answer"], item.get("prediction", ""))) for item in pending]
    raw = judge.run_cached(
        output_dir=output_dir,
        prompts=prompts,
        cache_name="judge_qwen32b.jsonl",
        max_tokens=64,
        temperature=0.0,
        top_p=1.0,
        no_resume=False,
        desc="ChartMuseum judge",
    )
    judged_map = {**existing, **raw}
    judged_rows = []
    for row in rows:
        item = dict(row)
        judged = judged_map[str(row["index"])]
        item["judge_model"] = args.judge_model
        item["judge_output"] = judged.get("judge_output", "")
        item["score"] = 1.0 if chartmuseum.parse_judge_output(str(item["judge_output"])) else 0.0
        item["judge_output_token_count"] = judged.get("judge_output_token_count", 0)
        item["judge_finish_reason"] = judged.get("judge_finish_reason", "")
        judged_rows.append(item)

    overall = sum(float(x["score"]) for x in judged_rows) / len(judged_rows)
    breakdown_counts: dict[str, list[float]] = defaultdict(list)
    for row in judged_rows:
        breakdown_counts[str(row.get("reasoning_type") or "unknown")].append(float(row["score"]))
    breakdown = {k: sum(v) / len(v) for k, v in sorted(breakdown_counts.items())}
    result_df = pd.DataFrame(judged_rows)
    result_df.to_json(output_dir / "judged_predictions.json", orient="records", force_ascii=False, indent=2)
    result_df.to_excel(output_dir / "judged_predictions.xlsx", index=False)
    scores = {
        "dataset": "ChartMuseum",
        "split": spec.split or "test",
        "model": model_path,
        "judge_model": args.judge_model,
        "rows": len(judged_rows),
        "accuracy": overall,
        "reasoning_type_accuracy": breakdown,
        "outputs": {
            "predictions_jsonl": str(jsonl_path),
            "official_predictions_json": str(output_dir / "official_predictions.json"),
            "judge_jsonl": str(judge_path),
            "judged_predictions_json": str(output_dir / "judged_predictions.json"),
            "judged_predictions_xlsx": str(output_dir / "judged_predictions.xlsx"),
        },
    }
    write_json(output_dir / "scores.json", scores)
    print(json.dumps(scores, indent=2, ensure_ascii=False, default=json_default))
    return scores


def _run_chartqapro_extracted_score(
    args: argparse.Namespace,
    spec: BenchmarkSpec,
    model_path: str,
    output_dir: Path,
) -> dict[str, Any]:
    scripts_root = VLMEVAL_ROOT / "scripts"
    if str(scripts_root) not in sys.path:
        sys.path.insert(0, str(scripts_root))
    import batched_chartqapro_vllm as chartqapro

    candidates = [
        output_dir / f"{spec.alias}_predictions_table.jsonl",
        output_dir / "predictions.jsonl",
    ]
    source_path = next((path for path in candidates if path.exists()), None)
    if source_path is None:
        raise FileNotFoundError(f"No ChartQAPro prediction jsonl found under {output_dir}")

    rows: list[dict[str, Any]] = []
    changed = 0
    missing_fields: list[str] = []
    with source_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            for key in ("answer", "question_type", "year"):
                if key not in row:
                    missing_fields.append(f"index={row.get('index')} missing={key}")
            raw = row.get("raw_prediction", row.get("prediction", ""))
            pred = chartqapro.extract_prediction(str(raw), str(row.get("question_type", "")))
            out = dict(row)
            out["raw_prediction"] = raw
            out["prediction"] = pred
            rows.append(out)
            if str(pred) != str(raw):
                changed += 1

    if missing_fields:
        preview = "; ".join(missing_fields[:5])
        raise ValueError(f"ChartQAPro predictions lack fields required for local scoring: {preview}")

    scores = chartqapro.evaluate_rows(rows, "prediction")
    extracted_jsonl = output_dir / f"{spec.alias}_predictions_extracted.jsonl"
    with extracted_jsonl.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, default=json_default) + "\n")
    extracted_xlsx = output_dir / f"{spec.alias}_predictions_extracted.xlsx"
    pd.DataFrame(rows).to_excel(extracted_xlsx, index=False)

    existing: dict[str, Any] = {}
    existing_path = output_dir / "scores.json"
    if existing_path.exists():
        try:
            existing = json.loads(existing_path.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
    summary = {
        **{k: v for k, v in existing.items() if k in {"generation", "elapsed_sec", "wall_time_sec_estimate"}},
        "dataset": "ChartQAPro",
        "model": model_path,
        "run_name": spec.run_name,
        "harness": "VLMEvalKit ChartQAPro with final-answer extraction",
        "prompt_setup": spec.alias,
        "rows": len(rows),
        "scores": scores,
        "extraction": {
            "source_predictions": str(source_path),
            "changed_predictions": changed,
            "unchanged_predictions": len(rows) - changed,
            "extractor": "batched_chartqapro_vllm.extract_prediction",
        },
        "artifacts": {
            "prediction_table": str(source_path),
            "extracted_predictions_jsonl": str(extracted_jsonl),
            "extracted_predictions_xlsx": str(extracted_xlsx),
        },
    }
    write_json(output_dir / "scores.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=json_default))
    return summary


def _run_score_for_spec(args: argparse.Namespace, spec: BenchmarkSpec, model_path: str, model_slug: str, judge: PersistentJudge) -> dict[str, Any]:
    output_dir = run_dir(spec, model_slug, args.run_root)
    mode = local_judge_eval_mode(spec)
    if spec.key == "chartqapro":
        summary = _run_chartqapro_extracted_score(args, spec, model_path, output_dir)
    elif mode == "chartmuseum_local_judge":
        summary = _run_chartmuseum_local_judge(args, spec, model_path, output_dir, judge)
    elif mode == "charxiv_local_judge":
        summary = _run_charxiv_local_judge(args, spec, model_path, output_dir, judge)
    elif mode in {"mathv_local_judge", "mathvista_local_judge", "mathverse_local_judge", "logicvista_local_judge"}:
        summary = _run_local_math_like(args, spec, model_path, output_dir, judge)
    else:
        summary = _run_direct_vlmeval(args, spec, model_path, output_dir)
    dst = _copy_score_to_benchmark(spec, model_slug, output_dir, args.benchmark_root)
    summary["benchmark_score_path"] = str(dst)
    return summary


def _maybe_write_screenspot_aggregate(model_slug: str, benchmark_root: Path) -> None:
    group_specs = [s for s in benchmark_specs_for_run_set("full") if s.aggregate_group == "screenspotpro"]
    if not group_specs:
        return
    paths = [score_path(spec, model_slug, benchmark_root) for spec in group_specs]
    if not all(path.exists() for path in paths):
        return
    rows_total = 0
    weighted = 0.0
    subset_scores = {}
    for spec, path in zip(group_specs, paths):
        obj = json.loads(path.read_text(encoding="utf-8"))
        score, rows = extract_score_and_rows(obj)
        if score is None or rows is None:
            return
        subset_scores[spec.display] = {"score": score, "rows": rows, "source": str(path)}
        rows_total += rows
        weighted += score * rows
    out = {
        "dataset": "ScreenSpotPro",
        "model_slug": model_slug,
        "rows": rows_total,
        "scores": {"Overall_Accuracy": weighted / rows_total if rows_total else None},
        "aggregation": "pooled sample-wise over ScreenSpot_Pro_* subsets",
        "subsets": subset_scores,
    }
    write_json(aggregate_score_path("screenspotpro", "vlmevalkit_defaults_pooled", model_slug, benchmark_root), out)


def run_worker(args: argparse.Namespace) -> None:
    if args.gpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu
    os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")
    os.environ.setdefault("VLLM_ATTENTION_BACKEND", args.attention_backend)

    specs = benchmark_specs_for_run_set(args.run_set, model_slug=args.model_slug)
    specs = filter_benchmark_specs(specs, only=args.only, exclude=args.exclude)
    queue_path = args.queue_root / f"score_{args.queue_name or args.model_slug + '_' + args.run_set}.json"
    jobs = [(spec.key, score_path(spec, args.model_slug, args.benchmark_root)) for spec in specs]
    print(
        "[score-worker:init] "
        f"model={args.model} slug={args.model_slug} gpu={os.environ.get('CUDA_VISIBLE_DEVICES', '')} "
        f"run_set={args.run_set} jobs={len(jobs)} queue={queue_path}"
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
                print("[score-worker:done] no remaining score jobs")
                break
            spec = spec_by_key(job_id)
            try:
                print(f"[score-worker:claim] {job_id}")
                summary = _run_score_for_spec(args, spec, args.model, args.model_slug, judge)
                mark_job(queue_path, job_id, "done", worker=args.worker_id, output_dir=str(run_dir(spec, args.model_slug, args.run_root)), rows=summary.get("rows"))
                _maybe_write_screenspot_aggregate(args.model_slug, args.benchmark_root)
            except Exception as exc:
                mark_job(queue_path, job_id, "failed", worker=args.worker_id, output_dir=str(run_dir(spec, args.model_slug, args.run_root)), error=repr(exc))
                if args.stop_on_error:
                    raise
                print(f"[score-worker:error] {job_id} failed and will be skipped by this worker: {exc!r}", file=sys.stderr)
    finally:
        judge.cleanup()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=BASE_MODEL_SPEC.path)
    parser.add_argument("--model-slug", default=BASE_MODEL_SPEC.slug)
    parser.add_argument("--run-set", choices=["full", "remaining_base", "base_all"], default="remaining_base")
    parser.add_argument("--gpu", default=os.environ.get("CUDA_VISIBLE_DEVICES", ""))
    parser.add_argument("--worker-id", default=f"score-{os.getpid()}")
    parser.add_argument("--queue-name", default="")
    parser.add_argument("--queue-root", type=Path, default=DEFAULT_QUEUE_ROOT)
    parser.add_argument("--run-root", type=Path, default=REPO_ROOT / "runs")
    parser.add_argument("--benchmark-root", type=Path, default=DEFAULT_BENCHMARK_ROOT)
    parser.add_argument("--only", nargs="*", default=[])
    parser.add_argument("--exclude", nargs="*", default=[])
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
    parser.add_argument("--attention-backend", default="FLASH_ATTN")
    parser.add_argument("--stale-after-sec", type=float, default=900)
    parser.add_argument("--max-attempts", type=int, default=2)
    parser.add_argument("--stop-on-error", action="store_true")
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args()
    run_worker(args)


if __name__ == "__main__":
    main()
