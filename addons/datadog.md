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
   `/tmp`, so request ~100 MB ephemeral storage. The docs give no native-memory overhead
   figure; A/B with `-Ddd.profiling.enabled=false` and compare RSS and NMT.

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
