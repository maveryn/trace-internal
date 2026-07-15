from __future__ import annotations

import argparse
import base64
import io
import json
import queue
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

from scripts import run_external_benchmark_generation_api_queue as runner
from scripts.benchmark_queue_lib import BenchmarkSpec


def _args(**overrides):
    values = {
        "api_model": "test-model",
        "api_key": "EMPTY",
        "api_timeout": 1.0,
        "api_max_retries": 4,
        "temperature": 0.0,
        "top_p": 1.0,
        "top_k": -1,
        "max_tokens": 32,
        "presence_penalty": 0.0,
        "repetition_penalty": 1.0,
        "seed": 42,
        "image_jpeg_quality": 85,
        "max_image_pixels": 1_000_000,
        "max_image_side": 1280,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class _Response:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


class _Progress:
    def __init__(self):
        self.count = 0

    def update(self, value: int):
        self.count += value


class ExternalBenchmarkGenerationAPIQueueTests(unittest.TestCase):
    def test_image_data_url_enforces_pixel_and_side_caps(self):
        image = Image.new("RGB", (2400, 1600), "white")

        data_url = runner._image_to_data_url(image, max_pixels=1_000_000, max_side=1280)
        encoded = data_url.split(",", 1)[1]
        resized = Image.open(io.BytesIO(base64.b64decode(encoded)))

        self.assertLessEqual(resized.width * resized.height, 1_000_000)
        self.assertLessEqual(max(resized.size), 1280)

    def test_permanent_http_error_includes_response_body_without_internal_retry(self):
        calls = []

        def fake_post(*args, **kwargs):
            calls.append((args, kwargs))
            return _Response(400, text='{"message":"prompt is too long"}')

        with patch.object(runner.requests, "post", side_effect=fake_post):
            with self.assertRaisesRegex(runner.PermanentAPIError, "prompt is too long"):
                runner._call_endpoint(_args(), "http://endpoint-a/v1", [{"role": "user", "content": []}])

        self.assertEqual(len(calls), 1)

    def test_retryable_endpoint_failure_fails_over_and_mirrors_exact_result(self):
        endpoint_a = "http://endpoint-a/v1"
        endpoint_b = "http://endpoint-b/v1"
        first_failure = threading.Event()

        def fake_call(args, endpoint, messages):
            if endpoint == endpoint_a:
                first_failure.set()
                raise runner.RetryableAPIError(endpoint, "engine input thread stopped")
            return {
                "choices": [{"message": {"content": "saved response"}, "finish_reason": "stop"}],
                "usage": {"completion_tokens": 2, "prompt_tokens": 7},
            }

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            spec = BenchmarkSpec("demo", "Demo", "Demo", "demo")
            primary = tmp_path / "tmpfs" / "row.json"
            mirror = tmp_path / "persistent" / "row.json"
            job = runner.RowJob(
                spec=spec,
                row={"index": "row-1", "question": "Question?"},
                rank=0,
                row_key="00000000:row-1:hash",
                output_dir=primary.parent,
                result_path=primary,
                mirror_result_path=mirror,
                kind="chartmuseum",
            )
            jobs: queue.Queue[runner.RowJob] = queue.Queue()
            jobs.put(job)
            errors = []
            progress = _Progress()
            health = runner.EndpointHealth([endpoint_a, endpoint_b], failure_threshold=1)
            stop_event = threading.Event()
            common = {
                "args": _args(),
                "handles": {spec.key: runner.DatasetHandle(spec=spec, rows=[job.row])},
                "jobs": jobs,
                "errors": errors,
                "error_lock": threading.Lock(),
                "progress": progress,
                "endpoint_health": health,
                "stop_event": stop_event,
            }

            with patch.object(runner, "_call_endpoint", side_effect=fake_call):
                worker_a = threading.Thread(target=runner._worker_loop, kwargs={**common, "endpoint": endpoint_a})
                worker_a.start()
                self.assertTrue(first_failure.wait(timeout=2))
                worker_b = threading.Thread(target=runner._worker_loop, kwargs={**common, "endpoint": endpoint_b})
                worker_b.start()
                jobs.join()
                stop_event.set()
                worker_a.join(timeout=2)
                worker_b.join(timeout=2)

            self.assertEqual(errors, [])
            self.assertEqual(progress.count, 1)
            self.assertEqual(primary.read_bytes(), mirror.read_bytes())
            result = json.loads(primary.read_text(encoding="utf-8"))
            self.assertEqual(result["prediction"], "saved response")
            self.assertEqual(result["api_endpoint"], endpoint_b)
            self.assertEqual(health.snapshot()["disabled_endpoints"], [endpoint_a])

    def test_restore_mirror_only_fills_missing_canonical_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            canonical = tmp_path / "canonical"
            mirror = tmp_path / "mirror"
            canonical.mkdir()
            mirror.mkdir()
            (canonical / "existing.json").write_text('{"source":"canonical"}\n', encoding="utf-8")
            (mirror / "existing.json").write_text('{"source":"mirror"}\n', encoding="utf-8")
            (mirror / "missing.json").write_text('{"source":"mirror"}\n', encoding="utf-8")

            runner._restore_mirrored_row_results(canonical, mirror)

            existing = json.loads((canonical / "existing.json").read_text(encoding="utf-8"))
            missing = json.loads((canonical / "missing.json").read_text(encoding="utf-8"))
            self.assertEqual(existing["source"], "canonical")
            self.assertEqual(missing["source"], "mirror")

    def test_finalize_uses_requested_alias_for_prediction_workbook(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_root = Path(tmp)
            spec = BenchmarkSpec("demo_video", "Demo video", "Demo_Video_8frame", "demo")
            row = {"index": "sample-1", "question": "What happens?", "answer": "A"}
            dataset = SimpleNamespace(dataset_name="Demo_Video", data=runner.pd.DataFrame([row]))
            handle = runner.DatasetHandle(spec=spec, dataset=dataset)
            output_dir = runner.run_dir(spec, "model", run_root)
            row_result_dir = output_dir / "api_row_results"
            row_result_dir.mkdir(parents=True)
            runner._atomic_write_json(
                row_result_dir / runner._safe_result_name_for_row(row, 0),
                {
                    "index": "sample-1",
                    "row_key": runner._row_key(row, 0),
                    "prediction": "A",
                    "finish_reason": "stop",
                    "output_token_count": 1,
                    "prompt_token_count": 4,
                },
            )
            args = SimpleNamespace(
                run_root=run_root,
                model="test-model",
                model_slug="model",
                temperature=0.0,
                top_p=1.0,
                top_k=-1,
                presence_penalty=0.0,
                repetition_penalty=1.0,
                max_tokens=32,
                seed=42,
                api_model="test-model",
                api_bases=["http://endpoint/v1"],
                parallelism_per_endpoint=1,
                max_image_pixels=1_000_000,
                max_image_side=1280,
                image_jpeg_quality=85,
                subset_root=None,
            )

            with patch.object(runner, "_import_vlmeval_runner", return_value=(object(), object())):
                summary = runner._finalize_spec(args, handle)

            expected = output_dir / "Demo_Video_8frame_predictions.xlsx"
            self.assertTrue(expected.exists())
            self.assertFalse((output_dir / "Demo_Video_predictions.xlsx").exists())
            self.assertEqual(summary["artifacts"]["eval_file"], str(expected))


if __name__ == "__main__":
    unittest.main()
