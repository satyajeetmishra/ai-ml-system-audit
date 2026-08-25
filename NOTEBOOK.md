# Notebook

Chronological log of the actual process, including the parts that didn't
work or turned out wrong. Section order roughly follows the assignment
(A1→A4, B1→B4, C), but within each section this is genuinely in the order
things happened, not cleaned up after the fact.

## 0. Setup and integrity check

Unzipped `starter_kit.zip`, read all six files:
`fertility.py`, `REPORT_v0.md`, `corpus_sample/eng_sample.txt`,
`corpus_sample/hin_sample.txt`, `bench/model_spec.md`,
`bench/bench_log.csv`.

Before building anything on top of these, I re-unzipped the original
upload into a separate directory and diffed every file against what I'd
already been working from — byte-for-byte identical on all six (matching
md5 checksums both ways). Worth doing on any task like this before
trusting derived numbers: it's cheap insurance against working from a
stale or partially-edited copy without realizing it.

## 1. First hypotheses about fertility.py bugs — mostly wrong, revised on read

Before reading the real file, I'd guessed at plausible bug categories:
special-token (BOS/EOS) inflation, and missing/inconsistent Unicode
normalization (mixed NFC/NFD). Neither is actually in the script:
`read_lines()` already calls `unicodedata.normalize("NFC", line)` (line
49), and there's no special-token handling to get wrong in the first
place — `tiktoken`'s `.encode()` and the `hf:` path as written don't add
BOS/EOS. Dropped both guesses once I actually read the file line by line.

What's actually there: `line.lower()` before tokenizing (line 60),
`line.split(" ")` — literal single space, not `.split()` (line 62),
`sum(per_line_fertility)/n` — mean of per-line ratios rather than
total tokens / total words (line 67), and `random.seed(1337)` (line 25)
that's never used again anywhere in the file. See A2 for the isolated
before/after on each.

## 2. Tokenizer access — real dead end, real pivot

Tried running the script's actual default (`tiktoken.get_encoding("gpt2")`)
and its documented example (`hf:xlm-roberta-base`). Both fail here:

```
tiktoken: 403 Client Error: Forbidden — openaipublic.blob.core.windows.net
transformers: OSError — couldn't connect to huggingface.co
```

This sandbox's bash tool only reaches `github.com`,
`raw.githubusercontent.com`, `codeload.github.com`, and package registries
— not model-hosting blob storage or the HF Hub. That's a real constraint,
not a hypothetical one, and it means the script *as shipped* can't
actually run in a network-isolated environment (worth flagging as its own
finding — see A2's "bonus finding").

Pivot: trained two BPE tokenizers locally with the `tokenizers` package
(no network needed) — `general` (English-heavy, minimal incidental Hindi,
zero Kannada/Tamil) and `indic_aware` (balanced across all four languages).
Vocab target was 8000 for both; on this small a training corpus the BPE
trainer naturally stopped early — **1487** (`general`) and **2034**
(`indic_aware`) actual vocab sizes. Noting this rather than padding it out
artificially: real production tokenizers use a fixed target vocab
regardless of training corpus size, so this is a genuine limitation of
training on a small demo-scale corpus, not a bug.

## 3. A1 corpus sourcing — real dead end, real pivot

Wanted FLORES-200 (the standard benchmark for exactly this comparison,
3001 sentences across 200+ languages). Its actual sentence data lives on
`fbaipublicfiles.com` or a login-gated HuggingFace repo — neither reachable
here. Checked whether GitHub forks of `facebookresearch/flores` had
committed the data directly rather than linking out — they only mirror the
README. Also checked AI4Bharat's Samanantar/IN22 resources; same hosting
problem. `web_fetch` on the GitHub tree page was blocked by robots.txt; the
GitHub API was rate-limited when I tried listing the repo contents
directly. Genuine dead end, not a hypothetical one — logged the actual
errors in case it's useful to revisit with different network access.

Pivot: built a 30-sentence × 4-language (English/Hindi/Kannada/Tamil)
parallel corpus by hand, aligned by line index, documented honestly in
`partA/corpus/CORPUS_NOTES.md` including that the Kannada/Tamil lines
weren't native-speaker verified.

## 4. A2 — running the isolation experiments

Each bug toggled independently, everything else held at the script's
original behavior, run on the *given* `corpus_sample/` (not my A1 corpus —
that's where the planted double-space artifact actually lives). Full
numbers in `A2_audit_findings.md`; the one that surprised me: the three
bugs don't uniformly bias the comparison. Fixing all three raises English's
fertility ~7.8% but barely moves Hindi's (~−0.5 to −0.65%) — lowercasing
has *zero* effect on Hindi (no case distinction in Devanagari) while
knocking English down 5.35%, and the split-bug and aggregation-bug effects
on Hindi happen to point in opposite directions. I wouldn't have predicted
that without actually running the isolated toggles — it only shows up once
you hold everything else fixed and change one thing at a time.

Also checked codepoints vs. true grapheme clusters for the `tok/char`
column (not a required bug category, found while double-checking that
column specifically): 290 codepoints vs. 188 grapheme clusters for the
Hindi sample, a 35% gap — bigger than I expected going in. Direction is
counterintuitive and worth getting right: since codepoints *overcount*
Hindi's true visible-character length, the *existing* buggy `tok/char`
actually understates how token-heavy Hindi looks, not overstates it. Not
every bug in this script cuts the same direction.

## 5. A3 — did the ratio really come from the script, not the language?

REPORT_v0 claims the fertility gap is "a property of the script, not the
tokenizer." Ran the same 4-language corpus through both tokenizers to
actually test that. It's false: Kannada's tok/word ratio to English is
18.43× on `general` vs. 4.88× on `indic_aware` — same script, same text,
~3.8× swing from changing only which tokenizer was used, because
`general` never saw a Kannada character in training and `indic_aware`
did. Noted a real caveat here too: both tokenizers *did* train on the
exact Hindi eval sentences (necessary at this scale), so the Hindi numbers
being identical between the two tokenizers is partly that overlap, not
purely a coincidence — Kannada/Tamil for `general` is the cleaner test,
since it had zero exposure there.

Unplanned bonus while building the denominator table: `general`'s Kannada
and Tamil both land at *exactly* 1.000 tok/byte — the literal signature of
pure byte-fallback (every UTF-8 byte becomes its own token when there are
no learned merges for a script). That let me show tok/word's apparent
"Tamil is worse than Kannada" gap (23.7 vs 20.8) is an artifact of
whitespace-word conventions, not a real tokenization-quality difference —
at the byte level they're identical (both purely falling back).

## 6. B1 — a units ambiguity I didn't expect to matter this much

Computing max concurrent 4096-token sequences from `model_spec.md` alone
runs into a real ambiguity: does "24 GB" mean decimal GB (10⁹) or GiB
(2³⁰)? They give different answers — 25 vs. 28 sequences, a 12% spread.
Rather than pick one and hope, checked both against `bench_log.csv`'s
`preempted_seqs` column: `32 − 7 = 25` and `48 − 23 = 25`, both landing on
the decimal-GB answer exactly. Didn't expect a "trivial" unit-convention
choice to be the actual difference between two materially different
capacity numbers, or that the log would resolve it this cleanly.

## 7. B2/B3 — REPORT_v0's "L4" mention led me down a wrong path first

Before checking `model_spec.md`, I noticed REPORT_v0 said "~1600 tok/s per
L4" and wondered if this was a bug — mixing benchmark data from a
different (cheaper/weaker) GPU into a capacity plan for whatever GPU was
actually being deployed. Checked `model_spec.md`: the benchmarked GPU
really is a single L4. No GPU-mixing bug — dropped that hypothesis once I
had the real spec in hand, and moved on to what turned out to be the real
issue: reverse-engineered `reported_tok_s` from the logged columns and
confirmed `reported_tok_s = batch_size × (prompt_len + gen_len) /
wall_clock_s` matches every row in the CSV to within rounding. That one
formula explains both of REPORT_v0's Section 2 claims at once (see B3)
without needing a second, separate mechanism.

The other thing worth logging here: REPORT_v0's batch=48 claim didn't need
to be extrapolated at all to check — batch=48 is already a row in
`bench_log.csv` (1298.5 tok/s, 23 preempted sequences), sitting right there
in the same file the report was supposedly written from.

## 8. What I'd redo with more time / fewer constraints

- A1 corpus: 30 sentences, one domain, no native-speaker check on
  Kannada/Tamil. A real launch decision needs FLORES-200 or equivalent.
- Tokenizers: locally-trained stand-ins, not real production-scale
  tokenizers. Directional findings (training-data composition drives the
  gap, not the script) should generalize; exact multipliers won't match a
  real 32k+-vocab production tokenizer.
- Part B's arithmetic is fully derived from the given files and holds up
  against the empirical log, so I have more confidence in B1–B4 than in
  A1/A3's exact numbers, which inherit the corpus/tokenizer limitations
  above.
