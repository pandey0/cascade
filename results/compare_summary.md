# Head-to-head comparison: summary tables (generated; do not edit)

Assumptions (NOT measured): human label $0.10; node $0.15/hour, 2 nodes always on ($7.2/day) for self-hosted approaches; small-model serving $8.3e-07/request; one-off engineering {'llm': 0, 'gold': 5000, 'cascade': 10000, 'cache': 3000}. LLM price per call is measured. Year-1 cost = one-off labels + engineering + 365 days of running cost.

### Scenario A. No prompt caching

## banking77 (LLM price $0.000204/call, LLM median latency 947 ms)

| approach | accuracy | LLM calls per request | year-1 cost at 10,000/day | year-1 cost at 100,000/day | year-1 cost at 1,000,000/day | year-1 cost at 10,000,000/day |
|---|---|---|---|---|---|---|
| LLM only | 75.8% | 1.00 | $745 | $7,448 | $74,482 | $744,823 |
| Small model, 1000 human labels, no LLM | 84.4% | 0.00 | $7,731 | $7,758 | $8,032 | $10,770 |
| Small model, 3000 human labels, no LLM | 89.5% | 0.00 | $7,931 | $7,958 | $8,232 | $10,970 |
| Cascade, 1000 LLM labels, error target 10% | 75.8% | 0.49 | $12,999 | $16,332 | $49,670 | $383,043 |
| Cascade, 3000 human labels, error target 10% | 76.0% | 0.95 | $13,638 | $20,032 | $83,964 | $723,289 |
| Semantic cache, similarity 0.9 | 75.4% | 0.74 | $6,184 | $11,192 | $61,273 | $562,073 |
| Semantic cache, similarity 0.85 | 75.2% | 0.55 | $6,043 | $9,775 | $47,096 | $420,309 |

## clinc150 (LLM price $0.000243/call, LLM median latency 893 ms)

| approach | accuracy | LLM calls per request | year-1 cost at 10,000/day | year-1 cost at 100,000/day | year-1 cost at 1,000,000/day | year-1 cost at 10,000,000/day |
|---|---|---|---|---|---|---|
| LLM only | 91.0% | 1.00 | $886 | $8,861 | $88,613 | $886,133 |
| Small model, 1000 human labels, no LLM | 86.2% | 0.00 | $7,731 | $7,758 | $8,032 | $10,770 |
| Small model, 3000 human labels, no LLM | 95.0% | 0.00 | $7,931 | $7,958 | $8,232 | $10,970 |
| Cascade, 1000 LLM labels, error target 10% | 90.3% | 0.56 | $13,127 | $17,617 | $62,510 | $511,448 |
| Cascade, 3000 human labels, error target 10% | 94.3% | 0.35 | $13,242 | $16,065 | $44,296 | $326,602 |
| Semantic cache, similarity 0.9 | 91.0% | 0.87 | $6,406 | $13,406 | $83,410 | $783,446 |
| Semantic cache, similarity 0.85 | 90.9% | 0.78 | $6,323 | $12,576 | $75,110 | $700,445 |

### Scenario B. Prompt caching on every LLM call (measured 7.2x cheaper, +$500 engineering)

## banking77 (LLM price $0.000028/call, LLM median latency 947 ms)

| approach | accuracy | LLM calls per request | year-1 cost at 10,000/day | year-1 cost at 100,000/day | year-1 cost at 1,000,000/day | year-1 cost at 10,000,000/day |
|---|---|---|---|---|---|---|
| LLM only | 75.8% | 1.00 | $604 | $1,540 | $10,896 | $104,459 |
| Small model, 1000 human labels, no LLM | 84.4% | 0.00 | $7,731 | $7,758 | $8,032 | $10,770 |
| Small model, 3000 human labels, no LLM | 89.5% | 0.00 | $7,931 | $7,958 | $8,232 | $10,970 |
| Cascade, 1000 LLM labels, error target 10% | 75.8% | 0.49 | $13,182 | $13,671 | $18,560 | $67,446 |
| Cascade, 3000 human labels, error target 10% | 76.0% | 0.95 | $13,530 | $14,446 | $23,605 | $115,194 |
| Semantic cache, similarity 0.9 | 75.4% | 0.74 | $6,208 | $6,931 | $14,156 | $86,411 |
| Semantic cache, similarity 0.85 | 75.2% | 0.55 | $6,188 | $6,733 | $12,178 | $66,624 |

## clinc150 (LLM price $0.000034/call, LLM median latency 893 ms)

| approach | accuracy | LLM calls per request | year-1 cost at 10,000/day | year-1 cost at 100,000/day | year-1 cost at 1,000,000/day | year-1 cost at 10,000,000/day |
|---|---|---|---|---|---|---|
| LLM only | 91.0% | 1.00 | $624 | $1,737 | $12,868 | $124,182 |
| Small model, 1000 human labels, no LLM | 86.2% | 0.00 | $7,731 | $7,758 | $8,032 | $10,770 |
| Small model, 3000 human labels, no LLM | 95.0% | 0.00 | $7,931 | $7,958 | $8,232 | $10,970 |
| Cascade, 1000 LLM labels, error target 10% | 90.3% | 0.56 | $13,200 | $13,850 | $20,352 | $85,368 |
| Cascade, 3000 human labels, error target 10% | 94.3% | 0.35 | $13,474 | $13,892 | $18,068 | $59,826 |
| Semantic cache, similarity 0.9 | 91.0% | 0.87 | $6,239 | $7,240 | $17,246 | $117,309 |
| Semantic cache, similarity 0.85 | 90.9% | 0.78 | $6,228 | $7,124 | $16,088 | $105,724 |
