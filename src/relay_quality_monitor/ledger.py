import json
import math
from .probes import PROBES


def append(path, records):
    with open(path, "a", encoding="utf-8") as stream:
        stream.write("".join(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n" for row in records))


def number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def validate(row):
    if not isinstance(row, dict):
        raise ValueError("invalid record")
    if not isinstance(row["round_id"], str) or not isinstance(row["ts"], str) or row["probe_id"] not in {p[0] for p in PROBES}:
        raise ValueError("invalid record")
    for side in ("target", "baseline"):
        item = row[side]
        if not isinstance(item, dict) or not isinstance(item["model"], str):
            raise ValueError("invalid side")
        if item["response"] is not None and not isinstance(item["response"], str):
            raise ValueError("invalid response")
        if item["error"] is not None and not isinstance(item["error"], str):
            raise ValueError("invalid error")
        expected_identity = row["probe_id"] == "identity" and item["error"] is None
        if (expected_identity and item["passed"] is not None) or (not expected_identity and type(item["passed"]) is not bool):
            raise ValueError("invalid passed")
        if item["latency_ms"] is not None and not number(item["latency_ms"]):
            raise ValueError("invalid latency")
        for field in ("prompt_tokens", "completion_tokens"):
            if item[field] is not None and (type(item[field]) is not int or item[field] < 0):
                raise ValueError("invalid usage")
    costs = row["cost_usd"]
    if costs is not None:
        if not isinstance(costs, dict) or set(costs) != {"target", "baseline"}:
            raise ValueError("invalid cost")
        if any(value is not None and not number(value) for value in costs.values()):
            raise ValueError("invalid cost")


def read(path):
    try:
        with open(path, encoding="utf-8") as stream:
            rows = [json.loads(line) for line in stream if line.strip()]
        if not rows:
            raise ValueError("empty")
        for row in rows:
            validate(row)
        return rows
    except (OSError, ValueError, KeyError, TypeError, OverflowError):
        raise ValueError("ledger: missing, empty, or malformed") from None
