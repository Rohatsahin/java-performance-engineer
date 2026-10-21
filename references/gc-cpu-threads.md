# GC, CPU and threads in containers

> Last reviewed: 2026-10. JDK 21-27 and the library versions named in the text; see `sources.md`.

Tags and source IDs are defined in `sources.md`.

## 1. Collector choice

- Oracle's guide: Serial for small data or a single CPU; Parallel when pauses of 1 s are fine
  and throughput matters; G1 when response time matters more than throughput; ZGC when latency
  is a top priority. It is a starting point, so measure. [O] ORA-GC-COLL
- JDK 9-26 ergonomics (`os::is_server_class_machine`): G1 when the JVM sees at least 2 active
  processors and at least 1792 MB; otherwise Serial. On x86 the source also divides the active
  processors by the threads-per-package value the CPU reports and requires at least 2, so a small
  container (for example 2-3 CPUs) on such a host may still get Serial; Oracle's guide states only the CPU and
  memory rule. Confirm on the real node with `jcmd <pid> VM.flags` or `-Xlog:gc+init`. [O]
  JDK-OS-CPP JEP 523 (JDK 27) always selects G1. [O] JEP-523
- Generational ZGC: JEP 439 (JDK 21), opt-in with `-XX:+ZGenerational`. `-XX:+UseZGC` is
  generational by default since JDK 23 (JEP 474) and the non-generational mode was removed in
  JDK 24 (JEP 490); `-XX:+/-ZGenerational` now only prints an obsolete-option warning and may be
  rejected in a future release. [O] JEP-439, JEP-474, JEP-490
- Pin the collector (`-XX:+UseG1GC` or `-XX:+UseSerialGC`) so the choice does not flip with the
  CPU limit or a JDK upgrade. Check the effective one with
  `java -XX:+PrintFlagsFinal -version | grep -E 'Use(G1|Serial|Parallel|Z)GC'`.

- Latency-driven collector choice (ZGC, Shenandoah, `SoftMaxHeapSize`) and the pause decision
  path are in `gc-pause-triage.md`.

## 2. GC logging

```
-Xlog:gc*,safepoint:file=/tmp/gc.log:time,uptime,level,tags:filecount=5,filesize=20m
-Xlog:os+container=trace
```

[O] JAVA-MAN21, ORA-G1-TUNE. Reading: pause lines `Pause Young ... 12.3ms`; "To-space
exhausted", `Pause Full` and a late concurrent mark signal marking started too late;
humongous region churn in `gc+heap=info`; the safepoint log shows time-to-safepoint stalls. [P]

## 3. G1 knobs (Oracle G1 tuning guide, [O] ORA-G1-TUNE)

| Knob | Guidance |
|---|---|
| `-Xmx`, `MaxGCPauseMillis` (soft goal, 200 ms default for G1 [O] JAVA-MAN21) | start here only |
| `-Xmn`, `NewRatio` | avoid: fixing young gen disables pause-time control. `G1NewSizePercent`/`G1MaxNewSizePercent`: the guide uses them only as targeted fixes (for example lower `G1NewSizePercent` when object copy dominates pauses); change only with pause evidence |
| IHOP | adaptive by default; if Full GCs follow late marking, raise `G1ReservePercent` (default 10) or disable adaptivity (`-XX:-G1UseAdaptiveIHOP`) and set `-XX:InitiatingHeapOccupancyPercent` below the occupancy at which the log shows marking starting (default 45) |
| `G1HeapRegionSize` | objects >= half a region are humongous; raise (e.g. 16m) if humongous churn drives Full GCs |
| `ConcGCThreads` | default about a quarter of `ParallelGCThreads` [O] JAVA-MAN21; raise only if concurrent marking does not finish and Full GCs follow, and re-check throttling |
| `G1PeriodicGCInterval` (0 = off) | when set, a periodic GC runs after that many ms without one, after which G1 can resize and return memory; G1 otherwise uncommits only at a full GC or during a concurrent cycle [O] JEP-346 |
| `Min/MaxHeapFreeRatio` | defaults 40/70 on JDK 21-26 [O] FORM-ORA-GC. On JDK 27 G1 sets them to 0/100 unless you set them, so it resizes on GC pressure instead (`jdk-27-ga` source; the JDK 27 man page still lists 40/70). Confirm with `PrintFlagsFinal` on your build [O] JDK-SRC-27 |
| `-Xms` = `-Xmx` + `AlwaysPreTouch` | steadier pauses, costs RSS immediately |

## 4. CPU limits and throttling

- `availableProcessors()` comes from the cgroup quota divided by the period, rounded up
  (500m -> 1, 1500m -> 2), capped at host CPUs. [O] JDK-SRC-21, JDK-SRC-27 (source: the cgroup
  code in JDK 21, `os::active_processor_count` in 27)
- CPU shares (requests) were treated as a hard limit on JDK 10-18; JDK-8281181 removed that in
  JDK 19 (11.0.17, 17.0.5, 18.0.2 backports). A pod with a request but no limit therefore sees
  host CPUs and sizes GC/JIT/ForkJoin/Netty pools for them. [O] JDK-8281181 Older posts that
  treat shares as the limit are only right for older JDKs.
- Override with `-XX:ActiveProcessorCount=N`; it sizes GC, ForkJoinPool and common pools.
  [O] JAVA-MAN21 `CICompilerCount` defaults from CPUs and can be set.
- Detect throttling in `/sys/fs/cgroup/cpu.stat`: `nr_periods`, `nr_throttled`,
  `throttled_usec`; `cpu.max` is `$MAX $PERIOD`. [O] KERNEL-CG2. Alert on the throttled-period
  ratio, not average CPU. cAdvisor exports `container_cpu_cfs_periods_total`,
  `container_cpu_cfs_throttled_periods_total` and `container_cpu_cfs_throttled_seconds_total`;
  throttle ratio = rate(throttled periods) / rate(periods). [O] CADVISOR
- Mechanism: `cpu.max` is `$MAX $PERIOD` (period default 100 ms); the quota is shared by all
  threads of the cgroup, so a 500m limit is 50 ms of CPU per 100 ms across all threads, and
  once spent every thread is throttled until the next period. Many GC/JIT/event-loop threads
  burn it fast and add latency at low average CPU. [O] KERNEL-CG2, KERNEL-BWC
- CPU limits vs requests: a limit is a hard cap enforced by throttling even when the node has
  idle CPU; a request is the scheduling guarantee and a proportional weight under contention.
  [O] K8S-RESOURCES, KERNEL-CG2 Dropping the limit lets the pod use idle node CPU (Burstable
  QoS) but the JVM then sees the node's cores (size pools with `ActiveProcessorCount`),
  neighbour protection depends on every pod having a sensible request, and HPA utilization is
  computed against the request, so a request is still required. [O] K8S-HPA Red Hat's
  OpenShift guidance advises against CPU limits for the throttling reason. [P] Keep the memory
  limit equal to the request: memory is not compressible. [P]

## 5. Thread-count audit

`jcmd <pid> Thread.print | grep '^"' | sed 's/-[0-9]*"/"/' | sort | uniq -c` [O] ORA-JCMD
gives threads per pool. Count threads; do not multiply by stack size. Stacks are reserved
virtual memory (1 MB Linux x64, 2 MB aarch64 [O] JAVA-MAN25); RSS counts touched pages.

| Pool | Default | Tag |
|---|---|---|
| Netty event loops | 2 x available processors (`io.netty.eventLoopThreads`, `io.netty.availableProcessors`) | [O] DEP-NETTY-SRC |
| gRPC worker loop / executor | cores; unbounded cached `grpc-default-executor` | [O] DEP-GRPC-SRC |
| Redisson | `nettyThreads` 32 (0 = cores x 2), `threads` 16 | [O] DEP-REDISSON-CONFIG |
| Kotlin `Dispatchers.Default` | cores, minimum 2; `Dispatchers.IO` max(64, cores) | [O] KOTLIN-DISPATCHERS |
| JIT, GC workers | derived from `ActiveProcessorCount` | [O] JAVA-MAN21 |
| Tomcat, Hikari, AWS SDK, virtual threads | see `dependency-tuning.md` | |

Fix: set `ActiveProcessorCount` to the intended CPU budget and cap Netty/Redisson/dispatcher
pools explicitly instead of inheriting host-derived defaults.
