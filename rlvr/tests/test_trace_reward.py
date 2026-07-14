from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import numpy as np
import pytest
from datasets import Dataset
from PIL import Image

if "qwen_vl_utils" not in sys.modules:
    vision_process = types.SimpleNamespace(fetch_video=lambda *args, **kwargs: [])
    sys.modules["qwen_vl_utils"] = types.SimpleNamespace(vision_process=vision_process)
    sys.modules["qwen_vl_utils.vision_process"] = vision_process

from examples.reward_function.reward_trace import compute_score
from verl.trainer.ppo.metric_utils import compute_rollout_group_metrics, reduce_numeric_reward_metrics
from verl.utils.dataset import TraceRLHFDataset
from verl.utils.trace_mode import (
    TRACE_OUTPUT_MODE_TASK_CONDITIONED,
    default_trace_system_prompt_path,
    resolve_trace_prompt_key,
    resolve_trace_reward_mode,
    resolve_trace_row_output_mode,
    resolve_trace_system_prompt,
)
from verl.utils.trace_reward import score_trace_response
from verl.utils.val_reward import score_external_response


def _reward_contract(annotation_id: str, annotation_type: str, answer_type: str = "integer") -> dict[str, object]:
    return {
        "reward_contract_version": "v0",
        "answer": {"id": "answer_exact_match_v0", "type": answer_type},
        "annotation": {"id": annotation_id, "type": annotation_type},
    }


def test_trace_reward_supports_all_active_annotation_contracts() -> None:
    cases = [
        (
            {"answer": 3, "annotation": [[10, 10, 20, 20], [30, 30, 40, 40]]},
            {"type": "integer", "value": 3},
            {"type": "bbox_set", "value": [[10, 10, 20, 20], [30, 30, 40, 40]]},
            _reward_contract("bbox_set_soft_iou_v0", "bbox_set"),
        ),
        (
            {"answer": 3, "annotation": [[10, 10, 20, 20], [30, 30, 40, 40]]},
            {"type": "integer", "value": 3},
            {"type": "bbox_sequence", "value": [[10, 10, 20, 20], [30, 30, 40, 40]]},
            _reward_contract("bbox_sequence_soft_iou_v0", "bbox_sequence"),
        ),
        (
            {"answer": 4, "annotation": [[0, 3], [0, 0], [4, 0]]},
            {"type": "integer", "value": 4},
            {"type": "point_set", "value": [[0, 0], [4, 0], [0, 3]]},
            _reward_contract("point_set_soft_distance_v0", "point_set"),
        ),
        (
            {"answer": 2, "annotation": [[100, 200], [320, 420]]},
            {"type": "integer", "value": 2},
            {"type": "point_set", "value": [[100, 200], [320, 420]]},
            _reward_contract("point_set_soft_distance_v0", "point_set"),
        ),
        (
            {"answer": 2, "annotation": [[100, 200], [320, 420]]},
            {"type": "integer", "value": 2},
            {"type": "point_sequence", "value": [[100, 200], [320, 420]]},
            _reward_contract("point_sequence_soft_distance_v0", "point_sequence"),
        ),
        (
            {"answer": 2, "annotation": [[[100, 200], [320, 420]], [[500, 300], [620, 300]]]},
            {"type": "integer", "value": 2},
            {"type": "segment_set", "value": [[[320, 420], [100, 200]], [[620, 300], [500, 300]]]},
            _reward_contract("segment_set_soft_distance_v0", "segment_set"),
        ),
        (
            {"answer": 2, "annotation": {"A": [100, 200], "B": [320, 420]}},
            {"type": "integer", "value": 2},
            {"type": "point_map", "value": {"B": [320, 420], "A": [100, 200]}},
            _reward_contract("point_map_soft_distance_v0", "point_map"),
        ),
        (
            {"answer": 2, "annotation": {"source": [10, 10, 20, 20], "target": [30, 30, 40, 40]}},
            {"type": "integer", "value": 2},
            {"type": "bbox_map", "value": {"target": [30, 30, 40, 40], "source": [10, 10, 20, 20]}},
            _reward_contract("bbox_map_soft_iou_v0", "bbox_map"),
        ),
    ]

    for payload, answer_gt, annotation_gt, reward_contract in cases:
        response = f"Reasoning.\n{json.dumps(payload)}"
        score = score_trace_response(
            response=response,
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            reward_contract=reward_contract,
        )
        assert score["overall"] == 1.0
        assert score["answer_reward"] == 1.0
        assert score["annotation_reward"] == 1.0
        assert score["format"] == 1.0


def test_trace_reward_point_annotation_uses_soft_distance_without_threshold() -> None:
    response = '{"answer":2,"annotation":[[132,200]]}'
    score = score_trace_response(
        response=response,
        answer_gt={"type": "integer", "value": 2},
        annotation_gt={"type": "point_set", "value": [[100, 200]]},
        reward_contract=_reward_contract("point_set_soft_distance_v0", "point_set"),
        point_half_life_px=32.0,
    )

    assert np.isclose(score["annotation_reward"], 0.5)
    assert score["annotation_parse_ok"] == 1.0


def test_trace_reward_exact_json_preserves_parsed_string_answers() -> None:
    score = score_trace_response(
        response='{"answer":"K","annotation":[[10,10,20,20]]}',
        answer_gt={"type": "option_letter", "value": "K"},
        annotation_gt={"type": "bbox_set", "value": [[10, 10, 20, 20]]},
        reward_contract=_reward_contract("bbox_set_soft_iou_v0", "bbox_set", answer_type="option_letter"),
    )

    assert score["answer_reward"] == 1.0
    assert score["annotation_reward"] == 1.0
    assert score["overall"] == 1.0


def test_trace_reward_point_half_life_scales_with_source_image_size() -> None:
    expected_half_life = 0.035 * float(np.hypot(1280, 1280))
    response = json.dumps({"answer": 2, "annotation": [[100 + expected_half_life, 200]]})
    score = score_trace_response(
        response=response,
        answer_gt={"type": "integer", "value": 2},
        annotation_gt={"type": "point_set", "value": [[100, 200]]},
        reward_contract=_reward_contract("point_set_soft_distance_v0", "point_set"),
        image_size=[1280, 1280],
    )

    assert np.isclose(score["annotation_reward"], 0.5)
    assert np.isclose(score["annotation_point_half_life_px"], expected_half_life)


def test_trace_reward_point_half_life_uses_configured_clamp() -> None:
    small = score_trace_response(
        response='{"answer":2,"annotation":[[120,200]]}',
        answer_gt={"type": "integer", "value": 2},
        annotation_gt={"type": "point_set", "value": [[100, 200]]},
        reward_contract=_reward_contract("point_set_soft_distance_v0", "point_set"),
        image_size=[100, 100],
    )
    large = score_trace_response(
        response='{"answer":2,"annotation":[[180,200]]}',
        answer_gt={"type": "integer", "value": 2},
        annotation_gt={"type": "point_set", "value": [[100, 200]]},
        reward_contract=_reward_contract("point_set_soft_distance_v0", "point_set"),
        image_size=[4000, 4000],
    )

    assert np.isclose(small["annotation_reward"], 0.5)
    assert small["annotation_point_half_life_px"] == 20.0
    assert np.isclose(large["annotation_reward"], 0.5)
    assert large["annotation_point_half_life_px"] == 80.0


def test_trace_reward_ordered_annotation_is_sequence_sensitive() -> None:
    response = '{"answer":2,"annotation":[[30,30,40,40],[10,10,20,20]]}'
    score = score_trace_response(
        response=response,
        answer_gt={"type": "integer", "value": 2},
        annotation_gt={"type": "bbox_sequence", "value": [[10, 10, 20, 20], [30, 30, 40, 40]]},
        reward_contract=_reward_contract("bbox_sequence_soft_iou_v0", "bbox_sequence"),
    )

    assert score["annotation_reward"] == 0.0
    assert score["annotation_parse_ok"] == 1.0


def test_trace_reward_answer_mode_ignores_annotation_in_overall() -> None:
    reward_contract = _reward_contract("bbox_set_soft_iou_v0", "bbox_set")

    score = score_trace_response(
        response='Reasoning.\n{"answer":2}',
        answer_gt={"type": "integer", "value": 2},
        annotation_gt={"type": "bbox_set", "value": [[0, 0, 10, 10]]},
        reward_contract=reward_contract,
        trace_reward_mode="answer",
    )

    assert score["answer_reward"] == 1.0
    assert score["annotation_reward"] == 0.0
    assert score["overall"] == 1.0
    assert score["trace_reward_mode_answer"] == 1.0
    assert score["trace_reward_mode_answer_only"] == 1.0
    assert score["trace_reward_mode_answer_and_annotation"] == 0.0


def test_trace_reward_annotation_additive_uses_normalized_fraction_and_format_blend() -> None:
    reward_contract = _reward_contract("bbox_set_soft_iou_v0", "bbox_set")

    score = score_trace_response(
        response='Reasoning.\n{"answer":3,"annotation":[[0,0,10,10]]}',
        answer_gt={"type": "integer", "value": 2},
        annotation_gt={"type": "bbox_set", "value": [[0, 0, 10, 10]]},
        reward_contract=reward_contract,
        trace_reward_mode="answer_and_annotation",
        trace_annotation_reward_formula="additive",
        answer_weight=0.75,
        annotation_weight=0.25,
        format_weight=0.05,
    )

    assert score["answer_reward"] == 0.0
    assert score["annotation_reward"] == 1.0
    assert score["task_reward_raw"] == 0.25
    assert score["overall"] == 0.2875
    assert score["trace_answer_weight"] == 0.75
    assert score["trace_annotation_weight"] == 0.25
    assert 0.0 <= score["overall"] <= 1.0


def test_trace_reward_annotation_gated_requires_answer_for_annotation_credit() -> None:
    reward_contract = _reward_contract("bbox_set_soft_iou_v0", "bbox_set")

    wrong_answer = score_trace_response(
        response='Reasoning.\n{"answer":3,"annotation":[[0,0,10,10]]}',
        answer_gt={"type": "integer", "value": 2},
        annotation_gt={"type": "bbox_set", "value": [[0, 0, 10, 10]]},
        reward_contract=reward_contract,
        trace_reward_mode="answer_and_annotation",
        trace_annotation_reward_formula="gated",
        answer_weight=0.5,
        annotation_weight=0.5,
        format_weight=0.05,
    )
    correct_answer_bad_annotation = score_trace_response(
        response='Reasoning.\n{"answer":2,"annotation":[[100,100,110,110]]}',
        answer_gt={"type": "integer", "value": 2},
        annotation_gt={"type": "bbox_set", "value": [[0, 0, 10, 10]]},
        reward_contract=reward_contract,
        trace_reward_mode="answer_and_annotation",
        trace_annotation_reward_formula="gated",
        answer_weight=0.5,
        annotation_weight=0.5,
        format_weight=0.05,
    )

    assert wrong_answer["answer_reward"] == 0.0
    assert wrong_answer["annotation_reward"] == 1.0
    assert wrong_answer["task_reward_raw"] == 0.0
    assert wrong_answer["overall"] == 0.05
    assert wrong_answer["zero_reward"] == 1.0

    assert correct_answer_bad_annotation["answer_reward"] == 1.0
    assert correct_answer_bad_annotation["annotation_reward"] == 0.0
    assert correct_answer_bad_annotation["task_reward_raw"] == 0.5
    assert correct_answer_bad_annotation["overall"] == 0.525
    assert correct_answer_bad_annotation["zero_reward"] == 0.0
    assert 0.0 <= correct_answer_bad_annotation["overall"] <= 1.0


def test_trace_reward_format_requires_final_json_object_not_tags() -> None:
    reward_contract = _reward_contract("bbox_set_soft_iou_v0", "bbox_set")

    score = score_trace_response(
        response='Reasoning outside JSON is allowed.\n{"answer":2}',
        answer_gt={"type": "integer", "value": 2},
        annotation_gt={"type": "bbox_set", "value": [[0, 0, 10, 10]]},
        reward_contract=reward_contract,
        trace_reward_mode="answer",
    )

    assert score["format"] == 1.0
    assert score["format_structure_ok"] == 1.0
    assert score["format_json_ok"] == 1.0
    assert score["format_schema_ok"] == 1.0
    assert score["answer_reward"] == 1.0


def test_trace_reward_format_accepts_final_json_code_block() -> None:
    reward_contract = _reward_contract("bbox_set_soft_iou_v0", "bbox_set")

    score = score_trace_response(
        response='Reasoning.\n```json\n{"answer":2}\n```',
        answer_gt={"type": "integer", "value": 2},
        annotation_gt={"type": "bbox_set", "value": [[0, 0, 10, 10]]},
        reward_contract=reward_contract,
        trace_reward_mode="answer",
    )

    assert score["format"] == 1.0
    assert score["format_structure_ok"] == 1.0
    assert score["format_json_ok"] == 1.0
    assert score["format_schema_ok"] == 1.0
    assert score["answer_reward"] == 1.0


def test_trace_reward_format_rejects_wrong_final_json_schema_without_partial_credit() -> None:
    reward_contract = _reward_contract("bbox_set_soft_iou_v0", "bbox_set")

    score = score_trace_response(
        response='Reasoning.\n{"result":2}',
        answer_gt={"type": "integer", "value": 2},
        annotation_gt={"type": "bbox_set", "value": [[0, 0, 10, 10]]},
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
    reward_contract = _reward_contract("bbox_set_soft_iou_v0", "bbox_set")

    score = score_trace_response(
        response='The answer is {"answer":2}.',
        answer_gt={"type": "integer", "value": 2},
        annotation_gt={"type": "bbox_set", "value": [[0, 0, 10, 10]]},
        reward_contract=reward_contract,
        trace_reward_mode="answer",
    )

    assert score["format"] == 0.0
    assert score["format_structure_ok"] == 0.0
    assert score["format_json_ok"] == 0.0
    assert score["format_schema_ok"] == 0.0
    assert score["answer_reward"] == 1.0


def test_trace_reward_answer_mode_does_not_gate_correctness_on_format() -> None:
    reward_contract = _reward_contract("bbox_set_soft_iou_v0", "bbox_set")

    score = score_trace_response(
        response='The answer is {"answer":2}.',
        answer_gt={"type": "integer", "value": 2},
        annotation_gt={"type": "bbox_set", "value": [[0, 0, 10, 10]]},
        reward_contract=reward_contract,
        trace_reward_mode="answer",
        format_weight=0.1,
    )

    assert score["answer_reward"] == 1.0
    assert score["format"] == 0.0
    assert score["overall"] == 0.9
    assert score["zero_reward"] == 0.0


def test_trace_reward_recovers_legacy_answer_tag_without_format_credit() -> None:
    reward_contract = _reward_contract("bbox_set_soft_iou_v0", "bbox_set")

    score = score_trace_response(
        response='<answer>{"answer":2}</answer>',
        answer_gt={"type": "integer", "value": 2},
        annotation_gt={"type": "bbox_set", "value": [[0, 0, 10, 10]]},
        reward_contract=reward_contract,
        trace_reward_mode="answer",
        format_weight=0.1,
    )

    assert score["answer_reward"] == 1.0
    assert score["json_found"] == 1.0
    assert score["format"] == 0.0
    assert score["overall"] == 0.9


def test_trace_reward_zero_reward_tracks_task_correctness_not_format_bonus() -> None:
    reward_contract = _reward_contract("bbox_set_soft_iou_v0", "bbox_set")

    score = score_trace_response(
        response='{"answer":3}',
        answer_gt={"type": "integer", "value": 2},
        annotation_gt={"type": "bbox_set", "value": [[0, 0, 10, 10]]},
        reward_contract=reward_contract,
        trace_reward_mode="answer",
        format_weight=0.1,
    )

    assert score["answer_reward"] == 0.0
    assert score["format"] == 1.0
    assert score["overall"] == 0.1
    assert score["zero_reward"] == 1.0


def test_trace_reward_default_format_weight_is_zero() -> None:
    reward_contract = _reward_contract("bbox_set_soft_iou_v0", "bbox_set")

    score = score_trace_response(
        response='{"answer":3}',
        answer_gt={"type": "integer", "value": 2},
        annotation_gt={"type": "bbox_set", "value": [[0, 0, 10, 10]]},
        reward_contract=reward_contract,
        trace_reward_mode="answer",
    )

    assert score["answer_reward"] == 0.0
    assert score["format"] == 1.0
    assert score["format_weight"] == 0.0
    assert score["overall"] == 0.0


def test_trace_reward_answer_scoring_mode_can_use_legacy_strict_matching() -> None:
    reward_contract = _reward_contract("bbox_set_soft_iou_v0", "bbox_set", answer_type="string")

    current = score_trace_response(
        response='{"answer":"The answer is B."}',
        answer_gt={"type": "string", "value": "B"},
        annotation_gt={"type": "bbox_set", "value": [[0, 0, 10, 10]]},
        reward_contract=reward_contract,
        trace_reward_mode="answer",
        trace_answer_scoring="exact_json",
    )
    legacy = score_trace_response(
        response='{"answer":"The answer is B."}',
        answer_gt={"type": "string", "value": "B"},
        annotation_gt={"type": "bbox_set", "value": [[0, 0, 10, 10]]},
        reward_contract=reward_contract,
        trace_reward_mode="answer",
        trace_answer_scoring="legacy_strict",
    )

    assert current["answer_reward"] == 0.0
    assert current["trace_answer_scoring_exact_json"] == 1.0
    assert legacy["answer_reward"] == 1.0
    assert legacy["trace_answer_scoring_legacy_strict"] == 1.0


def test_trace_reward_exact_json_preserves_numeric_string_labels() -> None:
    reward_contract = _reward_contract("bbox_set_soft_iou_v0", "bbox_set", answer_type="string")

    correct = score_trace_response(
        response='{"answer":"4"}',
        answer_gt={"type": "string", "value": "4"},
        annotation_gt={"type": "bbox_set", "value": [[0, 0, 10, 10]]},
        reward_contract=reward_contract,
        trace_reward_mode="answer",
        trace_answer_scoring="exact_json",
    )
    numeric = score_trace_response(
        response='{"answer":4}',
        answer_gt={"type": "string", "value": "4"},
        annotation_gt={"type": "bbox_set", "value": [[0, 0, 10, 10]]},
        reward_contract=reward_contract,
        trace_reward_mode="answer",
        trace_answer_scoring="exact_json",
    )

    assert correct["answer_reward"] == 1.0
    assert numeric["answer_reward"] == 0.0


def test_trace_reward_legacy_index_list_is_order_sensitive() -> None:
    reward_contract = _reward_contract("bbox_set_soft_iou_v0", "bbox_set", answer_type="index_list")

    correct = score_trace_response(
        response='{"answer":[1,3,2,4]}',
        answer_gt={"type": "index_list", "value": [1, 3, 2, 4]},
        annotation_gt={"type": "bbox_set", "value": [[0, 0, 1, 1]]},
        reward_contract=reward_contract,
        trace_reward_mode="answer",
        trace_answer_scoring="legacy_strict",
    )
    permuted = score_trace_response(
        response='{"answer":[1,2,3,4]}',
        answer_gt={"type": "index_list", "value": [1, 3, 2, 4]},
        annotation_gt={"type": "bbox_set", "value": [[0, 0, 1, 1]]},
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
            "reward_contract": '{"answer":{"id":"answer_exact_match_v0"}}',
        }
    )
    assert normalized["answer_gt"]["value"] == 2
    assert normalized["reward_contract"]["answer"]["id"] == "answer_exact_match_v0"


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
    assert resolve_trace_prompt_key("auto", trace_output_mode="annotation") == "prompt_answer_and_annotation"
    assert resolve_trace_prompt_key("auto", trace_output_mode="answer_and_annotation") == "prompt_answer_and_annotation"
    assert resolve_trace_reward_mode("auto", trace_output_mode="answer") == "answer"
    assert resolve_trace_reward_mode("auto", trace_output_mode="annotation") == "answer_and_annotation"
    assert resolve_trace_reward_mode("auto", trace_output_mode="answer_and_annotation") == "answer_and_annotation"
    assert resolve_trace_reward_mode("answer_only", trace_output_mode="answer_and_annotation") == "answer"

    answer_prompt_path = default_trace_system_prompt_path(trace_output_mode="answer")
    annotation_alias_prompt_path = default_trace_system_prompt_path(trace_output_mode="annotation")
    annotation_prompt_path = default_trace_system_prompt_path(trace_output_mode="answer_and_annotation")
    assert answer_prompt_path.name == "trace_vero_json_system_prompt_answer.txt"
    assert annotation_alias_prompt_path == annotation_prompt_path
    assert annotation_prompt_path.name == "trace_vero_json_system_prompt_answer_and_annotation.txt"
    assert resolve_trace_system_prompt("auto", trace_output_mode="answer") == str(answer_prompt_path)
    assert resolve_trace_system_prompt("auto", trace_output_mode="annotation") == str(annotation_prompt_path)
    assert resolve_trace_system_prompt("auto", trace_output_mode="answer_and_annotation") == str(annotation_prompt_path)


def test_task_conditioned_mode_resolves_concrete_row_contracts() -> None:
    assert resolve_trace_prompt_key("auto", trace_output_mode="task_conditioned") == "auto"
    assert resolve_trace_system_prompt("auto", trace_output_mode="task_conditioned") == "auto"
    assert (
        resolve_trace_row_output_mode("task_conditioned", trace_supervision_mode="answer")
        == "answer"
    )
    assert (
        resolve_trace_row_output_mode(
            "task_conditioned",
            trace_supervision_mode="answer_and_annotation",
        )
        == "answer_and_annotation"
    )
    assert (
        resolve_trace_reward_mode(
            "auto",
            trace_output_mode="task_conditioned",
            trace_effective_output_mode="answer_and_annotation",
        )
        == "answer_and_annotation"
    )
    with pytest.raises(ValueError, match="trace_supervision_mode"):
        resolve_trace_row_output_mode("task_conditioned")
    with pytest.raises(ValueError, match="no single default system prompt"):
        default_trace_system_prompt_path(trace_output_mode="task_conditioned")


def test_task_conditioned_dataset_routes_prompt_and_system_prompt_per_row() -> None:
    dataset = TraceRLHFDataset.__new__(TraceRLHFDataset)
    dataset.trace_output_mode = TRACE_OUTPUT_MODE_TASK_CONDITIONED
    dataset.prompt_key = "auto"
    dataset.answer_key = "answer_gt"
    dataset.system_prompt = None
    dataset.system_prompts_by_output_mode = {
        "answer": "Answer system contract",
        "answer_and_annotation": "Annotation system contract",
    }
    dataset.format_prompt = None
    dataset.format_prompt_variant = "boxed_only"
    dataset.image_key = "images"
    dataset.video_key = "videos"

    answer_row = {
        "trace_supervision_mode": "answer",
        "prompt_answer": "Return only the answer payload.",
        "prompt_answer_and_annotation": "Return answer and annotation.",
        "answer_gt": {"type": "integer", "value": 2},
    }
    annotation_row = {
        **answer_row,
        "trace_supervision_mode": "answer_and_annotation",
    }

    assert dataset._resolve_prompt_answer_keys(answer_row)[0] == "prompt_answer"
    assert dataset._resolve_prompt_answer_keys(annotation_row)[0] == "prompt_answer_and_annotation"
    assert dataset._build_messages(answer_row)[0] == {
        "role": "system",
        "content": "Answer system contract",
    }
    assert dataset._build_messages(annotation_row)[0] == {
        "role": "system",
        "content": "Annotation system contract",
    }


def test_task_conditioned_reward_routes_each_item_in_mixed_batch() -> None:
    common_extra = {
        "answer_gt": {"type": "integer", "value": 2},
        "annotation_gt": {"type": "bbox", "value": [0, 0, 10, 10]},
        "reward_contract": _reward_contract("bbox_soft_iou_v0", "bbox"),
    }
    scores = compute_score(
        data_sources=["trace", "trace"],
        solution_strs=[
            'Reasoning.\n{"answer":2}',
            'Reasoning.\n{"answer":2,"annotation":[0,0,10,10]}',
        ],
        ground_truths=[2, 2],
        extra_infos=[
            {**common_extra, "trace_output_mode": "answer", "trace_supervision_mode": "answer"},
            {
                **common_extra,
                "trace_output_mode": "answer_and_annotation",
                "trace_supervision_mode": "answer_and_annotation",
            },
        ],
        trace_output_mode="task_conditioned",
        trace_reward_mode="auto",
    )

    assert [score["score"] for score in scores] == [1.0, 1.0]
    assert scores[0]["trace_reward_mode_answer"] == 1.0
    assert scores[0]["trace_reward_mode_answer_and_annotation"] == 0.0
    assert scores[1]["trace_reward_mode_answer"] == 0.0
    assert scores[1]["trace_reward_mode_answer_and_annotation"] == 1.0
    assert scores[1]["annotation_reward"] == 1.0


def test_task_conditioned_reward_metrics_are_split_by_effective_mode() -> None:
    metrics = reduce_numeric_reward_metrics(
        {
            "overall": [1.0, 0.0, 0.5, 1.0],
            "accuracy": [1.0, 0.0, 1.0, 1.0],
            "annotation_reward": [0.0, 0.0, 0.0, 1.0],
            "trace_reward_mode_answer": [1.0, 1.0, 0.0, 0.0],
            "trace_reward_mode_answer_and_annotation": [0.0, 0.0, 1.0, 1.0],
        }
    )

    assert metrics["reward/mode_count/answer"] == 2.0
    assert metrics["reward/mode_count/answer_and_annotation"] == 2.0
    assert metrics["reward/by_mode/answer/overall"] == 0.5
    assert metrics["reward/by_mode/answer_and_annotation/overall"] == 0.75
    assert metrics["reward/by_mode/answer_and_annotation/annotation_reward"] == 0.5


def test_reward_trace_wrapper_returns_score_key() -> None:
    result = compute_score(
        data_source="trace",
        solution_str='Reasoning.\n{"answer":2}',
        ground_truth=2,
        extra_info={
            "answer_gt": {"type": "integer", "value": 2},
            "annotation_gt": {"type": "bbox_set", "value": [[0, 0, 10, 10]]},
            "reward_contract": _reward_contract("bbox_set_soft_iou_v0", "bbox_set"),
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
            "annotation_gt": {"type": "bbox_set", "value": [[0, 0, 10, 10]]},
            "reward_contract": _reward_contract("bbox_set_soft_iou_v0", "bbox_set", answer_type="string"),
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
            "annotation_gt": {"type": "bbox_set", "value": [[0, 0, 10, 10]]},
            "reward_contract": _reward_contract("bbox_set_soft_iou_v0", "bbox_set"),
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
