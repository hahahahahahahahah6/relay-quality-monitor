import contextlib
import io
import json
import os
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from relay_quality_monitor.cli import main
from relay_quality_monitor.probes import PROBES


def run(*args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(args))
    return code, out.getvalue(), err.getvalue()


class LocalServer:
    def __enter__(self):
        owner = self
        self.requests = []
        self.mode = "good"
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                owner.requests.append((self.path, payload, self.headers.get("Authorization")))
                if owner.mode == "http":
                    self.send_error(503)
                    return
                self.send_response(200)
                self.end_headers()
                if owner.mode == "malformed":
                    self.wfile.write(b'{"choices": []}')
                    return
                probe = next(p for p in PROBES if p[1] == payload["messages"][0]["content"])
                answer = probe[3] if probe[2] != "none" else "I am a synthetic model.\nVerbatim."
                data = {"choices": [{"message": {"content": answer}}]}
                if owner.mode != "no_usage":
                    data["usage"] = {"prompt_tokens": 9, "completion_tokens": 3}
                self.wfile.write(json.dumps(data).encode())
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = "http://127.0.0.1:%s/v1" % self.server.server_port
        return self
    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


def configuration(url):
    return {"target": {"base_url": url, "api_key_env": "TEST_TARGET_KEY", "model": "test-model"},
            "baseline": {"base_url": url, "api_key_env": "TEST_BASELINE_KEY", "model": "test-model"},
            "probes": "builtin"}


class Fixture:
    def __enter__(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)
        self.config = self.path / "config.json"
        self.ledger = self.path / "ledger.jsonl"
        self.env = patch.dict(os.environ, TEST_TARGET_KEY="test-key-target", TEST_BASELINE_KEY="test-key-baseline")
        self.env.start()
        return self
    def write(self, cfg):
        self.config.write_text(json.dumps(cfg))
    def probe(self, rid="round-1"):
        return run("probe", "--config", str(self.config), "--ledger", str(self.ledger), "--round-id", rid)
    def __exit__(self, *args):
        self.env.stop()
        self.temp.cleanup()
