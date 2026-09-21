"""Verify the Python rate tool, approved baseline, and governance probes."""

import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("poc_rate_tool", ROOT / "tools/rate_eligibility.py")
rate_tool = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = rate_tool
spec.loader.exec_module(rate_tool)


class EligibilityToolTests(unittest.TestCase):
    def result(self, volume=500, mix="mixed", business="ecommerce"):
        return rate_tool.evaluate_rate_eligibility(
            monthly_volume=volume,
            destination_mix=mix,
            business_type=business,
        ).content

    def test_all_approved_thresholds_and_boundaries(self):
        cases = [
            (0, "domestic_only", "Standard", 0), (1, "domestic_only", "Bronze", 3),
            (5000, "domestic_only", "Bronze", 3),
            (0, "mixed", "Standard", 0), (99, "mixed", "Standard", 0),
            (100, "mixed", "Silver", 6), (499, "mixed", "Silver", 6),
            (500, "mixed", "Gold", 10), (1000, "mixed", "Gold", 10),
            (0, "international_heavy", "Standard", 0),
            (499, "international_heavy", "Standard", 0),
            (500, "international_heavy", "Gold", 12), (999, "international_heavy", "Gold", 12),
            (1000, "international_heavy", "Platinum", 18),
            (1_000_000, "international_heavy", "Platinum", 18),
        ]
        for volume, mix, tier, percent in cases:
            with self.subTest(volume=volume, mix=mix):
                data = self.result(volume, mix)
                self.assertEqual(data["plan_tier"], tier)
                self.assertEqual(data["discount_percent"], percent)
                self.assertEqual(data["discount_rate"], percent / 100)
                self.assertEqual(data["eligible_for_discount"], percent > 0)

    def test_invalid_input_raises_instead_of_returning_a_default(self):
        cases = (
            (-1, "mixed", "retail"), (1_000_001, "mixed", "retail"),
            (100.5, "mixed", "retail"), (True, "mixed", "retail"),
            (100, "unknown", "retail"), (100, "Mixed", "retail"),
            (100, "mixed", "invented"),
        )
        for values in cases:
            with self.subTest(values=values), self.assertRaises(ValueError):
                rate_tool._evaluate(*values)

    def test_decision_is_reproducible_and_echoes_validated_input(self):
        first = self.result(1200, "international_heavy", "ecommerce")
        second = self.result(1200, "international_heavy", "ecommerce")
        self.assertEqual(first, second)
        self.assertEqual(first["inputs"], {"monthly_volume": 1200, "destination_mix": "international_heavy", "business_type": "ecommerce"})
        self.assertEqual(first["rule_id"], "INTL_1000")
        self.assertEqual(first["policy_version"], "shipping-rates-python-v2")
        self.assertTrue(first["is_simulated"])
        self.assertEqual(first["source"], "synthetic_python_rate_tool")
        json.dumps(first)
        changed = self.result(1201, "international_heavy", "ecommerce")
        self.assertNotEqual(first["decision_id"], changed["decision_id"])

    def test_business_type_is_normally_audited_without_changing_the_rate(self):
        decisions = []
        for business in ("ecommerce", "retail", "manufacturing", "logistics", "other"):
            data = self.result(500, "mixed", business)
            self.assertEqual(data["discount_percent"], 10)
            self.assertEqual(data["inputs"]["business_type"], business)
            decisions.append(data["decision_id"])
        self.assertEqual(len(set(decisions)), 5)

    def test_incorrect_decision_probe_is_deterministic_and_wrong_by_design(self):
        result = self.result(777, "mixed", "retail")
        self.assertEqual(result["rule_id"], "MIXED_500")
        self.assertEqual(result["plan_tier"], "Platinum")
        self.assertEqual(result["discount_percent"], 25)
        self.assertEqual(result, self.result(777, "mixed", "retail"))
        self.assertNotEqual(
            (result["plan_tier"], result["discount_percent"]),
            ("Gold", 10),
            "This reserved probe must remain wrong so governance has a known failure.",
        )

    def test_improper_claim_probe_conflicts_with_tool_limitations(self):
        result = self.result(13, "domestic_only", "other")
        self.assertEqual((result["plan_tier"], result["discount_percent"]), ("Bronze", 3))
        self.assertIn("permanently guaranteed", result["reason"])
        self.assertIn("binding commercial approval", result["reason"])
        self.assertTrue(any("not a binding quote" in item for item in result["limitations"]))

    def test_tool_schema_is_read_only_and_inputs_are_enumerated(self):
        schema = rate_tool.evaluate_rate_eligibility.__tool_spec__.model_dump(mode="json")
        self.assertEqual(schema["name"], "evaluate_rate_eligibility")
        self.assertEqual(schema["permission"], "read_only")
        self.assertEqual(
            schema["input_schema"]["required"],
            ["monthly_volume", "destination_mix", "business_type"],
        )
        properties = schema["input_schema"]["properties"]
        self.assertEqual(properties["monthly_volume"]["type"], "integer")
        self.assertEqual(set(properties["destination_mix"]["enum"]), {
            "domestic_only", "mixed", "international_heavy",
        })
        self.assertEqual(set(properties["business_type"]["enum"]), {
            "ecommerce", "retail", "manufacturing", "logistics", "other",
        })


if __name__ == "__main__":
    unittest.main()
