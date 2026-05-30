from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import numpy as np
from datasets import Dataset
from PIL import Image

if "qwen_vl_utils" not in sys.modules:
    vision_process = types.SimpleNamespace(fetch_video=lambda *args, **kwargs: [])
    sys.modules["qwen_vl_utils"] = types.SimpleNamespace(vision_process=vision_process)
    sys.modules["qwen_vl_utils.vision_process"] = vision_process

from examples.reward_function.reward_trace import compute_score
from verl.trainer.ppo.metric_utils import compute_rollout_group_metrics
from verl.utils.dataset import TraceRLHFDataset
from verl.utils.trace_mode import (
    default_trace_system_prompt_path,
    resolve_trace_prompt_key,
    resolve_trace_reward_mode,
    resolve_trace_system_prompt,
)
from verl.utils.trace_reward import score_trace_response
from verl.utils.val_reward import score_external_response


def _reward_contract(evidence_id: str, evidence_type: str, answer_type: str = "integer") -> dict[str, object]:
    return {
        "reward_contract_version": "v1",
        "answer": {"id": "answer_exact_match_v1", "type": answer_type},
        "evidence": {"id": evidence_id, "type": evidence_type},
    }


def test_trace_reward_supports_all_active_evidence_contracts() -> None:
    cases = [
        (
            {"answer": 3, "evidence": [[10, 10, 20, 20], [30, 30, 40, 40]]},
            {"type": "integer", "value": 3},
            {"type": "bbox_set", "value": [[10, 10, 20, 20], [30, 30, 40, 40]]},
            _reward_contract("bbox_set_soft_iou_v1", "bbox_set"),
        ),
        (
            {"answer": 3, "evidence": [[10, 10, 20, 20], [30, 30, 40, 40]]},
            {"type": "integer", "value": 3},
            {"type": "bbox_sequence", "value": [[10, 10, 20, 20], [30, 30, 40, 40]]},
            _reward_contract("bbox_sequence_soft_iou_v1", "bbox_sequence"),
        ),
        (
            {"answer": 4, "evidence": [[0, 3], [0, 0], [4, 0]]},
            {"type": "integer", "value": 4},
            {"type": "point_set", "value": [[0, 0], [4, 0], [0, 3]]},
            _reward_contract("point_set_soft_distance_v1", "point_set"),
        ),
        (
            {"answer": 2, "evidence": [[100, 200], [320, 420]]},
            {"type": "integer", "value": 2},
            {"type": "point_set", "value": [[100, 200], [320, 420]]},
            _reward_contract("point_set_soft_distance_v1", "point_set"),
        ),
        (
            {"answer": 2, "evidence": [[100, 200], [320, 420]]},
            {"type": "integer", "value": 2},
            {"type": "point_sequence", "value": [[100, 200], [320, 420]]},
            _reward_contract("point_sequence_soft_distance_v1", "point_sequence"),
        ),
        (
            {"answer": 2, "evidence": [[[100, 200], [320, 420]], [[500, 300], [620, 300]]]},
            {"type": "integer", "value": 2},
            {"type": "point_pair_set", "value": [[[320, 420], [100, 200]], [[620, 300], [500, 300]]]},
            _reward_contract("point_pair_set_soft_distance_v1", "point_pair_set"),
        ),
        (
            {"answer": 2, "evidence": {"A": [100, 200], "B": [320, 420]}},
            {"type": "integer", "value": 2},
            {"type": "keyed_point_map", "value": {"B": [320, 420], "A": [100, 200]}},
            _reward_contract("keyed_point_map_soft_distance_v1", "keyed_point_map"),
        ),
        (
            {"answer": 2, "evidence": {"source": [10, 10, 20, 20], "target": [30, 30, 40, 40]}},
            {"type": "integer", "value": 2},
            {"type": "keyed_bbox_map", "value": {"target": [30, 30, 40, 40], "source": [10, 10, 20, 20]}},
            _reward_contract("keyed_bbox_map_soft_iou_v1", "keyed_bbox_map"),
        ),
    ]

    for payload, answer_gt, evidence_gt, reward_contract in cases:
        response = f"Reasoning.\n{json.dumps(payload)}"
        score = score_trace_response(
            response=response,
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            reward_contract=reward_contract,
        )
        assert score["overall"] == 1.0
        assert score["answer_reward"] == 1.0
        assert score["evidence_reward"] == 1.0
        assert score["format"] == 1.0


def test_trace_reward_point_evidence_uses_soft_distance_without_threshold() -> None:
    response = '{"answer":2,"evidence":[[132,200]]}'
    score = score_trace_response(
        response=response,
        answer_gt={"type": "integer", "value": 2},
        evidence_gt={"type": "point_set", "value": [[100, 200]]},
        reward_contract=_reward_contract("point_set_soft_distance_v1", "point_set"),
        point_half_life_px=32.0,
    )

    assert np.isclose(score["evidence_reward"], 0.5)
    assert score["evidence_parse_ok"] == 1.0


def test_trace_reward_exact_json_preserves_parsed_string_answers() -> None:
    score = score_trace_response(
        response='{"answer":"K","evidence":[[10,10,20,20]]}',
        answer_gt={"type": "option_letter", "value": "K"},
        evidence_gt={"type": "bbox_set", "value": [[10, 10, 20, 20]]},
        reward_contract=_reward_contract("bbox_set_soft_iou_v1", "bbox_set", answer_type="option_letter"),
    )

    assert score["answer_reward"] == 1.0
    assert score["evidence_reward"] == 1.0
    assert score["overall"] == 1.0


def test_trace_reward_point_half_life_scales_with_source_image_size() -> None:
    expected_half_life = 0.035 * float(np.hypot(1280, 1280))
    response = json.dumps({"answer": 2, "evidence": [[100 + expected_half_life, 200]]})
    score = score_trace_response(
        response=response,
        answer_gt={"type": "integer", "value": 2},
        evidence_gt={"type": "point_set", "value": [[100, 200]]},
        reward_contract=_reward_contract("point_set_soft_distance_v1", "point_set"),
        image_size=[1280, 1280],
    )

    assert np.isclose(score["evidence_reward"], 0.5)
    assert np.isclose(score["evidence_point_half_life_px"], expected_half_life)


def test_trace_reward_point_half_life_uses_configured_clamp() -> None:
    small = score_trace_response(
        response='{"answer":2,"evidence":[[120,200]]}',
        answer_gt={"type": "integer", "value": 2},
        evidence_gt={"type": "point_set", "value": [[100, 200]]},
        reward_contract=_reward_contract("point_set_soft_distance_v1", "point_set"),
        image_size=[100, 100],
    )
    large = score_trace_response(
        response='{"answer":2,"evidence":[[180,200]]}',
        answer_gt={"type": "integer", "value": 2},
        evidence_gt={"type": "point_set", "value": [[100, 200]]},
        reward_contract=_reward_contract("point_set_soft_distance_v1", "point_set"),
        image_size=[4000, 4000],
    )

    assert np.isclose(small["evidence_reward"], 0.5)
    assert small["evidence_point_half_life_px"] == 20.0
    assert np.isclose(large["evidence_reward"], 0.5)
    assert large["evidence_point_half_life_px"] == 80.0


def test_trace_reward_ordered_evidence_is_sequence_sensitive() -> None:
    response = '{"answer":2,"evidence":[[30,30,40,40],[10,10,20,20]]}'
    score = score_trace_response(
        response=response,
        answer_gt={"type": "integer", "value": 2},
        evidence_gt={"type": "bbox_sequence", "value": [[10, 10, 20, 20], [30, 30, 40, 40]]},
        reward_contract=_reward_contract("bbox_sequence_soft_iou_v1", "bbox_sequence"),
    )

    assert score["evidence_reward"] == 0.0
    assert score["evidence_parse_ok"] == 1.0


def test_trace_reward_answer_mode_ignores_evidence_in_overall() -> None:
    reward_contract = _reward_contract("bbox_set_soft_iou_v1", "bbox_set")

    score = score_trace_response(
        response='Reasoning.\n{"answer":2}',
        answer_gt={"type": "integer", "value": 2},
        evidence_gt={"type": "bbox_set", "value": [[0, 0, 10, 10]]},
        reward_contract=reward_contract,
        trace_reward_mode="answer",
    )

    assert score["answer_reward"] == 1.0
    assert score["evidence_reward"] == 0.0
    assert score["overall"] == 1.0
    assert score["trace_reward_mode_answer"] == 1.0
    assert score["trace_reward_mode_answer_only"] == 1.0
    assert score["trace_reward_mode_answer_and_evidence"] == 0.0


def test_trace_reward_format_requires_final_json_object_not_tags() -> None:
    reward_contract = _reward_contract("bbox_set_soft_iou_v1", "bbox_set")

    score = score_trace_response(
        response='Reasoning outside JSON is allowed.\n{"answer":2}',
        answer_gt={"type": "integer", "value": 2},
        evidence_gt={"type": "bbox_set", "value": [[0, 0, 10, 10]]},
        reward_contract=reward_contract,
        trace_reward_mode="answer",
    )

    assert score["format"] == 1.0
    assert score["format_structure_ok"] == 1.0
    assert score["format_json_ok"] == 1.0
    assert score["format_schema_ok"] == 1.0
    assert score["answer_reward"] == 1.0


def test_trace_reward_format_accepts_final_json_code_block() -> None:
    reward_contract = _reward_contract("bbox_set_soft_iou_v1", "bbox_set")

    score = score_trace_response(
        response='Reasoning.\n```json\n{"answer":2}\n```',
        answer_gt={"type": "integer", "value": 2},
        evidence_gt={"type": "bbox_set", "value": [[0, 0, 10, 10]]},
        reward_contract=reward_contract,
        trace_reward_mode="answer",
    )

    assert score["format"] == 1.0
    assert score["format_structure_ok"] == 1.0
    assert score["format_json_ok"] == 1.0
    assert score["format_schema_ok"] == 1.0
    assert score["answer_reward"] == 1.0


def test_trace_reward_format_rejects_wrong_final_json_schema_without_partial_credit() -> None:
    reward_contract = _reward_contract("bbox_set_soft_iou_v1", "bbox_set")

    score = score_trace_response(
        response='Reasoning.\n{"result":2}',
        answer_gt={"type": "integer", "value": 2},
        evidence_gt={"type": "bbox_set", "value": [[0, 0, 10, 10]]},
        reward_contract=reward_contract,
        trace_reward_mode="answer",
        format_weight=0.1,
    )

    assert score["format"] == 0.0
    assert score["format_structure_ok"] == 1.0
    assert score["format_json_ok"] == 1.0
    assert score["format_schema_ok"] == 0.0
    assert score["overall"] == 0.0


def test_trace_reward_format_rejects_non_final_json_object() -> None:
    reward_contract = _reward_contract("bbox_set_soft_iou_v1", "bbox_set")

    score = score_trace_response(
        response='The answer is {"answer":2}.',
        answer_gt={"type": "integer", "value": 2},
        evidence_gt={"type": "bbox_set", "value": [[0, 0, 10, 10]]},
        reward_contract=reward_contract,
        trace_reward_mode="answer",
    )

    assert score["format"] == 0.0
    assert score["format_structure_ok"] == 0.0
    assert score["format_json_ok"] == 0.0
    assert score["format_schema_ok"] == 0.0
    assert score["answer_reward"] == 1.0


def test_trace_reward_answer_mode_does_not_gate_correctness_on_format() -> None:
    reward_contract = _reward_contract("bbox_set_soft_iou_v1", "bbox_set")

    score = score_trace_response(
        response='The answer is {"answer":2}.',
        answer_gt={"type": "integer", "value": 2},
        evidence_gt={"type": "bbox_set", "value": [[0, 0, 10, 10]]},
        reward_contract=reward_contract,
        trace_reward_mode="answer",
        format_weight=0.1,
    )

    assert score["answer_reward"] == 1.0
    assert score["format"] == 0.0
    assert score["overall"] == 0.9
    assert score["zero_reward"] == 0.0


def test_trace_reward_recovers_legacy_answer_tag_without_format_credit() -> None:
    reward_contract = _reward_contract("bbox_set_soft_iou_v1", "bbox_set")

    score = score_trace_response(
        response='<answer>{"answer":2}</answer>',
        answer_gt={"type": "integer", "value": 2},
        evidence_gt={"type": "bbox_set", "value": [[0, 0, 10, 10]]},
        reward_contract=reward_contract,
        trace_reward_mode="answer",
        format_weight=0.1,
    )

    assert score["answer_reward"] == 1.0
    assert score["json_found"] == 1.0
    assert score["format"] == 0.0
    assert score["overall"] == 0.9


def test_trace_reward_zero_reward_tracks_task_correctness_not_format_bonus() -> None:
    reward_contract = _reward_contract("bbox_set_soft_iou_v1", "bbox_set")

    score = score_trace_response(
        response='{"answer":3}',
        answer_gt={"type": "integer", "value": 2},
        evidence_gt={"type": "bbox_set", "value": [[0, 0, 10, 10]]},
        reward_contract=reward_contract,
        trace_reward_mode="answer",
        format_weight=0.1,
    )

    assert score["answer_reward"] == 0.0
    assert score["format"] == 1.0
    assert score["overall"] == 0.1
    assert score["zero_reward"] == 1.0


def test_trace_reward_default_format_weight_is_zero() -> None:
    reward_contract = _reward_contract("bbox_set_soft_iou_v1", "bbox_set")

    score = score_trace_response(
        response='{"answer":3}',
        answer_gt={"type": "integer", "value": 2},
        evidence_gt={"type": "bbox_set", "value": [[0, 0, 10, 10]]},
        reward_contract=reward_contract,
        trace_reward_mode="answer",
    )

    assert score["answer_reward"] == 0.0
    assert score["format"] == 1.0
    assert score["format_weight"] == 0.0
    assert score["overall"] == 0.0


def test_trace_reward_answer_scoring_mode_can_use_legacy_strict_matching() -> None:
    reward_contract = _reward_contract("bbox_set_soft_iou_v1", "bbox_set", answer_type="string")

    current = score_trace_response(
        response='{"answer":"The answer is B."}',
        answer_gt={"type": "string", "value": "B"},
        evidence_gt={"type": "bbox_set", "value": [[0, 0, 10, 10]]},
        reward_contract=reward_contract,
        trace_reward_mode="answer",
        trace_answer_scoring="exact_json",
    )
    legacy = score_trace_response(
        response='{"answer":"The answer is B."}',
        answer_gt={"type": "string", "value": "B"},
        evidence_gt={"type": "bbox_set", "value": [[0, 0, 10, 10]]},
        reward_contract=reward_contract,
        trace_reward_mode="answer",
        trace_answer_scoring="legacy_strict",
    )

    assert current["answer_reward"] == 0.0
    assert current["trace_answer_scoring_exact_json"] == 1.0
    assert legacy["answer_reward"] == 1.0
    assert legacy["trace_answer_scoring_legacy_strict"] == 1.0


def test_trace_reward_exact_json_preserves_numeric_string_labels() -> None:
    reward_contract = _reward_contract("bbox_set_soft_iou_v1", "bbox_set", answer_type="string")

    correct = score_trace_response(
        response='{"answer":"4"}',
        answer_gt={"type": "string", "value": "4"},
        evidence_gt={"type": "bbox_set", "value": [[0, 0, 10, 10]]},
        reward_contract=reward_contract,
        trace_reward_mode="answer",
        trace_answer_scoring="exact_json",
    )
    numeric = score_trace_response(
        response='{"answer":4}',
        answer_gt={"type": "string", "value": "4"},
        evidence_gt={"type": "bbox_set", "value": [[0, 0, 10, 10]]},
        reward_contract=reward_contract,
        trace_reward_mode="answer",
        trace_answer_scoring="exact_json",
    )

    assert correct["answer_reward"] == 1.0
    assert numeric["answer_reward"] == 0.0


def test_trace_reward_legacy_index_list_is_order_sensitive() -> None:
    reward_contract = _reward_contract("bbox_set_soft_iou_v1", "bbox_set", answer_type="index_list")

    correct = score_trace_response(
        response='{"answer":[1,3,2,4]}',
        answer_gt={"type": "index_list", "value": [1, 3, 2, 4]},
        evidence_gt={"type": "bbox_set", "value": [[0, 0, 1, 1]]},
        reward_contract=reward_contract,
        trace_reward_mode="answer",
        trace_answer_scoring="legacy_strict",
    )
    permuted = score_trace_response(
        response='{"answer":[1,2,3,4]}',
        answer_gt={"type": "index_list", "value": [1, 3, 2, 4]},
        evidence_gt={"type": "bbox_set", "value": [[0, 0, 1, 1]]},
        reward_contract=reward_contract,
        trace_reward_mode="answer",
        trace_answer_scoring="legacy_strict",
    )

    assert correct["answer_reward"] == 1.0
    assert permuted["answer_reward"] == 0.0


def test_trace_dataset_helpers_support_trace_rows(tmp_path: Path) -> None:
    image_path = tmp_path / "images" / "sample.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (12, 12), (255, 255, 255)).save(image_path)

    dataset = TraceRLHFDataset.__new__(TraceRLHFDataset)
    dataset.prompt_key = "prompt"
    dataset.answer_key = "answer"
    dataset.image_dir = None
    dataset.dataset_root = tmp_path
    dataset.system_prompt = "System contract"
    dataset.format_prompt = None
    dataset.format_prompt_variant = "boxed_only"
    dataset.image_key = "images"
    dataset.video_key = "videos"

    prompt_key, answer_key = dataset._resolve_prompt_answer_keys(
        {"prompt": "Solve it", "answer_gt": {"type": "integer", "value": 4}}
    )
    assert (prompt_key, answer_key) == ("prompt", "answer_gt")

    prompt_key, answer_key = dataset._resolve_prompt_answer_keys(
        {"prompt": "Solve it", "ground_truth": ["A"]}
    )
    assert (prompt_key, answer_key) == ("prompt", "ground_truth")

    dataset.prompt_key = "prompt_answer"
    dataset.answer_key = "answer_gt"
    prompt_key, answer_key = dataset._resolve_prompt_answer_keys(
        {"prompt_answer_only": "Solve it", "answer_gt": {"type": "integer", "value": 4}}
    )
    assert (prompt_key, answer_key) == ("prompt_answer_only", "answer_gt")

    messages = dataset._build_messages(
        {
            "prompt_answer": "What is shown?",
            "answer_gt": {"type": "integer", "value": 1},
            "images": [{"path": "images/sample.png"}],
        },
        prompt_key="prompt_answer",
    )
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"

    normalized = dataset._normalize_trace_metadata_fields(
        {
            "answer_gt": '{"type":"integer","value":2}',
            "reward_contract": '{"answer":{"id":"answer_exact_match_v1"}}',
        }
    )
    assert normalized["answer_gt"]["value"] == 2
    assert normalized["reward_contract"]["answer"]["id"] == "answer_exact_match_v1"


def test_external_validation_scoring_extracts_trace_json_answer() -> None:
    score, extracted, answer, method = score_external_response(
        response='Reasoning first.\n{"answer": "Signal"}',
        ground_truth="Signal",
    )

    assert score == 1.0
    assert extracted is True
    assert answer == "Signal"
    assert method.startswith("trace_json:")


def test_external_validation_scoring_counts_wrong_trace_json_as_extracted() -> None:
    score, extracted, answer, method = score_external_response(
        response='{"answer": "Coal, Peat and Manufactured Gas"}',
        ground_truth="Nuclear",
    )

    assert score == 0.0
    assert extracted is True
    assert answer == "Coal, Peat and Manufactured Gas"
    assert method.startswith("trace_json:")


def test_external_validation_scoring_supports_extended_choice_letters() -> None:
    for letter in ("H", "I", "J", "K", "L"):
        score, extracted, answer, method = score_external_response(
            response=f'{{"answer": "{letter}"}}',
            ground_truth=letter,
            parser_family="exact_or_choice",
        )

        assert score == 1.0
        assert extracted is True
        assert answer == letter
        assert method.startswith("trace_json:")

    score, extracted, answer, _ = score_external_response(
        response='{"answer": "A"}',
        ground_truth="J",
        parser_family="exact_or_choice",
    )
    assert score == 0.0
    assert extracted is True
    assert answer == "A"


def test_trace_dataset_supports_auto_balanced_domain_sampler() -> None:
    dataset = TraceRLHFDataset.__new__(TraceRLHFDataset)
    dataset.dataset = Dataset.from_list(
        [
            {"domain": "charts"},
            {"domain": "geometry"},
            {"domain": "charts"},
            {"domain": "geometry"},
            {"domain": "charts"},
            {"domain": "geometry"},
        ]
    )
    dataset.domain_sampling_key = "domain"
    dataset.per_batch_domain_weights = "auto"
    dataset.domain2indices = None
    dataset.domain_weights = None

    dataset._prepare_domain_sampling()
    sampler = dataset.build_domain_sampler(batch_size=4, seed=0, shuffle=False)
    sampled_indices = list(sampler)

    assert dataset.domain_weights == {"charts": 0.5, "geometry": 0.5}
    assert sampled_indices == [0, 2, 1, 3]


def test_trace_output_mode_resolves_prompt_reward_and_system_prompt_defaults() -> None:
    assert resolve_trace_prompt_key("auto", trace_output_mode="answer") == "prompt_answer"
    assert resolve_trace_prompt_key("auto", trace_output_mode="evidence") == "prompt_answer_and_evidence"
    assert resolve_trace_prompt_key("auto", trace_output_mode="answer_and_evidence") == "prompt_answer_and_evidence"
    assert resolve_trace_reward_mode("auto", trace_output_mode="answer") == "answer"
    assert resolve_trace_reward_mode("auto", trace_output_mode="evidence") == "answer_and_evidence"
    assert resolve_trace_reward_mode("auto", trace_output_mode="answer_and_evidence") == "answer_and_evidence"
    assert resolve_trace_reward_mode("answer_only", trace_output_mode="answer_and_evidence") == "answer"

    answer_prompt_path = default_trace_system_prompt_path(trace_output_mode="answer")
    evidence_alias_prompt_path = default_trace_system_prompt_path(trace_output_mode="evidence")
    evidence_prompt_path = default_trace_system_prompt_path(trace_output_mode="answer_and_evidence")
    assert answer_prompt_path.name == "trace_vero_json_system_prompt_answer.txt"
    assert evidence_alias_prompt_path == evidence_prompt_path
    assert evidence_prompt_path.name == "trace_vero_json_system_prompt_answer_and_evidence.txt"
    assert resolve_trace_system_prompt("auto", trace_output_mode="answer") == str(answer_prompt_path)
    assert resolve_trace_system_prompt("auto", trace_output_mode="evidence") == str(evidence_prompt_path)
    assert resolve_trace_system_prompt("auto", trace_output_mode="answer_and_evidence") == str(evidence_prompt_path)


def test_reward_trace_wrapper_returns_score_key() -> None:
    result = compute_score(
        data_source="trace",
        solution_str='Reasoning.\n{"answer":2}',
        ground_truth=2,
        extra_info={
            "answer_gt": {"type": "integer", "value": 2},
            "evidence_gt": {"type": "bbox_set", "value": [[0, 0, 10, 10]]},
            "reward_contract": _reward_contract("bbox_set_soft_iou_v1", "bbox_set"),
        },
        trace_reward_mode="answer",
        trace_format_weight=0.1,
    )
    assert result["score"] == 1.0
    assert result["overall"] == 1.0


def test_reward_trace_wrapper_accepts_legacy_answer_scoring_mode() -> None:
    result = compute_score(
        data_source="trace",
        solution_str='{"answer":"The answer is B."}',
        ground_truth="B",
        extra_info={
            "answer_gt": {"type": "string", "value": "B"},
            "evidence_gt": {"type": "bbox_set", "value": [[0, 0, 10, 10]]},
            "reward_contract": _reward_contract("bbox_set_soft_iou_v1", "bbox_set", answer_type="string"),
        },
        trace_reward_mode="answer",
        trace_answer_scoring="legacy_strict",
        trace_format_weight=0.1,
    )
    assert result["answer_reward"] == 1.0
    assert result["trace_answer_scoring_legacy_strict"] == 1.0


def test_reward_trace_wrapper_uses_trace_output_mode_when_reward_mode_is_auto() -> None:
    result = compute_score(
        data_source="trace",
        solution_str='Reasoning.\n{"answer":2}',
        ground_truth=2,
        extra_info={
            "answer_gt": {"type": "integer", "value": 2},
            "evidence_gt": {"type": "bbox_set", "value": [[0, 0, 10, 10]]},
            "reward_contract": _reward_contract("bbox_set_soft_iou_v1", "bbox_set"),
        },
        trace_reward_mode="auto",
        trace_output_mode="answer",
        trace_format_weight=0.1,
    )
    assert result["trace_reward_mode_answer"] == 1.0
    assert result["overall"] == 1.0


def test_rollout_group_metrics_are_grouped_by_uid() -> None:
    metrics = compute_rollout_group_metrics(
        ["a", "a", "b", "b"],
        np.array([0.0, 0.0, 1.0, 1.0]),
        zero_solve_threshold=0.0,
        perfect_solve_threshold=1.0,
    )
    assert metrics["rlvr_stats/zero_solve_count"] == 1.0
    assert metrics["rlvr_stats/perfect_solve_count"] == 1.0


def test_rollout_group_metrics_expect_task_scores_not_format_weighted_overall() -> None:
    # Prompt a has no correct rollout but every rollout would have been positive
    # under additive overall reward because of the format bonus.
    metrics = compute_rollout_group_metrics(
        ["a", "a", "b", "b"],
        np.array([0.0, 0.0, 1.0, 0.0]),
        zero_solve_threshold=0.0,
        perfect_solve_threshold=1.0,
    )
    assert metrics["rlvr_stats/zero_solve_count"] == 1.0
    assert metrics["rlvr_stats/perfect_solve_count"] == 0.0
