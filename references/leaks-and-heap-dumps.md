# Leaks, growth and heap dumps

> Last reviewed: 2026-10. JDK 21-27 and the library versions named in the text; see `sources.md`.

Tags and source IDs are defined in `sources.md`. Command risk tiers: `command-safety.md`.

## 1. Is it a leak?

A leak is live-set growth that does not level off. Do not call it a leak from "heap used
climbs": G1 usage sawtooths between collections.

- Plot the **live set**: heap occupancy after a collection that has finished reclaiming old
  regions (after a full GC, or after concurrent marking and mixed collections complete), or a
  live-data-size metric where your metrics library provides one. Under G1, occupancy after a
  young collection still contains garbage that mixed collections have not yet reclaimed, so
  that floor can mislead. A rising live-set floor over days is growth; a flat floor with a
  higher peak is not. [P]
- Separate heap growth from native growth: if the heap floor is flat but working set rises,
  go to native memory (`container-memory.md` section 4).
- Separate leak from cache: a bounded cache fills and stops; check configured maximums and
  eviction before suspecting code.
- Correlate with load and deploys; growth only under one traffic type points to one code path.

## 2. Cheapest evidence first

1. Metrics and logs that already exist: live-set trend, allocation rate, GC logs, per-type
   request counts. No new load on the process.
2. JFR with `jdk.OldObjectSample` (old-object sampling, optionally with the path to GC roots)
   for the suspect window; bounded duration and size (Tier 1/2). The event is in the JDK's
   `default` and `profile` JFR settings since JDK 21; path-to-GC-root collection is off by
   default and costs more, so enable it only for the suspect window. [O] JFR-META
3. Allocation profiling (async-profiler `alloc`, `profiling-and-load.md`) shows who allocates,
   not who retains; use it to narrow candidates. [O] ASYNC-MODES
4. Two `GC.class_histogram` snapshots hours apart on **one** pod (Tier 3: the man page rates it
   High impact and the default counts live objects, so expect a full collection). Diff the top
   classes by instance count and bytes; growth in your own types or in `byte[]`/`String`/
   collection entries tells you where to look. [O] JAVA-JCMD25 [P]
5. Heap dump only when 1-4 do not identify the retainer (Tier 3).

## 3. Taking a heap dump safely

- Cost: stop-the-world, writes about heap size, and by default requests a full GC unless
  `-all` is given. [O] JAVA-JCMD25
- Space and destination: see "Where a dump may go" in `command-safety.md` (memory-backed
  volumes count against the memory limit; disk volumes count as ephemeral storage; read-only
  root filesystems need a writable mount; plan retrieval with `kubectl cp`). Compress with
  `-gz` (1 is the fastest level). [O] JAVA-JCMD25 For the automatic dump, point
  `-XX:HeapDumpPath` at a writable volume too. [P]
- Pressure: do not dump a pod that is near its memory limit or being OOM-killed; the dump can
  tip it over. Route traffic away first, or dump a sibling that shows the same growth. [P]
- Automatic dump: `-XX:+HeapDumpOnOutOfMemoryError` fires only for OutOfMemoryError caused by
  Java heap exhaustion; the JDK 25 man page says it does not fire for OOMEs the JVM throws for
  other resource exhaustion such as native thread creation, and it never fires for a kernel
  kill. [O] JAVA-MAN25 The JDK 21 man page lacks that sentence and HotSpot source also dumps on a
  Metaspace OOME, so verify the trigger with a test OOME on your JDK.
  Combine it with `ExitOnOutOfMemoryError` so a wedged JVM restarts (`container-memory.md`).
- Privacy: dumps contain user data and secrets. Restrict access, do not attach them to
  tickets, delete after analysis. [P]

## 4. Reading a dump

- Use a dominator-tree tool (for example Eclipse MAT or a JDK-based analyzer). Sort by
  retained size, not shallow size. [P]
- Questions in order: what is the biggest retained set; which GC root holds it (static field,
  thread local, classloader, listener list); is it expected (cache) or accumulating (map keyed
  by request, unbounded queue, listener never removed). [P]
- Common retainers in services: unbounded queues and maps, `ThreadLocal` values in long-lived
  pools, classloaders after redeploy, listeners and callbacks never unregistered, per-tenant
  caches without limits. [P]
- Fix, then prove: the post-GC floor flattens over the same traffic and duration (use the same
  rollback triggers as `rollout-and-rollback.md`).

## 5. Not a leak

- Allocator retention (RSS stays high after load; `System.trim_native_heap` drops it).
- Direct buffer pools sized by the framework (`dependency-tuning.md`).
- Heap that grows to the ceiling because the ceiling is the setting: expected for a JVM that
  has not needed to collect.
