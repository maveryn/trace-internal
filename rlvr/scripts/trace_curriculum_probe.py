from __future__ import annotations

import argparse
import base64
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
import gzip
from io import BytesIO
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("VLLM_LOGGING_LEVEL", "WARN")

RLVR_ROOT = Path(__file__).resolve().parents[1]
if str(RLVR_ROOT) not in sys.path:
    sys.path.insert(0, str(RLVR_ROOT))

_ANSWER_TAG_RE = re.compile(r"<answer>(.*?)</answer>", re.DOTALL | re.IGNORECASE)
_TRACE_REQUIRED_KEY_ORDER = {
    "answer": ["answer"],
    "answer_and_annotation": ["answer", "annotation"],
    "annotation": ["answer", "annotation"],
}


def _json_default(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def _maybe_parse_json_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("{"):
            parsed = json.loads(stripped)
            if isinstance(parsed, dict):
                return parsed
    raise TypeError(f"Expected a mapping-like TRACE metadata value, got {type(value).__name__}")


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _probe_jsonable(value: Any) -> Any:
    if value is Ellipsis:
        return "..."
    if isinstance(value, dict):
        return {str(key): _probe_jsonable(item_value) for key, item_value in value.items()}
    if isinstance(value, (list, tuple)):
        return [_probe_jsonable(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return [_probe_jsonable(item) for item in value]
    if not isinstance(value, (str, bytes)):
        if hasattr(value, "tolist"):
            try:
                return _probe_jsonable(value.tolist())
            except Exception:
                pass
        if hasattr(value, "item"):
            try:
                return _probe_jsonable(value.item())
            except Exception:
                pass
    return value


def _resolve_system_prompt_arg(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if normalized.lower() in {"", "none", "null", "__none__"}:
        return None
    return normalized


def _load_prompt_text(value: str | None) -> str | None:
    resolved = _resolve_system_prompt_arg(value)
    if resolved is None:
        return None
    path = Path(resolved)
    if path.exists():
        return path.read_text(encoding="utf-8")
    return resolved


def _build_dataset(
    parquet_path: str,
    model: str,
    *,
    trace_output_mode: str,
    prompt_key: str,
    system_prompt: str | None,
    max_prompt_length: int,
    max_pixels: int,
    filter_overlong_prompts: bool,
) -> Any:
    from omegaconf import OmegaConf
    from transformers import AutoProcessor, AutoTokenizer

    from verl.utils.dataset.trace_rl_dataset import TraceRLHFDataset

    tokenizer = AutoTokenizer.from_pretrained(model, trust_remote_code=False)
    processor = AutoProcessor.from_pretrained(model, trust_remote_code=False)
    config = OmegaConf.create(
        {
            "trace_output_mode": trace_output_mode,
            "prompt_key": prompt_key,
            "answer_key": "answer_gt",
            "image_key": "images",
            "video_key": "videos",
            "system_prompt": system_prompt if system_prompt is not None else "__TRACE_NO_SYSTEM_PROMPT__",
            "max_prompt_length": max_prompt_length,
            "truncation": "error",
            "min_pixels": None,
            "max_pixels": max_pixels,
            "filter_overlong_prompts": filter_overlong_prompts,
            "filter_overlong_prompts_workers": 1,
            "default_data_source": "trace_curriculum_probe",
        }
    )
    dataset = TraceRLHFDataset(parquet_path, tokenizer=tokenizer, processor=processor, config=config)
    if system_prompt is None:
        dataset.system_prompt = None
    return dataset


def _normalize_probe_response(
    *,
    response: str,
    trace_reward_mode: str,
) -> tuple[str, str]:
    """Normalize one probe response for lenient curriculum scoring.

    Probe-only extraction policy:
    1. prefer the final JSON object
    2. otherwise fall back to valid JSON found anywhere in the response, including legacy `<answer>...</answer>`
    """

    from verl.utils.trace_reward import extract_trace_prediction

    answer_value, annotation_value, json_found = extract_trace_prediction(response)
    if not json_found:
        return response, "none"

    normalized_mode = str(trace_reward_mode or "").strip().lower()
    if normalized_mode in {"answer", "answer_only"}:
        if answer_value is None:
            return response, "none"
        payload: dict[str, Any] = {"answer": answer_value}
    else:
        payload = {}
        if answer_value is not None:
            payload["answer"] = answer_value
        if annotation_value is not None:
            payload["annotation"] = annotation_value
        if not payload:
            return response, "none"
    payload = _probe_jsonable(payload)
    return (
        json.dumps(payload, ensure_ascii=False, default=_json_default),
        "final_json_then_json_fallback",
    )


def _build_requests(batch_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    for item in batch_items:
        request: dict[str, Any] = {"prompt_token_ids": list(item["raw_prompt_ids"])}
        if "multi_modal_data" in item:
            request["multi_modal_data"] = item["multi_modal_data"]
        requests.append(request)
    return requests


@dataclass(frozen=True)
class _ProbeCompletion:
    text: str
    token_ids: list[int]


@dataclass(frozen=True)
class _ProbeGeneration:
    outputs: list[_ProbeCompletion]


def _image_to_data_url(image: Any) -> str:
    if isinstance(image, str):
        if image.startswith("data:"):
            return image
        path = Path(image)
        payload = path.read_bytes()
        suffix = path.suffix.lower().lstrip(".") or "png"
        mime = "jpeg" if suffix in {"jpg", "jpeg"} else suffix
        return f"data:image/{mime};base64,{base64.b64encode(payload).decode('ascii')}"
    if isinstance(image, bytes):
        return f"data:image/png;base64,{base64.b64encode(image).decode('ascii')}"
    if not hasattr(image, "save"):
        raise TypeError(f"Unsupported image payload type for OpenAI server backend: {type(image).__name__}")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode('ascii')}"


def _content_from_prompt_and_images(prompt: str, images: list[Any]) -> list[dict[str, Any]]:
    parts = str(prompt).split("<image>")
    content: list[dict[str, Any]] = []
    image_index = 0
    for part_index, text in enumerate(parts):
        if text:
            content.append({"type": "text", "text": text})
        if part_index < len(parts) - 1 and image_index < len(images):
            content.append({"type": "image_url", "image_url": {"url": _image_to_data_url(images[image_index])}})
            image_index += 1
    while image_index < len(images):
        content.insert(0, {"type": "image_url", "image_url": {"url": _image_to_data_url(images[image_index])}})
        image_index += 1
    if not content:
        content.append({"type": "text", "text": str(prompt)})
    return content


def _openai_messages_for_item(item: dict[str, Any], *, system_prompt: str | None) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    if system_prompt is not None:
        messages.append({"role": "system", "content": system_prompt})
    images = list((item.get("multi_modal_data") or {}).get("image") or [])
    messages.append(
        {
            "role": "user",
            "content": _content_from_prompt_and_images(str(item.get("prompt") or ""), images),
        }
    )
    return messages


def _server_url(base_url: str) -> str:
    base = str(base_url).rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


def _openai_server_completion(
    *,
    args: argparse.Namespace,
    item: dict[str, Any],
    tokenizer: Any,
    system_prompt: str | None,
) -> _ProbeGeneration:
    import requests

    model_name = str(args.server_model or args.model)
    payload: dict[str, Any] = {
        "model": model_name,
        "messages": _openai_messages_for_item(item, system_prompt=system_prompt),
        "n": int(args.rollouts_per_prompt),
        "temperature": float(args.temperature),
        "top_p": 1.0,
        "max_tokens": int(args.max_tokens),
    }
    headers = {"Content-Type": "application/json"}
    api_key = str(args.server_api_key or os.environ.get("TRACE_VLLM_API_KEY") or os.environ.get("OPENAI_API_KEY") or "EMPTY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    last_error: Exception | None = None
    for attempt in range(max(1, int(args.server_max_retries))):
        try:
            response = requests.post(
                _server_url(str(args.server_base_url)),
                headers=headers,
                json=payload,
                timeout=float(args.server_timeout),
            )
            response.raise_for_status()
            body = response.json()
            completions: list[_ProbeCompletion] = []
            for choice in body.get("choices", []):
                message = choice.get("message") if isinstance(choice, dict) else {}
                text = str((message or {}).get("content") or "")
                finish_reason = str(choice.get("finish_reason") or "") if isinstance(choice, dict) else ""
                if finish_reason == "length":
                    token_ids = [0] * int(args.max_tokens)
                else:
                    try:
                        token_ids = list(tokenizer.encode(text, add_special_tokens=False))
                    except TypeError:
                        token_ids = list(tokenizer.encode(text))
                completions.append(_ProbeCompletion(text=text, token_ids=token_ids))
            if len(completions) != int(args.rollouts_per_prompt):
                raise RuntimeError(
                    f"OpenAI server returned {len(completions)} choices; expected {int(args.rollouts_per_prompt)}"
                )
            return _ProbeGeneration(outputs=completions)
        except Exception as exc:
            last_error = exc
            if attempt + 1 >= max(1, int(args.server_max_retries)):
                break
            time.sleep(min(30.0, 1.5 ** attempt))
    assert last_error is not None
    raise last_error


def _generate_with_openai_server(
    *,
    args: argparse.Namespace,
    batch_items: list[dict[str, Any]],
    tokenizer: Any,
    system_prompt: str | None,
) -> list[_ProbeGeneration]:
    max_workers = max(1, min(len(batch_items), int(args.server_concurrency)))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                _openai_server_completion,
                args=args,
                item=item,
                tokenizer=tokenizer,
                system_prompt=system_prompt,
            )
            for item in batch_items
        ]
        return [future.result() for future in futures]


def _prepare_batch_payload(
    *,
    dataset: Any,
    batch_indices: list[int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    batch_items = [dataset[index] for index in batch_indices]
    requests = _build_requests(batch_items)
    return batch_items, requests


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def _detect_visible_gpu_ids() -> list[str]:
    visible = os.environ.get("CUDA_VISIBLE_DEVICES", "").strip()
    if visible:
        return [part.strip() for part in visible.split(",") if part.strip()]
    output = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=index", "--format=csv,noheader"],
        text=True,
    )
    return [line.strip() for line in output.splitlines() if line.strip()]


def _split_prompt_ranges(start_index: int, end_index: int, shard_count: int) -> list[tuple[int, int]]:
    total = max(0, end_index - start_index)
    if total <= 0:
        return []
    shard_count = max(1, min(shard_count, total))
    base = total // shard_count
    remainder = total % shard_count
    cursor = start_index
    ranges: list[tuple[int, int]] = []
    for shard_rank in range(shard_count):
        shard_size = base + (1 if shard_rank < remainder else 0)
        shard_end = cursor + shard_size
        ranges.append((cursor, shard_end))
        cursor = shard_end
    return ranges


def _prompt_batch_size_from_rollout_budget(batch_size: int, rollouts_per_prompt: int) -> int:
    """Convert a rollout batch budget into the prompt chunk size sent to vLLM."""

    return max(1, int(batch_size) // max(1, int(rollouts_per_prompt)))


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, default=_json_default), encoding="utf-8")
    tmp_path.replace(path)


def _count_jsonl_rows(path: Path) -> int:
    if not path.exists():
        return 0
    opener = gzip.open if str(path).endswith(".gz") else open
    count = 0
    with opener(path, "rt", encoding="utf-8", errors="ignore") as handle:
        for count, _ in enumerate(handle, 1):
            pass
    return count


def _parse_json_mapping_or_none(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("{"):
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                return None
            if isinstance(parsed, dict):
                return parsed
    return None


def _score_trace_response_with_item(
    *,
    response: str,
    item: dict[str, Any],
    answer_gt: dict[str, Any],
    annotation_gt: dict[str, Any],
    reward_contract: dict[str, Any],
    trace_reward_mode: str,
    trace_answer_scoring: str,
    format_weight: float,
) -> dict[str, float]:
    from verl.utils.trace_reward import score_trace_response

    return score_trace_response(
        response=response,
        answer_gt=answer_gt,
        annotation_gt=annotation_gt,
        reward_contract=reward_contract,
        image_size=item.get("image_size") or item.get("source_image_size"),
        image_sizes=item.get("image_sizes"),
        metadata=item.get("metadata"),
        extra_info=item.get("extra_info"),
        trace_reward_mode=trace_reward_mode,
        trace_answer_scoring=trace_answer_scoring,
        format_weight=format_weight,
    )


def _effective_per_rollout_response_mode(args: argparse.Namespace) -> str:
    response_mode = str(getattr(args, "per_rollout_response_mode", "none") or "none")
    if str(getattr(args, "diagnostics_mode", "none")) == "annotation_eval" and response_mode == "none":
        return "full"
    return response_mode


def _should_write_per_rollout(args: argparse.Namespace) -> bool:
    return bool(getattr(args, "write_per_rollout", False)) or str(getattr(args, "diagnostics_mode", "none")) == "annotation_eval"


def _stored_response_text(response: str, *, mode: str, max_chars: int) -> str | None:
    if mode == "none":
        return None
    if mode == "full":
        return response
    max_chars = max(0, int(max_chars))
    if len(response) <= max_chars:
        return response
    return response[:max_chars]


def _required_key_order(trace_reward_mode: str) -> list[str]:
    normalized = str(trace_reward_mode or "").strip().lower()
    if normalized == "auto":
        normalized = "answer_and_annotation"
    return list(_TRACE_REQUIRED_KEY_ORDER.get(normalized, ["annotation", "answer"]))


def _diagnose_trace_response(
    *,
    response: str,
    token_count: int,
    max_tokens: int,
    strict_score: dict[str, float],
    trace_reward_mode: str,
) -> dict[str, Any]:
    from verl.utils.trace_reward import evaluate_trace_response_format

    format_details = evaluate_trace_response_format(response, trace_reward_mode=trace_reward_mode)
    payload = format_details.get("payload") if isinstance(format_details.get("payload"), dict) else None
    required_order = _required_key_order(trace_reward_mode)
    required_keys = set(required_order)
    payload_keys = list(payload.keys()) if isinstance(payload, dict) else []
    missing_keys = sorted(required_keys.difference(payload_keys))
    extra_keys = sorted(set(payload_keys).difference(required_keys))
    key_order_ok = bool(payload_keys == required_order) if isinstance(payload, dict) else False
    answer_tag_count = len(_ANSWER_TAG_RE.findall(response))

    categories: list[str] = []
    if int(token_count) >= int(max_tokens):
        categories.append("hit_response_cap")
    if not bool(format_details.get("structure_ok")):
        categories.append("missing_final_json_object")
    if not bool(strict_score.get("json_found", 0.0)):
        categories.append("json_missing")
    if bool(format_details.get("structure_ok")) and not bool(format_details.get("json_ok")):
        categories.append("json_invalid_in_final_object")
    if isinstance(payload, dict):
        if missing_keys:
            categories.append("missing_required_keys")
        if extra_keys:
            categories.append("extra_keys")
        if not key_order_ok:
            categories.append("wrong_key_order")
    elif bool(format_details.get("json_ok")):
        categories.append("json_not_object")
    if not bool(strict_score.get("answer_parse_ok", 0.0)):
        categories.append("answer_parse_failed")
    if trace_reward_mode != "answer" and not bool(strict_score.get("annotation_parse_ok", 0.0)):
        categories.append("annotation_parse_failed")
    if float(strict_score.get("answer_reward", 0.0)) <= 0.0:
        categories.append("answer_wrong")
    if trace_reward_mode != "answer" and float(strict_score.get("annotation_reward", 0.0)) <= 0.0:
        categories.append("annotation_zero")
    if float(strict_score.get("task_reward_raw", 0.0)) <= 0.0 and not categories:
        categories.append("task_reward_zero")

    return {
        "answer_tag_count": int(answer_tag_count),
        "missing_keys": missing_keys,
        "extra_keys": extra_keys,
        "key_order_ok": bool(key_order_ok),
        "payload_keys": payload_keys,
        "failure_categories": categories,
    }


def _build_per_rollout_row(
    *,
    dataset_index: int,
    item: dict[str, Any],
    rollout_index: int,
    response: str,
    token_count: int,
    max_tokens: int,
    strict_score: dict[str, float],
    fallback_score: dict[str, float],
    extraction_source: str,
    trace_reward_mode: str,
    response_mode: str,
    response_max_chars: int,
) -> dict[str, Any]:
    answer_gt = _maybe_parse_json_mapping(item["answer_gt"])
    annotation_gt = _maybe_parse_json_mapping(item["annotation_gt"])
    diagnostics = _diagnose_trace_response(
        response=response,
        token_count=token_count,
        max_tokens=max_tokens,
        strict_score=strict_score,
        trace_reward_mode=trace_reward_mode,
    )

    row: dict[str, Any] = {
        "dataset_index": int(dataset_index),
        "uid": str(item.get("uid", "")),
        "domain": str(item.get("domain", "")),
        "scene_id": str(item.get("scene_id", "")),
        "task": str(item.get("task", "")),
        "query_id": None,
        "difficulty_bin": None if item.get("difficulty_bin") is None else int(item.get("difficulty_bin")),
        "bucket_id_str": None if item.get("bucket_id_str") is None else str(item.get("bucket_id_str")),
        "rollout_index": int(rollout_index),
        "generated_tokens": int(token_count),
        "max_generation_tokens_setting": int(max_tokens),
        "hit_response_cap": bool(int(token_count) >= int(max_tokens)),
        "answer_type": str(answer_gt.get("type", "")),
        "annotation_type": str(annotation_gt.get("type", "")),
        "extraction_source": str(extraction_source),
        **diagnostics,
    }
    metadata = _parse_json_mapping_or_none(item.get("metadata"))
    if metadata is not None:
        query_id = metadata.get("query_id")
        if query_id is not None:
            row["query_id"] = str(query_id)

    for prefix, score in (("strict", strict_score), ("fallback", fallback_score)):
        row[f"{prefix}_task_reward"] = float(score.get("task_reward_raw", 0.0))
        row[f"{prefix}_answer_reward"] = float(score.get("answer_reward", 0.0))
        row[f"{prefix}_annotation_reward"] = float(score.get("annotation_reward", 0.0))
        row[f"{prefix}_overall_reward"] = float(score.get("overall", 0.0))
        row[f"{prefix}_format_reward"] = float(score.get("format", 0.0))
        row[f"{prefix}_json_found"] = bool(score.get("json_found", 0.0))
        row[f"{prefix}_format_structure_ok"] = bool(score.get("format_structure_ok", 0.0))
        row[f"{prefix}_format_json_ok"] = bool(score.get("format_json_ok", 0.0))
        row[f"{prefix}_format_schema_ok"] = bool(score.get("format_schema_ok", 0.0))
        row[f"{prefix}_answer_parse_ok"] = bool(score.get("answer_parse_ok", 0.0))
        row[f"{prefix}_annotation_parse_ok"] = bool(score.get("annotation_parse_ok", 0.0))
        row[f"{prefix}_positive"] = bool(float(score.get("task_reward_raw", 0.0)) > 0.0)
        row[f"{prefix}_perfect"] = bool(float(score.get("task_reward_raw", 0.0)) >= 1.0)
        for key, value in score.items():
            if key.startswith("annotation_") and isinstance(value, (int, float)):
                row[f"{prefix}_{key}"] = float(value)

    stored_response = _stored_response_text(
        response,
        mode=response_mode,
        max_chars=response_max_chars,
    )
    if stored_response is not None:
        row["response"] = stored_response
        row["response_truncated"] = bool(response_mode == "truncated" and len(response) > int(response_max_chars))
        row["response_char_count"] = int(len(response))
    return row


def _build_instance_row(
    *,
    dataset_index: int,
    item: dict[str, Any],
    rollout_scores: list[dict[str, float]],
    token_counts: list[int],
    extraction_sources: list[str],
    max_tokens: int,
) -> dict[str, Any]:
    task_rewards = [float(score["task_reward_raw"]) for score in rollout_scores]
    answer_rewards = [float(score["answer_reward"]) for score in rollout_scores]
    overall_rewards = [float(score["overall"]) for score in rollout_scores]
    format_rewards = [float(score["format"]) for score in rollout_scores]
    json_found = [float(score["json_found"]) for score in rollout_scores]
    format_json_ok = [float(score["format_json_ok"]) for score in rollout_scores]
    format_schema_ok = [float(score["format_schema_ok"]) for score in rollout_scores]

    positive_rollout_count = sum(1 for reward in task_rewards if float(reward) > 0.0)
    perfect_rollout_count = sum(1 for reward in task_rewards if float(reward) >= 1.0)
    rollout_count = len(rollout_scores)
    max_token_rollout_count = sum(1 for count in token_counts if int(count) == int(max_tokens))
    extraction_none_count = sum(1 for source in extraction_sources if str(source) == "none")
    crop_or_no_extract_rollout_count = sum(
        1
        for count, source in zip(token_counts, extraction_sources, strict=True)
        if int(count) == int(max_tokens) or str(source) == "none"
    )
    answer_gt = _maybe_parse_json_mapping(item["answer_gt"])
    annotation_gt = _maybe_parse_json_mapping(item["annotation_gt"])

    return {
        "dataset_index": int(dataset_index),
        "uid": str(item.get("uid", "")),
        "domain": str(item.get("domain", "")),
        "scene_id": str(item.get("scene_id", "")),
        "task": str(item.get("task", "")),
        "difficulty_bin": None if item.get("difficulty_bin") is None else int(item.get("difficulty_bin")),
        "bucket_id_str": None if item.get("bucket_id_str") is None else str(item.get("bucket_id_str")),
        "prompt_length": int(len(item["raw_prompt_ids"])),
        "rollout_count": int(rollout_count),
        "positive_rollout_count": int(positive_rollout_count),
        "perfect_rollout_count": int(perfect_rollout_count),
        "solve_rate": float(positive_rollout_count / rollout_count) if rollout_count else 0.0,
        "perfect_rate": float(perfect_rollout_count / rollout_count) if rollout_count else 0.0,
        "zero_solve": bool(positive_rollout_count == 0),
        "perfect_solve": bool(perfect_rollout_count == rollout_count and rollout_count > 0),
        "mean_task_reward": _mean(task_rewards),
        "mean_answer_reward": _mean(answer_rewards),
        "mean_overall_reward": _mean(overall_rewards),
        "mean_format_reward": _mean(format_rewards),
        "json_found_rate": _mean(json_found),
        "format_json_ok_rate": _mean(format_json_ok),
        "format_schema_ok_rate": _mean(format_schema_ok),
        "probe_extraction_fallback_rate": _mean([1.0 if source != "none" else 0.0 for source in extraction_sources]),
        "mean_generated_tokens": _mean([float(count) for count in token_counts]),
        "max_generated_tokens": max(token_counts) if token_counts else 0,
        "max_generation_tokens_setting": int(max_tokens),
        "max_token_rollout_count": int(max_token_rollout_count),
        "max_token_rollout_rate": float(max_token_rollout_count / rollout_count) if rollout_count else 0.0,
        "extraction_none_count": int(extraction_none_count),
        "extraction_none_rate": float(extraction_none_count / rollout_count) if rollout_count else 0.0,
        "crop_or_no_extract_rollout_count": int(crop_or_no_extract_rollout_count),
        "crop_or_no_extract_rate": float(crop_or_no_extract_rollout_count / rollout_count) if rollout_count else 0.0,
        "answer_type": str(answer_gt.get("type", "")),
        "annotation_type": str(annotation_gt.get("type", "")),
    }


def _empty_aggregate() -> dict[str, float]:
    return {
        "prompt_count": 0,
        "rollout_count": 0,
        "positive_rollout_count": 0,
        "perfect_rollout_count": 0,
        "zero_solve_count": 0,
        "perfect_solve_count": 0,
        "sum_mean_task_reward": 0.0,
        "sum_mean_answer_reward": 0.0,
        "sum_mean_overall_reward": 0.0,
        "sum_mean_format_reward": 0.0,
        "sum_prompt_length": 0.0,
        "sum_mean_generated_tokens": 0.0,
        "max_generated_tokens": 0.0,
    }


def _update_aggregate(aggregate: dict[str, float], row: dict[str, Any]) -> None:
    aggregate["prompt_count"] += 1
    aggregate["rollout_count"] += int(row["rollout_count"])
    aggregate["positive_rollout_count"] += int(row["positive_rollout_count"])
    aggregate["perfect_rollout_count"] += int(row["perfect_rollout_count"])
    aggregate["zero_solve_count"] += 1 if bool(row["zero_solve"]) else 0
    aggregate["perfect_solve_count"] += 1 if bool(row["perfect_solve"]) else 0
    aggregate["sum_mean_task_reward"] += float(row["mean_task_reward"])
    aggregate["sum_mean_answer_reward"] += float(row["mean_answer_reward"])
    aggregate["sum_mean_overall_reward"] += float(row["mean_overall_reward"])
    aggregate["sum_mean_format_reward"] += float(row["mean_format_reward"])
    aggregate["sum_prompt_length"] += float(row["prompt_length"])
    aggregate["sum_mean_generated_tokens"] += float(row["mean_generated_tokens"])
    aggregate["max_generated_tokens"] = max(float(aggregate["max_generated_tokens"]), float(row["max_generated_tokens"]))


def _finalize_aggregate(name: str, aggregate: dict[str, float]) -> dict[str, Any]:
    prompt_count = int(aggregate["prompt_count"])
    rollout_count = int(aggregate["rollout_count"])
    return {
        "name": str(name),
        "prompt_count": prompt_count,
        "rollout_count": rollout_count,
        "positive_rollout_rate": float(aggregate["positive_rollout_count"] / rollout_count) if rollout_count else 0.0,
        "perfect_rollout_rate": float(aggregate["perfect_rollout_count"] / rollout_count) if rollout_count else 0.0,
        "zero_solve_rate": float(aggregate["zero_solve_count"] / prompt_count) if prompt_count else 0.0,
        "perfect_solve_rate": float(aggregate["perfect_solve_count"] / prompt_count) if prompt_count else 0.0,
        "mean_task_reward": float(aggregate["sum_mean_task_reward"] / prompt_count) if prompt_count else 0.0,
        "mean_answer_reward": float(aggregate["sum_mean_answer_reward"] / prompt_count) if prompt_count else 0.0,
        "mean_overall_reward": float(aggregate["sum_mean_overall_reward"] / prompt_count) if prompt_count else 0.0,
        "mean_format_reward": float(aggregate["sum_mean_format_reward"] / prompt_count) if prompt_count else 0.0,
        "mean_prompt_length": float(aggregate["sum_prompt_length"] / prompt_count) if prompt_count else 0.0,
        "mean_generated_tokens": float(aggregate["sum_mean_generated_tokens"] / prompt_count) if prompt_count else 0.0,
        "max_generated_tokens": int(aggregate["max_generated_tokens"]),
    }


def _run_single_probe(args: argparse.Namespace) -> dict[str, Any]:
    from tqdm.auto import tqdm

    args.output_dir.mkdir(parents=True, exist_ok=True)

    system_prompt = _resolve_system_prompt_arg(args.system_prompt)
    system_prompt_text = _load_prompt_text(args.system_prompt)
    dataset = _build_dataset(
        args.parquet,
        args.model,
        trace_output_mode=args.trace_output_mode,
        prompt_key=args.prompt_key,
        system_prompt=system_prompt,
        max_prompt_length=args.max_prompt_length,
        max_pixels=args.max_pixels,
        filter_overlong_prompts=args.filter_overlong_prompts,
    )

    start_index = max(0, int(args.start_index))
    dataset_len = len(dataset)
    if start_index >= dataset_len:
        raise ValueError(f"start_index={start_index} is outside dataset length {dataset_len}")
    end_index = dataset_len if args.count is None else min(dataset_len, start_index + max(0, int(args.count)))
    total_prompts = max(0, end_index - start_index)
    if total_prompts <= 0:
        raise ValueError("No prompts selected for probing")

    llm = None
    sampling_params = None
    if str(args.backend) == "local_vllm":
        from vllm import LLM, SamplingParams

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
            seed=args.seed,
        )
        sampling_params = SamplingParams(
            n=args.rollouts_per_prompt,
            temperature=args.temperature,
            top_p=1.0,
            top_k=-1,
            max_tokens=args.max_tokens,
            skip_special_tokens=True,
        )

    per_instance_path = args.output_dir / "per_instance.jsonl"
    per_rollout_path = args.output_dir / "per_rollout.jsonl.gz"
    summary_path = args.output_dir / "summary.json"
    task_summary_path = args.output_dir / "per_task_summary.json"
    bucket_summary_path = args.output_dir / "per_task_bucket_summary.json"
    progress_path = Path(args.progress_file) if getattr(args, "progress_file", None) else None
    append_output = bool(getattr(args, "append_output", False))
    existing_rows = _count_jsonl_rows(per_instance_path) if append_output else 0
    write_per_rollout = _should_write_per_rollout(args)
    response_mode = _effective_per_rollout_response_mode(args)

    overall_aggregate = _empty_aggregate()
    task_aggregates: dict[str, dict[str, float]] = defaultdict(_empty_aggregate)
    bucket_aggregates: dict[str, dict[str, float]] = defaultdict(_empty_aggregate)
    prompt_batch_size = _prompt_batch_size_from_rollout_budget(args.batch_size, args.rollouts_per_prompt)
    batch_ranges = [
        (batch_start, min(end_index, batch_start + prompt_batch_size))
        for batch_start in range(start_index, end_index, prompt_batch_size)
    ]

    file_mode = "a" if append_output else "w"
    rollout_file_mode = "at" if append_output else "wt"
    per_rollout_handle = gzip.open(per_rollout_path, rollout_file_mode, encoding="utf-8") if write_per_rollout else None
    try:
        with per_instance_path.open(file_mode, encoding="utf-8") as handle, tqdm(
            total=total_prompts,
            desc="Curriculum probe",
            unit="prompt",
            disable=bool(progress_path),
        ) as progress:
            completed_prompts = existing_rows
            prefetch_workers = max(0, int(args.prefetch_workers))
            with ThreadPoolExecutor(max_workers=max(1, prefetch_workers or 1)) as executor:
                current_indices = list(range(*batch_ranges[0]))
                if prefetch_workers > 0:
                    current_batch_items, current_requests = _prepare_batch_payload(
                        dataset=dataset,
                        batch_indices=current_indices,
                    )
                    prefetch_future: Future[tuple[list[dict[str, Any]], list[dict[str, Any]]]] | None = None
                else:
                    current_batch_items, current_requests = _prepare_batch_payload(
                        dataset=dataset,
                        batch_indices=current_indices,
                    )
                    prefetch_future = None

                for batch_idx, batch_range in enumerate(batch_ranges):
                    batch_start, batch_end = batch_range
                    batch_indices = list(range(batch_start, batch_end))

                    if batch_idx > 0:
                        if prefetch_future is not None:
                            current_batch_items, current_requests = prefetch_future.result()
                        else:
                            current_batch_items, current_requests = _prepare_batch_payload(
                                dataset=dataset,
                                batch_indices=batch_indices,
                            )

                    next_batch_idx = batch_idx + 1
                    if prefetch_workers > 0 and next_batch_idx < len(batch_ranges):
                        next_batch_start, next_batch_end = batch_ranges[next_batch_idx]
                        next_batch_indices = list(range(next_batch_start, next_batch_end))
                        prefetch_future = executor.submit(
                            _prepare_batch_payload,
                            dataset=dataset,
                            batch_indices=next_batch_indices,
                        )
                    else:
                        prefetch_future = None

                    if str(args.backend) == "openai_server":
                        outputs = _generate_with_openai_server(
                            args=args,
                            batch_items=current_batch_items,
                            tokenizer=dataset.tokenizer,
                            system_prompt=system_prompt_text,
                        )
                    else:
                        assert llm is not None and sampling_params is not None
                        outputs = llm.generate(current_requests, sampling_params=sampling_params, use_tqdm=False)

                    batch_solve_rates: list[float] = []
                    for dataset_index, item, generated in zip(batch_indices, current_batch_items, outputs, strict=True):
                        rollout_scores: list[dict[str, float]] = []
                        token_counts: list[int] = []
                        extraction_sources: list[str] = []
                        answer_gt = _maybe_parse_json_mapping(item["answer_gt"])
                        annotation_gt = _maybe_parse_json_mapping(item["annotation_gt"])
                        reward_contract = _maybe_parse_json_mapping(item["reward_contract"])

                        for rollout_index, completion in enumerate(generated.outputs):
                            response = completion.text
                            token_count = len(completion.token_ids or [])
                            strict_score = _score_trace_response_with_item(
                                response=response,
                                item=item,
                                answer_gt=answer_gt,
                                annotation_gt=annotation_gt,
                                reward_contract=reward_contract,
                                trace_reward_mode=args.trace_reward_mode,
                                trace_answer_scoring=args.trace_answer_scoring,
                                format_weight=args.trace_format_weight,
                            )
                            normalized_response, extraction_source = _normalize_probe_response(
                                response=response,
                                trace_reward_mode=args.trace_reward_mode,
                            )
                            fallback_score = _score_trace_response_with_item(
                                response=normalized_response,
                                item=item,
                                answer_gt=answer_gt,
                                annotation_gt=annotation_gt,
                                reward_contract=reward_contract,
                                trace_reward_mode=args.trace_reward_mode,
                                trace_answer_scoring=args.trace_answer_scoring,
                                format_weight=args.trace_format_weight,
                            )
                            primary_score = strict_score if str(args.diagnostics_mode) == "annotation_eval" else fallback_score
                            rollout_scores.append(primary_score)
                            extraction_sources.append(str(extraction_source))
                            token_counts.append(token_count)
                            if per_rollout_handle is not None:
                                per_rollout_handle.write(
                                    json.dumps(
                                        _build_per_rollout_row(
                                            dataset_index=dataset_index,
                                            item=item,
                                            rollout_index=rollout_index,
                                            response=response,
                                            token_count=token_count,
                                            max_tokens=int(args.max_tokens),
                                            strict_score=strict_score,
                                            fallback_score=fallback_score,
                                            extraction_source=str(extraction_source),
                                            trace_reward_mode=args.trace_reward_mode,
                                            response_mode=response_mode,
                                            response_max_chars=int(args.per_rollout_response_max_chars),
                                        ),
                                        ensure_ascii=False,
                                        default=_json_default,
                                    )
                                    + "\n"
                                )

                        row = _build_instance_row(
                            dataset_index=dataset_index,
                            item=item,
                            rollout_scores=rollout_scores,
                            token_counts=token_counts,
                            extraction_sources=extraction_sources,
                            max_tokens=int(args.max_tokens),
                        )
                        handle.write(json.dumps(row, ensure_ascii=False, default=_json_default) + "\n")

                        _update_aggregate(overall_aggregate, row)
                        task_key = str(row["task"])
                        bucket_key = f"{task_key}::{row['bucket_id_str'] if row['bucket_id_str'] is not None else row['difficulty_bin']}"
                        _update_aggregate(task_aggregates[task_key], row)
                        _update_aggregate(bucket_aggregates[bucket_key], row)
                        batch_solve_rates.append(float(row["solve_rate"]))

                    progress.update(len(batch_indices))
                    completed_prompts += len(batch_indices)
                    progress.set_postfix(
                        batch_prompts=len(batch_indices),
                        batch_solve_rate=f"{_mean(batch_solve_rates):.3f}",
                        global_solve_rate=f"{_finalize_aggregate('overall', overall_aggregate)['positive_rollout_rate']:.3f}",
                        prefetch_workers=prefetch_workers,
                    )
                    if progress_path is not None:
                        _write_json_atomic(
                            progress_path,
                            {
                                "prompts_completed": completed_prompts,
                                "prompts_total": total_prompts,
                                "last_batch_size": len(batch_indices),
                                "last_batch_solve_rate": _mean(batch_solve_rates),
                            },
                        )
    finally:
        if per_rollout_handle is not None:
            per_rollout_handle.close()

    summary = {
        "parquet": str(Path(args.parquet).resolve()),
        "model": args.model,
        "selected_range": {
            "start_index": start_index,
            "end_index_exclusive": end_index,
            "prompt_count": total_prompts,
        },
        "settings": {
            "trace_output_mode": args.trace_output_mode,
            "prompt_key": args.prompt_key,
            "system_prompt": system_prompt,
            "trace_reward_mode": args.trace_reward_mode,
            "trace_answer_scoring": args.trace_answer_scoring,
            "probe_extraction_mode": "final_json_then_json_fallback",
            "trace_format_weight": args.trace_format_weight,
            "backend": args.backend,
            "server_base_url": args.server_base_url if str(args.backend) == "openai_server" else None,
            "server_model": (args.server_model or args.model) if str(args.backend) == "openai_server" else None,
            "server_concurrency": args.server_concurrency if str(args.backend) == "openai_server" else None,
            "batch_size": args.batch_size,
            "effective_prompt_batch_size": prompt_batch_size,
            "effective_rollout_batch_size": prompt_batch_size * args.rollouts_per_prompt,
            "rollouts_per_prompt": args.rollouts_per_prompt,
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "tensor_parallel_size": args.tensor_parallel_size,
            "gpu_memory_utilization": args.gpu_memory_utilization,
            "max_model_len": args.max_model_len,
            "max_num_batched_tokens": args.max_num_batched_tokens,
            "max_num_seqs": args.max_num_seqs,
            "max_prompt_length": args.max_prompt_length,
            "max_pixels": args.max_pixels,
            "filter_overlong_prompts": args.filter_overlong_prompts,
            "prefetch_workers": args.prefetch_workers,
            "seed": args.seed,
            "enforce_eager": args.enforce_eager,
            "diagnostics_mode": args.diagnostics_mode,
            "primary_scoring_mode": "strict_raw" if str(args.diagnostics_mode) == "annotation_eval" else "normalized_fallback",
            "write_per_rollout": write_per_rollout,
            "per_rollout_response_mode": response_mode,
            "per_rollout_response_max_chars": args.per_rollout_response_max_chars,
            "replica_workers": 1,
            "effective_batch_size_per_worker": args.batch_size,
            "effective_prompt_batch_size_per_worker": prompt_batch_size,
            "append_output": append_output,
            "existing_rows_before_run": existing_rows,
        },
        "overall": _finalize_aggregate("overall", overall_aggregate),
        "outputs": {
            "per_instance_jsonl": str(per_instance_path),
            "per_rollout_jsonl_gz": str(per_rollout_path) if write_per_rollout else None,
            "task_summary_json": str(task_summary_path),
            "bucket_summary_json": str(bucket_summary_path),
        },
    }

    task_summaries = []
    for task_name, aggregate in sorted(task_aggregates.items()):
        payload = _finalize_aggregate(task_name, aggregate)
        payload["task"] = str(task_name)
        task_summaries.append(payload)

    bucket_summaries = []
    for bucket_name, aggregate in sorted(bucket_aggregates.items()):
        task_name, _, bucket_id = str(bucket_name).partition("::")
        payload = _finalize_aggregate(bucket_name, aggregate)
        payload["task"] = str(task_name)
        payload["bucket"] = str(bucket_id)
        bucket_summaries.append(payload)

    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")
    task_summary_path.write_text(json.dumps(task_summaries, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")
    bucket_summary_path.write_text(
        json.dumps(bucket_summaries, indent=2, ensure_ascii=False, default=_json_default),
        encoding="utf-8",
    )
    print(f"[done] wrote {summary_path}")
    print(f"[done] wrote {task_summary_path}")
    print(f"[done] wrote {bucket_summary_path}")
    if progress_path is not None:
        _write_json_atomic(
            progress_path,
            {
                "prompts_completed": completed_prompts,
                "prompts_total": existing_rows + total_prompts,
                "done": True,
            },
        )
    return summary


def _run_sharded_probe(args: argparse.Namespace) -> dict[str, Any]:
    from tqdm.auto import tqdm

    args.output_dir.mkdir(parents=True, exist_ok=True)
    visible_gpu_ids = _detect_visible_gpu_ids()
    requested_workers = int(args.replica_workers)
    if requested_workers <= 0:
        requested_workers = len(visible_gpu_ids)
    worker_count = max(1, min(requested_workers, len(visible_gpu_ids)))

    dataset = _build_dataset(
        args.parquet,
        args.model,
        trace_output_mode=args.trace_output_mode,
        prompt_key=args.prompt_key,
        system_prompt=_resolve_system_prompt_arg(args.system_prompt),
        max_prompt_length=args.max_prompt_length,
        max_pixels=args.max_pixels,
        filter_overlong_prompts=args.filter_overlong_prompts,
    )
    start_index = max(0, int(args.start_index))
    dataset_len = len(dataset)
    if start_index >= dataset_len:
        raise ValueError(f"start_index={start_index} is outside dataset length {dataset_len}")
    end_index = dataset_len if args.count is None else min(dataset_len, start_index + max(0, int(args.count)))
    total_prompts = max(0, end_index - start_index)
    if total_prompts <= 0:
        raise ValueError("No prompts selected for probing")

    worker_ranges = _split_prompt_ranges(start_index, end_index, worker_count)
    effective_worker_count = len(worker_ranges)
    per_worker_batch_size = max(1, math.ceil(args.batch_size / effective_worker_count))
    per_worker_prompt_batch_size = _prompt_batch_size_from_rollout_budget(
        per_worker_batch_size,
        args.rollouts_per_prompt,
    )
    resume = bool(getattr(args, "resume", False))

    worker_processes: list[tuple[subprocess.Popen[str], Path, Path, int]] = []
    existing_rows_by_worker: dict[int, int] = {}
    script_path = Path(__file__).resolve()
    for worker_rank, ((worker_start, worker_end), gpu_id) in enumerate(
        zip(worker_ranges, visible_gpu_ids[:effective_worker_count], strict=True)
    ):
        worker_dir = args.output_dir / f"worker_{worker_rank:02d}"
        if worker_dir.exists() and not resume:
            shutil.rmtree(worker_dir)
        worker_dir.mkdir(parents=True, exist_ok=True)
        progress_file = worker_dir / "_progress.json"
        log_file = worker_dir / "worker.log"
        existing_rows = _count_jsonl_rows(worker_dir / "per_instance.jsonl") if resume else 0
        shard_size = worker_end - worker_start
        existing_rows = min(existing_rows, shard_size)
        existing_rows_by_worker[worker_rank] = existing_rows
        remaining_count = shard_size - existing_rows
        if remaining_count <= 0:
            continue
        cmd = [
            sys.executable,
            str(script_path),
            "--parquet",
            str(args.parquet),
            "--output-dir",
            str(worker_dir),
            "--model",
            str(args.model),
            "--trace-output-mode",
            str(args.trace_output_mode),
            "--prompt-key",
            str(args.prompt_key),
            "--system-prompt",
            str(args.system_prompt),
            "--trace-reward-mode",
            str(args.trace_reward_mode),
            "--trace-answer-scoring",
            str(args.trace_answer_scoring),
            "--trace-format-weight",
            str(args.trace_format_weight),
            "--start-index",
            str(worker_start + existing_rows),
            "--count",
            str(remaining_count),
            "--batch-size",
            str(per_worker_batch_size),
            "--rollouts-per-prompt",
            str(args.rollouts_per_prompt),
            "--temperature",
            str(args.temperature),
            "--max-tokens",
            str(args.max_tokens),
            "--tensor-parallel-size",
            "1",
            "--gpu-memory-utilization",
            str(args.gpu_memory_utilization),
            "--max-model-len",
            str(args.max_model_len),
            "--max-num-batched-tokens",
            str(args.max_num_batched_tokens),
            "--max-num-seqs",
            str(args.max_num_seqs),
            "--max-prompt-length",
            str(args.max_prompt_length),
            "--max-pixels",
            str(args.max_pixels),
            "--prefetch-workers",
            str(args.prefetch_workers),
            "--seed",
            str(args.seed + worker_rank),
            "--diagnostics-mode",
            str(args.diagnostics_mode),
            "--per-rollout-response-mode",
            str(args.per_rollout_response_mode),
            "--per-rollout-response-max-chars",
            str(args.per_rollout_response_max_chars),
            "--progress-file",
            str(progress_file),
            "--replica-workers",
            "1",
            "--append-output",
        ]
        if args.write_per_rollout:
            cmd.append("--write-per-rollout")
        if args.filter_overlong_prompts:
            cmd.append("--filter-overlong-prompts")
        if args.enforce_eager:
            cmd.append("--enforce-eager")
        else:
            cmd.append("--no-enforce-eager")
        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
        log_mode = "a" if resume else "w"
        with log_file.open(log_mode, encoding="utf-8") as log_handle:
            process = subprocess.Popen(
                cmd,
                cwd=str(Path.cwd()),
                env=env,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                text=True,
            )
        worker_processes.append((process, progress_file, log_file, worker_rank))

    completed = sum(existing_rows_by_worker.values())
    with tqdm(total=total_prompts, desc="Curriculum probe", unit="prompt") as progress:
        if completed:
            progress.update(completed)
        while True:
            total_completed = 0
            active_workers = 0
            batch_solve_rates: list[float] = []
            for process, progress_file, _, worker_rank in worker_processes:
                if process.poll() is None:
                    active_workers += 1
                worker_completed = existing_rows_by_worker.get(worker_rank, 0)
                if progress_file.exists():
                    try:
                        payload = json.loads(progress_file.read_text(encoding="utf-8"))
                    except json.JSONDecodeError:
                        payload = {}
                    worker_completed = max(worker_completed, int(payload.get("prompts_completed", 0)))
                    if "last_batch_solve_rate" in payload:
                        batch_solve_rates.append(float(payload["last_batch_solve_rate"]))
                total_completed += worker_completed
            if total_completed > completed:
                progress.update(total_completed - completed)
                completed = total_completed
            progress.set_postfix(active_workers=active_workers, batch_solve_rate=f"{_mean(batch_solve_rates):.3f}")

            finished = [process.poll() for process, _, _, _ in worker_processes]
            if all(code is not None for code in finished):
                break
            time.sleep(1.0)

    failures = [(process.returncode, log_file) for process, _, log_file, _ in worker_processes if process.returncode != 0]
    if failures:
        failed_code, failed_log = failures[0]
        raise RuntimeError(f"One or more probe workers failed; first failure exit code={failed_code}, log={failed_log}")

    per_instance_path = args.output_dir / "per_instance.jsonl"
    per_rollout_path = args.output_dir / "per_rollout.jsonl.gz"
    task_summary_path = args.output_dir / "per_task_summary.json"
    bucket_summary_path = args.output_dir / "per_task_bucket_summary.json"
    summary_path = args.output_dir / "summary.json"

    overall_aggregate = _empty_aggregate()
    task_aggregates: dict[str, dict[str, float]] = defaultdict(_empty_aggregate)
    bucket_aggregates: dict[str, dict[str, float]] = defaultdict(_empty_aggregate)

    with per_instance_path.open("w", encoding="utf-8") as merged_handle:
        for worker_rank in range(effective_worker_count):
            worker_instance_path = args.output_dir / f"worker_{worker_rank:02d}" / "per_instance.jsonl"
            with worker_instance_path.open("r", encoding="utf-8") as worker_handle:
                for line in worker_handle:
                    row = json.loads(line)
                    merged_handle.write(line)
                    _update_aggregate(overall_aggregate, row)
                    task_key = str(row["task"])
                    bucket_key = f"{task_key}::{row['bucket_id_str'] if row['bucket_id_str'] is not None else row['difficulty_bin']}"
                    _update_aggregate(task_aggregates[task_key], row)
                    _update_aggregate(bucket_aggregates[bucket_key], row)

    write_per_rollout = _should_write_per_rollout(args)
    if write_per_rollout:
        with gzip.open(per_rollout_path, "wt", encoding="utf-8") as merged_rollout_handle:
            for worker_rank in range(effective_worker_count):
                worker_rollout_path = args.output_dir / f"worker_{worker_rank:02d}" / "per_rollout.jsonl.gz"
                if not worker_rollout_path.exists():
                    continue
                with gzip.open(worker_rollout_path, "rt", encoding="utf-8", errors="ignore") as worker_rollout_handle:
                    for line in worker_rollout_handle:
                        merged_rollout_handle.write(line)

    task_summaries = []
    for task_name, aggregate in sorted(task_aggregates.items()):
        payload = _finalize_aggregate(task_name, aggregate)
        payload["task"] = str(task_name)
        task_summaries.append(payload)

    bucket_summaries = []
    for bucket_name, aggregate in sorted(bucket_aggregates.items()):
        task_name, _, bucket_id = str(bucket_name).partition("::")
        payload = _finalize_aggregate(bucket_name, aggregate)
        payload["task"] = str(task_name)
        payload["bucket"] = str(bucket_id)
        bucket_summaries.append(payload)

    system_prompt = _resolve_system_prompt_arg(args.system_prompt)
    summary = {
        "parquet": str(Path(args.parquet).resolve()),
        "model": args.model,
        "selected_range": {
            "start_index": start_index,
            "end_index_exclusive": end_index,
            "prompt_count": total_prompts,
        },
        "settings": {
            "trace_output_mode": args.trace_output_mode,
            "prompt_key": args.prompt_key,
            "system_prompt": system_prompt,
            "trace_reward_mode": args.trace_reward_mode,
            "trace_answer_scoring": args.trace_answer_scoring,
            "probe_extraction_mode": "final_json_then_json_fallback",
            "trace_format_weight": args.trace_format_weight,
            "batch_size": args.batch_size,
            "rollouts_per_prompt": args.rollouts_per_prompt,
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "tensor_parallel_size": 1,
            "gpu_memory_utilization": args.gpu_memory_utilization,
            "max_model_len": args.max_model_len,
            "max_num_batched_tokens": args.max_num_batched_tokens,
            "max_num_seqs": args.max_num_seqs,
            "max_prompt_length": args.max_prompt_length,
            "max_pixels": args.max_pixels,
            "filter_overlong_prompts": args.filter_overlong_prompts,
            "prefetch_workers": args.prefetch_workers,
            "seed": args.seed,
            "enforce_eager": args.enforce_eager,
            "diagnostics_mode": args.diagnostics_mode,
            "primary_scoring_mode": "strict_raw" if str(args.diagnostics_mode) == "annotation_eval" else "normalized_fallback",
            "write_per_rollout": write_per_rollout,
            "per_rollout_response_mode": _effective_per_rollout_response_mode(args),
            "per_rollout_response_max_chars": args.per_rollout_response_max_chars,
            "resume": resume,
            "replica_workers": effective_worker_count,
            "effective_batch_size_per_worker": per_worker_batch_size,
            "effective_prompt_batch_size_per_worker": per_worker_prompt_batch_size,
            "effective_global_batch_size": per_worker_batch_size * effective_worker_count,
            "visible_gpu_ids": visible_gpu_ids[:effective_worker_count],
        },
        "overall": _finalize_aggregate("overall", overall_aggregate),
        "outputs": {
            "per_instance_jsonl": str(per_instance_path),
            "per_rollout_jsonl_gz": str(per_rollout_path) if write_per_rollout else None,
            "task_summary_json": str(task_summary_path),
            "bucket_summary_json": str(bucket_summary_path),
        },
    }

    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")
    task_summary_path.write_text(json.dumps(task_summaries, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")
    bucket_summary_path.write_text(
        json.dumps(bucket_summaries, indent=2, ensure_ascii=False, default=_json_default),
        encoding="utf-8",
    )
    print(f"[done] wrote {summary_path}")
    print(f"[done] wrote {task_summary_path}")
    print(f"[done] wrote {bucket_summary_path}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Probe a TRACE RLVR parquet with sampled base-model rollouts, then emit "
            "per-instance and aggregated solve statistics for curriculum construction."
        )
    )
    parser.add_argument(
        "--parquet",
        default="rlvr/dataset/train/trace_rlvr_train_128k_all_tasks_verojson.parquet",
        help="TRACE RLVR parquet to probe.",
    )
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for per-instance and summary outputs.")
    parser.add_argument("--model", default="Qwen/Qwen3-VL-8B-Instruct")
    parser.add_argument(
        "--backend",
        choices=("local_vllm", "openai_server"),
        default="local_vllm",
        help="Generation backend. openai_server calls a resident OpenAI-compatible vLLM server.",
    )
    parser.add_argument("--server-base-url", default=os.environ.get("TRACE_VLLM_BASE_URL", "http://127.0.0.1:8000/v1"))
    parser.add_argument("--server-api-key", default=os.environ.get("TRACE_VLLM_API_KEY", "EMPTY"))
    parser.add_argument("--server-model", default="", help="Served model name for OpenAI-compatible backend. Defaults to --model.")
    parser.add_argument("--server-timeout", type=float, default=600.0)
    parser.add_argument("--server-max-retries", type=int, default=3)
    parser.add_argument("--server-concurrency", type=int, default=128)
    parser.add_argument("--trace-output-mode", default="answer", choices=("answer", "answer_and_annotation", "annotation"))
    parser.add_argument("--prompt-key", default="prompt_answer")
    parser.add_argument(
        "--system-prompt",
        default=str(RLVR_ROOT / "examples/prompts/trace_vero_json_system_prompt_answer.txt"),
        help="Path to the system prompt file, or 'none' to disable.",
    )
    parser.add_argument("--trace-reward-mode", default="answer", choices=("answer", "answer_and_annotation", "auto"))
    parser.add_argument("--trace-answer-scoring", default="legacy_strict", choices=("legacy_strict", "exact_json", "strict", "legacy", "exact"))
    parser.add_argument("--trace-format-weight", type=float, default=0.0)
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--count", type=int, default=None, help="Number of prompts to probe. Default: all remaining rows.")
    parser.add_argument("--batch-size", type=int, default=6400, help="Global rollout batch budget per wave of vLLM generate() calls.")
    parser.add_argument("--rollouts-per-prompt", type=int, default=32)
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--tensor-parallel-size", type=int, default=1)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.9)
    parser.add_argument("--max-model-len", type=int, default=4096)
    parser.add_argument("--max-num-batched-tokens", type=int, default=16384)
    parser.add_argument("--max-num-seqs", type=int, default=1024)
    parser.add_argument("--max-prompt-length", type=int, default=1536)
    parser.add_argument("--max-pixels", type=int, default=4194304)
    parser.add_argument("--filter-overlong-prompts", action="store_true")
    parser.add_argument(
        "--prefetch-workers",
        type=int,
        default=1,
        help="CPU workers used to prebuild the next batch while vLLM generates the current batch. Set 0 to disable.",
    )
    parser.add_argument(
        "--replica-workers",
        type=int,
        default=0,
        help="Number of single-GPU probe workers when tensor_parallel_size=1. Default 0 means use all visible GPUs.",
    )
    parser.add_argument("--resume", action="store_true", help="Resume from existing worker shard outputs under output-dir.")
    parser.add_argument("--progress-file", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--append-output", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--seed", type=int, default=18)
    parser.add_argument(
        "--diagnostics-mode",
        choices=("none", "annotation_eval"),
        default="none",
        help=(
            "Optional diagnostic scoring/reporting mode. annotation_eval scores per-instance solve "
            "from strict raw responses and emits per-rollout format/annotation diagnostics."
        ),
    )
    parser.add_argument("--write-per-rollout", action="store_true", help="Write compressed per-rollout diagnostics JSONL.")
    parser.add_argument(
        "--per-rollout-response-mode",
        choices=("none", "full", "truncated"),
        default="none",
        help="How much raw response text to store in per-rollout diagnostics.",
    )
    parser.add_argument(
        "--per-rollout-response-max-chars",
        type=int,
        default=2000,
        help="Maximum response chars when --per-rollout-response-mode=truncated.",
    )
    parser.add_argument("--enforce-eager", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()

    if str(args.backend) == "local_vllm" and int(args.tensor_parallel_size) == 1:
        visible_gpu_count = len(_detect_visible_gpu_ids())
        requested_workers = int(args.replica_workers) if int(args.replica_workers) > 0 else visible_gpu_count
        if min(requested_workers, visible_gpu_count) > 1:
            _run_sharded_probe(args)
            return
    _run_single_probe(args)


if __name__ == "__main__":
    main()
