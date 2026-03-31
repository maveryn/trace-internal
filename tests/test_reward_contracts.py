"""Reward-contract resolution and validation tests."""

from __future__ import annotations

from trace.core.reward_contracts import (
    ANSWER_REWARD_CONTRACT_ID,
    resolve_reward_contract,
    validate_reward_contract_payload,
)


def test_resolve_reward_contract_for_supported_evidence_types() -> None:
    cases = [
        ("bbox_set", "bbox_set_iou_v1"),
        ("integer", "numeric_exact_v1"),
        ("integer_list", "numeric_exact_v1"),
        ("label_set", "symbolic_set_exact_v1"),
        ("edge_set", "symbolic_set_exact_v1"),
        ("grid_point_path", "sequence_exact_v1"),
        ("point_path", "sequence_exact_v1"),
        ("graph_point", "point_set_match_v1"),
        ("graph_point_set", "point_set_match_v1"),
        ("point_set", "point_set_match_v1"),
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


def test_reward_contract_validation_rejects_mismatched_evidence_contract() -> None:
    payload = resolve_reward_contract(answer_type="integer", evidence_type="bbox_set").to_dict()
    payload["evidence"]["id"] = "numeric_exact_v1"
    error = validate_reward_contract_payload(
        payload,
        answer_type="integer",
        evidence_type="bbox_set",
    )
    assert error is not None
    assert "must match the resolved contract" in error
