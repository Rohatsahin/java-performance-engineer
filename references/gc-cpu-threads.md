# GC, CPU and threads in containers

> Last reviewed: 2026-10. JDK 21-27 and the library versions named in the text; see `sources.md`.

Tags and source IDs are defined in `sources.md`.

## 1. Collector choice

- Oracle's guide: Serial for small data or a single CPU; Parallel when pauses of 1 s are fine
  and throughput matters; G1 when response time matters more than throughput; ZGC when latency
  is a top priority. It is a starting point, so measure. [O] ORA-GC-COLL
- JDK 9-26 ergonomics: a "server-class machine" (>= 2 CPUs and >= 1792 MB) gets G1; otherwise
  Serial. JEP 523 (JDK 27) always selects G1. [O] JEP-523
- Generational ZGC: JEP 439 (JDK 21), opt-in with `-XX:+ZGenerational`. `-XX:+UseZGC` is
  generational by default since JDK 23 (JEP 474) and the non-generational mode was removed in
  JDK 24 (JEP 490); `-XX:+/-ZGenerational` now only prints an obsolete-option warning and may be
  rejected in a future release. [O] JEP-439, JEP-474, JEP-490
- Pin the collector (`-XX:+UseG1GC` or `-XX:+UseSerialGC`) so the choice does not flip with the
  CPU limit or a JDK upgrade. Check the effective one with
  `java -XX:+PrintFlagsFinal -version | grep -E 'Use(G1|Serial|Parallel|Z)GC'`.

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
| `-Xmx`, `MaxGCPauseMillis` (200 default) | start here only |
| `-Xmn`, `NewRatio`, `G1NewSizePercent`, `G1MaxNewSizePercent` | avoid: fixing young gen disables pause-time control |
| IHOP | adaptive by default; if Full GCs follow late marking, raise `G1ReservePercent` or set `-XX:-G1UseAdaptiveIHOP -XX:InitiatingHeapOccupancyPercent=45` |
| `G1HeapRegionSize` | objects >= half a region are humongous; raise (e.g. 16m) if humongous churn drives Full GCs |
| `ConcGCThreads` | raise only if concurrent marking does not finish and Full GCs follow |
| `G1PeriodicGCInterval` (0 = off) | periodic GC so idle heap can be uncommitted (JEP 346); resize happens at Remark/Full [O] JEP-346 |
| `Min/MaxHeapFreeRatio` | defaults 40/70 [O] FORM-ORA-GC; confirm with `PrintFlagsFinal` on your JDK |
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
- Mechanism: a 500m limit is 50 ms per 100 ms period; once spent, all threads stop until the
  next period, so many GC/JIT/event-loop threads burn it fast and add latency at low average
  CPU. [P]
- Removing limits vs keeping requests: blogs only. Without a limit the pod is Burstable and
  can use idle node CPU but may starve neighbours and breaks %-of-limit autoscaling. Keep
  memory limit equal to request. [A]

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
