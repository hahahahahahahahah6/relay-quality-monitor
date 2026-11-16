import json
import os
import time
import urllib.request
from .probes import check


def request(side, cfg, probe):
    result = dict(model=side["model"], response=None, passed=False, latency_ms=None,
                  prompt_tokens=None, completion_tokens=None, error=None)
    start = time.perf_counter()
    try:
        payload = dict(model=side["model"], messages=[{"role": "user", "content": probe[1]}],
                       temperature=cfg["temperature"], max_tokens=cfg["max_tokens"])
        req = urllib.request.Request(side["base_url"].rstrip("/") + "/chat/completions",
            data=json.dumps(payload).encode(), headers={"Content-Type": "application/json",
            "Authorization": "Bearer " + os.environ[side["api_key_env"]]})
        with urllib.request.urlopen(req, timeout=cfg["timeout_s"]) as response:
            data = json.load(response)
        answer = data["choices"][0]["message"]["content"]
        if not isinstance(answer, str):
            raise ValueError("invalid content")
        usage = data.get("usage") or {}
        if not isinstance(usage, dict):
            raise ValueError("invalid usage")
        for field in ("prompt_tokens", "completion_tokens"):
            value = usage.get(field)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError("invalid token count")
            result[field] = value
        result.update(response=answer, passed=check(probe, answer))
    except Exception as exc:
        # Never expose exception text: servers can echo credentials in errors.
        result.update(response=None, passed=False, prompt_tokens=None, completion_tokens=None,
                      error="request failed: " + type(exc).__name__)
    finally:
        result["latency_ms"] = (time.perf_counter() - start) * 1000
    return result


def cost(result, prices):
    price = prices.get(result["model"])
    if price is None or result["prompt_tokens"] is None or result["completion_tokens"] is None:
        return None
    return (result["prompt_tokens"] * price["input_per_1k"] +
            result["completion_tokens"] * price["output_per_1k"]) / 1000
