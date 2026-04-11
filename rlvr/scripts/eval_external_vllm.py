#!/usr/bin/env python3
"""Run vLLM evaluation on an external RLVR validation parquet."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from jinja2 import Template
from transformers import AutoProcessor
from vllm import LLM, SamplingParams

try:
    import pillow_avif  # noqa: F401
except ImportError:
    pass


RLVR_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = RLVR_ROOT.parent
if str(RLVR_ROOT) not in sys.path:
    sys.path.append(str(RLVR_ROOT))

from verl.utils.dataset import process_image  # noqa: E402
from verl.utils.local_strict_eval import strict_score_response  # noqa: E402


DEFAULT_DATA = RLVR_ROOT / "dataset" / "validation" / "mathvista_mini.parquet"
DEFAULT_TEMPLATE = RLVR_ROOT / "examples" / "format_prompt" / "math.jinja"


def _jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return [_jsonable(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _normalize_images(raw_images: Any, *, min_pixels: int | None, max_pixels: int | None) -> list[Any]:
    return [process_image(image, min_pixels=min_pixels, max_pixels=max_pixels) for image in _as_list(raw_images)]


def _build_messages(prompt_text: str, image_count: int) -> list[dict[str, Any]]:
    if image_count > 0 and "<image>" not in prompt_text:
        prompt_text = ("<image>" * image_count) + prompt_text

    if image_count <= 0:
        return [{"role": "user", "content": prompt_text}]

    content: list[dict[str, str]] = []
    for index, segment in enumerate(prompt_text.split("<image>")):
        if index != 0:
            content.append({"type": "image"})
        if segment:
            content.append({"type": "text", "text": segment})
    return [{"role": "user", "content": content}]


def _render_prompt(template: Template | None, prompt: str, variant: str) -> str:
    if template is None:
        return prompt.strip()
    return template.render(content=prompt, format_prompt_variant=variant).strip()


def _resolve_output_dir(output_root: Path, dataset_name: str, overwrite: bool) -> Path:
    output_dir = output_root / dataset_name
    if output_dir.exists() and not overwrite:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output_dir = output_root / f"{dataset_name}_{stamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _load_template(path: Path | None) -> Template | None:
    if path is None:
        return None
    return Template(path.expanduser().resolve().read_text(encoding="utf-8").strip())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="Qwen/Qwen3-VL-2B-Instruct")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--dataset-name", default=None)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT / "runs")
    parser.add_argument("--prompt-key", default="prompt")
    parser.add_argument("--answer-key", default="ground_truth")
    parser.add_argument("--image-key", default="images")
    parser.add_argument("--format-prompt", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--format-prompt-variant", default="boxed_only")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument("--max-prompt-length", type=int, default=1024)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--tensor-parallel-size", type=int, default=1)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.8)
    parser.add_argument("--max-model-len", type=int, default=None)
    parser.add_argument("--max-num-batched-tokens", type=int, default=8192)
    parser.add_argument("--max-num-seqs", type=int, default=512)
    parser.add_argument("--limit-images", type=int, default=1)
    parser.add_argument("--min-pixels", type=int, default=262144)
    parser.add_argument("--max-pixels", type=int, default=4194304)
    parser.add_argument("--enable-chunked-prefill", action="store_true")
    parser.add_argument("--trust-remote-code", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_path = args.data.expanduser().resolve()
    dataset_name = args.dataset_name or data_path.stem
    output_dir = _resolve_output_dir(args.output_root.expanduser().resolve(), dataset_name, args.overwrite)

    df = pd.read_parquet(data_path)
    if args.limit is not None:
        df = df.head(args.limit).copy()

    template = _load_template(args.format_prompt)
    processor = AutoProcessor.from_pretrained(
        args.model,
        trust_remote_code=args.trust_remote_code,
        use_fast=True,
    )

    requests: list[dict[str, Any]] = []
    prepared_rows: list[dict[str, Any]] = []
    for row_index, row in df.iterrows():
        raw_prompt = str(row[args.prompt_key]).strip()
        rendered_prompt = _render_prompt(template, raw_prompt, args.format_prompt_variant)
        images = _normalize_images(
            row.get(args.image_key),
            min_pixels=args.min_pixels,
            max_pixels=args.max_pixels,
        )
        messages = _build_messages(rendered_prompt, len(images))
        chat_prompt = processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
        request: dict[str, Any] = {"prompt": chat_prompt}
        if images:
            request["multi_modal_data"] = {"image": images}
        requests.append(request)
        prepared_rows.append(
            {
                "row_index": int(row_index),
                "uid": row.get("uid"),
                "instance_id": row.get("instance_id"),
                "benchmark_id": row.get("benchmark_id", dataset_name),
                "source_id": row.get("source_id"),
                "prompt": raw_prompt,
                "formatted_prompt": rendered_prompt,
                "ground_truth": _jsonable(row[args.answer_key]),
                "parser_family": row.get("parser_family"),
                "metadata": _jsonable(row.get("metadata", {})),
            }
        )

    is_multimodal = any("multi_modal_data" in request for request in requests)
    if args.max_model_len is None:
        effective_max_model_len = args.max_prompt_length + args.max_tokens
        if is_multimodal:
            effective_max_model_len = max(effective_max_model_len, 8192)
    else:
        effective_max_model_len = args.max_model_len

    llm = LLM(
        model=args.model,
        trust_remote_code=args.trust_remote_code,
        seed=args.seed,
        tensor_parallel_size=args.tensor_parallel_size,
        gpu_memory_utilization=args.gpu_memory_utilization,
        disable_log_stats=True,
        mm_processor_cache_gb=0,
        max_model_len=effective_max_model_len,
        max_num_batched_tokens=args.max_num_batched_tokens,
        max_num_seqs=args.max_num_seqs,
        enable_chunked_prefill=args.enable_chunked_prefill,
        limit_mm_per_prompt={"image": args.limit_images},
    )
    sampling_params = SamplingParams(
        temperature=args.temperature,
        top_p=args.top_p,
        n=1,
        max_tokens=args.max_tokens,
    )
    outputs = []
    batch_size = max(1, int(args.batch_size))
    for start in range(0, len(requests), batch_size):
        batch_requests = requests[start : start + batch_size]
        outputs.extend(llm.generate(batch_requests, sampling_params=sampling_params, use_tqdm=True))

    records: list[dict[str, Any]] = []
    hit_count = 0.0
    extracted_count = 0
    for prepared, output in zip(prepared_rows, outputs):
        completion = output.outputs[0] if output.outputs else None
        prediction = completion.text if completion is not None else ""
        token_ids = getattr(completion, "token_ids", None) if completion is not None else None
        finish_reason = getattr(completion, "finish_reason", None) if completion is not None else None
        score, extracted, extracted_answer, extracted_method = strict_score_response(
            response=prediction,
            ground_truth=prepared["ground_truth"],
            prompt_text=prepared["formatted_prompt"],
            parser_family=prepared["parser_family"],
            metadata=prepared["metadata"],
        )
        hit = 1.0 if float(score) > 0.5 else 0.0
        hit_count += hit
        extracted_count += 1 if extracted else 0
        records.append(
            {
                **prepared,
                "prediction": prediction,
                "extracted": bool(extracted),
                "extracted_answer": extracted_answer,
                "extracted_method": extracted_method,
                "score": float(score),
                "hit": hit,
                "finish_reason": finish_reason,
                "generated_tokens": len(token_ids) if token_ids is not None else None,
            }
        )

    total = len(records)
    finish_reasons = Counter(str(record.get("finish_reason")) for record in records)
    capped_count = sum(
        1
        for record in records
        if record.get("generated_tokens") is not None and int(record["generated_tokens"]) >= args.max_tokens
    )
    metrics = {
        "dataset": dataset_name,
        "data": str(data_path),
        "model": args.model,
        "total": total,
        "extracted": extracted_count,
        "hit": hit_count,
        "accuracy_on_extracted": hit_count / extracted_count if extracted_count else 0.0,
        "accuracy_on_total": hit_count / total if total else 0.0,
        "extraction_rate": extracted_count / total if total else 0.0,
        "finish_reasons": dict(finish_reasons),
        "responses_at_token_cap": capped_count,
        "sampling": {
            "temperature": args.temperature,
            "top_p": args.top_p,
            "n": 1,
            "max_tokens": args.max_tokens,
            "seed": args.seed,
        },
        "engine": {
            "batch_size": args.batch_size,
            "max_prompt_length": args.max_prompt_length,
            "max_model_len": effective_max_model_len,
            "max_num_batched_tokens": args.max_num_batched_tokens,
            "max_num_seqs": args.max_num_seqs,
            "enable_chunked_prefill": bool(args.enable_chunked_prefill),
            "limit_images": args.limit_images,
        },
        "format_prompt": str(args.format_prompt) if args.format_prompt is not None else None,
        "format_prompt_variant": args.format_prompt_variant,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    jsonl_path = output_dir / "predictions.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    tsv_path = output_dir / "predictions.tsv"
    pd.DataFrame(records).to_csv(tsv_path, sep="\t", index=False)

    metrics_path = output_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(metrics, indent=2, ensure_ascii=False))
    print(f"predictions_jsonl={jsonl_path}")
    print(f"predictions_tsv={tsv_path}")
    print(f"metrics={metrics_path}")


if __name__ == "__main__":
    main()
