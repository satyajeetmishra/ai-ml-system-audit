# A2 — Audit of `fertility.py`

Run with: `python3 partA/audit_experiments.py` (uses the given
`starter_kit/corpus_sample/{eng,hin}_sample.txt` and our two locally-trained
tokenizers — see `partA/tokenizers/`). Full output in
`partA/results/audit_experiments_output.txt`.

Every number below is from that actual run, not hand-calculated.

## Code bug #1 — `line.lower()` before tokenizing (line 60)

**Claim:** lowercasing is applied identically to English and Hindi in the
code, but has a completely different real effect on each, because
Devanagari has no case distinction and Latin script does. That makes the
cross-language *comparison* asymmetric, not just each number individually.

**Command:** toggle `lowercase=True/False`, everything else held at the
script's original behavior (`split(" ")`, mean-of-ratios).

**Before/after:**

| lang | tokenizer | lower=True (script as-is) | lower=False | change |
|---|---|---|---|---|
| eng | general | 2.2354 | 2.3551 | **+5.35%** |
| eng | indic_aware | 2.2354 | 2.3551 | **+5.35%** |
| hin | general | 3.3168 | 3.3168 | **0.00%** |
| hin | indic_aware | 3.2468 | 3.2468 | **0.00%** |

**Why this proves the claim:** the effect on Hindi is exactly zero to six
decimal places, on both tokenizers, while English moves 5.35% on both. That
isn't "lowercasing helps a little less for Hindi" — it's zero, because
`str.lower()` is a no-op on every Devanagari codepoint in this corpus. A
preprocessing step described as "so casing doesn't add noise to the
comparison" (the code's own comment) in fact adds *asymmetric* noise: it
quietly changes what's being measured for one language in the pair and not
the other, which means part of the reported EN/HI gap is this step, not the
tokenizer.

## Code bug #2 — `words = line.split(" ")` (line 62)

**Claim:** splitting on a literal single space (instead of `.split()`,
which splits on any whitespace and collapses runs) silently creates
spurious empty-string "words" wherever a line has a double space —
inflating the word count and deflating fertility.

**Direct evidence — the given corpus has this exact artifact planted in
both files:**

```
[eng line 7] split(" ") -> 8 words (incl. 1 empty string) | split() -> 7 words
    raw: 'Please keep the books  in the cupboard.'
[hin line 10] split(" ") -> 6 words (incl. 1 empty string) | split() -> 5 words
    raw: 'किताबें  अलमारी में रखी हैं।'
```

**Before/after (aggregate, all 10 lines):**

| lang | tokenizer | split(" ") (script as-is) | split() | change |
|---|---|---|---|---|
| eng | general | 2.2354 | 2.2729 | **+1.68%** |
| eng | indic_aware | 2.2354 | 2.2729 | **+1.68%** |
| hin | general | 3.3168 | 3.3835 | **+2.01%** |
| hin | indic_aware | 3.2468 | 3.3101 | **+1.95%** |

**Why this proves the claim:** on a 10-line corpus, a single planted double
space measurably moves the aggregate by ~1.7–2.0%. On real production
traffic — which routinely has double spaces, tabs, and stray whitespace
from copy-paste — this would be a live, silent, corpus-dependent
undercount, not a one-off toy artifact.

## Conceptual note — mean of per-line ratios vs. ratio of totals (line 67)

**Claim:** `sum(per_line_fertility) / n` (mean of ratios) is not the same
number as `total_tokens / total_words` (ratio of totals), and the code
computes the former without saying so.

**Before/after:**

| lang | tokenizer | mean-of-ratios (script as-is) | ratio-of-totals | change |
|---|---|---|---|---|
| eng | general | 2.2354 | 2.2532 | +0.79% |
| eng | indic_aware | 2.2354 | 2.2532 | +0.79% |
| hin | general | 3.3168 | 3.2419 | −2.26% |
| hin | indic_aware | 3.2468 | 3.1774 | −2.14% |

**I'm flagging this as a minor, checked-and-real finding, not a headline
one.** The effect is small on this corpus (line lengths don't vary enough
to make mean-of-ratios diverge sharply from ratio-of-totals) — under 2.5%
either direction. It's worth naming because it's a real, silent statistical
choice with no comment explaining it, and it moves English and Hindi in
*opposite* directions, which matters for the next point.

## Compounding effect — the three bugs together don't cancel evenly

| lang | original (all 3 as-is) | all 3 fixed | net change |
|---|---|---|---|
| eng (either tok) | 2.2354 | 2.4103 | **+7.82%** |
| hin (general) | 3.3168 | 3.2951 | −0.65% |
| hin (indic_aware) | 3.2468 | 3.2295 | −0.53% |

This is the finding I did not expect going in and only found by actually
running the isolated toggles: the three bugs **compound for English**
(lowercase −5.35%, split −1.68%, aggregation −0.79%, all pushing the
reported number down) but **nearly cancel for Hindi** (split +2%, mean-of-
ratios −2.3%, lowercase exactly 0%). Net effect: fixing all three bugs
raises English's fertility by ~7.8% while barely moving Hindi's — which
means the reported EN/HI *ratio* is inflated by the bugs, independent of
which tokenizer is used. Using our indic_aware tokenizer as one concrete
example: buggy ratio = 3.2468/2.2354 = **1.452×**; fixed ratio =
3.2295/2.4103 = **1.340×**. (These are *our* tokenizer's numbers, not
`gpt2`'s — gpt2 isn't reachable here, see NOTEBOOK.md — but the direction
and mechanism apply regardless of which tokenizer is used, since none of
these three bugs are tokenizer-specific.)

## "Looks suspicious but is fine" — `random.seed(1337)` (line 25)

**Claim:** the seed looks like it could be hiding sampling, shuffling, or
cherry-picking, but the `random` module is never actually called anywhere
else in the file.

**Static check** — every line in the file mentioning `random`:
```
import random
random.seed(1337)  # reproducibility
```
That's the complete list. No `.shuffle`, `.sample`, `.choice`, nothing.

**Empirical check** — since a fixed seed with no actual random call can't
affect anything, I confirmed by literally reordering the input and
re-running:

```
eng: original-order=2.235444  shuffled=2.235444  reversed=2.235444  (identical: True)
hin: original-order=3.246786  shuffled=3.246786  reversed=3.246786  (identical: True)
```

**Why this proves the claim:** fertility is a mean over all lines, so line
order provably cannot change it — shuffling with a *different* seed (42,
not the script's own 1337) and full reversal both reproduce the original
number to the 6th decimal place. This is vestigial, most likely left over
from an earlier version of the script that did sample the corpus. Flagging
it as a real bug would have been a false flag under the assignment's
evidence rule (−5); the evidence here is that it costs nothing to leave in
and does nothing either way.

## Bonus finding — `chars = len(line)` counts codepoints, not visible characters (line 63)

Not one of the required categories, but found while checking the `tok/char`
column, and the size of the effect surprised me enough to include it.

`len(line)` counts Unicode codepoints. Devanagari vowel signs (matras) are
separate combining codepoints attached to a preceding consonant — one
*visible* character can be 2 codepoints. I compared codepoints against true
extended grapheme clusters (Unicode UAX #29, via `regex`'s `\X`):

| lang | codepoints | grapheme clusters | difference |
|---|---|---|---|
| eng (10 lines) | 448 | 448 | 0 (plain ASCII has no combining marks) |
| hin (10 lines) | 290 | 188 | **−35.17%** |

**Direction matters here, and it's counterintuitive:** since codepoints
*overcount* Hindi's true visible-character length relative to grapheme
clusters, the *existing* `tok/char` column is computed against an
inflated denominator — meaning it currently makes Hindi's tokens-per-
character look **better** (lower) than a grapheme-cluster-based version
would. Correcting this bug would make Hindi's `tok/char` number look
*worse*, not better. Not every bug in this script cuts in the direction of
"the problem was overstated" — this one goes the other way, and REPORT_v0's
claim that tok/char "confirms" the per-word number (Section 1, point 2)
is weaker evidence than it looks for an independent reason: see A3/A4.

## Bonus finding — the script's own default tokenizer isn't reproducible here

Not a bug in the fertility logic itself, but a real, tested finding:
`tiktoken.get_encoding("gpt2")` (the script's default) and
`hf:xlm-roberta-base` (its documented multilingual example) both require
live network access to hosts outside this sandbox's allowlist. Direct test:

```
$ python3 -c "import tiktoken; tiktoken.get_encoding('gpt2')"
requests.exceptions.HTTPError: 403 Client Error: Forbidden for url:
https://openaipublic.blob.core.windows.net/gpt-2/encodings/main/vocab.bpe

$ python3 -c "from transformers import AutoTokenizer; AutoTokenizer.from_pretrained('xlm-roberta-base')"
OSError: We couldn't connect to 'https://huggingface.co' ...
```

The script as shipped can't actually be *run* in a network-isolated
environment (CI, an air-gapped box, or — concretely — this sandbox) without
modification. That's an operational robustness gap worth flagging on its
own, separate from whether the fertility math is right.

## What I checked and did NOT flag

I checked for missing/inconsistent Unicode normalization, since that's a
classic tokenizer-fertility bug — the script already calls
`unicodedata.normalize("NFC", line)` in `read_lines()` (line 49), so this
is *not* a bug here and I'm not claiming it as one.
