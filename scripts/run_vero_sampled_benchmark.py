#!/usr/bin/env python3
"""Run deterministic sampled VERO evaluations through an OpenAI-compatible endpoint.

The runner keeps VERO's own task prompts, answer extraction, and scorers, but
restricts each benchmark to a deterministic pooled sample before requests are
built. It is intended for failure-pattern analysis, not final leaderboard
reporting.
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import datetime as dt
import hashlib
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from io import BytesIO
from dataclasses import dataclass, field, replace
from pathlib import Path
from types import MethodType
from types import SimpleNamespace
from typing import Any, Iterator


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VERO_ROOT = Path("/home/jovyan/work/vero/vero-eval")
DEFAULT_RUN_ROOT = REPO_ROOT / "runs/external_benchmarks/qwen25vl7b"
DEFAULT_LOCK_PATH = REPO_ROOT / "logs/vllm/locks/qwen25vl7b_8002.lock"
DEFAULT_MODEL_ID = "Qwen/Qwen2.5-VL-7B-Instruct"
DEFAULT_ENDPOINT = "http://127.0.0.1:8002/v1"
DEFAULT_SAMPLE_SEED = 20260522


@dataclass(frozen=True)
class BenchmarkSpec:
    key: str
    display: str
    tasks: tuple[str, ...]
    judge_deferred: bool = False
    judge_tasks: tuple[str, ...] | None = None
    generation_overrides: dict[str, Any] = field(default_factory=dict)
    notes: str = ""


SHORT_QWEN3_OVERRIDES = {
    "max_new_tokens": 2048,
    "temperature": 0,
    "do_sample": False,
}


BENCHMARK_SPECS: tuple[BenchmarkSpec, ...] = (
    BenchmarkSpec("chartqapro", "ChartQA-Pro", ("chartqa_pro_qwen25_zs",)),
    BenchmarkSpec("infovqa", "InfoVQA", ("infovqa_val_qwen25_zs",)),
    BenchmarkSpec(
        "chartmuseum",
        "ChartMuseum",
        ("chartmuseum_qwen25_zs",),
        judge_deferred=True,
        notes="Uses an LLM judge in VERO; this run records generations only.",
    ),
    BenchmarkSpec("evochart", "EvoChart", ("evochart_qwen25_zs",)),
    BenchmarkSpec(
        "mmmu_pro_vision",
        "MMMU-ProVis",
        ("mmmu_pro_vision_qwen3_zs",),
        generation_overrides=SHORT_QWEN3_OVERRIDES,
        notes="No qwen25-specific VERO task exists locally; qwen3 prompt alias is capped for the 4096-token endpoint.",
    ),
    BenchmarkSpec(
        "mathvista_testmini",
        "MathVista TestMini",
        ("mathvista_testmini_qwen3_zs",),
        judge_deferred=True,
        judge_tasks=("mathvista_testmini_gpt5nano_zs",),
        generation_overrides=SHORT_QWEN3_OVERRIDES,
        notes="No qwen25-specific VERO task exists locally; qwen3 prompt alias is capped for the 4096-token endpoint. The VERO gpt5nano alias uses LLM-judge answer extraction, so final scoring is judge-deferred.",
    ),
    BenchmarkSpec(
        "mathvision",
        "MathVision",
        ("mathvision_test_qwen3_zs",),
        judge_deferred=True,
        judge_tasks=("mathvision_test_gpt5nano_zs",),
        generation_overrides=SHORT_QWEN3_OVERRIDES,
        notes="No qwen25-specific VERO task exists locally; qwen3 prompt alias is capped for the 4096-token endpoint. The VERO gpt5nano alias uses LLM-as-judge scoring, so final scoring is judge-deferred.",
    ),
    BenchmarkSpec("blink", "BLINK", ("blink_qwen25_zs",)),
    BenchmarkSpec("erqa", "ERQA", ("erqa_qwen25_zs",)),
    BenchmarkSpec("game_qa_lite", "GameQALite", ("game_qa_lite_qwen25_zs",)),
    BenchmarkSpec("embspatial", "EmbSpatial", ("embspatial_qwen25_zs",)),
    BenchmarkSpec("countqa", "CountQA", ("countqa_qwen25_zs",)),
    BenchmarkSpec("vstarbench", "VStarBench", ("vstar_bench_qwen25_zs",)),
    BenchmarkSpec("screenspotpro", "ScreenSpotPro", ("screenspotpro_point_in_box_qwen25_zs",)),
    BenchmarkSpec("aerialvg", "AerialVG", ("aerialvg_bbox_qwen25_zs",)),
    BenchmarkSpec(
        "simplevqaen",
        "SimpleVQAEn",
        ("simplevqa_en_qwen25_zs",),
        judge_deferred=True,
        generation_overrides={"max_new_tokens": 512, "temperature": 0, "do_sample": False},
        notes="Uses an LLM judge in VERO; this run records generations only.",
    ),
)

SPEC_BY_KEY = {spec.key: spec for spec in BENCHMARK_SPECS}


def json_default(value: Any) -> Any:
    try:
        import numpy as np

        if isinstance(value, np.integer):
            return int(value)
        if isinstance(value, np.floating):
            return float(value)
        if isinstance(value, np.bool_):
            return bool(value)
        if isinstance(value, np.ndarray):
            return value.tolist()
    except Exception:
        pass
    if isinstance(value, Path):
        return str(value)
    return str(value)


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=json_default), encoding="utf-8")
    tmp.replace(path)


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, default=json_default) + "\n")


@contextlib.contextmanager
def temporary_env(updates: dict[str, str]) -> Iterator[None]:
    old = {key: os.environ.get(key) for key in updates}
    os.environ.update(updates)
    try:
        yield
    finally:
        for key, value in old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


@contextlib.contextmanager
def file_lock(lock_path: Path) -> Iterator[None]:
    import fcntl

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w", encoding="utf-8") as f:
        print(f"[lock] waiting for {lock_path}")
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        print(f"[lock] acquired {lock_path}")
        try:
            yield
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            print(f"[lock] released {lock_path}")


def utc_run_id() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def stable_int(*parts: Any) -> int:
    digest = hashlib.sha256("::".join(str(part) for part in parts).encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def normalize_benchmark_keys(raw_values: list[str]) -> list[str]:
    values: list[str] = []
    for raw in raw_values:
        values.extend(part.strip() for part in raw.split(",") if part.strip())
    if not values or values == ["all"] or "all" in values:
        return [spec.key for spec in BENCHMARK_SPECS]
    unknown = [value for value in values if value not in SPEC_BY_KEY]
    if unknown:
        raise SystemExit(f"Unknown benchmark key(s): {', '.join(unknown)}")
    return values


def install_vero_import_path(vero_root: Path) -> None:
    if not vero_root.exists():
        raise SystemExit(f"VERO eval root does not exist: {vero_root}")
    sys.path.insert(0, str(vero_root))


def check_endpoint(endpoint: str, model_id: str, timeout: int = 10) -> None:
    url = endpoint.rstrip("/") + "/models"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Endpoint health check failed for {url}: {exc}") from exc
    model_ids = [item.get("id") for item in payload.get("data", []) if isinstance(item, dict)]
    if model_id not in model_ids:
        print(f"[warn] endpoint models do not list {model_id!r}; models={model_ids}")


def task_config_name(task: Any, fallback: str) -> str:
    config = getattr(task, "config", None)
    return str(getattr(config, "task", None) or fallback)


def leaf_task(obj: Any) -> Any | None:
    if isinstance(obj, tuple):
        _, task = obj
        return task
    return obj


def iter_leaf_tasks(task_dict: dict[str, Any]) -> Iterator[tuple[str, Any]]:
    for name, obj in task_dict.items():
        if isinstance(obj, dict):
            yield from iter_leaf_tasks(obj)
            continue
        task = leaf_task(obj)
        if task is None:
            continue
        yield task_config_name(task, str(name)), task


def prune_task_dict(task_dict: dict[str, Any], selected_names: set[str]) -> dict[str, Any]:
    pruned: dict[str, Any] = {}
    for name, obj in task_dict.items():
        if isinstance(obj, dict):
            child = prune_task_dict(obj, selected_names)
            if child:
                pruned[name] = child
            continue
        task = leaf_task(obj)
        if task is None:
            continue
        if task_config_name(task, str(name)) in selected_names:
            pruned[name] = obj
    return pruned


def active_split(task: Any) -> str:
    if task.has_test_docs():
        return task.config.test_split
    if task.has_validation_docs():
        return task.config.validation_split
    raise ValueError(f"Task {task} has no active test or validation split")


def safe_len_eval_docs(task: Any) -> int:
    return len(task.eval_docs_no_media if hasattr(task, "eval_docs_no_media") else task.eval_docs)


def compact_value(value: Any, max_len: int = 300) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        text = str(value)
        return text[: max_len - 3] + "..." if len(text) > max_len else value
    if isinstance(value, (list, tuple)):
        return [compact_value(item, max_len=120) for item in list(value)[:8]]
    if isinstance(value, dict):
        return {str(k): compact_value(v, max_len=120) for k, v in list(value.items())[:16]}
    return str(value)[:max_len]


def doc_preview(doc: dict[str, Any]) -> dict[str, Any]:
    id_keys = (
        "id",
        "uid",
        "qid",
        "question_id",
        "sample_id",
        "index",
        "pid",
        "image_id",
        "file_name",
        "filename",
    )
    text_keys = (
        "question",
        "query",
        "prompt",
        "instruction",
        "problem",
        "text",
        "Question",
        "input",
    )
    meta_keys = (
        "category",
        "sub_task",
        "task",
        "question_type",
        "answer_type",
        "source",
        "subject",
        "split",
        "game_name",
        "state",
    )
    out: dict[str, Any] = {}
    for key in id_keys + text_keys + meta_keys:
        if key in doc and key not in out:
            out[key] = compact_value(doc[key])
    return out


def sample_indices_by_task(
    leaf_tasks: list[tuple[str, Any]],
    max_samples: int,
    seed: int,
    benchmark_key: str,
) -> tuple[dict[str, list[int]], dict[str, Any]]:
    task_lengths = {name: safe_len_eval_docs(task) for name, task in leaf_tasks}
    total = sum(task_lengths.values())
    if max_samples <= 0 or total <= max_samples:
        selected = {name: list(range(length)) for name, length in task_lengths.items()}
    else:
        population: list[tuple[str, int]] = []
        for name in sorted(task_lengths):
            population.extend((name, index) for index in range(task_lengths[name]))
        rng = random.Random(seed + stable_int(benchmark_key, "pooled_sample"))
        sampled = rng.sample(population, max_samples)
        selected = {name: [] for name in task_lengths}
        for name, index in sampled:
            selected[name].append(index)
        selected = {name: sorted(indices) for name, indices in selected.items() if indices}
    summary = {
        "benchmark": benchmark_key,
        "sample_seed": seed,
        "max_samples": max_samples,
        "total_available": total,
        "total_selected": sum(len(indices) for indices in selected.values()),
        "task_available": task_lengths,
        "task_selected": {name: len(indices) for name, indices in selected.items()},
    }
    return selected, summary


def add_trace_columns(dataset: Any, original_indices: list[int], benchmark_key: str, task_name: str) -> Any:
    if hasattr(dataset, "select"):
        selected = dataset.select(original_indices)
        for column in ("_trace_original_index", "_trace_benchmark", "_trace_task_name"):
            if column in selected.column_names:
                selected = selected.remove_columns(column)
        selected = selected.add_column("_trace_original_index", list(original_indices))
        selected = selected.add_column("_trace_benchmark", [benchmark_key] * len(original_indices))
        selected = selected.add_column("_trace_task_name", [task_name] * len(original_indices))
        return selected
    rows = []
    for index in original_indices:
        row = dict(dataset[index])
        row["_trace_original_index"] = index
        row["_trace_benchmark"] = benchmark_key
        row["_trace_task_name"] = task_name
        rows.append(row)
    return rows


def restrict_task(task: Any, task_name: str, indices: list[int], benchmark_key: str) -> None:
    split = active_split(task)
    task.dataset[split] = add_trace_columns(task.dataset[split], indices, benchmark_key, task_name)
    if hasattr(task, "dataset_no_image") and split in task.dataset_no_image:
        task.dataset_no_image[split] = add_trace_columns(task.dataset_no_image[split], indices, benchmark_key, task_name)
    task.task_docs = task.test_docs() if task.has_test_docs() else task.validation_docs()
    task.features = list(task.task_docs.features.keys()) if hasattr(task.task_docs, "features") else list(task.task_docs[0].keys())
    task._instances = []


def build_sample_manifest(
    benchmark_key: str,
    selected: dict[str, list[int]],
    leaf_tasks: list[tuple[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    task_by_name = dict(leaf_tasks)
    for task_name in sorted(selected):
        task = task_by_name[task_name]
        docs = task.eval_docs_no_media if hasattr(task, "eval_docs_no_media") else task.eval_docs
        for sample_doc_id, original_index in enumerate(selected[task_name]):
            row_doc = docs[original_index]
            preview = doc_preview(dict(row_doc))
            try:
                target = task.doc_to_target(row_doc)
            except Exception:
                target = None
            rows.append(
                {
                    "benchmark": benchmark_key,
                    "task_name": task_name,
                    "sample_doc_id": sample_doc_id,
                    "original_index": original_index,
                    "target_preview": compact_value(target, max_len=240),
                    "doc_preview": preview,
                }
            )
    return rows


def ensure_response_cache_parent(cache_dir: Path, model_id: str) -> None:
    response_file = cache_dir / f"{model_id}_response.json"
    response_file.parent.mkdir(parents=True, exist_ok=True)


def patch_image_encoder(lm: Any, max_pixels: int, max_side: int) -> None:
    from PIL import Image
    from tqdm import tqdm

    def encode_image(self: Any, image: Any) -> str:
        max_bytes = int(float(self.max_size_in_mb) * 1024 * 1024)
        if isinstance(image, str):
            img = Image.open(image).convert("RGB")
        else:
            img = image.copy().convert("RGB")

        width, height = img.size
        scales = [1.0]
        if max_pixels and max_pixels > 0 and width * height > max_pixels:
            scales.append((max_pixels / float(width * height)) ** 0.5)
        if max_side and max_side > 0 and max(width, height) > max_side:
            scales.append(max_side / float(max(width, height)))
        scale = min(scales)
        if scale < 1.0:
            new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        output_buffer = BytesIO()
        img.save(output_buffer, format="JPEG", quality=85, optimize=False)
        byte_data = output_buffer.getvalue()
        while len(byte_data) > max_bytes and img.size[0] > 100 and img.size[1] > 100:
            new_size = (int(img.size[0] * 0.75), int(img.size[1] * 0.75))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            output_buffer = BytesIO()
            img.save(output_buffer, format="JPEG", quality=85, optimize=False)
            byte_data = output_buffer.getvalue()
        return base64.b64encode(byte_data).decode("utf-8")

    def prepare_payload(self: Any, contexts: str, gen_kwargs: dict[str, Any], doc_to_visual: Any, doc_id: int, task: str, split: str) -> tuple[dict[str, Any] | None, str | None]:
        if self.continual_mode is True and self.cache_mode == "resume":
            doc_uuid = f"{task}___{split}___{doc_id}"
            if doc_uuid in self.response_cache:
                response_text = self.response_cache[doc_uuid]
                if response_text:
                    return None, response_text

        visuals = [doc_to_visual(self.task_dict[task][split][doc_id])]
        imgs: list[str] = []
        if None not in visuals:
            for visual in self.flatten(visuals):
                if isinstance(visual, str) and any(ext in visual for ext in (".mp4", ".avi", ".mov", ".flv", ".wmv")):
                    imgs.extend(self.encode_video(visual, self.max_frames_num))
                elif isinstance(visual, str) and any(ext in visual.lower() for ext in (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp")):
                    imgs.append(self.encode_image(visual))
                elif isinstance(visual, Image.Image):
                    imgs.append(self.encode_image(visual))

        payload: dict[str, Any] = {"messages": [{"role": "user", "content": [{"type": "text", "text": contexts}]}]}
        payload["model"] = self.model_version
        for img in imgs:
            payload["messages"][0]["content"].append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img}"}})

        if "max_new_tokens" not in gen_kwargs:
            gen_kwargs["max_new_tokens"] = 1024
        if "temperature" not in gen_kwargs:
            gen_kwargs["temperature"] = 0
        payload["max_tokens"] = gen_kwargs["max_new_tokens"]
        payload["temperature"] = gen_kwargs["temperature"]
        return payload, None

    def generate_until_streaming(self: Any, requests: list[Any]) -> list[str]:
        max_workers = int(os.environ.get("API_MAX_WORKERS", "8"))
        max_workers = max(1, max_workers)
        res: list[str | None] = [None] * len(requests)
        pbar = tqdm(total=len(requests), disable=(self.rank != 0), desc="Model Responding")

        def persist_response(task: str, split: str, doc_id: int, response_text: str) -> None:
            if self.continual_mode is True:
                doc_uuid = f"{task}___{split}___{doc_id}"
                self.response_cache[doc_uuid] = response_text
                with open(self.response_persistent_file, "w", encoding="utf-8") as f:
                    json.dump(self.response_cache, f)

        iterator = iter(enumerate(requests))
        inflight: dict[Any, tuple[int, str, str, int]] = {}

        def submit_next(executor: ThreadPoolExecutor) -> bool:
            for idx, reg in iterator:
                contexts, gen_kwargs, doc_to_visual, doc_id, task, split = reg.args
                payload, cached_text = self._prepare_payload(contexts, gen_kwargs, doc_to_visual, doc_id, task, split)
                if payload is None:
                    res[idx] = cached_text or ""
                    pbar.update(1)
                    continue
                future = executor.submit(self._call_api, payload)
                inflight[future] = (idx, task, split, doc_id)
                return True
            return False

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for _ in range(max_workers):
                if not submit_next(executor):
                    break
            while inflight:
                done, _ = wait(inflight.keys(), return_when=FIRST_COMPLETED)
                for future in done:
                    idx, task, split, doc_id = inflight.pop(future)
                    response_text = future.result()
                    res[idx] = response_text
                    persist_response(task, split, doc_id, response_text)
                    pbar.update(1)
                    submit_next(executor)
        pbar.close()
        return [text or "" for text in res]

    lm.encode_image = MethodType(encode_image, lm)
    lm._prepare_payload = MethodType(prepare_payload, lm)
    lm.generate_until = MethodType(generate_until_streaming, lm)


def create_model(
    model_id: str,
    timeout: int,
    max_retries: int,
    response_cache: Path,
    max_image_size_mb: float,
    max_image_pixels: int,
    max_image_side: int,
) -> tuple[Any, str]:
    import lmms_eval.models

    ensure_response_cache_parent(response_cache, model_id)
    model_args = ",".join(
        [
            f"model={model_id}",
            f"model_version={model_id}",
            f"timeout={timeout}",
            f"max_retries={max_retries}",
            f"max_size_in_mb={max_image_size_mb}",
            "continual_mode=True",
            f"response_persistent_folder={response_cache}",
            "httpx_trust_env=False",
        ]
    )
    model_cls = lmms_eval.models.get_model("openai_compatible", force_simple=True)
    lm = model_cls.create_from_arg_string(
        model_args,
        {
            "batch_size": None,
            "max_batch_size": None,
            "device": None,
        },
    )
    patch_image_encoder(lm, max_pixels=max_image_pixels, max_side=max_image_side)
    return lm, model_args


def prepare_tasks_for_eval(
    task_dict: dict[str, Any],
    spec: BenchmarkSpec,
    fewshot_seed: int,
    lm: Any,
    *,
    enable_judge_metrics: bool = False,
) -> None:
    for task_name, task in iter_leaf_tasks(task_dict):
        lm.task_dict[task_name] = task.dataset
        output_type = str(task.get_config("output_type") or getattr(task, "OUTPUT_TYPE", ""))
        if "generate_until" in output_type and spec.generation_overrides:
            current_kwargs = dict(task.get_config("generation_kwargs") or {})
            current_kwargs.update(spec.generation_overrides)
            task.set_config("generation_kwargs", current_kwargs)
        if spec.judge_deferred and not enable_judge_metrics:
            task.override_metric("bypass")
        if task.get_config("num_fewshot") is None:
            task.set_config("num_fewshot", 0)
        task.set_fewshot_seed(seed=fewshot_seed)


def save_evaluation_outputs(
    out_dir: Path,
    results: dict[str, Any],
    model_args: str,
    datetime_str: str,
) -> None:
    from lmms_eval.loggers.evaluation_tracker import EvaluationTracker

    samples = results.pop("samples", None)
    results["config"] = {
        "model": "openai_compatible",
        "model_args": model_args,
        "force_simple": True,
        "limit": None,
        "bootstrap_iters": 0,
    }
    results["date"] = datetime_str

    tracker = EvaluationTracker(output_path=str(out_dir))
    tracker.general_config_tracker.log_experiment_args(
        model_source="openai_compatible",
        model_args=model_args,
        system_instruction=None,
        chat_template=None,
        fewshot_as_multiturn=False,
    )
    tracker.save_results_aggregated(results=results, samples=samples, datetime_str=datetime_str)
    if samples:
        for task_name in sorted(samples):
            tracker.save_results_samples(task_name=task_name, samples=samples[task_name])


def response_stats(results: dict[str, Any]) -> dict[str, int]:
    total = 0
    empty = 0
    for rows in (results.get("samples") or {}).values():
        for row in rows:
            total += 1
            text = ""
            stack = [row.get("filtered_resps")]
            while stack:
                value = stack.pop()
                if isinstance(value, str):
                    text = value
                    break
                if isinstance(value, (list, tuple)):
                    stack.extend(reversed(value))
            if not text.strip():
                empty += 1
    return {"responses_total": total, "responses_empty": empty}


def load_vero_task_dict(spec: BenchmarkSpec, verbosity: str) -> dict[str, Any]:
    from lmms_eval.tasks import TaskManager, get_task_dict

    task_manager = TaskManager(verbosity, model_name="openai_compatible")
    matched = task_manager.match_tasks(list(spec.tasks))
    missing = [task for task in spec.tasks if task not in matched]
    if missing:
        raise ValueError(f"VERO task alias(es) not found for {spec.key}: {missing}")
    return get_task_dict(matched, task_manager, task_type="simple")


def run_one_benchmark(args: argparse.Namespace, spec: BenchmarkSpec, run_dir: Path) -> dict[str, Any]:
    from lmms_eval import evaluator

    eval_spec = spec
    if args.enable_judge_metrics and spec.judge_tasks:
        eval_spec = replace(spec, tasks=spec.judge_tasks)

    out_dir = run_dir / spec.key
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[benchmark] {spec.display} -> {out_dir}")
    if args.enable_judge_metrics and spec.judge_deferred:
        print(f"[judge] enabled real judge metrics for {spec.key}")

    task_dict = load_vero_task_dict(eval_spec, args.verbosity)
    leaf_tasks = list(iter_leaf_tasks(task_dict))
    selected, sample_summary = sample_indices_by_task(leaf_tasks, args.max_samples, args.sample_seed, spec.key)
    selected_names = set(selected)
    manifest_rows = build_sample_manifest(spec.key, selected, leaf_tasks)
    append_jsonl(out_dir / "sample_manifest.jsonl", manifest_rows)
    write_json(out_dir / "sample_summary.json", sample_summary)

    for task_name, task in leaf_tasks:
        if task_name in selected:
            restrict_task(task, task_name, selected[task_name], spec.key)
    task_dict = prune_task_dict(task_dict, selected_names)
    if not task_dict:
        raise RuntimeError(f"No sampled tasks remain for {spec.key}")

    run_summary: dict[str, Any] = {
        "benchmark": spec.key,
        "display": spec.display,
        "tasks": eval_spec.tasks,
        "generation_tasks": spec.tasks,
        "judge_tasks": spec.judge_tasks,
        "judge_deferred": spec.judge_deferred,
        "judge_metrics_enabled": bool(args.enable_judge_metrics and spec.judge_deferred),
        "generation_overrides": spec.generation_overrides,
        "notes": spec.notes,
        "sample_summary": sample_summary,
        "output_dir": str(out_dir),
        "manifest_only": args.manifest_only,
    }

    if args.manifest_only:
        write_json(out_dir / "run_summary.json", run_summary)
        print(f"[manifest] selected {sample_summary['total_selected']} / {sample_summary['total_available']}")
        return run_summary

    if not args.skip_endpoint_check:
        check_endpoint(args.endpoint, args.model_id, timeout=args.endpoint_timeout)
    env = {
        "OPENAI_API_BASE": args.endpoint,
        "OPENAI_API_KEY": args.api_key,
        "API_MAX_WORKERS": str(args.api_max_workers),
    }
    response_cache = out_dir / "response_cache"
    datetime_str = utc_run_id()
    lock_context = contextlib.nullcontext() if args.no_lock else file_lock(args.lock_path)
    with lock_context:
        with temporary_env(env):
            lm, model_args = create_model(
                args.model_id,
                args.timeout,
                args.max_retries,
                response_cache,
                args.max_image_size_mb,
                args.max_image_pixels,
                args.max_image_side,
            )
            prepare_tasks_for_eval(
                task_dict,
                spec,
                args.sample_seed,
                lm,
                enable_judge_metrics=args.enable_judge_metrics,
            )
            cli_args = SimpleNamespace(process_with_media=True, image_viz_path=str(out_dir))
            start = time.perf_counter()
            results = evaluator.evaluate(
                lm=lm,
                task_dict=task_dict,
                limit=None,
                cache_requests=False,
                rewrite_requests_cache=False,
                bootstrap_iters=args.bootstrap_iters,
                write_out=False,
                log_samples=True,
                system_instruction=None,
                apply_chat_template=False,
                fewshot_as_multiturn=False,
                verbosity=args.verbosity,
                distributed_executor_backend="accelerate",
                cli_args=cli_args,
            )
            elapsed = time.perf_counter() - start
            if results is None:
                raise RuntimeError(f"VERO evaluation returned no results for {spec.key}")
            stats = response_stats(results)
            if stats["responses_empty"]:
                print(f"[warn] {stats['responses_empty']} / {stats['responses_total']} responses were empty")
            save_evaluation_outputs(out_dir, results, model_args, datetime_str)
    run_summary.update(
        {
            "manifest_only": False,
            "datetime": datetime_str,
            "elapsed_seconds": elapsed,
            "endpoint": args.endpoint,
            "model_id": args.model_id,
            "api_max_workers": args.api_max_workers,
            "response_stats": stats,
        }
    )
    write_json(out_dir / "run_summary.json", run_summary)
    print(f"[done] {spec.display}: {sample_summary['total_selected']} samples in {elapsed:.1f}s")
    return run_summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmarks", nargs="*", default=["all"], help="Benchmark keys, comma-separated keys, or all.")
    parser.add_argument("--list-benchmarks", action="store_true")
    parser.add_argument("--vero-root", type=Path, default=DEFAULT_VERO_ROOT)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--max-samples", type=int, default=1000)
    parser.add_argument("--sample-seed", type=int, default=DEFAULT_SAMPLE_SEED)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--endpoint-timeout", type=int, default=10)
    parser.add_argument("--skip-endpoint-check", action="store_true")
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--api-key", default="EMPTY")
    parser.add_argument("--api-max-workers", type=int, default=8)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--max-retries", type=int, default=5)
    parser.add_argument("--max-image-size-mb", type=float, default=1.0)
    parser.add_argument("--max-image-pixels", type=int, default=1_000_000)
    parser.add_argument("--max-image-side", type=int, default=1280)
    parser.add_argument("--lock-path", type=Path, default=DEFAULT_LOCK_PATH)
    parser.add_argument("--no-lock", action="store_true")
    parser.add_argument("--manifest-only", action="store_true")
    parser.add_argument(
        "--enable-judge-metrics",
        action="store_true",
        help="Do not bypass VERO judge metrics for judge-deferred tasks. Intended for reruns that reuse cached model responses.",
    )
    parser.add_argument("--bootstrap-iters", type=int, default=0)
    parser.add_argument("--verbosity", default="WARNING")
    parser.add_argument("--stop-on-error", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.list_benchmarks:
        for spec in BENCHMARK_SPECS:
            suffix = " judge_deferred" if spec.judge_deferred else ""
            judge_suffix = f"\tjudge_tasks={','.join(spec.judge_tasks)}" if spec.judge_tasks else ""
            print(f"{spec.key}\t{spec.display}\t{','.join(spec.tasks)}{suffix}{judge_suffix}")
        return

    run_id = args.run_id or utc_run_id()
    run_dir = args.run_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    install_vero_import_path(args.vero_root)

    keys = normalize_benchmark_keys(args.benchmarks)
    summaries: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for key in keys:
        spec = SPEC_BY_KEY[key]
        try:
            summaries.append(run_one_benchmark(args, spec, run_dir))
        except Exception as exc:
            failure = {"benchmark": key, "error": repr(exc)}
            failures.append(failure)
            print(f"[error] {key}: {exc}", file=sys.stderr)
            if args.stop_on_error:
                raise
    manifest_path = run_dir / "RUN_MANIFEST.json"
    existing_manifest = read_json(manifest_path, {})
    benchmark_by_key = {
        row.get("benchmark"): row
        for row in existing_manifest.get("benchmarks", [])
        if isinstance(row, dict) and row.get("benchmark")
    }
    failure_by_key = {
        row.get("benchmark"): row
        for row in existing_manifest.get("failures", [])
        if isinstance(row, dict) and row.get("benchmark")
    }
    for summary in summaries:
        benchmark_by_key[summary["benchmark"]] = summary
        failure_by_key.pop(summary["benchmark"], None)
    for failure in failures:
        failure_by_key[failure["benchmark"]] = failure
    write_json(
        manifest_path,
        {
            "run_id": run_id,
            "run_dir": str(run_dir),
            "sample_seed": args.sample_seed,
            "max_samples": args.max_samples,
            "model_id": args.model_id,
            "endpoint": args.endpoint,
            "judge_metrics_enabled": args.enable_judge_metrics,
            "benchmarks": list(benchmark_by_key.values()),
            "failures": list(failure_by_key.values()),
        },
    )
    if failures:
        raise SystemExit(f"{len(failures)} benchmark(s) failed; see {run_dir / 'RUN_MANIFEST.json'}")
    print(f"[complete] run_id={run_id} root={run_dir}")


if __name__ == "__main__":
    main()
