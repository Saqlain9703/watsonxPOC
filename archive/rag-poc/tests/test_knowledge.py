"""Verify source fidelity and that incomplete/stale ingestion blocks agent import."""

from contextlib import redirect_stdout
import hashlib
from io import StringIO
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import Mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from knowledge_assets import assert_knowledge_ready, build_knowledge, load_knowledge


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "output"
        with redirect_stdout(StringIO()):
            self.files = build_knowledge(output=self.output)

    def ready_client(self):
        client = Mock()
        client.get_by_names.side_effect = lambda names: [{"id": names[0], "name": names[0]}]
        by_name = {p.stem: yaml.safe_load(p.read_text()) for p in self.files}
        client.status.side_effect = lambda name: {
            "built_in_index_status": "ready", "ready": True,
            "documents": [{"metadata": {"original_file_name": Path(p).name}}
                          for p in by_name[name]["documents"]],
        }
        return client

    def test_uploads_preserve_source_bytes_and_valid_relative_paths(self):
        manifest = json.loads((self.output / "manifest.json").read_text())
        self.assertEqual(len(manifest["knowledge_bases"]), 2)
        for kb in manifest["knowledge_bases"].values():
            self.assertEqual(len(kb), 6)
            for item in kb:
                source = ROOT / "knowledge" / item["source"]
                upload = self.output / item["upload"]
                self.assertEqual(upload.suffix, ".txt")
                self.assertEqual(upload.read_bytes(), source.read_bytes())
                self.assertEqual(item["sha256"], hashlib.sha256(source.read_bytes()).hexdigest())

    def test_build_is_repeatable(self):
        before = {p.relative_to(self.output): p.read_bytes() for p in self.output.rglob("*") if p.is_file()}
        with redirect_stdout(StringIO()):
            build_knowledge(output=self.output)
        after = {p.relative_to(self.output): p.read_bytes() for p in self.output.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_source_change_changes_upload_name(self):
        source_dir = Path(self.temp.name) / "knowledge"
        shutil.copytree(ROOT / "knowledge", source_dir)
        old = json.loads((self.output / "manifest.json").read_text())
        source = source_dir / "docs/account_billing/ab_001_account_setup.md"
        source.write_text(source.read_text() + "\nAdditional synthetic test content.\n")
        with redirect_stdout(StringIO()):
            build_knowledge(directory=source_dir, output=self.output)
        new = json.loads((self.output / "manifest.json").read_text())
        self.assertNotEqual(old["knowledge_bases"]["account_billing_kb"][0]["upload"],
                            new["knowledge_bases"]["account_billing_kb"][0]["upload"])

    def test_source_outside_domain_is_rejected(self):
        source_dir = Path(self.temp.name) / "knowledge"
        shutil.copytree(ROOT / "knowledge", source_dir)
        path = source_dir / "account_billing_kb.yaml"
        data = yaml.safe_load(path.read_text())
        data["documents"][0] = "../README.md"
        path.write_text(yaml.safe_dump(data))
        with self.assertRaisesRegex(ValueError, "source must"):
            load_knowledge(source_dir)

    def test_ready_and_current_indexes_pass(self):
        with redirect_stdout(StringIO()):
            assert_knowledge_ready(self.ready_client(), self.files)

    def test_pending_failed_or_unknown_index_stops(self):
        for state in ("in_progress", "not_ready", "error", "unknown"):
            client = self.ready_client()
            client.status.side_effect = None
            client.status.return_value = {"built_in_index_status": state}
            with self.subTest(state=state), self.assertRaisesRegex(RuntimeError, "ingestion state"):
                assert_knowledge_ready(client, self.files)

    def test_ready_index_with_stale_documents_stops(self):
        client = self.ready_client()
        client.status.side_effect = None
        client.status.return_value = {
            "built_in_index_status": "ready",
            "documents": [{"metadata": {"original_file_name": "old-content.txt"}}],
        }
        with self.assertRaisesRegex(RuntimeError, "do not match"):
            assert_knowledge_ready(client, self.files)

    def test_ambiguous_kb_name_stops(self):
        client = self.ready_client()
        client.get_by_names.side_effect = None
        client.get_by_names.return_value = [{"id": "one"}, {"id": "two"}]
        with self.assertRaisesRegex(RuntimeError, "exactly one"):
            assert_knowledge_ready(client, self.files)


if __name__ == "__main__":
    unittest.main()
