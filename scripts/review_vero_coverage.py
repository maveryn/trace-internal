#!/usr/bin/env python3
"""Build a first-pass Vero-600k coverage review against TRACE taxonomy.

The script intentionally uses the Hugging Face dataset-server API instead of
`datasets.load_dataset` because the Vero rows include large image payloads in
the parquet files. The dataset-server rows endpoint returns image metadata and
temporary URLs, which is enough for taxonomy/template analysis without pulling
image bytes into the repo.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import requests


DATASET = "zlab-princeton/Vero-600k"
DATASET_SERVER = "https://datasets-server.huggingface.co"
DEFAULT_OUTPUT_DIR = Path("plans/vero_coverage_review")


CANDIDATE_BACKLOG: list[dict[str, Any]] = [
    {
        "priority": "P0",
        "kind": "new_scene_existing_domain",
        "domain": "games",
        "scene_id": "minesweeper",
        "support_configs": [
            "spatial_action-game_QA",
        ],
        "tasks": [
            "proposal:games/minesweeper/flag_consistency_count",
            "proposal:games/minesweeper/safe_cell_count",
            "proposal:games/minesweeper/mine_candidate_count",
        ],
        "evidence": "cell grid, revealed numbers, flags, hidden cells, adjacency neighborhoods",
        "why": (
            "Vero game_QA includes explicit Minesweeper-style board states and "
            "rules. TRACE games has many board games, but not numerical "
            "constraint games over hidden cells."
        ),
    },
    {
        "priority": "P0",
        "kind": "new_scene_existing_domain",
        "domain": "puzzles",
        "scene_id": "strip_reconstruction",
        "support_configs": [
            "spatial_action-spatial_ssrl",
            "spatial_action-visual_jigsaw_2d",
        ],
        "tasks": [
            "proposal:puzzles/strip_reconstruction/order_label",
            "proposal:puzzles/strip_reconstruction/missing_region_option_label",
            "proposal:puzzles/strip_reconstruction/relative_depth_order_label",
        ],
        "evidence": "strip ids, option ids, region ids, adjacency/continuity refs, depth order",
        "why": (
            "Vero spatial/action data has repeated shuffled-strip, missing-region, "
            "and marked-region depth-order patterns. TRACE has jigsaw and missing "
            "patch tasks, but not a dedicated strip/region reconstruction scene."
        ),
    },
    {
        "priority": "P0",
        "kind": "new_scene_existing_domain",
        "domain": "pages",
        "scene_id": "science_process",
        "support_configs": [
            "stem-ai2d_merged",
            "stem-tqa",
            "stem-mmk12",
            "chart_ocr-CoSyn_400k_diagram",
            "stem-visualwebinstruct",
        ],
        "tasks": [
            "proposal:pages/science_process/arrow_path_count",
            "proposal:pages/science_process/branch_extremum_label",
            "proposal:pages/science_process/component_state_label",
        ],
        "evidence": "node bboxes, arrow polylines, branch ids, label bboxes",
        "why": (
            "Vero has large AI2D/TQA/MMK12/diagram coverage; TRACE pages has "
            "cycle and hierarchy diagrams, but lacks general science/process "
            "diagrams with typed arrows and explicit component-state reasoning."
        ),
    },
    {
        "priority": "P0",
        "kind": "new_task_existing_scene",
        "domain": "icons",
        "scene_id": "icon_field",
        "support_configs": [
            "counting_grounding_search-multihop",
            "counting_grounding_search-objects365_qa",
            "counting_grounding_search-tallyqa",
            "counting_grounding_search-refcocog",
            "counting_grounding_search-oodvqa",
            "counting_grounding_search-pixelreasoner",
            "counting_grounding_search-pixmo",
            "counting_grounding_search-visual_probe",
        ],
        "tasks": [
            "proposal:icons/icon_field/multihop_relation_count",
            "proposal:icons/icon_field/landmark_filtered_attribute_count",
            "proposal:icons/icon_field/ordered_relation_label",
        ],
        "evidence": "object bboxes, attributes, landmark refs, relation chain",
        "why": (
            "Vero's grounding/counting family is broad. Direct natural images "
            "should not be imported, but the repeated multi-hop object search "
            "patterns map cleanly to synthetic icon fields."
        ),
    },
    {
        "priority": "P0",
        "kind": "new_scene_existing_domain",
        "domain": "games",
        "scene_id": "arcade_grid",
        "support_configs": [
            "spatial_action-game_QA",
        ],
        "tasks": [
            "proposal:games/arcade_grid/projectile_target_label",
            "proposal:games/arcade_grid/collision_count",
            "proposal:games/arcade_grid/reachable_enemy_count",
        ],
        "evidence": "grid cells, actor/projectile location, obstacle cells, target/enemy ids",
        "why": (
            "Vero game_QA includes synthetic arcade-like grid games such as Space "
            "Invaders and Zuma-style targeting. These are visually and "
            "algorithmically different from TRACE's current classic board games."
        ),
    },
    {
        "priority": "P0",
        "kind": "new_scene_existing_domain",
        "domain": "puzzles",
        "scene_id": "jigsaw_3d",
        "support_configs": [
            "spatial_action-visual_jigsaw_2d",
            "spatial_action-visual_jigsaw_3d",
        ],
        "tasks": [
            "proposal:puzzles/jigsaw_3d/visible_face_label",
            "proposal:puzzles/jigsaw_3d/neighbor_piece_label",
            "proposal:puzzles/jigsaw_3d/assembly_position_label",
        ],
        "evidence": "piece ids, face ids, 2D/3D placement transforms",
        "why": (
            "Vero includes large 2D and 3D visual-jigsaw subsets. TRACE has a "
            "2D jigsaw scene, but no explicit 3D assembly scene."
        ),
    },
    {
        "priority": "P1",
        "kind": "new_task_existing_scene",
        "domain": "puzzles",
        "scene_id": "maze",
        "support_configs": [
            "spatial_action-game_QA",
        ],
        "tasks": [
            "proposal:puzzles/maze/shortest_path_length",
            "proposal:puzzles/maze/instruction_endpoint_label",
            "proposal:puzzles/maze/obstacle_detour_count",
        ],
        "evidence": "grid cells, start/goal, obstacles, valid path cells, instruction trace",
        "why": (
            "Vero game_QA includes maze mini-games. TRACE already has maze exit "
            "reachability/count tasks, but Vero coverage suggests richer path "
            "length and route-following tasks."
        ),
    },
    {
        "priority": "P1",
        "kind": "new_scene_existing_domain",
        "domain": "puzzles",
        "scene_id": "voxel_projection",
        "support_configs": [
            "spatial_action-game_QA",
        ],
        "tasks": [
            "proposal:puzzles/voxel_projection/missing_count",
            "proposal:puzzles/voxel_projection/candidate_match_label",
            "proposal:puzzles/voxel_projection/visible_face_count",
        ],
        "evidence": "voxel coords, projections, candidate additions, visible face refs",
        "why": (
            "Vero game_QA includes 3D reconstruction puzzles with voxel/projection "
            "rules. TRACE has cube and 3D point scenes, but no projection-based "
            "voxel reconstruction game."
        ),
    },
    {
        "priority": "P1",
        "kind": "new_task_existing_scene",
        "domain": "puzzles",
        "scene_id": "raven_matrix",
        "support_configs": [
            "stem-raven",
        ],
        "tasks": [
            "proposal:puzzles/raven_matrix/rule_axis_label",
            "proposal:puzzles/raven_matrix/missing_cell_attribute_count",
            "proposal:puzzles/raven_matrix/option_elimination_count",
        ],
        "evidence": "matrix cell ids, option ids, visual attributes, row/column rule refs",
        "why": (
            "Vero has a substantial Raven subset. TRACE already has Raven tasks, "
            "but this should be explicitly listed as a puzzle expansion/coverage "
            "validation target, not only an existing-task note."
        ),
    },
    {
        "priority": "P1",
        "kind": "new_scene_existing_domain",
        "domain": "pages",
        "scene_id": "aerial_map",
        "support_configs": [
            "counting_grounding_search-osatlas",
            "counting_grounding_search-aerialvg",
        ],
        "tasks": [
            "proposal:pages/aerial_map/landmark_relation_count",
            "proposal:pages/aerial_map/route_endpoint_label",
            "proposal:pages/aerial_map/zone_filtered_landmark_count",
        ],
        "evidence": "map cells/regions, landmarks, routes, relation anchors",
        "why": (
            "OS/atlas and aerial grounding data suggest map-like spatial "
            "reasoning. This should be a synthetic map/grid scene rather than "
            "natural-image aerial ingestion."
        ),
    },
    {
        "priority": "P1",
        "kind": "new_task_existing_scene",
        "domain": "pages",
        "scene_id": "web_action",
        "support_configs": [
            "spatial_action-magma_aitw",
            "spatial_action-magma_mind2web",
            "counting_grounding_search-groundui",
            "counting_grounding_search-osatlas",
        ],
        "tasks": [
            "proposal:pages/web_action/state_filtered_control_count",
            "proposal:pages/web_action/instruction_target_label",
            "proposal:pages/web_action/navigation_result_label",
        ],
        "evidence": "control bboxes, roles, labels, states, action target id",
        "why": (
            "Vero has substantial UI/action data. TRACE pages already has GUI "
            "scenes, so the main gap is richer target/action and state-filtered "
            "control tasks."
        ),
    },
    {
        "priority": "P1",
        "kind": "new_scene_existing_domain",
        "domain": "geometry",
        "scene_id": "composite_measurement",
        "support_configs": [
            "stem-geo170k",
            "stem-geomverse",
            "stem-geoqa_plus",
            "stem-wemath20_pro",
            "stem-wemath20_standard",
            "stem-CoSyn_400k_math",
        ],
        "tasks": [
            "proposal:geometry/composite_measurement/shaded_area_value",
            "proposal:geometry/composite_measurement/angle_chain_value",
            "proposal:geometry/composite_measurement/similarity_ratio_value",
        ],
        "evidence": "points, segments, regions, angle arcs, constraint refs",
        "why": (
            "The STEM geometry/math configs are large. TRACE has many geometry "
            "scenes, but Vero-style multi-constraint composite measurement diagrams support "
            "more composite measurement tasks."
        ),
    },
    {
        "priority": "P1",
        "kind": "new_task_existing_scene",
        "domain": "charts",
        "scene_id": "curve_panels",
        "support_configs": [
            "chart_ocr-arxivqa_formatted",
            "chart_ocr-reachqa",
            "chart_ocr-ecd_vqa",
            "stem-visualwebinstruct",
        ],
        "tasks": [
            "task_charts__curve_panels__cross_panel_delta_extremum_label",
            "proposal:charts/curve_panels/panel_delta_value",
            "proposal:charts/curve_panels/legend_conditioned_count",
        ],
        "evidence": "panel ids, plotted marks, legends, selected value refs",
        "why": (
            "ArxivQA/ReachQA examples emphasize figure panels and legends. "
            "TRACE has scientific multipanel charts, but can add more "
            "cross-panel tasks."
        ),
    },
    {
        "priority": "P2",
        "kind": "new_task_existing_scene",
        "domain": "pages",
        "scene_id": "infographic",
        "support_configs": [
            "chart_ocr-infographic_vqa",
            "chart_ocr-CoSyn_400k_chart",
            "chart_ocr-evochart",
        ],
        "tasks": [
            "task_pages__infographic__column_profile_comparison_value",
            "task_pages__infographic__section_ranked_total_label",
            "task_pages__infographic__metric_arithmetic_value",
        ],
        "evidence": "card/section bboxes, icon arrays, metric ids",
        "why": (
            "Vero has frequent infographic VQA, but simple value lookup is too "
            "easy. The useful TRACE expansion is synthetic infographic "
            "arithmetic and ranking."
        ),
    },
    {
        "priority": "P2",
        "kind": "conditional_new_scene",
        "domain": "physics",
        "scene_id": "rule_based_system_diagram",
        "support_configs": [
            "stem-ai2d_merged",
            "stem-tqa",
            "stem-mmk12",
            "stem-visualwebinstruct",
        ],
        "tasks": [
            "proposal:physics/system_flow/conservation_value",
            "proposal:physics/system_flow/rule_output_label",
        ],
        "evidence": "explicit rules, arrows, quantities, component bboxes",
        "why": (
            "Only include if all required science rules are printed in-scene. "
            "Otherwise these examples become external-knowledge tasks and "
            "should stay out of TRACE."
        ),
    },
]


EXCLUSION_RULES: list[dict[str, str]] = [
    {
        "pattern": "captioning_IF-*",
        "reason": "captioning/free-form instruction following; not a typed verifier task",
    },
    {
        "pattern": "knowledge_recognition-* except iconqa/kvg after inspection",
        "reason": "usually natural-image recognition or external knowledge rather than metadata-verifiable reasoning",
    },
    {
        "pattern": "stem-pathvqa, stem-vqarad",
        "reason": "medical/radiology domain; unsuitable unless a separate synthetic medical policy is created",
    },
    {
        "pattern": "open-ended chart/document value lookup",
        "reason": "often OCR-only and likely too easy unless converted into arithmetic/comparison tasks",
    },
]


def api_get(path: str, params: dict[str, Any], retries: int = 4) -> dict[str, Any]:
    url = f"{DATASET_SERVER}/{path}"
    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, timeout=60)
            if response.status_code == 200:
                return response.json()
            if response.status_code in {429, 500, 502, 503, 504}:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise RuntimeError(f"{url} returned {response.status_code}: {response.text[:300]}")
        except requests.RequestException as exc:
            if attempt + 1 >= retries:
                raise RuntimeError(f"{url} failed after {retries} attempts: {exc}") from exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"{url} failed after {retries} attempts")


def clean_question(text: str) -> str:
    text = text or ""
    text = text.replace("<image>", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_template(question: str) -> str:
    q = clean_question(question).lower()
    q = re.sub(r"['\"`][^'\"`]{1,80}['\"`]", "<label>", q)
    q = re.sub(r"\b\d+(?:\.\d+)?%?\b", "<num>", q)
    q = re.sub(r"\b[a-d]\)", "<choice>", q)
    q = re.sub(r"[^a-z0-9<>/%+\- ]+", " ", q)
    q = re.sub(r"\s+", " ", q).strip()
    return q[:240]


def family_from_config(config: str) -> str:
    return config.split("-", 1)[0]


def infer_answer_type(answer: str, reward_type: str | None) -> str:
    answer = (answer or "").strip()
    if reward_type:
        reward_type_l = reward_type.lower()
        if "numeric" in reward_type_l:
            return "numeric"
    if re.fullmatch(r"-?\d+", answer):
        return "integer"
    if re.fullmatch(r"-?\d+(?:\.\d+)?%?", answer):
        return "numeric"
    if answer.lower() in {"yes", "no", "true", "false"}:
        return "boolean"
    if re.fullmatch(r"[A-Ha-h]", answer):
        return "choice_label"
    if len(answer.split()) <= 4:
        return "short_label"
    return "free_form"


def infer_question_kind(config: str, question: str, answer_type: str) -> str:
    q = clean_question(question).lower()
    if family_from_config(config) == "captioning_IF":
        return "caption_freeform"
    if any(term in config for term in ["pathvqa", "vqarad"]):
        return "medical_vqa"
    if any(term in q for term in ["click", "tap", "button", "select", "menu", "screen", "website"]):
        return "screen_action"
    if any(term in q for term in ["route", "path", "follow", "from", "to", "navigate"]):
        return "path_navigation"
    if any(term in q for term in ["left", "right", "above", "below", "under", "over", "between", "near", "inside"]):
        return "spatial_relation"
    if any(term in q for term in ["arrow", "flow", "cycle", "stage", "process", "diagram"]):
        return "diagram_flow"
    if any(term in q for term in ["angle", "area", "perimeter", "length", "radius", "diameter", "triangle", "circle", "parallel"]):
        return "geometry_measurement"
    if any(term in q for term in ["ratio", "percent", "percentage", "fraction", "share", "proportion"]):
        return "ratio_percent"
    if any(term in q for term in ["difference", "more than", "less than", "increase", "decrease", "change", "delta"]):
        return "difference_arithmetic"
    if any(term in q for term in ["total", "sum", "combined", "altogether", "in all"]):
        return "sum_arithmetic"
    if any(term in q for term in ["highest", "lowest", "largest", "smallest", "maximum", "minimum", "most", "least", "fewest"]):
        return "comparison_extremum"
    if any(term in q for term in ["how many", "count", "number of"]):
        return "count_objects"
    if any(term in q for term in ["missing", "pattern", "rotate", "rotation", "fold", "matrix", "puzzle"]):
        return "puzzle_pattern"
    if answer_type == "free_form":
        return "open_free_form"
    return "lookup_or_short_answer"


def classify_config(config: str) -> tuple[str, str, str, str]:
    family = family_from_config(config)
    if family == "captioning_IF":
        return ("exclude", "", "", "caption/free-form")
    if config in {"stem-pathvqa", "stem-vqarad"}:
        return ("exclude", "", "", "medical/radiology")
    if config in {"spatial_action-visual_jigsaw_2d"}:
        return ("new_task_existing_scene", "puzzles", "image_cutout_board", "2D jigsaw expansion")
    if config in {"spatial_action-visual_jigsaw_3d"}:
        return ("new_scene_existing_domain", "puzzles", "jigsaw_3d", "3D jigsaw assembly")
    if config in {"spatial_action-magma_aitw", "spatial_action-magma_mind2web"}:
        return ("new_task_existing_scene", "pages", "web_action", "UI/action target tasks")
    if config in {"counting_grounding_search-groundui"}:
        return ("new_task_existing_scene", "pages", "control_board", "UI grounding/counting")
    if config in {"counting_grounding_search-osatlas", "counting_grounding_search-aerialvg"}:
        return ("new_scene_existing_domain", "pages", "aerial_map", "synthetic map grounding")
    if config.startswith("counting_grounding_search-"):
        return ("new_task_existing_scene", "icons", "icon_field", "synthetic object-field grounding proxy")
    if config == "knowledge_recognition-iconqa":
        return ("new_task_existing_scene", "icons", "pattern_grid", "icon/pattern QA")
    if family == "knowledge_recognition":
        return ("exclude", "", "", "natural-image/external knowledge")
    if config in {"stem-ai2d_merged", "stem-tqa", "stem-mmk12", "chart_ocr-CoSyn_400k_diagram", "stem-visualwebinstruct"}:
        return ("new_scene_existing_domain", "pages", "science_process", "science/process diagram")
    if config.startswith("stem-geo") or config in {"stem-geomverse", "stem-wemath20_pro", "stem-wemath20_standard", "stem-CoSyn_400k_math"}:
        return ("new_task_existing_scene", "geometry", "composite_measurement", "composite measurement diagrams")
    if config == "stem-raven":
        return ("existing_task", "puzzles", "raven_matrix", "already has Raven matrix scene")
    if config.startswith("chart_ocr-"):
        if config == "chart_ocr-infographic_vqa":
            return ("new_task_existing_scene", "pages", "infographic", "infographic arithmetic/ranking")
        if config in {"chart_ocr-arxivqa_formatted", "chart_ocr-reachqa", "chart_ocr-ecd_vqa"}:
            return ("new_task_existing_scene", "charts", "curve_panels", "scientific figure panels")
        if "table" in config:
            return ("existing_task", "charts", "table", "table/grid tasks already active")
        if "diagram" in config:
            return ("new_scene_existing_domain", "pages", "science_process", "diagram tasks")
        return ("new_task_existing_scene", "charts", "dashboard", "chart/dashboard variants")
    if config == "spatial_action-game_QA":
        return ("new_scene_existing_domain", "games", "mixed_game_and_puzzle_scenes", "mixed game QA source: minesweeper, arcade grids, maze, voxel reconstruction")
    if config == "spatial_action-stvqa":
        return ("exclude", "", "", "natural scene text/OCR")
    if config == "spatial_action-robo2vlm":
        return ("exclude", "", "", "robotics action/natural scene")
    if config == "spatial_action-spatial_ssrl":
        return ("new_task_existing_scene", "icons", "icon_field", "synthetic spatial relation proxy")
    return ("manual_review", "", "", "mixed source; needs image inspection")


def review_action(disposition: str) -> str:
    if disposition == "existing_task":
        return "No new scene; use as coverage validation/examples."
    if disposition == "new_task_existing_scene":
        return "Review representative images and draft task(s) under mapped scene."
    if disposition == "new_scene_existing_domain":
        return "Review representative images, then create scene renderer + task shortlist."
    if disposition == "conditional_new_scene":
        return "Only include if rules/evidence can be made explicit in-scene."
    if disposition == "exclude":
        return "Exclude from TRACE task backlog."
    return "Manual inspection before deciding."


def config_inventory(size_payload: dict[str, Any]) -> list[dict[str, Any]]:
    split_rows: dict[str, dict[str, int]] = defaultdict(dict)
    for split in size_payload["splits"]:
        split_rows[split["config"]][split["split"]] = split["num_rows"]
    rows = []
    for cfg in sorted(size_payload["configs"], key=lambda item: item["config"]):
        config = cfg["config"]
        disposition, domain, scene, note = classify_config(config)
        rows.append(
            {
                "config": config,
                "family": family_from_config(config),
                "num_rows": cfg["num_rows"],
                "train_rows": split_rows.get(config, {}).get("train", 0),
                "val_rows": split_rows.get(config, {}).get("val", 0),
                "disposition": disposition,
                "mapped_domain": domain,
                "mapped_scene": scene,
                "review_action": review_action(disposition),
                "notes": note,
            }
        )
    return rows


def sample_offsets(train_rows: int, sample_per_offset: int, max_offsets: int) -> list[int]:
    if train_rows <= 0:
        return []
    if train_rows <= sample_per_offset:
        return [0]
    if max_offsets <= 1:
        return [0]
    candidates = [0, train_rows // 2, max(0, train_rows - sample_per_offset)]
    if max_offsets > 3:
        candidates.extend([train_rows // 4, (3 * train_rows) // 4])
    offsets = []
    for offset in candidates:
        offset = min(max(0, offset), max(0, train_rows - sample_per_offset))
        if offset not in offsets:
            offsets.append(offset)
    return offsets[:max_offsets]


def fetch_samples(
    inventory: list[dict[str, Any]], sample_per_offset: int, max_offsets: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    samples: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for index, cfg in enumerate(inventory, start=1):
        config = cfg["config"]
        train_rows = int(cfg["train_rows"])
        offsets = sample_offsets(train_rows, sample_per_offset, max_offsets)
        print(f"[{index:02d}/{len(inventory)}] sampling {config}: offsets={offsets}", flush=True)
        for offset in offsets:
            length = min(sample_per_offset, max(0, train_rows - offset))
            if length <= 0:
                continue
            try:
                payload = api_get(
                    "rows",
                    {
                        "dataset": DATASET,
                        "config": config,
                        "split": "train",
                        "offset": offset,
                        "length": length,
                    },
                )
            except RuntimeError as exc:
                print(f"  sampling failed for {config} offset={offset}: {exc}", flush=True)
                errors.append(
                    {
                        "config": config,
                        "offset": offset,
                        "length": length,
                        "error": str(exc),
                    }
                )
                continue
            for item in payload.get("rows", []):
                row = item.get("row", {})
                extra = row.get("extra_info") or {}
                reward = row.get("reward_model") or {}
                image = row.get("image") or {}
                question = clean_question(extra.get("question") or " ".join((row.get("prompt") or {}).get("content") or []))
                answer = str(extra.get("answer") or reward.get("ground_truth") or "")
                answer_type = infer_answer_type(answer, extra.get("reward_type"))
                samples.append(
                    {
                        "config": config,
                        "family": cfg["family"],
                        "row_idx": item.get("row_idx"),
                        "id": row.get("id"),
                        "data_source": row.get("data_source"),
                        "ability": row.get("ability"),
                        "question": question,
                        "answer": answer,
                        "reward_type": extra.get("reward_type"),
                        "answer_type": answer_type,
                        "question_kind": infer_question_kind(config, question, answer_type),
                        "template": normalize_template(question),
                        "image_width": image.get("width"),
                        "image_height": image.get("height"),
                        "disposition": cfg["disposition"],
                        "mapped_domain": cfg["mapped_domain"],
                        "mapped_scene": cfg["mapped_scene"],
                    }
                )
    return samples, errors


def build_clusters(samples: list[dict[str, Any]], inventory_by_config: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for sample in samples:
        grouped[(sample["config"], sample["question_kind"], sample["template"])].append(sample)

    clusters = []
    for (config, question_kind, template), rows in grouped.items():
        cfg = inventory_by_config[config]
        sampled_config_count = sum(1 for sample in samples if sample["config"] == config)
        sample_hits = len(rows)
        estimated_config_hits = (
            int(round((sample_hits / sampled_config_count) * int(cfg["num_rows"])))
            if sampled_config_count
            else 0
        )
        answer_types = Counter(row["answer_type"] for row in rows)
        examples = [row["question"] for row in rows[:3]]
        clusters.append(
            {
                "config": config,
                "family": cfg["family"],
                "question_kind": question_kind,
                "template": template,
                "sample_hits": sample_hits,
                "sampled_config_rows": sampled_config_count,
                "estimated_config_hits": estimated_config_hits,
                "answer_types": ";".join(f"{k}:{v}" for k, v in answer_types.most_common()),
                "disposition": cfg["disposition"],
                "mapped_domain": cfg["mapped_domain"],
                "mapped_scene": cfg["mapped_scene"],
                "example_1": examples[0] if len(examples) > 0 else "",
                "example_2": examples[1] if len(examples) > 1 else "",
                "example_3": examples[2] if len(examples) > 2 else "",
            }
        )
    clusters.sort(key=lambda row: (-row["estimated_config_hits"], row["config"], row["question_kind"]))
    return clusters


def load_trace_inventory(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    data = json.loads(path.read_text())
    tasks = data["tasks"]
    scene_counter = Counter((row["domain"], row["scene_id"]) for row in tasks)
    scenes = [
        {"domain": domain, "scene_id": scene, "task_count": count}
        for (domain, scene), count in sorted(scene_counter.items())
    ]
    task_rows = [
        {
            "domain": row["domain"],
            "scene_id": row["scene_id"],
            "task_id": row["task_id"],
            "source_task_group": row.get("source_task_group", ""),
            "audit_status": row.get("audit_status", ""),
        }
        for row in sorted(tasks, key=lambda item: (item["domain"], item["scene_id"], item["task_id"]))
    ]
    return scenes, task_rows


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def refresh_sample_mappings(samples: list[dict[str, Any]], inventory_by_config: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    refreshed = []
    for sample in samples:
        row = dict(sample)
        cfg = inventory_by_config.get(row["config"])
        if cfg:
            row["family"] = cfg["family"]
            row["disposition"] = cfg["disposition"]
            row["mapped_domain"] = cfg["mapped_domain"]
            row["mapped_scene"] = cfg["mapped_scene"]
        refreshed.append(row)
    return refreshed


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        lines.append("| " + " | ".join(str(cell).replace("\n", " ") for cell in row) + " |")
    return "\n".join(lines)


def write_readme(
    output_dir: Path,
    inventory: list[dict[str, Any]],
    samples: list[dict[str, Any]],
    clusters: list[dict[str, Any]],
    trace_scenes: list[dict[str, Any]],
    errors: list[dict[str, Any]],
) -> None:
    disposition_counts = Counter(row["disposition"] for row in inventory)
    family_counts = Counter(row["family"] for row in inventory)
    sampled_by_family = Counter(row["family"] for row in samples)
    text = f"""# Vero-600k Coverage Review

Generated: {dt.datetime.now(dt.UTC).isoformat(timespec="seconds")}

Source dataset: <https://huggingface.co/datasets/zlab-princeton/Vero-600k/>

## Method

- Pulled config and row counts from the Hugging Face dataset-server `size` endpoint.
- Sampled non-image rows from the `rows` endpoint and saved question/answer/image-dimension metadata only.
- Did not download image bytes into the repo.
- Mapped Vero configs and sampled template clusters against the current TRACE public taxonomy.
- Recommended only synthetic, metadata-verifiable additions. Natural-image and free-form-only sources are excluded or marked as proxy inspiration.

## Inventory Summary

- Vero configs reviewed: {len(inventory)}
- Vero rows reported by dataset-server configs: {sum(int(row["num_rows"]) for row in inventory):,}
- Sampled non-image rows: {len(samples):,}
- Sampling errors: {len(errors)}
- Template clusters mined: {len(clusters):,}
- TRACE active scenes in audit: {len(trace_scenes)}

### Disposition Counts

{md_table(["disposition", "configs"], [[k, v] for k, v in disposition_counts.most_common()])}

### Vero Family Counts

{md_table(["family", "configs", "sampled_rows"], [[family, family_counts[family], sampled_by_family[family]] for family in sorted(family_counts)])}

## Puzzle/Game Coverage Note

Vero does contain substantial puzzle/game coverage. The main sources are
`spatial_action-game_QA`, `spatial_action-visual_jigsaw_2d`,
`spatial_action-visual_jigsaw_3d`, `spatial_action-spatial_ssrl`, and
`stem-raven`. These are now called out explicitly in
`candidate_scene_task_backlog.md`; several are mixed-source configs, so their
row counts are upper bounds until a deeper image-level split is done.

## Files

- `config_inventory.csv`: Vero config-level mapping to TRACE domains/scenes.
- `template_clusters.csv`: sampled normalized question-template clusters.
- `sample_questions.jsonl`: sampled rows without image bytes or signed image URLs.
- `sampling_errors.csv`: configs/offsets that the public dataset-server failed to return.
- `trace_scene_inventory.csv`: current TRACE scene/task counts.
- `trace_task_inventory.csv`: current TRACE active task inventory.
- `trace_gap_matrix.md`: config-level gap/reuse matrix.
- `candidate_scene_task_backlog.md`: ranked candidate scenes/tasks to implement.
- `excluded_clusters.md`: excluded source families and reasons.

## Important Caveat

This is a coverage and taxonomy review, not a solve-rate or final task-design pass. Before implementing a candidate, inspect representative images from its configs and confirm the proposed synthetic scene preserves the Vero reasoning pattern without importing natural-image assumptions.
"""
    (output_dir / "README.md").write_text(text, encoding="utf-8")


def write_gap_matrix(output_dir: Path, inventory: list[dict[str, Any]], clusters: list[dict[str, Any]]) -> None:
    cluster_counts_by_config = Counter(row["config"] for row in clusters)
    sample_kinds: dict[str, Counter[str]] = defaultdict(Counter)
    for row in clusters:
        sample_kinds[row["config"]][row["question_kind"]] += row["sample_hits"]
    table_rows = []
    for row in inventory:
        kinds = ", ".join(f"{k}:{v}" for k, v in sample_kinds[row["config"]].most_common(5))
        table_rows.append(
            [
                row["config"],
                f"{int(row['num_rows']):,}",
                row["disposition"],
                row["mapped_domain"] or "-",
                row["mapped_scene"] or "-",
                cluster_counts_by_config[row["config"]],
                kinds or "-",
                row["review_action"],
            ]
        )
    text = "# Vero to TRACE Gap Matrix\n\n"
    text += md_table(
        [
            "Vero config",
            "rows",
            "disposition",
            "domain",
            "scene",
            "clusters",
            "top sampled question kinds",
            "review action",
        ],
        table_rows,
    )
    text += "\n"
    (output_dir / "trace_gap_matrix.md").write_text(text, encoding="utf-8")


def candidate_score(candidate: dict[str, Any], inventory_by_config: dict[str, dict[str, Any]]) -> tuple[int, int]:
    support_rows = sum(int(inventory_by_config.get(config, {}).get("num_rows", 0)) for config in candidate["support_configs"])
    priority_bonus = {"P0": 3, "P1": 2, "P2": 1}.get(candidate["priority"], 0)
    kind_bonus = {
        "new_scene_existing_domain": 3,
        "new_task_existing_scene": 2,
        "conditional_new_scene": 1,
    }.get(candidate["kind"], 0)
    score = int(round(math.log10(max(1, support_rows)) * 20 + priority_bonus * 10 + kind_bonus * 5))
    return score, support_rows


def write_candidate_backlog(output_dir: Path, inventory_by_config: dict[str, dict[str, Any]]) -> None:
    rows = []
    for candidate in CANDIDATE_BACKLOG:
        score, support_rows = candidate_score(candidate, inventory_by_config)
        rows.append((score, support_rows, candidate))
    rows.sort(key=lambda item: (-item[0], item[2]["priority"], item[2]["domain"], item[2]["scene_id"]))

    lines = [
        "# Candidate Scene and Task Backlog from Vero",
        "",
        "Ranking uses Vero config support, novelty, evidence fit, synthetic feasibility, and expected implementation cost.",
        "Support row counts are config-level upper bounds, not exact template counts.",
        "",
    ]
    for score, support_rows, candidate in rows:
        lines.extend(
            [
                f"## {candidate['priority']} - {candidate['domain']} / {candidate['scene_id']}",
                "",
                f"- Type: `{candidate['kind']}`",
                f"- Score: `{score}`",
                f"- Supporting Vero configs: {', '.join(f'`{c}`' for c in candidate['support_configs'])}",
                f"- Config-level support rows: `{support_rows:,}`",
                f"- Proposed tasks: {', '.join(f'`{task}`' for task in candidate['tasks'])}",
                f"- Evidence contract: {candidate['evidence']}",
                f"- Rationale: {candidate['why']}",
                "",
            ]
        )
    (output_dir / "candidate_scene_task_backlog.md").write_text("\n".join(lines), encoding="utf-8")


def write_exclusions(output_dir: Path, inventory: list[dict[str, Any]], clusters: list[dict[str, Any]]) -> None:
    excluded_configs = [row for row in inventory if row["disposition"] == "exclude"]
    excluded_clusters = [row for row in clusters if row["disposition"] == "exclude"][:80]
    lines = [
        "# Excluded Vero Sources",
        "",
        "These are excluded from the TRACE task backlog unless the project explicitly changes scope.",
        "",
        "## Rules",
        "",
    ]
    for rule in EXCLUSION_RULES:
        lines.append(f"- `{rule['pattern']}`: {rule['reason']}")
    lines.extend(["", "## Excluded Configs", ""])
    lines.append(
        md_table(
            ["config", "rows", "reason"],
            [[row["config"], f"{int(row['num_rows']):,}", row["notes"]] for row in excluded_configs],
        )
    )
    lines.extend(["", "## Representative Excluded Template Clusters", ""])
    lines.append(
        md_table(
            ["config", "kind", "estimated hits", "example"],
            [
                [row["config"], row["question_kind"], row["estimated_config_hits"], row["example_1"]]
                for row in excluded_clusters
            ],
        )
    )
    lines.append("")
    (output_dir / "excluded_clusters.md").write_text("\n".join(lines), encoding="utf-8")


def write_manifest(
    output_dir: Path,
    args: argparse.Namespace,
    inventory: list[dict[str, Any]],
    samples: list[dict[str, Any]],
    clusters: list[dict[str, Any]],
    errors: list[dict[str, Any]],
) -> None:
    manifest = {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "dataset": DATASET,
        "sample_per_offset": args.sample_per_offset,
        "max_offsets": args.max_offsets,
        "config_count": len(inventory),
        "sample_count": len(samples),
        "sampling_error_count": len(errors),
        "cluster_count": len(clusters),
        "notes": "Image bytes were not downloaded; sample rows omit signed image URLs.",
    }
    (output_dir / "review_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--active-audit", type=Path, default=Path("plans/active_task_audit.json"))
    parser.add_argument("--sample-per-offset", type=int, default=100)
    parser.add_argument("--max-offsets", type=int, default=3)
    parser.add_argument("--skip-sampling", action="store_true")
    parser.add_argument(
        "--reuse-samples",
        type=Path,
        help="Reuse an existing sample_questions.jsonl file instead of calling the rows API.",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    size_payload = api_get("size", {"dataset": DATASET})["size"]
    inventory = config_inventory(size_payload)
    inventory_by_config = {row["config"]: row for row in inventory}

    trace_scenes, trace_tasks = load_trace_inventory(args.active_audit)
    write_csv(args.output_dir / "trace_scene_inventory.csv", trace_scenes)
    write_csv(args.output_dir / "trace_task_inventory.csv", trace_tasks)
    write_csv(args.output_dir / "config_inventory.csv", inventory)

    if args.reuse_samples:
        samples = refresh_sample_mappings(read_jsonl(args.reuse_samples), inventory_by_config)
        errors_path = args.output_dir / "sampling_errors.csv"
        if errors_path.exists():
            with errors_path.open(newline="", encoding="utf-8") as handle:
                errors = list(csv.DictReader(handle))
        else:
            errors = []
    elif args.skip_sampling:
        samples = []
        errors = []
    else:
        samples, errors = fetch_samples(inventory, args.sample_per_offset, args.max_offsets)
    write_jsonl(args.output_dir / "sample_questions.jsonl", samples)
    write_csv(
        args.output_dir / "sampling_errors.csv",
        errors,
        fieldnames=["config", "offset", "length", "error"],
    )

    clusters = build_clusters(samples, inventory_by_config)
    write_csv(args.output_dir / "template_clusters.csv", clusters)
    write_gap_matrix(args.output_dir, inventory, clusters)
    write_candidate_backlog(args.output_dir, inventory_by_config)
    write_exclusions(args.output_dir, inventory, clusters)
    write_readme(args.output_dir, inventory, samples, clusters, trace_scenes, errors)
    write_manifest(args.output_dir, args, inventory, samples, clusters, errors)

    print(f"Wrote Vero coverage review to {args.output_dir}")
    print(f"configs={len(inventory)} samples={len(samples)} clusters={len(clusters)}")


if __name__ == "__main__":
    main()
