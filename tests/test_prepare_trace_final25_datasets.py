from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import pandas as pd
import pytest
from PIL import Image

from scripts import prepare_trace_final25_datasets as prepare
from scripts import final25_media_contract as media_contract


class FakeDataset:
    def __init__(self, paths: list[Path]):
        self.data = pd.DataFrame(
            [{"index": index, "image_path": str(path)} for index, path in enumerate(paths)]
        )
        self.trace_normalization = {"fixture": True}

    def build_prompt(self, row):
        return [
            {"type": "image", "value": row["image_path"]},
            {"type": "text", "value": "question"},
        ]


def test_all26_selection_is_frozen_plus_mmvp():
    suite = json.loads(prepare.DEFAULT_SUITE_PATH.read_text(encoding="utf-8"))
    keys = prepare._selected_keys(suite, "all26", [])
    assert len(keys) == 26
    assert keys.count("countqa") == 1
    assert keys.count("mmvp") == 1


def test_frozen_snapshot_is_not_coupled_to_provisional_mmvp():
    datasets = {
        "frozen": {"status": "ready", "dataset_snapshot_sha256": "a" * 64},
        "mmvp": {"status": "ready", "dataset_snapshot_sha256": "b" * 64},
    }
    first = prepare.manifest_snapshot_sha256(
        suite_sha256="c" * 64,
        vlmevalkit_commit="d" * 40,
        datasets=datasets,
        keys=["frozen"],
    )
    datasets["mmvp"]["dataset_snapshot_sha256"] = "e" * 64
    second = prepare.manifest_snapshot_sha256(
        suite_sha256="c" * 64,
        vlmevalkit_commit="d" * 40,
        datasets=datasets,
        keys=["frozen"],
    )

    assert first == second


def test_manifest_loader_recomputes_row_and_dataset_hashes(tmp_path: Path):
    media = [{"type": "image", "sha256": "a" * 64}]
    media_hash = media_contract.media_set_sha256(media)
    row = {
        "ordinal": 0,
        "index": "0",
        "source_row_hash": "b" * 64,
        "media": media,
        "media_set_sha256": media_hash,
        "source_record_sha256": media_contract.source_record_sha256("b" * 64, media_hash),
    }
    receipt = {
        "status": "ready",
        "row_media": [row],
        "dataset_snapshot_sha256": media_contract.dataset_snapshot_sha256([row]),
    }
    datasets = {"fixture": receipt}
    snapshot = media_contract.manifest_snapshot_sha256(
        suite_sha256="c" * 64,
        vlmevalkit_commit="d" * 40,
        datasets=datasets,
        keys=["fixture"],
    )
    manifest = {
        "schema_version": media_contract.DATASET_MANIFEST_SCHEMA,
        "suite_sha256": "c" * 64,
        "vlmevalkit_commit": "d" * 40,
        "datasets": datasets,
        "dataset_views": {"frozen": ["fixture"]},
        "view_snapshot_sha256": {"frozen": snapshot},
        "dataset_snapshot_sha256": snapshot,
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    media_contract.load_dataset_manifest(path)

    manifest["datasets"]["fixture"]["row_media"][0]["media"][0]["sha256"] = "e" * 64
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(RuntimeError, match="corrupt row media hash"):
        media_contract.load_dataset_manifest(path)


def test_materialize_walks_and_decodes_every_prompt_image(tmp_path: Path):
    images = []
    for index in range(2):
        path = tmp_path / "images" / f"{index}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (8 + index, 9), color=(index, 0, 0)).save(path)
        images.append(path)
    (tmp_path / "Fixture.tsv").write_text("fixture\n", encoding="utf-8")

    with mock.patch.object(prepare, "_build_dataset", return_value=FakeDataset(images)):
        receipt = prepare._materialize_dataset(
            key="fixture",
            alias="Fixture",
            expected_rows=2,
            lmu_root=tmp_path,
            workers=2,
            token=None,
        )

    assert receipt["status"] == "ready"
    assert receipt["rows"] == 2
    assert receipt["unique_media"] == 2
    assert [item["width"] for item in receipt["media_files"]] == [8, 9]
    assert all(len(item["sha256"]) == 64 for item in receipt["media_files"])
    assert len(receipt["row_media"]) == 2
    assert all(len(row["media_set_sha256"]) == 64 for row in receipt["row_media"])
    assert all(len(row["source_record_sha256"]) == 64 for row in receipt["row_media"])
    assert len(receipt["dataset_snapshot_sha256"]) == 64
    assert prepare._receipt_is_complete(receipt, alias="Fixture", expected_rows=2)

    images[0].write_bytes(b"broken")
    assert not prepare._receipt_is_complete(receipt, alias="Fixture", expected_rows=2)


def test_materialize_rejects_rows_without_media(tmp_path: Path):
    class MissingMediaDataset:
        data = pd.DataFrame([{"index": "missing"}])

        @staticmethod
        def build_prompt(row):
            return [{"type": "text", "value": "question"}]

    (tmp_path / "Fixture.tsv").write_text("fixture\n", encoding="utf-8")
    with mock.patch.object(prepare, "_build_dataset", return_value=MissingMediaDataset()):
        with pytest.raises(RuntimeError, match="rows without prompt media"):
            prepare._materialize_dataset(
                key="fixture",
                alias="Fixture",
                expected_rows=1,
                lmu_root=tmp_path,
                workers=1,
                token=None,
            )


def test_materialize_supports_duplicate_index_and_nonmedia_rows_by_ordinal(tmp_path: Path):
    image_paths = []
    for name, color in (("a.png", "red"), ("b.png", "blue")):
        path = tmp_path / name
        Image.new("RGB", (6, 6), color).save(path)
        image_paths.append(path)
    (tmp_path / "Fixture.tsv").write_text("fixture\n", encoding="utf-8")

    class DuplicateDataset:
        data = pd.DataFrame(
            [
                {"index": "same", "question": "same", "image_path": str(path)}
                for path in image_paths
            ]
        )

        @staticmethod
        def build_prompt(row):
            return [{"type": "image", "value": row["image_path"]}]

    with mock.patch.object(prepare, "_build_dataset", return_value=DuplicateDataset()):
        receipt = prepare._materialize_dataset(
            key="fixture",
            alias="Fixture",
            expected_rows=2,
            lmu_root=tmp_path,
            workers=1,
            token=None,
        )

    assert [row["ordinal"] for row in receipt["row_media"]] == [0, 1]
    assert receipt["row_media"][0]["source_row_hash"] == receipt["row_media"][1]["source_row_hash"]
    assert receipt["row_media"][0]["media_set_sha256"] != receipt["row_media"][1]["media_set_sha256"]


def test_materialize_repairs_a_truncated_decoded_image(tmp_path: Path):
    image_path = tmp_path / "images" / "0.png"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"truncated-png")
    (tmp_path / "Fixture.tsv").write_text("fixture\n", encoding="utf-8")

    class RecoveringDataset:
        data = pd.DataFrame([{"index": "0", "image_path": str(image_path)}])

        @staticmethod
        def build_prompt(row):
            path = Path(row["image_path"])
            if not path.exists():
                Image.new("RGB", (11, 7), color=(1, 2, 3)).save(path)
            return [{"type": "image", "value": str(path)}]

    with mock.patch.object(prepare, "_build_dataset", return_value=RecoveringDataset()):
        receipt = prepare._materialize_dataset(
            key="fixture",
            alias="Fixture",
            expected_rows=1,
            lmu_root=tmp_path,
            workers=1,
            token=None,
        )

    assert receipt["media_files"][0]["width"] == 11
    assert receipt["media_files"][0]["height"] == 7


def test_metadata_files_include_concat_dataset_children(tmp_path: Path):
    child_paths = []
    dataset_map = {}
    for name in ("Mobile", "Desktop", "Web"):
        path = tmp_path / f"ScreenSpot_{name}.tsv"
        path.write_text(name, encoding="utf-8")
        child_paths.append(path.resolve())
        dataset_map[name] = type("Child", (), {"data_path": str(path)})()
    concat = type("Concat", (), {"dataset_map": dataset_map})()

    records = prepare._metadata_files(concat, "ScreenSpot", tmp_path)

    assert {Path(record["path"]) for record in records} == set(child_paths)
