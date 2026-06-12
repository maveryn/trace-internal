#!/usr/bin/env python3
"""Create a domain-by-domain second-pass Vero expansion analysis.

This script consumes the first-pass artifacts in `review/vero_coverage_review/`
and writes a domain-scoped candidate analysis. It does not query Hugging Face or
download images; support estimates come from the sampled non-image rows and the
config row counts captured by `scripts/review_vero_coverage.py`.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from trace.core.taxonomy import ACTIVE_DOMAINS


DEFAULT_REVIEW_DIR = Path("review/vero_coverage_review")
ACTIVE_DOMAIN_NAMES = tuple(sorted(str(domain) for domain in ACTIVE_DOMAINS))


NEW_SCENE_CANDIDATES: list[dict[str, Any]] = [
    {
        "priority": "P1",
        "domain": "charts",
        "scene_id": "callout_annotation",
        "support_configs": ["chart_ocr-arxivqa_formatted", "chart_ocr-reachqa", "chart_ocr-ecd_vqa"],
        "pattern": r"\b(figure|panel|subplot|arrow|label|annotat|highlight|marked|shown)\b",
        "rationale": "Vero scientific/chart OCR examples often ask about annotated figure panels. TRACE has scientific multipanel charts, but no scene where callouts/arrows are the primary visual grammar.",
        "annotation_contract": "panel bboxes, callout arrow polylines, mark ids, label bboxes",
        "overlap_risk": "Medium with `curve_panels`; keep this scene only if callouts/arrows are rendered as first-class queried objects.",
        "tasks": [
            {
                "task_id": "proposal:charts/callout_annotation/target_mark_label",
                "answer_type": "label",
                "annotation_type": "bbox_set",
                "difficulty_knobs": "panel count, callout count, distractor labels, legend sharing",
                "rationale": "Identify which plotted mark or panel element a callout refers to.",
            },
            {
                "task_id": "proposal:charts/callout_annotation/condition_count",
                "answer_type": "integer",
                "annotation_type": "bbox_set",
                "difficulty_knobs": "number of panels, callout density, condition difficulty",
                "rationale": "Count callouts or highlighted marks satisfying a visual/value condition.",
            },
        ],
    },
    {
        "priority": "P1",
        "domain": "charts",
        "scene_id": "table_combo",
        "support_configs": ["chart_ocr-CoSyn_400k_table", "chart_ocr-arxivqa_formatted", "chart_ocr-reachqa"],
        "pattern": r"\b(table|row|column|cell|figure|panel|chart)\b",
        "rationale": "Several Vero chart/OCR sources mix chart panels with tables. TRACE has data-table grids and chart dashboards separately, but not a coupled table+chart figure scene.",
        "annotation_contract": "table cell bboxes, chart panel ids, shared category/series ids",
        "overlap_risk": "Medium with `table` and `dashboard`; require questions to use both subpanels.",
        "tasks": [
            {
                "task_id": "proposal:charts/table_combo/consistency_count",
                "answer_type": "integer",
                "annotation_type": "bbox_set",
                "difficulty_knobs": "row count, chart mark count, mismatch count, shared labels",
                "rationale": "Count rows/categories where table and chart values agree or disagree.",
            },
            {
                "task_id": "proposal:charts/table_combo/cross_panel_difference_value",
                "answer_type": "integer",
                "annotation_type": "point_set",
                "difficulty_knobs": "value range, panel count, lookup distance",
                "rationale": "Compute a value from a table cell and a corresponding plotted mark.",
            },
        ],
    },
    {
        "priority": "P0",
        "domain": "games",
        "scene_id": "minesweeper",
        "support_configs": ["spatial_action-game_QA"],
        "pattern": r"\b(minesweeper|mines?|flagged|adjacent)\b",
        "rationale": "Vero game_QA includes explicit Minesweeper boards. This is a compact rule-based game scene absent from TRACE's current board-game set.",
        "annotation_contract": "cell grid, revealed numbers, flags, hidden cells, adjacency neighborhoods",
        "overlap_risk": "Low; current games do not use hidden-neighbor numeric constraints.",
        "tasks": [
            {
                "task_id": "proposal:games/minesweeper/flag_consistency_count",
                "answer_type": "integer",
                "annotation_type": "cell_set",
                "difficulty_knobs": "board size, mine count, revealed-number density, flagged-cell count",
                "rationale": "Count revealed cells whose adjacent flags match the clue number.",
            },
            {
                "task_id": "proposal:games/minesweeper/safe_cell_count",
                "answer_type": "integer",
                "annotation_type": "cell_set",
                "difficulty_knobs": "board size, local clue fanout, forced-safe count",
                "rationale": "Count hidden cells forced safe by local clue constraints.",
            },
        ],
    },
    {
        "priority": "P0",
        "domain": "games",
        "scene_id": "arcade_grid",
        "support_configs": ["spatial_action-game_QA"],
        "pattern": r"\b(zuma|space invaders|pac-man|projectile|shoot|enemy|frog|marbles|beans)\b",
        "rationale": "Vero game_QA includes arcade-like grid targeting scenes. These differ visually from static classic board games and support path/collision reasoning.",
        "annotation_contract": "grid cells, actor position, projectile/route trace, obstacles, targets",
        "overlap_risk": "Medium with maze/path puzzles; keep in games only when the scene is explicitly an arcade game.",
        "tasks": [
            {
                "task_id": "proposal:games/arcade_grid/projectile_target_label",
                "answer_type": "label",
                "annotation_type": "cell_set",
                "difficulty_knobs": "grid size, obstacle count, target count, projectile directions",
                "rationale": "Find which target a shot or move sequence reaches first.",
            },
            {
                "task_id": "proposal:games/arcade_grid/collision_count",
                "answer_type": "integer",
                "annotation_type": "cell_set",
                "difficulty_knobs": "path length, moving-object count, blocked cells",
                "rationale": "Count objects intersected by a route or projectile path.",
            },
        ],
    },
    {
        "priority": "P1",
        "domain": "games",
        "scene_id": "solitaire",
        "support_configs": ["spatial_action-game_QA"],
        "pattern": r"\b(klondike|solitaire|tableau|foundation|playing card)\b",
        "rationale": "Vero game_QA has card-tableau interfaces distinct from TRACE's flat card-hand scene.",
        "annotation_contract": "card bboxes, stack ids, visible ranks/suits, tableau/foundation zones",
        "overlap_risk": "Medium with `cards`; require tableau stacks and move legality rather than hand counting.",
        "tasks": [
            {
                "task_id": "proposal:games/solitaire/legal_move_count",
                "answer_type": "integer",
                "annotation_type": "bbox_set",
                "difficulty_knobs": "stack count, visible-card count, empty columns, suit/rank spread",
                "rationale": "Count legal card moves from visible tableau/foundation state.",
            },
            {
                "task_id": "proposal:games/solitaire/foundation_playable_label",
                "answer_type": "label",
                "annotation_type": "bbox",
                "difficulty_knobs": "foundation progress, candidate cards, suit distractors",
                "rationale": "Identify a visible card playable to a foundation pile.",
            },
        ],
    },
    {
        "priority": "P1",
        "domain": "geometry",
        "scene_id": "composite_measurement",
        "support_configs": ["stem-geo170k", "stem-geomverse", "stem-geoqa_plus", "stem-wemath20_pro", "stem-wemath20_standard", "stem-CoSyn_400k_math"],
        "pattern": r"\b(angle|triangle|circle|area|perimeter|length|radius|diameter|parallel|similar|geometry)\b",
        "rationale": "Vero STEM geometry/math configs have many multi-constraint composite measurement diagrams. TRACE has geometry primitives, but fewer composite measurement diagrams combining several constraints.",
        "annotation_contract": "points, segments, regions, angle arcs, length labels, constraint refs",
        "overlap_risk": "Medium with existing geometry scenes; require multi-object or multi-constraint composition.",
        "tasks": [
            {
                "task_id": "proposal:geometry/composite_measurement/shaded_area_value",
                "answer_type": "integer",
                "annotation_type": "polygon_region_set",
                "difficulty_knobs": "number of regions, decomposition steps, distractor dimensions",
                "rationale": "Compute shaded area from a compound diagram.",
            },
            {
                "task_id": "proposal:geometry/composite_measurement/angle_chain_value",
                "answer_type": "integer",
                "annotation_type": "arc_set",
                "difficulty_knobs": "angle chain length, parallel/transversal rules, known angle count",
                "rationale": "Infer a missing angle using multiple visible constraints.",
            },
        ],
    },
    {
        "priority": "P2",
        "domain": "geometry",
        "scene_id": "measurement_tool",
        "support_configs": ["knowledge_recognition-iconqa", "stem-mmk12", "stem-visualwebinstruct"],
        "pattern": r"\b(ruler|protractor|measure|centimeter|degree|nearest)\b",
        "rationale": "IconQA/MMK12 samples include ruler/protractor-style questions. This could add visual measurement-tool reading without depending on photos.",
        "annotation_contract": "tool tick positions, object endpoints, measured segment/angle refs",
        "overlap_risk": "Medium with geometry measurement tasks; scene must visibly include the measurement tool.",
        "tasks": [
            {
                "task_id": "proposal:geometry/measuring_tools/shape_length_value",
                "answer_type": "integer",
                "annotation_type": "keyed_point_map",
                "difficulty_knobs": "shape kind, tick spacing, start offset, side/radius target, distractor marks",
                "rationale": "Read a polygon side or circle radius from a rendered ruler placed on the shape.",
            },
            {
                "task_id": "proposal:geometry/measuring_tools/shape_angle_value",
                "answer_type": "integer",
                "annotation_type": "keyed_point_map",
                "difficulty_knobs": "shape kind, inner/outer scale, angle orientation, distractor rays",
                "rationale": "Read a polygon vertex angle from a rendered protractor placed on the shape.",
            },
        ],
    },
    {
        "priority": "P2",
        "domain": "graph",
        "scene_id": "semantic_node_link",
        "support_configs": ["stem-ai2d_merged", "chart_ocr-CoSyn_400k_diagram", "stem-tqa"],
        "pattern": r"\b(node|edge|arrow|connect|network|flow|dependency|graph)\b",
        "rationale": "Some Vero diagram examples may be true node-link graphs, but many are better treated as pages/process diagrams. Add only after image inspection confirms node-link grammar.",
        "annotation_contract": "node bboxes, directed/undirected edges, edge labels",
        "overlap_risk": "High with `pages/science_process`; use graph domain only for abstract node-link graphs.",
        "tasks": [
            {
                "task_id": "proposal:graph/semantic_node_link/dependency_reachable_count",
                "answer_type": "integer",
                "annotation_type": "node_edge_set",
                "difficulty_knobs": "node count, edge density, directionality, label filters",
                "rationale": "Count labeled nodes reachable through a semantic dependency graph.",
            },
            {
                "task_id": "proposal:graph/semantic_node_link/incoming_edge_extremum_label",
                "answer_type": "label",
                "annotation_type": "node_edge_set",
                "difficulty_knobs": "node count, tie avoidance, edge label distractors",
                "rationale": "Identify a node by edge-count extremum under a condition.",
            },
        ],
    },
    {
        "priority": "P1",
        "domain": "icons",
        "scene_id": "probability_widget",
        "support_configs": ["knowledge_recognition-iconqa"],
        "pattern": r"\b(spinner|marble|likely|unlikely|probable|certain|impossible|pick)\b",
        "rationale": "Vero IconQA has repeated elementary probability scenes. TRACE icons has pattern/counting scenes, but not probability widgets.",
        "annotation_contract": "spinner sectors or marble bboxes, color/type labels, option labels",
        "overlap_risk": "Low if answer is probability/category rather than raw count.",
        "tasks": [
            {
                "task_id": "proposal:icons/probability_widget/event_likelihood_label",
                "answer_type": "label",
                "annotation_type": "bbox_set",
                "difficulty_knobs": "sector count, equal/unequal sector sizes, marble count, option count",
                "rationale": "Answer likely/unlikely/certain/impossible from a synthetic spinner or bag.",
            },
            {
                "task_id": "proposal:icons/probability_widget/favorable_count",
                "answer_type": "integer",
                "annotation_type": "bbox_set",
                "difficulty_knobs": "object count, color categories, target conjunctions",
                "rationale": "Count favorable outcomes for a displayed random draw.",
            },
        ],
    },
    {
        "priority": "P1",
        "domain": "icons",
        "scene_id": "object_scene",
        "support_configs": ["counting_grounding_search-tallyqa", "counting_grounding_search-pixmo", "counting_grounding_search-oodvqa", "counting_grounding_search-objects365_qa"],
        "pattern": r"\b(how many|count|where are|person|people|car|object|left|right|above|below|near)\b",
        "rationale": "Vero object grounding/counting is broad. A synthetic object-scene canvas would be visually richer than flat icons while staying metadata-verifiable.",
        "annotation_contract": "object bboxes, categories, attributes, spatial relations, landmark refs",
        "overlap_risk": "Medium with `icon_field`; justify only if the scene uses layered/scene-like placement instead of uniform icon fields.",
        "tasks": [
            {
                "task_id": "proposal:icons/object_scene/multihop_count",
                "answer_type": "integer",
                "annotation_type": "bbox_set",
                "difficulty_knobs": "object count, relation chain length, category distractors, occlusion",
                "rationale": "Count objects satisfying multi-hop spatial/category conditions.",
            },
            {
                "task_id": "proposal:icons/object_scene/landmark_relation_label",
                "answer_type": "label",
                "annotation_type": "bbox_set",
                "difficulty_knobs": "landmark count, relation ambiguity, object density",
                "rationale": "Identify an object by relation to one or more landmarks.",
            },
        ],
    },
    {
        "priority": "P0",
        "domain": "pages",
        "scene_id": "science_process",
        "support_configs": ["stem-ai2d_merged", "stem-tqa", "stem-mmk12", "chart_ocr-CoSyn_400k_diagram", "stem-visualwebinstruct"],
        "pattern": r"\b(diagram|arrow|process|cycle|flow|stage|system|food chain|label)\b",
        "rationale": "Vero has large AI2D/TQA/MMK12/diagram coverage. TRACE pages has cycle/hierarchy scenes but lacks a general science/process diagram grammar.",
        "annotation_contract": "node bboxes, arrow polylines, typed labels, branch ids",
        "overlap_risk": "Medium with graph and page cycle/hierarchy scenes; use for semantic/process diagrams with visible labels.",
        "tasks": [
            {
                "task_id": "proposal:pages/science_process/arrow_path_count",
                "answer_type": "integer",
                "annotation_type": "node_edge_set",
                "difficulty_knobs": "node count, branch count, arrow direction, label distractors",
                "rationale": "Count reachable stages or arrows along a process path.",
            },
            {
                "task_id": "proposal:pages/science_process/branch_extremum_label",
                "answer_type": "label",
                "annotation_type": "node_edge_set",
                "difficulty_knobs": "branch fanout, tie avoidance, condition filters",
                "rationale": "Identify the branch or component with most/fewest downstream elements.",
            },
        ],
    },
    {
        "priority": "P1",
        "domain": "pages",
        "scene_id": "aerial_map",
        "support_configs": ["counting_grounding_search-aerialvg", "counting_grounding_search-osatlas"],
        "pattern": r"\b(map|aerial|satellite|road|building|north|south|east|west|route|locate)\b",
        "rationale": "Vero contains aerial/map/UI-location grounding. TRACE has a static map, but not an aerial/atlas-style grid with landmarks/roads/zones.",
        "annotation_contract": "map regions, road polylines, landmark bboxes, route trace, compass metadata",
        "overlap_risk": "Medium with `map`; require aerial/road/landmark grammar rather than zone-only maps.",
        "tasks": [
            {
                "task_id": "proposal:pages/aerial_map/landmark_relation_count",
                "answer_type": "integer",
                "annotation_type": "bbox_set",
                "difficulty_knobs": "landmark count, road density, relation filters, distractor zones",
                "rationale": "Count landmarks satisfying compass/road relation constraints.",
            },
            {
                "task_id": "proposal:pages/aerial_map/route_endpoint_label",
                "answer_type": "label",
                "annotation_type": "path",
                "difficulty_knobs": "route length, intersections, landmark density",
                "rationale": "Follow a route to identify the endpoint landmark/zone.",
            },
        ],
    },
    {
        "priority": "P2",
        "domain": "pages",
        "scene_id": "worksheet",
        "support_configs": ["stem-mmk12", "stem-visualwebinstruct", "stem-CoSyn_400k_math"],
        "pattern": r"\b(problem|question|worksheet|answer|solve|choices|shown below)\b",
        "rationale": "Vero STEM sources include worksheet-like pages. Add only if the visual annotation is in diagrams/tables/number lines, not text-only math.",
        "annotation_contract": "problem panel bboxes, diagram refs, option refs, numeric labels",
        "overlap_risk": "High with text-only math and existing geometry/pages scenes; defer unless visual grounding is central.",
        "tasks": [
            {
                "task_id": "proposal:pages/worksheet/visual_option_elimination_count",
                "answer_type": "integer",
                "annotation_type": "bbox_set",
                "difficulty_knobs": "option count, visual clue count, distractor diagrams",
                "rationale": "Count answer options inconsistent with the displayed visual clues.",
            },
            {
                "task_id": "proposal:pages/worksheet/diagram_referenced_value",
                "answer_type": "integer",
                "annotation_type": "bbox_set",
                "difficulty_knobs": "diagram label count, arithmetic steps, distractor labels",
                "rationale": "Compute a value referenced by a worksheet diagram.",
            },
        ],
    },
    {
        "priority": "P2",
        "domain": "physics",
        "scene_id": "experiment_setup",
        "support_configs": ["stem-ai2d_merged", "stem-tqa", "stem-mmk12", "stem-visualwebinstruct"],
        "pattern": r"\b(experiment|force|mass|circuit|light|ray|spring|pulley|battery|wire|temperature|system)\b",
        "rationale": "Some STEM diagrams are physical setups. They should enter physics only when all rules/quantities needed for verification are visible in the scene.",
        "annotation_contract": "components, quantities, arrows/rays/wires, explicit rule labels",
        "overlap_risk": "High with pages/science diagrams; use physics only for scenes requiring simple physics knowledge encoded in-scene.",
        "tasks": [
            {
                "task_id": "proposal:physics/experiment_setup/rule_output_value",
                "answer_type": "integer",
                "annotation_type": "component_set",
                "difficulty_knobs": "component count, rule count, arithmetic steps",
                "rationale": "Apply a displayed physical rule to a setup.",
            },
            {
                "task_id": "proposal:physics/experiment_setup/component_effect_label",
                "answer_type": "label",
                "annotation_type": "component_set",
                "difficulty_knobs": "component count, branch count, distractor labels",
                "rationale": "Identify the component causing a visible/defined effect.",
            },
        ],
    },
    {
        "priority": "P0",
        "domain": "puzzles",
        "scene_id": "strip_reconstruction",
        "support_configs": ["spatial_action-spatial_ssrl", "spatial_action-visual_jigsaw_2d"],
        "pattern": r"\b(shuffled|strip|patch|restore|reassemble|missing part|alignment|continuity)\b",
        "rationale": "Vero spatial_ssl and jigsaw examples repeatedly ask for strip/patch reconstruction. TRACE has jigsaw and missing patch tasks, but not strip/region ordering as a first-class scene.",
        "annotation_contract": "strip/patch ids, option ids, edge-continuity refs, position slots",
        "overlap_risk": "Medium with `image_cutout_board` and `missing_patch_options`; require ordered reconstruction output.",
        "tasks": [
            {
                "task_id": "proposal:puzzles/strip_reconstruction/order_label",
                "answer_type": "ordered_label_sequence",
                "annotation_type": "bbox_set",
                "difficulty_knobs": "strip count, orientation, edge texture detail, distractor continuity",
                "rationale": "Return the correct left-to-right/top-to-bottom strip order.",
            },
            {
                "task_id": "proposal:puzzles/strip_reconstruction/missing_region_option_label",
                "answer_type": "label",
                "annotation_type": "bbox_set",
                "difficulty_knobs": "option count, masked area size, edge clues",
                "rationale": "Choose a missing region from candidate patches.",
            },
        ],
    },
    {
        "priority": "P1",
        "domain": "puzzles",
        "scene_id": "voxel_projection",
        "support_configs": ["spatial_action-game_QA"],
        "pattern": r"\b(voxel|3d reconstruction|projection|minecraft|cubes|structure)\b",
        "rationale": "Vero game_QA includes 3D reconstruction and cube-building puzzles. TRACE has cube-count scenes, but not projection-constrained reconstruction.",
        "annotation_contract": "voxel coordinates, visible projections, candidate additions, face visibility",
        "overlap_risk": "Medium with cube/3D puzzle scenes; require projection constraints.",
        "tasks": [
            {
                "task_id": "proposal:puzzles/voxel_projection/missing_count",
                "answer_type": "integer",
                "annotation_type": "voxel_set",
                "difficulty_knobs": "grid size, projection count, hidden voxel count",
                "rationale": "Count voxels needed to satisfy displayed projections.",
            },
            {
                "task_id": "proposal:puzzles/voxel_projection/candidate_match_label",
                "answer_type": "label",
                "annotation_type": "voxel_set",
                "difficulty_knobs": "candidate count, projection ambiguity, distractor structures",
                "rationale": "Choose the candidate structure matching all projections.",
            },
        ],
    },
    {
        "priority": "P1",
        "domain": "puzzles",
        "scene_id": "color_sudoku",
        "support_configs": ["spatial_action-game_QA"],
        "pattern": r"\b(sudoku|rows columns|duplicate colours|empty cells)\b",
        "rationale": "Vero game_QA has color Sudoku tasks. This is better as a puzzle scene than a classic game scene because the core reasoning is grid constraint propagation.",
        "annotation_contract": "cell grid, color palette, row/column/subgrid constraints, queried cells",
        "overlap_risk": "Medium with `logic_grid` and `cell_board`; require Sudoku row/column/subgrid constraints.",
        "tasks": [
            {
                "task_id": "proposal:puzzles/color_sudoku/missing_cell_label",
                "answer_type": "label",
                "annotation_type": "cell_set",
                "difficulty_knobs": "grid size, empty-cell count, palette size, inference depth",
                "rationale": "Infer the color/value of a queried empty cell.",
            },
            {
                "task_id": "proposal:puzzles/color_sudoku/candidate_count",
                "answer_type": "integer",
                "annotation_type": "cell_set",
                "difficulty_knobs": "candidate palette size, clue density, queried region",
                "rationale": "Count valid candidates for a cell or region.",
            },
        ],
    },
    {
        "priority": "P1",
        "domain": "puzzles",
        "scene_id": "tents",
        "support_configs": ["spatial_action-game_QA"],
        "pattern": r"\b(tents puzzle|trees|tents|row.*column)\b",
        "rationale": "Vero game_QA includes Tents puzzles with row/column counts and tree adjacency constraints.",
        "annotation_contract": "cell grid, tree cells, row/column clues, tent candidates",
        "overlap_risk": "Medium with cell-board counting; require Tents-specific adjacency constraints.",
        "tasks": [
            {
                "task_id": "proposal:puzzles/tents/forced_tent_count",
                "answer_type": "integer",
                "annotation_type": "cell_set",
                "difficulty_knobs": "grid size, tree count, clue tightness, candidate cells",
                "rationale": "Count cells forced to contain tents.",
            },
            {
                "task_id": "proposal:puzzles/tents/valid_candidate_label",
                "answer_type": "label",
                "annotation_type": "cell_set",
                "difficulty_knobs": "candidate count, adjacency ambiguity, row/column clue density",
                "rationale": "Choose the candidate cell satisfying all visible Tents constraints.",
            },
        ],
    },
    {
        "priority": "P1",
        "domain": "puzzles",
        "scene_id": "rubiks_net",
        "support_configs": ["spatial_action-game_QA"],
        "pattern": r"\b(rubik|unfolded|cube.*view|3d views)\b",
        "rationale": "Vero game_QA has Rubik/unfolded cube view reasoning. TRACE has cube projections, but not colored cube-net face correspondence.",
        "annotation_contract": "cube faces, net cells, colors, view-camera mapping",
        "overlap_risk": "Medium with cube projection scenes; require cube-net/color mapping.",
        "tasks": [
            {
                "task_id": "proposal:puzzles/rubiks_net/hidden_face_color_label",
                "answer_type": "label",
                "annotation_type": "face_set",
                "difficulty_knobs": "visible views, color count, net ambiguity",
                "rationale": "Infer a hidden/queried face color from multiple views and unfolded net.",
            },
            {
                "task_id": "proposal:puzzles/rubiks_net/adjacent_face_count",
                "answer_type": "integer",
                "annotation_type": "face_set",
                "difficulty_knobs": "face count, queried color, view count",
                "rationale": "Count faces adjacent to a queried face/color in the cube net.",
            },
        ],
    },
    {
        "priority": "P2",
        "domain": "puzzles",
        "scene_id": "clock_collection",
        "support_configs": ["knowledge_recognition-iconqa", "stem-mmk12"],
        "pattern": r"\b(clock|time|earlier|later|first|last|schedule|calendar|date)\b",
        "rationale": "Vero/IconQA includes elementary time comparison questions. TRACE has clocks and schedules, so this is a lower-priority scene unless examples combine named events with clocks.",
        "annotation_contract": "clock faces, event labels, date/schedule rows",
        "overlap_risk": "High with `clock_collection` and `day_schedule_layout`; prefer adding tasks to existing scenes first.",
        "tasks": [
            {
                "task_id": "proposal:symbolic/clock_collection/event_clock_order_label",
                "answer_type": "label",
                "annotation_type": "bbox_set",
                "difficulty_knobs": "clock count, minute offsets, event label count, AM/PM ambiguity",
                "rationale": "Identify which named event happens first/last based on clocks.",
            },
            {
                "task_id": "proposal:symbolic/clock_collection/clock_schedule_gap_value",
                "answer_type": "integer",
                "annotation_type": "bbox_set",
                "difficulty_knobs": "clock count, interval count, minute arithmetic",
                "rationale": "Compute a time gap between clock-labeled events.",
            },
        ],
    },
]


EXISTING_SCENE_TASK_CANDIDATES: list[dict[str, Any]] = [
    {
        "priority": "P1",
        "domain": "charts",
        "scene_id": "curve_panels",
        "support_configs": ["chart_ocr-arxivqa_formatted", "chart_ocr-reachqa", "chart_ocr-ecd_vqa"],
        "pattern": r"\b(panel|figure|legend|curve|series|subplot|highest|lowest|increase|decrease)\b",
        "task_id": "proposal:charts/curve_panels/legend_conditioned_panel_count",
        "answer_type": "integer",
        "annotation_type": "point_set",
        "difficulty_knobs": "panel count, legend count, curve overlap, comparison threshold",
        "overlap_risk": "Low if it requires cross-panel legend-conditioned reasoning.",
        "rationale": "Count panels where a legend-selected series satisfies a visual condition.",
    },
    {
        "priority": "P1",
        "domain": "pages",
        "scene_id": "infographic",
        "support_configs": ["chart_ocr-infographic_vqa", "chart_ocr-CoSyn_400k_chart", "chart_ocr-evochart"],
        "pattern": r"\b(infographic|percentage|percent|number of|total|reported|recovered|section)\b",
        "task_id": "task_pages__infographic__section_ranked_total_label",
        "answer_type": "label",
        "annotation_type": "bbox_set",
        "difficulty_knobs": "section count, item count, icon-array scale, rank target",
        "overlap_risk": "Low if it uses section aggregation rather than single metric lookup.",
        "rationale": "Identify a section/card by ranked aggregate value.",
    },
    {
        "priority": "P1",
        "domain": "games",
        "scene_id": "cards",
        "support_configs": ["spatial_action-game_QA"],
        "pattern": r"\b(solitaire|klondike|playing card|card)\b",
        "task_id": "proposal:games/solitaire/tableau_transfer_count",
        "answer_type": "integer",
        "annotation_type": "bbox_set",
        "difficulty_knobs": "visible card count, stack count, legal transfer rules",
        "overlap_risk": "Medium; may become new `solitaire` scene if tableau layout is required.",
        "rationale": "Extend card reasoning from flat hands to tableau-like move counting if scene reuse is feasible.",
    },
    {
        "priority": "P1",
        "domain": "geometry",
        "scene_id": "circle_theorem_diagram",
        "support_configs": ["stem-geo170k", "stem-geoqa_plus", "stem-wemath20_standard"],
        "pattern": r"\b(circle|radius|diameter|chord|arc|tangent|secant|angle)\b",
        "task_id": "task_geometry__circle_theorem__multi_step_angle_value",
        "answer_type": "integer",
        "annotation_type": "arc_set",
        "difficulty_knobs": "known arc count, theorem chain length, distractor chords",
        "overlap_risk": "Medium; ensure it is not just another wrapper for existing circle value tasks.",
        "rationale": "Vero geometry supports more multi-step circle angle/arc inference.",
    },
    {
        "priority": "P2",
        "domain": "graph",
        "scene_id": "node_link",
        "support_configs": ["chart_ocr-CoSyn_400k_diagram", "stem-ai2d_merged"],
        "pattern": r"\b(arrow|node|connect|path|flow|dependency)\b",
        "task_id": "proposal:graph/node_link/label_filtered_path_count",
        "answer_type": "integer",
        "annotation_type": "node_edge_set",
        "difficulty_knobs": "node count, edge labels, allowed-label filters, path length",
        "overlap_risk": "High with pages process diagrams; only include for abstract graphs.",
        "rationale": "If image inspection finds abstract node-link diagrams, add label-filtered path reasoning.",
    },
    {
        "priority": "P0",
        "domain": "icons",
        "scene_id": "icon_field",
        "support_configs": ["counting_grounding_search-multihop", "counting_grounding_search-visual_probe", "counting_grounding_search-oodvqa"],
        "pattern": r"\b(left|right|above|below|between|near|how many|count)\b",
        "task_id": "proposal:icons/icon_field/multihop_relation_count",
        "answer_type": "integer",
        "annotation_type": "bbox_set",
        "difficulty_knobs": "relation chain length, object density, attribute conjunctions, landmark count",
        "overlap_risk": "Low; current icon field has too little multi-hop grounding coverage.",
        "rationale": "Convert Vero object grounding into synthetic multi-hop icon relation counting.",
    },
    {
        "priority": "P1",
        "domain": "icons",
        "scene_id": "pattern_grid",
        "support_configs": ["knowledge_recognition-iconqa"],
        "pattern": r"\b(how many|shape|square|star|heart|spinner|marble|likely)\b",
        "task_id": "proposal:icons/pattern_grid/probability_or_count_label",
        "answer_type": "label_or_integer",
        "annotation_type": "bbox_set",
        "difficulty_knobs": "grid size, shape palette, answer options, target condition",
        "overlap_risk": "Medium; split probability into new scene if it becomes visually distinct.",
        "rationale": "IconQA has repeated synthetic pattern/count/probability questions.",
    },
    {
        "priority": "P0",
        "domain": "pages",
        "scene_id": "web_action",
        "support_configs": ["spatial_action-magma_aitw", "spatial_action-magma_mind2web", "counting_grounding_search-groundui"],
        "pattern": r"\b(click|tap|button|menu|webpage|screen|select|element)\b",
        "task_id": "proposal:pages/web_action/instruction_target_label",
        "answer_type": "label",
        "annotation_type": "bbox",
        "difficulty_knobs": "control count, role ambiguity, text similarity, state filters",
        "overlap_risk": "Low; pages has GUI scenes but each currently has few tasks.",
        "rationale": "Vero has high UI/action coverage; add target-label tasks using synthetic screen metadata.",
    },
    {
        "priority": "P1",
        "domain": "pages",
        "scene_id": "map",
        "support_configs": ["counting_grounding_search-aerialvg", "counting_grounding_search-osatlas"],
        "pattern": r"\b(map|route|north|south|east|west|location|landmark)\b",
        "task_id": "proposal:pages/map/compass_relation_count",
        "answer_type": "integer",
        "annotation_type": "bbox_set",
        "difficulty_knobs": "landmark count, compass relation depth, route count",
        "overlap_risk": "Medium; use existing `map` if aerial-style rendering is not needed.",
        "rationale": "Add Vero-style map grounding as relation/count tasks.",
    },
    {
        "priority": "P2",
        "domain": "physics",
        "scene_id": "resistor_network",
        "support_configs": ["stem-ai2d_merged", "stem-mmk12", "stem-visualwebinstruct"],
        "pattern": r"\b(circuit|battery|resistor|wire|current|voltage)\b",
        "task_id": "proposal:physics/resistor_network/labeled_branch_value",
        "answer_type": "integer",
        "annotation_type": "component_set",
        "difficulty_knobs": "branch count, labeled component count, series/parallel depth",
        "overlap_risk": "Medium; only add if Vero examples show enough circuit-style diagrams.",
        "rationale": "Use STEM diagrams to expand circuit reasoning if in-scene rules/values are explicit.",
    },
    {
        "priority": "P1",
        "domain": "puzzles",
        "scene_id": "maze",
        "support_configs": ["spatial_action-game_QA"],
        "pattern": r"\b(maze|player|goal|obstacle|navigate)\b",
        "task_id": "proposal:puzzles/maze/shortest_path_length",
        "answer_type": "integer",
        "annotation_type": "path",
        "difficulty_knobs": "grid size, obstacle density, branch count, route constraints",
        "overlap_risk": "Low; current maze tasks are mostly reachability/exit count.",
        "rationale": "Vero game_QA has maze mini-games that support path-length and route-following tasks.",
    },
    {
        "priority": "P1",
        "domain": "puzzles",
        "scene_id": "raven_matrix",
        "support_configs": ["stem-raven"],
        "pattern": r"\b(logical sequence|complete|puzzle|figure|question mark)\b",
        "task_id": "proposal:puzzles/raven_matrix/rule_axis_label",
        "answer_type": "label",
        "annotation_type": "bbox_set",
        "difficulty_knobs": "matrix size, rule axes, attribute palette, option count",
        "overlap_risk": "Medium; avoid duplicate option-pick wrappers by asking about rule/annotation properties.",
        "rationale": "Add diagnostic Raven tasks beyond choosing the missing option.",
    },
    {
        "priority": "P2",
        "domain": "puzzles",
        "scene_id": "clock_collection",
        "support_configs": ["knowledge_recognition-iconqa", "stem-mmk12"],
        "pattern": r"\b(clock|time|earlier|later|first|last)\b",
        "task_id": "proposal:symbolic/clock_collection/named_event_order_label",
        "answer_type": "label",
        "annotation_type": "bbox_set",
        "difficulty_knobs": "clock count, minute offsets, labels, AM/PM markers",
        "overlap_risk": "Low if event labels are used; otherwise overlaps with basic clock comparison.",
        "rationale": "IconQA-style named clock comparisons can expand clock reasoning tasks without a new scene.",
    },
]


EXCLUSIONS: list[dict[str, str]] = [
    {
        "source": "captioning_IF-*",
        "domain": "-",
        "reason": "Free-form captioning/instruction-following; no typed metadata-grounded verifier contract.",
    },
    {
        "source": "knowledge_recognition-* except IconQA-style synthetic patterns",
        "domain": "-",
        "reason": "Mostly natural-image recognition or external knowledge; use only as synthetic icon/pattern inspiration.",
    },
    {
        "source": "spatial_action-robo2vlm",
        "domain": "-",
        "reason": "Embodied robotics/natural-scene action. Defer unless TRACE adds a synthetic robotics domain.",
    },
    {
        "source": "stem-pathvqa and stem-vqarad",
        "domain": "-",
        "reason": "Medical/radiology content outside current synthetic TRACE scope.",
    },
    {
        "source": "OCR-only value lookup in chart/table/page examples",
        "domain": "charts/pages",
        "reason": "Likely too easy and not sufficiently reasoning-heavy unless converted to arithmetic/comparison/reconciliation.",
    },
]


NEW_DOMAIN_CANDIDATES: list[dict[str, str]] = [
    {
        "candidate_domain": "natural_images",
        "recommendation": "defer",
        "support_source": "captioning_IF, knowledge_recognition, counting_grounding_search natural-image subsets",
        "reason": "Large Vero support but conflicts with current fully synthetic TRACE scope.",
    },
    {
        "candidate_domain": "robotics",
        "recommendation": "defer",
        "support_source": "spatial_action-robo2vlm",
        "reason": "Could be synthetic in the future, but current examples are embodied natural-scene actions and not enough to justify a domain now.",
    },
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        lines.append("| " + " | ".join(str(cell).replace("\n", " ") for cell in row) + " |")
    return "\n".join(lines)


def match_text(row: dict[str, Any]) -> str:
    return " ".join(
        str(row.get(key, ""))
        for key in ("config", "data_source", "question", "template", "question_kind")
    ).lower()


def support_for_candidate(
    candidate: dict[str, Any],
    samples: list[dict[str, Any]],
    config_rows: dict[str, int],
    sampled_counts: Counter[str],
) -> dict[str, Any]:
    configs = set(candidate["support_configs"])
    pattern = re.compile(candidate["pattern"], re.IGNORECASE)
    hits_by_config: Counter[str] = Counter()
    examples: list[str] = []
    for row in samples:
        if row["config"] not in configs:
            continue
        if not pattern.search(match_text(row)):
            continue
        hits_by_config[row["config"]] += 1
        if len(examples) < 3:
            examples.append(str(row.get("question", "")).replace("\n", " ")[:220])

    sample_hits = sum(hits_by_config.values())
    estimated_hits = 0
    for config, hits in hits_by_config.items():
        sampled = sampled_counts.get(config, 0)
        if sampled:
            estimated_hits += round(config_rows.get(config, 0) * hits / sampled)
    support_rows = sum(config_rows.get(config, 0) for config in configs)
    if not examples:
        for row in samples:
            if row["config"] in configs and len(examples) < 3:
                examples.append(str(row.get("question", "")).replace("\n", " ")[:220])
    return {
        "sample_hits": sample_hits,
        "estimated_hits": estimated_hits,
        "support_rows_upper_bound": support_rows,
        "sample_hits_by_config": "; ".join(f"{k}:{v}" for k, v in hits_by_config.most_common()),
        "examples": examples,
    }


def flatten_new_scene_rows(
    candidates: list[dict[str, Any]],
    samples: list[dict[str, Any]],
    config_rows: dict[str, int],
    sampled_counts: Counter[str],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    support_by_key: dict[str, dict[str, Any]] = {}
    rows = []
    for candidate in candidates:
        support = support_for_candidate(candidate, samples, config_rows, sampled_counts)
        key = f"{candidate['domain']}::{candidate['scene_id']}"
        support_by_key[key] = support
        rows.append(
            {
                "priority": candidate["priority"],
                "domain": candidate["domain"],
                "scene_id": candidate["scene_id"],
                "scene_status": "new_scene",
                "support_configs": ";".join(candidate["support_configs"]),
                "sample_hits": support["sample_hits"],
                "estimated_hits": support["estimated_hits"],
                "support_rows_upper_bound": support["support_rows_upper_bound"],
                "sample_hits_by_config": support["sample_hits_by_config"],
                "proposed_task_ids": ";".join(task["task_id"] for task in candidate["tasks"]),
                "annotation_contract": candidate["annotation_contract"],
                "difficulty_knobs": " | ".join(task["difficulty_knobs"] for task in candidate["tasks"]),
                "overlap_risk": candidate["overlap_risk"],
                "rationale": candidate["rationale"],
                "representative_examples": " || ".join(support["examples"]),
            }
        )
    return rows, support_by_key


def flatten_existing_task_rows(
    candidates: list[dict[str, Any]],
    samples: list[dict[str, Any]],
    config_rows: dict[str, int],
    sampled_counts: Counter[str],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    support_by_key: dict[str, dict[str, Any]] = {}
    rows = []
    for candidate in candidates:
        support = support_for_candidate(candidate, samples, config_rows, sampled_counts)
        key = f"{candidate['domain']}::{candidate['scene_id']}::{candidate['task_id']}"
        support_by_key[key] = support
        rows.append(
            {
                "priority": candidate["priority"],
                "domain": candidate["domain"],
                "scene_id": candidate["scene_id"],
                "task_id": candidate["task_id"],
                "scene_status": "existing_scene",
                "support_configs": ";".join(candidate["support_configs"]),
                "sample_hits": support["sample_hits"],
                "estimated_hits": support["estimated_hits"],
                "support_rows_upper_bound": support["support_rows_upper_bound"],
                "sample_hits_by_config": support["sample_hits_by_config"],
                "answer_type": candidate["answer_type"],
                "annotation_type": candidate["annotation_type"],
                "difficulty_knobs": candidate["difficulty_knobs"],
                "overlap_risk": candidate["overlap_risk"],
                "rationale": candidate["rationale"],
                "representative_examples": " || ".join(support["examples"]),
            }
        )
    return rows, support_by_key


def current_scenes_by_domain(scene_rows: list[dict[str, str]]) -> dict[str, list[tuple[str, int]]]:
    grouped: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for row in scene_rows:
        grouped[row["domain"]].append((row["scene_id"], int(row["task_count"])))
    for scenes in grouped.values():
        scenes.sort()
    return grouped


def inspected_sources_for_domain(domain: str, new_rows: list[dict[str, Any]], existing_rows: list[dict[str, Any]]) -> str:
    configs: set[str] = set()
    for row in new_rows + existing_rows:
        if row["domain"] == domain:
            configs.update(config for config in row["support_configs"].split(";") if config)
    return ", ".join(f"`{config}`" for config in sorted(configs)) or "-"


def write_round2_markdown(
    path: Path,
    new_rows: list[dict[str, Any]],
    existing_rows: list[dict[str, Any]],
    scene_rows: list[dict[str, str]],
    exclusions: list[dict[str, str]],
    new_domain_rows: list[dict[str, str]],
) -> None:
    scenes_by_domain = current_scenes_by_domain(scene_rows)
    new_by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    existing_by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in new_rows:
        new_by_domain[row["domain"]].append(row)
    for row in existing_rows:
        existing_by_domain[row["domain"]].append(row)

    lines = [
        "# Vero Round-2 Domain Expansion Analysis",
        "",
        f"Generated: {dt.datetime.now(dt.UTC).isoformat(timespec='seconds')}",
        "",
        "This pass reinterprets Vero-600k at the scene/task level instead of only mapping whole configs to one TRACE scene. It is intentionally analysis-only: no task/config/taxonomy code is changed.",
        "",
        "## Summary",
        "",
        md_table(
            ["domain", "new scene candidates", "existing-scene task candidates"],
            [
                [domain, len(new_by_domain.get(domain, [])), len(existing_by_domain.get(domain, []))]
                for domain in ACTIVE_DOMAIN_NAMES
            ],
        ),
        "",
        "## Inclusion Rule",
        "",
        "- Keep TRACE fully synthetic: Vero supplies coverage pressure and visual/task patterns, not images to ingest.",
        "- Recommend a new scene only when the visual grammar is distinct from current TRACE scenes or when existing scenes would obscure a materially different annotation contract.",
        "- Recommend a new task in an existing scene when the renderer/annotation contract can stay the same and only the reasoning changes.",
        "- Treat config-level row counts as upper bounds; `estimated_hits` are based on first-pass sampled rows and should be validated by image inspection before implementation.",
        "",
        "## Domain Implementation Workflow",
        "",
        "When working within a domain, use this order:",
        "",
        "1. Add and evaluate proposed tasks for existing active scenes first.",
        "2. After existing-scene task opportunities are exhausted or rejected, add a new scene renderer.",
        "3. Add tasks under that new scene only after the scene grammar, annotation contract, and task-review samples are clear.",
        "",
        "This keeps domain changes incremental: existing renderers get expanded before we introduce new visual grammars.",
        "",
    ]

    for domain in ACTIVE_DOMAIN_NAMES:
        lines.extend([f"## {domain.title()}", ""])
        scenes = scenes_by_domain.get(domain, [])
        lines.append("Current TRACE scenes:")
        lines.append(
            ", ".join(f"`{scene}` ({count})" for scene, count in scenes) if scenes else "-"
        )
        lines.extend(["", f"Vero sources inspected: {inspected_sources_for_domain(domain, new_rows, existing_rows)}", ""])

        domain_new = sorted(
            new_by_domain.get(domain, []),
            key=lambda row: (row["priority"], -int(row["estimated_hits"]), row["scene_id"]),
        )
        lines.append("### Proposed New Scenes")
        if domain_new:
            for row in domain_new:
                lines.extend(
                    [
                        f"- `{row['scene_id']}` ({row['priority']}): estimated `{int(row['estimated_hits']):,}` hits from `{row['sample_hits']}` sampled matches; upper-bound config rows `{int(row['support_rows_upper_bound']):,}`.",
                        f"  Tasks: {', '.join(f'`{task}`' for task in row['proposed_task_ids'].split(';'))}.",
                        f"  Annotation: {row['annotation_contract']}.",
                        f"  Why: {row['rationale']}",
                        f"  Overlap risk: {row['overlap_risk']}",
                    ]
                )
        else:
            lines.append("- None recommended in this pass.")
        lines.append("")

        domain_existing = sorted(
            existing_by_domain.get(domain, []),
            key=lambda row: (row["priority"], -int(row["estimated_hits"]), row["scene_id"], row["task_id"]),
        )
        lines.append("### Proposed Tasks In Existing Scenes")
        if domain_existing:
            for row in domain_existing:
                lines.extend(
                    [
                        f"- `{row['task_id']}` in `{row['scene_id']}` ({row['priority']}): estimated `{int(row['estimated_hits']):,}` hits from `{row['sample_hits']}` sampled matches.",
                        f"  Answer/annotation: `{row['answer_type']}` / `{row['annotation_type']}`.",
                        f"  Difficulty knobs: {row['difficulty_knobs']}.",
                        f"  Why: {row['rationale']}",
                        f"  Overlap risk: {row['overlap_risk']}",
                    ]
                )
        else:
            lines.append("- None recommended in this pass.")
        lines.append("")

        domain_exclusions = [row for row in exclusions if row["domain"] in {domain, "-", f"{domain}/pages", "charts/pages"}]
        lines.append("### Exclusions / Deferrals")
        if domain_exclusions:
            for row in domain_exclusions:
                lines.append(f"- `{row['source']}`: {row['reason']}")
        else:
            lines.append("- No domain-specific exclusions beyond the global synthetic/verifier constraints.")
        lines.append("")

    lines.extend(
        [
            "## New Domain Assessment",
            "",
            "No new domain is recommended for the current fully synthetic TRACE scope.",
            "",
            md_table(
                ["candidate domain", "recommendation", "support source", "reason"],
                [
                    [row["candidate_domain"], row["recommendation"], row["support_source"], row["reason"]]
                    for row in new_domain_rows
                ],
            ),
            "",
            "## Recommended Implementation Order",
            "",
            "Within each domain, first implement the proposed tasks in existing scenes, then move to new scene -> task implementation.",
            "",
            "1. `games/minesweeper` and `puzzles/strip_reconstruction`: high novelty, clean annotation, strong Vero support.",
            "2. `pages/science_process` and `icons/icon_field` multi-hop tasks: broad Vero coverage and clear synthetic proxies.",
            "3. `puzzles/color_sudoku`, `puzzles/tents`, and `games/arcade_grid`: good coverage but need careful difficulty tuning.",
            "4. `geometry/composite_measurement` and `charts/table_combo`: strong coverage but higher implementation effort.",
            "5. P2 scenes (`measurement_tool`, `semantic_node_link`, `experiment_setup`, clock-collection expansions): defer until P0/P1 candidates are inspected visually.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def update_readme(review_dir: Path, new_rows: list[dict[str, Any]], existing_rows: list[dict[str, Any]]) -> None:
    readme_path = review_dir / "README.md"
    if not readme_path.exists():
        return
    text = readme_path.read_text(encoding="utf-8")
    marker = "## Round-2 Expansion Analysis"
    if marker in text:
        text = text[: text.index(marker)].rstrip() + "\n"
    insertion = f"""
## Round-2 Expansion Analysis

The second-pass scene/task expansion analysis is in `round2_domain_expansion.md`.

- New scene candidates: {len(new_rows)}
- Existing-scene task candidates: {len(existing_rows)}
- Machine-readable tables:
  - `round2_scene_candidates.csv`
  - `round2_existing_scene_task_candidates.csv`
  - `round2_exclusions.csv`
  - `round2_new_domain_candidates.csv`

This pass is domain-by-domain and includes the current public domains:
{", ".join(f"`{domain}`" for domain in ACTIVE_DOMAIN_NAMES)}. It also records
that no new domain is recommended while TRACE remains fully synthetic.
"""
    if "## Important Caveat" in text:
        text = text.replace("## Important Caveat", insertion.strip() + "\n\n## Important Caveat", 1)
    else:
        text = text.rstrip() + "\n\n" + insertion.strip() + "\n"
    readme_path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-dir", type=Path, default=DEFAULT_REVIEW_DIR)
    args = parser.parse_args()

    review_dir = args.review_dir
    configs = read_csv(review_dir / "config_inventory.csv")
    scenes = read_csv(review_dir / "trace_scene_inventory.csv")
    samples = read_jsonl(review_dir / "sample_questions.jsonl")

    config_rows = {row["config"]: int(row["num_rows"]) for row in configs}
    sampled_counts = Counter(row["config"] for row in samples)

    new_scene_rows, _ = flatten_new_scene_rows(
        NEW_SCENE_CANDIDATES, samples, config_rows, sampled_counts
    )
    existing_scene_rows, _ = flatten_existing_task_rows(
        EXISTING_SCENE_TASK_CANDIDATES, samples, config_rows, sampled_counts
    )

    write_csv(
        review_dir / "round2_scene_candidates.csv",
        new_scene_rows,
        [
            "priority",
            "domain",
            "scene_id",
            "scene_status",
            "support_configs",
            "sample_hits",
            "estimated_hits",
            "support_rows_upper_bound",
            "sample_hits_by_config",
            "proposed_task_ids",
            "annotation_contract",
            "difficulty_knobs",
            "overlap_risk",
            "rationale",
            "representative_examples",
        ],
    )
    write_csv(
        review_dir / "round2_existing_scene_task_candidates.csv",
        existing_scene_rows,
        [
            "priority",
            "domain",
            "scene_id",
            "task_id",
            "scene_status",
            "support_configs",
            "sample_hits",
            "estimated_hits",
            "support_rows_upper_bound",
            "sample_hits_by_config",
            "answer_type",
            "annotation_type",
            "difficulty_knobs",
            "overlap_risk",
            "rationale",
            "representative_examples",
        ],
    )
    write_csv(
        review_dir / "round2_exclusions.csv",
        EXCLUSIONS,
        ["source", "domain", "reason"],
    )
    write_csv(
        review_dir / "round2_new_domain_candidates.csv",
        NEW_DOMAIN_CANDIDATES,
        ["candidate_domain", "recommendation", "support_source", "reason"],
    )
    write_round2_markdown(
        review_dir / "round2_domain_expansion.md",
        new_scene_rows,
        existing_scene_rows,
        scenes,
        EXCLUSIONS,
        NEW_DOMAIN_CANDIDATES,
    )
    update_readme(review_dir, new_scene_rows, existing_scene_rows)

    print(f"Wrote round-2 Vero expansion analysis to {review_dir}")
    print(f"new_scene_candidates={len(new_scene_rows)}")
    print(f"existing_scene_task_candidates={len(existing_scene_rows)}")


if __name__ == "__main__":
    main()
