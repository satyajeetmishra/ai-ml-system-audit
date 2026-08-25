#!/usr/bin/env python3
"""
train_tokenizers.py

Trains two byte-level BPE tokenizers locally (no network calls), to stand in
for A3's "at least one multilingual/Indic-aware tokenizer" requirement.

WHY: this sandbox cannot reach huggingface.co or tiktoken's blob storage
(confirmed by direct test -- see NOTEBOOK.md), so a real pretrained
tokenizer (gpt2, xlm-roberta, etc.) can't be loaded. Training our own BPE
tokenizer is the honest alternative: it lets us demonstrate the actual
MECHANISM (fertility differences come from what scripts were in the
training data) with a fully reproducible, from-scratch experiment, rather
than quoting a number for a tokenizer we can't actually run here.

Tokenizer A ("general"): trained overwhelmingly on English, with a small
amount of incidental Hindi -- meant to represent a typical production
tokenizer that wasn't deliberately built for Indic scripts, but also
wasn't trained on English alone.

Tokenizer B ("indic_aware"): trained on a roughly balanced mix of English,
Hindi, Kannada, and Tamil -- meant to represent a tokenizer someone
deliberately built with Indic coverage in mind.

Both use the same vocab size and same BPE algorithm so the comparison in
A3 isolates "what was in the training data", not "different algorithms".
"""
import os
import json
from tokenizers import Tokenizer, models, trainers, pre_tokenizers, decoders

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(HERE, "..", "corpus")
TRAIN_TXT = os.path.join(HERE, "training_text")

VOCAB_SIZE = 8000
MIN_FREQ = 1


def read_lines(path):
    with open(path, "r", encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip()]


def build_training_file(out_path, sources):
    """sources: list of (path, repeat_count) -- concatenate lines, repeating
    small sources so they contribute meaningful frequency mass."""
    lines = []
    for path, repeat in sources:
        block = read_lines(path)
        lines.extend(block * repeat)
    with open(out_path, "w", encoding="utf-8") as f:
        for l in lines:
            f.write(l + "\n")
    return len(lines)


def train_bpe(train_file, out_path, vocab_size=VOCAB_SIZE):
    tok = Tokenizer(models.BPE(unk_token="<unk>"))
    tok.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    tok.decoder = decoders.ByteLevel()
    trainer = trainers.BpeTrainer(
        vocab_size=vocab_size,
        min_frequency=MIN_FREQ,
        special_tokens=["<unk>", "<pad>"],
        initial_alphabet=pre_tokenizers.ByteLevel.alphabet(),
    )
    tok.train([train_file], trainer)
    tok.save(out_path)
    return tok


def main():
    eng_eval = os.path.join(CORPUS, "eng.txt")
    hin_eval = os.path.join(CORPUS, "hin.txt")
    kan_eval = os.path.join(CORPUS, "kan.txt")
    tam_eval = os.path.join(CORPUS, "tam.txt")
    eng_extra = os.path.join(TRAIN_TXT, "eng_extra.txt")
    hin_extra = os.path.join(TRAIN_TXT, "hin_extra.txt")
    kan_extra = os.path.join(TRAIN_TXT, "kan_extra.txt")
    tam_extra = os.path.join(TRAIN_TXT, "tam_extra.txt")

    # --- Tokenizer A: english-heavy, minimal incidental Hindi, NO Kannada/Tamil ---
    a_train_file = os.path.join(TRAIN_TXT, "_combined_general.txt")
    n_a = build_training_file(
        a_train_file,
        [
            (eng_eval, 3),
            (eng_extra, 3),
            (hin_eval, 1),   # small incidental exposure only
        ],
    )
    print(f"[general] training lines: {n_a}")
    tok_a = train_bpe(a_train_file, os.path.join(HERE, "tokenizer_general.json"))
    print(f"[general] vocab size: {tok_a.get_vocab_size()}")

    # --- Tokenizer B: balanced English + Hindi + Kannada + Tamil ---
    b_train_file = os.path.join(TRAIN_TXT, "_combined_indic_aware.txt")
    n_b = build_training_file(
        b_train_file,
        [
            (eng_eval, 2), (eng_extra, 2),
            (hin_eval, 2), (hin_extra, 2),
            (kan_eval, 3), (kan_extra, 3),   # upsampled: less raw text available
            (tam_eval, 3), (tam_extra, 3),
        ],
    )
    print(f"[indic_aware] training lines: {n_b}")
    tok_b = train_bpe(b_train_file, os.path.join(HERE, "tokenizer_indic_aware.json"))
    print(f"[indic_aware] vocab size: {tok_b.get_vocab_size()}")

    # quick sanity check: encode one sentence from each language with both tokenizers
    samples = {
        "eng": read_lines(eng_eval)[0],
        "hin": read_lines(hin_eval)[0],
        "kan": read_lines(kan_eval)[0],
        "tam": read_lines(tam_eval)[0],
    }
    print("\n--- sanity check: token counts on eval line 1 ---")
    print(f"{'lang':<6}{'general':>10}{'indic_aware':>14}")
    for lang, text in samples.items():
        n1 = len(tok_a.encode(text).ids)
        n2 = len(tok_b.encode(text).ids)
        print(f"{lang:<6}{n1:>10}{n2:>14}")


if __name__ == "__main__":
    main()
