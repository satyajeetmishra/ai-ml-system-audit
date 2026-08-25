# A4 — Recommendation memo

## Corrected headline numbers

REPORT_v0 claimed Hindi is **5.89× worse** than English and recommended
budgeting a flat **6×** for all Indic traffic. Both the EN/HI script's bugs
(A2) and the choice of denominator (A3) were driving that number up. On the
byte-normalized metric (the one that should drive a cost decision — see
A3), and comparing our actual English-heavy tokenizer against a balanced
one trained the same way:

| lang | current-tokenizer-like (tok/byte vs eng) | balanced-tokenizer-like (tok/byte vs eng) |
|---|---|---|
| Hindi | 1.18× | 1.18× |
| Kannada | 4.87× | 1.29× |
| Tamil | 4.87× | 1.32× |

Two things change the picture: Hindi was never really a 6× problem (1.18×
on bytes) — it looked large mainly because `fertility.py`'s bugs and the
tok/word denominator both inflated it (A2, A3). Kannada and Tamil, which
REPORT_v0 never measured at all, are the real cost story — and the gap is
overwhelmingly closable by tokenizer vocabulary coverage, not fixed by the
script (A3 Finding 1): the same text costs 4.87× on a tokenizer that's
never seen the script, and 1.3× on one trained with it included.

## Routing recommendation

1. **Stop using a flat multiplier for "Indic traffic."** Hindi, Kannada,
   and Tamil don't have the same cost profile — treating them as one
   bucket over- or under-charges depending on which language dominates the
   mix.
2. **Root-cause fix: extend tokenizer vocabulary coverage for Kannada,
   Tamil, and other under-represented scripts**, not just widen the token
   budget. The gap is a training-data-composition problem (A3), and a
   budget increase is a permanent tax that treats the symptom every
   request, forever, instead of fixing the cause once.
3. **Until that ships**, use byte-normalized ratios for interim
   cost/routing decisions, not tok/word — tok/word overstates the gap by
   roughly 4–5× for Kannada/Tamil and 2× for Hindi on this data (A3), which
   would lead to badly miscalibrated pricing or over-conservative capacity
   reservations.

## Biggest caveat

The corpus behind these numbers is 30 hand-built sentences (see
`partA/corpus/CORPUS_NOTES.md`) — enough to demonstrate the mechanism and
get the right order of magnitude, not enough to finalize a pricing or
capacity number. The Kannada and Tamil translations weren't verified by a
native speaker. Before this drives an actual routing/pricing change, re-run
this same analysis on a real benchmark (FLORES-200 or equivalent) with the
production tokenizer, not our two small locally-trained stand-ins — real
gpt2/production-scale tokenizers weren't reachable from this environment
(see NOTEBOOK.md), so the *direction* of these findings should hold but the
*exact multipliers* should not be treated as final.

## One production monitoring metric

**Byte-fallback rate per language**: the share of tokens in a request that
are single raw UTF-8 bytes rather than learned multi-byte merges, tracked
per detected input language. This is the direct, mechanism-level signal
behind Finding 2 in A3 — a script with poor vocabulary coverage shows up as
tokens-per-byte pinned near 1.0. It's more diagnostic than watching
raw cost or latency drift, because it points straight at "this language
needs vocabulary coverage" rather than requiring someone to re-derive that
from a cost anomaly after the fact, and it would have caught the Kannada/
Tamil gap this audit found even before anyone shipped traffic in those
languages.
