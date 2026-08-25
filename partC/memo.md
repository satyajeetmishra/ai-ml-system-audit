# Decision memo — casual tone in Hindi, Kannada, Tamil, Telugu, Bengali, Marathi

## Recommendation

Split by review coverage, not by picking one path for all six languages.
**Hindi and Kannada** (the two languages we can actually verify): build the
small inference-time rewriter (path b). **Tamil, Telugu, Bengali, Marathi**
(zero native-review capacity under these constraints): ship
prompt-engineering only (path c) as an interim measure, and hold SFT/
rewriter work for these four until reviewer bandwidth exists.

The binding constraint here isn't compute or timeline — it's that **one
reviewer, 10h/week, covers 2 of 6 languages.** Every path has the same
failure mode in the other four: nobody on the team can tell whether a
"casualized" output is natural, subtly wrong, or worse, without native
review. That risk doesn't go away by picking SFT or the rewriter instead of
prompting for those languages — it just becomes invisible until a user
finds it. The rewriter (not full SFT) for Hindi/Kannada because it's
modular: easy to scope a reviewer's limited hours around (they're checking
rewriter input→output pairs, not re-assessing the whole model), easy to
disable per-language if it goes wrong, and it trains fast enough on one
A100 to leave room for multiple review-and-retrain cycles instead of one
shot.

## Assumptions

1. This is a register problem, not a capability gap — the base model
   already produces fluent, correct output in all six languages; we're
   changing *how* it says things, not what it can say.
2. "SFT on synthetic pairs" (path a) means fine-tuning the production
   model itself, distinct from path b's separate ≤1B rewriter.
3. A reviewer doing quick accept/edit/reject passes (not deep linguistic
   review) can get through roughly 15–20 short examples/hour.
4. "No external API budget" rules out paid third-party models for
   generating or judging data, but the in-house base model and the A100
   are available for both.
5. The 10h/week is a shared ceiling across Hindi *and* Kannada combined,
   not 10h each.

## Back-of-envelope arithmetic

- Reviewer budget: 10h/week × 3 weeks = **30 person-hours total** ≈ 15h
  per language (Hindi, Kannada).
- At ~15–20 examples/hour: **~225–300 reviewed examples per language**
  across the 3 weeks — enough for an early seed set (~50–100 approved
  pairs/language, used for few-shot prompting and as rewriter training
  targets) plus a final held-out check (~150/language) before the week-3
  launch review.
- Data for the rewriter: self-generate synthetic formal→casual pairs by
  few-shot prompting the base model with the reviewer-approved seed set —
  no external API cost. ~2,000–3,000 pairs/language is enough for a ≤1B
  rewriter at this scale.
- Compute: fine-tuning a ≤1B model on a few thousand short pairs, for two
  languages, is hours on one A100-80GB, not days — leaves real room in the
  2-week window for 2–3 generate→review→retrain cycles instead of a single
  attempt.

## Success metric

**Hindi/Kannada:** on a 150-sample held-out set per language, reviewer
rates **≥75% as casual and natural**, with **0% rated as changing the
original meaning** — an incorrect casual rewrite is worse than staying
formal, so that's a hard floor, not a soft target.
**Tamil/Telugu/Bengali/Marathi:** no native-review capacity means no
casualness claim can be verified, so the bar here is safety, not quality —
**no regression on existing automated fluency checks** vs. the current
formal baseline. This asymmetry is deliberate and is the reason these four
stay on prompt-only for now.

## Kill criterion

**By end of week 2:** if fewer than 50% of a running Hindi/Kannada
rewriter sample is rated casual-and-natural, or if *any* reviewed output
is found to change meaning, halt the rewriter for that language and fall
back to prompt-engineering-only for it at the week-3 launch review. This
is checked mid-way specifically so there's still a week of runway to fall
back cleanly rather than discovering it at the launch review itself.

## Day-1 experiment

Prompt-engineer a casual-tone system prompt + few-shot examples across all
six languages (reviewer-approved examples for Hindi/Kannada; best-effort
for the other four), generate outputs on a fixed test set, and spend the
reviewer's first session rating the Hindi/Kannada baseline. This is
zero-training and instantly shippable — it might already clear the bar for
some languages on its own, it tells us in hours (not week 2) whether the
rewriter investment is worth making at all, and it produces the first
reviewer-approved examples the rewriter's synthetic data generation will
need anyway.
