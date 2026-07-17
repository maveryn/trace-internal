from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS_ROOT = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from screenspot_json_contract import parse_screenspot_json_point  # noqa: E402


def test_python_max_integer_digits_is_an_unresolved_screenspot_response() -> None:
    response = (
        "Here is the JSON array format:\n```json\n"
        '[{"point_2d": [1234, '
        + "9" * 13_053
    )

    parsed = parse_screenspot_json_point(response)

    assert parsed.status == "invalid"
    assert parsed.value is None
    assert parsed.method == "missing_json_point_2d"
    assert parsed.candidates == ()


def test_normal_malformed_and_conflicting_screenspot_results_are_unchanged() -> None:
    resolved = parse_screenspot_json_point('[{"point_2d": [12, 34]}]')
    malformed = parse_screenspot_json_point('{"point_2d": [12, 34]}')
    conflicting = parse_screenspot_json_point(
        '[{"point_2d": [12, 34]}]\n[{"point_2d": [56, 78]}]'
    )

    assert (resolved.status, resolved.value, resolved.method) == (
        "resolved",
        (12.0, 34.0),
        "json_point_2d",
    )
    assert (malformed.status, malformed.value, malformed.method) == (
        "invalid",
        None,
        "malformed_json_point_2d",
    )
    assert (conflicting.status, conflicting.value, conflicting.method) == (
        "ambiguous",
        None,
        "conflicting_json_point_2d",
    )
    assert conflicting.candidates == ((12.0, 34.0), (56.0, 78.0))
