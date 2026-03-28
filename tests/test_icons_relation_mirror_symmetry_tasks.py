"""Behavior tests for the icon mirror-symmetry relation task."""

from __future__ import annotations

import json
from collections import Counter

from trace.core.seed import hash64
from trace.tasks.icons.relation.mirror_symmetry import IconsRelationMirrorSymmetryTask


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def test_icons_relation_mirror_symmetry_contract_matches_scene() -> None:
    task = IconsRelationMirrorSymmetryTask()
    out = task.generate(
        15110,
        params={"task_variant": "mirror_diagonal_main", "target_count": 2, "distractor_count": 4},
        max_attempts=200,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    scene_entities = [entity for entity in trace["scene_ir"]["entities"] if str(entity.get("panel")) == "scene"]
    reference_entities = [entity for entity in trace["scene_ir"]["entities"] if str(entity.get("panel")) == "reference"]

    assert len(reference_entities) == 1
    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == 2
    assert out.evidence_gt.type == "label_set"
    assert out.evidence_gt.value == sorted(out.evidence_gt.value)
    assert len(out.evidence_gt.value) == 2
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert trace["query_spec"]["prompt_variant_active_key"] == "answer_and_evidence"
    assert trace["scene_ir"]["scene_kind"] == "icons_reference_grid_mirror_symmetry_count"
    assert execution["question_format"] == "count_scene_cells_matching_reference_mirror_symmetry"
    assert execution["task_variant"] == "mirror_diagonal_main"
    assert int(execution["object_count"]) == 6
    assert int(execution["target_count"]) == 2
    assert int(execution["distractor_count"]) == 4
    assert 0.0 <= float(out.complexity.complexity_score) <= 1.0
    assert set(out.complexity.complexity_components.keys()) == {
        "visual_scan",
        "spatial_reasoning",
        "ambiguity",
        "clutter",
    }
    assert all(0.0 <= float(value) <= 1.0 for value in out.complexity.complexity_components.values())

    reference_cell = reference_entities[0]
    ref_bbox = reference_cell["cell_bbox_xyxy"]
    assert int(ref_bbox[2]) - int(ref_bbox[0]) == int(ref_bbox[3]) - int(ref_bbox[1])
    assert str(reference_cell["symmetry_id"]) == "mirror_diagonal_main"
    assert int(reference_cell["icon_count"]) % 2 == 0
    assert bool(reference_cell["has_vertical_symmetry"]) is False
    assert bool(reference_cell["has_horizontal_symmetry"]) is False
    assert bool(reference_cell["has_diagonal_main_symmetry"]) is True
    assert bool(reference_cell["has_diagonal_anti_symmetry"]) is False
    assert len(scene_entities) == 6
    assert len({str(entity["label"]) for entity in scene_entities}) == 6
    matching_labels = set(str(value) for value in execution["matching_cell_labels"])
    assert matching_labels == set(str(value) for value in out.evidence_gt.value)
    sampled_palette = [tuple(int(channel) for channel in color) for color in trace["render_spec"]["style"]["sampled_palette_rgb"]]
    assert len(sampled_palette) >= 2

    for entity in scene_entities:
        cell_bbox = entity["cell_bbox_xyxy"]
        assert int(cell_bbox[2]) - int(cell_bbox[0]) == int(cell_bbox[3]) - int(cell_bbox[1])
        assert int(entity["icon_count"]) >= 2
        assert int(entity["icon_count"]) % 2 == 0
        is_match = bool(entity["is_match"])
        assert is_match == (str(entity["label"]) in matching_labels)
        if is_match:
            assert str(entity["symmetry_id"]) == "mirror_diagonal_main"
            assert bool(entity["has_vertical_symmetry"]) is False
            assert bool(entity["has_horizontal_symmetry"]) is False
            assert bool(entity["has_diagonal_main_symmetry"]) is True
            assert bool(entity["has_diagonal_anti_symmetry"]) is False
        else:
            if str(entity["symmetry_id"]) == "mirror_horizontal":
                assert bool(entity["has_vertical_symmetry"]) is False
                assert bool(entity["has_horizontal_symmetry"]) is True
                assert bool(entity["has_diagonal_main_symmetry"]) is False
                assert bool(entity["has_diagonal_anti_symmetry"]) is False
            elif str(entity["symmetry_id"]) == "mirror_vertical":
                assert bool(entity["has_vertical_symmetry"]) is True
                assert bool(entity["has_horizontal_symmetry"]) is False
                assert bool(entity["has_diagonal_main_symmetry"]) is False
                assert bool(entity["has_diagonal_anti_symmetry"]) is False
            elif str(entity["symmetry_id"]) == "mirror_diagonal_anti":
                assert bool(entity["has_vertical_symmetry"]) is False
                assert bool(entity["has_horizontal_symmetry"]) is False
                assert bool(entity["has_diagonal_main_symmetry"]) is False
                assert bool(entity["has_diagonal_anti_symmetry"]) is True
            elif str(entity["symmetry_id"]) == "mirror_both_axes":
                assert bool(entity["has_vertical_symmetry"]) is True
                assert bool(entity["has_horizontal_symmetry"]) is True
                assert bool(entity["has_diagonal_main_symmetry"]) is False
                assert bool(entity["has_diagonal_anti_symmetry"]) is False
            else:
                assert str(entity["symmetry_id"]) == "none"
                assert bool(entity["has_vertical_symmetry"]) is False
                assert bool(entity["has_horizontal_symmetry"]) is False
                assert bool(entity["has_diagonal_main_symmetry"]) is False
                assert bool(entity["has_diagonal_anti_symmetry"]) is False
        for placement in entity["placements"]:
            assert tuple(int(channel) for channel in placement["tint_rgb"]) in sampled_palette


def test_icons_relation_mirror_symmetry_supports_zero_matches() -> None:
    task = IconsRelationMirrorSymmetryTask()
    out = task.generate(
        15111,
        params={"task_variant": "mirror_horizontal", "target_count": 0, "distractor_count": 6},
        max_attempts=200,
    )
    assert int(out.answer_gt.value) == 0
    assert out.evidence_gt.value == []


def test_icons_relation_mirror_symmetry_prompt_example_matches_contract() -> None:
    task = IconsRelationMirrorSymmetryTask()
    out = task.generate(
        15112,
        params={"task_variant": "mirror_horizontal", "target_count": 2, "distractor_count": 4},
        max_attempts=200,
    )
    answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
    answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert answer_only == {"answer": 2}
    assert list(answer_and_evidence.keys()) == ["evidence", "answer"]
    assert answer_and_evidence["evidence"] == ["B", "E"]
    assert answer_and_evidence["answer"] == 2


def test_icons_relation_mirror_symmetry_supports_both_axes_reference() -> None:
    task = IconsRelationMirrorSymmetryTask()
    out = task.generate(
        15114,
        params={"task_variant": "mirror_both_axes", "target_count": 1, "distractor_count": 5},
        max_attempts=200,
    )
    reference_cell = next(
        entity for entity in out.trace_payload["scene_ir"]["entities"] if str(entity.get("panel")) == "reference"
    )
    assert str(reference_cell["symmetry_id"]) == "mirror_both_axes"
    assert int(reference_cell["icon_count"]) == 4
    assert bool(reference_cell["has_vertical_symmetry"]) is True
    assert bool(reference_cell["has_horizontal_symmetry"]) is True
    assert bool(reference_cell["has_diagonal_main_symmetry"]) is False
    assert bool(reference_cell["has_diagonal_anti_symmetry"]) is False


def test_icons_relation_mirror_symmetry_balanced_sampling_defaults() -> None:
    task = IconsRelationMirrorSymmetryTask()
    object_counts: Counter[int] = Counter()
    target_counts: Counter[int] = Counter()
    distractor_counts: Counter[int] = Counter()
    variant_counts: Counter[str] = Counter()
    for index in range(40):
        out = task.generate(
            hash64(15113, "icons_relation_mirror_symmetry", index),
            params={"_sampling_index": index},
            max_attempts=200,
        )
        execution = out.trace_payload["execution_trace"]
        object_count = int(execution["object_count"])
        target_count = int(execution["target_count"])
        distractor_count = int(execution["distractor_count"])
        object_counts[object_count] += 1
        target_counts[target_count] += 1
        distractor_counts[distractor_count] += 1
        variant_counts[str(execution["task_variant"])] += 1
        assert object_count == 6
        assert 0 <= target_count <= 4
        assert 2 <= distractor_count <= 6
        assert object_count == target_count + distractor_count
    assert set(object_counts.keys()) == {6}
    assert set(target_counts.keys()) == set(range(0, 5))
    assert set(distractor_counts.keys()) == set(range(2, 7))
    assert set(variant_counts.keys()) == {
        "mirror_vertical",
        "mirror_horizontal",
        "mirror_diagonal_main",
        "mirror_diagonal_anti",
        "mirror_both_axes",
    }
    assert max(target_counts.values()) - min(target_counts.values()) <= 1
    assert max(variant_counts.values()) - min(variant_counts.values()) <= 1
