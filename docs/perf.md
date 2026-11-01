# Performance (local, indicative only)

**Setup:** gateway + real Banking77 student + real MiniLM encoder on CPU (8 cores, shared desktop),
**simulated teacher** (fixed 300 ms), load generator on the same machine (`scripts/loadtest.py`,
closed loop). 2% audit rate; about 8-9% of requests escalate. These are NOT production capacity
numbers. During the A/B runs an unrelated embedding job (another project, ~4 cores) was running,
so absolute figures are depressed and noisy; only the paired comparison carries information.
Raw data: `evidence/logs/loadtest.jsonl`, `evidence/logs/perf_ab.jsonl`.

## Profile-and-fix story (with the dead ends)
Observation: a single encode costs 11-27 ms (host-load dependent), yet the gateway served only
16-73 req/s at 16-24 concurrent clients, far below `cores / encode_time`.
1. **Hypothesis: torch intra-op thread oversubscription.** Pinning torch to 1 thread under load
   made it *worse* (73 -> 48 req/s at 16 clients; p50 181 -> 285 ms). Rejected, not shipped.
2. **Hypothesis: per-request encodes are inefficient; batch them.** Offline microbenchmark
   (4 torch threads): 46 enc/s at batch 1 vs 220 enc/s at batch 16 (4.8x). Implemented
   `MicroBatcher` (batch <= 16, <= 5 ms wait; `src/cascade/batching.py`, 4 tests).
3. **End-to-end A/B**, 24 clients, 15 s, three alternating repetitions (default vs `--batch 16`):

| rep | default req/s | batched req/s | ratio | default p50/p99 ms | batched p50/p99 ms |
|---|---|---|---|---|---|
| 1 | 16.3 | 30.3 | 1.86 | 1465 / 2056 | 756 / 1281 |
| 2 | 18.1 | 31.0 | 1.71 | 1235 / 1987 | 728 / 1368 |
| 3 | 40.1 | 50.1 | 1.25 | 558 / 1010 | 409 / 1024 |

Batching won in 3 of 3 pairs in this contended set (median 31.0 vs 18.1 req/s; p50 about 35-50% lower). **But** an
earlier, uncontrolled run at 16 clients on a less loaded host went the other way (73 req/s default
vs 63 batched), and at 64 clients the 32-slot concurrency limit shed most load (HTTP 503) in both
configurations. So: batching helps most when CPU is contended or concurrency is high; it is not a
universal win. It stays **opt-in** (off by default). A clean, dedicated-host re-measurement is
still needed before quoting any throughput number.

4. **Re-run on a quieter host** (the other job had finished; load average ~3), same protocol, new data in `evidence/logs/perf_ab.jsonl` (the contended set is kept as `perf_ab_contended.jsonl`):

| rep | default req/s | batched req/s | ratio | default p50/p99 ms | batched p50/p99 ms |
|---|---|---|---|---|---|
| 1 | 39.8 | 48.9 | 1.23 | 560 / 1025 | 440 / 905 |
| 2 | 30.2 | 46.3 | 1.53 | 784 / 1159 | 470 / 1048 |
| 3 | 28.7 | 27.0 | 0.94 | 794 / 1309 | 827 / 1381 |

Across both sets batching won 5 of 6 pairs (ratios 0.94-1.86, median ~1.5) but lost one, and one
earlier unpaired run also favoured the default. Conclusion: a plausible gain of tens of percent
under load, **not established**; host noise (the desktop was in use) is as large as the effect.
Keep it opt-in; a dedicated host and more repetitions would be needed to settle it.

5. **Pinned cores** (server on cores 0-3, load generator on 4-5, 5 alternating pairs, 24 clients, 15 s; `evidence/logs/perf_ab_pinned.jsonl`, `SERVER_PIN=0-3 LOADGEN_PIN=4-5 REPS=5 ./scripts/perf_compare.sh`):

| rep | default req/s | batched req/s | ratio | default p50/p99 ms | batched p50/p99 ms |
|---|---|---|---|---|---|
| 1 | 37.5 | 59.1 | 1.58 | 589 / 1058 | 369 / 769 |
| 2 | 37.6 | 54.8 | 1.46 | 602 / 1020 | 407 / 787 |
| 3 | 30.6 | 43.2 | 1.41 | 749 / 1183 | 493 / 1103 |
| 4 | 22.7 | 10.1 | 0.44 | 1002 / 1648 | 2277 / 3044 |
| 5 | 8.2 | 16.3 | 1.99 | 3011 / 3974 | 1458 / 2130 |

Reps 4 and 5 are contaminated: **I was running lint, type checks and tests on the same machine at
that moment** (throughput fell for both configurations, to 8-23 req/s). They are kept in the table
for transparency; the median ratio over all five is 1.46, and the three quiet pairs give 1.41-1.58.

**Updated conclusion:** on this host, with pinned cores and no other load, micro-batching raised
throughput by roughly 40-60% and cut p50 by about 35% at 24 concurrent clients; across every paired
comparison in this document it won 9 of 11 (the losses: 0.94 in the unpinned quiet set and 0.44 in a
pinned pair that I contaminated myself), so the gain is plausible and repeatable under load but has
not been measured on a dedicated machine. It remains opt-in.

6. **Locust 2.46, resource use sampled** (`scripts/locust_ab.sh`: server pinned to cores 0-3, Locust to 4-5, 24 users, 30 s, 3 alternating pairs; CPU% summed over the server process tree, RSS = peak; raw CSVs in `evidence/logs/locust_ab/`). Zero failed requests in all six runs.

| pair | default req/s | batched req/s | ratio | default p50 / p95 / p99 ms | batched p50 / p95 / p99 ms | CPU% (default / batched) | peak RSS MB |
|---|---|---|---|---|---|---|---|
| 1 | 14.8 | 16.1 | 1.09 | 1500 / 2000 / 2200 | 1500 / 2100 / 2300 | 155 / 292 | 750 / 782 |
| 2 | 26.7 | 58.5 | 2.19 | 860 / 1200 / 1400 | 370 / 710 / 900 | 235 / 389 | 778 / 833 |
| 3 | 39.4 | 73.8 | 1.88 | 580 / 890 / 960 | 290 / 590 / 670 | 250 / 392 | 780 / 854 |

Medians: default 26.7 req/s (p50 860, p95 1200, p99 1400 ms); batched 58.5 req/s (p50 370, p95 710,
p99 900 ms). **Caveat:** throughput rises from pair to pair for *both* configurations (15 -> 27 -> 39
and 16 -> 58 -> 74), i.e. the shared desktop got quieter during the run, so absolute numbers are not
comparable across pairs and the ratio in pair 1 (both slow) is the least informative. Within each
adjacent pair batching won. Batching uses more CPU (about 3-4 cores vs 1.5-2.5 on the 4 pinned cores)
and about 50-100 MB more memory, but serves more requests per CPU-second (roughly 19 vs 16 req/s per
core in pairs 2-3). Memory is dominated by PyTorch and the encoder, about 0.8 GB per process.

## Other measured facts
- Process start-up is about 9 s (importing scipy.stats and loading the encoder dominates); the
  container healthcheck uses `--start-period=40s`.
- Backpressure works: at 64 clients with a 32-slot limit, excess requests got 503 + Retry-After
  instead of unbounded queueing.
- Unit-level costs are negligible next to the encoder: gate lookup and student inference are
  sub-millisecond.

## Not done
No k6/Locust run, no multi-replica test, no soak test, no latency measurement with a real teacher.
