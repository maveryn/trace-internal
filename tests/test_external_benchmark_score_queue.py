from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS_ROOT = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from benchmark_queue_lib import BenchmarkSpec  # noqa: E402
from run_external_benchmark_score_queue import _preferred_direct_score  # noqa: E402


class ExternalBenchmarkScoreQueueTests(unittest.TestCase):
    def test_videommmu_uses_accuracy_row_instead_of_averaging_counts(self):
        spec = BenchmarkSpec("videommmu", "VideoMMMU", "VideoMMMU_8frame", "video")
        summary = {
            "score": 453.7037037037037,
            "scores": {
                "table": [
                    {"Adaptation": 300.0, "Comprehension": 300.0, "Perception": 300.0, "Overall": 900.0},
                    {"Adaptation": 110.0, "Comprehension": 128.0, "Perception": 177.0, "Overall": 415.0},
                    {
                        "Adaptation": 36.6666666667,
                        "Comprehension": 42.6666666667,
                        "Perception": 59.0,
                        "Overall": 46.1111111111,
                    },
                ]
            },
        }

        self.assertAlmostEqual(_preferred_direct_score(spec, summary), 46.1111111111)

    def test_other_benchmarks_keep_generic_primary_score(self):
        spec = BenchmarkSpec("demo", "Demo", "Demo", "demo")
        self.assertIsNone(_preferred_direct_score(spec, {"score": 50.0}))

    def test_qbench_video_uses_row_weighted_accuracy_not_raw_counts(self):
        spec = BenchmarkSpec("qbench_video", "QBench-Video", "QBench_Video_8frame", "video")
        summary = {
            "scores": {
                "table": [
                    {"success": 134, "overall": 328, "acc": 40.9},
                    {"success": 161, "overall": 294, "acc": 54.8},
                    {"success": 153, "overall": 270, "acc": 28.35},
                ]
            }
        }
        expected = (40.9 * 328 + 54.8 * 294 + 28.35 * 270) / 892
        self.assertAlmostEqual(_preferred_direct_score(spec, summary), expected)

    def test_video_tt_uses_nested_overall_score(self):
        spec = BenchmarkSpec("video_tt", "Video-TT", "Video_TT_16frame", "video")
        summary = {"scores": {"overall": {"number": 1000, "correct": 384, "score": 38.4}}}
        self.assertEqual(_preferred_direct_score(spec, summary), 38.4)


if __name__ == "__main__":
    unittest.main()
