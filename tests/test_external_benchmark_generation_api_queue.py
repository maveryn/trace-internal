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
from unittest.mock import Mock, patch

from PIL import Image

from scripts import run_external_benchmark_generation_api_queue as runner
from scripts.benchmark_queue_lib import BenchmarkSpec


def _args(**overrides):
    values = {
        "api_model": "test-model",
        "model": "test-model",
        "model_slug": "model",
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
        "min_image_pixels": runner.QWEN_MIN_IMAGE_PIXELS,
        "media_transport": "data-url",
        "allowed_local_media_path": None,
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
    def test_subset_hash_ignores_internal_source_ordinal_and_preserves_it(self):
        frame = runner.pd.DataFrame(
            [
                {"index": "duplicate", "question": "first"},
                {"index": "duplicate", "question": "second"},
            ]
        )
        selected_hash = runner._row_hash(frame.iloc[1])
        frame[runner.SOURCE_ORDINAL_COLUMN] = [0, 1]

        selected = runner._apply_subset_frame(
            frame,
            [{"source_index": "duplicate", "sample_rank": 0, "row_hash": selected_hash}],
        )

        self.assertEqual(selected.iloc[0][runner.SOURCE_ORDINAL_COLUMN], 1)
        self.assertEqual(runner._row_hash(selected.iloc[0]), selected_hash)

    def test_result_preserves_original_source_ordinal(self):
        row = {"index": "row", "question": "question"}
        job = runner.RowJob(
            spec=BenchmarkSpec("demo", "Demo", "Demo", "demo"),
            row=row,
            rank=0,
            row_key=runner._row_key(row, 0),
            output_dir=Path("/tmp"),
            result_path=Path("/tmp/result.json"),
            kind="vlmeval",
            source_ordinal=17,
        )
        result = runner._result_from_response(
            job,
            {"choices": [{"message": {"content": "A"}}]},
            "http://endpoint",
        )

        self.assertEqual(result["source_ordinal"], 17)

    def test_parser_resolves_transport_specific_pixel_defaults(self):
        required = ["--model", "model", "--model-slug", "slug", "--api-model", "slug"]
        file_args = runner.build_parser().parse_args(
            [*required, "--media-transport", "file-url", "--allowed-local-media-path", "/tmp"]
        )
        legacy_args = runner.build_parser().parse_args(required)

        runner._resolve_image_pixel_defaults(file_args)
        runner._resolve_image_pixel_defaults(legacy_args)

        self.assertEqual(file_args.max_image_pixels, runner.QWEN_MAX_IMAGE_PIXELS)
        self.assertGreaterEqual(file_args.max_image_pixels, file_args.min_image_pixels)
        self.assertEqual(legacy_args.max_image_pixels, 1_000_000)

    def test_generation_contract_distinguishes_full_limit_and_subset_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            subset_root = Path(tmp)
            manifest = subset_root / "demo.jsonl"
            manifest.write_text('{"source_index":"1"}\n', encoding="utf-8")
            full_args = _args(subset_root=None, limit=None, sample_seed=0)
            limit_args = _args(subset_root=None, limit=2, sample_seed=7)
            subset_args = _args(subset_root=subset_root, limit=None, sample_seed=0)

            self.assertEqual(runner._selection_contract(full_args)["mode"], "full")
            self.assertEqual(runner._selection_contract(limit_args)["mode"], "limit")
            self.assertEqual(runner._selection_contract(subset_args)["mode"], "subset")
            self.assertEqual(
                len(
                    {
                        runner._generation_contract_hash(full_args),
                        runner._generation_contract_hash(limit_args),
                        runner._generation_contract_hash(subset_args),
                    }
                ),
                3,
            )

            manifest.write_text('{"source_index":"2"}\n', encoding="utf-8")
            changed_subset_args = _args(subset_root=subset_root, limit=None, sample_seed=0)
            self.assertNotEqual(
                runner._generation_contract_hash(subset_args),
                runner._generation_contract_hash(changed_subset_args),
            )

    def test_finalize_only_requires_no_endpoint_and_runs_cpu_finalization(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = BenchmarkSpec("demo", "Demo", "Demo", "demo")
            handle = runner.DatasetHandle(spec=spec, rows=[])
            args = _args(
                run_set="synthetic",
                run_root=root,
                only=[],
                exclude=[],
                exact_only=False,
                api_bases=[],
                endpoint_failure_threshold=2,
                parallelism_per_endpoint=1,
                preparation_workers=1,
                persistence_workers=1,
                finalization_workers=1,
                queue_capacity=1,
                media_cache_dir=None,
                finalize_only=True,
                defer_finalization=False,
                no_resume=False,
            )

            with (
                patch.object(runner, "benchmark_specs_for_run_set", return_value=[spec]),
                patch.object(runner, "filter_benchmark_specs", return_value=[spec]),
                patch.object(runner, "materialize_grounding_benchmark_files"),
                patch.object(runner, "_prepare_handles_and_jobs", return_value=({spec.key: handle}, [])),
                patch.object(runner, "_finalize_spec", return_value={"dataset": spec.alias}) as finalize,
            ):
                runner.run(args)

            finalize.assert_called_once_with(args, handle)
            summary = json.loads(
                (root / "model_api_generation_suite_summary.json").read_text(encoding="utf-8")
            )
            self.assertEqual(summary["mode"], "finalize_only")
            self.assertEqual(summary["error_count"], 0)

    def test_image_data_url_enforces_pixel_and_side_caps(self):
        image = Image.new("RGB", (2400, 1600), "white")

        data_url = runner._image_to_data_url(image, max_pixels=1_000_000, max_side=1280)
        encoded = data_url.split(",", 1)[1]
        resized = Image.open(io.BytesIO(base64.b64decode(encoded)))

        self.assertLessEqual(resized.width * resized.height, 1_000_000)
        self.assertLessEqual(max(resized.size), 1280)

    def test_final25_file_transport_preserves_source_and_sets_native_processor_bounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_path = root / "chart.png"
            Image.new("RGBA", (2400, 1600), (1, 2, 3, 127)).save(image_path)
            original = image_path.read_bytes()
            args = _args(
                media_transport=runner.MEDIA_TRANSPORT,
                allowed_local_media_path=root,
                min_image_pixels=runner.QWEN_MIN_IMAGE_PIXELS,
                max_image_pixels=runner.QWEN_MAX_IMAGE_PIXELS,
            )

            url = runner._image_transport_url(args, image_path)
            payload = runner._api_payload(
                args,
                [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": url}}]}],
            )

            self.assertEqual(url, image_path.resolve().as_uri())
            self.assertEqual(image_path.read_bytes(), original)
            self.assertEqual(
                payload["mm_processor_kwargs"],
                {
                    "min_pixels": 3_136,
                    "max_pixels": 12_845_056,
                },
            )

    def test_chartmuseum_api_uses_official_question_template_and_image_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_path = root / "chart.png"
            Image.new("RGB", (32, 24), "white").save(image_path)
            formatter = Mock(return_value="OFFICIAL CHARTMUSEUM PROMPT")
            chartmuseum = SimpleNamespace(format_question_prompt=formatter)
            args = _args(
                media_transport=runner.MEDIA_TRANSPORT,
                allowed_local_media_path=root,
            )

            with patch.object(
                runner,
                "_import_vlmeval_runner",
                return_value=(object(), chartmuseum),
            ):
                messages = runner._chartmuseum_messages(
                    args,
                    {"question": "What is the value?", "image_path": image_path},
                )

            formatter.assert_called_once_with("What is the value?")
            self.assertEqual(
                messages,
                [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": image_path.resolve().as_uri()},
                            },
                            {"type": "text", "text": "OFFICIAL CHARTMUSEUM PROMPT"},
                        ],
                    }
                ],
            )

    def test_screenspot_uses_vero_reasoning_prompt_with_original_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_path = root / "screen.png"
            Image.new("RGB", (960, 540), "white").save(image_path)

            class Dataset:
                def build_prompt(self, _row, video_llm):
                    del video_llm
                    return [
                        {"type": "image", "value": image_path},
                        {"type": "text", "value": "old VLMEvalKit prompt"},
                    ]

            handle = runner.DatasetHandle(
                spec=BenchmarkSpec("screenspot", "ScreenSpot", "ScreenSpot", "run"),
                dataset=Dataset(),
                rows=[],
            )
            args = _args(
                media_transport=runner.MEDIA_TRANSPORT,
                allowed_local_media_path=root,
            )
            with patch.object(runner, "_import_vlmeval_runner", return_value=(object(), object())):
                messages = runner._vlmeval_messages(
                    args,
                    handle,
                    {"question": "open settings", "image_path": str(image_path)},
                )

            self.assertEqual(messages[0]["role"], "system")
            self.assertEqual(messages[0]["content"][0]["text"], "You are a helpful assistant.")
            self.assertEqual(messages[1]["content"][0]["image_url"]["url"], image_path.as_uri())
            self.assertEqual(
                messages[1]["content"][1]["text"],
                "Provide the point for the command: open settings. "
                'Output the point in a JSON array format: [{"point_2d": [x, y]}].',
            )

    def test_manifest_lookup_uses_ordinal_for_duplicate_row_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = {"index": "same", "question": "same"}
            source_hash = runner._row_hash(row)
            media_rows = {}
            messages = []
            for ordinal, content in enumerate((b"first", b"other")):
                path = root / f"{ordinal}.png"
                path.write_bytes(content)
                sha = runner._sha256_file(path)
                media = [{"type": "image", "path": str(path), "size_bytes": len(content), "sha256": sha}]
                media_hash = runner.media_set_sha256(media)
                media_rows[(ordinal, row["index"], source_hash)] = {
                    "ordinal": ordinal,
                    "index": row["index"],
                    "source_row_hash": source_hash,
                    "media": media,
                    "media_set_sha256": media_hash,
                    "source_record_sha256": runner.source_record_sha256(source_hash, media_hash),
                }
                messages.append(
                    [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": path.as_uri()}}]}]
                )
            handle = runner.DatasetHandle(
                BenchmarkSpec("demo", "Demo", "Demo", "demo"),
                media_rows=media_rows,
                source_ordinals=[0, 1],
            )
            args = _args(media_transport="file-url", allowed_local_media_path=root)

            first = runner._media_provenance(args, handle, row, messages[0], 0)
            second = runner._media_provenance(args, handle, row, messages[1], 1)

            self.assertNotEqual(first["media_set_sha256"], second["media_set_sha256"])

    def test_permanent_http_error_includes_response_body_without_internal_retry(self):
        calls = []

        def fake_post(*args, **kwargs):
            calls.append((args, kwargs))
            return _Response(400, text='{"message":"prompt is too long"}')

        session = SimpleNamespace(post=fake_post)
        with patch.object(runner, "_http_session", return_value=session):
            with self.assertRaisesRegex(runner.PermanentAPIError, "prompt is too long"):
                runner._call_endpoint(_args(), "http://endpoint-a/v1", [{"role": "user", "content": []}])

        self.assertEqual(len(calls), 1)

    def test_endpoint_calls_reuse_thread_local_session(self):
        calls = []

        class FakeSession:
            def post(self, *args, **kwargs):
                calls.append((args, kwargs))
                return _Response(200, {"choices": [{"message": {"content": "ok"}}]})

            def close(self):
                calls.append(("close", {}))

        fake_session = FakeSession()
        runner._close_http_session()
        with patch.object(runner.requests, "Session", return_value=fake_session) as constructor:
            runner._call_endpoint(_args(), "http://endpoint-a/v1", [{"role": "user", "content": []}])
            runner._call_endpoint(_args(), "http://endpoint-a/v1", [{"role": "user", "content": []}])
            runner._close_http_session()

        constructor.assert_called_once_with()
        self.assertEqual(len([call for call in calls if call[0] != "close"]), 2)

    def test_media_cache_is_content_and_encoding_parameter_addressed(self):
        image = Image.new("RGB", (32, 24), "white")
        metrics = runner.PipelineMetrics()
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp)
            with patch.object(runner, "_encode_image_data_url", wraps=runner._encode_image_data_url) as encode:
                first = runner._image_to_data_url(image, quality=85, cache_dir=cache_dir, metrics=metrics)
                second = runner._image_to_data_url(image.copy(), quality=85, cache_dir=cache_dir, metrics=metrics)
                changed = runner._image_to_data_url(image, quality=90, cache_dir=cache_dir, metrics=metrics)

        self.assertEqual(first, second)
        self.assertNotEqual(first, changed)
        self.assertEqual(encode.call_count, 2)
        counters = metrics.snapshot()["counters"]
        self.assertEqual(counters["media_cache_hits"], 1)
        self.assertEqual(counters["media_cache_misses"], 2)

    def test_staged_pipeline_prepares_once_across_endpoint_failover(self):
        endpoint_a = "http://endpoint-a/v1"
        endpoint_b = "http://endpoint-b/v1"
        messages = [{"role": "user", "content": [{"type": "text", "text": "Question?"}]}]
        seen_message_ids = []

        def fake_call(args, endpoint, prepared_messages):
            seen_message_ids.append(id(prepared_messages))
            if endpoint == endpoint_a:
                raise runner.RetryableAPIError(endpoint, "temporary failure")
            return {
                "choices": [{"message": {"content": "B"}, "finish_reason": "stop"}],
                "usage": {"completion_tokens": 1, "prompt_tokens": 5},
            }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = BenchmarkSpec("demo", "Demo", "Demo", "demo")
            row = {"index": "row-1", "question": "Question?"}
            result_path = root / "row.json"
            job = runner.RowJob(
                spec=spec,
                row=row,
                rank=0,
                row_key=runner._row_key(row, 0),
                output_dir=root,
                result_path=result_path,
                kind="chartmuseum",
            )
            input_jobs = queue.Queue(maxsize=1)
            prepared_jobs = queue.Queue(maxsize=1)
            persistence_jobs = queue.Queue(maxsize=1)
            health = runner.EndpointHealth([endpoint_a, endpoint_b], failure_threshold=1)
            router = runner.EndpointRouter([endpoint_a, endpoint_b], 1, health)
            metrics = runner.PipelineMetrics()
            progress = _Progress()
            errors = []
            prep_stop = threading.Event()
            request_stop = threading.Event()
            persistence_stop = threading.Event()
            args = _args(api_max_retries=3)

            prep_thread = threading.Thread(
                target=runner._preparation_worker_loop,
                kwargs={
                    "args": args,
                    "handles": {spec.key: runner.DatasetHandle(spec=spec, rows=[row])},
                    "jobs": input_jobs,
                    "prepared_jobs": prepared_jobs,
                    "persistence_jobs": persistence_jobs,
                    "metrics": metrics,
                    "stop_event": prep_stop,
                },
            )
            request_thread = threading.Thread(
                target=runner._request_worker_loop,
                kwargs={
                    "args": args,
                    "prepared_jobs": prepared_jobs,
                    "persistence_jobs": persistence_jobs,
                    "endpoint_router": router,
                    "endpoint_health": health,
                    "metrics": metrics,
                    "stop_event": request_stop,
                },
            )
            persistence_thread = threading.Thread(
                target=runner._persistence_worker_loop,
                kwargs={
                    "jobs": persistence_jobs,
                    "errors": errors,
                    "error_lock": threading.Lock(),
                    "progress": progress,
                    "metrics": metrics,
                    "stop_event": persistence_stop,
                },
            )

            with (
                patch.object(runner, "_chartmuseum_messages", return_value=messages) as prepare,
                patch.object(runner, "_call_endpoint", side_effect=fake_call),
            ):
                persistence_thread.start()
                request_thread.start()
                prep_thread.start()
                input_jobs.put(job)
                input_jobs.join()
                prep_stop.set()
                prep_thread.join(timeout=2)
                prepared_jobs.join()
                request_stop.set()
                request_thread.join(timeout=2)
                persistence_jobs.join()
                persistence_stop.set()
                persistence_thread.join(timeout=2)

            prepare.assert_called_once()
            self.assertEqual(len(set(seen_message_ids)), 1)
            self.assertEqual(json.loads(result_path.read_text(encoding="utf-8"))["prediction"], "B")
            self.assertEqual(errors, [])
            self.assertEqual(progress.count, 1)
            snapshot = metrics.snapshot()
            self.assertEqual(snapshot["counters"]["request_retries"], 1)
            self.assertEqual(snapshot["counters"]["persisted_rows"], 1)
            self.assertEqual(health.snapshot()["disabled_endpoints"], [endpoint_a])

    def test_run_records_bounded_pipeline_metrics_with_synthetic_response(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = BenchmarkSpec("demo", "Demo", "Demo", "demo")
            row = {"index": "row-1", "question": "Question?"}
            output_dir = root / "demo"
            job = runner.RowJob(
                spec=spec,
                row=row,
                rank=0,
                row_key=runner._row_key(row, 0),
                output_dir=output_dir,
                result_path=output_dir / "api_row_results" / "row.json",
                kind="chartmuseum",
            )
            handle = runner.DatasetHandle(spec=spec, rows=[row])
            args = _args(
                run_set="synthetic",
                model="test-model",
                model_slug="model",
                run_root=root,
                only=[],
                exclude=[],
                exact_only=False,
                api_bases=["http://endpoint/v1"],
                endpoint_failure_threshold=2,
                parallelism_per_endpoint=1,
                preparation_workers=2,
                persistence_workers=2,
                finalization_workers=1,
                queue_capacity=1,
                media_cache_dir=None,
            )
            response = {
                "choices": [{"message": {"content": "A"}, "finish_reason": "stop"}],
                "usage": {"completion_tokens": 1, "prompt_tokens": 4},
            }

            with (
                patch.object(runner, "benchmark_specs_for_run_set", return_value=[spec]),
                patch.object(runner, "filter_benchmark_specs", return_value=[spec]),
                patch.object(runner, "materialize_grounding_benchmark_files"),
                patch.object(runner, "_prepare_handles_and_jobs", return_value=({spec.key: handle}, [job])),
                patch.object(runner, "_chartmuseum_messages", return_value=[{"role": "user", "content": []}]),
                patch.object(runner, "_call_endpoint", return_value=response),
                patch.object(runner, "_finalize_spec", return_value={"dataset": spec.alias}),
            ):
                runner.run(args)

            result = json.loads(job.result_path.read_text(encoding="utf-8"))
            self.assertEqual(result["prediction"], "A")
            self.assertEqual(len(result["request_hash"]), 64)
            summary = json.loads((root / "model_api_generation_suite_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["error_count"], 0)
            self.assertEqual(summary["pipeline_metrics"]["counters"]["request_successes"], 1)
            self.assertEqual(summary["pipeline_metrics"]["queue_high_watermarks"]["input"], 1)
            self.assertIn("preparation", summary["pipeline_metrics"]["stages"])
            self.assertIn("request", summary["pipeline_metrics"]["stages"])
            self.assertIn("persistence", summary["pipeline_metrics"]["stages"])
            self.assertIn("finalization", summary["pipeline_metrics"]["stages"])

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

            with (
                patch.object(
                    runner,
                    "_chartmuseum_messages",
                    return_value=[
                        {
                            "role": "user",
                            "content": [{"type": "text", "text": "official prompt"}],
                        }
                    ],
                ),
                patch.object(runner, "_call_endpoint", side_effect=fake_call),
            ):
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
            row = {
                "index": "sample-1",
                "question": "What happens?",
                "answer": "A",
                "image": "data:image/png;base64,duplicated-media",
                "image_size": "(640, 480)",
            }
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
                compact_prediction_tables=True,
            )

            with patch.object(runner, "_import_vlmeval_runner", return_value=(object(), object())):
                summary = runner._finalize_spec(args, handle)

            expected = output_dir / "Demo_Video_8frame_predictions.xlsx"
            self.assertTrue(expected.exists())
            self.assertFalse((output_dir / "Demo_Video_predictions.xlsx").exists())
            self.assertEqual(summary["artifacts"]["eval_file"], str(expected))
            self.assertEqual(summary["rows"], 1)
            persisted = runner.pd.read_excel(expected)
            self.assertNotIn("image", persisted.columns)
            self.assertIn("image_size", persisted.columns)
            self.assertTrue(summary["generation"]["compact_prediction_tables"])

    def test_resume_requires_exact_row_key_and_current_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            result_dir = output_dir / "api_row_results"
            result_dir.mkdir()
            original = {"index": "sample-1", "question": "Original prompt", "answer": "A"}
            path = result_dir / "result.json"
            runner._atomic_write_json(
                path,
                {
                    "index": original["index"],
                    "row_key": runner._row_key(original, 17),
                    "prediction": "A",
                    "request_hash": "a" * 64,
                    "source_row_hash": runner._row_hash(original),
                    "generation_contract_hash": runner._generation_contract_hash(_args()),
                    "model_revision": "test-model",
                },
            )

            existing = runner._load_existing_result_paths(output_dir)
            self.assertIn(runner._row_key(original, 17), existing)

            changed = {**original, "question": "Repaired prompt"}
            self.assertNotIn(runner._row_key(changed, 17), existing)

    def test_prune_and_finalize_ignore_stale_source_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_root = Path(tmp)
            spec = BenchmarkSpec("demo", "Demo", "Demo", "demo")
            current = {"index": "sample-1", "question": "Repaired prompt", "answer": "B"}
            stale = {"index": "sample-1", "question": "Broken prompt", "answer": "B"}
            dataset = SimpleNamespace(dataset_name="Demo", data=runner.pd.DataFrame([current]))
            handle = runner.DatasetHandle(spec=spec, dataset=dataset)
            args = _args()
            output_dir = runner.run_dir(spec, "model", run_root)
            result_dir = output_dir / "api_row_results"
            result_dir.mkdir(parents=True)
            runner._atomic_write_json(
                result_dir / runner._safe_result_name_for_row(stale, 0),
                {
                    "index": "sample-1",
                    "row_key": runner._row_key(stale, 0),
                    "prediction": "stale",
                    "output_token_count": 99,
                    "request_hash": "a" * 64,
                    "source_ordinal": 0,
                    "source_row_hash": runner._row_hash(stale),
                    "generation_contract_hash": runner._generation_contract_hash(args),
                    "generation_contract_version": runner.GENERATION_CONTRACT_VERSION,
                    "media_contract_version": runner.MEDIA_CONTRACT_VERSION,
                    "model_revision": "test-model",
                },
            )
            runner._atomic_write_json(
                result_dir / runner._safe_result_name_for_row(current, 0),
                {
                    "index": "sample-1",
                    "row_key": runner._row_key(current, 0),
                    "prediction": "current",
                    "finish_reason": "stop",
                    "output_token_count": 1,
                    "request_hash": "b" * 64,
                    "source_ordinal": 0,
                    "source_row_hash": runner._row_hash(current),
                    "generation_contract_hash": runner._generation_contract_hash(args),
                    "generation_contract_version": runner.GENERATION_CONTRACT_VERSION,
                    "media_contract_version": runner.MEDIA_CONTRACT_VERSION,
                    "model_revision": "test-model",
                },
            )

            pred_map = runner._prediction_map_from_row_results(output_dir)
            selected = runner._current_prediction_results(pred_map, [current])
            self.assertEqual(len(selected), 1)
            self.assertEqual(next(iter(selected.values()))["prediction"], "current")

            removed = runner._prune_stale_row_results(args, output_dir, [current])
            self.assertEqual(removed, 1)
            self.assertEqual(len(list(result_dir.glob("*.json"))), 1)

    def test_resume_prunes_result_from_a_different_source_ordinal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = BenchmarkSpec("demo", "Demo", "Demo", "demo")
            row = {"index": "same", "question": "same", "answer": "A"}
            handle = runner.DatasetHandle(spec=spec, source_ordinals=[1])
            args = _args()
            output_dir = runner.run_dir(spec, "model", root)
            result_dir = output_dir / "api_row_results"
            result_dir.mkdir(parents=True)
            runner._atomic_write_json(
                result_dir / "result.json",
                {
                    "index": row["index"],
                    "row_key": runner._row_key(row, 0),
                    "prediction": "A",
                    "request_hash": "a" * 64,
                    "source_ordinal": 0,
                    "source_row_hash": runner._row_hash(row),
                    "generation_contract_hash": runner._generation_contract_hash(args),
                    "generation_contract_version": runner.GENERATION_CONTRACT_VERSION,
                    "media_contract_version": runner.MEDIA_CONTRACT_VERSION,
                    "model_revision": "test-model",
                },
            )

            self.assertEqual(
                runner._prune_stale_row_results(args, output_dir, [row], handle),
                1,
            )

    def test_resume_prunes_image_only_media_hash_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = BenchmarkSpec("demo", "Demo", "Demo", "demo")
            row = {"index": "sample-1", "question": "Same prompt", "answer": "A"}
            source_row_hash = runner._row_hash(row)
            media_path = root / "image.bin"
            media_path.write_bytes(b"BBBB")
            media_a = [{"type": "image", "sha256": "a" * 64}]
            media_b = [
                {
                    "type": "image",
                    "path": str(media_path),
                    "size_bytes": 4,
                    "sha256": runner._sha256_file(media_path),
                }
            ]
            hash_a = runner.media_set_sha256(media_a)
            hash_b = runner.media_set_sha256(media_b)
            manifest_row = {
                "index": row["index"],
                "source_row_hash": source_row_hash,
                "media": media_b,
                "media_set_sha256": hash_b,
                "source_record_sha256": runner.source_record_sha256(source_row_hash, hash_b),
            }
            handle = runner.DatasetHandle(
                spec=spec,
                media_rows={(0, row["index"], source_row_hash): manifest_row},
                source_ordinals=[0],
            )
            args = _args(dataset_snapshot_sha256="c" * 64)
            output_dir = runner.run_dir(spec, "model", root)
            result_dir = output_dir / "api_row_results"
            result_dir.mkdir(parents=True)
            runner._atomic_write_json(
                result_dir / "result.json",
                {
                    "index": row["index"],
                    "row_key": runner._row_key(row, 0),
                    "prediction": "A",
                    "request_hash": "d" * 64,
                    "source_row_hash": source_row_hash,
                    "source_record_sha256": runner.source_record_sha256(source_row_hash, hash_a),
                    "media_set_sha256": hash_a,
                    "ordered_media_sha256": ["a" * 64],
                    "dataset_snapshot_sha256": "c" * 64,
                    "generation_contract_hash": runner._generation_contract_hash(args),
                    "generation_contract_version": runner.GENERATION_CONTRACT_VERSION,
                    "media_contract_version": runner.MEDIA_CONTRACT_VERSION,
                    "model_revision": "test-model",
                },
            )

            self.assertEqual(
                runner._prune_stale_row_results(args, output_dir, [row], handle),
                1,
            )

    def test_resume_rejects_same_size_media_mutation_against_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            media_path = root / "image.bin"
            media_path.write_bytes(b"AAAA")
            row = {"index": "sample-1", "question": "Question", "answer": "A"}
            source_row_hash = runner._row_hash(row)
            media = [
                {
                    "type": "image",
                    "path": str(media_path),
                    "size_bytes": 4,
                    "sha256": runner._sha256_file(media_path),
                }
            ]
            media_hash = runner.media_set_sha256(media)
            spec = BenchmarkSpec("demo", "Demo", "Demo", "demo")
            handle = runner.DatasetHandle(
                spec=spec,
                media_rows={
                    (0, row["index"], source_row_hash): {
                        "ordinal": 0,
                        "index": row["index"],
                        "source_row_hash": source_row_hash,
                        "media": media,
                        "media_set_sha256": media_hash,
                        "source_record_sha256": runner.source_record_sha256(
                            source_row_hash, media_hash
                        ),
                    }
                },
                source_ordinals=[0],
            )
            output_dir = runner.run_dir(spec, "model", root)
            result_dir = output_dir / "api_row_results"
            result_dir.mkdir(parents=True)
            runner._atomic_write_json(
                result_dir / "result.json",
                {
                    "index": row["index"],
                    "row_key": runner._row_key(row, 0),
                    "prediction": "A",
                    "request_hash": "d" * 64,
                    "source_row_hash": source_row_hash,
                },
            )
            media_path.write_bytes(b"ZZZZ")

            with self.assertRaisesRegex(RuntimeError, "media content changed"):
                runner._prune_stale_row_results(_args(), output_dir, [row], handle)


if __name__ == "__main__":
    unittest.main()
