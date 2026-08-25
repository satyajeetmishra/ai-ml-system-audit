#!/usr/bin/env python3
"""
capacity_and_throughput.py -- Part B, all sub-parts computed programmatically
against the actual starter_kit/bench/model_spec.md and bench_log.csv.

B1: KV-cache bytes/token, max concurrent 4096-token sequences
B2: throughput anomaly in the prompt=3584 sweep
B3: honest goodput of the batch=24 long-prompt row, two independent ways
B4: (answered in the write-up, not computed -- it's a "what would you pull" question)
"""
import csv
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
BENCH_LOG = os.path.join(ROOT, "..", "given_starter_kit", "bench", "bench_log.csv")

# ---- values transcribed directly from bench/model_spec.md ----
PARAMS = 4.2e9
LAYERS = 28
KV_HEADS = 8
HEAD_DIM = 128
DTYPE_BYTES = 2          # fp16 weights and KV cache
GPU_MEM_GB = 24          # "1x NVIDIA L4 (24 GB)"
GPU_UTIL = 0.92          # gpu_memory_utilization
NON_KV_OVERHEAD_GB = 1.6
MAX_MODEL_LEN = 4096

print("=" * 70)
print("B1 -- KV-cache bytes/token and max concurrent 4096-token sequences")
print("=" * 70)

kv_bytes_per_token = 2 * LAYERS * KV_HEADS * HEAD_DIM * DTYPE_BYTES
print(f"KV bytes/token = 2(K,V) x {LAYERS} layers x {KV_HEADS} kv_heads x "
      f"{HEAD_DIM} head_dim x {DTYPE_BYTES} bytes(fp16)")
print(f"              = {kv_bytes_per_token} bytes/token "
      f"({kv_bytes_per_token/1024:.1f} KiB/token)")

weight_bytes = PARAMS * DTYPE_BYTES
print(f"\nWeight bytes = {PARAMS:.2e} params x {DTYPE_BYTES} bytes = {weight_bytes:.4e} bytes")


def capacity(unit_bytes_per_gb, label):
    total = GPU_MEM_GB * unit_bytes_per_gb
    usable = total * GPU_UTIL
    overhead = NON_KV_OVERHEAD_GB * unit_bytes_per_gb
    avail_for_kv = usable - weight_bytes - overhead
    max_tokens = avail_for_kv / kv_bytes_per_token
    max_seqs = int(max_tokens // MAX_MODEL_LEN)
    print(f"\n-- interpreting '24 GB' as {label} ({unit_bytes_per_gb:.0f} bytes/GB) --")
    print(f"   total mem        = {total:.4e} bytes")
    print(f"   usable (x{GPU_UTIL}) = {usable:.4e} bytes")
    print(f"   - weights        = {weight_bytes:.4e} bytes")
    print(f"   - non-KV overhead= {overhead:.4e} bytes")
    print(f"   = available for KV cache = {avail_for_kv:.4e} bytes")
    print(f"   max tokens       = {max_tokens:,.0f}")
    print(f"   max concurrent {MAX_MODEL_LEN}-token sequences = {max_tokens:.0f} / {MAX_MODEL_LEN} "
          f"= {max_tokens/MAX_MODEL_LEN:.2f} -> floor = {max_seqs}")
    return max_seqs


max_seqs_decimal = capacity(1_000_000_000, "decimal GB, 10^9 bytes")
max_seqs_gib = capacity(1024**3, "GiB, 2^30 bytes")

print("\n" + "=" * 70)
print("Cross-check against bench_log.csv: preempted_seqs and kv_cache_util")
print("=" * 70)

rows = []
with open(BENCH_LOG) as f:
    reader = csv.DictReader(f)
    for r in reader:
        rows.append({k: float(v) if k != "batch_size" and k != "num_requests" and k != "preempted_seqs"
                      else int(float(v)) for k, v in r.items()})

long_rows = [r for r in rows if r["prompt_len"] == 3584]
print(f"{'batch':>6}{'kv_cache_util':>15}{'preempted_seqs':>16}{'implied true cap (batch-preempted)':>38}")
for r in long_rows:
    implied = r["batch_size"] - r["preempted_seqs"] if r["preempted_seqs"] > 0 else None
    print(f"{r['batch_size']:>6}{r['kv_cache_util']:>15}{r['preempted_seqs']:>16}"
          f"{'' if implied is None else implied:>38}")

print(f"\nB1 prediction (decimal GB interpretation): {max_seqs_decimal} concurrent full-context sequences")
print(f"B1 prediction (GiB interpretation):         {max_seqs_gib} concurrent full-context sequences")
print("Empirical (batch=32, 7 preempted): 32-7 = 25")
print("Empirical (batch=48, 23 preempted): 48-23 = 25")
print("=> decimal-GB interpretation matches the empirical onset exactly; GiB does not.")

print("\n" + "=" * 70)
print("B2/B3 -- reverse-engineering reported_tok_s, and honest goodput")
print("=" * 70)

print(f"\n{'batch':>6}{'prompt':>8}{'gen':>6}{'wall_s':>9}{'reported':>10}{'formula_check':>15}")
for r in rows:
    formula = r["batch_size"] * (r["prompt_len"] + r["gen_len"]) / r["wall_clock_s"]
    print(f"{r['batch_size']:>6}{r['prompt_len']:>8.0f}{r['gen_len']:>6.0f}{r['wall_clock_s']:>9.2f}"
          f"{r['reported_tok_s']:>10.1f}{formula:>15.1f}")
print("\nformula: reported_tok_s = batch_size * (prompt_len + gen_len) / wall_clock_s")
print("(blends one-time prefill tokens with sustained decode tokens over the FULL wall clock)")

print("\n-- long-prompt (3584) sweep: reported_tok_s trend by batch --")
for r in long_rows:
    print(f"  batch={r['batch_size']:>3}  reported_tok_s={r['reported_tok_s']:>8.1f}  "
          f"preempted={r['preempted_seqs']:>3}  kv_cache_util={r['kv_cache_util']:.2f}")

b24 = next(r for r in long_rows if r["batch_size"] == 24)
print(f"\n-- honest goodput of the batch=24, prompt=3584 row --")
print(f"   row: {b24}")

# Method 1: via itl_ms_p50 (inter-token latency = time per decode step across the batch)
goodput_1 = b24["batch_size"] / (b24["itl_ms_p50"] / 1000)
print(f"\n   Method 1 (itl_ms_p50): goodput = batch_size / (itl_ms_p50/1000)")
print(f"     = {b24['batch_size']:.0f} / ({b24['itl_ms_p50']}/1000) = {goodput_1:.1f} tok/s")

# Method 2: via wall_clock minus ttft (approx decode-only time), generated tokens only
decode_time = b24["wall_clock_s"] - (b24["ttft_ms_p50"] / 1000)
generated_tokens = b24["batch_size"] * b24["gen_len"]
goodput_2 = generated_tokens / decode_time
print(f"\n   Method 2 (wall_clock - ttft): decode_time = {b24['wall_clock_s']} - "
      f"{b24['ttft_ms_p50']}/1000 = {decode_time:.4f}s")
print(f"     generated tokens = {b24['batch_size']:.0f} x {b24['gen_len']:.0f} = {generated_tokens:.0f}")
print(f"     goodput = {generated_tokens:.0f} / {decode_time:.4f} = {goodput_2:.1f} tok/s")

print(f"\n   Both independently land in the same ballpark: {goodput_1:.0f} and {goodput_2:.0f} tok/s")
print(f"   vs. reported_tok_s for this row: {b24['reported_tok_s']:.1f} tok/s "
      f"({b24['reported_tok_s']/goodput_1:.1f}x - {b24['reported_tok_s']/goodput_2:.1f}x inflated)")

b48 = next(r for r in long_rows if r["batch_size"] == 48)
print(f"\n-- what REPORT_v0 claimed for batch=48 vs what the log already shows --")
print(f"   REPORT_v0 claim: ~3200 tok/s (naive 2x of the 'best observed' 1607.4 at batch=24)")
print(f"   Actual logged batch=48 row: reported_tok_s={b48['reported_tok_s']}, "
      f"preempted_seqs={b48['preempted_seqs']}, kv_cache_util={b48['kv_cache_util']}")
