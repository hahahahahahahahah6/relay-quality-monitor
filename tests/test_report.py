import unittest
from relay_quality_monitor.report import aggregate
from relay_quality_monitor.ledger import read
from .test_ledger import SAMPLE

class ReportTests(unittest.TestCase):
    def test_sample_statistics(self):
        r = aggregate(read(SAMPLE))
        self.assertEqual(r["rounds_covered"],3)
        self.assertAlmostEqual(r["mean_capability_gap"],4/11)
        self.assertEqual(r["rounds"][0]["target"],7/11)
        self.assertEqual(r["rounds"][0]["baseline"],1)
        self.assertIsNone(r["per_probe_pass_rates"]["identity"]["target"])
        self.assertEqual(r["per_probe_pass_rates"]["arith-1"]["target"],0)
        self.assertEqual(r["mean_latency_ratio"]["arith-1"],2)
        self.assertEqual(r["token_totals"]["target"],dict(prompt_tokens=720,completion_tokens=180))
        self.assertEqual(r["error_counts"],dict(target=0,baseline=0))
        self.assertNotIn("cost_totals",r)
        self.assertEqual(len(r["identity_answers"]),3)
        self.assertIn("unreliable", r["identity_warning"])
    def test_window_and_cost(self):
        rows = read(SAMPLE)
        for row in rows:
            row["cost_usd"] = dict(target=.2, baseline=.1)
        r = aggregate(rows,1)
        self.assertEqual(r["rounds_covered"],1)
        self.assertAlmostEqual(r["cost_totals"]["target"],2.4)
        self.assertEqual(r["rounds"][0]["round_id"],"synthetic-3")
    def test_missing_usage_not_estimated(self):
        rows=read(SAMPLE)[:12]
        for row in rows:
            for side in ("target","baseline"):
                row[side]["prompt_tokens"] = row[side]["completion_tokens"] = None
        r=aggregate(rows)
        self.assertEqual(r["token_totals"]["target"]["prompt_tokens"],0)
        self.assertEqual(r["missing_usage_counts"]["target"],12)
