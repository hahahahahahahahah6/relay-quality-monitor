import unittest
from relay_quality_monitor.ledger import append, read
from .helpers import Fixture
from pathlib import Path

SAMPLE = Path(__file__).resolve().parents[1] / "examples/sample-ledger.jsonl"

class LedgerTests(unittest.TestCase):
    def test_round_trip(self):
        rows = read(SAMPLE)
        with Fixture() as f:
            append(f.ledger, rows[:12])
            append(f.ledger, rows[12:])
            self.assertEqual(read(f.ledger), rows)
            self.assertEqual(len(f.ledger.read_text().splitlines()),36)
    def test_bad_ledgers(self):
        with Fixture() as f:
            with self.assertRaisesRegex(ValueError, "ledger"):
                read(f.ledger)
            for text in ("", "{", "{}", "[]", '{"round_id": "r", "probe_id": "unknown"}'):
                f.ledger.write_text(text)
                with self.subTest(text=text), self.assertRaisesRegex(ValueError,"ledger"):
                    read(f.ledger)

    def test_reject_invalid_field_types(self):
        import copy
        rows = read(SAMPLE)
        with Fixture() as f:
            for field, value in (("passed", 1), ("latency_ms", "slow"), ("prompt_tokens", -1), ("response", []), ("error", 3)):
                row = copy.deepcopy(rows[0])
                row["target"][field] = value
                append(f.ledger, [row])
                with self.subTest(field=field), self.assertRaises(ValueError):
                    read(f.ledger)
                f.ledger.unlink()
