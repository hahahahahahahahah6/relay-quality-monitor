import json
import unittest
from relay_quality_monitor.config import load
from .helpers import Fixture, configuration

class ConfigTests(unittest.TestCase):
    def test_defaults(self):
        with Fixture() as f:
            f.write(configuration("http://127.0.0.1:1/v1"))
            cfg = load(f.config)
            self.assertEqual((cfg["timeout_s"], cfg["max_tokens"], cfg["temperature"]), (60,64,0))
    def test_invalid_fields(self):
        variants = [("probes", "custom"), ("timeout_s", 0), ("max_tokens", 1.5), ("temperature", float("nan")), ("prices", {"x": {"input_per_1k": -1, "output_per_1k": 1}})]
        with Fixture() as f:
            for field, value in variants:
                cfg = configuration("http://127.0.0.1:1/v1")
                cfg[field] = value
                f.write(cfg)
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, field):
                    load(f.config)
    def test_inline_keys_missing_environment_and_model(self):
        with Fixture() as f:
            for field, value, message in (("api_key", "test-key-inline", "inline keys"), ("api_key_env", "R217_NONEXISTENT", "api_key_env"), ("model", "other-model", "model"), ("base_url", "https://test-key-inline@example.invalid", "base_url")):
                cfg = configuration("http://127.0.0.1:1/v1")
                cfg["baseline"][field] = value
                f.write(cfg)
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, message):
                    load(f.config)
    def test_bad_json_and_shape(self):
        with Fixture() as f:
            for value in ("{", "[]", "{}"):
                f.config.write_text(value)
                with self.assertRaises(ValueError):
                    load(f.config)
