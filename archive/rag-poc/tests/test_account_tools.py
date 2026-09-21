"""Verify the account tool's lookup contract and isolation between calls."""

import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("poc_test_account_tools", ROOT / "tools/account_tools.py")
account_tools = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = account_tools
spec.loader.exec_module(account_tools)
get_account_status = account_tools.get_account_status


class AccountToolTests(unittest.TestCase):
    def test_known_account_via_adk_wrapper(self):
        result = get_account_status(account_id="ACC-0002").content
        self.assertTrue(result["found"])
        self.assertIsNone(result["error"])
        self.assertEqual(result["source"], "synthetic_account_fixture_v1")
        self.assertEqual(result["as_of"], "2026-09-16T00:00:00Z")
        self.assertEqual(result["account"], {
            "account_id": "ACC-0002", "status": "active", "plan": "growth",
            "billing_frequency": "monthly", "next_billing_date": "2026-10-15",
        })
        json.dumps(result)

    def test_unknown_account_returns_no_other_records(self):
        result = get_account_status(account_id="ACC-9999").content
        self.assertFalse(result["found"])
        self.assertEqual(result["error"], "ACCOUNT_NOT_FOUND")
        self.assertIsNone(result["account"])
        self.assertNotIn("ACC-0001", json.dumps(result))

    def test_malformed_ids_are_not_coerced_or_guessed(self):
        for value in (None, 1, "", "acc-0001", "ACC-001", " ACC-0001", "ACC-0001\n",
                      "ACC-０００１", "ACC-0001,ACC-0002", "ACC-0001' OR 1=1"):
            with self.subTest(value=value):
                result = get_account_status(account_id=value).content
                self.assertEqual(result["error"], "INVALID_ACCOUNT_ID")
                self.assertFalse(result["found"])
                self.assertIsNone(result["account"])

    def test_pending_account_has_no_invented_billing_date(self):
        result = get_account_status(account_id="ACC-0004").content
        self.assertEqual(result["account"]["status"], "pending_activation")
        self.assertIsNone(result["account"]["next_billing_date"])

    def test_calls_are_repeatable_and_do_not_leak_mutations(self):
        original = get_account_status(account_id="ACC-0001").content
        changed = get_account_status(account_id="ACC-0001").content
        changed["account"]["plan"] = "tampered"
        changed["as_of"] = "tomorrow"
        self.assertEqual(get_account_status(account_id="ACC-0001").content, original)

    def test_tool_schema_is_read_only_with_one_required_argument(self):
        schema = get_account_status.__tool_spec__.model_dump(mode="json")
        self.assertEqual(schema["permission"], "read_only")
        self.assertEqual(schema["input_schema"]["required"], ["account_id"])
        self.assertEqual(schema["input_schema"]["properties"]["account_id"]["type"], "string")
        self.assertEqual(schema["binding"]["python"]["requirements"], [])


if __name__ == "__main__":
    unittest.main()
