# Container memory: sizing, kills, native memory, diagnostics

> Last reviewed: 2026-10. JDK 21-27 and the library versions named in the text; see `sources.md`.

Tags and source IDs are defined in `sources.md`.

## 1. JVM container ergonomics

- `UseContainerSupport` is on by default on Linux. [O] JAVA-MAN21
- `MaxRAMPercentage` default 25, `InitialRAMPercentage` 1.5625, `MinRAMPercentage` 50 (applies
  only to very small heaps). [O] JAVA-MAN21
- cgroup v2 detection: JDK 15+, backported to 8u372 and 11.0.16. Older builds on a v2 node may
  size from host RAM. [O] K8S-CGROUPS. Check: `stat -fc %T /sys/fs/cgroup/` (`cgroup2fs` = v2).
  Kubernetes deprecates cgroup v1. [O] K8S-CGROUPS
- Verify what the JVM sees (in the pod):
  `java -XX:+PrintFlagsFinal -version | grep -E 'MaxRAMPercentage|MaxHeapSize|UseContainerSupport'`,
  `java -Xlog:os+container=trace -version` ([O] JAVA-MAN21 documents the `os+container` tag),
  `cat /sys/fs/cgroup/memory.max`.
- Heap percentage is a judgment call. The JDK default is 25%. Vendor starting points: Red Hat
  UBI images use 80% (`JAVA_MAX_MEM_RATIO`) to leave room for probe/exec processes [O] RH-MEM;
  Microsoft's container guide says to allocate 75% of container memory to the heap and never to
  set it equal to the container memory (its example is a 4 GB container with
  `-XX:MaxRAMPercentage=75`). [O] MS-JAVA-CONTAINERS Both are generic starting points that do
  not know your non-heap use. Never 100%. Derive from measurement:
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
| `memory.high` | throttles and reclaims, never invokes the OOM killer; Kubernetes writes it only when the MemoryQoS feature is enabled, so read the value in your pod instead of assuming | [O] KERNEL-CG2 |
| `memory.events` | `oom`, `oom_kill`, `max`, `high` counters; `memory.oom.group=1` kills the whole cgroup | [O] KERNEL-CG2 |
| Node-pressure eviction | pod goes Failed (not OOMKilled); `memory.available = capacity - workingSet`; working set ~ `memory.current - inactive_file` | [O] K8S-EVICT (formula via its linked script, not read) |
| QoS | Guaranteed needs requests == limits for CPU and memory in every container. Kubelet eviction does not rank by QoS class: it ranks pods whose usage exceeds requests first, then Pod Priority, then usage relative to requests; QoS only estimates that order. The kernel OOM killer does use QoS, through the container's `oom_score_adj` (Guaranteed -997, BestEffort 1000) | [O] K8S-QOS, K8S-EVICT |

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
  memory") is logged by the JVM. `HeapDumpOnOutOfMemoryError` fires only for heap exhaustion,
  not for the other kinds, and never for a kernel SIGKILL. [O] JAVA-MAN25
- If the pod dies only when the node is tight, check node pressure and neighbours too.
- `ExitOnOutOfMemoryError` exits with status 3; the heap dump (if enabled) is written before the exit, and `CrashOnOutOfMemoryError` aborts instead. [O] JDK-SRC-27 (source at jdk-27-ga). It never fires for a kernel OOM kill (137).

## 4. Native memory workflow

1. Start with `-XX:NativeMemoryTracking=summary`; overhead is 5-10% plus a 2-word malloc header,
   and it needs a restart to toggle. [O] ORA-DIAG
2. After warm-up: `jcmd <pid> VM.native_memory baseline`; later `summary.diff` (or
   `detail.diff`). Repeat over time; small leaks surface slowly. [O] ORA-DIAG
3. Compare NMT committed with RSS (`grep -E 'VmRSS|VmHWM' /proc/<pid>/status`, cgroup
   `memory.stat` `anon`). A large gap means non-NMT native memory or allocator retention.
4. Map the gap with `pmap -x <pid> | sort -k3 -n | tail` or `/proc/<pid>/smaps`. Many ~64 MB
   anonymous regions suggest glibc arenas. [A]
5. glibc: `MALLOC_ARENA_MAX` default 0 means the cap derives from the CPUs online on the host
   (not the cgroup CPU limit), so a pod limited to 2 CPUs on a many-core node can still grow
   many arenas. [P] The source (`malloc/arena.c`, `NARENAS_FROM_NCORES`) gives 8 per core on
   64-bit [O] GLIBC-ARENA-SRC, and arena-sized region counts consistent with it were seen in the authors' runs [E]. It is an upper
   bound reached only with enough contending threads. `MALLOC_TRIM_THRESHOLD_` default 128 KB but dynamic; setting it (or
   `MALLOC_MMAP_THRESHOLD_`) fixes the value and disables the dynamic adjustment. [O] GLIBC-TUN
   Values from 1 to 4 are used in practice; none is backed by a vendor benchmark, and a lower
   cap trades memory for malloc lock contention, so A/B p99 and CPU under load. [P]
6. Return memory: `jcmd <pid> System.trim_native_heap` (Linux/glibc only; confirm it exists on
   your build with `jcmd <pid> help`). [O] HOTSPOT-TRIM
   Periodic `-XX:TrimNativeHeapInterval=<ms>`: fixed in JDK 22 with backports; it was
   experimental when introduced and became a product flag in 23 (JDK-8325496), so earlier
   builds need `-XX:+UnlockExperimentalVMOptions`. [O] JDK-8293114 It reclaims free pages at the top, not holes inside live memory. If trimming
   drops RSS sharply, it is allocator retention rather than a leak. Lower intervals reclaim more eagerly at higher overhead (JDK man page); the
   lock-contention mechanism is [U], so try the one-off `System.trim_native_heap` on a single
   canary pod first, not a whole fleet.
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
- Cheaper than dumps: `Thread.print` (Medium impact), bounded JFR (see `profiling-and-load.md`).
  `GC.class_histogram` is rated High impact and is Tier 3 (`command-safety.md`); prefer metrics
  and logs first, and run it on one pod.
