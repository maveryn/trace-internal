from __future__ import annotations

import json
from pathlib import Path

from PIL import Image


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def _make_run_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "runs" / "external_benchmarks" / "qwen25vl7b" / "20260522T062435Z"
    _write_json(
        root / "RUN_MANIFEST.json",
        {
            "run_id": "20260522T062435Z",
            "model_id": "Qwen/Qwen2.5-VL-7B-Instruct",
        },
    )
    bench = root / "countqa"
    image_path = bench / "images" / "sample_0.jpg"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (120, 80), (220, 230, 240)).save(image_path)
    _write_json(
        bench / "run_summary.json",
        {
            "benchmark": "countqa",
            "display": "CountQA",
            "model_id": "Qwen/Qwen2.5-VL-7B-Instruct",
            "datetime": "20260522T114551Z",
        },
    )
    _write_jsonl(
        bench / "20260522T114551Z_samples_countqa_qwen25_zs.jsonl",
        [
            {
                "doc_id": 0,
                "input": "How many tiles are on the wall?",
                "filtered_resps": ["12"],
                "target": "18",
                "exact_match": 0.0,
                "image": str(image_path),
            },
            {
                "doc_id": 1,
                "input": "How many lamps are visible?",
                "filtered_resps": ["3"],
                "target": "3",
                "exact_match": 1.0,
                "image": str(image_path),
            },
        ],
    )
    return root


def _add_mmmu_fixture(root: Path) -> None:
    bench = root / "mmmu_pro_vision"
    image_path = bench / "images" / "sample_0.jpg"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (140, 90), (235, 238, 244)).save(image_path)
    _write_json(
        bench / "run_summary.json",
        {
            "benchmark": "mmmu_pro_vision",
            "display": "MMMU-ProVis",
            "model_id": "Qwen/Qwen2.5-VL-7B-Instruct",
            "datetime": "20260522T063740Z",
        },
    )
    _write_jsonl(
        bench / "20260522T063740Z_samples_mmmu_pro_vision_qwen3_zs.jsonl",
        [
            {
                "doc_id": 12,
                "input": "Please answer with the option letter from the given choices.",
                "filtered_resps": ["B"],
                "target": "C",
                "individual_score": 0.0,
                "mmmu_acc": {
                    "id": "test_Biology_321",
                    "subject": "Biology",
                    "answer": "C",
                    "parsed_pred": "B",
                },
                "image": str(image_path),
            },
            {
                "doc_id": 20,
                "input": "Please answer with the option letter from the given choices.",
                "filtered_resps": ["H"],
                "target": "H",
                "individual_score": 1.0,
                "mmmu_acc": {
                    "id": "test_Economics_102",
                    "subject": "Economics",
                    "answer": "H",
                    "parsed_pred": "H",
                },
                "image": str(image_path),
            },
        ],
    )


def test_benchmark_index_reads_scores_and_images(tmp_path: Path) -> None:
    root = _make_run_fixture(tmp_path)

    from apps.benchmark_review.indexing import build_benchmark_index

    index = build_benchmark_index(root, repo_root=tmp_path)

    assert index.model_id == "Qwen/Qwen2.5-VL-7B-Instruct"
    assert list(index.benchmarks) == ["countqa"]
    benchmark = index.benchmarks["countqa"]
    assert benchmark.sample_count == 2
    assert benchmark.correct_count == 1
    assert benchmark.incorrect_count == 1
    assert benchmark.image_count == 2
    assert len(index.media) == 1


def test_benchmark_index_accepts_dataset_only_preview_rows(tmp_path: Path) -> None:
    root = _make_run_fixture(tmp_path)
    bench = root / "charxiv_reasoning"
    image_path = bench / "images" / "sample_0.jpg"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (160, 100), (245, 245, 245)).save(image_path)
    _write_json(
        bench / "run_summary.json",
        {
            "benchmark": "charxiv_reasoning",
            "display": "CharXiv Reasoning",
            "model_id": "dataset-preview/no-model-response",
            "mode": "dataset_only_preview",
        },
    )
    _write_jsonl(
        bench / "charxiv_reasoning_validation_samples.jsonl",
        [
            {
                "doc_id": "validation_00000",
                "input": "Which curve decreases the most?",
                "target": "Method A",
                "filtered_resps": [],
                "image": "images/sample_0.jpg",
            }
        ],
    )

    from apps.benchmark_review.indexing import build_benchmark_index

    index = build_benchmark_index(root, repo_root=tmp_path)

    benchmark = index.benchmarks["charxiv_reasoning"]
    assert benchmark.sample_count == 1
    assert benchmark.unknown_count == 1
    sample = index.samples[index.samples_by_benchmark["charxiv_reasoning"][0]]
    assert sample.status == "unknown"
    assert sample.model_response == ""
    assert sample.target == "Method A"
    assert sample.image_exists is True


def test_benchmark_review_app_serves_filtered_benchmark_page(tmp_path: Path) -> None:
    __import__("pytest").importorskip("fastapi")
    from fastapi.testclient import TestClient

    root = _make_run_fixture(tmp_path)
    from apps.benchmark_review.server import create_app

    app = create_app(run_root=root, repo_root=tmp_path, token="secret", base_url="/proxy/7861")
    client = TestClient(app)

    assert client.get("/api/index").status_code == 401
    response = client.get("/api/index", headers={"Authorization": "Bearer secret"})
    assert response.status_code == 200
    assert response.json()["sample_count"] == 2

    index_page = client.get("/benchmarks", headers={"Authorization": "Bearer secret"})
    assert index_page.status_code == 200
    assert "CountQA" in index_page.text

    page = client.get("/benchmarks/countqa?filter=incorrect", headers={"Authorization": "Bearer secret"})
    assert page.status_code == 200
    assert "How many tiles are on the wall?" in page.text
    assert "How many lamps are visible?" not in page.text
    assert 'href="/proxy/7861/benchmarks/countqa?filter=correct"' in page.text
    assert 'src="/proxy/7861/media/' in page.text
    assert 'data-row-order-toggle' in page.text
    assert 'data-row-order="original" aria-checked="true"' in page.text
    assert 'data-row-order="shuffle" aria-checked="false"' in page.text
    assert 'data-sample-table' in page.text

    suggestions = client.get("/api/search-suggest?q=tiles", headers={"Authorization": "Bearer secret"})
    assert suggestions.status_code == 200
    assert suggestions.json()["results"][0]["type"] == "sample"


def test_benchmark_review_app_filters_mmmu_by_category(tmp_path: Path) -> None:
    __import__("pytest").importorskip("fastapi")
    from fastapi.testclient import TestClient

    root = _make_run_fixture(tmp_path)
    _add_mmmu_fixture(root)

    from apps.benchmark_review.indexing import build_benchmark_index
    from apps.benchmark_review.server import create_app

    index = build_benchmark_index(root, repo_root=tmp_path)
    benchmark = index.benchmarks["mmmu_pro_vision"]
    assert benchmark.category_counts == {"Biology": 1, "Economics": 1}

    app = create_app(run_root=root, repo_root=tmp_path, token="secret", base_url="/proxy/7861")
    client = TestClient(app)

    page = client.get(
        "/benchmarks/mmmu_pro_vision?filter=all&category=Biology",
        headers={"Authorization": "Bearer secret"},
    )
    assert page.status_code == 200
    assert "Biology (1)" in page.text
    assert "Economics (1)" in page.text
    assert "test_Biology_321" not in page.text
    assert "#12" in page.text
    assert "#20" not in page.text
    assert 'href="/proxy/7861/benchmarks/mmmu_pro_vision?filter=incorrect&amp;category=Biology"' in page.text
