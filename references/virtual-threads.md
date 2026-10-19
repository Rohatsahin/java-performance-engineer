# Virtual threads

> Last reviewed: 2026-10. JDK 21-27 and the library versions named in the text; see `sources.md`.

Tags and source IDs are defined in `sources.md`. Virtual threads (final in JDK 21, JEP 444)
change what limits concurrency: the thread count stops being the cap, so the next-smallest
resource (connection pool, downstream rate limit, CPU) becomes the bottleneck and the failure
mode. This does not make code faster; it makes blocking code cheaper to run at high
concurrency.

## 1. What they are good for

- Many concurrent tasks that mostly wait on I/O. For CPU-bound work, more threads than cores
  does not help, virtual or not. [O] JEP-444
- They are meant to be one per task and never pooled; to limit concurrency use a semaphore or a
  bounded resource, not a pool of virtual threads. [O] JEP-444
- JDK 17 has no final virtual threads; JDK 21 and later do. The advice in this file does not
  apply to older runtimes.

## 2. Pinning

| Situation | JDK 21-23 | JDK 24+ (JEP 491) |
|---|---|---|
| Blocking while holding a `synchronized` monitor | pins the carrier | virtual thread can unmount |
| Blocking in `Object.wait()` | carrier captured; the scheduler temporarily adds parallelism to compensate | virtual thread can unmount |
| Blocking with a native frame on the stack (native method, or Foreign Function & Memory call back into blocking Java) | pins | still pins |
| Waiting on class loading or class initialization | pins | still pins |

[O] JEP-444, JEP-491. JEP 491 describes the remaining cases as unrelated to `synchronized` and
expected to cause few problems. [O] JEP-491

- The JFR event `jdk.VirtualThreadPinned` reports a virtual thread parked while pinned; it is
  enabled by default with a 20 ms threshold. [O] JEP-444 The `jdk.tracePinnedThreads` system
  property from JEP 444 is removed by JEP 491, so do not rely on it on JDK 24+. [O] JEP-491
- Some blocking operations (for example file I/O) cannot unmount on any release; the scheduler
  compensates by temporarily exceeding its parallelism, up to
  `jdk.virtualThreadScheduler.maxPoolSize`. [O] JEP-444
- Check which JDK you run before reading older advice about `synchronized`; blog posts from the
  JDK 21-23 era describe pinning that no longer applies on 24+. [P]
- Blocking JDBC and legacy client libraries that block inside `synchronized` are the usual
  source of pinning on JDK 21-23; check the driver version and look for `jdk.VirtualThreadPinned`
  events with stacks. [P]
- The scheduler's carrier threads default to the number of available processors
  (`jdk.virtualThreadScheduler.parallelism`); `jdk.virtualThreadScheduler.maxPoolSize` can be
  tuned. [O] JEP-444 Under a 1-2 CPU limit, a few pinned carriers can stall every virtual
  thread, so count CPUs as the JVM sees them (`gc-cpu-threads.md` section 4). [P]

## 3. What to re-size when you adopt them

| Resource | Why it matters now | Check |
|---|---|---|
| Database pool | thousands of tasks wait for ~10-50 connections; waiters queue in the pool | pool `pending` and `acquire` time; `formulas.md` sections 1-2 |
| Downstream HTTP/gRPC | no thread cap protects the callee | per-host connection limits, rate limiters, bulkheads |
| Semaphores | the replacement for pool size as the concurrency cap | one limiter per bounded resource, each sized from Little's Law (`formulas.md`) and that resource's own limit: the database pool size for database work, each downstream's concurrency limit for its calls, the CPU count for CPU-bound steps. One shared permit count sized for the loosest resource lets tasks pile up in front of the tightest one, for example 50 waiting for a pool of 10 |
| Memory | one stack object per task; deep stacks and many tasks cost heap, not reserved stack | `GC.heap_info`, allocation profile under peak |
| ThreadLocals | per-thread caches multiply with one thread per task | thread-local usage in libraries |
| Tomcat/Spring | the request thread cap no longer bounds concurrency; connection limits still apply | see `dependency-tuning.md` |

- Request timeouts matter more: without a thread cap, a slow dependency accumulates tasks
  until memory or a pool gives out. Set per-call timeouts. [P]
- The JIT, GC and the carrier scheduler still size from the CPUs the JVM sees
  (`gc-cpu-threads.md` section 4).

## 4. Diagnose

- Thread dump with virtual threads: `jcmd <pid> Thread.dump_to_file -format=json <file>`
  (Tier 2, `command-safety.md`). [O] JEP-444 The `-format` option accepts `plain` or `json`.
  JEP 444 states that traditional thread dumps are not extended to include
  virtual threads, so `Thread.print` will not show them. [O] JEP-444
- JFR: `jdk.VirtualThreadPinned` and `jdk.VirtualThreadSubmitFailed` (a start or unpark that
  failed, probably a resource issue) are enabled by default; `jdk.VirtualThreadStart` and
  `jdk.VirtualThreadEnd` are disabled by default and must be enabled to count threads. [O]
  JEP-444
- Symptom "latency up after adopting virtual threads, CPU low": suspect a bounded downstream or
  pool first (queueing), pinning second.
- Symptom "memory up": look at heap, not thread stacks; count live virtual threads with the
  Start/End events (off by default) or a JSON thread dump.

## 5. Adoption checklist

1. JDK version recorded; pinning rules checked for it.
2. Every bounded resource identified, with a limiter in front of it.
3. A/B at equal load: p99, error rate, pool pending, heap, CPU throttling (`ab-test-recipe.md`).
4. Rollback: there is no JVM flag that turns virtual threads off; rollback is the application or
   framework switch (or swapping the executor back to a bounded platform-thread pool) or a
   redeploy. Test it before relying on it.
