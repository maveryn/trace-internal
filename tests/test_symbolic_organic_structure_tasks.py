from __future__ import annotations

from io import BytesIO
from random import Random

import pytest

from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks.symbolic.shared.organic_structure_scene import (
    ORGANIC_STRUCTURE_MAX_BRANCH_POINT_COUNT,
    ORGANIC_STRUCTURE_MAX_BOND_ORDER_COUNT,
    ORGANIC_STRUCTURE_MAX_RING_SIZE_COUNT,
    build_constrained_organic_branch_structure,
    build_constrained_organic_ring_size_structure,
    build_constrained_organic_structure,
    organic_branch_point_atom_indices,
    organic_ring_item_ids,
    validate_organic_structure,
)
from trace.tasks.symbolic.notation.organic_structure import (
    BRANCH_POINT_COUNT_TASK_ID,
    SymbolicBranchPointCountTask,
    SymbolicBondOrderCountTask,
    SymbolicRingSizeCountTask,
    RING_SIZE_COUNT_TASK_ID,
    TARGET_BOND_ORDERS,
    TARGET_RING_SIZES,
    TASK_ID,
)
from trace.tasks.registry import TASK_REGISTRY


def _png_bytes(output) -> bytes:
    buffer = BytesIO()
    output.image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_organic_structure_bond_order_task_is_registered_and_taxonomized() -> None:
    assert TASK_ID in TASK_REGISTRY
    taxonomy = resolve_task_taxonomy(TASK_ID)
    assert taxonomy.domain == "symbolic"
    assert taxonomy.scene_id == "organic_structure"
    assert taxonomy.source_scene_id == "notation"


def test_organic_structure_branch_point_task_is_registered_and_taxonomized() -> None:
    assert BRANCH_POINT_COUNT_TASK_ID in TASK_REGISTRY
    taxonomy = resolve_task_taxonomy(BRANCH_POINT_COUNT_TASK_ID)
    assert taxonomy.domain == "symbolic"
    assert taxonomy.scene_id == "organic_structure"
    assert taxonomy.source_scene_id == "notation"


def test_organic_structure_ring_size_task_is_registered_and_taxonomized() -> None:
    assert RING_SIZE_COUNT_TASK_ID in TASK_REGISTRY
    taxonomy = resolve_task_taxonomy(RING_SIZE_COUNT_TASK_ID)
    assert taxonomy.domain == "symbolic"
    assert taxonomy.scene_id == "organic_structure"
    assert taxonomy.source_scene_id == "notation"


def test_organic_structure_double_bond_count_contract() -> None:
    out = SymbolicBondOrderCountTask().generate(
        102,
        params={"target_bond_order": "double"},
        max_attempts=3,
    )
    trace = out.trace_payload
    bonds = trace["execution_trace"]["bonds"]
    expected_ids = [bond["item_id"] for bond in bonds if bond["bond_order"] == "double"]
    assert out.query_id == "bond_order_count"
    assert out.answer_gt.type == "integer"
    assert out.annotation_gt.type == "point_pair_set"
    assert out.answer_gt.value == len(expected_ids)
    assert len(out.annotation_gt.value) == len(expected_ids)
    assert trace["execution_trace"]["annotation_item_ids"] == expected_ids
    assert trace["projected_annotation"]["type"] == "point_pair_set"
    assert trace["projected_annotation"]["point_pair_set"] == out.annotation_gt.value
    for bond_id, point_pair in zip(expected_ids, out.annotation_gt.value):
        assert point_pair == trace["render_map"]["bond_point_pairs_px"][str(bond_id)]
        assert len(point_pair) == 2
        assert all(len(point) == 2 for point in point_pair)
    assert trace["execution_trace"]["organic_metadata"]["text_label_policy"]
    assert trace["execution_trace"]["organic_metadata"]["constraint_report"]["max_valence"] <= 4
    assert "double" in out.prompt


def test_organic_structure_triple_bond_count_contract() -> None:
    out = SymbolicBondOrderCountTask().generate(
        209,
        params={"target_bond_order": "triple"},
        max_attempts=3,
    )
    trace = out.trace_payload
    bonds = trace["execution_trace"]["bonds"]
    expected_ids = [bond["item_id"] for bond in bonds if bond["bond_order"] == "triple"]
    assert out.query_id == "bond_order_count"
    assert out.annotation_gt.type == "point_pair_set"
    assert out.answer_gt.value == len(expected_ids)
    assert len(out.annotation_gt.value) == len(expected_ids)
    assert trace["execution_trace"]["annotation_item_ids"] == expected_ids
    assert trace["projected_annotation"]["type"] == "point_pair_set"
    assert trace["projected_annotation"]["point_pair_set"] == out.annotation_gt.value
    assert set(trace["execution_trace"]["organic_metadata"]["target_bond_order_support"]) == set(TARGET_BOND_ORDERS)
    assert "not enforced" not in trace["execution_trace"]["organic_metadata"]["chemical_validity_policy"]
    assert "triple" in out.prompt


def test_organic_structure_branch_point_count_contract() -> None:
    out = SymbolicBranchPointCountTask().generate(
        412,
        params={"answer_value": 3},
        max_attempts=3,
    )
    trace = out.trace_payload
    atoms = trace["execution_trace"]["atoms"]
    expected_ids = [atom["item_id"] for atom in atoms if atom["degree"] >= 3]
    assert out.query_id == "branch_point_count"
    assert out.answer_gt.type == "integer"
    assert out.annotation_gt.type == "point_set"
    assert out.answer_gt.value == len(expected_ids) == 3
    assert len(out.annotation_gt.value) == len(expected_ids)
    assert trace["execution_trace"]["annotation_item_ids"] == expected_ids
    assert trace["execution_trace"]["branch_point_item_ids"] == expected_ids
    assert trace["projected_annotation"]["type"] == "point_set"
    assert trace["projected_annotation"]["point_set"] == out.annotation_gt.value
    for atom_id, point in zip(expected_ids, out.annotation_gt.value):
        assert point == trace["render_map"]["atom_points_px"][str(atom_id)]
        assert len(point) == 2
    assert trace["render_map"]["annotation_source"] == "atom_points_px"
    assert trace["execution_trace"]["organic_metadata"]["constraint_report"]["max_valence"] <= 4
    assert "branch" in out.prompt


def test_organic_structure_branch_point_zero_case_has_empty_annotation() -> None:
    out = SymbolicBranchPointCountTask().generate(
        510,
        params={"answer_value": 0},
        max_attempts=3,
    )
    assert out.query_id == "branch_point_count"
    assert out.answer_gt.value == 0
    assert out.annotation_gt.type == "point_set"
    assert out.annotation_gt.value == []
    assert out.trace_payload["projected_annotation"]["point_set"] == []


def test_organic_structure_ring_size_count_contract() -> None:
    out = SymbolicRingSizeCountTask().generate(
        811,
        params={"target_ring_size": 6, "answer_value": 2},
        max_attempts=3,
    )
    trace = out.trace_payload
    rings = trace["execution_trace"]["rings"]
    expected_ids = [ring["item_id"] for ring in rings if ring["ring_size"] == 6]
    assert out.query_id == "ring_size_count"
    assert out.answer_gt.type == "integer"
    assert out.annotation_gt.type == "bbox_set"
    assert out.answer_gt.value == len(expected_ids) == 2
    assert len(out.annotation_gt.value) == len(expected_ids)
    assert trace["execution_trace"]["annotation_item_ids"] == expected_ids
    assert trace["execution_trace"]["matching_ring_item_ids"] == expected_ids
    assert trace["projected_annotation"]["type"] == "bbox_set"
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    for ring_id, bbox in zip(expected_ids, out.annotation_gt.value):
        assert bbox == trace["render_map"]["ring_bboxes_px"][str(ring_id)]
        assert len(bbox) == 4
    assert trace["execution_trace"]["target_ring_size"] == 6
    assert trace["execution_trace"]["organic_metadata"]["ring_layout_policy"]
    assert "hexagonal" in out.prompt


def test_organic_structure_ring_size_zero_case_has_empty_annotation() -> None:
    out = SymbolicRingSizeCountTask().generate(
        910,
        params={"target_ring_size": 5, "answer_value": 0},
        max_attempts=3,
    )
    assert out.query_id == "ring_size_count"
    assert out.answer_gt.value == 0
    assert out.annotation_gt.type == "bbox_set"
    assert out.annotation_gt.value == []
    assert out.trace_payload["projected_annotation"]["bbox_set"] == []
    assert all(ring["ring_size"] != 5 for ring in out.trace_payload["execution_trace"]["rings"])


def test_organic_structure_generation_is_deterministic() -> None:
    task = SymbolicBondOrderCountTask()
    params = {"target_bond_order": "triple", "scene_variant": "notebook_problem"}
    first = task.generate(311, params=params, max_attempts=3)
    second = task.generate(311, params=params, max_attempts=3)
    assert first.prompt == second.prompt
    assert first.answer_gt.to_dict() == second.answer_gt.to_dict()
    assert first.annotation_gt.to_dict() == second.annotation_gt.to_dict()
    assert first.trace_payload["execution_trace"] == second.trace_payload["execution_trace"]
    assert _png_bytes(first) == _png_bytes(second)

    branch_params = {"answer_value": 2, "scene_variant": "notebook_problem"}
    branch_first = SymbolicBranchPointCountTask().generate(612, params=branch_params, max_attempts=3)
    branch_second = SymbolicBranchPointCountTask().generate(612, params=branch_params, max_attempts=3)
    assert branch_first.prompt == branch_second.prompt
    assert branch_first.answer_gt.to_dict() == branch_second.answer_gt.to_dict()
    assert branch_first.annotation_gt.to_dict() == branch_second.annotation_gt.to_dict()
    assert branch_first.trace_payload["execution_trace"] == branch_second.trace_payload["execution_trace"]
    assert _png_bytes(branch_first) == _png_bytes(branch_second)

    ring_params = {"target_ring_size": 5, "answer_value": 3, "scene_variant": "notebook_problem"}
    ring_first = SymbolicRingSizeCountTask().generate(812, params=ring_params, max_attempts=3)
    ring_second = SymbolicRingSizeCountTask().generate(812, params=ring_params, max_attempts=3)
    assert ring_first.prompt == ring_second.prompt
    assert ring_first.answer_gt.to_dict() == ring_second.answer_gt.to_dict()
    assert ring_first.annotation_gt.to_dict() == ring_second.annotation_gt.to_dict()
    assert ring_first.trace_payload["execution_trace"] == ring_second.trace_payload["execution_trace"]
    assert _png_bytes(ring_first) == _png_bytes(ring_second)


def test_organic_structure_scaffolds_respect_v1_constraints() -> None:
    for target_bond_order in TARGET_BOND_ORDERS:
        for answer_count in range(1, ORGANIC_STRUCTURE_MAX_BOND_ORDER_COUNT + 1):
            spec = build_constrained_organic_structure(
                Random(1000 + answer_count),
                target_bond_order=target_bond_order,
                answer_count=answer_count,
            )
            report = validate_organic_structure(spec)
            matching_bonds = [bond for bond in spec.bonds if bond.order == target_bond_order]
            assert len(matching_bonds) == answer_count
            assert report.max_valence <= 4
            assert report.crossing_count == 0

    for answer_count in range(0, ORGANIC_STRUCTURE_MAX_BRANCH_POINT_COUNT + 1):
        spec = build_constrained_organic_branch_structure(
            Random(2000 + answer_count),
            answer_count=answer_count,
        )
        report = validate_organic_structure(spec)
        branch_indices = organic_branch_point_atom_indices(spec)
        assert len(branch_indices) == answer_count
        assert len(report.branch_point_atom_ids) == answer_count
        assert report.max_valence <= 4
        assert report.crossing_count == 0

    for target_ring_size in TARGET_RING_SIZES:
        for answer_count in range(0, ORGANIC_STRUCTURE_MAX_RING_SIZE_COUNT + 1):
            spec = build_constrained_organic_ring_size_structure(
                Random(3000 + target_ring_size * 10 + answer_count),
                target_ring_size=target_ring_size,
                answer_count=answer_count,
            )
            report = validate_organic_structure(spec)
            matching_ring_ids = organic_ring_item_ids(spec, target_ring_size)
            assert len(matching_ring_ids) == answer_count
            assert all(len(ring) in TARGET_RING_SIZES for ring in spec.ring_atom_sets)
            assert report.max_valence <= 4
            assert report.crossing_count == 0


def test_organic_structure_rejects_answer_count_above_v1_support() -> None:
    with pytest.raises(ValueError):
        build_constrained_organic_structure(
            Random(42),
            target_bond_order="double",
            answer_count=ORGANIC_STRUCTURE_MAX_BOND_ORDER_COUNT + 1,
        )
    with pytest.raises(ValueError):
        build_constrained_organic_branch_structure(
            Random(43),
            answer_count=ORGANIC_STRUCTURE_MAX_BRANCH_POINT_COUNT + 1,
        )
    with pytest.raises(ValueError):
        build_constrained_organic_ring_size_structure(
            Random(44),
            target_ring_size=6,
            answer_count=ORGANIC_STRUCTURE_MAX_RING_SIZE_COUNT + 1,
        )
