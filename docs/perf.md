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

## Other measured facts
- Process start-up is about 9 s (importing scipy.stats and loading the encoder dominates); the
  container healthcheck uses `--start-period=40s`.
- Backpressure works: at 64 clients with a 32-slot limit, excess requests got 503 + Retry-After
  instead of unbounded queueing.
- Unit-level costs are negligible next to the encoder: gate lookup and student inference are
  sub-millisecond.

## Not done
No k6/Locust run, no multi-replica test, no soak test, no latency measurement with a real teacher.
