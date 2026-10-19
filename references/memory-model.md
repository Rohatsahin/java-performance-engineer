# Where container memory goes

> Last reviewed: 2026-10. JDK 21-27 and the library versions named in the text; see `sources.md`.

An idle JVM service can use several times its heap in total. Attribute the rest.

| Region | How to measure | Notes |
|---|---|---|
| Java heap | `jcmd 1 GC.heap_info`, `-Xlog:gc*`, `jvm.heap_memory` | Committed vs used differ; free ratios decide uncommit |
| glibc malloc arenas | `/proc/1/smaps`: many 64 MiB-aligned `rw-p` regions | Rarely returned to the OS; grow with uptime |
| Metaspace, code cache | NMT summary | Bounded by `MaxMetaspaceSize`, `ReservedCodeCacheSize` |
| Thread stacks | NMT `Thread`, thread count | Reserved virtual memory (`-Xss`); RSS counts touched pages plus per-thread native allocations |
| Direct buffers | `jvm.buffer_pool.direct.used` | Netty, gRPC, Redis clients; cap with `MaxDirectMemorySize` |
| AOT/CDS cache | smaps file mappings | Mapped file, ~100-200 MB observed |
| Unaccounted native | cgroup memory minus the above | Usually arenas, JNI libraries, agents |

## Recipes

- Working set vs RSS vs page cache: the kubelet OOM decision uses working set (cgroup
  `memory.current` minus inactive file). `kubectl top` shows working set.
- smaps by mapping (arena regions are ~64 MiB `rw-p`):
  `awk '/^[0-9a-f]+-[0-9a-f]+ /{r=$1;p=$2} /^Rss:/{if(p=="rw-p")s[r]=$2} END{for(k in s)t+=s[k];print t" kB in rw-p"}' /proc/1/smaps`
  then count ~64 MiB regions to estimate arena count.
- NMT: needs `-XX:NativeMemoryTracking=summary` at start (restart to toggle; Oracle documents a
  5-10% performance cost and a 2-word malloc header). Read with
  `jcmd 1 VM.native_memory summary`; use `baseline` then `summary.diff` for growth. NMT does
  not see glibc arena fragmentation or non-JVM native libraries.
- Confirm what the JVM detected: `-Xlog:os+container=trace`.

## glibc arenas

glibc caps arenas by `arena_max`; when unset, the cap derives from online node cores (source:
`NARENAS_FROM_NCORES`, 8 per core on 64-bit; the current manual words this loosely). Arenas are
created on contention up to the cap. Verify the count by region counting on the actual image;
record the glibc version. `MALLOC_ARENA_MAX` and `GLIBC_TUNABLES=glibc.malloc.arena_max=N` are
the same setting. `MALLOC_TRIM_THRESHOLD_` (default 128 KB, dynamic) is an alternative lever;
setting it disables the dynamic adjustment. jemalloc/tcmalloc are other options. musl-based
images do not show the arena pattern.

## Interpreting

- Many arena regions, low heap: cap arenas before touching heap.
- Heap committed far above used, no major GCs: free-ratio flags can give memory back when a GC
  runs.
- High thread count: check default pool sizes in clients before JVM flags.
- Vendor profilers may print "estimated memory requirement exceeds available" warnings; see
  `addons/datadog.md`.
