#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import os
import re
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd
import requests
from tqdm import tqdm

from benchmark_queue_lib import (
    BASE_MODEL_SPEC,
    BENCHMARK_RUN_SETS,
    DEFAULT_BENCHMARK_ROOT,
    DEFAULT_QUEUE_ROOT,
    REPO_ROOT,
    TRACE_CANDIDATE37_200_BENCHMARKS,
    TRACE_CANDIDATE37_200_QUEUE_SUFFIX,
    TRACE_GROUNDING_BENCHMARKS,
    VLMEVAL_ROOT,
    BenchmarkSpec,
    aggregate_score_path,
    benchmark_dir,
    benchmark_specs_for_run_set,
    build_vlmeval_dataset,
    claim_next_job,
    extract_score_and_rows,
    filter_benchmark_specs,
    grounding_preferred_score_and_rows,
    json_default,
    local_judge_eval_mode,
    mark_job,
    materialize_grounding_benchmark_files,
    run_dir,
    score_to_percent,
    score_path,
    spec_by_key,
    weighted_prefixed_overall_accuracy,
    write_json,
)
from trace_benchmark_answer_parsing import (  # noqa: E402
    extract_click_point,
    extract_final_answer,
    parse_binary_score as _strict_parse_binary_score,
)
from trace_final25_contract import (  # noqa: E402
    DEDICATED_SCORE_KEYS,
    DIRECT_SCORE_KEYS,
    LLM_EXTRACT_SCORE_KEYS,
)


def _import_vlmeval_runner():
    scripts_root = VLMEVAL_ROOT / "scripts"
    for path in (VLMEVAL_ROOT, scripts_root):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    import batched_vlmevalkit_qwen3vl as runner
    import batched_chartmuseum_vllm as chartmuseum

    return runner, chartmuseum


def _judge_cache_entry_needs_retry(row: dict[str, Any]) -> bool:
    output = str(row.get("judge_output", "")).strip()
    finish_reason = str(row.get("judge_finish_reason", "")).strip().lower()
    return not output or finish_reason in {"length", "max_tokens"}


def _judge_retry_token_limits(initial_max_tokens: int) -> list[int]:
    limit = max(128, int(initial_max_tokens))
    ceiling = max(1024, limit)
    limits = [limit]
    while limits[-1] < ceiling:
        limits.append(min(ceiling, limits[-1] * 2))
    return limits


class PersistentJudge:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.llm = None
        self.tokenizer = None
        self.api_tokenizer = None

    @property
    def api_bases(self) -> list[str]:
        return [str(item).rstrip("/") for item in (getattr(self.args, "judge_api_bases", None) or []) if str(item).strip()]

    def _using_api_pool(self) -> bool:
        return bool(self.api_bases)

    def _ensure_loaded(self) -> None:
        if self.llm is not None:
            return
        if self.args.gpu:
            os.environ["CUDA_VISIBLE_DEVICES"] = self.args.gpu
        os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")
        os.environ.setdefault("VLLM_ATTENTION_BACKEND", self.args.attention_backend)
        os.environ.setdefault("VLLM_DISABLE_COMPILE_CACHE", "1")

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

    def _ensure_api_tokenizer(self) -> None:
        if self.api_tokenizer is not None:
            return
        from transformers import AutoTokenizer

        tokenizer_model = getattr(self.args, "judge_api_tokenizer_model", None) or self.args.judge_model
        self.api_tokenizer = AutoTokenizer.from_pretrained(tokenizer_model, trust_remote_code=True)

    def api_chat_prompt(self, prompt: str) -> str:
        self._ensure_api_tokenizer()
        assert self.api_tokenizer is not None
        messages = [{"role": "user", "content": prompt}]
        try:
            return self.api_tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
        except TypeError:
            return self.api_tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    @staticmethod
    def _completion_url(base: str) -> str:
        base = base.rstrip("/")
        if base.endswith("/v1"):
            return f"{base}/completions"
        if base.endswith("/v1/completions"):
            return base
        return f"{base}/v1/completions"

    def _call_api_completion(
        self,
        endpoint: str,
        prompt: str,
        *,
        max_tokens: int | None,
        temperature: float,
        top_p: float,
    ) -> dict[str, Any]:
        payload = {
            "model": getattr(self.args, "judge_api_model", "qwen3-32b-judge"),
            "prompt": prompt,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens if max_tokens is not None else self.args.judge_max_tokens,
        }
        timeout = float(getattr(self.args, "judge_api_timeout", 120.0))
        max_retries = int(getattr(self.args, "judge_api_max_retries", 5))
        last_error: Exception | None = None
        for attempt in range(max_retries):
            try:
                response = requests.post(self._completion_url(endpoint), json=payload, timeout=timeout)
                response.raise_for_status()
                data = response.json()
                choice = data["choices"][0]
                return {
                    "judge_output": str(choice.get("text", "")).strip(),
                    "judge_finish_reason": choice.get("finish_reason"),
                    "judge_output_token_count": (data.get("usage") or {}).get("completion_tokens"),
                    "judge_api_endpoint": endpoint,
                }
            except Exception as exc:
                last_error = exc
                time.sleep(min(8.0, 0.5 * (2**attempt)))
        raise RuntimeError(f"{endpoint} failed after {max_retries} attempts: {last_error}")

    def _run_cached_api(
        self,
        *,
        output_dir: Path,
        prompts: list[tuple[str, str]],
        cache_name: str,
        max_tokens: int | None,
        temperature: float,
        top_p: float,
        no_resume: bool,
        desc: str,
    ) -> dict[str, dict[str, Any]]:
        runner, _ = _import_vlmeval_runner()

        output_dir.mkdir(parents=True, exist_ok=True)
        cache_path = output_dir / cache_name
        if no_resume and cache_path.exists():
            cache_path.unlink()
        existing = {} if no_resume else runner.load_jsonl_by_index(cache_path)
        retry_ids = {
            str(idx)
            for idx, _ in prompts
            if str(idx) in existing and _judge_cache_entry_needs_retry(existing[str(idx)])
        }
        pending = [
            (idx, prompt)
            for idx, prompt in prompts
            if str(idx) not in existing or str(idx) in retry_ids
        ]
        endpoints = self.api_bases
        effective_max_tokens = max(
            128,
            int(max_tokens if max_tokens is not None else self.args.judge_max_tokens),
        )
        print(
            "[judge:api-cached] "
            f"cache={cache_path} rows={len(prompts)} existing={len(existing)} pending={len(pending)} "
            f"retry_incomplete={len(retry_ids)} max_tokens={effective_max_tokens} "
            f"endpoints={len(endpoints)} parallelism={getattr(self.args, 'judge_api_parallelism', 128)}"
        )
        if pending:
            rendered = {str(idx): self.api_chat_prompt(prompt) for idx, prompt in pending}

            def run_one(pos_item: tuple[int, tuple[str, str]]) -> dict[str, Any]:
                pos, (idx, _) = pos_item
                endpoint = endpoints[pos % len(endpoints)]
                result: dict[str, Any] = {}
                retry_count = 0
                for token_limit in _judge_retry_token_limits(effective_max_tokens):
                    result = self._call_api_completion(
                        endpoint,
                        rendered[str(idx)],
                        max_tokens=token_limit,
                        temperature=temperature,
                        top_p=top_p,
                    )
                    if not _judge_cache_entry_needs_retry(result):
                        break
                    retry_count += 1
                result["judge_retry_count"] = retry_count
                return {"index": str(idx), **result}

            max_workers = int(getattr(self.args, "judge_api_parallelism", 128))
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = [pool.submit(run_one, item) for item in enumerate(pending)]
                for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc=desc):
                    row = future.result()
                    runner.append_jsonl(cache_path, [row])
        return runner.load_jsonl_by_index(cache_path)

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
        if self._using_api_pool():
            return self._run_cached_api(
                output_dir=output_dir,
                prompts=prompts,
                cache_name=cache_name,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                no_resume=no_resume,
                desc=desc,
            )
        runner, _ = _import_vlmeval_runner()
        from vllm import SamplingParams

        output_dir.mkdir(parents=True, exist_ok=True)
        cache_path = output_dir / cache_name
        if no_resume and cache_path.exists():
            cache_path.unlink()
        existing = {} if no_resume else runner.load_jsonl_by_index(cache_path)
        retry_ids = {
            str(idx)
            for idx, _ in prompts
            if str(idx) in existing and _judge_cache_entry_needs_retry(existing[str(idx)])
        }
        pending = [
            (idx, prompt)
            for idx, prompt in prompts
            if str(idx) not in existing or str(idx) in retry_ids
        ]
        effective_max_tokens = max(
            128,
            int(max_tokens if max_tokens is not None else self.args.judge_max_tokens),
        )
        print(
            "[judge:cached] "
            f"cache={cache_path} rows={len(prompts)} existing={len(existing)} pending={len(pending)} "
            f"retry_incomplete={len(retry_ids)} max_tokens={effective_max_tokens}"
        )
        if pending:
            self._ensure_loaded()
            assert self.llm is not None
            sampling = SamplingParams(
                temperature=temperature,
                top_p=top_p,
                max_tokens=effective_max_tokens,
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
        if self._using_api_pool():
            self.api_tokenizer = None
            return
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


def _sanitize_prediction_table_for_scoring(spec: BenchmarkSpec, output_dir: Path) -> None:
    """Normalize evaluator input cells that some VLMEvalKit scorers assume are strings."""
    if spec.alias != "TableVQABench":
        return
    pred_table = output_dir / f"{spec.alias}_predictions.xlsx"
    if not pred_table.exists():
        return
    data = pd.read_excel(pred_table)
    changed = False
    for col in ("prediction", "answer"):
        if col not in data:
            continue
        fill_value = "__missing_prediction__" if col == "prediction" else "__missing_answer__"
        normalized = data[col].fillna(fill_value).map(str)
        if not normalized.equals(data[col]):
            data[col] = normalized
            changed = True
    if changed:
        data.to_excel(pred_table, index=False)
        print(f"[score:sanitize] {spec.alias} cast prediction/answer cells to strings: {pred_table}")


def _run_tablevqabench_local_score(
    spec: BenchmarkSpec,
    model_path: str,
    output_dir: Path,
) -> dict[str, Any]:
    """Score TableVQABench after deterministic final-answer wrapper parsing."""

    _import_vlmeval_runner()
    from vlmeval.dataset.utils.tablevqabench import evaluate_fintabnet, evaluate_tabfact, evaluate_wtq

    pred_table = output_dir / f"{spec.alias}_predictions.xlsx"
    if not pred_table.exists():
        raise FileNotFoundError(pred_table)
    data = pd.read_excel(pred_table).copy()
    if "prediction" not in data or "answer" not in data or "split" not in data:
        raise ValueError(f"Malformed TableVQABench prediction table: {pred_table}")

    parsed = [extract_final_answer(value) for value in data["prediction"]]
    data["raw_prediction"] = data["prediction"]
    data["prediction"] = [answer if answer else "__missing_prediction__" for answer, _ in parsed]
    data["trace_extraction_method"] = [method for _, method in parsed]
    data["answer"] = data["answer"].fillna("__missing_answer__").map(str)

    scored_rows: list[dict[str, Any]] = []
    score_table: list[dict[str, Any]] = []
    all_reported_scores: list[float] = []
    for split, group in data.groupby("split", sort=True):
        records = group.to_dict(orient="records")
        if split == "fintabnetqa":
            meta = evaluate_fintabnet(records, ["accuracy"])
            metric_names = ["relieved_accuracy", "strict_accuracy"]
        elif split == "vtabfact":
            meta = evaluate_tabfact(records, ["accuracy"])
            metric_names = ["accuracy"]
        elif split in {"vwtq", "vwtq_syn"}:
            meta = evaluate_wtq(records, ["accuracy"])
            metric_names = ["accuracy"]
        else:
            raise ValueError(f"Unknown TableVQABench split {split!r}")
        values = [float(value) for value in meta.get("average_scores", [])]
        if len(values) != len(metric_names):
            raise ValueError(f"Unexpected TableVQABench metrics for {split}: {meta}")
        score_table.append(
            {
                "split": str(split),
                "rows": int(len(records)),
                **dict(zip(metric_names, values)),
                "average_scores": values,
            }
        )
        all_reported_scores.extend(values)
        scored_rows.extend(records)

    if len(scored_rows) != len(data) or not all_reported_scores:
        raise ValueError("TableVQABench scorer did not account for every row")
    overall = float(sum(all_reported_scores) / len(all_reported_scores))
    judged_table = output_dir / f"{spec.alias}_trace_final_answer_scored.xlsx"
    pd.DataFrame(scored_rows).to_excel(judged_table, index=False)
    scores = {"Overall": overall, "table": score_table}
    summary = {
        "dataset": spec.alias,
        "model": model_path,
        "run_name": spec.run_name,
        "harness": "TRACE final-answer parser plus official TableVQABench split scorers",
        "rows": int(len(data)),
        "score": overall,
        "scores": scores,
        "aggregation": "macro mean over all official split average_scores values",
        "extraction": {
            "method_counts": data["trace_extraction_method"].value_counts().to_dict(),
            "empty_predictions": int(sum(answer == "" for answer, _ in parsed)),
        },
        "artifacts": {"prediction_table": str(pred_table), "judged_table": str(judged_table)},
    }
    write_json(output_dir / "scores.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=json_default))
    return summary


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
    _patch_refspatial_point_parser(spec)
    _patch_screenspot_point_parser(spec)
    _sanitize_prediction_table_for_scoring(spec, output_dir)
    ns = _namespace_for_spec(args, spec, output_dir, model_path)
    summary = runner.run_vlmeval_evaluate(ns)
    if spec.key == "screenspot":
        summary["harness"] = "VLMEvalKit ScreenSpot point-in-box scorer with TRACE click parser"
        summary["parser"] = "pyautogui named/positional, answer tag, boxed, and coordinate-pair formats"
        write_json(output_dir / "scores.json", summary)
    return summary


def _preferred_direct_score(spec: BenchmarkSpec, summary: dict[str, Any]) -> float | None:
    """Return a benchmark-specific primary score when the generic normalizer is ambiguous."""

    scores = summary.get("scores")
    if not isinstance(scores, dict):
        return None

    if spec.key == "videommmu":
        table = scores.get("table")
        if not isinstance(table, list) or not table:
            return None
        # VideoMMMU returns a DataFrame indexed by total/hit/acc with
        # categories as columns. The generic adapter drops that index and
        # averages the Overall column, mixing counts with the percentage. The
        # final row is the accuracy row produced by aggregate_results().
        last_row = table[-1]
        return score_to_percent(last_row.get("Overall")) if isinstance(last_row, dict) else None

    if spec.key == "qbench_video":
        table = scores.get("table")
        if not isinstance(table, list):
            return None
        weighted_score = 0.0
        total_rows = 0.0
        for row in table:
            if not isinstance(row, dict):
                continue
            acc = score_to_percent(row.get("acc"))
            try:
                count = float(row.get("overall"))
            except (TypeError, ValueError):
                continue
            if acc is not None and count > 0:
                weighted_score += acc * count
                total_rows += count
        return weighted_score / total_rows if total_rows else None

    if spec.key == "video_tt":
        overall = scores.get("overall")
        return score_to_percent(overall.get("score")) if isinstance(overall, dict) else None

    return None


def _patch_refspatial_point_parser(spec: BenchmarkSpec) -> None:
    if not str(spec.alias).startswith("RefSpatial"):
        return
    try:
        from vlmeval.dataset.utils.spatial_bench.tools import utils as spatial_utils

        if not hasattr(spatial_utils.Point2DParser, "logger"):
            spatial_utils.Point2DParser.logger = spatial_utils.logger
    except Exception:
        pass


def _patch_screenspot_point_parser(spec: BenchmarkSpec) -> None:
    if spec.key != "screenspot":
        return
    from vlmeval.dataset.GUI import screenspot as screenspot_module

    def parse_point(response: Any) -> list[float]:
        point = extract_click_point(response)
        if point is None:
            raise ValueError(f"Could not parse ScreenSpot click point from response: {response!r}")
        return [float(point[0]), float(point[1])]

    screenspot_module.parse_bbox_aguvis = parse_point


def _run_vlmeval_evaluate_with_kwargs(
    args: argparse.Namespace,
    spec: BenchmarkSpec,
    model_path: str,
    output_dir: Path,
    *,
    judge_kwargs: dict[str, Any],
    harness: str,
) -> dict[str, Any]:
    runner, _ = _import_vlmeval_runner()
    from vlmeval.smp import load

    dataset = build_vlmeval_dataset(spec)
    candidates = [
        output_dir / f"{spec.alias}_predictions.xlsx",
        output_dir / "predictions.xlsx",
    ]
    pred_table = next((path for path in candidates if path.exists()), None)
    if pred_table is None:
        matches = sorted(output_dir.glob("*_predictions.xlsx"))
        pred_table = matches[0] if matches else candidates[0]
    if not pred_table.exists():
        raise FileNotFoundError(pred_table)
    _sanitize_prediction_table_for_scoring(spec, output_dir)
    result = dataset.evaluate(str(pred_table), **judge_kwargs)
    scores = runner._normalize_eval_result(result)
    summary = {
        "dataset": spec.alias,
        "model": model_path,
        "run_name": spec.run_name,
        "harness": harness,
        "rows": len(load(str(pred_table))),
        "score": runner._primary_score(scores),
        "scores": scores,
        "artifacts": {"prediction_table": str(pred_table)},
    }
    write_json(output_dir / "scores.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=json_default))
    return summary


def _extract_braced_answer(text: Any) -> str:
    text = str(text or "").strip()
    matches = re.findall(r"\{([^{}]+)\}", text)
    if matches:
        return matches[-1].strip()
    boxed = re.findall(r"\\boxed\{([^{}]+)\}", text)
    if boxed:
        return boxed[-1].strip()
    yes_no = re.findall(r"\b(yes|no)\b", text, flags=re.I)
    if yes_no:
        return yes_no[-1].strip()
    final = list(re.finditer(r"\b(?:final\s+answer|answer)\b\s*[:：]?\s*(.+)", text, flags=re.I | re.S))
    if final:
        return final[-1].group(1).strip().splitlines()[0].strip()
    return text


def _normalize_rule_answer(text: Any) -> str:
    value = _extract_braced_answer(text).lower().strip()
    value = re.sub(r"^[\"'`]+|[\"'`]+$", "", value)
    value = re.sub(r"\s+", " ", value)
    try:
        from vlmeval.dataset.utils.omni_verifier import _process_digit_article

        value = _process_digit_article(value)
    except Exception:
        value = re.sub(r"^(a|an|the)\s+", "", value)
    return value.strip(" .,:;")


def _run_vlmbias_rule_score(
    args: argparse.Namespace,
    spec: BenchmarkSpec,
    model_path: str,
    output_dir: Path,
) -> dict[str, Any]:
    _import_vlmeval_runner()
    from vlmeval.smp import load

    pred_table = output_dir / f"{spec.alias}_predictions.xlsx"
    if not pred_table.exists():
        raise FileNotFoundError(pred_table)
    data = load(str(pred_table))
    data["eval_pred"] = [_normalize_rule_answer(x) for x in data["prediction"]]
    data["eval_gt"] = [_normalize_rule_answer(x) for x in data["answer"]]
    data["hit"] = [float(p == g) for p, g in zip(data["eval_pred"], data["eval_gt"])]
    judged = output_dir / f"{spec.alias}_rule_judged.xlsx"
    data.to_excel(judged, index=False)
    overall = float(data["hit"].mean() * 100.0) if len(data) else 0.0
    scores: dict[str, Any] = {"Overall": overall, "Accuracy (%)": overall}
    for col in ("category", "sub_topic", "qtype"):
        if col in data:
            for key, group in data.groupby(col):
                scores[f"{col}/{key}"] = float(group["hit"].mean() * 100.0)
    summary = {
        "dataset": spec.alias,
        "model": model_path,
        "run_name": spec.run_name,
        "harness": "local rule-only brace/exact scorer",
        "rows": len(data),
        "score": overall,
        "scores": scores,
        "artifacts": {"prediction_table": str(pred_table), "judged_table": str(judged)},
    }
    write_json(output_dir / "scores.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=json_default))
    return summary


def _extract_option_letter(text: Any, *, choices: str = "ABCD") -> str:
    text = str(text or "").strip()
    braced = _extract_braced_answer(text)
    answer_patterns = [
        rf"<\s*answer\s*>\s*[:：]?\s*([{choices}])\b",
        rf"\b(?:final\s+answer|answer|option|choice|correct)\b\s*(?:is|:|：)?\s*([{choices}])\b",
    ]
    for candidate in (braced, text):
        stripped = candidate.strip().upper()
        if stripped in set(choices):
            return stripped
        for pattern in answer_patterns:
            match = re.search(pattern, candidate, flags=re.I)
            if match:
                return match.group(1).upper()
    matches = re.findall(rf"\b([{choices}])\b", text, flags=re.I)
    return matches[-1].upper() if matches else ""


def _run_wemath_subset_score(
    args: argparse.Namespace,
    spec: BenchmarkSpec,
    model_path: str,
    output_dir: Path,
) -> dict[str, Any]:
    _import_vlmeval_runner()
    from vlmeval.smp import load

    pred_table = output_dir / f"{spec.alias}_predictions.xlsx"
    if not pred_table.exists():
        raise FileNotFoundError(pred_table)
    data = load(str(pred_table))
    data["eval_pred"] = [_extract_option_letter(x, choices="ABCDEFG") for x in data["prediction"]]
    data["eval_gt"] = [_extract_option_letter(x, choices="ABCDEFG") for x in data["answer"]]
    data["hit"] = [float(p != "" and p == g) for p, g in zip(data["eval_pred"], data["eval_gt"])]

    judged = output_dir / f"{spec.alias}_subset_option_judged.xlsx"
    data.to_excel(judged, index=False)
    overall = float(data["hit"].mean() * 100.0) if len(data) else 0.0
    table: list[dict[str, Any]] = [{"Split": "Overall", "Accuracy (%)": overall, "Samples": int(len(data))}]
    for col in ("key", "split", "knowledge concept"):
        if col in data:
            for key, group in data.groupby(col, dropna=False):
                table.append(
                    {
                        "Split": f"{col}/{key}",
                        "Accuracy (%)": float(group["hit"].mean() * 100.0),
                        "Samples": int(len(group)),
                    }
                )

    score_csv = output_dir / f"{spec.alias}_subset_option_score.csv"
    pd.DataFrame(table).to_csv(score_csv, index=False)
    scores = {"accuracy": overall, "Overall": overall, "table": table}
    summary = {
        "dataset": spec.alias,
        "model": model_path,
        "run_name": spec.run_name,
        "harness": "TRACE subset-safe WeMath option-letter exact scorer",
        "rows": len(data),
        "score": overall,
        "scores": scores,
        "artifacts": {"prediction_table": str(pred_table), "judged_table": str(judged), "score_csv": str(score_csv)},
    }
    write_json(output_dir / "scores.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=json_default))
    return summary


def _run_physics_subset_score(
    args: argparse.Namespace,
    spec: BenchmarkSpec,
    model_path: str,
    output_dir: Path,
    judge: PersistentJudge,
) -> dict[str, Any]:
    _import_vlmeval_runner()
    from vlmeval.dataset.utils.physic import PHYSIC_acc
    from vlmeval.dataset.utils.physics_eval_utils import extract_final_answer_allform
    from vlmeval.smp import load

    pred_table = output_dir / f"{spec.alias}_predictions.xlsx"
    if not pred_table.exists():
        raise FileNotFoundError(pred_table)
    data = load(str(pred_table))
    rows = []
    prompts = []
    for _, row in data.iterrows():
        row = row.copy()
        extract_error = ""
        prediction_text = str(row.get("prediction", ""))
        try:
            preds = extract_final_answer_allform(prediction_text)
        except Exception as exc:
            extract_error = f"{type(exc).__name__}: {exc}"
            preds = re.findall(r"\\boxed\{([^{}]*)\}", prediction_text, flags=re.S)
        flat: list[str] = []
        for item in preds:
            if isinstance(item, (list, tuple)):
                flat.extend(str(x).strip() for x in item if str(x).strip())
            elif str(item).strip():
                flat.append(str(item).strip())
        gt = str(row.get("answer", "")).strip()
        if gt and any(p == gt for p in flat):
            row["res"] = 1.0
            row["log"] = "Exact boxed match"
        elif flat:
            prompt = (
                "Compare the model answer to the standard answer for this physics problem. "
                "Return only True or False.\n\n"
                f"Question: {row.get('question', '')}\n"
                f"Standard answer: {gt}\n"
                f"Model answer: {flat[0]}\n"
                "Equivalent:"
            )
            prompts.append((str(row["index"]), prompt))
            row["res"] = 0.0
            row["log"] = "Pending local judge"
        else:
            row["res"] = 0.0
            row["log"] = f"Box extraction failed: {extract_error}" if extract_error else "No boxed answer"
        rows.append(row.to_dict())

    judged = judge.run_cached(
        output_dir=output_dir,
        prompts=prompts,
        cache_name="physics_qwen3_32b_score.jsonl",
        max_tokens=16,
        no_resume=args.no_resume,
        desc=f"{spec.alias} local judge",
    )
    malformed_judgements: list[str] = []
    for row in rows:
        if row["log"] == "Pending local judge":
            out = str(judged.get(str(row["index"]), {}).get("judge_output", "")).strip()
            parsed = _strict_parse_binary_score(out)
            if parsed is None:
                malformed_judgements.append(str(row["index"]))
                continue
            row["res"] = parsed
            row["log"] = f"Judge output: {out}"

    if malformed_judgements:
        raise RuntimeError(
            "Physics judge produced malformed decisions for "
            f"{len(malformed_judgements)} rows; first indices={malformed_judgements[:10]}"
        )

    judged_table = output_dir / f"{spec.alias}_judged_qwen3_32b.xlsx"
    pd.DataFrame(rows).to_excel(judged_table, index=False)
    score_df = PHYSIC_acc(str(judged_table))
    score_csv = output_dir / f"{spec.alias}_judged_qwen3_32b_score.csv"
    score_df.to_csv(score_csv, index=False)
    scores = {
        "table": score_df.to_dict(orient="records"),
        "Overall": float(score_df.loc[score_df["Subject"] == "Overall", "acc"].iloc[0])
        if "Overall" in set(score_df["Subject"])
        else None,
    }
    summary = {
        "dataset": spec.alias,
        "model": model_path,
        "run_name": spec.run_name,
        "harness": "TRACE local Physics boxed-answer scorer with timeout-safe extraction",
        "rows": len(rows),
        "score": scores["Overall"],
        "scores": scores,
        "artifacts": {"prediction_table": str(pred_table), "judged_table": str(judged_table), "score_csv": str(score_csv)},
    }
    write_json(output_dir / "scores.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=json_default))
    return summary


def _run_phyx_option_score(
    args: argparse.Namespace,
    spec: BenchmarkSpec,
    model_path: str,
    output_dir: Path,
) -> dict[str, Any]:
    _import_vlmeval_runner()
    from vlmeval.smp import load

    pred_table = output_dir / f"{spec.alias}_predictions.xlsx"
    if not pred_table.exists():
        raise FileNotFoundError(pred_table)
    data = load(str(pred_table))
    data["eval_pred"] = [_extract_option_letter(x, choices="ABCD") for x in data["prediction"]]
    data["eval_gt"] = [_extract_option_letter(x, choices="ABCD") for x in data["answer"]]
    data["hit"] = [float(p != "" and p == g) for p, g in zip(data["eval_pred"], data["eval_gt"])]
    judged = output_dir / f"{spec.alias}_option_judged.xlsx"
    data.to_excel(judged, index=False)
    overall = float(data["hit"].mean() * 100.0) if len(data) else 0.0
    scores: dict[str, Any] = {"Overall": overall, "Accuracy (%)": overall}
    for col in ("category", "subfield", "reasoning_type"):
        if col in data:
            for key, group in data.groupby(col):
                scores[f"{col}/{key}"] = float(group["hit"].mean() * 100.0)
    summary = {
        "dataset": spec.alias,
        "model": model_path,
        "run_name": spec.run_name,
        "harness": "local option-letter exact scorer",
        "rows": len(data),
        "score": overall,
        "scores": scores,
        "artifacts": {"prediction_table": str(pred_table), "judged_table": str(judged)},
    }
    write_json(output_dir / "scores.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=json_default))
    return summary


def _parse_binary_judgement_output(value: Any) -> int | None:
    parsed = _strict_parse_binary_score(value)
    return int(parsed) if parsed is not None else None


def _parse_chartmuseum_judgement_output(value: Any) -> int | None:
    """Parse ChartMuseum's explicit Yes/No contract without inferring from prose."""

    parsed = _parse_binary_judgement_output(value)
    if parsed is not None:
        return parsed

    text = str(value or "").strip()
    leading = re.match(
        r"^(?:\*{1,3}|_{1,3})?\s*(yes|no)\s*(?:\*{1,3}|_{1,3})?(?:\s|[.!,:;\-]|$)",
        text,
        flags=re.I,
    )
    if leading:
        return 1 if leading.group(1).lower() == "yes" else 0

    final = re.search(
        r"(?:final\s+answer|response)\s*:\s*(?:\*{1,3}|_{1,3})?\s*(yes|no)\b",
        text,
        flags=re.I,
    )
    if final:
        return 1 if final.group(1).lower() == "yes" else 0
    return None


def _parse_json_object(text: Any) -> dict[str, Any]:
    raw = str(text or "").strip()
    if not raw:
        return {}
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    match = re.search(r"\{.*?\}", raw, flags=re.S)
    if match:
        try:
            obj = json.loads(match.group(0))
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
    return {}


def _resolve_charxiv_extracted_answer(
    item: dict[str, Any],
    parsed: dict[str, Any],
    prediction: Any,
) -> tuple[str, str]:
    extracted = str(item.get("extract_answer", parsed.get("extract_answer", ""))).strip()
    if extracted:
        return extracted, "judge"

    if prediction is None or (isinstance(prediction, float) and math.isnan(prediction)):
        return "", "empty_prediction"
    fallback, method = extract_final_answer(prediction)
    if fallback:
        return fallback, f"deterministic_{method}"
    return "", "empty_prediction"


def _parse_binary_score(value: Any) -> float | None:
    return _strict_parse_binary_score(value)


def _resolve_evochart_judgement(output: Any, prediction: Any) -> tuple[float | None, str, str]:
    text = str(output or "")
    obj = _parse_json_object(text)
    score = _parse_binary_score(obj.get("score", obj.get("judgement", obj.get("judgment"))))
    if score is None:
        score_match = re.search(r'"score"\s*:\s*([01])(?:\.0+)?\b', text, flags=re.I)
        score = float(score_match.group(1)) if score_match else None

    extracted = str(obj.get("extracted_answer", obj.get("answer", ""))).strip()
    if extracted:
        return score, extracted, "judge_json"
    if prediction is None or (isinstance(prediction, float) and math.isnan(prediction)):
        return score, "", "empty_prediction"
    fallback, method = extract_final_answer(prediction)
    return score, fallback, f"deterministic_{method}" if fallback else "empty_prediction"


def _parse_shortqa_correctness_output(value: Any) -> tuple[float, str]:
    text = str(value or "").strip()
    correct_st, correct_ed = "[Begin Correctness]", "[End Correctness]"
    reason_st, reason_ed = "[Begin Reason]", "[End Reason]"
    reason = ""
    if reason_st in text and reason_ed in text:
        reason = text.split(reason_st, 1)[1].split(reason_ed, 1)[0].strip()
    if correct_st in text and correct_ed in text:
        correctness = text.split(correct_st, 1)[1].split(correct_ed, 1)[0].strip().lower()
        has_yes = "yes" in correctness
        has_no = "no" in correctness
        if has_yes ^ has_no:
            return (1.0 if has_yes else 0.0), reason

    obj = _parse_json_object(text)
    for key in ("correctness", "correct", "score", "judgement", "judgment", "hit"):
        if key not in obj:
            continue
        parsed = _parse_binary_score(obj.get(key))
        if parsed is not None:
            return parsed, reason or str(obj.get("reason", "")).strip()

    parsed = _parse_binary_score(text)
    if parsed is not None:
        return parsed, reason
    lowered = text.lower()
    if re.search(r"\b(correct|yes)\b", lowered) and not re.search(r"\b(incorrect|wrong|no)\b", lowered):
        return 1.0, reason
    if re.search(r"\b(incorrect|wrong|no)\b", lowered):
        return 0.0, reason
    return 0.0, reason or "Failed to parse judge correctness"


def _mcq_choice_labels(row: pd.Series) -> list[str]:
    return [label for label in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if label in row and pd.notna(row[label])]


def _extract_final_mcq_option(text: Any, choices: list[str]) -> tuple[str, str]:
    """Extract an explicit final MCQ option from verbose CoT-style answers."""

    if not choices:
        return "Z", "no_choices"
    value = str(text or "").replace("\r", "\n")
    labels = "".join(re.escape(label) for label in choices)
    marker_patterns = (
        rf"(?is)(?:\*\*)?\s*(?:final\s+answer|correct\s+answer|answer)"
        rf"\s*(?:is)?\s*:?\s*(?:\*\*)?\s*:?\s*"
        rf"(?:\*\*)?\(?([{labels}])\)?(?:\*\*)?\s*(?:[\.\):\-]|$)",
        rf"(?is)(?:therefore|thus|so),?\s*(?:the\s+)?(?:\*\*)?\s*"
        rf"(?:final\s+)?(?:correct\s+)?answer\s*(?:is)?\s*:?\s*(?:\*\*)?\s*:?\s*"
        rf"(?:\*\*)?\(?([{labels}])\)?(?:\*\*)?\s*(?:[\.\):\-]|$)",
        rf"(?is)(?:final\s+answer|correct\s+answer|answer)[\s\S]{{0,160}}?"
        rf"(?:\*\*)?\(?([{labels}])\)?(?:\*\*)?\s*[\.\)]",
    )
    matches: list[re.Match[str]] = []
    for pattern in marker_patterns:
        matches.extend(re.finditer(pattern, value))
    if matches:
        matches.sort(key=lambda match: match.start())
        return matches[-1].group(1).upper(), "answer_marker"

    tail = value[-1600:]
    line_matches = list(
        re.finditer(
            rf"(?im)^\s*(?:[-*]\s*)?(?:\*\*)?([{labels}])(?:\*\*)?\s*[\.\):]\s+",
            tail,
        )
    )
    if line_matches:
        return line_matches[-1].group(1).upper(), "tail_line_start"

    if len(re.findall(r"\S+", value)) <= 40:
        short_match = re.search(rf"(?<![A-Za-z])([{labels}])\s*[\.\):]\s+", value)
        if short_match:
            return short_match.group(1).upper(), "short_option"

    lines = [line.strip() for line in value.splitlines() if line.strip()]
    for line in reversed(lines[-8:]):
        line_match = re.search(rf"^(?:\*\*)?([{labels}])(?:\*\*)?(?:\s*[\.\):]|\s*$)", line)
        if line_match:
            return line_match.group(1).upper(), "last_line"
    return "Z", "unparsed"


def _run_scienceqa_local_score(
    args: argparse.Namespace,
    spec: BenchmarkSpec,
    model_path: str,
    output_dir: Path,
) -> dict[str, Any]:
    direct_summary = _run_direct_vlmeval(args, spec, model_path, output_dir)
    pred_table = output_dir / f"{spec.alias}_predictions.xlsx"
    exact_table = output_dir / f"{spec.alias}_predictions_exact_matching_result.xlsx"
    if not pred_table.exists():
        raise FileNotFoundError(pred_table)
    if not exact_table.exists():
        raise FileNotFoundError(exact_table)

    predictions = pd.read_excel(pred_table)
    exact = pd.read_excel(exact_table)
    exact_cols = exact[["index", "hit", "log"]].rename(columns={"hit": "exact_hit", "log": "exact_log"})
    data = predictions.merge(exact_cols, on="index", how="left")
    if data["exact_hit"].isna().any():
        missing = int(data["exact_hit"].isna().sum())
        raise ValueError(f"{missing} ScienceQA rows missing exact-matching score")

    fallback_opts: list[str] = []
    fallback_methods: list[str] = []
    fallback_hits: list[int] = []
    final_hits: list[int] = []
    used_fallback: list[bool] = []
    for _, row in data.iterrows():
        choices = _mcq_choice_labels(row)
        option, method = _extract_final_mcq_option(row["prediction"], choices)
        target = str(row["answer"]).strip().upper()
        fallback_hit = int(option == target)
        exact_failed = "Failed in Prefetch" in str(row["exact_log"])
        fallback_opts.append(option)
        fallback_methods.append(method)
        fallback_hits.append(fallback_hit)
        used_fallback.append(exact_failed)
        final_hits.append(fallback_hit if exact_failed else int(row["exact_hit"]))

    data["fallback_option"] = fallback_opts
    data["fallback_method"] = fallback_methods
    data["fallback_hit"] = fallback_hits
    data["used_trace_fallback"] = used_fallback
    data["hit"] = final_hits
    data["log"] = [
        (
            f"TRACE fallback: opt={opt} method={method}; exact_log={log}"
            if used
            else str(log)
        )
        for opt, method, used, log in zip(fallback_opts, fallback_methods, used_fallback, data["exact_log"])
    ]

    from vlmeval.dataset.utils.multiple_choice import report_acc

    acc_df = report_acc(data.copy())
    corrected_table = output_dir / f"{spec.alias}_predictions_trace_mcq_fallback_result.xlsx"
    corrected_csv = output_dir / f"{spec.alias}_predictions_trace_mcq_fallback_acc.csv"
    data.to_excel(corrected_table, index=False)
    acc_df.to_csv(corrected_csv, index=False)
    overall = float(data["hit"].mean() * 100.0)
    exact_overall = float(data["exact_hit"].mean() * 100.0)
    fallback_rows = int(data["used_trace_fallback"].sum())
    fallback_recovered = int(((data["used_trace_fallback"]) & (data["fallback_hit"] == 1)).sum())
    scores_obj = {
        "Overall": overall,
        "table": acc_df.to_dict(orient="records"),
        "vlmeval_exact_matching_overall": exact_overall,
        "fallback_rows": fallback_rows,
        "fallback_recovered": fallback_recovered,
        "fallback_method_counts": data.loc[data["used_trace_fallback"], "fallback_method"].value_counts().to_dict(),
    }
    summary = {
        "dataset": spec.alias,
        "model": model_path,
        "run_name": spec.run_name,
        "harness": "TRACE ScienceQA direct MCQ scorer with final-answer fallback",
        "rows": len(data),
        "score": overall,
        "scores": scores_obj,
        "direct_vlmeval_summary": direct_summary,
        "artifacts": {
            "prediction_table": str(pred_table),
            "exact_matching_table": str(exact_table),
            "trace_fallback_table": str(corrected_table),
            "trace_fallback_score_csv": str(corrected_csv),
        },
    }
    write_json(output_dir / "scores.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=json_default))
    return summary


def _truthy_score(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes"}


def _normalize_mathverse_score_table(score_df: pd.DataFrame) -> dict[str, Any]:
    records = json.loads(score_df.to_json(orient="records"))
    scores: dict[str, Any] = {"table": records}
    if records:
        row = records[0]
        for key, value in row.items():
            if key != "split":
                scores[key] = value
    return scores


def _repair_mathverse_binary_judgement_summary(
    spec: BenchmarkSpec,
    model_path: str,
    output_dir: Path,
    summary: dict[str, Any],
) -> dict[str, Any]:
    if spec.key != "mathverse":
        return summary
    judged_table = output_dir / f"{spec.alias}_judged_qwen3_32b.xlsx"
    if not judged_table.exists():
        return summary

    from vlmeval.dataset.utils.mathverse import MathVerse_acc
    from vlmeval.smp import dump, get_intermediate_file_path

    # Preserve literal judge answers such as "None". Pandas otherwise coerces
    # those Excel strings to NaN and reports a successful extraction as empty.
    df = pd.read_excel(judged_table, keep_default_na=False)
    if "score" not in df or "log_score" not in df:
        return summary

    missing_extract = [
        str(row.get("index"))
        for _, row in df.iterrows()
        if pd.isna(row.get("extract")) or not str(row.get("extract", "")).strip()
    ]
    if missing_extract:
        raise RuntimeError(
            f"MathVerse judge produced {len(missing_extract)} empty extractions; first indices={missing_extract[:10]}"
        )

    repaired: list[bool] = []
    changed = 0
    malformed: list[str] = []
    for _, row in df.iterrows():
        current = _truthy_score(row["score"])
        log_score = str(row.get("log_score", ""))
        if log_score == "Prefetch succeed":
            repaired.append(True)
            continue
        judgement = _parse_binary_judgement_output(log_score)
        if judgement is None:
            malformed.append(str(row.get("index")))
            repaired.append(current)
            continue
        fixed = judgement == 1
        if fixed != current:
            changed += 1
        repaired.append(fixed)

    if malformed:
        raise RuntimeError(
            f"MathVerse judge produced {len(malformed)} malformed score decisions; first indices={malformed[:10]}"
        )

    df["score"] = repaired
    df.to_excel(judged_table, index=False)
    score_df = MathVerse_acc(str(judged_table))
    dump(score_df, str(get_intermediate_file_path(str(judged_table), "_score", "csv")))
    scores = _normalize_mathverse_score_table(score_df)
    repaired_summary = {
        "dataset": spec.alias,
        "model": model_path,
        "rows": len(df),
        "score": float(scores.get("Overall", 0.0)),
        "scores": scores,
        "artifacts": {
            **(summary.get("artifacts") or {}),
            "judged_table": str(judged_table),
            "mathverse_repaired_binary_judgement_rows": changed,
            "mathverse_validated_judge_rows": int(len(df)),
        },
    }
    write_json(output_dir / "scores.json", repaired_summary)
    print(json.dumps(repaired_summary, indent=2, ensure_ascii=False, default=json_default))
    return repaired_summary


def _validate_math_like_judged_table(spec: BenchmarkSpec, output_dir: Path) -> None:
    judged_table = output_dir / f"{spec.alias}_judged_qwen3_32b.xlsx"
    if not judged_table.exists():
        raise FileNotFoundError(judged_table)
    # Preserve literal judge answers such as "None". They are valid non-empty
    # extraction outputs even when the benchmark scorer later marks them wrong.
    data = pd.read_excel(judged_table, keep_default_na=False)
    if spec.key in {"mathvision", "mathvista"}:
        bad = data["res"].isna() | data["res"].astype(str).str.strip().eq("")
        if bad.any():
            indices = data.loc[bad, "index"].astype(str).tolist()
            raise RuntimeError(
                f"{spec.display} judge produced {len(indices)} empty extractions; first indices={indices[:10]}"
            )
    elif spec.key == "logicvista":
        values = data["res"].fillna("").astype(str).str.strip().str.upper()
        bad = values.eq("") | ~values.map(lambda value: set(value) <= set("ABCDEFGHIJKZ"))
        if bad.any():
            indices = data.loc[bad, "index"].astype(str).tolist()
            raise RuntimeError(
                f"LogicVista judge produced {len(indices)} malformed option extractions; first indices={indices[:10]}"
            )


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
            summary = runner.run_mathv_local_judge(ns)
        elif mode == "mathvista_local_judge":
            summary = runner.run_mathvista_local_judge(ns)
        elif mode == "mathverse_local_judge":
            summary = runner.run_mathverse_local_judge(ns)
            summary = _repair_mathverse_binary_judgement_summary(spec, model_path, output_dir, summary)
        elif mode == "logicvista_local_judge":
            summary = runner.run_logicvista_local_judge(ns)
        else:
            raise ValueError(f"Unsupported math-like local judge mode for {spec.key}: {mode}")
        _validate_math_like_judged_table(spec, output_dir)
        return summary
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
    prediction_by_index = {str(row["index"]): row.get("prediction") for _, row in data.iterrows()}
    malformed: list[str] = []
    for idx, item in list(judged_map.items()):
        output = str(item.get("judge_output", ""))
        obj = _parse_json_object(output)
        raw_score = item.get("score", obj.get("score"))
        if raw_score is None:
            score_match = re.search(r'"?score"?\s*[:=]\s*([01](?:\.\d+)?)', output, flags=re.I)
            raw_score = score_match.group(1) if score_match else None
        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            malformed.append(str(idx))
            continue
        if not 0.0 <= score <= 1.0:
            malformed.append(str(idx))
            continue
        parsed = runner._parse_charxiv_judge(output)
        extract_answer, extraction_method = _resolve_charxiv_extracted_answer(
            item,
            parsed,
            prediction_by_index.get(str(idx)),
        )
        if not extract_answer and extraction_method != "empty_prediction":
            malformed.append(str(idx))
            continue
        if extraction_method == "empty_prediction" and score != 0.0:
            malformed.append(str(idx))
            continue
        item["score"] = score
        item["extract_answer"] = extract_answer
        item["extract_answer_method"] = extraction_method
        judged_map[idx] = item
    if malformed:
        raise RuntimeError(
            f"CharXiv judge produced {len(malformed)} malformed decisions; first indices={malformed[:10]}"
        )
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


def _build_evochart_judge_prompt(row: dict[str, Any]) -> str:
    clarity = "clear" if _truthy_score(row.get("is_clear", True)) else "approximate/low-clarity"
    return (
        "You are scoring an EvoChart chart question answering response.\n"
        "Decide whether the model's final answer matches the reference answer.\n"
        "Do not require boxed formatting, exact wording, or the same grammar. Accept paraphrases, tense changes, labels embedded in a sentence, punctuation/case differences, and article differences when the meaning is the same.\n"
        "For numeric answers, accept equivalent formatting such as commas, currency symbols, percent signs, or units. For approximate/low-clarity references, allow a small numeric tolerance when the value is essentially the same.\n"
        "Score only the final answer content. Mark incorrect if the response gives the wrong label/value/event, gives no answer, or only repeats unrelated reasoning.\n\n"
        f"Question:\n{row.get('question', '')}\n\n"
        f"Reference answer:\n{row.get('answer', '')}\n\n"
        f"Reference clarity: {clarity}\n"
        f"Chart type: {row.get('chart_type', '')}\n"
        f"Attribute: {row.get('attribute', '')}\n\n"
        f"Model response:\n{row.get('prediction', '')}\n\n"
        "Return exactly one JSON object: {\"score\": 1, \"extracted_answer\": \"<model final answer>\"}.\n"
        "Use score 1 for correct and 0 for incorrect."
    )


def _run_evochart_local_judge(
    args: argparse.Namespace,
    spec: BenchmarkSpec,
    model_path: str,
    output_dir: Path,
    judge: PersistentJudge,
) -> dict[str, Any]:
    _import_vlmeval_runner()
    from vlmeval.smp import load

    pred_table = output_dir / f"{spec.alias}_predictions.xlsx"
    if not pred_table.exists():
        raise FileNotFoundError(pred_table)
    data = load(str(pred_table))
    judge_jsonl = output_dir / "judge_qwen3_32b.jsonl"
    if args.no_resume and judge_jsonl.exists():
        judge_jsonl.unlink()

    prompts = []
    for _, row in data.iterrows():
        prompts.append((str(row["index"]), _build_evochart_judge_prompt(row.to_dict())))
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

    scores = []
    extracted = []
    extraction_methods = []
    judge_outputs = []
    malformed: list[str] = []
    for _, row in data.iterrows():
        item = raw.get(str(row["index"]), {})
        output = str(item.get("judge_output", ""))
        score, extracted_answer, extraction_method = _resolve_evochart_judgement(
            output,
            row.get("prediction"),
        )
        if score is None:
            malformed.append(str(row["index"]))
            score = float("nan")
        scores.append(float(score))
        extracted.append(extracted_answer)
        extraction_methods.append(extraction_method)
        judge_outputs.append(output)

    if malformed:
        raise RuntimeError(
            f"EvoChart judge produced {len(malformed)} malformed decisions; first indices={malformed[:10]}"
        )

    data["eval_score"] = scores
    data["eval_pred"] = extracted
    data["eval_pred_method"] = extraction_methods
    data["judge_output"] = judge_outputs
    judged_xlsx = output_dir / f"{spec.alias}_judged_qwen3_32b.xlsx"
    data.to_excel(judged_xlsx, index=False)

    rows = [{"split": "Overall", "tot": len(data), "hit": sum(scores), "acc": sum(scores) / len(scores) * 100 if scores else 0.0}]
    for field in ("chart_type", "attribute"):
        if field not in data:
            continue
        for name, group in data.groupby(field, dropna=False):
            vals = [float(x) for x in group["eval_score"].tolist()]
            rows.append(
                {
                    "split": f"{field}:{name}",
                    "tot": len(vals),
                    "hit": sum(vals),
                    "acc": sum(vals) / len(vals) * 100 if vals else 0.0,
                }
            )
    table = pd.DataFrame(rows)
    score_csv = output_dir / f"{spec.alias}_judged_qwen3_32b_acc.csv"
    table.to_csv(score_csv, index=False)
    overall = float(rows[0]["acc"]) if rows else 0.0
    scores_obj = {"Overall": overall, "table": rows}
    summary = {
        "dataset": spec.alias,
        "model": model_path,
        "run_name": spec.run_name,
        "judge_model": args.judge_model,
        "harness": "TRACE EvoChart Qwen3-32B direct-answer judge",
        "rows": len(data),
        "score": overall,
        "scores": scores_obj,
        "artifacts": {"prediction_table": str(pred_table), "judge_jsonl": str(judge_jsonl), "judged_table": str(judged_xlsx), "score_csv": str(score_csv)},
    }
    write_json(output_dir / "scores.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=json_default))
    return summary


def _run_mmesci_local_judge(
    args: argparse.Namespace,
    spec: BenchmarkSpec,
    model_path: str,
    output_dir: Path,
    judge: PersistentJudge,
) -> dict[str, Any]:
    _import_vlmeval_runner()
    from vlmeval.dataset.utils.multiple_choice import report_acc
    from vlmeval.dataset.utils.shortqa import ShortQA_prompt
    from vlmeval.smp import load

    pred_table = output_dir / f"{spec.alias}_predictions.xlsx"
    if not pred_table.exists():
        raise FileNotFoundError(pred_table)
    data = load(str(pred_table))
    data["prediction"] = [str(x) for x in data["prediction"]]
    data["answer"] = [str(x) for x in data["answer"]]

    prompts = []
    for _, row in data.iterrows():
        prompts.append((str(row["index"]), ShortQA_prompt(row)))

    raw = judge.run_cached(
        output_dir=output_dir,
        prompts=prompts,
        cache_name="judge_qwen3_32b_shortqa.jsonl",
        max_tokens=args.judge_max_tokens,
        temperature=0.0,
        top_p=1.0,
        no_resume=False,
        desc=f"{spec.alias} ShortQA judge",
    )

    hits = []
    logs = []
    judge_outputs = []
    for _, row in data.iterrows():
        item = raw.get(str(row["index"]), {})
        output = str(item.get("judge_output", ""))
        hit, log = _parse_shortqa_correctness_output(output)
        hits.append(hit)
        logs.append(log)
        judge_outputs.append(output)
    data["hit"] = hits
    data["log"] = logs
    data["judge_output"] = judge_outputs

    judged_xlsx = output_dir / f"{spec.alias}_judged_qwen3_32b.xlsx"
    data.to_excel(judged_xlsx, index=False)

    acc_df = report_acc(data.copy())
    score_csv = output_dir / f"{spec.alias}_judged_qwen3_32b_acc.csv"
    acc_df.to_csv(score_csv, index=False)
    overall = float(sum(hits) / len(hits) * 100.0) if hits else 0.0

    breakdowns: dict[str, dict[str, float]] = {}
    for col in ("category", "l2-category", "type"):
        if col not in data:
            continue
        breakdowns[col] = {
            str(name): float(group["hit"].mean() * 100.0)
            for name, group in data.groupby(col, dropna=False)
        }
    scores_obj = {
        "Overall": overall,
        "table": acc_df.to_dict(orient="records"),
        "breakdowns": breakdowns,
    }
    summary = {
        "dataset": spec.alias,
        "model": model_path,
        "run_name": spec.run_name,
        "judge_model": args.judge_model,
        "harness": "TRACE MMESCI_EN Qwen3-32B ShortQA judge",
        "rows": len(data),
        "score": overall,
        "scores": scores_obj,
        "artifacts": {
            "prediction_table": str(pred_table),
            "judge_jsonl": str(output_dir / "judge_qwen3_32b_shortqa.jsonl"),
            "judged_table": str(judged_xlsx),
            "score_csv": str(score_csv),
        },
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
    from vlmeval.smp import load

    candidates = [
        output_dir / f"{spec.alias}_predictions.xlsx",
        output_dir / "predictions.xlsx",
    ]
    pred_table = next((path for path in candidates if path.exists()), None)
    if pred_table is None:
        matches = sorted(output_dir.glob("*_predictions.xlsx"))
        pred_table = matches[0] if matches else candidates[0]
    if not pred_table.exists():
        raise FileNotFoundError(pred_table)
    data = load(str(pred_table))
    rows = [row.to_dict() for _, row in data.iterrows()]
    rows.sort(key=lambda x: str(x["index"]))
    judge_path = output_dir / "judge_qwen32b.jsonl"
    if args.no_resume and judge_path.exists():
        judge_path.unlink()
    existing = {} if args.no_resume else chartmuseum.load_existing(judge_path)
    pending = [r for r in rows if str(r["index"]) not in existing]
    print(f"[chartmuseum judge] rows={len(rows)} existing={len(existing)} pending={len(pending)}")

    output_contract = "\n\nReturn exactly one word: Yes or No. Do not use Markdown and do not explain."
    prompts = [
        (
            str(item["index"]),
            chartmuseum.format_compare_prompt(
                str(item.get("question", "")),
                str(item.get("answer", "")),
                chartmuseum.extract_answer(str(item.get("prediction", ""))),
            )
            + output_contract,
        )
        for item in pending
    ]
    raw = judge.run_cached(
        output_dir=output_dir,
        prompts=prompts,
        cache_name="judge_qwen32b.jsonl",
        max_tokens=8,
        temperature=0.0,
        top_p=1.0,
        no_resume=False,
        desc="ChartMuseum judge",
    )
    judged_map = {**existing, **raw}

    unresolved = [
        str(row["index"])
        for row in rows
        if _parse_chartmuseum_judgement_output(judged_map[str(row["index"])].get("judge_output", "")) is None
    ]
    if unresolved:
        row_by_index = {str(row["index"]): row for row in rows}
        retry_prompts = []
        for index in unresolved:
            item = row_by_index[index]
            retry_prompts.append(
                (
                    index,
                    "Output exactly Yes or No. Do not explain.\n\n"
                    + chartmuseum.format_compare_prompt(
                        str(item.get("question", "")),
                        str(item.get("answer", "")),
                        chartmuseum.extract_answer(str(item.get("prediction", ""))),
                    )
                    + output_contract,
                )
            )
        print(f"[chartmuseum judge retry] malformed={len(unresolved)}")
        retries = judge.run_cached(
            output_dir=output_dir,
            prompts=retry_prompts,
            cache_name="judge_qwen32b_binary_retry.jsonl",
            max_tokens=8,
            temperature=0.0,
            top_p=1.0,
            no_resume=False,
            desc="ChartMuseum judge retry",
        )
        judged_map.update(retries)

    judged_rows = []
    malformed: list[str] = []
    for row in rows:
        item = dict(row)
        judged = judged_map[str(row["index"])]
        item["judge_model"] = args.judge_model
        item["judge_output"] = judged.get("judge_output", "")
        clean_output = str(item["judge_output"]).strip().lower()
        parsed_binary = _parse_chartmuseum_judgement_output(clean_output)
        if parsed_binary is not None:
            item["score"] = float(parsed_binary)
        else:
            malformed.append(str(row["index"]))
            item["score"] = float("nan")
        item["judge_output_token_count"] = judged.get("judge_output_token_count", 0)
        item["judge_finish_reason"] = judged.get("judge_finish_reason", "")
        judged_rows.append(item)

    if malformed:
        raise RuntimeError(
            f"ChartMuseum judge produced {len(malformed)} malformed decisions; first indices={malformed[:10]}"
        )

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
            "prediction_table": str(pred_table),
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
    for path in (VLMEVAL_ROOT, scripts_root):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    import batched_chartqapro_vllm as chartqapro

    def clean_chartqapro_answer(value: str) -> str:
        text = str(value or "").strip()
        text = text.splitlines()[0].strip()
        text = re.sub(r"^(?:[-*]\s+)+", "", text).strip()
        text = re.sub(r"^(?:the\s+)?(?:final\s+)?answer\s*(?:is|=|:|：)?\s*", "", text, flags=re.I).strip()
        text = text.strip(" \t\r\n\"'`")
        text = text.rstrip(".。").strip()
        # Models often emphasize final answers as **42** or **A**. Strip only
        # balanced markdown wrappers so multiplication or exponent notation is
        # not altered inside the answer.
        changed = True
        while changed and len(text) >= 2:
            changed = False
            for marker in ("**", "__", "*", "_"):
                if text.startswith(marker) and text.endswith(marker) and len(text) >= 2 * len(marker):
                    text = text[len(marker) : -len(marker)].strip()
                    changed = True
                    break
        text = text.strip(" \t\r\n\"'`")
        text = re.sub(r"\s*(?:</s>|<\|im_end\|>)\s*$", "", text).strip()
        text = text.rstrip(".。").strip()
        return text

    def extract_chartqapro_prediction(raw: str, question_type: str = "") -> str:
        text = str(raw or "").strip()
        boxed = chartqapro._last_boxed(text) if hasattr(chartqapro, "_last_boxed") else None
        if boxed:
            return clean_chartqapro_answer(boxed)
        answer_tag = re.search(r"<answer>(.*?)</answer>", text, flags=re.I | re.S)
        if answer_tag:
            return clean_chartqapro_answer(answer_tag.group(1))
        try:
            obj = json.loads(text)
            if isinstance(obj, dict) and "answer" in obj:
                return clean_chartqapro_answer(str(obj["answer"]))
        except Exception:
            pass
        matches = list(
            re.finditer(
                r"\b(?:final\s+answer|answer)\b\s*(?:is|=|:|：)?\s*(.+)",
                text,
                flags=re.I | re.S,
            )
        )
        if matches:
            tail = matches[-1].group(1).strip().splitlines()[0].strip()
            return clean_chartqapro_answer(tail)
        return clean_chartqapro_answer(chartqapro.extract_prediction(text, question_type))

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
            pred = extract_chartqapro_prediction(str(raw), str(row.get("question_type", "")))
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
            "extractor": "TRACE ChartQAPro answer-is extractor",
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
    if args.run_set == "trace_final25" and spec.key in LLM_EXTRACT_SCORE_KEYS:
        raise RuntimeError(
            f"{spec.display} requires run_llm_extracted_benchmark_score_queue.py in the Final25 contract; "
            "the generic direct scorer is intentionally disabled for this benchmark"
        )
    if args.run_set == "trace_final25" and spec.key in DEDICATED_SCORE_KEYS:
        raise RuntimeError(
            f"{spec.display} requires run_mme_reasoning_eval.py in the Final25 contract; "
            "the generic direct scorer is intentionally disabled for this benchmark"
        )
    if spec.key == "chartqapro":
        summary = _run_chartqapro_extracted_score(args, spec, model_path, output_dir)
    elif spec.key == "tablevqabench":
        summary = _run_tablevqabench_local_score(spec, model_path, output_dir)
    elif spec.key == "qspatial_plus":
        summary = _run_vlmeval_evaluate_with_kwargs(
            args,
            spec,
            model_path,
            output_dir,
            judge_kwargs={},
            harness="VLMEvalKit QSpatial regex parser without API judge",
        )
    elif spec.key == "phyx_mini_mc":
        summary = _run_phyx_option_score(args, spec, model_path, output_dir)
    elif spec.key == "vlmbias":
        summary = _run_vlmbias_rule_score(args, spec, model_path, output_dir)
    elif spec.key == "tdbench_grounding":
        summary = _run_vlmeval_evaluate_with_kwargs(
            args,
            spec,
            model_path,
            output_dir,
            judge_kwargs={"model": "centroid"},
            harness="VLMEvalKit TDBenchGrounding centroid containment scorer",
        )
    elif mode == "chartmuseum_local_judge":
        summary = _run_chartmuseum_local_judge(args, spec, model_path, output_dir, judge)
    elif mode == "evochart_local_judge":
        summary = _run_evochart_local_judge(args, spec, model_path, output_dir, judge)
    elif mode == "charxiv_local_judge":
        summary = _run_charxiv_local_judge(args, spec, model_path, output_dir, judge)
    elif mode == "mmesci_local_judge":
        summary = _run_mmesci_local_judge(args, spec, model_path, output_dir, judge)
    elif mode == "scienceqa_local_score":
        summary = _run_scienceqa_local_score(args, spec, model_path, output_dir)
    elif mode in {"mathv_local_judge", "mathvista_local_judge", "mathverse_local_judge", "logicvista_local_judge"}:
        summary = _run_local_math_like(args, spec, model_path, output_dir, judge)
    elif mode == "wemath_local_judge":
        summary = _run_wemath_subset_score(args, spec, model_path, output_dir)
    elif mode == "seephys_local_judge":
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
            summary = runner.run_seephys_local_judge(ns)
        finally:
            runner._run_local_text_judge = old
    elif mode == "physics_local_judge":
        summary = _run_physics_subset_score(args, spec, model_path, output_dir, judge)
    else:
        summary = _run_direct_vlmeval(args, spec, model_path, output_dir)
    preferred_direct_score = _preferred_direct_score(spec, summary)
    if preferred_direct_score is not None:
        summary["score"] = preferred_direct_score
        write_json(output_dir / "scores.json", summary)
    grounding_score = grounding_preferred_score_and_rows(summary)
    if grounding_score is not None and grounding_score[0] is not None:
        summary["score"] = grounding_score[0]
        write_json(output_dir / "scores.json", summary)
    weighted = weighted_prefixed_overall_accuracy(summary.get("scores"))
    if weighted is not None:
        summary["score"] = weighted[0]
        write_json(output_dir / "scores.json", summary)
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
    os.environ.setdefault("VLLM_DISABLE_COMPILE_CACHE", "1")

    specs = benchmark_specs_for_run_set(args.run_set, model_slug=args.model_slug)
    specs = filter_benchmark_specs(specs, only=args.only, exclude=args.exclude)
    if args.run_set == "trace_final25":
        unsupported = [spec.key for spec in specs if spec.key not in DIRECT_SCORE_KEYS]
        if args.only and unsupported:
            raise ValueError(
                "The Final25 direct scorer only accepts DIRECT_SCORE_KEYS; route these separately: "
                f"{unsupported}"
            )
        specs = [spec for spec in specs if spec.key in DIRECT_SCORE_KEYS]
        print(
            "[score-worker:final25-route] "
            f"direct={len(specs)} llm_extract={len(LLM_EXTRACT_SCORE_KEYS)} "
            f"dedicated={len(DEDICATED_SCORE_KEYS)}"
        )
    materialize_grounding_benchmark_files(specs)
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
    parser.add_argument(
        "--run-set",
        choices=BENCHMARK_RUN_SETS,
        default="remaining_base",
    )
    parser.add_argument(
        "--trace-candidate37-200",
        action="store_true",
        help="Use the fixed 37-benchmark TRACE-aligned 200-row candidate suite.",
    )
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
    parser.add_argument("--judge-api-base", action="append", dest="judge_api_bases")
    parser.add_argument("--judge-api-model", default="qwen3-32b-judge")
    parser.add_argument("--judge-api-tokenizer-model", default="Qwen/Qwen3-32B")
    parser.add_argument("--judge-api-parallelism", type=int, default=128)
    parser.add_argument("--judge-api-timeout", type=float, default=120.0)
    parser.add_argument("--judge-api-max-retries", type=int, default=5)
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
        if not args.queue_name:
            args.queue_name = f"{args.model_slug}_{TRACE_CANDIDATE37_200_QUEUE_SUFFIX}"
    if args.run_set == "trace_grounding" and not args.only:
        args.only = list(TRACE_GROUNDING_BENCHMARKS)
    run_worker(args)


if __name__ == "__main__":
    main()
