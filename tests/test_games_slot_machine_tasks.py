"""Contract tests for games slot-machine tasks."""

from __future__ import annotations

from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks.games.slot_machine.winning_payline_count import GamesSlotMachineWinningPaylineCountTask


def test_games_slot_machine_winning_payline_count_contract() -> None:
    out = GamesSlotMachineWinningPaylineCountTask().generate(
        26062401,
        params={"target_winning_payline_count": 2},
        max_attempts=64,
    )
    execution = out.trace_payload["execution_trace"]
    winning_payline_ids = tuple(str(payline_id) for payline_id in execution["winning_payline_ids"])
    expected_segments = [
        out.trace_payload["render_map"]["payline_segments_px"][f"payline_{payline_id}"]
        for payline_id in winning_payline_ids
    ]

    assert out.scene_id == "slot_machine"
    assert out.query_id == "single"
    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == 2
    assert len(winning_payline_ids) == 2
    assert out.annotation_gt.type == "segment_set"
    assert out.annotation_gt.value == expected_segments
    assert out.trace_payload["projected_annotation"]["type"] == "segment_set"
    assert out.trace_payload["query_spec"]["params"]["target_winning_payline_count"] == 2
    assert execution["prompt_query_key"] == "winning_payline_count"


def test_games_slot_machine_winning_payline_count_support_and_taxonomy() -> None:
    task = GamesSlotMachineWinningPaylineCountTask()
    seen = set()
    for target in range(6):
        out = task.generate(
            26062410 + target,
            params={"target_winning_payline_count": target},
            max_attempts=64,
        )
        seen.add(int(out.answer_gt.value))
        assert int(out.answer_gt.value) == target
        assert len(out.annotation_gt.value) == target
        assert out.trace_payload["query_spec"]["params"]["winning_payline_count_support"] == [0, 1, 2, 3, 4, 5]

    taxonomy = resolve_task_taxonomy(
        "task_games__slot_machine__winning_payline_count",
        source_domain="games",
        source_scene_id="",
    )
    assert taxonomy.domain == "games"
    assert taxonomy.scene_id == "slot_machine"
    assert seen == {0, 1, 2, 3, 4, 5}
