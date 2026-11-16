import unittest
from relay_quality_monitor.report import check, aggregate
from relay_quality_monitor.ledger import read
from .test_ledger import SAMPLE

class CheckTests(unittest.TestCase):
    def test_pinned_thresholds_and_windows(self):
        rows=read(SAMPLE)
        self.assertEqual(check(aggregate(rows)),2)
        self.assertEqual(check(aggregate(rows,2)),1)
        self.assertEqual(check(aggregate(rows,1)),0)
        self.assertEqual(check(aggregate(rows),4/11,3),2)
    def test_errors_skip_without_breaking(self):
        rounds=[dict(gap=.3,eligible=True),dict(gap=-1,eligible=False),dict(gap=.3,eligible=True),dict(gap=.3,eligible=True)]
        self.assertEqual(check(dict(rounds=rounds)),2)
        self.assertEqual(check(dict(rounds=[dict(gap=1,eligible=False)]*9)),0)
    def test_low_gap_breaks(self):
        rounds=[dict(gap=.3,eligible=True),dict(gap=0,eligible=True),dict(gap=.3,eligible=True)]
        self.assertEqual(check(dict(rounds=rounds)),0)
    def test_no_paired_answers_is_ineligible(self):
        rows=read(SAMPLE)[:12]
        for i,row in enumerate(rows):
            row["target" if i%2 else "baseline"]["error"]="failed"
        self.assertFalse(aggregate(rows)["rounds"][0]["eligible"])
