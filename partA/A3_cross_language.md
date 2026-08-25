# A3 — Cross-language comparison, corrected

Run with: `python3 partA/cross_language_analysis.py`. Full output in
`partA/results/cross_language_analysis_output.txt`. Uses the 30-sentence
aligned A1 corpus (`partA/corpus/`), both local tokenizers, ratio-of-totals
(not mean-of-ratios), no lowercasing, correct `split()` — i.e. A2's bugs
already fixed.

## Full table

**general tokenizer** (English-heavy, essentially no Kannada/Tamil exposure):

| lang | tokens | tok/word | tok/grapheme | tok/byte | tok/sentence |
|---|---|---|---|---|---|
| eng | 284 | 1.127 | 0.205 | 0.205 | 9.467 |
| hin | 815 | 2.921 | 0.938 | 0.243 | 27.167 |
| kan | 3968 | 20.775 | 4.253 | **1.000** | 132.267 |
| tam | 4557 | 23.734 | 4.361 | **1.000** | 151.900 |

**indic_aware tokenizer** (deliberately balanced across all 4 languages):

| lang | tokens | tok/word | tok/grapheme | tok/byte | tok/sentence |
|---|---|---|---|---|---|
| eng | 284 | 1.127 | 0.205 | 0.205 | 9.467 |
| hin | 815 | 2.921 | 0.938 | 0.243 | 27.167 |
| kan | 1050 | 5.497 | 1.125 | 0.265 | 35.000 |
| tam | 1232 | 6.417 | 1.179 | 0.270 | 41.067 |

## Finding 1 — the report's "this is the script, not the tokenizer" claim is directly falsifiable, and false

REPORT_v0 Section 1 claims the EN/HI fertility gap is *"a property of the
script, not the tokenizer."* Same text, two tokenizers, very different
result:

- Kannada, tok/word ratio to English: **18.43×** (general) vs **4.88×**
  (indic_aware) — a ~3.8× swing from changing only which tokenizer was used.
- Tamil: **21.06×** (general) vs **5.69×** (indic_aware) — a ~3.7× swing.

`general` never saw a single Kannada or Tamil character during training;
`indic_aware` was deliberately trained on a balanced mix of all four
languages. Same script, same input text, wildly different fertility. If
fertility were a property of the script alone, changing the tokenizer
couldn't move the number this much. It's mostly a property of what the
tokenizer's training data contained.

(Caveat on Hindi specifically: both tokenizers were trained on text that
includes the exact 30 Hindi eval sentences — necessary at this small demo
scale — so the Hindi numbers being identical between the two tokenizers
likely partly reflects that shared exposure rather than pure coincidence.
Kannada and Tamil don't have this issue for `general`, which had zero
exposure to either — that's the methodologically cleanest part of this
comparison, and it's also where the effect is largest.)

## Finding 2 — the byte-fallback signature, and what it reveals about tok/word

`general`'s Kannada and Tamil both land at **exactly 1.000 tok/byte**. That's
not a coincidence — it's the literal signature of pure byte-level fallback:
a tokenizer with zero learned merges for a script encodes every UTF-8 byte
as its own token, so tokens == bytes, ratio == 1.000, for *any* text in that
script, regardless of content.

This is useful because it exposes something tok/word hides: under tok/word,
Tamil looks meaningfully worse than Kannada for `general` (23.7 vs 20.8,
a ~14% gap) — but at the byte level, the tokenizer is failing on both
*identically*. The apparent Tamil-vs-Kannada gap under tok/word isn't a
tokenization-quality difference at all; it's just that my Tamil sentences
happen to use somewhat more whitespace-delimited "words" for the same
content than my Kannada ones do. tok/word is measuring a fact about writing
convention, not about the tokenizer.

## Finding 3 — which denominator should drive a routing/cost decision

**tok/byte.** Reasoning:

A routing or capacity decision ultimately asks one question: *for a given
amount of input, how many tokens will this cost us?* The denominator that
answers that has to hold "amount of input" constant across languages in a
way that generalizes to arbitrary real traffic — not just to a hand-built
parallel corpus where I've made sure the sentences match.

- **tok/word fails this test.** "Word" isn't a comparable unit across
  language families. Kannada and Tamil are agglutinative — a single
  whitespace-delimited word often carries what English spreads across
  several words (case markers, postpositions, verb agreement folded onto
  the stem). tok/word is the *largest and most exaggerated* ratio in every
  row above precisely because it's conflating "how tokenization-friendly is
  this script" with "how does this language's morphology use whitespace" —
  it's the same conceptual error A2 flagged in `fertility.py` itself, just
  visible again here at the cross-language level.
- **tok/grapheme is better but still not neutral.** It fixes the
  codepoint-vs-visible-character issue from A2, but different scripts still
  pack different amounts of phonetic/semantic content per visible
  character (Devanagari conjuncts, for instance), so equal grapheme counts
  still don't mean equal content.
- **tok/sentence is a good internal-validity check, not a general metric.**
  It works *here* because I built genuinely parallel sentences, so "same
  sentence index" really does mean "same content." It doesn't generalize:
  a production router sees arbitrary, unmatched user messages, and "one
  sentence" isn't a fixed amount of anything across languages or writers.
- **tok/byte is what actually gets billed and transmitted.** Bytes are the
  unit a serving system already measures — request size over the wire,
  storage, bandwidth — independent of script or morphology. For a fixed
  byte budget (which is closer to what real traffic actually constrains),
  tok/byte directly answers "how many tokens will this consume." It isn't
  perfectly content-neutral either (UTF-8 uses 1 byte/codepoint for Latin
  script vs. 3 bytes/codepoint for the Devanagari/Kannada/Tamil blocks used
  here), but it's the denominator that's closest to what a capacity or cost
  model actually needs to hold constant, and it's the one that (Finding 2)
  correctly shows Kannada and Tamil as *equally* mishandled by `general`
  rather than inventing a spurious ranking between them.

Under tok/byte, the honest picture is: `general` costs ~4.9× more per byte
for Kannada/Tamil than English, and ~1.2× more for Hindi — both real, both
worth routing decisions, but nowhere near the 18–24× that tok/word implies,
and nowhere near uniform across the three Indic languages the way
REPORT_v0's single EN/HI number suggested.
