# B1 — KV-cache bytes/token and max concurrent 4096-token sequences

Computed programmatically in `capacity_and_throughput.py`; full output in
`results/capacity_and_throughput_output.txt`. From `model_spec.md` alone,
before looking at the log.

## (a) KV-cache bytes/token

```
KV bytes/token = 2 (K and V) x layers x kv_heads x head_dim x dtype_bytes
               = 2 x 28 x 8 x 128 x 2
               = 114,688 bytes/token  (= 112 KiB/token exactly)
```

All five inputs come straight from `model_spec.md`: 28 layers, 8 KV heads
(this model uses GQA — 8 KV heads vs. 24 query heads), head_dim 128, fp16
KV cache (2 bytes/element), and 2 for storing both K and V.

## (b) Max concurrent 4096-token sequences

```
weight_bytes = 4.2e9 params x 2 bytes (fp16) = 8.4e9 bytes

usable_mem = 24 GB x gpu_memory_utilization(0.92)
available_for_kv = usable_mem - weight_bytes - non_kv_overhead(1.6 GB)
max_tokens = available_for_kv / 114,688
max_seqs = floor(max_tokens / 4096)
```

This has a real unit ambiguity worth naming rather than hiding: does
`model_spec.md`'s "24 GB" mean decimal GB (10⁹ bytes, the marketing/spec
convention) or GiB (2³⁰ bytes, what CUDA/`nvidia-smi` and memory allocators
actually report)? I computed both:

| interpretation | available for KV | max tokens | max concurrent 4096-tok seqs |
|---|---|---|---|
| decimal GB (10⁹) | 1.208×10¹⁰ bytes | 105,329 | **25** |
| GiB (2³⁰) | 1.359×10¹⁰ bytes | 118,497 | **28** |

A 12% swing (25 vs. 28) just from which byte convention you assume — this
is exactly the kind of thing that looks like a rounding footnote until it's
the difference between "we have headroom" and "we're already over."

## Checked against the log — and it resolves the ambiguity

`bench_log.csv`'s long-prompt sweep (`prompt_len=3584, gen_len=512` — total
context 4096, i.e. exactly `max_model_len`) starts showing `preempted_seqs`
> 0 between batch=24 (0 preempted, `kv_cache_util`=0.93) and batch=32 (7
preempted). If a scheduler admits `batch_size` requests but can only
actually run `true_capacity` of them concurrently, the rest get preempted:
`preempted_seqs ≈ batch_size − true_capacity`.

```
batch=32: 32 - 7  preempted = 25
batch=48: 48 - 23 preempted = 25
```

Both point to **25**, independently of each other and of my arithmetic —
which matches the decimal-GB interpretation exactly and misses the GiB one
by 3. That's the practical answer to the units question: this serving
stack's `gpu_memory_utilization` is evidently being applied against a
decimal-GB reading of device memory, not GiB. I wouldn't have known which
convention was right from the spec alone — only checking against the log
tells you.

**Answer: ~112 KiB/token, ~25 concurrent 4096-token sequences** is the real
ceiling on this GPU for this model.
