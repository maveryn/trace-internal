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
    DEFAULT_BENCHMARK_ROOT,
    DEFAULT_QUEUE_ROOT,
    REPO_ROOT,
    TRACE_CANDIDATE37_200_BENCHMARKS,
    TRACE_CANDIDATE37_200_QUEUE_SUFFIX,
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
    weighted_prefixed_overall_accuracy,
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
        pending = [(idx, prompt) for idx, prompt in prompts if str(idx) not in existing]
        endpoints = self.api_bases
        print(
            "[judge:api-cached] "
            f"cache={cache_path} rows={len(prompts)} existing={len(existing)} pending={len(pending)} "
            f"endpoints={len(endpoints)} parallelism={getattr(self.args, 'judge_api_parallelism', 128)}"
        )
        if pending:
            rendered = {str(idx): self.api_chat_prompt(prompt) for idx, prompt in pending}

            def run_one(pos_item: tuple[int, tuple[str, str]]) -> dict[str, Any]:
                pos, (idx, _) = pos_item
                endpoint = endpoints[pos % len(endpoints)]
                result = self._call_api_completion(
                    endpoint,
                    rendered[str(idx)],
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                )
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
    from vlmeval.dataset import build_dataset
    from vlmeval.smp import load

    dataset = build_dataset(spec.alias)
    if dataset is None:
        raise RuntimeError(f"VLMEvalKit could not build dataset {spec.alias}")
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
    for row in rows:
        if row["log"] == "Pending local judge":
            out = str(judged.get(str(row["index"]), {}).get("judge_output", "")).strip().lower()
            row["res"] = 1.0 if "true" in out or out.startswith("yes") else 0.0
            row["log"] = f"Judge output: {out}"

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

    prompts = [
        (
            str(item["index"]),
            chartmuseum.format_compare_prompt(
                str(item.get("question", "")),
                str(item.get("answer", "")),
                chartmuseum.extract_answer(str(item.get("prediction", ""))),
            ),
        )
        for item in pending
    ]
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
    if spec.key == "chartqapro":
        summary = _run_chartqapro_extracted_score(args, spec, model_path, output_dir)
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
    elif mode == "chartmuseum_local_judge":
        summary = _run_chartmuseum_local_judge(args, spec, model_path, output_dir, judge)
    elif mode == "charxiv_local_judge":
        summary = _run_charxiv_local_judge(args, spec, model_path, output_dir, judge)
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
    parser.add_argument("--run-set", choices=["full", "remaining_base", "base_all", "trace_candidate37_200"], default="remaining_base")
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
    run_worker(args)


if __name__ == "__main__":
    main()
