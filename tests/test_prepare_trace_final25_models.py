from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts.prepare_trace_final25_models import (
    MARKER_NAME,
    PublicModel,
    download_public,
    register_local,
    verify,
)


class PrepareTraceFinal25ModelsTests(unittest.TestCase):
    def test_register_and_verify_local_model_content(self):
        with tempfile.TemporaryDirectory() as temporary:
            model = Path(temporary) / "model"
            model.mkdir()
            (model / "config.json").write_text('{"model_type":"test"}\n', encoding="utf-8")
            (model / "model.safetensors").write_bytes(b"synthetic-weights")
            (model / "chat_template.jinja").write_text("{{ messages }}\n", encoding="utf-8")
            (model / "tokenizer").mkdir()
            (model / "tokenizer" / "vocab.json").write_text("{}\n", encoding="utf-8")

            revision = register_local("trace-test", model, "synthetic-run")
            marker = json.loads((model / MARKER_NAME).read_text(encoding="utf-8"))

            self.assertEqual(marker["immutable_revision"], revision)
            self.assertTrue(revision.startswith("sha256set:"))
            self.assertEqual(
                set(marker["file_sha256"]),
                {
                    "chat_template.jinja",
                    "config.json",
                    "model.safetensors",
                    "tokenizer/vocab.json",
                },
            )
            verify([("trace-test", model, revision)], deep=True)

            (model / "special_tokens_map.json").write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "file set mismatch"):
                verify([("trace-test", model, revision)], deep=True)
            (model / "special_tokens_map.json").unlink()

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

    def test_public_download_records_and_deep_verifies_exact_snapshot(self):
        revision = "a" * 40
        public = PublicModel("public-test", "example/public-test", revision, "public-test")

        def fake_snapshot_download(**kwargs):
            target = Path(kwargs["local_dir"])
            target.mkdir(parents=True, exist_ok=True)
            (target / "config.json").write_text('{"model_type":"test"}\n', encoding="utf-8")
            (target / "model.safetensors").write_bytes(b"public-weights")
            (target / "tokenizer" ).mkdir()
            (target / "tokenizer" / "vocab.json").write_text("{}\n", encoding="utf-8")
            (target / ".cache" / "huggingface").mkdir(parents=True)
            (target / ".cache" / "huggingface" / "download.lock").write_text("ignored")
            return str(target)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with (
                patch("scripts.prepare_trace_final25_models.HfApi") as api_class,
                patch(
                    "scripts.prepare_trace_final25_models.snapshot_download",
                    side_effect=fake_snapshot_download,
                ),
            ):
                api_class.return_value.model_info.return_value = SimpleNamespace(
                    sha=revision,
                    siblings=[
                        SimpleNamespace(rfilename="config.json"),
                        SimpleNamespace(rfilename="model.safetensors"),
                        SimpleNamespace(rfilename="tokenizer/vocab.json"),
                    ],
                )
                download_public((public,), root, root / "missing-token.txt")

            model = root / "public-test"
            marker = json.loads((model / MARKER_NAME).read_text(encoding="utf-8"))
            self.assertEqual(marker["model_origin"], "public_download")
            self.assertEqual(marker["file_count"], 3)
            self.assertEqual(
                set(marker["file_sha256"]),
                {"config.json", "model.safetensors", "tokenizer/vocab.json"},
            )
            verify([("public-test", model, revision)], deep=True)

            (model / "model.safetensors").write_bytes(b"tampered")
            with self.assertRaisesRegex(RuntimeError, "content hash mismatch"):
                verify([("public-test", model, revision)], deep=True)
            (model / "model.safetensors").write_bytes(b"public-weights")

            (model / "unexpected.json").write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "file set mismatch"):
                verify([("public-test", model, revision)], deep=True)
            (model / "unexpected.json").unlink()

            (model / "tokenizer" / "vocab.json").unlink()
            with self.assertRaisesRegex(RuntimeError, "file set mismatch"):
                verify([("public-test", model, revision)], deep=True)

    def test_public_download_rejects_stale_preexisting_snapshot_file(self):
        revision = "a" * 40
        public = PublicModel("public-test", "example/public-test", revision, "public-test")

        def fake_snapshot_download(**kwargs):
            target = Path(kwargs["local_dir"])
            (target / "config.json").write_text("{}\n", encoding="utf-8")
            (target / "model.safetensors").write_bytes(b"weights")
            return str(target)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "public-test"
            target.mkdir()
            (target / "stale-chat-template.jinja").write_text("stale\n", encoding="utf-8")
            with (
                patch("scripts.prepare_trace_final25_models.HfApi") as api_class,
                patch(
                    "scripts.prepare_trace_final25_models.snapshot_download",
                    side_effect=fake_snapshot_download,
                ),
            ):
                api_class.return_value.model_info.return_value = SimpleNamespace(
                    sha=revision,
                    siblings=[
                        SimpleNamespace(rfilename="config.json"),
                        SimpleNamespace(rfilename="model.safetensors"),
                    ],
                )
                with self.assertRaisesRegex(RuntimeError, "stale=.*stale-chat-template"):
                    download_public((public,), root, root / "missing-token.txt")

            self.assertFalse((target / MARKER_NAME).exists())

    def test_deep_verify_rejects_legacy_public_marker_without_hashes(self):
        with tempfile.TemporaryDirectory() as temporary:
            model = Path(temporary) / "model"
            model.mkdir()
            (model / "config.json").write_text("{}\n", encoding="utf-8")
            (model / "model.safetensors").write_bytes(b"weights")
            revision = "b" * 40
            (model / MARKER_NAME).write_text(
                json.dumps(
                    {
                        "schema_version": "trace-model-revision-v1",
                        "slug": "public-test",
                        "source": "example/public-test",
                        "immutable_revision": revision,
                        "resolved_commit": revision,
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(RuntimeError, "requires immutable per-file hashes"):
                verify([("public-test", model, revision)], deep=True)


if __name__ == "__main__":
    unittest.main()
