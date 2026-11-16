import argparse
from datetime import datetime, timezone
import json
import math
import sys
from . import __version__
from . import client, config, ledger, report
from .probes import PROBES


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def positive(value):
    number = int(value)
    if number <= 0:
        raise ValueError("expected positive integer")
    return number


def gap(value):
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError("expected finite nonnegative gap")
    return number


def main(argv=None):
    try:
        parser = Parser(prog="relay-quality-monitor")
        parser.add_argument("--version", action="version", version=__version__)
        subs = parser.add_subparsers(dest="command", required=True, parser_class=Parser)
        probe = subs.add_parser("probe")
        probe.add_argument("--config", required=True)
        probe.add_argument("--ledger", required=True)
        probe.add_argument("--round-id")
        for name in ("report", "check"):
            sub = subs.add_parser(name)
            sub.add_argument("--ledger", required=True)
            sub.add_argument("--window", type=positive)
            if name == "report":
                sub.add_argument("--json", action="store_true")
            else:
                for level, default_gap, default_rounds in (("fail", .25, 3), ("warn", .15, 2)):
                    sub.add_argument("--" + level + "-gap", type=gap, default=default_gap)
                    sub.add_argument("--" + level + "-rounds", type=positive, default=default_rounds)
        args = parser.parse_args(argv)
        if args.command == "probe":
            cfg = config.load(args.config)
            ts = datetime.now(timezone.utc).isoformat()
            rid = args.round_id if args.round_id is not None else ts
            records = []
            for probe in PROBES:
                row = dict(ts=ts, round_id=rid, probe_id=probe[0])
                for side in ("target", "baseline"):
                    row[side] = client.request(cfg[side], cfg, probe)
                row["cost_usd"] = {s: client.cost(row[s], cfg["prices"]) for s in ("target", "baseline")} if "prices" in cfg else None
                records.append(row)
            ledger.append(args.ledger, records)
            print("Appended 12 probe records.")
            return 0
        result = report.aggregate(ledger.read(args.ledger), args.window)
        if args.command == "report":
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                for key, value in result.items():
                    print(key.replace("_", " ") + ": " + (value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)))
            return 0
        code = report.check(result, args.fail_gap, args.fail_rounds, args.warn_gap, args.warn_rounds)
        print(("No sustained drift", "Warning: sustained drift", "Failure: sustained drift")[code] + "; statistical signal, not proof of dilution.")
        return code
    except (ValueError, OSError, TypeError, OverflowError) as exc:
        print("Error: " + ("ledger: unable to read or write" if isinstance(exc, OSError) else str(exc)), file=sys.stderr)
        return 1
