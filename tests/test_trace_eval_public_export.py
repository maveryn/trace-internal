from __future__ import annotations

import json
import stat
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

import scripts.trace_eval_public_export as public_export
from scripts.trace_eval_public_export import (
    ExportPlan,
    PublicExportError,
    SCORE_SCHEMA,
    _assert_no_internal_markers,
    canonical_json,
    export_public_artifacts,
    load_and_verify_public_export,
    media_set_sha256,
    sha256_bytes,
    sha256_file,
    source_slice_set_sha256,
    source_record_sha256,
    validate_public_schema,
    verify_rebuilt_prompt,
)


SOURCE_RUN = "private-campaign"
SOURCE_MODEL = "private-model"
SOURCE_REVISION = "b" * 40
REPOSITORY_ID = "example/model"
REPOSITORY_REVISION = "c" * 40
PUBLIC_MODEL = "example-model"
PUBLIC_RUN = "example-comparison-v1"
BENCHMARK = "example_benchmark"


def _write_source_part(
    root: Path,
    *,
    stage: str,
    records: list[dict[str, object]],
    aggregate: dict[str, object],
    source_run: str = SOURCE_RUN,
    source_model: str = SOURCE_MODEL,
    source_revision: str = SOURCE_REVISION,
    repository_id: str = REPOSITORY_ID,
    repository_revision: str = REPOSITORY_REVISION,
    seed: int = 42,
    benchmark: str = BENCHMARK,
) -> None:
    data_dir = (
        root
        / "data"
        / stage
        / f"run={source_run}"
        / f"model={source_model}"
        / f"seed={seed}"
        / f"benchmark={benchmark}"
    )
    data_dir.mkdir(parents=True, exist_ok=True)
    pending = data_dir / "part.parquet"
    pq.write_table(
        pa.Table.from_pylist(
            [
                {
                    "record_id": str(record["record_id"]),
                    "record_json": canonical_json(record),
                }
                for record in records
            ]
        ),
        pending,
    )
    parquet_sha = sha256_file(pending)
    parquet = data_dir / f"part-{parquet_sha}.parquet"
    pending.replace(parquet)
    manifest = {
        "schema_version": "private-archive-v1",
        "identity": {
            "run_id": source_run,
            "model_slug": source_model,
            "model": f"{repository_id}@{repository_revision}",
            "model_revision": source_revision,
            "seed": seed,
            "benchmark": benchmark,
            "dataset_split": "test",
            "stage": stage,
        },
        "rows": len(records),
        "parquet_path": parquet.relative_to(root).as_posix(),
        "parquet_sha256": parquet_sha,
        "payload_sha256": "d" * 64,
        "aggregate": aggregate,
        "provenance": {
            "contract_version": f"private-{stage}-v1",
            "campaign_config_hash": "e" * 64,
            "trace_git_commit": "f" * 40,
            "vlmevalkit_git_commit": "1" * 40,
            "final25_code_hash": "2" * 64,
        },
    }
    manifest_dir = (
        root
        / "metadata"
        / "slices"
        / stage
        / f"run={source_run}"
        / f"model={source_model}"
        / f"seed={seed}"
        / f"benchmark={benchmark}"
    )
    manifest_dir.mkdir(parents=True, exist_ok=True)
    (manifest_dir / f"part-{parquet_sha}.manifest.json").write_text(
        canonical_json(manifest) + "\n", encoding="utf-8"
    )


def _plan(slice_set_digest: str = "0" * 64) -> ExportPlan:
    return ExportPlan.from_mapping(
        {
            "schema_version": "trace_eval_export_plan_v1",
            "source": {
                "run_id": SOURCE_RUN,
                "selection_sha256": "a" * 64,
                "slice_set_sha256": slice_set_digest,
            },
            "public": {
                "run_id": PUBLIC_RUN,
                "suite_id": "trace_eval_v1",
                "benchmarks": [BENCHMARK],
                "categories": {"Reasoning": [BENCHMARK]},
                "seeds": [42],
            },
            "models": [
                {
                    "source_model_id": SOURCE_MODEL,
                    "source_revision": SOURCE_REVISION,
                    "model_id": PUBLIC_MODEL,
                    "model_revision": "3" * 40,
                    "display_name": "Example Model",
                    "repository_id": REPOSITORY_ID,
                    "repository_revision": REPOSITORY_REVISION,
                }
            ],
            "judge": {
                "source_model_id": "qwen3-32b-judge",
                "model_id": "Qwen/Qwen3-32B",
                "model_revision": "5" * 40,
            },
        }
    )


def _build_source(
    root: Path,
    *,
    aggregate_only: bool = False,
    with_judge: bool = False,
    aggregate_rows: int | None = None,
    bad_stage_link: bool = False,
    response_override: str | None = None,
) -> tuple[str, int]:
    count = 2 if aggregate_only else 1
    dataset_sha = "4" * 64
    media_sha = media_set_sha256([])
    prompt = "What is shown?"
    for_generation = []
    for_extraction = []
    for_score = []
    for ordinal in range(count):
        record_id = f"record-{ordinal}"
        source_row_sha = sha256_bytes(f"row-{ordinal}".encode())
        response = (
            response_override
            if response_override is not None
            else ("10\x00units" if ordinal == 0 else "11")
        )
        for_generation.append(
            {
                "record_id": record_id,
                "source_index": str(ordinal),
                "source_ordinal": ordinal,
                "source_row_hash": source_row_sha,
                "prompt": prompt,
                "model_response": response,
                "finish_reason": "stop",
                "sampling": {
                    "temperature": 0.6,
                    "top_p": 1.0,
                    "top_k": -1,
                    "presence_penalty": 0.0,
                    "repetition_penalty": 1.0,
                    "max_tokens": 4096,
                    "seed": 42,
                },
                "metadata": {
                    "dataset_snapshot_sha256": dataset_sha,
                    "image_hash": [],
                    "media_hash": media_sha,
                    "source_record_sha256": source_record_sha256(
                        source_row_sha, media_sha
                    ),
                },
                "usage": {"prompt_tokens": 4, "completion_tokens": 2},
            }
        )
        extraction_record = {
            "record_id": record_id,
            "source_index": str(ordinal),
            "source_ordinal": ordinal,
            "source_row_hash": (
                "0" * 64 if bad_stage_link and ordinal == 0 else source_row_sha
            ),
            "normalized_extraction": {
                "status": "resolved",
                "value": 10 + ordinal,
                "candidates": [10 + ordinal],
                "method": "deterministic_parser",
            },
        }
        if with_judge:
            extraction_record.update(
                {
                    "judge_prompt": "private judge prompt",
                    "judge_response": str(10 + ordinal),
                    "retries": {"events": [{"response": str(10 + ordinal)}]},
                }
            )
        for_extraction.append(extraction_record)
        score = None if aggregate_only else 1
        for_score.append(
            {
                "record_id": record_id,
                "source_index": str(ordinal),
                "source_ordinal": ordinal,
                "source_row_hash": source_row_sha,
                "score": score,
                "excluded": False,
                "metadata": (
                    {
                        "score_contract": "aggregate_only",
                        "aggregate_score": 75.0,
                    }
                    if aggregate_only
                    else {}
                ),
            }
        )
    _write_source_part(
        root,
        stage="generation",
        records=for_generation,
        aggregate={
            "rows": count,
            "generation": {
                "media_contract_version": "private-media-v7",
                "media_transport": "file-url",
                "min_image_pixels": 3136,
                "max_image_pixels": 12845056,
                "max_image_side": None,
                "image_jpeg_quality": None,
            },
        },
    )
    _write_source_part(
        root,
        stage="extraction",
        records=for_extraction,
        aggregate={
            "rows": count,
            **(
                {"judge_model": "/models/qwen3-32b-judge"}
                if with_judge
                else {}
            ),
        },
    )
    _write_source_part(
        root,
        stage="score",
        records=for_score,
        aggregate={
            "rows": count if aggregate_rows is None else aggregate_rows,
            "score": 75.0 if aggregate_only else 100.0,
        },
    )
    return prompt, count


def _source_slice_digest(root: Path) -> str:
    config_for_stage = {
        "generation": "responses",
        "extraction": "extractions",
        "score": "scores",
    }
    records = []
    for stage, config_name in config_for_stage.items():
        manifest_path = next((root / "metadata" / "slices" / stage).rglob("*.json"))
        manifest = json.loads(manifest_path.read_text())
        parquet_path = root / manifest["parquet_path"]
        records.append(
            {
                "config_name": config_name,
                "model_id": PUBLIC_MODEL,
                "seed": 42,
                "benchmark_id": BENCHMARK,
                "manifest": {
                    "sha256": sha256_file(manifest_path),
                    "size": manifest_path.stat().st_size,
                },
                "parquet": {
                    "sha256": sha256_file(parquet_path),
                    "size": parquet_path.stat().st_size,
                },
            }
        )
    return source_slice_set_sha256(records)


def _artifact(result, config: str) -> dict[str, object]:
    return next(
        item for item in result.manifest["artifacts"] if item["config_name"] == config
    )


def test_public_export_preserves_authoritative_types_controls_and_is_idempotent(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    output = tmp_path / "public"
    prompt, _ = _build_source(source, with_judge=True)
    plan = _plan(_source_slice_digest(source))
    first = export_public_artifacts(source, plan, output)
    responses = pq.ParquetFile(output / _artifact(first, "responses")["parquet_path"]).read()
    extractions = pq.ParquetFile(
        output / _artifact(first, "extractions")["parquet_path"]
    ).read()
    response = responses.to_pylist()[0]
    extraction = extractions.to_pylist()[0]
    assert response["response_text"] == "10\x00units"
    assert extraction["extraction_value_type"] == "integer"
    assert json.loads(extraction["extraction_value_json"]) == 10
    assert isinstance(json.loads(extraction["extraction_value_json"]), int)
    assert extraction["used_judge"] is True
    assert extraction["judge_model_id"] == "Qwen/Qwen3-32B"
    assert extraction["judge_model_revision"] == "5" * 40
    assert extraction["retry_count"] == 0
    assert "prompt" not in responses.schema.names
    assert "ground_truth" not in extractions.schema.names
    settings = json.loads(response["generation_settings_json"])
    assert settings["media_contract_version"] == "trace_eval_media_v1"
    assert settings["media_transport"] == "file-url"
    assert settings["min_image_pixels"] == 3136
    assert settings["max_image_pixels"] == 12845056
    assert first.manifest["source_slice_set_sha256"] == plan.source_slice_set_sha256

    verified_prompt = verify_rebuilt_prompt(
        output,
        model_id=PUBLIC_MODEL,
        seed=42,
        benchmark_id=BENCHMARK,
        source_index="0",
        prompt_text=prompt,
    )
    assert verified_prompt["verified"] is True
    assert verified_prompt["dataset_reconstruction_status"] == "external_release_gate"

    before = {
        path.relative_to(output).as_posix(): sha256_file(path)
        for path in output.rglob("*")
        if path.is_file()
    }
    second = export_public_artifacts(source, plan, output)
    after = {
        path.relative_to(output).as_posix(): sha256_file(path)
        for path in output.rglob("*")
        if path.is_file()
    }
    assert second.manifest_sha256 == first.manifest_sha256
    assert after == before


def test_reload_rejects_private_marker_inside_opaque_response(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "public"
    private_marker = "unpublished-campaign-identifier-xyz"
    _build_source(source, response_override=f"answer from {private_marker}")
    plan = _plan(_source_slice_digest(source))
    export_public_artifacts(source, plan, output)
    load_and_verify_public_export(output, expected_artifacts=3)

    with pytest.raises(PublicExportError, match="private identifier or local path leaked"):
        load_and_verify_public_export(
            output,
            expected_artifacts=3,
            dynamic_markers=(private_marker,),
        )


def test_aggregate_only_placeholder_scores_are_collapsed(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "public"
    _, count = _build_source(source, aggregate_only=True)
    result = export_public_artifacts(
        source, _plan(_source_slice_digest(source)), output
    )
    artifact = _artifact(result, "scores")
    rows = pq.ParquetFile(output / artifact["parquet_path"]).read().to_pylist()
    assert artifact["scoring_scope"] == "aggregate_only"
    assert artifact["placeholder_records_removed"] == count
    assert len(rows) == 1
    assert rows[0]["score_scope"] == "aggregate"
    assert rows[0]["score_value"] == 75.0
    results = json.loads(
        (output / "metadata/results/benchmark_scores.json").read_text()
    )
    assert results["benchmark_scores"][0]["score"] == 75.0
    load_and_verify_public_export(output, expected_artifacts=3)


def test_forbidden_public_fields_and_schema_are_rejected() -> None:
    with pytest.raises(PublicExportError, match="forbidden public field"):
        _assert_no_internal_markers({"prompt": "do not publish"})
    bad_schema = SCORE_SCHEMA.append(pa.field("ground_truth", pa.string()))
    with pytest.raises(PublicExportError, match="forbidden fields"):
        validate_public_schema(bad_schema, "scores")


def test_source_inspection_derives_digest_without_claiming_verification(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    _build_source(source)
    digest = _source_slice_digest(source)
    inspection = public_export.inspect_source_selection(source, _plan())
    assert inspection == {
        "inspection_only": True,
        "coverage": 3,
        "expected_coverage": 3,
        "source_slice_set_sha256": digest,
        "matches_plan": False,
    }
    with pytest.raises(PublicExportError, match="slice-set digest"):
        export_public_artifacts(source, _plan(), tmp_path / "public")


def test_cross_stage_identity_mismatch_fails(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _build_source(source, bad_stage_link=True)
    with pytest.raises(PublicExportError, match="does not match generation"):
        export_public_artifacts(
            source, _plan(_source_slice_digest(source)), tmp_path / "public"
        )


def test_aggregate_row_count_mismatch_fails(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _build_source(source, aggregate_rows=2)
    with pytest.raises(PublicExportError, match="evaluated rows"):
        export_public_artifacts(
            source, _plan(_source_slice_digest(source)), tmp_path / "public"
        )


@pytest.mark.parametrize(
    "private_text", ["saved at /dev/shm/private.bin", SOURCE_RUN]
)
def test_private_output_leak_fails_without_redaction(
    tmp_path: Path, private_text: str
) -> None:
    source = tmp_path / "source"
    _build_source(source, response_override=private_text)
    with pytest.raises(PublicExportError, match="private identifier|local path"):
        export_public_artifacts(
            source, _plan(_source_slice_digest(source)), tmp_path / "public"
        )


def test_interrupt_removes_owned_temporary_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    (source / "data").mkdir(parents=True)
    (source / "metadata" / "slices").mkdir(parents=True)

    def interrupt(*_args, **_kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(public_export, "_discover_source_slices", interrupt)
    with pytest.raises(KeyboardInterrupt):
        export_public_artifacts(source, _plan(), tmp_path / "public")
    assert not list(tmp_path.glob(".trace-eval-public-*"))


def _canonical_plan_model(*, source_revision: str = SOURCE_REVISION) -> dict[str, str]:
    return {
        "source_model_id": SOURCE_MODEL,
        "source_revision": source_revision,
        "model_id": PUBLIC_MODEL,
        "model_revision": "3" * 40,
        "display_name": "Example Model",
        "repository_id": REPOSITORY_ID,
        "repository_revision": REPOSITORY_REVISION,
    }


def _canonical_plan_judge(*, revision: str = "5" * 40) -> dict[str, str]:
    return {
        "source_model_id": "qwen3-32b-judge",
        "model_id": "Qwen/Qwen3-32B",
        "model_revision": revision,
    }


def _build_canonical_plan_source(root: Path) -> None:
    suite = public_export._canonical_suite_dimensions()
    for benchmark in suite["benchmarks"]:
        for stage in ("generation", "extraction", "score"):
            _write_source_part(
                root,
                stage=stage,
                records=[{"record_id": f"{benchmark}-{stage}"}],
                aggregate={},
                benchmark=benchmark,
            )


def test_build_plan_cli_seals_canonical_source_and_writes_private_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "source"
    output = tmp_path / "private" / "export-plan.json"
    _build_canonical_plan_source(source)

    assert public_export.main(
        [
            "build-plan",
            "--source-root",
            str(source),
            "--source-run-id",
            SOURCE_RUN,
            "--public-run-id",
            PUBLIC_RUN,
            "--seed",
            "42",
            "--model",
            SOURCE_MODEL,
            SOURCE_REVISION,
            PUBLIC_MODEL,
            "3" * 40,
            "Example Model",
            REPOSITORY_ID,
            REPOSITORY_REVISION,
            "--judge",
            "qwen3-32b-judge",
            "Qwen/Qwen3-32B",
            "5" * 40,
            "--output",
            str(output),
        ]
    ) == 0
    report = json.loads(capsys.readouterr().out)
    plan = public_export.load_export_plan(output)
    assert report["coverage"] == 72
    assert report["source_slice_set_sha256"] == plan.source_slice_set_sha256
    assert len(plan.benchmarks) == 24
    assert plan.source_run_id == SOURCE_RUN
    assert plan.run_id == PUBLIC_RUN
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    inspection = public_export.inspect_source_selection(source, plan)
    assert inspection["coverage"] == inspection["expected_coverage"] == 72
    assert inspection["matches_plan"] is True

    linked_output = tmp_path / "linked-plan.json"
    linked_output.symlink_to(output)
    with pytest.raises(PublicExportError, match="through a symlink"):
        public_export.build_private_export_plan(
            source,
            source_run_id=SOURCE_RUN,
            public_run_id=PUBLIC_RUN,
            seeds=[42],
            models=[_canonical_plan_model()],
            judge=_canonical_plan_judge(),
            output=linked_output,
        )


def test_build_plan_fails_closed_on_missing_or_extra_source_slice(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _build_canonical_plan_source(source)
    extra = "not_in_trace_eval_v1"
    _write_source_part(
        source,
        stage="generation",
        records=[{"record_id": "extra"}],
        aggregate={},
        benchmark=extra,
    )
    arguments = {
        "source_run_id": SOURCE_RUN,
        "public_run_id": PUBLIC_RUN,
        "seeds": [42],
        "models": [_canonical_plan_model()],
        "judge": _canonical_plan_judge(),
    }
    with pytest.raises(PublicExportError, match="outside the requested canonical selection"):
        public_export.build_private_export_plan(
            source, output=tmp_path / "extra-plan.json", **arguments
        )

    extra_root = source / "metadata" / "slices" / "generation"
    next(extra_root.rglob(f"benchmark={extra}/*.manifest.json")).unlink()
    missing = next(
        (source / "metadata" / "slices" / "score").rglob(
            "benchmark=chartqapro/*.manifest.json"
        )
    )
    missing.unlink()
    with pytest.raises(PublicExportError, match="source coverage mismatch"):
        public_export.build_private_export_plan(
            source, output=tmp_path / "missing-plan.json", **arguments
        )


@pytest.mark.parametrize(
    ("models", "judge"),
    [
        ([_canonical_plan_model(source_revision="main")], _canonical_plan_judge()),
        ([_canonical_plan_model()], _canonical_plan_judge(revision="latest")),
    ],
)
def test_build_plan_rejects_mutable_model_or_judge_revision(
    tmp_path: Path,
    models: list[dict[str, str]],
    judge: dict[str, str],
) -> None:
    with pytest.raises(PublicExportError, match="commit or content digest"):
        public_export.build_private_export_plan(
            tmp_path / "source",
            source_run_id=SOURCE_RUN,
            public_run_id=PUBLIC_RUN,
            seeds=[42],
            models=models,
            judge=judge,
            output=tmp_path / "plan.json",
        )


@pytest.mark.parametrize("symlink_parent", [False, True])
def test_private_plan_writer_rejects_symlink_path_components(
    tmp_path: Path, symlink_parent: bool
) -> None:
    target = tmp_path / "target"
    if symlink_parent:
        target.mkdir()
        linked_parent = tmp_path / "linked-parent"
        linked_parent.symlink_to(target, target_is_directory=True)
        output = linked_parent / "plan.json"
    else:
        output = tmp_path / "plan.json"
        output.symlink_to(target / "plan.json")

    with pytest.raises(PublicExportError, match="through a symlink"):
        public_export._write_private_plan(output, {"private": True})
    assert not (target / "plan.json").exists()
