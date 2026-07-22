#!/usr/bin/env python3
"""Build the one-page-per-domain Trace appendix atlas."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SAMPLES_PER_DOMAIN = 12
ATLAS_COLUMNS = 3
DEFAULT_SEED = 20260714
NORMAL_PROMPT_MAX_CHARACTERS = 220
FULL_PROMPT_MAX_CHARACTERS = 320
DOMAIN_ORDER = (
    "charts",
    "games",
    "geometry",
    "graph",
    "icons",
    "illustrations",
    "pages",
    "physics",
    "puzzles",
    "symbolic",
    "three_d",
)
DOMAIN_TITLES = {
    "charts": "Charts",
    "geometry": "Geometry",
    "graph": "Graphs",
    "physics": "Physics",
    "games": "Games",
    "puzzles": "Puzzles",
    "symbolic": "Symbolic",
    "three_d": "3D",
    "pages": "Pages",
    "icons": "Icons",
    "illustrations": "Illustrations",
}
DOMAIN_CAPTION_NOUNS = {
    "charts": "chart",
    "geometry": "geometry",
    "graph": "graph",
    "physics": "physics",
    "games": "game",
    "puzzles": "puzzle",
    "symbolic": "symbolic",
    "three_d": "3D",
    "pages": "page",
    "icons": "icon",
    "illustrations": "illustration",
}

TITLE_OVERRIDES = {
    "task_charts__matrix__off_diagonal_confusion_label": (
        "Matrix: Off-Diagonal Confusion"
    ),
    "task_charts__size_encoding__panel_category_extremum_panel_label": (
        "Size Encoding: Category Extremum Across Panels"
    ),
    "task_charts__single_series__threshold_value_count": (
        "Single Series: Threshold Count"
    ),
    "task_games__pacman__next_item_label": "Pac-Man: Next Item",
    "task_games__snakes_ladders__remaining_to_finish_value": (
        "Snakes and Ladders: Remaining Distance to Finish"
    ),
    "task_geometry__circle_theorem__inscribed_angle_value_inscribed_angle_from_arc": (
        "Circle Theorem: Inscribed Angle from Arc"
    ),
    "task_geometry__circle_pair_tangents__external_tangent_segment_length_value": (
        "Circle Pair Tangents: Center Distance"
    ),
    "task_graph__phylogeny_tree__mrca_clade_membership_count": (
        "Phylogeny Tree: MRCA Clade Membership"
    ),
    "task_icons__named_path__path_neighbor_label": "Named Path: Immediate Successor",
    "task_illustrations__rpg_dungeon__safe_reachable_chest_count": (
        "RPG Dungeon: Safe Reachable Chest"
    ),
    "task_illustrations__rpg_tactical_map__water_barrier_unreachable_tile_label": (
        "RPG Tactical Map: Water-Barrier Unreachable Tile"
    ),
    "task_illustrations__rpg_house__adjacent_room_count": (
        "RPG House: Adjacent Room"
    ),
    "task_pages__mixed_infographic_page__two_module_field_total_comparison_module_label": (
        "Mixed Infographic Page: Field-Total Comparison"
    ),
    "task_pages__profile_card_grid__field_ranked_profile_label": (
        "Profile Card Grid: Highest-Value Profile"
    ),
    "task_puzzles__rubiks_net__post_move_face_color_count_label": (
        "Rubik's Cube Net: Post-Move Face Color Count"
    ),
    "task_puzzles__pipe_flow__pipe_flow_repair_tile_label": "Pipe Flow: Repair Tile",
    "task_puzzles__cyclic_order__cyclic_order_equivalent_label": (
        "Cyclic Order: Equivalent Arrangement"
    ),
    "task_puzzles__raven_matrix__raven_spatial_transform_label": (
        "Raven Matrix: Spatial Transform"
    ),
    "task_symbolic__abacus__displayed_value_readout": "Abacus: Displayed Value",
    "task_symbolic__dice__pair_attribute_combo_probability": (
        "Dice: Joint Even-Value Probability"
    ),
    "task_symbolic__spinner__multi_attribute_and_probability": (
        "Spinner: Color-and-Shape Probability"
    ),
    "task_symbolic__turing_tape__turing_written_symbol_count": (
        "Turing Tape: Written-Symbol Count"
    ),
    "task_three_d__object_cluster__multi_attribute_exclusion_count": (
        "Object Cluster: Color-and-Type Exclusion"
    ),
    "task_three_d__object_cluster__multi_attribute_or_count": (
        "Object Cluster: Type-or-Color Count"
    ),
    "task_three_d__object_scene__reference_nearest_label": (
        "Object Scene: Nearest to Reference"
    ),
    "task_three_d__room__wall_object_same_wall_reference_label": (
        "Room: Object on the Reference Wall"
    ),
    "task_three_d__carousel__object_type_ordered_adjacent_pair_count": (
        "Carousel: Ordered Adjacent Pair Count"
    ),
    "task_three_d__conveyor__object_type_ordered_adjacent_pair_count": (
        "Conveyor: Ordered Adjacent Pair Count"
    ),
    "task_three_d__conveyor__belt_total_object_count": (
        "Conveyor: Objects on Selected Belt"
    ),
    "task_three_d__surface_fixture__repeated_element_count": (
        "Surface Fixture: U-Bolt Count"
    ),
}

TITLE_SMALL_WORDS = frozenset(
    {"and", "as", "at", "by", "for", "from", "in", "of", "on", "or", "the", "to"}
)
TITLE_ACRONYMS = {
    "3d": "3D",
    "iqr": "IQR",
    "mrca": "MRCA",
    "rpg": "RPG",
}

# Publication-facing rewrites remove repetitive generic scaffolding while
# preserving every rule needed to answer the selected instance. Source hashes
# force explicit review whenever an underlying task prompt changes.
CURATED_PROMPT_OVERRIDES: dict[str, tuple[str, str]] = {
    "task_charts__error_interval__reference_containment_count": (
        "1d405668fe4c3e307b731bd992cdb1709d9d0f50b4f53d78024114d5760a42b4",
        "The image shows a horizontal interval chart with labeled categories, "
        "point estimates, and lower-to-upper interval whiskers. How many intervals "
        "contain the reference value 54?",
    ),
    "task_charts__region_map__numeric_interval_region_count": (
        "4e069555f353a76513bbe6cce13add1a6bec961c5122d9b033ad7dc4ca885cae",
        "This image shows a world map with selected countries colored by value and "
        "a color legend. How many countries fall in value bins between 20 and 99, "
        "inclusive?",
    ),
    "task_charts__population_pyramid__age_group_threshold_count": (
        "140065c573929b3849a9cd9894aae1569938f65d87106b60ab39830f2058ccac",
        "The image shows a mirrored horizontal bar chart with one row per age "
        "group. The left and right bars show the two legend series on the same "
        "positive scale. In how many age groups is the sum of Urban and Rural at "
        "most 140?",
    ),
    "task_games__pacman__next_item_label": (
        "7326829ed9dabd87edb8041d6761f7e67df547716686da8ebf0b8d0d98842fbf",
        "This scene shows a Pac-Man-style maze with a visible Pac-Man marker, "
        "ghosts, pellets, bonus items, and a highlighted route. Which labeled "
        "bonus item is encountered first along the highlighted route?",
    ),
    "task_geometry__rectangular_solid__open_box_net_dimension_value": (
        "e212e8e63dad027655ef01560a3560ab65d720392dcc7fa5aa2c2a82887ff608",
        "The diagram shows an open-box net with sheet dimensions, equal corner "
        "cutouts, and one missing base dimension. Using the sheet dimensions and "
        "cut size, find the marked base dimension.",
    ),
    "task_physics__wire_magnetism__wire_field_direction_choice": (
        "c42ddaccd12c9ee98227fcbd5334a1131eea19fc17b4cabf8c454b50d819d79e",
        "The diagram shows a current-carrying wire through the page, point P, and "
        "labeled arrow options. Use the current cue to determine the circular "
        "magnetic-field direction at P. Which arrow option matches that direction?",
    ),
    "task_physics__lever__missing_weight_balance_value": (
        "4e47b68a1ce4f4652d2ddfe6b965fb811365e8828bf6012680a495c235b91ecf",
        "The figure shows a lever with a fulcrum, distance marks, and weight blocks. "
        "What weight should replace the block marked with a question mark so the "
        "lever balances?",
    ),
    "task_physics__wave_interference__path_difference_value": (
        "0229561a31727b0ffaf5b435582d42e7f6eed967ab4d32af682d881fb95a12b8",
        "The diagram shows two labeled wave sources and their circular interference "
        "wavefronts. Using the visible wavefront spacing and labels, determine "
        "the absolute path difference between S1P and S2P in half-wavelength steps.",
    ),
    "task_icons__named_field__reference_distance_rank_label": (
        "6ff31dbc9b704c32fcc168db617699da307575eb125789d3cf2e331dec908c12",
        "The picture shows a panel with one reference icon, six option icons labeled "
        "A-F, and other icons. Which labeled icon is second closest to the magenta "
        "shield icon?",
    ),
    "task_puzzles__nonogram__candidate_solution_label": (
        "f134126720c75c0e0ead2c054d5b90f1276338978b622230237ae6cdb4afbea8",
        "This nonogram shows a clue grid with labeled filled-grid options. Use both "
        "clue rails to identify the correct candidate grid.",
    ),
    "task_puzzles__rubiks_net__post_move_face_color_count_label": (
        "687ec783793920a37b315a00cd2141eeff7ec72cf85dbdf01b85e5b75c322b05",
        "The scene shows a Rubik's Cube net with face labels, a target-color swatch, "
        "and four numbered options. A prime mark denotes a counterclockwise turn as "
        "viewed from outside the affected face. After the sequence R' B' L, which "
        "option gives the number of target-color stickers on the upper face?",
    ),
    "task_symbolic__organic_structure__bond_order_count": (
        "e06ea00be7c89829ec0113aa8742e069b66200a2cb87152cc3e2d274369e9088",
        "The visual panel contains an organic skeletal structure with line-angle "
        "bonds, rings, and occasional atom or substituent labels. Count only the "
        "visible triple bonds.",
    ),
    "task_symbolic__truth_table__truth_pattern_label": (
        "8a56fe1db19fc39a3f578b9f24c5e9c990da0defa08d475893320ac797205ea0",
        "A truth table shows an input table, a target expression P, and six labeled "
        "output-pattern options. Values use 1 for true and 0 for false. The "
        "operators are ! for NOT, & for AND, | for OR, and ^ for XOR. Reading rows "
        "from top to bottom, which option matches the truth pattern for P?",
    ),
    "task_symbolic__braille_cell__matching_pattern_label": (
        "c97dc3f1b35aa808b68f299a70a3659e0b0dbf3f3306209525671a02a998493a",
        "This panel shows a Braille reference cell and six labeled Braille option "
        "cells. Which option letter matches the reference pattern?",
    ),
    "task_symbolic__morse_code__morse_word_read_label": (
        "5893d94bbc4ae9721aea33f338bcd480468a17f93e9470cffda558f720851b86",
        "A visual Morse-code panel presents a Morse-code word above four labeled "
        "word options. Which labeled option matches the Morse code?",
    ),
    "task_symbolic__music_staff__scale_degree_function_label": (
        "2109cfa5ff0de46246c758809e69c1bee74b8e8c5b9346c24186ebbb1a07e106",
        "The visual shows a sheet-music staff with marked notation items. Select "
        "the option naming the scale-degree function of note 3 in G major.",
    ),
    "task_symbolic__logic_gate_circuit__output_value_label": (
        "45714263988de900b6f238982e9a241bb3c9fcf05c6133358010748858d29f87",
        "A Boolean logic-gate panel shows a circuit with labeled inputs, standard "
        "gate symbols, wires, and final OUT nodes. Evaluate each circuit. Which "
        "option's final OUT value is 1?",
    ),
    "task_three_d__carousel__object_type_ordered_adjacent_pair_count": (
        "670b588f8cf7c917fb238f36901ed25541b7f408cdcf630a4fb8c99d6f13c18f",
        "The scene shows small 3D objects on two concentric elliptical belts. "
        "Following the order of the inner belt, count each occurrence of gloves "
        "immediately followed by pyramids. How many pairs are there?",
    ),
    "task_three_d__conveyor__object_type_ordered_adjacent_pair_count": (
        "57c087be0bd9f967cd3b3a232bf46f3a77efb7db7f68eeb6e544dac6eb5ec7dc",
        "The visual shows a three-lane conveyor with small objects on each lane. "
        "Following the order of the left belt, count each occurrence of flowers "
        "immediately followed by trophies. How many pairs are there?",
    ),
    "task_three_d__object_cluster__multi_attribute_exclusion_count": (
        "e7be9f121b1417d25663d3b0d3098e040395f373fc86d38c756bbb42984c9524",
        "The visible scene contains many small 3D objects arranged on a plain "
        "surface. How many cyan objects are not cups?",
    ),
    "task_three_d__object_cluster__multi_attribute_or_count": (
        "dc80b310c428127f7bdd5175f32eff5b07e78143f5005d57f8d225989cbc6809",
        "The image shows many small 3D objects arranged on a plain surface. How many "
        "objects are either stools or blue?",
    ),
    "task_three_d__object_scene__reference_nearest_label": (
        "55f386c349f7766aae344f8ef6dd59569f490985faac838982b838b3154ff2c9",
        "The scene shows a washing machine as the reference and six smaller "
        "candidate objects. Which option identifies the candidate nearest the "
        "washing machine?",
    ),
}

# These paper-local condensations preserve every rule needed to answer the
# selected instance. The source hash forces explicit recuration if that prompt
# changes rather than silently publishing stale wording.
COMPACT_PROMPT_OVERRIDES: dict[str, tuple[str, str]] = {
    "task_games__checkers__max_capture_chain_length": (
        "3b68385aebaaf4bdf7d7483df5a154a8be1c345583dc91ef50431531f37e4c8b",
        "Red moves on the shown 8 by 8 checkers board. A jump captures an adjacent "
        "opponent and lands on the empty square beyond. The marked piece is a king, "
        "so it may jump diagonally in either direction and continue while another "
        "capture is available. What is its maximum capture-chain length?",
    ),
    "task_games__minesweeper__forced_cell_count": (
        "b470553c065a8003b0584e6bfad739e5aea56248467779b919dfc139185101ff",
        "In the Minesweeper grid, each number gives the mine count among its eight "
        "neighbors and each flag is a known mine. If a clue already has enough flags, "
        "its other hidden neighbors are safe; if every remaining hidden neighbor is "
        "needed, they are mines. From the outlined clue cells, how many hidden cells "
        "must be safe?",
    ),
    "task_games__reversi__marked_move_flip_count": (
        "d4caa4217d97b9698e53da9d9ab73a2610c516c6951204200591a51005e18fe8",
        "White moves on the shown 8 by 8 Reversi board. A legal move brackets opponent "
        "discs along one or more straight lines, and all bracketed discs flip. How many "
        "discs flip after playing at the red marked square?",
    ),
    "task_games__bubble_shooter__pop_color_label": (
        "a3062e2a0301a066bfddaab5b713be3458abd3cbf80078a55bed28d090c196bc",
        "A shot bubble attaches at the marked target. A connected same-color group "
        "pops when the placement makes its size at least three. Which option labels the "
        "bubble color that would pop a group there?",
    ),
    "task_games__circular_chess__target_cell_reacher_count": (
        "8a6bdf61be9214c93cb10ccf69955067c0f0820a95e22ff2c00b613b33d2fbd5",
        "On this four-ring, sixteen-sector circular chess board, sectors wrap but rings "
        "do not. The red cell is the target. Rooks move along or across rings, bishops "
        "diagonally, queens as both, knights jump, and kings one step; sliding pieces "
        "stop at the first occupied cell. How many Black pieces can reach the target?",
    ),
    "task_illustrations__rpg_tactical_map__water_barrier_unreachable_tile_label": (
        "d7068ad8bce614ed75159177020165c5e9bf1447c6f3543b98b3f84b2879c8a7",
        "Water tiles form a barrier and cannot be crossed; every other tile can. The "
        "blue unit moves only up, down, left, or right. Which candidate letter marks a "
        "tile the blue unit cannot reach?",
    ),
    "task_pages__web_action__action_target_label": (
        "df3daf318ee73e6bdb95510070c2467b098dcc1e66eeea9606555b611af22818",
        "The browser page includes a guide-code table and labeled candidate controls. "
        "Click the control on the item with category \"Home\", status \"Clearance\", "
        "and guide code \"M2\". Which candidate label marks that control?",
    ),
    "task_pages__paired_forms__total_amount_delta_value": (
        "35dc066ca991614233e0df31460951aa5ca95677969bd00aa2f25405e81c129a",
        "The purchase order and receiving slip show matching item codes, quantities, "
        "and purchase-order unit values. For each item with differing quantities, "
        "multiply the absolute quantity difference by its unit value and sum the "
        "products. What is the total amount delta?",
    ),
    "task_symbolic__life_automaton__one_step_cell_state_count": (
        "49a47ea044afc85ed1afb1b7833d0754435c57e10c8fc335e5aacaf74526fea3",
        "In the START grid, dark cells are alive. An alive cell survives with two or "
        "three live neighbors; an empty cell becomes alive with exactly three; every "
        "other cell is empty next. After one update, how many cells are empty?",
    ),
    "task_symbolic__dice__pair_attribute_combo_probability": (
        "f970e81e1af4dfde9997af12bd83996680d9cb9dfadb3cc218670db85d1015e6",
        "The trays show each die's top value. One die is selected uniformly and "
        "independently from each tray. Which A-F option gives the probability that both "
        "selected dice show even values?",
    ),
    "task_symbolic__spinner__multi_attribute_and_probability": (
        "8e4b449583d56f09ece55d29ac7b43e1fc79298f73f070d734567f9c5614573c",
        "Each spinner sector is equally likely and has a color and shape. Which A-F "
        "fraction option gives the probability of landing on a purple sector marked "
        "with a star?",
    ),
    "task_symbolic__abacus__displayed_value_readout": (
        "34539f41c2660200a531c56818986d95832cfa4d1c4043c76a667b3ae05eda5e",
        "On the three-column abacus, beads touching the center bar are active. An active "
        "upper bead is worth 5 and each active lower bead 1. Read the 100, 10, and 1 "
        "columns from left to right. Which option gives the displayed number?",
    ),
    "task_symbolic__agent_automaton__future_grid_label": (
        "3f9b8e2ca6b393054c9c45f0b132dac91469948e2889a24e2bcecb2501edbfca",
        "Starting at the arrow, apply three updates. Before moving, state 0 turns right "
        "and becomes 1; state 1 goes straight and becomes 2; state 2 turns left and "
        "becomes 0. The agent then moves one cell forward, wrapping at the grid edge. "
        "Which option shows the resulting grid?",
    ),
    "task_symbolic__turing_tape__turing_written_symbol_count": (
        "d6b75920514bdf8f85e71208ab133949d9b249a4e7595c57472d335a996ce94b",
        "Starting from the shown tape, head, and state, simulate six transitions. At "
        "each step, use the visible table to write a symbol, move left or right, and "
        "change state. How many tape cells contain symbol 0 afterward?",
    ),
}


@dataclass(frozen=True)
class SelectedSample:
    domain: str
    scene_id: str
    task_id: str
    query_id: str
    sample_id: str
    title: str
    source_question: str
    display_question: str
    prompt_display_mode: str
    prompt_font_tier: str
    answer_gt: dict[str, Any]
    instance_seed: int
    data_path: Path
    image_path: Path


def parse_args() -> argparse.Namespace:
    paper_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-root", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=paper_root / "figures" / "scene_atlas",
    )
    parser.add_argument(
        "--provenance-path",
        type=Path,
        default=paper_root / "provenance" / "scene_atlas.json",
    )
    parser.add_argument(
        "--tex-path",
        type=Path,
        default=paper_root / "sections" / "scene_atlas.tex",
    )
    return parser.parse_args()


def stable_rng(seed: int, domain: str) -> random.Random:
    payload = f"{seed}:{domain}".encode()
    domain_seed = int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")
    return random.Random(domain_seed)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repository_head(repository_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def latex_escape(text: str) -> str:
    # Tiny atlas captions render more reliably with textual angle names than
    # with a math glyph whose font has no matching size.
    text = text.replace("angle ∠", "angle ")
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
        "≤": r"$\leq$",
        "≥": r"$\geq$",
        "×": r"$\times$",
        "°": r"$^\circ$",
        "π": r"$\pi$",
        "∠": "angle ",
    }
    return "".join(replacements.get(character, character) for character in text)


def humanize(value: str) -> str:
    words = value.replace("_", " ").strip().split()
    rendered: list[str] = []
    for index, word in enumerate(words):
        lowered = word.lower()
        if lowered in TITLE_ACRONYMS:
            rendered.append(TITLE_ACRONYMS[lowered])
        elif index > 0 and lowered in TITLE_SMALL_WORDS:
            rendered.append(lowered)
        else:
            rendered.append(word.title())
    return " ".join(rendered)


def compact_title(scene_id: str, task_id: str) -> str:
    if task_id in TITLE_OVERRIDES:
        return TITLE_OVERRIDES[task_id]
    objective = task_id.rsplit("__", maxsplit=1)[-1]
    for suffix in ("_value", "_label", "_count"):
        if objective.endswith(suffix):
            objective = objective[: -len(suffix)]
            break
    scene = humanize(scene_id)
    objective_text = humanize(objective)
    return f"{scene}: {objective_text}"


def normalized_prompt(record: dict[str, Any]) -> str:
    variants = record.get("prompt_variants") or {}
    prompt = variants.get("answer_only") or record["prompt"]
    first_paragraph = prompt.split("\n", maxsplit=1)[0]
    return re.sub(r"\s+", " ", first_paragraph).strip()


def prompt_display(record: dict[str, Any]) -> tuple[str, str, str, str]:
    source_question = normalized_prompt(record)
    task_id = str(record["task_id"])
    if task_id in CURATED_PROMPT_OVERRIDES:
        expected_hash, display_question = CURATED_PROMPT_OVERRIDES[task_id]
        actual_hash = hashlib.sha256(source_question.encode()).hexdigest()
        if actual_hash != expected_hash:
            raise ValueError(
                f"Atlas source question changed for {task_id}: expected {expected_hash}, "
                f"found {actual_hash}; recurate its publication wording"
            )
        display_mode = "curated"
        font_tier = (
            "normal"
            if len(display_question) <= NORMAL_PROMPT_MAX_CHARACTERS
            else "dense"
        )
    elif len(source_question) <= FULL_PROMPT_MAX_CHARACTERS:
        font_tier = (
            "normal"
            if len(source_question) <= NORMAL_PROMPT_MAX_CHARACTERS
            else "dense"
        )
        display_question = source_question
        display_mode = "full"
    else:
        if task_id not in COMPACT_PROMPT_OVERRIDES:
            raise ValueError(
                f"Atlas question for {task_id} has {len(source_question)} characters; "
                "add a reviewed complete-sentence condensation before publishing it"
            )
        expected_hash, display_question = COMPACT_PROMPT_OVERRIDES[task_id]
        actual_hash = hashlib.sha256(source_question.encode()).hexdigest()
        if actual_hash != expected_hash:
            raise ValueError(
                f"Atlas source question changed for {task_id}: expected {expected_hash}, "
                f"found {actual_hash}; recurate its compact wording"
            )
        display_mode = "compact"
        font_tier = "dense"

    if len(display_question) > FULL_PROMPT_MAX_CHARACTERS:
        raise ValueError(
            f"Atlas display question for {record['task_id']} is too long: "
            f"{len(display_question)} characters"
        )
    if "..." in display_question or "…" in display_question:
        raise ValueError(f"Atlas question for {record['task_id']} contains an ellipsis")
    if display_question[-1:] not in ".?!":
        raise ValueError(f"Atlas question for {record['task_id']} is not a complete sentence")
    if "?" in source_question and "?" not in display_question:
        raise ValueError(f"Atlas question for {record['task_id']} omits its question")
    return source_question, display_question, display_mode, font_tier


def task_directories(domain_dir: Path) -> dict[str, list[Path]]:
    scenes: dict[str, list[Path]] = {}
    for scene_dir in domain_dir.iterdir():
        if not scene_dir.is_dir() or scene_dir.name.startswith("."):
            continue
        tasks = [
            task_dir
            for task_dir in scene_dir.iterdir()
            if task_dir.is_dir()
            and task_dir.name.startswith("task_")
            and any(task_dir.glob("data/*/*.json"))
        ]
        if tasks:
            scenes[scene_dir.name] = tasks
    return scenes


def select_task_paths(domain_dir: Path, rng: random.Random) -> list[Path]:
    scenes = task_directories(domain_dir)
    if not scenes:
        raise ValueError(f"No review tasks found under {domain_dir}")

    scene_ids = list(scenes)
    rng.shuffle(scene_ids)
    if len(scene_ids) >= SAMPLES_PER_DOMAIN:
        selected_scene_ids = scene_ids[:SAMPLES_PER_DOMAIN]
    else:
        selected_scene_ids = scene_ids

    selected: list[Path] = []
    for scene_id in selected_scene_ids:
        selected.append(rng.choice(scenes[scene_id]))

    if len(selected) < SAMPLES_PER_DOMAIN:
        selected_set = set(selected)
        fill_scene_ids = list(scenes)
        rng.shuffle(fill_scene_ids)
        fill_scene_ids.sort(
            key=lambda scene_id: sum(
                task_path not in selected_set for task_path in scenes[scene_id]
            ),
            reverse=True,
        )
        while len(selected) < SAMPLES_PER_DOMAIN:
            made_progress = False
            for scene_id in fill_scene_ids:
                remaining = [
                    task_path
                    for task_path in scenes[scene_id]
                    if task_path not in selected_set
                ]
                if not remaining:
                    continue
                chosen = rng.choice(remaining)
                selected.append(chosen)
                selected_set.add(chosen)
                made_progress = True
                if len(selected) == SAMPLES_PER_DOMAIN:
                    break
            if not made_progress:
                break

    if len(selected) != SAMPLES_PER_DOMAIN:
        raise ValueError(
            f"{domain_dir.name} has only {len(selected)} selectable tasks; "
            f"expected {SAMPLES_PER_DOMAIN}"
        )
    rng.shuffle(selected)
    return selected


def load_selected_sample(
    review_root: Path,
    domain: str,
    task_dir: Path,
    rng: random.Random,
) -> SelectedSample:
    data_paths = sorted(task_dir.glob("data/*/*.json"))
    data_path = rng.choice(data_paths)
    record = json.loads(data_path.read_text())
    image_path = review_root / record["image"]["path"]
    if not image_path.is_file():
        raise FileNotFoundError(image_path)
    source_question, display_question, display_mode, font_tier = prompt_display(record)
    return SelectedSample(
        domain=domain,
        scene_id=record["scene_id"],
        task_id=record["task_id"],
        query_id=record["query_id"],
        sample_id=data_path.stem,
        title=compact_title(record["scene_id"], record["task_id"]),
        source_question=source_question,
        display_question=display_question,
        prompt_display_mode=display_mode,
        prompt_font_tier=font_tier,
        answer_gt=record["answer_gt"],
        instance_seed=record["instance_seed"],
        data_path=data_path,
        image_path=image_path,
    )


def select_samples(review_root: Path, seed: int) -> dict[str, list[SelectedSample]]:
    selected: dict[str, list[SelectedSample]] = {}
    for domain in DOMAIN_ORDER:
        domain_dir = review_root / domain
        if not domain_dir.is_dir():
            raise FileNotFoundError(domain_dir)
        rng = stable_rng(seed, domain)
        task_paths = select_task_paths(domain_dir, rng)
        selected[domain] = [
            load_selected_sample(review_root, domain, task_path, rng)
            for task_path in task_paths
        ]
    return selected


def answer_text(answer_gt: dict[str, Any]) -> str:
    value = answer_gt["value"]
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def asset_name(domain: str, index: int, sample: SelectedSample) -> str:
    objective = sample.task_id.rsplit("__", maxsplit=1)[-1]
    return f"{domain}_{index:02d}_{sample.scene_id}_{objective}{sample.image_path.suffix.lower()}"


def latex_preamble() -> list[str]:
    return [
        "% Generated by scripts/build_scene_atlas.py; do not edit by hand.",
        r"\section{Representative Task Atlas}",
        r"\label{app:task-atlas}",
        "",
        r"Each page presents twelve seeded examples from one visual domain. Panels pair each rendered instance with its question and typed answer. Rule-heavy questions are condensed only when required for legibility.",
        "",
        r"\begingroup",
        r"\setlength{\fboxsep}{2pt}",
        r"\setlength{\fboxrule}{0.3pt}",
        r"\definecolor{traceatlasborder}{HTML}{D1D5DB}",
        r"\definecolor{traceatlasanswer}{HTML}{2A6FB5}",
        r"\newcommand{\traceatlaspromptnormal}{\fontsize{5.5}{6.0}\selectfont}",
        r"\newcommand{\traceatlaspromptdense}{\fontsize{4.75}{5.2}\selectfont}",
        r"\newcommand{\traceatlascard}[5]{%",
        r"  \begingroup",
        r"  \color{traceatlasborder}%",
        r"  \fbox{%",
        r"    \color{black}%",
        r"    \begin{minipage}[t][0.176\textheight][t]{0.298\textwidth}",
        r"      \raggedright\setlength{\parindent}{0pt}%",
        r"      {\fontsize{5.1}{5.6}\selectfont\sffamily\color{gray}\textbf{#1}\par}%",
        r"      \vspace{1pt}%",
        r"      \centering\includegraphics[width=\linewidth,height=0.088\textheight,keepaspectratio]{#2}\par",
        r"      \vspace{1pt}%",
        r"      \raggedright{\sffamily #5 #3\par}%",
        r"      \vfill",
        r"      {\fontsize{5.6}{6.1}\selectfont\sffamily\color{traceatlasanswer}\textbf{Answer: #4}\par}%",
        r"    \end{minipage}%",
        r"  }%",
        r"  \endgroup",
        r"}",
        "",
    ]


def build_atlas(
    *,
    review_root: Path,
    selected: dict[str, list[SelectedSample]],
    output_dir: Path,
    tex_path: Path,
) -> list[dict[str, Any]]:
    paper_root = Path(__file__).resolve().parents[1]
    asset_dir = output_dir / "assets"
    if asset_dir.exists():
        shutil.rmtree(asset_dir)
    asset_dir.mkdir(parents=True)

    lines = latex_preamble()
    manifest_domains: list[dict[str, Any]] = []
    for domain in DOMAIN_ORDER:
        domain_title = DOMAIN_TITLES[domain]
        placement = "t" if domain == DOMAIN_ORDER[0] else "p"
        lines.extend(
            [
                rf"\begin{{figure}}[{placement}]",
                r"\centering",
            ]
        )
        manifest_samples: list[dict[str, Any]] = []
        for index, sample in enumerate(selected[domain], start=1):
            destination = asset_dir / asset_name(domain, index, sample)
            shutil.copyfile(sample.image_path, destination)
            relative_asset = destination.relative_to(paper_root).as_posix()
            lines.append(
                "\\traceatlascard"
                f"{{{latex_escape(sample.title)}}}"
                f"{{{relative_asset}}}"
                f"{{{latex_escape(sample.display_question)}}}"
                f"{{{latex_escape(answer_text(sample.answer_gt))}}}"
                f"{{\\traceatlasprompt{sample.prompt_font_tier}}}"
            )
            column = (index - 1) % ATLAS_COLUMNS
            if column < ATLAS_COLUMNS - 1:
                lines.append(r"\hfill")
            elif index < SAMPLES_PER_DOMAIN:
                lines.extend([r"\par\vspace{2pt}", r"\noindent"])

            manifest_samples.append(
                {
                    "panel_index": index,
                    "scene_id": sample.scene_id,
                    "task_id": sample.task_id,
                    "query_id": sample.query_id,
                    "sample_id": sample.sample_id,
                    "instance_seed": sample.instance_seed,
                    "source_question": sample.source_question,
                    "display_question": sample.display_question,
                    "prompt_display_mode": sample.prompt_display_mode,
                    "prompt_font_tier": sample.prompt_font_tier,
                    "answer_gt": sample.answer_gt,
                    "review_data_path": sample.data_path.relative_to(review_root).as_posix(),
                    "review_image_path": sample.image_path.relative_to(review_root).as_posix(),
                    "review_data_sha256": sha256(sample.data_path),
                    "review_image_sha256": sha256(sample.image_path),
                    "paper_asset_path": relative_asset,
                    "paper_asset_sha256": sha256(destination),
                }
            )

        lines.extend(
            [
                rf"\caption{{Representative {latex_escape(DOMAIN_CAPTION_NOUNS[domain])} tasks.}}",
                rf"\label{{fig:task-atlas-{domain.replace('_', '-')}}}",
                r"\end{figure}",
                r"\clearpage",
                "",
            ]
        )
        manifest_domains.append(
            {
                "domain": domain,
                "display_name": domain_title,
                "samples": manifest_samples,
            }
        )
    lines.extend([r"\endgroup", ""])
    tex_path.parent.mkdir(parents=True, exist_ok=True)
    tex_path.write_text("\n".join(lines))
    return manifest_domains


def main() -> None:
    args = parse_args()
    paper_root = Path(__file__).resolve().parents[1]
    review_root = args.review_root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    selected = select_samples(review_root, args.seed)
    manifest_domains = build_atlas(
        review_root=review_root,
        selected=selected,
        output_dir=output_dir,
        tex_path=args.tex_path.resolve(),
    )

    manifest = {
        "schema_version": "trace_paper_scene_atlas_v3",
        "artifact": args.tex_path.resolve().relative_to(paper_root).as_posix(),
        "artifact_sha256": sha256(args.tex_path.resolve()),
        "generator": Path(__file__).resolve().relative_to(paper_root).as_posix(),
        "generator_sha256": sha256(Path(__file__).resolve()),
        "source_repository_head": repository_head(paper_root.parents[1]),
        "selection_seed": args.seed,
        "selection_strategy": {
            "samples_per_domain": SAMPLES_PER_DOMAIN,
            "scene_policy": "one random task per shuffled scene before scene reuse",
            "fill_policy": (
                "one random unselected task from the highest-coverage remaining scenes "
                f"when a domain has fewer than {SAMPLES_PER_DOMAIN} scenes"
            ),
            "layout": {
                "columns": ATLAS_COLUMNS,
                "rows": SAMPLES_PER_DOMAIN // ATLAS_COLUMNS,
            },
            "ordering": "seeded shuffle; not alphabetical",
            "prompt_policy": {
                "normal_font_max_characters": NORMAL_PROMPT_MAX_CHARACTERS,
                "full_question_max_characters": FULL_PROMPT_MAX_CHARACTERS,
                "long_question_policy": (
                    "reviewed complete-sentence condensation with source hash"
                ),
                "curated_display_policy": (
                    "publication wording overrides are source-hash guarded"
                ),
            },
            "title_policy": {
                "default": "humanized scene and objective identifiers",
                "publication_overrides": sorted(TITLE_OVERRIDES),
            },
        },
        "source_root": "review/task-reviews (supplied with --review-root)",
        "domains": manifest_domains,
    }
    args.provenance_path.parent.mkdir(parents=True, exist_ok=True)
    args.provenance_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(args.tex_path.resolve())
    print(args.provenance_path.resolve())
    print(f"domains={len(manifest_domains)} samples={len(manifest_domains) * SAMPLES_PER_DOMAIN}")


if __name__ == "__main__":
    main()
