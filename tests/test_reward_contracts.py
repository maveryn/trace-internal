"""Reward-contract resolution and validation tests."""

from __future__ import annotations

from trace.core.reward_contracts import (
    ANSWER_REWARD_CONTRACT_ID,
    resolve_reward_contract,
    validate_reward_contract_payload,
)


def test_resolve_reward_contract_for_supported_evidence_types() -> None:
    cases = [
        ("bbox_sequence", "bbox_sequence_soft_iou_v0"),
        ("bbox_set", "bbox_set_soft_iou_v0"),
        ("keyed_bbox_map", "keyed_bbox_map_soft_iou_v0"),
        ("keyed_point_map", "keyed_point_map_soft_distance_v0"),
        ("point_sequence", "point_sequence_soft_distance_v0"),
        ("point_pair_set", "point_pair_set_soft_distance_v0"),
        ("point_set", "point_set_soft_distance_v0"),
    ]

    for evidence_type, expected_contract_id in cases:
        contract = resolve_reward_contract(answer_type="integer", evidence_type=evidence_type)
        assert contract.answer.id == ANSWER_REWARD_CONTRACT_ID
        assert contract.answer.type == "integer"
        assert contract.evidence.id == expected_contract_id
        assert contract.evidence.type == evidence_type
        assert validate_reward_contract_payload(
            contract.to_dict(),
            answer_type="integer",
            evidence_type=evidence_type,
        ) is None


def test_resolve_reward_contract_rejects_unsupported_evidence_types() -> None:
    unsupported_types = [
        "integer",
        "integer_list",
        "label_list",
        "polygon_set",
        "line_set",
        "mask",
        "heatmap",
    ]

    for evidence_type in unsupported_types:
        try:
            resolve_reward_contract(answer_type="integer", evidence_type=evidence_type)
        except ValueError as exc:
            assert "unsupported evidence type" in str(exc)
        else:
            raise AssertionError(f"unsupported evidence type unexpectedly resolved: {evidence_type}")


def test_reward_contract_validation_rejects_mismatched_evidence_contract() -> None:
    payload = resolve_reward_contract(answer_type="integer", evidence_type="bbox_set").to_dict()
    payload["evidence"]["id"] = "point_set_soft_distance_v0"
    error = validate_reward_contract_payload(
        payload,
        answer_type="integer",
        evidence_type="bbox_set",
    )
    assert error is not None
    assert "must match the resolved contract" in error
