"""Behavior tests for graph automaton string-acceptance relation task."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.core.seed import hash64
from trace.tasks import TASK_REGISTRY
from trace.tasks.graph.relation.automaton_string_acceptance_label import (
    GraphRelationAutomatonStringAcceptanceLabelTask,
)
from tests.helpers import read_jsonl


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def _accepting_paths(trace: dict, input_string: str) -> list[list[str]]:
    execution = trace["execution_trace"]
    transition_function = execution["transition_function"]
    accepting = set(str(label) for label in execution["accepting_state_labels"])
    paths = [[str(execution["start_state_label"])]]
    for symbol in str(input_string):
        next_paths: list[list[str]] = []
        for path in paths:
            for target in transition_function[str(path[-1])][str(symbol)]:
                next_paths.append([*path, str(target)])
        paths = list(next_paths)
    return [path for path in paths if str(path[-1]) in accepting]


def _assert_acceptance_contract(out) -> None:
    trace = out.trace_payload
    execution = trace["execution_trace"]
    candidates = dict(execution["candidate_strings_by_option"])
    accepted_options = [
        str(option_label)
        for option_label, input_string in candidates.items()
        if _accepting_paths(trace, str(input_string))
    ]
    answer_option = str(execution["answer_option_label"])
    answer_string = str(candidates[answer_option])

    assert "task_graph__automaton__accepted_string_label" in TASK_REGISTRY
    assert out.scene_id == "automaton"
    assert out.query_id == "default"
    assert out.answer_gt.type == "string"
    assert out.answer_gt.value in set(candidates)
    assert out.answer_gt.value == answer_option
    assert out.evidence_gt.type == "point_sequence"
    assert len(candidates) == 6
    assert accepted_options == [answer_option]
    assert execution["accepted_option_labels"] == [answer_option]
    assert execution["answer_input_string"] == answer_string
    assert _accepting_paths(trace, answer_string)[0] == execution["accepting_path_labels"]
    assert len(out.evidence_gt.value) == len(str(answer_string)) + 1
    assert len(trace["projected_evidence"]["point_sequence"]) == len(out.evidence_gt.value)
    width, height = out.image.size
    for point in out.evidence_gt.value:
        assert 0 <= int(point[0]) < width
        assert 0 <= int(point[1]) < height


def test_graph_relation_automaton_dfa_acceptance_contract_matches_trace() -> None:
    task = GraphRelationAutomatonStringAcceptanceLabelTask()
    out = task.generate(
        91301,
        params={
            "query_id": "dfa_accepted_string_label",
            "state_count": 5,
            "input_length_min": 4,
            "input_length_max": 4,
            "layout_variant": "shell",
            "edge_routing_variant": "mixed_arc",
        },
        max_attempts=100,
    )

    assert out.query_id == "dfa_accepted_string_label"
    assert out.trace_payload["execution_trace"]["automaton_kind"] == "dfa"
    assert "deterministic automaton" in out.prompt
    _assert_acceptance_contract(out)


def test_graph_relation_automaton_nfa_acceptance_contract_matches_trace() -> None:
    task = GraphRelationAutomatonStringAcceptanceLabelTask()
    out = task.generate(
        91302,
        params={
            "query_id": "nfa_accepted_string_label",
            "state_count": 6,
            "input_length_min": 3,
            "input_length_max": 5,
            "layout_variant": "layered",
        },
        max_attempts=100,
    )

    assert out.query_id == "nfa_accepted_string_label"
    assert out.trace_payload["execution_trace"]["automaton_kind"] == "nfa"
    assert "nondeterministic automaton" in out.prompt
    _assert_acceptance_contract(out)


def test_graph_relation_automaton_string_acceptance_prompt_examples_match_contract() -> None:
    task = GraphRelationAutomatonStringAcceptanceLabelTask()
    out = task.generate(
        91303,
        params={"query_id": "dfa_accepted_string_label", "state_count": 4, "input_length_min": 3, "input_length_max": 3},
        max_attempts=100,
    )

    answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
    answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert answer_only == {"answer": "C"}
    assert list(answer_and_evidence.keys()) == ["evidence", "answer"]
    assert answer_and_evidence["evidence"] == [[150, 250], [310, 190], [480, 230]]
    assert answer_and_evidence["answer"] == "C"
    assert "[x,y]" in out.prompt_variants["answer_and_evidence"]


def test_graph_relation_automaton_string_acceptance_balanced_sampling_covers_queries_and_options() -> None:
    task = GraphRelationAutomatonStringAcceptanceLabelTask()
    query_ids: Counter[str] = Counter()
    answer_options: Counter[str] = Counter()
    state_counts: Counter[int] = Counter()
    for index in range(90):
        out = task.generate(
            hash64(91310, "graph_relation_automaton_string_acceptance_label", index),
            params={},
            max_attempts=100,
        )
        execution = out.trace_payload["execution_trace"]
        query_ids[str(out.query_id)] += 1
        answer_options[str(out.answer_gt.value)] += 1
        state_counts[int(execution["state_count"])] += 1
        _assert_acceptance_contract(out)

    assert set(query_ids) == {"dfa_accepted_string_label", "nfa_accepted_string_label"}
    assert all(30 <= count <= 60 for count in query_ids.values())
    assert set(answer_options) == set("ABCDEF")
    assert set(state_counts) == {4, 5, 6}


def test_graph_relation_automaton_string_acceptance_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "graph_automaton_string_acceptance"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_graph_automaton_string_acceptance",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_graph__automaton__accepted_string_label",
                count=4,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=100,
        sampling_seed=41,
    )
    final_path = build_dataset(config, code_hash="graph-relation-automaton-string-acceptance-smoke")
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 4
    assert all(record["domain"] == "graph" for record in train_records)
    assert all(record["task_group"] == "relation" for record in train_records)
    assert all(record["scene_id"] == "automaton" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"]["task_graph__automaton__accepted_string_label"]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
