# Formulas and sizing rules

> Last reviewed: 2026-10. JDK 21-27 and the library versions named in the text; see `sources.md`.

Each formula has its variables, validity limits and source. These are generic rules, not
company data. Tags and IDs: `sources.md`. A formula gives a starting point; confirm by
measurement.

## 1. Little's Law [O] FORM-LITTLE

`L = lambda x W`: average number in the system = arrival rate x average time in the system
(queue plus service).

- In-flight requests = RPS x latency. 200 RPS x 0.25 s = 50 concurrent requests, so a pool
  serving them without queueing needs about 50 workers.
- Busy DB connections = queries/s x connection hold time. 400 q/s x 5 ms = 2 busy connections
  on average; add headroom for variance (the law does not give it).
- Valid for long-run averages; `lambda` is accepted throughput, not offered load, if requests
  are rejected. It gives means, not percentiles, and does not give an optimal pool size.
- Use connection **hold time** (checkout to return, e.g. Hikari `connections.usage`), not the
  SQL execution time. Hold time grows with transaction scope: non-DB work or remote calls inside
  a transaction, several queries per transaction, and (with JPA) Spring's open-in-view, which is
  on by default. [P] If busy connections computed from query time are far below the pool size
  but the pool is saturated, hold time is the suspect.
- Pending threads with low average utilization mean bursts or long holds, so check
  `connections.pending`, `.acquire` and `.usage` percentiles before resizing.

## 2. Connection pool sizing [P] FORM-HIKARI-POOL, FORM-PG-CONNS

- Treat `connections = (core_count x 2) + effective_spindle_count` as an untested first guess
  for the pool's upper bound, not a rule. It is an older heuristic from the PostgreSQL wiki
  (last edited 2014, which says it needed adjustment for 9.2 and that its behavior on SSDs was
  never analyzed), quoted by the HikariCP wiki, which calls it a starting point; the current
  HikariCP README gives no formula and says the right value depends on your environment. Core
  count excludes hyperthreads; effective spindles are 0 if the active data set is fully cached.
  Example: 4 cores, cached data: 8 connections. Confirm the pool size with a load test on your
  own database, watching throughput, p99 and `connections.pending`.
- The wiki's illustrations (2048 to 96 connections, ~100 ms to ~2 ms; throughput flattening
  near 50 connections) point to an undated vendor video and chart with no data on the page.
  They show that oversized pools hurt, not which number is right.
- Deadlock avoidance (same wiki): `pool >= Tn x (Cm - 1) + 1`, where `Tn` is the maximum number
  of threads and `Cm` the maximum connections one thread holds at once.
- "core_count" is the **database server's** cores (shared by every service on that database),
  not the application's.
- Threads that outnumber connections queue in your process (cheap); connections that outnumber
  DB cores queue inside the database (expensive).
- Budget across services (arithmetic, [P]): `(replicas + surge) x pool_size + other services'
  maximums + superuser_reserved_connections (PostgreSQL default 3, [O] PG-DOCS) + admin/migration headroom
  <= max_connections`. Example: `max_connections` 100, two other services at 20 each, 3
  reserved, ~7 headroom leaves ~50 for this service; 6 replicas gives 8 each, and a rolling
  deploy that briefly adds a 7th replica needs `7 x 8 + 40 + 3 = 99`, which uses up the
  headroom, so shrink the pool, cap the surge, or use a transaction-mode pooler (PgBouncer,
  RDS Proxy). Check prepared-statement compatibility first (PgBouncer `max_prepared_statements`,
  default 200; 0 disables support in transaction mode; pgjdbc `prepareThreshold`). [O]
  PGBOUNCER-CFG
- Lower the pool's `connectionTimeout` (30 s default) when you want overload to fail fast
  instead of piling up behind a saturated pool. [P]
- Validity on managed databases or NVMe is [U]. Validate with a load test and Little's Law.

## 3. Thread pool sizing and scalability limits

- Goetz, *Java Concurrency in Practice*: `threads = N_cpu x U_cpu x (1 + W/C)` with `U_cpu`
  target utilization (0-1) and `W/C` wait time over compute time. 8 cores, U = 0.8, W/C = 9:
  64 threads. [P] (confirmed only via secondary sources). It assumes platform threads that
  block for W, so it does not apply to non-blocking code or virtual threads, where the limit is
  the downstream resource. It ignores memory, file handles and sockets, and fits one homogeneous task type with measurable W and C. Cap by the downstream
  limit (e.g. the DB pool) and by Little's Law: take the lesser.
- Amdahl: `speedup(N) = 1 / ((1 - p) + p/N)`; ceiling `1 / (1 - p)`. [O] FORM-USL
- Universal Scalability Law: `C(N) = N / (1 + alpha(N-1) + beta x N(N-1))`, `alpha` contention,
  `beta` coherency; peak at `N* = sqrt((1 - alpha)/beta)`. alpha = 0.05, beta = 0.001 gives
  N* of about 31; beyond it, more threads reduce throughput. Fit alpha and beta to measured
  throughput at several N. [O] FORM-USL

## 4. Container memory budget

- The Oracle, Red Hat and Microsoft pages read give a heap percentage, not a budget formula.
  The Paketo Java buildpack memory calculator does give one: heap = total container memory -
  non-heap - headroom, with non-heap = direct memory + metaspace + reserved code cache +
  thread stack x thread count (defaults assume 250 threads). [O] PAKETO-JAVA Treat the identity
  below as a check against measurements, not a predictor:
  `limit >= heap_max + metaspace + code_cache + threads x Xss + direct buffers + GC structures
  + malloc arenas/JIT/other native + agent overhead`.
- Official building blocks [O] JAVA-MAN21/25: `MaxRAMPercentage` 25; `MaxRAM` = min(available
  memory, 128 GB), where available memory is the container limit if lower; heap max = MaxRAM x
  percentage / 100 unless `-Xmx`. 2 GiB limit at 75% gives a 1.5 GiB heap and 0.5 GiB for
  everything else. `Xss` 1024 KB Linux x64, 2048 KB aarch64 (reserved virtual memory; only
  touched pages reach RSS, so threads x Xss is an upper bound). Code cache 240 MB; metaspace
  unlimited by default.
- Netty direct memory: default `io.netty.maxDirectMemory` falls back to the JDK maximum, which
  is about `Xmx` when `MaxDirectMemorySize` is unset ([O] DEP-NETTY-SRC, source logic). That
  direct buffers can then grow toward the heap size on top of the heap is an inference from
  that logic, not a measurement.
- Heap `%` from a limit: `heap % = (limit - non_heap_peak - safety) / limit`. `non_heap_peak`
  must be measured at steady state under peak load (NMT plus arena/smaps); `safety` is your
  choice (the authors use at least 10% of the limit; not from a source).

## 5. Kubernetes requests and limits [O] K8S-RESOURCES, K8S-QOS, FORM-VPA

- The scheduler places pods by requests. A container may exceed its request if the node has
  room. The CPU limit is a throttling cap; the memory limit is enforced by the kernel OOM
  killer.
- QoS: Guaranteed = every container has CPU and memory requests equal to limits; Burstable =
  something set; BestEffort = nothing. Kubelet node-pressure eviction does not rank by QoS
  class: it ranks pods whose usage exceeds requests first, then Pod Priority, then usage over
  requests; QoS is only a rough predictor. The kernel OOM killer does use QoS through
  `oom_score_adj`. [O] K8S-EVICT
- VPA recommender defaults (kubernetes/autoscaler): target CPU percentile 0.9, safety margin
  0.15, minimums 25m CPU and 250 MB memory, 24 h histogram half-life, OOM bump 1.2x with a
  100 MiB floor, target memory percentile 0.9. These are the flag defaults on the autoscaler's
  master branch, so confirm them against the VPA release you run. Target = percentile x
  (1 + margin), floored by the minimum. Example: p90 CPU 400m gives 460m. [O] FORM-VPA
- Conventions: memory request = limit for JVMs; size from observed peak working set plus a
  margin.

## 6. GC heap sizing [O] FORM-ORA-GC

Oracle's GC tuning guide: total memory is the most important factor; unless pauses are a
problem, grant as much as possible; `-Xms = -Xmx` removes a sizing decision; keep old gen
large enough for live data plus 10-20% or more of slack; the heap expands to keep free space
>= 40% (`MinHeapFreeRatio`) and contracts above 70% (`MaxHeapFreeRatio`); `NewRatio=2` default;
free-ratio trimming to 10 has worked "without too much performance degradation; results may
vary". The "heap = 3-4x live data" rule is from community material, not Oracle. [A] Live data
= old-gen occupancy after a full GC at steady state.

## 7. Profiler sanity checks

Profiler-specific memory checks are in `addons/datadog.md`.

## 8. Statistics for small experiments

- Welch t statistic: `T = (mean1 - mean2) / sqrt(s1^2/N1 + s2^2/N2)` with Welch-Satterthwaite
  degrees of freedom; handles unequal variances. [O] FORM-NIST A CI is
  `diff +/- t x sqrt(s1^2/N1 + s2^2/N2)` (textbook [P]).
- Welch's test compares means of roughly independent, comparable samples. Repeated readings
  within one pod or run are autocorrelated, so use one summary per pod or run as the sample
  unit; p99 is not a mean, so prefer a rank-based or bootstrap interval for latency
  percentiles. [P]
- Georges et al., OOPSLA 2007, "Statistically rigorous Java performance evaluation" covers JIT,
  GC and scheduling variance. Its specific rules are [U] here (PDF not readable).
- A/A noise floor: run the same configuration in both arms; only believe an effect larger than
  the A/A spread, and report effect size with its interval. [P]
