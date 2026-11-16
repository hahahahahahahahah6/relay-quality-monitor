import json
import math
import os
from urllib.parse import urlsplit


def load(path):
    try:
        with open(path, encoding="utf-8") as stream:
            cfg = json.load(stream)
    except (OSError, ValueError):
        raise ValueError("config: unreadable or invalid JSON") from None
    if not isinstance(cfg, dict):
        raise ValueError("config: expected object")
    allowed = {"target", "baseline", "prices", "timeout_s", "max_tokens", "temperature", "probes"}
    if set(cfg) - allowed:
        raise ValueError("config: unknown field " + sorted(set(cfg) - allowed)[0] + " (inline keys rejected)")
    for side in ("target", "baseline"):
        item = cfg.get(side)
        if not isinstance(item, dict) or set(item) != {"base_url", "api_key_env", "model"}:
            raise ValueError(side + ": requires base_url, api_key_env, model; inline keys rejected")
        for field in ("base_url", "api_key_env", "model"):
            if not isinstance(item[field], str) or not item[field].strip():
                raise ValueError(side + "." + field + ": expected nonempty string")
        url = urlsplit(item["base_url"])
        if url.scheme not in ("http", "https") or not url.netloc or url.username or url.password or url.query or url.fragment:
            raise ValueError(side + ".base_url: expected HTTP(S) URL without credentials/query/fragment")
        if not os.environ.get(item["api_key_env"]):
            raise ValueError(side + ".api_key_env: missing environment variable")
    if cfg["target"]["model"] != cfg["baseline"]["model"]:
        raise ValueError("baseline.model: must equal target.model")
    if cfg.get("probes") != "builtin":
        raise ValueError("probes: must be builtin")
    for field, default in (("timeout_s", 60), ("max_tokens", 64), ("temperature", 0)):
        value = cfg.setdefault(field, default)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 or (field != "temperature" and value == 0) or (field == "max_tokens" and not isinstance(value, int)):
            raise ValueError(field + ": invalid numeric value")
    if "prices" in cfg:
        if not isinstance(cfg["prices"], dict):
            raise ValueError("prices: expected object")
        for model, price in cfg["prices"].items():
            if not isinstance(price, dict) or set(price) != {"input_per_1k", "output_per_1k"}:
                raise ValueError("prices: requires input_per_1k and output_per_1k")
            for value in price.values():
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                    raise ValueError("prices: expected finite nonnegative rates")
    return cfg
