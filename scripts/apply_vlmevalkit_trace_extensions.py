#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VLMEVAL_ROOT = REPO_ROOT / "external" / "VLMEvalKit"
EXT_ROOT = REPO_ROOT / "rlvr" / "vlmevalkit_extensions"


def insert_once(text: str, needle: str, line: str) -> str:
    if line in text:
        return text
    if needle not in text:
        raise RuntimeError(f"Could not find insertion anchor: {needle}")
    return text.replace(needle, f"{needle}\n{line}", 1)


def replace_once(text: str, old: str, new: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise RuntimeError(f"Could not find replacement anchor: {old}")
    return text.replace(old, new, 1)


def insert_symbol_once(text: str, anchor: str, symbol: str, present: str) -> str:
    if present in text:
        return text
    if anchor not in text:
        raise RuntimeError(f"Could not find insertion anchor: {anchor}")
    return text.replace(anchor, f"{anchor} {symbol},", 1)


def apply_extensions(vlmeval_root: Path) -> None:
    dataset_root = vlmeval_root / "vlmeval" / "dataset"
    if not dataset_root.exists():
        raise RuntimeError(f"VLMEvalKit dataset directory does not exist: {dataset_root}")
    scripts_root = vlmeval_root / "scripts"
    if not scripts_root.exists():
        raise RuntimeError(f"VLMEvalKit scripts directory does not exist: {scripts_root}")

    for name in ("trace_local_vqa.py", "visiongraph.py", "evochart.py", "mirage.py"):
        shutil.copy2(EXT_ROOT / name, dataset_root / name)
    for name in ("batched_chartmuseum_vllm.py", "batched_chartqapro_vllm.py", "batched_vlmevalkit_qwen3vl.py"):
        shutil.copy2(EXT_ROOT / "scripts" / name, scripts_root / name)

    init_path = dataset_root / "__init__.py"
    text = init_path.read_text()
    text = insert_once(
        text,
        "from .text_mcq import CustomTextMCQDataset, TextMCQDataset",
        "from .trace_local_vqa import CountQA, GameQALite",
    )
    text = insert_once(
        text,
        "from .viewspatialbench import ViewSpatialBench",
        "from .visiongraph import VisionGraphQ3",
    )
    text = insert_once(
        text,
        "from .erqabench import ERQABench",
        "from .evochart import EvoChart",
    )
    text = insert_once(
        text,
        "from .mindcubebench import MindCubeBench",
        "from .mirage import MIRAGE",
    )
    text = insert_symbol_once(
        text,
        "ChartMuseum, ChartQAPro,",
        "EvoChart",
        "ChartMuseum, ChartQAPro, EvoChart,",
    )
    text = insert_symbol_once(
        text,
        "ReasonMap_Plus,",
        "CountQA, GameQALite",
        "ReasonMap_Plus, CountQA, GameQALite,",
    )
    text = insert_symbol_once(
        text,
        "MMRarebenchDiagnosis, MMRarebenchTreatment, MMRarebenchCrossmodal, MMRarebenchExamination,",
        "VisionGraphQ3",
        "VisionGraphQ3,",
    )
    text = insert_symbol_once(
        text,
        "VisionGraphQ3,",
        "MIRAGE",
        "VisionGraphQ3, MIRAGE,",
    )
    init_path.write_text(text)


def main() -> None:
    parser = argparse.ArgumentParser(description="Install TRACE local VLMEvalKit dataset extensions.")
    parser.add_argument("--vlmeval-root", type=Path, default=DEFAULT_VLMEVAL_ROOT)
    args = parser.parse_args()
    apply_extensions(args.vlmeval_root.resolve())
    print(f"Installed TRACE VLMEvalKit extensions into {args.vlmeval_root}")


if __name__ == "__main__":
    main()
