from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from statistics import mean
from typing import Any

os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")

from omegaconf import OmegaConf
from transformers import AutoProcessor, AutoTokenizer
from vllm import LLM, SamplingParams

from verl.utils.dataset.trace_rl_dataset import TraceRLHFDataset
from verl.utils.trace_reward import evaluate_trace_response_format, extract_trace_answer_for_scoring
from verl.utils.val_reward import _format_reward, score_external_response


DEFAULT_BENCHMARKS = (
    "mathvista_mini",
    "mmstar",
    "charxiv_rq",
    "embspatialbench",
    "mmmu_pro_vision",
    "countqa",
)


def _json_default(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def _build_dataset(
    parquet_path: Path,
    *,
    benchmark: str,
    tokenizer: Any,
    processor: Any,
    system_prompt: Path | None,
    format_prompt: Path | None,
    format_prompt_variant: str,
    prompt_key: str,
    answer_key: str,
    max_prompt_length: int,
    max_pixels: int,
) -> TraceRLHFDataset:
    config = OmegaConf.create(
        {
            "trace_output_mode": "answer",
            "prompt_key": prompt_key,
            "answer_key": answer_key,
            "image_key": "images",
            "video_key": "videos",
            # TraceRLHFDataset resolves empty/auto to the TRACE JSON system
            # prompt. Use a sentinel and clear it after construction when a
            # user-only legacy prompt is requested.
            "system_prompt": str(system_prompt) if system_prompt is not None else "__TRACE_NO_SYSTEM_PROMPT__",
            "format_prompt": str(format_prompt) if format_prompt is not None else None,
            "format_prompt_variant": format_prompt_variant,
            "max_prompt_length": max_prompt_length,
            "truncation": "error",
            "min_pixels": None,
            "max_pixels": max_pixels,
            "filter_overlong_prompts": False,
            "filter_overlong_prompts_workers": 1,
            "log_dataset_download_status": True,
            "default_data_source": benchmark,
        }
    )
    dataset = TraceRLHFDataset(str(parquet_path), tokenizer=tokenizer, processor=processor, config=config)
    if system_prompt is None:
        dataset.system_prompt = None
    return dataset


def _build_inputs(dataset: TraceRLHFDataset) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    vllm_inputs: list[dict[str, Any]] = []
    examples: list[dict[str, Any]] = []
    for idx in range(len(dataset)):
        item = dataset[idx]
        prompt_token_ids = list(item["raw_prompt_ids"])
        request: dict[str, Any] = {"prompt_token_ids": prompt_token_ids}
        if "multi_modal_data" in item:
            request["multi_modal_data"] = item["multi_modal_data"]
        vllm_inputs.append(request)
        examples.append(item)
    return vllm_inputs, examples


def _score_outputs(
    *,
    mode: str,
    benchmark: str,
    examples: list[dict[str, Any]],
    outputs: Any,
    output_jsonl: Path,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    token_counts: list[int] = []
    hits: list[float] = []
    extracted_flags: list[float] = []
    format_scores: list[float] = []
    boxed_flags: list[float] = []
    json_answer_flags: list[float] = []

    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with output_jsonl.open("w", encoding="utf-8") as handle:
        for item, generated in zip(examples, outputs, strict=True):
            completion = generated.outputs[0]
            response = completion.text
            token_count = len(completion.token_ids or [])
            prompt_text = item.get("extra_info", {}).get("prompt")
            accuracy, extracted, extracted_answer, method = score_external_response(
                response=response,
                ground_truth=item.get("ground_truth"),
                prompt_text=prompt_text,
                parser_family=item.get("parser_family"),
                metadata=item.get("metadata"),
            )
            hit = 1.0 if accuracy > 0.5 else 0.0
            if mode == "current_json":
                format_score = float(evaluate_trace_response_format(response, trace_reward_mode="answer")["format"])
            else:
                format_score = float(_format_reward(response))
            has_boxed = 1.0 if "\\boxed" in response else 0.0
            has_json_answer = 1.0 if extract_trace_answer_for_scoring(response) is not None else 0.0

            row = {
                "benchmark": benchmark,
                "uid": str(item.get("uid", "")),
                "benchmark_id": str(item.get("benchmark_id", benchmark)),
                "ground_truth": item.get("ground_truth"),
                "response": response,
                "score": float(accuracy),
                "hit": hit,
                "extracted": bool(extracted),
                "extracted_answer": extracted_answer,
                "extraction_method": method,
                "format": format_score,
                "generated_tokens": token_count,
                "has_boxed": bool(has_boxed),
                "has_json_answer": bool(has_json_answer),
            }
            handle.write(json.dumps(row, ensure_ascii=False, default=_json_default) + "\n")

            rows.append(row)
            token_counts.append(token_count)
            hits.append(hit)
            extracted_flags.append(1.0 if extracted else 0.0)
            format_scores.append(format_score)
            boxed_flags.append(has_boxed)
            json_answer_flags.append(has_json_answer)

    return {
        "benchmark": benchmark,
        "count": len(rows),
        "accuracy_on_total": mean(hits) if hits else 0.0,
        "overall": mean(float(row["score"]) for row in rows) if rows else 0.0,
        "extracted_rate": mean(extracted_flags) if extracted_flags else 0.0,
        "format_rate": mean(format_scores) if format_scores else 0.0,
        "boxed_rate": mean(boxed_flags) if boxed_flags else 0.0,
        "json_answer_rate": mean(json_answer_flags) if json_answer_flags else 0.0,
        "avg_generated_tokens": mean(token_counts) if token_counts else 0.0,
        "max_generated_tokens": max(token_counts) if token_counts else 0,
        "output_jsonl": str(output_jsonl),
    }


def _run_mode(
    *,
    mode: str,
    system_prompt: Path | None,
    format_prompt: Path | None,
    format_prompt_variant: str,
    prompt_key: str,
    answer_key: str,
    benchmarks: tuple[str, ...],
    data_dir: Path,
    output_dir: Path,
    tokenizer: Any,
    processor: Any,
    llm: LLM,
    sampling_params: SamplingParams,
    max_prompt_length: int,
    max_pixels: int,
    batch_size: int,
) -> list[dict[str, Any]]:
    mode_summaries: list[dict[str, Any]] = []
    for benchmark in benchmarks:
        parquet_path = data_dir / f"{benchmark}.parquet"
        if not parquet_path.exists():
            raise FileNotFoundError(parquet_path)
        print(f"[{mode}] preparing {benchmark}: {parquet_path}", flush=True)
        dataset = _build_dataset(
            parquet_path,
            benchmark=benchmark,
            tokenizer=tokenizer,
            processor=processor,
            system_prompt=system_prompt,
            format_prompt=format_prompt,
            format_prompt_variant=format_prompt_variant,
            prompt_key=prompt_key,
            answer_key=answer_key,
            max_prompt_length=max_prompt_length,
            max_pixels=max_pixels,
        )
        vllm_inputs, examples = _build_inputs(dataset)
        print(f"[{mode}] generating {benchmark}: count={len(vllm_inputs)} batch_size={batch_size}", flush=True)
        outputs = []
        for start in range(0, len(vllm_inputs), batch_size):
            batch = vllm_inputs[start : start + batch_size]
            outputs.extend(llm.generate(batch, sampling_params=sampling_params, use_tqdm=True))
        summary = _score_outputs(
            mode=mode,
            benchmark=benchmark,
            examples=examples,
            outputs=outputs,
            output_jsonl=output_dir / mode / f"{benchmark}.jsonl",
        )
        print(
            f"[{mode}] {benchmark}: acc={summary['accuracy_on_total']:.4f} "
            f"extracted={summary['extracted_rate']:.4f} avg_tokens={summary['avg_generated_tokens']:.1f}",
            flush=True,
        )
        mode_summaries.append(summary)
    return mode_summaries


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen3-VL-2B-Instruct")
    parser.add_argument("--data-dir", type=Path, default=Path("dataset/validation"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--benchmarks", nargs="*", default=list(DEFAULT_BENCHMARKS))
    parser.add_argument("--current-system-prompt", type=Path, default=Path("examples/prompts/trace_vero_json_system_prompt_answer.txt"))
    parser.add_argument("--boxed-system-prompt", type=Path, default=None)
    parser.add_argument("--boxed-format-prompt", type=Path, default=Path("../rlvr_legacy/examples/format_prompt/math.jinja"))
    parser.add_argument("--boxed-format-prompt-variant", default="boxed_only")
    parser.add_argument("--modes", nargs="+", choices=("current_json", "boxed"), default=["current_json", "boxed"])
    parser.add_argument("--tensor-parallel-size", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--max-model-len", type=int, default=8192)
    parser.add_argument("--max-num-batched-tokens", type=int, default=8192)
    parser.add_argument("--max-num-seqs", type=int, default=512)
    parser.add_argument("--max-tokens", type=int, default=1536)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.7)
    parser.add_argument("--enforce-eager", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--max-pixels", type=int, default=4194304)
    parser.add_argument("--max-prompt-length", type=int, default=1536)
    parser.add_argument("--attention-backend", default=None)
    parser.add_argument("--disable-trtllm-attention", action="store_true")
    args = parser.parse_args()

    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ.setdefault("VLLM_LOGGING_LEVEL", "WARN")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=False)
    processor = AutoProcessor.from_pretrained(args.model, trust_remote_code=False)
    sampling_params = SamplingParams(
        n=1,
        temperature=0.0,
        top_p=1.0,
        top_k=-1,
        max_tokens=args.max_tokens,
        skip_special_tokens=True,
    )

    print(
        "[vllm] loading "
        f"model={args.model} tp={args.tensor_parallel_size} max_model_len={args.max_model_len} "
        f"max_num_batched_tokens={args.max_num_batched_tokens} max_num_seqs={args.max_num_seqs}",
        flush=True,
    )
    attention_config = {}
    if args.attention_backend:
        attention_config["backend"] = args.attention_backend
    if args.disable_trtllm_attention:
        attention_config["use_trtllm_attention"] = False

    llm = LLM(
        model=args.model,
        tensor_parallel_size=args.tensor_parallel_size,
        dtype="bfloat16",
        gpu_memory_utilization=args.gpu_memory_utilization,
        max_model_len=args.max_model_len,
        max_num_batched_tokens=args.max_num_batched_tokens,
        max_num_seqs=args.max_num_seqs,
        enforce_eager=args.enforce_eager,
        enable_chunked_prefill=True,
        enable_prefix_caching=True,
        limit_mm_per_prompt={"image": 4},
        trust_remote_code=False,
        seed=18,
        attention_config=attention_config or None,
    )

    benchmarks = tuple(args.benchmarks)
    summaries = {
        "model": args.model,
        "benchmarks": benchmarks,
        "settings": {
            "tensor_parallel_size": args.tensor_parallel_size,
            "batch_size": args.batch_size,
            "max_model_len": args.max_model_len,
            "max_num_batched_tokens": args.max_num_batched_tokens,
            "max_num_seqs": args.max_num_seqs,
            "max_tokens": args.max_tokens,
            "temperature": 0.0,
            "enforce_eager": args.enforce_eager,
            "attention_backend": args.attention_backend,
            "disable_trtllm_attention": args.disable_trtllm_attention,
        },
        "modes": {},
    }

    if "current_json" in args.modes:
        summaries["modes"]["current_json"] = _run_mode(
            mode="current_json",
            system_prompt=args.current_system_prompt,
            format_prompt=None,
            format_prompt_variant="boxed_only",
            prompt_key="prompt_answer",
            answer_key="answer_gt",
            benchmarks=benchmarks,
            data_dir=args.data_dir,
            output_dir=args.output_dir,
            tokenizer=tokenizer,
            processor=processor,
            llm=llm,
            sampling_params=sampling_params,
            max_prompt_length=args.max_prompt_length,
            max_pixels=args.max_pixels,
            batch_size=args.batch_size,
        )
    if "boxed" in args.modes:
        summaries["modes"]["boxed"] = _run_mode(
            mode="boxed",
            system_prompt=args.boxed_system_prompt,
            format_prompt=args.boxed_format_prompt,
            format_prompt_variant=args.boxed_format_prompt_variant,
            prompt_key="prompt",
            answer_key="ground_truth",
            benchmarks=benchmarks,
            data_dir=args.data_dir,
            output_dir=args.output_dir,
            tokenizer=tokenizer,
            processor=processor,
            llm=llm,
            sampling_params=sampling_params,
            max_prompt_length=args.max_prompt_length,
            max_pixels=args.max_pixels,
            batch_size=args.batch_size,
        )

    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(json.dumps(summaries, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")
    print(f"[done] wrote {summary_path}", flush=True)


if __name__ == "__main__":
    main()
