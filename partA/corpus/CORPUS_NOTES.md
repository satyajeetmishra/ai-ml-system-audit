# A1 — Eval corpus notes

## What this is

30 parallel sentences × 4 languages: English (`eng.txt`), Hindi (`hin.txt`),
Kannada (`kan.txt`), Tamil (`tam.txt`). English + Hindi + 2 Dravidian
languages, as required. Lines are aligned by index — line *N* means the same
thing in all four files. 120 lines total.

## Domain

Everyday + light workplace register: meetings, commutes, weather, family,
food, deadlines, office logistics. Sentence length ranges from ~5 words
("What time does the office open tomorrow?") to ~20-word compound/subordinate
constructions ("When it is not too hot, I usually walk to work..."), so the
corpus has some real spread in fertility rather than being uniformly short.

## Sourcing — what I tried first

I looked for a real, professionally-translated parallel set before building
one by hand, since that's clearly the better source if reachable. FLORES-200
(842 articles, 3001 sentences/language, the standard academic benchmark for
exactly this kind of comparison) was the first choice. Its actual sentence
data is hosted on `fbaipublicfiles.com` or a login-gated HuggingFace repo —
neither reachable from this environment (only `github.com`,
`raw.githubusercontent.com`, `codeload.github.com`, and package registries
are reachable here). GitHub forks of `facebookresearch/flores` mirror the
README, not the sentence files. I also checked AI4Bharat's Samanantar/IN22
resources; same hosting problem. I was not able to reach a real corpus host
from this sandbox, so I built this set by hand instead.

## Preprocessing

Plain UTF-8 text, one sentence per line, no header. No case-folding, no
Unicode normalization applied at construction time (each language typed
directly, not converted from another form) — normalization is something
`fertility.py`/my audit scripts apply at *analysis* time, not baked into the
source files. Verified: exactly 30 lines per file, valid UTF-8, no stray
double-spaces or trailing whitespace (that artifact is deliberately present
in the *given* `corpus_sample/` files for A2's bug isolation, not here).

## Limitations

This is a small, single-author, single-domain corpus, not a substitute for a
real benchmark like FLORES-200. Concretely: (1) 30 sentences per language is
enough to see a fertility signal but not enough for tight confidence
intervals — a single unusual sentence can move the average noticeably;
(2) it covers one register (everyday/workplace) and misses others a
production system would see — code-mixed text, formal documents, social
media; (3) the Hindi translations are ones I'm reasonably confident in, but
the Kannada and Tamil lines were written by me without native-speaker
verification — they should read as natural, grammatical sentences, but I
can't rule out occasional phrasing a native speaker would word differently.
None of that affects the *methodology* this corpus supports (comparing
tokenizers/denominators against each other on the same fixed text), but it
does mean the specific fertility numbers below are indicative, not
production-grade, and a real launch decision should re-run this analysis on
FLORES-200 or an equivalent vetted set before being finalized.
