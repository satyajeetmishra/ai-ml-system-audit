# B2, B3, B4 — throughput anomaly, honest goodput, monitoring metric

Computed in `capacity_and_throughput.py`; full output in
`results/capacity_and_throughput_output.txt`.

## B2 — the anomaly, the mechanism, and a proposed fix

**The anomaly.** In the `prompt_len=3584` sweep, `reported_tok_s` rises with
batch size from 4 to 24 (565 → 903 → 1311 → **1607**), then *reverses* at
32 and 48 (1384 → **1299**) — fewer tokens/sec with *more* concurrent
requests. That's not just diminishing returns, it's a drop, which naive
"throughput scales with batch" doesn't predict at all.

**The mechanism, row by row.** `kv_cache_util` climbs 0.16 → 0.31 → 0.62 →
0.93 → **0.97** → **0.97** across the same batches, and `preempted_seqs`
goes 0/0/0/**0** → **7** → **23**. The reversal starts exactly where the
KV cache saturates and the scheduler starts preempting sequences (B1 found
the real ceiling here is ~25 concurrent full-context sequences — batch=24
is right at the edge with 0 preemptions; batch=32 and 48 are past it). A
preempted sequence's KV cache gets evicted and its prefill work has to be
redone when it's re-admitted — that's wasted compute that shows up as
ballooning wall-clock time (94.7s and 151.4s vs. what linear scaling from
batch=24's 61.2s would predict) and, eventually, drags down even the
blended `reported_tok_s` metric despite that metric's own tendency to look
inflated (see B3).

**Proposed change: cap admission for long-context requests at the actual
capacity ceiling (~24 concurrent sequences at ~4096 tokens) instead of
admitting up to 48 and letting the scheduler preempt.** Concretely, set
`max_num_seqs` (or the equivalent admission-control limit) context-aware,
so requests near `max_model_len` are capped near 24–25 concurrent, with
excess requests queued rather than admitted-then-preempted.

**Predicted quantitative effect — read directly off rows already in the
log**, since batch=24 *is* what "capped at capacity" looks like:

| | batch=48 (current/uncapped) | batch=24 (capped) | change |
|---|---|---|---|
| `reported_tok_s` | 1298.5 | 1607.4 | **+23.8%** |
| `e2e_ms_p95` | 105,427.5 ms | 69,221.3 ms | **−34.3%** |
| `preempted_seqs` | 23 | 0 | **eliminated** |

Capping admission at the real ceiling isn't a trade-off here — it's
strictly better on every axis this log actually measured, because the
"extra" batch beyond ~25 wasn't doing useful work, it was thrashing.

## B3 — honest goodput of the batch=24 long-prompt row, two ways

Row: `batch=24, prompt_len=3584, gen_len=512, wall_clock_s=61.16,
reported_tok_s=1607.4, ttft_ms_p50=500.5, itl_ms_p50=96.07`.

**Method 1 — from `itl_ms_p50`** (median time between successive decode
steps; each step advances every sequence in the batch by one token):
```
goodput = batch_size / (itl_ms_p50 / 1000)
        = 24 / (96.07 / 1000) = 249.8 tok/s
```

**Method 2 — from wall-clock minus time-to-first-token**, i.e. isolating
decode time and dividing by tokens actually generated:
```
decode_time = wall_clock_s - (ttft_ms_p50 / 1000) = 61.16 - 0.5005 = 60.66s
generated_tokens = batch_size x gen_len = 24 x 512 = 12,288
goodput = 12,288 / 60.66 = 202.6 tok/s
```

The two methods (249.8 vs. 202.6 tok/s) don't match to the decimal —
method 2 compares a total wall-clock figure against a median (`ttft_ms_p50`
is a p50 statistic, not a total), and ramp-up/scheduling overhead isn't
isolated the same way in both — but they agree on **order of magnitude and
conclusion**: honest goodput for this row is roughly **200–250 tok/s**,
not the 1607.4 tok/s `reported_tok_s` shows. That's a **6.4×–7.9×**
inflation.

**What REPORT_v0 should have said.** Both of Section 2's claims trace back
to the same formula: `reported_tok_s = batch_size × (prompt_len + gen_len)
/ wall_clock_s` (verified by recomputing it from logged fields — see
`capacity_and_throughput.py` output, matches the logged column to within
rounding on every row). That single formula explains both errors at once:

- *"Longer prompts give better throughput"* — prefill tokens are cheap to
  add to the numerator (prefill is fast and compute-parallel) without a
  proportional wall-clock cost, so blended throughput mechanically rises
  with prompt length. The decode-only signal says the opposite: at the
  same batch (16), `itl_ms_p50` is 48.33ms for short prompts vs. **77.2ms**
  for long ones — decode is **60% slower per token** with the long prompt,
  not faster. Every extra token of KV cache read at each step costs real
  time; that cost is invisible in a metric that also happens to be padded
  by "free" prefill tokens.
- *"Batch 48 should give ~3200 tok/s"* — this took the peak of the same
  blended metric (1607.4 at batch=24, "~1600 tok/s best observed") and
  linearly doubled it. But batch=48 was **already in the log** at the time
  this report was written — it shows 1298.5, not 3200, with 23 preempted
  sequences. The report didn't need to extrapolate anything; it needed to
  read the row that was already there.

The report should have said: honest decode goodput at batch=24 is roughly
200–250 tok/s, about 6–8× lower than the blended metric suggests; batch=48
at this context length is not a capacity target, it's already past this
GPU's ~25-sequence ceiling (B1) and is measurably worse than batch=24 on
every metric that matters, including the flawed one.

## B4 — which counter would confirm this, and what value to expect

I'd pull the serving engine's live **KV-cache block utilization gauge**
(this log's `kv_cache_util` is exactly that; in vLLM this is the
`gpu_cache_usage_perc` metric). If the B2 mechanism is right, this should
sit **near saturation (≥0.95, effectively capped around 0.97 here)**
precisely at the batch sizes where `reported_tok_s` reverses and
`preempted_seqs` turns nonzero — not gradually rising, but pinned at a
ceiling, which is the signature of a hard capacity limit rather than a
gradual efficiency loss. `preempted_seqs` (or vLLM's `num_preemptions`
counter) is the direct corroborating signal — nonzero preemptions only
where the cache gauge is already pinned — but the cache-utilization gauge
is the more fundamental one, because it would show the same saturation
even under a scheduler that rejects excess requests outright instead of
preempting them.
