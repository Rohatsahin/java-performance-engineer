# Datadog add-on

Optional. Datadog is a trademark of its owner; this project is not affiliated with or endorsed
by it. Tags: see `references/sources.md`.

## Profiler memory sanity check [O] DDPROF-SRC

`sanityCheck.cpp` in DataDog/java-profiler, HotSpot only. Warning text: "Sanity check failed:
estimated memory requirement (N MB) exceeds available memory (M MB)"; it is a warning and the
profiler still starts.

```
estimate = heap_max + metaspace_max + code_cache + 0.30 x heap_max
         + threads x stack_size + 64 MiB
metaspace_max = MaxMetaspaceSize, or 256 MiB when unlimited
code_cache    = ReservedCodeCacheSize (240 MiB default)
stack_size    = ThreadStackSize (512 KiB fallback); threads = live thread count (200 fallback)
available     = RAM - 128 MiB, or the container limit if smaller
```

It fails when `estimate > available`. It counts maximums, not usage, and ignores direct
buffers, malloc arenas and JIT scratch. Consequence: lowering `MaxRAMPercentage` lowers the
estimate by `1.3 x` the heap reduction, which is why the warning clears.

## Datadog dd-java-agent

The official setup page gives no thread, memory or startup overhead figures. [U] Measure: A/B
with and without `-javaagent`, using NMT and `Thread.print | grep dd-`. Profiler toggles:
`DD_PROFILING_HEAP_ENABLED=false` (master heap profiling off) and
`DD_PROFILING_DDPROF_LIVEHEAP_ENABLED=false` (native engine only). [O] DD-JAVA

## Continuous profiler

**Datadog continuous profiler** [O] DD-JAVA: Linux uses the perf-based engine with all
   profile types, JFR is the fallback; wallclock profiling is on by default and independent of
   `perf_event_paranoid`; live-heap profiling is on by default on Linux since dd-trace-java
   1.61.0 (disable with `DD_PROFILING_HEAP_ENABLED=false`); the native engine needs JDK
   11.0.23+/17.0.11+/21.0.3+/22+, else JFR `OldObjectSample`; profile data is written to
   `/tmp`; Datadog advises a small ephemeral-storage request (its example is 100MB) so the pod is not evicted first under node disk pressure, so size it from your observed `/tmp` use. The docs give no native-memory overhead
   figure; A/B with `-Ddd.profiling.enabled=false` and compare RSS and NMT.

## Fleet metrics as Tier 1 evidence

Datadog API reads and a per-pod `kubectl describe` are Tier 1 (`references/command-safety.md`);
a `kubectl` sweep over every replica is not, ask first. Metrics are a screen, not a diagnosis:
state the window and load shape, and a result of "nothing flagged" is not a clean bill of health.

**Observed in one account [A]**, checked 2026-10 on a small G1 fleet of JVM deployments,
24-hour window, Datadog Java agent and Kubernetes integration, versions not
recorded. Refuted if your account tags or scales these differently; list a metric's tags before
trusting a filter.

- `jvm.*` carried `service` and `env` and no `kube_deployment`; `kubernetes.*` carried
  `kube_deployment`, `container_name` and `pod_name`. A `jvm.*` query filtered by
  `kube_deployment` returned no series and no error. Join the two by hand.
- `kubernetes.memory.working_set` is per container: filter to the application container, or
  sidecars are included.
- `kubernetes.memory.limits` returned 0 for deployments with no limit. Treat 0 or absent as
  "no limit", never as a limit.
- `jvm.heap_memory_committed` exists alongside `jvm.heap_memory` (used) and
  `jvm.heap_memory_max`.

**Semantics not read in the vendor docs [U]**: verify before relying on them.

- `jvm.gc.major_collection_count` looked like a per-interval delta. Use `sum` over the window
  for "how many" and `max` for "worst interval". On G1 the old-generation counter is expected to
  reflect Full GCs, so zero means no Full GC in the window, not that no concurrent or mixed
  work ran. Refuted if GC logs show a `Pause Full` while the metric is 0.
- Aggregate per pod, or use `max` across pods: the default `avg` hides the hot pod.

**Reasoning rules [P]**

- Peak `jvm.heap_memory` over `jvm.heap_memory_max` is occupancy, not headroom. G1 lets used
  heap climb toward the ceiling between collections. Headroom needs the post-GC live set from
  GC logs (`references/gc-pause-triage.md`).
- Working set excludes inactive file cache; the OOM killer acts on `memory.current`
  (`references/container-memory.md`), so a working set under the limit is not proof of no OOM risk.
- Ranking non-heap suspects: compare per pod at the same timestamp, working set minus
  `jvm.heap_memory_committed`. This is a screen with unknown sign: file cache, mapped archives
  and tmpfs inflate it; non-coincident peaks deflate it. Confirm with `memory.stat` (anon vs
  file) and, if `NativeMemoryTracking` is already on, `VM.native_memory summary` (Tier 2, one
  pod). If NMT is off, turning it on is a restart (Tier 3).
- A rollout creates new pods whose restart count starts at 0, so rollouts do not show up as
  restarts. A restart count means a container restarted in place (OOM kill, probe kill, crash,
  `ExitOnOutOfMemoryError`). Read `lastState` per pod for the cause; it holds only the last
  termination. Summing restarts by deployment is distorted by pod replacement, so read it per pod.
- One window is one load shape. Do not size limits from it; include a known peak period
  (`SKILL.md` rule on measuring peaks under real traffic).

## Sources

- `DD-JAVA` https://docs.datadoghq.com/profiler/profiler_troubleshooting/java/
- `DD-SETUP` https://docs.datadoghq.com/tracing/trace_collection/automatic_instrumentation/dd_libraries/java/
- `DDPROF-SRC` https://github.com/DataDog/java-profiler/blob/bf00ddfb976d749e1a83fba36d5ce3e637b94257/ddprof-lib/src/main/cpp/sanityCheck.cpp ; warning seen in https://github.com/DataDog/dd-trace-java/issues/12542

## AOT cache compatibility [O] DD-AOT

Datadog documents AOT class loading and linking support on JDK 25+ with dd-java-agent 1.57.0 or
later. Attach the same `-javaagent` in both the training run and production; if it is missing at
training time the production JVM warns about a mismatched `java.instrument` module setting and
cannot use the cache. No Datadog statement on classic CDS was found.

- `DD-AOT` https://docs.datadoghq.com/tracing/trace_collection/compatibility/java/
