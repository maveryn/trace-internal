#!/usr/bin/env python3
"""Recover local image files for old sampled external-benchmark artifacts.

The original VERO/lmms-eval sample JSONL files sometimes dropped media paths
because sample manifests were built from no-media docs. This script reloads the
same sampled dataset docs, exports their visual inputs, and patches sample rows
with a local ``image`` path for review tooling.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_ROOT = REPO_ROOT / "runs/external_benchmarks/qwen25vl7b/20260522T062435Z"
DEFAULT_BENCHMARKS = ("blink", "erqa", "mathvision", "mathvista_testmini")


def _load_vero_runner():
    scripts_dir = REPO_ROOT / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    import run_vero_sampled_benchmark as runner

    runner.install_vero_import_path(runner.DEFAULT_VERO_ROOT)
    return runner


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    with tmp.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    tmp.replace(path)


def _font(size: int) -> ImageFont.ImageFont:
    for candidate in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        try:
            return ImageFont.truetype(candidate, size=size)
        except Exception:
            pass
    return ImageFont.load_default()


def _fit(image: Image.Image, *, max_width: int, max_height: int) -> Image.Image:
    rgb = image.convert("RGB")
    scale = min(max_width / max(1, rgb.width), max_height / max(1, rgb.height), 1.0)
    if scale >= 0.999:
        return rgb.copy()
    size = (max(1, round(rgb.width * scale)), max(1, round(rgb.height * scale)))
    return rgb.resize(size, Image.Resampling.LANCZOS)


def _contact_sheet(visuals: list[Image.Image]) -> Image.Image:
    if len(visuals) == 1:
        return visuals[0].convert("RGB")

    fitted = [_fit(image, max_width=430, max_height=330) for image in visuals]
    pad = 16
    label_h = 30
    cells = []
    for image in fitted:
        cells.append((max(image.width, 220), image.height + label_h))
    width = pad + sum(w + pad for w, _ in cells)
    height = pad + max(h for _, h in cells) + pad
    sheet = Image.new("RGB", (width, height), (248, 249, 251))
    draw = ImageDraw.Draw(sheet)
    font = _font(16)
    x = pad
    for index, image in enumerate(fitted, start=1):
        cell_w = cells[index - 1][0]
        draw.rounded_rectangle(
            (x, pad, x + cell_w, height - pad),
            radius=8,
            fill=(255, 255, 255),
            outline=(207, 214, 224),
            width=1,
        )
        label = f"image {index}"
        draw.text((x + 10, pad + 7), label, fill=(31, 41, 55), font=font)
        ix = x + (cell_w - image.width) // 2
        iy = pad + label_h + ((height - (2 * pad) - label_h - image.height) // 2)
        sheet.paste(image, (ix, iy))
        x += cell_w + pad
    return sheet


def _sample_files(bench_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in bench_dir.glob("*samples*.jsonl")
        if path.name != "sample_manifest.jsonl"
    )


def _infer_task_name(path: Path, task_names: list[str]) -> str | None:
    if len(task_names) == 1:
        return task_names[0]
    name = path.name
    for task_name in sorted(task_names, key=len, reverse=True):
        if task_name in name:
            return task_name
    return None


def _load_tasks(runner: Any, benchmark: str, task_names: list[str]) -> dict[str, Any]:
    spec = runner.BenchmarkSpec(benchmark, benchmark, tuple(task_names))
    task_dict = runner.load_vero_task_dict(spec, "ERROR")
    return {name: task for name, task in runner.iter_leaf_tasks(task_dict)}


def _visuals_for_task_doc(task: Any, original_index: int) -> list[Image.Image]:
    docs = task.eval_docs
    doc = docs[int(original_index)]
    visuals = task.doc_to_visual(doc)
    return [image.convert("RGB") for image in visuals if image is not None]


def recover_benchmark(run_root: Path, benchmark: str, *, dry_run: bool = False) -> dict[str, Any]:
    runner = _load_vero_runner()
    bench_dir = run_root / benchmark
    manifest_path = bench_dir / "sample_manifest.jsonl"
    if not manifest_path.exists():
        raise FileNotFoundError(manifest_path)

    manifest_rows = _read_jsonl(manifest_path)
    task_names = sorted({str(row["task_name"]) for row in manifest_rows})
    task_by_name = _load_tasks(runner, benchmark, task_names)
    original_by_task_doc = {
        (str(row["task_name"]), int(row["sample_doc_id"])): int(row["original_index"])
        for row in manifest_rows
    }

    images_dir = bench_dir / "images"
    if not dry_run:
        images_dir.mkdir(parents=True, exist_ok=True)

    visuals_cache: dict[tuple[str, int], tuple[str, list[str], int]] = {}
    image_manifest: list[dict[str, Any]] = []
    patched_rows = 0
    missing_rows = 0
    exported_images = 0

    for sample_path in _sample_files(bench_dir):
        task_name = _infer_task_name(sample_path, task_names)
        rows = _read_jsonl(sample_path)
        changed = False
        for row in rows:
            if row.get("image") and Path(str(row["image"])).exists():
                continue
            row_task_name = task_name
            if row_task_name is None:
                # Multi-task sample files should be inferable from the filename.
                missing_rows += 1
                continue
            doc_id = int(row["doc_id"])
            key = (row_task_name, doc_id)
            if benchmark == "mathvista_testmini":
                # The saved MathVista generation/direct-judge sample files use
                # dataset row ids directly. The side manifest was produced from
                # a separate judge-task sampling pass and does not align with
                # those files.
                original_index = doc_id
            else:
                original_index = original_by_task_doc.get(key)
            if original_index is None:
                missing_rows += 1
                continue
            if key not in visuals_cache:
                task = task_by_name[row_task_name]
                visuals = _visuals_for_task_doc(task, original_index)
                if not visuals:
                    missing_rows += 1
                    continue
                stem = f"{row_task_name}_{doc_id:04d}"
                individual_paths: list[str] = []
                if not dry_run:
                    for visual_index, visual in enumerate(visuals, start=1):
                        path = images_dir / f"{stem}_input{visual_index}.jpg"
                        visual.save(path, format="JPEG", quality=90)
                        individual_paths.append(str(path))
                else:
                    individual_paths = [str(images_dir / f"{stem}_input{i}.jpg") for i in range(1, len(visuals) + 1)]
                display_path = images_dir / f"{stem}.jpg"
                if not dry_run:
                    _contact_sheet(visuals).save(display_path, format="JPEG", quality=90)
                visuals_cache[key] = (str(display_path), individual_paths, len(visuals))
                exported_images += 1 + len(visuals)
                image_manifest.append(
                    {
                        "benchmark": benchmark,
                        "task_name": row_task_name,
                        "sample_doc_id": doc_id,
                        "original_index": original_index,
                        "image": str(display_path),
                        "input_images": individual_paths,
                        "visual_count": len(visuals),
                    }
                )
            display_path, individual_paths, visual_count = visuals_cache[key]
            row["image"] = display_path
            row["recovered_input_images"] = individual_paths
            row["image_recovery"] = {
                "source": "scripts/recover_external_benchmark_images.py",
                "task_name": row_task_name,
                "sample_doc_id": doc_id,
                "original_index": original_index,
                "visual_count": visual_count,
                "display_image": "contact_sheet" if visual_count > 1 else "single_image",
            }
            patched_rows += 1
            changed = True
        if changed and not dry_run:
            _write_jsonl(sample_path, rows)

    if not dry_run:
        _write_jsonl(bench_dir / "image_manifest.jsonl", image_manifest)

    return {
        "benchmark": benchmark,
        "tasks": len(task_names),
        "sample_files": len(_sample_files(bench_dir)),
        "patched_rows": patched_rows,
        "missing_rows": missing_rows,
        "exported_image_files": exported_images,
        "unique_recovered_samples": len(visuals_cache),
        "dry_run": dry_run,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--benchmarks", nargs="+", default=list(DEFAULT_BENCHMARKS))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    summaries = []
    for benchmark in args.benchmarks:
        summaries.append(recover_benchmark(args.run_root, benchmark, dry_run=args.dry_run))
    print(json.dumps(summaries, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
