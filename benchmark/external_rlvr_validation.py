"""One-shot external benchmark builder for RLVR validation packs."""

from __future__ import annotations

import io
import json
import os
import random
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping

import yaml
from datasets import load_dataset
from huggingface_hub import hf_hub_download, list_repo_files
from PIL import Image


ImagePathMode = Literal["relative", "absolute", "dataset_relative"]
ImageStorageMode = Literal["embedded_bytes", "external_files"]
OutputFormat = Literal["jsonl", "parquet"]

_PROMPT_SUFFIXES = {
    "boxed_final_answer": "Provide only the final answer, wrapped in \\boxed{}.",
    "boxed_option_letter": "Answer with only the single option letter, wrapped in \\boxed{}.",
}


@dataclass(frozen=True)
class ExternalValidationBenchmarkResult:
    benchmark_id: str
    source_ref: str
    split: str
    output_path: Path
    row_count: int
    sample_seed: int


@dataclass(frozen=True)
class ExternalValidationExportResult:
    manifest_path: Path
    output_root: Path
    output_format: OutputFormat
    benchmark_results: tuple[ExternalValidationBenchmarkResult, ...]

    @property
    def benchmark_count(self) -> int:
        return len(self.benchmark_results)

    @property
    def row_count(self) -> int:
        return sum(item.row_count for item in self.benchmark_results)


def _load_manifest(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"expected YAML object in {path}")
    return payload


def _write_jsonl_rows(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), ensure_ascii=False) + "\n")


def _write_parquet_rows(path: Path, rows: list[Mapping[str, Any]]) -> None:
    try:
        import pandas as pd
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("pandas is required to write parquet benchmark exports") from exc

    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame([dict(row) for row in rows])
    frame.to_parquet(path, index=False)


def _resolve_output_path(output_root: Path, benchmark_id: str, output_format: OutputFormat) -> Path:
    filename = f"{benchmark_id}.{'parquet' if output_format == 'parquet' else 'jsonl'}"
    return output_root / filename


def _save_image(image: Image.Image, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    image_to_save = image.convert("RGB") if image.mode not in {"RGB", "L"} else image
    image_to_save.save(destination, format="PNG")


def _encode_image_bytes(image: Image.Image) -> bytes:
    image_to_save = image.convert("RGB") if image.mode not in {"RGB", "L"} else image
    buffer = io.BytesIO()
    image_to_save.save(buffer, format="PNG")
    return buffer.getvalue()


def _format_saved_image_path(
    image_path: Path,
    *,
    output_root: Path,
    image_path_mode: ImagePathMode,
) -> str:
    resolved = image_path.resolve()
    if image_path_mode == "absolute":
        return str(resolved)
    # In this workflow the exported assets live under output_root, so dataset_relative
    # is equivalent to a stable path relative to that root.
    relative = os.path.relpath(str(resolved), start=str(output_root.resolve()))
    return str(Path(relative).as_posix())


def _coerce_choices(raw_choices: Any) -> list[tuple[str, str]] | None:
    if isinstance(raw_choices, Mapping):
        pairs: list[tuple[str, str]] = []
        for key, value in raw_choices.items():
            label = str(key).strip()
            text = str(value).strip()
            if label and text:
                pairs.append((label, text))
        return pairs or None

    if isinstance(raw_choices, list):
        pairs = []
        for index, value in enumerate(raw_choices):
            text = str(value).strip()
            if text:
                pairs.append((chr(ord("A") + index), text))
        return pairs or None

    return None


def _normalize_ground_truth(raw_ground_truth: Any) -> list[str]:
    if isinstance(raw_ground_truth, (list, tuple)):
        values = [str(item).strip() for item in raw_ground_truth if str(item).strip()]
        return values
    text = str(raw_ground_truth).strip() if raw_ground_truth is not None else ""
    return [text] if text else []


def _build_prompt(prompt: str, *, choices: list[tuple[str, str]] | None, prompt_suffix_style: str) -> str:
    suffix = _PROMPT_SUFFIXES.get(prompt_suffix_style)
    if suffix is None:
        raise ValueError(f"unsupported prompt suffix style: {prompt_suffix_style}")

    prompt_text = prompt.strip()
    if choices:
        prompt_text = f"{prompt_text}\n\n" + "\n".join(f"{label}. {text}" for label, text in choices)
    return f"{prompt_text.rstrip()}\n\n{suffix}"


def _sample_indices(total_count: int, sample_count: int, sample_seed: int) -> list[int]:
    if sample_count <= 0:
        raise ValueError(f"sample_count must be positive, got {sample_count}")
    if total_count < sample_count:
        raise ValueError(f"requested {sample_count} rows but source only has {total_count} rows")
    if total_count == sample_count:
        return list(range(total_count))
    rng = random.Random(sample_seed)
    return sorted(rng.sample(range(total_count), sample_count))


def _load_hf_split(repo_id: str, config_name: str | None, split: str):
    if config_name:
        return load_dataset(repo_id, config_name, split=split)
    return load_dataset(repo_id, split=split)


def _is_placeholder_choice_list(options: Any) -> bool:
    if not isinstance(options, list) or not options:
        return False
    expected = [chr(ord("A") + i) for i in range(len(options))]
    actual = [str(item).strip().upper() for item in options]
    return actual == expected


def _find_choice_letter(options: list[Any], answer_text: str) -> str | None:
    normalized = answer_text.strip()
    for index, option in enumerate(options):
        if str(option).strip() == normalized:
            return chr(ord("A") + index)
    return None


def _select_mathvista_rows(spec: Mapping[str, Any]) -> list[dict[str, Any]]:
    ds = _load_hf_split(str(spec["repo_id"]), spec.get("config_name"), str(spec["split"]))
    valid_indices = [index for index in range(len(ds)) if str(ds[index].get("answer", "")).strip()]
    selected = _sample_indices(len(valid_indices), int(spec["sample_count"]), int(spec["sample_seed"]))
    rows: list[dict[str, Any]] = []
    for rank, valid_position in enumerate(selected):
        source_row = ds[valid_indices[valid_position]]
        image = source_row.get("decoded_image")
        if image is None or not hasattr(image, "save"):
            continue
        rows.append(
            {
                "source_id": str(source_row.get("pid", rank)),
                "prompt": str(source_row.get("query") or source_row.get("question") or "").strip(),
                "ground_truth": str(source_row.get("answer", "")).strip(),
                "_images": [image],
                "metadata": {
                    "question_type": source_row.get("question_type"),
                    "answer_type": source_row.get("answer_type"),
                    "unit": source_row.get("unit"),
                },
            }
        )
    return rows


def _select_mathvision_rows(spec: Mapping[str, Any]) -> list[dict[str, Any]]:
    ds = _load_hf_split(str(spec["repo_id"]), spec.get("config_name"), str(spec["split"]))
    selected = _sample_indices(len(ds), int(spec["sample_count"]), int(spec["sample_seed"]))
    rows: list[dict[str, Any]] = []
    for index in selected:
        source_row = ds[index]
        image = source_row.get("decoded_image")
        if image is None or not hasattr(image, "save"):
            continue
        raw_prompt = str(source_row.get("question", "")).replace("<image1>", "<image>").strip()
        raw_options = source_row.get("options")
        choices = None if _is_placeholder_choice_list(raw_options) else _coerce_choices(raw_options)
        rows.append(
            {
                "source_id": str(source_row.get("id", index)),
                "prompt": raw_prompt,
                "choices": choices,
                "ground_truth": str(source_row.get("answer", "")).strip(),
                "_images": [image],
                "metadata": {
                    "subject": source_row.get("subject"),
                    "level": source_row.get("level"),
                },
            }
        )
    return rows


def _select_charxiv_rows(spec: Mapping[str, Any]) -> list[dict[str, Any]]:
    ds = _load_hf_split(str(spec["repo_id"]), spec.get("config_name"), str(spec["split"]))
    valid_indices = []
    for index in range(len(ds)):
        source_row = ds[index]
        if source_row.get("reasoning_a") is not None:
            valid_indices.append(index)
    selected = _sample_indices(len(valid_indices), int(spec["sample_count"]), int(spec["sample_seed"]))
    rows: list[dict[str, Any]] = []
    for valid_position in selected:
        source_row = ds[valid_indices[valid_position]]
        image = source_row.get("image")
        if image is None or not hasattr(image, "save"):
            continue
        rows.append(
            {
                "source_id": str(source_row.get("original_id", valid_position)),
                "prompt": str(source_row.get("reasoning_q", "")).strip(),
                "ground_truth": str(source_row.get("reasoning_a", "")).strip(),
                "_images": [image],
                "metadata": {
                    "category": source_row.get("category"),
                    "reasoning_q_source": source_row.get("reasoning_q_source"),
                    "reasoning_a_type": source_row.get("reasoning_a_type"),
                },
            }
        )
    return rows


def _select_ocrbenchv2_rows(spec: Mapping[str, Any]) -> list[dict[str, Any]]:
    ds = _load_hf_split(str(spec["repo_id"]), spec.get("config_name"), str(spec["split"]))
    selected = _sample_indices(len(ds), int(spec["sample_count"]), int(spec["sample_seed"]))
    rows: list[dict[str, Any]] = []
    for index in selected:
        source_row = ds[index]
        image = source_row.get("image")
        if image is None or not hasattr(image, "save"):
            continue
        answers = source_row.get("answers")
        ground_truth = list(answers) if isinstance(answers, list) else str(answers).strip()
        rows.append(
            {
                "source_id": str(source_row.get("id", index)),
                "prompt": str(source_row.get("question", "")).strip(),
                "ground_truth": ground_truth,
                "_images": [image],
                "metadata": {
                    "dataset_name": source_row.get("dataset_name"),
                    "type": source_row.get("type"),
                },
            }
        )
    return rows


def _select_seephys_rows(spec: Mapping[str, Any]) -> list[dict[str, Any]]:
    ds = _load_hf_split(str(spec["repo_id"]), spec.get("config_name"), str(spec["split"]))
    selected = _sample_indices(len(ds), int(spec["sample_count"]), int(spec["sample_seed"]))
    rows: list[dict[str, Any]] = []
    for index in selected:
        source_row = ds[index]
        images = [image for image in source_row.get("images", []) if hasattr(image, "save")]
        if not images:
            continue
        rows.append(
            {
                "source_id": str(source_row.get("index", index)),
                "prompt": str(source_row.get("question", "")).strip(),
                "ground_truth": str(source_row.get("answer", "")).strip(),
                "_images": images,
                "metadata": {
                    "subject": source_row.get("subject"),
                    "level": source_row.get("level"),
                    "img_category": source_row.get("img_category"),
                },
            }
        )
    return rows


def _select_spatialeval_rows(spec: Mapping[str, Any]) -> list[dict[str, Any]]:
    ds = _load_hf_split(str(spec["repo_id"]), spec.get("config_name"), str(spec["split"]))
    selected = _sample_indices(len(ds), int(spec["sample_count"]), int(spec["sample_seed"]))
    rows: list[dict[str, Any]] = []
    for index in selected:
        source_row = ds[index]
        image = source_row.get("image")
        if image is None or not hasattr(image, "save"):
            continue
        rows.append(
            {
                "source_id": str(source_row.get("id", index)),
                "prompt": str(source_row.get("text", "")).strip(),
                "ground_truth": str(source_row.get("oracle_option", "")).strip(),
                "_images": [image],
                "metadata": {
                    "oracle_answer": source_row.get("oracle_answer"),
                    "oracle_full_answer": source_row.get("oracle_full_answer"),
                },
            }
        )
    return rows


def _select_puzzlevqa_rows(spec: Mapping[str, Any]) -> list[dict[str, Any]]:
    ds = _load_hf_split(str(spec["repo_id"]), spec.get("config_name"), str(spec["split"]))
    selected = _sample_indices(len(ds), int(spec["sample_count"]), int(spec["sample_seed"]))
    rows: list[dict[str, Any]] = []
    for index in selected:
        source_row = ds[index]
        image = source_row.get("image")
        if image is None or not hasattr(image, "save"):
            continue
        options = source_row.get("options") or []
        answer_text = str(source_row.get("answer", "")).strip()
        answer_letter = _find_choice_letter(options, answer_text)
        ground_truth = answer_letter or answer_text
        rows.append(
            {
                "source_id": f"{source_row.get('category', 'puzzle')}::{index}",
                "prompt": str(source_row.get("question", "")).strip(),
                "choices": _coerce_choices(options),
                "ground_truth": ground_truth,
                "_images": [image],
                "metadata": {
                    "category": source_row.get("category"),
                    "answer_text": answer_text,
                },
            }
        )
    return rows


def _read_vgcure_records(spec: Mapping[str, Any]) -> list[dict[str, Any]]:
    repo_id = str(spec["repo_id"])
    allowed_tasks = tuple(spec.get("allowed_task_names", []))
    files = [
        path
        for path in list_repo_files(repo_id, repo_type="dataset")
        if path.startswith(f"VGCure/test_samples/{spec['subset']}/") and path.endswith(".json")
    ]
    rows: list[dict[str, Any]] = []
    for path in sorted(files):
        local_path = hf_hub_download(repo_id=repo_id, repo_type="dataset", filename=path)
        with open(local_path, "r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                raw = line.strip()
                if not raw:
                    continue
                payload = json.loads(raw)
                task_block = payload.get("task", {})
                if not isinstance(task_block, Mapping):
                    continue
                for task_name in allowed_tasks:
                    task_payload = task_block.get(task_name)
                    if not isinstance(task_payload, Mapping):
                        continue
                    qa = task_payload.get("qa")
                    if not isinstance(qa, Mapping):
                        continue
                    question = str(qa.get("question", "")).strip()
                    answer = str(qa.get("answer", "")).strip()
                    if not question or not answer:
                        continue
                    rows.append(
                        {
                            "source_id": f"{Path(path).stem}:{payload.get('id', line_number)}:{task_name}",
                            "prompt": question,
                            "ground_truth": answer,
                            "graph_image": str(payload.get("graph_image", "")).strip(),
                            "metadata": {
                                "task_name": task_name,
                                "source_file": path,
                                "subset": spec["subset"],
                            },
                        }
                    )
    return rows


class _VGCureImageResolver:
    def __init__(self, repo_id: str):
        self.repo_id = repo_id
        self._zip_files: dict[str, zipfile.ZipFile] = {}
        self._member_maps: dict[str, dict[str, str]] = {}

    def load(self, graph_image_path: str) -> Image.Image:
        graph_image = Path(graph_image_path)
        zip_repo_path = f"VGCure/images/{graph_image.parent.name}.zip"
        zip_local_path = hf_hub_download(repo_id=self.repo_id, repo_type="dataset", filename=zip_repo_path)
        if zip_repo_path not in self._zip_files:
            archive = zipfile.ZipFile(zip_local_path)
            self._zip_files[zip_repo_path] = archive
            member_map: dict[str, str] = {}
            for member in archive.namelist():
                normalized = member.strip("/")
                member_map[normalized] = member
                member_map[Path(normalized).name] = member
                member_map[str(Path(graph_image_path).as_posix())] = member_map.get(str(Path(graph_image_path).as_posix()), member)
            self._member_maps[zip_repo_path] = member_map

        archive = self._zip_files[zip_repo_path]
        member_map = self._member_maps[zip_repo_path]
        candidates = [
            str(graph_image.as_posix()),
            graph_image.name,
            f"{graph_image.parent.name}/{graph_image.name}",
        ]
        member_name = None
        for candidate in candidates:
            member_name = member_map.get(candidate)
            if member_name is not None:
                break
        if member_name is None:
            for member in archive.namelist():
                normalized = member.strip("/")
                if normalized.endswith(str(graph_image.as_posix())) or normalized.endswith(graph_image.name):
                    member_name = member
                    break
        if member_name is None:
            raise FileNotFoundError(f"could not resolve VGCure image {graph_image_path} inside {zip_repo_path}")

        with archive.open(member_name) as handle:
            data = handle.read()
        return Image.open(io.BytesIO(data)).convert("RGB")


def _select_vgcure_rows(spec: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = _read_vgcure_records(spec)
    selected = _sample_indices(len(rows), int(spec["sample_count"]), int(spec["sample_seed"]))
    resolver = _VGCureImageResolver(str(spec["repo_id"]))
    exported: list[dict[str, Any]] = []
    for index in selected:
        row = rows[index]
        exported.append(
            {
                "source_id": row["source_id"],
                "prompt": row["prompt"],
                "ground_truth": row["ground_truth"],
                "_images": [resolver.load(row["graph_image"])],
                "metadata": row["metadata"],
            }
        )
    return exported


_ADAPTERS = {
    "mathvista": _select_mathvista_rows,
    "mathvision": _select_mathvision_rows,
    "charxiv": _select_charxiv_rows,
    "ocrbenchv2": _select_ocrbenchv2_rows,
    "seephys": _select_seephys_rows,
    "spatialeval": _select_spatialeval_rows,
    "puzzlevqa": _select_puzzlevqa_rows,
    "vgcure": _select_vgcure_rows,
}


def _materialize_rlvr_rows(
    benchmark_id: str,
    rows: list[dict[str, Any]],
    *,
    output_root: Path,
    image_path_mode: ImagePathMode,
    image_storage_mode: ImageStorageMode,
    prompt_suffix_style: str,
    parser_family: str,
) -> list[dict[str, Any]]:
    exported_rows: list[dict[str, Any]] = []
    for row_index, row in enumerate(rows):
        source_id = str(row.get("source_id", f"{benchmark_id}-{row_index:04d}"))
        uid = f"{benchmark_id}::{source_id}"
        saved_images: list[dict[str, Any]] = []
        for image_index, image in enumerate(row.get("_images", [])):
            if image_storage_mode == "embedded_bytes":
                saved_images.append({"bytes": _encode_image_bytes(image), "format": "png"})
                continue
            asset_path = output_root / "assets" / benchmark_id / f"{uid.replace(':', '_')}__{image_index}.png"
            _save_image(image, asset_path)
            saved_images.append({"path": _format_saved_image_path(asset_path, output_root=output_root, image_path_mode=image_path_mode)})

        exported_rows.append(
            {
                "uid": uid,
                "instance_id": uid,
                "benchmark_id": benchmark_id,
                "source_id": source_id,
                "prompt": _build_prompt(
                    str(row["prompt"]),
                    choices=row.get("choices"),
                    prompt_suffix_style=prompt_suffix_style,
                ),
                "prompt_mode": "answer_only",
                "images": saved_images,
                "ground_truth": _normalize_ground_truth(row["ground_truth"]),
                "parser_family": parser_family,
                "metadata": row.get("metadata", {}),
            }
        )
    return exported_rows


def export_external_validation_to_rlvr(
    manifest_path: str | Path,
    *,
    output_root: str | Path,
    output_format: OutputFormat | None = None,
    image_path_mode: ImagePathMode | None = None,
    image_storage_mode: ImageStorageMode | None = None,
) -> ExternalValidationExportResult:
    manifest = _load_manifest(Path(manifest_path).expanduser().resolve())
    defaults = manifest.get("defaults")
    if not isinstance(defaults, Mapping):
        raise ValueError("external validation manifest requires a 'defaults' mapping")
    benchmark_specs = manifest.get("benchmarks")
    if not isinstance(benchmark_specs, list) or not benchmark_specs:
        raise ValueError("external validation manifest requires a non-empty 'benchmarks' list")

    resolved_output_root = Path(output_root).expanduser().resolve()
    resolved_output_root.mkdir(parents=True, exist_ok=True)

    final_output_format: OutputFormat = output_format or str(defaults.get("output_format", "parquet"))
    final_image_path_mode: ImagePathMode = image_path_mode or str(defaults.get("image_path_mode", "relative"))
    default_image_storage_mode: ImageStorageMode = "embedded_bytes" if final_output_format == "parquet" else "external_files"
    final_image_storage_mode: ImageStorageMode = image_storage_mode or str(
        defaults.get("image_storage_mode", default_image_storage_mode)
    )
    if final_output_format == "jsonl" and final_image_storage_mode == "embedded_bytes":
        raise ValueError("embedded_bytes image storage is only supported for parquet exports")

    benchmark_results: list[ExternalValidationBenchmarkResult] = []

    for raw_spec in benchmark_specs:
        if not isinstance(raw_spec, Mapping):
            raise ValueError("each benchmark spec must be a mapping")
        benchmark_id = str(raw_spec.get("benchmark_id", "")).strip()
        adapter_name = str(raw_spec.get("adapter", "")).strip()
        if not benchmark_id or not adapter_name:
            raise ValueError("each benchmark spec requires benchmark_id and adapter")
        adapter = _ADAPTERS.get(adapter_name)
        if adapter is None:
            raise ValueError(f"unsupported benchmark adapter: {adapter_name}")

        merged_spec = dict(defaults)
        merged_spec.update(raw_spec)
        sampled_rows = adapter(merged_spec)
        exported_rows = _materialize_rlvr_rows(
            benchmark_id,
            sampled_rows,
            output_root=resolved_output_root,
            image_path_mode=final_image_path_mode,
            image_storage_mode=final_image_storage_mode,
            prompt_suffix_style=str(merged_spec.get("prompt_suffix_style", "boxed_final_answer")),
            parser_family=str(merged_spec.get("parser_family", "generic")),
        )

        output_path = _resolve_output_path(resolved_output_root, benchmark_id, final_output_format)
        if final_output_format == "jsonl":
            _write_jsonl_rows(output_path, exported_rows)
        else:
            _write_parquet_rows(output_path, exported_rows)

        benchmark_results.append(
            ExternalValidationBenchmarkResult(
                benchmark_id=benchmark_id,
                source_ref=str(merged_spec.get("repo_id", "")),
                split=str(merged_spec.get("split", "")),
                output_path=output_path,
                row_count=len(exported_rows),
                sample_seed=int(merged_spec.get("sample_seed", defaults.get("sample_seed", 0))),
            )
        )

    return ExternalValidationExportResult(
        manifest_path=Path(manifest_path).expanduser().resolve(),
        output_root=resolved_output_root,
        output_format=final_output_format,
        benchmark_results=tuple(benchmark_results),
    )
