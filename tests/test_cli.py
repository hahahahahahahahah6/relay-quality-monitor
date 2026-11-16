import json
import unittest
from pathlib import Path
from unittest.mock import patch
from relay_quality_monitor import client
from relay_quality_monitor.probes import PROBES
from .helpers import Fixture, LocalServer, configuration, run
from .test_ledger import SAMPLE

class CliTests(unittest.TestCase):
    def test_end_to_end_identical_requests(self):
        with LocalServer() as server, Fixture() as f:
            f.write(configuration(server.url))
            self.assertEqual(f.probe()[0],0)
            rows=[json.loads(line) for line in f.ledger.read_text().splitlines()]
            self.assertEqual(len(rows),12)
            self.assertEqual(len(server.requests),24)
            for i in range(12):
                left,right=server.requests[2*i:2*i+2]
                self.assertEqual(left[0],"/v1/chat/completions")
                self.assertEqual(left[1],right[1])
                self.assertEqual(left[1],dict(model="test-model",messages=[dict(role="user",content=PROBES[i][1])],temperature=0,max_tokens=64))
                self.assertEqual(rows[i]["target"]["prompt_tokens"],9)
                self.assertIs(rows[i]["target"]["passed"], None if i==11 else True)
                self.assertNotIn("test-key", json.dumps(rows[i]))
            code,out,err=run("report","--ledger",str(f.ledger),"--json")
            self.assertEqual(code,0,err)
            report=json.loads(out)
            self.assertEqual(report["rounds"][0]["target"],1)
            self.assertEqual(report["identity_answers"][0]["target"],"I am a synthetic model.\nVerbatim.")
            self.assertEqual(run("check","--ledger",str(f.ledger))[0],0)
            self.assertEqual(f.probe("round-2")[0],0)
            self.assertEqual(len(f.ledger.read_text().splitlines()),24)
    def test_request_failures_are_data(self):
        with LocalServer() as server, Fixture() as f:
            f.write(configuration(server.url))
            for mode in ("http","malformed"):
                server.mode=mode
                self.assertEqual(f.probe(mode)[0],0)
            rows=[json.loads(line) for line in f.ledger.read_text().splitlines()]
            self.assertEqual(len(rows),24)
            for row in rows:
                self.assertFalse(row["target"]["passed"])
                self.assertIsNotNone(row["target"]["error"])
            self.assertEqual(run("check","--ledger",str(f.ledger))[0],0)
    def test_timeout_and_same_timeout_parameter(self):
        cfg=configuration("http://127.0.0.1:1/v1")
        cfg.update(timeout_s=.01,max_tokens=64,temperature=0)
        with Fixture(), patch("relay_quality_monitor.client.urllib.request.urlopen",side_effect=TimeoutError) as mocked:
            for side in ("target","baseline"):
                result=client.request(cfg[side],cfg,PROBES[0])
                self.assertFalse(result["passed"])
                self.assertIn("TimeoutError",result["error"])
                self.assertEqual(mocked.call_args.kwargs["timeout"],.01)
    def test_usage_and_prices(self):
        with LocalServer() as server, Fixture() as f:
            cfg=configuration(server.url)
            cfg["prices"]={"test-model":dict(input_per_1k=1,output_per_1k=2)}
            f.write(cfg)
            self.assertEqual(f.probe()[0],0)
            row=json.loads(f.ledger.read_text().splitlines()[0])
            self.assertEqual(row["cost_usd"]["target"],.015)
            server.mode="no_usage"
            self.assertEqual(f.probe("no-usage")[0],0)
            row=json.loads(f.ledger.read_text().splitlines()[-1])
            self.assertIsNone(row["target"]["prompt_tokens"])
            self.assertIsNone(row["cost_usd"]["target"])
    def test_exit_codes(self):
        self.assertEqual(run("report","--ledger",str(SAMPLE))[0],0)
        for window,expected in ((1,0),(2,1),(3,2)):
            self.assertEqual(run("check","--ledger",str(SAMPLE),"--window",str(window))[0],expected)
        with Fixture() as f:
            self.assertEqual(run("probe","--config",str(f.config),"--ledger",str(f.ledger))[0],1)
            for command in ("report","check"):
                self.assertEqual(run(command,"--ledger",str(f.ledger))[0],1)
                self.assertEqual(run(command,"--ledger",str(SAMPLE),"--window","0")[0],1)
            f.write(configuration("http://127.0.0.1:1/v1"))
            with patch("relay_quality_monitor.client.request",return_value={}):
                self.assertEqual(run("probe","--config",str(f.config),"--ledger",str(f.path))[0],1)
    def test_readme_audit(self):
        readme=(Path(__file__).resolve().parents[1]/"README.md").read_text()
        for probe in PROBES:
            self.assertIn(probe[0],readme)
            self.assertIn(probe[1],readme)
        for sentence in LIMITATIONS:
            self.assertIn(sentence,readme)
        for phrase in ("## Differentiation", "relay-audit", "blackbox-bill", "cctest / hvoy", "OpenRouter", "keys from environment only"):
            self.assertIn(phrase,readme)

LIMITATIONS = [
"A single probe round cannot prove dilution.",
"Only sustained statistical drift is a signal, and even then the cause can be the baseline drifting, rate limiting, transient errors, or a genuinely weaker model behind the same name — the report shows error rates and per-probe breakdowns so the user can tell these apart.",
"The probe set is fixed and public (it ships in the repo).",
"A relay could in principle special-case these exact prompts.",
"Identity answers are unreliable and never scored.",
"Cost numbers appear only with a user-supplied price table; token counts are endpoint-reported, never estimated client-side.",
"The tool is an end-user monitor ONLY.",
"It must not contain, and the README must not describe, any anti-detection help for relays (no prompt randomization to evade detection, no traffic shaping to look human, no guidance on defeating dilution detectors).",
"Probes cost real tokens on both endpoints.",
"small, bounded, and user-controlled via cron",
"keep the ledger local; do not publish it (it may contain anything the models returned)."
]
