from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_ROOT = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from run_trace_final26_official_score_campaign import Workbook, _stage_workbooks  # noqa: E402


class TraceFinal26ScoreCampaignTests(unittest.TestCase):
    def test_resume_restores_mutated_staged_workbook_from_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.xlsx"
            staged = root / "staged.xlsx"
            source.write_bytes(b"contract-verified source")
            staged.write_bytes(b"scorer-enriched staging copy")
            workbook = Workbook(
                benchmark_key="screenspot",
                alias="ScreenSpot",
                run_name="run",
                source=source,
                staged=staged,
                sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                primary=True,
            )

            _stage_workbooks({"model": [workbook]}, resume=True)

            self.assertEqual(staged.read_bytes(), source.read_bytes())


if __name__ == "__main__":
    unittest.main()
