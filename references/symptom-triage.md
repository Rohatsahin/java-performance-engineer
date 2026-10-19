# Symptom triage

> Last reviewed: 2026-10. JDK 21-27 and the library versions named in the text; see `sources.md`.

Start from the symptom, take the first measurement, and only then open the deep reference.
Every row is a hypothesis generator, not a diagnosis. Command tiers: `command-safety.md`.

| Symptom | First measurement (Tier 1 unless noted) | Branches | Read |
|---|---|---|---|
| Pod exit 137 | `lastState` reason, cgroup `memory.events`, `memory.current` vs `memory.max` | reason `OOMKilled`: cgroup OOM (no Java OOME in logs: native/non-heap; with OOME: heap, metaspace, thread creation). Reason `Error` or no OOM counter: probe kill, grace-period SIGKILL or eviction | `container-memory.md` section 3, `startup-and-warmup.md` |
| Working set high but heap small | `GC.heap_info` (Tier 2), smaps rw-p regions, thread count; NMT if enabled | arenas, thread stacks, direct buffers, code cache | `memory-model.md`, `container-memory.md` |
| p99 spikes, average fine | GC log pause lines, `cpu.stat` throttling, pool pending metrics, safepoint log | pause > spike: GC; throttled periods: CPU limit; pending: pool or downstream | `gc-pause-triage.md`, `gc-cpu-threads.md` |
| High CPU, low throughput | CPU profile (async-profiler `cpu` or JFR), GC share of CPU, JIT compile threads | GC dominates: allocation rate; app frames dominate: hot path; compiler dominates: warm-up | `hot-paths-and-allocation.md`, `startup-and-warmup.md` |
| Slow or failing startup, slow first requests | startup log timestamps, probe configuration, JIT/class-loading time | probes kill a slow start; cold JIT; class loading | `startup-and-warmup.md`, `aot-and-footprint-flags.md` |
| Latency right after scale-out or deploy | latency by pod age, readiness timing, compile queue | traffic arrives before warm-up | `startup-and-warmup.md` |
| Errors during rollout or scale-in | SIGTERM handling, `terminationGracePeriodSeconds`, in-flight request counts | no drain; grace period shorter than drain | `startup-and-warmup.md`, `rollout-and-rollback.md` |
| Heap live set climbs over days | live-set metric or GC-log occupancy after marking/mixed/full collections; histograms only on one pod (Tier 3) | leak vs cache growth vs fragmentation | `leaks-and-heap-dumps.md` |
| Threads very many, or `unable to create native thread` | thread count by pool, `ulimit`/`pids.max`, `memory.events` | default pools, unbounded executors | `gc-cpu-threads.md` section 5, `dependency-tuning.md` |
| Connection pool saturated, DB healthy | pending/usage metrics, hold time, `max_connections` budget | long holds beat undersized pool | `formulas.md`, `dependency-tuning.md` |
| Virtual threads: stalls or low concurrency | `jdk.VirtualThreadPinned` events, thread dump (Tier 2), semaphore/pool limits | pinning, downstream limit, CPU-bound work | `virtual-threads.md` |
| "Is this flag worth it?" | the flag catalog verdict, then an A/B | adopt, candidate, avoid | `flag-catalog.md`, `ab-test-recipe.md` |

## Ground rules

- Measure the symptom's own metric (latency, restarts, throttling), not a proxy such as
  average CPU.
- If two branches fit, run the cheaper refutation first.
- State the load shape (idle, steady, peak) for every number.
- If the first measurement points outside the JVM (node pressure, downstream saturation,
  network), say so and stop tuning flags.
