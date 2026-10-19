# Hot paths and allocation

> Last reviewed: 2026-10. JDK 21-27 and the library versions named in the text; see `sources.md`.

Tags and source IDs are defined in `sources.md`. Method: profile, find the wide plateau,
change it, prove it with a benchmark and a production comparison. Do not edit code on
intuition.

## 1. Profile first

1. Pick the metric (p99, CPU per request, allocation per request) and the load that shows it.
2. CPU: async-profiler `cpu` or JFR. JDK 25 adds JFR CPU-time sampling on Linux only
   (event `jdk.CPUTimeSample`, experimental and disabled by default). [O] JEP-509 Wall-clock mode shows blocked
   time that CPU mode hides (`profiling-and-load.md`). [O] ASYNC-MODES
3. Allocation: async-profiler `alloc` or JFR allocation sampling. Per-request bytes allocated
   is the number to track. [P]
4. Lock contention: async-profiler `lock`; contended monitors and queues show as wide frames
   in wall mode. [O] ASYNC-MODES
5. For accurate line attribution, async-profiler recommends
   `-XX:+UnlockDiagnosticVMOptions -XX:+DebugNonSafepoints`; in containers see the
   `perf_event` notes in `profiling-and-load.md`. [P]
6. Read the flame graph by width (share of samples), top-down from the entry point; ignore
   narrow towers. [P]

## 2. Typical findings

| Finding | Why it hurts | Direction |
|---|---|---|
| Serialization/deserialization dominates | CPU and garbage per request | reuse configured mappers; avoid re-parsing; stream large payloads; consider smaller payloads |
| Boxing, short-lived collections in loops | allocation rate raises GC frequency | primitive types, pre-sized collections, avoid stream pipelines in the hottest loops after measuring |
| Regex or string formatting per request | CPU and garbage | precompile patterns; avoid formatting when the level is disabled |
| Logging at high volume | CPU, allocation, I/O stalls | log level, sampling, asynchronous appender with a bounded queue |
| Large objects or buffers per request | humongous allocations, pauses | pool or reuse where safe, stream, chunk |
| Contended monitor or shared structure | threads blocked, throughput flat as threads rise | shrink critical sections, per-thread or sharded state, concurrent structures (`formulas.md` USL) |
| N+1 calls or queries | latency multiplies by call count | batch; the profile shows wait, not CPU (wall mode) |
| JIT deoptimization loops | repeated recompilation, unstable latency | find the cause in compilation events before touching flags |

These are directions, not recipes; each needs a measurement that shows it is the plateau in
your profile. [P]

## 3. Prove it

- **JMH** for the changed code in isolation: use forks, warm-up, consume results with a
  `Blackhole`, and avoid constant-folded inputs. `-prof gc` reports allocation rate and GC
  churn per operation, `-prof stack` samples hot methods, `-prof comp` shows whether compilation
  overlaps measurement. [O] JMH-SAMPLES
- JMH does not model GC pacing, throttling, queues or network; confirm in a load test and in
  production (`profiling-and-load.md`, `rollout-and-rollback.md`).
- Compare the same service before and after: latency percentiles, CPU per request, allocation
  per request, GC time share, and error rate. A benchmark win that does not move the
  production metric is not a win.

## 4. Anti-patterns

- Tuning GC flags to hide an allocation problem.
- Rewriting a method that is 1% of samples.
- Benchmarking with a closed-loop generator and reporting latency percentiles
  (`profiling-and-load.md`, coordinated omission).
- Reporting mean latency.
