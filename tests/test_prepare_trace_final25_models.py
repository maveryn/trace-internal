from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.prepare_trace_final25_models import MARKER_NAME, register_local, verify


class PrepareTraceFinal25ModelsTests(unittest.TestCase):
    def test_register_and_verify_local_model_content(self):
        with tempfile.TemporaryDirectory() as temporary:
            model = Path(temporary) / "model"
            model.mkdir()
            (model / "config.json").write_text('{"model_type":"test"}\n', encoding="utf-8")
            (model / "model.safetensors").write_bytes(b"synthetic-weights")

            revision = register_local("trace-test", model, "synthetic-run")
            marker = json.loads((model / MARKER_NAME).read_text(encoding="utf-8"))

            self.assertEqual(marker["immutable_revision"], revision)
            self.assertTrue(revision.startswith("sha256set:"))
            verify([("trace-test", model, revision)], deep=True)

            (model / "model.safetensors").write_bytes(b"tampered")
            with self.assertRaisesRegex(RuntimeError, "content hash mismatch"):
                verify([("trace-test", model, revision)], deep=True)

    def test_verify_rejects_revision_mismatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            model = Path(temporary) / "model"
            model.mkdir()
            (model / "config.json").write_text("{}\n", encoding="utf-8")
            (model / "model.safetensors").write_bytes(b"weights")
            register_local("trace-test", model, "synthetic-run")

            with self.assertRaisesRegex(RuntimeError, "model revision mismatch"):
                verify([("trace-test", model, "wrong")], deep=False)


if __name__ == "__main__":
    unittest.main()
