# Library memory, thread and connection behavior

> Last reviewed: 2026-10. JDK 21-27 and the library versions named in the text; see `sources.md`.

Defaults come from project docs or source read on 2026-10 (`sources.md` IDs below). A value may
differ in an older patch release, so check the version you run. Tags: [O] official, [P] practice,
[U] unverified.

## Cross-cutting trap: CPU-derived defaults

Netty, gRPC, the AWS SDK Netty client and Redisson (when set to 0) derive thread and arena
counts from `availableProcessors()`. In a container the JVM reports the CPU limit (quota) if one
is set; with only a request it sees the node's cores (see `gc-cpu-threads.md`). Pin counts
explicitly, or set `-XX:ActiveProcessorCount`; Netty also honors `-Dio.netty.availableProcessors`.
Check what the JVM uses: `jcmd <pid> VM.info | grep -i active_processor_count`.

## Redisson (4.x) [O] DEP-REDISSON, DEP-REDISSON-CONFIG

| Knob | Default |
|---|---|
| `threads` (topic listeners, remote service, executor tasks) | 16; 0 = cores x 2 |
| `nettyThreads` (shared encode/decode event loops) | 32; 0 = cores x 2 |
| `connectionPoolSize` / `connectionMinimumIdleSize` | 64 / 24 (per node in cluster/sentinel modes) |
| `subscriptionConnectionPoolSize` / `subscriptionsPerConnection` | 50 / 5 |
| `idleConnectionTimeout`, `timeout` | 10000 ms, 3000 ms |
| `transportMode` | NIO (EPOLL optional) |

- Several `RedissonClient` instances multiply both thread counts. Per-thread memory cost and
  local-cache memory (`RLocalCachedMap`, heap bounded by `cacheSize`) were not confirmed. [U]
- Verify: `jcmd <pid> Thread.print | grep -c redisson-`, and `ss -tn | grep :6379 | wc -l`
  for sockets. Thread-name prefixes are [P].

## Netty 4.2 [O] DEP-NETTY-SRC, DEP-NETTY-MIGRATION

- Event loop threads: `max(1, io.netty.eventLoopThreads or availableProcessors x 2)`.
- Default allocator is **adaptive** in 4.2 (`io.netty.allocator.type` = adaptive, pooled or
  unpooled); the release that first made it default is [U].
- Pooled allocator: arenas = min(cores x 2, memory-derived cap), chunk 4 MiB (page 8 KiB <<
  maxOrder 9), per-thread caches (small 256, normal 64, max cached buffer 32 KiB). Memory
  retained per arena or thread cache is not returned promptly. [O/P]
- Adaptive allocator: chunks 128 KiB to 8 MiB (2 MiB if max heap <= 512 MiB), stripes up to
  2 x cores, thread-local magazines for event-loop threads.
- `io.netty.maxDirectMemory`: unset means Netty derives the limit from `-XX:MaxDirectMemorySize`,
  else from max heap; 0 means no Netty counting. So heap plus direct can approach 2 x heap plus
  other native memory unless capped (inference from the source logic).
- Leak detection default SIMPLE (about 1% sampled); PARANOID is for tests only.
- Verify: `-XX:NativeMemoryTracking=summary` (Netty direct buffers show under Other/Internal) and
  the allocator's `metric()`/`usedDirectMemory()` APIs.

## gRPC-java 1.8x [O] DEP-GRPC-SRC, DEP-GRPC-PERF

- Worker event loop: shared singleton, thread count = `availableProcessors()`
  (`io.netty.eventLoopThreads` overrides); one shared boss thread.
- Default executor: **unbounded cached thread pool** `grpc-default-executor-%d` (daemon), used
  for callbacks and server application code unless you set `executor(...)`. This is the usual
  thread-count surprise. One timer thread.
- Flow-control window 1 MiB with auto-tuning (setting a fixed window disables tuning);
  `maxInboundMessageSize` 4 MiB; metadata 8 KiB; client keepalive off by default.
- Reuse channels and stubs; cap executor threads for your workload.
- Verify: `jcmd <pid> Thread.print | grep -c grpc-default-executor`.

## Spring Boot and Tomcat [O] DEP-SPRING-PROPS (page version not pinned)

| Property | Default |
|---|---|
| `server.tomcat.threads.max` / `min-spare` | 200 / 10 (ignored if virtual threads are on) |
| `server.tomcat.max-connections` / `accept-count` | 8192 / 100 |
| `spring.threads.virtual.enabled` | false |

- Platform thread stacks are reserved virtual memory (1 MB Linux x64, 2 MB aarch64, [O]
  JAVA-MAN25); only touched pages reach RSS. Count threads; do not multiply by stack size.
- Boot 3 vs 4 differences: [U]. Verify: `jcmd <pid> Thread.print | grep -c http-nio`, or the
  `tomcat.threads.current` actuator metric (needs `server.tomcat.mbeanregistry.enabled=true`).

## HikariCP and PostgreSQL JDBC [O] DEP-HIKARI, DEP-PGJDBC

- Hikari: `maximumPoolSize` 10; `minimumIdle` = max (fixed-size pool); `idleTimeout` 10 min
  (only when minimumIdle < max); `maxLifetime` 30 min, set a few seconds below any DB or proxy
  limit; `connectionTimeout` 30 s. `keepaliveTime` default: [U], check your version.
- The README argues far fewer connections usually perform better than many. Size the pool from
  concurrent DB work, not from request threads (`formulas.md`).
- pgjdbc: `prepareThreshold` 5; statement cache 256 queries or 5 MiB **per connection** (client
  heap = pool size x up to 5 MiB); `defaultRowFetchSize` 0 means the whole result set is read
  into memory, so set a fetch size (and disable autocommit) to stream large results.
- Server-side memory per PostgreSQL connection: [U].
- Verify: `hikaricp.connections.active/pending` metrics; `select count(*) from pg_stat_activity`.

## AWS SDK for Java v2 [O] DEP-AWS-HTTP, DEP-AWS-BEST

- Default sync client Apache5 (since 2.46.0); default async client Netty NIO; the CRT client is
  native ("high throughput"); URL-connection client has limits (no PATCH, no idle-timeout config).
- Defaults: max connections 50, connect timeout 2 s, read 30 s, connection max idle 60 s,
  acquire timeout 10 s; no default `apiCallTimeout` or `apiCallAttemptTimeout`, so set them.
- Netty async clients share a ref-counted `SdkEventLoopGroup` (threads named
  `aws-java-sdk-NettyEventLoop`); 0 threads means Netty's default.
- Each service client owns a connection pool: build one client and share it; close clients you
  stop using; an HTTP client you pass in must be closed by you.
- SQS: max `WaitTimeSeconds` is 20 s (long polling); client read timeout must exceed the wait.
  Each blocking poller thread holds a connection, so pool size >= pollers + other calls. [O/P]

## Jackson

Default buffer recycling uses `ThreadLocal` + `SoftReference`; the source warns about
ThreadLocal retention, and a custom pool can be set (`setRecyclerPool`, 2.16+). Which pool is
default in each of 2.18/2.19/3.x: [U]. Reuse one configured `ObjectMapper` (thread-safe) [P].
Verify retention with `jcmd <pid> GC.class_histogram | grep -i BufferRecycler`.

## APM agents

Agent-specific behavior (for example Datadog) is in `addons/`. Measure any agent with an A/B
with and without `-javaagent`, using NMT and `Thread.print`.
