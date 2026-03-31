from __future__ import annotations

from pathlib import Path
import sys
import types

from PIL import Image

if "codetiming" not in sys.modules:
    sys.modules["codetiming"] = types.SimpleNamespace(Timer=object)
if "qwen_vl_utils" not in sys.modules:
    vision_process = types.SimpleNamespace(fetch_video=lambda *args, **kwargs: [])
    sys.modules["qwen_vl_utils"] = types.SimpleNamespace(vision_process=vision_process)
    sys.modules["qwen_vl_utils.vision_process"] = vision_process
if "mathruler" not in sys.modules:
    grader = types.SimpleNamespace(
        extract_boxed_content=lambda text: text,
        grade_answer=lambda pred, gt: str(pred).strip() == str(gt).strip(),
    )
    sys.modules["mathruler"] = types.SimpleNamespace(grader=grader)
    sys.modules["mathruler.grader"] = grader
if "datasets" not in sys.modules:
    sys.modules["datasets"] = types.SimpleNamespace(load_dataset=lambda *args, **kwargs: None)
if "transformers" not in sys.modules:
    sys.modules["transformers"] = types.SimpleNamespace(
        PreTrainedTokenizer=object,
        ProcessorMixin=object,
    )

from verl.utils.dataset import RLHFDataset, process_image
from verl.utils.trace_reward import score_trace_response
from examples.reward_function.reward_tesserae import compute_score


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
            _reward_contract("bbox_set_iou_v1", "bbox_set"),
        ),
        (
            {"answer": 5, "evidence": [2, 4, 6]},
            {"type": "integer", "value": 5},
            {"type": "integer_list", "value": [2, 4, 6]},
            _reward_contract("numeric_exact_v1", "integer_list"),
        ),
        (
            {"answer": 2, "evidence": [["B", "D"], ["D", "G"]]},
            {"type": "integer", "value": 2},
            {"type": "edge_set", "value": [["D", "B"], ["G", "D"]]},
            _reward_contract("symbolic_set_exact_v1", "edge_set"),
        ),
        (
            {"answer": 2, "evidence": [[1, 1], [1, 2], [1, 3]]},
            {"type": "integer", "value": 2},
            {"type": "grid_point_path", "value": [[1, 1], [1, 2], [1, 3]]},
            _reward_contract("sequence_exact_v1", "grid_point_path"),
        ),
        (
            {"answer": 4, "evidence": [[0, 0], [4, 0], [0, 3]]},
            {"type": "integer", "value": 4},
            {"type": "graph_point_set", "value": [[0, 3], [0, 0], [4, 0]]},
            _reward_contract("point_set_match_v1", "graph_point_set"),
        ),
    ]

    for payload, answer_gt, evidence_gt, reward_contract in cases:
        response = str(payload).replace("'", '"')
        score = score_trace_response(
            response=response,
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            reward_contract=reward_contract,
        )
        assert score["overall"] == 1.0
        assert score["answer_reward"] == 1.0
        assert score["evidence_reward"] == 1.0


def test_trace_reward_gates_evidence_by_answer_correctness() -> None:
    reward_contract = _reward_contract("symbolic_set_exact_v1", "label_set")

    wrong_answer_score = score_trace_response(
        response='{"answer":1,"evidence":["B","D"]}',
        answer_gt={"type": "integer", "value": 2},
        evidence_gt={"type": "label_set", "value": ["D", "B"]},
        reward_contract=reward_contract,
    )
    assert wrong_answer_score["answer_reward"] == 0.0
    assert wrong_answer_score["evidence_reward"] == 1.0
    assert wrong_answer_score["accuracy"] == 0.0
    assert wrong_answer_score["overall"] == 0.0

    wrong_evidence_score = score_trace_response(
        response='{"answer":2,"evidence":["B"]}',
        answer_gt={"type": "integer", "value": 2},
        evidence_gt={"type": "label_set", "value": ["D", "B"]},
        reward_contract=reward_contract,
    )
    assert wrong_evidence_score["answer_reward"] == 1.0
    assert wrong_evidence_score["evidence_reward"] == 0.0
    assert wrong_evidence_score["accuracy"] == 1.0
    assert wrong_evidence_score["overall"] == 0.5


def test_trace_dataset_helpers_support_trace_rows(tmp_path: Path) -> None:
    image_path = tmp_path / "images" / "sample.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (12, 12), (255, 255, 255)).save(image_path)

    dataset = RLHFDataset.__new__(RLHFDataset)
    dataset.prism_mode = "trace"
    dataset.prompt_key = "prompt"
    dataset.answer_key = "answer"
    dataset.image_dir = None
    dataset.dataset_root = tmp_path

    prompt_key, answer_key = dataset._resolve_prompt_answer_keys(
        {"prompt": "Solve it", "answer_gt": {"type": "integer", "value": 4}}
    )
    assert (prompt_key, answer_key) == ("prompt", "answer_gt")

    normalized_images = dataset._normalize_image_entries([{"path": "images/sample.png"}])
    assert normalized_images == [str(image_path)]

    normalized_example = dataset._normalize_trace_metadata_fields(
        {
            "prompt": "Solve it",
            "answer_gt": '{"type":"integer","value":4}',
            "evidence_gt": '{"type":"bbox_set","value":[[1,2,3,4]]}',
            "reward_contract": (
                '{"reward_contract_version":"v1","answer":{"id":"answer_exact_match_v1","type":"integer"},'
                '"evidence":{"id":"bbox_set_iou_v1","type":"bbox_set"}}'
            ),
            "trace_ref": '{"shard_id":"trace-0001","line_index":0,"trace_record_hash":"hash"}',
        }
    )
    assert normalized_example["answer_gt"] == {"type": "integer", "value": 4}
    assert normalized_example["evidence_gt"] == {"type": "bbox_set", "value": [[1, 2, 3, 4]]}
    assert normalized_example["reward_contract"]["evidence"]["type"] == "bbox_set"
    assert normalized_example["trace_ref"]["shard_id"] == "trace-0001"

    loaded = process_image({"path": str(image_path)}, min_pixels=None, max_pixels=None)
    assert loaded.size == (12, 12)


def test_reward_tesserae_dispatches_trace_reward_contract() -> None:
    scores = compute_score(
        [
            {
                "prompt": "Return JSON.",
                "response": '{"answer":2,"evidence":["B","D"]}',
                "ground_truth": 2,
                "answer_gt": {"type": "integer", "value": 2},
                "evidence_gt": {"type": "label_set", "value": ["D", "B"]},
                "reward_contract": _reward_contract("symbolic_set_exact_v1", "label_set"),
            }
        ]
    )
    assert len(scores) == 1
    assert scores[0]["overall"] == 1.0
    assert scores[0]["trace_reward"] == 1.0
    assert scores[0]["answer_reward"] == 1.0
    assert scores[0]["evidence_reward"] == 1.0
