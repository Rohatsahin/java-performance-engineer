# GC pause and allocation triage

> Last reviewed: 2026-10. JDK 21-27 and the library versions named in the text; see `sources.md`.

Tags and source IDs are defined in `sources.md`. Collector basics and G1 knobs are in
`gc-cpu-threads.md`; this file is the decision path for "p99 is bad, is it the GC?".

## 1. Prove the GC is the cause

0. Confirm which collector is actually running: `jcmd <pid> VM.flags` or the GC log header.
   Before JDK 27 a JVM that sees fewer than 2 CPUs (or, on some x86 hosts, too few after the SMT adjustment in `gc-cpu-threads.md` section 1) or less than 1792 MB selects Serial unless
   a collector is pinned, so "we run G1" under a 1 CPU limit needs checking; JDK 27 always
   selects G1 (JEP 523). [O] JEP-523 and `gc-cpu-threads.md` section 1
1. Log GC and safepoints (`gc-cpu-threads.md` section 2). Without a log, add it and wait for a
   bad window; do not guess.
2. Line up the latency spike timestamps with pause lines. A pause shorter than the spike, or
   no pause at all, means the cause is elsewhere (throttling, downstream, lock, pool).
3. Check the safepoint log for time-to-safepoint: a long wait to reach a safepoint is not GC
   work, and no collector flag fixes it. [P]
4. Check `cpu.stat` throttling over the same window (`gc-cpu-threads.md` section 4). GC
   worker threads can burn a CPU quota and look like a pause problem. [P]
5. Read the CPU line of each stop-the-world pause in the GC log (`gc+cpu`, included in
   `-Xlog:gc*`; printed by G1, Parallel and Serial, so do not expect it from ZGC):
   `User`, `Sys` and `Real`. `Real` far above `User+Sys` means the GC threads were not
   scheduled (CPU starvation or throttling); `Sys` above `User` points to the kernel: memory
   reclaim, page faults, swap, or slow log I/O. `Real` at or below `User+Sys` with parallel
   workers is normal work. [P]

## 2. Read the pause

| Log signal | Likely meaning | First move |
|---|---|---|
| Young pauses grow with load | allocation rate or survivor/promotion pressure | reduce allocation (`hot-paths-and-allocation.md`); do not fix young size under G1 |
| `To-space exhausted`, `Pause Full` | marking began too late or heap too tight | more headroom; `G1ReservePercent`, IHOP per `gc-cpu-threads.md` |
| Humongous allocations in `gc+heap` | objects >= half a region | find the allocator (large arrays, buffers); raise `G1HeapRegionSize` only after |
| Long Remark/Cleanup | many references or large live set | check reference-heavy structures, class unloading |
| Pauses fine, heap near max, CPU high | allocation outpaces concurrent GC | headroom or fewer allocations |
| Pause tracks heap size (G1) | live set or region count | measure live set (old gen after GC) |

G1's pause target (`MaxGCPauseMillis`, default 200 ms) is a soft goal, not a guarantee. [O]
JAVA-MAN25 Oracle's G1 guide advises against fixing the young generation size (`-Xmn`,
`NewRatio`) because it disables pause-time control. [O] ORA-G1-TUNE (`gc-cpu-threads.md`
section 3)

## 3. Choose a collector only after measuring

- Oracle's ranking is a starting point: Parallel for throughput, G1 balanced, ZGC when latency
  is a top priority. [O] ORA-GC-COLL
- ZGC: Oracle's man page states pause times are independent of heap size and "a few
  milliseconds" at most; the ZGC wiki says application threads are not stopped for more than a
  millisecond. [O] JAVA-MAN25, ZGC-WIKI The two statements differ, so measure your own pauses.
  Unused memory is uncommitted by default (`-XX:-ZUncommit` turns it off; uncommit is also off
  when `-Xms` equals `-Xmx`). [O] ZGC-WIKI Cost is some throughput and extra memory
  headroom. [P]
- ZGC generations by release: generational ZGC arrived in JDK 21 behind `-XX:+ZGenerational`,
  became the default ZGC in JDK 23, and the non-generational mode was removed in JDK 24. [O]
  JEP-439, JEP-474, JEP-490 So on JDK 21-22 plain `-XX:+UseZGC` is non-generational, and
  footprint and throughput observations differ across the supported range; record the JDK.
- `SoftMaxHeapSize` (ZGC): a soft limit; ZGC tries to stay below it but may grow to the
  maximum heap rather than stall the application. [O] ZGC-WIKI Use it to keep steady-state
  footprint low while leaving burst headroom. It is a manageable flag introduced for
  ZGC in JDK 13; do not assume G1 honors it, and test the effect on your collector. [P]
- Shenandoah: generational mode is a product feature from JDK 25 (JEP 521), enabled with
  `-XX:+UseShenandoahGC -XX:ShenandoahGCMode=generational`; the default remains the
  single-generation mode. [O] JEP-521 Availability depends on the JDK vendor build. [U]
- Changing collector changes memory: ZGC and Shenandoah use more native bookkeeping and
  headroom than G1 in many workloads. [P] A/B memory and latency together
  (`ab-test-recipe.md`), and check the effect on the AOT cache (the GC may differ between
  training and run, `aot-and-footprint-flags.md`).
- Container limits: ZGC and G1 size their worker threads from the CPUs the JVM sees; a small
  CPU limit with a concurrent collector can starve the application. [P] Measure throttling
  after the change.

## 4. Allocation rate first

Most pause problems are allocation problems. Measure before touching a collector:

- JFR allocation sampling (`jdk.ObjectAllocationSample`, throttled; present in recent JDKs,
  confirm with `jfr summary`) and `jdk.GCHeapSummary`, or async-profiler `alloc`
  (`profiling-and-load.md`). [P] The async-profiler modes are [O] ASYNC-MODES
- Bytes allocated per request = allocation rate / throughput. A change in this number across
  releases is the regression, wherever it shows up.
- JMH `-prof gc` reports allocation rate and GC churn per benchmark operation. [O] JMH-SAMPLES

## 5. Exit criteria

State: pause p99 and max before/after under the same load, GC CPU share, allocation rate,
heap committed, throttling ratio, and rollback triggers (`rollout-and-rollback.md`).
