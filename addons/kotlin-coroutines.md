# Kotlin coroutines add-on

> Last reviewed: 2026-10. kotlinx.coroutines 1.x; every [O] claim was read at 1.11.0 (docs and
> source tag `1.11.0`); see the sources below.

Optional. Tags and shared source IDs: see `references/sources.md`. Pool-count audit and the
`ActiveProcessorCount` fix: `references/gc-cpu-threads.md` sections 4 and 5. Virtual threads:
`references/virtual-threads.md`.

## 1. One scheduler behind Default and IO

- `Dispatchers.Default` is backed by a shared pool of threads; by default the maximum number
  of threads is the number of CPU cores, at least two. [O] KCO-DEFAULT
- In source the default of `kotlinx.coroutines.scheduler.core.pool.size` is
  `AVAILABLE_PROCESSORS.coerceAtLeast(2)`. [O] KCO-TASKS
- `Dispatchers.IO` limits parallel blocking work with the system property
  `kotlinx.coroutines.io.parallelism`, default "the limit of 64 threads or the number of cores
  (whichever is larger)". [O] KOTLIN-DISPATCHERS
- IO and Default share threads: `withContext(Dispatchers.IO)` from Default "typically does not
  lead to an actual switching to another thread". [O] KOTLIN-DISPATCHERS
- The IO limit "is _not_ a strict limit on the number of threads"; extra threads may exist but
  only in start-up or shutdown phases. [O] KOTLIN-DISPATCHERS
- Scheduler design: `corePoolSize` workers for CPU-bound tasks plus up to `maxPoolSize` lazily
  created threads for blocking tasks. [O] KCO-SCHEDULER-SRC
- `kotlinx.coroutines.scheduler.max.pool.size` defaults to `MAX_SUPPORTED_POOL_SIZE`, defined as
  `(1 shl BLOCKING_SHIFT) - 2`; `kotlinx.coroutines.scheduler.keep.alive.sec` defaults to 60.
  [O] KCO-TASKS
- The Default count comes from the JVM's available processors, so in a container it follows
  `ActiveProcessorCount` and the cgroup CPU limit; set it explicitly (see
  `references/gc-cpu-threads.md`). [P] The docs say "CPU cores"; the mapping to the JVM value is
  inferred, check it with `Runtime.availableProcessors()` in the pod.

## 2. limitedParallelism

- It creates a view that runs on the original dispatcher with "no more than parallelism
  coroutines" executing at once; the view "does not constitute a resource" and need not be
  closed. [O] KCO-LIMITED
- It limits parallel execution, not concurrency: "It is not a mutex!" Coroutines that suspend
  can all be in flight; use `Mutex` or `Semaphore` to bound concurrent sections. [O] KCO-LIMITED
- `Dispatchers.IO` is elastic: views from `Dispatchers.IO.limitedParallelism(n)` "are not
  restricted by the `Dispatchers.IO` parallelism", so a view of 100 plus one of 60 can give up
  to `64 + 100 + 60` blocking threads at peak. [O] KOTLIN-DISPATCHERS
- Views of `Dispatchers.Default` cannot exceed Default's own parallelism. [O] KCO-LIMITED
- Use: size an IO view to the downstream resource (for example a connection pool) rather than
  relying on the 64 default. The docs give the 100/60 database-connection example; the advice to
  match a pool size is [P]. Pool sizing: `references/dependency-tuning.md`.
- Using `Dispatchers.IO` views to replace a fixed thread pool keeps the same available thread
  count. [O] KCO-LIMITED

## 3. Blocking and starvation

- `Dispatchers.IO` is "designed for offloading blocking IO tasks". [O] KOTLIN-DISPATCHERS
- A blocking call (JDBC, `Thread.sleep`, a blocking HTTP client) on `Dispatchers.Default`
  holds one of at most `cores` workers, so a few blocked requests can stall all coroutines on a
  small pod. [P] Symptom: low CPU, high latency, many parked threads in `jcmd <pid> Thread.print`.
- Default scheduler threads are named `DefaultDispatcher-worker-N`; the prefix comes from the
  `kotlinx.coroutines.scheduler.default.name` default `DefaultDispatcher`. [O] KCO-TASKS
- `runBlocking` blocks the current thread; it is for `main`, tests and non-`suspend` callbacks.
  Calling it in a `suspend` function is "redundant" and risks "thread starvation". [O]
  KCO-RUNBLOCKING On a request thread it parks that thread (Netty event loop, Tomcat worker)
  for the call. [P]

## 4. Cancellation, timeouts, load shedding

- `withTimeout` cancels the block with `TimeoutCancellationException`; cancellation "runs
  concurrently" with the block and may happen after the block finishes but before the caller
  resumes. [O] KCO-TIMEOUT
- Cancellation is cooperative: "withTimeout will not automatically stop all code inside it".
  For blocking JVM code use `runInterruptible` to turn cancellation into thread interruption.
  [O] KCO-TIMEOUT
- Consequence: a timeout on a blocking call without `runInterruptible` returns to the caller
  while the thread stays blocked, so a timeout alone does not shed load or free the thread. [P]

## 5. Flow and channel buffers

- `Flow.buffer()` defaults to `capacity = BUFFERED` and `onBufferOverflow = SUSPEND`: the
  emitter suspends when the buffer is full. [O] KCO-FLOW-BUFFER
- `Channel.BUFFERED` default capacity is 64 with `SUSPEND`; on the JVM the system property
  `kotlinx.coroutines.channels.defaultBuffer` overrides it for all channels with default
  capacity, including in third-party libraries. [O] KCO-CHANNEL-SRC
- `UNLIMITED` buffers grow without bound; they move overload into heap. [P]

## 6. Diagnostics

- `-Dkotlinx.coroutines.debug` (or `-ea`) enables debug mode, which adds coroutine names to
  thread names; the docs call its overhead "negligible". [O] KCO-DEBUG-DOC
- The `kotlinx-coroutines-debug` module is a JVM agent that tracks live coroutines and dumps
  them "similar to thread dump command"; it runs as `-javaagent:kotlinx-coroutines-debug-<ver>.jar`;
  typical probe overhead is "a single-digit percentage"; avoid `enableCreationStackTraces`.
  [O] KCO-DEBUG-README
- A coroutine-level dump is not in `jcmd Thread.print`: suspended coroutines hold no thread. [P]

## 7. Virtual threads

The kotlinx.coroutines pages read here do not mention virtual threads. [U] Whether
`Dispatchers.Default`/`IO` interact with them, or whether `asCoroutineDispatcher()` over a
virtual-thread executor is supported or advisable, is not verified; test it. Use
`references/virtual-threads.md` for the JDK side.

## Sources

- `KCO-DEFAULT` https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-dispatchers/-default.html
- `KCO-LIMITED` https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-coroutine-dispatcher/limited-parallelism.html
- `KCO-RUNBLOCKING` https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/run-blocking.html
- `KCO-TIMEOUT` https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/with-timeout.html
- `KCO-FLOW-BUFFER` https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines.flow/buffer.html
- `KCO-TASKS` https://github.com/Kotlin/kotlinx.coroutines/blob/1.11.0/kotlinx-coroutines-core/jvm/src/scheduling/Tasks.kt
- `KCO-SCHEDULER-SRC` https://github.com/Kotlin/kotlinx.coroutines/blob/1.11.0/kotlinx-coroutines-core/jvm/src/scheduling/CoroutineScheduler.kt
- `KCO-CHANNEL-SRC` https://github.com/Kotlin/kotlinx.coroutines/blob/1.11.0/kotlinx-coroutines-core/common/src/channels/Channel.kt
- `KCO-DEBUG-DOC` https://github.com/Kotlin/kotlinx.coroutines/blob/1.11.0/docs/topics/debugging.md
- `KCO-DEBUG-README` https://github.com/Kotlin/kotlinx.coroutines/blob/1.11.0/kotlinx-coroutines-debug/README.md
