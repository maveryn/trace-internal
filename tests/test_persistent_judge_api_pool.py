from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import mock


SCRIPTS_ROOT = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import run_external_benchmark_score_queue as score_queue  # noqa: E402


class _JSONLRunner:
    @staticmethod
    def load_jsonl_by_index(path: Path):
        rows = {}
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    row = json.loads(line)
                    rows[str(row["index"])] = row
        return rows

    @staticmethod
    def append_jsonl(path: Path, rows):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, sort_keys=True) + "\n")


class _CompletionServer:
    def __init__(self, callback):
        self.callback = callback
        self.requests = []
        self._lock = threading.Lock()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length))
                with owner._lock:
                    call_number = len(owner.requests)
                    owner.requests.append(payload)
                status, body = owner.callback(payload, call_number)
                encoded = json.dumps(body).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def log_message(self, *_args):
                return

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_port}/v1"

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def _prompts_from_payload(payload):
    prompt = payload["prompt"]
    return prompt if isinstance(prompt, list) else [prompt]


def _args(endpoints, **overrides):
    values = {
        "judge_api_bases": list(endpoints),
        "judge_api_model": "synthetic-judge",
        "judge_api_batch_size": 2,
        "judge_api_batches_per_endpoint": 1,
        "judge_api_max_batch_chars": 100_000,
        "judge_api_parallelism": 128,
        "judge_api_endpoint_failure_threshold": 3,
        "judge_api_endpoint_cooldown_seconds": 30.0,
        "judge_api_timeout": 5.0,
        "judge_api_max_retries": 3,
        "judge_api_retry_base_delay": 0.0,
        "judge_model": "synthetic-judge",
        "judge_max_tokens": 32,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class PersistentJudgeAPIPoolTests(unittest.TestCase):
    def _run_cached(self, judge, output_dir, prompts, **kwargs):
        judge.api_chat_prompt = lambda prompt, **_kwargs: prompt
        with mock.patch.object(score_queue, "_import_vlmeval_runner", return_value=(_JSONLRunner, None)):
            return judge.run_cached(
                output_dir=output_dir,
                prompts=prompts,
                cache_name="judge.jsonl",
                max_tokens=32,
                desc="synthetic judge",
                **kwargs,
            )

    def test_batches_map_out_of_order_choices_and_invalidate_changed_prompt(self):
        def callback(payload, _call_number):
            prompts = _prompts_from_payload(payload)
            choices = [
                {
                    "index": index,
                    "text": f"answer:{prompts[index]}",
                    "finish_reason": "stop",
                    "completion_tokens": index + 1,
                }
                for index in reversed(range(len(prompts)))
            ]
            return 200, {"choices": choices, "usage": {"completion_tokens": len(prompts) * 3}}

        server = _CompletionServer(callback)
        self.addCleanup(server.close)
        judge = score_queue.PersistentJudge(_args([server.base_url]))
        self.addCleanup(judge.cleanup)
        prompts = [(str(index), f"prompt-{index}") for index in range(5)]

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            first = self._run_cached(judge, output_dir, prompts)
            self.assertEqual(sorted(len(_prompts_from_payload(item)) for item in server.requests), [1, 2, 2])
            self.assertTrue(any(isinstance(item["prompt"], str) for item in server.requests))
            self.assertTrue(any(isinstance(item["prompt"], list) for item in server.requests))
            for index, prompt in prompts:
                row = first[index]
                self.assertEqual(row["judge_output"], f"answer:{prompt}")
                self.assertEqual(row["judge_finish_reason"], "stop")
                self.assertIsInstance(row["judge_api_batch_usage"]["completion_tokens"], int)
                self.assertIn(row["judge_output_token_count"], {1, 2})
                self.assertEqual(row["contract_version"], score_queue.PERSISTENT_JUDGE_CACHE_CONTRACT_VERSION)
                self.assertEqual(len(row["request_hash"]), 64)

            call_count = len(server.requests)
            resumed = self._run_cached(judge, output_dir, prompts)
            self.assertEqual(len(server.requests), call_count)
            self.assertEqual(resumed["4"]["judge_output"], "answer:prompt-4")

            changed = list(prompts)
            changed[0] = ("0", "changed-prompt")
            refreshed = self._run_cached(judge, output_dir, changed)
            self.assertEqual(len(server.requests), call_count + 1)
            self.assertEqual(refreshed["0"]["judge_output"], "answer:changed-prompt")
            self.assertNotEqual(first["0"]["request_hash"], refreshed["0"]["request_hash"])

    def test_malformed_choice_indices_fail_over_and_quarantine_endpoint(self):
        def bad_callback(payload, _call_number):
            prompts = _prompts_from_payload(payload)
            choices = [
                {"index": 0, "text": f"bad:{prompt}", "finish_reason": "stop"}
                for prompt in prompts
            ]
            return 200, {"choices": choices, "usage": {"completion_tokens": len(prompts)}}

        def good_callback(payload, _call_number):
            prompts = _prompts_from_payload(payload)
            return 200, {
                "choices": [
                    {"index": index, "text": f"good:{prompt}", "finish_reason": "stop"}
                    for index, prompt in enumerate(prompts)
                ],
                "usage": {"completion_tokens": len(prompts)},
            }

        bad = _CompletionServer(bad_callback)
        good = _CompletionServer(good_callback)
        self.addCleanup(bad.close)
        self.addCleanup(good.close)
        judge = score_queue.PersistentJudge(
            _args([bad.base_url, good.base_url], judge_api_endpoint_failure_threshold=1)
        )
        self.addCleanup(judge.cleanup)

        with tempfile.TemporaryDirectory() as tmp:
            rows = self._run_cached(judge, Path(tmp), [("a", "one"), ("b", "two")])

        self.assertEqual(rows["a"]["judge_output"], "good:one")
        self.assertEqual(rows["b"]["judge_output"], "good:two")
        self.assertEqual(rows["a"]["judge_api_endpoint"], good.base_url)
        self.assertEqual(len(bad.requests), 1)
        self.assertEqual(len(good.requests), 1)
        self.assertEqual(judge._get_endpoint_health().snapshot()["disabled_endpoints"], [bad.base_url])

    def test_incomplete_and_parse_invalid_rows_retry_individually(self):
        def callback(payload, call_number):
            prompts = _prompts_from_payload(payload)
            self.assertEqual(prompts, ["binary decision"])
            if call_number == 0:
                text, finish_reason = "", "length"
            elif call_number == 1:
                text, finish_reason = "Maybe", "stop"
            else:
                text, finish_reason = "Yes", "stop"
            return 200, {
                "choices": [{"index": 0, "text": text, "finish_reason": finish_reason}],
                "usage": {"completion_tokens": call_number + 1},
            }

        server = _CompletionServer(callback)
        self.addCleanup(server.close)
        judge = score_queue.PersistentJudge(_args([server.base_url], judge_api_batch_size=8))
        self.addCleanup(judge.cleanup)

        with tempfile.TemporaryDirectory() as tmp:
            rows = self._run_cached(
                judge,
                Path(tmp),
                [("row", "binary decision")],
                output_validator=lambda output: output in {"Yes", "No"},
            )

        self.assertEqual(rows["row"]["judge_output"], "Yes")
        self.assertEqual(rows["row"]["judge_retry_count"], 2)
        self.assertEqual(rows["row"]["judge_retry_reason"], "parse_invalid")
        self.assertEqual(rows["row"]["judge_max_tokens_used"], 512)
        self.assertEqual([item["max_tokens"] for item in server.requests], [128, 256, 512])

    def test_nonempty_length_output_can_follow_official_extraction_semantics(self):
        def callback(payload, _call_number):
            self.assertEqual(_prompts_from_payload(payload), ["extract an answer"])
            return 200, {
                "choices": [{"index": 0, "text": "E", "finish_reason": "length"}],
                "usage": {"completion_tokens": 1},
            }

        server = _CompletionServer(callback)
        self.addCleanup(server.close)
        judge = score_queue.PersistentJudge(_args([server.base_url]))
        self.addCleanup(judge.cleanup)

        with tempfile.TemporaryDirectory() as tmp:
            rows = self._run_cached(
                judge,
                Path(tmp),
                [("row", "extract an answer")],
                output_validator=lambda output: bool(output.strip()),
                retry_on_length=False,
            )

        self.assertEqual(rows["row"]["judge_output"], "E")
        self.assertEqual(rows["row"]["judge_finish_reason"], "length")
        self.assertEqual(rows["row"]["judge_retry_count"], 0)
        self.assertEqual(rows["row"]["judge_max_tokens_used"], 128)
        self.assertEqual([item["max_tokens"] for item in server.requests], [128])

    def test_parse_invalid_cached_output_is_recomputed_under_route_contract(self):
        def callback(payload, call_number):
            prompts = _prompts_from_payload(payload)
            return 200, {
                "choices": [
                    {
                        "index": index,
                        "text": "Maybe" if call_number == 0 else "Yes",
                        "finish_reason": "stop",
                    }
                    for index in range(len(prompts))
                ],
                "usage": {"completion_tokens": len(prompts)},
            }

        server = _CompletionServer(callback)
        self.addCleanup(server.close)
        judge = score_queue.PersistentJudge(_args([server.base_url], judge_api_batch_size=1))
        self.addCleanup(judge.cleanup)
        contract = score_queue.DIRECT_JUDGE_CACHE_CONTRACTS["chartmuseum_judge"]

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            first = self._run_cached(
                judge,
                output_dir,
                [("row", "binary decision")],
                contract_version=contract,
            )
            self.assertEqual(first["row"]["judge_output"], "Maybe")
            second = self._run_cached(
                judge,
                output_dir,
                [("row", "binary decision")],
                output_validator=lambda output: output in {"Yes", "No"},
                contract_version=contract,
            )

        self.assertEqual(second["row"]["judge_output"], "Yes")
        self.assertEqual(len(server.requests), 2)

    def test_local_cache_uses_index_aware_validator_before_reuse(self):
        class FakeSamplingParams:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        class FakeLLM:
            def __init__(self):
                self.calls = 0

            def generate(self, prompts, **_kwargs):
                self.calls += 1
                text = "B" if self.calls == 1 else '{"answer":"B"}'
                return [
                    SimpleNamespace(
                        outputs=[
                            SimpleNamespace(
                                text=text,
                                finish_reason="stop",
                                token_ids=[1],
                            )
                        ]
                    )
                    for _ in prompts
                ]

        module = ModuleType("vllm")
        module.SamplingParams = FakeSamplingParams
        args = SimpleNamespace(
            gpu="",
            attention_backend="FLASH_ATTN",
            judge_model="synthetic-judge",
            judge_batch_size=8,
            judge_max_tokens=32,
        )
        judge = score_queue.PersistentJudge(args)
        judge.llm = FakeLLM()
        judge.tokenizer = object()
        judge.chat_prompt = lambda prompt, **_kwargs: prompt

        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            sys.modules, {"vllm": module}
        ), mock.patch.object(
            score_queue, "_import_vlmeval_runner", return_value=(_JSONLRunner, None)
        ):
            first = judge.run_cached(
                output_dir=Path(tmp),
                prompts=[("row", "extract")],
                cache_name="local.jsonl",
                max_tokens=32,
            )
            self.assertEqual(first["row"]["judge_output"], "B")

            second = judge.run_cached(
                output_dir=Path(tmp),
                prompts=[("row", "extract")],
                cache_name="local.jsonl",
                max_tokens=32,
                output_validator_by_index=lambda index, output: (
                    index == "row" and output == '{"answer":"B"}'
                ),
            )

        self.assertEqual(second["row"]["judge_output"], '{"answer":"B"}')
        self.assertEqual(judge.llm.calls, 2)

    def test_all_quarantined_pool_recovers_via_half_open_probe(self):
        def callback(payload, call_number):
            prompts = _prompts_from_payload(payload)
            if call_number == 0:
                return 500, {"error": "temporary"}
            return 200, {
                "choices": [
                    {"index": index, "text": "Yes", "finish_reason": "stop"}
                    for index in range(len(prompts))
                ],
                "usage": {"completion_tokens": len(prompts)},
            }

        server = _CompletionServer(callback)
        self.addCleanup(server.close)
        judge = score_queue.PersistentJudge(
            _args(
                [server.base_url],
                judge_api_endpoint_failure_threshold=1,
                judge_api_endpoint_cooldown_seconds=0.0,
            )
        )
        self.addCleanup(judge.cleanup)

        with tempfile.TemporaryDirectory() as tmp:
            rows = self._run_cached(
                judge,
                Path(tmp),
                [("row", "binary decision")],
                output_validator=lambda output: output in {"Yes", "No"},
            )

        self.assertEqual(rows["row"]["judge_output"], "Yes")
        self.assertEqual(len(server.requests), 2)
        health = judge._get_endpoint_health().snapshot()
        self.assertEqual(health["disabled_endpoints"], [])
        self.assertEqual(health["consecutive_failures"][server.base_url], 0)

    def test_endpoint_health_reserves_one_probe_after_cooldown(self):
        now = [100.0]
        health = score_queue._JudgeEndpointHealth(
            ["endpoint"],
            1,
            cooldown_seconds=10.0,
            clock=lambda: now[0],
        )
        self.assertEqual(health.acquire(0, set()), "endpoint")
        self.assertTrue(health.record_failure("endpoint"))
        self.assertIsNone(health.acquire(0, set()))

        now[0] = 110.0
        self.assertEqual(health.acquire(0, set()), "endpoint")
        self.assertIsNone(health.acquire(0, set()))
        self.assertEqual(health.snapshot()["half_open_endpoints"], ["endpoint"])

        health.record_success("endpoint")
        self.assertEqual(health.acquire(0, set()), "endpoint")

    def test_direct_route_contracts_are_distinct_and_validators_are_strict(self):
        contracts = score_queue.DIRECT_JUDGE_CACHE_CONTRACTS
        self.assertEqual(len(contracts), len(set(contracts.values())))

        score_validator, score_contract = score_queue._math_like_judge_cache_policy(
            "mathverse", "mathverse_qwen3_32b_score.jsonl"
        )
        logic_validator, logic_contract = score_queue._math_like_judge_cache_policy(
            "logicvista", "logicvista_qwen3_32b_extract.jsonl"
        )
        self.assertNotEqual(score_contract, logic_contract)
        self.assertTrue(score_validator("1"))
        self.assertTrue(score_validator("Judgement: 0"))
        self.assertTrue(score_validator("**Judgement: 1**"))
        self.assertTrue(score_validator("Judgement: **1**\nReason\n**Judgement: 1**"))
        self.assertFalse(score_validator("Judgement: 1\nReason\nJudgement: 0"))
        self.assertFalse(score_validator("The answers match. Judgement: 1"))
        self.assertFalse(score_validator("Maybe"))
        self.assertTrue(logic_validator("A, C"))
        self.assertFalse(logic_validator("The answer may be A"))
        self.assertIsNotNone(score_queue._parse_charxiv_score_output('{"score": 0.5}'))
        self.assertIsNone(score_queue._parse_charxiv_score_output("unparseable"))
        self.assertTrue(score_queue._valid_evochart_judge_output('{"score": 1}'))
        self.assertFalse(score_queue._valid_evochart_judge_output("unparseable"))

    def test_local_judge_retries_parse_invalid_output_before_caching(self):
        class FakeLLM:
            def __init__(self):
                self.calls = 0

            def generate(self, prompts, sampling_params, use_tqdm):
                del prompts, sampling_params, use_tqdm
                text = "Maybe" if self.calls == 0 else "Yes"
                self.calls += 1
                completion = SimpleNamespace(
                    text=text,
                    finish_reason="stop",
                    token_ids=[1],
                )
                return [SimpleNamespace(outputs=[completion])]

        vllm = ModuleType("vllm")
        vllm.SamplingParams = lambda **kwargs: SimpleNamespace(**kwargs)
        judge = score_queue.PersistentJudge(
            SimpleNamespace(
                judge_api_bases=[],
                judge_model="synthetic-judge",
                judge_batch_size=1,
                judge_max_tokens=32,
            )
        )
        judge.llm = FakeLLM()
        judge.chat_prompt = lambda prompt, **_kwargs: prompt

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(sys.modules, {"vllm": vllm}), mock.patch.object(
                score_queue, "_import_vlmeval_runner", return_value=(_JSONLRunner, None)
            ):
                rows = judge.run_cached(
                    output_dir=Path(tmp),
                    prompts=[("row", "binary decision")],
                    cache_name="judge.jsonl",
                    max_tokens=32,
                    desc="synthetic local judge",
                    output_validator=lambda output: output in {"Yes", "No"},
                )

        self.assertEqual(judge.llm.calls, 2)
        self.assertEqual(rows["row"]["judge_output"], "Yes")
        self.assertEqual(rows["row"]["judge_retry_count"], 1)
        self.assertEqual(rows["row"]["judge_max_tokens_used"], 256)

    def test_legacy_cache_entry_without_request_hash_is_recomputed(self):
        def callback(payload, _call_number):
            prompts = _prompts_from_payload(payload)
            return 200, {
                "choices": [{"index": 0, "text": "fresh", "finish_reason": "stop"}],
                "usage": {"completion_tokens": len(prompts)},
            }

        server = _CompletionServer(callback)
        self.addCleanup(server.close)
        judge = score_queue.PersistentJudge(_args([server.base_url], judge_api_batch_size=1))
        self.addCleanup(judge.cleanup)

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            (output_dir / "judge.jsonl").write_text(
                json.dumps({"index": "row", "judge_output": "stale", "judge_finish_reason": "stop"}) + "\n",
                encoding="utf-8",
            )
            rows = self._run_cached(judge, output_dir, [("row", "prompt")])

        self.assertEqual(len(server.requests), 1)
        self.assertEqual(rows["row"]["judge_output"], "fresh")

    def test_programmatic_namespace_uses_scalar_compatibility_defaults(self):
        def callback(payload, _call_number):
            self.assertIsInstance(payload["prompt"], str)
            return 200, {
                "choices": [{"index": 0, "text": f"ok:{payload['prompt']}", "finish_reason": "stop"}],
                "usage": {"completion_tokens": 1},
            }

        server = _CompletionServer(callback)
        self.addCleanup(server.close)
        judge = score_queue.PersistentJudge(SimpleNamespace(judge_api_bases=[server.base_url]))
        self.addCleanup(judge.cleanup)

        with tempfile.TemporaryDirectory() as tmp:
            rows = self._run_cached(judge, Path(tmp), [("a", "one"), ("b", "two")])

        self.assertEqual(rows["a"]["judge_output"], "ok:one")
        self.assertEqual(rows["b"]["judge_output"], "ok:two")
        self.assertEqual(len(server.requests), 2)


if __name__ == "__main__":
    unittest.main()
