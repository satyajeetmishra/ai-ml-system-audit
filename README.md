# AI/ML System Audit

This repository contains an evidence-based audit of a multilingual AI/ML tokenizer and model-serving stack. The project focuses on validating benchmark claims, identifying measurement issues, reconciling serving capacity, and making deployment recommendations.

## Project Overview

### Part A — Tokenizer Audit
- Build a multilingual evaluation corpus covering English, Hindi, and Dravidian languages.
- Audit the original tokenizer implementation and metric.
- Quantify identified issues using controlled experiments.
- Compare multiple tokenizers using different denominators.
- Provide a routing and cost recommendation.

### Part B — Capacity Reconciliation
- Calculate KV-cache memory requirements from the model specification.
- Estimate maximum concurrent sequence capacity.
- Compare theoretical capacity with benchmark logs.
- Investigate throughput anomalies and determine the correct goodput interpretation.

### Part C — Decision Memo
- Evaluate approaches for making multilingual assistant responses more casual and conversational.
- Compare SFT, inference-time rewriting, and prompt engineering.
- Provide assumptions, cost estimates, success metrics, and a kill criterion.

## Repository Structure

```text
your-submission/
├── NOTEBOOK.md
├── AI_USAGE.md
├── partA/
├── partB/
└── partC/
```

## Evidence-First Methodology

Every substantive claim is supported by:
1. A reproducible experiment or calculation.
2. The command or code used to produce the result.
3. Before/after or expected/observed measurements where applicable.
4. A concise explanation of what the measured difference demonstrates.

The objective is to produce conclusions that can be independently reproduced and defended.

## Reproducibility

The analysis scripts and generated results are included alongside the written findings.

Example:

```bash
python partA/audit_experiments.py
python partA/cross_language_analysis.py
python partB/capacity_and_throughput.py
```

Refer to the individual files in `partA/`, `partB/`, and `partC/` for the exact commands and experimental setup used.

## Multilingual Evaluation

The evaluation covers multiple languages, including:
- English
- Hindi
- Kannada
- Tamil

The corpus construction, preprocessing, and limitations are documented within `partA/`.

The corpus is intended for comparative analysis rather than as a comprehensive multilingual benchmark, so conclusions are interpreted with appropriate sample-size and domain caveats.

## Tokenizer Analysis

Part A examines:
- Tokenizer implementation behavior
- The original fertility metric
- Alternative denominators
- Cross-language tokenization efficiency
- Routing and cost implications

Detailed findings and supporting experiments are contained in `partA/`.

## Serving and Capacity Analysis

Part B examines:
- KV-cache bytes per token
- Concurrent sequence capacity
- Long-context throughput
- Batch-size behavior
- Goodput
- Metrics that can validate the proposed serving mechanism

Detailed calculations and conclusions are contained in `partB/`.

## Decision Analysis

Part C evaluates:
1. Synthetic-data SFT
2. A lightweight inference-time rewriter
3. Prompt engineering

The recommendation considers GPU availability, reviewer capacity, timeline, data volume, serving/training cost, success criteria, and failure conditions.

See `partC/memo.md` for the complete recommendation.

## AI Usage

AI tools were used during the analysis and development process. Their contributions, limitations, and cases requiring independent verification are documented in:

`AI_USAGE.md`

## Lab Notebook

`NOTEBOOK.md` records the chronological progression of the investigation, including hypotheses, experiments, results, revisions, and dead ends.

It is maintained as an experimental record rather than a retrospective summary.

## Disclaimer

The conclusions are based on the supplied benchmark configuration, evaluation corpus, and available experimental evidence. Production routing and capacity decisions should be validated against representative production workloads.
