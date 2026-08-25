#!/usr/bin/env python3
"""
cross_language_analysis.py -- A3

Recomputes the cross-language comparison properly:
  - on the A1 parallel corpus (30 aligned sentences x 4 languages), not the
    10-line non-parallel corpus_sample/
  - with 2 tokenizers (general = English-heavy, indic_aware = balanced)
  - with 4 denominators: whitespace word, grapheme cluster, UTF-8 byte,
    parallel sentence
  - using ratio-of-totals (not mean-of-per-line-ratios -- see A2), no
    lowercasing (see A2), correct split() (see A2)
"""
import os
import regex
from tokenizers import Tokenizer

ROOT = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(ROOT, "corpus")
TOK_DIR = os.path.join(ROOT, "tokenizers")

tok_general = Tokenizer.from_file(os.path.join(TOK_DIR, "tokenizer_general.json"))
tok_indic = Tokenizer.from_file(os.path.join(TOK_DIR, "tokenizer_indic_aware.json"))
TOKENIZERS = {"general": tok_general, "indic_aware": tok_indic}
LANGS = ["eng", "hin", "kan", "tam"]


def read_lines(path):
    with open(path, "r", encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip()]


def n_words(line):
    return len(line.split())  # correct split -- any whitespace, no empties


def n_graphemes(line):
    return len(regex.findall(r"\X", line))


def n_bytes(line):
    return len(line.encode("utf-8"))


corpora = {lang: read_lines(os.path.join(CORPUS, f"{lang}.txt")) for lang in LANGS}
n_sentences = len(corpora["eng"])
assert all(len(corpora[l]) == n_sentences for l in LANGS), "corpus not aligned!"
print(f"Loaded {n_sentences} aligned parallel sentences x {len(LANGS)} languages\n")

results = {}  # results[tok_name][lang] = dict(tokens, words, graphemes, bytes)
for tname, tok in TOKENIZERS.items():
    results[tname] = {}
    for lang in LANGS:
        lines = corpora[lang]
        total_tokens = sum(len(tok.encode(l).ids) for l in lines)
        total_words = sum(n_words(l) for l in lines)
        total_graphemes = sum(n_graphemes(l) for l in lines)
        total_bytes = sum(n_bytes(l) for l in lines)
        results[tname][lang] = dict(
            tokens=total_tokens, words=total_words,
            graphemes=total_graphemes, bytes=total_bytes,
        )

# ---- print full table: tokenizer x language x 4 denominators ----
for tname in TOKENIZERS:
    print("=" * 78)
    print(f"TOKENIZER: {tname}")
    print("=" * 78)
    header = f"{'lang':<6}{'tokens':>8} | {'tok/word':>10}{'tok/grapheme':>14}{'tok/byte':>11}{'tok/sentence':>14}"
    print(header)
    print("-" * len(header))
    for lang in LANGS:
        r = results[tname][lang]
        tw = r["tokens"] / r["words"]
        tg = r["tokens"] / r["graphemes"]
        tb = r["tokens"] / r["bytes"]
        ts = r["tokens"] / n_sentences
        print(f"{lang:<6}{r['tokens']:>8} | {tw:>10.3f}{tg:>14.3f}{tb:>11.3f}{ts:>14.3f}")
    print()

# ---- normalized-to-English ratios, per denominator, per tokenizer ----
print("=" * 78)
print("RATIO TO ENGLISH (=1.00), per denominator -- this is what 'X times worse' means")
print("=" * 78)
for tname in TOKENIZERS:
    print(f"\n-- {tname} --")
    print(f"{'lang':<6}{'tok/word':>10}{'tok/grapheme':>14}{'tok/byte':>11}{'tok/sentence':>14}")
    eng = results[tname]["eng"]
    eng_tw = eng["tokens"] / eng["words"]
    eng_tg = eng["tokens"] / eng["graphemes"]
    eng_tb = eng["tokens"] / eng["bytes"]
    eng_ts = eng["tokens"] / n_sentences
    for lang in LANGS:
        r = results[tname][lang]
        tw = (r["tokens"] / r["words"]) / eng_tw
        tg = (r["tokens"] / r["graphemes"]) / eng_tg
        tb = (r["tokens"] / r["bytes"]) / eng_tb
        ts = (r["tokens"] / n_sentences) / eng_ts
        print(f"{lang:<6}{tw:>10.2f}{tg:>14.2f}{tb:>11.2f}{ts:>14.2f}")

# ---- does the RANKING of "which language is worse" change by denominator? ----
print("\n" + "=" * 78)
print("DOES THE ORDERING FLIP DEPENDING ON WHICH DENOMINATOR YOU PICK?")
print("=" * 78)
for tname in TOKENIZERS:
    print(f"\n-- {tname} --")
    for denom_name, denom_key in [("tok/word", "words"), ("tok/grapheme", "graphemes"),
                                     ("tok/byte", "bytes"), ("tok/sentence", None)]:
        if denom_key:
            ranked = sorted(LANGS, key=lambda l: results[tname][l]["tokens"] / results[tname][l][denom_key], reverse=True)
        else:
            ranked = sorted(LANGS, key=lambda l: results[tname][l]["tokens"], reverse=True)
        print(f"  {denom_name:<14} worst-to-best: {' > '.join(ranked)}")
