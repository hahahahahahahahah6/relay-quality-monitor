# relay-quality-monitor

A standard-library-only CLI that probes a live relay and a trusted baseline with
identical prompts, recording capability, latency, reported usage and optional
cost statistics in a local JSONL ledger. Statistics, not verdicts. No telemetry,
accounts, third-party runtime dependencies, or built-in endpoint addresses.

## Install and run

Requires Python 3.9+.

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install build
python3 -m build
python3 -m pip install dist/relay_quality_monitor-0.1.0-py3-none-any.whl
relay-quality-monitor --version
python3 -m relay_quality_monitor --help
python3 -m unittest discover
```

Copy `examples/sample-config.json` to your own local config, replace the placeholder
URLs and model, and set the named key variables in your environment. Use your
shell's secure credential workflow; never put credentials in the config.

```sh
relay-quality-monitor probe --config config.json --ledger ledger.jsonl
relay-quality-monitor report --ledger ledger.jsonl --window 10
relay-quality-monitor report --ledger ledger.jsonl --json
relay-quality-monitor check --ledger ledger.jsonl
```

Each probe invocation runs one round: 12 probes, target then baseline for each
probe, 24 HTTP requests total. Scheduling belongs to your cron. No daemon or
`--loop` exists. For example, after configuring environment variables for cron:

```cron
0 * * * * /absolute/path/.venv/bin/relay-quality-monitor probe --config /absolute/path/config.json --ledger /absolute/path/ledger.jsonl
```

## Configuration

**keys from environment only**: `target` and `baseline` each require exactly
`base_url`, `api_key_env`, and `model`. Inline keys are rejected. `api_key_env`
names an existing nonempty environment variable. Keys are never printed or stored
in the ledger. Use a chat API base URL such as your configured `/v1` root;
`/chat/completions` is appended. Both sides must use the same model name.
The same messages, temperature, max_tokens and timeout apply to both sides.

`probes` must be exactly `"builtin"`. Defaults: `timeout_s=60`, `max_tokens=64`,
`temperature=0`. Timeout and max_tokens must be positive; max_tokens is an integer;
temperature must be finite and nonnegative. Unknown fields are rejected.
An optional `prices` object maps model names to finite nonnegative
`input_per_1k` and `output_per_1k` rates in USD. For example:

```json
{"prices": {"example-model": {"input_per_1k": 0.001, "output_per_1k": 0.002}}}
```

This fragment belongs alongside target, baseline and probes in your config.
Without prices, no cost totals are shown. Missing rates or usage give null per-probe
costs. Reports show known token/cost totals and missing-data counts, so partial
totals are distinguishable from complete measurements. No usage is estimated.

## Fixed builtin probes (version 0.1.0)

All comparisons strip leading/trailing whitespace, collapse inner whitespace,
and casefold. The primes check accepts comma or whitespace separators and ignores
order. Identity is unscored. The capability score is always passed / 11.

| ID | Exact prompt | Check |
| --- | --- | --- |
| arith-1 | What is 847 × 293? Reply with only the number. | exact `248171` |
| arith-2 | What is 17 + 25 × 4? Reply with only the number. | exact `117` |
| capital-1 | What is the capital of Australia? Reply with only the city name. | exact `Canberra` |
| capital-2 | What is the capital of Canada? Reply with only the city name. | exact `Ottawa` |
| exact-word | Reply with exactly the word BLUE and nothing else. | exact `BLUE` |
| primes | List the first five prime numbers, separated by commas, and nothing else. | set {2, 3, 5, 7, 11}; order-insensitive; comma/whitespace tolerant |
| translate | Translate 'good morning' to French. Reply with only the translation. | contains bonjour |
| reverse | Reverse the string 'abcde'. Reply with only the reversed string. | exact `edcba` |
| count-letters | How many times does the letter 's' appear in the word 'mississippi'? Reply with only the number. | exact `4` |
| logic-1 | A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How much does the ball cost in cents? Reply with only the number. | exact `5` |
| contains-words | Write one sentence that contains all three words: river, bridge, moon. Reply with only the sentence. | contains river bridge moon |
| identity | Which model are you? Reply in one short sentence. | none; UNscored, raw answer only |

## Ledger and reports

The local JSONL ledger appends exactly 12 records per completed round, one per
probe. Each record has `ts` (ISO-8601 UTC), `round_id`, `probe_id`, `target`,
`baseline`, and `cost_usd` (null without prices, otherwise target/baseline values).
Each side contains `model`, `response` (verbatim), `passed` (boolean, null for a
successful identity response), `latency_ms`, `prompt_tokens`, `completion_tokens`,
and `error`. Request failures have response=null, passed=false, a short error
category, and null usage. Even a failed identity request never affects scoring.
Latency is measured client-side. Missing reported usage stays null.

Round IDs default to UTC timestamps; use `--round-id` to supply a unique string.
Reuse of a round ID groups its records together; use distinct IDs for each round.
Reports preserve the ledger's first-seen round order. `--window N` selects the last
N rounds; N must be positive. Missing, empty or malformed ledgers are errors.

Reports show rounds covered, per-probe pass rates, both capability scores per
round, mean capability gap (baseline score − target score), mean latency ratio
(target/baseline) per probe where both answered and baseline latency is positive,
reported token totals, optional known cost totals, error counts and raw identity
answers with an unreliability warning. Pass rates include request failures as
failures; identity has no pass rate. Failed requests do not enter latency ratios.

`check` detects any sustained streak in the selected window. A qualifying gap is
>= the threshold for K consecutive eligible rounds. A lower eligible gap breaks
a streak. A round is eligible only if at least one scored probe answered on both
sides. Error-only rounds neither count nor break a streak. Defaults:
`--fail-gap 0.25 --fail-rounds 3 --warn-gap 0.15 --warn-rounds 2`.
The fail condition takes precedence. This is a statistical signal, not proof of
dilution. Scores and mean gaps still show error-only rounds; streaks skip them.

Exit codes:

- `probe`: 0 on completed round, including request failures; 1 on config/ledger errors.
- `report`: 0 on success; 1 on missing/empty/invalid ledger or arguments.
- `check`: 2 sustained failure signal; 1 sustained warning signal (or input error);
  0 otherwise. Input errors print `Error:` on stderr.

The bundled sample ledger is entirely synthetic: 3 rounds, target 7/11, baseline
11/11, mean gap 4/11, latency ratio 2 for every probe, no errors or costs.
Each side totals 720 prompt and 180 completion tokens. `report` exits 0;
`check` exits 2, `check --window 2` exits 1, and `check --window 1` exits 0.

## Honest limitations

A single probe round cannot prove dilution.

Only sustained statistical drift is a signal, and even then the cause can be the baseline drifting, rate limiting, transient errors, or a genuinely weaker model behind the same name — the report shows error rates and per-probe breakdowns so the user can tell these apart.

The probe set is fixed and public (it ships in the repo).

A relay could in principle special-case these exact prompts.

Identity answers are unreliable and never scored.

Cost numbers appear only with a user-supplied price table; token counts are endpoint-reported, never estimated client-side.

The tool is an end-user monitor ONLY.

It must not contain, and the README must not describe, any anti-detection help for relays (no prompt randomization to evade detection, no traffic shaping to look human, no guidance on defeating dilution detectors).

Probes cost real tokens on both endpoints.

small, bounded, and user-controlled via cron

keep the ledger local; do not publish it (it may contain anything the models returned).

The 12-probe per-round token use is small, bounded, and user-controlled via cron.
The configured max_tokens bounds requested output per request, while prompt and
provider accounting can vary; all token totals come from endpoint usage objects.
Only your two configured endpoints receive traffic. No anti-detection features
are provided.

## Differentiation

- vs relay-audit (sibling): relay-audit is offline billing audit from a user-supplied
  JSONL of past transactions — billed vs ground-truth ratios, cache-impossible,
  model substitution from returned_model fields, duration outliers. It never sends
  traffic and never measures live capability. relay-quality-monitor is live
  continuous probing against a trusted baseline; it never reads billing logs and
  never computes billed-vs-actual ratios.
- vs #13 blackbox-bill: spend attribution across tools; this guards quality drift,
  not spend.
- vs cctest / hvoy: single-shot dilution tests, judged insufficient by the users who
  asked for this tool; this is scheduled probing plus drift statistics over a ledger.
- vs OpenRouter / first-party dashboards: those show one endpoint's own numbers;
  this compares two endpoints on identical prompts over time.

## Development

`python3 -m unittest discover` runs the bundled suite. HTTP integration tests use
an in-process stdlib server bound to 127.0.0.1 on an ephemeral port, canned
responses, and fake keys only. No tests contact external services. Build both
sdist and wheel using `python3 -m build` inside a venv with build installed.
MIT licensed.
