#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import concurrent.futures
import hashlib
import json
import math
import os
import re
import shutil
import sys
import threading
import time
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

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


def _judge_cache_entry_needs_retry(
    row: dict[str, Any],
    *,
    retry_on_length: bool = True,
) -> bool:
    output = str(row.get("judge_output", "")).strip()
    finish_reason = str(row.get("judge_finish_reason", "")).strip().lower()
    return not output or (retry_on_length and finish_reason in {"length", "max_tokens"})


def _judge_retry_token_limits(initial_max_tokens: int) -> list[int]:
    limit = max(128, int(initial_max_tokens))
    ceiling = max(1024, limit)
    limits = [limit]
    while limits[-1] < ceiling:
        limits.append(min(ceiling, limits[-1] * 2))
    return limits


PERSISTENT_JUDGE_CACHE_CONTRACT_VERSION = "trace-persistent-judge-v2"
DIRECT_JUDGE_CACHE_CONTRACTS = {
    "physics_equivalence": "trace-final25-physics-vlmevalkit-equivalence-v1",
    "mathvision_extract": "trace-final25-mathvision-extract-v2",
    "mathvista_extract": "trace-final25-mathvista-extract-v2",
    "mathverse_extract": "trace-final25-mathverse-extract-v2",
    "mathverse_score": "trace-final25-mathverse-vlmevalkit-judgement01-v4",
    "logicvista_extract": "trace-final25-logicvista-option-extract-v1",
    "charxiv_judge": "trace-final25-charxiv-judge-v1",
    "evochart_judge": "trace-final25-evochart-judge-v1",
    "chartmuseum_judge": "trace-final25-chartmuseum-vlmevalkit-v1",
}


def _nonempty_judge_output(value: Any) -> bool:
    return bool(str(value or "").strip())


def _binary_judge_output(value: Any) -> bool:
    return _strict_parse_binary_score(value) is not None


class _JudgeAPIRequestError(RuntimeError):
    def __init__(self, detail: str, *, affects_health: bool = True):
        super().__init__(detail)
        self.affects_health = bool(affects_health)


class _JudgeEndpointHealth:
    """Track endpoint failures and coordinate one recovery probe after cooldown."""

    def __init__(
        self,
        endpoints: list[str],
        failure_threshold: int,
        *,
        cooldown_seconds: float = 30.0,
        clock: Callable[[], float] | None = None,
    ):
        self.endpoints = list(endpoints)
        self.failure_threshold = max(1, int(failure_threshold))
        self.cooldown_seconds = max(0.0, float(cooldown_seconds))
        self._clock = clock or time.monotonic
        self._failures = {endpoint: 0 for endpoint in endpoints}
        self._quarantined_until: dict[str, float] = {}
        self._half_open: set[str] = set()
        self._lock = threading.Lock()

    def acquire(self, start: int, attempted: set[str]) -> str | None:
        """Return a healthy endpoint or reserve one expired endpoint as a probe."""

        with self._lock:
            ordered = self.endpoints[start:] + self.endpoints[:start]
            now = self._clock()
            for endpoint in ordered:
                if endpoint in attempted or endpoint in self._half_open:
                    continue
                quarantined_until = self._quarantined_until.get(endpoint)
                if quarantined_until is None:
                    return endpoint
                if quarantined_until is not None and quarantined_until <= now:
                    self._half_open.add(endpoint)
                    return endpoint
            return None

    def next_retry_delay(self, attempted: set[str]) -> float | None:
        """Return seconds until an endpoint can be acquired, if any remain."""

        with self._lock:
            if any(
                endpoint not in attempted
                and endpoint not in self._quarantined_until
                and endpoint not in self._half_open
                for endpoint in self.endpoints
            ):
                return 0.0
            waits = [
                max(0.0, ready_at - self._clock())
                for endpoint, ready_at in self._quarantined_until.items()
                if endpoint not in attempted and endpoint not in self._half_open
            ]
            if waits:
                return min(waits)
            if self._half_open:
                # Another worker owns the recovery probe. Poll without spinning.
                return 0.05
            return None

    def record_success(self, endpoint: str) -> None:
        with self._lock:
            self._failures[endpoint] = 0
            self._quarantined_until.pop(endpoint, None)
            self._half_open.discard(endpoint)

    def record_failure(self, endpoint: str) -> bool:
        with self._lock:
            self._half_open.discard(endpoint)
            self._failures[endpoint] += 1
            if self._failures[endpoint] >= self.failure_threshold:
                self._quarantined_until[endpoint] = self._clock() + self.cooldown_seconds
                return True
            return False

    def record_neutral_failure(self, endpoint: str) -> None:
        """Release a half-open probe after a request error that does not affect health."""

        with self._lock:
            if endpoint in self._half_open:
                self._half_open.discard(endpoint)
                self._quarantined_until[endpoint] = self._clock() + self.cooldown_seconds

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "failure_threshold": self.failure_threshold,
                "cooldown_seconds": self.cooldown_seconds,
                "consecutive_failures": dict(self._failures),
                # Keep the historical key for log and test compatibility.
                "disabled_endpoints": sorted(self._quarantined_until),
                "half_open_endpoints": sorted(self._half_open),
            }


def _make_judge_api_batches(
    pending: list[tuple[str, str]],
    rendered: dict[str, str],
    *,
    batch_size: int,
    max_batch_chars: int,
) -> list[list[tuple[str, str]]]:
    batches: list[list[tuple[str, str]]] = []
    current: list[tuple[str, str]] = []
    current_chars = 0
    for item in pending:
        prompt_chars = len(rendered[str(item[0])])
        if current and (len(current) >= batch_size or current_chars + prompt_chars > max_batch_chars):
            batches.append(current)
            current = []
            current_chars = 0
        current.append(item)
        current_chars += prompt_chars
        if prompt_chars >= max_batch_chars:
            batches.append(current)
            current = []
            current_chars = 0
    if current:
        batches.append(current)
    return batches


class PersistentJudge:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.llm = None
        self.tokenizer = None
        self.api_tokenizer = None
        self._api_thread_local = threading.local()
        self._api_sessions: list[requests.Session] = []
        self._api_sessions_lock = threading.Lock()
        self._endpoint_health: _JudgeEndpointHealth | None = None

    @property
    def api_bases(self) -> list[str]:
        return [str(item).rstrip("/") for item in (getattr(self.args, "judge_api_bases", None) or []) if str(item).strip()]

    def _using_api_pool(self) -> bool:
        return bool(self.api_bases)

    def _arg(self, name: str, default: Any) -> Any:
        return getattr(self.args, name, default)

    def _api_session(self) -> requests.Session:
        session = getattr(self._api_thread_local, "session", None)
        if session is None:
            session = requests.Session()
            self._api_thread_local.session = session
            with self._api_sessions_lock:
                self._api_sessions.append(session)
        return session

    def _get_endpoint_health(self) -> _JudgeEndpointHealth:
        endpoints = self.api_bases
        if self._endpoint_health is None or self._endpoint_health.endpoints != endpoints:
            self._endpoint_health = _JudgeEndpointHealth(
                endpoints,
                int(self._arg("judge_api_endpoint_failure_threshold", 3)),
                cooldown_seconds=float(self._arg("judge_api_endpoint_cooldown_seconds", 30.0)),
            )
        return self._endpoint_health

    def _request_metadata(
        self,
        prompt: str,
        *,
        max_tokens: int,
        temperature: float,
        top_p: float,
        contract_version: str,
        backend: str,
        system_prompt: str | None = None,
    ) -> dict[str, str]:
        prompt_identity = prompt
        if system_prompt is not None:
            prompt_identity = json.dumps(
                {"system": system_prompt, "user": prompt},
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )
        prompt_hash = hashlib.sha256(prompt_identity.encode("utf-8")).hexdigest()
        request_contract = {
            "contract_version": contract_version,
            "prompt_sha256": prompt_hash,
            "backend": backend,
            "judge_model": str(self._arg("judge_model", "Qwen/Qwen3-32B")),
            "judge_api_model": str(self._arg("judge_api_model", "qwen3-32b-judge")) if backend == "api" else None,
            "judge_api_tokenizer_model": (
                str(self._arg("judge_api_tokenizer_model", "Qwen/Qwen3-32B")) if backend == "api" else None
            ),
            "max_tokens": int(max_tokens),
            "temperature": float(temperature),
            "top_p": float(top_p),
            "chat_template": "user/add_generation_prompt/enable_thinking_false_when_supported",
            "system_prompt_sha256": (
                hashlib.sha256(system_prompt.encode("utf-8")).hexdigest() if system_prompt is not None else None
            ),
        }
        encoded = json.dumps(request_contract, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return {
            "request_hash": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
            "contract_version": contract_version,
            "judge_prompt_hash": prompt_hash,
        }

    @staticmethod
    def _cache_entry_needs_retry(
        row: dict[str, Any],
        expected: dict[str, str],
        output_validator: Callable[[str], bool] | None,
        output_validator_by_index: Callable[[str, str], bool] | None = None,
        *,
        retry_on_length: bool = True,
    ) -> bool:
        if any(str(row.get(key, "")) != str(value) for key, value in expected.items()):
            return True
        if _judge_cache_entry_needs_retry(row, retry_on_length=retry_on_length):
            return True
        if output_validator_by_index is not None:
            try:
                return not bool(
                    output_validator_by_index(
                        str(row.get("index", "")),
                        str(row.get("judge_output", "")),
                    )
                )
            except Exception:
                return True
        if output_validator is not None:
            try:
                return not bool(output_validator(str(row.get("judge_output", ""))))
            except Exception:
                return True
        return False

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

    def chat_prompt(self, prompt: str, *, system_prompt: str | None = None) -> str:
        self._ensure_loaded()
        assert self.tokenizer is not None
        messages = []
        if system_prompt is not None:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
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

        tokenizer_model = self._arg("judge_api_tokenizer_model", None) or self._arg("judge_model", "Qwen/Qwen3-32B")
        self.api_tokenizer = AutoTokenizer.from_pretrained(tokenizer_model, trust_remote_code=True)

    def api_chat_prompt(self, prompt: str, *, system_prompt: str | None = None) -> str:
        self._ensure_api_tokenizer()
        assert self.api_tokenizer is not None
        messages = []
        if system_prompt is not None:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
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

    def _call_api_completion_batch_once(
        self,
        endpoint: str,
        prompts: list[str],
        *,
        max_tokens: int | None,
        temperature: float,
        top_p: float,
    ) -> list[dict[str, Any]]:
        if not prompts:
            return []
        payload = {
            "model": self._arg("judge_api_model", "qwen3-32b-judge"),
            # Preserve the historical scalar request shape when batching is disabled.
            "prompt": prompts[0] if len(prompts) == 1 else prompts,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens if max_tokens is not None else self._arg("judge_max_tokens", 256),
        }
        timeout = float(self._arg("judge_api_timeout", 120.0))
        try:
            response = self._api_session().post(self._completion_url(endpoint), json=payload, timeout=timeout)
            if response.status_code >= 400:
                affects_health = response.status_code >= 500
                raise _JudgeAPIRequestError(
                    f"{endpoint} returned HTTP {response.status_code}: {response.text[:500]}",
                    affects_health=affects_health,
                )
            data = response.json()
        except _JudgeAPIRequestError:
            raise
        except Exception as exc:
            raise _JudgeAPIRequestError(f"{endpoint} request failed: {exc}") from exc

        choices = data.get("choices")
        if not isinstance(choices, list) or len(choices) != len(prompts):
            raise _JudgeAPIRequestError(
                f"{endpoint} returned {len(choices) if isinstance(choices, list) else 'invalid'} choices "
                f"for {len(prompts)} prompts"
            )
        mapped: list[dict[str, Any] | None] = [None] * len(prompts)
        usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
        for choice in choices:
            if not isinstance(choice, dict):
                raise _JudgeAPIRequestError(f"{endpoint} returned a non-object completion choice")
            choice_index = choice.get("index")
            if isinstance(choice_index, bool) or not isinstance(choice_index, int):
                raise _JudgeAPIRequestError(f"{endpoint} returned a choice without an integer index")
            if not 0 <= choice_index < len(prompts) or mapped[choice_index] is not None:
                raise _JudgeAPIRequestError(
                    f"{endpoint} returned duplicate or out-of-range choice index {choice_index}"
                )
            choice_usage = choice.get("usage") if isinstance(choice.get("usage"), dict) else {}
            token_count = choice_usage.get("completion_tokens", choice.get("completion_tokens"))
            if token_count is None and len(prompts) == 1:
                token_count = usage.get("completion_tokens")
            mapped[choice_index] = {
                "judge_output": str(choice.get("text", "")).strip(),
                "judge_finish_reason": choice.get("finish_reason"),
                "judge_output_token_count": token_count,
                "judge_api_batch_usage": usage,
                "judge_api_batch_prompt_count": len(prompts),
                "judge_api_response_id": data.get("id"),
                "judge_choice_index": choice_index,
                "judge_api_endpoint": endpoint,
            }
        if any(item is None for item in mapped):
            raise _JudgeAPIRequestError(f"{endpoint} response did not cover every prompt index")
        return [item for item in mapped if item is not None]

    def _call_api_completion_batch(
        self,
        health: _JudgeEndpointHealth,
        start_endpoint: int,
        prompts: list[str],
        *,
        max_tokens: int,
        temperature: float,
        top_p: float,
    ) -> list[dict[str, Any]]:
        endpoints = self.api_bases
        max_attempts = max(len(endpoints), int(self._arg("judge_api_max_retries", 5)))
        attempted: set[str] = set()
        last_error: Exception | None = None
        attempt = 0
        while attempt < max_attempts:
            endpoint = health.acquire(start_endpoint % len(endpoints), attempted)
            if endpoint is None and attempted:
                attempted.clear()
                endpoint = health.acquire(start_endpoint % len(endpoints), attempted)
            if endpoint is None:
                delay = health.next_retry_delay(attempted)
                if delay is None:
                    break
                if delay > 0:
                    time.sleep(delay)
                continue
            attempted.add(endpoint)
            attempt += 1
            try:
                rows = self._call_api_completion_batch_once(
                    endpoint,
                    prompts,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                )
                health.record_success(endpoint)
                return rows
            except _JudgeAPIRequestError as exc:
                last_error = exc
                if exc.affects_health:
                    disabled = health.record_failure(endpoint)
                    if disabled:
                        print(f"[judge:api-quarantine] endpoint={endpoint} error={exc}", file=sys.stderr)
                else:
                    health.record_neutral_failure(endpoint)
                if attempt < max_attempts:
                    delay = float(self._arg("judge_api_retry_base_delay", 0.5))
                    if delay > 0 and health.next_retry_delay(attempted) not in {None, 0.0}:
                        time.sleep(min(8.0, delay * (2 ** (attempt - 1))))
        raise RuntimeError(
            f"judge API batch failed after {max_attempts} attempts; "
            f"health={health.snapshot()} last_error={last_error}"
        )

    def _call_api_completion(
        self,
        endpoint: str,
        prompt: str,
        *,
        max_tokens: int | None,
        temperature: float,
        top_p: float,
    ) -> dict[str, Any]:
        """Compatibility wrapper retained for callers that issue one completion."""

        return self._call_api_completion_batch_once(
            endpoint,
            [prompt],
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
        )[0]

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
        output_validator: Callable[[str], bool] | None,
        output_validator_by_index: Callable[[str, str], bool] | None,
        contract_version: str,
        system_prompt: str | None,
        retry_on_length: bool,
        return_unresolved: bool,
    ) -> dict[str, dict[str, Any]]:
        runner, _ = _import_vlmeval_runner()

        output_dir.mkdir(parents=True, exist_ok=True)
        cache_path = output_dir / cache_name
        if no_resume and cache_path.exists():
            cache_path.unlink()
        existing = {} if no_resume else runner.load_jsonl_by_index(cache_path)
        if len({str(idx) for idx, _ in prompts}) != len(prompts):
            raise ValueError(f"Duplicate judge prompt indices are not supported: {cache_path}")
        effective_max_tokens = max(
            128,
            int(max_tokens if max_tokens is not None else self._arg("judge_max_tokens", 256)),
        )
        expected = {
            str(idx): self._request_metadata(
                prompt,
                max_tokens=effective_max_tokens,
                temperature=temperature,
                top_p=top_p,
                contract_version=contract_version,
                backend="api",
                system_prompt=system_prompt,
            )
            for idx, prompt in prompts
        }
        retry_ids = {
            str(idx)
            for idx, _ in prompts
            if str(idx) in existing
            and (
                any(
                    str(existing[str(idx)].get(key, "")) != str(value)
                    for key, value in expected[str(idx)].items()
                )
                or (
                    not return_unresolved
                    and self._cache_entry_needs_retry(
                        existing[str(idx)],
                        expected[str(idx)],
                        output_validator,
                        output_validator_by_index,
                        retry_on_length=retry_on_length,
                    )
                )
            )
        }
        pending = [
            (idx, prompt)
            for idx, prompt in prompts
            if str(idx) not in existing or str(idx) in retry_ids
        ]
        endpoints = self.api_bases
        batch_size = max(1, int(self._arg("judge_api_batch_size", 1)))
        max_batch_chars = max(1, int(self._arg("judge_api_max_batch_chars", 100_000)))
        batches_per_endpoint = max(1, int(self._arg("judge_api_batches_per_endpoint", 1)))
        print(
            "[judge:api-cached] "
            f"cache={cache_path} rows={len(prompts)} existing={len(existing)} pending={len(pending)} "
            f"retry_incomplete={len(retry_ids)} max_tokens={effective_max_tokens} "
            f"endpoints={len(endpoints)} batch_size={batch_size} max_batch_chars={max_batch_chars}"
        )
        if pending:
            rendered = {
                str(idx): self.api_chat_prompt(prompt, system_prompt=system_prompt)
                for idx, prompt in pending
            }
            batches = _make_judge_api_batches(
                pending,
                rendered,
                batch_size=batch_size,
                max_batch_chars=max_batch_chars,
            )
            health = self._get_endpoint_health()

            def run_batch(pos_batch: tuple[int, list[tuple[str, str]]]) -> list[dict[str, Any]]:
                pos, batch = pos_batch
                active = list(batch)
                accepted: dict[str, dict[str, Any]] = {}
                retry_counts = {str(idx): 0 for idx, _ in batch}
                retry_reasons: dict[str, str] = {}
                last_results: dict[str, tuple[dict[str, Any], str, int]] = {}
                limits = _judge_retry_token_limits(effective_max_tokens)
                for retry_round, token_limit in enumerate(limits):
                    rows = self._call_api_completion_batch(
                        health,
                        pos + retry_round,
                        [rendered[str(idx)] for idx, _ in active],
                        max_tokens=token_limit,
                        temperature=temperature,
                        top_p=top_p,
                    )
                    unresolved: list[tuple[str, str]] = []
                    for (idx, original_prompt), result in zip(active, rows):
                        last_results[str(idx)] = (result, original_prompt, token_limit)
                        output = str(result.get("judge_output", ""))
                        reason = ""
                        if _judge_cache_entry_needs_retry(result, retry_on_length=retry_on_length):
                            reason = "incomplete"
                        elif output_validator_by_index is not None:
                            try:
                                if not bool(output_validator_by_index(str(idx), output)):
                                    reason = "parse_invalid"
                            except Exception:
                                reason = "parse_invalid"
                        elif output_validator is not None:
                            try:
                                if not bool(output_validator(output)):
                                    reason = "parse_invalid"
                            except Exception:
                                reason = "parse_invalid"
                        if reason:
                            retry_counts[str(idx)] += 1
                            retry_reasons[str(idx)] = reason
                            unresolved.append((idx, original_prompt))
                            continue
                        accepted[str(idx)] = {
                            "index": str(idx),
                            **result,
                            **expected[str(idx)],
                            "judge_prompt": original_prompt,
                            "judge_max_tokens_used": token_limit,
                            "judge_retry_count": retry_counts[str(idx)],
                            "judge_retry_reason": retry_reasons.get(str(idx), ""),
                        }
                    active = unresolved
                    if not active:
                        break
                if active:
                    failed = [str(idx) for idx, _ in active]
                    if not return_unresolved:
                        raise RuntimeError(
                            "Judge produced incomplete or parse-invalid output after retries "
                            f"for indices={failed[:10]}"
                        )
                    for idx, _ in active:
                        result, original_prompt, token_limit = last_results[str(idx)]
                        accepted[str(idx)] = {
                            "index": str(idx),
                            **result,
                            **expected[str(idx)],
                            "judge_prompt": original_prompt,
                            "judge_max_tokens_used": token_limit,
                            "judge_retry_count": retry_counts[str(idx)],
                            "judge_retry_reason": retry_reasons.get(str(idx), ""),
                        }
                return [accepted[str(idx)] for idx, _ in batch]

            max_workers = min(
                len(batches),
                max(1, len(endpoints) * batches_per_endpoint),
                max(1, int(self._arg("judge_api_parallelism", 128))),
            )
            print(
                "[judge:api-batches] "
                f"batches={len(batches)} workers={max_workers} batches_per_endpoint={batches_per_endpoint}"
            )
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = [pool.submit(run_batch, item) for item in enumerate(batches)]
                for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc=desc):
                    runner.append_jsonl(cache_path, future.result())
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
        output_validator: Callable[[str], bool] | None = None,
        output_validator_by_index: Callable[[str, str], bool] | None = None,
        contract_version: str | None = None,
        system_prompt: str | None = None,
        retry_on_length: bool = True,
        return_unresolved: bool = False,
    ) -> dict[str, dict[str, Any]]:
        effective_contract_version = contract_version or str(
            self._arg("judge_cache_contract_version", PERSISTENT_JUDGE_CACHE_CONTRACT_VERSION)
        )
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
                output_validator=output_validator,
                output_validator_by_index=output_validator_by_index,
                contract_version=effective_contract_version,
                system_prompt=system_prompt,
                retry_on_length=retry_on_length,
                return_unresolved=return_unresolved,
            )
        runner, _ = _import_vlmeval_runner()
        from vllm import SamplingParams

        output_dir.mkdir(parents=True, exist_ok=True)
        cache_path = output_dir / cache_name
        if no_resume and cache_path.exists():
            cache_path.unlink()
        existing = {} if no_resume else runner.load_jsonl_by_index(cache_path)
        if len({str(idx) for idx, _ in prompts}) != len(prompts):
            raise ValueError(f"Duplicate judge prompt indices are not supported: {cache_path}")
        effective_max_tokens = max(
            128,
            int(max_tokens if max_tokens is not None else self._arg("judge_max_tokens", 256)),
        )
        expected = {
            str(idx): self._request_metadata(
                prompt,
                max_tokens=effective_max_tokens,
                temperature=temperature,
                top_p=top_p,
                contract_version=effective_contract_version,
                backend="local",
                system_prompt=system_prompt,
            )
            for idx, prompt in prompts
        }
        retry_ids = {
            str(idx)
            for idx, _ in prompts
            if str(idx) in existing
            and (
                any(
                    str(existing[str(idx)].get(key, "")) != str(value)
                    for key, value in expected[str(idx)].items()
                )
                or (
                    not return_unresolved
                    and self._cache_entry_needs_retry(
                        existing[str(idx)],
                        expected[str(idx)],
                        output_validator,
                        output_validator_by_index,
                        retry_on_length=retry_on_length,
                    )
                )
            )
        }
        pending = [
            (idx, prompt)
            for idx, prompt in prompts
            if str(idx) not in existing or str(idx) in retry_ids
        ]
        print(
            "[judge:cached] "
            f"cache={cache_path} rows={len(prompts)} existing={len(existing)} pending={len(pending)} "
            f"retry_incomplete={len(retry_ids)} max_tokens={effective_max_tokens}"
        )
        if pending:
            self._ensure_loaded()
            assert self.llm is not None
            judge_batch_size = max(1, int(self._arg("judge_batch_size", 1024)))
            active = list(pending)
            accepted: dict[str, dict[str, Any]] = {}
            retry_counts = {str(idx): 0 for idx, _ in pending}
            retry_reasons: dict[str, str] = {}
            last_results: dict[str, tuple[dict[str, Any], str, int]] = {}
            for token_limit in _judge_retry_token_limits(effective_max_tokens):
                sampling = SamplingParams(
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=token_limit,
                )
                unresolved: list[tuple[str, str]] = []
                total_batches = math.ceil(len(active) / judge_batch_size)
                for start in tqdm(
                    range(0, len(active), judge_batch_size),
                    total=total_batches,
                    desc=desc,
                ):
                    batch = active[start:start + judge_batch_size]
                    llm_prompts = [
                        self.chat_prompt(prompt, system_prompt=system_prompt)
                        for _, prompt in batch
                    ]
                    outputs = self.llm.generate(llm_prompts, sampling_params=sampling, use_tqdm=False)
                    completed_rows: list[dict[str, Any]] = []
                    for (idx, original_prompt), out in zip(batch, outputs):
                        result = {
                            "judge_output": out.outputs[0].text.strip(),
                            "judge_finish_reason": out.outputs[0].finish_reason,
                            "judge_output_token_count": len(out.outputs[0].token_ids),
                        }
                        last_results[str(idx)] = (result, original_prompt, token_limit)
                        reason = ""
                        if _judge_cache_entry_needs_retry(result, retry_on_length=retry_on_length):
                            reason = "incomplete"
                        elif output_validator_by_index is not None:
                            try:
                                if not bool(
                                    output_validator_by_index(str(idx), str(result["judge_output"]))
                                ):
                                    reason = "parse_invalid"
                            except Exception:
                                reason = "parse_invalid"
                        elif output_validator is not None:
                            try:
                                if not bool(output_validator(str(result["judge_output"]))):
                                    reason = "parse_invalid"
                            except Exception:
                                reason = "parse_invalid"
                        if reason:
                            retry_counts[str(idx)] += 1
                            retry_reasons[str(idx)] = reason
                            unresolved.append((idx, original_prompt))
                            continue
                        accepted[str(idx)] = {
                            "index": str(idx),
                            **result,
                            **expected[str(idx)],
                            "judge_prompt": original_prompt,
                            "judge_max_tokens_used": token_limit,
                            "judge_retry_count": retry_counts[str(idx)],
                            "judge_retry_reason": retry_reasons.get(str(idx), ""),
                        }
                        completed_rows.append(accepted[str(idx)])
                    if completed_rows:
                        runner.append_jsonl(cache_path, completed_rows)
                active = unresolved
                if not active:
                    break
            if active:
                failed = [str(idx) for idx, _ in active]
                if not return_unresolved:
                    raise RuntimeError(
                        "Judge produced incomplete or parse-invalid output after retries "
                        f"for indices={failed[:10]}"
                    )
                unresolved_rows = []
                for idx, _ in active:
                    result, original_prompt, token_limit = last_results[str(idx)]
                    unresolved_rows.append(
                        {
                            "index": str(idx),
                            **result,
                            **expected[str(idx)],
                            "judge_prompt": original_prompt,
                            "judge_max_tokens_used": token_limit,
                            "judge_retry_count": retry_counts[str(idx)],
                            "judge_retry_reason": retry_reasons.get(str(idx), ""),
                        }
                    )
                runner.append_jsonl(cache_path, unresolved_rows)
        return runner.load_jsonl_by_index(cache_path)

    def cleanup(self) -> None:
        if self._using_api_pool():
            self.api_tokenizer = None
            with self._api_sessions_lock:
                sessions = list(self._api_sessions)
                self._api_sessions.clear()
            for session in sessions:
                session.close()
            self._api_thread_local = threading.local()
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


def _restore_screenspot_prediction_metadata(spec: BenchmarkSpec, output_dir: Path) -> None:
    if spec.key != "screenspot":
        return
    pred_table = output_dir / f"{spec.alias}_predictions.xlsx"
    if not pred_table.exists():
        return
    data = pd.read_excel(pred_table)
    if "image_path" in data:
        return
    if "index" not in data:
        raise ValueError(f"ScreenSpot prediction table has no index column: {pred_table}")

    dataset = build_vlmeval_dataset(spec)
    source = dataset.data
    if "index" not in source or "image_path" not in source:
        raise ValueError("ScreenSpot source dataset lacks index/image_path metadata")
    source_keys = source["index"].map(str)
    if source_keys.duplicated().any():
        raise ValueError("ScreenSpot source dataset contains duplicate indices")
    image_paths = dict(zip(source_keys, source["image_path"].map(str)))
    data["image_path"] = data["index"].map(str).map(image_paths)
    missing = data["image_path"].isna()
    if missing.any():
        indices = data.loc[missing, "index"].astype(str).tolist()
        raise ValueError(f"ScreenSpot image_path metadata missing for indices={indices[:10]}")
    data.to_excel(pred_table, index=False)
    print(f"[score:metadata] restored ScreenSpot image_path for {len(data)} rows: {pred_table}")


def _run_tablevqabench_local_score(
    spec: BenchmarkSpec,
    model_path: str,
    output_dir: Path,
) -> dict[str, Any]:
    """Run the pinned TableVQABench parser and four split scorers."""

    _import_vlmeval_runner()
    from vlmeval.dataset.utils.tablevqabench import evaluate_fintabnet, evaluate_tabfact, evaluate_wtq
    from vlmeval.dataset.utils.trace_final25_answer_parsing import unwrap_single_answer_block

    pred_table = output_dir / f"{spec.alias}_predictions.xlsx"
    if not pred_table.exists():
        raise FileNotFoundError(pred_table)
    data = pd.read_excel(pred_table).copy()
    if "prediction" not in data or "answer" not in data or "split" not in data:
        raise ValueError(f"Malformed TableVQABench prediction table: {pred_table}")

    data["raw_prediction"] = data["prediction"]
    data["prediction"] = data["prediction"].map(unwrap_single_answer_block)
    data["prediction"] = data["prediction"].str.replace("^Answer: ", "", regex=True)

    scored_rows: list[dict[str, Any]] = []
    score_table: list[dict[str, Any]] = []
    all_reported_scores: list[float] = []
    data_group = dict(tuple(data.groupby("split")))
    for split in ("fintabnetqa", "vtabfact", "vwtq", "vwtq_syn"):
        group = data_group[split]
        records = group.to_dict(orient="records")
        if split == "fintabnetqa":
            meta = evaluate_fintabnet(records, ["accuracy"])
        elif split == "vtabfact":
            meta = evaluate_tabfact(records, ["accuracy"])
        else:
            meta = evaluate_wtq(records, ["accuracy"])
        values = [float(value) for value in meta.get("average_scores", [])]
        score_table.append({"split": split, "average_scores": values})
        all_reported_scores.extend(values)
        scored_rows.extend(records)

    if len(scored_rows) != len(data) or not all_reported_scores:
        raise ValueError("TableVQABench scorer did not account for every row")
    overall = float(sum(all_reported_scores) / len(all_reported_scores))
    judged_table = output_dir / f"{spec.alias}_trace_final_answer_scored.xlsx"
    pd.DataFrame(scored_rows).to_excel(judged_table, index=False)
    score_csv = output_dir / f"{spec.alias}_predictions_acc.csv"
    pd.DataFrame(score_table).to_csv(score_csv, index=False)
    scores = {"Overall": overall, "table": score_table}
    summary = {
        "dataset": spec.alias,
        "model": model_path,
        "run_name": spec.run_name,
        "harness": "Pinned VLMEvalKit TableVQABench parser and split scorers",
        "rows": int(len(data)),
        "score": overall,
        "scores": scores,
        "aggregation": "macro mean over all official split average_scores values",
        "extraction": {
            "method": "single <answer> unwrap, then pinned VLMEvalKit leading '^Answer: ' removal",
            "changed_predictions": int((data["raw_prediction"] != data["prediction"]).sum()),
        },
        "artifacts": {
            "prediction_table": str(pred_table),
            "judged_table": str(judged_table),
            "score_csv": str(score_csv),
        },
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


def _archive_scalar(value: Any) -> Any:
    if value is None:
        return None
    try:
        if bool(pd.isna(value)):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _archive_first_present(*values: Any) -> Any:
    """Return the first non-null value without treating ordinal zero as missing."""

    for value in values:
        normalized = _archive_scalar(value)
        if normalized is None:
            continue
        if isinstance(normalized, str) and not normalized.strip():
            continue
        return normalized
    return None


def _archive_expected_rows(summary: dict[str, Any]) -> int | None:
    value = _archive_scalar(summary.get("rows"))
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, bool):
        raise RuntimeError(f"Archive summary rows must be a non-negative integer, got {value!r}")
    try:
        rows = int(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise RuntimeError(f"Archive summary rows must be a non-negative integer, got {value!r}") from exc
    if isinstance(value, str):
        is_exact = bool(re.fullmatch(r"\+?\d+", value.strip()))
    else:
        try:
            is_exact = bool(rows == value)
        except Exception:
            is_exact = False
    if rows < 0 or not is_exact:
        raise RuntimeError(f"Archive summary rows must be a non-negative integer, got {value!r}")
    return rows


_ARCHIVE_AGGREGATE_ONLY_SCORE_KEYS = frozenset({"tablevqabench", "mathvision", "mathvista"})

_SCREENSPOT_OFFICIAL_POINT_RE = re.compile(r"x=([\d.]+), y=([\d.]+)")
_SCREENSPOT_ANSWER_BLOCK_RE = re.compile(
    r"<answer>\s*(.*?)\s*</answer>",
    flags=re.IGNORECASE | re.DOTALL,
)
_SCREENSPOT_ACTION_CALL_RE = re.compile(
    r"pyautogui\.(?:click|moveTo)\s*\((.*?)\)",
    flags=re.IGNORECASE | re.DOTALL,
)
_SCREENSPOT_NUMBER = r"(?:\d+(?:\.\d*)?|\.\d+)"
_SCREENSPOT_ACTION_ARGS_RE = re.compile(
    rf"^\s*(?:x\s*=\s*)?({_SCREENSPOT_NUMBER})\s*,\s*"
    rf"(?:y\s*=\s*)?({_SCREENSPOT_NUMBER})\s*$",
    flags=re.IGNORECASE,
)
SCREENSPOT_ACTION_ADAPTER_CONTRACT = "screenspot-vero-absolute-point-v2"


def _screenspot_balanced_boxed_values(text: str) -> list[str]:
    values: list[str] = []
    for match in re.finditer(r"\\boxed\s*\{", text):
        start = match.end()
        depth = 1
        pos = start
        while pos < len(text) and depth:
            if text[pos] == "{":
                depth += 1
            elif text[pos] == "}":
                depth -= 1
            pos += 1
        if depth == 0:
            values.append(text[start : pos - 1])
    return values


def _screenspot_action_points(text: str) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for call in _SCREENSPOT_ACTION_CALL_RE.finditer(text):
        match = _SCREENSPOT_ACTION_ARGS_RE.fullmatch(call.group(1))
        if match:
            point = (float(match.group(1)), float(match.group(2)))
            if all(math.isfinite(coordinate) for coordinate in point):
                points.append(point)
    return points


def _screenspot_unique_point(points: list[tuple[float, float]]) -> tuple[float, float] | None:
    unique = set(points)
    return next(iter(unique)) if len(unique) == 1 else None


def _screenspot_point_text(value: float) -> str:
    return str(int(value)) if value.is_integer() else format(value, ".15g")


def _screenspot_vero_final_answer(value: Any) -> str:
    """Mirror VERO's answer/thinking/boxed unwrapping for ScreenSpot."""

    text = str(value or "").strip()
    if "</think>" in text and "<think>" not in text:
        text = f"<think>\n{text}"
    if "<answer>" in text and "</answer>" in text:
        text = text.split("<answer>", 1)[1].split("</answer>", 1)[0].strip()
    if "</think>" in text:
        text = text.split("</think>", 1)[-1].strip()
    boxed = _screenspot_balanced_boxed_values(text)
    return (boxed[-1] if boxed else text).strip()


def _screenspot_point_from_json(value: Any) -> tuple[float, float] | None:
    if isinstance(value, dict):
        point = value.get("point_2d")
        if isinstance(point, (list, tuple)) and len(point) >= 2:
            try:
                candidate = (float(point[0]), float(point[1]))
            except (TypeError, ValueError, OverflowError):
                candidate = None
            if candidate is not None and all(math.isfinite(item) for item in candidate):
                return candidate
        for child in value.values():
            candidate = _screenspot_point_from_json(child)
            if candidate is not None:
                return candidate
    elif isinstance(value, list):
        for child in value:
            candidate = _screenspot_point_from_json(child)
            if candidate is not None:
                return candidate
    return None


def _screenspot_vero_point(value: Any) -> tuple[float, float] | None:
    """Parse an absolute point with VERO's released ScreenSpot fallback order."""

    text = _screenspot_vero_final_answer(value)
    if not text:
        return None
    try:
        point = _screenspot_point_from_json(json.loads(text))
    except (TypeError, ValueError, json.JSONDecodeError):
        point = None

    if point is None:
        blocks = re.findall(r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", text, flags=re.IGNORECASE)
        for block in reversed(blocks):
            try:
                point = _screenspot_point_from_json(json.loads(block))
            except (TypeError, ValueError, json.JSONDecodeError):
                point = None
            if point is not None:
                break

    if point is None:
        matches = re.findall(
            r'point_2d"?\s*[:=]\s*\[\s*([^\]]+)\]',
            text,
            flags=re.IGNORECASE,
        )
        if matches:
            numbers = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", matches[-1])
            if len(numbers) >= 2:
                point = (float(numbers[0]), float(numbers[1]))

    if point is None:
        pairs = re.findall(r"\[\s*(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)\s*\]", text)
        if pairs:
            point = (float(pairs[-1][0]), float(pairs[-1][1]))

    if point is None:
        numbers = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", text)
        if len(numbers) >= 2:
            point = (float(numbers[-2]), float(numbers[-1]))

    if point is None or not all(math.isfinite(item) for item in point):
        return None
    return point


def _screenspot_explicit_action_prediction(
    value: Any,
    *,
    image_size: tuple[int, int] | None = None,
) -> tuple[str | None, str]:
    """Adapt VERO's absolute point to the pinned ScreenSpot named-x/y parser."""

    point = _screenspot_vero_point(value)
    if point is None:
        return None, "unresolved"
    x, y = point
    method = "vero_absolute_point"
    if image_size is not None:
        width, height = image_size
        if width <= 0 or height <= 0:
            raise ValueError(f"ScreenSpot image dimensions must be positive, got {image_size!r}")
        x = max(0.0, min(1.0, x / width))
        y = max(0.0, min(1.0, y / height))
        method = "vero_absolute_point_to_normalized"
    x_text, y_text = (_screenspot_point_text(coordinate) for coordinate in (x, y))
    return f"pyautogui.click(x={x_text}, y={y_text})", method


def _adapt_screenspot_prediction_table(
    spec: BenchmarkSpec,
    output_dir: Path,
) -> dict[str, Any] | None:
    if spec.key != "screenspot":
        return None
    prediction = output_dir / f"{spec.alias}_predictions.xlsx"
    if not prediction.exists():
        raise FileNotFoundError(prediction)
    data = pd.read_excel(prediction, keep_default_na=False)
    if "prediction" not in data:
        raise KeyError(f"ScreenSpot workbook lacks prediction column: {prediction}")
    original = (
        data["raw_prediction"].copy()
        if "raw_prediction" in data
        else data["prediction"].copy()
    )
    data["raw_prediction"] = original
    adapted: list[Any] = []
    methods: list[str] = []
    changed = 0
    image_sizes: dict[Path, tuple[int, int]] = {}
    rows = data.to_dict(orient="records")
    for raw, row in zip(original, rows):
        image_size = _screenspot_archive_image_size(
            sub_dataset=row.get("SUB_DATASET"),
            image_path=row.get("image_path"),
            cache=image_sizes,
        )
        normalized, method = _screenspot_explicit_action_prediction(
            raw,
            image_size=image_size,
        )
        value = raw if normalized is None else normalized
        changed += int(str(value) != str(raw))
        adapted.append(value)
        methods.append(method)
    data["prediction"] = adapted
    data["trace_extraction_method"] = methods
    data.to_excel(prediction, index=False)
    method_counts = data["trace_extraction_method"].value_counts().to_dict()
    return {
        "contract": SCREENSPOT_ACTION_ADAPTER_CONTRACT,
        "changed_rows": changed,
        "method_counts": {str(key): int(value) for key, value in method_counts.items()},
        "rows": int(len(data)),
    }


def _screenspot_point_in_box_score(
    *,
    bbox: Any,
    prediction: Any,
    image_size: tuple[int, int],
) -> float:
    """Reproduce VLMEvalKit ScreenSpot's instance-level point score."""

    parsed_bbox = bbox if isinstance(bbox, (list, tuple)) else ast.literal_eval(str(bbox))
    if not isinstance(parsed_bbox, (list, tuple)) or len(parsed_bbox) != 4:
        raise ValueError(f"ScreenSpot bbox must contain four values, got {bbox!r}")
    try:
        x1, y1, width, height = (float(value) for value in parsed_bbox)
        image_width, image_height = (int(value) for value in image_size)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"Malformed ScreenSpot geometry: bbox={bbox!r} image_size={image_size!r}") from exc
    if not all(math.isfinite(value) for value in (x1, y1, width, height)):
        raise ValueError(f"ScreenSpot bbox contains a non-finite value: {bbox!r}")
    if image_width <= 0 or image_height <= 0:
        raise ValueError(f"ScreenSpot image dimensions must be positive, got {image_size!r}")

    x2 = x1 + width - 1
    y2 = y1 + height - 1
    normalized_bbox = [
        (0.0 if value == -1 else value) / divisor
        for value, divisor in zip(
            (x1, y1, x2, y2),
            (image_width, image_height, image_width, image_height),
        )
    ]
    if any(value < 0 or value > 1 for value in normalized_bbox):
        raise ValueError(
            f"ScreenSpot bbox out of range: {normalized_bbox!r} | {bbox!r} | {image_size!r}"
        )

    _import_vlmeval_runner()
    from vlmeval.dataset.GUI.screenspot import parse_bbox_aguvis

    point_x, point_y = parse_bbox_aguvis(str(prediction))
    if point_x > 1 or point_y > 1:
        point_x /= image_width
        point_y /= image_height
    return float(
        normalized_bbox[0] <= point_x <= normalized_bbox[2]
        and normalized_bbox[1] <= point_y <= normalized_bbox[3]
    )


def _screenspot_archive_image_size(
    *,
    sub_dataset: Any,
    image_path: Any,
    cache: dict[Path, tuple[int, int]],
) -> tuple[int, int]:
    """Resolve original ScreenSpot dimensions from the same LMUData layout as VLMEvalKit."""

    sub_dataset_value = str(sub_dataset or "").strip()
    image_path_value = str(image_path or "").strip()
    if not sub_dataset_value or not image_path_value:
        raise ValueError(
            "ScreenSpot row-level archival requires SUB_DATASET and image_path metadata"
        )
    configured_root = os.environ.get("LMUData", "").strip()
    lmu_root = (
        Path(configured_root)
        if configured_root and Path(configured_root).exists()
        else Path.home() / "LMUData"
    )
    path = lmu_root / "images" / sub_dataset_value / image_path_value
    if path not in cache:
        from PIL import Image

        with Image.open(path) as image:
            cache[path] = image.size
    return cache[path]


def _archive_table_candidates(output_dir: Path, summary: dict[str, Any]) -> list[Path]:
    values: list[Any] = []

    def collect(value: Any) -> None:
        if isinstance(value, dict):
            for child in value.values():
                collect(child)
        elif isinstance(value, (list, tuple)):
            for child in value:
                collect(child)
        else:
            values.append(value)

    collect(summary.get("artifacts") or {})
    collect(summary.get("outputs") or {})
    paths: list[Path] = []
    for value in values:
        if not isinstance(value, (str, Path)):
            continue
        path = Path(value)
        if path.suffix.lower() in {".xlsx", ".xls"} and path.exists():
            paths.append(path)
    paths.extend(sorted(output_dir.glob("*.xlsx")))
    return list(dict.fromkeys(paths))


def _archive_best_score_table(output_dir: Path, summary: dict[str, Any]) -> pd.DataFrame:
    best: tuple[int, pd.DataFrame] | None = None
    for path in _archive_table_candidates(output_dir, summary):
        try:
            frame = pd.read_excel(path, keep_default_na=False)
        except Exception:
            continue
        columns = set(frame.columns)
        quality = 0
        lowered = path.name.lower()
        if any(token in lowered for token in ("judged", "scored", "result")):
            quality += 100
        if any(key in columns for key in ("eval_score", "hit", "score", "correct")):
            quality += 80
        if any(key in columns for key in ("eval_pred", "res", "extract", "extract_answer", "raw_prediction")):
            quality += 40
        if "prediction" in columns:
            quality += 20
        if "index" in columns:
            quality += 10
        quality += min(len(frame), 10)
        if best is None or quality > best[0]:
            best = (quality, frame)
    if best is None:
        raise FileNotFoundError(f"No readable score/prediction table under {output_dir}")
    return best[1]


def _archive_judge_events(output_dir: Path) -> dict[str, list[dict[str, Any]]]:
    events: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path in sorted(output_dir.glob("*.jsonl")):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if not isinstance(row, dict) or "judge_output" not in row or "index" not in row:
                continue
            events[str(row["index"])].append(
                {
                    "cache": path.name,
                    "prompt": row.get("judge_prompt", ""),
                    "response": row.get("judge_output", ""),
                    "request_hash": row.get("request_hash"),
                    "contract_version": row.get("contract_version"),
                    "finish_reason": row.get("judge_finish_reason"),
                    "retry_count": row.get("judge_retry_count", 0),
                    "max_tokens_used": row.get("judge_max_tokens_used"),
                }
            )
    return events


def _archive_direct_score_slices(
    args: argparse.Namespace,
    spec: BenchmarkSpec,
    model_path: str,
    model_slug: str,
    output_dir: Path,
    summary: dict[str, Any],
) -> tuple[Path | None, Path | None]:
    if not os.environ.get("TRACE_FINAL25_HF_SPOOL_ROOT", "").strip():
        return None, None
    from final25_archive_hooks import (
        canonical_json,
        emit_extraction_slice,
        emit_score_slice,
        resolve_model_revision,
        resolve_model_source,
        sanitize_benchmark_source_row,
    )

    frame = _archive_best_score_table(output_dir, summary)
    expected_rows = _archive_expected_rows(summary)
    if expected_rows is not None and len(frame) != expected_rows:
        raise RuntimeError(
            f"Refusing to archive {spec.key}: selected score table has {len(frame)} rows, "
            f"but the score summary declares {expected_rows}"
        )
    judge_events = _archive_judge_events(output_dir)
    source_rows_by_index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    source_candidates = [
        output_dir / f"{spec.alias}_predictions.xlsx",
        output_dir / "predictions.xlsx",
    ]
    for source_path in source_candidates:
        if not source_path.exists():
            continue
        try:
            source_frame = pd.read_excel(source_path, keep_default_na=False)
        except Exception:
            continue
        if len(source_frame) != len(frame):
            raise RuntimeError(
                f"Refusing to archive {spec.key}: selected score table has {len(frame)} rows, "
                f"but source prediction table {source_path.name} has {len(source_frame)}"
            )
        if expected_rows is not None and len(source_frame) != expected_rows:
            raise RuntimeError(
                f"Refusing to archive {spec.key}: source prediction table {source_path.name} has "
                f"{len(source_frame)} rows, but the score summary declares {expected_rows}"
            )
        for source_ordinal, source_row in enumerate(source_frame.to_dict(orient="records")):
            source_rows_by_index[str(source_row.get("index", source_ordinal))].append(
                {**source_row, "_source_ordinal": source_ordinal}
            )
        break
    source_occurrences: defaultdict[str, int] = defaultdict(int)
    extraction_records: list[dict[str, Any]] = []
    score_records: list[dict[str, Any]] = []
    missing_row_scores: list[str] = []
    screenspot_row_scores: list[float] = []
    screenspot_image_sizes: dict[Path, tuple[int, int]] = {}
    aggregate_only_scores = spec.key in _ARCHIVE_AGGREGATE_ONLY_SCORE_KEYS
    aggregate_score = _archive_scalar(summary.get("score"))
    if aggregate_only_scores and aggregate_score is None:
        raise RuntimeError(
            f"Refusing to archive {spec.key}: aggregate-only score contract requires summary.score"
        )
    generated_keys = {
        "prediction",
        "raw_prediction",
        "finish_reason",
        "output_token_count",
        "prompt_token_count",
        "request_hash",
        "source_ordinal",
        "source_row_hash",
        "prompt",
        "usage",
        "_source_ordinal",
    }
    for ordinal, raw_row in enumerate(frame.to_dict(orient="records")):
        row = {str(key): _archive_scalar(value) for key, value in raw_row.items()}
        index = str(row.get("index", ordinal))
        occurrence = source_occurrences[index]
        source_occurrences[index] += 1
        source_matches = source_rows_by_index.get(index, [])
        source_row = source_matches[min(occurrence, len(source_matches) - 1)] if source_matches else {}
        events = judge_events.get(index, [])
        model_response = row.get("raw_prediction", source_row.get("raw_prediction"))
        if model_response in {None, ""}:
            model_response = source_row.get("prediction", row.get("prediction", ""))
        extraction_value = None
        extraction_method = ""
        for key in ("extract_answer", "eval_pred", "res", "extract", "prediction"):
            value = row.get(key)
            if value not in {None, ""}:
                extraction_value = value
                extraction_method = key
                break
        if spec.key == "screenspot":
            point = _screenspot_vero_point(str(row.get("raw_prediction", model_response)))
            if point is None:
                point = (0.0, 0.0)
            extraction_value = point
            extraction_method = "vero_screenspot_absolute_point"
        for method_key in ("extract_answer_method", "eval_pred_method", "trace_extraction_method"):
            if row.get(method_key) not in {None, ""}:
                extraction_method = str(row[method_key])
                break
        source_hash = str(row.get("source_row_hash") or source_row.get("source_row_hash") or "").strip()
        if not source_hash:
            safe_source_row = sanitize_benchmark_source_row(
                {key: value for key, value in (source_row or row).items() if key not in generated_keys}
            )
            source_hash = hashlib.sha256(canonical_json(safe_source_row).encode("utf-8")).hexdigest()
        event_request_hashes = [event.get("request_hash") for event in events if event.get("request_hash")]
        extraction_request_hash = hashlib.sha256(
            canonical_json(
                {
                    "contract_version": "trace-final25-direct-extraction-v1",
                    "benchmark": spec.key,
                    "source_row_hash": source_hash,
                    "model_response": model_response,
                    "judge_request_hashes": event_request_hashes,
                    "extraction": extraction_value,
                }
            ).encode("utf-8")
        ).hexdigest()
        common = {
            "source_index": index,
            "source_ordinal": int(
                _archive_first_present(
                    row.get("source_ordinal"),
                    source_row.get("source_ordinal"),
                    source_row.get("_source_ordinal"),
                    ordinal,
                )
            ),
            "source_row_hash": source_hash,
            "question": row.get("question", source_row.get("question", row.get("query"))),
            "ground_truth": row.get("answer", source_row.get("answer")),
            "metadata": {"benchmark_run_name": spec.run_name},
        }
        extraction_records.append(
            {
                **common,
                "request_hash": extraction_request_hash,
                "model_response": model_response,
                "judge_prompt": canonical_json([event.get("prompt", "") for event in events]),
                "judge_response": canonical_json([event.get("response", "") for event in events]),
                "normalized_extraction": {
                    "status": "resolved" if extraction_value not in {None, ""} else "invalid",
                    "value": extraction_value,
                    "method": extraction_method,
                },
                "retries": {
                    "events": events,
                    "total_retries": sum(int(event.get("retry_count") or 0) for event in events),
                },
            }
        )
        score_value = None
        for key in ("eval_score", "hit", "score", "correct"):
            if row.get(key) not in {None, ""}:
                score_value = row[key]
                break
        if spec.key == "screenspot":
            sub_dataset = _archive_first_present(
                row.get("SUB_DATASET"), source_row.get("SUB_DATASET")
            )
            image_path = _archive_first_present(row.get("image_path"), source_row.get("image_path"))
            bbox = _archive_first_present(row.get("bbox"), source_row.get("bbox"))
            prediction = _archive_first_present(
                row.get("prediction"), source_row.get("prediction"), model_response
            )
            derived_score = _screenspot_point_in_box_score(
                bbox=bbox,
                prediction=prediction,
                image_size=_screenspot_archive_image_size(
                    sub_dataset=sub_dataset,
                    image_path=image_path,
                    cache=screenspot_image_sizes,
                ),
            )
            if score_value is not None:
                try:
                    explicit_score = float(score_value)
                except (TypeError, ValueError, OverflowError) as exc:
                    raise RuntimeError(
                        f"ScreenSpot row {index} has a non-numeric explicit score: {score_value!r}"
                    ) from exc
                if not math.isclose(explicit_score, derived_score, rel_tol=0.0, abs_tol=1e-12):
                    raise RuntimeError(
                        f"ScreenSpot row {index} explicit score {explicit_score} does not match "
                        f"the official point-in-box score {derived_score}"
                    )
            score_value = derived_score
            screenspot_row_scores.append(derived_score)
        if score_value is None and not aggregate_only_scores:
            missing_row_scores.append(index)
        scorer = str(summary.get("harness") or summary.get("run_name") or spec.run_name)
        score_request_hash = hashlib.sha256(
            canonical_json(
                {
                    "contract_version": "trace-final25-score-v1",
                    "extraction_request_hash": extraction_request_hash,
                    "prediction": extraction_value,
                    "score": score_value,
                    "scorer": scorer,
                }
            ).encode("utf-8")
        ).hexdigest()
        score_records.append(
            {
                **common,
                "metadata": {
                    **common["metadata"],
                    "score_contract": "aggregate_only" if aggregate_only_scores else "per_row",
                    **({"aggregate_score": aggregate_score} if aggregate_only_scores else {}),
                },
                "request_hash": score_request_hash,
                "prediction": extraction_value,
                "score": score_value,
                "scorer": scorer,
                "excluded": False,
            }
        )

    if missing_row_scores:
        raise RuntimeError(
            f"Refusing to archive {spec.key}: {len(missing_row_scores)} scored rows have no explicit "
            f"per-row score; first indices={missing_row_scores[:10]}"
        )
    if spec.key == "screenspot":
        official_score = score_to_percent(summary.get("score"))
        if official_score is None:
            raise RuntimeError("Refusing to archive ScreenSpot without an official aggregate score")
        derived_score = (
            sum(screenspot_row_scores) / len(screenspot_row_scores) * 100.0
            if screenspot_row_scores
            else 0.0
        )
        if not math.isclose(derived_score, official_score, rel_tol=0.0, abs_tol=1e-9):
            raise RuntimeError(
                "Refusing to archive ScreenSpot because derived per-row scores do not match the "
                f"official aggregate: derived={derived_score} official={official_score}"
            )

    identity = {
        "model": resolve_model_source(model_slug, model_path),
        "model_slug": model_slug,
        "model_revision": resolve_model_revision(model_slug, model_path),
        "seed": int(getattr(args, "seed", 0)),
        "benchmark": spec.key,
        "dataset_alias": spec.alias,
        "dataset_split": spec.split or "default",
        "dataset_revision": os.environ.get(
            "TRACE_FINAL25_DATASET_REVISION",
            os.environ.get("TRACE_VLMEVALKIT_GIT_COMMIT", "unknown"),
        ),
    }
    extraction_path = emit_extraction_slice(
        records=extraction_records,
        contract_version="trace-final25-direct-extraction-v1",
        aggregate={"rows": len(extraction_records), "judge_model": getattr(args, "judge_model", None)},
        **identity,
    )
    score_path = emit_score_slice(
        records=score_records,
        contract_version="trace-final25-score-v1",
        aggregate=summary,
        **identity,
    )
    return extraction_path, score_path


def _run_direct_vlmeval(args: argparse.Namespace, spec: BenchmarkSpec, model_path: str, output_dir: Path) -> dict[str, Any]:
    runner, _ = _import_vlmeval_runner()
    _patch_refspatial_point_parser(spec)
    _restore_screenspot_prediction_metadata(spec, output_dir)
    screenspot_adapter = _adapt_screenspot_prediction_table(spec, output_dir)
    _sanitize_prediction_table_for_scoring(spec, output_dir)
    ns = _namespace_for_spec(args, spec, output_dir, model_path)
    summary = runner.run_vlmeval_evaluate(ns)
    if spec.key == "screenspot":
        summary["harness"] = (
            "VERO absolute-point parser with pinned VLMEvalKit ScreenSpot point-in-box geometry"
        )
        summary["parser"] = (
            "VERO JSON/fenced JSON/point_2d/pair/final-number fallbacks, then "
            "normalized named-x/y adapter"
        )
        summary["prediction_adapter"] = screenspot_adapter
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
    """Compatibility no-op: ScreenSpot now uses the pinned parser unchanged."""

    del spec


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
        "harness": "Trace subset-safe WeMath option-letter exact scorer",
        "rows": len(data),
        "score": overall,
        "scores": scores,
        "artifacts": {"prediction_table": str(pred_table), "judged_table": str(judged), "score_csv": str(score_csv)},
    }
    write_json(output_dir / "scores.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=json_default))
    return summary


def _physics_ground_truths(value: Any) -> list[str]:
    """Decode the typed answer list produced by the pinned Physics dataset."""

    if isinstance(value, (list, tuple)):
        raw_values = list(value)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError("Physics source answer is empty")
        if text.startswith("[") and text.endswith("]"):
            try:
                decoded = ast.literal_eval(text)
            except (SyntaxError, ValueError) as exc:
                raise ValueError(f"Malformed Physics source answer list: {value!r}") from exc
            if not isinstance(decoded, (list, tuple)):
                raise ValueError(f"Physics source answer did not decode to a list: {value!r}")
            raw_values = list(decoded)
        else:
            raw_values = [text]
    else:
        raise ValueError(f"Physics source answer has unsupported type {type(value).__name__}")

    answers: list[str] = []
    for item in raw_values:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"Physics source answer contains a non-string or empty item: {value!r}")
        answers.append(item.strip())
    if not answers:
        raise ValueError("Physics source answer list is empty")
    return answers


def _parse_physics_equivalence_output(value: Any) -> bool | None:
    text = str(value or "").strip()
    if not text:
        return None
    # Match pinned VLMEvalKit is_equiv exactly: any nonempty judge response is
    # valid, and the decision is true iff the response contains "true".
    return "true" in text.lower()


def _physics_equivalence_output(value: Any) -> bool:
    return bool(str(value or "").strip())


def _run_physics_subset_score(
    args: argparse.Namespace,
    spec: BenchmarkSpec,
    model_path: str,
    output_dir: Path,
    judge: PersistentJudge,
) -> dict[str, Any]:
    _import_vlmeval_runner()
    from vlmeval.dataset.utils.physic import PHYSIC_acc
    from vlmeval.dataset.utils.physics_eval_utils import (
        Judge_SYS_PROMPT,
        extract_final_answer_allform,
        is_equiv,
    )
    from vlmeval.smp import load

    pred_table = output_dir / f"{spec.alias}_predictions.xlsx"
    if not pred_table.exists():
        raise FileNotFoundError(pred_table)
    data = load(str(pred_table))
    source_data = build_vlmeval_dataset(spec).data
    source_by_index: dict[str, Any] = {}
    for _, source_row in source_data.iterrows():
        source_index = str(source_row["index"])
        if source_index in source_by_index:
            raise ValueError(f"Physics source dataset has duplicate index {source_index!r}")
        source_by_index[source_index] = source_row

    class PromptRecorder:
        def __init__(self) -> None:
            self.sys_prompt = ""
            self.calls: list[tuple[str, str]] = []

        def generate(self, prompt: str) -> str:
            self.calls.append((str(self.sys_prompt), str(prompt)))
            return "False"

    rows: list[dict[str, Any]] = []
    row_states: list[dict[str, Any]] = []
    pair_inputs: list[tuple[int, str, int, str, int, str, dict[str, Any]]] = []
    prompts: list[tuple[str, str]] = []
    prompt_pairs: dict[str, dict[str, Any]] = {}
    seen_prediction_indices: set[str] = set()
    for ordinal, (_, input_row) in enumerate(data.iterrows()):
        row = input_row.copy()
        row_index = str(row.get("index", ""))
        if not row_index or row_index in seen_prediction_indices:
            raise ValueError(f"Physics predictions contain a missing or duplicate index {row_index!r}")
        seen_prediction_indices.add(row_index)
        source_row = source_by_index.get(row_index)
        if source_row is None:
            raise ValueError(f"Physics prediction index is absent from the source dataset: {row_index!r}")
        ground_truths = _physics_ground_truths(source_row.get("answer"))

        prediction_text = row.get("prediction")
        if not isinstance(prediction_text, str) or not prediction_text.strip():
            boxed_predictions: list[str] = []
        else:
            extracted = extract_final_answer_allform(prediction_text)
            flattened: list[str] = []
            for item in extracted:
                values = item if isinstance(item, (list, tuple)) else [item]
                flattened.extend(str(value).strip() for value in values if str(value).strip())
            boxed_predictions = list(dict.fromkeys(flattened))

        state = {
            "ground_truths": ground_truths,
            "boxed_predictions": boxed_predictions,
            "comparisons": [[] for _ in boxed_predictions],
        }
        row_states.append(state)
        row["physics_ground_truths"] = json.dumps(ground_truths, ensure_ascii=False)
        row["physics_boxed_predictions"] = json.dumps(boxed_predictions, ensure_ascii=False)
        rows.append(row.to_dict())

        for pred_ordinal, pred in enumerate(boxed_predictions):
            for gt_ordinal, gt in enumerate(ground_truths):
                pair_inputs.append((ordinal, row_index, pred_ordinal, pred, gt_ordinal, gt, state))

    def probe_pair(
        item: tuple[int, str, int, str, int, str, dict[str, Any]],
    ) -> tuple[tuple[int, str, int, str, int, str, dict[str, Any]], dict[str, Any], list[tuple[str, str]]]:
        _, _, pred_ordinal, pred, gt_ordinal, gt, _ = item
        recorder = PromptRecorder()
        comparison = is_equiv(recorder, pred, gt)
        comparison["pred_ordinal"] = pred_ordinal
        comparison["gt_ordinal"] = gt_ordinal
        return item, comparison, recorder.calls

    probe_workers = max(1, int(getattr(args, "eval_nproc", 16)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=probe_workers) as pool:
        probed = pool.map(probe_pair, pair_inputs)
        for item, comparison, calls in tqdm(
            probed,
            total=len(pair_inputs),
            desc=f"{spec.alias} official deterministic equivalence",
        ):
            ordinal, row_index, pred_ordinal, pred, gt_ordinal, gt, state = item
            if not calls:
                if not bool(comparison.get("final_result")):
                    raise RuntimeError(
                        "Pinned Physics is_equiv returned an unresolved deterministic result for "
                        f"index={row_index!r} pred={pred!r} gt={gt!r}: {comparison}"
                    )
                state["comparisons"][pred_ordinal].append(comparison)
                continue
            if len(calls) != 1 or calls[0][0] != Judge_SYS_PROMPT:
                raise RuntimeError(
                    "Pinned Physics is_equiv produced an unexpected judge-call contract for "
                    f"index={row_index!r} pred={pred!r} gt={gt!r}: {calls}"
                )
            identity = json.dumps(
                {"index": row_index, "pred": pred, "pred_ordinal": pred_ordinal, "gt": gt, "gt_ordinal": gt_ordinal},
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )
            digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
            prompt_id = f"{ordinal:06d}__p{pred_ordinal}__g{gt_ordinal}__{digest}"
            prompts.append((prompt_id, calls[0][1]))
            comparison["judge_cache_index"] = prompt_id
            state["comparisons"][pred_ordinal].append(comparison)
            prompt_pairs[prompt_id] = comparison

    judged = judge.run_cached(
        output_dir=output_dir,
        prompts=prompts,
        cache_name="physics_qwen3_32b_official_equiv.jsonl",
        max_tokens=4096,
        no_resume=args.no_resume,
        desc=f"{spec.alias} official equivalence judge",
        output_validator=_physics_equivalence_output,
        contract_version=DIRECT_JUDGE_CACHE_CONTRACTS["physics_equivalence"],
        system_prompt=Judge_SYS_PROMPT,
    )
    for prompt_id, comparison in prompt_pairs.items():
        output = str(judged.get(prompt_id, {}).get("judge_output", "")).strip()
        decision = _parse_physics_equivalence_output(output)
        if decision is None:
            raise RuntimeError(f"Physics judge produced a malformed decision for {prompt_id}: {output!r}")
        comparison["llm_result"] = int(decision)
        comparison["final_result"] = decision
        comparison["llm_comparison_result"] = output

    for row, state in zip(rows, row_states):
        correct_count = sum(
            any(bool(comparison.get("final_result")) for comparison in comparisons)
            for comparisons in state["comparisons"]
        )
        prediction_count = len(state["boxed_predictions"])
        row["res"] = correct_count / prediction_count if prediction_count else 0.0
        row["log"] = json.dumps(state["comparisons"], ensure_ascii=False, default=json_default)

    judged_table = output_dir / f"{spec.alias}_official_judged_qwen3_32b.xlsx"
    pd.DataFrame(rows).to_excel(judged_table, index=False)
    score_df = PHYSIC_acc(str(judged_table))
    score_csv = output_dir / f"{spec.alias}_official_judged_qwen3_32b_score.csv"
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
        "harness": "Pinned VLMEvalKit Physics boxed-answer/is_equiv scorer with batched Qwen3-32B fallback",
        "contract_version": DIRECT_JUDGE_CACHE_CONTRACTS["physics_equivalence"],
        "official_source": {
            "extractor": "vlmeval.dataset.utils.physics_eval_utils.extract_final_answer_allform",
            "equivalence": "vlmeval.dataset.utils.physics_eval_utils.is_equiv",
            "aggregation": "vlmeval.dataset.utils.physic.PHYSIC_acc",
            "hardening_deviation": "empty, truncated, or failed judge responses fail the job instead of scoring false",
        },
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
    """Apply pinned ChartMuseum's non-empty ``'yes' in response`` rule."""
    text = str(value or "").strip()
    return int("yes" in text.lower()) if text else None


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


def _parse_charxiv_score_output(value: Any) -> float | None:
    output = str(value or "")
    obj = _parse_json_object(output)
    raw_score = obj.get("score")
    if raw_score is None:
        score_match = re.search(r'"?score"?\s*[:=]\s*([01](?:\.\d+)?)', output, flags=re.I)
        raw_score = score_match.group(1) if score_match else None
    try:
        score = float(raw_score)
    except (TypeError, ValueError):
        return None
    return score if 0.0 <= score <= 1.0 else None


def _charxiv_primary_score(scores: dict[str, float]) -> float:
    return float(scores["Overall"] * 100.0)


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


def _valid_evochart_judge_output(value: Any) -> bool:
    score, _, _ = _resolve_evochart_judgement(value, "")
    return score is not None


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


def _logicvista_label_tokens(value: Any) -> tuple[str, list[str]] | None:
    compact = re.sub(r"[\s,;/]+", "", str(value or "").strip().upper())
    if re.fullmatch(r"[A-KZ]+", compact):
        return "letter", list(compact)
    if re.fullmatch(r"[1-9]+", compact):
        return "number", list(compact)
    return None


def _normalize_logicvista_judgement(judge_output: Any, answer: Any) -> tuple[str, bool, bool] | None:
    extracted = _logicvista_label_tokens(judge_output)
    target = _logicvista_label_tokens(answer)
    if extracted is None or target is None:
        return None
    extracted_kind, extracted_tokens = extracted
    target_kind, target_tokens = target
    mapped = extracted_kind != target_kind
    if mapped and extracted_tokens == ["Z"]:
        normalized_tokens = ["Z"]
    elif extracted_kind == "number" and target_kind == "letter":
        normalized_tokens = [chr(ord("A") + int(token) - 1) for token in extracted_tokens]
    elif extracted_kind == "letter" and target_kind == "number":
        if any(token == "Z" for token in extracted_tokens):
            normalized_tokens = ["Z"]
        else:
            normalized_tokens = [str(ord(token) - ord("A") + 1) for token in extracted_tokens]
    else:
        normalized_tokens = extracted_tokens
    normalized = "".join(sorted(normalized_tokens))
    expected = "".join(sorted(target_tokens))
    return normalized, normalized == expected, mapped


_OFFICIAL_MATH_EXTRACTION_ROUTES = frozenset(
    {
        ("mathvision", "mathvision_qwen3_32b_extract.jsonl"),
        ("mathvista", "mathvista_qwen3_32b_extract.jsonl"),
        ("mathverse", "mathverse_qwen3_32b_extract.jsonl"),
    }
)


_MATHVERSE_SCORE_DECISION_RE = re.compile(
    r"(?m)^[ \t]*(?:"
    r"\*\*Judgement[ \t]*:[ \t]*([01])\*\*"
    r"|\*\*Judgement\*\*[ \t]*:[ \t]*(?:\*\*([01])\*\*|([01]))"
    r"|Judgement[ \t]*:[ \t]*(?:\*\*([01])\*\*|([01]))"
    r")(?=$|[ \t\r\n])"
)


def _parse_mathverse_score_output(value: Any) -> int | None:
    output = str(value or "").strip()
    if output in {"0", "1"}:
        return int(output)
    matches = list(_MATHVERSE_SCORE_DECISION_RE.finditer(output))
    if not matches:
        return None
    decisions = {
        int(next(group for group in match.groups() if group is not None))
        for match in matches
    }
    return decisions.pop() if len(decisions) == 1 else None


def _math_like_judge_cache_policy(
    spec_key: str,
    cache_name: str,
) -> tuple[Callable[[str], bool], str]:
    route = (spec_key, cache_name)
    policies: dict[tuple[str, str], tuple[Callable[[str], bool], str]] = {
        ("mathvision", "mathvision_qwen3_32b_extract.jsonl"): (
            _nonempty_judge_output,
            DIRECT_JUDGE_CACHE_CONTRACTS["mathvision_extract"],
        ),
        ("mathvista", "mathvista_qwen3_32b_extract.jsonl"): (
            _nonempty_judge_output,
            DIRECT_JUDGE_CACHE_CONTRACTS["mathvista_extract"],
        ),
        ("mathverse", "mathverse_qwen3_32b_extract.jsonl"): (
            _nonempty_judge_output,
            DIRECT_JUDGE_CACHE_CONTRACTS["mathverse_extract"],
        ),
        ("mathverse", "mathverse_qwen3_32b_score.jsonl"): (
            lambda output: _parse_mathverse_score_output(output) is not None,
            DIRECT_JUDGE_CACHE_CONTRACTS["mathverse_score"],
        ),
        ("logicvista", "logicvista_qwen3_32b_extract.jsonl"): (
            lambda output: _logicvista_label_tokens(output) is not None,
            DIRECT_JUDGE_CACHE_CONTRACTS["logicvista_extract"],
        ),
    }
    if route not in policies:
        raise RuntimeError(f"No judge cache contract registered for {spec_key}:{cache_name}")
    return policies[route]


def _repair_logicvista_option_summary(
    spec: BenchmarkSpec,
    model_path: str,
    output_dir: Path,
    summary: dict[str, Any],
) -> dict[str, Any]:
    if spec.key != "logicvista":
        return summary
    judged_table = output_dir / f"{spec.alias}_judged_qwen3_32b.xlsx"
    cache_path = output_dir / "logicvista_qwen3_32b_extract.jsonl"
    if not judged_table.exists() or not cache_path.exists():
        return summary

    runner, _ = _import_vlmeval_runner()
    from vlmeval.dataset.utils.logicvista import evaluate_logicvista
    from vlmeval.smp import dump, get_intermediate_file_path

    data = pd.read_excel(judged_table, keep_default_na=False)
    cached = runner.load_jsonl_by_index(cache_path)
    malformed: list[str] = []
    normalized_values: list[str] = []
    hits: list[int] = []
    mapped_rows = 0
    for _, row in data.iterrows():
        index = str(row.get("index"))
        judge_output = cached.get(index, {}).get("judge_output", "")
        normalized = _normalize_logicvista_judgement(judge_output, row.get("answer", ""))
        if normalized is None:
            malformed.append(index)
            normalized_values.append("")
            hits.append(0)
            continue
        value, hit, mapped = normalized
        normalized_values.append(value)
        hits.append(int(hit))
        mapped_rows += int(mapped)
    if malformed:
        raise RuntimeError(
            f"LogicVista judge produced {len(malformed)} malformed option extractions; "
            f"first indices={malformed[:10]}"
        )

    data["res"] = normalized_values
    data["log"] = "Succeed"
    data["hit"] = hits
    data.to_excel(judged_table, index=False)
    score_df = evaluate_logicvista(str(judged_table))
    dump(score_df, str(get_intermediate_file_path(str(judged_table), "_score", "csv")))
    records = json.loads(score_df.to_json(orient="records"))
    overall_rows = [row for row in records if row.get("Task&Skill") == "Overall"]
    if len(overall_rows) != 1:
        raise RuntimeError(f"LogicVista scorer returned no unique Overall row: {records}")
    overall = float(overall_rows[0]["acc"])
    repaired_summary = {
        "dataset": spec.alias,
        "model": model_path,
        "rows": len(data),
        "score": overall,
        "scores": {"table": records, "Overall": overall},
        "artifacts": {
            **(summary.get("artifacts") or {}),
            "judged_table": str(judged_table),
            "logicvista_ordinal_label_mappings": mapped_rows,
            "logicvista_validated_judge_rows": int(len(data)),
        },
    }
    write_json(output_dir / "scores.json", repaired_summary)
    print(json.dumps(repaired_summary, indent=2, ensure_ascii=False, default=json_default))
    return repaired_summary


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
        prefix = "Judge output:"
        raw_decision = log_score[len(prefix):].strip() if log_score.startswith(prefix) else ""
        decision = _parse_mathverse_score_output(raw_decision)
        if decision is None:
            malformed.append(str(row.get("index")))
            repaired.append(current)
            continue
        fixed = decision == 1
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
        bad = values.eq("") | ~values.map(lambda value: set(value) <= set("ABCDEFGHIJKZ123456789"))
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
        output_validator, contract_version = _math_like_judge_cache_policy(spec.key, cache_name)
        if spec.key == "mathverse" and cache_name == "mathverse_qwen3_32b_score.jsonl":
            accepted: dict[str, dict[str, Any]] = {}
            pending = list(prompts)
            if not pending:
                return accepted
            cache_path = Path(cache_name)
            for attempt in range(5):
                attempt_cache = (
                    cache_name
                    if attempt == 0
                    else f"{cache_path.stem}_retry_{attempt}{cache_path.suffix}"
                )
                judged = judge.run_cached(
                    output_dir=call_args.output_dir,
                    prompts=pending,
                    cache_name=attempt_cache,
                    max_tokens=max_tokens,
                    temperature=attempt * 0.5,
                    top_p=top_p,
                    no_resume=call_args.no_resume,
                    desc=f"{call_args.dataset} local judge score attempt {attempt + 1}",
                    output_validator=_nonempty_judge_output,
                    contract_version=f"{contract_version}-attempt{attempt + 1}",
                )
                unresolved = []
                for index, prompt in pending:
                    item = judged.get(str(index), {})
                    if output_validator(item.get("judge_output", "")):
                        accepted[str(index)] = item
                    else:
                        unresolved.append((index, prompt))
                pending = unresolved
                if not pending:
                    return accepted
            failed = [str(index) for index, _ in pending]
            raise RuntimeError(
                f"MathVerse judge produced non-0/1 output after 5 attempts; indices={failed[:10]}"
            )
        return judge.run_cached(
            output_dir=call_args.output_dir,
            prompts=prompts,
            cache_name=cache_name,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            no_resume=call_args.no_resume,
            desc=f"{call_args.dataset} local judge",
            output_validator=output_validator,
            contract_version=contract_version,
            retry_on_length=(spec.key, cache_name) not in _OFFICIAL_MATH_EXTRACTION_ROUTES,
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
            summary = _repair_logicvista_option_summary(spec, model_path, output_dir, summary)
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
    print(f"[charxiv judge] dataset={spec.alias} rows={len(data)} existing={len(existing)}")
    prompts: list[tuple[str, str]] = []
    for _, row in data.iterrows():
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
        output_validator=lambda output: _parse_charxiv_score_output(output) is not None,
        contract_version=DIRECT_JUDGE_CACHE_CONTRACTS["charxiv_judge"],
    )
    judged_map = {**existing, **raw}
    prediction_by_index = {str(row["index"]): row.get("prediction") for _, row in data.iterrows()}
    malformed: list[str] = []
    for idx, item in list(judged_map.items()):
        output = str(item.get("judge_output", ""))
        parsed_score = item.get("score")
        if parsed_score is None:
            parsed_score = _parse_charxiv_score_output(output)
        try:
            score = float(parsed_score)
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
        "score": _charxiv_primary_score(scores),
        "scores": scores,
        "judge": {"temperature": 0.0, "top_p": 1.0, "max_tokens": args.judge_max_tokens, "thinking": "disabled via chat template enable_thinking=False when supported"},
        "artifacts": {"prediction_table": str(pred_table), "judge_jsonl": str(judge_jsonl), "judged_xlsx": str(judged_xlsx)},
    }
    write_json(output_dir / "scores.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=json_default))
    return summary


def _run_evochart_local_score(
    spec: BenchmarkSpec,
    model_path: str,
    output_dir: Path,
) -> dict[str, Any]:
    _import_vlmeval_runner()
    from vlmeval.smp import get_intermediate_file_path

    pred_table = output_dir / f"{spec.alias}_predictions.xlsx"
    if not pred_table.exists():
        raise FileNotFoundError(pred_table)
    dataset = build_vlmeval_dataset(spec)
    result = dataset.evaluate(str(pred_table))
    rows = json.loads(result.to_json(orient="records"))
    overall_rows = [row for row in rows if row.get("split") == "Overall"]
    if len(overall_rows) != 1:
        raise RuntimeError(f"EvoChart scorer returned no unique Overall row: {rows}")
    overall = float(overall_rows[0]["acc"])
    judged_xlsx = Path(get_intermediate_file_path(str(pred_table), "_results"))
    score_csv = Path(get_intermediate_file_path(str(pred_table), "_acc", "csv"))
    summary = {
        "dataset": spec.alias,
        "model": model_path,
        "run_name": spec.run_name,
        "harness": "Local deterministic EvoChart extension scorer",
        "rows": int(overall_rows[0]["tot"]),
        "score": overall,
        "scores": {"Overall": overall, "table": rows},
        "artifacts": {
            "prediction_table": str(pred_table),
            "judged_table": str(judged_xlsx),
            "score_csv": str(score_csv),
        },
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
    _import_vlmeval_runner()
    from vlmeval.dataset.chartmuseum import COMPARE_ANSWER_PROMPT, extract_answer
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
    benchmark = build_vlmeval_dataset(spec).data.reset_index(drop=True)
    data = data.reset_index(drop=True)
    if len(data) != len(benchmark):
        raise RuntimeError(
            f"ChartMuseum prediction/source row mismatch: predictions={len(data)} source={len(benchmark)}"
        )
    rows = []
    for position, prediction_row in data.iterrows():
        item = prediction_row.to_dict()
        source_row = benchmark.iloc[position]
        item["question"] = source_row["question"]
        item["answer"] = str(source_row["answer"])
        item["category"] = str(source_row["category"])
        rows.append(item)
    rows.sort(key=lambda x: str(x["index"]))
    judge_path = output_dir / "judge_qwen32b.jsonl"
    print(f"[chartmuseum judge] rows={len(rows)}")

    prompts = [
        (
            str(item["index"]),
            COMPARE_ANSWER_PROMPT.replace(
                "[QUESTION]", str(item.get("question", ""))
            ).replace(
                "[ANSWER1]", str(item.get("answer", ""))
            ).replace(
                "[ANSWER2]", extract_answer(str(item.get("prediction", "")))
            )
        )
        for item in rows
    ]
    judged_map = judge.run_cached(
        output_dir=output_dir,
        prompts=prompts,
        cache_name="judge_qwen32b.jsonl",
        max_tokens=128,
        temperature=0.0,
        top_p=1.0,
        no_resume=args.no_resume,
        desc="ChartMuseum judge",
        output_validator=_nonempty_judge_output,
        contract_version=DIRECT_JUDGE_CACHE_CONTRACTS["chartmuseum_judge"],
    )

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

    overall = sum(float(x["score"]) for x in judged_rows) / len(judged_rows) * 100.0
    breakdown_counts: dict[str, list[float]] = defaultdict(list)
    for row in judged_rows:
        breakdown_counts[str(row.get("category") or "unknown")].append(float(row["score"]))
    breakdown = {k: sum(v) / len(v) * 100.0 for k, v in sorted(breakdown_counts.items())}
    result_df = pd.DataFrame(judged_rows)
    result_df.to_json(output_dir / "judged_predictions.json", orient="records", force_ascii=False, indent=2)
    result_df.to_excel(output_dir / "judged_predictions.xlsx", index=False)
    summary = {
        "dataset": spec.alias,
        "model": model_path,
        "run_name": spec.run_name,
        "harness": "Pinned VLMEvalKit ChartMuseum prompt, extractor, parser, and category aggregation",
        "rows": len(judged_rows),
        "score": overall,
        "scores": {"Overall": overall, **breakdown},
        "judge_model": args.judge_model,
        "artifacts": {
            "prediction_table": str(pred_table),
            "judge_jsonl": str(judge_path),
            "judged_predictions_json": str(output_dir / "judged_predictions.json"),
            "judged_predictions_xlsx": str(output_dir / "judged_predictions.xlsx"),
        },
    }
    write_json(output_dir / "scores.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=json_default))
    return summary


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
            "extractor": "Trace ChartQAPro answer-is extractor",
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
    elif spec.key == "evochart":
        summary = _run_evochart_local_score(spec, model_path, output_dir)
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
    archive_paths = _archive_direct_score_slices(
        args,
        spec,
        model_path,
        model_slug,
        output_dir,
        summary,
    )
    if any(archive_paths):
        summary["archive_descriptors"] = [str(path) for path in archive_paths if path is not None]
        write_json(output_dir / "scores.json", summary)
        shutil.copy2(output_dir / "scores.json", dst)
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
        help="Use the fixed 37-benchmark Trace-aligned 200-row candidate suite.",
    )
    parser.add_argument("--gpu", default=os.environ.get("CUDA_VISIBLE_DEVICES", ""))
    parser.add_argument("--worker-id", default=f"score-{os.getpid()}")
    parser.add_argument("--queue-name", default="")
    parser.add_argument("--seed", type=int, default=int(os.environ.get("TRACE_FINAL25_SEED", "42")))
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
    parser.add_argument(
        "--judge-api-batch-size",
        type=int,
        default=1,
        help="Prompts per /completions request; one preserves the historical request shape.",
    )
    parser.add_argument("--judge-api-batches-per-endpoint", type=int, default=1)
    parser.add_argument("--judge-api-max-batch-chars", type=int, default=100_000)
    parser.add_argument("--judge-api-endpoint-failure-threshold", type=int, default=3)
    parser.add_argument("--judge-api-endpoint-cooldown-seconds", type=float, default=30.0)
    parser.add_argument("--judge-api-timeout", type=float, default=120.0)
    parser.add_argument("--judge-api-max-retries", type=int, default=5)
    parser.add_argument("--judge-cache-contract-version", default=PERSISTENT_JUDGE_CACHE_CONTRACT_VERSION)
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
