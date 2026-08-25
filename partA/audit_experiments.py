#!/usr/bin/env python3
"""
audit_experiments.py -- A2 evidence-rule experiments for fertility.py

For each claimed flaw, this holds everything else fixed and toggles ONE
thing at a time, so the printed before/after numbers isolate that flaw's
own effect (per the assignment's evidence rule: exact command, before/after
numbers, one sentence on why it proves the claim).

Run on the GIVEN starter_kit/corpus_sample/ files (eng_sample.txt,
hin_sample.txt) -- that's where the planted double-space artifact lives,
and it's the actual input the original script/report used.

Tokenizers: our own locally-trained tokenizer_general.json and
tokenizer_indic_aware.json (see ../tokenizers/train_tokenizers.py and
NOTEBOOK.md for why: tiktoken's gpt2 encoding and any hf: model both
require network access this sandbox doesn't have).
"""
import os
import sys
import unicodedata
import random
import regex
from tokenizers import Tokenizer

ROOT = os.path.dirname(os.path.abspath(__file__))
GIVEN_CORPUS = os.path.join(ROOT, "..", "given_starter_kit", "corpus_sample")
TOK_DIR = os.path.join(ROOT, "tokenizers")

tok_general = Tokenizer.from_file(os.path.join(TOK_DIR, "tokenizer_general.json"))
tok_indic = Tokenizer.from_file(os.path.join(TOK_DIR, "tokenizer_indic_aware.json"))
TOKENIZERS = {"general": tok_general, "indic_aware": tok_indic}


def encode(tok, s):
    return tok.encode(s).ids


# ---- exact reimplementation of fertility.py's read_lines() (unchanged) ----
def read_lines(path):
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            line = unicodedata.normalize("NFC", line)  # already in original -- not a bug
            lines.append(line)
    return lines


# ---- generalized analyze(): each flaw is a toggle, default = ORIGINAL script behavior ----
def analyze(lines, tok, lowercase=True, split_mode="buggy", agg="mean_of_ratios"):
    per_line_fert = []
    total_tokens = 0
    total_words = 0
    for line in lines:
        l = line.lower() if lowercase else line
        tokens = encode(tok, l)
        if split_mode == "buggy":
            words = l.split(" ")   # ORIGINAL: literal single-space split
        else:
            words = l.split()      # FIX: any whitespace, collapses runs, no empty strings
        per_line_fert.append(len(tokens) / len(words))
        total_tokens += len(tokens)
        total_words += len(words)
    mean_of_ratios = sum(per_line_fert) / len(per_line_fert)
    ratio_of_sums = total_tokens / total_words
    return mean_of_ratios if agg == "mean_of_ratios" else ratio_of_sums


def pct(new, old):
    return (new - old) / old * 100


def divider(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


eng_lines = read_lines(os.path.join(GIVEN_CORPUS, "eng_sample.txt"))
hin_lines = read_lines(os.path.join(GIVEN_CORPUS, "hin_sample.txt"))
print(f"Loaded {len(eng_lines)} eng lines, {len(hin_lines)} hin lines from GIVEN corpus_sample/")

# =====================================================================
# EXPERIMENT 1: lowercase bug
# =====================================================================
divider("EXPERIMENT 1 -- lower() applied before tokenizing (fertility.py line 60)")
print(f"{'lang':<6}{'tok':<12}{'baseline (lower=True)':>24}{'fixed (lower=False)':>22}{'% change':>12}")
for lang, lines in [("eng", eng_lines), ("hin", hin_lines)]:
    for tname, tok in TOKENIZERS.items():
        base = analyze(lines, tok, lowercase=True, split_mode="buggy", agg="mean_of_ratios")
        fixed = analyze(lines, tok, lowercase=False, split_mode="buggy", agg="mean_of_ratios")
        print(f"{lang:<6}{tname:<12}{base:>24.4f}{fixed:>22.4f}{pct(fixed, base):>11.2f}%")

# =====================================================================
# EXPERIMENT 2: split(" ") vs split() -- the planted double-space
# =====================================================================
divider("EXPERIMENT 2 -- split(\" \") literal-space split (fertility.py line 62)")
# show the actual empty-string artifact directly
for lang, path in [("eng", "eng_sample.txt"), ("hin", "hin_sample.txt")]:
    raw_lines = read_lines(os.path.join(GIVEN_CORPUS, path))
    for i, l in enumerate(raw_lines):
        buggy_words = l.split(" ")
        fixed_words = l.split()
        if len(buggy_words) != len(fixed_words):
            print(f"  [{lang} line {i+1}] split(\" \") -> {len(buggy_words)} words "
                  f"(incl. {buggy_words.count('')} empty string(s)) | "
                  f"split() -> {len(fixed_words)} words")
            print(f"    raw: {l!r}")

print(f"\n{'lang':<6}{'tok':<12}{'baseline split(\" \")':>22}{'fixed split()':>16}{'% change':>12}")
for lang, lines in [("eng", eng_lines), ("hin", hin_lines)]:
    for tname, tok in TOKENIZERS.items():
        base = analyze(lines, tok, lowercase=True, split_mode="buggy", agg="mean_of_ratios")
        fixed = analyze(lines, tok, lowercase=True, split_mode="fixed", agg="mean_of_ratios")
        print(f"{lang:<6}{tname:<12}{base:>22.4f}{fixed:>16.4f}{pct(fixed, base):>11.2f}%")

# =====================================================================
# EXPERIMENT 3: mean-of-ratios vs ratio-of-sums
# =====================================================================
divider("EXPERIMENT 3 -- mean of per-line ratios vs ratio of totals (fertility.py line 67)")
print(f"{'lang':<6}{'tok':<12}{'mean_of_ratios (orig)':>24}{'ratio_of_sums':>16}{'% change':>12}")
for lang, lines in [("eng", eng_lines), ("hin", hin_lines)]:
    for tname, tok in TOKENIZERS.items():
        base = analyze(lines, tok, lowercase=True, split_mode="buggy", agg="mean_of_ratios")
        fixed = analyze(lines, tok, lowercase=True, split_mode="buggy", agg="ratio_of_sums")
        print(f"{lang:<6}{tname:<12}{base:>24.4f}{fixed:>16.4f}{pct(fixed, base):>11.2f}%")

# =====================================================================
# EXPERIMENT 4: all three fixes combined (cumulative effect)
# =====================================================================
divider("EXPERIMENT 4 -- all fixes combined vs original script behavior")
print(f"{'lang':<6}{'tok':<12}{'original (all 3 bugs)':>24}{'all fixed':>14}{'% change':>12}")
for lang, lines in [("eng", eng_lines), ("hin", hin_lines)]:
    for tname, tok in TOKENIZERS.items():
        base = analyze(lines, tok, lowercase=True, split_mode="buggy", agg="mean_of_ratios")
        fixed = analyze(lines, tok, lowercase=False, split_mode="fixed", agg="ratio_of_sums")
        print(f"{lang:<6}{tname:<12}{base:>24.4f}{fixed:>14.4f}{pct(fixed, base):>11.2f}%")

# =====================================================================
# EXPERIMENT 5: the "looks suspicious but is fine" red herring -- random.seed(1337)
# =====================================================================
divider("EXPERIMENT 5 -- random.seed(1337) red herring")
with open(os.path.join(ROOT, "..", "given_starter_kit", "fertility.py")) as f:
    src = f.read()
random_calls = [ln for ln in src.splitlines() if "random." in ln or "random.seed" in ln.lower() or ln.strip().startswith("import random")]
print("All lines in fertility.py mentioning 'random':")
for ln in random_calls:
    print(f"    {ln}")
print(f"\nStatic check: {'random module used beyond the seed line' if any('random.' in l and 'seed' not in l for l in random_calls) else 'random is imported and seeded, but NEVER called again anywhere in the file'}")

print("\nEmpirical check: does shuffling line order change the reported fertility?")
for lang, lines in [("eng", eng_lines), ("hin", hin_lines)]:
    tok = tok_indic
    original_order = analyze(lines, tok, lowercase=True, split_mode="buggy", agg="mean_of_ratios")
    shuffled = lines[:]
    random.Random(42).shuffle(shuffled)   # a DIFFERENT seed than the script's own -- deliberately not reusing 1337
    shuffled_order = analyze(shuffled, tok, lowercase=True, split_mode="buggy", agg="mean_of_ratios")
    reversed_order = analyze(list(reversed(lines)), tok, lowercase=True, split_mode="buggy", agg="mean_of_ratios")
    print(f"  {lang}: original-order={original_order:.6f}  shuffled={shuffled_order:.6f}  "
          f"reversed={reversed_order:.6f}  (all identical: {original_order == shuffled_order == reversed_order})")

# =====================================================================
# EXPERIMENT 6: chars = len(line) codepoints vs true grapheme clusters
# =====================================================================
divider("EXPERIMENT 6 -- tok/char: Unicode codepoints (original) vs extended grapheme clusters")
print(f"{'lang':<6}{'line#':<7}{'codepoints (orig)':>18}{'grapheme clusters':>20}{'diff':>8}")
for lang, lines in [("eng", eng_lines), ("hin", hin_lines)]:
    for i, l in enumerate(lines):
        cp = len(l)
        gc = len(regex.findall(r"\X", l))
        if cp != gc:
            print(f"{lang:<6}{i+1:<7}{cp:>18}{gc:>20}{cp-gc:>8}")
total_cp_eng = sum(len(l) for l in eng_lines)
total_gc_eng = sum(len(regex.findall(r"\X", l)) for l in eng_lines)
total_cp_hin = sum(len(l) for l in hin_lines)
total_gc_hin = sum(len(regex.findall(r"\X", l)) for l in hin_lines)
print(f"\nTotals -- eng: {total_cp_eng} codepoints vs {total_gc_eng} grapheme clusters "
      f"({'no difference -- pure ASCII has no combining marks' if total_cp_eng==total_gc_eng else 'differs'})")
print(f"Totals -- hin: {total_cp_hin} codepoints vs {total_gc_hin} grapheme clusters "
      f"({pct(total_gc_hin, total_cp_hin):.2f}% fewer grapheme clusters than codepoints)")
