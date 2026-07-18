from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from PIL import Image

pa = pytest.importorskip("pyarrow")
pq = pytest.importorskip("pyarrow.parquet")

from evaluation.trace_validation import prepare_dataset as prepare


def _png_bytes(color: str, size: tuple[int, int]) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


def _write_fixture_parquet(path: Path, *, duplicate_ids: bool = False) -> list[bytes]:
    payloads = [_png_bytes("red", (11, 7)), _png_bytes("blue", (9, 13))]
    rows = []
    for index, payload in enumerate(payloads):
        instance_id = "instance-0" if duplicate_ids else f"instance-{index}"
        rows.append(
            {
                "images": [{"bytes": payload, "path": None}],
                "image_sizes": [
                    {
                        "width": 11 if index == 0 else 9,
                        "height": 7 if index == 0 else 13,
                    }
                ],
                "prompt_answer": f"<image>fixture question {index}",
                "answer_gt": json.dumps({"type": "integer", "value": index}),
                "instance_id": instance_id,
                "domain": "fixture",
                "task": "task_fixture__scene__objective",
            }
        )
    schema = pa.schema(
        [
            (
                "images",
                pa.list_(pa.struct([("bytes", pa.binary()), ("path", pa.string())])),
            ),
            (
                "image_sizes",
                pa.list_(pa.struct([("width", pa.int64()), ("height", pa.int64())])),
            ),
            ("prompt_answer", pa.string()),
            ("answer_gt", pa.string()),
            ("instance_id", pa.string()),
            ("domain", pa.string()),
            ("task", pa.string()),
        ]
    )
    pq.write_table(pa.Table.from_pylist(rows, schema=schema), path)
    return payloads


def test_prepare_preserves_embedded_bytes_and_writes_stable_manifest(tmp_path: Path):
    parquet_path = tmp_path / "validation.parquet"
    original_payloads = _write_fixture_parquet(parquet_path)
    parquet_sha256 = prepare.sha256_file(parquet_path)
    output_root = tmp_path / "prepared"

    manifest_path = prepare.prepare_dataset(
        parquet_path,
        output_root,
        dataset_repo_id="fixture/trace",
        dataset_revision="a" * 40,
        dataset_file="data/validation.parquet",
        expected_file_sha256=parquet_sha256,
        expected_rows=2,
    )
    first_manifest_bytes = manifest_path.read_bytes()
    manifest = prepare.load_manifest(
        manifest_path,
        expected_rows=2,
        require_pinned=False,
        verify_media=True,
    )

    assert manifest["dataset"]["file_sha256"] == parquet_sha256
    assert [row["row_index"] for row in manifest["rows"]] == [0, 1]
    assert [row["answer_gt"] for row in manifest["rows"]] == [
        {"type": "integer", "value": 0},
        {"type": "integer", "value": 1},
    ]
    for row, original in zip(manifest["rows"], original_payloads):
        image = row["images"][0]
        prepared_path = manifest_path.parent / image["relative_path"]
        assert prepared_path.read_bytes() == original
        assert image["sha256"] == prepare.sha256_bytes(original)
        assert image["size_bytes"] == len(original)
        assert image["format"] == "PNG"
        assert image["mime_type"] == "image/png"

    second_path = prepare.prepare_dataset(
        parquet_path,
        output_root,
        dataset_repo_id="fixture/trace",
        dataset_revision="a" * 40,
        dataset_file="data/validation.parquet",
        expected_file_sha256=parquet_sha256,
        expected_rows=2,
    )
    assert second_path.read_bytes() == first_manifest_bytes


def test_prepare_rejects_wrong_source_hash_before_materializing(tmp_path: Path):
    parquet_path = tmp_path / "validation.parquet"
    _write_fixture_parquet(parquet_path)

    with pytest.raises(RuntimeError, match="parquet SHA-256 mismatch"):
        prepare.prepare_dataset(
            parquet_path,
            tmp_path / "prepared",
            expected_file_sha256="0" * 64,
            expected_rows=2,
        )
    assert not (tmp_path / "prepared" / prepare.MANIFEST_NAME).exists()


def test_prepare_rejects_duplicate_instance_ids(tmp_path: Path):
    parquet_path = tmp_path / "validation.parquet"
    _write_fixture_parquet(parquet_path, duplicate_ids=True)

    with pytest.raises(RuntimeError, match="duplicate TRACE instance_id"):
        prepare.prepare_dataset(
            parquet_path,
            tmp_path / "prepared",
            expected_file_sha256=prepare.sha256_file(parquet_path),
            expected_rows=2,
        )


def test_manifest_verification_detects_media_drift(tmp_path: Path):
    parquet_path = tmp_path / "validation.parquet"
    _write_fixture_parquet(parquet_path)
    manifest_path = prepare.prepare_dataset(
        parquet_path,
        tmp_path / "prepared",
        dataset_repo_id="fixture/trace",
        dataset_revision="a" * 40,
        dataset_file="data/validation.parquet",
        expected_file_sha256=prepare.sha256_file(parquet_path),
        expected_rows=2,
    )
    manifest = prepare.load_manifest(
        manifest_path,
        expected_rows=2,
        require_pinned=False,
    )
    image_path = manifest_path.parent / manifest["rows"][0]["images"][0]["relative_path"]
    image_path.write_bytes(b"corrupt")

    with pytest.raises(RuntimeError, match="image size changed"):
        prepare.load_manifest(
            manifest_path,
            expected_rows=2,
            require_pinned=False,
            verify_media=True,
        )
