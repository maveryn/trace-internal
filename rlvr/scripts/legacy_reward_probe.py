from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("VLLM_LOGGING_LEVEL", "WARN")

from omegaconf import OmegaConf
import torch
from transformers import AutoProcessor, AutoTokenizer
from vllm import LLM, SamplingParams

from verl.utils.dataset.trace_rl_dataset import TraceRLHFDataset


def build_dataset(parquet_path: str, model: str, *, filter_overlong_prompts: bool) -> TraceRLHFDataset:
    tokenizer = AutoTokenizer.from_pretrained(model, trust_remote_code=False)
    processor = AutoProcessor.from_pretrained(model, trust_remote_code=False)
    config = OmegaConf.create(
        {
            "trace_output_mode": "answer",
            "prompt_key": "prompt_answer_only",
            "answer_key": "answer_gt",
            "image_key": "images",
            "video_key": "videos",
            "system_prompt": "__TRACE_NO_SYSTEM_PROMPT__",
            "max_prompt_length": 1536,
            "truncation": "error",
            "min_pixels": None,
            "max_pixels": 4194304,
            "filter_overlong_prompts": filter_overlong_prompts,
            "filter_overlong_prompts_workers": 1,
            "default_data_source": "trace_train_probe",
        }
    )
    dataset = TraceRLHFDataset(parquet_path, tokenizer=tokenizer, processor=processor, config=config)
    dataset.system_prompt = None
    return dataset


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parquet", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="Qwen/Qwen3-VL-2B-Instruct")
    parser.add_argument("--count", type=int, default=32)
    parser.add_argument("--shuffle-seed", type=int, default=None)
    parser.add_argument("--filter-overlong-prompts", action="store_true")
    parser.add_argument("--n", type=int, default=1)
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.7)
    parser.add_argument("--max-model-len", type=int, default=4096)
    parser.add_argument("--max-num-batched-tokens", type=int, default=4096)
    parser.add_argument("--max-num-seqs", type=int, default=64)
    parser.add_argument("--tensor-parallel-size", type=int, default=1)
    args = parser.parse_args()

    dataset = build_dataset(
        args.parquet,
        args.model,
        filter_overlong_prompts=args.filter_overlong_prompts,
    )
    if args.shuffle_seed is None:
        indices = list(range(args.count))
    else:
        generator = torch.Generator()
        generator.manual_seed(args.shuffle_seed)
        indices = torch.randperm(len(dataset), generator=generator).tolist()[: args.count]

    items = [dataset[i] for i in indices]

    requests = []
    rows = []
    for item in items:
        request = {"prompt_token_ids": list(item["raw_prompt_ids"])}
        if "multi_modal_data" in item:
            request["multi_modal_data"] = item["multi_modal_data"]
        requests.append(request)
        rows.append(
            {
                "dataset_index": indices[len(rows)],
                "uid": item.get("uid"),
                "prompt": item.get("extra_info", {}).get("prompt"),
                "ground_truth": item.get("ground_truth"),
                "answer_gt": item.get("answer_gt"),
                "annotation_gt": item.get("annotation_gt"),
                "reward_contract": item.get("reward_contract"),
                "metadata": item.get("metadata"),
                "trace_ref": item.get("trace_ref"),
                "data_source": item.get("data_source", "trace_train_probe"),
            }
        )

    llm = LLM(
        model=args.model,
        tensor_parallel_size=args.tensor_parallel_size,
        dtype="bfloat16",
        gpu_memory_utilization=args.gpu_memory_utilization,
        max_model_len=args.max_model_len,
        max_num_batched_tokens=args.max_num_batched_tokens,
        max_num_seqs=args.max_num_seqs,
        enforce_eager=True,
        enable_chunked_prefill=True,
        enable_prefix_caching=True,
        limit_mm_per_prompt={"image": 4},
        trust_remote_code=False,
        seed=1,
    )
    sampling_params = SamplingParams(
        n=args.n,
        temperature=args.temperature,
        top_p=1.0,
        top_k=-1,
        max_tokens=args.max_tokens,
        skip_special_tokens=True,
    )
    outputs = llm.generate(requests, sampling_params=sampling_params, use_tqdm=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for row, generated in zip(rows, outputs, strict=True):
            for rollout_index, completion in enumerate(generated.outputs):
                result = dict(row)
                result["rollout_index"] = rollout_index
                result["response"] = completion.text
                result["generated_tokens"] = len(completion.token_ids or [])
                handle.write(json.dumps(result, ensure_ascii=False) + "\n")

    print(args.output)


if __name__ == "__main__":
    main()
