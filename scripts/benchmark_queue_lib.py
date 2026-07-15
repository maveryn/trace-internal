#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import os
import re
import shutil
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VLMEVAL_ROOT = REPO_ROOT / "external" / "VLMEvalKit"
VLMEVAL_ROOT = Path(os.environ.get("VLMEVAL_ROOT", str(DEFAULT_VLMEVAL_ROOT)))
BASE_MODEL = "Qwen/Qwen3-VL-4B-Instruct"
BASE_MODEL_SLUG = "qwen3-vl-4b-instruct"
DEFAULT_RUN_ROOT = REPO_ROOT / "runs"
DEFAULT_BENCHMARK_ROOT = REPO_ROOT / "benchmark"
DEFAULT_QUEUE_ROOT = DEFAULT_BENCHMARK_ROOT / "queues"
BENCHMARK_RUN_SETS = (
    "full",
    "remaining_base",
    "base_all",
    "trace_candidate37_200",
    "trace_grounding",
    "trace_video4",
    "trace_final25",
)
EXTERNAL_EVAL_V1_SUBSET_ROOT = DEFAULT_BENCHMARK_ROOT / "subsets" / "external_eval_v1"
EXTERNAL_EVAL_V1_QUEUE_SUFFIX = "external_eval_v1"
EXTERNAL_EVAL_V1_BENCHMARKS = (
    "chartqapro",
    "charxivreason",
    "mathvista",
    "mmmu_pro_vision",
    "countqa",
    "game_qa_lite",
    "blink",
    "screenspotpro",
)
TRACE_CANDIDATE37_200_SUBSET_ROOT = DEFAULT_BENCHMARK_ROOT / "subsets" / "trace_candidate37_200"
TRACE_CANDIDATE37_200_QUEUE_SUFFIX = "trace_candidate37_200"
TRACE_GROUNDING_SUBSET_ROOT = DEFAULT_BENCHMARK_ROOT / "subsets" / "trace_grounding"
TRACE_CANDIDATE37_200_BENCHMARKS = (
    "chartmuseum",
    "game_qa_lite",
    "mindcubebench_tiny",
    "screenspot",
    "screenspotpro",
    "chartqapro",
    "puzzlevqa",
    "vstarbench",
    "logicvista",
    "omni3dbench",
    "mathvista",
    "visualpuzzles",
    "cvbench_3d",
    "omnispatialbench_manual_cot",
    "wemath",
    "mathvision",
    "refspatial",
    "qspatial_plus",
    "erqa",
    "treebench",
    "countbenchqa",
    "mathverse",
    "charxivreason",
    "countqa",
    "phyx_mini_mc",
    "visulogic",
    "spbench_si_cot",
    "spatialvizbench_cot",
    "mmhelix",
    "physics",
    "tablevqabench",
    "mmmu_pro_vision",
    "blink",
    "seephys",
    "infovqa",
    "charxivdesc",
    "vlmbias",
    "visiongraph_q3",
)

TRACE_GROUNDING_BENCHMARKS = (
    "refspatial_wo_unseen",
    "osworld_g",
    "refcoco",
    "groundingme",
    "tdbench_grounding",
)

TRACE_GROUNDING_COUNTING_EXTRA_BENCHMARKS = (
    "ocrbench_v2_mini",
    "screenspot_v2",
)

TRACE_VIDEO4_BENCHMARKS = (
    "qbench_video",
    "videommmu",
    "video_tt",
    "tempcompass",
)


def parse_lettered_option_blob(value: Any) -> dict[str, str]:
    """Parse a lettered option block stored in one metadata cell.

    Most sources use ``A. ...``, while a few TreeBench OCR rows use a bare
    letter at the beginning of each line. Duplicated source labels retain
    their first value, matching the first visible option with that label.
    """

    if value is None or (isinstance(value, float) and math.isnan(value)):
        return {}
    text = str(value).strip()
    if not text:
        return {}

    markers_by_start: dict[int, tuple[int, str]] = {}
    for marker in re.finditer(r"(?:^|\s)([A-K])[\.\):]\s+", text):
        markers_by_start[marker.start(1)] = (marker.end(), marker.group(1))
    for marker in re.finditer(r"(?m)^\s*([A-K])\s+(?=\S)", text):
        markers_by_start.setdefault(marker.start(1), (marker.end(), marker.group(1)))

    markers = sorted((start, end, letter) for start, (end, letter) in markers_by_start.items())
    options: dict[str, str] = {}
    for pos, (_, value_start, letter) in enumerate(markers):
        value_end = markers[pos + 1][0] if pos + 1 < len(markers) else len(text)
        option = re.sub(r"\s+", " ", text[value_start:value_end]).strip()
        if option:
            options.setdefault(letter, option)
    return options

TRACE_FINAL25_BENCHMARK_CATEGORIES: dict[str, tuple[str, ...]] = {
    "Charts, Tables & Structured Figures": (
        "chartmuseum",
        "chartqapro",
        "charxivreason",
        "tablevqabench",
        "evochart",
    ),
    "Visual Mathematics": ("mathvision", "mathvista", "mathverse", "wemath"),
    "Science & Academic Reasoning": ("phyx_mini_mc", "physics", "mmmu_pro_vision", "mmstar"),
    "Spatial, 3D, Embodied & UI Grounding": ("screenspot", "spatialvizbench_cot", "cvbench_3d", "erqa"),
    "Visual Perception, Counting & Evidence Grounding": ("blink", "countbenchqa", "countqa", "treebench"),
    "Puzzles & Abstract Logic": ("puzzlevqa", "visualpuzzles", "logicvista", "mme_reasoning"),
}
TRACE_FINAL25_BENCHMARKS = tuple(
    key for category_keys in TRACE_FINAL25_BENCHMARK_CATEGORIES.values() for key in category_keys
)

MME_REASONING_TSV_URL = (
    "https://huggingface.co/datasets/InternScience/MME-Reasoning/resolve/main/MME_Reasoning.tsv"
)
MME_REASONING_MD5 = "b243f44778782d3821523689f6b40a1e"


@dataclass(frozen=True)
class BenchmarkSpec:
    key: str
    display: str
    alias: str
    run_name: str
    eval_mode: str = "auto"
    kind: str = "vlmeval"
    split: str | None = None
    max_tokens: int = 16384
    temperature: float = 0.7
    top_p: float = 0.8
    top_k: int = 20
    presence_penalty: float = 1.5
    repetition_penalty: float = 1.0
    max_model_len: int | None = 32768
    max_pixels: int | None = None
    total_pixels: int | None = None
    max_images: int = 24
    max_videos: int = 3
    generation_batch_size: int | None = None
    video_llm: bool = False
    aggregate_group: str | None = None
    aggregate_run_name: str | None = None
    note: str = ""


@dataclass(frozen=True)
class ModelSpec:
    name: str
    slug: str
    path: str
    default_gpus: tuple[str, ...]
    run_set: str


BENCHMARKS: tuple[BenchmarkSpec, ...] = (
    BenchmarkSpec("chartqa", "ChartQA", "ChartQA_TEST", "vlmevalkit_defaults", max_tokens=1024),
    BenchmarkSpec("chartqapro", "ChartQAPro", "ChartQAPro_CoT", "vlmevalkit_faithful_cot"),
    BenchmarkSpec("chartmuseum", "ChartMuseum", "ChartMuseum_test", "vlmevalkit_defaults_qwen32b_judge_test", split="test", eval_mode="chartmuseum_local_judge", max_model_len=32768),
    BenchmarkSpec("charxivdesc", "CharXivDesc", "CharXiv_descriptive_val", "vlmevalkit_defaults_qwen32b_judge"),
    BenchmarkSpec("charxivreason", "CharXivReason", "CharXiv_reasoning_val", "vlmevalkit_defaults_qwen32b_judge"),
    BenchmarkSpec("evochart", "EvoChart", "EvoChart", "vlmevalkit_defaults_qwen32b_judge", eval_mode="evochart_local_judge"),
    BenchmarkSpec("infovqa", "InfoVQA", "InfoVQA_VAL", "vlmevalkit_defaults_val"),
    BenchmarkSpec("mmmu_pro_vision", "MMMU-ProVis", "MMMU_Pro_V_COT", "vlmevalkit_cot_max2048", max_tokens=2048),
    BenchmarkSpec("mathvision", "MathVision", "MathVision", "vlmevalkit_defaults_qwen32b_judge"),
    BenchmarkSpec("mathvista", "MathVista", "MathVista_MINI", "vlmevalkit_defaults_qwen32b_judge"),
    BenchmarkSpec("mathverse", "MathVerse", "MathVerse_MINI_Vision_Only_cot", "vlmevalkit_defaults_qwen32b_judge"),
    BenchmarkSpec("logicvista", "LogicVista", "LogicVista", "vlmevalkit_defaults_qwen32b_judge"),
    BenchmarkSpec("mmesci_en", "MME-SCI EN", "MMESCI_EN", "vlmevalkit_defaults_qwen32b_judge", eval_mode="mmesci_local_judge", max_tokens=4096),
    BenchmarkSpec("scienceqa_test", "ScienceQA TEST", "ScienceQA_TEST", "vlmevalkit_defaults", eval_mode="scienceqa_local_score", max_tokens=4096),
    BenchmarkSpec("wemath", "WeMath", "WeMath_COT", "vlmevalkit_cot_qwen32b_judge", eval_mode="wemath_local_judge", max_tokens=2048),
    BenchmarkSpec("mmhelix", "MM-HELIX", "MM-HELIX", "vlmevalkit_boxed_defaults", eval_mode="mmhelix_local_score", max_tokens=4096),
    BenchmarkSpec("blink", "Blink", "BLINK", "vlmevalkit_defaults"),
    BenchmarkSpec("erqa", "ERQA", "ERQA", "vlmevalkit_defaults"),
    BenchmarkSpec("embspatial", "EmbSpatial", "EmbSpatialBench", "vlmevalkit_defaults"),
    BenchmarkSpec("robospatialhome", "RoboSpatialHome", "RoboSpatialHome", "vlmevalkit_defaults"),
    BenchmarkSpec("game_qa_lite", "Game-QA-Lite", "Game-QA-Lite", "vlmevalkit_cot_boxed"),
    BenchmarkSpec("countqa", "CountQA", "CountQA", "vlmevalkit_cot_boxed"),
    BenchmarkSpec("vstarbench", "VStarBench", "VStarBench", "vlmevalkit_defaults"),
    BenchmarkSpec("screenspotpro_development", "ScreenSpotPro/Development", "ScreenSpot_Pro_Development", "vlmevalkit_defaults_pooled/development", aggregate_group="screenspotpro", aggregate_run_name="vlmevalkit_defaults_pooled"),
    BenchmarkSpec("screenspotpro_creative", "ScreenSpotPro/Creative", "ScreenSpot_Pro_Creative", "vlmevalkit_defaults_pooled/creative", aggregate_group="screenspotpro", aggregate_run_name="vlmevalkit_defaults_pooled"),
    BenchmarkSpec("screenspotpro_cad", "ScreenSpotPro/CAD", "ScreenSpot_Pro_CAD", "vlmevalkit_defaults_pooled/cad", aggregate_group="screenspotpro", aggregate_run_name="vlmevalkit_defaults_pooled"),
    BenchmarkSpec("screenspotpro_scientific", "ScreenSpotPro/Scientific", "ScreenSpot_Pro_Scientific", "vlmevalkit_defaults_pooled/scientific", aggregate_group="screenspotpro", aggregate_run_name="vlmevalkit_defaults_pooled"),
    BenchmarkSpec("screenspotpro_office", "ScreenSpotPro/Office", "ScreenSpot_Pro_Office", "vlmevalkit_defaults_pooled/office", aggregate_group="screenspotpro", aggregate_run_name="vlmevalkit_defaults_pooled"),
    BenchmarkSpec("screenspotpro_os", "ScreenSpotPro/OS", "ScreenSpot_Pro_OS", "vlmevalkit_defaults_pooled/os", aggregate_group="screenspotpro", aggregate_run_name="vlmevalkit_defaults_pooled"),
    BenchmarkSpec("mmstar", "MMStar", "MMStar", "vlmevalkit_defaults"),
    BenchmarkSpec(
        "mme_reasoning",
        "MME-Reasoning",
        "MME-Reasoning",
        "vlmevalkit_defaults_qwen32b_judge",
        eval_mode="mme_reasoning_local_judge",
        max_tokens=4096,
    ),
    BenchmarkSpec("mme_realworld_lite", "MME-RealWorld-Lite", "MME-RealWorld-Lite", "vlmevalkit_defaults"),
    BenchmarkSpec("treebench", "TreeBench", "TreeBench", "vlmevalkit_defaults"),
    BenchmarkSpec("vlmblind", "VLMBlind", "VLMBlind", "vlmevalkit_defaults"),
)

TRACE_CANDIDATE37_EXTRA_BENCHMARKS: tuple[BenchmarkSpec, ...] = (
    BenchmarkSpec("mindcubebench_tiny", "MindCubeBench tiny", "MindCubeBench_tiny_raw_qa", "vlmevalkit_defaults"),
    BenchmarkSpec("screenspot", "ScreenSpot", "ScreenSpot", "vlmevalkit_defaults_sample200", max_tokens=1024),
    BenchmarkSpec("screenspotpro", "ScreenSpot-Pro", "ScreenSpot_Pro", "vlmevalkit_defaults_sample200", max_tokens=1024),
    BenchmarkSpec("puzzlevqa", "PuzzleVQA", "PuzzleVQA", "vlmevalkit_reasoning"),
    BenchmarkSpec("omni3dbench", "Omni3DBench", "Omni3DBench", "vlmevalkit_defaults"),
    BenchmarkSpec("visualpuzzles", "VisualPuzzles", "VisualPuzzles", "vlmevalkit_reasoning"),
    BenchmarkSpec("cvbench_3d", "CV-Bench 3D", "CV-Bench-3D", "vlmevalkit_defaults"),
    BenchmarkSpec("omnispatialbench_manual_cot", "OmniSpatialBench manual CoT", "OmniSpatialBench_manual_cot", "vlmevalkit_cot"),
    BenchmarkSpec("refspatial", "RefSpatial-Bench", "RefSpatial-Bench", "vlmevalkit_defaults"),
    BenchmarkSpec("qspatial_plus", "QSpatial plus", "QSpatial_plus", "vlmevalkit_reasoning"),
    BenchmarkSpec("countbenchqa", "CountBenchQA", "CountBenchQA", "vlmevalkit_defaults"),
    BenchmarkSpec("phyx_mini_mc", "PhyX mini MC", "PhyX_mini_MC", "vlmevalkit_defaults"),
    BenchmarkSpec("visulogic", "VisuLogic", "VisuLogic", "vlmevalkit_reasoning"),
    BenchmarkSpec("spbench_si_cot", "SPBench SI COT", "SPBench-SI_CoT", "vlmevalkit_cot"),
    BenchmarkSpec("spatialvizbench_cot", "SpatialVizBench COT", "SpatialVizBench_CoT", "vlmevalkit_cot"),
    BenchmarkSpec("physics", "Physics", "Physics", "vlmevalkit_reasoning"),
    BenchmarkSpec("tablevqabench", "TableVQABench", "TableVQABench", "vlmevalkit_defaults"),
    BenchmarkSpec("seephys", "SEEPhys", "SeePhys", "vlmevalkit_reasoning"),
    BenchmarkSpec("vlmbias", "VLMBias", "VLMBias", "vlmevalkit_defaults"),
    BenchmarkSpec("visiongraph_q3", "VisionGraph-Q3", "VisionGraph_Q3", "vlmevalkit_q3", max_tokens=2048),
    BenchmarkSpec(
        "qbench_video",
        "QBench-Video",
        "QBench_Video_8frame",
        "vlmevalkit_8frame_temp06",
        max_tokens=4096,
        max_images=8,
        note="Fast video benchmark; VLMEvalKit concatenates MCQ and VQA splits.",
    ),
    BenchmarkSpec(
        "videommmu",
        "VideoMMMU",
        "VideoMMMU_8frame",
        "vlmevalkit_8frame_temp06",
        max_tokens=4096,
        max_images=8,
        note="Gated HF dataset; access must be available via HF_TOKEN.",
    ),
    BenchmarkSpec(
        "video_tt",
        "Video-TT",
        "Video_TT_16frame",
        "vlmevalkit_16frame_temp06",
        max_tokens=4096,
        max_images=16,
    ),
    BenchmarkSpec(
        "tempcompass",
        "TempCompass",
        "TempCompass_8frame",
        "vlmevalkit_8frame_temp06",
        max_tokens=4096,
        max_images=8,
        note="Uses the smallest VLMEvalKit frame-count alias; media payload is small but row count is larger.",
    ),
    BenchmarkSpec("refspatial_wo_unseen", "RefSpatial wo unseen", "RefSpatial_wo_unseen", "vlmevalkit_point_mask", max_tokens=1024),
    BenchmarkSpec("osworld_g", "OSWorld-G", "OSWorld_G", "vlmevalkit_gui_click", max_tokens=1024),
    BenchmarkSpec("refcoco", "RefCOCO", "RefCOCO", "vlmevalkit_bbox_iou", max_tokens=1024),
    BenchmarkSpec("groundingme", "GroundingME", "GroundingME", "vlmevalkit_bbox_iou", max_tokens=1024),
    BenchmarkSpec("tdbench_grounding", "TDBenchGrounding rot0", "tdbench_grounding_rot0", "vlmevalkit_bbox_centroid", max_tokens=1024),
    BenchmarkSpec("ocrbench_v2_mini", "OCRBench v2 MINI", "OCRBench_v2_MINI", "vlmevalkit_defaults", max_tokens=2048),
    BenchmarkSpec("screenspot_v2", "ScreenSpot v2", "ScreenSpot_v2", "vlmevalkit_defaults", max_tokens=1024),
)

ALL_BENCHMARKS: tuple[BenchmarkSpec, ...] = BENCHMARKS + TRACE_CANDIDATE37_EXTRA_BENCHMARKS


ABLATION_MODELS: tuple[ModelSpec, ...] = (
    ModelSpec(
        "Trace alpha0 answer step250",
        "trace-qwen3vl4b-alpha0-answer-step250",
        str(REPO_ROOT / "checkpoints/trace_rlvr_merged_hf/trace_qwen3vl4b_alpha0_answer_step250"),
        ("0", "1"),
        "full",
    ),
    ModelSpec(
        "Trace alpha0.5 answer step250",
        "trace-qwen3vl4b-alpha0-5-answer-step250",
        str(REPO_ROOT / "checkpoints/trace_rlvr_merged_hf/trace_qwen3vl4b_alpha0_5_answer_step250"),
        ("2", "3"),
        "full",
    ),
    ModelSpec(
        "Trace alpha1 answer step250",
        "trace-qwen3vl4b-alpha1-answer-step250",
        str(REPO_ROOT / "checkpoints/trace_rlvr_merged_hf/trace_qwen3vl4b_alpha1_answer_step250"),
        ("4", "5"),
        "full",
    ),
)

BASE_MODEL_SPEC = ModelSpec("Qwen3-VL-4B-Instruct base", BASE_MODEL_SLUG, BASE_MODEL, ("6", "7"), "remaining_base")


def all_model_specs(include_base: bool = True, include_ablations: bool = True) -> list[ModelSpec]:
    out: list[ModelSpec] = []
    if include_base:
        out.append(BASE_MODEL_SPEC)
    if include_ablations:
        out.extend(ABLATION_MODELS)
    return out


def spec_by_key(key: str) -> BenchmarkSpec:
    for spec in ALL_BENCHMARKS:
        if spec.key == key:
            return spec
    raise KeyError(key)


def _repair_treebench_options(dataset: Any) -> list[dict[str, Any]]:
    """Repair a known TreeBench TSV delimiter defect before prompt generation.

    At least one upstream row stores option B at the end of column A and shifts
    the remaining choices left, leaving the ground-truth option absent from the
    generated prompt. The repair is intentionally narrow: it only applies when
    a single-letter ground truth is missing and the preceding option contains
    an explicit marker for the next option.
    """

    import pandas as pd

    def has_value(value: Any) -> bool:
        try:
            if pd.isna(value):
                return False
        except (TypeError, ValueError):
            pass
        return bool(str(value).strip())

    data = dataset.data.copy()
    repairs: list[dict[str, Any]] = []
    option_letters = "ABCDEFGHIJK"
    for row_pos, row in data.iterrows():
        answer = str(row.get("answer", "")).strip().upper()
        if len(answer) != 1 or answer not in option_letters:
            continue
        present = [letter for letter in option_letters if letter in data and has_value(row.get(letter))]
        if answer in present:
            continue

        metadata_options = parse_lettered_option_blob(row.get("multi-choice options"))
        if not present and answer in metadata_options:
            # TreeBench's OCR split deliberately leaves the option columns
            # empty because the model must read the choices from the image.
            # Keep its prompt unchanged; the metadata text is only for scorer
            # validation and answer extraction.
            continue

        repaired = False
        for letter in present:
            if letter == option_letters[-1]:
                continue
            next_letter = option_letters[option_letters.index(letter) + 1]
            value = str(row.get(letter, ""))
            marker = re.search(rf"\s+{re.escape(next_letter)}\.\s+", value)
            if marker is None:
                continue

            prefix = value[: marker.start()].strip()
            embedded = value[marker.end() :].strip()
            if not prefix or not embedded:
                continue

            highest = max(option_letters.index(item) for item in present)
            next_index = option_letters.index(next_letter)
            for option_index in range(highest, next_index - 1, -1):
                source = option_letters[option_index]
                target = option_letters[option_index + 1]
                data.at[row_pos, target] = row.get(source)
            data.at[row_pos, letter] = prefix
            data.at[row_pos, next_letter] = embedded
            repairs.append(
                {
                    "index": str(row.get("index", row_pos)),
                    "split_column": letter,
                    "inserted_column": next_letter,
                    "ground_truth": answer,
                }
            )
            repaired = True
            break

        refreshed = data.loc[row_pos]
        repaired_present = [
            letter for letter in option_letters if letter in data and has_value(refreshed.get(letter))
        ]
        if not repaired or answer not in repaired_present:
            raise ValueError(
                "TreeBench row has a ground-truth option missing from its prompt choices: "
                f"index={row.get('index', row_pos)!r} answer={answer!r} choices={present!r}"
            )

    dataset.data = data
    return repairs


def build_vlmeval_dataset(spec: BenchmarkSpec) -> Any:
    """Build a VLMEvalKit dataset with TRACE's reproducibility fixes applied."""

    if spec.key == "mme_reasoning":
        # Keep the release URL/checksum in the shared builder so Final25
        # generation does not depend on the dedicated scorer's runtime patch.
        from vlmeval.dataset.image_vqa import MMEReasoning

        MMEReasoning.DATASET_URL[spec.alias] = MME_REASONING_TSV_URL
        MMEReasoning.DATASET_MD5 = {spec.alias: MME_REASONING_MD5}

    if spec.key == "erqa":
        # Upstream registers two incompatible classes under the same ``ERQA``
        # alias. Explicit construction avoids registry-order and cache-dependent
        # behavior and pins the 400-row EASI leaderboard benchmark used by TRACE.
        from vlmeval.dataset.erqabench import ERQABench

        dataset = ERQABench(dataset=spec.alias)
    else:
        from vlmeval.dataset import build_dataset

        dataset = build_dataset(spec.alias)
    if dataset is None:
        raise RuntimeError(f"VLMEvalKit could not build dataset {spec.alias}")

    normalization: dict[str, Any] = {}
    if spec.key == "treebench":
        normalization["treebench_option_repairs"] = _repair_treebench_options(dataset)
    dataset.trace_normalization = normalization
    return dataset


def benchmark_dir(spec: BenchmarkSpec, model_slug: str, benchmark_root: Path = DEFAULT_BENCHMARK_ROOT) -> Path:
    key = spec.aggregate_group or spec.key
    run_name = spec.aggregate_run_name if spec.aggregate_group else spec.run_name
    return benchmark_root / key / model_slug / str(run_name)


def run_dir(spec: BenchmarkSpec, model_slug: str, run_root: Path = DEFAULT_RUN_ROOT) -> Path:
    key = spec.aggregate_group or spec.key
    return run_root / key / model_slug / spec.run_name


def score_path(spec: BenchmarkSpec, model_slug: str, benchmark_root: Path = DEFAULT_BENCHMARK_ROOT) -> Path:
    if spec.aggregate_group:
        return benchmark_dir(spec, model_slug, benchmark_root) / f"{spec.key}_scores.json"
    return benchmark_dir(spec, model_slug, benchmark_root) / "scores.json"


def aggregate_score_path(group: str, run_name: str, model_slug: str, benchmark_root: Path = DEFAULT_BENCHMARK_ROOT) -> Path:
    return benchmark_root / group / model_slug / run_name / "scores.json"


def benchmark_specs_for_run_set(run_set: str, model_slug: str = BASE_MODEL_SLUG) -> list[BenchmarkSpec]:
    specs = list(ALL_BENCHMARKS)
    if run_set == "full":
        return specs
    if run_set == "remaining_base":
        return [spec for spec in specs if not score_path(spec, model_slug).exists()]
    if run_set == "base_all":
        return specs
    if run_set == "trace_candidate37_200":
        return [spec_by_key(key) for key in TRACE_CANDIDATE37_200_BENCHMARKS]
    if run_set == "trace_grounding":
        return [spec_by_key(key) for key in TRACE_GROUNDING_BENCHMARKS]
    if run_set == "trace_grounding_counting_extra":
        return [spec_by_key(key) for key in TRACE_GROUNDING_COUNTING_EXTRA_BENCHMARKS]
    if run_set == "trace_video4":
        return [spec_by_key(key) for key in TRACE_VIDEO4_BENCHMARKS]
    if run_set == "trace_final25":
        return [spec_by_key(key) for key in TRACE_FINAL25_BENCHMARKS]
    raise ValueError(f"Unknown run_set {run_set!r}")


def spec_matches_selector(spec: BenchmarkSpec, selector: str) -> bool:
    """Return whether a CLI selector names this spec or its aggregate group."""
    values = {
        spec.key,
        spec.alias,
        spec.display,
        spec.run_name,
    }
    if spec.aggregate_group:
        values.add(spec.aggregate_group)
    if spec.aggregate_run_name:
        values.add(spec.aggregate_run_name)
    return selector in values


def filter_benchmark_specs(
    specs: Iterable[BenchmarkSpec],
    *,
    only: Iterable[str] = (),
    exclude: Iterable[str] = (),
) -> list[BenchmarkSpec]:
    out = list(specs)
    keep = {str(item) for item in only if str(item)}
    if keep:
        out = [spec for spec in out if any(spec_matches_selector(spec, selector) for selector in keep)]
    drop = {str(item) for item in exclude if str(item)}
    if drop:
        out = [spec for spec in out if not any(spec_matches_selector(spec, selector) for selector in drop)]
    return out


def effective_generation_batch_size(
    spec: BenchmarkSpec,
    requested_batch_size: int,
    max_tokens_override: int | None = None,
) -> int:
    max_tokens = spec.max_tokens
    if max_tokens_override is not None and max_tokens_override > 0:
        max_tokens = min(max_tokens, max_tokens_override)
    if spec.generation_batch_size is not None:
        return max(1, min(requested_batch_size, spec.generation_batch_size))
    if spec.video_llm:
        return max(1, min(requested_batch_size, 32))
    if max_tokens_override is not None and max_tokens_override > 0 and max_tokens <= 4096:
        return max(1, requested_batch_size)
    if max_tokens >= 8192:
        return max(1, min(requested_batch_size, 128))
    if max_tokens >= 2048:
        return max(1, min(requested_batch_size, 256))
    return max(1, requested_batch_size)


def local_judge_eval_mode(spec: BenchmarkSpec) -> str | None:
    if spec.kind == "chartmuseum" or spec.key == "chartmuseum" or spec.eval_mode == "chartmuseum_local_judge":
        return "chartmuseum_local_judge"
    if spec.eval_mode == "wemath_local_judge" or spec.alias.startswith("WeMath"):
        return "wemath_local_judge"
    if spec.eval_mode == "evochart_local_judge" or spec.alias == "EvoChart":
        return "evochart_local_judge"
    if spec.alias.startswith("CharXiv_"):
        return "charxiv_local_judge"
    if spec.alias == "MathVision":
        return "mathv_local_judge"
    if spec.alias.startswith("MathVista"):
        return "mathvista_local_judge"
    if spec.alias.startswith("MathVerse"):
        return "mathverse_local_judge"
    if spec.alias == "LogicVista":
        return "logicvista_local_judge"
    if spec.eval_mode == "mmesci_local_judge" or spec.alias == "MMESCI_EN":
        return "mmesci_local_judge"
    if spec.eval_mode == "scienceqa_local_score" or spec.alias == "ScienceQA_TEST":
        return "scienceqa_local_score"
    if spec.alias == "SeePhys":
        return "seephys_local_judge"
    if spec.alias == "Physics":
        return "physics_local_judge"
    return None


def json_default(value: Any) -> Any:
    try:
        import numpy as np

        if isinstance(value, np.integer):
            return int(value)
        if isinstance(value, np.floating):
            return float(value)
        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, np.bool_):
            return bool(value)
    except Exception:
        pass
    return str(value)


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=json_default), encoding="utf-8")
    tmp.replace(path)


@contextmanager
def file_lock(lock_path: Path):
    import fcntl

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def _job_done(job_id: str, done_path: Path | None) -> bool:
    return bool(done_path and done_path.exists())


def _pid_alive(pid: Any) -> bool:
    try:
        pid_int = int(pid)
    except Exception:
        return False
    if pid_int <= 0:
        return False
    try:
        os.kill(pid_int, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def claim_next_job(
    *,
    queue_path: Path,
    jobs: Iterable[tuple[str, Path | None]],
    worker_id: str,
    stale_after_sec: float = 12 * 3600,
    max_attempts: int = 2,
) -> str | None:
    lock_path = queue_path.with_suffix(queue_path.suffix + ".lock")
    now = time.time()
    with file_lock(lock_path):
        state = load_json(queue_path, {"jobs": {}})
        state_jobs = state.setdefault("jobs", {})
        for job_id, done_path in jobs:
            info = state_jobs.get(job_id, {})
            if _job_done(job_id, done_path):
                state_jobs[job_id] = {**info, "status": "done", "done_path": str(done_path), "updated_at": now}
                continue
            attempts = int(info.get("attempts") or 0)
            if info.get("status") == "failed" and attempts >= max_attempts:
                continue
            if info.get("status") == "running":
                if _pid_alive(info.get("pid")):
                    continue
                if now - float(info.get("updated_at", 0)) < stale_after_sec:
                    continue
            if info.get("status") == "done":
                continue
            state_jobs[job_id] = {
                "status": "running",
                "worker": worker_id,
                "pid": os.getpid(),
                "updated_at": now,
                "attempts": attempts + 1,
            }
            write_json(queue_path, state)
            return job_id
        write_json(queue_path, state)
    return None


def mark_job(queue_path: Path, job_id: str, status: str, **extra: Any) -> None:
    now = time.time()
    lock_path = queue_path.with_suffix(queue_path.suffix + ".lock")
    with file_lock(lock_path):
        state = load_json(queue_path, {"jobs": {}})
        state_jobs = state.setdefault("jobs", {})
        previous = state_jobs.get(job_id, {})
        entry = {
            "status": status,
            "worker": extra.pop("worker", None),
            "pid": os.getpid(),
            "updated_at": now,
            **extra,
        }
        if "attempts" not in entry and "attempts" in previous:
            entry["attempts"] = previous["attempts"]
        state_jobs[job_id] = entry
        write_json(queue_path, state)


def score_to_percent(value: Any) -> float | None:
    try:
        score = float(value)
    except Exception:
        return None
    if math.isnan(score):
        return None
    if abs(score) <= 1.0:
        score *= 100.0
    return score


def weighted_prefixed_overall_accuracy(scores: Any) -> tuple[float, int] | None:
    """Compute weighted ScreenSpot-style overall accuracy from grouped metrics.

    VLMEvalKit GUI benchmarks return dictionaries like
    ``ScreenSpot_Mobile:Overall_Accuracy`` plus matching ``*:cnt`` entries.
    The generic numeric fallback is wrong for these dictionaries because it
    averages count fields together with accuracy fields.
    """
    if not isinstance(scores, dict):
        return None
    total = 0.0
    correct = 0.0
    for key, value in scores.items():
        key_str = str(key)
        if not key_str.endswith(":Overall_Accuracy"):
            continue
        try:
            accuracy = float(value)
        except Exception:
            continue
        prefix = key_str[: -len(":Overall_Accuracy")]
        count = 0.0
        for count_key, count_value in scores.items():
            count_key_str = str(count_key)
            if count_key_str.startswith(prefix + ":") and count_key_str.endswith(":cnt"):
                try:
                    count += float(count_value)
                except Exception:
                    pass
        if count <= 0:
            continue
        total += count
        correct += count * accuracy / 100.0
    if total <= 0:
        return None
    return correct / total * 100.0, int(total)


GROUNDING_DATASET_ALIASES = {
    "RefSpatial_wo_unseen",
    "OSWorld_G",
    "RefCOCO",
    "GroundingME",
    "tdbench_grounding_rot0",
}

GROUNDING_HF_DATASET_FILES = {
    "refcoco": ("mjuicem/RefCOCO-VLMEvalKit", "RefCOCO.tsv", "RefCOCO.tsv"),
    "groundingme": ("lirang04/GroundingME", "groundingme.tsv", "GroundingME.tsv"),
    "tdbench_grounding": ("Columbia-ICSL/TDBench", "tdbench_grounding_rot0.tsv", "tdbench_grounding_rot0.tsv"),
}

REMOTE_TSV_DATASET_FILES = {
    "ocrbench_v2_mini": (
        "https://opencompass.openxlab.space/utils/VLMEval/OCRBench_v2_MINI.tsv",
        "OCRBench_v2_MINI.tsv",
    ),
    "screenspot_v2": (
        "https://opencompass.openxlab.space/utils/benchmarks/GUI/ScreenSpot_v2/ScreenSpot_v2_Mobile.tsv",
        "ScreenSpot_v2/ScreenSpot_v2_Mobile.tsv",
    ),
    "screenspot_v2_desktop": (
        "https://opencompass.openxlab.space/utils/benchmarks/GUI/ScreenSpot_v2/ScreenSpot_v2_Desktop.tsv",
        "ScreenSpot_v2/ScreenSpot_v2_Desktop.tsv",
    ),
    "screenspot_v2_web": (
        "https://opencompass.openxlab.space/utils/benchmarks/GUI/ScreenSpot_v2/ScreenSpot_v2_Web.tsv",
        "ScreenSpot_v2/ScreenSpot_v2_Web.tsv",
    ),
}


def lmu_data_root() -> Path:
    env_root = os.environ.get("LMUData")
    if env_root:
        root = Path(env_root).expanduser()
        root.mkdir(parents=True, exist_ok=True)
        return root
    root = Path.home() / "LMUData"
    root.mkdir(parents=True, exist_ok=True)
    return root


def materialize_grounding_benchmark_files(specs: Iterable[BenchmarkSpec], *, root: Path | None = None) -> None:
    """Pre-download HF TSVs that VLMEvalKit's raw URL downloader cannot fetch reliably."""
    specs = list(specs)
    needed = [spec for spec in specs if spec.key in GROUNDING_HF_DATASET_FILES]
    data_root = root or lmu_data_root()
    token = (
        os.environ.get("HF_TOKEN")
        or os.environ.get("HUGGING_FACE_HUB_TOKEN")
        or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    )
    if needed:
        from huggingface_hub import hf_hub_download

        for spec in needed:
            repo_id, hf_filename, local_filename = GROUNDING_HF_DATASET_FILES[spec.key]
            target = data_root / local_filename
            if target.exists() and target.stat().st_size > 0:
                continue
            print(f"[grounding-data] materializing {spec.key}: {repo_id}/{hf_filename} -> {target}")
            cached = hf_hub_download(
                repo_id=repo_id,
                filename=hf_filename,
                repo_type="dataset",
                token=token,
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(cached, target)

    remote_targets: list[tuple[str, str, str]] = []
    spec_keys = {spec.key for spec in specs}
    if "ocrbench_v2_mini" in spec_keys:
        remote_targets.append(("ocrbench_v2_mini", *REMOTE_TSV_DATASET_FILES["ocrbench_v2_mini"]))
    if "screenspot_v2" in spec_keys:
        for key in ("screenspot_v2", "screenspot_v2_desktop", "screenspot_v2_web"):
            remote_targets.append((key, *REMOTE_TSV_DATASET_FILES[key]))
    if not remote_targets:
        return

    import requests
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    for key, url, local_filename in remote_targets:
        target = data_root / local_filename
        if target.exists() and target.stat().st_size > 0:
            continue
        print(f"[benchmark-data] materializing {key}: {url} -> {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + f".tmp.{os.getpid()}")
        with requests.get(url, stream=True, timeout=120, verify=False) as response:
            response.raise_for_status()
            with tmp.open("wb") as f:
                for chunk in response.iter_content(chunk_size=16 * 1024 * 1024):
                    if chunk:
                        f.write(chunk)
        tmp.replace(target)


def grounding_preferred_score_and_rows(scores_obj: dict[str, Any]) -> tuple[float | None, int | None] | None:
    """Return the canonical grounding metric for the supported bbox/point tasks."""
    dataset = str(scores_obj.get("dataset") or "")
    if dataset not in GROUNDING_DATASET_ALIASES:
        return None

    rows = scores_obj.get("rows")
    rows_int = int(rows) if rows is not None else None
    scores = scores_obj.get("scores", {})
    if not isinstance(scores, dict):
        scores = {}

    if dataset == "RefSpatial_wo_unseen":
        if "overall" in scores:
            return score_to_percent(scores["overall"]), rows_int
        if "overall" in scores_obj:
            return score_to_percent(scores_obj["overall"]), rows_int

    if dataset == "OSWorld_G":
        weighted = weighted_prefixed_overall_accuracy(scores)
        if weighted is not None:
            score, weighted_rows = weighted
            return score, rows_int or weighted_rows
        if "Overall_Accuracy" in scores:
            return score_to_percent(scores["Overall_Accuracy"]), rows_int
        if "Overall_Accuracy" in scores_obj:
            return score_to_percent(scores_obj["Overall_Accuracy"]), rows_int

    if dataset == "GroundingME":
        if "ACC@0.5" in scores:
            return score_to_percent(scores["ACC@0.5"]), rows_int
        table = scores.get("table")
        if isinstance(table, list) and table:
            row = table[0]
            if isinstance(row, dict) and "ACC@0.5" in row:
                return score_to_percent(row["ACC@0.5"]), rows_int

    if dataset == "tdbench_grounding_rot0":
        metric_key = "Average Centroid Containment"
        if metric_key in scores:
            return score_to_percent(scores[metric_key]), rows_int
        table = scores.get("table")
        if isinstance(table, list):
            for row in table:
                if not isinstance(row, dict):
                    continue
                if str(row.get("Metric")) == metric_key and "Score" in row:
                    return score_to_percent(row["Score"]), rows_int

    if dataset == "RefCOCO":
        table = scores.get("table")
        if isinstance(table, list):
            for row in table:
                if not isinstance(row, dict):
                    continue
                if str(row.get("Split")) == "Average" and "Precision@1" in row:
                    parsed_rows = row.get("Samples", rows)
                    return score_to_percent(row["Precision@1"]), int(parsed_rows) if parsed_rows is not None else rows_int
        if "Precision@1" in scores:
            return score_to_percent(scores["Precision@1"]), rows_int

    return None


def extract_score_and_rows(scores_obj: dict[str, Any]) -> tuple[float | None, int | None]:
    rows = scores_obj.get("rows")
    rows_int = int(rows) if rows is not None else None
    grounding = grounding_preferred_score_and_rows(scores_obj)
    if grounding is not None:
        return grounding
    dataset = str(scores_obj.get("dataset") or "")
    if dataset.startswith("OCRBench_v2"):
        scores = scores_obj.get("scores", {})
        if isinstance(scores, dict):
            values = [
                score_to_percent(scores[key])
                for key in ("English Overall Score", "Chinese Overall Score")
                if key in scores
            ]
            values = [value for value in values if value is not None]
            if values:
                return sum(values) / len(values), rows_int
    weighted = weighted_prefixed_overall_accuracy(scores_obj.get("scores"))
    if weighted is not None:
        score, weighted_rows = weighted
        return score, rows_int or weighted_rows
    if "Overall_Accuracy" in scores_obj:
        return float(scores_obj["Overall_Accuracy"]), rows_int
    for key in ("accuracy", "acc", "score", "Overall", "overall"):
        if key in scores_obj:
            parsed = score_to_percent(scores_obj[key])
            if parsed is not None:
                return parsed, rows_int
    scores = scores_obj.get("scores", {})
    if isinstance(scores, dict):
        if "Overall_Accuracy" in scores:
            return float(scores["Overall_Accuracy"]), rows_int
        for key in ("Overall", "overall", "accuracy", "acc", "val"):
            if key in scores:
                value = scores[key]
                if isinstance(value, dict):
                    for nested_key in ("Accuracy (%)", "accuracy", "acc", "score", "Score", "Overall", "overall"):
                        if nested_key in value:
                            parsed = score_to_percent(value[nested_key])
                            if parsed is not None:
                                return parsed, rows_int
                return score_to_percent(value), rows_int
        table = scores.get("table")
        if isinstance(table, list):
            average_values: list[float] = []
            for row in table:
                if not isinstance(row, dict):
                    continue
                if isinstance(row.get("average_scores"), list):
                    for value in row["average_scores"]:
                        parsed = score_to_percent(value)
                        if parsed is not None:
                            average_values.append(parsed)
                if any(str(v).lower() == "overall" for v in row.values()):
                    for key in ("acc", "accuracy", "Accuracy (%)", "score", "Score", "Overall", "overall", "1"):
                        if key in row:
                            return score_to_percent(row[key]), int(row.get("tot", row.get("Samples", rows or 0)) or 0)
                    for key, value in row.items():
                        if str(value).lower() == "overall":
                            continue
                        parsed = score_to_percent(value)
                        if parsed is not None:
                            return parsed, int(row.get("tot", row.get("Samples", rows or 0)) or 0)
            if average_values:
                return sum(average_values) / len(average_values), rows_int

        numeric_scores: list[float] = []
        skip_keys = {
            "rows",
            "samples",
            "num_correct",
            "num_total",
            "illformed_responses",
            "category_stats",
            "table",
            "tabulated_keys",
            "tabulated_results",
        }
        for key, value in scores.items():
            if str(key).lower() in skip_keys:
                continue
            parsed = score_to_percent(value)
            if parsed is not None:
                numeric_scores.append(parsed)
        if numeric_scores:
            return sum(numeric_scores) / len(numeric_scores), rows_int
    return None, rows_int
