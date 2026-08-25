# AI usage

I used Claude for this entire submission — exploring the starter kit,
designing and running the experiments, building the corpus and tokenizers,
and drafting the write-ups. This is an honest account of where that helped
and, more importantly, where it could mislead me if I walked into the
defense just trusting the output instead of checking it myself.

## Where it genuinely helped

- **Systematic bug isolation.** Toggling one variable at a time (lowercase
  on/off, split method, aggregation method) across two languages and two
  tokenizers is a lot of careful bookkeeping to do by hand without making a
  transcription error somewhere. Having it done in code, printed in full,
  and saved to `results/` means I can re-run any single number myself.
- **Catching things I wasn't specifically looking for.** The 35% gap
  between codepoints and grapheme clusters, and the fact that Kannada and
  Tamil land at *exactly* 1.000 tok/byte under the English-heavy tokenizer
  (the byte-fallback signature) — both came out of running the full table
  rather than checking a specific hypothesis, and both turned into real
  findings I wouldn't have thought to go looking for by hand.
- **Volume.** Two trained tokenizers, a 120-line parallel corpus, and full
  before/after tables across two tokenizers × four denominators × four
  languages is more exhaustive than I'd have had time to build and check
  by hand in the time available.

## Where it could mislead — and what I'm actually checking before the defense

- **The Kannada and Tamil translations are AI-written and I have not had
  them checked by a native speaker.** I can read Hindi confidently; my
  ability to independently verify Kannada/Tamil sentence quality is
  limited. If asked to defend a specific translation choice live, I need
  to be upfront that this is a real gap, not something I can wing.
- **The absolute fertility numbers are tied to two tokenizers *I* trained
  on a few hundred sentences, not `gpt2` or any real production
  tokenizer** — those weren't reachable from the sandbox (see NOTEBOOK.md).
  The mechanism (training-data composition drives the gap) should hold
  generally; the specific multipliers (e.g., "4.88× for Kannada") are
  demo-scale numbers, not numbers I'd want to defend as production-ready
  without rerunning against a real tokenizer and a real benchmark corpus.
  I'm treating the *direction* of every finding as load-bearing and the
  *exact number* as illustrative — I need to be able to say that
  distinction out loud, not just hope nobody asks.
- **Confident prose isn't the same as a number I can re-derive.** Before
  the defense, I'm re-doing the KV-cache arithmetic (B1), the
  `reported_tok_s` formula check (B2/B3), and at least one of the two
  goodput derivations (B3) by hand, from the raw numbers in
  `model_spec.md` and `bench_log.csv`, without looking at the scripts —
  specifically because "modify the code live" and "answer counterfactuals"
  are explicit parts of the defense format, and I can't do either of those
  from memory of what a script printed.
- **Small samples make confident-sounding claims easy to write.** 30
  sentences, 10 given corpus lines — both small enough that I should be
  ready to say "this is directionally right but not statistically tight"
  rather than defend a specific decimal as if it were precise.
- **I had Claude independently re-verify the starter kit files it was
  working from against a fresh unzip of my original upload before it built
  anything on top of them** (see NOTEBOOK.md section 0). I'm noting this
  because it's a real risk with any AI-assisted analysis of files, not
  just this one — it's easy for a summary or a half-remembered version of
  a file to drift from the actual source over a long session, and worth
  checking rather than assuming.

## What I'd do differently with more time

Get an actual native Kannada and Tamil speaker to review the A1 corpus
before treating the specific numbers as final, and re-run A2/A3 against a
real tokenizer (would need network access this sandbox didn't have) rather
than my own small trained ones.
