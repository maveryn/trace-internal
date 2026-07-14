from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from scripts.update_trace_hf_task_supervision import MODE_COLUMN, augment_parquet


def test_augment_parquet_only_appends_supervision_mode(tmp_path: Path) -> None:
    source = tmp_path / "source.parquet"
    output = tmp_path / "output.parquet"
    table = pa.table(
        {
            "images": [[{"bytes": b"one", "path": None}], [{"bytes": b"two", "path": None}]],
            "task": ["task_a", "task_b"],
            "instance_id": ["instance_a", "instance_b"],
        }
    )
    pq.write_table(table, source, row_group_size=1)

    result = augment_parquet(
        source,
        output,
        {"task_a": "answer", "task_b": "answer_and_annotation"},
    )

    augmented = pq.read_table(output)
    assert augmented.schema.names == [*table.schema.names, MODE_COLUMN]
    assert augmented.select(table.schema.names).equals(table)
    assert augmented.column(MODE_COLUMN).to_pylist() == ["answer", "answer_and_annotation"]
    assert result["mode_counts"] == {"answer": 1, "answer_and_annotation": 1}
