import unittest
from relay_quality_monitor.probes import PROBES, check, normalize

class ProbesTests(unittest.TestCase):
    def test_exact_set_and_prompts(self):
        self.assertEqual([p[0] for p in PROBES], ["arith-1", "arith-2", "capital-1", "capital-2", "exact-word", "primes", "translate", "reverse", "count-letters", "logic-1", "contains-words", "identity"])
        self.assertEqual(len(PROBES), 12)
        self.assertEqual(sum(p[2] != "none" for p in PROBES), 11)
        for probe in PROBES:
            self.assertIs(check(probe, "  " + probe[3].upper() + "\n"), None if probe[2] == "none" else True)
    def test_normalization(self):
        self.assertEqual(normalize("  A\n B "), "a b")
        self.assertTrue(check(PROBES[5], " 11, 7  5,3,2 "))
        self.assertFalse(check(PROBES[5], "2,3,5,7,11,13"))
        self.assertFalse(check(PROBES[0], "248171."))
        self.assertTrue(check(PROBES[6], "Bonjour à vous"))
        self.assertTrue(check(PROBES[10], "The MOON shines over a river bridge."))
    def test_identity_never_scored(self):
        self.assertIsNone(check(PROBES[-1], "anything"))
