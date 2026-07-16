from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pyarrow.parquet as pq

from scripts.final25_hf_archive_lib import (
    ArchiveDaemon,
    ArchiveIntegrityError,
    ArchiveValidationError,
    emit_slice_ready,
    read_token_file,
    reconstruct_remote,
    verify_expected_slice_coverage,
)
from scripts.final25_hf_archive import _expected_coverage, _parser as archive_cli_parser


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _provenance() -> dict:
    return {
        "trace_git_commit": "trace-commit",
        "vlmevalkit_git_commit": "vlm-commit",
        "contract_version": "final25-v1",
        "campaign_config_hash": "config-sha",
        "wandb_run_id": "run-123",
        "packages": {"pyarrow": "test"},
    }


def _generation_record(index: str = "sample-1", ordinal: int = 0) -> dict:
    return {
        "source_index": index,
        "source_ordinal": ordinal,
        "source_row_hash": _sha(f"source:{index}:{ordinal}".encode()),
        "request_hash": _sha(f"request:{index}:{ordinal}".encode()),
        "question": "Which option is correct?",
        "ground_truth": "B",
        "options": {"A": "one", "B": "two"},
        "source_row": {"index": index, "question": "Which option is correct?", "image_hash": "abc"},
        "metadata": {"category": "synthetic", "image_count": 1},
        "prompt": "<image> Which option is correct?",
        "model_response": "<answer>B</answer>",
        "sampling": {"temperature": 0.6, "seed": 42},
        "finish_reason": "stop",
        "usage": {"prompt_tokens": 10, "completion_tokens": 4},
    }


def _extraction_record(index: str = "sample-1", ordinal: int = 0) -> dict:
    base = _generation_record(index, ordinal)
    return {
        key: base[key]
        for key in (
            "source_index",
            "source_ordinal",
            "source_row_hash",
            "question",
            "ground_truth",
            "model_response",
        )
    } | {
        "request_hash": _sha(f"extract:{index}:{ordinal}".encode()),
        "judge_prompt": "Return the selected option.",
        "judge_response": '{"answer":"B"}',
        "normalized_extraction": "B",
        "retries": [],
    }


def _score_record(index: str = "sample-1", ordinal: int = 0) -> dict:
    base = _generation_record(index, ordinal)
    return {
        key: base[key]
        for key in (
            "source_index",
            "source_ordinal",
            "source_row_hash",
            "question",
            "ground_truth",
        )
    } | {
        "request_hash": _sha(f"score:{index}:{ordinal}".encode()),
        "prediction": "B",
        "score": 1.0,
        "scorer": "official_exact_match",
        "excluded": False,
    }


def _emit(
    root: Path,
    stage: str,
    records: list[dict] | None = None,
    *,
    aggregate: dict | None = None,
    provenance: dict | None = None,
) -> Path:
    factory = {
        "generation": _generation_record,
        "extraction": _extraction_record,
        "score": _score_record,
    }[stage]
    return emit_slice_ready(
        root,
        stage=stage,
        run_id="trace-eval-001",
        model="Qwen/Test-7B",
        model_revision="checkpoint-500",
        model_slug="qwen-test-7b",
        seed=42,
        benchmark="chartqapro",
        dataset_alias="ChartQAPro_CoT",
        dataset_split="test",
        dataset_revision="dataset-sha",
        records=records or [factory()],
        provenance=provenance or _provenance(),
        aggregate=(
            aggregate
            if aggregate is not None
            else ({"accuracy": 1.0} if stage == "score" else {})
        ),
    )


class FakeHfApi:
    def __init__(self, *, private: bool = True, exists: bool = True):
        self.private = private
        self.exists = exists
        self.create_calls = 0
        self.files: dict[str, bytes] = {}
        self.commits = 0
        self.commit_failures = 0
        self.last_num_threads = None

    def create_repo(self, *, private: bool, **_kwargs):
        self.create_calls += 1
        self.exists = True
        self.private = private
        return SimpleNamespace(repo_id="maveryn/test")

    def repo_info(self, **_kwargs):
        if not self.exists:
            from huggingface_hub.errors import RepositoryNotFoundError

            raise RepositoryNotFoundError("synthetic missing repo")
        siblings = [
            SimpleNamespace(
                rfilename=name,
                lfs=SimpleNamespace(sha256=_sha(content)),
            )
            for name, content in sorted(self.files.items())
        ]
        return SimpleNamespace(private=self.private, siblings=siblings)

    def create_commit(self, *, operations, num_threads, **_kwargs):
        if self.commit_failures:
            self.commit_failures -= 1
            raise RuntimeError("synthetic transient failure")
        for operation in operations:
            source = operation.path_or_fileobj
            if isinstance(source, bytes):
                content = source
            elif hasattr(source, "read"):
                position = source.tell()
                content = source.read()
                source.seek(position)
            else:
                content = Path(source).read_bytes()
            self.files[operation.path_in_repo] = content
        self.commits += 1
        self.last_num_threads = num_threads
        return SimpleNamespace(oid=f"commit-{self.commits}")

    def list_repo_files(self, **_kwargs):
        return sorted(self.files)

    def hf_hub_download(self, *, filename, local_dir, **_kwargs):
        destination = Path(local_dir) / filename
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(self.files[filename])
        return str(destination)


class Final25HfArchiveTests(unittest.TestCase):
    def test_emit_is_atomic_idempotent_and_stable_across_stages(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = _emit(root, "generation")
            second = _emit(root, "generation")
            extraction = _emit(root, "extraction")

            self.assertEqual(first, second)
            self.assertEqual(len(list((root / "ready").glob("*.ready.json"))), 2)
            self.assertEqual(list(root.rglob("*.tmp")), [])
            self.assertEqual(root.stat().st_mode & 0o777, 0o700)
            self.assertEqual(first.stat().st_mode & 0o777, 0o600)
            generation_payload = json.loads(
                (root / json.loads(first.read_text())["payload_path"]).read_text().strip()
            )
            payload_path = root / json.loads(first.read_text())["payload_path"]
            self.assertEqual(payload_path.stat().st_mode & 0o777, 0o600)
            extraction_payload = json.loads(
                (root / json.loads(extraction.read_text())["payload_path"]).read_text().strip()
            )
            self.assertEqual(generation_payload["record_id"], extraction_payload["record_id"])

    def test_rejects_media_credentials_and_incomplete_records(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for field, value in (
                ("image", "pixels omitted"),
                ("artifact", "data:image/png;base64,abc"),
                ("artifact", "/tmp/benchmark/image.png"),
                ("artifact", "image.png"),
                ("blob", b"raw pixels"),
                ("hf_token", "secret"),
                ("github_token", "secret"),
                ("wandbToken", "secret"),
                ("private_key", "secret"),
            ):
                record = _generation_record()
                record[field] = value
                with self.subTest(field=field, value_type=type(value).__name__):
                    with self.assertRaises(ArchiveValidationError):
                        _emit(root, "generation", [record])

            incomplete = _generation_record()
            del incomplete["source_row_hash"]
            with self.assertRaisesRegex(ArchiveValidationError, "source_row_hash"):
                _emit(root, "generation", [incomplete])

    def test_generation_aggregate_allows_media_contract_metadata_only(self):
        aggregate = {
            "generation": {
                "media_contract_version": "trace-final25-media-v1",
                "media_transport": "file-url",
                "min_image_pixels": 1_003_520,
                "max_image_pixels": 12_845_056,
                "max_image_side": None,
                "image_jpeg_quality": None,
                "media_cache_dir": None,
            }
        }
        with tempfile.TemporaryDirectory() as temporary:
            descriptor_path = _emit(
                Path(temporary), "generation", aggregate=aggregate
            )
            descriptor = json.loads(descriptor_path.read_text())
            self.assertEqual(descriptor["aggregate"], aggregate)

        for key, value in (
            ("media_cache_dir", "/dev/shm/trace/media-cache"),
            ("image", "pixels omitted"),
            ("artifact", "/tmp/benchmark/image.png"),
        ):
            unsafe = {"generation": dict(aggregate["generation"])}
            unsafe["generation"][key] = value
            with self.subTest(key=key):
                with tempfile.TemporaryDirectory() as temporary:
                    with self.assertRaises(ArchiveValidationError):
                        _emit(Path(temporary), "generation", aggregate=unsafe)

    def test_duplicate_source_indices_require_distinct_ordinals(self):
        with tempfile.TemporaryDirectory() as temporary:
            duplicate = [_generation_record(), _generation_record()]
            with self.assertRaisesRegex(ArchiveValidationError, "duplicate record identity"):
                _emit(Path(temporary), "generation", duplicate)

            distinct = [_generation_record(), _generation_record(ordinal=1)]
            descriptor = _emit(Path(temporary), "generation", distinct)
            self.assertTrue(descriptor.is_file())

    def test_builds_zstd_parquet_and_provenance_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            descriptor = _emit(root, "generation")
            daemon = ArchiveDaemon(spool_root=root, api=FakeHfApi(), token="not-logged")
            built = daemon.build_descriptor(descriptor)

            parquet_path = Path(built["parquet_path"])
            self.assertEqual(parquet_path.stat().st_mode & 0o777, 0o600)
            self.assertEqual((root / "ledger.sqlite3").stat().st_mode & 0o777, 0o600)
            self.assertRegex(
                built["remote_parquet_path"],
                r"^data/generation/run=trace-eval-001/model=qwen-test-7b/seed=42/"
                r"benchmark=chartqapro/part-[0-9a-f]{64}\.parquet$",
            )
            metadata = pq.ParquetFile(parquet_path).metadata
            self.assertEqual(metadata.num_rows, 1)
            self.assertEqual(metadata.row_group(0).column(0).compression, "ZSTD")
            row = pq.ParquetFile(parquet_path).read().to_pylist()[0]
            self.assertEqual(row["source_index"], "sample-1")
            self.assertNotIn("base64", row["record_json"])
            manifest = json.loads(Path(built["manifest_path"]).read_text())
            self.assertEqual(manifest["parquet_sha256"], built["parquet_sha256"])
            self.assertEqual(manifest["provenance"]["wandb_run_id"], "run-123")
            self.assertNotIn("created_at", manifest)
            manifest_material = dict(manifest)
            manifest_sha = manifest_material.pop("manifest_sha256")
            self.assertEqual(
                manifest_sha,
                _sha(
                    json.dumps(
                        manifest_material,
                        ensure_ascii=True,
                        sort_keys=True,
                        separators=(",", ":"),
                        allow_nan=False,
                    ).encode("utf-8")
                ),
            )

            score_descriptor = _emit(root, "score")
            score_built = daemon.build_descriptor(score_descriptor)
            self.assertEqual(
                pq.ParquetFile(parquet_path).schema_arrow,
                pq.ParquetFile(score_built["parquet_path"]).schema_arrow,
            )

    def test_identical_slice_is_remote_idempotent_across_fresh_spools(self):
        with tempfile.TemporaryDirectory() as temporary:
            fake = FakeHfApi()
            first_root = Path(temporary) / "first"
            second_root = Path(temporary) / "second"
            with patch(
                "scripts.final25_hf_archive_lib.utc_now",
                return_value="2026-01-01T00:00:00+00:00",
            ):
                _emit(first_root, "generation")
            first = ArchiveDaemon(
                spool_root=first_root, repo_id="maveryn/test", api=fake, token="x"
            )
            self.assertEqual(first.flush_all().uploaded, 1)

            with patch(
                "scripts.final25_hf_archive_lib.utc_now",
                return_value="2026-01-02T00:00:00+00:00",
            ):
                _emit(second_root, "generation")
            second = ArchiveDaemon(
                spool_root=second_root, repo_id="maveryn/test", api=fake, token="x"
            )
            report = second.flush_all()

            self.assertEqual(report.failed, 0)
            self.assertEqual(report.already_remote, 1)
            self.assertEqual(report.uploaded, 0)

    def test_private_init_flush_remote_verify_and_idempotency(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _emit(root, "generation")
            fake = FakeHfApi(private=False, exists=False)
            daemon = ArchiveDaemon(
                spool_root=root,
                repo_id="maveryn/test",
                token="not-logged",
                api=fake,
                upload_threads=8,
            )
            daemon.initialize_repo()
            daemon.initialize_repo()
            report = daemon.flush_all()

            self.assertTrue(fake.private)
            self.assertEqual(fake.create_calls, 1)
            self.assertEqual(report.uploaded, 1)
            self.assertEqual(fake.last_num_threads, 8)
            self.assertTrue(any(name.endswith(".parquet") for name in fake.files))
            self.assertTrue(any(name.endswith(".manifest.json") for name in fake.files))
            self.assertEqual(daemon.verify(), {"slices": 1, "rows": 1})
            commits = fake.commits
            second = daemon.flush_all()
            self.assertEqual(second.uploaded, 0)
            self.assertEqual(fake.commits, commits)

            for ledger_path in root.glob("ledger.sqlite3*"):
                ledger_path.unlink()
            recovered = ArchiveDaemon(
                spool_root=root,
                repo_id="maveryn/test",
                token="not-logged",
                api=fake,
            )
            recovery_report = recovered.flush_all()
            self.assertEqual(recovery_report.already_remote, 1)
            self.assertEqual(fake.commits, commits)

    def test_upload_retries_then_verifies(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _emit(root, "score")
            fake = FakeHfApi()
            fake.commit_failures = 2
            sleeps: list[float] = []
            daemon = ArchiveDaemon(
                spool_root=root,
                repo_id="maveryn/test",
                token="not-logged",
                api=fake,
                max_retries=3,
                retry_base_seconds=1,
                retry_cap_seconds=10,
                sleep=sleeps.append,
            )
            report = daemon.flush_all()

            self.assertEqual(report.uploaded, 1)
            self.assertEqual(sleeps, [1, 2])
            self.assertEqual(daemon.verify()["slices"], 1)

    def test_refuses_remote_content_mismatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _emit(root, "generation")
            fake = FakeHfApi()
            daemon = ArchiveDaemon(spool_root=root, repo_id="maveryn/test", api=fake, token="x")
            daemon.build_ready()
            row = daemon.ledger.rows(("built",))[0]
            fake.files[row["remote_parquet_path"]] = b"different immutable content"

            with self.assertRaises(ArchiveIntegrityError):
                daemon._upload_rows([row])

    def test_reconstructs_matching_remote_slices(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "spool"
            for stage in ("generation", "extraction", "score"):
                _emit(root, stage)
            fake = FakeHfApi()
            daemon = ArchiveDaemon(spool_root=root, repo_id="maveryn/test", api=fake, token="x")
            report = daemon.flush_all()
            self.assertEqual(report.uploaded, 3)

            output = Path(temporary) / "reconstructed.parquet"
            rows = reconstruct_remote(
                api=fake,
                repo_id="maveryn/test",
                revision="main",
                token="x",
                output=output,
                run_id="trace-eval-001",
                model_slug="qwen-test-7b",
                seed=42,
                benchmark="chartqapro",
            )
            table = pq.ParquetFile(output).read()
            self.assertEqual(rows, 3)
            self.assertEqual(set(table.column("stage").to_pylist()), {"generation", "extraction", "score"})
            self.assertEqual(len(set(table.column("record_id").to_pylist())), 1)

    def test_reconstruct_rejects_duplicate_logical_slices(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "spool"
            _emit(root, "generation", aggregate={"version": 1})
            _emit(root, "generation", aggregate={"version": 2})
            fake = FakeHfApi()
            daemon = ArchiveDaemon(
                spool_root=root, repo_id="maveryn/test", api=fake, token="x"
            )
            self.assertEqual(daemon.flush_all().uploaded, 2)

            with self.assertRaisesRegex(ArchiveIntegrityError, "duplicate logical remote slice"):
                reconstruct_remote(
                    api=fake,
                    repo_id="maveryn/test",
                    revision="main",
                    token="x",
                    output=Path(temporary) / "duplicate.parquet",
                    stage="generation",
                    run_id="trace-eval-001",
                    model_slug="qwen-test-7b",
                    seed=42,
                    benchmark="chartqapro",
                )

    def test_reconstruct_verifies_remote_parquet_and_manifest_digests(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "spool"
            _emit(root, "generation")
            fake = FakeHfApi()
            daemon = ArchiveDaemon(
                spool_root=root, repo_id="maveryn/test", api=fake, token="x"
            )
            self.assertEqual(daemon.flush_all().uploaded, 1)
            output = Path(temporary) / "reconstructed.parquet"
            parquet_path = next(name for name in fake.files if name.endswith(".parquet"))
            original_parquet = fake.files[parquet_path]
            fake.files[parquet_path] = b"corrupt"
            with self.assertRaisesRegex(ArchiveIntegrityError, "Parquet digest mismatch"):
                reconstruct_remote(
                    api=fake,
                    repo_id="maveryn/test",
                    revision="main",
                    token="x",
                    output=output,
                    stage="generation",
                )

            fake.files[parquet_path] = original_parquet
            manifest_path = next(name for name in fake.files if name.endswith(".manifest.json"))
            manifest = json.loads(fake.files[manifest_path])
            manifest["aggregate"] = {"tampered": True}
            fake.files[manifest_path] = json.dumps(manifest, sort_keys=True).encode("utf-8")
            with self.assertRaisesRegex(ArchiveIntegrityError, "manifest digest mismatch"):
                reconstruct_remote(
                    api=fake,
                    repo_id="maveryn/test",
                    revision="main",
                    token="x",
                    output=output,
                    stage="generation",
                )

    def test_reconstruct_sorts_rows_by_source_ordinal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "spool"
            _emit(
                root,
                "generation",
                records=[
                    _generation_record(index="2", ordinal=1),
                    _generation_record(index="10", ordinal=0),
                ],
            )
            fake = FakeHfApi()
            daemon = ArchiveDaemon(
                spool_root=root, repo_id="maveryn/test", api=fake, token="x"
            )
            self.assertEqual(daemon.flush_all().uploaded, 1)
            output = Path(temporary) / "ordered.parquet"
            reconstruct_remote(
                api=fake,
                repo_id="maveryn/test",
                revision="main",
                token="x",
                output=output,
                stage="generation",
            )
            reconstructed = pq.read_table(output)
            self.assertEqual(reconstructed.column("source_ordinal").to_pylist(), [0, 1])
            self.assertEqual(reconstructed.column("source_index").to_pylist(), ["10", "2"])

    def test_token_file_must_be_private(self):
        with tempfile.TemporaryDirectory() as temporary:
            token_path = Path(temporary) / "hf-token.txt"
            token_path.write_text("secret-token\n", encoding="utf-8")
            os.chmod(token_path, 0o644)
            with self.assertRaisesRegex(ArchiveValidationError, "mode 600"):
                read_token_file(token_path)
            os.chmod(token_path, 0o600)
            self.assertEqual(read_token_file(token_path), "secret-token")

    def test_expected_campaign_coverage_detects_missing_stage(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for stage in ("generation", "extraction", "score"):
                _emit(root, stage)
            report = verify_expected_slice_coverage(
                root,
                run_id="trace-eval-001",
                model_slugs=["qwen-test-7b"],
                seeds=[42],
                benchmarks=["chartqapro"],
            )
            self.assertEqual(report["expected_identities"], 3)

            (root / "ready" / _emit(root, "score").name).unlink()
            with self.assertRaisesRegex(ArchiveIntegrityError, "missing 1 expected slices"):
                verify_expected_slice_coverage(
                    root,
                    run_id="trace-eval-001",
                    model_slugs=["qwen-test-7b"],
                    seeds=[42],
                    benchmarks=["chartqapro"],
                )

    def test_expected_coverage_rejects_duplicates_and_provenance_mismatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _emit(root, "generation", aggregate={"version": 1})
            verified = verify_expected_slice_coverage(
                root,
                run_id="trace-eval-001",
                model_slugs=["qwen-test-7b"],
                seeds=[42],
                benchmarks=["chartqapro"],
                stages=["generation"],
                campaign_config_hash="config-sha",
                dataset_revision="dataset-sha",
            )
            self.assertEqual(verified["descriptor_versions"], 1)
            with self.assertRaisesRegex(ArchiveIntegrityError, "provenance mismatches"):
                verify_expected_slice_coverage(
                    root,
                    run_id="trace-eval-001",
                    model_slugs=["qwen-test-7b"],
                    seeds=[42],
                    benchmarks=["chartqapro"],
                    stages=["generation"],
                    campaign_config_hash="wrong-config",
                )

            _emit(root, "generation", aggregate={"version": 2})
            with self.assertRaisesRegex(ArchiveIntegrityError, "duplicate logical slices"):
                verify_expected_slice_coverage(
                    root,
                    run_id="trace-eval-001",
                    model_slugs=["qwen-test-7b"],
                    seeds=[42],
                    benchmarks=["chartqapro"],
                    stages=["generation"],
                )

    def test_discover_skips_one_malformed_descriptor(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _emit(root, "generation")
            malformed = root / "ready" / "malformed.ready.json"
            malformed.write_text("{not-json", encoding="utf-8")
            daemon = ArchiveDaemon(spool_root=root, api=FakeHfApi(), token="x")

            discovered = daemon.discover()

            self.assertEqual(len(discovered), 1)
            self.assertEqual(len(daemon.ledger.rows()), 1)

    def test_cli_wires_expected_provenance_flags_for_verify_and_coverage(self):
        parser = archive_cli_parser()
        common = [
            "--spool-root",
            "/tmp/archive",
            "--expect-run-id",
            "run",
            "--expect-model-slug",
            "model",
            "--expect-seed",
            "42",
            "--expect-campaign-config-hash",
            "config",
            "--expect-dataset-revision",
            "dataset",
        ]
        coverage = parser.parse_args(
            common[:2] + ["coverage", "--expect-final25"] + common[2:]
        )
        self.assertEqual(coverage.expect_campaign_config_hash, "config")
        self.assertEqual(coverage.expect_dataset_revision, "dataset")
        verify = parser.parse_args(
            common[:2] + ["verify", "--expect-final25"] + common[2:]
        )
        self.assertEqual(verify.expect_campaign_config_hash, "config")
        self.assertEqual(verify.expect_dataset_revision, "dataset")
        targeted = parser.parse_args(
            common[:2]
            + ["coverage", "--expect-benchmark", "mme_reasoning"]
            + common[2:]
        )
        self.assertFalse(targeted.expect_final25)
        self.assertEqual(targeted.expect_benchmark, ["mme_reasoning"])

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _emit(root, "generation")
            targeted = parser.parse_args(
                [
                    "--spool-root",
                    str(root),
                    "coverage",
                    "--expect-run-id",
                    "trace-eval-001",
                    "--expect-model-slug",
                    "qwen-test-7b",
                    "--expect-seed",
                    "42",
                    "--expect-benchmark",
                    "chartqapro",
                    "--expect-stage",
                    "generation",
                    "--expect-campaign-config-hash",
                    "config-sha",
                    "--expect-dataset-revision",
                    "dataset-sha",
                ]
            )
            self.assertEqual(_expected_coverage(targeted)["expected_identities"], 1)


if __name__ == "__main__":
    unittest.main()
