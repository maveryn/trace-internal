#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import numpy as np
from datasets import Dataset, load_dataset
from jinja2 import Template
from PIL import Image
from tqdm import tqdm
from transformers import AutoProcessor

try:
    from mathruler.grader import extract_boxed_content
except Exception:  # pragma: no cover - optional dependency in some envs
    extract_boxed_content = None


RLVR_ROOT = Path(__file__).resolve().parents[1]

INT_RE = re.compile(r"[-+]?\d+")

# Match RLVR launch behavior and avoid CUDA re-init failures in forked workers.
os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")


@dataclass
class EvalRecord:
    index: int
    bucket_id_str: str
    task_variant_id: int
    task_variant_key: str
    count_bin: int
    ground_truth_integer: Optional[int]
    prediction_integer: Optional[int]
    prediction_text: str
    correct: int
    parse_ok: int
    abs_error: Optional[int]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate Prism integer prompts with vLLM and export bucket stats.")
    parser.add_argument(
        "--dataset",
        type=str,
        default="xashru/prism@train",
        help="HF dataset id with optional @split, local parquet path, or local dataset directory.",
    )
    parser.add_argument("--problem-key", type=str, default="problem_integer", help="Prompt column for integer eval.")
    parser.add_argument("--answer-key", type=str, default="answer_integer", help="Integer answer column.")
    parser.add_argument("--image-key", type=str, default="images", help="Image column key.")
    parser.add_argument(
        "--model",
        type=str,
        default="Qwen/Qwen2.5-VL-7B-Instruct",
        help="Model path (HF id or local path). Defaults to the Prism RLVR VL checkpoint.",
    )
    parser.add_argument(
        "--format-prompt",
        type=str,
        default=str(RLVR_ROOT / "examples" / "format_prompt" / "math.jinja"),
        help="Optional Jinja prompt wrapper (set '' to disable).",
    )
    parser.add_argument("--batch-size", type=int, default=512, help="Validation batch size (default matches RLVR config).")
    parser.add_argument("--max-samples", type=int, default=0, help="Optional cap for quick smoke runs (0=all rows).")
    parser.add_argument("--max-tokens", type=int, default=256, help="Max new tokens per response.")
    parser.add_argument("--temperature", type=float, default=0.0, help="Decode temperature.")
    parser.add_argument("--top-p", type=float, default=1.0, help="Top-p sampling.")
    parser.add_argument("--n", type=int, default=1, help="Number of generations per sample (uses first for scoring).")
    parser.add_argument("--seed", type=int, default=42, help="Sampling seed.")
    parser.add_argument("--min-pixels", type=int, default=262_144, help="Min image pixels (same default as RLVR).")
    parser.add_argument("--max-pixels", type=int, default=4_194_304, help="Max image pixels (same default as RLVR).")
    parser.add_argument("--limit-images", type=int, default=1, help="vLLM per-prompt image limit.")
    parser.add_argument(
        "--tensor-parallel-size",
        type=int,
        default=1,
        help="Tensor parallel size (default 1 to match qwen2_5-7b-vl rollout strategy).",
    )
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.7, help="vLLM GPU memory utilization target.")
    parser.add_argument("--trust-remote-code", action="store_true", help="Pass trust_remote_code=True to processor/vLLM.")
    parser.add_argument("--disable-tqdm", action="store_true", help="Disable progress bars.")
    parser.add_argument(
        "--out-dir",
        type=str,
        default=str(RLVR_ROOT / "mydata" / "prism_eval"),
        help="Output directory for predictions and summary stats.",
    )
    parser.add_argument(
        "--include-prompt-in-predictions",
        action="store_true",
        help="Include rendered prompt text in predictions.jsonl (larger file).",
    )
    return parser.parse_args()


def _split_data_source(data_source: str) -> tuple[str, str]:
    if "@" in data_source and not os.path.exists(data_source):
        dataset_name, split = data_source.rsplit("@", 1)
        return dataset_name, split
    return data_source, "train"


def _load_dataset_any(source: str) -> Dataset:
    dataset_name, split = _split_data_source(source)
    if os.path.isdir(dataset_name):
        files = [p for p in Path(dataset_name).iterdir() if p.is_file()]
        if not files:
            raise FileNotFoundError(f"No files found in dataset directory: {dataset_name}")
        file_type = files[0].suffix.lstrip(".").replace("jsonl", "json")
        return load_dataset(file_type, data_dir=dataset_name, split=split)

    if os.path.isfile(dataset_name):
        file_type = Path(dataset_name).suffix.lstrip(".").replace("jsonl", "json")
        return load_dataset(file_type, data_files=dataset_name, split=split)

    return load_dataset(dataset_name, split=split)


def _load_prompt_template(path_str: str) -> Optional[Template]:
    if not path_str:
        return None
    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError(f"format prompt template not found: {path}")
    return Template(path.read_text(encoding="utf-8").strip())


def _build_messages(prompt_text: str, has_image: bool) -> List[Dict[str, Any]]:
    if not has_image:
        return [{"role": "user", "content": prompt_text}]

    content_list: List[Dict[str, Any]] = []
    for i, segment in enumerate(prompt_text.split("<image>")):
        if i > 0:
            content_list.append({"type": "image"})
        segment = segment or ""
        if segment:
            content_list.append({"type": "text", "text": segment})
    return [{"role": "user", "content": content_list}]


def _to_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float) and value.is_integer():
        return int(value)

    s = str(value).strip()
    if not s:
        return None
    try:
        parsed = json.loads(s)
        if isinstance(parsed, int):
            return int(parsed)
        if isinstance(parsed, float) and float(parsed).is_integer():
            return int(parsed)
    except Exception:
        pass
    matches = INT_RE.findall(s)
    if not matches:
        return None
    try:
        return int(matches[-1])
    except Exception:
        return None


def _extract_predicted_integer(response_text: str) -> Optional[int]:
    response_text = response_text or ""
    if extract_boxed_content is not None:
        try:
            boxed = extract_boxed_content(response_text)
            if boxed:
                boxed_int = _to_int(boxed)
                if boxed_int is not None:
                    return boxed_int
        except Exception:
            pass
    return _to_int(response_text)


def _process_image_local(image: Any, min_pixels: Optional[int], max_pixels: Optional[int]) -> Image.Image:
    """Local copy of RLVR image normalization to avoid importing full `verl` in utility scripts."""
    if isinstance(image, str):
        image = Image.open(image)
    elif isinstance(image, dict):
        image = Image.open(BytesIO(image["bytes"]))
    elif isinstance(image, bytes):
        image = Image.open(BytesIO(image))

    image.load()
    if max_pixels is not None and (image.width * image.height) > max_pixels:
        resize_factor = math.sqrt(max_pixels / (image.width * image.height))
        width, height = int(image.width * resize_factor), int(image.height * resize_factor)
        image = image.resize((width, height))

    if min_pixels is not None and (image.width * image.height) < min_pixels:
        resize_factor = math.sqrt(min_pixels / (image.width * image.height))
        width, height = int(image.width * resize_factor), int(image.height * resize_factor)
        image = image.resize((width, height))

    if image.mode != "RGB":
        image = image.convert("RGB")
    return image


def _normalize_images(raw_images: Any, min_pixels: int, max_pixels: int) -> List[Any]:
    if raw_images is None:
        return []
    if not isinstance(raw_images, list):
        raw_images = [raw_images]
    images = []
    for image in raw_images:
        images.append(_process_image_local(image, min_pixels=min_pixels, max_pixels=max_pixels))
    return images


def _bucket_fields(row: Dict[str, Any]) -> tuple[str, int, str, int]:
    task_variant_id = _to_int(row.get("task_variant_id"))
    count_bin = _to_int(row.get("count_bin"))
    task_variant_key = str(row.get("task_variant_key", "") or "")
    bucket_id_str = str(row.get("bucket_id_str", "") or "")

    if task_variant_id is None:
        task_variant_id = -1
    if count_bin is None:
        count_bin = -1
    if not bucket_id_str:
        bucket_id_str = f"{task_variant_id}-{count_bin}" if task_variant_id >= 0 and count_bin >= 0 else "unknown"
    return bucket_id_str, task_variant_id, task_variant_key, count_bin


def _build_vllm(
    model: str,
    tp_size: int,
    gpu_memory_utilization: float,
    trust_remote_code: bool,
    seed: int,
    limit_images: int,
) -> Any:
    try:
        from vllm import LLM
    except Exception as exc:  # pragma: no cover - runtime dependency
        raise RuntimeError(
            "vLLM is not installed in this environment. Install vllm in the RLVR runtime before running eval."
        ) from exc

    engine_kwargs: Dict[str, Any] = {}
    if limit_images > 0:
        engine_kwargs["limit_mm_per_prompt"] = {"image": int(limit_images)}
    return LLM(
        model=model,
        trust_remote_code=trust_remote_code,
        seed=seed,
        tensor_parallel_size=tp_size,
        gpu_memory_utilization=gpu_memory_utilization,
        disable_log_stats=True,
        mm_processor_cache_gb=0,
        **engine_kwargs,
    )


def _safe_float_mean(values: Iterable[float]) -> float:
    values = list(values)
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def main() -> int:
    args = _parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    dataset = _load_dataset_any(args.dataset)
    if args.max_samples > 0:
        dataset = dataset.select(range(min(args.max_samples, len(dataset))))

    if args.problem_key not in dataset.column_names:
        if "problem" in dataset.column_names:
            print(
                f"[warn] column '{args.problem_key}' not found. Falling back to 'problem'.",
                flush=True,
            )
            args.problem_key = "problem"
        else:
            raise KeyError(f"Missing prompt column '{args.problem_key}'. Available: {dataset.column_names}")
    if args.answer_key not in dataset.column_names:
        if "answer" in dataset.column_names:
            print(
                f"[warn] column '{args.answer_key}' not found. Falling back to 'answer'.",
                flush=True,
            )
            args.answer_key = "answer"
        else:
            raise KeyError(f"Missing answer column '{args.answer_key}'. Available: {dataset.column_names}")
    if args.image_key not in dataset.column_names:
        raise KeyError(f"Missing image column '{args.image_key}'. Available: {dataset.column_names}")

    format_template = _load_prompt_template(args.format_prompt)

    tp_size = max(1, int(args.tensor_parallel_size))

    print(
        f"[info] rows={len(dataset)} batch_size={args.batch_size} tp_size={tp_size} "
        f"problem_key={args.problem_key} answer_key={args.answer_key}",
        flush=True,
    )

    processor = AutoProcessor.from_pretrained(args.model, trust_remote_code=args.trust_remote_code)
    llm = _build_vllm(
        model=args.model,
        tp_size=tp_size,
        gpu_memory_utilization=float(args.gpu_memory_utilization),
        trust_remote_code=args.trust_remote_code,
        seed=int(args.seed),
        limit_images=int(args.limit_images),
    )
    try:
        from vllm import SamplingParams
    except Exception as exc:  # pragma: no cover - runtime dependency
        raise RuntimeError(
            "vLLM is not installed in this environment. Install vllm in the RLVR runtime before running eval."
        ) from exc
    sampling = SamplingParams(
        temperature=float(args.temperature),
        top_p=float(args.top_p),
        n=int(args.n),
        max_tokens=int(args.max_tokens),
    )

    predictions_path = out_dir / "predictions.jsonl"
    summary_path = out_dir / "summary.json"
    bucket_stats_path = out_dir / "bucket_stats.json"
    bucket_order_path = out_dir / "bucket_order.json"

    overall_correct = 0
    overall_parse_ok = 0
    overall_total = 0
    overall_abs_error_sum = 0.0
    overall_abs_error_n = 0

    by_bucket: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {
            "n": 0,
            "correct": 0,
            "parse_ok": 0,
            "abs_error_sum": 0.0,
            "abs_error_n": 0,
            "task_variant_id": -1,
            "task_variant_key": "",
            "count_bin": -1,
        }
    )

    by_variant: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"n": 0, "correct": 0, "parse_ok": 0, "abs_error_sum": 0.0, "abs_error_n": 0}
    )

    with predictions_path.open("w", encoding="utf-8") as pred_fp:
        iterator = range(0, len(dataset), int(args.batch_size))
        if not args.disable_tqdm:
            iterator = tqdm(iterator, total=math.ceil(len(dataset) / int(args.batch_size)), desc="Evaluating")

        for start in iterator:
            end = min(len(dataset), start + int(args.batch_size))
            requests: List[Dict[str, Any]] = []
            metas: List[Dict[str, Any]] = []

            for idx in range(start, end):
                row = dataset[int(idx)]
                prompt_text = str(row.get(args.problem_key, ""))
                if format_template is not None:
                    prompt_text = format_template.render(content=prompt_text)

                images = _normalize_images(
                    row.get(args.image_key),
                    min_pixels=int(args.min_pixels),
                    max_pixels=int(args.max_pixels),
                )
                messages = _build_messages(prompt_text, has_image=len(images) > 0)
                chat_prompt = processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)

                request: Dict[str, Any] = {"prompt": chat_prompt}
                if images:
                    request["multi_modal_data"] = {"image": images}
                requests.append(request)

                bucket_id_str, task_variant_id, task_variant_key, count_bin = _bucket_fields(row)
                gt_int = _to_int(row.get(args.answer_key))
                metas.append(
                    {
                        "index": int(idx),
                        "bucket_id_str": bucket_id_str,
                        "task_variant_id": int(task_variant_id),
                        "task_variant_key": str(task_variant_key),
                        "count_bin": int(count_bin),
                        "ground_truth_integer": gt_int,
                        "rendered_prompt": chat_prompt if args.include_prompt_in_predictions else None,
                    }
                )

            outputs = llm.generate(requests, sampling, use_tqdm=False)
            for meta, req_output in zip(metas, outputs):
                pred_text = ""
                if req_output.outputs:
                    pred_text = req_output.outputs[0].text
                pred_int = _extract_predicted_integer(pred_text)
                gt_int = meta["ground_truth_integer"]
                parse_ok = int(pred_int is not None)
                correct = int(pred_int is not None and gt_int is not None and pred_int == gt_int)
                abs_error: Optional[int] = None
                if pred_int is not None and gt_int is not None:
                    abs_error = abs(int(pred_int) - int(gt_int))

                record = EvalRecord(
                    index=int(meta["index"]),
                    bucket_id_str=str(meta["bucket_id_str"]),
                    task_variant_id=int(meta["task_variant_id"]),
                    task_variant_key=str(meta["task_variant_key"]),
                    count_bin=int(meta["count_bin"]),
                    ground_truth_integer=gt_int,
                    prediction_integer=pred_int,
                    prediction_text=pred_text,
                    correct=correct,
                    parse_ok=parse_ok,
                    abs_error=abs_error,
                )

                overall_total += 1
                overall_correct += record.correct
                overall_parse_ok += record.parse_ok
                if record.abs_error is not None:
                    overall_abs_error_sum += float(record.abs_error)
                    overall_abs_error_n += 1

                bucket = by_bucket[record.bucket_id_str]
                bucket["n"] += 1
                bucket["correct"] += record.correct
                bucket["parse_ok"] += record.parse_ok
                bucket["task_variant_id"] = record.task_variant_id
                bucket["task_variant_key"] = record.task_variant_key
                bucket["count_bin"] = record.count_bin
                if record.abs_error is not None:
                    bucket["abs_error_sum"] += float(record.abs_error)
                    bucket["abs_error_n"] += 1

                variant_key = record.task_variant_key or f"variant_{record.task_variant_id}"
                variant = by_variant[variant_key]
                variant["n"] += 1
                variant["correct"] += record.correct
                variant["parse_ok"] += record.parse_ok
                if record.abs_error is not None:
                    variant["abs_error_sum"] += float(record.abs_error)
                    variant["abs_error_n"] += 1

                rec_dict: Dict[str, Any] = {
                    "index": record.index,
                    "bucket_id_str": record.bucket_id_str,
                    "task_variant_id": record.task_variant_id,
                    "task_variant_key": record.task_variant_key,
                    "count_bin": record.count_bin,
                    "ground_truth_integer": record.ground_truth_integer,
                    "prediction_integer": record.prediction_integer,
                    "prediction_text": record.prediction_text,
                    "parse_ok": record.parse_ok,
                    "correct": record.correct,
                    "abs_error": record.abs_error,
                }
                if args.include_prompt_in_predictions:
                    rec_dict["rendered_prompt"] = meta["rendered_prompt"]
                pred_fp.write(json.dumps(rec_dict, ensure_ascii=False) + "\n")

    bucket_stats = []
    for bucket_id_str, stats in by_bucket.items():
        n = int(stats["n"])
        acc = (float(stats["correct"]) / n) if n else 0.0
        parse_rate = (float(stats["parse_ok"]) / n) if n else 0.0
        mae = (float(stats["abs_error_sum"]) / float(stats["abs_error_n"])) if stats["abs_error_n"] else None
        bucket_stats.append(
            {
                "bucket_id_str": bucket_id_str,
                "task_variant_id": int(stats["task_variant_id"]),
                "task_variant_key": str(stats["task_variant_key"]),
                "count_bin": int(stats["count_bin"]),
                "n": n,
                "accuracy": acc,
                "parse_rate": parse_rate,
                "mae": mae,
            }
        )

    def _bucket_sort_key(item: Dict[str, Any]) -> tuple[int, int, str]:
        return (int(item.get("task_variant_id", -1)), int(item.get("count_bin", -1)), str(item.get("bucket_id_str", "")))

    bucket_stats.sort(key=_bucket_sort_key)
    bucket_stats_path.write_text(json.dumps(bucket_stats, indent=2), encoding="utf-8")

    # Hard-to-easy ranking for fixed curriculum unlocking.
    # Tie-breakers keep ordering stable across reruns.
    rank_sorted = sorted(
        bucket_stats,
        key=lambda x: (
            float(x["accuracy"]),
            -float(x["parse_rate"]),
            -int(x["n"]),
            int(x["task_variant_id"]),
            int(x["count_bin"]),
        ),
    )
    bucket_order = [str(item["bucket_id_str"]) for item in rank_sorted]
    bucket_order_path.write_text(json.dumps(bucket_order, indent=2), encoding="utf-8")

    variant_stats = []
    for variant_key, stats in sorted(by_variant.items(), key=lambda kv: kv[0]):
        n = int(stats["n"])
        variant_stats.append(
            {
                "task_variant_key": variant_key,
                "n": n,
                "accuracy": (float(stats["correct"]) / n) if n else 0.0,
                "parse_rate": (float(stats["parse_ok"]) / n) if n else 0.0,
                "mae": (float(stats["abs_error_sum"]) / float(stats["abs_error_n"])) if stats["abs_error_n"] else None,
            }
        )

    summary = {
        "dataset": args.dataset,
        "model": args.model,
        "problem_key": args.problem_key,
        "answer_key": args.answer_key,
        "image_key": args.image_key,
        "rows": int(overall_total),
        "accuracy": (float(overall_correct) / float(overall_total)) if overall_total else 0.0,
        "parse_rate": (float(overall_parse_ok) / float(overall_total)) if overall_total else 0.0,
        "mae": (float(overall_abs_error_sum) / float(overall_abs_error_n)) if overall_abs_error_n else None,
        "bucket_count": len(bucket_stats),
        "task_variant_count": len(variant_stats),
        "tensor_parallel_size": int(tp_size),
        "batch_size": int(args.batch_size),
        "sampling": {
            "temperature": float(args.temperature),
            "top_p": float(args.top_p),
            "max_tokens": int(args.max_tokens),
            "n": int(args.n),
            "seed": int(args.seed),
        },
        "outputs": {
            "predictions_jsonl": str(predictions_path),
            "bucket_stats_json": str(bucket_stats_path),
            "bucket_order_json": str(bucket_order_path),
        },
        "variant_stats": variant_stats,
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(
        f"[done] accuracy={summary['accuracy']:.4f} parse_rate={summary['parse_rate']:.4f} "
        f"rows={summary['rows']} buckets={summary['bucket_count']}",
        flush=True,
    )
    print(f"[done] wrote: {predictions_path}", flush=True)
    print(f"[done] wrote: {bucket_stats_path}", flush=True)
    print(f"[done] wrote: {bucket_order_path}", flush=True)
    print(f"[done] wrote: {summary_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
