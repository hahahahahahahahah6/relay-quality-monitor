from statistics import mean
from .probes import PROBES

WARNING = "Identity answers are unreliable and never scored; models may refuse, or answer with their training identity."


def aggregate(rows, window=None):
    groups = {}
    for row in rows:
        groups.setdefault(row["round_id"], []).append(row)
    selected = list(groups.items())[-window:] if window else list(groups.items())
    rows = [row for _, group in selected for row in group]
    rounds = []
    for rid, group in selected:
        scored = [r for r in group if r["probe_id"] != "identity"]
        scores = {s: sum(r[s]["passed"] is True for r in scored) / 11 for s in ("target", "baseline")}
        rounds.append(dict(round_id=rid, **scores, gap=scores["baseline"] - scores["target"],
                           eligible=any(r["target"]["error"] is None and r["baseline"]["error"] is None for r in scored)))
    rates, ratios = {}, {}
    for pid, *_ in PROBES:
        group = [r for r in rows if r["probe_id"] == pid]
        rates[pid] = {s: (sum(r[s]["passed"] is True for r in group) / len(group) if group and pid != "identity" else None) for s in ("target", "baseline")}
        values = [r["target"]["latency_ms"] / r["baseline"]["latency_ms"] for r in group
                  if r["target"]["error"] is None and r["baseline"]["error"] is None
                  and r["baseline"]["latency_ms"] and r["target"]["latency_ms"] is not None]
        ratios[pid] = mean(values) if values else None
    result = dict(rounds_covered=len(rounds), per_probe_pass_rates=rates, rounds=rounds,
        mean_capability_gap=mean(r["gap"] for r in rounds), mean_latency_ratio=ratios,
        token_totals={s: {f: sum(r[s][f] for r in rows if r[s][f] is not None) for f in ("prompt_tokens", "completion_tokens")} for s in ("target", "baseline")},
        missing_usage_counts={s: sum(r[s]["prompt_tokens"] is None or r[s]["completion_tokens"] is None for r in rows) for s in ("target", "baseline")},
        error_counts={s: sum(r[s]["error"] is not None for r in rows) for s in ("target", "baseline")},
        identity_warning=WARNING, identity_answers=[dict(round_id=r["round_id"], **{s: r[s]["response"] for s in ("target", "baseline")}) for r in rows if r["probe_id"] == "identity"])
    if any(r["cost_usd"] is not None for r in rows):
        result["cost_totals"] = {s: sum(r["cost_usd"][s] for r in rows if r["cost_usd"] is not None and r["cost_usd"][s] is not None) for s in ("target", "baseline")}
        result["missing_cost_counts"] = {s: sum(r["cost_usd"] is None or r["cost_usd"][s] is None for r in rows) for s in ("target", "baseline")}
    return result


def sustained(rounds, threshold, count):
    streak = 0
    for row in rounds:
        if not row["eligible"]:
            continue
        streak = streak + 1 if row["gap"] >= threshold else 0
        if streak >= count:
            return True
    return False


def check(result, fail_gap=.25, fail_rounds=3, warn_gap=.15, warn_rounds=2):
    if sustained(result["rounds"], fail_gap, fail_rounds):
        return 2
    return 1 if sustained(result["rounds"], warn_gap, warn_rounds) else 0
