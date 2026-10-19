# Container memory: sizing, kills, native memory, diagnostics

Tags and source IDs are defined in `sources.md`.

## 1. JVM container ergonomics

- `UseContainerSupport` is on by default on Linux. [O] JAVA-MAN21
- `MaxRAMPercentage` default 25, `InitialRAMPercentage` 1.5625, `MinRAMPercentage` 50 (applies
  only to very small heaps). [O] JAVA-MAN21
- cgroup v2 detection: JDK 15+, backported to 8u372 and 11.0.16. Older builds on a v2 node may
  size from host RAM. [O/P] K8S-CGROUPS. Check: `stat -fc %T /sys/fs/cgroup/` (`cgroup2fs` = v2).
  Kubernetes deprecates cgroup v1. [O] K8S-CGROUPS
- Verify what the JVM sees (in the pod):
  `java -XX:+PrintFlagsFinal -version | grep -E 'MaxRAMPercentage|MaxHeapSize|UseContainerSupport'`,
  `java -Xlog:os+container=trace -version` ([O] JAVA-MAN21 documents the `os+container` tag),
  `cat /sys/fs/cgroup/memory.max`.
- Heap percentage is a judgment call. The JDK default is 25%; Red Hat UBI images use 80%
  (`JAVA_MAX_MEM_RATIO`) and say it leaves room for probe/exec processes [O] RH-MEM; blogs say
  60-80% depending on non-heap use [A]. Never 100%. Derive from measurement:
  `heap % = (limit - measured non-heap peak - safety) / limit`, where the non-heap peak comes
  from NMT plus arena/smaps at steady state under peak load and `safety` is your choice
  (`formulas.md` section 4). `MaxRAMPercentage` applies to the cgroup limit.

## 2. Memory budget

`limit >= heap + metaspace + code cache + threads x stack + direct buffers + GC structures +
compiler/symbol/internal + malloc overhead and fragmentation + JNI/native libraries + any
non-JVM processes (probes, tmpfs, page cache charged to the cgroup)`.

- Code cache max 240 MB default (48 MB without tiered). Metaspace unlimited by default.
  `MaxDirectMemorySize` is chosen by the JVM when unset. [O] JAVA-MAN21
- NMT categories (Java Heap, Class, Thread, Code, GC, Compiler, Internal, Symbol, Arena Chunk,
  Logging, Other...). Only committed memory counts; RSS counts touched pages. [O] ORA-DIAG
- NMT does not track non-JVM native code (JNI libs, Netty native, zlib) or glibc fragmentation,
  so RSS minus NMT committed points at arenas or native libraries. [O] ORA-DIAG
- This list is a checklist, not a predictor: `threads x Xss` is reserved virtual memory, not
  RSS. No vendor publishes a budget formula; hundreds of MB non-heap is typical. [A]
  Use NMT committed plus measured arenas instead.

## 3. Who kills the pod

| Mechanism | Detail | Source |
|---|---|---|
| cgroup OOM | `memory.max` hit and reclaim fails; container terminated, `lastState.terminated.reason: OOMKilled`, exit 137 (128 + SIGKILL) | [O] K8S-MEM, KERNEL-CG2 |
| `memory.high` | throttles and reclaims, never invokes the OOM killer; used by Kubernetes MemoryQoS on v2 | [O] KERNEL-CG2 |
| `memory.events` | `oom`, `oom_kill`, `max`, `high` counters; `memory.oom.group=1` kills the whole cgroup | [O] KERNEL-CG2 |
| Node-pressure eviction | pod goes Failed (not OOMKilled); `memory.available = capacity - workingSet`; working set ~ `memory.current - inactive_file` | [O] K8S-EVICT (formula via its linked script, not read) |
| QoS | Guaranteed needs requests == limits for CPU and memory in every container; eviction order BestEffort, Burstable, Guaranteed | [O] K8S-QOS |

Requests drive scheduling; the limit is the hard ceiling. `kubectl top` shows working set, so
compare it with the limit, not with heap. [O] K8S-MEM

### Diagnose OOMKilled vs Java OutOfMemoryError

```
kubectl describe pod P | grep -A6 'Last State'
kubectl get pod P -o jsonpath='{.status.containerStatuses[*].lastState}'
kubectl top pod P --containers
kubectl exec P -- cat /sys/fs/cgroup/memory.max /sys/fs/cgroup/memory.current /sys/fs/cgroup/memory.events
kubectl exec P -- grep -E '^(anon|file|kernel|slab|inactive_file|active_file) ' /sys/fs/cgroup/memory.stat
kubectl logs P --previous | grep -i OutOfMemoryError
dmesg -T | grep -iE 'oom|killed process'        # on the node
```

- 137 + OOMKilled + no OutOfMemoryError in logs: total working set hit the limit, usually
  native or non-heap memory. [P]
- 137 without OOMKilled can be a liveness-probe kill or node eviction. [P]
- A Java `OutOfMemoryError` (heap, metaspace, "unable to create native thread", "Direct buffer
  memory") is logged by the JVM; the heap dump hook fires only for that, never for a kernel
  SIGKILL. [P]
- If the pod dies only when the node is tight, check node pressure and neighbours too.
- Exit code and dump ordering for `ExitOnOutOfMemoryError`: [U]; confirm on your JDK.

## 4. Native memory workflow

1. Start with `-XX:NativeMemoryTracking=summary`; overhead is 5-10% plus a 2-word malloc header,
   and it needs a restart to toggle. [O] ORA-DIAG
2. After warm-up: `jcmd <pid> VM.native_memory baseline`; later `summary.diff` (or
   `detail.diff`). Repeat over time; small leaks surface slowly. [O] ORA-DIAG
3. Compare NMT committed with RSS (`grep -E 'VmRSS|VmHWM' /proc/<pid>/status`, cgroup
   `memory.stat` `anon`). A large gap means non-NMT native memory or allocator retention.
4. Map the gap with `pmap -x <pid> | sort -k3 -n | tail` or `/proc/<pid>/smaps`. Many ~64 MB
   anonymous regions suggest glibc arenas. [A]
5. glibc: `MALLOC_ARENA_MAX` default 0 means the cap derives from online cores; the manual
   words it loosely. The source (`malloc/arena.c`, `NARENAS_FROM_NCORES`) gives 8 per core on
   64-bit [O] GLIBC-ARENA-SRC, and arena-sized region counts consistent with it were seen in the authors' runs [E]. It is an upper
   bound reached only with enough contending threads. `MALLOC_TRIM_THRESHOLD_` default 128 KB but dynamic; setting it (or
   `MALLOC_MMAP_THRESHOLD_`) fixes the value and disables the dynamic adjustment. [O] GLIBC-TUN
   The popular `MALLOC_ARENA_MAX=2` has no tested source; A/B it. [A]
6. Return memory: `jcmd <pid> System.trim_native_heap` (JDK 18+, glibc). [O] HOTSPOT-TRIM
   Periodic `-XX:TrimNativeHeapInterval=<ms>`: fix version 22 with backports to 21.0.1 and
   17.0.9, experimental when introduced and made a product flag in 23 (JDK-8325496). [O]
   JDK-8293114. It reclaims free pages at the top, not holes inside live memory. If trimming
   drops RSS sharply, it is allocator retention rather than a leak. Caution: trimming takes
   arena locks and can briefly stall allocating threads, so try the one-off
   `System.trim_native_heap` on a single canary pod first, not a whole fleet.
7. Allocation profiling with jemalloc: `LD_PRELOAD` plus
   `MALLOC_CONF=prof:true,lg_prof_sample:17,lg_prof_interval:30,prof_final:true`, then
   `jeprof --show_bytes <java> <dump>`; needs debug symbols, adds overhead. [A] (vendor guides
  )
8. Direct buffers: BufferPool MXBean and NMT; Netty leak detection
   (`-Dio.netty.leakDetection.level`) [U].

## 5. Diagnostics hygiene

- `-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=<dir>`; default is the working directory,
  off by default. [O] JAVA-MAN21 Mount the dump directory on a volume larger than the heap that
  survives restarts; the container layer is lost and counts toward ephemeral storage.
- `-XX:+ExitOnOutOfMemoryError` so Kubernetes restarts a wedged JVM. [P]
- No JDK in the image: `jattach <pid> jcmd VM.native_memory summary` or
  `jattach <pid> dumpheap /dumps/x.hprof` works with a JRE. [O] JATTACH Ephemeral containers
  with a shared process namespace are the alternative; attach needs the same uid (or root)
  and access to the target's `/tmp`, so verify in staging. [P/U]
- Cheaper than dumps: `jcmd <pid> GC.class_histogram`, `Thread.print`, JFR (see
  `profiling-and-load.md`).
